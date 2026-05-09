from dash_iconify import DashIconify

import dash_mantine_components as dmc

from cards.models import UpdDocument

import dash_ag_grid as dag

from .data import get_grid_data

class UpdForm:

    def __init__(self, upd_id):

        self.upd_id = upd_id

        upd = UpdDocument.objects.select_related(

            'lot',

            'counterparty',

            'contract',

        ).get(id=upd_id)

        self.header = dmc.Box(

            [

                dmc.Title(

                    f"УПД №{upd.number} от {upd.date.strftime('%d.%m.%Y')}",

                    order=2,

                ),

                dmc.Text(

                    f"Контрагент: {upd.counterparty}, Контракт: {upd.contract}"

                ),

                dmc.Divider(size='xs'),

            ]

        )

    def grid(self):

        df = get_grid_data(self.upd_id)

        return dag.AgGrid(

            id="upd-grid",

            rowData=df.to_dict("records"),

            columnDefs=[

                {"field": "id", "headerName": "ID", "hide": True},

                {"field": "upd_pos", "headerName": "Поз.", "width": 90},

                {"field": "brand", "headerName": "Бренд", "width": 120},

                {"field": "upd_title", "headerName": "Название УПД", "width": 300},

                {"field": "upd_sa_name", "headerName": "Артикул УПД", "width": 160},

                {"field": "sa_name", "headerName": "Артикул продавца", "width": 160},

                {"field": "nm_id", "headerName": "Артикль WB (nmId)", "width": 140},

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

                    "width": 220,

                },

                {"field": "available_sizes", "headerName": "Размеры WB", "width": 180},

                {"field": "size_options", "hide": True},

                {"field": "upd_qty", "headerName": "Кол-во", "width": 110},

                {"field": "upd_price_vatless", "headerName": "Цена без НДС", "width": 140},

                {"field": "upd_vat_rate", "headerName": "Ставка НДС в УПД", "width": 140},

                {"field": "upd_amount_vatadd", "headerName": "Сумма с НДС", "width": 140},

                {

                    "field": "man_cost_per_unit",

                    "headerName": "Упр. себес.",

                    "editable": True,

                    "width": 140,

                },

                {

                    "field": "currency_code",

                    "headerName": "Валюта",

                    "editable": True,

                    "width": 110,

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

    def layout(self):

        return dmc.Container(

            [

                self.header,

                self.grid(),

            ],

            fluid=True,

        )
    
    
        