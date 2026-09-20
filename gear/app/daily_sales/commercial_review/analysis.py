# gear/app/daily_sales/commercial_review/analysis.py
"""
Движок выводов коммерческого обзора.

Отличие от прежней версии: вывод не срабатывает по порогу, а
раскладывает отклонение на причины и называет их в рублях.
«Выручка ниже на 12%» — это не вывод. Вывод — «выручка ниже
на 12%, из них 9 п.п. дал спад количества и 3 п.п. цена».

Каждая находка отвечает на три вопроса:
  что произошло  — факт с цифрой;
  почему         — разложение или конкретный виновник;
  что делать     — одно действие, а не список областей для изучения.

Если причину назвать не получается, находка не пишется вообще.
Общая фраза хуже молчания: она занимает место и создаёт
ощущение, что вопрос разобран.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from . import config as C
from .formats import (
    as_date,
    date_short as fmt_date,
    level_pct,
    days as fmt_days,
    hours as fmt_hours,
    money,
    num,
    pct,
    plural,
    pp,
    qty as fmt_qty,
    signed_money,
    signed_pct,
)


# ============================================================
# НАХОДКА
# ============================================================

@dataclass
class Finding:
    """
    Один вывод отчёта.

    severity — насколько срочно; от неё зависит и порядок,
    и цвет плашки. scope — к какому разделу относится,
    чтобы находку можно было показать рядом с её графиком.
    """

    severity: str          # critical | serious | warning | good | neutral
    scope: str             # sales | plan | finance | stocks | price | fbs | data
    title: str
    fact: str
    cause: str = ""
    action: str = ""
    metric: str = ""       # короткая цифра для плашки
    weight: float = 0.0    # вес в рублях, для сортировки внутри severity
    live: bool = False     # верно "прямо сейчас", а не на report_date --
                            # такие находки не попадают на страницу 1

    def sort_key(self):
        return (
            C.SEVERITY_ORDER.get(self.severity, 9),
            -abs(self.weight),
        )


def _rows(payload, *path):
    """Достаёт вложенное значение, не падая на пустых узлах."""
    node = payload
    for key in path:
        if not isinstance(node, dict):
            return None
        node = node.get(key)
    return node


# ============================================================
# 1. ВЫРУЧКА: РАЗЛОЖЕНИЕ НА КОЛИЧЕСТВО И ЦЕНУ
# ============================================================

def _period_stats(rows, start, end):
    """
    Количество, продажи, возвраты и чистая выручка за отрезок.

    Считаем по одному контуру — тому же, из которого берутся
    карточки и календарь: продажи и возвраты по строкам
    реализации. Разные витрины дают разную выручку за одну
    и ту же неделю, и если разложение взять из другой, отчёт
    начнёт спорить сам с собой.

        продажи  = сумма продаж без учёта возвратов
        возвраты = сумма возвратов
        чистая   = продажи - возвраты

    Средняя цена считается только по продажам: возвраты
    участвуют отдельным фактором, иначе их всплеск выглядел
    бы как падение цены.
    """
    total_qty = 0.0
    gross = 0.0
    returns = 0.0
    net = 0.0

    for row in rows or []:
        d = as_date(row.get("date_from"))
        if d is None or d < start or d > end:
            continue

        total_qty += num(row.get("sales_transactions")) or 0.0
        gross += num(row.get("sales_amount")) or 0.0
        returns += num(row.get("returns_amount")) or 0.0
        net += num(row.get("amount")) or 0.0

    return {
        "qty": total_qty,
        "gross": gross,
        "returns": returns,
        "amount": net,
        "price": gross / total_qty if total_qty else None,
    }


def week_bounds(report_date):
    """
    Границы календарных недель вокруг даты отчёта.

    Неделя считается с понедельника по воскресенье. Если
    текущая неделя ещё не закрыта, сравнивать её с полной
    нельзя — падение получится не от плохой торговли,
    а от нехватки дней. Поэтому за «текущую» берём последнюю
    ЗАКРЫТУЮ неделю, а незакрытую отдаём отдельно, чтобы
    отчёт мог честно про неё написать.
    """
    this_monday = report_date - timedelta(days=report_date.weekday())
    complete = report_date.weekday() == 6

    if complete:
        cur_start, cur_end = this_monday, report_date
        running = None
    else:
        cur_start = this_monday - timedelta(days=7)
        cur_end = this_monday - timedelta(days=1)
        running = {
            "start": this_monday,
            "end": report_date,
            "days": report_date.weekday() + 1,
        }

    return {
        "cur_start": cur_start,
        "cur_end": cur_end,
        "prev_start": cur_start - timedelta(days=7),
        "prev_end": cur_start - timedelta(days=1),
        "running": running,
    }


def decompose_revenue(payload, window=None):
    """
    Раскладывает изменение чистой выручки на три фактора.

    Сравниваются две соседние КАЛЕНДАРНЫЕ недели, понедельник —
    воскресенье. Скользящее окно «последние 7 дней» выглядит
    похоже, но говорить «за неделю» про него нельзя: у бизнеса
    неделя — это отрезок в календаре, по нему ставят задачи
    и подводят итоги.

        вклад количества = (Q1 - Q0) * P0
        вклад цены       = (P1 - P0) * Q1
        вклад возвратов  = -(R1 - R0)

    Чистая выручка = количество * цена - возвраты, поэтому
    сумма трёх вкладов точно равна её изменению.

    Возвраты вынесены отдельным фактором намеренно: в исходных
    данных avg_price считается только по продажам, а net_amount
    уже очищен от возвратов. Если этого не разделить, всплеск
    возвратов выглядит как падение средней цены — и решение
    принимается не по той причине.
    """
    # Берём тот же ряд, что и календарь выручки: одна витрина
    # на весь отчёт — иначе недельный итог в календаре
    # и в разложении не совпадут, и доверия не будет ни к чему.
    rows = _rows(payload, "sales", "trend")
    report_date = as_date(payload.get("report_date"))

    if not rows or report_date is None:
        return None

    bounds = week_bounds(report_date)

    cur = _period_stats(rows, bounds["cur_start"], bounds["cur_end"])
    prev = _period_stats(rows, bounds["prev_start"], bounds["prev_end"])

    if not cur["qty"] or not prev["qty"]:
        return None
    if cur["price"] is None or prev["price"] is None:
        return None

    qty_effect = (cur["qty"] - prev["qty"]) * prev["price"]
    price_effect = (cur["price"] - prev["price"]) * cur["qty"]
    returns_effect = -(cur["returns"] - prev["returns"])
    total = cur["amount"] - prev["amount"]

    change_pct = (
        100.0 * total / prev["amount"] if prev["amount"] else None
    )

    running = bounds["running"]
    running_stats = None

    if running:
        running_stats = _period_stats(
            rows, running["start"], running["end"]
        )
        running_stats.update(running)

    return {
        "current": cur,
        "previous": prev,
        "cur_start": bounds["cur_start"],
        "cur_end": bounds["cur_end"],
        "prev_start": bounds["prev_start"],
        "prev_end": bounds["prev_end"],
        "running": running_stats,
        "total": total,
        "qty_effect": qty_effect,
        "price_effect": price_effect,
        "returns_effect": returns_effect,
        "change_pct": change_pct,
        "qty_change_pct": (
            100.0 * (cur["qty"] - prev["qty"]) / prev["qty"]
            if prev["qty"] else None
        ),
        "price_change_pct": (
            100.0 * (cur["price"] - prev["price"]) / prev["price"]
            if prev["price"] else None
        ),
    }


def _revenue_findings(payload):
    out = []

    split = decompose_revenue(payload, window=7)

    if split and split["change_pct"] is not None:
        change = split["change_pct"]
        qty_effect = split["qty_effect"]
        price_effect = split["price_effect"]

        if abs(change) >= C.NOISE_PCT:
            qty_effect = split["qty_effect"]
            price_effect = split["price_effect"]
            returns_effect = split["returns_effect"]

            factors = [
                ("количество", qty_effect),
                ("средняя цена", price_effect),
                ("возвраты", returns_effect),
            ]

            factors.sort(key=lambda item: -abs(item[1]))
            driver, driver_value = factors[0]

            direction = "выше" if change > 0 else "ниже"
            severity = (
                "good" if change > 0
                else ("critical" if change <= -C.ALERT_PCT else "warning")
            )

            cause = (
                f"Считаем по трём факторам: количество дало "
                f"{signed_money(qty_effect)}, средняя цена — "
                f"{signed_money(price_effect)}, возвраты — "
                f"{signed_money(returns_effect)}. Больше всего "
                f"повлияло: {driver} ({signed_money(driver_value)})."
            )

            if driver == "возвраты":
                action = (
                    "Главный фактор здесь не продажи, а возвраты. "
                    "Смотреть надо категории с самым большим "
                    "возвратом: размерная сетка, фото, описание. "
                    "Менять цену в такой ситуации бессмысленно."
                )
            elif driver == "количество" and qty_effect < 0:
                action = (
                    "Смотреть надо не на цену, а на спрос: наличие "
                    "товаров-лидеров, позиции в выдаче и рекламу. "
                    "Снижать цену при падающем количестве — значит "
                    "терять и объём, и маржу."
                )
            elif driver == "количество" and qty_effect > 0:
                action = (
                    "Рост держится на количестве, а не на скидке — "
                    "это здоровый рост. Проверьте, хватит ли запаса "
                    "держать такой темп."
                )
            elif price_effect < 0:
                action = (
                    "Падение средней цены при сохранившемся количестве — "
                    "обычно это скидка, которая не окупилась объёмом. "
                    "Проверьте, по каким брендам она давалась. "
                    "Учтите и смену ассортимента: средняя цена падает "
                    "сама, если больше продаётся дешёвых позиций."
                )
            else:
                action = (
                    "Цена выросла без потери количества — редкий и "
                    "хороший случай. Стоит понять, на каких позициях "
                    "это получилось, и повторить."
                )

            out.append(Finding(
                severity=severity,
                scope="sales",
                title=(
                    f"Выручка за неделю {direction} "
                    f"на {pct(abs(change))}"
                ),
                metric=signed_pct(change),
                fact=(
                    f"Неделя {fmt_date(split['cur_start'])}–"
                    f"{fmt_date(split['cur_end'])}: "
                    f"{money(split['current']['amount'])} против "
                    f"{money(split['previous']['amount'])} "
                    f"за {fmt_date(split['prev_start'])}–"
                    f"{fmt_date(split['prev_end'])} — разница "
                    f"{signed_money(split['total'])}. "
                    f"Продано "
                    f"{fmt_qty(split['current']['qty'])} "
                    f"{plural(split['current']['qty'], 'штука', 'штуки', 'штук')} "
                    f"по средней цене "
                    f"{money(split['current']['price'])}, "
                    f"возвращено на "
                    f"{money(split['current']['returns'])}."
                ),
                cause=cause,
                action=action,
                weight=abs(split["total"]),
            ))

    # Незакрытая неделя не участвует в сравнении, но молчать
    # про неё нельзя: её цифры уже видно в дашборде.
    running = (split or {}).get("running")

    if running and running.get("qty"):
        out.append(Finding(
            severity="neutral",
            scope="sales",
            title="Текущая неделя ещё не закрыта",
            metric=money(running.get("amount")),
            fact=(
                f"С {fmt_date(running['start'])} по "
                f"{fmt_date(running['end'])} прошло "
                f"{fmt_days(running['days'])} из семи, "
                f"выручка {money(running.get('amount'))} "
                f"при средней цене {money(running.get('price'))}."
            ),
            cause=(
                "В сравнении недель она не участвует: сравнивать "
                "неполную неделю с полной — значит получить "
                "падение там, где просто меньше дней."
            ),
            weight=0,
        ))

    # --- год к году -------------------------------------------------
    ytd = _rows(payload, "sales", "comparisons", "ytd") or {}
    ytd_change = num(ytd.get("change_pct"))

    if ytd_change is not None and abs(ytd_change) >= C.NOISE_PCT:
        out.append(Finding(
            severity="good" if ytd_change > 0 else "warning",
            scope="sales",
            title=(
                "С начала года "
                + ("опережаем" if ytd_change > 0 else "отстаём от")
                + " прошлый год"
            ),
            metric=signed_pct(ytd_change),
            fact=(
                f"{money(ytd.get('current'))} против "
                f"{money(ytd.get('previous'))} за тот же отрезок "
                f"прошлого года, разница "
                f"{signed_money(ytd.get('delta'))}."
            ),
            action=(
                ""
                if ytd_change > 0
                else "Разрыв копится с начала года — наверстать "
                     "его разовой акцией не получится, нужен "
                     "пересмотр плана на остаток года."
            ),
            weight=abs(num(ytd.get("delta")) or 0),
        ))

    # --- возвраты ---------------------------------------------------
    kpi = _rows(payload, "sales", "kpi") or {}
    returns_rate = num(kpi.get("returns_rate"))

    if returns_rate is not None and returns_rate >= C.RETURNS_ALERT_PCT:
        cats = _rows(payload, "sales", "return_categories") or []
        top = cats[0] if cats else None

        cause = ""
        if top:
            cause = (
                f"Больше всего возвращают в категории "
                f"«{top.get('name')}»: "
                f"{money(top.get('returns_amount'))} "
                f"за день."
            )

        out.append(Finding(
            severity="serious" if returns_rate >= 15 else "warning",
            scope="sales",
            title=f"Возвраты {pct(returns_rate)} от числа продаж",
            metric=pct(returns_rate),
            fact=(
                f"На каждые 100 проданных единиц приходится "
                f"{pct(returns_rate)} возвратов. В деньгах это "
                f"{money(kpi.get('returns_amount'))} при продажах "
                f"{money(kpi.get('sales_amount'))} — "
                f"{pct(100.0 * (num(kpi.get('returns_amount')) or 0) / (num(kpi.get('sales_amount')) or 1))} "
                f"от суммы."
            ),
            cause=cause,
            action=(
                "Возврат съедает не только выручку, но и логистику "
                "в обе стороны. Начните с карточек этой категории: "
                "размерная сетка, фото, описание."
            ),
            weight=num(kpi.get("returns_amount")) or 0,
        ))

    return out


# ============================================================
# 2. ПЛАН
# ============================================================

def _plan_findings(payload):
    out = []
    plan = payload.get("plan") or {}

    if not plan.get("available"):
        return out

    exec_pct = num(plan.get("exec_to_date_pct"))
    delta = num(plan.get("delta_to_date"))
    required = num(plan.get("required_daily_rate"))
    remaining_days = num(plan.get("remaining_days")) or 0
    fact_to_date = num(plan.get("fact_to_date")) or 0

    if exec_pct is None:
        return out

    # текущий темп, чтобы сравнить с требуемым
    rows = plan.get("rows") or []
    done_days = len([r for r in rows if num(r.get("fact"))])
    current_rate = fact_to_date / done_days if done_days else None

    if exec_pct < C.PLAN_BEHIND_PCT:
        gap = ""
        if current_rate and required:
            ratio = 100.0 * (required / current_rate - 1)
            if ratio > 0:
                gap = (
                    f"Чтобы закрыть месяц по плану, оставшиеся "
                    f"{fmt_days(remaining_days)} нужно делать по "
                    f"{money(required)} в день — это на "
                    f"{pct(ratio)} выше текущего темпа "
                    f"({money(current_rate)} в день)."
                )
            else:
                gap = (
                    f"Требуемый темп {money(required)} в день ниже "
                    f"текущего — план закроется, если ничего "
                    f"не ухудшится."
                )

        realistic = (
            current_rate and required and required / current_rate > 1.3
        )

        out.append(Finding(
            severity="critical" if realistic else "warning",
            scope="plan",
            title=f"План месяца выполнен на {pct(exec_pct)}",
            metric=pct(exec_pct),
            fact=(
                f"Факт {money(fact_to_date)} против плана "
                f"{money(plan.get('plan_to_date'))} на эту дату, "
                f"отставание {signed_money(delta)}."
                "Корректировка плана пока не проведена: в отчёте используется "
                "первоначальный план, утверждённый в начале года, без учёта последствий "
                "пожаров и потери товара."
            ),
            cause=gap,
            action=(
                "Разрыв больше трети текущего темпа — арифметически "
                "он уже не закрывается обычной работой. Либо "
                "отдельная акция с посчитанной экономикой, либо "
                "честный пересмотр плана."
                if realistic else
                "Разрыв в пределах досягаемости. Держите темп "
                "и следите, чтобы лидеры продаж не уходили в ноль "
                "по остаткам."
            ),
            weight=abs(delta or 0),
        ))

    elif exec_pct >= C.PLAN_AHEAD_PCT:
        out.append(Finding(
            severity="good",
            scope="plan",
            title=f"План месяца перевыполняется: {pct(exec_pct)}",
            metric=pct(exec_pct),
            fact=(
                f"Факт {money(fact_to_date)} против плана "
                f"{money(plan.get('plan_to_date'))}, "
                f"опережение {signed_money(delta)}."
            ),
            action=(
                "Проверьте остатки по позициям, которые дают это "
                "опережение: закончиться в середине месяца — "
                "обычный способ потерять перевыполнение."
            ),
            weight=abs(delta or 0),
        ))

    # --- полугодие --------------------------------------------------
    half = payload.get("half_year_wb_plan") or {}

    if half.get("available"):
        pace = num(half.get("pace_delta_pp"))
        if pace is not None and abs(pace) >= 5:
            out.append(Finding(
                severity="good" if pace > 0 else "warning",
                scope="plan",
                title=(
                    f"{half.get('label', 'Полугодие')}: "
                    + ("идём с опережением" if pace > 0 else "отстаём от графика")
                ),
                metric=pp(pace),
                fact=(
                    f"Выполнено {pct(half.get('execution_pct'))} плана, "
                    f"календарь прошёл на "
                    f"{pct(half.get('calendar_pct'))}."
                ),
                cause=(
                    f"Чтобы закрыть полугодие, нужно "
                    f"{money(half.get('required_daily_rate'))} в день "
                    f"на оставшиеся "
                    f"{fmt_days(half.get('days_remaining'))}."
                ),
                weight=abs(num(half.get("remaining_amount")) or 0),
            ))

    return out


# ============================================================
# 3. ФИНАНСЫ
# ============================================================

def _finance_findings(payload):
    out = []
    fin = payload.get("financial") or {}

    current_week = fin.get("current_week") or {}
    previous_week = fin.get("previous_week") or {}

    result_pct = num(current_week.get("result_pct"))
    result_delta = num(current_week.get("result_delta_pp"))

    if result_pct is not None:
        econ = _rows(payload, "financial", "current", "economics_100") or {}

        severity = "neutral"
        if result_pct < 0:
            severity = "critical"
        elif result_pct < 5:
            severity = "serious"
        elif result_delta is not None and result_delta <= -3:
            severity = "warning"
        elif result_delta is not None and result_delta >= 3:
            severity = "good"

        cause = ""
        if econ:
            cause = (
                f"Из каждых 100 ₽ выручки без НДС "
                f"{pct(econ.get('cogs'), 0)} уходит на себестоимость, "
                f"{pct(econ.get('commission'), 0)} — комиссия WB, "
                f"{pct(econ.get('wb_costs'), 0)} — логистика, хранение "
                f"и штрафы. Остаётся "
                f"{pct(econ.get('result'), 0)}."
            )

        drivers = []
        for label, key in (
            ("себестоимость", "cogs_share"),
            ("комиссия", "commission_share"),
            ("расходы WB", "wb_costs_share"),
        ):
            now = num(current_week.get(key))
            was = num(previous_week.get(key))
            if now is not None and was is not None and abs(now - was) >= 1:
                drivers.append((label, now - was))

        if drivers:
            drivers.sort(key=lambda x: -abs(x[1]))
            label, delta = drivers[0]
            word = "выросла" if delta > 0 else "снизилась"
            cause += (
                f" За неделю сильнее всего изменилась {label}: "
                f"{word} на {pp(abs(delta))}."
            )

        out.append(Finding(
            severity=severity,
            scope="finance",
            title=(
                f"Рентабельность недели {pct(result_pct)}"
                + (f", {pp(result_delta)} к прошлой" if result_delta else "")
            ),
            metric=pct(result_pct),
            fact=(
                f"Выручка без НДС {money(current_week.get('revenue_net'))}, "
                f"результат после расходов площадки "
                f"{money(current_week.get('wb_result'))}."
            ),
            cause=cause,
            action=(
                "Отрицательный результат означает, что каждая продажа "
                "приносит убыток. Это не решается объёмом — сначала "
                "цена и себестоимость, потом рост."
                if result_pct < 0 else
                ("Запас прочности небольшой: любое подорожание "
                 "логистики или рост скидок уводит в минус."
                 if result_pct < 5 else "")
            ),
            weight=abs(num(current_week.get("wb_result")) or 0),
        ))

    # --- достоверность себестоимости --------------------------------
    quality = _rows(payload, "financial", "cost_quality", "ytd") or {}
    no_cost_pct = num(quality.get("no_cost_pct"))

    if no_cost_pct is not None and no_cost_pct >= 5:
        out.append(Finding(
            severity="serious" if no_cost_pct >= 15 else "warning",
            scope="data",
            title=f"У {pct(no_cost_pct)} продаж нет себестоимости",
            metric=pct(no_cost_pct),
            fact=(
                f"С начала года {fmt_qty(quality.get('no_cost_units'))} "
                f"{plural(num(quality.get('no_cost_units')) or 0, 'единица', 'единицы', 'единиц')} "
                f"продано без известной себестоимости."
            ),
            cause=(
                "В проводке по этим продажам не записана "
                "бухгалтерская себестоимость, поэтому вместо неё "
                "подставляется оценка: последняя известная цена "
                "по товару, а если и её нет — усреднённый резерв "
                "(620 ₽ для управленческого учёт)."
                " Маржа по этим продажам посчитана "
                "по оценке, а не по факту, и может быть как ниже, "
                "так и выше реальной."
            ),
            action=(
                "Проверьте приходные документы по товарам без "
                "себестоимости — чем их больше, тем сильнее "
                "оценочная себестоимость может расходиться "
                "с реальной по этим позициям."
            ),
            weight=num(quality.get("no_cost_units")) or 0,
        ))

    return out


# ============================================================
# 4. ЦЕНЫ
# ============================================================

def _price_findings(payload):
    out = []
    analysis = _rows(payload, "sales", "brand_price_analysis") or {}

    for item in (analysis.get("anomalies") or [])[:3]:
        kind = item.get("type")
        brand = item.get("brand", "бренд")
        price_change = num(item.get("price_change_pct"))
        qty_change = num(item.get("qty_change_pct"))
        revenue = num(item.get("revenue_14d")) or 0

        if kind == "ineffective_discount":
            # Одно правило источника покрывает два разных случая:
            # спрос не вырос — и спрос вообще упал. Это сильно
            # разные новости, и писать их одинаково нельзя.
            falling = (qty_change or 0) < -5

            if falling:
                title = f"«{brand}»: цену снизили, а продажи всё равно упали"
                fact = (
                    f"Цена ниже на {pct(abs(price_change))}, "
                    f"но количество не выросло, а упало на "
                    f"{pct(abs(qty_change))}. Выручка бренда "
                    f"за две недели {money(revenue)}."
                )
                cause = (
                    "Скидка не удержала спрос, значит дело не в цене. "
                    "Так обычно выглядит закончившийся размер или "
                    "цвет, просадка в выдаче или ушедший сезон."
                )
                action = (
                    "Сначала проверьте наличие ходовых позиций "
                    "и позицию в выдаче. Пока причина не найдена, "
                    "скидку лучше убрать: она уменьшает маржу "
                    "и ничего не даёт взамен."
                )
                severity = "serious"
            else:
                title = f"«{brand}»: скидка не дала объёма"
                fact = (
                    f"Цена ниже на {pct(abs(price_change))}, "
                    f"а количество почти не изменилось — "
                    f"{signed_pct(qty_change)}. Выручка бренда "
                    f"за две недели {money(revenue)}."
                )
                cause = (
                    "Покупатель не отреагировал на снижение — "
                    "значит цена не была причиной отказа от покупки."
                )
                action = (
                    "Вернуть цену и искать причину в другом: наличие "
                    "размеров, позиция в выдаче, карточка. Скидка "
                    "здесь просто отдаёт маржу."
                )
                severity = "warning"

            out.append(Finding(
                severity=severity,
                scope="price",
                title=title,
                metric=signed_pct(qty_change),
                fact=fact,
                cause=cause,
                action=action,
                weight=revenue,
            ))

        elif kind == "price_pressure":
            out.append(Finding(
                severity="serious",
                scope="price",
                title=f"«{brand}»: подняли цену — потеряли покупателя",
                metric=signed_pct(qty_change),
                fact=(
                    f"Цена выросла на {pct(abs(price_change))}, "
                    f"количество упало на {pct(abs(qty_change))}."
                ),
                cause=(
                    "Спрос на этот бренд чувствителен к цене — "
                    "покупатель уходит к конкуренту."
                ),
                action=(
                    "Сравните с ценами конкурентов по этим позициям. "
                    "Если разрыв большой, цену придётся вернуть."
                ),
                weight=revenue,
            ))

        elif kind == "pricing_power":
            out.append(Finding(
                severity="good",
                scope="price",
                title=f"«{brand}»: цену подняли, спрос вырос",
                metric=signed_pct(price_change),
                fact=(
                    f"Цена выше на {pct(abs(price_change))}, "
                    f"количество выше на {pct(abs(qty_change))}."
                ),
                cause=(
                    "Редкое сочетание: бренд продаётся не ценой. "
                    "Значит, есть запас для дальнейшего повышения."
                ),
                action=(
                    "Проверьте, можно ли так же поднять цену "
                    "на соседние позиции этого бренда."
                ),
                weight=revenue,
            ))

    # --- возможности по эластичности --------------------------------
    opportunities = analysis.get("opportunities") or []

    if opportunities:
        best = opportunities[0]
        balance = best.get("balance") or {}

        if balance.get("available"):
            out.append(Finding(
                severity="neutral",
                scope="price",
                title=(
                    f"«{best.get('brand')}»: модель предлагает "
                    f"снизить цену"
                ),
                metric=signed_pct(balance.get("recommended_price_change_pct")),
                fact=(
                    f"При снижении цены на "
                    f"{pct(abs(num(balance.get('recommended_price_change_pct')) or 0))} "
                    f"модель ожидает рост количества на "
                    f"{signed_pct(balance.get('projected_qty_change_pct'))} "
                    f"при марже "
                    f"{pct(balance.get('projected_margin_pct'))}."
                ),
                cause=(
                    "Оценка построена на связи цены и количества "
                    "за последние 90 дней. Это модель, а не обещание: "
                    "она не знает про конкурентов и сезон."
                ),
                action=(
                    "Проверьте на части ассортимента и сравните "
                    "с расчётом, прежде чем менять цену везде."
                ),
                weight=num(best.get("revenue_14d")) or 0,
            ))

    return out


# ============================================================
# 5. ЗАПАСЫ
# ============================================================

def _stock_findings(payload):
    out = []

    balance = payload.get("stock_balance") or {}
    health = balance.get("health") or {}

    if health.get("available"):
        risk_share = num(health.get("risk_share_pct"))
        risk_value = num(health.get("risk_management_value"))
        coverage = num(health.get("coverage_days"))

        arrival_reliable = bool(health.get("arrival_data_reliable"))
        risk_stale_share = num(health.get("risk_stale_share_pct"))
        risk_new_share = num(health.get("risk_new_share_pct"))

        if (
            arrival_reliable
            and risk_stale_share is not None
        ):
            # Данных о дате прихода достаточно, чтобы не путать
            # новый товар с залежавшимся -- пишем вывод именно
            # про залежавшееся, а не про всю зону риска разом.
            if risk_stale_share >= C.STOCK_RISK_ALERT_PCT:
                out.append(Finding(
                    severity="serious" if risk_stale_share >= 45 else "warning",
                    scope="stocks",
                    title=(
                        f"{pct(risk_stale_share)} запаса залежалось "
                        f"и продаётся плохо или не продаётся"
                    ),
                    metric=money(health.get("risk_stale_management_value")),
                    fact=(
                        f"В залежавшемся товаре лежит "
                        f"{money(health.get('risk_stale_management_value'))} "
                        f"управленческой стоимости, это "
                        f"{fmt_qty(health.get('risk_stale_qty'))} "
                        f"{plural(num(health.get('risk_stale_qty')) or 0, 'штука', 'штуки', 'штук')} "
                        f"по {fmt_qty(health.get('risk_stale_products'))} "
                        f"{plural(num(health.get('risk_stale_products')) or 0, 'товару', 'товарам', 'товарам')}."
                    ),
                    cause=(
                        f"Это товар старше "
                        f"{fmt_days(health.get('new_arrival_window_days'))} "
                        f"на складе, у которого либо нет продаж, "
                        f"либо покрытие больше 90 дней — новые "
                        f"поставки сюда уже не попадают, они "
                        f"показаны отдельно."
                    ),
                    action=(
                        "По каждой позиции нужно решение — уценка, "
                        "вывоз или списание, а не ожидание."
                    ),
                    weight=num(health.get("risk_stale_management_value")) or 0,
                ))

            if (
                risk_new_share is not None
                and risk_new_share >= C.STOCK_NEW_ARRIVAL_NOTE_PCT
            ):
                out.append(Finding(
                    severity="neutral",
                    scope="stocks",
                    title=(
                        f"{pct(risk_new_share)} запаса — новые поставки "
                        f"без продаж"
                    ),
                    metric=money(health.get("risk_new_management_value")),
                    fact=(
                        f"Приехало за последние "
                        f"{fmt_days(health.get('new_arrival_window_days'))} "
                        f"и пока без продаж (или с покрытием больше "
                        f"90 дней при малой истории) "
                        f"{fmt_qty(health.get('risk_new_qty'))} "
                        f"{plural(num(health.get('risk_new_qty')) or 0, 'штука', 'штуки', 'штук')} "
                        f"по {fmt_qty(health.get('risk_new_products'))} "
                        f"{plural(num(health.get('risk_new_products')) or 0, 'товару', 'товарам', 'товарам')} "
                        f"на {money(health.get('risk_new_management_value'))}."
                    ),
                    cause=(
                        "Это не проблема, а нормальный разгон продаж "
                        "после поставки — решение по этому товару "
                        "пока не нужно, нужно время."
                    ),
                    action="",
                    weight=0,
                ))

        elif risk_share is not None and risk_share >= C.STOCK_RISK_ALERT_PCT:
            # Истории остатков не хватает, чтобы надёжно отличить
            # новое от залежавшегося (например, свежее подключение
            # склада) -- честно откатываемся к общей формулировке
            # с оговоркой, а не делаем вид, что деление посчитано.
            no_sales_share = num(health.get("no_sales_share_pct")) or 0

            out.append(Finding(
                severity="serious" if risk_share >= 45 else "warning",
                scope="stocks",
                title=f"{pct(risk_share)} запаса продаётся плохо или не продаётся",
                metric=money(risk_value),
                fact=(
                    f"В медленном и мёртвом товаре лежит "
                    f"{money(risk_value)} управленческой стоимости, "
                    f"это {fmt_qty(health.get('risk_qty'))} "
                    f"{plural(num(health.get('risk_qty')) or 0, 'штука', 'штуки', 'штук')} "
                    f"по {fmt_qty(health.get('risk_products'))} "
                    f"{plural(num(health.get('risk_products')) or 0, 'товару', 'товарам', 'товарам')}."
                ),
                cause=(
                    f"Из них {pct(no_sales_share)} запаса не продавалось "
                    f"вообще ни разу за последние 30 дней. "
                    f"Важная оговорка: в эту же группу попадает "
                    f"товар, который только что приехал и ещё не "
                    f"успел начать продаваться — по остаткам он "
                    f"неотличим от залежавшегося, а истории "
                    f"остатков пока не хватает, чтобы их разделить."
                ),
                action=(
                    "Сначала отделите новые поставки: по ним "
                    "решение не нужно, нужно время. По остальному "
                    "это замороженные деньги и оплаченное хранение, "
                    "и по каждой позиции нужно решение — уценка, "
                    "вывоз или списание, а не ожидание."
                ),
                weight=risk_value or 0,
            ))

        if coverage is not None:
            if coverage <= C.COVERAGE_LOW_DAYS:
                out.append(Finding(
                    severity="serious",
                    scope="stocks",
                    title=f"Запаса осталось на {fmt_days(coverage)}",
                    metric=fmt_days(coverage),
                    fact=(
                        f"При текущем темпе продаж "
                        f"{fmt_qty(health.get('average_daily_sales'))} "
                        f"в день остатка хватит до "
                        f"{fmt_days(coverage)}."
                    ),
                    cause=(
                        "Поставка занимает время: если заказ не "
                        "размещён сейчас, разрыв в продажах уже "
                        "заложен."
                    ),
                    action=(
                        "Проверьте сроки по позициям-лидерам "
                        "и разместите заказ по ним в первую очередь."
                    ),
                    weight=1_000_000,
                ))
            elif coverage >= C.COVERAGE_HIGH_DAYS:
                out.append(Finding(
                    severity="warning",
                    scope="stocks",
                    title=f"Запаса на {fmt_days(coverage)} вперёд",
                    metric=fmt_days(coverage),
                    fact=(
                        f"Общий остаток "
                        f"{fmt_qty(health.get('total_qty'))} "
                        f"при продажах "
                        f"{fmt_qty(health.get('sales_qty_30d'))} "
                        f"за 30 дней."
                    ),
                    cause=(
                        "Такой запас — это деньги, которые не "
                        "работают, плюс постоянная плата за хранение."
                    ),
                    action=(
                        "Притормозите закупку по категориям "
                        "с самым долгим покрытием."
                    ),
                    weight=num(balance.get("management_cost")) or 0,
                ))

    # --- концентрация по складам ------------------------------------
    stocks = payload.get("stocks") or {}
    warehouses = stocks.get("top_warehouses") or []
    total_qty = num(stocks.get("total_qty")) or 0

    # Вывод про концентрацию имеет смысл только там, где складов
    # реально несколько. Если в разрезе одна строка — это не
    # «весь запас на одном складе», а просто отсутствие разреза.
    named = [
        row for row in warehouses
        if (num(row.get("total_qty")) or 0) > 0
    ]

    if len(named) > 1 and total_qty:
        top = named[0]
        share = 100.0 * (num(top.get("total_qty")) or 0) / total_qty

        if C.CONCENTRATION_ALERT_PCT <= share < 99.5:
            out.append(Finding(
                severity="warning",
                scope="stocks",
                title=(
                    f"{pct(share)} запаса на одном складе — "
                    f"{top.get('warehouse')}"
                ),
                metric=pct(share),
                fact=(
                    f"Там лежит {fmt_qty(top.get('total_qty'))} "
                    f"{plural(num(top.get('total_qty')) or 0, 'штука', 'штуки', 'штук')} "
                    f"из {fmt_qty(total_qty)}."
                ),
                cause=(
                    "Любая проблема этого склада — приёмка, "
                    "ограничения, авария — сразу бьёт по трети "
                    "продаж."
                ),
                action=(
                    "Распределите ближайшие поставки на другие "
                    "склады, даже если этот удобнее."
                ),
                weight=total_qty,
            ))

    # --- товар в пути -----------------------------------------------
    transit_share = num(balance.get("transit_share_pct"))

    if transit_share is not None and transit_share >= 25:
        out.append(Finding(
            severity="neutral",
            scope="stocks",
            title=f"{pct(transit_share)} запаса в пути",
            metric=pct(transit_share),
            fact=(
                f"{fmt_qty(balance.get('transit_qty'))} "
                f"{plural(num(balance.get('transit_qty')) or 0, 'штука', 'штуки', 'штук')} "
                f"едет и пока не продаётся."
            ),
            action=(
                "Учитывайте это при оценке покрытия: доступный "
                "к продаже остаток меньше общего."
            ),
            weight=0,
        ))

    return out


# ============================================================
# 6. СТРУКТУРА: КТО ДАЁТ ВЫРУЧКУ, А КТО ПРИБЫЛЬ
# ============================================================

def _mix_findings(payload):
    """
    Выводы по разрезам «выручка против маржинальности».

    Главный вопрос раздела: совпадают ли те, кто делает нам
    оборот, с теми, кто делает прибыль. Обычно не совпадают,
    и это самое полезное, что можно узнать из такого разреза.
    """
    out = []
    mix = payload.get("mix") or {}

    if not mix.get("available"):
        return out

    days = num(mix.get("days")) or 90
    period = f"за {fmt_days(days)}"

    for dimension, rows, one, many in (
        ("brand", mix.get("brands") or [], "бренд", "брендов"),
        ("category", mix.get("categories") or [], "категория", "категорий"),
    ):
        material = [
            row for row in rows
            if (num(row.get("revenue_vatless")) or 0) > 0
        ]

        if not material:
            continue

        total_revenue = sum(
            num(row.get("revenue_vatless")) or 0 for row in material
        )
        total_profit = sum(
            num(row.get("gross_profit_man")) or 0 for row in material
        )

        if not total_revenue:
            continue

        # --- продаём в минус ---------------------------------
        losers = [
            row for row in material
            if (num(row.get("gross_profit_man")) or 0) < 0
            and (num(row.get("revenue_vatless")) or 0)
            >= total_revenue * 0.01
        ]

        if losers:
            losers.sort(key=lambda r: num(r.get("gross_profit_man")) or 0)
            worst = losers[0]
            loss = sum(
                num(row.get("gross_profit_man")) or 0 for row in losers
            )

            names = ", ".join(
                f"«{row.get('name')}»" for row in losers[:3]
            )

            if dimension == "brand":
                # Убыток считаем один раз — по брендам. Складывать
                # его ещё и по категориям нельзя: это те же самые
                # продажи, посчитанные в другом разрезе.
                out.append(Finding(
                    severity="critical",
                    scope="mix",
                    title=(
                        f"Продаём в минус: "
                        f"{fmt_qty(len(losers))} "
                        f"{plural(len(losers), one, many, many)}"
                    ),
                    metric=money(loss),
                    fact=(
                        f"{names} {period} дали выручку "
                        f"{money(sum(num(r.get('revenue_vatless')) or 0 for r in losers))}, "
                        f"а маржу — {money(loss)}. Хуже всех "
                        f"«{worst.get('name')}»: маржинальность "
                        f"{level_pct(worst.get('margin_man_pct'))}."
                    ),
                    cause=(
                        "Себестоимость вместе с комиссией WB съедает "
                        "больше, чем приносит продажа. Каждая "
                        "дополнительная единица здесь увеличивает "
                        "убыток, а не выручку."
                    ),
                    action=(
                        "По этим позициям нужна либо цена выше, либо "
                        "закупка дешевле, либо вывод из ассортимента. "
                        "Реклама и продвижение тут только ускоряют "
                        "потери."
                    ),
                    weight=abs(loss),
                ))
            else:
                out.append(Finding(
                    severity="serious",
                    scope="mix",
                    title=(
                        f"Категория «{worst.get('name')}» "
                        f"убыточна целиком"
                    ),
                    metric=level_pct(worst.get("margin_man_pct")),
                    fact=(
                        f"{period} направление дало выручку "
                        f"{money(worst.get('revenue_vatless'))} "
                        f"и маржу {money(worst.get('gross_profit_man'))} "
                        f"по {fmt_qty(worst.get('products_count'))} "
                        f"товарам."
                    ),
                    cause=(
                        "Убыточный бренд — это вопрос к поставщику "
                        "и цене. Убыточная категория целиком — "
                        "вопрос к самому направлению: обычно там "
                        "либо тяжёлая логистика, либо высокая "
                        "комиссия WB, либо и то и другое."
                    ),
                    action=(
                        "Посмотрите комиссию WB по этой категории "
                        "и сравните с ценой. Если категория "
                        "не вытягивает даже до нуля, её стоит "
                        "сокращать, а не пытаться раскачать "
                        "рекламой."
                    ),
                    weight=abs(num(worst.get("gross_profit_man")) or 0),
                ))

        # --- оборот есть, прибыли нет ------------------------
        if total_profit > 0:
            gap_rows = []

            for row in material:
                revenue_share = (
                    100.0 * (num(row.get("revenue_vatless")) or 0)
                    / total_revenue
                )
                profit_share = (
                    100.0 * (num(row.get("gross_profit_man")) or 0)
                    / total_profit
                )

                if revenue_share >= 10 and revenue_share - profit_share >= 8:
                    gap_rows.append((row, revenue_share, profit_share))

            if gap_rows:
                gap_rows.sort(key=lambda item: -(item[1] - item[2]))
                row, revenue_share, profit_share = gap_rows[0]

                out.append(Finding(
                    severity="warning",
                    scope="mix",
                    title=(
                        f"«{row.get('name')}»: много оборота, "
                        f"мало прибыли"
                    ),
                    metric=pp(profit_share - revenue_share),
                    fact=(
                        f"{period} даёт {pct(revenue_share)} всей "
                        f"выручки, но только {pct(profit_share)} "
                        f"маржи — маржинальность "
                        f"{level_pct(row.get('margin_man_pct'))} против "
                        f"{level_pct(100.0 * total_profit / total_revenue)} "
                        f"в среднем."
                    ),
                    cause=(
                        "Такой перекос обычно означает высокую "
                        "себестоимость или глубокую скидку именно "
                        "здесь: объём есть, но он оплачивается "
                        "маржой."
                    ),
                    action=(
                        "Проверьте закупочную цену и глубину скидки "
                        "по этим позициям. Пока маржинальность ниже "
                        "средней, наращивать здесь объём — значит "
                        "снижать прибыль компании в целом."
                    ),
                    weight=(
                        (revenue_share - profit_share)
                        / 100.0 * total_profit
                    ),
                ))

        # --- качество себестоимости в разрезе ----------------
        risky = [
            row for row in material
            if (num(row.get("rows_count")) or 0) > 0
            and (num(row.get("no_man_cost")) or 0)
            / (num(row.get("rows_count")) or 1) >= 0.25
            and (num(row.get("revenue_vatless")) or 0)
            >= total_revenue * 0.05
        ]

        if risky and dimension == "brand":
            worst = max(
                risky,
                key=lambda r: (num(r.get("no_man_cost")) or 0)
                / (num(r.get("rows_count")) or 1),
            )
            share = (
                100.0 * (num(worst.get("no_man_cost")) or 0)
                / (num(worst.get("rows_count")) or 1)
            )

            out.append(Finding(
                severity="warning",
                scope="data",
                title=(
                    f"Маржа по «{worst.get('name')}» завышена: "
                    f"нет себестоимости"
                ),
                metric=pct(share),
                fact=(
                    f"У {pct(share)} продаж этого бренда "
                    f"{period} не нашлась управленческая "
                    f"себестоимость. Маржинальность "
                    f"{level_pct(worst.get('margin_man_pct'))} "
                    f"посчитана как будто товар достался бесплатно."
                ),
                cause=(
                    "Обычно это незакрытые партии прихода или "
                    "товар, проданный раньше, чем оприходован."
                ),
                action=(
                    "Пока себестоимость не заведена, решения "
                    "по цене и ассортименту этого бренда лучше "
                    "не принимать: цифра выглядит лучше, чем есть."
                ),
                weight=num(worst.get("revenue_vatless")) or 0,
            ))

    return out


# ============================================================
# 7. ЗАКАЗЫ FBS
# ============================================================

def fbs_findings(fbs, window_days=30):
    """
    Выводы по заказам FBS.

    fbs — результат collect_fbs_analysis. Отдельная функция,
    потому что эти данные приходят не из payload обзора.

    window_days нужен для честных формулировок: доля отмен
    за 30 дней и за день — разные величины, и не написать
    период значит ввести читателя в заблуждение.
    """
    out = []

    if not fbs:
        return out

    period = f"за последние {fmt_days(window_days)}"

    kpi = fbs.get("kpi") or {}

    in_work = num(kpi.get("orders_in_work")) or 0
    overdue = num(kpi.get("orders_overdue")) or 0
    amount = num(kpi.get("amount")) or 0
    total = num(kpi.get("orders_total")) or 0

    # Если срез заказов не обновлялся давно, "просрочка" в нём
    # не значит реальную просрочку -- она значит, что статусы
    # просто не снялись. Писать вывод по таким цифрам как про
    # проблему сборки нельзя, поэтому просрочку из выводов
    # в этом случае не считаем вовсе.
    # Та же логика "устарел ли снимок", что и в pages.py::
    # _fbs_is_stale -- для отчёта за прошлую дату сравниваем
    # снимок с самой этой датой, а не с "сейчас" (иначе любой
    # исторический отчёт считался бы устаревшим просто по факту
    # того, что дата в прошлом).
    as_of = fbs.get("as_of")
    requested = fbs.get("as_of_date_requested")

    if isinstance(as_of, datetime):
        if requested is not None and requested != date.today():
            reference = datetime.combine(requested, datetime.max.time())
            if as_of.tzinfo:
                reference = reference.replace(tzinfo=as_of.tzinfo)
        else:
            reference = (
                datetime.now(as_of.tzinfo) if as_of.tzinfo else datetime.now()
            )
        is_stale = (reference - as_of) > timedelta(hours=C.FBS_STALE_HOURS)
    else:
        is_stale = False

    if in_work and overdue and not is_stale:
        share = 100.0 * overdue / in_work
        avg_check = amount / total if total else 0
        frozen = overdue * avg_check

        buckets = fbs.get("buckets_in_work")
        oldest = num(kpi.get("max_age_in_work"))

        severity = (
            "critical" if share >= 25
            else ("serious" if share >= C.FBS_OVERDUE_ALERT_PCT else "warning")
        )

        as_of_label = (
            f" (данные на {fmt_date(as_of)}"
            + (f", {as_of.strftime('%H:%M')}" if as_of else "")
            + ")"
            if isinstance(as_of, datetime)
            else ""
        )

        out.append(Finding(
            severity=severity,
            scope="fbs",
            title=(
                f"Просрочено {fmt_qty(overdue)} заказов FBS "
                f"на момент среза{as_of_label}"
            ),
            metric=pct(share),
            fact=(
                f"Это {pct(share)} от того, что было на сборке "
                f"({fmt_qty(in_work)}). Самый старый заказ провисел "
                f"{fmt_hours(oldest)} при нормативе "
                f"{C.FBS_SLA_HOURS} часов. Возраст заказов и статус "
                f"«просрочено» считаются от снимка данных, ближайшего "
                f"к дате этого отчёта, а не от текущего момента."
            ),
            cause=(
                f"В этих заказах примерно {money(frozen)} — деньги, "
                f"которые уже заказаны, но ещё не отгружены."
            ),
            action=(
                "Просрочка по FBS бьёт по позиции в выдаче и "
                "по рейтингу продавца. Разобрать хвост стоит "
                "раньше, чем собирать новые заказы."
            ),
            weight=frozen,
            # "Прямо сейчас" -- живой остаток на сборке, привязанный
            # к моменту синхронизации с WB, а не к report_date отчёта.
            # На странице 1 (которая всегда про report_date) это
            # вводит в заблуждение, поэтому там эта находка не
            # показывается -- см. summary_page(). В разделе FBS
            # (там, где ясно видно as_of) остаётся.
            live=True,
        ))

    # --- скорость сборки закрытых заказов -----------------------------
    avg_close = num(kpi.get("avg_hours_to_close"))
    closed = num(kpi.get("orders_closed")) or 0

    if closed and avg_close is not None:
        over_norm = avg_close > C.FBS_SLA_HOURS

        if over_norm:
            ratio = avg_close / C.FBS_SLA_HOURS if C.FBS_SLA_HOURS else 1
            out.append(Finding(
                severity="serious" if ratio >= 1.5 else "warning",
                scope="fbs",
                title=(
                    f"Закрытые заказы FBS собираются в среднем "
                    f"{fmt_hours(avg_close)} {period}"
                ),
                metric=fmt_hours(avg_close),
                fact=(
                    f"Норматив — {C.FBS_SLA_HOURS} ч. Расчёт по "
                    f"{fmt_qty(closed)} уже закрытым "
                    f"{plural(closed, 'заказу', 'заказам', 'заказам')} "
                    f"{period} — это факт по отгруженному, а не срез "
                    f"на текущий момент, поэтому он не зависит от "
                    f"того, когда собирался отчёт."
                ),
                cause=(
                    "Сборка стабильно выходит за норматив — это "
                    "уже не разовый затор, а рабочий темп склада."
                ),
                action=(
                    "Стоит смотреть, что именно тормозит сборку: "
                    "конкретный склад, категория товара или общая "
                    "нагрузка на команду."
                ),
                weight=closed * (avg_close - C.FBS_SLA_HOURS),
            ))
        else:
            out.append(Finding(
                severity="good",
                scope="fbs",
                title=(
                    f"Закрытые заказы FBS собираются в среднем "
                    f"{fmt_hours(avg_close)} {period}"
                ),
                metric=fmt_hours(avg_close),
                fact=(
                    f"Это в пределах норматива ({C.FBS_SLA_HOURS} ч). "
                    f"Расчёт по {fmt_qty(closed)} уже закрытым "
                    f"{plural(closed, 'заказу', 'заказам', 'заказам')} "
                    f"{period}."
                ),
                weight=closed,
            ))

    # --- отмены ------------------------------------------------------
    cancelled = num(kpi.get("orders_cancelled")) or 0

    if total and cancelled:
        share = 100.0 * cancelled / total
        if share >= 10:
            out.append(Finding(
                severity="warning",
                scope="fbs",
                title=(
                    f"Отменено {pct(share)} заказов FBS "
                    f"{period}"
                ),
                metric=pct(share),
                fact=(
                    f"{fmt_qty(cancelled)} "
                    f"{plural(cancelled, 'заказ', 'заказа', 'заказов')} "
                    f"из {fmt_qty(total)} {period} отменены "
                    f"покупателем или отклонены. Это накопленная "
                    f"величина за весь период, а не за один день."
                ),
                cause=(
                    "Часть из них доходит до сборки — и тогда "
                    "время склада тратится впустую."
                ),
                action=(
                    "Проверьте, сколько отмен приходит после "
                    "подтверждения: если много, стоит менять "
                    "порядок сборки."
                ),
                weight=cancelled,
            ))

    # --- концентрация просрочки по направлениям ----------------------
    logistics = fbs.get("logistics")

    if (
        not is_stale
        and logistics is not None
        and not getattr(logistics, "empty", True)
    ):
        try:
            grouped = (
                logistics
                .groupby("warehouse", as_index=False)[["orders", "orders_overdue"]]
                .sum()
                .sort_values("orders_overdue", ascending=False)
            )
            total_overdue = float(grouped["orders_overdue"].sum())

            if total_overdue:
                top = grouped.iloc[0]
                top_share = 100.0 * float(top["orders_overdue"]) / total_overdue

                if top_share >= 60 and len(grouped) > 1:
                    out.append(Finding(
                        severity="warning",
                        scope="fbs",
                        title=(
                            f"Просрочка собрана на одном складе: "
                            f"{top['warehouse']}"
                        ),
                        metric=pct(top_share),
                        fact=(
                            f"На него приходится {pct(top_share)} всей "
                            f"просрочки — "
                            f"{fmt_qty(top['orders_overdue'])} "
                            f"{plural(float(top['orders_overdue']), 'заказ', 'заказа', 'заказов')}."
                        ),
                        cause=(
                            "Проблема не в общем темпе сборки, "
                            "а в конкретной точке."
                        ),
                        action=(
                            "Разбираться надо там, а не менять "
                            "процесс на всех складах."
                        ),
                        weight=float(top["orders_overdue"]),
                    ))
        except (KeyError, IndexError, ValueError):
            pass

    return out


# ============================================================
# СБОРКА
# ============================================================

def build_findings(payload, fbs=None):
    """
    Собирает все выводы и сортирует по важности.

    Внутри одной степени важности впереди идёт то, за чем
    стоит больше денег.
    """
    out = []
    out += _revenue_findings(payload)
    out += _plan_findings(payload)
    out += _finance_findings(payload)
    out += _price_findings(payload)
    out += _mix_findings(payload)
    out += _stock_findings(payload)
    out += fbs_findings(fbs)

    # Один и тот же вывод не должен появиться дважды — в том числе
    # в двух разных степенях важности: читатель видит одинаковый
    # текст в двух блоках и перестаёт доверять всему списку.
    unique = []
    seen_titles = set()

    for item in sorted(out, key=lambda f: f.sort_key()):
        key = item.title.strip().lower()
        if key in seen_titles:
            continue
        seen_titles.add(key)
        unique.append(item)

    return unique


def headline(payload, findings):
    """
    Главная мысль отчёта одной фразой.

    Берём самую тяжёлую находку: если она критична — говорим
    о ней, если всё спокойно — говорим о выручке.
    """
    if findings and findings[0].severity in ("critical", "serious"):
        top = findings[0]
        return f"{top.title}. {top.fact}"

    split = decompose_revenue(payload, window=7)

    if split and split["change_pct"] is not None:
        direction = "выше" if split["change_pct"] > 0 else "ниже"
        return (
            f"За неделю {fmt_date(split['cur_start'])}–"
            f"{fmt_date(split['cur_end'])} выручка "
            f"{money(split['current']['amount'])}, на "
            f"{pct(abs(split['change_pct']))} {direction} "
            f"предыдущей. Критичных отклонений нет."
        )

    return "Существенных отклонений за период не обнаружено."
