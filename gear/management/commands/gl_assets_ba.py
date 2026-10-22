from django.core.management.base import BaseCommand, CommandError
from django.db import models
from django.db import transaction
from django.db import connection

from conns import get_duckdb_conn_with_opt

import pandas as pd

from treasury.models import CfData

# Queries

NORMALIZED_STATEMENTS = """
SELECT
    row_number() OVER (ORDER BY x.date_from) AS id,
    x.date_from::date as date_from,
    x.acc_id::bigint as acc_id,
    x.currency::text as currency,
    x.company_id::bigint as company_id,
	x.contract_id::bigint as contract_id,
    x.subconto_id::bigint as subconto_id,
    x.fx_rate::double as fx_rate,
    x.base_dt::bigint as base_dt,
    x.base_cr::bigint as base_cr,
    ROUND(x.base_dt * x.fx_rate, 0)::bigint AS dt,
    ROUND(x.base_cr * x.fx_rate, 0)::bigint AS cr,
    x.description::text as description
    FROM (
        SELECT
            t.date AS date_from,
            b.bs_acc_id AS acc_id,
            b.currency,
            t.contract_id,
            b.corporate_id AS company_id,
            t.cfitem_id AS subconto_id,
            CASE
                WHEN b.currency = 'RUB' THEN 1
                ELSE fx.rate
            END AS fx_rate,
            ROUND(t.dt * 100, 0)::bigint AS base_dt,
            ROUND(t.cr * 100, 0)::bigint AS base_cr,
            t.temp AS description
        FROM gl_assets_ba.statements t
        JOIN gl_refs.bank_accounts b
        ON t.ba_id = b.id
        LEFT JOIN LATERAL (
            SELECT r.rate
            FROM gl_refs.fx_rates r
            WHERE r.date = t.date
            AND r.currency = b.currency
            ORDER BY r.date
            LIMIT 1
        ) fx ON TRUE
    ) x;
"""

V_BANK_ACCOUNT = """ 
SELECT ba_id::bigint as ba_id,
    acc_id::bigint as acc_id,
    currency::text as currency,
    is_active::bool as is_active,
    min_date::date as min_date,
        CASE
            WHEN is_active IS TRUE THEN CURRENT_DATE
            ELSE max_date::date
        END AS max_date
   FROM ( SELECT a.id AS ba_id,
            a.bs_acc_id AS acc_id,
            a.currency,
            a.is_active,
            min(t.date) AS min_date,
            max(t.date) AS max_date
           FROM gl_refs.bank_accounts a
             JOIN gl_assets_ba.statements t ON t.ba_id = a.id
          GROUP BY a.id, a.bs_acc_id, a.currency, a.is_active) x;
"""


def cash_revaluation(acc_id):
    
    query = """ 
    INSERT INTO gl_assets_ba.cash_revaluation (
    acc_id,
    date_from,
    currency,
    rate_previous,
    fx_rate,
    fx_diff,
    base_bb,
    base_eb,
    bb,
    eb,
    fx_gains_loss
    )
    WITH ballances AS (
    SELECT
        x.acc_id,
        x.date_from::date AS date_from,
        COALESCE(
            LEAD(x.date_from) OVER (
                PARTITION BY x.acc_id
                ORDER BY x.date_from
            ),
            a.max_date + 1
        ) AS date_to,
        SUM(x.turnover) OVER (
            PARTITION BY x.acc_id
            ORDER BY x.date_from
        ) AS eb
    FROM (
        SELECT
            acc_id,
            date_from::date AS date_from,
            SUM(base_dt - base_cr) AS turnover
        FROM gl_assets_ba.normalize
        WHERE acc_id = ?
        GROUP BY acc_id, date_from
        UNION ALL
        SELECT
            acc_id,
            date::date AS date_from,
            ROUND(SUM(dt - cr) * 100, 0)::BIGINT AS turnover
        FROM gl_refs.manual
        WHERE acc_id = ?
        GROUP BY acc_id, date_from
    ) x
    JOIN gl_assets_ba.v_bank_account a
        ON a.acc_id = x.acc_id
)
SELECT
    t.acc_id,
    t.date_from::date AS date_from,
    t.currency,
    t.rate_previous,
    t.fx_rate,
    t.fx_diff,
    t.base_bb,
    t.base_eb,
    ROUND(t.base_bb * t.fx_rate, 0)::BIGINT AS bb,
    ROUND(t.base_eb * t.fx_rate, 0)::BIGINT AS eb,
    ROUND(t.base_bb * t.fx_diff, 0)::BIGINT AS fx_gains_loss
FROM (
    SELECT
        x.acc_id,
        x.d::date AS date_from,   -- теперь x.d уже DATE, можно убрать ::date
        x.currency,
        CASE
            WHEN x.currency = 'RUB' THEN 1
            ELSE COALESCE(LAG(fx.rate) OVER (ORDER BY x.d), 0)
        END AS rate_previous,
        CASE
            WHEN x.currency = 'RUB' THEN 1
            ELSE fx.rate
        END AS fx_rate,
        CASE
            WHEN x.currency = 'RUB' THEN 0
            ELSE fx.rate - COALESCE(LAG(fx.rate) OVER (ORDER BY x.d), 0)
        END AS fx_diff,
        COALESCE(LAG(b.eb) OVER (ORDER BY x.d), 0) AS base_bb,
        b.eb AS base_eb
    FROM (
        -- ИСПРАВЛЕННЫЙ ПОДЗАПРОС
        SELECT
            a.acc_id,
            a.currency,
            g.series::DATE AS d
        FROM gl_assets_ba.v_bank_account a,
        LATERAL generate_series(a.min_date, a.max_date, INTERVAL '1 day') AS g(series)
        WHERE a.acc_id = ?
    ) x
    LEFT JOIN gl_refs.fx_rates fx
        ON fx.currency = x.currency
        AND fx.date = x.d
        AND x.currency <> 'RUB'
    LEFT JOIN ballances b
        ON x.d >= b.date_from AND x.d < b.date_to
) t   
ON CONFLICT (acc_id, date_from) DO UPDATE
SET
    currency       = EXCLUDED.currency,
    rate_previous  = EXCLUDED.rate_previous,
    fx_rate        = EXCLUDED.fx_rate,
    fx_diff        = EXCLUDED.fx_diff,
    base_bb        = EXCLUDED.base_bb,
    base_eb        = EXCLUDED.base_eb,
    bb             = EXCLUDED.bb,
    eb             = EXCLUDED.eb,
    fx_gains_loss  = EXCLUDED.fx_gains_loss
WHERE
    (gl_assets_ba.cash_revaluation.currency,
     gl_assets_ba.cash_revaluation.rate_previous,
     gl_assets_ba.cash_revaluation.fx_rate,
     gl_assets_ba.cash_revaluation.fx_diff,
     gl_assets_ba.cash_revaluation.base_bb,
     gl_assets_ba.cash_revaluation.base_eb,
     gl_assets_ba.cash_revaluation.bb,
     gl_assets_ba.cash_revaluation.eb,
     gl_assets_ba.cash_revaluation.fx_gains_loss)
IS DISTINCT FROM
    (EXCLUDED.currency,
     EXCLUDED.rate_previous,
     EXCLUDED.fx_rate,
     EXCLUDED.fx_diff,
     EXCLUDED.base_bb,
     EXCLUDED.base_eb,
     EXCLUDED.bb,
     EXCLUDED.eb,
     EXCLUDED.fx_gains_loss);
    """
    with get_duckdb_conn_with_opt() as con:
        con.execute(
            query,parameters=[acc_id,acc_id,acc_id]
        )

