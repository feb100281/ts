from decimal import Decimal
from datetime import date

from django.db.models import Min, Max

from treasury.models import CfData, CfSplits

from ..registry import ACCRUAL_REGISTRY
from ..utils import q2


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


def _flow_type(code, placement_code, interest_code, return_code):
    if code == placement_code:
        return "placement"
    if code == interest_code:
        return "interest"
    if code == return_code:
        return "principal_return"
    return ""


def _flow_title(flow_type):
    return {
        "placement": "Размещение депозита",
        "interest": "Проценты по депозиту",
        "principal_return": "Возврат тела депозита",
    }.get(flow_type, "Депозит")


def preview(cond, anchor_date):
    params = cond.params or {}
    fn = "deposit_by_bank_statement"
    title = ACCRUAL_REGISTRY.get(fn, {}).get("title", fn)

    start, finish = _resolve_cash_period(cond, anchor_date)

    placement_cf_code = str(params.get("placement_cf_code") or "322100").strip()
    interest_cf_code = str(params.get("interest_cf_code") or "313100").strip()
    return_cf_code = str(params.get("return_cf_code") or "314100").strip()

    rows = []

    interest_total = Decimal("0.00")
    placed_total = Decimal("0.00")
    returned_total = Decimal("0.00")

    used_transaction_ids = set()

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
            placement_cf_code,
            interest_cf_code,
            return_cf_code,
        )

        if not flow_type:
            continue

        if flow_type == "interest":
            interest_total += amount
        elif flow_type == "placement":
            placed_total += amount
        elif flow_type == "principal_return":
            returned_total += amount

        rows.append({
            "period_from": s.transaction.date,
            "period_to": s.transaction.date,
            "days": 1,
            "amount_net": q2(amount),
            "vat_amount": Decimal("0.00"),
            "amount_gross": q2(amount),
            "amount": q2(amount),
            "vat_rate": Decimal("0"),
            "vat_mode": getattr(cond, "vat_mode", "no_vat"),
            "flow_type": flow_type,
            "cf_code": code,
            "cf_name": s.cfitem.name if s.cfitem else "",
            "comment": f"{_flow_title(flow_type)} / сплит #{s.transaction_id}",
        })

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
            placement_cf_code,
            interest_cf_code,
            return_cf_code,
        )

        if not flow_type:
            continue

        if flow_type == "interest":
            interest_total += amount
        elif flow_type == "placement":
            placed_total += amount
        elif flow_type == "principal_return":
            returned_total += amount

        rows.append({
            "period_from": p.date,
            "period_to": p.date,
            "days": 1,
            "amount_net": q2(amount),
            "vat_amount": Decimal("0.00"),
            "amount_gross": q2(amount),
            "amount": q2(amount),
            "vat_rate": Decimal("0"),
            "vat_mode": getattr(cond, "vat_mode", "no_vat"),
            "flow_type": flow_type,
            "cf_code": code,
            "cf_name": p.cfitem.name if p.cfitem else "",
            "comment": f"{_flow_title(flow_type)} #{p.id}",
        })

    principal_outstanding = placed_total - returned_total

    return {
        "condition_id": cond.id,
        "fn": fn,
        "title": title,
        "period": {"from": start, "to": finish},

        # В обычную сумму начислений берем только проценты
        "total_net": q2(interest_total),
        "total_vat": Decimal("0.00"),
        "total_gross": q2(interest_total),
        "total": q2(interest_total),

        # Отдельная аналитика по телу депозита
        "interest_total": q2(interest_total),
        "placed_total": q2(placed_total),
        "returned_total": q2(returned_total),
        "principal_outstanding": q2(principal_outstanding),

        "vat_rate": Decimal("0"),
        "vat_mode": getattr(cond, "vat_mode", "no_vat"),
        "rows": rows,
        "note": "Начисление по депозиту сформировано по данным банковской выписки.",
    }