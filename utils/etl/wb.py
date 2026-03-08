#!/usr/bin/env python3


# ------
# СКРИПТ ДЕЛАЕТ:
# - ОТЧЕТ CF
# - PL WB
# - РАСЧЕТНЫЙ НДС WB
# - запуск раз в сутки в 10 утра МСК или через systemctl


import os
from datetime import datetime, timedelta, timezone

import psycopg


from wbmaping import FIELD


CONTRACT_ID = 109
CF_ACCOUNT = 46


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
    return "ok"


# --------------------
# DB CONFIG
# --------------------
SOURCE_TABLE = "wb_dwh.realization_kv"

SHCEMA = "gl"
TARGET_TEMP_TABLE = f"{SHCEMA}.temp_tbl"
TARGET_TABLE = f"{SHCEMA}.base"


def drop_temp_table(conn):
    with conn.cursor() as cur:
        cur.execute(f"DROP TABLE IF EXISTS {TARGET_TEMP_TABLE}")
    conn.commit()


def create_temp_table(conn, start_date, end_date, fields):
    drop_temp_table(conn)
    q = f"""
    CREATE TABLE IF NOT EXISTS {TARGET_TEMP_TABLE} AS
    SELECT 
        t.date_from::date AS date_from,
        t.rrd_id, 
        t.nm_id,
        t.report_type,
        t.dtn_id,
        t.son_id,
        t.bonus_type_name,
        t.field,
        t.value,
        COALESCE(p.vat_rate::numeric, vr.rate::numeric) AS vat_rate
       
    FROM wb_dwh.realization_kv AS t   
    

    LEFT JOIN LATERAL (
        SELECT p1.vat_rate
        FROM public.wb_product p1
        WHERE p1.nm_id = t.nm_id
        AND t.field IN ('retail_price', 'ppvz_for_pay')
        ORDER BY p1.nm_id  -- можно заменить на updated_at desc, если есть
        LIMIT 1
    ) p ON TRUE

    LEFT JOIN LATERAL (
        SELECT vr1.rate
        FROM gl.vr vr1
        WHERE t.date_from::date >= vr1.date_from
        AND t.date_from::date <  vr1.date_to
        ORDER BY vr1.date_from DESC
        LIMIT 1
    ) vr ON TRUE
    
    WHERE t.date_from >= '{start_date}'
    AND t.date_from <  '{end_date}'
    AND t.quantity <> 2
    AND t.field IN (
        {fields}
    );
    """
    with conn.cursor() as cur:
        cur.execute(q)
    conn.commit()


def drop_base_table(conn):
    with conn.cursor() as cur:
        cur.execute(f"DROP TABLE IF EXISTS {TARGET_TABLE}")
    conn.commit()


def make_target_tbl(conn):
    drop_base_table(conn)
    q = f"""
    CREATE TABLE IF NOT EXISTS {TARGET_TABLE} AS
    SELECT
    x.date_from::date,
    x.rrd_id::bigint, 
    x.nm_id::bigint,
    x.report_type::int,
    x.dtn_id::int,
    x.son_id::int,
    x.btn,
    x.field::text,
    x.value::bigint,
    x.vat_rate::numeric,
    x.dt::bigint as dt_wb,
    x.cr::bigint as cr_wb,
    CASE WHEN x.dt = 0 THEN abs(x.vat_free)::bigint ELSE 0 END AS cr_pl,
    CASE WHEN x.cr = 0 THEN abs(x.vat_free)::bigint ELSE 0 END AS dt_pl,
    CASE WHEN x.dt = 0 THEN abs(x.vat)::bigint ELSE 0 END AS cr_vat,
    CASE WHEN x.cr = 0 THEN abs(x.vat)::bigint ELSE 0 END AS dt_vat
FROM (
    SELECT
        date_from::date AS date_from,
        rrd_id, 
        nm_id,
        report_type::int AS report_type,
        dtn_id::int AS dtn_id,
        son_id::int as son_id,
        bonus_type_name::text AS btn,
        field::text AS field,
        value::bigint AS value,
        vat_rate::numeric AS vat_rate,

        ROUND(
            (value::numeric * vat_rate::numeric) / (100 + vat_rate::numeric),
            0
        )::bigint AS vat,

        ROUND(
            value::numeric / (100 + vat_rate::numeric) * 100,
            0
        )::bigint AS vat_free,

      -- CR
CASE
  WHEN field = 'additional_payment' THEN GREATEST(value, 0)

  WHEN field IN ('cashback_commission_change', 'cashback_amount')
       THEN CASE WHEN dtn_id = 2 THEN value ELSE 0 END

  WHEN field = 'payment_schedule' THEN value

  WHEN dtn_id = 1 THEN value
  WHEN dtn_id = 2 THEN 0
  WHEN dtn_id IS NULL THEN value
  ELSE 0
END AS cr,

-- DT
CASE
  WHEN field = 'additional_payment' THEN GREATEST(-value, 0)

  WHEN field IN ('cashback_commission_change', 'cashback_amount')
       THEN CASE WHEN dtn_id = 1 THEN value ELSE 0 END

  WHEN dtn_id = 2 THEN value
  WHEN dtn_id = 1 THEN 0
  WHEN dtn_id IS NULL THEN 0
  ELSE 0
END AS dt

    FROM gl.temp_tbl
    ) AS x;    
    
    """
    with conn.cursor() as cur:
        cur.execute(q)
    conn.commit()


