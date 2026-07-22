# gear/app/daily_sales/stocks/dashboard.py
from __future__ import annotations

from datetime import date

import pandas as pd
import dash_ag_grid as dag
import dash_mantine_components as dmc

from dash import (
    dcc,
    html,
    Input,
    Output,
    State,
    no_update,
)

from .dashboard_data import (
    get_effective_stock_date,
    get_stock_dashboard_summary,
    get_stock_regions,
    get_stock_warehouses,
    get_warehouse_options,
    get_warehouse_products,
)

from .dashboard_charts import (
    build_warehouses_map,
    build_regions_chart,
)

from .transfer_excel import (
    build_transfer_plan_excel,
    build_warehouses_excel,
)


# =============================================================================
# IDs
# =============================================================================

STOCK_MAP_ID = "stock-dashboard-map"
STOCK_REGION_CHART_ID = "stock-dashboard-region-chart"

STOCK_WAREHOUSES_GRID_ID = "stock-dashboard-warehouses-grid"
STOCK_PRODUCTS_GRID_ID = "stock-dashboard-products-grid"
STOCK_TRANSFER_GRID_ID = "stock-dashboard-transfer-grid"

STOCK_CONTEXT_ID = "stock-dashboard-context"

STOCK_WAREHOUSE_SELECT_ID = "stock-dashboard-warehouse-select"

# Кнопка возврата всей таблицы складов
STOCK_SHOW_ALL_WAREHOUSES_ID = "stock-dashboard-show-all-warehouses"

# Excel таблицы складов
STOCK_WAREHOUSES_DOWNLOAD_BTN_ID = "stock-dashboard-warehouses-download-btn"
STOCK_WAREHOUSES_DOWNLOAD_ID = "stock-dashboard-warehouses-download"

# Детализация выбранного склада через chip
STOCK_SELECTED_WAREHOUSE_CHIPS_ID = "stock-dashboard-selected-warehouse-chips"
STOCK_WAREHOUSES_CONTAINER_ID = "stock-dashboard-warehouses-container"
STOCK_WAREHOUSE_DETAILS_CONTAINER_ID = "stock-dashboard-warehouse-details-container"

# Текущий склад-источник для плана перемещения
STOCK_SELECTED_WAREHOUSE_STORE_ID = "stock-dashboard-selected-warehouse-store"

STOCK_TRANSFER_BTN_ID = "stock-dashboard-transfer-btn"

STOCK_TRANSFER_MODAL_ID = "stock-dashboard-transfer-modal"
STOCK_TRANSFER_GRID_CONTAINER_ID = "stock-transfer-grid-container"
STOCK_TRANSFER_VALIDATION_ID = "stock-transfer-validation"

STOCK_TRANSFER_BULK_WAREHOUSE_ID = "stock-transfer-bulk-warehouse"
STOCK_TRANSFER_ALL_QTY_BTN_ID = "stock-transfer-all-qty-btn"

STOCK_TRANSFER_DOWNLOAD_BTN_ID = "stock-dashboard-transfer-download-btn"
STOCK_TRANSFER_DOWNLOAD_ID = "stock-dashboard-transfer-download"

STOCK_PRODUCTS_COUNT_ID = "stock-dashboard-products-count"


# =============================================================================
# Вспомогательные функции
# =============================================================================

def fmt(value):
    try:
        return f"{float(value or 0):,.0f}".replace(",", " ")
    except (TypeError, ValueError):
        return "0"


def _safe_float(value) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def warehouse_chip_maker(warehouse_name):
    """
    Chip детализации выбранного склада.
    """
    warehouse_name = str(
        warehouse_name
        or ""
    ).strip()

    return dmc.Chip(
        f"Детализация · {warehouse_name}",
        value=warehouse_name,
        variant="light",
        color="green",
        size="xs",
        radius=0,
        checked=False,
    )


# =============================================================================
# KPI
# =============================================================================

def metric_card(
    label,
    value,
    suffix="шт",
):
    return dmc.Paper(
        radius=0,
        p="md",
        style={
            "border": "1px solid #D6DFDB",
            "background": "#FFFFFF",
            "minHeight": "94px",
        },
        children=[
            dmc.Text(
                label,
                size="xs",
                c="dimmed",
                fw=500,
            ),

            dmc.Group(
                gap=6,
                align="baseline",
                mt=6,
                children=[
                    dmc.Text(
                        fmt(value),
                        size="xl",
                        fw=700,
                        c="#18352F",
                    ),

                    dmc.Text(
                        suffix,
                        size="sm",
                        c="dimmed",
                    ),
                ],
            ),
        ],
    )


