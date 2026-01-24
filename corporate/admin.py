from django.contrib import admin

from django.db.models import Count, Max
from django.shortcuts import render
from django.urls import path
from django.utils import timezone
from datetime import datetime
from django.conf import settings
from django.utils.html import format_html
from django.contrib import messages
from django.shortcuts import redirect
from django import forms
from .models import Owners, BankAccount, Bank, COA, CfItems
from .services.checko_bank import get_bank_data_by_bik, CheckoBankClientError
from .services.checko_company import get_company_data_by_inn, CheckoCompanyClientError
from mptt.admin import DraggableMPTTAdmin
from django.db.models.functions import Cast
from django.db.models import IntegerField

from treasury.models import BankStatements

from utils.choises import CURRENCY_FLAGS, CURRENCY_SYMBOLS


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
        css = {
            "all": (
                "fonts/glyphs.css",
                "css/admin_overrides.css", 
            )
        }
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
                "width:28px;height:28px;border-radius:6px;"
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
                "css/admin_overrides.css",  
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
    list_display = ( "bank_logo", "bank_name",  "account", "currency_view", "bs_acc_code", 'last_statement_day')
    list_display_links = ("bank_name",)
    search_fields = ("corporate__name", "bank__name",  "account")
    list_filter = ("corporate__name",) 
    
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return (
            qs.select_related("bank", "corporate")
            .annotate(_last_bs_day=Max("bankstatements__finish"))
        )
    
    class Media:
        css = {
            "all": (
                "fonts/glyphs.css",
                "css/admin_overrides.css",
            )
        }
        
    @admin.display(description="Последняя выписка", ordering="_last_bs_day")
    def last_statement_day(self, obj):
        d = getattr(obj, "_last_bs_day", None)
        if not d:
            return format_html('<span style="color:#94a3b8;font-weight:800;">—</span>')
        return format_html(
            '<span style="font-weight:900;color:#0f172a;font-variant-numeric:tabular-nums;">{}</span>',
            d.strftime("%d.%m.%Y"),
        )

        
    
    @admin.display(description="Валюта", ordering="currency")
    def currency_view(self, obj):
        code = (obj.currency or "").upper()
        flag = CURRENCY_FLAGS.get(code, "")
        sym = CURRENCY_SYMBOLS.get(code, "")
        # показываем: 🇷🇺 ₽ RUB (или просто RUB если нет в словаре)
        return format_html(
            '<span style="display:inline-flex;align-items:center;gap:6px;white-space:nowrap;">'
            '<span style="font-size:16px;line-height:1;">{}</span>'
            '<span style="font-weight:700;">{}</span>'
            '<span style="opacity:.8;">{}</span>'
            '</span>',
            flag, sym, code
        )
        
        
    @admin.display(description="Балансовый счет", ordering="bs_acc__code")
    def bs_acc_code(self, obj):
        if not obj.bs_acc:
            return "—"
        return obj.bs_acc.code  # <-- только номер

    @admin.display(description="", ordering="bank__name")
    def bank_logo(self, obj):
        if not obj.bank or not obj.bank.logo:
            return "—"

        outer = (
            "display:inline-flex;align-items:center;justify-content:center;"
            "width:24px;height:24px;border-radius:6px;"
            "background:linear-gradient(135deg,#f8fafc,#f1f5f9);"
            "box-shadow:0 0 0 1px rgba(148,163,184,.35);"
        )
        inner = "font-family:NotoManu;font-size:16px;line-height:1;"
        return format_html('<span style="{}"><span style="{}">{}</span></span>', outer, inner, obj.bank.logo)

    @admin.display(description="Банк", ordering="bank__name")
    def bank_name(self, obj):
        return obj.bank.name if obj.bank else "—"


# ----- ПЛАН СЧЕТОВ ---- #

def _now_pretty():
    if getattr(settings, "USE_TZ", False):
        return timezone.localtime(timezone.now())
    return datetime.now()


@admin.register(COA)

