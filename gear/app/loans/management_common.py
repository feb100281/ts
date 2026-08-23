# gear/app/loans/management_common.py
from __future__ import annotations

from calendar import monthrange
from datetime import date, datetime, timedelta
from typing import Iterable

import pandas as pd
from psycopg.rows import dict_row

from .data import get_db_connection, get_loans_snapshot


PAY_RULE_MONTHS = {
    "month": 1,
    "quarter": 3,
    "half_year": 6,
    "year": 12,
    "m2": 2,
    "m3": 3,
    "m4": 4,
    "custom": 1,
}


def _as_date(value) -> date | None:
    if value is None or value == "":
        return None
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return None
    return parsed.date()


def _safe_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _add_months(value: date, months: int, preferred_day: int | None = None) -> date:
    month_index = value.year * 12 + (value.month - 1) + months
    year = month_index // 12
    month = month_index % 12 + 1
    day = preferred_day or value.day
    day = min(max(1, day), monthrange(year, month)[1])
    return date(year, month, day)


def _first_payment_date(
    report_date: date,
    pay_day: int | None,
    pay_offset_months: int | None,
    pay_offset_days: int | None,
) -> date:
    offset_months = int(pay_offset_months or 0)
    preferred_day = int(pay_day) if pay_day else report_date.day

    result = _add_months(report_date, max(offset_months, 0), preferred_day)

    if result <= report_date:
        result = _add_months(result, 1, preferred_day)

    if pay_offset_days:
        result += timedelta(days=int(pay_offset_days))

    return result


def get_payment_terms(contract_ids: list[int] | None = None) -> pd.DataFrame:
    """
    Берём последнее актуальное условие каждого договора.
    Поля нужны только для управленческого прогноза платежей.
    """
    query = """
        SELECT DISTINCT ON (cc.contract_id)
            cc.contract_id,
            cc.pay_rule,
            cc.pay_timing,
            cc.pay_day,
            cc.pay_offset_months,
            cc.pay_offset_days,
            cc.date_start,
            cc.date_finish
        FROM public.contracts_conditions cc
        WHERE 1 = 1
    """
    params = []

    if contract_ids:
        query += " AND cc.contract_id = ANY(%s::bigint[])"
        params.append(contract_ids)

    query += """
        ORDER BY
            cc.contract_id,
            COALESCE(cc.date_start, DATE '1900-01-01') DESC,
            cc.id DESC
    """

    with get_db_connection() as conn:
        return pd.read_sql_query(query, conn, params=params)


def get_management_snapshot(report_date: str | date) -> pd.DataFrame:
    report_date = _as_date(report_date) or date.today()

    snapshot = get_loans_snapshot(report_date.isoformat())
    if snapshot.empty:
        return snapshot

    ids = [
        int(x)
        for x in snapshot["contract_id"].dropna().unique().tolist()
    ]

    terms = get_payment_terms(ids)

    if not terms.empty:
        snapshot = snapshot.merge(
            terms,
            how="left",
            on="contract_id",
        )

    defaults = {
        "pay_rule": "month",
        "pay_timing": "postpay",
        "pay_day": None,
        "pay_offset_months": 1,
        "pay_offset_days": None,
    }
    for column, default in defaults.items():
        if column not in snapshot.columns:
            snapshot[column] = default
        else:
            snapshot[column] = snapshot[column].where(
                snapshot[column].notna(),
                default,
            )

    return snapshot


