# gear/app/loans/layout.py
from __future__ import annotations

import dash_mantine_components as dmc
from dash import dcc, html
from dash_iconify import DashIconify

from .components import (
    action_button,
    chart_panel,
    kpi_card,
    section_header,
)
from .config import (
    APP_TITLE,
    COLORS,
    PLOTLY_CONFIG,
)
from .filters import build_filter_panel
from .grid import (
    build_loans_grid,
    build_transactions_grid,
)
from .ids import (
    COUNTERPARTY_DEBT_CHART_ID,
    DASHBOARD_LOADING_ID,
    DASHBOARD_LOADING_TRIGGER_ID,
    DATA_SIGNAL_ID,
    DEBT_DYNAMICS_CHART_ID,
    DOWNLOAD_EXCEL_BTN_ID,
    DOWNLOAD_ID,
    FILTER_STORE_ID,
    INTEREST_FLOW_CHART_ID,
    KPI_ACTIVE_LOANS_ID,
    KPI_DUE_30_ID,
    KPI_INTEREST_DEBT_ID,
    KPI_OVERDUE_ID,
    KPI_PRINCIPAL_DEBT_ID,
    KPI_TOTAL_DEBT_ID,
    KPI_TOTAL_DRAWNDOWN_ID,
    KPI_WEIGHTED_RATE_ID,
    LAST_UPDATE_ID,
    MATURITY_CHART_ID,
    REFRESH_BTN_ID,
    SELECTED_LOAN_CHART_ID,
    SELECTED_LOAN_META_ID,
    SELECTED_LOAN_STORE_ID,
    SELECTED_LOAN_TITLE_ID,
    DEBT_DYNAMICS_INSIGHT_ID,
    COUNTERPARTY_DEBT_INSIGHT_ID,
    MATURITY_INSIGHT_ID,
    INTEREST_FLOW_INSIGHT_ID,
)

from .selected_loan_panel import (
    build_selected_loan_panel,
)

from .automatic_alerts import (
    build_alerts_button,
    build_alerts_modal,
)

from .daily_interest_indicator import (
    build_daily_interest_indicator,
    build_daily_interest_modal,
)


PAGE_STYLE = {
    "backgroundColor": "#F6F7F8",
    "minHeight": "100vh",
    "padding": "16px",
}

HEADER_STYLE = {
    "backgroundColor": COLORS["white"],
    "border": f"1px solid {COLORS['border']}",
    "padding": "14px 16px",
    "marginBottom": "10px",
}

KPI_GRID_STYLE = {
    "display": "grid",
    "gridTemplateColumns": (
        "repeat(4, minmax(190px, 1fr))"
    ),
    "gap": "8px",
}

CHART_GRID_STYLE = {
    "display": "grid",
    "gridTemplateColumns": (
        "repeat(2, minmax(0, 1fr))"
    ),
    "columnGap": "10px",
    "rowGap": "12px",
    "alignItems": "stretch",
}


def _empty_figure():
    return {
        "data": [],
        "layout": {
            "template": "plotly_white",
            "paper_bgcolor": "#FFFFFF",
            "plot_bgcolor": "#FFFFFF",
            "xaxis": {"visible": False},
            "yaxis": {"visible": False},
            "annotations": [
                {
                    "text": "Данные загружаются…",
                    "x": 0.5,
                    "y": 0.5,
                    "xref": "paper",
                    "yref": "paper",
                    "showarrow": False,
                }
            ],
        },
    }


