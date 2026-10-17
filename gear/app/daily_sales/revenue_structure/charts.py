# gear/app/daily_sales/revenue_structure/charts.py

from __future__ import annotations

from datetime import date, datetime
from typing import Any

import pandas as pd
import plotly.graph_objects as go


# =========================================================
# Общие настройки дизайна
# =========================================================

CHART_HEIGHT = 470


# =========================================================
# Цвета
# =========================================================

TEXT_COLOR = "#1D2939"
MUTED_COLOR = "#667085"
LIGHT_TEXT_COLOR = "#98A2B3"

GRID_COLOR = "#EAECF0"
AXIS_COLOR = "#D0D5DD"

# Выручка
BAR_COLOR = "rgba(53, 95, 140, 0.68)"
BAR_BORDER = "#355F8C"

# Маржинальность
MARGIN_COLOR = "#1F6F5C"

# Отрицательная маржинальность
NEGATIVE_MARGIN_COLOR = "#B42318"

# Нулевая линия
ZERO_LINE_COLOR = "#D92D20"


# =========================================================
# Палитра donut
# =========================================================

DONUT_COLORS = [
    "#355F8C",
    "#4F7CAC",
    "#668F80",
    "#7A8B99",
    "#4E6E81",
    "#829AB1",
    "#A68A64",
    "#738290",
    "#B0B8C1",
]


# =========================================================
# Шрифт
# =========================================================

FONT_FAMILY = (
    "Inter, "
    "-apple-system, "
    "BlinkMacSystemFont, "
    "'Segoe UI', "
    "Arial, "
    "sans-serif"
)


# =========================================================
# Вспомогательные функции
# =========================================================

def _format_compact_money(
    value: float,
) -> str:
    """
    Компактное отображение денежных значений.

    Примеры:
        1 250 000 -> 1,3 млн ₽
        350 000   -> 350 тыс. ₽
    """

    value = float(value or 0)
    abs_value = abs(value)

    if abs_value >= 1_000_000_000:
        result = (
            f"{value / 1_000_000_000:.1f} млрд ₽"
        )

    elif abs_value >= 1_000_000:
        result = (
            f"{value / 1_000_000:.1f} млн ₽"
        )

    elif abs_value >= 1_000:
        result = (
            f"{value / 1_000:.0f} тыс. ₽"
        )

    else:
        result = (
            f"{value:,.0f} ₽"
        )

    return (
        result
        .replace(",", " ")
        .replace(".", ",")
    )


def _format_period_date(
    value: Any,
) -> str | None:
    """
    Приводит дату к формату ДД.ММ.ГГГГ.

    Поддерживает:
    - datetime
    - date
    - pandas.Timestamp
    - строки ISO
    """

    if value is None:
        return None

    try:
        parsed = pd.to_datetime(
            value,
            errors="coerce",
        )

        if pd.isna(parsed):
            return None

        return parsed.strftime(
            "%d.%m.%Y"
        )

    except Exception:
        return None


def _extract_period_from_rows(
    rows: list[dict],
) -> tuple[Any | None, Any | None]:
    """
    Пытается автоматически найти период внутри rows.

    Это сделано для обратной совместимости.

    Возможные названия полей:
    - date_from / date_to
    - start_date / end_date
    - period_start / period_end
    - min_date / max_date
    """

    if not rows:
        return None, None

    first_row = rows[0]

    start_candidates = [
        "date_from",
        "start_date",
        "period_start",
        "min_date",
    ]

    end_candidates = [
        "date_to",
        "end_date",
        "period_end",
        "max_date",
    ]

    date_from = None
    date_to = None

    for column in start_candidates:
        if column in first_row:
            date_from = first_row.get(
                column
            )
            break

    for column in end_candidates:
        if column in first_row:
            date_to = first_row.get(
                column
            )
            break

    return (
        date_from,
        date_to,
    )


