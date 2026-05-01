import os
from pathlib import Path

import duckdb
import pandas as pd
from django.core.management.base import BaseCommand, CommandError

from dotenv import load_dotenv

from inventories.models import Delivery, Lot

load_dotenv()


class Command(BaseCommand):
    help = "Transfers csv package file to parquet"

    def add_arguments(self, parser):
        parser.add_argument("delivery_id", type=int)

    def handle(self, *args, **options):
        delivery_id = options["delivery_id"]

        db_path = os.getenv("DUCKDB_PATH")
        parquet_root = os.getenv("PARQUET_PATH")

        if not db_path:
            raise CommandError("DUCKDB_PATH is not set")

        if not parquet_root:
            raise CommandError("PARQUET_PATH is not set")

        parquet_root = Path(parquet_root)

        # 📁 папка deliveries
        output_dir = parquet_root / "deliveries"
        output_dir.mkdir(parents=True, exist_ok=True)

        try:
            delivery = Delivery.objects.get(id=delivery_id)
        except Delivery.DoesNotExist:
            raise CommandError(f"Delivery {delivery_id} not found")

        csv_path = Path(delivery.file.path)

        if not csv_path.exists():
            raise CommandError(f"CSV not found: {csv_path}")

        # имя файла
        parquet_path = output_dir / f"lot_{delivery.lot_id}_delivery_{delivery_id}.parquet"

        self.stdout.write(f"CSV: {csv_path}")
        self.stdout.write(f"Parquet: {parquet_path}")

        try:
            df = pd.read_csv(csv_path, dtype=str)

            # 🔥 просто добавляем id
            df["delivery_id"] = delivery_id
            # df["lot_id"] = delivery.lot_id

            with duckdb.connect(db_path) as con:
                con.register("df", df)

                con.execute(f"""
                    COPY df TO '{parquet_path.as_posix()}'
                    (FORMAT PARQUET);
                """)
                con.execute("CREATE SCHEMA IF NOT EXISTS deliveries;") 
                
                delivery_df = pd.DataFrame(
                    list(Delivery.objects.all().values())
                )

                lot_df = pd.DataFrame(
                    list(Lot.objects.all().values())
                )

                # =========================
                # в DuckDB
                # =========================
                con.register("delivery_df", delivery_df)
                con.register("lot_df", lot_df)

                con.execute(f"""
                    CREATE VIEW IF NOT EXISTS deliveries.deliveries_raw AS
                    SELECT *
                    FROM read_parquet('{parquet_path}/deliveries/*.parquet', union_by_name=true);
                """)
                
                
                con.execute("""
                    CREATE OR REPLACE TABLE deliveries.delivery AS
                    SELECT * FROM delivery_df;
                """)

                con.execute("""
                    CREATE OR REPLACE TABLE deliveries.lot AS
                    SELECT * FROM lot_df;
                """)
                

        except Exception as e:
            raise CommandError(f"DuckDB error: {e}")

        self.stdout.write(self.style.SUCCESS("OK"))