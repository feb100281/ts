#Это функции для расчета выручки

from prophet import Prophet
import pandas as pd
import numpy as np
from conns import get_duckdb_conn
from duckdb import DuckDBPyConnection
from pprint import pprint


def calculation(frc:pd.DataFrame,stats:dict,dt_from):
    
    dt_fr = pd.to_datetime(dt_from)    
    forecast = frc.copy()
    forecast['ds'] = pd.to_datetime(forecast['ds'])
    forecast = forecast[forecast['ds'] >= dt_fr]
    
    date_from = forecast['ds'].to_numpy()
    tot_revenue = forecast['yhat'].to_numpy(dtype=int)
    
    #Выручка
    wa_shear = stats['wb_share']    
    buyback_revenue: np.ndarray = (
    (tot_revenue * wa_shear / 100)
    .round(0)
    .astype(int)
    )
    mp_revenue = tot_revenue - buyback_revenue
    mp_av_price = stats['wa_prices'][1]    
    buyback_av_price = stats['wa_prices'][2]
    
    #Количество
    mp_qty: np.ndarray = (
    (mp_revenue / mp_av_price)
    .round(0)
    .astype(int)
    )
    buyback_qty: np.ndarray = (
    (buyback_revenue / buyback_av_price)
    .round(0)
    .astype(int)
    )
    
    #Комисия
    dic:dict = stats['wb_comm']
    mp_coms = dic.get(1) or 0
    buyback_coms = dic.get(2) or 0  
    
    mp_com_costs: np.ndarray = (
    (mp_revenue * mp_coms / 100)
    .round(0)
    .astype(int)
    )
    buyback_com_costs: np.ndarray = (
    (buyback_revenue * buyback_coms / 100)
    .round(0)
    .astype(int)
    )
    
    #Логистика
    
    dic:dict = stats['logistic']
    mp_logs = dic.get(1) or 0
    buyback_logs = dic.get(2) or 0 
    
    
    
    mp_log_costs: np.ndarray = (
    (mp_qty * mp_logs)
    .round(0)
    .astype(int)
    )
    buyback_log_costs: np.ndarray = (
    (buyback_qty * buyback_logs)
    .round(0)
    .astype(int)
    )
    
    #Хранение
    
    
    dic:dict = stats['storage']
    mp_store = dic.get(1) or 0
    buyback_store = dic.get(2) or 0 
    
    
    
    mp_storage_costs: np.ndarray = (
    (mp_qty * mp_store)
    .round(0)
    .astype(int)
    )
    buyback_storage_costs: np.ndarray = (
    (buyback_qty * buyback_store)
    .round(0)
    .astype(int)
    )
    
    #штрафы
    mp_penalties = stats['penalty'][1]      
    
    mp_penalties_costs: np.ndarray = (
    (mp_qty * mp_penalties)
    .round(0)
    .astype(int)
    )
    
    #cashback_commision
    mp_cashback_commision = stats['cashback_commision'][1]      
    mp_cashback_commision_costs: np.ndarray = (
    (mp_qty * mp_cashback_commision)
    .round(0)
    .astype(int)
    )
    
    mp_loyality = stats['loyality'] 
    mp_loyality_costs: np.ndarray = (
    (mp_cashback_commision_costs * mp_loyality)
    
   
    )
    
    
    #deduction
    weekly_deduction = stats['deduction'][1]
    n = len(date_from)
    mask = (np.arange(1, n + 1) % 7 == 0).astype(int)
    
    mp_deduction_costs = mask * weekly_deduction
    
    # Делаем словарь для df
    d = {
        "date_from":date_from,
        "total_revenue":tot_revenue,
        "mp_revenue":mp_revenue,
        "purchase_revenue":buyback_revenue,        
        "mp_qty":mp_qty,
        "purchase_qty":buyback_qty,
        "mp_comission":mp_com_costs,
        "purchase_comission":buyback_com_costs,
        "mp_logistic":mp_log_costs,
        "purchase_logistic":buyback_log_costs,
        "mp_storage_fee":mp_storage_costs,
        "purchase_storage_fee":buyback_storage_costs,
        "mp_penalties":mp_penalties_costs,
        "mp_cashback_comission":mp_cashback_commision_costs,
        "mp_loyality":mp_loyality_costs,
        "mp_deduction":mp_deduction_costs
    }
    df = pd.DataFrame(d)
    df = df.set_index('date_from')
    cols = df.columns
    df = df / 100
    df['mp_qty'] =  df['mp_qty'] * 100
    df['purchase_qty'] =  df['purchase_qty'] * 100
    df = df.reset_index()
    df['ME'] = pd.to_datetime(df['date_from']) + pd.offsets.MonthEnd(0)
    
    monthes_df = df.pivot_table(
        index='ME',
        values=cols,
        aggfunc='sum'
    ).reset_index()
    
    monthes_df['ME'] = pd.to_datetime(monthes_df['ME'])
    monthes_df['ME'] = monthes_df['ME'].dt.strftime('%b %Y')
    monthes_df = monthes_df[['ME','total_revenue','mp_revenue','purchase_revenue','mp_qty',
                             'purchase_qty','mp_comission','purchase_comission','mp_logistic',
                             'purchase_logistic','mp_storage_fee','purchase_storage_fee',
                             'mp_penalties','mp_deduction','mp_cashback_comission','mp_loyality'
                             ]]
    
    
    
    monthes_df.to_excel('tr.xlsx')
    
    return d
    

