"""Строки УПД без NM_ID: есть ли теперь карточка WB с таким артикулом (только чтение).

    python manage.py upd_nm_match            # все УПД
    python manage.py upd_nm_match --upd TS-013
"""
import pandas as pd
from django.core.management.base import BaseCommand

from conns import get_duckdb_conn_with_opt

SQL = """
WITH l AS (
    SELECT d.number AS upd, l.id AS line_id, l.brand, l.upd_sa_name, l.upd_size, l.upd_qty
    FROM pg.public.upd_income_lines l
    JOIN pg.public.cards_upddocument d ON d.id = l.upd_document_id
    WHERE l.nm_id IS NULL AND d.number ILIKE ?
),
p AS (
    SELECT UPPER(TRIM(sa_name)) AS sa, MIN(card_id) AS card_id, COUNT(DISTINCT card_id) AS cards
    FROM pg.public.wb_products WHERE sa_name IS NOT NULL GROUP BY 1
),
u AS (
    SELECT TRY_CAST(card_id AS BIGINT) AS card_id, MAX(TRY_CAST(usk AS BIGINT)) AS usk
    FROM inventories.usk GROUP BY 1
)
SELECT l.*, p.card_id, p.cards, u.usk
FROM l
LEFT JOIN p ON p.sa = UPPER(TRIM(l.upd_sa_name))
LEFT JOIN u ON u.card_id = p.card_id
ORDER BY l.upd, l.upd_sa_name, l.upd_size
"""


class Command(BaseCommand):
    help = "УПД: строки без NM_ID и найденные для них карточки WB"

    def add_arguments(self, p):
        p.add_argument("--upd", default="")

    def handle(self, *a, **o):
        pd.set_option("display.width", 250)
        pd.set_option("display.max_rows", 200)
        with get_duckdb_conn_with_opt(ro=True) as con:
            df = con.execute(SQL, [f"%{o['upd']}%"]).df()
        if df.empty:
            print("Строк без NM_ID нет")
            return
        found = df["card_id"].notna()
        print(f"Строк без NM_ID: {len(df)}; карточка по артикулу найдена: {int(found.sum())}; "
              f"не найдена: {int((~found).sum())}; из найденных без USK в словаре: "
              f"{int((found & df['usk'].isna()).sum())}")
        print(df[["upd", "upd_sa_name", "upd_size", "upd_qty", "card_id", "cards", "usk"]]
              .to_string(index=False))
