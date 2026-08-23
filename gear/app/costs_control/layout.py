# gear/app/costs_control/layout.py
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
    build_history_grid_section,
    build_main_grid_section,
)
from .ids import (
    BRAND_SUMMARY_CHART_ID,
    CV_DISTRIBUTION_CHART_ID,
    DATA_STORE_ID,
    DOWNLOAD_EXCEL_BTN_ID,
    DOWNLOAD_ID,
    FILTERED_DATA_STORE_ID,
    KPI_AVG_CV_ID,
    KPI_CHANGED_PRODUCTS_ID,
    KPI_CRITICAL_PRODUCTS_ID,
    KPI_MAX_DECREASE_ID,
    KPI_MAX_INCREASE_ID,
    KPI_TOTAL_PRODUCTS_ID,
    LAST_UPDATE_ID,
    MAIN_TABS_ID,
    MEDIAN_DEVIATION_CHART_ID,
    PRICE_HISTORY_CHART_ID,
    REFRESH_DATA_BTN_ID,
    SELECTED_PRODUCT_STORE_ID,
    TOP_CV_CHART_ID,
)
from .modal import (
    build_chart_product_modal_components,
)
from .styles import (
    CHART_GRID_STYLE,
    HEADER_STYLE,
    KPI_GRID_STYLE,
    PAGE_STYLE,
    PANEL_STYLE,
)

from .article_report import (
    build_article_report_button,
    build_article_report_components,
)


# ---------------------------------------------------------------------
# ID loader
# ---------------------------------------------------------------------

# Специально определяем ID здесь,
# чтобы не менять файл ids.py.
DASHBOARD_LOADING_ID = (
    "costs-control-dashboard-loading"
)

DASHBOARD_LOADING_TRIGGER_ID = (
    "costs-control-dashboard-loading-trigger"
)


# ---------------------------------------------------------------------
# Пустой график
# ---------------------------------------------------------------------


def _empty_figure():
    """
    Пустой график до первой загрузки данных.
    """

    return {
        "data": [],
        "layout": {
            "template": "plotly_white",
            "paper_bgcolor": "#FFFFFF",
            "plot_bgcolor": "#FFFFFF",
            "margin": {
                "l": 40,
                "r": 20,
                "t": 30,
                "b": 40,
            },
            "xaxis": {
                "visible": False,
            },
            "yaxis": {
                "visible": False,
            },
            "annotations": [
                {
                    "text": "Данные загружаются…",
                    "x": 0.5,
                    "y": 0.5,
                    "xref": "paper",
                    "yref": "paper",
                    "showarrow": False,
                    "font": {
                        "family": (
                            "Inter, Arial, sans-serif"
                        ),
                        "size": 13,
                        "color": COLORS.get(
                            "muted",
                            "#6B7280",
                        ),
                    },
                },
            ],
        },
    }


# ---------------------------------------------------------------------
# Заголовок вкладки
# ---------------------------------------------------------------------


def _tab_label(
    icon: str,
    label: str,
):
    """
    Заголовок вкладки с иконкой.
    """

    return dmc.Group(
        gap=7,
        wrap="nowrap",
        children=[
            DashIconify(
                icon=icon,
                width=16,
                height=16,
            ),
            dmc.Text(
                label,
                size="xs",
                fw=600,
            ),
        ],
    )


# ---------------------------------------------------------------------
# Шапка
# ---------------------------------------------------------------------


