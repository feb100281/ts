# gear/app/daily_sales/ai_analysis/callbacks.py
from __future__ import annotations

from datetime import date

import dash_mantine_components as dmc
from dash import Input, Output, State
from dash_iconify import DashIconify

from .components import build_analysis_content
from .data import (
    get_compare_period,
    get_mtd_qtd_ytd,
    get_period_comparison,
    get_entity_analysis,
    get_product_analysis,
)
from .engine import (
    build_analysis_payload,
    build_entity_summary,
    build_product_summary,
    build_recommendations,
)
from .ids import (
    AI_ANALYSIS_MODAL_ID,
    AI_ANALYSIS_OPEN_BTN_ID,
    AI_ANALYSIS_PERIOD_ID,
    AI_ANALYSIS_COMPARE_MODE_ID,
    AI_ANALYSIS_RUN_BTN_ID,
    AI_ANALYSIS_CONTENT_ID,
)

from ..wb_plan_monitor.data import build_plan_analysis


def register_ai_analysis_callbacks(app):
    @app.callback(
        Output(AI_ANALYSIS_MODAL_ID, "opened"),
        Input(AI_ANALYSIS_OPEN_BTN_ID, "n_clicks"),
        State(AI_ANALYSIS_MODAL_ID, "opened"),
        prevent_initial_call=True,
    )
    def open_ai_analysis_modal(n_clicks, opened):
        return True

    @app.callback(
        Output(AI_ANALYSIS_CONTENT_ID, "children"),
        Input(AI_ANALYSIS_RUN_BTN_ID, "n_clicks"),
        State(AI_ANALYSIS_PERIOD_ID, "value"),
        State(AI_ANALYSIS_COMPARE_MODE_ID, "value"),
        prevent_initial_call=True,
    )
    def run_ai_analysis(
        n_clicks,
        period_value,
        compare_mode,
    ):
        if not period_value or len(period_value) != 2:
            return dmc.Alert(
                "Выберите начало и конец периода анализа.",
                title="Период не выбран",
                color="orange",
                variant="light",
                radius="sm",
                icon=DashIconify(
                    icon="solar:calendar-linear",
                    width=20,
                ),
            )

        start_date = date.fromisoformat(str(period_value[0])[:10])
        end_date = date.fromisoformat(str(period_value[1])[:10])

        if end_date < start_date:
            return dmc.Alert(
                "Дата окончания не может быть раньше даты начала.",
                title="Некорректный период",
                color="red",
                variant="light",
                radius="sm",
            )

        compare_start, compare_end = get_compare_period(
            start_date=start_date,
            end_date=end_date,
            compare_mode=compare_mode,
        )

        period_data = get_period_comparison(
            start_date=start_date,
            end_date=end_date,
            compare_start=compare_start,
            compare_end=compare_end,
        )

        period_rows = get_mtd_qtd_ytd(end_date)
        plan_analysis = build_plan_analysis()

        payload = build_analysis_payload(
            current=period_data["current"],
            previous=period_data["previous"],
            daily_rows=period_data["daily"],
            period_rows=period_rows,
            plan_analysis=plan_analysis,
        )

        brand_rows = get_entity_analysis(
            start_date=start_date,
            end_date=end_date,
            compare_start=compare_start,
            compare_end=compare_end,
            dimension="brand",
        )

        category_rows = get_entity_analysis(
            start_date=start_date,
            end_date=end_date,
            compare_start=compare_start,
            compare_end=compare_end,
            dimension="category",
        )

        product_rows = get_product_analysis(
            start_date=start_date,
            end_date=end_date,
            compare_start=compare_start,
            compare_end=compare_end,
        )

        brand_summary = build_entity_summary(brand_rows)
        category_summary = build_entity_summary(category_rows)
        product_summary = build_product_summary(product_rows)

        recommendations = build_recommendations(
            brand_summary=brand_summary,
            category_summary=category_summary,
            product_summary=product_summary,
        )

        payload["daily_previous"] = period_data["daily_previous"]
        payload["brand_summary"] = brand_summary
        payload["category_summary"] = category_summary
        payload["product_summary"] = product_summary
        payload["recommendations"] = recommendations
        payload["stock_date"] = (
            product_rows[0]["stock_date"]
            if product_rows
            else None
        )

        return build_analysis_content(payload)