def wb_distribution(conn):
    """
    Таблица для расспеределения операций WB по дням
    """

    q = """
    
    CREATE TABLE IF NOT EXISTS gl.wb_distibution AS
    SELECT
    t.date_from,
    t.report_type,
    t.field,
    t.dt_wb,
    t.cr_wb,
    t.dt_pl,
    t.cr_pl,
    t.dt_vat,
    t.cr_vat,
    m.acc_ws,
    m.acc_pl,
    m.acc_vat,
    m.subconto_ws,
    m.subconto_pl,
    m.subconto_vat,
    m.vat,
    m.ns

    FROM (

    SELECT
    date_from,
    report_type,
    field,


    sum(dt_wb) as dt_wb,
    sum(cr_wb) as cr_wb,
    sum(dt_pl) as dt_pl,
    sum(cr_pl) as cr_pl,
    sum(dt_vat) as dt_vat,
    sum(cr_vat) as cr_vat
    from gl.base
    group by  date_from, report_type, field

    UNION ALL

    SELECT
        date_from,
        report_type,
        'comission' AS field,

        COALESCE(SUM(cr_wb) FILTER (WHERE field = 'retail_price'), 0) -
        COALESCE(SUM(cr_wb) FILTER (WHERE field = 'ppvz_for_pay'), 0) AS dt_wb,
        
        COALESCE(SUM(dt_wb) FILTER (WHERE field = 'retail_price'), 0) -
        COALESCE(SUM(dt_wb) FILTER (WHERE field = 'ppvz_for_pay'), 0) AS cr_wb,

        COALESCE(SUM(cr_pl) FILTER (WHERE field = 'retail_price'), 0) -
        COALESCE(SUM(cr_pl) FILTER (WHERE field = 'ppvz_for_pay'), 0) AS dt_pl,
        
        COALESCE(SUM(dt_pl) FILTER (WHERE field = 'retail_price'), 0) -
        COALESCE(SUM(dt_pl) FILTER (WHERE field = 'ppvz_for_pay'), 0) AS cr_pl,

        COALESCE(SUM(cr_vat) FILTER (WHERE field = 'retail_price'), 0) -
        COALESCE(SUM(cr_vat) FILTER (WHERE field = 'ppvz_for_pay'), 0) AS dt_vat,

        COALESCE(SUM(dt_vat) FILTER (WHERE field = 'retail_price'), 0) -
        COALESCE(SUM(dt_vat) FILTER (WHERE field = 'ppvz_for_pay'), 0) AS cr_vat

        
    FROM gl.base 
    GROUP BY date_from, report_type
    ) t

    left join gl.wb_mapping as m on m.field = t.field and m.report_type = t.report_type
    
    """
    with conn.cursor() as cur:
        cur.execute(f"DROP TABLE IF EXISTS  gl.wb_distibution")
    conn.commit()
    with conn.cursor() as cur:
        cur.execute(q)
    conn.commit()
    with conn.cursor() as cur:
        cur.execute(f"DROP TABLE IF EXISTS {TARGET_TEMP_TABLE}")
    conn.commit()
    with conn.cursor() as cur:
        cur.execute(f"DROP TABLE IF EXISTS {TARGET_TABLE}")
    conn.commit()


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


CONTRACT_ID = 109  # ПОКА ТАК
COMPANY_ID = 1


def get_id(ns):
    return f"""
    uuid_generate_v5(
            '{ns}'::uuid, 
            concat_ws('|', to_char(date_from::date, 'YYYY-MM-DD'))
            )
    """


def parse_fields():

    fields = list(FIELD.keys())
    field = {f"'{f}'" for f in fields}
    return ",\n".join(field)


