# gear/app/daily_sales/commercial_review/pages.py
"""
Страницы отчёта.

Порядок страниц не случайный: сначала ответ («что происходит
и что делать»), потом доказательства. Руководитель читает
первые три страницы, коммерческая команда — все.

Каждая страница отвечает на один вопрос, и этот вопрос
написан в заголовке.
"""

from __future__ import annotations

from . import charts, config as C
from .analysis import decompose_revenue
from .blocks import (
    bullet_bar,
    bullets,
    callout,
    figure,
    finding_card,
    kpi,
    kpi_grid,
    page,
    revenue_calendar,
    severity_legend,
    table,
    toc,
    week_tiles,
)
from .formats import (
    as_date,
    date_full,
    date_short,
    date_words,
    days as fmt_days,
    escape,
    hours as fmt_hours,
    money,
    money_exact,
    month_label,
    month_name,
    num,
    pct,
    plural,
    pp,
    qty as fmt_qty,
    signed_money,
    signed_pct,
)


# ============================================================
# ВСПОМОГАТЕЛЬНОЕ
# ============================================================

def _node(payload, *path):
    node = payload
    for key in path:
        if not isinstance(node, dict):
            return {}
        node = node.get(key)
    return node if isinstance(node, dict) else {}


def _list(payload, *path):
    node = payload
    for key in path:
        if not isinstance(node, dict):
            return []
        node = node.get(key)
    return node if isinstance(node, list) else []


def _scope(findings, *scopes, limit=None, severities=None):
    out = [
        item for item in findings
        if item.scope in scopes
        and (severities is None or item.severity in severities)
    ]
    return out[:limit] if limit else out


def _cards(findings, show_action=True):
    return "".join(
        finding_card(item, show_action=show_action)
        for item in findings
    )


def _state(value, good_when_up=True):
    v = num(value)
    if v is None or abs(v) < 0.05:
        return "flat"
    rising = v > 0
    return "good" if (rising == good_when_up) else "bad"


def _no_findings_note(subject):
    return callout(
        "",
        f"<b>Отклонений по этому разделу нет.</b> "
        f"{escape(subject)} в пределах обычного разброса, "
        f"отдельного решения не требует.",
        plain=True,
    )


# ============================================================
# 1. ОБЛОЖКА
# ============================================================

def cover(payload, findings, headline_text) -> str:
    report_date = as_date(payload.get("report_date"))

    kpi_sales = _node(payload, "sales", "kpi")
    previous_day = _node(payload, "sales", "comparisons", "previous_day")
    plan = _node(payload, "plan")
    balance = _node(payload, "stock_balance")
    health = _node(payload, "stock_balance", "health")

    margin_pct = num(kpi_sales.get("margin_pct"))

    cards = [
        kpi(
            "Выручка за день",
            money(kpi_sales.get("amount")),
            signed_pct(previous_day.get("change_pct")) + " ко дню ранее",
            _state(previous_day.get("change_pct")),
        ),
        # Маржи здесь сознательно нет: расходы WB приходят
        # раз в неделю, и карточка на обложке меняла бы
        # значение задним числом. Реализация и скидка
        # известны сразу и больше не пересчитываются.
        kpi(
            "WB реализовал с НДС",
            money(kpi_sales.get("retail_amount")),
            (
                "скидка WB "
                + signed_pct(kpi_sales.get("wb_discount_percent"))
            ),
            _state(kpi_sales.get("wb_discount_percent")),
            signed_money(kpi_sales.get("wb_discount_amount"))
            + " к нашей цене",
        ),
        kpi(
            "Выполнение плана месяца",
            pct(plan.get("month_exec_pct")),
            (
                pct(plan.get("exec_to_date_pct")) + " к плану на дату"
                if plan.get("exec_to_date_pct") is not None
                else ""
            ),
            (
                "good"
                if (num(plan.get("exec_to_date_pct")) or 0)
                >= C.PLAN_BEHIND_PCT
                else "bad"
            ),
        ),
        kpi(
            "Запас на складах",
            fmt_qty(balance.get("total_qty")) + " шт.",
            (
                "хватит на " + fmt_days(health.get("coverage_days"))
                if health.get("coverage_days") is not None
                else ""
            ),
            "flat",
        ),
    ]

    # Три самых тяжёлых вывода прямо на обложку: чтобы понять,
    # о чём выпуск, не открывая его.
    urgent = [
        item for item in findings
        if item.severity in ("critical", "serious")
    ][:3]

    if urgent:
        rows = "".join(
            f'<div class="agenda-row">'
            f'<span class="agenda-metric">{item.metric or "—"}</span>'
            f'<span class="agenda-title">{item.title}</span>'
            f"</div>"
            for item in urgent
        )
        agenda = (
            '<div class="agenda">'
            '<h4>В этом выпуске — прежде всего</h4>'
            f"{rows}"
            "</div>"
        )
    else:
        agenda = (
            '<div class="agenda">'
            '<h4>В этом выпуске</h4>'
            '<div class="agenda-row">'
            '<span class="agenda-metric">—</span>'
            '<span class="agenda-title">Вопросов, требующих '
            'решения на этой неделе, нет</span>'
            "</div></div>"
        )

    critical = len([f for f in findings if f.severity == "critical"])
    serious = len([f for f in findings if f.severity == "serious"])

    counters = []
    if critical:
        counters.append(
            f"{critical} "
            f"{plural(critical, 'вопрос требует', 'вопроса требуют', 'вопросов требуют')}"
            f" решения"
        )
    if serious:
        counters.append(f"{serious} — под контроль")
    if not counters:
        counters.append("критичных отклонений нет")

    return f"""
    <section class="page page-cover">
        <div class="issue">Выпуск за {escape(date_short(report_date))}</div>
        <div class="cover-band">
            <div class="cover-brand">ТРЕНДСЕТТЕР</div>
            <div class="cover-title">Коммерческий<br>обзор</div>
            <p class="cover-sub">
                По состоянию на {escape(date_full(report_date))}
            </p>
        </div>

        <div class="cover-body">
            <div class="cover-headline">{headline_text}</div>
            {kpi_grid(cards)}
            {agenda}
            <p class="small dim">
                Разобрано отклонений: {len(findings)}, из них
                {escape(", ".join(counters))}.
                Что с каждым делать — в разделе «Выводы
                и рекомендации».
            </p>
        </div>

        <div class="cover-foot">
            Отчёт собран автоматически
            {escape(date_short(payload.get("generated_at")))}
            по закрытым данным продаж, финансового результата,
            запасов и заказов FBS.
            Суммы в рублях; где указано «без НДС», показатель
            приведён к базе без налога.
        </div>
    </section>
    """


# ============================================================
# 2. ОГЛАВЛЕНИЕ И КАК ЧИТАТЬ
# ============================================================

def contents(payload) -> str:
    rows = [
        ("01", "Главное на одной странице",
         "выводы, которые требуют решения на этой неделе"),
        ("02", "Выручка: как менялась",
         "календарь по дням, динамика и накопленный итог к прошлому году"),
        ("03", "Выручка: почему изменилась",
         "разложение на количество, цену и возвраты"),
        ("04", "Цена, количество и скидка WB",
         "расходятся ли цена и спрос, сколько стоит скидка"),
        ("05", "Бренды: цена против количества",
         "кто поднял цену без потери объёма, а кто нет"),
        ("06", "Бренды: оборот и прибыль",
         "кто делает выручку, а кто зарабатывает — за 90 дней и за неделю"),
        ("07", "Категории: оборот и прибыль",
         "какое направление тянет маржу вниз"),
        ("08", "План месяца",
         "темп внутри месяца и сколько нужно делать в день"),
        ("09", "План года и полугодия",
         "по месяцам: где догнали, где отстали"),
        ("10", "Прогноз до конца года",
         "ожидаемый итог против плана по месяцам"),
        ("11", "Финансовый результат",
         "куда уходят 100 ₽ и как шла рентабельность неделя за неделей"),
        ("12", "Запасы: структура и стоимость",
         "где лежит товар, сколько он стоит в двух контурах"),
        ("13", "Запасы: зона риска",
         "что не продаётся и сколько в этом заморожено денег"),
        ("14", "Заказы FBS: сборка и сроки",
         "сколько заказов приходит по дням и что висит на сборке"),
        ("15", "Заказы FBS: склады, поставки, товары",
         "откуда и куда отправляем, что именно заказывают"),
        ("16", "Выводы и рекомендации",
         "полный список: что произошло, почему, что делать"),
        ("17", "Методика",
         "как считаются показатели и чего в отчёте нет"),
    ]

    how = bullets([
        "<b>Сначала ответ, потом доказательства.</b> Первые три "
        "страницы отвечают на вопрос «что делать». Дальше — "
        "цифры и графики, на которых этот ответ построен.",

        "<b>Каждый вывод состоит из трёх частей:</b> что "
        "произошло (факт с цифрой), почему (разложение или "
        "конкретный виновник) и что делать (одно действие). "
        "Если причину назвать нельзя, вывод не пишется вообще — "
        "общая фраза хуже молчания.",

        "<b>Плашки показывают срочность, а не оценку работы.</b> "
        "«Требует решения» значит, что без решения цифра "
        "продолжит ухудшаться сама.",

        "<b>Отрицательные значения в скобках</b>, как в "
        "управленческой отчётности: (1 200 ₽) — это минус "
        "1 200 ₽.",
    ])

    vat = callout(
        "Про НДС",
        "Выручка показана с НДС — так её видно в личном кабинете "
        "WB и так её проще сверить. Маржа, себестоимость, комиссия "
        "и расходы WB приведены к базе <b>без НДС</b>: иначе "
        "процент маржи получается завышенным. Где показатель "
        "считается иначе, это написано прямо под цифрой.",
    )

    return page(
        "",
        "Как читать этот отчёт",
        "Содержание",
        "Отчёт собирается из закрытых данных: цифры в нём "
        "не меняются после выпуска, поэтому на него можно "
        "ссылаться в переписке.",
        toc(rows) + '<div class="rule-soft"></div>'
        + "<h3>Как читать</h3>" + how + severity_legend() + vat,
    )


# ============================================================
# 3. ГЛАВНОЕ НА ОДНОЙ СТРАНИЦЕ
# ============================================================

def summary_page(payload, findings, headline_text) -> str:
    urgent = [
        item for item in findings
        if item.severity in ("critical", "serious")
    ][:4]

    watch = [
        item for item in findings
        if item.severity == "warning"
    ][:3]

    good = [item for item in findings if item.severity == "good"][:3]

    body = callout("Главное", f"<b>{headline_text}</b>")

    if urgent:
        body += "<h3>Требует решения</h3>" + _cards(urgent)
    else:
        body += callout(
            "",
            "<b>Вопросов, требующих решения прямо сейчас, нет.</b> "
            "Ни один показатель не вышел за пороги, при которых "
            "отклонение перестаёт быть обычным разбросом.",
            plain=True,
        )

    if watch:
        body += "<h3>Обратить внимание</h3>" + _cards(
            watch, show_action=False
        )

    if good:
        body += "<h3>Что работает</h3>" + bullets([
            f"<b>{item.title}.</b> {item.fact}" for item in good
        ])

    return page(
        "01",
        "Главное",
        "Главное на одной странице",
        "Если дальше читать некогда — достаточно этой страницы. "
        "Выводы отсортированы по деньгам, которые за ними стоят.",
        body,
    )


# ============================================================
# 4. ВЫРУЧКА: ДИНАМИКА
# ============================================================

