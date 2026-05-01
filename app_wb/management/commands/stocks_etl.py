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
                
        except Exception as e:
            raise CommandError(f"DuckDB error: {e}")