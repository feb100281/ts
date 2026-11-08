# Планировщик WB
# Расчитывает доходную часть по WB и расходы связанные с реализацией товаров

import psycopg
from psycopg.rows import dict_row
import pandas as pd
import numpy as np
from pprint import pprint
from psycopg import Connection
from prophet import Prophet
from conns import connect_db, get_duckdb_conn_str
import duckdb # Просто бомба


# Глобальные переменные уберем потом

SUBCONTOS = [52,87]



def data_analisys():
    sql = """
        select
        date_from,
        nm_id,
        report_type,
        son_id,
        dtn_id,
        pmt_processing_id,
        field,
        value
        from pg.wb_dwh.realization_kv
        where quantity <> 2
        and date_from > '2024-12-31' and date_from <= CURRENT_DATE 
    """

    con = duckdb.connect()
    con.execute("INSTALL postgres;")
    con.execute("LOAD postgres;")

    conn_str = get_duckdb_conn_str()

    con.execute(f"""
        ATTACH '{conn_str}'
        AS pg (TYPE postgres);
    """)
    # con.execute("""
    # COPY (
    #     SELECT
    #         date_from,
    #         nm_id,
    #         report_type,
    #         son_id,
    #         dtn_id,
    #         pmt_processing_id,
    #         field,
    #         value
    #     FROM pg.wb_dwh.realization_kv
    #     WHERE quantity <> 2
    #     AND date_from > DATE '2024-12-31'
    #     AND date_from <= CURRENT_DATE
    # ) TO 'realization_stage.parquet' (FORMAT parquet);
    # """)
    
    res = con.sql("""
    SELECT 
    date_from,
    sum(value) filter (where  field = 'retail_price' and dtn_id = 2) as sales, 
    sum(value) filter (where  field = 'retail_price' and dtn_id = 1) as returns,
    avg(value) filter (where  field = 'retail_price' and dtn_id = 2) as sales_av, 
    avg(value) filter (where  field = 'retail_price' and dtn_id = 1) as returns_av,
    count(value) filter (where  field = 'retail_price' and dtn_id = 2) as sales_qt,
    count(value) filter (where  field = 'retail_price' and dtn_id = 1) as returns_qt
    
    FROM '/Users/pavelustenko/ts/utils/forecast/realization_stage.parquet'
    
    group by date_from
    order by 1
""")
    wa_data = con.sql("""
                      SELECT
                      date_from,
                      sales_av,
                      returns_av,
                      COALESCE(sales,0) - COALESCE(returns,0) as total_sold,
                      COALESCE(sales_qt,0) - COALESCE(returns_qt,0) as total_qt,
                      (COALESCE(sales,0) - COALESCE(returns,0)) / 
                      (COALESCE(sales_qt,0) - COALESCE(returns_qt,0)) as wa
                      from res
                      
                      """)


   
    
    
    return wa_data



# Делаем forecast по доходной части и записываем его в gl.forecast

def get_forecast_data(conn, start_date, end_date):
    SQL = """
    SELECT
    date_from as ds,
    sum(dt-cr) as y
    from gl.fact
    where acc_id = 46 and subconto_id in (52,87)
    and date_from > %s and date_from <= %s
    group by date_from
    order by 1  
    """
    
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(SQL,(start_date,end_date))        
        rows = cur.fetchall()
    
    df = pd.DataFrame(rows)
    
    if df.empty:
        return df

    df["ds"] = pd.to_datetime(df["ds"])
    df["y"] = pd.to_numeric(df["y"], errors="coerce")
    df = df.dropna(subset=["ds", "y"]).sort_values("ds")

    return df

def revenue_prophet_forecast(conn, start_date, end_date, forecast_period, freq="D"):
    
    #Получаем данные для погноза
    data = get_forecast_data(conn, start_date, end_date)
    model = Prophet(
        yearly_seasonality=True,
        weekly_seasonality=True,
        daily_seasonality=False,
    )
    periods = (pd.to_datetime(forecast_period) - pd.to_datetime(end_date)).days

    model.fit(data)

    future = model.make_future_dataframe(periods=periods, freq=freq)
    forecast = model.predict(future)

    return data, forecast, model


def main():
    conn = connect_db()
    print(get_duckdb_conn_str())
   
    START_DATE = '2024-01-31'
    END_DATE = '2026-03-15'
    FORECAST_DATE = '2026-12-31'
    
    res = data_analisys()
    res.show()
    df = res.df()
    df['sales_av'] = df['sales_av'] / 100
    df['returns_av'] = df['returns_av'] / 100
    df['total_sold'] = df['total_sold'] / 100
    df['wa'] = df['wa'] / 100
    df.to_excel('tr.xlsx')
    
    # data, forecast, model = revenue_prophet_forecast(conn, START_DATE, END_DATE, FORECAST_DATE)
    
    
   
    

if __name__ == "__main__":
    main()
    