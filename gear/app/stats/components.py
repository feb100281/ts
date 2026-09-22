# gear/app/stats/components.py
from __future__ import annotations

import dash_mantine_components as dmc
from dash import html
from dash_iconify import DashIconify

from .config import COLORS


def section_header(
    title: str,
    subtitle: str | None = None,
):
    children = [
        dmc.Text(
            title,
            fw=700,
            size="sm",
            c=COLORS[
                "text"
            ],
        ),
    ]

    if subtitle:
        children.append(
            dmc.Text(
                subtitle,
                size="xs",
                c=COLORS[
                    "muted"
                ],
            )
        )

    return dmc.Stack(
        gap=1,
        children=children,
    )




def kpi_card(
    *,
    title: str,
    value_id: str,
    subtitle: str,
    icon: str,
    accent: str,
    tooltip: str | None = None,
):
    title_block = dmc.Group(
        gap=5,
        align="center",
        children=[
            dmc.Text(
                title,
                size="xs",
                fw=600,
                c=COLORS[
                    "muted"
                ],
            ),

            (
                dmc.Tooltip(
                    label=tooltip,
                    multiline=True,
                    w=320,
                    position="top",
                    withArrow=True,
                    radius=0,
                    children=DashIconify(
                        icon=(
                            "solar:"
                            "info-circle-linear"
                        ),
                        width=15,
                        color=COLORS[
                            "muted"
                        ],
                        style={
                            "cursor": (
                                "help"
                            ),
                        },
                    ),
                )
                if tooltip
                else None
            ),
        ],
    )

    return html.Div(
        style={
            "backgroundColor": (
                COLORS[
                    "white"
                ]
            ),
            "border": (
                f"1px solid "
                f"{COLORS['border']}"
            ),
            "borderLeft": (
                f"3px solid "
                f"{accent}"
            ),
            "padding": (
                "12px 14px"
            ),
            "minHeight": (
                "104px"
            ),
        },
        children=[
            dmc.Group(
                justify=(
                    "space-between"
                ),
                align="center",
                children=[
                    title_block,

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
                c=COLORS[
                    "text"
                ],
                mt=5,
            ),

            dmc.Text(
                subtitle,
                size="xs",
                c=COLORS[
                    "muted"
                ],
                mt=2,
            ),
        ],
    )


def chart_panel(
    *,
    title: str,
    subtitle: str,
    graph,
    insight=None,
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

        graph,
    ]

    if insight is not None:
        children.append(
            html.Div(
                style={
                    "marginTop": "8px",
                },
                children=insight,
            )
        )

    return html.Div(
        style={
            "backgroundColor": (
                COLORS[
                    "white"
                ]
            ),
            "border": (
                f"1px solid "
                f"{COLORS['border']}"
            ),
            "padding": "14px",
            "minWidth": 0,
        },
        children=children,
    )