# gear/app/daily_sales/daily_brief/presentation/pages/price_page.py

from __future__ import annotations

from html import escape

import pandas as pd
import numpy as np


from ...helpers import fmt_money, number
from ..components import safe
from .demand_charts import (
    brand_price_scenario_chart,
)


TITLE = "Коммерческий обзор · цена"
SUBTITLE = "ЦЕНА · СКИДКА WB · ОБЪЁМ · МАРЖА"


# =============================================================================
# COLORS
# =============================================================================

NAVY = "#14213D"
MUTED = "#667085"
BORDER = "#D7DCE2"
GRID = "#E8EBEF"

CORAL = "#E85D75"
CORAL_SOFT = "#FFF1F4"

GREEN = "#16805E"
GREEN_SOFT = "#E9F5EF"

PURPLE = "#8067AB"
PURPLE_SOFT = "#F2EDF7"

YELLOW = "#E9B949"
YELLOW_SOFT = "#FFF8DF"

PAPER = "#FFFDF7"


# =============================================================================
# INLINE CSS
# =============================================================================

PRICE_PAGE_CSS = r"""
<style>

/* ======================================================================
   PRICE PAGE
   ====================================================================== */

.price-page {
    --p-navy: #14213D;
    --p-muted: #667085;
    --p-border: #D7DCE2;
    --p-grid: #E8EBEF;

    --p-coral: #E85D75;
    --p-coral-soft: #FFF1F4;

    --p-green: #16805E;
    --p-green-soft: #E9F5EF;

    --p-purple: #8067AB;
    --p-purple-soft: #F2EDF7;

    --p-yellow: #E9B949;
    --p-yellow-soft: #FFF8DF;
}


/* KPI */

.price-kpi-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 7px;

    margin-bottom: 8px;
}

.price-kpi {
    min-height: 71px;
    padding: 8px 9px;

    border: 1px solid var(--p-border);
    border-top: 3px solid var(--p-navy);

    background: #FFFDF7;
}

.price-kpi.discount {
    border-top-color: var(--p-coral);
}

.price-kpi.buyer {
    border-top-color: var(--p-purple);
}

.price-kpi.qty {
    border-top-color: var(--p-green);
}

.price-kpi.margin {
    border-top-color: var(--p-yellow);
}

.price-kpi-label {
    color: var(--p-muted);

    font-size: 6.6px;
    font-weight: 800;
    letter-spacing: .65px;
    text-transform: uppercase;
}

.price-kpi-value {
    margin-top: 5px;

    font-family: Georgia, serif;
    font-size: 17px;
    line-height: 1;
    font-weight: 800;
    white-space: nowrap;
}

.price-kpi-note {
    display: flex;
    justify-content: space-between;
    gap: 5px;

    margin-top: 6px;

    color: var(--p-muted);
    font-size: 6.1px;
}

.price-kpi-change {
    flex-shrink: 0;
    font-weight: 800;
}

.price-kpi-change.up {
    color: var(--p-green);
}

.price-kpi-change.down {
    color: #BD3D59;
}


/* Common */

.price-kicker {
    color: var(--p-coral);

    font-size: 6.5px;
    line-height: 1;
    font-weight: 800;
    letter-spacing: 1px;
    text-transform: uppercase;
}

.price-block-title {
    margin-top: 3px;

    color: var(--p-navy);

    font-family: Georgia, serif;
    font-size: 16px;
    line-height: 1.04;
    font-weight: 800;
}

.price-block-title.small {
    font-size: 14px;
}

.price-block-subtitle {
    margin-top: 3px;

    color: var(--p-muted);
    font-size: 6.4px;
}

.price-head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 10px;

    margin-bottom: 5px;
}

.price-caption {
    color: var(--p-muted);
    font-size: 6px;
    text-align: right;
}


/* ================================================================
   TOP STORY
   ================================================================ */

.price-story-grid {
    display: grid;
    grid-template-columns: .78fr 1.42fr;
    gap: 8px;

    margin-bottom: 8px;
}

.price-editorial {
    min-height: 157px;

    padding: 10px 11px;

    background: var(--p-coral-soft);
    border-left: 5px solid var(--p-coral);
}

.price-editorial.positive {
    background: var(--p-green-soft);
    border-left-color: var(--p-green);
}

.price-editorial.neutral {
    background: #F4F0E6;
    border-left-color: var(--p-navy);
}

.price-editorial-title {
    margin-top: 6px;

    font-family: Georgia, serif;
    font-size: 18px;
    line-height: 1.04;
    font-weight: 800;
}

.price-editorial-copy {
    margin-top: 8px;

    color: #354052;

    font-family: Georgia, serif;
    font-size: 8.4px;
    line-height: 1.45;

    text-align: justify;
    hyphens: auto;
}

.price-editorial-metrics {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 5px;

    margin-top: 9px;
}

.price-editorial-metrics > div {
    padding: 6px 7px;

    background: rgba(255,255,255,.58);
}

.price-editorial-metrics span {
    display: block;

    color: var(--p-muted);
    font-size: 5.7px;
    text-transform: uppercase;
}

.price-editorial-metrics b {
    display: block;
    margin-top: 2px;

    font-family: Georgia, serif;
    font-size: 10px;
}


/* ================================================================
   PRICE / DISCOUNT CHART
   ================================================================ */

.price-history-card {
    min-height: 157px;

    padding: 8px 9px 4px;

    border-top: 3px solid var(--p-navy);
    border-bottom: 1px solid var(--p-border);
}

.price-history-chart svg {
    display: block;
    width: 100%;
    height: 121px;
}


/* ================================================================
   DISCOUNT EFFECT
   ================================================================ */

.price-effect-card {
    margin-bottom: 8px;

    padding: 7px 9px 6px;

    border-top: 3px solid var(--p-navy);
    border-bottom: 1px solid var(--p-border);
}

.price-effect-grid {
    display: grid;
    grid-template-columns: 1.35fr .65fr;
    gap: 9px;

    margin-top: 5px;
}

.price-effect-chart svg {
    display: block;
    width: 100%;
    height: 174px;
}

.price-effect-summary {
    padding: 8px 9px;

    background: #F8F5ED;
    border-left: 3px solid var(--p-yellow);
}

.price-effect-summary-title {
    font-family: Georgia, serif;
    font-size: 13px;
    line-height: 1.07;
    font-weight: 800;
}

.price-effect-summary-copy {
    margin-top: 6px;

    color: #4B5563;

    font-size: 6.7px;
    line-height: 1.42;
}

.price-effect-stat {
    margin-top: 8px;
    padding-top: 7px;

    border-top: 1px solid var(--p-border);
}

.price-effect-stat span {
    color: var(--p-muted);
    font-size: 5.8px;
}

.price-effect-stat b {
    display: block;
    margin-top: 2px;

    font-family: Georgia, serif;
    font-size: 13px;
}


/* ================================================================
   MODEL
   ================================================================ */

.price-model {
    margin-bottom: 8px;
    padding-top: 6px;

    border-top: 3px solid var(--p-navy);
}

.price-model-focus {
    display: grid;
    grid-template-columns: 1.45fr .55fr;
    gap: 8px;

    margin-top: 5px;
}

.price-model-chart {
    min-width: 0;
}

.price-model-chart svg {
    display: block;
    width: 100%;
    height: 184px;
}

.price-model-summary {
    padding: 8px 9px;

    background: var(--p-purple-soft);
    border-left: 4px solid var(--p-purple);
}

.price-model-brand {
    font-family: Georgia, serif;
    font-size: 17px;
    line-height: 1;
    font-weight: 800;
}

.price-model-action {
    margin-top: 6px;

    color: var(--p-purple);

    font-size: 7px;
    font-weight: 800;
    letter-spacing: .7px;
    text-transform: uppercase;
}

.price-model-price {
    display: grid;
    grid-template-columns: 1fr auto 1fr;
    gap: 5px;
    align-items: end;

    margin-top: 9px;
    padding: 7px;

    background: rgba(255,255,255,.58);
}

.price-model-price span {
    display: block;
    color: var(--p-muted);
    font-size: 5.6px;
    text-transform: uppercase;
}

.price-model-price b {
    display: block;
    margin-top: 2px;

    font-family: Georgia, serif;
    font-size: 11px;
}

.price-model-price .arrow {
    padding-bottom: 2px;
    color: var(--p-muted);
}

.price-model-metrics {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 5px;

    margin-top: 6px;
}

.price-model-metrics > div {
    padding: 5px 6px;

    border: 1px solid rgba(128,103,171,.18);
    background: rgba(255,255,255,.54);
}

.price-model-metrics span {
    display: block;
    color: var(--p-muted);
    font-size: 5.5px;
}

.price-model-metrics b {
    display: block;
    margin-top: 2px;

    font-size: 8.5px;
}


/* ================================================================
   BRAND TABLE
   ================================================================ */

.price-brand-table {
    margin-top: 6px;
}

.price-brand-row {
    display: grid;

    grid-template-columns:
        1.3fr
        .85fr
        .85fr
        .72fr
        .72fr
        .72fr
        .82fr;

    min-height: 20px;

    border-bottom: 1px solid #E8EBEF;
}

.price-brand-row > div {
    display: flex;
    align-items: center;

    min-width: 0;
    padding: 4px 5px;

    font-size: 5.9px;
}

.price-brand-row.header {
    min-height: 18px;

    background: #F4F0E6;

    color: var(--p-muted);
    font-weight: 800;
    text-transform: uppercase;
}

.price-brand-row .brand {
    color: var(--p-navy);
    font-weight: 800;
}


/* ================================================================
   DISCLAIMER
   ================================================================ */

.price-disclaimer {
    margin-top: 6px;
    padding: 6px 7px;

    background: #F8F5ED;
    border-top: 2px solid var(--p-yellow);

    color: #667085;

    font-size: 5.8px;
    line-height: 1.3;
}

.price-footer {
    display: flex;
    justify-content: space-between;

    margin-top: 5px;

    color: #7A8492;
    font-size: 5.6px;
}

</style>
"""


