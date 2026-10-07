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


def _pre(rows) -> str:
    """Таблица моноширинным блоком: первая колонка влево, числа вправо, стрелки — в столбик."""
    def split(c):
        c = str(c)
        return (c[0], c[2:]) if c[:2] in ("▲ ", "▼ ") else ("", c)
    cells = [[split(c) for c in r] for r in rows]
    n = len(rows[0])
    arrow = [any(r[i][0] for r in cells) for i in range(n)]
    w = [max(len(r[i][1]) for r in cells) for i in range(n)]
    out = []
    for r in cells:
        line = []
        for i, (a, v) in enumerate(r):
            if i == 0:
                line.append(v.ljust(w[i]))
            else:
                line.append((a or " " if arrow[i] else "") + v.rjust(w[i]))
        out.append(" ".join(line).rstrip())
    return "<pre>" + escape("\n".join(out)) + "</pre>"


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

    # ---- 1. продажи
    table = [("", "млн ₽", "шт", "изм."),
             ("Вчера", _mln(t[NET_RUB]), _n(t[NET_QTY]), _chg(t[NET_RUB], week_val)),
             ("Неделя", _mln(span(mon, day, NET_RUB)), _n(span(mon, day, NET_QTY)),
              _chg(span(mon, day, NET_RUB), span(*w_prev, NET_RUB))),
             ("Месяц", _mln(span(m_start, day, NET_RUB)), _n(span(m_start, day, NET_QTY)),
              _chg(span(m_start, day, NET_RUB), span(pm_start, pm_to, NET_RUB)))]
    head = f"<b>{_rub(t[NET_RUB])}</b> · {_n(t[NET_QTY])} шт"
    if week_val:
        head += f" — <b>{_chg(t[NET_RUB], week_val)}</b> к прошл. {wd_w}"
    lines = [f"<b>Продажи · {wd} {day:%d.%m.%Y}</b>", _quote(head), _pre(table),
             f"<i>Вчера — к {wd_w} {week:%d.%m} · Неделя {rng(mon, day)} — к {rng(*w_prev)} · "
             f"Месяц {rng(m_start, day)} — к {rng(pm_start, pm_to)}</i>", ""]
    if prev in days.index:
        lines.append(f"К {WD[prev.weekday()]} {prev:%d.%m}: <b>{_chg(t[NET_RUB], days.at[prev, NET_RUB])}</b>")
    ret_rub = f" · −{_rub(abs(t[RET_RUB]))}" if RET_RUB in days.columns else ""
    ret_pct = (f" ({float(t[RET]) / float(t[QTY]) * 100:.1f}".replace(".", ",") + "%)"
               if t[QTY] else "")
    lines += [f"Продано: <b>{_n(t[QTY])} шт</b> · {_rub(t[RUB])}",
              f"Возвраты: −{_n(t[RET])} шт{ret_rub}{ret_pct}"]
    if t[NET_QTY] > 0:
        check = f"Средний чек: <b>{_n(t[NET_RUB] / t[NET_QTY])} ₽</b> до СПП"
        if AFTER in days.columns:
            spp = (1 - float(t[AFTER]) / float(t[NET_RUB])) * 100 if t[NET_RUB] else 0
            check += (f" · <b>{_n(t[AFTER] / t[NET_QTY])} ₽</b> после "
                      f"(скидка WB {spp:.1f}".replace(".", ",") + "%)")
        lines.append(check)
    if PAY in days.columns:
        lines.append(f"К перечислению от WB: <b>{_rub(t[PAY])}</b>")
    lines += ["", f"<i>Как на сайте WB, с НДС, до СПП, продажи минус возвраты. "
                  f"Данные в базе по {(loaded or day):%d.%m}.</i>"]
    d14 = [day - timedelta(days=13 - i) for i in range(14)]
    v14 = [float(days.at[d, NET_RUB]) / 1e6 if d in days.index else 0.0 for d in d14]
    sub = (f"{_chg(t[NET_RUB], week_val)} к {wd_w} {week:%d.%m} · " if week_val else "") \
        + "14 дней, млн ₽"
    out.append({"text": "\n".join(lines), "photo": pic("продажи", lambda: ch.sales_days(
        d14, v14, f"Продажи за {day:%d.%m} — {_rub(t[NET_RUB])}", sub))})

    # ---- 2. бренды: заметные изменения к тому же дню прошлой недели
    if week in days.index:
        cur = df[df[dcol] == day].groupby(bcol)[NET_RUB].sum()
        old = df[df[dcol] == week].groupby(bcol)[NET_RUB].sum()
        diff = cur.sub(old, fill_value=0).sort_values()
        up, down = diff[diff >= BRAND_MIN].tail(3)[::-1], diff[diff <= -BRAND_MIN].head(3)
        if len(up) or len(down):
            lines = [f"<b>Бренды за день</b> · к {wd_w} {week:%d.%m}"]
            top = max(list(up.items()) + list(down.items()), key=lambda x: abs(x[1]))
            lines.append(_quote(
                f"Сильнее всех {'вырос' if top[1] > 0 else 'просел'} "
                f"<b>{escape(str(top[0]))}</b>: {'+' if top[1] > 0 else '−'}{_rub(abs(top[1]))}"))
            lines += [f"▲ {escape(str(b))} <b>+{_rub(v)}</b>" for b, v in up.items()]
            lines += [f"▼ {escape(str(b))} <b>−{_rub(abs(v))}</b>" for b, v in down.items()]
            rows = [(str(b), float(v)) for b, v in list(up.items()) + list(down.items())]
            out.append({"text": "\n".join(lines), "photo": pic("бренды", lambda: ch.brands(
                rows, "Бренды: что выросло и что просело",
                f"{day:%d.%m} к {wd_w} {week:%d.%m} · изменение продаж"))})

    # ---- 3. остатки: все места вместе, изменение за день и за неделю
    def stock_block():
        from .stocks import series
        ser = series(day, 14)
        if not ser:
            return None
        by = {r["date"]: r for r in ser}
        st = ser[-1]
        st_d, st_w = by.get(st["date"] - timedelta(days=1)), by.get(st["date"] - timedelta(days=7))
        places = (("Склады WB", "wb"), ("К клиенту", "to_client"),
                  ("От клиента", "from_client"), ("Склад FBS", "fbs"), ("Итого", "total"))
        lines = [f"<b>Остатки на {st['date']:%d.%m}: {_n(st['total'])} шт</b>"]
        if st_w and st_w["total"]:
            dlt = st["total"] - st_w["total"]
            lines.append(_quote(f"За неделю <b>{_diff(dlt)} шт</b> "
                                f"({_chg(st['total'], st_w['total'])})"))
        lines.append(_pre([("", "шт", "день", "неделя")] + [
            (name, _n(st[k]), _diff(st[k] - st_d[k]) if st_d else "—",
             _diff(st[k] - st_w[k]) if st_w else "—") for name, k in places]))
        lines.append("<i>Все места: склады WB, в пути к клиенту и от клиента, наш склад FBS.</i>")
        parts = [(n, st[k], (st[k] - st_w[k]) if st_w else None) for n, k in (
            ("Склад FBS", "fbs"), ("Склады WB", "wb"), ("В пути к клиенту", "to_client"),
            ("В пути от клиента", "from_client"))]
        sub = (f"{_diff(st['total'] - st_w['total'])} шт за неделю · " if st_w else "") \
            + "склады WB, в пути, наш склад FBS"
        return {"text": "\n".join(lines), "photo": pic("остатки", lambda: ch.stocks(
            [r["date"] for r in ser], [r["total"] for r in ser], parts,
            f"Остатки на {st['date']:%d.%m} — {_n(st['total'])} шт", sub))}
    b = _safe("остатки", stock_block)
    if b:
        out.append(b)

    # ---- 4. маржинальность с начала месяца по брендам
    def margin_block():
        from .margin import margin_table
        m, start, end, _ = margin_table(m_start.isoformat(), day.isoformat(), "brand")
        if m is None or m.empty:
            return None
        rev_c, md_c = "Выручка без НДС, ₽", "МД2 после расходов WB, ₽"
        m = m[m["Бренд"].notna() & ~m["Бренд"].astype(str).str.startswith("Итого")]
        rev, md = float(m[rev_c].sum()), float(m[md_c].sum())
        if not rev:
            return None
        avg = md / rev * 100
        big = m[m[rev_c] > 0].sort_values(rev_c, ascending=False).head(8)
        rows = [(str(r["Бренд"]), float(r[md_c]) / float(r[rev_c]) * 100, float(r[md_c]))
                for _, r in big.iterrows()]
        best, worst = max(rows, key=lambda r: r[1]), min(rows, key=lambda r: r[1])
        loss = [r for r in rows if r[2] < 0]
        pc = lambda v: f"{v:.1f}".replace(".", ",").replace("-", "−") + "%"
        lines = [f"<b>Маржинальность с начала месяца: {pc(avg)}</b>",
                 _quote(f"Маржинальный доход <b>{_rub(md)}</b> при выручке {_rub(rev)} без НДС"),
                 f"▲ Лучше всех: {escape(best[0])} <b>{pc(best[1])}</b>"]
        if loss:
            lines.append("▼ В убытке: " + "; ".join(
                f"{escape(r[0])} <b>{pc(r[1])}</b>" for r in sorted(loss, key=lambda r: r[1])[:3]))
        else:
            lines.append(f"▼ Ниже всех: {escape(worst[0])} <b>{pc(worst[1])}</b>")
        lines.append(f"<i>{rng(start, end)} · управленческая маржа: выручка без НДС минус "
                     "себестоимость, комиссия и расходы WB. Показаны 8 крупнейших брендов.</i>")
        return {"text": "\n".join(lines), "photo": pic("маржа", lambda: ch.margin(
            rows, avg, f"Маржинальность с начала месяца — {pc(avg)}",
            f"{rng(start, end)} · маржа, % от выручки без НДС, и маржинальный доход"))}
    b = _safe("маржа", margin_block)
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
        share = (f"{tot[1] / sales7 * 100:.1f}".replace(".", ",") + "% от продаж"
                 if sales7 else "")
        lines += ["<b>Расходы WB</b> · тыс ₽, с НДС",
                  _quote(f"За 7 дней <b>{_rub(tot[1])}</b>"
                         + (f" — {share}" if share else "")
                         + f" · {_chg(tot[1], tot[2])} к предыдущим 7"),
                  _pre([("", "вчера", "7 дней", "изм.")]
                       + [(n, _ths(d), _ths(c), _chg(c, o)) for n, d, c, o in costs]
                       + [("Итого", _ths(tot[0]), _ths(tot[1]), _chg(tot[1], tot[2]))]),
                  f"<i>7 дней: {rng(w_from, day)}. По дате операции в отчёте WB; "
                  "комиссия WB не входит.</i>", ""]
    lines.append("<i>Подробности — спросите меня: по брендам, артикулам, в Excel.</i>")
    out.append({"text": "\n".join(lines), "photo": None})
    return out


def greet(parts: list[dict], today: date) -> list[dict]:
    """Приветствие в начале утренней рассылки (в ответе на кнопку его нет)."""
    if parts:
        extra = {0: " Хорошей недели!", 4: " Пятница!"}.get(today.weekday(), "")
        parts[0]["text"] = (f"Доброе утро, коллеги! ☀️{extra}\nВот как прошёл вчерашний день.\n\n"
                            + parts[0]["text"])
    return parts


def build(day: date, loaded: date | None = None) -> str | None:
    """Вся сводка одним текстом, без картинок (для предпросмотра в терминале)."""
    parts = blocks(day, loaded, charts=False)
    return "\n\n".join(b["text"] for b in parts) if parts else None
