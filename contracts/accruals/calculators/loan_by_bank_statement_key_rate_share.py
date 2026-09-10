# contracts/accruals/calculators/loan_by_bank_statement_key_rate_share.py
from decimal import Decimal, InvalidOperation
from datetime import date, timedelta
import calendar

from django.db.models import Min, Max

from treasury.models import CfData, CfSplits
from macro.models import TaxesList, TaxRates, KeyRate

from ..registry import ACCRUAL_REGISTRY
from ..utils import q2


def _days_in_year_actual(d: date) -> Decimal:
    return Decimal("366") if calendar.isleap(d.year) else Decimal("365")


def _resolve_day_count_basis(current_date: date, basis: str) -> Decimal:
    """
    Поддержка:
    - "365"   -> всегда 365
    - "366"   -> всегда 366
    - "actual" / "actual_actual" -> 365/366 в зависимости от года
    """
    basis = str(basis or "365").strip().lower()

    if basis == "366":
        return Decimal("366")
    if basis in {"actual", "actual_actual", "fact", "fact_actual"}:
        return _days_in_year_actual(current_date)
    return Decimal("365")


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


def _resolve_cash_period(cond, anchor_date):
    """
    Если у условия задан date_start / date_finish -> берем их.
    Иначе ищем границы по движению денег по договору.
    """
    if cond.date_start or cond.date_finish:
        start = cond.date_start or anchor_date
        finish = cond.date_finish or anchor_date
        return start, finish

    cf_agg = CfData.objects.filter(contract=cond.contract).aggregate(
        min_date=Min("date"),
        max_date=Max("date"),
    )

    split_agg = CfSplits.objects.filter(contract=cond.contract).aggregate(
        min_date=Min("transaction__date"),
        max_date=Max("transaction__date"),
    )

    candidate_starts = [
        cf_agg.get("min_date"),
        split_agg.get("min_date"),
    ]
    candidate_finishes = [
        cf_agg.get("max_date"),
        split_agg.get("max_date"),
        date.today(),
    ]

    candidate_starts = [d for d in candidate_starts if d]
    candidate_finishes = [d for d in candidate_finishes if d]

    start = min(candidate_starts) if candidate_starts else anchor_date
    finish = max(candidate_finishes) if candidate_finishes else anchor_date

    return start, finish


def _cfitem_code(cfitem) -> str:
    if not cfitem:
        return ""
    return str(cfitem.code or "").strip()


def _flow_type(code, issue_code, principal_return_code, interest_payment_code):
    """
    issue               -> выдача тела займа
    principal_return    -> возврат тела
    interest_payment    -> оплата процентов
    """
    if code == issue_code:
        return "issue"
    if code == principal_return_code:
        return "principal_return"
    if code == interest_payment_code:
        return "interest_payment"
    return ""


def _flow_title(flow_type):
    return {
        "issue": "Выдача займа",
        "principal_return": "Возврат тела займа",
        "interest_payment": "Оплата процентов",
        "interest_accrual": "Начисление процентов",
        "ndfl_withholding": "Удержание НДФЛ",
    }.get(flow_type, "Заем")


def _iter_dates(start_date: date, end_date: date):
    current = start_date
    while current <= end_date:
        yield current
        current += timedelta(days=1)


def _group_cash_flows_by_date(cash_flows: list[dict]) -> dict[date, list[dict]]:
    result = {}
    for row in cash_flows:
        d = row["flow_date"]
        result.setdefault(d, []).append(row)
    return result


def _to_decimal(value, default="0.00") -> Decimal:
    if value is None or value == "":
        return Decimal(default)
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _to_int(value, default=0) -> int:
    if value is None or value == "":
        return default
    return int(value)


