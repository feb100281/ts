# # gear/app/daily_sales/wb_plan_monitor/prophet_note/calculations.py
# from __future__ import annotations

# from dataclasses import dataclass
# from datetime import date
# from typing import Any

# from .formatting import (
#     half_year_label,
#     period_days,
#     to_date,
# )


# @dataclass(frozen=True)
# class PeriodResult:
#     label: str
#     date_start: date
#     date_end: date
#     plan: float
#     fact: float
#     forecast: float
#     expected: float
#     delta: float
#     execution_pct: float


# def build_note_context(result: dict[str, Any]) -> dict[str, Any]:
#     if not result:
#         raise ValueError("Нет данных прогноза для формирования записки.")

#     params = result.get("params") or {}
#     metrics = result.get("metrics") or {}
#     monthly = result.get("monthly") or []

#     date_start = to_date(params.get("date_start"))
#     date_end = to_date(params.get("date_end"))
#     forecast_end = to_date(params.get("forecast_end"))

#     year = date_end.year
#     current_half = 1 if date_end.month <= 6 else 2
#     half_months = (
#         range(1, 7)
#         if current_half == 1
#         else range(7, 13)
#     )
#     half_keys = {
#         f"{year}-{month:02d}"
#         for month in half_months
#     }

#     half_rows = [
#         row
#         for row in monthly
#         if str(row.get("month")) in half_keys
#     ]

#     half_start = date(
#         year,
#         1 if current_half == 1 else 7,
#         1,
#     )
#     half_end = date(
#         year,
#         6 if current_half == 1 else 12,
#         30 if current_half == 1 else 31,
#     )

#     half_plan = sum(float(row.get("plan") or 0) for row in half_rows)
#     half_fact = sum(float(row.get("fact") or 0) for row in half_rows)
#     half_forecast = sum(
#         float(row.get("forecast") or 0)
#         for row in half_rows
#     )
#     half_expected = half_fact + half_forecast
#     half_delta = half_expected - half_plan
#     half_execution = (
#         half_expected / half_plan * 100
#         if half_plan
#         else 0.0
#     )

#     annual_plan = float(metrics.get("annual_plan") or 0)
#     year_fact = float(metrics.get("year_fact_total") or 0)
#     forecast_to_year_end = float(
#         metrics.get("forecast_to_year_end") or 0
#     )
#     projected_year_total = float(
#         metrics.get("projected_year_total") or 0
#     )
#     projected_year_delta = float(
#         metrics.get("projected_plan_delta") or 0
#     )
#     projected_year_execution = float(
#         metrics.get("projected_plan_exec_pct") or 0
#     )

#     year_period = PeriodResult(
#         label=f"{year} год",
#         date_start=date(year, 1, 1),
#         date_end=date(year, 12, 31),
#         plan=annual_plan,
#         fact=year_fact,
#         forecast=forecast_to_year_end,
#         expected=projected_year_total,
#         delta=projected_year_delta,
#         execution_pct=projected_year_execution,
#     )

#     half_period = PeriodResult(
#         label=half_year_label(date_end.month, year),
#         date_start=half_start,
#         date_end=half_end,
#         plan=half_plan,
#         fact=half_fact,
#         forecast=half_forecast,
#         expected=half_expected,
#         delta=half_delta,
#         execution_pct=half_execution,
#     )

#     scenario_growth = float(params.get("growth_pct") or 0)
#     training_days = period_days(date_start, date_end)
#     forecast_days = max((forecast_end - date_end).days, 0)

#     return {
#         "params": params,
#         "metrics": metrics,
#         "monthly": monthly,
#         "date_start": date_start,
#         "date_end": date_end,
#         "forecast_end": forecast_end,
#         "training_days": training_days,
#         "forecast_days": forecast_days,
#         "scenario_growth": scenario_growth,
#         "year": year,
#         "year_period": year_period,
#         "half_period": half_period,
#         "current_half": current_half,
#     }


# def conclusion_status(execution_pct: float) -> str:
#     value = float(execution_pct or 0)

#     if 99.5 <= value <= 100.5:
#         return "соответствует плановому уровню"

#     if value > 100.5:
#         return "превышает плановый уровень"

