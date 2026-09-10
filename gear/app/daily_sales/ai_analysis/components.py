# gear/app/daily_sales/ai_analysis/components.py
from __future__ import annotations

import dash_mantine_components as dmc
from dash import dcc
from dash_iconify import DashIconify
import dash_ag_grid as dag
from .entity_grid import entity_table

from .charts import (
    build_daily_comparison_chart,
    build_driver_chart,
    build_entity_delta_chart,
)
from .engine import compare_metrics
from .formatters import (
    change_color,
    change_icon,
    format_money,
    format_number,
    format_pct,
)


LEVEL_CONFIG = {
    "positive": {
        "color": "green",
        "icon": "solar:check-circle-linear",
    },
    "negative": {
        "color": "red",
        "icon": "solar:danger-circle-linear",
    },
    "warning": {
        "color": "orange",
        "icon": "solar:danger-triangle-linear",
    },
    "neutral": {
        "color": "gray",
        "icon": "solar:minus-circle-linear",
    },
    "info": {
        "color": "blue",
        "icon": "solar:info-circle-linear",
    },
}


def metric_card(
    title: str,
    value: str,
    change: float,
    subtitle: str,
    icon: str,
    color: str,
    inverse_change: bool = False,
):
    trend_color = change_color(change, inverse=inverse_change)
    trend_icon = change_icon(change, inverse=inverse_change)

    return dmc.Paper(
        withBorder=True,
        radius="sm",
        p="sm",
        style={"height": "100%"},
        children=[
            dmc.Group(
                justify="space-between",
                align="flex-start",
                wrap="nowrap",
                children=[
                    dmc.Stack(
                        gap=4,
                        children=[
                            dmc.Text(
                                title,
                                size="xs",
                                fw=700,
                                c="dimmed",
                            ),
                            dmc.Text(
                                value,
                                size="xl",
                                fw=800,
                                c="#212529",
                            ),
                            dmc.Group(
                                gap=4,
                                wrap="nowrap",
                                children=[
                                    DashIconify(
                                        icon=trend_icon,
                                        width=14,
                                        color=trend_color,
                                    ),
                                    dmc.Text(
                                        format_pct(change, signed=True),
                                        size="xs",
                                        fw=800,
                                        c=trend_color,
                                    ),
                                    dmc.Text(
                                        subtitle,
                                        size="xs",
                                        c="dimmed",
                                    ),
                                ],
                            ),
                        ],
                    ),
                    dmc.ThemeIcon(
                        variant="light",
                        color=color,
                        radius="sm",
                        size=36,
                        children=DashIconify(
                            icon=icon,
                            width=19,
                        ),
                    ),
                ],
            ),
        ],
    )


def finding_card(item: dict):
    cfg = LEVEL_CONFIG.get(item["level"], LEVEL_CONFIG["info"])

    return dmc.Paper(
        withBorder=True,
        radius="sm",
        p="sm",
        children=[
            dmc.Group(
                align="flex-start",
                wrap="nowrap",
                gap="sm",
                children=[
                    dmc.ThemeIcon(
                        variant="light",
                        color=cfg["color"],
                        radius="sm",
                        size=34,
                        children=DashIconify(
                            icon=cfg["icon"],
                            width=18,
                        ),
                    ),
                    dmc.Stack(
                        gap=2,
                        children=[
                            dmc.Text(
                                item["title"],
                                fw=800,
                                size="sm",
                            ),
                            dmc.Text(
                                item["text"],
                                size="sm",
                                c="dimmed",
                                lh=1.45,
                            ),
                        ],
                    ),
                ],
            ),
        ],
    )





