# gear/app/stats/charts.py
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from .config import COLORS


BASE_FONT = (
    "Inter, Arial, sans-serif"
)

RU_MONTHS_SHORT = {
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


def _format_change(
    first_value,
    last_value,
):
    if (
        first_value is None
        or last_value is None
        or first_value == 0
    ):
        return "—"

    change = (
        (last_value - first_value)
        / abs(first_value)
        * 100
    )

    return f"{change:+.1f}%"


def _format_money_short(
    value,
):
    if value is None:
        return "—"

    value = float(value)

    if abs(value) >= 1_000_000_000:
        return (
            f"{value / 1_000_000_000:.1f}"
            " млрд ₽"
        )

    if abs(value) >= 1_000_000:
        return (
            f"{value / 1_000_000:.1f}"
            " млн ₽"
        )

    if abs(value) >= 1_000:
        return (
            f"{value / 1_000:.1f}"
            " тыс. ₽"
        )

    return f"{value:,.0f} ₽".replace(
        ",",
        " ",
    )


def _base_layout(
    fig: go.Figure,
):
    fig.update_layout(
        template="plotly_white",
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        font={
            "family": BASE_FONT,
            "color": COLORS["text"],
        },
        margin={
            "l": 55,
            "r": 30,
            "t": 30,
            "b": 55,
        },
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "left",
            "x": 0,
        },
        hoverlabel={
            "font_family": BASE_FONT,
        },
    )

    fig.update_xaxes(
        showgrid=False,
        zeroline=False,
        linecolor=COLORS[
            "border"
        ],
    )

    fig.update_yaxes(
        gridcolor="#EEF0F2",
        zeroline=False,
        linecolor=COLORS[
            "border"
        ],
    )

    return fig


def empty_figure(
    text: str = (
        "Нет данных для отображения"
    ),
):
    fig = go.Figure()

    fig.update_layout(
        template="plotly_white",
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        xaxis={
            "visible": False,
        },
        yaxis={
            "visible": False,
        },
        annotations=[
            {
                "text": text,
                "x": 0.5,
                "y": 0.5,
                "xref": "paper",
                "yref": "paper",
                "showarrow": False,
                "font": {
                    "family": BASE_FONT,
                    "size": 13,
                    "color": COLORS[
                        "muted"
                    ],
                },
            }
        ],
    )

    return fig


def build_trend_chart(
    df: pd.DataFrame,
):
    """
    Динамика выручки и маркетинговых расходов.

    Дополнительно отображает:
    - русские сокращения месяцев;
    - изменение выручки за период;
    - изменение маркетинга за период;
    - долю маркетинга в выручке
      в последнем периоде.
    """

    if df.empty:
        return empty_figure()

    work = df.copy()

    work["period"] = pd.to_datetime(
        work["period"],
        errors="coerce",
    )

    work["revenue"] = pd.to_numeric(
        work["revenue"],
        errors="coerce",
    )

    work["marketing_spend"] = (
        pd.to_numeric(
            work["marketing_spend"],
            errors="coerce",
        )
    )

    work = (
        work
        .dropna(
            subset=[
                "period",
            ]
        )
        .sort_values(
            "period"
        )
        .reset_index(
            drop=True
        )
    )

    if work.empty:
        return empty_figure()

    # -------------------------------------------------
    # Русские подписи дат для hover
    # -------------------------------------------------

    work["period_label"] = work[
        "period"
    ].apply(
        lambda value: (
            f"{value.day:02d} "
            f"{RU_MONTHS_SHORT[value.month]} "
            f"{value.year}"
        )
    )

    # -------------------------------------------------
    # Русские подписи месяцев на оси X
    # -------------------------------------------------

    min_date = work[
        "period"
    ].min()

    max_date = work[
        "period"
    ].max()

    month_ticks = pd.date_range(
        start=pd.Timestamp(
            year=min_date.year,
            month=min_date.month,
            day=1,
        ),
        end=pd.Timestamp(
            year=max_date.year,
            month=max_date.month,
            day=1,
        ),
        freq="MS",
    )

    month_tick_text = [
        (
            f"{RU_MONTHS_SHORT[dt.month]}"
            f"<br>{dt.year}"
        )
        for dt in month_ticks
    ]

    # -------------------------------------------------
    # KPI для аналитической подписи
    # -------------------------------------------------

    first_revenue = work[
        "revenue"
    ].iloc[0]

    last_revenue = work[
        "revenue"
    ].iloc[-1]

    first_marketing = work[
        "marketing_spend"
    ].iloc[0]

    last_marketing = work[
        "marketing_spend"
    ].iloc[-1]

    revenue_change = _format_change(
        first_revenue,
        last_revenue,
    )

    marketing_change = _format_change(
        first_marketing,
        last_marketing,
    )

    if (
        pd.notna(last_revenue)
        and last_revenue != 0
        and pd.notna(last_marketing)
    ):
        marketing_share = (
            last_marketing
            / last_revenue
            * 100
        )

        marketing_share_text = (
            f"{marketing_share:.1f}%"
        )
    else:
        marketing_share_text = "—"

    # -------------------------------------------------
    # График
    # -------------------------------------------------

    fig = go.Figure()

    # Выручка
    fig.add_trace(
        go.Scatter(
            x=work["period"],
            y=work["revenue"],
            name="Выручка",
            mode="lines",
            customdata=work[
                "period_label"
            ],
            line={
                "color": COLORS[
                    "blue"
                ],
                "width": 3,
            },
            fill="tozeroy",
            fillcolor=(
                "rgba(37, 99, 235, 0.06)"
            ),
            hovertemplate=(
                "<b>%{customdata}</b><br>"
                "<span style='color:#2563EB'>"
                "●</span> Выручка: "
                "<b>%{y:,.0f} ₽</b>"
                "<extra></extra>"
            ),
        )
    )

    # Маркетинг
    fig.add_trace(
        go.Scatter(
            x=work["period"],
            y=work[
                "marketing_spend"
            ],
            name="Маркетинг",
            mode="lines",
            customdata=work[
                "period_label"
            ],
            yaxis="y2",
            line={
                "color": COLORS[
                    "orange"
                ],
                "width": 2.5,
            },
            hovertemplate=(
                "<b>%{customdata}</b><br>"
                "<span style='color:#F97316'>"
                "●</span> Маркетинг: "
                "<b>%{y:,.0f} ₽</b>"
                "<extra></extra>"
            ),
        )
    )

    # -------------------------------------------------
    # Аналитическая подпись
    # -------------------------------------------------

    fig.add_annotation(
        x=1,
        y=1,
        xref="paper",
        yref="paper",
        xanchor="right",
        yanchor="bottom",
        yshift=46,
        showarrow=False,
        align="right",
        text=(
            "<span style='color:#6B7280'>"
            "Динамика за период"
            "</span>"
            "<br>"
            f"Выручка "
            f"<b>{revenue_change}</b>"
            "   ·   "
            f"Маркетинг "
            f"<b>{marketing_change}</b>"
            "   ·   "
            "Доля маркетинга "
            f"<b>{marketing_share_text}</b>"
        ),
        font={
            "family": BASE_FONT,
            "size": 11,
            "color": COLORS[
                "text"
            ],
        },
    )

    fig.update_layout(
        hovermode="x unified",

        yaxis={
            "title": {
                "text": "Выручка по нашей цене, ₽",
                "font": {
                    "size": 11,
                    "color": COLORS["blue"],
                },
                "standoff": 12,
            },
            "tickformat": ",.0f",
            "ticksuffix": " ₽",
            "showgrid": True,
        },

        yaxis2={
            "title": {
                "text": "Маркетинговые расходы, ₽",
                "font": {
                    "size": 11,
                    "color": COLORS["orange"],
                },
                "standoff": 12,
            },
            "overlaying": "y",
            "side": "right",
            "tickformat": ",.0f",
            "ticksuffix": " ₽",
            "showgrid": False,
        },

        hoverlabel={
            "bgcolor": "white",
            "font_family": BASE_FONT,
            "font_size": 12,
        },
    )

    fig.update_xaxes(
        tickmode="array",
        tickvals=month_ticks,
        ticktext=month_tick_text,
        tickfont={
            "size": 11,
            "color": COLORS[
                "muted"
            ],
        },
        showgrid=False,
        rangeslider={
            "visible": False,
        },
    )

    return _base_layout(
        fig
    )
    
    
    
def build_marketing_scatter(
    df: pd.DataFrame,
):
    """
    Связь маркетинговых расходов
    и выручки по нашей цене
    + линейный тренд.
    """

    if df.empty:
        return empty_figure()

    work = (
        df[
            [
                "period",
                "marketing_spend",
                "revenue",
            ]
        ]
        .copy()
    )

    work["marketing_spend"] = (
        pd.to_numeric(
            work["marketing_spend"],
            errors="coerce",
        )
    )

    work["revenue"] = (
        pd.to_numeric(
            work["revenue"],
            errors="coerce",
        )
    )

    work["period"] = pd.to_datetime(
        work["period"],
        errors="coerce",
    )

    work = (
        work
        .dropna(
            subset=[
                "period",
                "marketing_spend",
                "revenue",
            ]
        )
        .sort_values(
            "period"
        )
        .reset_index(
            drop=True
        )
    )

    if work.empty:
        return empty_figure()

    # -------------------------------------------------
    # Подпись периода для hover
    # -------------------------------------------------

    work["period_label"] = work[
        "period"
    ].dt.strftime(
        "%d.%m.%Y"
    )

    # -------------------------------------------------
    # График
    # -------------------------------------------------

    fig = go.Figure()

    # Точки наблюдений
    fig.add_trace(
        go.Scatter(
            x=work[
                "marketing_spend"
            ],
            y=work[
                "revenue"
            ],
            mode="markers",
            name="Периоды",
            marker={
                "size": 9,
                "opacity": 0.78,
                "color": COLORS[
                    "green"
                ],
                "line": {
                    "width": 1,
                    "color": (
                        "rgba("
                        "255,255,255,0.9"
                        ")"
                    ),
                },
            },
            customdata=work[
                [
                    "period_label",
                ]
            ].to_numpy(),
            hovertemplate=(
                "<b>%{customdata[0]}</b>"
                "<br><br>"
                "Маркетинговые расходы: "
                "<b>%{x:,.0f} ₽</b>"
                "<br>"
                "Выручка по нашей цене: "
                "<b>%{y:,.0f} ₽</b>"
                "<extra></extra>"
            ),
        )
    )

    # -------------------------------------------------
    # Линейный тренд
    # -------------------------------------------------

    if (
        len(work) >= 3
        and work[
            "marketing_spend"
        ].nunique() > 1
    ):
        x = work[
            "marketing_spend"
        ].to_numpy(
            dtype=float
        )

        y = work[
            "revenue"
        ].to_numpy(
            dtype=float
        )

        coefficients = np.polyfit(
            x,
            y,
            1,
        )

        x_line = np.linspace(
            x.min(),
            x.max(),
            100,
        )

        y_line = (
            coefficients[0]
            * x_line
            + coefficients[1]
        )

        fig.add_trace(
            go.Scatter(
                x=x_line,
                y=y_line,
                mode="lines",
                name="Линейный тренд",
                line={
                    "color": COLORS[
                        "red"
                    ],
                    "width": 2,
                    "dash": "dash",
                },
                hoverinfo="skip",
            )
        )

    # -------------------------------------------------
    # Оформление
    # -------------------------------------------------

    fig.update_layout(
        xaxis={
            "title": {
                "text": (
                    "Маркетинговые расходы, ₽"
                ),
                "font": {
                    "size": 11,
                    "color": COLORS[
                        "muted"
                    ],
                },
                "standoff": 12,
            },
            "tickformat": ",.0f",
            "ticksuffix": " ₽",
        },

        yaxis={
            "title": {
                "text": (
                    "Выручка по нашей цене, ₽"
                ),
                "font": {
                    "size": 11,
                    "color": COLORS[
                        "muted"
                    ],
                },
                "standoff": 12,
            },
            "tickformat": ",.0f",
            "ticksuffix": " ₽",
        },

        hoverlabel={
            "bgcolor": "white",
            "font_family": BASE_FONT,
            "font_size": 12,
        },
    )

    return _base_layout(
        fig
    )
    
    




