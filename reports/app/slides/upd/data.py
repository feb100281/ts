from conns import get_duckdb_conn_with_opt

from ...queries import BaseQueries

bq = BaseQueries()

def get_upd_data():
      
    
    return bq.upd_documents()
    
         
def get_inventorie(cut_off_date):
    
    with get_duckdb_conn_with_opt() as con:
        df = con.execute(
            """ 
            SELECT
                x.period,
                x.year,
                x.dt,
                x.cr,

                SUM(x.dt) OVER (
                    ORDER BY x.year, x.quarter
                ) AS dt_cum,

                SUM(x.cr) OVER (
                    ORDER BY x.year, x.quarter
                ) AS cr_cum,


                SUM(x.dt) OVER (
                    ORDER BY x.year, x.quarter
                ) -

                SUM(x.cr) OVER (
                    ORDER BY x.year, x.quarter
                ) as inventories



            FROM (

                SELECT
                    year(date_from) AS year,
                    quarter(date_from) AS quarter,

                    CONCAT(
                        year(date_from),
                        ' Q',
                        quarter(date_from)
                    ) AS period,

                    ROUND(
                        SUM(dt / 100.0),
                        2
                    ) AS dt,

                    ROUND(
                        SUM(cr / 100.0),
                        2
                    ) AS cr

                FROM inventories.inv_gl_final
                where date_from > ?

                GROUP BY
                    year(date_from),
                    quarter(date_from)

            ) x

            ORDER BY
                x.year,
                x.quarter
            """,
            parameters=[cut_off_date]
        ).df()
    
    return df
         
