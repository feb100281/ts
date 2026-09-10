# тестим договора с расчетом арендной платы condition 31 и 32

import os
import importlib
import psycopg
from psycopg.rows import dict_row
import pandas as pd
import numpy as np
from pprint import pprint


# Подключаемся к базе данных 
def connect_db():
    return psycopg.connect(
        dbname="ts_db",  # DB_NAME
        user="ts_user",  # DB_USER
        password="Dec8108079",  # DB_PASSWORD
        host="127.0.0.1",  # DB_HOST
        port="5433",  # DB_PORT
        connect_timeout=10,
    )

# Загружаем строку для теста
def load_row_for_test(conn,condition_id):
    sql = f"""
        SELECT *
        FROM gl.accurals_args
        WHERE fn_id IS NOT NULL
        AND condition_id = {condition_id}
    """
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(sql)
        return cur.fetchall()


def insert_accrual_distribution(conn, final: dict):
    cols = [
        "p_fn_id",
        "pid",
        "date_from",
        "contract_id",
        "condition_id",
        "company_id",
        "acc_st",
        "dt_st",
        "cr_st",
        "vat_rate",
        "acc_vat",
        "dt_vat",
        "cr_vat",
        "acc_pl",
        "subconto_pl",
        "dt_pl",
        "cr_pl",
        "acc_bs",
        "subconto_bs",
        "dt_bs",
        "cr_bs",
        "description_st",
        "description_pl",
        "description_bs",
        "vat_mode",
    ]

    n = len(final["date_from"])

    with conn.cursor() as cur:
        with cur.copy("""
            COPY gl.accural_distribution (
                p_fn_id, pid, date_from, contract_id, condition_id,
                company_id, acc_st, dt_st, cr_st, vat_rate, acc_vat,
                dt_vat, cr_vat, acc_pl, subconto_pl, dt_pl, cr_pl,
                acc_bs, subconto_bs, dt_bs, cr_bs,
                description_st, description_pl, description_bs, vat_mode
            )
            FROM STDIN
        """) as copy:

            for i in range(n):
                row = [
                    final[col][i].item() if hasattr(final[col][i], "item") else final[col][i]
                    for col in cols
                ]

                copy.write_row(row)

    conn.commit()


