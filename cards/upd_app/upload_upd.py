# upload_upd.py

from tempfile import NamedTemporaryFile

import duckdb

from django.db import transaction

from cards.models import (
    UPDData,
    UpdDocument,
)


def delete_lines(upd_id):
    """
    Удаляем старые строки УПД.
    """
    return (
        UPDData.objects
        .filter(upd_document_id=upd_id)
        .delete()
    )


def read_parquet(file_bytes):
    """
    Читаем parquet через DuckDB.
    """

    with NamedTemporaryFile(
        suffix=".parquet"
    ) as tmp:

        tmp.write(file_bytes)
        tmp.flush()

        with duckdb.connect() as con:

            rows = con.execute("""
                SELECT *
                FROM read_parquet(?)
            """, [tmp.name]).fetchall()

            columns = [
                x[0]
                for x in con.description
            ]

    return [
        dict(zip(columns, row))
        for row in rows
    ]


@transaction.atomic
def upload_data(
    upd_id,
    parquet_bytes,
):

    upd_document = (
        UpdDocument.objects
        .get(pk=upd_id)
    )

    delete_lines(upd_id)

    rows = read_parquet(
        parquet_bytes
    )

    objs = []

    for i, r in enumerate(rows, start=1):

        objs.append(
            UPDData(
                upd_document=upd_document,

                upd_pos=i,

                brand=r.get(
                    "brand"
                ),

                upd_sa_name=r.get(
                    "upd_sa_name"
                ),

                upd_title=r.get(
                    "upd_title"
                ),

                upd_size=r.get(
                    "upd_size"
                ),

                upd_unit=r.get(
                    "upd_unit"
                ) or r.get(
                    "upd_units"
                ),

                upd_qty=r.get(
                    "upd_qty"
                ),

                upd_price_vatless=r.get(
                    "upd_price_vatless"
                ),

                upd_amount_vatless=r.get(
                    "upd_amount_vatless"
                ),

                upd_vat_rate=r.get(
                    "upd_vat_rate"
                ),

                upd_vat_amount=r.get(
                    "upd_vat_amount"
                ),

                upd_amount_vatadd=r.get(
                    "upd_amount_vatadd"
                ),

                currency_code="RUB",
            )
        )

    UPDData.objects.bulk_create(
        objs,
        batch_size=5000,
    )

    return len(objs)