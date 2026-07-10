# gear/app/daily_sales/wb_plan_monitor/data.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from django.db import connection
from conns import get_duckdb_conn_with_opt

from .config import REVENUE_CODE, BUDGET_VERSION_ID, RATE_WINDOW_DAYS
from .formatters import (
    get_month_name_ru,
    get_month_name_short_ru,
    get_weekday_ru,
)


@dataclass
class BudgetVersion:
    id: int
    date_from: date


def get_budget_version():
    sql = """
        SELECT id, date_from::date
        FROM public.budget_budgetversion
        WHERE id = %s
        LIMIT 1
    """

    with connection.cursor() as cursor:
        cursor.execute(sql, [int(BUDGET_VERSION_ID)])
        row = cursor.fetchone()

    if not row:
        return None

    return BudgetVersion(
        id=int(row[0]),
        date_from=row[1],
    )


# def get_last_fact_date(date_from):
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

def get_last_fact_date(date_from):
    with get_duckdb_conn_with_opt() as con:
        row = con.execute(
            """
            SELECT MAX(date_from)::date
            FROM sales.sales_long
            WHERE date_from >= ?
              AND field = 'retail_price'
            """,
            [date_from],
        ).fetchone()

    return row[0] if row and row[0] else None



def get_monthly_plan_full_year(version_id, year):
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


# def get_monthly_fact(date_from, report_date):
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
#         cursor.execute(
#             sql,
#             [
#                 REVENUE_CODE,
#                 date_from,
#                 report_date,
#                 int(report_date.year),
#             ],
#         )
#         rows = cursor.fetchall()

#     return {
#         f"{int(year)}-{int(month):02d}": float(amount or 0)
#         for year, month, amount in rows
#     }



def get_monthly_fact(date_from, report_date):
    with get_duckdb_conn_with_opt() as con:
        rows = con.execute(
            """
            SELECT
                EXTRACT(YEAR FROM date_from) AS year,
                EXTRACT(MONTH FROM date_from) AS month,

                COALESCE(SUM(CASE WHEN oper = 'dt' THEN val ELSE 0 END), 0) / 100.0 AS sales_amount,
                COALESCE(SUM(CASE WHEN oper = 'cr' THEN val ELSE 0 END), 0) / 100.0 AS returns_amount

            FROM sales.sales_long
            WHERE date_from BETWEEN ? AND ?
              AND EXTRACT(YEAR FROM date_from) = ?
              AND field = 'retail_price'
            GROUP BY year, month
            ORDER BY year, month
            """,
            [date_from, report_date, int(report_date.year)],
        ).fetchall()

    result = {}

    for year, month, sales_amount, returns_amount in rows:
        sales_amount = float(sales_amount or 0)
        returns_amount = float(returns_amount or 0)

        result[f"{int(year)}-{int(month):02d}"] = sales_amount - returns_amount

    return result


# def get_fact_for_period(date_start, date_end):
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


def get_fact_for_period(date_start, date_end):
    with get_duckdb_conn_with_opt() as con:
        row = con.execute(
            """
            SELECT
                COALESCE(SUM(CASE WHEN oper = 'dt' THEN val ELSE 0 END), 0) / 100.0 AS sales_amount,
                COALESCE(SUM(CASE WHEN oper = 'cr' THEN val ELSE 0 END), 0) / 100.0 AS returns_amount
            FROM sales.sales_long
            WHERE date_from BETWEEN ? AND ?
              AND field = 'retail_price'
            """,
            [date_start, date_end],
        ).fetchone()

    sales_amount = float(row[0] or 0)
    returns_amount = float(row[1] or 0)

    return sales_amount - returns_amount


# def get_daily_fact(year, month, up_to_day=None):
#     sql = """
#         SELECT
#             x.date_from::date,
#             SUM(ROUND(x.amount, 2)) AS amount
#         FROM public.cf_to_csv x
#         JOIN corporate_cfitems i ON i.id = x.subconto_id
#         JOIN corporate_cfitems lv3 ON lv3.id = i.parent_id
#         WHERE lv3.code = %s
#           AND EXTRACT(YEAR FROM x.date_from) = %s
#           AND EXTRACT(MONTH FROM x.date_from) = %s
#     """

