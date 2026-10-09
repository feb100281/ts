# gear/app/manpack/data.py
"""Данные дашборда «Управленческий пакет». Только чтение.

P&L, ТБУ и выводы — те же расчёты, что в мэн паке (gear.management.commands.mp).
ДДС — public.cf_to_csv, остатки — запросы листа «Остатки ДС», займы — данные
дашборда «Займы и кредиты», курсы — справочник «Макро».
"""
from __future__ import annotations

import re
import threading
import time
from collections import defaultdict
from datetime import date, timedelta

import pandas as pd
from django.db import connection

from .config import CACHE_TTL, FX_CURRENCIES, SALARY_SUBITEM_CODES

_cache: dict = {}
_lock = threading.Lock()


def cached(key, fn, ttl=CACHE_TTL):
    with _lock:
        hit = _cache.get(key)
        if hit and time.time() - hit[0] < ttl:
            return hit[1]
    t0 = time.time()
    val = fn()
    dt = time.time() - t0
    if dt > 0.5:                                   # видно в консоли, что именно грузится долго
        name = key[0] if isinstance(key, tuple) else key
        print(f"[manpack] {name}: {dt:.1f} c", flush=True)
    with _lock:
        if len(_cache) > 64:
            _cache.clear()
        _cache[key] = (time.time(), val)
    return val


def month_end(d: date) -> date:
    nxt = d.replace(day=28) + timedelta(days=4)
    return nxt - timedelta(days=nxt.day)


def month_start(d: date) -> date:
    return d.replace(day=1)


def prev_month_end(d: date) -> date:
    return d.replace(day=1) - timedelta(days=1)


# ------------------------------------------------------------------ P&L
def pl_bundle() -> dict:
    from ..daily_sales.assistant.pl import get_pl
    return get_pl()


def months_list() -> list[date]:
    return pl_bundle()["months"]


def month_summary(me: date) -> dict:
    """Выводы за месяц — тексты и цифры листа «Выводы» мэн пака."""
    from gear.management.commands import mp
    b = pl_bundle()
    months = [m for m in b["months"] if m <= me]
    as_of = min(b["report_date"], me)
    return mp.month_summary(b["pl"], defaultdict(float, b["tax"]), months, as_of, b["conv"])


def derive_period(months: list[date]) -> dict:
    """Показатели за несколько месяцев суммой (как «с начала года» в мэн паке)."""
    from gear.management.commands import mp
    b = pl_bundle()
    agg = defaultdict(float)
    for m in months:
        for k, v in b["base"].get(m, {}).items():
            agg[k] += v or 0.0
    return mp._derive(dict(agg)) if agg else {}


# ------------------------------------------------------------------ ДДС
# операции без банковского счёта — расчёты через личный кабинет WB
NO_BANK = "Баланс WB (не банковский счёт)"
_BANK_RE = re.compile(r"банк|bank|^ba_|счет|счёт", re.I)


def _cf_columns() -> list[str]:
    def load():
        with connection.cursor() as cur:
            cur.execute("SELECT * FROM public.cf_to_csv LIMIT 0")
            return [c[0] for c in cur.description]
    return cached("cf_cols", load, 3600)


def _bank_names() -> dict:
    """acc_id балансового счёта → название банковского счёта."""
    def load():
        from corporate.models import BankAccount
        out = {}
        for ba in BankAccount.objects.select_related("bank"):
            if ba.bs_acc_id:
                out[ba.bs_acc_id] = str(ba)
        return out
    return cached("bank_names", load, 3600)


def cf_frame(start: date, end: date) -> pd.DataFrame:
    """Операции ДДС за период: d, bank, cp, contract, activity, item, subitem, amount."""
    def load():
        cols = _cf_columns()
        with connection.cursor() as cur:
            cur.execute("SELECT * FROM public.cf_to_csv WHERE date_from::date BETWEEN %s AND %s",
                        [start, end])
            df = pd.DataFrame(cur.fetchall(), columns=cols)
        out = pd.DataFrame(index=df.index)
        out["d"] = pd.to_datetime(df["date_from"]).dt.date if len(df) else []
        out["amount"] = pd.to_numeric(df.get("amount"), errors="coerce").fillna(0.0) if len(df) else []

        def text(col, default):
            if col in df:
                return df[col].fillna("").astype(str).str.strip().replace("", default)
            return default

        out["cp"] = text("cp_name", "Без контрагента")
        out["contract"] = text("contract_name", "Без договора")
        for c in ("activity", "operation", "item", "subitem"):
            out[c] = text(c, "—")
        bank_col = next((c for c in cols if _BANK_RE.search(c)
                         and c not in ("cp_name", "contract_name")), None)
        if bank_col:
            out["bank"] = text(bank_col, NO_BANK)
        else:
            acc_col = next((c for c in cols if c in ("acc_id", "bs_acc_id", "ba_acc_id")), None)
            names = _bank_names() if acc_col else {}
            out["bank"] = df[acc_col].map(names).fillna(NO_BANK) if acc_col and len(df) else NO_BANK
        out["contract_id"] = df["contract_id"] if "contract_id" in df else None
        return out
    return cached(("cf", start, end), load)


