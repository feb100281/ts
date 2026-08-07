# gear/app/daily_sales/daily_brief/presentation/pages/plan_charts.py

from __future__ import annotations

import math
from html import escape
from typing import Any

import pandas as pd

from ...helpers import number


# =============================================================================
# ЦВЕТА
# =============================================================================

NAVY = "#14213D"
CORAL = "#E85D75"
CORAL_DARK = "#B53C56"
TEAL = "#0F766E"
GREEN = "#12654F"
YELLOW = "#FFD84D"

MUTED = "#667085"
GRID = "#E4E7EB"
BORDER = "#D7DCE2"
PAPER = "#FFFDF7"
SOFT_PINK = "#FBECEF"
SOFT_YELLOW = "#FFF2C7"
SOFT_GREEN = "#E3F2ED"
SOFT_GRAY = "#F5F3EC"


MONTHS = {
    1: "янв",
    2: "фев",
    3: "мар",
    4: "апр",
    5: "май",
    6: "июн",
    7: "июл",
    8: "авг",
    9: "сен",
    10: "окт",
    11: "ноя",
    12: "дек",
}



MONTH_NAME_TO_NUMBER = {
    "январь": 1,
    "января": 1,
    "янв": 1,

    "февраль": 2,
    "февраля": 2,
    "фев": 2,

    "март": 3,
    "марта": 3,
    "мар": 3,

    "апрель": 4,
    "апреля": 4,
    "апр": 4,

    "май": 5,
    "мая": 5,

    "июнь": 6,
    "июня": 6,
    "июн": 6,

    "июль": 7,
    "июля": 7,
    "июл": 7,

    "август": 8,
    "августа": 8,
    "авг": 8,

    "сентябрь": 9,
    "сентября": 9,
    "сен": 9,
    "сент": 9,

    "октябрь": 10,
    "октября": 10,
    "окт": 10,

    "ноябрь": 11,
    "ноября": 11,
    "ноя": 11,

    "декабрь": 12,
    "декабря": 12,
    "дек": 12,
}


def _month_number_from_row(
    row: dict,
) -> int | None:
    """
    Приводит месяц из monthly_rows к номеру 1..12.

    Поддерживает:
        7
        "7"
        "07"
        "2026-07"
        "Июль"
        "июля"
        "июл"

    В текущем WB Plan Monitor поле row["month"]
    содержит русское название месяца, а не номер.
    """

    raw = row.get("month")

    if raw is None:
        raw = row.get("month_short")

    if raw is None:
        return None

    # Уже число
    if isinstance(raw, (int, float)):
        month = int(raw)

        return (
            month
            if 1 <= month <= 12
            else None
        )

    text = (
        str(raw)
        .strip()
        .lower()
        .replace(".", "")
    )

    if not text:
        return None

    # 7 / 07
    if text.isdigit():
        month = int(text)

        return (
            month
            if 1 <= month <= 12
            else None
        )

    # 2026-07 / 2026-07-01
    parsed = pd.to_datetime(
        text,
        errors="coerce",
    )

    if not pd.isna(parsed):
        return int(parsed.month)

    return MONTH_NAME_TO_NUMBER.get(
        text
    )


# =============================================================================
# ОБЩИЕ ФУНКЦИИ
# =============================================================================


def _money_short(
    value: Any,
) -> str:
    value = number(value)

    if abs(value) >= 1_000_000_000:
        return (
            f"{value / 1_000_000_000:.1f}"
            .replace(".", ",")
            + " млрд ₽"
        )

    if abs(value) >= 1_000_000:
        return (
            f"{value / 1_000_000:.0f}"
            .replace(".", ",")
            + " млн ₽"
        )

    if abs(value) >= 1_000:
        return (
            f"{value / 1_000:.0f}"
            .replace(".", ",")
            + " тыс. ₽"
        )

    return (
        f"{value:.0f} ₽"
    )


def _mln(
    value: Any,
) -> float:
    return number(value) / 1_000_000


def _format_mln(
    value: Any,
    digits: int = 0,
) -> str:
    value = number(value)

    return (
        f"{value / 1_000_000:.{digits}f}"
        .replace(".", ",")
        + " млн"
    )


def _clamp(
    value: float,
    minimum: float,
    maximum: float,
) -> float:
    return max(
        minimum,
        min(
            value,
            maximum,
        ),
    )


def _line_points(
    values: list[float],
    *,
    left: float,
    top: float,
    width: float,
    height: float,
    maximum: float,
) -> list[tuple[float, float]]:
    if not values:
        return []

    denominator = max(
        len(values) - 1,
        1,
    )

    result: list[tuple[float, float]] = []

    for index, value in enumerate(
        values
    ):
        x = (
            left
            + index
            * width
            / denominator
        )

        y = (
            top
            + height
            - (
                value
                / maximum
                * height
            )
        )

        result.append(
            (
                x,
                y,
            )
        )

    return result


def _points_attribute(
    points: list[tuple[float, float]],
) -> str:
    return " ".join(
        f"{x:.2f},{y:.2f}"
        for x, y in points
    )


def _svg_empty(
    message: str,
    *,
    width: int = 720,
    height: int = 220,
) -> str:
    return f"""
    <svg
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 {width} {height}"
        width="100%"
        height="100%"
        preserveAspectRatio="xMidYMid meet"
    >
        <rect
            x="1"
            y="1"
            width="{width - 2}"
            height="{height - 2}"
            fill="{SOFT_GRAY}"
            stroke="{BORDER}"
            stroke-width="1"
            stroke-dasharray="5 4"
        />

        <text
            x="{width / 2}"
            y="{height / 2}"
            text-anchor="middle"
            dominant-baseline="middle"
            font-family="Arial, sans-serif"
            font-size="14"
            fill="{MUTED}"
        >
            {escape(message)}
        </text>
    </svg>
    """


# =============================================================================
# НАКОПИТЕЛЬНЫЙ ПЛАН И ФАКТ ТЕКУЩЕГО МЕСЯЦА
# =============================================================================


