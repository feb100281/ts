# gear/app/daily_sales/ai_analysis/charts.py
from __future__ import annotations

from typing import Any

import plotly.graph_objects as go
import pandas as pd
import plotly.graph_objects as go





def build_daily_comparison_chart(
    current_rows: list[dict],
    previous_rows: list[dict],
) -> go.Figure:
    current_df = pd.DataFrame(current_rows).copy()
    previous_df = pd.DataFrame(previous_rows).copy()

    # -----------------------------
    # Цвета графика
    # -----------------------------
    current_color = "#2563EB"
    current_fill = "rgba(37, 99, 235, 0.08)"

    previous_color = "#94A3B8"

    grid_color = "#E9EDF2"
    text_color = "#344054"
    muted_text_color = "#667085"

    fig = go.Figure()

    # -----------------------------
    # Вспомогательные функции
    # -----------------------------
    def prepare_dataframe(df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df

        df = df.copy()

        df["date"] = pd.to_datetime(
            df["date"],
            errors="coerce",
        )

        numeric_columns = [
            "revenue",
            "sales_amount",
            "returns_amount",
        ]

        for column in numeric_columns:
            if column not in df.columns:
                df[column] = 0

            df[column] = pd.to_numeric(
                df[column],
                errors="coerce",
            ).fillna(0)

        df = (
            df
            .dropna(subset=["date"])
            .sort_values("date")
            .reset_index(drop=True)
        )

        df["period_day"] = range(1, len(df) + 1)

        return df

    def get_period_label(
        df: pd.DataFrame,
        title: str,
    ) -> str:
        if df.empty:
            return title

        start_date = df["date"].min()
        end_date = df["date"].max()

        if pd.isna(start_date) or pd.isna(end_date):
            return title

        if start_date == end_date:
            return (
                f"{title}: "
                f"{start_date.strftime('%d.%m.%Y')}"
            )

        return (
            f"{title}: "
            f"{start_date.strftime('%d.%m.%Y')}–"
            f"{end_date.strftime('%d.%m.%Y')}"
        )

    def format_compact_money(value: float) -> str:
        value = float(value or 0)
        abs_value = abs(value)

        if abs_value >= 1_000_000:
            formatted = f"{value / 1_000_000:.1f} млн ₽"
        elif abs_value >= 1_000:
            formatted = f"{value / 1_000:.0f} тыс. ₽"
        else:
            formatted = f"{value:,.0f} ₽"

        return (
            formatted
            .replace(",", " ")
            .replace(".", ",")
        )

    current_df = prepare_dataframe(current_df)
    previous_df = prepare_dataframe(previous_df)

    current_name = get_period_label(
        current_df,
        "Текущий период",
    )

    previous_name = get_period_label(
        previous_df,
        "Сравниваемый период",
    )

    # -----------------------------
    # Сравниваемый период
    # Добавляем первым, чтобы текущий
    # период визуально был сверху
    # -----------------------------
    if not previous_df.empty:
        fig.add_trace(
            go.Scatter(
                x=previous_df["period_day"],
                y=previous_df["revenue"],
                mode="lines+markers",
                name=previous_name,
                line={
                    "color": previous_color,
                    "width": 2,
                    "dash": "dot",
                    "shape": "spline",
                    "smoothing": 0.65,
                },
                marker={
                    "size": 6,
                    "color": "white",
                    "line": {
                        "color": previous_color,
                        "width": 1.5,
                    },
                },
                customdata=previous_df[
                    [
                        "date",
                        "sales_amount",
                        "returns_amount",
                    ]
                ].to_numpy(),
                hovertemplate=(
                    "<b>%{customdata[0]|%d.%m.%Y}</b>"
                    "<br><br>"
                    "Чистая выручка: <b>%{y:,.0f} ₽</b><br>"
                    "Продажи: %{customdata[1]:,.0f} ₽<br>"
                    "Возвраты: %{customdata[2]:,.0f} ₽"
                    "<extra></extra>"
                ),
                hoverlabel={
                    "bgcolor": "white",
                    "bordercolor": previous_color,
                    "font": {
                        "color": text_color,
                        "size": 12,
                    },
                },
            )
        )

    # -----------------------------
    # Текущий период
    # -----------------------------
    if not current_df.empty:
        fig.add_trace(
            go.Scatter(
                x=current_df["period_day"],
                y=current_df["revenue"],
                mode="lines+markers",
                name=current_name,
                line={
                    "color": current_color,
                    "width": 3,
                    "shape": "spline",
                    "smoothing": 0.65,
                },
                marker={
                    "size": 7,
                    "color": current_color,
                    "line": {
                        "color": "white",
                        "width": 1.5,
                    },
                },
                fill="tozeroy",
                fillcolor=current_fill,
                customdata=current_df[
                    [
                        "date",
                        "sales_amount",
                        "returns_amount",
                    ]
                ].to_numpy(),
                hovertemplate=(
                    "<b>%{customdata[0]|%d.%m.%Y}</b>"
                    "<br><br>"
                    "Чистая выручка: <b>%{y:,.0f} ₽</b><br>"
                    "Продажи: %{customdata[1]:,.0f} ₽<br>"
                    "Возвраты: %{customdata[2]:,.0f} ₽"
                    "<extra></extra>"
                ),
                hoverlabel={
                    "bgcolor": "white",
                    "bordercolor": current_color,
                    "font": {
                        "color": text_color,
                        "size": 12,
                    },
                },
            )
        )

    # -----------------------------
    # Подписи последних значений
    # -----------------------------
    if not previous_df.empty:
        last_previous = previous_df.iloc[-1]

        fig.add_annotation(
            x=last_previous["period_day"],
            y=last_previous["revenue"],
            text=format_compact_money(
                last_previous["revenue"]
            ),
            showarrow=False,
            xanchor="right",
            yanchor="bottom",
            xshift=-8,
            yshift=8,
            bgcolor="rgba(255, 255, 255, 0.88)",
            bordercolor="rgba(148, 163, 184, 0.45)",
            borderwidth=1,
            borderpad=5,
            font={
                "size": 11,
                "color": muted_text_color,
            },
        )

    if not current_df.empty:
        last_current = current_df.iloc[-1]

        fig.add_annotation(
            x=last_current["period_day"],
            y=last_current["revenue"],
            text=f"<b>{format_compact_money(last_current['revenue'])}</b>",
            showarrow=False,
            xanchor="right",
            yanchor="bottom",
            xshift=-8,
            yshift=8,
            bgcolor="rgba(255, 255, 255, 0.92)",
            bordercolor="rgba(37, 99, 235, 0.35)",
            borderwidth=1,
            borderpad=5,
            font={
                "size": 11,
                "color": current_color,
            },
        )

    # -----------------------------
    # Настройка осей
    # -----------------------------
    max_days = max(
        len(current_df),
        len(previous_df),
        1,
    )

    # Чтобы подписи последних точек
    # не упирались в правый край
    x_range_end = max_days + max(0.6, max_days * 0.025)

    fig.update_layout(
        height=410,
        margin={
            "l": 25,
            "r": 30,
            "t": 68,
            "b": 45,
        },
        paper_bgcolor="white",
        plot_bgcolor="white",
        hovermode="x unified",
        font={
            "family": (
                "Inter, -apple-system, BlinkMacSystemFont, "
                "'Segoe UI', sans-serif"
            ),
            "color": text_color,
            "size": 12,
        },
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.04,
            "xanchor": "left",
            "x": 0,
            "font": {
                "size": 11,
                "color": text_color,
            },
            "itemsizing": "constant",
            "traceorder": "reversed",
        },
        hoverlabel={
            "namelength": -1,
            "align": "left",
        },
        xaxis={
            "title": {
                "text": "День периода",
                "font": {
                    "size": 11,
                    "color": muted_text_color,
                },
                "standoff": 12,
            },
            "range": [0.7, x_range_end],
            "tickmode": "linear",
            "dtick": 1 if max_days <= 16 else 2,
            "tickfont": {
                "size": 11,
                "color": muted_text_color,
            },
            "showgrid": False,
            "showline": True,
            "linecolor": "#D7DCE2",
            "linewidth": 1,
            "ticks": "",
            "zeroline": False,
            "fixedrange": True,
        },
        yaxis={
            "title": {
                "text": "Чистая выручка, ₽",
                "font": {
                    "size": 11,
                    "color": muted_text_color,
                },
                "standoff": 8,
            },
            "tickformat": "~s",
            "separatethousands": True,
            "tickfont": {
                "size": 11,
                "color": muted_text_color,
            },
            "showgrid": True,
            "gridcolor": grid_color,
            "gridwidth": 1,
            "showline": False,
            "zeroline": True,
            "zerolinecolor": "#C9D0D8",
            "zerolinewidth": 1,
            "rangemode": "tozero",
            "fixedrange": True,
        },
        modebar={
            "orientation": "v",
            "bgcolor": "rgba(255,255,255,0.85)",
            "color": muted_text_color,
            "activecolor": current_color,
        },
    )

    return fig



