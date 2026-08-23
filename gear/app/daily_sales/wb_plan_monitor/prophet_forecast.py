# gear/app/daily_sales/wb_plan_monitor/prophet_forecast.py
from __future__ import annotations

from datetime import date, datetime, timedelta
from io import BytesIO
from typing import Any

import pandas as pd
import plotly.graph_objects as go
import xlsxwriter
import dash_mantine_components as dmc
from dash import Input, Output, State, dcc, html, no_update
from dash_iconify import DashIconify

from conns import get_duckdb_conn_with_opt

from .data import (
    get_budget_version,
    get_monthly_plan_full_year,
)

from .prophet_note import (
        build_prophet_note_pdf,
        get_prophet_note_filename,
    )


TAB_VALUE = "prophet-forecast"

START_ID = "wb-prophet-start"
END_ID = "wb-prophet-end"
GROWTH_ID = "wb-prophet-growth"
CHANGEPOINT_ID = "wb-prophet-changepoint"
SEASONALITY_ID = "wb-prophet-seasonality"
INTERVAL_ID = "wb-prophet-interval"
MODE_ID = "wb-prophet-mode"
OUTLIERS_ID = "wb-prophet-outliers"
BUILD_ID = "wb-prophet-build"
DOWNLOAD_BTN_ID = "wb-prophet-download-btn"
GRAPH_ID = "wb-prophet-graph"
PLAN_COMPARISON_GRAPH_ID = "wb-prophet-plan-comparison-graph"
KPI_ID = "wb-prophet-kpi"
STATUS_ID = "wb-prophet-status"
STORE_ID = "wb-prophet-store"
DOWNLOAD_ID = "wb-prophet-download"
PDF_DOWNLOAD_BTN_ID = "wb-prophet-pdf-download-btn"
PDF_DOWNLOAD_ID = "wb-prophet-pdf-download"


def get_daily_sales(date_start: date, date_end: date) -> pd.DataFrame:
    """Дневная net-выручка: продажи минус возвраты."""
    if not date_start or not date_end:
        raise ValueError("Не задан период анализа.")
    if date_start > date_end:
        raise ValueError("Дата начала больше даты окончания.")

    with get_duckdb_conn_with_opt() as con:
        df = con.execute(
            """
            SELECT
                date_from::DATE AS ds,
                COALESCE(SUM(CASE WHEN oper = 'dt' THEN val ELSE 0 END), 0)
                    / 100.0 AS sales_amount,
                COALESCE(SUM(CASE WHEN oper = 'cr' THEN val ELSE 0 END), 0)
                    / 100.0 AS returns_amount
            FROM sales.sales_long
            WHERE date_from BETWEEN ? AND ?
              AND field = 'retail_price'
            GROUP BY date_from::DATE
            ORDER BY date_from::DATE
            """,
            [date_start, date_end],
        ).df()

    calendar_df = pd.DataFrame({
        "ds": pd.date_range(date_start, date_end, freq="D")
    })

    if df.empty:
        calendar_df["sales_amount"] = 0.0
        calendar_df["returns_amount"] = 0.0
    else:
        df["ds"] = pd.to_datetime(df["ds"])
        calendar_df = calendar_df.merge(df, on="ds", how="left")
        for col in ("sales_amount", "returns_amount"):
            calendar_df[col] = pd.to_numeric(
                calendar_df[col], errors="coerce"
            ).fillna(0.0)

    calendar_df["y"] = (
        calendar_df["sales_amount"] - calendar_df["returns_amount"]
    ).clip(lower=0.0)
    return calendar_df


def _clip_outliers(df: pd.DataFrame, enabled: bool) -> pd.DataFrame:
    work = df.copy()
    if not enabled or len(work) < 30:
        return work

    q1 = float(work["y"].quantile(0.25))
    q3 = float(work["y"].quantile(0.75))
    iqr = q3 - q1
    if iqr <= 0:
        return work

    work["y"] = work["y"].clip(
        lower=max(0.0, q1 - 1.5 * iqr),
        upper=q3 + 1.5 * iqr,
    )
    return work