def current_month_plan_chart(
    plan: dict,
) -> str:
    rows = list(
        plan.get(
            "rows",
            [],
        )
        or []
    )

    if len(rows) < 2:
        return _svg_empty(
            "Недостаточно данных для графика текущего месяца."
        )

    prepared: list[dict] = []

    for index, row in enumerate(
        rows
    ):
        prepared.append(
            {
                "label": str(
                    row.get("date_label")
                    or index + 1
                ),
                "fact": number(
                    row.get(
                        "running_fact"
                    )
                ),
                "plan": number(
                    row.get(
                        "running_plan"
                    )
                ),
            }
        )

    width = 760
    height = 270

    left = 67
    right = 24
    top = 35
    bottom = 48

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

    fact_values = [
        row["fact"]
        for row in prepared
    ]

    plan_values = [
        row["plan"]
        for row in prepared
    ]

    maximum = max(
        max(fact_values),
        max(plan_values),
        1,
    ) * 1.16

    fact_points = _line_points(
        fact_values,
        left=left,
        top=top,
        width=plot_width,
        height=plot_height,
        maximum=maximum,
    )

    plan_points = _line_points(
        plan_values,
        left=left,
        top=top,
        width=plot_width,
        height=plot_height,
        maximum=maximum,
    )

    fact_points_text = (
        _points_attribute(
            fact_points
        )
    )

    plan_points_text = (
        _points_attribute(
            plan_points
        )
    )

    baseline_y = (
        top
        + plot_height
    )

    area_points = (
        f"{fact_points[0][0]:.2f},{baseline_y:.2f} "
        + fact_points_text
        + f" {fact_points[-1][0]:.2f},{baseline_y:.2f}"
    )

    grid_html: list[str] = []

    for index in range(5):
        ratio = (
            index
            / 4
        )

        y = (
            top
            + plot_height
            - ratio
            * plot_height
        )

        grid_value = (
            maximum
            * ratio
        )

        grid_html.append(
            f"""
            <line
                x1="{left}"
                y1="{y:.2f}"
                x2="{left + plot_width}"
                y2="{y:.2f}"
                stroke="{GRID}"
                stroke-width="1"
            />

            <text
                x="{left - 9}"
                y="{y + 3:.2f}"
                text-anchor="end"
                font-family="Arial, sans-serif"
                font-size="9"
                fill="{MUTED}"
            >
                {escape(_format_mln(grid_value))}
            </text>
            """
        )

    label_indices = sorted(
        set(
            [
                0,
                len(prepared) // 4,
                len(prepared) // 2,
                len(prepared) * 3 // 4,
                len(prepared) - 1,
            ]
        )
    )

    x_labels: list[str] = []

    denominator = max(
        len(prepared) - 1,
        1,
    )

    for index in label_indices:
        x = (
            left
            + index
            * plot_width
            / denominator
        )

        x_labels.append(
            f"""
            <text
                x="{x:.2f}"
                y="{height - 20}"
                text-anchor="middle"
                font-family="Arial, sans-serif"
                font-size="10"
                fill="{NAVY}"
            >
                {escape(prepared[index]["label"])}
            </text>
            """
        )

    last_fact = fact_values[-1]
    last_plan = plan_values[-1]

    execution = (
        last_fact
        / last_plan
        * 100
        if last_plan
        else 0
    )

    delta = (
        last_fact
        - last_plan
    )

    status_color = (
        GREEN
        if delta >= 0
        else CORAL_DARK
    )

    status_sign = (
        "+"
        if delta > 0
        else "−"
        if delta < 0
        else ""
    )

    last_x, last_fact_y = (
        fact_points[-1]
    )

    _, last_plan_y = (
        plan_points[-1]
    )

    box_width = 138
    box_height = 39

    box_x = (
        last_x
        - box_width
        - 9
    )

    box_y = max(
        7,
        min(
            last_fact_y - 48,
            height - bottom - box_height,
        ),
    )

    return f"""
    <svg
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 {width} {height}"
        width="100%"
        height="100%"
        preserveAspectRatio="xMidYMid meet"
        role="img"
        aria-label="Накопительный план и факт текущего месяца"
    >
        <rect
            x="0"
            y="0"
            width="{width}"
            height="{height}"
     
        />

        <text
            x="{left}"
            y="18"
            font-family="Arial, sans-serif"
            font-size="10"
            font-weight="700"
            fill="{MUTED}"
        >
            Накопительно с начала месяца
        </text>

        <g>
            {"".join(grid_html)}
        </g>

        <line
            x1="{left}"
            y1="{baseline_y}"
            x2="{left + plot_width}"
            y2="{baseline_y}"
            stroke="{MUTED}"
            stroke-width="1"
        />

        <polygon
            points="{area_points}"
            fill="{CORAL}"
            fill-opacity="0.12"
            stroke="none"
        />

        <polyline
            points="{plan_points_text}"
            fill="none"
            stroke="{NAVY}"
            stroke-width="3"
            stroke-dasharray="9 6"
            stroke-linecap="round"
            stroke-linejoin="round"
        />

        <polyline
            points="{fact_points_text}"
            fill="none"
            stroke="{CORAL}"
            stroke-width="4"
            stroke-linecap="round"
            stroke-linejoin="round"
        />

        <line
            x1="{last_x:.2f}"
            y1="{last_plan_y:.2f}"
            x2="{last_x:.2f}"
            y2="{last_fact_y:.2f}"
            stroke="{status_color}"
            stroke-width="2"
            stroke-dasharray="4 3"
        />

        <circle
            cx="{last_x:.2f}"
            cy="{last_plan_y:.2f}"
            r="5"
     
            stroke="{NAVY}"
            stroke-width="2"
        />

        <circle
            cx="{last_x:.2f}"
            cy="{last_fact_y:.2f}"
            r="7"
            fill="{status_color}"
            stroke="{PAPER}"
            stroke-width="2"
        />

        <rect
            x="{box_x:.2f}"
            y="{box_y:.2f}"
            width="{box_width}"
            height="{box_height}"
            fill="{PAPER}"
            stroke="{status_color}"
            stroke-width="1.5"
        />

        <text
            x="{box_x + 7:.2f}"
            y="{box_y + 15:.2f}"
            font-family="Arial, sans-serif"
            font-size="11"
            font-weight="700"
            fill="{status_color}"
        >
            {execution:.1f}% плана
        </text>

        <text
            x="{box_x + 7:.2f}"
            y="{box_y + 30:.2f}"
            font-family="Arial, sans-serif"
            font-size="10"
            font-weight="700"
            fill="{status_color}"
        >
            {status_sign}{escape(_money_short(abs(delta)))}
        </text>

        <g>
            {"".join(x_labels)}
        </g>

        <g transform="translate({left}, {height - 3})">
            <line
                x1="0"
                y1="-3"
                x2="18"
                y2="-3"
                stroke="{CORAL}"
                stroke-width="4"
            />

            <text
                x="24"
                y="0"
                font-family="Arial, sans-serif"
                font-size="9"
                fill="{MUTED}"
            >
                Факт
            </text>

            <line
                x1="76"
                y1="-3"
                x2="94"
                y2="-3"
                stroke="{NAVY}"
                stroke-width="3"
                stroke-dasharray="6 4"
            />

            <text
                x="100"
                y="0"
                font-family="Arial, sans-serif"
                font-size="9"
                fill="{MUTED}"
            >
                План к дате
            </text>
        </g>
    </svg>
    """


