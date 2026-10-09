# gear/app/daily_sales/assistant/cashflow.py
"""ДДС для помощника: та же выборка, что и лист Cash Flow мэн пака
(public.cf_to_csv). Только чтение. Имена ИП и физлиц маскируются."""
from __future__ import annotations

import re
import threading
import time
from datetime import date, timedelta

import pandas as pd
from django.db import connection

CACHE_TTL = 15 * 60
_cache: dict = {}
_lock = threading.Lock()

GROUPS = {
    "month": "Месяц",
    "day": "Дата",
    "activity": "Вид деятельности",
    "item": "Статья",
    "subitem": "Подстатья",
    "counterparty": "Контрагент",
    "contract": "Договор",
}
_PERSON = re.compile(r"^(ИП|индивидуальный предприниматель)\s|^[А-ЯЁ][а-яё-]+\s[А-ЯЁ][а-яё-]+\s[А-ЯЁ][а-яё-]+(вич|вна|ична|чна|оглы|кызы)$", re.I)


def _mask(name, inn=None):
    n = (name or "").strip()
    inn = (str(inn).strip() if inn is not None else "")
    if (len(inn) == 12 and inn.isdigit()) or _PERSON.search(n):
        return "ИП/физлицо" + (f" (ИНН …{inn[-4:]})" if inn else "")
    return n or "Без контрагента"


def _load(start: date, end: date) -> pd.DataFrame:
    with connection.cursor() as cur:
        cur.execute("SELECT * FROM public.cf_to_csv WHERE date_from::date BETWEEN %s AND %s",
                    [start, end])
        cols = [c[0] for c in cur.description]
        df = pd.DataFrame(cur.fetchall(), columns=cols)
    if df.empty:
        return df
    inn_col = next((c for c in cols if re.search(r"(inn|tax_id)", c, re.I)
                    and re.search(r"cp|counter|contr", c, re.I)), None)
    df["cp"] = [_mask(n, df.at[i, inn_col] if inn_col else None)
                for i, n in zip(df.index, df.get("cp_name", pd.Series([""] * len(df))))]
    df["contract"] = df.get("contract_name", "").fillna("").replace("", "Без договора")
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)
    df["d"] = pd.to_datetime(df["date_from"]).dt.date
    for c in ("activity", "item", "subitem", "operation"):
        if c not in df:
            df[c] = ""
        df[c] = df[c].fillna("").astype(str)
    return df[["d", "activity", "operation", "item", "subitem", "cp", "contract", "amount"]]


def _get(start, end):
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


def _fmt(v):
    return f"{v:,.0f}".replace(",", " ")


def cf_report(date_from=None, date_to=None, group_by="item", search=None,
              direction="all", top=30, operations=False) -> str:
    end = date.fromisoformat(str(date_to)[:10]) if date_to else date.today()
    start = date.fromisoformat(str(date_from)[:10]) if date_from else end.replace(day=1)
    df = _get(start, end)
    if df.empty:
        return f"Движений ДДС за {start:%d.%m.%Y}–{end:%d.%m.%Y} нет."
    if search:
        q = str(search).lower()
        mask = pd.Series(False, index=df.index)
        for c in ("cp", "contract", "item", "subitem", "activity", "operation"):
            mask |= df[c].str.lower().str.contains(q, regex=False)
        df = df[mask]
    if direction == "in":
        df = df[df["amount"] > 0]
    elif direction == "out":
        df = df[df["amount"] < 0]
    if df.empty:
        return "По условию движений нет."
    top = min(int(top or 30), 200)
    head = (f"ДДС {start:%d.%m.%Y}–{end:%d.%m.%Y}: поступления {_fmt(df.loc[df.amount > 0, 'amount'].sum())} ₽, "
            f"выплаты {_fmt(df.loc[df.amount < 0, 'amount'].sum())} ₽, сальдо {_fmt(df.amount.sum())} ₽, "
            f"операций {len(df)}.")

    if operations:
        v = df.sort_values("d", ascending=False).head(top)
        lines = ["Дата\tСумма, ₽\tСтатья\tПодстатья\tКонтрагент\tДоговор"]
        lines += [f"{r.d:%d.%m.%Y}\t{_fmt(r.amount)}\t{r.item}\t{r.subitem}\t{r.cp}\t{r.contract}"
                  for r in v.itertuples()]
        return head + "\n" + "\n".join(lines) + f"\nПоказано {len(v)} последних операций."

    key = {"month": None, "day": "d", "activity": "activity", "item": "item",
           "subitem": "subitem", "counterparty": "cp", "contract": "contract"}.get(group_by, "item")
    d = df.copy()
    if group_by == "month":
        d["m"] = pd.to_datetime(d["d"]).dt.strftime("%Y-%m")
        key = "m"
    g = d.groupby(key).agg(
        inflow=("amount", lambda s: s[s > 0].sum()),
        outflow=("amount", lambda s: s[s < 0].sum()),
        net=("amount", "sum"), n=("amount", "size"),
        first=("d", "min"), last=("d", "max"),
    ).reset_index()
    g = g.sort_values(key) if group_by in ("month", "day") else g.reindex(
        g["net"].abs().sort_values(ascending=False).index)
    v = g.head(top)
    lines = [f"{GROUPS.get(group_by, 'Статья')}\tПоступления, ₽\tВыплаты, ₽\tСальдо, ₽\tОпераций\tПервая\tПоследняя"]
    lines += [f"{getattr(r, key)}\t{_fmt(r.inflow)}\t{_fmt(r.outflow)}\t{_fmt(r.net)}\t{r.n}\t"
              f"{r.first:%d.%m.%Y}\t{r.last:%d.%m.%Y}" for r in v.itertuples()]
    return (head + "\n" + "\n".join(lines)
            + f"\nСтрок: {len(g)}, показано {len(v)}. Выплаты со знаком минус. "
              "Источник — Cash Flow мэн пака.")
