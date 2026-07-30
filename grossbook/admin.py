# grossbook/admin.py
from __future__ import annotations

from decimal import Decimal

from django.contrib import admin, messages
from django.contrib.admin import RelatedOnlyFieldListFilter, SimpleListFilter
from django.db.models import (
    Count,
    Q,
    DecimalField,
    IntegerField,
    OuterRef,
    Subquery,
    Sum,
)
from django.http import Http404
from django.urls import path, reverse
from django.utils.html import format_html
from django.utils.http import urlencode

from .models import LoanAdjustment, Manual
from .reporting.loan_adjustment_pdf import (
    generate_loan_adjustment_pdf,
    generate_loan_adjustments_registry_pdf,
)


class GroupedEntriesFilter(SimpleListFilter):
    title = "Групповые проводки"
    parameter_name = "grouped"

    def lookups(self, request, model_admin):
        return (
            ("yes", "Только группы"),
            ("no", "Только одиночные"),
        )

    def queryset(self, request, queryset):
        duplicate_subquery = (
            Manual.objects.filter(
                contract_id=OuterRef("contract_id"),
                date=OuterRef("date"),
            )
            .values("contract_id", "date")
            .annotate(cnt=Count("id"))
            .values("cnt")[:1]
        )

        queryset = queryset.annotate(
            same_contract_date_count=Subquery(
                duplicate_subquery,
                output_field=IntegerField(),
            )
        )

        if self.value() == "yes":
            return queryset.filter(same_contract_date_count__gt=1)
        if self.value() == "no":
            return queryset.filter(same_contract_date_count=1)

        return queryset


