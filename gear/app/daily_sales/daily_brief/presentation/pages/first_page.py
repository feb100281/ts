# gear/app/daily_sales/daily_brief/presentation/pages/first_page.py

from __future__ import annotations

from ...helpers import (
    fmt_money,
    fmt_number,
    fmt_pct,
    number,
)
from ..charts import (
    heat_calendar,
    ytd_revenue_bloomberg_chart,
)
from ..components import (
    comparison_card,
    metric,
    prose,
    safe,
    section,
)
from ..icons import icon


TITLE = "Коммерческий обзор · продажи"
SUBTITLE = "Продажи · спрос · цена · план · запасы"


def _masthead(
    payload: dict,
) -> str:
    return f"""
    <header class="masthead">
        <div>
            <div class="brandline">
                ТРЕНДСЕТТЕР · ЕЖЕДНЕВНЫЙ ВЫПУСК
            </div>

            <h1>{TITLE}</h1>

            <div class="mast-subtitle">
                {SUBTITLE}
            </div>
        </div>

        <div class="issue-meta">
            Выпуск за
            <b>{safe(payload.get("report_date"))}</b>
            <br>
            Сформирован автоматически
        </div>
    </header>
    """


def _daily_kpis(
    payload: dict,
) -> str:
    kpi = (
        payload
        .get("sales", {})
        .get("kpi", {})
    )

    cards = [
        metric(
            "Чистая выручка (до СПП) с НДС",
            fmt_money(
                kpi.get("amount")
            ),
            (
                "Продажи "
                f"{fmt_money(kpi.get('sales_amount'))}"
            ),
            "revenue",
            "accent",
        ),

        metric(
            "Чистые продажи",
            (
                f"{fmt_number(kpi.get('total_net_sales'))} "
                "шт"
            ),
            (
                "Средняя цена "
                f"{fmt_money(kpi.get('avg_price'))}"
            ),
            "units",
        ),

        metric(
            "Возвраты",
            (
                f"{fmt_number(kpi.get('returns_transactions'))} "
                "шт"
            ),
            (
                f"{fmt_money(kpi.get('returns_amount'))} · "
                f"{fmt_pct(kpi.get('returns_rate'))}"
            ),
            "returns",
        ),

        metric(
                "WB реализовал с НДС",
                fmt_money(
                    kpi.get("retail_amount")
                ),
                (
                    "Скидка WB "
                    f"{fmt_pct(kpi.get('wb_discount_percent'))}"
                    " · "
                    f"{fmt_money(kpi.get('wb_discount_amount'))}"
                ),
                "margin",
            ),
    ]

    return (
        '<div class="metric-grid four">'
        + "".join(cards)
        + "</div>"
    )


def _comparisons(
    payload: dict,
) -> str:
    comparison_data = (
        payload
        .get("sales", {})
        .get("comparisons", {})
    )

    daily_cards = "".join(
        comparison_card(
            comparison_data.get(
                key,
                {},
            ),
            card_class="comparison-day",
        )
        for key in (
            "previous_day",
            "previous_month_day",
            "previous_year_day",
        )
    )

    period_cards = "".join(
        comparison_card(
            comparison_data.get(
                key,
                {},
            ),
            card_class="comparison-period",
        )
        for key in (
            "mtd",
            "ytd",
        )
    )

    editorial_text = (
        payload
        .get("editorial", {})
        .get("periods", "")
    )

    body = f"""
    <div class="comparison-layout">
        <div class="comparison-row comparison-row-daily">
            {daily_cards}
        </div>

        <div class="comparison-row comparison-row-periods">
            {period_cards}
        </div>
    </div>

    {prose(
        editorial_text,
        True,
    )}
    """

    return section(
        "СОПОСТАВИМАЯ ДИНАМИКА",
        "День, месяц и год",
        body,
        (
            "Три дневных ориентира и два "
            "накопительных периода"
        ),
        "calendar",
    )


def _heatmap(
    payload: dict,
) -> str:
    rows = (
        payload
        .get("sales", {})
        .get("trend", [])
    )

    return section(
        "КАЛЕНДАРЬ ВЫРУЧКИ",
        "Выручка последних пяти недель",
        heat_calendar(rows),
        "Каждая клетка — один закрытый день (выручка указана до СПП)",
        "calendar",
        "first-page-heatmap-section",
    )