class Command(BaseCommand):
    help = "Эта комманда распределяет GL по банковским счетам"    
    
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
        
        try:
            with get_duckdb_conn_with_opt() as con:                
                               
                statement_df = self._prepare_df(
                    CfData.objects.all(),
                    CfData
                )                
                               
                con.execute("""
                    CREATE SCHEMA IF NOT EXISTS gl_assets_ba
                """)
                
                
                self.stdout.write(
                    self.style.NOTICE("Обновляем Bank Accounts (gl_asset_ba)")
                )

                con.execute("""
                    CREATE OR REPLACE TABLE gl_assets_ba.statements
                    AS SELECT * FROM statement_df
                """)
                
                self.stdout.write(
                    self.style.SUCCESS("Загружены банковские выписки в gl_assets_ba.statements")                    
                )
                
                con.execute(f"""
                    CREATE OR REPLACE TABLE gl_assets_ba.normalize
                    AS {NORMALIZED_STATEMENTS}
                """)
                
                self.stdout.write(
                    self.style.SUCCESS("Нормализация выписок gl_assets_ba.normalize")                    
                )
                
                con.execute(f"""
                    CREATE OR REPLACE VIEW gl_assets_ba.v_bank_account
                    AS {V_BANK_ACCOUNT}
                """)
                
                self.stdout.write(
                    self.style.SUCCESS("View  gl_assets_ba.v_bank_account обновлен")                    
                )
                
                con.execute(
                    "DROP TABLE IF EXISTS gl_assets_ba.cash_revaluation;"
                )
                
                con.execute(
                    """ 
                    CREATE TABLE IF NOT EXISTS gl_assets_ba.cash_revaluation
                    (
                        acc_id bigint NOT NULL,
                        date_from date NOT NULL,
                        currency text NOT NULL,
                        rate_previous numeric NOT NULL,
                        fx_rate numeric NOT NULL,
                        fx_diff numeric NOT NULL,
                        base_bb bigint NOT NULL,
                        base_eb bigint NOT NULL,
                        bb bigint NOT NULL,
                        eb bigint NOT NULL,
                        fx_gains_loss bigint NOT NULL,
                        CONSTRAINT uq_cash_revaluation_acc_date UNIQUE (acc_id, date_from)
                    )
                    """
                )
                
                self.stdout.write(
                    self.style.SUCCESS("Создана таблица gl_assets_ba.cash_revaluation")                    
                )
                
                rows = con.execute("SELECT DISTINCT acc_id FROM gl_assets_ba.v_bank_account").fetchall()
                acc_ids = [row[0] for row in rows]
                print(acc_ids)
                
                self.stdout.write(
                    self.style.NOTICE("Выполняем пересчет курсовых разниц")                    
                )
                for acc in acc_ids:                
                    cash_revaluation(acc)
                    self.stdout.write(
                    self.style.SUCCESS(f"Id_счета {acc} - выполнен")                    
                )                   
                
                
                
                      
                
        except Exception as e:
            raise CommandError(f"DuckDB error: {e}")