#     return "ниже планового уровня"


# def conclusion_direction(delta: float) -> str:
#     value = float(delta or 0)

#     if abs(value) < 0.5:
#         return "без существенного отклонения"

#     if value > 0:
#         return "выше плана"

#     return "ниже плана"




from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from .formatting import half_year_label, period_days, to_date


@dataclass(frozen=True)
class PeriodResult:
    label: str
    date_start: date
    date_end: date
    plan: float
    fact: float
    forecast: float
    expected: float
    delta: float
    execution_pct: float

    @property
    def is_on_plan(self) -> bool:
        return self.execution_pct >= 100.0

    @property
    def severity(self) -> str:
        if self.execution_pct >= 100:
            return "success"
        if self.execution_pct >= 95:
            return "warning"
        return "danger"


def build_note_context(result: dict[str, Any]) -> dict[str, Any]:
    if not result:
        raise ValueError("Нет данных прогноза для формирования записки.")

    params = result.get("params") or {}
    metrics = result.get("metrics") or {}
    monthly = result.get("monthly") or []

    date_start = to_date(params.get("date_start"))
    date_end = to_date(params.get("date_end"))
    forecast_end = to_date(params.get("forecast_end"))

    year = date_end.year
    current_half = 1 if date_end.month <= 6 else 2
    half_months = range(1, 7) if current_half == 1 else range(7, 13)
    half_keys = {f"{year}-{month:02d}" for month in half_months}

    half_rows = [
        row for row in monthly
        if str(row.get("month")) in half_keys
    ]

    half_start = date(year, 1 if current_half == 1 else 7, 1)
    half_end = date(year, 6 if current_half == 1 else 12, 30 if current_half == 1 else 31)

    half_plan = sum(float(row.get("plan") or 0) for row in half_rows)
    half_fact = sum(float(row.get("fact") or 0) for row in half_rows)
    half_forecast = sum(float(row.get("forecast") or 0) for row in half_rows)
    half_expected = half_fact + half_forecast
    half_delta = half_expected - half_plan
    half_execution = half_expected / half_plan * 100 if half_plan else 0.0

    annual_plan = float(metrics.get("annual_plan") or 0)
    year_fact = float(metrics.get("year_fact_total") or 0)
    forecast_to_year_end = float(metrics.get("forecast_to_year_end") or 0)
    projected_year_total = float(metrics.get("projected_year_total") or 0)
    projected_year_delta = float(metrics.get("projected_plan_delta") or 0)
    projected_year_execution = float(metrics.get("projected_plan_exec_pct") or 0)

    year_period = PeriodResult(
        label=f"{year} год",
        date_start=date(year, 1, 1),
        date_end=date(year, 12, 31),
        plan=annual_plan,
        fact=year_fact,
        forecast=forecast_to_year_end,
        expected=projected_year_total,
        delta=projected_year_delta,
        execution_pct=projected_year_execution,
    )

    half_period = PeriodResult(
        label=half_year_label(date_end.month, year),
        date_start=half_start,
        date_end=half_end,
        plan=half_plan,
        fact=half_fact,
        forecast=half_forecast,
        expected=half_expected,
        delta=half_delta,
        execution_pct=half_execution,
    )

    return {
        "params": params,
        "metrics": metrics,
        "monthly": monthly,
        "date_start": date_start,
        "date_end": date_end,
        "forecast_end": forecast_end,
        "training_days": period_days(date_start, date_end),
        "forecast_days": max((forecast_end - date_end).days, 0),
        "scenario_growth": float(params.get("growth_pct") or 0),
        "year": year,
        "year_period": year_period,
        "half_period": half_period,
        "current_half": current_half,
    }


def conclusion_status(execution_pct: float) -> str:
    value = float(execution_pct or 0)
    if value >= 100.5:
        return "превышает плановый уровень"
    if value >= 99.5:
        return "соответствует плановому уровню"
    if value >= 95:
        return "незначительно ниже планового уровня"
    return "ниже планового уровня"


def conclusion_direction(delta: float) -> str:
    value = float(delta or 0)
    if abs(value) < 0.5:
        return "без существенного отклонения"
    return "выше плана" if value > 0 else "ниже плана"