def _ytd_revenue(
    payload: dict,
) -> str:
    rows = (
        payload
        .get("sales", {})
        .get("ytd_daily_rows", [])
    )

    chart = ytd_revenue_bloomberg_chart(
        rows=rows,
        report_date=str(
            payload.get(
                "report_date",
                "",
            )
        ),
    )

    if chart:
        body = f"""
        <img
            class="ytd-bloomberg-chart"
            src="{chart}"
            alt="Накопленная чистая выручка с начала года"
        >
        """
    else:
        body = """
        <div class="ytd-empty">
            Недостаточно данных для накопительного графика.
        </div>
        """

    return section(
        "ДИНАМИКА ГОДА",
        "Накопленная выручка",
        body,
        (
            "Текущий год и сопоставимый "
            "период прошлого года"
        ),
        "trend",
        "ytd-compact-section",
    )


def _leader_chart(
    rows: list[dict],
) -> str:
    """
    Горизонтальный рейтинг брендов или категорий.

    Для каждой позиции показываются:
    - чистая выручка с учётом возвратов;
    - количество положительных продаж;
    - средняя цена положительной продажи.
    """

    rows = list(
        rows or []
    )[:3]

    if not rows:
        return """
        <div class="empty">
            Нет данных
        </div>
        """

    maximum = max(
        number(
            row.get("revenue")
        )
        for row in rows
    ) or 1

    items: list[str] = []

    for row in rows:
        name = safe(
            row.get("name")
            or "Не указано"
        )

        revenue = number(
            row.get("revenue")
        )

        sold_units = number(
            row.get("sold_units")
        )

        avg_price = number(
            row.get("avg_price")
        )

        width = max(
            0,
            min(
                revenue / maximum * 100,
                100,
            ),
        )

        items.append(
            f"""
            <div class="leader-row">
                <div class="leader-row-name">
                    {name}
                </div>

                <div class="leader-row-main">
                    <div class="leader-row-track">
                        <div
                            class="leader-row-fill"
                            style="width:{width:.2f}%"
                        ></div>
                    </div>

                    <div class="leader-row-revenue">
                        {fmt_money(revenue)}
                    </div>
                </div>

                <div class="leader-row-meta">
                    <span>
                        Продано
                        <b>{fmt_number(sold_units)} шт</b>
                    </span>

                    <span class="leader-row-meta-divider">
                        ·
                    </span>

                    <span>
                        Средняя цена
                        <b>{fmt_money(avg_price)}</b>
                    </span>
                </div>
            </div>
            """
        )

    return (
        '<div class="leader-chart">'
        + "".join(items)
        + "</div>"
    )


def _leader_section(
    payload: dict,
    *,
    key: str,
    title: str,
    kicker: str,
    icon_name: str,
) -> str:
    rows = (
        payload
        .get("sales", {})
        .get(key, [])
    )

    return section(
        kicker,
        title,
        _leader_chart(
            rows
        ),
        (
            "Чистая выручка · количество продаж · "
            "средняя цена"
        ),
        icon_name,
        "first-page-leader-section",
    )


def _leaders_row(
    payload: dict,
) -> str:
    brands = _leader_section(
        payload,
        key="top_brands",
        title="Бренды дня",
        kicker="КТО СДЕЛАЛ РЕЗУЛЬТАТ",
        icon_name="brand",
    )

    categories = _leader_section(
        payload,
        key="top_categories",
        title="Категории дня",
        kicker="ЧТО ПОКУПАЛИ",
        icon_name="category",
    )

    return f"""
    <div class="first-page-leaders">
        <div class="first-page-leader-column">
            {brands}
        </div>

        <div class="first-page-leader-column">
            {categories}
        </div>
    </div>
    """


def build_first_page(
    payload: dict,
) -> str:
    editorial = payload.get(
        "editorial",
        {},
    )

    return f"""
    <!-- =============================================================
         СТРАНИЦА 1 — КОММЕРЧЕСКИЙ РЕЗУЛЬТАТ
         ============================================================= -->

    <div class="page first-page">
        {_masthead(payload)}

        <div class="lead">
            <div class="lead-icon">
                {icon("newspaper", 38)}
            </div>

            <div class="lead-text">
                {editorial.get("intro", "")}
            </div>
        </div>

        {_daily_kpis(payload)}

        <div class="big-quote">
            <p>{safe(editorial.get("lead", ""))}</p>
        </div>

        <div class="first-page-analysis">
            <div class="first-page-analysis-left">
                {_comparisons(payload)}
            </div>

            <div class="first-page-analysis-right">
                {_heatmap(payload)}

                {_ytd_revenue(payload)}
            </div>
        </div>

        {_leaders_row(payload)}

        <div class="footer-note">
            <span>
                Источник: WB и управленческий контур
            </span>

            <span>
                Данные на закрытую дату
            </span>
        </div>
    </div>
    """