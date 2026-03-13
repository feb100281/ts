# # contracts/reconciliation/service.py
# from __future__ import annotations

# from datetime import date, datetime
# from decimal import Decimal, ROUND_HALF_UP
# from typing import Any

# from django.db.models import Max

# from contracts.models import Conditions, Contracts
# from contracts.accruals.service import preview_accruals
# from treasury.models import CfData, CfSplits
# from grossbook.models import Manual


# def q2(x: Decimal | str | int | float | None) -> Decimal:
#     return Decimal(str(x or "0")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


# def _safe_date(value) -> date | None:
#     if not value:
#         return None

#     if isinstance(value, datetime):
#         return value.date()

#     if isinstance(value, date):
#         return value

#     if isinstance(value, str):
#         value = value.strip()
#         if not value:
#             return None

#         for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%Y-%m-%d %H:%M:%S", "%d.%m.%Y %H:%M:%S"):
#             try:
#                 return datetime.strptime(value, fmt).date()
#             except ValueError:
#                 pass

#     return None


# def _payment_amount_from_cfdata(obj: CfData) -> Decimal:
#     """
#     Для MVP считаем оплатой положительный приход денег:
#     если cr > 0 -> берем cr
#     иначе если dt > 0 -> берем dt
#     иначе 0

#     Если у тебя в учете поступления арендаторов всегда сидят, например, только в cr,
#     потом можно упростить до return q2(obj.cr).
#     """
#     cr = q2(obj.cr)
#     dt = q2(obj.dt)

#     if cr > 0:
#         return cr
#     if dt > 0:
#         return dt
#     return Decimal("0.00")


# def _payment_amount_from_split(obj: CfSplits) -> Decimal:
#     cr = q2(obj.cr)
#     dt = q2(obj.dt)

#     if cr > 0:
#         return cr
#     if dt > 0:
#         return dt
#     return Decimal("0.00")


# def _cfitem_code(cfitem) -> str:
#     if not cfitem:
#         return ""
#     return str(cfitem.code or "").strip()


# def _is_deposit_condition(cond: Conditions) -> bool:
#     return (cond.accrual_fn or "") == "deposit_by_bank_statement"


# def _is_deposit_principal_flow(flow_type: str) -> bool:
#     return flow_type in {"placement", "principal_return"}


# def _is_deposit_principal_cf_code(code: str) -> bool:
#     return code in {"322100", "314100"}


# def _is_deposit_interest_cf_code(code: str) -> bool:
#     return code == "313100"


# def get_contract_full_horizon_date(contract: Contracts) -> date:
#     cond_agg = Conditions.objects.filter(contract=contract).aggregate(
#         max_finish=Max("date_finish"),
#         max_start=Max("date_start"),
#     )

#     cf_agg = CfData.objects.filter(contract=contract).aggregate(
#         max_date=Max("date"),
#     )

#     split_agg = CfSplits.objects.filter(contract=contract).aggregate(
#         max_date=Max("transaction__date"),
#     )
    
#     manual_agg = Manual.objects.filter(contract=contract).aggregate(
#         max_date=Max("date"),
#     )

#     candidate_dates = [
#         cond_agg.get("max_finish"),
#         cond_agg.get("max_start"),
#         cf_agg.get("max_date"),
#         split_agg.get("max_date"),
#         manual_agg.get("max_date"),
#         date.today(),
#     ]
#     candidate_dates = [d for d in candidate_dates if d]

#     return max(candidate_dates) if candidate_dates else date.today()

# def _manual_adjustment_amount(obj: Manual) -> Decimal:
#     cr = q2(obj.cr)
#     dt = q2(obj.dt)

#     if cr > 0:
#         return cr
#     if dt > 0:
#         return dt
#     return Decimal("0.00")

# def _build_accrual_rows_for_condition(cond: Conditions, date_from: date, date_to: date) -> list[dict[str, Any]]:
#     """
#     Используем твою существующую логику preview_accruals.
#     Для deposit_by_bank_statement в акт сверки берем только проценты,
#     а размещение и возврат тела депозита не включаем.
#     """
#     result = preview_accruals(cond, anchor_date=date_from)
#     rows = result.get("rows", []) or []
#     title = result.get("title") or cond.accrual_fn or "Начисление"

#     output = []

#     for r in rows:
#         row_date = _safe_date(r.get("accrual_date")) or _safe_date(r.get("period_from"))
#         row_from = _safe_date(r.get("period_from")) or row_date
#         row_to = _safe_date(r.get("period_to")) or row_date
#         flow_type = (r.get("flow_type") or "").strip()

#         if not row_date or not row_from or not row_to:
#             continue

#         # Для депозитов в акт сверки берем только проценты
#         if _is_deposit_condition(cond) and _is_deposit_principal_flow(flow_type):
#             continue

#         # оставляем только строки, пересекающиеся с периодом акта
#         if row_to < date_from or row_from > date_to:
#             continue

#         amount = q2(r.get("amount_gross") or r.get("amount") or "0")

#         output.append({
#             "row_date": row_date,
#             "row_type": "accrual",
#             "row_type_label": "Начисление",
#             "doc_label": f"Условие #{cond.id}",
#             "description": f"{title}",
#             "period_from": row_from,
#             "period_to": row_to,
#             "accrual": amount,
#             "payment": Decimal("0.00"),
#             "sort_order": 1,
#             "comment": (r.get("comment") or "").strip(),
#         })
#     return output


# def get_contract_accrual_rows(contract: Contracts, date_from: date, date_to: date) -> list[dict[str, Any]]:
#     conditions = (
#         Conditions.objects
#         .filter(contract=contract)
#         .order_by("date_start", "id")
#     )

#     rows: list[dict[str, Any]] = []

#     for cond in conditions:
#         # грубая отсечка по пересечению периодов условия и периода акта
#         cond_start = cond.date_start or date_from
#         cond_finish = cond.date_finish or date_to

#         if cond_finish < date_from or cond_start > date_to:
#             continue

#         rows.extend(_build_accrual_rows_for_condition(cond, date_from, date_to))

#     return rows


# def get_contract_payment_rows(contract: Contracts, date_from: date, date_to: date) -> list[dict[str, Any]]:
#     rows: list[dict[str, Any]] = []

#     # 1. Сначала берем сплиты - это приоритетный источник аналитики по договору
#     split_qs = (
#         CfSplits.objects
#         .select_related("transaction", "contract", "cfitem")
#         .filter(
#             contract=contract,
#             transaction__date__gte=date_from,
#             transaction__date__lte=date_to,
#         )
#         .order_by("transaction__date", "id")
#     )

#     used_transaction_ids = set()

#     for s in split_qs:
#         amount = _payment_amount_from_split(s)
#         if amount <= 0:
#             continue

#         code = _cfitem_code(s.cfitem)

#         if _is_deposit_principal_cf_code(code):
#             continue

#         used_transaction_ids.add(s.transaction_id)

#         doc_number = s.transaction.doc_numner or "б/н"
#         doc_date = s.transaction.doc_date or ""
#         temp = (s.temp or s.transaction.temp or "").strip()

#         rows.append({
#             "row_date": s.transaction.date,
#             "row_type": "payment",
#             "row_type_label": "Оплата",
#             "doc_label": f"Выписка / сплит #{s.transaction_id}",
#             "description": f"Оплата по док. {doc_number} {('от ' + doc_date) if doc_date else ''}".strip(),
#             "period_from": None,
#             "period_to": None,
#             "accrual": Decimal("0.00"),
#             "payment": amount,
#             "sort_order": 2,
#             "comment": temp,
#         })

#     # 2. Берем прямые CfData по договору, но исключаем те, что уже разложены сплитами
#     cf_qs = (
#         CfData.objects
#         .select_related("contract", "cfitem")
#         .filter(
#             contract=contract,
#             date__gte=date_from,
#             date__lte=date_to,
#         )
#         .exclude(id__in=used_transaction_ids)
#         .order_by("date", "id")
#     )

#     for p in cf_qs:
#         amount = _payment_amount_from_cfdata(p)
#         if amount <= 0:
#             continue

#         code = _cfitem_code(p.cfitem)

#         if _is_deposit_principal_cf_code(code):
#             continue

#         doc_number = p.doc_numner or "б/н"
#         doc_date = p.doc_date or ""
#         temp = (p.temp or "").strip()

#         rows.append({
#             "row_date": p.date,
#             "row_type": "payment",
#             "row_type_label": "Оплата",
#             "doc_label": f"Выписка #{p.id}",
#             "description": f"Оплата по док. {doc_number} {('от ' + doc_date) if doc_date else ''}".strip(),
#             "period_from": None,
#             "period_to": None,
#             "accrual": Decimal("0.00"),
#             "payment": amount,
#             "sort_order": 2,
#             "comment": temp,
#         })

