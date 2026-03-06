# contracts/accruals/utils.py
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from calendar import monthrange

from contracts.models import VatMode


def q2(x: Decimal) -> Decimal:
    return x.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def month_start(d: date) -> date:
    return date(d.year, d.month, 1)


def month_end(d: date) -> date:
    last_day = monthrange(d.year, d.month)[1]
    return date(d.year, d.month, last_day)


def next_month(d: date) -> date:
    if d.month == 12:
        return date(d.year + 1, 1, 1)
    return date(d.year, d.month + 1, 1)


def iter_months(start: date, finish: date):
    cur = month_start(start)
    end = month_start(finish)
    while cur <= end:
        yield cur
        cur = next_month(cur)


def resolve_period(cond, anchor_date: date):
    start = cond.date_start or month_start(anchor_date)
    finish = cond.date_finish or month_end(anchor_date)
    return start, finish


def split_vat(amount: Decimal, vat_mode: str, vat_rate: Decimal | None) -> dict:
    amount = Decimal(str(amount or "0"))
    vat_rate = Decimal(str(vat_rate or "0"))

    if vat_mode == VatMode.EXEMPT or vat_rate == 0:
        return {
            "amount_net": q2(amount),
            "vat_amount": Decimal("0.00"),
            "amount_gross": q2(amount),
        }

    if vat_mode == VatMode.INCLUDED:
        coef = Decimal("1") + vat_rate / Decimal("100")
        net = amount / coef
        vat = amount - net
        return {
            "amount_net": q2(net),
            "vat_amount": q2(vat),
            "amount_gross": q2(amount),
        }

    if vat_mode == VatMode.EXCLUDED:
        vat = amount * vat_rate / Decimal("100")
        gross = amount + vat
        return {
            "amount_net": q2(amount),
            "vat_amount": q2(vat),
            "amount_gross": q2(gross),
        }

    return {
        "amount_net": q2(amount),
        "vat_amount": Decimal("0.00"),
        "amount_gross": q2(amount),
    }