# =============================================================================
# СПИДОМЕТР ПОЛУГОДОВОГО ПЛАНА
# =============================================================================


def _polar(
    center_x: float,
    center_y: float,
    radius: float,
    angle_degrees: float,
) -> tuple[float, float]:
    angle_radians = math.radians(
        angle_degrees
    )

    return (
        center_x
        + radius
        * math.cos(angle_radians),
        center_y
        + radius
        * math.sin(angle_radians),
    )


def _arc(
    center_x: float,
    center_y: float,
    radius: float,
    start_angle: float,
    finish_angle: float,
) -> str:
    start_x, start_y = _polar(
        center_x,
        center_y,
        radius,
        start_angle,
    )

    finish_x, finish_y = _polar(
        center_x,
        center_y,
        radius,
        finish_angle,
    )

    large_arc = (
        1
        if abs(
            finish_angle
            - start_angle
        ) > 180
        else 0
    )

    sweep = (
        1
        if finish_angle > start_angle
        else 0
    )

    return (
        f"M {start_x:.2f} {start_y:.2f} "
        f"A {radius:.2f} {radius:.2f} "
        f"0 {large_arc} {sweep} "
        f"{finish_x:.2f} {finish_y:.2f}"
    )


def half_year_gauge_chart(
    data: dict,
) -> str:
    execution = max(
        0.0,
        number(
            data.get(
                "execution_pct"
            )
        ),
    )

    maximum = 120.0

    display_execution = min(
        execution,
        maximum,
    )

    width = 410
    height = 225

    center_x = 205
    center_y = 178

    zone_radius = 135
    value_radius = 113

    start_angle = 180.0
    finish_angle = 360.0

    angle_80 = (
        start_angle
        + 80
        / maximum
        * 180
    )

    angle_100 = (
        start_angle
        + 100
        / maximum
        * 180
    )

    value_angle = (
        start_angle
        + display_execution
        / maximum
        * 180
    )

    needle_x, needle_y = _polar(
        center_x,
        center_y,
        value_radius - 7,
        value_angle,
    )

    threshold_x1, threshold_y1 = _polar(
        center_x,
        center_y,
        zone_radius - 19,
        angle_100,
    )

    threshold_x2, threshold_y2 = _polar(
        center_x,
        center_y,
        zone_radius + 8,
        angle_100,
    )

    ticks: list[str] = []

    for tick_value in (
        0,
        20,
        40,
        60,
        80,
        100,
        120,
    ):
        angle = (
            start_angle
            + tick_value
            / maximum
            * 180
        )

        tick_x1, tick_y1 = _polar(
            center_x,
            center_y,
            zone_radius - 10,
            angle,
        )

        tick_x2, tick_y2 = _polar(
            center_x,
            center_y,
            zone_radius + 1,
            angle,
        )

        label_x, label_y = _polar(
            center_x,
            center_y,
            zone_radius + 19,
            angle,
        )

        ticks.append(
            f"""
            <line
                x1="{tick_x1:.2f}"
                y1="{tick_y1:.2f}"
                x2="{tick_x2:.2f}"
                y2="{tick_y2:.2f}"
                stroke="{MUTED}"
                stroke-width="1"
            />

            <text
                x="{label_x:.2f}"
                y="{label_y + 4:.2f}"
                text-anchor="middle"
                font-family="Arial, sans-serif"
                font-size="11"
                fill="{NAVY}"
            >
                {tick_value}
            </text>
            """
        )

    return f"""
    <svg
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 {width} {height}"
        width="100%"
        height="100%"
        preserveAspectRatio="xMidYMid meet"
        role="img"
        aria-label="Спидометр выполнения полугодового плана"
    >

        <!--
            ВАЖНО:
            не оставляем SVG прозрачным.
            Цвет совпадает с .plans-half-year-column.
        -->
        <rect
            x="0"
            y="0"
            width="{width}"
            height="{height}"
            fill="#F8F5ED"
        />

        <!-- 0–80 -->
        <path
            d="{_arc(
                center_x,
                center_y,
                zone_radius,
                start_angle,
                angle_80,
            )}"
            fill="none"
            stroke="{SOFT_PINK}"
            stroke-width="34"
        />

        <!-- 80–100 -->
        <path
            d="{_arc(
                center_x,
                center_y,
                zone_radius,
                angle_80,
                angle_100,
            )}"
            fill="none"
            stroke="{SOFT_YELLOW}"
            stroke-width="34"
        />

        <!-- 100–120 -->
        <path
            d="{_arc(
                center_x,
                center_y,
                zone_radius,
                angle_100,
                finish_angle,
            )}"
            fill="none"
            stroke="{SOFT_GREEN}"
            stroke-width="34"
        />

        <!-- Выполнено -->
        <path
            d="{_arc(
                center_x,
                center_y,
                value_radius,
                start_angle,
                value_angle,
            )}"
            fill="none"
            stroke="{CORAL}"
            stroke-width="15"
        />

        {"".join(ticks)}

        <!-- План = 100% -->
        <line
            x1="{threshold_x1:.2f}"
            y1="{threshold_y1:.2f}"
            x2="{threshold_x2:.2f}"
            y2="{threshold_y2:.2f}"
            stroke="{GREEN}"
            stroke-width="5"
        />

        <text
            x="{threshold_x2 + 4:.2f}"
            y="{threshold_y2 - 4:.2f}"
            font-family="Arial, sans-serif"
            font-size="10"
            font-weight="700"
            fill="{GREEN}"
        >
            план
        </text>

        <!-- Стрелка -->
        <line
            x1="{center_x}"
            y1="{center_y}"
            x2="{needle_x:.2f}"
            y2="{needle_y:.2f}"
            stroke="{NAVY}"
            stroke-width="5"
            stroke-linecap="round"
        />

        <circle
            cx="{center_x}"
            cy="{center_y}"
            r="11"
            fill="{YELLOW}"
            stroke="{NAVY}"
            stroke-width="3"
        />

        <circle
            cx="{center_x}"
            cy="{center_y}"
            r="4"
            fill="{CORAL}"
        />

        <!-- Значение -->
        <text
            x="{center_x}"
            y="137"
            text-anchor="middle"
            font-family="Georgia, 'Times New Roman', serif"
            font-size="37"
            font-weight="700"
            fill="{NAVY}"
        >
            {execution:.1f}%
        </text>

        <text
            x="{center_x}"
            y="157"
            text-anchor="middle"
            font-family="Arial, sans-serif"
            font-size="11"
            font-weight="700"
            letter-spacing="2"
            fill="{MUTED}"
        >
            ПОЛНОГО ПЛАНА
        </text>

    </svg>
    """

