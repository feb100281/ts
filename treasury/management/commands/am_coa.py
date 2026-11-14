"""Счета и статьи для зарубежных компаний: балансовые счета банковских счетов, розница."""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from corporate.models import COA, BankAccount, CfItems
from utils.bsparsers.am.loader import ensure_bs_acc

RU_GROUP = "Трендсеттер РФ"

# код: (наименование, код родителя)
RETAIL_COA = {
    "199100": ("Товары в рознице (зарубежные компании)", "100000"),
    "799100": ("Расчёты с покупателями в рознице", "700000"),
}
RETAIL_ITEMS = {
    "510190": ("Выручка розница", "510100"),
    "520190": ("Себестоимость розница", "520100"),
}


def ensure(model, code, name, parent_code, log):
    obj = model.objects.filter(code=code).first()
    if obj:
        if obj.name != name:
            raise CommandError(f"код {code} уже занят: {obj}")
        return obj
    parent = model.objects.filter(code=parent_code).first()
    if parent is None:
        raise CommandError(f"нет родителя {parent_code} для {code} {name}")
    obj = model.objects.create(code=code, name=name, parent=parent)
    log(f"  + {model._meta.verbose_name}: {obj}")
    return obj


class Command(BaseCommand):
    help = "Заводит счета и статьи для армянских счетов и розницы"

    def handle(self, *args, **options):
        log = self.stdout.write
        qs = (BankAccount.objects.filter(bs_acc__isnull=True).exclude(corporate__report_group=RU_GROUP)
              .select_related("bank").order_by("bank__name", "currency", "account"))
        n = 0
        with transaction.atomic():
            for ba in qs:
                ensure_bs_acc(ba, log=log)
                n += 1
            for code, (name, parent) in RETAIL_COA.items():
                ensure(COA, code, name, parent, log)
            for code, (name, parent) in RETAIL_ITEMS.items():
                ensure(CfItems, code, name, parent, log)
        log(f"Балансовых счетов заведено: {n}")
