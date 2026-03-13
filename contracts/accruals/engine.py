# # contracts/accruals/engine.py
# from .registry import ACCRUAL_REGISTRY
# from .calculators.fixed_payments import preview as preview_fixed_payments
# from .calculators.fixed_total_by_period import preview as preview_fixed_total_by_period
# from .calculators.by_bank_statement import preview as preview_by_bank_statement
# from .calculators.rent_premises import preview as preview_rent_premises
# from .calculators.deposit_by_bank_statement import preview as preview_deposit_by_bank_statement
# from .calculators.own_funds_transfer import preview as preview_own_funds_transfer
# from .calculators.annual_payment import preview as preview_annual_payment
# from .calculators.loan_by_bank_statement import preview as preview_loan_by_bank_statement




# PREVIEW_HANDLERS = {
#     "fixed_payments": preview_fixed_payments,
#     "fixed_total_by_period": preview_fixed_total_by_period,
#     "by_bank_statement": preview_by_bank_statement,
#     "rent_premises": preview_rent_premises,
#     "deposit_by_bank_statement": preview_deposit_by_bank_statement,
#     "own_funds_transfer": preview_own_funds_transfer,
#      "annual_payment": preview_annual_payment,
#     "loan_by_bank_statement": preview_loan_by_bank_statement,
     
    

    
# }


# def preview_accruals(cond, anchor_date):
#     fn = cond.accrual_fn or "fixed_payments"
#     title = ACCRUAL_REGISTRY.get(fn, {}).get("title", fn)

#     handler = PREVIEW_HANDLERS.get(fn)
#     if not handler:
#         return {
#             "condition_id": cond.id,
#             "fn": fn,
#             "title": title,
#             "rows": [],
#             "note": "Для этой функции пока не настроен preview.",
#         }

#     return handler(cond, anchor_date)



# contracts/accruals/engine.py

# contracts/accruals/engine.py

import importlib

from .registry import ACCRUAL_REGISTRY
from .calculators.fixed_payments import preview as preview_fixed_payments
from .calculators.fixed_total_by_period import preview as preview_fixed_total_by_period
from .calculators.by_bank_statement import preview as preview_by_bank_statement
from .calculators.rent_premises import preview as preview_rent_premises
from .calculators.deposit_by_bank_statement import preview as preview_deposit_by_bank_statement
from .calculators.own_funds_transfer import preview as preview_own_funds_transfer
from .calculators.annual_payment import preview as preview_annual_payment
from .calculators.loan_by_bank_statement import preview as preview_loan_by_bank_statement


PREVIEW_HANDLERS = {
    "fixed_payments": preview_fixed_payments,
    "fixed_total_by_period": preview_fixed_total_by_period,
    "by_bank_statement": preview_by_bank_statement,
    "rent_premises": preview_rent_premises,
    "deposit_by_bank_statement": preview_deposit_by_bank_statement,
    "own_funds_transfer": preview_own_funds_transfer,
    "annual_payment": preview_annual_payment,
    "loan_by_bank_statement": preview_loan_by_bank_statement,
}


def build_new_logic_args(cond):
    contract = cond.contract

    return {
        "contract_id": contract.id,
        "condition_id": cond.id,
        "company_id": getattr(contract.owner, "id", None),

        "date_start": cond.date_start,
        "date_finish": cond.date_finish,

        "amount": cond.amount,
        "currency": contract.currency,

        "vat_mode": cond.vat_mode,
        "vat_json": cond.vat_json or {},
        "params_json": cond.param_json or {},

        "acc_bs_id": cond.acc_bs_id,
        "subconto_bs_id": cond.subconto_bs_id,
        "acc_pl_id": cond.acc_pl_id,
        "subconto_pl_id": cond.subconto_pl_id,

        "acc_st_id": contract.st_id,
        "fn_id": cond.fn_id,
    }


def preview_accruals(cond, anchor_date):
    # новая логика через cond.fn
    if cond.fn_id and cond.fn and cond.fn.python_path:
        try:
            module = importlib.import_module(cond.fn.python_path)
        except Exception as e:
            return {
                "condition_id": cond.id,
                "fn": f"new:{cond.fn_id}",
                "title": cond.fn.name if cond.fn else "Новая функция",
                "rows": [],
                "note": f"Не удалось импортировать модуль {cond.fn.python_path}: {e}",
            }

        if not hasattr(module, "preview"):
            return {
                "condition_id": cond.id,
                "fn": f"new:{cond.fn_id}",
                "title": cond.fn.name if cond.fn else "Новая функция",
                "rows": [],
                "note": f"В модуле {cond.fn.python_path} нет функции preview(conn, **args).",
            }

        try:
            from django.db import connection

            if connection.connection is None:
                connection.ensure_connection()

            conn = connection.connection
            args = build_new_logic_args(cond)

            result = module.preview(conn, **args)

            if isinstance(result, dict):
                result.setdefault("condition_id", cond.id)
                result.setdefault("fn", f"new:{cond.fn_id}")
                result.setdefault("title", cond.fn.name if cond.fn else "Новая функция")
                return result

            return {
                "condition_id": cond.id,
                "fn": f"new:{cond.fn_id}",
                "title": cond.fn.name if cond.fn else "Новая функция",
                "rows": [],
                "note": "Новая функция preview() вернула не dict.",
            }

        except Exception as e:
            return {
                "condition_id": cond.id,
                "fn": f"new:{cond.fn_id}",
                "title": cond.fn.name if cond.fn else "Новая функция",
                "rows": [],
                "note": f"Ошибка при выполнении новой preview логики: {e}",
            }

    # старая логика
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