def build_lag_chart(
    df: pd.DataFrame,
):
    """
    Анализ связи маркетинговых расходов
    с будущей выручкой при разных лагах.

    lag = 0:
        маркетинг и выручка одного периода.

    lag = 1:
        маркетинг текущего периода
        сравнивается с выручкой следующего периода.

    lag = 2:
        маркетинг текущего периода
        сравнивается с выручкой через два периода.

    Pearson:
        показывает силу линейной связи.

    Spearman:
        показывает, сохраняется ли общее направление
        зависимости, даже если связь не является
        строго линейной.
    """

    if df.empty:
        return empty_figure()

    work = df.copy()

    # ================================================================
    # Подготовка данных
    # ================================================================

    work["lag"] = pd.to_numeric(
        work["lag"],
        errors="coerce",
    )

    work["pearson"] = (
        pd.to_numeric(
            work["pearson"],
            errors="coerce",
        )
        .round(2)
    )

    work["spearman"] = (
        pd.to_numeric(
            work["spearman"],
            errors="coerce",
        )
        .round(2)
    )

    work = work.dropna(
        subset=[
            "lag",
            "pearson",
        ]
    )

    if work.empty:
        return empty_figure()

    # ================================================================
    # Лучший лаг
    #
    # Выбираем максимальную по модулю корреляцию Pearson.
    # ================================================================

    best_index = (
        work["pearson"]
        .abs()
        .idxmax()
    )

    best_lag = float(
        work.loc[
            best_index,
            "lag",
        ]
    )

    best_pearson = float(
        work.loc[
            best_index,
            "pearson",
        ]
    )

    # ================================================================
    # Динамический диапазон оси Y
    # ================================================================

    all_values = pd.concat(
        [
            work["pearson"],
            work["spearman"],
        ],
        ignore_index=True,
    ).dropna()

    if all_values.empty:
        y_min = 0.0
        y_max = 0.2

    else:
        min_value = float(
            all_values.min()
        )

        max_value = float(
            all_values.max()
        )

        data_min = min(
            0.0,
            min_value,
        )

        data_max = max(
            0.0,
            max_value,
        )

        data_range = (
            data_max
            - data_min
        )

        padding = max(
            0.05,
            data_range * 0.18,
        )

        if data_min < 0:
            y_min = max(
                -1.0,
                data_min - padding,
            )
        else:
            y_min = 0.0

        y_max = min(
            1.0,
            data_max + padding,
        )

        if (
            y_max
            - y_min
        ) < 0.15:
            y_max = min(
                1.0,
                y_min + 0.15,
            )

    # ================================================================
    # Цвета Pearson
    #
    # Лучший лаг — зелёный.
    # Остальные — синие.
    #
    # Прозрачность задаём через opacity самого trace.
    # ================================================================

    bar_colors = [
        (
            COLORS["green"]
            if lag == best_lag
            else COLORS["blue"]
        )
        for lag in work["lag"]
    ]

    # ================================================================
    # График
    # ================================================================

    fig = go.Figure()

    # ================================================================
    # Pearson — полупрозрачные столбцы
    # ================================================================

    fig.add_trace(
        go.Bar(
            x=work["lag"],
            y=work["pearson"],

            name="Pearson",

            marker={
                "color": bar_colors,

                # Тонкая граница делает
                # полупрозрачные столбцы аккуратнее.
                "line": {
                    "color": bar_colors,
                    "width": 1,
                },
            },

            # Полупрозрачность столбцов
            opacity=0.72,

            # Значения над столбцами
            text=work[
                "pearson"
            ].map(
                lambda value: (
                    f"{value:+.2f}"
                    if pd.notna(value)
                    else ""
                )
            ),

            textposition="outside",

            textfont={
                "size": 11,
                "color": COLORS.get(
                    "text",
                    "#1F2937",
                ),
            },

            cliponaxis=False,

            hovertemplate=(
                "<b>Лаг %{x}</b><br>"
                "Pearson: "
                "<b>%{y:+.2f}</b>"
                "<extra></extra>"
            ),
        )
    )

    # ================================================================
    # Spearman — линия поверх столбцов
    # ================================================================

    fig.add_trace(
        go.Scatter(
            x=work["lag"],
            y=work["spearman"],

            name="Spearman",

            mode="lines+markers",

            line={
                "color": COLORS["orange"],
                "width": 3,
            },

            marker={
                "size": 9,
                "color": COLORS["orange"],

                # Белая окантовка визуально
                # отделяет маркеры от столбцов.
                "line": {
                    "color": "white",
                    "width": 2,
                },
            },

            hovertemplate=(
                "<b>Лаг %{x}</b><br>"
                "Spearman: "
                "<b>%{y:+.2f}</b>"
                "<extra></extra>"
            ),
        )
    )

    # ================================================================
    # Нулевая линия
    # ================================================================

    fig.add_hline(
        y=0,
        line_width=1,
        line_color=COLORS["border"],
    )

    # ================================================================
    # Вертикальная линия лучшего лага
    # ================================================================

    fig.add_vline(
        x=best_lag,
        line_width=1.5,
        line_dash="dot",
        line_color=COLORS["green"],
    )

    # ================================================================
    # Аннотация лучшего лага
    # ================================================================

    fig.add_annotation(
        x=best_lag,
        y=best_pearson,

        text=(
            f"<b>Лучший лаг: "
            f"{int(best_lag)}</b><br>"
            f"Pearson = "
            f"{best_pearson:+.2f}"
        ),

        showarrow=True,

        arrowhead=2,
        arrowsize=1,
        arrowwidth=1,

        arrowcolor=COLORS["green"],

        ax=45,

        ay=(
            -55
            if best_pearson >= 0
            else 55
        ),

        bgcolor="rgba(255,255,255,0.95)",

        bordercolor=COLORS["border"],

        borderwidth=1,

        borderpad=5,

        font={
            "size": 11,
            "color": COLORS.get(
                "text",
                "#1F2937",
            ),
        },
    )

    # ================================================================
    # Общий layout
    # ================================================================

    fig.update_layout(
        xaxis_title=(
            "Лаг, периодов"
        ),

        yaxis_title=(
            "Корреляция маркетинга "
            "с последующей выручкой"
        ),

        yaxis_range=[
            y_min,
            y_max,
        ],

        # Чуть больше воздуха между столбцами
        bargap=0.32,

        hovermode="closest",

        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "left",
            "x": 0,
        },

        margin={
            "l": 70,
            "r": 30,
            "t": 70,
            "b": 65,
        },
    )

    # ================================================================
    # Ось X
    # ================================================================

    fig.update_xaxes(
        dtick=1,

        showgrid=False,

        zeroline=False,

        ticks="outside",
    )

    # ================================================================
    # Ось Y
    # ================================================================

    fig.update_yaxes(
        tickformat=".2f",

        gridcolor=COLORS["border"],

        # Делаем сетку менее визуально тяжёлой
        gridwidth=1,

        zeroline=False,
    )

    return _base_layout(
        fig
    )
    
    

def build_rolling_corr_chart(
    df: pd.DataFrame,
):
    """
    Изменение скользящей корреляции
    между маркетинговыми расходами
    и выручкой во времени.

    Корреляция находится в диапазоне от -1 до +1.

    Ближе к +1:
        рост маркетинга обычно сопровождается
        ростом выручки.

    Около 0:
        выраженной линейной связи нет.

    Ближе к -1:
        маркетинг и выручка движутся
        преимущественно в противоположных направлениях.

    Важно:
        корреляция показывает статистическую связь,
        но не доказывает причинно-следственную зависимость.
    """

    if df.empty:
        return empty_figure()

    work = df.copy()

    # ================================================================
    # Проверка обязательных колонок
    # ================================================================

    required_columns = {
        "period",
        "rolling_correlation",
    }

    if not required_columns.issubset(
        work.columns
    ):
        return empty_figure()

    # ================================================================
    # Подготовка данных
    # ================================================================

    work["period"] = pd.to_datetime(
        work["period"],
        errors="coerce",
    )

    work["rolling_correlation"] = pd.to_numeric(
        work["rolling_correlation"],
        errors="coerce",
    )

    work = (
        work
        .dropna(
            subset=[
                "period",
                "rolling_correlation",
            ]
        )
        .sort_values(
            "period"
        )
        .reset_index(
            drop=True
        )
    )

    if work.empty:
        return empty_figure()

    # ================================================================
    # Ограничиваем корреляцию допустимым диапазоном
    # и округляем В PYTHON до двух знаков.
    #
    # Теперь Plotly получает, например:
    #     0.90
    # вместо:
    #     0.9000362181794538
    # ================================================================

    work["rolling_correlation"] = (
        work["rolling_correlation"]
        .clip(
            lower=-1,
            upper=1,
        )
        .round(2)
    )

    # ================================================================
    # Основные показатели
    # ================================================================

    average_corr = round(
        float(
            work[
                "rolling_correlation"
            ].mean()
        ),
        2,
    )

    last_corr = round(
        float(
            work.iloc[-1][
                "rolling_correlation"
            ]
        ),
        2,
    )

    last_period = work.iloc[-1][
        "period"
    ]

    max_index = (
        work[
            "rolling_correlation"
        ]
        .idxmax()
    )

    min_index = (
        work[
            "rolling_correlation"
        ]
        .idxmin()
    )

    max_corr = round(
        float(
            work.loc[
                max_index,
                "rolling_correlation",
            ]
        ),
        2,
    )

    min_corr = round(
        float(
            work.loc[
                min_index,
                "rolling_correlation",
            ]
        ),
        2,
    )

    max_period = work.loc[
        max_index,
        "period",
    ]

    min_period = work.loc[
        min_index,
        "period",
    ]

    # ================================================================
    # Цвета и размеры точек
    # ================================================================

    marker_colors = []
    marker_sizes = []

    for index in work.index:

        value = float(
            work.loc[
                index,
                "rolling_correlation",
            ]
        )

        if index == max_index:

            marker_colors.append(
                COLORS["green"]
            )

            marker_sizes.append(
                12
            )

        elif index == min_index:

            marker_colors.append(
                COLORS["orange"]
            )

            marker_sizes.append(
                12
            )

        elif value >= 0:

            marker_colors.append(
                COLORS["green"]
            )

            marker_sizes.append(
                6
            )

        else:

            marker_colors.append(
                COLORS["orange"]
            )

            marker_sizes.append(
                6
            )

    # ================================================================
    # Создаём график
    # ================================================================

    fig = go.Figure()

    # ================================================================
    # Фоновые смысловые зоны
    # ================================================================

    # Сильная положительная связь
    fig.add_hrect(
        y0=0.6,
        y1=1.0,

        fillcolor=(
            "rgba(15, 118, 110, 0.06)"
        ),

        line_width=0,

        layer="below",
    )

    # Зона слабой связи
    fig.add_hrect(
        y0=-0.2,
        y1=0.2,

        fillcolor=(
            "rgba(107, 114, 128, 0.05)"
        ),

        line_width=0,

        layer="below",
    )

    # Сильная отрицательная связь
    fig.add_hrect(
        y0=-1.0,
        y1=-0.6,

        fillcolor=(
            "rgba(249, 115, 22, 0.06)"
        ),

        line_width=0,

        layer="below",
    )

    # ================================================================
    # Основная линия
    # ================================================================

    fig.add_trace(
        go.Scatter(
            x=work["period"],

            y=work[
                "rolling_correlation"
            ],

            mode="lines+markers",

            name=(
                "Скользящая корреляция"
            ),

            line={
                "color": COLORS[
                    "green"
                ],
                "width": 2.8,
            },

            marker={
                "size": marker_sizes,

                "color": marker_colors,

                "line": {
                    "color": "white",
                    "width": 1.5,
                },
            },

            fill="tozeroy",

            fillcolor=(
                "rgba(15, 118, 110, 0.07)"
            ),

            # В y уже лежит округлённое
            # Python-значение.
            hovertemplate=(
                "<b>%{x|%d.%m.%Y}</b>"
                "<br><br>"

                "Корреляция: "
                "<b>%{y}</b>"

                "<br><br>"

                "<b>Положительное значение</b>"
                " — маркетинг и выручка "
                "движутся в одном направлении"

                "<br>"

                "<b>Отрицательное значение</b>"
                " — движение преимущественно "
                "в разных направлениях"

                "<extra></extra>"
            ),
        )
    )

    # ================================================================
    # Нулевая линия
    # ================================================================

    fig.add_hline(
        y=0,

        line_width=1.5,

        line_dash="dash",

        line_color=COLORS[
            "gray"
        ],
    )

    # ================================================================
    # Граница сильной положительной связи
    # ================================================================

    fig.add_hline(
        y=0.6,

        line_width=1,

        line_dash="dot",

        line_color=COLORS[
            "green"
        ],
    )

    # ================================================================
    # Граница сильной отрицательной связи
    # ================================================================

    fig.add_hline(
        y=-0.6,

        line_width=1,

        line_dash="dot",

        line_color=COLORS[
            "orange"
        ],
    )

    # ================================================================
    # Средняя корреляция
    # ================================================================

    fig.add_hline(
        y=average_corr,

        line_width=1.5,

        line_dash="dashdot",

        line_color=COLORS[
            "blue"
        ],

        annotation_text=(
            f"Средняя: "
            f"{average_corr:+.2f}"
        ),

        annotation_position=(
            "top left"
        ),

        annotation_font={
            "size": 10,
            "color": COLORS[
                "blue"
            ],
        },

        annotation_bgcolor=(
            "rgba(255,255,255,0.94)"
        ),

        annotation_borderpad=3,
    )

    # ================================================================
    # Максимальная положительная корреляция
    #
    # Аннотацию размещаем НИЖЕ максимальной точки,
    # если она находится слишком близко к верхней границе.
    #
    # Так рамка всегда остаётся внутри графика.
    # ================================================================

    if max_corr >= 0.75:

        max_annotation_ay = 65

    else:

        max_annotation_ay = -65

    fig.add_annotation(
        x=max_period,
        y=max_corr,

        text=(
            "<b>Максимальная связь</b><br>"
            f"{max_period:%d.%m.%Y}<br>"
            f"r = <b>{max_corr:+.2f}</b>"
        ),

        showarrow=True,

        arrowhead=2,

        arrowsize=1,

        arrowwidth=1,

        arrowcolor=COLORS[
            "green"
        ],

        # Немного смещаем влево
        ax=-85,

        # Автоматически внутрь графика
        ay=max_annotation_ay,

        bgcolor=(
            "rgba(255,255,255,0.97)"
        ),

        bordercolor=COLORS[
            "green"
        ],

        borderwidth=1,

        borderpad=5,

        font={
            "size": 10,
            "color": COLORS.get(
                "text",
                "#111827",
            ),
        },

        align="left",
    )

    # ================================================================
    # Минимальная корреляция
    #
    # Если точка близко к -1,
    # подпись размещаем ВЫШЕ точки,
    # чтобы она не накладывалась на ось X.
    # ================================================================

    if min_index != max_index:

        if min_corr <= -0.75:

            min_annotation_ay = -65

        else:

            min_annotation_ay = 65

        fig.add_annotation(
            x=min_period,
            y=min_corr,

            text=(
                "<b>Минимальная связь</b><br>"
                f"{min_period:%d.%m.%Y}<br>"
                f"r = <b>{min_corr:+.2f}</b>"
            ),

            showarrow=True,

            arrowhead=2,

            arrowsize=1,

            arrowwidth=1,

            arrowcolor=COLORS[
                "orange"
            ],

            ax=85,

            ay=min_annotation_ay,

            bgcolor=(
                "rgba(255,255,255,0.97)"
            ),

            bordercolor=COLORS[
                "orange"
            ],

            borderwidth=1,

            borderpad=5,

            font={
                "size": 10,
                "color": COLORS.get(
                    "text",
                    "#111827",
                ),
            },

            align="left",
        )

    # ================================================================
    # Последнее значение
    # ================================================================

    if (
        last_period != max_period
        and last_period != min_period
    ):

        fig.add_annotation(
            x=last_period,
            y=last_corr,

            text=(
                f"<b>{last_corr:+.2f}</b>"
            ),

            showarrow=True,

            arrowhead=0,

            arrowwidth=1,

            arrowcolor=(
                COLORS["green"]
                if last_corr >= 0
                else COLORS["orange"]
            ),

            ax=-35,

            ay=(
                -25
                if last_corr < 0.75
                else 25
            ),

            bgcolor=(
                "rgba(255,255,255,0.96)"
            ),

            bordercolor=(
                COLORS["green"]
                if last_corr >= 0
                else COLORS["orange"]
            ),

            borderwidth=1,

            borderpad=4,

            font={
                "size": 11,

                "color": (
                    COLORS["green"]
                    if last_corr >= 0
                    else COLORS["orange"]
                ),
            },
        )

    # ================================================================
    # Подписи смысловых зон
    # ================================================================

    fig.add_annotation(
        x=1,
        y=0.82,

        xref="paper",
        yref="y",

        xanchor="right",

        text=(
            "Сильная положительная связь"
        ),

        showarrow=False,

        font={
            "size": 9,
            "color": COLORS[
                "green"
            ],
        },

        bgcolor=(
            "rgba(255,255,255,0.78)"
        ),
    )

    fig.add_annotation(
        x=1,
        y=-0.82,

        xref="paper",
        yref="y",

        xanchor="right",

        text=(
            "Сильная отрицательная связь"
        ),

        showarrow=False,

        font={
            "size": 9,
            "color": COLORS[
                "orange"
            ],
        },

        bgcolor=(
            "rgba(255,255,255,0.78)"
        ),
    )

    fig.add_annotation(
        x=1,
        y=0,

        xref="paper",
        yref="y",

        xanchor="right",

        text=(
            "Выраженной связи нет"
        ),

        showarrow=False,

        yshift=12,

        font={
            "size": 9,
            "color": COLORS[
                "muted"
            ],
        },

        bgcolor=(
            "rgba(255,255,255,0.78)"
        ),
    )

    # ================================================================
    # Layout
    #
    # Диапазон немного шире [-1; +1].
    #
    # Сами значения корреляции остаются
    # строго в диапазоне [-1; +1],
    # но дополнительное пространство позволяет
    # нормально разместить аннотации.
    # ================================================================

    fig.update_layout(
        yaxis_title=(
            "Корреляция маркетинга и выручки"
        ),

        yaxis_range=[
            -1.18,
            1.18,
        ],

        hovermode="closest",

        showlegend=False,

        hoverlabel={
            "font": {
                "size": 11,
                "color": "white",
            },

            "bgcolor": COLORS[
                "green"
            ],

            "bordercolor": COLORS[
                "green"
            ],
        },

        margin={
            "l": 75,
            "r": 55,
            "t": 85,
            "b": 75,
        },
    )

    # ================================================================
    # Ось X
    # ================================================================

    fig.update_xaxes(
        showgrid=False,

        zeroline=False,

        tickformat=(
            "%d.%m.%Y"
        ),

        hoverformat=(
            "%d.%m.%Y"
        ),

        automargin=True,
    )

    # ================================================================
    # Ось Y
    #
    # Тики оставляем только в логическом
    # диапазоне корреляции от -1 до +1.
    # ================================================================

    fig.update_yaxes(
        tickmode="array",

        tickvals=[
            -1.0,
            -0.8,
            -0.6,
            -0.4,
            -0.2,
            0.0,
            0.2,
            0.4,
            0.6,
            0.8,
            1.0,
        ],

        ticktext=[
            "-1.0",
            "-0.8",
            "-0.6",
            "-0.4",
            "-0.2",
            "0.0",
            "0.2",
            "0.4",
            "0.6",
            "0.8",
            "1.0",
        ],

        gridcolor=COLORS[
            "border"
        ],

        gridwidth=1,

        zeroline=False,

        automargin=True,
    )

    return _base_layout(
        fig
    )


