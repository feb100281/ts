# gear/app/daily_sales/ai_analysis/engine.py
from __future__ import annotations

from .config import (
    SIGNIFICANT_CHANGE_PCT,
    CRITICAL_CHANGE_PCT,
    HIGH_RETURN_RATE_PCT,
    VERY_HIGH_RETURN_RATE_PCT,
)
from .formatters import (
    format_money,
    format_number,
    format_pct,
    safe_pct_change,
)


def compare_metrics(current: dict, previous: dict) -> dict:
    return {
        "revenue_change_pct": safe_pct_change(
            current["revenue"],
            previous["revenue"],
        ),
        "sales_change_pct": safe_pct_change(
            current["sales_amount"],
            previous["sales_amount"],
        ),
        "returns_change_pct": safe_pct_change(
            current["returns_amount"],
            previous["returns_amount"],
        ),
        "quantity_change_pct": safe_pct_change(
            current["quantity"],
            previous["quantity"],
        ),
        "average_price_change_pct": safe_pct_change(
            current["average_price"],
            previous["average_price"],
        ),
        "daily_revenue_change_pct": safe_pct_change(
            current["daily_revenue"],
            previous["daily_revenue"],
        ),
        "return_rate_delta": (
            current["return_rate"] - previous["return_rate"]
        ),
    }


def build_summary(current: dict, previous: dict, comparison: dict) -> str:
    revenue_change = comparison["revenue_change_pct"]

    if revenue_change > 0:
        direction = "выше"
    elif revenue_change < 0:
        direction = "ниже"
    else:
        direction = "на уровне"

    return (
        f"За период с {current['start_date'].strftime('%d.%m.%Y')} "
        f"по {current['end_date'].strftime('%d.%m.%Y')} "
        f"чистая выручка составила {format_money(current['revenue'])}. "
        f"Это на {format_pct(abs(revenue_change))} {direction} "
        f"сопоставимого периода. Продажи до возвратов — "
        f"{format_money(current['sales_amount'])}, возвраты — "
        f"{format_money(current['returns_amount'])} "
        f"({format_pct(current['return_rate'])} от продаж). "
        f"Средняя цена составила {format_money(current['average_price'])}, "
        f"чистое количество операций — {format_number(current['quantity'])}."
    )


# def build_driver_analysis(current: dict, previous: dict, comparison: dict) -> dict:
#     qty_change = comparison["quantity_change_pct"]
#     price_change = comparison["average_price_change_pct"]
#     returns_change = comparison["returns_change_pct"]

#     drivers = [
#         {
#             "name": "Количество",
#             "change_pct": qty_change,
#             "impact": abs(qty_change),
#         },
#         {
#             "name": "Средняя цена",
#             "change_pct": price_change,
#             "impact": abs(price_change),
#         },
#         {
#             "name": "Возвраты",
#             "change_pct": returns_change,
#             "impact": abs(returns_change),
#         },
#     ]

#     main_driver = max(drivers, key=lambda x: x["impact"])

#     return {
#         "drivers": drivers,
#         "main_driver": main_driver,
#     }


