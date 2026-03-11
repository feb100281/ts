from django.contrib import admin
from django.contrib.admin import RelatedOnlyFieldListFilter
from django.db.models import Count, Prefetch
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django import forms
import json
import os
from datetime import date
from django.urls import reverse

from contracts.accruals.registry import ACCRUAL_REGISTRY
from django.template.response import TemplateResponse
from django.shortcuts import get_object_or_404

from contracts.accruals.service import preview_accruals

from .models import (
    Contracts,
    Conditions,
    ContractsTitle,
    ContractItems,
    ContractFiles,
    CfItemAuto,
    AccountingMethod,
)
from .models import AccuralFn

from jsoneditor.forms import JSONEditor

from django.db import models


def get_current_condition(obj):
    # если conditions уже prefetched — это будет обычный список в памяти
    conds = list(getattr(obj, "conditions", []).all())
    if not conds:
        return None

    # date_start=None считаем самым старым
    conds.sort(
        key=lambda c: (c.date_start is not None, c.date_start, c.id), reverse=True
    )
    return conds[0]


class HasAccrualFunctionFilter(admin.SimpleListFilter):
    title = "Функция начисления"
    parameter_name = "has_accrual_fn"

    def lookups(self, request, model_admin):
        return (
            ("yes", "Есть функция"),
            ("no", "Нет функции"),
        )

    def queryset(self, request, queryset):
        val = self.value()

        if val == "yes":
            return queryset.filter(conditions__isnull=False).distinct()

        if val == "no":
            return queryset.filter(conditions__isnull=True)

        return queryset


class HasFilesFilter(admin.SimpleListFilter):
    title = "Файлы"
    parameter_name = "has_files"

    def lookups(self, request, model_admin):
        return (
            ("yes", "Есть файлы"),
            ("no", "Нет файлов"),
        )

    def queryset(self, request, queryset):
        val = self.value()
        if val == "yes":
            return queryset.filter(files__isnull=False).distinct()
        if val == "no":
            return queryset.filter(files__isnull=True)
        return queryset


class AccountingMethodFilter(admin.SimpleListFilter):
    title = "Метод учёта"
    parameter_name = "acc_method"

    def lookups(self, request, model_admin):
        qs = AccountingMethod.objects.filter(is_active=True).order_by("name")
        return [(str(x.pk), f"{x.icon or ''} {x.name}".strip()) for x in qs]

    def queryset(self, request, queryset):
        val = self.value()
        if not val:
            return queryset
        return queryset.filter(conditions__accounting_method_id=val).distinct()


class PayTimingFilter(admin.SimpleListFilter):
    title = "Тип оплаты"
    parameter_name = "pay_timing"

    def lookups(self, request, model_admin):
        return [("prepay", "Предоплата"), ("postpay", "Постоплата")]

    def queryset(self, request, queryset):
        val = self.value()
        if not val:
            return queryset
        return queryset.filter(conditions__pay_timing=val).distinct()


def build_params_template(fn: str) -> dict:
    schema = ACCRUAL_REGISTRY.get(fn) or {}
    defaults = schema.get("defaults") or {}
    fields = schema.get("fields") or []

    tmpl = {}
    for f in fields:
        key = f.get("key")
        if key:
            tmpl[key] = defaults.get(key, "")

    # добавим defaults, которых нет в fields
    for k, v in defaults.items():
        tmpl.setdefault(k, v)

    return tmpl