def wb_cf(conn):
    q = f"""
    INSERT INTO gl.wb_cf (
    id,
    date_from,
    acc_id,
    currency,
    company_id,
    subconto_id,
    fx_rate,
    base_dt,
    base_cr,
    dt,
    cr,
    description,
    contract_id
)
SELECT
    uuid_generate_v5(
        ns,
        concat_ws('|', date_from, field, report_type)
    ) AS id,
    date_from,
    acc_ws AS acc_id,
    'RUB' AS currency,
    1 AS company_id,
    subconto_ws AS subconto_id,
    1 AS fx_rate,
    dt_wb AS base_dt,
    cr_wb AS base_cr,
    dt_wb AS dt,
    cr_wb AS cr,
    field AS description,
    {CONTRACT_ID} AS contract_id
FROM gl.wb_distibution
WHERE acc_ws = {CF_ACCOUNT}

ON CONFLICT (id) DO UPDATE
SET
    date_from   = EXCLUDED.date_from,
    acc_id      = EXCLUDED.acc_id,
    currency    = EXCLUDED.currency,
    company_id  = EXCLUDED.company_id,
    subconto_id = EXCLUDED.subconto_id,
    fx_rate     = EXCLUDED.fx_rate,
    base_dt     = EXCLUDED.base_dt,
    base_cr     = EXCLUDED.base_cr,
    dt          = EXCLUDED.dt,
    cr          = EXCLUDED.cr,
    description = EXCLUDED.description,
    contract_id = EXCLUDED.contract_id
WHERE
    (gl.wb_cf.date_from,
     gl.wb_cf.acc_id,
     gl.wb_cf.currency,
     gl.wb_cf.company_id,
     gl.wb_cf.subconto_id,
     gl.wb_cf.fx_rate,
     gl.wb_cf.base_dt,
     gl.wb_cf.base_cr,
     gl.wb_cf.dt,
     gl.wb_cf.cr,
     gl.wb_cf.description,
     gl.wb_cf.contract_id)
IS DISTINCT FROM
    (EXCLUDED.date_from,
     EXCLUDED.acc_id,
     EXCLUDED.currency,
     EXCLUDED.company_id,
     EXCLUDED.subconto_id,
     EXCLUDED.fx_rate,
     EXCLUDED.base_dt,
     EXCLUDED.base_cr,
     EXCLUDED.dt,
     EXCLUDED.cr,
     EXCLUDED.description,
     EXCLUDED.contract_id);  
    """
    with conn.cursor() as cur:
        cur.execute(q)
    conn.commit()


def add_trasfers(conn, start, finish):
    # Добавляем выведеные деньги
    q = f"""
    INSERT INTO gl.wb_cf (
    id,
    date_from,
    acc_id,
    currency,
    company_id,
    subconto_id,
    fx_rate,
    base_dt,
    base_cr,
    dt,
    cr,
    description,
    contract_id
)
    SELECT
    uuid_generate_v5(
        '11111111-1111-1111-1111-111111111200',
        concat_ws('|', date, cr, dt)
    ) AS id,
    date as date_from,
    46 AS acc_id,
    'RUB' AS currency,
    1 AS company_id,
    134 AS subconto_id,
    1 AS fx_rate,
    round(cr*100,0)::bigint AS base_dt,
    round(dt*100,0)::bigint AS base_cr,
    round(cr*100,0)::bigint AS dt,
    round(dt*100,0)::bigint AS cr,
    'Переводы дс с баланса на баланс WB' AS description,
    109 AS contract_id
    FROM public.treasury_cfdata
    where cfitem_id = 134 
    and date >= '{start}' and date < '{finish}'
    
    ON CONFLICT (id) DO UPDATE
SET
    date_from   = EXCLUDED.date_from,
    acc_id      = EXCLUDED.acc_id,
    currency    = EXCLUDED.currency,
    company_id  = EXCLUDED.company_id,
    subconto_id = EXCLUDED.subconto_id,
    fx_rate     = EXCLUDED.fx_rate,
    base_dt     = EXCLUDED.base_dt,
    base_cr     = EXCLUDED.base_cr,
    dt          = EXCLUDED.dt,
    cr          = EXCLUDED.cr,
    description = EXCLUDED.description,
    contract_id = EXCLUDED.contract_id
WHERE
    (gl.wb_cf.date_from,
     gl.wb_cf.acc_id,
     gl.wb_cf.currency,
     gl.wb_cf.company_id,
     gl.wb_cf.subconto_id,
     gl.wb_cf.fx_rate,
     gl.wb_cf.base_dt,
     gl.wb_cf.base_cr,
     gl.wb_cf.dt,
     gl.wb_cf.cr,
     gl.wb_cf.description,
     gl.wb_cf.contract_id)
IS DISTINCT FROM
    (EXCLUDED.date_from,
     EXCLUDED.acc_id,
     EXCLUDED.currency,
     EXCLUDED.company_id,
     EXCLUDED.subconto_id,
     EXCLUDED.fx_rate,
     EXCLUDED.base_dt,
     EXCLUDED.base_cr,
     EXCLUDED.dt,
     EXCLUDED.cr,
     EXCLUDED.description,
     EXCLUDED.contract_id);  
    """
    with conn.cursor() as cur:
        cur.execute(q)
    conn.commit()

