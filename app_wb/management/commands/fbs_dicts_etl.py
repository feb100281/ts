from __future__ import annotations

import os
from pathlib import Path

import duckdb

from django.core.management.base import (
    BaseCommand,
    CommandError,
)

from dotenv import load_dotenv


load_dotenv()


# ============================================================
# СПРАВОЧНИКИ СКЛАДОВ FBS
#
# Parquet кладёт utils/load_fbs_orders.py, шаг 11:
#
#   fbs_warehouses.parquet — наши склады отправления
#   fbs_offices.parquet    — склады WB, куда отгружаем
#
# Здесь они превращаются в таблицы DuckDB. Без них дашборд
# показывает номера складов вместо названий, но работает.
# ============================================================

FBS_WAREHOUSES = """
CREATE OR REPLACE TABLE
orders.fbs_warehouses AS

SELECT

    warehouse_id::BIGINT AS warehouse_id,

    warehouse_name,

    office_id::BIGINT AS office_id,

    cargo_type::INTEGER AS cargo_type,

    cargo_type_name,

    delivery_type::INTEGER AS delivery_type,

    delivery_type_name,

    loaded_at::TIMESTAMPTZ AS loaded_at

FROM read_parquet('{path}')
"""


FBS_OFFICES = """
CREATE OR REPLACE TABLE
orders.fbs_offices AS

SELECT

    office_id::BIGINT AS office_id,

    office_name,

    address,

    city,

    cargo_type::INTEGER AS cargo_type,

    cargo_type_name,

    delivery_type::INTEGER AS delivery_type,

    delivery_type_name,

    loaded_at::TIMESTAMPTZ AS loaded_at

FROM read_parquet('{path}')
"""


class Command(BaseCommand):

    help = (
        "Загружает справочники складов FBS "
        "(orders.fbs_warehouses, orders.fbs_offices) "
        "из parquet в DuckDB"
    )


    def handle(self, *args, **options):

        # ====================================================
        # ENV
        # ====================================================

        db_path = os.getenv(
            "DUCKDB_PATH"
        )

        parquet_path = os.getenv(
            "PARQUET_PATH"
        )


        if not db_path:

            raise CommandError(
                "DUCKDB_PATH is not set"
            )


        if not parquet_path:

            raise CommandError(
                "PARQUET_PATH is not set"
            )


        # ====================================================
        # ФАЙЛЫ
        # ====================================================

        fbs_dir = (
            Path(parquet_path)
            / "fbs_orders"
        )


        warehouses_file = (
            fbs_dir
            / "fbs_warehouses.parquet"
        )


        offices_file = (
            fbs_dir
            / "fbs_offices.parquet"
        )


        missing = [
            str(path)
            for path in (
                warehouses_file,
                offices_file,
            )
            if not path.exists()
        ]


        if missing:

            raise CommandError(
                "Не найдены справочники: "
                + ", ".join(missing)
                + ". Сначала запустите "
                "python utils/load_fbs_orders.py — "
                "он их скачивает на шаге 11."
            )


        self.stdout.write(
            f"DuckDB: {db_path}"
        )

        self.stdout.write(
            f"Справочники: {fbs_dir}"
        )


        # ====================================================
        # DUCKDB
        # ====================================================

        try:

            with duckdb.connect(
                db_path
            ) as con:

                con.execute("""
                    CREATE SCHEMA
                    IF NOT EXISTS orders;
                """)


                con.execute(
                    FBS_WAREHOUSES.format(
                        path=warehouses_file
                    )
                )


                con.execute(
                    FBS_OFFICES.format(
                        path=offices_file
                    )
                )


                # ============================================
                # ДИАГНОСТИКА
                # ============================================

                warehouses_rows = con.execute("""
                    SELECT COUNT(*)
                    FROM orders.fbs_warehouses
                """).fetchone()[0]


                offices_rows = con.execute("""
                    SELECT COUNT(*)
                    FROM orders.fbs_offices
                """).fetchone()[0]


                # Сколько складов и пунктов из заказов
                # реально получится назвать по имени.
                coverage = None

                try:

                    coverage = con.execute("""
                        SELECT
                            COUNT(DISTINCT o.warehouse_id),

                            COUNT(
                                DISTINCT o.warehouse_id
                            ) FILTER (
                                WHERE w.warehouse_id IS NOT NULL
                            ),

                            COUNT(DISTINCT o.destination_office_id),

                            COUNT(
                                DISTINCT o.destination_office_id
                            ) FILTER (
                                WHERE f.office_id IS NOT NULL
                            )

                        FROM orders.unpacked_fbs_orders o

                        LEFT JOIN orders.fbs_warehouses w
                            ON w.warehouse_id = o.warehouse_id

                        LEFT JOIN orders.fbs_offices f
                            ON f.office_id = o.destination_office_id
                    """).fetchone()

                except duckdb.Error:

                    # Заказы ещё не залиты — не повод падать.
                    coverage = None


        except duckdb.Error as e:

            raise CommandError(
                f"DuckDB error: {e}"
            )


        # ====================================================
        # ИТОГ
        # ====================================================

        report = [
            "",
            "СПРАВОЧНИКИ FBS ЗАГРУЖЕНЫ",
            "-" * 44,
            f"orders.fbs_warehouses: {warehouses_rows:,}",
            f"orders.fbs_offices:    {offices_rows:,}",
        ]


        if coverage:

            (
                warehouses_total,
                warehouses_named,
                offices_total,
                offices_named,
            ) = coverage

            report += [
                "",
                "ПОКРЫТИЕ ЗАКАЗОВ",
                "-" * 44,
                f"Складов отправления: {warehouses_total:,}, "
                f"с названием: {warehouses_named:,}",
                f"Пунктов назначения:  {offices_total:,}, "
                f"с названием: {offices_named:,}",
            ]

            if warehouses_total > warehouses_named:

                report.append(
                    "Склады без названия — удалённые "
                    "или чужие, WB их в справочнике "
                    "уже не отдаёт"
                )


        report.append("-" * 44)


        self.stdout.write(
            self.style.SUCCESS(
                "\n".join(report)
            )
        )
