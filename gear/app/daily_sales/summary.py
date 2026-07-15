# # gear/app/daily_sales/summary.py

# import pandas as pd
# import dash_mantine_components as dmc
# from dash_iconify import DashIconify
# from dash import html
# from .methodology import methodology_button

# from ..data.base import DashboardData
# from ..misc.baners import empty_df_banner


# def _money(value):
#     value = value or 0
#     if abs(value) >= 1_000_000_000:
#         return f"{value / 1_000_000_000:,.1f}".replace(",", " ") + " млрд ₽"
#     if abs(value) >= 1_000_000:
#         return f"{value / 1_000_000:,.1f}".replace(",", " ") + " млн ₽"
#     return f"{value:,.0f}".replace(",", " ") + " ₽"


# def _num(value):
#     return f"{(value or 0):,.0f}".replace(",", " ")


# def _pct(value):
#     return f"{(value or 0):.1f}%"


# def _safe_div(num, den):
#     return num / den if den else 0


# def _icon(icon, color="blue"):
#     return dmc.ThemeIcon(
#         DashIconify(icon=icon, width=15, height=15),
#         variant="light",
#         color=color,
#         size=28,
#         radius=0,
#     )


# def _kpi(title, value, note, icon, color="blue", extra=None):
#     return dmc.Box(
#         style={
#             "borderLeft": "1px solid #e5e7eb",
#             "paddingLeft": "16px",
#             "height": "100%",
#         },
#         children=dmc.Group(
#             justify="space-between",
#             align="flex-start",
#             gap="sm",
#             children=[
#                 dmc.Box(
#                     children=[
#                         dmc.Text(title, size="xs", c="dimmed", fw=700),
#                         dmc.Text(value, size="22px", fw=800, lh=1.15, mt=3),
#                         dmc.Text(note, size="xs", c="dimmed", mt=4),
#                         extra if extra else None,
#                     ],
#                 ),
#                 _icon(icon, color),
#             ],
#         ),
#     )


# def _mini_progress(title, value, label, color="blue"):
#     progress_value = max(0, min(abs(float(value or 0)), 100))

#     return dmc.Box(
#         children=[
#             dmc.Group(
#                 justify="space-between",
#                 align="center",
#                 mb=5,
#                 gap=8,
#                 children=[
#                     dmc.Text(title, size="xs", fw=700),
#                     dmc.Text(
#                         label,
#                         size="xs",
#                         fw=800,
#                         c=color,
#                         ta="right",
#                         style={"whiteSpace": "nowrap"},
#                     ),
#                 ],
#             ),
#             dmc.Progress(
#                 value=progress_value,
#                 color=color,
#                 size=8,
#                 radius=0,
#             ),
#         ],
#     )


# def get_sales_summary(start, end, cat_list=None, brand_list=None, gender_list=None):
#     with DashboardData() as d:
#         df = d.get_dayly_sales_grid_data(
#             start,
#             end,
#             cat_list,
#             brand_list,
#             gender_list,
#         )

#     if df.empty:
#         return empty_df_banner()

#     numeric_cols = [
#         "amount",
#         "retail_amount",
#         "wb_discount",
#         "vat_amount",
#         "amount_vatless",
#         "cogs",
#         "cogs_man",
#         "net_comission",
#         "margin",
#         "margin_man",
#         "total_net_sales",
#         "no_cost",
#         "no_stocks",
#         "no_income",
#         "wb_costs",
#         "wb_result",
#     ]

#     for col in numeric_cols:
#         if col in df.columns:
#             df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

#     amount = df["amount"].sum()
#     retail_amount = df["retail_amount"].sum()
#     vat_amount = df["vat_amount"].sum()
#     amount_vatless = df["amount_vatless"].sum()

#     cogs = df["cogs"].sum()
#     cogs_man = df["cogs_man"].sum()

#     margin = df["margin"].sum()
#     margin_man = df["margin_man"].sum()

#     commission = df["net_comission"].sum()
#     wb_costs = df["wb_costs"].sum() if "wb_costs" in df.columns else 0
#     wb_total_costs = commission + (-wb_costs)

#     # Финрезультат после WB-расходов
#     fin_result_buh = margin - wb_costs
#     fin_result_man = (
#         df["wb_result"].sum()
#         if "wb_result" in df.columns
#         else margin_man - wb_costs
#     )

#     qty = df["total_net_sales"].sum()

#     no_cost = df["no_cost"].sum()
#     no_stocks = df["no_stocks"].sum()
#     no_income = df["no_income"].sum()

#     days_count = len(df)
#     avg_daily_amount = _safe_div(amount, days_count)

#     wb_discount_amount = retail_amount - amount
#     wb_discount_percent = _safe_div(wb_discount_amount, amount) * 100

#     cogs_percent = _safe_div(cogs, amount_vatless) * 100
#     cogs_man_percent = _safe_div(cogs_man, amount_vatless) * 100

#     margin_percent = _safe_div(margin, amount_vatless) * 100
#     margin_man_percent = _safe_div(margin_man, amount_vatless) * 100

#     fin_result_buh_percent = _safe_div(fin_result_buh, amount_vatless) * 100
#     fin_result_man_percent = _safe_div(fin_result_man, amount_vatless) * 100

