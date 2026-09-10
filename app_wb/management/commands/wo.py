import os
import duckdb
from duckdb import DuckDBPyConnection
from django.core.management.base import BaseCommand, CommandError

from conns import get_duckdb_conn_with_opt


MAKE_SALES_GL = """ 
create or replace table inventories.sales_gl as
with a as (
    select
        rrd_id,
        nm_id,
        date_from,
        oper,
        vat_rate,
        val
    from sales.sales_long
    where field = 'retail_price'
),

dt_rows as (
    select
        *,
        row_number() over (
            partition by nm_id, val
            order by date_from, rrd_id
        ) as rn
    from a
    where oper = 'dt'
),

cr_rows as (
    select
        *,
        row_number() over (
            partition by nm_id, val
            order by date_from, rrd_id
        ) as rn
    from a
    where oper = 'cr'
),

matched as (
    select
        d.rrd_id
    from dt_rows d
    join cr_rows c
        on d.nm_id = c.nm_id
       and d.val = c.val
       and d.rn = c.rn
)

select
    t.rrd_id,
    t.nm_id,
    COALESCE(u.usk,t.nm_id) as usk,
    t.date_from,
    t.vat_rate,
    0::bigint as dt,
    t.val::bigint as cr
from dt_rows t
left join inventories.usk u on u.card_id = t.nm_id
where rrd_id not in (
    select rrd_id
    from matched
);
"""

MAKE_WRITE_OFF = """ 
create or replace table inventories.write_off as
WITH sales AS (
    SELECT
        usk,
        list(date_from ORDER BY date_from, rrd_id) AS sales_dates,
        list(cr ORDER BY date_from, rrd_id) AS sales_cr,
        list(rrd_id ORDER BY date_from, rrd_id) AS rrd_ids,
        list(vat_rate ORDER BY date_from, rrd_id) as vat_rates
    FROM inventories.sales_gl
    GROUP BY usk
),

inv AS (
    SELECT
        usk,
        list(id ORDER BY date_from, id) AS inv_ids,
        list(date_from ORDER BY date_from, id) AS inv_dates,
        list(dt ORDER BY date_from, id) AS inv_dt
    FROM inventories.inv_gl
    WHERE usk IS NOT NULL
    GROUP BY usk
)

SELECT
    coalesce(i.usk, s.usk) AS usk,

    i.inv_ids,
    i.inv_dates,
    i.inv_dt,

    s.sales_dates,
    s.sales_cr,
    s.rrd_ids,
    s.vat_rates,

    case
        when s.sales_dates is null then 0
        else len(s.sales_dates)
    end as sales_qty,

    case
        when i.inv_ids is null then 0
        else len(i.inv_ids)
    end as inv_qty

FROM inv i
FULL OUTER JOIN sales s
    ON i.usk = s.usk;
"""

MAKE_GL_MAIN = """
CREATE OR REPLACE TABLE inventories.gl_main AS
WITH x AS (
    SELECT
        usk,
        sales_dates,
        sales_cr,
        vat_rates,
        rrd_ids,
        list_resize(
            inv_ids,
            sales_qty,
            0
        ) AS inv_ids,
        list_resize(
            inv_dt,
            sales_qty,
            0
        ) AS inv_dt
    FROM inventories.write_off
    WHERE sales_qty > 0
)
SELECT
    usk,
    unnest(inv_ids) AS inv_id,
    unnest(inv_dt) AS cr,
    unnest(sales_dates)
        AS sales_date,
    coalesce(
        unnest(vat_rates),
        0
    ) AS vat_rate,
    unnest(sales_cr)
        AS cr_rev,
    unnest(rrd_ids)
        AS rrd_id
FROM x;
"""

MAKE_FINAL_GL = """ 
CREATE OR REPLACE TABLE inventories.inv_gl_final AS
WITH x AS (
    SELECT
        usk,
        case
            when inv_qty > sales_qty
                then sales_qty
            else inv_qty
        end as cut_qty,
        inv_ids,
        inv_dt,
        sales_dates,
        sales_cr,
        vat_rates,
        rrd_ids
    FROM inventories.write_off
    WHERE sales_qty > 0
      AND inv_qty > 0
),

cut AS (
    SELECT
        usk,
        list_slice(inv_ids, 1, cut_qty) AS inv_ids,
        list_slice(inv_dt, 1, cut_qty) AS inv_dt,
        list_slice(sales_dates, 1, cut_qty) AS sales_dates,
        list_slice(sales_cr, 1, cut_qty) AS sales_cr,
        list_slice(vat_rates, 1, cut_qty) AS vat_rates,
        list_slice(rrd_ids, 1, cut_qty) AS rrd_ids
    FROM x
),

fifo_cr AS (
    SELECT
        -- NULL::BIGINT AS id,
        unnest(inv_ids) as id,
        unnest(sales_dates) AS date_from,        
        cut.usk,
        NULL AS brand,
        NULL::BIGINT AS chrt_id,

        0::BIGINT AS dt,
        unnest(inv_dt) AS cr,

        0::BIGINT AS dt_man,
        0::BIGINT AS cr_man,

        unnest(sales_cr) AS cr_rev,
        unnest(vat_rates) AS vat_rate,
        unnest(rrd_ids) AS rrd_id
    FROM cut
   
)

SELECT
    id,
    date_from,
    upd_document_id,
    usk,
    brand,
    chrt_id,
    dt,
    cr,
    dt_man,
    cr_man,
    cr_rev,
    0 as vat_rate,
    rrd_id
FROM inventories.inv_gl

UNION ALL

SELECT
    t.id,
    t.date_from,
    i.upd_document_id as upd_document_id,
    t.usk,
    t.brand,
    t.chrt_id,
    t.dt,
    t.cr,
    t.dt_man,
    t.cr_man,
    t.cr_rev,
    t.vat_rate,
    t.rrd_id
FROM fifo_cr t
left join inventories.inv_gl i on i.id = t.id;
"""


class Command(BaseCommand):
    help = "THIS IS THE WRITE OFF ETL"
    
    def handle(self, *args, **options):
        try:
            with get_duckdb_conn_with_opt() as con:
                
               
                
                self.stdout.write(
                    self.style.NOTICE("Делаем таблицы для списаний продаж")                    
                )
                con.execute(MAKE_SALES_GL)
                con.execute(MAKE_WRITE_OFF)                
                con.execute(MAKE_GL_MAIN)
                con.execute(MAKE_FINAL_GL)
                
                con.execute("""
                    DROP TABLE IF EXISTS pg.gl.inv_gl_final
                """)

                con.execute("""
                    CREATE TABLE pg.gl.inv_gl_final AS
                    SELECT *
                    FROM inventories.inv_gl_final
                """)
                    
                
                self.stdout.write(
                    self.style.SUCCESS("Основные таблицы inventorie.gl_main, inventorie.write_off и inventorie.inv_gl_final созданы")                    
                )
               
        
        except Exception as e:
            raise CommandError(f"DuckDB error: {e}")


