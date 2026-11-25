# from __future__ import annotations

# from datetime import date, timedelta
# from typing import Optional
# import calendar

# from django.db import connection

# REVENUE_CODE = "111000"


# def _get_last_fact_date(date_from: date) -> Optional[date]:
#     """Последняя дата факта по выручке WB"""
#     sql = """
#         SELECT MAX(x.date_from)::date
#         FROM public.cf_to_csv x
#         JOIN corporate_cfitems i ON i.id = x.subconto_id
#         JOIN corporate_cfitems lv3 ON lv3.id = i.parent_id
#         WHERE lv3.code = %s
#           AND x.date_from >= %s
#     """
#     with connection.cursor() as cursor:
#         cursor.execute(sql, [REVENUE_CODE, date_from])
#         row = cursor.fetchone()
#     return row[0] if row and row[0] else None


# def get_revenue_analysis(version, report_date: Optional[date] = None):
#     """Анализ выполнения плана выручки WB по полугодиям"""
    
#     if report_date is None:
#         report_date = _get_last_fact_date(version.date_from) or date.today()
    
#     # Полный помесячный план года
#     monthly_plan_full_year = _get_monthly_plan_full_year(version.id, report_date.year)
    
#     # Факт до даты отчета
#     monthly_fact = _get_monthly_fact(version.date_from, report_date)
    
#     # Полугодовые цели
#     semi_targets = _get_semi_annual_targets(monthly_plan_full_year, report_date.year)
    
#     # Полугодовой анализ
#     semi_analysis = _build_semi_analysis(
#         semi_targets=semi_targets,
#         monthly_fact=monthly_fact,
#         version=version,
#         report_date=report_date,
#     )
    
#     # Итоги по году
#     total_plan = sum(monthly_plan_full_year.values())
#     total_fact = sum(monthly_fact.values())
#     total_delta = total_fact - total_plan
#     exec_pct = total_fact / total_plan * 100 if total_plan > 0 else 0
    
#     # Анализ последних 10 дней
#     daily_analysis = get_avg_daily_rate_last_10_days(report_date)
    
#     return {
#         "report_date": report_date,
#         "report_date_str": report_date.strftime("%d.%m.%Y"),
#         "semi_analysis": semi_analysis,
#         "totals": {
#             "plan": total_plan,
#             "fact": total_fact,
#             "delta": total_delta,
#             "exec_pct": exec_pct,
#         },
#         "daily_analysis": daily_analysis,
#     }


# def _get_monthly_plan_full_year(version_id: int, year: int) -> dict:
#     """Полный помесячный план года"""
#     sql = """
#         SELECT
#             EXTRACT(YEAR FROM x.date_from) AS year,
#             EXTRACT(MONTH FROM x.date_from) AS month,
#             SUM(ROUND((x.dt - x.cr) / 100.0, 2)) AS amount
#         FROM (
#             SELECT "date" AS date_from, dt, cr, subconto_id
#             FROM public.budget_gl
#             WHERE version_id = %s
#         ) x
#         JOIN corporate_cfitems i ON i.id = x.subconto_id
#         JOIN corporate_cfitems lv3 ON lv3.id = i.parent_id
#         WHERE lv3.code = %s
#           AND EXTRACT(YEAR FROM x.date_from) = %s
#         GROUP BY year, month
#         ORDER BY year, month
#     """
#     with connection.cursor() as cursor:
#         cursor.execute(sql, [int(version_id), REVENUE_CODE, int(year)])
#         rows = cursor.fetchall()
    
#     return {f"{int(year)}-{int(month):02d}": float(amount or 0) for year, month, amount in rows}


