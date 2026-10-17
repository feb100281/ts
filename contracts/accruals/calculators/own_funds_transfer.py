from decimal import Decimal

from ..registry import ACCRUAL_REGISTRY
from ..utils import q2


def preview(cond, anchor_date):
    fn = "own_funds_transfer"
    title = ACCRUAL_REGISTRY.get(fn, {}).get("title", fn)

    return {
        "condition_id": cond.id,
        "fn": fn,
        "title": title,
        "period": {
            "from": cond.date_start or anchor_date,
            "to": cond.date_finish or anchor_date,
        },
        "total_net": q2(Decimal("0.00")),
        "total_vat": q2(Decimal("0.00")),
        "total_gross": q2(Decimal("0.00")),
        "total": q2(Decimal("0.00")),
        "vat_rate": Decimal("0"),
        "vat_mode": getattr(cond, "vat_mode", "no_vat"),
        "rows": [],
        "note": "По переводу собственных средств начисления не формируются.",
    }