def build_roas_chart(
    df: pd.DataFrame,
):
    """
    Динамика ROAS.

    ROAS = Выручка / Маркетинговые расходы.

    Показывает, сколько рублей выручки приходится
    на каждый 1 ₽ маркетинговых расходов.

    На графике:
    - динамика ROAS;
    - средний ROAS;
    - максимальный ROAS;
    - минимальный ROAS;
    - последнее значение;
    - выручка и маркетинг в hover.
    """

    if df.empty:
        return empty_figure()

    work = df.copy()

    # ================================================================
    # Проверка обязательных колонок
    # ================================================================

    required_columns = {
        "period",
        "roas",
    }

    if not required_columns.issubset(
        work.columns
    ):
        return empty_figure()

    # ================================================================
    # Подготовка данных
    # ================================================================

    work["period"] = pd.to_datetime(
        work["period"],
        errors="coerce",
    )

    work["roas"] = pd.to_numeric(
        work["roas"],
        errors="coerce",
    )

    if "revenue" in work.columns:
        work["revenue"] = pd.to_numeric(
            work["revenue"],
            errors="coerce",
        )
    else:
        work["revenue"] = float("nan")

    if "marketing_spend" in work.columns:
        work["marketing_spend"] = pd.to_numeric(
            work["marketing_spend"],
            errors="coerce",
        )
    else:
        work["marketing_spend"] = float("nan")

    work = (
        work
        .dropna(
            subset=[
                "period",
                "roas",
            ]
        )
        .sort_values(
            "period"
        )
        .reset_index(
            drop=True
        )
    )

    if work.empty:
        return empty_figure()

    # ================================================================
    # Основные показатели
    # ================================================================

    average_roas = float(
        work["roas"].mean()
    )

    median_roas = float(
        work["roas"].median()
    )

    max_index = (
        work["roas"]
        .idxmax()
    )

    min_index = (
        work["roas"]
        .idxmin()
    )

    max_roas = float(
        work.loc[
            max_index,
            "roas",
        ]
    )

    min_roas = float(
        work.loc[
            min_index,
            "roas",
        ]
    )

    max_period = work.loc[
        max_index,
        "period",
    ]

    min_period = work.loc[
        min_index,
        "period",
    ]

    last_roas = float(
        work.iloc[-1][
            "roas"
        ]
    )

    last_period = work.iloc[-1][
        "period"
    ]

    # ================================================================
    # Цвета и размеры точек
    # ================================================================

    marker_colors = []

    marker_sizes = []

    for index in work.index:

        if index == max_index:
            marker_colors.append(
                COLORS["green"]
            )

            marker_sizes.append(
                13
            )

        elif index == min_index:
            marker_colors.append(
                COLORS["orange"]
            )

            marker_sizes.append(
                11
            )

        else:
            marker_colors.append(
                COLORS["purple"]
            )

            marker_sizes.append(
                7
            )

    # ================================================================
    # Данные для hover
    # ================================================================

    customdata = work[
        [
            "revenue",
            "marketing_spend",
        ]
    ].to_numpy()

    # ================================================================
    # Динамический диапазон оси Y
    #
    # Обычная линейная шкала.
    # Никакой логарифмической шкалы.
    # ================================================================

    data_min = min(
        0.0,
        min_roas,
    )

    data_max = max(
        max_roas,
        average_roas,
    )

    data_range = (
        data_max
        - data_min
    )

    padding = max(
        5.0,
        data_range * 0.12,
    )

    y_min = 0.0

    y_max = (
        data_max
        + padding
    )

    # ================================================================
    # График
    # ================================================================

    fig = go.Figure()

    # ================================================================
    # Полупрозрачная заливка
    # ================================================================

    fig.add_trace(
        go.Scatter(
            x=work["period"],
            y=work["roas"],

            mode="lines",

            line={
                "width": 0,
            },

            fill="tozeroy",

            fillcolor=(
                "rgba(124, 58, 237, 0.08)"
            ),

            hoverinfo="skip",

            showlegend=False,
        )
    )

    # ================================================================
    # Основная линия ROAS
    # ================================================================

    fig.add_trace(
        go.Scatter(
            x=work["period"],
            y=work["roas"],

            mode="lines+markers",

            name="ROAS",

            line={
                "color": COLORS["purple"],
                "width": 3,
            },

            marker={
                "size": marker_sizes,
                "color": marker_colors,

                "line": {
                    "color": "white",
                    "width": 1.5,
                },
            },

            customdata=customdata,

            hovertemplate=(
                "<b>%{x|%d.%m.%Y}</b>"
                "<br><br>"

                "ROAS: "
                "<b>%{y:.2f}</b>"

                "<br>"

                "Выручка: "
                "<b>%{customdata[0]:,.0f} ₽</b>"

                "<br>"

                "Маркетинг: "
                "<b>%{customdata[1]:,.0f} ₽</b>"

                "<br><br>"

                "<b>"
                "На 1 ₽ маркетинга приходится "
                "%{y:.2f} ₽ выручки"
                "</b>"

                "<extra></extra>"
            ),
        )
    )

    # ================================================================
    # Средний ROAS
    # ================================================================

    fig.add_hline(
        y=average_roas,

        line_width=1.5,

        line_dash="dash",

        line_color=COLORS["blue"],

        annotation_text=(
            f"Средний ROAS: "
            f"{average_roas:.2f}"
        ),

        annotation_position=(
            "top left"
        ),

        annotation_font={
            "size": 10,
            "color": COLORS["blue"],
        },

        annotation_bgcolor=(
            "rgba(255,255,255,0.92)"
        ),

        annotation_borderpad=3,
    )

    # ================================================================
    # Аннотация максимального ROAS
    # ================================================================

    fig.add_annotation(
        x=max_period,
        y=max_roas,

        text=(
            "<b>Максимальный ROAS</b><br>"
            f"{max_period:%d.%m.%Y}<br>"
            f"ROAS: <b>{max_roas:.2f}</b>"
        ),

        showarrow=True,

        arrowhead=2,

        arrowsize=1,

        arrowwidth=1,

        arrowcolor=COLORS["green"],

        ax=-80,

        ay=35,

        bgcolor=(
            "rgba(255,255,255,0.96)"
        ),

        bordercolor=COLORS["green"],

        borderwidth=1,

        borderpad=5,

        font={
            "size": 11,
            "color": COLORS.get(
                "text",
                "#111827",
            ),
        },

        align="left",
    )

    # ================================================================
    # Аннотация минимального ROAS
    # ================================================================

    if min_index != max_index:

        fig.add_annotation(
            x=min_period,
            y=min_roas,

            text=(
                f"<b>Мин.: "
                f"{min_roas:.2f}</b>"
            ),

            showarrow=True,

            arrowhead=0,

            arrowwidth=1,

            arrowcolor=COLORS[
                "orange"
            ],

            ax=25,

            ay=-30,

            bgcolor=(
                "rgba(255,255,255,0.96)"
            ),

            bordercolor=COLORS[
                "orange"
            ],

            borderwidth=1,

            borderpad=4,

            font={
                "size": 10,
                "color": COLORS[
                    "orange"
                ],
            },
        )

    # ================================================================
    # Последнее значение
    #
    # Если последняя точка совпадает с максимумом,
    # дополнительную подпись не рисуем.
    # ================================================================

    if (
        last_period
        != max_period
    ):

        fig.add_annotation(
            x=last_period,
            y=last_roas,

            text=(
                f"<b>{last_roas:.2f}</b>"
            ),

            showarrow=True,

            arrowhead=0,

            arrowwidth=1,

            arrowcolor=COLORS[
                "purple"
            ],

            ax=35,

            ay=-25,

            bgcolor=(
                "rgba(255,255,255,0.96)"
            ),

            bordercolor=COLORS[
                "purple"
            ],

            borderwidth=1,

            borderpad=4,

            font={
                "size": 11,
                "color": COLORS[
                    "purple"
                ],
            },
        )

    # ================================================================
    # Layout
    # ================================================================

    fig.update_layout(
        yaxis_title=(
            "ROAS, ₽ выручки на 1 ₽ маркетинга"
        ),

        yaxis_range=[
            y_min,
            y_max,
        ],

        hovermode="closest",

        showlegend=False,

        hoverlabel={
            "font": {
                "size": 12,
                "color": "white",
            },

            "bgcolor": COLORS[
                "purple"
            ],

            "bordercolor": COLORS[
                "purple"
            ],
        },

        margin={
            "l": 75,
            "r": 45,
            "t": 65,
            "b": 65,
        },
    )

    # ================================================================
    # Ось X
    # ================================================================

    fig.update_xaxes(
        showgrid=False,

        zeroline=False,

        tickformat=(
            "%d.%m.%Y"
        ),

        hoverformat=(
            "%d.%m.%Y"
        ),
    )

    # ================================================================
    # Ось Y
    # ================================================================

    fig.update_yaxes(
        type="linear",

        tickformat=".0f",

        gridcolor=COLORS[
            "border"
        ],

        gridwidth=1,

        zeroline=False,
    )

    return _base_layout(
        fig
    )
    


