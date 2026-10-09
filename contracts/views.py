# contracts/views.py
from datetime import datetime, date
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Min, Max
from django.http import HttpResponse, HttpResponseBadRequest

from .models import Conditions

from .models import Contracts
from contracts.reconciliation.service import (
    build_contract_reconciliation,
    get_contract_full_horizon_date,
    LOAN_ACCRUAL_FNS,

)
from django.db.models import Min, Max
from treasury.models import CfData, CfSplits
from .models import Conditions
from contracts.accruals.engine import preview_accruals

from django.db import connection
from pprint import pprint

from django.http import JsonResponse
from django.urls import reverse
from django.db.models import Q


import pandas as pd
import numpy as np


#####-----ДЛЯ КОЛОКОЛЬЧИКА - ЕСЛИ НЕ ЗАПОЛНЕЕНЫ СТАТЬИ У ДОГОВОРОВ-----#####
from django.http import JsonResponse
from django.db.models import Q
from .models import Contracts


def contracts_issues_status(request):
    qs = Contracts.objects.all()

    no_accrual_total = qs.filter(conditions__isnull=True).distinct().count()

    missing_bs_total = qs.filter(bs_id__isnull=True).count()
    missing_pl_total = qs.filter(pl_id__isnull=True).count()
    missing_subconto_pl_total = qs.filter(subconto_pl_id__isnull=True).count()

    missing_distribution_total = qs.filter(
        Q(bs_id__isnull=True) |
        Q(pl_id__isnull=True) |
        Q(subconto_pl_id__isnull=True)
    ).distinct().count()

    return JsonResponse({
        "ok": True,
        "no_accrual_fn": {
            "total": no_accrual_total,
            "admin_url": "/admin/contracts/contracts/?has_accrual_fn=no",
        },
        "missing_distribution": {
            "total": missing_distribution_total,
            "admin_url": "/admin/contracts/contracts/?missing_distribution=any",
        },
        "missing_bs": {
            "total": missing_bs_total,
            "admin_url": "/admin/contracts/contracts/?missing_distribution=bs",
        },
        "missing_pl": {
            "total": missing_pl_total,
            "admin_url": "/admin/contracts/contracts/?missing_distribution=pl",
        },
        "missing_subconto_pl": {
            "total": missing_subconto_pl_total,
            "admin_url": "/admin/contracts/contracts/?missing_distribution=subconto_pl",
        },
    })
#####-----СТАТУСЫ ПО ДОЛГАМ-----#####
def balance_status(balance: float) -> str:
    if balance > 2:
        return "Наш долг"
    if balance < -2:
        return "Переплата"
    return "Сальдо закрыто"


def balance_comment(balance: float) -> str:
    if balance > 2:
        return "Положительное сальдо на текущую дату означает задолженность нашей компании перед контрагентом."
    if balance < -2:
        return "Отрицательное сальдо на текущую дату означает переплату со стороны нашей компании."
    return "По состоянию на текущую дату задолженность отсутствует."


def balance_status_class(balance: float) -> str:
    if balance > 2:
        return "is-debt"
    if balance < -2:
        return "is-overpayment"
    return "is-closed"


def prepare_reconciliation_df(df, report_date, opening_balance=0.0):
    """
    df — все строки по договору за весь период
    report_date — дата, на которую считаем текущую ситуацию
    opening_balance — начальное сальдо, если нужно
    """

    opening_balance = float(opening_balance or 0)

    if df.empty:
        return {
            "rows": [],
            "total_accruals": 0.0,
            "total_payments": 0.0,
            "closing_balance": opening_balance,
            "current_accruals": 0.0,
            "current_payments": 0.0,
            "current_balance": opening_balance,
            "closing_balance_status": balance_status(opening_balance),
            "closing_balance_comment": balance_comment(opening_balance),
            "closing_balance_status_class": balance_status_class(opening_balance),
            "current_balance_status": balance_status(opening_balance),
            "current_balance_comment": balance_comment(opening_balance),
            "current_balance_status_class": balance_status_class(opening_balance),
        }

    df = df.copy()

    for col in ["accrual", "payment", "loan_issue", "loan_principal_return"]:
        if col not in df.columns:
            df[col] = 0.0
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    df["row_date"] = pd.to_datetime(df["row_date"], errors="coerce").dt.date
    df = df.sort_values(by=["row_date", "sort_order", "description"], kind="stable")

    # Баланс по всем строкам
    df["balance"] = opening_balance + (df["accrual"] - df["payment"]).cumsum()

    # Срез на текущую дату
    current_df = df[df["row_date"] <= report_date].copy()

    total_accruals = float(df["accrual"].sum())
    total_payments = float(df["payment"].sum())
    closing_balance = float(opening_balance + total_accruals - total_payments)

    current_accruals = float(current_df["accrual"].sum()) if not current_df.empty else 0.0
    current_payments = float(current_df["payment"].sum()) if not current_df.empty else 0.0
    current_balance = float(opening_balance + current_accruals - current_payments)

    return {
        "rows": df.to_dict(orient="records"),
        "total_accruals": total_accruals,
        "total_payments": total_payments,
        "closing_balance": closing_balance,
        "current_accruals": current_accruals,
        "current_payments": current_payments,
        "current_balance": current_balance,
        "closing_balance_status": balance_status(closing_balance),
        "closing_balance_comment": balance_comment(closing_balance),
        "closing_balance_status_class": balance_status_class(closing_balance),
        "current_balance_status": balance_status(current_balance),
        "current_balance_comment": balance_comment(current_balance),
        "current_balance_status_class": balance_status_class(current_balance),
    }

#####-------------------------------------#####

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


