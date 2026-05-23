# cards/upd_app/callbacks.py
from dash import Input, Output, State, no_update
from .data import update_size, get_grid_data


def register_callbacks(app):

    @app.callback(
        Output("dummy", "children"),
        Output("upd-grid", "rowData", allow_duplicate=True),

        Input("upd-grid", "cellValueChanged"),

        State("upd-id-store", "data"),

        prevent_initial_call=True,
    )
    def save_grid_change(change, upd_id):

        if not change:
            return no_update, no_update

        if isinstance(change, list):
            change = change[-1]

        if change.get("colId") != "chrt_id":
            return no_update, no_update

        row = change.get("data", {})
        row_id = row.get("id")
        raw_value = change.get("value")

        if row_id is None or raw_value in [None, ""]:
            return no_update, no_update

        chrt_id = str(raw_value).split("|")[0].strip()

        update_size(row_id, chrt_id)

        df = get_grid_data(upd_id)

        return "", df.to_dict("records")