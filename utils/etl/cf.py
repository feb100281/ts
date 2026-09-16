#!/usr/bin/env python3

#-----------------
# Скрипт нормализует CF выписки дальнейщей работы и создает таблицу normilized_cf
# Пишем курсовые разницы в gl
# Обновляем балансы по дням в активах
# обновление раз в сутки или через systemctl 
#-----------------

import os
from datetime import datetime, timedelta, timezone
import psycopg
from psycopg.rows import dict_row
from pprint import pprint
# --------------------
# Helpers
# --------------------
def get_env(name: str) -> str:
    v = os.getenv(name)
    if not v:
        raise RuntimeError(f"{name} is not set")
    return v

# def connect_db():
#     return psycopg.connect(
#         dbname=get_env("ts_db"), #DB_NAME
#         user=get_env("ts_user"), #DB_USER
#         password=get_env("Dec8108079"), #DB_PASSWORD
#         host=get_env("127.0.0.1"), #DB_HOST
#         port=get_env("5433"), #DB_PORT
#         connect_timeout=10,
#     )


def connect_db():
    return psycopg.connect(
        dbname="ts_db",  # DB_NAME
        user="ts_user",  # DB_USER
        password="Dec8108079",  # DB_PASSWORD
        host="127.0.0.1",  # DB_HOST
        port="5433",  # DB_PORT
        connect_timeout=10,
    )

SHCEMA = "gl"
TARGET_TABLE = 'normalized_cf'

def insert_normizized(conn):
    """
    Стираем и перезаписываем заного весь CF для работы
    """
    
    q = """
    INSERT INTO gl.normalized_cf
    (
        date_from,
        acc_id,
        currency,
        company_id,
        contract_id,
        subconto_id,
        fx_rate,
        base_dt,
        base_cr,
        dt,
        cr,
        description
    )
    SELECT
    x.date_from,
    x.acc_id,
    x.currency,
    x.company_id,
	x.contract_id,
    x.subconto_id,
    x.fx_rate,
    x.base_dt,
    x.base_cr,
    ROUND(x.base_dt * x.fx_rate, 0)::bigint AS dt,
    ROUND(x.base_cr * x.fx_rate, 0)::bigint AS cr,
    x.description
    FROM (
        SELECT 
            t.date AS date_from,
            b.bs_acc_id AS acc_id,
            b.currency,
            t.contract_id,
            b.corporate_id AS company_id,
            t.cfitem_id AS subconto_id,
            CASE 
                WHEN b.currency = 'RUB' THEN 1
                ELSE fx.rate
            END AS fx_rate,
            ROUND(t.dt * 100, 0)::bigint AS base_dt,
            ROUND(t.cr * 100, 0)::bigint AS base_cr,
            t.temp AS description
        FROM public.treasury_cfdata t
        JOIN public.corporate_bankaccount b
        ON t.ba_id = b.id
        LEFT JOIN LATERAL (
            SELECT r.rate
            FROM public.macro_currencyrate r
            WHERE r.date = t.date
            AND r.currency = b.currency
            ORDER BY r.date
            LIMIT 1
        ) fx ON TRUE
    ) x  
    """
    with conn.cursor() as cur:
         cur.execute("TRUNCATE TABLE gl.normalized_cf;")
    conn.commit()    
    with conn.cursor() as cur:
         cur.execute(q)
    conn.commit()
    return 'ok'

def fletch_accounts(conn):
    
    SQL = """
    SELECT 
        x.ba_id,
        x.acc_id,
        x.currency,
        x.is_active,
        x.min_date,
        CASE 
            WHEN x.is_active IS TRUE THEN CURRENT_DATE
            ELSE x.max_date
        END AS max_date
    FROM (
        SELECT
            a.id AS ba_id,
            a.bs_acc_id AS acc_id,
            a.currency,
            a.is_active,
            MIN(t.date) AS min_date,
            MAX(t.date) AS max_date
        FROM public.corporate_bankaccount a
        JOIN public.treasury_cfdata t 
            ON t.ba_id = a.id
        GROUP BY a.id, a.bs_acc_id, a.currency, a.is_active
    ) x    
    """
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(SQL)
        rows = cur.fetchall()
    return rows





# --------------------
# MAIN
# --------------------
def main():
    
    conn = connect_db()  
    insert_normizized(conn)
    # pprint(fletch_accounts(conn))
    
if __name__ == "__main__":
    main()


