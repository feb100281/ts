# contracts/views.py
from datetime import datetime, date
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Min, Max

from .models import Conditions
from contracts.accruals.service import preview_accruals

from .models import Contracts
from contracts.reconciliation.service import build_contract_reconciliation,  get_contract_full_horizon_date
from django.db.models import Min, Max
from treasury.models import CfData, CfSplits
from .models import Conditions


@staff_member_required
def condition_accruals_preview(request, condition_id: int):
    condition = get_object_or_404(
        Conditions.objects.select_related("contract", "contract__cp", "accounting_method"),
        pk=condition_id
    )
    contract = condition.contract

    result = preview_accruals(condition, anchor_date=date.today())

    rows = result.get("rows", []) or []

    context = {
        "condition": condition,
        "contract": contract,
        "result": result,
        "rows": rows,
        "total": result.get("total"),
        "total_net": result.get("total_net"),
        "total_vat": result.get("total_vat"),
        "total_gross": result.get("total_gross"),
        "vat_rate": result.get("vat_rate"),
        "vat_mode": result.get("vat_mode"),
        "period_from": (result.get("period") or {}).get("from"),
        "period_to": (result.get("period") or {}).get("to"),
        "fn_title": result.get("title"),
    }
    return TemplateResponse(request, "admin/contracts/accruals_print.html", context)


@staff_member_required
def contract_reconciliation_preview(request, contract_id: int):
    contract = get_object_or_404(
        Contracts.objects.select_related("cp", "title"),
        pk=contract_id
    )

    date_from_str = request.GET.get("date_from")
    date_to_str = request.GET.get("date_to")

    report_date = date.today()

    if date_from_str:
        date_from = datetime.strptime(date_from_str, "%Y-%m-%d").date()
    else:
        cond_agg = Conditions.objects.filter(contract=contract).aggregate(
            min_start=Min("date_start"),
        )

        cf_agg = CfData.objects.filter(contract=contract).aggregate(
            min_date=Min("date"),
        )

        split_agg = CfSplits.objects.filter(contract=contract).aggregate(
            min_date=Min("transaction__date"),
        )

        candidate_starts = [
            cond_agg.get("min_start"),
            cf_agg.get("min_date"),
            split_agg.get("min_date"),
            contract.date,
        ]
        candidate_starts = [d for d in candidate_starts if d]

        date_from = min(candidate_starts) if candidate_starts else (contract.date or date.today())

    if date_to_str:
        date_to = datetime.strptime(date_to_str, "%Y-%m-%d").date()
    else:
        date_to = get_contract_full_horizon_date(contract)

    if date_to < date_from:
        date_to = date_from

    result = build_contract_reconciliation(
        contract=contract,
        date_from=date_from,
        date_to=date_to,
        report_date=report_date,
    )

    context = {
        "contract": contract,
        "result": result,
        "rows": result["rows"],

        "date_from": result["date_from"],
        "date_to": result["date_to"],
        "report_date": result["report_date"],

        "opening_balance": result["opening_balance"],

        # весь горизонт
        "total_accruals": result["total_accruals"],
        "total_payments": result["total_payments"],
        "closing_balance": result["closing_balance"],
        "closing_balance_status": result["closing_balance_status"],
        "closing_balance_comment": result["closing_balance_comment"],
        "closing_balance_status_class": result["closing_balance_status_class"],

        # текущее состояние
        "current_accruals": result["current_accruals"],
        "current_payments": result["current_payments"],
        "current_balance": result["current_balance"],
        "current_balance_status": result["current_balance_status"],
        "current_balance_comment": result["current_balance_comment"],
        "current_balance_status_class": result["current_balance_status_class"],
    }

    return TemplateResponse(request, "admin/contracts/reconciliation_print.html", context)