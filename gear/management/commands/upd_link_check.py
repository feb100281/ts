"""Строки УПД, привязанные к карточке WB с другим артикулом продавца (только чтение).

    python manage.py upd_link_check            # сводка по УПД и брендам
    python manage.py upd_link_check --upd TS-012 --rows 50
"""
import pandas as pd
from django.core.management.base import BaseCommand

from conns import get_duckdb_conn_with_opt

SQL = """
WITH p AS (
    SELECT card_id, ANY_VALUE(UPPER(TRIM(sa_name))) AS sa
    FROM inventories.wb_product GROUP BY 1
),
own AS (   -- карточка, у которой ровно такой артикул продавца
    SELECT UPPER(TRIM(sa_name)) AS sa, MIN(card_id) AS card_id, COUNT(DISTINCT card_id) AS n
    FROM inventories.wb_product WHERE sa_name IS NOT NULL GROUP BY 1
)
SELECT d.number AS upd, d.date::DATE AS upd_date, l.brand,
       l.upd_sa_name, l.nm_id AS linked_nm, p.sa AS linked_sa,
       own.card_id AS own_nm, l.upd_qty, l.upd_price_vatless
FROM pg.public.upd_income_lines l
JOIN pg.public.cards_upddocument d ON d.id = l.upd_document_id
LEFT JOIN p ON p.card_id = l.nm_id
LEFT JOIN own ON own.sa = UPPER(TRIM(l.upd_sa_name))
WHERE l.nm_id IS NOT NULL
  AND l.upd_sa_name IS NOT NULL
  AND UPPER(TRIM(l.upd_sa_name)) <> COALESCE(p.sa, '')
"""


class Command(BaseCommand):
    help = "УПД: строки, привязанные к чужой карточке WB"

    def add_arguments(self, p):
        p.add_argument("--upd", default=None)
        p.add_argument("--rows", type=int, default=0, help="показать N строк-примеров")

    def handle(self, *a, **o):
        pd.set_option("display.width", 250)
        pd.set_option("display.max_rows", 300)
        with get_duckdb_conn_with_opt(ro=True) as con:
            df = con.execute(SQL).df()
            total = con.execute("""
                SELECT COUNT(*) AS lines, SUM(upd_qty) AS qty
                FROM pg.public.upd_income_lines WHERE nm_id IS NOT NULL""").fetchone()
        if o["upd"]:
            df = df[df["upd"].astype(str).str.contains(o["upd"], case=False)]
        df["fixable"] = df["own_nm"].notna()
        print(f"Строк УПД с привязкой к карточке: {total[0]:,.0f}, шт {total[1]:,.0f}".replace(",", " "))
        print(f"Из них привязаны к карточке с другим артикулом продавца: {len(df):,} строк, "
              f"{df['upd_qty'].sum():,.0f} шт".replace(",", " "))
        print(f"  есть своя карточка с точно таким артикулом (можно перепривязать): "
              f"{int(df['fixable'].sum()):,} строк".replace(",", " "))
        print(f"  своей карточки нет: {int((~df['fixable']).sum()):,} строк".replace(",", " "))
        if df.empty:
            return
        print("\n== По УПД")
        g = df.groupby(["upd", "upd_date"]).agg(lines=("upd_qty", "size"), qty=("upd_qty", "sum"),
                                                fixable=("fixable", "sum")).reset_index()
        print(g.sort_values("upd_date").to_string(index=False))
        print("\n== По брендам")
        b = df.groupby("brand", dropna=False).agg(lines=("upd_qty", "size"), qty=("upd_qty", "sum"),
                                                  fixable=("fixable", "sum")).reset_index()
        print(b.sort_values("lines", ascending=False).to_string(index=False))
        if o["rows"]:
            print("\n== Примеры")
            print(df.head(o["rows"])[["upd", "brand", "upd_sa_name", "linked_nm", "linked_sa",
                                      "own_nm", "upd_qty"]].to_string(index=False))
