# # cards/upd_app/components/grid.py
# import dash_ag_grid as dag


# def build_upd_grid(df):

#     return dag.AgGrid(
#         id="upd-grid",

#         rowData=df.to_dict("records"),

#         columnDefs=[
#             {"field": "id", "headerName": "ID", "hide": True},
#             {"field": "upd_pos", "headerName": "Поз.", "width": 90, "pinned": "left",},
#             {"field": "brand", "headerName": "Бренд", "width": 120, "pinned": "left",},
#             {"field": "upd_title", "headerName": "Название УПД", "width": 300, "pinned": "left",},
#             {"field": "upd_sa_name", "headerName": "Артикул УПД", "width": 160, "pinned": "left",},
#             {"field": "sa_name", "headerName": "Артикул продавца", "width": 160},

#             {
#                 "field": "nm_id",
#                 "headerName": "Артикль WB (nmId)",
#                 "cellStyle": {
#                     "styleConditions": [
#                         {
#                             "condition": "!params.value",
#                             "style": {"backgroundColor": "#ffe5e5"},
#                         }
#                     ],
#                     "defaultStyle": {"backgroundColor": "transparent"},
#                 },
#                 "width": 140,
#             },

#             {"field": "upd_size", "headerName": "Размер УПД", "width": 120},
#             {"field": "tech_size", "headerName": "Принятый размер", "width": 120},

#             {
#                 "field": "chrt_id",
#                 "headerName": "Код размера WB (chrt_id)",
#                 "editable": True,
#                 "cellEditor": "agSelectCellEditor",
#                 "cellEditorParams": {
#                     "function": "sizeOptions(params)"
#                 },
#                 "valueParser": {
#                     "function": """
#                     params.newValue.split('|')[0].trim()
#                     """
#                 },
#                 "cellStyle": {
#                     "styleConditions": [
#                         {
#                             "condition": "!params.value",
#                             "style": {"backgroundColor": "#ffe5e5"},
#                         }
#                     ],
#                     "defaultStyle": {"backgroundColor": "transparent"},
#                 },
#                 "width": 220,
#             },

#             {"field": "available_sizes", "headerName": "Размеры WB", "width": 180},
#             {"field": "size_options", "hide": True},
#             {"field": "upd_qty", "headerName": "Кол-во", "width": 110},
#             {"field": "upd_price_vatless", "headerName": "Цена без НДС", "width": 140},
            
            
#             {
#                 "field": "man_cost_per_unit",
#                 "headerName": "Упр. себес.",
#                 "editable": True,
#                 "width": 140,
#             },
                  
#             {"field": "upd_vat_rate", "headerName": "Ставка НДС в УПД", "width": 140},
#             {"field": "upd_amount_vatadd", "headerName": "Сумма с НДС", "width": 140},

      

#             {
#                 "field": "currency_code",
#                 "headerName": "Валюта",
#                 "editable": True,
#                 "width": 110,
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
#             "rowSelection": "multiple",
#             "enableCellTextSelection": True,
#             "ensureDomOrder": True,
#         },

#         getRowId="params.data.id.toString()",

#         style={
#             "height": "800px",
#             "width": "100%",
#         },

#         className="ag-theme-alpine compact-grid",
#     )




# cards/upd_app/components/grid.py
import dash_ag_grid as dag