#     # 3. Добавляем ручные проводки
#     manual_qs = (
#         Manual.objects
#         .select_related("contract", "cfitem")
#         .filter(
#             contract=contract,
#             date__gte=date_from,
#             date__lte=date_to,
#         )
#         .order_by("date", "id")
#     )

#     for m in manual_qs:
#         amount = _manual_adjustment_amount(m)
#         if amount <= 0:
#             continue

#         code = _cfitem_code(m.cfitem)

#         if _is_deposit_principal_cf_code(code):
#             continue

#         temp = (m.temp or "").strip()

#         rows.append({
#             "row_date": m.date,
#             "row_type": "manual_adjustment",
#             "row_type_label": "Ручная корректировка",
#             "doc_label": f"Ручная корректировка #{m.id}",
#            "description": "Ручная корректировка",
#             "period_from": None,
#             "period_to": None,
#             "accrual": Decimal("0.00"),
#             "payment": amount,
#             "sort_order": 3,
#             "comment": temp,
#         })

#     return rows






# def _get_accrual_total_before(contract: Contracts, date_from: date) -> Decimal:
#     """
#     MVP-вариант:
#     считаем начисления по всем условиям, оставляя строки строго ДО date_from.
#     Для deposit_by_bank_statement учитываем только проценты.
#     """
#     if not contract:
#         return Decimal("0.00")

#     conditions = (
#         Conditions.objects
#         .filter(contract=contract)
#         .order_by("date_start", "id")
#     )

#     total = Decimal("0.00")

#     for cond in conditions:
#         result = preview_accruals(cond, anchor_date=date_from)
#         rows = result.get("rows", []) or []

#         for r in rows:
#             row_date = _safe_date(r.get("accrual_date")) or _safe_date(r.get("period_from"))
#             flow_type = (r.get("flow_type") or "").strip()

#             if not row_date:
#                 continue

#             if _is_deposit_condition(cond) and _is_deposit_principal_flow(flow_type):
#                 continue

#             if row_date < date_from:
#                 total += q2(r.get("amount_gross") or r.get("amount") or "0")

#     return q2(total)



# def _get_payment_total_before(contract: Contracts, date_from: date) -> Decimal:
#     used_transaction_ids = set()
#     total = Decimal("0.00")

#     split_qs = (
#         CfSplits.objects
#         .select_related("transaction", "cfitem")
#         .filter(
#             contract=contract,
#             transaction__date__lt=date_from,
#         )
#     )

#     for s in split_qs:
#         amount = _payment_amount_from_split(s)
#         if amount <= 0:
#             continue

#         code = _cfitem_code(s.cfitem)

#         if _is_deposit_principal_cf_code(code):
#             continue

#         total += amount
#         used_transaction_ids.add(s.transaction_id)

#     cf_qs = (
#         CfData.objects
#         .select_related("cfitem")
#         .filter(
#             contract=contract,
#             date__lt=date_from,
#         )
#         .exclude(id__in=used_transaction_ids)
#     )

#     for p in cf_qs:
#         amount = _payment_amount_from_cfdata(p)
#         if amount <= 0:
#             continue

#         code = _cfitem_code(p.cfitem)

#         if _is_deposit_principal_cf_code(code):
#             continue

#         total += amount

#     manual_qs = (
#         Manual.objects
#         .select_related("cfitem")
#         .filter(
#             contract=contract,
#             date__lt=date_from,
#         )
#     )

#     for m in manual_qs:
#         amount = _manual_adjustment_amount(m)
#         if amount <= 0:
#             continue

#         code = _cfitem_code(m.cfitem)

#         if _is_deposit_principal_cf_code(code):
#             continue

#         total += amount

#     return q2(total)


# def get_balance_status(balance: Decimal) -> str:
#     balance = q2(balance)

#     if balance > 0:
#         return "Наш долг"
#     if balance < 0:
#         return "Переплата"
#     return "Сальдо закрыто"


# def get_balance_comment(balance: Decimal) -> str:
#     balance = q2(balance)

#     if balance > 0:
#         return "Положительное сальдо на текущую дату означает задолженность нашей компании перед контрагентом."
#     if balance < 0:
#         return "Отрицательное сальдо на текущую дату означает переплату со стороны нашей компании."
#     return "По состоянию на текущую дату задолженность отсутствует."


# def get_balance_status_class(balance: Decimal) -> str:
#     balance = q2(balance)

#     if balance > 0:
#         return "is-debt"
#     if balance < 0:
#         return "is-overpayment"
#     return "is-closed"



# def build_contract_reconciliation(
#     contract: Contracts,
#     date_from: date,
#     date_to: date,
#     report_date: date | None = None,
# ) -> dict[str, Any]:
#     """
#     date_to     -> до какой даты строим весь реестр (полный горизонт)
#     report_date -> на какую дату отдельно считаем текущее сальдо
#     """
#     report_date = report_date or date.today()

#     accrual_rows = get_contract_accrual_rows(contract, date_from, date_to)
#     payment_rows = get_contract_payment_rows(contract, date_from, date_to)

#     opening_accruals = _get_accrual_total_before(contract, date_from)
#     opening_payments = _get_payment_total_before(contract, date_from)
#     opening_balance = q2(opening_accruals - opening_payments)

#     rows = accrual_rows + payment_rows
#     rows.sort(key=lambda x: (x["row_date"], x["sort_order"], x["description"]))

#     running_balance = opening_balance
#     current_balance = opening_balance

#     total_accruals = Decimal("0.00")
#     total_payments = Decimal("0.00")

#     current_accruals = Decimal("0.00")
#     current_payments = Decimal("0.00")

#     prepared_rows = []

#     for row in rows:
#         accrual = q2(row.get("accrual"))
#         payment = q2(row.get("payment"))

#         total_accruals += accrual
#         total_payments += payment
#         running_balance = q2(running_balance + accrual - payment)

#         prepared = dict(row)
#         prepared["accrual"] = accrual
#         prepared["payment"] = payment
#         prepared["balance"] = running_balance

#         # Отдельно считаем состояние на report_date
#         if row["row_date"] <= report_date:
#             current_accruals += accrual
#             current_payments += payment
#             current_balance = q2(current_balance + accrual - payment)

#         prepared_rows.append(prepared)

#     closing_balance = q2(opening_balance + total_accruals - total_payments)

#     return {
#         "contract": contract,
#         "date_from": date_from,
#         "date_to": date_to,              # полный горизонт
#         "report_date": report_date,      # текущая дата / дата состояния
#         "opening_balance": q2(opening_balance),

#         # Итоги за весь горизонт
#         "total_accruals": q2(total_accruals),
#         "total_payments": q2(total_payments),
#         "closing_balance": q2(closing_balance),
#         "closing_balance_status": get_balance_status(closing_balance),
#         "closing_balance_comment": get_balance_comment(closing_balance),
#         "closing_balance_status_class": get_balance_status_class(closing_balance),

#         # Итоги на текущую дату
#         "current_accruals": q2(current_accruals),
#         "current_payments": q2(current_payments),
#         "current_balance": q2(current_balance),
#         "current_balance_status": get_balance_status(current_balance),
#         "current_balance_comment": get_balance_comment(current_balance),
#         "current_balance_status_class": get_balance_status_class(current_balance),

#         "rows": prepared_rows,
#     }





# from __future__ import annotations

# from datetime import date, datetime, timedelta
# from decimal import Decimal, ROUND_HALF_UP
# from typing import Any

# from django.db.models import Max

# from contracts.models import Conditions, Contracts
# from contracts.accruals.service import preview_accruals
# from treasury.models import CfData, CfSplits
# from grossbook.models import Manual
# from collections import defaultdict


# def q2(x: Decimal | str | int | float | None) -> Decimal:
#     return Decimal(str(x or "0")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


# def _safe_date(value) -> date | None:
#     if not value:
#         return None

#     if isinstance(value, datetime):
#         return value.date()

#     if isinstance(value, date):
#         return value

#     if isinstance(value, str):
#         value = value.strip()
#         if not value:
#             return None

#         for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%Y-%m-%d %H:%M:%S", "%d.%m.%Y %H:%M:%S"):
#             try:
#                 return datetime.strptime(value, fmt).date()
#             except ValueError:
#                 pass

#     return None


# def _payment_amount_from_cfdata(obj: CfData) -> Decimal:
#     cr = q2(obj.cr)
#     dt = q2(obj.dt)

#     if cr > 0:
#         return cr
#     if dt > 0:
#         return dt
#     return Decimal("0.00")


# def _payment_amount_from_split(obj: CfSplits) -> Decimal:
#     cr = q2(obj.cr)
#     dt = q2(obj.dt)

#     if cr > 0:
#         return cr
#     if dt > 0:
#         return dt
#     return Decimal("0.00")


# def _cfitem_code(cfitem) -> str:
#     if not cfitem:
#         return ""
#     return str(cfitem.code or "").strip()


# def _is_deposit_condition(cond: Conditions) -> bool:
#     return (cond.accrual_fn or "") == "deposit_by_bank_statement"


