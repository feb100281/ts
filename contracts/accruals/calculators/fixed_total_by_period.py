from decimal import Decimal

from ..registry import ACCRUAL_REGISTRY
from ..utils import q2, month_start, month_end, iter_months, resolve_period, split_vat


def preview(cond, anchor_date):
    params = cond.params or {}
    fn = "fixed_total_by_period"
    title = ACCRUAL_REGISTRY.get(fn, {}).get("title", fn)

    start, finish = resolve_period(cond, anchor_date)

    amount = params.get("amount")
    if amount is None:
        amount = cond.amount
    total_amount = Decimal(str(amount or "0"))

    vat_rate = Decimal(str(params.get("vat_rate") or "0"))

    total_days = Decimal(str((finish - start).days + 1))
    daily_amount = (total_amount / total_days) if total_days else Decimal("0")

    rows = []
    total_net = Decimal("0")
    total_vat = Decimal("0")
    total_gross = Decimal("0")

    months = list(iter_months(start, finish))

    allocated_gross = Decimal("0")

    for i, m in enumerate(months):
        m_from = month_start(m)
        m_to = month_end(m)

        p_from = max(start, m_from)
        p_to = min(finish, m_to)

        days_used = Decimal(str((p_to - p_from).days + 1))

        # Чтобы итог всегда сходился ровно в общую сумму,
        # последний месяц берем как остаток
        if i == len(months) - 1:
            part_gross = total_amount - allocated_gross
        else:
            part_gross = q2(daily_amount * days_used)
            allocated_gross += part_gross

        vat_data = split_vat(part_gross, cond.vat_mode, vat_rate)

        total_net += vat_data["amount_net"]
        total_vat += vat_data["vat_amount"]
        total_gross += vat_data["amount_gross"]

        rows.append({
            "period_from": str(p_from),
            "period_to": str(p_to),
            "days": int(days_used),
            "amount_net": str(vat_data["amount_net"]),
            "vat_amount": str(vat_data["vat_amount"]),
            "amount_gross": str(vat_data["amount_gross"]),
            "amount": str(vat_data["amount_gross"]),
            "vat_rate": str(vat_rate),
            "vat_mode": cond.vat_mode,
            "comment": (
                f"Фикс. сумма за период {total_amount} "
                f"• {int(days_used)} дн. из {int(total_days)}"
            ),
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