# # gear/app/daily_sales/daily_brief/presentation/pages/financial_charts.py

# from __future__ import annotations

# from html import escape

# import pandas as pd

# from ...helpers import number


# # =============================================================================
# # ПАЛИТРА
# # =============================================================================


# NAVY = "#14213D"
# CORAL = "#E85D75"

# GREEN = "#16805E"
# GREEN_SOFT = "#DDF2E9"

# RED = "#C23D58"
# RED_SOFT = "#F8E1E6"

# PURPLE = "#8067AB"
# PURPLE_SOFT = "#EEE9F5"

# YELLOW = "#E9B949"
# YELLOW_SOFT = "#FAF0CC"

# GREY = "#667085"
# GREY_LIGHT = "#E9EDF1"

# PAPER = "#FFFDF7"


# # =============================================================================
# # ОБЩИЕ ФУНКЦИИ
# # =============================================================================


# def _safe(value) -> str:
#     return escape(
#         str(
#             value
#             if value is not None
#             else ""
#         )
#     )


# def _money_short(
#     value,
# ) -> str:
#     value = number(value)

#     sign = "−" if value < 0 else ""

#     value = abs(value)

#     if value >= 1_000_000_000:
#         text = (
#             f"{value / 1_000_000_000:.1f}"
#             .replace(".", ",")
#         )
#         return f"{sign}{text} млрд ₽"

#     if value >= 1_000_000:
#         text = (
#             f"{value / 1_000_000:.1f}"
#             .replace(".", ",")
#         )
#         return f"{sign}{text} млн ₽"

#     if value >= 1_000:
#         text = (
#             f"{value / 1_000:.0f}"
#             .replace(".", ",")
#         )
#         return f"{sign}{text} тыс ₽"

#     return (
#         f"{sign}{value:,.0f} ₽"
#         .replace(",", " ")
#     )


# def _pct(
#     value,
#     digits: int = 1,
# ) -> str:
#     return (
#         f"{number(value):.{digits}f}%"
#         .replace(".", ",")
#     )


# # =============================================================================
# # МОСТ ФИНАНСОВОГО РЕЗУЛЬТАТА
# # =============================================================================


# def financial_bridge_chart(
#     finance: dict,
# ) -> str:
#     """
#     Визуальный мост экономики дня.

#     Логика:
#         Выручка без НДС
#         → себестоимость
#         → комиссия WB
#         → управленческая маржа
#         → расходы WB
#         → финансовый результат

#     Значения маржи и финрезультата берём готовыми из dashboard.
#     Мы не пересчитываем их формулой на странице.
#     """

#     revenue = number(
#         finance.get("revenue_net")
#     )

#     cogs = abs(
#         number(
#             finance.get("cogs_man")
#         )
#     )

#     commission = abs(
#         number(
#             finance.get("commission")
#         )
#     )

#     margin = number(
#         finance.get("margin_man")
#     )

#     wb_costs = abs(
#         number(
#             finance.get("wb_costs")
#         )
#     )

#     result = number(
#         finance.get("wb_result")
#     )

#     values = [
#         abs(revenue),
#         abs(cogs),
#         abs(commission),
#         abs(margin),
#         abs(wb_costs),
#         abs(result),
#     ]

#     maximum = max(
#         values
#         or [1]
#     ) or 1

#     width = 700
#     height = 245

#     chart_top = 53
#     chart_bottom = 184
#     chart_height = (
#         chart_bottom
#         - chart_top
#     )

#     columns = [
#         (
#             "Выручка",
#             "без НДС",
#             revenue,
#             NAVY,
#         ),
#         (
#             "Себестоимость",
#             "управленческая",
#             -cogs,
#             CORAL,
#         ),
#         (
#             "Комиссия",
#             "Wildberries",
#             -commission,
#             PURPLE,
#         ),
#         (
#             "Маржа",
#             "управленческая",
#             margin,
#             GREEN
#             if margin >= 0
#             else RED,
#         ),
#         (
#             "WB расходы",
#             "на реализацию",
#             -wb_costs,
#             YELLOW,
#         ),
#         (
#             "Финрезультат",
#             "после WB расходов",
#             result,
#             GREEN
#             if result >= 0
#             else RED,
#         ),
#     ]