def build_forecast(
    date_start: date,
    date_end: date,
    forecast_end: date,
    growth_pct: float = 0.0,
    changepoint_prior_scale: float = 0.05,
    seasonality_prior_scale: float = 10.0,
    interval_width: float = 0.80,
    seasonality_mode: str = "multiplicative",
    clip_outliers: bool = True,
) -> dict[str, Any]:
    """
    Строит дневной прогноз Prophet до forecast_end.

    Важно:
    - date_start/date_end задают только период обучения модели;
    - факт текущего года считается отдельно с 1 января по date_end;
    - growth_pct применяется только к будущей части прогноза;
    - базовый прогноз Prophet сохраняется отдельно.
    """
    try:
        from prophet import Prophet
    except ImportError as exc:
        raise RuntimeError(
            "Не установлен Prophet. Выполни: pip install prophet"
        ) from exc

    if forecast_end < date_end:
        raise ValueError("Дата окончания прогноза меньше даты окончания анализа.")

    history = get_daily_sales(date_start, date_end)

    if len(history) < 30:
        raise ValueError("Для прогноза нужно минимум 30 календарных дней.")

    if float(history["y"].sum()) <= 0:
        raise ValueError("За выбранный период нет положительной выручки.")

    training = _clip_outliers(
        history[["ds", "y"]],
        clip_outliers,
    )

    yearly_enabled = len(training) >= 365

    model = Prophet(
        growth="linear",
        changepoint_prior_scale=float(changepoint_prior_scale),
        seasonality_prior_scale=float(seasonality_prior_scale),
        seasonality_mode=seasonality_mode,
        interval_width=float(interval_width),
        weekly_seasonality=True,
        yearly_seasonality=yearly_enabled,
        daily_seasonality=False,
    )

    if len(training) >= 180:
        model.add_seasonality(
            name="monthly",
            period=30.5,
            fourier_order=5,
            prior_scale=float(seasonality_prior_scale),
        )

    model.fit(training)

    future_days = max(
        (forecast_end - date_end).days,
        0,
    )

    future = model.make_future_dataframe(
        periods=future_days,
        freq="D",
        include_history=True,
    )

    forecast = model.predict(future)

    cols = [
        "ds",
        "yhat",
        "yhat_lower",
        "yhat_upper",
        "trend",
        "weekly",
    ]

    for optional in ("yearly", "monthly"):
        if optional in forecast.columns:
            cols.append(optional)

    result = forecast[cols].merge(
        history[
            [
                "ds",
                "y",
                "sales_amount",
                "returns_amount",
            ]
        ],
        on="ds",
        how="left",
    )

    result["is_future"] = (
        result["ds"].dt.date > date_end
    )

    result["yhat_base"] = result["yhat"]

    scenario_factor = (
        1.0 + float(growth_pct) / 100.0
    )

    future_mask = result["is_future"]

    for column in (
        "yhat",
        "yhat_lower",
        "yhat_upper",
    ):
        result.loc[future_mask, column] = (
            result.loc[future_mask, column]
            * scenario_factor
        )

    for column in (
        "yhat",
        "yhat_lower",
        "yhat_upper",
        "yhat_base",
    ):
        result[column] = pd.to_numeric(
            result[column],
            errors="coerce",
        ).fillna(0.0).clip(lower=0.0)

    # ================================================================
    # План WB
    # ================================================================

    budget_version = get_budget_version()

    if budget_version:
        monthly_plan = get_monthly_plan_full_year(
            version_id=budget_version.id,
            year=date_end.year,
        )
    else:
        monthly_plan = {}

    annual_plan = sum(
        float(value or 0)
        for value in monthly_plan.values()
    )

    # ================================================================
    # Факт текущего года
    #
    # Период обучения может начинаться раньше 1 января текущего года,
    # поэтому годовой факт считаем отдельно.
    # ================================================================

    year_start_date = date(
        date_end.year,
        1,
        1,
    )

    year_fact_source = get_daily_sales(
        year_start_date,
        date_end,
    )

    year_fact_total = float(
        year_fact_source["y"].sum()
    )

    # Добавляем годовой факт в общий набор, если период обучения
    # начинается позже 1 января. Это нужно для корректной месячной
    # таблицы и сравнения с годовым планом.
    result_year_actual = year_fact_source[
        [
            "ds",
            "y",
            "sales_amount",
            "returns_amount",
        ]
    ].copy()

    # ================================================================
    # Прогноз до конца года
    # ================================================================

    future_df = result.loc[future_mask].copy()

    forecast_to_year_end = float(
        future_df["yhat"].sum()
    )

    forecast_base_to_year_end = float(
        future_df["yhat_base"].sum()
    )

    forecast_lower_to_year_end = float(
        future_df["yhat_lower"].sum()
    )

    forecast_upper_to_year_end = float(
        future_df["yhat_upper"].sum()
    )

    projected_year_total = (
        year_fact_total
        + forecast_to_year_end
    )

    projected_year_base_total = (
        year_fact_total
        + forecast_base_to_year_end
    )

    projected_year_lower_total = (
        year_fact_total
        + forecast_lower_to_year_end
    )

    projected_year_upper_total = (
        year_fact_total
        + forecast_upper_to_year_end
    )

    projected_plan_exec_pct = (
        projected_year_total
        / annual_plan
        * 100
        if annual_plan
        else 0.0
    )

    projected_plan_delta = (
        projected_year_total
        - annual_plan
    )

    remaining_to_plan = max(
        annual_plan
        - projected_year_total,
        0.0,
    )

    plan_overperformance = max(
        projected_year_total
        - annual_plan,
        0.0,
    )

    # ================================================================
    # Сравнение по месяцам:
    # план WB / факт / прогноз / ожидаемый итог
    # ================================================================

    actual_monthly = (
        result_year_actual
        .assign(
            month=(
                result_year_actual["ds"]
                .dt.to_period("M")
                .astype(str)
            )
        )
        .groupby(
            "month",
            as_index=False,
        )
        .agg(
            fact=("y", "sum"),
        )
    )

    future_monthly_source = (
        future_df.copy()
    )

    if future_monthly_source.empty:
        forecast_monthly = pd.DataFrame(
            columns=[
                "month",
                "forecast",
                "forecast_base",
                "lower_forecast",
                "upper_forecast",
            ]
        )
    else:
        future_monthly_source["month"] = (
            future_monthly_source["ds"]
            .dt.to_period("M")
            .astype(str)
        )

        forecast_monthly = (
            future_monthly_source
            .groupby(
                "month",
                as_index=False,
            )
            .agg(
                forecast=("yhat", "sum"),
                forecast_base=("yhat_base", "sum"),
                lower_forecast=("yhat_lower", "sum"),
                upper_forecast=("yhat_upper", "sum"),
            )
        )

    all_months = pd.DataFrame(
        {
            "month": [
                f"{date_end.year}-{month:02d}"
                for month in range(1, 13)
            ]
        }
    )

    monthly = (
        all_months
        .merge(
            actual_monthly,
            on="month",
            how="left",
        )
        .merge(
            forecast_monthly,
            on="month",
            how="left",
        )
    )

    numeric_columns = [
        "fact",
        "forecast",
        "forecast_base",
        "lower_forecast",
        "upper_forecast",
    ]

    for column in numeric_columns:
        monthly[column] = pd.to_numeric(
            monthly[column],
            errors="coerce",
        ).fillna(0.0)

    monthly["plan"] = monthly["month"].map(
        lambda month_key: float(
            monthly_plan.get(
                month_key,
                0,
            )
            or 0
        )
    )

    monthly["expected_total"] = (
        monthly["fact"]
        + monthly["forecast"]
    )

    monthly["expected_base_total"] = (
        monthly["fact"]
        + monthly["forecast_base"]
    )

    monthly["expected_lower"] = (
        monthly["fact"]
        + monthly["lower_forecast"]
    )

    monthly["expected_upper"] = (
        monthly["fact"]
        + monthly["upper_forecast"]
    )

    monthly["delta_to_plan"] = (
        monthly["expected_total"]
        - monthly["plan"]
    )

    monthly["plan_exec_pct"] = monthly.apply(
        lambda row: (
            row["expected_total"]
            / row["plan"]
            * 100
        )
        if row["plan"]
        else 0.0,
        axis=1,
    )

    # ================================================================
    # Дополнительная аналитика
    # ================================================================

    recent = history.loc[
        history["ds"]
        >= (
            pd.Timestamp(date_end)
            - pd.Timedelta(days=29)
        )
    ]

    recent_daily = (
        float(recent["y"].mean())
        if not recent.empty
        else 0.0
    )

    return {
        "params": {
            "date_start": date_start.isoformat(),
            "date_end": date_end.isoformat(),
            "forecast_end": forecast_end.isoformat(),
            "growth_pct": float(growth_pct),
            "changepoint_prior_scale": float(
                changepoint_prior_scale
            ),
            "seasonality_prior_scale": float(
                seasonality_prior_scale
            ),
            "interval_width": float(interval_width),
            "seasonality_mode": seasonality_mode,
            "clip_outliers": bool(clip_outliers),
            "yearly_seasonality": yearly_enabled,
        },
        "metrics": {
            "year_fact_total": year_fact_total,

            "forecast_to_year_end": (
                forecast_to_year_end
            ),
            "forecast_base_to_year_end": (
                forecast_base_to_year_end
            ),
            "forecast_lower_to_year_end": (
                forecast_lower_to_year_end
            ),
            "forecast_upper_to_year_end": (
                forecast_upper_to_year_end
            ),

            "projected_year_total": (
                projected_year_total
            ),
            "projected_year_base_total": (
                projected_year_base_total
            ),
            "projected_year_lower_total": (
                projected_year_lower_total
            ),
            "projected_year_upper_total": (
                projected_year_upper_total
            ),

            "annual_plan": annual_plan,
            "projected_plan_exec_pct": (
                projected_plan_exec_pct
            ),
            "projected_plan_delta": (
                projected_plan_delta
            ),
            "remaining_to_plan": (
                remaining_to_plan
            ),
            "plan_overperformance": (
                plan_overperformance
            ),

            "recent_daily": recent_daily,
            "simple_projection": (
                recent_daily
                * future_days
            ),
            "future_days": future_days,
        },
        "daily": _json_records(result),
        "monthly": _json_records(monthly),
    }


