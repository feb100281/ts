# Движек держит в порядне аналитические слови и уткобазу
# analytics/engine.py
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


def get_duckdb_path():
    # можно потом вынести в Django settings
    return os.getenv("DUCKDB_PATH", "analytics/analytics.duckdb")


def get_duckdb_conn():
    db_path = get_duckdb_path()
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect(db_path)
    con.execute("INSTALL postgres;")
    con.execute("LOAD postgres;")

    conn_str = get_psql_conn_str()
    con.execute(f"ATTACH '{conn_str}' AS pg (TYPE postgres);")
    return con

def rewrite_sales(con, limit=100000):
    start = time.time()

    con.execute(f"""
        CREATE OR REPLACE TABLE sales AS
        SELECT *
        FROM pg.wb_dwh.realization_kv
        WHERE quantity <> 2
        -- LIMIT {limit}
    """)

    con.execute("CHECKPOINT")

    end = time.time()
    print(f"⏱ time: {end - start:.2f} sec")

    print("sales rewritten")


def main():
    con = get_duckdb_conn()
    try:
        rewrite_sales(con, limit=1_000_000)
        con.sql("SELECT count(*) AS cnt FROM sales").show()
        con.sql("SELECT * FROM sales LIMIT 5").show()
    finally:
        con.close()


if __name__ == "__main__":
    main()
    







