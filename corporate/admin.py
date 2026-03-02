from django.contrib import admin
from django.core.exceptions import ValidationError
import re
from django.utils.safestring import mark_safe


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
from .models import Owners, BankAccount, Bank, COA, CfItems,Countries
from .services.checko_bank import get_bank_data_by_bik, CheckoBankClientError
from .services.checko_company import get_company_data_by_inn, CheckoCompanyClientError
from mptt.admin import DraggableMPTTAdmin
from django.db.models.functions import Cast
from django.db.models import IntegerField


from utils.choises import CURRENCY_FLAGS, CURRENCY_SYMBOLS


from counterparties.models import Glyph
from counterparties.helpers.glyph_fields import GlyphChoiceField, char_to_code, code_to_char
from .models import Subconto


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
        mark_safe("🏷️ <b>Наименование</b>"),
        {
            "fields": ("name",),
        },
    ),
    (
        mark_safe("📄 <b>Реквизиты</b>"),
        {
            "fields": (
                "full_name",
                "inn",
                "kpp",
                "ogrn",
            ),
        },
    ),
    (
        mark_safe("📍 <b>Контакты</b>"),
        {
            "fields": (
                "address",
                "phone",
                "email",
                "website",
            ),
        },
    ),
    (
        mark_safe("👤 <b>Руководитель</b>"),
        {
            "fields": (
                "ceo_name",
                "ceo_post",
                "ceo_record_date",
            ),
            "classes": ("collapse",),  
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
    readonly_fields = ("type", "address")
    list_filter = ("bik", "name",)

    fieldsets = (
    (
        mark_safe("🏦 <b>Банк</b>"),
        {
            "fields": ("name", "name_eng"),
        },
    ),
    (
        mark_safe("💳 <b>Платёжные реквизиты</b>"),
        {
            "fields": ("bik", "corr_account"),
        },
    ),
    (
        mark_safe("🖼️ <b>Логотип</b>"),
        {
            "fields": ("logo_glyph", "logo"),
            "classes": ("collapse",),   
        },
    ),
    (
        mark_safe("📍 <b>Адрес и тип</b>"),
        {
            "fields": ("type", "address"),
            "classes": ("collapse",),
        },
    ),
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
    list_display = ( "bank_logo", "bank_name",  "account", "currency_view", "bs_acc_code", 'last_statement_day','is_active')
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
    mptt_level_indent = 32
    actions = ["print_coa_registry"]

    list_display = ("tree_actions", "indented_title", "active_badge", "children_badge","id")
    list_display_links = ("indented_title",)
    search_fields = ("code", "name")
    # list_filter = ("is_active",)
    ordering = ("code",)
    preserve_filters = True
    
    
    def _step_for_parent(self, parent_level: int) -> int:
        """
        Шаг для детей в зависимости от уровня родителя.
        Под 6-значные коды:
        level 0: 100000 -> дети 110000/120000... (шаг 10000)
        level 1: 310000 -> дети 311000/312000... (шаг 1000)
        level 2: 321000 -> дети 321100/321200... (шаг 100)
        """
        mapping = {
            0: 10_000,
            1: 1_000,
            2: 100,
            3: 10,
            4: 1,
        }
        return mapping.get(parent_level, 1)
    
    
    def get_changeform_initial_data(self, request):
        """
        Автоподстановка code при 'Добавить дочернюю' (MPTT передаёт ?parent=<id>).
        Шаг зависит от уровня parent.
        """
        initial = super().get_changeform_initial_data(request)

        parent_id = request.GET.get("parent") or request.GET.get("parent_id")
        if not parent_id:
            return initial

        try:
            parent_id = int(parent_id)
        except ValueError:
            return initial

        parent = COA.objects.filter(pk=parent_id).only("id", "code", "level").first()
        if not parent or not (parent.code and parent.code.isdigit()):
            return initial

        # сразу выставляем parent в форме
        initial["parent"] = parent_id

        step = self._step_for_parent(getattr(parent, "level", 0) or 0)

        max_code = (
            COA.objects
            .filter(parent_id=parent_id)              # только прямые дети
            .annotate(code_int=Cast("code", IntegerField()))
            .aggregate(m=Max("code_int"))
            .get("m")
        )

        if max_code is None:
            suggested = int(parent.code) + step
        else:
            suggested = max_code + step

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
    mptt_level_indent = 32

    list_display = ("tree_actions", "indented_title",  "active_badge", "children_badge")
    list_display_links = ("indented_title",)

    search_fields = ("code", "name")
    # list_filter = ("is_active",)
    ordering = ("code",)
    preserve_filters = True
    
    change_list_template = "admin/corporate/cfitems/change_list.html"
    change_form_template = "admin/corporate/cfitems/change_form.html"
    
    
    
    def _count_trailing_zeros(self, code_int: int) -> int:
        """
        Считает количество нулей в конце числа:
        124000 -> 3
        123600 -> 2
        100000 -> 5
        """
        s = str(code_int)
        return len(s) - len(s.rstrip("0"))

    def _step_for_parent(self, parent_code: str) -> int:
        """
        Универсальный шаг "по хвостовым нулям", чтобы влезало до 99 детей
        в рамках диапазона родителя.

        Логика:
        - Диапазон родителя = base .. base + 10^tz - 1, где tz = trailing zeros
        Пример: 124000 (tz=3) -> 124000..124999
        - Хотим до 99 детей -> шаг = 10^(tz-2)
        Пример: tz=3 -> step=10  -> 124010..124990 (99 детей)
                tz=2 -> step=1   -> 123601..123699 (99 детей)
                tz=4 -> step=100 -> 120100..129900 (99 детей)

        Если нулей мало (tz < 2), то шаг = 1.
        """
        if not parent_code or not parent_code.isdigit():
            return 1

        base = int(parent_code)
        tz = self._count_trailing_zeros(base)

        power = max(tz - 2, 0)   # tz=3 -> 1 (10), tz=2 -> 0 (1), tz=4 -> 2 (100)
        return 10 ** power

    def get_changeform_initial_data(self, request):
        initial = super().get_changeform_initial_data(request)

        parent_id = request.GET.get("parent") or request.GET.get("parent_id")
        if not parent_id:
            return initial

        try:
            parent_id = int(parent_id)
        except ValueError:
            return initial

        parent = CfItems.objects.filter(pk=parent_id).only("id", "code").first()
        if not parent or not (parent.code and parent.code.isdigit()):
            return initial

        initial["parent"] = parent_id

        base = int(parent.code)

        # границы диапазона родителя (чтобы дети не "убегали" в соседние статьи)
        tz = self._count_trailing_zeros(base)
        range_end = base + (10 ** tz) - 1  # напр. 124000..124999

        step = self._step_for_parent(parent.code)

        # берём максимум ТОЛЬКО внутри диапазона родителя
        max_code = (
            CfItems.objects
            .filter(parent_id=parent_id)
            .annotate(code_int=Cast("code", IntegerField()))
            .filter(code_int__gte=base, code_int__lte=range_end)
            .aggregate(m=Max("code_int"))
            .get("m")
        )

        if max_code is None:
            suggested = base + step
        else:
            suggested = max_code + step

        # защита от переполнения диапазона
        if suggested > range_end:
            raise ValidationError(
                f"Достигнут лимит дочерних статей для {parent.code}: "
                f"следующий код {suggested} выходит за диапазон {base}-{range_end}."
            )

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




# --- ГЕОГРАФИЯ ---


# --- Validators ---
ISO2_RE = re.compile(r"^[A-Z]{2}$")
CURRENCY_RE = re.compile(r"^[A-Z]{3}$")


class CountriesForm(forms.ModelForm):
    class Meta:
        model = Countries
        fields = "__all__"
        widgets = {
            "regex_patterns": forms.Textarea(
                attrs={
                    "rows": 6,
                    "style": (
                        "font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "
                        "'Liberation Mono', monospace;"
                    ),
                }
            ),
        }

    def clean_code(self):
        code = (self.cleaned_data.get("code") or "").strip().upper()
        if code and not ISO2_RE.match(code):
            raise ValidationError(
                "Код страны должен быть ISO-2: ровно 2 латинские буквы (например, RU, KZ)."
            )
        return code or None

    def clean_currency_code(self):
        c = (self.cleaned_data.get("currency_code") or "").strip().upper()
        if c and not CURRENCY_RE.match(c):
            raise ValidationError(
                "Код валюты должен быть ISO-4217: ровно 3 латинские буквы (например, RUB, EUR)."
            )
        return c or None

    def clean_emojy_flag(self):
        f = (self.cleaned_data.get("emojy_flag") or "").strip()
        return f or None

    def clean_regex_patterns(self):
        text = (self.cleaned_data.get("regex_patterns") or "").strip()
        if not text:
            return None

        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        for i, ln in enumerate(lines, start=1):
            try:
                re.compile(ln)
            except re.error as e:
                raise ValidationError(f"RegEx ошибка в строке {i}: {e}. Паттерн: {ln}")
        return "\n".join(lines)


@admin.register(Countries)
class CountriesAdmin(admin.ModelAdmin):
    form = CountriesForm

    list_display = (
       "country_name", 
        "flag_col",   
        "code_text",
        "currency_text",
    )
    list_display_links = ("country_name",)

    search_fields = ("name", "code", "currency_code")
    list_filter = ("currency_code",)
    ordering = ("name",)
    list_per_page = 50

    fieldsets = (
        (mark_safe("🌍 <b>Страна</b>"), {
            "fields": ("name", "code", "emojy_flag"),

        }),
        (mark_safe("💱 <b>Валюта</b>"), {
            "fields": ("currency_code",),

        }),
        (mark_safe("🔎 <b>Поисковая модель (RegEx)</b>"), {
            "fields": ("regex_patterns",),
  
        }),
    )

    actions = ("normalize_codes", "clear_empty_regex")

    class Media:
        css = {"all": ("css/admin_overrides.css",)}

    # ---------- UI helpers ----------
    @admin.display(description="Флаг")
    def flag_col(self, obj: Countries):
        flag = (obj.emojy_flag or "").strip()
        if not flag:
            return "—"
        return format_html('<span style="font-size:18px;line-height:1;">{}</span>', flag)


    @admin.display(description="Страна", ordering="name")
    def country_name(self, obj: Countries):
        name = obj.name or "—"
        return format_html(
            '<span style="font-weight:900;color:#0f172a;">{}</span>',
            name,
        )

    @admin.display(description="ISO-2", ordering="code")
    def code_text(self, obj: Countries):
        v = (obj.code or "").strip()
        if not v:
            return "—"
        return format_html(
            '<span style="font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas,'
            '\'Liberation Mono\', monospace; font-weight:700; color:#0f172a;'
            'font-variant-numeric: tabular-nums;">{}</span>',
            v,
        )

    @admin.display(description="Валюта", ordering="currency_code")
    def currency_text(self, obj: Countries):
        c = (obj.currency_code or "").strip().upper()
        if not c:
            return "—"
        return format_html(
            '<span style="font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas,'
            '\'Liberation Mono\', monospace; font-weight:700; color:#0f172a;'
            'font-variant-numeric: tabular-nums;">{}</span>',
            c,
        )

    # ---------- actions ----------
    @admin.action(description="🔤 Нормализовать коды (верхний регистр, trim)")
    def normalize_codes(self, request, queryset):
        updated = 0
        for obj in queryset.only("id", "code", "currency_code", "emojy_flag", "regex_patterns"):
            changed = False

            code = (obj.code or "").strip().upper() or None
            if code != obj.code:
                obj.code = code
                changed = True

            cur = (obj.currency_code or "").strip().upper() or None
            if cur != obj.currency_code:
                obj.currency_code = cur
                changed = True

            flag = (obj.emojy_flag or "").strip() or None
            if flag != obj.emojy_flag:
                obj.emojy_flag = flag
                changed = True

            rp = (obj.regex_patterns or "").strip() or None
            if rp != obj.regex_patterns:
                obj.regex_patterns = rp
                changed = True

            if changed:
                obj.save(update_fields=["code", "currency_code", "emojy_flag", "regex_patterns"])
                updated += 1

        self.message_user(request, f"Обновлено записей: {updated}")

    @admin.action(description="🧹 Очистить пустые regex_patterns")
    def clear_empty_regex(self, request, queryset):
        # чистим и пустые строки, и строки из пробелов
        qs = queryset.filter(regex_patterns__isnull=False)
        updated = 0
        for obj in qs.only("id", "regex_patterns"):
            if not (obj.regex_patterns or "").strip():
                obj.regex_patterns = None
                obj.save(update_fields=["regex_patterns"])
                updated += 1
        self.message_user(request, f"Очищено записей: {updated}")


@admin.register(Subconto)
class SubcontoAdmin(DraggableMPTTAdmin):
    mptt_level_indent = 32
    list_display = ("tree_actions", "indented_title", "code", "name", "id")
    list_display_links = ("indented_title",)
    search_fields = ("code", "name")
    ordering = ("code",)
    preserve_filters = True
    
  
    class Media:
        css = {
            "all": (
              
                "css/admin_overrides.css",  
                "css/mptt_pretty.css"
            )
        }