#     commission_percent = _safe_div(commission, amount_vatless) * 100
#     wb_total_costs_percent = _safe_div(wb_total_costs, amount_vatless) * 100

#     no_cost_share = _safe_div(no_cost, qty) * 100
#     no_stocks_share = _safe_div(no_stocks, qty) * 100
#     no_income_share = _safe_div(no_income, qty) * 100

#     revenue_extra = dmc.Box(
#         mt=8,
#         pt=7,
#         style={
#             "borderTop": "1px solid #e5e7eb",
#         },
#         children=[
#             dmc.Group(
#                 justify="space-between",
#                 gap=10,
#                 children=[
#                     dmc.Text("без НДС", size="xs", c="dimmed"),
#                     dmc.Text(
#                         _money(amount_vatless),
#                         size="xs",
#                         fw=800,
#                         c="#111827",
#                     ),
#                 ],
#             ),
#             dmc.Group(
#                 justify="space-between",
#                 gap=10,
#                 mt=2,
#                 children=[
#                     dmc.Text("НДС", size="xs", c="dimmed"),
#                     dmc.Text(
#                         _money(vat_amount),
#                         size="xs",
#                         fw=700,
#                         c="dimmed",
#                     ),
#                 ],
#             ),
#         ],
#     )

#     return dmc.Paper(
#         withBorder=True,
#         radius=0,
#         shadow="xs",
#         px="md",
#         py="sm",
#         mb="md",
#         style={
#             "width": "100%",
#             "backgroundColor": "#fbfcfe",
#             "borderColor": "#d9e0e8",
#         },
#         children=[
           
            
#             dmc.Group(
#     justify="space-between",
#     align="center",
#     mb="sm",
#     children=[
#         dmc.Group(
#             gap=8,
#             children=[
#                 DashIconify(
#                     icon="solar:chart-2-linear",
#                     width=19,
#                     height=19,
#                     color="#228be6",
#                 ),
#                 dmc.Text(
#                     "Ключевые показатели",
#                     fw=800,
#                     size="md",
#                     c="#228be6",
#                 ),
#                 dmc.Text(
#                     "· по текущим фильтрам",
#                     size="sm",
#                     c="dimmed",
#                 ),
#             ],
#         ),

#         methodology_button(),
#     ],
# ),

#             dmc.Grid(
#                 gutter="md",
#                 mb="sm",
#                 children=[
#                     dmc.GridCol(
#                         _kpi(
#                             "Выручка с НДС",
#                             _money(amount),
#                             f"среднее в день: {_money(avg_daily_amount)}",
#                             "solar:wallet-money-linear",
#                             "blue",
#                             extra=revenue_extra,
#                         ),
#                         span={"base": 12, "md": 6, "xl": 3},
#                     ),
#                     dmc.GridCol(
#                         _kpi(
#                             "WB реализовал с НДС",
#                             _money(retail_amount),
#                             f"скидка WB: {_money(wb_discount_amount)}",
#                             "solar:tag-price-linear",
#                             "cyan",
#                         ),
#                         span={"base": 12, "md": 6, "xl": 3},
#                     ),
#                     dmc.GridCol(
#                         _kpi(
#                             "Скидка WB",
#                             _pct(wb_discount_percent),
#                             "от выручки с НДС",
#                             "solar:sale-linear",
#                             "orange" if wb_discount_percent else "gray",
#                         ),
#                         span={"base": 12, "md": 6, "xl": 3},
#                     ),
#                     dmc.GridCol(
#                         _kpi(
#                             "Продажи, шт.",
#                             _num(qty),
#                             f"дней в выборке: {days_count}",
#                             "solar:cart-large-linear",
#                             "teal",
#                         ),
#                         span={"base": 12, "md": 6, "xl": 3},
#                     ),
#                 ],
#             ),

#             dmc.Divider(my="xs"),

#             dmc.Grid(
#                 gutter="md",
#                 mb="sm",
#                 children=[
#                     dmc.GridCol(
#                         _mini_progress(
#                             "Бухгалтерская маржинальность",
#                             margin_percent,
#                             f"{_pct(margin_percent)} / {_money(margin)}",
#                             "green" if margin_percent >= 0 else "red",
#                         ),
#                         span={"base": 12, "md": 6},
#                     ),
#                     dmc.GridCol(
#                         _mini_progress(
#                             "Управленческая маржинальность",
#                             margin_man_percent,
#                             f"{_pct(margin_man_percent)} / {_money(margin_man)}",
#                             "green" if margin_man_percent >= 0 else "red",
#                         ),
#                         span={"base": 12, "md": 6},
#                     ),
#                     dmc.GridCol(
#                         _mini_progress(
#                             "Финрезультат бухгалтерский",
#                             fin_result_buh_percent,
#                             f"{_pct(fin_result_buh_percent)} / {_money(fin_result_buh)}",
#                             "green" if fin_result_buh >= 0 else "red",
#                         ),
#                         span={"base": 12, "md": 6},
#                     ),
#                     dmc.GridCol(
#                         _mini_progress(
#                             "Финрезультат управленческий",
#                             fin_result_man_percent,
#                             f"{_pct(fin_result_man_percent)} / {_money(fin_result_man)}",
#                             "green" if fin_result_man >= 0 else "red",
#                         ),
#                         span={"base": 12, "md": 6},
#                     ),
#                 ],
#             ),

#             dmc.Divider(my="xs"),