def _json_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    work = df.copy()
    for col in work.columns:
        if pd.api.types.is_datetime64_any_dtype(work[col]):
            work[col] = work[col].dt.strftime("%Y-%m-%d")
    work = work.where(pd.notna(work), None)
    return work.to_dict("records")


def build_chart(result: dict[str, Any] | None) -> go.Figure:
    if not result or not result.get("daily"):
        return _empty_chart("Настрой параметры и построй прогноз.")

    df = pd.DataFrame(result["daily"])
    df["ds"] = pd.to_datetime(df["ds"])
    for col in ("y", "yhat", "yhat_base", "yhat_lower", "yhat_upper"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["is_future"] = df["is_future"].astype(bool)

    history = df.loc[~df["is_future"]]
    future = df.loc[df["is_future"]]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=history["ds"],
        y=history["y"],
        name="Факт",
        mode="lines",
        line={"width": 2.2, "color": "#2563EB"},
        hovertemplate="<b>%{x|%d.%m.%Y}</b><br>Факт: %{y:,.0f} ₽<extra></extra>",
    ))

    if not future.empty:
        fig.add_trace(go.Scatter(
            x=future["ds"], y=future["yhat_upper"],
            mode="lines", line={"width": 0},
            hoverinfo="skip", showlegend=False,
        ))
        fig.add_trace(go.Scatter(
            x=future["ds"], y=future["yhat_lower"],
            name="Доверительный интервал",
            mode="lines", line={"width": 0},
            fill="tonexty",
            fillcolor="rgba(15,118,110,0.10)",
            hoverinfo="skip",
        ))
        fig.add_trace(go.Scatter(
            x=future["ds"], y=future["yhat_base"],
            name="Prophet без корректировки",
            mode="lines",
            line={"width": 2, "dash": "dot", "color": "#94A3B8"},
        ))
        fig.add_trace(go.Scatter(
            x=future["ds"], y=future["yhat"],
            name="Сценарный прогноз",
            mode="lines",
            line={"width": 3.2, "color": "#0F766E"},
        ))
        forecast_start = future["ds"].min()

        fig.add_shape(
            type="line",
            x0=forecast_start,
            x1=forecast_start,
            y0=0,
            y1=1,
            xref="x",
            yref="paper",
            line={
                "width": 1.2,
                "dash": "dash",
                "color": "#64748B",
            },
        )

        fig.add_annotation(
            x=forecast_start,
            y=1,
            xref="x",
            yref="paper",
            text="Начало прогноза",
            showarrow=False,
            xanchor="left",
            yanchor="bottom",
            xshift=6,
            font={
                "size": 11,
                "color": "#64748B",
            },
            bgcolor="rgba(255,255,255,0.90)",
        )

    fig.update_layout(
        height=520,
        margin={"l": 60, "r": 30, "t": 60, "b": 55},
        paper_bgcolor="white",
        plot_bgcolor="white",
        hovermode="x unified",
        font={"family": "Inter, Arial, sans-serif", "color": "#334155"},
        legend={"orientation": "h", "y": 1.04, "x": 0},
        xaxis={
            "showgrid": False,
            "linecolor": "#CBD5E1",
            "rangeslider": {"visible": True, "thickness": 0.08},
        },
        yaxis={
            "title": "Выручка net, ₽",
            "tickformat": "~s",
            "showgrid": True,
            "gridcolor": "rgba(148,163,184,0.20)",
            "zeroline": False,
        },
    )
    return fig


