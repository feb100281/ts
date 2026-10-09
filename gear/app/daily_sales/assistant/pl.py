# gear/app/daily_sales/assistant/pl.py
"""P&L по методике мэн пака для помощника.

Запускает те же SQL, что и gear/management/commands/mp.py (без казначейства,
ДДС-детализации и прочих листов), и считает показатели функцией mp._derive —
цифры совпадают с файлом мэн пака. Результат кэшируется на CACHE_TTL.
"""
from __future__ import annotations

import threading
import time
from collections import defaultdict
from datetime import date, timedelta

from conns import get_duckdb_conn_with_opt

CACHE_TTL = 60 * 60
_cache: dict = {}
_lock = threading.Lock()

METRICS = [
    ("rev", "Выручка без НДС, ₽"),
    ("cogs", "Себестоимость, ₽"),
    ("comm", "Комиссия WB, ₽"),
    ("sell", "Расходы на реализацию (разд. 3), ₽"),
    ("promo", "Продвижение WB (разд. 4), ₽"),
    ("md", "Маржинальный доход, ₽"),
    ("kmd", "КМД, %"),
    ("other", "Прочие доходы и расходы (разд. 5), ₽"),
    ("ovh", "Накладные (разд. 6), ₽"),
    ("corp", "Корпоративные (разд. 7), ₽"),
    ("fin", "Финансовые (разд. 8), ₽"),
    ("conv", "  в т.ч. % по конвертируемым займам, ₽"),
    ("fc", "Постоянные затраты (6+7+8), ₽"),
    ("ebt", "Результат до налога, ₽"),
    ("tax", "Налог на прибыль, ₽"),
    ("net", "Чистая прибыль, ₽"),
    ("tbu", "ТБУ (вся фин. нагрузка), ₽"),
    ("zfp", "Запас фин. прочности, ₽"),
    ("zfp_pct", "Запас фин. прочности, %"),
    ("tbu_ex", "ТБУ без конв. займов, ₽"),
    ("zfp_ex_pct", "Запас прочности без конв. займов, %"),
]


def _as_date(v):
    return v if isinstance(v, date) else date.fromisoformat(str(v)[:10])


def _load(report_date: date) -> dict:
    from gear.management.commands import mp

    with get_duckdb_conn_with_opt(ro=True) as con:
        for name in ("base.txt", "base_stocks.txt", "wb_costs.txt",
                     "dayly_sales_agg.txt"):
            con.execute(mp.read_sql(name))
        p = {"date_from": report_date}
        con.execute(mp.read_sql("margin.txt"), parameters=p)
        from gear.management.commands.sql.read_query import ensure_pl_src
        ensure_pl_src(con)
        con.execute(mp.read_sql("opex.txt"), parameters=p)
        con.execute(mp.read_sql("cf.txt"), parameters=p)
        con.execute(mp.read_sql("conv_loans.txt"),
                    parameters={**p, "title_id": mp.CONV_LOAN_TITLE_ID})
        pl_rows = con.execute("""
            SELECT me, section, item, value FROM month_margins_wb_long
            UNION ALL
            SELECT me, section, item, value FROM opex
        """).fetchall()
        tax_rows = con.execute("""
            SELECT LAST_DAY(date_from)::date, SUM(amount) FROM cf
            WHERE subitem = ? GROUP BY 1
        """, [mp.TAX_SUBITEM]).fetchall()
        conv_rows = con.execute("SELECT me, value FROM conv_loans").fetchall()

    pl_data = {}
    for me, section, item, value in pl_rows:
        pl_data[(_as_date(me), section, item)] = (
            round(float(value), 2) if value is not None else None)
    tax = defaultdict(float)
    for me, v in tax_rows:
        tax[_as_date(me)] += float(v or 0)
    conv = {_as_date(me): float(v or 0) for me, v in conv_rows}

    months = sorted({k[0] for k in pl_data})
    derived, bases = {}, {}
    for me in months:
        b = mp._base(pl_data, tax, me)
        b["conv"] = conv.get(me, 0.0)
        bases[me] = dict(b)
        derived[me] = mp._derive(b)
    return {"report_date": report_date, "pl": pl_data, "months": months,
            "derived": derived, "base": bases, "tax": dict(tax), "conv": conv,
            "loaded": time.time()}


def _report_date() -> date:
    try:
        from ..ai_analysis.data import get_last_sales_date
        d = get_last_sales_date()
        if d:
            return d
    except Exception:
        pass
    return date.today() - timedelta(days=1)


def get_pl(report_date: date | None = None) -> dict:
    report_date = report_date or _report_date()
    with _lock:
        hit = _cache.get(report_date)
        if hit and time.time() - hit["loaded"] < CACHE_TTL:
            return hit
        data = _load(report_date)
        _cache.clear()
        _cache[report_date] = data
        return data


def _fmt(v, pct=False):
    if v is None:
        return "—"
    if pct:
        return f"{v:.1f}%"
    return f"{v:,.0f}".replace(",", " ")


def _pick_months(months, date_from, date_to):
    df = _as_date(date_from) if date_from else None
    dt_ = _as_date(date_to) if date_to else None
    sel = [m for m in months
           if (df is None or m >= df.replace(day=1)) and (dt_ is None or m <= _ceil(dt_))]
    if not date_from and not date_to:
        sel = months[-3:]
    return sel[-14:]


def _ceil(d):
    nxt = (d.replace(day=28) + timedelta(days=4))
    return nxt - timedelta(days=nxt.day)


def pl_report(date_from=None, date_to=None, detail="summary") -> str:
    data = get_pl()
    months = _pick_months(data["months"], date_from, date_to)
    if not months:
        return "Нет данных P&L за этот период. Доступно: %s – %s" % (
            data["months"][0], data["months"][-1])
    rd = data["report_date"]
    hdr = ["Показатель"] + [m.strftime("%m.%Y") + ("*" if m > rd else "")
                            for m in months]
    lines = ["\t".join(hdr)]
    from .tools import MARGIN_OFF
    for key, label in METRICS:
        if MARGIN_OFF and key in ("md", "kmd"):          # до утверждения методики маржи
            continue
        pct = key in ("kmd", "zfp_pct", "zfp_ex_pct")
        vals = [data["derived"][m].get(key) for m in months]
        if key == "conv" and not any(vals):
            continue
        lines.append("\t".join([label] + [_fmt(v, pct) for v in vals]))

    if detail == "full":
        lines.append("\nДЕТАЛИЗАЦИЯ P&L (раздел | статья | суммы)")
        items = sorted({(s, i) for (m, s, i) in data["pl"] if m in months})
        for s, i in items:
            vals = [data["pl"].get((m, s, i)) for m in months]
            if not any(vals) or (MARGIN_OFF and "арж" in str(i)):
                continue
            lines.append("\t".join([f"{s.strip()} | {i}"] + [_fmt(v) for v in vals]))

    note = (f"\nДанные мэн пака на {rd:%d.%m.%Y}. Расходы со знаком минус. "
            "* — месяц неполный. ТБУ = постоянные затраты / КМД.")
    part = [m for m in months if m > rd]
    if part:
        note += (f"\nВНИМАНИЕ: {part[-1]:%m.%Y} не закрыт — в колонке со * факт только по "
                 f"{rd:%d.%m.%Y}. Затраты месяца начислены не полностью, поэтому ТБУ и запас "
                 "прочности в этой колонке не показательны: ТБУ неполного месяца оценивай "
                 "через scenario_report. Цифры других месяцев этим месяцем не называй.")
    return "\n".join(lines) + note
