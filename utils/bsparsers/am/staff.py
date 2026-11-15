"""Сотрудники зарубежной компании: контрагент, счёт и договор на каждого получателя зарплаты из выписок."""
import re
from collections import Counter, defaultdict

from django.db import transaction

from contracts.models import CfItemAuto, Contracts
from corporate.models import BankAccount
from counterparties.models import Counterparty
from treasury.models import CfData, CounterpartyAccount

SALARY = re.compile(r"աշխատավարձ|արձակուրդ|պարգև", re.I)


def _name(names: Counter) -> str:
    n = names.most_common(1)[0][0] if names else ""
    return " ".join(n.upper().split())


def staff_template(owner_id: int):
    """Образец — последний трудовой договор компании."""
    return (Contracts.objects.filter(owner_id=owner_id, title__title__icontains="трудов")
            .select_related("owner").order_by("-id").first())


def find_staff(owner_id: int) -> dict:
    """Получатели зарплаты, чьи счета ещё не привязаны к контрагентам: {счёт: {ids, names}}."""
    known = set(CounterpartyAccount.objects.values_list("account", flat=True))
    ours = set(BankAccount.objects.values_list("account", flat=True))
    rows = (CfData.objects.filter(owner_id=owner_id, cr__gt=0)
            .values_list("id", "reciver_account", "temp", "cp_name_ru", "cp_bs_name"))
    people = defaultdict(lambda: {"ids": [], "names": Counter()})
    for pk, acc, temp, name_ru, name in rows:
        if not acc or acc in known or acc in ours or not SALARY.search(temp or ""):
            continue
        people[acc]["ids"].append(pk)
        people[acc]["names"][(name_ru or name or acc).strip()] += 1
    return dict(people)


def create_staff(tpl: Contracts, people: dict, log=print) -> int:
    """Контрагент, счёт и копия договора-образца на каждого; затем авторазноска их операций."""
    from utils.bsparsers.am.loader import auto_assign

    owner = tpl.owner
    autos = list(CfItemAuto.objects.filter(contract=tpl))
    made, ids = 0, []
    with transaction.atomic():
        for acc, p in people.items():
            cp, _ = Counterparty.objects.get_or_create(
                tax_id=f"AM-{acc}", defaults={"name": _name(p["names"]), "country": "AM"})
            CounterpartyAccount.objects.get_or_create(account=acc, defaults={"cp": cp, "comment": "зарплата"})
            if not Contracts.objects.filter(owner=owner, cp=cp).exists():
                c = Contracts.objects.get(pk=tpl.pk)
                c.pk = c.id = None
                c.cp = cp
                c.regex = None                           # договор единственный у контрагента — подбор по счёту
                c.save()
                CfItemAuto.objects.bulk_create([CfItemAuto(contract=c, regex=a.regex,
                                                           defaultcfdt=a.defaultcfdt,
                                                           defaultcfcr=a.defaultcfcr) for a in autos])
                made += 1
                log(f"  новый сотрудник: {cp.name} | {acc}")
            ids += p["ids"]
        auto_assign(ids, owner.id, lambda *_: None)
    return made


def auto_staff(owner_id: int, log=print) -> int:
    """После загрузки выписки: новые получатели зарплаты — по последнему трудовому договору компании."""
    people = find_staff(owner_id)
    if not people:
        return 0
    tpl = staff_template(owner_id)
    if tpl is None:
        log(f"  получателей зарплаты без договора: {len(people)} — нет трудового договора-образца")
        return 0
    return create_staff(tpl, people, log)
