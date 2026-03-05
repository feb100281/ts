#!/usr/bin/env python3
import os
from datetime import datetime, timedelta, timezone

import psycopg

import pandas as pd

# WB expects Moscow timezone in request params
MSK = timezone(timedelta(hours=3))

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


def fix_subcontos(conn):
    d = {
        "sale": """
        UPDATE gl.temp_tbl
        SET subconto_id = CASE
        WHEN field in ('ppvz_for_pay','retail_price') and report_type=1 and dtn_id = 2
        THEN  20
        WHEN field in ('ppvz_for_pay','retail_price') and report_type=2 and dtn_id = 2
        THEN  21
        WHEN field in ('ppvz_for_pay','retail_price') and report_type=1 and dtn_id = 1
        THEN  22
        WHEN field in ('ppvz_for_pay','retail_price') and report_type=2 and dtn_id = 1
        THEN  23
        ELSE
        subconto_id
        END        
        """,
        "delivery": """
        UPDATE gl.temp_tbl
        SET subconto_id = 36
        WHERE field = 'delivery_rub' and subconto_id is null        
        """,
        "storage": """
        UPDATE gl.temp_tbl
        SET subconto_id = 38
        WHERE field = 'storage_fee' and subconto_id is null        
        """,
    }
    for k, v in d.items():
        with conn.cursor() as cur:
            cur.execute(v)
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
        COALESCE(p.vat_rate::numeric, vr.rate::numeric) AS vat_rate,
        sc.id AS subconto_id
    FROM wb_dwh.realization_kv AS t
    
    LEFT JOIN LATERAL (
    SELECT sc1.id
    FROM public.corporate_subconto sc1
    WHERE t.bonus_type_name ~ sc1.rgex
    ORDER BY sc1.id  -- или приоритет/длина rgex, если есть логика
    LIMIT 1
    ) sc ON TRUE

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
    
    fix_subcontos(conn)


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
    x.subconto_id::int,
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
        subconto_id,
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





# --------------------
# Helpers
# --------------------
def get_env(name: str) -> str:
    v = os.getenv(name)
    if not v:
        raise RuntimeError(f"{name} is not set")
    return v


def iso_msk(dt: datetime) -> str:
    return dt.astimezone(MSK).replace(microsecond=0).isoformat()


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

CONTRACT_ID = 109 #ПОКА ТАК