# =============================================================================
# ТАБЛИЦА СКЛАДОВ
# =============================================================================
def warehouses_grid(
    df: pd.DataFrame,
):
    if df is None:
        df = pd.DataFrame()

    return dag.AgGrid(
        id=STOCK_WAREHOUSES_GRID_ID,

        rowData=df.to_dict("records"),
        getRowId="params.data.warehouse",

        columnDefs=[
            {
                "headerName": "",
                "width": 48,
                "minWidth": 48,
                "maxWidth": 48,
                "pinned": "left",

                # Открываем склад только через checkbox.
                "checkboxSelection": True,

                "sortable": False,
                "filter": False,
                "resizable": False,
                "suppressHeaderMenuButton": True,
            },

            {
                "headerName": "Регион",
                "field": "region",
                "flex": 1.2,
                "minWidth": 220,
            },

            {
                "headerName": "Склад",
                "field": "warehouse",
                "flex": 1.5,
                "minWidth": 250,
                "cellStyle": {
                    "fontWeight": "600",
                },
            },

            {
                "headerName": "NM ID",
                "field": "products",
                "type": "numericColumn",
                "width": 110,
                "valueFormatter": {
                    "function": (
                        "params.value == null ? '' : "
                        "d3.format(',.0f')(params.value)"
                    )
                },
            },

            {
                "headerName": "На складе",
                "field": "on_hand",
                "type": "numericColumn",
                "width": 135,
                "valueFormatter": {
                    "function": (
                        "params.value == null ? '' : "
                        "d3.format(',.0f')(params.value)"
                    )
                },
            },

            {
                "headerName": "В пути",
                "field": "in_transit",
                "type": "numericColumn",
                "width": 120,
                "valueFormatter": {
                    "function": (
                        "params.value == null ? '' : "
                        "d3.format(',.0f')(params.value)"
                    )
                },
            },

            {
                "headerName": "Итого",
                "field": "total_qty",
                "type": "numericColumn",
                "width": 135,
                "valueFormatter": {
                    "function": (
                        "params.value == null ? '' : "
                        "d3.format(',.0f')(params.value)"
                    )
                },
            },
        ],

        dangerously_allow_code=True,

        defaultColDef={
            "sortable": True,
            "filter": True,
            "resizable": True,
            "floatingFilter": False,
        },

        dashGridOptions={
            "pagination": True,
            "paginationPageSize": 20,

            # Один склад за раз.
            # Выбор делаем только через checkbox.
            "rowSelection": {
                "mode": "singleRow",
                "enableClickSelection": False,
                "checkboxes": False,
                "headerCheckbox": False,
            },

            "animateRows": False,
        },

        style={
            "height": "500px",
            "width": "100%",
        },

        className="ag-theme-quartz",
    )

# =============================================================================
# ТОВАРЫ СКЛАДА
# =============================================================================

def products_grid(
    df: pd.DataFrame,
):
    if df is None:
        df = pd.DataFrame()

    return dag.AgGrid(
        id=STOCK_PRODUCTS_GRID_ID,

        rowData=df.to_dict("records"),

        columnDefs=[
            {
                "headerName": "",
                "width": 46,
                "pinned": "left",

                "checkboxSelection": True,
                "headerCheckboxSelection": True,

                "sortable": False,
                "filter": False,
                "resizable": False,
            },

            {
                "headerName": "Бренд",
                "field": "Бренд",
                "width": 150,
            },

            {
                "headerName": "Категория",
                "field": "Категория",
                "width": 180,
            },

            {
                "headerName": "Артикул",
                "field": "Артикул",
                "width": 145,
            },

            {
                "headerName": "Наименование",
                "field": "Наименование",
                "minWidth": 340,
                "flex": 1,
            },

            {
                "headerName": "Размер",
                "field": "Размер",
                "width": 95,
            },

            {
                "headerName": "Остаток",
                "field": "Остаток",
                "type": "numericColumn",
                "width": 115,

                "valueFormatter": {
                    "function": (
                        "params.value == null ? '' : "
                        "d3.format(',.0f')(params.value)"
                    )
                },
            },

            {
                "headerName": "В пути от клиента",
                "field": "В пути от клиента",
                "type": "numericColumn",
                "width": 155,

                "valueFormatter": {
                    "function": (
                        "params.value == null ? '' : "
                        "d3.format(',.0f')(params.value)"
                    )
                },
            },

            {
                "headerName": "В пути к клиенту",
                "field": "В пути к клиенту",
                "type": "numericColumn",
                "width": 155,

                "valueFormatter": {
                    "function": (
                        "params.value == null ? '' : "
                        "d3.format(',.0f')(params.value)"
                    )
                },
            },

            {
                "headerName": "Итого",
                "field": "Итого",
                "type": "numericColumn",
                "width": 110,

                "valueFormatter": {
                    "function": (
                        "params.value == null ? '' : "
                        "d3.format(',.0f')(params.value)"
                    )
                },
            },

            {
                "headerName": "Продажи 7д",
                "field": "Продажи 7 дней",
                "type": "numericColumn",
                "width": 125,

                "valueFormatter": {
                    "function": (
                        "params.value == null ? '' : "
                        "d3.format(',.0f')(params.value)"
                    )
                },
            },

            {
                "headerName": "Оборачиваемость, дн.",
                "field": "Оборачиваемость",
                "type": "numericColumn",
                "width": 170,

                "valueFormatter": {
                    "function": (
                        "params.value == null ? '' : "
                        "d3.format(',.1f')(params.value)"
                    )
                },
            },

            {
                "headerName": "NM ID",
                "field": "NM ID",
                "width": 135,
            },

            {
                "headerName": "Chrt ID",
                "field": "Chrt ID",
                "width": 135,
            },
        ],

        defaultColDef={
            "sortable": True,
            "filter": True,
            "resizable": True,
            "floatingFilter": False,
        },

        dashGridOptions={
            "pagination": True,
            "paginationPageSize": 50,

            "rowSelection": "multiple",

            # Checkbox выбирает.
            # Обычный клик по строке — нет.
            "suppressRowClickSelection": True,

            "animateRows": False,
        },

        style={
            "height": "620px",
            "width": "100%",
        },

        className="ag-theme-quartz",
    )


