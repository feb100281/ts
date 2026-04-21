import os
from sqlalchemy import create_engine
from dotenv import load_dotenv

import psycopg
from psycopg.rows import dict_row
from psycopg import Connection
import duckdb

load_dotenv()

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME")

DATABASE_URL = (
    f"postgresql+psycopg://{DB_USER}:{DB_PASSWORD}"
    f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

ENGINE = create_engine(
    DATABASE_URL,
    # echo=True,
    pool_pre_ping=True
)

def connect_db():
    return psycopg.connect(
        dbname=os.getenv("DB_NAME"),  # DB_NAME
        user=os.getenv("DB_USER"),  # DB_USER
        password=os.getenv("DB_PASSWORD"),  # DB_PASSWORD
        host=os.getenv("DB_HOST", "localhost"),  # DB_HOST
        port=os.getenv("DB_PORT", "5432"),  # DB_PORT
        connect_timeout=10,
    )

def get_psql_conn_str():
    return (
        f"host={os.getenv('DB_HOST', 'localhost')} "
        f"port={os.getenv('DB_PORT', '5432')} "
        f"dbname={os.getenv('DB_NAME')} "
        f"user={os.getenv('DB_USER')} "
        f"password={os.getenv('DB_PASSWORD')}"
    )

def get_duckdb_conn()->duckdb.DuckDBPyConnection:
    db_path = os.getenv("DUCKDB_PATH")

    print(f"Using DuckDB: {db_path}")

    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    con = duckdb.connect(db_path, read_only=True)
    con.execute("INSTALL postgres;")
    con.execute("LOAD postgres;")

    conn_str = get_psql_conn_str()
    con.execute(f"ATTACH '{conn_str}' AS pg (TYPE postgres);")

    return con