# gear/app/daily_sales/pricing_strategy/charts.py

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

import dash_mantine_components as dmc
from dash import dcc, html


CHART_FONT = "Inter, Arial, sans-serif"


# ============================================================
# HELPERS
# ============================================================

def _num(series):
    return (
        pd.to_numeric(
            series,
            errors="coerce",
        )
        .fillna(0)
    )


def _label(
    frame: pd.DataFrame,
) -> pd.Series:
    return (
        frame["brand"]
        .fillna(
            "Без бренда"
        )
        .astype(str)
        .str.strip()
        + " · "
        + frame["category"]
        .fillna(
            "Без категории"
        )
        .astype(str)
        .str.strip()
    )


# ============================================================
# BASE PLOTLY STYLE
# ============================================================

def _base_layout(
    fig: go.Figure,
    *,
    height: int,
    left: int = 40,
    right: int = 30,
    bottom: int = 42,
    top: int = 22,
):
    fig.update_layout(
        height=height,
  

        margin=dict(
            l=left,
            r=right,
            t=top,
            b=bottom,
        ),

        paper_bgcolor="white",
        plot_bgcolor="white",

        font=dict(
            family=CHART_FONT,
            size=11,
            color="#334155",
        ),

        hoverlabel=dict(
            bgcolor="white",
            font_size=11,
            font_family=CHART_FONT,
        ),

        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
            font=dict(
                size=11,
            ),
            bgcolor=(
                "rgba(255,255,255,0)"
            ),
        ),

        separators=",. ",
    )

    fig.update_xaxes(
        showgrid=True,
        gridcolor="#EEF2F7",
        zeroline=False,

        tickfont=dict(
            size=11,
            color="#64748B",
        ),

        title_font=dict(
            size=11,
            color="#64748B",
        ),

        automargin=True,
    )

    fig.update_yaxes(
        showgrid=False,
        zeroline=False,

        tickfont=dict(
            size=11,
            color="#334155",
        ),

        title_font=dict(
            size=11,
            color="#64748B",
        ),

        automargin=True,
    )

    return fig


# ============================================================
# EMPTY
# ============================================================

def _empty(
    text: str,
    *,
    height: int,
):
    fig = go.Figure()

    fig.add_annotation(
        x=0.5,
        y=0.5,

        xref="paper",
        yref="paper",

        text=text,

        showarrow=False,

        font=dict(
            family=CHART_FONT,
            size=14,
            color="#94A3B8",
        ),
    )

    fig.update_xaxes(
        visible=False,
    )

    fig.update_yaxes(
        visible=False,
    )

    return _base_layout(
        fig,
        height=height,
    )


# ============================================================
# 1. ГДЕ СОСРЕДОТОЧЕН ЗАПАС
# ============================================================

def stock_structure_figure(
    portfolio: pd.DataFrame,
) -> go.Figure:

    height = 330

    if (
        portfolio is None
        or portfolio.empty
    ):
        return _empty(
            "Нет данных по товарному запасу",
            height=height,
        )

    work = portfolio.copy()

    for column in (
        "wb_stock",
        "fbs_stock",
        "in_transit",
        "stock_units",
    ):

        if column not in work.columns:
            work[
                column
            ] = 0

        work[
            column
        ] = _num(
            work[
                column
            ]
        )

    work[
        "label"
    ] = _label(
        work
    )

    work = (
        work
        .sort_values(
            "stock_units",
            ascending=False,
        )
        .head(10)
        .sort_values(
            "stock_units",
            ascending=True,
        )
    )

    if work.empty:
        return _empty(
            "Нет данных по товарному запасу",
            height=height,
        )

    fig = go.Figure()

    fig.add_bar(
        y=work[
            "label"
        ],

        x=work[
            "wb_stock"
        ],

        name="WB",

        orientation="h",

        marker_color=(
            "#2563EB"
        ),

        hovertemplate=(
            "<b>%{y}</b><br>"
            "WB: %{x:,.0f} шт."
            "<extra></extra>"
        ),
    )

    fig.add_bar(
        y=work[
            "label"
        ],

        x=work[
            "fbs_stock"
        ],

        name="FBS",

        orientation="h",

        marker_color=(
            "#14B8A6"
        ),

        hovertemplate=(
            "<b>%{y}</b><br>"
            "FBS: %{x:,.0f} шт."
            "<extra></extra>"
        ),
    )

    fig.add_bar(
        y=work[
            "label"
        ],

        x=work[
            "in_transit"
        ],

        name="В пути",

        orientation="h",

        marker_color=(
            "#F59E0B"
        ),

        hovertemplate=(
            "<b>%{y}</b><br>"
            "В пути: %{x:,.0f} шт."
            "<extra></extra>"
        ),
    )

    fig.update_layout(
        barmode="stack",
        bargap=0.28,
    )

    fig.update_xaxes(
        title=(
            "Остаток, шт."
        ),
    )

    return _base_layout(
        fig,

        height=height,

        left=185,

        right=25,

        bottom=38,

        top=30,
    )


# ============================================================
# 2. ПОТЕНЦИАЛ МАРЖИ
# ============================================================