#             dmc.Grid(
#                 gutter="md",
#                 mb="sm",
#                 children=[
#                     dmc.GridCol(
#                         _mini_progress(
#                             "Бухгалтерская с/с",
#                             cogs_percent,
#                             f"{_pct(cogs_percent)} / {_money(cogs)}",
#                             "violet",
#                         ),
#                         span={"base": 12, "md": 6},
#                     ),
#                     dmc.GridCol(
#                         _mini_progress(
#                             "Управленческая с/с",
#                             cogs_man_percent,
#                             f"{_pct(cogs_man_percent)} / {_money(cogs_man)}",
#                             "blue",
#                         ),
#                         span={"base": 12, "md": 6},
#                     ),
#                 ],
#             ),

#             dmc.Divider(my="xs"),

#             dmc.Grid(
#                 gutter="md",
#                 children=[
#                     dmc.GridCol(
#                         _mini_progress(
#                             "Расходы WB итого",
#                             wb_total_costs_percent,
#                             f"{_pct(wb_total_costs_percent)} / {_money(wb_total_costs)}",
#                             "orange",
#                         ),
#                         span={"base": 12, "md": 3},
#                     ),
#                     dmc.GridCol(
#                         _mini_progress(
#                             "Без себестоимости",
#                             no_cost_share,
#                             f"{_num(no_cost)} шт. / {_pct(no_cost_share)}",
#                             "red" if no_cost_share else "gray",
#                         ),
#                         span={"base": 12, "md": 3},
#                     ),
#                     dmc.GridCol(
#                         _mini_progress(
#                             "Нет на складе",
#                             no_stocks_share,
#                             f"{_num(no_stocks)} шт. / {_pct(no_stocks_share)}",
#                             "red" if no_stocks_share else "gray",
#                         ),
#                         span={"base": 12, "md": 3},
#                     ),
#                     dmc.GridCol(
#                         _mini_progress(
#                             "Нет прихода",
#                             no_income_share,
#                             f"{_num(no_income)} шт. / {_pct(no_income_share)}",
#                             "red" if no_income_share else "gray",
#                         ),
#                         span={"base": 12, "md": 3},
#                     ),
#                 ],
#             ),
#         ],
#     )




# gear/app/daily_sales/summary.py

from __future__ import annotations

import pandas as pd
import dash_mantine_components as dmc
from dash import html
from dash_iconify import DashIconify

from .methodology import methodology_button
from ..data.base import DashboardData
from ..misc.baners import empty_df_banner


# ============================================================
# ЦВЕТА
# ============================================================

PANEL_BACKGROUND = "#FFFFFF"
PAGE_BACKGROUND = "#F8FAFC"

PANEL_BORDER = "#DEE2E6"
BLOCK_BORDER = "#E9ECEF"
PROGRESS_BACKGROUND = "#E9ECEF"

TEXT_COLOR = "#212529"
MUTED_TEXT_COLOR = "#868E96"

BLUE = "#228BE6"
BLUE_BG = "#E7F5FF"

CYAN = "#15AABF"
CYAN_BG = "#E3FAFC"

GREEN = "#2FB344"
GREEN_BG = "#EBFBEE"

RED = "#FA5252"
RED_BG = "#FFF5F5"

ORANGE = "#F76707"
ORANGE_BG = "#FFF4E6"

VIOLET = "#7950F2"
VIOLET_BG = "#F3F0FF"

TEAL = "#12B886"
TEAL_BG = "#E6FCF5"

GRAY = "#868E96"
GRAY_BG = "#F1F3F5"


# ============================================================
# ТЕКСТЫ ПОДСКАЗОК
# ============================================================

MARGIN_TOOLTIP = (
    "Маржинальность рассчитывается как выручка без НДС "
    "минус себестоимость и минус комиссия WB. "
    "Маркетинг, штрафы и прочие дополнительные расходы "
    "в этом показателе не учитываются."
)

FIN_RESULT_TOOLTIP = (
    "Финансовый результат учитывает себестоимость, комиссию WB, "
    "маркетинг, штрафы, логистику и прочие дополнительные "
    "расходы и удержания."
)

WB_EXPENSES_TOOLTIP = (
    "Расходы WB включают комиссию, маркетинг, штрафы, "
    "логистику и прочие дополнительные расходы и удержания."
)

DATA_CONTROL_TOOLTIP = (
    "Показывает количество проданных единиц, по которым "
    "не удалось определить себестоимость, остаток или приход."
)


# ============================================================
# ФОРМАТИРОВАНИЕ
# ============================================================

def _money(value):
    value = float(value or 0)

    if abs(value) >= 1_000_000_000:
        result = (
            f"{value / 1_000_000_000:,.1f}"
            .replace(",", " ")
        )
        return f"{result} млрд ₽"

    if abs(value) >= 1_000_000:
        result = (
            f"{value / 1_000_000:,.1f}"
            .replace(",", " ")
        )
        return f"{result} млн ₽"

    if abs(value) >= 1_000:
        result = (
            f"{value / 1_000:,.1f}"
            .replace(",", " ")
        )
        return f"{result} тыс. ₽"

    return f"{value:,.0f}".replace(",", " ") + " ₽"


def _num(value):
    return f"{float(value or 0):,.0f}".replace(",", " ")


