# gear/app/stats/layout.py
from __future__ import annotations

import dash_mantine_components as dmc
from dash import dcc, html
from dash_iconify import DashIconify

from .components import (
    chart_panel,
    kpi_card,
    section_header,
)
from .config import (
    APP_TITLE,
    COLORS,
    PLOTLY_CONFIG,
)
from .filters import (
    build_filter_panel,
)
from .ids import (
    ANOMALY_CHART_ID,
    CORRELATION_MATRIX_ID,
    INSIGHTS_CONTAINER_ID,
    KPI_BEST_LAG_ID,
    KPI_BEST_WEEKDAY_ID,
    KPI_CORRELATION_ID,
    KPI_MARKETING_ID,
    KPI_MARKETING_SHARE_ID,
    KPI_PRICE_CORRELATION_ID,
    KPI_REVENUE_ID,
    KPI_ROAS_ID,
    LAG_CHART_ID,
    LAG_INSIGHT_ID,
    LAST_UPDATE_ID,
    LOADING_TRIGGER_ID,
    MARKETING_SCATTER_ID,
    MONTH_CHART_ID,
    PRICE_ELASTICITY_CHART_ID,
    PRICE_SCATTER_ID,
    REFRESH_BTN_ID,
    ROAS_CHART_ID,
    ROAS_INSIGHT_ID,
    ROLLING_CORR_CHART_ID,
    TREND_CHART_ID,
    WEEKDAY_CHART_ID,
    MARKETING_SCATTER_INSIGHT_ID,
    CORRELATION_MATRIX_INSIGHT_ID,
    ROLLING_CORR_INSIGHT_ID,
    PRICE_SCATTER_INSIGHT_ID,
    PRICE_ELASTICITY_INSIGHT_ID,
    WEEKDAY_INSIGHT_ID,
    MONTH_INSIGHT_ID,
    ANOMALY_INSIGHT_ID,
    
    

)
from .styles import (
    CHART_GRID_STYLE,
    FULL_WIDTH_STYLE,
    HEADER_STYLE,
    KPI_GRID_STYLE,
    PAGE_STYLE,
    PANEL_STYLE,
)

from .profit_optimizer import (
    build_profit_optimizer_tab,
)


def _empty_figure():
    return {
        "data": [],
        "layout": {
            "template": (
                "plotly_white"
            ),
            "paper_bgcolor": (
                "#FFFFFF"
            ),
            "plot_bgcolor": (
                "#FFFFFF"
            ),
            "xaxis": {
                "visible": False,
            },
            "yaxis": {
                "visible": False,
            },
            "annotations": [
                {
                    "text": (
                        "Данные "
                        "загружаются…"
                    ),
                    "x": 0.5,
                    "y": 0.5,
                    "xref": "paper",
                    "yref": "paper",
                    "showarrow": False,
                }
            ],
        },
    }


def graph_component(
    component_id: str,
    height: str = "460px",
):
    return dcc.Graph(
        id=component_id,
        figure=_empty_figure(),
        config=PLOTLY_CONFIG,
        style={
            "height": height,
        },
    )


