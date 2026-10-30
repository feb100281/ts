from django.core.management.base import BaseCommand, CommandError
from django.db import models
from django.db import transaction
from django.db import connection

from conns import get_duckdb_conn_with_opt

import pandas as pd

from contracts.models import Contracts
from corporate.models import COA, CfItems, BankAccount
from macro.models import CurrencyRate
from grossbook.models import Manual

class Command(BaseCommand):
    help = "Эта комманда загружает базовые справочники из psql в утку"    
    
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
                               
                contract_df = self._prepare_df(
                    Contracts.objects.all(),
                    Contracts
                )
                
                coa_df = self._prepare_df(
                    COA.objects.all(),
                    COA
                )
                
                cfitem_df = self._prepare_df(
                    CfItems.objects.all(),
                    CfItems
                )
                
                fx_rate_df = self._prepare_df(
                    CurrencyRate.objects.all(),
                    CurrencyRate
                ) 
                
                bankaccount_df = self._prepare_df(
                    BankAccount.objects.all(),
                    BankAccount
                ) 
                
                manual_df = self._prepare_df(
                    Manual.objects.all(),
                    Manual
                ) 
                
                con.execute("""
                    CREATE SCHEMA IF NOT EXISTS gl_refs
                """)
                
                
                self.stdout.write(
                    self.style.NOTICE("Обновляем справочники из моделей")
                )

                con.execute("""
                    CREATE OR REPLACE TABLE gl_refs.contracts
                    AS SELECT * FROM contract_df
                """)
                
                self.stdout.write(
                    self.style.SUCCESS("Договора обновлены")                    
                )

                con.execute("""
                    CREATE OR REPLACE TABLE gl_refs.coa
                    AS SELECT * FROM coa_df
                """)
                
                self.stdout.write(
                    self.style.SUCCESS("План счетов обновлен")                    
                )
                
                con.execute("""
                    CREATE OR REPLACE TABLE gl_refs.cfitems
                    AS SELECT * FROM cfitem_df
                """)
                
                self.stdout.write(
                    self.style.SUCCESS("Статьи обновлены")                    
                )
                
                con.execute("""
                    CREATE OR REPLACE TABLE gl_refs.fx_rates
                    AS SELECT * FROM fx_rate_df
                """)
                
                self.stdout.write(
                    self.style.SUCCESS("Курсы валют обновлены")                    
                )
                
                con.execute("""
                    CREATE OR REPLACE TABLE gl_refs.bank_accounts
                    AS SELECT * FROM bankaccount_df
                """)
                
                self.stdout.write(
                    self.style.SUCCESS("Банковкие счета обновлены")                    
                ) 
                
                con.execute("""
                    CREATE OR REPLACE TABLE gl_refs.manual
                    AS SELECT * FROM manual_df
                """)
                
                self.stdout.write(
                    self.style.SUCCESS("Ручные проводки обновлены")                    
                )              
                
        except Exception as e:
            raise CommandError(f"DuckDB error: {e}")
        