def update_gl_with_wb(conn):
    q = f"""
    WITH src AS (

    -- PL
    SELECT 
        uuid_generate_v5(
            ns,
            concat_ws('|', date_from, field, report_type, 'PL')
        ) AS id,
        uuid_generate_v5(
            ns,
            concat_ws('|', date_from, field, report_type)
        ) AS pid,
        date_from,
        acc_pl AS acc_id,
        {CONTRACT_ID} AS contract_id,
        CASE WHEN vat THEN cr_pl ELSE cr_wb END AS dt,
        CASE WHEN vat THEN dt_pl ELSE dt_wb END AS cr,
        field || ' отражение в pl без НДС' AS description,
        subconto_pl AS subconto_id,
        1 AS company_id,
        'PL' as chapter
    FROM gl.wb_distibution
    WHERE acc_pl IS NOT NULL

    UNION ALL

    -- VAT
    SELECT 
        uuid_generate_v5(
            ns,
            concat_ws('|', date_from, field, report_type, 'VAT')
        ) AS id,
        uuid_generate_v5(
            ns,
            concat_ws('|', date_from, field, report_type)
        ) AS pid,
        date_from,
        acc_vat AS acc_id,
        {CONTRACT_ID} AS contract_id,
        CASE WHEN vat THEN cr_vat ELSE 0 END AS dt,
        CASE WHEN vat THEN dt_vat ELSE 0 END AS cr,
        field || ' отражение НДС' AS description,
        subconto_pl AS subconto_id,
        1 AS company_id,
        'VAT_S' as chapter
    FROM gl.wb_distibution
    WHERE acc_vat IS NOT NULL

    UNION ALL

    -- OB
    SELECT 
        uuid_generate_v5(
            ns,
            concat_ws('|', date_from, field, report_type, 'OB')
        ) AS id,
        uuid_generate_v5(
            ns,
            concat_ws('|', date_from, field, report_type)
        ) AS pid,
        date_from,
        acc_ws AS acc_id,
        {CONTRACT_ID} AS contract_id,
        cr_wb AS dt,
        dt_wb AS cr,
        field || ' отражение на забалансовом счете' AS description,
        subconto_pl AS subconto_id,
        1 AS company_id,
        'OB' as chapter
    FROM gl.wb_distibution
    WHERE acc_ws <> 46
      AND acc_ws IS NOT NULL
)

INSERT INTO gl.fact (
    id,
    pid,
    date_from,
    acc_id,
    contract_id,
    dt,
    cr,
    description,
    subconto_id,
    company_id,
    chapter
)
SELECT
    id,
    pid,
    date_from,
    acc_id,
    contract_id,
    dt,
    cr,
    description,
    subconto_id,
    company_id,
    chapter
FROM src

ON CONFLICT (id) DO UPDATE
SET
    pid         = EXCLUDED.pid,
    date_from        = EXCLUDED.date_from,
    acc_id      = EXCLUDED.acc_id,
    contract_id = EXCLUDED.contract_id,
    dt          = EXCLUDED.dt,
    cr          = EXCLUDED.cr,
    description = EXCLUDED.description,
    subconto_id = EXCLUDED.subconto_id,
    company_id  = EXCLUDED.company_id,
    chapter     =EXCLUDED.chapter
WHERE
    (gl.fact.pid,
     gl.fact.date_from,
     gl.fact.acc_id,
     gl.fact.contract_id,
     gl.fact.dt,
     gl.fact.cr,
     gl.fact.description,
     gl.fact.subconto_id,
     gl.fact.company_id,
     gl.fact.chapter
     )
IS DISTINCT FROM
    (EXCLUDED.pid,
     EXCLUDED.date_from,
     EXCLUDED.acc_id,
     EXCLUDED.contract_id,
     EXCLUDED.dt,
     EXCLUDED.cr,
     EXCLUDED.description,
     EXCLUDED.subconto_id,
     EXCLUDED.company_id,
     EXCLUDED.chapter
     );
    
    
    """
    with conn.cursor() as cur:
        cur.execute(q)
    conn.commit()
    

# --------------------
# MAIN
# --------------------
def main():

    conn = connect_db()
    START_DATE = "2025-01-01"
    END_DATE = "2026-01-01"
    
    with conn.cursor() as cur:
        cur.execute("REFRESH MATERIALIZED VIEW gl.vr;")
    conn.commit()
    
    
    insert_normizized(conn)

    fields = parse_fields()
    create_temp_table(conn, START_DATE, END_DATE, fields)
    make_target_tbl(conn)
    wb_distribution(conn)
    wb_cf(conn)
    add_trasfers(conn, START_DATE, END_DATE)
    update_gl_with_wb(conn)
    
    
    with conn.cursor() as cur:
        cur.execute("REFRESH MATERIALIZED VIEW gl.mv_cf_report;")
    conn.commit()
    


if __name__ == "__main__":
    main()
