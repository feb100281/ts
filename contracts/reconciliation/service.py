# contracts/reconciliation/service.py
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from django.db.models import Max

from contracts.models import Conditions, Contracts
from contracts.accruals.service import preview_accruals
from treasury.models import CfData, CfSplits


def q2(x: Decimal | str | int | float | None) -> Decimal:
    return Decimal(str(x or "0")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _safe_date(value) -> date | None:
    if not value:
        return None

    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None

        for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%Y-%m-%d %H:%M:%S", "%d.%m.%Y %H:%M:%S"):
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                pass

    return None


def _payment_amount_from_cfdata(obj: CfData) -> Decimal:
    """
    Для MVP считаем оплатой положительный приход денег:
    если cr > 0 -> берем cr
    иначе если dt > 0 -> берем dt
    иначе 0

    Если у тебя в учете поступления арендаторов всегда сидят, например, только в cr,
    потом можно упростить до return q2(obj.cr).
    """
    cr = q2(obj.cr)
    dt = q2(obj.dt)

    if cr > 0:
        return cr
    if dt > 0:
        return dt
    return Decimal("0.00")


def _payment_amount_from_split(obj: CfSplits) -> Decimal:
    cr = q2(obj.cr)
    dt = q2(obj.dt)

    if cr > 0:
        return cr
    if dt > 0:
        return dt
    return Decimal("0.00")

def get_contract_full_horizon_date(contract: Contracts) -> date:
    cond_agg = Conditions.objects.filter(contract=contract).aggregate(
        max_finish=Max("date_finish"),
        max_start=Max("date_start"),
    )

    cf_agg = CfData.objects.filter(contract=contract).aggregate(
        max_date=Max("date"),
    )

    split_agg = CfSplits.objects.filter(contract=contract).aggregate(
        max_date=Max("transaction__date"),
    )

    candidate_dates = [
        cond_agg.get("max_finish"),
        cond_agg.get("max_start"),
        cf_agg.get("max_date"),
        split_agg.get("max_date"),
        date.today(),
    ]
    candidate_dates = [d for d in candidate_dates if d]

    return max(candidate_dates) if candidate_dates else date.today()


def _build_accrual_rows_for_condition(cond: Conditions, date_from: date, date_to: date) -> list[dict[str, Any]]:
    """
    Используем твою существующую логику preview_accruals.
    ВАЖНО:
    preview_accruals считает период по самому condition:
    - от cond.date_start / cond.date_finish
    - либо anchor month

    Поэтому для акта сверки берем только те строки, которые попадают в период акта.
    """
    result = preview_accruals(cond, anchor_date=date_from)
    rows = result.get("rows", []) or []
    title = result.get("title") or cond.accrual_fn or "Начисление"

    output = []

    for r in rows:
        row_from = _safe_date(r.get("period_from"))
        row_to = _safe_date(r.get("period_to"))

        if not row_from or not row_to:
            continue

        # оставляем только строки, пересекающиеся с периодом акта
        if row_to < date_from or row_from > date_to:
            continue

        amount = q2(r.get("amount_gross") or r.get("amount") or "0")

        output.append({
            "row_date": row_from,
            "row_type": "accrual",
            "row_type_label": "Начисление",
            "doc_label": f"Условие #{cond.id}",
            "description": f"{title}",
            "period_from": row_from,
            "period_to": row_to,
            "accrual": amount,
            "payment": Decimal("0.00"),
            "sort_order": 1,
        })

    return output


def get_contract_accrual_rows(contract: Contracts, date_from: date, date_to: date) -> list[dict[str, Any]]:
    conditions = (
        Conditions.objects
        .filter(contract=contract)
        .order_by("date_start", "id")
    )

    rows: list[dict[str, Any]] = []

    for cond in conditions:
        # грубая отсечка по пересечению периодов условия и периода акта
        cond_start = cond.date_start or date_from
        cond_finish = cond.date_finish or date_to

        if cond_finish < date_from or cond_start > date_to:
            continue

        rows.extend(_build_accrual_rows_for_condition(cond, date_from, date_to))

    return rows


def get_contract_payment_rows(contract: Contracts, date_from: date, date_to: date) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    # 1. Сначала берем сплиты - это приоритетный источник аналитики по договору
    split_qs = (
        CfSplits.objects
        .select_related("transaction", "contract", "cfitem")
        .filter(
            contract=contract,
            transaction__date__gte=date_from,
            transaction__date__lte=date_to,
        )
        .order_by("transaction__date", "id")
    )

    used_transaction_ids = set()

    for s in split_qs:
        amount = _payment_amount_from_split(s)
        if amount <= 0:
            continue

        used_transaction_ids.add(s.transaction_id)

        doc_number = s.transaction.doc_numner or "б/н"
        doc_date = s.transaction.doc_date or ""
        temp = (s.temp or s.transaction.temp or "").strip()

        rows.append({
            "row_date": s.transaction.date,
            "row_type": "payment",
            "row_type_label": "Оплата",
            "doc_label": f"Выписка / сплит #{s.transaction_id}",
            "description": f"Оплата по док. {doc_number} {('от ' + doc_date) if doc_date else ''}".strip(),
            "period_from": None,
            "period_to": None,
            "accrual": Decimal("0.00"),
            "payment": amount,
            "sort_order": 2,
            "comment": temp,
        })

    # 2. Берем прямые CfData по договору, но исключаем те, что уже разложены сплитами
    cf_qs = (
        CfData.objects
        .select_related("contract", "cfitem")
        .filter(
            contract=contract,
            date__gte=date_from,
            date__lte=date_to,
        )
        .exclude(id__in=used_transaction_ids)
        .order_by("date", "id")
    )

    for p in cf_qs:
        amount = _payment_amount_from_cfdata(p)
        if amount <= 0:
            continue

        doc_number = p.doc_numner or "б/н"
        doc_date = p.doc_date or ""
        temp = (p.temp or "").strip()

        rows.append({
            "row_date": p.date,
            "row_type": "payment",
            "row_type_label": "Оплата",
            "doc_label": f"Выписка #{p.id}",
            "description": f"Оплата по док. {doc_number} {('от ' + doc_date) if doc_date else ''}".strip(),
            "period_from": None,
            "period_to": None,
            "accrual": Decimal("0.00"),
            "payment": amount,
            "sort_order": 2,
            "comment": temp,
        })

    return rows


def _get_accrual_total_before(contract: Contracts, date_from: date) -> Decimal:
    """
    MVP-вариант:
    считаем начисления по всем условиям, оставляя строки строго ДО date_from.
    """
    if not contract:
        return Decimal("0.00")

    conditions = (
        Conditions.objects
        .filter(contract=contract)
        .order_by("date_start", "id")
    )

    total = Decimal("0.00")

    for cond in conditions:
        result = preview_accruals(cond, anchor_date=date_from)
        rows = result.get("rows", []) or []

        for r in rows:
            row_from = _safe_date(r.get("period_from"))
            if not row_from:
                continue

            if row_from < date_from:
                total += q2(r.get("amount_gross") or r.get("amount") or "0")

    return q2(total)


def _get_payment_total_before(contract: Contracts, date_from: date) -> Decimal:
    used_transaction_ids = set()
    total = Decimal("0.00")

    split_qs = (
        CfSplits.objects
        .select_related("transaction")
        .filter(
            contract=contract,
            transaction__date__lt=date_from,
        )
    )

    for s in split_qs:
        amount = _payment_amount_from_split(s)
        if amount > 0:
            total += amount
            used_transaction_ids.add(s.transaction_id)

    cf_qs = (
        CfData.objects
        .filter(
            contract=contract,
            date__lt=date_from,
        )
        .exclude(id__in=used_transaction_ids)
    )

    for p in cf_qs:
        amount = _payment_amount_from_cfdata(p)
        if amount > 0:
            total += amount

    return q2(total)


def get_balance_status(balance: Decimal) -> str:
    balance = q2(balance)

    if balance > 0:
        return "Наш долг"
    if balance < 0:
        return "Переплата"
    return "Сальдо закрыто"


def get_balance_comment(balance: Decimal) -> str:
    balance = q2(balance)

    if balance > 0:
        return "Положительное сальдо на текущую дату означает задолженность нашей компании перед контрагентом."
    if balance < 0:
        return "Отрицательное сальдо на текущую дату означает переплату со стороны нашей компании."
    return "По состоянию на текущую дату задолженность отсутствует."


def get_balance_status_class(balance: Decimal) -> str:
    balance = q2(balance)

    if balance > 0:
        return "is-debt"
    if balance < 0:
        return "is-overpayment"
    return "is-closed"



def build_contract_reconciliation(
    contract: Contracts,
    date_from: date,
    date_to: date,
    report_date: date | None = None,
) -> dict[str, Any]:
    """
    date_to     -> до какой даты строим весь реестр (полный горизонт)
    report_date -> на какую дату отдельно считаем текущее сальдо
    """
    report_date = report_date or date.today()

    accrual_rows = get_contract_accrual_rows(contract, date_from, date_to)
    payment_rows = get_contract_payment_rows(contract, date_from, date_to)

    opening_accruals = _get_accrual_total_before(contract, date_from)
    opening_payments = _get_payment_total_before(contract, date_from)
    opening_balance = q2(opening_accruals - opening_payments)

    rows = accrual_rows + payment_rows
    rows.sort(key=lambda x: (x["row_date"], x["sort_order"], x["description"]))

    running_balance = opening_balance
    current_balance = opening_balance

    total_accruals = Decimal("0.00")
    total_payments = Decimal("0.00")

    current_accruals = Decimal("0.00")
    current_payments = Decimal("0.00")

    prepared_rows = []

    for row in rows:
        accrual = q2(row.get("accrual"))
        payment = q2(row.get("payment"))

        total_accruals += accrual
        total_payments += payment
        running_balance = q2(running_balance + accrual - payment)

        prepared = dict(row)
        prepared["accrual"] = accrual
        prepared["payment"] = payment
        prepared["balance"] = running_balance

        # Отдельно считаем состояние на report_date
        if row["row_date"] <= report_date:
            current_accruals += accrual
            current_payments += payment
            current_balance = q2(current_balance + accrual - payment)

        prepared_rows.append(prepared)

    closing_balance = q2(opening_balance + total_accruals - total_payments)

    return {
        "contract": contract,
        "date_from": date_from,
        "date_to": date_to,              # полный горизонт
        "report_date": report_date,      # текущая дата / дата состояния
        "opening_balance": q2(opening_balance),

        # Итоги за весь горизонт
        "total_accruals": q2(total_accruals),
        "total_payments": q2(total_payments),
        "closing_balance": q2(closing_balance),
        "closing_balance_status": get_balance_status(closing_balance),
        "closing_balance_comment": get_balance_comment(closing_balance),
        "closing_balance_status_class": get_balance_status_class(closing_balance),

        # Итоги на текущую дату
        "current_accruals": q2(current_accruals),
        "current_payments": q2(current_payments),
        "current_balance": q2(current_balance),
        "current_balance_status": get_balance_status(current_balance),
        "current_balance_comment": get_balance_comment(current_balance),
        "current_balance_status_class": get_balance_status_class(current_balance),

        "rows": prepared_rows,
    }