# grossbook/reporting/loan_adjustment_pdf.py

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from pathlib import Path
from urllib.parse import quote

from django.conf import settings
from django.db import connection
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils import timezone
from weasyprint import CSS, HTML


# =====================================================================
# ОБЩИЕ ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# =====================================================================


def _to_decimal(
    value,
    default: Decimal = Decimal("0"),
) -> Decimal:
    """
    Безопасно приводит значение к Decimal.
    """

    if value is None:
        return default

    if isinstance(value, Decimal):
        return value

    return Decimal(
        str(value)
    )


def _money(
    value,
) -> str:
    """
    Форматирует сумму:

    1234567.89 -> 1 234 567.89
    """

    amount = _to_decimal(
        value
    )

    return (
        f"{amount:,.2f}"
        .replace(
            ",",
            " ",
        )
    )


def _signed_money(
    value,
) -> str:
    """
    Форматирует изменение суммы со знаком.

    100    -> +100.00
    -100   -> −100.00
    0      -> 0.00
    None   -> —
    """

    if value is None:
        return "—"

    amount = _to_decimal(
        value
    )

    if amount > 0:
        sign = "+"

    elif amount < 0:
        sign = "−"

    else:
        sign = ""

    return (
        f"{sign}{_money(abs(amount))}"
    )


def _current_datetime():
    """
    Работает как при USE_TZ=True,
    так и при USE_TZ=False.
    """

    current = timezone.now()

    if timezone.is_aware(
        current
    ):
        return timezone.localtime(
            current
        )

    return current


def _counterparty_name(
    contract,
) -> str:
    counterparty = getattr(
        contract,
        "cp",
        None,
    )

    if counterparty is None:
        return str(
            contract
        )

    return (
        getattr(
            counterparty,
            "name",
            None,
        )
        or str(counterparty)
    )


def _contract_number(
    contract,
) -> str:
    return (
        getattr(
            contract,
            "number",
            None,
        )
        or "б/н"
    )


def _contract_date(
    contract,
):
    return (
        getattr(
            contract,
            "date",
            None,
        )
        or getattr(
            contract,
            "date_start",
            None,
        )
    )


def _contract_currency(
    contract,
) -> str:
    return (
        getattr(
            contract,
            "currency",
            None,
        )
        or "RUB"
    )


def _author_name(
    adjustment,
) -> str:
    user = adjustment.created_by

    if not user:
        return "Не указан"

    full_name = (
        user
        .get_full_name()
        .strip()
    )

    return (
        full_name
        or user.get_username()
    )


# =====================================================================
# ПОЛУЧЕНИЕ СОСТОЯНИЯ ДО КОРРЕКТИРОВКИ
# =====================================================================