def build_upd_grid(df):
    # Рассчитаем дельты относительно управленческой себестоимости
    df['cost_delta_rub'] = (df['upd_price_vatless'] - df['man_cost_per_unit']).round(2)
    df['cost_delta_percent'] = (
        (df['upd_price_vatless'] - df['man_cost_per_unit']) / df['man_cost_per_unit'] * 100
    ).round(2)

    # Флаг, что управленческая себестоимость выше обычной
    df['is_man_cost_higher'] = df['man_cost_per_unit'] > df['upd_price_vatless']

    return dag.AgGrid(
        id="upd-grid",
        rowData=df.to_dict("records"),
        columnDefs=[
            {"field": "id", "headerName": "ID", "hide": True},
            {"field": "upd_pos", "headerName": "Поз.", "width": 90, "pinned": "left"},
            {"field": "brand", "headerName": "Бренд", "width": 120, "pinned": "left"},
            {"field": "upd_title", "headerName": "Название УПД", "width": 300, "pinned": "left"},
            {"field": "upd_sa_name", "headerName": "Артикул УПД", "width": 160, "pinned": "left"},
            {"field": "sa_name", "headerName": "Артикул продавца", "width": 160},

            {
                "field": "nm_id",
                "headerName": "Артикль WB (nmId)",
                "cellStyle": {
                    "styleConditions": [
                        {
                            "condition": "!params.value",
                            "style": {"backgroundColor": "#ffe5e5"},
                        }
                    ],
                    "defaultStyle": {"backgroundColor": "transparent"},
                },
                "width": 140,
            },

            {"field": "upd_size", "headerName": "Размер УПД", "width": 120},
            {"field": "tech_size", "headerName": "Принятый размер", "width": 120},

            {
                "field": "chrt_id",
                "headerName": "Код размера WB (chrt_id)",
                "editable": True,
                "cellEditor": "agSelectCellEditor",
                "cellEditorParams": {
                    "function": "sizeOptions(params)"
                },
                "valueParser": {
                    "function": """
                    params.newValue.split('|')[0].trim()
                    """
                },
                "cellStyle": {
                    "styleConditions": [
                        {
                            "condition": "!params.value",
                            "style": {"backgroundColor": "#ffe5e5"},
                        }
                    ],
                    "defaultStyle": {"backgroundColor": "transparent"},
                },
                "width": 220,
            },

            {"field": "available_sizes", "headerName": "Размеры WB", "width": 180},
            {"field": "size_options", "hide": True},
            {"field": "upd_qty", "headerName": "Кол-во", "width": 110},
            
            # Цена без НДС
            {
                "field": "upd_price_vatless", 
                "headerName": "Цена без НДС (бух с/сть)", 
                "width": 170,
                "valueFormatter": {"function": "params.value ? Number(params.value).toFixed(2) : ''"},
                "cellStyle": {
                    "defaultStyle": {"backgroundColor": "#f0f0f0"},
                },
            },
            
            # Упр. себес. - базовое значение
            {
                "field": "man_cost_per_unit",
                "headerName": "Упр. себес. (база)",
                "editable": True,
                "width": 150,
                "valueFormatter": {"function": "params.value ? Number(params.value).toFixed(2) : ''"},
                "cellStyle": {
                    "styleConditions": [
                        {
                            "condition": "params.data.is_man_cost_higher === true",
                            "style": {
                                "backgroundColor": "#ffcdd2",
                                "color": "#d32f2f",
                                "fontWeight": "bold",
                            },
                        }
                    ],
                    "defaultStyle": {
                        "backgroundColor": "#e3f2fd",
                        "color": "#000000",
                    },
                },
            },
            
            # Дельта в рублях (отклонение обычной от управленческой)
            {
                "field": "cost_delta_rub",
                "headerName": "Дельта, руб",
                "width": 180,
                "valueFormatter": {"function": "params.value ? Number(params.value).toFixed(2) : ''"},
                "cellStyle": {
                    "styleConditions": [
                        {
                            "condition": "params.value < 0",  # Отрицательная дельта = перерасход
                            "style": {
                                "color": "#d32f2f",
                                "fontWeight": "bold",
                            },
                        },
                        {
                            "condition": "params.value > 0",  # Положительная дельта = экономия
                            "style": {
                                "color": "#2e7d32",
                                "fontWeight": "bold",
                            },
                        },
                    ],
                    "defaultStyle": {"color": "#000000"},
                },
            },
            
            # Дельта в процентах
            {
                "field": "cost_delta_percent",
                "headerName": "Дельта, %",
                "width": 180,
                "valueFormatter": {"function": "params.value ? Number(params.value).toFixed(2) + '%' : ''"},
                "cellStyle": {
                    "styleConditions": [
                        {
                            "condition": "params.value < 0",  # Отрицательная дельта = перерасход
                            "style": {
                                "color": "#d32f2f",
                                "fontWeight": "bold",
                            },
                        },
                        {
                            "condition": "params.value > 0",  # Положительная дельта = экономия
                            "style": {
                                "color": "#2e7d32",
                                "fontWeight": "bold",
                            },
                        },
                    ],
                    "defaultStyle": {"color": "#000000"},
                },
            },
                  
            {"field": "upd_vat_rate", "headerName": "Ставка НДС в УПД", "width": 140},
            {"field": "upd_amount_vatadd", "headerName": "Сумма с НДС", "width": 140},

            {
                "field": "currency_code",
                "headerName": "Валюта",
                "editable": True,
                "width": 110,
            },
        ],
        
        # Подсветка всей строки при перерасходе
        rowStyle={
            "styleConditions": [
                {
                    "condition": "params.data.is_man_cost_higher === true",
                    "style": {"backgroundColor": "#ffebee"},
                }
            ],
            "defaultStyle": {"backgroundColor": "transparent"},
        },

        defaultColDef={
            "sortable": True,
            "filter": True,
            "resizable": True,
            "editable": False,
        },

        dashGridOptions={
            "pagination": True,
            "paginationPageSize": 50,
            "rowSelection": "multiple",
            "enableCellTextSelection": True,
            "ensureDomOrder": True,
        },

        getRowId="params.data.id.toString()",

        style={
            "height": "800px",
            "width": "100%",
        },

        className="ag-theme-alpine compact-grid",
    )