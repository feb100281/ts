# #!/usr/bin/env python3

# # Функция рассчета депозита по кэшу

# import psycopg
# from psycopg.rows import dict_row
# import pandas as pd
# import numpy as np
# from pprint import pprint
# from psycopg import Connection


# # Подключаемся к базе данных
# def connect_db():
#     return psycopg.connect(
#         dbname="ts_db",  # DB_NAME
#         user="ts_user",  # DB_USER
#         password="Dec8108079",  # DB_PASSWORD
#         host="127.0.0.1",  # DB_HOST
#         port="5433",  # DB_PORT
#         connect_timeout=10,
#     )


# # Загружаем строку для теста
# def load_row_for_test(conn, condition_id):
#     sql = f"""
#         SELECT *
#         FROM gl.accurals_args
#         WHERE fn_id IS NOT NULL
#         AND condition_id = {condition_id}
#     """
#     with conn.cursor(row_factory=dict_row) as cur:
#         cur.execute(sql)
#         return cur.fetchall()


# def update_gl(bs_acc, pl_acc, deposit_sc_id, contract_id, conn: Connection):

#     sql = """
#     with src as (
#         SELECT
#         id,
#         pid,
#         date_from,
#         acc_id,
#         contract_id,
#         dt,
#         cr,
#         description,
#         subconto_id,
#         company_id,
#         chapter
#         from gl.fact where contract_id = %s
#         ),

#         src_a as (
#         SELECT
#         gen_random_uuid()::uuid as id,
#         s.id::uuid as pid,
#         s.date_from,
#         %s as acc_id,
#         s.contract_id,
#         s.cr as dt,
#         s.dt as cr,
#         s.description,
#         s.subconto_id,
#         s.company_id,
#         'PL deposits' as chapter
#         from src s
#         where subconto_id = %s

#         UNION ALL

#         SELECT
#         gen_random_uuid()::uuid as id,
#         s.id::uuid as pid,
#         s.date_from,
#         %s as acc_id,
#         s.contract_id,
#         s.dt as dt,
#         s.cr as cr,
#         s.description,
#         s.subconto_id,
#         s.company_id,
#         'BS deposits' as chapter
#         from src s
#         where subconto_id <> %s

#         ),

#         src_m as (

#         SELECT * FROM src_a

#             UNION ALL

#             SELECT
#                 gen_random_uuid()::uuid      AS id,
#                 NULL::uuid                   AS pid,
#                 t.date::date                 AS date_from,
#                 t.acc_id::bigint             AS acc_id,
#                 t.contract_id::bigint        AS contract_id,
#                 round(t.dt * 100, 0)::bigint AS dt,
#                 round(t.cr * 100, 0)::bigint AS cr,
#                 t.temp::text                 AS description,
#                 t.cfitem_id::bigint          AS subconto_id,
#                 t.owner_id::bigint           AS company_id,
#                 'MANUAL_TRS'::text           AS chapter
#             FROM public.grossbook_manual t
#             WHERE EXISTS (
#                 SELECT 1
#                 FROM src s
#                 WHERE s.acc_id = t.acc_id
#             )
#         ),

#         filtered AS (
#             SELECT *
#             FROM src_m s
#             WHERE COALESCE(s.dt, 0) <> 0
#             OR COALESCE(s.cr, 0) <> 0
#         )

#         INSERT INTO gl.fact (
#             id,
#             pid,
#             date_from,
#             acc_id,
#             contract_id,
#             dt,
#             cr,
#             description,
#             subconto_id,
#             company_id,
#             chapter
#         )
#         SELECT
#             id,
#             pid,
#             date_from,
#             acc_id,
#             contract_id,
#             dt,
#             cr,
#             description,
#             subconto_id,
#             company_id,
#             chapter
#         FROM filtered
#         ON CONFLICT (id) DO UPDATE
#         SET
#             pid         = EXCLUDED.pid,
#             date_from   = EXCLUDED.date_from,
#             acc_id      = EXCLUDED.acc_id,
#             contract_id = EXCLUDED.contract_id,
#             dt          = EXCLUDED.dt,
#             cr          = EXCLUDED.cr,
#             description = EXCLUDED.description,
#             subconto_id = EXCLUDED.subconto_id,
#             company_id  = EXCLUDED.company_id,
#             chapter     = EXCLUDED.chapter
#         WHERE
#             (gl.fact.pid,
#             gl.fact.date_from,
#             gl.fact.acc_id,
#             gl.fact.contract_id,
#             gl.fact.dt,
#             gl.fact.cr,
#             gl.fact.description,
#             gl.fact.subconto_id,
#             gl.fact.company_id,
#             gl.fact.chapter)
#         IS DISTINCT FROM
#             (EXCLUDED.pid,
#             EXCLUDED.date_from,
#             EXCLUDED.acc_id,
#             EXCLUDED.contract_id,
#             EXCLUDED.dt,
#             EXCLUDED.cr,
#             EXCLUDED.description,
#             EXCLUDED.subconto_id,
#             EXCLUDED.company_id,
#             EXCLUDED.chapter);
#             """
#     with conn.cursor() as cur:
#         cur.execute(sql, (contract_id, pl_acc, deposit_sc_id, bs_acc, deposit_sc_id))
#     conn.commit()


# def cashbased_deposits(conn, **args):
#     param = args.get("params_json", None)

#     # Получаем счет для начислений
#     acc_bs_id = args.get("acc_bs_id", None)
#     subconto_bs_id = args.get("subconto_bs_id", None)

#     acc_pl_id = args.get("acc_bs_id", None)
#     acc_pl_id = args.get("subconto_pl_id", None)

#     contract_id = args.get("contract_id", None)

#     q_filter = param.get("Субконто процентов", None)

