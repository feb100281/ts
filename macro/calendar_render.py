from calendar import Calendar
from datetime import date

MONTHS_RU = [
    "", "Январь", "Февраль", "Март",
    "Апрель", "Май", "Июнь",
    "Июль", "Август", "Сентябрь",
    "Октябрь", "Ноябрь", "Декабрь"
]

WEEKDAYS_RU = ["пн", "вт", "ср", "чт", "пт", "сб", "вс"]


def render_month(year, month, exceptions):
    cal = Calendar()
    today = date.today()
    rows = cal.monthdayscalendar(year, month)

    html = []
    html.append("<div class='month-card'>")
    html.append(f"<div class='month-title'>{MONTHS_RU[month]} {year}</div>")

    html.append("<table class='month-table'>")
    html.append("<thead><tr>")
    for i, wd in enumerate(WEEKDAYS_RU):
        cls = "wd-weekend" if i >= 5 else ""
        html.append(f"<th class='{cls}'>{wd}</th>")
    html.append("</tr></thead><tbody>")

    for row in rows:
        html.append("<tr>")
        for i, day in enumerate(row):
            if day == 0:
                html.append("<td class='empty'></td>")
                continue

            dt = date(year, month, day)
            weekday = i  # 0=пн ... 6=вс (как в monthdayscalendar)

            classes = []

            # стандартные выходные для текста
            if weekday >= 5:
                classes.append("weekend")

            # базовое правило: пн–пт = рабочий, сб/вс = выходной
            default_is_work = weekday < 5

            # фактический статус: если есть запись в исключениях — берём её,
            # иначе — базовое правило
            actual_is_work = exceptions.get(dt, default_is_work)

            # если статус отличается от базового — это исключение -> подсветка
            if actual_is_work != default_is_work:
                if actual_is_work:
                    classes.append("workday")   # выходной стал рабочим
                else:
                    classes.append("offday")    # будний стал праздничным / выходным

            # сегодня
            if dt == date.today():
                classes.append("today")

            html.append(f"<td class='{' '.join(classes)}'>{day}</td>")
        html.append("</tr>")

    html.append("</tbody></table></div>")
    return "".join(html)


def calc_quarter_stats(year, months, exceptions):
    """
    Считаем статистику по кварталу:
    - календарных дней
    - рабочих
    - выходных (сб/вс)
    - праздничных/переносов (будние, которые стали нерабочими)
    """
    total_days = 0
    working_days = 0
    weekend_days = 0
    holidays = 0  # будние, которые стали нерабочими по П-календарю

    for month in months:
        cal = Calendar()
        rows = cal.monthdayscalendar(year, month)

        for row in rows:
            for i, day in enumerate(row):
                if day == 0:
                    continue

                dt = date(year, month, day)
                weekday = i  # 0=пн ... 6=вс
                total_days += 1

                default_is_work = weekday < 5
                actual_is_work = exceptions.get(dt, default_is_work)

                # рабочие / нерабочие
                if actual_is_work:
                    working_days += 1
                else:
                    # по факту день нерабочий
                    if weekday >= 5:
                        weekend_days += 1  # обычные выходные
                    else:
                        holidays += 1      # будний, ставший праздничным/выходным

    return {
        "total": total_days,
        "working": working_days,
        "weekend": weekend_days,
        "holidays": holidays,
    }


def render_quarter_summary(quarter_num, stats):
    return (
        "<div class='quarter-summary'>"
        f"<div class='quarter-title'>{quarter_num} квартал</div>"
        "<ul class='quarter-list'>"

        "<li class='qs-total'>"
        "  <span class='qs-label'><span class='qs-icon'></span>Календарных дней</span>"
        f"  <span class='qs-value'>{stats['total']}</span>"
        "</li>"

        "<li class='qs-work'>"
        "  <span class='qs-label'><span class='qs-icon'></span>Рабочих</span>"
        f"  <span class='qs-value'>{stats['working']}</span>"
        "</li>"

        "<li class='qs-weekend'>"
        "  <span class='qs-label'><span class='qs-icon'></span>Выходных (сб/вс)</span>"
        f"  <span class='qs-value'>{stats['weekend']}</span>"
        "</li>"

        "<li class='qs-holidays'>"
        "  <span class='qs-label'><span class='qs-icon'></span>Праздничных / переносов</span>"
        f"  <span class='qs-value'>{stats['holidays']}</span>"
        "</li>"

        "</ul>"
        "</div>"
    )



def build_year_calendar(year, exceptions):
    """
    Рисуем календарь по кварталам:
    строка:
      [месяц][месяц][месяц] [карточка со статистикой квартала]
    """
    html = []

    for q in range(4):
        months = [1 + 3 * q, 2 + 3 * q, 3 + 3 * q]
        stats = calc_quarter_stats(year, months, exceptions)

        html.append("<div class='quarter-row'>")

        # три месяца
        html.append("<div class='quarter-months'>")
        for m in months:
            html.append(render_month(year, m, exceptions))
        html.append("</div>")

        # сводка квартала
        html.append(render_quarter_summary(q + 1, stats))

        html.append("</div>")  # .quarter-row

    return "".join(html)


