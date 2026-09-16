# # gear/app/daily_sales/grids.py
# import dash_mantine_components as dmc
# import dash_ag_grid as dag
# from datetime import date
# import pandas as pd
# from ..data.base import DashboardData
# from ..misc.baners import empty_df_banner


# def grid_date(start=date(2024,1,1), end=date.today(), cat_list=None, brand_list=None, gender_list=None):

#     with DashboardData() as d:
#         df = d.get_dayly_sales_grid_data(start,end,cat_list,brand_list,gender_list)
        
#         if df.empty:
#             return empty_df_banner()

#         row_data = df.to_dict(orient="records")
        
#     return dag.AgGrid(
#         id={"type":"dates_grid","index":"1"},
#         rowData=row_data,
#         columnDefs=[
#             {

#             "headerName": "",
#             "width": 40,
#             "checkboxSelection": True,
#             "headerCheckboxSelection": False,
#             "pinned": "left",
#             "lockPinned": True,
#             "sortable": False,
#             "filter": False,
#             "resizable": False,},
#             {
#                 "field": "date_from",
#                 "headerName": "Дата",
#                 "width": 130,
#                 "pinned": "left",
#                 "filter": "agDateColumnFilter",
#             },
#             {
#                 "field": "amount",
#                 "headerName": "Выручка",
#                 "width": 150,
#                 "type": "numericColumn",
#                 "valueFormatter": {
#                     "function": """
#                     params.value == null
#                         ? ''
#                         : d3.format(',.2f')(params.value)
#                     """
#                 },
#             },
#             {
#                 "field": "retail_amount",
#                 "headerName": "WB реализовал",
#                 "width": 150,
#                 "type": "numericColumn",
#                 "valueFormatter": {
#                     "function": """
#                     params.value == null
#                         ? ''
#                         : d3.format(',.2f')(params.value)
#                     """
#                 },
#             },
#             {
#                 "field": "wb_discount",
#                 "headerName": "WB дисконт (%)",
#                 "width": 130,
#                 "type": "numericColumn",
#                 "valueFormatter": {
#                     "function": """
#                     params.value == null
#                         ? ''
#                         : d3.format(',.2f')(params.value)
#                     """
#                 },
#             },
#             {
#                 "field": "vat_amount",
#                 "headerName": "НДС",
#                 "width": 140,
#                 "type": "numericColumn",
#                 "valueFormatter": {
#                     "function": """
#                     params.value == null
#                         ? ''
#                         : d3.format(',.2f')(params.value)
#                     """
#                 },
#             },
#             {
#                 "field": "amount_vatless",
#                 "headerName": "Без НДС",
#                 "width": 150,
#                 "type": "numericColumn",
#                 "valueFormatter": {
#                     "function": """
#                     params.value == null
#                         ? ''
#                         : d3.format(',.2f')(params.value)
#                     """
#                 },
#             },
#             {
#                 "field": "cogs",
#                 "headerName": "Бух с/с",
#                 "width": 150,
#                 "type": "numericColumn",
#                 "valueFormatter": {
#                     "function": """
#                     params.value == null
#                         ? ''
#                         : d3.format(',.2f')(params.value)
#                     """
#                 },
#             },
#             {
#                 "field": "cogs_man",
#                 "headerName": "Упр с/с",
#                 "width": 150,
#                 "type": "numericColumn",
#                 "valueFormatter": {
#                     "function": """
#                     params.value == null
#                         ? ''
#                         : d3.format(',.2f')(params.value)
#                     """
#                 },
#             },
#             {
#                 "field": "net_comission",
#                 "headerName": "Комиссия WB",
#                 "width": 130,
#                 "type": "numericColumn",
#                 "valueFormatter": {
#                     "function": """
#                     params.value == null
#                         ? ''
#                         : d3.format(',.2f')(params.value)
#                     """
#                 },
#             },
#             {
#                 "field": "margin",
#                 "headerName": "Бух маржа",
#                 "width": 150,
#                 "type": "numericColumn",
#                 "valueFormatter": {
#                     "function": """
#                     params.value == null
#                         ? ''
#                         : d3.format(',.2f')(params.value)
#                     """
#                 },
#             },
#             {
#                 "field": "margin_man",
#                 "headerName": "Упр маржа",
#                 "width": 150,
#                 "type": "numericColumn",
#                 "valueFormatter": {
#                     "function": """
#                     params.value == null
#                         ? ''
#                         : d3.format(',.2f')(params.value)
#                     """
#                 },
#             },
#             {
#                 "field": "total_net_sales",
#                 "headerName": "Q продаж",
#                 "width": 110,
#                 "type": "numericColumn",
#             },
#             {
#                 "field": "no_cost",
#                 "headerName": "Q без себест.",
#                 "width": 130,
#                 "type": "numericColumn",
#             },
#             {
#                 "field": "no_stocks",
#                 "headerName": "Нет на складе",
#                 "width": 130,
#                 "type": "numericColumn",
#             },
#             {
#                 "field": "no_income",
#                 "headerName": "Нет прихода",
#                 "width": 130,
#                 "type": "numericColumn",
#             },
#             {
#                 "field": "cogs_man_share",
#                 "headerName": "С/С (%)",
#                 "width": 130,
#                 "type": "numericColumn",
#                 "valueFormatter": {
#                     "function": """
#                     params.value == null
#                         ? ''
#                         : d3.format(',.2f')(params.value)
#                     """
#                 },
#             },
#             {
#                 "field": "commision_percent",
#                 "headerName": "Комиссия (%)",
#                 "width": 130,
#                 "type": "numericColumn",
#                 "valueFormatter": {
#                     "function": """
#                     params.value == null
#                         ? ''
#                         : d3.format(',.2f')(params.value)
#                     """
#                 },
#             },
#             {
#                 "field": "margin_percent",
#                 "headerName": "Маржинальность (%)",
#                 "width": 130,
#                 "type": "numericColumn",
#                 "valueFormatter": {
#                     "function": """
#                     params.value == null
#                         ? ''
#                         : d3.format(',.2f')(params.value)
#                     """
#                 },
#             },
#         ],
#         defaultColDef={
#             "sortable": True,
#             "filter": True,
#             "resizable": True,
#             "editable": False,
#         },
#         dashGridOptions={
#             "pagination": True,
#             "paginationPageSize": 50,
#             "enableCellTextSelection": True,
#             "ensureDomOrder": True,
#             "rowSelection": {'mode': 'multiRow', "headerCheckbox": False, "checkboxes": False},
#         },
#         style={
#             "height": "800px",
#             "width": "100%",
#         },
#         csvExportParams={
#                 "fileName": "grid_export.csv",
#             },
#         className="ag-theme-alpine compact-grid",
#     )