def build_driver_analysis(
    current: dict,
    previous: dict,
    comparison: dict,
) -> dict:
    qty_change = comparison["quantity_change_pct"]
    price_change = comparison["average_price_change_pct"]
    returns_change = comparison["returns_change_pct"]

    current_quantity = float(current.get("quantity") or 0)
    previous_quantity = float(previous.get("quantity") or 0)

    current_average_price = float(
        current.get("average_price") or 0
    )
    previous_average_price = float(
        previous.get("average_price") or 0
    )

    current_returns = float(
        current.get("returns_amount") or 0
    )
    previous_returns = float(
        previous.get("returns_amount") or 0
    )

    drivers = [
        {
            "name": "Количество",
            "current_value": current_quantity,
            "previous_value": previous_quantity,
            "delta": current_quantity - previous_quantity,
            "change_pct": qty_change,
            "visual_change_pct": qty_change,
            "value_type": "quantity",
            "impact": abs(qty_change),
        },
        {
            "name": "Средняя цена",
            "current_value": current_average_price,
            "previous_value": previous_average_price,
            "delta": (
                current_average_price
                - previous_average_price
            ),
            "change_pct": price_change,
            "visual_change_pct": price_change,
            "value_type": "money",
            "impact": abs(price_change),
        },
        {
            "name": "Возвраты",
            "current_value": current_returns,
            "previous_value": previous_returns,
            "delta": current_returns - previous_returns,
            "change_pct": returns_change,

            # Рост возвратов — негативный фактор,
            # поэтому столбец направляем в отрицательную сторону.
            "visual_change_pct": -returns_change,

            "value_type": "money",
            "impact": abs(returns_change),
        },
    ]

    main_driver = max(
        drivers,
        key=lambda row: row["impact"],
    )

    return {
        "drivers": drivers,
        "main_driver": main_driver,
    }


def build_findings(
    current: dict,
    previous: dict,
    comparison: dict,
    daily_rows: list[dict],
) -> list[dict]:
    findings = []
    revenue_change = comparison["revenue_change_pct"]

    if revenue_change >= CRITICAL_CHANGE_PCT:
        findings.append(
            {
                "level": "positive",
                "title": "Сильный рост выручки",
                "text": (
                    f"Чистая выручка выросла на "
                    f"{format_pct(revenue_change)} — "
                    f"с {format_money(previous['revenue'])} "
                    f"до {format_money(current['revenue'])}."
                ),
            }
        )
    elif revenue_change >= SIGNIFICANT_CHANGE_PCT:
        findings.append(
            {
                "level": "positive",
                "title": "Положительная динамика",
                "text": (
                    f"Чистая выручка увеличилась на "
                    f"{format_pct(revenue_change)}."
                ),
            }
        )
    elif revenue_change <= -CRITICAL_CHANGE_PCT:
        findings.append(
            {
                "level": "negative",
                "title": "Критичное снижение выручки",
                "text": (
                    f"Чистая выручка сократилась на "
                    f"{format_pct(abs(revenue_change))} — "
                    f"с {format_money(previous['revenue'])} "
                    f"до {format_money(current['revenue'])}."
                ),
            }
        )
    elif revenue_change <= -SIGNIFICANT_CHANGE_PCT:
        findings.append(
            {
                "level": "negative",
                "title": "Отрицательная динамика",
                "text": (
                    f"Чистая выручка снизилась на "
                    f"{format_pct(abs(revenue_change))}."
                ),
            }
        )
    else:
        findings.append(
            {
                "level": "neutral",
                "title": "Выручка без существенных изменений",
                "text": (
                    f"Отклонение от сопоставимого периода составило "
                    f"{format_pct(revenue_change, signed=True)}."
                ),
            }
        )

    driver = build_driver_analysis(current, previous, comparison)["main_driver"]

    if driver["name"] == "Количество":
        findings.append(
            {
                "level": "info",
                "title": "Главный драйвер — количество",
                "text": (
                    f"Количество изменилось на "
                    f"{format_pct(driver['change_pct'], signed=True)}. "
                    f"Изменение средней цены составило "
                    f"{format_pct(comparison['average_price_change_pct'], signed=True)}."
                ),
            }
        )
    elif driver["name"] == "Средняя цена":
        findings.append(
            {
                "level": "info",
                "title": "Главный драйвер — средняя цена",
                "text": (
                    f"Средняя цена изменилась на "
                    f"{format_pct(driver['change_pct'], signed=True)}. "
                    f"Количество изменилось на "
                    f"{format_pct(comparison['quantity_change_pct'], signed=True)}."
                ),
            }
        )
    else:
        findings.append(
            {
                "level": "warning",
                "title": "Главный фактор — возвраты",
                "text": (
                    f"Сумма возвратов изменилась на "
                    f"{format_pct(driver['change_pct'], signed=True)}."
                ),
            }
        )

    if current["return_rate"] >= VERY_HIGH_RETURN_RATE_PCT:
        findings.append(
            {
                "level": "negative",
                "title": "Очень высокая доля возвратов",
                "text": (
                    f"Возвраты составляют "
                    f"{format_pct(current['return_rate'])} от продаж. "
                    f"Показатель требует отдельной проверки."
                ),
            }
        )
    elif current["return_rate"] >= HIGH_RETURN_RATE_PCT:
        findings.append(
            {
                "level": "warning",
                "title": "Повышенная доля возвратов",
                "text": (
                    f"Возвраты составляют "
                    f"{format_pct(current['return_rate'])} от продаж."
                ),
            }
        )
    elif comparison["return_rate_delta"] <= -2:
        findings.append(
            {
                "level": "positive",
                "title": "Качество продаж улучшилось",
                "text": (
                    f"Доля возвратов снизилась на "
                    f"{abs(comparison['return_rate_delta']):.1f} п.п."
                ),
            }
        )

    if daily_rows:
        best_day = max(daily_rows, key=lambda x: x["revenue"])
        worst_day = min(daily_rows, key=lambda x: x["revenue"])
        max_returns_day = max(
            daily_rows,
            key=lambda x: x["returns_amount"],
        )

        findings.extend(
            [
                {
                    "level": "positive",
                    "title": "Лучший день периода",
                    "text": (
                        f"{best_day['date'].strftime('%d.%m.%Y')} — "
                        f"{format_money(best_day['revenue'])} чистой выручки."
                    ),
                },
                {
                    "level": "negative",
                    "title": "Самый слабый день",
                    "text": (
                        f"{worst_day['date'].strftime('%d.%m.%Y')} — "
                        f"{format_money(worst_day['revenue'])} чистой выручки."
                    ),
                },
                {
                    "level": "warning",
                    "title": "Максимальные возвраты",
                    "text": (
                        f"{max_returns_day['date'].strftime('%d.%m.%Y')} — "
                        f"{format_money(max_returns_day['returns_amount'])}."
                    ),
                },
            ]
        )

    return findings


