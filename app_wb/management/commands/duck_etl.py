# ОБРАБОТКА ПРОДАЖ

import os
import duckdb
from duckdb import DuckDBPyConnection
import json
from django.core.management.base import BaseCommand, CommandError

from dotenv import load_dotenv

import psycopg
from psycopg.rows import dict_row
from psycopg import Connection
import pandas as pd

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


# --------
# Запросы
# --------

# Обновляем таблицу raw
def insert_new_rows(con:DuckDBPyConnection):
    con.execute("""
    INSERT INTO sales.wb_raw(
        rrd_id,
    rr_dt,
    date_from,

    nm_id,
    report_type,
    ts_name,
    sop_name,
    dtn,
    report_id,
    barcode,
    srid,
    gi_id,
    currency_name,
    btn,

    comissioning_percent,
    sale_percent,
    quantity,

    retail_price,
    retail_amount,
    loyalty_discount,
    ppvz_for_pay,
    delivery_rub,
    storage_fee,
    acceptance,
    deduction,
    penalty,
    additional_payment,
    cashback_amount,
    cashback_commission_change,
    payment_schedule,

    _loaded_at
    )
    SELECT
    rrd_id,
    rr_dt,
    date_from,

    nm_id,
    report_type,
    ts_name,
    sop_name,
    dtn,
    report_id,
    barcode,
    srid,
    gi_id,
    currency_name,
    btn,

    comissioning_percent,
    sale_percent,
    quantity,

    retail_price,
    retail_amount,
    loyalty_discount,
    ppvz_for_pay,
    delivery_rub,
    storage_fee,
    acceptance,
    deduction,
    penalty,
    additional_payment,
    cashback_amount,
    cashback_commission_change,
    payment_schedule,

    _loaded_at
FROM (
    SELECT
        rrd_id,
        rr_dt::DATE AS rr_dt,
        date_from::DATE AS date_from,

        json_extract_string(payload, '$.nmId')::BIGINT AS nm_id,
        json_extract_string(payload, '$.reportType')::INT AS report_type,
        json_extract_string(payload, '$.techSize') AS ts_name,
        json_extract_string(payload, '$.sellerOperName') AS sop_name,
        json_extract_string(payload, '$.docTypeName') AS dtn,
        json_extract_string(payload, '$.reportId') AS report_id,
        json_extract_string(payload, '$.sku') AS barcode,
        json_extract_string(payload, '$.srid') AS srid,
        json_extract_string(payload, '$.giId') AS gi_id,
        json_extract_string(payload, '$.currency') AS currency_name,
        json_extract_string(payload, '$.bonusTypeName') AS btn,
        json_extract_string(payload, '$.country') AS country,

        json_extract_string(payload, '$.commissionPercent')::DOUBLE AS comissioning_percent,
        json_extract_string(payload, '$.salePercent')::DOUBLE AS sale_percent,
        json_extract_string(payload, '$.quantity')::DOUBLE AS quantity,

        json_extract_string(payload, '$.retailPrice')::DOUBLE AS retail_price,
        json_extract_string(payload, '$.retailAmount')::DOUBLE AS retail_amount,
        json_extract_string(payload, '$.loyaltyDiscount')::DOUBLE AS loyalty_discount,
        json_extract_string(payload, '$.forPay')::DOUBLE AS ppvz_for_pay,
        json_extract_string(payload, '$.deliveryService')::DOUBLE AS delivery_rub,
        json_extract_string(payload, '$.paidStorage')::DOUBLE AS storage_fee,
        json_extract_string(payload, '$.paidAcceptance')::DOUBLE AS acceptance,
        json_extract_string(payload, '$.deduction')::DOUBLE AS deduction,
        json_extract_string(payload, '$.penalty')::DOUBLE AS penalty,
        json_extract_string(payload, '$.additionalPayment')::DOUBLE AS additional_payment,
        json_extract_string(payload, '$.cashbackAmount')::DOUBLE AS cashback_amount,
        json_extract_string(payload, '$.cashbackCommissionChange')::DOUBLE AS cashback_commission_change,
        json_extract_string(payload, '$.paymentSchedule')::DOUBLE AS payment_schedule,

        _loaded_at,

        ROW_NUMBER() OVER (
            PARTITION BY rrd_id
            ORDER BY _loaded_at DESC
        ) AS rn

    FROM new_rows
    WHERE rrd_id IS NOT NULL
)
WHERE rn = 1;
    """)
    

