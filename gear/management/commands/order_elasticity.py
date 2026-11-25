"""Эластичность «заказы → выкупы» по категориям и проверка на артикулах. Только чтение.

    python manage.py order_elasticity                      # окно: 3 полных месяца до прошлого
    python manage.py order_elasticity --from 2026-08-01 --to 2026-10-31

k = заказы / чистые выкупы за окно: во сколько раз срок оборота остатка в выкупах длиннее,
чем в заказах (остаток в обоих сроках один и тот же). Лаг «заказ → выкуп» — по заказам
старше 45 дней. Проверка на артикулах: средний остаток (склады WB + FBS) за окно / заказы
в день → дни в заказах; / выкупы в день → дни в выкупах.
"""
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
from django.core.management.base import BaseCommand

MIN_ORDERS = 30          # артикул в проверке — от 30 заказов за окно

FLOW_SQL = """
WITH o AS (
    SELECT nm_id AS nm, COUNT(*) AS orders
    FROM pg.wb_raw.wb_orders
    WHERE order_dt::DATE BETWEEN $a AND $b
    GROUP BY 1
),
s AS (
    SELECT nm_id AS nm, SUM(CASE WHEN dtn = 'Продажа' THEN 1 ELSE -1 END) AS buys
    FROM sales.wb_raw
    WHERE quantity <> 2 AND dtn IN ('Продажа', 'Возврат')
      AND COALESCE(sop_name, '') NOT ILIKE '%оррекц%' AND COALESCE(retail_price, 0) <> 0
      AND rr_dt::DATE BETWEEN $a AND $b
    GROUP BY 1
),
st AS (
    SELECT nm, AVG(q) AS stock FROM (
        SELECT d, nm, SUM(q) AS q FROM (
            SELECT date_from::DATE AS d, nm_id AS nm, COALESCE(quantity, 0) AS q
            FROM stocks.unpacked_stocks WHERE date_from::DATE BETWEEN $a AND $b
            UNION ALL
            SELECT date_from::DATE, nm_id, COALESCE(quantity, 0)
            FROM stocks.unpacked_fbs_stocks WHERE date_from::DATE BETWEEN $a AND $b
        ) GROUP BY 1, 2
    ) GROUP BY 1
),
p AS (SELECT card_id AS nm, ANY_VALUE(COALESCE(NULLIF(TRIM(subject_name), ''), 'Не указана')) AS category,
             ANY_VALUE(UPPER(TRIM(brand))) AS brand
      FROM inventories.wb_product GROUP BY 1)
SELECT COALESCE(o.nm, s.nm) AS nm, COALESCE(o.orders, 0) AS orders, COALESCE(s.buys, 0) AS buys,
       COALESCE(st.stock, 0) AS stock, COALESCE(p.category, 'Не указана') AS category, p.brand
FROM o FULL OUTER JOIN s ON s.nm = o.nm
LEFT JOIN st ON st.nm = COALESCE(o.nm, s.nm)
LEFT JOIN p ON p.nm = COALESCE(o.nm, s.nm)
"""

LAG_SQL = """
WITH o AS (SELECT srid, order_dt::DATE AS od, nm_id AS nm FROM pg.wb_raw.wb_orders
           WHERE order_dt::DATE <= $c),
s AS (SELECT srid, MIN(rr_dt::DATE) FILTER (WHERE dtn = 'Продажа') AS bd,
             COUNT(*) FILTER (WHERE dtn = 'Возврат') AS nr
      FROM sales.wb_raw WHERE srid IN (SELECT srid FROM o) GROUP BY 1),
p AS (SELECT card_id AS nm, ANY_VALUE(COALESCE(NULLIF(TRIM(subject_name), ''), 'Не указана')) AS category
      FROM inventories.wb_product GROUP BY 1)
SELECT COALESCE(p.category, 'Не указана') AS category,
       COUNT(*) AS orders_lag,
       AVG(CASE WHEN s.bd IS NOT NULL AND COALESCE(s.nr, 0) = 0 THEN 1.0 ELSE 0 END) * 100 AS buy_pct,
       MEDIAN(s.bd - o.od) FILTER (WHERE s.bd IS NOT NULL AND COALESCE(s.nr, 0) = 0) AS lag_med,
       QUANTILE_CONT(s.bd - o.od, 0.9) FILTER (WHERE s.bd IS NOT NULL AND COALESCE(s.nr, 0) = 0) AS lag_p90
FROM o LEFT JOIN s USING (srid) LEFT JOIN p USING (nm)
GROUP BY 1
"""