def build_entity_delta_chart(
    rows: list[dict],
    title_name: str,
) -> go.Figure:
    # ---------------------------------------------------------
    # Палитра
    # ---------------------------------------------------------
    positive_fill = "rgba(21, 94, 65, 0.72)"
    positive_border = "#155E41"

    negative_fill = "rgba(190, 24, 93, 0.62)"
    negative_border = "#BE185D"

    text_color = "#344054"
    muted_color = "#667085"
    grid_color = "#E8ECF1"
    zero_line_color = "#98A2B3"

    # ---------------------------------------------------------
    # Вспомогательные функции
    # ---------------------------------------------------------
    def safe_float(value, default: float = 0.0) -> float:
        try:
            if value is None:
                return default
            return float(value)
        except (TypeError, ValueError):
            return default

    def format_money(value: float, signed: bool = False) -> str:
        value = safe_float(value)

        if signed:
            if value > 0:
                sign = "+"
            elif value < 0:
                sign = "−"
            else:
                sign = ""
        else:
            sign = "−" if value < 0 else ""

        formatted = f"{abs(value):,.0f}".replace(",", " ")

        return f"{sign}{formatted} ₽"

    def format_percent(value: float, signed: bool = False) -> str:
        value = safe_float(value)

        if signed:
            if value > 0:
                sign = "+"
            elif value < 0:
                sign = "−"
            else:
                sign = ""
        else:
            sign = ""

        return (
            f"{sign}{abs(value):.1f}%"
            .replace(".", ",")
        )

    def format_compact_money(
        value: float,
        signed: bool = True,
    ) -> str:
        value = safe_float(value)

        if signed:
            if value > 0:
                sign = "+"
            elif value < 0:
                sign = "−"
            else:
                sign = ""
        else:
            sign = "−" if value < 0 else ""

        abs_value = abs(value)

        if abs_value >= 1_000_000_000:
            result = f"{abs_value / 1_000_000_000:.1f} млрд ₽"
        elif abs_value >= 1_000_000:
            result = f"{abs_value / 1_000_000:.1f} млн ₽"
        elif abs_value >= 1_000:
            result = f"{abs_value / 1_000:.0f} тыс. ₽"
        else:
            result = f"{abs_value:,.0f} ₽"

        return (
            f"{sign}{result}"
            .replace(",", " ")
            .replace(".", ",")
        )

    # ---------------------------------------------------------
    # Подготовка данных
    # ---------------------------------------------------------
    data = [
        row
        for row in rows
        if safe_float(row.get("revenue_delta")) != 0
    ]

    # Берём 15 самых существенных изменений по модулю
    data = sorted(
        data,
        key=lambda row: abs(
            safe_float(row.get("revenue_delta"))
        ),
        reverse=True,
    )[:15]

    # Для горизонтального графика сортируем снизу вверх
    data = sorted(
        data,
        key=lambda row: safe_float(
            row.get("revenue_delta")
        ),
    )

    # ---------------------------------------------------------
    # Пустое состояние
    # ---------------------------------------------------------
    if not data:
        fig = go.Figure()

        fig.add_annotation(
            x=0.5,
            y=0.5,
            xref="paper",
            yref="paper",
            text="Нет изменений для отображения",
            showarrow=False,
            font={
                "size": 13,
                "color": muted_color,
            },
        )

        fig.update_layout(
            height=360,
            margin={
                "l": 20,
                "r": 20,
                "t": 20,
                "b": 20,
            },
            paper_bgcolor="white",
            plot_bgcolor="white",
            xaxis={"visible": False},
            yaxis={"visible": False},
        )

        return fig

    # ---------------------------------------------------------
    # Основные массивы
    # ---------------------------------------------------------
    names = [
        str(row.get("name", "Без названия"))
        for row in data
    ]

    values = [
        safe_float(row.get("revenue_delta"))
        for row in data
    ]

    fill_colors = [
        positive_fill if value > 0 else negative_fill
        for value in values
    ]

    border_colors = [
        positive_border if value > 0 else negative_border
        for value in values
    ]

    # Передаём в customdata уже готовые строки.
    # Так разделители тысяч и десятичные знаки всегда будут аккуратными.
    customdata = [
        [
            format_money(
                row.get("current_revenue", 0)
            ),
            format_money(
                row.get("previous_revenue", 0)
            ),
            format_money(
                row.get("revenue_delta", 0),
                signed=True,
            ),
            format_percent(
                row.get("revenue_change_pct", 0),
                signed=True,
            ),
            format_percent(
                row.get("current_return_rate", 0),
            ),
            format_percent(
                row.get("previous_return_rate", 0),
            ),
        ]
        for row in data
    ]

    # ---------------------------------------------------------
    # Основной график
    # ---------------------------------------------------------
    fig = go.Figure(
        go.Bar(
            x=values,
            y=names,
            orientation="h",
            marker={
                "color": fill_colors,
                "line": {
                    "color": border_colors,
                    "width": 1,
                },
            },
            customdata=customdata,
            hovertemplate=(
                "<b>%{y}</b>"
                "<br><br>"
                "Текущий период: "
                "<b>%{customdata[0]}</b><br>"
                "Предыдущий период: "
                "%{customdata[1]}<br>"
                "Дельта выручки: "
                "<b>%{customdata[2]}</b><br>"
                "Изменение: "
                "<b>%{customdata[3]}</b><br>"
                "<br>"
                "Возвраты, текущий: "
                "%{customdata[4]}<br>"
                "Возвраты, предыдущий: "
                "%{customdata[5]}"
                "<extra></extra>"
            ),
            hoverlabel={
                "bgcolor": "white",
                "bordercolor": "#D0D5DD",
                "font": {
                    "size": 12,
                    "color": text_color,
                },
                "align": "left",
            },
        )
    )

    # ---------------------------------------------------------
    # Подписи на столбцах
    # ---------------------------------------------------------
    for row, value, border_color in zip(
        data,
        values,
        border_colors,
    ):
        label = format_compact_money(
            value,
            signed=True,
        )

        fig.add_annotation(
            x=value,
            y=str(row.get("name", "Без названия")),
            text=f"<b>{label}</b>",
            showarrow=False,
            xanchor="left" if value >= 0 else "right",
            yanchor="middle",
            xshift=10 if value >= 0 else -10,
            bgcolor="rgba(255, 255, 255, 0.92)",
            bordercolor=border_color,
            borderwidth=1,
            borderpad=4,
            font={
                "size": 10,
                "color": border_color,
            },
        )

    # ---------------------------------------------------------
    # Диапазон оси с запасом под подписи
    # ---------------------------------------------------------
    min_value = min(values)
    max_value = max(values)

    max_abs_value = max(
        max(abs(value) for value in values),
        100_000,
    )

    padding = max_abs_value * 0.30

    x_min = min(
        min_value - padding,
        -padding * 0.20,
    )

    x_max = max(
        max_value + padding,
        padding * 0.20,
    )

    # ---------------------------------------------------------
    # Layout
    # ---------------------------------------------------------
    fig.update_layout(
        height=max(
            390,
            len(data) * 35 + 115,
        ),
        margin={
            "l": 20,
            "r": 115,
            "t": 18,
            "b": 62,
        },
        paper_bgcolor="white",
        plot_bgcolor="white",
        showlegend=False,
        bargap=0.38,
        font={
            "family": (
                "Inter, -apple-system, BlinkMacSystemFont, "
                "'Segoe UI', sans-serif"
            ),
            "size": 12,
            "color": text_color,
        },
        hoverlabel={
            "namelength": -1,
        },
        xaxis={
            "title": {
                "text": "Вклад в изменение чистой выручки, ₽",
                "font": {
                    "size": 11,
                    "color": muted_color,
                },
                "standoff": 16,
            },
            "range": [x_min, x_max],
            "tickformat": "~s",
            "tickfont": {
                "size": 10,
                "color": muted_color,
            },
            "showgrid": True,
            "gridcolor": grid_color,
            "gridwidth": 1,
            "zeroline": True,
            "zerolinecolor": zero_line_color,
            "zerolinewidth": 1.2,
            "showline": False,
            "ticks": "",
            "fixedrange": True,
        },
        yaxis={
            "title": {
                "text": title_name,
                "font": {
                    "size": 11,
                    "color": muted_color,
                },
                "standoff": 10,
            },
            "showgrid": False,
            "automargin": True,
            "tickfont": {
                "size": 11,
                "color": text_color,
            },
            "fixedrange": True,
        },
        modebar={
            "orientation": "v",
            "bgcolor": "rgba(255, 255, 255, 0.88)",
            "color": muted_color,
            "activecolor": positive_border,
        },
    )

    return fig