RAW_TABLE = """ 
    
CREATE OR REPLACE TABLE sales.wb_raw AS
SELECT
    rrd_id,
    rr_dt,
    date_from,

    nm_id,
    report_type,
    ts_name,
    sop_name,
    dtn,
    report_id,
    barcode,
    srid,
    gi_id,
    currency_name,
    btn,

    comissioning_percent,
    sale_percent,
    quantity,

    retail_price,
    retail_amount,
    loyalty_discount,
    ppvz_for_pay,
    delivery_rub,
    storage_fee,
    acceptance,
    deduction,
    penalty,
    additional_payment,
    cashback_amount,
    cashback_commission_change,
    payment_schedule,

    _loaded_at
FROM (
    SELECT
        rrd_id,
        rr_dt::DATE AS rr_dt,
        date_from::DATE AS date_from,

        json_extract_string(payload, '$.nmId')::BIGINT AS nm_id,
        json_extract_string(payload, '$.reportType')::INT AS report_type,
        json_extract_string(payload, '$.techSize') AS ts_name,
        json_extract_string(payload, '$.sellerOperName') AS sop_name,
        json_extract_string(payload, '$.docTypeName') AS dtn,
        json_extract_string(payload, '$.reportId') AS report_id,
        json_extract_string(payload, '$.sku') AS barcode,
        json_extract_string(payload, '$.srid') AS srid,
        json_extract_string(payload, '$.giId') AS gi_id,
        json_extract_string(payload, '$.currency') AS currency_name,
        json_extract_string(payload, '$.bonusTypeName') AS btn,
        json_extract_string(payload, '$.country') AS country,

        json_extract_string(payload, '$.commissionPercent')::DOUBLE AS comissioning_percent,
        json_extract_string(payload, '$.salePercent')::DOUBLE AS sale_percent,
        json_extract_string(payload, '$.quantity')::DOUBLE AS quantity,

        json_extract_string(payload, '$.retailPrice')::DOUBLE AS retail_price,
        json_extract_string(payload, '$.retailAmount')::DOUBLE AS retail_amount,
        json_extract_string(payload, '$.loyaltyDiscount')::DOUBLE AS loyalty_discount,
        json_extract_string(payload, '$.forPay')::DOUBLE AS ppvz_for_pay,
        json_extract_string(payload, '$.deliveryService')::DOUBLE AS delivery_rub,
        json_extract_string(payload, '$.paidStorage')::DOUBLE AS storage_fee,
        json_extract_string(payload, '$.paidAcceptance')::DOUBLE AS acceptance,
        json_extract_string(payload, '$.deduction')::DOUBLE AS deduction,
        json_extract_string(payload, '$.penalty')::DOUBLE AS penalty,
        json_extract_string(payload, '$.additionalPayment')::DOUBLE AS additional_payment,
        json_extract_string(payload, '$.cashbackAmount')::DOUBLE AS cashback_amount,
        json_extract_string(payload, '$.cashbackCommissionChange')::DOUBLE AS cashback_commission_change,
        json_extract_string(payload, '$.paymentSchedule')::DOUBLE AS payment_schedule,

        _loaded_at,

        ROW_NUMBER() OVER (
            PARTITION BY rrd_id
            ORDER BY _loaded_at DESC
        ) AS rn

    FROM sales.realization_raw
    WHERE rrd_id IS NOT NULL
)
WHERE rn = 1;
"""

