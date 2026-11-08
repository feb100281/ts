#!/usr/bin/env python3


# ------
# СКРИПТ ДЕЛАЕТ:
# таблицу wb_destribution ддя распределения WB
# - запуск раз в сутки в 10 утра МСК или через systemctl
# - sudo systemctl start wb-etl.service
# - sudo journalctl -u wb-etl -n 50
# - sudo systemctl start wb-etl.timer
# - sudo systemctl start wb-etl.timer
# - sudo systemctl status wb-etl.timer


import os
from datetime import datetime, timedelta, timezone
import psycopg

CONTRACT_ID = 109
CF_ACCOUNT = 46

FIELD = {
    "retail_price": {
        "acc_ws": 46,
        "acc_pl": 48,
        "acc_vat": 80,
        "subconto_ws": (52, 87),
        "sunconto_pl": (90, 91),
        "sunconto_vat": (52, 87),
        "ns": "11111111-1111-1111-1111-111111111111",
    },
    "retail_amount": {
        "acc_ws": 91,
        "subconto_ws": (52, 87),
        "ns": "11111111-1111-1111-1111-111111111113",
    },
    "ppvz_for_pay": {
        "acc_ws": 92,
        "subconto_ws": (52, 87),
        "ns": "11111111-1111-1111-1111-111111111114",
    },
    "comission": {
        "acc_ws": 46,
        "acc_pl": 59,
        "acc_vat": 81,
        "subconto_ws": (52, 87),
        "sunconto_pl": (90, 91),
        "sunconto_vat": (52, 87),
        "ns": "11111111-1111-1111-1111-111111111115",
    },
    "delivery_rub": {
        "acc_ws": 46,
        "acc_pl": 60,
        "acc_vat": 82,
        "subconto_ws": (78, 97),
        "sunconto_pl": (108, 109),
        "sunconto_vat": (78, 97),
        "ns": "11111111-1111-1111-1111-111111111116",
    },
    "storage_fee": {
        "acc_ws": 46,
        "acc_pl": 60,
        "acc_vat": 82,
        "subconto_ws": (79, 98),
        "sunconto_pl": (111, 112),
        "sunconto_vat": (79, 98),
        "ns": "11111111-1111-1111-1111-111111111117",
    },
    "acceptance": {
        "acc_ws": 46,
        "acc_pl": 60,
        "acc_vat": 82,
        "subconto_ws": (80, 99),
        "sunconto_pl": (114, 115),
        "sunconto_vat": (80, 99),
        "ns": "11111111-1111-1111-1111-111111111118",
    },
    "deduction": {
        "acc_ws": 46,
        "acc_pl": 62,
        "acc_vat": 82,
        "subconto_ws": (81, 100),
        "sunconto_pl": (118, 119),
        "sunconto_vat": (81, 100),
        "ns": "11111111-1111-1111-1111-111111111119",
    },
    "penalty": {
        "acc_ws": 46,
        "acc_pl": 60,
        "subconto_ws": (82, 101),
        "sunconto_pl": (121, 122),
        "ns": "11111111-1111-1111-1111-111111111120",
    },
    "additional_payment": {
        "acc_ws": 46,
        "acc_pl": 49,
        "subconto_ws": (83, 102),
        "sunconto_pl": (125, 126),
        "ns": "11111111-1111-1111-1111-111111111121",
    },
    "cashback_commission_change": {
        "acc_ws": 46,
        "acc_pl": 62,
        "acc_vat": 82,
        "subconto_ws": (84, 103),
        "sunconto_pl": (127, 128),
        "sunconto_vat": (84, 103),
        "ns": "11111111-1111-1111-1111-111111111122",
    },
    "cashback_amount": {
        "acc_ws": 46,
        "acc_pl": 62,
        # "acc_vat":82,
        "subconto_ws": (85, 104),
        "sunconto_pl": (129, 130),
        # "sunconto_vat":(84,103),
        "ns": "11111111-1111-1111-1111-111111111123",
    },
    "payment_schedule": {
        "acc_ws": 46,
        "acc_pl": 62,
        "subconto_ws": (86, 95),
        "sunconto_pl": (132, 133),
        "ns": "11111111-1111-1111-1111-111111111124",
    },
}

# --------------------
# DB CONFIG
# --------------------
SOURCE_TABLE = "wb_dwh.realization_kv"

SHCEMA = "gl"
TARGET_TEMP_TABLE = f"{SHCEMA}.temp_tbl"
TARGET_TABLE = f"{SHCEMA}.base"

MSK = timezone(timedelta(hours=3))


def get_env(name: str) -> str:
    v = os.getenv(name)
    if not v:
        raise RuntimeError(f"{name} is not set")
    return v


def iso_msk(dt: datetime) -> str:
    return dt.astimezone(MSK).replace(microsecond=0).isoformat()


def connect_db():
    return psycopg.connect(
        dbname=get_env("DB_NAME"),
        user=get_env("DB_USER"),
        password=get_env("DB_PASSWORD"),
        host=get_env("DB_HOST"),
        port=get_env("DB_PORT"),
        connect_timeout=10,
    )


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


def parse_fields():

    fields = list(FIELD.keys())
    field = {f"'{f}'" for f in fields}
    return ",\n".join(field)


def main():

    conn = connect_db()

    date_to_msk = datetime.now(timezone.utc).astimezone(MSK)
    date_from_msk = date_to_msk - timedelta(days=2)

    DATE_FROM = iso_msk(date_from_msk)
    DATE_TO = iso_msk(date_to_msk)

    with conn.cursor() as cur:
        cur.execute("REFRESH MATERIALIZED VIEW gl.vr;")
    conn.commit()

    fields = parse_fields()
    create_temp_table(conn, DATE_FROM, DATE_TO, fields)
    make_target_tbl(conn)
    wb_distribution(conn)
    conn.close()


# scp /Users/pavelustenko/ts/utils/etl/wb_elt.py daria@82.202.197.94:/opt/wb_jobs/wb_etl.py

if __name__ == "__main__":
    main()
