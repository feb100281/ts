# budget/reporting/pdf/services/budget_ytd_service.py
from __future__ import annotations

from datetime import date
from typing import Optional
import calendar

from django.db import connection
from django.utils import timezone


REVENUE_CODE = "111000"

def _get_last_fact_date(date_from):
    """
    Последняя дата факта по выручке WB.
    Именно от нее считаем прогноз, а не от текущей календарной даты.
    """

    sql = """
        SELECT MAX(x.date_from)::date
        FROM public.cf_to_csv x
        JOIN corporate_cfitems i ON i.id = x.subconto_id
        JOIN corporate_cfitems lv3 ON lv3.id = i.parent_id
        WHERE lv3.code = %s
          AND x.date_from >= %s
    """

    with connection.cursor() as cursor:
        cursor.execute(sql, [REVENUE_CODE, date_from])
        row = cursor.fetchone()

    return row[0] if row and row[0] else None


def get_budget_ytd_analysis(version, report_date: Optional[date] = None):
    """
    Анализ выполнения плана выручки WB.

    report_date — дата последнего факта в базе, а не текущая дата.
    """

    if report_date is None:
        report_date = _get_last_fact_date(version.date_from) or timezone.now().date()

    # План до текущего месяца включительно — для YTD таблицы
    monthly_plan_ytd = _get_monthly_plan_ytd(version.id, report_date)

    # Полный помесячный план года — для полугодовых целей
    monthly_plan_full_year = _get_monthly_plan_full_year(version.id, report_date.year)

    # Факт до даты отчета
    monthly_fact = _get_monthly_fact(version.date_from, report_date)

    # Полугодовые цели считаем по полному годовому плану
    semi_targets = _get_semi_annual_targets(monthly_plan_full_year, report_date.year)

    ytd_analysis = _build_ytd_summary(
        monthly_plan=monthly_plan_ytd,
        monthly_fact=monthly_fact,
        version=version,
        report_date=report_date,
        semi_targets=semi_targets,
        monthly_plan_full_year=monthly_plan_full_year,
    )

    if ytd_analysis:
        ytd_analysis["daily_analysis"] = _build_daily_analysis(version, report_date)

    return ytd_analysis


def _get_monthly_plan_ytd(version_id, report_date):
    """
    План по месяцам до текущего месяца включительно.
    Возвращает dict: {"YYYY-MM": amount}
    """

    sql = """
        SELECT
            EXTRACT(YEAR FROM x.date_from) AS year,
            EXTRACT(MONTH FROM x.date_from) AS month,
            SUM(ROUND((x.dt - x.cr) / 100.0, 2)) AS amount
        FROM (
            SELECT "date" AS date_from, dt, cr, subconto_id
            FROM public.budget_gl
            WHERE version_id = %s
        ) x
        JOIN corporate_cfitems i ON i.id = x.subconto_id
        JOIN corporate_cfitems lv3 ON lv3.id = i.parent_id
        WHERE lv3.code = %s
          AND EXTRACT(YEAR FROM x.date_from) = %s
          AND EXTRACT(MONTH FROM x.date_from) <= %s
        GROUP BY year, month
        ORDER BY year, month
    """

    params = [
        int(version_id),
        REVENUE_CODE,
        int(report_date.year),
        int(report_date.month),
    ]

    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        rows = cursor.fetchall()

    return {
        f"{int(year)}-{int(month):02d}": float(amount or 0)
        for year, month, amount in rows
    }


def _get_monthly_plan_full_year(version_id, year):
    """
    Полный помесячный план года.
    Нужен для корректного расчета I и II полугодия.
    """

    sql = """
        SELECT
            EXTRACT(YEAR FROM x.date_from) AS year,
            EXTRACT(MONTH FROM x.date_from) AS month,
            SUM(ROUND((x.dt - x.cr) / 100.0, 2)) AS amount
        FROM (
            SELECT "date" AS date_from, dt, cr, subconto_id
            FROM public.budget_gl
            WHERE version_id = %s
        ) x
        JOIN corporate_cfitems i ON i.id = x.subconto_id
        JOIN corporate_cfitems lv3 ON lv3.id = i.parent_id
        WHERE lv3.code = %s
          AND EXTRACT(YEAR FROM x.date_from) = %s
        GROUP BY year, month
        ORDER BY year, month
    """

    with connection.cursor() as cursor:
        cursor.execute(sql, [int(version_id), REVENUE_CODE, int(year)])
        rows = cursor.fetchall()

    return {
        f"{int(year)}-{int(month):02d}": float(amount or 0)
        for year, month, amount in rows
    }


