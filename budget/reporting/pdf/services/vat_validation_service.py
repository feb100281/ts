from __future__ import annotations

from typing import Any
import re
import pandas as pd

from utils.vat_check.vat_exceptions import VAT_EXCEPTIONS_NM_IDS
from utils.vat_check.vat_rules import CHILDREN_10_VAT_TNVED_RULES, REDUCED_VAT_RATE


# REDUCED_VAT_RATE = 10.0


# # Льготные коды ТН ВЭД для ставки 10%
# CHILDREN_10_VAT_TNVED_RULES: list[dict[str, Any]] = [
#     {
#         "name": "Игрушки детские",
#         "prefixes": ["950300"],
#         "exclude_prefixes": [],
#     },
#     {
#         "name": "Коляски детские",
#         "prefixes": ["871500"],
#         "exclude_prefixes": [],
#     },
#     {
#         "name": "Одежда и принадлежности для детей младшего возраста, трикотажные",
#         "prefixes": ["6111"],
#         "exclude_prefixes": [],
#     },
#     {
#         "name": "Одежда и принадлежности для детей младшего возраста, текстильные",
#         "prefixes": ["6209"],
#         "exclude_prefixes": [],
#     },
# ]


def _normalize_tnved_code(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    digits = re.sub(r"\D", "", text)
    return digits or None


def _normalize_nm_id(value: Any) -> int | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    digits = re.sub(r"\D", "", text)
    return int(digits) if digits else None


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _format_money(value: float | int | None) -> str:
    value = float(value or 0)
    return f"{value:,.0f}".replace(",", " ")


def _match_tnved_rule(
    tnved_code: str | None,
    rules: list[dict[str, Any]],
) -> dict[str, Any] | None:
    if not tnved_code:
        return None

    normalized_code = _normalize_tnved_code(tnved_code)
    if not normalized_code:
        return None

    for rule in rules:
        exact_codes = [_normalize_tnved_code(x) for x in rule.get("exact", [])]
        prefixes = [_normalize_tnved_code(x) for x in rule.get("prefixes", [])]
        exclude_prefixes = [_normalize_tnved_code(x) for x in rule.get("exclude_prefixes", [])]

        if normalized_code in exact_codes:
            return rule

        matched_prefix = any(prefix and normalized_code.startswith(prefix) for prefix in prefixes)
        if not matched_prefix:
            continue

        is_excluded = any(
            ex_prefix and normalized_code.startswith(ex_prefix)
            for ex_prefix in exclude_prefixes
        )
        if not is_excluded:
            return rule

    return None


def calculate_vat_delta(
    gross_amount: float,
    actual_rate: float,
    expected_rate: float,
) -> float:
    """
    Рассчитывает разницу в НДС между ожидаемой и фактической ставкой.
    Отрицательный результат = переплата, положительный = недоплата.
    
    Формула:
    НДС = gross_amount × (rate / (100 + rate))
    """
    if gross_amount == 0:
        return 0.0
    
    # Фактический НДС
    actual_vat = gross_amount * (actual_rate / (100 + actual_rate))
    
    # Ожидаемый НДС
    expected_vat = gross_amount * (expected_rate / (100 + expected_rate))
    
    # Разница (отрицательная = переплата)
    return expected_vat - actual_vat


def _main_rate_for_year(year: int) -> float:
    # до 2026 — 20%, с 2026 и далее — 22%
    return 20.0 if year < 2026 else 22.0


def validate_vat_rate_simple(
    tnved_code: str | None,
    current_vat_rate: float | int | None,
    nm_id: Any = None,
) -> dict[str, Any]:
    """
    Проверяем только логику:
    если код ТН ВЭД льготный -> у товара должна быть ставка 10%.
    Исключенные nm_id не считаются ошибкой.
    """
    normalized_nm_id = _normalize_nm_id(nm_id)
    if normalized_nm_id in VAT_EXCEPTIONS_NM_IDS:
        return {
            "has_issue": False,
            "is_excluded": True,
            "normalized_nm_id": normalized_nm_id,
            "normalized_tnved_code": _normalize_tnved_code(tnved_code),
            "matched_rule_name": None,
        }

    normalized_code = _normalize_tnved_code(tnved_code)
    matched_rule = _match_tnved_rule(normalized_code, CHILDREN_10_VAT_TNVED_RULES)

    if matched_rule:
        is_correct_rate = (
            current_vat_rate is not None
            and abs(float(current_vat_rate) - REDUCED_VAT_RATE) < 1e-9
        )

        if not is_correct_rate:
            if current_vat_rate is None:
                message = "Льготный ТН ВЭД, но ставка не указана (должно быть 10%)"
            else:
                actual_rate = float(current_vat_rate)
                message = (
                    f"Льготный ТН ВЭД, но указана основная ставка "
                    f"{int(actual_rate)}% вместо льготной 10%"
                )

            return {
                "has_issue": True,
                "issue_type": "children_tnved_with_wrong_rate",
                "severity": "error",
                "message_short": message,
                "matched_rule_name": matched_rule.get("name"),
                "normalized_tnved_code": normalized_code,
                "normalized_nm_id": normalized_nm_id,
                "expected_rate": REDUCED_VAT_RATE,
                "current_rate": current_vat_rate,
                "is_excluded": False,
            }

    return {
        "has_issue": False,
        "normalized_tnved_code": normalized_code,
        "normalized_nm_id": normalized_nm_id,
        "matched_rule_name": matched_rule.get("name") if matched_rule else None,
        "is_excluded": False,
    }


def _build_sales_lines(row: dict[str, Any], years_to_show: list[int]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []

    for year in years_to_show:
        value = _safe_float(row.get(f"sales_{year}"), 0.0)
        quantity = _safe_float(row.get(f"quantity_{year}"), 0.0)

        if abs(value) < 1e-9:
            continue

        out.append({
            "year": int(year),
            "amount": value,
            "amount_fmt": f"{_format_money(value)} руб.",
            "quantity": int(quantity),
            "quantity_fmt": str(int(quantity)),
        })

    return out


def get_vat_validation_report(
    df: pd.DataFrame,
    report_year: int,
) -> dict[str, Any]:
    """
    Ожидаемые колонки:
    - nm_id
    - title
    - vat_rate
    - tnved_code
    - sales_YYYY
    - quantity_YYYY
    - last_sale_date
    """
    if df.empty:
        return {
            "total_items": 0,
            "has_issues": False,
            "summary": "Нет данных для анализа",
            "issue_items": [],
        }

    years_to_show = [report_year - 2, report_year - 1, report_year]
    issues: list[dict[str, Any]] = []

    for _, row in df.iterrows():
        nm_id = _normalize_nm_id(row.get("nm_id"))

        # Полностью исключаем товар из проверки
        if nm_id in VAT_EXCEPTIONS_NM_IDS:
            continue

        matched_rule = _match_tnved_rule(row.get("tnved_code"), CHILDREN_10_VAT_TNVED_RULES)
        if not matched_rule:
            continue

        original_rate = row.get("vat_rate")

        is_rate_10 = (
            original_rate is not None
            and abs(float(original_rate) - REDUCED_VAT_RATE) < 1e-9
        )
        if is_rate_10:
            continue

        sales_lines = _build_sales_lines(row, years_to_show)

        vat_deltas: list[dict[str, Any]] = []
        total_vat_delta = 0.0

        for year in years_to_show:
            sales_value = _safe_float(row.get(f"sales_{year}"), 0.0)
            if abs(sales_value) < 1e-9:
                continue

            expected_rate = REDUCED_VAT_RATE

            if original_rate is None:
                actual_rate = _main_rate_for_year(year)
            else:
                actual_rate = float(original_rate)

            delta = calculate_vat_delta(
                gross_amount=sales_value,
                actual_rate=actual_rate,
                expected_rate=expected_rate,
            )
            total_vat_delta += delta

            delta_class = "negative" if delta < 0 else "positive" if delta > 0 else "neutral"

            vat_deltas.append({
                "year": int(year),
                "amount": delta,
                "amount_fmt": f"{_format_money(delta)} руб.",
                "expected_rate": expected_rate,
                "actual_rate": actual_rate,
                "actual_rate_fmt": f"{int(actual_rate)}%",
                "delta_class": delta_class,
            })

        last_sale_date_fmt = None
        last_sale_date = row.get("last_sale_date")
        if pd.notna(last_sale_date):
            try:
                last_sale_date_fmt = pd.to_datetime(last_sale_date).strftime("%d.%m.%Y")
            except Exception:
                last_sale_date_fmt = str(last_sale_date)

        if original_rate is None:
            current_rate_display = "основная"
            current_rate_value = None
            message = "Льготный ТН ВЭД, но ставка не указана (должно быть 10%)"
        else:
            current_rate_value = float(original_rate)
            current_rate_display = f"{int(current_rate_value)}%"
            message = (
                f"Льготный ТН ВЭД, но указана основная ставка "
                f"{int(original_rate)}% вместо льготной 10%"
            )

        issues.append({
            "nm_id": nm_id,
            "title": row.get("title"),
            "tnved_code": _normalize_tnved_code(row.get("tnved_code")),
            "current_rate": current_rate_value,
            "current_rate_fmt": current_rate_display,
            "message_short": message,
            "matched_rule_name": matched_rule.get("name"),
            "sales_lines": sales_lines,
            "vat_delta_lines": vat_deltas,
            "total_vat_delta": total_vat_delta,
            "total_vat_delta_fmt": f"{_format_money(total_vat_delta)} руб.",
            "total_delta_class": (
                "negative" if total_vat_delta < 0 else "positive" if total_vat_delta > 0 else "neutral"
            ),
            "last_sale_date_fmt": last_sale_date_fmt,
        })

    issues = sorted(
        issues,
        key=lambda x: abs(float(x.get("total_vat_delta") or 0)),
        reverse=True,
    )

    if not issues:
        return {
            "total_items": len(df),
            "has_issues": False,
            "summary": "✅ Явных несоответствий ставок НДС не обнаружено",
            "issue_items": [],
        }

    total_impact = sum(float(x.get("total_vat_delta") or 0) for x in issues)
    total_impact_class = "negative" if total_impact < 0 else "positive" if total_impact > 0 else "neutral"

    summary = (
        f"Проверено товаров: {len(df)}. "
        f"Обнаружено проблемных товаров: {len(issues)}. "
        f"Оценочный эффект по НДС за последние 3 года: {_format_money(total_impact)} руб."
    )

    return {
        "total_items": len(df),
        "has_issues": True,
        "issue_count": len(issues),
        "summary": summary,
        "issue_items": issues,
        "total_vat_delta": total_impact,
        "total_vat_delta_fmt": f"{_format_money(total_impact)} руб.",
        "total_delta_class": total_impact_class,
        "years_to_show": years_to_show,
    }