def build_plan_findings(plan_analysis: dict | None) -> list[dict]:
    if not plan_analysis:
        return [
            {
                "level": "warning",
                "title": "План WB недоступен",
                "text": "Не удалось получить данные по плану и факту WB.",
            }
        ]

    current = plan_analysis.get("current_semi")

    if not current:
        return [
            {
                "level": "warning",
                "title": "Текущий плановый период не найден",
                "text": "В данных нет активного полугодия.",
            }
        ]

    exec_pct = float(current.get("exec_pct") or 0)
    remaining = float(current.get("remaining") or 0)
    current_rate = float(current.get("current_daily_rate") or 0)
    required_rate = float(current.get("required_daily_rate") or 0)
    projected_end = float(current.get("projected_end") or 0)
    plan = float(current.get("plan") or 0)

    projected_pct = projected_end / plan * 100 if plan else 0

    if exec_pct >= 100:
        level = "positive"
        title = "План выполнен"
        text = (
            f"Выполнение плана — {format_pct(exec_pct)}. "
            f"План превышен на {format_money(max(current.get('over', 0), 0))}."
        )
    elif current.get("days_remaining", 0) <= 0:
        level = "negative"
        title = "Период завершён ниже плана"
        text = (
            f"Выполнение составило {format_pct(exec_pct)}. "
            f"Недовыполнение — {format_money(remaining)}."
        )
    elif current_rate >= required_rate:
        level = "positive"
        title = "Текущий темп достаточен"
        text = (
            f"Выполнение плана — {format_pct(exec_pct)}. "
            f"Текущий темп {format_money(current_rate)} в день "
            f"не ниже требуемого {format_money(required_rate)}."
        )
    else:
        level = "warning"
        title = "Темп ниже необходимого"
        text = (
            f"Выполнение плана — {format_pct(exec_pct)}. "
            f"Осталось {format_money(remaining)}. "
            f"Текущий темп — {format_money(current_rate)} в день, "
            f"требуется — {format_money(required_rate)}."
        )

    return [
        {
            "level": level,
            "title": title,
            "text": text,
        },
        {
            "level": (
                "positive"
                if projected_pct >= 100
                else "warning"
            ),
            "title": "Прогноз выполнения",
            "text": (
                f"При сохранении текущего темпа прогноз на конец периода — "
                f"{format_pct(projected_pct)} плана "
                f"({format_money(projected_end)})."
            ),
        },
    ]