def build_plan_comparison_chart(
    result: dict[str, Any] | None,
) -> go.Figure:
    if not result or not result.get("monthly"):
        return _empty_chart(
            "Построй прогноз для сравнения с планом."
        )

    df = pd.DataFrame(
        result["monthly"]
    ).copy()

    if df.empty:
        return _empty_chart(
            "Нет данных для сравнения."
        )

    df["month_date"] = pd.to_datetime(
        df["month"] + "-01"
    )

    month_names = {
        1: "Янв",
        2: "Фев",
        3: "Мар",
        4: "Апр",
        5: "Май",
        6: "Июн",
        7: "Июл",
        8: "Авг",
        9: "Сен",
        10: "Окт",
        11: "Ноя",
        12: "Дек",
    }

    df["month_label"] = (
        df["month_date"]
        .dt.month
        .map(month_names)
    )

    numeric_columns = [
        "plan",
        "fact",
        "forecast",
        "expected_total",
        "delta_to_plan",
        "plan_exec_pct",
    ]

    for column in numeric_columns:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce",
        ).fillna(0.0)
        
    
    # Округляем показатели ещё до передачи в Plotly,
    # чтобы в customdata не попадал хвост float.
    df["plan"] = df["plan"].round(2)
    df["fact"] = df["fact"].round(2)
    df["forecast"] = df["forecast"].round(2)
    df["expected_total"] = df["expected_total"].round(2)
    df["delta_to_plan"] = df["delta_to_plan"].round(2)
    df["plan_exec_pct"] = df["plan_exec_pct"].round(2)

    # Готовим отображаемые строки в Python.
    # Так разделители тысяч не зависят от локали Plotly/browser.
    df["expected_total_display"] = df["expected_total"].map(
        lambda value: f"{value:,.0f}".replace(",", " ")
    )
    df["delta_to_plan_display"] = df["delta_to_plan"].map(
        lambda value: f"{value:+,.0f}".replace(",", " ")
    )
    df["plan_exec_pct_display"] = df["plan_exec_pct"].map(
        lambda value: f"{value:.2f}"
    )

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=df["month_label"],
            y=df["plan"],
            name="План WB",
            marker={
                "color": "rgba(249,115,22,0.30)",
                "line": {
                    "color": "rgba(249,115,22,0.75)",
                    "width": 1,
                },
            },
            hovertemplate=(
                "<b>%{x}</b><br>"
                "План WB: "
                "<b>%{y:,.0f} ₽</b>"
                "<extra></extra>"
            ),
        )
    )

    fig.add_trace(
        go.Bar(
            x=df["month_label"],
            y=df["fact"],
            name="Факт",
            marker={
                "color": "rgba(37,99,235,0.72)",
            },
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Факт: "
                "<b>%{y:,.0f} ₽</b>"
                "<extra></extra>"
            ),
        )
    )

    fig.add_trace(
        go.Bar(
            x=df["month_label"],
            y=df["forecast"],
            name="Прогноз Prophet",
            marker={
                "color": "rgba(15,118,110,0.62)",
            },
            customdata=df[
                [
                    "expected_total_display",
                    "delta_to_plan_display",
                    "plan_exec_pct_display",
                ]
            ],
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Прогнозная часть: "
                "<b>%{y:,.0f} ₽</b><br>"
                "Ожидаемый итог: "
                "<b>%{customdata[0]} ₽</b><br>"
                "Отклонение от плана: "
                "<b>%{customdata[1]} ₽</b><br>"
                "Выполнение: "
                "<b>%{customdata[2]}%</b>"
                "<extra></extra>"
            ),
        )
    )

    fig.add_trace(
        go.Scatter(
            x=df["month_label"],
            y=df["expected_total"],
            name="Ожидаемый итог",
            mode="lines+markers",
            line={
                "color": "#0F172A",
                "width": 3,
            },
            marker={
                "size": 8,
                "color": "#0F172A",
                "line": {
                    "color": "white",
                    "width": 1.5,
                },
            },
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Ожидаемый итог: "
                "<b>%{y:,.0f} ₽</b>"
                "<extra></extra>"
            ),
        )
    )

    fig.update_layout(
        height=500,
        barmode="group",
        bargap=0.22,
        margin={
            "l": 60,
            "r": 35,
            "t": 65,
            "b": 55,
        },
        paper_bgcolor="white",
        plot_bgcolor="white",
        hovermode="x unified",
        font={
            "family": "Inter, Arial, sans-serif",
            "color": "#334155",
        },
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.04,
            "xanchor": "left",
            "x": 0,
        },
        xaxis={
            "showgrid": False,
            "linecolor": "#CBD5E1",
        },
        yaxis={
            "title": "Сумма, ₽",
            "tickformat": "~s",
            "showgrid": True,
            "gridcolor": "rgba(148,163,184,0.20)",
            "zeroline": False,
        },
    )

    return fig


def _empty_chart(message: str) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(
        text=message, x=0.5, y=0.5,
        xref="paper", yref="paper",
        showarrow=False,
        font={"size": 15, "color": "#64748B"},
    )
    fig.update_layout(
        height=520,
        paper_bgcolor="white",
        plot_bgcolor="white",
        xaxis={"visible": False},
        yaxis={"visible": False},
    )
    return fig


def prophet_tab_header():
    return dmc.TabsTab(
        "Прогноз Prophet",
        value=TAB_VALUE,
        leftSection=DashIconify(
            icon="solar:graph-new-up-linear",
            width=16,
        ),
    )