# def _get_monthly_fact(date_from: date, report_date: date) -> dict:
#     """Факт по месяцам до report_date"""
#     sql = """
#         SELECT
#             EXTRACT(YEAR FROM x.date_from) AS year,
#             EXTRACT(MONTH FROM x.date_from) AS month,
#             SUM(ROUND(x.amount, 2)) AS amount
#         FROM public.cf_to_csv x
#         JOIN corporate_cfitems i ON i.id = x.subconto_id
#         JOIN corporate_cfitems lv3 ON lv3.id = i.parent_id
#         WHERE lv3.code = %s
#           AND x.date_from BETWEEN %s AND %s
#           AND EXTRACT(YEAR FROM x.date_from) = %s
#         GROUP BY year, month
#         ORDER BY year, month
#     """
#     with connection.cursor() as cursor:
#         cursor.execute(sql, [REVENUE_CODE, date_from, report_date, int(report_date.year)])
#         rows = cursor.fetchall()
    
#     return {f"{int(year)}-{int(month):02d}": float(amount or 0) for year, month, amount in rows}


# def _get_fact_for_period(date_start: date, date_end: date) -> float:
#     """Факт выручки за произвольный период"""
#     sql = """
#         SELECT SUM(ROUND(x.amount, 2)) AS amount
#         FROM public.cf_to_csv x
#         JOIN corporate_cfitems i ON i.id = x.subconto_id
#         JOIN corporate_cfitems lv3 ON lv3.id = i.parent_id
#         WHERE lv3.code = %s
#           AND x.date_from BETWEEN %s AND %s
#     """
#     with connection.cursor() as cursor:
#         cursor.execute(sql, [REVENUE_CODE, date_start, date_end])
#         row = cursor.fetchone()
#     return float(row[0] or 0) if row else 0.0


# def _get_semi_annual_targets(monthly_plan_full_year: dict, year: int) -> dict:
#     """Полугодовые цели из полного годового плана"""
#     semi_targets = {}
    
#     months_1 = [f"{year}-{m:02d}" for m in range(1, 7)]
#     target_1 = sum(float(monthly_plan_full_year.get(m, 0)) for m in months_1)
    
#     months_2 = [f"{year}-{m:02d}" for m in range(7, 13)]
#     target_2 = sum(float(monthly_plan_full_year.get(m, 0)) for m in months_2)
    
#     if target_1 > 0:
#         semi_targets[f"{year}_1"] = {
#             "period": f"I полугодие {year}",
#             "start_date": date(year, 1, 1),
#             "end_date": date(year, 6, 30),
#             "target": target_1,
#             "months": months_1,
#         }
    
#     if target_2 > 0:
#         semi_targets[f"{year}_2"] = {
#             "period": f"II полугодие {year}",
#             "start_date": date(year, 7, 1),
#             "end_date": date(year, 12, 31),
#             "target": target_2,
#             "months": months_2,
#         }
    
#     return semi_targets


# def _build_semi_analysis(semi_targets: dict, monthly_fact: dict, version, report_date: date) -> list:
#     """Построение анализа по полугодиям"""
#     result = []
    
#     for sem_key, sem_data in semi_targets.items():
#         sem_fact = sum(float(monthly_fact.get(month_key, 0)) for month_key in sem_data["months"])
#         sem_plan = float(sem_data["target"])
        
#         exec_pct = sem_fact / sem_plan * 100 if sem_plan > 0 else 0
#         remaining = max(sem_plan - sem_fact, 0)
#         overachievement = max(sem_fact - sem_plan, 0)
        
#         is_completed = report_date > sem_data["end_date"]
#         is_current = sem_data["start_date"] <= report_date <= sem_data["end_date"]
        
#         # Расчеты для текущего полугодия
#         current_daily_rate = 0.0
#         required_daily_rate = 0.0
#         gap_daily_rate = 0.0
#         gap_total = 0.0
#         projected_end = sem_fact
#         days_remaining = 0
#         rate_window_days = 0
#         rate_start_date = None
        
#         if is_current and sem_fact > 0:
#             rate_window_days = 10
#             days_remaining = max((sem_data["end_date"] - report_date).days, 0)
#             rate_start_date = max(sem_data["start_date"], report_date - timedelta(days=rate_window_days - 1))
#             actual_rate_days = (report_date - rate_start_date).days + 1
            
#             fact_last_period = _get_fact_for_period(rate_start_date, report_date)
#             current_daily_rate = fact_last_period / actual_rate_days if actual_rate_days > 0 else 0.0
#             projected_end = sem_fact + current_daily_rate * days_remaining
            
