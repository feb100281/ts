#!/usr/bin/env python3


# ------
# СКРИПТ ДЕЛАЕТ:
# - обновляет gl предварительно стирая ее
# - запуск раз в сутки в 10 утра МСК или через systemctl


import os
from datetime import datetime, timedelta, timezone
import psycopg
import ba_elt
# from psycopg.rows import dict_row


def get_env(name: str) -> str:
    v = os.getenv(name)
    if not v:
        raise RuntimeError(f"{name} is not set")
    return v

def connect_db():
    return psycopg.connect(
        dbname="ts_db",  # DB_NAME
        user="ts_user",  # DB_USER
        password="Dec8108079",  # DB_PASSWORD
        host="127.0.0.1",  # DB_HOST
        port="5433",  # DB_PORT
        connect_timeout=10,
    )
    

# def connect_db():
#     return psycopg.connect(
#         dbname=get_env("DB_NAME"),
#         user=get_env("DB_USER"),
#         password=get_env("DB_PASSWORD"),
#         host=get_env("DB_HOST"),
#         port=get_env("DB_PORT"),
#         connect_timeout=10,
#     )

def update_gl_with_wb(conn):
    q = """
    INSERT INTO gl.fact(
	id, pid, date_from, acc_id, contract_id, dt, cr, description, subconto_id, company_id, chapter)
    SELECT
    id, pid, date_from, acc_id, contract_id, dt, cr, description, subconto_id, company_id, chapter
    FROM gl.wb_to_gl    
    """
    with conn.cursor() as cur:
        cur.execute(q)
    conn.commit()
    return 'wb done'

def update_gl_with_ba(conn):
    q = """
    INSERT INTO gl.fact(
	id, pid, date_from, acc_id, contract_id, dt, cr, description, subconto_id, company_id, chapter)
    SELECT
    id, pid, date_from, acc_id, contract_id, dt, cr, description, subconto_id, company_id, chapter
    FROM gl.ba_to_gl 
    """
    with conn.cursor() as cur:
        cur.execute(q)
    conn.commit()
    return 'wb done'
    


def main():

    conn = connect_db()
    
    ba_elt.main()

    with conn.cursor() as cur:
        cur.execute("REFRESH MATERIALIZED VIEW gl.mv_ba_distribution;")
    conn.commit()
    
    with conn.cursor() as cur:
        cur.execute("TRUNCATE gl.details, gl.fact;")
    conn.commit()
    
    update_gl_with_wb(conn)
    
    update_gl_with_ba(conn)
    
    with conn.cursor() as cur:
        cur.execute("REFRESH MATERIALIZED VIEW gl.mv_cf_report;")
    conn.commit()

    conn.close()


# scp /Users/pavelustenko/ts/utils/etl/ba_elt.py daria@82.202.197.94:/opt/wb_jobs/ba_etl.py

if __name__ == "__main__":
    main()