# =============================================================================
# FORMATTERS
# =============================================================================

def _money_short(
    value,
) -> str:
    value = number(
        value
    )

    sign = (
        "−"
        if value < 0
        else ""
    )

    absolute = abs(
        value
    )

    if absolute >= 1_000_000:
        return (
            f"{sign}"
            f"{absolute / 1_000_000:.1f}"
            .replace(".", ",")
            + "\u00A0млн\u00A0₽"
        )

    if absolute >= 1_000:
        return (
            f"{sign}"
            f"{absolute / 1_000:.1f}"
            .replace(".", ",")
            + "\u00A0тыс.\u00A0₽"
        )

    return fmt_money(
        value
    )


def _pct(
    value,
    *,
    signed=False,
) -> str:
    value = number(
        value
    )

    sign = ""

    if signed:
        sign = (
            "+"
            if value > 0
            else "−"
            if value < 0
            else ""
        )

    elif value < 0:
        sign = "−"

    return (
        f"{sign}{abs(value):.1f}%"
        .replace(".", ",")
    )


def _pp(
    value,
) -> str:
    value = number(
        value
    )

    sign = (
        "+"
        if value > 0
        else "−"
        if value < 0
        else ""
    )

    return (
        f"{sign}{abs(value):.1f} п.п."
        .replace(".", ",")
    )