def build_header():
    return html.Div(
        style=HEADER_STYLE,
        children=[
            dmc.Group(
                justify=(
                    "space-between"
                ),
                align="center",
                children=[
                    dmc.Group(
                        gap=12,
                        children=[
                            html.Div(
                                style={
                                    "width": (
                                        "40px"
                                    ),
                                    "height": (
                                        "40px"
                                    ),
                                    "display": (
                                        "flex"
                                    ),
                                    "alignItems": (
                                        "center"
                                    ),
                                    "justifyContent": (
                                        "center"
                                    ),
                                    "backgroundColor": (
                                        COLORS[
                                            "light_green"
                                        ]
                                    ),
                                    "border": (
                                        f"1px solid "
                                        f"{COLORS['border']}"
                                    ),
                                },
                                children=(
                                    DashIconify(
                                        icon=(
                                            "solar:"
                                            "chart-2-linear"
                                        ),
                                        width=22,
                                        color=COLORS[
                                            "green"
                                        ],
                                    )
                                ),
                            ),

                            html.Div(
                                children=[
                                    html.H1(
                                        APP_TITLE,
                                        style={
                                            "margin": 0,
                                            "fontSize": (
                                                "21px"
                                            ),
                                            "fontWeight": (
                                                700
                                            ),
                                            "color": (
                                                COLORS[
                                                    "text"
                                                ]
                                            ),
                                        },
                                    ),

                                    dmc.Text(
                                        (
                                            "Корреляции, "
                                            "маркетинг, "
                                            "цены, сезонность "
                                            "и поиск аномалий"
                                        ),
                                        size="xs",
                                        c=COLORS[
                                            "muted"
                                        ],
                                    ),
                                ],
                            ),
                        ],
                    ),

                    dmc.Group(
                        gap=8,
                        children=[
                            html.Div(
                                style={
                                    "border": (
                                        f"1px solid "
                                        f"{COLORS['border']}"
                                    ),
                                    "height": (
                                        "34px"
                                    ),
                                    "display": (
                                        "flex"
                                    ),
                                    "alignItems": (
                                        "center"
                                    ),
                                    "padding": (
                                        "0 10px"
                                    ),
                                    "gap": (
                                        "6px"
                                    ),
                                },
                                children=[
                                    DashIconify(
                                        icon=(
                                            "solar:"
                                            "clock-circle-linear"
                                        ),
                                        width=15,
                                        color=COLORS[
                                            "muted"
                                        ],
                                    ),
                                    dmc.Text(
                                        (
                                            "Обновление:"
                                        ),
                                        size="xs",
                                        c=COLORS[
                                            "muted"
                                        ],
                                    ),
                                    dmc.Text(
                                        id=(
                                            LAST_UPDATE_ID
                                        ),
                                        children="—",
                                        size="xs",
                                        fw=600,
                                    ),
                                ],
                            ),

                            dmc.Button(
                                id=(
                                    REFRESH_BTN_ID
                                ),
                                children=(
                                    "Обновить"
                                ),
                                leftSection=(
                                    DashIconify(
                                        icon=(
                                            "solar:"
                                            "refresh-linear"
                                        ),
                                        width=16,
                                    )
                                ),
                                radius=0,
                                size="xs",
                                h=34,
                                color="teal",
                                variant="light",
                            ),
                        ],
                    ),
                ],
            ),
        ],
    )





