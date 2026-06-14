# cards/wo_app/data.py
from conns import get_duckdb_conn
from datetime import datetime, date, timedelta


def get_data_by_date(start=None, end=None):
    start_date = start if start else date(2004,1,1)
    end_date = end if end else date.today()
        
    with get_duckdb_conn() as con:
        df = con.execute(
            """ 
            with a as (
        select 
        rrd_id,
        COALESCE(sum(val) filter (where field = 'comission' and oper = 'dt'),0) -
        COALESCE(sum(val) filter (where field = 'comission' and oper = 'cr')) as gross_comission,
        COALESCE(sum(val / (100+vat_rate)*100) filter (where field = 'comission' and oper = 'dt'),0) -
        COALESCE(sum(val/ (100+vat_rate)*100) filter (where field = 'comission' and oper = 'cr')) as net_comission
        from sales.sales_long
        group by rrd_id
    ),
    b as (
    select 
        date_from,
        COALESCE(sum(val/(100+vat_rate)*100) filter (where oper = 'dt'),0) -
        COALESCE(sum(val/(100+vat_rate)*100) filter (where oper = 'cr'),0) 
        as wb_costs
        from sales.sales_long
        where field not in (
            'ppvz_for_pay',
            'comission',
            'retail_amount',
            'retail_price'
            )
        GROUP BY date_from
    )
    select
    x.date_from,
    round(x.amount/100.00,2) as amount,
    round(x.vat_amount/100.00,2) as vat_amount,
    round(x.amount_vatless/100,2) as amount_vatless,
    round(x.cogs/100,2) as cogs,
    round((x.amount_vatless - x.cogs)/100.00,2) as margin_gross,
    x.total_net_sales,
    x.no_cost,
    round(coalesce(x.comparison_rev,0)/100.0,2) as comparison_rev,
    round((coalesce(x.comparison_rev,0) - x.cogs)/100.00,2) as man_margin,
    
    round(
        case
            when coalesce(x.comparison_rev,0) = 0
            then 0
            else round((coalesce(x.comparison_rev,0) - x.cogs) / coalesce(x.comparison_rev,0) * 100.0,2)
        end,
        2
    ) as margin,
    round(net_comission/100.0,2) as net_comission,
    abs(round(net_comission / amount_vatless * 100.0,2)) as wb_comission,
    round((x.amount_vatless - x.cogs + net_comission)/100.0,2) as acc_margin,    
    round(x.wb_costs / 100.0,2) as wb_costs,
    round((x.amount_vatless - x.cogs + net_comission+wb_costs)/100.0,2) as day_result
    from(
    select  
    t.date_from,
    sum(cr_rev) as amount,
    sum(cr_rev) -
    sum(cr_rev / (100+vat_rate) * 100) as vat_amount,
    sum(cr_rev / (100+vat_rate) * 100) as amount_vatless,
    sum(cr) as cogs,    
    count(cr_rev) as total_net_sales,
    count(cr_rev) filter (where cr =0) as no_cost,
    sum(
    case
        when coalesce(cr, 0) <> 0
        then (
            cr_rev
            / (100 + coalesce(vat_rate, 0))
            * 100
        )
        else 0
    end
    ) as comparison_rev,
    sum(a.net_comission) as net_comission,
    b.wb_costs
    from inventories.inv_gl_final t    
    left join a on a.rrd_id = t.rrd_id
    left join b on t.date_from::date = b.date_from::date
    where cr_rev <> 0                       
    group by t.date_from,  b.wb_costs
    ) x
    where x.date_from between ? and ?
    order by x.date_from desc;

            """,
            parameters=[start_date, end_date]
        ).df()

        df["date_from"] = (
            df["date_from"]
            .dt.date
        )

    return df

