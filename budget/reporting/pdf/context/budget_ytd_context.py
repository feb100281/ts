# budget/reporting/pdf/context/budget_ytd_context.py
from budget.reporting.pdf.services.budget_ytd_service import (
    get_budget_ytd_analysis,
    format_money_compact,
    format_money_full
)
from budget.reporting.pdf.charts.ytd_charts import (
    build_ytd_plan_fact_chart_base64,
    build_ytd_daily_chart_base64,
    build_monthly_delta_waterfall_chart_base64,
)


def build_monthly_insight(monthly_data):
    if not monthly_data:
        return None

    # Все месяцы, включая текущий неполный
    all_months = monthly_data

    # Для худшего/лучшего месяца тоже лучше брать все месяцы,
    # потому что waterfall показывает текущий месяц
    worst = min(all_months, key=lambda x: x["delta"])
    best = max(all_months, key=lambda x: x["delta"])

    total_delta = sum(float(m["delta"]) for m in all_months)

    worst_sign = "-" if worst["delta"] < 0 else "+"
    best_sign = "+" if best["delta"] > 0 else ""

    current_month = next((m for m in all_months if m.get("is_current_month")), None)

    text = (
        f"Основное отклонение сформировано в месяце {worst['month_label']} "
        f"({worst_sign}{format_money_full(abs(worst['delta']))} ₽). "
        f"Наибольший положительный вклад — {best['month_label']} "
        f"({best_sign}{format_money_full(abs(best['delta']))} ₽). "
        f"Итоговое отклонение YTD: "
        f"{'+' if total_delta >= 0 else '-'}{format_money_full(abs(total_delta))} ₽."
    )

    if current_month and not current_month.get("is_completed"):
        text += (
            f" Текущий месяц ({current_month['month_label']}) включен в расчет "
            f"по данным на отчетную дату."
        )

    return {
        "text": text
    }


def build_budget_ytd_context(version):
    """Строит контекст для YTD анализа бюджета"""
    ytd_data = get_budget_ytd_analysis(version)
    
    if not ytd_data or not ytd_data.get("monthly_data"):
        return {"budget_ytd": None}
    
    # Форматируем помесячные данные
    monthly_data = []
    for m in ytd_data["monthly_data"]:
        monthly_data.append({
            **m,
            "plan_fmt": format_money_full(m["plan"]),
            "fact_fmt": format_money_full(m["fact"]),
            "delta_fmt": format_money_full(abs(m["delta"])),
            "running_plan_fmt": format_money_full(m["running_plan"]),
            "running_fact_fmt": format_money_full(m["running_fact"]),
            "running_delta_fmt": format_money_full(abs(m["running_delta"])),
        })
    
    # Форматируем полугодовые данные
    semi_analysis = []
    for s in ytd_data["semi_analysis"]:
        semi_analysis.append({
            **s,
            "plan_fmt": format_money_full(s["plan"]),
            "target_fmt": format_money_full(s["target"]),
            "fact_fmt": format_money_full(s["fact"]),
            "remaining_fmt": format_money_full(s["remaining"]),
            "overachievement_fmt": format_money_full(s["overachievement"]),
            "required_daily_rate_fmt": format_money_compact(s["required_daily_rate"]),
            "current_daily_rate_fmt": format_money_compact(s["current_daily_rate"]),
            "gap_daily_rate_fmt": format_money_compact(s["gap_daily_rate"]),
            "gap_total_fmt": format_money_full(s["gap_total"]),
            "projected_end_fmt": format_money_full(s["projected_end"]),
        })
    
    # Форматируем дневные данные
    daily = ytd_data.get("daily_analysis")
    if daily:
        for d in daily["days"]:
            d["plan_day_fmt"] = format_money_full(d["plan_day"])
            d["fact_day_fmt"] = format_money_full(d["fact_day"])
            d["delta_day_fmt"] = format_money_full(abs(d["delta_day"]))
            d["running_plan_fmt"] = format_money_full(d["running_plan"])
            d["running_fact_fmt"] = format_money_full(d["running_fact"])

        daily["avg_daily_plan_fmt"] = format_money_full(daily["avg_daily_plan"])
        daily["avg_daily_fact_fmt"] = format_money_full(daily["avg_daily_fact"])
        daily["best_day"]["fact_day_fmt"] = format_money_full(daily["best_day"]["fact_day"])
        daily["worst_day"]["fact_day_fmt"] = format_money_full(daily["worst_day"]["fact_day"])
    
    # Итоги
    totals = ytd_data["totals"]
    monthly_insight = build_monthly_insight(monthly_data)
    
    return {
        "budget_ytd": {
            "period_info": ytd_data["period_info"],
            "monthly_data": monthly_data,
            "semi_analysis": semi_analysis,
            "daily_analysis": daily,
            "totals": {
                "plan": totals["plan"],
                "plan_compact": format_money_compact(totals["plan"]),
                "plan_full": format_money_full(totals["plan"]),
                "plan_full_year": totals["plan_full_year"],
                "plan_full_year_compact": format_money_compact(totals["plan_full_year"]),
                "fact": totals["fact"],
                "fact_compact": format_money_compact(totals["fact"]),
                "fact_full": format_money_full(totals["fact"]),
                "delta": totals["delta"],
                "delta_compact": format_money_compact(abs(totals["delta"])),
                "delta_full": format_money_full(totals["delta"]),
                "exec_pct": totals["exec_pct"],
                "delta_pct": totals["delta_pct"]
            },
            "monthly_insight": monthly_insight,
            "charts": {
                "plan_fact": build_ytd_plan_fact_chart_base64(monthly_data),
                "monthly_waterfall": build_monthly_delta_waterfall_chart_base64(monthly_data),
                "daily": build_ytd_daily_chart_base64(daily) if daily else None,
                
            }
        }
    }
    
    


