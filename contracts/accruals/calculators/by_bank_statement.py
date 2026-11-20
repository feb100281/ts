# contracts/accruals/calculators/by_bank_statement.py
# from ..registry import ACCRUAL_REGISTRY
# from ..utils import resolve_period


# def preview(cond, anchor_date):
#     fn = "by_bank_statement"
#     title = ACCRUAL_REGISTRY.get(fn, {}).get("title", fn)

#     start, finish = resolve_period(cond, anchor_date)

#     return {
#         "condition_id": cond.id,
#         "fn": fn,
#         "title": title,
#         "period": {"from": str(start), "to": str(finish)},
#         "rows": [],
#         "note": "Начисление определяется по данным банковской выписки (cash-based).",
#     }



# from decimal import Decimal

# from treasury.models import CfData, CfSplits

# from ..registry import ACCRUAL_REGISTRY
# from ..utils import q2, resolve_period, split_vat


# def _payment_amount_from_cfdata(obj: CfData) -> Decimal:
#     cr = q2(obj.cr)
#     dt = q2(obj.dt)

#     if cr > 0:
#         return cr
#     if dt > 0:
#         return dt
#     return Decimal("0.00")


# def _payment_amount_from_split(obj: CfSplits) -> Decimal:
#     cr = q2(obj.cr)
#     dt = q2(obj.dt)

#     if cr > 0:
#         return cr
#     if dt > 0:
#         return dt
#     return Decimal("0.00")


# def preview(cond, anchor_date):
#     params = cond.params or {}
#     fn = "by_bank_statement"
#     title = ACCRUAL_REGISTRY.get(fn, {}).get("title", fn)

#     start, finish = resolve_period(cond, anchor_date)

#     vat_rate = Decimal(str(params.get("vat_rate") or "0"))

#     rows = []
#     total_net = Decimal("0.00")
#     total_vat = Decimal("0.00")
#     total_gross = Decimal("0.00")

#     used_transaction_ids = set()

#     # 1. Сначала берем сплиты
#     split_qs = (
#         CfSplits.objects
#         .select_related("transaction", "contract", "cfitem")
#         .filter(
#             contract=cond.contract,
#             transaction__date__gte=start,
#             transaction__date__lte=finish,
#         )
#         .order_by("transaction__date", "id")
#     )

#     for s in split_qs:
#         amount = _payment_amount_from_split(s)
#         if amount <= 0:
#             continue

#         used_transaction_ids.add(s.transaction_id)

#         vat_data = split_vat(amount, cond.vat_mode, vat_rate)

#         total_net += vat_data["amount_net"]
#         total_vat += vat_data["vat_amount"]
#         total_gross += vat_data["amount_gross"]

#         rows.append({
#             "period_from": str(s.transaction.date),
#             "period_to": str(s.transaction.date),
#             "days": 1,
#             "amount_net": str(vat_data["amount_net"]),
#             "vat_amount": str(vat_data["vat_amount"]),
#             "amount_gross": str(vat_data["amount_gross"]),
#             "amount": str(vat_data["amount_gross"]),
#             "vat_rate": str(vat_rate),
#             "vat_mode": cond.vat_mode,
#             "comment": f"Начисление по банковской выписке / сплит #{s.transaction_id}",
#             "source": "cf_split",
#             "source_id": s.id,
#             "source_transaction_id": s.transaction_id,
#         })

#     # 2. Потом прямые записи CfData, которые не были разложены сплитами
#     cf_qs = (
#         CfData.objects
#         .select_related("contract", "cfitem")
#         .filter(
#             contract=cond.contract,
#             date__gte=start,
#             date__lte=finish,
#         )
#         .exclude(id__in=used_transaction_ids)
#         .order_by("date", "id")
#     )

#     for p in cf_qs:
#         amount = _payment_amount_from_cfdata(p)
#         if amount <= 0:
#             continue

#         vat_data = split_vat(amount, cond.vat_mode, vat_rate)