def has_bank_dimension() -> bool:
    cols = _cf_columns()
    return any(_BANK_RE.search(c) and c not in ("cp_name", "contract_name") for c in cols) \
        or any(c in ("acc_id", "bs_acc_id", "ba_acc_id") for c in cols)


def cf_months(as_of: date, months: int = 13):
    from ..daily_sales.assistant.treasury import _cf_months
    return cached(("cfm", as_of, months), lambda: _cf_months(as_of, months))


def cf_first_seen() -> pd.DataFrame:
    """Первая дата появления контрагента в ДДС по подстатьям (за всю историю);
    salary — подстатья «Заработная плата»."""
    def load():
        with connection.cursor() as cur:
            cur.execute("""
                SELECT COALESCE(NULLIF(TRIM(cp_name), ''), 'Без контрагента') AS cp,
                       TRIM(COALESCE(subitem, '')) AS item,
                       MIN(date_from::date) AS first_d, MAX(date_from::date) AS last_d,
                       SUM(amount)::float AS amount, COUNT(*) AS n
                FROM public.cf_to_csv GROUP BY 1, 2
            """)
            df = pd.DataFrame(cur.fetchall(), columns=["cp", "item", "first", "last", "amount", "n"])
        if df.empty:
            return df
        df["salary"] = df["item"].str.startswith(tuple(SALARY_SUBITEM_CODES))
        return df
    return cached("cf_first", load)


# ------------------------------------------------------------------ остатки
def treasury(as_of: date):
    from ..daily_sales.assistant.treasury import _treasury
    return cached(("tr", as_of), lambda: _treasury(as_of))


# ------------------------------------------------------------------ займы
def loans(as_of: date) -> pd.DataFrame:
    def load():
        from ..loans.data import get_loans_snapshot
        df = get_loans_snapshot(as_of.isoformat())
        return df if df is not None else pd.DataFrame()
    return cached(("loans", as_of), load)


# ------------------------------------------------------------------ договоры
def contracts(search: str = "", title: str | None = None, only_files: bool = False,
              limit: int = 500) -> list[dict]:
    from django.db.models import Count, Max, Q
    from contracts.models import Contracts

    qs = (Contracts.objects.select_related("title", "owner", "cp")
          .prefetch_related("files")
          .annotate(n_files=Count("files", filter=Q(files__file__isnull=False) & ~Q(files__file=""),
                                 distinct=True))
          .annotate(date_end=Max("conditions__date_finish"))
          .order_by("-date"))
    q = (search or "").strip()
    if q:
        qs = qs.filter(Q(cp__name__icontains=q) | Q(number__icontains=q) | Q(cp__tax_id=q))
    if title:
        qs = qs.filter(title__title=title)
    if only_files:
        qs = qs.filter(n_files__gt=0)
    out = []
    for c in qs[:limit]:
        files = [f for f in c.files.all() if f.file]
        out.append({
            "id": c.id,
            "cp": c.cp.name if c.cp_id else "",
            "inn": c.cp.tax_id if c.cp_id else "",
            "type": c.title.title if c.title_id else "",
            "number": c.number or "б/н",
            "date": c.date,
            "date_end": c.date_end,
            "owner": c.owner.name if c.owner_id else "",
            "currency": getattr(c, "currency", "") or "",
            "signed": bool(c.is_signed),
            "amendment": c.pid_id is not None,
            "files": [{"url": f.file.url, "name": (f.doc_number or f.get_doc_type_display()
                                                   or "Документ"),
                       "date": f.doc_date} for f in files],
        })
    return out


