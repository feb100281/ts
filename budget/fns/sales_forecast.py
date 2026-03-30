#Это функции для расчета выручки

from prophet import Prophet
import pandas as pd
# from conns import get_duckdb_conn
from duckdb import DuckDBPyConnection
import duckdb
from pprint import pprint
import datetime
from reporter_builder import Section, P, T

# Делаем экземпляры классов разделов отчета о планировании

revenue_settings = Section(1,"Исходные данные для планирование доходной части")

def intro_text(date_from, date_to, revenue_params, wb_params):
    
    intro = (
        "Для планирования доходной части бюджета были использованы следуюшие "
        "исходные данные:"
    )
    
dfs = []


test = {'budget_type': 'baseline',
 'date_from': datetime.date(2026, 3, 20),
 'date_to': datetime.date(2027, 3, 28),
 'description': 'ффф',
 'id': 3,
 'number': '33',
 'revenue_param': {'add_monthly_seasonality': True,
                   'changepoint_prior_scale': 0.08,
                   'daily_seasonality': False,
                   'holidays_prior_scale': 10.0,
                   'interval_width': 0.8,
                   'monthly_fourier_order': 5,
                   'monthly_period': 30.5,
                   'seasonality_mode': 'multiplicative',
                   'seasonality_prior_scale': 10.0,
                   'weekly_seasonality': True,
                   'yearly_seasonality': True},
 'wb_costs_params': {'average_unit_price': [{'Manual': 0.0,
                                             'historical': True,
                                             'n_monthes': 6}],
                     'buyback_share': [{'Manual': 0.0,
                                        'historical': True,
                                        'n_monthes': 6}],
                     'cost_per_unit': 0.0,
                     'delivery_unit_cost': [{'Manual': 0.0,
                                             'historical': True,
                                             'n_monthes': 6}],
                     'discout_vat_share': [{'Manual': 0.0,
                                            'historical': True,
                                            'n_monthes': 6}],
                     'marketplace_comission': [{'Manual': 0.0,
                                                'historical': True,
                                                'n_monthes': 6}],
                     'storage_unit_costs': [{'Manual': 0.0,
                                             'historical': True,
                                             'n_monthes': 6}],
                    "penalty_unit_costs": [{"historical": True, 
                                            "n_monthes": 6, "Manual": 0.0}],  
 },
 }




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
           round(x.amount / x.quant,0)::bigint as wa_price
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
            where date_from < ?
            group by report_type
            ) x
           """,params=[first_date]                    
       )
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
                AND date_from < ?
            )

            SELECT 
                round(a.amount / x.amount * 100, 2) AS wa_share
            FROM (
                SELECT
                    sum(value) FILTER (WHERE field = 'retail_price' AND dtn_id = 2) -
                    sum(value) FILTER (WHERE field = 'retail_price' AND dtn_id = 1) AS amount
                FROM rel
                WHERE date_from < ?
            ) x, a
            """,
            [first_date, first_date]
        )
        wb_s = wb_s.fetchone()[0]
        stats['wb_share'] = wb_s
    else:
        stats['buyback_share'] = wb_share['Manual']
    
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
            where date_from < ?          
            ) as tot_amount          
            from rel
            where date_from < ? and vat_rate = 1
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
            where date_from < ?
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
            where date_from < ?
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
            where date_from < ?
            group by report_type
            ) x
            """, params=[first_date]
        )
        logst = storege.fetchall()
        logst = {r[0]: r[1] for r in logst}
        stats['storage'] = logst
    else:
        stats['storege'] = {1:storage['Manual'],2:storage['Manual']}
    
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
            where date_from < ?
            group by report_type
            ) x
            """, params=[first_date]
        )
        
        logst = penalty.fetchall()
        logst = {r[0]: r[1] for r in logst}
        stats['penalty'] = logst
    else:
        stats['penalty'] = {1:penalty['Manual'],2:penalty['Manual']}
    
    
    
    
    
    pprint(stats) 
     
       
       
       
    
    


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
def make_forecast(conn, date_from, date_to, prophet_params, freq="D"):
    end_date = pd.to_datetime(date_from)
    forecast_date = pd.to_datetime(date_to)
    
    data = get_forecast_data(conn,date_from)

    periods = (forecast_date - end_date).days
    if periods < 0:
        raise ValueError("forecast_date должен быть позже или равен last_actual_date")

    model = build_prophet_model(prophet_params)
    model.fit(data)

    future = model.make_future_dataframe(periods=periods, freq=freq, include_history=True)
    forecast = model.predict(future)

    forecast["yhat"] = forecast["yhat"].clip(lower=0)
    forecast["yhat_lower"] = forecast["yhat_lower"].clip(lower=0)
    forecast["yhat_upper"] = forecast["yhat_upper"].clip(lower=0)

    return model, forecast

def main(**args):
    ddb_con = duckdb.connect('/Users/pavelustenko/ts/data/analytics.duckdb')
    pprint(args)
    # model, forecast = make_forecast(
    #     ddb_con,
    #     args['date_from'],
    #     args['date_to'],
    #     args['revenue_param'],    
    # )
    stats(
        ddb_con,
        args['date_from'],
        args['wb_costs_params']        
    )
    
    
main(**test)