#     x_positions = [
#         23,
#         139,
#         255,
#         371,
#         487,
#         603,
#     ]

#     bar_width = 72

#     parts = [
#         f"""
#         <svg
#             viewBox="0 0 {width} {height}"
#             xmlns="http://www.w3.org/2000/svg"
#             role="img"
#             aria-label="Мост финансового результата"
#         >
#         """
#     ]

#     # ---------------------------------------------------------------------
#     # Базовая линия
#     # ---------------------------------------------------------------------

#     parts.append(
#         f"""
#         <line
#             x1="15"
#             y1="{chart_bottom}"
#             x2="{width - 15}"
#             y2="{chart_bottom}"
#             stroke="{GREY_LIGHT}"
#             stroke-width="1"
#         />
#         """
#     )

#     # ---------------------------------------------------------------------
#     # Колонки
#     # ---------------------------------------------------------------------

#     for index, (
#         label,
#         sublabel,
#         value,
#         color,
#     ) in enumerate(columns):

#         x = x_positions[index]

#         bar_height = max(
#             abs(value)
#             / maximum
#             * chart_height,
#             4,
#         )

#         y = (
#             chart_bottom
#             - bar_height
#         )

#         # Значения-расходы показываем светлым фоном,
#         # итоговые/положительные показатели — более насыщенно.
#         opacity = (
#             0.42
#             if index in (1, 2, 4)
#             else 0.88
#         )

#         sign = (
#             "−"
#             if value < 0
#             else ""
#         )

#         parts.append(
#             f"""
#             <rect
#                 x="{x}"
#                 y="{y:.1f}"
#                 width="{bar_width}"
#                 height="{bar_height:.1f}"
#                 fill="{color}"
#                 opacity="{opacity}"
#             />

#             <text
#                 x="{x + bar_width / 2}"
#                 y="{max(y - 8, 15):.1f}"
#                 text-anchor="middle"
#                 fill="{NAVY}"
#                 font-family="Arial, sans-serif"
#                 font-size="11"
#                 font-weight="700"
#             >
#                 {_safe(sign + _money_short(abs(value)))}
#             </text>

#             <text
#                 x="{x + bar_width / 2}"
#                 y="207"
#                 text-anchor="middle"
#                 fill="{NAVY}"
#                 font-family="Arial, sans-serif"
#                 font-size="9"
#                 font-weight="700"
#             >
#                 {_safe(label)}
#             </text>

#             <text
#                 x="{x + bar_width / 2}"
#                 y="221"
#                 text-anchor="middle"
#                 fill="{GREY}"
#                 font-family="Arial, sans-serif"
#                 font-size="7.2"
#             >
#                 {_safe(sublabel)}
#             </text>
#             """
#         )

#         if index < len(columns) - 1:
#             arrow_x = (
#                 x
#                 + bar_width
#                 + 18
#             )

#             parts.append(
#                 f"""
#                 <text
#                     x="{arrow_x}"
#                     y="139"
#                     text-anchor="middle"
#                     fill="{GREY}"
#                     font-family="Arial, sans-serif"
#                     font-size="15"
#                 >
#                     →
#                 </text>
#                 """
#             )

#     parts.append("</svg>")

#     return "".join(parts)


# # =============================================================================
# # ЭКОНОМИКА 100 ₽
# # =============================================================================


# def economics_100_chart(
#     finance: dict,
# ) -> str:
#     """
#     Показывает структуру каждых 100 ₽ выручки без НДС.
#     """

#     economics = (
#         finance.get("economics_100")
#         or {}
#     )

#     rows = [
#         (
#             "Себестоимость",
#             max(
#                 number(
#                     economics.get("cogs")
#                 ),
#                 0,
#             ),
#             CORAL,
#         ),
#         (
#             "Комиссия WB",
#             max(
#                 number(
#                     economics.get("commission")
#                 ),
#                 0,
#             ),
#             PURPLE,
#         ),
#         (
#             "WB расходы",
#             max(
#                 number(
#                     economics.get("wb_costs")
#                 ),
#                 0,
#             ),
#             YELLOW,
#         ),
#     ]

#     result = number(
#         economics.get("result")
#     )

#     width = 330
#     height = 202

#     x_bar = 108
#     bar_width = 145

#     parts = [
#         f"""
#         <svg
#             viewBox="0 0 {width} {height}"
#             xmlns="http://www.w3.org/2000/svg"
#         >
#         """
#     ]