def period_overview_table(period_rows: list[dict]):
    # ---------------------------------------------------------
    # Палитра
    # ---------------------------------------------------------
    positive_color = "#087f5b"
    positive_bg = "rgba(22, 101, 52, 0.09)"
    positive_border = "rgba(22, 101, 52, 0.22)"

    negative_color = "#B42318"
    negative_bg = "rgba(180, 35, 24, 0.08)"
    negative_border = "rgba(180, 35, 24, 0.20)"

    neutral_color = "#667085"
    neutral_bg = "#F2F4F7"
    neutral_border = "#E4E7EC"

    text_color = "#1D2939"
    muted_color = "#667085"
    header_bg = "#F8FAFC"
    border_color = "#E4E7EC"

    # ---------------------------------------------------------
    # Вспомогательные функции
    # ---------------------------------------------------------
    def period_date_label(start_date, end_date) -> str:
        if not start_date or not end_date:
            return "Период не указан"

        if start_date == end_date:
            return start_date.strftime("%d.%m.%Y")

        return (
            f"{start_date.strftime('%d.%m.%Y')} — "
            f"{end_date.strftime('%d.%m.%Y')}"
        )

    def get_change_style(
        value: float,
        inverse: bool = False,
    ) -> dict:
        value = float(value or 0)

        effective_value = -value if inverse else value

        if effective_value > 0:
            return {
                "color": positive_color,
                "backgroundColor": positive_bg,
                "border": f"1px solid {positive_border}",
            }

        if effective_value < 0:
            return {
                "color": negative_color,
                "backgroundColor": negative_bg,
                "border": f"1px solid {negative_border}",
            }

        return {
            "color": neutral_color,
            "backgroundColor": neutral_bg,
            "border": f"1px solid {neutral_border}",
        }

    def change_badge(
        value: float,
        text: str,
        inverse: bool = False,
    ):
        style = get_change_style(
            value=value,
            inverse=inverse,
        )

        return dmc.Box(
            style={
                "display": "inline-flex",
                "alignItems": "center",
                "justifyContent": "center",
                "minWidth": "72px",
                "padding": "4px 8px",
                "borderRadius": "4px",
                "fontSize": "12px",
                "fontWeight": 800,
                "lineHeight": 1.2,
                "whiteSpace": "nowrap",
                **style,
            },
            children=text,
        )

    def money_text(
        value: float,
        *,
        fw: int = 700,
        color: str = text_color,
    ):
        return dmc.Text(
            format_money(value),
            size="sm",
            fw=fw,
            c=color,
            ta="right",
            style={
                "whiteSpace": "nowrap",
                "fontVariantNumeric": "tabular-nums",
            },
        )

    def number_text(
        value: float,
        *,
        fw: int = 700,
    ):
        return dmc.Text(
            format_number(value),
            size="sm",
            fw=fw,
            c=text_color,
            ta="right",
            style={
                "whiteSpace": "nowrap",
                "fontVariantNumeric": "tabular-nums",
            },
        )

    def header_cell(
        title: str,
        subtitle: str | None = None,
        *,
        align: str = "right",
    ):
        children = [
            dmc.Text(
                title,
                size="xs",
                fw=800,
                c="#344054",
                ta=align,
                lh=1.2,
            ),
        ]

        if subtitle:
            children.append(
                dmc.Text(
                    subtitle,
                    size="10px",
                    c=muted_color,
                    ta=align,
                    lh=1.2,
                )
            )

        return dmc.TableTh(
            dmc.Stack(
                gap=2,
                align=(
                    "flex-end"
                    if align == "right"
                    else "flex-start"
                ),
                children=children,
            ),
            style={
                "padding": "10px 10px",
                "backgroundColor": header_bg,
                "borderBottom": f"1px solid {border_color}",
                "verticalAlign": "bottom",
                "whiteSpace": "nowrap",
            },
        )

    # ---------------------------------------------------------
    # Строки таблицы
    # ---------------------------------------------------------
    body = []

    for index, row in enumerate(period_rows):
        current = row["current"]
        previous = row["previous"]

        comparison = compare_metrics(
            current,
            previous,
        )

        revenue_change = float(
            comparison["revenue_change_pct"] or 0
        )

        return_rate_delta = float(
            comparison["return_rate_delta"] or 0
        )

        current_start = current.get(
            "start_date",
            row.get("start"),
        )
        current_end = current.get(
            "end_date",
            row.get("end"),
        )

        previous_start = previous.get(
            "start_date",
            row.get("compare_start"),
        )
        previous_end = previous.get(
            "end_date",
            row.get("compare_end"),
        )

        current_period_text = period_date_label(
            current_start,
            current_end,
        )

        previous_period_text = period_date_label(
            previous_start,
            previous_end,
        )

        return_rate = float(
            current.get("return_rate") or 0
        )

        if return_rate >= 20:
            return_rate_color = negative_color
            return_rate_bg = negative_bg
        elif return_rate >= 15:
            return_rate_color = "#B54708"
            return_rate_bg = "rgba(181, 71, 8, 0.08)"
        else:
            return_rate_color = text_color
            return_rate_bg = "transparent"

        row_background = (
            "#FFFFFF"
            if index % 2 == 0
            else "#FCFCFD"
        )

        body.append(
            dmc.TableTr(
                style={
                    "backgroundColor": row_background,
                    "transition": "background-color 120ms ease",
                },
                children=[
                    # -----------------------------------------
                    # Период
                    # -----------------------------------------
                    dmc.TableTd(
                        dmc.Stack(
                            gap=5,
                            children=[
                                dmc.Group(
                                    gap=7,
                                    wrap="nowrap",
                                    children=[
                                        dmc.Badge(
                                            row["label"],
                                            variant="light",
                                            radius="sm",
                                            size="sm",
                                            styles={
                                                "root": {
                                                    "backgroundColor": (
                                                        "rgba(49, 46, 129, 0.09)"
                                                    ),
                                                    "color": "#3730A3",
                                                    "border": (
                                                        "1px solid "
                                                        "rgba(49, 46, 129, 0.16)"
                                                    ),
                                                    "fontWeight": 800,
                                                }
                                            },
                                        ),
                                        dmc.Text(
                                            row["title"],
                                            size="sm",
                                            fw=800,
                                            c=text_color,
                                            style={
                                                "whiteSpace": "nowrap",
                                            },
                                        ),
                                    ],
                                ),

                                dmc.Stack(
                                    gap=2,
                                    children=[
                                        dmc.Group(
                                            gap=5,
                                            wrap="nowrap",
                                            children=[
                                                dmc.Text(
                                                    "Текущий:",
                                                    size="10px",
                                                    fw=700,
                                                    c=muted_color,
                                                ),
                                                dmc.Text(
                                                    current_period_text,
                                                    size="10px",
                                                    fw=700,
                                                    c=text_color,
                                                    style={
                                                        "whiteSpace": "nowrap",
                                                        "fontVariantNumeric": (
                                                            "tabular-nums"
                                                        ),
                                                    },
                                                ),
                                            ],
                                        ),
                                        dmc.Group(
                                            gap=5,
                                            wrap="nowrap",
                                            children=[
                                                dmc.Text(
                                                    "Сравнение:",
                                                    size="10px",
                                                    fw=700,
                                                    c=muted_color,
                                                ),
                                                dmc.Text(
                                                    previous_period_text,
                                                    size="10px",
                                                    c=muted_color,
                                                    style={
                                                        "whiteSpace": "nowrap",
                                                        "fontVariantNumeric": (
                                                            "tabular-nums"
                                                        ),
                                                    },
                                                ),
                                            ],
                                        ),
                                    ],
                                ),
                            ],
                        ),
                        style={
                            "padding": "10px 12px",
                            "minWidth": "220px",
                            "borderBottom": (
                                f"1px solid {border_color}"
                            ),
                        },
                    ),

                    # -----------------------------------------
                    # Чистая выручка
                    # -----------------------------------------
                    dmc.TableTd(
                        money_text(
                            current["revenue"],
                            fw=800,
                        ),
                        style={
                            "padding": "10px",
                            "borderBottom": (
                                f"1px solid {border_color}"
                            ),
                        },
                    ),

                    # -----------------------------------------
                    # Δ выручки
                    # -----------------------------------------
                    dmc.TableTd(
                        dmc.Box(
                            style={"textAlign": "right"},
                            children=change_badge(
                                revenue_change,
                                format_pct(
                                    revenue_change,
                                    signed=True,
                                ),
                            ),
                        ),
                        style={
                            "padding": "10px",
                            "borderBottom": (
                                f"1px solid {border_color}"
                            ),
                        },
                    ),

                    # -----------------------------------------
                    # Продажи
                    # -----------------------------------------
                    dmc.TableTd(
                        money_text(
                            current["sales_amount"],
                        ),
                        style={
                            "padding": "10px",
                            "borderBottom": (
                                f"1px solid {border_color}"
                            ),
                        },
                    ),

                    # -----------------------------------------
                    # Возвраты
                    # -----------------------------------------
                    dmc.TableTd(
                        money_text(
                            current["returns_amount"],
                            color=(
                                negative_color
                                if current["returns_amount"] > 0
                                else text_color
                            ),
                        ),
                        style={
                            "padding": "10px",
                            "borderBottom": (
                                f"1px solid {border_color}"
                            ),
                        },
                    ),

                    # -----------------------------------------
                    # Доля возвратов
                    # -----------------------------------------
                    dmc.TableTd(
                        dmc.Box(
                            style={
                                "textAlign": "right",
                            },
                            children=dmc.Box(
                                style={
                                    "display": "inline-flex",
                                    "padding": "4px 7px",
                                    "borderRadius": "4px",
                                    "backgroundColor": return_rate_bg,
                                },
                                children=dmc.Text(
                                    format_pct(return_rate),
                                    size="sm",
                                    fw=800,
                                    c=return_rate_color,
                                    style={
                                        "whiteSpace": "nowrap",
                                        "fontVariantNumeric": (
                                            "tabular-nums"
                                        ),
                                    },
                                ),
                            ),
                        ),
                        style={
                            "padding": "10px",
                            "borderBottom": (
                                f"1px solid {border_color}"
                            ),
                        },
                    ),

                    # -----------------------------------------
                    # Δ доли возвратов
                    # -----------------------------------------
                    dmc.TableTd(
                        dmc.Box(
                            style={"textAlign": "right"},
                            children=change_badge(
                                return_rate_delta,
                                (
                                    f"{return_rate_delta:+.1f} п.п."
                                    .replace(".", ",")
                                ),
                                inverse=True,
                            ),
                        ),
                        style={
                            "padding": "10px",
                            "borderBottom": (
                                f"1px solid {border_color}"
                            ),
                        },
                    ),

                    # -----------------------------------------
                    # Количество
                    # -----------------------------------------
                    dmc.TableTd(
                        number_text(
                            current["quantity"],
                        ),
                        style={
                            "padding": "10px",
                            "borderBottom": (
                                f"1px solid {border_color}"
                            ),
                        },
                    ),

                    # -----------------------------------------
                    # Средняя цена
                    # -----------------------------------------
                    dmc.TableTd(
                        money_text(
                            current["average_price"],
                        ),
                        style={
                            "padding": "10px 12px 10px 10px",
                            "borderBottom": (
                                f"1px solid {border_color}"
                            ),
                        },
                    ),
                ],
            )
        )

    # ---------------------------------------------------------
    # Итоговая таблица
    # ---------------------------------------------------------
    return dmc.TableScrollContainer(
        minWidth=1120,
        children=dmc.Table(
            highlightOnHover=True,
            withTableBorder=True,
            withColumnBorders=False,
            horizontalSpacing=0,
            verticalSpacing=0,
            styles={
                "table": {
                    "borderCollapse": "separate",
                    "borderSpacing": 0,
                    "fontVariantNumeric": "tabular-nums",
                }
            },
            children=[
                dmc.TableThead(
                    dmc.TableTr(
                        children=[
                            header_cell(
                                "Период",
                                "Текущий и сопоставимый",
                                align="left",
                            ),
                            header_cell(
                                "Чистая выручка",
                                "Продажи − возвраты",
                            ),
                            header_cell(
                                "Δ выручки",
                                "К сравнению",
                            ),
                            header_cell(
                                "Продажи",
                                "До возвратов",
                            ),
                            header_cell(
                                "Возвраты",
                                "Сумма",
                            ),
                            header_cell(
                                "Доля возвратов",
                                "От продаж",
                            ),
                            header_cell(
                                "Δ доли",
                                "В процентных пунктах",
                            ),
                            header_cell(
                                "Количество",
                                "Чистое",
                            ),
                            header_cell(
                                "Средняя цена",
                                "На операцию",
                            ),
                        ]
                    )
                ),
                dmc.TableTbody(body),
            ],
        ),
    )



