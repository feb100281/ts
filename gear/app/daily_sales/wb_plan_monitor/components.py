# gear/app/daily_sales/wb_plan_monitor/components.py
import dash_mantine_components as dmc
from dash import html
from dash_iconify import DashIconify

from .formatters import format_money, format_money_short, format_pct


# def kpi_card(label, value, note=None, color="blue", icon="solar:chart-linear"):
#     return dmc.Paper(
#         withBorder=True,
#         radius="sm",
#         p="sm",
#         style={
#             "height": "100%",
#             "backgroundColor": "#ffffff",
#             "borderColor": "#e9ecef",
#         },
#         children=[
#             dmc.Group(
#                 justify="space-between",
#                 align="flex-start",
#                 children=[
#                     dmc.Box(
#                         children=[
#                             dmc.Text(label, size="xs", c="dimmed", fw=700),
#                             dmc.Text(value, size="xl", fw=900, c="#212529"),
#                             dmc.Text(note or "", size="xs", c="dimmed", mt=2),
#                         ],
#                     ),
#                     dmc.ThemeIcon(
#                         variant="light",
#                         color=color,
#                         radius="sm",
#                         size=34,
#                         children=DashIconify(icon=icon, width=18),
#                     ),
#                 ],
#             )
#         ],
#     )



def kpi_card(
    label,
    value,
    note=None,
    color="blue",
    icon="solar:chart-linear",
):
    return dmc.Paper(
        withBorder=True,
        radius="sm",
        px="md",
        py="sm",
        style={
            "height": "100%",
            "minHeight": "112px",
            "backgroundColor": "#ffffff",
            "borderColor": "#e2e8f0",
        },
        children=dmc.Box(
            style={
                "position": "relative",
                "height": "100%",
            },
            children=[
                # Иконка фиксированно справа сверху
                dmc.ThemeIcon(
                    variant="light",
                    color=color,
                    radius="sm",
                    size=36,
                    style={
                        "position": "absolute",
                        "top": "0",
                        "right": "0",
                    },
                    children=DashIconify(
                        icon=icon,
                        width=18,
                        height=18,
                    ),
                ),

                # Контент
                dmc.Box(
                    style={
                        "paddingRight": "46px",
                    },
                    children=[
                        dmc.Text(
                            label,
                            c="#7C8797",
                            fw=700,
                            style={
                                "fontSize": "13px",
                                "lineHeight": "1.2",
                                "minHeight": "31px",
                            },
                        ),

                        dmc.Text(
                            value,
                            fw=900,
                            c="#212529",
                            mt=2,
                            style={
                                "fontSize": "24px",
                                "lineHeight": "1.05",
                                "whiteSpace": "nowrap",
                                "fontVariantNumeric": "tabular-nums",
                                "letterSpacing": "-0.5px",
                            },
                        ),

                        dmc.Text(
                            note or "",
                            c="#8A94A3",
                            mt=6,
                            style={
                                "fontSize": "12px",
                                "lineHeight": "1.2",
                            },
                        ),
                    ],
                ),
            ],
        ),
    )







