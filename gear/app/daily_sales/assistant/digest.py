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


# расходы WB за день: (подпись, условие по sales.sales_long); суммы с НДС, как в отчёте WB
WB_COSTS = (
    ("Логистика", "field = 'delivery_rub'"),
    ("Хранение", "field = 'storage_fee'"),
    ("Приёмка", "field = 'acceptance'"),
    ("Штрафы", "field = 'penalty'"),
    ("Программа лояльности", "field IN ('cashback_amount', 'cashback_commission_change')"),
    ("Маркетинг: продвижение и услуги WB", "field = 'deduction' AND btn IS NOT NULL "
                                "AND NOT STARTS_WITH(btn, 'Платеж') "
                                "AND NOT STARTS_WITH(btn, 'Перевод')"),
)


def wb_costs(day: date, prev: date) -> list[tuple[str, float, float]]:
    """[(статья, расход за день, расход за день сравнения)], расход — положительный."""
    cols = ", ".join(
        f"SUM(CASE WHEN {cond} THEN (CASE WHEN oper = 'cr' THEN val ELSE -val END) END) / 100"
        for _, cond in WB_COSTS)
    with get_duckdb_conn_with_opt(with_pg=False) as con:
        rows = dict((r[0], r[1:]) for r in con.execute(
            f"SELECT date_from::DATE, {cols} FROM sales.sales_long "
            "WHERE date_from::DATE IN (?, ?) GROUP BY 1", [day, prev]).fetchall())
    cur, old = rows.get(day) or [0] * len(WB_COSTS), rows.get(prev) or [0] * len(WB_COSTS)
    return [(name, float(cur[i] or 0), float(old[i] or 0))
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
    if not prev:
        return "нет данных для сравнения"
    p = (float(cur) - float(prev)) / abs(float(prev)) * 100
    return ("+" if p >= 0 else "−") + f"{abs(p):.1f}".replace(".", ",") + "%"


def build(day: date) -> str | None:
    """Текст сводки (HTML для Telegram) или None, если за день продаж нет."""
    import pandas as pd
    from ..wb_sales_export import fetch

    df = fetch(day - timedelta(days=7), day, "brand_day", [])
    if df.empty:
        return None
    dcol, bcol = df.columns[0], df.columns[1]
    df[dcol] = pd.to_datetime(df[dcol]).dt.date
    num = [c for c in (QTY, RET, NET_QTY, RUB, NET_RUB, PAY) if c in df.columns]
    days = df.groupby(dcol)[num].sum()
    if day not in days.index or not days.at[day, QTY]:
        return None
    t = days.loc[day]
    prev, week = day - timedelta(days=1), day - timedelta(days=7)

    lines = [
        f"<b>Продажи за {day:%d.%m.%Y}</b> ({WD[day.weekday()]})",
        f"Данные загружены по {day:%d.%m.%Y}. Продажи «как на сайте WB», с НДС, до СПП.",
        "",
        f"Продано: <b>{_n(t[QTY])} шт</b> на <b>{_rub(t[RUB])}</b>",
        f"Возвраты: {_n(t[RET])} шт"
        + (f" ({float(t[RET]) / float(t[QTY]) * 100:.1f}%".replace(".", ",") + " от продаж)"
           if t[QTY] else ""),
        f"Итого за вычетом возвратов: <b>{_n(t[NET_QTY])} шт</b> на <b>{_rub(t[NET_RUB])}</b>",
    ]
    if PAY in days.columns:
        lines.append(f"К перечислению от WB: {_rub(t[PAY])}")
    lines += ["", "<b>Сравнение</b> (итого в рублях)"]
    for d, label in ((prev, "к предыдущему дню"), (week, "к тому же дню недели")):
        if d in days.index:
            lines.append(f"• {label}, {d:%d.%m} ({WD[d.weekday()]}): "
                         f"<b>{_chg(t[NET_RUB], days.at[d, NET_RUB])}</b>"
                         f" · {_rub(days.at[d, NET_RUB])}")
        else:
            lines.append(f"• {label}, {d:%d.%m}: нет данных")

    # бренды: что выросло и что просело к тому же дню прошлой недели
    if week in days.index:
        cur = df[df[dcol] == day].groupby(bcol)[NET_RUB].sum()
        old = df[df[dcol] == week].groupby(bcol)[NET_RUB].sum()
        diff = cur.sub(old, fill_value=0).sort_values()
        up = [f"{escape(str(b))} +{_rub(v)}" for b, v in diff[diff > 0].tail(3)[::-1].items()]
        down = [f"{escape(str(b))} −{_rub(abs(v))}" for b, v in diff[diff < 0].head(3).items()]
        if up or down:
            lines += ["", f"<b>Бренды к {week:%d.%m}</b>"]
            if up:
                lines.append("Рост: " + "; ".join(up))
            if down:
                lines.append("Падение: " + "; ".join(down))
    # расходы WB за день
    try:
        costs = [c for c in wb_costs(day, week) if abs(c[1]) >= 1]
    except Exception as e:
        costs = []
        print(f"[digest] расходы WB: {type(e).__name__}: {e}", flush=True)
    if costs:
        total = sum(c[1] for c in costs)
        share = (f" — {total / float(t[RUB]) * 100:.1f}".replace(".", ",") + "% от продаж"
                 if t[RUB] else "")
        lines += ["", f"<b>Расходы WB за день: {_rub(total)}</b>{share}"]
        for name, v, old in costs:
            cmp_ = f" ({_chg(v, old)} к {week:%d.%m})" if abs(old) >= 1 else ""
            lines.append(f"• {name}: {_rub(v)}{cmp_}")
        lines.append("<i>С НДС, по дате операции в отчёте WB; за последние дни может "
                     "дополниться.</i>")

    # остатки: все места вместе
    try:
        from .stocks import totals
        st = totals(day)
    except Exception as e:
        st = None
        print(f"[digest] остатки: {type(e).__name__}: {e}", flush=True)
    if st:
        lines += ["", f"<b>Остатки на {st['date']:%d.%m.%Y}: {_n(st['total'])} шт</b>",
                  f"• на складах WB: {_n(st['wb'])}",
                  f"• в пути к клиенту: {_n(st['to_client'])}",
                  f"• в пути от клиента: {_n(st['from_client'])}",
                  f"• на нашем складе FBS: {_n(st['fbs'])}"]
    lines += ["", "<i>Подробности — спросите меня: по брендам, артикулам, в Excel.</i>"]
    return "\n".join(lines)
