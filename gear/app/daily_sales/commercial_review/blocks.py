# gear/app/daily_sales/commercial_review/blocks.py
"""
Готовые блоки страницы.

Каждая функция возвращает готовый HTML. Смысл в том, чтобы
страницы собирались из одних и тех же деталей: тогда отчёт
выглядит как один документ, а не как склейка непохожих
разворотов.
"""

from __future__ import annotations

from datetime import timedelta

from . import config as C
from .formats import MONTHS_RU_SHORT as MONTHS_SHORT_RU
from .formats import escape, num, pct


# ============================================================
# КАРКАС СТРАНИЦЫ
# ============================================================

def page(
    number,
    chapter,
    title,
    note="",
    body="",
    source="",
    landscape=False,
    anchor=True,
) -> str:
    """
    Обычная страница отчёта.

    Номер и название раздела уезжают в колонтитул: читатель
    на любой странице видит, где он находится, а отчёт можно
    обсуждать вслух — «посмотри раздел семь», а не «где-то
    в середине».
    """
    note_html = f'<p class="head-note">{note}</p>' if note else ""
    source_html = f'<div class="source">{source}</div>' if source else ""

    number_html = (
        f'<div class="head-number">{escape(number)}</div>'
        if number
        else ""
    )

    chapter_mark = (
        f"{escape(number)} · {escape(chapter)}".upper()
        if number
        else escape(chapter).upper()
    )

    klass = "page page-landscape" if landscape else "page"

    id_attr = (
        f' id="section-{escape(number)}"' if number and anchor else ""
    )

    return f"""
    <section class="{klass}"{id_attr}>
        <div class="chapter">{chapter_mark}</div>
        <div class="head">
            <div class="head-rule">
                {number_html}
                <div class="head-kicker">{escape(chapter)}</div>
            </div>
            <h2>{title}</h2>
            {note_html}
        </div>
        {body}
        {source_html}
    </section>
    """


# ============================================================
# KPI
# ============================================================

def kpi(label, value, delta="", delta_state="", note="") -> str:
    """
    Карточка показателя.

    delta_state — good / bad / flat. От неё зависит цвет и знак,
    но рядом всегда стоит текст, поэтому смысл не держится
    только на цвете.
    """
    colors = {
        "good": C.GOOD,
        "bad": C.CRITICAL,
        "flat": C.MUTED,
    }

    delta_html = ""
    if delta:
        color = colors.get(delta_state, C.INK_2)
        delta_html = (
            f'<div class="kpi-delta" style="color:{color}">'
            f"{delta}</div>"
        )

    note_html = (
        f'<div class="kpi-note">{note}</div>' if note else ""
    )

    return f"""
    <div class="kpi">
        <div class="kpi-label">{escape(label)}</div>
        <div class="kpi-value">{value}</div>
        {delta_html}
        {note_html}
    </div>
    """


def kpi_grid(cards, cols=4) -> str:
    klass = {4: "", 3: " three", 2: " two", 5: " five"}.get(cols, "")
    return f'<div class="kpi-grid{klass}">{"".join(cards)}</div>'


# ============================================================
# ВЫВОД
# ============================================================

def finding_card(finding, show_action=True) -> str:
    """
    Один вывод: что произошло, почему и что делать.

    Пустые части не рисуются — лучше короткая карточка,
    чем строка «нет данных» в ней.
    """
    color, background = C.SEVERITY_COLOR.get(
        finding.severity,
        (C.MUTED, C.SURFACE_SOFT),
    )

    label = C.SEVERITY_LABEL.get(finding.severity, "К сведению")

    metric_html = (
        f'<div class="finding-metric" style="color:{color}">'
        f"{finding.metric}</div>"
        if finding.metric
        else ""
    )

    parts = [
        f'<div class="finding-line"><b>Что произошло</b><br>'
        f"{finding.fact}</div>"
    ]

    if finding.cause:
        parts.append(
            f'<div class="finding-line"><b>Почему</b><br>'
            f"{finding.cause}</div>"
        )

    if show_action and finding.action:
        parts.append(
            f'<div class="finding-action"><b>Что делать. </b>'
            f"{finding.action}</div>"
        )

    return f"""
    <div class="finding" style="border-left-color:{color}">
        <span class="finding-tag"
              style="background:{background};color:{color}">
            {escape(label)}
        </span>
        <div class="finding-head">
            <div class="finding-title">{finding.title}</div>
            {metric_html}
        </div>
        {"".join(parts)}
    </div>
    """