SALES_LONG = """ 
with a as (
select 
rr_dt::date as date_from,
report_type::bigint as report_type,
rrd_id::bigint as rrd_id,
nm_id::bigint as nm_id,
ts_name::text as ts_name,
barcode::text as barcode,
btn,
dtn,
sop_name,
COALESCE(retail_price::double) as retail_price,
COALESCE(retail_amount::double) as retail_amount,
COALESCE(ppvz_for_pay::double) as ppvz_for_pay,
COALESCE(retail_price::double) - COALESCE(ppvz_for_pay::double) as comission,
COALESCE(delivery_rub::double) as delivery_rub,
COALESCE(storage_fee::double) as storage_fee,
COALESCE(acceptance::double) as acceptance,
COALESCE(deduction::double) as deduction,
COALESCE(penalty::double) as penalty,
COALESCE(additional_payment::double) as additional_payment,
COALESCE(cashback_amount::double) as cashback_amount,
COALESCE(cashback_commission_change::double) as cashback_commission_change,
COALESCE(payment_schedule::double) as payment_schedule
from sales.wb_raw
where quantity <> 2 
order by date_from desc

),
-- делаем dt/cr
dtcr as (
select 
x.date_from,
x.report_type,
x.rrd_id,
x.nm_id,
x.dtn,
x.sop_name,
x.btn,
x.ts_name,
x.barcode,
x.field,
CASE 
    WHEN x.field = 'additional_payment' 
        THEN abs(round(x.val * 100, 0))
    ELSE round(x.val * 100, 0)
END AS val,
CASE 
WHEN x.field in ('retail_price', 'retail_amount', 'ppvz_for_pay') and x.dtn = 'Продажа' then 'dt'
WHEN x.field in ('retail_price', 'retail_amount', 'ppvz_for_pay') and x.dtn = 'Возврат' then 'cr'
WHEN x.field in ('comission','cashback_amount','cashback_commission_change') and x.dtn = 'Продажа' then 'cr'
WHEN x.field in ('comission','cashback_amount','cashback_commission_change') and x.dtn = 'Возврат' then 'dt'
WHEN x.field = 'additional_payment' and x.val < 0 then 'dt' 
ELSE 'cr'
END as oper,
v.rate as general_vat_rate,
p.vat_rate as discount_vat_rate

from(
UNPIVOT a
ON COLUMNS(* EXCLUDE (date_from, report_type,rrd_id,nm_id,dtn,sop_name,btn,ts_name,barcode))
INTO
    NAME field
    VALUE val
) x
LEFT JOIN vat AS v
    ON x.date_from >= v.date_from 
   AND x.date_from < v.date_to
LEFT JOIN cards.product as p on p.nm_id = x.nm_id
where x.val != 0
),
vat_adj as (
select 
*,
CASE 
WHEN field in ('retail_price', 'retail_amount', 'ppvz_for_pay') then COALESCE(discount_vat_rate,general_vat_rate)
WHEN field in ('penalty') then 0.0
ELSE general_vat_rate
END as vat_rate
from dtcr 
)
select * from vat_adj
"""

UPDATE_WB_DISTRIBUTION = """ 
with a as (
select 
date_from::date as date_from,
report_type::bigint as report_type,
field::text as field,
val::bigint as val,
case when oper = 'dt' then 'dt_wb' else 'cr_wb' end as oper
from sales.sales_long
union all
select 
date_from::date as date_from,
report_type::bigint as report_type,
field::text as field,
round(val::bigint / (100+vat_rate) * 100,0)::bigint as val,
case when oper = 'dt' then 'dt_pl' else 'cr_pl' end as oper
from sales.sales_long
union all
select 
date_from::date as date_from,
report_type::bigint as report_type,
field::text as field,
round(val::bigint / (100+vat_rate) * vat_rate,0)::bigint as val,
case when oper = 'dt' then 'dt_vat' else 'cr_vat' end as oper
from sales.sales_long
)
select 
x.date_from,
x.report_type,
x.field,
x.dt_wb,
x.cr_wb,
x.dt_pl,
x.cr_pl,
x.dt_vat,
x.cr_vat,
m.acc_ws,
m.acc_pl,
m.acc_vat,
m.subconto_ws,
m.subconto_pl,
m.subconto_vat,
m.vat,
m.ns,
uuid() as id,
m.acc_ob
from (
PIVOT a
on oper
using COALESCE(sum(val),0)
group by date_from, report_type, field
) x
left join maping as m on m.field = x.field and m.report_type = x.report_type

order by date_from, field, report_type

"""



def get_psql_data():
    conn = connect_db()

    vat = pd.read_sql(
        """
        SELECT date AS date_from,
               COALESCE(lead(date) OVER (ORDER BY date), '2090-12-31'::date) AS date_to,
               rate
        FROM public.macro_taxrates
        WHERE tax_id = 1;
        """,
        con=conn,
    )
    maping = pd.read_sql("select * from gl.wb_mapping", con=conn)

    conn.close()

    return vat, maping