# def day_details(date,cat,brand,gender):

#     with DashboardData() as d:
#         df = d.get_day_details(date,cat,brand,gender)
        
#         if df.empty:
#             return empty_df_banner()

#         row_data = df.to_dict(orient="records")
        
#     return dag.AgGrid(
#         id={"type":"dates_grid","index":"2"},
#         rowData=row_data,
#         columnDefs=[
            
#             {
#                 "field": "usk",
#                 "headerName": "usk",
#                 "width": 50,
#                 "pinned": "left",
#                 # "filter": "agDateColumnFilter",
#             },
#             {
#                 "field": "brand",
#                 "headerName": "Брэнд",
#                 "width": 100,
#                 "pinned": "left",
#                 # "filter": "agDateColumnFilter",
#             },
#             {
#                 "field": "subject_name",
#                 "headerName": "Категория",
#                 "width": 100,
#                 "pinned": "left",
#                 # "filter": "agDateColumnFilter",
#             },
#             {
#                 "field": "title",
#                 "headerName": "Наименование",
#                 "width": 159,
#                 "pinned": "left",
#                 # "filter": "agDateColumnFilter",
#             },
#             {
#                 "field": "amount",
#                 "headerName": "Выручка",
#                 "width": 150,
#                 "type": "numericColumn",
#                 "valueFormatter": {
#                     "function": """
#                     params.value == null
#                         ? ''
#                         : d3.format(',.2f')(params.value)
#                     """
#                 },
#             },
#             {
#                 "field": "retail_amount",
#                 "headerName": "WB реализовал",
#                 "width": 150,
#                 "type": "numericColumn",
#                 "valueFormatter": {
#                     "function": """
#                     params.value == null
#                         ? ''
#                         : d3.format(',.2f')(params.value)
#                     """
#                 },
#             },
#             {
#                 "field": "wb_discount",
#                 "headerName": "WB дисконт (%)",
#                 "width": 130,
#                 "type": "numericColumn",
#                 "valueFormatter": {
#                     "function": """
#                     params.value == null
#                         ? ''
#                         : d3.format(',.2f')(params.value)
#                     """
#                 },
#             },
#             {
#                 "field": "vat_amount",
#                 "headerName": "НДС",
#                 "width": 140,
#                 "type": "numericColumn",
#                 "valueFormatter": {
#                     "function": """
#                     params.value == null
#                         ? ''
#                         : d3.format(',.2f')(params.value)
#                     """
#                 },
#             },
#             {
#                 "field": "amount_vatless",
#                 "headerName": "Без НДС",
#                 "width": 150,
#                 "type": "numericColumn",
#                 "valueFormatter": {
#                     "function": """
#                     params.value == null
#                         ? ''
#                         : d3.format(',.2f')(params.value)
#                     """
#                 },
#             },
#             {
#                 "field": "cogs",
#                 "headerName": "Бух с/с",
#                 "width": 150,
#                 "type": "numericColumn",
#                 "valueFormatter": {
#                     "function": """
#                     params.value == null
#                         ? ''
#                         : d3.format(',.2f')(params.value)
#                     """
#                 },
#             },
#             {
#                 "field": "cogs_man",
#                 "headerName": "Упр с/с",
#                 "width": 150,
#                 "type": "numericColumn",
#                 "valueFormatter": {
#                     "function": """
#                     params.value == null
#                         ? ''
#                         : d3.format(',.2f')(params.value)
#                     """
#                 },
#             },
#             {
#                 "field": "net_comission",
#                 "headerName": "Комиссия WB",
#                 "width": 130,
#                 "type": "numericColumn",
#                 "valueFormatter": {
#                     "function": """
#                     params.value == null
#                         ? ''
#                         : d3.format(',.2f')(params.value)
#                     """
#                 },
#             },
#             {
#                 "field": "margin",
#                 "headerName": "Бух маржа",
#                 "width": 150,
#                 "type": "numericColumn",
#                 "valueFormatter": {
#                     "function": """
#                     params.value == null
#                         ? ''
#                         : d3.format(',.2f')(params.value)
#                     """
#                 },
#             },
#             {
#                 "field": "margin_man",
#                 "headerName": "Упр маржа",
#                 "width": 150,
#                 "type": "numericColumn",
#                 "valueFormatter": {
#                     "function": """
#                     params.value == null
#                         ? ''
#                         : d3.format(',.2f')(params.value)
#                     """
#                 },
#             },
#             {
#                 "field": "total_net_sales",
#                 "headerName": "Q продаж",
#                 "width": 110,
#                 "type": "numericColumn",
#             },
#             {
#                 "field": "no_cost",
#                 "headerName": "Q без себест.",
#                 "width": 130,
#                 "type": "numericColumn",
#             },
#             {
#                 "field": "no_stocks",
#                 "headerName": "Нет на складе",
#                 "width": 130,
#                 "type": "numericColumn",
#             },
#             {
#                 "field": "no_income",
#                 "headerName": "Нет прихода",
#                 "width": 130,
#                 "type": "numericColumn",
#             },
#             {
#                 "field": "cogs_man_share",
#                 "headerName": "С/С (%)",
#                 "width": 130,
#                 "type": "numericColumn",
#                 "valueFormatter": {
#                     "function": """
#                     params.value == null
#                         ? ''
#                         : d3.format(',.2f')(params.value)
#                     """
#                 },
#             },
#             {
#                 "field": "commision_percent",
#                 "headerName": "Комиссия (%)",
#                 "width": 130,
#                 "type": "numericColumn",
#                 "valueFormatter": {
#                     "function": """
#                     params.value == null
#                         ? ''
#                         : d3.format(',.2f')(params.value)
#                     """
#                 },
#             },
#             {
#                 "field": "margin_percent",
#                 "headerName": "Маржинальность (%)",
#                 "width": 130,
#                 "type": "numericColumn",
#                 "valueFormatter": {
#                     "function": """
#                     params.value == null
#                         ? ''
#                         : d3.format(',.2f')(params.value)
#                     """
#                 },
#             },
#         ],
#         defaultColDef={
#             "sortable": True,
#             "filter": True,
#             "resizable": True,
#             "editable": False,
#         },
#         dashGridOptions={
#             "pagination": True,
#             "paginationPageSize": 50,
#             "enableCellTextSelection": True,
#             "ensureDomOrder": True,
            