def _get_ndfl_brackets_from_model(anchor_date: date, tax_name: str = "НДФЛ") -> list[dict]:
    """
    Берем прогрессивную шкалу НДФЛ из модели TaxRates.
    """
    tax = TaxesList.objects.filter(tax_name=tax_name).first()
    if not tax:
        raise ValueError(f"Не найден налог '{tax_name}' в справочнике TaxesList.")

    effective_date = (
        TaxRates.objects
        .filter(tax=tax, date__lte=anchor_date)
        .aggregate(max_date=Max("date"))
        .get("max_date")
    )

    if not effective_date:
        raise ValueError(
            f"Для налога '{tax_name}' не найдены ставки на дату {anchor_date} "
            f"(или ранее) в модели TaxRates."
        )

    rate_rows = list(
        TaxRates.objects
        .filter(tax=tax, date=effective_date)
        .order_by("id")
    )

    if not rate_rows:
        raise ValueError(
            f"Для налога '{tax_name}' не найдены строки ставок на дату {effective_date}."
        )

    brackets = []
    for row in rate_rows:
        rate_dec = q2(_to_decimal(row.rate))
        if rate_dec <= 0:
            continue

        limit_dec = None
        if row.income_limit is not None:
            limit_dec = q2(_to_decimal(row.income_limit))

        brackets.append({
            "limit": limit_dec,
            "rate": rate_dec,
            "effective_date": effective_date,
            "tax_name": tax_name,
            "comment": row.comment or "",
        })

    if not brackets:
        raise ValueError(
            f"Для налога '{tax_name}' на дату {effective_date} нет корректных ставок."
        )

    brackets.sort(
        key=lambda x: (
            x["limit"] is None,
            x["limit"] if x["limit"] is not None else Decimal("999999999999999999.99"),
        )
    )

    return brackets


def _calculate_progressive_tax(amount: Decimal, brackets: list[dict]) -> tuple[Decimal, list[dict]]:
    amount = q2(amount)

    if amount <= 0:
        return Decimal("0.00"), []

    if not brackets:
        raise ValueError("Не передана шкала ставок НДФЛ.")

    total_tax = Decimal("0.00")
    prev_limit = Decimal("0.00")
    breakdown = []
    remaining = amount

    for bracket in brackets:
        upper_limit = bracket["limit"]
        rate = q2(_to_decimal(bracket["rate"]))

        if remaining <= 0:
            break

        if upper_limit is None:
            taxable_part = remaining
            range_from = prev_limit
            range_to = None
        else:
            band_amount = q2(upper_limit - prev_limit)

            if band_amount <= 0:
                continue

            taxable_part = min(remaining, band_amount)
            range_from = prev_limit
            range_to = upper_limit

        if taxable_part <= 0:
            continue

        tax_amount = q2(taxable_part * rate / Decimal("100"))

        breakdown.append({
            "from_amount": q2(range_from),
            "to_amount": q2(range_to) if range_to is not None else None,
            "taxable_amount": q2(taxable_part),
            "rate": q2(rate),
            "tax_amount": q2(tax_amount),
        })

        total_tax += tax_amount
        remaining -= taxable_part

        if upper_limit is not None:
            prev_limit = upper_limit

    return q2(total_tax), breakdown


def _get_key_rate_on(current_date: date) -> dict:
    """
    Берем последнюю действующую ключевую ставку на дату.
    Логика именно такая, как вы описали:
    если появилась новая дата начала действия, старая ставка больше не работает.
    """
    row = (
        KeyRate.objects
        .filter(date__lte=current_date)
        .order_by("-date")
        .first()
    )

    if not row:
        raise ValueError(
            f"Не найдена ключевая ставка на дату {current_date} "
            f"(или ранее) в модели KeyRate."
        )

    return {
        "effective_date": row.date,
        "key_rate": q2(_to_decimal(row.key_rate)),
        "comment": row.comment or "",
    }


