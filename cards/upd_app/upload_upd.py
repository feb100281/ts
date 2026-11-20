# upload_upd.py

from django.db import transaction

from .parse_upd import read_file
from cards.models import (
    UPDData,
    UpdDocument,
)


def _key(sa, size):
    return ((sa or "").strip().upper(), (size or "").strip().upper())


def _old_marks(upd_id):
    """Ручная разметка прежних строк: карточка, размер, упр. себестоимость, канал — по артикулу и размеру."""
    marks = {}
    for r in (UPDData.objects.filter(upd_document_id=upd_id)
              .values("upd_sa_name", "upd_size", "nm_id", "chrt_id", "man_cost_per_unit", "channel")):
        m = marks.setdefault(_key(r["upd_sa_name"], r["upd_size"]), {})
        for f in ("nm_id", "chrt_id", "man_cost_per_unit", "channel"):
            if m.get(f) is None and r[f] is not None:
                m[f] = r[f]
    return marks


@transaction.atomic
def upload_data(
    upd_id,
    file_bytes,
    filename="upd.parquet",
):
    """Перезагрузка строк УПД с сохранением разметки (nm_id, chrt_id, себестоимость) по артикулу и размеру."""
    upd_document = UpdDocument.objects.get(pk=upd_id)
    rows = read_file(file_bytes, filename)
    marks = _old_marks(upd_id)

    UPDData.objects.filter(upd_document_id=upd_id).delete()

    objs = []
    for i, r in enumerate(rows, start=1):
        old = marks.get(_key(r.get("upd_sa_name"), r.get("upd_size")), {})
        objs.append(UPDData(
            upd_document=upd_document,
            upd_pos=i,
            brand=r.get("brand"),
            upd_sa_name=r.get("upd_sa_name"),
            upd_title=r.get("upd_title"),
            upd_size=r.get("upd_size"),
            upd_unit=r.get("upd_unit") or r.get("upd_units"),
            upd_qty=r.get("upd_qty"),
            upd_price_vatless=r.get("upd_price_vatless"),
            upd_amount_vatless=r.get("upd_amount_vatless"),
            upd_vat_rate=r.get("upd_vat_rate"),
            upd_vat_amount=r.get("upd_vat_amount"),
            upd_amount_vatadd=r.get("upd_amount_vatadd"),
            man_cost_per_unit=r.get("man_cost_per_unit") if r.get("man_cost_per_unit") is not None
            else old.get("man_cost_per_unit"),
            currency_code="RUB",
            nm_id=old.get("nm_id"),
            chrt_id=old.get("chrt_id"),
            channel=r["channel"] if "channel" in r else old.get("channel"),
            shipped=r.get("shipped"),
        ))

    UPDData.objects.bulk_create(objs, batch_size=5000)
    return len(objs)


@transaction.atomic
def update_channels(upd_id, file_bytes, filename):
    """Только каналы и отгрузка из «Рабочего щита»; строки, карточки и размеры не трогаются."""
    rows = read_file(file_bytes, filename)
    if not any("channel" in r for r in rows):
        raise ValueError("В файле нет листа «Рабочий щит» с колонкой «Канал продаж»")
    lines = {l.upd_pos: l for l in UPDData.objects.filter(upd_document_id=upd_id)}
    changed, missed = [], 0
    for i, r in enumerate(rows, start=1):
        l = lines.get(i)
        if l is None or _key(l.upd_sa_name, l.upd_size) != _key(r.get("upd_sa_name"), r.get("upd_size")):
            missed += 1
            continue
        if (l.channel, l.shipped) != (r.get("channel"), r.get("shipped")):
            l.channel, l.shipped = r.get("channel"), r.get("shipped")
            changed.append(l)
    UPDData.objects.bulk_update(changed, ["channel", "shipped"], batch_size=5000)
    return len(changed), missed
