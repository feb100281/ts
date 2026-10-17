# gear/app/daily_sales/daily_brief/presentation/pages/demand_charts.py

from __future__ import annotations

from html import escape

import pandas as pd

from ...helpers import number


# =============================================================================
# ПАЛИТРА
# =============================================================================


PAPER = "#FFFDF7"

NAVY = "#14213D"
MUTED = "#667085"

BORDER = "#D7DCE2"
GRID = "#E8EBEF"

CORAL = "#E85D75"
CORAL_SOFT = "#F5C2CD"

GREEN = "#16805E"
GREEN_SOFT = "#DCEFE8"

PURPLE = "#8067AB"
PURPLE_SOFT = "#E8E1F0"

YELLOW = "#E9B949"


# =============================================================================
# FORMATTERS
# =============================================================================


def _safe(
    value,
) -> str:
    return escape(
        str(
            value
            if value is not None
            else ""
        )
    )


def _compact(
    value,
) -> str:
    value = number(
        value
    )

    absolute = abs(
        value
    )

    sign = (
        "−"
        if value < 0
        else ""
    )

    if absolute >= 1_000_000_000:
        return (
            f"{sign}"
            f"{absolute / 1_000_000_000:.1f}"
            .replace(".", ",")
            + " млрд"
        )

    if absolute >= 1_000_000:
        return (
            f"{sign}"
            f"{absolute / 1_000_000:.1f}"
            .replace(".", ",")
            + " млн"
        )

    if absolute >= 1_000:
        return (
            f"{sign}"
            f"{absolute / 1_000:.1f}"
            .replace(".", ",")
            + " тыс"
        )

    return (
        f"{sign}{absolute:,.0f}"
        .replace(",", " ")
    )


def _pct(
    value,
    *,
    signed: bool = False,
) -> str:
    value = number(
        value
    )

    sign = ""

    if signed:
        if value > 0:
            sign = "+"
        elif value < 0:
            sign = "−"

    elif value < 0:
        sign = "−"

    return (
        f"{sign}{abs(value):.1f}%"
        .replace(".", ",")
    )


# =============================================================================
# DATA PREPARATION
# =============================================================================


def _daily_frame(
    rows: list[dict],
) -> pd.DataFrame:

    frame = pd.DataFrame(
        rows or []
    )

    if frame.empty:
        return frame

    required = [
        "date_from",
        "sales_qty",
        "avg_price",
        "net_amount",
    ]

    for column in required:
        if column not in frame.columns:
            frame[column] = None

    frame["date_from"] = pd.to_datetime(
        frame["date_from"],
        errors="coerce",
    )

    for column in (
        "sales_qty",
        "avg_price",
        "net_amount",
    ):
        frame[column] = pd.to_numeric(
            frame[column],
            errors="coerce",
        )

    frame = (
        frame
        .dropna(
            subset=[
                "date_from",
            ]
        )
        .sort_values(
            "date_from"
        )
        .reset_index(
            drop=True
        )
    )

    return frame


def _monthly_frame(
    rows: list[dict],
) -> pd.DataFrame:

    frame = pd.DataFrame(
        rows or []
    )

    if frame.empty:
        return frame

    if "month_date" not in frame:
        frame["month_date"] = None

    frame["month_date"] = pd.to_datetime(
        frame["month_date"],
        errors="coerce",
    )

    for column in (
        "sales_qty",
        "avg_price",
        "net_amount",
    ):
        if column not in frame:
            frame[column] = None

        frame[column] = pd.to_numeric(
            frame[column],
            errors="coerce",
        )

    return (
        frame
        .dropna(
            subset=[
                "month_date",
            ]
        )
        .sort_values(
            "month_date"
        )
        .reset_index(
            drop=True
        )
    )


# =============================================================================
# 90 DAYS — DEMAND / PRICE REGIME
# =============================================================================