def preview(cond, anchor_date):
    """
    Логика:
    1. Из выписки читаем:
       - выдачу займа
       - возврат тела
       - оплату процентов
    2. Проценты начисляем ежедневно на фактический остаток тела.
    3. Годовая ставка на каждый день = ключевая ставка на эту дату * (числитель / знаменатель)
       Например: 2/3 ключевой ставки.
    4. В total попадают только начисленные проценты.
    5. НДФЛ считаем только от начисленных процентов.
    """
    params = cond.params or {}
    withholding_ndfl = bool(params.get("withholding_ndfl", False))

    fn = "loan_by_bank_statement_key_rate_share"
    title = ACCRUAL_REGISTRY.get(fn, {}).get("title", fn)

    start, finish = _resolve_cash_period(cond, anchor_date)

    vat_rate = q2(_to_decimal(params.get("vat_rate") or "0"))

    key_rate_numerator = _to_int(params.get("key_rate_numerator"), 2)
    key_rate_denominator = _to_int(params.get("key_rate_denominator"), 3)

    if key_rate_denominator == 0:
        raise ValueError("Знаменатель доли ключевой ставки не может быть равен 0.")

    share_multiplier = (
        Decimal(str(key_rate_numerator)) / Decimal(str(key_rate_denominator))
    )

    issue_cf_code = str(params.get("issue_cf_code") or "").strip()
    principal_return_cf_code = str(params.get("principal_return_cf_code") or "").strip()
    interest_payment_cf_code = str(params.get("interest_payment_cf_code") or "").strip()

    interest_start_mode = str(params.get("interest_start_mode") or "next_day").strip()
    if interest_start_mode not in {"same_day", "next_day"}:
        interest_start_mode = "next_day"

    day_count_basis_mode = str(params.get("day_count_basis") or "actual").strip().lower()
    ndfl_tax_name = str(params.get("ndfl_tax_name") or "НДФЛ").strip()

    rows = []

    issued_total = Decimal("0.00")
    principal_returned_total = Decimal("0.00")
    interest_paid_total = Decimal("0.00")
    interest_accrued_total = Decimal("0.00")
    ndfl_withheld_total = Decimal("0.00")
    ndfl_breakdown = []
    ndfl_brackets = []

    used_transaction_ids = set()
    cash_flows = []

    # ---------------------------------------------------------
    # 1. Сначала сплиты
    # ---------------------------------------------------------
    split_qs = (
        CfSplits.objects
        .select_related("transaction", "contract", "cfitem")
        .filter(
            contract=cond.contract,
            transaction__date__gte=start,
            transaction__date__lte=finish,
        )
        .order_by("transaction__date", "id")
    )

    for s in split_qs:
        amount = _payment_amount_from_split(s)
        if amount <= 0:
            continue

        used_transaction_ids.add(s.transaction_id)

        code = _cfitem_code(s.cfitem)
        flow_type = _flow_type(
            code,
            issue_cf_code,
            principal_return_cf_code,
            interest_payment_cf_code,
        )
        if not flow_type:
            continue

        cash_flows.append({
            "flow_date": s.transaction.date,
            "flow_type": flow_type,
            "amount": q2(amount),
            "cf_code": code,
            "cf_name": s.cfitem.name if s.cfitem else "",
            "comment": f"{_flow_title(flow_type)} / сплит #{s.transaction_id}",
        })

    # ---------------------------------------------------------
    # 2. Потом прямые CfData, которых нет в сплитах
    # ---------------------------------------------------------
    cf_qs = (
        CfData.objects
        .select_related("contract", "cfitem")
        .filter(
            contract=cond.contract,
            date__gte=start,
            date__lte=finish,
        )
        .exclude(id__in=used_transaction_ids)
        .order_by("date", "id")
    )

    for p in cf_qs:
        amount = _payment_amount_from_cfdata(p)
        if amount <= 0:
            continue

        code = _cfitem_code(p.cfitem)
        flow_type = _flow_type(
            code,
            issue_cf_code,
            principal_return_cf_code,
            interest_payment_cf_code,
        )
        if not flow_type:
            continue

        cash_flows.append({
            "flow_date": p.date,
            "flow_type": flow_type,
            "amount": q2(amount),
            "cf_code": code,
            "cf_name": p.cfitem.name if p.cfitem else "",
            "comment": f"{_flow_title(flow_type)} #{p.id}",
        })

    cash_flows.sort(key=lambda x: (x["flow_date"], x["flow_type"], x["amount"]))

    # ---------------------------------------------------------
    # 3. Считаем ежедневные начисления процентов
    # ---------------------------------------------------------
    flow_map = _group_cash_flows_by_date(cash_flows)
    principal_balance = Decimal("0.00")
    accrual_rows = []

    for current_date in _iter_dates(start, finish):
        current_flows = flow_map.get(current_date, [])

        if interest_start_mode == "same_day":
            for f in current_flows:
                if f["flow_type"] == "issue":
                    principal_balance += q2(f["amount"])
                elif f["flow_type"] == "principal_return":
                    principal_balance -= q2(f["amount"])

        if principal_balance < 0:
            principal_balance = Decimal("0.00")

        key_rate_data = _get_key_rate_on(current_date)
        key_rate = _to_decimal(key_rate_data["key_rate"])

        annual_rate_raw = key_rate * share_multiplier
        annual_rate = q2(annual_rate_raw)

        day_count_basis = _resolve_day_count_basis(current_date, day_count_basis_mode)

        daily_interest = q2(
            principal_balance * annual_rate_raw / Decimal("100") / day_count_basis
        )

        if daily_interest > 0:
            interest_accrued_total += daily_interest
            accrual_rows.append({
                "accrual_date": current_date,
                "period_from": current_date,
                "period_to": current_date,
                "days": 1,
                "amount_net": daily_interest,
                "vat_amount": Decimal("0.00"),
                "amount_gross": daily_interest,
                "amount": daily_interest,
                "vat_rate": vat_rate,
                "vat_mode": getattr(cond, "vat_mode", "no_vat"),
                "flow_type": "interest_accrual",
                "cf_code": "",
                "cf_name": "",
                "comment": (
                    f"Начисление процентов на остаток тела займа "
                    f"по ставке {key_rate_numerator}/{key_rate_denominator} "
                    f"от ключевой ставки"
                ),
                "principal_balance": q2(principal_balance),
                "key_rate": q2(key_rate),
                "annual_rate": q2(annual_rate),
                "rate_multiplier": share_multiplier,
                "key_rate_effective_date": key_rate_data["effective_date"],
                "day_count_basis": q2(day_count_basis),
            })

        if interest_start_mode == "next_day":
            for f in current_flows:
                if f["flow_type"] == "issue":
                    principal_balance += q2(f["amount"])
                elif f["flow_type"] == "principal_return":
                    principal_balance -= q2(f["amount"])

        if principal_balance < 0:
            principal_balance = Decimal("0.00")

    interest_accrued_total = q2(interest_accrued_total)

    # ---------------------------------------------------------
    # 4. Движения из выписки
    # ---------------------------------------------------------
    for f in cash_flows:
        if f["flow_type"] == "issue":
            issued_total += q2(f["amount"])

            rows.append({
                "accrual_date": f["flow_date"],
                "period_from": f["flow_date"],
                "period_to": f["flow_date"],
                "days": 1,
                "amount_net": q2(f["amount"]),
                "vat_amount": Decimal("0.00"),
                "amount_gross": q2(f["amount"]),
                "amount": q2(f["amount"]),
                "vat_rate": vat_rate,
                "vat_mode": getattr(cond, "vat_mode", "no_vat"),
                "flow_type": "issue",
                "cf_code": f["cf_code"],
                "cf_name": f["cf_name"],
                "comment": f["comment"],
            })
            continue

        if f["flow_type"] == "principal_return":
            principal_returned_total += q2(f["amount"])

            rows.append({
                "accrual_date": f["flow_date"],
                "period_from": f["flow_date"],
                "period_to": f["flow_date"],
                "days": 1,
                "amount_net": q2(f["amount"]),
                "vat_amount": Decimal("0.00"),
                "amount_gross": q2(f["amount"]),
                "amount": q2(f["amount"]),
                "vat_rate": vat_rate,
                "vat_mode": getattr(cond, "vat_mode", "no_vat"),
                "flow_type": "principal_return",
                "cf_code": f["cf_code"],
                "cf_name": f["cf_name"],
                "comment": f["comment"],
            })
            continue

        if f["flow_type"] == "interest_payment":
            payment_amount = q2(f["amount"])
            interest_paid_total += payment_amount

            rows.append({
                "accrual_date": f["flow_date"],
                "period_from": f["flow_date"],
                "period_to": f["flow_date"],
                "days": 1,
                "amount_net": payment_amount,
                "vat_amount": Decimal("0.00"),
                "amount_gross": payment_amount,
                "amount": payment_amount,
                "vat_rate": vat_rate,
                "vat_mode": getattr(cond, "vat_mode", "no_vat"),
                "flow_type": "interest_payment",
                "cf_code": f["cf_code"],
                "cf_name": f["cf_name"],
                "comment": "Оплата процентов",
            })
            continue

    # ---------------------------------------------------------
    # 5. Добавляем начисления процентов
    # ---------------------------------------------------------
    rows.extend(accrual_rows)

    # ---------------------------------------------------------
    # 6. НДФЛ только от начисленных процентов
    # ---------------------------------------------------------
    if withholding_ndfl and interest_accrued_total > 0:
        ndfl_brackets = _get_ndfl_brackets_from_model(
            anchor_date=anchor_date,
            tax_name=ndfl_tax_name,
        )

        ndfl_withheld_total, ndfl_breakdown = _calculate_progressive_tax(
            amount=interest_accrued_total,
            brackets=ndfl_brackets,
        )

        if ndfl_withheld_total > interest_accrued_total:
            raise ValueError(
                f"НДФЛ ({ndfl_withheld_total}) не может быть больше начисленных процентов "
                f"({interest_accrued_total}). Проверь ставки налога '{ndfl_tax_name}'."
            )

        if ndfl_withheld_total > 0:
            rows.append({
                "accrual_date": finish,
                "period_from": finish,
                "period_to": finish,
                "days": 1,
                "amount_net": ndfl_withheld_total,
                "vat_amount": Decimal("0.00"),
                "amount_gross": ndfl_withheld_total,
                "amount": ndfl_withheld_total,
                "vat_rate": Decimal("0.00"),
                "vat_mode": "no_vat",
                "flow_type": "ndfl_withholding",
                "cf_code": "",
                "cf_name": "",
                "comment": (
                    "Удержан НДФЛ с начисленных процентов по займу "
                    "по ставке, привязанной к ключевой ставке"
                ),
            })

    issued_total = q2(issued_total)
    principal_returned_total = q2(principal_returned_total)
    interest_paid_total = q2(interest_paid_total)
    ndfl_withheld_total = q2(ndfl_withheld_total)

    principal_outstanding = q2(issued_total - principal_returned_total)
    interest_outstanding = q2(interest_accrued_total - interest_paid_total)

    rows.sort(
        key=lambda x: (
            x.get("accrual_date") or x.get("period_from") or start,
            x.get("flow_type") or "",
            x.get("comment") or "",
        )
    )

    return {
        "condition_id": cond.id,
        "fn": fn,
        "title": title,
        "period": {"from": start, "to": finish},

        "total_net": q2(interest_accrued_total),
        "total_vat": Decimal("0.00"),
        "total_gross": q2(interest_accrued_total),
        "total": q2(interest_accrued_total),

        "issued_total": issued_total,
        "principal_returned_total": principal_returned_total,
        "principal_outstanding": principal_outstanding,

        "interest_accrued_total": interest_accrued_total,
        "interest_paid_total": interest_paid_total,
        "interest_outstanding": interest_outstanding,

        "ndfl_withheld_total": ndfl_withheld_total,
        "ndfl_brackets": ndfl_brackets,
        "ndfl_breakdown": ndfl_breakdown,

        "key_rate_numerator": key_rate_numerator,
        "key_rate_denominator": key_rate_denominator,
        "rate_multiplier": share_multiplier,

        "vat_rate": vat_rate,
        "vat_mode": getattr(cond, "vat_mode", "no_vat"),
        "rows": rows,
        "note": (
            f"Проценты по займу рассчитаны на фактический остаток тела займа "
            f"по ставке {key_rate_numerator}/{key_rate_denominator} от ключевой ставки. "
            f"Ключевая ставка определяется по модели KeyRate на каждую дату начисления. "
            f"НДФЛ рассчитан только от начисленных процентов по прогрессивной шкале "
            f"из модели TaxRates."
        ),
    }