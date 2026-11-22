"""
Пересборка разноски зарубежной компании по резолверам («Правила разноски»).

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
from treasury.models import AmResolver, AmRule, CfData, CounterpartyAccount, TransitAccount

from .resolve_core import Rule, resolve_one

FIELDS = ("cp_id", "cp_final_id", "contract_id", "cfitem_id")


def context(owner_id: int) -> dict:
    links = {a: (cp, c) for a, cp, c in CounterpartyAccount.objects.values_list("account", "cp_id", "contract_id")}
    inn_cps = {t: i for i, t in Counterparty.objects.values_list("id", "tax_id") if t and t.isdigit()}
    rules: dict = {}
    for r in (AmRule.objects.filter(resolver__owner_id=owner_id)
              .select_related("resolver").order_by("resolver_id", "order", "id")):
        rules.setdefault((owner_id, r.resolver.cp_id), []).append(
            Rule(r.id, (r.text_regex or "").strip(), r.contract_id, r.cf_item_dt_id, r.cf_item_cr_id))
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
            if ids is None:                              # счётчики правил — по полному прогону
                rules = list(AmRule.objects.filter(resolver__owner_id=owner_id))
                for x in rules:
                    x.hits = hits.get(x.id, 0)
                AmRule.objects.bulk_update(rules, ["hits"], batch_size=500)
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
