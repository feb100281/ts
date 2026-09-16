from conns import get_duckdb_conn_with_opt
from datetime import date

def get_tree_data(
    subject_id=None,
    brand=None,
    start=date(2023,1,1),
    end=date.today(),
):
    with get_duckdb_conn_with_opt(ro=True) as con:
        df = con.execute(
            """
            with sales as (
                SELECT
                    nm_id,
                    COALESCE(sum(val) filter (where oper='dt'),0) -
                    COALESCE(sum(val) filter (where oper='cr'),0) as net_sales,
                    count(val) filter (where oper='dt') -
                    count(val) filter (where oper='cr') as net_qty,
                    max(date_from) as date_from
                FROM sales.sales_long
                WHERE field = 'retail_price'
                GROUP BY nm_id
            ),
            rel as (
                select 
                    i.card_id,
                    i.sa_name,
                    u.usk,
                    u.usk_sa_name,
                    CASE when u.usk is null then 'Нет ключа' else CONCAT('(',u.usk_sa_name,') ',p.title) end as pid,
                    i.title,
                    i.subject_name,
                    i.subject_id,
                    UPPER(i.brand) as brand,
                    CONCAT('(',i.sa_name,') ',i.title) as item,
                    CASE 
                        when p.gender = 'Женский' then '🙋‍♀️'
                        when p.gender = 'Мужской' then '🙋🏻‍♂️'
                        when p.gender = 'Девочки' then '🧍🏻‍♀️'
                        when p.gender = 'Мальчики' then '🧍🏻‍♂️'
                        when p.gender = 'Детский' then '🍼'
                        else '🦄'
                    end as gender,
                    COALESCE(s.net_sales,0) as net_sales,
                    COALESCE(s.net_qty,0) as net_qty,
                    s.date_from
                from inventories.wb_product i
                left join inventories.usk u on i.sa_name = u.sa_name
                left join sales s on s.nm_id = i.card_id
                left join inventories.wb_product p on p.card_id = i.card_id
                WHERE (i.subject_id = ? OR ? IS NULL)
                  AND (UPPER(i.brand) = UPPER(?) OR ? IS NULL)
                  AND (s.date_from BETWEEN ? AND ? OR s.date_from IS NULL)
            )
            select
                CONCAT(1,'_',lv1::text) as lv1_id,
                CONCAT(lv1,' (',items_by_lv1,') 🤑 ₽',
                    CASE 
                        when revenue_by_lv1 / 100 > 1_000_000 then PRINTF('%,d',ROUND(revenue_by_lv1/100/1_000_000,0)::bigint)||'M'
                        ELSE PRINTF('%.d',ROUND(revenue_by_lv1/100/1_000,0)::bigint)||'K'
                    end,
                    ' 📦',
                    CASE 
                        when qty_by_lv1  > 1_000 then PRINTF('%,d',ROUND(qty_by_lv1/1_000,0)::bigint)||'K'
                        ELSE PRINTF('%.d',ROUND(qty_by_lv1,0)::bigint)
                    end
                ) as lv1_label,
                CONCAT(2,'_',subject_id::text,'_',lv1) as lv2_id,
                CONCAT(lv2,' (',items_by_lv2,') 🤑 ₽',
                    CASE 
                        when revenue_by_lv2 / 100 > 1_000_000 then PRINTF('%,d',ROUND(revenue_by_lv2/100/1_000_000,0)::bigint)||'M'
                        ELSE PRINTF('%.d',ROUND(revenue_by_lv2/100/1_000,0)::bigint)||'K'
                    end,
                    ' 📦',
                    CASE 
                        when qty_by_lv2  > 1_000 then PRINTF('%,d',ROUND(qty_by_lv2/1_000,0)::bigint)||'K'
                        ELSE PRINTF('%.d',ROUND(qty_by_lv2,0)::bigint)
                    end
                ) as lv2_label,
                CONCAT(3,'_',COALESCE(usk::text,'0')) as lv3_id,
                CONCAT(lv3,' (',items_by_lv3,') 🤑 ₽',
                    CASE 
                        when revenue_by_lv3 / 100 > 1_000_000 then PRINTF('%,.2f',ROUND(revenue_by_lv3/100/1_000_000,2)::double)||'M'
                        ELSE PRINTF('%,.2f',ROUND(revenue_by_lv3/100/1_000,2)::double)||'K'
                    end,
                    ' 📦',
                    CASE 
                        when qty_by_lv3  > 1_000 then PRINTF('%,.2f',ROUND(qty_by_lv3/1_000,1)::double)||'K'
                        ELSE PRINTF('%,d',ROUND(qty_by_lv3,0)::bigint)
                    end
                ) as lv3_label,
                CONCAT(4,'_',card_id::text) as lv4_id,
                CONCAT(item,' ',gender,' 🤑 ₽',
                    CASE 
                        when revenue_by_items / 100 > 1_000_000 then PRINTF('%,.2f',ROUND(revenue_by_items/100/1_000_000,2)::double)||'M'
                        ELSE PRINTF('%,.2f',ROUND(revenue_by_items/100/1_000,2)::double)||'K'
                    end,
                    ' 📦',
                    CASE 
                        when qty_by_items  > 1_000 then PRINTF('%,.2f',ROUND(qty_by_items/1_000,1)::double)||'K'
                        ELSE PRINTF('%,d',ROUND(qty_by_items,0)::bigint)
                    end
                ) as item_label
            from (
                select 
                    brand as lv1,
                    subject_name as lv2,
                    pid as lv3,
                    usk,
                    subject_id,
                    card_id,
                    item,
                    gender,
                    COUNT(item) OVER (PARTITION BY brand) AS items_by_lv1,
                    sum(net_sales) OVER (PARTITION BY brand) AS revenue_by_lv1,
                    sum(net_qty) OVER (PARTITION BY brand) AS qty_by_lv1,
                    COUNT(item) OVER (PARTITION BY brand,subject_name) AS items_by_lv2,
                    sum(net_sales) OVER (PARTITION BY brand,subject_name) AS revenue_by_lv2,
                    sum(net_qty) OVER (PARTITION BY brand,subject_name) AS qty_by_lv2,
                    COUNT(item) OVER (PARTITION BY brand,subject_name,pid) AS items_by_lv3,
                    sum(net_sales) OVER (PARTITION BY brand,subject_name,pid) AS revenue_by_lv3,
                    sum(net_qty) OVER (PARTITION BY brand,subject_name,pid) AS qty_by_lv3,
                    sum(net_sales) OVER (PARTITION BY brand,subject_name,pid,item) AS revenue_by_items,
                    sum(net_qty) OVER (PARTITION BY brand,subject_name,pid,item) AS qty_by_items
                from rel
            )
            ORDER BY revenue_by_lv1 DESC, revenue_by_lv2 DESC, revenue_by_lv3 DESC, revenue_by_items DESC
            """,
            parameters=[subject_id, subject_id, brand, brand, start, end]
        ).df()
    return df




        