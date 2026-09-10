# budget/reporting/pdf/analytics/sales_analytics.py

from __future__ import annotations

import math

from budget.reporting.pdf.utils.formatters import format_corr, format_pct_signed
from budget.reporting.pdf.utils.math_utils import safe_corr, safe_pct_change


def _strength(abs_value: float) -> str:
    if abs_value >= 0.7:
        return "сильная"
    if abs_value >= 0.4:
        return "умеренная"
    if abs_value >= 0.2:
        return "слабая"
    return "очень слабая"


def _short_corr_comment(value: float | None) -> str:
    if value is None:
        return "Недостаточно данных для надежного вывода."

    abs_value = abs(value)

    if abs_value < 0.2:
        return (
            "Линейная связь практически не выражена: изменение одного показателя "
            "не объясняет динамику второго."
        )

    if value > 0:
        return (
            "Положительное значение означает, что показатели в среднем менялись в одном направлении: "
            "при росте одного чаще рос и второй."
        )

    return (
        "Отрицательное значение означает, что показатели в среднем менялись в противоположных направлениях: "
        "при росте одного второй чаще снижался."
    )


def _interpret_corr(value: float | None, pair_code: str) -> tuple[str, str, str]:
    if value is None:
        return (
            "Недостаточно данных",
            "flat",
            "Для надежного вывода требуется более длинный временной ряд или большая вариативность показателей.",
        )

    abs_value = abs(value)
    strength = _strength(abs_value)

    if value > 0.05:
        direction = "прямая"
        css_class = "up"
    elif value < -0.05:
        direction = "обратная"
        css_class = "down"
    else:
        direction = "нейтральная"
        css_class = "flat"

    if direction == "нейтральная":
        text = "Линейная связь практически отсутствует"
    else:
        text = f"{strength} {direction} связь"

    if pair_code == "price_revenue":
        if direction == "прямая":
            meaning = (
                "Рост средней цены в анализируемом периоде, как правило, сопровождался ростом чистой выручки. "
                "Это может означать, что выручка поддерживается не только объемом, но и ценовым уровнем."
            )
        elif direction == "обратная":
            meaning = (
                "Рост средней цены сопровождался снижением чистой выручки. "
                "Это может указывать на чувствительность спроса к цене или на сужение объема продаж при повышении цены."
            )
        else:
            meaning = (
                "Чистая выручка изменялась в основном не из-за цены, а за счет других факторов: количества продаж, "
                "ассортимента, возвратов или сезонности."
            )

    elif pair_code == "qty_price":
        if direction == "прямая":
            meaning = (
                "Увеличение количества продаж сопровождалось ростом средней цены. "
                "Это благоприятный сценарий, при котором компания одновременно наращивает объем и сохраняет ценность продажи."
            )
        elif direction == "обратная":
            meaning = (
                "При росте количества продаж средняя цена, как правило, снижалась. "
                "Это может означать работу через скидки, промо-механику, изменение товарного микса "
                "или смещение спроса в более дешевый сегмент."
            )
        else:
            meaning = (
                "Количество продаж и средняя цена менялись независимо друг от друга. "
                "Это означает, что масштаб продаж не был жестко связан с ценовым уровнем."
            )

    else:
        if direction == "прямая":
            meaning = (
                "Рост количества продаж сопровождался ростом чистой выручки. "
                "Следовательно, объем реализации выступает ключевым драйвером выручки."
            )
        elif direction == "обратная":
            meaning = (
                "Рост количества продаж не приводил к увеличению чистой выручки. "
                "Это может означать снижение средней цены, ухудшение товарного микса или усиление возвратов."
            )
        else:
            meaning = (
                "Чистая выручка зависела не только от количества продаж; существенную роль играли цена, возвраты "
                "или структура реализованного ассортимента."
            )

    return text, css_class, meaning