def _pct(value):
    return f"{float(value or 0):.1f}%"


def _signed_pct(value):
    value = float(value or 0)
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.1f}%"


def _safe_div(num, den):
    return num / den if den else 0


def _clamp_progress(value):
    """
    Mantine Progress принимает значения от 0 до 100.

    Для отрицательных показателей длина индикатора строится
    по модулю, а знак отображается в числовом значении.
    """
    value = abs(float(value or 0))
    return max(0, min(value, 100))


# ============================================================
# БАЗОВЫЕ КОМПОНЕНТЫ
# ============================================================

def _section_icon(
    icon,
    color,
    background_color,
    size=34,
    icon_size=18,
):
    return dmc.Center(
        w=size,
        h=size,
        style={
            "backgroundColor": background_color,
            "border": f"1px solid {color}22",
            "flexShrink": 0,
        },
        children=DashIconify(
            icon=icon,
            width=icon_size,
            height=icon_size,
            color=color,
        ),
    )


def _info_tooltip(
    text,
    color=GRAY,
    width=320,
):
    return dmc.Tooltip(
        label=text,
        position="top",
        withArrow=True,
        multiline=True,
        w=width,
        openDelay=250,
        children=dmc.Center(
            w=18,
            h=18,
            style={
                "cursor": "help",
                "flexShrink": 0,
            },
            children=DashIconify(
                icon="solar:info-circle-linear",
                width=15,
                height=15,
                color=color,
            ),
        ),
    )


def _title_with_info(
    title,
    tooltip=None,
    color=GRAY,
    size="12px",
    weight=700,
):
    children = [
        dmc.Text(
            title,
            size=size,
            fw=weight,
            c=TEXT_COLOR,
            lh=1.2,
        )
    ]

    if tooltip:
        children.append(
            _info_tooltip(
                text=tooltip,
                color=color,
            )
        )

    return dmc.Group(
        gap=5,
        align="center",
        wrap="nowrap",
        style={"minWidth": 0},
        children=children,
    )


def _section_title(
    title,
    subtitle,
    icon,
    color,
    background_color,
    tooltip=None,
):
    return dmc.Group(
        gap=10,
        align="center",
        wrap="nowrap",
        children=[
            _section_icon(
                icon=icon,
                color=color,
                background_color=background_color,
                size=34,
                icon_size=18,
            ),
            dmc.Stack(
                gap=2,
                style={
                    "minWidth": 0,
                    "flex": "1 1 auto",
                },
                children=[
                    _title_with_info(
                        title=title,
                        tooltip=tooltip,
                        color=color,
                        size="14px",
                        weight=750,
                    ),
                    dmc.Text(
                        subtitle,
                        size="11px",
                        c=MUTED_TEXT_COLOR,
                        lh=1.2,
                    ),
                ],
            ),
        ],
    )


def _section_block(
    title,
    subtitle,
    icon,
    color,
    background_color,
    children,
    tooltip=None,
):
    return html.Div(
        style={
            "height": "100%",
            "padding": "12px 14px",
            "backgroundColor": PANEL_BACKGROUND,
            "border": f"1px solid {BLOCK_BORDER}",
            "boxSizing": "border-box",
        },
        children=[
            _section_title(
                title=title,
                subtitle=subtitle,
                icon=icon,
                color=color,
                background_color=background_color,
                tooltip=tooltip,
            ),
            dmc.Divider(
                my=10,
                color=BLOCK_BORDER,
            ),
            dmc.Stack(
                gap=15,
                children=children,
            ),
        ],
    )


# ============================================================
# ВЕРХНИЕ KPI-КАРТОЧКИ
# ============================================================

def _kpi_card(
    title,
    value,
    note,
    icon,
    color,
    background_color,
    extra=None,
):
    return html.Div(
        style={
            "height": "100%",
            "minHeight": "124px",
            "padding": "12px 14px",
            "backgroundColor": PANEL_BACKGROUND,
            "border": f"1px solid {BLOCK_BORDER}",
            "boxSizing": "border-box",
        },
        children=[
            dmc.Group(
                justify="space-between",
                align="flex-start",
                gap="sm",
                wrap="nowrap",
                children=[
                    dmc.Stack(
                        gap=0,
                        style={
                            "minWidth": 0,
                            "flex": "1 1 auto",
                        },
                        children=[
                            dmc.Text(
                                title,
                                size="12px",
                                fw=700,
                                c=MUTED_TEXT_COLOR,
                                lh=1.2,
                            ),
                            dmc.Text(
                                value,
                                size="24px",
                                fw=800,
                                c=TEXT_COLOR,
                                lh=1.15,
                                mt=5,
                                style={
                                    "letterSpacing": "-0.4px",
                                    "whiteSpace": "nowrap",
                                    "fontVariantNumeric": "tabular-nums",
                                },
                            ),
                            dmc.Text(
                                note,
                                size="11px",
                                c=MUTED_TEXT_COLOR,
                                lh=1.25,
                                mt=5,
                            ),
                        ],
                    ),
                    _section_icon(
                        icon=icon,
                        color=color,
                        background_color=background_color,
                        size=34,
                        icon_size=18,
                    ),
                ],
            ),
            extra if extra is not None else None,
        ],
    )


