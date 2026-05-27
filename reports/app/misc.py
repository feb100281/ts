# app/misc.py
import dash_mantine_components as dmc
from dash_iconify import DashIconify


""" 
Сюда давай пихать функции которые используют все слайды
"""


# Напимер карточки c paper


def paper_card(
    title,
    content=None,
    **kwargs,
):

    children = [
        dmc.Group(
            [title],
        ),
        dmc.Space(h=5),
        dmc.Divider(size="xs"),
        dmc.Space(h=10),
    ]

    if content is not None:
        children.append(content)

    return dmc.Paper(
        p="sm",
        radius="md",
        shadow="xs",
        withBorder=True,
        children=children,
        **kwargs,
    )


def fancy_numbers(
    big_number, description, icon: DashIconify = None, badge=None, **kwargs
):
    children = [
        icon,
        dmc.Stack(
            [
                dmc.Group(
                    [
                        dmc.Text(
                            big_number,
                            size="lg",
                        ),
                        badge,
                    ],
                    align="flex-start",
                    gap=2,
                ),
                dmc.Text(description, size="xs", c="dimmed"),
            ],
            gap=0,
        ),
    ]
    return dmc.Group(
        children=children,
        # justify="space-between",
        align="flex-start",
        **kwargs,
    )