def contract_titles() -> list[str]:
    def load():
        from contracts.models import ContractsTitle
        return list(ContractsTitle.objects.order_by("title").values_list("title", flat=True))
    return cached("ct_titles", load, 3600)


# ------------------------------------------------------------------ УПД
def upd(start: date, end: date) -> pd.DataFrame:
    """Строки приходов: бухгалтерская и управленческая стоимость без НДС."""
    def load():
        from cards.models import UPDData
        rows = list(UPDData.objects.filter(upd_document__date__range=(start, end)).values(
            "upd_document_id", "upd_document__number", "upd_document__date",
            "upd_document__counterparty__name", "upd_document__contract__number",
            "brand", "upd_qty", "upd_price_vatless", "upd_amount_vatless",
            "man_cost_per_unit"))
        df = pd.DataFrame(rows)
        if df.empty:
            return df
        df = df.rename(columns={
            "upd_document_id": "doc_id", "upd_document__number": "number",
            "upd_document__date": "d", "upd_document__counterparty__name": "cp",
            "upd_document__contract__number": "contract"})
        for c in ("upd_qty", "upd_price_vatless", "upd_amount_vatless", "man_cost_per_unit"):
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)
        df["buh"] = df["upd_amount_vatless"].where(
            df["upd_amount_vatless"] != 0, df["upd_qty"] * df["upd_price_vatless"])
        df["man"] = df["upd_qty"] * df["man_cost_per_unit"]
        df["no_man"] = (df["man_cost_per_unit"] == 0)
        df["brand"] = df["brand"].fillna("").replace("", "Без бренда").str.upper()
        df["cp"] = df["cp"].fillna("Без поставщика")
        return df
    return cached(("upd", start, end), load)


# ------------------------------------------------------------------ курсы
def fx(start: date, end: date) -> pd.DataFrame:
    def load():
        from macro.models import CurrencyRate
        rows = list(CurrencyRate.objects.filter(
            base_currency="RUB", currency__in=FX_CURRENCIES,
            date__range=(start - timedelta(days=10), end)).values("date", "currency", "rate"))
        df = pd.DataFrame(rows)
        if df.empty:
            return df
        df["rate"] = pd.to_numeric(df["rate"], errors="coerce")
        return df.sort_values("date")
    return cached(("fx", start, end), load)


def fx_at(df: pd.DataFrame, cur: str, d: date):
    """Курс на дату (последний известный не позже неё)."""
    if df.empty:
        return None, None
    s = df[(df["currency"] == cur) & (df["date"] <= d)]
    if s.empty:
        return None, None
    r = s.iloc[-1]
    return float(r["rate"]), r["date"]


def key_rate(d: date):
    def load():
        from macro.models import KeyRate
        o = KeyRate.objects.filter(date__lte=d).order_by("-date").first()
        return (float(o.key_rate), o.date) if o else (None, None)
    return cached(("kr", d), load, 3600)


# ------------------------------------------------------------------ договоры: сроки и платежи
def contracts_ending(start: date, end: date) -> list[dict]:
    """Договоры, у которых последняя дата окончания условий попадает в период."""
    def load():
        from django.db.models import Max
        from contracts.models import Contracts
        qs = (Contracts.objects.select_related("title", "cp")
              .annotate(date_end=Max("conditions__date_finish"))
              .filter(date_end__range=(start, end)).order_by("date_end"))
        return [{"id": c.id, "cp": c.cp.name if c.cp_id else "",
                 "type": c.title.title if c.title_id else "",
                 "number": c.number or "б/н", "date": c.date, "date_end": c.date_end}
                for c in qs[:200]]
    return cached(("ct_end", start, end), load)