def _get_adjustment_comparison(
    adjustment,
) -> dict:
    """
    Возвращает:

    - расчётное состояние до ручной корректировки;
    - состояние после корректировки;
    - величину изменения.

    В gl.borrowings_tp денежные значения хранятся
    в минимальных единицах валюты — для рублей в копейках.

    Остаток тела до корректировки:

        bb
        + drawdown_amount
        - principal_repayment

    Остаток процентов до корректировки:

        interest_balance предыдущего дня
        + interest_accrued текущего дня
        - interest_repayment текущего дня
    """

    contract_id = (
        adjustment.contract_id
    )

    adjustment_date = (
        adjustment.adjustment_date
    )

    principal_after = _to_decimal(
        adjustment.principal_balance
    )

    interest_after = _to_decimal(
        adjustment.interest_balance
    )

    total_after = (
        principal_after
        + interest_after
    )

    with connection.cursor() as cursor:
        cursor.execute(
            """
            WITH current_day AS (
                SELECT
                    date_from,
                    contract_id,
                    COALESCE(
                        bb,
                        0
                    ) AS bb,
                    COALESCE(
                        drawdown_amount,
                        0
                    ) AS drawdown_amount,
                    COALESCE(
                        principal_repayment,
                        0
                    ) AS principal_repayment,
                    COALESCE(
                        interest_accrued,
                        0
                    ) AS interest_accrued,
                    COALESCE(
                        interest_repayment,
                        0
                    ) AS interest_repayment
                FROM gl.borrowings_tp
                WHERE
                    contract_id = %s
                    AND date_from::date = %s
                ORDER BY date_from DESC
                LIMIT 1
            ),

            previous_day AS (
                SELECT
                    COALESCE(
                        interest_balance,
                        0
                    ) AS interest_balance
                FROM gl.borrowings_tp
                WHERE
                    contract_id = %s
                    AND date_from::date < %s
                ORDER BY date_from DESC
                LIMIT 1
            )

            SELECT
                current_day.bb,
                current_day.drawdown_amount,
                current_day.principal_repayment,
                current_day.interest_accrued,
                current_day.interest_repayment,
                COALESCE(
                    previous_day.interest_balance,
                    0
                ) AS previous_interest_balance
            FROM current_day
            LEFT JOIN previous_day
                ON TRUE
            """,
            [
                contract_id,
                adjustment_date,
                contract_id,
                adjustment_date,
            ],
        )

        row = cursor.fetchone()

    # Договор ещё не был пересчитан либо на дату
    # корректировки отсутствует строка в borrowings_tp.
    if row is None:
        return {
            "has_calculation": False,

            "principal_before": None,
            "interest_before": None,
            "total_before": None,

            "principal_after": principal_after,
            "interest_after": interest_after,
            "total_after": total_after,

            "principal_delta": None,
            "interest_delta": None,
            "total_delta": None,
        }

    (
        bb,
        drawdown_amount,
        principal_repayment,
        interest_accrued,
        interest_repayment,
        previous_interest_balance,
    ) = row

    divider = Decimal(
        "100"
    )

    # ---------------------------------------------------------------
    # Тело до ручной корректировки
    # ---------------------------------------------------------------

    principal_before = (
        _to_decimal(
            bb
        )
        + _to_decimal(
            drawdown_amount
        )
        - _to_decimal(
            principal_repayment
        )
    ) / divider

    # ---------------------------------------------------------------
    # Проценты до ручной корректировки
    # ---------------------------------------------------------------

    interest_before = (
        _to_decimal(
            previous_interest_balance
        )
        + _to_decimal(
            interest_accrued
        )
        - _to_decimal(
            interest_repayment
        )
    ) / divider

    # Убираем возможный технический минус
    # от округлений в копейках.
    principal_before = max(
        principal_before,
        Decimal("0"),
    )

    interest_before = max(
        interest_before,
        Decimal("0"),
    )

    total_before = (
        principal_before
        + interest_before
    )

    principal_delta = (
        principal_after
        - principal_before
    )

    interest_delta = (
        interest_after
        - interest_before
    )

    total_delta = (
        total_after
        - total_before
    )

    return {
        "has_calculation": True,

        "principal_before": principal_before,
        "interest_before": interest_before,
        "total_before": total_before,

        "principal_after": principal_after,
        "interest_after": interest_after,
        "total_after": total_after,

        "principal_delta": principal_delta,
        "interest_delta": interest_delta,
        "total_delta": total_delta,
    }


# =====================================================================
# ФОРМИРОВАНИЕ PDF
# =====================================================================


def _render_pdf(
    template_name: str,
    context: dict,
) -> bytes:
    html = render_to_string(
        template_name,
        context,
    )

    css_path = (
        Path(
            settings.BASE_DIR
        )
        / "static"
        / "css"
        / "loan_adjustments"
        / "pdf.css"
    )

    stylesheets = []

    if css_path.exists():
        stylesheets.append(
            CSS(
                filename=str(
                    css_path
                )
            )
        )

    return HTML(
        string=html,
        base_url=str(
            settings.BASE_DIR
        ),
    ).write_pdf(
        stylesheets=stylesheets,
        presentational_hints=True,
    )


def _pdf_response(
    pdf_bytes: bytes,
    filename: str,
    *,
    inline: bool,
) -> HttpResponse:
    response = HttpResponse(
        pdf_bytes,
        content_type="application/pdf",
    )

    disposition = (
        "inline"
        if inline
        else "attachment"
    )

    encoded_filename = quote(
        filename
    )

    response[
        "Content-Disposition"
    ] = (
        f"{disposition}; "
        f"filename*=UTF-8''{encoded_filename}"
    )

    response[
        "Content-Length"
    ] = str(
        len(pdf_bytes)
    )

    return response


# =====================================================================
# PDF ПО ОДНОЙ КОРРЕКТИРОВКЕ
# =====================================================================


