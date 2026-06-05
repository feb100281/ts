# cards/wo_app/data.py
from conns import get_duckdb_conn
from datetime import datetime, date, timedelta
from .product_rules import get_product_family, PRODUCT_GROUPS


def get_data_by_date(start=None, end=None):
    start_date = start if start else date(2004,1,1)
    end_date = end if end else date.today()
        
    with get_duckdb_conn() as con:
        df = con.execute(
            """ 
            select
            x.date_from,
            round(x.amount/100.00,2) as amount,
            round(x.vat_amount/100.00,2) as vat_amount,
            round(x.amount_vatless/100,2) as amount_vatless,
            round(x.cogs/100,2) as cogs,
            x.total_net_sales,
            x.no_cost,
            round(coalesce(x.comparison_rev,0)/100.0,2) as comparison_rev,
            round(
                case
                    when coalesce(x.comparison_rev,0) = 0
                    then 0
                    else x.cogs / x.comparison_rev * 100
                end,
                2
            ) as margin
            from(
            select  
            date_from,
            sum(cr_rev) as amount,
            sum(cr_rev) -
            sum(cr_rev / (100+vat_rate) * 100) as vat_amount,
            sum(cr_rev / (100+vat_rate) * 100) as amount_vatless,
            sum(cr) as cogs,    
            count(cr_rev) as total_net_sales,
            count(cr_rev) filter (where cr =0) as no_cost,
            coalesce(
                sum(cr_rev) filter (where cr <> 0),
                0
            ) as comparison_rev
            from inventories.inv_gl_final    
            where cr_rev <> 0                       
            group by date_from
            ) x
            where x.date_from between ? and ?
            order by x.date_from desc
            """,
            parameters=[start_date, end_date]
        ).df()

        df["date_from"] = (
            df["date_from"]
            .dt.date
        )

    return df

# def get_data_by_item(start, end):
    
#     with get_duckdb_conn() as con:
#         df = con.execute(""" 
#         with a as (
#             SELECT
#             u.usk,
#             w.title,
#             STRING_AGG(distinct u.sa_name, ' | ') as nm_ids,
#             STRING_AGG(distinct t.title, ' | ') as aka,
#             count(distinct t.title) as titles_cnt,
#             case 
#             when count(distinct t.title) between 2 and 3  then '⚠️'
#             when count(distinct t.title) >= 4 then '‼️'
#             else '✅'
#             end as mix_warning
#             from inventories.usk u
#             left join inventories.wb_product w on w.card_id = u.usk
#             left join inventories.wb_product t on t.card_id = u.card_id
#             group by u.usk,
#             w.title
#             )
#             select 
#             x.usk,
#             a.title,
#             a.nm_ids,
#             a.aka,
#             a.titles_cnt,
#             a.mix_warning,
#             round(x.amount / 100.0,2) as amount,
#             round(x.vat_amount / 100.0,2) as vat_amount,
#             round(x.amount_vatless / 100.0,2) as amount_vatless,
#             round(x.dt / 100.0,2) as costs,
#             x.total_net_sales as total_net_sales_qty,
#             x.no_cost  as no_cost_qty,
#             round(x.comparison_revenue / 100.0,2) as comparison_revenue,
#             COALESCE(round((x.comparison_revenue - x.dt) /100.00,2),0) as net_margin,
#             round((x.comparison_revenue - x.dt)/NULLIF(x.comparison_revenue, 0) * 100.00,2) AS relative_margin,
#             ROUND(price_high/100.00,2) as price_high,
#             ROUND(price_low/100.00,2) as price_low,
#             ROUND(price_median/100.00,2) as price_median,
#             ROUND(price_mean/100.00,2) as price_mean,
#             ROUND(cost_high/100.00,2) as cost_high,
#             ROUND(cost_low/100.00,2) as cost_low,
#             ROUND(costs_median/100.00,2) as costs_median,
#             ROUND(cost_mean/100.00,2) as cost_mean

#             from (
#             select 
#             t.usk,
            
#             sum(t.cr_rev) as amount,
#             sum(t.cr_rev) -
#             sum(t.cr_rev / (100+t.vat_rate) * 100) as vat_amount,
#             sum(t.cr_rev / (100+t.vat_rate) * 100) as amount_vatless,
#             COALESCE(sum(t.cr),0) as dt,
#             count(t.cr_rev) as total_net_sales,
#             sum(case when COALESCE(t.cr,0) = 0 then 1 else 0 end) as no_cost,
#             sum(case when COALESCE(t.cr,0) <> 0 then (t.cr_rev / (100+t.vat_rate) * 100)  else 0 end) as comparison_revenue,
#             max(t.cr_rev) as price_high,
#             min(t.cr_rev) as price_low,
#             MEDIAN(t.cr_rev) as price_median,
#             AVG(t.cr_rev) as price_mean,
#             max(NULLIF(t.cr, 0)) AS cost_high,
#             min(NULLIF(t.cr, 0)) AS cost_low,
#             MEDIAN(NULLIF(t.cr, 0)) AS costs_median,
#             avg(NULLIF(t.cr, 0)) AS cost_mean
#             from inventories.gl_main t
#             where sales_date between ? and ?
#             group by t.usk
#             ) x
#             left join a on a.usk = x.usk;
#         """, parameters=[start,end]
#         ).df()
#     return df


