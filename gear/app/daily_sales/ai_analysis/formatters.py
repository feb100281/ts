from __future__ import annotations


def format_money(value: float | int | None) -> str:
    value = float(value or 0)

    if abs(value) >= 1_000_000_000:
        return f"{value / 1_000_000_000:,.2f} млрд ₽".replace(",", " ")

    if abs(value) >= 1_000_000:
        return f"{value / 1_000_000:,.2f} млн ₽".replace(",", " ")

    if abs(value) >= 1_000:
        return f"{value / 1_000:,.1f} тыс. ₽".replace(",", " ")

    return f"{value:,.0f} ₽".replace(",", " ")


def format_number(value: float | int | None) -> str:
    return f"{float(value or 0):,.0f}".replace(",", " ")


def format_pct(value: float | int | None, signed: bool = False) -> str:
    value = float(value or 0)
    sign = "+" if signed and value > 0 else ""
    return f"{sign}{value:.1f}%"


def safe_pct_change(current: float, previous: float) -> float:
    current = float(current or 0)
    previous = float(previous or 0)

    if previous == 0:
        return 0.0 if current == 0 else 100.0

    return (current - previous) / abs(previous) * 100


def change_color(value: float, inverse: bool = False) -> str:
    value = float(value or 0)

    if inverse:
        if value < 0:
            return "green"
        if value > 0:
            return "red"
        return "gray"

    if value > 0:
        return "green"
    if value < 0:
        return "red"
    return "gray"


def change_icon(value: float, inverse: bool = False) -> str:
    value = float(value or 0)

    if inverse:
        if value < 0:
            return "solar:arrow-down-linear"
        if value > 0:
            return "solar:arrow-up-linear"
        return "solar:minus-circle-linear"

    if value > 0:
        return "solar:arrow-up-linear"
    if value < 0:
        return "solar:arrow-down-linear"
    return "solar:minus-circle-linear"