#     # Что бы не падало не выполняем функцию если нет условий и счета
#     if not param or not q_filter:
#         return "Не указаны ключевые параметры param, Субконто процентов"

#     update_gl(
#         bs_acc=acc_bs_id,
#         pl_acc=acc_pl_id,
#         deposit_sc_id=q_filter,
#         contract_id=contract_id,
#         conn=conn,
#     )

#     return "депозиты разнесены"


# def main():
#     conn = connect_db()

#     # df = annual_fixed(conn,**rows[0])
#     # df.to_excel('rp.xlsx')

#     conn.close()


# if __name__ == "__main__":
#     main()






#!/usr/bin/env python3

import psycopg
from psycopg.rows import dict_row
from psycopg import Connection


def connect_db():
    return psycopg.connect(
        dbname="ts_db",
        user="ts_user",
        password="Dec8108079",
        host="127.0.0.1",
        port="5433",
        connect_timeout=10,
    )


def load_row_for_test(conn, condition_id):
    sql = """
        SELECT *
        FROM gl.accurals_args
        WHERE fn_id IS NOT NULL
          AND condition_id = %s
    """
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(sql, (condition_id,))
        return cur.fetchall()


def update_gl(bs_acc, pl_acc, deposit_sc_id, contract_id, conn: Connection):
    """
    Логика:
    1. Берем только исходные проводки из gl.fact по договору,
       исключая ранее созданные служебные главы.
    2. Удаляем старые служебные строки по этому договору:
       'PL deposits', 'BS deposits', 'MANUAL_TRS'
    3. Формируем новые служебные строки.
    4. Добавляем ручные проводки только из grossbook_manual по этому договору.
    """

    sql = """
    -- 1. Удаляем ранее рассчитанные служебные проводки по договору
    DELETE FROM gl.fact
    WHERE contract_id = %(contract_id)s
      AND chapter IN ('PL deposits', 'BS deposits', 'MANUAL_TRS');

    -- 2. Формируем и вставляем заново
    WITH src AS (
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
        FROM gl.fact
        WHERE contract_id = %(contract_id)s
          AND chapter NOT IN ('PL deposits', 'BS deposits', 'MANUAL_TRS')
    ),

    src_a AS (
        -- PL deposits: меняем местами dt/cr для нужного subconto
        SELECT
            gen_random_uuid()::uuid AS id,
            s.id::uuid AS pid,
            s.date_from,
            %(pl_acc)s AS acc_id,
            s.contract_id,
            s.cr AS dt,
            s.dt AS cr,
            s.description,
            s.subconto_id,
            s.company_id,
            'PL deposits'::text AS chapter
        FROM src s
        WHERE s.subconto_id = %(deposit_sc_id)s

        UNION ALL

        -- BS deposits: оставляем dt/cr как есть для остальных строк
        SELECT
            gen_random_uuid()::uuid AS id,
            s.id::uuid AS pid,
            s.date_from,
            %(bs_acc)s AS acc_id,
            s.contract_id,
            s.dt AS dt,
            s.cr AS cr,
            s.description,
            s.subconto_id,
            s.company_id,
            'BS deposits'::text AS chapter
        FROM src s
        WHERE s.subconto_id <> %(deposit_sc_id)s
    ),

    manual_src AS (
        SELECT
            -- детерминированный UUID, чтобы одна и та же ручная проводка
            -- не плодилась бесконечно, если потом решишь вернуться к UPSERT
            md5('manual_' || t.id::text)::uuid AS id,
            NULL::uuid AS pid,
            t.date::date AS date_from,
            t.acc_id::bigint AS acc_id,
            t.contract_id::bigint AS contract_id,
            round(COALESCE(t.dt, 0) * 100, 0)::bigint AS dt,
            round(COALESCE(t.cr, 0) * 100, 0)::bigint AS cr,
            t.temp::text AS description,
            t.cfitem_id::bigint AS subconto_id,
            t.owner_id::bigint AS company_id,
            'MANUAL_TRS'::text AS chapter
        FROM public.grossbook_manual t
        WHERE t.contract_id = %(contract_id)s
          AND (COALESCE(t.dt, 0) <> 0 OR COALESCE(t.cr, 0) <> 0)
    ),

    final_rows AS (
        SELECT * FROM src_a
        UNION ALL
        SELECT * FROM manual_src
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
    FROM final_rows
    WHERE COALESCE(dt, 0) <> 0
       OR COALESCE(cr, 0) <> 0;
    """

    params = {
        "contract_id": contract_id,
        "bs_acc": bs_acc,
        "pl_acc": pl_acc,
        "deposit_sc_id": deposit_sc_id,
    }

    with conn.cursor() as cur:
        cur.execute(sql, params)

    conn.commit()


def cashbased_deposits(conn, **args):
    param = args.get("params_json", {}) or {}

    acc_bs_id = args.get("acc_bs_id")
    acc_pl_id = args.get("acc_pl_id")
    contract_id = args.get("contract_id")

    q_filter = param.get("Субконто процентов")

    missing = []
    if not acc_bs_id:
        missing.append("acc_bs_id")
    if not acc_pl_id:
        missing.append("acc_pl_id")
    if not contract_id:
        missing.append("contract_id")
    if not q_filter:
        missing.append("params_json['Субконто процентов']")

    if missing:
        return f"Не указаны обязательные параметры: {', '.join(missing)}"

    update_gl(
        bs_acc=acc_bs_id,
        pl_acc=acc_pl_id,
        deposit_sc_id=q_filter,
        contract_id=contract_id,
        conn=conn,
    )

    return "депозиты разнесены"


def main():
    conn = connect_db()
    conn.close()


if __name__ == "__main__":
    main()