def semi_table(rows):
    total_plan = sum(float(row.get("plan") or 0) for row in rows)
    total_fact = sum(float(row.get("fact") or 0) for row in rows)

    total_exec_pct = (total_fact / total_plan * 100) if total_plan else 0
    total_remaining = max(total_plan - total_fact, 0)
    total_over = max(total_fact - total_plan, 0)

    def get_status(row):
        if row["is_current"]:
            return "В процессе", "blue"
        if row["is_completed"] and row["exec_pct"] >= 100:
            return "Выполнен", "green"
        if row["is_completed"]:
            return "Не выполнен", "red"
        return "Не начат", "gray"

    def exec_color(value):
        if value >= 100:
            return "green"
        if value >= 80:
            return "orange"
        return "red"

    def diff_text(remaining, over):
        if remaining > 0:
            return format_money(remaining)
        return f"+{format_money(over)}"

    cell_style = {
        "paddingTop": "7px",
        "paddingBottom": "7px",
        "borderBottom": "1px solid #E2E8F0",
        "fontVariantNumeric": "tabular-nums",
        "fontSize": "13px",
        "lineHeight": "1.25",
    }

    head_style = {
        "paddingTop": "10px",
        "paddingBottom": "10px",
        "backgroundColor": "#F1F5F9",
        "borderBottom": "1px solid #CBD5E1",
        "color": "#22324D",
        "fontSize": "11px",
        "fontWeight": 500,
        "lineHeight": "1.2",
    }

    def pct_badge(value, filled=False):
        return dmc.Badge(
            format_pct(value),
            color=exec_color(value),
            variant="filled" if filled else "light",
            radius="sm",
            size="sm",
            fw=800,
            miw=78,
            style={
                "height": "24px",
                "fontSize": "12px",
                "letterSpacing": "0.1px",
                "paddingLeft": "8px",
                "paddingRight": "8px",
            },
        )

    def status_badge(status, color, filled=False):
        return dmc.Badge(
            status.upper(),
            color=color,
            variant="filled" if filled else "light",
            radius="sm",
            size="sm",
            fw=800,
            miw=116,
            style={
                "height": "24px",
                "fontSize": "11px",
                "letterSpacing": "0.25px",
                "paddingLeft": "8px",
                "paddingRight": "8px",
            },
        )

    body = []

    for row in rows:
        status, color = get_status(row)

        body.append(
            html.Tr(
                children=[
                    html.Td(
                        html.Strong(row["label"]),
                        style={
                            **cell_style,
                            "color": "#1F2F46",
                            "fontWeight": 800,
                            "paddingLeft": "18px",
                        },
                    ),
                    html.Td(
                        format_money(row["plan"]),
                        style={**cell_style, "textAlign": "right"},
                    ),
                    html.Td(
                        format_money(row["fact"]),
                        style={**cell_style, "textAlign": "right"},
                    ),
                    html.Td(
                        pct_badge(row["exec_pct"]),
                        style={**cell_style, "textAlign": "center"},
                    ),
                    html.Td(
                        diff_text(row["remaining"], row["over"]),
                        style={
                            **cell_style,
                            "textAlign": "right",
                            "fontWeight": 700,
                            "color": "#1F2F46",
                        },
                    ),
                    html.Td(
                        status_badge(status, color),
                        style={**cell_style, "textAlign": "center"},
                    ),
                ],
            )
        )

    total_status = "Выполнен" if total_exec_pct >= 100 else "В процессе"
    total_status_color = "green" if total_exec_pct >= 100 else "blue"

    body.append(
        html.Tr(
            children=[
                html.Td(
                    html.Strong("ИТОГО ЗА ГОД"),
                    style={
                        **cell_style,
                        "color": "#1F2F46",
                        "fontWeight": 900,
                        "paddingLeft": "18px",
                    },
                ),
                html.Td(
                    format_money(total_plan),
                    style={
                        **cell_style,
                        "textAlign": "right",
                        "fontWeight": 900,
                    },
                ),
                html.Td(
                    format_money(total_fact),
                    style={
                        **cell_style,
                        "textAlign": "right",
                        "fontWeight": 900,
                    },
                ),
                html.Td(
                    pct_badge(total_exec_pct, filled=True),
                    style={**cell_style, "textAlign": "center"},
                ),
                html.Td(
                    diff_text(total_remaining, total_over),
                    style={
                        **cell_style,
                        "textAlign": "right",
                        "fontWeight": 900,
                    },
                ),
                html.Td(
                    status_badge(total_status, total_status_color, filled=True),
                    style={**cell_style, "textAlign": "center"},
                ),
            ],
            style={
                "backgroundColor": "#F8FAFC",
                "borderTop": "2px solid #CBD5E1",
            },
        )
    )

    return dmc.Table(
        striped=False,
        highlightOnHover=True,
        withTableBorder=True,
        withColumnBorders=False,
        horizontalSpacing="md",
        verticalSpacing=0,
        style={
            "borderColor": "#E2E8F0",
            "borderCollapse": "collapse",
            "fontSize": "13px",
            "color": "#1F2F46",
            "width": "100%",
        },
        children=[
            html.Thead(
                html.Tr(
                    [
                        html.Th("Период", style={**head_style, "paddingLeft": "18px"}),
                        html.Th("План, ₽", style={**head_style, "textAlign": "right"}),
                        html.Th("Факт, ₽", style={**head_style, "textAlign": "right"}),
                        html.Th("Выполнение", style={**head_style, "textAlign": "center"}),
                        html.Th(
                            "Остаток / перевыполнение",
                            style={**head_style, "textAlign": "right"},
                        ),
                        html.Th("Статус", style={**head_style, "textAlign": "center"}),
                    ]
                )
            ),
            html.Tbody(body),
        ],
    )
    
    
    
    