def severity_legend() -> str:
    order = ["critical", "serious", "warning", "good"]

    items = []
    for key in order:
        color, _background = C.SEVERITY_COLOR[key]
        items.append(
            f'<span><i style="background:{color}"></i>'
            f"{escape(C.SEVERITY_LABEL[key])}</span>"
        )

    return f'<div class="legend">{"".join(items)}</div>'


# ============================================================
# ГРАФИК
# ============================================================

def figure(title, image, sub="", note="", empty="") -> str:
    """
    График с заголовком и выводом под ним.

    Если картинки нет, вместо неё честная рамка с причиной:
    «данных за период не хватает» лучше, чем пустое место,
    из которого непонятно, сломался отчёт или нет.
    """
    head = f'<div class="figure-title">{title}</div>'

    if sub:
        head += f'<div class="figure-sub">{sub}</div>'

    if image:
        visual = f'<img src="{image}" alt="">'
    else:
        visual = (
            '<div class="figure-empty">'
            + escape(empty or "Данных за период недостаточно для графика")
            + "</div>"
        )

    note_html = (
        f'<div class="figure-note">{note}</div>' if note else ""
    )

    return f'<div class="figure">{head}{visual}{note_html}</div>'


# ============================================================
# ТАБЛИЦА
# ============================================================

def table(columns, rows, total=None, caption="", note="", wide=False) -> str:
    """
    Таблица.

    columns — список словарей: key, label, num (выравнивание
    по правому краю), fmt (функция форматирования).
    total — та же структура строки, печатается жирным итогом.
    """
    head_cells = "".join(
        f'<th class="{"num" if column.get("num") else ""}">'
        f'{escape(column["label"])}</th>'
        for column in columns
    )

    body_rows = []

    for row in rows:
        classes = []
        if row.get("_alert"):
            classes.append("alert")

        cells = []
        for column in columns:
            value = row.get(column["key"])
            fmt = column.get("fmt")
            text = fmt(value) if fmt else escape(value)
            cells.append(
                f'<td class="{"num" if column.get("num") else ""}">'
                f"{text}</td>"
            )

        body_rows.append(
            f'<tr class="{" ".join(classes)}">{"".join(cells)}</tr>'
        )

    if total:
        cells = []
        for column in columns:
            value = total.get(column["key"])
            fmt = column.get("fmt")
            text = fmt(value) if fmt else escape(value)
            cells.append(
                f'<td class="{"num" if column.get("num") else ""}">'
                f"{text}</td>"
            )
        body_rows.append(
            f'<tr class="total">{"".join(cells)}</tr>'
        )

    caption_html = (
        f"<caption>{caption}</caption>" if caption else ""
    )

    note_html = (
        f'<div class="table-note">{note}</div>' if note else ""
    )

    return f"""
    <table class="tbl{' wide' if wide else ''}">
        {caption_html}
        <thead><tr>{head_cells}</tr></thead>
        <tbody>{"".join(body_rows)}</tbody>
    </table>
    {note_html}
    """


# ============================================================
# ТЕКСТОВЫЕ БЛОКИ
# ============================================================

def callout(title, body, plain=False) -> str:
    klass = "callout plain" if plain else "callout"
    title_html = f"<h4>{escape(title)}</h4>" if title else ""
    return f'<div class="{klass}">{title_html}{body}</div>'


def bullets(items) -> str:
    clean = [item for item in items if item]
    if not clean:
        return ""
    return (
        '<ul class="bullets">'
        + "".join(f"<li>{item}</li>" for item in clean)
        + "</ul>"
    )


def bullet_bar(
    done_pct,
    marker_pct=None,
    left_label="",
    right_label="",
    center_label="",
) -> str:
    """
    Полоса выполнения плана.

    Заливка — сделано, вертикальная метка — где по календарю
    надо быть сейчас. Разрыв между ними и есть отставание.
    """
    done = max(0.0, min(160.0, num(done_pct) or 0.0))
    fill = min(100.0, done)

    marker_html = ""
    marker = num(marker_pct)

    if marker is not None:
        position = max(0.0, min(100.0, marker))
        marker_html = (
            f'<span class="bullet-marker" '
            f'style="left:{position:.2f}%"></span>'
        )

    color = (
        C.GOOD if done >= 100
        else (C.NAVY if done >= C.PLAN_BEHIND_PCT else C.SERIOUS)
    )

    center_html = (
        f'<span>{center_label}</span>' if center_label else "<span></span>"
    )

    return f"""
    <div class="bullet-bar">
        <div class="bullet-track">
            <div class="bullet-fill"
                 style="width:{fill:.2f}%;background:{color}"></div>
            {marker_html}
        </div>
        <div class="bullet-legend">
            <span>{left_label}</span>
            {center_html}
            <span>{right_label}</span>
        </div>
    </div>
    """


