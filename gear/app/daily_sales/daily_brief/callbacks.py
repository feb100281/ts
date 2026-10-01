from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
from dash import Input, Output, State, dcc, no_update

from .data import build_daily_brief_payload
from .ids import (
    DAILY_BRIEF_CLOSE_BTN_ID,
    DAILY_BRIEF_DATE_ID,
    DAILY_BRIEF_DOWNLOAD_BTN_ID,
    DAILY_BRIEF_DOWNLOAD_ID,
    DAILY_BRIEF_MODAL_ID,
    DAILY_BRIEF_OPEN_BTN_ID,
    DAILY_BRIEF_REFRESH_BTN_ID,
    DAILY_BRIEF_STORE_ID,
)
from .pdf import build_daily_brief_pdf


def _normalize_report_date(report_date) -> date:
    selected = pd.to_datetime(report_date, errors="coerce")
    return date.today() - timedelta(days=1) if pd.isna(selected) else selected.date()


def _payload_matches_date(payload, report_date: date) -> bool:
    if not payload:
        return False
    payload_date = pd.to_datetime(payload.get("report_date"), errors="coerce")
    return pd.notna(payload_date) and payload_date.date() == report_date


def register_daily_brief_callbacks(app):
    @app.callback(Output(DAILY_BRIEF_MODAL_ID, "opened"), Input(DAILY_BRIEF_OPEN_BTN_ID, "n_clicks"), prevent_initial_call=True)
    def open_daily_brief_modal(n_clicks):
        return True if n_clicks else no_update

    @app.callback(Output(DAILY_BRIEF_MODAL_ID, "opened", allow_duplicate=True), Input(DAILY_BRIEF_CLOSE_BTN_ID, "n_clicks"), prevent_initial_call=True)
    def close_daily_brief_modal(n_clicks):
        return False if n_clicks else no_update

    @app.callback(Output(DAILY_BRIEF_STORE_ID, "data"), Input(DAILY_BRIEF_REFRESH_BTN_ID, "n_clicks"), State(DAILY_BRIEF_DATE_ID, "value"), prevent_initial_call=True)
    def refresh_daily_brief_data(n_clicks, report_date):
        if not n_clicks:
            return no_update
        return build_daily_brief_payload(_normalize_report_date(report_date))

    @app.callback(Output(DAILY_BRIEF_DOWNLOAD_ID, "data"), Input(DAILY_BRIEF_DOWNLOAD_BTN_ID, "n_clicks"), State(DAILY_BRIEF_DATE_ID, "value"), State(DAILY_BRIEF_STORE_ID, "data"), prevent_initial_call=True)
    def download_daily_brief_pdf(n_clicks, report_date, stored_payload):
        if not n_clicks:
            return no_update
        selected_date = _normalize_report_date(report_date)
        payload = stored_payload if _payload_matches_date(stored_payload, selected_date) else build_daily_brief_payload(selected_date)
        return dcc.send_bytes(build_daily_brief_pdf(payload), f"trendsetter_commercial_review_{selected_date.isoformat()}.pdf")
