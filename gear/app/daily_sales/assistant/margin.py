# gear/app/daily_sales/assistant/margin.py
"""Маржинальность продаж по брендам / категориям / артикулам.

Методика мэн пака (витрина base из gear/management/commands/sql/base.txt):
  выручка — продажи до СПП без НДС, управленческая себестоимость FIFO, комиссия WB с
  корректировкой НДС, как в дашборде продаж (строка 1.16 мэн пака)
  → МД1 «маржа после комиссии» (строка 1.11 P&L).
Расходы WB и продвижение (разделы 3–4 P&L, без НДС) — как в дашборде продаж:
  по неделе внутри месяца на проданную штуку.
  → МД2 «маржа после расходов WB». МД2 < 0 — продажи в убыток.
"""
from __future__ import annotations

import threading
import time
from datetime import date, timedelta

import pandas as pd

from conns import get_duckdb_conn_with_opt
from gear.app.data.queries import DAY_COST_RATE_SQL

CACHE_TTL = 30 * 60
_cache: dict = {}
_lock = threading.Lock()

GROUPS = {
    "brand": ["Бренд"],
    "category": ["Категория"],
    "gender": ["Пол"],
    "brand_category": ["Бренд", "Категория"],
    "article": ["Бренд", "Категория", "Артикул WB", "Наименование"],
    "total": [],
}

WB_FIELDS = ("delivery_rub", "storage_fee", "acceptance", "penalty",
             "cashback_amount", "cashback_commission_change")

SALES_SQL = """
    SELECT
        usk AS nm_id,
        COALESCE(NULLIF(TRIM(ANY_VALUE(brand)), ''), 'НЕ УКАЗАН') AS brand,
        COALESCE(NULLIF(TRIM(ANY_VALUE(subject_name)), ''), 'Не указана') AS category,
        COALESCE(ANY_VALUE(gender), 'Не указан') AS gender,
        COALESCE(NULLIF(TRIM(ANY_VALUE(title)), ''), 'Без наименования') AS title,
        SUM(CASE WHEN cr_rev > 0 THEN 1 WHEN cr_rev < 0 THEN -1 ELSE 0 END) AS qty,
        SUM(cr_rev / (100 + vat_rate) * 100) / 100 AS rev,
        SUM(adjusted_cogs_man) / 100 AS cogs,
        SUM(net_comission) / 100 AS comm,
        -- оценочная себестоимость: нет приходов → резерв 620 ₽; нет на складе → последняя цена
        COUNT(*) FILTER (WHERE cr_rev > 0 AND cr_man = 0 AND last_man_cr IS NULL) AS q_reserve,
        COUNT(*) FILTER (WHERE cr_rev > 0 AND last_man_cr IS NOT NULL) AS q_last,
        COALESCE(SUM(adjusted_cogs_man) FILTER (
            WHERE (cr_man = 0 AND last_man_cr IS NULL) OR last_man_cr IS NOT NULL), 0) / 100 AS cogs_est
    FROM base
    WHERE cr_rev <> 0 AND date_from::DATE BETWEEN ? AND ?
    GROUP BY usk
"""

COSTS_SQL = f"""
    SELECT
        nm_id,
        CASE WHEN field = 'deduction' THEN 'promo' ELSE 'wb' END AS kind,
        SUM((CASE WHEN oper = 'dt' THEN val ELSE -val END)
            / (100 + COALESCE(vat_rate, 20)) * 100) / 100 AS v
    FROM sales.sales_long
    WHERE date_from::DATE BETWEEN ? AND ?
      AND (field IN {WB_FIELDS}
           OR (field = 'deduction' AND btn IS NOT NULL
               AND NOT STARTS_WITH(btn, 'Платеж')
               AND NOT STARTS_WITH(btn, 'Перевод')))
    GROUP BY 1, 2
"""

# расходы WB и продвижение (разделы 3–4 P&L, без НДС) — как в дашборде продаж:
# по неделе внутри месяца на проданную штуку (DAY_COST_RATE_SQL)
WB_RATE_SQL = ("WITH " + DAY_COST_RATE_SQL.replace("wb_costs_pl", "wb_costs") + """
    SELECT b.usk AS nm_id,
           SUM((CASE WHEN b.cr_rev > 0 THEN 1 WHEN b.cr_rev < 0 THEN -1 ELSE 0 END)
               * COALESCE(dr.r, 0)) / 100 AS wb
    FROM base b
    LEFT JOIN day_rate dr ON dr.d = b.date_from::DATE
    WHERE b.cr_rev <> 0 AND b.date_from::DATE BETWEEN ? AND ?
    GROUP BY 1
""")

ADS_SQL = """
    SELECT nm_id, SUM(spend_rub) AS spend
    FROM ads.unpacked_ad_campaigns_stats_by_nm
    WHERE date BETWEEN ? AND ?
    GROUP BY nm_id
"""


