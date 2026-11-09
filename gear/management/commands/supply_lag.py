"""Связь «заказы → выкупы» по поставкам WB. Только чтение, ничего не пишет.

    python manage.py supply_lag

1) Судьба заказов старше 45 дней: доля выкупа (продажа без возврата по srid), лаг
   «заказ → выкуп» (дни: медиана, 75%, 90%) — всего и по категориям.
2) Поставки с полной историей заказов (приняты не раньше начала заказов + 2 дня и не
   позже 90 дней назад): дни до 100% принятого в заказах и до 90% в выкупах.
"""
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
from django.core.management.base import BaseCommand

BUY_SHARE = 0.9          # «выкуплена» — выкуплено 90% принятого
HORIZON = 90             # окно наблюдения выкупов, дней


ORDERS_SQL = """
WITH o AS (
    SELECT srid, order_dt::DATE AS od, income_id, nm_id, COALESCE(subject, '') AS subject
    FROM pg.wb_raw.wb_orders
),
s AS (
    SELECT srid,
           MIN(rr_dt::DATE) FILTER (WHERE dtn = 'Продажа') AS bd,
           COUNT(*) FILTER (WHERE dtn = 'Возврат') AS nr
    FROM sales.wb_raw
    WHERE srid IN (SELECT srid FROM o)
    GROUP BY 1
)
SELECT o.*, s.bd, COALESCE(s.nr, 0) AS nr
FROM o LEFT JOIN s USING (srid)
"""

SUPPLY_SQL = """
WITH s AS (
    SELECT supply_id AS sid,
           TRY_CAST(LEFT(COALESCE(NULLIF(json_extract_string(row_json::VARCHAR, '$.factDate'), ''),
                                  json_extract_string(row_json::VARCHAR, '$.supplyDate')), 10) AS DATE) AS fact
    FROM pg.wb_raw.wb_supplies),
g AS (
    SELECT supply_id AS sid,
           SUM(COALESCE(TRY_CAST(json_extract_string(row_json::VARCHAR, '$.acceptedQuantity') AS DOUBLE), 0)) AS acc
    FROM pg.wb_raw.wb_supply_goods GROUP BY 1)
SELECT s.sid, s.fact, g.acc FROM s JOIN g USING (sid) WHERE g.acc > 0 AND s.fact IS NOT NULL
"""


def _q(x, q):
    x = x.dropna()
    return round(float(x.quantile(q)), 1) if len(x) else None


class Command(BaseCommand):
    help = "Заказы → выкупы по поставкам WB (анализ, только чтение)"

    def handle(self, *args, **o):
        from conns import get_duckdb_conn_with_opt
        with get_duckdb_conn_with_opt(ro=True) as con:
            od = con.execute(ORDERS_SQL).df()
            sup = con.execute(SUPPLY_SQL).df()
        od["od"] = pd.to_datetime(od["od"])
        od["bd"] = pd.to_datetime(od["bd"])
        od["bought"] = od["bd"].notna() & (od["nr"] == 0)
        od["lag"] = (od["bd"] - od["od"]).dt.days.where(od["bought"])
        today = pd.Timestamp(date.today())
        first = od["od"].min()
        self.stdout.write(f"Заказы в базе: {len(od)}, с {first:%d.%m.%Y} по {od['od'].max():%d.%m.%Y}")

        # ---- 1. судьба заказов
        old = od[od["od"] <= today - timedelta(days=45)]
        ret = (old["bd"].notna() & (old["nr"] > 0)).mean() * 100
        self.stdout.write(f"\n1. Заказы старше 45 дней: {len(old)}")
        self.stdout.write(f"   выкуплено (без возврата): {old['bought'].mean() * 100:.1f}%; "
                          f"выкуп и потом возврат: {ret:.1f}%; не выкуплено: "
                          f"{(old['bd'].isna()).mean() * 100:.1f}%")
        self.stdout.write(f"   дней от заказа до выкупа: медиана {_q(old['lag'], .5)}, "
                          f"75% — до {_q(old['lag'], .75)}, 90% — до {_q(old['lag'], .9)}")
        cat = (old.groupby("subject").agg(orders=("srid", "count"), buy=("bought", "mean"),
                                          med=("lag", "median"),
                                          p90=("lag", lambda x: x.quantile(.9)))
               .sort_values("orders", ascending=False).head(12))
        cat["buy"] = (cat["buy"] * 100).round(1)
        self.stdout.write("   по категориям (топ-12 по заказам): заказов / % выкупа / медиана / 90%\n"
                          + cat.round(1).to_string())

        # ---- 2. поставки
        sup["fact"] = pd.to_datetime(sup["fact"])
        sup = sup[(sup["fact"] >= first + timedelta(days=2))
                  & (sup["fact"] <= today - timedelta(days=HORIZON))]
        rows = []
        by = {k: g for k, g in od[od["income_id"] > 0].groupby("income_id")}
        for r in sup.itertuples(index=False):
            g = by.get(r.sid)
            if g is None or g.empty:
                rows.append((r.sid, r.fact, r.acc, 0, None, None, 0.0))
                continue
            age_o = (g["od"] - r.fact).dt.days.sort_values()
            n_o = len(age_o)
            d_ord = int(age_o.iloc[int(r.acc) - 1]) if n_o >= r.acc else None
            b = g[g["bought"]]
            age_b = (b["bd"] - r.fact).dt.days.sort_values()
            need = int(round(r.acc * BUY_SHARE))
            d_buy = int(age_b.iloc[need - 1]) if need >= 1 and len(age_b) >= need else None
            b90 = (age_b <= HORIZON).sum() / r.acc * 100
            rows.append((r.sid, r.fact, r.acc, n_o, d_ord, d_buy, b90))
        t = pd.DataFrame(rows, columns=["sid", "fact", "acc", "orders", "d_ord", "d_buy", "b90"])
        self.stdout.write(f"\n2. Поставки, принятые {first + timedelta(days=2):%d.%m}–"
                          f"{today - timedelta(days=HORIZON):%d.%m.%Y}: {len(t)}, принято "
                          f"{t['acc'].sum():,.0f} шт; заказов по ним {t['orders'].sum():,.0f}"
                          .replace(",", " "))

        def bucket(d):
            if d is None or pd.isna(d):
                return "6) не заказали целиком"
            return ("1) ≤30" if d <= 30 else "2) 31–45" if d <= 45 else "3) 46–60" if d <= 60
                    else "4) 61–90" if d <= 90 else "5) >90")
        t["bucket"] = t["d_ord"].map(bucket)
        rep = t.groupby("bucket").agg(
            supplies=("sid", "count"), units=("acc", "sum"),
            buy_med=("d_buy", "median"),
            buy_p75=("d_buy", lambda x: x.quantile(.75)),
            done90=("d_buy", lambda x: (x.notna() & (x <= HORIZON)).mean() * 100),
            b90_avg=("b90", "mean"))
        rep.columns = ["поставок", "принято шт", f"дней до {int(BUY_SHARE*100)}% выкупа: медиана",
                       "75%", f"% поставок, выкупленных на {int(BUY_SHARE*100)}% за {HORIZON} дн",
                       f"выкуплено за {HORIZON} дн, % принятого (среднее)"]
        self.stdout.write("   за сколько дней поставку заказали целиком → выкупы\n"
                          + rep.round(1).to_string())