def _revenue_breakdown(
    amount_vatless,
    vat_amount,
):
    return dmc.Box(
        mt=9,
        pt=8,
        style={
            "borderTop": f"1px solid {BLOCK_BORDER}",
        },
        children=[
            dmc.Group(
                justify="space-between",
                align="center",
                gap=10,
                wrap="nowrap",
                children=[
                    dmc.Text(
                        "без НДС",
                        size="11px",
                        c=MUTED_TEXT_COLOR,
                    ),
                    dmc.Text(
                        _money(amount_vatless),
                        size="11px",
                        fw=750,
                        c=TEXT_COLOR,
                        ta="right",
                        style={
                            "whiteSpace": "nowrap",
                            "fontVariantNumeric": "tabular-nums",
                        },
                    ),
                ],
            ),
            dmc.Group(
                justify="space-between",
                align="center",
                gap=10,
                wrap="nowrap",
                mt=3,
                children=[
                    dmc.Text(
                        "НДС",
                        size="11px",
                        c=MUTED_TEXT_COLOR,
                    ),
                    dmc.Text(
                        _money(vat_amount),
                        size="11px",
                        fw=650,
                        c=MUTED_TEXT_COLOR,
                        ta="right",
                        style={
                            "whiteSpace": "nowrap",
                            "fontVariantNumeric": "tabular-nums",
                        },
                    ),
                ],
            ),
        ],
    )


# ============================================================
# БУХГАЛТЕРСКИЕ И УПРАВЛЕНЧЕСКИЕ ПОКАЗАТЕЛИ
# ============================================================

def _financial_metric(
    title,
    percent,
    amount,
    color,
    icon,
    tooltip=None,
    signed=False,
):
    percent_text = (
        _signed_pct(percent)
        if signed
        else _pct(percent)
    )

    return dmc.Box(
        children=[
            dmc.Group(
                justify="space-between",
                align="center",
                gap=12,
                wrap="nowrap",
                children=[
                    dmc.Group(
                        gap=7,
                        align="center",
                        wrap="nowrap",
                        style={
                            "minWidth": 0,
                            "flex": "1 1 auto",
                        },
                        children=[
                            DashIconify(
                                icon=icon,
                                width=15,
                                height=15,
                                color=color,
                                style={"flexShrink": 0},
                            ),
                            _title_with_info(
                                title=title,
                                tooltip=tooltip,
                                color=color,
                            ),
                        ],
                    ),
                    dmc.Text(
                        f"{percent_text}  ·  {_money(amount)}",
                        size="12px",
                        fw=800,
                        c=color,
                        ta="right",
                        lh=1.15,
                        style={
                            "whiteSpace": "nowrap",
                            "fontVariantNumeric": "tabular-nums",
                        },
                    ),
                ],
            ),
            dmc.Progress(
                value=_clamp_progress(percent),
                color=color,
                size=6,
                radius=0,
                mt=7,
                styles={
                    "root": {
                        "backgroundColor": PROGRESS_BACKGROUND,
                    },
                },
            ),
        ],
    )


def _accounting_column(
    cogs_percent,
    cogs,
    margin_percent,
    margin,
    fin_result_percent,
    fin_result,
):
    margin_color = GREEN if margin >= 0 else RED
    result_color = GREEN if fin_result >= 0 else RED

    return _section_block(
        title="Бухгалтерские показатели",
        subtitle="Себестоимость по данным бухгалтерского учёта",
        icon="solar:document-text-linear",
        color=VIOLET,
        background_color=VIOLET_BG,
        children=[
            _financial_metric(
                title="Себестоимость",
                percent=cogs_percent,
                amount=cogs,
                color=VIOLET,
                icon="solar:calculator-minimalistic-linear",
            ),
            _financial_metric(
                title="Маржинальность",
                percent=margin_percent,
                amount=margin,
                color=margin_color,
                icon="solar:graph-up-linear",
                tooltip=MARGIN_TOOLTIP,
            ),
            _financial_metric(
                title="Финансовый результат",
                percent=fin_result_percent,
                amount=fin_result,
                color=result_color,
                icon="solar:wallet-money-linear",
                tooltip=FIN_RESULT_TOOLTIP,
                signed=True,
            ),
        ],
    )


def _management_column(
    cogs_percent,
    cogs,
    margin_percent,
    margin,
    fin_result_percent,
    fin_result,
):
    margin_color = GREEN if margin >= 0 else RED
    result_color = GREEN if fin_result >= 0 else RED

    return _section_block(
        title="Управленческие показатели",
        subtitle="Себестоимость по данным управленческого учёта",
        icon="solar:settings-minimalistic-linear",
        color=BLUE,
        background_color=BLUE_BG,
        children=[
            _financial_metric(
                title="Себестоимость",
                percent=cogs_percent,
                amount=cogs,
                color=BLUE,
                icon="solar:calculator-minimalistic-linear",
            ),
            _financial_metric(
                title="Маржинальность",
                percent=margin_percent,
                amount=margin,
                color=margin_color,
                icon="solar:graph-up-linear",
                tooltip=MARGIN_TOOLTIP,
            ),
            _financial_metric(
                title="Финансовый результат",
                percent=fin_result_percent,
                amount=fin_result,
                color=result_color,
                icon="solar:wallet-money-linear",
                tooltip=FIN_RESULT_TOOLTIP,
                signed=True,
            ),
        ],
    )


# ============================================================
# РАСХОДЫ WB
# ============================================================