def get_data_by_item(start, end):

    with get_duckdb_conn() as con:
        # Сначала получаем базовые данные с тайтлами
        df = con.execute(""" 
        with a as (
            SELECT
            u.usk,
            w.title,
            STRING_AGG(distinct u.sa_name, ' | ') as nm_ids,
            STRING_AGG(distinct t.title, ' | ') as aka,
            count(distinct t.title) as titles_cnt
            from inventories.usk u
            left join inventories.wb_product w on w.card_id = u.usk
            left join inventories.wb_product t on t.card_id = u.card_id
            group by u.usk, w.title
        )
        select 
        x.usk,
        a.title,
        a.nm_ids,
        a.aka,
        a.titles_cnt,
        round(x.amount / 100.0,2) as amount,
        round(x.vat_amount / 100.0,2) as vat_amount,
        round(x.amount_vatless / 100.0,2) as amount_vatless,
        round(x.dt / 100.0,2) as costs,
        x.total_net_sales as total_net_sales_qty,
        x.no_cost  as no_cost_qty,
        round(x.comparison_revenue / 100.0,2) as comparison_revenue,
        COALESCE(round((x.comparison_revenue - x.dt) /100.00,2),0) as net_margin,
        round((x.comparison_revenue - x.dt)/NULLIF(x.comparison_revenue, 0) * 100.00,2) AS relative_margin,
        ROUND(price_high/100.00,2) as price_high,
        ROUND(price_low/100.00,2) as price_low,
        ROUND(price_median/100.00,2) as price_median,
        ROUND(price_mean/100.00,2) as price_mean,
        ROUND(cost_high/100.00,2) as cost_high,
        ROUND(cost_low/100.00,2) as cost_low,
        ROUND(costs_median/100.00,2) as costs_median,
        ROUND(cost_mean/100.00,2) as cost_mean

        from (
        select 
        t.usk,
        
        sum(t.cr_rev) as amount,
        sum(t.cr_rev) -
        sum(t.cr_rev / (100+t.vat_rate) * 100) as vat_amount,
        sum(t.cr_rev / (100+t.vat_rate) * 100) as amount_vatless,
        COALESCE(sum(t.cr),0) as dt,
        count(t.cr_rev) as total_net_sales,
        sum(case when COALESCE(t.cr,0) = 0 then 1 else 0 end) as no_cost,
        sum(case when COALESCE(t.cr,0) <> 0 then (t.cr_rev / (100+t.vat_rate) * 100)  else 0 end) as comparison_revenue,
        max(t.cr_rev) as price_high,
        min(t.cr_rev) as price_low,
        MEDIAN(t.cr_rev) as price_median,
        AVG(t.cr_rev) as price_mean,
        max(NULLIF(t.cr, 0)) AS cost_high,
        min(NULLIF(t.cr, 0)) AS cost_low,
        MEDIAN(NULLIF(t.cr, 0)) AS costs_median,
        avg(NULLIF(t.cr, 0)) AS cost_mean
        from inventories.gl_main t
        where sales_date between ? and ?
        group by t.usk
        ) x
        left join a on a.usk = x.usk;
    """, parameters=[start,end]).df()
    
    # ========== НОВАЯ ЛОГИКА ОБРАБОТКИ ==========
    
    # 1. Определяем семейство для каждого товара
    families = df['title'].apply(lambda x: get_product_family(x))
    df['product_family_key'] = families.apply(lambda x: x[0])
    df['product_family_label'] = families.apply(lambda x: x[1])
    
    # 2. Группируем по USK и считаем разные семейства
    # Для этого нужно собрать все тайтлы внутри USK
    usk_families = df.groupby('usk')['product_family_key'].agg(
        unique_families=lambda x: list(set(x)),
        families_cnt='nunique'
    ).reset_index()
    
    # 3. Добавляем информацию о пересорте
    df = df.merge(usk_families[['usk', 'families_cnt', 'unique_families']], on='usk', how='left')
    
    # 4. Создаем финальный warning
    def determine_warning(row):
        if row['families_cnt'] > 1:
            families_list = ', '.join(row['unique_families'])
            return f'🔄 ПЕРЕСОРТ ({families_list})'
        elif row['titles_cnt'] >= 4:
            return '‼️'
        elif row['titles_cnt'] >= 2:
            return '⚠️'
        else:
            return '✅'
    
    df['mix_warning'] = df.apply(determine_warning, axis=1)
    
    # 5. Добавляем колонку с семействами для отладки (опционально)
    df['families_detected'] = df['unique_families'].apply(lambda x: ' | '.join(x))
    
    return df
