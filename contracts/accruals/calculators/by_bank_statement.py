from ..registry import ACCRUAL_REGISTRY
from ..utils import resolve_period


def preview(cond, anchor_date):
    fn = "by_bank_statement"
    title = ACCRUAL_REGISTRY.get(fn, {}).get("title", fn)

    start, finish = resolve_period(cond, anchor_date)

    return {
        "condition_id": cond.id,
        "fn": fn,
        "title": title,
        "period": {"from": str(start), "to": str(finish)},
        "rows": [],
        "note": "Начисление определяется по данным банковской выписки (cash-based).",
    }