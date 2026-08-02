# gear/app/daily_sales/daily_brief/layout.py

from __future__ import annotations

from datetime import date, timedelta

import dash_mantine_components as dmc

from dash import (
    dcc,
    html,
)

from dash_iconify import DashIconify

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


def daily_brief_controls():
    """
    Кнопка открытия и компактное модальное окно
    формирования ежедневной деловой сводки.

    Сама сводка в интерфейсе не отображается.
    Пользователь только:

    - выбирает дату;
    - обновляет данные;
    - скачивает готовый PDF.
    """

    default_date = (
        date.today()
        - timedelta(days=1)
    ).isoformat()

    return html.Div(
        [
            # =========================================================
            # КНОПКА ОТКРЫТИЯ
            # =========================================================
            dmc.Button(
                "Коммерческий обзор",
                id=DAILY_BRIEF_OPEN_BTN_ID,
                radius=0,
                variant="outline",
                color="teal",
                size="sm",
                leftSection=DashIconify(
                    icon=(
                        "material-symbols:"
                        "newspaper-outline-rounded"
                    ),
                    width=18,
                ),
            ),

            # =========================================================
            # ХРАНИЛИЩЕ ПОДГОТОВЛЕННЫХ ДАННЫХ
            #
            # Визуально не отображается.
            # После кнопки «Обновить данные» здесь сохраняется payload.
            # =========================================================
            dcc.Store(
                id=DAILY_BRIEF_STORE_ID,
                data=None,
                storage_type="memory",
            ),

            # =========================================================
            # СКАЧИВАНИЕ PDF
            # =========================================================
            dcc.Download(
                id=DAILY_BRIEF_DOWNLOAD_ID,
            ),

            # =========================================================
            # КОМПАКТНОЕ МОДАЛЬНОЕ ОКНО
            # =========================================================
            dmc.Modal(
                id=DAILY_BRIEF_MODAL_ID,
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
                            # =========================================
                            # ЗАГОЛОВОК
                            # =========================================
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
                                                variant="light",
                                                color="teal",
                                                children=DashIconify(
                                                    icon=(
                                                        "material-symbols:"
                                                        "newspaper-outline-rounded"
                                                    ),
                                                    width=22,
                                                ),
                                            ),

                                            html.Div(
                                                [
                                                    dmc.Text(
                                                        (
                                                            "Деловая "
                                                            "сводка"
                                                        ),
                                                        fw=800,
                                                        size="lg",
                                                        c="#18352F",
                                                    ),

                                                    dmc.Text(
                                                        (
                                                            "Выберите дату "
                                                            "закрытого дня"
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
                                        id=DAILY_BRIEF_CLOSE_BTN_ID,
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

                            # =========================================
                            # ВЫБОР ДАТЫ
                            # =========================================
                            dmc.DatePickerInput(
                                id=DAILY_BRIEF_DATE_ID,
                                label="Дата выпуска",
                                description=(
                                    "Все показатели будут рассчитаны "
                                    "на конец выбранной даты."
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

                            # =========================================
                            # КНОПКИ
                            # =========================================
                            dmc.Group(
                                grow=True,
                                gap="sm",
                                children=[
                                    dmc.Button(
                                        "Обновить данные",
                                        id=(
                                            DAILY_BRIEF_REFRESH_BTN_ID
                                        ),
                                        radius=0,
                                        variant="default",
                                        leftSection=DashIconify(
                                            icon=(
                                                "material-symbols:"
                                                "refresh-rounded"
                                            ),
                                            width=18,
                                        ),
                                    ),

                                    dmc.Button(
                                        "Скачать PDF",
                                        id=(
                                            DAILY_BRIEF_DOWNLOAD_BTN_ID
                                        ),
                                        radius=0,
                                        color="teal",
                                        leftSection=DashIconify(
                                            icon=(
                                                "material-symbols:"
                                                "download-rounded"
                                            ),
                                            width=18,
                                        ),
                                    ),
                                ],
                            ),

                            dmc.Text(
                                (
                                    "Если данные уже загружены, можно "
                                    "сразу нажать «Скачать PDF»."
                                ),
                                size="xs",
                                c="dimmed",
                                ta="center",
                            ),
                        ],
                    ),
                ],
            ),
        ]
    )