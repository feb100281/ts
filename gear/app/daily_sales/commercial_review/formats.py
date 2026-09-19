# gear/app/daily_sales/commercial_review/formats.py
"""
Форматирование чисел и дат для отчёта.

Правила одни на весь документ: отрицательные значения
в скобках, крупные суммы сокращаются до миллионов,
пустое значение — тире, а не ноль.
"""

from __future__ import annotations

from datetime import date, datetime

MONTHS_RU = {
    1: "января", 2: "февраля", 3: "марта", 4: "апреля",
    5: "мая", 6: "июня", 7: "июля", 8: "августа",
    9: "сентября", 10: "октября", 11: "ноября", 12: "декабря",
}

MONTHS_RU_NOM = {
    1: "январь", 2: "февраль", 3: "март", 4: "апрель",
    5: "май", 6: "июнь", 7: "июль", 8: "август",
    9: "сентябрь", 10: "октябрь", 11: "ноябрь", 12: "декабрь",
}

MONTHS_RU_SHORT = {
    1: "янв", 2: "фев", 3: "мар", 4: "апр",
    5: "май", 6: "июн", 7: "июл", 8: "авг",
    9: "сен", 10: "окт", 11: "ноя", 12: "дек",
}

WEEKDAYS_RU = {
    0: "понедельник", 1: "вторник", 2: "среда", 3: "четверг",
    4: "пятница", 5: "суббота", 6: "воскресенье",
}


NBSP = " "


def num(value):
    """Число в float или None. Пустые значения не превращаются в ноль."""
    if value is None:
        return None

    if isinstance(value, bool):
        return None

    try:
        result = float(value)
    except (TypeError, ValueError):
        return None

    if result != result:          # NaN
        return None

    return result


def _spaced(text: str) -> str:
    """
    Русская запись числа: пробел между разрядами, запятая
    в дробной части. Питон по умолчанию делает наоборот,
    поэтому меняем через временный символ.
    """
    return (
        text
        .replace(",", "\x00")
        .replace(".", ",")
        .replace("\x00", NBSP)
    )


def money(value, dash="—", sign=False) -> str:
    """
    Сумма в рублях. Отрицательные в скобках.

    От миллиона сокращаем: читать «26,0 млн ₽» проще,
    чем считать нули в «26 025 839 ₽».
    """
    v = num(value)
    if v is None:
        return dash

    negative = v < 0
    a = abs(v)

    if a >= 1_000_000_000:
        text = _spaced(f"{a / 1_000_000_000:,.2f}") + f"{NBSP}млрд{NBSP}₽"
    elif a >= 1_000_000:
        text = _spaced(f"{a / 1_000_000:,.1f}") + f"{NBSP}млн{NBSP}₽"
    elif a >= 1_000:
        text = _spaced(f"{a:,.0f}") + f"{NBSP}₽"
    else:
        text = _spaced(f"{a:,.0f}") + f"{NBSP}₽"

    if negative:
        return f"({text})"

    if sign and v > 0:
        return f"+{text}"

    return text


def money_exact(value, dash="—") -> str:
    """Полная сумма без сокращения — для таблиц."""
    v = num(value)
    if v is None:
        return dash

    text = _spaced(f"{abs(v):,.0f}")
    return f"({text})" if v < 0 else text


def qty(value, dash="—") -> str:
    v = num(value)
    if v is None:
        return dash

    text = _spaced(f"{abs(v):,.0f}")
    return f"({text})" if v < 0 else text


def pct(value, digits=1, dash="—", sign=False) -> str:
    """Проценты. На вход 12.5, а не 0.125."""
    v = num(value)
    if v is None:
        return dash

    text = f"{abs(v):,.{digits}f}".replace(",", NBSP).replace(".", ",")

    if v < 0:
        return f"({text}{NBSP}%)"

    if sign and v > 0:
        return f"+{text}{NBSP}%"

    return f"{text}{NBSP}%"


def level_pct(value, digits=1, dash="—") -> str:
    """
    Процент как уровень, а не как сумма.

    В таблицах отрицательное берём в скобки — это управленческая
    норма. Но в связном тексте «(6,5 %) маржинальности» читается
    как сноска, а не как минус, поэтому здесь знак.
    """
    v = num(value)
    if v is None:
        return dash

    text = f"{abs(v):,.{digits}f}".replace(",", NBSP).replace(".", ",")
    prefix = "−" if v < 0 else ""
    return f"{prefix}{text}{NBSP}%"