def generate_loan_adjustment_pdf(
    adjustment,
) -> HttpResponse:
    contract = (
        adjustment.contract
    )

    comparison = (
        _get_adjustment_comparison(
            adjustment
        )
    )

    principal_after = (
        comparison[
            "principal_after"
        ]
    )

    interest_after = (
        comparison[
            "interest_after"
        ]
    )

    total_after = (
        comparison[
            "total_after"
        ]
    )

    context = {
        "company": getattr(
            settings,
            "COMPANY_LEGAL_NAME",
            'ООО "ТРЕНДСЕТТЕР"',
        ),

        "document_number": (
            f"КЗ-{adjustment.pk:06d}"
        ),

        "adjustment": adjustment,

        "counterparty": (
            _counterparty_name(
                contract
            )
        ),

        "contract_number": (
            _contract_number(
                contract
            )
        ),

        "contract_date": (
            _contract_date(
                contract
            )
        ),

        "currency": (
            _contract_currency(
                contract
            )
        ),

        "reason_text": (
            adjustment
            .get_reason_display()
        ),

        "author": (
            _author_name(
                adjustment
            )
        ),

        "generated_at": (
            _current_datetime()
        ),

        "status_text": (
            "Учитывается в расчёте"
            if adjustment.is_active
            else "Не учитывается в расчёте"
        ),

        # -------------------------------------------------------------
        # Полный словарь сравнения
        # -------------------------------------------------------------

        "comparison": comparison,

        # -------------------------------------------------------------
        # До корректировки
        # -------------------------------------------------------------

        "principal_before_text": (
            _money(
                comparison[
                    "principal_before"
                ]
            )
            if comparison[
                "principal_before"
            ] is not None
            else "—"
        ),

        "interest_before_text": (
            _money(
                comparison[
                    "interest_before"
                ]
            )
            if comparison[
                "interest_before"
            ] is not None
            else "—"
        ),

        "total_before_text": (
            _money(
                comparison[
                    "total_before"
                ]
            )
            if comparison[
                "total_before"
            ] is not None
            else "—"
        ),

        # -------------------------------------------------------------
        # После корректировки
        # -------------------------------------------------------------

        "principal_after_text": (
            _money(
                principal_after
            )
        ),

        "interest_after_text": (
            _money(
                interest_after
            )
        ),

        "total_after_text": (
            _money(
                total_after
            )
        ),

        # Для совместимости со старым шаблоном
        "principal_text": (
            _money(
                principal_after
            )
        ),

        "interest_text": (
            _money(
                interest_after
            )
        ),

        "total_balance_text": (
            _money(
                total_after
            )
        ),

        # -------------------------------------------------------------
        # Изменение
        # -------------------------------------------------------------

        "principal_delta_text": (
            _signed_money(
                comparison[
                    "principal_delta"
                ]
            )
        ),

        "interest_delta_text": (
            _signed_money(
                comparison[
                    "interest_delta"
                ]
            )
        ),

        "total_delta_text": (
            _signed_money(
                comparison[
                    "total_delta"
                ]
            )
        ),
    }

    pdf_bytes = _render_pdf(
        (
            "reporting/"
            "loan_adjustments/"
            "document.html"
        ),
        context,
    )

    filename = (
        "Справка_по_корректировке_займа_"
        f"{adjustment.pk}_"
        f"{adjustment.adjustment_date:%Y%m%d}.pdf"
    )

    # ВАЖНО:
    # функция обязательно возвращает HttpResponse.
    return _pdf_response(
        pdf_bytes,
        filename,
        inline=True,
    )


# =====================================================================
# ОБЩИЙ PDF ПО ВЫБРАННЫМ КОРРЕКТИРОВКАМ
# =====================================================================