def build_sales_auto_comment(month_rows: list[dict]) -> str | None:
    if not month_rows or len(month_rows) < 2:
        return None

    current = month_rows[-1]
    prev = month_rows[-2]

    cur_net = float(current.get("net_amount") or 0)
    prev_net = float(prev.get("net_amount") or 0)

    cur_price = float(current.get("avg_price") or 0)
    prev_price = float(prev.get("avg_price") or 0)

    cur_qty = float(current.get("sales_qty") or 0)
    prev_qty = float(prev.get("sales_qty") or 0)

    delta_net = safe_pct_change(cur_net, prev_net)
    delta_price = safe_pct_change(cur_price, prev_price)
    delta_qty = safe_pct_change(cur_qty, prev_qty)

    def trend_word(v: float | None, noun_up: str, noun_down: str):
        if v is None:
            return "существенных изменений не зафиксировано"
        if v > 0.1:
            return f"{noun_up} на {format_pct_signed(abs(v)).lstrip('+')}"
        if v < -0.1:
            return f"{noun_down} на {format_pct_signed(abs(v)).lstrip('+')}"
        return "существенных изменений не зафиксировано"

    net_phrase = trend_word(delta_net, "рост", "снижение")
    price_phrase = trend_word(delta_price, "рост", "снижение")
    qty_phrase = trend_word(delta_qty, "рост", "снижение")

    comment = (
        f"В {current.get('month_label')} чистая выручка составила "
        f"{(cur_net / 1_000_000):.1f} млн руб.; ".replace(".", ",")
        + f"по сравнению с предыдущим месяцем зафиксирован {net_phrase}. "
        f"Средняя цена продажи показала {price_phrase}, количество продаж — {qty_phrase}. "
    )

    if delta_net is not None and delta_qty is not None and delta_price is not None:
        if delta_qty > 0.1 and delta_price <= 0.1:
            comment += "Основным фактором изменения выручки, вероятно, выступила динамика объема продаж."
        elif delta_price > 0.1 and delta_qty <= 0.1:
            comment += "Основным фактором изменения выручки, вероятно, выступило изменение средней цены."
        elif delta_price > 0.1 and delta_qty > 0.1:
            comment += "Выручка поддерживалась одновременно ростом средней цены и объема продаж."
        elif delta_price < -0.1 and delta_qty < -0.1:
            comment += "Снижение выручки происходило одновременно на фоне ослабления спроса и ухудшения ценовой динамики."
        else:
            comment += "Динамика выручки носит смешанный характер и формируется под влиянием одновременно нескольких факторов."

    return comment


def build_sales_correlation_context(month_rows: list[dict]) -> dict | None:
    if not month_rows:
        return None

    price = [float(row.get("avg_price") or 0) for row in month_rows]
    net_revenue = [float(row.get("net_amount") or 0) for row in month_rows]
    qty = [float(row.get("sales_qty") or 0) for row in month_rows]

    corr_price_revenue = safe_corr(price, net_revenue)
    corr_qty_price = safe_corr(qty, price)
    corr_qty_revenue = safe_corr(qty, net_revenue)

    pr_text, pr_class, pr_meaning = _interpret_corr(corr_price_revenue, "price_revenue")
    qp_text, qp_class, qp_meaning = _interpret_corr(corr_qty_price, "qty_price")
    qr_text, qr_class, qr_meaning = _interpret_corr(corr_qty_revenue, "qty_revenue")

    driver_comment = (
        "По итогам корреляционного анализа основной вывод следует делать по наибольшей по модулю связи."
    )

    candidates = [
        ("цена и выручка", corr_price_revenue),
        ("количество и цена", corr_qty_price),
        ("количество и выручка", corr_qty_revenue),
    ]
    valid = [(name, val) for name, val in candidates if val is not None]

    if valid:
        best_name, best_val = max(valid, key=lambda x: abs(x[1]))
        if abs(best_val) >= 0.7:
            driver_comment = (
                f"Наиболее выраженная связь наблюдается между показателями «{best_name}» "
                f"(коэффициент {format_corr(best_val)}). "
                f"Это означает, что именно эта пара в наибольшей степени объясняет изменения внутри анализируемого периода."
            )
        elif abs(best_val) >= 0.4:
            driver_comment = (
                f"Наиболее заметная, но не доминирующая связь наблюдается между показателями «{best_name}» "
                f"(коэффициент {format_corr(best_val)}). "
                f"Связь присутствует, однако для управленческих выводов ее следует рассматривать совместно с сезонностью, ассортиментом и возвратами."
            )
        else:
            driver_comment = (
                "Выраженных линейных зависимостей между анализируемыми показателями не выявлено. "
                "Это означает, что динамика продаж формируется под влиянием нескольких факторов одновременно."
            )

    general_note = (
        "Коэффициент корреляции принимает значения от -1 до +1. "
        "Положительное значение означает движение показателей в одном направлении, отрицательное — в противоположных. "
        "Чем ближе значение по модулю к 1, тем сильнее линейная связь."
    )

    return {
        "general_note": general_note,
        "price_revenue": {
            "value": format_corr(corr_price_revenue),
            "text": pr_text,
            "class": pr_class,
            "meaning": pr_meaning,
            "short_comment": _short_corr_comment(corr_price_revenue),
        },
        "qty_price": {
            "value": format_corr(corr_qty_price),
            "text": qp_text,
            "class": qp_class,
            "meaning": qp_meaning,
            "short_comment": _short_corr_comment(corr_qty_price),
        },
        "qty_revenue": {
            "value": format_corr(corr_qty_revenue),
            "text": qr_text,
            "class": qr_class,
            "meaning": qr_meaning,
            "short_comment": _short_corr_comment(corr_qty_revenue),
        },
        "driver_comment": driver_comment,
    }


