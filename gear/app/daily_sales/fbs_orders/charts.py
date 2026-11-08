# gear/app/daily_sales/fbs_orders/charts.py
"""
Графики анализа заказов FBS.

Правила оформления одинаковы для всех графиков: тонкие метки,
приглушённая сетка, подписи значений прямо на метках вместо
второй оси, текст нейтральным цветом, цвет метки отвечает
только за состояние.

Палитра проверена на различимость при дальтонизме: синий
#2A78D6, «внимание» #EC835A, «критично» #D03B3B — худшая пара
по CVD ΔE 13.9 при пороге 8.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from .config import (
    HOUR_BUCKET_OVERFLOW,
    SLA_LIMIT_HOURS,
    SLA_WARNING_HOURS,
)


# ============================================================
# ПАЛИТРА ГРАФИКОВ
# ============================================================

SERIES_BLUE = "#2A78D6"
SERIES_ORANGE = "#EB6834"

STATUS_GOOD = "#0CA30C"
STATUS_WARNING = "#FAB219"
STATUS_SERIOUS = "#EC835A"
STATUS_CRITICAL = "#D03B3B"

INK_PRIMARY = "#0B0B0B"
INK_SECONDARY = "#52514E"
INK_MUTED = "#898781"
GRIDLINE = "#E1E0D9"
AXIS_LINE = "#C3C2B7"
SURFACE = "#FFFFFF"

FONT_FAMILY = (
    'system-ui, -apple-system, "Segoe UI", sans-serif'
)


def _base_layout(height, margin_left=150):
    return dict(
        height=height,
        paper_bgcolor=SURFACE,
        plot_bgcolor=SURFACE,
        font=dict(
            family=FONT_FAMILY,
            size=12,
            color=INK_SECONDARY,
        ),
        margin=dict(l=margin_left, r=28, t=16, b=36),
        showlegend=False,
        hoverlabel=dict(
            bgcolor=SURFACE,
            bordercolor=AXIS_LINE,
            font=dict(
                family=FONT_FAMILY,
                size=12,
                color=INK_PRIMARY,
            ),
        ),
    )


def _thousands(value) -> str:
    try:
        return f"{int(round(float(value))):,}".replace(",", " ")
    except (TypeError, ValueError):
        return ""


def _empty_figure(text="Нет данных"):
    figure = go.Figure()

    figure.add_annotation(
        text=text,
        showarrow=False,
        font=dict(family=FONT_FAMILY, size=13, color=INK_MUTED),
    )

    figure.update_layout(
        **_base_layout(180, margin_left=28),
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
    )

    return figure


# ============================================================
# 1. СРОКИ СБОРКИ
# ============================================================

def _bucket_color(label: str) -> str:
    """
    Цвет отвечает за состояние, а не за порядок.

    До порога внимания — обычный синий, «жёлтая зона» между
    порогом и нормативом — оранжевый, сверх норматива —
    красный. Подпись корзины всегда рядом, поэтому смысл
    не держится на одном цвете.
    """
    if label == HOUR_BUCKET_OVERFLOW:
        return STATUS_CRITICAL

    digits = [
        int(part)
        for part in label.replace("–", " ").replace("+", " ").split()
        if part.isdigit()
    ]

    upper = max(digits) if digits else 0

    if upper > SLA_LIMIT_HOURS:
        return STATUS_CRITICAL

    if upper > SLA_WARNING_HOURS:
        return STATUS_SERIOUS

    return SERIES_BLUE


def assembly_buckets_figure(df: pd.DataFrame):
    """Сколько заказов в каждой корзине времени сборки."""
    if df is None or df.empty:
        return _empty_figure("Нет заказов на сборке")

    data = df.sort_values("time_sort", ascending=False)

    labels = data["time_group"].tolist()
    values = data["orders"].tolist()
    shares = data["share_pct"].tolist()
    hours = data["avg_hours"].tolist()

    colors = [_bucket_color(label) for label in labels]

    figure = go.Figure(
        go.Bar(
            x=values,
            y=labels,
            orientation="h",
            marker=dict(
                color=colors,
                line=dict(width=0),
            ),
            width=0.62,
            text=[
                f"{_thousands(v)}  ·  {s:.1f} %"
                for v, s in zip(values, shares)
            ],
            textposition="outside",
            textfont=dict(
                family=FONT_FAMILY,
                size=12,
                color=INK_SECONDARY,
            ),
            cliponaxis=False,
            customdata=list(zip(shares, hours)),
            hovertemplate=(
                "<b>%{y}</b><br>"
                "Заказов: %{x}<br>"
                "Доля: %{customdata[0]:.2f} %<br>"
                "Средние часы: %{customdata[1]:.1f}"
                "<extra></extra>"
            ),
        )
    )

    figure.update_layout(
        **_base_layout(max(240, 46 * len(labels) + 60)),
        bargap=0.34,
        xaxis=dict(
            showgrid=True,
            gridcolor=GRIDLINE,
            gridwidth=1,
            zeroline=False,
            showline=False,
            ticks="",
            tickfont=dict(size=11, color=INK_MUTED),
            rangemode="tozero",
        ),
        yaxis=dict(
            showgrid=False,
            zeroline=False,
            showline=False,
            ticks="",
            tickfont=dict(size=12, color=INK_PRIMARY),
        ),
    )

    return figure


# ============================================================
# 2. ДИНАМИКА ПО ДНЯМ
# ============================================================

def daily_orders_figure(df: pd.DataFrame, days=60):
    """
    Заказы и отмены по дням.

    Две линии на одной оси: отмены — часть заказов, поэтому
    вторая шкала здесь была бы враньём.
    """
    if df is None or df.empty:
        return _empty_figure("Нет заказов за период")

    data = (
        df.sort_values("order_date")
        .tail(days)
        .copy()
    )

    dates = pd.to_datetime(data["order_date"])

    figure = go.Figure()

    figure.add_trace(
        go.Scatter(
            x=dates,
            y=data["orders"],
            name="Заказов",
            mode="lines",
            line=dict(color=SERIES_BLUE, width=2),
            hovertemplate="Заказов: %{y}<extra></extra>",
        )
    )

    figure.add_trace(
        go.Scatter(
            x=dates,
            y=data["cancelled_orders"],
            name="Отменено",
            mode="lines",
            line=dict(color=SERIES_ORANGE, width=2),
            hovertemplate="Отменено: %{y}<extra></extra>",
        )
    )

    layout = _base_layout(300, margin_left=56)
    layout["showlegend"] = True
    layout["margin"]["t"] = 40

    figure.update_layout(
        **layout,
        hovermode="x unified",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
            font=dict(size=12, color=INK_SECONDARY),
            bgcolor="rgba(0,0,0,0)",
        ),
        xaxis=dict(
            showgrid=False,
            zeroline=False,
            showline=True,
            linecolor=AXIS_LINE,
            ticks="",
            tickfont=dict(size=11, color=INK_MUTED),
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor=GRIDLINE,
            gridwidth=1,
            zeroline=False,
            showline=False,
            ticks="",
            tickfont=dict(size=11, color=INK_MUTED),
            rangemode="tozero",
        ),
    )

    return figure


# ============================================================
# 3. НАПРАВЛЕНИЯ ЛОГИСТИКИ
# ============================================================

def logistics_figure(df: pd.DataFrame, top=12):
    """
    Крупнейшие направления «склад → пункт выдачи».

    Одна серия, один цвет: сравнивается величина, а не
    принадлежность. Направления с просрочкой окрашены
    красным и названы в подсказке.
    """
    if df is None or df.empty:
        return _empty_figure("Нет данных по направлениям")

    # Складываем строки, которые попадают в одну подпись.
    # В таблице строка — это «склад × пункт × ID пункта», и у
    # одного пункта выдачи бывает несколько ID. Без свёртки
    # plotly кладёт такие строки в одну категорию друг на
    # друга, и столбик показывает сумму, а цвет — только
    # последнюю строку. Именно так и получался столбик,
    # наполовину синий и наполовину красный.
    place = (
        "destination_office"
        if "destination_office" in df.columns
        else "office_name"
    )

    grouped = (
        df.groupby(["warehouse", place], as_index=False)
        .agg(
            orders=("orders", "sum"),
            orders_overdue=("orders_overdue", "sum"),
            avg_hours=("avg_hours", "mean"),
        )
    )

    data = (
        grouped.sort_values("orders", ascending=False)
        .head(top)
        .sort_values("orders")
        .copy()
    )

    labels = [
        f"{w} → {o}"
        for w, o in zip(data["warehouse"], data[place])
    ]

    overdue = data["orders_overdue"].fillna(0).tolist()

    colors = [
        STATUS_CRITICAL if value else SERIES_BLUE
        for value in overdue
    ]

    figure = go.Figure(
        go.Bar(
            x=data["orders"],
            y=labels,
            orientation="h",
            marker=dict(color=colors, line=dict(width=0)),
            width=0.62,
            text=[_thousands(v) for v in data["orders"]],
            textposition="outside",
            textfont=dict(
                family=FONT_FAMILY,
                size=12,
                color=INK_SECONDARY,
            ),
            cliponaxis=False,
            customdata=list(
                zip(overdue, data["avg_hours"].fillna(0))
            ),
            hovertemplate=(
                "<b>%{y}</b><br>"
                "Заказов: %{x}<br>"
                "Просрочено: %{customdata[0]}<br>"
                "Средние часы: %{customdata[1]:.1f}"
                "<extra></extra>"
            ),
        )
    )

    layout = _base_layout(
        max(260, 34 * len(labels) + 70),
        margin_left=250,
    )
    layout["margin"]["r"] = 80

    figure.update_layout(
        **layout,
        bargap=0.34,
        xaxis=dict(
            showgrid=True,
            gridcolor=GRIDLINE,
            gridwidth=1,
            zeroline=False,
            showline=False,
            ticks="",
            tickfont=dict(size=11, color=INK_MUTED),
            rangemode="tozero",
        ),
        yaxis=dict(
            showgrid=False,
            zeroline=False,
            showline=False,
            ticks="",
            tickfont=dict(size=11, color=INK_PRIMARY),
        ),
    )

    return figure


# ============================================================
# 4. СОСТОЯНИЯ ЗАКАЗОВ
# ============================================================

def order_state_figure(kpi: dict):
    """
    Из чего складывается общее количество заказов.

    Одна полоса на всю ширину: открытые, закрытые поставкой
    и отменённые в сумме дают общее число — это и надо
    увидеть, а не три отдельные цифры.
    """
    parts = [
        ("Открытые", kpi.get("orders_open") or 0, SERIES_BLUE),
        ("Закрыты поставкой", kpi.get("orders_closed") or 0, STATUS_GOOD),
        ("Отменены", kpi.get("orders_cancelled") or 0, STATUS_SERIOUS),
    ]

    total = sum(value for _, value, _ in parts)

    if not total:
        return _empty_figure("Нет заказов")

    figure = go.Figure()

    for name, value, color in parts:
        share = 100.0 * value / total

        figure.add_trace(
            go.Bar(
                x=[value],
                y=["Заказы"],
                orientation="h",
                name=f"{name} — {_thousands(value)}",
                marker=dict(
                    color=color,
                    line=dict(color=SURFACE, width=2),
                ),
                text=(
                    f"{_thousands(value)}"
                    if share >= 7
                    else ""
                ),
                textposition="inside",
                insidetextanchor="middle",
                textfont=dict(
                    family=FONT_FAMILY,
                    size=12,
                    color=SURFACE,
                ),
                hovertemplate=(
                    f"<b>{name}</b><br>"
                    "Заказов: %{x}<br>"
                    f"Доля: {share:.1f} %"
                    "<extra></extra>"
                ),
            )
        )

    layout = _base_layout(132, margin_left=16)
    layout["showlegend"] = True
    layout["margin"]["t"] = 44
    layout["margin"]["b"] = 16

    figure.update_layout(
        **layout,
        barmode="stack",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.05,
            xanchor="left",
            x=0,
            font=dict(size=12, color=INK_SECONDARY),
            bgcolor="rgba(0,0,0,0)",
        ),
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
    )

    return figure