class AccountAdmin(DraggableMPTTAdmin):
    mptt_level_indent = 12
    actions = ["print_coa_registry"]

    list_display = ("tree_actions", "indented_title", "active_badge", "children_badge")
    list_display_links = ("indented_title",)
    search_fields = ("code", "name")
    # list_filter = ("is_active",)
    ordering = ("code",)
    preserve_filters = True
    
    
    def get_changeform_initial_data(self, request):
        """
        Автоподстановка code при 'Добавить дочернюю' (MPTT передаёт ?parent=<id>).
        Шаг: 100
        """
        initial = super().get_changeform_initial_data(request)

        parent_id = request.GET.get("parent") or request.GET.get("parent_id")
        if not parent_id:
            return initial

        try:
            parent_id = int(parent_id)
        except ValueError:
            return initial

        # пусть parent в форме будет сразу выставлен
        initial["parent"] = parent_id

        # максимум среди прямых детей
        max_code = (
            COA.objects
            .filter(parent_id=parent_id)
            .annotate(code_int=Cast("code", IntegerField()))
            .aggregate(m=Max("code_int"))
            .get("m")
        )

        if max_code is None:
            parent_code = COA.objects.filter(pk=parent_id).values_list("code", flat=True).first()
            if parent_code and parent_code.isdigit():
                suggested = int(parent_code) + 100
            else:
                suggested = 100000
        else:
            suggested = max_code + 100

        initial["code"] = f"{suggested:06d}"
        return initial

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(_children_count=Count("children"))

    @admin.display(description="Статус", ordering="is_active")
    def active_badge(self, obj):
        if obj.is_active:
            return format_html(
                '<span style="display:inline-flex;align-items:center;gap:6px;'
                'padding:4px 10px;border-radius:6px;font-size:10px;font-weight:700;'
                'background:rgba(16,185,129,.12);color:#065f46;'
                'border:1px solid rgba(16,185,129,.22);'
                'box-shadow:0 6px 18px rgba(15,23,42,.08);">'
                '<span style="width:8px;height:8px;border-radius:50%;background:#10b981;'
                'box-shadow:0 0 0 3px rgba(16,185,129,.18);"></span>'
                'Активен</span>'
            )
        return format_html(
            '<span style="display:inline-flex;align-items:center;gap:6px;'
            'padding:4px 10px;border-radius:6px;font-size:10px;font-weight:700;'
            'background:rgba(239,68,68,.10);color:#7f1d1d;'
            'border:1px solid rgba(239,68,68,.20);'
            'box-shadow:0 6px 18px rgba(15,23,42,.08);">'
            '<span style="width:8px;height:8px;border-radius:50%;background:#ef4444;'
            'box-shadow:0 0 0 3px rgba(239,68,68,.16);"></span>'
            'Выключен</span>'
        )

    @admin.display(description="Дочерних", ordering="_children_count")
    def children_badge(self, obj):
        n = getattr(obj, "_children_count", 0) or 0
        if n == 0:
            return format_html(
                '<span style="display:inline-flex;align-items:center;justify-content:center;'
                'min-width:30px;padding:4px 10px;border-radius:6px;'
                'font-size:10px;font-weight:800;'
                'background:rgba(148,163,184,.16);color:#475569;'
                'border:1px solid rgba(148,163,184,.28);">0</span>'
            )
        return format_html(
            '<span style="display:inline-flex;align-items:center;justify-content:center;'
            'min-width:30px;padding:4px 10px;border-radius:6px;'
            'font-size:10px;font-weight:800;'
            'background:rgba(59,130,246,.10);color:#1e3a8a;'
            'border:1px solid rgba(59,130,246,.18);">{}</span>',
            n,
        )

    # ---------- ACTION: печать выбранных ----------
    @admin.action(description="🖨 Печатная форма выбранных счетов")
    def print_coa_registry(self, request, queryset):
        qs = queryset.order_by("tree_id", "lft", "code")
        items = list(qs)
        for x in items:
            x.indent_px = (getattr(x, "level", 0) or 0) * 16  # можно 14–18

        context = {
            "title": "План счетов — печатная форма (выбранные)",
            "printed_at": _now_pretty(),
            "items": items,
            "mode": "selected",
            "total": len(items),
        }
        return render(request, "admin/corporate/coa/coa_print.html", context)


    # ---------- URL: печать всего плана ----------
    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "print/",
                self.admin_site.admin_view(self.print_all),
                name=f"{COA._meta.app_label}_{COA._meta.model_name}_print_all",
            ),
        ]
        return custom + urls


    def print_all(self, request):
        qs = COA.objects.all().order_by("tree_id", "lft", "code")
        items = list(qs)
        for x in items:
            x.indent_px = (getattr(x, "level", 0) or 0) * 16

        context = {
            "title": "План счетов — печатная форма",
            "printed_at": _now_pretty(),   
            "items": items,
            "mode": "all",
            "total": len(items),
        }
        return render(request, "admin/corporate/coa/coa_print.html", context)
    

    class Media:
        css = {
            "all": (
              
                "css/admin_overrides.css",  
                "css/mptt_pretty.css"
            )
        }

# ----- СТАТЬИ ДВИЖЕНИЯ ДЕНЕЖНЫХ СРЕДСТВ ---- #  

@admin.register(CfItems)