#             if days_remaining > 0 and remaining > 0:
#                 required_daily_rate = remaining / days_remaining
            
#             gap_daily_rate = max(required_daily_rate - current_daily_rate, 0)
#             gap_total = gap_daily_rate * days_remaining
        
#         result.append({
#             "period": sem_data["period"],
#             "plan": sem_plan,
#             "fact": sem_fact,
#             "exec_pct": exec_pct,
#             "remaining": remaining,
#             "overachievement": overachievement,
#             "is_completed": is_completed,
#             "is_current": is_current,
#             "current_daily_rate": current_daily_rate,
#             "required_daily_rate": required_daily_rate,
#             "gap_daily_rate": gap_daily_rate,
#             "gap_total": gap_total,
#             "projected_end": projected_end,
#             "days_remaining": days_remaining,
#             "rate_window_days": rate_window_days,
#             "rate_start_date": rate_start_date,
#         })
    
#     return result


# def format_money_compact(value: float) -> str:
#     """Компактный формат денег (1.5M, 120K)"""
#     if value is None:
#         return "0"
#     value = float(value)
#     if abs(value) >= 1_000_000:
#         return f"{value / 1_000_000:.1f}M"
#     if abs(value) >= 1_000:
#         return f"{value / 1_000:.0f}K"
#     return f"{value:,.0f}".replace(",", " ")


# def format_money_full(value: float) -> str:
#     """Полный формат денег с пробелами"""
#     if value is None:
#         return "0"
#     return f"{float(value):,.0f}".replace(",", " ")


# def get_last_10_days_fact(report_date: date) -> list:
#     """
#     Получает факт выручки за последние 10 дней (включительно до report_date)
#     """
#     start_date = report_date - timedelta(days=9)
    
#     sql = """
#         SELECT
#             x.date_from,
#             SUM(ROUND(x.amount, 2)) AS amount,
#             COUNT(*) AS transactions_count
#         FROM public.cf_to_csv x
#         JOIN corporate_cfitems i ON i.id = x.subconto_id
#         JOIN corporate_cfitems lv3 ON lv3.id = i.parent_id
#         WHERE lv3.code = %s
#           AND x.date_from BETWEEN %s AND %s
#         GROUP BY x.date_from
#         ORDER BY x.date_from DESC
#     """
    
#     with connection.cursor() as cursor:
#         cursor.execute(sql, [REVENUE_CODE, start_date, report_date])
#         rows = cursor.fetchall()
    
#     result = []
#     for row in rows:
#         result.append({
#             "date": row[0],
#             "amount": float(row[1] or 0),
#             "transactions_count": int(row[2] or 0),
#         })
    
#     # Заполняем пропущенные дни (где не было продаж)
#     current = start_date
#     existing_dates = {d["date"] for d in result}
    
#     full_result = []
#     while current <= report_date:
#         if current in existing_dates:
#             day_data = next(d for d in result if d["date"] == current)
#             full_result.append(day_data)
#         else:
#             full_result.append({
#                 "date": current,
#                 "amount": 0.0,
#                 "transactions_count": 0,
#             })
#         current += timedelta(days=1)
    
#     # Возвращаем в порядке от новых к старым (последние дни сверху)
#     return list(reversed(full_result))


# def get_avg_daily_rate_last_10_days(report_date: date) -> dict:
#     """
#     Рассчитывает среднюю дневную выручку за последние 10 дней
#     """
#     last_10_days = get_last_10_days_fact(report_date)
    
#     if not last_10_days:
#         return {
#             "avg_daily_rate": 0,
#             "total_amount": 0,
#             "days_with_sales": 0,
#             "days_count": 0,
#         }
    
#     total_amount = sum(d["amount"] for d in last_10_days)
#     days_count = len(last_10_days)
#     days_with_sales = sum(1 for d in last_10_days if d["amount"] > 0)
#     avg_daily_rate = total_amount / days_count if days_count > 0 else 0
    
#     return {
#         "avg_daily_rate": avg_daily_rate,
#         "total_amount": total_amount,
#         "days_with_sales": days_with_sales,
#         "days_count": days_count,
#         "last_10_days": last_10_days,
#     }



