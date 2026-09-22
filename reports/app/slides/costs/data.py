from conns import get_duckdb_conn_with_pg
import pandas as pd
from utils.wb_fields import WB_FIELDS

def get_summary(start, end):
    with get_duckdb_conn_with_pg() as con:
        df = con.execute(
            """ 
            SELECT
            x.field,
            round(x.amount/100.0,2) as amount
            from(
            select 
            field,
            COALESCE(sum(val) filter (where oper='dt'),0) as dt,
            COALESCE(sum(val) filter (where oper='cr'),0) as cr,
            COALESCE(sum(val / (100+vat_rate) *100) filter (where oper='dt'),0) -
            COALESCE(sum(val / (100+vat_rate) *100) filter (where oper='cr'),0) as amount
            from sales.sales_long
            where field not in (
                'comission',
                'ppvz_for_pay',
                'retail_amount',
                'retail_price'
            )
            and date_from BETWEEN ? and ?
            group by field) x;
            """,
            parameters=[start,end]
        ).df()
        
    return df


def get_deduction_card(start, end):
    with get_duckdb_conn_with_pg() as con:
        df = con.execute(
            """ 
            SELECT
                btn,
                ROUND(amount/100.0, 2) as amount
            FROM (
                SELECT
                    COALESCE(SUM(val / (100+vat_rate) *100) FILTER (WHERE oper = 'dt'), 0) - 
                    COALESCE(SUM(val / (100+vat_rate) *100) FILTER (WHERE oper = 'cr'), 0) AS amount,
                    CASE 
                        WHEN btn LIKE '%Списание за отзыв%' THEN 'Отзывы'
                        WHEN btn LIKE '%Оказание услуг%' THEN 'Подписка'
                        ELSE 'Прочие'
                    END AS btn
                FROM sales.sales_long
                WHERE field = 'deduction'
                    AND date_from BETWEEN ? AND ?
                GROUP BY 
                    CASE 
                        WHEN btn LIKE '%Списание за отзыв%' THEN 'Отзывы'
                        WHEN btn LIKE '%Оказание услуг%' THEN 'Подписка'
                        ELSE 'Прочие'
                    END
            )
            """,
            parameters=[start, end]
        ).df()
    
    # Всегда добавляем 3 строки
    all_categories = pd.DataFrame({
        'btn': ['Отзывы', 'Подписка', 'Прочие'],
        'amount': [0, 0, 0]
    })
    
    # Объединяем, суммируем и сортируем по amount
    result = pd.concat([all_categories, df]).groupby('btn', as_index=False)['amount'].sum()
    result = result.sort_values('amount', ascending= True)
    
    return result




def get_logictic_card(start, end):
    with get_duckdb_conn_with_pg() as con:
        df = con.execute(
           """
           SELECT 
                field as btn,
                ROUND(SUM(CASE WHEN oper = 'dt' THEN val / (100+vat_rate) *100 ELSE 0 END) - 
                        SUM(CASE WHEN oper = 'cr' THEN val / (100+vat_rate) *100 ELSE 0 END), 2) / 100.0 AS amount
            FROM sales.sales_long
            WHERE field in ('delivery_rub','storage_fee','acceptance')
                        AND date_from BETWEEN ? AND ?
                    GROUP BY 
                        field
                        order by amount;
           """, 
           parameters=[start, end]
        ).df()
    
    df = df.set_index('btn')
    df = df.rename(index=WB_FIELDS)
    df =df.reset_index()
    # Всегда добавляем 3 строки
    all_categories = pd.DataFrame({
        'btn': ['Приемка', 'Хранение', 'Логистика'],
        'amount': [0, 0, 0]
    })
    
    # Объединяем и суммируем
    result = pd.concat([all_categories, df]).groupby('btn', as_index=False)['amount'].sum()
    result = result.sort_values('amount', ascending=True) 
    
    
    return result