def prophet_tab_panel(report_date: date):
    default_start = (
        report_date
        - timedelta(days=59)
    )

    return dmc.TabsPanel(
        value=TAB_VALUE,
        pt="sm",
        children=dmc.Stack(
            gap="sm",
            children=[
                # Служебные компоненты тоже должны находиться
                # внутри одного общего контейнера.
                dcc.Store(
                    id=STORE_ID,
                    storage_type="memory",
                ),

                dcc.Download(
                    id=DOWNLOAD_ID,
                ),
                
                 dcc.Download(
                        id=PDF_DOWNLOAD_ID,
                    ),

                # ====================================================
                # Параметры прогноза
                # ====================================================
                dmc.Paper(
                    withBorder=True,
                    radius=0,
                    p="sm",
                    children=[
                        dmc.Group(
                            justify="flex-start",
                            align="flex-end",
                            gap="sm",
                            wrap="wrap",
                            children=[
                                dmc.DatePickerInput(
                                    id=START_ID,
                                    label="Начало периода анализа",
                                    description="История для обучения модели",
                                    value=default_start,
                                    maxDate=report_date,
                                    valueFormat="DD.MM.YYYY",
                                    clearable=False,
                                    w=210,
                                ),

                                dmc.DatePickerInput(
                                    id=END_ID,
                                    label="Конец периода анализа",
                                    description="Последняя дата фактических продаж",
                                    value=report_date,
                                    maxDate=report_date,
                                    valueFormat="DD.MM.YYYY",
                                    clearable=False,
                                    w=210,
                                ),

                                dmc.NumberInput(
                                    id=GROWTH_ID,
                                    label="Корректировка прогноза",
                                    description="Рост или снижение, %",
                                    value=0,
                                    min=-80,
                                    max=300,
                                    step=1,
                                    decimalScale=1,
                                    suffix=" %",
                                    w=185,
                                ),

                                dmc.NumberInput(
                                    id=CHANGEPOINT_ID,
                                    label="Гибкость тренда",
                                    description="Обычно от 0,01 до 0,20",
                                    value=0.05,
                                    min=0.001,
                                    max=0.5,
                                    step=0.01,
                                    decimalScale=3,
                                    w=180,
                                ),

                                dmc.NumberInput(
                                    id=SEASONALITY_ID,
                                    label="Сила сезонности",
                                    description="Влияние сезонных колебаний",
                                    value=10,
                                    min=0.01,
                                    max=50,
                                    step=0.5,
                                    decimalScale=2,
                                    w=180,
                                ),

                                dmc.Select(
                                    id=MODE_ID,
                                    label="Тип сезонности",
                                    description="Способ расчёта сезонных эффектов",
                                    value="multiplicative",
                                    allowDeselect=False,
                                    data=[
                                        {
                                            "value": "multiplicative",
                                            "label": "Мультипликативная",
                                        },
                                        {
                                            "value": "additive",
                                            "label": "Аддитивная",
                                        },
                                    ],
                                    w=210,
                                ),

                                dmc.Select(
                                    id=INTERVAL_ID,
                                    label="Доверительный интервал",
                                    description="Ширина диапазона прогноза",
                                    value="0.80",
                                    allowDeselect=False,
                                    data=[
                                        {
                                            "value": "0.80",
                                            "label": "80%",
                                        },
                                        {
                                            "value": "0.90",
                                            "label": "90%",
                                        },
                                        {
                                            "value": "0.95",
                                            "label": "95%",
                                        },
                                    ],
                                    w=190,
                                ),
                            ],
                        ),

                        dmc.Group(
                            justify="space-between",
                            align="center",
                            mt="md",
                            wrap="wrap",
                            children=[
                                dmc.Group(
                                    gap="md",
                                    children=[
                                        dmc.Switch(
                                            id=OUTLIERS_ID,
                                            label="Сглаживать аномальные выбросы",
                                            checked=True,
                                            color="teal",
                                        ),
                                        dmc.Text(
                                            (
                                                "Прогноз строится по дневной net-выручке: "
                                                "продажи минус возвраты. Минимальный период "
                                                "обучения — 30 календарных дней."
                                            ),
                                            size="xs",
                                            c="dimmed",
                                        ),
                                    ],
                                ),

                                dmc.Group(
                                    gap="xs",
                                    children=[
                                        dmc.Button(
                                            "Построить прогноз",
                                            id=BUILD_ID,
                                            radius=0,
                                            leftSection=DashIconify(
                                                icon="solar:play-linear",
                                                width=18,
                                            ),
                                        ),

                                        dmc.Button(
                                            "Скачать Excel",
                                            id=DOWNLOAD_BTN_ID,
                                            radius=0,
                                            variant="outline",
                                            color="gray",
                                            disabled=True,
                                            leftSection=DashIconify(
                                                icon=(
                                                    "material-symbols:"
                                                    "download-rounded"
                                                ),
                                                width=18,
                                                color="#15803D",
                                            ),
                                            styles={
                                                "root": {
                                                    "backgroundColor": "#FFFFFF",
                                                    "border": (
                                                        "1px solid #D1D5DB"
                                                    ),
                                                    "color": "#374151",
                                                },
                                            },
                                        ),
                                        
                                        dmc.Button(
                                        "Скачать пояснительную записку",
                                        id=PDF_DOWNLOAD_BTN_ID,
                                        radius=0,
                                        variant="outline",
                                        color="gray",
                                        disabled=True,
                                        leftSection=DashIconify(
                                            icon="solar:file-text-linear",
                                            width=18,
                                            color="#B91C1C",
                                        ),
                                        styles={
                                            "root": {
                                                "backgroundColor": "#FFFFFF",
                                                "border": "1px solid #D1D5DB",
                                                "color": "#374151",
                                            },
                                        },
                                    ),
                                    ],
                                ),
                            ],
                        ),
                    ],
                ),
                
                
                 
                
                dmc.Alert(
                    children=dmc.Stack(
                        gap=4,
                        children=[
                            dmc.Text(
                                "Как работает прогноз Prophet",
                                fw=700,
                                size="sm",
                            ),

                            dmc.Text(
                                (
                                    "Prophet — модель прогнозирования временных рядов. "
                                    "Она анализирует историческую динамику продаж, "
                                    "общий тренд, недельную и годовую сезонность, "
                                    "а затем рассчитывает ожидаемые продажи "
                                    "до конца года."
                                ),
                                size="sm",
                            ),

                            dmc.Text(
                                (
                                    "Для построения прогноза необходимо минимум "
                                    "30 календарных дней истории. Чем длиннее "
                                    "и стабильнее период наблюдения, тем больше "
                                    "сезонных закономерностей может учесть модель."
                                ),
                                size="xs",
                                c="dimmed",
                            ),
                        ],
                    ),
                    color="blue",
                    variant="light",
                    radius=0,
                    icon=DashIconify(
                        icon="solar:info-circle-linear",
                        width=21,
                    ),
                ),

                # ====================================================
                # Статус расчёта
                # ====================================================
                html.Div(
                    id=STATUS_ID,
                ),

                # ====================================================
                # KPI
                # ====================================================
                dmc.SimpleGrid(
                    id=KPI_ID,
                    cols=5,
                    spacing="sm",
                    children=_empty_kpis(),
                ),

                # ====================================================
                # График
                # ====================================================
                dmc.Paper(
                    withBorder=True,
                    radius=0,
                    p="sm",
                    children=[
                        dmc.Group(
                            justify="space-between",
                            align="center",
                            mb="xs",
                            children=[
                                dmc.Text(
                                    "Факт и прогноз продаж до конца года",
                                    fw=800,
                                    size="sm",
                                ),

                                dmc.Badge(
                                    "PROPHET",
                                    variant="light",
                                    color="teal",
                                    radius=0,
                                ),
                            ],
                        ),

                        dcc.Loading(
                            type="cube",
                            children=dcc.Graph(
                                id=GRAPH_ID,
                                figure=_empty_chart(
                                    (
                                        "Настрой параметры и нажми "
                                        "«Построить прогноз»."
                                    )
                                ),
                                style={
                                    "height": "520px",
                                },
                                config={
                                    "displaylogo": False,
                                    "toImageButtonOptions": {
                                        "format": "png",
                                        "filename": (
                                            "wb_prophet_forecast"
                                        ),
                                        "scale": 3,
                                    },
                                },
                            ),
                        ),
                    ],
                ),

                dmc.Paper(
                    withBorder=True,
                    radius=0,
                    p="sm",
                    children=[
                        dmc.Group(
                            justify="space-between",
                            align="center",
                            mb="xs",
                            children=[
                                dmc.Text(
                                    (
                                        "План WB и ожидаемое "
                                        "выполнение по месяцам"
                                    ),
                                    fw=800,
                                    size="sm",
                                ),

                                dmc.Badge(
                                    "ПЛАН / PROPHET",
                                    variant="light",
                                    color="indigo",
                                    radius=0,
                                ),
                            ],
                        ),

                        dcc.Loading(
                            type="cube",
                            children=dcc.Graph(
                                id=PLAN_COMPARISON_GRAPH_ID,
                                figure=_empty_chart(
                                    (
                                        "Построй прогноз для "
                                        "сравнения с планом."
                                    )
                                ),
                                style={
                                    "height": "500px",
                                },
                                config={
                                    "displaylogo": False,
                                    "toImageButtonOptions": {
                                        "format": "png",
                                        "filename": (
                                            "wb_plan_vs_prophet"
                                        ),
                                        "scale": 3,
                                    },
                                },
                            ),
                        ),
                    ],
                ),
            ],
        ),
    )

