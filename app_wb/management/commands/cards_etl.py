#скрипт обрабатывает карточки ранинить после подгрузки
import os
import duckdb
from duckdb import DuckDBPyConnection
import json
from django.core.management.base import BaseCommand, CommandError

from dotenv import load_dotenv

import psycopg
from psycopg.rows import dict_row
from psycopg import Connection
from psycopg.types.json import Jsonb

import pandas as pd

load_dotenv()


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

UNPACTED_CARDS = """ 
SELECT
    nm_id,

    json_extract_string(payload, '$.nmUUID') AS nm_uuid,
    json_extract_string(payload, '$.subjectName') AS subject_name,
    json_extract_string(payload, '$.vendorCode') AS vendor_code,
    json_extract_string(payload, '$.brand') AS brand,
    json_extract_string(payload, '$.title') AS title,
    json_extract_string(payload, '$.description') AS description,

    json_extract_string(payload, '$.kizMarked')::BOOLEAN AS kiz_marked,
    json_extract_string(payload, '$.subjectID')::BIGINT AS subject_id,

    -- 🔥 фото (только первая, hq)
    json_extract_string(
        json_extract(payload, '$.photos[0]'),
        '$.hq'
    ) AS photo_hq,

    -- 🔥 размеры
    json_extract_string(size_item.value, '$.chrtID')::BIGINT AS chrt_id,
    json_extract_string(size_item.value, '$.techSize') AS tech_size,
    json_extract_string(size_item.value, '$.wbSize') AS wb_size,
    json_extract_string(sku_item.value, '$') AS sku,

    -- 🔥 характеристики
    cert_end.value AS cert_end_date,
    tnved.value AS tnved,
    gender.value AS gender,
    vat.value::DOUBLE AS vat_rate,
    komplekt.value AS komplekt,
    declaration.value AS declaration_number,
    country.value as origin_country,
    color.value AS color,
    

    json_extract_string(payload, '$.createdAt') AS created_at,
    json_extract_string(payload, '$.updatedAt') AS updated_at

FROM cards.cards_raw

-- размеры
CROSS JOIN json_each(json_extract(payload, '$.sizes')) AS size_item
CROSS JOIN json_each(json_extract(size_item.value, '$.skus')) AS sku_item

-- характеристики
LEFT JOIN LATERAL (
    SELECT json_extract_string(ch.value, '$.value[0]') AS value
    FROM json_each(json_extract(payload, '$.characteristics')) AS ch
    WHERE json_extract_string(ch.value, '$.name') = 'Дата окончания действия сертификата/декларации'
    LIMIT 1
) cert_end ON TRUE

LEFT JOIN LATERAL (
    SELECT json_extract_string(ch.value, '$.value[0]') AS value
    FROM json_each(json_extract(payload, '$.characteristics')) AS ch
    WHERE json_extract_string(ch.value, '$.name') = 'ТНВЭД'
    LIMIT 1
) tnved ON TRUE

LEFT JOIN LATERAL (
    SELECT json_extract_string(ch.value, '$.value[0]') AS value
    FROM json_each(json_extract(payload, '$.characteristics')) AS ch
    WHERE json_extract_string(ch.value, '$.name') = 'Пол'
    LIMIT 1
) gender ON TRUE

LEFT JOIN LATERAL (
    SELECT json_extract_string(ch.value, '$.value[0]') AS value
    FROM json_each(json_extract(payload, '$.characteristics')) AS ch
    WHERE json_extract_string(ch.value, '$.name') = 'Ставка НДС'
    LIMIT 1
) vat ON TRUE

LEFT JOIN LATERAL (
    SELECT json_extract_string(ch.value, '$.value[0]') AS value
    FROM json_each(json_extract(payload, '$.characteristics')) AS ch
    WHERE json_extract_string(ch.value, '$.name') = 'Комплектация'
    LIMIT 1
) komplekt ON TRUE

LEFT JOIN LATERAL (
    SELECT json_extract_string(ch.value, '$.value[0]') AS value
    FROM json_each(json_extract(payload, '$.characteristics')) AS ch
    WHERE json_extract_string(ch.value, '$.name') = 'Номер декларации соответствия'
    LIMIT 1
) declaration ON TRUE

LEFT JOIN LATERAL (
    SELECT json_extract_string(ch.value, '$.value[0]') AS value
    FROM json_each(json_extract(payload, '$.characteristics')) AS ch
    WHERE json_extract_string(ch.value, '$.name') = 'Страна производства'
    LIMIT 1
) country ON TRUE

LEFT JOIN LATERAL (
    SELECT json_extract_string(ch.value, '$.value[0]') AS value
    FROM json_each(json_extract(payload, '$.characteristics')) AS ch
    WHERE json_extract_string(ch.value, '$.name') = 'Цвет'
    LIMIT 1
) color ON TRUE

"""