# =============================================================================
# ПЛАН И ФАКТ ПО МЕСЯЦАМ
# =============================================================================


def monthly_plan_fact_chart(
    rows: list[dict],
    *,
    report_month: int,
) -> str:
    source = list(
        rows
        or []
    )

    if not source:
        return _svg_empty(
            "Нет данных план/факт по месяцам."
        )

    by_month: dict[int, dict] = {}

    for row in source:
        month_number = int(
            number(
                row.get(
                    "month"
                )
            )
        )

        if not 1 <= month_number <= 12:
            continue

        by_month[month_number] = {
            "month": month_number,
            "plan": number(
                row.get(
                    "plan"
                )
            ),
            "fact": number(
                row.get(
                    "fact"
                )
            ),
        }

    prepared = [
        by_month.get(
            month_number,
            {
                "month": month_number,
                "plan": 0,
                "fact": 0,
            },
        )
        for month_number in range(
            1,
            13,
        )
    ]

    width = 760
    height = 285

    left = 63
    right = 18
    top = 42
    bottom = 47

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

    maximum = max(
        max(
            row["plan"]
            for row in prepared
        ),
        max(
            row["fact"]
            for row in prepared
        ),
        1,
    ) * 1.2

    slot_width = (
        plot_width
        / 12
    )

    bar_width = min(
        18,
        slot_width * 0.32,
    )

    grid_html: list[str] = []

    for index in range(5):
        ratio = index / 4

        y = (
            top
            + plot_height
            - ratio
            * plot_height
        )

        value = maximum * ratio

        grid_html.append(
            f"""
            <line
                x1="{left}"
                y1="{y:.2f}"
                x2="{left + plot_width}"
                y2="{y:.2f}"
                stroke="{GRID}"
                stroke-width="1"
            />

            <text
                x="{left - 8}"
                y="{y + 3:.2f}"
                text-anchor="end"
                font-family="Arial, sans-serif"
                font-size="9"
                fill="{MUTED}"
            >
                {escape(_format_mln(value))}
            </text>
            """
        )

    bars_html: list[str] = []

    for index, row in enumerate(
        prepared
    ):
        month_number = row["month"]

        center_x = (
            left
            + index
            * slot_width
            + slot_width / 2
        )

        plan_value = row["plan"]
        fact_value = row["fact"]

        plan_height = (
            plan_value
            / maximum
            * plot_height
        )

        fact_height = (
            fact_value
            / maximum
            * plot_height
        )

        plan_x = (
            center_x
            - bar_width
            - 2
        )

        fact_x = (
            center_x
            + 2
        )

        plan_y = (
            top
            + plot_height
            - plan_height
        )

        fact_y = (
            top
            + plot_height
            - fact_height
        )

        fact_opacity = (
            1
            if month_number <= report_month
            else 0.14
        )

        plan_text = (
            f"{plan_value / 1_000_000:.0f}"
            if plan_value > 0
            else ""
        )

        fact_text = (
            f"{fact_value / 1_000_000:.0f}"
            if fact_value > 0
            else ""
        )

        bars_html.append(
            f"""
            <rect
                x="{plan_x:.2f}"
                y="{plan_y:.2f}"
                width="{bar_width:.2f}"
                height="{plan_height:.2f}"
                fill="{NAVY}"
                fill-opacity="0.26"
                stroke="{NAVY}"
                stroke-width="1"
            />

            <rect
                x="{fact_x:.2f}"
                y="{fact_y:.2f}"
                width="{bar_width:.2f}"
                height="{fact_height:.2f}"
                fill="{CORAL}"
                fill-opacity="{fact_opacity}"
                stroke="{CORAL}"
                stroke-width="1"
            />

            <text
                x="{plan_x + bar_width / 2:.2f}"
                y="{max(plan_y - 5, 11):.2f}"
                text-anchor="middle"
                font-family="Arial, sans-serif"
                font-size="8"
                font-weight="700"
                fill="{NAVY}"
            >
                {plan_text}
            </text>

            <text
                x="{fact_x + bar_width / 2:.2f}"
                y="{max(fact_y - 5, 11):.2f}"
                text-anchor="middle"
                font-family="Arial, sans-serif"
                font-size="8"
                font-weight="700"
                fill="{CORAL_DARK}"
            >
                {fact_text}
            </text>

            <text
                x="{center_x:.2f}"
                y="{height - 23}"
                text-anchor="middle"
                font-family="Arial, sans-serif"
                font-size="10"
                font-weight="700"
                fill="{NAVY}"
            >
                {MONTHS[month_number]}
            </text>
            """
        )

    return f"""
    <svg
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 {width} {height}"
        width="100%"
        height="100%"
        preserveAspectRatio="xMidYMid meet"
        role="img"
        aria-label="План и факт по месяцам"
    >
        <rect
            x="0"
            y="0"
            width="{width}"
            height="{height}"

        />

        <g>
            {"".join(grid_html)}
        </g>

        <line
            x1="{left}"
            y1="{top + plot_height}"
            x2="{left + plot_width}"
            y2="{top + plot_height}"
            stroke="{MUTED}"
            stroke-width="1"
        />

        <g>
            {"".join(bars_html)}
        </g>

        <g transform="translate({left}, 17)">
            <rect
                x="0"
                y="0"
                width="13"
                height="9"
                fill="{NAVY}"
                fill-opacity="0.26"
                stroke="{NAVY}"
                stroke-width="1"
            />

            <text
                x="19"
                y="8"
                font-family="Arial, sans-serif"
                font-size="10"
                fill="{MUTED}"
            >
                План
            </text>

            <rect
                x="67"
                y="0"
                width="13"
                height="9"
                fill="{CORAL}"
            />

            <text
                x="86"
                y="8"
                font-family="Arial, sans-serif"
                font-size="10"
                fill="{MUTED}"
            >
                Факт
            </text>

            <text
                x="142"
                y="8"
                font-family="Arial, sans-serif"
                font-size="9"
                fill="{MUTED}"
            >
                цифры над столбцами — млн ₽
            </text>
        </g>
    </svg>
    """