# ---------------------------------------------------------
# Палитра
# ---------------------------------------------------------

DRIVER_POSITIVE_COLOR = "rgba(22, 138, 99, 0.78)"
DRIVER_POSITIVE_BORDER = "rgba(22, 138, 99, 1)"

DRIVER_NEGATIVE_COLOR = "rgba(214, 69, 80, 0.76)"
DRIVER_NEGATIVE_BORDER = "rgba(214, 69, 80, 1)"

DRIVER_NEUTRAL_COLOR = "rgba(132, 146, 166, 0.68)"
DRIVER_NEUTRAL_BORDER = "rgba(132, 146, 166, 1)"

DRIVER_TEXT_COLOR = "#344054"
DRIVER_MUTED_COLOR = "#667085"
DRIVER_GRID_COLOR = "#EAECF0"
DRIVER_ZERO_LINE_COLOR = "#667085"


# ---------------------------------------------------------
# Вспомогательные функции
# ---------------------------------------------------------

def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _calculate_change_pct(
    current_value: float,
    previous_value: float,
) -> float:
    """
    Процент изменения относительно предыдущего периода.

    Если предыдущий показатель равен нулю:
    - оба значения 0 -> 0%;
    - текущее значение не равно 0 -> 100%.
    """
    current_value = _safe_float(current_value)
    previous_value = _safe_float(previous_value)

    if previous_value == 0:
        return 0.0 if current_value == 0 else 100.0

    return (
        (current_value - previous_value)
        / abs(previous_value)
        * 100
    )


