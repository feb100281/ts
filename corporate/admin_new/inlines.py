from unfold.admin import TabularInline

from corporate.models import BankAccount


class BankAccountInline(TabularInline):
    model = BankAccount

    extra = 1
    tab = True

    fields = (
        "bank",
        "account",
        "currency",
    )

    autocomplete_fields = (
        "bank",
    )