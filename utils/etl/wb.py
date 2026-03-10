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

from psycopg.rows import dict_row ##ДОБАВИЛИ


FIELD = {
    "retail_price": {
        "acc_ws":46,
        "acc_pl":48,
        "acc_vat":80,
        "subconto_ws":(52,87),
        "sunconto_pl":(90,91),
        "sunconto_vat":(52,87),
        "ns":"11111111-1111-1111-1111-111111111111"        
    },
    "retail_amount": {
        "acc_ws":91,        
        "subconto_ws":(52,87),        
        "ns":"11111111-1111-1111-1111-111111111113"    
    },
    "ppvz_for_pay": {
        "acc_ws":92,        
        "subconto_ws":(52,87),        
        "ns":"11111111-1111-1111-1111-111111111114"    
    },
    "comission": {
        "acc_ws":46,
        "acc_pl":59,
        "acc_vat":81,
        "subconto_ws":(52,87),
        "sunconto_pl":(90,91),
        "sunconto_vat":(52,87),
        "ns":"11111111-1111-1111-1111-111111111115"        
    },
    "delivery_rub": {
        "acc_ws":46,
        "acc_pl":60,
        "acc_vat":82,
        "subconto_ws":(78,97),
        "sunconto_pl":(108,109),
        "sunconto_vat":(78,97),
        "ns":"11111111-1111-1111-1111-111111111116"        
    },
    "storage_fee": {
        "acc_ws":46,
        "acc_pl":60,
        "acc_vat":82,
        "subconto_ws":(79,98),
        "sunconto_pl":(111,112),
        "sunconto_vat":(79,98),
        "ns":"11111111-1111-1111-1111-111111111117"        
    },
    "acceptance": {
        "acc_ws":46,
        "acc_pl":60,
        "acc_vat":82,
        "subconto_ws":(80,99),
        "sunconto_pl":(114,115),
        "sunconto_vat":(80,99),
        "ns":"11111111-1111-1111-1111-111111111118"        
    },
    "deduction": {
        "acc_ws":46,
        "acc_pl":62,
        "acc_vat":82,
        "subconto_ws":(81,100),
        "sunconto_pl":(118,119),
        "sunconto_vat":(81,100),
        "ns":"11111111-1111-1111-1111-111111111119"        
    },
    "penalty": {
        "acc_ws":46,
        "acc_pl":60,        
        "subconto_ws":(82,101),
        "sunconto_pl":(121,122),
        "ns":"11111111-1111-1111-1111-111111111120"        
    },
    "additional_payment": {
        "acc_ws":46,
        "acc_pl":49,        
        "subconto_ws":(83,102),
        "sunconto_pl":(125,126),
        "ns":"11111111-1111-1111-1111-111111111121"        
    },
    "cashback_commission_change": {
        "acc_ws":46,
        "acc_pl":62,
        "acc_vat":82,
        "subconto_ws":(84,103),
        "sunconto_pl":(127,128),
        "sunconto_vat":(84,103),
        "ns":"11111111-1111-1111-1111-111111111122"     
    },
    "cashback_amount": {
        "acc_ws":46,
        "acc_pl":62,
        # "acc_vat":82,
        "subconto_ws":(85,104),
        "sunconto_pl":(129,130),
        # "sunconto_vat":(84,103),
        "ns":"11111111-1111-1111-1111-111111111123"     
    },
    "payment_schedule": {
        "acc_ws":46,
        "acc_pl":62,        
        "subconto_ws":(86,95),
        "sunconto_pl":(132,133),
        "ns":"11111111-1111-1111-1111-111111111124"        
    },
    
}


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
    
    INSERT INTO gl.wb_distibution (
    id,
    date_from,
    report_type,
    field,
    dt_wb,
    cr_wb,
    dt_pl,
    cr_pl,
    dt_vat,
    cr_vat,
    acc_ws,
    acc_pl,
    acc_vat,
    acc_ob,
    subconto_ws,
    subconto_pl,
    subconto_vat,
    vat,
    ns
)
SELECT
    uuid_generate_v5(
        ns,
        concat_ws('|', t.date_from, t.field, t.report_type, t.cr_wb, t.dt_wb)
    ) AS id,
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
    m.acc_ob,
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
        SUM(dt_wb) AS dt_wb,
        SUM(cr_wb) AS cr_wb,
        SUM(dt_pl) AS dt_pl,
        SUM(cr_pl) AS cr_pl,
        SUM(dt_vat) AS dt_vat,
        SUM(cr_vat) AS cr_vat
    FROM gl.base
    GROUP BY date_from, report_type, field

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

    UNION ALL

    SELECT
        date AS date_from,
        1 AS report_type,
        'withdraw' AS field,
        ROUND(cr * 100, 0)::bigint AS dt_wb,
        ROUND(dt * 100, 0)::bigint AS cr_wb,
        0 AS dt_pl,
        0 AS cr_pl,
        0 AS dt_vat,
        0 AS cr_vat
    FROM public.treasury_cfdata
    WHERE cfitem_id = 134
) t
LEFT JOIN gl.wb_mapping AS m
  ON m.field = t.field
 AND m.report_type = t.report_type

