# gear/app/stats/profit_optimizer.py
from __future__ import annotations

from typing import Any

import dash_ag_grid as dag
import dash_mantine_components as dmc
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, State, dcc, html
from dash_iconify import DashIconify

from .config import COLORS, PLOTLY_CONFIG
from .ids import DATE_FILTER_ID, REFRESH_BTN_ID
from .profit_optimizer_data import (
    get_profit_optimizer_data,
    simulate_product_price,
)


# =====================================================================
# IDs
# =====================================================================

STORE_ID = "profit-optimizer-store"

KPI_POTENTIAL_ID = "profit-optimizer-kpi-potential"
KPI_PRICE_ID = "profit-optimizer-kpi-price"
KPI_MARKETING_ID = "profit-optimizer-kpi-marketing"
KPI_RISK_ID = "profit-optimizer-kpi-risk"

OPPORTUNITY_CHART_ID = "profit-optimizer-opportunity-chart"
ACTIONS_CHART_ID = "profit-optimizer-actions-chart"
GRID_ID = "profit-optimizer-grid"
INSIGHT_ID = "profit-optimizer-insight"

PRODUCT_SELECT_ID = "profit-optimizer-product-select"
PRICE_SLIDER_ID = "profit-optimizer-price-slider"

SIM_CURRENT_PRICE_ID = "profit-optimizer-sim-current-price"
SIM_NEW_PRICE_ID = "profit-optimizer-sim-new-price"
SIM_QUANTITY_ID = "profit-optimizer-sim-quantity"
SIM_REVENUE_ID = "profit-optimizer-sim-revenue"
SIM_PROFIT_ID = "profit-optimizer-sim-profit"
SIM_CHANGE_ID = "profit-optimizer-sim-change"
SIM_STATUS_ID = "profit-optimizer-sim-status"
SIM_CHART_ID = "profit-optimizer-sim-chart"


# =====================================================================
# Colors
# =====================================================================

def _c(name: str, fallback: str) -> str:
    return COLORS.get(name, fallback)


GREEN = _c("green", "#0F766E")
BLUE = _c("blue", "#2563EB")
ORANGE = _c("orange", "#F97316")
PURPLE = _c("purple", "#7C3AED")
RED = _c("red", "#DC2626")
GRAY = _c("gray", "#6B7280")
BORDER = _c("border", "#E5E7EB")
TEXT = _c("text", "#111827")
MUTED = _c("muted", "#6B7280")


ACTION_COLORS = {
    "Пополнить остаток": RED,
    "Пересмотреть экономику": RED,
    "Снизить запас / ускорить продажи": ORANGE,
    "Рассмотреть повышение цены": PURPLE,
    "Рассмотреть снижение цены": BLUE,
    "Тестировать усиление маркетинга": GREEN,
    "Проверить товар без продаж": ORANGE,
    "Оставить / наблюдать": GRAY,
}


# =====================================================================
# Formatters
# =====================================================================

def _format_money(value) -> str:
    if value is None:
        return "—"
    try:
        value = float(value)
    except (TypeError, ValueError):
        return "—"
    if np.isnan(value):
        return "—"

    if abs(value) >= 1_000_000_000:
        return f"{value / 1_000_000_000:.2f} млрд ₽"
    if abs(value) >= 1_000_000:
        return f"{value / 1_000_000:.2f} млн ₽"

    return f"{value:,.0f}".replace(",", " ") + " ₽"


def _empty_figure(text: str = "Нет данных") -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(
        x=0.5,
        y=0.5,
        xref="paper",
        yref="paper",
        text=text,
        showarrow=False,
        font={"size": 12, "color": MUTED},
    )
    fig.update_layout(
        paper_bgcolor="white",
        plot_bgcolor="white",
        xaxis={"visible": False},
        yaxis={"visible": False},
        margin={"l": 20, "r": 20, "t": 20, "b": 20},
    )
    return fig