def generate_loan_adjustments_registry_pdf(
    queryset,
) -> HttpResponse:
    """
    Формирует общий PDF-реестр выбранных корректировок.

    По каждой корректировке показывает:
    - расчётное состояние до корректировки;
    - состояние после корректировки;
    - величину изменения.
    """

    adjustments = list(
        queryset
        .select_related(
            "contract",
            "contract__cp",
            "created_by",
        )
        .order_by(
            "adjustment_date",
            "id",
        )
    )

    rows = []

    principal_before_total = Decimal("0")
    principal_after_total = Decimal("0")
    principal_delta_total = Decimal("0")

    interest_before_total = Decimal("0")
    interest_after_total = Decimal("0")
    interest_delta_total = Decimal("0")

    debt_before_total = Decimal("0")
    debt_after_total = Decimal("0")
    debt_delta_total = Decimal("0")

    rows_without_calculation = 0

    for adjustment in adjustments:
        contract = adjustment.contract

        comparison = _get_adjustment_comparison(
            adjustment
        )

        has_calculation = bool(
            comparison["has_calculation"]
        )

        principal_before = (
            comparison["principal_before"]
            if has_calculation
            else None
        )

        interest_before = (
            comparison["interest_before"]
            if has_calculation
            else None
        )

        total_before = (
            comparison["total_before"]
            if has_calculation
            else None
        )

        principal_after = _to_decimal(
            comparison["principal_after"]
        )

        interest_after = _to_decimal(
            comparison["interest_after"]
        )

        total_after = _to_decimal(
            comparison["total_after"]
        )

        principal_delta = (
            comparison["principal_delta"]
            if has_calculation
            else None
        )

        interest_delta = (
            comparison["interest_delta"]
            if has_calculation
            else None
        )

        total_delta = (
            comparison["total_delta"]
            if has_calculation
            else None
        )

        if has_calculation:
            principal_before_total += _to_decimal(
                principal_before
            )

            interest_before_total += _to_decimal(
                interest_before
            )

            debt_before_total += _to_decimal(
                total_before
            )

            principal_delta_total += _to_decimal(
                principal_delta
            )

            interest_delta_total += _to_decimal(
                interest_delta
            )

            debt_delta_total += _to_decimal(
                total_delta
            )

        else:
            rows_without_calculation += 1

        principal_after_total += principal_after
        interest_after_total += interest_after
        debt_after_total += total_after

        author = _author_name(
            adjustment
        )

        rows.append(
            {
                "document_number": (
                    f"КЗ-{adjustment.pk:06d}"
                ),

                "date": (
                    adjustment.adjustment_date
                ),

                "counterparty": (
                    _counterparty_name(
                        contract
                    )
                ),

                "contract_number": (
                    _contract_number(
                        contract
                    )
                ),

                "contract_date": (
                    _contract_date(
                        contract
                    )
                ),

                "currency": (
                    _contract_currency(
                        contract
                    )
                ),

                "reason": (
                    adjustment
                    .get_reason_display()
                ),

                "comment": (
                    adjustment.comment
                    or ""
                ),

                "author": author,

                "is_active": (
                    adjustment.is_active
                ),

                "has_calculation": (
                    has_calculation
                ),

                # Тело
                "principal_before_text": (
                    _money(
                        principal_before
                    )
                    if principal_before is not None
                    else "—"
                ),

                "principal_after_text": (
                    _money(
                        principal_after
                    )
                ),

                "principal_delta_text": (
                    _signed_money(
                        principal_delta
                    )
                ),

                # Проценты
                "interest_before_text": (
                    _money(
                        interest_before
                    )
                    if interest_before is not None
                    else "—"
                ),

                "interest_after_text": (
                    _money(
                        interest_after
                    )
                ),

                "interest_delta_text": (
                    _signed_money(
                        interest_delta
                    )
                ),

                # Общая задолженность
                "total_before_text": (
                    _money(
                        total_before
                    )
                    if total_before is not None
                    else "—"
                ),

                "total_after_text": (
                    _money(
                        total_after
                    )
                ),

                "total_delta_text": (
                    _signed_money(
                        total_delta
                    )
                ),

                # Используем для цвета изменения
                "principal_delta": (
                    principal_delta
                ),

                "interest_delta": (
                    interest_delta
                ),

                "total_delta": (
                    total_delta
                ),
            }
        )

    context = {
        "company": getattr(
            settings,
            "COMPANY_LEGAL_NAME",
            'ООО "ТРЕНДСЕТТЕР"',
        ),

        "title": (
            "Реестр корректировок займов"
        ),

        "generated_at": (
            _current_datetime()
        ),

        "rows": rows,

        "records_count": len(
            rows
        ),

        "rows_without_calculation": (
            rows_without_calculation
        ),

        # Итоги по телу
        "principal_before_total_text": (
            _money(
                principal_before_total
            )
        ),

        "principal_after_total_text": (
            _money(
                principal_after_total
            )
        ),

        "principal_delta_total_text": (
            _signed_money(
                principal_delta_total
            )
        ),

        # Итоги по процентам
        "interest_before_total_text": (
            _money(
                interest_before_total
            )
        ),

        "interest_after_total_text": (
            _money(
                interest_after_total
            )
        ),

        "interest_delta_total_text": (
            _signed_money(
                interest_delta_total
            )
        ),

        # Итоги по общей задолженности
        "debt_before_total_text": (
            _money(
                debt_before_total
            )
        ),

        "debt_after_total_text": (
            _money(
                debt_after_total
            )
        ),

        "debt_delta_total_text": (
            _signed_money(
                debt_delta_total
            )
        ),

        "principal_delta_total": (
            principal_delta_total
        ),

        "interest_delta_total": (
            interest_delta_total
        ),

        "debt_delta_total": (
            debt_delta_total
        ),
    }

    pdf_bytes = _render_pdf(
        (
            "reporting/"
            "loan_adjustments/"
            "registry.html"
        ),
        context,
    )

    filename = (
        "Реестр_корректировок_займов_"
        f"{datetime.now():%Y%m%d_%H%M}.pdf"
    )

    return _pdf_response(
        pdf_bytes,
        filename,
        inline=False,
    )