# contracts/reconciliation/portfolio_report.py
from __future__ import annotations

from datetime import date, timedelta
from calendar import monthrange
from decimal import Decimal

from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required

from contracts.models import Contracts, Conditions
from contracts.reconciliation.service import q2, _get_payment_total_before
from contracts.accruals.engine import preview_accruals
from treasury.models import CfData, CfSplits


MONTHS_RU_NOMINATIVE = {
    1: "январь",
    2: "февраль",
    3: "март",
    4: "апрель",
    5: "май",
    6: "июнь",
    7: "июль",
    8: "август",
    9: "сентябрь",
    10: "октябрь",
    11: "ноябрь",
    12: "декабрь",
}


def format_money(val: Decimal) -> str:
    val = q2(val)
    return f"{val:,.2f}".replace(",", " ").replace(".", ",")


def get_report_period(request):
    month_str = request.GET.get("month")

    if month_str:
        try:
            year_str, month_str_only = month_str.split("-")
            year = int(year_str)
            month = int(month_str_only)
            if not (1 <= month <= 12):
                raise ValueError
            return year, month, month_str
        except Exception:
            pass

    today = date.today()
    return today.year, today.month, f"{today.year:04d}-{today.month:02d}"


def pluralize_contracts(count: int) -> str:
    n = abs(count) % 100
    n1 = n % 10
    if 11 <= n <= 19:
        return "договоров"
    if n1 == 1:
        return "договор"
    if 2 <= n1 <= 4:
        return "договора"
    return "договоров"


def _safe_date(value):
    from datetime import datetime, date as dt_date

    if not value:
        return None

    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, dt_date):
        return value

    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None

        for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%Y-%m-%d %H:%M:%S", "%d.%m.%Y %H:%M:%S"):
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                pass

    return None


def _is_deposit_condition(cond: Conditions) -> bool:
    return (cond.accrual_fn or "") == "deposit_by_bank_statement"


def _is_deposit_principal_flow(flow_type: str) -> bool:
    return flow_type in {"placement", "principal_return"}


def get_balance_label(balance: Decimal) -> str:
    balance = q2(balance)

    if balance > 0:
        return "Дебитор"
    if balance < 0:
        return "Кредитор"
    return "Закрыто"


def get_balance_class(balance: Decimal) -> str:
    balance = q2(balance)

    if balance > 0:
        return "is-debtor"
    if balance < 0:
        return "is-creditor"
    return "is-closed"


def _get_accrual_total_to_date(contract: Contracts, end_date: date) -> Decimal:
    """
    Считаем все начисления по договору накопительно до end_date включительно.
    Это проще для отчета по сальдо на конец месяца.
    """
    total = Decimal("0.00")

    conditions = (
        Conditions.objects
        .filter(contract=contract)
        .order_by("date_start", "id")
    )

    for cond in conditions:
        result = preview_accruals(cond, anchor_date=end_date)
        rows = result.get("rows", []) or []

        for r in rows:
            row_date = _safe_date(r.get("accrual_date")) or _safe_date(r.get("period_from"))
            flow_type = (r.get("flow_type") or "").strip()

            if not row_date:
                continue

            if _is_deposit_condition(cond) and _is_deposit_principal_flow(flow_type):
                continue

            if row_date <= end_date:
                total += q2(r.get("amount_gross") or r.get("amount") or "0")

    return q2(total)


@staff_member_required
def debt_report(request):
    year, month, selected_month = get_report_period(request)

    start_date = date(year, month, 1)
    end_date = date(year, month, monthrange(year, month)[1])
    next_day = end_date + timedelta(days=1)

    condition_contract_ids = set(
        Conditions.objects
        .filter(date_start__lte=end_date)
        .values_list("contract_id", flat=True)
    )

    cfdata_contract_ids = set(
        CfData.objects
        .filter(date__lte=end_date, contract_id__isnull=False)
        .values_list("contract_id", flat=True)
    )

    cfsplit_contract_ids = set(
        CfSplits.objects
        .filter(transaction__date__lte=end_date, contract_id__isnull=False)
        .values_list("contract_id", flat=True)
    )

    contract_ids = condition_contract_ids | cfdata_contract_ids | cfsplit_contract_ids

    contracts_qs = (
        Contracts.objects
        .select_related("cp")
        .filter(id__in=contract_ids)
        .order_by("cp__name", "number", "id")
    )

    rows = []
    total_debit_raw = Decimal("0.00")
    total_credit_raw = Decimal("0.00")
    debit_count = 0
    credit_count = 0
    closed_count = 0

    for contract in contracts_qs:
        cp = getattr(contract, "cp", None)
        contragent_name = getattr(cp, "name", "—") or "—"

        try:
            total_accruals = _get_accrual_total_to_date(contract, end_date)
            total_payments = _get_payment_total_before(contract, next_day)
            closing_balance = q2(total_accruals - total_payments)
        except Exception:
            continue

        if (
            total_accruals == Decimal("0.00")
            and total_payments == Decimal("0.00")
            and closing_balance == Decimal("0.00")
        ):
            continue

        balance_label = get_balance_label(closing_balance)
        balance_class = get_balance_class(closing_balance)

        if closing_balance > 0:
            debit_count += 1
            total_debit_raw += closing_balance
        elif closing_balance < 0:
            credit_count += 1
            total_credit_raw += abs(closing_balance)
        else:
            closed_count += 1

        rows.append({
            "contragent": contragent_name,
            "contract_number": contract.number or "без номера",
            "contract_title": str(contract.title) if contract.title else "—",
            "total_accruals_raw": total_accruals,
            "total_accruals": format_money(total_accruals),
            "total_payments_raw": total_payments,
            "total_payments": format_money(total_payments),
            "closing_balance_raw": closing_balance,
            "closing_balance_abs": format_money(abs(closing_balance)),
            "balance_label": balance_label,
            "balance_class": balance_class,
            "contract_id": contract.id,
        })

    def sort_key(r):
        bal = r["closing_balance_raw"]
        if bal > 0:
            return (0, -bal, r["contragent"])
        if bal < 0:
            return (1, -abs(bal), r["contragent"])
        return (2, 0, r["contragent"])

    rows.sort(key=sort_key)

    total_net_raw = q2(total_debit_raw - total_credit_raw)
    month_label = f"{MONTHS_RU_NOMINATIVE[month]} {year}"

    return render(
        request,
        "contracts/debt_report.html",
        {
            "rows": rows,
            "month_label": month_label,
            "start_date": start_date,
            "end_date": end_date,
            "selected_month": selected_month,

            "debit_count": debit_count,
            "credit_count": credit_count,
            "closed_count": closed_count,

            "debit_count_label": pluralize_contracts(debit_count),
            "credit_count_label": pluralize_contracts(credit_count),
            "closed_count_label": pluralize_contracts(closed_count),

            "total_debit": format_money(total_debit_raw),
            "total_credit": format_money(total_credit_raw),
            "total_net": format_money(total_net_raw),
            "total_net_raw": total_net_raw,
        },
    )