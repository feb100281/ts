# cards/upd_app/upd_form.py
import dash_mantine_components as dmc

from cards.models import UpdDocument
from .components.header import build_upd_header
from .components.summary_cards import build_upd_summary_cards
from .components.grid import build_upd_grid
from dash import dcc


from .data import get_grid_data

class UpdForm:

    def __init__(self, upd_id):
        self.upd_id = upd_id
        upd = UpdDocument.objects.select_related(

            'lot',
            'counterparty',
            'contract',

        ).get(id=upd_id)

        self.header = build_upd_header(upd)
        
    def summary_cards(self):
        df = get_grid_data(self.upd_id)
        return build_upd_summary_cards(df)
    

    def grid(self):
        df = get_grid_data(self.upd_id)
        return build_upd_grid(df)

    def layout(self):

        return dmc.Container(
            [
                dcc.Store(id="upd-id-store", data=self.upd_id),
                dcc.Store(id="id_row_store"),
                dcc.Store(id="chrt_id_store"),
                dcc.Store(id="selected_chrt"),

                dmc.NotificationProvider(
                    id="success-notification"
                ),

                self.header,
                self.summary_cards(),
                self.grid(),


            ],
            fluid=True,
        )
        
            