#     params = [REVENUE_CODE, int(year), int(month)]

#     if up_to_day:
#         sql += " AND EXTRACT(DAY FROM x.date_from) <= %s"
#         params.append(int(up_to_day))

#     sql += """
#         GROUP BY x.date_from::date
#         ORDER BY x.date_from::date
#     """

#     with connection.cursor() as cursor:
#         cursor.execute(sql, params)
#         rows = cursor.fetchall()

#     return [
#         {
#             "date": row[0],
#             "fact": float(row[1] or 0),
#         }
#         for row in rows
#     ]


def get_daily_fact(year, month, up_to_day=None):
    sql = """
        SELECT
            date_from::date AS date_from,

            COALESCE(SUM(CASE WHEN oper = 'dt' THEN val ELSE 0 END), 0) / 100.0 AS sales_amount,
            COALESCE(SUM(CASE WHEN oper = 'cr' THEN val ELSE 0 END), 0) / 100.0 AS returns_amount,

            COUNT(CASE WHEN oper = 'dt' THEN 1 END) AS sales_transactions,
            COUNT(CASE WHEN oper = 'cr' THEN 1 END) AS returns_transactions

        FROM sales.sales_long
        WHERE EXTRACT(YEAR FROM date_from) = ?
          AND EXTRACT(MONTH FROM date_from) = ?
          AND field = 'retail_price'
    """

    params = [int(year), int(month)]

    if up_to_day:
        sql += " AND EXTRACT(DAY FROM date_from) <= ?"
        params.append(int(up_to_day))

    sql += """
        GROUP BY date_from::date
        ORDER BY date_from::date
    """

    with get_duckdb_conn_with_opt() as con:
        rows = con.execute(sql, params).fetchall()

    result = []

    for row in rows:
        sales_amount = float(row[1] or 0)
        returns_amount = float(row[2] or 0)

        sales_transactions = int(row[3] or 0)
        returns_transactions = int(row[4] or 0)

        fact = sales_amount - returns_amount
        qty = sales_transactions - returns_transactions
        avg_price = fact / qty if qty > 0 else 0

        result.append({
            "date": row[0],
            "fact": fact,
            "sales_amount": sales_amount,
            "returns_amount": returns_amount,
            "sales_transactions": sales_transactions,
            "returns_transactions": returns_transactions,
            "qty": qty,
            "avg_price": avg_price,
        })

    return result

def get_semi_periods(year, monthly_plan):
    periods = []

    first_months = [f"{year}-{m:02d}" for m in range(1, 7)]
    second_months = [f"{year}-{m:02d}" for m in range(7, 13)]

    first_plan = sum(float(monthly_plan.get(m, 0)) for m in first_months)
    second_plan = sum(float(monthly_plan.get(m, 0)) for m in second_months)

    if first_plan > 0:
        periods.append({
            "key": "h1",
            "label": f"I полугодие {year}",
            "start": date(year, 1, 1),
            "end": date(year, 6, 30),
            "months": first_months,
            "plan": first_plan,
        })

    if second_plan > 0:
        periods.append({
            "key": "h2",
            "label": f"II полугодие {year}",
            "start": date(year, 7, 1),
            "end": date(year, 12, 31),
            "months": second_months,
            "plan": second_plan,
        })

    return periods


