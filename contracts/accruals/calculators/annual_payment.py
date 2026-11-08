# contracts/accruals/calculators/annual_payment.py
from datetime import date
from decimal import Decimal

from ..registry import ACCRUAL_REGISTRY
from ..utils import q2, resolve_period, split_vat


def preview(cond, anchor_date):
    params = cond.params or {}
    fn = "annual_payment"
    title = ACCRUAL_REGISTRY.get(fn, {}).get("title", fn)

    start, finish = resolve_period(cond, anchor_date)

    amount = params.get("amount")
    if amount is None:
        amount = cond.amount
    amount = Decimal(str(amount or "0"))

    payment_month = int(params.get("payment_month") or 1)
    vat_rate = Decimal(str(params.get("vat_rate") or "0"))

    if payment_month < 1 or payment_month > 12:
        return {
            "condition_id": cond.id,
            "fn": fn,
            "title": title,
            "period": {"from": str(start), "to": str(finish)},
            "total_net": "0.00",
            "total_vat": "0.00",
            "total_gross": "0.00",
            "total": "0.00",
            "vat_rate": str(vat_rate),
            "vat_mode": cond.vat_mode,
            "rows": [],
            "note": "Месяц начисления должен быть в диапазоне от 1 до 12.",
        }

    rows = []
    total_net = Decimal("0")
    total_vat = Decimal("0")
    total_gross = Decimal("0")

    for year in range(start.year, finish.year + 1):
        accrual_date = date(year, payment_month, 1)

        if accrual_date < start or accrual_date > finish:
            continue

        vat_data = split_vat(amount, cond.vat_mode, vat_rate)

        total_net += vat_data["amount_net"]
        total_vat += vat_data["vat_amount"]
        total_gross += vat_data["amount_gross"]

        rows.append({
            "accrual_date": str(accrual_date),
            "period_from": str(accrual_date),
            "period_to": str(accrual_date),
            "days": 1,
            "amount_net": str(vat_data["amount_net"]),
            "vat_amount": str(vat_data["vat_amount"]),
            "amount_gross": str(vat_data["amount_gross"]),
            "amount": str(vat_data["amount_gross"]),
            "vat_rate": str(vat_rate),
            "vat_mode": cond.vat_mode,
            "comment": f"Ежегодный платёж {amount} • месяц начисления {payment_month}",
        })

    return {
        "condition_id": cond.id,
        "fn": fn,
        "title": title,
        "period": {"from": str(start), "to": str(finish)},
        "total_net": str(q2(total_net)),
        "total_vat": str(q2(total_vat)),
        "total_gross": str(q2(total_gross)),
        "total": str(q2(total_gross)),
        "vat_rate": str(vat_rate),
        "vat_mode": cond.vat_mode,
        "rows": rows,
    }