def _fix_comm(con) -> None:
    """Комиссия как в дашборде продаж: + НДС с суммы СПП (1.14) и НДС WB служебных
    строк по дням. В base.txt комиссия уже за вычетом фактического НДС WB (1.15)."""
    from gear.app.data.queries import COMM_TECH_SQL
    con.execute("UPDATE base SET net_comission = net_comission "
                "+ (cr_rev - COALESCE(retail_amount, 0)) * vat_rate / (100 + vat_rate) "
                "WHERE cr_rev <> 0")
    con.execute(COMM_TECH_SQL)


def _load(start: date, end: date) -> pd.DataFrame:
    from gear.management.commands import mp

    with get_duckdb_conn_with_opt(ro=True) as con:
        con.execute(mp.read_sql("base.txt"))
        _fix_comm(con)
        con.execute(mp.read_sql("wb_costs.txt"))
        s = con.execute(SALES_SQL, [start, end]).df()
        w = con.execute(WB_RATE_SQL, [start, end]).df()

    if s.empty:
        return s
    s["nm_id"] = pd.to_numeric(s["nm_id"], errors="coerce")
    w["nm_id"] = pd.to_numeric(w["nm_id"], errors="coerce")
    # расходы со знаком минус, как в P&L
    s["wb_direct"] = -s["nm_id"].map(w.groupby("nm_id")["wb"].sum()).fillna(0.0)
    s["wb_alloc"] = 0.0
    s["promo"] = 0.0
    s.attrs["promo_basis"] = "вместе с расходами WB — по неделе внутри месяца на штуку"
    s.attrs["wb_unallocated"] = 0.0
    return s


def get_margin(start: date, end: date) -> pd.DataFrame:
    key = (start, end)
    with _lock:
        hit = _cache.get(key)
        if hit and time.time() - hit[0] < CACHE_TTL:
            return hit[1]
        df = _load(start, end)
        if len(_cache) > 8:
            _cache.clear()
        _cache[key] = (time.time(), df)
        return df


def _period(date_from, date_to):
    end = date.fromisoformat(str(date_to)[:10]) if date_to else date.today() - timedelta(days=1)
    start = date.fromisoformat(str(date_from)[:10]) if date_from else end.replace(day=1)
    return start, end


def margin_table(date_from=None, date_to=None, group_by="brand", search=None,
                 only_loss=False, top=50):
    """DataFrame с маржинальностью по выбранному разрезу (для чата и Excel)."""
    start, end = _period(date_from, date_to)
    s = get_margin(start, end)
    if s.empty:
        return pd.DataFrame(), start, end, {}
    meta = dict(s.attrs)
    d = s.rename(columns={"brand": "Бренд", "category": "Категория", "gender": "Пол",
                          "nm_id": "Артикул WB", "title": "Наименование"})
    if search:
        q = str(search).lower()
        mask = (d["Категория"].str.lower().str.contains(q, regex=False)
                | d["Бренд"].str.lower().str.contains(q, regex=False)
                | d["Наименование"].str.lower().str.contains(q, regex=False))
        d = d[mask]
    keys = GROUPS.get(group_by, GROUPS["brand"])
    num = ["qty", "rev", "cogs", "comm", "wb_direct", "wb_alloc", "promo",
           "q_reserve", "q_last", "cogs_est"]
    g = d.groupby(keys, dropna=False)[num].sum().reset_index() if keys \
        else d[num].sum().to_frame().T
    g["wb"] = g["wb_direct"] + g["wb_alloc"]
    g["md1"] = g["rev"] - g["cogs"] + g["comm"]
    g["md2"] = g["md1"] + g["wb"] + g["promo"]
    rv = g["rev"].where(g["rev"] != 0)
    out = pd.DataFrame({k: g[k] for k in keys})
    out["Продажи, шт"] = g["qty"]
    out["Выручка без НДС, ₽"] = g["rev"]
    out["Себестоимость, ₽"] = -g["cogs"]
    out["Комиссия WB, ₽"] = g["comm"]
    out["МД1 после комиссии, ₽"] = g["md1"]
    out["МД1, %"] = g["md1"] / rv * 100
    out["Расходы WB и продвижение, ₽"] = g["wb"] + g["promo"]
    out["МД2 после расходов WB, ₽"] = g["md2"]
    out["МД2, %"] = g["md2"] / rv * 100
    out["Доля выручки, %"] = g["rev"] / g["rev"].sum() * 100 if g["rev"].sum() else None
    out["С/с резерв 620 ₽, шт"] = g["q_reserve"]
    out["С/с по последней цене, шт"] = g["q_last"]
    est = (g["cogs_est"] / g["cogs"].where(g["cogs"] != 0) * 100).clip(lower=0, upper=100)
    out["Оценочная с/с, %"] = est

    def status(md2, e):
        if md2 >= 0:
            return ""
        if e is not None and e == e and e >= 50:
            return "УБЫТОК? с/с оценочная — проверить"
        if e is not None and e == e and e >= 10:
            return "УБЫТОК (часть с/с оценочная)"
        return "УБЫТОК"
    out["Статус"] = [status(m, e) for m, e in zip(g["md2"], est)]
    out = out.sort_values("МД2 после расходов WB, ₽")
    if only_loss:
        out = out[out["МД2 после расходов WB, ₽"] < 0]
    return out, start, end, meta