def daily_table(rows):
    visible_rows = rows[-10:]

    total_fact = sum(float(row.get("fact") or 0) for row in visible_rows)
    total_sales = sum(float(row.get("sales_amount") or 0) for row in visible_rows)
    total_returns = sum(float(row.get("returns_amount") or 0) for row in visible_rows)
    total_qty = sum(int(row.get("qty") or 0) for row in visible_rows)

    avg_price = total_fact / total_qty if total_qty > 0 else 0

    cell_style = {
        "paddingTop": "8px",
        "paddingBottom": "8px",
        "borderBottom": "1px solid #E2E8F0",
        "fontVariantNumeric": "tabular-nums",
        "fontSize": "11px",
        "lineHeight": "1.25",
        "color": "#1F2F46",
    }

    head_style = {
        "paddingTop": "10px",
        "paddingBottom": "10px",
        "backgroundColor": "#F1F5F9",
        "borderBottom": "1px solid #CBD5E1",
        "color": "#22324D",
        "fontSize": "11px",
        "fontWeight": 900,
        "textTransform": "uppercase",
        "letterSpacing": "0.25px",
        "lineHeight": "1.15",
    }

    body = []

    for row in visible_rows:
        qty = int(row.get("qty") or 0)

        body.append(
            html.Tr(
                children=[
                    html.Td(
                        html.Strong(row["date"].strftime("%d.%m.%Y")),
                        style={**cell_style, "paddingLeft": "16px"},
                    ),
                    html.Td(
                        row["weekday"],
                        style={
                            **cell_style,
                            "textAlign": "center",
                            "color": "#64748B",
                            "fontWeight": 500,
                        },
                    ),
                    html.Td(
                        format_money(row["fact"]),
                        style={
                            **cell_style,
                            "textAlign": "right",
                            "fontWeight": 700,
                        },
                    ),
                    html.Td(
                        format_money(row["sales_amount"]),
                        style={**cell_style, "textAlign": "right"},
                    ),
                    html.Td(
                        format_money(row["returns_amount"]),
                        style={
                            **cell_style,
                            "textAlign": "right",
                            "color": "#C92A2A",
                            "fontWeight": 600,
                        },
                    ),
                    html.Td(
                        f"{qty:,.0f}".replace(",", " "),
                        style={**cell_style, "textAlign": "right"},
                    ),
                    html.Td(
                        format_money(row["avg_price"]),
                        style={
                            **cell_style,
                            "textAlign": "right",
                            "fontWeight": 600,
                        },
                    ),
                ],
            )
        )

    body.append(
        html.Tr(
            children=[
                html.Td(
                    html.Strong("ИТОГО ЗА 10 ДНЕЙ"),
                    colSpan=2,
                    style={
                        **cell_style,
                        # "paddingLeft": "16px",
                        "fontWeight": 700,
                    },
                ),
                html.Td(
                    html.Strong(format_money(total_fact)),
                    style={**cell_style, "textAlign": "right", "fontWeight": 700},
                ),
                html.Td(
                    html.Strong(format_money(total_sales)),
                    style={**cell_style, "textAlign": "right", "fontWeight": 700},
                ),
                html.Td(
                    html.Strong(format_money(total_returns)),
                    style={
                        **cell_style,
                        "textAlign": "right",
                        "fontWeight": 700,
                        "color": "#C92A2A",
                    },
                ),
                html.Td(
                    html.Strong(f"{total_qty:,.0f}".replace(",", " ")),
                    style={**cell_style, "textAlign": "right", "fontWeight": 700},
                ),
                html.Td(
                    html.Strong(format_money(avg_price)),
                    style={**cell_style, "textAlign": "right", "fontWeight": 700},
                ),
            ],
            style={
                "backgroundColor": "#F8FAFC",
                "borderTop": "2px solid #CBD5E1",
            },
        )
    )

    return dmc.Table(
        striped=False,
        highlightOnHover=True,
        withTableBorder=True,
        withColumnBorders=False,
        horizontalSpacing="md",
        verticalSpacing=0,
        style={
            "borderColor": "#E2E8F0",
            "borderCollapse": "collapse",
            "fontSize": "11px",
            "color": "#1F2F46",
            "width": "100%",
        },
        children=[
            html.Thead(
                html.Tr(
                    [
                        html.Th("Дата", style={**head_style}),
                        html.Th("День", style={**head_style, "textAlign": "center"}),
                        html.Th("Выручка", style={**head_style, "textAlign": "right"}),
                        html.Th("Продажи", style={**head_style, "textAlign": "right"}),
                        html.Th("Возвраты", style={**head_style, "textAlign": "right"}),
                        html.Th("Кол-во", style={**head_style, "textAlign": "right"}),
                        html.Th("Ср. цена", style={**head_style, "textAlign": "right"}),
                    ]
                )
            ),
            html.Tbody(body),
        ],
    )