def update_wb_distribution(conn: DuckDBPyConnection):
    duck = conn
    psql = connect_db()

    # данные из duck
    result = duck.sql(UPDATE_WB_DISTRIBUTION)

    # границы дат
    min_date, max_date = duck.execute(
        f"""
        SELECT min(date_from), max(date_from)
        FROM ({UPDATE_WB_DISTRIBUTION})
    """
    ).fetchone()

    print(min_date, max_date)

    rows = result.fetchall()
    cols = [c[0] for c in result.description]

    # 🔥 подготовим SQL
    columns_sql = ", ".join(cols)
    placeholders = ", ".join(["%s"] * len(cols))

    insert_sql = f"""
        INSERT INTO gl.wb_distibution ({columns_sql})
        VALUES ({placeholders})
    """
    print("ROWS:", len(rows))

    with psql.cursor() as cur:
        # DELETE
        cur.execute(
            """
            DELETE FROM gl.wb_distibution
            WHERE date_from BETWEEN %s AND %s
            """,
            (min_date, max_date),
        )

        # INSERT
        cur.executemany(insert_sql, rows)

    psql.commit()
    psql.close()


def log(
    conn: DuckDBPyConnection,
    fun="handle",
    status=None,
    details=None,
    msg=None,
):
    try:
        conn.execute(
            """
            INSERT INTO duck_logs (command, function, status, details, message)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                "duck_etl",
                fun,
                status,
                json.dumps(details, ensure_ascii=False) if details else None,
                msg,
            ],
        )
    except Exception as e:
        # логгер не должен валить основной процесс
        print(f"[LOG ERROR] {e}")


class Command(BaseCommand):
    help = "Initialize DuckDB views for WB parquet"
    
    def add_arguments(self, parser):
        parser.add_argument(
            "--update",
            action="store_true",
            help="Update wb_distribution"
        )

    def handle(self, *args, **options):
        update_flag = options.get("update", False)
        db_path = os.getenv("DUCKDB_PATH")
        parquet_path = os.getenv("PARQUET_PATH")
        

        if not db_path:
            raise CommandError("DUCKDB_PATH is not set")

        if not parquet_path:
            raise CommandError("PARQUET_PATH is not set")

        self.stdout.write(f"DuckDB: {db_path}")
        self.stdout.write(f"Parquet path: {parquet_path}")

        try:
            with duckdb.connect(db_path) as con:

                con.execute("CREATE SCHEMA IF NOT EXISTS sales;")

                con.execute(
                    f"""
                    CREATE VIEW IF NOT EXISTS sales.realization_raw AS
                    SELECT *
                    FROM read_parquet('{parquet_path}/*.parquet', union_by_name=true);
                """
                )
                
                con.execute(
                    """ 
                    CREATE TABLE IF NOT EXISTS duck_logs (
                        ts TIMESTAMP DEFAULT current_timestamp,

                        command TEXT,
                        function TEXT,
                        status TEXT,

                        details JSON,
                        message TEXT
                    );
                    """
                )

                self.stdout.write(self.style.SUCCESS("VIEW realization_raw created"))

                cnt = con.execute("SELECT COUNT(*) FROM sales.realization_raw").fetchone()[0]

                self.stdout.write(self.style.SUCCESS(f"Rows available: {cnt}"))
                log(con, msg=f"Rows available: {cnt}", status="ok")

                try:
                    new_rows = con.sql(
                        """ 
                        select * from sales.realization_raw
                        where rrd_id not in (
                            select rrd_id from sales.wb_raw
                        )
                        """
                    )
                except:
                    con.execute(RAW_TABLE)
                    
                
                if new_rows:
                   con.register("new_rows", new_rows)  
                   nr = con.sql("SELECT COUNT(*) FROM new_rows").fetchone()[0]
                   insert_new_rows(con) 
                   self.stdout.write(self.style.SUCCESS(f"Rows inserter: {nr}"))
                else:
                   self.stdout.write(self.style.SUCCESS(f"Nothing to insert")) 
                   
                    

                self.stdout.write(
                    self.style.SUCCESS(f"Table wb_raw and products were renewed")
                )

                vat, maping = get_psql_data()

                con.execute("CREATE OR REPLACE TABLE main.vat AS select * from vat")
                con.execute(
                    "CREATE OR REPLACE TABLE main.maping AS select * from maping"
                )
                self.stdout.write(self.style.SUCCESS(f"vat_renew"))

                con.execute(
                    f""" 
                    CREATE OR REPLACE TABLE sales.sales_long AS
                    {SALES_LONG}
                    """
                )
                self.stdout.write(self.style.SUCCESS(f"Table sales_long was renewed"))

                if update_flag:
                    update_wb_distribution(con)
                    self.stdout.write(
                        self.style.SUCCESS("Table wb_distibution was updated")
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING("Skip wb_distribution update")
                    )

        except Exception as e:
            log(con, status="faild", msg=f"DuckDB error: {e}")
            raise CommandError(f"DuckDB error: {e}")