# def _is_deposit_principal_flow(flow_type: str) -> bool:
#     return flow_type in {"placement", "principal_return"}


# def _is_deposit_principal_cf_code(code: str) -> bool:
#     return code in {"322100", "314100"}


# def _is_deposit_interest_cf_code(code: str) -> bool:
#     return code == "313100"


# def _is_loan_condition(cond: Conditions) -> bool:
#     return (cond.accrual_fn or "") == "loan_by_bank_statement"


# def _is_loan_principal_flow(flow_type: str) -> bool:
#     return flow_type in {"issue", "principal_return"}


# def _is_loan_interest_flow(flow_type: str) -> bool:
#     return flow_type in {"interest_accrual", "interest_payment"}

# def _month_start(d: date) -> date:
#     return d.replace(day=1)


# def _month_end(d: date) -> date:
#     if d.month == 12:
#         return d.replace(month=12, day=31)
#     next_month = d.replace(day=28) + timedelta(days=4)
#     return next_month.replace(day=1) - timedelta(days=1)

# def _group_loan_interest_rows_by_month(
#     rows: list[dict[str, Any]],
#     cond: Conditions,
#     title: str,
#     date_from: date,
#     date_to: date,
# ) -> list[dict[str, Any]]:
#     grouped: dict[tuple[int, int], dict[str, Any]] = {}

#     for r in rows:
#         row_date = _safe_date(r.get("accrual_date")) or _safe_date(r.get("period_from"))
#         row_from = _safe_date(r.get("period_from")) or row_date
#         row_to = _safe_date(r.get("period_to")) or row_date
#         flow_type = (r.get("flow_type") or "").strip()

#         if not row_date or not row_from or not row_to:
#             continue

#         if flow_type != "interest_accrual":
#             continue

#         if row_to < date_from or row_from > date_to:
#             continue

#         key = (row_date.year, row_date.month)
#         amount = q2(r.get("amount_gross") or r.get("amount") or "0")

#         if key not in grouped:
#             month_first = date(row_date.year, row_date.month, 1)
#             month_last = _month_end(month_first)

#             period_from = max(month_first, date_from)
#             period_to = min(month_last, date_to)

#             grouped[key] = {
#                 "row_date": period_to,  # можно ставить конец месяца
#                 "row_type": "accrual",
#                 "row_type_label": "Начисление",
#                 "doc_label": f"Условие #{cond.id}",
#                 "description": f"{title} за {row_date.strftime('%m.%Y')}",
#                 "period_from": period_from,
#                 "period_to": period_to,
#                 "accrual": Decimal("0.00"),
#                 "payment": Decimal("0.00"),
#                 "sort_order": 1,
#                 "comment": "Начисление процентов по займу за месяц",
#             }

#         grouped[key]["accrual"] = q2(grouped[key]["accrual"] + amount)

#     return sorted(grouped.values(), key=lambda x: (x["row_date"], x["description"]))


# def _get_loan_codes(cond: Conditions) -> tuple[str, str, str]:
#     params = cond.params or {}
#     issue_code = str(params.get("issue_cf_code") or "").strip()
#     principal_return_code = str(params.get("principal_return_cf_code") or "").strip()
#     interest_payment_code = str(params.get("interest_payment_cf_code") or "").strip()
#     return issue_code, principal_return_code, interest_payment_code


# def _is_loan_principal_cf_code_for_contract(contract: Contracts, code: str) -> bool:
#     conditions = Conditions.objects.filter(
#         contract=contract,
#         accrual_fn="loan_by_bank_statement",
#     )

#     for cond in conditions:
#         issue_code, principal_return_code, _ = _get_loan_codes(cond)
#         if code in {issue_code, principal_return_code}:
#             return True
#     return False


# def _is_loan_interest_payment_cf_code_for_contract(contract: Contracts, code: str) -> bool:
#     conditions = Conditions.objects.filter(
#         contract=contract,
#         accrual_fn="loan_by_bank_statement",
#     )

#     for cond in conditions:
#         _, _, interest_payment_code = _get_loan_codes(cond)
#         if code and code == interest_payment_code:
#             return True
#     return False


# def get_contract_full_horizon_date(contract: Contracts) -> date:
#     cond_agg = Conditions.objects.filter(contract=contract).aggregate(
#         max_finish=Max("date_finish"),
#         max_start=Max("date_start"),
#     )

#     cf_agg = CfData.objects.filter(contract=contract).aggregate(
#         max_date=Max("date"),
#     )

#     split_agg = CfSplits.objects.filter(contract=contract).aggregate(
#         max_date=Max("transaction__date"),
#     )

#     manual_agg = Manual.objects.filter(contract=contract).aggregate(
#         max_date=Max("date"),
#     )

#     candidate_dates = [
#         cond_agg.get("max_finish"),
#         cond_agg.get("max_start"),
#         cf_agg.get("max_date"),
#         split_agg.get("max_date"),
#         manual_agg.get("max_date"),
#         date.today(),
#     ]
#     candidate_dates = [d for d in candidate_dates if d]

#     return max(candidate_dates) if candidate_dates else date.today()


# def _manual_adjustment_amount(obj: Manual) -> Decimal:
#     cr = q2(obj.cr)
#     dt = q2(obj.dt)

#     if cr > 0:
#         return cr
#     if dt > 0:
#         return dt
#     return Decimal("0.00")


# def _month_end(d: date) -> date:
#     if d.month == 12:
#         return date(d.year, 12, 31)
#     first_next_month = date(d.year + (1 if d.month == 12 else 0), 1 if d.month == 12 else d.month + 1, 1)
#     return first_next_month - timedelta(days=1)


# def _build_loan_rows_for_condition(cond: Conditions, date_from: date, date_to: date) -> list[dict[str, Any]]:
#     """
#     Для займа:
#     - выдачи тела и возвраты тела показываем отдельными строками
#     - начисление процентов агрегируем по месяцам
#     - оплату процентов показываем отдельными строками
#     """
#     result = preview_accruals(cond, anchor_date=date_from)
#     rows = result.get("rows", []) or []
#     title = result.get("title") or cond.accrual_fn or "Заем"

#     output: list[dict[str, Any]] = []
#     interest_monthly: dict[tuple[int, int], dict[str, Any]] = {}

#     for r in rows:
#         row_date = _safe_date(r.get("accrual_date")) or _safe_date(r.get("period_from"))
#         row_from = _safe_date(r.get("period_from")) or row_date
#         row_to = _safe_date(r.get("period_to")) or row_date
#         flow_type = (r.get("flow_type") or "").strip()

#         if not row_date or not row_from or not row_to:
#             continue

#         if row_to < date_from or row_from > date_to:
#             continue

#         amount = q2(r.get("amount_gross") or r.get("amount") or "0")
#         if amount <= 0:
#             continue

#         # 1. Выдача тела займа
#         if flow_type == "issue":
#             output.append({
#                 "row_date": row_date,
#                 "row_type": "loan_issue",
#                 "row_type_label": "Выдача займа",
#                 "doc_label": f"Условие #{cond.id}",
#                 "description": "Выдача тела займа",
#                 "period_from": row_date,
#                 "period_to": row_date,
#                 "accrual": Decimal("0.00"),
#                 "payment": Decimal("0.00"),
#                 "loan_issue": amount,
#                 "loan_principal_return": Decimal("0.00"),
#                 "sort_order": 0,
#                 "comment": (r.get("comment") or "").strip(),
#             })
#             continue

#         # 2. Возврат тела займа
#         if flow_type == "principal_return":
#             output.append({
#                 "row_date": row_date,
#                 "row_type": "loan_principal_return",
#                 "row_type_label": "Возврат тела займа",
#                 "doc_label": f"Условие #{cond.id}",
#                 "description": "Возврат тела займа",
#                 "period_from": row_date,
#                 "period_to": row_date,
#                 "accrual": Decimal("0.00"),
#                 "payment": Decimal("0.00"),
#                 "loan_issue": Decimal("0.00"),
#                 "loan_principal_return": amount,
#                 "sort_order": 0,
#                 "comment": (r.get("comment") or "").strip(),
#             })
#             continue

#         # 3. Начисление процентов — агрегируем по месяцу
#         if flow_type == "interest_accrual":
#             key = (row_date.year, row_date.month)

#             if key not in interest_monthly:
#                 interest_monthly[key] = {
#                     "row_date": row_date,
#                     "row_type": "accrual",
#                     "row_type_label": "Начисление",
#                     "doc_label": f"Условие #{cond.id}",
#                     "description": f"{title} за {row_date.strftime('%m.%Y')}",
#                     "period_from": row_date,
#                     "period_to": row_date,
#                     "accrual": Decimal("0.00"),
#                     "payment": Decimal("0.00"),
#                     "loan_issue": Decimal("0.00"),
#                     "loan_principal_return": Decimal("0.00"),
#                     "sort_order": 1,
#                     "comment": "",
#                 }