def _interpret_daily_corr(value: float | None) -> str:
    if value is None:
        return (
            "Недостаточно данных для анализа дневной корреляции. "
            "Для устойчивого вывода нужен более длинный ряд наблюдений."
        )

    abs_value = abs(value)
    if abs_value < 0.2:
        return (
            "На дневном уровне выраженной линейной связи между количеством продаж и средней ценой не наблюдается. "
            "Это означает, что краткосрочные всплески продаж, вероятно, зависят от нескольких факторов одновременно."
        )

    if value < 0:
        return (
            "Отрицательная дневная корреляция указывает, что в дни роста количества продаж средняя цена чаще снижалась. "
            "Это характерно для промо-акций, скидок, распродаж и смещения спроса в более доступный ассортимент."
        )

    return (
        "Положительная дневная корреляция указывает, что в дни роста количества продаж средняя цена также имела тенденцию к росту. "
        "Это может говорить о сильном спросе без необходимости агрессивного ценового стимулирования."
    )


def build_daily_correlation_context(daily_rows: list[dict]) -> dict | None:
    if not daily_rows:
        return None

    qty = [float(row.get("sales_qty") or 0) for row in daily_rows]
    price = [float(row.get("avg_price") or 0) for row in daily_rows]

    corr = safe_corr(qty, price)
    return {
        "value": format_corr(corr),
        "comment": _interpret_daily_corr(corr),
        "note": (
            "Дневная корреляция более чувствительна к промо-акциям, выходным, праздничным дням, "
            "маркетинговым активностям и разовым всплескам спроса, чем месячная."
        ),
    }


def build_qty_price_auto_comment(month_rows: list[dict]) -> str | None:
    if not month_rows or len(month_rows) < 2:
        return None

    current = month_rows[-1]
    prev = month_rows[-2]

    cur_qty = float(current.get("sales_qty") or 0)
    prev_qty = float(prev.get("sales_qty") or 0)

    cur_price = float(current.get("avg_price") or 0)
    prev_price = float(prev.get("avg_price") or 0)

    delta_qty = safe_pct_change(cur_qty, prev_qty)
    delta_price = safe_pct_change(cur_price, prev_price)

    def _trend_text(value: float | None, noun_up: str, noun_down: str) -> str:
        if value is None:
            return "без сопоставимой базы"
        if value > 0.1:
            return f"{noun_up} на {format_pct_signed(abs(value)).lstrip('+')}"
        if value < -0.1:
            return f"{noun_down} на {format_pct_signed(abs(value)).lstrip('+')}"
        return "без существенных изменений"

    qty_text = _trend_text(delta_qty, "рост", "снижение")
    price_text = _trend_text(delta_price, "рост", "снижение")

    comment = (
        f"В {current.get('month_label')} количество продаж составило "
        f"{int(round(cur_qty)):,} шт., средняя цена — {cur_price:,.0f} руб./шт. "
        f"По сравнению с предыдущим месяцем по количеству зафиксирован {qty_text}, "
        f"по средней цене — {price_text}. "
    ).replace(",", " ")

    if delta_qty is not None and delta_price is not None:
        if delta_qty > 0.1 and delta_price > 0.1:
            comment += (
                "Наблюдается одновременное усиление объема продаж и ценового уровня, "
                "что свидетельствует о сильной текущей коммерческой динамике."
            )
        elif delta_qty > 0.1 and delta_price < -0.1:
            comment += (
                "Объем продаж растет при одновременном снижении средней цены; "
                "это может быть следствием промо-активности, скидок или смещения спроса в более доступный ассортимент."
            )
        elif delta_qty < -0.1 and delta_price > 0.1:
            comment += (
                "Средняя цена растет при снижении количества продаж; "
                "это может указывать на повышение цены, изменение товарного микса или снижение чувствительности части спроса."
            )
        elif delta_qty < -0.1 and delta_price < -0.1:
            comment += (
                "И количество продаж, и средняя цена снижаются, что требует дополнительной проверки причин: "
                "сезонность, ассортимент, маркетинговая активность или усиление возвратов."
            )
        else:
            comment += (
                "Динамика носит смешанный характер и требует совместной оценки количества продаж, цены и структуры ассортимента."
            )

    return comment