# budget/reporting/pdf/revenue_analysis/service.py
from __future__ import annotations

from datetime import date, timedelta
from typing import Optional
import calendar

from django.db import connection

from budget.reporting.pdf.revenue_analysis.duck_connector import get_revenue_connector

REVENUE_CODE = "111000"
connector = get_revenue_connector()


def _get_last_fact_date(date_from: date) -> Optional[date]:
    """Последняя дата факта выручки из DuckDB"""
    return connector.get_last_fact_date(date_from)


def get_revenue_analysis(version, report_date: Optional[date] = None):
    """Анализ выполнения плана выручки WB по полугодиям"""
    
    if report_date is None:
        report_date = _get_last_fact_date(version.date_from) or date.today()
    
    # Полный помесячный план года (из PostgreSQL)
    monthly_plan_full_year = _get_monthly_plan_full_year(version.id, report_date.year)
    
    # Факт до даты отчета (из DuckDB)
    monthly_fact_data = connector.get_monthly_fact(version.date_from, report_date)
    
    # Извлекаем net_amount для totals
    monthly_fact = {k: v["net_amount"] for k, v in monthly_fact_data.items()}
    
    # Полугодовые цели
    semi_targets = _get_semi_annual_targets(monthly_plan_full_year, report_date.year)
    
    # Полугодовой анализ
    semi_analysis = _build_semi_analysis(
        semi_targets=semi_targets,
        monthly_fact=monthly_fact,
        version=version,
        report_date=report_date,
    )
    
    # Итоги по году
    total_plan = sum(monthly_plan_full_year.values())
    total_fact = sum(monthly_fact.values())
    total_delta = total_fact - total_plan
    exec_pct = total_fact / total_plan * 100 if total_plan > 0 else 0
    
    # Анализ последних 10 дней (из DuckDB)
    daily_analysis = get_avg_daily_rate_last_10_days(report_date)
    
    return {
        "report_date": report_date,
        "report_date_str": report_date.strftime("%d.%m.%Y"),
        "semi_analysis": semi_analysis,
        "totals": {
            "plan": total_plan,
            "fact": total_fact,
            "delta": total_delta,
            "exec_pct": exec_pct,
        },
        "daily_analysis": daily_analysis,
        "monthly_fact_details": monthly_fact_data,  # добавляем детали по месяцам
    }


def _get_monthly_plan_full_year(version_id: int, year: int) -> dict:
    """Полный помесячный план года из PostgreSQL"""
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
    
    return {f"{int(year)}-{int(month):02d}": float(amount or 0) for year, month, amount in rows}


def _get_semi_annual_targets(monthly_plan_full_year: dict, year: int) -> dict:
    """Полугодовые цели из полного годового плана"""
    semi_targets = {}
    
    months_1 = [f"{year}-{m:02d}" for m in range(1, 7)]
    target_1 = sum(float(monthly_plan_full_year.get(m, 0)) for m in months_1)
    
    months_2 = [f"{year}-{m:02d}" for m in range(7, 13)]
    target_2 = sum(float(monthly_plan_full_year.get(m, 0)) for m in months_2)
    
    if target_1 > 0:
        semi_targets[f"{year}_1"] = {
            "period": f"I полугодие {year}",
            "start_date": date(year, 1, 1),
            "end_date": date(year, 6, 30),
            "target": target_1,
            "months": months_1,
        }
    
    if target_2 > 0:
        semi_targets[f"{year}_2"] = {
            "period": f"II полугодие {year}",
            "start_date": date(year, 7, 1),
            "end_date": date(year, 12, 31),
            "target": target_2,
            "months": months_2,
        }
    
    return semi_targets


def _get_fact_for_period(date_start: date, date_end: date) -> dict:
    """Факт выручки за произвольный период из DuckDB"""
    return connector.get_fact_for_period(date_start, date_end)