def revenue_dynamics_page(payload) -> str:
    daily_rows = _list(payload, "sales", "daily_price_rows")
    ytd_rows = _list(payload, "sales", "ytd_daily_rows")
    comparisons = _node(payload, "sales", "comparisons")

    cards = []

    for key, label in (
        ("previous_day", "Ко дню ранее"),
        ("previous_month_day", "К тому же дню месяцем ранее"),
        ("previous_year_day", "К тому же дню годом ранее"),
        ("mtd", "С начала месяца"),
    ):
        block = comparisons.get(key) or {}
        cards.append(
            kpi(
                label,
                money(block.get("current")),
                signed_pct(block.get("change_pct")),
                _state(block.get("change_pct")),
                f"было {money(block.get('previous'))} "
                f"({escape(str(block.get('previous_label') or ''))})",
            )
        )

    trend = charts.revenue_trend(daily_rows)
    ytd = charts.revenue_vs_last_year(ytd_rows)

    # Вывод под графиком: последняя закрытая календарная неделя
    # против предыдущей — это и есть текущий темп.
    split = decompose_revenue(payload)

    trend_note = (
        f"<b>Текущий темп:</b> неделя "
        f"{escape(date_short(split['cur_start']))}–"
        f"{escape(date_short(split['cur_end']))} дала "
        f"{money(split['current']['amount'])} против "
        f"{money(split['previous']['amount'])} неделей раньше — "
        f"{signed_money(split['total'])} "
        f"({signed_pct(split['change_pct'])}). "
        f"Столбики показывают выходные провалы, линия — "
        f"скользящее среднее за 7 дней, то есть тренд без них."
        if split and split.get("change_pct") is not None
        else "Линия — скользящее среднее за 7 дней: она сглаживает "
             "разницу между выходными и буднями."
    )

    ytd_years = sorted({
        (as_date(row.get("date_from")) or as_date("1970-01-01")).year
        for row in ytd_rows
        if as_date(row.get("date_from"))
    })

    ytd_block = comparisons.get("ytd") or {}

    ytd_note = (
        f"<b>С начала года {money(ytd_block.get('current'))} "
        f"против {money(ytd_block.get('previous'))}</b> — "
        f"{signed_money(ytd_block.get('delta'))} "
        f"({signed_pct(ytd_block.get('change_pct'))}). "
        + (
            "Линии расходятся — значит разрыв копится, и одной "
            "акцией его не закрыть."
            if (num(ytd_block.get("change_pct")) or 0) < 0
            else "Опережение устойчивое: линия текущего года выше "
                 "на всём отрезке."
        )
        if ytd_block
        else ""
    )

    body = (
        kpi_grid(cards)
        + revenue_calendar(
            _list(payload, "sales", "trend"),
            weeks=5,
            subtitle=(
                "Каждая клетка — один закрытый день, выручка с НДС "
                "до скидки WB. Справа итог недели"
            ),
        )
        + figure(
            "Выручка по дням и скользящее среднее за 7 дней",
            trend,
            "За последние 90 дней, ₽ с НДС",
            trend_note,
            "Для графика нужно минимум 7 дней данных",
        )
        + figure(
            "Накопленная выручка: этот год против прошлого",
            ytd,
            (
                f"С 1 января по {escape(date_short(payload.get('report_date')))}"
                if not ytd_years
                else f"Годы {escape(' и '.join(str(y) for y in ytd_years[-2:]))}, "
                     f"накопленным итогом"
            ),
            ytd_note,
            "В данных нет сопоставимого периода прошлого года",
        )
    )

    return page(
        "02",
        "Выручка",
        "Выручка: как она менялась",
        "Два взгляда на одно и то же: короткий — что происходит "
        "прямо сейчас, и длинный — куда мы идём с начала года.",
        body,
    )


# ============================================================
# 5. ВЫРУЧКА: ПОЧЕМУ ИЗМЕНИЛАСЬ
# ============================================================

def revenue_reasons_page(payload, findings) -> str:
    split = decompose_revenue(payload, window=7)
    waterfall = charts.revenue_waterfall(split)

    if split:
        qty_effect = split["qty_effect"]
        price_effect = split["price_effect"]
        returns_effect = split["returns_effect"]

        leader = max(
            (
                ("количество", qty_effect),
                ("средняя цена", price_effect),
                ("возвраты", returns_effect),
            ),
            key=lambda item: abs(item[1]),
        )[0]

        running = split.get("running")

        running_note = ""
        if running and running.get("qty"):
            running_note = (
                f" Текущая неделя "
                f"({escape(date_short(running['start']))}–"
                f"{escape(date_short(running['end']))}) ещё идёт: "
                f"{fmt_days(running['days'])} из семи, "
                f"{money(running.get('amount'))} — в сравнение "
                f"она не входит."
            )

        note = (
            f"<b>Изменение {signed_money(split['total'])} складывается "
            f"из трёх частей:</b> количество дало "
            f"{signed_money(qty_effect)}, средняя цена — "
            f"{signed_money(price_effect)}, возвраты — "
            f"{signed_money(returns_effect)}. Сумма трёх вкладов "
            f"точно равна изменению выручки, поэтому спорить "
            f"про «примерно» не нужно. Главный фактор — {leader}."
            + running_note
        )

        method = callout(
            "Как считается",
            "Вклад количества — разница в проданных штуках, "
            "умноженная на прежнюю цену. Вклад цены — разница "
            "в средней цене, умноженная на новое количество. "
            "Вклад возвратов — насколько больше или меньше "
            "вернули. Возвраты вынесены отдельно не для красоты: "
            "средняя цена в данных считается только по продажам, "
            "и без этого разделения рост возвратов выглядел бы "
            "как падение цены. Сравниваются две соседние "
            "календарные недели, понедельник — воскресенье: "
            f"{escape(date_short(split['prev_start']))}–"
            f"{escape(date_short(split['prev_end']))} и "
            f"{escape(date_short(split['cur_start']))}–"
            f"{escape(date_short(split['cur_end']))}. "
            "Если текущая неделя ещё не закрыта, она в сравнение "
            "не входит — иначе падение получилось бы просто "
            "от нехватки дней. "
            "Средняя цена — это выручка, делённая на штуки, "
            "поэтому она меняется и сама по себе, когда "
            "в продажах меняется доля дорогих и дешёвых позиций.",
            plain=True,
        )
    else:
        note = ""
        method = ""

    brands = _list(payload, "sales", "top_brands")

    brand_table = table(
        [
            {"key": "name", "label": "Бренд"},
            {"key": "revenue", "label": "Выручка, ₽",
             "num": True, "fmt": money_exact},
            {"key": "sold_units", "label": "Продано, шт.",
             "num": True, "fmt": fmt_qty},
            {"key": "avg_price", "label": "Средняя цена, ₽",
             "num": True, "fmt": money_exact},
            {"key": "returns_amount", "label": "Возвраты, ₽",
             "num": True, "fmt": money_exact},
            {"key": "returns_share", "label": "Доля возвратов",
             "num": True, "fmt": lambda v: pct(v)},
        ],
        [
            {
                **row,
                "returns_share": (
                    100.0 * (num(row.get("returns_amount")) or 0)
                    / (num(row.get("sales_amount")) or 1)
                ),
                "_alert": (
                    100.0 * (num(row.get("returns_amount")) or 0)
                    / (num(row.get("sales_amount")) or 1)
                ) >= C.RETURNS_ALERT_PCT,
            }
            for row in brands
        ],
        total=(
            {
                "name": "Итого по топ-5 брендов",
                "revenue": sum(num(r.get("revenue")) or 0 for r in brands),
                "sold_units": sum(
                    num(r.get("sold_units")) or 0 for r in brands
                ),
                "avg_price": (
                    sum(num(r.get("sales_amount")) or 0 for r in brands)
                    / (sum(num(r.get("sold_units")) or 0 for r in brands) or 1)
                ),
                "returns_amount": sum(
                    num(r.get("returns_amount")) or 0 for r in brands
                ),
                "returns_share": (
                    100.0
                    * sum(num(r.get("returns_amount")) or 0 for r in brands)
                    / (sum(num(r.get("sales_amount")) or 0 for r in brands) or 1)
                ),
            }
            if brands
            else None
        ),
        caption="Бренды за день: кто принёс выручку",
        note=(
            "Красным выделены бренды, где возвраты превысили "
            f"{pct(C.RETURNS_ALERT_PCT, 0)} продаж. "
            "<b>Важно про источник:</b> разрез по брендам "
            "берётся из витрины продаж, а карточки и календарь "
            "выше — из контура реализации, по которому считается "
            "план. Итоги этих двух витрин за один день отличаются "
            "на несколько процентов, поэтому сумма по брендам "
            "и выручка в карточке не обязаны совпадать до рубля. "
            "Подробнее — в разделе «Методика»."
        ),
    ) if brands else ""

    sales_findings = _scope(findings, "sales", limit=3)

    body = (
        figure(
            "Из чего сложилось изменение выручки за неделю",
            waterfall,
            "Последняя закрытая неделя против предыдущей, ₽",
            note,
            "Недостаточно дней для сравнения двух недель",
        )
        + method
        + brand_table
        + (_cards(sales_findings) if sales_findings
           else _no_findings_note("Выручка"))
    )

    return page(
        "03",
        "Выручка",
        "Выручка: почему она изменилась",
        "«Выручка упала на 12 %» — это не вывод. Вывод — какая "
        "часть этих 12 % пришлась на количество, какая на цену "
        "и какая на возвраты. Недели здесь календарные, "
        "с понедельника по воскресенье.",
        body,
    )


# ============================================================
# 6. ЦЕНА, КОЛИЧЕСТВО И СКИДКА
# ============================================================

def price_page(payload) -> str:
    daily_rows = _list(payload, "sales", "daily_price_rows")
    price_rows = _list(payload, "price_analysis_page", "rows")

    recent = _node(payload, "price_analysis_page", "recent_14")
    previous = _node(payload, "price_analysis_page", "previous_14")

    corr = num(_node(payload, "sales", "price_analysis").get("daily_corr"))

    cards = [
        kpi(
            "Наша цена, 14 дней",
            money(recent.get("seller_avg_price")),
            signed_pct(
                100.0
                * ((num(recent.get("seller_avg_price")) or 0)
                   - (num(previous.get("seller_avg_price")) or 0))
                / (num(previous.get("seller_avg_price")) or 1)
            ),
            _state(
                (num(recent.get("seller_avg_price")) or 0)
                - (num(previous.get("seller_avg_price")) or 0)
            ),
            "цена до скидки WB",
        ),
        kpi(
            "Цена покупателя, 14 дней",
            money(recent.get("buyer_avg_price")),
            "",
            "flat",
            "то, что человек видит в приложении",
        ),
        kpi(
            "Скидка WB",
            pct(recent.get("discount_pct")),
            pp(
                (num(recent.get("discount_pct")) or 0)
                - (num(previous.get("discount_pct")) or 0)
            ),
            _state(
                (num(recent.get("discount_pct")) or 0)
                - (num(previous.get("discount_pct")) or 0),
                good_when_up=False,
            ),
            money(recent.get("discount_amount")) + " за 14 дней",
        ),
        kpi(
            "Маржинальность, 14 дней",
            pct(recent.get("margin_pct")),
            pp(
                (num(recent.get("margin_pct")) or 0)
                - (num(previous.get("margin_pct")) or 0)
            ),
            _state(
                (num(recent.get("margin_pct")) or 0)
                - (num(previous.get("margin_pct")) or 0)
            ),
            "от выручки без НДС",
        ),
    ]

    if corr is None:
        corr_note = (
            "Связи между ценой и количеством по этим данным "
            "посчитать не удалось."
        )
    elif corr <= -0.4:
        corr_note = (
            f"<b>Связь обратная и заметная (коэффициент {corr:.2f}).</b> "
            f"Когда цена ниже, покупают больше — скидка работает "
            f"на объём. Но проверьте по брендам: средняя цена "
            f"падает и просто от смены ассортимента."
        ).replace(".", ",", 1)
    elif corr >= 0.4:
        corr_note = (
            f"<b>Связь прямая (коэффициент {corr:.2f}).</b> "
            f"Цена и количество растут вместе — это обычно значит, "
            f"что дело не в цене, а в ассортименте или сезоне."
        )
    else:
        corr_note = (
            f"<b>Связи почти нет (коэффициент {corr:.2f}).</b> "
            f"Спрос в этом периоде двигала не цена. Скидка "
            f"в таких условиях уменьшает маржу и почти не "
            f"добавляет объёма."
        )

    corr_note += (
        " <span class=\"muted\">Коэффициент показывает связь, "
        "а не причину: средняя цена — это выручка, делённая "
        "на штуки, поэтому она сама падает, когда растёт доля "
        "дешёвых позиций. Решение принимайте по брендам "
        "на следующей странице, а не по этому числу.</span>"
    )

    body = (
        kpi_grid(cards)
        + figure(
            "Количество и средняя цена рядом",
            charts.qty_price_pair(daily_rows),
            "За последние 60 дней",
            corr_note,
            "Мало дней с продажами для сопоставления",
        )
        + figure(
            "Цена до скидки WB и цена покупателя",
            charts.price_and_discount(price_rows),
            "За последние 60 дней, ₽ за единицу",
            "<b>Заливка между линиями — это скидка WB в рублях "
            "на каждую единицу.</b> Чем она шире, тем большую "
            "часть цены оплачивает не покупатель, а наша маржа.",
            "Нет истории цен за период",
        )
    )

    return page(
        "04",
        "Цена",
        "Цена, количество и скидка WB",
        "Три вопроса на одной странице: меняли ли мы цену, "
        "ответил ли на это спрос и сколько стоит скидка WB.",
        body,
    )


