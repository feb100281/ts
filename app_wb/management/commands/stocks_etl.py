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

UNPACKED_STOCKS = """
CREATE OR REPLACE TABLE stocks.unpacked_stocks as
SELECT
    _loaded_at::date as date_from,
    nm_id,
    (payload::JSON ->> 'chrtId')::BIGINT AS chrt_id,
    (payload::JSON ->> 'warehouseId')::BIGINT AS warehouse_id,
    payload::JSON ->> 'warehouseName' AS warehouse_name,
    payload::JSON ->> 'regionName' AS region_name,
    (payload::JSON ->> 'quantity')::BIGINT AS quantity,
    (payload::JSON ->> 'inWayToClient')::BIGINT AS in_way_to_client,
    (payload::JSON ->> 'inWayFromClient')::BIGINT AS in_way_from_client
from stocks.stocks_raw
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

                con.execute("CREATE SCHEMA IF NOT EXISTS stocks;")                
               
                con.execute(f"""
                    CREATE VIEW IF NOT EXISTS stocks.stocks_raw AS
                    SELECT *
                    FROM read_parquet('{parquet_path}/stocks/*.parquet', union_by_name=true);
                """)
                
                con.execute(UNPACKED_STOCKS)      
                
                self.stdout.write(self.style.SUCCESS("ALL STOCKS UNPACKED"))
                
        except Exception as e:
            raise CommandError(f"DuckDB error: {e}")