ON CONFLICT (id) DO UPDATE
SET
    date_from     = EXCLUDED.date_from,
    report_type   = EXCLUDED.report_type,
    field         = EXCLUDED.field,
    dt_wb         = EXCLUDED.dt_wb,
    cr_wb         = EXCLUDED.cr_wb,
    dt_pl         = EXCLUDED.dt_pl,
    cr_pl         = EXCLUDED.cr_pl,
    dt_vat        = EXCLUDED.dt_vat,
    cr_vat        = EXCLUDED.cr_vat,
    acc_ws        = EXCLUDED.acc_ws,
    acc_pl        = EXCLUDED.acc_pl,
    acc_vat       = EXCLUDED.acc_vat,
    subconto_ws   = EXCLUDED.subconto_ws,
    subconto_pl   = EXCLUDED.subconto_pl,
    subconto_vat  = EXCLUDED.subconto_vat,
    vat           = EXCLUDED.vat,
    ns            = EXCLUDED.ns
WHERE
    (gl.wb_distibution.date_from,
     gl.wb_distibution.report_type,
     gl.wb_distibution.field,
     gl.wb_distibution.dt_wb,
     gl.wb_distibution.cr_wb,
     gl.wb_distibution.dt_pl,
     gl.wb_distibution.cr_pl,
     gl.wb_distibution.dt_vat,
     gl.wb_distibution.cr_vat,
     gl.wb_distibution.acc_ws,
     gl.wb_distibution.acc_pl,
     gl.wb_distibution.acc_vat,
     gl.wb_distibution.subconto_ws,
     gl.wb_distibution.subconto_pl,
     gl.wb_distibution.subconto_vat,
     gl.wb_distibution.vat,
     gl.wb_distibution.ns)
IS DISTINCT FROM
    (EXCLUDED.date_from,
     EXCLUDED.report_type,
     EXCLUDED.field,
     EXCLUDED.dt_wb,
     EXCLUDED.cr_wb,
     EXCLUDED.dt_pl,
     EXCLUDED.cr_pl,
     EXCLUDED.dt_vat,
     EXCLUDED.cr_vat,
     EXCLUDED.acc_ws,
     EXCLUDED.acc_pl,
     EXCLUDED.acc_vat,
     EXCLUDED.subconto_ws,
     EXCLUDED.subconto_pl,
     EXCLUDED.subconto_vat,
     EXCLUDED.vat,
     EXCLUDED.ns);
    """
    
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

MSK = timezone(timedelta(hours=3))

def get_env(name: str) -> str:
    v = os.getenv(name)
    if not v:
        raise RuntimeError(f"{name} is not set")
    return v

def iso_msk(dt: datetime) -> str:
    return dt.astimezone(MSK).replace(microsecond=0).isoformat()


# def connect_db():
#     return psycopg.connect(
#         dbname=get_env("DB_NAME"),
#         user=get_env("DB_USER"),
#         password=get_env("DB_PASSWORD"),
#         host=get_env("DB_HOST"),
#         port=get_env("DB_PORT"),
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
    date_from   = EXCLUDED.date_from,
    acc_id      = EXCLUDED.acc_id,
    contract_id = EXCLUDED.contract_id,
    dt          = EXCLUDED.dt,
    cr          = EXCLUDED.cr,
    description = EXCLUDED.description,
    subconto_id = EXCLUDED.subconto_id,
    company_id  = EXCLUDED.company_id,
    chapter     = EXCLUDED.chapter
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
    
### СЧИТАЕМ БАЛАНСЫ И КУРСОВЫЕ РАЗНИЦЫ

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


def cash_revolution(acc_id,conn):
    q = f"""
    INSERT INTO gl.cash_revaluation (
    acc_id,
    date_from,
    currency,
    rate_previous,
    fx_rate,
    fx_diff,
    base_bb,
    base_eb,
    bb,
    eb,
    fx_gains_loss
    )
    with ballances AS(
    SELECT
        x.acc_id,
        x.date_from,
        COALESCE(
            LEAD(x.date_from) OVER (
                PARTITION BY x.acc_id
                ORDER BY x.date_from
            ),
            a.max_date + 1
        ) AS date_to,
        SUM(x.turnover) OVER (
            PARTITION BY x.acc_id
            ORDER BY x.date_from
        ) AS eb
    FROM (
        SELECT
            acc_id,
            date_from,
            SUM(base_dt - base_cr) AS turnover
        FROM gl.normalized_cf
        WHERE acc_id = {acc_id}
        GROUP BY acc_id, date_from
        UNION ALL
        SELECT 
        acc_id,
        date::date as date_from,
        round(sum(dt-cr)*100,0)::bigint as turnover		
        from public.grossbook_manual
        WHERE acc_id = {acc_id}
        GROUP BY acc_id, date_from	
    ) x
    JOIN gl.v_bank_acounts a
    ON a.acc_id = x.acc_id
    )


    SELECT
    t.acc_id,
    t.date_from,
    t.currency,
    t.rate_previous,
    t.fx_rate,
    t.fx_diff,
    t.base_bb,
    t.base_eb,
    round(t.base_bb * t.fx_rate,0)::bigint as bb,
    round(t.base_eb * t.fx_rate,0)::bigint as eb,
    round(t.base_bb * t.fx_diff,0)::bigint as fx_gains_loss


    FROM(
    SELECT 
    x.acc_id,
    x.d::date as date_from,
    x.currency,
    case when x.currency = 'RUB' then 1 else
    COALESCE(LAG(fx.rate) OVER (ORDER BY date), 0) end as rate_previous,
    case when x.currency = 'RUB' then 1 else 
    fx.rate end as fx_rate,
    case when x.currency = 'RUB' then 0 else 
    fx.rate - COALESCE(LAG(fx.rate) OVER (ORDER BY date), 0) end as fx_diff,
    COALESCE(LAG(b.eb) OVER (ORDER BY x.d::date), 0) as base_bb,
    b.eb as base_eb
    FROM (
    select 
    a.acc_id,
    a.currency,
    generate_series(
            a.min_date,
            a.max_date,
            '1 day'
        ) d
    from gl.v_bank_acounts a 
    where acc_id = {acc_id}
    order by d
    ) x 
    LEFT JOIN public.macro_currencyrate fx
    ON fx.currency = x.currency
    AND fx.date = x.d
    AND x.currency <> 'RUB'
    left join ballances b on x.d::date >= b.date_from and x.d::date < b.date_to 
    ) t
    ON CONFLICT (acc_id, date_from) DO UPDATE