def build_price_scatter(
    df: pd.DataFrame,
):
    """
    Анализ связи средней цены реализации
    и количества проданных единиц.

    График показывает:
    - как меняется количество продаж
      при разных уровнях средней цены;
    - линейную связь между ценой и количеством;
    - медианный уровень цены;
    - медианный объём продаж;
    - направление и силу корреляции Pearson.

    Интерпретация:

    Отрицательная корреляция:
        более высокая цена обычно сопровождается
        снижением количества продаж.

    Положительная корреляция:
        цена и количество продаж растут
        преимущественно одновременно.

    Корреляция около 0:
        выраженной линейной зависимости
        между ценой и количеством не обнаружено.
    """

    if df.empty:
        return empty_figure()

    work = df.copy()

    # ================================================================
    # Проверка обязательных колонок
    # ================================================================

    required_columns = {
        "period",
        "average_price",
        "quantity",
    }

    if not required_columns.issubset(
        work.columns
    ):
        return empty_figure()

    # ================================================================
    # Подготовка данных
    # ================================================================

    work["period"] = pd.to_datetime(
        work["period"],
        errors="coerce",
    )

    work["average_price"] = pd.to_numeric(
        work["average_price"],
        errors="coerce",
    )

    work["quantity"] = pd.to_numeric(
        work["quantity"],
        errors="coerce",
    )

    # Дополнительные поля для hover
    if "revenue" in work.columns:

        work["revenue"] = pd.to_numeric(
            work["revenue"],
            errors="coerce",
        )

    else:

        work["revenue"] = float(
            "nan"
        )

    work = (
        work
        .replace(
            [
                np.inf,
                -np.inf,
            ],
            np.nan,
        )
        .dropna(
            subset=[
                "period",
                "average_price",
                "quantity",
            ]
        )
        .sort_values(
            "period"
        )
        .reset_index(
            drop=True
        )
    )

    if work.empty:
        return empty_figure()

    # ================================================================
    # Основные показатели
    # ================================================================

    median_price = float(
        work[
            "average_price"
        ].median()
    )

    median_quantity = float(
        work[
            "quantity"
        ].median()
    )

    average_price = float(
        work[
            "average_price"
        ].mean()
    )

    average_quantity = float(
        work[
            "quantity"
        ].mean()
    )

    # ================================================================
    # Корреляция Pearson
    # ================================================================

    correlation = None

    if (
        len(work) >= 2
        and work[
            "average_price"
        ].nunique() > 1
        and work[
            "quantity"
        ].nunique() > 1
    ):

        correlation = work[
            "average_price"
        ].corr(
            work[
                "quantity"
            ]
        )

        if pd.notna(
            correlation
        ):

            correlation = round(
                float(
                    correlation
                ),
                2,
            )

        else:

            correlation = None

    # ================================================================
    # Цвет точек
    #
    # Цена выше медианы:
    #     фиолетовая
    #
    # Цена ниже медианы:
    #     синяя
    # ================================================================

    marker_colors = [
        (
            COLORS["purple"]
            if price >= median_price
            else COLORS["blue"]
        )
        for price in work[
            "average_price"
        ]
    ]

    # ================================================================
    # График
    # ================================================================

    fig = go.Figure()

    # ================================================================
    # Фоновые зоны
    #
    # Делаем очень лёгкими,
    # чтобы они только помогали читать график.
    # ================================================================

    # Низкая цена / высокий объём
    fig.add_shape(
        type="rect",

        x0=work[
            "average_price"
        ].min(),

        x1=median_price,

        y0=median_quantity,

        y1=work[
            "quantity"
        ].max(),

        fillcolor=(
            "rgba(15, 118, 110, 0.04)"
        ),

        line_width=0,

        layer="below",
    )

    # Высокая цена / низкий объём
    fig.add_shape(
        type="rect",

        x0=median_price,

        x1=work[
            "average_price"
        ].max(),

        y0=work[
            "quantity"
        ].min(),

        y1=median_quantity,

        fillcolor=(
            "rgba(249, 115, 22, 0.04)"
        ),

        line_width=0,

        layer="below",
    )

    # ================================================================
    # Scatter
    # ================================================================

    fig.add_trace(
        go.Scatter(
            x=work[
                "average_price"
            ],

            y=work[
                "quantity"
            ],

            mode="markers",

            marker={
                "size": 10,

                "opacity": 0.78,

                "color": marker_colors,

                "line": {
                    "color": "white",
                    "width": 1.5,
                },
            },

            customdata=work[
                [
                    "period",
                    "revenue",
                ]
            ].to_numpy(),

            hovertemplate=(
                "<b>%{customdata[0]|%d.%m.%Y}</b>"
                "<br><br>"

                "Средняя цена: "
                "<b>%{x:,.2f} ₽</b>"

                "<br>"

                "Количество: "
                "<b>%{y:,.0f} шт.</b>"

                "<br>"

                "Выручка: "
                "<b>%{customdata[1]:,.0f} ₽</b>"

                "<extra></extra>"
            ),

            name="Периоды",
        )
    )

    # ================================================================
    # Линейный тренд
    # ================================================================

    if (
        len(work) >= 3
        and work[
            "average_price"
        ].nunique() > 1
    ):

        x = work[
            "average_price"
        ].to_numpy(
            dtype=float
        )

        y = work[
            "quantity"
        ].to_numpy(
            dtype=float
        )

        coefficients = np.polyfit(
            x,
            y,
            1,
        )

        slope = float(
            coefficients[0]
        )

        x_line = np.linspace(
            x.min(),
            x.max(),
            100,
        )

        y_line = (
            slope
            * x_line
            + coefficients[1]
        )

        fig.add_trace(
            go.Scatter(
                x=x_line,

                y=y_line,

                mode="lines",

                line={
                    "color": COLORS[
                        "red"
                    ],

                    "width": 2.2,

                    "dash": "dash",
                },

                name=(
                    "Линейный тренд"
                ),

                hoverinfo="skip",
            )
        )

    # ================================================================
    # Медианная цена
    # ================================================================

    fig.add_vline(
        x=median_price,

        line_width=1.2,

        line_dash="dot",

        line_color=COLORS[
            "purple"
        ],

        annotation_text=(
            f"Медианная цена: "
            f"{median_price:,.0f} ₽"
        ),

        annotation_position=(
            "top"
        ),

        annotation_font={
            "size": 10,
            "color": COLORS[
                "purple"
            ],
        },

        annotation_bgcolor=(
            "rgba(255,255,255,0.90)"
        ),
    )

    # ================================================================
    # Медианный объём продаж
    # ================================================================

    fig.add_hline(
        y=median_quantity,

        line_width=1.2,

        line_dash="dot",

        line_color=COLORS[
            "blue"
        ],

        annotation_text=(
            f"Медиана продаж: "
            f"{median_quantity:,.0f}"
        ),

        annotation_position=(
            "top left"
        ),

        annotation_font={
            "size": 10,
            "color": COLORS[
                "blue"
            ],
        },

        annotation_bgcolor=(
            "rgba(255,255,255,0.90)"
        ),
    )

    # ================================================================
    # Корреляция на графике
    # ================================================================

    if correlation is not None:

        if abs(
            correlation
        ) < 0.2:

            correlation_text = (
                "Связь практически отсутствует"
            )

        elif abs(
            correlation
        ) < 0.4:

            correlation_text = (
                "Слабая связь"
            )

        elif abs(
            correlation
        ) < 0.6:

            correlation_text = (
                "Умеренная связь"
            )

        elif abs(
            correlation
        ) < 0.8:

            correlation_text = (
                "Сильная связь"
            )

        else:

            correlation_text = (
                "Очень сильная связь"
            )

        fig.add_annotation(
            x=0.01,
            y=0.99,

            xref="paper",
            yref="paper",

            xanchor="left",
            yanchor="top",

            text=(
                f"<b>Цена ↔ количество</b><br>"
                f"Pearson r = "
                f"<b>{correlation:+.2f}</b><br>"
                f"{correlation_text}"
            ),

            showarrow=False,

            align="left",

            bgcolor=(
                "rgba(255,255,255,0.94)"
            ),

            bordercolor=COLORS[
                "border"
            ],

            borderwidth=1,

            borderpad=6,

            font={
                "size": 10,
                "color": COLORS.get(
                    "text",
                    "#111827",
                ),
            },
        )

    # ================================================================
    # Подписи смысловых зон
    # ================================================================

    fig.add_annotation(
        x=0.01,
        y=0.03,

        xref="paper",
        yref="paper",

        xanchor="left",
        yanchor="bottom",

        text=(
            "Ниже цена / выше продажи"
        ),

        showarrow=False,

        font={
            "size": 9,
            "color": COLORS[
                "green"
            ],
        },

        bgcolor=(
            "rgba(255,255,255,0.75)"
        ),
    )

    fig.add_annotation(
        x=0.99,
        y=0.03,

        xref="paper",
        yref="paper",

        xanchor="right",
        yanchor="bottom",

        text=(
            "Выше цена / ниже продажи"
        ),

        showarrow=False,

        font={
            "size": 9,
            "color": COLORS[
                "orange"
            ],
        },

        bgcolor=(
            "rgba(255,255,255,0.75)"
        ),
    )

    # ================================================================
    # Layout
    # ================================================================

    fig.update_layout(
        xaxis_title=(
            "Средняя цена реализации, ₽"
        ),

        yaxis_title=(
            "Количество проданных единиц"
        ),

        hovermode="closest",

        legend={
            "orientation": "h",

            "yanchor": "bottom",

            "y": 1.02,

            "xanchor": "right",

            "x": 1,
        },

        margin={
            "l": 75,
            "r": 45,
            "t": 80,
            "b": 70,
        },
    )

    # ================================================================
    # Ось X
    # ================================================================

    fig.update_xaxes(
        tickformat=",",

        showgrid=False,

        zeroline=False,

        automargin=True,
    )

    # ================================================================
    # Ось Y
    # ================================================================

    fig.update_yaxes(
        tickformat=",",

        gridcolor=COLORS[
            "border"
        ],

        zeroline=False,

        automargin=True,
    )

    return _base_layout(
        fig
    )
    
    