def build_header():
    return html.Div(
        style=HEADER_STYLE,
        children=[
            html.Div(
                style={
                    "display": "flex",
                    "alignItems": "center",
                    "justifyContent": (
                        "space-between"
                    ),
                    "gap": "18px",
                    "flexWrap": "wrap",
                },
                children=[
                    # -------------------------------------------------
                    # Название приложения
                    # -------------------------------------------------

                    html.Div(
                        style={
                            "display": "flex",
                            "alignItems": "center",
                            "gap": "12px",
                            "minWidth": 0,
                        },
                        children=[
                            html.Div(
                                style={
                                    "width": "38px",
                                    "height": "38px",
                                    "display": "flex",
                                    "alignItems": "center",
                                    "justifyContent": (
                                        "center"
                                    ),
                                    "flex": "0 0 auto",
                                    "backgroundColor": (
                                        COLORS.get(
                                            "light_green",
                                            "#E7F1ED",
                                        )
                                    ),
                                    "border": (
                                        "1px solid "
                                        + COLORS.get(
                                            "border",
                                            "#D9DEE2",
                                        )
                                    ),
                                },
                                children=DashIconify(
                                    icon=(
                                        "solar:"
                                        "chart-square-linear"
                                    ),
                                    width=21,
                                    height=21,
                                    color=COLORS.get(
                                        "green",
                                        "#2F6656",
                                    ),
                                ),
                            ),

                            html.Div(
                                style={
                                    "minWidth": 0,
                                },
                                children=[
                                    html.H1(
                                        APP_TITLE,
                                        style={
                                            "margin": 0,
                                            "fontSize": (
                                                "21px"
                                            ),
                                            "fontWeight": 700,
                                            "lineHeight": (
                                                "26px"
                                            ),
                                            "color": (
                                                COLORS.get(
                                                    "text",
                                                    "#111827",
                                                )
                                            ),
                                        },
                                    ),

                                    html.Div(
                                        (
                                            "Контроль изменения "
                                            "бухгалтерской и "
                                            "управленческой "
                                            "закупочной цены"
                                        ),
                                        style={
                                            "marginTop": "3px",
                                            "fontSize": "12px",
                                            "lineHeight": "17px",
                                            "color": COLORS.get(
                                                "muted",
                                                "#6B7280",
                                            ),
                                        },
                                    ),
                                ],
                            ),
                        ],
                    ),

                    # -------------------------------------------------
                    # Действия
                    # -------------------------------------------------

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
                                    "backgroundColor": (
                                        "#FFFFFF"
                                    ),
                                    "border": (
                                        "1px solid "
                                        + COLORS.get(
                                            "border",
                                            "#D9DEE2",
                                        )
                                    ),
                                },
                                children=[
                                    DashIconify(
                                        icon=(
                                            "solar:"
                                            "clock-circle-linear"
                                        ),
                                        width=15,
                                        height=15,
                                        color=COLORS.get(
                                            "muted",
                                            "#6B7280",
                                        ),
                                    ),

                                    html.Span(
                                        "Обновление:",
                                        style={
                                            "fontSize": "11px",
                                            "color": COLORS.get(
                                                "muted",
                                                "#6B7280",
                                            ),
                                        },
                                    ),

                                    html.Span(
                                        id=LAST_UPDATE_ID,
                                        children="—",
                                        style={
                                            "fontSize": "11px",
                                            "fontWeight": 600,
                                            "color": COLORS.get(
                                                "text",
                                                "#111827",
                                            ),
                                        },
                                    ),
                                ],
                            ),

                            action_button(
                                component_id=(
                                    REFRESH_DATA_BTN_ID
                                ),
                                label="Обновить",
                                icon=(
                                    "solar:"
                                    "refresh-linear"
                                ),
                                color="teal",
                            ),
                
                            build_article_report_button(),

                            action_button(
                                component_id=(
                                    DOWNLOAD_EXCEL_BTN_ID
                                ),
                                label="Excel",
                                icon=(
                                    "solar:"
                                    "file-download-linear"
                                ),
                                color="green",
                            ),
                        ],
                    ),
                ],
            ),
        ],
    )


# ---------------------------------------------------------------------
# KPI
# ---------------------------------------------------------------------