#         },
#         style={
#             "height": "800px",
#             "width": "100%",
#         },
#         csvExportParams={
#                 "fileName": "daily_details.csv",
#             },
#         className="ag-theme-alpine compact-grid",
#     )



# # gear/app/daily_sales/grids.py

# from datetime import date

# import dash_ag_grid as dag
# import dash_mantine_components as dmc
# import pandas as pd

# from ..data.base import DashboardData
# from ..misc.baners import empty_df_banner


# MONEY_FORMATTER = {
#     "function": """
#     params.value == null
#         ? ''
#         : d3.format(',.2f')(params.value).replaceAll(',', ' ')
#     """
# }

# INT_FORMATTER = {
#     "function": """
#     params.value == null
#         ? ''
#         : d3.format(',.0f')(params.value).replaceAll(',', ' ')
#     """
# }

# PERCENT_FORMATTER = {
#     "function": """
#     params.value == null
#         ? ''
#         : d3.format(',.2f')(params.value).replaceAll(',', ' ') + ' %'
#     """
# }




# def _money_col(field, header, width=145, cell_style=None):
#     return {
#         "field": field,
#         "headerName": header,
#         "width": width,
#         "type": "numericColumn",
#         "valueFormatter": MONEY_FORMATTER,
#         "cellStyle": cell_style or {},
#     }


# def _int_col(field, header, width=120, cell_style=None):
#     return {
#         "field": field,
#         "headerName": header,
#         "width": width,
#         "type": "numericColumn",
#         "valueFormatter": INT_FORMATTER,
#         "cellStyle": cell_style or {},
#     }


# def _percent_col(field, header, width=135, cell_style=None):
#     return {
#         "field": field,
#         "headerName": header,
#         "width": width,
#         "type": "numericColumn",
#         "valueFormatter": PERCENT_FORMATTER,
#         "cellStyle": cell_style or {},
#     }


# def _base_grid(row_data, column_defs, grid_id, file_name):
#     return dag.AgGrid(
#         id=grid_id,
#         rowData=row_data,
#         columnDefs=column_defs,
#         dangerously_allow_code=True,
#         defaultColDef={
#             "sortable": True,
#             "filter": True,
#             "resizable": True,
#             "editable": False,
#             "floatingFilter": False,
#             "cellStyle": {
#                 "fontSize": "12px",
#                 "lineHeight": "1.25",
#             },
#         },
#         dashGridOptions={
#             "pagination": True,
#             "paginationPageSize": 50,
#             "enableCellTextSelection": True,
#             "ensureDomOrder": True,
#             "rowHeight": 34,
#             "headerHeight": 38,
#         },
#         style={
#             "height": "800px",
#             "width": "100%",
#         },
#         csvExportParams={
#     "fileName": file_name,
#     "columnSeparator": ";",
#     "useValueFormatterForExport": False,
#     "processCellCallback": {
#         "function": """
#         const value = params.value;

#         if (value === null || value === undefined) {
#             return '';
#         }

#         if (typeof value === 'number') {
#             return String(value).replace('.', ',');
#         }

#         return value;
#         """
#     },
# },
#         className="ag-theme-alpine compact-grid",
#     )


# def _daily_columns(include_checkbox=False):
#     columns = []

#     if include_checkbox:
#         columns.append(
#             {
#                 "headerName": "",
#                 "width": 44,
#                 "checkboxSelection": True,
#                 "headerCheckboxSelection": False,
#                 "pinned": "left",
#                 "lockPinned": True,
#                 "sortable": False,
#                 "filter": False,
#                 "resizable": False,
#                 "cellStyle": {
#                     "backgroundColor": "#f8fafc",
#                 },
#             }
#         )

#     columns.extend(
#         [
#             {
#                 "field": "date_from",
#                 "headerName": "Дата",
#                 "width": 120,
#                 "pinned": "left",
#                 "filter": "agDateColumnFilter",
#                 "cellStyle": {
#                     "fontWeight": "700",
#                     "backgroundColor": "#f8fafc",
#                     "borderRight": "1px solid #e5e7eb",
#                 },
#             },

#             _money_col(
#                 "amount",
#                 "Выручка",
#                 145,
#                 {
#                     "backgroundColor": "#eff6ff",
#                     "fontWeight": "700",
#                 },
#             ),
#             _money_col(
#                 "retail_amount",
#                 "WB реализовал",
#                 150,
#                 {
#                     "backgroundColor": "#ecfeff",
#                     "fontWeight": "700",
#                 },
#             ),
#             _percent_col(
#                 "wb_discount",
#                 "WB дисконт",
#                 130,
#                 {
#                     "backgroundColor": "#fff7ed",
#                     "fontWeight": "600",
#                 },
#             ),

