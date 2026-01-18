from django.contrib import admin
from django.db.models import Count
from django.utils.html import format_html
from django.contrib import messages
from django.shortcuts import redirect
from django import forms
from .models import Owners, BankAccount, Bank, COA, СfItems
from .services.checko_bank import get_bank_data_by_bik, CheckoBankClientError
from .services.checko_company import get_company_data_by_inn, CheckoCompanyClientError
from mptt.admin import DraggableMPTTAdmin


from counterparties.models import Glyph
from counterparties.helpers.glyph_fields import GlyphChoiceField, char_to_code, code_to_char



#---------- ФОРМЫ ---------#
class BankForm(forms.ModelForm):
    logo_glyph = GlyphChoiceField(
        queryset=Glyph.objects.all().order_by("sort", "title"),
        required=False,
        label="Логотип (глиф)",
        help_text="Выберите глиф банка. В базе сохранится символ.",
    )

    class Meta:
        model = Bank
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # скрываем реальное поле logo
        if "logo" in self.fields:
            self.fields["logo"].widget = forms.HiddenInput()
            self.fields["logo"].required = False

        # initial по сохранённому символу
        current = getattr(self.instance, "logo", None)
        code = char_to_code(current)
        if code:
            self.fields["logo_glyph"].initial = Glyph.objects.filter(code=code).first()

        # шрифт для select
        self.fields["logo_glyph"].widget.attrs.update({
            "style": "font-family:NotoManu, sans-serif; font-size:18px;",
        })

    def save(self, commit=True):
        instance = super().save(commit=False)

        g = self.cleaned_data.get("logo_glyph")
        instance.logo = code_to_char(g.code) if g else None

        if commit:
            instance.save()
            self.save_m2m()

        return instance



class BankAccountInline(admin.TabularInline):
    model = BankAccount
    extra = 1
    # bik убрали — у собственника только выбор банка, счёт и валюта
    fields = ("bank", "account", "currency")
    autocomplete_fields = ("bank",)
    

#----- СОБСТВЕННИКИ ----#
@admin.register(Owners)
class OwnersAdmin(admin.ModelAdmin):

    list_display = ("name", "inn", "ceo_display", "bankaccounts_count_display")
    inlines = [BankAccountInline]

    class Media:
        js = ("corporate/js/owners_fill.js",)

    fieldsets = (
        (
            "Отображение в системе",
            {"fields": ("name",)},
        ),
        (
            "Юридические реквизиты",
            {
                "fields": (
                    "full_name",
                    "inn",
                    "kpp",
                    "ogrn",
                )
            },
        ),
        (
            "Контакты и адрес",
            {
                "fields": (
                    "address",
                    "phone",
                    "email",
                    "website",
                )
            },
        ),
        (
            "Руководитель",
            {
                "fields": (
                    "ceo_name",
                    "ceo_post",
                    "ceo_record_date",
                )
            },
        ),
    )

    @admin.display(description="Руководитель")
    def ceo_display(self, obj):
        if not obj.ceo_name and not obj.ceo_post:
            return "—"
        if obj.ceo_post:
            return format_html(
                "{}<br><span style='color:#666;font-size:11px;'>{}</span>",
                obj.ceo_name or "",
                obj.ceo_post,
            )
        return obj.ceo_name or "—"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(_bankaccounts_count=Count("bankaccount"))

    @admin.display(description="Кол-во расчётных счетов", ordering="_bankaccounts_count")
    def bankaccounts_count_display(self, obj):
        return obj._bankaccounts_count

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        if "_fill_by_inn" in request.POST:
            post = request.POST.copy()
            inn = (post.get("inn") or "").strip()

            if not inn:
                messages.warning(request, "Сначала введите ИНН.")
            else:
                try:
                    data = get_company_data_by_inn(inn)
                except CheckoCompanyClientError as e:
                    messages.error(request, f"Ошибка Checko: {e}")
                except Exception as e:
                    messages.error(request, f"Ошибка при обращении к API Checko: {e}")
                else:
                    if data:
                        # name не трогаем
                        post["kpp"] = data.get("kpp") or post.get("kpp", "")
                        post["ogrn"] = data.get("ogrn") or post.get("ogrn", "")
                        post["address"] = data.get("address") or post.get("address", "")
                        post["phone"] = data.get("phone") or post.get("phone", "")
                        post["email"] = data.get("email") or post.get("email", "")
                        post["website"] = data.get("website") or post.get("website", "")

                        post["full_name"] = data.get("full_name") or post.get("full_name", "")
                        post["ceo_name"] = data.get("ceo_name") or post.get("ceo_name", "")
                        post["ceo_post"] = data.get("ceo_post") or post.get("ceo_post", "")
                        post["ceo_record_date"] = data.get("ceo_record_date") or post.get(
                            "ceo_record_date", ""
                        )

                        post["_continue"] = "1"
                        if "_fill_by_inn" in post:
                            del post["_fill_by_inn"]

                        request.POST = post

                        messages.success(
                            request,
                            f"Данные по компании с ИНН {inn} подтянуты и подставлены в форму.",
                        )
                    else:
                        messages.warning(request, f"Компания по ИНН {inn} не найдена.")

        return super().changeform_view(request, object_id, form_url, extra_context)
    
    

