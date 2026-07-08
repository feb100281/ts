# from io import BytesIO
# from datetime import date, timedelta

# import pandas as pd
# from dash import dcc, Input, Output, State, no_update

# from .data import get_stocks_export_data
# from .excel_styles import apply_excel_style
# from .ui import (
#     STOCKS_DATE_PICKER_ID,
#     STOCKS_EXPORT_BTN_ID,
#     STOCKS_EXPORT_DOWNLOAD_ID,
# )


# def _make_stocks_excel(df: pd.DataFrame) -> bytes:
#     if "USK" in df.columns:
#         df["USK"] = df["USK"].astype(str)

#     output = BytesIO()

#     with pd.ExcelWriter(output, engine="openpyxl") as writer:
#         df.to_excel(
#             writer,
#             index=False,
#             sheet_name="Остатки",
#         )

#         ws = writer.sheets["Остатки"]

#         numeric_columns = {
#             idx
#             for idx, column_name in enumerate(df.columns, start=1)
#             if column_name != "USK"
#             and pd.api.types.is_numeric_dtype(df[column_name])
#         }

#         apply_excel_style(
#             ws,
#             freeze_panes="A2",
#             numeric_columns=numeric_columns,
#         )

#     output.seek(0)
#     return output.read()


# def register_stock_excel_export_callbacks(app):
#     @app.callback(
#         Output(STOCKS_EXPORT_DOWNLOAD_ID, "data"),
#         Input(STOCKS_EXPORT_BTN_ID, "n_clicks"),
#         State(STOCKS_DATE_PICKER_ID, "value"),
#         prevent_initial_call=True,
#     )
#     def export_stocks_excel(n_clicks, report_date):
#         if not n_clicks:
#             return no_update

#         if not report_date:
#             report_date = date.today() - timedelta(days=1)

#         report_date = pd.to_datetime(report_date).date()

#         df = get_stocks_export_data(report_date)

#         if df.empty:
#             return no_update

#         content = _make_stocks_excel(df)

#         file_date = report_date.strftime("%Y-%m-%d")

#         return dcc.send_bytes(
#             content,
#             filename=f"stocks_{file_date}.xlsx",
#         )