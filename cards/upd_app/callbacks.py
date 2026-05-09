from dash import Input, Output, no_update
from .data import update_size


def register_callbacks(app):

    @app.callback(
        Output("dummy", "children"),
        Input("upd-grid", "cellValueChanged"),
        prevent_initial_call=True,
    )
    def save_grid_change(change):

        if not change:
            return no_update

        if isinstance(change, list):
            change = change[-1]

        if change.get("colId") != "chrt_id":
            return no_update

        row = change.get("data", {})
        row_id = row.get("id")
        raw_value = change.get("value")

        if not row_id or not raw_value:
            return no_update

        chrt_id = str(raw_value).split("|")[0].strip()

        update_size(row_id, chrt_id)

        return ""