def pp(value, digits=1, dash="—") -> str:
    """Процентные пункты со знаком."""
    v = num(value)
    if v is None:
        return dash

    text = f"{abs(v):,.{digits}f}".replace(",", NBSP).replace(".", ",")
    prefix = "+" if v > 0 else ("−" if v < 0 else "")
    return f"{prefix}{text}{NBSP}п.п."


def signed_pct(value, digits=1, dash="—") -> str:
    """Изменение в процентах со знаком: +12,5 % или −12,5 %."""
    v = num(value)
    if v is None:
        return dash

    text = f"{abs(v):,.{digits}f}".replace(",", NBSP).replace(".", ",")
    prefix = "+" if v > 0 else ("−" if v < 0 else "")
    return f"{prefix}{text}{NBSP}%"


def signed_money(value, dash="—") -> str:
    """Изменение в рублях со знаком, без скобок."""
    v = num(value)
    if v is None:
        return dash

    prefix = "+" if v > 0 else ("−" if v < 0 else "")
    return prefix + money(abs(v))


def days(value, dash="—") -> str:
    v = num(value)
    if v is None:
        return dash

    n = int(round(v))
    last, last_two = n % 10, n % 100

    if 11 <= last_two <= 14:
        word = "дней"
    elif last == 1:
        word = "день"
    elif last in (2, 3, 4):
        word = "дня"
    else:
        word = "дней"

    return f"{n}{NBSP}{word}"


def hours(value, dash="—") -> str:
    v = num(value)
    if v is None:
        return dash
    return f"{v:,.1f}".replace(",", NBSP).replace(".", ",") + f"{NBSP}ч"


def as_date(value):
    """Приводит что угодно к date или None."""
    if value is None or value == "":
        return None

    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    text = str(value)[:10]

    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def date_short(value, dash="—") -> str:
    d = as_date(value)
    return d.strftime("%d.%m.%Y") if d else dash


def date_words(value, dash="—") -> str:
    d = as_date(value)
    if not d:
        return dash
    return f"{d.day} {MONTHS_RU[d.month]} {d.year}"


def date_full(value, dash="—") -> str:
    d = as_date(value)
    if not d:
        return dash
    return (
        f"{WEEKDAYS_RU[d.weekday()]}, "
        f"{d.day} {MONTHS_RU[d.month]} {d.year}"
    )


def month_name(value, dash="—") -> str:
    d = as_date(value)
    return MONTHS_RU_NOM[d.month] if d else dash


def month_number(value):
    """
    Номер месяца из чего угодно.

    Источники дают месяц по-разному: числом 9, строкой «2026-09»
    из периода pandas, полной датой. Приводим всё к одному виду,
    иначе int() спотыкается на «2026-09».
    """
    if value is None or value == "":
        return None

    if isinstance(value, bool):
        return None

    if isinstance(value, (datetime, date)):
        return value.month

    if isinstance(value, (int, float)):
        n = int(value)
        return n if 1 <= n <= 12 else None

    text = str(value).strip()
    parts = text.split("-")

    if len(parts) >= 2:
        try:
            n = int(parts[1])
        except ValueError:
            return None
        return n if 1 <= n <= 12 else None

    try:
        n = int(text)
    except ValueError:
        return None

    return n if 1 <= n <= 12 else None


def month_label(value, dash="—", short=False) -> str:
    """Название месяца по любому представлению месяца."""
    n = month_number(value)

    if n is None:
        return dash

    name = MONTHS_RU_NOM[n]

    return name[:3] if short else name


def plural(n, one, few, many) -> str:
    """Склонение существительного при числительном."""
    value = num(n)

    if value is None:
        return many

    n = int(abs(value))
    last, last_two = n % 10, n % 100

    if 11 <= last_two <= 14:
        return many
    if last == 1:
        return one
    if last in (2, 3, 4):
        return few
    return many


def escape(text) -> str:
    """Экранирование для вставки в HTML."""
    if text is None:
        return ""

    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