SET
    currency       = EXCLUDED.currency,
    rate_previous  = EXCLUDED.rate_previous,
    fx_rate        = EXCLUDED.fx_rate,
    fx_diff        = EXCLUDED.fx_diff,
    base_bb        = EXCLUDED.base_bb,
    base_eb        = EXCLUDED.base_eb,
    bb             = EXCLUDED.bb,
    eb             = EXCLUDED.eb,
    fx_gains_loss  = EXCLUDED.fx_gains_loss
WHERE
    (gl.cash_revaluation.currency,
     gl.cash_revaluation.rate_previous,
     gl.cash_revaluation.fx_rate,
     gl.cash_revaluation.fx_diff,
     gl.cash_revaluation.base_bb,
     gl.cash_revaluation.base_eb,
     gl.cash_revaluation.bb,
     gl.cash_revaluation.eb,
     gl.cash_revaluation.fx_gains_loss)
IS DISTINCT FROM
    (EXCLUDED.currency,
     EXCLUDED.rate_previous,
     EXCLUDED.fx_rate,
     EXCLUDED.fx_diff,
     EXCLUDED.base_bb,
     EXCLUDED.base_eb,
     EXCLUDED.bb,
     EXCLUDED.eb,
     EXCLUDED.fx_gains_loss);    
    
    """
    
    
    with conn.cursor() as cur:
        cur.execute(q)
    conn.commit()

def execute_cash_revolution(conn):
    with conn.cursor() as cur:
        cur.execute("TRUNCATE gl.cash_revaluation;")
    conn.commit()
    accounts = fletch_accounts(conn)
    for acc in accounts:
        acc_id = acc['acc_id']
        cash_revolution(acc_id,conn)

def include_WB_ballance(conn):
    q = """
    INSERT INTO gl.cash_revaluation (
    acc_id,
    date_from,
    currency,
    rate_previous,
    fx_rate,
    fx_diff,
    base_bb,
    base_eb,
    bb,
    eb,
    fx_gains_loss
    )    
    with ballances AS(
    SELECT
        x.acc_id,
        x.date_from,
        COALESCE(
            LEAD(x.date_from) OVER (
                PARTITION BY x.acc_id
                ORDER BY x.date_from
            ),
            current_date + 1
        ) AS date_to,
        SUM(x.turnover) OVER (
            PARTITION BY x.acc_id
            ORDER BY x.date_from
        ) AS eb
    FROM (
        SELECT
            acc_id,
            date_from,
            SUM(base_dt - base_cr) AS turnover
        FROM gl.wb_cf
        WHERE acc_id = 46
        GROUP BY acc_id, date_from
        UNION ALL
        SELECT 
        acc_id,
        date::date as date_from,
        round(sum(dt-cr)*100,0)::bigint as turnover		
        from public.grossbook_manual
        WHERE acc_id = 46
        GROUP BY acc_id, date_from	
    ) x
    
    )


    SELECT
    t.acc_id,
    t.date_from,
    t.currency,
    t.rate_previous,
    t.fx_rate,
    t.fx_diff,
    t.base_bb,
    t.base_eb,
    round(t.base_bb * t.fx_rate,0)::bigint as bb,
    round(t.base_eb * t.fx_rate,0)::bigint as eb,
    round(t.base_bb * t.fx_diff,0)::bigint as fx_gains_loss


    FROM(
    SELECT 
    x.acc_id,
    x.d::date as date_from,
    x.currency,
    1 as rate_previous,
    1 as fx_rate,
    0 as fx_diff,
    COALESCE(LAG(b.eb) OVER (ORDER BY x.d::date), 0) as base_bb,
    b.eb as base_eb
    FROM (
    select 
    46 as acc_id,
    'RUB' as currency,
    generate_series(
            '2023-08-28',
            current_date,
            '1 day'
        ) d    
    order by d
    ) x 
    LEFT JOIN public.macro_currencyrate fx
    ON fx.currency = x.currency
    AND fx.date = x.d
    AND x.currency <> 'RUB'
    left join ballances b on x.d::date >= b.date_from and x.d::date < b.date_to 
    ) t
    ON CONFLICT (acc_id, date_from) DO UPDATE