# =============================================================================
# ПЛАН ПЕРЕМЕЩЕНИЯ
# =============================================================================

def transfer_grid(
    rows,
    warehouses,
):
    return dag.AgGrid(
        id=STOCK_TRANSFER_GRID_ID,

        rowData=rows,

        columnDefs=[
            {
                "headerName": "Откуда",
                "field": "Откуда",
                "width": 220,
            },

            {
                "headerName": "Куда",
                "field": "Куда",
                "width": 220,

                "editable": True,

                "cellEditor": "agSelectCellEditor",

                "cellEditorParams": {
                    "values": warehouses,
                },

                "cellStyle": {
                    "backgroundColor": "#F4F8F6",
                    "fontWeight": "600",
                },
            },

            {
                "headerName": "Бренд",
                "field": "Бренд",
                "width": 140,
            },

            {
                "headerName": "Категория",
                "field": "Категория",
                "width": 160,
            },

            {
                "headerName": "Артикул",
                "field": "Артикул",
                "width": 140,
            },

            {
                "headerName": "Наименование",
                "field": "Наименование",
                "minWidth": 300,
                "flex": 1,
            },

            {
                "headerName": "Размер",
                "field": "Размер",
                "width": 90,
            },

            {
                "headerName": "Доступно",
                "field": "Доступно",
                "type": "numericColumn",
                "width": 110,

                "valueFormatter": {
                    "function": (
                        "params.value == null ? '' : "
                        "d3.format(',.0f')(params.value)"
                    )
                },
            },

            {
                "headerName": "Переместить",
                "field": "Переместить",
                "type": "numericColumn",
                "width": 135,

                "editable": True,
                "cellDataType": "number",

                "cellStyle": {
                    "backgroundColor": "#FFF9E8",
                    "fontWeight": "600",
                },

                "valueFormatter": {
                    "function": (
                        "params.value == null ? '' : "
                        "d3.format(',.0f')(params.value)"
                    )
                },
            },

            {
                "headerName": "NM ID",
                "field": "NM ID",
                "width": 130,
            },

            {
                "headerName": "Chrt ID",
                "field": "Chrt ID",
                "width": 130,
            },
        ],

        defaultColDef={
            "sortable": True,
            "filter": True,
            "resizable": True,
        },

        dashGridOptions={
            "animateRows": False,
        },

        style={
            "height": "520px",
            "width": "100%",
        },

        className="ag-theme-quartz",
    )


# =============================================================================
# ДАННЫЕ МОДАЛКИ СКЛАДА
# =============================================================================

def _warehouse_modal_payload(
    warehouse_name,
    context,
):
    context = context or {}

    report_date = context.get(
        "report_date"
    )

    df = get_warehouse_products(
        report_date=report_date,
        warehouse_name=warehouse_name,

        cat_list=context.get(
            "cat_list"
        ),

        brand_list=context.get(
            "brand_list"
        ),

        gender_list=context.get(
            "gender_list"
        ),
    )

    if df.empty:
        title = str(
            warehouse_name
        )

        meta = (
            "По текущим фильтрам "
            "товаров на складе нет."
        )

        return (
            title,
            meta,
            products_grid(df),
        )

    on_hand = pd.to_numeric(
        df["Остаток"],
        errors="coerce",
    ).fillna(
        0
    ).sum()

    in_transit = (
        pd.to_numeric(
            df["В пути от клиента"],
            errors="coerce",
        ).fillna(0).sum()
        +
        pd.to_numeric(
            df["В пути к клиенту"],
            errors="coerce",
        ).fillna(0).sum()
    )

    total_qty = pd.to_numeric(
        df["Итого"],
        errors="coerce",
    ).fillna(
        0
    ).sum()

    nm_count = (
        df["NM ID"]
        .dropna()
        .nunique()
    )

    title = str(
        warehouse_name
    )

    meta = (
        f"На складе: {fmt(on_hand)} шт"
        f" · в пути: {fmt(in_transit)} шт"
        f" · всего: {fmt(total_qty)} шт"
        f" · товаров: {fmt(nm_count)} NM ID"
    )

    return (
        title,
        meta,
        products_grid(df),
    )