def build_analysis_payload(
    current: dict,
    previous: dict,
    daily_rows: list[dict],
    period_rows: list[dict],
    plan_analysis: dict | None,
) -> dict:
    comparison = compare_metrics(current, previous)

    return {
        "current": current,
        "previous": previous,
        "comparison": comparison,
        "summary": build_summary(current, previous, comparison),
        "findings": build_findings(
            current,
            previous,
            comparison,
            daily_rows,
        ),
        "drivers": build_driver_analysis(
            current,
            previous,
            comparison,
        ),
        "daily_rows": daily_rows,
        "period_rows": period_rows,
        "plan_analysis": plan_analysis,
        "plan_findings": build_plan_findings(plan_analysis),
    }



# ---------------------------------------------------------------------
# Аналитика брендов, категорий, товаров и рекомендации
# ---------------------------------------------------------------------

from .config import (
    ENTITY_TOP_N,
    PRODUCT_TOP_N,
    STOCK_SHORTAGE_DAYS,
    STOCK_WARNING_DAYS,
    STOCK_EXCESS_DAYS,
    STOCK_DEAD_DAYS,
    SALES_DROP_WARNING_PCT,
    SALES_DROP_CRITICAL_PCT,
    RETURNS_GROWTH_WARNING_PCT,
    MIN_ENTITY_REVENUE,
    MIN_PRODUCT_REVENUE,
)


def enrich_entity_rows(rows: list[dict]) -> list[dict]:
    result = []

    for row in rows:
        enriched = dict(row)
        enriched["revenue_change_pct"] = safe_pct_change(
            row["current_revenue"],
            row["previous_revenue"],
        )
        enriched["qty_change_pct"] = safe_pct_change(
            row["current_qty"],
            row["previous_qty"],
        )
        enriched["avg_price_change_pct"] = safe_pct_change(
            row["current_avg_price"],
            row["previous_avg_price"],
        )
        enriched["returns_change_pct"] = safe_pct_change(
            row["current_returns"],
            row["previous_returns"],
        )
        enriched["return_rate_delta"] = (
            row["current_return_rate"] - row["previous_return_rate"]
        )
        result.append(enriched)

    return result


def build_entity_summary(rows: list[dict]) -> dict:
    rows = enrich_entity_rows(rows)

    relevant = [
        row for row in rows
        if abs(row["current_revenue"]) >= MIN_ENTITY_REVENUE
        or abs(row["previous_revenue"]) >= MIN_ENTITY_REVENUE
    ]

    growth = sorted(
        relevant,
        key=lambda x: x["revenue_delta"],
        reverse=True,
    )[:ENTITY_TOP_N]

    decline = sorted(
        relevant,
        key=lambda x: x["revenue_delta"],
    )[:ENTITY_TOP_N]

    return_growth = sorted(
        relevant,
        key=lambda x: x["return_rate_delta"],
        reverse=True,
    )[:ENTITY_TOP_N]

    return {
        "all": relevant,
        "growth": growth,
        "decline": decline,
        "return_growth": return_growth,
    }


