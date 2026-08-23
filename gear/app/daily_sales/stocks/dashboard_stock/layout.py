# gear/app/daily_sales/stocks/dashboard_stock/layout.py
"""Главный layout dashboard остатков."""

from datetime import date

import pandas as pd
import dash_mantine_components as dmc

from dash import dcc, html
from dash_iconify import DashIconify

from ..dashboard_data import (
    get_effective_stock_date,
    get_stock_dashboard_summary,
    get_stock_regions,
    get_stock_warehouses,
)
from ..dashboard_charts import (
    build_warehouses_map,
)

from .components import metric_card
from .distribution_data import (
    get_dashboard_distributions,
)
from .distribution_tabs import (
    build_stock_distribution_tabs,
)
from .grids import warehouses_grid
from .map_modal import map_info_modal
from .warehouse_modal import warehouse_action_modal
from .transfer_modal import transfer_modal
from .incidents_panel import build_incidents_panel
from .ids import (
    STOCK_MAP_ID,
    STOCK_CONTEXT_ID,
    STOCK_WAREHOUSE_SELECT_ID,
    STOCK_SELECTED_WAREHOUSE_STORE_ID,
    STOCK_PRODUCTS_COUNT_ID,
    STOCK_WAREHOUSES_DOWNLOAD_BTN_ID,
    STOCK_WAREHOUSES_DOWNLOAD_ID,
    STOCK_WAREHOUSE_DOWNLOAD_ID,
    STOCK_TRANSFER_DOWNLOAD_ID,
)