def _wb_expenses_block(
    total_percent,
    total_amount,
):
    value_color = RED if total_amount < 0 else ORANGE

    return _section_block(
        title="Расходы WB",
        subtitle="Комиссия, маркетинг и прочие удержания",
        icon="solar:bill-list-linear",
        color=ORANGE,
        background_color=ORANGE_BG,
        tooltip=WB_EXPENSES_TOOLTIP,
        children=[
            dmc.Box(
                children=[
                    dmc.Group(
                        justify="space-between",
                        align="center",
                        gap=12,
                        wrap="nowrap",
                        children=[
                            dmc.Group(
                                gap=8,
                                align="center",
                                wrap="nowrap",
                                style={
                                    "minWidth": 0,
                                    "flex": "1 1 auto",
                                },
                                children=[
                                    dmc.Center(
                                        w=28,
                                        h=28,
                                        style={
                                            "backgroundColor": ORANGE_BG,
                                            "border": f"1px solid {ORANGE}22",
                                            "flexShrink": 0,
                                        },
                                        children=DashIconify(
                                            icon=(
                                                "solar:"
                                                "card-transfer-linear"
                                            ),
                                            width=15,
                                            height=15,
                                            color=ORANGE,
                                        ),
                                    ),
                                    dmc.Text(
                                        "Расходы WB итого",
                                        size="12px",
                                        fw=750,
                                        c=TEXT_COLOR,
                                        lh=1.2,
                                    ),
                                ],
                            ),
                            dmc.Stack(
                                gap=1,
                                align="flex-end",
                                children=[
                                    dmc.Text(
                                        _money(total_amount),
                                        size="15px",
                                        fw=800,
                                        c=value_color,
                                        lh=1.05,
                                        style={
                                            "whiteSpace": "nowrap",
                                            "fontVariantNumeric": (
                                                "tabular-nums"
                                            ),
                                        },
                                    ),
                                    dmc.Text(
                                        _signed_pct(total_percent),
                                        size="10px",
                                        fw=650,
                                        c=MUTED_TEXT_COLOR,
                                        lh=1.05,
                                    ),
                                ],
                            ),
                        ],
                    ),
                    dmc.Progress(
                        value=_clamp_progress(total_percent),
                        color="orange",
                        size=6,
                        radius=0,
                        mt=9,
                        styles={
                            "root": {
                                "backgroundColor": PROGRESS_BACKGROUND,
                            },
                        },
                    ),
                ],
            ),
        ],
    )


# ============================================================
# КОНТРОЛЬ ДАННЫХ
# ============================================================

def _quality_metric(
    title,
    qty,
    share,
    icon,
):
    has_issue = float(share or 0) > 0

    color = RED if has_issue else GREEN
    background_color = RED_BG if has_issue else GREEN_BG

    return dmc.Box(
        children=[
            dmc.Group(
                justify="space-between",
                align="center",
                wrap="nowrap",
                gap=10,
                children=[
                    dmc.Group(
                        gap=8,
                        align="center",
                        wrap="nowrap",
                        style={
                            "minWidth": 0,
                            "flex": "1 1 auto",
                        },
                        children=[
                            dmc.Center(
                                w=28,
                                h=28,
                                style={
                                    "backgroundColor": background_color,
                                    "border": f"1px solid {color}22",
                                    "flexShrink": 0,
                                },
                                children=DashIconify(
                                    icon=icon,
                                    width=15,
                                    height=15,
                                    color=color,
                                ),
                            ),
                            dmc.Text(
                                title,
                                size="12px",
                                fw=700,
                                c=TEXT_COLOR,
                                lh=1.2,
                            ),
                        ],
                    ),
                    dmc.Stack(
                        gap=1,
                        align="flex-end",
                        children=[
                            dmc.Text(
                                f"{_num(qty)} шт.",
                                size="12px",
                                fw=800,
                                c=color,
                                lh=1.05,
                                style={
                                    "whiteSpace": "nowrap",
                                    "fontVariantNumeric": "tabular-nums",
                                },
                            ),
                            dmc.Text(
                                _pct(share),
                                size="10px",
                                fw=650,
                                c=MUTED_TEXT_COLOR,
                                lh=1.05,
                            ),
                        ],
                    ),
                ],
            ),
            dmc.Progress(
                value=_clamp_progress(share),
                color="red" if has_issue else "green",
                size=5,
                radius=0,
                mt=7,
                styles={
                    "root": {
                        "backgroundColor": PROGRESS_BACKGROUND,
                    },
                },
            ),
        ],
    )