def build_price_elasticity_chart(
    df: pd.DataFrame,
):
    """
    Анализ изменения цены и спроса.

    X:
        изменение средней цены, %

    Y:
        изменение количества продаж, %

    Квадранты:

    1. Цена снизилась / продажи выросли
       -> классическая положительная реакция спроса.

    2. Цена выросла / продажи выросли
       -> рост спроса несмотря на повышение цены.

    3. Цена снизилась / продажи снизились
       -> спрос падает несмотря на снижение цены.

    4. Цена выросла / продажи снизились
       -> классическая ценовая чувствительность.

    Proxy elasticity:
        quantity_change_pct / price_change_pct

    Это приближённый показатель, а не полноценная
    эконометрическая оценка эластичности.
    """

    if df.empty:
        return empty_figure()

    work = df.copy()

    # ================================================================
    # Проверка обязательных колонок
    # ================================================================

    required_columns = {
        "period",
        "price_change_pct",
        "quantity_change_pct",
        "elasticity",
    }

    if not required_columns.issubset(
        work.columns
    ):
        return empty_figure()

    # ================================================================
    # Подготовка данных
    # ================================================================

    work["period"] = pd.to_datetime(
        work["period"],
        errors="coerce",
    )

    work["price_change_pct"] = pd.to_numeric(
        work["price_change_pct"],
        errors="coerce",
    )

    work["quantity_change_pct"] = pd.to_numeric(
        work["quantity_change_pct"],
        errors="coerce",
    )

    work["elasticity"] = pd.to_numeric(
        work["elasticity"],
        errors="coerce",
    )

    work = (
        work
        .replace(
            [
                np.inf,
                -np.inf,
            ],
            np.nan,
        )
        .dropna(
            subset=[
                "period",
                "price_change_pct",
                "quantity_change_pct",
            ]
        )
        .sort_values(
            "period"
        )
        .reset_index(
            drop=True
        )
    )

    if work.empty:
        return empty_figure()

    # ================================================================
    # Округляем В PYTHON
    # ================================================================

    work["price_change_pct"] = (
        work["price_change_pct"]
        .round(2)
    )

    work["quantity_change_pct"] = (
        work["quantity_change_pct"]
        .round(2)
    )

    work["elasticity"] = (
        work["elasticity"]
        .round(2)
    )

    # ================================================================
    # Классификация квадрантов
    # ================================================================

    def classify_quadrant(
        price_change,
        quantity_change,
    ):
        if (
            price_change < 0
            and quantity_change > 0
        ):
            return (
                "Цена ↓ / продажи ↑"
            )

        if (
            price_change > 0
            and quantity_change > 0
        ):
            return (
                "Цена ↑ / продажи ↑"
            )

        if (
            price_change < 0
            and quantity_change < 0
        ):
            return (
                "Цена ↓ / продажи ↓"
            )

        if (
            price_change > 0
            and quantity_change < 0
        ):
            return (
                "Цена ↑ / продажи ↓"
            )

        return "Около нулевого изменения"

    work["quadrant"] = [
        classify_quadrant(
            price_change,
            quantity_change,
        )
        for price_change, quantity_change
        in zip(
            work["price_change_pct"],
            work["quantity_change_pct"],
        )
    ]

    # ================================================================
    # Цвета квадрантов
    # ================================================================

    quadrant_colors = {
        "Цена ↓ / продажи ↑": (
            COLORS["green"]
        ),

        "Цена ↑ / продажи ↑": (
            COLORS["blue"]
        ),

        "Цена ↓ / продажи ↓": (
            COLORS["gray"]
        ),

        "Цена ↑ / продажи ↓": (
            COLORS["orange"]
        ),

        "Около нулевого изменения": (
            COLORS["purple"]
        ),
    }

    # ================================================================
    # Цвета точек
    # ================================================================

    marker_colors = [
        quadrant_colors.get(
            value,
            COLORS["purple"],
        )
        for value in work[
            "quadrant"
        ]
    ]

    # ================================================================
    # Размер точки
    #
    # Чем сильнее изменение количества,
    # тем крупнее точка.
    # ================================================================

    abs_quantity_change = (
        work[
            "quantity_change_pct"
        ]
        .abs()
    )

    if (
        abs_quantity_change.max()
        > 0
    ):

        marker_sizes = (
            8
            + (
                abs_quantity_change
                / abs_quantity_change.max()
                * 8
            )
        )

    else:

        marker_sizes = pd.Series(
            10,
            index=work.index,
        )

    # ================================================================
    # Диапазоны осей
    #
    # Делаем симметричными относительно 0,
    # чтобы квадранты читались правильно.
    # ================================================================

    max_abs_x = max(
        abs(
            float(
                work[
                    "price_change_pct"
                ].min()
            )
        ),
        abs(
            float(
                work[
                    "price_change_pct"
                ].max()
            )
        ),
        1.0,
    )

    max_abs_y = max(
        abs(
            float(
                work[
                    "quantity_change_pct"
                ].min()
            )
        ),
        abs(
            float(
                work[
                    "quantity_change_pct"
                ].max()
            )
        ),
        1.0,
    )

    x_padding = (
        max_abs_x
        * 0.15
    )

    y_padding = (
        max_abs_y
        * 0.15
    )

    x_limit = (
        max_abs_x
        + x_padding
    )

    y_limit = (
        max_abs_y
        + y_padding
    )

    # ================================================================
    # График
    # ================================================================

    fig = go.Figure()

    # ================================================================
    # Фоновые квадранты
    # ================================================================

    # Цена ↓ / продажи ↑
    fig.add_shape(
        type="rect",

        x0=-x_limit,
        x1=0,

        y0=0,
        y1=y_limit,

        fillcolor=(
            "rgba(15, 118, 110, 0.05)"
        ),

        line_width=0,

        layer="below",
    )

    # Цена ↑ / продажи ↑
    fig.add_shape(
        type="rect",

        x0=0,
        x1=x_limit,

        y0=0,
        y1=y_limit,

        fillcolor=(
            "rgba(37, 99, 235, 0.04)"
        ),

        line_width=0,

        layer="below",
    )

    # Цена ↓ / продажи ↓
    fig.add_shape(
        type="rect",

        x0=-x_limit,
        x1=0,

        y0=-y_limit,
        y1=0,

        fillcolor=(
            "rgba(107, 114, 128, 0.04)"
        ),

        line_width=0,

        layer="below",
    )

    # Цена ↑ / продажи ↓
    fig.add_shape(
        type="rect",

        x0=0,
        x1=x_limit,

        y0=-y_limit,
        y1=0,

        fillcolor=(
            "rgba(249, 115, 22, 0.05)"
        ),

        line_width=0,

        layer="below",
    )

    # ================================================================
    # Scatter
    # ================================================================

    fig.add_trace(
        go.Scatter(
            x=work[
                "price_change_pct"
            ],

            y=work[
                "quantity_change_pct"
            ],

            mode="markers",

            marker={
                "size": marker_sizes,

                "opacity": 0.80,

                "color": marker_colors,

                "line": {
                    "color": "white",
                    "width": 1.5,
                },
            },

            customdata=work[
                [
                    "period",
                    "elasticity",
                    "quadrant",
                ]
            ].to_numpy(),

            hovertemplate=(
                "<b>%{customdata[0]|%d.%m.%Y}</b>"
                "<br><br>"

                "Изменение цены: "
                "<b>%{x:+.2f}%</b>"

                "<br>"

                "Изменение количества: "
                "<b>%{y:+.2f}%</b>"

                "<br>"

                "Proxy elasticity: "
                "<b>%{customdata[1]}</b>"

                "<br><br>"

                "<b>%{customdata[2]}</b>"

                "<extra></extra>"
            ),

            showlegend=False,
        )
    )

    # ================================================================
    # Нулевая горизонтальная линия
    # ================================================================

    fig.add_hline(
        y=0,

        line_width=1.3,

        line_color=COLORS[
            "gray"
        ],
    )

    # ================================================================
    # Нулевая вертикальная линия
    # ================================================================

    fig.add_vline(
        x=0,

        line_width=1.3,

        line_color=COLORS[
            "gray"
        ],
    )

    # ================================================================
    # Подписи квадрантов
    # ================================================================

    fig.add_annotation(
        x=0.02,
        y=0.97,

        xref="paper",
        yref="paper",

        xanchor="left",
        yanchor="top",

        text=(
            "<b>Цена ↓ / продажи ↑</b><br>"
            "Спрос реагирует положительно "
            "на снижение цены"
        ),

        showarrow=False,

        align="left",

        font={
            "size": 9,
            "color": COLORS[
                "green"
            ],
        },

        bgcolor=(
            "rgba(255,255,255,0.78)"
        ),
    )

    fig.add_annotation(
        x=0.98,
        y=0.97,

        xref="paper",
        yref="paper",

        xanchor="right",
        yanchor="top",

        text=(
            "<b>Цена ↑ / продажи ↑</b><br>"
            "Рост спроса сильнее "
            "ценового эффекта"
        ),

        showarrow=False,

        align="right",

        font={
            "size": 9,
            "color": COLORS[
                "blue"
            ],
        },

        bgcolor=(
            "rgba(255,255,255,0.78)"
        ),
    )

    fig.add_annotation(
        x=0.02,
        y=0.03,

        xref="paper",
        yref="paper",

        xanchor="left",
        yanchor="bottom",

        text=(
            "<b>Цена ↓ / продажи ↓</b><br>"
            "Снижение цены не поддержало спрос"
        ),

        showarrow=False,

        align="left",

        font={
            "size": 9,
            "color": COLORS[
                "gray"
            ],
        },

        bgcolor=(
            "rgba(255,255,255,0.78)"
        ),
    )

    fig.add_annotation(
        x=0.98,
        y=0.03,

        xref="paper",
        yref="paper",

        xanchor="right",
        yanchor="bottom",

        text=(
            "<b>Цена ↑ / продажи ↓</b><br>"
            "Классическая ценовая чувствительность"
        ),

        showarrow=False,

        align="right",

        font={
            "size": 9,
            "color": COLORS[
                "orange"
            ],
        },

        bgcolor=(
            "rgba(255,255,255,0.78)"
        ),
    )

    # ================================================================
    # Layout
    # ================================================================

    fig.update_layout(
        xaxis_title=(
            "Изменение средней цены, %"
        ),

        yaxis_title=(
            "Изменение количества продаж, %"
        ),

        xaxis_range=[
            -x_limit,
            x_limit,
        ],

        yaxis_range=[
            -y_limit,
            y_limit,
        ],

        hovermode="closest",

        showlegend=False,

        margin={
            "l": 80,
            "r": 50,
            "t": 65,
            "b": 75,
        },
    )

    # ================================================================
    # Ось X
    # ================================================================

    fig.update_xaxes(
        ticksuffix="%",

        zeroline=False,

        gridcolor=COLORS[
            "border"
        ],

        automargin=True,
    )

    # ================================================================
    # Ось Y
    # ================================================================

    fig.update_yaxes(
        ticksuffix="%",

        zeroline=False,

        gridcolor=COLORS[
            "border"
        ],

        automargin=True,
    )

    return _base_layout(
        fig
    )
    
    