#             interest_monthly[key]["accrual"] = q2(interest_monthly[key]["accrual"] + amount)

#             if row_date < interest_monthly[key]["period_from"]:
#                 interest_monthly[key]["period_from"] = row_date

#             if row_date > interest_monthly[key]["period_to"]:
#                 interest_monthly[key]["period_to"] = row_date
#                 interest_monthly[key]["row_date"] = row_date

#             days_count = (interest_monthly[key]["period_to"] - interest_monthly[key]["period_from"]).days + 1
#             interest_monthly[key]["comment"] = f"Начисление процентов по займу за {days_count} дн."

#             continue

        

#     output.extend(interest_monthly.values())

#     for row in output:
#         row.setdefault("loan_issue", Decimal("0.00"))
#         row.setdefault("loan_principal_return", Decimal("0.00"))

#     return sorted(output, key=lambda x: (x["row_date"], x["sort_order"], x["description"]))


# def _build_accrual_rows_for_condition(cond: Conditions, date_from: date, date_to: date) -> list[dict[str, Any]]:
#     """
#     Используем preview_accruals.
#     Для deposit_by_bank_statement в сверку берем только проценты.
#     Для loan_by_bank_statement:
#     - показываем выдачи тела
#     - показываем возвраты тела
#     - показываем оплаты процентов
#     - начисления процентов агрегируем по месяцам
#     """
#     if _is_loan_condition(cond):
#         return _build_loan_rows_for_condition(cond, date_from, date_to)

#     result = preview_accruals(cond, anchor_date=date_from)
#     rows = result.get("rows", []) or []
#     title = result.get("title") or cond.accrual_fn or "Начисление"

#     output = []

#     for r in rows:
#         row_date = _safe_date(r.get("accrual_date")) or _safe_date(r.get("period_from"))
#         row_from = _safe_date(r.get("period_from")) or row_date
#         row_to = _safe_date(r.get("period_to")) or row_date
#         flow_type = (r.get("flow_type") or "").strip()

#         if not row_date or not row_from or not row_to:
#             continue

#         if _is_deposit_condition(cond) and _is_deposit_principal_flow(flow_type):
#             continue

#         if row_to < date_from or row_from > date_to:
#             continue

#         amount = q2(r.get("amount_gross") or r.get("amount") or "0")

#         output.append({
#             "row_date": row_date,
#             "row_type": "accrual",
#             "row_type_label": "Начисление",
#             "doc_label": f"Условие #{cond.id}",
#             "description": f"{title}",
#             "period_from": row_from,
#             "period_to": row_to,
#             "accrual": amount,
#             "payment": Decimal("0.00"),
#             "loan_issue": Decimal("0.00"),
#             "loan_principal_return": Decimal("0.00"),
#             "sort_order": 1,
#             "comment": (r.get("comment") or "").strip(),
#         })
#     return output

# def get_contract_accrual_rows(contract: Contracts, date_from: date, date_to: date) -> list[dict[str, Any]]:
#     conditions = (
#         Conditions.objects
#         .filter(contract=contract)
#         .order_by("date_start", "id")
#     )

#     rows: list[dict[str, Any]] = []

#     for cond in conditions:
#         cond_start = cond.date_start or date_from
#         cond_finish = cond.date_finish or date_to

#         if cond_finish < date_from or cond_start > date_to:
#             continue

#         rows.extend(_build_accrual_rows_for_condition(cond, date_from, date_to))

#     return rows


# def get_contract_payment_rows(contract: Contracts, date_from: date, date_to: date) -> list[dict[str, Any]]:
#     """
#     В общий акт сверки попадают:
#     - обычные оплаты
#     - проценты по депозиту
#     - проценты по кредиту
#     Не попадают:
#     - тело депозита
#     - тело кредита
#     """
#     rows: list[dict[str, Any]] = []

#     split_qs = (
#         CfSplits.objects
#         .select_related("transaction", "contract", "cfitem")
#         .filter(
#             contract=contract,
#             transaction__date__gte=date_from,
#             transaction__date__lte=date_to,
#         )
#         .order_by("transaction__date", "id")
#     )

#     used_transaction_ids = set()

#     for s in split_qs:
#         amount = _payment_amount_from_split(s)
#         if amount <= 0:
#             continue

#         code = _cfitem_code(s.cfitem)

#         # Исключаем тело депозита
#         if _is_deposit_principal_cf_code(code):
#             continue

#         # Исключаем тело кредита
#         if _is_loan_principal_cf_code_for_contract(contract, code):
#             continue

#         used_transaction_ids.add(s.transaction_id)

#         doc_number = s.transaction.doc_numner or "б/н"
#         doc_date = s.transaction.doc_date or ""
#         temp = (s.temp or s.transaction.temp or "").strip()

#         rows.append({
#             "row_date": s.transaction.date,
#             "row_type": "payment",
#             "row_type_label": "Оплата",
#             "doc_label": f"Выписка / сплит #{s.transaction_id}",
#             "description": f"Оплата по док. {doc_number} {('от ' + doc_date) if doc_date else ''}".strip(),
#             "period_from": None,
#             "period_to": None,
#             "accrual": Decimal("0.00"),
#             "payment": amount,
#             "sort_order": 2,
#             "comment": temp,
#         })

#     cf_qs = (
#         CfData.objects
#         .select_related("contract", "cfitem")
#         .filter(
#             contract=contract,
#             date__gte=date_from,
#             date__lte=date_to,
#         )
#         .exclude(id__in=used_transaction_ids)
#         .order_by("date", "id")
#     )

#     for p in cf_qs:
#         amount = _payment_amount_from_cfdata(p)
#         if amount <= 0:
#             continue

#         code = _cfitem_code(p.cfitem)

#         if _is_deposit_principal_cf_code(code):
#             continue

#         if _is_loan_principal_cf_code_for_contract(contract, code):
#             continue

#         doc_number = p.doc_numner or "б/н"
#         doc_date = p.doc_date or ""
#         temp = (p.temp or "").strip()

#         rows.append({
#             "row_date": p.date,
#             "row_type": "payment",
#             "row_type_label": "Оплата",
#             "doc_label": f"Выписка #{p.id}",
#             "description": f"Оплата по док. {doc_number} {('от ' + doc_date) if doc_date else ''}".strip(),
#             "period_from": None,
#             "period_to": None,
#             "accrual": Decimal("0.00"),
#             "payment": amount,
#             "sort_order": 2,
#             "comment": temp,
#         })

#     manual_qs = (
#         Manual.objects
#         .select_related("contract", "cfitem")
#         .filter(
#             contract=contract,
#             date__gte=date_from,
#             date__lte=date_to,
#         )
#         .order_by("date", "id")
#     )

#     for m in manual_qs:
#         amount = _manual_adjustment_amount(m)
#         if amount <= 0:
#             continue

#         code = _cfitem_code(m.cfitem)

#         if _is_deposit_principal_cf_code(code):
#             continue

#         if _is_loan_principal_cf_code_for_contract(contract, code):
#             continue

#         temp = (m.temp or "").strip()

#         rows.append({
#             "row_date": m.date,
#             "row_type": "manual_adjustment",
#             "row_type_label": "Ручная корректировка",
#             "doc_label": f"Ручная корректировка #{m.id}",
#             "description": "Ручная корректировка",
#             "period_from": None,
#             "period_to": None,
#             "accrual": Decimal("0.00"),
#             "payment": amount,
#             "sort_order": 3,
#             "comment": temp,
#         })

#     return rows


# def _get_accrual_total_before(contract: Contracts, date_from: date) -> Decimal:
#     """
#     До начала периода считаем начисления:
#     - для депозитов: только проценты
#     - для кредитов: только начисленные проценты
#     """
#     if not contract:
#         return Decimal("0.00")

#     conditions = (
#         Conditions.objects
#         .filter(contract=contract)
#         .order_by("date_start", "id")
#     )

#     total = Decimal("0.00")

#     for cond in conditions:
#         result = preview_accruals(cond, anchor_date=date_from)
#         rows = result.get("rows", []) or []

#         for r in rows:
#             row_date = _safe_date(r.get("accrual_date")) or _safe_date(r.get("period_from"))
#             flow_type = (r.get("flow_type") or "").strip()

#             if not row_date:
#                 continue

#             if _is_deposit_condition(cond) and _is_deposit_principal_flow(flow_type):
#                 continue

#             if _is_loan_condition(cond) and flow_type != "interest_accrual":
#                 continue

#             if row_date < date_from:
#                 total += q2(r.get("amount_gross") or r.get("amount") or "0")

#     return q2(total)


# def _get_payment_total_before(contract: Contracts, date_from: date) -> Decimal:
#     """
#     До начала периода считаем оплаты:
#     - исключаем тело депозита
#     - исключаем тело кредита
#     """
#     used_transaction_ids = set()
#     total = Decimal("0.00")

#     split_qs = (
#         CfSplits.objects
#         .select_related("transaction", "cfitem")
#         .filter(
#             contract=contract,
#             transaction__date__lt=date_from,
#         )
#     )

