# contracts/views.py
from datetime import datetime, date
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Min, Max

from .models import Conditions

from .models import Contracts
from contracts.reconciliation.service import build_contract_reconciliation,  get_contract_full_horizon_date, LOAN_ACCRUAL_FNS
from django.db.models import Min, Max
from treasury.models import CfData, CfSplits
from .models import Conditions
from contracts.accruals.engine import preview_accruals

from django.db import connection
from pprint import pprint

import pandas as pd
import numpy as np

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

# Нужно потом в SQL функцию перетащий; Это порнография какая то получается
# 1 запрос и все
# def get_sql(pid):
#     return f"""
#     SELECT
#     case when cr=0 then round((dt-cr)/100,2)::numeric else 0 end as accrual,
#     0 as balance,
#     description as comment,
#     'ХЗ' as description,
#     'Выписки но блин не хочу' as doc_label,
#     0 as loan_issue,
#     0 as loan_principal_return,
#     case when dt = 0 then round((cr-dt)/100,2)::numeric else 0 end as payment,
#     null as period_from,
#     null as period_to,
#     date_from as row_date,
#     case when cr = 0 then 'accrual' else 'payment' end as row_type,
#     case when cr = 0 then 'Начисление' else 'Оплата' end as row_type_label,
#     case when cr = 0 then 1 else 2 end as sort_order
#     from gl.mv_accurals
#     where pid_id = {pid} and date_from::date <= current_date
#     order by date_from
#     """



def get_sql():
    return """
    SELECT
        CASE
            WHEN cr = 0 THEN ROUND((dt - cr) / 100.0, 2)::numeric
            ELSE 0::numeric
        END AS accrual,

        0::numeric AS balance,

        COALESCE(temp, description, '') AS comment,

        CASE
            WHEN dt = 0
                 AND COALESCE(doc_numner, '') <> ''
                 AND doc_date IS NOT NULL
                THEN 'Оплата по документу № ' || doc_numner || ' от ' || TO_CHAR(doc_date, 'DD.MM.YYYY')
            WHEN dt = 0
                 AND COALESCE(doc_numner, '') <> ''
                THEN 'Оплата по документу № ' || doc_numner
            WHEN cr = 0
                THEN COALESCE(description, 'Начисление')
            ELSE COALESCE(description, 'Операция')
        END AS description,

        CASE
            WHEN dt = 0 AND COALESCE(cp_bs_name, '') <> ''
                THEN 'Выписка — ' || cp_bs_name
            WHEN cr = 0
                THEN 'Начисление'
            ELSE 'Документ'
        END AS doc_label,

        0::numeric AS loan_issue,
        0::numeric AS loan_principal_return,

        CASE
            WHEN dt = 0 THEN ROUND((cr - dt) / 100.0, 2)::numeric
            ELSE 0::numeric
        END AS payment,

        NULL::date AS period_from,
        NULL::date AS period_to,

        date_from::date AS row_date,

        CASE
            WHEN cr = 0 THEN 'accrual'
            ELSE 'payment'
        END AS row_type,

        CASE
            WHEN cr = 0 THEN 'Начисление'
            ELSE 'Оплата'
        END AS row_type_label,

        CASE
            WHEN cr = 0 THEN 1
            ELSE 2
        END AS sort_order

    FROM gl.mv_accurals
    WHERE pid_id = %s
      AND date_from::date <= current_date
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

    result = build_contract_reconciliation(
        contract=contract,
        date_from=date_from,
        date_to=date_to,
        report_date=report_date,
    )
    
    # ------------------------------------------
    # ### ВСЕ ПРЕВЬЮ В ТРИ СТРОЧКИ!!! ЗАКОМЕНТЬ ПОТОМ ЕСЛИ ЧТО ЭТО ОТ ПАШИ
    # #ВАЖНО СЧИТАЕМ ПО PID
    root_id = contract.pid_id or contract.id
    # df = pd.read_sql(get_sql(root_id),connection)
    df = pd.read_sql(get_sql(), connection, params=[root_id])
    
    #Делаем сверку    
    # rows_new = {
    # "rows": df.to_dict(orient="records")
    # }    
    # #ХОД КОНЕМ ЧТО БЫ НЕ КОПАТЬСЯ В 2 тыс срок services
    # result["rows"] = rows_new["rows"]
    # result["total_accruals"] = df['accrual'].sum()
    # result["total_payments"] = df['payment'].sum()    
    # result["current_accruals"] = df['accrual'].sum()  ### Не увенер просто так сделал
    # result["current_balance"] = df['accrual'].sum() - df['payment'].sum() 
    # result["closing_balance"] = df['accrual'].sum() - df['payment'].sum() 
    # ВСЕ ОСТАЛЬНОЕ МОЖНО ЧЕРЕЗ DF найти и передать в шаблон.
    # #ДЖАНГО НЕ ЮЗАЕМ В РАСЧЕТАХ
    
    if df.empty:
        df = pd.DataFrame(columns=[
            "accrual", "balance", "comment", "description", "doc_label",
            "loan_issue", "loan_principal_return", "payment",
            "period_from", "period_to", "row_date",
            "row_type", "row_type_label", "sort_order"
        ])

    for col in ["accrual", "payment", "loan_issue", "loan_principal_return"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    df["balance"] = (df["accrual"] - df["payment"]).cumsum()

    result["rows"] = df.to_dict(orient="records")
    result["total_accruals"] = df["accrual"].sum()
    result["total_payments"] = df["payment"].sum()
    result["current_accruals"] = df["accrual"].sum()
    result["current_payments"] = df["payment"].sum()
    result["current_balance"] = df["accrual"].sum() - df["payment"].sum()
    result["closing_balance"] = df["accrual"].sum() - df["payment"].sum()
    # ------------------------------------------
    
    
    has_loan = Conditions.objects.filter(
            contract=contract,
            accrual_fn__in=LOAN_ACCRUAL_FNS,
        ).exists()
    
    context = {
        **result,
        "contract": contract,
        "result": result,
        "has_loan": has_loan,
    }
    
    

    return TemplateResponse(request, "admin/contracts/reconciliation_print.html", context)