def build_header():
    return html.Div(
        style=HEADER_STYLE,
        children=[
            html.Div(
                style={
                    "display": "flex",
                    "alignItems": "center",
                    "justifyContent": "space-between",
                    "gap": "18px",
                    "flexWrap": "wrap",
                },
                children=[
                    html.Div(
                        style={
                            "display": "flex",
                            "alignItems": "center",
                            "gap": "12px",
                        },
                        children=[
                            html.Div(
                                style={
                                    "width": "38px",
                                    "height": "38px",
                                    "display": "flex",
                                    "alignItems": "center",
                                    "justifyContent": "center",
                                    "backgroundColor": COLORS["light_green"],
                                    "border": f"1px solid {COLORS['border']}",
                                },
                                children=DashIconify(
                                    icon="solar:hand-money-linear",
                                    width=22,
                                    color=COLORS["green"],
                                ),
                            ),
                            html.Div(
                                children=[
                                    html.H1(
                                        APP_TITLE,
                                        style={
                                            "margin": 0,
                                            "fontSize": "21px",
                                            "fontWeight": 700,
                                            "lineHeight": "26px",
                                            "color": COLORS["text"],
                                        },
                                    ),
                                    html.Div(
                                        (
                                            "Мониторинг портфеля обязательств, "
                                            "сроков погашения и процентной нагрузки"
                                        ),
                                        style={
                                            "marginTop": "3px",
                                            "fontSize": "12px",
                                            "color": COLORS["muted"],
                                        },
                                    ),
                                ],
                            ),
                        ],
                    ),
                    html.Div(
                        style={
                            "display": "flex",
                            "alignItems": "center",
                            "gap": "8px",
                            "flexWrap": "wrap",
                        },
                        children=[
                            html.Div(
                                style={
                                    "display": "flex",
                                    "alignItems": "center",
                                    "gap": "6px",
                                    "height": "34px",
                                    "padding": "0 10px",
                                    "backgroundColor": "#FFFFFF",
                                    "border": f"1px solid {COLORS['border']}",
                                },
                                children=[
                                    DashIconify(
                                        icon="solar:clock-circle-linear",
                                        width=15,
                                        color=COLORS["muted"],
                                    ),
                                    html.Span(
                                        "Обновление:",
                                        style={
                                            "fontSize": "11px",
                                            "color": COLORS["muted"],
                                        },
                                    ),
                                    html.Span(
                                        id=LAST_UPDATE_ID,
                                        children="—",
                                        style={
                                            "fontSize": "11px",
                                            "fontWeight": 600,
                                        },
                                    ),
                                ],
                            ),
                            
                            build_daily_interest_indicator(),
                            build_alerts_button(),
                            
                            action_button(
                                component_id=REFRESH_BTN_ID,
                                label="Обновить",
                                icon="solar:refresh-linear",
                                color="gray",
                                variant="outline",
                            ),
                            action_button(
                                component_id=DOWNLOAD_EXCEL_BTN_ID,
                                label="Excel",
                                icon="material-symbols:download-rounded",
                                color="green",
                                variant="outline",
                            ),
                        ],
                    ),
                ],
            )
        ],
    )


def build_kpis():
    return html.Div(
        style=KPI_GRID_STYLE,
        children=[
            kpi_card(
                title="Активные договоры",
                value_id=KPI_ACTIVE_LOANS_ID,
                subtitle="с ненулевым долгом",
                icon="solar:document-text-linear",
                accent=COLORS["green"],
            ),
            kpi_card(
                title="Общий долг",
                value_id=KPI_TOTAL_DEBT_ID,
                subtitle="тело + проценты",
                icon="solar:wallet-money-linear",
                accent=COLORS["dark_green"],
            ),
            kpi_card(
                title="Основной долг",
                value_id=KPI_PRINCIPAL_DEBT_ID,
                subtitle="остаток тела займа",
                icon="solar:banknote-2-linear",
                accent=COLORS["blue"],
            ),
            kpi_card(
                title="Проценты к оплате",
                value_id=KPI_INTEREST_DEBT_ID,
                subtitle="накопленный процентный долг",
                icon="solar:percent-linear",
                accent=COLORS["orange"],
            ),
            kpi_card(
                title="Средневзвешенная ставка",
                value_id=KPI_WEIGHTED_RATE_ID,
                subtitle="взвешено по основному долгу",
                icon="solar:graph-up-linear",
                accent=COLORS["green"],
            ),
            kpi_card(
                title="Погашение ≤ 30 дней",
                value_id=KPI_DUE_30_ID,
                subtitle="договоров к погашению",
                icon="solar:calendar-minimalistic-linear",
                accent=COLORS["yellow"],
            ),
            kpi_card(
                title="Просрочено",
                value_id=KPI_OVERDUE_ID,
                subtitle="договоров с истёкшим сроком",
                icon="solar:danger-triangle-linear",
                accent=COLORS["red"],
            ),
            kpi_card(
                title="Всего привлечено",
                value_id=KPI_TOTAL_DRAWNDOWN_ID,
                subtitle="накопительный объём выдач",
                icon="solar:inbox-in-linear",
                accent=COLORS["blue"],
            ),
        ],
    )


