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
                   
                
                self.stdout.write(self.style.SUCCESS("ALL DELIVERIES CREATED"))
                
        except Exception as e:
            raise CommandError(f"DuckDB error: {e}")