PIDS = """
CREATE OR REPLACE TABLE cards.pids as
WITH a AS (
    SELECT DISTINCT
        nm_id,
        vendor_code AS sa_name
    FROM analytics.cards.unpacked_cards
),
fin as (
SELECT
    c.nm_id,
    p.nm_id AS nm_pid,
    c.sa_name,
    p.sa_name AS sa_pid
FROM a c
LEFT JOIN a p
    ON left(c.sa_name, 10) = p.sa_name
   AND try_cast(left(c.sa_name,10) AS BIGINT) IS NOT NULL
)
select 
nm_id::bigint as nm_id,
COALESCE(nm_pid,nm_id)::bigint as nm_pid,
sa_name::text as sa_name,
coalesce(sa_pid, sa_name)::text as sa_pid,
case when nm_id::bigint <> COALESCE(nm_pid,nm_id)::bigint 
then true else false end has_parent
from fin
"""

SIZES = """
create or replace table cards.sizes as
select distinct 
nm_id,
chrt_id,
tech_size
from cards.unpacked_cards
"""

PRODUCTS = """
create or replace table cards.product as
select 
t.nm_id,
t.nm_pid,
t.sa_name,
t.sa_pid,
s.title,
s.komplekt as alternative_name, 
s.subject_name,
s.brand,
s.subject_id::bigint as subject_id,
t.has_parent,
s.vat_rate::double as vat_rate,
case when s.vat_rate is null then false else true end as discount_vat,
s.tnved::text as tnved,
s.gender,
s.origin_country,
s.photo_hq,
try_strptime(s.cert_end_date, '%d.%m.%Y')::date as cert_end_date,
s.created_at::timestamp as created_at,
s.updated_at::timestamp as updated_at,
list(distinct s.tech_size order by s.tech_size) as available_sizes
from cards.pids t
left join cards.unpacked_cards s on s.nm_id::bigint = t.nm_id
group by 
t.nm_id,
t.nm_pid,
t.sa_name,
t.sa_pid,
s.title,
s.komplekt,
s.subject_name,
s.brand,
s.subject_id,
t.has_parent,
s.vat_rate,
discount_vat,
cert_end_date,
s.tnved,
s.gender,
s.origin_country,
s.photo_hq,
s.created_at,
s.updated_at

"""


# Вставляем корточки и меняем если что

def upsert_cards_raw(rows):

    sql = """
        INSERT INTO wb_cards_raw (
            nm_id,
            payload,
            loaded_at
        )
        VALUES (
            %s,
            %s,
            %s
        )
        ON CONFLICT (nm_id)
        DO UPDATE SET
            payload = EXCLUDED.payload,
            loaded_at = EXCLUDED.loaded_at
    """

    data = []

    for nm_id, payload, loaded_at in rows:

        data.append(
            (
                int(nm_id),
                Jsonb(json.loads(payload)),
                loaded_at
            )
        )

    with connect_db() as conn:

        with conn.cursor() as cur:

            cur.executemany(sql, data)

        conn.commit()

    return len(data)