def _money_short(value: float) -> str:
    value = float(value or 0)
    if abs(value) >= 1_000_000_000:
        return f"{value / 1_000_000_000:,.2f} млрд ₽".replace(",", " ")
    if abs(value) >= 1_000_000:
        return f"{value / 1_000_000:,.1f} млн ₽".replace(",", " ")
    if abs(value) >= 1_000:
        return f"{value / 1_000:,.1f} тыс. ₽".replace(",", " ")
    return f"{value:,.0f} ₽".replace(",", " ")


def _kpi(label: str, value: str, subtitle: str):
    return dmc.Paper(
        withBorder=True,
        radius=0,
        p="sm",
        children=[
            dmc.Text(label, size="xs", c="dimmed", fw=600),
            dmc.Text(value, size="xl", fw=800, mt=4),
            dmc.Text(subtitle, size="xs", c="dimmed", mt=2),
        ],
    )


def _empty_kpis():
    return [
        _kpi(
            "Факт текущего года",
            "—",
            "с 1 января по дату отчёта",
        ),
        _kpi(
            "Прогноз до конца года",
            "—",
            "будущий период",
        ),
        _kpi(
            "Ожидаемый итог года",
            "—",
            "факт + прогноз",
        ),
        _kpi(
            "Годовой план WB",
            "—",
            "план по соглашению",
        ),
        _kpi(
            "Ожидаемое выполнение",
            "—",
            "прогноз / план",
        ),
    ]


def build_kpis(
    result: dict[str, Any],
):
    params = result["params"]
    metrics = result["metrics"]

    projected_delta = float(
        metrics["projected_plan_delta"]
        or 0
    )

    delta_sign = (
        "+"
        if projected_delta >= 0
        else ""
    )

    report_year = params["date_end"][:4]

    return [
        _kpi(
            "Факт текущего года",
            _money_short(
                metrics["year_fact_total"]
            ),
            (
                f"01.01.{report_year} — "
                f"{params['date_end']}"
            ),
        ),

        _kpi(
            "Прогноз до конца года",
            _money_short(
                metrics["forecast_to_year_end"]
            ),
            (
                f"{metrics['future_days']} "
                "прогнозных дней"
            ),
        ),

        _kpi(
            "Ожидаемый итог года",
            _money_short(
                metrics["projected_year_total"]
            ),
            "факт текущего года + прогноз",
        ),

        _kpi(
            "Годовой план WB",
            _money_short(
                metrics["annual_plan"]
            ),
            "план по соглашению с WB",
        ),

        _kpi(
            "Ожидаемое выполнение",
            (
                f"{metrics['projected_plan_exec_pct']:.1f}%"
            ),
            (
                f"{delta_sign}"
                f"{_money_short(projected_delta)} "
                "к годовому плану"
            ),
        ),
    ]


def build_excel(result: dict[str, Any]) -> bytes:
    if not result:
        raise ValueError("Сначала построй прогноз.")

    output = BytesIO()
    workbook = xlsxwriter.Workbook(output, {"in_memory": True})
    formats = _formats(workbook)

    _summary_sheet(workbook, formats, result)
    _monthly_sheet(workbook, formats, result)
    _daily_sheet(workbook, formats, result)

    workbook.close()
    output.seek(0)
    return output.getvalue()


def _formats(workbook):
    base = {
        "font_name": "Arial",
        "font_size": 10,
        "border": 1,
        "border_color": "#E2E8F0",
    }
    return {
        "title": workbook.add_format({
            "font_name": "Arial", "font_size": 18,
            "bold": True, "font_color": "#0F172A",
        }),
        "subtitle": workbook.add_format({
            "font_name": "Arial", "font_size": 10,
            "font_color": "#64748B",
        }),
        "section": workbook.add_format({
            "font_name": "Arial", "font_size": 11,
            "bold": True, "font_color": "#FFFFFF",
            "bg_color": "#334155",
        }),
        "header": workbook.add_format({
            **base, "bold": True, "font_color": "#FFFFFF",
            "bg_color": "#0F766E", "align": "center",
            "valign": "vcenter", "text_wrap": True,
        }),
        "text": workbook.add_format(base),
        "label": workbook.add_format({
            **base, "font_color": "#475569", "bg_color": "#F8FAFC",
        }),
        "money": workbook.add_format({
            **base, "num_format": '#,##0.00" ₽"',
        }),
        "money_future": workbook.add_format({
            **base, "num_format": '#,##0.00" ₽"',
            "bg_color": "#ECFDF5",
        }),
        "date": workbook.add_format({
            **base, "num_format": "dd.mm.yyyy",
        }),
        "date_future": workbook.add_format({
            **base, "num_format": "dd.mm.yyyy",
            "bg_color": "#ECFDF5",
        }),
        
        "percent_2": workbook.add_format({
            **base,
            "num_format": "0.00%",
        }),
    }


