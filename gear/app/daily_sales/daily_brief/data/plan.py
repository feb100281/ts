# gear/app/daily_sales/daily_brief/data/plan.py
from __future__ import annotations

from datetime import date
from typing import Any

from gear.app.daily_sales.wb_plan_monitor.data import (
    build_current_month_analysis,
    calculate_period_plan_to_date,
    get_budget_version,
    get_daily_fact,
    get_fact_for_period,
    get_monthly_plan_full_year,
    get_semi_periods,
)

from ..helpers import json_safe, number


def get_plan_source(report_date: date) -> dict[str, Any]:
    version = get_budget_version()
    if version is None:
        return {"available": False, "reason": "Не найдена бюджетная версия.", "daily_rows": []}

    monthly_plan = get_monthly_plan_full_year(version_id=version.id, year=report_date.year)
    daily_rows = get_daily_fact(
        year=report_date.year,
        month=report_date.month,
        up_to_day=report_date.day,
    )
    current_month = build_current_month_analysis(
        report_date=report_date,
        monthly_plan=monthly_plan,
        daily_raw=daily_rows,
    )
    return {
        "available": True,
        "version_id": version.id,
        "version_date": json_safe(version.date_from),
        "daily_rows": daily_rows,
        "current_month": current_month,
        "monthly_plan": monthly_plan,
    }


def get_month_plan(plan_source: dict[str, Any]) -> dict[str, Any]:
    if not plan_source.get("available"):
        return {"available": False, "reason": plan_source.get("reason")}

    analysis = plan_source.get("current_month", {})
    return {
        "available": True,
        "label": analysis.get("label"),
        "month_plan": number(analysis.get("month_plan")),
        "daily_plan": number(analysis.get("daily_plan")),
        "plan_to_date": number(analysis.get("plan_to_date")),
        "fact_to_date": number(analysis.get("fact_to_date")),
        "exec_to_date_pct": number(analysis.get("exec_to_date_pct")),
        "month_exec_pct": number(analysis.get("month_exec_pct")),
        "delta_to_date": number(analysis.get("delta_to_date")),
        "remaining_month": number(analysis.get("remaining_month")),
        "required_daily_rate": number(analysis.get("required_daily_rate")),
        "remaining_days": int(number(analysis.get("remaining_days"))),
        "rows": [
            {
                "date": json_safe(row.get("date")),
                "date_label": row.get("date_label"),
                "fact": number(row.get("fact")),
                "running_fact": number(row.get("running_fact")),
                "running_plan": number(row.get("running_plan")),
                "exec_to_date_pct": number(row.get("exec_to_date_pct")),
            }
            for row in analysis.get("rows", [])
        ],
    }


def get_half_year_plan(report_date: date, plan_source: dict[str, Any]) -> dict[str, Any]:
    if not plan_source.get("available"):
        return {"available": False, "reason": plan_source.get("reason")}

    monthly_plan = plan_source.get("monthly_plan", {})
    current_period = next(
        (p for p in get_semi_periods(report_date.year, monthly_plan) if p["start"] <= report_date <= p["end"]),
        None,
    )
    if current_period is None:
        return {"available": False, "reason": "Не найден план полугодия."}

    effective_date = min(report_date, current_period["end"])
    plan_amount = number(current_period.get("plan"))
    fact_amount = number(get_fact_for_period(current_period["start"], effective_date))
    plan_to_date = number(calculate_period_plan_to_date(
        period=current_period,
        monthly_plan=monthly_plan,
        report_date=effective_date,
    ))
    execution_pct = fact_amount / plan_amount * 100 if plan_amount else 0
    execution_to_date_pct = fact_amount / plan_to_date * 100 if plan_to_date else 0
    remaining_amount = max(plan_amount - fact_amount, 0)
    total_days = (current_period["end"] - current_period["start"]).days + 1
    elapsed_days = (effective_date - current_period["start"]).days + 1
    calendar_pct = elapsed_days / total_days * 100 if total_days else 0
    days_remaining = max((current_period["end"] - effective_date).days, 0)
    required_daily_rate = remaining_amount / days_remaining if days_remaining else 0

    return {
        "available": True,
        "label": current_period["label"],
        "date_start": json_safe(current_period["start"]),
        "date_finish": json_safe(current_period["end"]),
        "plan_amount": plan_amount,
        "fact_amount": fact_amount,
        "plan_to_date": plan_to_date,
        "execution_pct": execution_pct,
        "execution_to_date_pct": execution_to_date_pct,
        "remaining_amount": remaining_amount,
        "calendar_pct": calendar_pct,
        "pace_delta_pp": execution_pct - calendar_pct,
        "days_remaining": days_remaining,
        "required_daily_rate": required_daily_rate,
        "status": "ahead" if execution_to_date_pct >= 100 else "behind",
    }