#     for s in split_qs:
#         amount = _payment_amount_from_split(s)
#         if amount <= 0:
#             continue

#         code = _cfitem_code(s.cfitem)

#         if _is_deposit_principal_cf_code(code):
#             continue

#         if _is_loan_principal_cf_code_for_contract(contract, code):
#             continue

#         total += amount
#         used_transaction_ids.add(s.transaction_id)

#     cf_qs = (
#         CfData.objects
#         .select_related("cfitem")
#         .filter(
#             contract=contract,
#             date__lt=date_from,
#         )
#         .exclude(id__in=used_transaction_ids)
#     )

#     for p in cf_qs:
#         amount = _payment_amount_from_cfdata(p)
#         if amount <= 0:
#             continue

#         code = _cfitem_code(p.cfitem)

#         if _is_deposit_principal_cf_code(code):
#             continue

#         if _is_loan_principal_cf_code_for_contract(contract, code):
#             continue

#         total += amount

#     manual_qs = (
#         Manual.objects
#         .select_related("cfitem")
#         .filter(
#             contract=contract,
#             date__lt=date_from,
#         )
#     )

#     for m in manual_qs:
#         amount = _manual_adjustment_amount(m)
#         if amount <= 0:
#             continue

#         code = _cfitem_code(m.cfitem)

#         if _is_deposit_principal_cf_code(code):
#             continue

#         if _is_loan_principal_cf_code_for_contract(contract, code):
#             continue

#         total += amount

#     return q2(total)


# def get_balance_status(balance: Decimal) -> str:
#     balance = q2(balance)

#     if balance > 0:
#         return "Наш долг"
#     if balance < 0:
#         return "Переплата"
#     return "Сальдо закрыто"


# def get_balance_comment(balance: Decimal) -> str:
#     balance = q2(balance)

#     if balance > 0:
#         return "Положительное сальдо на текущую дату означает задолженность нашей компании перед контрагентом."
#     if balance < 0:
#         return "Отрицательное сальдо на текущую дату означает переплату со стороны нашей компании."
#     return "По состоянию на текущую дату задолженность отсутствует."


# def get_balance_status_class(balance: Decimal) -> str:
#     balance = q2(balance)

#     if balance > 0:
#         return "is-debt"
#     if balance < 0:
#         return "is-overpayment"
#     return "is-closed"


# def get_contract_loan_summary(contract: Contracts, date_from: date, date_to: date) -> dict[str, Decimal]:
#     """
#     Аналитика по кредиту / займу строго в пределах периода date_from-date_to:
#     - выдано
#     - возвращено тела
#     - остаток тела на конец периода
#     - начислено процентов
#     - оплачено процентов
#     - остаток процентов на конец периода
#     """
#     conditions = (
#         Conditions.objects
#         .filter(
#             contract=contract,
#             accrual_fn="loan_by_bank_statement",
#         )
#         .order_by("date_start", "id")
#     )

#     issued_total = Decimal("0.00")
#     principal_returned_total = Decimal("0.00")
#     interest_accrued_total = Decimal("0.00")
#     interest_paid_total = Decimal("0.00")

#     issued_total_before = Decimal("0.00")
#     principal_returned_total_before = Decimal("0.00")
#     interest_accrued_total_before = Decimal("0.00")
#     interest_paid_total_before = Decimal("0.00")

#     for cond in conditions:
#         result = preview_accruals(cond, anchor_date=date_from)
#         rows = result.get("rows", []) or []

#         for r in rows:
#             row_date = _safe_date(r.get("accrual_date")) or _safe_date(r.get("period_from"))
#             flow_type = (r.get("flow_type") or "").strip()
#             amount = q2(r.get("amount_gross") or r.get("amount") or "0")

#             if not row_date or amount <= 0:
#                 continue

#             # До начала периода — для расчета остатка на начало
#             if row_date < date_from:
#                 if flow_type == "issue":
#                     issued_total_before += amount
#                 elif flow_type == "principal_return":
#                     principal_returned_total_before += amount
#                 elif flow_type == "interest_accrual":
#                     interest_accrued_total_before += amount
#                 elif flow_type == "interest_payment":
#                     interest_paid_total_before += amount

#             # Внутри периода
#             if date_from <= row_date <= date_to:
#                 if flow_type == "issue":
#                     issued_total += amount
#                 elif flow_type == "principal_return":
#                     principal_returned_total += amount
#                 elif flow_type == "interest_accrual":
#                     interest_accrued_total += amount
#                 elif flow_type == "interest_payment":
#                     interest_paid_total += amount

#     principal_outstanding = q2(
#         (issued_total_before + issued_total) - (principal_returned_total_before + principal_returned_total)
#     )
#     interest_outstanding = q2(
#         (interest_accrued_total_before + interest_accrued_total) - (interest_paid_total_before + interest_paid_total)
#     )

#     return {
#         "issued_total": q2(issued_total),
#         "principal_returned_total": q2(principal_returned_total),
#         "principal_outstanding": q2(principal_outstanding),
#         "interest_accrued_total": q2(interest_accrued_total),
#         "interest_paid_total": q2(interest_paid_total),
#         "interest_outstanding": q2(interest_outstanding),
#     }

# def build_contract_reconciliation(
#     contract: Contracts,
#     date_from: date,
#     date_to: date,
#     report_date: date | None = None,
# ) -> dict[str, Any]:
#     """
#     date_to     -> до какой даты строим весь реестр
#     report_date -> на какую дату отдельно считаем текущее сальдо
#     """
#     report_date = report_date or date.today()

#     accrual_rows = get_contract_accrual_rows(contract, date_from, date_to)
#     payment_rows = get_contract_payment_rows(contract, date_from, date_to)

#     opening_accruals = _get_accrual_total_before(contract, date_from)
#     opening_payments = _get_payment_total_before(contract, date_from)
#     opening_balance = q2(opening_accruals - opening_payments)

#     rows = accrual_rows + payment_rows
#     rows.sort(key=lambda x: (x["row_date"], x["sort_order"], x["description"]))

#     running_balance = opening_balance
#     current_balance = opening_balance

#     total_accruals = Decimal("0.00")
#     total_payments = Decimal("0.00")

#     current_accruals = Decimal("0.00")
#     current_payments = Decimal("0.00")

#     prepared_rows = []

#     for row in rows:
#         accrual = q2(row.get("accrual"))
#         payment = q2(row.get("payment"))

#         total_accruals += accrual
#         total_payments += payment
#         running_balance = q2(running_balance + accrual - payment)

#         prepared = dict(row)
#         prepared["accrual"] = accrual
#         prepared["payment"] = payment
#         prepared["loan_issue"] = q2(row.get("loan_issue"))
#         prepared["loan_principal_return"] = q2(row.get("loan_principal_return"))
#         prepared["balance"] = running_balance

#         if row["row_date"] <= report_date:
#             current_accruals += accrual
#             current_payments += payment
#             current_balance = q2(current_balance + accrual - payment)

#         prepared_rows.append(prepared)

#     closing_balance = q2(opening_balance + total_accruals - total_payments)

#     loan_summary = get_contract_loan_summary(contract, date_from, date_to)

#     return {
#         "contract": contract,
#         "date_from": date_from,
#         "date_to": date_to,
#         "report_date": report_date,
#         "opening_balance": q2(opening_balance),

#         # Итоги по сверке процентов / обычных начислений
#         "total_accruals": q2(total_accruals),
#         "total_payments": q2(total_payments),
#         "closing_balance": q2(closing_balance),
#         "closing_balance_status": get_balance_status(closing_balance),
#         "closing_balance_comment": get_balance_comment(closing_balance),
#         "closing_balance_status_class": get_balance_status_class(closing_balance),

#         # Итоги на текущую дату
#         "current_accruals": q2(current_accruals),
#         "current_payments": q2(current_payments),
#         "current_balance": q2(current_balance),
#         "current_balance_status": get_balance_status(current_balance),
#         "current_balance_comment": get_balance_comment(current_balance),
#         "current_balance_status_class": get_balance_status_class(current_balance),

#         # Отдельная аналитика по кредиту / займу
#         "loan_issued_total": q2(loan_summary["issued_total"]),
#         "loan_principal_returned_total": q2(loan_summary["principal_returned_total"]),
#         "loan_principal_outstanding": q2(loan_summary["principal_outstanding"]),
#         "loan_interest_accrued_total": q2(loan_summary["interest_accrued_total"]),
#         "loan_interest_paid_total": q2(loan_summary["interest_paid_total"]),
#         "loan_interest_outstanding": q2(loan_summary["interest_outstanding"]),

#         "rows": prepared_rows,
#     }



# contracts/reconciliation/service.py
from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from django.db.models import Max

from contracts.models import Conditions, Contracts
from contracts.accruals.service import preview_accruals
from treasury.models import CfData, CfSplits
from grossbook.models import Manual


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


