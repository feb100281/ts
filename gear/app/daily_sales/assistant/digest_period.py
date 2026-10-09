# gear/app/daily_sales/assistant/digest_period.py
"""Итоги недели (по понедельникам) и месяца (1-го числа) для утренней рассылки.

Период сравнивается с предыдущим таким же: неделя — с прошлой неделей, месяц — с прошлым
месяцем. Собирается из базы без обращения к Claude.
"""
from __future__ import annotations

from datetime import date, timedelta
from html import escape

from conns import get_duckdb_conn_with_opt

from .digest import (AFTER, BRAND_MIN, DOWN, MONTHS, NET_QTY, NET_RUB, PAY, QTY, RET, RET_RUB,
                     RUB, UP, WB_COSTS, WD_FULL, _chg, _diff, _long, _mln, _more, _n, _pre,
                     _quote, _rub, _safe, _span_long, _ths)

MONTHS_NOM = ("январь", "февраль", "март", "апрель", "май", "июнь", "июль", "август",
              "сентябрь", "октябрь", "ноябрь", "декабрь")
MONTHS_IN = ("январе", "феврале", "марте", "апреле", "мае", "июне", "июле", "августе",
             "сентябре", "октябре", "ноябре", "декабре")
MONTHS_SHORT = ("янв", "фев", "мар", "апр", "май", "июн", "июл", "авг", "сен", "окт", "ноя", "дек")
MOVERS_MIN = {"week": 3 * BRAND_MIN, "month": 10 * BRAND_MIN}   # порог для брендов, ₽