def del_version(conn, instance_id):
    with conn.cursor() as cur:
        cur.execute(
            "DELETE FROM budget_gl WHERE version_id = %s",
            (instance_id,)
        )

    conn.commit() 


def insert_results(conn,rows,instance_id):
    
    with conn.cursor() as cur:
        with cur.copy(
            """
            COPY public.budget_gl (
                "date",
                dt,
                cr,
                description,
                chapter,
                acc_id,
                contract_id,
                subconto_id,
                version_id
            )
            FROM STDIN
            """
            
        ) as copy:
            for row in rows:
                copy.write_row(row)

    conn.commit()

def write_forecast(d:dict,instance_id,conn):
    date_from = d['date_from']
    n = len(date_from)
    
    mapping = {
        "mp_revenue":{"st_acc":45,"st_sc":52},
        "purchase_revenue":{"st_acc":45,"st_sc":87},
        
        "mp_comission":{"st_acc":45,"st_sc":77},
        "purchase_comission":{"st_acc":45,"st_sc":96},
        
        "mp_logistic":{"st_acc":45,"st_sc":78},
        "purchase_logistic":{"st_acc":45,"st_sc":97},
        
        "mp_storage_fee":{"st_acc":45,"st_sc":79},
        "purchase_storage_fee":{"st_acc":45,"st_sc":98},
        
        "mp_penalties":{"st_acc":45,"st_sc":82},
        "mp_deduction":{"st_acc":45,"st_sc":81},
        "mp_cashback_comission":{"st_acc":45,"st_sc":84},
        "mp_loyality":{"st_acc":45,"st_sc":85},        
    }
    
    del_version(conn, instance_id)
    
    for item in mapping:
        if item.endswith("revenue"):
           rows = [
               (
                   str(date_from[i]),
                   int(d[item][i]),
                   0,
                   str(item),
                   "Прогноз выручки",
                   int(mapping[item]['st_acc']),
                   109,
                   int(mapping[item]['st_sc']),
                   int(instance_id)
               )
               for i in range(n)
           ] 
        else:
            rows = [
               (
                   str(date_from[i]),
                   0,
                   int(d[item][i]),                
                   str(item),
                   "Прогноз выручки",
                   int(mapping[item]['st_acc']),
                   109,
                   int(mapping[item]['st_sc']),
                   int(instance_id)
               )
               for i in range(n)
           ]
        
        insert_results(conn,rows,instance_id) 
    
 