def _cfitem_code(cfitem) -> str:
    if not cfitem:
        return ""
    return str(cfitem.code or "").strip()


def _is_deposit_condition(cond: Conditions) -> bool:
    return (cond.accrual_fn or "") == "deposit_by_bank_statement"


def _is_deposit_principal_flow(flow_type: str) -> bool:
    return flow_type in {"placement", "principal_return"}


def _is_deposit_principal_cf_code(code: str) -> bool:
    return code in {"322100", "314100"}


def _is_deposit_interest_cf_code(code: str) -> bool:
    return code == "313100"


def _is_loan_condition(cond: Conditions) -> bool:
    return (cond.accrual_fn or "") == "loan_by_bank_statement"


def _is_loan_principal_flow(flow_type: str) -> bool:
    return flow_type in {"issue", "principal_return"}


def _is_loan_interest_flow(flow_type: str) -> bool:
    return flow_type in {"interest_accrual", "interest_payment"}


def _month_end(d: date) -> date:
    if d.month == 12:
        return date(d.year, 12, 31)
    first_next_month = date(d.year, d.month + 1, 1)
    return first_next_month - timedelta(days=1)


def _format_decimal_plain(x: Decimal | str | int | float | None) -> str:
    v = q2(x)
    s = f"{v:,.2f}"
    return s.replace(",", " ").replace(".", ",")


def _build_monthly_interest_comment(bucket: dict[str, Any]) -> str:
    """
    Детальная расшифровка начисления процентов по займу за месяц:
    по каждому отрезку с одинаковым телом / ставкой / базой дней.

    Пример:
    01.02.2026–10.02.2026: 30 000 000,00 × 14,50% / 365 × 10 дн. = 119 178,08
    11.02.2026–28.02.2026: 25 000 000,00 × 14,50% / 365 × 18 дн. = 178 767,12
    """
    period_from = bucket.get("period_from")
    period_to = bucket.get("period_to")
    calc_lines = bucket.get("calc_lines") or []

    if not period_from or not period_to:
        return "Начисление процентов по займу за месяц"

    if not calc_lines:
        days_count = (period_to - period_from).days + 1
        return f"Начисление процентов по займу за {days_count} дн."

    # Нормализуем и сортируем строки расчёта по дате
    normalized_lines: list[dict[str, Any]] = []
    for x in calc_lines:
        row_date = _safe_date(x.get("date"))
        if not row_date:
            continue

        principal_balance = q2(x.get("principal_balance"))
        annual_rate = q2(x.get("annual_rate"))
        day_count_basis = q2(x.get("day_count_basis"))
        amount = q2(x.get("amount"))

        normalized_lines.append({
            "date": row_date,
            "principal_balance": principal_balance,
            "annual_rate": annual_rate,
            "day_count_basis": day_count_basis,
            "amount": amount,
        })

    if not normalized_lines:
        days_count = (period_to - period_from).days + 1
        return f"Начисление процентов по займу за {days_count} дн."

    normalized_lines.sort(key=lambda x: x["date"])

    # Склеиваем подряд идущие дни с одинаковыми параметрами
    grouped_periods: list[dict[str, Any]] = []
    current = None

    for line in normalized_lines:
        if current is None:
            current = {
                "date_from": line["date"],
                "date_to": line["date"],
                "principal_balance": line["principal_balance"],
                "annual_rate": line["annual_rate"],
                "day_count_basis": line["day_count_basis"],
                "amount": line["amount"],
            }
            continue

        prev_date = current["date_to"]
        is_next_day = line["date"] == prev_date + timedelta(days=1)
        same_terms = (
            line["principal_balance"] == current["principal_balance"]
            and line["annual_rate"] == current["annual_rate"]
            and line["day_count_basis"] == current["day_count_basis"]
        )

        if is_next_day and same_terms:
            current["date_to"] = line["date"]
            current["amount"] = q2(current["amount"] + line["amount"])
        else:
            grouped_periods.append(current)
            current = {
                "date_from": line["date"],
                "date_to": line["date"],
                "principal_balance": line["principal_balance"],
                "annual_rate": line["annual_rate"],
                "day_count_basis": line["day_count_basis"],
                "amount": line["amount"],
            }

    if current:
        grouped_periods.append(current)

    parts: list[str] = []

    for g in grouped_periods:
        d1 = g["date_from"]
        d2 = g["date_to"]
        days_count = (d2 - d1).days + 1

        balance_str = _format_decimal_plain(g["principal_balance"])
        rate_str = _format_decimal_plain(g["annual_rate"])
        basis_str = str(int(g["day_count_basis"]))
        amount_str = _format_decimal_plain(g["amount"])

        if d1 == d2:
            period_str = d1.strftime("%d.%m.%Y")
        else:
            period_str = f"{d1.strftime('%d.%m.%Y')}–{d2.strftime('%d.%m.%Y')}"

        parts.append(
            f"{period_str}: "
            f"{balance_str} × {rate_str}% / {basis_str} × {days_count} дн. = {amount_str}"
        )

    total_amount = q2(sum((g["amount"] for g in grouped_periods), Decimal("0.00")))
    total_amount_str = _format_decimal_plain(total_amount)

    if len(parts) == 1:
        return f"Расчёт процентов: {parts[0]}"

    return "Расчёт процентов:\n" + "\n".join(parts) + f"\nИтого за период: {total_amount_str}"

def _get_loan_codes(cond: Conditions) -> tuple[str, str, str]:
    params = cond.params or {}
    issue_code = str(params.get("issue_cf_code") or "").strip()
    principal_return_code = str(params.get("principal_return_cf_code") or "").strip()
    interest_payment_code = str(params.get("interest_payment_cf_code") or "").strip()
    return issue_code, principal_return_code, interest_payment_code


def _is_loan_principal_cf_code_for_contract(contract: Contracts, code: str) -> bool:
    conditions = Conditions.objects.filter(
        contract=contract,
        accrual_fn="loan_by_bank_statement",
    )

    for cond in conditions:
        issue_code, principal_return_code, _ = _get_loan_codes(cond)
        if code in {issue_code, principal_return_code}:
            return True
    return False


def _is_loan_ndfl_flow(flow_type: str) -> bool:
    return flow_type == "ndfl_withholding"


def _is_loan_interest_payment_cf_code_for_contract(contract: Contracts, code: str) -> bool:
    conditions = Conditions.objects.filter(
        contract=contract,
        accrual_fn="loan_by_bank_statement",
    )

    for cond in conditions:
        _, _, interest_payment_code = _get_loan_codes(cond)
        if code and code == interest_payment_code:
            return True
    return False


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

    manual_agg = Manual.objects.filter(contract=contract).aggregate(
        max_date=Max("date"),
    )

    candidate_dates = [
        cond_agg.get("max_finish"),
        cond_agg.get("max_start"),
        cf_agg.get("max_date"),
        split_agg.get("max_date"),
        manual_agg.get("max_date"),
        date.today(),
    ]
    candidate_dates = [d for d in candidate_dates if d]

    return max(candidate_dates) if candidate_dates else date.today()


def _manual_adjustment_amount(obj: Manual) -> Decimal:
    cr = q2(obj.cr)
    dt = q2(obj.dt)

    if cr > 0:
        return cr
    if dt > 0:
        return dt
    return Decimal("0.00")


