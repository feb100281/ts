# gear/app/daily_sales/assistant/digest.py
"""Утренняя сводка продаж для Telegram: собирается из базы без обращения к Claude.

Продажи «как на сайте WB» за последний загруженный день в сравнении с предыдущим
днём и тем же днём недели неделю назад.
"""
from __future__ import annotations

from datetime import date, timedelta
from html import escape

from conns import get_duckdb_conn_with_opt

WD = ("пн", "вт", "ср", "чт", "пт", "сб", "вс")
QTY, RET, NET_QTY = "Продажи, шт", "Возвраты, шт", "Итого, шт"
AFTER, RET_RUB = "После СПП: итого, ₽", "До СПП: возвраты, ₽"
RUB, NET_RUB, PAY = "До СПП: продажи, ₽", "До СПП: итого, ₽", "К перечислению, ₽"


def loaded_date() -> date | None:
    """Последняя дата продаж в базе; None — если узнать не удалось."""
    try:
        with get_duckdb_conn_with_opt(with_pg=False) as con:
            r = con.execute("SELECT MAX(date_from)::DATE FROM sales.sales_long "
                            "WHERE field = 'retail_price'").fetchone()
        return r[0] if r and r[0] else None
    except Exception:
        return None


# расходы WB: (подпись, условие по sales.sales_long); суммы с НДС, как в отчёте WB
WB_COSTS = (
    ("Логистика", "field = 'delivery_rub'"),
    ("Хранение", "field = 'storage_fee'"),
    ("Приёмка", "field = 'acceptance'"),
    ("Штрафы", "field = 'penalty'"),
    ("Лояльность", "field IN ('cashback_amount', 'cashback_commission_change')"),
    ("Маркетинг", "field = 'deduction' AND btn IS NOT NULL "
                  "AND NOT STARTS_WITH(btn, 'Платеж') "
                  "AND NOT STARTS_WITH(btn, 'Перевод')"),
)
BRAND_MIN = 10_000            # изменения бренда мельче этого в сводку не идут, ₽


def wb_costs(day: date) -> list[tuple[str, float, float, float]]:
    """[(статья, за день, за 7 дней по day, за 7 дней до этого)]; расход — положительный."""
    cols = ", ".join(
        f"SUM(CASE WHEN {cond} THEN (CASE WHEN oper = 'cr' THEN val ELSE -val END) END) / 100"
        for _, cond in WB_COSTS)
    with get_duckdb_conn_with_opt(with_pg=False) as con:
        rows = dict((r[0], r[1:]) for r in con.execute(
            "SELECT CASE WHEN date_from::DATE = ?::DATE THEN 'day' "
            "            WHEN date_from::DATE > ?::DATE THEN 'cur' ELSE 'old' END AS k, "
            f"{cols} FROM sales.sales_long WHERE date_from::DATE BETWEEN ? AND ? GROUP BY 1",
            [day, day - timedelta(days=7), day - timedelta(days=13), day]).fetchall())
    zero = [0] * len(WB_COSTS)
    d, c, o = (rows.get(k) or zero for k in ("day", "cur", "old"))
    return [(name, float(d[i] or 0), float(d[i] or 0) + float(c[i] or 0), float(o[i] or 0))
            for i, (name, _) in enumerate(WB_COSTS)]


def _n(v):
    return f"{int(round(float(v or 0))):,}".replace(",", " ")


def _rub(v):
    v = float(v or 0)
    if abs(v) >= 1_000_000:
        return f"{v / 1_000_000:.2f}".replace(".", ",") + " млн ₽"
    if abs(v) >= 100_000:
        return f"{v / 1000:.0f} тыс ₽"
    if abs(v) >= 1000:
        return f"{v / 1000:.1f}".replace(".", ",") + " тыс ₽"
    return f"{v:.0f} ₽"


def _chg(cur, prev):
    """Изменение в процентах со стрелкой; «—», если сравнивать не с чем."""
    if not prev:
        return "—"
    p = (float(cur) - float(prev)) / abs(float(prev)) * 100
    return ("▲ " if p >= 0 else "▼ ") + f"{abs(p):.1f}".replace(".", ",") + "%"