def build_kpi_section():
    return html.Div(
        children=[
            section_header(
                "Ключевые показатели",
                (
                    "Показатели пересчитываются "
                    "после применения фильтров"
                ),
            ),

            html.Div(
                style={
                    **KPI_GRID_STYLE,
                    "marginTop": "12px",
                },
                children=[
                    kpi_card(
                        title="Товаров",
                        value_id=(
                            KPI_TOTAL_PRODUCTS_ID
                        ),
                        subtitle="NM ID в выборке",
                        icon="solar:box-linear",
                        accent=COLORS["green"],
                    ),

                    kpi_card(
                        title="Менялась цена",
                        value_id=(
                            KPI_CHANGED_PRODUCTS_ID
                        ),
                        subtitle=(
                            "Более одной "
                            "закупочной цены"
                        ),
                        icon=(
                            "solar:"
                            "refresh-circle-linear"
                        ),
                        accent=COLORS["blue"],
                    ),

                    kpi_card(
                        title="Критические",
                        value_id=(
                            KPI_CRITICAL_PRODUCTS_ID
                        ),
                        subtitle="CV 75% и выше",
                        icon=(
                            "solar:"
                            "danger-triangle-linear"
                        ),
                        accent=COLORS["red"],
                    ),

                    kpi_card(
                        title="Средний CV",
                        value_id=(
                            KPI_AVG_CV_ID
                        ),
                        subtitle=(
                            "По отфильтрованным "
                            "товарам"
                        ),
                        icon=(
                            "solar:"
                            "chart-square-linear"
                        ),
                        accent=COLORS["orange"],
                    ),

                    kpi_card(
                        title="Макс. рост",
                        value_id=(
                            KPI_MAX_INCREASE_ID
                        ),
                        subtitle=(
                            "Относительно "
                            "медианной цены"
                        ),
                        icon=(
                            "solar:"
                            "arrow-up-linear"
                        ),
                        accent=COLORS["red"],
                    ),

                    kpi_card(
                        title="Макс. снижение",
                        value_id=(
                            KPI_MAX_DECREASE_ID
                        ),
                        subtitle=(
                            "Относительно "
                            "медианной цены"
                        ),
                        icon=(
                            "solar:"
                            "arrow-down-linear"
                        ),
                        accent=COLORS["green"],
                    ),
                ],
            ),
        ],
    )


# ---------------------------------------------------------------------
# Вкладка «Обзор»
# ---------------------------------------------------------------------


def build_overview_tab():
    return html.Div(
        style={
            "paddingTop": "16px",
        },
        children=[
            html.Div(
                style=CHART_GRID_STYLE,
                children=[
                    chart_panel(
                        title=(
                            "Распределение по "
                            "коэффициенту вариации"
                        ),
                        subtitle=(
                            "Количество товаров "
                            "в каждом диапазоне CV"
                        ),
                        graph=dcc.Graph(
                            id=(
                                CV_DISTRIBUTION_CHART_ID
                            ),
                            figure=_empty_figure(),
                            config={
                                **PLOTLY_CONFIG,
                                "toImageButtonOptions": {
                                    "format": "png",
                                    "filename": (
                                        "распределение_"
                                        "по_cv"
                                    ),
                                    "height": 1200,
                                    "width": 1800,
                                    "scale": 3,
                                },
                            },
                            style={
                                "height": "430px",
                            },
                        ),
                    ),

                    chart_panel(
                        title="Анализ по брендам",
                        subtitle=(
                            "Средний CV, количество "
                            "товаров и критические "
                            "позиции"
                        ),
                        graph=dcc.Graph(
                            id=(
                                BRAND_SUMMARY_CHART_ID
                            ),
                            figure=_empty_figure(),
                            config={
                                **PLOTLY_CONFIG,
                                "toImageButtonOptions": {
                                    "format": "png",
                                    "filename": (
                                        "анализ_"
                                        "по_брендам"
                                    ),
                                    "height": 1200,
                                    "width": 1800,
                                    "scale": 3,
                                },
                            },
                            style={
                                "height": "430px",
                            },
                        ),
                    ),
                ],
            ),

            html.Div(
                style={
                    "marginTop": "14px",
                },
                children=[
                    chart_panel(
                        title=(
                            "Товары с "
                            "максимальным CV"
                        ),
                        subtitle=(
                            "Щёлкните по столбцу, "
                            "чтобы открыть "
                            "детализацию товара"
                        ),
                        graph=dcc.Graph(
                            id=TOP_CV_CHART_ID,
                            figure=_empty_figure(),
                            config={
                                **PLOTLY_CONFIG,
                                "toImageButtonOptions": {
                                    "format": "png",
                                    "filename": (
                                        "товары_с_"
                                        "максимальным_cv"
                                    ),
                                    "height": 1600,
                                    "width": 2400,
                                    "scale": 3,
                                },
                            },
                            style={
                                "height": "720px",
                            },
                        ),
                    ),
                ],
            ),

            html.Div(
                style={
                    "marginTop": "14px",
                },
                children=[
                    chart_panel(
                        title=(
                            "Отклонение от "
                            "медианной цены"
                        ),
                        subtitle=(
                            "Наведите курсор, "
                            "чтобы увидеть NM ID"
                        ),
                        graph=dcc.Graph(
                            id=(
                                MEDIAN_DEVIATION_CHART_ID
                            ),
                            figure=_empty_figure(),
                            config={
                                **PLOTLY_CONFIG,
                                "toImageButtonOptions": {
                                    "format": "png",
                                    "filename": (
                                        "отклонение_"
                                        "от_медианы"
                                    ),
                                    "height": 1600,
                                    "width": 2400,
                                    "scale": 3,
                                },
                            },
                            style={
                                "height": "720px",
                            },
                        ),
                    ),
                ],
            ),
        ],
    )


