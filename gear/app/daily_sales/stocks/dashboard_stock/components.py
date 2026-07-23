"""Переиспользуемые UI-компоненты."""

import dash_mantine_components as dmc

from .helpers import fmt


def metric_card(label, value, suffix="шт", note=None):
    children = [
        dmc.Text(
            label,
            size="xs",
            c="dimmed",
            fw=500,
        ),
        dmc.Group(
            gap=6,
            align="baseline",
            mt=5,
            children=[
                dmc.Text(
                    fmt(value),
                    size="xl",
                    fw=700,
                    c="#18352F",
                ),
                dmc.Text(
                    suffix,
                    size="sm",
                    c="dimmed",
                ) if suffix else None,
            ],
        ),
    ]

    if note:
        children.append(
            dmc.Text(
                note,
                size="xs",
                c="dimmed",
                mt=2,
            )
        )

    return dmc.Paper(
        radius=0,
        p="md",
        style={
            "border": "1px solid #D6DFDB",
            "background": "#FFFFFF",
            "minHeight": "92px",
        },
        children=[
            child for child in children
            if child is not None
        ],
    )