def margin_report(date_from=None, date_to=None, group_by="brand", search=None,
                  only_loss=False, top=50) -> str:
    out, start, end, meta = margin_table(date_from, date_to, group_by, search, only_loss)
    if out.empty:
        return f"Нет продаж за {start:%d.%m.%Y}–{end:%d.%m.%Y} по этому условию."
    n_all = len(out)
    n_loss = int(out["Статус"].str.startswith("УБЫТОК").sum())
    n_doubt = int(out["Статус"].str.contains("оценочн").sum())
    view = out.head(int(top or 50))

    def f(v, pct=False):
        if v is None or pd.isna(v):
            return "—"
        return f"{v:.1f}%" if pct else f"{v:,.0f}".replace(",", " ")

    lines = ["\t".join(view.columns)]
    for _, r in view.iterrows():
        lines.append("\t".join(
            f(v, c.endswith("%")) if isinstance(v, (int, float)) and not isinstance(v, bool)
            else str(v) for c, v in r.items()))
    tot_rev = out["Выручка без НДС, ₽"].sum()
    tot_md2 = out["МД2 после расходов WB, ₽"].sum()
    note = (f"\nПериод {start:%d.%m.%Y}–{end:%d.%m.%Y}. Строк: {n_all}, в убытке: {n_loss}. "
            f"Итого выручка без НДС {f(tot_rev)} ₽, МД2 {f(tot_md2)} ₽ "
            f"({f(tot_md2 / tot_rev * 100 if tot_rev else None, True)}). "
            f"Из убыточных с оценочной себестоимостью: {n_doubt}. "
            "Сортировка: от худшей МД2. Методика как в дашборде продаж: комиссия WB с "
            "корректировкой НДС, расходы WB и продвижение (разделы 3–4 P&L, без НДС) — по "
            "неделе внутри месяца на проданную штуку. "
            "Расходы со знаком минус. Постоянные затраты (накладные, корпоративные, "
            "финансовые) в МД2 не входят.")
    return "\n".join(lines) + note


# ---- маржа «как в дашборде продаж»: расходы WB за неделю делятся на проданные штуки
DASH_SQL = """
    WITH """ + DAY_COST_RATE_SQL.replace("wb_costs_pl", "wb_costs").replace("{", "{{").replace("}", "}}") + """
    SELECT
        COALESCE(NULLIF(TRIM({dim}), ''), 'Не указано') AS name,
        SUM(CASE WHEN b.cr_rev > 0 THEN 1 WHEN b.cr_rev < 0 THEN -1 ELSE 0 END) AS qty,
        SUM(b.cr_rev / (100 + b.vat_rate) * 100) / 100 AS rev,
        SUM(b.adjusted_cogs_man) / 100 AS cogs,
        SUM(b.net_comission) / 100 AS comm,
        SUM((CASE WHEN b.cr_rev > 0 THEN 1 WHEN b.cr_rev < 0 THEN -1 ELSE 0 END)
            * COALESCE(dr.r, 0)) / 100 AS wb
    FROM base b
    LEFT JOIN day_rate dr ON dr.d = b.date_from::DATE
    WHERE b.cr_rev <> 0 AND b.date_from::DATE BETWEEN ? AND ?
    GROUP BY 1
"""
_dash_cache: dict = {}


def dashboard_margin(start: date, end: date, group_by: str = "brand") -> pd.DataFrame:
    """Маржа по методике дашборда продаж: name, qty, rev, cogs, md1, wb, md2.

    md1 = выручка без НДС − себестоимость − комиссия; md2 = md1 − расходы WB, где расходы
    WB (разделы 3–4 P&L, без НДС) делятся поровну на штуки, проданные за ту же неделю
    внутри месяца.
    """
    from gear.management.commands import mp

    dim = {"brand": "b.brand", "category": "b.subject_name"}[group_by]
    key = (start, end, group_by)
    with _lock:
        hit = _dash_cache.get(key)
        if hit and time.time() - hit[0] < CACHE_TTL:
            return hit[1].copy()
    with get_duckdb_conn_with_opt(ro=True) as con:
        con.execute(mp.read_sql("base.txt"))
        _fix_comm(con)
        con.execute(mp.read_sql("wb_costs.txt"))
        d = con.execute(DASH_SQL.format(dim=dim), [start, end]).df()
    if not d.empty:
        for c in ("qty", "rev", "cogs", "comm", "wb"):
            d[c] = pd.to_numeric(d[c], errors="coerce").fillna(0.0)
        d["md1"] = d["rev"] - d["cogs"] + d["comm"]
        d["md2"] = d["md1"] - d["wb"]
    with _lock:
        if len(_dash_cache) > 8:
            _dash_cache.clear()
        _dash_cache[key] = (time.time(), d)
    return d.copy()