def _build_loan_rows_for_condition(cond: Conditions, date_from: date, date_to: date) -> list[dict[str, Any]]:
    """
    Для займа:
    - выдачи тела и возвраты тела показываем отдельными строками
    - начисление процентов агрегируем по месяцам
    - оплату процентов здесь НЕ добавляем, потому что она уже приходит из выписки
    """
    # result = preview_accruals(cond, anchor_date=date_from)
    result = preview_accruals(cond, anchor_date=date_to)
    rows = result.get("rows", []) or []
    title = result.get("title") or cond.accrual_fn or "Заем"

    output: list[dict[str, Any]] = []
    interest_monthly: dict[tuple[int, int], dict[str, Any]] = {}

    for r in rows:
        row_date = _safe_date(r.get("accrual_date")) or _safe_date(r.get("period_from"))
        row_from = _safe_date(r.get("period_from")) or row_date
        row_to = _safe_date(r.get("period_to")) or row_date
        
        
        
        flow_type = (r.get("flow_type") or "").strip()

        if not row_date or not row_from or not row_to:
            continue

        if row_to < date_from or row_from > date_to:
            continue

        amount = q2(r.get("amount_gross") or r.get("amount") or "0")
        if amount <= 0:
            continue

        # 5. Удержание НДФЛ
        if flow_type == "ndfl_withholding":
            output.append({
                "row_date": row_date,
                "row_type": "payment",
                "row_type_label": "Удержан НДФЛ",
                "doc_label": f"Условие #{cond.id}",
                "description": "Удержан НДФЛ с процентов по займу",
                "period_from": row_date,
                "period_to": row_date,
                "accrual": Decimal("0.00"),
                "payment": amount,
                "loan_issue": Decimal("0.00"),
                "loan_principal_return": Decimal("0.00"),
                "sort_order": 2,
                "comment": "НДФЛ удержан налоговым агентом",
            })
            continue

        if not row_date or not row_from or not row_to:
            continue

        if row_to < date_from or row_from > date_to:
            continue

        amount = q2(r.get("amount_gross") or r.get("amount") or "0")
        if amount <= 0:
            continue

        # 1. Выдача тела займа
        if flow_type == "issue":
            output.append({
                "row_date": row_date,
                "row_type": "loan_issue",
                "row_type_label": "Выдача займа",
                "doc_label": f"Условие #{cond.id}",
                "description": "Выдача тела займа",
                "period_from": row_date,
                "period_to": row_date,
                "accrual": Decimal("0.00"),
                "payment": Decimal("0.00"),
                "loan_issue": amount,
                "loan_principal_return": Decimal("0.00"),
                "sort_order": 0,
                "comment": (r.get("comment") or "").strip(),
            })
            continue

        # 2. Возврат тела займа
        if flow_type == "principal_return":
            output.append({
                "row_date": row_date,
                "row_type": "loan_principal_return",
                "row_type_label": "Возврат тела займа",
                "doc_label": f"Условие #{cond.id}",
                "description": "Возврат тела займа",
                "period_from": row_date,
                "period_to": row_date,
                "accrual": Decimal("0.00"),
                "payment": Decimal("0.00"),
                "loan_issue": Decimal("0.00"),
                "loan_principal_return": amount,
                "sort_order": 0,
                "comment": (r.get("comment") or "").strip(),
            })
            continue

        # 3. Начисление процентов — агрегируем по месяцу, но период берем фактический
        if flow_type == "interest_accrual":
            key = (row_date.year, row_date.month)

            if key not in interest_monthly:
                interest_monthly[key] = {
                    "row_date": row_date,
                    "row_type": "accrual",
                    "row_type_label": "Начисление",
                    "doc_label": f"Условие #{cond.id}",
                    "description": f"{title} за {row_date.strftime('%m.%Y')}",
                    "period_from": row_date,
                    "period_to": row_date,
                    "accrual": Decimal("0.00"),
                    "payment": Decimal("0.00"),
                    "loan_issue": Decimal("0.00"),
                    "loan_principal_return": Decimal("0.00"),
                    "sort_order": 1,
                    "comment": "",
                    "calc_lines": [],
                }

            bucket = interest_monthly[key]
            bucket["accrual"] = q2(bucket["accrual"] + amount)

            if row_date < bucket["period_from"]:
                bucket["period_from"] = row_date

            if row_date > bucket["period_to"]:
                bucket["period_to"] = row_date
                bucket["row_date"] = row_date

            bucket["calc_lines"].append({
                "principal_balance": q2(r.get("principal_balance")),
                "annual_rate": q2(r.get("annual_rate")),
                "day_count_basis": q2(r.get("day_count_basis")),
                "amount": q2(amount),
                "date": row_date,
            })
            continue

        # 4. Оплату процентов здесь не добавляем
        if flow_type == "interest_payment":
            continue

    output.extend(interest_monthly.values())

    for row in output:
        row.setdefault("loan_issue", Decimal("0.00"))
        row.setdefault("loan_principal_return", Decimal("0.00"))
        row["comment"] = _build_monthly_interest_comment(row) if row.get("row_type") == "accrual" else row.get("comment", "")
        row.pop("calc_lines", None)

    return sorted(output, key=lambda x: (x["row_date"], x["sort_order"], x["description"]))


def _build_accrual_rows_for_condition(cond: Conditions, date_from: date, date_to: date) -> list[dict[str, Any]]:
    """
    Используем preview_accruals.
    Для deposit_by_bank_statement в сверку берем только проценты.
    Для loan_by_bank_statement:
    - показываем выдачи тела
    - показываем возвраты тела
    - начисления процентов агрегируем по месяцам
    """
    if _is_loan_condition(cond):
        return _build_loan_rows_for_condition(cond, date_from, date_to)

    result = preview_accruals(cond, anchor_date=date_from)
    rows = result.get("rows", []) or []
    title = result.get("title") or cond.accrual_fn or "Начисление"

    output = []

    for r in rows:
        row_date = _safe_date(r.get("accrual_date")) or _safe_date(r.get("period_from"))
        row_from = _safe_date(r.get("period_from")) or row_date
        row_to = _safe_date(r.get("period_to")) or row_date
        flow_type = (r.get("flow_type") or "").strip()

        if not row_date or not row_from or not row_to:
            continue

        if _is_deposit_condition(cond) and _is_deposit_principal_flow(flow_type):
            continue

        if row_to < date_from or row_from > date_to:
            continue

        amount = q2(r.get("amount_gross") or r.get("amount") or "0")

        output.append({
            "row_date": row_date,
            "row_type": "accrual",
            "row_type_label": "Начисление",
            "doc_label": f"Условие #{cond.id}",
            "description": f"{title}",
            "period_from": row_from,
            "period_to": row_to,
            "accrual": amount,
            "payment": Decimal("0.00"),
            "loan_issue": Decimal("0.00"),
            "loan_principal_return": Decimal("0.00"),
            "sort_order": 1,
            "comment": (r.get("comment") or "").strip(),
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
        cond_start = cond.date_start or date_from
        cond_finish = cond.date_finish or date_to

        if cond_finish < date_from or cond_start > date_to:
            continue

        rows.extend(_build_accrual_rows_for_condition(cond, date_from, date_to))

    return rows


def get_contract_payment_rows(contract: Contracts, date_from: date, date_to: date) -> list[dict[str, Any]]:
    """
    В общий акт сверки попадают:
    - обычные оплаты
    - проценты по депозиту
    - проценты по кредиту
    Не попадают:
    - тело депозита
    - тело кредита
    """
    rows: list[dict[str, Any]] = []

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

        code = _cfitem_code(s.cfitem)

        if _is_deposit_principal_cf_code(code):
            continue

        if _is_loan_principal_cf_code_for_contract(contract, code):
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
            "loan_issue": Decimal("0.00"),
            "loan_principal_return": Decimal("0.00"),
            "sort_order": 2,
            "comment": temp,
        })

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

        code = _cfitem_code(p.cfitem)

        if _is_deposit_principal_cf_code(code):
            continue

        if _is_loan_principal_cf_code_for_contract(contract, code):
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
            "loan_issue": Decimal("0.00"),
            "loan_principal_return": Decimal("0.00"),
            "sort_order": 2,
            "comment": temp,
        })

    manual_qs = (
        Manual.objects
        .select_related("contract", "cfitem")
        .filter(
            contract=contract,
            date__gte=date_from,
            date__lte=date_to,
        )
        .order_by("date", "id")
    )

    for m in manual_qs:
        amount = _manual_adjustment_amount(m)
        if amount <= 0:
            continue

        code = _cfitem_code(m.cfitem)

        if _is_deposit_principal_cf_code(code):
            continue

        if _is_loan_principal_cf_code_for_contract(contract, code):
            continue

        temp = (m.temp or "").strip()

        rows.append({
            "row_date": m.date,
            "row_type": "manual_adjustment",
            "row_type_label": "Ручная корректировка",
            "doc_label": f"Ручная корректировка #{m.id}",
            "description": "Ручная корректировка",
            "period_from": None,
            "period_to": None,
            "accrual": Decimal("0.00"),
            "payment": amount,
            "loan_issue": Decimal("0.00"),
            "loan_principal_return": Decimal("0.00"),
            "sort_order": 3,
            "comment": temp,
        })

    return rows