SET
    currency       = EXCLUDED.currency,
    rate_previous  = EXCLUDED.rate_previous,
    fx_rate        = EXCLUDED.fx_rate,
    fx_diff        = EXCLUDED.fx_diff,
    base_bb        = EXCLUDED.base_bb,
    base_eb        = EXCLUDED.base_eb,
    bb             = EXCLUDED.bb,
    eb             = EXCLUDED.eb,
    fx_gains_loss  = EXCLUDED.fx_gains_loss
WHERE
    (gl.cash_revaluation.currency,
     gl.cash_revaluation.rate_previous,
     gl.cash_revaluation.fx_rate,
     gl.cash_revaluation.fx_diff,
     gl.cash_revaluation.base_bb,
     gl.cash_revaluation.base_eb,
     gl.cash_revaluation.bb,
     gl.cash_revaluation.eb,
     gl.cash_revaluation.fx_gains_loss)
IS DISTINCT FROM
    (EXCLUDED.currency,
     EXCLUDED.rate_previous,
     EXCLUDED.fx_rate,
     EXCLUDED.fx_diff,
     EXCLUDED.base_bb,
     EXCLUDED.base_eb,
     EXCLUDED.bb,
     EXCLUDED.eb,
     EXCLUDED.fx_gains_loss);    
    
    """
    with conn.cursor() as cur:
        cur.execute(q)
    conn.commit()
    




# --------------------
# MAIN
# --------------------
def main():

    conn = connect_db()
    START_DATE = "2026-01-01"
    END_DATE = "2026-03-09"
    
    date_to_msk = datetime.now(timezone.utc).astimezone(MSK)
    date_from_msk = date_to_msk - timedelta(days=2)
    
    DATE_FROM = iso_msk(date_from_msk)
    DATE_TO = iso_msk(date_to_msk)
    
    # with conn.cursor() as cur:
    #     cur.execute("REFRESH MATERIALIZED VIEW gl.vr;")
    # conn.commit()
    
    
    # insert_normizized(conn)

    fields = parse_fields()
    create_temp_table(conn, START_DATE, END_DATE, fields)
    make_target_tbl(conn)
    wb_distribution(conn)
    # wb_cf(conn)
    # add_trasfers(conn, DATE_FROM, DATE_TO)
    # update_gl_with_wb(conn)
    # # print(fletch_accounts(conn))
    # execute_cash_revolution(conn)
    # include_WB_ballance(conn)
    
    # with conn.cursor() as cur:
    #     cur.execute("REFRESH MATERIALIZED VIEW gl.mv_cf_report;")
    # conn.commit()
    conn.close()
    
# scp /Users/pavelustenko/ts/utils/etl/wb.py daria@82.202.197.94:/opt/wb_jobs/wb_etl.py

if __name__ == "__main__":
    main()