def _build_period_label(
    rows: list[dict] | None = None,
    date_from: Any | None = None,
    date_to: Any | None = None,
) -> str:
    """
    Возвращает красивую подпись периода.

    Например:
        Период: 13.07.2026 — 14.07.2026
    """

    rows = rows or []

    if (
        date_from is None
        or date_to is None
    ):
        (
            rows_date_from,
            rows_date_to,
        ) = _extract_period_from_rows(
            rows
        )

        if date_from is None:
            date_from = rows_date_from

        if date_to is None:
            date_to = rows_date_to

    formatted_from = _format_period_date(
        date_from
    )

    formatted_to = _format_period_date(
        date_to
    )

    if (
        formatted_from
        and formatted_to
    ):
        if (
            formatted_from
            == formatted_to
        ):
            return (
                f"Период: {formatted_from}"
            )

        return (
            f"Период: "
            f"{formatted_from} — "
            f"{formatted_to}"
        )

    if formatted_from:
        return (
            f"Период: с {formatted_from}"
        )

    if formatted_to:
        return (
            f"Период: по {formatted_to}"
        )

    return "Период: выбранный период"


def _prepare_numeric_columns(
    df: pd.DataFrame,
    columns: list[str],
) -> pd.DataFrame:
    """
    Гарантирует наличие числовых колонок.
    """

    for column in columns:

        if column not in df.columns:
            df[column] = 0

        df[column] = pd.to_numeric(
            df[column],
            errors="coerce",
        ).fillna(0)

    return df


# =========================================================
# Пустой график
# =========================================================

def empty_figure(
    text: str = "Нет данных",
) -> go.Figure:

    fig = go.Figure()

    fig.add_annotation(
        text=text,

        x=0.5,
        y=0.5,

        xref="paper",
        yref="paper",

        showarrow=False,

        font={
            "family": FONT_FAMILY,
            "size": 14,
            "color": MUTED_COLOR,
        },
    )

    fig.update_layout(
        height=CHART_HEIGHT,

        paper_bgcolor="white",
        plot_bgcolor="white",

        xaxis={
            "visible": False,
        },

        yaxis={
            "visible": False,
        },

        margin={
            "l": 20,
            "r": 20,
            "t": 20,
            "b": 20,
        },

        font={
            "family": FONT_FAMILY,
        },
    )

    return fig


# =========================================================
# Основной график
#
# Выручка без НДС
# +
# Управленческая маржинальность
#
# Маржа:
#
# Выручка без НДС
# - Себестоимость
# - Комиссия WB
#
# НЕ учитываются:
# - маркетинг
# - логистика
# - штрафы
# - прочие расходы WB
#
# gross_profit_book / gross_profit_man —
# исторические названия колонок.
#
# По смыслу это МАРЖА В РУБЛЯХ,
# а не чистая / операционная прибыль.
# =========================================================