# ----- БАНКИ ---- #
@admin.register(Bank)
class BankAdmin(admin.ModelAdmin):
    form = BankForm
    exclude = ("inn", "kpp")
    list_display = ( "logo_preview","name", "bik", "corr_account")
    search_fields = ("name", "bik")
    list_display_links = ("name",)

    fieldsets = (
    ("🏦 Банк", {
        "fields": ("name", "name_eng", "bik", "corr_account"),
    }),
    ("🖼️ Логотип", {
        "fields": ("logo_glyph", "logo"),  # logo hidden в форме, но пусть будет
        "description": "Выберите глиф — в базе сохранится символ в поле «logo».",
    }),
    ("📍 Адрес и тип", {
        "fields": ("type", "address"),
    }),
)
    
    
    @admin.display(description="Лого")
    def logo_preview(self, obj):
            if not obj.logo:
                return "—"

            outer = (
                "display:inline-flex;align-items:center;justify-content:center;"
                "width:28px;height:28px;border-radius:999px;"
                "background:linear-gradient(135deg,#f8fafc,#f1f5f9);"
                "box-shadow:0 0 0 1px rgba(148,163,184,.35);"
            )
            inner = "font-family:NotoManu;font-size:20px;line-height:1;"

            return format_html(
                '<span style="{}"><span style="{}">{}</span></span>',
                outer, inner, obj.logo
            )

    class Media:
        css = {
            "all": (
                "fonts/glyphs.css",
                "css/admin_overrides.css",  # ← критично, ты уже поймала это 👍
            )
        }
        js = ("corporate/js/bank_fill.js", "js/glyph_select2.js",)

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        """
        Обработка кнопки 'Заполнить по БИК' на форме банка.
        """
        if "_fill_by_bik" in request.POST:
            post = request.POST.copy()
            bik = (post.get("bik") or "").strip()

            if not bik:
                messages.warning(request, "Сначала введите БИК.")
                return redirect(request.path)

            try:
                data = get_bank_data_by_bik(bik)
            except CheckoBankClientError as e:
                messages.error(request, f"Ошибка Checko: {e}")
                return redirect(request.path)
            except Exception as e:
                messages.error(request, f"Ошибка при обращении к API Checko: {e}")
                return redirect(request.path)
            else:
                if data:
                    post["name"] = data.get("name") or post.get("name", "")
                    post["name_eng"] = data.get("name_eng") or post.get("name_eng", "")
                    post["address"] = data.get("address") or post.get("address", "")
                    post["corr_account"] = data.get("corr_account") or post.get(
                        "corr_account", ""
                    )
                    post["type"] = data.get("type") or post.get("type", "")

                    # Остаёмся на форме
                    post["_continue"] = "1"
                    if "_fill_by_bik" in post:
                        del post["_fill_by_bik"]

                    request.POST = post

                    messages.success(
                        request,
                        f"Данные по банку с БИК {bik} подтянуты и подставлены в форму.",
                    )
                else:
                    messages.warning(request, f"Банк по БИК {bik} не найден.")
                    return redirect(request.path)

        return super().changeform_view(request, object_id, form_url, extra_context)


# ----- БАНКОВСКИЕ СЧЕТА ---- #

@admin.register(BankAccount)
class BankAccountAdmin(admin.ModelAdmin):
    list_display = ("corporate", "bank_logo", "bank_name", "bik", "account", "currency")
    list_display_links = ("bank_name",)
    search_fields = ("corporate__name", "bank__name", "bik", "account")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related("bank", "corporate")
    
    class Media:
        css = {
            "all": (
                "fonts/glyphs.css",
                "css/admin_overrides.css",
            )
        }

    @admin.display(description="", ordering="bank__name")
    def bank_logo(self, obj):
        if not obj.bank or not obj.bank.logo:
            return "—"

        outer = (
            "display:inline-flex;align-items:center;justify-content:center;"
            "width:24px;height:24px;border-radius:999px;"
            "background:linear-gradient(135deg,#f8fafc,#f1f5f9);"
            "box-shadow:0 0 0 1px rgba(148,163,184,.35);"
        )
        inner = "font-family:NotoManu;font-size:16px;line-height:1;"
        return format_html('<span style="{}"><span style="{}">{}</span></span>', outer, inner, obj.bank.logo)

    @admin.display(description="Банк", ordering="bank__name")
    def bank_name(self, obj):
        return obj.bank.name if obj.bank else "—"


@admin.register(COA)
class AccountAdmin(DraggableMPTTAdmin):
    mptt_level_indent = 7
    list_display = ("tree_actions", "indented_title", "code", "is_active")
    list_display_links = ("indented_title",)
    search_fields = ("code", "name")

@admin.register(СfItems)
class CashFlowItemAdmin(DraggableMPTTAdmin):
    mptt_level_indent = 7
    list_display = ("tree_actions", "indented_title", "code", "is_active")
    list_display_links = ("indented_title",)
    search_fields = ("code", "name")