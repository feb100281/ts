# gear/app/daily_sales/ai_analysis/layout.py
from __future__ import annotations

from datetime import timedelta

import dash_mantine_components as dmc
from dash import dcc
from dash_iconify import DashIconify
from .instructions import build_analysis_instructions

from .config import DEFAULT_ANALYSIS_DAYS
from .data import get_last_sales_date
from .ids import (
    AI_ANALYSIS_MODAL_ID,
    AI_ANALYSIS_OPEN_BTN_ID,
    AI_ANALYSIS_PERIOD_ID,
    AI_ANALYSIS_COMPARE_MODE_ID,
    AI_ANALYSIS_RUN_BTN_ID,
    AI_ANALYSIS_CONTENT_ID,
)


def ai_analysis_button():
    return dmc.Tooltip(
        label="Умный анализ продаж",
        position="top",
        withArrow=True,
        children=dmc.ActionIcon(
            id=AI_ANALYSIS_OPEN_BTN_ID,
            variant="light",
            color="violet",
            radius="sm",
            size=32,
            children=DashIconify(
                icon="solar:magic-stick-3-linear",
                width=18,
                height=18,
            ),
        ),
    )


def ai_analysis_modal():
    report_date = get_last_sales_date()

    if report_date:
        start_date = report_date - timedelta(
            days=DEFAULT_ANALYSIS_DAYS - 1
        )
        default_period = [start_date, report_date]
    else:
        default_period = None

    return dmc.Modal(
        id=AI_ANALYSIS_MODAL_ID,
        opened=False,
        size="95%",
        centered=True,
        padding="md",
        title=dmc.Group(
            gap=8,
            align="center",
            wrap="nowrap",
            children=[
                DashIconify(
                    icon="solar:magic-stick-3-linear",
                    width=21,
                    height=21,
                    color="#7950f2",
                ),
                dmc.Text(
                    "Умный анализ продаж WB",
                    fw=800,
                    size="md",
                ),
            ],
        ),
        children=[
            dmc.Stack(
                gap="sm",
                children=[
                    dmc.Paper(
                        withBorder=True,
                        radius="sm",
                        p="sm",
                        children=[
                            dmc.Group(
                                justify="space-between",
                                align="end",
                                wrap="wrap",
                                gap="sm",
                                children=[
                                    dmc.Group(
                                        align="end",
                                        wrap="wrap",
                                        gap="sm",
                                        children=[
                                            dmc.DatePickerInput(
                                                id=AI_ANALYSIS_PERIOD_ID,
                                                type="range",
                                                label="Период анализа",
                                                value=default_period,
                                                valueFormat="DD.MM.YYYY",
                                                clearable=False,
                                                radius="sm",
                                                w=280,
                                            ),
                                            dmc.Select(
                                                id=AI_ANALYSIS_COMPARE_MODE_ID,
                                                label="Сравнить с",
                                                value="previous_period",
                                                clearable=False,
                                                radius="sm",
                                                w=260,
                                                data=[
                                                    {
                                                        "value": "previous_period",
                                                        "label": "Предыдущий период",
                                                    },
                                                    {
                                                        "value": "previous_week",
                                                        "label": "Неделя назад",
                                                    },
                                                    {
                                                        "value": "previous_month",
                                                        "label": "Месяц назад",
                                                    },
                                                    {
                                                        "value": "previous_year",
                                                        "label": "Год назад",
                                                    },
                                                ],
                                            ),
                                        ],
                                    ),
                                    dmc.Button(
                                        "Провести анализ",
                                        id=AI_ANALYSIS_RUN_BTN_ID,
                                        color="violet",
                                        radius="sm",
                                        leftSection=DashIconify(
                                            icon="solar:magic-stick-3-linear",
                                            width=17,
                                        ),
                                    ),
                                ],
                            ),
                        ],
                    ),
                    dcc.Loading(
                        type="cube",
                        children=dmc.Box(
                            id=AI_ANALYSIS_CONTENT_ID,
                            style={"minHeight": "480px"},
                            children=build_analysis_instructions(),
                        ),
                    ),
                ],
            ),
        ],
        styles={
            "content": {
                "height": "92vh",
                "maxHeight": "92vh",
                "display": "flex",
                "flexDirection": "column",
                "borderRadius": "6px",
            },
            "header": {
                "flex": "0 0 auto",
                "borderBottom": "1px solid #e9ecef",
            },
            "body": {
                "flex": "1 1 auto",
                "minHeight": "0",
                "overflowY": "auto",
                "overflowX": "hidden",
            },
        },
    )
