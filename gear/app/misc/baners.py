import dash_mantine_components as dmc
from dash_iconify import DashIconify


def empty_df_banner():
    return dmc.Paper(
        children=[
            dmc.Stack(
                [
                    DashIconify(
                        icon="mdi:database-off",
                        width=64,
                        color="#ff6b6b",
                    ),

                    dmc.Title(
                        "Данных нет",
                        order=2,
                        ta="center",
                    ),

                    dmc.Text(
                        "Запрос вернул пустой DataFrame.\n"
                        "Либо фильтры слишком умные, либо данных реально нет.",
                        ta="center",
                        c="dimmed",
                    ),

                    dmc.Divider(),

                    dmc.Text(
                        "Shit in → shit out.",
                        ta="center",
                        c="red",
                        fw=700,
                    ),

                    dmc.Text(
                        "Попробуй ослабить фильтры или проверь источник данных.",
                        ta="center",
                        size="sm",
                        c="gray",
                    ),
                ],
                align="center",
                gap="sm",
            )
        ],
        shadow="md",
        radius="md",
        p="xl",
        withBorder=True,
        style={
            "maxWidth": "520px",
            "margin": "40px auto",
            "textAlign": "center",
        },
    )

import dash_mantine_components as dmc
from dash_iconify import DashIconify


def in_construction_banner():
    return dmc.Paper(
        children=[
            dmc.Stack(
                [
                    DashIconify(
                        icon="mdi:tools",
                        width=64,
                        color="#ffa94d",
                    ),

                    dmc.Title(
                        "Идёт работа",
                        order=2,
                        ta="center",
                    ),

                    dmc.Text(
                        "Я сейчас чиню/строю эту часть дашборда.\n"
                        "Данные и логика в процессе сборки.",
                        ta="center",
                        c="dimmed",
                    ),

                    dmc.Divider(),

                    dmc.Text(
                        "Без дедлайнов, пожалуйста.",
                        ta="center",
                        fw=700,
                        c="orange",
                    ),

                    dmc.Text(
                        "Я не ленюсь — я рефакторю реальность.\n"
                        "Приходите позже, будет красиво.",
                        ta="center",
                        size="sm",
                        c="gray",
                    ),
                ],
                align="center",
                gap="sm",
            )
        ],
        shadow="md",
        radius="md",
        p="xl",
        withBorder=True,
        style={
            "maxWidth": "540px",
            "margin": "40px auto",
            "textAlign": "center",
        },
    )