def _quality_control_block(
    no_cost,
    no_cost_share,
    no_stocks,
    no_stocks_share,
    no_income,
    no_income_share,
):
    total_issues = (
        float(no_cost or 0)
        + float(no_stocks or 0)
        + float(no_income or 0)
    )

    has_issues = total_issues > 0

    return _section_block(
        title="Контроль данных",
        subtitle="Позиции, по которым требуется проверить данные",
        icon=(
            "solar:danger-triangle-linear"
            if has_issues
            else "solar:check-circle-linear"
        ),
        color=RED if has_issues else GREEN,
        background_color=RED_BG if has_issues else GREEN_BG,
        tooltip=DATA_CONTROL_TOOLTIP,
        children=[
            html.Div(
                style={
                    "display": "grid",
                    "gridTemplateColumns": (
                        "repeat(3, minmax(180px, 1fr))"
                    ),
                    "gap": "24px",
                    "overflowX": "auto",
                },
                children=[
                    _quality_metric(
                        title="Без себестоимости",
                        qty=no_cost,
                        share=no_cost_share,
                        icon=(
                            "solar:"
                            "calculator-minimalistic-linear"
                        ),
                    ),
                    _quality_metric(
                        title="Нет на складе",
                        qty=no_stocks,
                        share=no_stocks_share,
                        icon="solar:box-minimalistic-linear",
                    ),
                    _quality_metric(
                        title="Нет прихода",
                        qty=no_income,
                        share=no_income_share,
                        icon="solar:delivery-linear",
                    ),
                ],
            ),
        ],
    )


# ============================================================
# ОСНОВНОЙ SUMMARY
# ============================================================

