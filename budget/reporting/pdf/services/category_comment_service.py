from __future__ import annotations

from typing import Any


def _to_float(v: Any) -> float:
    try:
        return float(v or 0)
    except Exception:
        return 0.0


def _fmt_pct(v: float) -> str:
    return f"{v:.1f}%"


def build_category_summary(
    rows: list[dict[str, Any]],
    segment_rows: list[dict[str, Any]] | None = None,
    total_net_base: float | None = None,
) -> dict | None:
    if not rows:
        return None

    total_categories = len(rows)

    # сумма чистой выручки по переданной выборке строк
    selected_total_net = sum(_to_float(r.get("net_amount")) for r in rows)

    # база для карточек:
    # если передали общую базу - используем её,
    # иначе fallback на сумму по выборке
    total_net = float(total_net_base) if total_net_base is not None else selected_total_net

    # Сортировка и концентрация — по чистой выручке
    rows_sorted_net = sorted(
        rows,
        key=lambda x: _to_float(x.get("net_amount")),
        reverse=True,
    )

    top1 = rows_sorted_net[0] if rows_sorted_net else None
    top3 = rows_sorted_net[:3]

    top1_share = (
        _to_float(top1.get("net_amount")) / total_net * 100
        if top1 and total_net else 0
    )
    top3_share = (
        sum(_to_float(r.get("net_amount")) for r in top3) / total_net * 100
        if total_net else 0
    )

    avg_return_rate = (
        sum(_to_float(r.get("return_rate_pct")) for r in rows) / total_categories
        if total_categories else 0
    )
    avg_price = (
        sum(_to_float(r.get("avg_sku_price")) for r in rows) / total_categories
        if total_categories else 0
    )

    best_net = rows_sorted_net[0] if rows_sorted_net else None

    # Значимые категории — по доле чистой выручки
    major_categories = []
    for r in rows:
        revenue_share_pct = _to_float(r.get("net_revenue_share_pct"))
        if revenue_share_pct == 0:
            revenue_share_pct = _to_float(r.get("revenue_share_pct"))
        if revenue_share_pct >= 5:
            major_categories.append(r)

    risk_category = None
    if major_categories:
        risk_category = max(
            major_categories,
            key=lambda x: _to_float(x.get("return_rate_pct")),
        )

    strong_categories = [
        r for r in rows
        if _to_float(r.get("avg_sku_price")) >= avg_price
        and _to_float(r.get("return_rate_pct")) <= avg_return_rate
    ]
    premium_winner = None
    if strong_categories:
        premium_winner = max(
            strong_categories,
            key=lambda x: _to_float(x.get("net_amount")),
        )

    dominant_segment_count = {"Low": 0, "Medium": 0, "High": 0}
    dominant_segment_examples: list[dict[str, str]] = []
    dominant_segment = None

    if segment_rows:
        grouped: dict[str, list[dict[str, Any]]] = {}
        for row in segment_rows:
            grouped.setdefault(row.get("subject_name") or "Не указана", []).append(row)

        for subject_name, items in grouped.items():
            best_seg = max(
                items,
                key=lambda x: _to_float(
                    x.get("category_net_share_pct", x.get("category_sales_share_pct"))
                ),
                default=None,
            )
            if best_seg:
                seg = best_seg.get("price_segment") or "—"
                if seg in dominant_segment_count:
                    dominant_segment_count[seg] += 1

                share_value = _to_float(
                    best_seg.get(
                        "category_net_share_pct",
                        best_seg.get("category_sales_share_pct"),
                    )
                )

                dominant_segment_examples.append(
                    {
                        "subject_name": subject_name,
                        "price_segment": seg,
                        "share_pct": f"{share_value:.1f}",
                        "price_range": best_seg.get("segment_price_range_fmt", "—"),
                    }
                )

        dominant_segment = max(
            dominant_segment_count,
            key=dominant_segment_count.get,
        )

    # ---------------------------------------------------------
    # 1. Главный вывод
    # ---------------------------------------------------------
    if top3_share >= 55:
        headline = (
            f"Чистая выручка категорий концентрируется в ограниченном числе товарных групп: "
            f"топ-3 формируют {_fmt_pct(top3_share)} чистой выручки, поэтому именно ключевые категории "
            f"определяют итоговый результат блока."
        )
    elif best_net:
        headline = (
            f"Основной вклад в результат дают несколько устойчивых категорий, "
            f"а максимальную чистую выручку формирует «{best_net.get('subject_name', '—')}»."
        )
    else:
        headline = (
            "Структура чистой выручки по категориям выглядит относительно сбалансированной, "
            "без критической концентрации в одной товарной группе."
        )

    # ---------------------------------------------------------
    # 2. Короткие управленческие тезисы
    # ---------------------------------------------------------
    executive_points: list[str] = []

    if top1:
        executive_points.append(
            f"Лидер по чистой выручке — «{top1.get('subject_name', '—')}» "
            f"с долей {_fmt_pct(top1_share)}."
        )

    executive_points.append(
        f"Топ-3 категории формируют {_fmt_pct(top3_share)} чистой выручки."
    )

    if best_net:
        executive_points.append(
            f"Максимальная чистая выручка у категории «{best_net.get('subject_name', '—')}» — "
            f"{best_net.get('net_amount_fmt', '—')}."
        )

    if risk_category:
        executive_points.append(
            f"Наибольшая возвратность среди значимых категорий у «{risk_category.get('subject_name', '—')}» — "
            f"{risk_category.get('return_rate_pct', '0')}%."
        )

    if dominant_segment:
        executive_points.append(
            f"Чаще всего продажи внутри категорий формирует сегмент {dominant_segment}."
        )

    # ---------------------------------------------------------
    # 3. Сильные стороны
    # ---------------------------------------------------------
    strengths: list[str] = []

    if premium_winner:
        strengths.append(
            f"«{premium_winner.get('subject_name', '—')}» сочетает более высокий средний чек "
            f"({premium_winner.get('avg_sku_price_fmt', '—')}) и возвратность не выше средней."
        )

    if best_net and top1 and best_net.get("subject_name") == top1.get("subject_name"):
        strengths.append(
            "Лидер по чистой выручке одновременно удерживает максимальный вклад в структуре категорий, "
            "что говорит о хорошем качестве результата в этой категории."
        )

    # ---------------------------------------------------------
    # 4. Риски
    # ---------------------------------------------------------
    risks: list[str] = []

    if risk_category:
        risks.append(
            f"Категория «{risk_category.get('subject_name', '—')}» требует отдельного наблюдения: "
            f"при заметной доле в чистой выручке возвратность составляет {risk_category.get('return_rate_pct', '0')}%."
        )

    if top3_share >= 55:
        risks.append(
            "Высокая концентрация чистой выручки в нескольких категориях увеличивает зависимость результата "
            "от сезонности, доступности размеров и качества карточек товара."
        )

    # ---------------------------------------------------------
    # 5. Действия
    # ---------------------------------------------------------
    actions: list[str] = []

    actions.append(
        "Для маркетплейс-канала возвратность стоит трактовать как показатель операционного качества категории, "
        "а не как автоматический признак проблемы товара."
    )

    if risk_category:
        actions.append(
            f"По категории «{risk_category.get('subject_name', '—')}» рекомендуется проверить размерную сетку, "
            "карточку товара, визуал и распределение заказов по размерам."
        )

    if dominant_segment:
        actions.append(
            "Ценовые решения лучше принимать внутри ценовых слоев категории, так как основной объем продаж "
            "часто формирует один конкретный сегмент, а не вся матрица целиком."
        )

    # ---------------------------------------------------------
    # 6. KPI-карточки
    # ---------------------------------------------------------
    kpi_cards = [
        {
            "title": "Лидер категории",
            "value": top1.get("subject_name", "—") if top1 else "—",
            "subtitle": f"Доля {_fmt_pct(top1_share)}",
        },
        {
            "title": "Концентрация топ-3",
            "value": _fmt_pct(top3_share),
            "subtitle": "доля в чистой выручке",
        },
        {
            "title": "Средняя возвратность",
            "value": _fmt_pct(avg_return_rate),
            "subtitle": "по анализируемым категориям",
        },
        {
            "title": "Доминирующий слой",
            "value": dominant_segment or "—",
            "subtitle": "внутри категорий",
        },
    ]

    note = (
        "Анализ построен по ключевым категориям, которые формируют основную часть чистой выручки. "
        "Карточки доли и концентрации рассчитываются от общей базы чистой выручки, если она передана в сервис. "
        "Для анализа использован период последних 90 дней: он сглаживает колебания одного месяца, "
        "учитывает лаг по возвратам и показывает более устойчивую структуру спроса. "
        "Сегменты Low / Medium / High рассчитываются отдельно внутри каждой категории по фактическому распределению цен SKU."
    )

    return {
        "total_categories": total_categories,
        "total_net": total_net,
        "selected_total_net": selected_total_net,
        "headline": headline,
        "executive_points": executive_points,
        "strengths": strengths,
        "risks": risks,
        "actions": actions,
        "note": note,
        "top1_category": top1.get("subject_name") if top1 else "—",
        "top1_share_pct": f"{top1_share:.1f}",
        "top3_share_pct": f"{top3_share:.1f}",
        "avg_return_rate": f"{avg_return_rate:.2f}",
        "dominant_segment": dominant_segment or "—",
        "dominant_segment_examples": dominant_segment_examples[:8],
        "kpi_cards": kpi_cards,
    }