def build_revenue_margin_chart(
    rows: list[dict],
    top_n: int = 15,
    date_from: Any | None = None,
    date_to: Any | None = None,
) -> go.Figure:
    """
    TOP категорий по выручке без НДС.

    Показывает:
    - выручку без НДС;
    - управленческую маржинальность, %.

    Маржа считается после:
    - себестоимости;
    - комиссии WB.

    Не включает:
    - маркетинг;
    - логистику;
    - штрафы;
    - прочие расходы WB.
    """

    if not rows:
        return empty_figure()

    df = pd.DataFrame(
        rows
    ).copy()

    if df.empty:
        return empty_figure()

    # =====================================================
    # Период
    # =====================================================

    period_label = _build_period_label(
        rows=rows,
        date_from=date_from,
        date_to=date_to,
    )

    # =====================================================
    # Числовые колонки
    # =====================================================

    numeric_columns = [
        "revenue_vatless",
        "revenue_share_pct",

        "net_comission",
        "commission_pct",

        "cogs_book",
        "cogs_man",

        # Названия сохранены для совместимости
        # с текущим data layer.
        # Фактически это маржа, ₽.
        "gross_profit_book",
        "gross_profit_man",

        "margin_book_pct",
        "margin_man_pct",

        "products_count",
        "net_qty",
    ]

    df = _prepare_numeric_columns(
        df,
        numeric_columns,
    )

    if "name" not in df.columns:
        df["name"] = "Не указано"

    df["name"] = (
        df["name"]
        .fillna("Не указано")
        .astype(str)
    )

    # =====================================================
    # TOP N по выручке
    #
    # После сортировки самый крупный показатель
    # будет визуально находиться сверху.
    # =====================================================

    df = (
        df
        .nlargest(
            top_n,
            "revenue_vatless",
        )
        .sort_values(
            "revenue_vatless",
            ascending=True,
        )
        .reset_index(
            drop=True
        )
    )

    if df.empty:
        return empty_figure()

    # =====================================================
    # Цвет маржинальности
    # =====================================================

    margin_colors = [
        (
            NEGATIVE_MARGIN_COLOR
            if value < 0
            else MARGIN_COLOR
        )
        for value
        in df["margin_man_pct"]
    ]

    # =====================================================
    # График
    # =====================================================

    fig = go.Figure()

    # =====================================================
    # Выручка без НДС
    # =====================================================

    fig.add_trace(
        go.Bar(
            x=df[
                "revenue_vatless"
            ],

            y=df[
                "name"
            ],

            orientation="h",

            name="Выручка без НДС",

            marker={
                "color": BAR_COLOR,

                "line": {
                    "color": BAR_BORDER,
                    "width": 0.8,
                },
            },

            text=[
                _format_compact_money(
                    value
                )
                for value
                in df[
                    "revenue_vatless"
                ]
            ],

            textposition="outside",

            cliponaxis=False,

            textfont={
                "family": FONT_FAMILY,
                "size": 10,
                "color": TEXT_COLOR,
            },

            customdata=df[
                [
                    "name",
                    "revenue_share_pct",

                    "net_comission",
                    "commission_pct",

                    "gross_profit_book",
                    "gross_profit_man",

                    "margin_book_pct",
                    "margin_man_pct",

                    "cogs_book",
                    "cogs_man",

                    "products_count",
                    "net_qty",
                ]
            ].to_numpy(),

            hovertemplate=(
                "<b>%{customdata[0]}</b>"
                "<br>"
                f"<span style='color:{MUTED_COLOR}'>"
                f"{period_label}"
                "</span>"
                "<br>"
                "<span style='color:#98A2B3'>"
                "────────────────────────"
                "</span>"
                "<br><br>"

                "Выручка без НДС: "
                "<b>%{x:,.0f} ₽</b>"
                "<br>"

                "Доля выручки: "
                "%{customdata[1]:.1f}%"
                "<br><br>"

                "<b>Комиссия WB</b>"
                "<br>"

                "Сумма: "
                "%{customdata[2]:,.0f} ₽"
                "<br>"

                "Доля: "
                "%{customdata[3]:.1f}%"
                "<br><br>"

                "<b>Маржа после с/с и комиссии WB</b>"
                "<br>"

                "Маржа бух.: "
                "%{customdata[4]:,.0f} ₽"
                "<br>"

                "Маржа упр.: "
                "<b>%{customdata[5]:,.0f} ₽</b>"
                "<br><br>"

                "Маржинальность бух.: "
                "%{customdata[6]:.1f}%"
                "<br>"

                "Маржинальность упр.: "
                "<b>%{customdata[7]:.1f}%</b>"
                "<br><br>"

                "<b>Себестоимость</b>"
                "<br>"

                "С/с бух.: "
                "%{customdata[8]:,.0f} ₽"
                "<br>"

                "С/с упр.: "
                "%{customdata[9]:,.0f} ₽"
                "<br><br>"

                "Товаров: "
                "%{customdata[10]:,.0f}"
                "<br>"

                "Количество нетто: "
                "%{customdata[11]:,.0f}"
                "<br><br>"

                "<span style='color:#98A2B3'>"
                "Маркетинг, логистика и штрафы "
                "не учитываются"
                "</span>"

                "<extra></extra>"
            ),
        )
    )

    # =====================================================
    # Управленческая маржинальность
    # =====================================================

    fig.add_trace(
        go.Scatter(
            x=df[
                "margin_man_pct"
            ],

            y=df[
                "name"
            ],

            xaxis="x2",

            mode="markers+text",

            name="Упр. маржинальность",

            marker={
                "size": 9,

                "color": margin_colors,

                "line": {
                    "color": "white",
                    "width": 1.5,
                },
            },

            text=[
                f"{value:.0f}%"
                for value
                in df[
                    "margin_man_pct"
                ]
            ],

            textposition="middle right",

            textfont={
                "family": FONT_FAMILY,
                "size": 10,
                "color": MARGIN_COLOR,
            },

            customdata=df[
                [
                    "name",
                    "margin_man_pct",
                    "margin_book_pct",
                    "gross_profit_man",
                    "gross_profit_book",
                    "net_comission",
                    "cogs_man",
                    "cogs_book",
                ]
            ].to_numpy(),

            hovertemplate=(
                "<b>%{customdata[0]}</b>"
                "<br>"
                f"<span style='color:{MUTED_COLOR}'>"
                f"{period_label}"
                "</span>"
                "<br>"
                "<span style='color:#98A2B3'>"
                "────────────────────────"
                "</span>"
                "<br><br>"

                "Маржинальность упр.: "
                "<b>%{customdata[1]:.1f}%</b>"
                "<br>"

                "Маржинальность бух.: "
                "%{customdata[2]:.1f}%"
                "<br><br>"

                "Маржа упр.: "
                "<b>%{customdata[3]:,.0f} ₽</b>"
                "<br>"

                "Маржа бух.: "
                "%{customdata[4]:,.0f} ₽"
                "<br><br>"

                "Комиссия WB: "
                "%{customdata[5]:,.0f} ₽"
                "<br>"

                "С/с упр.: "
                "%{customdata[6]:,.0f} ₽"
                "<br>"

                "С/с бух.: "
                "%{customdata[7]:,.0f} ₽"
                "<br><br>"

                "<span style='color:#98A2B3'>"
                "Маржа = выручка без НДС − "
                "себестоимость − комиссия WB"
                "<br>"
                "Без маркетинга, логистики и штрафов"
                "</span>"

                "<extra></extra>"
            ),
        )
    )

    # =====================================================
    # Диапазон оси маржинальности
    # =====================================================

    margin_min = float(
        df[
            "margin_man_pct"
        ].min()
    )

    margin_max = float(
        df[
            "margin_man_pct"
        ].max()
    )

    margin_padding = max(
        (
            margin_max
            - margin_min
        )
        * 0.15,
        5,
    )

    margin_axis_min = min(
        0,
        margin_min
        - margin_padding,
    )

    margin_axis_max = max(
        0,
        margin_max
        + margin_padding,
    )

    # =====================================================
    # Layout
    # =====================================================

    fig.update_layout(
        height=CHART_HEIGHT,

        margin={
            "l": 10,
            "r": 90,
            "t": 92,
            "b": 45,
        },

        paper_bgcolor="white",
        plot_bgcolor="white",

        bargap=0.38,

        font={
            "family": FONT_FAMILY,
            "color": TEXT_COLOR,
            "size": 11,
        },

        # =================================================
        # Заголовок + период
        # =================================================

        title={
            "text": (
              
                "<span style='"
                "font-size:11px;"
                f"color:{MUTED_COLOR};"
                "'>"
                f"{period_label}"
                "</span>"
            ),

            "x": 0,
            "xanchor": "left",

            "y": 0.985,
            "yanchor": "top",

            "font": {
                "family": FONT_FAMILY,
                "size": 15,
                "color": TEXT_COLOR,
            },
        },

        # =================================================
        # Легенда
        # =================================================

        legend={
            "orientation": "h",

            "yanchor": "bottom",
            "y": 1.05,

            "xanchor": "right",
            "x": 1,

            "font": {
                "family": FONT_FAMILY,
                "size": 10,
                "color": MUTED_COLOR,
            },

            "bgcolor": (
                "rgba(255,255,255,0)"
            ),
        },

        # =================================================
        # Hover
        # =================================================

        hoverlabel={
            "bgcolor": "white",

            "bordercolor": AXIS_COLOR,

            "font": {
                "family": FONT_FAMILY,
                "color": TEXT_COLOR,
                "size": 12,
            },

            "align": "left",
        },

        hovermode="closest",

        # =================================================
        # Нижняя ось — выручка
        # =================================================

        xaxis={
            "title": {
                "text": "Выручка без НДС",

                "font": {
                    "family": FONT_FAMILY,
                    "size": 10,
                    "color": MUTED_COLOR,
                },
            },

            "side": "bottom",

            "showgrid": True,

            "gridcolor": GRID_COLOR,
            "gridwidth": 1,

            "zeroline": False,
            "showline": False,

            "tickformat": "~s",

            "tickfont": {
                "family": FONT_FAMILY,
                "size": 9,
                "color": LIGHT_TEXT_COLOR,
            },

            "automargin": True,
            "fixedrange": True,
        },

        # =================================================
        # Верхняя ось — маржинальность
        # =================================================

        xaxis2={
            "title": {
                "text": (
                    "Управленческая "
                    "маржинальность, %"
                ),

                "font": {
                    "family": FONT_FAMILY,
                    "size": 10,
                    "color": MARGIN_COLOR,
                },
            },

            "overlaying": "x",

            "side": "top",

            "range": [
                margin_axis_min,
                margin_axis_max,
            ],

            "ticksuffix": "%",

            "showgrid": False,

            "zeroline": True,

            "zerolinecolor": (
                ZERO_LINE_COLOR
            ),

            "zerolinewidth": 1,

            "showline": False,

            "tickfont": {
                "family": FONT_FAMILY,
                "size": 9,
                "color": MARGIN_COLOR,
            },

            "fixedrange": True,
        },

        # =================================================
        # Категории
        # =================================================

        yaxis={
            "showgrid": False,

            "showline": False,

            "ticks": "",

            "tickfont": {
                "family": FONT_FAMILY,
                "size": 10,
                "color": TEXT_COLOR,
            },

            "automargin": True,

            "fixedrange": True,
        },
    )

    return fig