def build_analysis_content(payload: dict):
    current = payload["current"]
    comparison = payload["comparison"]

    stock_date_label = (
        payload["stock_date"].strftime("%d.%m.%Y")
        if payload.get("stock_date")
        else "нет данных"
    )

    return dmc.Stack(
        gap="sm",
        children=[
            dmc.Alert(
                title="Краткий аналитический вывод",
                color="violet",
                variant="light",
                radius="sm",
                icon=DashIconify(
                    icon="solar:magic-stick-3-linear",
                    width=20,
                ),
                children=payload["summary"],
            ),

            dmc.SimpleGrid(
                cols=4,
                spacing="sm",
                children=[
                    metric_card(
                        "Чистая выручка",
                        format_money(current["revenue"]),
                        comparison["revenue_change_pct"],
                        "к сопоставимому периоду",
                        "solar:wallet-money-linear",
                        "blue",
                    ),
                    metric_card(
                        "Продажи",
                        format_money(current["sales_amount"]),
                        comparison["sales_change_pct"],
                        "до вычета возвратов",
                        "solar:cart-large-2-linear",
                        "indigo",
                    ),
                    metric_card(
                        "Возвраты",
                        format_money(current["returns_amount"]),
                        comparison["returns_change_pct"],
                        f"{format_pct(current['return_rate'])} от продаж",
                        "solar:restart-square-linear",
                        "red",
                        inverse_change=True,
                    ),
                    metric_card(
                        "Средняя цена",
                        format_money(current["average_price"]),
                        comparison["average_price_change_pct"],
                        f"{format_number(current['quantity'])} операций",
                        "solar:tag-price-linear",
                        "green",
                    ),
                ],
            ),

            dmc.Tabs(
                value="overview",
                radius="sm",
                color="violet",
                keepMounted=False,
                children=[
                    # -------------------------------------------------
                    # Основной уровень навигации
                    # -------------------------------------------------
                    dmc.TabsList(
                        grow=True,
                        children=[
                            dmc.TabsTab(
                                "Обзор",
                                value="overview",
                                leftSection=DashIconify(
                                    icon="solar:chart-2-linear",
                                    width=17,
                                ),
                            ),
                            
                             dmc.TabsTab(
                                "Периоды",
                                value="periods",
                                leftSection=DashIconify(
                                    icon="solar:calendar-linear",
                                    width=17,
                                ),
                            ),
                             
                            dmc.TabsTab(
                                "План WB",
                                value="plan",
                                leftSection=DashIconify(
                                    icon="solar:target-linear",
                                    width=17,
                                ),
                            ),
                             
                            dmc.TabsTab(
                                "Ассортимент",
                                value="assortment",
                                leftSection=DashIconify(
                                    icon="solar:box-linear",
                                    width=17,
                                ),
                            ),
                 
                           
                            dmc.TabsTab(
                                "Рекомендации",
                                value="recommendations",
                                leftSection=DashIconify(
                                    icon="solar:lightbulb-linear",
                                    width=17,
                                ),
                            ),
                        ],
                    ),

                    # -------------------------------------------------
                    # 1. Обзор
                    # -------------------------------------------------
                    dmc.TabsPanel(
                        value="overview",
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
                                            "Динамика чистой выручки",
                                            fw=800,
                                            size="sm",
                                            mb="xs",
                                        ),
                                        dcc.Graph(
                                            figure=build_daily_comparison_chart(
                                                payload["daily_rows"],
                                                payload.get(
                                                    "daily_previous",
                                                    [],
                                                ),
                                            ),
                                            config={
                                                "displaylogo": False,
                                                "toImageButtonOptions": {
                                                    "format": "png",
                                                    "filename": "ai_sales_analysis",
                                                    "scale": 3,
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
                                            "Драйверы изменения",
                                            fw=800,
                                            size="sm",
                                            mb="xs",
                                        ),
                                        dcc.Graph(
                                            figure=build_driver_chart(
                                                payload["drivers"]["drivers"]
                                            ),
                                            config={
                                                "displayModeBar": False,
                                            },
                                        ),
                                        dmc.Alert(
                                            title="Главный фактор",
                                            color="blue",
                                            variant="light",
                                            radius="sm",
                                            children=(
                                                f"{payload['drivers']['main_driver']['name']}: "
                                                f"{payload['drivers']['main_driver']['change_pct']:+.1f}%"
                                            ),
                                        ),
                                    ],
                                ),
                            ],
                        ),
                    ),
                    
                    
                    

                    # -------------------------------------------------
                    # 2. Ассортимент
                    # -------------------------------------------------
                    dmc.TabsPanel(
                        value="assortment",
                        pt="sm",
                        children=dmc.Paper(
                            withBorder=True,
                            radius="sm",
                            p="sm",
                            children=[
                                dmc.Group(
                                    justify="space-between",
                                    align="center",
                                    mb="xs",
                                    children=[
                                        dmc.Stack(
                                            gap=0,
                                            children=[
                                                dmc.Text(
                                                    "Ассортимент, товары и запасы",
                                                    fw=800,
                                                    size="sm",
                                                ),
                                                dmc.Text(
                                                    "Драйверы по брендам и категориям, "
                                                    "риски дефицита, избытка и падения продаж",
                                                    size="xs",
                                                    c="dimmed",
                                                ),
                                            ],
                                        ),
                                        dmc.Badge(
                                            f"Остатки на {stock_date_label}",
                                            color="gray",
                                            variant="light",
                                            radius="sm",
                                        ),
                                    ],
                                ),
                                assortment_analysis_tabs(payload),
                            ],
                        ),
                    ),

                    # -------------------------------------------------
                    # 3. План WB
                    # -------------------------------------------------
                    dmc.TabsPanel(
                        value="plan",
                        pt="sm",
                        children=dmc.Paper(
                            withBorder=True,
                            radius="sm",
                            p="sm",
                            children=[
                                dmc.Text(
                                    "Выполнение плана WB",
                                    fw=800,
                                    size="sm",
                                    mb="xs",
                                ),
                                dmc.Stack(
                                    gap="xs",
                                    children=[
                                        finding_card(item)
                                        for item in payload["plan_findings"]
                                    ],
                                ),
                            ],
                        ),
                    ),

                    # -------------------------------------------------
                    # 4. Периоды
                    # -------------------------------------------------
                    dmc.TabsPanel(
                        value="periods",
                        pt="sm",
                        children=dmc.Paper(
                            withBorder=True,
                            radius="sm",
                            p="sm",
                            children=[
                                dmc.Text(
                                    "Сопоставимый анализ MTD / QTD / YTD",
                                    fw=800,
                                    size="sm",
                                    mb="xs",
                                ),
                                period_overview_table(
                                    payload["period_rows"]
                                ),
                            ],
                        ),
                    ),

                    # -------------------------------------------------
                    # 5. Рекомендации
                    # -------------------------------------------------
                    dmc.TabsPanel(
                        value="recommendations",
                        pt="sm",
                        children=dmc.Stack(
                            gap="sm",
                            children=[
                                # dmc.Paper(
                                #     withBorder=True,
                                #     radius="sm",
                                #     p="sm",
                                #     children=[
                                #         dmc.Group(
                                #             gap=8,
                                #             align="center",
                                #             mb="xs",
                                #             children=[
                                #                 dmc.ThemeIcon(
                                #                     color="violet",
                                #                     variant="light",
                                #                     radius="sm",
                                #                     size=34,
                                #                     children=DashIconify(
                                #                         icon="solar:lightbulb-linear",
                                #                         width=18,
                                #                     ),
                                #                 ),
                                #                 # dmc.Stack(
                                #                 #     gap=0,
                                #                 #     children=[
                                #                 #         dmc.Text(
                                #                 #             "Приоритетные действия",
                                #                 #             fw=800,
                                #                 #             size="sm",
                                #                 #         ),
                                #                 #         dmc.Text(
                                #                 #             "Рекомендации сформированы "
                                #                 #             "по текущим отклонениям",
                                #                 #             size="xs",
                                #                 #             c="dimmed",
                                #                 #         ),
                                #                 #     ],
                                #                 # ),
                                #             ],
                                #         ),
                                #         # dmc.Stack(
                                #         #     gap="xs",
                                #         #     children=[
                                #         #         recommendation_card(item)
                                #         #         for item in payload["recommendations"]
                                #         #     ],
                                #         # ),
                                #     ],
                                # ),

                                dmc.Paper(
                                    withBorder=True,
                                    radius="sm",
                                    p="sm",
                                    children=[
                                        dmc.Text(
                                            "Дополнительные аналитические выводы",
                                            fw=800,
                                            size="sm",
                                            mb="xs",
                                        ),
                                        dmc.SimpleGrid(
                                            cols=2,
                                            spacing="sm",
                                            children=[
                                                finding_card(item)
                                                for item in payload["findings"]
                                            ],
                                        ),
                                    ],
                                ),
                            ],
                        ),
                    ),
                ],
            ),
        ],
    )


