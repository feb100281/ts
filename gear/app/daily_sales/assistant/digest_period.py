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