def _summary_sheet(
    workbook,
    f,
    result,
):
    ws = workbook.add_worksheet(
        "Параметры и итоги"
    )

    ws.hide_gridlines(2)
    ws.set_column("A:A", 35)
    ws.set_column("B:B", 24)
    ws.set_column("D:K", 19)

    params = result["params"]
    metrics = result["metrics"]

    ws.merge_range(
        "A1:K1",
        "Прогноз продаж WB — Prophet",
        f["title"],
    )

    ws.merge_range(
        "A2:K2",
        (
            f"Обучение: "
            f"{params['date_start']} — "
            f"{params['date_end']} | "
            f"Прогноз до: "
            f"{params['forecast_end']}"
        ),
        f["subtitle"],
    )

    ws.merge_range(
        "A4:B4",
        "Параметры модели",
        f["section"],
    )

    parameter_rows = [
        (
            "Начало обучения",
            params["date_start"],
        ),
        (
            "Конец обучения",
            params["date_end"],
        ),
        (
            "Конец прогноза",
            params["forecast_end"],
        ),
        (
            "Корректировка",
            f"{params['growth_pct']:+.1f}%",
        ),
        (
            "Гибкость тренда",
            params["changepoint_prior_scale"],
        ),
        (
            "Сила сезонности",
            params["seasonality_prior_scale"],
        ),
        (
            "Тип сезонности",
            params["seasonality_mode"],
        ),
        (
            "Доверительный интервал",
            f"{params['interval_width']:.0%}",
        ),
        (
            "Сглаживание выбросов",
            (
                "Да"
                if params["clip_outliers"]
                else "Нет"
            ),
        ),
    ]

    for row_index, (
        label,
        value,
    ) in enumerate(
        parameter_rows,
        start=4,
    ):
        ws.write(
            row_index,
            0,
            label,
            f["label"],
        )

        ws.write(
            row_index,
            1,
            value,
            f["text"],
        )

    ws.merge_range(
        "A15:B15",
        "Итоги",
        f["section"],
    )

    metric_rows = [
        (
            "Факт текущего года",
            metrics["year_fact_total"],
        ),
        (
            "Прогноз до конца года",
            metrics["forecast_to_year_end"],
        ),
        (
            "Ожидаемый итог года",
            metrics["projected_year_total"],
        ),
        (
            "Годовой план WB",
            metrics["annual_plan"],
        ),
        (
            "Отклонение от плана",
            metrics["projected_plan_delta"],
        ),
        (
            "Ожидаемое выполнение, %",
            metrics["projected_plan_exec_pct"],
        ),
        (
            "Нижняя граница итога года",
            metrics["projected_year_lower_total"],
        ),
        (
            "Верхняя граница итога года",
            metrics["projected_year_upper_total"],
        ),
        (
            "Среднее последних 30 дней",
            metrics["recent_daily"],
        ),
        (
            "Простая проекция до конца года",
            metrics["simple_projection"],
        ),
    ]

    for row_index, (
        label,
        value,
    ) in enumerate(
        metric_rows,
        start=15,
    ):
        ws.write(
            row_index,
            0,
            label,
            f["label"],
        )

        if label.endswith("%"):
            ws.write_number(
                row_index,
                1,
                float(value or 0) / 100,
                f["percent_2"],
            )
        else:
            ws.write_number(
                row_index,
                1,
                round(float(value or 0), 2),
                f["money"],
            )

    monthly = result["monthly"]

    headers = [
        "Месяц",
        "План WB",
        "Факт",
        "Прогноз",
        "Ожидаемый итог",
        "Отклонение",
        "Выполнение, %",
    ]

    for column, header in enumerate(
        headers,
        start=3,
    ):
        ws.write(
            3,
            column,
            header,
            f["header"],
        )

    for row_index, row in enumerate(
        monthly,
        start=4,
    ):
        ws.write(
            row_index,
            3,
            row["month"],
            f["text"],
        )

        for column, key in enumerate(
            (
                "plan",
                "fact",
                "forecast",
                "expected_total",
                "delta_to_plan",
            ),
            start=4,
        ):
            ws.write_number(
                row_index,
                column,
                float(row.get(key) or 0),
                f["money"],
            )

        ws.write_number(
            row_index,
            9,
            float(
                row.get("plan_exec_pct")
                or 0
            ) / 100,
            f["percent_2"],
        )

    if monthly:
        chart = workbook.add_chart(
            {
                "type": "column",
            }
        )

        first_row = 4
        last_row = (
            3 + len(monthly)
        )

        chart.add_series(
            {
                "name": "План WB",
                "categories": [
                    "Параметры и итоги",
                    first_row,
                    3,
                    last_row,
                    3,
                ],
                "values": [
                    "Параметры и итоги",
                    first_row,
                    4,
                    last_row,
                    4,
                ],
                "fill": {
                    "color": "#F97316",
                    "transparency": 30,
                },
                "border": {
                    "none": True,
                },
            }
        )

        chart.add_series(
            {
                "name": "Ожидаемый итог",
                "categories": [
                    "Параметры и итоги",
                    first_row,
                    3,
                    last_row,
                    3,
                ],
                "values": [
                    "Параметры и итоги",
                    first_row,
                    7,
                    last_row,
                    7,
                ],
                "fill": {
                    "color": "#0F766E",
                    "transparency": 15,
                },
                "border": {
                    "none": True,
                },
            }
        )

        chart.set_title(
            {
                "name": (
                    "План WB и ожидаемый итог "
                    "по месяцам"
                ),
            }
        )

        chart.set_legend(
            {
                "position": "top",
            }
        )

        chart.set_y_axis(
            {
                "num_format": '#,##0,," млн"',
                "major_gridlines": {
                    "visible": True,
                    "line": {
                        "color": "#E2E8F0",
                    },
                },
            }
        )

        chart.set_chartarea(
            {
                "border": {
                    "none": True,
                },
            }
        )

        chart.set_plotarea(
            {
                "border": {
                    "none": True,
                },
            }
        )

        chart.set_size(
            {
                "width": 790,
                "height": 370,
            }
        )

        ws.insert_chart(
            "D18",
            chart,
        )


def _monthly_sheet(
    workbook,
    f,
    result,
):
    ws = workbook.add_worksheet(
        "Прогноз по месяцам"
    )

    ws.hide_gridlines(2)
    ws.freeze_panes(3, 1)

    ws.set_column("A:A", 14)
    ws.set_column("B:J", 21)

    ws.merge_range(
        "A1:J1",
        "План WB и прогноз Prophet по месяцам",
        f["title"],
    )

    ws.merge_range(
        "A2:J2",
        (
            "Факт текущего года, прогнозная часть, "
            "ожидаемый итог и сравнение с планом"
        ),
        f["subtitle"],
    )

    headers = [
        "Месяц",
        "План WB",
        "Факт",
        "Прогноз Prophet",
        "Ожидаемый итог",
        "Отклонение от плана",
        "Выполнение, %",
        "Базовый итог",
        "Нижняя граница",
        "Верхняя граница",
    ]

    for column, header in enumerate(
        headers
    ):
        ws.write(
            2,
            column,
            header,
            f["header"],
        )

    for row_index, row in enumerate(
        result["monthly"],
        start=3,
    ):
        ws.write(
            row_index,
            0,
            row["month"],
            f["text"],
        )

        money_fields = [
            "plan",
            "fact",
            "forecast",
            "expected_total",
            "delta_to_plan",
        ]

        for column, key in enumerate(
            money_fields,
            start=1,
        ):
            ws.write_number(
                row_index,
                column,
                float(row.get(key) or 0),
                f["money"],
            )

        ws.write_number(
            row_index,
            6,
            float(
                row.get("plan_exec_pct")
                or 0
            ) / 100,
            f["percent_2"],
        )

        for column, key in enumerate(
            (
                "expected_base_total",
                "expected_lower",
                "expected_upper",
            ),
            start=7,
        ):
            ws.write_number(
                row_index,
                column,
                float(row.get(key) or 0),
                f["money"],
            )

    if result["monthly"]:
        ws.autofilter(
            2,
            0,
            2 + len(result["monthly"]),
            9,
        )