def _base_figure(fig: go.Figure) -> go.Figure:
    fig.update_layout(
        paper_bgcolor="white",
        plot_bgcolor="white",
        font={
            "family": "Inter, Arial, sans-serif",
            "color": TEXT,
            "size": 11,
        },
    )
    return fig


# =====================================================================
# UI helpers
# =====================================================================

def _kpi_card(
    *,
    title: str,
    value_id: str,
    subtitle: str,
    accent: str,
    icon: str,
):
    return html.Div(
        style={
            "border": f"1px solid {BORDER}",
            "backgroundColor": "white",
            "padding": "14px 16px",
            "minHeight": "105px",
        },
        children=[
            html.Div(
                style={
                    "display": "flex",
                    "justifyContent": "space-between",
                    "alignItems": "center",
                    "gap": "10px",
                },
                children=[
                    dmc.Text(title, size="xs", c=MUTED, fw=600),
                    html.Div(
                        style={
                            "width": "30px",
                            "height": "30px",
                            "display": "flex",
                            "alignItems": "center",
                            "justifyContent": "center",
                            "border": f"1px solid {accent}30",
                            "backgroundColor": f"{accent}12",
                        },
                        children=DashIconify(
                            icon=icon,
                            width=17,
                            color=accent,
                        ),
                    ),
                ],
            ),
            html.Div(
                id=value_id,
                children="—",
                style={
                    "fontSize": "23px",
                    "fontWeight": 700,
                    "lineHeight": "30px",
                    "marginTop": "6px",
                    "color": TEXT,
                },
            ),
            dmc.Text(subtitle, size="xs", c=MUTED),
        ],
    )


def _panel(
    *,
    title: str,
    subtitle: str,
    children,
):
    return html.Div(
        style={
            "border": f"1px solid {BORDER}",
            "backgroundColor": "white",
            "padding": "16px",
        },
        children=[
            dmc.Text(title, fw=700, size="sm"),
            dmc.Text(subtitle, size="xs", c=MUTED),
            html.Div(
                style={"marginTop": "12px"},
                children=children,
            ),
        ],
    )


# =====================================================================
# Charts
# =====================================================================

def build_opportunity_chart(df: pd.DataFrame) -> go.Figure:
    if df.empty:
        return _empty_figure()

    work = df[
        (df["quantity_30d"] > 0)
        | (df["stock_on_hand"] > 0)
    ].copy()

    if work.empty:
        return _empty_figure()

    gain = (
        pd.to_numeric(
            work["profit_opportunity_30d"],
            errors="coerce",
        )
        .fillna(0)
        .clip(lower=0)
    )

    sizes = (
        10 + gain / gain.max() * 22
        if gain.max() > 0
        else pd.Series(12, index=work.index)
    )

    fig = go.Figure()

    for action in work["recommendation"].dropna().unique():
        part = work[work["recommendation"] == action]

        fig.add_trace(
            go.Scatter(
                x=part["quantity_30d"],
                y=part["profit_margin_pct_30d"],
                mode="markers",
                name=action,
                marker={
                    "size": sizes.loc[part.index],
                    "color": ACTION_COLORS.get(action, GRAY),
                    "opacity": 0.72,
                    "line": {"color": "white", "width": 1},
                },
                customdata=part[
                    [
                        "nm_id",
                        "title",
                        "current_price_gross",
                        "suggested_price",
                        "profit_opportunity_30d",
                        "stock_days",
                        "roas_30d",
                        "recommendation_reason",
                    ]
                ].to_numpy(),
                hovertemplate=(
                    "<b>%{customdata[1]}</b><br>"
                    "NM ID: %{customdata[0]}<br><br>"
                    "Продажи 30д: <b>%{x:,.0f} шт.</b><br>"
                    "Прибыльность: <b>%{y:.1f}%</b><br>"
                    "Цена сейчас: <b>%{customdata[2]:,.0f} ₽</b><br>"
                    "Цена-ориентир: <b>%{customdata[3]:,.0f} ₽</b><br>"
                    "Потенциал прибыли: <b>%{customdata[4]:,.0f} ₽</b><br>"
                    "Запас: <b>%{customdata[5]:.0f} дн.</b><br>"
                    "ROAS: <b>%{customdata[6]:.2f}</b><br><br>"
                    "%{customdata[7]}"
                    "<extra></extra>"
                ),
            )
        )

    fig.add_hline(y=0, line_width=1, line_color=BORDER)

    fig.update_layout(
        xaxis_title="Продажи за 30 дней, шт.",
        yaxis_title="Оценочная прибыльность, %",
        hovermode="closest",
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "left",
            "x": 0,
            "font": {"size": 9},
        },
        margin={"l": 70, "r": 25, "t": 80, "b": 65},
    )
    fig.update_xaxes(showgrid=False, zeroline=False)
    fig.update_yaxes(gridcolor=BORDER, zeroline=False)

    return _base_figure(fig)