# ============================================================
# 7. БРЕНДЫ: ЦЕНА ПРОТИВ КОЛИЧЕСТВА
# ============================================================

def brands_page(payload, findings) -> str:
    analysis = _node(payload, "sales", "brand_price_analysis")
    brands = analysis.get("brands") or []
    anomalies = analysis.get("anomalies") or []

    scatter = charts.brand_price_scatter(brands)

    quarters = bullets([
        "<b>Справа вверху — лучший случай:</b> цену подняли, "
        "а количество не упало. Такую цену держим и смотрим, "
        "можно ли повторить на других брендах.",

        "<b>Слева вверху:</b> цену снизили, количество выросло. "
        "Скидка сработала на объём — но это не всегда выгодно, "
        "смотрите маржу в таблице.",

        "<b>Справа внизу — самое неприятное:</b> цену подняли "
        "и потеряли покупателей. Здесь цену стоит вернуть.",

        "<b>Слева внизу:</b> цена ниже, а покупают всё равно "
        "меньше. Дело не в цене — смотрите наличие, карточку "
        "и позицию в выдаче.",
    ])

    brand_table = table(
        [
            {"key": "brand", "label": "Бренд"},
            {"key": "revenue_14d", "label": "Выручка 14 дн., ₽",
             "num": True, "fmt": money_exact},
            {"key": "sales_qty_14d", "label": "Продано, шт.",
             "num": True, "fmt": fmt_qty},
            {"key": "avg_price_14d", "label": "Средняя цена, ₽",
             "num": True, "fmt": money_exact},
            {"key": "price_change_pct", "label": "Цена",
             "num": True, "fmt": lambda v: signed_pct(v)},
            {"key": "qty_change_pct", "label": "Количество",
             "num": True, "fmt": lambda v: signed_pct(v)},
            {"key": "margin_pct", "label": "Маржа",
             "num": True, "fmt": lambda v: pct(v)},
            {"key": "confidence", "label": "Надёжность модели"},
        ],
        [
            {
                **row,
                "_alert": (
                    (num(row.get("price_change_pct")) or 0) > 0
                    and (num(row.get("qty_change_pct")) or 0) < -10
                ),
            }
            for row in sorted(
                brands,
                key=lambda r: -(num(r.get("revenue_14d")) or 0),
            )[:12]
        ],
        caption="Бренды: что стало с ценой и количеством за 14 дней",
        note="Изменение считается к предыдущим 14 дням. "
             "Красным — бренды, где цена выросла, а количество "
             "упало больше чем на 10 %: там подорожание "
             "не приняли.",
    ) if brands else callout(
        "",
        "<b>Модель по брендам не построена.</b> Для оценки нужна "
        "история продаж с разной ценой: если цена почти не "
        "менялась, связь посчитать не на чем.",
        plain=True,
    )

    anomaly_block = ""
    if anomalies:
        anomaly_block = "<h3>Что выбивается из общей картины</h3>" + bullets([
            f"<b>{escape(str(item.get('brand')))}. "
            f"{escape(str(item.get('title')))}.</b> "
            f"Цена {signed_pct(item.get('price_change_pct'))}, "
            f"количество {signed_pct(item.get('qty_change_pct'))}, "
            f"маржа {pct(item.get('margin_pct'))}, "
            f"выручка за 14 дней {money(item.get('revenue_14d'))}."
            for item in anomalies
        ])

    price_findings = _scope(findings, "price", limit=3)

    body = (
        figure(
            "Бренды: изменение цены и изменение количества",
            scatter,
            "За 14 дней к предыдущим 14. Размер круга — выручка бренда",
            "",
            "Для этой картинки нужно минимум три бренда "
            "с надёжной моделью",
        )
        + quarters
        + brand_table
        + anomaly_block
        + (_cards(price_findings) if price_findings else "")
    )

    return page(
        "05",
        "Цена",
        "Бренды: цена против количества",
        "Один и тот же процент скидки по разным брендам даёт "
        "разный результат. Здесь видно, где он окупается, "
        "а где просто уменьшает маржу.",
        body,
    )


# ============================================================
# 8. ПЛАН МЕСЯЦА
# ============================================================

def plan_month_page(payload, findings) -> str:
    plan = _node(payload, "plan")
    report_date = as_date(payload.get("report_date"))

    if not plan.get("available"):
        return page(
            "08",
            "План",
            "План месяца",
            "",
            callout(
                "",
                (
                    "<b>Плановая версия не найдена.</b> Пока в системе "
                    "нет утверждённого бюджета на этот период, сравнить "
                    "факт с планом не с чем."
                    + (
                        f"<br><span class=\"small muted\">Причина: "
                        f"{escape(plan.get('reason'))}</span>"
                        if plan.get("reason")
                        else ""
                    )
                ),
                plain=True,
            ),
        )

    exec_to_date = num(plan.get("exec_to_date_pct"))
    month_exec = num(plan.get("month_exec_pct"))
    remaining_days = num(plan.get("remaining_days")) or 0

    calendar_pct = None
    if report_date:
        import calendar as _calendar
        in_month = _calendar.monthrange(report_date.year, report_date.month)[1]
        calendar_pct = 100.0 * report_date.day / in_month

    cards = [
        kpi(
            "План на месяц",
            money(plan.get("month_plan")),
            "",
            "flat",
            escape(str(plan.get("label") or month_name(report_date))),
        ),
        kpi(
            "Факт на дату",
            money(plan.get("fact_to_date")),
            pct(exec_to_date) + " от плана на дату",
            "good" if (exec_to_date or 0) >= C.PLAN_BEHIND_PCT else "bad",
            "план на дату " + money(plan.get("plan_to_date")),
        ),
        kpi(
            "Разрыв к плану на дату",
            signed_money(plan.get("delta_to_date")),
            "",
            _state(plan.get("delta_to_date")),
            "накопленно с начала месяца",
        ),
        kpi(
            "Нужно делать в день",
            money(plan.get("required_daily_rate")),
            "",
            "flat",
            (
                f"осталось {fmt_days(remaining_days)}, "
                f"добрать {money(plan.get('remaining_month'))}"
            ),
        ),
    ]

    bar = bullet_bar(
        month_exec,
        calendar_pct,
        left_label="начало месяца",
        center_label=(
            f"сделано {pct(month_exec)} месячного плана · "
            f"по календарю прошло {pct(calendar_pct)}"
            if calendar_pct is not None
            else f"сделано {pct(month_exec)} месячного плана"
        ),
        right_label="месячный план",
    )

    daily_rate = num(plan.get("daily_plan")) or 0
    required = num(plan.get("required_daily_rate")) or 0

    if required and daily_rate:
        ratio = required / daily_rate
        if ratio > 1.25:
            pace_text = (
                f"Чтобы закрыть месяц, в оставшиеся "
                f"{fmt_days(remaining_days)} нужно делать "
                f"{money(required)} в день — это в "
                f"{ratio:.1f} раза больше планового темпа "
                f"({money(daily_rate)} в день). "
                f"Такой рывок обычно не случается сам: либо "
                f"появляется акция и рекламный бюджет, либо "
                f"месяц закрывается с недобором."
            ).replace(".", ",", 1)
        elif ratio < 0.9:
            pace_text = (
                f"Требуемый темп {money(required)} в день ниже "
                f"планового {money(daily_rate)} — месяц "
                f"закрывается с запасом, если не случится "
                f"провала в последние дни."
            )
        else:
            pace_text = (
                f"Требуемый темп {money(required)} в день "
                f"примерно равен плановому — месяц закроется, "
                f"если держать текущую скорость."
            )
    else:
        pace_text = ""

    plan_findings = _scope(findings, "plan", limit=3)

    body = (
        kpi_grid(cards)
        + bar
        + (callout("Что это значит", pace_text) if pace_text else "")
        + figure(
            "Темп внутри месяца: факт против плана накопленно",
            charts.plan_month_pace(plan.get("rows")),
            "Накопленным итогом с 1-го числа, ₽",
            "<b>Закрашенная область — это и есть отставание "
            "или опережение в рублях</b> на каждый день, "
            "а не только на конец месяца.",
            "Мало дней в месяце для графика темпа",
        )
        + (_cards(plan_findings) if plan_findings
           else _no_findings_note("Выполнение плана"))
    )

    return page(
        "08",
        "План",
        "План месяца",
        "Главный вопрос страницы: закроем ли месяц, если ничего "
        "не менять.",
        body,
    )


# ============================================================
# 9. ПЛАН ГОДА И ПОЛУГОДИЯ
# ============================================================

def plan_year_page(payload) -> str:
    half = _node(payload, "half_year_wb_plan")
    monthly = _list(payload, "plan", "monthly_rows")

    cards = []

    if half.get("available"):
        cards = [
            kpi(
                "План полугодия",
                money(half.get("plan_amount")),
                "",
                "flat",
                escape(str(half.get("label") or "")),
            ),
            kpi(
                "Факт полугодия",
                money(half.get("fact_amount")),
                pct(half.get("execution_to_date_pct")) + " к плану на дату",
                (
                    "good"
                    if (num(half.get("execution_to_date_pct")) or 0)
                    >= C.PLAN_BEHIND_PCT
                    else "bad"
                ),
                "план на дату " + money(half.get("plan_to_date")),
            ),
            kpi(
                "Темп против календаря",
                pp(half.get("pace_delta_pp")),
                "",
                _state(half.get("pace_delta_pp")),
                (
                    f"прошло {pct(half.get('calendar_pct'))} времени, "
                    f"сделано {pct(half.get('execution_pct'))} плана"
                ),
            ),
            kpi(
                "Осталось добрать",
                money(half.get("remaining_amount")),
                "",
                "flat",
                (
                    f"за {fmt_days(half.get('days_remaining'))}, "
                    f"по {money(half.get('required_daily_rate'))} в день"
                ),
            ),
        ]

    half_note = ""
    if not half.get("available"):
        half_note = callout(
            "",
            (
                "<b>План полугодия не собрался.</b>"
                + (
                    f" Причина: {escape(half.get('reason'))}."
                    if half.get("reason")
                    else ""
                )
            ),
            plain=True,
        )

    months_note = ""

    if monthly and not sum(num(r.get("plan")) or 0 for r in monthly):
        months_note = callout(
            "",
            "<b>В бюджетной версии нет плановых сумм на этот год.</b> "
            "Факт показан, сравнивать его не с чем: проверьте, что "
            "план заведён в ту же версию бюджета, по которой "
            "считается план месяца.",
            plain=True,
        )

    if not monthly:
        months_note = callout(
            "",
            "<b>Месячных плановых строк нет.</b> Проверьте, что "
            "бюджетная версия заведена на текущий год: план "
            "берётся из неё, а не из факта.",
            plain=True,
        )

    months_table = table(
        [
            {"key": "month_short", "label": "Месяц"},
            {"key": "plan", "label": "План, ₽", "num": True,
             "fmt": money_exact},
            {"key": "fact", "label": "Факт, ₽", "num": True,
             "fmt": money_exact},
            {"key": "delta", "label": "Разница, ₽", "num": True,
             "fmt": money_exact},
            {"key": "month_exec_pct", "label": "Выполнение",
             "num": True, "fmt": lambda v: pct(v)},
            {"key": "running_exec_pct", "label": "Накопленно",
             "num": True, "fmt": lambda v: pct(v)},
        ],
        [
            {
                **row,
                "_alert": (
                    (num(row.get("plan")) or 0) > 0
                    and (num(row.get("month_exec_pct")) or 0)
                    < C.PLAN_BEHIND_PCT
                    and not row.get("is_future")
                ),
            }
            for row in monthly
        ],
        total=(
            {
                "month_short": "Год",
                "plan": sum(num(r.get("plan")) or 0 for r in monthly),
                "fact": sum(num(r.get("fact")) or 0 for r in monthly),
                "delta": sum(num(r.get("delta")) or 0 for r in monthly),
                "month_exec_pct": (
                    100.0
                    * sum(num(r.get("fact")) or 0 for r in monthly)
                    / sum(num(r.get("plan")) or 0 for r in monthly)
                    if sum(num(r.get("plan")) or 0 for r in monthly)
                    else None
                ),
                "running_exec_pct": None,
            }
            if monthly
            else None
        ),
        caption="План и факт по месяцам года",
        note="Красным — закрытые месяцы, где выполнение оказалось "
             f"ниже {pct(C.PLAN_BEHIND_PCT, 0)}. Будущие месяцы "
             "показаны для полноты картины.",
    ) if monthly else ""

    body = (
        (kpi_grid(cards) if cards else "")
        + half_note
        + months_note
        + figure(
            "План и факт по месяцам, плюс накопленное выполнение",
            charts.plan_months(monthly),
            "Столбики — рубли по левой оси, линия — процент "
            "накопленного выполнения по правой",
            "<b>Линия важнее столбиков:</b> она показывает, "
            "закрывается ли отставание прошлых месяцев или "
            "накапливается.",
            "Нет месячных плановых данных",
        )
        + months_table
    )

    return page(
        "09",
        "План",
        "План года и полугодия",
        "Здесь видно, отставание этого месяца — случайность "
        "или продолжение тенденции.",
        body,
    )


