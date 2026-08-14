# gear/app/costs_control/article_report/layout.py
from __future__ import annotations

import dash_mantine_components as dmc
from dash import dcc, html
from dash_iconify import DashIconify

from ..components import (
    action_button,
)
from ..config import COLORS

from .ids import (
    ARTICLE_REPORT_BTN_ID,
    ARTICLE_REPORT_CLOSE_BTN_ID,
    ARTICLE_REPORT_DOWNLOAD_BTN_ID,
    ARTICLE_REPORT_DOWNLOAD_ID,
    ARTICLE_REPORT_MODAL_ID,
    ARTICLE_REPORT_STATUS_ID,
    ARTICLE_REPORT_STORE_ID,
    ARTICLE_REPORT_UPLOAD_ID,
)


def build_article_report_button():
    """
    Кнопка в шапке.
    """

    return action_button(
        component_id=(
            ARTICLE_REPORT_BTN_ID
        ),
        label="Анализ артикулов",
        icon=(
            "solar:"
            "file-check-linear"
        ),
        color="teal",
        variant="light",
    )


def _build_upload_area():
    """
    Область загрузки файла.
    """

    return dcc.Upload(
        id=(
            ARTICLE_REPORT_UPLOAD_ID
        ),
        multiple=False,
        accept=(
            ".xlsx,"
            "application/vnd."
            "openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
        children=html.Div(
            style={
                "minHeight": "150px",
                "display": "flex",
                "alignItems": "center",
                "justifyContent": "center",
                "border": (
                    "1px dashed "
                    + COLORS.get(
                        "green",
                        "#3C7A67",
                    )
                ),
                "backgroundColor": (
                    COLORS.get(
                        "very_light_green",
                        "#F3F8F6",
                    )
                ),
                "cursor": "pointer",
                "padding": "22px",
            },
            children=[
                html.Div(
                    style={
                        "textAlign": "center",
                    },
                    children=[
                        html.Div(
                            style={
                                "width": "44px",
                                "height": "44px",
                                "margin": (
                                    "0 auto 12px"
                                ),
                                "display": "flex",
                                "alignItems": (
                                    "center"
                                ),
                                "justifyContent": (
                                    "center"
                                ),
                                "backgroundColor": (
                                    COLORS.get(
                                        "light_green",
                                        "#E7F1ED",
                                    )
                                ),
                                "border": (
                                    "1px solid "
                                    + COLORS.get(
                                        "border",
                                        "#D9DEE2",
                                    )
                                ),
                            },
                            children=(
                                DashIconify(
                                    icon=(
                                        "solar:"
                                        "cloud-upload-linear"
                                    ),
                                    width=24,
                                    height=24,
                                    color=(
                                        COLORS.get(
                                            "dark_green",
                                            "#2F6656",
                                        )
                                    ),
                                )
                            ),
                        ),

                        html.Div(
                            (
                                "Перетащите "
                                "Excel-файл сюда"
                            ),
                            style={
                                "fontSize": (
                                    "14px"
                                ),
                                "fontWeight": 600,
                                "color": (
                                    COLORS.get(
                                        "text",
                                        "#111827",
                                    )
                                ),
                            },
                        ),

                        html.Div(
                            (
                                "или нажмите "
                                "для выбора файла"
                            ),
                            style={
                                "marginTop": (
                                    "4px"
                                ),
                                "fontSize": (
                                    "12px"
                                ),
                                "color": (
                                    COLORS.get(
                                        "muted",
                                        "#6B7280",
                                    )
                                ),
                            },
                        ),

                        html.Div(
                            "Формат .xlsx",
                            style={
                                "marginTop": (
                                    "9px"
                                ),
                                "fontSize": (
                                    "11px"
                                ),
                                "color": (
                                    COLORS.get(
                                        "muted",
                                        "#6B7280",
                                    )
                                ),
                            },
                        ),
                    ],
                ),
            ],
        ),
    )


def build_article_report_modal():
    """
    Модальное окно.
    """

    return dmc.Modal(
        id=(
            ARTICLE_REPORT_MODAL_ID
        ),
        opened=False,
        centered=True,
        size="lg",
        radius=0,

        title=dmc.Group(
            gap=9,
            wrap="nowrap",
            children=[
                DashIconify(
                    icon=(
                        "solar:"
                        "document-add-linear"
                    ),
                    width=20,
                    height=20,
                    color=COLORS.get(
                        "dark_green",
                        "#2F6656",
                    ),
                ),

                dmc.Text(
                    (
                        "Анализ закупочных цен "
                        "по списку артикулов"
                    ),
                    fw=700,
                    size="md",
                ),
            ],
        ),

        styles={
            "header": {
                "borderBottom": (
                    "1px solid "
                    + COLORS.get(
                        "border",
                        "#D9DEE2",
                    )
                ),
            },
            "body": {
                "padding": "18px",
            },
        },

        children=[
            html.Div(
                style={
                    "padding": (
                        "12px 14px"
                    ),
                    "backgroundColor": (
                        COLORS.get(
                            "light_blue",
                            "#EDF4FA",
                        )
                    ),
                    "borderLeft": (
                        "3px solid "
                        + COLORS.get(
                            "blue",
                            "#3B6B8F",
                        )
                    ),
                    "marginBottom": (
                        "16px"
                    ),
                },
                children=[
                    html.Div(
                        (
                            "Требования "
                            "к файлу"
                        ),
                        style={
                            "fontSize": (
                                "12px"
                            ),
                            "fontWeight": (
                                700
                            ),
                        },
                    ),

                    html.Div(
                        [
                            (
                                "Excel-файл "
                                "должен содержать "
                            ),
                            html.Strong(
                                (
                                    "ровно "
                                    "один лист"
                                )
                            ),
                            " и ",
                            html.Strong(
                                (
                                    "одну "
                                    "колонку"
                                )
                            ),
                            (
                                " с названием "
                            ),
                            html.Code(
                                "Article"
                            ),
                            (
                                ". Article — "
                                "артикул поставщика "
                                "из УПД."
                            ),
                        ],
                        style={
                            "marginTop": (
                                "5px"
                            ),
                            "fontSize": (
                                "12px"
                            ),
                            "lineHeight": (
                                "18px"
                            ),
                        },
                    ),
                ],
            ),

            dcc.Loading(
                type="cube",
                color=COLORS.get(
                    "green",
                    "#3C7A67",
                ),
                children=(
                    _build_upload_area()
                ),
            ),

            html.Div(
                id=(
                    ARTICLE_REPORT_STATUS_ID
                ),
                style={
                    "marginTop": "14px",
                },
            ),

            html.Div(
                style={
                    "marginTop": "18px",
                    "paddingTop": "14px",
                    "borderTop": (
                        "1px solid "
                        + COLORS.get(
                            "border",
                            "#D9DEE2",
                        )
                    ),
                    "display": "flex",
                    "alignItems": "center",
                    "justifyContent": (
                        "flex-end"
                    ),
                    "gap": "8px",
                },
                children=[
                    # dmc.Button(
                    #     "Закрыть",
                    #     id=(
                    #         ARTICLE_REPORT_CLOSE_BTN_ID
                    #     ),
                    #     variant="default",
                    #     radius=0,
                    #     size="xs",
                    # ),

                    dmc.Button(
                        "Скачать анализ",
                        id=(
                            ARTICLE_REPORT_DOWNLOAD_BTN_ID
                        ),
                        leftSection=(
                            DashIconify(
                                icon=(
                                    "solar:"
                                    "file-download-linear"
                                ),
                                width=16,
                            )
                        ),
                        color="teal",
                        variant="filled",
                        radius=0,
                        size="xs",
                        disabled=True,
                    ),
                ],
            ),
        ],
    )


def build_article_report_components():
    """
    Служебные компоненты.
    """

    return html.Div(
        children=[
            dcc.Store(
                id=(
                    ARTICLE_REPORT_STORE_ID
                ),
                storage_type="memory",
            ),

            dcc.Download(
                id=(
                    ARTICLE_REPORT_DOWNLOAD_ID
                ),
            ),

            build_article_report_modal(),
        ],
    )