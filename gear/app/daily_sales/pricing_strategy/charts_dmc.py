# gear/app/daily_sales/pricing_strategy/charts_dmc.py
"""
ГРАФИКИ НА DASH MANTINE COMPONENTS.

Зачем отдельный модуль: графики Mantine визуально живут в той же
системе, что и остальной интерфейс — те же скругления, шрифты,
тултипы, легенды. Plotly рядом с Mantine всегда выглядит гостем.

ВАЖНО ПРО СОВМЕСТИМОСТЬ.

Компоненты BarChart / DonutChart / LineChart / CompositeChart /
ScatterChart появились в dash-mantine-components начиная с 0.14.
Если в проекте стоит более ранняя версия, модуль это спокойно
переживёт: charts_available() вернёт False, и приложение
отрисует прежние графики Plotly. Ничего не упадёт.
"""

from __future__ import annotations

import pandas as pd

import dash_mantine_components as dmc


# ============================================================
# ПАЛИТРА
#
# Берём из общего модуля theme.py: цвет статуса в графике,
# в таблице и в Excel должен означать одно и то же.
# ============================================================

from .theme import (  # noqa: E402
    CHART_ACCENT,
    CHART_DANGER,
    CHART_NEUTRAL,
    CHART_PRIMARY,
    CHART_SECONDARY,
    CHART_SUCCESS,
    STATUS_COLORS,
    STATUS_ORDER,
    STATUS_SHORT,
)

COLOR_WB = CHART_PRIMARY
COLOR_FBS = CHART_SECONDARY
COLOR_TRANSIT = CHART_ACCENT

COLOR_LOSS = CHART_DANGER
COLOR_RAISE = CHART_SUCCESS
COLOR_HOLD = CHART_NEUTRAL

COLOR_PRICE = CHART_PRIMARY
COLOR_BUYER = CHART_SECONDARY
COLOR_FLOOR = CHART_DANGER
COLOR_MARGIN = CHART_PRIMARY

STATUS_LABELS = STATUS_SHORT


# ============================================================
# ДОСТУПНОСТЬ КОМПОНЕНТОВ
# ============================================================

REQUIRED_COMPONENTS = (
    "BarChart",
    "DonutChart",
    "CompositeChart",
)


def charts_available() -> bool:
    """Есть ли в установленной версии DMC графики."""

    return all(
        getattr(dmc, name, None) is not None
        for name in REQUIRED_COMPONENTS
    )


def _has(name: str) -> bool:
    return getattr(dmc, name, None) is not None


# ============================================================
# ХЕЛПЕРЫ
# ============================================================

def _num(series):
    return pd.to_numeric(
        series,
        errors="coerce",
    ).fillna(0)


def _label(frame: pd.DataFrame) -> pd.Series:
    return (
        frame["brand"]
        .fillna("Без бренда")
        .astype(str)
        .str.strip()
        + " · "
        + frame["category"]
        .fillna("Без категории")
        .astype(str)
        .str.strip()
    )


def _round(value, digits=0):
    """
    Округление ДО передачи в график.

    Mantine показывает в тултипе ровно то число, которое
    получил. Без округления там появляется
    «243088.69766242165» — цифра, которую невозможно
    прочитать и стыдно показать коллеге.
    """

    try:
        value = float(value)
    except (TypeError, ValueError):
        return 0

    if value != value:
        return 0

    value = round(value, digits)

    return int(value) if digits == 0 else value


def _short(text, limit=34):
    text = str(text or "")

    if len(text) <= limit:
        return text

    return text[: limit - 1] + "…"


def _card(
    title: str,
    subtitle: str,
    body,
    *,
    extra=None,
):
    header = [
        dmc.Text(
            title,
            fw=700,
            size="md",
            style={"lineHeight": "1.2"},
        ),
        dmc.Text(
            subtitle,
            size="xs",
            c="dimmed",
            mt=2,
        ),
    ]

    return dmc.Paper(
        withBorder=True,
        radius="md",
        p="md",
        children=[
            dmc.Group(
                justify="space-between",
                align="flex-start",
                wrap="nowrap",
                children=[
                    dmc.Box(children=header),
                    extra or dmc.Box(),
                ],
            ),
            dmc.Space(h=12),
            body,
        ],
    )


def _empty(text: str, height: int = 260):
    return dmc.Center(
        h=height,
        children=dmc.Text(
            text,
            c="dimmed",
            size="sm",
        ),
    )


# ============================================================
# 1. ГДЕ ЛЕЖИТ ЗАПАС
# ============================================================