def build_actions_chart(df: pd.DataFrame) -> go.Figure:
    if df.empty:
        return _empty_figure()

    counts = (
        df["recommendation"]
        .fillna("Не определено")
        .value_counts()
        .reset_index()
    )
    counts.columns = ["recommendation", "count"]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=counts["count"],
            y=counts["recommendation"],
            orientation="h",
            marker={
                "color": [
                    ACTION_COLORS.get(x, GRAY)
                    for x in counts["recommendation"]
                ],
                "opacity": 0.78,
            },
            text=counts["count"],
            textposition="outside",
            cliponaxis=False,
            hovertemplate=(
                "<b>%{y}</b><br>"
                "Товаров: <b>%{x}</b>"
                "<extra></extra>"
            ),
        )
    )

    fig.update_layout(
        xaxis_title="Количество товаров",
        showlegend=False,
        margin={"l": 210, "r": 50, "t": 25, "b": 55},
    )
    fig.update_xaxes(showgrid=False, zeroline=False)
    fig.update_yaxes(autorange="reversed", showgrid=False)
    return _base_figure(fig)


def build_simulator_curve(
    product: dict[str, Any],
    selected_price: float,
) -> go.Figure:
    current = float(product.get("current_price_gross") or 0)

    if current <= 0:
        return _empty_figure("Нет текущей цены")

    elasticity = product.get("price_elasticity")
    obs = int(product.get("elasticity_observations") or 0)

    if elasticity is None or pd.isna(elasticity) or obs < 3:
        return _empty_figure(
            "Недостаточно истории цены для кривой прибыли"
        )

    prices = np.linspace(current * 0.80, current * 1.20, 61)
    profits = [
        simulate_product_price(product, float(price))["profit"]
        for price in prices
    ]

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=prices,
            y=profits,
            mode="lines",
            line={"color": PURPLE, "width": 3},
            name="Прогноз прибыли",
            hovertemplate=(
                "Цена: <b>%{x:,.0f} ₽</b><br>"
                "Прогноз прибыли 30д: <b>%{y:,.0f} ₽</b>"
                "<extra></extra>"
            ),
        )
    )

    current_result = simulate_product_price(product, current)
    selected_result = simulate_product_price(product, selected_price)

    fig.add_trace(
        go.Scatter(
            x=[current],
            y=[current_result["profit"]],
            mode="markers",
            marker={
                "size": 11,
                "color": BLUE,
                "line": {"color": "white", "width": 2},
            },
            name="Текущая цена",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=[selected_price],
            y=[selected_result["profit"]],
            mode="markers",
            marker={
                "size": 13,
                "color": GREEN,
                "symbol": "diamond",
                "line": {"color": "white", "width": 2},
            },
            name="Сценарий",
        )
    )

    fig.update_layout(
        xaxis_title="Цена, ₽",
        yaxis_title="Прогноз прибыли за 30 дней, ₽",
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "left",
            "x": 0,
        },
        margin={"l": 80, "r": 30, "t": 65, "b": 60},
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor=BORDER)

    return _base_figure(fig)


