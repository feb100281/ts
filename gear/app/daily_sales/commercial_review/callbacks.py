# gear/app/daily_sales/commercial_review/callbacks.py
from __future__ import annotations

from datetime import date, timedelta

import dash_mantine_components as dmc
import pandas as pd

from dash import Input, Output, State, dcc, no_update

from .config import (
    CR_CLOSE_BTN_ID,
    CR_DATE_ID,
    CR_DOWNLOAD_BTN_ID,
    CR_DOWNLOAD_ID,
    CR_LOADING_ID,
    CR_MODAL_ID,
    CR_OPEN_BTN_ID,
)


def _report_date(value) -> date:
    parsed = pd.to_datetime(value, errors="coerce")

    if pd.isna(parsed):
        return date.today() - timedelta(days=1)

    return parsed.date()


def register_commercial_review_callbacks(app):
    @app.callback(
        Output(CR_MODAL_ID, "opened"),
        Input(CR_OPEN_BTN_ID, "n_clicks"),
        prevent_initial_call=True,
    )
    def open_modal(n_clicks):
        return True if n_clicks else no_update

    @app.callback(
        Output(CR_MODAL_ID, "opened", allow_duplicate=True),
        Input(CR_CLOSE_BTN_ID, "n_clicks"),
        prevent_initial_call=True,
    )
    def close_modal(n_clicks):
        return False if n_clicks else no_update

    @app.callback(
        Output(CR_DOWNLOAD_ID, "data"),
        Output(CR_LOADING_ID, "children"),
        Input(CR_DOWNLOAD_BTN_ID, "n_clicks"),
        State(CR_DATE_ID, "value"),
        prevent_initial_call=True,
    )
    def download_report(n_clicks, value):
        if not n_clicks:
            return no_update, no_update

        report_date = _report_date(value)

        # Импорт внутри обработчика: weasyprint и matplotlib
        # тяжёлые, и тянуть их при старте приложения незачем.
        from .data import build_review_data
        from .report import build_commercial_review_pdf

        try:
            payload, fbs = build_review_data(report_date)
            content = build_commercial_review_pdf(payload, fbs=fbs)

        except Exception as error:
            return no_update, dmc.Alert(
                str(error),
                title="Отчёт собрать не удалось",
                color="red",
                radius=0,
            )

        note = dmc.Text(
            (
                f"Готово: обзор за "
                f"{report_date.strftime('%d.%m.%Y')}"
                + ("" if fbs else " · раздел FBS недоступен")
            ),
            size="xs",
            c="dimmed",
            ta="center",
        )

        return (
            dcc.send_bytes(
                content,
                (
                    "trendsetter_commercial_review_v2_"
                    f"{report_date.isoformat()}.pdf"
                ),
            ),
            note,
        )