#         total_net += vat_data["amount_net"]
#         total_vat += vat_data["vat_amount"]
#         total_gross += vat_data["amount_gross"]

#         rows.append({
#             "period_from": str(p.date),
#             "period_to": str(p.date),
#             "days": 1,
#             "amount_net": str(vat_data["amount_net"]),
#             "vat_amount": str(vat_data["vat_amount"]),
#             "amount_gross": str(vat_data["amount_gross"]),
#             "amount": str(vat_data["amount_gross"]),
#             "vat_rate": str(vat_rate),
#             "vat_mode": cond.vat_mode,
#             "comment": f"Начисление по банковской выписке #{p.id}",
#             "source": "cf_data",
#             "source_id": p.id,
#         })

#     return {
#         "condition_id": cond.id,
#         "fn": fn,
#         "title": title,
#         "period": {"from": str(start), "to": str(finish)},
#         "total_net": str(q2(total_net)),
#         "total_vat": str(q2(total_vat)),
#         "total_gross": str(q2(total_gross)),
#         "total": str(q2(total_gross)),
#         "vat_rate": str(vat_rate),
#         "vat_mode": cond.vat_mode,
#         "rows": rows,
#         "note": "Начисление сформировано по данным банковской выписки (cash-based).",
#     }



# from decimal import Decimal

# from treasury.models import CfData, CfSplits

# from ..registry import ACCRUAL_REGISTRY
# from ..utils import q2, resolve_period, split_vat


# def _payment_amount_from_cfdata(obj: CfData) -> Decimal:
#     cr = q2(obj.cr)
#     dt = q2(obj.dt)

#     if cr > 0:
#         return cr
#     if dt > 0:
#         return dt
#     return Decimal("0.00")


# def _payment_amount_from_split(obj: CfSplits) -> Decimal:
#     cr = q2(obj.cr)
#     dt = q2(obj.dt)

#     if cr > 0:
#         return cr
#     if dt > 0:
#         return dt
#     return Decimal("0.00")


# def preview(cond, anchor_date):
#     params = cond.params or {}
#     fn = "by_bank_statement"
#     title = ACCRUAL_REGISTRY.get(fn, {}).get("title", fn)

#     start, finish = resolve_period(cond, anchor_date)
#     vat_rate = Decimal(str(params.get("vat_rate") or "0"))

#     rows = []
#     total_net = Decimal("0.00")
#     total_vat = Decimal("0.00")
#     total_gross = Decimal("0.00")

#     used_transaction_ids = set()

#     split_qs = (
#         CfSplits.objects
#         .select_related("transaction", "contract", "cfitem")
#         .filter(
#             contract=cond.contract,
#             transaction__date__gte=start,
#             transaction__date__lte=finish,
#         )
#         .order_by("transaction__date", "id")
#     )

#     for s in split_qs:
#         amount = _payment_amount_from_split(s)
#         if amount <= 0:
#             continue

#         used_transaction_ids.add(s.transaction_id)

#         vat_data = split_vat(amount, cond.vat_mode, vat_rate)

#         total_net += vat_data["amount_net"]
#         total_vat += vat_data["vat_amount"]
#         total_gross += vat_data["amount_gross"]

#         rows.append({
#             "period_from": s.transaction.date,
#             "period_to": s.transaction.date,
#             "days": 1,
#             "amount_net": vat_data["amount_net"],
#             "vat_amount": vat_data["vat_amount"],
#             "amount_gross": vat_data["amount_gross"],
#             "amount": vat_data["amount_gross"],
#             "vat_rate": vat_rate,
#             "vat_mode": cond.vat_mode,
#             "comment": f"Начисление по выписке / сплит #{s.transaction_id}",
#         })

#     cf_qs = (
#         CfData.objects
#         .select_related("contract", "cfitem")
#         .filter(
#             contract=cond.contract,
#             date__gte=start,
#             date__lte=finish,
#         )
#         .exclude(id__in=used_transaction_ids)
#         .order_by("date", "id")
#     )

