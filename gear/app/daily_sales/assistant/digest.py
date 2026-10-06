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
    """Таблица моноширинным блоком: первая колонка влево, остальные вправо."""
    w = [max(len(str(r[i])) for r in rows) for i in range(len(rows[0]))]
    return "<pre>" + escape("\n".join(
        " ".join(str(c).ljust(w[i]) if i == 0 else str(c).rjust(w[i])
                 for i, c in enumerate(r)).rstrip() for r in rows)) + "</pre>"


def build(day: date, loaded: date | None = None) -> str | None:
    """Текст сводки (HTML для Telegram) или None, если за день продаж нет."""
    import pandas as pd
    from ..wb_sales_export import fetch

    prev, week = day - timedelta(days=1), day - timedelta(days=7)
    mon = day - timedelta(days=day.weekday())               # неделя нарастающим итогом
    m_start = day.replace(day=1)                            # месяц с начала
    pm_end = m_start - timedelta(days=1)
    pm_start = pm_end.replace(day=1)
    pm_to = min(pm_start + (day - m_start), pm_end)         # столько же дней прошлого месяца

    df = fetch(min(pm_start, day - timedelta(days=13)), day, "brand_day", [])
    if df.empty:
        return None
    dcol, bcol = df.columns[0], df.columns[1]
    df[dcol] = pd.to_datetime(df[dcol]).dt.date
    num = [c for c in (QTY, RET, NET_QTY, RUB, NET_RUB, PAY, AFTER, RET_RUB) if c in df.columns]
    days = df.groupby(dcol)[num].sum()
    if day not in days.index or not days.at[day, QTY]:
        return None
    t = days.loc[day]

    def span(a, b, col):
        return float(days.loc[[d for d in days.index if a <= d <= b], col].sum())

    def rng(a, b):
        if a == b:
            return f"{a:%d.%m}"
        return f"{a:%d}–{b:%d.%m}" if a.month == b.month else f"{a:%d.%m}–{b:%d.%m}"

    w_prev = (mon - timedelta(days=7), week)
    table = [("", "млн ₽", "шт", "изм."),
             ("Вчера", _mln(t[NET_RUB]), _n(t[NET_QTY]),
              _chg(t[NET_RUB], span(week, week, NET_RUB))),
             ("Неделя", _mln(span(mon, day, NET_RUB)), _n(span(mon, day, NET_QTY)),
              _chg(span(mon, day, NET_RUB), span(*w_prev, NET_RUB))),
             ("Месяц", _mln(span(m_start, day, NET_RUB)), _n(span(m_start, day, NET_QTY)),
              _chg(span(m_start, day, NET_RUB), span(pm_start, pm_to, NET_RUB)))]
    lines = [
        f"<b>Продажи · {WD[day.weekday()]} {day:%d.%m.%Y}</b>",
        f"<i>данные в базе по {(loaded or day):%d.%m} · как на сайте WB, с НДС, до СПП, "
        "за вычетом возвратов</i>",
        "", _pre(table),
        f"<i>Вчера — к {WD[week.weekday()]} {week:%d.%m} · Неделя {rng(mon, day)} — к "
        f"{rng(*w_prev)} · Месяц {rng(m_start, day)} — к {rng(pm_start, pm_to)}</i>",
        "", "<b>Вчера подробнее</b>",
    ]
    if prev in days.index:
        lines.append(f"{_chg(t[NET_RUB], days.at[prev, NET_RUB])} к {WD[prev.weekday()]} "
                     f"{prev:%d.%m} ({_rub(days.at[prev, NET_RUB])})")
    ret_rub = f" · −{_rub(abs(t[RET_RUB]))}" if RET_RUB in days.columns else ""
    ret_pct = (f" ({float(t[RET]) / float(t[QTY]) * 100:.1f}".replace(".", ",") + "% от штук)"
               if t[QTY] else "")
    lines += [f"Продано: {_n(t[QTY])} шт · {_rub(t[RUB])}",
              f"Возвраты: −{_n(t[RET])} шт{ret_rub}{ret_pct}",
              f"<b>Итого: {_n(t[NET_QTY])} шт · {_rub(t[NET_RUB])}</b> "
              "<i>(продажи минус возвраты, до СПП)</i>"]
    if PAY in days.columns:
        lines.append(f"К перечислению от WB: {_rub(t[PAY])}")
    if AFTER in days.columns and t[NET_RUB]:
        spp = (1 - float(t[AFTER]) / float(t[NET_RUB])) * 100
        lines.append(f"WB продал покупателям на {_rub(t[AFTER])} · скидка WB (СПП) "
                     + f"{spp:.1f}".replace(".", ",") + "%")

    # бренды: заметные изменения к тому же дню прошлой недели
    if week in days.index:
        cur = df[df[dcol] == day].groupby(bcol)[NET_RUB].sum()
        old = df[df[dcol] == week].groupby(bcol)[NET_RUB].sum()
        diff = cur.sub(old, fill_value=0).sort_values()
        up = diff[diff >= BRAND_MIN].tail(3)[::-1]
        down = diff[diff <= -BRAND_MIN].head(3)
        if len(up) or len(down):
            lines += ["", f"<b>Бренды за день</b> <i>(к {WD[week.weekday()]} {week:%d.%m})</i>"]
            lines += [f"▲ {escape(str(b))} +{_rub(v)}" for b, v in up.items()]
            lines += [f"▼ {escape(str(b))} −{_rub(abs(v))}" for b, v in down.items()]

    # остатки: все места вместе, изменение за день и за неделю
    try:
        from .stocks import totals
        st, st_d, st_w = totals(day), totals(prev), totals(week)
    except Exception as e:
        st = None
        print(f"[digest] остатки: {type(e).__name__}: {e}", flush=True)
    if st:
        def ch(old, key):
            return _diff(st[key] - old[key]) if old and old["date"] < st["date"] else "—"
        lines += ["", f"<b>Остатки на {st['date']:%d.%m}: {_n(st['total'])} шт</b> "
                      "<i>(изменение за день и за неделю)</i>",
                  _pre([("", "шт", "день", "неделя")] + [
                      (name, _n(st[k]), ch(st_d, k), ch(st_w, k)) for name, k in (
                          ("Склады WB", "wb"), ("К клиенту", "to_client"),
                          ("От клиента", "from_client"), ("Склад FBS", "fbs"),
                          ("Итого", "total"))])]

    # расходы WB: вчера и 7 дней против предыдущих 7
    w_from = day - timedelta(days=6)
    try:
        costs = [c for c in wb_costs(day) if abs(c[1]) >= 1 or abs(c[2]) >= 1]
    except Exception as e:
        costs = []
        print(f"[digest] расходы WB: {type(e).__name__}: {e}", flush=True)
    if costs:
        tot = [sum(c[i] for c in costs) for i in (1, 2, 3)]
        sales7 = span(w_from, day, RUB)
        share = (f"{tot[1] / sales7 * 100:.1f}".replace(".", ",") + "% от продаж"
                 if sales7 else "")
        lines += ["", f"<b>Расходы WB</b> <i>(тыс ₽, с НДС)</i>",
                  _pre([("", "вчера", "7 дней", "изм.")]
                       + [(n, _ths(d), _ths(c), _chg(c, o)) for n, d, c, o in costs]
                       + [("Итого", _ths(tot[0]), _ths(tot[1]), _chg(tot[1], tot[2]))]),
                  f"<i>7 дней: {rng(w_from, day)}, изменение — к предыдущим 7 дням"
                  + (f" · {share}" if share else "")
                  + ". По дате операции в отчёте WB; комиссия WB не входит.</i>"]

    lines += ["", "<i>Подробности — спросите меня: по брендам, артикулам, в Excel.</i>"]
    return "\n".join(lines)
