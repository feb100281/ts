from decimal import Decimal, InvalidOperation
from datetime import datetime, date

from django import template

register = template.Library()


MONTHS_RU = {
    1: "Январь",
    2: "Февраль",
    3: "Март",
    4: "Апрель",
    5: "Май",
    6: "Июнь",
    7: "Июль",
    8: "Август",
    9: "Сентябрь",
    10: "Октябрь",
    11: "Ноябрь",
    12: "Декабрь",
}


def _to_date(value):
    if not value:
        return None

    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None

        patterns = (
            "%Y-%m-%d",
            "%Y-%m-%d %H:%M:%S",
            "%d.%m.%Y",
            "%d.%m.%Y %H:%M:%S",
        )

        for pattern in patterns:
            try:
                return datetime.strptime(value, pattern).date()
            except ValueError:
                continue

    return None


@register.filter
def money_ru(value):
    """
    1234567.8 -> 1 234 567,80
    """
    if value in (None, "", False):
        return "—"

    try:
        dec_value = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return value

    formatted = f"{dec_value:,.2f}"
    formatted = formatted.replace(",", "X").replace(".", ",").replace("X", " ")
    return formatted


@register.filter
def date_ru(value):
    dt = _to_date(value)
    if not dt:
        return "—"
    return dt.strftime("%d.%m.%Y")


@register.filter
def month_year_ru(value):
    dt = _to_date(value)
    if not dt:
        return "—"
    return f"{MONTHS_RU.get(dt.month, '')} {dt.year}"


@register.filter
def vat_mode_ru(value):
    mapping = {
        "included": "НДС включён",
        "excluded": "НДС сверху",
        "exempt": "Без НДС",
    }
    return mapping.get(value, "Не задано")