#     for p in cf_qs:
#         amount = _payment_amount_from_cfdata(p)
#         if amount <= 0:
#             continue

#         vat_data = split_vat(amount, cond.vat_mode, vat_rate)

#         total_net += vat_data["amount_net"]
#         total_vat += vat_data["vat_amount"]
#         total_gross += vat_data["amount_gross"]

#         rows.append({
#             "period_from": p.date,
#             "period_to": p.date,
#             "days": 1,
#             "amount_net": vat_data["amount_net"],
#             "vat_amount": vat_data["vat_amount"],
#             "amount_gross": vat_data["amount_gross"],
#             "amount": vat_data["amount_gross"],
#             "vat_rate": vat_rate,
#             "vat_mode": cond.vat_mode,
#             "comment": f"Начисление по выписке #{p.id}",
#         })

#     return {
#         "condition_id": cond.id,
#         "fn": fn,
#         "title": title,
#         "period": {"from": start, "to": finish},
#         "total_net": q2(total_net),
#         "total_vat": q2(total_vat),
#         "total_gross": q2(total_gross),
#         "total": q2(total_gross),
#         "vat_rate": vat_rate,
#         "vat_mode": cond.vat_mode,
#         "rows": rows,
#         "note": "Начисление сформировано по данным банковской выписки.",
#     }


# contracts/accruals/calculators/by_bank_statement.py

from decimal import Decimal
from datetime import date

from django.db.models import Min, Max

from treasury.models import CfData, CfSplits

from ..registry import ACCRUAL_REGISTRY
from ..utils import q2, split_vat


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
    Для cash-based не ограничиваемся только текущим месяцем,
    если условие бессрочное. Берем фактический горизонт движения денег.
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


def preview(cond, anchor_date):
    params = cond.params or {}
    fn = "by_bank_statement"
    title = ACCRUAL_REGISTRY.get(fn, {}).get("title", fn)

    start, finish = _resolve_cash_period(cond, anchor_date)
    vat_rate = Decimal(str(params.get("vat_rate") or "0"))

    rows = []
    total_net = Decimal("0.00")
    total_vat = Decimal("0.00")
    total_gross = Decimal("0.00")

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

        vat_data = split_vat(amount, cond.vat_mode, vat_rate)

        total_net += vat_data["amount_net"]
        total_vat += vat_data["vat_amount"]
        total_gross += vat_data["amount_gross"]

        rows.append({
            "period_from": s.transaction.date,
            "period_to": s.transaction.date,
            "days": 1,
            "amount_net": vat_data["amount_net"],
            "vat_amount": vat_data["vat_amount"],
            "amount_gross": vat_data["amount_gross"],
            "amount": vat_data["amount_gross"],
            "vat_rate": vat_rate,
            "vat_mode": cond.vat_mode,
            "comment": f"Начисление по выписке / сплит #{s.transaction_id}",
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

        vat_data = split_vat(amount, cond.vat_mode, vat_rate)

        total_net += vat_data["amount_net"]
        total_vat += vat_data["vat_amount"]
        total_gross += vat_data["amount_gross"]

        rows.append({
            "period_from": p.date,
            "period_to": p.date,
            "days": 1,
            "amount_net": vat_data["amount_net"],
            "vat_amount": vat_data["vat_amount"],
            "amount_gross": vat_data["amount_gross"],
            "amount": vat_data["amount_gross"],
            "vat_rate": vat_rate,
            "vat_mode": cond.vat_mode,
            "comment": f"Начисление по выписке #{p.id}",
        })

    return {
        "condition_id": cond.id,
        "fn": fn,
        "title": title,
        "period": {"from": start, "to": finish},
        "total_net": q2(total_net),
        "total_vat": q2(total_vat),
        "total_gross": q2(total_gross),
        "total": q2(total_gross),
        "vat_rate": vat_rate,
        "vat_mode": cond.vat_mode,
        "rows": rows,
        "note": "Начисление сформировано по данным банковской выписки.",
    }