# budget/reporting/pdf/utils/formatters.py

def format_money(value):
    if value is None:
        return "—"
    return f"{value:,.2f}".replace(",", " ")


def format_money_compact(value):
    if value is None:
        return "—"
    return f"{value:,.2f}".replace(",", " ").replace(".00", "")


def format_qty(value):
    if value is None:
        return "—"
    return f"{int(round(value)):,}".replace(",", " ")


def format_percent(value):
    if value is None:
        return "—"
    return f"{value:.1f}%"


def format_percent_comma(value):
    if value is None:
        return "—"
    return f"{value:.1f}%".replace(".", ",")


def format_pct_signed(value: float | None) -> str:
    if value is None:
        return "—"
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.1f}%".replace(".", ",")


def format_corr(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{value:.2f}".replace(".", ",")


def format_money_axis_ru(x, pos=None):
    abs_x = abs(x)
    if abs_x >= 1_000_000:
        value = x / 1_000_000
        return f"{value:,.1f} млн".replace(",", " ").replace(".", ",")
    if abs_x >= 1_000:
        value = x / 1_000
        return f"{value:,.0f} тыс".replace(",", " ")
    return f"{x:,.0f}".replace(",", " ")


def format_price_axis_ru(x, pos=None):
    return f"{x:,.0f}".replace(",", " ")


def format_pct_label(value: float | None) -> str:
    if value is None:
        return "—"
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.1f}%".replace(".", ",")


def format_bar_label(value):
    abs_x = abs(value)
    if abs_x >= 1_000_000:
        return f"{value / 1_000_000:.1f} млн".replace(".", ",")
    if abs_x >= 1_000:
        return f"{value / 1_000:.0f} тыс".replace(".", ",")
    return f"{value:,.0f}".replace(",", " ")