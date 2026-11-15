"""Сотрудники зарубежной компании: контрагент, счёт и договор на каждого получателя зарплаты из выписок."""
import re
from collections import Counter, defaultdict

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from contracts.models import CfItemAuto, Contracts
from corporate.models import BankAccount
from counterparties.models import Counterparty
from treasury.models import CfData, CounterpartyAccount
from utils.bsparsers.am.loader import auto_assign

SALARY = re.compile(r"աշխատավարձ|արձակուրդ|պարգև", re.I)


def _name(names: Counter) -> str:
    n = names.most_common(1)[0][0] if names else ""
    return " ".join(w.capitalize() for w in n.split())


class Command(BaseCommand):
    help = "Создаёт контрагента, счёт и договор (копию шаблона) на каждого получателя зарплаты; без --apply только список"

    def add_arguments(self, p):
        p.add_argument("--template", type=int, required=True, help="id договора-образца с зарплатными настройками")
        p.add_argument("--apply", action="store_true", help="записать в базу")

    def handle(self, template, apply, **_):
        try:
            tpl = Contracts.objects.select_related("owner").get(pk=template)
        except Contracts.DoesNotExist:
            raise CommandError(f"договор {template} не найден")
        owner = tpl.owner
        if (owner.country or "RU") == "RU":
            raise CommandError("шаблон должен принадлежать зарубежной компании")

        known = set(CounterpartyAccount.objects.values_list("account", flat=True))
        ours = set(BankAccount.objects.values_list("account", flat=True))
        rows = (CfData.objects.filter(owner=owner, cr__gt=0)
                .values_list("id", "reciver_account", "temp", "cp_name_ru", "cp_bs_name"))

        people = defaultdict(lambda: {"ids": [], "names": Counter(), "sum": 0})
        for pk, acc, temp, name_ru, name in rows:
            if not acc or acc in known or acc in ours or not SALARY.search(temp or ""):
                continue
            p = people[acc]
            p["ids"].append(pk)
            p["names"][(name_ru or name or acc).strip()] += 1

        if not people:
            self.stdout.write("Новых получателей зарплаты нет.")
            return

        autos = list(CfItemAuto.objects.filter(contract=tpl))
        self.stdout.write(f"Компания: {owner}; шаблон: {tpl} ({len(autos)} правил статей)")
        for acc, p in sorted(people.items(), key=lambda x: _name(x[1]["names"])):
            self.stdout.write(f"  {_name(p['names'])} | {acc} | операций {len(p['ids'])}")
        if not apply:
            self.stdout.write("Проверка без записи. Для создания добавьте --apply.")
            return

        made = 0
        ids = []
        with transaction.atomic():
            for acc, p in people.items():
                cp, _ = Counterparty.objects.get_or_create(
                    tax_id=f"AM-{acc}", defaults={"name": _name(p["names"]), "country": "AM"})
                CounterpartyAccount.objects.get_or_create(account=acc, defaults={"cp": cp, "comment": "зарплата"})
                if not Contracts.objects.filter(owner=owner, cp=cp).exists():
                    c = Contracts.objects.get(pk=tpl.pk)
                    c.pk = c.id = None
                    c.cp = cp
                    c.regex = None                       # договор единственный у контрагента — подбор по счёту
                    c.save()
                    CfItemAuto.objects.bulk_create([CfItemAuto(contract=c, regex=a.regex,
                                                               defaultcfdt=a.defaultcfdt,
                                                               defaultcfcr=a.defaultcfcr) for a in autos])
                    made += 1
                ids += p["ids"]
            lines = []
            auto_assign(ids, owner.id, lines.append)
        self.stdout.write(f"Сотрудников: {len(people)}, новых договоров: {made}, операций разнесено заново: {len(ids)}")
        for x in lines:
            self.stdout.write(x)