# =====================================================================
# Insight
# =====================================================================

def build_optimizer_insight(df: pd.DataFrame) -> str:
    if df.empty:
        return "Недостаточно данных для формирования рекомендаций."

    total = len(df)
    potential = (
        pd.to_numeric(
            df["profit_opportunity_30d"],
            errors="coerce",
        )
        .fillna(0)
        .clip(lower=0)
        .sum()
    )

    raise_price = int(
        (df["recommendation"] == "Рассмотреть повышение цены").sum()
    )
    lower_price = int(
        (df["recommendation"] == "Рассмотреть снижение цены").sum()
    )
    marketing = int(
        (df["recommendation"] == "Тестировать усиление маркетинга").sum()
    )
    stockout = int(
        (df["recommendation"] == "Пополнить остаток").sum()
    )
    negative = int(
        (df["recommendation"] == "Пересмотреть экономику").sum()
    )
    excess = int(
        (df["recommendation"] == "Снизить запас / ускорить продажи").sum()
    )

    parts = [
        f"Оптимизатор проанализировал {total} товаров."
    ]

    if potential > 0:
        parts.append(
            f"Суммарный модельный потенциал роста 30-дневной прибыли "
            f"по ценовым сценариям составляет около {_format_money(potential)}. "
            f"Это ориентир, а не гарантированный эффект."
        )

    parts.append(
        f"Для {raise_price} товаров стоит проверить повышение цены, "
        f"для {lower_price} — снижение цены или промо."
    )

    if marketing:
        parts.append(
            f"{marketing} товаров подходят для теста усиления маркетинга: "
            f"у них достаточная прибыльность, ROAS и запас."
        )

    if stockout:
        parts.append(
            f"У {stockout} товаров есть риск дефицита и потери продаж."
        )

    if excess:
        parts.append(
            f"У {excess} товаров избыточный запас; они требуют плана "
            f"ускорения продаж или сокращения закупок."
        )

    if negative:
        parts.append(
            f"{negative} товаров имеют отрицательную оценочную экономику "
            f"и требуют первоочередной проверки."
        )

    parts.append(
        "Рекомендации следует использовать как систему поддержки решений: "
        "перед изменением цены или бюджета учитывайте акции WB, "
        "позиционирование товара и качество карточки."
    )

    return " ".join(parts)


# =====================================================================
# Grid
# =====================================================================

GRID_COLUMNS = [
    {"headerName": "Приоритет", "field": "priority", "width": 115, "pinned": "left"},
    {"headerName": "Действие", "field": "recommendation", "width": 215, "pinned": "left"},
    {"headerName": "NM ID", "field": "nm_id", "width": 115},
    {"headerName": "Наименование", "field": "title", "minWidth": 260, "flex": 1},
    {"headerName": "Бренд", "field": "brand", "width": 150},
    {"headerName": "Категория", "field": "subject_name", "width": 170},
    {
        "headerName": "Score",
        "field": "opportunity_score",
        "width": 95,
        "type": "numericColumn",
    },
    {
        "headerName": "Цена сейчас",
        "field": "current_price_gross",
        "width": 125,
        "type": "numericColumn",
    },
    {
        "headerName": "Цена-ориентир",
        "field": "suggested_price",
        "width": 135,
        "type": "numericColumn",
    },
    {
        "headerName": "Продажи 30д",
        "field": "quantity_30d",
        "width": 115,
        "type": "numericColumn",
    },
    {
        "headerName": "Остаток",
        "field": "stock_on_hand",
        "width": 100,
        "type": "numericColumn",
    },
    {
        "headerName": "Запас, дней",
        "field": "stock_days",
        "width": 110,
        "type": "numericColumn",
    },
    {
        "headerName": "Прибыльность, %",
        "field": "profit_margin_pct_30d",
        "width": 130,
        "type": "numericColumn",
    },
    {
        "headerName": "ROAS",
        "field": "roas_30d",
        "width": 90,
        "type": "numericColumn",
    },
    {
        "headerName": "Эластичность",
        "field": "price_elasticity",
        "width": 115,
        "type": "numericColumn",
    },
    {
        "headerName": "Потенциал прибыли 30д",
        "field": "profit_opportunity_30d",
        "width": 170,
        "type": "numericColumn",
    },
    {
        "headerName": "Почему",
        "field": "recommendation_reason",
        "minWidth": 360,
        "flex": 1,
        "wrapText": True,
        "autoHeight": True,
    },
]