# ============================================================
# 10. ПРОГНОЗ
# ============================================================

def forecast_page(payload) -> str:
    prophet = _node(payload, "prophet_plan")
    monthly = prophet.get("monthly") or []
    metrics = prophet.get("metrics") or {}
    params = prophet.get("params") or {}

    if not prophet.get("available") or not monthly:
        return page(
            "10",
            "Прогноз",
            "Прогноз до конца года",
            "",
            callout(
                "",
                "<b>Прогноз не построен.</b> Модели нужна история "
                "продаж за последние месяцы: пока её недостаточно, "
                "числа были бы выдумкой.",
                plain=True,
            ),
        )

    expected_year = sum(
        num(row.get("expected_total")) or 0 for row in monthly
    )
    plan_year = sum(num(row.get("plan")) or 0 for row in monthly)
    gap = expected_year - plan_year

    behind = [
        row for row in monthly
        if (num(row.get("plan")) or 0) > 0
        and (num(row.get("plan_exec_pct")) or 0) < C.PLAN_BEHIND_PCT
    ]

    cards = [
        kpi(
            "Ожидаемый итог года",
            money(expected_year),
            "",
            "flat",
            "факт закрытых месяцев плюс прогноз остатка",
        ),
        kpi(
            "План года",
            money(plan_year),
            "",
            "flat",
            "утверждённая бюджетная версия",
        ),
        kpi(
            "Разрыв к плану",
            signed_money(gap),
            (
                pct(100.0 * expected_year / plan_year) + " от плана"
                if plan_year
                else ""
            ),
            _state(gap),
            "по ожидаемому итогу",
        ),
        kpi(
            "Месяцев ниже плана",
            str(len(behind)),
            "",
            "bad" if behind else "good",
            (
                "хуже всего: " + escape(
                    ", ".join(
                        month_label(row.get("month"))
                        for row in sorted(
                            behind,
                            key=lambda r: num(r.get("plan_exec_pct")) or 0,
                        )[:2]
                    )
                )
                if behind
                else "все месяцы в плане"
            ),
        ),
    ]

    if gap < 0 and plan_year:
        verdict = (
            f"<b>По текущему темпу год закрывается с недобором "
            f"{money(abs(gap))}</b> — это "
            f"{pct(100.0 * abs(gap) / plan_year)} плана. "
            f"Разрыв набирается постепенно, поэтому закрыть его "
            f"в декабре не получится: решение нужно в тех месяцах, "
            f"где прогноз ниже плана."
        )
    elif plan_year:
        verdict = (
            f"<b>По текущему темпу год закрывается с превышением "
            f"плана на {money(gap)}.</b> Проверьте, хватит ли "
            f"запаса и производственных сроков удержать такой "
            f"темп до декабря."
        )
    else:
        verdict = ""

    forecast_table = table(
        [
            {"key": "month_label", "label": "Месяц"},
            {"key": "fact", "label": "Факт, ₽", "num": True,
             "fmt": money_exact},
            {"key": "forecast", "label": "Прогноз, ₽", "num": True,
             "fmt": money_exact},
            {"key": "expected_total", "label": "Ожидаемый итог, ₽",
             "num": True, "fmt": money_exact},
            {"key": "plan", "label": "План, ₽", "num": True,
             "fmt": money_exact},
            {"key": "delta_to_plan", "label": "Разница, ₽",
             "num": True, "fmt": money_exact},
            {"key": "plan_exec_pct", "label": "Выполнение",
             "num": True, "fmt": lambda v: pct(v)},
        ],
        [
            {
                **row,
                "month_label": month_label(row.get("month")),
                "_alert": (
                    (num(row.get("plan")) or 0) > 0
                    and (num(row.get("plan_exec_pct")) or 0)
                    < C.PLAN_BEHIND_PCT
                ),
            }
            for row in monthly
        ],
        total={
            "month_label": "Год",
            "fact": sum(num(r.get("fact")) or 0 for r in monthly),
            "forecast": sum(num(r.get("forecast")) or 0 for r in monthly),
            "expected_total": expected_year,
            "plan": plan_year,
            "delta_to_plan": gap,
            "plan_exec_pct": (
                100.0 * expected_year / plan_year if plan_year else None
            ),
        },
        caption="Ожидаемый итог по месяцам против плана",
    )

    method = callout(
        "Как построен прогноз",
        f"Модель Prophet обучена на последних "
        f"{fmt_days(params.get('training_days'))} продаж и учитывает "
        f"недельную и годовую сезонность. Это продолжение текущего "
        f"темпа, а не обещание: акции, новые товары и изменения "
        f"рекламного бюджета в него не заложены. "
        + (
            f"Средняя ошибка модели на истории — "
            f"{pct(metrics.get('mape'))}."
            if metrics.get("mape") is not None
            else ""
        ),
        plain=True,
    )

    body = (
        kpi_grid(cards)
        + (callout("Что это значит", verdict) if verdict else "")
        + figure(
            "Факт, прогноз и план по месяцам",
            charts.forecast_months(monthly),
            "Столбик — факт плюс прогноз, чёрточка — план",
            "Красные подписи — месяцы, где ожидаемый итог ниже "
            "плана больше чем на 5 %.",
            "Нет месячного прогноза",
        )
        + forecast_table
        + method
    )

    return page(
        "10",
        "Прогноз",
        "Прогноз до конца года",
        "Вопрос страницы: если ничего не менять, каким будет год.",
        body,
    )


# ============================================================
# 11. ФИНАНСОВЫЙ РЕЗУЛЬТАТ
# ============================================================

def finance_page(payload, findings) -> str:
    current = _node(payload, "financial", "current")
    history = _list(payload, "financial", "history_30d")
    weeks = _list(payload, "financial", "weeks")
    week = _node(payload, "financial", "current_week")
    quality = _node(payload, "financial", "cost_quality", "ytd")

    if not current.get("has_data"):
        return page(
            "11",
            "Финансовый результат",
            "Финансовый результат",
            "",
            callout(
                "",
                "<b>За этот день финансовый контур пуст.</b> "
                "Пока не загружены себестоимость и отчёт WB, "
                "считать маржу нечем.",
                plain=True,
            ),
        )

    result_pct = num(current.get("result_pct"))
    margin_pct = num(current.get("margin_pct"))

    cards = [
        kpi(
            "Выручка без НДС",
            money(current.get("revenue_net")),
            "",
            "flat",
            "база для всех процентов на этой странице",
        ),
        kpi(
            "Маржа до расходов WB",
            money(current.get("margin_man")),
            pct(margin_pct),
            "good" if (margin_pct or 0) >= C.MARGIN_ALERT_PCT else "bad",
            "после себестоимости и комиссии, до расходов WB",
        ),
        kpi(
            "Расходы WB",
            money(current.get("wb_costs")),
            pct(current.get("wb_costs_share")) + " от выручки",
            _state(current.get("wb_costs_share"), good_when_up=False),
            "логистика, хранение, приёмка, реклама, штрафы",
        ),
        kpi(
            "Результат после WB",
            money(current.get("wb_result")),
            pct(result_pct),
            "good" if (result_pct or 0) > 0 else "bad",
            "то, что осталось с каждого рубля выручки",
        ),
    ]

    parts = [
        ("Себестоимость", current.get("cogs_share"), C.SERIES_2),
        ("Комиссия WB", current.get("commission_share"), C.INK_2),
        ("Расходы WB", current.get("wb_costs_share"), C.WARNING),
        ("Результат", current.get("result_pct"), C.NAVY),
    ]

    structure = charts.structure_100(parts)

    if (result_pct or 0) < 0:
        structure_note = (
            f"<b>Результат отрицательный ({pct(result_pct)}), поэтому "
            f"на полосе его нет:</b> себестоимость, комиссия и "
            f"расходы WB вместе съедают больше 100 % выручки. "
            f"Это значит, что каждая дополнительная продажа "
            f"в таком виде увеличивает убыток, а не выручку."
        )
    else:
        structure_note = (
            f"<b>Из каждых 100 ₽ выручки без НДС остаётся "
            f"{pct(result_pct)}.</b> "
            f"Себестоимость забирает {pct(current.get('cogs_share'))}, "
            f"комиссия WB — {pct(current.get('commission_share'))}, "
            f"остальные расходы WB — "
            f"{pct(current.get('wb_costs_share'))}."
        )

    week_block = ""
    if week.get("has_data"):
        week_block = table(
            [
                {"key": "name", "label": "Показатель"},
                {"key": "value", "label": "За неделю, ₽", "num": True,
                 "fmt": money_exact},
                {"key": "share", "label": "От выручки", "num": True,
                 "fmt": lambda v: pct(v)},
            ],
            [
                {"name": "Выручка без НДС",
                 "value": week.get("revenue_net"), "share": 100.0},
                {"name": "Себестоимость",
                 "value": week.get("cogs_man"),
                 "share": week.get("cogs_share")},
                {"name": "Комиссия WB",
                 "value": week.get("commission"),
                 "share": week.get("commission_share")},
                {"name": "Маржа после себестоимости и комиссии",
                 "value": week.get("margin_man"),
                 "share": week.get("margin_pct")},
                {"name": "Расходы WB",
                 "value": week.get("wb_costs"),
                 "share": week.get("wb_costs_share")},
            ],
            total={
                "name": "Результат после расходов WB",
                "value": week.get("wb_result"),
                "share": week.get("result_pct"),
            },
            caption=(
                f"Неделя "
                f"{escape(date_short(week.get('date_from')))}–"
                f"{escape(date_short(week.get('date_to')))}"
            ),
            note=(
                "Все суммы приведены к базе без НДС — иначе процент "
                "маржи получается завышенным."
                + (
                    f" Расходы WB загружены за "
                    f"{fmt_days(week.get('wb_costs_days'))} из "
                    f"{fmt_days(week.get('days'))}: покрытие "
                    f"{pct(week.get('wb_costs_coverage_pct'))}."
                    if week.get("wb_costs_coverage_pct") is not None
                    else ""
                )
            ),
        )

    quality_block = ""
    if quality:
        no_cost = num(quality.get("no_cost_pct"))
        quality_block = callout(
            "Насколько можно доверять этим цифрам",
            (
                f"С начала года продано "
                f"{fmt_qty(quality.get('sales_units'))} "
                f"{plural(num(quality.get('sales_units')) or 0, 'единица', 'единицы', 'единиц')}, "
                f"из них у {fmt_qty(quality.get('no_cost_units'))} "
                f"не нашлась себестоимость — это "
                f"{pct(no_cost)} продаж. "
                + (
                    "Маржа по ним считается завышенной, поэтому "
                    "итоговый процент немного оптимистичен."
                    if (no_cost or 0) >= 3
                    else "На итог это практически не влияет."
                )
            ),
            plain=True,
        )

    finance_findings = _scope(findings, "finance", limit=3)

    body = (
        kpi_grid(cards)
        + figure(
            "Куда уходят 100 ₽ выручки",
            structure,
            "Доли от выручки без НДС за день",
            structure_note,
            "Нет данных для структуры",
        )
        + week_tiles(
            weeks,
            title="Рентабельность неделя за неделей",
            subtitle=(
                "Крупно — результат после расходов WB в процентах "
                "от выручки без НДС, мелко — он же в рублях"
            ),
            note=(
                "<b>Смотреть надо на ход, а не на точку.</b> "
                "Одна просевшая неделя — обычное дело: расходы WB "
                "приходят неравномерно. Две-три подряд — это уже "
                "изменение экономики. Текущая неделя обведена "
                "рамкой и помечена как оперативная: её цифра ещё "
                "уточнится, когда WB выгрузит логистику и рекламу."
            ),
        )
        + figure(
            "Маржа и итоговый результат по дням",
            charts.margin_history(history),
            "Проценты от выручки без НДС, последние 30 дней",
            "<b>Смотреть надо на разрыв между линиями:</b> "
            "это и есть расходы WB. Если он растёт, а маржа "
            "стоит на месте, экономика ухудшается без нашего "
            "участия.",
            "Мало дней с финансовыми данными",
        )
        + week_block
        + quality_block
        + (_cards(finance_findings) if finance_findings
           else _no_findings_note("Экономика продаж"))
    )

    return page(
        "11",
        "Финансовый результат",
        "Финансовый результат",
        "Выручка — это не деньги. Здесь видно, сколько остаётся "
        "после себестоимости, комиссии и расходов WB.",
        body,
    )