def _diff(v):
    v = int(round(v))
    return ("▲ " if v > 0 else "▼ " if v < 0 else "") + _n(abs(v)) if v else "0"


def _mln(v):
    return f"{float(v or 0) / 1_000_000:.2f}".replace(".", ",")


def _ths(v):
    return f"{float(v or 0) / 1000:.1f}".replace(".", ",")


def _pre(rows, wide: bool = True) -> str:
    """Таблица моноширинным блоком с границами колонок; стрелки стоят в столбик."""
    def split(c):
        c = str(c)
        return (c[0], c[2:]) if c[:2] in ("▲ ", "▼ ") else ("", c)
    cells = [[split(c) for c in r] for r in rows]
    n = len(rows[0])
    arrow = [any(r[i][0] for r in cells) for i in range(n)]
    w = [max(len(r[i][1]) for r in cells) + (1 if arrow[i] else 0) for i in range(n)]
    sep, cross = (" │ ", "─┼─") if wide else ("│", "┼")
    out = []
    for k, r in enumerate(cells):
        line = [r[0][1].ljust(w[0])] + [
            ((a or " ") if arrow[i] else "") + v.rjust(w[i] - (1 if arrow[i] else 0))
            for i, (a, v) in enumerate(r) if i]
        out.append(sep.join(line).rstrip())
        if k == 0:
            out.append(cross.join("─" * x for x in w))
    return "<pre>" + escape("\n".join(out)) + "</pre>"


MONTHS = ("января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа",
          "сентября", "октября", "ноября", "декабря")
WD_FULL = ("понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье")
WD_IN = ("в понедельник", "во вторник", "в среду", "в четверг", "в пятницу", "в субботу",
         "в воскресенье")
WD_LAST = ("в прошлый понедельник", "в прошлый вторник", "в прошлую среду", "в прошлый четверг",
           "в прошлую пятницу", "в прошлую субботу", "в прошлое воскресенье")
WD_TO = ("к прошлому понедельнику", "к прошлому вторнику", "к прошлой среде",
         "к прошлому четвергу", "к прошлой пятнице", "к прошлой субботе",
         "к прошлому воскресенью")


def _long(d: date) -> str:
    return f"{d.day} {MONTHS[d.month - 1]}"


def _span_long(a: date, b: date) -> str:
    if a == b:
        return _long(a)
    return f"{a.day}–{_long(b)}" if a.month == b.month else f"{_long(a)} – {_long(b)}"


UP, DOWN = "🟢", "🔴"          # цвет в тексте Telegram задать нельзя — только значком


def _more(cur, prev) -> str:
    """«на 12,3% больше» / «на 4,0% меньше» — для связного текста."""
    if not prev:
        return ""
    p = (float(cur) - float(prev)) / abs(float(prev)) * 100
    if abs(p) < 0.05:
        return "столько же"
    return f"на <b>{abs(p):.1f}".replace(".", ",") + ("% больше</b>" if p > 0 else "% меньше</b>")


def _safe(what, fn):
    """Блок сводки не должен ронять всю рассылку."""
    try:
        return fn()
    except Exception as e:
        print(f"[digest] {what}: {type(e).__name__}: {e}", flush=True)
        return None


def _quote(text):
    return f"<blockquote>{text}</blockquote>"