CTEs = {
   
    "sale_wb": {
        "field": "retail_price",
        "ns": "11111111-1111-1111-1111-111111111111",
        "agg": ["report_type", "dtn_id"],
        "acc_id": 68,
        "description": "Продажи / Возвраты",
        "parent": None,      
        "subconto":None  
    },
    "sale_pl": {
        "field": "retail_price",
        "ns": "11111111-1111-1111-1111-111111111112",
        "agg": ["report_type", "dtn_id"],
        "acc_id": 50,
        "description": "Отражение выручки в PL",
        "parent": "sale_wb",
        "subconto":None          
    },
    "sale_vat": {
        "field": "retail_price",
        "ns": "11111111-1111-1111-1111-111111111113",
        "agg": ["report_type", "dtn_id"],
        "acc_id": 80,
        "description": "Выделение НДС с продаж / возвратов",
        "parent": "sale_wb",   
        "subconto":None      
    },
    
    "comission_wb": {
        "field": "ppvz_for_pay",
        "ns": "11111111-1111-1111-1111-111111111114",
        "agg": ["report_type", "dtn_id"],
        "acc_id": 69,
        "description": "Комиссия WB",
        "parent": "sale_wb",
        "subconto":None  
        
    },
    "comission_pl": {
        "field": "ppvz_for_pay",
        "ns": "11111111-1111-1111-1111-111111111115",
        "agg": ["report_type", "dtn_id"],
        "acc_id": 59,
        "description": "Отражение комисии WB в PL",
        "parent": "comission_wb",
        "subconto":None
       
    },
    "comission_vat": {
        "field": "ppvz_for_pay",
        "ns": "11111111-1111-1111-1111-111111111116",
        "agg": ["report_type", "dtn_id"],
        "acc_id": 31,
        "description": "Выделение НДС с комиссии WB ",
        "parent": "comission_wb",
        "subconto":None 
    },
   
    "logistic_wb": {
        "field": "delivery_rub",
        "ns": "11111111-1111-1111-1111-111111111117",
        "agg": [
            "report_type",
        ],
        "acc_id": 70,
        "description": "Логистика WB",
        "parent": "sale_wb",
        "subconto":None
       
    },
    "logistic_pl": {
        "field": "delivery_rub",
        "ns": "11111111-1111-1111-1111-111111111118",
        "agg": [
            "report_type",
        ],
        "acc_id": 60,
        "description": "Отражение расходов на логистику в PL",
        "parent": "logistic_wb",
        "subconto":None 
        
    },
    "logistic_vat": {
        "field": "delivery_rub",
        "ns": "11111111-1111-1111-1111-111111111119",
        "agg": [
            "report_type",
        ],
        "acc_id": 31,
        "description": "Выделение НДС с логистики",
        "parent": "logistic_wb",
        "subconto":None
    },
   
    "storage_wb": {
        "field": "storage_fee",
        "ns": "11111111-1111-1111-1111-111111111120",
        "agg": [
            "report_type",
        ],
        "acc_id": 71,
        "description": "Хранение WB",
        "parent": "sale_wb",
        "subconto":None
    },
    "storage_pl": {
        "field": "storage_fee",
        "ns": "11111111-1111-1111-1111-111111111121",
        "agg": [
            "report_type",
        ],
        "acc_id": 60,
        "description": "Отражение расходов WB по хранению в PL",
        "parent": "storage_wb",
        "subconto":None
    },
    "storage_vat": {
        "field": "storage_fee",
        "ns": "11111111-1111-1111-1111-111111111122",
        "agg": [
            "report_type",
        ],
        "acc_id": 31,
        "description": "Выделение НДС с Хранения WB",
        "parent": "storage_wb",
        "subconto":None
    },
   
    "acceptance_wb": {
        "field": "acceptance",
        "ns": "11111111-1111-1111-1111-111111111123",
        "agg": [
            "report_type",
        ],
        "acc_id": 72,
        "description": "Приемка WB",
        "parent": "sale_wb",
        "subconto":None 
    },
    "acceptance_pl": {
        "field": "acceptance",
        "ns": "11111111-1111-1111-1111-111111111124",
        "agg": [
            "report_type",
        ],
        "acc_id": 60,
        "description": "Отражение расходов по приемки WB в PL",
        "parent": "acceptance_wb",
        "subconto":None
    },
    "acceptance_vat": {
        "field": "acceptance",
        "ns": "11111111-1111-1111-1111-111111111125",
        "agg": [
            "report_type",
        ],
        "acc_id": 31,
        "description": "Выделение НДС с расходов по приемке WB",
        "parent": "acceptance_wb",
        "subconto":None 
    },
   
    "deduction_wb": {
        "field": "deduction",
        "ns": "11111111-1111-1111-1111-111111111126",
        "agg": [
            "report_type",
        ],
        "acc_id": 73,
        "description": "Ужержания WB",
        "parent": "sale_wb",
        "subconto":None 
    },
    "deduction_pl": {
        "field": "deduction",
        "ns": "11111111-1111-1111-1111-111111111127",
        "agg": [
            "report_type",
        ],
        "acc_id": 60,
        "description": "Отражение расходов по Удержаниям WB в PL",
        "parent": "deduction_wb",
        "subconto":None 
    },
    "deduction_vat": {
        "field": "deduction",
        "ns": "11111111-1111-1111-1111-111111111128",
        "agg": [
            "report_type",
        ],
        "acc_id": 31,
        "description": "НДС с удержаний WB",
        "parent": "deduction_wb",
        "subconto":None 
    },
    
    "penalty_wb": {
        "field": "penalty",
        "ns": "11111111-1111-1111-1111-111111111129",
        "agg": [
            "report_type",
        ],
        "acc_id": 74,
        "description": "Штрафы WB",
        "parent": "sale_wb",
        "subconto":None
    },
    "penalty_pl": {
        "field": "penalty",
        "ns": "11111111-1111-1111-1111-111111111130",
        "agg": [
            "report_type",
        ],
        "acc_id": 60,
        "description": "Отражение расходов по штрафам WB в pl",
        "parent": "penalty_wb",
        "subconto":None
    },
    
    "correction_wb": {
        "field": "additional_payment",
        "ns": "11111111-1111-1111-1111-111111111131",
        "agg": [
            "report_type",
        ],
        "acc_id": 75,
        "description": "Корректировки WB",
        "parent": "sale_wb",
        "subconto":None
    },
    "correction_pl": {
        "field": "additional_payment",
        "ns": "11111111-1111-1111-1111-111111111132",
        "agg": [
            "report_type",
        ],
        "acc_id": 52,
        "description": "Отражение корректировок WB в pl",
        "parent": "correction_wb",
        "subconto":None
    },
    
    "cashbackcommissionchange_wb": {
        "field": "cashback_commission_change",
        "ns": "11111111-1111-1111-1111-111111111133",
        "agg": [
            "report_type",
        ],
        "acc_id": 76,
        "description": "Программа лояльности участие WB",
        "parent": "sale_wb",
        "subconto":None 
    },
    "cashbackcommissionchange_pl": {
        "field": "cashback_commission_change",
        "ns": "11111111-1111-1111-1111-111111111134",
        "agg": [
            "report_type",
        ],
        "acc_id": 60,
        "description": "Отражение расходов по участию в ПЛ WB в PL",
        "parent": "cashbackcommissionchange_wb",
        "subconto":None 
    },
    "cashbackcommissionchange_vat": {
        "field": "cashback_commission_change",
        "ns": "11111111-1111-1111-1111-111111111135",
        "agg": [
            "report_type",
        ],
        "acc_id": 31,
        "description": "НДС по участию в ПЛ WB",
        "parent": "cashbackcommissionchange_wb",
        "subconto":None 
    },
    
    "cashbackamount_wb": {
        "field": "cashback_amount",
        "ns": "11111111-1111-1111-1111-111111111136",
        "agg": [
            "report_type",
        ],
        "acc_id": 77,
        "description": "Балы за ПЛ WB",
        "parent": "sale_wb",
        "subconto":None
    },
    "cashbackamount_pl": {
        "field": "cashback_amount",
        "ns": "11111111-1111-1111-1111-111111111137",
        "agg": [
            "report_type",
        ],
        "acc_id": 52,
        "description": "Отражение удержания баллов за ПЛ  WB в pl",
        "parent": "cashbackamount_wb",
        "subconto":None
    },
    
    "paymentschedule_wb": {
        "field": "payment_schedule",
        "ns": "11111111-1111-1111-1111-111111111138",
        "agg": [
            "report_type",
        ],
        "acc_id": 78,
        "description": "Комиссия за досрочный перевод",
        "parent": "sale_wb",
        "subconto":None
    },
    "paymentschedule_pl": {
        "field": "payment_schedule",
        "ns": "11111111-1111-1111-1111-111111111139",
        "agg": [
            "report_type",
        ],
        "acc_id": 52,
        "description": "Отражение комиссии за досроч перевод  WB в pl",
        "parent": "paymentschedule_wb",
        "subconto":None
    },
}

