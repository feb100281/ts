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

from cards.models import WbProduct, UPDData, USK, UskUpd

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
CREATE or replace table inventories.stock_key as
with upd as (
    select
        upd_sa_name,
        trim(left(upd_sa_name, 10)) as prefix
    from inventories.upd_income
),

matched as (
    select
        t.upd_sa_name,
        list(distinct p.sa_name order by p.sa_name) as sa_names
    from upd t
    left join inventories.wb_product p
        on starts_with(p.sa_name, t.prefix)
    group by t.upd_sa_name
)

select
    upd_sa_name,
    sa_names,
    sa_names[1] as stock_key
from matched;

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
                
                self.stdout.write(
                    self.style.SUCCESS("USK обновлены для всех приходов по УПД")                    
                )                  
        
        
        except Exception as e:
            raise CommandError(f"DuckDB error: {e}")
        
        
        
        
        