class ConditionsInlineForm(forms.ModelForm):
    params_editor = forms.CharField(
        label="Параметры начисления (JSON)",
        required=False,
        widget=forms.Textarea(
            attrs={
                "rows": 7,
                "style": "width: 95%; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;",
                "placeholder": '{\n  "amount": "",\n  "vat_mode": "included"\n}',
            }
        ),
        help_text="Заполняется по выбранной функции начисления.",
    )

    class Meta:
        model = Conditions
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # params храним скрыто, редактируем через params_editor
        self.fields["params"].widget = forms.HiddenInput()
        self.fields["params"].required = False

        inst = getattr(self, "instance", None)
        params = (inst.params or {}) if inst else {}

        # показываем текущие params
        if params:
            self.initial["params_editor"] = json.dumps(
                params, ensure_ascii=False, indent=2, default=str
            )
        else:
            self.initial["params_editor"] = ""

        # ✅ КЛЮЧЕВОЕ: если форма уже отправлена (POST) и params_editor пустой —
        # подставим шаблон по выбранной функции, чтобы он был виден даже при ошибке сохранения
        if self.is_bound:
            pe_key = self.add_prefix("params_editor")
            fn_key = self.add_prefix("accrual_fn")

            current = (self.data.get(pe_key) or "").strip()
            if current == "":
                fn = (self.data.get(fn_key) or "").strip() or "fixed_payments"
                tmpl = build_params_template(fn)

                qd = self.data.copy()  # QueryDict -> mutable copy
                qd[pe_key] = json.dumps(tmpl, ensure_ascii=False, indent=2, default=str)
                self.data = qd

    def clean(self):
        cleaned = super().clean()
        raw = (cleaned.get("params_editor") or "").strip()

        # 1) если JSON ввели руками — парсим
        if raw:
            try:
                parsed = json.loads(raw)
            except Exception as e:
                raise forms.ValidationError(
                    {"params_editor": f"Некорректный JSON: {e}"}
                )
            if not isinstance(parsed, dict):
                raise forms.ValidationError(
                    {"params_editor": "JSON должен быть объектом { ... }"}
                )
            cleaned["params"] = parsed

        # 2) если JSON пустой — генерим шаблон по accrual_fn
        else:
            fn = (
                cleaned.get("accrual_fn")
                or getattr(self.instance, "accrual_fn", None)
                or "fixed_payments"
            )
            cleaned["params"] = build_params_template(fn)

        # 3) CASH BASED: принудительно ставим функцию, НО params не затираем
        acc = cleaned.get("accounting_method")
        if acc:
            name = (acc.name or "").lower()
            code = (getattr(acc, "code", "") or "").lower()

            if "cash" in name or "cash" in code:
                cleaned["accrual_fn"] = "by_bank_statement"

                params = cleaned.get("params") or {}
                if not isinstance(params, dict):
                    params = {}

                params.setdefault("vat_rate", "0")
                cleaned["params"] = params

        return cleaned

    def save(self, commit=True):
        inst = super().save(commit=False)
        inst.params = self.cleaned_data.get("params") or {}
        if commit:
            inst.save()
            self.save_m2m()
        return inst


class CfItemAutoInline(admin.StackedInline):
    model = CfItemAuto
    extra = 0
    fields = ("regex", "defaultcfdt", "defaultcfcr")
    # template = "admin/contracts/inlines/cfitemauto_stacked_inline.html"  # <-- УБРАТЬ
    verbose_name = mark_safe("⚙️ <b>Автоматизация</b>")
    verbose_name_plural = mark_safe("⚙️ <b>Автоматизация</b>")


class ContractItemsInlineForm(forms.ModelForm):
    class Meta:
        model = ContractItems
        fields = "__all__"
        widgets = {
            "item": forms.Textarea(attrs={"rows": 2, "style": "width: 70%;"}),
        }


class ContractItemsInline(admin.StackedInline):
    model = ContractItems
    form = ContractItemsInlineForm
    extra = 0
    fields = ("item",)
    verbose_name = mark_safe("<b>🧾 Предмет</b>")
    verbose_name_plural = mark_safe("🧾 <b>Предмет</b>")


class ConditionsInline(admin.StackedInline):
    model = Conditions
    form = ConditionsInlineForm
    extra = 0
    show_change_link = True
    formfield_overrides = {models.JSONField: {"widget": JSONEditor}}
    # autocomplete_fields = ("accounting_method", "tax")
    template = "admin/contracts/inlines/conditions_stacked_inline.html"

    fieldsets = (
        (
            "Начисление",
            {
                "fields": (
                    "accounting_method",
                    "accrual_fn",
                    "date_start",
                    "date_finish",
                    "vat_mode",
                    "params_editor",
                )
            },
        ),
        (
            "Оплата",
            {
                "fields": (
                    ("pay_rule", "pay_timing"),
                    ("pay_day", "pay_offset_months"),
                )
            },
        ),
        ("Неустойка", {"fields": ("penalty_rate_day",)}),
        ("Доп. параметры", {"classes": ("collapse",), "fields": ("params",)}),
        (
            "Новые поля. параметры",
            {
                "classes": ("collapse",),
                "fields": (
                    "fn",
                    "param_json",
                    "vat_json",
                    "acc_bs",
                    "subconto_bs",
                    "acc_pl",
                ),
            },
        ),
    )
    verbose_name = mark_safe("<b>✅ Условие</b>")
    verbose_name_plural = mark_safe("✅<b>Условия</b>")

    class Meta:
        model = Conditions
        fields = "__all__"
        widgets = {
            "param_json": JSONEditor,
            "vat_json": JSONEditor,
        }