# ---------------------------------------------------------------------
# Вкладка «Товары»
# ---------------------------------------------------------------------


def build_products_tab():
    return html.Div(
        style={
            "paddingTop": "16px",
        },
        children=[
            html.Div(
                style=PANEL_STYLE,
                children=[
                    dmc.Group(
                        justify="space-between",
                        align="flex-start",
                        mb=12,
                        children=[
                            section_header(
                                "Товары",
                                (
                                    "Выберите товар "
                                    "через чекбокс, "
                                    "чтобы построить "
                                    "историю цены"
                                ),
                            ),

                            dmc.Badge(
                                "Выберите товар",
                                variant="light",
                                color="gray",
                                radius=0,
                                size="sm",
                                leftSection=DashIconify(
                                    icon=(
                                        "solar:"
                                        "check-square-linear"
                                    ),
                                    width=13,
                                ),
                            ),
                        ],
                    ),

                    build_main_grid_section(),
                ],
            ),
        ],
    )


# ---------------------------------------------------------------------
# Вкладка «История цен»
# ---------------------------------------------------------------------


def build_history_tab():
    return html.Div(
        style={
            "paddingTop": "16px",
        },
        children=[
            chart_panel(
                title=(
                    "История закупочной цены"
                ),
                subtitle=(
                    "Динамика бухгалтерской "
                    "и управленческой "
                    "себестоимости выбранного "
                    "товара"
                ),
                graph=dcc.Graph(
                    id=PRICE_HISTORY_CHART_ID,
                    figure=_empty_figure(),
                    config=PLOTLY_CONFIG,
                    style={
                        "height": "540px",
                    },
                ),
            ),

            html.Div(
                style={
                    **PANEL_STYLE,
                    "marginTop": "14px",
                },
                children=[
                    section_header(
                        "Документы и поставщики",
                        (
                            "История цены по УПД "
                            "для выбранного товара"
                        ),
                    ),

                    html.Div(
                        style={
                            "marginTop": "12px",
                        },
                        children=(
                            build_history_grid_section()
                        ),
                    ),
                ],
            ),
        ],
    )


# ---------------------------------------------------------------------
# Главные вкладки
# ---------------------------------------------------------------------