def upsert_wb_sizes():
    sql = """
        INSERT INTO wb_sizes (
            chrt_id,
            nm_id,
            tech_size
        )
        SELECT
            (size_item->>'chrtID')::bigint AS chrt_id,
            r.nm_id,
            size_item->>'techSize' AS tech_size
        FROM wb_cards_raw r
        CROSS JOIN LATERAL jsonb_array_elements(r.payload->'sizes') AS size_item
        WHERE size_item ? 'chrtID'
        ON CONFLICT (chrt_id)
        DO UPDATE SET
            tech_size = EXCLUDED.tech_size
        WHERE wb_sizes.tech_size IS DISTINCT FROM EXCLUDED.tech_size
    """

    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            changed = cur.rowcount

        conn.commit()

    return changed

def upsert_wb_barcodes():
    sql = """
        INSERT INTO wb_barcodes (
            barcode,
            chrt_id
        )
        SELECT
            barcode_item AS barcode,
            (size_item->>'chrtID')::bigint AS chrt_id
        FROM wb_cards_raw r
        CROSS JOIN LATERAL jsonb_array_elements(r.payload->'sizes') AS size_item
        CROSS JOIN LATERAL jsonb_array_elements_text(size_item->'skus') AS barcode_item
        WHERE
            size_item ? 'chrtID'
            AND size_item ? 'skus'
        ON CONFLICT (barcode)
        DO UPDATE SET
            chrt_id = EXCLUDED.chrt_id
        WHERE wb_barcodes.chrt_id IS DISTINCT FROM EXCLUDED.chrt_id
    """

    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            changed = cur.rowcount

        conn.commit()

    return changed

def upsert_wb_barcodes():

    sql = """
        INSERT INTO wb_barcodes (
            barcode,
            chrt_id
        )
        SELECT DISTINCT
            barcode_item AS barcode,
            (size_item->>'chrtID')::bigint AS chrt_id

        FROM wb_cards_raw r

        CROSS JOIN LATERAL jsonb_array_elements(r.payload->'sizes') AS size_item

        CROSS JOIN LATERAL jsonb_array_elements_text(
            size_item->'skus'
        ) AS barcode_item

        WHERE
            size_item ? 'chrtID'
            AND size_item ? 'skus'
            AND barcode_item IS NOT NULL
            AND barcode_item <> ''

        ON CONFLICT (barcode, chrt_id)
        DO NOTHING
    """

    with connect_db() as conn:

        with conn.cursor() as cur:

            cur.execute(sql)

            inserted = cur.rowcount

        conn.commit()

    return inserted


def upsert_wb_products(rows):

    sql = """
        INSERT INTO wb_products (
            nm_id,
            nm_pid,
            sa_name,
            sa_pid,
            title,
            alternative_name,
            subject_name,
            brand,
            subject_id,
            has_parent,
            vat_rate,
            discount_vat,
            tnved,
            gender,
            origin_country,
            photo_hq,
            cert_end_date,
            wb_created_at,
            wb_updated_at,
            available_sizes,
            updated_at
        )
        VALUES (
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s,
            now()
        )
        ON CONFLICT (nm_id)
        DO UPDATE SET
            nm_pid = EXCLUDED.nm_pid,
            sa_name = EXCLUDED.sa_name,
            sa_pid = EXCLUDED.sa_pid,
            title = EXCLUDED.title,
            alternative_name = EXCLUDED.alternative_name,
            subject_name = EXCLUDED.subject_name,
            brand = EXCLUDED.brand,
            subject_id = EXCLUDED.subject_id,
            has_parent = EXCLUDED.has_parent,
            vat_rate = EXCLUDED.vat_rate,
            discount_vat = EXCLUDED.discount_vat,
            tnved = EXCLUDED.tnved,
            gender = EXCLUDED.gender,
            origin_country = EXCLUDED.origin_country,
            photo_hq = EXCLUDED.photo_hq,
            cert_end_date = EXCLUDED.cert_end_date,
            wb_created_at = EXCLUDED.wb_created_at,
            wb_updated_at = EXCLUDED.wb_updated_at,
            available_sizes = EXCLUDED.available_sizes,
            updated_at = now()
    """

    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.executemany(sql, rows)

        conn.commit()

    return len(rows)

