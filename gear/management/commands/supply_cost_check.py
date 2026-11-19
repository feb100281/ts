"""Проверка: почему у артикулов поставки WB нет себестоимости (только чтение).

    python manage.py supply_cost_check 42021852 --brand GAS --upd TS-012
"""
import pandas as pd
from django.core.management.base import BaseCommand

from conns import get_duckdb_conn_with_opt
from gear.app.daily_sales.supplies_cost.data import supply_articles


class Command(BaseCommand):
    help = "Разбор себестоимости артикулов одной поставки WB"

    def add_arguments(self, p):
        p.add_argument("sid", type=int)
        p.add_argument("--brand", default=None)
        p.add_argument("--upd", default=None, help="номер УПД для сверки")

    def handle(self, *a, **o):
        pd.set_option("display.width", 250)
        pd.set_option("display.max_columns", 30)
        pd.set_option("display.max_rows", 200)
        arts = supply_articles(o["sid"])
        if o["brand"]:
            arts = arts[arts["brand"].str.upper() == o["brand"].upper()]
        print(f"\n== Поставка {o['sid']}: строк {len(arts)}")
        print(arts[["nm", "sa", "brand", "qty", "cost_status", "no_cost_qty",
                    "upd_rows", "upd_qty", "cum_qty", "upd_last_number"]].to_string(index=False))
        nms = [int(x) for x in arts["nm"].unique()]
        if not nms:
            return
        ph = ",".join("?" * len(nms))
        with get_duckdb_conn_with_opt(ro=True) as con:
            # история поставок этих артикулов: что «съело» количество по УПД
            print("\n== Все поставки этих артикулов (FIFO по дате)")
            from gear.app.daily_sales.supplies_cost.data import _base
            b = _base()
            h = b[b["nm"].isin(nms)].sort_values(["nm", "d", "sid"])
            print(h[["nm", "sid", "d", "qty", "cum_qty", "upd_qty", "cost_status"]]
                  .to_string(index=False))
            if not o["upd"]:
                return
            n = o["upd"]
            print(f"\n== УПД {n} в DuckDB (inventories.upd_income — источник вкладки)")
            print(con.execute("""
                SELECT ud.id, ud.number, ud.date::DATE AS date, COUNT(ui.upd_document_id) AS lines,
                       COUNT(*) FILTER (WHERE ui.nm_id IS NULL) AS no_nm,
                       COUNT(*) FILTER (WHERE COALESCE(ui.upd_price_vatless, 0) = 0) AS no_price,
                       SUM(ui.upd_qty) AS qty
                FROM inventories.upd_documents ud
                LEFT JOIN inventories.upd_income ui ON ui.upd_document_id = ud.id
                WHERE CAST(ud.number AS VARCHAR) ILIKE ?
                GROUP BY 1, 2, 3""", [f"%{n}%"]).df().to_string(index=False))
            print(f"\n== Строки УПД {n} по артикулам поставки (DuckDB)")
            print(con.execute(f"""
                SELECT ui.nm_id, ui.upd_qty, ui.upd_price_vatless
                FROM inventories.upd_income ui
                JOIN inventories.upd_documents ud ON ud.id = ui.upd_document_id
                WHERE CAST(ud.number AS VARCHAR) ILIKE ? AND ui.nm_id IN ({ph})""",
                [f"%{n}%", *nms]).df().to_string(index=False))
            try:
                self._pg(con, n, o["brand"])
            except Exception as e:
                print(f"\nPostgres-сверка не выполнена: {e}")

    def _pg(self, con, n, brand):
        if True:
            print(f"\n== УПД {n} в Postgres (то, что видно в админке)")
            print(con.execute("""
                SELECT d.id, d.number, d.date, COUNT(l.id) AS lines,
                       COUNT(*) FILTER (WHERE l.nm_id IS NULL) AS no_nm,
                       COUNT(*) FILTER (WHERE COALESCE(l.upd_price_vatless, 0) = 0) AS no_price,
                       SUM(l.upd_qty) AS qty
                FROM pg.public.cards_upddocument d
                LEFT JOIN pg.public.upd_income_lines l ON l.upd_document_id = d.id
                WHERE d.number ILIKE ?
                GROUP BY 1, 2, 3""", [f"%{n}%"]).df().to_string(index=False))
            if brand:
                print(f"\n== Строки УПД {n} бренда {brand} без привязки к артикулу WB (Postgres)")
                print(con.execute("""
                    SELECT l.upd_sa_name, l.upd_title, l.upd_qty, l.upd_price_vatless
                    FROM pg.public.cards_upddocument d
                    JOIN pg.public.upd_income_lines l ON l.upd_document_id = d.id
                    WHERE d.number ILIKE ? AND l.nm_id IS NULL AND UPPER(l.brand) = UPPER(?)
                    LIMIT 30""", [f"%{n}%", brand]).df().to_string(index=False))