def stock_structure_chart(
    portfolio: pd.DataFrame,
    height: int = 300,
):

    if portfolio is None or portfolio.empty:
        return _empty(
            "Нет данных по товарному запасу",
            height,
        )

    work = portfolio.copy()

    for column in (
        "wb_stock",
        "fbs_stock",
        "in_transit",
        "stock_units",
    ):
        if column not in work.columns:
            work[column] = 0

        work[column] = _num(work[column])

    work["label"] = _label(work)

    work = (
        work
        .sort_values(
            "stock_units",
            ascending=False,
        )
        .head(10)
    )

    if work.empty:
        return _empty(
            "Нет данных по товарному запасу",
            height,
        )

    data = [
        {
            "label": _short(row["label"]),
            "WB": _round(row["wb_stock"]),
            "FBS": _round(row["fbs_stock"]),
            "В пути": _round(row["in_transit"]),
        }
        for _, row in work.iterrows()
    ]

    return dmc.BarChart(
        h=height,
        data=data,
        dataKey="label",
        orientation="vertical",
        type="stacked",
        withLegend=True,
        withBarValueLabel=False,
        gridAxis="x",
        yAxisProps={"width": 190},
        series=[
            {"name": "WB", "color": COLOR_WB},
            {"name": "FBS", "color": COLOR_FBS},
            {"name": "В пути", "color": COLOR_TRANSIT},
        ],
    )


# ============================================================
# 2. СТРУКТУРА РЕШЕНИЙ
# ============================================================

def decisions_chart(
    recommendations: pd.DataFrame,
    height: int = 300,
):

    if (
        recommendations is None
        or recommendations.empty
        or "status" not in recommendations.columns
    ):
        return _empty("Нет рекомендаций", height)

    counts = (
        recommendations["status"]
        .fillna("HOLD")
        .value_counts()
    )

    data = [
        {
            "name": STATUS_LABELS.get(status, status),
            "value": int(counts[status]),
            "color": STATUS_COLORS.get(
                status,
                COLOR_HOLD,
            ),
        }
        for status in STATUS_ORDER
        if status in counts.index
    ]

    if not data:
        return _empty("Нет рекомендаций", height)

    total = sum(item["value"] for item in data)

    return dmc.Center(
        dmc.DonutChart(
            h=height - 20,
            data=data,
            withLabelsLine=False,
            withTooltip=True,
            tooltipDataSource="segment",
            chartLabel=f"{total} шт.",
            thickness=26,
            paddingAngle=2,
        )
    )


# ============================================================
# 3. ГДЕ ТЕРЯЕМ ДЕНЬГИ
#
# Самый полезный график для решения: бренд × категория,
# где цена уже ниже точки безубыточности, и во сколько
# это обходится на остатке.
# ============================================================

def loss_chart(
    portfolio: pd.DataFrame,
    height: int = 300,
):

    if (
        portfolio is None
        or portfolio.empty
        or "stock_at_risk_value" not in portfolio.columns
    ):
        return _empty(
            "Нет данных по убыточным позициям",
            height,
        )

    work = portfolio.copy()

    work["stock_at_risk_value"] = _num(
        work["stock_at_risk_value"]
    )

    work["label"] = _label(work)

    work = (
        work[work["stock_at_risk_value"] > 0]
        .sort_values(
            "stock_at_risk_value",
            ascending=False,
        )
        .head(10)
    )

    if work.empty:
        return _empty(
            "Товаров ниже точки безубыточности не найдено",
            height,
        )

    data = [
        {
            "label": _short(row["label"]),
            "Потенциальный убыток, ₽": _round(
                row["stock_at_risk_value"]
            ),
        }
        for _, row in work.iterrows()
    ]

    return dmc.BarChart(
        h=height,
        data=data,
        dataKey="label",
        orientation="vertical",
        withLegend=False,
        gridAxis="x",
        yAxisProps={"width": 190},
        series=[
            {
                "name": "Потенциальный убыток, ₽",
                "color": COLOR_LOSS,
            },
        ],
    )


# ============================================================
# 4. ПОТЕНЦИАЛ МАРЖИ
# ============================================================

def margin_upside_chart(
    portfolio: pd.DataFrame,
    height: int = 300,
):

    if (
        portfolio is None
        or portfolio.empty
        or "margin_upside_day" not in portfolio.columns
    ):
        return _empty(
            "Нет данных по потенциалу маржи",
            height,
        )

    work = portfolio.copy()

    work["margin_upside_day"] = _num(
        work["margin_upside_day"]
    )

    work["label"] = _label(work)

    work = (
        work[work["margin_upside_day"] > 0]
        .sort_values(
            "margin_upside_day",
            ascending=False,
        )
        .head(10)
    )

    if work.empty:
        return _empty(
            "Положительный модельный потенциал не найден",
            height,
        )

    data = [
        {
            "label": _short(row["label"]),
            "Потенциал, ₽/день": _round(
                row["margin_upside_day"]
            ),
        }
        for _, row in work.iterrows()
    ]

    return dmc.BarChart(
        h=height,
        data=data,
        dataKey="label",
        orientation="vertical",
        withLegend=False,
        gridAxis="x",
        yAxisProps={"width": 190},
        series=[
            {
                "name": "Потенциал, ₽/день",
                "color": COLOR_RAISE,
            },
        ],
    )


# ============================================================
# 5. ИСТОРИЯ ПО ТОВАРУ
#
# Три вещи на одной оси времени: сколько продали,
# по какой цене продавали мы и сколько платил покупатель.
# Плюс горизонтальная линия минимальной цены — сразу видно
# периоды, когда товар уходил в минус.
# ============================================================

