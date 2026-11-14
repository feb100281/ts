"""Загрузка продаж и возвратов из 1С (Армения) в sales.RetailSale. Месяц из файла заменяется целиком."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from django.db import transaction
from django.utils import timezone

from corporate.models import Owners
from sales.models import RetailSale

from .sales import SalesError, is_sales_file, parse_sales  # noqa: F401  (is_sales_file — для вызывающих)


def _owner(owner: Owners | None) -> Owners:
    if owner is not None:
        return owner
    qs = list(Owners.objects.filter(country="AM"))
    if len(qs) != 1:
        raise SalesError("не определить компанию: компаний с страной AM — %d, укажите явно" % len(qs))
    return qs[0]


def _aware(dt):
    return timezone.make_aware(dt) if dt is not None and timezone.is_naive(dt) else dt


def load_sales(path, owner: Owners | None = None, log=print) -> dict:
    path = Path(path)
    f = parse_sales(path)
    owner = _owner(owner)
    months = sorted(f.months())
    if not months:
        raise SalesError("в файле нет строк")
    objs = [RetailSale(
        owner=owner, kind=r.kind, period=date(r.doc_date.year, r.doc_date.month, 1),
        doc_number=r.doc_number, doc_date=_aware(r.doc_date), check_number=r.check_number,
        check_date=_aware(r.check_date), article_invoice=r.article_invoice, article=r.article, size=r.size,
        barcode=r.barcode, name=r.name[:500], qty=r.qty, price=r.price, amount=r.amount,
        amount_novat=r.amount_novat, cost_unit=r.cost_unit, cost_total=r.cost_total,
        disc_manual_pct=r.disc_manual_pct, disc_manual_sum=r.disc_manual_sum, disc_auto_pct=r.disc_auto_pct,
        disc_auto_sum=r.disc_auto_sum, bonus_sum=r.bonus_sum, row_key=r.key, source_file=path.name[:255],
    ) for r in f.rows]
    with transaction.atomic():
        removed, _ = RetailSale.objects.filter(owner=owner, period__in=months).delete()
        RetailSale.objects.bulk_create(objs, batch_size=1000)
    for m in months:
        s = [o for o in objs if o.period == m]
        sale = sum(o.amount_novat for o in s if o.kind == "sale")
        ret = sum(o.amount_novat for o in s if o.kind == "return")
        cost = sum(o.cost_total for o in s if o.kind == "sale") - sum(o.cost_total for o in s if o.kind == "return")
        log(f"{owner.name} {m:%m.%Y}: продажи без НДС {sale:,.2f}, возвраты {ret:,.2f}, "
            f"нетто {sale - ret:,.2f}, себестоимость {cost:,.2f}, строк {len(s)}")
    log(f"  заменено строк: {removed} → {len(objs)}")
    return {"owner_id": owner.id, "rows": len(objs), "removed": removed, "months": months}
