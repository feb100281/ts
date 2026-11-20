"""Сотрудники зарубежной компании: контрагент, счёт и договор на каждого получателя зарплаты из выписок."""
import re
from collections import Counter, defaultdict

from django.db import transaction
from django.db.models import Q

from contracts.models import CfItemAuto, Contracts
from corporate.models import BankAccount
from counterparties.models import Counterparty
from treasury.models import CfData, CounterpartyAccount

SALARY = re.compile(r"աշխատավարձ|արձակուրդ|պարգև|վերահաշվարկ", re.I)


def _name(names: Counter) -> str:
    n = names.most_common(1)[0][0] if names else ""
    return " ".join(n.upper().split())


def _tokens(name: str) -> list[str]:
    return [w for w in re.findall(r"[A-ZА-ЯЁ]+", (name or "").upper()) if w not in ("ИП", "ООО")][:3]


def same_person(a: str, b: str) -> bool:
    """Фамилия и имя совпадают по первым 4 буквам, в любом порядке (МОЛЕВАН ЮЛИЯ = МОЛЕВА ЮЛИЯ);
    отчество, если есть у обоих, — тоже (ДМИТРИЕВИЧ = ДМИТРИИ)."""
    x, y = _tokens(a), _tokens(b)
    if len(x) < 2 or len(y) < 2:
        return False
    eq = lambda p, q: p[:4] == q[:4]
    if len(x) > 2 and len(y) > 2 and not eq(x[2], y[2]):
        return False
    return (eq(x[0], y[0]) and eq(x[1], y[1])) or (eq(x[0], y[1]) and eq(x[1], y[0]))


STAFF_TITLES = Q(contracts__title__title__icontains="трудов") | Q(contracts__title__title__icontains="подотч")


def existing_staff(owner_id: int | None = None) -> list:
    """Сотрудники всех компаний группы (трудовой договор или подотчёт): один человек — одна карточка."""
    return list(Counterparty.objects.filter(STAFF_TITLES).distinct())


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
            if found:                                    # тот же человек (в т. ч. сотрудник другой компании группы)
                cp = found[0]
                log(f"  счёт {acc} → существующий сотрудник {cp.name}")
            else:
                cp, _ = Counterparty.objects.get_or_create(
                    tax_id=f"AM-{acc}", defaults={"name": _name(p["names"]), "country": "AM"})
                staff.append(cp)
                log(f"  новый сотрудник: {cp.name} | {acc}")
            CounterpartyAccount.objects.get_or_create(account=acc, defaults={"cp": cp, "comment": "зарплата"})
            if not Contracts.objects.filter(owner=owner, cp=cp, title_id=tpl.title_id).exists():
                c = Contracts.objects.get(pk=tpl.pk)
                c.pk = c.id = None
                c.cp = cp
                c.regex = None                           # договор единственный у контрагента — подбор по счёту
                c.save()
                CfItemAuto.objects.bulk_create([CfItemAuto(contract=c, regex=a.regex,
                                                           defaultcfdt=a.defaultcfdt,
                                                           defaultcfcr=a.defaultcfcr) for a in autos])
                made += 1
                if found:
                    log(f"  трудовой договор в {owner} для {cp.name}")
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


# ============================================================
# Дубли сотрудников
# ============================================================

def staff_duplicates(owner_id: int | None = None) -> list[list]:
    """Группы карточек одного сотрудника, где есть сотрудник зарубежной компании.
    Основная — с настоящим ИНН (не «AM-…»), затем с большим числом операций."""
    foreign = set(Counterparty.objects.filter(contracts__owner__country__isnull=False)
                  .exclude(contracts__owner__country="RU").values_list("pk", flat=True))
    staff = existing_staff()
    groups: list[list] = []
    for c in staff:
        g = next((g for g in groups if any(same_person(c.name, x.name) for x in g)), None)
        if g is None:
            groups.append([c])
        else:
            g.append(c)
    ops = lambda c: CfData.objects.filter(cp_final=c).count()
    return [sorted(g, key=lambda c: ((c.tax_id or "").startswith("AM-"), -ops(c), c.pk))
            for g in groups if len(g) > 1 and any(c.pk in foreign for c in g)]


def _relink(obj, target, skip: tuple) -> int:
    """Все ссылки на obj (кроме моделей skip) — на target."""
    n = 0
    for rel in obj._meta.related_objects:
        if rel.related_model in skip or not (rel.one_to_many or rel.one_to_one):
            continue
        n += rel.related_model.objects.filter(**{rel.field.name: obj}).update(**{rel.field.name: target})
    return n


def _refs(obj, skip: tuple) -> int:
    """Сколько объектов ссылается на obj (без моделей skip)."""
    return sum(rel.related_model.objects.filter(**{rel.field.name: obj}).count()
               for rel in obj._meta.related_objects
               if rel.related_model not in skip and (rel.one_to_many or rel.one_to_one))


def merge_staff(owner_id, main: Counterparty, dup: Counterparty, log=print) -> None:
    """Счета, операции и договоры дубля — на основную карточку; пустой дубль удаляется.
    Договор дубля сливается с таким же договором основной карточки в той же компании, иначе переходит к ней."""
    from contracts.models import ContractItems
    with transaction.atomic():
        for c in Contracts.objects.filter(cp=dup).select_related("title"):
            main_c = (Contracts.objects.filter(owner_id=c.owner_id, cp=main, title_id=c.title_id)
                      .order_by("id").first())
            if main_c is not None:
                n = _relink(c, main_c, (CfItemAuto, ContractItems))
                log(f"    договор {c.pk} → {main_c.pk}: ссылок {n}")
            else:
                c.cp = main
                c.save(update_fields=["cp"])
                log(f"    договор {c.pk} перенесён на {main.name}")
        n = _relink(dup, main, (Contracts,))
        left = [c for c in Contracts.objects.filter(cp=dup) if _refs(c, (CfItemAuto, ContractItems))]
        if _refs(dup, (Contracts,)) or left:             # что-то не перенеслось — не удаляем
            log(f"    карточка {dup.pk}: ссылок перенесено {n}, остались связи — не удалена")
            return
        name, pk = dup.name, dup.pk
        dup.delete()                                     # пустая карточка с её пустым договором
        log(f"    {name} (id {pk}): ссылок перенесено {n}, дубль удалён")


def staff_template_of(owner_id: int, cp):
    return (Contracts.objects.filter(owner_id=owner_id, cp=cp, title__title__icontains="трудов")
            .order_by("id").first())
