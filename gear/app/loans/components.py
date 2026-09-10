# gear/app/loans/components.py
from __future__ import annotations

import dash_mantine_components as dmc
from dash import html
from dash_iconify import DashIconify

from .config import COLORS


def section_header(title: str, subtitle: str | None = None):
    children = [
        dmc.Text(
            title,
            fw=700,
            size="sm",
            c=COLORS["text"],
        ),
    ]

    if subtitle:
        children.append(
            dmc.Text(
                subtitle,
                size="xs",
                c=COLORS["muted"],
            )
        )

    return dmc.Stack(gap=1, children=children)


def action_button(
    *,
    component_id: str,
    label: str,
    icon: str,
    color: str = "green",
    variant: str = "light",
):
    return dmc.Button(
        id=component_id,
        children=label,
        leftSection=DashIconify(
            icon=icon,
            width=16,
        ),
        color=color,
        variant=variant,
        radius=0,
        size="xs",
        h=34,
    )


def kpi_card(
    *,
    title: str,
    value_id: str,
    subtitle: str,
    icon: str,
    accent: str,
):
    return html.Div(
        style={
            "backgroundColor": COLORS["white"],
            "border": f"1px solid {COLORS['border']}",
            "borderLeft": f"3px solid {accent}",
            "padding": "12px 14px",
            "minHeight": "104px",
        },
        children=[
            dmc.Group(
                justify="space-between",
                align="center",
                children=[
                    dmc.Text(
                        title,
                        size="xs",
                        fw=600,
                        c=COLORS["muted"],
                    ),
                    DashIconify(
                        icon=icon,
                        width=18,
                        color=accent,
                    ),
                ],
            ),
            dmc.Text(
                id=value_id,
                children="—",
                fw=700,
                size="xl",
                c=COLORS["text"],
                mt=5,
            ),
            dmc.Text(
                subtitle,
                size="xs",
                c=COLORS["muted"],
                mt=2,
            ),
        ],
    )


def chart_panel(
    *,
    title: str,
    subtitle: str,
    graph,
    insight_id: str | None = None,
):
    children = [
        section_header(
            title,
            subtitle,
        ),

        html.Div(
            style={
                "height": "10px",
            },
        ),

        html.Div(
            style={
                "height": "410px",
                "minHeight": "410px",
                "width": "100%",
                "minWidth": 0,
                "position": "relative",
            },
            children=graph,
        ),
    ]

    # -------------------------------------------------------------
    # Выводы
    # -------------------------------------------------------------

    if insight_id:
        children.append(
            insights_panel(
                component_id=insight_id,
            )
        )
    else:
        # Даже если выводы для графика
        # пока не реализованы,
        # оставляем такую же высоту.
        children.append(
            html.Div(
                style={
                    "height": "128px",
                    "minHeight": "128px",
                    "marginTop": "8px",
                },
            )
        )

    return html.Div(
        style={
            "backgroundColor": COLORS["white"],
            "border": (
                f"1px solid "
                f"{COLORS['border']}"
            ),
            "padding": "14px",

            "minWidth": 0,

            # Одинаковая высота карточек
            "height": "640px",

            "boxSizing": "border-box",
            "overflow": "hidden",
        },
        children=children,
    )
    

def filter_field(
    *,
    icon: str,
    title: str,
    subtitle: str,
    component,
):
    return html.Div(
        style={
            "minWidth": 0,
            "height": "100%",
            "padding": "10px 11px",
            "backgroundColor": "#FFFFFF",
            "border": f"1px solid {COLORS['border']}",
        },
        children=[
            html.Div(
                style={
                    "display": "flex",
                    "alignItems": "flex-start",
                    "gap": "7px",
                    "marginBottom": "8px",
                },
                children=[
                    DashIconify(
                        icon=icon,
                        width=16,
                        height=16,
                        color=COLORS["green"],
                        style={
                            "marginTop": "1px",
                            "flex": "0 0 auto",
                        },
                    ),
                    html.Div(
                        style={"minWidth": 0},
                        children=[
                            dmc.Text(
                                title,
                                size="xs",
                                fw=600,
                                c=COLORS["text"],
                            ),
                            dmc.Text(
                                subtitle,
                                size="10px",
                                c=COLORS["muted"],
                            ),
                        ],
                    ),
                ],
            ),
            component,
        ],
    )
    
    

def insights_panel(
    *,
    component_id: str,
):
    return html.Div(
        style={
            "height": "145px",
            "minHeight": "145px",
            "maxHeight": "145px",

            "backgroundColor": "#F8FAF9",

            "border": (
                f"1px solid "
                f"{COLORS['border']}"
            ),

            "borderBottom": (
                f"2px solid "
                f"{COLORS['border']}"
            ),

            "boxSizing": "border-box",

            # ВАЖНО:
            # внешний контейнер НЕ скроллится
            "overflow": "hidden",

            "display": "flex",
            "flexDirection": "column",
        },

        children=[
            # =====================================================
            # Закреплённый заголовок
            # =====================================================

            html.Div(
                style={
                    "height": "38px",
                    "minHeight": "38px",

                    "display": "flex",
                    "alignItems": "center",

                    "padding": "0 12px",

                    "backgroundColor": "#F8FAF9",

                    "borderBottom": (
                        f"1px solid "
                        f"{COLORS['border']}"
                    ),

                    "boxSizing": "border-box",

                    "flex": "0 0 auto",
                },

                children=[
                    dmc.Group(
                        gap=7,
                        wrap="nowrap",

                        children=[
                            DashIconify(
                                icon=(
                                    "solar:"
                                    "lightbulb-minimalistic-linear"
                                ),
                                width=17,
                                height=17,
                                color=COLORS["green"],
                            ),

                            dmc.Text(
                                "Автоматические выводы",
                                size="xs",
                                fw=700,
                                c=COLORS["text"],
                            ),
                        ],
                    ),
                ],
            ),

            # =====================================================
            # Скроллящаяся часть
            # =====================================================

            html.Div(
                style={
                    "flex": "1 1 auto",

                    "minHeight": 0,

                    "padding": (
                        "8px 12px 14px 12px"
                    ),

                    "overflowY": "auto",
                    "overflowX": "hidden",

                    "boxSizing": "border-box",
                },

                children=[
                    html.Div(
                        id=component_id,

                        children=dmc.Text(
                            "Анализ формируется…",
                            size="xs",
                            c=COLORS["muted"],
                        ),
                    ),
                ],
            ),
        ],
    )