#             _money_col("vat_amount", "НДС", 130),
#             _money_col("amount_vatless", "Без НДС", 145),

#             _money_col(
#                 "cogs",
#                 "Бух с/с",
#                 145,
#                 {
#                     "backgroundColor": "#f5f3ff",
#                     "fontWeight": "600",
#                 },
#             ),
#             _money_col(
#                 "cogs_man",
#                 "Упр с/с",
#                 145,
#                 {
#                     "backgroundColor": "#eef2ff",
#                     "fontWeight": "600",
#                 },
#             ),
#             _money_col(
#                 "net_comission",
#                 "Комиссия WB",
#                 145,
#                 {
#                     "backgroundColor": "#fff7ed",
#                     "fontWeight": "600",
#                 },
#             ),

#             _money_col(
#                 "margin",
#                 "Бух маржа",
#                 145,
#                 {
#                     "backgroundColor": "#f0fdf4",
#                     "fontWeight": "700",
#                 },
#             ),
#             _money_col(
#                 "margin_man",
#                 "Упр маржа",
#                 145,
#                 {
#                     "backgroundColor": "#ecfdf5",
#                     "fontWeight": "700",
#                 },
#             ),

#             _int_col("total_net_sales", "Q продаж", 115),

#             _int_col(
#                 "no_cost",
#                 "Q без себест.",
#                 130,
#                 {
#                     "backgroundColor": "#fff1f2",
#                     "fontWeight": "700",
#                     "color": "#dc2626",
#                 },
#             ),
#             _int_col(
#                 "no_stocks",
#                 "Нет на складе",
#                 130,
#                 {
#                     "backgroundColor": "#fff1f2",
#                     "fontWeight": "700",
#                     "color": "#dc2626",
#                 },
#             ),
#             _int_col(
#                 "no_income",
#                 "Нет прихода",
#                 130,
#                 {
#                     "backgroundColor": "#fff1f2",
#                     "fontWeight": "700",
#                     "color": "#dc2626",
#                 },
#             ),

#             _percent_col("cogs_man_share", "Упр с/с %", 130),
#             _percent_col("commision_percent", "Комиссия %", 130),
#             _percent_col(
#                 "margin_percent",
#                 "Марж. %",
#                 130,
#                 {
#                     "backgroundColor": "#f0fdf4",
#                     "fontWeight": "700",
#                 },
#             ),
#             _money_col(
#                 "cost_per_sold",
#                 "WB расходы руб / ед",
#                 145,
#                 {
#                     "backgroundColor": "#e5eedd",
#                     "fontWeight": "700",
#                 },
#             ),
#             _money_col(
#                 "wb_costs",
#                 "WB расходы руб",
#                 145,
#                 {
#                     "backgroundColor": "#f8fdec",
#                     "fontWeight": "700",
#                 },
#             ),
#             _money_col(
#                 "wb_result",
#                 "Фин результат WB",
#                 145,
#                 {
#                     "backgroundColor": "#E1F4F3",
#                     "fontWeight": "700",
#                 },
#             ),
#         ]
#     )

#     return columns


# def _details_columns():
#     return [
#         {
#             "field": "usk",
#             "headerName": "USK",
#             "width": 80,
#             "pinned": "left",
#             "cellStyle": {
#                 "backgroundColor": "#f8fafc",
#                 "fontWeight": "700",
#             },
#         },
#         {
#             "field": "brand",
#             "headerName": "Бренд",
#             "width": 120,
#             "pinned": "left",
#             "cellStyle": {
#                 "backgroundColor": "#f8fafc",
#             },
#         },
#         {
#             "field": "subject_name",
#             "headerName": "Категория",
#             "width": 145,
#             "pinned": "left",
#             "cellStyle": {
#                 "backgroundColor": "#f8fafc",
#             },
#         },
#         {
#             "field": "title",
#             "headerName": "Наименование",
#             "width": 240,
#             "pinned": "left",
#             "cellStyle": {
#                 "backgroundColor": "#f8fafc",
#                 "borderRight": "1px solid #e5e7eb",
#             },
#         },

#         _money_col(
#             "amount",
#             "Выручка",
#             145,
#             {
#                 "backgroundColor": "#eff6ff",
#                 "fontWeight": "700",
#             },
#         ),
#         _money_col(
#             "retail_amount",
#             "WB реализовал",
#             150,
#             {
#                 "backgroundColor": "#ecfeff",
#                 "fontWeight": "700",
#             },
#         ),
#         _percent_col(
#             "wb_discount",
#             "WB дисконт",
#             130,
#             {
#                 "backgroundColor": "#fff7ed",
#                 "fontWeight": "600",
#             },
#         ),

#         _money_col("vat_amount", "НДС", 130),
#         _money_col("amount_vatless", "Без НДС", 145),

#         _money_col(
#             "cogs",
#             "Бух с/с",
#             145,
#             {
#                 "backgroundColor": "#f5f3ff",
#                 "fontWeight": "600",
#             },
#         ),
#         _money_col(
#             "cogs_man",
#             "Упр с/с",
#             145,
#             {
#                 "backgroundColor": "#eef2ff",
#                 "fontWeight": "600",
#             },
#         ),
#         _money_col(
#             "net_comission",
#             "Комиссия WB",
#             145,
#             {
#                 "backgroundColor": "#fff7ed",
#                 "fontWeight": "600",
#             },
#         ),