def product_history_chart(
    history: list[dict],
    *,
    breakeven=None,
    height: int = 280,
):

    if not history:
        return _empty("История продаж отсутствует", height)

    frame = pd.DataFrame(history)

    if frame.empty or "date_from" not in frame.columns:
        return _empty("История продаж отсутствует", height)

    frame["date_from"] = frame["date_from"].astype(str)

    frame = frame.sort_values("date_from")

    data = []

    for _, row in frame.iterrows():

        item = {
            "Дата": str(row.get("date_from"))[:10],

            "Продажи, шт": _round(
                pd.to_numeric(
                    row.get("sales_qty"),
                    errors="coerce",
                )
            ),
        }

        seller_price = pd.to_numeric(
            row.get("seller_price"),
            errors="coerce",
        )

        buyer_price = pd.to_numeric(
            row.get("buyer_price"),
            errors="coerce",
        )

        if seller_price and seller_price > 0:
            item["Наша цена"] = _round(seller_price)

        if buyer_price and buyer_price > 0:
            item["Цена покупателя"] = _round(buyer_price)

        data.append(item)

    series = [
        {
            "name": "Продажи, шт",
            "color": "#CBD5E1",
            "type": "bar",
            "yAxisId": "right",
        },
        {
            "name": "Наша цена",
            "color": COLOR_PRICE,
            "type": "line",
        },
        {
            "name": "Цена покупателя",
            "color": COLOR_BUYER,
            "type": "line",
        },
    ]

    reference_lines = []

    if breakeven:
        reference_lines.append(
            {
                "y": _round(breakeven),
                "label": "Минимальная цена",
                "color": COLOR_FLOOR,
            }
        )

    return dmc.CompositeChart(
        h=height,
        data=data,
        dataKey="Дата",
        withRightYAxis=True,
        rightYAxisLabel="шт.",
        yAxisLabel="₽",
        withLegend=True,
        curveType="monotone",
        strokeWidth=2,
        withDots=False,
        referenceLines=reference_lines,
        series=series,
    )


# ============================================================
# 6. СЦЕНАРИИ ЦЕНЫ ПО ТОВАРУ
# ============================================================

def scenarios_chart(
    scenarios: list[dict],
    *,
    recommended_change=None,
    height: int = 260,
):

    if not scenarios:
        return _empty("Сценарии недоступны", height)

    rows = sorted(
        scenarios,
        key=lambda item: float(
            item.get("price_change_pct") or 0
        ),
    )

    data = [
        {
            "Изменение": f"{float(row.get('price_change_pct') or 0):+.1f}%",

            "Маржа 30д, ₽": _round(
                row.get("projected_margin")
            ),

            "Продаж в день": _round(
                row.get("projected_daily_qty"),
                1,
            ),
        }
        for row in rows
    ]

    reference_lines = []

    if recommended_change is not None:
        reference_lines.append(
            {
                "x": f"{float(recommended_change):+.1f}%",
                "label": "Рекомендация",
                "color": COLOR_RAISE,
            }
        )

    return dmc.CompositeChart(
        h=height,
        data=data,
        dataKey="Изменение",
        withRightYAxis=True,
        rightYAxisLabel="шт./день",
        yAxisLabel="₽",
        withLegend=True,
        curveType="monotone",
        strokeWidth=2,
        withDots=True,
        referenceLines=reference_lines,
        series=[
            {
                "name": "Маржа 30д, ₽",
                "color": COLOR_MARGIN,
                "type": "area",
            },
            {
                "name": "Продаж в день",
                "color": COLOR_TRANSIT,
                "type": "line",
                "yAxisId": "right",
            },
        ],
    )


# ============================================================
# СЕКЦИЯ ГРАФИКОВ
# ============================================================

def dmc_charts_section(
    portfolio: pd.DataFrame,
    recommendations: pd.DataFrame,
):
    """
    Четыре карточки: где лежит запас, где теряем деньги,
    структура решений, где потенциал.

    Возвращает None, если версия DMC без графиков —
    вызывающая сторона тогда рисует Plotly.
    """

    if not charts_available():
        return None

    return dmc.SimpleGrid(
        cols={"base": 1, "lg": 2},
        spacing="md",
        children=[
            _card(
                "Где сосредоточен товарный запас",
                "Топ-10 бренд × категория · WB / FBS / товар в пути",
                stock_structure_chart(portfolio),
            ),

            _card(
                "Где мы теряем деньги прямо сейчас",
                "Потенциальный убыток на остатке при текущей цене",
                loss_chart(portfolio),
            ),

            _card(
                "Что делать с ассортиментом",
                "Распределение артикулов по рекомендованному действию",
                decisions_chart(recommendations),
            ),

            _card(
                "Где потенциал дополнительной маржи",
                "Топ-10 бренд × категория · модельный эффект в день",
                margin_upside_chart(portfolio),
            ),
        ],
    )