# =============================================================================
# PROPHET: ПЛАН / ФАКТ / ПРОГНОЗ
# =============================================================================

def prophet_monthly_chart(
    rows: list[dict],
) -> str:
    source = list(
        rows
        or []
    )

    if not source:
        return _svg_empty(
            "Нет месячных данных Prophet."
        )

    prepared: list[dict] = []

    for row in source:
        parsed_month = pd.to_datetime(
            str(
                row.get(
                    "month",
                    "",
                )
            )
            + "-01",
            errors="coerce",
        )

        if pd.isna(
            parsed_month
        ):
            continue

        plan = number(
            row.get(
                "plan"
            )
        )

        fact = number(
            row.get(
                "fact"
            )
        )

        forecast = number(
            row.get(
                "forecast"
            )
        )

        expected = number(
            row.get(
                "expected_total"
            )
        )

        execution_pct = (
            expected
            / plan
            * 100
            if plan > 0
            else 0.0
        )

        prepared.append(
            {
                "month": int(
                    parsed_month.month
                ),
                "plan": plan,
                "fact": fact,
                "forecast": forecast,
                "expected": expected,
                "execution_pct": execution_pct,
            }
        )

    if not prepared:
        return _svg_empty(
            "Нет корректных данных Prophet."
        )

    width = 1060
    height = 345

    left = 67
    right = 23
    top = 54
    bottom = 78

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

    maximum = max(
        max(
            max(
                row["plan"],
                row["fact"],
                row["forecast"],
                row["expected"],
            )
            for row in prepared
        ),
        1.0,
    ) * 1.22

    slot_width = (
        plot_width
        / len(prepared)
    )

    bar_width = min(
        18,
        slot_width * 0.20,
    )

    # -------------------------------------------------------------
    # Сетка
    # -------------------------------------------------------------

    grid_html: list[str] = []

    for index in range(5):
        ratio = (
            index / 4
        )

        y = (
            top
            + plot_height
            - ratio
            * plot_height
        )

        value = (
            maximum
            * ratio
        )

        grid_html.append(
            f"""
            <line
                x1="{left}"
                y1="{y:.2f}"
                x2="{left + plot_width}"
                y2="{y:.2f}"
                stroke="{GRID}"
                stroke-width="1"
            />

            <text
                x="{left - 8}"
                y="{y + 3:.2f}"
                text-anchor="end"
                font-family="Arial, sans-serif"
                font-size="9"
                fill="{MUTED}"
            >
                {escape(_format_mln(value))}
            </text>
            """
        )

    elements: list[str] = []

    expected_points: list[
        tuple[float, float]
    ] = []

    badges: list[str] = []

    for index, row in enumerate(
        prepared
    ):
        center_x = (
            left
            + index
            * slot_width
            + slot_width / 2
        )

        columns = [
            {
                "value": row["plan"],
                "color": NAVY,
                "opacity": 0.26,
                "x": (
                    center_x
                    - bar_width * 1.5
                    - 4
                ),
                "label": NAVY,
            },
            {
                "value": row["fact"],
                "color": CORAL,
                "opacity": 1.0,
                "x": (
                    center_x
                    - bar_width / 2
                ),
                "label": CORAL_DARK,
            },
            {
                "value": row["forecast"],
                "color": TEAL,
                "opacity": 0.66,
                "x": (
                    center_x
                    + bar_width / 2
                    + 4
                ),
                "label": TEAL,
            },
        ]

        for column in columns:
            value = number(
                column["value"]
            )

            if value <= 0:
                continue

            bar_height = (
                value
                / maximum
                * plot_height
            )

            y = (
                top
                + plot_height
                - bar_height
            )

            inside = (
                bar_height >= 31
            )

            text_y = (
                y + 14
                if inside
                else max(
                    y - 6,
                    12,
                )
            )

            text_fill = (
                PAPER
                if (
                    inside
                    and column["opacity"]
                    >= 0.55
                )
                else column["label"]
            )

            elements.append(
                f"""
                <rect
                    x="{column['x']:.2f}"
                    y="{y:.2f}"
                    width="{bar_width:.2f}"
                    height="{bar_height:.2f}"
                    fill="{column['color']}"
                    fill-opacity="{column['opacity']}"
                    stroke="{column['color']}"
                    stroke-width="0.8"
                />

                <text
                    x="{column['x'] + bar_width / 2:.2f}"
                    y="{text_y:.2f}"
                    text-anchor="middle"
                    font-family="Arial, sans-serif"
                    font-size="8"
                    font-weight="800"
                    fill="{text_fill}"
                >
                    {value / 1_000_000:.0f}
                </text>
                """
            )

        expected_y = (
            top
            + plot_height
            - row["expected"]
            / maximum
            * plot_height
        )

        expected_points.append(
            (
                center_x,
                expected_y,
            )
        )

        if row["expected"] > 0:
            elements.append(
                f"""
                <text
                    x="{center_x:.2f}"
                    y="{max(expected_y - 10, 13):.2f}"
                    text-anchor="middle"
                    font-family="Arial, sans-serif"
                    font-size="9"
                    font-weight="800"
                    fill="{GREEN}"
                >
                    {row["expected"] / 1_000_000:.0f}
                </text>
                """
            )

        # месяц
        elements.append(
            f"""
            <text
                x="{center_x:.2f}"
                y="{top + plot_height + 20}"
                text-anchor="middle"
                font-family="Arial, sans-serif"
                font-size="10"
                font-weight="800"
                fill="{NAVY}"
            >
                {MONTHS[row["month"]]}
            </text>
            """
        )

        pct = (
            row["execution_pct"]
        )

        if pct >= 100:
            badge_fill = SOFT_GREEN
            badge_text = GREEN

        elif pct >= 90:
            badge_fill = SOFT_YELLOW
            badge_text = NAVY

        else:
            badge_fill = SOFT_PINK
            badge_text = CORAL_DARK

        badge_width = 49
        badge_height = 19

        badge_x = (
            center_x
            - badge_width / 2
        )

        badge_y = (
            top
            + plot_height
            + 31
        )

        badges.append(
            f"""
            <rect
                x="{badge_x:.2f}"
                y="{badge_y:.2f}"
                width="{badge_width}"
                height="{badge_height}"
                rx="2"
                fill="{badge_fill}"
                stroke="{BORDER}"
                stroke-width="0.7"
            />

            <text
                x="{center_x:.2f}"
                y="{badge_y + 13:.2f}"
                text-anchor="middle"
                font-family="Arial, sans-serif"
                font-size="9"
                font-weight="800"
                fill="{badge_text}"
            >
                {pct:.0f}%
            </text>
            """
        )

    expected_points_text = (
        _points_attribute(
            expected_points
        )
    )

    expected_dots = "".join(
        f"""
        <circle
            cx="{x:.2f}"
            cy="{y:.2f}"
            r="5"
            fill="{GREEN}"
            stroke="{PAPER}"
            stroke-width="2"
        />
        """
        for x, y
        in expected_points
    )

    return f"""
    <svg
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 {width} {height}"
        width="100%"
        height="100%"
        preserveAspectRatio="xMidYMid meet"
        role="img"
        aria-label="План, факт и прогноз Prophet"
    >

        <!-- ФОН СТРАНИЦЫ -->
        <rect
            x="0"
            y="0"
            width="{width}"
            height="{height}"
            fill="{PAPER}"
        />

        {"".join(grid_html)}

        <line
            x1="{left}"
            y1="{top + plot_height}"
            x2="{left + plot_width}"
            y2="{top + plot_height}"
            stroke="{MUTED}"
            stroke-width="1"
        />

        {"".join(elements)}

        <polyline
            points="{expected_points_text}"
            fill="none"
            stroke="{GREEN}"
            stroke-width="4"
            stroke-linecap="round"
            stroke-linejoin="round"
        />

        {expected_dots}

        {"".join(badges)}

        <!-- ЛЕГЕНДА -->
        <g transform="translate({left}, 20)">

            <rect
                x="0"
                y="0"
                width="13"
                height="9"
                fill="{NAVY}"
                fill-opacity="0.26"
                stroke="{NAVY}"
            />

            <text
                x="19"
                y="8"
                font-family="Arial, sans-serif"
                font-size="10"
                fill="{MUTED}"
            >
                План
            </text>

            <rect
                x="67"
                y="0"
                width="13"
                height="9"
                fill="{CORAL}"
            />

            <text
                x="86"
                y="8"
                font-family="Arial, sans-serif"
                font-size="10"
                fill="{MUTED}"
            >
                Факт
            </text>

            <rect
                x="132"
                y="0"
                width="13"
                height="9"
                fill="{TEAL}"
                fill-opacity="0.66"
            />

            <text
                x="151"
                y="8"
                font-family="Arial, sans-serif"
                font-size="10"
                fill="{MUTED}"
            >
                Прогноз
            </text>

            <line
                x1="225"
                y1="5"
                x2="247"
                y2="5"
                stroke="{GREEN}"
                stroke-width="4"
            />

            <circle
                cx="236"
                cy="5"
                r="4"
                fill="{GREEN}"
            />

            <text
                x="255"
                y="8"
                font-family="Arial, sans-serif"
                font-size="10"
                fill="{MUTED}"
            >
                Ожидаемый итог
            </text>

            <text
                x="385"
                y="8"
                font-family="Arial, sans-serif"
                font-size="9"
                fill="{MUTED}"
            >
                значения — млн ₽ · внизу — выполнение месячного плана
            </text>

        </g>

    </svg>
    """