def _get_monthly_fact(date_from, report_date):
    """
    Факт по месяцам до report_date.
    Возвращает dict: {"YYYY-MM": amount}
    """

    sql = """
        SELECT
            EXTRACT(YEAR FROM x.date_from) AS year,
            EXTRACT(MONTH FROM x.date_from) AS month,
            SUM(ROUND(x.amount, 2)) AS amount
        FROM public.cf_to_csv x
        JOIN corporate_cfitems i ON i.id = x.subconto_id
        JOIN corporate_cfitems lv3 ON lv3.id = i.parent_id
        WHERE lv3.code = %s
          AND x.date_from BETWEEN %s AND %s
          AND EXTRACT(YEAR FROM x.date_from) = %s
          AND EXTRACT(MONTH FROM x.date_from) <= %s
        GROUP BY year, month
        ORDER BY year, month
    """

    params = [
        REVENUE_CODE,
        date_from,
        report_date,
        int(report_date.year),
        int(report_date.month),
    ]

    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        rows = cursor.fetchall()

    return {
        f"{int(year)}-{int(month):02d}": float(amount or 0)
        for year, month, amount in rows
    }


def _get_semi_annual_targets(monthly_plan_full_year, year):
    """
    Полугодовые цели из полного годового плана.
    """

    semi_targets = {}

    months_1 = [f"{year}-{m:02d}" for m in range(1, 7)]
    target_1 = sum(float(monthly_plan_full_year.get(m, 0)) for m in months_1)

    months_2 = [f"{year}-{m:02d}" for m in range(7, 13)]
    target_2 = sum(float(monthly_plan_full_year.get(m, 0)) for m in months_2)

    if target_1 > 0:
        semi_targets[f"{year}_1"] = {
            "period": f"I полугодие {year}",
            "start_month": f"{year}-01",
            "end_month": f"{year}-06",
            "target": target_1,
            "months": months_1,
        }

    if target_2 > 0:
        semi_targets[f"{year}_2"] = {
            "period": f"II полугодие {year}",
            "start_month": f"{year}-07",
            "end_month": f"{year}-12",
            "target": target_2,
            "months": months_2,
        }

    return semi_targets