# Делаем статистику и находим основные параметры для рассчетов
def stats(conn:DuckDBPyConnection,date_from,wb):
    
    pd_date = pd.to_datetime(date_from)
    
    rel = conn.sql(
        """
        SELECT 
        t.date_from,
        t.report_type,        
        CASE WHEN v.vat_rate IS NOT NULL THEN 1 ELSE 0 END as vat_rate,
        t.field,        
        t.value,
        t.dtn_id
        from sales t
        left join product v on v.nm_id = t.nm_id
        """        
    )
    
    stats = {}
    
    #Находим средние цены
    wa_prices = wb['average_unit_price'][0]
    
    if wa_prices['historical']:
       n_month =  wa_prices['n_monthes']
       first_date = (pd_date - pd.DateOffset(months=n_month)).date()
       wa_price = conn.sql(
           """
           SELECT
           x.report_type,
           round(x.amount / x.quant,0)::bigint as wa_price,
           x.quant,
           x.amount
           
           FROM(
           SELECT  
            report_type,         
            sum(value) filter (where field = 'retail_price' and dtn_id = 2) -
            sum(value) filter (where field = 'retail_price' and dtn_id = 1) 
            as amount,
            count(value) filter (where field = 'retail_price' and dtn_id = 2) -
            count(value) filter (where field = 'retail_price' and dtn_id = 1) 
            as quant  
            from rel
            where date_from >= ?
            group by report_type
            ) x
           """,params=[first_date]                    
       )
    #    wa_price.show()
       wa_p = wa_price.fetchall()
       wa_p = {r[0]: r[1] for r in wa_p}
       stats['wa_prices'] = wa_p
       
    else:
       stats['wa_prices'] = {1:wa_prices['Manual'],2:wa_prices['Manual']}
    
    #Находим долю выкупа
    wb_share = wb['buyback_share'][0]
    
    if wb_share['historical']:
        n_month =  wb_share['n_monthes']
        first_date = (pd_date - pd.DateOffset(months=n_month)).date()
        wb_s = conn.execute(
            """
            WITH a AS (
                SELECT
                    sum(value) FILTER (WHERE field = 'retail_price' AND dtn_id = 2) -
                    sum(value) FILTER (WHERE field = 'retail_price' AND dtn_id = 1) AS amount
                FROM rel
                WHERE report_type = 2
                AND date_from >= ?
            )

            SELECT 
                round(a.amount / x.amount * 100, 2) AS wa_share
            FROM (
                SELECT
                    sum(value) FILTER (WHERE field = 'retail_price' AND dtn_id = 2) -
                    sum(value) FILTER (WHERE field = 'retail_price' AND dtn_id = 1) AS amount
                FROM rel
                WHERE date_from >= ?
            ) x, a
            """,
            [first_date, first_date]
        )
        wb_s = wb_s.fetchone()[0]
        stats['wb_share'] = wb_s
    else:
        stats['wb_share'] = wb_share['Manual']
    
    #Считаем долю НДС в расчетах
    discout_vat =  wb['discout_vat_share'][0]
    if discout_vat['historical']:
        n_month =  discout_vat['n_monthes']
        first_date = (pd_date - pd.DateOffset(months=n_month)).date() 
        dvs = conn.sql(
           """
           SELECT
           x.report_type,
           round(x.amount / x.tot_amount * 100,2) as dvs          
           FROM(           
           SELECT  
            report_type,
            sum(value) filter (where field = 'retail_price' and dtn_id = 2) -
            sum(value) filter (where field = 'retail_price' and dtn_id = 1) 
            as amount,
            (SELECT
            sum(value) filter (where field = 'retail_price' and dtn_id = 2) -
            sum(value) filter (where field = 'retail_price' and dtn_id = 1) 
            from rel  
            where date_from >= ?          
            ) as tot_amount          
            from rel
            where date_from >= ? and vat_rate = 1
            group by report_type
            ) x
           
           """, params=[first_date, first_date]
           
        )
        dvsd = dvs.fetchall()
        dvsd = {r[0]: r[1] for r in dvsd}
        stats['dvs'] = dvsd
    else:
        stats['dvs'] = {1:discout_vat['Manual'],2:discout_vat['Manual']}
       
    #Считаем процент комисии для рассчетов
    wb_comm = wb['marketplace_comission'][0]
    if wb_comm['historical']:
        n_month =  wb_comm['n_monthes']
        first_date = (pd_date - pd.DateOffset(months=n_month)).date() 
        wb_c = conn.sql(
            """ 
           SELECT
           x.report_type,
           round((x.amount - x.to_pay) / x.amount*100,2) as comm
           FROM(
           SELECT  
            report_type,         
            sum(value) filter (where field = 'retail_price' and dtn_id = 2) -
            sum(value) filter (where field = 'retail_price' and dtn_id = 1) 
            as amount,
            sum(value) filter (where field = 'ppvz_for_pay' and dtn_id = 2) -
            sum(value) filter (where field = 'ppvz_for_pay' and dtn_id = 1) 
            as to_pay  
            from rel
            where date_from >= ?
            group by report_type
            ) x
            """, params=[first_date]
        )
        wbcomm = wb_c.fetchall()
        wbcomm = {r[0]: r[1] for r in wbcomm}
        stats['wb_comm'] = wbcomm
    else:
        stats['wb_comm'] = {1:wb_comm['Manual'],2:wb_comm['Manual']}
    
    #Добавляем unit costs
    unit_cost = wb['cost_per_unit']
    stats['unit_cost'] = unit_cost
    
    #Добавляем delivery costs
    logictic = wb['delivery_unit_cost'][0]
    if logictic['historical']:
        n_month =  logictic['n_monthes']
        first_date = (pd_date - pd.DateOffset(months=n_month)).date() 
        lgc = conn.sql(
            """ 
           SELECT
           x.report_type,
           round(x.delivery_rub/x.qty,0)::bigint as delivery
           FROM(
           SELECT  
            report_type,         
            sum(value) filter (where field = 'delivery_rub')  as delivery_rub,
            count(value) filter (where field = 'retail_price' and dtn_id = 2) -
            count(value) filter (where field = 'retail_price' and dtn_id = 1) 
            as qty  
            from rel
            where date_from >= ?
            group by report_type
            ) x
            """, params=[first_date]
        )
        logst = lgc.fetchall()
        logst = {r[0]: r[1] for r in logst}
        stats['logistic'] = logst
    else:
        stats['logistic'] = {1:logictic['Manual'],2:logictic['Manual']}
    
    #Добавляем storage fees
    storage = wb['storage_unit_costs'][0]
    if storage['historical']:
        n_month =  storage['n_monthes']
        first_date = (pd_date - pd.DateOffset(months=n_month)).date() 
        # fields = conn.sql("select distinct field from rel")
        # pprint(fields.fetchall())
        storege = conn.sql(
            """ 
           SELECT
           x.report_type,
           round(x.storage_fee/x.qty,0)::bigint as delivery
           FROM(
           SELECT  
            report_type,         
            sum(value) filter (where field = 'storage_fee')  as storage_fee,
            count(value) filter (where field = 'retail_price' and dtn_id = 2) -
            count(value) filter (where field = 'retail_price' and dtn_id = 1) 
            as qty  
            from rel
            where date_from >= ?
            group by report_type
            ) x
            """, params=[first_date]
        )
        logst = storege.fetchall()
        logst = {r[0]: r[1] for r in logst}
        stats['storage'] = logst
    else:
        stats['storage'] = {1:storage['Manual'],2:storage['Manual']}
    
    #Штрафы
    penalty = wb['penalty_unit_costs'][0]
    if penalty['historical']:
        n_month =  penalty['n_monthes']
        first_date = (pd_date - pd.DateOffset(months=n_month)).date() 
        # fields = conn.sql("select distinct field from rel")
        # pprint(fields.fetchall())
        penalty = conn.sql(
            """ 
           SELECT
           x.report_type,
           round(x.storage_fee/x.qty,0)::bigint as delivery
           FROM(
           SELECT  
            report_type,         
            sum(value) filter (where field = 'penalty')  as storage_fee,
            count(value) filter (where field = 'retail_price' and dtn_id = 2) -
            count(value) filter (where field = 'retail_price' and dtn_id = 1) 
            as qty  
            from rel
            where date_from >= ?
            group by report_type
            ) x
            """, params=[first_date]
        )
        
        logst = penalty.fetchall()
        logst = {r[0]: r[1] for r in logst}
        stats['penalty'] = logst
    else:
        stats['penalty'] = {1:penalty['Manual'],2:penalty['Manual']}
    
    #Удержания
    deduction = wb['deduction'][0]
    if deduction['historical']:
        n_month =  deduction['n_monthes']
        first_date = (pd_date - pd.DateOffset(months=n_month)).date() 
        # fields = conn.sql("select distinct field from rel")
        # pprint(fields.fetchall())
        deduct = conn.sql(
            """ 
            SELECT
                x.report_type,
                round(avg(x.deduction), 0)::bigint AS deduction
            FROM (
                SELECT  
                    report_type,
                    date_trunc('week', date_from) AS week,         
                    sum(value) FILTER (WHERE field = 'deduction') AS deduction           
                FROM rel
                WHERE date_from >= ?
                GROUP BY week, report_type
            ) x
            GROUP BY report_type
            """,
            params=[first_date]
        )
        
        logst = deduct.fetchall()
        logst = {r[0]: r[1] for r in logst}
        stats['deduction'] = logst
    else:
        stats['deduction'] = {1:deduction['Manual'],2:deduction['Manual']}
    
    #Cashback commisioning charge
    cashback_commision = wb['cashback_commision'][0]
    if cashback_commision['historical']:
        n_month =  cashback_commision['n_monthes']
        first_date = (pd_date - pd.DateOffset(months=n_month)).date() 
        
        cbc = conn.sql(
           """ 
           SELECT
           x.report_type,
           x.amount / x.qty as comm,
           x.amount,
           x.qty
           FROM(
           SELECT  
            report_type,         
            sum(value) filter (where field = 'cashback_commission_change' and dtn_id = 2) -
            sum(value) filter (where field = 'cashback_commission_change' and dtn_id = 1) 
            as amount,
            count(value) filter (where field = 'retail_price' and dtn_id = 2) -
            count(value) filter (where field = 'retail_price' and dtn_id = 1) 
            as qty  
            from rel
            where date_from >= ?
            group by report_type
            ) x
            """, params=[first_date]
        )
        
        # cbc.show()
        logst = cbc.fetchall()
        logst = {r[0]: r[1] for r in logst}
        stats['cashback_commision'] = logst
    else:
        stats['cashback_commision'] = {1:cashback_commision['Manual'],2:cashback_commision['Manual']}
    
    #Добавляем wb_херн
    loyality = wb['cashback_commision_programm_ratio']
    stats['loyality'] = loyality
    
    return stats

