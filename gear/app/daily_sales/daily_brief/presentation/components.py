# gear/app/daily_sales/daily_brief/presentation/components.py
from __future__ import annotations

from html import escape

from ..helpers import fmt_number
from .icons import icon


def safe(value) -> str:
    return escape(str(value if value is not None else ""))


def metric(label: str, value: str, note: str = "", icon_name: str = "revenue", tone: str = "") -> str:
    return f'''<div class="metric {tone}"><div class="metric-top"><span>{safe(label)}</span>{icon(icon_name, 27)}</div><div class="metric-value">{safe(value)}</div><div class="metric-note">{safe(note)}</div></div>'''


def section(kicker: str, title: str, body: str, subtitle: str = "", icon_name: str = "newspaper", class_name: str = "") -> str:
    return f'''<section class="section {class_name}"><header class="section-head"><div><div class="kicker">{safe(kicker)}</div><h2>{safe(title)}</h2><div class="section-subtitle">{safe(subtitle)}</div></div>{icon(icon_name, 34)}</header>{body}</section>'''


def change_badge(value) -> str:
    if value is None:
        return '<span class="badge neutral">нет базы</span>'
    css = "up" if value > 0 else "down" if value < 0 else "neutral"
    arrow = "▲" if value > 0 else "▼" if value < 0 else "•"
    return f'<span class="badge {css}">{arrow} {abs(float(value)):.1f}%</span>'


def comparison_card(
    data: dict,
    *,
    card_class: str = "",
) -> str:
    """
    Карточка сопоставимой динамики.

    Для дневных сравнений:
    - крупно показывается процент изменения;
    - ниже выводится отклонение в рублях;
    - внизу — значение и дата базы.

    Для MTD/YTD:
    - крупно показывается текущая накопленная выручка;
    - ниже — процент и отклонение в рублях;
    - внизу — значение и период базы.
    """

    from ..helpers import (
        fmt_money,
        fmt_pct,
        number,
    )

    label = safe(
        data.get("label")
        or "Период сравнения"
    )

    current = number(
        data.get("current")
    )

    previous = number(
        data.get("previous")
    )

    previous_label = safe(
        data.get("previous_label")
        or "период не указан"
    )

    change = data.get(
        "change_pct"
    )

    difference = (
        current
        - previous
    )

    is_period_card = (
        "comparison-period"
        in str(card_class)
    )

    if change is None:
        change_class = "neutral"
        change_icon = "•"
        change_text = "нет базы"
        difference_text = (
            "Сравнение недоступно"
        )

    else:
        change = number(
            change
        )

        if change > 0:
            change_class = "up"
            change_icon = "▲"
            change_text = fmt_pct(
                abs(change)
            )
            difference_text = (
                f"+{fmt_money(abs(difference))}"
            )

        elif change < 0:
            change_class = "down"
            change_icon = "▼"
            change_text = fmt_pct(
                abs(change)
            )
            difference_text = (
                f"−{fmt_money(abs(difference))}"
            )

        else:
            change_class = "neutral"
            change_icon = "•"
            change_text = "0,0%"
            difference_text = (
                "без изменений"
            )

    # ================================================================
    # MTD / YTD
    # ================================================================

    if is_period_card:
        return f"""
        <article class="comparison-card comparison-period">
            <div class="comparison-card-label">
                {label}
            </div>

            <div class="comparison-period-current">
                {fmt_money(current)}
            </div>

            <div class="comparison-period-dynamics">
                <div class="comparison-period-change {change_class}">
                    <span class="comparison-period-arrow">
                        {change_icon}
                    </span>

                    <span>
                        {change_text}
                    </span>
                </div>

                <div class="comparison-period-delta {change_class}">
                    {difference_text}
                </div>
            </div>

            <div class="comparison-base comparison-period-base">
                <div class="comparison-base-caption">
                    Было
                </div>

                <div class="comparison-base-value">
                    {fmt_money(previous)}
                </div>

                <div class="comparison-base-period">
                    {previous_label}
                </div>
            </div>
        </article>
        """

    # ================================================================
    # ДЕНЬ / ПРОШЛЫЙ МЕСЯЦ / ПРОШЛЫЙ ГОД
    # ================================================================

    return f"""
    <article class="comparison-card comparison-day">
        <div class="comparison-card-label">
            {label}
        </div>

        <div class="comparison-day-main {change_class}">
            <span class="comparison-day-arrow">
                {change_icon}
            </span>

            <span class="comparison-day-percent">
                {change_text}
            </span>
        </div>

        <div class="comparison-day-delta {change_class}">
            {difference_text}
        </div>

        <div class="comparison-base comparison-day-base">
            <div class="comparison-base-caption">
                Было
            </div>

            <div class="comparison-base-value">
                {fmt_money(previous)}
            </div>

            <div class="comparison-base-period">
                {previous_label}
            </div>
        </div>
    </article>
    """

def bar_chart(
    rows,
    value_key: str,
    suffix: str = "₽",
    limit: int = 6,
    *,
    tone: str = "coral",
    show_share: bool = False,
    total: float | None = None,
) -> str:
    rows = list(
        rows
        or []
    )[:limit]

    if not rows:
        return '<div class="empty">Нет данных</div>'

    values = [
        float(
            row.get(value_key)
            or 0
        )
        for row in rows
    ]

    maximum = max(
        values
    ) or 1

    if total is None:
        total = sum(
            values
        )

    items = []

    for row in rows:
        value = float(
            row.get(value_key)
            or 0
        )

        width = max(
            0,
            value
            / maximum
            * 100,
        )

        label = (
            row.get("name")
            or row.get("warehouse")
            or row.get("warehouse_name")
            or row.get("region")
            or "Не указано"
        )

        share = (
            value
            / total
            * 100
            if total
            else 0
        )

        share_html = (
            f"""
            <span class="bar-share">
                {share:.1f}%
            </span>
            """.replace(".", ",")
            if show_share
            else ""
        )

        items.append(
            f"""
            <div class="bar-row bar-tone-{safe(tone)}">

                <div
                    class="bar-label"
                    title="{safe(label)}"
                >
                    {safe(label)}
                </div>

                <div class="bar-track">
                    <div
                        class="bar-fill"
                        style="width:{width:.2f}%"
                    ></div>
                </div>

                <div class="bar-number">
                    {fmt_number(value)} {safe(suffix)}
                    {share_html}
                </div>

            </div>
            """
        )

    return "".join(
        items
    )


def prose(text: str, dropcap: bool = False) -> str:
    cls = "prose dropcap" if dropcap else "prose"
    return f'<div class="{cls}">{safe(text)}</div>'
