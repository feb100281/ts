# #  gear/app/daily_sales/stocks/dashboard_stock/callbacks.py
# """Небольшие callbacks верхнего уровня dashboard."""

# from dash import dcc, Input, Output, State, no_update

# from ..transfer_excel import build_warehouses_excel
# from .ids import (
#     STOCK_WAREHOUSES_GRID_ID,
#     STOCK_PRODUCTS_COUNT_ID,
#     STOCK_WAREHOUSES_DOWNLOAD_BTN_ID,
#     STOCK_WAREHOUSES_DOWNLOAD_ID,
#     STOCK_CONTEXT_ID,
# )


# def register_main_callbacks(app):
#     @app.callback(
#         Output(
#             STOCK_PRODUCTS_COUNT_ID,
#             "children",
#         ),
#         Input(
#             STOCK_WAREHOUSES_GRID_ID,
#             "virtualRowData",
#         ),
#     )
#     def update_warehouse_count(
#         rows,
#     ):
#         return (
#             f"Показано складов: "
#             f"{len(rows or [])}"
#         )

#     @app.callback(
#         Output(
#             STOCK_WAREHOUSES_DOWNLOAD_ID,
#             "data",
#         ),
#         Input(
#             STOCK_WAREHOUSES_DOWNLOAD_BTN_ID,
#             "n_clicks",
#         ),
#         State(
#             STOCK_WAREHOUSES_GRID_ID,
#             "virtualRowData",
#         ),
#         State(
#             STOCK_CONTEXT_ID,
#             "data",
#         ),
#         prevent_initial_call=True,
#     )
#     def download_warehouses(
#         n_clicks,
#         rows,
#         context,
#     ):
#         if not n_clicks:
#             return no_update

#         context = context or {}

#         try:
#             content, filename = (
#                 build_warehouses_excel(
#                     rows=rows,
#                     report_date=context.get(
#                         "report_date"
#                     ),
#                 )
#             )
#         except ValueError:
#             return no_update

#         return dcc.send_bytes(
#             content,
#             filename,
#         )



#  gear/app/daily_sales/stocks/dashboard_stock/callbacks.py
"""Небольшие callbacks верхнего уровня dashboard."""

from dash import dcc, Input, Output, State, no_update

from ..transfer_excel import build_warehouses_excel
from ..incident_loss_export import (
    build_incident_loss_excel,
    build_incident_cover_letter_pdf,
)
from .incidents_panel import get_incident_events
from .ids import (
    STOCK_WAREHOUSES_GRID_ID,
    STOCK_PRODUCTS_COUNT_ID,
    STOCK_WAREHOUSES_DOWNLOAD_BTN_ID,
    STOCK_WAREHOUSES_DOWNLOAD_ID,
    STOCK_CONTEXT_ID,
    STOCK_INCIDENT_EXCEL_BTN_ID,
    STOCK_INCIDENT_EXCEL_DOWNLOAD_ID,
    STOCK_INCIDENT_PDF_BTN_ID,
    STOCK_INCIDENT_PDF_DOWNLOAD_ID,
)


def register_main_callbacks(app):
    @app.callback(
        Output(
            STOCK_PRODUCTS_COUNT_ID,
            "children",
        ),
        Input(
            STOCK_WAREHOUSES_GRID_ID,
            "virtualRowData",
        ),
    )
    def update_warehouse_count(
        rows,
    ):
        return (
            f"Показано складов: "
            f"{len(rows or [])}"
        )

    @app.callback(
        Output(
            STOCK_WAREHOUSES_DOWNLOAD_ID,
            "data",
        ),
        Input(
            STOCK_WAREHOUSES_DOWNLOAD_BTN_ID,
            "n_clicks",
        ),
        State(
            STOCK_WAREHOUSES_GRID_ID,
            "virtualRowData",
        ),
        State(
            STOCK_CONTEXT_ID,
            "data",
        ),
        prevent_initial_call=True,
    )
    def download_warehouses(
        n_clicks,
        rows,
        context,
    ):
        if not n_clicks:
            return no_update

        context = context or {}

        try:
            content, filename = (
                build_warehouses_excel(
                    rows=rows,
                    report_date=context.get(
                        "report_date"
                    ),
                )
            )
        except ValueError:
            return no_update

        return dcc.send_bytes(
            content,
            filename,
        )

    @app.callback(
        Output(
            STOCK_INCIDENT_EXCEL_DOWNLOAD_ID,
            "data",
        ),
        Input(
            STOCK_INCIDENT_EXCEL_BTN_ID,
            "n_clicks",
        ),
        prevent_initial_call=True,
    )
    def download_incident_loss_excel(
        n_clicks,
    ):
        if not n_clicks:
            return no_update

        events = get_incident_events()

        if not events:
            return no_update

        content, filename = build_incident_loss_excel(events)

        return dcc.send_bytes(
            content,
            filename,
        )

    @app.callback(
        Output(
            STOCK_INCIDENT_PDF_DOWNLOAD_ID,
            "data",
        ),
        Input(
            STOCK_INCIDENT_PDF_BTN_ID,
            "n_clicks",
        ),
        prevent_initial_call=True,
    )
    def download_incident_cover_letter(
        n_clicks,
    ):
        if not n_clicks:
            return no_update

        events = get_incident_events()

        if not events:
            return no_update

        content, filename = build_incident_cover_letter_pdf(events)

        return dcc.send_bytes(
            content,
            filename,
        )
