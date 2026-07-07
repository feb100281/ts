# gear/app/daily_sales/summary.py

import pandas as pd
import dash_mantine_components as dmc
from dash_iconify import DashIconify
from dash import html
from .methodology import methodology_button

from ..data.base import DashboardData
from ..misc.baners import empty_df_banner


def _money(value):
    value = value or 0
    if abs(value) >= 1_000_000_000:
        return f"{value / 1_000_000_000:,.1f}".replace(",", " ") + " млрд ₽"
    if abs(value) >= 1_000_000:
        return f"{value / 1_000_000:,.1f}".replace(",", " ") + " млн ₽"
    return f"{value:,.0f}".replace(",", " ") + " ₽"


def _num(value):
    return f"{(value or 0):,.0f}".replace(",", " ")


def _pct(value):
    return f"{(value or 0):.1f}%"


def _safe_div(num, den):
    return num / den if den else 0


def _icon(icon, color="blue"):
    return dmc.ThemeIcon(
        DashIconify(icon=icon, width=15, height=15),
        variant="light",
        color=color,
        size=28,
        radius=0,
    )


def _kpi(title, value, note, icon, color="blue", extra=None):
    return dmc.Box(
        style={
            "borderLeft": "1px solid #e5e7eb",
            "paddingLeft": "16px",
            "height": "100%",
        },
        children=dmc.Group(
            justify="space-between",
            align="flex-start",
            gap="sm",
            children=[
                dmc.Box(
                    children=[
                        dmc.Text(title, size="xs", c="dimmed", fw=700),
                        dmc.Text(value, size="22px", fw=800, lh=1.15, mt=3),
                        dmc.Text(note, size="xs", c="dimmed", mt=4),
                        extra if extra else None,
                    ],
                ),
                _icon(icon, color),
            ],
        ),
    )


def _mini_progress(title, value, label, color="blue"):
    progress_value = max(0, min(abs(float(value or 0)), 100))

    return dmc.Box(
        children=[
            dmc.Group(
                justify="space-between",
                align="center",
                mb=5,
                gap=8,
                children=[
                    dmc.Text(title, size="xs", fw=700),
                    dmc.Text(
                        label,
                        size="xs",
                        fw=800,
                        c=color,
                        ta="right",
                        style={"whiteSpace": "nowrap"},
                    ),
                ],
            ),
            dmc.Progress(
                value=progress_value,
                color=color,
                size=8,
                radius=0,
            ),
        ],
    )