#     y = 23

#     for label, value, color in rows:
#         display_width = min(
#             value,
#             100,
#         ) / 100 * bar_width

#         parts.append(
#             f"""
#             <text
#                 x="2"
#                 y="{y + 10}"
#                 fill="{NAVY}"
#                 font-family="Arial, sans-serif"
#                 font-size="9"
#                 font-weight="700"
#             >
#                 {_safe(label)}
#             </text>

#             <rect
#                 x="{x_bar}"
#                 y="{y}"
#                 width="{bar_width}"
#                 height="13"
#                 fill="{GREY_LIGHT}"
#             />

#             <rect
#                 x="{x_bar}"
#                 y="{y}"
#                 width="{display_width:.1f}"
#                 height="13"
#                 fill="{color}"
#                 opacity=".72"
#             />

#             <text
#                 x="320"
#                 y="{y + 10}"
#                 text-anchor="end"
#                 fill="{NAVY}"
#                 font-family="Arial, sans-serif"
#                 font-size="9"
#                 font-weight="700"
#             >
#                 {_safe(_pct(value))}
#             </text>
#             """
#         )

#         y += 38

#     result_color = (
#         GREEN
#         if result >= 0
#         else RED
#     )

#     parts.append(
#         f"""
#         <line
#             x1="0"
#             y1="143"
#             x2="330"
#             y2="143"
#             stroke="{GREY_LIGHT}"
#         />

#         <text
#             x="2"
#             y="169"
#             fill="{GREY}"
#             font-family="Arial, sans-serif"
#             font-size="8"
#             font-weight="700"
#         >
#             ОСТАЁТСЯ В ФИНРЕЗУЛЬТАТЕ
#         </text>

#         <text
#             x="328"
#             y="177"
#             text-anchor="end"
#             fill="{result_color}"
#             font-family="Georgia, serif"
#             font-size="24"
#             font-weight="700"
#         >
#             {_safe(_pct(result))}
#         </text>

#         <text
#             x="328"
#             y="193"
#             text-anchor="end"
#             fill="{GREY}"
#             font-family="Arial, sans-serif"
#             font-size="7.5"
#         >
#             из каждых 100 ₽ выручки без НДС
#         </text>

#         </svg>
#         """
#     )

#     return "".join(parts)


# # =============================================================================
# # ДИНАМИКА ФИНАНСОВОГО РЕЗУЛЬТАТА
# # =============================================================================


# def financial_result_trend_chart(
#     rows: list[dict],
# ) -> str:
#     """
#     30-дневная динамика WB financial result.

#     Нулевая линия обязательна:
#     сразу видно прибыльные и убыточные дни.
#     """

#     prepared = []

#     for row in rows or []:
#         parsed = pd.to_datetime(
#             row.get("date"),
#             errors="coerce",
#         )

#         if pd.isna(parsed):
#             continue

#         prepared.append(
#             {
#                 "date": parsed,
#                 "value": number(
#                     row.get("wb_result")
#                 ),
#             }
#         )

#     if not prepared:
#         return ""

#     width = 690
#     height = 205

#     left = 48
#     right = 12
#     top = 22
#     bottom = 35

#     plot_width = (
#         width
#         - left
#         - right
#     )

#     plot_height = (
#         height
#         - top
#         - bottom
#     )

#     values = [
#         row["value"]
#         for row in prepared
#     ]

#     minimum = min(
#         min(values),
#         0,
#     )

#     maximum = max(
#         max(values),
#         0,
#     )

#     span = (
#         maximum
#         - minimum
#     ) or 1

#     def y_pos(value):
#         return (
#             top
#             + (
#                 maximum
#                 - value
#             )
#             / span
#             * plot_height
#         )

#     zero_y = y_pos(0)

#     count = len(prepared)

#     step = (
#         plot_width
#         / max(
#             count - 1,
#             1,
#         )
#     )

#     points = []

#     for index, row in enumerate(
#         prepared
#     ):
#         x = (
#             left
#             + index * step
#         )

#         y = y_pos(
#             row["value"]
#         )

#         points.append(
#             f"{x:.1f},{y:.1f}"
#         )

