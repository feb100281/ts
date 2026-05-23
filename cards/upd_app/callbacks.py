from dash import Input, Output, State, no_update
import dash_mantine_components as dmc

import base64

from .data import (
    update_size,
    get_grid_data,
)

from .upload_upd import upload_data


def register_callbacks(app):

    @app.callback(
        Output("dummy", "children"),
        Output(
            "upd-grid",
            "rowData",
            allow_duplicate=True,
        ),

        Input(
            "upd-grid",
            "cellValueChanged"
        ),

        State(
            "upd-id-store",
            "data"
        ),

        prevent_initial_call=True,
    )
    def save_grid_change(
        change,
        upd_id,
    ):

        if not change:
            return (
                no_update,
                no_update
            )

        if isinstance(
            change,
            list,
        ):
            change = change[-1]

        if (
            change.get(
                "colId"
            )
            != "chrt_id"
        ):
            return (
                no_update,
                no_update
            )

        row = change.get(
            "data",
            {},
        )

        row_id = row.get(
            "id"
        )

        raw_value = change.get(
            "value"
        )

        if (
            row_id is None
            or raw_value
            in [None, ""]
        ):
            return (
                no_update,
                no_update
            )

        chrt_id = (
            str(raw_value)
            .split("|")[0]
            .strip()
        )

        update_size(
            row_id,
            chrt_id,
        )

        df = get_grid_data(
            upd_id
        )

        return (
            "",
            df.to_dict(
                "records"
            ),
        )

    @app.callback(
        Output(
            "alert-slot",
            "children"
        ),

        Output(
            "upd-grid",
            "rowData",
            allow_duplicate=True,
        ),

        Input(
            "import-upd-btn",
            "n_clicks"
        ),

        State(
            "upd-upload",
            "contents"
        ),

        State(
            "upd-upload",
            "filename"
        ),

        State(
            "upd-id-store",
            "data"
        ),

        prevent_initial_call=True,
    )
    def upload_parquet_callback(
        n_clicks,
        contents,
        filename,
        upd_id,
    ):

        if not contents:

            return (
                dmc.Alert(
                    title="Файл не выбран",
                    children=(
                        "Выберите parquet"
                    ),
                    color="red",
                    variant="filled",
                    withCloseButton=True,
                ),
                no_update,
            )

        try:

            _, content_string = (
                contents.split(",")
            )

            parquet_bytes = (
                base64.b64decode(
                    content_string
                )
            )

            rows_count = (
                upload_data(
                    upd_id,
                    parquet_bytes,
                )
            )

            df = get_grid_data(
                upd_id
            )

            return (
                dmc.Alert(
                    title="Импорт завершён",
                    children=(
                        f"{filename} "
                        f"→ "
                        f"{rows_count:,} "
                        f"строк"
                    ),
                    color="green",
                    variant="filled",
                    withCloseButton=True,
                ),
                df.to_dict(
                    "records"
                ),
            )

        except Exception as e:

            return (
                dmc.Alert(
                    title="Ошибка импорта",
                    children=str(e),
                    color="red",
                    variant="filled",
                    withCloseButton=True,
                ),
                no_update,
            )

    @app.callback(
        Output(
            "upload-filename",
            "children"
        ),

        Input(
            "upd-upload",
            "filename"
        ),
    )
    def show_filename(
        filename
    ):

        if not filename:
            return (
                "Файл "
                "не выбран"
            )

        return (
            f"📄 "
            f"{filename}"
        )