# =============================================================================
# DASHBOARD
# =============================================================================

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

        if pd.isna(
            requested_date
        ):
            requested_date = pd.Timestamp(
                date.today()
            )

        requested_date = (
            requested_date.strftime(
                "%Y-%m-%d"
            )
        )

        effective_date = (
            get_effective_stock_date(
                requested_date
            )
        )

        if effective_date is None:
            effective_date = (
                requested_date
            )

        effective_date = (
            pd.to_datetime(
                effective_date
            ).strftime(
                "%Y-%m-%d"
            )
        )

        # =====================================================================
        # Данные
        # =====================================================================

        summary = (
            get_stock_dashboard_summary(
                effective_date
            )
        )

        regions = (
            get_stock_regions(
                effective_date
            )
        )

        warehouses = (
            get_stock_warehouses(
                effective_date
            )
        )

        # =====================================================================
        # Подписи дат
        # =====================================================================

        requested_label = (
            pd.to_datetime(
                requested_date
            ).strftime(
                "%d.%m.%Y"
            )
        )

        effective_label = (
            pd.to_datetime(
                effective_date
            ).strftime(
                "%d.%m.%Y"
            )
        )

        if (
            effective_date
            != requested_date
        ):
            subtitle = (
                f"Остатки на {effective_label}"
                f" · выбрана дата {requested_label}"
                f" · использованы последние доступные данные"
            )

        else:
            subtitle = (
                "Интерактивный анализ распределения "
                f"на {effective_label}"
            )

        # =====================================================================
        # Dropdown быстрого открытия
        # =====================================================================

        warehouse_options = [
            {
                "label": row["warehouse"],
                "value": row["warehouse"],
            }
            for _, row
            in warehouses.iterrows()
        ]

        # =====================================================================
        # Layout
        # =====================================================================

        return dcc.Loading(
            children=dmc.Stack(
            gap="lg",

            children=[

                # =============================================================
                # Store
                # =============================================================

                dcc.Store(
                    id=STOCK_CONTEXT_ID,

                    data={
                        "report_date": (
                            effective_date
                        ),

                        "requested_date": (
                            requested_date
                        ),

                        "cat_list": (
                            cat_list or []
                        ),

                        "brand_list": (
                            brand_list or []
                        ),

                        "gender_list": (
                            gender_list or []
                        ),

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

                # =============================================================
                # Downloads
                # =============================================================

                dcc.Download(
                    id=STOCK_TRANSFER_DOWNLOAD_ID
                ),

                dcc.Download(
                    id=STOCK_WAREHOUSES_DOWNLOAD_ID
                ),

                # =============================================================
                # Заголовок
                # =============================================================

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

                            label="Быстро открыть склад",

                            placeholder="Выберите склад",

                            data=warehouse_options,

                            searchable=True,
                            clearable=True,

                            radius=0,

                            w=340,
                        ),
                    ],
                ),

                # =============================================================
                # KPI
                # =============================================================

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
                            suffix="",
                        ),

                        metric_card(
                            "Товаров",
                            summary["products"],
                            suffix="NM ID",
                        ),
                    ],
                ),

                # =============================================================
                # Подсказка
                # =============================================================

                dmc.Alert(
                    (
                        "Выберите склад на карте, на графике или в таблице → "
                        "откроется детализация склада. В детализации отметьте "
                        "нужные размеры checkbox → добавьте их в план "
                        "перемещения. В плане можно заполнить каждую строку "
                        "вручную либо одним действием переместить весь "
                        "доступный остаток на выбранный склад."
                    ),

                    title="Управление остатками",

                    color="green",
                    radius=0,
                    variant="light",
                ),

                # =============================================================
                # Карта
                # =============================================================

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
                                                "Размер точки отражает общий "
                                                "остаток. Нажмите на склад "
                                                "для открытия детализации."
                                            ),
                                            size="xs",
                                            c="dimmed",
                                        ),
                                    ]
                                ),

                                dmc.Text(
                                    (
                                        "Колёсико — масштаб · "
                                        "двойной клик/кнопка домика — сброс"
                                    ),
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

                                # Не даём колесику мыши резко менять масштаб.
                                # Масштаб можно менять кнопками Plotly,
                                # а двойной клик возвращает исходный вид.
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

                # =============================================================
                # Регионы
                #
                # Dropdown Регион УДАЛЁН.
                # =============================================================

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
                            mb="md",

                            children=[

                                html.Div(
                                    [
                                        dmc.Text(
                                            "Распределение по регионам",
                                            fw=700,
                                        ),

                                        dmc.Text(
                                            (
                                                "Распределение остатков по регионам. "
                                                "График информационный и не влияет "
                                                "на таблицу складов."
                                            ),
                                            size="xs",
                                            c="dimmed",
                                        ),
                                    ]
                                ),                                dmc.Text(
                                    "Только просмотр",
                                    size="xs",
                                    c="dimmed",
                                ),
                            ],
                        ),

                        dcc.Graph(
                            id=STOCK_REGION_CHART_ID,

                            figure=build_regions_chart(
                                regions
                            ),

                            config={
                                "displayModeBar": False,
                                "responsive": True,

                                # График полностью пассивный:
                                # ни zoom, ни pan, ни selection.
                                "staticPlot": True,
                            },
                        ),
                    ],
                ),

                # =============================================================
                # Таблица складов + chip детализации
                # =============================================================

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
                                                "Отметьте checkbox у склада — "
                                                "появится chip детализации. "
                                                "Нажмите chip, чтобы открыть товары склада. "
                                                "Excel учитывает встроенные фильтры таблицы."
                                            ),
                                            size="xs",
                                            c="dimmed",
                                        ),
                                    ]
                                ),

                                dmc.Group(
                                    gap="sm",
                                    align="center",

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
                                            "Скачать Excel",

                                            id=(
                                                STOCK_WAREHOUSES_DOWNLOAD_BTN_ID
                                            ),

                                            radius=0,
                                            color="green",
                                        ),
                                    ],
                                ),
                            ],
                        ),

                        dmc.Group(
                            justify="flex-start",
                            mb="sm",

                            children=[
                                dmc.ChipGroup(
                                    id=STOCK_SELECTED_WAREHOUSE_CHIPS_ID,
                                    children=[],
                                    multiple=False,
                                    deselectable=True,
                                ),
                            ],
                        ),

                        html.Div(
                            id=STOCK_WAREHOUSES_CONTAINER_ID,
                            style={
                                "display": "block",
                            },
                            children=[
                                warehouses_grid(
                                    warehouses
                                ),
                            ],
                        ),

                        dcc.Loading(
                            dmc.Container(
                                id=STOCK_WAREHOUSE_DETAILS_CONTAINER_ID,
                                fluid=True,
                                px=0,
                                style={
                                    "display": "none",
                                },
                            ),
                            type="graph",
                        ),
                    ],
                ),

                # =============================================================
                # Модалка плана перемещения
                # =============================================================

                dmc.Modal(
                    id=STOCK_TRANSFER_MODAL_ID,

                    opened=False,

                    size="95%",
                    radius=0,
                    centered=True,

                    title=dmc.Text(
                        "План перемещения товаров",
                        fw=700,
                    ),

                    children=[

                        dmc.Alert(
                            (
                                "Можно заполнить склад назначения и количество "
                                "вручную либо выбрать склад ниже и одним "
                                "действием перенести весь доступный физический "
                                "остаток выбранных позиций."
                            ),

                            color="green",
                            radius=0,
                            mb="md",
                        ),

                        # -----------------------------------------------------
                        # Массовое заполнение
                        # -----------------------------------------------------

                        dmc.Paper(
                            radius=0,
                            p="md",
                            mb="md",

                            style={
                                "border": (
                                    "1px solid #D6DFDB"
                                ),

                                "background": (
                                    "#F8FAF9"
                                ),
                            },

                            children=[

                                dmc.Text(
                                    "Массовое заполнение",
                                    fw=700,
                                    size="sm",
                                ),

                                dmc.Text(
                                    (
                                        "Выберите склад назначения. "
                                        "После нажатия кнопки во всех строках "
                                        "будет указан этот склад, а количество "
                                        "будет равно физически доступному остатку."
                                    ),
                                    size="xs",
                                    c="dimmed",
                                    mt=2,
                                    mb="sm",
                                ),

                                dmc.Group(
                                    align="flex-end",
                                    gap="sm",

                                    children=[

                                        dmc.Select(
                                            id=(
                                                STOCK_TRANSFER_BULK_WAREHOUSE_ID
                                            ),

                                            label=(
                                                "Склад назначения"
                                            ),

                                            placeholder=(
                                                "Выберите склад"
                                            ),

                                            data=[],

                                            searchable=True,
                                            clearable=True,

                                            radius=0,

                                            w=380,
                                        ),

                                        dmc.Button(
                                            "Переместить всё доступное",

                                            id=(
                                                STOCK_TRANSFER_ALL_QTY_BTN_ID
                                            ),

                                            disabled=True,

                                            radius=0,
                                            color="green",
                                        ),
                                    ],
                                ),
                            ],
                        ),

                        # -----------------------------------------------------
                        # Таблица плана
                        # -----------------------------------------------------

                        html.Div(
                            id=(
                                STOCK_TRANSFER_GRID_CONTAINER_ID
                            )
                        ),

                        # -----------------------------------------------------
                        # Footer
                        # -----------------------------------------------------

                        dmc.Group(
                            justify="space-between",
                            align="center",
                            mt="md",

                            children=[

                                dmc.Text(
                                    id=(
                                        STOCK_TRANSFER_VALIDATION_ID
                                    ),

                                    size="sm",
                                    c="dimmed",
                                ),

                                dmc.Button(
                                    "Скачать план Excel",

                                    id=(
                                        STOCK_TRANSFER_DOWNLOAD_BTN_ID
                                    ),

                                    radius=0,
                                    color="green",
                                ),
                            ],
                        ),
                    ],
                ),
            ],
            ),
            type="circle",
            fullscreen=True,
            overlay_style={
                "visibility": "visible",
                "filter": "blur(1px)",
            },
        )