@admin.register(Manual)
class ManualAdmin(admin.ModelAdmin):
    change_list_template = "admin/grossbook/manual/change_list.html"
    change_form_template = "admin/grossbook/manual/change_form.html"

    actions = ["duplicate_entries"]

    list_display = (
        "id_col",
        "date_col",
        "contract_col",
        "acc_col",
        "amount_dt",
        "amount_cr",
        "cfitem_col",
        "comment_short",
    )

    list_display_links = ("date_col", "contract_col")

    search_fields = (
        "id",
        "temp",
        "contract__number",
        "contract__cp__name",
        "acc__name",
        "acc__number",
    )

    list_filter = (
        GroupedEntriesFilter,
        ("owner", RelatedOnlyFieldListFilter),
        ("contract", RelatedOnlyFieldListFilter),
        ("acc", RelatedOnlyFieldListFilter),
        "date",
    )

    list_per_page = 25
    date_hierarchy = "date"
    ordering = ("-date", "-contract_id", "-id")
    preserve_filters = True

    autocomplete_fields = ("owner", "acc", "contract", "cfitem", "pid")

    fieldsets = (
        (
            "Основные данные",
            {
                "fields": (
                    "date",
                    "currency",
                    "owner",
                    "contract",
                    "acc",
                    "cfitem",
                    ("dt", "cr"),
                    "temp",
                )
            },
        ),
        (
            "Связь",
            {
                "fields": ("pid",),
                "classes": ("collapse",),
            },
        ),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related(
            "owner",
            "contract",
            "contract__cp",
            "acc",
            "cfitem",
            "pid",
        )

        duplicate_subquery = (
            Manual.objects.filter(
                contract_id=OuterRef("contract_id"),
                date=OuterRef("date"),
            )
            .values("contract_id", "date")
            .annotate(cnt=Count("id"))
            .values("cnt")[:1]
        )

        return qs.annotate(
            same_contract_date_count=Subquery(
                duplicate_subquery,
                output_field=IntegerField(),
            )
        )

    @admin.action(description="Скопировать выбранные проводки")
    def duplicate_entries(self, request, queryset):
        created_count = 0

        for obj in queryset:
            Manual.objects.create(
                pid=obj.pid,
                date=obj.date,
                owner=obj.owner,
                acc=obj.acc,
                contract=obj.contract,
                dt=obj.dt,
                cr=obj.cr,
                currency=obj.currency,
                cfitem=obj.cfitem,
                temp=obj.temp,
            )
            created_count += 1

        self.message_user(
            request,
            f"Скопировано проводок: {created_count}",
            level=messages.SUCCESS,
        )

    @admin.display(description="ID", ordering="id")
    def id_col(self, obj):
        return format_html(
            '<span style="color:#9ca3af;font-size:12px;font-weight:500;">#{}</span>',
            obj.id,
        )

    @admin.display(description="Дата", ordering="date")
    def date_col(self, obj):
        if not obj.date:
            return "—"
        return format_html(
            '<div style="font-weight:700;color:#111827;font-size:13px;">{}</div>',
            obj.date.strftime("%d.%m.%Y"),
        )

    @admin.display(description="CF статья", ordering="cfitem__name")
    def cfitem_col(self, obj):
        if not obj.cfitem:
            return "—"
        return format_html(
            '<span style="color:#1f2937;font-weight:500;">{}</span>',
            obj.cfitem,
        )

    @admin.display(description="Договор", ordering="contract__number")
    def contract_col(self, obj):
        if not obj.contract:
            return "—"

        contract_number = obj.contract.number or "без номера"
        contract_id = obj.contract.id
        cp_name = getattr(obj.contract.cp, "name", "—")
        group_count = getattr(obj, "same_contract_date_count", 1)
        group_key = f"{obj.date.isoformat()}__{contract_id}"

        return format_html(
            (
                '<div class="manual-contract-cell" data-group-key="{}" '
                'data-group-count="{}" data-contract-id="{}">'
                '<div style="font-weight:700;color:#111827;line-height:1.2;">{}</div>'
                '<div style="font-size:12px;color:#374151;line-height:1.2;margin-top:4px;">'
                'Договор: {}</div>'
                '<div style="font-size:11px;color:#6b7280;line-height:1.2;margin-top:2px;">'
                'ID: {}</div></div>'
            ),
            group_key,
            group_count,
            contract_id,
            cp_name,
            contract_number,
            contract_id,
        )

    @admin.display(description="Счёт", ordering="acc__name")
    def acc_col(self, obj):
        return obj.acc or "—"

    @admin.display(description="Дт", ordering="dt")
    def amount_dt(self, obj):
        return format_html(
            '<span style="font-weight:600;color:#166534;">{}</span>',
            f"{(obj.dt or 0):,.2f}",
        )

    @admin.display(description="Кт", ordering="cr")
    def amount_cr(self, obj):
        return format_html(
            '<span style="font-weight:600;color:#991b1b;">{}</span>',
            f"{(obj.cr or 0):,.2f}",
        )

    @admin.display(description="Комментарий", ordering="temp")
    def comment_short(self, obj):
        if not obj.temp:
            return format_html('<span style="color:#9ca3af;">—</span>')
        text = obj.temp.strip()
        return text[:60] + "…" if len(text) > 60 else text

    class Media:
        css = {
            "all": (
                "css/admin_overrides.css",
                "css/wide-table.css",
                "css/manual_admin_groups.css",
            )
        }
        js = ("js/manual_admin_groups.js",)


@admin.register(LoanAdjustment)
class LoanAdjustmentAdmin(admin.ModelAdmin):
    change_list_template = (
        "admin/grossbook/loanadjustment/change_list.html"
    )

    change_form_template = (
        "admin/grossbook/loanadjustment/change_form.html"
    )

    actions = (
        "activate_adjustments",
        "deactivate_adjustments",
        "export_selected_pdf",
    )

    list_display = (
        "document_col",
        "adjustment_date_col",
        "contract_col",
        "principal_balance_col",
        "interest_balance_col",
        "total_balance_col",
        "reason_col",
        "pdf_col",
    )

    list_display_links = (
        "document_col",
        "adjustment_date_col",
        "contract_col",
    )

    list_filter = (
        "is_active",
        "reason",
        "adjustment_date",
        (
            "contract",
            RelatedOnlyFieldListFilter,
        ),
        (
            "created_by",
            RelatedOnlyFieldListFilter,
        ),
    )

    search_fields = (
        "=id",
        "contract__number",
        "contract__cp__name",
        "comment",
        "created_by__username",
        "created_by__first_name",
        "created_by__last_name",
    )

    autocomplete_fields = (
        "contract",
    )

    readonly_fields = (
        "created_by",
        "created_at",
        "updated_at",
        "pdf_preview",
    )

    ordering = (
        "-adjustment_date",
        "-id",
    )

    list_per_page = 30
    date_hierarchy = "adjustment_date"
    preserve_filters = True
    save_on_top = True
    empty_value_display = "—"

    fieldsets = (
        (
            "Контрольная точка займа",
            {
                "fields": (
                    "contract",
                    "adjustment_date",
                    "is_active",
                ),
                "description": (
                    "Корректировка устанавливает фактический "
                    "остаток займа на конец выбранного дня."
                ),
            },
        ),
        (
            "Остаток задолженности после корректировки",
            {
                "fields": (
                    (
                        "principal_balance",
                        "interest_balance",
                    ),
                ),
                "description": (
                    "Суммы вводятся в валюте договора, "
                    "не в копейках."
                ),
            },
        ),
        (
            "Основание корректировки",
            {
                "fields": (
                    "reason",
                    "comment",
                ),
            },
        ),
        (
            "Документ",
            {
                "fields": (
                    "pdf_preview",
                ),
            },
        ),
        (
            "Аудит",
            {
                "fields": (
                    "created_by",
                    "created_at",
                    "updated_at",
                ),
                "classes": (
                    "collapse",
                ),
            },
        ),
    )

    def get_queryset(
        self,
        request,
    ):
        return (
            super()
            .get_queryset(request)
            .select_related(
                "contract",
                "contract__cp",
                "created_by",
            )
        )

    def get_urls(self):
        urls = super().get_urls()

        custom_urls = [
            path(
                "<int:object_id>/pdf/",
                self.admin_site.admin_view(
                    self.pdf_view
                ),
                name="grossbook_loanadjustment_pdf",
            ),
        ]

        return custom_urls + urls

    def pdf_view(
        self,
        request,
        object_id,
    ):
        adjustment = self.get_object(
            request,
            object_id,
        )

        if adjustment is None:
            raise Http404(
                "Корректировка займа не найдена."
            )

        return generate_loan_adjustment_pdf(
            adjustment
        )

    def save_model(
        self,
        request,
        obj,
        form,
        change,
    ):
        if not obj.created_by_id:
            obj.created_by = request.user

        super().save_model(
            request,
            obj,
            form,
            change,
        )
    
    
    class Media:
            css = {
                "all": (
                    "css/admin_overrides.css",
                    "css/wide-table.css",
                    "css/manual_admin_groups.css",
                )
            }
            js = ("js/manual_admin_groups.js",)

    # ================================================================
    # ADMIN ACTIONS
    # ================================================================

    @admin.action(
        description="Включить выбранные корректировки"
    )
    def activate_adjustments(
        self,
        request,
        queryset,
    ):
        updated = queryset.update(
            is_active=True
        )

        self.message_user(
            request,
            f"Включено корректировок: {updated}.",
            level=messages.SUCCESS,
        )

    @admin.action(
        description="Отключить выбранные корректировки"
    )
    def deactivate_adjustments(
        self,
        request,
        queryset,
    ):
        updated = queryset.update(
            is_active=False
        )

        self.message_user(
            request,
            f"Отключено корректировок: {updated}.",
            level=messages.WARNING,
        )

    @admin.action(
        description="Печать справки по выбранным корректировкам"
    )
    def export_selected_pdf(
        self,
        request,
        queryset,
    ):
        queryset = queryset.select_related(
            "contract",
            "contract__cp",
            "created_by",
        )

        return generate_loan_adjustments_registry_pdf(
            queryset
        )

    # ================================================================
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # ================================================================

    @staticmethod
    def _money(
        value,
    ):
        value = value or Decimal("0")

        return (
            f"{value:,.2f}"
            .replace(
                ",",
                " ",
            )
        )

    @staticmethod
    def _counterparty_name(
        contract,
    ):
        counterparty = getattr(
            contract,
            "cp",
            None,
        )

        if counterparty is None:
            return str(contract)

        return (
            getattr(
                counterparty,
                "name",
                None,
            )
            or str(counterparty)
        )

    # ================================================================
    # КОЛОНКИ
    # ================================================================

    @admin.display(
        description="Документ",
        ordering="id",
    )
    def document_col(
        self,
        obj,
    ):
        document_number = (
            f"КЗ-{obj.id:06d}"
        )

        return format_html(
            (
                '<div class="loan-adj-doc">'
                '<div class="loan-adj-doc-number">'
                "{}"
                "</div>"
                '<div class="loan-adj-doc-id">'
                "ID: {}"
                "</div>"
                "</div>"
            ),
            document_number,
            obj.id,
        )

    @admin.display(
        description="Дата",
        ordering="adjustment_date",
    )
    def adjustment_date_col(
        self,
        obj,
    ):
        return format_html(
            (
                '<div class="loan-adj-date">'
                "{}"
                "</div>"
                '<div class="loan-adj-date-note">'
                "на конец дня"
                "</div>"
            ),
            obj.adjustment_date.strftime(
                "%d.%m.%Y"
            ),
        )

    @admin.display(
        description="Договор",
        ordering="contract__number",
    )
    def contract_col(
        self,
        obj,
    ):
        contract = obj.contract

        contract_number = (
            getattr(
                contract,
                "number",
                None,
            )
            or "б/н"
        )

        counterparty_name = (
            self._counterparty_name(
                contract
            )
        )

        return format_html(
            (
                '<div class="loan-adj-contract">'
                '<div class="loan-adj-counterparty">'
                "{}"
                "</div>"
                '<div class="loan-adj-contract-meta">'
                "Договор № {} · ID {}"
                "</div>"
                "</div>"
            ),
            counterparty_name,
            contract_number,
            contract.pk,
        )

    @admin.display(
        description="Тело",
        ordering="principal_balance",
    )
    def principal_balance_col(
        self,
        obj,
    ):
        return format_html(
            (
                '<span class="loan-adj-money '
                'loan-adj-principal">'
                "{}"
                "</span>"
            ),
            self._money(
                obj.principal_balance
            ),
        )

    @admin.display(
        description="Проценты",
        ordering="interest_balance",
    )
    def interest_balance_col(
        self,
        obj,
    ):
        return format_html(
            (
                '<span class="loan-adj-money '
                'loan-adj-interest">'
                "{}"
                "</span>"
            ),
            self._money(
                obj.interest_balance
            ),
        )

    @admin.display(
        description="Общий долг"
    )
    def total_balance_col(
        self,
        obj,
    ):
        total = (
            (
                obj.principal_balance
                or Decimal("0")
            )
            + (
                obj.interest_balance
                or Decimal("0")
            )
        )

        return format_html(
            (
                '<span class="loan-adj-money '
                'loan-adj-total">'
                "{}"
                "</span>"
            ),
            self._money(
                total
            ),
        )

    @admin.display(
        description="Причина",
        ordering="reason",
    )
    def reason_col(
        self,
        obj,
    ):
        comment = (
            obj.comment
            or ""
        ).strip()

        short_comment = (
            comment[:90] + "…"
            if len(comment) > 90
            else comment
        )

        return format_html(
            (
                '<div class="loan-adj-reason">'
                "{}"
                "</div>"
                '<div class="loan-adj-comment" '
                'title="{}">'
                "{}"
                "</div>"
            ),
            obj.get_reason_display(),
            comment,
            short_comment or "—",
        )

    
    @admin.display(
        description="Автор",
        ordering="created_by",
    )
    def author_col(
        self,
        obj,
    ):
        if not obj.created_by:
            return "—"

        full_name = (
            obj.created_by
            .get_full_name()
            .strip()
        )

        return (
            full_name
            or obj.created_by.get_username()
        )

    @admin.display(
        description="PDF"
    )
    def pdf_col(
        self,
        obj,
    ):
        url = reverse(
            "admin:grossbook_loanadjustment_pdf",
            args=(
                obj.pk,
            ),
        )

        return format_html(
            (
                '<a href="{}" '
                'class="loan-adj-pdf-button" '
                'target="_blank" '
                'title="Открыть справку PDF">'
                '<span aria-hidden="true">🖨</span>'
                "<span>PDF</span>"
                "</a>"
            ),
            url,
        )

    @admin.display(
        description="Документ PDF"
    )
    def pdf_preview(
        self,
        obj,
    ):
        if not obj or not obj.pk:
            return format_html(
                (
                    '<span style="color:#94a3b8;">'
                    "PDF станет доступен "
                    "после сохранения корректировки."
                    "</span>"
                )
            )

        url = reverse(
            "admin:grossbook_loanadjustment_pdf",
            args=(
                obj.pk,
            ),
        )

        return format_html(
            (
                '<a href="{}" '
                'class="loan-adj-form-pdf" '
                'target="_blank">'
                '<span class="loan-adj-form-pdf-icon">'
                "PDF"
                "</span>"
                "<span>"
                "<strong>"
                "Сформировать справку"
                "</strong>"
                "<small>"
                "Открыть профессиональный PDF-документ"
                "</small>"
                "</span>"
                "</a>"
            ),
            url,
        )