#     parts = [
#         f"""
#         <svg
#             viewBox="0 0 {width} {height}"
#             xmlns="http://www.w3.org/2000/svg"
#         >

#         <line
#             x1="{left}"
#             y1="{zero_y:.1f}"
#             x2="{width - right}"
#             y2="{zero_y:.1f}"
#             stroke="{GREY}"
#             stroke-width="1"
#             stroke-dasharray="4 4"
#             opacity=".7"
#         />

#         <text
#             x="{left - 6}"
#             y="{zero_y + 3:.1f}"
#             text-anchor="end"
#             fill="{GREY}"
#             font-family="Arial, sans-serif"
#             font-size="7"
#         >
#             0
#         </text>

#         <polyline
#             points="{" ".join(points)}"
#             fill="none"
#             stroke="{NAVY}"
#             stroke-width="2.4"
#             stroke-linejoin="round"
#             stroke-linecap="round"
#         />
#         """
#     ]

#     for index, row in enumerate(
#         prepared
#     ):
#         x = (
#             left
#             + index * step
#         )

#         value = row["value"]
#         y = y_pos(value)

#         color = (
#             GREEN
#             if value >= 0
#             else RED
#         )

#         parts.append(
#             f"""
#             <circle
#                 cx="{x:.1f}"
#                 cy="{y:.1f}"
#                 r="2.7"
#                 fill="{color}"
#             />
#             """
#         )

#     # ---------------------------------------------------------------------
#     # Подписи дат — только несколько опорных,
#     # чтобы график оставался чистым.
#     # ---------------------------------------------------------------------

#     indexes = sorted(
#         {
#             0,
#             count // 2,
#             count - 1,
#         }
#     )

#     for index in indexes:
#         row = prepared[index]

#         x = (
#             left
#             + index * step
#         )

#         label = row[
#             "date"
#         ].strftime(
#             "%d.%m"
#         )

#         parts.append(
#             f"""
#             <text
#                 x="{x:.1f}"
#                 y="{height - 10}"
#                 text-anchor="middle"
#                 fill="{GREY}"
#                 font-family="Arial, sans-serif"
#                 font-size="7"
#             >
#                 {label}
#             </text>
#             """
#         )

#     # Текущее значение

#     last = prepared[-1]

#     parts.append(
#         f"""
#         <text
#             x="{width - right}"
#             y="12"
#             text-anchor="end"
#             fill="{NAVY}"
#             font-family="Arial, sans-serif"
#             font-size="9"
#             font-weight="700"
#         >
#             последний день · {_safe(_money_short(last["value"]))}
#         </text>

#         </svg>
#         """
#     )

#     return "".join(parts)


# # =============================================================================
# # ВОЗВРАТЫ ПО КАТЕГОРИЯМ
# # =============================================================================


# def return_categories_chart(
#     rows: list[dict],
#     *,
#     limit: int = 5,
# ) -> str:
#     """
#     Компактный SVG top-категорий по сумме возвратов.
#     """

#     rows = list(
#         rows
#         or []
#     )[:limit]

#     if not rows:
#         return ""

#     values = [
#         abs(
#             number(
#                 row.get(
#                     "returns_amount"
#                 )
#             )
#         )
#         for row in rows
#     ]

#     maximum = max(
#         values
#         or [1]
#     ) or 1

#     width = 340
#     height = 175

#     bar_x = 112
#     bar_max = 145

#     parts = [
#         f"""
#         <svg
#             viewBox="0 0 {width} {height}"
#             xmlns="http://www.w3.org/2000/svg"
#         >
#         """
#     ]

#     y = 10

#     for row, value in zip(
#         rows,
#         values,
#     ):
#         label = (
#             row.get("name")
#             or "Не указано"
#         )

#         display_width = (
#             value
#             / maximum
#             * bar_max
#         )

#         parts.append(
#             f"""
#             <text
#                 x="0"
#                 y="{y + 10}"
#                 fill="{NAVY}"
#                 font-family="Arial, sans-serif"
#                 font-size="8"
#                 font-weight="700"
#             >
#                 {_safe(str(label)[:24])}
#             </text>

#             <rect
#                 x="{bar_x}"
#                 y="{y}"
#                 width="{bar_max}"
#                 height="12"
#                 fill="{GREY_LIGHT}"
#             />