def contracts_paid(start: date, end: date) -> pd.DataFrame:
    """Договоры с движением денег за период и их метод учёта / функция списания.

    group: метод учёта договора; «Без функции списания» — у договора нет условий
    с функцией списания.
    """
    def load():
        from contracts.models import Conditions, Contracts
        cf = cf_frame(start, end)
        if cf.empty or cf["contract_id"].isna().all():
            return pd.DataFrame()
        cf = cf.dropna(subset=["contract_id"]).copy()
        cf["contract_id"] = pd.to_numeric(cf["contract_id"], errors="coerce")
        cf = cf.dropna(subset=["contract_id"])
        cf["contract_id"] = cf["contract_id"].astype(int)
        g = cf.groupby("contract_id").agg(
            inflow=("amount", lambda x: x[x > 0].sum()),
            outflow=("amount", lambda x: x[x < 0].sum()),
            n=("amount", "size"), last=("d", "max")).reset_index()
        ids = g["contract_id"].tolist()
        info = {c.id: c for c in Contracts.objects.select_related("title", "cp", "pid")
                .filter(id__in=ids)}
        # условия ищем у самого договора и у основного (для доп. соглашений)
        owners = {i: [i] + ([info[i].pid_id] if i in info and info[i].pid_id else [])
                  for i in ids}
        all_ids = {x for v in owners.values() for x in v}
        conds = defaultdict(list)
        for c in (Conditions.objects.select_related("accounting_method", "fn",
                                                    "fn__accounting_method")
                  .filter(contract_id__in=all_ids)):
            conds[c.contract_id].append(c)
        rows = []
        for r in g.itertuples():
            c = info.get(r.contract_id)
            cs = [x for cid in owners.get(r.contract_id, []) for x in conds.get(cid, [])]
            methods = sorted({(x.accounting_method or (x.fn.accounting_method if x.fn_id else None)).name
                              for x in cs
                              if x.accounting_method_id or (x.fn_id and x.fn.accounting_method_id)})
            fns = sorted({x.fn.name for x in cs if x.fn_id})
            finish = max((x.date_finish for x in cs if x.date_finish), default=None)
            rows.append({
                "group": "Без функции списания" if not fns else
                         (", ".join(methods) or "Метод учёта не задан"),
                "cp": c.cp.name if c and c.cp_id else "",
                "type": c.title.title if c and c.title_id else "",
                "number": (c.number or "б/н") if c else str(r.contract_id),
                "date": c.date if c else None, "date_end": finish,
                "fn": ", ".join(fns), "conditions": len(cs),
                "inflow": float(r.inflow), "outflow": float(r.outflow),
                "n": int(r.n), "last": r.last, "id": r.contract_id,
            })
        return pd.DataFrame(rows)
    return cached(("ct_paid", start, end), load)


# ------------------------------------------------------------------ поступления от WB
def wb_payouts(as_of: date) -> dict:
    """Вывод средств из кабинета WB и зачисление на расчётный счёт (как в мэн паке)."""
    def load():
        from conns import get_duckdb_conn_with_opt
        from gear.management.commands import mp
        with get_duckdb_conn_with_opt(ro=True) as con:
            con.execute(mp.read_sql("wb_payouts.txt"), parameters={"date_from": as_of})
            rows = con.execute("SELECT * FROM wb_payouts").fetchall()
        outs, ins = mp.split_payouts(rows)
        pairs = mp.match_wb_payouts(outs, ins)
        return {"pairs": pairs, "last_in": max((i["dt"] for i in ins), default=None)}
    return cached(("wbp", as_of), load)


# ------------------------------------------------------------------ P&L: расшифровка
PL_DETAIL_SQL = """
    SELECT (date_trunc('month', p.date_from::date) + interval '1 month - 1 day')::date AS me,
           CASE WHEN p.account_name LIKE '420000%%' THEN '5'
                WHEN p.account_name LIKE '610000%%' THEN '6'
                WHEN p.account_name LIKE '620000%%' THEN '7'
                ELSE '8' END AS sec,
           CASE WHEN p.account_name LIKE '630000%%'
                    THEN COALESCE(NULLIF(TRIM(p.cost_item), ''), 'Без группы')
                ELSE COALESCE(NULLIF(TRIM(p.cost_item_group), ''), 'Без группы') END AS item,
           COALESCE(NULLIF(TRIM(p.cost_item), ''), 'Без статьи') AS sub,
           SUM(p.amount)::float AS amount
    FROM public.pl_for_csv p
    WHERE p.date_from::date BETWEEN %s AND %s
      AND (
            (p.account_name LIKE '420000%%' AND p.cost_item_group NOT LIKE '590100%%')
         OR (p.account_name LIKE '610000%%' AND p.cost_item NOT LIKE '540101%%')
         OR p.account_name LIKE '620000%%'
         OR p.account_name LIKE '630000%%'
      )
    GROUP BY 1, 2, 3, 4
"""


