# # cards/upd_app/data.py
# from conns import get_duckdb_conn_with_pg, connect_db
# import pandas as pd

# def get_grid_data(upd_id) -> pd.DataFrame:
#     with get_duckdb_conn_with_pg() as conn:
#         df = conn.sql(
#             """ 
#             WITH available AS (
#                 SELECT 
#                     nm_id,
#                     list(distinct tech_size order by tech_size) as available_sizes
#                 FROM analytics.cards.sizes
#                 GROUP BY nm_id
#             ),

#             size_options AS (
#                 SELECT
#                     nm_id,
#                     list(
#                         DISTINCT concat(chrt_id::text, ' | ', tech_size)
#                         ORDER BY concat(chrt_id::text, ' | ', tech_size)
#                     ) AS size_options
#                 FROM analytics.cards.sizes
#                 GROUP BY nm_id
#             )

#             SELECT
#                 t.id,
#                 t.upd_pos,
#                 t.brand,
#                 t.upd_title,
#                 t.upd_sa_name,
#                 p.sa_name,
#                 t.nm_id,
#                 t.upd_size,
#                 s.tech_size,
#                 t.chrt_id,
#                 available.available_sizes,
#                 size_options.size_options,
#                 t.upd_qty,
#                 t.upd_price_vatless,
#                 t.upd_amount_vatadd,
#                 t.upd_vat_rate,            
#                 t.man_cost_per_unit,
#                 t.currency_code
#             FROM pg.public.upd_income_lines t            
#             LEFT JOIN analytics.cards.product p 
#                 ON p.nm_id = t.nm_id
#             LEFT JOIN analytics.cards.sizes s 
#                 ON s.chrt_id = t.chrt_id
#             LEFT JOIN available 
#                 ON available.nm_id = t.nm_id
#             LEFT JOIN size_options 
#                 ON size_options.nm_id = t.nm_id
#             WHERE upd_document_id = ?
#             """,
#             params=[upd_id]
#         ).df()

#     return df
        
    

# def get_size_options(nm_id):

#     with get_duckdb_conn_with_pg() as conn:
#         df = conn.sql(
#             """
#             SELECT DISTINCT
#                 chrt_id,
#                 tech_size
#             FROM analytics.cards.sizes
#             WHERE nm_id = ?
#             ORDER BY tech_size
#             """,
#             params=[nm_id]
#         ).df()

#     data = [
#         [str(row.chrt_id), f"{row.tech_size} ({row.chrt_id})"]
#         for row in df.itertuples()
#     ]
#     return data
    
# def update_size(row_id, chrt_id):
#     with connect_db() as conn:
#         with conn.cursor() as cur:
#             cur.execute(
#                 """
#                 UPDATE public.upd_income_lines
#                 SET chrt_id = %s
#                 WHERE id = %s
#                 """,
#                 (int(chrt_id), int(row_id))
#             )
#         conn.commit()



# cards/upd_app/data.py
from conns import get_duckdb_conn_with_pg, connect_db
import pandas as pd

def get_grid_data(upd_id) -> pd.DataFrame:
    with get_duckdb_conn_with_pg() as conn:
        df = conn.sql(
            """ 
            WITH available AS (
                SELECT 
                    nm_id,
                    list(distinct tech_size order by tech_size) as available_sizes
                FROM analytics.cards.sizes
                GROUP BY nm_id
            ),

            size_options AS (
                SELECT
                    nm_id,
                    list(
                        DISTINCT concat(chrt_id::text, ' | ', tech_size)
                        ORDER BY concat(chrt_id::text, ' | ', tech_size)
                    ) AS size_options
                FROM analytics.cards.sizes
                GROUP BY nm_id
            )

            SELECT
                t.id,
                t.upd_pos,
                t.brand,
                t.upd_title,
                t.upd_sa_name,
                p.sa_name,
                t.nm_id,
                t.upd_size,
                s.tech_size,
                t.chrt_id,
                available.available_sizes,
                size_options.size_options,
                t.upd_qty,
                t.upd_price_vatless,
                t.upd_amount_vatadd,
                -- Рассчитываем сумму без НДС
                (t.upd_price_vatless * t.upd_qty) AS upd_amount_vatless,
                t.upd_vat_rate,            
                t.man_cost_per_unit,
                t.currency_code
            FROM pg.public.upd_income_lines t            
            LEFT JOIN analytics.cards.product p 
                ON p.nm_id = t.nm_id
            LEFT JOIN analytics.cards.sizes s 
                ON s.chrt_id = t.chrt_id
            LEFT JOIN available 
                ON available.nm_id = t.nm_id
            LEFT JOIN size_options 
                ON size_options.nm_id = t.nm_id
            WHERE upd_document_id = ?
            """,
            params=[upd_id]
        ).df()

    return df
        
    

def get_size_options(nm_id):

    with get_duckdb_conn_with_pg() as conn:
        df = conn.sql(
            """
            SELECT DISTINCT
                chrt_id,
                tech_size
            FROM analytics.cards.sizes
            WHERE nm_id = ?
            ORDER BY tech_size
            """,
            params=[nm_id]
        ).df()

    data = [
        [str(row.chrt_id), f"{row.tech_size} ({row.chrt_id})"]
        for row in df.itertuples()
    ]
    return data
    
def update_size(row_id, chrt_id):
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE public.upd_income_lines
                SET chrt_id = %s
                WHERE id = %s
                """,
                (int(chrt_id), int(row_id))
            )
        conn.commit()