# ============================================================
# 12. ЗАПАСЫ: СТРУКТУРА И ПОКРЫТИЕ
# ============================================================

def stocks_page(payload) -> str:
    balance = _node(payload, "stock_balance")
    health = _node(payload, "stock_balance", "health")

    if not balance.get("available"):
        return page(
            "12",
            "Запасы",
            "Запасы: структура и покрытие",
            "",
            callout(
                "",
                "<b>Снимок остатков за эту дату не найден.</b>",
                plain=True,
            ),
        )

    cards = [
        kpi(
            "Всего запаса",
            fmt_qty(balance.get("total_qty")) + " шт.",
            "",
            "flat",
            (
                f"{fmt_qty(balance.get('products'))} товаров, "
                f"{fmt_qty(balance.get('brands_count'))} брендов"
            ),
        ),
        kpi(
            "На складах WB",
            pct(balance.get("wb_share_pct")),
            "",
            "flat",
            fmt_qty(balance.get("wb_qty")) + " шт.",
        ),
        kpi(
            "Свой склад FBS",
            pct(balance.get("fbs_share_pct")),
            "",
            "flat",
            fmt_qty(balance.get("fbs_qty")) + " шт.",
        ),
        kpi(
            "В пути",
            pct(balance.get("transit_share_pct")),
            "",
            "flat",
            fmt_qty(balance.get("transit_qty")) + " шт. пока не продаётся",
        ),
    ]

    coverage = num(health.get("coverage_days"))

    if coverage is None:
        coverage_note = ""
    elif coverage <= C.COVERAGE_LOW_DAYS:
        coverage_note = (
            f"<b>Запаса хватит на {fmt_days(coverage)}.</b> "
            f"Это меньше обычного срока поставки, то есть разрыв "
            f"в продажах уже заложен — вопрос только в том, "
            f"по каким товарам он случится."
        )
    elif coverage >= C.COVERAGE_HIGH_DAYS:
        coverage_note = (
            f"<b>Запаса на {fmt_days(coverage)} вперёд.</b> "
            f"При среднем темпе "
            f"{fmt_qty(health.get('average_daily_sales'))} шт. в день "
            f"это деньги, которые лежат и платят за хранение "
            f"вместо того, чтобы работать."
        )
    else:
        coverage_note = (
            f"<b>Покрытие {fmt_days(coverage)}</b> — нормальный "
            f"диапазон: хватает на поставку и не переплачиваем "
            f"за хранение."
        )

    brands = balance.get("brands") or []

    brand_chart = charts.hbar(
        [row.get("brand") or "Без бренда" for row in brands],
        [num(row.get("total_qty")) or 0 for row in brands],
        value_labels=[
            f"{charts._short(num(row.get('total_qty')))} шт."
            + (
                f" · WB {charts._short(num(row.get('wb_qty')))}"
                f" · FBS {charts._short(num(row.get('fbs_qty')))}"
                if row.get("wb_qty") is not None
                else ""
            )
            for row in brands
        ],
        axis_label="Запас, шт.",
    )

    # Таблицу «Где лежит запас» убрали: разрез по складам WB
    # в отчёте не использовался для решений, а место занимал.
    # Концентрация по складам осталась отдельным выводом.

    # ---- стоимость запаса в двух контурах -----------------------
    accounting = num(balance.get("accounting_cost"))
    management = num(balance.get("management_cost"))
    delta = num(balance.get("cost_delta"))

    cost_cards = [
        kpi(
            "Бухгалтерская стоимость",
            money(accounting),
            "",
            "flat",
            "склад WB + FBS + товар в пути",
        ),
        kpi(
            "Управленческая стоимость",
            money(management),
            "",
            "flat",
            "по управленческой себестоимости FIFO",
        ),
        kpi(
            "Разница оценок",
            signed_money(delta),
            (
                signed_pct(balance.get("cost_delta_pct"))
                + " к бухгалтерской"
                if balance.get("cost_delta_pct") is not None
                else ""
            ),
            "flat",
            (
                f"без управленческой цены "
                f"{fmt_qty(balance.get('no_management_cost_qty'))} шт., "
                f"без бухгалтерской "
                f"{fmt_qty(balance.get('no_accounting_cost_qty'))} шт."
            ),
        ),
    ]

    # ---- собственный склад FBS ----------------------------------
    fbs_cards = [
        kpi(
            "Лежит на своём складе",
            fmt_qty(balance.get("fbs_qty")) + " шт.",
            pct(balance.get("fbs_share_pct")) + " всего запаса",
            "flat",
            "этим запасом мы управляем сами",
        ),
        kpi(
            "Товаров на своём складе",
            fmt_qty(balance.get("fbs_products")) + " NM ID",
            "",
            "flat",
            (
                f"только на FBS — "
                f"{fmt_qty(balance.get('fbs_only_products'))} NM ID "
                f"({fmt_qty(balance.get('fbs_only_qty'))} шт.)"
            ),
        ),
        kpi(
            "Концентрация склада",
            pct(balance.get("fbs_top5_share_pct")),
            "",
            (
                "bad"
                if (num(balance.get("fbs_top5_share_pct")) or 0) >= 80
                else "flat"
            ),
            "приходится на пять крупнейших брендов",
        ),
    ]

    fbs_brand_rows = balance.get("fbs_brands") or []
    fbs_category_rows = balance.get("fbs_categories") or []

    fbs_tables = ""

    if fbs_brand_rows:
        fbs_tables += table(
            [
                {"key": "brand", "label": "Бренд"},
                {"key": "fbs_qty", "label": "На своём складе, шт.",
                 "num": True, "fmt": fmt_qty},
                {"key": "share", "label": "Доля FBS", "num": True,
                 "fmt": lambda v: pct(v)},
                {"key": "total_qty", "label": "Весь запас бренда, шт.",
                 "num": True, "fmt": fmt_qty},
            ],
            [
                {
                    **row,
                    "share": (
                        100.0 * (num(row.get("fbs_qty")) or 0)
                        / (num(balance.get("fbs_qty")) or 1)
                    ),
                }
                for row in fbs_brand_rows
            ],
            caption="Что лежит на собственном складе: бренды",
        )

    if fbs_category_rows:
        fbs_tables += table(
            [
                {"key": "category", "label": "Категория"},
                {"key": "fbs_qty", "label": "На своём складе, шт.",
                 "num": True, "fmt": fmt_qty},
                {"key": "products", "label": "Товаров", "num": True,
                 "fmt": fmt_qty},
                {"key": "share", "label": "Доля FBS", "num": True,
                 "fmt": lambda v: pct(v)},
            ],
            [
                {
                    **row,
                    "share": (
                        100.0 * (num(row.get("fbs_qty")) or 0)
                        / (num(balance.get("fbs_qty")) or 1)
                    ),
                }
                for row in fbs_category_rows
            ],
            caption="Что лежит на собственном складе: категории",
        )

    body = (
        kpi_grid(cards)
        + "<h3>Сколько этот запас стоит</h3>"
        + kpi_grid(cost_cards, cols=3)
        + callout(
            "Почему две стоимости",
            (
                "<b>Бухгалтерская</b> — цена, по которой товар "
                "принят к учёту. <b>Управленческая</b> — та, по "
                "которой мы считаем маржу: FIFO по фактическим "
                "партиям. Расхождение само по себе не ошибка, но "
                "если оно растёт, расходится и прибыль в двух "
                "отчётах. Позиции без управленческой цены "
                "занижают стоимость запаса и завышают маржу "
                "по продажам."
            ),
            plain=True,
        )
        + "<h3>Собственный склад FBS</h3>"
        + kpi_grid(fbs_cards, cols=3)
        + fbs_tables
        + "<h3>Покрытие и размещение</h3>"
        + figure(
            "Запас по группам покрытия",
            charts.coverage_buckets(health.get("buckets")),
            "Сколько дней продаж хватит текущего остатка",
            coverage_note,
            "Нет данных о здоровье запаса",
        )
        + figure(
            "Запас по брендам",
            brand_chart,
            "Штуки на складах WB, своём складе и в пути",
            "",
            "Нет разбивки запаса по брендам",
        )
    )

    return page(
        "12",
        "Запасы",
        "Запасы: структура и стоимость",
        "Три вопроса: хватит ли товара, сколько он стоит "
        "и сколько из него лежит на нашем собственном складе.",
        body,
    )


# ============================================================
# 13. ЗАПАСЫ: ЗОНА РИСКА
# ============================================================

def stock_risk_page(payload, findings) -> str:
    health = _node(payload, "stock_balance", "health")
    balance = _node(payload, "stock_balance")

    if not health.get("available"):
        return page(
            "13",
            "Запасы",
            "Запасы: зона риска",
            "",
            callout(
                "",
                "<b>Расчёт здоровья запаса недоступен.</b>",
                plain=True,
            ),
        )

    cards = [
        kpi(
            "Плохо или совсем не продаётся",
            pct(health.get("risk_share_pct")),
            money(health.get("risk_management_value")),
            (
                "bad"
                if (num(health.get("risk_share_pct")) or 0)
                >= C.STOCK_RISK_ALERT_PCT
                else "good"
            ),
            (
                f"{fmt_qty(health.get('risk_qty'))} шт. "
                f"по {fmt_qty(health.get('risk_products'))} товарам"
            ),
        ),
        kpi(
            "Покрытие больше 90 дней",
            pct(health.get("slow_share_pct")),
            "",
            "flat",
            fmt_qty(health.get("slow_qty")) + " шт.",
        ),
        kpi(
            "Без продаж 30 дней",
            pct(health.get("no_sales_share_pct")),
            "",
            (
                "bad"
                if (num(health.get("no_sales_share_pct")) or 0) >= 15
                else "flat"
            ),
            fmt_qty(health.get("no_sales_qty")) + " шт.",
        ),
        kpi(
            "Управленческая стоимость",
            money(balance.get("management_cost")),
            (
                signed_pct(balance.get("cost_delta_pct"))
                + " к бухгалтерской"
                if balance.get("cost_delta_pct") is not None
                else ""
            ),
            "flat",
            (
                f"бухгалтерская "
                f"{money(balance.get('accounting_cost'))}"
            ),
        ),
    ]

    buckets = health.get("buckets") or []

    bucket_table = table(
        [
            {"key": "label", "label": "Группа покрытия"},
            {"key": "qty", "label": "Запас, шт.", "num": True,
             "fmt": fmt_qty},
            {"key": "share_pct", "label": "Доля", "num": True,
             "fmt": lambda v: pct(v)},
            {"key": "products", "label": "Товаров", "num": True,
             "fmt": fmt_qty},
            {"key": "management_value", "label": "Стоимость, ₽",
             "num": True, "fmt": money_exact},
        ],
        [
            {
                **row,
                "_alert": row.get("key") in ("90_plus", "no_sales"),
            }
            for row in buckets
        ],
        total={
            "label": "Итого",
            "qty": sum(num(r.get("qty")) or 0 for r in buckets),
            "share_pct": 100.0,
            "products": sum(num(r.get("products")) or 0 for r in buckets),
            "management_value": sum(
                num(r.get("management_value")) or 0 for r in buckets
            ),
        },
        caption="Запас по группам покрытия в деньгах",
        note="Красным — группы, которые и есть зона риска: "
             "покрытие больше 90 дней и товар без продаж.",
    ) if buckets else ""

    no_cost = num(balance.get("no_management_cost_qty"))

    caveat = callout(
        "Что здесь важно понимать",
        (
            "«Не продавалось за 30 дней» не всегда значит «списывать». "
            "Сезонный товар в межсезонье выглядит точно так же. "
            "Но решение всё равно нужно принять по каждой позиции: "
            "уценка, вывоз, списание или сознательное ожидание "
            "сезона — потому что хранение оплачивается в любом "
            "из этих случаев."
            + (
                f" У {fmt_qty(no_cost)} "
                f"{plural(no_cost or 0, 'единицы', 'единиц', 'единиц')} "
                f"запаса нет управленческой себестоимости, "
                f"их стоимость в расчёте занижена."
                if no_cost
                else ""
            )
        ),
        plain=True,
    )

    stock_findings = _scope(findings, "stocks", limit=4)

    body = (
        kpi_grid(cards)
        + bucket_table
        + caveat
        + (_cards(stock_findings) if stock_findings
           else _no_findings_note("Состояние запаса"))
    )

    return page(
        "13",
        "Запасы",
        "Запасы: зона риска",
        "Сколько денег лежит в товаре, который не двигается, "
        "и что с этим делать.",
        body,
    )