def margin_upside_figure(
    portfolio: pd.DataFrame,
) -> go.Figure:

    height = 330

    if (
        portfolio is None
        or portfolio.empty
        or (
            "margin_upside_day"
            not in portfolio.columns
        )
    ):
        return _empty(
            (
                "Нет данных по "
                "потенциалу маржи"
            ),
            height=height,
        )

    work = (
        portfolio.copy()
    )

    work[
        "margin_upside_day"
    ] = _num(
        work[
            "margin_upside_day"
        ]
    )

    work[
        "label"
    ] = _label(
        work
    )

    work = (
        work[
            work[
                "margin_upside_day"
            ] > 0
        ]
        .sort_values(
            "margin_upside_day",
            ascending=False,
        )
        .head(10)
        .sort_values(
            "margin_upside_day",
            ascending=True,
        )
    )

    if work.empty:
        return _empty(
            (
                "Положительный "
                "модельный потенциал "
                "не найден"
            ),
            height=height,
        )

    fig = go.Figure()

    fig.add_bar(
        y=work[
            "label"
        ],

        x=work[
            "margin_upside_day"
        ],

        orientation="h",

        marker_color=(
            "#10B981"
        ),

        text=[
            (
                f"{value:,.0f} ₽"
                .replace(
                    ",",
                    " ",
                )
            )
            for value
            in work[
                "margin_upside_day"
            ]
        ],

        textposition="outside",

        cliponaxis=False,

        hovertemplate=(
            "<b>%{y}</b><br>"
            "Потенциал: "
            "%{x:,.0f} ₽ / день"
            "<extra></extra>"
        ),
    )

    fig.update_xaxes(
        title=(
            "Потенциал маржи, ₽ / день"
        ),
    )

    return _base_layout(
        fig,

        height=height,

        left=185,

        right=95,

        bottom=38,

        top=22,
    )


# ============================================================
# 3. СТРУКТУРА РЕШЕНИЙ
# ============================================================

def recommendation_structure_figure(
    recommendations: pd.DataFrame,
) -> go.Figure:

    height = 285

    if (
        recommendations is None
        or recommendations.empty
        or (
            "status"
            not in recommendations.columns
        )
    ):
        return _empty(
            "Нет рекомендаций",
            height=height,
        )

    counts = (
        recommendations[
            "status"
        ]
        .fillna(
            "HOLD"
        )
        .value_counts()
    )

    order = [
        "CLEARANCE",
        "REDUCE",
        "TEST",
        "RAISE",
        "HOLD",
    ]

    labels = {
        "CLEARANCE": (
            "Распродажа"
        ),
        "REDUCE": (
            "Снизить"
        ),
        "TEST": (
            "Тест"
        ),
        "RAISE": (
            "Повысить"
        ),
        "HOLD": (
            "Оставить"
        ),
    }

    colors = {
        "CLEARANCE": (
            "#DC2626"
        ),
        "REDUCE": (
            "#F97316"
        ),
        "TEST": (
            "#EAB308"
        ),
        "RAISE": (
            "#16A34A"
        ),
        "HOLD": (
            "#94A3B8"
        ),
    }

    statuses = [
        status
        for status in order
        if status
        in counts.index
    ]

    values = [
        int(
            counts[
                status
            ]
        )
        for status
        in statuses
    ]

    fig = go.Figure(
        go.Pie(
            labels=[
                labels[
                    status
                ]
                for status
                in statuses
            ],

            values=values,

            hole=0.66,

            marker=dict(
                colors=[
                    colors[
                        status
                    ]
                    for status
                    in statuses
                ],
            ),

            sort=False,

            textinfo="none",

            hovertemplate=(
                "<b>%{label}</b><br>"
                "%{value:,.0f} артикулов<br>"
                "%{percent}"
                "<extra></extra>"
            ),

            domain=dict(
                x=[
                    0.05,
                    0.95,
                ],
                y=[
                    0.02,
                    0.92,
                ],
            ),
        )
    )

    total = sum(
        values
    )

    fig.add_annotation(
        x=0.5,
        y=0.47,

        text=(
            f"<b>{total:,}</b>"
            "<br>"
            "<span "
            "style='font-size:11px;"
            "color:#64748B'>"
            "артикулов"
            "</span>"
        ).replace(
            ",",
            " ",
        ),

        showarrow=False,

        align="center",

        font=dict(
            family=CHART_FONT,
            size=18,
            color="#0F172A",
        ),
    )

    fig.update_layout(
        showlegend=True,

        legend=dict(
            orientation="h",

            yanchor="top",

            y=-0.02,

            xanchor="center",

            x=0.5,

            font=dict(
                size=11,
            ),
        ),
    )

    return _base_layout(
        fig,

        height=height,

        left=15,

        right=15,

        bottom=52,

        top=8,
    )


# ============================================================
# 4. ЗАПАС × ПРОДАЖИ
# ============================================================