class CashFlowItemAdmin(DraggableMPTTAdmin):
    mptt_level_indent = 12

    list_display = ("tree_actions", "indented_title",  "active_badge", "children_badge")
    list_display_links = ("indented_title",)

    search_fields = ("code", "name")
    # list_filter = ("is_active",)
    ordering = ("code",)
    preserve_filters = True
    
    change_list_template = "admin/corporate/cfitems/change_list.html"
    change_form_template = "admin/corporate/cfitems/change_form.html"
    
    
    
    
    def get_changeform_initial_data(self, request):
        """
        Когда открываем /add/?parent=<id> (кнопка 'Добавить дочернюю'),
        подставляем следующий code внутри ветки этого parent.
        """
        initial = super().get_changeform_initial_data(request)

        parent_id = request.GET.get("parent") or request.GET.get("parent_id")
        if not parent_id:
            return initial

        try:
            parent_id = int(parent_id)
        except ValueError:
            return initial

        # Если parent уже будет проставлен MPTT — ок, но мы продублируем.
        initial["parent"] = parent_id

        # Ищем максимум среди детей этого parent (только прямые дети)
        # code хранится как строка, поэтому приводим к int для Max
        max_code = (
            CfItems.objects
            .filter(parent_id=parent_id)
            .annotate(code_int=Cast("code", IntegerField()))
            .aggregate(m=Max("code_int"))
            .get("m")
        )

        if max_code is None:
            # если детей нет — можно начать с "код_родителя + 01" (или +001)
            parent_code = CfItems.objects.filter(pk=parent_id).values_list("code", flat=True).first()
            if parent_code and parent_code.isdigit():
                # пример логики: 123000 -> 123100 (первый ребенок сотней)
                # можно выбрать любую логику, ниже типовая "следующая сотня"
                base = int(parent_code)
                suggested = base + 100
            else:
                suggested = 100000
        else:
            suggested = max_code + 100  # твоя логика шага (100)

        initial["code"] = f"{suggested:06d}"
        return initial



    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(_children_count=Count("children"))

    @admin.display(description="Статус", ordering="is_active")
    def active_badge(self, obj):
        if obj.is_active:
            return format_html(
                '<span style="display:inline-flex;align-items:center;gap:6px;'
                'padding:4px 10px;border-radius:6px;'
                'font-size:12px;font-weight:700;'
                'background:rgba(16,185,129,.12);color:#065f46;'
                'border:1px solid rgba(16,185,129,.22);">'
                '<span style="width:8px;height:8px;border-radius:50%;background:#10b981;'
                'box-shadow:0 0 0 3px rgba(16,185,129,.16);"></span>'
                'Активна</span>'
            )
        return format_html(
            '<span style="display:inline-flex;align-items:center;gap:6px;'
            'padding:4px 10px;border-radius:6px;'
            'font-size:12px;font-weight:700;'
            'background:rgba(239,68,68,.10);color:#7f1d1d;'
            'border:1px solid rgba(239,68,68,.20);">'
            '<span style="width:8px;height:8px;border-radius:50%;background:#ef4444;'
            'box-shadow:0 0 0 3px rgba(239,68,68,.12);"></span>'
            'Выключена</span>'
        )

    @admin.display(description="Дочерних", ordering="_children_count")
    def children_badge(self, obj):
        n = getattr(obj, "_children_count", 0) or 0
        if n == 0:
            return format_html(
                '<span style="display:inline-flex;align-items:center;justify-content:center;'
                'min-width:30px;padding:4px 10px;border-radius:6px;'
                'font-size:12px;font-weight:800;'
                'background:rgba(148,163,184,.16);color:#475569;'
                'border:1px solid rgba(148,163,184,.28);">0</span>'
            )
        return format_html(
            '<span style="display:inline-flex;align-items:center;justify-content:center;'
            'min-width:30px;padding:4px 10px;border-radius:6px;'
            'font-size:12px;font-weight:800;'
            'background:rgba(14,165,233,.10);color:#075985;'
            'border:1px solid rgba(14,165,233,.18);">{}</span>',
            n,
        )


    @admin.display(description="Код", ordering="code")
    def code_badge(self, obj):
        return format_html(
            '<span style="font-family: ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,'
            '\'Liberation Mono\',monospace;'
            'font-weight:800;font-size:12px;'
            'padding:4px 10px;border-radius:10px;'
            'background:#f1f5f9;color:#0f172a;'
            'border:1px solid rgba(15,23,42,.10);'
            'display:inline-flex;align-items:center;">{}</span>',
            obj.code,
        )
        
    
    
    # ---------- ACTION: печать выбранных ----------
    @admin.action(description="🖨 Печатная форма выбранных статей ДС")
    def print_cfitems_registry(self, request, queryset):
        items = list(queryset.order_by("tree_id", "lft", "code"))
        for x in items:
            x.indent_px = (getattr(x, "level", 0) or 0) * 16

        context = {
            "title": "Статьи ДС — печатная форма (выбранные)",
            "printed_at": _now_pretty(),

            "items": items,
            "mode": "selected",
            "total": len(items),
            "back_url": request.META.get("HTTP_REFERER") or "",
        }
        return render(request, "admin/corporate/cfitems/cfitems_print.html", context)

    # ---------- URL: печать всего списка ----------
    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "print/",
                self.admin_site.admin_view(self.print_all),
                name=f"{CfItems._meta.app_label}_{CfItems._meta.model_name}_print_all",
            ),
        ]
        return custom + urls

    def print_all(self, request):
        items = list(CfItems.objects.all().order_by("tree_id", "lft", "code"))
        for x in items:
            x.indent_px = (getattr(x, "level", 0) or 0) * 16

        context = {
            "title": "Статьи ДС — печатная форма",
            "printed_at": _now_pretty(),
   
            "items": items,
            "mode": "all",
            "total": len(items),
            "back_url": request.META.get("HTTP_REFERER") or "",
        }
        return render(request, "admin/corporate/cfitems/cfitems_print.html", context)
    
    
    class Media:
        css = {
            "all": (
              
                "css/admin_overrides.css",  
                "css/mptt_pretty.css"
            )
        }

