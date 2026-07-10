# gear/app/daily_sales/wb_plan_monitor/layout.py
import dash_mantine_components as dmc
from dash import dcc
from dash_iconify import DashIconify

from .ids import (
    WB_PLAN_MODAL_ID,
    WB_PLAN_OPEN_BTN_ID,
    WB_PLAN_CONTENT_ID,
)
from .formatters import format_money_short, format_pct
from .charts import (
    build_progress_chart,
    build_monthly_chart,
    build_daily_chart,
)
from .components import (
    kpi_card,
    semi_table,
    daily_table,
    forecast_block,
)


def wb_plan_button():
    return dmc.Tooltip(
        label="Контроль выполнения плана WB",
        position="top",
        withArrow=True,
        children=dmc.ActionIcon(
            id=WB_PLAN_OPEN_BTN_ID,
            variant="light",
            color="indigo",
            radius="sm",
            size=32,
            children=DashIconify(
                icon="solar:monitor-smartphone-linear",
                width=18,
                height=18,
            ),
        ),
    )




def wb_plan_modal():
    return dmc.Modal(
        id=WB_PLAN_MODAL_ID,
        opened=False,
        size="95%",
        centered=True,
        padding="md",
        title=dmc.Group(
            gap=8,
            align="center",
            wrap="nowrap",
            children=[
                DashIconify(
                    icon="solar:chart-square-linear",
                    width=20,
                    height=20,
                    color="#228be6",
                ),
                dmc.Text(
                    "Выполнение целевого оборота WB",
                    fw=800,
                    size="md",
                ),
            ],
        ),
        children=[
            dcc.Loading(
                type="cube",
                children=dmc.Box(
                    id=WB_PLAN_CONTENT_ID,
                    style={
                        "minHeight": "650px",
                    },
                ),
            ),
        ],
        styles={
            "title": {
                "width": "100%",
            },
            "content": {
                "height": "92vh",
                "maxHeight": "92vh",
                "borderRadius": "6px",
                "display": "flex",
                "flexDirection": "column",
            },
            "header": {
                "flex": "0 0 auto",
                "borderBottom": "1px solid #e9ecef",
            },
            "body": {
                "flex": "1 1 auto",
                "minHeight": "0",
                "overflowY": "auto",
                "overflowX": "hidden",
            },
        },
    )
    

