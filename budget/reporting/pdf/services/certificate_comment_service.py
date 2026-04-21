# from __future__ import annotations

# from typing import Any


# def build_certificate_risk_comment(rows: list[dict[str, Any]]) -> dict | None:
#     if not rows:
#         return None

#     total_items = len(rows)

#     expired = [r for r in rows if r.get("risk_level") == "Истек"]
#     critical = [r for r in rows if r.get("risk_level") == "Критично"]
#     high = [r for r in rows if r.get("risk_level") == "Высокий риск"]

#     total_sales = sum(float(r.get("sales_amount_90d", 0) or 0) for r in rows)
#     expired_sales = sum(float(r.get("sales_amount_90d", 0) or 0) for r in expired)
#     critical_sales = sum(float(r.get("sales_amount_90d", 0) or 0) for r in critical)

#     # топ рисков
#     top_risk = sorted(rows, key=lambda x: float(x.get("sales_amount_90d", 0) or 0), reverse=True)[:5]

#     top_risk = [
#         {
#             "product_name": r.get("product_name"),
#             "sales_amount_fmt": r.get("sales_amount_90d_fmt"),
#             "risk_level": r.get("risk_level"),
#         }
#         for r in top_risk
#     ]

#     # концентрация риска
#     top3_sales = sum(float(r.get("sales_amount_90d", 0) or 0) for r in rows[:3])
#     concentration_pct = (top3_sales / total_sales * 100) if total_sales else 0

#     if concentration_pct > 60:
#         concentration_text = "Риск существенно сконцентрирован в ограниченном количестве SKU."
#     elif concentration_pct > 30:
#         concentration_text = "Риск умеренно сконцентрирован."
#     else:
#         concentration_text = "Риск распределен по широкому ассортименту."

#     comment = (
#         f"В выборке выявлено {total_items} SKU с риском истечения сертификатов. "
#         f"Из них {len(expired)} позиций уже имеют истекшие сертификаты, "
#         f"{len(critical)} — находятся в критической зоне (до 30 дней), "
#         f"{len(high)} — в зоне повышенного риска (до 90 дней). "
#         f"Совокупный объем продаж по данным SKU за последние 90 дней составляет "
#         f"{total_sales:,.0f} руб.".replace(",", " ")
#     )

#     if expired_sales > 0:
#         comment += (
#             f" При этом по товарам с уже истекшими сертификатами приходится "
#             f"{expired_sales:,.0f} руб. выручки.".replace(",", " ")
#         )

#     if critical_sales > 0:
#         comment += (
#             f" Дополнительно {critical_sales:,.0f} руб. приходится на товары с критическим сроком истечения."
#             .replace(",", " ")
#         )

#     return {
#         "comment": comment,
#         "note": concentration_text,
#         "top_risk": top_risk,
#         "total_items": total_items,
#         "expired_count": len(expired),
#         "critical_count": len(critical),
#         "high_count": len(high),
#     }


# budget/reporting/pdf/services/certificate_comment_service.py
from __future__ import annotations

from typing import Any

from budget.reporting.pdf.services.sales_data_service import _format_money


