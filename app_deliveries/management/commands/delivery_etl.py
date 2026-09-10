import os
import duckdb
from duckdb import DuckDBPyConnection
import json
from django.core.management.base import BaseCommand, CommandError

from dotenv import load_dotenv

import psycopg
from psycopg.rows import dict_row
from psycopg import Connection
import pandas as pd

load_dotenv()

from inventories.models import Delivery, Lot


DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME")


def connect_db():
    return psycopg.connect(
        dbname=os.getenv("DB_NAME"),  # DB_NAME
        user=os.getenv("DB_USER"),  # DB_USER
        password=os.getenv("DB_PASSWORD"),  # DB_PASSWORD
        host=os.getenv("DB_HOST", "localhost"),  # DB_HOST
        port=os.getenv("DB_PORT", "5432"),  # DB_PORT
        connect_timeout=10,
    )


# --------
# Запросы
# --------

MATCHING_CARDS = """
-- делаем вью для матчинга карточек
CREATE OR REPLACE VIEW deliveries.matching_cards as
with a as (
select 
t.sa_pid,
list(DISTINCT t.sa_name order by t.sa_name) as sa_lists,
list(DISTINCT t.title order by t.title) as sa_titles,
list(DISTINCT t.gender order by t.gender) available_genders,
list(DISTINCT lower(t.gender) order by lower(t.gender)) available_genders_l,
list(DISTINCT c.brand order by c.brand) as brand_list,
list(DISTINCT lower(c.brand) order by lower(c.brand)) as brand_list_l,
list(DISTINCT c.color order by c.color) as available_colors,
list(DISTINCT lower(c.color) order by lower(c.color)) as available_colors_l,

list(DISTINCT c.tech_size order by c.tech_size) as available_sizes,
list(DISTINCT lower(c.tech_size) order by lower(c.tech_size)) as available_sizes_l
from cards.product t
left join cards.unpacked_cards c on c.nm_id = t.nm_id
group by 
t.sa_pid
)

select 
t.delivery_id,
t.sa_pid as sa_file,
s.sa_pid as sa_cards,
s.sa_lists,
t.name_file,
s.sa_titles,
length(
    list_filter(
        string_split(
            regexp_replace(lower(t.name_file), '[^a-zа-яё0-9]+', ' ', 'g'),
            ' '
        ),
        w ->
            length(w) > 2
            AND length(
                list_filter(
                    s.sa_titles,
                    x ->
                        regexp_replace(lower(x), '[^a-zа-яё0-9]+', ' ', 'g')
                        LIKE '%' || w || '%'
                )
            ) > 0
    )
) > 0 AS match_name,
t.size_file,
s.available_sizes,
list_contains(s.available_sizes_l, trim(lower(t.size_file))) as match_size,
t.color_file,
s.available_colors,
list_contains(s.available_colors_l, trim(lower(t.color_file))) as match_color,
t.gender_file,
s.available_genders,
list_contains(s.available_genders_l, trim(lower(t.gender_file))) as match_gender,
t.brand as brand_file,
s.brand_list,
list_contains(s.brand_list_l, trim(lower(t.brand))) as match_brand,
qty

from deliveries.deliveries_raw t
left join a s on s.sa_pid = t.sa_pid

"""

MARKING_ERRORS = """ 
CREATE OR REPLACE VIEW deliveries.marking_errors as 

select  
delivery_id,
'Цвет' as reason,
false as critical,
sa_file,
sa_cards,
sa_lists,
name_file,
sa_titles,
color_file as attr,
available_colors as available_attr,
sum(qty::double) as qty
from deliveries.matching_cards
where match_color = false and sa_cards is not null
group by 
delivery_id,
sa_file,
sa_cards,
sa_lists,
name_file,
sa_titles,
color_file,
available_colors

union all

select 
delivery_id,
'Размер' as reason,
false as critical,
sa_file,
sa_cards,
sa_lists,
name_file,
sa_titles,
size_file as attr,
available_sizes as avalable_attr,
sum(qty::double) as qty
from deliveries.matching_cards
where match_size = false and sa_cards is not null
group by 
delivery_id,
sa_file,
sa_cards,
sa_lists,
name_file,
sa_titles,
size_file,
available_sizes

union all

select 
delivery_id,
'Наименование' as reason,
true as critical,
sa_file,
sa_cards,
sa_lists,
name_file,
sa_titles,
name_file as attr,
sa_titles as avalable_attr,
sum(qty::double) as qty
from deliveries.matching_cards
where match_name = false and sa_cards is not null
group by 
delivery_id,
sa_file,
sa_cards,
sa_lists,
name_file,
sa_titles


union all

select 
delivery_id,
'НЕТ КАРТОЧКИ' as reason,
true as critical,
sa_file,
null::text as sa_cards,
null::text as sa_lists,
name_file,
null as sa_titles,
name_file as attr,
null as avalable_attr,
sum(qty::double) as qty
from deliveries.matching_cards
where sa_cards is null
group by 
delivery_id,
sa_file,
name_file
"""



class Command(BaseCommand):
    help = "Initialize DuckDB views for WB parquet"

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

                con.execute("CREATE SCHEMA IF NOT EXISTS deliveries;") 
                
                delivery_df = pd.DataFrame(
                    list(Delivery.objects.all().values())
                )

                lot_df = pd.DataFrame(
                    list(Lot.objects.all().values())
                )

                # =========================
                # в DuckDB
                # =========================
                con.register("delivery_df", delivery_df)
                con.register("lot_df", lot_df)

                con.execute(f"""
                    CREATE VIEW IF NOT EXISTS deliveries.deliveries_raw AS
                    SELECT *
                    FROM read_parquet('{parquet_path}/deliveries/*.parquet', union_by_name=true);
                """)
                
                
                con.execute("""
                    CREATE OR REPLACE TABLE deliveries.delivery AS
                    SELECT * FROM delivery_df;
                """)

                con.execute("""
                    CREATE OR REPLACE TABLE deliveries.lot AS
                    SELECT * FROM lot_df;
                """)
                
                con.execute(MATCHING_CARDS)
                con.execute(MARKING_ERRORS)               
                   
                
                self.stdout.write(self.style.SUCCESS("ALL DELIVERIES CREATED"))
                
        except Exception as e:
            raise CommandError(f"DuckDB error: {e}")