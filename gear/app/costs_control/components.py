# gear/app/costs_control/components.py
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

    return dmc.Stack(
        gap=1,
        children=children,
    )


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
):
    return html.Div(
        style={
            "backgroundColor": COLORS["white"],
            "border": f"1px solid {COLORS['border']}",
            "padding": "14px",
            "minWidth": 0,
        },
        children=[
            section_header(
                title,
                subtitle,
            ),
            html.Div(
                style={"height": "10px"},
            ),
            graph,
        ],
    )


def empty_state(
    text: str = "Нет данных для отображения",
):
    return dmc.Center(
        h=300,
        children=dmc.Stack(
            align="center",
            gap=6,
            children=[
                DashIconify(
                    icon="solar:document-text-linear",
                    width=30,
                    color=COLORS["muted"],
                ),
                dmc.Text(
                    text,
                    size="sm",
                    c=COLORS["muted"],
                ),
            ],
        ),
    )