# contracts/accruals/calculators/loan_by_bank_statement.py

from decimal import Decimal
from datetime import date, timedelta
import calendar

from django.db.models import Min, Max

from treasury.models import CfData, CfSplits

from ..registry import ACCRUAL_REGISTRY
from ..utils import q2


def _days_in_year(d: date) -> Decimal:
    return Decimal("366") if calendar.isleap(d.year) else Decimal("365")


def _payment_amount_from_cfdata(obj: CfData) -> Decimal:
    cr = q2(obj.cr)
    dt = q2(obj.dt)

    if cr > 0:
        return cr
    if dt > 0:
        return dt
    return Decimal("0.00")


def _payment_amount_from_split(obj: CfSplits) -> Decimal:
    cr = q2(obj.cr)
    dt = q2(obj.dt)

    if cr > 0:
        return cr
    if dt > 0:
        return dt
    return Decimal("0.00")


def _resolve_cash_period(cond, anchor_date):
    """
    Если у условия задан date_start / date_finish -> берем их.
    Иначе ищем границы по движению денег по договору.
    """
    if cond.date_start or cond.date_finish:
        start = cond.date_start or anchor_date
        finish = cond.date_finish or anchor_date
        return start, finish

    cf_agg = CfData.objects.filter(contract=cond.contract).aggregate(
        min_date=Min("date"),
        max_date=Max("date"),
    )

    split_agg = CfSplits.objects.filter(contract=cond.contract).aggregate(
        min_date=Min("transaction__date"),
        max_date=Max("transaction__date"),
    )

    candidate_starts = [
        cf_agg.get("min_date"),
        split_agg.get("min_date"),
    ]
    candidate_finishes = [
        cf_agg.get("max_date"),
        split_agg.get("max_date"),
        date.today(),
    ]

    candidate_starts = [d for d in candidate_starts if d]
    candidate_finishes = [d for d in candidate_finishes if d]

    start = min(candidate_starts) if candidate_starts else anchor_date
    finish = max(candidate_finishes) if candidate_finishes else anchor_date

    return start, finish


def _cfitem_code(cfitem) -> str:
    if not cfitem:
        return ""
    return str(cfitem.code or "").strip()


def _flow_type(code, issue_code, principal_return_code, interest_payment_code):
    """
    issue               -> выдача тела кредита / займа
    principal_return    -> возврат тела
    interest_payment    -> оплата процентов
    """
    if code == issue_code:
        return "issue"
    if code == principal_return_code:
        return "principal_return"
    if code == interest_payment_code:
        return "interest_payment"
    return ""


def _flow_title(flow_type):
    return {
        "issue": "Выдача кредита",
        "principal_return": "Возврат тела кредита",
        "interest_payment": "Оплата процентов",
        "interest_accrual": "Начисление процентов",
    }.get(flow_type, "Кредит")


def _iter_dates(start_date: date, end_date: date):
    current = start_date
    while current <= end_date:
        yield current
        current += timedelta(days=1)


def _group_cash_flows_by_date(cash_flows: list[dict]) -> dict[date, list[dict]]:
    result = {}
    for row in cash_flows:
        d = row["flow_date"]
        result.setdefault(d, []).append(row)
    return result


