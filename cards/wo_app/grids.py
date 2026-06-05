# cards/wo_app/grids.py
import dash_mantine_components as dmc
import dash_ag_grid as dag
from .data import get_data_by_date,get_data_by_item
import pandas as pd


def grid_date(start=None, end=None):

    row_data = get_data_by_date(start, end).to_dict(orient='records')

    if not row_data:
        return dmc.Alert(
            title="Нет данных",
            children="Пустой dataset",
            color="gray",
        )

    return dag.AgGrid(
        id="dates_grid",

        rowData=row_data,

        columnDefs=[
            {
                "field": "sales_date",
                "headerName": "Дата",
                "width": 130,
                "pinned": "left",
                "filter": "agDateColumnFilter",
            },

            {
                "field": "amount",
                "headerName": "Выручка",
                "width": 150,
                "type": "numericColumn",
                "valueFormatter": {
                    "function": """
                    params.value == null
                        ? ''
                        : d3.format(',.2f')(params.value)
                    """
                },
            },

            {
                "field": "vat_amount",
                "headerName": "НДС",
                "width": 140,
                "type": "numericColumn",
                "valueFormatter": {
                    "function": """
                    params.value == null
                        ? ''
                        : d3.format(',.2f')(params.value)
                    """
                },
            },

            {
                "field": "amount_vatless",
                "headerName": "Без НДС",
                "width": 150,
                "type": "numericColumn",
                "valueFormatter": {
                    "function": """
                    params.value == null
                        ? ''
                        : d3.format(',.2f')(params.value)
                    """
                },
            },

            {
                "field": "dt",
                "headerName": "Себестоимость",
                "width": 150,
                "type": "numericColumn",
                "valueFormatter": {
                    "function": """
                    params.value == null
                        ? ''
                        : d3.format(',.2f')(params.value)
                    """
                },
            },

            {
                "field": "total_net_sales",
                "headerName": "Продаж",
                "width": 110,
                "type": "numericColumn",
            },

            {
                "field": "no_cost",
                "headerName": "Без себест.",
                "width": 130,
                "type": "numericColumn",
            },
        ],

        defaultColDef={
            "sortable": True,
            "filter": True,
            "resizable": True,
            "editable": False,
        },

        dashGridOptions={
            "pagination": True,
            "paginationPageSize": 50,
            "enableCellTextSelection": True,
            "ensureDomOrder": True,
        },

        style={
            "height": "800px",
            "width": "100%",
        },

        className="ag-theme-alpine compact-grid",
    )


def grid_item(start=None, end=None):

    row_data = (
        get_data_by_item(start, end)
        .to_dict(orient="records")
    )

    if not row_data:
        return dmc.Alert(
            title="Нет данных",
            children="Пустой dataset",
            color="gray",
        )

    money_formatter = {
        "function": """
        d3.format(',.2f')(params.value)
        """
    }

    return dag.AgGrid(
        id="items_grid",

        rowData=row_data,

        columnDefs=[

            {
                "field": "mix_warning",
                "headerName": "",
                "width": 70,
                "pinned": "left",
            },

            {
                "field": "usk",
                "headerName": "USK",
                "width": 110,
                "pinned": "left",
            },

            {
                "field": "title",
                "headerName": "Название",
                "width": 320,
                "pinned": "left",
            },

            {
                "field": "nm_ids",
                "headerName": "Артикулы",
                "width": 220,
            },

            {
                "field": "aka",
                "headerName": "AKA",
                "width": 320,
            },

            {
                "field": "titles_cnt",
                "headerName": "Тайтлов",
                "width": 90,
                "type": "numericColumn",
            },
            
            {
            "field": "families_detected",
            "headerName": "Семейства",
            "width": 200,
            "tooltipField": "families_detected",  # показывать весь список при наведении
        },
            

            {
                "field": "amount",
                "headerName": "Выручка",
                "width": 150,
                "type": "numericColumn",
                "valueFormatter": money_formatter,
            },

            {
                "field": "vat_amount",
                "headerName": "НДС",
                "width": 130,
                "type": "numericColumn",
                "valueFormatter": money_formatter,
            },

            {
                "field": "amount_vatless",
                "headerName": "Без НДС",
                "width": 150,
                "type": "numericColumn",
                "valueFormatter": money_formatter,
            },

            {
                "field": "costs",
                "headerName": "Себест.",
                "width": 140,
                "type": "numericColumn",
                "valueFormatter": money_formatter,
            },

            {
                "field": "comparison_revenue",
                "headerName": "Соп. выручка",
                "width": 160,
                "type": "numericColumn",
                "valueFormatter": money_formatter,
            },

            {
                "field": "net_margin",
                "headerName": "Маржа",
                "width": 130,
                "type": "numericColumn",
                "valueFormatter": money_formatter,
            },

            {
                "field": "relative_margin",
                "headerName": "Маржа %",
                "width": 120,
                "type": "numericColumn",
                "valueFormatter": {
                    "function": """
                    d3.format(',.2f')(params.value) + '%'
                    """
                },
            },

            {
                "field": "total_net_sales_qty",
                "headerName": "Q продаж",
                "width": 100,
                "type": "numericColumn",
            },

            {
                "field": "no_cost_qty",
                "headerName": "Q без себест.",
                "width": 120,
                "type": "numericColumn",
            },

            {
                "field": "price_low",
                "headerName": "Цена min",
                "width": 120,
                "type": "numericColumn",
                "valueFormatter": money_formatter,
            },

            {
                "field": "price_median",
                "headerName": "Цена med",
                "width": 120,
                "type": "numericColumn",
                "valueFormatter": money_formatter,
            },

            {
                "field": "price_mean",
                "headerName": "Цена avg",
                "width": 120,
                "type": "numericColumn",
                "valueFormatter": money_formatter,
            },

            {
                "field": "price_high",
                "headerName": "Цена max",
                "width": 120,
                "type": "numericColumn",
                "valueFormatter": money_formatter,
            },

            {
                "field": "cost_low",
                "headerName": "Себест. min",
                "width": 130,
                "type": "numericColumn",
                "valueFormatter": money_formatter,
            },

            {
                "field": "costs_median",
                "headerName": "Себест. med",
                "width": 130,
                "type": "numericColumn",
                "valueFormatter": money_formatter,
            },

            {
                "field": "cost_mean",
                "headerName": "Себест. avg",
                "width": 130,
                "type": "numericColumn",
                "valueFormatter": money_formatter,
            },

            {
                "field": "cost_high",
                "headerName": "Себест. max",
                "width": 130,
                "type": "numericColumn",
                "valueFormatter": money_formatter,
            },
        ],

        defaultColDef={
            "sortable": True,
            "filter": True,
            "resizable": True,
            "editable": False,
        },

        dashGridOptions={
            "pagination": True,
            "paginationPageSize": 50,
            "enableCellTextSelection": True,
            "ensureDomOrder": True,
        },

        style={
            "height": "800px",
            "width": "100%",
        },

        className="ag-theme-alpine compact-grid",
    )