def forecast_block(current_semi):
    if not current_semi:
        return dmc.Alert(
            "Текущий период плана не найден.",
            color="gray",
            variant="light",
        )

    is_ok = current_semi["projected_end"] >= current_semi["plan"]

    return dmc.Alert(
        color="green" if is_ok else "red",
        variant="light",
        radius="sm",
        title="Прогноз выполнения текущего полугодия",
        icon=DashIconify(
            icon="solar:plain-2-linear" if is_ok else "solar:danger-triangle-linear",
            width=20,
        ),
        children=[
            dmc.SimpleGrid(
                cols=4,
                spacing="sm",
                children=[
                    kpi_card(
                        "Темп за последние дни",
                        f"{format_money_short(current_semi['current_daily_rate'])}/день",
                        f"окно: {current_semi['rate_days']} дн.",
                        "blue",
                        "solar:graph-up-linear",
                    ),
                    kpi_card(
                        "Нужно в день",
                        f"{format_money_short(current_semi['required_daily_rate'])}/день",
                        f"осталось дней: {current_semi['days_remaining']}",
                        "orange",
                        "solar:calendar-mark-linear",
                    ),
                    kpi_card(
                        "Прогноз на конец",
                        format_money_short(current_semi["projected_end"]),
                        "при текущем темпе",
                        "green" if is_ok else "red",
                        "solar:chart-2-linear",
                    ),
                    kpi_card(
                        "Разрыв темпа в день",
                        format_money_short(current_semi["gap_daily_rate"]),
                        f"всего: {format_money_short(current_semi['gap_total'])}",
                        "red" if current_semi["gap_daily_rate"] > 0 else "green",
                        "solar:bolt-linear",
                    ),
                ],
            )
        ],
    )
    
    
    