#             <rect
#                 x="{bar_x}"
#                 y="{y}"
#                 width="{display_width:.1f}"
#                 height="12"
#                 fill="{CORAL}"
#                 opacity=".74"
#             />

#             <text
#                 x="337"
#                 y="{y + 10}"
#                 text-anchor="end"
#                 fill="{NAVY}"
#                 font-family="Arial, sans-serif"
#                 font-size="7.7"
#                 font-weight="700"
#             >
#                 {_safe(_money_short(value))}
#             </text>
#             """
#         )

#         y += 32

#     parts.append("</svg>")

#     return "".join(parts)




# gear/app/daily_sales/daily_brief/presentation/pages/financial_charts.py

from __future__ import annotations

from html import escape

import pandas as pd

from ...helpers import number


# =============================================================================
# ЦВЕТА
# =============================================================================


PAPER = "#FFFDF7"

NAVY = "#14213D"
MUTED = "#667085"
GRID = "#D7DCE2"
GRID_LIGHT = "#E9EDF1"

CORAL = "#E85D75"
CORAL_SOFT = "#F3B7C3"

GREEN = "#16805E"
GREEN_SOFT = "#DDF2E9"

RED = "#C23D58"
RED_SOFT = "#F7DCE2"

PURPLE = "#8067AB"
PURPLE_SOFT = "#D3C9E3"

YELLOW = "#E9B949"
YELLOW_SOFT = "#F6E6AB"


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


def _money_short(
    value,
    *,
    signed: bool = False,
) -> str:
    value = number(value)

    sign = ""

    if signed:
        if value > 0:
            sign = "+"
        elif value < 0:
            sign = "−"

    elif value < 0:
        sign = "−"

    absolute = abs(value)

    if absolute >= 1_000_000_000:
        text = (
            f"{absolute / 1_000_000_000:.1f}"
            .replace(".", ",")
        )

        return (
            f"{sign}{text} млрд ₽"
        )

    if absolute >= 1_000_000:
        text = (
            f"{absolute / 1_000_000:.1f}"
            .replace(".", ",")
        )

        return (
            f"{sign}{text} млн ₽"
        )

    if absolute >= 1_000:
        text = (
            f"{absolute / 1_000:.0f}"
            .replace(".", ",")
        )

        return (
            f"{sign}{text} тыс ₽"
        )

    return (
        f"{sign}{absolute:,.0f} ₽"
        .replace(",", " ")
    )


def _pct(
    value,
    digits: int = 1,
    *,
    signed: bool = False,
) -> str:
    value = number(value)

    sign = ""

    if signed:
        if value > 0:
            sign = "+"
        elif value < 0:
            sign = "−"

    elif value < 0:
        sign = "−"

    return (
        f"{sign}{abs(value):.{digits}f}%"
        .replace(".", ",")
    )


# =============================================================================
# МОСТ ДНЕВНОГО РЕЗУЛЬТАТА
# =============================================================================