def _get_accrual_total_before(contract: Contracts, date_from: date) -> Decimal:
    """
    До начала периода считаем начисления:
    - для депозитов: только проценты
    - для кредитов: только начисленные проценты
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
            row_date = _safe_date(r.get("accrual_date")) or _safe_date(r.get("period_from"))
            flow_type = (r.get("flow_type") or "").strip()

            if not row_date:
                continue

            if _is_deposit_condition(cond) and _is_deposit_principal_flow(flow_type):
                continue

            if _is_loan_condition(cond) and flow_type != "interest_accrual":
                continue

            if row_date < date_from:
                total += q2(r.get("amount_gross") or r.get("amount") or "0")

    return q2(total)


def _get_payment_total_before(contract: Contracts, date_from: date) -> Decimal:
    """
    До начала периода считаем оплаты:
    - исключаем тело депозита
    - исключаем тело кредита
    - ДОБАВЛЯЕМ удержанный НДФЛ по займу из preview_accruals,
      потому что это не банковская выписка, а синтетическая строка начисления
    """
    used_transaction_ids = set()
    total = Decimal("0.00")

    split_qs = (
        CfSplits.objects
        .select_related("transaction", "cfitem")
        .filter(
            contract=contract,
            transaction__date__lt=date_from,
        )
    )

    for s in split_qs:
        amount = _payment_amount_from_split(s)
        if amount <= 0:
            continue

        code = _cfitem_code(s.cfitem)

        if _is_deposit_principal_cf_code(code):
            continue

        if _is_loan_principal_cf_code_for_contract(contract, code):
            continue

        total += amount
        used_transaction_ids.add(s.transaction_id)

    cf_qs = (
        CfData.objects
        .select_related("cfitem")
        .filter(
            contract=contract,
            date__lt=date_from,
        )
        .exclude(id__in=used_transaction_ids)
    )

    for p in cf_qs:
        amount = _payment_amount_from_cfdata(p)
        if amount <= 0:
            continue

        code = _cfitem_code(p.cfitem)

        if _is_deposit_principal_cf_code(code):
            continue

        if _is_loan_principal_cf_code_for_contract(contract, code):
            continue

        total += amount

    manual_qs = (
        Manual.objects
        .select_related("cfitem")
        .filter(
            contract=contract,
            date__lt=date_from,
        )
    )

    for m in manual_qs:
        amount = _manual_adjustment_amount(m)
        if amount <= 0:
            continue

        code = _cfitem_code(m.cfitem)

        if _is_deposit_principal_cf_code(code):
            continue

        if _is_loan_principal_cf_code_for_contract(contract, code):
            continue

        total += amount

    # ---------------------------------------------------------
    # ДОБАВЛЯЕМ синтетические оплаты НДФЛ по займам из preview
    # ---------------------------------------------------------
    loan_conditions = (
        Conditions.objects
        .filter(contract=contract, accrual_fn="loan_by_bank_statement")
        .order_by("date_start", "id")
    )

    for cond in loan_conditions:
        result = preview_accruals(cond, anchor_date=date_from)
        rows = result.get("rows", []) or []

        for r in rows:
            row_date = _safe_date(r.get("accrual_date")) or _safe_date(r.get("period_from"))
            flow_type = (r.get("flow_type") or "").strip()

            if not row_date:
                continue

            if flow_type == "ndfl_withholding" and row_date < date_from:
                total += q2(r.get("amount_gross") or r.get("amount") or "0")

    return q2(total)

def get_balance_status(balance: Decimal) -> str:
    balance = q2(balance)

    if balance > 2:
        return "Наш долг"
    if balance < -2:
        return "Переплата"
    return "Сальдо закрыто"


def get_balance_comment(balance: Decimal) -> str:
    balance = q2(balance)

    if balance > 2:
        return "Положительное сальдо на текущую дату означает задолженность нашей компании перед контрагентом."
    if balance < -2:
        return "Отрицательное сальдо на текущую дату означает переплату со стороны нашей компании."
    return "По состоянию на текущую дату задолженность отсутствует."


def get_balance_status_class(balance: Decimal) -> str:
    balance = q2(balance)

    if balance > 2:
        return "is-debt"
    if balance < -2:
        return "is-overpayment"
    return "is-closed"


def get_contract_loan_summary(contract: Contracts, date_from: date, date_to: date) -> dict[str, Decimal]:
    """
    Аналитика по кредиту / займу строго в пределах периода date_from-date_to:
    - выдано
    - возвращено тела
    - остаток тела на конец периода
    - начислено процентов
    - оплачено процентов
    - удержан НДФЛ
    - остаток процентов на конец периода
    """
    conditions = (
        Conditions.objects
        .filter(
            contract=contract,
            accrual_fn="loan_by_bank_statement",
        )
        .order_by("date_start", "id")
    )

    issued_total = Decimal("0.00")
    principal_returned_total = Decimal("0.00")
    interest_accrued_total = Decimal("0.00")
    interest_paid_total = Decimal("0.00")
    ndfl_withheld_total = Decimal("0.00")

    issued_total_before = Decimal("0.00")
    principal_returned_total_before = Decimal("0.00")
    interest_accrued_total_before = Decimal("0.00")
    interest_paid_total_before = Decimal("0.00")
    ndfl_withheld_total_before = Decimal("0.00")

    for cond in conditions:
        result = preview_accruals(cond, anchor_date=date_to)
        rows = result.get("rows", []) or []

        for r in rows:
            row_date = _safe_date(r.get("accrual_date")) or _safe_date(r.get("period_from"))
            flow_type = (r.get("flow_type") or "").strip()
            amount = q2(r.get("amount_gross") or r.get("amount") or "0")

            if not row_date or amount <= 0:
                continue

            if row_date < date_from:
                if flow_type == "issue":
                    issued_total_before += amount
                elif flow_type == "principal_return":
                    principal_returned_total_before += amount
                elif flow_type == "interest_accrual":
                    interest_accrued_total_before += amount
                elif flow_type == "interest_payment":
                    interest_paid_total_before += amount
                elif flow_type == "ndfl_withholding":
                    ndfl_withheld_total_before += amount

            if date_from <= row_date <= date_to:
                if flow_type == "issue":
                    issued_total += amount
                elif flow_type == "principal_return":
                    principal_returned_total += amount
                elif flow_type == "interest_accrual":
                    interest_accrued_total += amount
                elif flow_type == "interest_payment":
                    interest_paid_total += amount
                elif flow_type == "ndfl_withholding":
                    ndfl_withheld_total += amount

    principal_outstanding = q2(
        (issued_total_before + issued_total)
        - (principal_returned_total_before + principal_returned_total)
    )

    interest_outstanding = q2(
        (interest_accrued_total_before + interest_accrued_total)
        - (interest_paid_total_before + interest_paid_total)
        - (ndfl_withheld_total_before + ndfl_withheld_total)
    )

    return {
        "issued_total": q2(issued_total),
        "principal_returned_total": q2(principal_returned_total),
        "principal_outstanding": q2(principal_outstanding),

        "interest_accrued_total": q2(interest_accrued_total),
        "interest_paid_total": q2(interest_paid_total),
        "ndfl_withheld_total": q2(ndfl_withheld_total),

        "interest_outstanding": q2(interest_outstanding),
    }
def build_contract_reconciliation(
    contract: Contracts,
    date_from: date,
    date_to: date,
    report_date: date | None = None,
) -> dict[str, Any]:
    """
    date_to     -> до какой даты строим весь реестр
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
    total_loan_issue = Decimal("0.00")
    total_loan_principal_return = Decimal("0.00")

    current_accruals = Decimal("0.00")
    current_payments = Decimal("0.00")

    prepared_rows = []

    for row in rows:
        accrual = q2(row.get("accrual"))
        payment = q2(row.get("payment"))
        loan_issue = q2(row.get("loan_issue"))
        loan_principal_return = q2(row.get("loan_principal_return"))

        total_accruals += accrual
        total_payments += payment
        total_loan_issue += loan_issue
        total_loan_principal_return += loan_principal_return

        running_balance = q2(running_balance + accrual - payment)

        prepared = dict(row)
        prepared["accrual"] = accrual
        prepared["payment"] = payment
        prepared["loan_issue"] = loan_issue
        prepared["loan_principal_return"] = loan_principal_return
        prepared["balance"] = running_balance

        if row["row_date"] <= report_date:
            current_accruals += accrual
            current_payments += payment
            current_balance = q2(current_balance + accrual - payment)

        prepared_rows.append(prepared)

    closing_balance = q2(opening_balance + total_accruals - total_payments)

    loan_summary = get_contract_loan_summary(contract, date_from, date_to)

    return {
        "contract": contract,
        "date_from": date_from,
        "date_to": date_to,
        "report_date": report_date,
        "opening_balance": q2(opening_balance),

        "total_accruals": q2(total_accruals),
        "total_payments": q2(total_payments),
        "total_loan_issue": q2(total_loan_issue),
        "total_loan_principal_return": q2(total_loan_principal_return),
        "closing_balance": q2(closing_balance),
        "closing_balance_status": get_balance_status(closing_balance),
        "closing_balance_comment": get_balance_comment(closing_balance),
        "closing_balance_status_class": get_balance_status_class(closing_balance),

        "current_accruals": q2(current_accruals),
        "current_payments": q2(current_payments),
        "current_balance": q2(current_balance),
        "current_balance_status": get_balance_status(current_balance),
        "current_balance_comment": get_balance_comment(current_balance),
        "current_balance_status_class": get_balance_status_class(current_balance),

        "loan_issued_total": q2(loan_summary["issued_total"]),
        "loan_principal_returned_total": q2(loan_summary["principal_returned_total"]),
        "loan_principal_outstanding": q2(loan_summary["principal_outstanding"]),
        "loan_interest_accrued_total": q2(loan_summary["interest_accrued_total"]),
        "loan_interest_paid_total": q2(loan_summary["interest_paid_total"]),
        "loan_ndfl_withheld_total": q2(loan_summary["ndfl_withheld_total"]), 
        "loan_interest_outstanding": q2(loan_summary["interest_outstanding"]),

        "rows": prepared_rows,
    }