def pl_detail(start: date, end: date) -> pd.DataFrame:
    """Разделы 5–8 P&L до подстатьи (те же фильтры, что в мэн паке)."""
    def load():
        with connection.cursor() as cur:
            cur.execute(PL_DETAIL_SQL, [start, end])
            return pd.DataFrame(cur.fetchall(),
                                columns=["me", "sec", "item", "sub", "amount"])
    return cached(("pl_detail", start, end), load, 3600)


# ------------------------------------------------------------------ изменения затрат
def cost_changes(me: date, top: int = 10) -> list[dict]:
    """Статьи P&L (разделы 3–8) с наибольшим изменением к прошлому месяцу."""
    b = pl_bundle()
    prev = prev_month_end(me)
    keys = {(s, i) for (m, s, i) in b["pl"]
            if m in (me, prev) and s.strip()[:1] in "345678" and "%" not in i}
    rows = []
    for sec, item in keys:
        cur = b["pl"].get((me, sec, item)) or 0.0
        old = b["pl"].get((prev, sec, item)) or 0.0
        if abs(cur - old) < 1:
            continue
        rows.append({"sec": sec.strip().split(".")[0], "item": item, "cur": cur, "prev": old,
                     "diff": cur - old})
    rows.sort(key=lambda r: -abs(r["diff"]))
    return rows[:top]


# ------------------------------------------------------------------ прибыль против денег
def profit_vs_cash(me: date) -> dict:
    """Сопоставление P&L (начисление) и ДДС (деньги) за месяц."""
    b = pl_bundle()
    d = b["derived"].get(me) or {}
    cf = cf_frame(month_start(me), me)
    by_act = (cf.groupby("activity")["amount"].sum().to_dict() if not cf.empty else {})
    text = (cf["item"].str.lower() + " " + cf["subitem"].str.lower()) if not cf.empty else None
    pick = lambda words: float(cf.loc[text.str.contains(words, regex=True), "amount"].sum()) \
        if text is not None else 0.0
    try:
        pairs = wb_payouts(min(me, date.today()))["pairs"]
        wb_in = sum(p["out_amount"] for p in pairs
                    if p["in_dt"] and month_start(me) <= p["in_dt"] <= me)
    except Exception:
        wb_in = None
    return {"net": d.get("net"), "rev": d.get("rev"), "cogs": d.get("cogs"), "fin": d.get("fin"),
            "tax": d.get("tax"), "cf_net": float(cf["amount"].sum()) if not cf.empty else 0.0,
            "by_activity": by_act, "interest_paid": pick("процент"),
            "tax_paid": pick("налог на прибыль"), "wb_in": wb_in,
            "top_cf": (cf.groupby("subitem")["amount"].sum().sort_values().to_dict()
                       if not cf.empty else {})}


def pl_item_counterparties(me: date, sec: str, item: str, sub: str | None = None) -> pd.DataFrame:
    """Контрагенты одной статьи P&L: сумма за месяц и с начала года (грузится по запросу)."""
    def load():
        sql = PL_DETAIL_SQL.replace(
            "COALESCE(NULLIF(TRIM(p.cost_item), ''), 'Без статьи') AS sub,",
            "COALESCE(NULLIF(TRIM(p.cost_item), ''), 'Без статьи') AS sub,\n"
            "           COALESCE(NULLIF(TRIM(p.cp_name), ''), 'Без контрагента') AS cp,\n"
            "           COALESCE(NULLIF(TRIM(p.contract_name), ''), 'Без договора') AS contract,"
        ).replace("GROUP BY 1, 2, 3, 4", "GROUP BY 1, 2, 3, 4, 5, 6")
        with connection.cursor() as cur:
            cur.execute(sql, [date(me.year, 1, 1), me])
            df = pd.DataFrame(cur.fetchall(), columns=["me", "sec", "item", "sub", "cp",
                                                       "contract", "amount"])
        return df
    df = cached(("pl_cp", me), load, 3600)
    if df.empty:
        return df
    d = df[(df["sec"] == sec) & (df["item"] == item)]
    if sub:
        d = d[d["sub"] == sub]
    if d.empty:
        return d
    g = d.groupby(["cp", "contract", "sub"]).agg(
        ytd=("amount", "sum"),
        month=("amount", lambda x: x[d.loc[x.index, "me"] == me].sum())).reset_index()
    return g.reindex(g["month"].abs().sort_values(ascending=False).index)
