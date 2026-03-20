#!/usr/bin/env python3

# Функция рассчета депозита по кэшу

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

def cashbased_deposits(conn,**args):
    param = args.get('params_json',None)
    
    # Получаем счет для начислений
    acc_bs_id = args.get('acc_bs_id',None)
    subconto_bs_id = args.get('subconto_bs_id',None)
    
    acc_pl_id = args.get('acc_bs_id',None)
    acc_pl_id = args.get('subconto_pl_id',None)
    
    contract_id = args.get('contract_id',None)
    
    q_filter = param.get('Субконто процентов',None)
   
    # Что бы не падало не выполняем функцию если нет условий и счета
    if not param or not q_filter:
       return "Не указаны ключевые параметры param, Субконто процентов"
   
    

def main():
    conn = connect_db()
    
    rows = load_row_for_test(conn,50)
    
    pprint(rows)
    
    # df = annual_fixed(conn,**rows[0])
    # df.to_excel('rp.xlsx')

        
    conn.close()

if __name__ == "__main__":
    main()