# ============================================================
# ЗАКАЗЫ FBS
# ============================================================

def _recs(value, limit=None):
    """
    Приводит источник к списку словарей.

    Данные FBS приходят из DuckDB как DataFrame, а страницы
    работают со словарями: конвертируем в одном месте.
    """
    if value is None:
        return []

    if isinstance(value, list):
        rows = value
    elif hasattr(value, "to_dict"):
        if getattr(value, "empty", False):
            return []
        rows = value.to_dict("records")
    else:
        return []

    return rows[:limit] if limit else rows


def _fbs_unavailable(number, reason) -> str:
    return page(
        number,
        "Заказы FBS",
        "Заказы FBS",
        "",
        callout(
            "",
            f"<b>Данные по заказам FBS недоступны.</b> {escape(reason)}",
            plain=True,
        ),
    )


WEEKDAY_RU_SHORT = {
    0: "пн", 1: "вт", 2: "ср", 3: "чт",
    4: "пт", 5: "сб", 6: "вс",
}


def _fbs_recent_days(daily, days=7):
    """Последние N дней приёма заказов, свежие сверху не нужны."""
    rows = []

    for row in _recs(daily):
        d = as_date(row.get("order_date") or row.get("date"))
        if d is None:
            continue
        rows.append({**row, "_date": d})

    rows.sort(key=lambda item: item["_date"])

    return rows[-days:]


def fbs_assembly_page(fbs) -> str:
    if not fbs:
        return _fbs_unavailable(
            "14",
            "Срез заказов не загрузился, поэтому раздел пуст.",
        )

    kpi_data = fbs.get("kpi") or {}

    total = num(kpi_data.get("orders_total")) or 0
    in_work = num(kpi_data.get("orders_in_work")) or 0
    overdue = num(kpi_data.get("orders_overdue")) or 0
    amount = num(kpi_data.get("amount")) or 0

    overdue_share = 100.0 * overdue / in_work if in_work else 0.0
    avg_check = amount / total if total else 0.0

    cards = [
        kpi(
            "Заказов за период",
            fmt_qty(total) + " шт.",
            money(amount),
            "flat",
            f"средний заказ {money(avg_check)}",
        ),
        kpi(
            "Сейчас на сборке",
            fmt_qty(in_work) + " шт.",
            (
                pct(100.0 * in_work / total) + " от всех заказов"
                if total
                else ""
            ),
            "flat",
            (
                f"в среднем ждут "
                f"{fmt_hours(kpi_data.get('avg_age_in_work'))}"
            ),
        ),
        kpi(
            f"Просрочено, дольше {C.FBS_SLA_HOURS} ч",
            fmt_qty(overdue) + " шт.",
            pct(overdue_share) + " от сборки",
            (
                "bad"
                if overdue_share >= C.FBS_OVERDUE_ALERT_PCT
                else ("good" if not overdue else "flat")
            ),
            (
                f"самый старый "
                f"{fmt_hours(kpi_data.get('max_age_in_work'))}"
            ),
        ),
        kpi(
            "Отменено покупателем",
            fmt_qty(kpi_data.get("orders_cancelled")) + " шт.",
            (
                pct(
                    100.0
                    * (num(kpi_data.get("orders_cancelled")) or 0)
                    / total
                )
                if total
                else ""
            ),
            (
                "bad"
                if total
                and 100.0
                * (num(kpi_data.get("orders_cancelled")) or 0)
                / total
                >= 10
                else "flat"
            ),
            (
                f"закрыто и отгружено "
                f"{fmt_qty(kpi_data.get('orders_closed'))} шт."
            ),
        ),
    ]

    if overdue and in_work:
        assembly_note = (
            f"<b>Просрочено {fmt_qty(overdue)} "
            f"{plural(overdue, 'заказ', 'заказа', 'заказов')} — "
            f"{pct(overdue_share)} всего, что сейчас на сборке.</b> "
            f"В них примерно {money(overdue * avg_check)}: покупатель "
            f"эти деньги уже отдал, а мы их ещё не отгрузили. "
            f"Просрочка по FBS бьёт по позиции в выдаче и по "
            f"рейтингу продавца, поэтому хвост очереди разбирают "
            f"раньше, чем берут новые заказы."
        )
    else:
        assembly_note = (
            f"<b>Просрочки нет:</b> все заказы на сборке моложе "
            f"{C.FBS_SLA_HOURS} часов."
        )

    overdue_rows = sorted(
        _recs(fbs.get("overdue")),
        key=lambda row: -(num(row.get("age_hours")) or 0),
    )[:14]

    overdue_table = table(
        [
            {"key": "age_hours", "label": "Ждёт, ч", "num": True,
             "fmt": lambda v: fmt_hours(v)},
            {"key": "article", "label": "Артикул"},
            {"key": "title", "label": "Товар"},
            {"key": "brand", "label": "Бренд"},
            {"key": "warehouse", "label": "Склад отправки"},
            {"key": "office_name", "label": "Куда"},
            {"key": "amount", "label": "Сумма, ₽", "num": True,
             "fmt": money_exact},
        ],
        [
            {
                **row,
                "warehouse": _place(
                    row.get("warehouse"), row.get("warehouse_id")
                ),
                "office_name": _place(
                    row.get("office_name"),
                    row.get("destination_office"),
                ),
                "_alert": True,
            }
            for row in overdue_rows
        ],
        caption="Самые старые заказы на сборке",
        note="Отсортировано по времени ожидания. Этот список "
             "и есть план работы на сегодня.",
    ) if overdue_rows else ""

    try:
        from ..fbs_orders.config import (
            SUPPLIER_STATUS_NAMES,
            WB_STATUS_NAMES,
        )
    except Exception:
        SUPPLIER_STATUS_NAMES, WB_STATUS_NAMES = {}, {}

    statuses = [
        {
            **row,
            "supplier_status": SUPPLIER_STATUS_NAMES.get(
                row.get("supplier_status"),
                row.get("supplier_status") or "—",
            ),
            "wb_status": WB_STATUS_NAMES.get(
                row.get("wb_status"),
                row.get("wb_status") or "—",
            ),
        }
        for row in _recs(fbs.get("statuses"), limit=10)
    ]

    status_table = table(
        [
            {"key": "supplier_status", "label": "Наш статус"},
            {"key": "wb_status", "label": "Статус WB"},
            {"key": "orders", "label": "Заказов", "num": True,
             "fmt": fmt_qty},
            {"key": "avg_hours", "label": "Средний возраст",
             "num": True, "fmt": lambda v: fmt_hours(v)},
            {"key": "amount", "label": "Сумма, ₽", "num": True,
             "fmt": money_exact},
        ],
        statuses,
        caption="Где сейчас стоят заказы",
        note="Полезно, когда заказы «застряли»: видно, ждём мы "
             "или ждёт WB.",
    ) if statuses else ""

    recent_days = _fbs_recent_days(fbs.get("daily"), days=7)

    days_table = table(
        [
            {"key": "day_label", "label": "День"},
            {"key": "orders", "label": "Создано заказов, шт.",
             "num": True, "fmt": fmt_qty},
            {"key": "closed_orders", "label": "Закрыто", "num": True,
             "fmt": fmt_qty},
            {"key": "cancelled_orders", "label": "Отменено", "num": True,
             "fmt": fmt_qty},
            {"key": "cancel_share", "label": "Доля отмен", "num": True,
             "fmt": lambda v: pct(v)},
            {"key": "amount", "label": "Сумма, ₽", "num": True,
             "fmt": money_exact},
            {"key": "avg_check", "label": "Средний заказ, ₽",
             "num": True, "fmt": money_exact},
        ],
        [
            {
                **row,
                "day_label": (
                    f"{row['_date'].strftime('%d.%m')}, "
                    f"{WEEKDAY_RU_SHORT[row['_date'].weekday()]}"
                ),
                "cancel_share": (
                    100.0 * (num(row.get("cancelled_orders")) or 0)
                    / (num(row.get("orders")) or 1)
                ),
                "avg_check": (
                    (num(row.get("amount")) or 0)
                    / (num(row.get("orders")) or 1)
                ),
                "_alert": (
                    100.0 * (num(row.get("cancelled_orders")) or 0)
                    / (num(row.get("orders")) or 1)
                ) >= 15,
            }
            for row in recent_days
        ],
        total={
            "day_label": "За 7 дней",
            "orders": sum(
                num(r.get("orders")) or 0 for r in recent_days
            ),
            "closed_orders": sum(
                num(r.get("closed_orders")) or 0 for r in recent_days
            ),
            "cancelled_orders": sum(
                num(r.get("cancelled_orders")) or 0 for r in recent_days
            ),
            "cancel_share": (
                100.0
                * sum(num(r.get("cancelled_orders")) or 0 for r in recent_days)
                / (sum(num(r.get("orders")) or 0 for r in recent_days) or 1)
            ),
            "amount": sum(
                num(r.get("amount")) or 0 for r in recent_days
            ),
            "avg_check": (
                sum(num(r.get("amount")) or 0 for r in recent_days)
                / (sum(num(r.get("orders")) or 0 for r in recent_days) or 1)
            ),
        },
        caption="Сколько заказов приходило каждый день",
        note="Красным — дни, где отменили больше 15 % заказов. "
             "Дни недели подписаны: провал в субботу и провал "
             "во вторник — разные новости.",
    ) if recent_days else ""

    body = (
        kpi_grid(cards)
        + "<h3>Сколько заказов приходит</h3>"
        + days_table
        + figure(
            "Заказы FBS по дням",
            charts.fbs_daily(_recs(fbs.get("daily"))),
            "Столбики — количество заказов, линия — их сумма",
            "<b>Если линия и столбики расходятся, изменился "
            "средний чек:</b> заказов столько же, а денег больше "
            "или меньше.",
            "Мало дней для динамики",
        )
        + "<h3>Что сейчас на сборке</h3>"
        + figure(
            "Сколько заказов сколько времени ждёт сборки",
            charts.fbs_assembly_buckets(_recs(fbs.get("buckets_in_work"))),
            f"Красным — корзины за нормативом {C.FBS_SLA_HOURS} часов",
            assembly_note,
            "Сейчас на сборке ничего нет",
        )
        + overdue_table
        + status_table
    )

    return page(
        "14",
        "Заказы FBS",
        "Заказы FBS: сборка и сроки",
        (
            f"Данные актуальны на "
            f"{escape(date_short(fbs.get('as_of')))}. "
            f"Заказ считается просроченным, если ждёт сборки "
            f"дольше {C.FBS_SLA_HOURS} часов."
        ),
        body,
    )


