# gear/app/daily_sales/daily_brief/editorial.py
from __future__ import annotations

from datetime import date
from typing import Any

from .helpers import fmt_money, fmt_number, fmt_pct, number


MONTHS_RU = {
    1: "января",
    2: "февраля",
    3: "марта",
    4: "апреля",
    5: "мая",
    6: "июня",
    7: "июля",
    8: "августа",
    9: "сентября",
    10: "октября",
    11: "ноября",
    12: "декабря",
}

WEEKDAYS_RU = {
    0: "понедельник",
    1: "вторник",
    2: "среда",
    3: "четверг",
    4: "пятница",
    5: "суббота",
    6: "воскресенье",
}


def date_words(value: date) -> str:
    return f"{value.day:02d} {MONTHS_RU[value.month]} {value.year} года"


def _direction(change: float | None) -> str:
    if change is None:
        return "сопоставимой базы пока нет"
    if change > 0:
        return f"выше на {abs(change):.1f}%"
    if change < 0:
        return f"ниже на {abs(change):.1f}%"
    return "на том же уровне"


def _direction_sentence(change: float | None) -> str:
    if change is None:
        return "Сопоставимая база для расчёта изменения отсутствует."
    if change > 0:
        return f"Это на {abs(change):.1f}% больше сопоставимого значения."
    if change < 0:
        return f"Это на {abs(change):.1f}% меньше сопоставимого значения."
    return "Показатель не изменился относительно сопоставимой базы."


def _share(value: float, total: float) -> float:
    return value / total * 100 if total else 0.0


def _corr_text(value: float | None, period_label: str) -> str:
    if value is None:
        return (
            f"Для оценки связи между ценой и количеством на {period_label} "
            "пока недостаточно наблюдений или значения почти не менялись."
        )

    absolute = abs(value)
    if absolute < 0.2:
        strength = "практически отсутствует"
    elif absolute < 0.4:
        strength = "слабая"
    elif absolute < 0.65:
        strength = "умеренная"
    else:
        strength = "заметная"

    direction = "положительная" if value > 0 else "отрицательная"

    return (
        f"На {period_label} корреляция количества продаж и средней цены "
        f"составила {value:.2f}; связь {strength} и {direction}. "
        "Этот коэффициент показывает совместное движение показателей, "
        "но сам по себе не доказывает, что изменение цены стало причиной "
        "роста или снижения спроса."
    )


def _top_name(rows: list[dict]) -> str | None:
    return str(rows[0].get("name") or "").strip() if rows else None