def build_plan_analysis():
    version = get_budget_version()

    if not version:
        return None

    report_date = get_last_fact_date(version.date_from)

    if not report_date:
        return None

    year = int(report_date.year)

    monthly_plan = get_monthly_plan_full_year(version.id, year)
    monthly_fact = get_monthly_fact(version.date_from, report_date)

    semi_periods = get_semi_periods(year, monthly_plan)

    monthly_rows = []
    running_plan = 0
    running_fact = 0

    for month in range(1, 13):
        month_key = f"{year}-{month:02d}"

        plan = float(monthly_plan.get(month_key, 0))
        fact = float(monthly_fact.get(month_key, 0))

        if plan == 0 and fact == 0:
            continue

        running_plan += plan
        running_fact += fact

        monthly_rows.append({
            "month": get_month_name_ru(month),
            "month_short": get_month_name_short_ru(month),
            "plan": plan,
            "fact": fact,
            "delta": fact - plan,
            "exec_pct": fact / plan * 100 if plan else 0,
            "running_plan": running_plan,
            "running_fact": running_fact,
            "running_delta": running_fact - running_plan,
            "running_exec_pct": running_fact / running_plan * 100 if running_plan else 0,
        })

    semi_rows = []

    for period in semi_periods:
        fact = sum(float(monthly_fact.get(m, 0)) for m in period["months"])
        plan = float(period["plan"])

        remaining = max(plan - fact, 0)
        over = max(fact - plan, 0)
        exec_pct = fact / plan * 100 if plan else 0

        is_current = period["start"] <= report_date <= period["end"]
        is_completed = report_date > period["end"]

        days_remaining = 0
        required_daily_rate = 0
        current_daily_rate = 0
        projected_end = fact
        gap_daily_rate = 0
        gap_total = 0
        rate_start = None
        rate_days = 0

        if is_current:
            days_remaining = max((period["end"] - report_date).days, 0)

            rate_start = max(
                period["start"],
                report_date - timedelta(days=RATE_WINDOW_DAYS - 1),
            )

            rate_days = (report_date - rate_start).days + 1
            fact_last_period = get_fact_for_period(rate_start, report_date)

            current_daily_rate = (
                fact_last_period / rate_days
                if rate_days > 0
                else 0
            )

            projected_end = fact + current_daily_rate * days_remaining

            if days_remaining > 0 and remaining > 0:
                required_daily_rate = remaining / days_remaining

            gap_daily_rate = max(required_daily_rate - current_daily_rate, 0)
            gap_total = gap_daily_rate * days_remaining

        semi_rows.append({
            "label": period["label"],
            "start": period["start"],
            "end": period["end"],
            "plan": plan,
            "fact": fact,
            "remaining": remaining,
            "over": over,
            "exec_pct": exec_pct,
            "is_current": is_current,
            "is_completed": is_completed,
            "days_remaining": days_remaining,
            "required_daily_rate": required_daily_rate,
            "current_daily_rate": current_daily_rate,
            "projected_end": projected_end,
            "gap_daily_rate": gap_daily_rate,
            "gap_total": gap_total,
            "rate_start": rate_start,
            "rate_days": rate_days,
        })

    current_semi = next(
        (x for x in semi_rows if x["is_current"]),
        semi_rows[-1] if semi_rows else None,
    )

    daily_raw = get_daily_fact(
        report_date.year,
        report_date.month,
        report_date.day,
    )

    # daily_rows = []
    # running_fact_daily = 0

    # for row in daily_raw:
    #     running_fact_daily += row["fact"]

    #     daily_rows.append({
    #         "date": row["date"],
    #         "date_label": row["date"].strftime("%d.%m"),
    #         "weekday": get_weekday_ru(row["date"]),
    #         "fact": row["fact"],
    #         "running_fact": running_fact_daily,
    #     })
    
    
    daily_rows = []
    running_fact_daily = 0

    for row in daily_raw:
        running_fact_daily += row["fact"]

        daily_rows.append({
            "date": row["date"],
            "date_label": row["date"].strftime("%d.%m"),
            "weekday": get_weekday_ru(row["date"]),
            "fact": row["fact"],
            "running_fact": running_fact_daily,

            "sales_amount": row["sales_amount"],
            "returns_amount": row["returns_amount"],
            "sales_transactions": row["sales_transactions"],
            "returns_transactions": row["returns_transactions"],
            "qty": row["qty"],
            "avg_price": row["avg_price"],
        })
        
    total_plan = sum(x["plan"] for x in semi_rows)
    total_fact = sum(x["fact"] for x in semi_rows)

    return {
        "version": version,
        "report_date": report_date,
        "monthly_rows": monthly_rows,
        "semi_rows": semi_rows,
        "current_semi": current_semi,
        "daily_rows": daily_rows,
        "totals": {
            "plan": total_plan,
            "fact": total_fact,
            "delta": total_fact - total_plan,
            "exec_pct": total_fact / total_plan * 100 if total_plan else 0,
        },
    }