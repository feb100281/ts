# app/misc.py
import dash_mantine_components as dmc
from dash_iconify import DashIconify
import pandas as pd

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




def fancy_table(
    df: pd.DataFrame,
    title: str = None,
    precision: int = 0,
):

    table_df = df.copy().reset_index()

    table_df = table_df.fillna(0)

    for col in table_df.columns:

        if pd.api.types.is_numeric_dtype(
            table_df[col]
        ):
            table_df[col] = table_df[col].map(
                lambda x:
                f"{x:,.{precision}f}"
            )

    header = dmc.TableThead(
        dmc.TableTr(
            [
                dmc.TableTh(str(col))
                for col in table_df.columns
            ]
        )
    )

    body = dmc.TableTbody(
        [
            dmc.TableTr(
                [
                    dmc.TableTd(value)
                    for value in row
                ]
            )
            for row in table_df.values
        ]
    )

    table = dmc.Table(
        [
            header,
            body,
        ],
        striped=True,
        highlightOnHover=True,
        withTableBorder=True,
        withColumnBorders=True,
        horizontalSpacing="md",
        verticalSpacing="2",
    )

    if title:
        return dmc.Stack(
            [
                dmc.Title(
                    title,
                    order=4,
                ),
                table,
            ],
            gap="xs",
        )

    return table