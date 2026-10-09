"""Мелкие helpers."""

def fmt(value):
    try:
        return f"{float(value or 0):,.0f}".replace(",", " ")
    except (TypeError, ValueError):
        return "0"


def fmt_money(value):
    try:
        return f"{float(value or 0):,.0f}".replace(",", " ")
    except (TypeError, ValueError):
        return "0"


def safe_float(value):
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0