def build_editorial(
    report_date: date,
    sales: dict,
    plan: dict,
    stocks: dict,
    half_year: dict,
) -> dict[str, str]:
    kpi = sales.get("kpi", {})
    comparisons = sales.get("comparisons", {})

    net_revenue = number(kpi.get("amount"))
    gross_sales = number(kpi.get("sales_amount"))
    returns_amount = number(kpi.get("returns_amount"))
    net_units = number(kpi.get("total_net_sales"))
    sales_transactions = number(kpi.get("sales_transactions"))
    returns_transactions = number(kpi.get("returns_transactions"))
    avg_price = number(kpi.get("avg_price"))
    returns_rate = number(kpi.get("returns_rate"))
    margin = number(kpi.get("margin_man"))
    margin_pct = number(kpi.get("margin_percent"))
    wb_result = number(kpi.get("wb_result"))

    day_change = comparisons.get("previous_day", {}).get("change_pct")
    month_day_change = comparisons.get("previous_month_day", {}).get("change_pct")
    year_day_change = comparisons.get("previous_year_day", {}).get("change_pct")
    mtd_change = comparisons.get("mtd", {}).get("change_pct")
    ytd_change = comparisons.get("ytd", {}).get("change_pct")

    report_date_text = date_words(report_date)
    weekday = WEEKDAYS_RU[report_date.weekday()]

    top_brands = sales.get("top_brands", [])
    top_categories = sales.get("top_categories", [])
    return_categories = sales.get("return_categories", [])

    top_brand = top_brands[0] if top_brands else {}
    top_category = top_categories[0] if top_categories else {}
    top_return_category = return_categories[0] if return_categories else {}

    top_brand_share = _share(
        number(top_brand.get("revenue")),
        net_revenue,
    )
    top_category_share = _share(
        number(top_category.get("revenue")),
        net_revenue,
    )

    intro = (
        f"В выпуске за {report_date_text} собраны итог закрытого дня, "
        "сопоставимая динамика продаж, изменение средней цены, качество "
        "выручки, выполнение коммерческого плана и география товарного "
        "запаса."
    )

    # ================================================================
    # ГЛАВНЫЙ РЕДАКЦИОННЫЙ ТЕКСТ ПЕРВОЙ СТРАНИЦЫ
    # ================================================================

    lead_parts: list[str] = []

    # ---------------------------------------------------------------
    # 1. Итог дня
    # ---------------------------------------------------------------

    lead_parts.append(
        f"В {weekday}, {report_date_text}, компания завершила торговый день "
        f"с чистой выручкой {fmt_money(net_revenue)}."
    )

    # ---------------------------------------------------------------
    # 2. Продажи, возвраты и количество товара
    # ---------------------------------------------------------------

    sales_text = (
        f"За день оформлено {fmt_number(sales_transactions)} продаж "
        f"на общую сумму {fmt_money(gross_sales)}"
    )

    if returns_transactions > 0:
        sales_text += (
            f"; после обработки {fmt_number(returns_transactions)} возвратов "
            f"на сумму {fmt_money(returns_amount)} покупателям реализовано "
            f"{fmt_number(net_units)} единиц товара"
        )
    else:
        sales_text += (
            f", покупателям реализовано "
            f"{fmt_number(net_units)} единиц товара"
        )

    if avg_price > 0:
        sales_text += (
            f" при средней цене {fmt_money(avg_price)} за единицу"
        )

    lead_parts.append(
        sales_text + "."
    )

    # ---------------------------------------------------------------
    # 3. Сравнение с предыдущими периодами
    # ---------------------------------------------------------------

    comparison_parts: list[str] = []

    if day_change is not None:
        comparison_parts.append(
            f"к предыдущему торговому дню выручка "
            f"{_direction(day_change)}"
        )

    if month_day_change is not None:
        comparison_parts.append(
            f"к сопоставимой дате прошлого месяца — "
            f"{_direction(month_day_change)}"
        )

    if year_day_change is not None:
        comparison_parts.append(
            f"к аналогичному дню прошлого года — "
            f"{_direction(year_day_change)}"
        )

    if comparison_parts:
        if len(comparison_parts) == 1:
            comparison_text = comparison_parts[0]

        elif len(comparison_parts) == 2:
            comparison_text = (
                f"{comparison_parts[0]}, "
                f"а {comparison_parts[1]}"
            )

        else:
            comparison_text = (
                f"{comparison_parts[0]}, "
                f"{comparison_parts[1]}, "
                f"а {comparison_parts[2]}"
            )

        lead_parts.append(
            f"По сравнению с основными периодами: "
            f"{comparison_text}."
        )

    # ---------------------------------------------------------------
    # 4. Короткий управленческий вывод
    # ---------------------------------------------------------------

    positive_count = sum(
        change is not None and change > 0
        for change in (
            day_change,
            month_day_change,
            year_day_change,
        )
    )

    negative_count = sum(
        change is not None and change < 0
        for change in (
            day_change,
            month_day_change,
            year_day_change,
        )
    )

    if positive_count == 3:
        conclusion = (
            "Продажи превышают все ключевые ориентиры сравнения, "
            "что указывает на устойчивое усиление текущего результата."
        )

    elif negative_count == 3:
        conclusion = (
            "Результат оказался ниже всех ключевых ориентиров сравнения; "
            "при сохранении такой динамики потребуется отдельный разбор "
            "причин снижения продаж."
        )

    elif (
        day_change is not None
        and day_change > 0
        and negative_count >= 2
    ):
        conclusion = (
            "Продажи восстановились относительно предыдущего дня, "
            "однако пока не вернулись к уровням прошлого месяца "
            "и прошлого года."
        )

    elif (
        day_change is not None
        and day_change < 0
        and positive_count >= 2
    ):
        conclusion = (
            "Текущий день оказался слабее предыдущего, однако результат "
            "по-прежнему превышает более длинные исторические ориентиры."
        )

    elif positive_count > negative_count:
        conclusion = (
            "В целом динамика остаётся положительной, хотя отдельные "
            "периоды сравнения показывают более слабый результат."
        )

    elif negative_count > positive_count:
        conclusion = (
            "В целом динамика остаётся слабее исторических ориентиров, "
            "несмотря на отдельные положительные изменения."
        )

    else:
        conclusion = (
            "Динамика продаж остаётся разнонаправленной и требует "
            "наблюдения в ближайшие торговые дни."
        )

    lead_parts.append(
        conclusion
    )

    lead = " ".join(
        lead_parts
    )

    day_analysis = (
        f"Валовая сумма продаж превышает чистую выручку на "
        f"{fmt_money(max(gross_sales - net_revenue, 0))}; эта разница в первую "
        "очередь отражает возвраты и корректировки, попавшие в закрытый день. "
        f"Доля возвратов по количеству составила {fmt_pct(returns_rate)}. "
        f"Управленческая маржа сформирована в размере {fmt_money(margin)}, "
        f"что соответствует {fmt_pct(margin_pct)} чистой выручки. "
        + (
            f"Финансовый результат после расходов WB составил {fmt_money(wb_result)}. "
            if wb_result
            else ""
        )
        + (
            "Возвратность находится выше условной зоны внимания в 10%, поэтому "
            "стоит отдельно проверить категории, размеры и карточки товаров, "
            "давшие наибольшую сумму возвратов."
            if returns_rate >= 10
            else "Возвратность пока не вышла за условную зону внимания в 10%, "
            "однако её необходимо оценивать не только за один день, но и в динамике."
        )
    )

    periods = (
        f"С начала текущего месяца получено "
        f"{fmt_money(comparisons.get('mtd', {}).get('current'))} чистой выручки. "
        f"В сопоставимом количестве дней прошлого месяца было получено "
        f"{fmt_money(comparisons.get('mtd', {}).get('previous'))}; текущий темп "
        f"{_direction(mtd_change)}. С начала года накопленная чистая выручка "
        f"достигла {fmt_money(comparisons.get('ytd', {}).get('current'))}, "
        f"тогда как за аналогичный период прошлого года она составляла "
        f"{fmt_money(comparisons.get('ytd', {}).get('previous'))}; результат "
        f"{_direction(ytd_change)} год к году. "
    )

    leaders = (
        (
            f"Наибольший вклад в чистую выручку дня внёс бренд "
            f"{top_brand.get('name')}: {fmt_money(top_brand.get('revenue'))}, "
            f"или около {fmt_pct(top_brand_share)} результата дня. "
        )
        if top_brand
        else "Данные по вкладу брендов в результат дня отсутствуют. "
    ) + (
        f"В категорийном разрезе лидером стала категория "
        f"{top_category.get('name')} с выручкой "
        f"{fmt_money(top_category.get('revenue'))}, что составляет примерно "
        f"{fmt_pct(top_category_share)} чистой выручки. "
        if top_category
        else "Данные по категориям отсутствуют. "
    ) + (
        "Высокая концентрация результата в одном бренде или одной категории "
        "делает дневную выручку чувствительной к наличию, скидкам и позиции "
        "товаров-лидеров в выдаче Wildberries."
    )

    quality = (
        f"Управленческая маржинальность дня составила {fmt_pct(margin_pct)}. "
        + (
            "Это низкий уровень для устойчивого покрытия постоянных расходов; "
            "необходимо проверить себестоимость, размер скидок, комиссию и "
            "логистические расходы по товарам, сформировавшим основной объём. "
            if margin_pct < 15
            else "Показатель следует сопоставить с плановой маржинальностью и "
            "средним уровнем последних недель: один сильный день не гарантирует "
            "устойчивости результата. "
        )
        + (
            f"Максимальная сумма возвратов пришлась на категорию "
            f"{top_return_category.get('name')}: "
            f"{fmt_money(top_return_category.get('returns_amount'))}. "
            "Для неё имеет смысл проверить причины возврата, размерную сетку, "
            "описание карточек и долю проблемных SKU."
            if top_return_category
            else "В разрезе категорий возвраты за день не зафиксированы либо "
            "данные для детализации отсутствуют."
        )
    )

    price_data = sales.get("price_analysis", {})
    price = (
        "Выручка изменяется одновременно под влиянием количества проданных "
        "единиц и средней цены. Поэтому рост суммы продаж не всегда означает "
        "увеличение физического спроса: он может быть вызван более дорогим "
        "товарным миксом, меньшей скидкой или разовой продажей дорогих позиций. "
        f"{_corr_text(price_data.get('daily_corr'), 'дневном уровне за последние 90 дней')} "
        f"{_corr_text(price_data.get('monthly_corr'), 'месячном уровне за последние 12 месяцев')} "
        "Точки, заметно удалённые от основной группы на диаграмме, следует "
        "рассматривать отдельно: в такие дни могли проходить акции, меняться "
        "ассортимент продаж, возникать крупные возвраты или заканчиваться "
        "наличие товаров-лидеров."
    )

    if plan.get("available"):
        execution = number(plan.get("exec_to_date_pct"))
        delta = number(plan.get("delta_to_date"))
        plan = (
            f"К концу {report_date_text} накопленный факт месяца составил "
            f"{fmt_money(plan.get('fact_to_date'))} при распределённом плане к "
            f"дате {fmt_money(plan.get('plan_to_date'))}. План к дате выполнен "
            f"на {fmt_pct(execution)}. "
            + (
                f"Опережение графика составляет {fmt_money(abs(delta))}. "
                if delta >= 0
                else f"Отставание от графика составляет {fmt_money(abs(delta))}. "
            )
            + f"Полный план месяца равен {fmt_money(plan.get('month_plan'))}; "
            f"его текущая степень выполнения — {fmt_pct(plan.get('month_exec_pct'))}. "
            + (
                f"До конца месяца осталось {int(number(plan.get('remaining_days')))} дней, "
                f"и для закрытия полного плана необходим средний темп "
                f"{fmt_money(plan.get('required_daily_rate'))} в день."
                if number(plan.get("remaining_days")) > 0
                else "Месяц завершён, поэтому необходимый темп на оставшиеся дни равен нулю."
            )
        )
    else:
        plan = (
            "Месячный план-факт не рассчитан. Необходимо проверить наличие "
            "активной бюджетной версии и корректность распределения месячного "
            "плана по дням."
        )

    if half_year.get("available"):
        half_year_text = (
            f"За текущее полугодие выполнено "
            f"{fmt_pct(half_year.get('execution_pct'))} полного плана, или "
            f"{fmt_money(half_year.get('fact_amount'))} из "
            f"{fmt_money(half_year.get('plan_amount'))}. План, который должен "
            f"быть выполнен именно к выбранной дате, закрыт на "
            f"{fmt_pct(half_year.get('execution_to_date_pct'))}. "
            f"Календарный прогресс равен {fmt_pct(half_year.get('calendar_pct'))}: "
            "это доля уже прошедших календарных дней полугодия. Он не является "
            "самостоятельным планом продаж и используется только как простой "
            "ориентир времени. Если месяцы внутри полугодия имеют разные планы, "
            "доля прошедших дней и доля выполненного плана закономерно могут "
            "отличаться. Главный операционный показатель — выполнение "
            "распределённого плана к дате."
        )
    else:
        half_year_text = "Полугодовой план по соглашению с Wildberries не рассчитан."

    if stocks.get("available"):
        total = number(stocks.get("total_qty"))
        on_hand = number(stocks.get("on_hand"))
        transit = number(stocks.get("in_transit"))
        transit_share = number(stocks.get("transit_share"))
        regions = stocks.get("regions", [])
        warehouses = stocks.get("top_warehouses", [])
        top_region = regions[0] if regions else {}
        top_warehouse = warehouses[0] if warehouses else {}

        stock = (
            f"На дату снимка в товарном контуре учитывается "
            f"{fmt_number(total)} единиц по {fmt_number(stocks.get('products'))} NM ID. "
            f"На складах находится {fmt_number(on_hand)} единиц, ещё "
            f"{fmt_number(transit)} единиц находятся в пути к клиенту или от клиента. "
            f"Таким образом, доля товара в пути составляет {fmt_pct(transit_share)} "
            
        )

        geography = (
            (
                f"Крупнейшая географическая зона — {top_region.get('region')}: "
                f"{fmt_number(top_region.get('total_qty'))} единиц, или около "
                f"{fmt_pct(stocks.get('top_region_share'))} общего запаса. "
                f"В этой зоне задействовано {fmt_number(top_region.get('warehouses'))} складов, "
                f"а в пути находится {fmt_number(top_region.get('in_transit'))} единиц. "
                if top_region
                else "Региональная разбивка запасов не сформирована. "
            )
            + (
                f"Самая крупная отдельная складская точка — "
                f"{top_warehouse.get('warehouse_name')}: "
                f"{fmt_number(top_warehouse.get('total_qty'))} единиц, или "
                f"{fmt_pct(stocks.get('top_warehouse_share'))} общего товарного контура. "
                if top_warehouse
                else "Разбивка по отдельным складам отсутствует. "
            )
            + "Чем выше концентрация товара в одной зоне или на одном складе, "
            "тем сильнее компания зависит от его загрузки, сроков приёмки и "
            "локального спроса. Карта показывает общий запас как сумму товара "
            "на складах и товара в пути; подписи дополнительно показывают число "
            "складов и объём в пути."
        )
    else:
        stock = "Актуальный снимок товарных остатков на выбранную дату не найден."
        geography = "Региональная аналитика не построена из-за отсутствия снимка остатков."

    closing = (
        "Главная задача выпуска — не просто зафиксировать итоговую сумму, а "
        "связать её с физическим количеством продаж, средней ценой, возвратами, "
        "маржой, плановым темпом и наличием товара. После прочтения стоит "
        "проверить три вопроса: какие товары действительно создали результат, "
        "какие отклонения могут повториться в ближайшие дни и достаточно ли "
        "доступного запаса в тех регионах, где формируется спрос."
    )

    return {
        "intro": intro,
        "lead": lead,
        "day_analysis": day_analysis,
        "periods": periods,
        "leaders": leaders,
        "quality": quality,
        "price": price,
        "plan": plan,
        "half_year": half_year_text,
        "stocks": stock,
        "geography": geography,
        "closing": closing,
    }