class StocksDashboard:
    def layout(
        self,
        report_date,
        cat_list=None,
        brand_list=None,
        gender_list=None,
    ):
        requested_date = pd.to_datetime(
            report_date,
            errors="coerce",
        )

        if pd.isna(requested_date):
            requested_date = pd.Timestamp(
                date.today()
            )

        requested_date = requested_date.strftime(
            "%Y-%m-%d"
        )

        effective_date = get_effective_stock_date(
            requested_date
        )

        if effective_date is None:
            effective_date = requested_date

        effective_date = pd.to_datetime(
            effective_date
        ).strftime("%Y-%m-%d")

        summary = get_stock_dashboard_summary(
            effective_date
        )

        regions = get_stock_regions(
            effective_date
        )

        warehouses = get_stock_warehouses(
            effective_date
        )

        brands, categories = (
            get_dashboard_distributions(
                report_date=effective_date,
                brand_list=brand_list,
                cat_list=cat_list,
                gender_list=gender_list,
            )
        )

        requested_label = pd.to_datetime(
            requested_date
        ).strftime("%d.%m.%Y")

        effective_label = pd.to_datetime(
            effective_date
        ).strftime("%d.%m.%Y")

        if effective_date != requested_date:
            subtitle = (
                f"Остатки на {effective_label}"
                f" · выбрана дата {requested_label}"
                f" · использованы последние доступные данные"
            )
        else:
            subtitle = (
                f"Интерактивный анализ распределения "
                f"на {effective_label}"
            )

        warehouse_options = [
            {
                "label": row["warehouse"],
                "value": row["warehouse"],
            }
            for _, row
            in warehouses.iterrows()
        ]

        return dcc.Loading(
            type="dot",
            children=dmc.Stack(
                gap="lg",
                children=[
                    dcc.Store(
                        id=STOCK_CONTEXT_ID,
                        data={
                            "report_date": effective_date,
                            "requested_date": requested_date,
                            "cat_list": cat_list or [],
                            "brand_list": brand_list or [],
                            "gender_list": gender_list or [],
                            "warehouses": (
                                warehouses.to_dict(
                                    "records"
                                )
                            ),
                        },
                    ),

                    dcc.Store(
                        id=STOCK_SELECTED_WAREHOUSE_STORE_ID,
                        data=None,
                    ),

                    dcc.Download(
                        id=STOCK_TRANSFER_DOWNLOAD_ID
                    ),
                    dcc.Download(
                        id=STOCK_WAREHOUSES_DOWNLOAD_ID
                    ),
                    dcc.Download(
                        id=STOCK_WAREHOUSE_DOWNLOAD_ID
                    ),

                    dmc.Group(
                        justify="space-between",
                        align="flex-end",
                        children=[
                            html.Div(
                                [
                                    dmc.Title(
                                        "Остатки товаров",
                                        order=3,
                                        fw=700,
                                    ),
                                    dmc.Text(
                                        subtitle,
                                        size="sm",
                                        c="dimmed",
                                        mt=2,
                                    ),
                                ]
                            ),
                            dmc.Select(
                                id=STOCK_WAREHOUSE_SELECT_ID,
                                label="Быстро открыть рабочую карточку",
                                placeholder="Выберите склад",
                                data=warehouse_options,
                                searchable=True,
                                clearable=True,
                                radius=0,
                                w=360,
                            ),
                        ],
                    ),

                    dmc.SimpleGrid(
                        cols={
                            "base": 1,
                            "sm": 2,
                            "lg": 5,
                        },
                        spacing="sm",
                        children=[
                            metric_card(
                                "Физически на складах",
                                summary["on_hand"],
                            ),
                            metric_card(
                                "В пути",
                                summary["in_transit"],
                            ),
                            metric_card(
                                "Всего товара",
                                summary["total_qty"],
                            ),
                            metric_card(
                                "Складов",
                                summary["warehouses"],
                                "",
                            ),
                            metric_card(
                                "Товаров",
                                summary["products"],
                                "NM ID",
                            ),
                        ],
                    ),

                    build_incidents_panel(),

                    dmc.Paper(
                        radius=0,
                        p="md",
                        style={
                            "border": "1px solid #D6DFDB",
                        },
                        children=[
                            dmc.Group(
                                justify="space-between",
                                align="center",
                                mb="xs",
                                children=[
                                    html.Div(
                                        [
                                            dmc.Text(
                                                "Карта складов",
                                                fw=700,
                                            ),
                                            dmc.Text(
                                                (
                                                    "Размер точки отражает общий остаток. "
                                                    "Нажмите на точку для "
                                                    "аналитики выбранного склада."
                                                ),
                                                size="xs",
                                                c="dimmed",
                                            ),
                                        ]
                                    ),
                                    dmc.Text(
                                        "Карта · обзор склада",
                                        size="xs",
                                        c="dimmed",
                                    ),
                                ],
                            ),
                            dcc.Graph(
                                id=STOCK_MAP_ID,
                                figure=build_warehouses_map(
                                    warehouses
                                ),
                                config={
                                    "displayModeBar": True,
                                    "displaylogo": False,
                                    "scrollZoom": False,
                                    "doubleClick": "reset",
                                    "responsive": True,
                                    "modeBarButtonsToRemove": [
                                        "lasso2d",
                                        "select2d",
                                    ],
                                },
                                style={
                                    "height": "500px",
                                    "width": "100%",
                                },
                            ),
                        ],
                    ),

                    # Отдельный обслуживаемый модуль вкладок.
                    build_stock_distribution_tabs(
                        regions=regions,
                        brands=brands,
                        categories=categories,
                    ),

                    dmc.Paper(
                        radius=0,
                        p="md",
                        style={
                            "border": "1px solid #D6DFDB",
                        },
                        children=[
                            dmc.Group(
                                justify="space-between",
                                align="center",
                                mb="sm",
                                children=[
                                    html.Div(
                                        [
                                            dmc.Text(
                                                "Склады",
                                                fw=700,
                                            ),
                                            dmc.Text(
                                                (
                                                    "Checkbox открывает рабочую карточку "
                                                    "склада. Только в ней доступны Excel "
                                                    "и план перемещения."
                                                ),
                                                size="xs",
                                                c="dimmed",
                                            ),
                                        ]
                                    ),
                                    dmc.Group(
                                        gap="sm",
                                        children=[
                                            dmc.Text(
                                                id=STOCK_PRODUCTS_COUNT_ID,
                                                children=(
                                                    f"Показано складов: "
                                                    f"{len(warehouses)}"
                                                ),
                                                size="sm",
                                                c="dimmed",
                                            ),
                                            dmc.Button(
                                                "Скачать список складов",
                                                id=(
                                                    STOCK_WAREHOUSES_DOWNLOAD_BTN_ID
                                                ),
                                                leftSection=DashIconify(
                                                    icon=(
                                                        "material-symbols:"
                                                        "download-rounded"
                                                    ),
                                                    width=18,
                                                ),
                                                variant="outline",
                                                color="green",
                                                radius=0,
                                                size="sm",
                                            ),
                                        ],
                                    ),
                                ],
                            ),
                            warehouses_grid(
                                warehouses
                            ),
                        ],
                    ),

                    # Отдельные модалки.
                    map_info_modal(),
                    warehouse_action_modal(),
                    transfer_modal(),
                ],
            ),
        )