class Command(BaseCommand):
    help = "THIS IS THE WB CARDS ETL"

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

                con.execute("CREATE SCHEMA IF NOT EXISTS cards;")                
               
                con.execute(f"""
                    CREATE VIEW IF NOT EXISTS cards.cards_raw AS
                    SELECT *
                    FROM read_parquet('{parquet_path}/cards/*.parquet', union_by_name=true);
                """)
                
                con.execute(f"""
                    create or replace table cards.unpacked_cards AS
                    {UNPACTED_CARDS}
                """)
                
                con.execute(PIDS)
                
                con.execute(SIZES)
                
                con.execute(PRODUCTS)
                
                cnt_double = con.sql("SELECT nm_id, count(*) as cnt from cards.product group by nm_id having cnt > 1")
                                
                cnt_cards = con.execute("SELECT COUNT(*) FROM cards.cards_raw").fetchone()[0]
                details_count = con.execute("SELECT COUNT(*) FROM cards.unpacked_cards").fetchone()[0]
                pids_count = con.execute("SELECT COUNT(*) FROM cards.pids where has_parent = true").fetchone()[0]
                size_count = con.execute("SELECT COUNT(distinct tech_size) from cards.sizes").fetchone()[0]
                chrid_count = con.execute("SELECT COUNT(*) from cards.sizes").fetchone()[0]
                product_cnt = con.execute("SELECT COUNT(*) from cards.product").fetchone()[0]

                self.stdout.write(self.style.SUCCESS(f"Cards available: {cnt_cards}"))
                self.stdout.write(self.style.SUCCESS(f"Cards unpacked raws: {details_count}"))
                self.stdout.write(self.style.SUCCESS(f"Pids created: {pids_count}"))
                self.stdout.write(self.style.SUCCESS(f"SIZES created: {size_count} sizes on {chrid_count} nm_ids"))
                if cnt_double:
                   self.stdout.write(self.style.ERROR(f"ЗАДВОЯШКИ В КАРТОЧКАХ")) 
                else:
                   self.stdout.write(self.style.SUCCESS(f"UNIQUE cards created: {product_cnt}")) 
                
                rows = con.execute("""
                        SELECT
                            nm_id,
                            payload,
                            _loaded_at
                        FROM cards.cards_raw
                    """).fetchall()
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Rows fetched from DuckDB: {len(rows)}"
                    )
                )
                count = upsert_cards_raw(rows)
                self.stdout.write(
                    self.style.SUCCESS(
                        f"UPSERTED: {count}"
                    )
                )
                changed_sizes = upsert_wb_sizes()

                self.stdout.write(
                    self.style.SUCCESS(
                        f"WbSizes inserted/updated: {changed_sizes}"
                    )
                )  
                
                inserted_barcodes = upsert_wb_barcodes()

                self.stdout.write(
                    self.style.SUCCESS(
                        f"WbBarcodes inserted: {inserted_barcodes}"
                    )
                ) 
                
                rows = con.execute("""
                    SELECT
                        nm_id,
                        nm_pid,
                        sa_name,
                        sa_pid,
                        title,
                        alternative_name,
                        subject_name,
                        brand,
                        subject_id,
                        has_parent,
                        vat_rate,
                        discount_vat,
                        tnved,
                        gender,
                        origin_country,
                        photo_hq,
                        cert_end_date,
                        created_at,
                        updated_at,
                        available_sizes
                    FROM cards.product
                """).fetchall()

                count_details = upsert_wb_products(rows)   
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f"details inserted: {count_details}"
                    )
                )          
                
        except Exception as e:
            raise CommandError(f"DuckDB error: {e}")