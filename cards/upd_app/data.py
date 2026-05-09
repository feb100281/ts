from conns import get_duckdb_conn_with_pg, connect_db
import pandas as pd

def get_grid_data(upd_id)->pd.DataFrame:
    with get_duckdb_conn_with_pg() as conn:
        df = conn.sql(
            """ 
            with a as(
                select 
                nm_id,
                list(distinct tech_size order by tech_size) as available_sizes
                from analytics.cards.sizes
                group by nm_id
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
            a.available_sizes,
            t.upd_qty,
            t.upd_price_vatless,
            t.upd_amount_vatadd,
            t.upd_vat_rate,            
            t.man_cost_per_unit,
            t.currency_code
            from pg.public.upd_income_lines t            
            left join analytics.cards.product p on p.nm_id = t.nm_id
            left join analytics.cards.sizes s on s.chrt_id = t.chrt_id
            left join a on a.nm_id = t.nm_id
            where upd_document_id = ?
            
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
    