def build_kpi_section():
    return html.Div(
        children=[
            section_header(
                "Ключевые показатели",
                (
                    "Показатели "
                    "пересчитываются "
                    "для выбранного периода"
                ),
            ),

            html.Div(
                style={
                    **KPI_GRID_STYLE,
                    "marginTop": "12px",
                },
                children=[
                    kpi_card(
                        title="Выручка без НДС",
                        value_id=KPI_REVENUE_ID,
                        subtitle=(
                            "За выбранный период "
                            "(по нашей цене)"
                        ),
                        tooltip=(
                            "Суммарная выручка без НДС "
                            "за выбранный период. "
                            "Рассчитывается по нашей "
                            "цене реализации."
                        ),
                        icon=(
                            "solar:"
                            "wallet-money-linear"
                        ),
                        accent=COLORS[
                            "blue"
                        ],
                    ),

                    kpi_card(
                        title="Маркетинг",
                        value_id=KPI_MARKETING_ID,
                        subtitle=(
                            "Все расходы на маркетинг"
                        ),
                        tooltip=(
                            "Общая сумма расходов "
                            "на маркетинг за выбранный "
                            "период."
                        ),
                        icon=(
                            "solar:"
                            "graph-up-linear"
                        ),
                        accent=COLORS[
                            "orange"
                        ],
                    ),

                    kpi_card(
                        title="Доля маркетинга",
                        value_id=(
                            KPI_MARKETING_SHARE_ID
                        ),
                        subtitle=(
                            "Маркетинг / выручка"
                        ),
                        tooltip=(
                            "Показывает, какую долю "
                            "выручки составляют расходы "
                            "на маркетинг. Например, "
                            "10% означает, что на каждые "
                            "100 ₽ выручки приходится "
                            "10 ₽ маркетинговых расходов."
                        ),
                        icon=(
                            "solar:"
                            "pie-chart-2-linear"
                        ),
                        accent=COLORS[
                            "purple"
                        ],
                    ),

                    kpi_card(
                        title="ROAS",
                        value_id=KPI_ROAS_ID,
                        subtitle=(
                            "Выручка / маркетинг"
                        ),
                        tooltip=(
                            "Показывает, сколько рублей "
                            "выручки приходится на 1 ₽ "
                            "расходов на маркетинг. "
                            "Например, ROAS 5 означает, "
                            "что на каждый 1 ₽ маркетинга "
                            "приходится 5 ₽ выручки."
                        ),
                        icon=(
                            "solar:"
                            "chart-square-linear"
                        ),
                        accent=COLORS[
                            "green"
                        ],
                    ),

                    kpi_card(
                        title=(
                            "Маркетинг ↔ выручка"
                        ),
                        value_id=(
                            KPI_CORRELATION_ID
                        ),
                        subtitle=(
                            "Корреляция Pearson"
                        ),
                        tooltip=(
                            "Показывает силу связи между "
                            "расходами на маркетинг и "
                            "выручкой. Значение ближе "
                            "к +1 означает сильную "
                            "положительную связь, "
                            "около 0 — слабую связь, "
                            "ближе к −1 — обратную связь. "
                            "Корреляция не доказывает "
                            "причинно-следственную связь."
                        ),
                        icon=(
                            "solar:"
                            "link-circle-linear"
                        ),
                        accent=COLORS[
                            "blue"
                        ],
                    ),

                    kpi_card(
                        title="Лучший лаг",
                        value_id=KPI_BEST_LAG_ID,
                        subtitle=(
                            "Макс. связь "
                            "маркетинг → выручка"
                        ),
                        tooltip=(
                            "Показывает временную задержку, "
                            "при которой связь между "
                            "маркетинговыми расходами "
                            "и последующей выручкой "
                            "максимальна. Например, лаг "
                            "3 дня означает, что наиболее "
                            "сильная связь наблюдается "
                            "между маркетингом и выручкой "
                            "через 3 дня."
                        ),
                        icon=(
                            "solar:"
                            "clock-circle-linear"
                        ),
                        accent=COLORS[
                            "purple"
                        ],
                    ),

                    kpi_card(
                        title=(
                            "Цена ↔ количество"
                        ),
                        value_id=(
                            KPI_PRICE_CORRELATION_ID
                        ),
                        subtitle=(
                            "Корреляция Pearson"
                        ),
                        tooltip=(
                            "Показывает связь между "
                            "ценой товара и количеством "
                            "проданных единиц. "
                            "Отрицательное значение "
                            "означает, что при росте цены "
                            "количество продаж обычно "
                            "снижается. Положительное — "
                            "что цена и количество продаж "
                            "движутся в одном направлении."
                        ),
                        icon=(
                            "solar:"
                            "tag-price-linear"
                        ),
                        accent=COLORS[
                            "orange"
                        ],
                    ),

                    kpi_card(
                        title="Лучший день",
                        value_id=(
                            KPI_BEST_WEEKDAY_ID
                        ),
                        subtitle=(
                            "По средней выручке"
                        ),
                        tooltip=(
                            "День недели с самой высокой "
                            "средней выручкой за выбранный "
                            "период. Для каждого дня недели "
                            "рассчитывается средняя выручка, "
                            "после чего выбирается "
                            "максимальное значение."
                        ),
                        icon=(
                            "solar:"
                            "calendar-linear"
                        ),
                        accent=COLORS[
                            "green"
                        ],
                    ),
                ],
            ),
        ],
    )