def _format_money(value: float) -> str:
    value = _safe_float(value)

    return (
        f"{value:,.0f} ₽"
        .replace(",", " ")
    )


def _format_quantity(value: float) -> str:
    value = _safe_float(value)

    return (
        f"{value:,.0f} шт."
        .replace(",", " ")
    )


def _format_percent(value: float) -> str:
    value = _safe_float(value)

    if value > 0:
        result = f"+{value:.1f}%"
    elif value < 0:
        result = f"−{abs(value):.1f}%"
    else:
        result = "0,0%"

    return result.replace(".", ",")


def _format_value(
    value: float,
    value_type: str,
) -> str:
    if value_type == "quantity":
        return _format_quantity(value)

    if value_type == "percent":
        return (
            f"{_safe_float(value):.1f}%"
            .replace(".", ",")
        )

    return _format_money(value)


def _format_delta(
    value: float,
    value_type: str,
) -> str:
    value = _safe_float(value)

    if value > 0:
        sign = "+"
    elif value < 0:
        sign = "−"
    else:
        sign = ""

    formatted_value = _format_value(
        abs(value),
        value_type,
    )

    return f"{sign}{formatted_value}"


def _get_bar_colors(
    value: float,
) -> tuple[str, str]:
    if value > 0:
        return (
            DRIVER_POSITIVE_COLOR,
            DRIVER_POSITIVE_BORDER,
        )

    if value < 0:
        return (
            DRIVER_NEGATIVE_COLOR,
            DRIVER_NEGATIVE_BORDER,
        )

    return (
        DRIVER_NEUTRAL_COLOR,
        DRIVER_NEUTRAL_BORDER,
    )


