# gear/app/daily_sales/wb_plan_monitor/layout.py
import dash_mantine_components as dmc
from dash import dcc
from dash_iconify import DashIconify

from .ids import (
    WB_PLAN_MODAL_ID,
    WB_PLAN_OPEN_BTN_ID,
    WB_PLAN_CONTENT_ID,
    WB_PLAN_DOWNLOAD_BTN_ID,
    WB_PLAN_DOWNLOAD_ID,
)
from .formatters import format_money_short, format_pct
from .charts import (
    build_progress_chart,
    build_monthly_chart,
    build_daily_chart,
    build_current_month_plan_chart,
)
from .components import (
    kpi_card,
    semi_table,
    daily_table,
    forecast_block,
    current_month_plan_table,
)

from .prophet_forecast import (
    prophet_tab_header,
    prophet_tab_panel,
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




# def wb_plan_modal():
#     return dmc.Modal(
#         id=WB_PLAN_MODAL_ID,
#         opened=False,
#         size="95%",
#         centered=True,
#         padding="md",
#         title=dmc.Group(
#             gap=8,
#             align="center",
#             wrap="nowrap",
#             children=[
#                 DashIconify(
#                     icon="solar:chart-square-linear",
#                     width=20,
#                     height=20,
#                     color="#228be6",
#                 ),
#                 dmc.Text(
#                     "Выполнение целевого оборота WB",
#                     fw=800,
#                     size="md",
#                 ),
#             ],
#         ),
#         children=[
#             dcc.Loading(
#                 type="cube",
#                 children=dmc.Box(
#                     id=WB_PLAN_CONTENT_ID,
#                     style={
#                         "minHeight": "650px",
#                     },
#                 ),
#             ),
#         ],
#         styles={
#             "title": {
#                 "width": "100%",
#             },
#             "content": {
#                 "height": "92vh",
#                 "maxHeight": "92vh",
#                 "borderRadius": "6px",
#                 "display": "flex",
#                 "flexDirection": "column",
#             },
#             "header": {
#                 "flex": "0 0 auto",
#                 "borderBottom": "1px solid #e9ecef",
#             },
#             "body": {
#                 "flex": "1 1 auto",
#                 "minHeight": "0",
#                 "overflowY": "auto",
#                 "overflowX": "hidden",
#             },
#         },
#     )
    
    
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
            dcc.Download(
                id=WB_PLAN_DOWNLOAD_ID,
            ),

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
    current_month = data["current_month"]
    totals = data["totals"]

    current_fact = current_semi["fact"] if current_semi else totals["fact"]
    current_plan = current_semi["plan"] if current_semi else totals["plan"]
    current_exec = current_semi["exec_pct"] if current_semi else totals["exec_pct"]
    current_exec_to_date = (
        current_semi["exec_to_date_pct"]
        if current_semi
        else current_exec
    )
    current_plan_to_date = (
        current_semi["plan_to_date"]
        if current_semi
        else current_plan
    )



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
                cols=5,
                spacing=8,
                children=[
                    kpi_card(
                        "План текущего периода",
                        format_money_short(
                            current_plan
                        ),
                        "полный план полугодия",
                        "indigo",
                        "solar:target-linear",
                    ),

                    kpi_card(
                        "Факт текущего периода",
                        format_money_short(
                            current_fact
                        ),
                        (
                            "по "
                            f"{data['report_date'].strftime('%d.%m.%Y')}"
                        ),
                        "blue",
                        "solar:wallet-money-linear",
                    ),

                    kpi_card(
                        "Выполнение полного плана",
                        format_pct(
                            current_exec
                        ),
                        "факт / полный план периода",
                        (
                            "green"
                            if current_exec >= 100
                            else "orange"
                        ),
                        "solar:chart-square-linear",
                    ),

                    kpi_card(
                        "Выполнение на текущую дату",
                        format_pct(
                            current_exec_to_date
                        ),
                        (
                            "план к дате: "
                            f"{format_money_short(current_plan_to_date)}"
                        ),
                        (
                            "green"
                            if current_exec_to_date >= 100
                            else "red"
                        ),
                        "solar:calendar-mark-linear",
                    ),

                    kpi_card(
                        "Осталось до полного плана",
                        format_money_short(
                            current_remaining
                        ),
                        (
                            "план уже закрыт"
                            if current_remaining <= 0
                            else "до плана полугодия"
                        ),
                        (
                            "orange"
                            if current_remaining > 0
                            else "green"
                        ),
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
                                "Текущий месяц",
                                value="current-month",
                                leftSection=DashIconify(
                                    icon="solar:calendar-minimalistic-linear",
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
                            
                            prophet_tab_header(),
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
                                        dmc.Group(
    justify="space-between",
    align="center",
    mb="xs",
    wrap="nowrap",
    children=[
        dmc.Text(
            "План / факт по месяцам",
            fw=800,
            size="sm",
        ),

        dmc.Button(
            "Скачать Excel",
            id=WB_PLAN_DOWNLOAD_BTN_ID,
            variant="outline",
            color="gray",
            radius=0,
            size="xs",
            leftSection=DashIconify(
                icon="material-symbols:download-rounded",
                width=17,
                color="#15803D",
            ),
            styles={
                "root": {
                    "height": "32px",
                    "backgroundColor": "#FFFFFF",
                    "border": "1px solid #D1D5DB",
                    "color": "#374151",
                    "fontWeight": 600,
                    "fontSize": "12px",
                    "paddingLeft": "12px",
                    "paddingRight": "14px",
                },
            },
        ),
    ],
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
    value="current-month",
    pt="sm",
    children=dmc.Stack(
        gap="sm",
        children=[
           dmc.SimpleGrid(
    cols=6,
    spacing="sm",
    children=[
        kpi_card(
            "План месяца",
            format_money_short(
                current_month["month_plan"]
            ),
            current_month["label"],
            "indigo",
            "solar:target-linear",
        ),

        kpi_card(
            "Факт месяца",
            format_money_short(
                current_month["fact_to_date"]
            ),
            (
                "по "
                f"{data['report_date'].strftime('%d.%m.%Y')}"
            ),
            "blue",
            "solar:wallet-money-linear",
        ),

        kpi_card(
            "Выполнено плана месяца",
            format_pct(
                current_month["month_exec_pct"]
            ),
            "факт / полный план месяца",
            (
                "green"
                if current_month["month_exec_pct"] >= 100
                else "blue"
            ),
            "solar:pie-chart-2-linear",
        ),

        kpi_card(
            "План на текущую дату",
            format_money_short(
                current_month["plan_to_date"]
            ),
            (
                f"{current_month['elapsed_days']} "
                f"из {current_month['days_in_month']} дней"
            ),
            "orange",
            "solar:calendar-mark-linear",
        ),

        kpi_card(
            "Выполнение на текущую дату",
            format_pct(
                current_month["exec_to_date_pct"]
            ),
            "факт / план к текущей дате",
            (
                "green"
                if current_month["exec_to_date_pct"] >= 100
                else "red"
            ),
            "solar:chart-square-linear",
        ),

        kpi_card(
            "Отклонение от графика",
            (
                "+"
                if current_month["delta_to_date"] >= 0
                else ""
            )
            + format_money_short(
                current_month["delta_to_date"]
            ),
            (
                "выше плана на дату"
                if current_month["delta_to_date"] >= 0
                else "ниже плана на дату"
            ),
            (
                "green"
                if current_month["delta_to_date"] >= 0
                else "red"
            ),
            "solar:graph-up-linear",
        ),
    ],
),
            dmc.Paper(
                withBorder=True,
                radius="sm",
                p="sm",
                children=[
                    dmc.Group(
                        justify="space-between",
                        align="center",
                        mb="xs",
                        children=[
                            dmc.Text(
                                (
                                    "Выполнение плана "
                                    "текущего месяца"
                                ),
                                fw=800,
                                size="sm",
                            ),

                            dmc.Badge(
                                current_month["label"],
                                color="blue",
                                variant="light",
                                radius="sm",
                            ),
                        ],
                    ),

                    dcc.Graph(
                        figure=(
                            build_current_month_plan_chart(
                                current_month
                            )
                        ),
                        config={
                            "displaylogo": False,
                            "toImageButtonOptions": {
                                "format": "png",
                                "filename": (
                                    "wb_current_month_plan"
                                ),
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
                        "План / факт по дням",
                        fw=800,
                        size="sm",
                        mb="xs",
                    ),

                    current_month_plan_table(
                        current_month
                    ),
                ],
            ),
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
                    
                    prophet_tab_panel(
                        report_date=data["report_date"],
                    ),
                ],
            ),
        ],
    )