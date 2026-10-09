### Тут синхронизируем notebooks с сервера
### Запуская как python manage.py notebooks

import os
import duckdb
from django.core.management.base import BaseCommand, CommandError

from dotenv import load_dotenv



load_dotenv()


DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME")

REPORT_STOCK_NOTEBOOK = """
CREATE SCHEMA IF NOT EXISTS reports_stocks;

-- Вьюха по остаткам по номенклатурам
CREATE OR REPLACE VIEW reports_stocks.stocks_by_product as
select 
x.date_from,
x.nm_id,
p.sa_name,
p.subject_name,
p.gender,
p.title,
list(concat(x.qty,' шт -> ', s.tech_size)) as available_sizes,
sum(x.qty) as qty
from(
select
t.date_from,
t.nm_id,
t.chrt_id,
sum(quantity+in_way_to_client+in_way_from_client) as qty
from stocks.unpacked_stocks t
group by t.date_from,
t.nm_id,
t.chrt_id
) x
left join cards.product p on p.nm_id = x.nm_id
left join cards.sizes s on s.chrt_id = x.chrt_id
group by x.date_from,
x.nm_id,
p.sa_name,
p.subject_name,
p.gender,
p.title;

-- Вьюха по категориям и и полам
CREATE OR REPLACE view  reports_stocks.stocks_by_cats as 
WITH a AS (
    SELECT 
        gender,
        subject_name,
        SUM(qty) AS qty
    FROM reports_stocks.stocks_by_product
    where date_from =  '2026-04-30'
    GROUP BY 
        gender,
        subject_name
)
SELECT 
    subject_name,
    LIST(
        CONCAT(
            COALESCE(gender::text, 'без пола'),
            ' -> ',
            qty::text,
            ' шт'
        )
    ) AS list_gender,
    SUM(qty) AS total_qty
FROM a
GROUP BY subject_name
order by total_qty desc;
"""

query = """
WITH a AS (
    SELECT 
        COALESCE(gender,'Пол не указан') as gender,
        subject_name,
        SUM(qty) AS qty
    FROM reports_stocks.stocks_by_product
    where date_from =  '2026-04-30'
    GROUP BY 
        gender,
        subject_name
)
SELECT 
    subject_name as 'категория',
    LIST(
        CONCAT(
            COALESCE(gender::text, 'без пола'),
            ' -> ',
            qty::text,
            ' шт'
        )
    ) AS 'разбивка_по_полу',
    SUM(qty) as 'всего'
FROM a
GROUP BY subject_name
order by total_qty desc;
           
        """



class Command(BaseCommand):
    help = "Import NOTEBOKKS AND VIEWS"

    def handle(self, *args, **options):
        db_path = os.getenv("DUCKDB_PATH")
        parquet_path = os.getenv("PARQUET_PATH")

        if not db_path:
            raise CommandError("DUCKDB_PATH is not set")

        if not parquet_path:
            raise CommandError("PARQUET_PATH is not set")

        self.stdout.write(f"DuckDB: {db_path}")
        self.stdout.write(f"Parquet path: {parquet_path}")

        try:
            with duckdb.connect(db_path) as con:
                
                con.execute(REPORT_STOCK_NOTEBOOK)      
                
                self.stdout.write(self.style.SUCCESS("ALL NOTEBOOKS UPDATED"))
                
        except Exception as e:
            raise CommandError(f"DuckDB error: {e}")