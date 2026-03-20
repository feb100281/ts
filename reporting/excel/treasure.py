from django.db import connection
import pandas as pd
import warnings


def get_treasury_report(date_to):
    #Банковкие счета
    
    ba_q = """
    SELECT 
    "Банковский счет",
    min(date_from) as "Начальная дата",
    max(date_from) as "Последняя дата",
    ba.currency as "Валюта",
    case when ba.is_active = True then '✅' else '❌' end as "Действующий счет",
    sum("Поступления") as "Поступления",
    sum("Расход") as "Расход",
    sum("Обороты") as "Остаток"
    FROM public.ba_balance_csv t
    join public.corporate_bankaccount as ba on ba.bs_acc_id = t.acc_id
    where date_from <= %s
    group by "Банковский счет", ba.currency, "Действующий счет"
    order by "Остаток" DESC       
    """
    
    #Баланс WB
    
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        df = pd.read_sql(ba_q, params=(date_to,), con=connection)
    
    df = df.set_index("Банковский счет")
    
    
    return df
    

from django.db import connection
import pandas as pd


def get_wb_balance(wb_date=None):
    date_to = wb_date
    if not date_to:
        with connection.cursor() as cur:
            cur.execute("SELECT max(date_from) FROM public.wb_balance_for_csv")
            date_to = cur.fetchone()[0]

    q = """
    SELECT 
        t1.date_from,
        t1."К перечислению продавцу",
        t1."Вывод средств",
        t2."Конечный баланс без ДВП ",
        t2."Деньги в пути (ДВП)",
        t2."Конечный баланс"
    FROM (
        SELECT 
            %(date)s::date as date_from,
            sum("К перечислению продавцу") as "К перечислению продавцу",
            sum("Вывод средств") as "Вывод средств"
        FROM public.wb_balance_for_csv
        WHERE date_from <= %(date)s
    ) t1
    CROSS JOIN (
        SELECT 
            date_from,
            "Конечный баланс без ДВП ",
            "Деньги в пути (ДВП)",
            "Конечный баланс"
        FROM public.wb_balance_for_csv
        WHERE date_from = %(date)s
    ) t2
    """

    with connection.cursor() as cur:
        cur.execute(q, {"date": date_to})
        rows = cur.fetchall()
        columns = [col[0] for col in cur.description]
        
    df = pd.DataFrame(rows, columns=columns)
    df = df.set_index('date_from')

    return df
    

    
    