"""Балансовые счета для банковских счетов зарубежных компаний, у которых их ещё нет."""
from django.core.management.base import BaseCommand
from django.db import transaction

from corporate.models import BankAccount
from utils.bsparsers.am.loader import ensure_bs_acc

RU_GROUP = "Трендсеттер РФ"


class Command(BaseCommand):
    help = "Заводит балансовые счета для армянских банковских счетов"

    def handle(self, *args, **options):
        qs = (BankAccount.objects.filter(bs_acc__isnull=True).exclude(corporate__report_group=RU_GROUP)
              .select_related("bank").order_by("bank__name", "currency", "account"))
        n = 0
        with transaction.atomic():
            for ba in qs:
                ensure_bs_acc(ba, log=self.stdout.write)
                n += 1
        self.stdout.write(f"Балансовых счетов заведено: {n}")
