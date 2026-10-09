# gear/app/daily_sales/ai_analysis/instructions.py
from __future__ import annotations

import dash_mantine_components as dmc
from dash_iconify import DashIconify


def instruction_step(
    number: str,
    title: str,
    description: str,
    icon: str,
    color: str,
):
    return dmc.Paper(
        withBorder=True,
        radius="sm",
        p="md",
        h="100%",
        style={
            "backgroundColor": "#ffffff",
            "borderColor": "#e9ecef",
        },
        children=[
            dmc.Group(
                align="flex-start",
                wrap="nowrap",
                gap="sm",
                children=[
                    dmc.ThemeIcon(
                        size=42,
                        radius="sm",
                        color=color,
                        variant="light",
                        children=DashIconify(
                            icon=icon,
                            width=21,
                            height=21,
                        ),
                    ),
                    dmc.Stack(
                        gap=4,
                        style={"flex": 1},
                        children=[
                            dmc.Group(
                                gap=7,
                                wrap="nowrap",
                                children=[
                                    dmc.Badge(
                                        number,
                                        size="sm",
                                        radius="sm",
                                        color=color,
                                        variant="filled",
                                    ),
                                    dmc.Text(
                                        title,
                                        fw=800,
                                        size="sm",
                                    ),
                                ],
                            ),
                            dmc.Text(
                                description,
                                size="xs",
                                c="dimmed",
                                lh=1.5,
                            ),
                        ],
                    ),
                ],
            ),
        ],
    )


def build_analysis_instructions():
    return dmc.Center(
        style={
            "minHeight": "480px",
            "padding": "32px 16px",
        },
        children=dmc.Stack(
            gap="lg",
            maw=980,
            w="100%",
            children=[
                dmc.Stack(
                    align="center",
                    gap=7,
                    children=[
                        dmc.ThemeIcon(
                            size=58,
                            radius="sm",
                            color="violet",
                            variant="light",
                            children=DashIconify(
                                icon="solar:magic-stick-3-linear",
                                width=29,
                                height=29,
                            ),
                        ),
                        dmc.Text(
                            "Подготовьте анализ продаж",
                            fw=900,
                            size="xl",
                            ta="center",
                        ),
                        dmc.Text(
                            (
                                "Выберите период и способ сравнения, "
                                "после чего запустите автоматический анализ."
                            ),
                            size="sm",
                            c="dimmed",
                            ta="center",
                            maw=620,
                        ),
                    ],
                ),

                dmc.SimpleGrid(
                    cols={
                        "base": 1,
                        "sm": 3,
                    },
                    spacing="sm",
                    children=[
                        instruction_step(
                            number="1",
                            title="Выберите период",
                            description=(
                                "Укажите даты, за которые необходимо "
                                "проанализировать продажи, возвраты, "
                                "товары и остатки."
                            ),
                            icon="solar:calendar-linear",
                            color="blue",
                        ),
                        instruction_step(
                            number="2",
                            title="Настройте сравнение",
                            description=(
                                "Выберите сопоставимый период: предыдущий "
                                "период, неделю, месяц или год назад."
                            ),
                            icon="solar:refresh-square-linear",
                            color="indigo",
                        ),
                        instruction_step(
                            number="3",
                            title="Запустите анализ",
                            description=(
                                "Нажмите «Провести анализ». Расчёт может "
                                "занять некоторое время — дождитесь "
                                "завершения загрузки."
                            ),
                            icon="solar:magic-stick-3-linear",
                            color="violet",
                        ),
                    ],
                ),

                dmc.Alert(
                    title="Что будет подготовлено",
                    color="violet",
                    variant="light",
                    radius="sm",
                    icon=DashIconify(
                        icon="solar:chart-square-linear",
                        width=20,
                    ),
                    children=dmc.Text(
                        (
                            "Динамика продаж, сравнение периодов, "
                            "выполнение плана WB, анализ ассортимента, "
                            "риски по запасам и дополнительные "
                            "аналитические выводы."
                        ),
                        size="sm",
                        lh=1.5,
                    ),
                ),
            ],
        ),
    )