def build_weekday_chart(
    df: pd.DataFrame,
):
    """
    Сезонность продаж по дням недели.

    Показывает отклонение средней выручки
    каждого дня недели от общего среднего уровня.

    Положительное значение:
        в этот день средняя выручка выше общего среднего.

    Отрицательное значение:
        в этот день средняя выручка ниже общего среднего.
    """

    if df.empty:
        return empty_figure()

    work = df.copy()

    # ================================================================
    # Проверка обязательных колонок
    # ================================================================

    required_columns = {
        "weekday",
        "revenue_deviation_pct",
        "average_revenue",
        "median_revenue",
        "average_quantity",
        "roas",
    }

    if not required_columns.issubset(
        work.columns
    ):
        return empty_figure()

    # ================================================================
    # Подготовка данных
    # ================================================================

    numeric_columns = [
        "revenue_deviation_pct",
        "average_revenue",
        "median_revenue",
        "average_quantity",
        "roas",
    ]

    for column in numeric_columns:

        work[column] = pd.to_numeric(
            work[column],
            errors="coerce",
        )

    work = work.dropna(
        subset=[
            "weekday",
            "revenue_deviation_pct",
        ]
    ).copy()

    if work.empty:
        return empty_figure()

    # ================================================================
    # Округляем значения в Python
    # ================================================================

    work["revenue_deviation_pct"] = (
        work["revenue_deviation_pct"]
        .round(1)
    )

    work["average_revenue"] = (
        work["average_revenue"]
        .round(0)
    )

    work["median_revenue"] = (
        work["median_revenue"]
        .round(0)
    )

    work["average_quantity"] = (
        work["average_quantity"]
        .round(0)
    )

    work["roas"] = (
        work["roas"]
        .round(2)
    )

    # ================================================================
    # Лучший и худший день
    # ================================================================

    best_index = (
        work[
            "revenue_deviation_pct"
        ]
        .idxmax()
    )

    worst_index = (
        work[
            "revenue_deviation_pct"
        ]
        .idxmin()
    )

    best_day = work.loc[
        best_index,
        "weekday",
    ]

    worst_day = work.loc[
        worst_index,
        "weekday",
    ]

    best_deviation = float(
        work.loc[
            best_index,
            "revenue_deviation_pct",
        ]
    )

    worst_deviation = float(
        work.loc[
            worst_index,
            "revenue_deviation_pct",
        ]
    )

    # ================================================================
    # Цвета столбиков
    #
    # Лучший день:
    #     насыщенный зелёный.
    #
    # Выше среднего:
    #     полупрозрачный зелёный.
    #
    # Ниже среднего:
    #     оранжевый.
    # ================================================================

    bar_colors = []

    for index, value in zip(
        work.index,
        work[
            "revenue_deviation_pct"
        ],
    ):

        if index == best_index:

            bar_colors.append(
                COLORS["green"]
            )

        elif value >= 0:

            bar_colors.append(
                "rgba(15, 118, 110, 0.65)"
            )

        else:

            bar_colors.append(
                "rgba(249, 115, 22, 0.68)"
            )

    # ================================================================
    # Динамический диапазон Y
    # ================================================================

    min_value = float(
        work[
            "revenue_deviation_pct"
        ].min()
    )

    max_value = float(
        work[
            "revenue_deviation_pct"
        ].max()
    )

    data_range = (
        max_value
        - min_value
    )

    padding = max(
        3.0,
        data_range * 0.22,
    )

    y_min = min(
        0.0,
        min_value - padding,
    )

    y_max = max(
        0.0,
        max_value + padding,
    )

    # ================================================================
    # График
    # ================================================================

    fig = go.Figure()

    # ================================================================
    # Столбики
    # ================================================================

    fig.add_trace(
        go.Bar(
            x=work[
                "weekday"
            ],

            y=work[
                "revenue_deviation_pct"
            ],

            text=work[
                "revenue_deviation_pct"
            ].map(
                lambda value: (
                    f"{value:+.1f}%"
                )
            ),

            textposition="outside",

            textfont={
                "size": 11,
            },

            cliponaxis=False,

            customdata=work[
                [
                    "average_revenue",
                    "median_revenue",
                    "average_quantity",
                    "roas",
                ]
            ].to_numpy(),

            hovertemplate=(
                "<b>%{x}</b>"
                "<br><br>"

                "Отклонение от среднего: "
                "<b>%{y:+.1f}%</b>"

                "<br>"

                "Средняя выручка: "
                "<b>%{customdata[0]:,.0f} ₽</b>"

                "<br>"

                "Медианная выручка: "
                "<b>%{customdata[1]:,.0f} ₽</b>"

                "<br>"

                "Среднее количество: "
                "<b>%{customdata[2]:,.0f} шт.</b>"

                "<br>"

                "ROAS: "
                "<b>%{customdata[3]:.2f}</b>"

                "<extra></extra>"
            ),

            marker={
                "color": bar_colors,

                "line": {
                    "color": bar_colors,
                    "width": 1,
                },
            },

            opacity=0.88,

            name=(
                "Отклонение от среднего"
            ),
        )
    )

    # ================================================================
    # Нулевая линия
    # ================================================================

    fig.add_hline(
        y=0,

        line_width=1.2,

        line_color=COLORS[
            "border"
        ],
    )

    # ================================================================
    # Лёгкие фоновые зоны
    # ================================================================

    fig.add_hrect(
        y0=0,
        y1=y_max,

        fillcolor=(
            "rgba(15, 118, 110, 0.025)"
        ),

        line_width=0,

        layer="below",
    )

    fig.add_hrect(
        y0=y_min,
        y1=0,

        fillcolor=(
            "rgba(249, 115, 22, 0.025)"
        ),

        line_width=0,

        layer="below",
    )

    # ================================================================
    # Аннотация лучшего дня
    # ================================================================

    fig.add_annotation(
        x=best_day,
        y=best_deviation,

        text=(
            "<b>Лучший день</b><br>"
            f"{best_day}<br>"
            f"{best_deviation:+.1f}%"
        ),

        showarrow=True,

        arrowhead=2,

        arrowsize=1,

        arrowwidth=1,

        arrowcolor=COLORS[
            "green"
        ],

        ax=0,

        ay=(
            65
            if best_deviation > 0
            else -65
        ),

        bgcolor=(
            "rgba(255,255,255,0.96)"
        ),

        bordercolor=COLORS[
            "green"
        ],

        borderwidth=1,

        borderpad=5,

        font={
            "size": 10,
            "color": COLORS.get(
                "text",
                "#111827",
            ),
        },

        align="center",
    )

    # ================================================================
    # Аннотация худшего дня
    # ================================================================

    if worst_index != best_index:

        fig.add_annotation(
            x=worst_day,
            y=worst_deviation,

            text=(
                "<b>Минимум</b><br>"
                f"{worst_day}<br>"
                f"{worst_deviation:+.1f}%"
            ),

            showarrow=True,

            arrowhead=2,

            arrowsize=1,

            arrowwidth=1,

            arrowcolor=COLORS[
                "orange"
            ],

            ax=0,

            ay=(
                -65
                if worst_deviation < 0
                else 65
            ),

            bgcolor=(
                "rgba(255,255,255,0.96)"
            ),

            bordercolor=COLORS[
                "orange"
            ],

            borderwidth=1,

            borderpad=5,

            font={
                "size": 10,
                "color": COLORS.get(
                    "text",
                    "#111827",
                ),
            },

            align="center",
        )

    # ================================================================
    # Подписи смысловых зон
    # ================================================================

    fig.add_annotation(
        x=1,
        y=1,

        xref="paper",
        yref="paper",

        xanchor="right",
        yanchor="top",

        text=(
            "Выше среднего"
        ),

        showarrow=False,

        font={
            "size": 9,
            "color": COLORS[
                "green"
            ],
        },

        bgcolor=(
            "rgba(255,255,255,0.80)"
        ),
    )

    fig.add_annotation(
        x=1,
        y=0,

        xref="paper",
        yref="paper",

        xanchor="right",
        yanchor="bottom",

        text=(
            "Ниже среднего"
        ),

        showarrow=False,

        font={
            "size": 9,
            "color": COLORS[
                "orange"
            ],
        },

        bgcolor=(
            "rgba(255,255,255,0.80)"
        ),
    )

    # ================================================================
    # Layout
    # ================================================================

    fig.update_layout(
        yaxis_title=(
            "Отклонение средней выручки, %"
        ),

        yaxis_range=[
            y_min,
            y_max,
        ],

        bargap=0.28,

        hovermode="closest",

        showlegend=False,

        margin={
            "l": 75,
            "r": 45,
            "t": 75,
            "b": 65,
        },
    )

    # ================================================================
    # Ось X
    # ================================================================

    fig.update_xaxes(
        showgrid=False,

        zeroline=False,

        automargin=True,
    )

    # ================================================================
    # Ось Y
    # ================================================================

    fig.update_yaxes(
        ticksuffix="%",

        gridcolor=COLORS[
            "border"
        ],

        zeroline=False,

        automargin=True,
    )

    return _base_layout(
        fig
    )
    
    

# def build_month_chart(
#     df: pd.DataFrame,
# ):
#     """
#     Сезонность продаж по месяцам.

#     Показывает отклонение средней дневной выручки
#     каждого календарного месяца
#     от общего среднего уровня.

#     Положительное значение:
#         месяц в среднем сильнее общего уровня.

#     Отрицательное значение:
#         месяц в среднем слабее общего уровня.
#     """

#     if df.empty:
#         return empty_figure()

#     work = df.copy()

#     # ================================================================
#     # Проверка обязательных колонок
#     # ================================================================

#     required_columns = {
#         "month",
#         "revenue_deviation_pct",
#         "average_revenue",
#         "median_revenue",
#         "average_quantity",
#         "roas",
#     }

#     if not required_columns.issubset(
#         work.columns
#     ):
#         return empty_figure()

#     # ================================================================
#     # Подготовка данных
#     # ================================================================

#     numeric_columns = [
#         "revenue_deviation_pct",
#         "average_revenue",
#         "median_revenue",
#         "average_quantity",
#         "roas",
#     ]

#     for column in numeric_columns:
#         work[column] = pd.to_numeric(
#             work[column],
#             errors="coerce",
#         )

#     work = work.dropna(
#         subset=[
#             "month",
#             "revenue_deviation_pct",
#         ]
#     ).copy()

#     if work.empty:
#         return empty_figure()

#     # ================================================================
#     # Округление в Python
#     # ================================================================

#     work["revenue_deviation_pct"] = (
#         work["revenue_deviation_pct"]
#         .round(1)
#     )

#     work["average_revenue"] = (
#         work["average_revenue"]
#         .round(0)
#     )

#     work["median_revenue"] = (
#         work["median_revenue"]
#         .round(0)
#     )

#     work["average_quantity"] = (
#         work["average_quantity"]
#         .round(0)
#     )

#     work["roas"] = (
#         work["roas"]
#         .round(2)
#     )

#     # ================================================================
#     # Лучший и худший месяц
#     # ================================================================

#     best_index = (
#         work[
#             "revenue_deviation_pct"
#         ]
#         .idxmax()
#     )

#     worst_index = (
#         work[
#             "revenue_deviation_pct"
#         ]
#         .idxmin()
#     )

#     best_month = work.loc[
#         best_index,
#         "month",
#     ]

#     worst_month = work.loc[
#         worst_index,
#         "month",
#     ]

#     best_deviation = float(
#         work.loc[
#             best_index,
#             "revenue_deviation_pct",
#         ]
#     )

#     worst_deviation = float(
#         work.loc[
#             worst_index,
#             "revenue_deviation_pct",
#         ]
#     )

#     # ================================================================
#     # Цвета столбцов
#     # ================================================================

#     bar_colors = []

#     for index, value in zip(
#         work.index,
#         work[
#             "revenue_deviation_pct"
#         ],
#     ):

#         if index == best_index:

#             bar_colors.append(
#                 COLORS["green"]
#             )

#         elif index == worst_index:

#             bar_colors.append(
#                 COLORS["orange"]
#             )

#         elif value >= 0:

#             bar_colors.append(
#                 "rgba(37, 99, 235, 0.68)"
#             )

#         else:

#             bar_colors.append(
#                 "rgba(249, 115, 22, 0.58)"
#             )

#     # ================================================================
#     # Динамический диапазон оси Y
#     # ================================================================

#     min_value = float(
#         work[
#             "revenue_deviation_pct"
#         ].min()
#     )

#     max_value = float(
#         work[
#             "revenue_deviation_pct"
#         ].max()
#     )

#     data_range = (
#         max_value
#         - min_value
#     )

#     padding = max(
#         4.0,
#         data_range * 0.22,
#     )

#     y_min = min(
#         0.0,
#         min_value - padding,
#     )

#     y_max = max(
#         0.0,
#         max_value + padding,
#     )

#     # ================================================================
#     # График
#     # ================================================================

#     fig = go.Figure()

#     # ================================================================
#     # Фоновые зоны
#     # ================================================================

#     fig.add_hrect(
#         y0=0,
#         y1=y_max,

#         fillcolor=(
#             "rgba(37, 99, 235, 0.025)"
#         ),

#         line_width=0,

#         layer="below",
#     )

#     fig.add_hrect(
#         y0=y_min,
#         y1=0,

#         fillcolor=(
#             "rgba(249, 115, 22, 0.025)"
#         ),

#         line_width=0,

#         layer="below",
#     )

#     # ================================================================
#     # Столбцы
#     # ================================================================

#     fig.add_trace(
#         go.Bar(
#             x=work[
#                 "month"
#             ],

#             y=work[
#                 "revenue_deviation_pct"
#             ],

#             text=work[
#                 "revenue_deviation_pct"
#             ].map(
#                 lambda value: (
#                     f"{value:+.1f}%"
#                 )
#             ),

#             textposition="outside",

#             textfont={
#                 "size": 11,
#             },

#             cliponaxis=False,

#             customdata=work[
#                 [
#                     "average_revenue",
#                     "median_revenue",
#                     "average_quantity",
#                     "roas",
#                 ]
#             ].to_numpy(),

#             hovertemplate=(
#                 "<b>%{x}</b>"
#                 "<br><br>"

#                 "Отклонение от среднего: "
#                 "<b>%{y:+.1f}%</b>"

#                 "<br>"

#                 "Средняя дневная выручка: "
#                 "<b>%{customdata[0]:,.0f} ₽</b>"

#                 "<br>"

#                 "Медианная дневная выручка: "
#                 "<b>%{customdata[1]:,.0f} ₽</b>"

#                 "<br>"

#                 "Среднее количество: "
#                 "<b>%{customdata[2]:,.0f} шт.</b>"

#                 "<br>"

#                 "ROAS: "
#                 "<b>%{customdata[3]:.2f}</b>"

#                 "<extra></extra>"
#             ),

#             marker={
#                 "color": bar_colors,

#                 "line": {
#                     "color": bar_colors,
#                     "width": 1,
#                 },
#             },

#             opacity=0.88,

#             name=(
#                 "Отклонение от среднего"
#             ),
#         )
#     )

#     # ================================================================
#     # Нулевая линия
#     # ================================================================

#     fig.add_hline(
#         y=0,

#         line_width=1.2,

#         line_color=COLORS[
#             "border"
#         ],
#     )

#     # ================================================================
#     # Лучший месяц
#     # ================================================================

#     fig.add_annotation(
#         x=best_month,
#         y=best_deviation,

#         text=(
#             "<b>Лучший месяц</b><br>"
#             f"{best_month}<br>"
#             f"{best_deviation:+.1f}%"
#         ),

#         showarrow=True,

#         arrowhead=2,

#         arrowsize=1,

#         arrowwidth=1,

#         arrowcolor=COLORS[
#             "green"
#         ],

#         ax=0,

#         ay=(
#             65
#             if best_deviation > 0
#             else -65
#         ),

#         bgcolor=(
#             "rgba(255,255,255,0.96)"
#         ),

