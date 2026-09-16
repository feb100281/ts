from conns import get_duckdb_conn_with_opt
from django.core.management.base import BaseCommand, CommandError
import os
from dotenv import load_dotenv

load_dotenv()


DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME")

class Command(BaseCommand):
    help = "UPDATE QTY for COSTS"

    def handle(self, *args, **options):
        db_path = os.getenv("DUCKDB_PATH")
        parquet_path = os.getenv("PARQUET_PATH")

        if not db_path:
            raise CommandError("DUCKDB_PATH is not set")

        if not parquet_path:
            raise CommandError("PARQUET_PATH is not set")

        
        self.stdout.write(f"Обновляем кол-во продаж")

        try:
            with get_duckdb_conn_with_opt()  as con:

                                # TRUNCATE - правильное написание, а не "trancate"
                con.execute("TRUNCATE TABLE pg.gl.wb_quant")

                con.execute("""
                    INSERT INTO pg.gl.wb_quant (date_from, sell_quant, return_quant, quant)
                    SELECT 
                        date_from::date as date_from,
                        COUNT(val) FILTER (WHERE oper = 'dt') as sell_quant,
                        COUNT(val) FILTER (WHERE oper = 'cr') as return_quant,
                        COUNT(val) FILTER (WHERE oper = 'dt') - 
                        COUNT(val) FILTER (WHERE oper = 'cr') as quant
                    FROM sales.sales_long
                    WHERE field = 'retail_price'
                    GROUP BY date_from
                """)
                
        except Exception as e:
            raise CommandError(f"DuckDB error: {e}")