def get_data_by_item(start, end):

    with get_duckdb_conn() as con:
        df = con.execute(
            """
            with a as (
    SELECT
        u.usk,
        w.title,
        STRING_AGG(distinct u.sa_name, ' | ') as nm_ids,
        STRING_AGG(distinct t.title, ' | ') as aka,
        count(distinct t.title) as titles_cnt,
        case 
            when count(distinct t.title) between 2 and 3 then '⚠️'
            when count(distinct t.title) >= 4 then '‼️'
            else '✅'
        end as mix_warning
    from inventories.usk u
    left join inventories.wb_product w
        on w.card_id = u.usk
    left join inventories.wb_product t
        on t.card_id = u.card_id
    group by
        u.usk,
        w.title
),
stock_q as (
    
    select
        usk,
        count(dt) filter (where dt <> 0) as dt_qty,
        count(cr) filter (where cr <> 0) as cr_qty,
        count(cr) filter (where cr <> 0 and date_from < '2024-01-01') as cr_qty_2023
    from inventories.inv_gl_final
    where date_from <= ?
    group by usk
)  

-- Основной SELECT
SELECT 
    x.usk,
    a.title,
    a.nm_ids,
    a.aka,
    a.titles_cnt,
    a.mix_warning,

    round(x.amount / 100.0, 2) as amount,
    round(x.vat_amount / 100.0, 2) as vat_amount,
    round(x.amount_vatless / 100.0, 2) as amount_vatless,
    round(x.dt / 100.0, 2) as costs,

    s.dt_qty as dt_qty,
    s.cr_qty,
    s.cr_qty_2023 as cr_qty_2023,
    x.total_net_sales as total_net_sales_qty,
    s.dt_qty - x.total_net_sales - s.cr_qty_2023 as stocks_qty,
    x.no_cost as no_cost_qty,

    round(x.comparison_revenue / 100.0, 2) as comparison_revenue,

    coalesce(
        round(
            (x.comparison_revenue - x.dt) / 100.00,
            2
        ),
        0
    ) as net_margin,

    coalesce(
        round(
            (
                x.comparison_revenue - x.dt
            )
            / nullif(x.comparison_revenue, 0)
            * 100.00,
            2
        ),
        0
    ) as relative_margin,

    round(price_high / 100.00, 2) as price_high,
    round(price_low / 100.00, 2) as price_low,
    round(price_median / 100.00, 2) as price_median,
    round(price_mean / 100.00, 2) as price_mean,

    round(cost_high / 100.00, 2) as cost_high,
    round(cost_low / 100.00, 2) as cost_low,
    round(costs_median / 100.00, 2) as costs_median,
    round(cost_mean / 100.00, 2) as cost_mean

from (
    select
        t.usk,

        sum(t.cr_rev) as amount,

        sum(t.cr_rev)
        - sum(
            t.cr_rev
            / (100 + coalesce(t.vat_rate, 0))
            * 100
        ) as vat_amount,

        sum(
            t.cr_rev
            / (100 + coalesce(t.vat_rate, 0))
            * 100
        ) as amount_vatless,

        coalesce(sum(t.cr), 0) as dt,

        count(t.cr_rev) as total_net_sales,

        sum(
            case
                when coalesce(t.cr, 0) = 0
                then 1
                else 0
            end
        ) as no_cost,

        sum(
            case
                when coalesce(t.cr, 0) <> 0
                then (
                    t.cr_rev
                    / (100 + coalesce(t.vat_rate, 0))
                    * 100
                )
                else 0
            end
        ) as comparison_revenue,

        max(t.cr_rev) as price_high,
        min(t.cr_rev) as price_low,
        median(t.cr_rev) as price_median,
        avg(t.cr_rev) as price_mean,

        max(nullif(t.cr, 0)) as cost_high,
        min(nullif(t.cr, 0)) as cost_low,
        median(nullif(t.cr, 0)) as costs_median,
        avg(nullif(t.cr, 0)) as cost_mean

    from inventories.inv_gl_final t
    where
        t.date_from between ? and ?
        and 
        t.cr_rev <> 0
    group by t.usk
) x
left join a
    on a.usk = x.usk
left join stock_q s 
    on s.usk = x.usk  
            """,
            parameters=[end, start, end]
        ).df()

    return df

def get_inventories_by_date(date_to):
    df = get_data_by_item(date(2023,1,1),date_to)
    with get_duckdb_conn() as con:
        con.register("items",df)
        rel = con.sql(
            """ 
            WITH wb_stocks AS (
                SELECT
                    COALESCE(u.usk, t.nm_id) AS usk,
                    SUM(
                        t.quantity +
                        t.in_way_from_client +
                        t.in_way_from_client
                    ) AS residual
                FROM stocks.unpacked_stocks t
                LEFT JOIN inventories.usk u
                    ON u.card_id = t.nm_id
                WHERE date_from = ?
                GROUP BY COALESCE(u.usk, t.nm_id)
            ),

            gl_stocks AS (
                SELECT
                    t.usk,
                    COUNT(t.dt) FILTER (WHERE t.dt <> 0) AS dt_qty,
                    COUNT(t.cr) FILTER (WHERE t.cr <> 0) AS cr_qty,
                    COUNT(t.dt) FILTER (WHERE t.dt <> 0)
                    - COUNT(t.cr) FILTER (WHERE t.cr <> 0) AS residual
                FROM inventories.inv_gl_final t
                WHERE date_from <= ?
                GROUP BY t.usk
            )

            SELECT
                COALESCE(g.usk, w.usk) AS usk,
                COALESCE(g.residual,0) AS gl_residual,
                COALESCE(w.residual,0) AS stock_residual,
                COALESCE(g.residual, 0) - COALESCE(w.residual, 0) AS diff
            FROM gl_stocks g
            FULL OUTER JOIN wb_stocks w
                ON w.usk = g.usk
            ORDER BY usk;            
            """,
            params=[date_to,date_to]
        )
        con.register("stocks",rel)
        
        
        
    
    