def recommendation_card(item: dict):
    priority_cfg = {
        "high": ("red", "solar:danger-triangle-linear", "Высокий приоритет"),
        "medium": ("orange", "solar:flag-linear", "Средний приоритет"),
        "low": ("green", "solar:check-circle-linear", "Низкий приоритет"),
    }

    color, icon, label = priority_cfg.get(
        item["priority"],
        priority_cfg["medium"],
    )

    return dmc.Paper(
        withBorder=True,
        radius="sm",
        p="sm",
        children=[
            dmc.Group(
                align="flex-start",
                wrap="nowrap",
                children=[
                    dmc.ThemeIcon(
                        color=color,
                        variant="light",
                        radius="sm",
                        size=36,
                        children=DashIconify(icon=icon, width=19),
                    ),
                    dmc.Stack(
                        gap=4,
                        style={"flex": 1},
                        children=[
                            dmc.Group(
                                justify="space-between",
                                align="center",
                                children=[
                                    dmc.Text(item["title"], fw=800, size="sm"),
                                    dmc.Badge(
                                        label,
                                        color=color,
                                        variant="light",
                                        radius="sm",
                                    ),
                                ],
                            ),
                            dmc.Text(
                                item["text"],
                                size="sm",
                                c="dimmed",
                                lh=1.5,
                            ),
                        ],
                    ),
                ],
            ),
        ],
    )