def _records(df: pd.DataFrame) -> list[dict[str, Any]]:
    if df.empty:
        return []

    fields = [
        x["field"]
        for x in GRID_COLUMNS
        if "field" in x and x["field"] in df.columns
    ]

    work = df[fields].replace([np.inf, -np.inf], np.nan)
    return work.where(pd.notna(work), None).to_dict("records")


def _store_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    if df.empty:
        return []

    fields = [
        "nm_id",
        "title",
        "brand",
        "current_price_gross",
        "average_price_30d",
        "average_cogs_man_30d",
        "quantity_30d",
        "revenue_30d",
        "estimated_profit_30d",
        "commission_rate_30d",
        "other_wb_rate_30d",
        "marketing_spend_30d",
        "price_elasticity",
        "elasticity_observations",
        "suggested_price",
    ]

    work = df[fields].replace([np.inf, -np.inf], np.nan)
    return work.where(pd.notna(work), None).to_dict("records")


# =====================================================================
# Layout
# =====================================================================

def build_profit_optimizer_tab():
    return html.Div(
        style={"paddingTop": "16px"},
        children=[
            dcc.Store(id=STORE_ID, storage_type="memory"),

            html.Div(
                style={
                    "display": "grid",
                    "gridTemplateColumns": "repeat(4, minmax(0, 1fr))",
                    "gap": "12px",
                },
                children=[
                    _kpi_card(
                        title="Потенциал прибыли",
                        value_id=KPI_POTENTIAL_ID,
                        subtitle="Модельный прирост за 30 дней",
                        accent=GREEN,
                        icon="solar:chart-2-linear",
                    ),
                    _kpi_card(
                        title="Повысить цену",
                        value_id=KPI_PRICE_ID,
                        subtitle="Товаров для ценового теста",
                        accent=PURPLE,
                        icon="solar:tag-price-linear",
                    ),
                    _kpi_card(
                        title="Усилить маркетинг",
                        value_id=KPI_MARKETING_ID,
                        subtitle="Товаров для теста масштабирования",
                        accent=BLUE,
                        icon="solar:graph-up-linear",
                    ),
                    _kpi_card(
                        title="Требуют внимания",
                        value_id=KPI_RISK_ID,
                        subtitle="Дефицит или отрицательная экономика",
                        accent=RED,
                        icon="solar:danger-triangle-linear",
                    ),
                ],
            ),

            html.Div(
                style={
                    "display": "grid",
                    "gridTemplateColumns": "minmax(0, 1.45fr) minmax(360px, 0.55fr)",
                    "gap": "14px",
                    "marginTop": "14px",
                },
                children=[
                    _panel(
                        title="Карта возможностей",
                        subtitle="Спрос, прибыльность и рекомендуемое действие по NM ID",
                        children=dcc.Graph(
                            id=OPPORTUNITY_CHART_ID,
                            figure=_empty_figure(),
                            config=PLOTLY_CONFIG,
                            style={"height": "560px"},
                        ),
                    ),
                    _panel(
                        title="Распределение действий",
                        subtitle="Сколько товаров попадает в каждую рекомендацию",
                        children=dcc.Graph(
                            id=ACTIONS_CHART_ID,
                            figure=_empty_figure(),
                            config=PLOTLY_CONFIG,
                            style={"height": "560px"},
                        ),
                    ),
                ],
            ),

            html.Div(
                style={"marginTop": "14px"},
                children=dmc.Alert(
                    title="Что рекомендует оптимизатор",
                    children=html.Div(
                        id=INSIGHT_ID,
                        children="Расчёт рекомендаций…",
                        style={"lineHeight": "19px"},
                    ),
                    icon=DashIconify(
                        icon="solar:lightbulb-bolt-linear",
                        width=18,
                    ),
                    color="teal",
                    variant="light",
                    radius=0,
                    styles={
                        "title": {"fontSize": "12px", "fontWeight": 600},
                        "message": {"fontSize": "11px"},
                    },
                ),
            ),

            html.Div(
                style={"marginTop": "14px"},
                children=_panel(
                    title="Рекомендуемые действия",
                    subtitle="Приоритетный список товаров с объяснением причины",
                    children=dag.AgGrid(
                        id=GRID_ID,
                        columnDefs=GRID_COLUMNS,
                        rowData=[],
                        defaultColDef={
                            "sortable": True,
                            "resizable": True,
                            "filter": True,
                        },
                        dashGridOptions={
                            "pagination": True,
                            "paginationPageSize": 50,
                        },
                        style={"height": "680px"},
                    ),
                ),
            ),

            html.Div(
                style={"marginTop": "14px"},
                children=_panel(
                    title="Симулятор цены",
                    subtitle=(
                        "Что произойдёт с объёмом продаж и прибылью "
                        "при изменении цены"
                    ),
                    children=[
                        html.Div(
                            style={
                                "display": "grid",
                                "gridTemplateColumns": "minmax(320px, 0.8fr) minmax(0, 1.2fr)",
                                "gap": "18px",
                            },
                            children=[
                                html.Div(
                                    children=[
                                        dmc.Select(
                                            id=PRODUCT_SELECT_ID,
                                            label="Товар",
                                            placeholder="Выберите NM ID",
                                            data=[],
                                            searchable=True,
                                            clearable=False,
                                            radius=0,
                                        ),
                                        html.Div(
                                            style={"marginTop": "18px"},
                                            children=[
                                                dmc.Text(
                                                    "Цена сценария",
                                                    size="xs",
                                                    fw=600,
                                                ),
                                                html.Div(
                                                    style={
                                                        "marginTop": "14px",
                                                        "padding": "0 8px",
                                                    },
                                                    children=dcc.Slider(
                                                        id=PRICE_SLIDER_ID,
                                                        min=0,
                                                        max=100,
                                                        step=1,
                                                        value=50,
                                                        marks={},
                                                        tooltip={
                                                            "placement": "bottom",
                                                            "always_visible": True,
                                                        },
                                                    ),
                                                ),
                                            ],
                                        ),
                                        html.Div(
                                            id=SIM_STATUS_ID,
                                            style={
                                                "marginTop": "22px",
                                                "fontSize": "11px",
                                                "color": MUTED,
                                                "lineHeight": "18px",
                                            },
                                        ),
                                    ]
                                ),
                                html.Div(
                                    style={
                                        "display": "grid",
                                        "gridTemplateColumns": "repeat(3, minmax(0, 1fr))",
                                        "gap": "10px",
                                    },
                                    children=[
                                        _kpi_card(
                                            title="Цена сейчас",
                                            value_id=SIM_CURRENT_PRICE_ID,
                                            subtitle="Текущая gross-цена",
                                            accent=BLUE,
                                            icon="solar:tag-price-linear",
                                        ),
                                        _kpi_card(
                                            title="Цена сценария",
                                            value_id=SIM_NEW_PRICE_ID,
                                            subtitle="Выбранная цена",
                                            accent=PURPLE,
                                            icon="solar:tag-linear",
                                        ),
                                        _kpi_card(
                                            title="Прогноз продаж",
                                            value_id=SIM_QUANTITY_ID,
                                            subtitle="Следующие 30 дней",
                                            accent=GREEN,
                                            icon="solar:box-linear",
                                        ),
                                        _kpi_card(
                                            title="Прогноз выручки",
                                            value_id=SIM_REVENUE_ID,
                                            subtitle="Следующие 30 дней",
                                            accent=BLUE,
                                            icon="solar:wallet-money-linear",
                                        ),
                                        _kpi_card(
                                            title="Прогноз прибыли",
                                            value_id=SIM_PROFIT_ID,
                                            subtitle="После основных расходов",
                                            accent=GREEN,
                                            icon="solar:graph-up-linear",
                                        ),
                                        _kpi_card(
                                            title="Изменение прибыли",
                                            value_id=SIM_CHANGE_ID,
                                            subtitle="Относительно текущего сценария",
                                            accent=ORANGE,
                                            icon="solar:sort-vertical-linear",
                                        ),
                                    ],
                                ),
                            ],
                        ),

                        dcc.Graph(
                            id=SIM_CHART_ID,
                            figure=_empty_figure("Выберите товар"),
                            config=PLOTLY_CONFIG,
                            style={"height": "480px", "marginTop": "12px"},
                        ),

                        dmc.Alert(
                            title="Важно",
                            children=(
                                "Симулятор использует историческую proxy-эластичность "
                                "товара и предполагает постоянную себестоимость за единицу, "
                                "пропорциональные выручке комиссию и прочие расходы WB, "
                                "а также неизменный маркетинговый бюджет. "
                                "Это сценарный инструмент, а не гарантия будущей прибыли."
                            ),
                            color="yellow",
                            variant="light",
                            radius=0,
                            styles={
                                "title": {"fontSize": "12px", "fontWeight": 600},
                                "message": {"fontSize": "11px", "lineHeight": "18px"},
                            },
                        ),
                    ],
                ),
            ),
        ],
    )