#         _money_col(
#             "margin",
#             "Бух маржа",
#             145,
#             {
#                 "backgroundColor": "#f0fdf4",
#                 "fontWeight": "700",
#             },
#         ),
#         _money_col(
#             "margin_man",
#             "Упр маржа",
#             145,
#             {
#                 "backgroundColor": "#ecfdf5",
#                 "fontWeight": "700",
#             },
#         ),

#         _int_col("total_net_sales", "Q продаж", 115),

#         _int_col(
#             "no_cost",
#             "Q без себест.",
#             130,
#             {
#                 "backgroundColor": "#fff1f2",
#                 "fontWeight": "700",
#                 "color": "#dc2626",
#             },
#         ),
#         _int_col(
#             "no_stocks",
#             "Нет на складе",
#             130,
#             {
#                 "backgroundColor": "#fff1f2",
#                 "fontWeight": "700",
#                 "color": "#dc2626",
#             },
#         ),
#         _int_col(
#             "no_income",
#             "Нет прихода",
#             130,
#             {
#                 "backgroundColor": "#fff1f2",
#                 "fontWeight": "700",
#                 "color": "#dc2626",
#             },
#         ),

#         _percent_col("cogs_man_share", "Упр с/с %", 130),
#         _percent_col("commision_percent", "Комиссия %", 130),
#         _percent_col(
#             "margin_percent",
#             "Марж. %",
#             130,
#             {
#                 "backgroundColor": "#f0fdf4",
#                 "fontWeight": "700",
#             },
#         ),
        
       
#     ]


# def grid_date(
#     start=date(2024, 1, 1),
#     end=date.today(),
#     cat_list=None,
#     brand_list=None,
#     gender_list=None,
# ):
#     with DashboardData() as d:
#         df = d.get_dayly_sales_grid_data(
#             start,
#             end,
#             cat_list,
#             brand_list,
#             gender_list,
#         )

#     if df.empty:
#         return empty_df_banner()
    
#     df["date_from"] = (
#             pd.to_datetime(df["date_from"])
#             .dt.strftime("%Y-%m-%d")
#         )

#     row_data = df.to_dict(orient="records")

#     grid = _base_grid(
#         row_data=row_data,
#         column_defs=_daily_columns(include_checkbox=True),
#         grid_id={"type": "dates_grid", "index": "1"},
#         file_name="daily_sales.csv",
#     )

#     grid.dashGridOptions.update(
#         {
#             "rowSelection": {
#                 "mode": "multiRow",
#                 "headerCheckbox": False,
#                 "checkboxes": False,
#             },
#         }
#     )

#     return grid


# def day_details(date, cat, brand, gender):
#     with DashboardData() as d:
#         df = d.get_day_details(date, cat, brand, gender)

#     if df.empty:
#         return empty_df_banner()

#     row_data = df.to_dict(orient="records")

#     return _base_grid(
#         row_data=row_data,
#         column_defs=_details_columns(),
#         grid_id={"type": "dates_grid", "index": "2"},
#         file_name=f"daily_details_{date}.csv",
    
#     )
    

# def period_details(
#     start,
#     end,
#     cat=None,
#     brand=None,
#     gender=None,
# ):
#     """
#     Детализация по товарам за весь выбранный период.

#     Одна строка = один товар.
#     Даты в таблице нет.
#     """
#     with DashboardData() as d:
#         df = d.get_period_details(
#             start=start,
#             end=end,
#             cat_list=cat,
#             brand_list=brand,
#             gender_list=gender,
#         )

#     if df.empty:
#         return empty_df_banner()

#     row_data = df.to_dict(orient="records")

#     start_name = pd.to_datetime(start).strftime("%Y-%m-%d")
#     end_name = pd.to_datetime(end).strftime("%Y-%m-%d")

#     return _base_grid(
#         row_data=row_data,
#         column_defs=_period_details_columns(),
#         grid_id={
#             "type": "dates_grid",
#             "index": "2",
#         },
#         file_name=(
#             f"daily_details_"
#             f"{start_name}_"
#             f"{end_name}.csv"
#         ),
#     )
    
    
# def _period_details_columns():
#     columns = _details_columns()

#     columns.extend(
#         [
#             _int_col(
#                 "stock_quantity_sum",
#                 "Сумма остатков за период",
#                 175,
#                 {
#                     "backgroundColor": "#f0fdfa",
#                     "fontWeight": "600",
#                 },
#             ),

#             _int_col(
#                 "stock_days_count",
#                 "Дней с остатками",
#                 145,
#                 {
#                     "backgroundColor": "#f8fafc",
#                 },
#             ),

#             _money_col(
#                 "turnover_days",
#                 "Оборачиваемость, дней",
#                 175,
#                 {
#                     "backgroundColor": "#ecfdf5",
#                     "fontWeight": "700",
#                 },
#             ),

#             _int_col(
#                 "ending_stock",
#                 "Остаток на конец периода",
#                 190,
#                 {
#                     "backgroundColor": "#e0f2fe",
#                     "fontWeight": "700",
#                 },
#             ),

#             _int_col(
#                 "ending_warehouse_stock",
#                 "На складе на конец",
#                 165,
#                 {
#                     "backgroundColor": "#eff6ff",
#                     "fontWeight": "600",
#                 },
#             ),

#             _int_col(
#                 "ending_in_transit_stock",
#                 "В пути на конец",
#                 155,
#                 {
#                     "backgroundColor": "#f5f3ff",
#                     "fontWeight": "600",
#                 },
#             ),
#         ]
#     )

#     return columns


# gear/app/daily_sales/grids.py
from datetime import date

import dash_ag_grid as dag
import pandas as pd

from ..data.base import DashboardData
from ..misc.baners import empty_df_banner


MONEY_FORMATTER = {
    "function": """
    params.value == null
        ? ''
        : d3.format(',.2f')(params.value)
            .replaceAll(',', ' ')
    """
}

INT_FORMATTER = {
    "function": """
    params.value == null
        ? ''
        : d3.format(',.0f')(params.value)
            .replaceAll(',', ' ')
    """
}