def _change(
    current,
    previous,
) -> float | None:
    current = number(
        current
    )

    previous = number(
        previous
    )

    if previous == 0:
        return None

    return (
        current
        / previous
        - 1
    ) * 100


def _change_span(
    value,
) -> str:
    if value is None:
        return ""

    value = number(
        value
    )

    css = (
        "up"
        if value > 0
        else "down"
        if value < 0
        else ""
    )

    arrow = (
        "▲"
        if value > 0
        else "▼"
        if value < 0
        else "•"
    )

    return (
        f'<span class="price-kpi-change {css}">'
        f"{arrow} {_pct(abs(value))}"
        "</span>"
    )


# =============================================================================
# DATA ACCESS
# =============================================================================

def _price_data(
    payload: dict,
) -> dict:
    return (
        payload.get(
            "price_analysis_page",
            {},
        )
        or {}
    )


# =============================================================================
# HEADER
# =============================================================================

def _masthead(
    payload: dict,
) -> str:
    return f"""
    <header class="masthead">

        <div>
            <div class="brandline">
                ТРЕНДСЕТТЕР · ЦЕНОВАЯ АНАЛИТИКА
            </div>

            <h1>
                {TITLE}
            </h1>

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


# =============================================================================
# KPI
# =============================================================================

def _kpi(
    label,
    value,
    note,
    change,
    tone,
) -> str:
    return f"""
    <article class="price-kpi {safe(tone)}">

        <div class="price-kpi-label">
            {safe(label)}
        </div>

        <div class="price-kpi-value">
            {safe(value)}
        </div>

        <div class="price-kpi-note">
            <span>{safe(note)}</span>
            {_change_span(change)}
        </div>

    </article>
    """


def _kpi_row(
    payload: dict,
) -> str:
    data = _price_data(
        payload
    )

    recent = data.get(
        "recent_14",
        {},
    )

    previous = data.get(
        "previous_14",
        {},
    )

    discount_change = (
        number(recent.get("discount_pct"))
        - number(previous.get("discount_pct"))
    )

    return f"""
    <div class="price-kpi-grid">

        {_kpi(
            "Средняя цена до СПП · 14 дней",
            _money_short(
                recent.get("seller_avg_price")
            ),
            "на единицу",
            _change(
                recent.get("seller_avg_price"),
                previous.get("seller_avg_price"),
            ),
            "buyer",
        )}

        {_kpi(
            "Цена покупателя · 14 дней",
            _money_short(
                recent.get("buyer_avg_price")
            ),
            "фактическая реализация WB",
            _change(
                recent.get("buyer_avg_price"),
                previous.get("buyer_avg_price"),
            ),
            "buyer",
        )}

        {_kpi(
            "Эффективная скидка WB",
            _pct(
                recent.get("discount_pct")
            ),
            (
                "разница "
                + _money_short(
                    recent.get("discount_amount")
                )
            ),
            discount_change,
            "discount",
        )}

        {_kpi(
            "Управленческая маржа",
            _pct(
                recent.get("margin_pct")
            ),
            "до распределяемых расходов WB",
            (
                number(recent.get("margin_pct"))
                - number(previous.get("margin_pct"))
            ),
            "margin",
        )}

    </div>
    """


# =============================================================================
# PRICE HISTORY SVG
# =============================================================================

def _price_history_chart(
    rows: list[dict],
) -> str:
    frame = pd.DataFrame(
        rows or []
    )

    if frame.empty:
        return ""

    for column in (
        "date_from",
        "seller_avg_price",
        "buyer_avg_price",
        "discount_pct",
    ):
        if column not in frame:
            return ""

    frame["date_from"] = pd.to_datetime(
        frame["date_from"],
        errors="coerce",
    )

    for column in (
        "seller_avg_price",
        "buyer_avg_price",
        "discount_pct",
    ):
        frame[column] = pd.to_numeric(
            frame[column],
            errors="coerce",
        )

    frame = (
        frame
        .dropna(
            subset=["date_from"]
        )
        .sort_values("date_from")
        .tail(90)
        .reset_index(drop=True)
    )

    if len(frame) < 2:
        return ""

    frame["seller_ma"] = (
        frame["seller_avg_price"]
        .rolling(
            7,
            min_periods=3,
        )
        .mean()
    )

    frame["buyer_ma"] = (
        frame["buyer_avg_price"]
        .rolling(
            7,
            min_periods=3,
        )
        .mean()
    )

    valid = frame[
        frame["seller_ma"].notna()
        & frame["buyer_ma"].notna()
    ].copy()

    if len(valid) < 2:
        return ""

    width = 720
    height = 180

    left = 44
    right = 18
    top = 28
    bottom = 28

    plot_width = (
        width
        - left
        - right
    )

    plot_height = (
        height
        - top
        - bottom
    )

    values = pd.concat(
        [
            valid["seller_ma"],
            valid["buyer_ma"],
        ]
    )

    y_min = float(
        values.min()
    )

    y_max = float(
        values.max()
    )

    padding = max(
        (
            y_max
            - y_min
        ) * .12,
        50,
    )

    y_min -= padding
    y_max += padding

    span = (
        y_max
        - y_min
    ) or 1

    def x_pos(
        index,
    ):
        return (
            left
            + index
            / max(
                len(valid) - 1,
                1,
            )
            * plot_width
        )

    def y_pos(
        value,
    ):
        return (
            top
            + (
                y_max
                - value
            )
            / span
            * plot_height
        )

    seller_points = []
    buyer_points = []

    area_points_top = []
    area_points_bottom = []

    for index, row in valid.iterrows():
        local = (
            valid.index.get_loc(
                index
            )
        )

        x = x_pos(
            local
        )

        seller_y = y_pos(
            row["seller_ma"]
        )

        buyer_y = y_pos(
            row["buyer_ma"]
        )

        seller_points.append(
            f"{x:.1f},{seller_y:.1f}"
        )

        buyer_points.append(
            f"{x:.1f},{buyer_y:.1f}"
        )

        area_points_top.append(
            f"{x:.1f},{seller_y:.1f}"
        )

        area_points_bottom.append(
            f"{x:.1f},{buyer_y:.1f}"
        )

    area_polygon = (
        " ".join(
            area_points_top
            + list(
                reversed(
                    area_points_bottom
                )
            )
        )
    )

    html = [
        f"""
        <svg
            viewBox="0 0 {width} {height}"
            xmlns="http://www.w3.org/2000/svg"
        >

            <polygon
                points="{area_polygon}"
                fill="{CORAL_SOFT}"
                opacity=".75"
            />

            <polyline
                points="{" ".join(seller_points)}"
                fill="none"
                stroke="{NAVY}"
                stroke-width="2.4"
                stroke-linecap="round"
                stroke-linejoin="round"
            />

            <polyline
                points="{" ".join(buyer_points)}"
                fill="none"
                stroke="{PURPLE}"
                stroke-width="2.4"
                stroke-linecap="round"
                stroke-linejoin="round"
            />

            <line
                x1="{left}"
                y1="12"
                x2="{left + 18}"
                y2="12"
                stroke="{NAVY}"
                stroke-width="2.4"
            />

            <text
                x="{left + 24}"
                y="15"
                fill="{NAVY}"
                font-family="Arial"
                font-size="6"
                font-weight="700"
            >
                цена до СПП
            </text>

            <line
                x1="{left + 118}"
                y1="12"
                x2="{left + 136}"
                y2="12"
                stroke="{PURPLE}"
                stroke-width="2.4"
            />

            <text
                x="{left + 142}"
                y="15"
                fill="{PURPLE}"
                font-family="Arial"
                font-size="6"
                font-weight="700"
            >
                цена покупателя
            </text>

            <text
                x="{width - right}"
                y="15"
                text-anchor="end"
                fill="{MUTED}"
                font-family="Arial"
                font-size="5.7"
            >
                область между линиями — скидка WB
            </text>
        """
    ]

    for fraction in (
        .25,
        .50,
        .75,
    ):
        y = (
            top
            + plot_height
            * fraction
        )

        html.append(
            f"""
            <line
                x1="{left}"
                y1="{y:.1f}"
                x2="{width - right}"
                y2="{y:.1f}"
                stroke="{GRID}"
                stroke-width="1"
            />
            """
        )

    labels = sorted(
        {
            0,
            len(valid) // 2,
            len(valid) - 1,
        }
    )

    for index in labels:
        row = valid.iloc[
            index
        ]

        html.append(
            f"""
            <text
                x="{x_pos(index):.1f}"
                y="{height - 7}"
                text-anchor="middle"
                fill="{MUTED}"
                font-family="Arial"
                font-size="5.8"
            >
                {row["date_from"].strftime("%d.%m")}
            </text>
            """
        )

    html.append(
        "</svg>"
    )

    return "".join(
        html
    )


# =============================================================================
# DISCOUNT VS QTY SVG
# =============================================================================

def _discount_effect_chart(
    rows: list[dict],
) -> str:
    frame = pd.DataFrame(
        rows or []
    )

    if frame.empty:
        return ""

    required = (
        "discount_pct",
        "total_net_sales",
    )

    for column in required:
        if column not in frame:
            return ""

        frame[column] = pd.to_numeric(
            frame[column],
            errors="coerce",
        )

    frame = frame[
        frame["discount_pct"].notna()
        & frame["total_net_sales"].notna()
        & (frame["total_net_sales"] > 0)
    ].copy()

    if len(frame) < 5:
        return ""

    width = 720
    height = 205

    left = 43
    right = 18
    top = 25
    bottom = 34

    plot_width = (
        width
        - left
        - right
    )

    plot_height = (
        height
        - top
        - bottom
    )

    x_min = float(
        frame["discount_pct"].min()
    )

    x_max = float(
        frame["discount_pct"].max()
    )

    y_min = 0

    y_max = float(
        frame["total_net_sales"]
        .quantile(.98)
    )

    if y_max <= 0:
        return ""

    x_pad = max(
        (
            x_max
            - x_min
        ) * .08,
        1,
    )

    x_min -= x_pad
    x_max += x_pad

    x_span = (
        x_max
        - x_min
    ) or 1

    y_span = (
        y_max
        - y_min
    ) or 1

    def x_pos(
        value,
    ):
        return (
            left
            + (
                value
                - x_min
            )
            / x_span
            * plot_width
        )

    def y_pos(
        value,
    ):
        value = max(
            y_min,
            min(
                value,
                y_max,
            ),
        )

        return (
            top
            + (
                y_max
                - value
            )
            / y_span
            * plot_height
        )

    # ================================================================
    # ТОЧКИ
    # ================================================================

    points = []

    for _, row in frame.iterrows():
        x = x_pos(
            number(
                row["discount_pct"]
            )
        )

        y = y_pos(
            number(
                row["total_net_sales"]
            )
        )

        points.append(
            f"""
            <circle
                cx="{x:.1f}"
                cy="{y:.1f}"
                r="3.2"
                fill="{PURPLE}"
                opacity=".55"
            />
            """
        )

    # ================================================================
    # КОРРЕЛЯЦИЯ
    # ================================================================

    corr = (
        frame[
            [
                "discount_pct",
                "total_net_sales",
            ]
        ]
        .corr()
        .iloc[0, 1]
    )

    corr = (
        float(corr)
        if pd.notna(corr)
        else 0
    )

    # ================================================================
    # ЛИНЕЙНЫЙ ТРЕНД
    # ================================================================

    trend_line = ""

    x_values = (
        frame["discount_pct"]
        .astype(float)
    )

    y_values = (
        frame["total_net_sales"]
        .astype(float)
    )

    if (
        len(frame) >= 2
        and x_values.nunique() > 1
    ):
        slope, intercept = np.polyfit(
            x_values,
            y_values,
            1,
        )

        # Линию строим по фактическому диапазону X,
        # без искусственного padding.
        trend_x1 = float(
            frame["discount_pct"].min()
        )

        trend_x2 = float(
            frame["discount_pct"].max()
        )

        trend_y1 = (
            slope * trend_x1
            + intercept
        )

        trend_y2 = (
            slope * trend_x2
            + intercept
        )

        trend_line = f"""
        <line
            x1="{x_pos(trend_x1):.1f}"
            y1="{y_pos(trend_y1):.1f}"
            x2="{x_pos(trend_x2):.1f}"
            y2="{y_pos(trend_y2):.1f}"
            stroke="{CORAL}"
            stroke-width="2.2"
            stroke-dasharray="7 5"
            opacity=".95"
        />
        """

    # ================================================================
    # SVG
    # ================================================================

    return f"""
    <svg
        viewBox="0 0 {width} {height}"
        xmlns="http://www.w3.org/2000/svg"
    >

        <!-- Оси -->

        <line
            x1="{left}"
            y1="{top + plot_height}"
            x2="{width - right}"
            y2="{top + plot_height}"
            stroke="{BORDER}"
        />

        <line
            x1="{left}"
            y1="{top}"
            x2="{left}"
            y2="{top + plot_height}"
            stroke="{BORDER}"
        />

        <!-- Горизонтальные направляющие -->

        <line
            x1="{left}"
            y1="{top + plot_height * 0.25:.1f}"
            x2="{width - right}"
            y2="{top + plot_height * 0.25:.1f}"
            stroke="{GRID}"
            stroke-width="1"
        />

        <line
            x1="{left}"
            y1="{top + plot_height * 0.50:.1f}"
            x2="{width - right}"
            y2="{top + plot_height * 0.50:.1f}"
            stroke="{GRID}"
            stroke-width="1"
        />

        <line
            x1="{left}"
            y1="{top + plot_height * 0.75:.1f}"
            x2="{width - right}"
            y2="{top + plot_height * 0.75:.1f}"
            stroke="{GRID}"
            stroke-width="1"
        />

        <!-- Точки -->

        {"".join(points)}

        <!-- Линейный тренд -->

        {trend_line}

        <!-- Верхняя подпись -->

        <text
            x="{left}"
            y="14"
            fill="{NAVY}"
            font-family="Arial"
            font-size="6"
            font-weight="700"
        >
            один маркер — один закрытый день
        </text>

        <!-- Легенда тренда -->

        <line
            x1="{left + 185}"
            y1="12"
            x2="{left + 207}"
            y2="12"
            stroke="{CORAL}"
            stroke-width="2"
            stroke-dasharray="7 5"
        />

        <text
            x="{left + 213}"
            y="15"
            fill="{CORAL}"
            font-family="Arial"
            font-size="5.8"
            font-weight="700"
        >
            линейный тренд
        </text>

        <!-- Корреляция -->

        <text
            x="{width - right}"
            y="14"
            text-anchor="end"
            fill="{MUTED}"
            font-family="Arial"
            font-size="5.8"
        >
            корреляция скидки и количества: {corr:.2f}
        </text>

        <!-- X title -->

        <text
            x="{left + plot_width / 2}"
            y="{height - 4}"
            text-anchor="middle"
            fill="{NAVY}"
            font-family="Arial"
            font-size="6"
            font-weight="700"
        >
            эффективная скидка WB, %
        </text>

        <!-- Y title -->

        <text
            x="8"
            y="{top + plot_height / 2}"
            transform="rotate(-90 8 {top + plot_height / 2})"
            text-anchor="middle"
            fill="{NAVY}"
            font-family="Arial"
            font-size="6"
            font-weight="700"
        >
            продано, ед.
        </text>

    </svg>
    """
# =============================================================================
# EDITORIAL
# =============================================================================

def _editorial(
    payload: dict,
) -> str:
    data = _price_data(
        payload
    )

    recent = data.get(
        "recent_14",
        {},
    )

    previous = data.get(
        "previous_14",
        {},
    )

    discount = number(
        recent.get(
            "discount_pct"
        )
    )

    previous_discount = number(
        previous.get(
            "discount_pct"
        )
    )

    qty_change = _change(
        recent.get("qty"),
        previous.get("qty"),
    )

    discount_delta = (
        discount
        - previous_discount
    )

    if (
        discount_delta > 1
        and number(qty_change) < 0
    ):
        title = (
            "Более глубокая скидка "
            "не сопровождается ростом объёма"
        )

        copy = (
            f"Эффективная скидка WB за последние "
            f"14 дней увеличилась на "
            f"{_pp(discount_delta)}, при этом "
            f"количество проданных единиц изменилось "
            f"на {_pct(qty_change, signed=True)}. "
            f"Такой результат не подтверждает, что "
            f"дополнительное углубление скидки само "
            f"по себе создаёт необходимый прирост продаж."
        )

        tone = ""

    elif (
        discount_delta > 1
        and number(qty_change) > 0
    ):
        title = (
            "Рост скидки сопровождается "
            "увеличением объёма продаж"
        )

        copy = (
            f"Эффективная скидка выросла "
            f"на {_pp(discount_delta)}, одновременно "
            f"количество проданных единиц изменилось "
            f"на {_pct(qty_change, signed=True)}. "
            f"Связь требует проверки на уровне брендов: "
            f"часть прироста может объясняться товарным "
            f"миксом, наличием или продвижением."
        )

        tone = "positive"

    elif (
        discount_delta < -1
        and number(qty_change) >= 0
    ):
        title = (
            "Скидка сократилась без потери "
            "физического объёма"
        )

        copy = (
            f"Эффективная скидка снизилась "
            f"на {_pp(abs(discount_delta))}, "
            f"а количество проданных единиц "
            f"не уменьшилось. Такой режим особенно "
            f"интересен с точки зрения защиты цены "
            f"и маржинальности."
        )

        tone = "positive"

    else:
        title = (
            "Скидка и объём пока не дают "
            "однозначного сигнала"
        )

        copy = (
            f"За последние 14 дней эффективная скидка "
            f"составила {_pct(discount)}. "
            f"Изменение относительно предыдущего периода "
            f"равно {_pp(discount_delta)}. "
            f"Для решения о ценовом шаге важнее смотреть "
            f"не только на общий уровень скидки, но и "
            f"на реакцию отдельных брендов и маржу."
        )

        tone = "neutral"

    return f"""
    <section class="price-editorial {safe(tone)}">

        <div class="price-kicker">
            ГЛАВНЫЙ ЦЕНОВОЙ СИГНАЛ
        </div>

        <div class="price-editorial-title">
            {safe(title)}
        </div>

        <div class="price-editorial-copy">
            {safe(copy)}
        </div>

        <div class="price-editorial-metrics">

            <div>
                <span>Скидка · 14 дней</span>
                <b>{_pct(discount)}</b>
            </div>

            <div>
                <span>Изменение скидки</span>
                <b>{_pp(discount_delta)}</b>
            </div>

            <div>
                <span>Изменение количества</span>
                <b>{_pct(qty_change, signed=True)}</b>
            </div>

            <div>
                <span>Маржа · 14 дней</span>
                <b>{_pct(recent.get("margin_pct"))}</b>
            </div>

        </div>

    </section>
    """


# =============================================================================
# HISTORY
# =============================================================================

def _history_block(
    payload: dict,
) -> str:
    data = _price_data(
        payload
    )

    chart = _price_history_chart(
        data.get(
            "rows",
            [],
        )
    )

    if not chart:
        chart = (
            '<div class="empty">'
            "Недостаточно данных"
            "</div>"
        )

    return f"""
    <section class="price-history-card">

        <div class="price-head">

            <div>
                <div class="price-kicker">
                    ЦЕНА ПОКУПАТЕЛЯ
                </div>

                <div class="price-block-title small">
                    Что происходит между ценой до СПП и реализацией WB
                </div>

                <div class="price-block-subtitle">
                    7-дневные средние · последние 90 дней
                </div>
            </div>

        </div>

        <div class="price-history-chart">
            {chart}
        </div>

    </section>
    """


# =============================================================================
# EFFECT
# =============================================================================

def _effect_block(
    payload: dict,
) -> str:
    data = _price_data(
        payload
    )

    rows = data.get(
        "rows",
        [],
    )

    chart = (
        _discount_effect_chart(
            rows
        )
    )

    frame = pd.DataFrame(
        rows or []
    )

    corr = 0

    if (
        not frame.empty
        and "discount_pct" in frame
        and "total_net_sales" in frame
    ):
        x = pd.to_numeric(
            frame["discount_pct"],
            errors="coerce",
        )

        y = pd.to_numeric(
            frame["total_net_sales"],
            errors="coerce",
        )

        valid = (
            x.notna()
            & y.notna()
        )

        if (
            valid.sum() >= 5
            and x[valid].nunique() > 1
            and y[valid].nunique() > 1
        ):
            corr = float(
                x[valid].corr(
                    y[valid]
                )
            )

    absolute = abs(
        corr
    )

    if absolute < .20:
        label = (
            "явной связи не видно"
        )

        copy = (
            "Изменение общей скидки по дням "
            "почти не связано с изменением количества. "
            "Решения лучше принимать на уровне брендов "
            "и конкретных ценовых зон."
        )

    elif absolute < .45:
        label = (
            "связь слабая"
        )

        copy = (
            "Между скидкой и количеством присутствует "
            "слабая статистическая связь. Она не позволяет "
            "считать скидку главным объяснением динамики."
        )

    else:
        direction = (
            "прямая"
            if corr > 0
            else "обратная"
        )

        label = (
            f"{direction} связь"
        )

        copy = (
            "Связь заметна, однако это не причинный эффект: "
            "одновременно меняются наличие, товарный микс, "
            "продвижение и сезонность."
        )

    return f"""
    <section class="price-effect-card">

        <div class="price-head">

            <div>
                <div class="price-kicker">
                    ОТДАЧА ОТ СКИДКИ
                </div>

                <div class="price-block-title">
                    Сопровождается ли скидка большим количеством продаж
                </div>

                <div class="price-block-subtitle">
                    один день — одна точка · последние 90 дней
                </div>
            </div>

        </div>

        <div class="price-effect-grid">

            <div class="price-effect-chart">
                {chart}
            </div>

            <aside class="price-effect-summary">

                <div class="price-kicker">
                    НАБЛЮДАЕМАЯ СВЯЗЬ
                </div>

                <div class="price-effect-summary-title">
                    {safe(label)}
                </div>

                <div class="price-effect-summary-copy">
                    {safe(copy)}
                </div>

                <div class="price-effect-stat">
                    <span>
                        Корреляция скидки и количества
                    </span>

                    <b>
                        {corr:.2f}
                    </b>
                </div>

            </aside>

        </div>

    </section>
    """


# =============================================================================
# PRICE MODEL
# =============================================================================

def _focus_brand(
    payload: dict,
) -> dict | None:
    brands = (
        payload
        .get("sales", {})
        .get("brand_price_analysis", {})
        .get("brands", [])
    )

    candidates = []

    for row in brands:
        balance_data = (
            row.get("balance")
            or {}
        )

        if not balance_data.get(
            "available"
        ):
            continue

        confidence = (
            row.get("confidence")
            or ""
        )

        if confidence not in (
            "Высокая",
            "Средняя",
        ):
            continue

        balance = (
            balance_data.get("balance")
            or {}
        )

        candidates.append(
            (
                row,
                abs(
                    number(
                        balance.get(
                            "price_change_pct"
                        )
                    )
                ),
                number(
                    row.get(
                        "revenue_14d"
                    )
                ),
            )
        )

    if not candidates:
        return None

    candidates.sort(
        key=lambda item: (
            item[1],
            item[2],
        ),
        reverse=True,
    )

    return (
        candidates[0][0]
    )


def _model_block(
    payload: dict,
) -> str:
    focus = _focus_brand(
        payload
    )

    if focus is None:
        return """
        <section class="price-model">

            <div class="price-kicker">
                ЦЕНОВОЙ ПОТЕНЦИАЛ
            </div>

            <div class="price-block-title">
                Сценарная модель по брендам
            </div>

            <div class="empty">
                Пока недостаточно данных
                для надёжной сценарной оценки.
            </div>

        </section>
        """

    balance_data = (
        focus.get("balance")
        or {}
    )

    balance = (
        balance_data.get("balance")
        or {}
    )

    chart = (
        brand_price_scenario_chart(
            focus
        )
    )

    current_price = number(
        balance_data.get(
            "base_price"
        )
    )

    balance_price = number(
        balance.get(
            "projected_price"
        )
    )

    price_change = number(
        balance.get(
            "price_change_pct"
        )
    )

    qty_change = number(
        balance.get(
            "qty_change_pct"
        )
    )

    revenue_change = number(
        balance.get(
            "revenue_change_pct"
        )
    )

    margin_change = number(
        balance.get(
            "margin_change_pct"
        )
    )

    margin_pp = number(
        balance.get(
            "margin_delta_pp"
        )
    )

    if price_change < -1:
        action = (
            "РАССМОТРЕТЬ ТЕСТ БОЛЕЕ НИЗКОЙ ЦЕНЫ"
        )

    elif price_change > 1:
        action = (
            "ЗАЩИЩАТЬ ЦЕНУ"
        )

    else:
        action = (
            "СОХРАНИТЬ ТЕКУЩИЙ УРОВЕНЬ"
        )

    brands = (
        payload
        .get("sales", {})
        .get("brand_price_analysis", {})
        .get("brands", [])
    )

    table_rows = []

    candidates = [
        row
        for row in brands
        if (
            row.get("balance")
            or {}
        ).get("available")
    ]

    candidates.sort(
        key=lambda row: number(
            row.get(
                "revenue_14d"
            )
        ),
        reverse=True,
    )

    for row in candidates[:5]:
        data = (
            row.get("balance")
            or {}
        )

        row_balance = (
            data.get("balance")
            or {}
        )

        row_price_change = number(
            row_balance.get(
                "price_change_pct"
            )
        )

        signal = (
            "Тест ниже"
            if row_price_change < -1
            else "Защищать"
            if row_price_change > 1
            else "Сохранить"
        )

        table_rows.append(
            f"""
            <div class="price-brand-row">

                <div class="brand">
                    {safe(row.get("brand"))}
                </div>

                <div>
                    {_money_short(
                        data.get("base_price")
                    )}
                </div>

                <div>
                    {_money_short(
                        row_balance.get(
                            "projected_price"
                        )
                    )}
                </div>

                <div>
                    {_pct(
                        row_balance.get(
                            "price_change_pct"
                        ),
                        signed=True,
                    )}
                </div>

                <div>
                    {_pct(
                        row_balance.get(
                            "qty_change_pct"
                        ),
                        signed=True,
                    )}
                </div>

                <div>
                    {_pct(
                        row_balance.get(
                            "margin_change_pct"
                        ),
                        signed=True,
                    )}
                </div>

                <div>
                    {safe(signal)}
                </div>

            </div>
            """
        )

    return f"""
    <section class="price-model">

        <div class="price-head">

            <div>
                <div class="price-kicker">
                    ЦЕНОВОЙ ПОТЕНЦИАЛ
                </div>

                <div class="price-block-title">
                    Где находится баланс объёма и маржи
                </div>

                <div class="price-block-subtitle">
                    сценарная модель по брендам · последние 90 дней
                </div>
            </div>

            <div class="price-caption">
                Модель, а не гарантия результата
            </div>

        </div>

        <div class="price-model-focus">

            <div class="price-model-chart">
                {chart}
            </div>

            <aside class="price-model-summary">

                <div class="price-model-brand">
                    {safe(focus.get("brand"))}
                </div>

                <div class="price-model-action">
                    {safe(action)}
                </div>

                <div class="price-model-price">

                    <div>
                        <span>Сейчас</span>
                        <b>
                            {_money_short(
                                current_price
                            )}
                        </b>
                    </div>

                    <div class="arrow">
                        →
                    </div>

                    <div>
                        <span>Баланс</span>
                        <b>
                            {_money_short(
                                balance_price
                            )}
                        </b>
                    </div>

                </div>

                <div class="price-model-metrics">

                    <div>
                        <span>Δ цены</span>
                        <b>
                            {_pct(
                                price_change,
                                signed=True,
                            )}
                        </b>
                    </div>

                    <div>
                        <span>Δ количества</span>
                        <b>
                            {_pct(
                                qty_change,
                                signed=True,
                            )}
                        </b>
                    </div>

                    <div>
                        <span>Δ выручки</span>
                        <b>
                            {_pct(
                                revenue_change,
                                signed=True,
                            )}
                        </b>
                    </div>

                    <div>
                        <span>Δ маржи ₽</span>
                        <b>
                            {_pct(
                                margin_change,
                                signed=True,
                            )}
                        </b>
                    </div>

                    <div>
                        <span>Δ маржинальности</span>
                        <b>
                            {_pp(
                                margin_pp
                            )}
                        </b>
                    </div>

                    <div>
                        <span>Качество модели</span>
                        <b>
                            {safe(
                                focus.get(
                                    "confidence"
                                )
                            )}
                        </b>
                    </div>

                </div>

            </aside>

        </div>

        <div class="price-brand-table">

            <div class="price-brand-row header">
                <div>Бренд</div>
                <div>Сейчас</div>
                <div>Баланс</div>
                <div>Δ цены</div>
                <div>Δ кол-ва</div>
                <div>Δ маржи</div>
                <div>Сигнал</div>
            </div>

            {"".join(table_rows)}

        </div>

        <div class="price-disclaimer">
            Сценарная модель оценивает историческую статистическую связь
            средней цены и количества продаж. Она не доказывает причинный
            эффект цены. На продажи одновременно влияют наличие,
            ассортимент, продвижение и сезонность. Маржа модели —
            после управленческой FIFO-себестоимости и комиссии WB,
            но до маркетинга, штрафов и прочих распределяемых расходов WB.
        </div>

    </section>
    """


# =============================================================================
# PAGE
# =============================================================================

def build_price_page(
    payload: dict,
) -> str:
    data = _price_data(
        payload
    )

    if not data.get(
        "available"
    ):
        return f"""
        {PRICE_PAGE_CSS}

        <div class="page price-page">

            {_masthead(payload)}

            <section class="price-editorial neutral">
                <div class="price-kicker">
                    ЦЕНОВАЯ АНАЛИТИКА
                </div>

                <div class="price-editorial-title">
                    Недостаточно данных
                </div>

                <div class="price-editorial-copy">
                    История цены и скидки WB
                    для выбранной даты не сформирована.
                </div>
            </section>

        </div>
        """

    return f"""
    {PRICE_PAGE_CSS}

    <!-- =============================================================
         PRICE & DISCOUNT PAGE
         ============================================================= -->

    <div class="page price-page">

        {_masthead(payload)}

        {_kpi_row(payload)}

        <div class="price-story-grid">
            {_editorial(payload)}
            {_history_block(payload)}
        </div>

        {_effect_block(payload)}

        {_model_block(payload)}

        <div class="price-footer">
            <span>
                Цена · скидка WB · количество · управленческая маржа
            </span>

            <span>
                Горизонт: 14 дней · 90 дней
            </span>
        </div>

    </div>
    """