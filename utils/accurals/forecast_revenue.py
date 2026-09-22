import psycopg
from psycopg.rows import dict_row
import pandas as pd
import numpy as np
from pprint import pprint
from psycopg import Connection
from prophet import Prophet

def connect_db():
    return psycopg.connect(
        dbname="ts_db",  # DB_NAME
        user="ts_user",  # DB_USER
        password="Dec8108079",  # DB_PASSWORD
        host="127.0.0.1",  # DB_HOST
        port="5433",  # DB_PORT
        connect_timeout=10,
    )


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
    
    START_DATE = '2024-01-31'
    END_DATE = '2026-03-15'
    FORECAST_DATE = '2026-12-31'
    
    data, forecast, model = revenue_prophet_forecast(conn, START_DATE, END_DATE, FORECAST_DATE)
    
    
    pprint(forecast)
    


if __name__ == "__main__":
    main()
    