def get_sales_summary(
    start,
    end,
    cat_list=None,
    brand_list=None,
    gender_list=None,
):
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

    # --------------------------------------------------------
    # ПРИВЕДЕНИЕ ЧИСЛОВЫХ КОЛОНОК
    # --------------------------------------------------------

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
        if col not in df.columns:
            df[col] = 0

        df[col] = (
            pd.to_numeric(
                df[col],
                errors="coerce",
            )
            .fillna(0)
        )

    # --------------------------------------------------------
    # ВЫРУЧКА
    # --------------------------------------------------------

    amount = df["amount"].sum()
    retail_amount = df["retail_amount"].sum()
    vat_amount = df["vat_amount"].sum()
    amount_vatless = df["amount_vatless"].sum()

    # --------------------------------------------------------
    # СЕБЕСТОИМОСТЬ
    # --------------------------------------------------------

    cogs = df["cogs"].sum()
    cogs_man = df["cogs_man"].sum()

    # --------------------------------------------------------
    # МАРЖИНАЛЬНОСТЬ
    #
    # margin / margin_man должны включать:
    #
    # выручку без НДС
    # минус себестоимость
    # минус комиссию WB
    #
    # Без маркетинга, штрафов и прочих overhead-расходов.
    # --------------------------------------------------------

    margin = df["margin"].sum()
    margin_man = df["margin_man"].sum()

    # --------------------------------------------------------
    # РАСХОДЫ WB
    # --------------------------------------------------------

    commission = df["net_comission"].sum()
    wb_costs = df["wb_costs"].sum()

    # Сохраняем действующую логику проекта.
    wb_total_costs = commission + (-wb_costs)

    # --------------------------------------------------------
    # ФИНАНСОВЫЙ РЕЗУЛЬТАТ
    #
    # Финансовый результат учитывает дополнительные расходы:
    # маркетинг, штрафы, логистику и прочие удержания.
    # --------------------------------------------------------

    fin_result_buh = margin - wb_costs

    fin_result_man = (
        df["wb_result"].sum()
        if "wb_result" in df.columns
        else margin_man - wb_costs
    )

    # --------------------------------------------------------
    # КОЛИЧЕСТВО И КОНТРОЛЬ ДАННЫХ
    # --------------------------------------------------------

    qty = df["total_net_sales"].sum()

    no_cost = df["no_cost"].sum()
    no_stocks = df["no_stocks"].sum()
    no_income = df["no_income"].sum()

    days_count = len(df)
    avg_daily_amount = _safe_div(amount, days_count)

    # --------------------------------------------------------
    # СКИДКА WB
    # --------------------------------------------------------

    wb_discount_amount = retail_amount - amount

    wb_discount_percent = (
        _safe_div(
            wb_discount_amount,
            amount,
        )
        * 100
    )

    # --------------------------------------------------------
    # ДОЛИ ОТ ВЫРУЧКИ БЕЗ НДС
    # --------------------------------------------------------

    cogs_percent = (
        _safe_div(
            cogs,
            amount_vatless,
        )
        * 100
    )

    cogs_man_percent = (
        _safe_div(
            cogs_man,
            amount_vatless,
        )
        * 100
    )

    margin_percent = (
        _safe_div(
            margin,
            amount_vatless,
        )
        * 100
    )

    margin_man_percent = (
        _safe_div(
            margin_man,
            amount_vatless,
        )
        * 100
    )

    fin_result_buh_percent = (
        _safe_div(
            fin_result_buh,
            amount_vatless,
        )
        * 100
    )

    fin_result_man_percent = (
        _safe_div(
            fin_result_man,
            amount_vatless,
        )
        * 100
    )

    wb_total_costs_percent = (
        _safe_div(
            wb_total_costs,
            amount_vatless,
        )
        * 100
    )

    # --------------------------------------------------------
    # ДОЛИ ПРОБЛЕМНЫХ ПОЗИЦИЙ
    # --------------------------------------------------------

    no_cost_share = (
        _safe_div(
            no_cost,
            qty,
        )
        * 100
    )

    no_stocks_share = (
        _safe_div(
            no_stocks,
            qty,
        )
        * 100
    )

    no_income_share = (
        _safe_div(
            no_income,
            qty,
        )
        * 100
    )

    # ========================================================
    # UI
    # ========================================================

    return dmc.Paper(
        withBorder=True,
        radius=0,
        shadow="xs",
        p=0,
        mb="md",
        style={
            "width": "100%",
            "backgroundColor": PAGE_BACKGROUND,
            "borderColor": PANEL_BORDER,
            "overflow": "hidden",
        },
        children=[
            # =================================================
            # ЗАГОЛОВОК SUMMARY
            # =================================================

            html.Div(
                style={
                    "padding": "12px 14px",
                    "backgroundColor": PANEL_BACKGROUND,
                    "borderBottom": f"1px solid {PANEL_BORDER}",
                },
                children=dmc.Group(
                    justify="space-between",
                    align="center",
                    gap="md",
                    wrap="nowrap",
                    children=[
                        dmc.Group(
                            gap=9,
                            align="center",
                            wrap="nowrap",
                            children=[
                                _section_icon(
                                    icon="solar:chart-2-linear",
                                    color=BLUE,
                                    background_color=BLUE_BG,
                                    size=34,
                                    icon_size=18,
                                ),
                                dmc.Stack(
                                    gap=1,
                                    children=[
                                        dmc.Text(
                                            "Ключевые показатели",
                                            fw=800,
                                            size="md",
                                            c=TEXT_COLOR,
                                            lh=1.15,
                                        ),
                                        dmc.Text(
                                            "Результаты по текущим фильтрам",
                                            size="11px",
                                            c=MUTED_TEXT_COLOR,
                                            lh=1.15,
                                        ),
                                    ],
                                ),
                            ],
                        ),
                        methodology_button(),
                    ],
                ),
            ),

            # =================================================
            # ОСНОВНОЕ СОДЕРЖИМОЕ
            # =================================================

            html.Div(
                style={
                    "padding": "12px",
                },
                children=[
                    # =========================================
                    # ВЕРХНИЕ KPI
                    # =========================================

                    html.Div(
                        style={
                            "display": "grid",
                            "gridTemplateColumns": (
                                "repeat(4, minmax(220px, 1fr))"
                            ),
                            "gap": "10px",
                            "overflowX": "auto",
                        },
                        children=[
                            _kpi_card(
                                title="Выручка с НДС",
                                value=_money(amount),
                                note=(
                                    "Среднее в день: "
                                    f"{_money(avg_daily_amount)}"
                                ),
                                icon="solar:wallet-money-linear",
                                color=BLUE,
                                background_color=BLUE_BG,
                                extra=_revenue_breakdown(
                                    amount_vatless=amount_vatless,
                                    vat_amount=vat_amount,
                                ),
                            ),
                            _kpi_card(
                                title="WB реализовал с НДС",
                                value=_money(retail_amount),
                                note=(
                                    "Скидка WB: "
                                    f"{_money(wb_discount_amount)}"
                                ),
                                icon="solar:tag-price-linear",
                                color=CYAN,
                                background_color=CYAN_BG,
                            ),
                            _kpi_card(
                                title="Скидка WB",
                                value=_pct(wb_discount_percent),
                                note="От выручки с НДС",
                                icon="solar:sale-linear",
                                color=ORANGE,
                                background_color=ORANGE_BG,
                            ),
                            _kpi_card(
                                title="Продажи, шт.",
                                value=_num(qty),
                                note=f"Дней в выборке: {days_count}",
                                icon="solar:cart-large-linear",
                                color=TEAL,
                                background_color=TEAL_BG,
                            ),
                        ],
                    ),

                    # =========================================
                    # БУХГАЛТЕРСКИЕ / УПРАВЛЕНЧЕСКИЕ
                    # =========================================

                    html.Div(
                        style={
                            "display": "grid",
                            "gridTemplateColumns": (
                                "repeat(2, minmax(420px, 1fr))"
                            ),
                            "gap": "10px",
                            "marginTop": "10px",
                            "overflowX": "auto",
                        },
                        children=[
                            _accounting_column(
                                cogs_percent=cogs_percent,
                                cogs=cogs,
                                margin_percent=margin_percent,
                                margin=margin,
                                fin_result_percent=(
                                    fin_result_buh_percent
                                ),
                                fin_result=fin_result_buh,
                            ),
                            _management_column(
                                cogs_percent=cogs_man_percent,
                                cogs=cogs_man,
                                margin_percent=margin_man_percent,
                                margin=margin_man,
                                fin_result_percent=(
                                    fin_result_man_percent
                                ),
                                fin_result=fin_result_man,
                            ),
                        ],
                    ),

                    # =========================================
                    # РАСХОДЫ WB / КОНТРОЛЬ ДАННЫХ
                    # =========================================

                    html.Div(
                        style={
                            "display": "grid",
                            "gridTemplateColumns": (
                                "minmax(350px, 0.75fr) "
                                "minmax(720px, 2fr)"
                            ),
                            "gap": "10px",
                            "marginTop": "10px",
                            "overflowX": "auto",
                            "alignItems": "stretch",
                        },
                        children=[
                            _wb_expenses_block(
                                total_percent=(
                                    wb_total_costs_percent
                                ),
                                total_amount=wb_total_costs,
                            ),
                            _quality_control_block(
                                no_cost=no_cost,
                                no_cost_share=no_cost_share,
                                no_stocks=no_stocks,
                                no_stocks_share=no_stocks_share,
                                no_income=no_income,
                                no_income_share=no_income_share,
                            ),
                        ],
                    ),
                ],
            ),
        ],
    )