def _build_semi_analysis(semi_targets: dict, monthly_fact: dict, version, report_date: date) -> list:
    """Построение анализа по полугодиям"""
    result = []
    
    for sem_key, sem_data in semi_targets.items():
        sem_fact = sum(float(monthly_fact.get(month_key, 0)) for month_key in sem_data["months"])
        sem_plan = float(sem_data["target"])
        
        exec_pct = sem_fact / sem_plan * 100 if sem_plan > 0 else 0
        remaining = max(sem_plan - sem_fact, 0)
        overachievement = max(sem_fact - sem_plan, 0)
        
        is_completed = report_date > sem_data["end_date"]
        is_current = sem_data["start_date"] <= report_date <= sem_data["end_date"]
        
        # Расчеты для текущего полугодия
        current_daily_rate = 0.0
        required_daily_rate = 0.0
        gap_daily_rate = 0.0
        gap_total = 0.0
        projected_end = sem_fact
        days_remaining = 0
        rate_window_days = 0
        rate_start_date = None
        
        if is_current and sem_fact > 0:
            rate_window_days = 10
            days_remaining = max((sem_data["end_date"] - report_date).days, 0)
            rate_start_date = max(sem_data["start_date"], report_date - timedelta(days=rate_window_days - 1))
            actual_rate_days = (report_date - rate_start_date).days + 1
            
            fact_last_period = _get_fact_for_period(rate_start_date, report_date)
            current_daily_rate = fact_last_period["net_amount"] / actual_rate_days if actual_rate_days > 0 else 0.0
            projected_end = sem_fact + current_daily_rate * days_remaining
            
            if days_remaining > 0 and remaining > 0:
                required_daily_rate = remaining / days_remaining
            
            gap_daily_rate = max(required_daily_rate - current_daily_rate, 0)
            gap_total = gap_daily_rate * days_remaining
        
        result.append({
            "period": sem_data["period"],
            "plan": sem_plan,
            "fact": sem_fact,
            "exec_pct": exec_pct,
            "remaining": remaining,
            "overachievement": overachievement,
            "is_completed": is_completed,
            "is_current": is_current,
            "current_daily_rate": current_daily_rate,
            "required_daily_rate": required_daily_rate,
            "gap_daily_rate": gap_daily_rate,
            "gap_total": gap_total,
            "projected_end": projected_end,
            "days_remaining": days_remaining,
            "rate_window_days": rate_window_days,
            "rate_start_date": rate_start_date,
        })
    
    return result


def get_last_10_days_fact(report_date: date) -> list:
    """Получает факт выручки за последние 10 дней из DuckDB"""
    return connector.get_last_10_days_fact(report_date)


def get_avg_daily_rate_last_10_days(report_date: date) -> dict:
    """Рассчитывает среднюю дневную выручку за последние 10 дней"""
    last_10_days = get_last_10_days_fact(report_date)
    
    if not last_10_days:
        return {
            "avg_daily_rate": 0,
            "total_amount": 0,
            "total_sales": 0,
            "total_returns": 0,
            "days_with_sales": 0,
            "days_count": 0,
        }
    
    total_amount = sum(d["net_amount"] for d in last_10_days)
    total_sales = sum(d["sales_amount"] for d in last_10_days)
    total_returns = sum(d["returns_amount"] for d in last_10_days)
    days_count = len(last_10_days)
    days_with_sales = sum(1 for d in last_10_days if d["net_amount"] > 0)
    avg_daily_rate = total_amount / days_count if days_count > 0 else 0
    
    return {
        "avg_daily_rate": avg_daily_rate,
        "total_amount": total_amount,
        "total_sales": total_sales,
        "total_returns": total_returns,
        "days_with_sales": days_with_sales,
        "days_count": days_count,
        "last_10_days": last_10_days,
    }


def format_money_compact(value: float) -> str:
    """Компактный формат денег (1.5M, 120K)"""
    if value is None:
        return "0"
    value = float(value)
    if abs(value) >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if abs(value) >= 1_000:
        return f"{value / 1_000:.0f}K"
    return f"{value:,.0f}".replace(",", " ")


def format_money_full(value: float) -> str:
    """Полный формат денег с пробелами"""
    if value is None:
        return "0"
    return f"{float(value):,.0f}".replace(",", " ")