def financial_bridge_chart(
    finance: dict,
) -> str:

    revenue = number(
        finance.get(
            "revenue_net"
        )
    )

    cogs = abs(
        number(
            finance.get(
                "cogs_man"
            )
        )
    )

    commission = abs(
        number(
            finance.get(
                "commission"
            )
        )
    )

    margin = number(
        finance.get(
            "margin_man"
        )
    )

    wb_costs = abs(
        number(
            finance.get(
                "wb_costs"
            )
        )
    )

    result = number(
        finance.get(
            "wb_result"
        )
    )

    bars = [
        {
            "title": "Выручка",
            "subtitle": "без НДС",
            "value": revenue,
            "display": revenue,
            "color": NAVY,
        },

        {
            "title": "Себестоимость",
            "subtitle": "управленческая FIFO",
            "value": cogs,
            "display": -cogs,
            "color": CORAL_SOFT,
        },

        {
            "title": "Комиссия",
            "subtitle": "Wildberries",
            "value": commission,
            "display": -commission,
            "color": PURPLE_SOFT,
        },

        {
            "title": "Маржа",
            "subtitle": "до прочих расходов WB",
            "value": abs(margin),
            "display": margin,
            "color": (
                GREEN
                if margin >= 0
                else RED
            ),
        },

        {
            "title": "WB расходы",
            "subtitle": "распределяемые",
            "value": wb_costs,
            "display": -wb_costs,
            "color": YELLOW_SOFT,
        },

        {
            "title": "Финрезультат",
            "subtitle": "после расходов WB",
            "value": abs(result),
            "display": result,
            "color": (
                GREEN
                if result >= 0
                else RED
            ),
        },
    ]

    maximum = max(
        [
            number(
                item["value"]
            )
            for item in bars
        ]
        or [1]
    ) or 1

    width = 720
    height = 240

    baseline = 175
    top = 47

    available_height = (
        baseline - top
    )

    x_positions = [
        16,
        137,
        258,
        379,
        500,
        621,
    ]

    bar_width = 73

    html = [
        f"""
        <svg
            viewBox="0 0 {width} {height}"
            xmlns="http://www.w3.org/2000/svg"
        >
        """
    ]

    html.append(
        f"""
        <line
            x1="8"
            y1="{baseline}"
            x2="{width - 8}"
            y2="{baseline}"
            stroke="{GRID_LIGHT}"
            stroke-width="1"
        />
        """
    )

    for index, item in enumerate(
        bars
    ):

        height_value = max(
            number(
                item["value"]
            )
            / maximum
            * available_height,
            3,
        )

        x = x_positions[
            index
        ]

        y = (
            baseline
            - height_value
        )

        html.append(
            f"""
            <rect
                x="{x}"
                y="{y:.1f}"
                width="{bar_width}"
                height="{height_value:.1f}"
                fill="{item['color']}"
                opacity=".88"
            />

            <text
                x="{x + bar_width / 2}"
                y="{max(y - 8, 14):.1f}"
                text-anchor="middle"
                fill="{NAVY}"
                font-family="Arial, sans-serif"
                font-size="10"
                font-weight="700"
            >
                {_safe(
                    _money_short(
                        item["display"]
                    )
                )}
            </text>

            <text
                x="{x + bar_width / 2}"
                y="198"
                text-anchor="middle"
                fill="{NAVY}"
                font-family="Arial, sans-serif"
                font-size="8"
                font-weight="700"
            >
                {_safe(item["title"])}
            </text>

            <text
                x="{x + bar_width / 2}"
                y="214"
                text-anchor="middle"
                fill="{MUTED}"
                font-family="Arial, sans-serif"
                font-size="6.6"
            >
                {_safe(item["subtitle"])}
            </text>
            """
        )

        if index < len(bars) - 1:
            html.append(
                f"""
                <text
                    x="{x + bar_width + 23}"
                    y="129"
                    text-anchor="middle"
                    fill="{MUTED}"
                    font-family="Arial, sans-serif"
                    font-size="16"
                >
                    →
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
# UNIT ECONOMICS — 100 ₽
# =============================================================================


def economics_100_chart(
    finance: dict,
) -> str:

    economics = (
        finance.get(
            "economics_100"
        )
        or {}
    )

    rows = [
        (
            "Себестоимость",
            number(
                economics.get(
                    "cogs"
                )
            ),
            CORAL,
        ),

        (
            "Комиссия WB",
            number(
                economics.get(
                    "commission"
                )
            ),
            PURPLE,
        ),

        (
            "WB расходы",
            number(
                economics.get(
                    "wb_costs"
                )
            ),
            YELLOW,
        ),
    ]

    result = number(
        economics.get(
            "result"
        )
    )

    width = 330
    height = 190

    bar_x = 113
    bar_width = 150

    html = [
        f"""
        <svg
            viewBox="0 0 {width} {height}"
            xmlns="http://www.w3.org/2000/svg"
        >
        """
    ]

    y = 18

    for (
        label,
        value,
        color,
    ) in rows:

        safe_value = max(
            value,
            0,
        )

        fill_width = min(
            safe_value,
            100,
        ) / 100 * bar_width

        html.append(
            f"""
            <text
                x="0"
                y="{y + 10}"
                fill="{NAVY}"
                font-family="Arial, sans-serif"
                font-size="8.4"
                font-weight="700"
            >
                {_safe(label)}
            </text>

            <rect
                x="{bar_x}"
                y="{y}"
                width="{bar_width}"
                height="13"
                fill="{GRID_LIGHT}"
            />

            <rect
                x="{bar_x}"
                y="{y}"
                width="{fill_width:.1f}"
                height="13"
                fill="{color}"
                opacity=".68"
            />

            <text
                x="328"
                y="{y + 10}"
                text-anchor="end"
                fill="{NAVY}"
                font-family="Arial, sans-serif"
                font-size="8.5"
                font-weight="700"
            >
                {_safe(_pct(value))}
            </text>
            """
        )

        y += 39

    result_color = (
        GREEN
        if result >= 0
        else RED
    )

    html.append(
        f"""
        <line
            x1="0"
            y1="139"
            x2="330"
            y2="139"
            stroke="{GRID}"
            stroke-width="1"
        />

        <text
            x="0"
            y="158"
            fill="{MUTED}"
            font-family="Arial, sans-serif"
            font-size="6.6"
            font-weight="700"
        >
            ОСТАЁТСЯ В ФИНРЕЗУЛЬТАТЕ
        </text>

        <text
            x="328"
            y="169"
            text-anchor="end"
            fill="{result_color}"
            font-family="Georgia, serif"
            font-size="24"
            font-weight="700"
        >
            {_safe(_pct(result))}
        </text>

        <text
            x="328"
            y="183"
            text-anchor="end"
            fill="{MUTED}"
            font-family="Arial, sans-serif"
            font-size="6.3"
        >
            из каждых 100 ₽ выручки без НДС
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
# 30 ДНЕЙ
# =============================================================================


def financial_result_trend_chart(
    rows: list[dict],
) -> str:

    prepared = []

    for row in rows or []:
        parsed = pd.to_datetime(
            row.get("date"),
            errors="coerce",
        )

        if pd.isna(parsed):
            continue

        prepared.append(
            {
                "date": parsed,

                "result": number(
                    row.get(
                        "wb_result"
                    )
                ),
            }
        )

    if not prepared:
        return ""

    width = 720
    height = 190

    left = 43
    right = 10
    top = 27
    bottom = 28

    plot_width = (
        width - left - right
    )

    plot_height = (
        height - top - bottom
    )

    values = [
        item["result"]
        for item in prepared
    ]

    minimum = min(
        min(values),
        0,
    )

    maximum = max(
        max(values),
        0,
    )

    span = (
        maximum - minimum
    ) or 1

    def y_pos(
        value,
    ):
        return (
            top
            + (
                maximum - value
            )
            / span
            * plot_height
        )

    zero_y = y_pos(
        0
    )

    count = len(
        prepared
    )

    step = (
        plot_width
        / max(
            count - 1,
            1,
        )
    )

    points = []

    for index, row in enumerate(
        prepared
    ):
        x = (
            left
            + index * step
        )

        y = y_pos(
            row["result"]
        )

        points.append(
            f"{x:.1f},{y:.1f}"
        )

    html = [
        f"""
        <svg
            viewBox="0 0 {width} {height}"
            xmlns="http://www.w3.org/2000/svg"
        >
        """
    ]

    html.append(
        f"""
        <line
            x1="{left}"
            y1="{zero_y:.1f}"
            x2="{width - right}"
            y2="{zero_y:.1f}"
            stroke="{MUTED}"
            stroke-width="1"
            stroke-dasharray="5 5"
            opacity=".55"
        />

        <text
            x="{left - 7}"
            y="{zero_y + 3:.1f}"
            text-anchor="end"
            fill="{MUTED}"
            font-family="Arial"
            font-size="6.5"
        >
            0
        </text>

        <polyline
            points="{" ".join(points)}"
            fill="none"
            stroke="{NAVY}"
            stroke-width="2.5"
            stroke-linecap="round"
            stroke-linejoin="round"
        />
        """
    )

    for index, row in enumerate(
        prepared
    ):
        x = (
            left
            + index * step
        )

        y = y_pos(
            row["result"]
        )

        color = (
            GREEN
            if row["result"] >= 0
            else RED
        )

        html.append(
            f"""
            <circle
                cx="{x:.1f}"
                cy="{y:.1f}"
                r="2.8"
                fill="{color}"
            />
            """
        )

    label_indexes = sorted(
        {
            0,
            count // 2,
            count - 1,
        }
    )

    for index in label_indexes:
        row = prepared[
            index
        ]

        x = (
            left
            + index * step
        )

        html.append(
            f"""
            <text
                x="{x:.1f}"
                y="{height - 6}"
                text-anchor="middle"
                fill="{MUTED}"
                font-family="Arial"
                font-size="6.5"
            >
                {row["date"].strftime("%d.%m")}
            </text>
            """
        )

    last = prepared[-1]

    html.append(
        f"""
        <text
            x="{width - right}"
            y="12"
            text-anchor="end"
            fill="{NAVY}"
            font-family="Arial"
            font-size="8"
            font-weight="700"
        >
            последний день · {_safe(_money_short(last["result"]))}
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
# НЕДЕЛЬНАЯ ЛЕНТА
# =============================================================================


def weekly_result_strip(
    rows: list[dict],
) -> str:
    """
    Газетная недельная heat-strip.

    Цвет определяется не абсолютной суммой результата,
    а рентабельностью — wb_result / revenue_net.
    """

    rows = list(
        rows
        or []
    )

    if not rows:
        return ""

    values = [
        number(
            row.get(
                "result_pct"
            )
        )
        for row in rows
    ]

    max_positive = max(
        [
            value
            for value in values
            if value > 0
        ]
        or [1]
    )

    max_negative = abs(
        min(
            [
                value
                for value in values
                if value < 0
            ]
            or [0]
        )
    ) or 1

    def cell_color(
        value: float,
    ) -> str:

        if value < 0:
            ratio = min(
                abs(value)
                / max_negative,
                1,
            )

            if ratio > 0.65:
                return "#E8A1B0"

            if ratio > 0.30:
                return "#F2C8D0"

            return "#FAE7EB"

        ratio = min(
            value
            / max_positive,
            1,
        )

        if ratio > 0.75:
            return "#84C5AE"

        if ratio > 0.45:
            return "#AFE0CF"

        if ratio > 0.20:
            return "#D8EEE6"

        return "#EEF6F2"

    cell_width = 88
    gap = 6

    width = (
        len(rows)
        * cell_width
        + max(
            len(rows) - 1,
            0,
        )
        * gap
    )

    height = 125

    html = [
        f"""
        <svg
            viewBox="0 0 {width} {height}"
            xmlns="http://www.w3.org/2000/svg"
        >
        """
    ]

    x = 0

    for row in rows:

        result_pct = number(
            row.get(
                "result_pct"
            )
        )

        result = number(
            row.get(
                "wb_result"
            )
        )

        start = pd.to_datetime(
            row.get(
                "date_from"
            ),
            errors="coerce",
        )

        end = pd.to_datetime(
            row.get(
                "date_to"
            ),
            errors="coerce",
        )

        period = ""

        if (
            not pd.isna(start)
            and not pd.isna(end)
        ):
            period = (
                f"{start:%d.%m}–{end:%d.%m}"
            )

        current = bool(
            row.get(
                "is_current"
            )
        )

        border_width = (
            2
            if current
            else 1
        )

        border_color = (
            NAVY
            if current
            else GRID
        )

        html.append(
            f"""
            <rect
                x="{x}"
                y="2"
                width="{cell_width}"
                height="106"
                fill="{cell_color(result_pct)}"
                stroke="{border_color}"
                stroke-width="{border_width}"
            />

            <text
                x="{x + 8}"
                y="18"
                fill="{CORAL if current else MUTED}"
                font-family="Arial"
                font-size="6.5"
                font-weight="700"
            >
                {_safe(row.get("label"))}
            </text>

            <text
                x="{x + 8}"
                y="32"
                fill="{MUTED}"
                font-family="Arial"
                font-size="6"
            >
                {_safe(period)}
            </text>

            <text
                x="{x + 8}"
                y="61"
                fill="{GREEN if result_pct >= 0 else RED}"
                font-family="Georgia"
                font-size="17"
                font-weight="700"
            >
                {_safe(_pct(result_pct))}
            </text>

            <text
                x="{x + 8}"
                y="80"
                fill="{NAVY}"
                font-family="Arial"
                font-size="7"
                font-weight="700"
            >
                {_safe(_money_short(result))}
            </text>

            <text
                x="{x + 8}"
                y="96"
                fill="{MUTED}"
                font-family="Arial"
                font-size="5.8"
            >
                {"оперативно" if current else "неделя"}
            </text>
            """
        )

        x += (
            cell_width
            + gap
        )

    html.append(
        """
        </svg>
        """
    )

    return "".join(
        html
    )