def period(kind: str, end: date) -> tuple[date, date, date, date]:
    """(начало, конец, начало прошлого, конец прошлого) для недели или месяца по end."""
    if kind == "week":
        b = end + timedelta(days=6 - end.weekday())          # воскресенье
        a = b - timedelta(days=6)
        return a, b, a - timedelta(days=7), a - timedelta(days=1)
    a = end.replace(day=1)
    b = (a + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    pb = a - timedelta(days=1)
    return a, b, pb.replace(day=1), pb


def last_closed(kind: str, loaded: date) -> date:
    """Конец последней полностью загруженной недели или месяца."""
    if kind == "week":
        return loaded - timedelta(days=(loaded.weekday() + 1) % 7)
    nxt = loaded + timedelta(days=1)
    return loaded if nxt.day == 1 else loaded.replace(day=1) - timedelta(days=1)


def kinds_for(today: date) -> list[str]:
    """Что шлём сегодня: 1-го — итоги месяца, в понедельник — недели, иначе — вчерашний день."""
    if today.day == 1:
        return ["month"]                 # в понедельник 1-го неделя целиком внутри месяца
    return ["week"] if today.weekday() == 0 else ["day"]


def _names(kind, a, pa):
    """Подписи периода: (заголовок, «за неделю», «неделей раньше», колонка, колонка прошлого)."""
    if kind == "week":
        return (f"Неделя {a:%d.%m}–{a + timedelta(days=6):%d.%m}", "За неделю", "неделей раньше",
                "неделя", "прошлая")
    return (MONTHS_NOM[a.month - 1].capitalize(), f"За {MONTHS_NOM[a.month - 1]}",
            f"в {MONTHS_IN[pa.month - 1]}", MONTHS_SHORT[a.month - 1],
            MONTHS_SHORT[pa.month - 1])


def wb_costs_range(a, b, pa, pb) -> list[tuple[str, float, float]]:
    """[(статья, за период, за прошлый период)]; расход — положительный, с НДС."""
    cols = ", ".join(
        f"SUM(CASE WHEN {cond} THEN (CASE WHEN oper = 'cr' THEN val ELSE -val END) END) / 100"
        for _, cond in WB_COSTS)
    with get_duckdb_conn_with_opt(with_pg=False) as con:
        rows = dict((r[0], r[1:]) for r in con.execute(
            "SELECT CASE WHEN date_from::DATE >= ?::DATE THEN 'cur' ELSE 'old' END AS k, "
            f"{cols} FROM sales.sales_long WHERE date_from::DATE BETWEEN ? AND ? GROUP BY 1",
            [a, pa, b]).fetchall())
    zero = [0] * len(WB_COSTS)
    c, o = (rows.get(k) or zero for k in ("cur", "old"))
    return [(name, float(c[i] or 0), float(o[i] or 0)) for i, (name, _) in enumerate(WB_COSTS)]


def blocks(kind: str, end: date, loaded: date | None = None, charts: bool = True) -> list[dict]:
    """Итоги недели или месяца по блокам: [{"photo": PNG | None, "text": HTML}]."""
    import pandas as pd
    from ..wb_sales_export import fetch
    from . import digest_charts as ch

    a, b, pa, pb = period(kind, end)
    title, during, before, col, col_old = _names(kind, a, pa)
    df = fetch(pa, b, "day", [])
    if df.empty:
        return []
    dcol = df.columns[0]
    df[dcol] = pd.to_datetime(df[dcol]).dt.date
    days = df.set_index(dcol)
    if b not in days.index or not days.at[b, QTY]:
        return []
    pc = lambda v: f"{v:.1f}".replace(".", ",").replace("-", "−") + "%"

    def tot(x, y, c):
        if c not in days.columns:
            return 0.0
        return float(days.loc[[d for d in days.index if x <= d <= y], c].sum())

    def pic(what, fn):
        return _safe(f"график «{what}»", fn) if charts else None

    n_cur, n_old = (b - a).days + 1, (pb - pa).days + 1
    cur, old = {}, {}
    for c in (QTY, RET, NET_QTY, NET_RUB, RET_RUB, AFTER, PAY):
        cur[c], old[c] = tot(a, b, c), tot(pa, pb, c)
    word = "за неделю" if kind == "week" else f"за {MONTHS_NOM[a.month - 1]}"
    out = []

    # ---- 1. продажи
    v, vo = cur[NET_RUB], old[NET_RUB]
    lines = [f"<b>Продажи {word} · {a:%d.%m}–{b:%d.%m}</b>",
             _quote((f"{UP if v >= vo else DOWN} " if vo else "")
                    + f"{during} продали на <b>{_rub(v)}</b> — это <b>{_n(cur[NET_QTY])} шт</b> "
                    "за вычетом возвратов.")]
    if vo:
        lines.append(f"Это {_more(v, vo)}, чем {before} ({_rub(vo)}).")
    if kind == "month":
        avg, avg_o = v / n_cur, vo / n_old if n_old else 0
        s = f"В среднем за день — <b>{_rub(avg)}</b>"
        if avg_o:
            s += f", {before} было {_rub(avg_o)} ({_chg(avg, avg_o)})"
        lines.append(s + ".")
        if n_cur != n_old:
            lines.append(f"<i>В {MONTHS_IN[a.month - 1]} {n_cur} дн., {before} — {n_old}: "
                         "честнее сравнивать средние за день.</i>")
    inside = [d for d in days.index if a <= d <= b]
    if len(inside) > 1:
        best = max(inside, key=lambda d: float(days.at[d, NET_RUB]))
        worst = min(inside, key=lambda d: float(days.at[d, NET_RUB]))
        when = lambda d: f"{WD_FULL[d.weekday()]}, {_long(d)}"
        lines.append(f"Лучший день — {when(best)}: <b>{_rub(days.at[best, NET_RUB])}</b>; "
                     f"слабее всего — {when(worst)}: {_rub(days.at[worst, NET_RUB])}.")
    chk = lambda d: d[NET_RUB] / d[NET_QTY] if d[NET_QTY] else 0
    rows = [("", col, col_old, "изм."),
            ("Продажи, млн", _mln(v), _mln(vo), _chg(v, vo)),
            ("Штук", _n(cur[NET_QTY]), _n(old[NET_QTY]), _chg(cur[NET_QTY], old[NET_QTY])),
            ("Возвраты", _n(cur[RET]), _n(old[RET]), _chg(cur[RET], old[RET])),
            ("Ср. чек, ₽", _n(chk(cur)), _n(chk(old)), _chg(chk(cur), chk(old)))]
    if PAY in days.columns:
        rows.append(("Выплата, млн", _mln(cur[PAY]), _mln(old[PAY]), _chg(cur[PAY], old[PAY])))
    lines.append(_pre(rows, wide=False))
    if cur[QTY]:
        lines.append(f"Покупатели вернули <b>{_n(cur[RET])} шт</b>"
                     + (f" на {_rub(abs(cur[RET_RUB]))}" if cur[RET_RUB] else "")
                     + f" — {pc(cur[RET] / cur[QTY] * 100)} от проданного"
                     + (f" ({before} — {pc(old[RET] / old[QTY] * 100)})" if old[QTY] else "")
                     + ".")
    if cur[AFTER] and v:
        lines.append(f"Скидка WB (СПП) в среднем — <b>{pc((1 - cur[AFTER] / v) * 100)}</b>"
                     + (f", {before} — {pc((1 - old[AFTER] / vo) * 100)}" if old[AFTER] and vo
                        else "") + ".")
    lines.append(f"<i>Как на сайте WB, с НДС, до СПП. Данные в базе по "
                 f"{(loaded or b):%d.%m}.</i>")
    if kind == "week":
        ds = [pa + timedelta(days=i) for i in range(14)]
        sub = (f"{_chg(v, vo)} к прошлой неделе · " if vo else "") + "по дням, млн ₽"
        photo = pic("продажи", lambda: ch.sales_period(
            ds, [float(days.at[d, NET_RUB]) / 1e6 if d in days.index else 0.0 for d in ds], 7,
            None, f"{title} — {_rub(v)}", sub))
    else:
        ds = [a + timedelta(days=i) for i in range(n_cur)]
        ref = vo / n_old / 1e6 if vo and n_old else None
        sub = (f"{_chg(v, vo)} к прошлому месяцу · " if vo else "") + "по дням, млн ₽"
        photo = pic("продажи", lambda: ch.sales_period(
            ds, [float(days.at[d, NET_RUB]) / 1e6 if d in days.index else 0.0 for d in ds],
            n_cur, ref, f"{title} — {_rub(v)}", sub))
    out.append({"text": "\n".join(lines), "photo": photo})

    # ---- 1б. динамика: 5 недель или месяцы с начала года
    blk = _safe("динамика", lambda: trend_block(kind, a, b, charts))
    if blk:
        out.append(blk)

    # ---- 2. бренды и категории
    lim = MOVERS_MIN[kind]

    def movers(level, head, what):
        c1, c0 = fetch(a, b, level, []), fetch(pa, pb, level, [])
        if c1.empty:
            return None
        s1 = c1.groupby(c1.columns[0])[NET_RUB].sum()
        s0 = c0.groupby(c0.columns[0])[NET_RUB].sum() if not c0.empty else s1 * 0
        diff = s1.sub(s0, fill_value=0).sort_values()
        up, down = diff[diff >= lim].tail(3)[::-1], diff[diff <= -lim].head(3)
        if not (len(up) or len(down)):
            return None
        top = max(list(up.items()) + list(down.items()), key=lambda x: abs(x[1]))
        lines = [f"<b>{head}</b>", _quote(
            f"{UP if top[1] > 0 else DOWN} Сильнее всего {'выросли' if top[1] > 0 else 'просели'} "
            f"продажи {'в категории ' if level == 'category' else ''}"
            f"<b>{escape(str(top[0]))}</b>: {'+' if top[1] > 0 else '−'}{_rub(abs(top[1]))} "
            f"к {'прошлой неделе' if kind == 'week' else 'прошлому месяцу'}.")]
        if len(up):
            lines.append(f"{UP} Выросли: " + ", ".join(
                f"{escape(str(k))} (<b>+{_rub(x)}</b>)" for k, x in up.items()) + ".")
        if len(down):
            lines.append(f"{DOWN} Просели: " + ", ".join(
                f"{escape(str(k))} (<b>−{_rub(abs(x))}</b>)" for k, x in down.items()) + ".")
        lines.append(f"<i>Сравниваем {_span_long(a, b)} с {_span_long(pa, pb)}, {what}, "
                     "продажи за вычетом возвратов.</i>")
        rows = [(str(k), float(x)) for k, x in list(up.items()) + list(down.items())]
        return {"text": "\n".join(lines), "photo": pic(head, lambda: ch.brands(
            rows, head.replace("кто вырос, кто просел", "что выросло и что просело"),
            f"{title} к {'прошлой неделе' if kind == 'week' else MONTHS_NOM[pa.month - 1]}"
            " · изменение продаж"))}

    for args in (("brand", "Бренды: кто вырос, кто просел", "по брендам"),
                 ("category", "Категории: кто вырос, кто просел", "по категориям товара")):
        blk = _safe(args[1], lambda: movers(*args))
        if blk:
            out.append(blk)

    # ---- 3. остатки: конец периода против конца прошлого
    def stock_block():
        from .stocks import series
        ser = series(b, 14 if kind == "week" else (b - pb).days + 1)
        if not ser:
            return None
        by = {r["date"]: r for r in ser}
        st, st_o = ser[-1], by.get(pb)
        places = (("на нашем складе FBS", "fbs"), ("на складах WB", "wb"),
                  ("едет к покупателям", "to_client"), ("возвращается от покупателей", "from_client"))
        head = f"На {_long(st['date'])} у нас <b>{_n(st['total'])} шт</b> товара"
        if st_o and st_o["total"] and st["total"] != st_o["total"]:
            dlt = st["total"] - st_o["total"]
            head += (f" — на {_n(abs(dlt))} шт {'больше' if dlt > 0 else 'меньше'}, чем "
                     f"{_long(pb)} ({pc(dlt / st_o['total'] * 100)})")
        lines = [f"<b>Остатки товаров на {st['date']:%d.%m}</b>", _quote(head + "."),
                 "Где лежит товар: " + ", ".join(
                     f"{name} — <b>{_n(st[k])}</b>" for name, k in places) + "."]
        if st_o:
            name, k = max(places, key=lambda p: abs(st[p[1]] - st_o[p[1]]))
            if st[k] != st_o[k]:
                lines.append(f"{during} сильнее всего изменилось «{name}»: "
                             f"<b>{_diff(st[k] - st_o[k])} шт</b>.")
        if cur[NET_QTY] > 0 and st["total"]:
            per_day = cur[NET_QTY] / n_cur
            lines.append(f"При продажах около {_n(per_day)} шт в день остатков хватит примерно на "
                         f"<b>{_n(st['total'] / per_day)} дн.</b>")
        lines.append("<i>Считаем все места вместе: склады WB, товар в пути и наш склад FBS.</i>")
        parts = [(n, st[k], (st[k] - st_o[k]) if st_o else None) for n, k in (
            ("Склад FBS", "fbs"), ("Склады WB", "wb"), ("В пути к клиенту", "to_client"),
            ("В пути от клиента", "from_client"))]
        ref = next((i for i, r in enumerate(ser) if r["date"] == pb), None)
        span_word = "неделю" if kind == "week" else "месяц"
        sub = (f"{_diff(st['total'] - st_o['total'])} шт за {span_word} · " if st_o else "") \
            + "склады WB, в пути, наш склад FBS"
        return {"text": "\n".join(lines), "photo": pic("остатки", lambda: ch.stocks(
            [r["date"] for r in ser], [r["total"] for r in ser], parts,
            f"Остатки товаров на {st['date']:%d.%m} — {_n(st['total'])} шт", sub,
            ref=ref, note=f"за {span_word}"))}
    blk = _safe("остатки", stock_block)
    if blk:
        out.append(blk)

    # ---- 4. маржинальность за период — по методике дашборда продаж
    def margin_block(group, head, whose, many):
        from .margin import dashboard_margin
        m = dashboard_margin(a, b, group)
        if m is None or m.empty:
            return None
        rev, md1, md = float(m["rev"].sum()), float(m["md1"].sum()), float(m["md2"].sum())
        if not rev:
            return None
        avg = md / rev * 100
        mo = dashboard_margin(pa, pb, group)
        avg_o = (float(mo["md2"].sum()) / float(mo["rev"].sum()) * 100
                 if mo is not None and not mo.empty and float(mo["rev"].sum()) else None)
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
        q = (f"{during} заработали <b>{_rub(md)}</b> — это <b>{pc(avg)}</b> от выручки без НДС, "
             "после всех расходов WB.")
        if avg_o is not None:
            dp = avg - avg_o
            q = (f"{UP if dp >= 0 else DOWN} " + q + f" {before.capitalize()} — {pc(avg_o)}"
                 + (f" ({'+' if dp >= 0 else '−'}" + f"{abs(dp):.1f}".replace(".", ",")
                    + " п.п.)" if abs(dp) >= 0.05 else "") + ".")
        lines = [f"<b>{head}</b>", _quote(q)]
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
        rng = f"{a:%d.%m}–{b:%d.%m}"
        return {"text": "\n".join(lines), "photo": pic(head, lambda: ch.margin(
            rows, avg, f"{head} — {pc(avg)}",
            f"{rng} · маржа после расходов WB, % от выручки без НДС"))}
    for args in (("brand", f"Маржинальность {word}", "у", "брендов"),
                 ("category", "Маржинальность по категориям", "в категории", "категорий")):
        blk = _safe(args[1], lambda: margin_block(*args))
        if blk:
            out.append(blk)

    # ---- 5. расходы WB за период против прошлого
    costs = _safe("расходы WB", lambda: [c for c in wb_costs_range(a, b, pa, pb)
                                         if abs(c[1]) >= 1 or abs(c[2]) >= 1]) or []
    lines = []
    if costs:
        t1, t0 = sum(c[1] for c in costs), sum(c[2] for c in costs)
        sales = tot(a, b, RUB)
        mark = f"{UP if t1 <= t0 else DOWN} " if t0 else ""
        h = f"{mark}{during} WB удержал с нас <b>{_rub(t1)}</b>"
        if sales:
            h += f" — это {pc(t1 / sales * 100)} от продаж"
        if t0:
            h += f" и {_more(t1, t0)}, чем {before}"
        big = max(costs, key=lambda c: c[1])
        grew = max(costs, key=lambda c: c[1] - c[2])
        lines += ["<b>Расходы WB</b>", _quote(h + "."),
                  f"Больше всего ушло на «{big[0].lower()}» — <b>{_rub(big[1])}</b>."]
        if t0 and grew[1] - grew[2] >= 1000 and grew is not big:
            lines.append(f"Сильнее всего выросла статья «{grew[0].lower()}»: "
                         f"+{_rub(grew[1] - grew[2])}.")
        lines += [_pre([("тыс ₽", col, col_old, "изм.")]
                       + [(n, _ths(c), _ths(o), _chg(c, o)) for n, c, o in costs]
                       + [("Итого", _ths(t1), _ths(t0), _chg(t1, t0))], wide=False),
                  "<i>С НДС, по дате операции в отчёте WB; комиссия WB сюда не входит.</i>", ""]
    lines.append("<i>Хотите подробнее — напишите мне вопрос: по брендам, артикулам, в Excel.</i>")
    out.append({"text": "\n".join(lines), "photo": None})
    return out


TREND_WEEKS = 5
TREND_MONTHS_MIN = 6           # в начале года берём хотя бы полгода назад


def trend_periods(kind: str, a: date, b: date) -> list[tuple[date, date, str]]:
    """[(начало, конец, подпись)] от старого к текущему периоду."""
    if kind == "week":
        out = []
        for i in range(TREND_WEEKS - 1, -1, -1):
            x, y = a - timedelta(days=7 * i), b - timedelta(days=7 * i)
            out.append((x, y, f"{x:%d}–{y:%d.%m}" if x.month == y.month
                        else f"{x:%d.%m}–{y:%d.%m}"))
        return out
    out, x = [], a                       # с января, но не меньше TREND_MONTHS_MIN месяцев
    while x.year == a.year or len(out) < TREND_MONTHS_MIN:
        e = (x + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        out.insert(0, (x, e, MONTHS_SHORT[x.month - 1]))
        x = (x - timedelta(days=1)).replace(day=1)
    return out


def trend_block(kind: str, a: date, b: date, charts: bool = True) -> dict | None:
    """Динамика за несколько периодов: выручка, штуки, чек, маржа, возвраты и выводы."""
    import pandas as pd
    from ..wb_sales_export import fetch
    from . import digest_charts as ch
    from .margin import dashboard_margin

    per = trend_periods(kind, a, b)
    df = fetch(per[0][0], b, "day", [])
    if df.empty:
        return None
    dcol = df.columns[0]
    df[dcol] = pd.to_datetime(df[dcol]).dt.date
    pc = lambda v: f"{v:.1f}".replace(".", ",").replace("-", "−") + "%"

    rows = []
    for x, y, lab in per:
        d = df[(df[dcol] >= x) & (df[dcol] <= y)]
        rev, qty = float(d[NET_RUB].sum()), float(d[NET_QTY].sum())
        sold, ret = float(d[QTY].sum()), float(d[RET].sum())

        def mg(x=x, y=y):
            m = dashboard_margin(x, y, "brand")
            r = float(m["rev"].sum()) if m is not None and not m.empty else 0
            return float(m["md2"].sum()) / r * 100 if r else None
        n = (y - x).days + 1
        rows.append({"lab": lab, "rev": rev, "qty": qty, "n": n, "per_day": rev / n,
                     "check": rev / qty if qty else 0, "ret": ret / sold * 100 if sold else None,
                     "margin": _safe(f"маржа {lab}", mg)})
    rows = [r for r in rows if r["rev"]]
    if len(rows) < 3:
        return None
    cur, prev, old = rows[-1], rows[-2], rows[:-1]
    key = "rev" if kind == "week" else "per_day"           # месяцы сравниваем по среднему дню
    avg = sum(r[key] for r in old) / len(old)
    nm = f"{len(rows)} недель" if kind == "week" else f"{len(rows)} мес."

    # ---- выводы
    vs = (cur[key] - avg) / avg * 100 if avg else 0
    if cur[key] >= max(r[key] for r in rows):
        head = (f"{UP} Лучшая неделя за {nm}" if kind == "week" else f"{UP} Лучший месяц за {nm}")
    elif cur[key] <= min(r[key] for r in rows):
        head = (f"{DOWN} Самая слабая неделя за {nm}" if kind == "week"
                else f"{DOWN} Самый слабый месяц за {nm}")
    elif abs(vs) < 2:
        head = ("Неделя" if kind == "week" else "Месяц") + " на уровне среднего"
    else:
        head = f"{UP if vs >= 0 else DOWN} " + (
            "Неделя" if kind == "week" else "Месяц") + f" {'выше' if vs >= 0 else 'ниже'} среднего"
    what = "продажи" if kind == "week" else "продажи в среднем за день"
    head += (f": {what} {_rub(cur[key])} при среднем {_rub(avg)} за предыдущие "
             f"{len(old)} ({'+' if vs >= 0 else '−'}{pc(abs(vs))}).")
    lines = [f"<b>Динамика: {'последние ' + nm if kind == 'week' else 'по месяцам'}</b>",
             _quote(head)]

    k = 0                                                   # серия роста или падения
    sign = 1 if cur[key] > prev[key] else -1
    for i in range(len(rows) - 1, 0, -1):
        if (rows[i][key] - rows[i - 1][key]) * sign > 0:
            k += 1
        else:
            break
    if k >= 2:
        lines.append(f"{UP if sign > 0 else DOWN} Продажи {'растут' if sign > 0 else 'снижаются'} "
                     f"{k}-{'ю неделю' if kind == 'week' else 'й месяц'} подряд.")

    if prev["qty"] and prev["check"]:
        dq = ((cur["qty"] / cur["n"]) / (prev["qty"] / prev["n"]) - 1) * 100
        dc = (cur["check"] / prev["check"] - 1) * 100
        if abs(dq) >= 1 or abs(dc) >= 1:
            main = "количества проданного" if abs(dq) >= abs(dc) else "среднего чека"
            lines.append(f"К {'прошлой неделе' if kind == 'week' else 'прошлому месяцу'} изменение "
                         f"в основном за счёт {main}: штук в день {_chg(100 + dq, 100)}, "
                         f"средний чек {_chg(100 + dc, 100)}.")

    ms = [r["margin"] for r in rows if r["margin"] is not None]
    m_cur, m_avg = cur["margin"], None
    if m_cur is not None and len(ms) >= 3:
        m_old = [r["margin"] for r in old if r["margin"] is not None]
        m_avg = sum(m_old) / len(m_old)
        dm = m_cur - m_avg
        lines.append(f"Маржа после расходов WB — <b>{pc(m_cur)}</b>, в среднем за прошлые "
                     f"{'недели' if kind == 'week' else 'месяцы'} {pc(m_avg)} ({'+' if dm >= 0 else '−'}"
                     + f"{abs(dm):.1f}".replace(".", ",") + " п.п.).")
    rets = [r["ret"] for r in rows if r["ret"] is not None]
    if cur["ret"] is not None and len(rets) >= 3:
        if cur["ret"] >= max(rets) and cur["ret"] > min(rets):
            lines.append(f"{DOWN} Доля возвратов — самая высокая за {nm}: {pc(cur['ret'])}.")
        elif cur["ret"] <= min(rets) and cur["ret"] < max(rets):
            lines.append(f"{UP} Доля возвратов — самая низкая за {nm}: {pc(cur['ret'])}.")

    if m_avg is not None:
        lvl = lambda v, eps: 1 if v >= eps else -1 if v <= -eps else 0
        ls, lm = lvl(vs, 2), lvl(m_cur - m_avg, 0.5)
        word = {1: "выше обычного", 0: "на обычном уровне", -1: "ниже обычного"}
        hint = ("стоит проверить скидки и расходы WB (блоки ниже)." if lm < 0 else
                "стоит посмотреть, какие бренды и категории просели (ниже)." if ls < 0 else
                "хороший период." if ls > 0 and lm > 0 else "")
        lines.append(f"<b>Вывод:</b> продажи {word[ls]}, маржа {word[lm]}"
                     + (f" — {hint}" if hint else "."))

    t = [("", "млн ₽", "шт", "чек", "маржа")] + [
        (r["lab"], _mln(r["rev"]), _n(r["qty"]), _n(r["check"]),
         pc(r["margin"]) if r["margin"] is not None else "—") for r in rows]
    lines.append(_pre(t, wide=False))
    if kind == "month":
        ytd = [r for r, p in zip(rows, per[-len(rows):]) if p[0].year == b.year]
        if len(ytd) > 1:
            lines.append(f"С начала года продали на <b>{_rub(sum(r['rev'] for r in ytd))}</b>.")
        lines.append("<i>Месяцы разной длины, поэтому сравниваем средние продажи за день.</i>")
    lines.append("<i>Продажи как на сайте WB, с НДС, до СПП; маржа — по методике дашборда.</i>")
    return {"text": "\n".join(lines), "photo": _safe("график «динамика»", lambda: ch.trend(
        [r["lab"] for r in rows], [r["rev"] / 1e6 for r in rows], [r["margin"] for r in rows],
        f"Динамика продаж: {nm}",
        "млн ₽ по " + ("неделям" if kind == "week" else "месяцам") + " · под столбиком — маржа"))
        if charts else None}


def morning(today: date, day: date, loaded: date | None, kinds: list[str] | None = None,
            charts: bool = True) -> list[dict]:
    """Вся утренняя рассылка с приветствием; пусто — данных за day ещё нет."""
    from . import digest
    kinds = kinds or kinds_for(today)
    if not loaded or loaded < day:
        return []
    parts, what = [], []
    for k in kinds:
        if k == "day":
            got = digest.blocks(day, loaded, charts)
            if got:
                return digest.greet(got, today, day)
            continue
        end = day if k == "month" and (day + timedelta(days=1)).day == 1 else last_closed(k, day)
        got = blocks(k, end, loaded, charts)
        if got:
            a, b, *_ = period(k, end)
            what.append(f"прошлой недели — <b>{_span_long(a, b)}</b>" if k == "week"
                        else f"<b>{MONTHS[a.month - 1]}</b>")
            parts += got
    if parts:
        extra = {0: " Хорошей недели!", 4: " Пятница!"}.get(today.weekday(), "")
        parts.insert(0, {"photo": None, "text": (
            f"Доброе утро! ☀️{extra}\nВот итоги " + " и ".join(what) + ".")})
    return parts


def build(kind: str, end: date, loaded: date | None = None) -> str | None:
    """Итоги одним текстом, без картинок (для предпросмотра в терминале)."""
    parts = blocks(kind, end, loaded, charts=False)
    return "\n\n".join(b["text"] for b in parts) if parts else None
