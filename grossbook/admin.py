from django.contrib import admin
from .models import Manual
# from .models import Settlements
# Register your models here.
# @admin.register(Manual)
# class ManualAdmin(admin.ModelAdmin):
#     list_display = (
#         'id',
#         'pid',
#         'date',
#         'owner',
#         'acc',
#         'contract',
#         'dt',
#         'cr',
#         'currency',
        
        
#     )
#     search_fields = ("owner", "contract","acc")
#     list_filter = ("contract","acc", )
#     list_per_page = 25
    
    
#     class Media:
#         css = {"all": ("css/admin_overrides.css",'css/wide-table.css')}





from django.contrib import admin
from django.contrib.admin import RelatedOnlyFieldListFilter
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from .models import Manual


@admin.register(Manual)
class ManualAdmin(admin.ModelAdmin):
    change_list_template = "admin/grossbook/manual/change_list.html"
    change_form_template = "admin/grossbook/manual/change_form.html"

    list_display = (
        "id_badge",
        "date_short",
        # "owner_badge",
        "contract_badge",
        "acc_badge",
        "amount_dt",
        "amount_cr",
        "balance_badge",
        "currency_badge",
        "pid_badge",
    )
    list_display_links = ("id_badge", "contract_badge")
    search_fields = (
        "id",
        "temp",
        "owner__name",
        "contract__number",
        "contract__cp__name",
        "acc__name",
        "acc__number",
    )
    list_filter = (
        "currency",
        ("owner", RelatedOnlyFieldListFilter),
        ("contract", RelatedOnlyFieldListFilter),
        ("acc", RelatedOnlyFieldListFilter),
    )
    list_per_page = 25
    date_hierarchy = "date"
    ordering = ("-date", "-id")
    preserve_filters = True

    autocomplete_fields = ("owner", "acc", "contract", "cfitem", "pid")

    fieldsets = (
        (
            mark_safe("🧾 <b>Карточка проводки</b>"),
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
            mark_safe("🔗 <b>Связи</b>"),
            {
                "fields": ("pid",),
                "classes": ("collapse",),
            },
        ),
    )

    @admin.display(description="ID", ordering="id")
    def id_badge(self, obj):
        return format_html(
            '<span style="display:inline-flex;align-items:center;justify-content:center;'
            "min-width:44px;padding:4px 10px;border-radius:2px;"
            "font-size:12px;font-weight:800;"
            "background:rgba(15,23,42,.08);color:#0f172a;"
            'border:1px solid rgba(15,23,42,.10);">#{}</span>',
            obj.id,
        )

    @admin.display(description="Дата", ordering="date")
    def date_short(self, obj):
        if not obj.date:
            return "—"
        return obj.date.strftime("%d.%m.%Y")

    @admin.display(description="Компания", ordering="owner__name")
    def owner_badge(self, obj):
        if not obj.owner:
            return "—"
        return format_html(
            '<span style="font-weight:700;color:#0f172a;">{}</span>',
            obj.owner,
        )
    @admin.display(description="Договор", ordering="contract__number")
    def contract_badge(self, obj):
        if not obj.contract:
            return "—"

        number = obj.contract.number or "без номера"
        cp_name = getattr(obj.contract.cp, "name", "—")

        return format_html(
            '<div style="display:flex;flex-direction:column;gap:2px;">'
            '<span style="font-weight:800;color:#0f172a;">{}</span>'
            '<span style="font-size:11px;color:#475569;">{}</span>'
            "</div>",
            number,
            cp_name,
        )

    @admin.display(description="Счёт", ordering="acc__name")
    def acc_badge(self, obj):
        if not obj.acc:
            return "—"
        return format_html(
            '<div style="display:flex;flex-direction:column;gap:2px;">'
            '<span style="font-weight:700;color:#0f172a;">{}</span>'
            "</div>",
            obj.acc,
        )

    @admin.display(description="Дт", ordering="dt")
    def amount_dt(self, obj):
        value = f"{(obj.dt or 0):,.2f}"
        return format_html(
            '<span style="font-weight:800;color:#166534;">{}</span>',
            value,
        )

    @admin.display(description="Кт", ordering="cr")
    def amount_cr(self, obj):
        value = f"{(obj.cr or 0):,.2f}"
        return format_html(
            '<span style="font-weight:800;color:#991b1b;">{}</span>',
            value,
        )

    @admin.display(description="Сумма")
    def balance_badge(self, obj):
        value = (obj.dt or 0) - (obj.cr or 0)

        if value > 0:
            bg = "rgba(22,163,74,.10)"
            color = "#166534"
            sign = "+"
        elif value < 0:
            bg = "rgba(220,38,38,.10)"
            color = "#991b1b"
            sign = ""
        else:
            bg = "rgba(148,163,184,.16)"
            color = "#475569"
            sign = ""

        value_str = f"{sign}{value:,.2f}"

        return format_html(
            '<span style="display:inline-flex;align-items:center;justify-content:center;'
            'min-width:88px;padding:4px 10px;border-radius:2px;'
            'font-size:12px;font-weight:800;'
            'background:{};color:{};'
            'border:1px solid rgba(148,163,184,.16);">{}</span>',
            bg,
            color,
            value_str,
        )
    @admin.display(description="Валюта", ordering="currency")
    def currency_badge(self, obj):
        return format_html(
            '<span style="display:inline-flex;align-items:center;justify-content:center;'
            "padding:4px 10px;border-radius:2px;"
            "font-size:11px;font-weight:800;"
            "background:rgba(37,99,235,.10);color:#1d4ed8;"
            'border:1px solid rgba(37,99,235,.18);">{}</span>',
            obj.currency,
        )

    @admin.display(description="Связь")
    def pid_badge(self, obj):
        if not obj.pid_id:
            return format_html('<span style="color:#94a3b8;">—</span>')

        return format_html(
            '<span style="display:inline-flex;align-items:center;justify-content:center;'
            "padding:4px 10px;border-radius:2px;"
            "font-size:11px;font-weight:800;"
            "background:rgba(124,58,237,.10);color:#6d28d9;"
            'border:1px solid rgba(124,58,237,.18);">#{} </span>',
            obj.pid_id,
        )

    class Media:
        css = {
            "all": (
                "css/admin_overrides.css",
                "css/wide-table.css",
            )
        }


# @admin.register(Settlements)
# class SettlementsAdmin(admin.ModelAdmin):
#     list_display = (
#         "date_from",
#         "pid",
#         "contract",
#         "cp",
#         "st",
#         "description",
#         "dt",
#         "cr",       
#     )
#     class Media:
#         css = {
#             "all": (
#                 "css/admin_overrides.css",
#                 "css/wide-table.css",
#             )
#         }
    