def preview(cond, anchor_date):
    """
    Логика:
    1. Из выписки читаем:
       - выдачу кредита
       - возврат тела
       - оплату процентов
    2. Проценты начисляем ежедневно на фактический остаток тела.
    3. В total попадают только начисленные проценты.
    4. Тело кредита показываем отдельной аналитикой.
    """
    params = cond.params or {}
    fn = "loan_by_bank_statement"
    title = ACCRUAL_REGISTRY.get(fn, {}).get("title", fn)

    start, finish = _resolve_cash_period(cond, anchor_date)

    annual_rate = q2(params.get("annual_rate") or "0")
    vat_rate = q2(params.get("vat_rate") or "0")

    issue_cf_code = str(params.get("issue_cf_code") or "").strip()
    principal_return_cf_code = str(params.get("principal_return_cf_code") or "").strip()
    interest_payment_cf_code = str(params.get("interest_payment_cf_code") or "").strip()

    interest_start_mode = str(params.get("interest_start_mode") or "next_day").strip()
    if interest_start_mode not in {"same_day", "next_day"}:
        interest_start_mode = "next_day"

    rows = []

    issued_total = Decimal("0.00")
    principal_returned_total = Decimal("0.00")
    interest_paid_total = Decimal("0.00")
    interest_accrued_total = Decimal("0.00")

    used_transaction_ids = set()
    cash_flows = []

    # ---------------------------------------------------------
    # 1. Сначала сплиты
    # ---------------------------------------------------------
    split_qs = (
        CfSplits.objects
        .select_related("transaction", "contract", "cfitem")
        .filter(
            contract=cond.contract,
            transaction__date__gte=start,
            transaction__date__lte=finish,
        )
        .order_by("transaction__date", "id")
    )

    for s in split_qs:
        amount = _payment_amount_from_split(s)
        if amount <= 0:
            continue

        used_transaction_ids.add(s.transaction_id)

        code = _cfitem_code(s.cfitem)
        flow_type = _flow_type(
            code,
            issue_cf_code,
            principal_return_cf_code,
            interest_payment_cf_code,
        )
        if not flow_type:
            continue

        cash_flows.append({
            "flow_date": s.transaction.date,
            "flow_type": flow_type,
            "amount": q2(amount),
            "cf_code": code,
            "cf_name": s.cfitem.name if s.cfitem else "",
            "comment": f"{_flow_title(flow_type)} / сплит #{s.transaction_id}",
        })

    # ---------------------------------------------------------
    # 2. Потом прямые CfData, которых нет в сплитах
    # ---------------------------------------------------------
    cf_qs = (
        CfData.objects
        .select_related("contract", "cfitem")
        .filter(
            contract=cond.contract,
            date__gte=start,
            date__lte=finish,
        )
        .exclude(id__in=used_transaction_ids)
        .order_by("date", "id")
    )

    for p in cf_qs:
        amount = _payment_amount_from_cfdata(p)
        if amount <= 0:
            continue

        code = _cfitem_code(p.cfitem)
        flow_type = _flow_type(
            code,
            issue_cf_code,
            principal_return_cf_code,
            interest_payment_cf_code,
        )
        if not flow_type:
            continue

        cash_flows.append({
            "flow_date": p.date,
            "flow_type": flow_type,
            "amount": q2(amount),
            "cf_code": code,
            "cf_name": p.cfitem.name if p.cfitem else "",
            "comment": f"{_flow_title(flow_type)} #{p.id}",
        })

    cash_flows.sort(key=lambda x: (x["flow_date"], x["flow_type"], x["amount"]))

    # ---------------------------------------------------------
    # 3. Фактические движения из выписки — сразу в rows
    # ---------------------------------------------------------
    for f in cash_flows:
        if f["flow_type"] == "issue":
            issued_total += f["amount"]
        elif f["flow_type"] == "principal_return":
            principal_returned_total += f["amount"]
        elif f["flow_type"] == "interest_payment":
            interest_paid_total += f["amount"]

        rows.append({
            "accrual_date": f["flow_date"],
            "period_from": f["flow_date"],
            "period_to": f["flow_date"],
            "days": 1,
            "amount_net": q2(f["amount"]),
            "vat_amount": Decimal("0.00"),
            "amount_gross": q2(f["amount"]),
            "amount": q2(f["amount"]),
            "vat_rate": vat_rate,
            "vat_mode": getattr(cond, "vat_mode", "no_vat"),
            "flow_type": f["flow_type"],
            "cf_code": f["cf_code"],
            "cf_name": f["cf_name"],
            "comment": f["comment"],
        })

    # ---------------------------------------------------------
    # 4. Начисляем проценты на остаток тела по дням
    # ---------------------------------------------------------
    flow_map = _group_cash_flows_by_date(cash_flows)
    principal_balance = Decimal("0.00")

    for current_date in _iter_dates(start, finish):
        current_flows = flow_map.get(current_date, [])

        # same_day:
        # движения текущего дня сразу участвуют в расчете процентов за этот день
        if interest_start_mode == "same_day":
            for f in current_flows:
                if f["flow_type"] == "issue":
                    principal_balance += q2(f["amount"])
                elif f["flow_type"] == "principal_return":
                    principal_balance -= q2(f["amount"])

        if principal_balance < 0:
            principal_balance = Decimal("0.00")

        day_count_basis = _days_in_year(current_date)

        daily_interest = q2(
            principal_balance * annual_rate / Decimal("100") / day_count_basis
        )

        if daily_interest > 0:
            interest_accrued_total += daily_interest
            rows.append({
                "accrual_date": current_date,
                "period_from": current_date,
                "period_to": current_date,
                "days": 1,
                "amount_net": daily_interest,
                "vat_amount": Decimal("0.00"),
                "amount_gross": daily_interest,
                "amount": daily_interest,
                "vat_rate": vat_rate,
                "vat_mode": getattr(cond, "vat_mode", "no_vat"),
                "flow_type": "interest_accrual",
                "cf_code": "",
                "cf_name": "",
                "comment": "Начисление процентов на остаток тела кредита",
                "principal_balance": q2(principal_balance),
                "annual_rate": q2(annual_rate),
                "day_count_basis": q2(day_count_basis),
            })

        # next_day:
        # движения текущего дня начинают влиять на проценты только со следующего дня
        if interest_start_mode == "next_day":
            for f in current_flows:
                if f["flow_type"] == "issue":
                    principal_balance += q2(f["amount"])
                elif f["flow_type"] == "principal_return":
                    principal_balance -= q2(f["amount"])

        if principal_balance < 0:
            principal_balance = Decimal("0.00")

    principal_outstanding = q2(issued_total - principal_returned_total)
    interest_outstanding = q2(interest_accrued_total - interest_paid_total)

    rows.sort(
        key=lambda x: (
            x.get("accrual_date") or x.get("period_from") or start,
            x.get("flow_type") or "",
            x.get("comment") or "",
        )
    )

    return {
        "condition_id": cond.id,
        "fn": fn,
        "title": title,
        "period": {"from": start, "to": finish},

        # В начисление берем только проценты
        "total_net": q2(interest_accrued_total),
        "total_vat": Decimal("0.00"),
        "total_gross": q2(interest_accrued_total),
        "total": q2(interest_accrued_total),

        # Аналитика по телу кредита
        "issued_total": q2(issued_total),
        "principal_returned_total": q2(principal_returned_total),
        "principal_outstanding": q2(principal_outstanding),

        # Аналитика по процентам
        "interest_accrued_total": q2(interest_accrued_total),
        "interest_paid_total": q2(interest_paid_total),
        "interest_outstanding": q2(interest_outstanding),

        "vat_rate": vat_rate,
        "vat_mode": getattr(cond, "vat_mode", "no_vat"),
        "rows": rows,
        "note": "Проценты по кредиту рассчитаны на фактический остаток тела кредита по данным банковской выписки.",
    }