PERCENT_FORMATTER = {
    "function": """
    params.value == null
        ? ''
        : d3.format(',.2f')(params.value)
            .replaceAll(',', ' ') + ' %'
    """
}

DATE_FORMATTER = {
    "function": """
    if (
        params.value === null
        || params.value === undefined
        || params.value === ''
    ) {
        return '';
    }

    const value = String(params.value).slice(0, 10);
    const parts = value.split('-');

    if (parts.length !== 3) {
        return value;
    }

    return `${parts[2]}.${parts[1]}.${parts[0]}`;
    """
}


def _money_col(
    field,
    header,
    width=145,
    cell_style=None,
):
    return {
        "field": field,
        "headerName": header,
        "width": width,
        "type": "numericColumn",
        "valueFormatter": MONEY_FORMATTER,
        "cellStyle": cell_style or {},
    }


def _int_col(
    field,
    header,
    width=120,
    cell_style=None,
):
    return {
        "field": field,
        "headerName": header,
        "width": width,
        "type": "numericColumn",
        "valueFormatter": INT_FORMATTER,
        "cellStyle": cell_style or {},
    }


def _percent_col(
    field,
    header,
    width=135,
    cell_style=None,
):
    return {
        "field": field,
        "headerName": header,
        "width": width,
        "type": "numericColumn",
        "valueFormatter": PERCENT_FORMATTER,
        "cellStyle": cell_style or {},
    }


def _date_col(
    field,
    header,
    width=130,
    cell_style=None,
    pinned=False,
):
    column = {
        "field": field,
        "headerName": header,
        "width": width,
        "filter": "agDateColumnFilter",
        "valueFormatter": DATE_FORMATTER,
        "cellStyle": cell_style or {},
    }

    if pinned:
        column["pinned"] = "left"
        column["lockPinned"] = True

    return column


def _base_grid(
    row_data,
    column_defs,
    grid_id,
    file_name,
):
    return dag.AgGrid(
        id=grid_id,
        rowData=row_data,
        columnDefs=column_defs,
        dangerously_allow_code=True,
        defaultColDef={
            "sortable": True,
            "filter": True,
            "resizable": True,
            "editable": False,
            "floatingFilter": False,
            "cellStyle": {
                "fontSize": "12px",
                "lineHeight": "1.25",
            },
        },
        dashGridOptions={
            "pagination": True,
            "paginationPageSize": 50,
            "enableCellTextSelection": True,
            "ensureDomOrder": True,
            "rowHeight": 34,
            "headerHeight": 38,
        },
        style={
            "height": "800px",
            "width": "100%",
        },
        csvExportParams={
            "fileName": file_name,
            "columnSeparator": ";",
            "useValueFormatterForExport": False,
            "processCellCallback": {
                "function": """
                const value = params.value;

                if (
                    value === null
                    || value === undefined
                ) {
                    return '';
                }

                if (typeof value === 'number') {
                    return String(value)
                        .replace('.', ',');
                }

                return value;
                """
            },
        },
        className=(
            "ag-theme-alpine compact-grid"
        ),
    )


def _stock_columns():
    return [
        _date_col(
            "ending_stock_date",
            "Дата остатка",
            130,
            {
                "backgroundColor": "#f8fafc",
                "fontWeight": "600",
            },
        ),

        _int_col(
            "ending_stock",
            "Остаток всего",
            145,
            {
                "backgroundColor": "#e0f2fe",
                "fontWeight": "700",
            },
        ),

        _int_col(
            "ending_warehouse_stock",
            "На WB",
            125,
            {
                "backgroundColor": "#eff6ff",
                "fontWeight": "600",
            },
        ),

        _int_col(
            "ending_fbs_stock",
            "FBS",
            110,
            {
                "backgroundColor": "#ecfdf5",
                "fontWeight": "700",
            },
        ),

        _int_col(
            "ending_in_transit_stock",
            "В пути",
            125,
            {
                "backgroundColor": "#f5f3ff",
                "fontWeight": "600",
            },
        ),
    ]