# Функция для расчетов
def rent_premises(conn,**args):
    
    # Получаем параметры для расчеты
    param = args.get('params_json',None)
    
    # Получаем счет для начислений
    acc_st_id = args.get('acc_st_id',None)
    
    #Получаем даты начала и конца арены
    date_start = args.get('date_start',None)
    date_finish = args.get('date_finish',None)    
       
    # Что бы не падало не выполняем функцию если нет условий и счета
    if not param or not acc_st_id or not date_start or not date_finish:
       return "Не указаны ключевые параметры param, acc_st_id, date_start, date_finish"
    
    # ----------------------------------------------
    # Считаем векторно 1 быстреее в тыс раз 2 тип данных строго привязан. Нет косяков с Pandas
    # ----------------------------------------------
    
    # Делаем timeline договора помесячно через pandas selires
    start_interval = pd.to_datetime(date_start).normalize()
    end_interval = pd.to_datetime(date_finish).normalize()

    month_starts = pd.date_range(
        start=start_interval.to_period("M").to_timestamp(),
        end=end_interval.to_period("M").to_timestamp(),
        freq="MS",
    ) # это начало месяца
    
    # Сразу делаем numpy массивы что бы небыло кошмара с PANDAs
    ms = month_starts.to_numpy() # массив Numpy вместо df['start']
    me = (month_starts + pd.offsets.MonthEnd(0)).to_numpy() # конец месяца
    
    # меняем дату начала и конца в масивах что бы посчитать дни первого и последнено месяца
    ms[0] = np.datetime64(start_interval)
    me[-1] = np.datetime64(end_interval)
    
    # Считаем кол-во дней в месяце и количество дней для начислений
    days_in_month = month_starts.days_in_month.to_numpy()
    days = (me - ms).astype("timedelta64[D]").astype(int) + 1
    
    # Считаем размер массива
    n = len(me)
    
    # Все теперь у нас создан каркасс и мы можем заполнять массивы np.full и считать все как в pandas только легче и быстрее
    
    # Добавляем НДС
    # делаем серию ставок по датам начала
    vat_series = pd.Series(args['vat_json'])
    vat_series.index = pd.to_datetime(vat_series.index)
    vat_series = vat_series.sort_index()

    # мапим и теперь у нас есть ставки НДС
    vat_rate = vat_series.reindex(ms, method='ffill').values
    
    # теперь определяем сверху снизу итд то есть находим сумму с НДС и без
    vat_mode = args.get('vat_mode',None)   
    base_bap = np.full(n,param['БАП']['Ставка'],dtype=float)
    base_ep = np.full(n,param['ЭП']['Ставка'],dtype=float)

    #Находим ставки с НДС и без
    if vat_mode == 'included':
       bap_vat =  base_bap
       bap_clean = base_bap / (100+vat_rate) * 100
       ep_vat =  base_ep
       ep_clean = base_ep / (100+vat_rate) * 100
       acc_vat = np.full(n,84)
    elif vat_mode == 'excluded':
       bap_vat =  base_bap * (100+vat_rate) / 100
       bap_clean = base_bap
       ep_vat =  base_ep * (100+vat_rate) / 100
       ep_clean = base_ep
       acc_vat = np.full(n,84)
    else:
       bap_vat =  base_bap
       bap_clean = base_bap
       ep_vat = base_ep
       ep_clean = base_ep
       acc_vat = np.full(n,None)
    
    # Теперь расчитываем индексации
    bap_index_rate = 0 if not param['БАП']['Индексация'] else param['БАП']['Процент индексации']
    ep_index_rate = 0 if not param['БАП']['Индексация'] else param['БАП']['Процент индексации']
    
    bap_index_start = np.datetime64(date_start) if not param['БАП']['Индексация'] else np.datetime64(param['БАП']['Начало индексации'])
    ep_index_start = np.datetime64(date_start) if not param['ЭП']['Индексация'] else np.datetime64(param['БАП']['Начало индексации'])
    
    bap_index_period = 0 if not param['БАП']['Индексация'] else param['БАП']['Период индексации']
    ep_index_period = 0 if not param['ЭП']['Индексация'] else param['БАП']['Период индексации']
    
    # Делаем пустые массивы
    bap_index_periods = np.zeros(n)
    ep_index_periods = np.zeros(n)
    
    # Находим с какого элемента начисляем индексацию
    bap_n = np.where(ms == bap_index_start)[0][0]
    ep_n = np.where(ms == ep_index_start)[0][0]
    
    # Находим с массив периодов
    if bap_index_period > 0:
        bap_index_periods[bap_n:] = np.arange(n - bap_n) // bap_index_period
    
    if ep_index_period > 0:
        ep_index_periods[ep_n:] = np.arange(n - ep_n) // ep_index_period
        
    
    # теперь считаем БАП и ЭП с учетом индексации самое сложное позади   
    bap_vat = bap_vat * (1+bap_index_rate/100)**bap_index_periods
    ep_vat = ep_vat * (1+ep_index_rate/100)**ep_index_periods
    bap_clean = bap_clean * (1+bap_index_rate/100)**bap_index_periods
    ep_clean = ep_clean * (1+bap_index_rate/100)**bap_index_periods
    
    # Теперь считаем accurals
    area = np.full(n, param['Площадь']['Расчетная'])
    
    
    dt_st = np.zeros(n) #Просто пустой массив для DT
    cr_st = (bap_vat*area / 12 / days_in_month * days) + (ep_vat*area / 12 / days_in_month * days)
    cr_st = cr_st * 100
    
    
    dt_pl = (bap_clean*area / 12 / days_in_month * days) + (ep_clean*area / 12 / days_in_month * days)
    cr_pl = np.zeros(n)
    dt_pl = dt_pl * 100
    
    dt_bs = (bap_clean*area / 12 / days_in_month * days) + (ep_clean*area / 12 / days_in_month * days)
    cr_bs = np.zeros(n)
    dt_bs = dt_bs * 100
    
    
    dt_vat = cr_st - dt_pl
    cr_vat = np.zeros(n)
    
    description_st = np.array([
    f"""Начисления: c {pd.Timestamp(ms).strftime("%d.%m.%Y")} по {pd.Timestamp(me).strftime("%d.%m.%Y")}
    на сумму {cr_st / 100:,.2f} рублей. НДС({vat_rate}%).
    Расчет: ({bap_vat} / 12 мес * {area} м2 + {ep_vat} / 12 мес * {area} м2) / {dim} дней * {d} дней"""
        for ms, me, cr_st, vat_rate, bap_vat, area, ep_vat, dim, d in zip(
            ms, me, cr_st, vat_rate, bap_vat, area, ep_vat, days_in_month, days
        )
    ], dtype=object)
    
    description_pl = np.array([
        f"""Списание на PL: c {pd.Timestamp(ms_i).strftime("%d.%m.%Y")} по {pd.Timestamp(me_i).strftime("%d.%m.%Y")}
    на сумму {dt_pl_i / 100:,.2f} рублей.
    Расчет: ({bap_clean_i} / 12 мес * {area_i} м2 + {ep_clean_i} / 12 мес * {area_i} м2) / {dim_i} дней * {d_i} дней"""
        for ms_i, me_i, dt_pl_i, bap_clean_i, area_i, ep_clean_i, dim_i, d_i in zip(
            ms,
            me,
            dt_pl,
            np.full(n, bap_clean),
            np.full(n, area),
            np.full(n, ep_clean),
            days_in_month,
            days,
        )
    ], dtype=object)
    
    description_bs = np.array([
        f"""Списание на PL: c {pd.Timestamp(ms_i).strftime("%d.%m.%Y")} по {pd.Timestamp(me_i).strftime("%d.%m.%Y")}
    на сумму {dt_bs_i / 100:,.2f} рублей.
    Расчет: ({bap_clean_i} / 12 мес * {area_i} м2 + {ep_clean_i} / 12 мес * {area_i} м2) / {dim_i} дней * {d_i} дней"""
        for ms_i, me_i, dt_bs_i, bap_clean_i, area_i, ep_clean_i, dim_i, d_i in zip(
            ms,
            me,
            dt_bs,
            np.full(n, bap_clean),
            np.full(n, area),
            np.full(n, ep_clean),
            days_in_month,
            days,
        )
    ], dtype=object)
    
    
    
        
     
    final = {
        "p_fn_id":np.full(n,args['fn_id'],dtype=int),
        "pid":np.full(n, None,dtype=object),
        "date_from":me,
        "contract_id":np.full(n,args['contract_id'],dtype=int),
        "condition_id":np.full(n,args['condition_id'],dtype=int),
        "company_id":np.full(n, 1,dtype=int),
        "acc_st":np.full(n,args['acc_st_id'],dtype=int),
        "dt_st":dt_st.round(0),
        "cr_st":cr_st.round(0),
        "vat_rate":vat_rate,
        "acc_vat":acc_vat,
        "dt_vat":dt_vat.round(0),
        "cr_vat":cr_vat.round(0),
        "acc_pl":np.full(n,args['acc_pl_id']),
        "subconto_pl":np.full(n,args['subconto_pl_id']),
        "dt_pl":dt_pl.round(0),
        "cr_pl":cr_pl.round(0),
        "acc_bs":np.full(n,args['acc_bs_id']),
        "subconto_bs":np.full(n,args['subconto_bs_id']),
        "dt_bs":dt_bs.round(0),
        "cr_bs":cr_bs.round(0),
        "description_st":description_st,
        "description_pl":description_pl,
        "description_bs":description_bs,
        "vat_mode":np.full(n,args['vat_mode']),        
    }
    
    insert_accrual_distribution(conn,final)
    
    return "OK"
    
    
    


def main():
    conn = connect_db()
    
    rows = load_row_for_test(conn,31)
    
    #pprint(rows)
    df = rent_premises(conn,**rows[0])
    df.to_excel('rp.xlsx')

        
    conn.close()

if __name__ == "__main__":
    main()