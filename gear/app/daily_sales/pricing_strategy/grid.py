
from __future__ import annotations

import dash_ag_grid as dag


def money_formatter():
    return {
        "function": """
            params.value === null || params.value === undefined
                ? ''
                : d3.format(',.0f')(params.value).replace(/,/g, ' ')
        """
    }


def number_formatter(digits=0):
    return {
        "function": f"""
            params.value === null || params.value === undefined
                ? ''
                : Number(params.value).toFixed({digits})
        """
    }


def pct_formatter(digits=1):
    return {
        "function": f"""
            params.value === null || params.value === undefined
                ? ''
                : Number(params.value).toFixed({digits}) + '%'
        """
    }


def pricing_grid(records):
    columns = [
        {
            "headerName": "Приоритет",
            "field": "priority",
            "width": 100,
            "pinned": "left",
            "sort": "desc",
            "valueFormatter": number_formatter(0),
        },
        {
            "headerName": "Решение",
            "field": "status",
            "width": 120,
            "pinned": "left",
            "cellStyle": {
                "styleConditions": [
                    {
                        "condition": "params.value === 'CLEARANCE'",
                        "style": {
                            "backgroundColor": "#FEE2E2",
                            "fontWeight": "700",
                        },
                    },
                    {
                        "condition": "params.value === 'REDUCE'",
                        "style": {
                            "backgroundColor": "#FFEDD5",
                            "fontWeight": "700",
                        },
                    },
                    {
                        "condition": "params.value === 'RAISE'",
                        "style": {
                            "backgroundColor": "#DCFCE7",
                            "fontWeight": "700",
                        },
                    },
                    {
                        "condition": "params.value === 'TEST'",
                        "style": {
                            "backgroundColor": "#FEF9C3",
                            "fontWeight": "700",
                        },
                    },
                    {
                        "condition": "params.value === 'HOLD'",
                        "style": {
                            "backgroundColor": "#F3F4F6",
                            "fontWeight": "700",
                        },
                    },
                ],
            },
        },
        {
            "headerName": "NM ID",
            "field": "nm_id",
            "width": 125,
            "pinned": "left",
        },
        {
            "headerName": "Бренд",
            "field": "brand",
            "width": 140,
        },
        {
            "headerName": "Наименование",
            "field": "title",
            "minWidth": 260,
            "flex": 1,
        },
        {
            "headerName": "Категория",
            "field": "category",
            "width": 160,
        },
        {
            "headerName": "Цена в карточке",
            "field": "current_seller_list_price",
            "width": 130,
            "type": "numericColumn",
            "valueFormatter": money_formatter(),
        },
        {
            "headerName": "Наша факт. цена 30д",
            "field": "seller_price_30d",
            "width": 145,
            "type": "numericColumn",
            "valueFormatter": money_formatter(),
        },
        {
            "headerName": "Цена покупателя 30д",
            "field": "buyer_price_30d",
            "width": 155,
            "type": "numericColumn",
            "valueFormatter": money_formatter(),
        },
        {
            "headerName": "Разница WB",
            "field": "wb_price_delta_pct_30d",
            "width": 110,
            "type": "numericColumn",
            "valueFormatter": pct_formatter(1),
        },
        {
            "headerName": "Рекоменд. наша",
            "field": "recommended_seller_price",
            "width": 140,
            "type": "numericColumn",
            "valueFormatter": money_formatter(),
        },
        {
            "headerName": "Рекоменд. покупателю",
            "field": "recommended_buyer_price",
            "width": 160,
            "type": "numericColumn",
            "valueFormatter": money_formatter(),
        },
        {
            "headerName": "Δ нашей цены",
            "field": "recommended_change_pct",
            "width": 115,
            "type": "numericColumn",
            "valueFormatter": pct_formatter(1),
        },
        {
            "headerName": "Маржа 30д",
            "field": "margin_man_30d",
            "width": 120,
            "type": "numericColumn",
            "valueFormatter": money_formatter(),
        },
        {
            "headerName": "Маржа %",
            "field": "margin_pct_30d",
            "width": 95,
            "type": "numericColumn",
            "valueFormatter": pct_formatter(1),
        },
        {
            "headerName": "Маржа сценарий",
            "field": "recommended_margin_30d",
            "width": 135,
            "type": "numericColumn",
            "valueFormatter": money_formatter(),
        },
        {
            "headerName": "+ маржа/день",
            "field": "margin_upside_day",
            "width": 125,
            "type": "numericColumn",
            "valueFormatter": money_formatter(),
        },
        {
            "headerName": "Остаток",
            "field": "stock_on_hand",
            "width": 105,
            "type": "numericColumn",
            "valueFormatter": number_formatter(0),
        },
        {
            "headerName": "В пути",
            "field": "stock_in_transit",
            "width": 95,
            "type": "numericColumn",
            "valueFormatter": number_formatter(0),
        },
        {
            "headerName": "Запас, дн.",
            "field": "days_of_stock",
            "width": 105,
            "type": "numericColumn",
            "valueFormatter": number_formatter(0),
            "cellStyle": {
                "styleConditions": [
                    {
                        "condition": "params.value >= 365",
                        "style": {
                            "backgroundColor": "#FEE2E2",
                            "fontWeight": "700",
                        },
                    },
                    {
                        "condition": "params.value >= 180 && params.value < 365",
                        "style": {
                            "backgroundColor": "#FFEDD5",
                        },
                    },
                ],
            },
        },
        {
            "headerName": "После решения, дн.",
            "field": "recommended_stock_days",
            "width": 125,
            "type": "numericColumn",
            "valueFormatter": number_formatter(0),
        },
        {
            "headerName": "Возраст, дн.",
            "field": "stock_age_days",
            "width": 105,
            "type": "numericColumn",
            "valueFormatter": number_formatter(0),
        },
        {
            "headerName": "Продажи 7д",
            "field": "sales_qty_7d",
            "width": 105,
            "type": "numericColumn",
            "valueFormatter": number_formatter(0),
        },
        {
            "headerName": "Продажи 30д",
            "field": "sales_qty_30d",
            "width": 110,
            "type": "numericColumn",
            "valueFormatter": number_formatter(0),
        },
        {
            "headerName": "Продажи 90д",
            "field": "sales_qty_90d",
            "width": 110,
            "type": "numericColumn",
            "valueFormatter": number_formatter(0),
        },
        {
            "headerName": "Тренд скорости",
            "field": "sales_speed_trend_pct",
            "width": 120,
            "type": "numericColumn",
            "valueFormatter": pct_formatter(0),
        },
        {
            "headerName": "Эластичность",
            "field": "elasticity",
            "width": 110,
            "type": "numericColumn",
            "valueFormatter": number_formatter(2),
        },
        {
            "headerName": "R²",
            "field": "elasticity_r2",
            "width": 75,
            "type": "numericColumn",
            "valueFormatter": number_formatter(2),
        },
        {
            "headerName": "Надёжность",
            "field": "elasticity_confidence",
            "width": 145,
        },
        {
            "headerName": "Confidence",
            "field": "confidence_score",
            "width": 105,
            "type": "numericColumn",
            "valueFormatter": pct_formatter(0),
        },
        {
            "headerName": "Почему",
            "field": "reason",
            "minWidth": 500,
            "wrapText": True,
            "autoHeight": True,
        },
    ]

    return dag.AgGrid(
        id="pricing-strategy-grid",
        rowData=records,
        columnDefs=columns,
        defaultColDef={
            "sortable": True,
            "filter": True,
            "resizable": True,
        },
        dashGridOptions={
            "rowSelection": "single",
            "animateRows": False,
            "pagination": True,
            "paginationPageSize": 50,
            "paginationPageSizeSelector": [25, 50, 100, 250],
            "suppressCellFocus": True,
        },
        style={
            "height": "720px",
            "width": "100%",
        },
        className="ag-theme-quartz",
    )