def build_modal_content(data):
    current_semi = data["current_semi"]
    totals = data["totals"]

    current_fact = current_semi["fact"] if current_semi else totals["fact"]
    current_plan = current_semi["plan"] if current_semi else totals["plan"]
    current_exec = current_semi["exec_pct"] if current_semi else totals["exec_pct"]
    current_remaining = (
        current_semi["remaining"]
        if current_semi
        else max(current_plan - current_fact, 0)
    )

    return dmc.Stack(
        gap="sm",
        children=[
            dmc.Group(
                justify="space-between",
                align="center",
                children=[
                    dmc.Text(
                        f"Данные на дату последней загрузки: {data['report_date'].strftime('%d.%m.%Y')}",
                        size="sm",
                        c="dimmed",
                        fw=600,
                    ),
                    dmc.Badge(
                        current_semi["label"] if current_semi else "Период не найден",
                        color="blue",
                        variant="light",
                        radius="sm",
                        size="lg",
                    ),
                ],
            ),

            dmc.SimpleGrid(
                cols=4,
                spacing="sm",
                children=[
                    kpi_card(
                        "План текущего периода",
                        format_money_short(current_plan),
                        "целевой оборот WB",
                        "indigo",
                        "solar:target-linear",
                    ),
                    kpi_card(
                        "Факт текущего периода",
                        format_money_short(current_fact),
                        "накопительно",
                        "blue",
                        "solar:wallet-money-linear",
                    ),
                    kpi_card(
                        "Выполнение",
                        format_pct(current_exec),
                        "факт / план",
                        "green" if current_exec >= 100 else "red",
                        "solar:chart-square-linear",
                    ),
                    kpi_card(
                        "Осталось до плана",
                        format_money_short(current_remaining),
                        "план уже закрыт" if current_remaining <= 0 else "до целевого оборота",
                        "orange" if current_remaining > 0 else "green",
                        "solar:flag-linear",
                    ),
                ],
            ),

   
            forecast_block(current_semi) if current_semi and current_semi["days_remaining"] > 0 else None,

            dmc.Tabs(
                value="chart",
                radius="sm",
                color="blue",
                children=[
                    dmc.TabsList(
                        [
                            dmc.TabsTab(
                                "График",
                                value="chart",
                                leftSection=DashIconify(
                                    icon="solar:chart-linear",
                                    width=16,
                                ),
                            ),
                            dmc.TabsTab(
                                "Полугодия",
                                value="semi",
                                leftSection=DashIconify(
                                    icon="solar:calendar-linear",
                                    width=16,
                                ),
                            ),
                            dmc.TabsTab(
                                "Дни месяца",
                                value="daily",
                                leftSection=DashIconify(
                                    icon="solar:calendar-date-linear",
                                    width=16,
                                ),
                            ),
                        ]
                    ),

                    dmc.TabsPanel(
                        value="chart",
                        pt="sm",
                        children=dmc.SimpleGrid(
                            cols=2,
                            spacing="sm",
                            children=[
                                dmc.Paper(
                                    withBorder=True,
                                    radius="sm",
                                    p="sm",
                                    children=[
                                        dmc.Text(
                                            "Прогресс текущего полугодия",
                                            fw=800,
                                            size="sm",
                                        ),
                                        dcc.Graph(
                                            figure=build_progress_chart(current_semi),
                                            config={"displayModeBar": False},
                                        ),
                                    ],
                                ),
                                dmc.Paper(
                                    withBorder=True,
                                    radius="sm",
                                    p="sm",
                                    children=[
                                        dmc.Text(
                                            "План / факт по месяцам",
                                            fw=800,
                                            size="sm",
                                        ),
                                        dcc.Graph(
                                            figure=build_monthly_chart(
                                                data["monthly_rows"]
                                            ),
                                            config={
                                                "displaylogo": False,
                                                "toImageButtonOptions": {
                                                    "format": "png",
                                                    "filename": "wb_plan_monthly",
                                                    "scale": 3,
                                                },
                                            },
                                        ),
                                    ],
                                ),
                            ],
                        ),
                    ),

                    dmc.TabsPanel(
                        value="semi",
                        pt="sm",
                        children=dmc.Paper(
                            withBorder=True,
                            radius="sm",
                            p="sm",
                            children=[
                                dmc.Text(
                                    "Выполнение по полугодиям",
                                    fw=800,
                                    size="sm",
                                    mb="xs",
                                ),
                                semi_table(data["semi_rows"]),
                            ],
                        ),
                    ),

       
                    
                    
                    dmc.TabsPanel(
    value="daily",
    pt="sm",
    children=dmc.Stack(
        gap="sm",
        children=[
            dmc.Paper(
                withBorder=True,
                radius="sm",
                p="sm",
                children=[
                    dmc.Text(
                        "Динамика по дням текущего месяца",
                        fw=800,
                        size="sm",
                    ),
                    dcc.Graph(
                        figure=build_daily_chart(data["daily_rows"]),
                        style={"height": "500px"},
                        config={
                            "displaylogo": False,
                            "toImageButtonOptions": {
                                "format": "png",
                                "filename": "wb_plan_daily",
                                "scale": 4,
                            },
                        },
                    ),
                ],
            ),
            dmc.Paper(
                withBorder=True,
                radius="sm",
                p="sm",
                children=[
                    dmc.Text(
                        "Последние 10 дней",
                        fw=800,
                        size="sm",
                        mb="xs",
                    ),
                    daily_table(data["daily_rows"]),
                ],
            ),
        ],
    ),
),
                ],
            ),
        ],
    )