def get_sales_summary(start, end, cat_list=None, brand_list=None, gender_list=None):
    with DashboardData() as d:
        df = d.get_dayly_sales_grid_data(
            start,
            end,
            cat_list,
            brand_list,
            gender_list,
        )

    if df.empty:
        return empty_df_banner()

    numeric_cols = [
        "amount",
        "retail_amount",
        "wb_discount",
        "vat_amount",
        "amount_vatless",
        "cogs",
        "cogs_man",
        "net_comission",
        "margin",
        "margin_man",
        "total_net_sales",
        "no_cost",
        "no_stocks",
        "no_income",
        "wb_costs",
        "wb_result",
    ]

    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    amount = df["amount"].sum()
    retail_amount = df["retail_amount"].sum()
    vat_amount = df["vat_amount"].sum()
    amount_vatless = df["amount_vatless"].sum()

    cogs = df["cogs"].sum()
    cogs_man = df["cogs_man"].sum()

    margin = df["margin"].sum()
    margin_man = df["margin_man"].sum()

    commission = df["net_comission"].sum()
    wb_costs = df["wb_costs"].sum() if "wb_costs" in df.columns else 0
    wb_total_costs = commission + (-wb_costs)

    # Финрезультат после WB-расходов
    fin_result_buh = margin - wb_costs
    fin_result_man = (
        df["wb_result"].sum()
        if "wb_result" in df.columns
        else margin_man - wb_costs
    )

    qty = df["total_net_sales"].sum()

    no_cost = df["no_cost"].sum()
    no_stocks = df["no_stocks"].sum()
    no_income = df["no_income"].sum()

    days_count = len(df)
    avg_daily_amount = _safe_div(amount, days_count)

    wb_discount_amount = retail_amount - amount
    wb_discount_percent = _safe_div(wb_discount_amount, amount) * 100

    cogs_percent = _safe_div(cogs, amount_vatless) * 100
    cogs_man_percent = _safe_div(cogs_man, amount_vatless) * 100

    margin_percent = _safe_div(margin, amount_vatless) * 100
    margin_man_percent = _safe_div(margin_man, amount_vatless) * 100

    fin_result_buh_percent = _safe_div(fin_result_buh, amount_vatless) * 100
    fin_result_man_percent = _safe_div(fin_result_man, amount_vatless) * 100

    commission_percent = _safe_div(commission, amount_vatless) * 100
    wb_total_costs_percent = _safe_div(wb_total_costs, amount_vatless) * 100

    no_cost_share = _safe_div(no_cost, qty) * 100
    no_stocks_share = _safe_div(no_stocks, qty) * 100
    no_income_share = _safe_div(no_income, qty) * 100

    revenue_extra = dmc.Box(
        mt=8,
        pt=7,
        style={
            "borderTop": "1px solid #e5e7eb",
        },
        children=[
            dmc.Group(
                justify="space-between",
                gap=10,
                children=[
                    dmc.Text("без НДС", size="xs", c="dimmed"),
                    dmc.Text(
                        _money(amount_vatless),
                        size="xs",
                        fw=800,
                        c="#111827",
                    ),
                ],
            ),
            dmc.Group(
                justify="space-between",
                gap=10,
                mt=2,
                children=[
                    dmc.Text("НДС", size="xs", c="dimmed"),
                    dmc.Text(
                        _money(vat_amount),
                        size="xs",
                        fw=700,
                        c="dimmed",
                    ),
                ],
            ),
        ],
    )

    return dmc.Paper(
        withBorder=True,
        radius=0,
        shadow="xs",
        px="md",
        py="sm",
        mb="md",
        style={
            "width": "100%",
            "backgroundColor": "#fbfcfe",
            "borderColor": "#d9e0e8",
        },
        children=[
           
            
            dmc.Group(
    justify="space-between",
    align="center",
    mb="sm",
    children=[
        dmc.Group(
            gap=8,
            children=[
                DashIconify(
                    icon="solar:chart-2-linear",
                    width=19,
                    height=19,
                    color="#228be6",
                ),
                dmc.Text(
                    "Ключевые показатели",
                    fw=800,
                    size="md",
                    c="#228be6",
                ),
                dmc.Text(
                    "· по текущим фильтрам",
                    size="sm",
                    c="dimmed",
                ),
            ],
        ),

        methodology_button(),
    ],
),

            dmc.Grid(
                gutter="md",
                mb="sm",
                children=[
                    dmc.GridCol(
                        _kpi(
                            "Выручка с НДС",
                            _money(amount),
                            f"среднее в день: {_money(avg_daily_amount)}",
                            "solar:wallet-money-linear",
                            "blue",
                            extra=revenue_extra,
                        ),
                        span={"base": 12, "md": 6, "xl": 3},
                    ),
                    dmc.GridCol(
                        _kpi(
                            "WB реализовал с НДС",
                            _money(retail_amount),
                            f"скидка WB: {_money(wb_discount_amount)}",
                            "solar:tag-price-linear",
                            "cyan",
                        ),
                        span={"base": 12, "md": 6, "xl": 3},
                    ),
                    dmc.GridCol(
                        _kpi(
                            "Скидка WB",
                            _pct(wb_discount_percent),
                            "от выручки с НДС",
                            "solar:sale-linear",
                            "orange" if wb_discount_percent else "gray",
                        ),
                        span={"base": 12, "md": 6, "xl": 3},
                    ),
                    dmc.GridCol(
                        _kpi(
                            "Продажи, шт.",
                            _num(qty),
                            f"дней в выборке: {days_count}",
                            "solar:cart-large-linear",
                            "teal",
                        ),
                        span={"base": 12, "md": 6, "xl": 3},
                    ),
                ],
            ),

            dmc.Divider(my="xs"),

            dmc.Grid(
                gutter="md",
                mb="sm",
                children=[
                    dmc.GridCol(
                        _mini_progress(
                            "Бухгалтерская маржинальность",
                            margin_percent,
                            f"{_pct(margin_percent)} / {_money(margin)}",
                            "green" if margin_percent >= 0 else "red",
                        ),
                        span={"base": 12, "md": 6},
                    ),
                    dmc.GridCol(
                        _mini_progress(
                            "Управленческая маржинальность",
                            margin_man_percent,
                            f"{_pct(margin_man_percent)} / {_money(margin_man)}",
                            "green" if margin_man_percent >= 0 else "red",
                        ),
                        span={"base": 12, "md": 6},
                    ),
                    dmc.GridCol(
                        _mini_progress(
                            "Финрезультат бухгалтерский",
                            fin_result_buh_percent,
                            f"{_pct(fin_result_buh_percent)} / {_money(fin_result_buh)}",
                            "green" if fin_result_buh >= 0 else "red",
                        ),
                        span={"base": 12, "md": 6},
                    ),
                    dmc.GridCol(
                        _mini_progress(
                            "Финрезультат управленческий",
                            fin_result_man_percent,
                            f"{_pct(fin_result_man_percent)} / {_money(fin_result_man)}",
                            "green" if fin_result_man >= 0 else "red",
                        ),
                        span={"base": 12, "md": 6},
                    ),
                ],
            ),

            dmc.Divider(my="xs"),

            dmc.Grid(
                gutter="md",
                mb="sm",
                children=[
                    dmc.GridCol(
                        _mini_progress(
                            "Бухгалтерская с/с",
                            cogs_percent,
                            f"{_pct(cogs_percent)} / {_money(cogs)}",
                            "violet",
                        ),
                        span={"base": 12, "md": 6},
                    ),
                    dmc.GridCol(
                        _mini_progress(
                            "Управленческая с/с",
                            cogs_man_percent,
                            f"{_pct(cogs_man_percent)} / {_money(cogs_man)}",
                            "blue",
                        ),
                        span={"base": 12, "md": 6},
                    ),
                ],
            ),

            dmc.Divider(my="xs"),

            dmc.Grid(
                gutter="md",
                children=[
                    dmc.GridCol(
                        _mini_progress(
                            "Расходы WB итого",
                            wb_total_costs_percent,
                            f"{_pct(wb_total_costs_percent)} / {_money(wb_total_costs)}",
                            "orange",
                        ),
                        span={"base": 12, "md": 3},
                    ),
                    dmc.GridCol(
                        _mini_progress(
                            "Без себестоимости",
                            no_cost_share,
                            f"{_num(no_cost)} шт. / {_pct(no_cost_share)}",
                            "red" if no_cost_share else "gray",
                        ),
                        span={"base": 12, "md": 3},
                    ),
                    dmc.GridCol(
                        _mini_progress(
                            "Нет на складе",
                            no_stocks_share,
                            f"{_num(no_stocks)} шт. / {_pct(no_stocks_share)}",
                            "red" if no_stocks_share else "gray",
                        ),
                        span={"base": 12, "md": 3},
                    ),
                    dmc.GridCol(
                        _mini_progress(
                            "Нет прихода",
                            no_income_share,
                            f"{_num(no_income)} шт. / {_pct(no_income_share)}",
                            "red" if no_income_share else "gray",
                        ),
                        span={"base": 12, "md": 3},
                    ),
                ],
            ),
        ],
    )