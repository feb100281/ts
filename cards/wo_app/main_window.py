import dash_mantine_components as dmc
import dash_ag_grid as dag

from .data import get_ag_grid_data


def make_ag_grid(opt):

    row_data = get_ag_grid_data(opt)

    if not row_data:
        return dmc.Alert(
            title="Нет данных",
            children="Пустой dataset",
            color="gray",
        )

    return dag.AgGrid(
        id=f"ag-grid-{opt}",

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
                    d3.format(',.2f')(params.value)
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
                    d3.format(',.2f')(params.value)
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
                    d3.format(',.2f')(params.value)
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
                    d3.format(',.2f')(params.value)
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

class MainWindow:
    def __init__(self):        
        self.ag_container_id = 'ag_container'
    
    
        
    def layout(self):
        return dmc.Container(
            [
                dmc.Container(
                    [
                        make_ag_grid('dates')
                    ],
                    id = self.ag_container_id,
                    fluid=True                    
                )
            ],
            fluid=True
        )
        
        