def demand_price_index_chart(
    rows: list[dict],
) -> str:
    """
    90 дней.

    Вместо scatter используем две 7-дневные скользящие линии,
    приведённые к единой базе 100:

        спрос = количество положительных продаж;
        цена  = средняя цена продажи.

    Это позволяет визуально сравнивать изменение показателей,
    несмотря на совершенно разные единицы измерения.
    """

    frame = _daily_frame(
        rows
    )

    if len(frame) < 7:
        return ""

    frame["qty_ma"] = (
        frame["sales_qty"]
        .rolling(
            7,
            min_periods=4,
        )
        .mean()
    )

    frame["price_ma"] = (
        frame["avg_price"]
        .rolling(
            7,
            min_periods=4,
        )
        .mean()
    )

    valid = frame[
        frame["qty_ma"].notna()
        & frame["price_ma"].notna()
        & (frame["qty_ma"] > 0)
        & (frame["price_ma"] > 0)
    ].copy()

    if len(valid) < 2:
        return ""

    base_qty = number(
        valid.iloc[0]["qty_ma"]
    )

    base_price = number(
        valid.iloc[0]["price_ma"]
    )

    if not base_qty or not base_price:
        return ""

    valid["qty_index"] = (
        valid["qty_ma"]
        / base_qty
        * 100
    )

    valid["price_index"] = (
        valid["price_ma"]
        / base_price
        * 100
    )

    width = 720
    height = 210

    left = 42
    right = 18
    top = 28
    bottom = 30

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

    combined = pd.concat(
        [
            valid["qty_index"],
            valid["price_index"],
        ]
    )

    y_min = min(
        float(
            combined.min()
        ),
        100,
    )

    y_max = max(
        float(
            combined.max()
        ),
        100,
    )

    padding = max(
        (
            y_max
            - y_min
        )
        * 0.10,
        5,
    )

    y_min -= padding
    y_max += padding

    span = (
        y_max
        - y_min
    ) or 1

    def x_pos(
        index: int,
    ) -> float:

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
        value: float,
    ) -> float:

        return (
            top
            + (
                y_max
                - value
            )
            / span
            * plot_height
        )

    qty_points = []
    price_points = []

    for index, row in valid.iterrows():

        local_index = (
            valid.index.get_loc(
                index
            )
        )

        x = x_pos(
            local_index
        )

        qty_points.append(
            f"{x:.1f},"
            f"{y_pos(row['qty_index']):.1f}"
        )

        price_points.append(
            f"{x:.1f},"
            f"{y_pos(row['price_index']):.1f}"
        )

    html = [
        f"""
        <svg
            viewBox="0 0 {width} {height}"
            xmlns="http://www.w3.org/2000/svg"
        >
        """
    ]

    # -----------------------------------------------------------------
    # BASE 100
    # -----------------------------------------------------------------

    base_y = y_pos(
        100
    )

    html.append(
        f"""
        <line
            x1="{left}"
            y1="{base_y:.1f}"
            x2="{width - right}"
            y2="{base_y:.1f}"
            stroke="{MUTED}"
            stroke-width="1"
            stroke-dasharray="4 4"
            opacity=".45"
        />

        <text
            x="{left - 7}"
            y="{base_y + 3:.1f}"
            text-anchor="end"
            fill="{MUTED}"
            font-family="Arial"
            font-size="6"
        >
            100
        </text>
        """
    )

    # -----------------------------------------------------------------
    # GRID
    # -----------------------------------------------------------------

    for fraction in (
        0.25,
        0.50,
        0.75,
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

    # -----------------------------------------------------------------
    # LAST 14 DAYS HIGHLIGHT
    # -----------------------------------------------------------------

    if len(valid) >= 14:

        first_recent_index = (
            len(valid) - 14
        )

        recent_x = x_pos(
            first_recent_index
        )

        html.append(
            f"""
            <rect
                x="{recent_x:.1f}"
                y="{top}"
                width="{width - right - recent_x:.1f}"
                height="{plot_height}"
                fill="{GREEN_SOFT}"
                opacity=".28"
            />

            <text
                x="{recent_x + 5:.1f}"
                y="{top + 10}"
                fill="{GREEN}"
                font-family="Arial"
                font-size="6"
                font-weight="700"
            >
                ПОСЛЕДНИЕ 14 ДНЕЙ
            </text>
            """
        )

    # -----------------------------------------------------------------
    # LINES
    # -----------------------------------------------------------------

    html.append(
        f"""
        <polyline
            points="{" ".join(qty_points)}"
            fill="none"
            stroke="{NAVY}"
            stroke-width="2.5"
            stroke-linecap="round"
            stroke-linejoin="round"
        />

        <polyline
            points="{" ".join(price_points)}"
            fill="none"
            stroke="{CORAL}"
            stroke-width="2.2"
            stroke-linecap="round"
            stroke-linejoin="round"
        />
        """
    )

    # -----------------------------------------------------------------
    # DATE LABELS
    # -----------------------------------------------------------------

    label_indexes = sorted(
        {
            0,
            len(valid) // 2,
            len(valid) - 1,
        }
    )

    for index in label_indexes:

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
                font-size="6"
            >
                {row["date_from"].strftime("%d.%m")}
            </text>
            """
        )

    # -----------------------------------------------------------------
    # LEGEND
    # -----------------------------------------------------------------

    html.append(
        f"""
        <line
            x1="{left}"
            y1="12"
            x2="{left + 18}"
            y2="12"
            stroke="{NAVY}"
            stroke-width="2.5"
        />

        <text
            x="{left + 24}"
            y="15"
            fill="{NAVY}"
            font-family="Arial"
            font-size="6.4"
            font-weight="700"
        >
            спрос · 7-дневная средняя
        </text>

        <line
            x1="{left + 150}"
            y1="12"
            x2="{left + 168}"
            y2="12"
            stroke="{CORAL}"
            stroke-width="2.5"
        />

        <text
            x="{left + 174}"
            y="15"
            fill="{CORAL}"
            font-family="Arial"
            font-size="6.4"
            font-weight="700"
        >
            средняя цена · 7-дневная средняя
        </text>

        <text
            x="{width - right}"
            y="15"
            text-anchor="end"
            fill="{MUTED}"
            font-family="Arial"
            font-size="5.8"
        >
            начало ряда = 100
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
# 12 MONTHS — REVENUE DRIVERS
# =============================================================================


def monthly_drivers_chart(
    rows: list[dict],
) -> str:
    """
    Показывает 12 месяцев не как обычный bar+line,
    а как месячные карточки:

        чистая выручка,
        изменение количества продаж,
        изменение средней цены.

    Так сразу видно, чем был обеспечен рост / падение месяца.
    """

    frame = _monthly_frame(
        rows
    )

    if frame.empty:
        return ""

    frame = frame.tail(
        12
    ).copy()

    frame["qty_change"] = (
        frame["sales_qty"]
        .pct_change()
        * 100
    )

    frame["price_change"] = (
        frame["avg_price"]
        .pct_change()
        * 100
    )

    revenues = (
        frame["net_amount"]
        .fillna(0)
        .abs()
    )

    max_revenue = (
        float(
            revenues.max()
        )
        if not revenues.empty
        else 1
    ) or 1

    cell_width = 58
    gap = 4

    width = (
        len(frame)
        * cell_width
        + max(
            len(frame) - 1,
            0,
        )
        * gap
    )

    height = 170

    html = [
        f"""
        <svg
            viewBox="0 0 {width} {height}"
            xmlns="http://www.w3.org/2000/svg"
        >
        """
    ]

    x = 0

    for index, row in frame.iterrows():

        revenue = number(
            row.get(
                "net_amount"
            )
        )

        qty_change = row.get(
            "qty_change"
        )

        price_change = row.get(
            "price_change"
        )

        bar_height = (
            abs(revenue)
            / max_revenue
            * 54
        )

        bar_y = (
            89
            - bar_height
        )

        month = row[
            "month_date"
        ].strftime(
            "%m.%y"
        )

        qty_color = (
            GREEN
            if number(qty_change) >= 0
            else CORAL
        )

        price_color = (
            GREEN
            if number(price_change) >= 0
            else CORAL
        )

        html.append(
            f"""
            <text
                x="{x + cell_width / 2}"
                y="13"
                text-anchor="middle"
                fill="{MUTED}"
                font-family="Arial"
                font-size="6"
                font-weight="700"
            >
                {month}
            </text>

            <rect
                x="{x + 12}"
                y="{bar_y:.1f}"
                width="{cell_width - 24}"
                height="{bar_height:.1f}"
                fill="{CORAL_SOFT}"
            />

            <text
                x="{x + cell_width / 2}"
                y="{max(bar_y - 5, 25):.1f}"
                text-anchor="middle"
                fill="{NAVY}"
                font-family="Arial"
                font-size="6.2"
                font-weight="700"
            >
                {_safe(_compact(revenue))}
            </text>

            <line
                x1="{x + 5}"
                y1="98"
                x2="{x + cell_width - 5}"
                y2="98"
                stroke="{BORDER}"
            />

            <text
                x="{x + 5}"
                y="114"
                fill="{MUTED}"
                font-family="Arial"
                font-size="5.2"
            >
                спрос
            </text>

            <text
                x="{x + cell_width - 5}"
                y="114"
                text-anchor="end"
                fill="{qty_color}"
                font-family="Arial"
                font-size="6.4"
                font-weight="700"
            >
                {
                    "—"
                    if pd.isna(qty_change)
                    else _safe(
                        _pct(
                            qty_change,
                            signed=True,
                        )
                    )
                }
            </text>

            <text
                x="{x + 5}"
                y="132"
                fill="{MUTED}"
                font-family="Arial"
                font-size="5.2"
            >
                цена
            </text>

            <text
                x="{x + cell_width - 5}"
                y="132"
                text-anchor="end"
                fill="{price_color}"
                font-family="Arial"
                font-size="6.4"
                font-weight="700"
            >
                {
                    "—"
                    if pd.isna(price_change)
                    else _safe(
                        _pct(
                            price_change,
                            signed=True,
                        )
                    )
                }
            </text>
            """
        )

        x += (
            cell_width
            + gap
        )

    html.append(
        f"""
        <text
            x="0"
            y="158"
            fill="{MUTED}"
            font-family="Arial"
            font-size="5.3"
        >
            столбик — чистая выручка · проценты — изменение к предыдущему месяцу
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
# TOP ENTITIES
# =============================================================================


def ranking_chart(
    rows: list[dict],
    *,
    limit: int = 5,
) -> str:
    """
    Top брендов / категорий.

    Основной показатель — чистая выручка.
    Дополнительно показываем количество положительных продаж.
    """

    prepared = list(
        rows
        or []
    )[:limit]

    if not prepared:
        return ""

    max_value = max(
        [
            max(
                number(
                    row.get(
                        "revenue"
                    )
                ),
                0,
            )
            for row in prepared
        ]
        or [1]
    ) or 1

    width = 330
    height = 145

    label_width = 105
    bar_width = 135

    html = [
        f"""
        <svg
            viewBox="0 0 {width} {height}"
            xmlns="http://www.w3.org/2000/svg"
        >
        """
    ]

    y = 7

    for row in prepared:

        label = (
            row.get(
                "name"
            )
            or "Не указано"
        )

        revenue = max(
            number(
                row.get(
                    "revenue"
                )
            ),
            0,
        )

        units = int(
            number(
                row.get(
                    "sold_units"
                )
            )
        )

        fill = (
            revenue
            / max_value
            * bar_width
        )

        html.append(
            f"""
            <text
                x="0"
                y="{y + 9}"
                fill="{NAVY}"
                font-family="Arial"
                font-size="6.4"
                font-weight="700"
            >
                {_safe(str(label)[:22])}
            </text>

            <rect
                x="{label_width}"
                y="{y}"
                width="{bar_width}"
                height="11"
                fill="{GRID}"
            />

            <rect
                x="{label_width}"
                y="{y}"
                width="{fill:.1f}"
                height="11"
                fill="{CORAL}"
                opacity=".70"
            />

            <text
                x="328"
                y="{y + 8}"
                text-anchor="end"
                fill="{NAVY}"
                font-family="Arial"
                font-size="6"
                font-weight="700"
            >
                {_safe(_compact(revenue))} ₽
            </text>

            <text
                x="{label_width}"
                y="{y + 20}"
                fill="{MUTED}"
                font-family="Arial"
                font-size="5"
            >
                {units:,} ед.
            </text>
            """
        )

        y += 27

    html.append(
        "</svg>"
    )

    return (
        "".join(
            html
        )
        .replace(
            ",",
            " "
        )
    )
    
    

# =============================================================================
# МАТРИЦА ЦЕНОВОГО ПОТЕНЦИАЛА БРЕНДОВ
# =============================================================================


# =============================================================================
# PRICE / DEMAND / MARGIN SCENARIO
# =============================================================================


def brand_price_scenario_chart(
    row: dict,
) -> str:
    """
    Для одного бренда показывает:

        X  = изменение средней цены, %
        Y1 = изменение количества продаж, %
        Y2 = изменение маржи в рублях, %

    Отмечаем:
        ТЕКУЩАЯ ЦЕНА
        MAX МАРЖИ
        БАЛАНС

    Это намного полезнее bubble-chart:
    пользователь видит конкретный trade-off.
    """

    balance_data = (
        row.get(
            "balance"
        )
        or {}
    )

    if not balance_data.get(
        "available"
    ):
        return ""

    scenarios = list(
        balance_data.get(
            "scenarios"
        )
        or []
    )

    if len(scenarios) < 2:
        return ""

    width = 700
    height = 245

    left = 48
    right = 18
    top = 28
    bottom = 42

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

    x_values = [
        number(
            item.get(
                "price_change_pct"
            )
        )
        for item in scenarios
    ]

    qty_values = [
        number(
            item.get(
                "qty_change_pct"
            )
        )
        for item in scenarios
    ]

    margin_values = [
        number(
            item.get(
                "margin_change_pct"
            )
        )
        for item in scenarios
    ]

    y_values = (
        qty_values
        + margin_values
        + [0]
    )

    x_min = min(
        x_values
    )

    x_max = max(
        x_values
    )

    y_min = min(
        y_values
    )

    y_max = max(
        y_values
    )

    y_padding = max(
        (
            y_max
            - y_min
        )
        * 0.12,
        5,
    )

    y_min -= y_padding
    y_max += y_padding

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
        return (
            top
            + (
                y_max
                - value
            )
            / y_span
            * plot_height
        )

    qty_points = []

    margin_points = []

    for item in scenarios:

        x = x_pos(
            number(
                item.get(
                    "price_change_pct"
                )
            )
        )

        qty_points.append(
            f"{x:.1f},"
            f"{y_pos(item.get('qty_change_pct')):.1f}"
        )

        margin_points.append(
            f"{x:.1f},"
            f"{y_pos(item.get('margin_change_pct')):.1f}"
        )

    html = [
        f"""
        <svg
            viewBox="0 0 {width} {height}"
            xmlns="http://www.w3.org/2000/svg"
        >
        """
    ]

    # -----------------------------------------------------------------
    # ZERO LINES
    # -----------------------------------------------------------------

    zero_y = y_pos(
        0
    )

    zero_x = x_pos(
        0
    )

    html.append(
        f"""
        <line
            x1="{left}"
            y1="{zero_y:.1f}"
            x2="{width - right}"
            y2="{zero_y:.1f}"
            stroke="{MUTED}"
            stroke-width="1"
            stroke-dasharray="4 4"
            opacity=".55"
        />

        <line
            x1="{zero_x:.1f}"
            y1="{top}"
            x2="{zero_x:.1f}"
            y2="{top + plot_height}"
            stroke="{MUTED}"
            stroke-width="1"
            stroke-dasharray="4 4"
            opacity=".35"
        />
        """
    )

    # -----------------------------------------------------------------
    # GOLDEN ZONE
    # -----------------------------------------------------------------

    max_margin_value = number(
        (
            balance_data.get(
                "max_margin"
            )
            or {}
        ).get(
            "projected_margin"
        )
    )

    zone = [
        item
        for item in scenarios
        if (
            number(
                item.get(
                    "projected_margin"
                )
            )
            >= max_margin_value
            * 0.98
        )
        and (
            number(
                item.get(
                    "projected_margin_pct"
                )
            )
            >= number(
                balance_data.get(
                    "base_margin_pct"
                )
            )
            - 3
        )
    ]

    if zone:

        zone_min = min(
            number(
                item.get(
                    "price_change_pct"
                )
            )
            for item in zone
        )

        zone_max = max(
            number(
                item.get(
                    "price_change_pct"
                )
            )
            for item in zone
        )

        zx1 = x_pos(
            zone_min
        )

        zx2 = x_pos(
            zone_max
        )

        html.append(
            f"""
            <rect
                x="{zx1:.1f}"
                y="{top}"
                width="{max(zx2 - zx1, 2):.1f}"
                height="{plot_height}"
                fill="{GREEN_SOFT}"
                opacity=".55"
            />

            <text
                x="{(zx1 + zx2) / 2:.1f}"
                y="{top + 10}"
                text-anchor="middle"
                fill="{GREEN}"
                font-family="Arial"
                font-size="5.7"
                font-weight="700"
            >
                ЗОНА БАЛАНСА
            </text>
            """
        )

    # -----------------------------------------------------------------
    # CURVES
    # -----------------------------------------------------------------

    html.append(
        f"""
        <polyline
            points="{" ".join(qty_points)}"
            fill="none"
            stroke="{NAVY}"
            stroke-width="2.5"
            stroke-linejoin="round"
            stroke-linecap="round"
        />

        <polyline
            points="{" ".join(margin_points)}"
            fill="none"
            stroke="{CORAL}"
            stroke-width="2.5"
            stroke-linejoin="round"
            stroke-linecap="round"
        />
        """
    )

    # -----------------------------------------------------------------
    # POINT HELPER
    # -----------------------------------------------------------------

    def point(
        item: dict,
        label: str,
        color: str,
        label_y_offset: float,
    ) -> str:

        price_change = number(
            item.get(
                "price_change_pct"
            )
        )

        margin_change = number(
            item.get(
                "margin_change_pct"
            )
        )

        x = x_pos(
            price_change
        )

        y = y_pos(
            margin_change
        )

        return f"""
        <circle
            cx="{x:.1f}"
            cy="{y:.1f}"
            r="5"
            fill="{color}"
            stroke="#FFFDF7"
            stroke-width="2"
        />

        <text
            x="{x:.1f}"
            y="{y + label_y_offset:.1f}"
            text-anchor="middle"
            fill="{color}"
            font-family="Arial"
            font-size="5.5"
            font-weight="700"
        >
            {label}
        </text>
        """

    current = (
        balance_data.get(
            "current"
        )
        or {}
    )

    max_margin = (
        balance_data.get(
            "max_margin"
        )
        or {}
    )

    balance = (
        balance_data.get(
            "balance"
        )
        or {}
    )

    html.append(
        point(
            current,
            "СЕЙЧАС",
            MUTED,
            17,
        )
    )

    html.append(
        point(
            max_margin,
            "MAX МАРЖИ",
            CORAL,
            -10,
        )
    )

    html.append(
        point(
            balance,
            "БАЛАНС",
            GREEN,
            18,
        )
    )

    # -----------------------------------------------------------------
    # LEGEND
    # -----------------------------------------------------------------

    html.append(
        f"""
        <line
            x1="{left}"
            y1="12"
            x2="{left + 18}"
            y2="12"
            stroke="{NAVY}"
            stroke-width="2.5"
        />

        <text
            x="{left + 24}"
            y="15"
            fill="{NAVY}"
            font-family="Arial"
            font-size="6"
            font-weight="700"
        >
            количество продаж
        </text>

        <line
            x1="{left + 135}"
            y1="12"
            x2="{left + 153}"
            y2="12"
            stroke="{CORAL}"
            stroke-width="2.5"
        />

        <text
            x="{left + 159}"
            y="15"
            fill="{CORAL}"
            font-family="Arial"
            font-size="6"
            font-weight="700"
        >
            маржа ₽
        </text>
        """
    )

    # -----------------------------------------------------------------
    # X LABELS
    # -----------------------------------------------------------------

    for value in (
        -15,
        -10,
        -5,
        0,
        5,
        10,
        15,
    ):

        if (
            value < x_min
            or value > x_max
        ):
            continue

        html.append(
            f"""
            <text
                x="{x_pos(value):.1f}"
                y="{height - 18}"
                text-anchor="middle"
                fill="{MUTED}"
                font-family="Arial"
                font-size="5.5"
            >
                {value:+d}%
            </text>
            """
        )

    html.append(
        f"""
        <text
            x="{left + plot_width / 2}"
            y="{height - 3}"
            text-anchor="middle"
            fill="{NAVY}"
            font-family="Arial"
            font-size="6"
            font-weight="700"
        >
            изменение средней цены относительно текущего уровня
        </text>
        """
    )

    html.append(
        "</svg>"
    )

    return "".join(
        html
    )