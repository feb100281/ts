"""
Пересборка разноски зарубежной компании по карточкам договоров (RegEx и автоматизация).

    resolve(owner_id)            — все операции компании, кроме разнесённых руками и со сплитами
    resolve(owner_id, ids=[…])   — только эти операции
    resolve(..., dry=True)       — ничего не пишет, возвращает изменения (для сверки «было/стало»)

Прогон можно повторять сколько угодно: автоматическая разноска строится заново по текущим правилам.
Сами правила — utils/bsparsers/am/resolve_core.py.
"""

from __future__ import annotations

from collections import Counter

from django.db import transaction

from contracts.models import CfItemAuto, Contracts
from corporate.models import CfItems
from counterparties.models import Counterparty
from treasury.models import CfData, CounterpartyAccount, TransitAccount

from .resolve_core import Rule, resolve_one

FIELDS = ("cp_id", "cp_final_id", "contract_id", "cfitem_id")


CATCH_ALL = (".", ".*")


def _and(a: str, b: str) -> str:
    """И RegEx договора, и RegEx строки автоматизации."""
    a, b = (a or "").strip(), (b or "").strip()
    if b in ("",) + CATCH_ALL:
        return "" if a in CATCH_ALL else a
    if a in ("",) + CATCH_ALL:
        return b
    return f"(?s)(?=.*(?:{a}))(?=.*(?:{b}))"


def contract_rules(owner_id: int, bound: set) -> dict:
    """Правила из карточек договоров: RegEx договора + строки автоматизации (статья Дт / Кт).

    У контрагента: договоры с RegEx — длинный RegEx первым; RegEx «.» — всё остальное, последним.
    Единственный договор контрагента без RegEx и единственный трудовой — тоже всё остальное.
    Без контрагента (не найден по счёту и ИНН) — RegEx всех договоров компании, кроме «.».
    Договоры, привязанные к счетам, ставятся только по счёту.
    """
    autos: dict = {}
    for a in CfItemAuto.objects.filter(contract__owner_id=owner_id).order_by("id"):
        if a.defaultcfdt_id or a.defaultcfcr_id:
            autos.setdefault(a.contract_id, []).append(a)

    def lines(c, rx):
        items = sorted(autos.get(c.pk, []), key=lambda a: -len((a.regex or "").strip(". ")))
        return [Rule(None, _and(rx, a.regex), c.pk, a.defaultcfdt_id, a.defaultcfcr_id) for a in items]

    def rest(c):
        items = sorted(autos.get(c.pk, []), key=lambda a: len((a.regex or "").strip(". ")))
        d = next((a.defaultcfdt_id for a in items if a.defaultcfdt_id), None)
        k = next((a.defaultcfcr_id for a in items if a.defaultcfcr_id), None)
        return [Rule(None, "", c.pk, d, k)] if d or k else []

    by_cp: dict = {}
    for c in Contracts.objects.filter(owner_id=owner_id).exclude(pk__in=bound).select_related("title"):
        if c.cp_id:
            by_cp.setdefault(c.cp_id, []).append(c)
    rules, general = {}, []
    for cp_id, cs in by_cp.items():
        rx = {c.pk: (c.regex or "").strip() for c in cs}
        specific = sorted([c for c in cs if rx[c.pk] and rx[c.pk] not in CATCH_ALL], key=lambda c: -len(rx[c.pk]))
        plan = [r for c in specific for r in lines(c, rx[c.pk])]
        general += [(len(rx[c.pk]), r) for c in specific for r in lines(c, rx[c.pk])]
        for c in cs:
            if rx[c.pk] in CATCH_ALL:
                plan += lines(c, "") + rest(c)
        if len(cs) == 1:
            c = cs[0]
            labor = "трудов" in (c.title.title if c.title_id else "").lower()
            if not rx[c.pk]:
                plan += lines(c, "") + rest(c)
            elif labor:
                plan += rest(c)
        rules[(owner_id, cp_id)] = plan
    rules[(owner_id, None)] = [r for _, r in sorted(general, key=lambda t: -t[0])]
    for c in Contracts.objects.filter(owner_id=owner_id, pk__in=bound):   # статьи по счёту — по автоматизации
        rules[(owner_id, ("bound", c.pk))] = lines(c, "")
    return rules


def context(owner_id: int) -> dict:
    links = {a: (cp, c) for a, cp, c in CounterpartyAccount.objects.values_list("account", "cp_id", "contract_id")}
    inn_cps = {t: i for i, t in Counterparty.objects.values_list("id", "tax_id") if t and t.isdigit()}
    bound = {c for _, c in links.values() if c}
    rules = contract_rules(owner_id, bound)
    contracts = {i: (cp, ow) for i, cp, ow in Contracts.objects.values_list("id", "cp_id", "owner_id")}
    auto = {}
    for a in CfItemAuto.objects.order_by("id"):
        auto.setdefault(a.contract_id, (a.defaultcfdt_id, a.defaultcfcr_id))
    transit = frozenset(TransitAccount.objects.values_list("account", flat=True))
    return dict(links=links, inn_cps=inn_cps, rules=rules, contracts=contracts, auto=auto, transit=transit)


def resolve(owner_id: int, ids=None, dry: bool = False, log=print) -> dict:
    ctx = context(owner_id)
    qs = CfData.objects.filter(owner_id=owner_id, manual=False).exclude(splits__isnull=False)
    if ids is not None:
        qs = qs.filter(id__in=list(ids))
    rows = qs.values("id", "dt", "payer_account", "reciver_account", "ba__account", "temp", "temp_ru",
                     "cp_bs_name", "intercompany", *FIELDS)
    conv = CfItems.objects.filter(code="410201").values_list("id", flat=True).first()
    changed, changes, hits = [], [], Counter()
    total = with_contract = 0
    for r in rows:
        total += 1
        op = dict(r, owner=owner_id, ba_account=r["ba__account"])
        res = resolve_one(op, **ctx)
        if res.rule:
            hits[res.rule] += 1
        if res.contract:
            with_contract += 1
        new = (res.cp, res.cp_final, res.contract, res.cfitem)
        old = tuple(r[f] for f in FIELDS)
        ic = r["intercompany"] and not (conv and res.cfitem == conv)
        if new != old or ic != r["intercompany"]:
            changes.append((r["id"], old, new, res.how))
            changed.append(CfData(id=r["id"], cp_id=res.cp, cp_final_id=res.cp_final, contract_id=res.contract,
                                  cfitem_id=res.cfitem, intercompany=ic))
    if not dry:
        with transaction.atomic():
            CfData.objects.bulk_update(changed, ["cp", "cp_final", "contract", "cfitem", "intercompany"],
                                       batch_size=1000)
    stats = dict(total=total, changed=len(changes), with_contract=with_contract, without=total - with_contract)
    log(f"  разноска: операций {total}, изменено {len(changes)}, с договором {with_contract}, "
        f"без договора {total - with_contract}")
    return dict(stats, changes=changes)


def resolve_ids(ids, log=print) -> None:
    """Пересборка для набора операций (любых зарубежных компаний)."""
    by_owner: dict = {}
    for o, i in (CfData.objects.filter(id__in=list(ids)).exclude(owner__country="RU")
                 .exclude(owner__isnull=True).values_list("owner_id", "id")):
        by_owner.setdefault(o, []).append(i)
    for o, part in by_owner.items():
        resolve(o, part, log=log)
