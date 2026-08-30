# gear/app/loans/selected_loan_panel.py

from __future__ import annotations

import dash_mantine_components as dmc
from dash import dcc, html
from dash_iconify import DashIconify

from .config import COLORS, PLOTLY_CONFIG
from .grid import build_transactions_grid
from .ids import (
    SELECTED_LOAN_CHART_ID,
    SELECTED_LOAN_META_ID,
    SELECTED_LOAN_TITLE_ID,
    TRANSACTIONS_TITLE_ID,
    RECONCILIATION_EXPORT_BTN_ID,
    RECONCILIATION_DOWNLOAD_ID,
)

from .components import action_button


# =====================================================================
# IDs блока документов
# =====================================================================


SELECTED_LOAN_DOCUMENTS_ID = (
    "loans-selected-loan-documents"
)

SELECTED_LOAN_DOCUMENTS_COUNT_ID = (
    "loans-selected-loan-documents-count"
)


# =====================================================================
# Пустой график
# =====================================================================


def _empty_selected_loan_figure():
    return {
        "data": [],
        "layout": {
            "template": "plotly_white",
            "paper_bgcolor": "#FFFFFF",
            "plot_bgcolor": "#FFFFFF",

            "xaxis": {
                "visible": False,
            },

            "yaxis": {
                "visible": False,
            },

            "annotations": [
                {
                    "text": (
                        "Выберите договор "
                        "в реестре выше"
                    ),
                    "x": 0.5,
                    "y": 0.5,
                    "xref": "paper",
                    "yref": "paper",
                    "showarrow": False,
                    "font": {
                        "size": 12,
                        "color": COLORS["muted"],
                    },
                }
            ],

            "margin": {
                "l": 20,
                "r": 20,
                "t": 20,
                "b": 20,
            },
        },
    }


# =====================================================================
# Документ
# =====================================================================


def document_row(
    *,
    title: str,
    subtitle: str | None = None,
    description: str | None = None,
    url: str | None = None,
):
    """
    Одна строка документа.

    Например:

    Договор № 12 от 01.03.2025
    Основной договор
                                  [Открыть]
    """

    left_children = [
        html.Div(
            title,
            style={
                "fontSize": "12px",
                "fontWeight": 600,
                "color": COLORS["text"],
                "lineHeight": "16px",
            },
        ),
    ]

    if subtitle:
        left_children.append(
            html.Div(
                subtitle,
                style={
                    "fontSize": "11px",
                    "color": COLORS["muted"],
                    "lineHeight": "15px",
                    "marginTop": "2px",
                },
            )
        )

    if description:
        left_children.append(
            html.Div(
                description,
                style={
                    "fontSize": "10px",
                    "color": COLORS["muted"],
                    "lineHeight": "14px",
                    "marginTop": "2px",
                },
            )
        )

    if url:
        action = dmc.Anchor(
            href=url,
            target="_blank",
            underline="never",
            children=dmc.Button(
                "Открыть",
                size="xs",
                radius=0,
                variant="outline",
                color="gray",
                leftSection=DashIconify(
                    icon="solar:square-arrow-right-up-linear",
                    width=14,
                ),
                styles={
                    "root": {
                        "height": "30px",
                        "fontSize": "11px",
                        "fontWeight": 500,
                    }
                },
            ),
        )
    else:
        action = dmc.Text(
            "Файл отсутствует",
            size="10px",
            c=COLORS["muted"],
        )

    return html.Div(
        style={
            "display": "grid",
            "gridTemplateColumns": (
                "34px minmax(0, 1fr) auto"
            ),
            "alignItems": "center",
            "gap": "10px",

            "padding": "9px 10px",

            "borderBottom": (
                f"1px solid {COLORS['border']}"
            ),

            "backgroundColor": COLORS["white"],
        },

        children=[
            # Иконка
            html.Div(
                style={
                    "width": "30px",
                    "height": "30px",

                    "display": "flex",
                    "alignItems": "center",
                    "justifyContent": "center",

                    "backgroundColor": (
                        COLORS["very_light_green"]
                    ),

                    "border": (
                        f"1px solid "
                        f"{COLORS['border']}"
                    ),
                },

                children=DashIconify(
                    icon=(
                        "solar:"
                        "document-text-linear"
                    ),
                    width=17,
                    color=COLORS["green"],
                ),
            ),

            # Информация
            html.Div(
                style={
                    "minWidth": 0,
                },
                children=left_children,
            ),

            # Кнопка
            action,
        ],
    )


# =====================================================================
# Пустой блок документов
# =====================================================================


def empty_documents_state():
    return html.Div(
        style={
            "padding": "20px",
            "textAlign": "center",
        },

        children=[
            DashIconify(
                icon="solar:folder-open-linear",
                width=26,
                color=COLORS["muted"],
            ),

            html.Div(
                "Документы по договору не найдены",
                style={
                    "marginTop": "6px",
                    "fontSize": "11px",
                    "color": COLORS["muted"],
                },
            ),
        ],
    )


# =====================================================================
# Панель документов
# =====================================================================