def _build_ytd_summary(
    monthly_plan,
    monthly_fact,
    version,
    report_date,
    semi_targets,
    monthly_plan_full_year,
):
    """
    YTD-свод с помесячной детализацией.
    """

    all_months = sorted(set(monthly_plan.keys()) | set(monthly_fact.keys()))

    if not all_months:
        return None

    monthly_data = []
    running_plan = 0.0
    running_fact = 0.0
    completed_months_count = 0

    for month_key in all_months:
        year_str, month_str = month_key.split("-")
        year = int(year_str)
        month = int(month_str)

        last_day = calendar.monthrange(year, month)[1]
        month_end_date = date(year, month, last_day)

        plan_month = float(monthly_plan.get(month_key, 0))
        fact_month = float(monthly_fact.get(month_key, 0))

        running_plan += plan_month
        running_fact += fact_month

        delta_month = fact_month - plan_month
        running_delta = running_fact - running_plan

        exec_month_pct = fact_month / plan_month * 100 if plan_month > 0 else 0.0
        exec_running_pct = running_fact / running_plan * 100 if running_plan > 0 else 0.0

        is_completed_month = report_date >= month_end_date
        is_current_month = report_date.year == year and report_date.month == month

        if is_completed_month:
            completed_months_count += 1

        monthly_data.append({
            "month_key": month_key,
            "month_label": f"{_get_month_name_ru(month)} {year}",
            "month_num": month,
            "year": year,
            "plan": plan_month,
            "fact": fact_month,
            "delta": delta_month,
            "exec_pct": exec_month_pct,
            "running_plan": running_plan,
            "running_fact": running_fact,
            "running_delta": running_delta,
            "running_exec_pct": exec_running_pct,
            "is_current_month": is_current_month,
            "is_completed": is_completed_month,
        })

    has_partial_month = any(
        m["is_current_month"] and not m["is_completed"]
        for m in monthly_data
    )

    semi_analysis = []

    for sem_data in semi_targets.values():
        sem_plan_total = float(sem_data["target"])
        sem_fact = sum(float(monthly_fact.get(month_key, 0)) for month_key in sem_data["months"])

        exec_pct = sem_fact / sem_plan_total * 100 if sem_plan_total > 0 else 0.0

        remaining = max(sem_plan_total - sem_fact, 0)
        overachievement = max(sem_fact - sem_plan_total, 0)

        last_month = sem_data["months"][-1]
        last_year, last_month_num = map(int, last_month.split("-"))
        last_day = calendar.monthrange(last_year, last_month_num)[1]
        sem_end_date = date(last_year, last_month_num, last_day)

        start_year, start_month_num = map(int, sem_data["start_month"].split("-"))
        sem_start_date = date(start_year, start_month_num, 1)

        is_completed = report_date > sem_end_date
        is_current = sem_start_date <= report_date <= sem_end_date

        current_daily_rate = 0.0
        projected_end = sem_fact
        remaining_target = sem_plan_total - sem_fact
        days_remaining = 0
        required_daily_rate = 0.0
        gap_daily_rate = 0.0
        gap_total = 0.0
        gap_pct = 0.0

        if is_current and sem_fact > 0:
            days_passed = (report_date - sem_start_date).days + 1
            days_total = (sem_end_date - sem_start_date).days + 1
            days_remaining = max((sem_end_date - report_date).days, 0)

            current_daily_rate = sem_fact / days_passed if days_passed > 0 else 0.0
            projected_end = current_daily_rate * days_total

            if days_remaining > 0 and remaining_target > 0:
                required_daily_rate = remaining_target / days_remaining

            gap_daily_rate = max(required_daily_rate - current_daily_rate, 0)
            gap_total = gap_daily_rate * days_remaining

            if required_daily_rate > 0:
                gap_pct = gap_daily_rate / required_daily_rate * 100

        semi_analysis.append({
            "period": sem_data["period"],
            "plan": sem_plan_total,
            "target": sem_plan_total,
            "fact": sem_fact,
            "exec_pct": exec_pct,
            "remaining": remaining,
            "overachievement": overachievement,
            "is_completed": is_completed,
            "is_current": is_current,
            "current_daily_rate": current_daily_rate,
            "projected_end": projected_end,
            "required_daily_rate": required_daily_rate,
            "gap_daily_rate": gap_daily_rate,
            "gap_total": gap_total,
            "gap_pct": gap_pct,
            "days_remaining": days_remaining,
        })
    total_plan = sum(float(m["plan"]) for m in monthly_data)
    total_fact = sum(float(m["fact"]) for m in monthly_data)
    total_delta = total_fact - total_plan
    exec_pct = total_fact / total_plan * 100 if total_plan > 0 else 0.0
    delta_pct = exec_pct - 100

    full_year_plan = sum(float(v) for v in monthly_plan_full_year.values())

    return {
        "period_info": {
            "report_date": report_date,
            "report_date_str": report_date.strftime("%d.%m.%Y"),
            "months_passed": completed_months_count,
            "days_passed_current_month": report_date.day,
            "has_partial_month": has_partial_month,
        },
        "monthly_data": monthly_data,
        "semi_analysis": semi_analysis,
        "totals": {
            "plan": total_plan,
            "fact": total_fact,
            "delta": total_delta,
            "exec_pct": exec_pct,
            "delta_pct": delta_pct,
            "plan_full_year": full_year_plan,
        },
    }


def _get_daily_target(version_id, year, month):
    """
    Дневной план из GL.

    Если в GL есть полноценный дневной план — используем его.
    Если план лежит одной строкой на месяц — распределяем по рабочим дням.
    """

    sql = """
        SELECT
            EXTRACT(DAY FROM x.date_from) AS day,
            SUM(ROUND((x.dt - x.cr) / 100.0, 2)) AS amount
        FROM (
            SELECT "date" AS date_from, dt, cr, subconto_id
            FROM public.budget_gl
            WHERE version_id = %s
        ) x
        JOIN corporate_cfitems i ON i.id = x.subconto_id
        JOIN corporate_cfitems lv3 ON lv3.id = i.parent_id
        WHERE lv3.code = %s
          AND EXTRACT(YEAR FROM x.date_from) = %s
          AND EXTRACT(MONTH FROM x.date_from) = %s
        GROUP BY day
        ORDER BY day
    """

    with connection.cursor() as cursor:
        cursor.execute(sql, [int(version_id), REVENUE_CODE, int(year), int(month)])
        rows = cursor.fetchall()

    raw_daily_target = {
        int(day): float(amount or 0)
        for day, amount in rows
    }

    if not raw_daily_target:
        return {}

    # Если план только на 1 день — считаем, что это месячный план,
    # и распределяем по рабочим дням.
    if len(raw_daily_target) <= 1:
        monthly_plan = sum(raw_daily_target.values())
        return _distribute_monthly_plan_by_workdays(monthly_plan, year, month)

    return raw_daily_target


