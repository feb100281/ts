
import duckdb
from duckdb import DuckDBPyConnection
import pandas as pd

duck_file = "/Users/daria/Documents/Projects/ts/data/analytics.duckdb"

def connect_duck_db(file) -> DuckDBPyConnection:
    "conn establish"
    return duckdb.connect(file)


def get_analysis(conn:DuckDBPyConnection):
    rel = conn.sql(
        """ 
        SELECT
            nm_id,
            sa_name,
            COALESCE(count(value) FILTER (WHERE dtn_id = 2 AND field = 'retail_price'), 0) -
            COALESCE(count(value) FILTER (WHERE dtn_id = 1 AND field = 'retail_price'), 0) AS qty,

            COALESCE(sum(value) FILTER (WHERE dtn_id = 2 AND field = 'retail_price'), 0) -
            COALESCE(sum(value) FILTER (WHERE dtn_id = 1 AND field = 'retail_price'), 0) AS amount
        FROM sales
        WHERE date_from >= '2024-01-01'
        AND date_from < '2026-01-01'
        group by nm_id,
            sa_name
        """
    )
    
    rel.show()
    

    
    
    
    
def main():
    conn = connect_duck_db(duck_file)
    get_analysis(conn)
    
main()
    

