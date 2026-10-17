#!/usr/bin/env python3


# ------
# СКРИПТ ДЕЛАЕТ:
# - ba_distribution table
# - запуск раз в сутки в 10 утра МСК или через systemctl


import os
from datetime import datetime, timedelta, timezone
import psycopg
from psycopg.rows import dict_row

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


def fletch_accounts(conn) -> dict:
    """Возвращаем словарик с банковскими счетами для работы

    Args:
        conn (_type_): _description_
    """
    q = """
    SELECT ba_id, acc_id, currency, is_active, min_date, max_date
	FROM gl.v_bank_acounts;
    """
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(q)
        rows = cur.fetchall()
    return rows


def cash_revolution(acc_id, conn):
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
        acc_id = acc["acc_id"]
        cash_revolution(acc_id, conn)


def main(conn):

    conn = conn

    with conn.cursor() as cur:
        cur.execute("REFRESH MATERIALIZED VIEW gl.vr;")
    conn.commit()

    insert_normizized(conn)
    execute_cash_revolution(conn)

    


# scp /Users/pavelustenko/ts/utils/etl/ba_elt.py daria@82.202.197.94:/opt/wb_jobs/ba_etl.py

if __name__ == "__main__":
    main()