def blocks(day: date, loaded: date | None = None, charts: bool = True) -> list[dict]:
    """Сводка по блокам: [{"photo": PNG | None, "text": HTML}]; пусто — продаж за день нет."""
    import pandas as pd
    from ..wb_sales_export import fetch
    from . import digest_charts as ch

    prev, week = day - timedelta(days=1), day - timedelta(days=7)
    mon = day - timedelta(days=day.weekday())               # неделя нарастающим итогом
    m_start = day.replace(day=1)                            # месяц с начала
    pm_end = m_start - timedelta(days=1)
    pm_start = pm_end.replace(day=1)
    pm_to = min(pm_start + (day - m_start), pm_end)         # столько же дней прошлого месяца

    df = fetch(min(pm_start, day - timedelta(days=13)), day, "brand_day", [])
    if df.empty:
        return []
    dcol, bcol = df.columns[0], df.columns[1]
    df[dcol] = pd.to_datetime(df[dcol]).dt.date
    num = [c for c in (QTY, RET, NET_QTY, RUB, NET_RUB, PAY, AFTER, RET_RUB) if c in df.columns]
    days = df.groupby(dcol)[num].sum()
    if day not in days.index or not days.at[day, QTY]:
        return []
    t = days.loc[day]

    def span(a, b, col):
        return float(days.loc[[d for d in days.index if a <= d <= b], col].sum())

    def rng(a, b):
        if a == b:
            return f"{a:%d.%m}"
        return f"{a:%d}–{b:%d.%m}" if a.month == b.month else f"{a:%d.%m}–{b:%d.%m}"

    def pic(what, fn):
        return _safe(f"график «{what}»", fn) if charts else None

    out = []
    wd, wd_w = WD[day.weekday()], WD[week.weekday()]
    week_val = span(week, week, NET_RUB)
    w_prev = (mon - timedelta(days=7), week)
    pc = lambda v: f"{v:.1f}".replace(".", ",").replace("-", "−") + "%"

    # ---- 1. продажи
    wk, wk_old = span(mon, day, NET_RUB), span(*w_prev, NET_RUB)
    mo, mo_old = span(m_start, day, NET_RUB), span(pm_start, pm_to, NET_RUB)
    lines = [f"<b>Продажи · {wd} {day:%d.%m}</b>",
             _quote((f"{UP if t[NET_RUB] >= week_val else DOWN} " if week_val else "")
                    + f"Вчера продали на <b>{_rub(t[NET_RUB])}</b> — это <b>{_n(t[NET_QTY])} шт</b> "
                    "за вычетом возвратов.")]
    cmp_ = []
    if week_val:
        cmp_.append(f"{_more(t[NET_RUB], week_val)}, чем {WD_LAST[week.weekday()]} "
                    f"({_rub(week_val)})")
    if prev in days.index and days.at[prev, NET_RUB]:
        cmp_.append(f"{_more(t[NET_RUB], days.at[prev, NET_RUB])}, чем "
                    f"{WD_IN[prev.weekday()]}")
    if cmp_:
        lines.append("Это " + " и ".join(cmp_) + ".")
    tail = []
    if day > mon and wk_old:
        tail.append(f"С начала недели наторговали на <b>{_rub(wk)}</b> — {_more(wk, wk_old)}, чем за "
                    "те же дни прошлой недели.")
    if day > m_start and mo_old:
        tail.append(f"С начала месяца — <b>{_rub(mo)}</b>, {_more(mo, mo_old)}, чем за "
                    f"{_span_long(pm_start, pm_to)}.")
    if tail:
        lines.append(" ".join(tail))
    lines.append(_pre([("", "млн ₽", "шт", "изм."),
                       ("Вчера", _mln(t[NET_RUB]), _n(t[NET_QTY]), _chg(t[NET_RUB], week_val)),
                       ("Неделя", _mln(wk), _n(span(mon, day, NET_QTY)), _chg(wk, wk_old)),
                       ("Месяц", _mln(mo), _n(span(m_start, day, NET_QTY)), _chg(mo, mo_old))]))
    if t[QTY]:
        ret_rub = f" на {_rub(abs(t[RET_RUB]))}" if RET_RUB in days.columns else ""
        lines.append(f"Покупатели вернули <b>{_n(t[RET])} шт</b>{ret_rub} — это "
                     f"{pc(float(t[RET]) / float(t[QTY]) * 100)} от проданного.")
    if t[NET_QTY] > 0:
        check = f"Средний чек — <b>{_n(t[NET_RUB] / t[NET_QTY])} ₽</b> по нашей цене"
        if AFTER in days.columns and t[NET_RUB]:
            spp = (1 - float(t[AFTER]) / float(t[NET_RUB])) * 100
            check += (f"; покупатель со скидкой WB ({pc(spp)}) платил в среднем "
                      f"<b>{_n(t[AFTER] / t[NET_QTY])} ₽</b>")
        lines.append(check + ".")
    if PAY in days.columns:
        lines.append(f"WB перечислит нам за этот день <b>{_rub(t[PAY])}</b>.")
    lines.append(f"<i>Как на сайте WB, с НДС, до СПП. Данные в базе по "
                 f"{(loaded or day):%d.%m}.</i>")
    d14 = [day - timedelta(days=13 - i) for i in range(14)]
    v14 = [float(days.at[d, NET_RUB]) / 1e6 if d in days.index else 0.0 for d in d14]
    sub = (f"{_chg(t[NET_RUB], week_val)} к {wd_w} {week:%d.%m} · " if week_val else "") \
        + "14 дней, млн ₽"
    out.append({"text": "\n".join(lines), "photo": pic("продажи", lambda: ch.sales_days(
        d14, v14, f"Продажи за {day:%d.%m} — {_rub(t[NET_RUB])}", sub))})

    # ---- 2. бренды и категории: заметные изменения к тому же дню прошлой недели
    def movers(cur, old, title, chart_title, what):
        diff = cur.sub(old, fill_value=0).sort_values()
        up, down = diff[diff >= BRAND_MIN].tail(3)[::-1], diff[diff <= -BRAND_MIN].head(3)
        if not (len(up) or len(down)):
            return None
        top = max(list(up.items()) + list(down.items()), key=lambda x: abs(x[1]))
        lines = [f"<b>{title}</b>", _quote(
            f"{UP if top[1] > 0 else DOWN} Сильнее всего {'выросли' if top[1] > 0 else 'просели'} "
            f"продажи {'в категории ' if 'категор' in what else ''}"
            f"<b>{escape(str(top[0]))}</b>: {'+' if top[1] > 0 else '−'}"
            f"{_rub(abs(top[1]))} {WD_TO[week.weekday()]}.")]
        if len(up):
            lines.append(f"{UP} Выросли: " + ", ".join(
                f"{escape(str(k))} (<b>+{_rub(v)}</b>)" for k, v in up.items()) + ".")
        if len(down):
            lines.append(f"{DOWN} Просели: " + ", ".join(
                f"{escape(str(k))} (<b>−{_rub(abs(v))}</b>)" for k, v in down.items()) + ".")
        lines.append(f"<i>Сравниваем вчерашний день с тем же днём прошлой недели, {what}, "
                     "продажи за вычетом возвратов.</i>")
        rows = [(str(k), float(v)) for k, v in list(up.items()) + list(down.items())]
        return {"text": "\n".join(lines), "photo": pic(title, lambda: ch.brands(
            rows, chart_title, f"{day:%d.%m} к {wd_w} {week:%d.%m} · изменение продаж"))}

    if week in days.index:
        b = movers(df[df[dcol] == day].groupby(bcol)[NET_RUB].sum(),
                   df[df[dcol] == week].groupby(bcol)[NET_RUB].sum(),
                   "Бренды: кто вырос, кто просел", "Бренды: что выросло и что просело",
                   "по брендам")
        if b:
            out.append(b)

        def cat_block():
            c1, c0 = fetch(day, day, "category", []), fetch(week, week, "category", [])
            if c1.empty or c0.empty:
                return None
            return movers(c1.groupby(c1.columns[0])[NET_RUB].sum(),
                          c0.groupby(c0.columns[0])[NET_RUB].sum(),
                          "Категории: кто вырос, кто просел",
                          "Категории: что выросло и что просело", "по категориям товара")
        b = _safe("категории", cat_block)
        if b:
            out.append(b)

    # ---- 3. остатки: все места вместе, изменение за день и за неделю
    def stock_block():
        from .stocks import series
        ser = series(day, 14)
        if not ser:
            return None
        by = {r["date"]: r for r in ser}
        st = ser[-1]
        st_d, st_w = by.get(st["date"] - timedelta(days=1)), by.get(st["date"] - timedelta(days=7))
        places = (("на нашем складе FBS", "fbs"), ("на складах WB", "wb"),
                  ("едет к покупателям", "to_client"), ("возвращается от покупателей", "from_client"))
        word = lambda v: f"на {_n(abs(v))} шт {'больше' if v > 0 else 'меньше'}"
        head = f"Всего у нас <b>{_n(st['total'])} шт</b> товара"
        if st_w and st_w["total"] and st["total"] != st_w["total"]:
            dlt = st["total"] - st_w["total"]
            head += f" — {word(dlt)}, чем неделю назад ({pc(dlt / st_w['total'] * 100)})"
        lines = [f"<b>Остатки товаров на {st['date']:%d.%m}</b>", _quote(head + "."),
                 "Где лежит товар: " + ", ".join(
                     f"{name} — <b>{_n(st[k])}</b>" for name, k in places) + "."]
        if st_w:
            name, k = max(places, key=lambda p: abs(st[p[1]] - st_w[p[1]]))
            if st[k] != st_w[k]:
                lines.append(f"За неделю сильнее всего изменилось «{name}»: "
                             f"<b>{_diff(st[k] - st_w[k])} шт</b>.")
        if st_d and st["total"] != st_d["total"]:
            lines.append(f"За вчерашний день общий остаток: <b>{_diff(st['total'] - st_d['total'])} "
                         "шт</b>.")
        lines.append("<i>Считаем все места вместе: склады WB, товар в пути и наш склад FBS.</i>")
        parts = [(n, st[k], (st[k] - st_w[k]) if st_w else None) for n, k in (
            ("Склад FBS", "fbs"), ("Склады WB", "wb"), ("В пути к клиенту", "to_client"),
            ("В пути от клиента", "from_client"))]
        sub = (f"{_diff(st['total'] - st_w['total'])} шт за неделю · " if st_w else "") \
            + "склады WB, в пути, наш склад FBS"
        return {"text": "\n".join(lines), "photo": pic("остатки", lambda: ch.stocks(
            [r["date"] for r in ser], [r["total"] for r in ser], parts,
            f"Остатки товаров на {st['date']:%d.%m} — {_n(st['total'])} шт", sub))}
    b = _safe("остатки", stock_block)
    if b:
        out.append(b)

    # ---- 4. маржинальность с начала месяца — по методике дашборда продаж
    def margin_block(group, title, whose, many):
        from .margin import dashboard_margin
        m = dashboard_margin(m_start, day, group)
        if m is None or m.empty:
            return None
        rev, md1, md = float(m["rev"].sum()), float(m["md1"].sum()), float(m["md2"].sum())
        if not rev:
            return None
        avg = md / rev * 100
        big = m[m["rev"] > 0].sort_values("rev", ascending=False).head(8)
        rows = [(str(r["name"]), float(r["md2"]) / float(r["rev"]) * 100, float(r["md2"]))
                for _, r in big.iterrows()]
        best, worst = max(rows, key=lambda r: r[1]), min(rows, key=lambda r: r[1])
        loss = sorted([r for r in rows if r[2] < 0], key=lambda r: r[1])[:3]

        def reason(r):
            if float(r["cogs"]) >= float(r["rev"]):
                return "цена ниже себестоимости"
            if float(r["md1"]) <= 0:
                return "себестоимость и комиссия съедают всю выручку"
            return "маржи не хватает на расходы WB"
        why = {str(r["name"]): reason(r) for _, r in big.iterrows() if float(r["md2"]) < 0}
        period = (f"За {_long(m_start)}" if m_start == day
                  else f"С {m_start.day} по {_long(day)}")
        lines = [f"<b>{title}</b>",
                 _quote(f"{period} заработали <b>{_rub(md)}</b> — это <b>{pc(avg)}</b> "
                        "от выручки без НДС, после всех расходов WB.")]
        if group == "brand":
            lines.append(f"До расходов WB (логистика, реклама, штрафы) маржа — "
                         f"<b>{pc(md1 / rev * 100)}</b>, {_rub(md1)}.")
        lines.append(f"{UP} Самая высокая маржа {whose} {escape(best[0])} — <b>{pc(best[1])}</b>.")
        if loss:
            lines.append(f"{DOWN} В убыток продаём:")
            lines += [f"• {escape(r[0])} <b>{pc(r[1])}</b> — {why.get(r[0], 'расходы выше выручки')}"
                      for r in loss]
        else:
            lines.append(f"{UP} Убыточных среди крупных {many} нет; ниже всех {escape(worst[0])} "
                         f"— <b>{pc(worst[1])}</b>.")
        return {"text": "\n".join(lines), "photo": pic(title, lambda: ch.margin(
            rows, avg, f"{title} — {pc(avg)}",
            f"{rng(m_start, day)} · маржа после расходов WB, % от выручки без НДС"))}
    for args in (("brand", "Маржинальность с начала месяца", "у", "брендов"),
                 ("category", "Маржинальность по категориям", "в категории", "категорий")):
        b = _safe(args[1], lambda: margin_block(*args))
        if b:
            out.append(b)

    # ---- 5. расходы WB: вчера и 7 дней против предыдущих 7
    w_from = day - timedelta(days=6)
    costs = _safe("расходы WB", lambda: [c for c in wb_costs(day)
                                         if abs(c[1]) >= 1 or abs(c[2]) >= 1]) or []
    lines = []
    if costs:
        tot = [sum(c[i] for c in costs) for i in (1, 2, 3)]
        sales7 = span(w_from, day, RUB)
        mark = f"{UP if tot[1] <= tot[2] else DOWN} " if tot[2] else ""      # рост расходов — красный
        head = f"{mark}За последние 7 дней WB удержал с нас <b>{_rub(tot[1])}</b>"
        if sales7:
            head += f" — это {pc(tot[1] / sales7 * 100)} от продаж"
        if tot[2]:
            head += f" и {_more(tot[1], tot[2])}, чем неделей раньше"
        big = max(costs, key=lambda c: c[2])
        lines += ["<b>Расходы WB</b>", _quote(head + "."),
                  f"Больше всего ушло на «{big[0].lower()}» — <b>{_rub(big[2])}</b>. "
                  f"Вчера WB удержал <b>{_rub(tot[0])}</b>.",
                  _pre([("тыс ₽", "вчера", "7 дней", "изм.")]
                       + [(n, _ths(d), _ths(c), _chg(c, o)) for n, d, c, o in costs]
                       + [("Итого", _ths(tot[0]), _ths(tot[1]), _chg(tot[1], tot[2]))], wide=False),
                  f"<i>7 дней — это {_span_long(w_from, day)}, сравниваем с предыдущими 7 днями. "
                  "С НДС, по дате операции в отчёте WB; комиссия WB сюда не входит.</i>", ""]
    lines.append("<i>Хотите подробнее — напишите мне вопрос: по брендам, артикулам, в Excel.</i>")
    out.append({"text": "\n".join(lines), "photo": None})
    return out


def greet(parts: list[dict], today: date, day: date | None = None) -> list[dict]:
    """Приветствие отдельным первым сообщением утренней рассылки (на кнопке его нет)."""
    if parts:
        extra = {0: " Хорошей недели!", 4: " Пятница!"}.get(today.weekday(), "")
        when = f" — <b>{WD_FULL[day.weekday()]}, {_long(day)}</b>" if day else ""
        parts.insert(0, {"photo": None, "text": (
            f"Доброе утро! ☀️{extra}\nВот как прошёл вчерашний день{when}.")})
    return parts


def build(day: date, loaded: date | None = None) -> str | None:
    """Вся сводка одним текстом, без картинок (для предпросмотра в терминале)."""
    parts = blocks(day, loaded, charts=False)
    return "\n\n".join(b["text"] for b in parts) if parts else None
