# contracts/accruals/engine.py
from .registry import ACCRUAL_REGISTRY
from .calculators.fixed_payments import preview as preview_fixed_payments
from .calculators.by_bank_statement import preview as preview_by_bank_statement
from .calculators.rent_premises import preview as preview_rent_premises
from .calculators.deposit_by_bank_statement import preview as preview_deposit_by_bank_statement
from .calculators.own_funds_transfer import preview as preview_own_funds_transfer
from .calculators.annual_payment import preview as preview_annual_payment



PREVIEW_HANDLERS = {
    "fixed_payments": preview_fixed_payments,
    "by_bank_statement": preview_by_bank_statement,
    "rent_premises": preview_rent_premises,
    "deposit_by_bank_statement": preview_deposit_by_bank_statement,
    "own_funds_transfer": preview_own_funds_transfer,
     "annual_payment": preview_annual_payment,
    

    
}


def preview_accruals(cond, anchor_date):
    fn = cond.accrual_fn or "fixed_payments"
    title = ACCRUAL_REGISTRY.get(fn, {}).get("title", fn)

    handler = PREVIEW_HANDLERS.get(fn)
    if not handler:
        return {
            "condition_id": cond.id,
            "fn": fn,
            "title": title,
            "rows": [],
            "note": "Для этой функции пока не настроен preview.",
        }

    return handler(cond, anchor_date)