# =====================================================================
# Callback helpers
# =====================================================================

def _date_to(date_range):
    if (
        isinstance(date_range, (list, tuple))
        and len(date_range) >= 2
        and date_range[1]
    ):
        return str(date_range[1])[:10]
    return None


def _options(df: pd.DataFrame):
    if df.empty:
        return []

    work = df.sort_values("opportunity_score", ascending=False)
    result = []

    for row in work.itertuples():
        nm_id = int(row.nm_id)
        result.append(
            {
                "value": str(nm_id),
                "label": (
                    f"{nm_id} · {row.brand or ''} · "
                    f"{row.title or 'Без названия'}"
                ),
            }
        )
    return result


def _find_product(records, nm_id):
    if not records or nm_id is None:
        return None
    target = str(nm_id)
    for row in records:
        if str(row.get("nm_id")) == target:
            return row
    return None


# =====================================================================
# Callbacks
# =====================================================================

def register_profit_optimizer_callbacks(app):

    @app.callback(
        Output(KPI_POTENTIAL_ID, "children"),
        Output(KPI_PRICE_ID, "children"),
        Output(KPI_MARKETING_ID, "children"),
        Output(KPI_RISK_ID, "children"),
        Output(OPPORTUNITY_CHART_ID, "figure"),
        Output(ACTIONS_CHART_ID, "figure"),
        Output(GRID_ID, "rowData"),
        Output(PRODUCT_SELECT_ID, "data"),
        Output(PRODUCT_SELECT_ID, "value"),
        Output(STORE_ID, "data"),
        Output(INSIGHT_ID, "children"),
        Input(DATE_FILTER_ID, "value"),
        Input(REFRESH_BTN_ID, "n_clicks"),
    )
    def update_optimizer(date_range, _refresh):
        df = get_profit_optimizer_data(
            date_to=_date_to(date_range)
        )

        if df.empty:
            return (
                "0 ₽",
                "0",
                "0",
                "0",
                _empty_figure(),
                _empty_figure(),
                [],
                [],
                None,
                [],
                "Недостаточно данных для оптимизации прибыли.",
            )

        potential = (
            pd.to_numeric(
                df["profit_opportunity_30d"],
                errors="coerce",
            )
            .fillna(0)
            .clip(lower=0)
            .sum()
        )

        raise_price = int(
            (df["recommendation"] == "Рассмотреть повышение цены").sum()
        )
        marketing = int(
            (df["recommendation"] == "Тестировать усиление маркетинга").sum()
        )
        risk = int(
            df["recommendation"].isin(
                ["Пополнить остаток", "Пересмотреть экономику"]
            ).sum()
        )

        options = _options(df)
        selected = options[0]["value"] if options else None

        return (
            _format_money(potential),
            str(raise_price),
            str(marketing),
            str(risk),
            build_opportunity_chart(df),
            build_actions_chart(df),
            _records(df),
            options,
            selected,
            _store_records(df),
            build_optimizer_insight(df),
        )

    @app.callback(
        Output(PRICE_SLIDER_ID, "min"),
        Output(PRICE_SLIDER_ID, "max"),
        Output(PRICE_SLIDER_ID, "step"),
        Output(PRICE_SLIDER_ID, "value"),
        Output(PRICE_SLIDER_ID, "marks"),
        Input(PRODUCT_SELECT_ID, "value"),
        State(STORE_ID, "data"),
    )
    def configure_slider(nm_id, records):
        product = _find_product(records, nm_id)

        if not product:
            return 0, 100, 1, 50, {}

        current = float(product.get("current_price_gross") or 0)

        if current <= 0:
            return 0, 100, 1, 50, {}

        minimum = round(current * 0.80)
        maximum = round(current * 1.20)
        step = max(1, round(current * 0.005))
        suggested = float(product.get("suggested_price") or current)
        suggested = min(maximum, max(minimum, suggested))

        marks = {
            float(minimum): f"{minimum:,.0f} ₽".replace(",", " "),
            float(current): f"Сейчас {current:,.0f} ₽".replace(",", " "),
            float(maximum): f"{maximum:,.0f} ₽".replace(",", " "),
        }

        return minimum, maximum, step, round(suggested), marks

    @app.callback(
        Output(SIM_CURRENT_PRICE_ID, "children"),
        Output(SIM_NEW_PRICE_ID, "children"),
        Output(SIM_QUANTITY_ID, "children"),
        Output(SIM_REVENUE_ID, "children"),
        Output(SIM_PROFIT_ID, "children"),
        Output(SIM_CHANGE_ID, "children"),
        Output(SIM_STATUS_ID, "children"),
        Output(SIM_CHART_ID, "figure"),
        Input(PRODUCT_SELECT_ID, "value"),
        Input(PRICE_SLIDER_ID, "value"),
        State(STORE_ID, "data"),
    )
    def update_simulator(nm_id, selected_price, records):
        product = _find_product(records, nm_id)

        if not product:
            return (
                "—", "—", "—", "—", "—", "—",
                "Выберите товар.",
                _empty_figure("Выберите товар"),
            )

        current = float(product.get("current_price_gross") or 0)
        selected_price = float(selected_price or current or 0)

        result = simulate_product_price(
            product,
            selected_price,
        )

        delta = float(result.get("profit_change") or 0)
        delta_pct = float(result.get("profit_change_pct") or 0)
        sign = "+" if delta > 0 else ""

        elasticity = product.get("price_elasticity")
        obs = int(product.get("elasticity_observations") or 0)

        if elasticity is not None and not pd.isna(elasticity):
            elasticity_text = (
                f"Proxy-эластичность {float(elasticity):.2f}; "
                f"наблюдений: {obs}."
            )
        else:
            elasticity_text = (
                "Надёжная proxy-эластичность не рассчитана."
            )

        return (
            _format_money(current),
            _format_money(selected_price),
            f"{float(result.get('quantity') or 0):,.0f} шт.".replace(",", " "),
            _format_money(result.get("revenue")),
            _format_money(result.get("profit")),
            (
                f"{sign}{_format_money(delta)} "
                f"({sign}{delta_pct:.1f}%)"
            ),
            f"{result.get('status', '')}. {elasticity_text}",
            build_simulator_curve(
                product,
                selected_price,
            ),
        )