def get_id(ns):
    return f"""
    uuid_generate_v5(
            '{ns}'::uuid, 
            concat_ws('|', to_char(date_from::date, 'YYYY-MM-DD'))
            )
    """
    
def parse_fields():
    
    fields = [] 
    for k, v in CTEs.items():        
        fields.append(f"'{v['field']}'")
        field = set(fields)

    return ",\n".join(field)

def fact_query(d:dict,k):
    
    parts = str(k).split('_')   
    pref =  parts[1]
    description = d['description']
    
    id = get_id(d['ns'])
    pid = d['parent']
    if pid:
       pid = get_id(CTEs[pid]['ns']) 
    else:
        pid = "NULL"
    
    acc_id = d['acc_id']
    contract_id = CONTRACT_ID
    field = d['field']
    sc = d['subconto']    
    if sc:
       subconto_id = sc
    else:
       subconto_id = "NULL"  
        
    if str(k).startswith("comission"):
       q = f"""
       select
        {id} as id,
        {pid} as pid,
        date_from,
        {acc_id} as acc_id,
        {contract_id} as contract_id,
        sum(cr_{pref}) filter (where field = 'retail_price') 
        - 
        sum(cr_{pref}) filter (where field = 'ppvz_for_pay') 
        as dt,
        
        sum(dt_{pref}) filter (where field = 'retail_price') 
        - 
        sum(dt_{pref}) filter (where field = 'ppvz_for_pay') 
        as cr,
        '{description}' as description,
        {subconto_id} as subconto_id
        from gl.base
        where field in  ('retail_price','ppvz_for_pay')
         
        group by date_from
       """ 
       
    else:    
        q = f"""
        select
        {id} as id,
        {pid} as pid,
        date_from,
        {acc_id} as acc_id,
        {contract_id} as contract_id,
        sum(dt_{pref}) as dt,
        sum(cr_{pref}) as cr,
        '{description}' as description,
        {subconto_id} as subconto_id
        from gl.base
        where field = '{field}' 
        group by date_from
        """
    return q