def product_table(rows: list[dict]):
    body = []

    for row in rows[:30]:
        days = row["days_of_stock"]
        days_text = (
            f"{days:.1f}"
            if days is not None
            else "Нет продаж"
        )

        body.append(
            dmc.TableTr(
                [
                    dmc.TableTd(str(row["nm_id"])),
                    dmc.TableTd(
                        dmc.Stack(
                            gap=0,
                            children=[
                                dmc.Text(row["title"], fw=700, size="sm"),
                                dmc.Text(
                                    f"{row['brand']} · {row['category']}",
                                    size="xs",
                                    c="dimmed",
                                ),
                            ],
                        )
                    ),
                    dmc.TableTd(
                        format_money(row["current_revenue"]),
                        style={"textAlign": "right"},
                    ),
                    dmc.TableTd(
                        dmc.Text(
                            format_pct(
                                row["revenue_change_pct"],
                                signed=True,
                            ),
                            fw=800,
                            c=change_color(
                                row["revenue_change_pct"]
                            ),
                            ta="right",
                        )
                    ),
                    dmc.TableTd(
                        format_number(row["stock_qty"]),
                        style={"textAlign": "right"},
                    ),
                    dmc.TableTd(
                        dmc.Text(
                            days_text,
                            fw=800,
                            c=(
                                "red"
                                if days is not None and days <= 7
                                else (
                                    "orange"
                                    if days is None or days >= 120
                                    else "#212529"
                                )
                            ),
                            ta="right",
                        )
                    ),
                    dmc.TableTd(
                        format_money(row["stock_man_value"]),
                        style={"textAlign": "right"},
                    ),
                    dmc.TableTd(
                        format_pct(row["current_return_rate"]),
                        style={"textAlign": "right"},
                    ),
                ]
            )
        )

    return dmc.Table(
        striped=True,
        highlightOnHover=True,
        withTableBorder=True,
        withColumnBorders=True,
        horizontalSpacing="sm",
        verticalSpacing="xs",
        children=[
            dmc.TableThead(
                dmc.TableTr(
                    [
                        dmc.TableTh("NM ID"),
                        dmc.TableTh("Товар"),
                        dmc.TableTh("Выручка", ta="right"),
                        dmc.TableTh("Δ выручки", ta="right"),
                        dmc.TableTh("Остаток", ta="right"),
                        dmc.TableTh("Дней запаса", ta="right"),
                        dmc.TableTh("Запас по упр. с/с", ta="right"),
                        dmc.TableTh("Возвраты", ta="right"),
                    ]
                )
            ),
            dmc.TableTbody(body),
        ],
    )