def _distribute_monthly_plan_by_workdays(monthly_plan, year, month):
    daily_target = {}

    days_in_month = calendar.monthrange(int(year), int(month))[1]

    working_days = [
        d for d in range(1, days_in_month + 1)
        if date(int(year), int(month), d).weekday() < 5
    ]

    if not working_days:
        return daily_target

    daily_amount = float(monthly_plan) / len(working_days)

    for d in working_days:
        daily_target[d] = daily_amount

    return daily_target


def _get_daily_fact(year, month, up_to_day=None):
    """
    Дневной факт по текущему месяцу.
    """

    sql = """
        SELECT
            EXTRACT(DAY FROM x.date_from) AS day,
            SUM(ROUND(x.amount, 2)) AS amount
        FROM public.cf_to_csv x
        JOIN corporate_cfitems i ON i.id = x.subconto_id
        JOIN corporate_cfitems lv3 ON lv3.id = i.parent_id
        WHERE lv3.code = %s
          AND EXTRACT(YEAR FROM x.date_from) = %s
          AND EXTRACT(MONTH FROM x.date_from) = %s
    """

    params = [REVENUE_CODE, int(year), int(month)]

    if up_to_day:
        sql += " AND EXTRACT(DAY FROM x.date_from) <= %s"
        params.append(int(up_to_day))

    sql += " GROUP BY day ORDER BY day"

    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        rows = cursor.fetchall()

    return {
        int(day): float(amount or 0)
        for day, amount in rows
    }
    
def _get_month_name_short_ru(month_num):
    months = [
        "янв", "фев", "мар", "апр", "май", "июн",
        "июл", "авг", "сен", "окт", "ноя", "дек"
    ]
    return months[month_num - 1]


def _build_daily_analysis(version, report_date):
    """
    Дневной анализ текущего месяца.
    Показываем только дни, по которым есть факт.
    """

    current_year = int(report_date.year)
    current_month = int(report_date.month)

    daily_target = _get_daily_target(version.id, current_year, current_month)
    daily_fact = _get_daily_fact(current_year, current_month, report_date.day)

    if not daily_fact:
        return None

    daily_data = []
    running_plan = 0.0
    running_fact = 0.0

    for day in sorted(daily_fact.keys()):
        current_date = date(current_year, current_month, int(day))

        plan_day = float(daily_target.get(int(day), 0))
        fact_day = float(daily_fact.get(int(day), 0))

        running_plan += plan_day
        running_fact += fact_day

        daily_data.append({
            "day": int(day),
            "date": current_date,
            "weekday": _get_weekday_ru(current_date.weekday()),
            "date_label": f"{int(day):02d} {_get_month_name_short_ru(current_month)}",
            "plan_day": plan_day,
            "fact_day": fact_day,
            "delta_day": fact_day - plan_day,
            "exec_day_pct": fact_day / plan_day * 100 if plan_day > 0 else 0.0,
            "running_plan": running_plan,
            "running_fact": running_fact,
            "running_delta": running_fact - running_plan,
            "running_exec_pct": running_fact / running_plan * 100 if running_plan > 0 else 0.0,
        })

    if not daily_data:
        return None

    best_day = max(daily_data, key=lambda x: float(x["fact_day"]))
    worst_day = min(daily_data, key=lambda x: float(x["fact_day"]))

    return {
        "year": current_year,
        "month": current_month,
        "month_name": f"{_get_month_name_ru(current_month)} {current_year}",
        "days": daily_data,
        "best_day": best_day,
        "worst_day": worst_day,
        "total_plan": running_plan,
        "total_fact": running_fact,
        "total_delta": running_fact - running_plan,
        "avg_daily_plan": running_plan / len(daily_data) if daily_data else 0.0,
        "avg_daily_fact": running_fact / len(daily_data) if daily_data else 0.0,
    }


def _get_month_name_ru(month_num):
    months = [
        "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
        "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь",
    ]
    return months[int(month_num) - 1]


def _get_weekday_ru(weekday):
    days = ["пн", "вт", "ср", "чт", "пт", "сб", "вс"]
    return days[int(weekday)]


def format_money_compact(value):
    if value is None:
        return "0"

    value = float(value)

    if abs(value) >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if abs(value) >= 1_000:
        return f"{value / 1_000:.0f}K"

    return f"{value:,.0f}".replace(",", " ")


def format_money_full(value):
    if value is None:
        return "0"

    return f"{float(value):,.0f}".replace(",", " ")