def stock_vs_sales_figure(
    portfolio: pd.DataFrame,
) -> go.Figure:

    height = 285

    if (
        portfolio is None
        or portfolio.empty
    ):
        return _empty(
            (
                "Нет данных для "
                "карты запас × продажи"
            ),
            height=height,
        )

    work = (
        portfolio.copy()
    )

    for column in (
        "stock_units",
        "sales_30d",
        "stock_days",
        "margin_upside_day",
    ):

        if (
            column
            not in work.columns
        ):
            work[
                column
            ] = 0

        work[
            column
        ] = _num(
            work[
                column
            ]
        )

    work = (
        work[
            work[
                "stock_units"
            ] > 0
        ]
        .copy()
    )

    if work.empty:
        return _empty(
            "Нет товарного запаса",
            height=height,
        )

    work[
        "label"
    ] = _label(
        work
    )

    # Чтобы scatter оставался читаемым
    work = (
        work
        .sort_values(
            "stock_units",
            ascending=False,
        )
        .head(80)
    )

    max_stock = max(
        float(
            work[
                "stock_units"
            ].max()
        ),
        1.0,
    )

    sizes = (
        9
        + 27
        * (
            work[
                "stock_units"
            ]
            / max_stock
        )
        ** 0.5
    )

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=work[
                "sales_30d"
            ],

            y=work[
                "stock_units"
            ],

            mode="markers",

            text=work[
                "label"
            ],

            customdata=(
                work[
                    [
                        "stock_days",
                        "margin_upside_day",
                    ]
                ]
            ),

            marker=dict(
                size=sizes,

                color=work[
                    "margin_upside_day"
                ],

                colorscale=[
                    [
                        0.0,
                        "#F59E0B",
                    ],
                    [
                        0.5,
                        "#60A5FA",
                    ],
                    [
                        1.0,
                        "#16A34A",
                    ],
                ],

                showscale=True,

                colorbar=dict(
                    title=(
                        "₽/день"
                    ),

                    thickness=8,

                    len=0.62,

                    x=1.01,

                    xanchor="left",

                    y=0.52,

                    yanchor="middle",

                    outlinewidth=0,

                    tickfont=dict(
                        size=9,
                    ),

                    title_font=dict(
                        size=10,
                    ),
                ),

                opacity=0.72,

                line=dict(
                    width=1,
                    color="#FFFFFF",
                ),
            ),

            hovertemplate=(
                "<b>%{text}</b><br>"
                "Продажи 30д: "
                "%{x:,.0f} шт.<br>"
                "Общий запас: "
                "%{y:,.0f} шт.<br>"
                "Запас: "
                "%{customdata[0]:,.0f} дн.<br>"
                "Потенциал: "
                "%{customdata[1]:,.0f} ₽/день"
                "<extra></extra>"
            ),
        )
    )

    fig.update_xaxes(
        title=(
            "Продажи 30д, шт."
        ),
    )

    fig.update_yaxes(
        title=(
            "Общий запас, шт."
        ),
    )

    return _base_layout(
        fig,

        height=height,

        left=65,

        right=75,

        bottom=48,

        top=12,
    )


# ============================================================
# CHART CARD
# ============================================================

def _chart_card(
    title: str,
    subtitle: str,
    figure: go.Figure,
    *,
    height: int,
):
    figure.update_layout(
        height=height - 85,
        autosize=True,
    )

    return dmc.Paper(
        withBorder=True,
        radius=0,
        p="md",
        style={
            "height": f"{height}px",
            "overflow": "hidden",
        },
        children=[
            dmc.Text(
                title,
                fw=800,
                size="18px",
                style={
                    "lineHeight": "1.15",
                    "color": "#0F172A",
                },
            ),

            dmc.Text(
                subtitle,
                size="13px",
                c="dimmed",
                mt=4,
                mb=4,
            ),

            dcc.Graph(
                figure=figure,
                config={
                    "displayModeBar": False,
                },
            ),
        ],
    )

# ============================================================
# CHARTS SECTION
# ============================================================

def pricing_charts_section(
    portfolio: pd.DataFrame,
    recommendations: pd.DataFrame,
):
    stock_fig = stock_structure_figure(
        portfolio
    )

    margin_fig = margin_upside_figure(
        portfolio
    )

    status_fig = recommendation_structure_figure(
        recommendations
    )

    stock_sales_fig = stock_vs_sales_figure(
        portfolio
    )

    return dmc.SimpleGrid(
        cols=2,
        spacing="md",
        children=[
            _chart_card(
                title="Где сосредоточен товарный запас",
                subtitle=(
                    "Топ-10 бренд × категория · "
                    "WB / FBS / товар в пути"
                ),
                figure=stock_fig,
                height=430,
            ),

            _chart_card(
                title="Потенциал дополнительной маржи",
                subtitle=(
                    "Топ-10 бренд × категория · "
                    "модельный эффект в день"
                ),
                figure=margin_fig,
                height=430,
            ),

            _chart_card(
                title="Структура решений",
                subtitle=(
                    "Распределение рекомендаций "
                    "по NM ID"
                ),
                figure=status_fig,
                height=370,
            ),

            _chart_card(
                title="Запас × продажи",
                subtitle=(
                    "Размер точки = запас · "
                    "цвет = потенциал маржи"
                ),
                figure=stock_sales_fig,
                height=370,
            ),
        ],
    )