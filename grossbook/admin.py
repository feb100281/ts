# grossbook/admin.py
from django.contrib import admin, messages
from django.contrib.admin import RelatedOnlyFieldListFilter, SimpleListFilter
from django.db.models import Count, OuterRef, Subquery, IntegerField
from django.utils.html import format_html

from .models import Manual


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
                    "date", "currency",
                    "owner", "contract",
                    "acc", "cfitem",
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
            level=messages.SUCCESS
        )

    @admin.display(description="ID", ordering="id")
    def id_col(self, obj):
        return format_html(
            '<span style="color:#9ca3af; font-size:12px; font-weight:500;">#{}</span>',
            obj.id,
        )

    @admin.display(description="Дата", ordering="date")
    def date_col(self, obj):
        if not obj.date:
            return "—"

        return format_html(
            '<div style="font-weight:700; color:#111827; font-size:13px;">{}</div>',
            obj.date.strftime("%d.%m.%Y"),
        )

    @admin.display(description="Компания", ordering="owner__name")
    def owner_col(self, obj):
        if not obj.owner:
            return "—"

        return format_html(
            '<span style="font-weight:600; color:#111827;">{}</span>',
            obj.owner,
        )
        
    @admin.display(description="CF статья", ordering="cfitem__name")
    def cfitem_col(self, obj):
        if not obj.cfitem:
            return "—"

        return format_html(
            '<span style="color:#1f2937; font-weight:500;">{}</span>',
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

        # ключ группы: только дата + договор
        # именно это и нужно по бизнес-логике
        group_key = f"{obj.date.isoformat()}__{contract_id}"

        return format_html(
            (
                '<div class="manual-contract-cell" '
                'data-group-key="{}" '
                'data-group-count="{}" '
                'data-contract-id="{}">'
                '<div style="font-weight:700; color:#111827; line-height:1.2;">{}</div>'
                '<div style="font-size:12px; color:#374151; line-height:1.2; margin-top:4px;">'
                'Договор: {}'
                '</div>'
                '<div style="font-size:11px; color:#6b7280; line-height:1.2; margin-top:2px;">'
                'ID: {}'
                '</div>'
                '</div>'
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
        if not obj.acc:
            return "—"

        return format_html(
            '<span style="color:#111827;">{}</span>',
            obj.acc,
        )

    @admin.display(description="Дт", ordering="dt")
    def amount_dt(self, obj):
        value = f"{(obj.dt or 0):,.2f}"
        return format_html(
            '<span style="font-weight:600; color:#166534;">{}</span>',
            value,
        )

    @admin.display(description="Кт", ordering="cr")
    def amount_cr(self, obj):
        value = f"{(obj.cr or 0):,.2f}"
        return format_html(
            '<span style="font-weight:600; color:#991b1b;">{}</span>',
            value,
        )

    @admin.display(description="Сальдо")
    def balance_col(self, obj):
        value = (obj.dt or 0) - (obj.cr or 0)

        if value > 0:
            color = "#166534"
            sign = "+"
        elif value < 0:
            color = "#991b1b"
            sign = ""
        else:
            color = "#6b7280"
            sign = ""

        return format_html(
            '<span style="font-weight:700; color:{};">{}{}</span>',
            color,
            sign,
            f"{value:,.2f}",
        )

    @admin.display(description="Комментарий", ordering="temp")
    def comment_short(self, obj):
        if not obj.temp:
            return format_html('<span style="color:#9ca3af;">—</span>')

        text = obj.temp.strip()
        short_text = text[:6] + "..." if len(text) > 6 else text

        return format_html(
            '<span style="color:#374151;">{}</span>',
            short_text,
        )

    class Media:
        css = {
            "all": (
                "css/admin_overrides.css",
                "css/wide-table.css",
                "css/manual_admin_groups.css",
            )
        }
        js = (
            "js/manual_admin_groups.js",
        )