def build_main_tabs():
    return dmc.Tabs(
        id=MAIN_TABS_ID,
        value="overview",
        keepMounted=True,
        variant="outline",
        radius=0,
        children=[
            dmc.TabsList(
                children=[
                    dmc.TabsTab(
                        _tab_label(
                            icon=(
                                "solar:"
                                "chart-2-linear"
                            ),
                            label="Обзор",
                        ),
                        value="overview",
                    ),

                    dmc.TabsTab(
                        _tab_label(
                            icon=(
                                "solar:"
                                "box-linear"
                            ),
                            label="Товары",
                        ),
                        value="products",
                    ),

                    dmc.TabsTab(
                        _tab_label(
                            icon=(
                                "solar:"
                                "history-linear"
                            ),
                            label="История цен",
                        ),
                        value="history",
                    ),
                ],
            ),

            dmc.TabsPanel(
                build_overview_tab(),
                value="overview",
            ),

            dmc.TabsPanel(
                build_products_tab(),
                value="products",
            ),

            dmc.TabsPanel(
                build_history_tab(),
                value="history",
            ),
        ],
    )


# ---------------------------------------------------------------------
# Служебные компоненты
# ---------------------------------------------------------------------


def build_service_components():
    """
    Служебные компоненты приложения.
    """

    return html.Div(
        children=[
            dcc.Store(
                id=DATA_STORE_ID,
                storage_type="memory",
            ),

            dcc.Store(
                id=FILTERED_DATA_STORE_ID,
                storage_type="memory",
            ),

            dcc.Store(
                id=SELECTED_PRODUCT_STORE_ID,
                storage_type="memory",
            ),

            dcc.Download(
                id=DOWNLOAD_ID,
            ),
            build_chart_product_modal_components(),
            build_article_report_components(),
        ],
    )


# ---------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------


def build_dashboard_loader():
    """
    Полноэкранный loader.

    Loader следит только за скрытым компонентом
    DASHBOARD_LOADING_TRIGGER_ID.

    Этот компонент обновляется главным callback
    после окончания пересчёта dashboard.
    """

    return dcc.Loading(
        id=DASHBOARD_LOADING_ID,
        type="cube",
        color=COLORS.get(
            "green",
            "#2F6656",
        ),
        fullscreen=True,
        delay_show=150,
        delay_hide=150,
        overlay_style={
            "visibility": "visible",
            "backgroundColor": (
                "rgba(255, 255, 255, 0.78)"
            ),
            "backdropFilter": "blur(1px)",
        },
        children=html.Div(
            id=DASHBOARD_LOADING_TRIGGER_ID,
            style={
                "display": "none",
            },
        ),
    )


# ---------------------------------------------------------------------
# Содержимое страницы
# ---------------------------------------------------------------------


def build_page_content():
    """
    Основное содержимое страницы.
    """

    return html.Div(
        style=PAGE_STYLE,
        children=[
            build_header(),

            html.Div(
                style={
                    "marginTop": "14px",
                },
                children=build_filter_panel(),
            ),

            html.Div(
                style={
                    "marginTop": "18px",
                },
                children=build_kpi_section(),
            ),

            html.Div(
                style={
                    "marginTop": "18px",
                },
                children=build_main_tabs(),
            ),

            html.Div(
                style={
                    "height": "24px",
                },
            ),
        ],
    )


# ---------------------------------------------------------------------
# Общий layout
# ---------------------------------------------------------------------


def build_layout():
    """
    Основной layout приложения
    контроля закупочных цен.
    """

    return dmc.MantineProvider(
        theme={
            "primaryColor": "teal",
            "fontFamily": (
                "Inter, Arial, sans-serif"
            ),
            "headings": {
                "fontFamily": (
                    "Inter, Arial, sans-serif"
                ),
            },
            "defaultRadius": 0,
            "components": {
                "Button": {
                    "defaultProps": {
                        "radius": 0,
                    },
                },
                "Input": {
                    "defaultProps": {
                        "radius": 0,
                    },
                },
                "Paper": {
                    "defaultProps": {
                        "radius": 0,
                    },
                },
                "Card": {
                    "defaultProps": {
                        "radius": 0,
                    },
                },
            },
        },
        children=[
            build_service_components(),

            # Полноэкранный кубик.
            build_dashboard_loader(),

            # Содержимое приложения.
            build_page_content(),
        ],
    )


layout = build_layout()