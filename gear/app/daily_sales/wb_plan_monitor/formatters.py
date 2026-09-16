# gear/app/daily_sales/wb_plan_monitor/formatters.py
def format_money(value):
    value = float(value or 0)
    return f"{value:,.0f}".replace(",", " ")


def format_money_short(value):
    value = float(value or 0)

    if abs(value) >= 1_000_000_000:
        return f"{value / 1_000_000_000:.1f} млрд ₽"

    if abs(value) >= 1_000_000:
        return f"{value / 1_000_000:.1f} млн ₽"

    if abs(value) >= 1_000:
        return f"{value / 1_000:.0f} тыс. ₽"

    return f"{value:,.0f} ₽".replace(",", " ")


def format_pct(value):
    return f"{float(value or 0):.1f}%"


def get_month_name_ru(month_num):
    months = [
        "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
        "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь",
    ]
    return months[int(month_num) - 1]


def get_month_name_short_ru(month_num):
    months = [
        "янв", "фев", "мар", "апр", "май", "июн",
        "июл", "авг", "сен", "окт", "ноя", "дек",
    ]
    return months[int(month_num) - 1]


def get_weekday_ru(dt):
    days = ["пн", "вт", "ср", "чт", "пт", "сб", "вс"]
    return days[dt.weekday()]