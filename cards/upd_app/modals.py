# cards/upd_app/modals.py
from dash_iconify import DashIconify
import dash_mantine_components as dmc
from django.urls import reverse, NoReverseMatch
from cards.models import UpdDocument
import dash_ag_grid as dag
from .data import get_grid_data, get_size_options,update_size
from dash import dcc
from dash import Input, Output, no_update, State

class SizeModal:
    def __init__(self):
        pass
    
    def update_modal(self, nm_id):
        data = get_size_options(nm_id)
        return dmc.Stack(
            [
                dmc.RadioGroup(
                    id="size-radio",
                    children=dmc.Stack(
                        [
                            dmc.Radio(label=l, value=k)
                            for k, l in data
                        ],
                    ),
                    label="Выберите размер",
                    size="sm",
                ),
                dmc.Button(
                    id="insert-btn",
                    children="Применить",
                    disabled=True
                ),
                
            

            ],
            gap="sm",
        )
        
        
    
    def layout(self):
        return dmc.Modal(            
                id="size-modal",
                title="Выбор размера WB",
                opened=False,
                size="xl",
                children=[
                    dmc.Container(children=
                        [
                                          
                        ],
                        id="chrt-modal-content",
                        fluid=True)                    
                ],
            )
    
    def registered_callbacks(self,app):

        @app.callback(
            Output('size-modal', "opened"),
            Output("chrt-modal-content", "children"),
            Output("id_row_store", "data"),
            Output("chrt_id_store", "data"),
            Input('upd-grid', "cellDoubleClicked"),
            Input("upd-grid", "rowData"),

            prevent_initial_call=True,
        )
        def open_chrt_modal(cell, row_data):
            print(cell)
            if not cell:
                return no_update, no_update, no_update,no_update
            
            if cell.get("colId") != "chrt_id":
                return no_update, no_update,no_update,no_update
            
            row_id = cell.get("rowId")
            
            row = next(
                (r for r in row_data if str(r.get("id")) == str(row_id)),
                None
            )
            if row is None:
                return no_update, no_update, no_update,no_update
            
            upd_line_id = row.get("id")
            chrt_id = row.get("chrt_id")
            nm_id = row.get("nm_id")
            return (
                True,
                self.update_modal(nm_id),
                upd_line_id,
                chrt_id
            )
        
        @app.callback(
            Output("insert-btn", "disabled"),
            Output("selected_chrt", "data"),
            Input("size-radio", "value"),
            State("chrt_id_store", "data"),
        )
        def make_chose(val, current_chrt_id):

            if not val:
                return True, no_update

            if str(val) == str(current_chrt_id):
                return True, no_update

            return False, val
        
        @app.callback(
            Output("success-notification", "sendNotifications"),
            Output("upd-grid", "rowData", allow_duplicate=True),
            Output("size-modal", "opened", allow_duplicate=True),

            Input("insert-btn", "n_clicks"),

            State("id_row_store", "data"),
            State("selected_chrt", "data"),
            State("upd-id-store", "data"),

            prevent_initial_call=True,
        )
        def insert_new_item(n_click, row_id, chrt_id, upd_id):

            if not n_click:
                return no_update, no_update, no_update

            if not row_id or not chrt_id:
                return no_update, no_update, no_update

            update_size(row_id, chrt_id)

            df = get_grid_data(upd_id)

            return (
                [
                    dict(
                        title="Удачно!",
                        id="show-notify",
                        action="show",
                        message=f"Строка ID {row_id}: размер обновлен на {chrt_id}",
                        color="green",
                    )
                ],
                df.to_dict("records"),
                False,
            )