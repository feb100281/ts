# gear/app/daily_sales/commercial_review/layout.py
"""
Кнопка и окно нового коммерческого обзора.

Сам отчёт в интерфейсе не показывается: он большой и его
читают в PDF. В окне только выбор даты и скачивание.
"""

from __future__ import annotations

from datetime import date, timedelta

import dash_mantine_components as dmc

from dash import dcc, html
from dash_iconify import DashIconify

from .config import (
    CR_CLOSE_BTN_ID,
    CR_DATE_ID,
    CR_DOWNLOAD_BTN_ID,
    CR_DOWNLOAD_ID,
    CR_LOADING_ID,
    CR_MODAL_ID,
    CR_OPEN_BTN_ID,
)


def commercial_review_controls():
    default_date = (
        date.today() - timedelta(days=1)
    ).isoformat()

    return html.Div(
        [
            dmc.Button(
                "Коммерческий обзор 2.0",
                id=CR_OPEN_BTN_ID,
                radius=0,
                variant="filled",
                color="teal",
                size="sm",
                leftSection=DashIconify(
                    icon=(
                        "material-symbols:"
                        "lab-profile-outline-rounded"
                    ),
                    width=18,
                ),
            ),

            dcc.Download(id=CR_DOWNLOAD_ID),

            dmc.Modal(
                id=CR_MODAL_ID,
                opened=False,
                size="md",
                radius=0,
                padding="lg",
                centered=True,
                withCloseButton=False,
                title=None,
                children=[
                    dmc.Stack(
                        gap="lg",
                        children=[
                            # =====================================
                            # ЗАГОЛОВОК
                            # =====================================
                            dmc.Group(
                                justify="space-between",
                                align="flex-start",
                                children=[
                                    dmc.Group(
                                        gap="sm",
                                        align="center",
                                        children=[
                                            dmc.ThemeIcon(
                                                radius=0,
                                                size=40,
                                                variant="filled",
                                                color="teal",
                                                children=DashIconify(
                                                    icon=(
                                                        "material-symbols:"
                                                        "lab-profile-outline-rounded"
                                                    ),
                                                    width=22,
                                                ),
                                            ),

                                            html.Div(
                                                [
                                                    dmc.Text(
                                                        (
                                                            "Коммерческий "
                                                            "обзор 2.0"
                                                        ),
                                                        fw=800,
                                                        size="lg",
                                                        c="#18352F",
                                                    ),

                                                    dmc.Text(
                                                        (
                                                            "17 страниц: "
                                                            "выводы, графики, "
                                                            "заказы FBS"
                                                        ),
                                                        size="xs",
                                                        c="dimmed",
                                                        mt=2,
                                                    ),
                                                ]
                                            ),
                                        ],
                                    ),

                                    dmc.ActionIcon(
                                        id=CR_CLOSE_BTN_ID,
                                        variant="subtle",
                                        color="gray",
                                        radius=0,
                                        size="lg",
                                        children=DashIconify(
                                            icon=(
                                                "material-symbols:"
                                                "close-rounded"
                                            ),
                                            width=21,
                                        ),
                                    ),
                                ],
                            ),

                            dmc.Divider(),

                            # =====================================
                            # ДАТА
                            # =====================================
                            dmc.DatePickerInput(
                                id=CR_DATE_ID,
                                label="Дата выпуска",
                                description=(
                                    "Все показатели считаются "
                                    "на конец выбранного дня."
                                ),
                                value=default_date,
                                valueFormat="DD.MM.YYYY",
                                radius=0,
                                clearable=False,
                                maxDate=default_date,
                                leftSection=DashIconify(
                                    icon=(
                                        "material-symbols:"
                                        "calendar-month-outline-rounded"
                                    ),
                                    width=18,
                                ),
                                styles={
                                    "input": {
                                        "height": "42px",
                                        "fontWeight": 600,
                                    },
                                },
                            ),

                            dmc.Button(
                                "Собрать и скачать PDF",
                                id=CR_DOWNLOAD_BTN_ID,
                                radius=0,
                                color="teal",
                                fullWidth=True,
                                leftSection=DashIconify(
                                    icon=(
                                        "material-symbols:"
                                        "download-rounded"
                                    ),
                                    width=18,
                                ),
                            ),

                            # =====================================
                            # СОСТОЯНИЕ
                            #
                            # dcc.Loading показывает спиннер, пока
                            # считается отчёт: сборка занимает
                            # десятки секунд, и без этого кажется,
                            # что кнопка не сработала.
                            # =====================================
                            dcc.Loading(
                                type="dot",
                                color="#2F6656",
                                children=html.Div(
                                    id=CR_LOADING_ID,
                                    children=dmc.Text(
                                        (
                                            "Сборка занимает до минуты: "
                                            "считаются продажи, финансовый "
                                            "результат, запасы, прогноз "
                                            "и заказы FBS."
                                        ),
                                        size="xs",
                                        c="dimmed",
                                        ta="center",
                                    ),
                                ),
                            ),
                        ],
                    ),
                ],
            ),
        ]
    )
