from django.utils.module_loading import import_string


def load_condition_module(condition):
    if not condition.fn_id:
        return None

    if not condition.fn or not condition.fn.python_path:
        raise ValueError("У условия не заполнен python_path в AccuralFn")

    return import_string(condition.fn.python_path)


def build_condition_args(condition):
    contract = condition.contract

    return {
        "contract_id": contract.id,
        "condition_id": condition.id,
        "company_id": getattr(contract.owner, "id", None),

        "date_start": condition.date_start,
        "date_finish": condition.date_finish,

        "amount": condition.amount,
        "currency": contract.currency,

        "vat_mode": condition.vat_mode,
        "vat_json": condition.vat_json or {},
        "params_json": condition.param_json or {},

        "acc_bs_id": condition.acc_bs_id,
        "subconto_bs_id": condition.subconto_bs_id,
        "acc_pl_id": condition.acc_pl_id,
        "subconto_pl_id": condition.subconto_pl_id,

        # если у тебя ST берется из договора:
        "acc_st_id": contract.st_id,

        "fn_id": condition.fn_id,
    }