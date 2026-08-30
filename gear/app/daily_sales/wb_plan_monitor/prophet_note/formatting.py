from __future__ import annotations

from datetime import date, datetime
from typing import Any


MONTHS_GENITIVE_RU = {
    1: "января",
    2: "февраля",
    3: "марта",
    4: "апреля",
    5: "мая",
    6: "июня",
    7: "июля",
    8: "августа",
    9: "сентября",
    10: "октября",
    11: "ноября",
    12: "декабря",
}

MONTHS_SHORT_RU = {
    1: "Янв",
    2: "Фев",
    3: "Мар",
    4: "Апр",
    5: "Май",
    6: "Июн",
    7: "Июл",
    8: "Авг",
    9: "Сен",
    10: "Окт",
    11: "Ноя",
    12: "Дек",
}


def to_date(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    if not value:
        raise ValueError("Не задана дата.")

    return datetime.fromisoformat(str(value)).date()


def format_date_ru(value: Any) -> str:
    dt = to_date(value)
    return f"{dt.day} {MONTHS_GENITIVE_RU[dt.month]} {dt.year} г."


def format_date_short(value: Any) -> str:
    return to_date(value).strftime("%d.%m.%Y")


def format_money(value: float, decimals: int = 0) -> str:
    number = float(value or 0)

    if decimals == 0:
        result = f"{number:,.0f}"
    else:
        result = f"{number:,.{decimals}f}"

    return result.replace(",", " ")


def format_money_mln(value: float, decimals: int = 1) -> str:
    number = float(value or 0) / 1_000_000
    return (
        f"{number:,.{decimals}f}"
        .replace(",", " ")
        .replace(".", ",")
    )


def format_pct(value: float, decimals: int = 2) -> str:
    return (
        f"{float(value or 0):.{decimals}f}"
        .replace(".", ",")
        + "%"
    )


def signed_money(value: float, decimals: int = 0) -> str:
    number = float(value or 0)
    sign = "+" if number > 0 else ""

    if decimals == 0:
        result = f"{sign}{number:,.0f}"
    else:
        result = f"{sign}{number:,.{decimals}f}"

    return result.replace(",", " ")


def half_year_label(month: int, year: int) -> str:
    return (
        f"I полугодие {year} года"
        if month <= 6
        else f"II полугодие {year} года"
    )


def period_days(date_start: date, date_end: date) -> int:
    return (date_end - date_start).days + 1
