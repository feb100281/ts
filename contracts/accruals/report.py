# contracts/accruals/report.py
from datetime import date, datetime
from calendar import monthrange
from decimal import Decimal

from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Q

from contracts.models import Conditions
from contracts.accruals.engine import preview_accruals


MONTHS_RU_NOMINATIVE = {
    1: "январь",
    2: "февраль",
    3: "март",
    4: "апрель",
    5: "май",
    6: "июнь",
    7: "июль",
    8: "август",
    9: "сентябрь",
    10: "октябрь",
    11: "ноябрь",
    12: "декабрь",
}


def to_decimal(val):
    if val is None or val == "":
        return Decimal("0")
    try:
        return Decimal(str(val))
    except Exception:
        return Decimal("0")


def format_money(val: Decimal) -> str:
    if val is None:
        val = Decimal("0")
    return f"{val:,.2f}".replace(",", " ").replace(".", ",")


def _safe_date(value):
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

        try:
            return date.fromisoformat(value)
        except Exception:
            pass

    return None


def _is_deposit_condition(cond: Conditions) -> bool:
    return (cond.accrual_fn or "") == "deposit_by_bank_statement"


def _is_deposit_principal_flow(flow_type: str) -> bool:
    return flow_type in {"placement", "principal_return"}


def get_report_period(request):
    month_str = request.GET.get("month")

    if month_str:
        try:
            year_str, month_str_only = month_str.split("-")
            year = int(year_str)
            month = int(month_str_only)
            if not (1 <= month <= 12):
                raise ValueError
            return year, month, month_str
        except Exception:
            pass

    today = date.today()
    return today.year, today.month, f"{today.year:04d}-{today.month:02d}"


def pluralize_contracts(count: int) -> str:
    n = abs(count) % 100
    n1 = n % 10
    if 11 <= n <= 19:
        return "договоров"
    if n1 == 1:
        return "договор"
    if 2 <= n1 <= 4:
        return "договора"
    return "договоров"


@staff_member_required
def accruals_report(request):
    year, month, selected_month = get_report_period(request)

    start_date = date(year, month, 1)
    end_date = date(year, month, monthrange(year, month)[1])

    qs = (
        Conditions.objects
        .select_related("contract", "contract__cp", "accounting_method")
        .filter(
            Q(date_start__isnull=True) | Q(date_start__lte=end_date)
        )
        .filter(
            Q(date_finish__isnull=True) | Q(date_finish__gte=start_date)
        )
        .order_by("contract__cp__name", "contract__number", "date_start")
    )

    rows = []

    for cond in qs:
        contract = cond.contract
        cp = getattr(contract, "cp", None)

        preview = preview_accruals(cond, anchor_date=end_date)
        preview_rows = preview.get("rows", []) or []

        month_sum = Decimal("0")

        for r in preview_rows:
            flow_type = (r.get("flow_type") or "").strip()

            # Для депозитов берем только проценты,
            # размещение и возврат тела депозита исключаем
            if _is_deposit_condition(cond) and _is_deposit_principal_flow(flow_type):
                continue

            row_date = (
                r.get("accrual_date")
                or r.get("period_from")
                or r.get("date")
                or r.get("period_date")
                or r.get("start")
                or r.get("period_start")
            )

            row_amount = (
                r.get("amount_gross")
                or r.get("amount")
                or r.get("sum")
                or r.get("accrual")
                or r.get("value")
                or 0
            )

            parsed_date = _safe_date(row_date)
            if not parsed_date:
                continue

            if parsed_date.year == year and parsed_date.month == month:
                month_sum += to_decimal(row_amount)

        rows.append({
            "contragent": getattr(cp, "name", "—") or "—",
            "contract_number": contract.number or "без номера",
            "contract_title": str(contract.title) if contract.title else "—",
            "method": cond.accounting_method.name if cond.accounting_method else "—",
            "amount_raw": month_sum,
            "amount": format_money(month_sum),
            "date_start": cond.date_start,
            "date_finish": cond.date_finish,
            "condition_id": cond.id,
            "contract_id": getattr(contract, "id", None),
        })

    rows = [r for r in rows if r["amount_raw"] != Decimal("0")]
    total_raw = sum((r["amount_raw"] for r in rows), Decimal("0"))

    # Accrual / Accural — учитываем оба написания
    accrual_rows = [
        r for r in rows
        if str(r.get("method", "")).strip().lower() in {"accrual", "accural"}
    ]

    accrual_total_raw = sum((r["amount_raw"] for r in accrual_rows), Decimal("0"))

    # Считаем уникальные договоры, а не строки
    accrual_contract_ids = {
        r["contract_id"] for r in accrual_rows if r.get("contract_id")
    }
    accrual_count = len(accrual_contract_ids)

    month_label = f"{MONTHS_RU_NOMINATIVE[month]} {year}"

    return render(
        request,
        "contracts/accruals_report.html",
        {
            "rows": rows,
            "total": format_money(total_raw),
            "total_raw": total_raw,
            "month_label": month_label,
            "start_date": start_date,
            "end_date": end_date,
            "selected_month": selected_month,
            "accrual_count": accrual_count,
            "accrual_count_label": pluralize_contracts(accrual_count),
            "accrual_total": format_money(accrual_total_raw),
        },
    )