def _daily_sheet(workbook, f, result):
    ws = workbook.add_worksheet("Прогноз по дням")
    ws.hide_gridlines(2)
    ws.freeze_panes(3, 2)
    ws.set_column("A:A", 13)
    ws.set_column("B:B", 12)
    ws.set_column("C:J", 20)

    ws.merge_range("A1:J1", "Дневной прогноз продаж WB", f["title"])
    ws.merge_range(
        "A2:J2",
        "Будущие даты выделены светло-зелёным",
        f["subtitle"],
    )

    headers = [
        "Дата", "Тип", "Факт net", "Продажи", "Возвраты",
        "Prophet без корректировки", "Сценарный прогноз",
        "Нижняя граница", "Верхняя граница", "Тренд",
    ]
    for c, header in enumerate(headers):
        ws.write(2, c, header, f["header"])

    for r, row in enumerate(result["daily"], start=3):
        is_future = bool(row.get("is_future"))
        date_fmt = f["date_future"] if is_future else f["date"]
        money_fmt = f["money_future"] if is_future else f["money"]

        ws.write_datetime(
            r, 0,
            datetime.strptime(row["ds"], "%Y-%m-%d"),
            date_fmt,
        )
        ws.write(r, 1, "Прогноз" if is_future else "Факт", f["text"])

        values = [
            row.get("y"), row.get("sales_amount"), row.get("returns_amount"),
            row.get("yhat_base"), row.get("yhat"), row.get("yhat_lower"),
            row.get("yhat_upper"), row.get("trend"),
        ]
        for c, value in enumerate(values, start=2):
            ws.write_number(r, c, float(value or 0), money_fmt)

    if result["daily"]:
        ws.autofilter(2, 0, 2 + len(result["daily"]), 9)


def get_excel_filename(result: dict[str, Any]) -> str:
    end_date = result.get("params", {}).get("date_end", date.today().isoformat())
    return f"wb_prophet_forecast_{end_date}.xlsx"


def register_prophet_callbacks(app):
    @app.callback(
        Output(GRAPH_ID, "figure"),
        Output(
            PLAN_COMPARISON_GRAPH_ID,
            "figure",
        ),
        Output(KPI_ID, "children"),
        Output(STORE_ID, "data"),
        Output(STATUS_ID, "children"),
        Output(
            DOWNLOAD_BTN_ID,
            "disabled",
        ),
        Output(PDF_DOWNLOAD_BTN_ID, "disabled"),
        
        Input(BUILD_ID, "n_clicks"),
        State(START_ID, "value"),
        State(END_ID, "value"),
        State(GROWTH_ID, "value"),
        State(CHANGEPOINT_ID, "value"),
        State(SEASONALITY_ID, "value"),
        State(INTERVAL_ID, "value"),
        State(MODE_ID, "value"),
        State(OUTLIERS_ID, "checked"),
        prevent_initial_call=True,
    )
    def _run(
        n_clicks,
        start_value,
        end_value,
        growth,
        changepoint,
        seasonality,
        interval,
        mode,
        outliers,
    ):
        if not n_clicks:
            return (
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                True,
                True,
            )

        try:
            date_start = _to_date(
                start_value
            )

            date_end = _to_date(
                end_value
            )

            result = build_forecast(
                date_start=date_start,
                date_end=date_end,
                forecast_end=date(
                    date_end.year,
                    12,
                    31,
                ),
                growth_pct=float(
                    growth or 0
                ),
                changepoint_prior_scale=float(
                    changepoint or 0.05
                ),
                seasonality_prior_scale=float(
                    seasonality or 10
                ),
                interval_width=float(
                    interval or 0.80
                ),
                seasonality_mode=(
                    mode
                    or "multiplicative"
                ),
                clip_outliers=bool(
                    outliers
                ),
            )

            status = dmc.Alert(
                (
                    "Прогноз построен. "
                    "Ожидаемый итог года рассчитан "
                    "как факт с 1 января плюс прогноз "
                    "до 31 декабря."
                ),
                title="Готово",
                color="green",
                radius=0,
                icon=DashIconify(
                    icon=(
                        "solar:"
                        "check-circle-linear"
                    ),
                    width=20,
                ),
            )

            return (
                build_chart(result),
                build_plan_comparison_chart(
                    result
                ),
                build_kpis(result),
                result,
                status,
                False,
                False,
            )

        except Exception as exc:
            status = dmc.Alert(
                str(exc),
                title=(
                    "Не удалось построить прогноз"
                ),
                color="red",
                radius=0,
                icon=DashIconify(
                    icon=(
                        "solar:"
                        "danger-circle-linear"
                    ),
                    width=20,
                ),
            )

            return (
                _empty_chart(
                    "Проверь параметры прогноза."
                ),
                _empty_chart(
                    (
                        "Не удалось выполнить "
                        "сравнение с планом."
                    )
                ),
                _empty_kpis(),
                None,
                status,
                True,
                True,
            )

    @app.callback(
        Output(DOWNLOAD_ID, "data"),
        Input(
            DOWNLOAD_BTN_ID,
            "n_clicks",
        ),
        State(STORE_ID, "data"),
        prevent_initial_call=True,
    )
    def _download(
        n_clicks,
        result,
    ):
        if not n_clicks or not result:
            return no_update

        return dcc.send_bytes(
            build_excel(result),
            get_excel_filename(result),
        )
        
    
    @app.callback(
        Output(PDF_DOWNLOAD_ID, "data"),
        Input(PDF_DOWNLOAD_BTN_ID, "n_clicks"),
        State(STORE_ID, "data"),
        prevent_initial_call=True,
    )
    def _download_prophet_note(
        n_clicks,
        result,
    ):
        if not n_clicks or not result:
            return no_update

        pdf_bytes = build_prophet_note_pdf(
            result=result,
        )

        return dcc.send_bytes(
            pdf_bytes,
            get_prophet_note_filename(result),
        )


def _to_date(value) -> date:
    if isinstance(value, date):
        return value
    if not value:
        raise ValueError("Не задана дата.")
    return pd.to_datetime(value).date()