def build_documents_panel():
    return html.Div(
        style={
            "border": (
                f"1px solid "
                f"{COLORS['border']}"
            ),

            "backgroundColor": COLORS["white"],

            "marginTop": "10px",
        },

        children=[
            # =====================================================
            # Header
            # =====================================================

            html.Div(
                style={
                    "height": "42px",

                    "display": "flex",
                    "alignItems": "center",
                    "justifyContent": "space-between",

                    "gap": "10px",

                    "padding": "0 12px",

                    "backgroundColor": "#F8FAF9",

                    "borderBottom": (
                        f"1px solid "
                        f"{COLORS['border']}"
                    ),
                },

                children=[
                    html.Div(
                        style={
                            "display": "flex",
                            "alignItems": "center",
                            "gap": "7px",
                        },

                        children=[
                            DashIconify(
                                icon="solar:folder-with-files-linear",
                                width=17,
                                color=COLORS["green"],
                            ),

                            dmc.Text(
                                "Документы договора",
                                size="xs",
                                fw=700,
                                c=COLORS["text"],
                            ),
                        ],
                    ),

                    html.Div(
                        style={
                            "display": "flex",
                            "alignItems": "center",
                            "gap": "5px",

                            "padding": "4px 8px",

                            "backgroundColor": (
                                COLORS["very_light_green"]
                            ),

                            "border": (
                                f"1px solid "
                                f"{COLORS['border']}"
                            ),
                        },

                        children=[
                            DashIconify(
                                icon="solar:paperclip-linear",
                                width=14,
                                color=COLORS["green"],
                            ),

                            html.Span(
                                id=(
                                    SELECTED_LOAN_DOCUMENTS_COUNT_ID
                                ),
                                children="0 файлов",
                                style={
                                    "fontSize": "10px",
                                    "fontWeight": 600,
                                    "color": COLORS["dark_green"],
                                },
                            ),
                        ],
                    ),
                ],
            ),

            # =====================================================
            # Документы
            # =====================================================

            html.Div(
                id=SELECTED_LOAN_DOCUMENTS_ID,

                style={
                    "maxHeight": "240px",

                    "overflowY": "auto",
                    "overflowX": "hidden",
                },

                children=[
                    empty_documents_state()
                ],
            ),
        ],
    )


# =====================================================================
# Основная панель выбранного договора
# =====================================================================


def build_selected_loan_panel():
    return html.Div(
        style={
            "backgroundColor": COLORS["white"],

            "border": (
                f"1px solid "
                f"{COLORS['border']}"
            ),

            "padding": "14px",
        },

        children=[
            # =====================================================
            # Шапка договора
            # =====================================================

            html.Div(
                style={
                    "display": "flex",
                    "justifyContent": "space-between",
                    "alignItems": "flex-start",

                    "gap": "12px",

                    "paddingBottom": "12px",

                    "borderBottom": (
                        f"1px solid "
                        f"{COLORS['border']}"
                    ),
                },

                children=[
                    html.Div(
                        style={
                            "minWidth": 0,
                        },

                        children=[
                            dmc.Text(
                                id=SELECTED_LOAN_TITLE_ID,

                                children=(
                                    "Договор не выбран"
                                ),

                                fw=700,
                                size="sm",

                                c=COLORS["text"],
                            ),

                            dmc.Text(
                                id=SELECTED_LOAN_META_ID,

                                children=(
                                    "Выберите договор "
                                    "в реестре выше"
                                ),

                                size="xs",

                                c=COLORS["muted"],

                                mt=2,
                            ),
                        ],
                    ),
                ],
            ),

            # =====================================================
            # График
            # =====================================================

            html.Div(
                style={
                    "marginTop": "12px",
                },

                children=[
                    dcc.Graph(
                        id=SELECTED_LOAN_CHART_ID,

                        figure=(
                            _empty_selected_loan_figure()
                        ),

                        config={
                            **PLOTLY_CONFIG,

                            "toImageButtonOptions": {
                                "format": "png",
                                "filename": (
                                    "Динамика_выбранного_договора"
                                ),
                                "width": 1800,
                                "height": 900,
                                "scale": 2,
                            },
                        },

                        style={
                            "height": "390px",
                            "width": "100%",
                        },
                    ),
                ],
            ),

            # =====================================================
            # Документы
            # =====================================================

            build_documents_panel(),

            # =====================================================
            # История операций
            # =====================================================

            html.Div(
    style={
        "marginTop": "12px",
    },

    children=[
        # =========================================================
        # Header истории
        # =========================================================

        html.Div(
            style={
                "display": "flex",
                "alignItems": "center",
                "justifyContent": "space-between",
                "gap": "12px",

                "marginBottom": "9px",
            },

            children=[
                # -------------------------------------------------
                # Заголовок
                # -------------------------------------------------

                html.Div(
                    style={
                        "display": "flex",
                        "alignItems": "center",
                        "gap": "7px",
                        "minWidth": 0,
                    },

                    children=[
                        DashIconify(
                            icon="solar:history-linear",
                            width=17,
                            color=COLORS["green"],
                        ),

                        dmc.Text(
                            id=TRANSACTIONS_TITLE_ID,

                            children=(
                                "История операций"
                            ),

                            size="xs",
                            fw=700,
                            c=COLORS["text"],
                        ),
                    ],
                ),

                # -------------------------------------------------
                # Скачать акт
                # -------------------------------------------------

                action_button(
                    component_id=(
                        RECONCILIATION_EXPORT_BTN_ID
                    ),
                    label="Скачать сверку по договору",
                    icon=(
                        "solar:"
                        "file-download-linear"
                    ),
                    color="green",
                    variant="outline",
                ),
            ],
        ),

        # =========================================================
        # Download
        # =========================================================

        dcc.Download(
            id=RECONCILIATION_DOWNLOAD_ID
        ),

        # =========================================================
        # Grid
        # =========================================================

        build_transactions_grid(),
    ],
),
        ],
    )