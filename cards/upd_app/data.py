from conns import get_duckdb_conn, connect_db
import pandas as pd

def get_grid_data(upd_id)->pd.DataFrame:
    with get_duckdb_conn() as conn:
        df = conn.sql(
            """ 
            SELECT
            *
            from pg.public.upd_income_lines
            where upd_document_id = ?
            """,
            params=[upd_id]
        ).df()
        
    
    return df
        
