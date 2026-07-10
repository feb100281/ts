# gear/app/daily_sales/wb_plan_monitor/callbacks.py
import dash_mantine_components as dmc
from dash import Input, Output, State
from dash_iconify import DashIconify

from .ids import (
    WB_PLAN_MODAL_ID,
    WB_PLAN_OPEN_BTN_ID,
    WB_PLAN_CONTENT_ID,
)
from .data import build_plan_analysis
from .layout import build_modal_content


def register_wb_plan_callbacks(app):
    @app.callback(
        Output(WB_PLAN_MODAL_ID, "opened"),
        Input(WB_PLAN_OPEN_BTN_ID, "n_clicks"),
        State(WB_PLAN_MODAL_ID, "opened"),
        prevent_initial_call=True,
    )
    def open_wb_plan_modal(n_clicks, opened):
        return True

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
                "Нет данных для расчета выполнения плана WB. Проверь BUDGET_VERSION_ID, план в budget_gl и факт в cf_to_csv.",
                color="red",
                variant="light",
                radius="sm",
                icon=DashIconify(
                    icon="solar:danger-triangle-linear",
                    width=20,
                ),
            )

        return build_modal_content(data)