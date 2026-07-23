"""AG Grid компоненты. Используется современный rowSelection API v32+."""

import pandas as pd
import dash_ag_grid as dag

from .ids import (
    STOCK_WAREHOUSES_GRID_ID,
    STOCK_WAREHOUSE_PRODUCTS_GRID_ID,
    STOCK_TRANSFER_GRID_ID,
)


NUMBER_FORMATTER = {
    "function": (
        "params.value == null ? '' : "
        "d3.format(',.0f')(params.value)"
    )
}


def warehouses_grid(df: pd.DataFrame):
    df = df if df is not None else pd.DataFrame()

    return dag.AgGrid(
        id=STOCK_WAREHOUSES_GRID_ID,
        rowData=df.to_dict("records"),
        getRowId="params.data.warehouse",

        columnDefs=[
            {
                "headerName": "Регион",
                "field": "region",
                "flex": 1.15,
                "minWidth": 210,
            },
            {
                "headerName": "Склад",
                "field": "warehouse",
                "flex": 1.45,
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
                "valueFormatter": NUMBER_FORMATTER,
            },
            {
                "headerName": "На складе",
                "field": "on_hand",
                "type": "numericColumn",
                "width": 135,
                "valueFormatter": NUMBER_FORMATTER,
            },
            {
                "headerName": "В пути",
                "field": "in_transit",
                "type": "numericColumn",
                "width": 120,
                "valueFormatter": NUMBER_FORMATTER,
            },
            {
                "headerName": "Итого",
                "field": "total_qty",
                "type": "numericColumn",
                "width": 135,
                "valueFormatter": NUMBER_FORMATTER,
                "cellStyle": {
                    "fontWeight": "600",
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
            "animateRows": False,

            # AG Grid 32+: никаких deprecated checkboxSelection /
            # suppressRowClickSelection.
            "rowSelection": {
                "mode": "singleRow",
                "checkboxes": True,
                "headerCheckbox": False,
                "enableClickSelection": False,
            },

            "selectionColumnDef": {
                "width": 48,
                "minWidth": 48,
                "maxWidth": 48,
                "pinned": "left",
                "sortable": False,
                "resizable": False,
            },
        },

        style={
            "height": "500px",
            "width": "100%",
        },
        className="ag-theme-quartz",
    )


def products_grid(
    df: pd.DataFrame,
    grid_id=STOCK_WAREHOUSE_PRODUCTS_GRID_ID,
):
    df = df if df is not None else pd.DataFrame()

    return dag.AgGrid(
        id=grid_id,
        rowData=df.to_dict("records"),

        columnDefs=[
            {"headerName": "Бренд", "field": "Бренд", "width": 150},
            {"headerName": "Категория", "field": "Категория", "width": 180},
            {"headerName": "Артикул", "field": "Артикул", "width": 145},
            {
                "headerName": "Наименование",
                "field": "Наименование",
                "minWidth": 340,
                "flex": 1,
            },
            {"headerName": "Размер", "field": "Размер", "width": 95},
            {
                "headerName": "Остаток",
                "field": "Остаток",
                "type": "numericColumn",
                "width": 115,
                "valueFormatter": NUMBER_FORMATTER,
            },
            {
                "headerName": "В пути от клиента",
                "field": "В пути от клиента",
                "type": "numericColumn",
                "width": 155,
                "valueFormatter": NUMBER_FORMATTER,
            },
            {
                "headerName": "В пути к клиенту",
                "field": "В пути к клиенту",
                "type": "numericColumn",
                "width": 155,
                "valueFormatter": NUMBER_FORMATTER,
            },
            {
                "headerName": "Итого",
                "field": "Итого",
                "type": "numericColumn",
                "width": 110,
                "valueFormatter": NUMBER_FORMATTER,
            },
            {
                "headerName": "Продажи 7д",
                "field": "Продажи 7 дней",
                "type": "numericColumn",
                "width": 125,
                "valueFormatter": NUMBER_FORMATTER,
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
            {"headerName": "NM ID", "field": "NM ID", "width": 135},
            {"headerName": "Chrt ID", "field": "Chrt ID", "width": 135},
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
            "animateRows": False,
            "rowSelection": {
                "mode": "multiRow",
                "checkboxes": True,
                "headerCheckbox": True,
                "enableClickSelection": False,
            },
            "selectionColumnDef": {
                "width": 48,
                "minWidth": 48,
                "maxWidth": 48,
                "pinned": "left",
                "sortable": False,
                "resizable": False,
            },
        },

        style={
            "height": "610px",
            "width": "100%",
        },
        className="ag-theme-quartz",
    )


def transfer_grid(rows, warehouses):
    return dag.AgGrid(
        id=STOCK_TRANSFER_GRID_ID,
        rowData=rows or [],

        columnDefs=[
            {"headerName": "Откуда", "field": "Откуда", "width": 220},
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
            {"headerName": "Бренд", "field": "Бренд", "width": 140},
            {"headerName": "Категория", "field": "Категория", "width": 160},
            {"headerName": "Артикул", "field": "Артикул", "width": 140},
            {
                "headerName": "Наименование",
                "field": "Наименование",
                "minWidth": 300,
                "flex": 1,
            },
            {"headerName": "Размер", "field": "Размер", "width": 90},
            {
                "headerName": "Доступно",
                "field": "Доступно",
                "type": "numericColumn",
                "width": 110,
                "valueFormatter": NUMBER_FORMATTER,
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
                "valueFormatter": NUMBER_FORMATTER,
            },
            {"headerName": "NM ID", "field": "NM ID", "width": 130},
            {"headerName": "Chrt ID", "field": "Chrt ID", "width": 130},
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
