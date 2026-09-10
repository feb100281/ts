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

def annual_fixed(conn,**args):
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
    
    fix_amount = np.full(n,param['Сумма'])
       
    if vat_mode == 'included':
       amount_vat =  fix_amount
       amount_clean = fix_amount / (100+vat_rate) * 100 
       acc_vat = np.full(n,84)
    
    elif vat_mode == 'excluded':
       amount_vat =  fix_amount * (100+vat_rate) / 100
       amount_clean = fix_amount
       acc_vat = np.full(n,84)
    
    else:
       amount_vat =  fix_amount 
       amount_clean = fix_amount 
       acc_vat = np.full(n,None)
    
    total_days = days.sum()
    
    dt_st = np.zeros(n) #Просто пустой массив для DT
    cr_st = amount_vat / total_days * days
    cr_st = cr_st * 100
    
    
    dt_pl = amount_clean / total_days * days
    cr_pl = np.zeros(n)
    dt_pl = dt_pl * 100
    
    dt_bs = amount_clean / total_days * days
    cr_bs = np.zeros(n)
    dt_bs = dt_bs * 100
    
    
    dt_vat = cr_st - dt_pl
    cr_vat = np.zeros(n)
    
    
    description_st = np.array([
    f"""Начисления: c {pd.Timestamp(ms).strftime("%d.%m.%Y")} по {pd.Timestamp(me).strftime("%d.%m.%Y")}
    на сумму {cr_st / 100:,.2f} рублей. НДС({vat_rate}%).
    Расчет: ({param['Сумма']:,.2f} / {total_days} дней за год * {d} дней"""
        for ms, me, cr_st, vat_rate, d in zip(
            ms, me, cr_st, vat_rate, days
        )
    ], dtype=object)
    
    description_pl = np.array([
    f"""Списание: c {pd.Timestamp(ms).strftime("%d.%m.%Y")} по {pd.Timestamp(me).strftime("%d.%m.%Y")}
    на сумму {dt_pl / 100:,.2f} рублей. Минус НДС({vat_rate}%).
    Расчет: ({param['Сумма']:,.2f} минус НДС({vat_rate}% / {total_days} дней за год * {d} дней"""
        for ms, me, dt_pl, vat_rate, d in zip(
            ms, me, dt_pl, vat_rate, days
        )
    ], dtype=object)
    
    description_bs = np.array([
    f"""Списание: c {pd.Timestamp(ms).strftime("%d.%m.%Y")} по {pd.Timestamp(me).strftime("%d.%m.%Y")}
    на сумму {dt_bs / 100:,.2f} рублей. Минус НДС({vat_rate}%).
    Расчет: ({param['Сумма']:,.2f} минус НДС({vat_rate}% / {total_days} дней за год * {d} дней"""
        for ms, me, dt_bs, vat_rate, d in zip(
            ms, me, dt_pl, vat_rate, days
        )
    ], dtype=object)
    
    
    
    
    dt_st = dt_st.round(0).astype(np.int64)
    cr_st = cr_st.round(0).astype(np.int64)
    dt_vat = dt_vat.round(0).astype(np.int64)
    cr_vat = cr_vat.round(0).astype(np.int64)
    dt_pl = dt_pl.round(0).astype(np.int64)
    cr_pl = cr_pl.round(0).astype(np.int64)
    dt_bs = dt_bs.round(0).astype(np.int64)
    cr_bs = cr_bs.round(0).astype(np.int64)
    
    
    
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
    
    return pd.DataFrame(final)

def main():
    conn = connect_db()
    
    rows = load_row_for_test(conn,33)
    
    pprint(rows)
    
    df = annual_fixed(conn,**rows[0])
    df.to_excel('rp.xlsx')

        
    conn.close()

if __name__ == "__main__":
    main()