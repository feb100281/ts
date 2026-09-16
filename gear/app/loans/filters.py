from __future__ import annotations

from datetime import date, timedelta

import dash_mantine_components as dmc
from dash import Input, Output, State, html, no_update
from dash_iconify import DashIconify

from .calculations import build_filter_options
from .components import action_button, filter_field, section_header
from .config import COLORS, STATUS_OPTIONS
from .data import get_loans_snapshot, get_min_borrowing_date
from .ids import (
    CONTRACT_TYPE_FILTER_ID,
    COUNTERPARTY_FILTER_ID,
    CURRENCY_FILTER_ID,
    DATA_SIGNAL_ID,
    HISTORY_DATE_RANGE_ID,
    LAST_UPDATE_ID,
    REFRESH_BTN_ID,
    REPORT_DATE_ID,
    RESET_FILTERS_BTN_ID,
    STATUS_FILTER_ID,
)


def get_default_report_date() -> str:
    return date.today().isoformat()


def get_default_history_range() -> list[str]:
    today = date.today()
    date_from = max(
        get_min_borrowing_date(),
        today - timedelta(days=365),
    )

    return [
        date_from.isoformat(),
        today.isoformat(),
    ]


def normalise_history_range(
    value,
) -> tuple[str, str]:
    default = get_default_history_range()

    if (
        not value
        or not isinstance(value, (list, tuple))
        or len(value) < 2
        or not value[0]
        or not value[1]
    ):
        return default[0], default[1]

    date_from = str(value[0])[:10]
    date_to = str(value[1])[:10]

    if date_from > date_to:
        date_from, date_to = (
            date_to,
            date_from,
        )

    return date_from, date_to


def build_filter_panel():
    return html.Div(
        style={
            "backgroundColor": COLORS["white"],
            "border": f"1px solid {COLORS['border']}",
            "padding": "14px",
        },
        children=[
            html.Div(
                style={
                    "display": "flex",
                    "justifyContent": "space-between",
                    "alignItems": "center",
                    "gap": "10px",
                    "marginBottom": "12px",
                },
                children=[
                    section_header(
                        "Параметры портфеля",
                        "Срез на дату и фильтры договоров",
                    ),
                    action_button(
                        component_id=RESET_FILTERS_BTN_ID,
                        label="Сбросить",
                        icon="solar:restart-linear",
                        color="gray",
                        variant="subtle",
                    ),
                ],
            ),
            html.Div(
                style={
                    "display": "grid",
                    "gridTemplateColumns": (
                        "repeat(6, minmax(170px, 1fr))"
                    ),
                    "gap": "8px",
                },
                children=[
                    filter_field(
                        icon="solar:calendar-date-linear",
                        title="Срез на дату",
                        subtitle="Состояние долга",
                        component=dmc.DateInput(
                            id=REPORT_DATE_ID,
                            value=get_default_report_date(),
                            valueFormat="DD.MM.YYYY",
                            clearable=False,
                            radius=0,
                            size="xs",
                        ),
                    ),
                    filter_field(
                        icon="solar:calendar-search-linear",
                        title="Период динамики",
                        subtitle="Графики движения",
                        component=dmc.DatePickerInput(
                            id=HISTORY_DATE_RANGE_ID,
                            type="range",
                            value=get_default_history_range(),
                            valueFormat="DD.MM.YYYY",
                            clearable=False,
                            radius=0,
                            size="xs",
                        ),
                    ),
                    filter_field(
                        icon="solar:buildings-2-linear",
                        title="Контрагент",
                        subtitle="Кредитор / заимодавец",
                        component=dmc.MultiSelect(
                            id=COUNTERPARTY_FILTER_ID,
                            data=[],
                            value=[],
                            searchable=True,
                            clearable=True,
                            placeholder="Все",
                            radius=0,
                            size="xs",
                        ),
                    ),
                    filter_field(
                        icon="solar:document-text-linear",
                        title="Тип договора",
                        subtitle="Вид обязательства",
                        component=dmc.MultiSelect(
                            id=CONTRACT_TYPE_FILTER_ID,
                            data=[],
                            value=[],
                            searchable=True,
                            clearable=True,
                            placeholder="Все",
                            radius=0,
                            size="xs",
                        ),
                    ),
                    filter_field(
                        icon="solar:dollar-minimalistic-linear",
                        title="Валюта",
                        subtitle="Валюта договора",
                        component=dmc.MultiSelect(
                            id=CURRENCY_FILTER_ID,
                            data=[],
                            value=[],
                            searchable=True,
                            clearable=True,
                            placeholder="Все",
                            radius=0,
                            size="xs",
                        ),
                    ),
                    filter_field(
                        icon="solar:shield-check-linear",
                        title="Статус",
                        subtitle="Срок погашения",
                        component=dmc.MultiSelect(
                            id=STATUS_FILTER_ID,
                            data=STATUS_OPTIONS,
                            value=[],
                            searchable=False,
                            clearable=True,
                            placeholder="Все",
                            radius=0,
                            size="xs",
                        ),
                    ),
                ],
            ),
        ],
    )


def register_filter_callbacks(app):
    @app.callback(
        Output(COUNTERPARTY_FILTER_ID, "data"),
        Output(CONTRACT_TYPE_FILTER_ID, "data"),
        Output(CURRENCY_FILTER_ID, "data"),
        Input(DATA_SIGNAL_ID, "data"),
        Input(REPORT_DATE_ID, "value"),
    )
    def update_filter_options(
        data_signal,
        report_date,
    ):
        if not report_date:
            return [], [], []

        df = get_loans_snapshot(
            str(report_date)[:10]
        )

        return (
            build_filter_options(
                df,
                "counterparty_name",
            ),
            build_filter_options(
                df,
                "contract_type",
            ),
            build_filter_options(
                df,
                "currency",
            ),
        )

    @app.callback(
        Output(COUNTERPARTY_FILTER_ID, "value"),
        Output(CONTRACT_TYPE_FILTER_ID, "value"),
        Output(CURRENCY_FILTER_ID, "value"),
        Output(STATUS_FILTER_ID, "value"),
        Input(RESET_FILTERS_BTN_ID, "n_clicks"),
        prevent_initial_call=True,
    )
    def reset_filters(n_clicks):
        if not n_clicks:
            return (
                no_update,
                no_update,
                no_update,
                no_update,
            )

        return [], [], [], []