def get_sql():
    return """
    SELECT
        CASE
            WHEN dt = 0 THEN ROUND((cr - dt) / 100.0, 2)::numeric
            ELSE 0::numeric
        END AS accrual,

        0::numeric AS balance,
        
        COALESCE(contract_name, '') AS contract_name,

        CASE
            -- ОПЛАТА
            WHEN cr = 0 
                 AND COALESCE(acc_name, '') <> '' 
                 AND COALESCE(temp, description, '') <> ''
                THEN acc_name || E'\\n' || COALESCE(temp, description, '')

            WHEN cr = 0 
                 AND COALESCE(acc_name, '') <> ''
                THEN acc_name

            WHEN cr = 0
                THEN COALESCE(temp, description, '')

            -- НАЧИСЛЕНИЕ
                WHEN dt = 0 
                    AND COALESCE(acc_name, '') <> '' 
                    AND COALESCE(description, '') <> ''
                    THEN acc_name || E'\n' || description

                WHEN dt = 0 
                    AND COALESCE(acc_name, '') <> ''
                    THEN acc_name

                WHEN dt = 0
                    THEN COALESCE(description, '')

            ELSE ''
        END AS comment,

        CASE
            WHEN cr = 0
                 AND COALESCE(doc_numner, '') <> ''
                 AND COALESCE(doc_date, '') <> ''
                THEN 'Оплата по документу № ' || doc_numner || ' от ' || doc_date

            WHEN cr = 0
                 AND COALESCE(doc_numner, '') <> ''
                THEN 'Оплата по документу № ' || doc_numner

            WHEN cr = 0
                THEN 'Оплата'

            WHEN dt = 0
                THEN 'Начисление'

            ELSE 'Операция'
        END AS description,

        ''::text AS doc_label,

        0::numeric AS loan_issue,
        0::numeric AS loan_principal_return,

        CASE
            WHEN cr = 0 THEN ROUND((dt - cr) / 100.0, 2)::numeric
            ELSE 0::numeric
        END AS payment,

        NULL::date AS period_from,
        NULL::date AS period_to,

        date_from::date AS row_date,

        CASE
            WHEN dt = 0 THEN 'accrual'
            WHEN cr = 0 THEN 'payment'
            ELSE 'operation'
        END AS row_type,

        CASE
            WHEN dt = 0 THEN 'Начисление'
            WHEN cr = 0 THEN 'Оплата'
            ELSE 'Операция'
        END AS row_type_label,

        CASE
            WHEN dt = 0 THEN 1
            WHEN cr = 0 THEN 2
            ELSE 3
        END AS sort_order

    FROM gl.mv_accurals
    WHERE pid_id = %s
      -- AND date_from::date <= current_date
    ORDER BY date_from::date, sort_order, description
    """
    

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

    root_id = contract.pid_id or contract.id
    df = pd.read_sql(get_sql(), connection, params=[root_id])

    contract_name_from_mv = None
    if not df.empty and "contract_name" in df.columns:
        non_empty_names = df["contract_name"].dropna().astype(str).str.strip()
        non_empty_names = non_empty_names[non_empty_names != ""]
        if not non_empty_names.empty:
            contract_name_from_mv = non_empty_names.iloc[0]

    prepared = prepare_reconciliation_df(
        df=df,
        report_date=report_date,
        opening_balance=0.0,
    )

    has_loan = Conditions.objects.filter(
        contract=contract,
        accrual_fn__in=LOAN_ACCRUAL_FNS,
    ).exists()

    context = {
        "contract": contract,
        "date_from": date_from,
        "date_to": date_to,
        "report_date": report_date,
        "opening_balance": 0.0,

        "rows": prepared["rows"],
        "total_accruals": prepared["total_accruals"],
        "total_payments": prepared["total_payments"],
        "closing_balance": prepared["closing_balance"],
        "closing_balance_status": prepared["closing_balance_status"],
        "closing_balance_comment": prepared["closing_balance_comment"],
        "closing_balance_status_class": prepared["closing_balance_status_class"],

        "current_accruals": prepared["current_accruals"],
        "current_payments": prepared["current_payments"],
        "current_balance": prepared["current_balance"],
        "current_balance_status": prepared["current_balance_status"],
        "current_balance_comment": prepared["current_balance_comment"],
        "current_balance_status_class": prepared["current_balance_status_class"],

        "has_loan": has_loan,
        "contract_name_from_mv": contract_name_from_mv,

        "loan_issued_total": 0.0,
        "loan_principal_returned_total": 0.0,
        "loan_principal_outstanding": 0.0,
        "loan_interest_accrued_total": 0.0,
        "loan_interest_paid_total": 0.0,
        "loan_ndfl_withheld_total": 0.0,
        "loan_interest_outstanding": 0.0,
        "total_loan_issue": 0.0,
        "total_loan_principal_return": 0.0,
    }

    return TemplateResponse(request, "admin/contracts/reconciliation_print.html", context)




@staff_member_required
def export_loans_report(request):
    """Экспорт отчёта по договорам займа и кредитным договорам в Excel"""
    from datetime import datetime
    from django.http import HttpResponse, HttpResponseBadRequest
    
    # Получаем дату из GET параметра
    report_date = request.GET.get('report_date')
    
    if not report_date:
        return HttpResponseBadRequest("Не указана дата отчёта")
    
    try:
        # Используем ваш билдер
        from contracts.loans_report.builder import LoansReportGenerator
        
        generator = LoansReportGenerator()
        output = generator.generate(report_date)
        
        filename = f"Loans_Report_{report_date}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        response = HttpResponse(
            output.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return HttpResponseBadRequest(f"Ошибка: {str(e)}")