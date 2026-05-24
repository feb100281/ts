import os
import duckdb
from duckdb import DuckDBPyConnection
import json
from django.core.management.base import BaseCommand, CommandError
from django.db import models
from django.db import transaction
from django.db import connection

from dotenv import load_dotenv

import psycopg
from psycopg.rows import dict_row
from psycopg import Connection
import pandas as pd
import numpy as np

from cards.models import WbProduct, UPDData, USK, UskUpd, UpdDocument

load_dotenv()


DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME")


def connect_db():
    return psycopg.connect(
        dbname=os.getenv("DB_NAME"),  # DB_NAME
        user=os.getenv("DB_USER"),  # DB_USER
        password=os.getenv("DB_PASSWORD"),  # DB_PASSWORD
        host=os.getenv("DB_HOST", "localhost"),  # DB_HOST
        port=os.getenv("DB_PORT", "5432"),  # DB_PORT
        connect_timeout=10,
    )
    
FIND_KEY = """
CREATE OR REPLACE TABLE inventories.stock_key AS

WITH upd AS (
    SELECT
        upd_sa_name,
        trim(left(upd_sa_name, 10)) AS prefix,
        trim(left(upd_sa_name, 9)) AS prefix9
    FROM inventories.upd_income
),

matched AS (
    SELECT
        t.upd_sa_name,
        list(distinct p.sa_name ORDER BY p.sa_name) AS sa_names
    FROM upd t
    LEFT JOIN inventories.wb_product p
        ON starts_with(p.sa_name, t.prefix)
        OR starts_with(p.sa_name, '0' || t.prefix9)
    GROUP BY t.upd_sa_name
)

SELECT
    upd_sa_name,
    sa_names,
    sa_names[1] AS stock_key
FROM matched;

"""


MAKE_USK = """
CREATE or replace table inventories.usk as
with b as (
SELECT
"upd_sa_name",
"stock_key",
unnest(sa_names) as sa_name
from inventories.stock_key
),
a as (select
sa_name,
list(DISTINCT stock_key order by stock_key)[1] as usk,
list(DISTINCT stock_key order by stock_key) as stock_keys,
list(DISTINCT upd_sa_name order by upd_sa_name) as upd_sa_names
from b
where stock_key is not null
group by sa_name
)
select 
a.sa_name,
p.card_id,
a.usk as usk_sa_name,
pa.card_id as usk,
a.upd_sa_names
from a
left join inventories.wb_product p on p.sa_name = a.sa_name
left join inventories.wb_product pa on pa.sa_name = a.usk;
"""


MAKE_UPD_USK = """ 
CREATE or replace table inventories.usk_upd as
SELECT DISTINCT
unnest(upd_sa_names) as upd_sa_name,
usk
from inventories.usk;
"""


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


