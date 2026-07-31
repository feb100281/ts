# # gear/app/daily_sales/wb_plan_monitor/callbacks.py
# import dash_mantine_components as dmc
# from dash import Input, Output, State
# from dash_iconify import DashIconify

# from .ids import (
#     WB_PLAN_MODAL_ID,
#     WB_PLAN_OPEN_BTN_ID,
#     WB_PLAN_CONTENT_ID,
# )
# from .data import build_plan_analysis
# from .layout import build_modal_content


# def register_wb_plan_callbacks(app):
#     @app.callback(
#         Output(WB_PLAN_MODAL_ID, "opened"),
#         Input(WB_PLAN_OPEN_BTN_ID, "n_clicks"),
#         State(WB_PLAN_MODAL_ID, "opened"),
#         prevent_initial_call=True,
#     )
#     def open_wb_plan_modal(n_clicks, opened):
#         return True

#     @app.callback(
#         Output(WB_PLAN_CONTENT_ID, "children"),
#         Input(WB_PLAN_MODAL_ID, "opened"),
#         prevent_initial_call=True,
#     )
#     def load_wb_plan_content(opened):
#         if not opened:
#             return ""

#         data = build_plan_analysis()

#         if not data:
#             return dmc.Alert(
#                 "Нет данных для расчета выполнения плана WB. Проверь BUDGET_VERSION_ID, план в budget_gl и факт в cf_to_csv.",
#                 color="red",
#                 variant="light",
#                 radius="sm",
#                 icon=DashIconify(
#                     icon="solar:danger-triangle-linear",
#                     width=20,
#                 ),
#             )

#         return build_modal_content(data)


# gear/app/daily_sales/wb_plan_monitor/callbacks.py

import dash_mantine_components as dmc
from dash import Input, Output, State, dcc
from dash.exceptions import PreventUpdate
from dash_iconify import DashIconify

from .ids import (
    WB_PLAN_MODAL_ID,
    WB_PLAN_OPEN_BTN_ID,
    WB_PLAN_CONTENT_ID,
    WB_PLAN_DOWNLOAD_BTN_ID,
    WB_PLAN_DOWNLOAD_ID,
)
from .data import build_plan_analysis
from .layout import build_modal_content
from .excel import (
    build_wb_plan_excel,
    get_wb_plan_excel_filename,
)

from .prophet_forecast import (
    register_prophet_callbacks,
)


def register_wb_plan_callbacks(app):
    
    register_prophet_callbacks(app)
    # ================================================================
    # Открытие модального окна
    # ================================================================

    @app.callback(
        Output(WB_PLAN_MODAL_ID, "opened"),
        Input(WB_PLAN_OPEN_BTN_ID, "n_clicks"),
        State(WB_PLAN_MODAL_ID, "opened"),
        prevent_initial_call=True,
    )
    def open_wb_plan_modal(n_clicks, opened):
        if not n_clicks:
            raise PreventUpdate

        return True

    # ================================================================
    # Загрузка содержимого модального окна
    # ================================================================

    @app.callback(
        Output(WB_PLAN_CONTENT_ID, "children"),
        Input(WB_PLAN_MODAL_ID, "opened"),
        prevent_initial_call=True,
    )
    def load_wb_plan_content(opened):
        if not opened:
            return ""

        data = build_plan_analysis()

        if not data:
            return dmc.Alert(
                (
                    "Нет данных для расчета выполнения плана WB. "
                    "Проверь BUDGET_VERSION_ID, план в budget_gl "
                    "и факт в sales.sales_long."
                ),
                color="red",
                variant="light",
                radius="sm",
                icon=DashIconify(
                    icon="solar:danger-triangle-linear",
                    width=20,
                ),
            )

        return build_modal_content(data)

    # ================================================================
    # Выгрузка плана / факта в Excel
    # ================================================================

    @app.callback(
        Output(WB_PLAN_DOWNLOAD_ID, "data"),
        Input(WB_PLAN_DOWNLOAD_BTN_ID, "n_clicks"),
        prevent_initial_call=True,
    )
    def download_wb_plan_excel(n_clicks):
        if not n_clicks:
            raise PreventUpdate

        data = build_plan_analysis()

        if not data:
            raise PreventUpdate

        excel_bytes = build_wb_plan_excel(data)
        filename = get_wb_plan_excel_filename(data)

        return dcc.send_bytes(
            excel_bytes,
            filename,
        )