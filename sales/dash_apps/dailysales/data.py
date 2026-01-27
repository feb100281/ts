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
        SELECT *, 'this_year' AS period
        FROM mv_sales_daily
        WHERE date >= %(ms)s AND date < %(me)s
        UNION ALL
        SELECT *, 'last_year' AS period
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