def _daily_columns(
    include_checkbox=False,
):
    columns = []

    if include_checkbox:
        columns.append(
            {
                "headerName": "",
                "width": 44,
                "checkboxSelection": True,
                "headerCheckboxSelection": False,
                "pinned": "left",
                "lockPinned": True,
                "sortable": False,
                "filter": False,
                "resizable": False,
                "cellStyle": {
                    "backgroundColor": "#f8fafc",
                },
            }
        )

    columns.extend(
        [
            _date_col(
                "date_from",
                "Дата",
                120,
                {
                    "fontWeight": "700",
                    "backgroundColor": "#f8fafc",
                    "borderRight": (
                        "1px solid #e5e7eb"
                    ),
                },
                pinned=True,
            ),

            _money_col(
                "amount",
                "Выручка",
                145,
                {
                    "backgroundColor": "#eff6ff",
                    "fontWeight": "700",
                },
            ),

            _money_col(
                "retail_amount",
                "WB реализовал",
                150,
                {
                    "backgroundColor": "#ecfeff",
                    "fontWeight": "700",
                },
            ),

            _percent_col(
                "wb_discount",
                "WB дисконт",
                130,
                {
                    "backgroundColor": "#fff7ed",
                    "fontWeight": "600",
                },
            ),

            _money_col(
                "vat_amount",
                "НДС",
                130,
            ),

            _money_col(
                "amount_vatless",
                "Без НДС",
                145,
            ),

            _money_col(
                "cogs",
                "Бух с/с",
                145,
                {
                    "backgroundColor": "#f5f3ff",
                    "fontWeight": "600",
                },
            ),

            _money_col(
                "cogs_man",
                "Упр с/с",
                145,
                {
                    "backgroundColor": "#eef2ff",
                    "fontWeight": "600",
                },
            ),

            _money_col(
                "net_comission",
                "Комиссия WB",
                145,
                {
                    "backgroundColor": "#fff7ed",
                    "fontWeight": "600",
                },
            ),

            _money_col(
                "margin",
                "Бух маржа",
                145,
                {
                    "backgroundColor": "#f0fdf4",
                    "fontWeight": "700",
                },
            ),

            _money_col(
                "margin_man",
                "Упр маржа",
                145,
                {
                    "backgroundColor": "#ecfdf5",
                    "fontWeight": "700",
                },
            ),

            _int_col(
                "total_net_sales",
                "Q продаж",
                115,
            ),

            _int_col(
                "no_cost",
                "Q без себест.",
                130,
                {
                    "backgroundColor": "#fff1f2",
                    "fontWeight": "700",
                    "color": "#dc2626",
                },
            ),

            _int_col(
                "no_stocks",
                "Нет на складе",
                130,
                {
                    "backgroundColor": "#fff1f2",
                    "fontWeight": "700",
                    "color": "#dc2626",
                },
            ),

            _int_col(
                "no_income",
                "Нет прихода",
                130,
                {
                    "backgroundColor": "#fff1f2",
                    "fontWeight": "700",
                    "color": "#dc2626",
                },
            ),

            _percent_col(
                "cogs_man_share",
                "Упр с/с %",
                130,
            ),

            _percent_col(
                "commision_percent",
                "Комиссия %",
                130,
            ),

            _percent_col(
                "margin_percent",
                "Марж. %",
                130,
                {
                    "backgroundColor": "#f0fdf4",
                    "fontWeight": "700",
                },
            ),

            _money_col(
                "cost_per_sold",
                "WB расходы руб / ед",
                155,
                {
                    "backgroundColor": "#e5eedd",
                    "fontWeight": "700",
                },
            ),

            _money_col(
                "wb_costs",
                "WB расходы руб",
                145,
                {
                    "backgroundColor": "#f8fdec",
                    "fontWeight": "700",
                },
            ),

            _money_col(
                "wb_result",
                "Фин результат WB",
                155,
                {
                    "backgroundColor": "#E1F4F3",
                    "fontWeight": "700",
                },
            ),

            *_stock_columns(),

            _money_col(
                "daily_stock_days",
                "Запас при темпе дня, дней",
                190,
                {
                    "backgroundColor": "#ecfdf5",
                    "fontWeight": "700",
                },
            ),
        ]
    )

    return columns


def _details_columns():
    return [
        {
            "field": "usk",
            "headerName": "USK",
            "width": 90,
            "pinned": "left",
            "cellStyle": {
                "backgroundColor": "#f8fafc",
                "fontWeight": "700",
            },
        },

        {
            "field": "brand",
            "headerName": "Бренд",
            "width": 130,
            "pinned": "left",
            "cellStyle": {
                "backgroundColor": "#f8fafc",
            },
        },

        {
            "field": "subject_name",
            "headerName": "Категория",
            "width": 155,
            "pinned": "left",
            "cellStyle": {
                "backgroundColor": "#f8fafc",
            },
        },

        {
            "field": "title",
            "headerName": "Наименование",
            "width": 260,
            "pinned": "left",
            "cellStyle": {
                "backgroundColor": "#f8fafc",
                "borderRight": (
                    "1px solid #e5e7eb"
                ),
            },
        },

        _money_col(
            "amount",
            "Выручка",
            145,
            {
                "backgroundColor": "#eff6ff",
                "fontWeight": "700",
            },
        ),

        _money_col(
            "retail_amount",
            "WB реализовал",
            150,
            {
                "backgroundColor": "#ecfeff",
                "fontWeight": "700",
            },
        ),

        _percent_col(
            "wb_discount",
            "WB дисконт",
            130,
            {
                "backgroundColor": "#fff7ed",
                "fontWeight": "600",
            },
        ),

        _money_col(
            "vat_amount",
            "НДС",
            130,
        ),

        _money_col(
            "amount_vatless",
            "Без НДС",
            145,
        ),

        _money_col(
            "cogs",
            "Бух с/с",
            145,
            {
                "backgroundColor": "#f5f3ff",
                "fontWeight": "600",
            },
        ),

        _money_col(
            "cogs_man",
            "Упр с/с",
            145,
            {
                "backgroundColor": "#eef2ff",
                "fontWeight": "600",
            },
        ),

        _money_col(
            "net_comission",
            "Комиссия WB",
            145,
            {
                "backgroundColor": "#fff7ed",
                "fontWeight": "600",
            },
        ),

        _money_col(
            "margin",
            "Бух маржа",
            145,
            {
                "backgroundColor": "#f0fdf4",
                "fontWeight": "700",
            },
        ),

        _money_col(
            "margin_man",
            "Упр маржа",
            145,
            {
                "backgroundColor": "#ecfdf5",
                "fontWeight": "700",
            },
        ),

        _int_col(
            "total_net_sales",
            "Q продаж",
            115,
        ),

        _int_col(
            "no_cost",
            "Q без себест.",
            130,
            {
                "backgroundColor": "#fff1f2",
                "fontWeight": "700",
                "color": "#dc2626",
            },
        ),

        _int_col(
            "no_stocks",
            "Нет на складе",
            130,
            {
                "backgroundColor": "#fff1f2",
                "fontWeight": "700",
                "color": "#dc2626",
            },
        ),

        _int_col(
            "no_income",
            "Нет прихода",
            130,
            {
                "backgroundColor": "#fff1f2",
                "fontWeight": "700",
                "color": "#dc2626",
            },
        ),

        _percent_col(
            "cogs_man_share",
            "Упр с/с %",
            130,
        ),

        _percent_col(
            "commision_percent",
            "Комиссия %",
            130,
        ),

        _percent_col(
            "margin_percent",
            "Марж. %",
            130,
            {
                "backgroundColor": "#f0fdf4",
                "fontWeight": "700",
            },
        ),
    ]


