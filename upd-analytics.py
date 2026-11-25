#!/usr/bin/env python3
# Скрипт обновляет аналитические слои для отчетов 

import os
from pathlib import Path

import duckdb
from dotenv import load_dotenv

load_dotenv()

import time


def get_psql_conn_str():
    return (
        f"host={os.getenv('DB_HOST', 'localhost')} "
        f"port={os.getenv('DB_PORT', '5432')} "
        f"dbname={os.getenv('DB_NAME')} "
        f"user={os.getenv('DB_USER')} "
        f"password={os.getenv('DB_PASSWORD')}"
    )


def get_duckdb_conn():
    db_path = os.getenv("DUCKDB_PATH")

    print(f"Using DuckDB: {db_path}")

    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    con = duckdb.connect(db_path)
    con.execute("INSTALL postgres;")
    con.execute("LOAD postgres;")

    conn_str = get_psql_conn_str()
    con.execute(f"ATTACH '{conn_str}' AS pg (TYPE postgres);")

    return con

def rewrite_sales(con):
    start = time.time()

    con.execute(f"""
        CREATE OR REPLACE TABLE sales AS
        SELECT *
        FROM pg.wb_dwh.realization_kv
        WHERE quantity <> 2
      
    """)

    con.execute("CHECKPOINT")

    end = time.time()
    print(f"⏱ time: {end - start:.2f} sec")

    print("sales rewritten")

def rewrite_cards(con):
    start = time.time()

    con.execute(f"""
        CREATE OR REPLACE TABLE cards AS
        SELECT *
        FROM pg.wb_raw.raw_cards
        
      
    """)

    con.execute("CHECKPOINT")

    end = time.time()
    print(f"⏱ time: {end - start:.2f} sec")

    print("cards rewritten")
    
def rewrite_nms(con):
    start = time.time()

    con.execute(f"""
        CREATE OR REPLACE TABLE product AS
        SELECT *
        FROM pg.public.wb_product
        
      
    """)

    con.execute("CHECKPOINT")

    end = time.time()
    print(f"⏱ time: {end - start:.2f} sec")

    print("Noms rewritten")



def main():
    con = get_duckdb_conn()
    try:
        rewrite_sales(con)
        con.sql("SELECT count(*) AS cnt FROM sales").show()
        con.sql("SELECT * FROM sales LIMIT 5").show()
        rewrite_cards(con)
        rewrite_nms(con)
    finally:
        con.close()


if __name__ == "__main__":
    main()

