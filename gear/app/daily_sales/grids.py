import dash_mantine_components as dmc
import dash_ag_grid as dag
from datetime import date
import pandas as pd
from ..data.base import DashboardData
from ..misc.baners import empty_df_banner


def grid_date(start=date(2024,1,1), end=date.today(), cat_list=None, brand_list=None, gender_list=None):

    with DashboardData() as d:
        df = d.get_dayly_sales_grid_data(start,end,cat_list,brand_list,gender_list)
        
        if df.empty:
            return empty_df_banner()

        row_data = df.to_dict(orient="records")
        
    return dag.AgGrid(
        id={"type":"dates_grid","index":"1"},
        rowData=row_data,
        columnDefs=[
            {

            "headerName": "",
            "width": 40,
            "checkboxSelection": True,
            "headerCheckboxSelection": False,
            "pinned": "left",
            "lockPinned": True,
            "sortable": False,
            "filter": False,
            "resizable": False,},
            {
                "field": "date_from",
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
                "field": "retail_amount",
                "headerName": "WB реализовал",
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
                "field": "wb_discount",
                "headerName": "WB дисконт (%)",
                "width": 130,
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
                "field": "cogs",
                "headerName": "Бух с/с",
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
                "field": "cogs_man",
                "headerName": "Упр с/с",
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
                "field": "net_comission",
                "headerName": "Комиссия WB",
                "width": 130,
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
                "field": "margin",
                "headerName": "Бух маржа",
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
                "field": "margin_man",
                "headerName": "Упр маржа",
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
                "headerName": "Q продаж",
                "width": 110,
                "type": "numericColumn",
            },
            {
                "field": "no_cost",
                "headerName": "Q без себест.",
                "width": 130,
                "type": "numericColumn",
            },
            {
                "field": "no_stocks",
                "headerName": "Нет на складе",
                "width": 130,
                "type": "numericColumn",
            },
            {
                "field": "no_income",
                "headerName": "Нет прихода",
                "width": 130,
                "type": "numericColumn",
            },
            {
                "field": "cogs_man_share",
                "headerName": "С/С (%)",
                "width": 130,
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
                "field": "commision_percent",
                "headerName": "Комиссия (%)",
                "width": 130,
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
                "field": "margin_percent",
                "headerName": "Маржинальность (%)",
                "width": 130,
                "type": "numericColumn",
                "valueFormatter": {
                    "function": """
                    params.value == null
                        ? ''
                        : d3.format(',.2f')(params.value)
                    """
                },
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
            "rowSelection": {'mode': 'multiRow', "headerCheckbox": False, "checkboxes": False},
        },
        style={
            "height": "800px",
            "width": "100%",
        },
        csvExportParams={
                "fileName": "grid_export.csv",
            },
        className="ag-theme-alpine compact-grid",
    )


def day_details(date,cat,brand,gender):

    with DashboardData() as d:
        df = d.get_day_details(date,cat,brand,gender)
        
        if df.empty:
            return empty_df_banner()

        row_data = df.to_dict(orient="records")
        
    return dag.AgGrid(
        id={"type":"dates_grid","index":"2"},
        rowData=row_data,
        columnDefs=[
            
            {
                "field": "usk",
                "headerName": "usk",
                "width": 50,
                "pinned": "left",
                # "filter": "agDateColumnFilter",
            },
            {
                "field": "brand",
                "headerName": "Брэнд",
                "width": 100,
                "pinned": "left",
                # "filter": "agDateColumnFilter",
            },
            {
                "field": "subject_name",
                "headerName": "Категория",
                "width": 100,
                "pinned": "left",
                # "filter": "agDateColumnFilter",
            },
            {
                "field": "title",
                "headerName": "Наименование",
                "width": 159,
                "pinned": "left",
                # "filter": "agDateColumnFilter",
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
                "field": "retail_amount",
                "headerName": "WB реализовал",
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
                "field": "wb_discount",
                "headerName": "WB дисконт (%)",
                "width": 130,
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
                "field": "cogs",
                "headerName": "Бух с/с",
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
                "field": "cogs_man",
                "headerName": "Упр с/с",
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
                "field": "net_comission",
                "headerName": "Комиссия WB",
                "width": 130,
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
                "field": "margin",
                "headerName": "Бух маржа",
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
                "field": "margin_man",
                "headerName": "Упр маржа",
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
                "headerName": "Q продаж",
                "width": 110,
                "type": "numericColumn",
            },
            {
                "field": "no_cost",
                "headerName": "Q без себест.",
                "width": 130,
                "type": "numericColumn",
            },
            {
                "field": "no_stocks",
                "headerName": "Нет на складе",
                "width": 130,
                "type": "numericColumn",
            },
            {
                "field": "no_income",
                "headerName": "Нет прихода",
                "width": 130,
                "type": "numericColumn",
            },
            {
                "field": "cogs_man_share",
                "headerName": "С/С (%)",
                "width": 130,
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
                "field": "commision_percent",
                "headerName": "Комиссия (%)",
                "width": 130,
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
                "field": "margin_percent",
                "headerName": "Маржинальность (%)",
                "width": 130,
                "type": "numericColumn",
                "valueFormatter": {
                    "function": """
                    params.value == null
                        ? ''
                        : d3.format(',.2f')(params.value)
                    """
                },
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
        csvExportParams={
                "fileName": "daily_details.csv",
            },
        className="ag-theme-alpine compact-grid",
    )