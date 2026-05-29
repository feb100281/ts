from django.contrib import admin
from django.db.models import Max
from django.utils.html import format_html

from unfold.admin import ModelAdmin
from unfold.decorators import display

from corporate.models import BankAccount
from utils.choises import (
    CURRENCY_FLAGS,
    CURRENCY_SYMBOLS,
)


@admin.register(BankAccount)
class BankAccountAdmin(ModelAdmin):

    list_display = (
        "bank_logo",
        "bank_name",
        "account",
        "currency_view",
        "bs_acc_code",
        "last_statement_day",
        "is_active",
    )

    list_display_links = (
        "bank_name",
    )

    search_fields = (
        "corporate__name",
        "bank__name",
        "account",
    )

    list_filter = (
        "corporate__name",
    )

    class Media:
        css = {
            "all": (
                "fonts/glyphs.css",
                "css/admin_overrides.css",
            )
        }

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related(
                "bank",
                "corporate",
            )
            .annotate(
                _last_bs_day=Max(
                    "bankstatements__finish"
                )
            )
        )

    @display(
        description="Последняя выписка",
        ordering="_last_bs_day",
    )
    def last_statement_day(self, obj):
        d = getattr(obj, "_last_bs_day", None)

        if not d:
            return "—"

        return d.strftime("%d.%m.%Y")

    @display(
        description="Валюта",
        ordering="currency",
    )
    def currency_view(self, obj):
        code = (obj.currency or "").upper()
        flag = CURRENCY_FLAGS.get(code, "")
        sym = CURRENCY_SYMBOLS.get(code, "")

        return format_html(
            "{} {} {}",
            flag,
            sym,
            code,
        )

    @display(
        description="Балансовый счет",
        ordering="bs_acc__code",
    )
    def bs_acc_code(self, obj):
        if not obj.bs_acc:
            return "—"

        return obj.bs_acc.code

    @display(
        description="",
        ordering="bank__name",
    )
    def bank_logo(self, obj):
        if not obj.bank or not obj.bank.logo:
            return "—"

        outer = (
            "display:inline-flex;align-items:center;justify-content:center;"
            "width:24px;height:24px;border-radius:6px;"
            "background:linear-gradient(135deg,#f8fafc,#f1f5f9);"
            "box-shadow:0 0 0 1px rgba(148,163,184,.35);"
        )

        inner = (
            "font-family:NotoManu;"
            "font-size:16px;"
            "line-height:1;"
        )

        return format_html(
            '<span style="{}"><span style="{}">{}</span></span>',
            outer,
            inner,
            obj.bank.logo,
        )

    @display(
        description="Банк",
        ordering="bank__name",
    )
    def bank_name(self, obj):
        if not obj.bank:
            return "—"

        return obj.bank.name