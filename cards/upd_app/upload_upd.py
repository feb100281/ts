# upload_upd.py

from django.db import transaction

from .parse_upd import read_file
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


@transaction.atomic
def upload_data(
    upd_id,
    file_bytes,
    filename="upd.parquet",
):

    upd_document = (
        UpdDocument.objects
        .get(pk=upd_id)
    )

    delete_lines(upd_id)

    rows = read_file(
        file_bytes,
        filename,
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
                
                man_cost_per_unit=r.get(
                    "man_cost_per_unit"
                ),
                
       

                currency_code="RUB",
            )
        )

    UPDData.objects.bulk_create(
        objs,
        batch_size=5000,
    )

    return len(objs)