def _day_details_columns():
    columns = _details_columns()

    columns.extend(
        [
            *_stock_columns(),

            _money_col(
                "daily_stock_days",
                "Запас при темпе дня, дней",
                190,
                {
                    "backgroundColor": "#ecfdf5",
                    "fontWeight": "700",
                },
            ),

            {
                "field": "stock_status",
                "headerName": "Статус остатка",
                "width": 175,
                "cellStyle": {
                    "function": """
                    if (
                        params.value
                        === 'Остаток без продаж'
                    ) {
                        return {
                            backgroundColor: '#fff7ed',
                            color: '#c2410c',
                            fontWeight: '700'
                        };
                    }

                    if (
                        params.value
                        === 'Нет данных об остатке'
                    ) {
                        return {
                            backgroundColor: '#fff1f2',
                            color: '#dc2626',
                            fontWeight: '700'
                        };
                    }

                    return {
                        backgroundColor: '#f0fdf4',
                        color: '#166534',
                        fontWeight: '600'
                    };
                    """
                },
            },
        ]
    )

    return columns


def _period_details_columns():
    columns = _details_columns()

    columns.extend(
        [
            _int_col(
                "stock_quantity_sum",
                "Сумма ежедневных остатков",
                195,
                {
                    "backgroundColor": "#f0fdfa",
                    "fontWeight": "600",
                },
            ),

            _int_col(
                "stock_days_count",
                "Дней с остатками",
                145,
                {
                    "backgroundColor": "#f8fafc",
                },
            ),

            _date_col(
                "first_stock_date",
                "Первая дата остатка",
                155,
                {
                    "backgroundColor": "#f8fafc",
                },
            ),

            _date_col(
                "last_stock_date",
                "Последняя дата в периоде",
                175,
                {
                    "backgroundColor": "#f8fafc",
                },
            ),

            _money_col(
                "turnover_days",
                "Оборачиваемость, дней",
                175,
                {
                    "backgroundColor": "#ecfdf5",
                    "fontWeight": "700",
                },
            ),

            *_stock_columns(),

            {
                "field": "stock_status",
                "headerName": "Статус остатка",
                "width": 175,
                "cellStyle": {
                    "function": """
                    if (
                        params.value
                        === 'Остаток без продаж'
                    ) {
                        return {
                            backgroundColor: '#fff7ed',
                            color: '#c2410c',
                            fontWeight: '700'
                        };
                    }

                    if (
                        params.value
                        === 'Нет данных об остатке'
                        || params.value
                        === 'Нет истории остатков'
                    ) {
                        return {
                            backgroundColor: '#fff1f2',
                            color: '#dc2626',
                            fontWeight: '700'
                        };
                    }

                    return {
                        backgroundColor: '#f0fdf4',
                        color: '#166534',
                        fontWeight: '600'
                    };
                    """
                },
            },
        ]
    )

    return columns


def _prepare_dates(df):
    date_columns = {
        "date_from",
        "ending_stock_date",
        "first_stock_date",
        "last_stock_date",
    }

    for column in date_columns:
        if column not in df.columns:
            continue

        df[column] = (
            pd.to_datetime(
                df[column],
                errors="coerce",
            )
            .dt.strftime("%Y-%m-%d")
        )

        df[column] = df[column].where(
            df[column].notna(),
            None,
        )

    return df


def grid_date(
    start=date(2024, 1, 1),
    end=date.today(),
    cat_list=None,
    brand_list=None,
    gender_list=None,
):
    with DashboardData() as dashboard:
        df = dashboard.get_dayly_sales_grid_data(
            start,
            end,
            cat_list,
            brand_list,
            gender_list,
        )

    if df.empty:
        return empty_df_banner()

    df = _prepare_dates(df)

    row_data = df.to_dict(
        orient="records"
    )

    grid = _base_grid(
        row_data=row_data,
        column_defs=_daily_columns(
            include_checkbox=True
        ),
        grid_id={
            "type": "dates_grid",
            "index": "1",
        },
        file_name="daily_sales.csv",
    )

    grid.dashGridOptions.update(
        {
            "rowSelection": {
                "mode": "multiRow",
                "headerCheckbox": False,
                "checkboxes": False,
            },
        }
    )

    return grid


def day_details(
    date,
    cat,
    brand,
    gender,
):
    with DashboardData() as dashboard:
        df = dashboard.get_day_details(
            date,
            cat,
            brand,
            gender,
        )

    if df.empty:
        return empty_df_banner()

    df = _prepare_dates(df)

    row_data = df.to_dict(
        orient="records"
    )

    return _base_grid(
        row_data=row_data,
        column_defs=_day_details_columns(),
        grid_id={
            "type": "dates_grid",
            "index": "2",
        },
        file_name=(
            f"daily_details_{date}.csv"
        ),
    )


def period_details(
    start,
    end,
    cat=None,
    brand=None,
    gender=None,
):
    with DashboardData() as dashboard:
        df = dashboard.get_period_details(
            start=start,
            end=end,
            cat_list=cat,
            brand_list=brand,
            gender_list=gender,
        )

    if df.empty:
        return empty_df_banner()

    df = _prepare_dates(df)

    row_data = df.to_dict(
        orient="records"
    )

    start_name = (
        pd.to_datetime(start)
        .strftime("%Y-%m-%d")
    )

    end_name = (
        pd.to_datetime(end)
        .strftime("%Y-%m-%d")
    )

    return _base_grid(
        row_data=row_data,
        column_defs=_period_details_columns(),
        grid_id={
            "type": "dates_grid",
            "index": "2",
        },
        file_name=(
            f"daily_details_"
            f"{start_name}_"
            f"{end_name}.csv"
        ),
    )
    
