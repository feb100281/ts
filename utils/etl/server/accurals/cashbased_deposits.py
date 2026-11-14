
import psycopg
from psycopg.rows import dict_row
import pandas as pd
import numpy as np
from pprint import pprint
from psycopg import Connection

def update_gl(bs_acc, pl_acc, bs_sc, pl_sc, filter, contract_id, conn: Connection):

    sql = """
    with src as (
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
        from gl.fact where contract_id = %s
        ),

        src_a as (
        SELECT
        gen_random_uuid()::uuid as id,
        s.id::uuid as pid,
        s.date_from,
        %s as acc_id,
        s.contract_id,
        s.cr as dt,
        s.dt as cr,
        s.description,
        %s as subconto_id,
        s.company_id,
        'PL deposits' as chapter
        from src s
        where subconto_id = %s

        UNION ALL

        SELECT
        gen_random_uuid()::uuid as id,
        s.id::uuid as pid,
        s.date_from,
        %s as acc_id,
        s.contract_id,
        s.cr as dt,
        s.dt as cr,
        s.description,
        %s as subconto_id,
        s.company_id,
        'BS deposits' as chapter
        from src s
        where subconto_id <> %s

        ),

        src_m as (

        SELECT * FROM src_a

            UNION ALL

            SELECT
                gen_random_uuid()::uuid      AS id,
                NULL::uuid                   AS pid,
                t.date::date                 AS date_from,
                t.acc_id::bigint             AS acc_id,
                t.contract_id::bigint        AS contract_id,
                round(t.dt * 100, 0)::bigint AS dt,
                round(t.cr * 100, 0)::bigint AS cr,
                t.temp::text                 AS description,
                t.cfitem_id::bigint          AS subconto_id,
                t.owner_id::bigint           AS company_id,
                'MANUAL_TRS'::text           AS chapter
            FROM public.grossbook_manual t
            WHERE EXISTS (
                SELECT 1
                FROM src s
                WHERE s.acc_id = t.acc_id
            )
        ),

        filtered AS (
            SELECT *
            FROM src_a s
            WHERE COALESCE(s.dt, 0) <> 0
            OR COALESCE(s.cr, 0) <> 0
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
        FROM filtered
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
            gl.fact.chapter)
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
            EXCLUDED.chapter);
            """
    with conn.cursor() as cur:
        cur.execute(sql, (contract_id, 
                          pl_acc, 
                          pl_sc,
                          filter,                          
                          bs_acc, 
                          bs_sc,
                          filter,
                          ))
    conn.commit()


def cashbased_deposits(conn, **args):
    param = args.get("params_json", None)

    # Получаем счет для начислений
    acc_bs_id = args.get("acc_bs_id", None)
    subconto_bs_id = args.get("subconto_bs_id", None)
    

    acc_pl_id = args.get("acc_pl_id", None)
    subconto_pl_id = args.get("subconto_pl_id", None)

    contract_id = args.get("contract_id", None)

    q_filter = param.get("Субконто процентов", None)

    # Что бы не падало не выполняем функцию если нет условий и счета
    if not param or not q_filter:
        return "Не указаны ключевые параметры param, Субконто процентов"

    update_gl(
        bs_acc=acc_bs_id,
        pl_acc=acc_pl_id,
        bs_sc=subconto_bs_id,
        pl_sc=subconto_pl_id,
        filter=q_filter,
        contract_id=contract_id,
        conn=conn,
    )

    return "депозиты разнесены"


# [{'acc_bs_id': 10,
#   'acc_pl_id': 49,
#   'acc_st_id': 110,
#   'condition_id': 50,
#   'contract_id': 87,
#   'date_finish': None,
#   'date_start': None,
#   'fn_id': 7,
#   'params_json': {'Субконто процентов': 46},
#   'python_path': '/opt/wb_jobs/accurals/cashbased.py',
#   'server_path': '/opt/wb_jobs/accurals/cashbased_deposits.py',
#   'subconto_bs_id': None,
#   'subconto_pl_id': 180,
#   'vat_json': {'2023-01-01': 20,
#                '2024-01-01': 20,
#                '2025-01-01': 20,
#                '2026-01-01': 22},
#   'vat_mode': 'exempt'}]



def main(conn, **args):
    
    print(cashbased_deposits(conn, **args))


if __name__ == "__main__":
    main()
