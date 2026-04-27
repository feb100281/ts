import os
import duckdb
from duckdb import DuckDBPyConnection

from django.core.management.base import BaseCommand, CommandError

def create_parse_table(conn:DuckDBPyConnection):
    conn.execute(
        """ 
        
        """
    )

class Command(BaseCommand):
    help = "Initialize DuckDB views for WB parquet"

    def handle(self, *args, **options):
        db_path = os.getenv("DUCKDB_PATH")
        parquet_path = os.getenv("PARQUET_PATH")

        if not db_path:
            raise CommandError("DUCKDB_PATH is not set")

        if not parquet_path:
            raise CommandError("PARQUET_PATH is not set")

        self.stdout.write(f"DuckDB: {db_path}")
        self.stdout.write(f"Parquet path: {parquet_path}")

        try:
            con = duckdb.connect(db_path)

            # RAW view
            con.execute(f"""
                CREATE VIEW IF NOT EXISTS realization_raw AS
                SELECT *
                FROM read_parquet('{parquet_path}/*.parquet', union_by_name=true);
            """)

            self.stdout.write(self.style.SUCCESS("VIEW realization_raw created"))

            # тестовый селект
            cnt = con.execute("SELECT COUNT(*) FROM realization_raw").fetchone()[0]

            self.stdout.write(self.style.SUCCESS(f"Rows available: {cnt}"))

        except Exception as e:
            raise CommandError(f"DuckDB error: {e}")

        finally:
            con.close()