# ---------------------------------------------------------
# Формирование данных для графика
# ---------------------------------------------------------

def build_revenue_drivers(
    current: dict,
    previous: dict,
) -> list[dict]:
    """
    Формирует драйверы на основании результата get_period_comparison().

    current и previous — словари из get_sales_metrics().
    """

    driver_definitions = [
        {
            "name": "Чистая выручка",
            "field": "revenue",
            "value_type": "money",
        },
        {
            "name": "Продажи",
            "field": "sales_amount",
            "value_type": "money",
        },
        {
            "name": "Возвраты",
            "field": "returns_amount",
            "value_type": "money",
            # Рост возвратов является негативным фактором.
            "reverse_direction": True,
        },
        {
            "name": "Количество продаж",
            "field": "quantity",
            "value_type": "quantity",
        },
        {
            "name": "Средняя цена",
            "field": "average_price",
            "value_type": "money",
        },
        {
            "name": "Доля возвратов",
            "field": "return_rate",
            "value_type": "percent",
            # Рост доли возвратов является негативным фактором.
            "reverse_direction": True,
        },
    ]

    result = []

    for definition in driver_definitions:
        field = definition["field"]

        current_value = _safe_float(
            current.get(field)
        )

        previous_value = _safe_float(
            previous.get(field)
        )

        delta = current_value - previous_value

        change_pct = _calculate_change_pct(
            current_value=current_value,
            previous_value=previous_value,
        )

        visual_change_pct = change_pct

        if definition.get("reverse_direction"):
            visual_change_pct = -change_pct

        result.append(
            {
                "name": definition["name"],
                "current_value": current_value,
                "previous_value": previous_value,
                "delta": delta,
                "change_pct": change_pct,
                "visual_change_pct": visual_change_pct,
                "value_type": definition["value_type"],
            }
        )

    return result


