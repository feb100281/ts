# gear/app/daily_sales/assistant/cards.py
"""Проверка карточек с остатком (GTIN, ТН ВЭД, документы, ОКПД2) для помощника.
Та же функция, что у кнопки в блоке «Остатки» (cards_compliance)."""
from __future__ import annotations

import threading
import time
from datetime import date, timedelta

import pandas as pd

CACHE_TTL = 30 * 60
_cache: dict = {}
_lock = threading.Lock()
CHECK_NAMES = {"gtin": "GTIN", "tnved": "ТН ВЭД", "doc": "Документы", "okpd": "ОКПД2"}


def get_df(report_date: date) -> pd.DataFrame:
    from ..cards_compliance import get_cards_check_data
    with _lock:
        hit = _cache.get(report_date)
        if hit and time.time() - hit[0] < CACHE_TTL:
            return hit[1]
        df = get_cards_check_data(report_date)
        _cache.clear()
        _cache[report_date] = (time.time(), df)
        return df


def _n(v):
    return f"{int(v or 0):,}".replace(",", " ")


def cards_check(report_date=None, view="summary", brand=None, level=None,
                check=None, top=40) -> str:
    from ..cards_compliance import CRIT, CHECK, OK
    rd = date.fromisoformat(str(report_date)[:10]) if report_date else date.today() - timedelta(days=1)
    df = get_df(rd)
    avail = df.attrs.get("avail", {})
    if brand:
        df = df[df["brand"].str.contains(str(brand).upper(), regex=False)]
    if df.empty:
        return "Нет карточек с остатком по условию."
    total_qty = df["total_qty"].sum()
    off = [CHECK_NAMES[k] for k, v in avail.items() if not v]

    def block(d):
        cards = d.groupby("nm_id")["status"].agg(
            lambda s: CRIT if (s == CRIT).any() else (CHECK if (s == CHECK).any() else OK))
        q = d.groupby("status")["total_qty"].sum()
        return [f"{st}: {_n((cards == st).sum())} карточек ({(cards == st).mean() * 100:.1f}%), "
                f"остаток {_n(q.get(st, 0))} шт ({q.get(st, 0) / d['total_qty'].sum() * 100 if d['total_qty'].sum() else 0:.1f}%)"
                for st in (CRIT, CHECK, OK)]

    lines = [f"ПРОВЕРКА КАРТОЧЕК С ОСТАТКОМ на {rd:%d.%m.%Y}: {_n(df['nm_id'].nunique())} карточек, "
             f"{_n(len(df))} размеров, остаток {_n(total_qty)} шт"
             + (f" · бренд «{brand}»" if brand else "")]
    if off:
        lines.append("Не проверялось (нет данных): " + ", ".join(off))

    if view == "summary":
        lines += block(df)
        lines.append("\nПо проверкам (карточек с проблемой: критично / проверить):")
        for k, name in CHECK_NAMES.items():
            if not avail.get(k, True):
                continue
            c = df[df[k + "_level"] == CRIT]["nm_id"].nunique()
            w = df[df[k + "_level"] == CHECK]["nm_id"].nunique()
            top_issue = (df[df[k + "_level"].isin([CRIT, CHECK])][k + "_issue"]
                         .value_counts().head(3))
            lines.append(f"{name}: {_n(c)} / {_n(w)}"
                         + ("; частые: " + "; ".join(f"{i} — {_n(n)}" for i, n in top_issue.items())
                            if len(top_issue) else ""))
    elif view == "brand":
        lines.append("Бренд\tКарточек\tКритично\tПроверить\tОстаток, шт\tОстаток в «Критично», шт")
        for b, d in df.groupby("brand"):
            cards = d.groupby("nm_id")["status"].agg(lambda s: (s == CRIT).any())
            warn = d.groupby("nm_id")["status"].agg(lambda s: (s == CHECK).any() and not (s == CRIT).any())
            lines.append(f"{b}\t{_n(len(cards))}\t{_n(cards.sum())}\t{_n(warn.sum())}\t"
                         f"{_n(d['total_qty'].sum())}\t{_n(d[d['status'] == CRIT]['total_qty'].sum())}")
    else:  # issues
        d = df[df["status"].isin([CRIT, CHECK])]
        if level in (CRIT, CHECK):
            d = d[d["status"] == level]
        if check in CHECK_NAMES:
            d = d[d[check + "_level"].isin([CRIT, CHECK])]
        d = d.sort_values(["status", "total_qty"], ascending=[True, False]).head(min(int(top or 40), 200))
        lines.append("Статус\tАртикул WB\tАртикул продавца\tБренд\tРазмер\tОстаток, шт\tПроблемы")
        for r in d.itertuples():
            issues = "; ".join(f"{CHECK_NAMES[k]}: {getattr(r, k + '_issue')}"
                               for k in CHECK_NAMES if getattr(r, k + "_issue", None))
            lines.append(f"{r.status}\t{r.nm_id}\t{r.vendor_code}\t{r.brand}\t{r.tech_size}\t"
                         f"{_n(r.total_qty)}\t{issues}")
    lines.append("\nКритично — нужно исправить до проверки WB (нет GTIN у маркируемого товара, "
                 "пустой ТН ВЭД, истёкший документ, карточка не найдена). Проверить — данные "
                 "есть, но требуют сверки. Это наша проверка данных карточек, а не статус "
                 "блокировки WB.")
    return "\n".join(lines)