# Берем данные для анализа
def get_forecast_data(conn:DuckDBPyConnection,date_from):
    return conn.execute(
        """
        SELECT
        date_from as ds,
        sum(value) filter (where field = 'retail_price' and dtn_id = 2) -
        sum(value) filter (where field = 'retail_price' and dtn_id = 1) 
        as y  
        from sales
        where date_from < ? 
        group by date_from
        HAVING
            SUM(value) FILTER (WHERE field = 'retail_price' AND dtn_id = 2)
            - SUM(value) FILTER (WHERE field = 'retail_price' AND dtn_id = 1) > 0
        """,
        [date_from],
    ).df()
    
# Строим модель профет
def build_prophet_model(params: dict) -> Prophet:
    model = Prophet(
        yearly_seasonality=params["yearly_seasonality"],
        weekly_seasonality=params["weekly_seasonality"],
        daily_seasonality=params["daily_seasonality"],
        seasonality_mode=params["seasonality_mode"],
        changepoint_prior_scale=params["changepoint_prior_scale"],
        seasonality_prior_scale=params["seasonality_prior_scale"],
        holidays_prior_scale=params["holidays_prior_scale"],
        interval_width=params["interval_width"],
    )

    if params.get("add_monthly_seasonality", False):
        model.add_seasonality(
            name="monthly",
            period=params.get("monthly_period", 30.5),
            fourier_order=params.get("monthly_fourier_order", 5),
        )

    return model