def build_overview_tab():
    return html.Div(
        style={
            "paddingTop": (
                "16px"
            ),
        },
        children=[
            chart_panel(
                title=(
                    "Выручка и "
                    "маркетинговые расходы"
                ),
                subtitle=(
                    "Совместная динамика "
                    "основных показателей"
                ),
                graph=graph_component(
                    TREND_CHART_ID,
                    "520px",
                ),
            ),

            html.Div(
                style={
                    **CHART_GRID_STYLE,
                    "marginTop": (
                        "14px"
                    ),
                },
                children=[
                    chart_panel(
                            title=(
                                "Маркетинг → "
                                "выручка"
                            ),
                            subtitle=(
                                "Связь маркетинговых расходов "
                                "с выручкой по нашей цене"
                            ),
                            graph=(
                                graph_component(
                                    MARKETING_SCATTER_ID,
                                      "560px",
                                )
                            ),
             insight=dmc.Alert(
                        title="Что показывает график",
                        children=html.Div(
                            id=MARKETING_SCATTER_INSIGHT_ID,
                            children="Расчёт аналитического вывода…",
                            style={
                                "height": "120px",
                                "overflowY": "auto",
                                "overflowX": "hidden",
                                "paddingRight": "8px",
                            },
                        ),
                        icon=DashIconify(
                            icon="solar:lightbulb-bolt-linear",
                            width=18,
                        ),
                        color="teal",
                        variant="light",
                        radius=0,
                        style={
                            "height": "190px",
                            "overflow": "hidden",
                        },
                        styles={
                            "title": {
                                "fontSize": "12px",
                                "fontWeight": 600,
                            },
                            "message": {
                                "fontSize": "11px",
                                "lineHeight": "18px",
                            },
                        },
                    ),
                        ),
                   chart_panel(
    title=(
        "Корреляционная "
        "матрица"
    ),
    subtitle=(
        "Связь между "
        "ключевыми показателями"
    ),
    graph=(
        graph_component(
            CORRELATION_MATRIX_ID,
              "560px",
        )
    ),
    insight=dmc.Alert(
            title="Что показывает матрица",
            children=html.Div(
                id=CORRELATION_MATRIX_INSIGHT_ID,
                children="Расчёт аналитического вывода…",
                style={
                    "height": "120px",
                    "overflowY": "auto",
                    "overflowX": "hidden",
                    "paddingRight": "8px",
                },
            ),
            icon=DashIconify(
                icon="solar:lightbulb-bolt-linear",
                width=18,
            ),
            color="teal",
            variant="light",
            radius=0,
            style={
                "height": "190px",
                "overflow": "hidden",
            },
            styles={
                "title": {
                    "fontSize": "12px",
                    "fontWeight": 600,
                },
                "message": {
                    "fontSize": "11px",
                    "lineHeight": "18px",
                },
            },
        ),
        ),
                ],
            ),
        ],
    )


def build_marketing_tab():
    return html.Div(
        style={
            "paddingTop": (
                "16px"
            ),
        },
        children=[
            html.Div(
                style=(
                    CHART_GRID_STYLE
                ),
                children=[
                    chart_panel(
                        title=(
                            "Lag-анализ "
                            "маркетинга"
                        ),
                        subtitle=(
                            "Через сколько периодов после "
                            "маркетинговых расходов наиболее "
                            "заметна связь с выручкой"
                        ),
                        graph=(
                            graph_component(
                                LAG_CHART_ID,
                                "520px",
                            )
                        ),
                        insight=dmc.Alert(
                                title="Что показывает график",
                                children=html.Div(
                                    id=LAG_INSIGHT_ID,
                                    children="Расчёт аналитического вывода…",
                                    style={
                                        "height": "120px",
                                        "overflowY": "auto",
                                        "overflowX": "hidden",
                                        "paddingRight": "8px",
                                    },
                                ),
                                icon=DashIconify(
                                    icon="solar:lightbulb-bolt-linear",
                                    width=18,
                                ),
                                color="teal",
                                variant="light",
                                radius=0,
                                style={
                                    "height": "190px",
                                    "overflow": "hidden",
                                },
                                styles={
                                    "title": {
                                        "fontSize": "12px",
                                        "fontWeight": 600,
                                    },
                                    "message": {
                                        "fontSize": "11px",
                                        "lineHeight": "18px",
                                    },
                                },
                            ),
                    ),
                    chart_panel(
                            title=(
                                "Динамика ROAS"
                            ),
                            subtitle=(
                                "Сколько рублей выручки "
                                "приходится на 1 ₽ "
                                "маркетинговых расходов"
                            ),
                            graph=(
                                graph_component(
                                    ROAS_CHART_ID,
                                    "520px",
                                )
                            ),
                            insight=dmc.Alert(
                                    title="Что показывает график",
                                    children=html.Div(
                                        id=ROAS_INSIGHT_ID,
                                        children="Расчёт аналитического вывода…",
                                        style={
                                            "height": "120px",
                                            "overflowY": "auto",
                                            "overflowX": "hidden",
                                            "paddingRight": "8px",
                                        },
                                    ),
                                    icon=DashIconify(
                                        icon="solar:lightbulb-bolt-linear",
                                        width=18,
                                    ),
                                    color="teal",
                                    variant="light",
                                    radius=0,
                                    style={
                                        "height": "190px",
                                        "overflow": "hidden",
                                    },
                                    styles={
                                        "title": {
                                            "fontSize": "12px",
                                            "fontWeight": 600,
                                        },
                                        "message": {
                                            "fontSize": "11px",
                                            "lineHeight": "18px",
                                        },
                                    },
                                ),
                        ),
                ],
            ),

            html.Div(
                style=(
                    FULL_WIDTH_STYLE
                ),
                children=[
                    chart_panel(
    title=(
        "Стабильность связи "
        "маркетинга и выручки"
    ),
    subtitle=(
        "Скользящая корреляция "
        "показывает, как связь "
        "меняется во времени"
    ),
    graph=(
        graph_component(
            ROLLING_CORR_CHART_ID,
            "600px",
        )
    ),
                insight=dmc.Alert(
                    title="Что показывает график",
                    children=html.Div(
                        id=ROLLING_CORR_INSIGHT_ID,
                        children=(
                            "Расчёт аналитического вывода…"
                        ),
                        style={
                            "height": "120px",
                            "overflowY": "auto",
                            "overflowX": "hidden",
                            "paddingRight": "8px",
                        },
                    ),
                    icon=DashIconify(
                        icon=(
                            "solar:"
                            "lightbulb-bolt-linear"
                        ),
                        width=18,
                    ),
                    color="teal",
                    variant="light",
                    radius=0,
                    style={
                        "height": "190px",
                        "overflow": "hidden",
                    },
                    styles={
                        "title": {
                            "fontSize": "12px",
                            "fontWeight": 600,
                        },
                        "message": {
                            "fontSize": "11px",
                            "lineHeight": "18px",
                        },
                    },
                ),
            ),
                ],
            ),
        ],
    )