# =============================================================================
# CALLBACKS
# =============================================================================

def register_stock_dashboard_callbacks(app):
    """
    Детализация склада работает через chip:

    - checkbox в таблице -> появляется chip;
    - клик по chip -> открывается детализация на странице;
    - снятие chip -> возврат к таблице складов;
    - карта и быстрый Select открывают ту же детализацию.
    """

    # =========================================================================
    # 1. Таблица складов -> checkbox -> показать chip
    # =========================================================================

    @app.callback(
        Output(
            STOCK_SELECTED_WAREHOUSE_CHIPS_ID,
            "children",
        ),

        Output(
            STOCK_SELECTED_WAREHOUSE_CHIPS_ID,
            "value",
        ),

        Input(
            STOCK_WAREHOUSES_GRID_ID,
            "selectedRows",
        ),

        prevent_initial_call=True,
    )
    def make_warehouse_chip(
        selected_rows,
    ):
        if not selected_rows:
            return (
                [],
                None,
            )

        row = selected_rows[0] or {}

        warehouse_name = str(
            row.get("warehouse")
            or ""
        ).strip()

        if not warehouse_name:
            return (
                [],
                None,
            )

        # Chip появляется, но не открывается автоматически:
        # пользователь сам нажимает на него.
        return (
            [
                warehouse_chip_maker(
                    warehouse_name
                )
            ],
            None,
        )

    # =========================================================================
    # 2. Карта -> сразу открыть ту же детализацию через chip
    # =========================================================================

    @app.callback(
        Output(
            STOCK_SELECTED_WAREHOUSE_CHIPS_ID,
            "children",
            allow_duplicate=True,
        ),

        Output(
            STOCK_SELECTED_WAREHOUSE_CHIPS_ID,
            "value",
            allow_duplicate=True,
        ),

        Input(
            STOCK_MAP_ID,
            "clickData",
        ),

        prevent_initial_call=True,
    )
    def select_warehouse_from_map(
        click_data,
    ):
        if not click_data:
            return (
                no_update,
                no_update,
            )

        points = (
            click_data.get("points")
            or []
        )

        if not points:
            return (
                no_update,
                no_update,
            )

        customdata = (
            points[0].get(
                "customdata"
            )
            or []
        )

        if not customdata:
            return (
                no_update,
                no_update,
            )

        warehouse_name = str(
            customdata[0]
            or ""
        ).strip()

        if not warehouse_name:
            return (
                no_update,
                no_update,
            )

        return (
            [
                warehouse_chip_maker(
                    warehouse_name
                )
            ],
            warehouse_name,
        )

    # =========================================================================
    # 3. Быстрый Select -> сразу открыть ту же детализацию через chip
    # =========================================================================

    @app.callback(
        Output(
            STOCK_SELECTED_WAREHOUSE_CHIPS_ID,
            "children",
            allow_duplicate=True,
        ),

        Output(
            STOCK_SELECTED_WAREHOUSE_CHIPS_ID,
            "value",
            allow_duplicate=True,
        ),

        Input(
            STOCK_WAREHOUSE_SELECT_ID,
            "value",
        ),

        prevent_initial_call=True,
    )
    def select_warehouse_from_dropdown(
        warehouse_name,
    ):
        warehouse_name = str(
            warehouse_name
            or ""
        ).strip()

        if not warehouse_name:
            return (
                no_update,
                no_update,
            )

        return (
            [
                warehouse_chip_maker(
                    warehouse_name
                )
            ],
            warehouse_name,
        )

    # =========================================================================
    # 4. Chip -> показать / скрыть детализацию склада
    # =========================================================================

    @app.callback(
        Output(
            STOCK_WAREHOUSES_CONTAINER_ID,
            "style",
        ),

        Output(
            STOCK_WAREHOUSE_DETAILS_CONTAINER_ID,
            "style",
        ),

        Output(
            STOCK_WAREHOUSE_DETAILS_CONTAINER_ID,
            "children",
        ),

        Output(
            STOCK_SELECTED_WAREHOUSE_STORE_ID,
            "data",
        ),

        Input(
            STOCK_SELECTED_WAREHOUSE_CHIPS_ID,
            "value",
        ),

        State(
            STOCK_CONTEXT_ID,
            "data",
        ),

        prevent_initial_call=True,
    )
    def display_warehouse_details(
        warehouse_name,
        context,
    ):
        warehouse_name = str(
            warehouse_name
            or ""
        ).strip()

        # Chip снят -> возвращаем список складов.
        if not warehouse_name:
            return (
                {"display": "block"},
                {"display": "none"},
                [],
                None,
            )

        title, meta, grid = (
            _warehouse_modal_payload(
                warehouse_name,
                context,
            )
        )

        return (
            {"display": "none"},
            {"display": "block"},
            [
                dmc.Stack(
                    gap="md",
                    children=[

                        dmc.Group(
                            justify="space-between",
                            align="center",

                            children=[

                                html.Div(
                                    [
                                        dmc.Title(
                                            title,
                                            order=4,
                                            fw=700,
                                        ),

                                        dmc.Text(
                                            meta,
                                            size="sm",
                                            c="dimmed",
                                            mt=2,
                                        ),

                                        dmc.Text(
                                            (
                                                "Checkbox выбирает конкретный "
                                                "размер / Chrt ID для плана перемещения."
                                            ),
                                            size="xs",
                                            c="dimmed",
                                            mt=3,
                                        ),
                                    ]
                                ),

                                dmc.Button(
                                    "Добавить выбранное в план",
                                    id=STOCK_TRANSFER_BTN_ID,
                                    disabled=True,
                                    radius=0,
                                    color="green",
                                ),
                            ],
                        ),

                        grid,
                    ],
                ),
            ],
            warehouse_name,
        )

    # =========================================================================
    # График по регионам — только визуализация.
    # =========================================================================


    # =========================================================================
    # 5. Выбор товаров checkbox -> активировать кнопку плана
    # =========================================================================

    @app.callback(
        Output(
            STOCK_TRANSFER_BTN_ID,
            "disabled",
        ),

        Input(
            STOCK_PRODUCTS_GRID_ID,
            "selectedRows",
        ),
    )
    def toggle_transfer_button(
        selected_rows,
    ):
        return not bool(
            selected_rows
        )

    # =========================================================================
    # 6. Открытие плана перемещения
    # =========================================================================

    @app.callback(
        Output(
            STOCK_TRANSFER_MODAL_ID,
            "opened",
        ),

        Output(
            STOCK_TRANSFER_GRID_CONTAINER_ID,
            "children",
        ),

        Output(
            STOCK_TRANSFER_VALIDATION_ID,
            "children",
        ),

        Output(
            STOCK_TRANSFER_BULK_WAREHOUSE_ID,
            "data",
        ),

        Output(
            STOCK_TRANSFER_BULK_WAREHOUSE_ID,
            "value",
        ),

        Input(
            STOCK_TRANSFER_BTN_ID,
            "n_clicks",
        ),

        State(
            STOCK_PRODUCTS_GRID_ID,
            "selectedRows",
        ),

        State(
            STOCK_SELECTED_WAREHOUSE_STORE_ID,
            "data",
        ),

        State(
            STOCK_CONTEXT_ID,
            "data",
        ),

        prevent_initial_call=True,
    )
    def open_transfer_modal(
        n_clicks,
        selected_rows,
        source_warehouse,
        context,
    ):
        if (
            not n_clicks
            or not selected_rows
            or not source_warehouse
        ):
            return (
                False,
                no_update,
                no_update,
                no_update,
                no_update,
            )

        context = context or {}

        report_date = (
            context.get(
                "report_date"
            )
        )

        # ---------------------------------------------------------------------
        # Склады назначения
        # ---------------------------------------------------------------------

        warehouses = (
            get_warehouse_options(
                report_date
            )
        )

        # Исключаем склад-источник.
        warehouses = [
            warehouse
            for warehouse in warehouses
            if warehouse
            != source_warehouse
        ]

        warehouse_options = [
            {
                "label": warehouse,
                "value": warehouse,
            }
            for warehouse in warehouses
        ]

        # ---------------------------------------------------------------------
        # Регион склада-источника
        # ---------------------------------------------------------------------

        source_region = ""

        for row in (
            context.get(
                "warehouses"
            )
            or []
        ):
            if (
                row.get("warehouse")
                == source_warehouse
            ):
                source_region = (
                    row.get("region")
                    or ""
                )

                break

        # ---------------------------------------------------------------------
        # Строки плана
        # ---------------------------------------------------------------------

        rows = []

        for row in selected_rows:
            # ВАЖНО:
            # доступно для перемещения только физическое
            # количество на складе.
            #
            # Не используем "Итого",
            # потому что туда входит товар в пути.
            available = _safe_float(
                row.get("Остаток")
            )

            rows.append(
                {
                    "Откуда": (
                        source_warehouse
                    ),

                    "Регион откуда": (
                        source_region
                    ),

                    "Куда": None,

                    "Бренд": row.get(
                        "Бренд"
                    ),

                    "Категория": row.get(
                        "Категория"
                    ),

                    "Артикул": row.get(
                        "Артикул"
                    ),

                    "Наименование": row.get(
                        "Наименование"
                    ),

                    "Размер": row.get(
                        "Размер"
                    ),

                    "Доступно": available,

                    "Переместить": 0,

                    "NM ID": row.get(
                        "NM ID"
                    ),

                    "Chrt ID": row.get(
                        "Chrt ID"
                    ),
                }
            )

        return (
            True,

            transfer_grid(
                rows,
                warehouses,
            ),

            (
                f"Выбрано позиций: {len(rows)}. "
                "Заполните план вручную или "
                "используйте массовое перемещение."
            ),

            warehouse_options,

            # При каждом новом открытии
            # очищаем предыдущий массовый склад.
            None,
        )

    # =========================================================================
    # 7. Активировать кнопку "Переместить всё доступное"
    # =========================================================================

    @app.callback(
        Output(
            STOCK_TRANSFER_ALL_QTY_BTN_ID,
            "disabled",
        ),

        Input(
            STOCK_TRANSFER_BULK_WAREHOUSE_ID,
            "value",
        ),
    )
    def toggle_bulk_transfer_button(
        warehouse,
    ):
        return not bool(
            warehouse
        )

    # =========================================================================
    # 8. Массово заполнить:
    #
    # Куда = выбранный склад
    # Переместить = весь доступный физический остаток
    # =========================================================================

    @app.callback(
        Output(
            STOCK_TRANSFER_GRID_ID,
            "rowData",
        ),

        Output(
            STOCK_TRANSFER_VALIDATION_ID,
            "children",
            allow_duplicate=True,
        ),

        Input(
            STOCK_TRANSFER_ALL_QTY_BTN_ID,
            "n_clicks",
        ),

        State(
            STOCK_TRANSFER_BULK_WAREHOUSE_ID,
            "value",
        ),

        State(
            STOCK_TRANSFER_GRID_ID,
            "rowData",
        ),

        prevent_initial_call=True,
    )
    def fill_all_transfer_rows(
        n_clicks,
        destination_warehouse,
        rows,
    ):
        if (
            not n_clicks
            or not destination_warehouse
            or not rows
        ):
            return (
                no_update,
                no_update,
            )

        updated_rows = []

        total_qty = 0.0
        active_rows = 0

        for row in rows:
            new_row = dict(
                row
            )

            available = _safe_float(
                new_row.get(
                    "Доступно"
                )
            )

            new_row["Куда"] = (
                destination_warehouse
            )

            new_row["Переместить"] = (
                available
            )

            updated_rows.append(
                new_row
            )

            if available > 0:
                active_rows += 1
                total_qty += available

        return (
            updated_rows,

            (
                f"Готово к выгрузке: "
                f"{active_rows} позиций · "
                f"{fmt(total_qty)} шт. · "
                f"склад назначения: "
                f"{destination_warehouse}"
            ),
        )

    # =========================================================================
    # 9. Валидация плана после ручных изменений
    # =========================================================================

    @app.callback(
        Output(
            STOCK_TRANSFER_VALIDATION_ID,
            "children",
            allow_duplicate=True,
        ),

        Input(
            STOCK_TRANSFER_GRID_ID,
            "cellValueChanged",
        ),

        State(
            STOCK_TRANSFER_GRID_ID,
            "rowData",
        ),

        prevent_initial_call=True,
    )
    def validate_transfer_plan(
        _,
        rows,
    ):
        if not rows:
            return ""

        total = 0.0

        invalid_qty = 0
        missing_destination = 0
        active_rows = 0

        for row in rows:
            available = _safe_float(
                row.get(
                    "Доступно"
                )
            )

            qty = _safe_float(
                row.get(
                    "Переместить"
                )
            )

            if qty <= 0:
                continue

            active_rows += 1
            total += qty

            if qty > available:
                invalid_qty += 1

            if not (
                str(
                    row.get("Куда")
                    or ""
                ).strip()
            ):
                missing_destination += 1

        if invalid_qty:
            return (
                f"Ошибка: в {invalid_qty} строках "
                "количество превышает физический остаток."
            )

        if missing_destination:
            return (
                "Не выбран склад назначения "
                f"для {missing_destination} строк."
            )

        if active_rows == 0:
            return (
                "Укажите количество "
                "хотя бы в одной строке."
            )

        return (
            f"Готово к выгрузке: "
            f"{active_rows} позиций · "
            f"{fmt(total)} шт."
        )

    # =========================================================================
    # 10. Скачать Excel плана перемещений
    # =========================================================================

    @app.callback(
        Output(
            STOCK_TRANSFER_DOWNLOAD_ID,
            "data",
        ),

        Input(
            STOCK_TRANSFER_DOWNLOAD_BTN_ID,
            "n_clicks",
        ),

        State(
            STOCK_TRANSFER_GRID_ID,
            "rowData",
        ),

        prevent_initial_call=True,
    )
    def download_transfer_plan(
        n_clicks,
        rows,
    ):
        if (
            not n_clicks
            or not rows
        ):
            return no_update

        selected = []

        for row in rows:
            qty = _safe_float(
                row.get(
                    "Переместить"
                )
            )

            available = _safe_float(
                row.get(
                    "Доступно"
                )
            )

            # Нулевая строка в Excel не нужна.
            if qty <= 0:
                continue

            if qty > available:
                return no_update

            destination = str(
                row.get("Куда")
                or ""
            ).strip()

            if not destination:
                return no_update

            selected.append(
                row
            )

        if not selected:
            return no_update

        try:
            content, filename = (
                build_transfer_plan_excel(
                    selected
                )
            )

        except ValueError:
            return no_update

        return dcc.send_bytes(
            content,
            filename,
        )

    # =========================================================================
    # 11. Excel таблицы складов
    #
    # virtualRowData =
    # строки ПОСЛЕ встроенных AG Grid фильтров и сортировки.
    # =========================================================================

    @app.callback(
        Output(
            STOCK_WAREHOUSES_DOWNLOAD_ID,
            "data",
        ),

        Input(
            STOCK_WAREHOUSES_DOWNLOAD_BTN_ID,
            "n_clicks",
        ),

        State(
            STOCK_WAREHOUSES_GRID_ID,
            "virtualRowData",
        ),

        State(
            STOCK_WAREHOUSES_GRID_ID,
            "rowData",
        ),

        State(
            STOCK_CONTEXT_ID,
            "data",
        ),

        prevent_initial_call=True,
    )
    def download_warehouses_excel(
        n_clicks,
        virtual_rows,
        row_data,
        context,
    ):
        if not n_clicks:
            return no_update

        # virtualRowData содержит данные после
        # встроенных фильтров AG Grid.
        #
        # При первом рендере некоторые версии AG Grid
        # могут вернуть None, поэтому есть fallback.
        rows = (
            virtual_rows
            if virtual_rows is not None
            else row_data
        )

        if not rows:
            return no_update

        context = context or {}

        report_date = (
            context.get(
                "report_date"
            )
        )

        try:
            content, filename = (
                build_warehouses_excel(
                    rows=rows,
                    report_date=report_date,
                )
            )

        except ValueError:
            return no_update

        return dcc.send_bytes(
            content,
            filename,
        )