def build_recommendations(payload: dict[str, Any]) -> list[dict]:
    result: list[dict] = []

    sales = payload.get("sales", {})
    kpi = sales.get("kpi", {})
    comparisons = sales.get("comparisons", {})

    month_change = comparisons.get("mtd", {}).get("change_pct")

    if month_change is not None and month_change <= -5:
        result.append(
            {
                "level": "warning",
                "title": "Вернуть месячный темп",
                "text": (
                    f"MTD ниже сопоставимого периода на {abs(month_change):.1f}%. "
                    "Разберите вклад количества продаж, средней цены, брендов, "
                    "категорий и отсутствия товаров-лидеров."
                ),
            }
        )

    if number(kpi.get("returns_rate")) >= 10:
        result.append(
            {
                "level": "danger",
                "title": "Разобрать возвраты",
                "text": (
                    "Проверьте категории с наибольшей суммой возвратов, причины "
                    "по SKU, размерную сетку, описание карточек и качество товара."
                ),
            }
        )

    if number(kpi.get("margin_percent")) < 15:
        result.append(
            {
                "level": "warning",
                "title": "Защитить маржу",
                "text": (
                    "Проверьте скидки, комиссию Wildberries, логистику, стоимость "
                    "хранения и себестоимость товаров, давших основную выручку."
                ),
            }
        )

    stocks = payload.get("stocks", {})
    transit_share = number(stocks.get("transit_share"))

    if transit_share >= 30:
        result.append(
            {
                "level": "info",
                "title": "Контролировать товар в пути",
                "text": (
                    f"В пути находится {transit_share:.1f}% общего запаса. "
                    "Проверьте сроки приёмки крупнейших складов и долю товара, "
                    "который пока недоступен для немедленной продажи."
                ),
            }
        )

    if number(stocks.get("top_warehouse_share")) >= 25:
        result.append(
            {
                "level": "info",
                "title": "Снизить складскую концентрацию",
                "text": (
                    f"На крупнейший склад приходится "
                    f"{number(stocks.get('top_warehouse_share')):.1f}% общего запаса. "
                    "Оцените соответствие такой концентрации региональному спросу."
                ),
            }
        )

    if number(kpi.get("no_cost")) > 0:
        result.append(
            {
                "level": "danger",
                "title": "Закрыть себестоимость",
                "text": (
                    f"Есть {int(number(kpi.get('no_cost')))} операций без "
                    "себестоимости. До исправления маржа и финансовый результат "
                    "могут быть искажены."
                ),
            }
        )

    plan = payload.get("plan", {})
    if plan.get("available") and number(plan.get("exec_to_date_pct")) < 100:
        result.append(
            {
                "level": "info",
                "title": "Держать дневной ориентир",
                "text": (
                    f"До конца месяца нужен средний темп "
                    f"{fmt_money(plan.get('required_daily_rate'))} в день. "
                    "Сопоставляйте фактический темп с наличием и активностью "
                    "товаров, которые обычно формируют основной объём."
                ),
            }
        )

    if not result:
        result.append(
            {
                "level": "positive",
                "title": "Критичных отклонений нет",
                "text": (
                    "Сохраните ежедневный контроль темпа, возвратов, маржи, "
                    "средней цены и географии запасов."
                ),
            }
        )

    return result[:6]