# =========================================================
# DONUT
#
# Структура положительной управленческой маржи.
#
# Маржа:
# Выручка без НДС
# - Управленческая себестоимость
# - Комиссия WB
#
# Без:
# - маркетинга
# - логистики
# - штрафов
#
# Важно:
# gross_profit_man — старое техническое
# название поля.
#
# По бизнес-смыслу здесь это МАРЖА, ₽.
# =========================================================

def build_profit_donut(
    rows: list[dict],
    top_n: int = 8,
    date_from: Any | None = None,
    date_to: Any | None = None,
) -> go.Figure:
    """
    Структура положительной управленческой маржи.

    Для совместимости имя функции оставлено
    build_profit_donut.

    gross_profit_man фактически используется
    как управленческая маржа в рублях.
    """

    if not rows:
        return empty_figure()

    df = pd.DataFrame(
        rows
    ).copy()

    if df.empty:
        return empty_figure()

    if (
        "gross_profit_man"
        not in df.columns
    ):
        return empty_figure()

    # =====================================================
    # Период
    # =====================================================

    period_label = _build_period_label(
        rows=rows,
        date_from=date_from,
        date_to=date_to,
    )

    # =====================================================
    # Подготовка данных
    # =====================================================

    if "name" not in df.columns:
        df["name"] = "Не указано"

    df["name"] = (
        df["name"]
        .fillna("Не указано")
        .astype(str)
    )

    df[
        "gross_profit_man"
    ] = pd.to_numeric(
        df[
            "gross_profit_man"
        ],
        errors="coerce",
    ).fillna(0)

    # =====================================================
    # В donut показываем только
    # ПОЛОЖИТЕЛЬНУЮ маржу.
    #
    # Отрицательную маржу нельзя корректно
    # интерпретировать как долю круга.
    # =====================================================

    positive_df = df[
        df[
            "gross_profit_man"
        ]
        > 0
    ].copy()

    if positive_df.empty:
        return empty_figure(
            "Нет положительной "
            "управленческой маржи"
        )

    positive_df = (
        positive_df
        .sort_values(
            "gross_profit_man",
            ascending=False,
        )
        .reset_index(
            drop=True
        )
    )

    # =====================================================
    # TOP N
    # =====================================================

    top_df = positive_df.head(
        top_n
    ).copy()

    other_df = positive_df.iloc[
        top_n:
    ].copy()

    labels = (
        top_df[
            "name"
        ]
        .astype(str)
        .tolist()
    )

    values = (
        top_df[
            "gross_profit_man"
        ]
        .tolist()
    )

    # =====================================================
    # Прочие
    # =====================================================

    if not other_df.empty:

        other_value = float(
            other_df[
                "gross_profit_man"
            ].sum()
        )

        if other_value > 0:

            labels.append(
                "Прочие"
            )

            values.append(
                other_value
            )

    total = float(
        sum(values)
    )

    # =====================================================
    # Цвета
    # =====================================================

    colors = [
        DONUT_COLORS[
            index
            % len(
                DONUT_COLORS
            )
        ]
        for index
        in range(
            len(labels)
        )
    ]

    # =====================================================
    # График
    # =====================================================

    fig = go.Figure()

    fig.add_trace(
        go.Pie(
            labels=labels,

            values=values,

            hole=0.68,

            sort=False,

            direction="clockwise",

            rotation=0,

            # =============================================
            # Подписи внутри
            # =============================================

            textinfo="percent",

            textposition="inside",

            textfont={
                "family": FONT_FAMILY,
                "size": 10,
                "color": "white",
            },

            insidetextorientation=(
                "horizontal"
            ),

            texttemplate=(
                "%{percent:.0%}"
            ),

            # =============================================
            # Цвета
            # =============================================

            marker={
                "colors": colors,

                "line": {
                    "color": "white",
                    "width": 2,
                },
            },

            # =============================================
            # Hover
            # =============================================

            hovertemplate=(
                "<b>%{label}</b>"
                "<br>"
                f"<span style='color:{MUTED_COLOR}'>"
                f"{period_label}"
                "</span>"
                "<br>"
                "<span style='color:#98A2B3'>"
                "────────────────────────"
                "</span>"
                "<br><br>"

                "Упр. маржа: "
                "<b>%{value:,.0f} ₽</b>"
                "<br>"

                "Доля в положительной марже: "
                "<b>%{percent:.1%}</b>"
                "<br><br>"

                "<span style='color:#98A2B3'>"
                "Маржа = выручка без НДС − "
                "себестоимость − комиссия WB"
                "<br>"
                "Без маркетинга, логистики и штрафов"
                "</span>"

                "<extra></extra>"
            ),
        )
    )

    # =====================================================
    # Центральная подпись
    # =====================================================

    fig.add_annotation(
        text=(
            "<span style='"
            "font-size:10px;"
            f"color:{MUTED_COLOR};"
            "'>"
            "Упр. маржа"
            "</span>"
            "<br>"

            "<span style='"
            "font-size:17px;"
            f"color:{TEXT_COLOR};"
            "'>"
            f"<b>{_format_compact_money(total)}</b>"
            "</span>"
            "<br>"

            "<span style='"
            "font-size:9px;"
            f"color:{LIGHT_TEXT_COLOR};"
            "'>"
            "после с/с и комиссии WB"
            "</span>"
        ),

        x=0.37,
        y=0.5,

        showarrow=False,

        align="center",
    )

    # =====================================================
    # Layout
    # =====================================================

    fig.update_layout(
        height=CHART_HEIGHT,

        margin={
            "l": 5,
            "r": 5,
            "t": 90,
            "b": 20,
        },

        paper_bgcolor="white",
        plot_bgcolor="white",

        font={
            "family": FONT_FAMILY,
            "color": TEXT_COLOR,
            "size": 10,
        },

        # =================================================
        # Заголовок + период
        # =================================================

        title={
            "text": (
     
                "<br>"
                "<span style='"
                "font-size:11px;"
                f"color:{MUTED_COLOR};"
                "'>"
                f"{period_label}"
                "</span>"
            ),

            "x": 0,
            "xanchor": "left",

            "y": 0.985,
            "yanchor": "top",

            "font": {
                "family": FONT_FAMILY,
                "size": 15,
                "color": TEXT_COLOR,
            },
        },

        # =================================================
        # Легенда
        # =================================================

        legend={
            "orientation": "v",

            "yanchor": "middle",
            "y": 0.5,

            "xanchor": "left",
            "x": 0.76,

            "font": {
                "family": FONT_FAMILY,
                "size": 9,
                "color": MUTED_COLOR,
            },

            "itemsizing": "constant",

            "tracegroupgap": 4,

            "bgcolor": (
                "rgba(255,255,255,0)"
            ),
        },

        # =================================================
        # Hover
        # =================================================

        hoverlabel={
            "bgcolor": "white",

            "bordercolor": AXIS_COLOR,

            "font": {
                "family": FONT_FAMILY,
                "color": TEXT_COLOR,
                "size": 12,
            },

            "align": "left",
        },
    )

    # =====================================================
    # Donut сдвигаем влево,
    # чтобы справа осталось место под легенду.
    # =====================================================

    fig.update_traces(
        domain={
            "x": [
                0.02,
                0.70,
            ],

            "y": [
                0.08,
                0.92,
            ],
        },

        selector={
            "type": "pie",
        },
    )

    return fig