def build_certificate_risk_comment(rows: list[dict[str, Any]]) -> dict | None:
    if not rows:
        return None

    valid_rows = [r for r in rows if float(r.get("sales_amount_90d", 0) or 0) > 0]
    if not valid_rows:
        return None

    total_items = len(valid_rows)

    expired = [r for r in valid_rows if r.get("risk_level") == "Истек"]
    critical = [r for r in valid_rows if r.get("risk_level") == "Критично"]
    high = [r for r in valid_rows if r.get("risk_level") == "Высокий риск"]
    control = [r for r in valid_rows if r.get("risk_level") == "Контроль"]

    total_sales = sum(float(r.get("sales_amount_90d", 0) or 0) for r in valid_rows)
    expired_sales = sum(float(r.get("sales_amount_90d", 0) or 0) for r in expired)
    critical_sales = sum(float(r.get("sales_amount_90d", 0) or 0) for r in critical)
    high_sales = sum(float(r.get("sales_amount_90d", 0) or 0) for r in high)
    control_sales = sum(float(r.get("sales_amount_90d", 0) or 0) for r in control)

    rows_sorted = sorted(
        valid_rows,
        key=lambda x: float(x.get("sales_amount_90d", 0) or 0),
        reverse=True,
    )

    top_risk = rows_sorted[:5]

    top3_sales = sum(float(r.get("sales_amount_90d", 0) or 0) for r in rows_sorted[:3])
    concentration_pct = (top3_sales / total_sales * 100) if total_sales else 0

    if concentration_pct >= 60:
        concentration_text = "Риск существенно сконцентрирован в ограниченном количестве SKU."
    elif concentration_pct >= 35:
        concentration_text = "Риск умеренно сконцентрирован."
    else:
        concentration_text = "Риск распределен по широкому ассортименту."

    parts = []

    parts.append(
        f"В анализ включены {total_items} SKU с наибольшим объемом продаж, "
        f"имеющие риск истечения сертификатов или деклараций."
    )

    risk_parts = []

    if len(expired) > 0:
        if len(expired) == total_items:
            risk_parts.append("Все позиции в выборке уже имеют истекшие документы")
        else:
            risk_parts.append(f"{len(expired)} позиций уже имеют истекшие документы")

    if len(critical) > 0:
        risk_parts.append(f"{len(critical)} находятся в критической зоне (до 30 дней)")

    if len(high) > 0:
        risk_parts.append(f"{len(high)} — в зоне повышенного риска (до 90 дней)")

    if len(control) > 0:
        risk_parts.append(f"{len(control)} — в зоне контроля (91–180 дней)")

    if risk_parts:
        parts.append(". ".join(risk_parts) + ".")

    parts.append(
        f"Совокупный объем продаж по данным SKU за последние 90 дней составляет "
        f"{_format_money(total_sales)} руб."
    )

    if expired_sales > 0:
        if abs(expired_sales - total_sales) < 0.01:
            parts.append(
                "На товары с истекшими документами приходится весь объем продаж, "
                "отраженный в данной выборке."
            )
        else:
            parts.append(
                f"На товары с уже истекшими документами приходится "
                f"{_format_money(expired_sales)} руб. продаж."
            )

    if critical_sales > 0:
        parts.append(
            f"Дополнительно на товары с критическим сроком истечения приходится "
            f"{_format_money(critical_sales)} руб."
        )

    if high_sales > 0:
        parts.append(
            f"На товары в зоне повышенного риска приходится "
            f"{_format_money(high_sales)} руб."
        )

    comment = " ".join(parts)

    if expired_sales > 0:
        comment += (
            f" На товары с уже истекшими документами приходится "
            f"{_format_money(expired_sales)} руб. продаж."
        )

    if critical_sales > 0:
        comment += (
            f" Дополнительно на товары с критическим сроком истечения приходится "
            f"{_format_money(critical_sales)} руб."
        )

    summary = {
        "total_items": total_items,
        "expired_count": len(expired),
        "critical_count": len(critical),
        "high_count": len(high),
        "control_count": len(control),
        "total_sales_90d": _format_money(total_sales),
        "expired_sales_90d": _format_money(expired_sales),
        "critical_sales_90d": _format_money(critical_sales),
        "high_sales_90d": _format_money(high_sales),
        "control_sales_90d": _format_money(control_sales),
        "top3_concentration_pct": f"{concentration_pct:.1f}",
    }

    top_risk_rows = [
        {
            "product_name": r.get("product_name") or "—",
            "sales_amount_90d_fmt": r.get("sales_amount_90d_fmt") or _format_money(r.get("sales_amount_90d", 0)),
            "sales_qty_90d_fmt": r.get("sales_qty_90d_fmt") or str(r.get("sales_qty_90d", 0)),
            "risk_level": r.get("risk_level") or "—",
        }
        for r in top_risk
    ]

    return {
        "comment": comment,
        "note": concentration_text,
        "summary": summary,
        "top_risk": top_risk_rows,
    }