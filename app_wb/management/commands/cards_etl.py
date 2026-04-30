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

                con.execute("CREATE SCHEMA IF NOT EXISTS cards;")                
               
                con.execute(f"""
                    CREATE VIEW IF NOT EXISTS cards.cards_raw AS
                    SELECT *
                    FROM read_parquet('{parquet_path}/cards/*.parquet', union_by_name=true);
                """)
                
                
                
                con.execute(f"""
                    CREATE TABLE IF NOT EXISTS cards.unpacked_cards AS
                    {UNPACTED_CARDS}
                """)
                
                
                cnt_cards = con.execute("SELECT COUNT(*) FROM cards.cards_raw").fetchone()[0]
                details_count = con.execute("SELECT COUNT(*) FROM cards.unpacked_cards").fetchone()[0]

                self.stdout.write(self.style.SUCCESS(f"Cards available: {cnt_cards}"))
                self.stdout.write(self.style.SUCCESS(f"Cards unpacked raws: {details_count}"))
 

        except Exception as e:
            raise CommandError(f"DuckDB error: {e}")