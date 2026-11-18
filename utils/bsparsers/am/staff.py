"""Сотрудники зарубежной компании: контрагент, счёт и договор на каждого получателя зарплаты из выписок."""
import re
from collections import Counter, defaultdict

from django.db import transaction

from contracts.models import CfItemAuto, Contracts
from corporate.models import BankAccount
from counterparties.models import Counterparty
from treasury.models import CfData, CounterpartyAccount

SALARY = re.compile(r"աշխատավարձ|արձակուրդ|պարգև|վերահաշվարկ", re.I)


def _name(names: Counter) -> str:
    n = names.most_common(1)[0][0] if names else ""
    return " ".join(n.upper().split())


def _tokens(name: str) -> list[str]:
    return [w for w in re.findall(r"[A-ZА-ЯЁ]+", (name or "").upper()) if w not in ("ИП", "ООО")][:2]


def same_person(a: str, b: str) -> bool:
    """Фамилия и имя совпадают по первым 4 буквам, в любом порядке (МОЛЕВАН ЮЛИЯ = МОЛЕВА ЮЛИЯ)."""
    x, y = _tokens(a), _tokens(b)
    if len(x) < 2 or len(y) < 2:
        return False
    eq = lambda p, q: p[:4] == q[:4]
    return (eq(x[0], y[0]) and eq(x[1], y[1])) or (eq(x[0], y[1]) and eq(x[1], y[0]))


def existing_staff(owner_id: int) -> list:
    """Контрагенты с трудовым договором компании."""
    return list(Counterparty.objects.filter(contracts__owner_id=owner_id,
                                            contracts__title__title__icontains="трудов").distinct())


def match_staff(name: str, staff: list) -> list:
    """Существующие сотрудники с тем же именем (больше одного — неоднозначно)."""
    return [c for c in staff if same_person(name, c.name)]


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
    staff = existing_staff(owner.id)
    made, ids = 0, []
    with transaction.atomic():
        for acc, p in people.items():
            found = match_staff(_name(p["names"]), staff)
            if len(found) > 1:                           # несколько карточек — решает пользователь
                log(f"  пропуск {acc}: похожих сотрудников несколько — " + "; ".join(c.name for c in found))
                continue
            if found:                                    # тот же сотрудник с новым счётом
                CounterpartyAccount.objects.get_or_create(account=acc, defaults={"cp": found[0], "comment": "зарплата"})
                log(f"  счёт {acc} → существующий сотрудник {found[0].name}")
                ids += p["ids"]
                continue
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
                staff.append(cp)
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