def build_price_tab():
    return html.Div(
        style={
            "paddingTop": (
                "16px"
            ),
        },
        children=[
            html.Div(
                style=(
                    CHART_GRID_STYLE
                ),
                children=[
                    chart_panel(
                        title=(
                            "Цена → количество"
                        ),
                        subtitle=(
                            "Связь средней цены "
                            "реализации с объёмом "
                            "продаж"
                        ),
                        graph=(
                            graph_component(
                                PRICE_SCATTER_ID,
                                "520px",
                            )
                        ),
                        insight=dmc.Alert(
                            title="Что показывает график",
                            children=html.Div(
                                id=PRICE_SCATTER_INSIGHT_ID,
                                children=(
                                    "Расчёт аналитического вывода…"
                                ),
                                style={
                                    "height": "120px",
                                    "overflowY": "auto",
                                    "overflowX": "hidden",
                                    "paddingRight": "8px",
                                },
                            ),
                            icon=DashIconify(
                                icon=(
                                    "solar:"
                                    "lightbulb-bolt-linear"
                                ),
                                width=18,
                            ),
                            color="teal",
                            variant="light",
                            radius=0,
                            style={
                                "height": "190px",
                                "overflow": "hidden",
                            },
                            styles={
                                "title": {
                                    "fontSize": "12px",
                                    "fontWeight": 600,
                                },
                                "message": {
                                    "fontSize": "11px",
                                    "lineHeight": "18px",
                                },
                            },
                        ),
                    ),

                    chart_panel(
                            title=(
                                "Изменение цены "
                                "и спроса"
                            ),
                            subtitle=(
                                "Как изменение средней цены "
                                "связано с изменением объёма продаж"
                            ),
                            graph=(
                                graph_component(
                                    PRICE_ELASTICITY_CHART_ID,
                                    "520px",
                                )
                            ),
                            insight=dmc.Alert(
                                title="Что показывает график",
                                children=html.Div(
                                    id=PRICE_ELASTICITY_INSIGHT_ID,
                                    children=(
                                        "Расчёт аналитического вывода…"
                                    ),
                                    style={
                                        "height": "120px",
                                        "overflowY": "auto",
                                        "overflowX": "hidden",
                                        "paddingRight": "8px",
                                    },
                                ),
                                icon=DashIconify(
                                    icon=(
                                        "solar:"
                                        "lightbulb-bolt-linear"
                                    ),
                                    width=18,
                                ),
                                color="teal",
                                variant="light",
                                radius=0,
                                style={
                                    "height": "190px",
                                    "overflow": "hidden",
                                },
                                styles={
                                    "title": {
                                        "fontSize": "12px",
                                        "fontWeight": 600,
                                    },
                                    "message": {
                                        "fontSize": "11px",
                                        "lineHeight": "18px",
                                    },
                                },
                            ),
                        ),
                ],
            ),
        ],
    )