def _place(*candidates) -> str:
    """
    Берёт первое осмысленное название места.

    Справочник складов и ПВЗ подтягивается отдельной командой,
    и пока он не залит, код подставляет заглушки вида «Склад 507»
    или «Пункт 12». Если рядом есть настоящее название — берём
    его, а голый номер оставляем только когда выбора нет.
    """
    fallback = ""

    for value in candidates:
        text = str(value or "").strip()

        if not text or text in ("—", "Не указан", "Склад не указан"):
            continue

        if text.startswith("Пункт ") or text.startswith("Склад "):
            fallback = fallback or text
            continue

        return text

    return fallback or "—"


def fbs_logistics_page(fbs, findings) -> str:
    if not fbs:
        return ""

    logistics = _recs(fbs.get("logistics"))

    grouped = {}
    for row in logistics:
        key = _place(row.get("warehouse"), row.get("warehouse_id"))
        current = grouped.setdefault(
            key,
            {"warehouse": key, "orders": 0.0, "overdue": 0.0, "amount": 0.0},
        )
        current["orders"] += num(row.get("orders")) or 0
        current["overdue"] += num(row.get("orders_overdue")) or 0
        current["amount"] += num(row.get("amount")) or 0

    warehouse_rows = sorted(
        grouped.values(),
        key=lambda row: -row["orders"],
    )[:10]

    warehouse_chart = charts.hbar(
        [row["warehouse"] for row in warehouse_rows],
        [row["orders"] for row in warehouse_rows],
        value_labels=[
            f"{charts._short(row['orders'])} заказов"
            + (
                f" · просрочено {charts._short(row['overdue'])}"
                if row["overdue"]
                else ""
            )
            + f" · {charts._short(row['amount'])} ₽"
            for row in warehouse_rows
        ],
        colors=[
            C.CRITICAL if row["overdue"] else C.SERIES_1
            for row in warehouse_rows
        ],
        axis_label="Заказов, шт.",
    )

    logistics_table = table(
        [
            {"key": "warehouse", "label": "Склад отправки"},
            {"key": "destination_office", "label": "Пункт назначения"},
            {"key": "orders", "label": "Заказов", "num": True,
             "fmt": fmt_qty},
            {"key": "orders_in_work", "label": "На сборке", "num": True,
             "fmt": fmt_qty},
            {"key": "orders_overdue", "label": "Просрочено", "num": True,
             "fmt": fmt_qty},
            {"key": "supplies", "label": "Поставок", "num": True,
             "fmt": fmt_qty},
            {"key": "amount", "label": "Сумма, ₽", "num": True,
             "fmt": money_exact},
        ],
        [
            {
                **row,
                "warehouse": _place(
                    row.get("warehouse"), row.get("warehouse_id")
                ),
                "destination_office": _place(
                    row.get("destination_office"),
                    row.get("office_name"),
                    row.get("destination_office_id"),
                ),
                "_alert": (num(row.get("orders_overdue")) or 0) > 0,
            }
            for row in sorted(
                logistics,
                key=lambda r: -(num(r.get("orders")) or 0),
            )[:14]
        ],
        total={
            "warehouse": "Итого",
            "destination_office": "",
            "orders": sum(num(r.get("orders")) or 0 for r in logistics),
            "orders_in_work": sum(
                num(r.get("orders_in_work")) or 0 for r in logistics
            ),
            "orders_overdue": sum(
                num(r.get("orders_overdue")) or 0 for r in logistics
            ),
            "supplies": sum(num(r.get("supplies")) or 0 for r in logistics),
            "amount": sum(num(r.get("amount")) or 0 for r in logistics),
        },
        caption="Откуда и куда уходят заказы",
        note="Красным — направления, где есть просроченные заказы.",
    ) if logistics else ""

    supplies = _recs(fbs.get("supplies"), limit=12)

    supplies_table = table(
        [
            {"key": "supply_name", "label": "Поставка"},
            {"key": "created_at", "label": "Создана", "num": True,
             "fmt": lambda v: date_short(v)},
            {"key": "closed_at", "label": "Закрыта", "num": True,
             "fmt": lambda v: date_short(v)},
            {"key": "orders", "label": "Заказов", "num": True,
             "fmt": fmt_qty},
            {"key": "cancelled_orders", "label": "Отменено", "num": True,
             "fmt": fmt_qty},
            {"key": "avg_hours_to_close", "label": "Часов до закрытия",
             "num": True, "fmt": lambda v: fmt_hours(v)},
            {"key": "amount", "label": "Сумма, ₽", "num": True,
             "fmt": money_exact},
        ],
        [
            {
                **row,
                "_alert": not row.get("closed_at"),
            }
            for row in supplies
        ],
        caption="Последние поставки",
        note="Красным — поставки, которые ещё не закрыты: пока они "
             "открыты, заказы внутри не считаются отгруженными.",
    ) if supplies else ""

    products = _recs(fbs.get("products"), limit=14)

    products_table = table(
        [
            {"key": "article", "label": "Артикул"},
            {"key": "title", "label": "Товар"},
            {"key": "brand", "label": "Бренд"},
            {"key": "orders", "label": "Заказов", "num": True,
             "fmt": fmt_qty},
            {"key": "orders_in_work", "label": "На сборке", "num": True,
             "fmt": fmt_qty},
            {"key": "cancelled_orders", "label": "Отменено", "num": True,
             "fmt": fmt_qty},
            {"key": "amount", "label": "Сумма, ₽", "num": True,
             "fmt": money_exact},
        ],
        products,
        caption="Что заказывают чаще всего",
        note="Эти товары стоит держать на своём складе в первую "
             "очередь: по ним каждая просрочка заметнее всего.",
    ) if products else ""

    fbs_cards = _scope(findings, "fbs", limit=3)

    body = (
        figure(
            "Заказы по складам отправки",
            warehouse_chart,
            "Красным — склады, где есть просрочка",
            "<b>Если просрочка собрана на одном складе, менять "
            "процесс на всех не нужно</b> — разбираться надо там.",
            "Нет данных по складам",
        )
        + logistics_table
        + supplies_table
        + products_table
        + (_cards(fbs_cards) if fbs_cards
           else _no_findings_note("Работа с заказами FBS"))
    )

    return page(
        "15",
        "Заказы FBS",
        "Заказы FBS: склады, поставки и товары",
        "Откуда отправляем, как быстро закрываются поставки "
        "и что именно у нас заказывают.",
        body,
    )


# ============================================================
# 16. ВЫВОДЫ И РЕКОМЕНДАЦИИ
# ============================================================

def findings_page(payload, findings) -> str:
    if not findings:
        return page(
            "16",
            "Выводы",
            "Выводы и рекомендации",
            "",
            callout(
                "",
                "<b>Отклонений, о которых стоит говорить, нет.</b> "
                "Все показатели в пределах обычного разброса.",
                plain=True,
            ),
        )

    groups = [
        ("critical", "Требует решения",
         "Без решения цифра продолжит ухудшаться сама."),
        ("serious", "Под контроль",
         "Пока не критично, но тенденция неприятная."),
        ("warning", "Обратить внимание",
         "Стоит проверить, пока не выросло."),
        ("good", "Что работает",
         "Это стоит сохранить и по возможности повторить."),
        ("neutral", "К сведению",
         "Факты, которые полезно держать в голове."),
    ]

    body = ""

    for severity, title, note in groups:
        block = [item for item in findings if item.severity == severity]
        if not block:
            continue

        body += f"<h3>{escape(title)}</h3>"
        body += f'<p class="small muted">{escape(note)}</p>'
        body += _cards(block)

    actions = [
        f"<b>{item.title}.</b> {item.action}"
        for item in findings
        if item.action and item.severity in ("critical", "serious")
    ]

    if actions:
        body += (
            '<div class="rule-soft"></div>'
            + "<h3>Что сделать в первую очередь</h3>"
            + '<p class="small muted">'
            + "Список отсортирован по деньгам, которые стоят "
            + "за каждым пунктом."
            + "</p>"
            + bullets(actions)
        )

    return page(
        "16",
        "Выводы",
        "Выводы и рекомендации",
        "Полный список: что произошло, почему и что делать. "
        "Выводы, у которых не удалось назвать причину, в отчёт "
        "не попадают — общая фраза занимает место и создаёт "
        "ощущение, что вопрос разобран.",
        body,
    )


# ============================================================
# 17. МЕТОДИКА
# ============================================================

def methodology_page(payload, fbs) -> str:
    financial = _node(payload, "financial")
    quality = _node(payload, "financial", "cost_quality", "ytd")

    definitions = table(
        [
            {"key": "term", "label": "Показатель"},
            {"key": "how", "label": "Как считается"},
        ],
        [
            {"term": "Выручка",
             "how": "Продажи минус возвраты, с НДС, по строкам "
                    "реализации. Это же число стоит в карточках, "
                    "в календаре по дням и в разложении по "
                    "факторам — они считаются из одного контура "
                    "и обязаны сходиться."},
            {"term": "Почему бренды не сходятся с карточкой",
             "how": "Разрезы по брендам, категориям и ценам "
                    "берутся из витрины продаж, а карточки, "
                    "календарь и план — из контура реализации. "
                    "Витрины собираются по-разному и за один день "
                    "расходятся на несколько процентов. Внутри "
                    "каждого разреза цифры согласованы, "
                    "но складывать их между разрезами нельзя."},
            {"term": "Выручка без НДС",
             "how": "База для процентов маржи и расходов: "
                    "выручка, приведённая к сумме без налога."},
            {"term": "Себестоимость",
             "how": "Управленческая себестоимость по FIFO на дату "
                    "продажи, без НДС."},
            {"term": "Комиссия WB",
             "how": "Комиссия маркетплейса по отчёту реализации, "
                    "без НДС."},
            {"term": "Маржа",
             "how": "Выручка без НДС минус себестоимость и комиссия. "
                    "До логистики, хранения, рекламы и штрафов."},
            {"term": "Расходы WB",
             "how": "Логистика, хранение, приёмка, продвижение "
                    "и штрафы по отчёту WB, без НДС."},
            {"term": "Результат после расходов WB",
             "how": "Маржа минус расходы WB. Это ещё не чистая "
                    "прибыль: сюда не входят налоги, зарплаты "
                    "и прочие расходы компании."},
            {"term": "Покрытие запасом",
             "how": "Остаток, делённый на средние продажи за "
                    "последние 30 дней. Показывает, на сколько "
                    "дней хватит товара."},
            {"term": "Зона риска по запасу",
             "how": "Позиции с покрытием больше 90 дней плюс те, "
                    "что не продавались ни разу за 30 дней."},
            {"term": "Просрочка FBS",
             "how": f"Заказ, который ждёт сборки дольше "
                    f"{C.FBS_SLA_HOURS} часов."},
            {"term": "Вклад количества и цены",
             "how": "Разница в штуках, умноженная на прежнюю цену, "
                    "и разница в цене, умноженная на новое "
                    "количество. Сумма двух вкладов равна "
                    "изменению выручки."},
        ],
        caption="Что означает каждый показатель",
    )

    limits = bullets([
        "<b>Отчёт строится по закрытым данным.</b> Цифры в нём "
        "не меняются после выпуска — на выпуск можно ссылаться "
        "в переписке.",

        "<b>Неделя здесь всегда календарная</b>, с понедельника "
        "по воскресенье. Незакрытая неделя в сравнения не входит "
        "и помечается отдельно: сравнивать четыре дня с семью — "
        "значит увидеть падение там, где его нет.",

        "<b>В отчёте два контура выручки, и это нормально.</b> "
        "Контур реализации (карточки, календарь, недели, план) "
        "и витрина продаж (бренды, категории, цены). Они "
        "расходятся на несколько процентов, потому что "
        "собираются из разных таблиц. Внутри одного контура "
        "всё сходится до рубля; между контурами — нет, "
        "и складывать их не надо.",

        (
            f"<b>Расходы WB загружены не за все дни периода.</b> "
            f"Где покрытие неполное, это указано прямо под "
            f"таблицей: результат за такие дни выглядит лучше, "
            f"чем он есть."
        ),

        (
            f"<b>У части продаж нет управленческой себестоимости</b> — "
            f"{pct(quality.get('no_cost_pct'))} единиц с начала года. "
            f"По ним маржа завышена."
            if quality.get("no_cost_pct") is not None
            else ""
        ),

        "<b>Прогноз — это продолжение текущего темпа</b>, а не "
        "обещание. Акции, новые товары и изменения рекламного "
        "бюджета в модель не заложены.",

        "<b>Эластичность по брендам считается только там, где "
        "цена реально менялась.</b> Если бренд весь период "
        "продавался по одной цене, связь считать не на чем, "
        "и он в матрицу не попадает.",

        (
            f"<b>Заказы FBS — оперативный срез</b> на "
            f"{escape(date_short(fbs.get('as_of')))}, он "
            f"обновляется раз в сутки и не сверен с отчётом "
            f"реализации: суммы по нему и по продажам совпадать "
            f"не должны."
            if fbs
            else ""
        ),
    ])

    history = ""
    if financial.get("history_start"):
        history = (
            f'<p class="small muted">Финансовая история загружена '
            f'с {escape(date_short(financial.get("history_start")))} '
            f'по {escape(date_short(financial.get("history_end")))}, '
            f'{escape(str(financial.get("source_rows") or 0))} '
            f'дней с данными.</p>'
        )

    body = (
        definitions
        + '<div class="rule-soft"></div>'
        + "<h3>Что этот отчёт не показывает</h3>"
        + limits
        + history
    )

    return page(
        "17",
        "Методика",
        "Методика",
        "Чтобы к цифрам не возвращаться с вопросом «а как это "
        "посчитано».",
        body,
    )