def assortment_analysis_tabs(payload: dict):
    brand_summary = payload["brand_summary"]
    category_summary = payload["category_summary"]
    product_summary = payload["product_summary"]

    graph_config = {
        "displaylogo": False,
        "responsive": True,
        "toImageButtonOptions": {
            "format": "png",
            "scale": 3,
        },
    }

    return dmc.Tabs(
        value="brands",
        radius="sm",
        color="violet",
        keepMounted=False,

        children=[
            # -------------------------------------------------
            # Внутренние вкладки ассортимента
            # -------------------------------------------------
            dmc.TabsList(
                children=[
                    dmc.TabsTab(
                        "Бренды",
                        value="brands",
                        leftSection=DashIconify(
                            icon="solar:tag-linear",
                            width=16,
                        ),
                    ),

                    dmc.TabsTab(
                        "Категории",
                        value="categories",
                        leftSection=DashIconify(
                            icon="solar:layers-linear",
                            width=16,
                        ),
                    ),

                    # dmc.TabsTab(
                    #     "Избыток",
                    #     value="excess",
                    #     leftSection=DashIconify(
                    #         icon="solar:box-linear",
                    #         width=16,
                    #     ),
                    # ),

                    # dmc.TabsTab(
                    #     "Возвраты",
                    #     value="returns",
                    #     leftSection=DashIconify(
                    #         icon="solar:restart-square-linear",
                    #         width=16,
                    #     ),
                    # ),
                ],
            ),

            # =================================================
            # БРЕНДЫ
            # =================================================
            dmc.TabsPanel(
                value="brands",
                pt="sm",

                children=dmc.Stack(
                    gap="sm",

                    children=[
                        # -----------------------------------------
                        # График на всю ширину
                        # -----------------------------------------
                        dmc.Paper(
                            withBorder=True,
                            radius="sm",
                            p="sm",

                            children=[
                                dmc.Stack(
                                    gap=2,
                                    mb="xs",

                                    children=[
                                        dmc.Text(
                                            "Главные драйверы по брендам",
                                            fw=800,
                                            size="sm",
                                        ),

                                        dmc.Text(
                                            "Вклад брендов в изменение "
                                            "чистой выручки относительно "
                                            "сопоставимого периода",
                                            size="xs",
                                            c="dimmed",
                                        ),
                                    ],
                                ),

                                dcc.Graph(
                                    figure=build_entity_delta_chart(
                                        (
                                            brand_summary["growth"][:8]
                                            + brand_summary["decline"][:8]
                                        ),
                                        "Бренд",
                                    ),

                                    config={
                                        **graph_config,
                                        "toImageButtonOptions": {
                                            "format": "png",
                                            "filename": "brand_drivers",
                                            "scale": 3,
                                        },
                                    },

                                    style={
                                        "width": "100%",
                                        "height": "500px",
                                    },
                                ),
                            ],
                        ),

                        # -----------------------------------------
                        # Таблица на всю ширину
                        # -----------------------------------------
                        dmc.Paper(
                            withBorder=True,
                            radius="sm",
                            p="sm",

                            children=[
                                dmc.Stack(
                                    gap=2,
                                    mb="xs",

                                    children=[
                                        dmc.Text(
                                            "Детализация по брендам",
                                            fw=800,
                                            size="sm",
                                        ),

                                        dmc.Text(
                                            "Текущая и предыдущая выручка, "
                                            "вклад в изменение и динамика "
                                            "возвратов",
                                            size="xs",
                                            c="dimmed",
                                        ),
                                    ],
                                ),

                                entity_table(
                                    sorted(
                                        brand_summary["all"],
                                        key=lambda row: abs(
                                            float(
                                                row.get(
                                                    "revenue_delta",
                                                    0,
                                                )
                                                or 0
                                            )
                                        ),
                                        reverse=True,
                                    ),
                                    "Бренд",
                                ),
                            ],
                        ),
                    ],
                ),
            ),

            # =================================================
            # КАТЕГОРИИ
            # =================================================
            dmc.TabsPanel(
                value="categories",
                pt="sm",

                children=dmc.Stack(
                    gap="sm",

                    children=[
                        # -----------------------------------------
                        # График на всю ширину
                        # -----------------------------------------
                        dmc.Paper(
                            withBorder=True,
                            radius="sm",
                            p="sm",

                            children=[
                                dmc.Stack(
                                    gap=2,
                                    mb="xs",

                                    children=[
                                        dmc.Text(
                                            "Главные драйверы по категориям",
                                            fw=800,
                                            size="sm",
                                        ),

                                        dmc.Text(
                                            "Вклад категорий в изменение "
                                            "чистой выручки относительно "
                                            "сопоставимого периода",
                                            size="xs",
                                            c="dimmed",
                                        ),
                                    ],
                                ),

                                dcc.Graph(
                                    figure=build_entity_delta_chart(
                                        (
                                            category_summary["growth"][:8]
                                            + category_summary["decline"][:8]
                                        ),
                                        "Категория",
                                    ),

                                    config={
                                        **graph_config,
                                        "toImageButtonOptions": {
                                            "format": "png",
                                            "filename": "category_drivers",
                                            "scale": 3,
                                        },
                                    },

                                    style={
                                        "width": "100%",
                                        "height": "500px",
                                    },
                                ),
                            ],
                        ),

                        # -----------------------------------------
                        # Таблица на всю ширину
                        # -----------------------------------------
                        dmc.Paper(
                            withBorder=True,
                            radius="sm",
                            p="sm",

                            children=[
                                dmc.Stack(
                                    gap=2,
                                    mb="xs",

                                    children=[
                                        dmc.Text(
                                            "Детализация по категориям",
                                            fw=800,
                                            size="sm",
                                        ),

                                        dmc.Text(
                                            "Текущая и предыдущая выручка, "
                                            "вклад в изменение и динамика "
                                            "возвратов",
                                            size="xs",
                                            c="dimmed",
                                        ),
                                    ],
                                ),

                                entity_table(
                                    sorted(
                                        category_summary["all"],
                                        key=lambda row: abs(
                                            float(
                                                row.get(
                                                    "revenue_delta",
                                                    0,
                                                )
                                                or 0
                                            )
                                        ),
                                        reverse=True,
                                    ),
                                    "Категория",
                                ),
                            ],
                        ),
                    ],
                ),
            ),

            # =================================================
            # ТОВАРЫ С ПАДЕНИЕМ
            # Оставляем панель, даже если вкладка сейчас скрыта
            # =================================================
            dmc.TabsPanel(
                value="sales-down",
                pt="sm",

                children=dmc.Paper(
                    withBorder=True,
                    radius="sm",
                    p="sm",

                    children=[
                        dmc.Text(
                            "Товары есть в наличии, "
                            "но продажи снизились",
                            fw=800,
                            size="sm",
                            mb=2,
                        ),

                        dmc.Text(
                            "Приоритетная проверка карточки, цены, "
                            "скидки, рекламы и позиции в выдаче",
                            size="xs",
                            c="dimmed",
                            mb="sm",
                        ),

                        product_table(
                            product_summary[
                                "sales_down_with_stock"
                            ]
                        ),
                    ],
                ),
            ),

            # =================================================
            # ДЕФИЦИТ
            # Оставляем панель, даже если вкладка сейчас скрыта
            # =================================================
            dmc.TabsPanel(
                value="shortage",
                pt="sm",

                children=dmc.Paper(
                    withBorder=True,
                    radius="sm",
                    p="sm",

                    children=[
                        dmc.Text(
                            "Риск дефицита и низкий запас",
                            fw=800,
                            size="sm",
                            mb=2,
                        ),

                        dmc.Text(
                            "Товары отсортированы от самого "
                            "короткого срока запаса",
                            size="xs",
                            c="dimmed",
                            mb="sm",
                        ),

                        product_table(
                            product_summary["shortage"]
                        ),
                    ],
                ),
            ),

            # =================================================
            # ИЗБЫТОК
            # =================================================
            dmc.TabsPanel(
                value="excess",
                pt="sm",

                children=dmc.Paper(
                    withBorder=True,
                    radius="sm",
                    p="sm",

                    children=[
                        dmc.Text(
                            "Избыточный и неликвидный запас",
                            fw=800,
                            size="sm",
                            mb=2,
                        ),

                        dmc.Text(
                            "Товары с длительным сроком хранения "
                            "либо отсутствием продаж",
                            size="xs",
                            c="dimmed",
                            mb="sm",
                        ),

                        product_table(
                            product_summary["excess"]
                        ),
                    ],
                ),
            ),

            # =================================================
            # ВОЗВРАТЫ
            # =================================================
            dmc.TabsPanel(
                value="returns",
                pt="sm",

                children=dmc.Paper(
                    withBorder=True,
                    radius="sm",
                    p="sm",

                    children=[
                        dmc.Text(
                            "Товары с высокими или "
                            "растущими возвратами",
                            fw=800,
                            size="sm",
                            mb=2,
                        ),

                        dmc.Text(
                            "Проверка качества, описания, "
                            "фотографий и размерной сетки",
                            size="xs",
                            c="dimmed",
                            mb="sm",
                        ),

                        product_table(
                            product_summary["returns"]
                        ),
                    ],
                ),
            ),
        ],
    )