def import_facts(d:dict,conn):
    queries = []
    for k,v in d.items():
        parts = str(k).split('_')            
        query = fact_query(v,k)
        queries.append(query)    
   
    q = 'UNION ALL \n'.join(queries)
    
    final_query = f"""
    INSERT INTO gl.fact (id, pid, date_from, acc_id, contract_id, dt, cr, description)
    SELECT id, pid, date_from, acc_id, contract_id, dt, cr, description
    FROM(
        {q}
    ) src
    ON CONFLICT (id) DO UPDATE
    SET
        pid         = EXCLUDED.pid,
        date_from   = EXCLUDED.date_from,
        acc_id      = EXCLUDED.acc_id,
        contract_id = EXCLUDED.contract_id,
        dt          = EXCLUDED.dt,
        cr          = EXCLUDED.cr,
        description = EXCLUDED.description
        
    WHERE
        (gl.fact.pid, gl.fact.date_from, gl.fact.acc_id, gl.fact.contract_id, gl.fact.dt, gl.fact.cr, gl.fact.description)
        IS DISTINCT FROM
        (EXCLUDED.pid, EXCLUDED.date_from, EXCLUDED.acc_id, EXCLUDED.contract_id, EXCLUDED.dt, EXCLUDED.cr, EXCLUDED.description);        
    """    
    with conn.cursor() as cur:
         cur.execute(final_query)
    conn.commit()
    
    return final_query
    
     
def make_details(conn):
    q = """
    select  
    report_type,
    sum(dt_wb) as dt_wb,
    sum(dt_vat) as dt_vat,
    sum(cr_wb) as cr_wb,
    sum(cr_vat) as cr_vat,
    sum(dt_wb - cr_wb) as amount,
    sum(dt_vat-cr_vat) as vat

    from gl.base
    where field = 'retail_price' and date_from = '2025-07-18'
    group by date_from, report_type       
    
    """
    return pd.read_sql(q,conn)
    
    



# --------------------
# MAIN
# --------------------
def main():

    conn = connect_db()
    START_DATE = "2024-03-01"
    END_DATE = "2025-01-01"

    fields = parse_fields()
    print(fields)
    create_temp_table(conn, START_DATE, END_DATE, fields)    
    make_target_tbl(conn)
    t = import_facts(CTEs,conn)
    # df = make_details(conn)
    # print(df.to_markdown())
    # print(df.to_dict(orient='records'))
    


if __name__ == "__main__":
    main()