def build_overview():
    return html.Div(
        children=[
            html.Div(
                style=CHART_GRID_STYLE,
                children=[
                    chart_panel(
                        title="Динамика задолженности",
                        subtitle=(
                            "Основной долг, проценты "
                            "и общий объём обязательств"
                        ),
              graph=dcc.Graph(
                    id=DEBT_DYNAMICS_CHART_ID,
                    figure=_empty_figure(),

                    config={
                        **PLOTLY_CONFIG,

                        "toImageButtonOptions": {
                            "format": "png",
                            "filename": "Динамика_задолженности",
                            "width": 1800,
                            "height": 900,
                            "scale": 2,
                        },
                    },

                    style={
                        "height": "100%",
                        "width": "100%",
                    },
                ),
                        insight_id=DEBT_DYNAMICS_INSIGHT_ID,
                    ),
                    chart_panel(
                            title="Долг по контрагентам",

                            subtitle=(
                                "Крупнейшие кредиторы / заимодавцы"
                            ),

                            graph=dcc.Graph(
                                id=COUNTERPARTY_DEBT_CHART_ID,

                                figure=_empty_figure(),

                                config={
                                    **PLOTLY_CONFIG,

                                    "toImageButtonOptions": {
                                        "format": "png",
                                        "filename": (
                                            "Долг_по_контрагентам"
                                        ),
                                        "width": 1800,
                                        "height": 900,
                                        "scale": 2,
                                    },
                                },

                                style={
                                    "height": "100%",
                                    "width": "100%",
                                },
                            ),

                            insight_id=(
                                COUNTERPARTY_DEBT_INSIGHT_ID
                            ),
                        ),
                    chart_panel(
                        title="График погашения",

                        subtitle=(
                            "Распределение текущего долга "
                            "по срокам погашения"
                        ),

                        graph=dcc.Graph(
                            id=MATURITY_CHART_ID,

                            figure=_empty_figure(),

                            config={
                                **PLOTLY_CONFIG,

                                "toImageButtonOptions": {
                                    "format": "png",

                                    "filename": (
                                        "График_погашения_задолженности"
                                    ),

                                    "width": 1800,
                                    "height": 900,
                                    "scale": 2,
                                },
                            },

                            style={
                                "height": "100%",
                                "width": "100%",
                            },
                        ),

                        insight_id=(
                            MATURITY_INSIGHT_ID
                        ),
                    ),
                    chart_panel(
                        title="Процентный поток",

                        subtitle=(
                            "Начисление, погашение "
                            "и изменение процентной задолженности"
                        ),

                        graph=dcc.Graph(
                            id=INTEREST_FLOW_CHART_ID,

                            figure=_empty_figure(),

                            config={
                                **PLOTLY_CONFIG,

                                "toImageButtonOptions": {
                                    "format": "png",

                                    "filename": (
                                        "Процентный_поток"
                                    ),

                                    "width": 1800,
                                    "height": 900,
                                    "scale": 2,
                                },
        },

        style={
            "height": "100%",
            "width": "100%",
        },
    ),

    insight_id=(
        INTEREST_FLOW_INSIGHT_ID
    ),
),
                ],
            ),
        ],
    )


def build_registry():
    return html.Div(
        style={
            "backgroundColor": COLORS["white"],
            "border": f"1px solid {COLORS['border']}",
            "padding": "14px",
        },
        children=[
            section_header(
                "Реестр договоров",
                (
                    "Выберите договор через checkbox — "
                    "ниже откроется история"
                ),
            ),
            html.Div(style={"height": "10px"}),
            build_loans_grid(),
        ],
    )


# def build_selected_loan():
#     return html.Div(
#         style={
#             "backgroundColor": COLORS["white"],
#             "border": f"1px solid {COLORS['border']}",
#             "padding": "14px",
#         },
#         children=[
#             html.Div(
#                 style={
#                     "display": "flex",
#                     "justifyContent": "space-between",
#                     "gap": "12px",
#                     "alignItems": "flex-start",
#                     "marginBottom": "10px",
#                 },
#                 children=[
#                     html.Div(
#                         children=[
#                             dmc.Text(
#                                 id=SELECTED_LOAN_TITLE_ID,
#                                 children="Договор не выбран",
#                                 fw=700,
#                                 size="sm",
#                                 c=COLORS["text"],
#                             ),
#                             dmc.Text(
#                                 id=SELECTED_LOAN_META_ID,
#                                 children=(
#                                     "Выберите договор "
#                                     "в реестре выше"
#                                 ),
#                                 size="xs",
#                                 c=COLORS["muted"],
#                             ),
#                         ],
#                     ),
#                 ],
#             ),
#             dcc.Graph(
#                 id=SELECTED_LOAN_CHART_ID,
#                 figure=_empty_figure(),
#                 config=PLOTLY_CONFIG,
#             ),
#             html.Div(style={"height": "8px"}),
#             build_transactions_grid(),
#         ],
#     )


layout = dmc.MantineProvider(
    withCssVariables=True,
    withGlobalClasses=True,
    children=[
        dcc.Store(id=DATA_SIGNAL_ID),
        dcc.Store(id=FILTER_STORE_ID),
        dcc.Store(id=SELECTED_LOAN_STORE_ID),
        dcc.Download(id=DOWNLOAD_ID),
        build_alerts_modal(),
        build_daily_interest_modal(),

        html.Div(
            style=PAGE_STYLE,
            children=[
                build_header(),
                build_filter_panel(),
                html.Div(style={"height": "10px"}),

                dcc.Loading(
                    id=DASHBOARD_LOADING_ID,
                    type="cube",
                    children=html.Div(
                        children=[
                            html.Div(
                                id=DASHBOARD_LOADING_TRIGGER_ID,
                                style={"display": "none"},
                            ),
                            build_kpis(),
                            html.Div(style={"height": "10px"}),
                            build_overview(),
                            html.Div(style={"height": "10px"}),
                            build_registry(),
                            html.Div(style={"height": "10px"}),
                            build_selected_loan_panel(),
                  
                        ],
                    ),
                ),
            ],
        ),
    ],
)
