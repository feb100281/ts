#!/usr/bin/env python
# Движок под accurals

import os
import importlib
from datetime import datetime, timedelta, timezone
import psycopg
from psycopg.rows import dict_row
from pathlib import Path
import uuid

# Загружаем функцию
def load_function(path: str, func_name: str = "main"):
    file_path = Path(path).resolve()

    if not file_path.exists():
        raise FileNotFoundError(f"Файл не найден: {file_path}")

    module_name = f"accural_{uuid.uuid4().hex}"
    spec = importlib.util.spec_from_file_location(module_name, str(file_path))
    if spec is None or spec.loader is None:
        raise ImportError(f"Не удалось загрузить модуль из {file_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    return getattr(module, func_name)


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
    
def coa_conditions(conn):
    sql = """
        SELECT *
        FROM gl.coa_args
        WHERE fn_id IS NOT NULL
    """
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(sql)
        return cur.fetchall()


def accruals(conn, row):
    fn = load_function(row["server_path"])
    args = {k: v for k, v in row.items() if k != "server_path"}
    return fn(conn=conn, **args)

#Запускаем accurals все
def main(connection):
    conn = connection
    try:
        rows = load_conditions(conn)
        with conn.cursor() as cur:
            cur.execute("TRUNCATE gl.accural_distribution;")
        conn.commit()
        
        with conn.cursor() as cur:
            cur.execute("TRUNCATE gl.borrowings_tp;")
        conn.commit()

        for row in rows:
            accruals(conn, row)
        
        with conn.cursor() as cur:
            cur.execute("SELECT gl.load_accrual_distribution_to_fact();")
        conn.commit()
        
        with conn.cursor() as cur:
            cur.execute("SELECT gl.load_tp_borrowings_to_fact();")
        conn.commit()
        
        #Делаем цикл для COA
        coa_rows = coa_conditions(conn)
        
        for row in coa_rows:
            accruals(conn, row)
        
    finally:
        # conn.close()
        print('ok')

if __name__ == "__main__":
    main()