def get_penalty_card(start, end):
    with get_duckdb_conn_with_pg() as con:
        df = con.execute(
            """
            SELECT
                btn,
                ROUND(amount/100.0, 2) as amount
            FROM (
                SELECT
                    COALESCE(SUM(val / (100+vat_rate) *100) FILTER (WHERE oper = 'dt'), 0) - 
                    COALESCE(SUM(val / (100+vat_rate) *100) FILTER (WHERE oper = 'cr'), 0) AS amount,
                    CASE 
                        WHEN btn LIKE '%Выявленные расхождения%' OR btn LIKE '%Подмена товара%' THEN 'Карточки'
                        WHEN btn LIKE '%Штраф за недовоз%' OR btn LIKE '%Разворот поставки%' 
                             OR btn LIKE '%Платное хранение%' OR btn LIKE '%габаритов%' THEN 'Поставка/габариты'
                        ELSE 'Прочее'
                    END AS btn
                FROM sales.sales_long
                WHERE field = 'penalty'
                    AND date_from BETWEEN ? AND ?
                GROUP BY 
                    CASE 
                        WHEN btn LIKE '%Выявленные расхождения%' OR btn LIKE '%Подмена товара%' THEN 'Карточки'
                        WHEN btn LIKE '%Штраф за недовоз%' OR btn LIKE '%Разворот поставки%' 
                             OR btn LIKE '%Платное хранение%' OR btn LIKE '%габаритов%' THEN 'Поставка/габариты'
                        ELSE 'Прочее'
                    END
            )
            """,
            parameters=[start, end]
        ).df()
    
    # Всегда добавляем 3 строки
    all_categories = pd.DataFrame({
        'btn': ['Карточки', 'Поставка/габариты', 'Прочее'],
        'amount': [0, 0, 0]
    })
    
    # Объединяем, суммируем и сортируем по amount (по возрастанию)
    result = pd.concat([all_categories, df]).groupby('btn', as_index=False)['amount'].sum()
    result = result.sort_values('amount', ascending=True)
    
    return result


def get_other_card(start, end):
    with get_duckdb_conn_with_pg() as con:
        df = con.execute(
            """ 
            SELECT
                'Участие в ПЛ' as btn,
                ROUND(SUM(CASE WHEN oper = 'dt' THEN val / (100+vat_rate) *100 ELSE 0 END) - 
                      SUM(CASE WHEN oper = 'cr' THEN val / (100+vat_rate) *100 ELSE 0 END), 2) / 100.0 AS amount
            FROM sales.sales_long
            WHERE field IN ('cashback_commission_change','cashback_amount')
                AND date_from BETWEEN ? AND ?
            
            UNION ALL 
            
            SELECT 
                field as btn,
                ROUND(SUM(CASE WHEN oper = 'dt' THEN val / (100+vat_rate) *100 ELSE 0 END) - 
                      SUM(CASE WHEN oper = 'cr' THEN val / (100+vat_rate) *100 ELSE 0 END), 2) / 100.0 AS amount
            FROM sales.sales_long
            WHERE field IN ('additional_payment','payment_schedule')
                AND date_from BETWEEN ? AND ?
            GROUP BY field
            ORDER BY amount
            """,
            parameters=[start, end, start, end]  # ← 4 параметра
        ).df()
    
    # Переименование индексов (если нужно)
    if 'WB_FIELDS' in globals():
        df = df.set_index('btn')
        df = df.rename(index=WB_FIELDS)
        df = df.reset_index()
    
    # Всегда добавляем 3 строки
    all_categories = pd.DataFrame({
        'btn': ['Участие в ПЛ', 'Корректировки', 'Изменение СП'],
        'amount': [0, 0, 0]
    })
    
    # Объединяем и суммируем
    result = pd.concat([all_categories, df]).groupby('btn', as_index=False)['amount'].sum()
    result = result.sort_values('amount', ascending=True)
    
    return result