def current_month_plan_table(current_month):
    rows = current_month.get("rows", [])

    cell_style = {
        "paddingTop": "8px",
        "paddingBottom": "8px",
        "borderBottom": "1px solid #E2E8F0",
        "fontVariantNumeric": "tabular-nums",
        "fontSize": "12px",
        "lineHeight": "1.25",
        "color": "#1F2F46",
    }

    head_style = {
        "paddingTop": "10px",
        "paddingBottom": "10px",
        "backgroundColor": "#F1F5F9",
        "borderBottom": "1px solid #CBD5E1",
        "color": "#22324D",
        "fontSize": "11px",
        "fontWeight": 800,
        "lineHeight": "1.15",
    }

    def exec_color(value):
        if value >= 100:
            return "green"

        if value >= 90:
            return "yellow"

        return "red"

    body = []

    for row in rows:
        delta = float(
            row.get("delta_to_plan") or 0
        )

        exec_pct = float(
            row.get("exec_to_date_pct") or 0
        )

        body.append(
            html.Tr(
                children=[
                    html.Td(
                        row["date"].strftime(
                            "%d.%m.%Y"
                        ),
                        style={
                            **cell_style,
                            "fontWeight": 700,
                            "paddingLeft": "16px",
                        },
                    ),

                    html.Td(
                        row["weekday"],
                        style={
                            **cell_style,
                            "textAlign": "center",
                            "color": "#64748B",
                        },
                    ),

                    html.Td(
                        format_money(
                            row["daily_plan"]
                        ),
                        style={
                            **cell_style,
                            "textAlign": "right",
                        },
                    ),

                    html.Td(
                        format_money(
                            row["running_plan"]
                        ),
                        style={
                            **cell_style,
                            "textAlign": "right",
                            "fontWeight": 600,
                        },
                    ),

                    html.Td(
                        format_money(
                            row["fact"]
                        ),
                        style={
                            **cell_style,
                            "textAlign": "right",
                        },
                    ),

                    html.Td(
                        format_money(
                            row["running_fact"]
                        ),
                        style={
                            **cell_style,
                            "textAlign": "right",
                            "fontWeight": 700,
                        },
                    ),

                    html.Td(
                        dmc.Badge(
                            format_pct(exec_pct),
                            color=exec_color(
                                exec_pct
                            ),
                            variant="light",
                            radius="sm",
                            size="sm",
                        ),
                        style={
                            **cell_style,
                            "textAlign": "center",
                        },
                    ),

                    html.Td(
                        (
                            f"+{format_money(delta)}"
                            if delta >= 0
                            else format_money(delta)
                        ),
                        style={
                            **cell_style,
                            "textAlign": "right",
                            "fontWeight": 700,
                            "color": (
                                "#15803D"
                                if delta >= 0
                                else "#C92A2A"
                            ),
                        },
                    ),
                ],
            )
        )

    return dmc.Table(
        striped=False,
        highlightOnHover=True,
        withTableBorder=True,
        withColumnBorders=False,
        horizontalSpacing="md",
        verticalSpacing=0,

        style={
            "borderColor": "#E2E8F0",
            "borderCollapse": "collapse",
            "width": "100%",
        },

        children=[
            html.Thead(
                html.Tr(
                    [
                        html.Th(
                            "Дата",
                            style={
                                **head_style,
                                "paddingLeft": "16px",
                            },
                        ),

                        html.Th(
                            "День",
                            style={
                                **head_style,
                                "textAlign": "center",
                            },
                        ),

                        html.Th(
                            "План дня",
                            style={
                                **head_style,
                                "textAlign": "right",
                            },
                        ),

                        html.Th(
                            "План к дате",
                            style={
                                **head_style,
                                "textAlign": "right",
                            },
                        ),

                        html.Th(
                            "Факт дня",
                            style={
                                **head_style,
                                "textAlign": "right",
                            },
                        ),

                        html.Th(
                            "Факт к дате",
                            style={
                                **head_style,
                                "textAlign": "right",
                            },
                        ),

                        html.Th(
                            "Выполнение",
                            style={
                                **head_style,
                                "textAlign": "center",
                            },
                        ),

                        html.Th(
                            "Отклонение",
                            style={
                                **head_style,
                                "textAlign": "right",
                            },
                        ),
                    ]
                )
            ),

            html.Tbody(body),
        ],
    )