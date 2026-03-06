# contracts/accruals/service.py
# from datetime import date
# from decimal import Decimal, ROUND_HALF_UP
# from calendar import monthrange

# from contracts.models import VatMode
# from .registry import ACCRUAL_REGISTRY


# def q2(x: Decimal) -> Decimal:
#     return x.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


# def _month_start(d: date) -> date:
#     return date(d.year, d.month, 1)


# def _month_end(d: date) -> date:
#     last_day = monthrange(d.year, d.month)[1]
#     return date(d.year, d.month, last_day)


# def _next_month(d: date) -> date:
#     if d.month == 12:
#         return date(d.year + 1, 1, 1)
#     return date(d.year, d.month + 1, 1)


# def _iter_months(start: date, finish: date):
#     cur = _month_start(start)
#     end = _month_start(finish)
#     while cur <= end:
#         yield cur
#         cur = _next_month(cur)


# def split_vat(amount: Decimal, vat_mode: str, vat_rate: Decimal | None) -> dict:
#     """
#     amount:
#         - если vat_mode=included -> сумма уже с НДС
#         - если vat_mode=excluded -> сумма без НДС, НДС добавляем сверху
#         - если exempt/unknown -> считаем без НДС
#     """
#     amount = Decimal(str(amount or "0"))
#     vat_rate = Decimal(str(vat_rate or "0"))

#     if vat_mode == VatMode.EXEMPT or vat_rate == 0:
#         return {
#             "amount_net": q2(amount),
#             "vat_amount": Decimal("0.00"),
#             "amount_gross": q2(amount),
#         }

#     if vat_mode == VatMode.INCLUDED:
#         coef = Decimal("1") + vat_rate / Decimal("100")
#         net = amount / coef
#         vat = amount - net
#         return {
#             "amount_net": q2(net),
#             "vat_amount": q2(vat),
#             "amount_gross": q2(amount),
#         }

#     if vat_mode == VatMode.EXCLUDED:
#         vat = amount * vat_rate / Decimal("100")
#         gross = amount + vat
#         return {
#             "amount_net": q2(amount),
#             "vat_amount": q2(vat),
#             "amount_gross": q2(gross),
#         }

#     return {
#         "amount_net": q2(amount),
#         "vat_amount": Decimal("0.00"),
#         "amount_gross": q2(amount),
#     }


# def preview_accruals(cond, anchor_date: date) -> dict:
#     params = cond.params or {}
#     fn = cond.accrual_fn or "fixed_payments"

#     title = ACCRUAL_REGISTRY.get(fn, {}).get("title", fn)

#     if cond.date_start:
#         start = cond.date_start
#     else:
#         start = _month_start(anchor_date)

#     if cond.date_finish:
#         finish = cond.date_finish
#     else:
#         finish = _month_end(anchor_date)

#     if fn == "by_bank_statement":
#         return {
#             "condition_id": cond.id,
#             "fn": fn,
#             "title": title,
#             "period": {"from": str(start), "to": str(finish)},
#             "rows": [],
#             "note": "Начисление определяется по данным банковской выписки (cash-based).",
#         }

#     if fn == "fixed_payments":
#         amount = params.get("amount")
#         if amount is None:
#             amount = cond.amount
#         amount = Decimal(str(amount or "0"))

#         vat_rate = Decimal(str(params.get("vat_rate") or "0"))

#         rows = []
#         total_net = Decimal("0")
#         total_vat = Decimal("0")
#         total_gross = Decimal("0")

#         for m in _iter_months(start, finish):
#             m_from = _month_start(m)
#             m_to = _month_end(m)

#             p_from = max(start, m_from)
#             p_to = min(finish, m_to)

#             days_in_month = Decimal(str((m_to - m_from).days + 1))
#             days_used = Decimal(str((p_to - p_from).days + 1))

#             part = (amount * days_used / days_in_month) if days_in_month else Decimal("0")
#             part = q2(part)

#             vat_data = split_vat(part, cond.vat_mode, vat_rate)

#             total_net += vat_data["amount_net"]
#             total_vat += vat_data["vat_amount"]
#             total_gross += vat_data["amount_gross"]

#             rows.append({
#                 "period_from": str(p_from),
#                 "period_to": str(p_to),
#                 "days": int(days_used),

#                 "amount_net": str(vat_data["amount_net"]),
#                 "vat_amount": str(vat_data["vat_amount"]),
#                 "amount_gross": str(vat_data["amount_gross"]),

#                 "amount": str(vat_data["amount_gross"]),  # для совместимости
#                 "vat_rate": str(vat_rate),
#                 "vat_mode": cond.vat_mode,

#                 "comment": f"Фикс. платёж {amount} / мес • {int(days_used)}/{int(days_in_month)} дней",
#             })

#         return {
#             "condition_id": cond.id,
#             "fn": fn,
#             "title": title,
#             "period": {"from": str(start), "to": str(finish)},
#             "total_net": str(q2(total_net)),
#             "total_vat": str(q2(total_vat)),
#             "total_gross": str(q2(total_gross)),
#             "total": str(q2(total_gross)),
#             "vat_rate": str(vat_rate),
#             "vat_mode": cond.vat_mode,
#             "rows": rows,
#         }

#     if fn == "rent_premises":
#         bap = Decimal(str(params.get("bap") or "0"))
#         ep = Decimal(str(params.get("ep") or "0"))
#         area = Decimal(str(params.get("calc_area") or "0"))
#         vat_rate = Decimal(str(params.get("vat_rate") or "0"))

#         part = q2((bap + ep) * area)
#         vat_data = split_vat(part, cond.vat_mode, vat_rate)

#         return {
#             "condition_id": cond.id,
#             "fn": fn,
#             "title": title,
#             "period": {"from": str(start), "to": str(finish)},
#             "total_net": str(vat_data["amount_net"]),
#             "total_vat": str(vat_data["vat_amount"]),
#             "total_gross": str(vat_data["amount_gross"]),
#             "total": str(vat_data["amount_gross"]),
#             "vat_rate": str(vat_rate),
#             "vat_mode": cond.vat_mode,
#             "rows": [{
#                 "period_from": str(start),
#                 "period_to": str(finish),
#                 "days": "",
#                 "amount_net": str(vat_data["amount_net"]),
#                 "vat_amount": str(vat_data["vat_amount"]),
#                 "amount_gross": str(vat_data["amount_gross"]),
#                 "amount": str(vat_data["amount_gross"]),
#                 "comment": f"(БАП+ЭП)*площадь = ({bap}+{ep})*{area}",
#             }],
#         }

#     return {
#         "condition_id": cond.id,
#         "fn": fn,
#         "title": title,
#         "period": {"from": str(start), "to": str(finish)},
#         "rows": [],
#         "note": "Для этой функции пока не настроен preview.",
#     }


from .engine import preview_accruals