def toc(rows) -> str:
    """
    rows -- (номер раздела, название, что внутри).

    Каждая строка -- ссылка на якорь страницы (id="section-NN",
    его ставит page()), поэтому в PDF по оглавлению можно
    кликать. Номер страницы справа подтягивается из PDF через
    target-counter -- поддерживать его руками не нужно.
    """
    items = []

    for number, name, what in rows:
        anchor = f"#section-{escape(number)}"
        items.append(
            f'<a class="toc-row" href="{anchor}">'
            f'<span class="toc-num">{escape(number)}</span>'
            f'<span class="toc-name">{escape(name)}</span>'
            f'<span class="toc-what">{escape(what)}</span>'
            f"</a>"
        )

    return f'<div class="toc">{"".join(items)}</div>'


def delta_state(value, good_when_up=True) -> str:
    v = num(value)
    if v is None or abs(v) < 0.05:
        return "flat"

    rising = v > 0
    good = rising if good_when_up else not rising

    return "good" if good else "bad"


def share_note(part, whole, subject="") -> str:
    """Короткая приписка «это X % от целого»."""
    p, w = num(part), num(whole)
    if not p or not w:
        return ""
    return f"{subject}{pct(100.0 * p / w)} от общего"


# ============================================================
# КАЛЕНДАРЬ ВЫРУЧКИ
# ============================================================

WEEKDAY_SHORT = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]


def _heat(value, values):
    """
    Цвет клетки по силе дня.

    Ранг, а не доля от максимума: один выброс не должен красить
    все остальные дни в бледный.
    """
    clean = sorted(v for v in values if v is not None and v > 0)

    if not clean or value is None or value <= 0:
        return C.SURFACE_SOFT, C.MUTED

    rank = sum(1 for v in clean if v < value) / len(clean)
    index = min(len(C.HEAT) - 1, int(rank * len(C.HEAT)))

    # На тёмной заливке чёрный текст не читается.
    text = "#FFFFFF" if index >= 5 else C.INK

    return C.HEAT[index], text


def revenue_calendar(rows, weeks=5, money_fmt=None, subtitle="") -> str:
    """
    Тепловой календарь выручки: одна клетка — один закрытый день.

    Читается быстрее любого графика: сразу видно выходные
    провалы, сильные дни и итог недели рядом, в той же строке.
    """
    from .formats import as_date, money as _money, num as _num, signed_pct

    fmt = money_fmt or _money

    points = {}
    for row in rows or []:
        d = as_date(row.get("date_from") or row.get("date"))
        if d is None:
            continue
        points[d] = _num(row.get("amount")) or 0.0

    if len(points) < 7:
        return ""

    last = max(points)
    first_day = min(points)

    # Начало недели, в которую попадает самый ранний день.
    start = last - timedelta(days=last.weekday())
    start -= timedelta(weeks=weeks - 1)

    while start > first_day:
        start -= timedelta(weeks=1)

    values = list(points.values())

    header = "".join(f"<th>{day}</th>" for day in WEEKDAY_SHORT)
    header += '<th class="cal-week-head">Неделя</th>'

    body = []
    previous_total = None
    previous_full = True

    week_start = start

    while week_start <= last:
        cells = []
        total = 0.0
        filled = 0
        has_any = False

        for offset in range(7):
            day = week_start + timedelta(days=offset)
            value = points.get(day)

            if value is None:
                cells.append('<td class="cal-empty"></td>')
                continue

            has_any = True
            filled += 1
            total += value
            background, color = _heat(value, values)

            cells.append(
                f'<td style="background:{background};'
                f'border-color:{background}">'
                f'<div class="cal-date" style="color:{color}">'
                f"{day.day} {MONTHS_SHORT_RU[day.month]}</div>"
                f'<div class="cal-value" style="color:{color}">'
                f"{fmt(value)}</div>"
                f"</td>"
            )

        if not has_any:
            week_start += timedelta(days=7)
            continue

        full_week = filled == 7

        if not full_week:
            # Неполную неделю сравнивать с полной нельзя: падение
            # будет не потому, что хуже торговали, а потому что
            # дней меньше. Пишем это прямо.
            delta = (
                '<div class="cal-week-delta muted">'
                f"не закончена · {filled} из 7 дней</div>"
            )
        elif previous_total and previous_full:
            change = 100.0 * (total - previous_total) / previous_total
            arrow = "▲" if change >= 0 else "▼"
            delta_color = C.GOOD if change >= 0 else C.CRITICAL
            delta = (
                f'<div class="cal-week-delta" style="color:{delta_color}">'
                f"{arrow} {signed_pct(change)}</div>"
            )
        elif previous_total:
            delta = (
                '<div class="cal-week-delta muted">'
                "не с чем сравнить</div>"
            )
        else:
            delta = (
                '<div class="cal-week-delta muted">база сравнения</div>'
            )

        cells.append(
            '<td class="cal-week">'
            '<div class="cal-week-label">итого</div>'
            f'<div class="cal-week-value">{fmt(total)}</div>'
            f"{delta}"
            "</td>"
        )

        body.append(f"<tr>{''.join(cells)}</tr>")
        previous_total = total
        previous_full = full_week
        week_start += timedelta(days=7)

    subtitle_html = (
        f'<div class="figure-sub">{subtitle}</div>' if subtitle else ""
    )

    return (
        '<div class="figure">'
        '<div class="figure-title">Выручка по дням и неделям</div>'
        f"{subtitle_html}"
        f'<table class="cal"><thead><tr>{header}</tr></thead>'
        f"<tbody>{''.join(body)}</tbody></table>"
        '<div class="cal-legend">'
        "<span>Светлее — день слабее, насыщеннее — сильнее</span>"
        "<span>Справа итог недели и изменение к прошлой полной</span>"
        "</div>"
        "</div>"
    )