class ContractFilesInline(admin.StackedInline):
    model = ContractFiles
    extra = 0
    show_change_link = True
    template = "admin/contracts/inlines/contractfiles_stacked_inline.html"

    verbose_name = mark_safe("<b>📎 Файл</b>")
    verbose_name_plural = mark_safe("<b>📎 Файлы</b>")

    fields = (
        "doc_type",
        "doc_date",
        "doc_number",
        "amount",
        "document",
        "file",
    )
    readonly_fields = ("document",)

    def document(self, obj):
        if not obj or not obj.file:
            return "—"
        name = os.path.basename(obj.file.name)
        return format_html(
            '<a href="{}" target="_blank" style="font-weight:800;">📄 {}</a>',
            obj.file.url,
            name,
        )

    document.short_description = "Текущий документ"


@admin.register(Contracts)
class ContractsAdmin(admin.ModelAdmin):
    inlines = (
        ContractFilesInline,
        ContractItemsInline,
        ConditionsInline,
        CfItemAutoInline,
    )

    list_display = (
        "cp_logo",
        "cp_with_inn",
        "title",
        "number_with_id",
        "date_short",
        "files_badge",
        "method_icon",
        "contract_end_date",
        # "amendment",
        "payment_type",
        "reconciliation_button",
        "cf_defaults",
    )
    list_display_links = (
        "cp_with_inn",
        "number_with_id",
    )
    list_select_related = (
        "title",
        "cp",
        "cp__gr",
        "owner",
        "manager",
        "pid",
    )

    search_fields = ("number", "cp__name", "title__title", "regex")
    search_help_text = "Поиск: номер, контрагент, тип, RegEx"

    list_filter = (
        ("cp", RelatedOnlyFieldListFilter),
        "title",
        "owner",
        #    "is_signed",
        HasFilesFilter,
        AccountingMethodFilter,
        PayTimingFilter,
        HasAccrualFunctionFilter,
    )
    date_hierarchy = "date"
    ordering = ("cp__name", "-date", "number")
    preserve_filters = True
    autocomplete_fields = (
        "title",
        "cp",
        "manager",
    )

    list_per_page = 25

    change_list_template = "admin/contracts/contracts/change_list.html"
    change_form_template = "admin/contracts/contracts/change_form.html"

    fieldsets = (
        (
            mark_safe("📄 <b>Карточка</b>"),
            {
                "fields": (
                    "title",
                    "number",
                    "date",
                    "cp",
                    "owner",
                    "currency",
                    "manager",
                    "is_signed",
                    "regex",
                    
                )
            },
        ),
        (
            mark_safe("📄 <b>Распределения</b>"),
            {"fields":(
                "bs",
                "st",
                "subconto_bs",
                "pl",
                "subconto_pl")
                
            }
        ),
        (
            mark_safe("🔗 <b>Связи</b>"),
            {
                "fields": ("pid",),
                "classes": ("collapse",),
            },
        ),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        qs = (
            qs.select_related("title", "cp", "cp__gr", "owner", "manager", "pid")
            .annotate(
                _files_count=Count("files", distinct=True),
                _amendments_count=Count("amendments", distinct=True),
            )
            .prefetch_related(
                Prefetch(
                    "cfitemauto_set",
                    queryset=CfItemAuto.objects.select_related(
                        "defaultcfdt", "defaultcfcr"
                    ),
                    to_attr="_cf_auto",
                ),
                "conditions",
                "conditions__accounting_method",
            )
        )

        return qs

    # def condition_accruals_preview(self, request, condition_id: int):
    #     cond = get_object_or_404(
    #         Conditions.objects.select_related("contract", "accounting_method"),
    #         pk=condition_id
    #     )

    #     result = preview_accruals(cond, anchor_date=date.today())

    #     context = {
    #         "condition": cond,
    #         "contract": cond.contract,
    #         "result": result,
    #         "rows": result.get("rows", []) or [],
    #         "total": result.get("total"),
    #     }

    #     return TemplateResponse(request, "contracts/accruals_print.html", context)

    @admin.display(description="Файлы", ordering="_files_count")
    def files_badge(self, obj):
        n = getattr(obj, "_files_count", 0) or 0

        if n == 0:
            return format_html('<span style="color:#94a3b8;">—</span>')

        return format_html(
            '<span style="display:inline-flex;align-items:center;gap:4px;'
            "padding:3px 8px;border-radius:2px;"
            "background:rgba(14,165,233,.12);"
            'color:#075985;font-weight:800;">'
            "📎 {}"
            "</span>",
            n,
        )

    @admin.display(description="Метод")
    def method_icon(self, obj):
        cond = get_current_condition(obj)
        m = getattr(cond, "accounting_method", None) if cond else None
        if not m:
            return "—"
        icon = (m.icon or "").strip() or "🧩"
        return format_html(
            '<span style="font-size:18px; line-height:1;">{}</span>', icon
        )

    @admin.display(description="Окончание")
    def contract_end_date(self, obj):
        cond = get_current_condition(obj)
        if not cond:
            return "—"
        if not cond.date_finish:
            return format_html('<span style="color:#94a3b8;">∞</span>')
        return cond.date_finish.strftime("%d.%m.%Y")

    @admin.display(description="Оплата")
    def payment_type(self, obj):
        cond = get_current_condition(obj)
        if not cond:
            return "—"
        return "Предоплата" if cond.pay_timing == "prepay" else "Постоплата"

    @admin.display(description="№ договора", ordering="number")
    def number_with_id(self, obj):
        number = obj.number or "без номера"
        return format_html(
            '{}<br><span style="font-size:11px; color:#94a3b8;">id: {}</span>',
            number,
            obj.id,
        )

    @admin.display(description="Контрагент", ordering="cp__name")
    def cp_with_inn(self, obj):
        cp = obj.cp
        if not cp:
            return "—"

        return format_html(
            '{}<br><span style="font-size:11px; line-height:1.2; color:#94a3b8;">ИНН: {}</span>',
            cp.name,
            cp.tax_id,
        )

    @admin.display(description="Дата", ordering="date")
    def date_short(self, obj):
        if not obj.date:
            return "—"

        months = {
            1: "янв",
            2: "фев",
            3: "мар",
            4: "апр",
            5: "май",
            6: "июн",
            7: "июл",
            8: "авг",
            9: "сент",
            10: "окт",
            11: "ноя",
            12: "дек",
        }

        d = obj.date
        return f"{d.day} {months[d.month]} {d.year}"

    @admin.display(description="CF по умолч.", ordering=None)
    def cf_defaults(self, obj):
        # берём первую запись автоматизации (обычно она одна на договор)
        auto = getattr(obj, "_cf_auto", None) or []
        auto = auto[0] if auto else None

        dt = getattr(auto, "defaultcfdt", None) if auto else None
        cr = getattr(auto, "defaultcfcr", None) if auto else None

        dt_txt = str(dt) if dt else "—"
        cr_txt = str(cr) if cr else "—"

        # маленький светло-серый текст, две строки
        return format_html(
            '<div style="font-size:11px; line-height:1.25; color:#94a3b8;">'
            '<div><span style="font-weight:700; color:#cbd5e1;">Дт:</span> {}</div>'
            '<div><span style="font-weight:700; color:#cbd5e1;">Кт:</span> {}</div>'
            "</div>",
            dt_txt,
            cr_txt,
        )

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        field = super().formfield_for_foreignkey(db_field, request, **kwargs)

        if db_field.name == "pid":
            obj_id = request.resolver_match.kwargs.get("object_id")
            if obj_id:
                try:
                    obj = Contracts.objects.select_related("cp").get(pk=obj_id)
                    field.queryset = Contracts.objects.filter(cp=obj.cp).order_by(
                        "-date"
                    )
                    # если хочешь выбирать только “основные” договоры:
                    # field.queryset = field.queryset.filter(pid__isnull=True)
                except Contracts.DoesNotExist:
                    field.queryset = Contracts.objects.none()
            else:
                # форма создания: пока cp не выбран — скрываем варианты
                field.queryset = Contracts.objects.none()

        return field

    @admin.display(description="Лого")
    def cp_logo(self, obj):
        cp = getattr(obj, "cp", None)
        if not cp:
            return "—"

        # 1) приоритет: лого контрагента, 2) fallback: лого группы
        glyph = (cp.logo or "").strip() or (getattr(cp.gr, "logo", "") or "").strip()
        if not glyph:
            return "—"

        outer = (
            "display:inline-flex;align-items:center;justify-content:center;"
            "width:28px;height:28px;border-radius:6px;"
            "background:linear-gradient(135deg,#f8fafc,#f1f5f9);"
            "box-shadow:0 0 0 1px rgba(148,163,184,.35);"
        )
        inner = "font-family:NotoManu;font-size:20px;line-height:1;"

        return format_html(
            '<span style="{}"><span style="{}">{}</span></span>', outer, inner, glyph
        )

    @admin.display(description="Доп.согл.", ordering="_amendments_count")
    def amendment(self, obj):
        # если текущая запись — допник
        if obj.pid_id:
            return format_html(
                '<span style="display:inline-flex;align-items:center;justify-content:center;'
                "padding:4px 10px;border-radius:999px;"
                "font-size:11px;font-weight:900;"
                "background:rgba(148,163,184,.16);color:#475569;"
                'border:1px solid rgba(148,163,184,.28);">доп.согл.</span>'
            )

        n = getattr(obj, "_amendments_count", 0) or 0
        if not n:
            return "—"

        return format_html(
            '<span style="display:inline-flex;align-items:center;justify-content:center;'
            "min-width:34px;padding:4px 10px;border-radius:999px;"
            "font-size:11px;font-weight:900;"
            "background:rgba(14,165,233,.10);color:#075985;"
            'border:1px solid rgba(14,165,233,.18);">+{} док.</span>',
            n,
        )

    @admin.display(description="Файлы", ordering="_files_count")
    def files_count(self, obj):
        return getattr(obj, "_files_count", 0) or 0

    @admin.display(description="Сверка")
    def reconciliation_button(self, obj):
        url = reverse("contracts:contract_reconciliation_preview", args=[obj.id])

        return format_html(
            '<a href="{}" target="_blank" '
            'style="display:inline-flex;align-items:center;justify-content:center;'
            "padding:5px 10px;border-radius:2px;"
            "background:rgba(37,99,235,.10);"
            "color:#1d4ed8;font-weight:800;text-decoration:none;"
            'border:1px solid rgba(37,99,235,.18);">📘</a>',
            url,
        )

    def render_change_form(
        self, request, context, add=False, change=False, form_url="", obj=None
    ):
        context["accrual_registry_json"] = json.dumps(
            ACCRUAL_REGISTRY, ensure_ascii=False, default=str
        )
        return super().render_change_form(request, context, add, change, form_url, obj)

    class Media:
        css = {
            "all": (
                "fonts/glyphs.css",
                "css/admin_overrides.css",
            )
        }
        js = ("js/conditions_inline_collapse.js",)


@admin.register(AccuralFn)
class AccuralFnAdmin(admin.ModelAdmin):
    list_display = ("name", "accounting_method", "description")
    formfield_overrides = {models.JSONField: {"widget": JSONEditor}}

    class Media:
        css = {
            "all": (
                "fonts/glyphs.css",
                "css/admin_overrides.css",
            )
        }


@admin.register(ContractsTitle)
class ContractsTitleAdmin(admin.ModelAdmin):
    change_list_template = "admin/contracts/contractstitle/change_list.html"
    change_form_template = "admin/contracts/contractstitle/change_form.html"

    list_display = ("title", "contracts_badge")
    search_fields = ("title",)
    ordering = ("title",)
    preserve_filters = True

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(_contracts_count=Count("contracts", distinct=True))

    @admin.display(description="Договоров", ordering="_contracts_count")
    def contracts_badge(self, obj):
        n = getattr(obj, "_contracts_count", 0) or 0
        if n == 0:
            return admin.utils.format_html(
                '<span style="display:inline-flex;align-items:center;justify-content:center;'
                "min-width:34px;padding:4px 10px;border-radius:6px;"
                "font-size:12px;font-weight:800;"
                "background:rgba(148,163,184,.16);color:#475569;"
                'border:1px solid rgba(148,163,184,.28);">0</span>'
            )
        return admin.utils.format_html(
            '<span style="display:inline-flex;align-items:center;justify-content:center;'
            "min-width:34px;padding:4px 10px;border-radius:6px;"
            "font-size:12px;font-weight:800;"
            "background:rgba(29,78,216,.10);color:#1e3a8a;"
            'border:1px solid rgba(29,78,216,.18);">{}</span>',
            n,
        )

    class Media:
        css = {
            "all": (
                "fonts/glyphs.css",
                "css/admin_overrides.css",
            )
        }


@admin.register(AccountingMethod)
class AccountingMethodAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "icon")
    list_filter = ("is_active",)
    search_fields = ("name",)
    ordering = ("name",)
    list_per_page = 50

    fields = ("name", "icon", "is_active")