# делаем план по выручке
# def make_forecast(conn, date_from, date_to, prophet_params, freq="D"):
#     end_date = pd.to_datetime(date_from)
#     forecast_date = pd.to_datetime(date_to)
    
#     data = get_forecast_data(conn,date_from)

#     periods = (forecast_date - end_date).days
#     if periods < 0:
#         raise ValueError("forecast_date должен быть позже или равен last_actual_date")

#     model = build_prophet_model(prophet_params)
#     model.fit(data)

#     future = model.make_future_dataframe(periods=periods, freq=freq, include_history=True)
#     forecast = model.predict(future)

#     forecast["yhat"] = forecast["yhat"].clip(lower=0)
#     forecast["yhat_lower"] = forecast["yhat_lower"].clip(lower=0)
#     forecast["yhat_upper"] = forecast["yhat_upper"].clip(lower=0)

#     return model, forecast



def make_forecast(conn, date_from, date_to, prophet_params, freq="D"):
    plan_start = pd.to_datetime(date_from)
    plan_end = pd.to_datetime(date_to)

    data = get_forecast_data(conn, date_from)
    if data.empty:
        raise ValueError("Нет исторических данных для построения прогноза")

    data["ds"] = pd.to_datetime(data["ds"])
    last_actual_date = data["ds"].max()

    periods = (plan_end - last_actual_date).days
    if periods < 0:
        raise ValueError("date_to раньше последней фактической даты")

    model = build_prophet_model(prophet_params)
    model.fit(data)

    future = model.make_future_dataframe(
        periods=periods,
        freq=freq,
        include_history=True
    )
    forecast = model.predict(future)

    forecast["yhat"] = forecast["yhat"].clip(lower=0)
    forecast["yhat_lower"] = forecast["yhat_lower"].clip(lower=0)
    forecast["yhat_upper"] = forecast["yhat_upper"].clip(lower=0)

    return model, forecast

def main(conn, **args):
    ddb_con = None
    psql_con = conn

    try:
        ddb_con = get_duckdb_conn()

        model, forecast = make_forecast(
            ddb_con,
            args["date_from"],
            args["date_to"],
            args["revenue_param"],
        )

        stat = stats(
            ddb_con,
            args["date_from"],
            args["wb_costs_params"],
        )

        d = calculation(forecast, stat, args["date_from"])
        write_forecast(d, args["id"], psql_con)

    finally:
        if ddb_con is not None:
            try:
                ddb_con.execute("DETACH pg")
            except Exception:
                pass
            ddb_con.close()
    