def build_seasonality_tab():
    return html.Div(
        style={
            "paddingTop": (
                "16px"
            ),
        },
        children=[
            html.Div(
                style=(
                    CHART_GRID_STYLE
                ),
                children=[
                                    chart_panel(
                    title=(
                        "Сезонность "
                        "по дням недели"
                    ),
                    subtitle=(
                        "Отклонение средней "
                        "выручки каждого дня "
                        "от общего среднего"
                    ),
                    graph=(
                        graph_component(
                            WEEKDAY_CHART_ID,
                            "520px",
                        )
                    ),
                    insight=dmc.Alert(
                        title="Что показывает график",
                        children=html.Div(
                            id=WEEKDAY_INSIGHT_ID,
                            children=(
                                "Расчёт аналитического вывода…"
                            ),
                            style={
                                "height": "120px",
                                "overflowY": "auto",
                                "overflowX": "hidden",
                                "paddingRight": "8px",
                            },
                        ),
                        icon=DashIconify(
                            icon=(
                                "solar:"
                                "lightbulb-bolt-linear"
                            ),
                            width=18,
                        ),
                        color="teal",
                        variant="light",
                        radius=0,
                        style={
                            "height": "190px",
                            "overflow": "hidden",
                        },
                        styles={
                            "title": {
                                "fontSize": "12px",
                                "fontWeight": 600,
                            },
                            "message": {
                                "fontSize": "11px",
                                "lineHeight": "18px",
                            },
                        },
                    ),
                ),

                    chart_panel(
                            title=(
                                "Сезонность "
                                "по месяцам"
                            ),
                            subtitle=(
                                "Отклонение средней дневной "
                                "выручки каждого месяца "
                                "от общего среднего"
                            ),
                            graph=(
                                graph_component(
                                    MONTH_CHART_ID,
                                    "520px",
                                )
                            ),
                            insight=dmc.Alert(
                                title="Что показывает график",
                                children=html.Div(
                                    id=MONTH_INSIGHT_ID,
                                    children=(
                                        "Расчёт аналитического вывода…"
                                    ),
                                    style={
                                        "height": "120px",
                                        "overflowY": "auto",
                                        "overflowX": "hidden",
                                        "paddingRight": "8px",
                                    },
                                ),
                                icon=DashIconify(
                                    icon=(
                                        "solar:"
                                        "lightbulb-bolt-linear"
                                    ),
                                    width=18,
                                ),
                                color="teal",
                                variant="light",
                                radius=0,
                                style={
                                    "height": "190px",
                                    "overflow": "hidden",
                                },
                                styles={
                                    "title": {
                                        "fontSize": "12px",
                                        "fontWeight": 600,
                                    },
                                    "message": {
                                        "fontSize": "11px",
                                        "lineHeight": "18px",
                                    },
                                },
                            ),
                        ),
                ],
            ),
        ],
    )


def build_anomalies_tab():
    return html.Div(
        style={
            "paddingTop": (
                "16px"
            ),
        },
        children=[
            chart_panel(
                    title=(
                        "Аномальные периоды"
                    ),
                    subtitle=(
                        "Необычные изменения выручки "
                        "и возможные факторы отклонений"
                    ),
                    graph=(
                        graph_component(
                            ANOMALY_CHART_ID,
                            "540px",
                        )
                    ),
                    insight=dmc.Alert(
                        title="Что показывает график",
                        children=html.Div(
                            id=ANOMALY_INSIGHT_ID,
                            children=(
                                "Расчёт аналитического вывода…"
                            ),
                            style={
                                "height": "140px",
                                "overflowY": "auto",
                                "overflowX": "hidden",
                                "paddingRight": "8px",
                            },
                        ),
                        icon=DashIconify(
                            icon=(
                                "solar:"
                                "lightbulb-bolt-linear"
                            ),
                            width=18,
                        ),
                        color="teal",
                        variant="light",
                        radius=0,
                        style={
                            "height": "210px",
                            "overflow": "hidden",
                        },
                        styles={
                            "title": {
                                "fontSize": "12px",
                                "fontWeight": 600,
                            },
                            "message": {
                                "fontSize": "11px",
                                "lineHeight": "18px",
                            },
                        },
                    ),
                ),
        ],
    )