# ---------------------------------------------------------
# График драйверов
# ---------------------------------------------------------

def build_driver_chart(
    drivers: list[dict],
) -> go.Figure:
    prepared_data = []

    for row in drivers:
        current_value = _safe_float(
            row.get("current_value")
        )

        previous_value = _safe_float(
            row.get("previous_value")
        )

        delta = _safe_float(
            row.get(
                "delta",
                current_value - previous_value,
            )
        )

        change_pct = _safe_float(
            row.get(
                "change_pct",
                _calculate_change_pct(
                    current_value,
                    previous_value,
                ),
            )
        )

        # visual_change_pct нужен для возвратов:
        # рост возвратов будет отображаться красным,
        # хотя обычный change_pct у них положительный.
        visual_change_pct = _safe_float(
            row.get(
                "visual_change_pct",
                change_pct,
            )
        )

        value_type = row.get(
            "value_type",
            "money",
        )

        fill_color, border_color = (
            _get_bar_colors(visual_change_pct)
        )

        prepared_data.append(
            {
                "name": str(
                    row.get("name", "Без названия")
                ),
                "current_value": current_value,
                "previous_value": previous_value,
                "delta": delta,
                "change_pct": change_pct,
                "visual_change_pct": visual_change_pct,
                "value_type": value_type,
                "fill_color": fill_color,
                "border_color": border_color,
                "current_text": _format_value(
                    current_value,
                    value_type,
                ),
                "previous_text": _format_value(
                    previous_value,
                    value_type,
                ),
                "delta_text": _format_delta(
                    delta,
                    value_type,
                ),
                "change_text": _format_percent(
                    change_pct
                ),
                "label_text": _format_percent(
                    visual_change_pct
                ),
            }
        )

    if not prepared_data:
        fig = go.Figure()

        fig.add_annotation(
            x=0.5,
            y=0.5,
            xref="paper",
            yref="paper",
            text="Нет данных для отображения",
            showarrow=False,
            font={
                "size": 13,
                "color": DRIVER_MUTED_COLOR,
            },
        )

        fig.update_layout(
            height=290,
            margin={
                "l": 20,
                "r": 20,
                "t": 20,
                "b": 20,
            },
            paper_bgcolor="white",
            plot_bgcolor="white",
            xaxis={"visible": False},
            yaxis={"visible": False},
        )

        return fig

    # Маленькие значения снизу, большие сверху.
    prepared_data = sorted(
        prepared_data,
        key=lambda item: item["visual_change_pct"],
    )

    names = [
        item["name"]
        for item in prepared_data
    ]

    values = [
        item["visual_change_pct"]
        for item in prepared_data
    ]

    fill_colors = [
        item["fill_color"]
        for item in prepared_data
    ]

    border_colors = [
        item["border_color"]
        for item in prepared_data
    ]

    customdata = [
        [
            item["current_text"],
            item["previous_text"],
            item["delta_text"],
            item["change_text"],
        ]
        for item in prepared_data
    ]

    fig = go.Figure(
        go.Bar(
            x=values,
            y=names,
            orientation="h",
            marker={
                "color": fill_colors,
                "line": {
                    "color": border_colors,
                    "width": 1,
                },
            },
            customdata=customdata,
            hovertemplate=(
                "<b>%{y}</b>"
                "<br><br>"
                "Текущий период: "
                "<b>%{customdata[0]}</b><br>"
                "Предыдущий период: "
                "%{customdata[1]}<br>"
                "Дельта: "
                "<b>%{customdata[2]}</b><br>"
                "Изменение: "
                "<b>%{customdata[3]}</b>"
                "<extra></extra>"
            ),
            hoverlabel={
                "bgcolor": "white",
                "bordercolor": "#D0D5DD",
                "font": {
                    "size": 12,
                    "color": DRIVER_TEXT_COLOR,
                },
                "align": "left",
            },
        )
    )

    # -----------------------------------------------------
    # Подписи на полупрозрачной подложке
    # -----------------------------------------------------

    for index, item in enumerate(prepared_data):
        value = item["visual_change_pct"]

        is_positive = value >= 0

        fig.add_annotation(
            x=value,
            y=item["name"],
            text=f"<b>{item['label_text']}</b>",
            showarrow=False,
            xanchor="left" if is_positive else "right",
            yanchor="middle",
            xshift=9 if is_positive else -9,
            bgcolor="rgba(255, 255, 255, 0.90)",
            bordercolor=item["border_color"],
            borderwidth=1,
            borderpad=4,
            font={
                "size": 10,
                "color": item["border_color"],
            },
        )

    # -----------------------------------------------------
    # Диапазон оси с запасом под подписи
    # -----------------------------------------------------

    min_value = min(values)
    max_value = max(values)

    max_abs_value = max(
        abs(min_value),
        abs(max_value),
        10,
    )

    axis_padding = max_abs_value * 0.32

    x_min = min(
        min_value - axis_padding,
        -axis_padding * 0.35,
    )

    x_max = max(
        max_value + axis_padding,
        axis_padding * 0.35,
    )

    fig.update_layout(
        height=max(
            300,
            len(prepared_data) * 42 + 90,
        ),
        margin={
            "l": 20,
            "r": 65,
            "t": 15,
            "b": 55,
        },
        paper_bgcolor="white",
        plot_bgcolor="white",
        showlegend=False,
        bargap=0.38,
        font={
            "family": (
                "Inter, -apple-system, BlinkMacSystemFont, "
                "'Segoe UI', sans-serif"
            ),
            "size": 12,
            "color": DRIVER_TEXT_COLOR,
        },
        xaxis={
            "title": {
                "text": "Изменение к сопоставимому периоду",
                "font": {
                    "size": 11,
                    "color": DRIVER_MUTED_COLOR,
                },
                "standoff": 14,
            },
            "range": [x_min, x_max],
            "ticksuffix": "%",
            "tickfont": {
                "size": 10,
                "color": DRIVER_MUTED_COLOR,
            },
            "showgrid": True,
            "gridcolor": DRIVER_GRID_COLOR,
            "gridwidth": 1,
            "zeroline": True,
            "zerolinecolor": DRIVER_ZERO_LINE_COLOR,
            "zerolinewidth": 1.2,
            "showline": False,
            "fixedrange": True,
        },
        yaxis={
            "showgrid": False,
            "automargin": True,
            "tickfont": {
                "size": 11,
                "color": DRIVER_TEXT_COLOR,
            },
            "fixedrange": True,
        },
        hoverlabel={
            "namelength": -1,
        },
        modebar={
            "orientation": "v",
            "bgcolor": "rgba(255, 255, 255, 0.85)",
            "color": DRIVER_MUTED_COLOR,
            "activecolor": DRIVER_POSITIVE_BORDER,
        },
    )

    return fig
