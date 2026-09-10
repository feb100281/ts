#!/usr/bin/env python3

# Движок под accurals

import os
import importlib
from datetime import datetime, timedelta, timezone
import psycopg
from psycopg.rows import dict_row

# Подключаемся к базе данных 
def connect_db():
    return psycopg.connect(
        dbname="ts_db",  # DB_NAME
        user="ts_user",  # DB_USER
        password="Dec8108079",  # DB_PASSWORD
        host="127.0.0.1",  # DB_HOST
        port="5433",  # DB_PORT
        connect_timeout=10,
    )

# Для сервера пока комментим  

# def connect_db():
#     return psycopg.connect(
#         dbname=get_env("DB_NAME"),
#         user=get_env("DB_USER"),
#         password=get_env("DB_PASSWORD"),
#         host=get_env("DB_HOST"),
#         port=get_env("DB_PORT"),
#         connect_timeout=10,
#     )

# Загружаем функцию
def load_function(path: str):
    module_path = path.replace("/", ".").removesuffix(".py")
    module = importlib.import_module(module_path)
    return getattr(module, "main")


def load_conditions(conn, contract_id=None, condition_id=None):
    sql = """
        SELECT *
        FROM gl.accurals_args
        WHERE fn_id IS NOT NULL
    """
    params = []

    if contract_id is not None:
        sql += " AND contract_id = %s"
        params.append(contract_id)

    if condition_id is not None:
        sql += " AND condition_id = %s"
        params.append(condition_id)

    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def accruals(conn, row):
    fn = load_function(row["python_path"])
    args = {k: v for k, v in row.items() if k != "python_path"}
    return fn(conn=conn, **args)

#Запускаем accurals все
def main():
    conn = connect_db()
    try:
        rows = load_conditions(conn)
        with conn.cursor() as cur:
            cur.execute("TRUNCATE gl.accural_distribution;")
        conn.commit()

        for row in rows:
            accruals(conn, row)
        
        with conn.cursor() as cur:
            cur.execute("SELECT gl.load_accrual_distribution_to_fact();")
        conn.commit()

    finally:
        conn.close()

if __name__ == "__main__":
    main()