class Command(BaseCommand):
    help = "Эластичность заказы → выкупы (анализ, только чтение)"

    def add_arguments(self, parser):
        parser.add_argument("--from", dest="a")
        parser.add_argument("--to", dest="b")

    def handle(self, *args, **o):
        from conns import get_duckdb_conn_with_opt
        today = date.today()
        b = date.fromisoformat(o["b"]) if o["b"] else today.replace(day=1) - timedelta(days=1)
        a = date.fromisoformat(o["a"]) if o["a"] else (b.replace(day=1) - timedelta(days=40)).replace(day=1)
        with get_duckdb_conn_with_opt(ro=True) as con:
            f = con.execute(FLOW_SQL, {"a": a, "b": b}).df()
            lag = con.execute(LAG_SQL, {"c": today - timedelta(days=45)}).df()
        days = (b - a).days + 1
        self.stdout.write(f"Окно {a:%d.%m.%Y}–{b:%d.%m.%Y} ({days} дн). Заказов {f['orders'].sum():,.0f}, "
                          f"чистых выкупов {f['buys'].sum():,.0f}, k = {f['orders'].sum() / f['buys'].sum():.2f}"
                          .replace(",", " "))

        # ---- категории
        g = f.groupby("category").agg(orders=("orders", "sum"), buys=("buys", "sum"))
        g = g.join(lag.set_index("category"))
        g["k"] = g["orders"] / g["buys"].where(g["buys"] > 0)
        g["T30"] = 30 * g["k"]
        g["T45"] = 45 * g["k"]
        g = g.sort_values("orders", ascending=False).head(20)
        out = pd.DataFrame({
            "заказов": g["orders"], "выкупов": g["buys"], "% выкупа": g["buy_pct"].round(1),
            "k": g["k"].round(2), "лаг: медиана": g["lag_med"], "лаг: 90%": g["lag_p90"],
            "заказы 30 дн → выкупы, дн": g["T30"].round(0), "заказы 45 дн → выкупы, дн": g["T45"].round(0)})
        self.stdout.write("\n1. Категории (топ-20 по заказам). k = заказы / выкупы; выкупы, дн = k × дни в заказах\n"
                          + out.to_string())

        # ---- проверка на артикулах
        x = f[(f["orders"] >= MIN_ORDERS) & (f["stock"] > 0)].copy()
        x["d_ord"] = x["stock"] / (x["orders"] / days)
        x["d_buy"] = x["stock"] / (x["buys"].where(x["buys"] > 0) / days)

        def bk(d):
            return ("1) ≤30" if d <= 30 else "2) 31–45" if d <= 45 else "3) 46–60" if d <= 60
                    else "4) 61–90" if d <= 90 else "5) >90")
        x["bucket"] = x["d_ord"].map(bk)
        t = x.groupby("bucket").agg(
            арт=("nm", "count"), остаток=("stock", "sum"),
            выкупы_медиана=("d_buy", "median"), выкупы_75=("d_buy", lambda s: s.quantile(.75)),
            доля_до_90=("d_buy", lambda s: (s <= 90).mean() * 100),
            доля_до_120=("d_buy", lambda s: (s <= 120).mean() * 100))
        self.stdout.write(f"\n2. Артикулы (от {MIN_ORDERS} заказов за окно, с остатком): {len(x)}. "
                          "Дни = средний остаток (WB + FBS) / поток в день.\n"
                          "   дни в заказах → дни в выкупах: медиана, 75%, доля артикулов ≤90 и ≤120 дней\n"
                          + t.round(1).to_string())
