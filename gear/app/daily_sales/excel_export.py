# # gear/app/daily_sales/excel_export.py
# from io import BytesIO

# import pandas as pd
# import dash_mantine_components as dmc
# from dash import dcc, Input, Output, State, ALL, no_update
# from dash_iconify import DashIconify
# from .excel_styles import apply_excel_style


# MAIN_EXCEL_DOWNLOAD_ID = "daily-sales-main-excel-download"
# DETAILS_EXCEL_DOWNLOAD_ID = "daily-sales-details-excel-download"


# def excel_button_main():
#     return [
#         dmc.Button(
#             "Excel",
#             id={"type": "main-dnl", "index": "excel"},
#             variant="light",
#             color="green",
#             radius=0,
#             size="xs",
#             leftSection=DashIconify(icon="vscode-icons:file-type-excel", width=18),
#         ),
#         dcc.Download(id=MAIN_EXCEL_DOWNLOAD_ID),
#     ]


# def excel_button_details():
#     return [
#         dmc.Button(
#             "Excel",
#             id={"type": "details-dnl", "index": "excel"},
#             variant="light",
#             color="green",
#             radius=0,
#             size="xs",
#             leftSection=DashIconify(icon="vscode-icons:file-type-excel", width=18),
#         ),
#         dcc.Download(id=DETAILS_EXCEL_DOWNLOAD_ID),
#     ]


# def _flatten_columns(column_defs):
#     result = []

#     for col in column_defs or []:
#         if "children" in col:
#             result.extend(_flatten_columns(col["children"]))
#             continue

#         field = col.get("field")
#         if not field:
#             continue

#         result.append(
#             {
#                 "field": field,
#                 "header": col.get("headerName", field),
#             }
#         )

#     return result


# def _make_excel(rows, column_defs, sheet_name="Данные"):
#     df = pd.DataFrame(rows or [])

#     columns = _flatten_columns(column_defs)

#     ordered_fields = [
#         col["field"]
#         for col in columns
#         if col["field"] in df.columns
#     ]

#     rename_map = {
#         col["field"]: col["header"]
#         for col in columns
#         if col["field"] in df.columns
#     }

#     if ordered_fields:
#         df = df[ordered_fields]

#     df = df.rename(columns=rename_map)

#     output = BytesIO()

#     with pd.ExcelWriter(output, engine="openpyxl") as writer:
#         df.to_excel(writer, index=False, sheet_name=sheet_name)

#         ws = writer.sheets[sheet_name]

#         numeric_columns = {
#             idx
#             for idx, column_name in enumerate(df.columns, start=1)
#             if pd.api.types.is_numeric_dtype(df[column_name])
#         }

#         apply_excel_style(
#             ws,
#             freeze_panes="A2",
#             numeric_columns=numeric_columns,
#         )

#     output.seek(0)
#     return output.read()



# def register_excel_export_callbacks(app, selected_dates_chips_id):
#     @app.callback(
#        Output(MAIN_EXCEL_DOWNLOAD_ID, "data"),
#         Input({"type": "main-dnl", "index": "xls"}, "n_clicks"),
#         State({"type": "dates_grid", "index": "1"}, "virtualRowData"),
#         State({"type": "dates_grid", "index": "1"}, "columnDefs"),
#         prevent_initial_call=True,
#         )
#     def export_main_excel(n_clicks, rows, column_defs):
#         if not n_clicks or not rows:
#             return no_update

#         content = _make_excel(
#             rows=rows,
#             column_defs=column_defs,
#             sheet_name="Продажи за период",
#         )

#         return dcc.send_bytes(
#             content,
#             filename="daily_sales.xlsx",
#         )

