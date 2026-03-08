#!/usr/bin/env python3

#--------------------------------
# Скрипт для отражения денег в GL
# Как запускать? Нужно решить
# -------------------------------

import os
from datetime import datetime, timedelta, timezone

import psycopg

# import pandas as pd

# WB expects Moscow timezone in request params
MSK = timezone(timedelta(hours=3))




# SOURCE_TABLE = "wb_dwh.realization_kv"

# SHCEMA = "gl"
# TARGET_TEMP_TABLE = f"{SHCEMA}.temp_tbl"
# TARGET_TABLE = f"{SHCEMA}.base"


# from conns import ENGINE
# from sqlalchemy import text
# import pandas as pd
# import numpy as np
# from datetime import date


# # Считаем остатки и курсовые разницы

# def get_bs_ids() -> list:
#     q = text("SELECT DISTINCT bs_acc_id FROM mv_cf_master")

#     with ENGINE.connect() as conn:
#         result = conn.execute(q)
#         return result.scalars().all()
    
# def get_dates(bs_id):
#     q = text("""
#         SELECT 
#             min(date) as start_date,
#             max(date) as end_date
#         FROM mv_cf_master
#         WHERE bs_acc_id = :bs_id
#     """)
#     with ENGINE.connect() as conn:
#         row = conn.execute(q, {"bs_id": bs_id}).first()
#         return row.start_date, row.end_date

# def get_status(bs_id)->bool:
#     q = text(
#     """
#     SELECT
#     is_active
#     from public.corporate_bankaccount
#     where bs_acc_id = :bs_id
#     """
#     )
#     with ENGINE.connect() as conn:
#         row = conn.execute(q, {"bs_id": bs_id}).first()
#         return row.is_active
    


# def generate_series(bs_id):
#     start, finish = get_dates(bs_id)
    
#     is_active = get_status(bs_id)
    
    
#     finish = finish if not is_active else date.today()

#     q = text("""
#     with cf as(

#         SELECT

#         date,
#         bs_acc_id,
#         sum(dt) as dt,
#         sum(cr) as cr,
#         sum(dt-cr) as amount
#         from mv_cf_master
#         where bs_acc_id = :bs_id
#         group by bs_acc_id, date
#         order by bs_acc_id, date

#         ),
#         tl as (
#         SELECT generate_series(
#                 :start,
#                 :finish,
#                 interval '1 day'
#             )::date AS date

#         ),

#         dayly_balace as (

#         SELECT 
#             x.date,
#             x.bs_acc_id,
#             x.dt,
#             x.cr,
#             x.amount,
#             SUM(x.amount) OVER (
#                 PARTITION BY x.bs_acc_id
#                 ORDER BY x.date
#             ) AS eb,
#             ba.currency
#         FROM (
#             SELECT
#                 s.date,
#                 :bs_id AS bs_acc_id,
#                 COALESCE(t.dt, 0) AS dt,
#                 COALESCE(t.cr, 0) AS cr,
#                 COALESCE(t.amount, 0) AS amount
#             FROM tl AS s
#             LEFT JOIN cf AS t 
#                 ON s.date = t.date
#             AND t.bs_acc_id = :bs_id
#         ) AS x
#         JOIN public.corporate_bankaccount AS ba 
#             ON ba.bs_acc_id = x.bs_acc_id
#         ORDER BY x.date
#         ),

#         fx_rates as (

#         SELECT
#         d.date,
#         d.bs_acc_id,
#         d.dt, 
#         d.cr,
#         d.amount,
#         COALESCE(LAG(d.eb) OVER (ORDER BY d.date),0.0) AS bb,
#         d.eb,
#         d.currency,
#         COALESCE(fx.rate,1) as fx,
#         COALESCE(LAG(COALESCE(fx.rate,1)) OVER (ORDER BY d.date),fx.rate) AS prev_fx
#         from dayly_balace as d
#         left join macro_currencyrate as fx on 
#             d.date = fx.date 
#             and d.currency=fx.currency
#         )
#         SELECT
#         date,
#         bs_acc_id,
#         bb,
#         eb,
#         dt as dt_turnover,
#         cr as cr_turnover,
#         dt-cr as turnover,
#         round(bb * fx,2) as bb_base,
#         round(eb * fx,2) as eb_base,        
#         round((eb-bb) * fx,2) as turnover_base,
#         currency,
#         fx - prev_fx as fx_dif,

#         round(bb*(fx-prev_fx),2) as fxs
#         from fx_rates
#     """
#     )

#     with ENGINE.connect() as conn:
#         result = conn.execute(q, {"bs_id":bs_id,"start": start, "finish": finish})
#         return pd.DataFrame(result).fillna(0)   

# acc_list = get_bs_ids() 
# dfs = []
# for acc in acc_list:
#     dfs.append(generate_series(acc))
    
# df:pd.DataFrame = pd.concat(dfs,ignore_index=True)

# # d = pd.DataFrame()

# df.to_sql('temp_cf_ballance',if_exists='replace',index=False,con=ENGINE)