# ============================================================
# СТРУКТУРА: ВЫРУЧКА ПРОТИВ ПРИБЫЛИ
# ============================================================

def _mix_totals(rows):
    revenue = sum(num(r.get("revenue_vatless")) or 0 for r in rows)
    profit = sum(num(r.get("gross_profit_man")) or 0 for r in rows)
    margin = 100.0 * profit / revenue if revenue else None
    return revenue, profit, margin


def _mix_table(rows, subject, total_revenue, total_profit, average_margin,
               limit=18, caption="", note="", wide=True):
    ranked = sorted(
        rows,
        key=lambda r: -(num(r.get("revenue_vatless")) or 0),
    )[:limit]

    table_rows = []

    for row in ranked:
        revenue = num(row.get("revenue_vatless")) or 0
        profit = num(row.get("gross_profit_man")) or 0
        rows_count = num(row.get("rows_count")) or 0
        no_cost = num(row.get("no_man_cost")) or 0

        table_rows.append({
            **row,
            "revenue_share": (
                100.0 * revenue / total_revenue if total_revenue else None
            ),
            "profit_share": (
                100.0 * profit / total_profit if total_profit else None
            ),
            "no_cost_share": (
                100.0 * no_cost / rows_count if rows_count else None
            ),
            "_alert": profit < 0,
        })

    return table(
        [
            {"key": "name", "label": subject},
            {"key": "revenue_vatless", "label": "Выручка без НДС, ₽",
             "num": True, "fmt": money_exact},
            {"key": "revenue_share", "label": "Доля выручки",
             "num": True, "fmt": lambda v: pct(v)},
            {"key": "net_qty", "label": "Продано, шт.",
             "num": True, "fmt": fmt_qty},
            {"key": "cogs_man", "label": "Себестоимость, ₽",
             "num": True, "fmt": money_exact},
            {"key": "net_comission", "label": "Комиссия WB, ₽",
             "num": True, "fmt": money_exact},
            {"key": "gross_profit_man", "label": "Маржа, ₽",
             "num": True, "fmt": money_exact},
            {"key": "margin_man_pct", "label": "Маржинальность",
             "num": True, "fmt": lambda v: pct(v)},
            {"key": "profit_share", "label": "Доля маржи",
             "num": True, "fmt": lambda v: pct(v)},
            {"key": "products_count", "label": "Товаров",
             "num": True, "fmt": fmt_qty},
            {"key": "no_cost_share", "label": "Без с/с",
             "num": True, "fmt": lambda v: pct(v)},
        ],
        table_rows,
        total={
            "name": "Итого",
            "revenue_vatless": total_revenue,
            "revenue_share": 100.0,
            "net_qty": sum(num(r.get("net_qty")) or 0 for r in rows),
            "cogs_man": sum(num(r.get("cogs_man")) or 0 for r in rows),
            "net_comission": sum(
                num(r.get("net_comission")) or 0 for r in rows
            ),
            "gross_profit_man": total_profit,
            "margin_man_pct": average_margin,
            "profit_share": 100.0,
            "products_count": sum(
                num(r.get("products_count")) or 0 for r in rows
            ),
            "no_cost_share": None,
        },
        caption=caption,
        note=note,
        wide=wide,
    )


def _mix_page(payload, findings, number, dimension, title, note, subject) -> str:
    mix = _node(payload, "mix")
    rows = mix.get(dimension) or []
    week_rows = mix.get(f"{dimension}_week") or []

    if not mix.get("available") or not rows:
        return page(
            number,
            "Структура",
            title,
            "",
            callout(
                "",
                f"<b>Разрез «{escape(subject)}» не собрался.</b> "
                "Показатель считается тем же запросом, что и "
                "вкладка «Структура выручки» в дашборде — если "
                "он недоступен, отчёт не выдумывает цифры.",
                plain=True,
            ),
        )

    total_revenue, total_profit, average_margin = _mix_totals(rows)
    week_revenue, week_profit, week_margin = _mix_totals(week_rows)

    losers = [
        r for r in rows
        if (num(r.get("gross_profit_man")) or 0) < 0
    ]

    # Сколько позиций делают половину прибыли — короткий ответ
    # на вопрос «на чём мы вообще зарабатываем».
    by_profit = sorted(
        (r for r in rows if (num(r.get("gross_profit_man")) or 0) > 0),
        key=lambda r: -(num(r.get("gross_profit_man")) or 0),
    )

    half, half_count = 0.0, 0
    for row in by_profit:
        if total_profit and half >= total_profit * 0.5:
            break
        half += num(row.get("gross_profit_man")) or 0
        half_count += 1

    period_label = (
        f"{escape(date_short(mix.get('date_from')))}–"
        f"{escape(date_short(mix.get('date_to')))}"
    )

    week_label = (
        f"{escape(date_short(mix.get('week_from')))}–"
        f"{escape(date_short(mix.get('week_to')))}"
    )

    cards = [
        kpi(
            "Выручка без НДС",
            money(total_revenue),
            "",
            "flat",
            f"за {fmt_days(mix.get('days'))}, {period_label}",
        ),
        kpi(
            "Маржа",
            money(total_profit),
            pct(average_margin),
            "good" if (average_margin or 0) >= C.MARGIN_ALERT_PCT else "bad",
            "после себестоимости и комиссии WB",
        ),
        kpi(
            "Половину прибыли дают",
            f"{half_count} из {len(rows)}",
            "",
            "flat",
            f"остальные {len(rows) - half_count} — вторую половину",
        ),
        kpi(
            "Работают в минус",
            str(len(losers)),
            (
                money(sum(num(r.get("gross_profit_man")) or 0 for r in losers))
                if losers
                else ""
            ),
            "bad" if losers else "good",
            "маржа ниже нуля после себестоимости и комиссии",
        ),
    ]

    chart_note = (
        f"<b>Слева деньги, справа процент — строки одни и те же.</b> "
        f"Пунктир справа — средняя маржинальность "
        f"{pct(average_margin)}. Жёлтым отмечено то, что ниже "
        f"средней, красным — то, что уходит в минус. "
        f"Длинная синяя полоса и жёлтая рядом — это и есть "
        f"случай «много оборота, мало прибыли»."
    )

    # ---- короткий горизонт: последняя закрытая неделя ------------
    week_block = ""

    if week_rows:
        ranked_week = sorted(
            week_rows,
            key=lambda r: -(num(r.get("revenue_vatless")) or 0),
        )[:8]

        week_table_rows = []

        for row in ranked_week:
            margin_now = num(row.get("margin_man_pct"))

            base = next(
                (
                    num(r.get("margin_man_pct"))
                    for r in rows
                    if r.get("name") == row.get("name")
                ),
                None,
            )

            week_table_rows.append({
                **row,
                "revenue_share": (
                    100.0 * (num(row.get("revenue_vatless")) or 0)
                    / week_revenue
                    if week_revenue else None
                ),
                "margin_base": base,
                "margin_delta": (
                    margin_now - base
                    if margin_now is not None and base is not None
                    else None
                ),
                "_alert": (num(row.get("gross_profit_man")) or 0) < 0,
            })

        week_block = (
            f"<h3>Последняя закрытая неделя: {week_label}</h3>"
            + table(
                [
                    {"key": "name", "label": subject},
                    {"key": "revenue_vatless", "label": "Выручка, ₽",
                     "num": True, "fmt": money_exact},
                    {"key": "revenue_share", "label": "Доля",
                     "num": True, "fmt": lambda v: pct(v)},
                    {"key": "gross_profit_man", "label": "Маржа, ₽",
                     "num": True, "fmt": money_exact},
                    {"key": "margin_man_pct", "label": "Маржинальность",
                     "num": True, "fmt": lambda v: pct(v)},
                    {"key": "margin_base", "label": "Она же за 90 дней",
                     "num": True, "fmt": lambda v: pct(v)},
                    {"key": "margin_delta", "label": "Разница",
                     "num": True, "fmt": lambda v: pp(v)},
                ],
                week_table_rows,
                total={
                    "name": "Итого за неделю",
                    "revenue_vatless": week_revenue,
                    "revenue_share": 100.0,
                    "gross_profit_man": week_profit,
                    "margin_man_pct": week_margin,
                    "margin_base": average_margin,
                    "margin_delta": (
                        week_margin - average_margin
                        if week_margin is not None
                        and average_margin is not None
                        else None
                    ),
                },
                caption="",
                note=(
                    "Колонка «разница» показывает, стала "
                    "маржинальность за неделю выше или ниже "
                    "своего обычного уровня за 90 дней. Неделя "
                    "короткая, поэтому одна крупная поставка "
                    "или возврат двигают её сильно — решения "
                    "принимайте по 90 дням, а неделю используйте "
                    "как сигнал, что что-то изменилось."
                ),
            )
        )

    method = callout(
        "Как считается маржа",
        "Выручка без НДС минус управленческая себестоимость FIFO "
        "плюс комиссия WB — комиссия приходит со своим знаком, "
        "поэтому здесь сложение. Это тот же расчёт, что во "
        "вкладке «Структура выручки» в дашборде, цифры должны "
        "совпадать. В маржу не входят логистика, хранение, "
        "реклама и штрафы: они не раскладываются по брендам "
        "и живут в разделе «Финансовый результат».",
        plain=True,
    )

    cards_html = _cards(
        [f for f in findings if f.scope in ("mix", "data")][:3]
    )

    body = (
        kpi_grid(cards)
        + figure(
            f"{subject}: выручка и маржинальность",
            charts.revenue_vs_margin(rows),
            f"Топ-12 по выручке за {fmt_days(mix.get('days'))}",
            chart_note,
            "Нет данных для разреза",
        )
        + week_block
        + method
        + cards_html
    )

    main = page(number, "Структура", title, note, body)

    # Широкая таблица уезжает на отдельную альбомную страницу:
    # одиннадцать колонок в портрете читать невозможно.
    wide = page(
        number,
        "Структура",
        f"{subject}: полная таблица",
        (
            f"За {fmt_days(mix.get('days'))}, {period_label}. "
            f"Отсортировано по выручке."
        ),
        _mix_table(
            rows,
            subject,
            total_revenue,
            total_profit,
            average_margin,
            caption="",
            note=(
                "Красным — то, что работает в минус. Колонка "
                "«без с/с» — доля продаж, у которых не нашлась "
                "управленческая себестоимость: чем она выше, тем "
                "сильнее завышена маржинальность в этой строке. "
                "Комиссия WB показана со своим знаком, поэтому "
                "маржа = выручка − себестоимость + комиссия."
            ),
        ),
        landscape=True,
    )

    return main + wide


def brand_profit_page(payload, findings) -> str:
    return _mix_page(
        payload,
        findings,
        "06",
        "brands",
        "Бренды: кто даёт оборот, а кто прибыль",
        "Это разные списки почти всегда. Страница нужна, чтобы "
        "не перепутать большой бренд с выгодным.",
        "Бренд",
    )


def category_profit_page(payload, findings) -> str:
    return _mix_page(
        payload,
        findings,
        "07",
        "categories",
        "Категории: кто даёт оборот, а кто прибыль",
        "То же самое в разрезе категорий: здесь обычно виднее, "
        "какое направление тянет маржу вниз.",
        "Категория",
    )