def enrich_product_rows(rows: list[dict]) -> list[dict]:
    result = []

    for row in rows:
        enriched = dict(row)

        enriched["revenue_change_pct"] = safe_pct_change(
            row["current_revenue"],
            row["previous_revenue"],
        )
        enriched["qty_change_pct"] = safe_pct_change(
            row["current_qty"],
            row["previous_qty"],
        )
        enriched["avg_price_change_pct"] = safe_pct_change(
            row["current_avg_price"],
            row["previous_avg_price"],
        )
        enriched["returns_change_pct"] = safe_pct_change(
            row["current_returns"],
            row["previous_returns"],
        )
        enriched["return_rate_delta"] = (
            row["current_return_rate"] - row["previous_return_rate"]
        )

        flags = []

        if (
            row["stock_qty"] > 0
            and row["previous_revenue"] >= MIN_PRODUCT_REVENUE
            and enriched["revenue_change_pct"] <= SALES_DROP_WARNING_PCT
        ):
            flags.append("stock_but_sales_down")

        if (
            row["stock_qty"] > 0
            and row["current_qty"] <= 0
            and row["previous_qty"] > 0
        ):
            flags.append("stock_without_sales")

        days_of_stock = row["days_of_stock"]

        if days_of_stock is not None:
            if 0 < days_of_stock <= STOCK_SHORTAGE_DAYS:
                flags.append("shortage")
            elif days_of_stock <= STOCK_WARNING_DAYS:
                flags.append("stock_warning")
            elif days_of_stock >= STOCK_DEAD_DAYS:
                flags.append("dead_stock")
            elif days_of_stock >= STOCK_EXCESS_DAYS:
                flags.append("excess_stock")
        elif row["stock_qty"] > 0 and row["current_qty"] <= 0:
            flags.append("dead_stock")

        if (
            enriched["returns_change_pct"] >= RETURNS_GROWTH_WARNING_PCT
            and row["current_returns"] > 0
        ):
            flags.append("returns_growth")

        if row["current_return_rate"] >= 25:
            flags.append("high_return_rate")

        enriched["flags"] = flags
        result.append(enriched)

    return result


def build_product_summary(rows: list[dict]) -> dict:
    rows = enrich_product_rows(rows)

    relevant = [
        row for row in rows
        if row["stock_qty"] > 0
        or abs(row["current_revenue"]) >= MIN_PRODUCT_REVENUE
        or abs(row["previous_revenue"]) >= MIN_PRODUCT_REVENUE
    ]

    problem_rows = [
        row for row in relevant
        if row["flags"]
    ]

    sales_down_with_stock = sorted(
        [
            row for row in relevant
            if "stock_but_sales_down" in row["flags"]
            or "stock_without_sales" in row["flags"]
        ],
        key=lambda x: (
            x["revenue_change_pct"],
            -x["stock_man_value"],
        ),
    )[:PRODUCT_TOP_N]

    shortage = sorted(
        [
            row for row in relevant
            if "shortage" in row["flags"]
            or "stock_warning" in row["flags"]
        ],
        key=lambda x: (
            x["days_of_stock"] if x["days_of_stock"] is not None else 10**9
        ),
    )[:PRODUCT_TOP_N]

    excess = sorted(
        [
            row for row in relevant
            if "excess_stock" in row["flags"]
            or "dead_stock" in row["flags"]
        ],
        key=lambda x: x["stock_man_value"],
        reverse=True,
    )[:PRODUCT_TOP_N]

    returns = sorted(
        [
            row for row in relevant
            if "returns_growth" in row["flags"]
            or "high_return_rate" in row["flags"]
        ],
        key=lambda x: (
            x["current_return_rate"],
            x["current_returns"],
        ),
        reverse=True,
    )[:PRODUCT_TOP_N]

    growth = sorted(
        relevant,
        key=lambda x: x["revenue_delta"] if "revenue_delta" in x else (
            x["current_revenue"] - x["previous_revenue"]
        ),
        reverse=True,
    )[:PRODUCT_TOP_N]

    return {
        "all": relevant,
        "problems": problem_rows,
        "sales_down_with_stock": sales_down_with_stock,
        "shortage": shortage,
        "excess": excess,
        "returns": returns,
        "growth": growth,
    }


