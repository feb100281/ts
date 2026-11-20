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
                SELECT ui.nm_id, COUNT(*) AS lines, SUM(ui.upd_qty) AS qty,
                       MIN(ui.upd_price_vatless) AS price_min, MAX(ui.upd_price_vatless) AS price_max
                FROM inventories.upd_income ui
                JOIN inventories.upd_documents ud ON ud.id = ui.upd_document_id
                WHERE CAST(ud.number AS VARCHAR) ILIKE ? AND ui.nm_id IN ({ph})
                GROUP BY 1 ORDER BY 1""",
                [f"%{n}%", *nms]).df().to_string(index=False))
            red = arts[arts["cost_status"].str.startswith("🔴")]
            if len(red):
                self._by_sa(con, red)
            try:
                self._pg(con, n, o["brand"])
            except Exception as e:
                print(f"\nPostgres-сверка не выполнена: {e}")

    def _by_sa(self, con, red):
        """Ищем красные артикулы во всех УПД по артикулу продавца."""
        sas = [str(x) for x in red["sa"].unique() if x]
        if not sas:
            return
        ph = ",".join("?" * len(sas))
        print("\n== Красные артикулы: есть ли такой артикул продавца в каких-либо УПД (Postgres)")
        df = con.execute(f"""
            SELECT l.upd_sa_name AS sa, d.number AS upd, d.date,
                   COUNT(*) AS lines, SUM(l.upd_qty) AS qty,
                   STRING_AGG(DISTINCT CAST(l.nm_id AS VARCHAR), ', ') AS linked_nm
            FROM pg.public.upd_income_lines l
            JOIN pg.public.cards_upddocument d ON d.id = l.upd_document_id
            WHERE l.upd_sa_name IN ({ph})
            GROUP BY 1, 2, 3 ORDER BY 1, 3""", sas).df()
        found = set(df["sa"]) if len(df) else set()
        print(df.to_string(index=False) if len(df) else "ни одной строки")
        miss = [x for x in sas if x not in found]
        print(f"\nНе найдено ни в одном УПД: {len(miss)} из {len(sas)}")
        if miss:
            # та же модель (первые две части артикула) в других цветах/размерах
            models = sorted({"-".join(x.split("-")[:2]) for x in miss})
            cond = " OR ".join(["l.upd_sa_name LIKE ?"] * len(models))
            mm = con.execute(f"""
                SELECT SPLIT_PART(l.upd_sa_name, '-', 1) || '-' || SPLIT_PART(l.upd_sa_name, '-', 2) AS model,
                       STRING_AGG(DISTINCT l.upd_sa_name, ', ') AS sa_in_upd
                FROM pg.public.upd_income_lines l
                WHERE {cond}
                GROUP BY 1 ORDER BY 1""", [m + "-%" for m in models]).df()
            print("\n== Та же модель в УПД, но другие цвета (для ненайденных)")
            print(mm.to_string(index=False) if len(mm) else "моделей нет в УПД")

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