# =============================================================================
# ТРАЕКТОРИЯ ВЫПОЛНЕНИЯ ПОЛУГОДОВОГО ПЛАНА
# =============================================================================


def half_year_trajectory_chart(
    data: dict,
) -> str:
    """
    Траектория ТЕКУЩЕГО полугодия.

    Например для периода 01.07–31.12:
        показывает только июль–декабрь.

    Зелёная линия:
        накопительный план текущего полугодия.

        Для текущего месяца используется PLAN_TO_DATE,
        а не полный месячный план.

        Для будущих месяцев:
            полный план текущего месяца
            + планы следующих месяцев.

    Коралловая линия:
        фактически выполненная доля полного
        полугодового плана.

    ВАЖНО:
        running_plan / running_fact из monthly_rows
        не используются, потому что они накоплены
        с января и относятся ко всему году.
    """

    rows = list(
        data.get(
            "monthly_rows",
            [],
        )
        or []
    )

    full_plan = number(
        data.get(
            "plan_amount"
        )
    )

    fact_amount = number(
        data.get(
            "fact_amount"
        )
    )

    plan_to_date = number(
        data.get(
            "plan_to_date"
        )
    )

    start_date = pd.to_datetime(
        data.get(
            "date_start"
        ),
        errors="coerce",
    )

    finish_date = pd.to_datetime(
        data.get(
            "date_finish"
        ),
        errors="coerce",
    )

    if (
        not rows
        or full_plan <= 0
        or pd.isna(start_date)
        or pd.isna(finish_date)
    ):
        return _svg_empty(
            "Нет данных для траектории полугодия.",
            width=760,
            height=190,
        )

    start_month = int(
        start_date.month
    )

    finish_month = int(
        finish_date.month
    )

    # -------------------------------------------------------------
    # Определяем текущий месяц по данным факта
    #
    # Для текущего полугодового payload дата отчёта отдельно
    # сюда не передаётся.
    #
    # Последний месяц внутри периода, где есть факт,
    # является текущим отчётным месяцем.
    # -------------------------------------------------------------

    by_month: dict[int, dict] = {}

    for row in rows:
        month_number = (
            _month_number_from_row(
                row
            )
        )

        if month_number is None:
            continue

        if not (
            start_month
            <= month_number
            <= finish_month
        ):
            continue

        by_month[
            month_number
        ] = {
            "month": month_number,
            "plan": number(
                row.get(
                    "plan"
                )
            ),
            "fact": number(
                row.get(
                    "fact"
                )
            ),
        }

    period_months = list(
        range(
            start_month,
            finish_month + 1,
        )
    )

    if not period_months:
        return _svg_empty(
            "Нет месяцев текущего полугодия.",
            width=760,
            height=190,
        )

    # Текущий месяц = последний месяц периода,
    # в котором уже присутствует факт.
    fact_months = [
        month
        for month in period_months
        if number(
            by_month
            .get(month, {})
            .get("fact")
        ) != 0
    ]

    current_month = (
        max(fact_months)
        if fact_months
        else start_month
    )

    # -------------------------------------------------------------
    # Готовим корректную траекторию
    # -------------------------------------------------------------

    prepared: list[dict] = []

    cumulative_full_month_plan = 0.0

    for month in period_months:
        month_data = by_month.get(
            month,
            {
                "plan": 0.0,
                "fact": 0.0,
            },
        )

        month_plan = number(
            month_data.get(
                "plan"
            )
        )

        # ---------------------------------------------------------
        # ПЛАН
        # ---------------------------------------------------------

        if month < current_month:
            # Закрытые месяцы:
            # используем полный план месяца.
            cumulative_full_month_plan += (
                month_plan
            )

            planned_amount = (
                cumulative_full_month_plan
            )

        elif month == current_month:
            # Самое важное:
            # для текущей даты используем план К ДАТЕ.
            #
            # plan_to_date уже рассчитан корректно тем же
            # механизмом, что WB Plan Monitor.
            planned_amount = (
                plan_to_date
            )

            # Для расчёта будущих месячных точек
            # после этого месяца нам всё равно нужен
            # полный план текущего месяца.
            cumulative_full_month_plan += (
                month_plan
            )

        else:
            cumulative_full_month_plan += (
                month_plan
            )

            planned_amount = (
                cumulative_full_month_plan
            )

        plan_pct = (
            planned_amount
            / full_plan
            * 100
            if full_plan > 0
            else 0.0
        )

        # ---------------------------------------------------------
        # ФАКТ
        # ---------------------------------------------------------

        if month == current_month:
            # Это точно тот же факт, что стоит
            # рядом со спидометром.
            fact_value = fact_amount

            fact_pct = (
                fact_value
                / full_plan
                * 100
                if full_plan > 0
                else 0.0
            )

        elif month < current_month:
            # Если отчёт будет уже в августе/сентябре,
            # для закрытых месяцев считаем накопительный
            # факт внутри ТЕКУЩЕГО полугодия.
            cumulative_fact = sum(
                number(
                    by_month
                    .get(m, {})
                    .get("fact")
                )
                for m in period_months
                if m <= month
            )

            fact_pct = (
                cumulative_fact
                / full_plan
                * 100
                if full_plan > 0
                else 0.0
            )

        else:
            fact_pct = None

        prepared.append(
            {
                "month": month,
                "plan_pct": plan_pct,
                "fact_pct": fact_pct,
                "is_current": (
                    month
                    == current_month
                ),
            }
        )

    # -------------------------------------------------------------
    # Размеры
    # -------------------------------------------------------------

    width = 760
    height = 190

    left = 51
    right = 20
    top = 42
    bottom = 35

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

    maximum = max(
        100.0,
        max(
            row["plan_pct"]
            for row in prepared
        ),
        max(
            (
                row["fact_pct"]
                or 0
            )
            for row in prepared
        ),
    )

    maximum = max(
        maximum * 1.06,
        105.0,
    )

    denominator = max(
        len(prepared) - 1,
        1,
    )

    def point_x(
        index: int,
    ) -> float:
        return (
            left
            + index
            * plot_width
            / denominator
        )

    def point_y(
        value: float,
    ) -> float:
        return (
            top
            + plot_height
            - value
            / maximum
            * plot_height
        )

    # -------------------------------------------------------------
    # Сетка
    # -------------------------------------------------------------

    grid_html: list[str] = []

    for value in (
        0,
        25,
        50,
        75,
        100,
    ):
        y = point_y(
            value
        )

        grid_html.append(
            f"""
            <line
                x1="{left}"
                y1="{y:.2f}"
                x2="{left + plot_width}"
                y2="{y:.2f}"
                stroke="{GRID}"
                stroke-width="1"
                stroke-dasharray="4 4"
            />

            <text
                x="{left - 8}"
                y="{y + 3:.2f}"
                text-anchor="end"
                font-family="Arial, sans-serif"
                font-size="9"
                fill="{MUTED}"
            >
                {value}%
            </text>
            """
        )

    # -------------------------------------------------------------
    # Плановая линия
    # -------------------------------------------------------------

    plan_points = [
        (
            point_x(index),
            point_y(
                row["plan_pct"]
            ),
        )
        for index, row
        in enumerate(prepared)
    ]

    plan_points_text = (
        _points_attribute(
            plan_points
        )
    )

    # -------------------------------------------------------------
    # Факт — только существующие точки
    # -------------------------------------------------------------

    fact_rows = [
        (
            index,
            row,
        )
        for index, row
        in enumerate(prepared)
        if row["fact_pct"] is not None
    ]

    fact_points = [
        (
            point_x(index),
            point_y(
                row["fact_pct"]
            ),
        )
        for index, row
        in fact_rows
    ]

    fact_points_text = (
        _points_attribute(
            fact_points
        )
        if fact_points
        else ""
    )

    # -------------------------------------------------------------
    # Точки плана
    # -------------------------------------------------------------

    plan_dots: list[str] = []

    for index, row in enumerate(
        prepared
    ):
        x = point_x(index)
        y = point_y(
            row["plan_pct"]
        )

        label = (
            f"{row['plan_pct']:.1f}%"
            .replace(".", ",")
        )

        plan_dots.append(
            f"""
            <circle
                cx="{x:.2f}"
                cy="{y:.2f}"
                r="4"
                fill="#F8F5ED"
                stroke="{TEAL}"
                stroke-width="2"
            />

            <text
                x="{x:.2f}"
                y="{max(y - 8, 35):.2f}"
                text-anchor="middle"
                font-family="Arial, sans-serif"
                font-size="8"
                font-weight="800"
                fill="{TEAL}"
            >
                {label}
            </text>
            """
        )

    # -------------------------------------------------------------
    # Фактические точки
    # -------------------------------------------------------------

    fact_dots: list[str] = []

    for index, row in fact_rows:
        x = point_x(index)

        y = point_y(
            row["fact_pct"]
        )

        label = (
            f"{row['fact_pct']:.1f}%"
            .replace(".", ",")
        )

        fact_dots.append(
            f"""
            <circle
                cx="{x:.2f}"
                cy="{y:.2f}"
                r="5.5"
                fill="{CORAL}"
                stroke="#F8F5ED"
                stroke-width="2"
            />

            <text
                x="{x:.2f}"
                y="{min(y + 16, height - 30):.2f}"
                text-anchor="middle"
                font-family="Arial, sans-serif"
                font-size="8"
                font-weight="800"
                fill="{CORAL_DARK}"
            >
                {label}
            </text>
            """
        )

    # -------------------------------------------------------------
    # Месяцы
    # -------------------------------------------------------------

    month_html: list[str] = []

    for index, row in enumerate(
        prepared
    ):
        x = point_x(index)

        weight = (
            "800"
            if row["is_current"]
            else "700"
        )

        month_html.append(
            f"""
            <text
                x="{x:.2f}"
                y="{height - 12}"
                text-anchor="middle"
                font-family="Arial, sans-serif"
                font-size="10"
                font-weight="{weight}"
                fill="{NAVY}"
            >
                {MONTHS[row["month"]]}
            </text>
            """
        )

    return f"""
    <svg
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 {width} {height}"
        width="100%"
        height="100%"
        preserveAspectRatio="xMidYMid meet"
        role="img"
        aria-label="Траектория выполнения текущего полугодия"
    >

        <!-- фон совпадает с правой колонкой -->
        <rect
            x="0"
            y="0"
            width="{width}"
            height="{height}"
            fill="#F8F5ED"
        />

        <text
            x="{left}"
            y="14"
            font-family="Arial, sans-serif"
            font-size="10"
            font-weight="800"
            fill="{NAVY}"
        >
            ТРАЕКТОРИЯ ВЫПОЛНЕНИЯ ПЛАНА
        </text>

        <text
            x="{left}"
            y="27"
            font-family="Arial, sans-serif"
            font-size="8"
            fill="{MUTED}"
        >
            накопительно, % полного плана текущего полугодия
        </text>

        <!-- легенда -->
        <g transform="translate({width - 238}, 17)">

            <line
                x1="0"
                y1="0"
                x2="20"
                y2="0"
                stroke="{TEAL}"
                stroke-width="3"
            />

            <text
                x="26"
                y="3"
                font-family="Arial, sans-serif"
                font-size="8"
                fill="{MUTED}"
            >
                план
            </text>

            <line
                x1="78"
                y1="0"
                x2="98"
                y2="0"
                stroke="{CORAL}"
                stroke-width="4"
            />

            <text
                x="104"
                y="3"
                font-family="Arial, sans-serif"
                font-size="8"
                fill="{MUTED}"
            >
                факт
            </text>

        </g>

        {"".join(grid_html)}

        <!-- план -->
        <polyline
            points="{plan_points_text}"
            fill="none"
            stroke="{TEAL}"
            stroke-width="3"
            stroke-linecap="round"
            stroke-linejoin="round"
        />

        {"".join(plan_dots)}

        <!-- факт -->
        {
            f'''
            <polyline
                points="{fact_points_text}"
                fill="none"
                stroke="{CORAL}"
                stroke-width="4"
                stroke-linecap="round"
                stroke-linejoin="round"
            />
            '''
            if len(fact_points) > 1
            else ""
        }

        {"".join(fact_dots)}

        {"".join(month_html)}

    </svg>
    """