MAKE_INV_GL = """ 
CREATE OR REPLACE TABLE inventories.inv_gl AS
SELECT
    row_number() OVER (
        ORDER BY
            u.date,
            t.upd_document_id,
            t.nm_id,
            t.chrt_id
    ) AS id,

    u.date AS date_from,
    t.upd_document_id,
    t.nm_id AS usk,
    t.brand,
    t.chrt_id,    

    COALESCE(round(t.upd_price_vatless * 100, 0),0)::BIGINT AS dt,
    0::BIGINT AS cr,
    COALESCE(round(t.man_cost_per_unit * 100, 0),0)::BIGINT AS dt_man,
    0::BIGINT AS cr_man,
    0::bigint as cr_rev,
    0::bigint as rrd_id

FROM inventories.upd_income t
LEFT JOIN inventories.upd_documents u
    ON u.id = t.upd_document_id,
UNNEST(range(CAST(t.upd_qty AS BIGINT))) x(i)

WHERE t.nm_id IS NOT NULL;
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
        list_slice(rrd_ids, 1, cut_qty) AS rrd_ids
    FROM x
),

fifo_cr AS (
    SELECT
        NULL::BIGINT AS id,
        unnest(sales_dates) AS date_from,
        NULL::BIGINT AS upd_document_id,
        usk,
        NULL AS brand,
        NULL::BIGINT AS chrt_id,

        0::BIGINT AS dt,
        unnest(inv_dt) AS cr,

        0::BIGINT AS dt_man,
        0::BIGINT AS cr_man,

        unnest(sales_cr) AS cr_rev,
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
    rrd_id
FROM inventories.inv_gl

UNION ALL

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
    rrd_id
FROM fifo_cr;
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


def update_usk_table(df:pd.DataFrame):
    pass


class Command(BaseCommand):
    help = "THIS IS THE INVENTORIES ETL"
    def _prepare_df(self, queryset, model):
        df = pd.DataFrame.from_records(queryset.values())
        # DecimalField -> float
        decimal_fields = [
            field.name
            for field in model._meta.fields
            if isinstance(field, models.DecimalField)
        ]
        for col in decimal_fields:
            if col in df.columns:
                df[col] = df[col].astype(float)
        return df
    def handle(self, *args, **options):
        db_path = os.getenv("DUCKDB_PATH")
        try:
            with duckdb.connect(db_path) as con:
                
                was_no_keys = 0
                was_no_costs = 0
                try:
                    was_keys = con.execute(
                        """ 
                        select count(*)
                        from (
                        select 
                        t.card_id,
                        u.usk
                        from inventories.wb_product t
                        left join inventories.usk u on u.card_id = t.card_id
                        where u.usk is null
                        )
                        """
                    ).fetchone()[0]
                    
                    was_sales_wo_costs = con.execute("select sum(sales_qty) from inventories.write_off where inv_qty = 0").fetchone()[0]
                    
                    was_no_keys = was_keys
                    was_no_costs = was_sales_wo_costs
                
                except:
                    self.stdout.write(
                    self.style.NOTICE("Пока таблицы не созданы")
                )
                
                self.stdout.write(
                    self.style.NOTICE("Получаем обновленные данные из карточек и УПЛ")
                )
                
                product_df = self._prepare_df(
                    WbProduct.objects.all(),
                    WbProduct
                )
                income_lines_df = self._prepare_df(
                    UPDData.objects.all(),
                    UPDData
                )
                upd_documets_df = self._prepare_df(
                    UpdDocument.objects.all(),
                    UpdDocument
                )
                con.execute("""
                    CREATE SCHEMA IF NOT EXISTS inventories
                """)
                
                self.stdout.write(
                    self.style.SUCCESS("Данные получены")
                )
                self.stdout.write(
                    self.style.NOTICE("Записываем временные данные из моделей")
                )

                con.execute("""
                    CREATE OR REPLACE TABLE inventories.wb_product
                    AS SELECT * FROM product_df
                """)

                con.execute("""
                    CREATE OR REPLACE TABLE inventories.upd_income
                    AS SELECT * FROM income_lines_df
                """)
                
                con.execute("""
                    CREATE OR REPLACE TABLE inventories.upd_documents
                    AS SELECT * FROM upd_documets_df
                """)
                
                self.stdout.write(
                    self.style.SUCCESS("Созданы таблицы inventories.upd_income и inventories.wb_product")                    
                )
                
                self.stdout.write(
                    self.style.NOTICE("Расчитываем складские ключи для артиклей УПД - это может занять нескольно минут")
                )
                con.execute(FIND_KEY)
                self.stdout.write(
                    self.style.SUCCESS("Расчет ключей завершен")                    
                )
                
                self.stdout.write(
                    self.style.NOTICE("Импортируем ключи в базу данных и обновляем таблицы")
                )
                con.execute(MAKE_USK)
                con.execute(MAKE_UPD_USK)        
                
                with connection.cursor() as cursor:

                    cursor.execute("""
                        TRUNCATE TABLE
                            cards_usk,
                            cards_uskupd
                        RESTART IDENTITY
                    """)
                
                with transaction.atomic():

                    # очищаем
                    USK.objects.all().delete()
                    UskUpd.objects.all().delete()

                    # вытаскиваем из duckdb
                    usk_df = con.execute("""
                        SELECT
                            sa_name,
                            card_id,
                            usk_sa_name,
                            usk,
                            upd_sa_names
                        FROM inventories.usk
                    """).df()
                    
                    usk_df["upd_sa_names"] = usk_df["upd_sa_names"].apply(
                        lambda x: x.tolist()
                        if isinstance(x, np.ndarray)
                        else x
                    )

                    upd_usk_df = con.execute("""
                        SELECT
                            upd_sa_name,
                            usk
                        FROM inventories.usk_upd
                    """).df()

                    # bulk insert
                    USK.objects.bulk_create(
                        [
                            USK(
                                sa_name=row.sa_name,
                                card_id=row.card_id,
                                usk_sa_name=row.usk_sa_name,
                                usk=row.usk,
                                upd_sa_names=row.upd_sa_names,
                            )
                            for row in usk_df.itertuples(index=False)
                        ],
                        batch_size=5000,
                    )

                    UskUpd.objects.bulk_create(
                        [
                            UskUpd(
                                upd_sa_name=row.upd_sa_name,
                                usk=row.usk,
                            )
                            for row in upd_usk_df.itertuples(index=False)
                        ],
                        batch_size=5000,
                    )

                self.stdout.write(
                    self.style.SUCCESS("Ключи созданы")                    
                )
                self.stdout.write(
                    self.style.NOTICE("Обновляем таблицу UPD_income_lines")
                )
                
                with connection.cursor() as cursor:

                    cursor.execute("""
                        UPDATE upd_income_lines u
                        SET nm_id = m.usk
                        FROM cards_uskupd m
                        WHERE u.upd_sa_name = m.upd_sa_name
                    """)
                
                con.execute(
                    """ 
                    UPDATE inventories.upd_income u
                    SET nm_id = m.usk
                    FROM inventories.usk_upd m
                    WHERE u.upd_sa_name = m.upd_sa_name 
                    """
                )
                
                self.stdout.write(
                    self.style.SUCCESS("USK обновлены для всех приходов по УПД")                    
                )  
                
                self.stdout.write(
                    self.style.NOTICE("Делаем таблицы для списаний продаж")                    
                )
                con.execute(MAKE_SALES_GL)
                con.execute(MAKE_INV_GL)
                con.execute(MAKE_WRITE_OFF)
                con.execute(MAKE_FINAL_GL)
                con.execute(MAKE_GL_MAIN)
                self.stdout.write(
                    self.style.SUCCESS("Основные таблицы inventorie.gl_main, inventorie.write_off и inventorie.inv_gl_final созданы")                    
                )
                now_keys = con.execute(
                        """ 
                        select count(*)
                        from (
                        select 
                        t.card_id,
                        u.usk
                        from inventories.wb_product t
                        left join inventories.usk u on u.card_id = t.card_id
                        where u.usk is null
                        )
                        """
                    ).fetchone()[0]
                
                self.stdout.write(
                    self.style.WARNING(f"Не было ключей {was_no_keys} / стало ключей {now_keys}")                    
                )      
                
                now_no_costs = con.execute("select sum(sales_qty) from inventories.write_off where inv_qty = 0").fetchone()[0]
                
                self.stdout.write(
                    self.style.WARNING(f"Не было себестоимости для  {was_no_costs} продаж / стало  {now_no_costs}")                    
                )   
        
        except Exception as e:
            raise CommandError(f"DuckDB error: {e}")
        
        
        
        
        