def build_payment_schedule(
    snapshot: pd.DataFrame,
    report_date: str | date,
    horizon_days: int = 365,
    *,
    principal_plan: dict[int, list[dict]] | None = None,
) -> pd.DataFrame:
    """
    Управленческий прогноз.

    Базовый сценарий:
    - проценты начисляются на текущий основной долг по ставке договора;
    - дата процентной выплаты строится из pay_rule/pay_day;
    - накопленный на report_date процентный долг включается в первую выплату;
    - основной долг гасится на repayment_date;
    - principal_plan позволяет наложить сценарные досрочные погашения.

    Это forecast, а не бухгалтерский регистр начислений.
    """
    report = _as_date(report_date) or date.today()
    horizon_end = report + timedelta(days=int(horizon_days))

    if snapshot.empty:
        return pd.DataFrame(columns=[
            "payment_date",
            "contract_id",
            "counterparty_name",
            "contract_number",
            "currency",
            "payment_type",
            "principal_amount",
            "interest_amount",
            "total_amount",
            "balance_after",
            "days_from_report",
            "is_overdue",
        ])

    principal_plan = principal_plan or {}
    rows: list[dict] = []

    for item in snapshot.to_dict("records"):
        contract_id = int(item["contract_id"])
        currency = item.get("currency") or "RUB"
        balance = max(_safe_float(item.get("ending_balance")), 0.0)
        rate = max(_safe_float(item.get("rate")), 0.0)
        interest_balance = max(_safe_float(item.get("interest_balance")), 0.0)
        repayment_date = _as_date(item.get("repayment_date"))

        if balance <= 0.01 and interest_balance <= 0.01:
            continue

        pay_rule = item.get("pay_rule") or "month"
        step_months = PAY_RULE_MONTHS.get(str(pay_rule), 1)

        first_payment = _first_payment_date(
            report,
            item.get("pay_day"),
            item.get("pay_offset_months"),
            item.get("pay_offset_days"),
        )

        # Сценарные погашения тела.
        scenario = []
        for p in principal_plan.get(contract_id, []):
            p_date = _as_date(p.get("date"))
            amount = max(_safe_float(p.get("amount")), 0.0)
            if p_date and amount > 0 and report < p_date <= horizon_end:
                scenario.append((p_date, amount))

        # Базовое погашение остатка на дату окончания договора.
        if repayment_date and report < repayment_date <= horizon_end:
            scenario.append((repayment_date, float("inf")))

        scenario.sort(key=lambda x: x[0])

        # Процентные даты.
        interest_dates = []
        d = first_payment
        while d <= horizon_end:
            if repayment_date and d > repayment_date:
                break
            interest_dates.append(d)
            d = _add_months(d, step_months, item.get("pay_day"))

        event_dates = sorted(set(
            interest_dates + [x[0] for x in scenario]
        ))

        previous_date = report
        accrued_bucket = interest_balance
        scenario_by_date: dict[date, float] = {}
        for p_date, amount in scenario:
            current = scenario_by_date.get(p_date, 0.0)
            if amount == float("inf") or current == float("inf"):
                scenario_by_date[p_date] = float("inf")
            else:
                scenario_by_date[p_date] = current + amount

        for event_date in event_dates:
            if event_date <= report:
                continue

            days = max((event_date - previous_date).days, 0)
            if balance > 0 and rate > 0 and days > 0:
                accrued_bucket += balance * rate / 100.0 * days / 365.0

            principal = 0.0
            interest = 0.0

            if event_date in interest_dates:
                interest = accrued_bucket
                accrued_bucket = 0.0

            if event_date in scenario_by_date:
                requested = scenario_by_date[event_date]
                principal = balance if requested == float("inf") else min(balance, requested)
                balance = max(balance - principal, 0.0)

            if principal > 0.005 or interest > 0.005:
                rows.append({
                    "payment_date": event_date.isoformat(),
                    "contract_id": contract_id,
                    "counterparty_name": item.get("counterparty_name"),
                    "contract_number": item.get("contract_number"),
                    "currency": currency,
                    "payment_type": (
                        "Тело + проценты"
                        if principal > 0 and interest > 0
                        else "Тело"
                        if principal > 0
                        else "Проценты"
                    ),
                    "principal_amount": round(principal, 2),
                    "interest_amount": round(interest, 2),
                    "total_amount": round(principal + interest, 2),
                    "balance_after": round(balance, 2),
                    "days_from_report": (event_date - report).days,
                    "is_overdue": event_date < report,
                })

            previous_date = event_date

            if balance <= 0.01 and accrued_bucket <= 0.01:
                break

    result = pd.DataFrame(rows)
    if result.empty:
        return result

    result["payment_date"] = pd.to_datetime(result["payment_date"])
    return result.sort_values(
        ["payment_date", "counterparty_name", "contract_id"]
    ).reset_index(drop=True)


def monthly_payment_summary(schedule: pd.DataFrame) -> pd.DataFrame:
    if schedule.empty:
        return pd.DataFrame(
            columns=["month", "principal_amount", "interest_amount", "total_amount"]
        )

    work = schedule.copy()
    work["month"] = pd.to_datetime(work["payment_date"]).dt.to_period("M").dt.to_timestamp()

    return (
        work.groupby("month", as_index=False)[
            ["principal_amount", "interest_amount", "total_amount"]
        ]
        .sum()
        .sort_values("month")
    )


def get_document_counts(contract_ids: list[int] | None = None) -> pd.DataFrame:
    query = """
        SELECT
            cf.contract_id,
            COUNT(*) FILTER (
                WHERE cf.file IS NOT NULL AND cf.file <> ''
            ) AS documents_count
        FROM public.contracts_contractfiles cf
        WHERE 1 = 1
    """
    params = []
    if contract_ids:
        query += " AND cf.contract_id = ANY(%s::bigint[])"
        params.append(contract_ids)

    query += " GROUP BY cf.contract_id"

    with get_db_connection() as conn:
        return pd.read_sql_query(query, conn, params=params)