def build_insights_tab():
    return html.Div(
        style={
            "paddingTop": (
                "16px"
            ),
        },
        children=[
            html.Div(
                style=PANEL_STYLE,
                children=[
                    section_header(
                        "Автоматические выводы",
                        (
                            "Система автоматически "
                            "описывает наиболее "
                            "заметные статистические "
                            "закономерности"
                        ),
                    ),

                    html.Div(
                        id=(
                            INSIGHTS_CONTAINER_ID
                        ),
                        style={
                            "marginTop": (
                                "14px"
                            ),
                        },
                    ),
                ],
            ),
        ],
    )


def build_main_tabs():
    return dmc.Tabs(
        value="overview",
        variant="outline",
        radius=0,
        keepMounted=True,
        children=[
            dmc.TabsList(
                children=[
                    dmc.TabsTab(
                        "Обзор",
                        value="overview",
                    ),

                    dmc.TabsTab(
                        "Маркетинг",
                        value="marketing",
                    ),

                    dmc.TabsTab(
                        "Цена",
                        value="price",
                    ),

                    dmc.TabsTab(
                        "Сезонность",
                        value="seasonality",
                    ),

                    dmc.TabsTab(
                        "Аномалии",
                        value="anomalies",
                    ),

                    dmc.TabsTab(
                        "Выводы",
                        value="insights",
                    ),
                    
                    dmc.TabsTab(
                        "Оптимизация прибыли",
                        value="profit_optimizer",
                    ),
                ],
            ),

            dmc.TabsPanel(
                build_overview_tab(),
                value="overview",
            ),

            dmc.TabsPanel(
                build_marketing_tab(),
                value="marketing",
            ),

            dmc.TabsPanel(
                build_price_tab(),
                value="price",
            ),

            dmc.TabsPanel(
                build_seasonality_tab(),
                value="seasonality",
            ),

            dmc.TabsPanel(
                build_anomalies_tab(),
                value="anomalies",
            ),

            dmc.TabsPanel(
                build_insights_tab(),
                value="insights",
            ),
            
            dmc.TabsPanel(
                build_profit_optimizer_tab(),
                value="profit_optimizer",
            ),
        ],
    )


def build_loader():
    return dcc.Loading(
        type="cube",
        color=COLORS[
            "green"
        ],
        fullscreen=True,
        delay_show=150,
        delay_hide=150,
        overlay_style={
            "visibility": (
                "visible"
            ),
            "backgroundColor": (
                "rgba("
                "255,255,255,0.75"
                ")"
            ),
        },
        children=html.Div(
            id=LOADING_TRIGGER_ID,
            style={
                "display": "none",
            },
        ),
    )


def build_layout():
    return dmc.MantineProvider(
        theme={
            "primaryColor": (
                "teal"
            ),
            "fontFamily": (
                "Inter, "
                "Arial, "
                "sans-serif"
            ),
            "defaultRadius": 0,
        },
        children=[
            build_loader(),

            html.Div(
                style=PAGE_STYLE,
                children=[
                    build_header(),

                    html.Div(
                        style={
                            "marginTop": (
                                "14px"
                            ),
                        },
                        children=(
                            build_filter_panel()
                        ),
                    ),

                    html.Div(
                        style={
                            "marginTop": (
                                "18px"
                            ),
                        },
                        children=(
                            build_kpi_section()
                        ),
                    ),

                    html.Div(
                        style={
                            "marginTop": (
                                "18px"
                            ),
                        },
                        children=(
                            build_main_tabs()
                        ),
                    ),

                    html.Div(
                        style={
                            "height": (
                                "30px"
                            ),
                        },
                    ),
                ],
            ),
        ],
    )


layout = build_layout()