#         bordercolor=COLORS[
#             "green"
#         ],

#         borderwidth=1,

#         borderpad=5,

#         font={
#             "size": 10,
#             "color": COLORS.get(
#                 "text",
#                 "#111827",
#             ),
#         },

#         align="center",
#     )

#     # ================================================================
#     # Худший месяц
#     # ================================================================

#     if worst_index != best_index:

#         fig.add_annotation(
#             x=worst_month,
#             y=worst_deviation,

#             text=(
#                 "<b>Минимум</b><br>"
#                 f"{worst_month}<br>"
#                 f"{worst_deviation:+.1f}%"
#             ),

#             showarrow=True,

#             arrowhead=2,

#             arrowsize=1,

#             arrowwidth=1,

#             arrowcolor=COLORS[
#                 "orange"
#             ],

#             ax=0,

#             ay=(
#                 -65
#                 if worst_deviation < 0
#                 else 65
#             ),

#             bgcolor=(
#                 "rgba(255,255,255,0.96)"
#             ),

#             bordercolor=COLORS[
#                 "orange"
#             ],

#             borderwidth=1,

#             borderpad=5,

#             font={
#                 "size": 10,
#                 "color": COLORS.get(
#                     "text",
#                     "#111827",
#                 ),
#             },

#             align="center",
#         )

#     # ================================================================
#     # Подписи зон
#     # ================================================================

#     fig.add_annotation(
#         x=1,
#         y=1,

#         xref="paper",
#         yref="paper",

#         xanchor="right",
#         yanchor="top",

#         text=(
#             "Месяцы выше среднего"
#         ),

#         showarrow=False,

#         font={
#             "size": 9,
#             "color": COLORS[
#                 "blue"
#             ],
#         },

#         bgcolor=(
#             "rgba(255,255,255,0.80)"
#         ),
#     )

#     fig.add_annotation(
#         x=1,
#         y=0,

#         xref="paper",
#         yref="paper",

#         xanchor="right",
#         yanchor="bottom",

#         text=(
#             "Месяцы ниже среднего"
#         ),

#         showarrow=False,

#         font={
#             "size": 9,
#             "color": COLORS[
#                 "orange"
#             ],
#         },

#         bgcolor=(
#             "rgba(255,255,255,0.80)"
#         ),
#     )

#     # ================================================================
#     # Layout
#     # ================================================================

#     fig.update_layout(
#         yaxis_title=(
#             "Отклонение средней дневной выручки, %"
#         ),

#         yaxis_range=[
#             y_min,
#             y_max,
#         ],

#         bargap=0.24,

#         hovermode="closest",

#         showlegend=False,

#         margin={
#             "l": 80,
#             "r": 45,
#             "t": 75,
#             "b": 70,
#         },
#     )

#     # ================================================================
#     # Ось X
#     # ================================================================

#     fig.update_xaxes(
#         showgrid=False,

#         zeroline=False,

#         automargin=True,
#     )

#     # ================================================================
#     # Ось Y
#     # ================================================================

#     fig.update_yaxes(
#         ticksuffix="%",

#         gridcolor=COLORS[
#             "border"
#         ],

#         zeroline=False,

#         automargin=True,
#     )

#     return _base_layout(
#         fig
#     )
    
    
    
    
def build_month_chart(
    df: pd.DataFrame,
):
    """
    Сезонность продаж по месяцам.

    Показывает отклонение средней дневной выручки
    каждого календарного месяца
    от общего среднего уровня.

    Положительное значение:
        месяц в среднем сильнее общего уровня.

    Отрицательное значение:
        месяц в среднем слабее общего уровня.
    """

    if df.empty:
        return empty_figure()

    work = df.copy()

    # ================================================================
    # Проверка обязательных колонок
    # ================================================================

    required_columns = {
        "month",
        "revenue_deviation_pct",
        "average_revenue",
        "median_revenue",
        "average_quantity",
        "roas",
    }

    if not required_columns.issubset(
        work.columns
    ):
        return empty_figure()

    # ================================================================
    # Подготовка данных
    # ================================================================

    numeric_columns = [
        "revenue_deviation_pct",
        "average_revenue",
        "median_revenue",
        "average_quantity",
        "roas",
    ]

    for column in numeric_columns:
        work[column] = pd.to_numeric(
            work[column],
            errors="coerce",
        )

    work = work.dropna(
        subset=[
            "month",
            "revenue_deviation_pct",
        ]
    ).copy()

    if work.empty:
        return empty_figure()

    # ================================================================
    # Округление в Python
    # ================================================================

    work["revenue_deviation_pct"] = (
        work["revenue_deviation_pct"]
        .round(1)
    )

    work["average_revenue"] = (
        work["average_revenue"]
        .round(0)
    )

    work["median_revenue"] = (
        work["median_revenue"]
        .round(0)
    )

    work["average_quantity"] = (
        work["average_quantity"]
        .round(0)
    )

    work["roas"] = (
        work["roas"]
        .round(2)
    )

    # ================================================================
    # Лучший и худший месяц
    # ================================================================

    best_index = (
        work[
            "revenue_deviation_pct"
        ]
        .idxmax()
    )

    worst_index = (
        work[
            "revenue_deviation_pct"
        ]
        .idxmin()
    )

    best_month = work.loc[
        best_index,
        "month",
    ]

    worst_month = work.loc[
        worst_index,
        "month",
    ]

    best_deviation = float(
        work.loc[
            best_index,
            "revenue_deviation_pct",
        ]
    )

    worst_deviation = float(
        work.loc[
            worst_index,
            "revenue_deviation_pct",
        ]
    )

    # ================================================================
    # Цвета столбцов
    #
    # Основная идея:
    # все обычные месяцы имеют единый спокойный цвет.
    # Выделяем только два действительно важных значения:
    # лучший и худший месяц.
    # ================================================================

    default_bar_color = (
        "rgba(37, 99, 235, 0.58)"
    )

    best_bar_color = (
        "rgba(15, 118, 110, 0.72)"
    )

    worst_bar_color = (
        "rgba(180, 83, 9, 0.72)"
    )

    bar_colors = []

    for index in work.index:

        if index == best_index:
            bar_colors.append(
                best_bar_color
            )

        elif index == worst_index:
            bar_colors.append(
                worst_bar_color
            )

        else:
            bar_colors.append(
                default_bar_color
            )

    # ================================================================
    # Динамический диапазон оси Y
    # ================================================================

    min_value = float(
        work[
            "revenue_deviation_pct"
        ].min()
    )

    max_value = float(
        work[
            "revenue_deviation_pct"
        ].max()
    )

    data_range = (
        max_value
        - min_value
    )

    padding = max(
        4.0,
        data_range * 0.22,
    )

    y_min = min(
        0.0,
        min_value - padding,
    )

    y_max = max(
        0.0,
        max_value + padding,
    )

    # ================================================================
    # График
    # ================================================================

    fig = go.Figure()

    # ================================================================
    # Очень лёгкие фоновые зоны
    # ================================================================

    fig.add_hrect(
        y0=0,
        y1=y_max,

        fillcolor=(
            "rgba(37, 99, 235, 0.018)"
        ),

        line_width=0,

        layer="below",
    )

    fig.add_hrect(
        y0=y_min,
        y1=0,

        fillcolor=(
            "rgba(180, 83, 9, 0.018)"
        ),

        line_width=0,

        layer="below",
    )

    # ================================================================
    # Столбцы
    # ================================================================

    fig.add_trace(
        go.Bar(
            x=work[
                "month"
            ],

            y=work[
                "revenue_deviation_pct"
            ],

            text=work[
                "revenue_deviation_pct"
            ].map(
                lambda value: (
                    f"{value:+.1f}%"
                )
            ),

            textposition="outside",

            textfont={
                "size": 11,
            },

            cliponaxis=False,

            customdata=work[
                [
                    "average_revenue",
                    "median_revenue",
                    "average_quantity",
                    "roas",
                ]
            ].to_numpy(),

            hovertemplate=(
                "<b>%{x}</b>"
                "<br><br>"

                "Отклонение от среднего: "
                "<b>%{y:+.1f}%</b>"

                "<br>"

                "Средняя дневная выручка: "
                "<b>%{customdata[0]:,.0f} ₽</b>"

                "<br>"

                "Медианная дневная выручка: "
                "<b>%{customdata[1]:,.0f} ₽</b>"

                "<br>"

                "Среднее количество: "
                "<b>%{customdata[2]:,.0f} шт.</b>"

                "<br>"

                "ROAS: "
                "<b>%{customdata[3]:.2f}</b>"

                "<extra></extra>"
            ),

            marker={
                "color": bar_colors,

                "line": {
                    "color": bar_colors,
                    "width": 1,
                },
            },

            name=(
                "Отклонение от среднего"
            ),
        )
    )

    # ================================================================
    # Нулевая линия
    # ================================================================

    fig.add_hline(
        y=0,

        line_width=1.2,

        line_color=COLORS[
            "border"
        ],
    )

    # ================================================================
    # Лучший месяц
    # ================================================================

    fig.add_annotation(
        x=best_month,
        y=best_deviation,

        text=(
            "<b>Лучший месяц</b><br>"
            f"{best_month}<br>"
            f"{best_deviation:+.1f}%"
        ),

        showarrow=True,

        arrowhead=2,

        arrowsize=1,

        arrowwidth=1,

        arrowcolor=COLORS[
            "green"
        ],

        ax=0,

        ay=(
            65
            if best_deviation > 0
            else -65
        ),

        bgcolor=(
            "rgba(255,255,255,0.96)"
        ),

        bordercolor=COLORS[
            "green"
        ],

        borderwidth=1,

        borderpad=5,

        font={
            "size": 10,
            "color": COLORS.get(
                "text",
                "#111827",
            ),
        },

        align="center",
    )

    # ================================================================
    # Худший месяц
    # ================================================================

    if worst_index != best_index:

        fig.add_annotation(
            x=worst_month,
            y=worst_deviation,

            text=(
                "<b>Минимум</b><br>"
                f"{worst_month}<br>"
                f"{worst_deviation:+.1f}%"
            ),

            showarrow=True,

            arrowhead=2,

            arrowsize=1,

            arrowwidth=1,

            arrowcolor=COLORS[
                "orange"
            ],

            ax=0,

            ay=(
                -65
                if worst_deviation < 0
                else 65
            ),

            bgcolor=(
                "rgba(255,255,255,0.96)"
            ),

            bordercolor=COLORS[
                "orange"
            ],

            borderwidth=1,

            borderpad=5,

            font={
                "size": 10,
                "color": COLORS.get(
                    "text",
                    "#111827",
                ),
            },

            align="center",
        )

    # ================================================================
    # Подписи зон
    # ================================================================

    fig.add_annotation(
        x=1,
        y=1,

        xref="paper",
        yref="paper",

        xanchor="right",
        yanchor="top",

        text=(
            "Месяцы выше среднего"
        ),

        showarrow=False,

        font={
            "size": 9,
            "color": COLORS[
                "blue"
            ],
        },

        bgcolor=(
            "rgba(255,255,255,0.80)"
        ),
    )

    fig.add_annotation(
        x=1,
        y=0,

        xref="paper",
        yref="paper",

        xanchor="right",
        yanchor="bottom",

        text=(
            "Месяцы ниже среднего"
        ),

        showarrow=False,

        font={
            "size": 9,
            "color": COLORS[
                "orange"
            ],
        },

        bgcolor=(
            "rgba(255,255,255,0.80)"
        ),
    )

    # ================================================================
    # Layout
    # ================================================================

    fig.update_layout(
        yaxis_title=(
            "Отклонение средней дневной выручки, %"
        ),

        yaxis_range=[
            y_min,
            y_max,
        ],

        bargap=0.24,

        hovermode="closest",

        showlegend=False,

        margin={
            "l": 80,
            "r": 45,
            "t": 75,
            "b": 70,
        },
    )

    # ================================================================
    # Ось X
    # ================================================================

    fig.update_xaxes(
        showgrid=False,

        zeroline=False,

        automargin=True,
    )

    # ================================================================
    # Ось Y
    # ================================================================

    fig.update_yaxes(
        ticksuffix="%",

        gridcolor=COLORS[
            "border"
        ],

        zeroline=False,

        automargin=True,
    )

    return _base_layout(
        fig
    )
    
    
    
    