#     @app.callback(
#         Output(DETAILS_EXCEL_DOWNLOAD_ID, "data"),
#         Input({"type": "xls-dnl", "index": ALL}, "n_clicks"),
#         State(selected_dates_chips_id, "value"),
#         State({"type": "dates_grid", "index": "2"}, "virtualRowData"),
#         State({"type": "dates_grid", "index": "2"}, "columnDefs"),
#         prevent_initial_call=True,
#     )
#     def export_details_excel(n_clicks, date_value, rows, column_defs):
#         if not any(n_clicks or []) or not rows:
#             return no_update

    

#         content = _make_excel(
#             rows=rows,
#             column_defs=column_defs,
#             sheet_name="Детализация",
#         )

#         return dcc.send_bytes(
#                 content,
#                 filename=f"daily_details_{date_value}.xlsx",
#             )



from io import BytesIO

import pandas as pd
from dash import dcc, Input, Output, State, ALL, no_update

from .excel_styles import apply_excel_style


MAIN_EXCEL_DOWNLOAD_ID = "daily-sales-main-excel-download"
DETAILS_EXCEL_DOWNLOAD_ID = "daily-sales-details-excel-download"


def _flatten_columns(column_defs):
    result = []

    for col in column_defs or []:
        if "children" in col:
            result.extend(_flatten_columns(col["children"]))
            continue

        field = col.get("field")
        if not field:
            continue

        result.append(
            {
                "field": field,
                "header": col.get("headerName", field),
            }
        )

    return result


def _make_excel(
    rows,
    column_defs,
    sheet_name="Данные",
    freeze_panes="B2",
):
    df = pd.DataFrame(rows or [])

    columns = _flatten_columns(column_defs)

    ordered_fields = [
        col["field"]
        for col in columns
        if col["field"] in df.columns
    ]

    rename_map = {
        col["field"]: col["header"]
        for col in columns
        if col["field"] in df.columns
    }

    if ordered_fields:
        df = df[ordered_fields]

    df = df.rename(columns=rename_map)

    # USK всегда оставляем как текст,
    # чтобы Excel не делал 2 знака после запятой
    if "USK" in df.columns:
        df["USK"] = df["USK"].astype(str)

    output = BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)

        ws = writer.sheets[sheet_name]

        numeric_columns = {
            idx
            for idx, column_name in enumerate(df.columns, start=1)
            if column_name != "USK"
            and pd.api.types.is_numeric_dtype(df[column_name])
        }

        apply_excel_style(
            ws,
            freeze_panes=freeze_panes,
            numeric_columns=numeric_columns,
        )

    output.seek(0)
    return output.read()


def register_excel_export_callbacks(app, selected_dates_chips_id):
    @app.callback(
        Output(MAIN_EXCEL_DOWNLOAD_ID, "data"),
        Input({"type": "main-dnl", "index": "xls"}, "n_clicks"),
        State({"type": "dates_grid", "index": "1"}, "virtualRowData"),
        State({"type": "dates_grid", "index": "1"}, "columnDefs"),
        prevent_initial_call=True,
    )
    def export_main_excel(n_clicks, rows, column_defs):
        if not n_clicks or not rows:
            return no_update

        content = _make_excel(
            rows=rows,
            column_defs=column_defs,
            sheet_name="Продажи за период",
            freeze_panes="B2",
        )

        return dcc.send_bytes(
            content,
            filename="daily_sales.xlsx",
        )

    @app.callback(
        Output(DETAILS_EXCEL_DOWNLOAD_ID, "data"),
        Input({"type": "xls-dnl", "index": ALL}, "n_clicks"),
        State(selected_dates_chips_id, "value"),
        State({"type": "dates_grid", "index": "2"}, "virtualRowData"),
        State({"type": "dates_grid", "index": "2"}, "columnDefs"),
        prevent_initial_call=True,
    )
    def export_details_excel(n_clicks, date_value, rows, column_defs):
        if not any(n_clicks or []) or not rows:
            return no_update

        content = _make_excel(
            rows=rows,
            column_defs=column_defs,
            sheet_name="Детализация",
            freeze_panes="E2",
        )

        return dcc.send_bytes(
            content,
            filename=f"daily_details_{date_value}.xlsx",
        )