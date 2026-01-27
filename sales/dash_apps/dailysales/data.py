# Данные для дневного отчета

from django.db import connection
import pandas as pd
import numpy as np
from dateutil.relativedelta import relativedelta


def get_month_data(date):
    d = pd.to_datetime(date).date()

    ms = d.replace(day=1)
    me = d

    ms_prev = ms - relativedelta(years=1)
    me_prev = me - relativedelta(years=1)
    
    

    q = """
        SELECT *
        FROM mv_sales_daily
        WHERE date >= %(ms)s AND date < %(me)s
        UNION ALL
        SELECT *
        FROM mv_sales_daily
        WHERE date >= %(ms_prev)s AND date < %(me_prev)s
    """

    with connection.cursor() as cur:
        cur.execute(q, {
            "ms": ms, "me": me,
            "ms_prev": ms_prev, "me_prev": me_prev
        })
        rows = cur.fetchall()
        cols = [desc.name for desc in cur.description]
    return pd.DataFrame(rows, columns=cols)

def get_ytd_data(date):
    d:pd.Timestamp = pd.to_datetime(date).date()

    ms = d.replace(month = 1, day=1)
    me = d

    ms_prev = ms - relativedelta(years=1)
    me_prev = me - relativedelta(years=1)
    

    q = """
    SELECT 
    (date_trunc('month', date) 
    + interval '1 month' 
    - interval '1 day')::date as date,
    sum(amount) as amount,
    sum(revenue) as revenue,
    sum(quant) as quant,
    sum(sales) as sales,
    sum(rtr) as rtr
    from mv_sales_daily 
    WHERE date >= %(ms)s AND date < %(me)s
    group by (date_trunc('month', date) 
    + interval '1 month' 
    - interval '1 day')::date

    union all

    SELECT 
    (date_trunc('month', date) 
    + interval '1 month' 
    - interval '1 day')::date as date,
    sum(amount) as amount,
    sum(revenue) as revenue,
    sum(quant) as quant,
    sum(sales) as sales,
    sum(rtr) as rtr
    from mv_sales_daily 
    WHERE date >= %(ms_prev)s AND date < %(me_prev)s
    group by (date_trunc('month', date) 
    + interval '1 month' 
    - interval '1 day')::date
    """
    with connection.cursor() as cur:
        cur.execute(q, {
            "ms": ms, "me": me,
            "ms_prev": ms_prev, "me_prev": me_prev
        })
        rows = cur.fetchall()
        cols = [desc.name for desc in cur.description]
    return pd.DataFrame(rows, columns=cols)
    