def build_correlation_matrix(
    matrix: pd.DataFrame,
):
    if matrix.empty:
        return empty_figure()

    # ================================================================
    # Русские названия показателей
    # ================================================================

    labels = {
        "revenue": "Выручка",
        "quantity": "Количество",
        "average_price": "Средняя цена",
        "average_retail_price": "Средняя цена WB",
        "marketing_spend": "Маркетинг",
        "other_wb_costs": "Остальные расходы WB",
        "net_comission": "Комиссия WB",
        "cogs_man": "Себестоимость упр.",
        "margin_man": "Маржа упр.",
        "wb_result": "Финрезультат WB",
        "roas": "ROAS",
    }

    # ================================================================
    # Подписи
    # ================================================================

    x_labels = [
        labels.get(
            column,
            column,
        )
        for column in matrix.columns
    ]

    y_labels = [
        labels.get(
            index,
            index,
        )
        for index in matrix.index
    ]

    values = matrix.values

    # ================================================================
    # Heatmap
    # ================================================================

    fig = go.Figure(
        data=go.Heatmap(
            z=values,
            x=x_labels,
            y=y_labels,

            zmin=-1,
            zmax=1,
            zmid=0,

            colorscale=[
                [0.00, "#A33A3A"],
                [0.50, "#FFFFFF"],
                [1.00, "#3C7A67"],
            ],

            text=np.round(
                values,
                2,
            ),

            texttemplate="%{text:.2f}",

            hovertemplate=(
                "<b>%{y}</b><br>"
                "↕<br>"
                "<b>%{x}</b><br><br>"
                "Корреляция: "
                "<b>%{z:.3f}</b>"
                "<extra></extra>"
            ),

            colorbar={
                "title": {
                    "text": "Корреляция",
                },
                "tickvals": [
                    -1,
                    -0.5,
                    0,
                    0.5,
                    1,
                ],
                "ticktext": [
                    "-1,0",
                    "-0,5",
                    "0",
                    "0,5",
                    "1,0",
                ],
                "thickness": 12,
                "len": 0.8,
            },

            # Небольшое расстояние между ячейками
            xgap=2,
            ygap=2,
        )
    )

    # ================================================================
    # Оси
    # ================================================================

    fig.update_xaxes(
        side="bottom",

        # Поворачиваем подписи,
        # иначе при 11 показателях они накладываются
        tickangle=-35,

        tickfont={
            "size": 11,
        },

        showgrid=False,
        zeroline=False,

        automargin=True,
    )

    fig.update_yaxes(
        autorange="reversed",

        tickfont={
            "size": 12,
        },

        showgrid=False,
        zeroline=False,

        automargin=True,
    )

    # ================================================================
    # Базовый layout
    # ================================================================

    fig = _base_layout(
        fig
    )

    # ================================================================
    # Финальная настройка
    # ================================================================

    fig.update_layout(


        margin={
            "l": 30,
            "r": 30,
            "t": 20,
            "b": 140,
        },
    )

    return fig


# def build_anomaly_chart(
#     df: pd.DataFrame,
# ):
#     """
#     Выручка по периодам
#     с выделением аномальных периодов.
#     """

#     if df.empty:
#         return empty_figure(
#             "Аномальные периоды не обнаружены"
#         )

#     fig = go.Figure()

#     fig.add_trace(
#         go.Scatter(
#             x=df["period"],
#             y=df["revenue"],
#             mode="markers",
#             name="Аномалии",
#             marker={
#                 "size": 12,
#                 "color": COLORS[
#                     "red"
#                 ],
#                 "symbol": "diamond",
#             },
#             customdata=df[
#                 [
#                     "anomaly_type",
#                     "marketing_change_pct",
#                     "revenue_change_pct",
#                     "price_change_pct",
#                     "quantity_change_pct",
#                 ]
#             ].to_numpy(),
#             hovertemplate=(
#                 "<b>%{x|%d.%m.%Y}</b><br>"
#                 "%{customdata[0]}<br><br>"
#                 "Выручка: "
#                 "%{y:,.0f} ₽<br>"
#                 "Δ маркетинга: "
#                 "%{customdata[1]:+.1f}%<br>"
#                 "Δ выручки: "
#                 "%{customdata[2]:+.1f}%<br>"
#                 "Δ цены: "
#                 "%{customdata[3]:+.1f}%<br>"
#                 "Δ количества: "
#                 "%{customdata[4]:+.1f}%"
#                 "<extra></extra>"
#             ),
#         )
#     )

#     fig.update_layout(
#         yaxis_title=(
#             "Выручка, ₽"
#         ),
#     )

#     return _base_layout(
#         fig
#     )



def build_anomaly_chart(
    df: pd.DataFrame,
):
    """
    Анализ аномальных периодов продаж.

    График показывает аномальные периоды
    и помогает понять возможную причину
    необычного изменения выручки.

    Размер точки:
        сила изменения выручки.

    Цвет точки:
        положительная / отрицательная
        динамика выручки.

    Hover:
        изменение маркетинга,
        выручки,
        средней цены
        и количества продаж.
    """

    if df.empty:
        return empty_figure(
            "Аномальные периоды не обнаружены"
        )

    work = df.copy()

    # ================================================================
    # Проверка обязательных колонок
    # ================================================================

    required_columns = {
        "period",
        "revenue",
        "anomaly_type",
        "marketing_change_pct",
        "revenue_change_pct",
        "price_change_pct",
        "quantity_change_pct",
    }

    if not required_columns.issubset(
        work.columns
    ):
        return empty_figure(
            "Недостаточно данных для анализа аномалий"
        )

    # ================================================================
    # Подготовка данных
    # ================================================================

    work["period"] = pd.to_datetime(
        work["period"],
        errors="coerce",
    )

    numeric_columns = [
        "revenue",
        "marketing_change_pct",
        "revenue_change_pct",
        "price_change_pct",
        "quantity_change_pct",
    ]

    for column in numeric_columns:

        work[column] = pd.to_numeric(
            work[column],
            errors="coerce",
        )

    work = (
        work
        .replace(
            [
                np.inf,
                -np.inf,
            ],
            np.nan,
        )
        .dropna(
            subset=[
                "period",
                "revenue",
            ]
        )
        .sort_values(
            "period"
        )
        .reset_index(
            drop=True
        )
    )

    if work.empty:
        return empty_figure(
            "Аномальные периоды не обнаружены"
        )

    # ================================================================
    # Округление в Python
    # ================================================================

    for column in [
        "marketing_change_pct",
        "revenue_change_pct",
        "price_change_pct",
        "quantity_change_pct",
    ]:

        work[column] = (
            work[column]
            .round(1)
        )

    work["revenue"] = (
        work["revenue"]
        .round(0)
    )

    # ================================================================
    # Направление аномалии
    # ================================================================

    def classify_direction(
        revenue_change,
    ):

        if pd.isna(
            revenue_change
        ):
            return "Не определено"

        if revenue_change > 0:
            return "Положительная аномалия"

        if revenue_change < 0:
            return "Негативная аномалия"

        return "Нейтральная аномалия"

    work["anomaly_direction"] = (
        work[
            "revenue_change_pct"
        ]
        .apply(
            classify_direction
        )
    )

    # ================================================================
    # Цвета точек
    # ================================================================

    marker_colors = []

    for direction in work[
        "anomaly_direction"
    ]:

        if direction == (
            "Положительная аномалия"
        ):

            marker_colors.append(
                COLORS["green"]
            )

        elif direction == (
            "Негативная аномалия"
        ):

            marker_colors.append(
                COLORS["red"]
            )

        else:

            marker_colors.append(
                COLORS["orange"]
            )

    # ================================================================
    # Размер точек
    #
    # Чем сильнее изменение выручки,
    # тем крупнее маркер.
    # ================================================================

    anomaly_strength = (
        work[
            "revenue_change_pct"
        ]
        .abs()
        .fillna(0)
    )

    max_strength = float(
        anomaly_strength.max()
    )

    if max_strength > 0:

        marker_sizes = (
            11
            + (
                anomaly_strength
                / max_strength
                * 10
            )
        )

    else:

        marker_sizes = pd.Series(
            13,
            index=work.index,
        )

    # ================================================================
    # Самая сильная положительная
    # и негативная аномалия
    # ================================================================

    positive_work = work[
        work[
            "revenue_change_pct"
        ] > 0
    ]

    negative_work = work[
        work[
            "revenue_change_pct"
        ] < 0
    ]

    best_index = None
    worst_index = None

    if not positive_work.empty:

        best_index = (
            positive_work[
                "revenue_change_pct"
            ]
            .idxmax()
        )

    if not negative_work.empty:

        worst_index = (
            negative_work[
                "revenue_change_pct"
            ]
            .idxmin()
        )

    # ================================================================
    # Диапазон Y
    # ================================================================

    min_revenue = float(
        work[
            "revenue"
        ].min()
    )

    max_revenue = float(
        work[
            "revenue"
        ].max()
    )

    revenue_range = (
        max_revenue
        - min_revenue
    )

    padding = max(
        revenue_range * 0.20,
        max_revenue * 0.08,
        1.0,
    )

    y_min = max(
        0,
        min_revenue - padding,
    )

    y_max = (
        max_revenue
        + padding
    )

    # ================================================================
    # График
    # ================================================================

    fig = go.Figure()

    # ================================================================
    # Линия между аномальными периодами
    #
    # Очень лёгкая — только для визуального
    # понимания последовательности во времени.
    # ================================================================

    if len(
        work
    ) > 1:

        fig.add_trace(
            go.Scatter(
                x=work[
                    "period"
                ],

                y=work[
                    "revenue"
                ],

                mode="lines",

                line={
                    "color": (
                        "rgba(107, 114, 128, 0.28)"
                    ),
                    "width": 1.5,
                    "dash": "dot",
                },

                hoverinfo="skip",

                showlegend=False,
            )
        )

    # ================================================================
    # Аномальные точки
    # ================================================================

    fig.add_trace(
        go.Scatter(
            x=work[
                "period"
            ],

            y=work[
                "revenue"
            ],

            mode="markers",

            name="Аномальные периоды",

            marker={
                "size": marker_sizes,

                "color": marker_colors,

                "opacity": 0.82,

                "symbol": "diamond",

                "line": {
                    "color": "white",
                    "width": 1.5,
                },
            },

            customdata=work[
                [
                    "anomaly_type",
                    "anomaly_direction",
                    "marketing_change_pct",
                    "revenue_change_pct",
                    "price_change_pct",
                    "quantity_change_pct",
                ]
            ].to_numpy(),

            hovertemplate=(
                "<b>%{x|%d.%m.%Y}</b>"
                "<br><br>"

                "<b>%{customdata[0]}</b>"

                "<br>"

                "%{customdata[1]}"

                "<br><br>"

                "Выручка: "
                "<b>%{y:,.0f} ₽</b>"

                "<br>"

                "Δ выручки: "
                "<b>%{customdata[3]:+.1f}%</b>"

                "<br>"

                "Δ маркетинга: "
                "<b>%{customdata[2]:+.1f}%</b>"

                "<br>"

                "Δ средней цены: "
                "<b>%{customdata[4]:+.1f}%</b>"

                "<br>"

                "Δ количества: "
                "<b>%{customdata[5]:+.1f}%</b>"

                "<extra></extra>"
            ),
        )
    )

    # ================================================================
    # Аннотация максимальной положительной аномалии
    # ================================================================

    if best_index is not None:

        row = work.loc[
            best_index
        ]

        fig.add_annotation(
            x=row[
                "period"
            ],

            y=row[
                "revenue"
            ],

            text=(
                "<b>Максимальный рост</b><br>"
                f"Выручка "
                f"{row['revenue_change_pct']:+.1f}%"
            ),

            showarrow=True,

            arrowhead=2,

            arrowsize=1,

            arrowwidth=1,

            arrowcolor=COLORS[
                "green"
            ],

            ax=0,

            ay=65,

            bgcolor=(
                "rgba(255,255,255,0.96)"
            ),

            bordercolor=COLORS[
                "green"
            ],

            borderwidth=1,

            borderpad=5,

            font={
                "size": 10,
                "color": COLORS.get(
                    "text",
                    "#111827",
                ),
            },
        )

    # ================================================================
    # Аннотация максимального падения
    # ================================================================

    if worst_index is not None:

        row = work.loc[
            worst_index
        ]

        fig.add_annotation(
            x=row[
                "period"
            ],

            y=row[
                "revenue"
            ],

            text=(
                "<b>Максимальное падение</b><br>"
                f"Выручка "
                f"{row['revenue_change_pct']:+.1f}%"
            ),

            showarrow=True,

            arrowhead=2,

            arrowsize=1,

            arrowwidth=1,

            arrowcolor=COLORS[
                "red"
            ],

            ax=0,

            ay=-65,

            bgcolor=(
                "rgba(255,255,255,0.96)"
            ),

            bordercolor=COLORS[
                "red"
            ],

            borderwidth=1,

            borderpad=5,

            font={
                "size": 10,
                "color": COLORS.get(
                    "text",
                    "#111827",
                ),
            },
        )

    # ================================================================
    # Layout
    # ================================================================

    fig.update_layout(
        yaxis_title=(
            "Выручка, ₽"
        ),

        yaxis_range=[
            y_min,
            y_max,
        ],

        hovermode="closest",

        showlegend=False,

        margin={
            "l": 85,
            "r": 45,
            "t": 80,
            "b": 70,
        },
    )

    # ================================================================
    # Ось X
    # ================================================================

    fig.update_xaxes(
        showgrid=False,

        zeroline=False,

        automargin=True,
    )

    # ================================================================
    # Ось Y
    # ================================================================

    fig.update_yaxes(
        tickformat=",",

        gridcolor=COLORS[
            "border"
        ],

        zeroline=False,

        automargin=True,
    )

    return _base_layout(
        fig
    )