# ============================================================
# ПЛИТКИ НЕДЕЛЬ
# ============================================================

def week_tiles(weeks, title="", subtitle="", note="") -> str:
    """
    Недели в ряд: рентабельность крупно, деньги мелко.

    Так видно не точку, а ход: где экономика просела и
    вернулась ли она обратно.
    """
    from .formats import as_date, num, signed_money, signed_pct

    rows = [row for row in (weeks or []) if row.get("has_data")]

    if not rows:
        return ""

    rows = rows[-10:]

    tiles = []

    for row in rows:
        result_pct = num(row.get("result_pct"))
        amount = num(row.get("wb_result"))

        if result_pct is None:
            background, color = C.SURFACE_SOFT, C.MUTED
        elif result_pct < 0:
            background, color = C.CRITICAL_BG, C.CRITICAL
        elif result_pct >= 20:
            background, color = C.TINT, C.NAVY_3
        elif result_pct >= 10:
            background, color = C.TINT_2, C.NAVY
        else:
            background, color = C.WARNING_BG, "#8A6100"

        start = as_date(row.get("date_from"))
        end = as_date(row.get("date_to"))

        dates = (
            f"{start.strftime('%d.%m')}–{end.strftime('%d.%m')}"
            if start and end
            else ""
        )

        classes = "wtile current" if row.get("is_current") else "wtile"

        note_text = (
            "оперативно"
            if row.get("is_operational")
            else "закрыта"
        )

        tiles.append(
            f'<div class="{classes}" style="background:{background}">'
            f'<div class="wtile-label">{escape(row.get("label") or "")}</div>'
            f'<div class="wtile-dates">{escape(dates)}</div>'
            f'<div class="wtile-value" style="color:{color}">'
            f"{signed_pct(result_pct) if (result_pct or 0) < 0 else pct(result_pct)}"
            f"</div>"
            f'<div class="wtile-amount">{signed_money(amount)}</div>'
            f'<div class="wtile-note">{note_text}</div>'
            "</div>"
        )

    columns = len(tiles)

    head = (
        f'<div class="figure-title">{title}</div>' if title else ""
    )

    if subtitle:
        head += f'<div class="figure-sub">{subtitle}</div>'

    note_html = (
        f'<div class="figure-note">{note}</div>' if note else ""
    )

    return (
        '<div class="figure">'
        f"{head}"
        f'<div class="wtiles" '
        f'style="grid-template-columns:repeat({columns},1fr)">'
        f"{''.join(tiles)}</div>"
        f"{note_html}"
        "</div>"
    )