def build_recommendations(
    brand_summary: dict,
    category_summary: dict,
    product_summary: dict,
) -> list[dict]:
    recommendations = []

    if brand_summary["decline"]:
        row = brand_summary["decline"][0]
        if row["revenue_delta"] < 0:
            recommendations.append(
                {
                    "priority": "high",
                    "title": f"Проверить бренд «{row['name']}»",
                    "text": (
                        f"Вклад бренда в снижение выручки — "
                        f"{format_money(abs(row['revenue_delta']))}. "
                        f"Выручка изменилась на "
                        f"{format_pct(row['revenue_change_pct'], signed=True)}. "
                        f"Проверьте ассортимент, остатки, цену и рекламную активность."
                    ),
                }
            )

    if category_summary["return_growth"]:
        row = category_summary["return_growth"][0]
        if row["return_rate_delta"] > 2:
            recommendations.append(
                {
                    "priority": "medium",
                    "title": f"Разобрать возвраты в категории «{row['name']}»",
                    "text": (
                        f"Доля возвратов выросла на "
                        f"{row['return_rate_delta']:+.1f} п.п. "
                        f"Текущий уровень — "
                        f"{format_pct(row['current_return_rate'])}. "
                        f"Проверьте размеры, карточки, качество и причины возвратов."
                    ),
                }
            )

    if product_summary["sales_down_with_stock"]:
        row = product_summary["sales_down_with_stock"][0]
        recommendations.append(
            {
                "priority": "high",
                "title": "Товар есть в наличии, но продажи падают",
                "text": (
                    f"NM ID {row['nm_id']}, «{row['title']}»: "
                    f"остаток {format_number(row['stock_qty'])} шт., "
                    f"выручка изменилась на "
                    f"{format_pct(row['revenue_change_pct'], signed=True)}. "
                    f"Проверьте позицию в выдаче, цену, скидку, рекламу "
                    f"и актуальность карточки."
                ),
            }
        )

    if product_summary["shortage"]:
        row = product_summary["shortage"][0]
        recommendations.append(
            {
                "priority": "high",
                "title": "Риск дефицита",
                "text": (
                    f"NM ID {row['nm_id']}, «{row['title']}»: "
                    f"запаса примерно на "
                    f"{row['days_of_stock']:.1f} дня. "
                    f"Рекомендуется проверить поставку и приоритет пополнения."
                ),
            }
        )

    if product_summary["excess"]:
        row = product_summary["excess"][0]
        days_text = (
            f"{row['days_of_stock']:.0f} дней"
            if row["days_of_stock"] is not None
            else "продажи отсутствуют"
        )
        recommendations.append(
            {
                "priority": "medium",
                "title": "Избыточный или неликвидный запас",
                "text": (
                    f"NM ID {row['nm_id']}, «{row['title']}»: "
                    f"остаток {format_number(row['stock_qty'])} шт., "
                    f"{days_text}, заморожено по управленческой себестоимости "
                    f"{format_money(row['stock_man_value'])}. "
                    f"Рассмотрите промо, перераспределение или ограничение закупки."
                ),
            }
        )

    if product_summary["returns"]:
        row = product_summary["returns"][0]
        recommendations.append(
            {
                "priority": "medium",
                "title": "Высокие возвраты по товару",
                "text": (
                    f"NM ID {row['nm_id']}, «{row['title']}»: "
                    f"доля возвратов {format_pct(row['current_return_rate'])}, "
                    f"сумма возвратов {format_money(row['current_returns'])}. "
                    f"Проверьте причины возвратов, размерную сетку и описание."
                ),
            }
        )

    if not recommendations:
        recommendations.append(
            {
                "priority": "low",
                "title": "Критичных отклонений не найдено",
                "text": (
                    "По выбранному периоду существенных проблем по брендам, "
                    "категориям, товарам и запасам не выявлено."
                ),
            }
        )

    return recommendations
