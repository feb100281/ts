"""Проверка договоров зарубежных компаний: контрагенты с несколькими договорами и перенос операций по RegEx.

Без --apply — только отчёт. Данные РФ не затрагиваются.
"""
from django.core.management.base import BaseCommand
from django.db import connection
from django.db.models import Count, Q

from contracts.models import Contracts
from corporate.models import Owners
from treasury.models import CfData, CounterpartyAccount
from utils.bsparsers.am.loader import is_transit, reassign, regroup_contract

MOVABLE = """
    SELECT count(*) FROM treasury_cfdata d
    WHERE d.owner_id = %(owner)s AND (d.cp_id = %(cp)s OR d.cp_final_id = %(cp)s)
      AND (d.temp ~* %(rx)s OR coalesce(d.temp_ru, '') ~* %(rx)s)
      AND d.contract_id IS DISTINCT FROM %(c)s
      AND (d.contract_id IS NULL OR EXISTS (
            SELECT 1 FROM contracts_contracts o
            WHERE o.id = d.contract_id AND o.cp_id = %(cp)s AND coalesce(o.regex, '') = ''))
      AND NOT EXISTS (SELECT 1 FROM treasury_cfsplits s WHERE s.transaction_id = d.id)
"""


class Command(BaseCommand):
    help = "Договоры зарубежных компаний: проверка RegEx и перенос операций; без --apply только отчёт"

    def add_arguments(self, p):
        p.add_argument("--apply", action="store_true", help="перенести операции и переразнести пустые")

    def handle(self, apply, **_):
        self._transit(apply)
        self._foreign_contract(apply)
        for owner in Owners.objects.exclude(country="RU").exclude(country__isnull=True):
            self.stdout.write(f"\n{owner}")
            multi = (Contracts.objects.filter(owner=owner).values("cp_id")
                     .annotate(n=Count("id"), empty=Count("id", filter=Q(regex__isnull=True) | Q(regex="")))
                     .filter(n__gt=1))
            bad = [m for m in multi if m["empty"] > 1]
            self.stdout.write(f"  контрагентов с несколькими договорами: {len(multi)}; "
                              f"без RegEx больше одного договора: {len(bad)}")
            for m in bad:
                for c in Contracts.objects.filter(owner=owner, cp_id=m["cp_id"]).select_related("cp", "title"):
                    self.stdout.write(f"    {c.cp.name} | {c.title} id {c.pk} | RegEx: {c.regex or '—'}")
            moves = 0
            for c in (Contracts.objects.filter(owner=owner).exclude(regex__isnull=True).exclude(regex="")
                      .select_related("cp", "owner")):
                try:
                    if apply:
                        n = regroup_contract(c, lambda *_: None)
                    else:
                        with connection.cursor() as cur:
                            cur.execute(MOVABLE, {"owner": owner.pk, "cp": c.cp_id, "rx": c.regex.strip(), "c": c.pk})
                            n = cur.fetchone()[0]
                except Exception as exc:
                    self.stdout.write(self.style.ERROR(f"  ✗ {c.cp.name} id {c.pk}: RegEx «{c.regex}» — {exc}"))
                    continue
                if n:
                    moves += n
                    self.stdout.write(f"  {c.cp.name} | {c.title} id {c.pk} ← операций по RegEx: {n}")
            self.stdout.write(f"  итого {'перенесено' if apply else 'будет перенесено'}: {moves}")
            if apply:
                reassign(owner.pk, log=lambda x: self.stdout.write("  " + x.strip()))
        if not apply:
            self.stdout.write("\nПроверка без записи. Для переноса добавьте --apply.")

    def _transit(self, apply):
        """Транзитные счета банков, привязанные к контрагенту: отвязать, их операции разнести заново (по ИНН)."""
        links = [a for a in CounterpartyAccount.objects.select_related("cp") if is_transit(a.account)]
        self.stdout.write(f"Транзитные счета банков, привязанные к контрагентам: {len(links)}")
        foreign = CfData.objects.exclude(owner__country="RU").exclude(owner__isnull=True)
        for a in links:
            ops = (foreign.filter(Q(dt__gt=0, payer_account=a.account) | Q(cr__gt=0, reciver_account=a.account))
                   .filter(Q(cp=a.cp) | Q(cp_final=a.cp)).exclude(splits__isnull=False))
            self.stdout.write(f"  {a.account} → {a.cp.name}: операций по нему {ops.count()}"
                              + (" — отвязан, операции переразносятся" if apply else ""))
            if apply:
                ops.update(cp=None, cp_final=None, contract=None, cfitem=None)
                a.delete()

    def _foreign_contract(self, apply):
        """Операции, где договор принадлежит другому контрагенту: договор и статью — сбросить и разнести заново."""
        from django.db.models import F
        ops = (CfData.objects.exclude(owner__country="RU").exclude(owner__isnull=True)
               .filter(cp__isnull=False, contract__isnull=False).exclude(contract__cp_id=F("cp_id"))
               .exclude(splits__isnull=False))
        rows = list(ops.select_related("cp", "contract__cp").order_by("cp__name")[:30])
        self.stdout.write(f"Операций, где договор другого контрагента: {ops.count()}")
        for o in rows:
            self.stdout.write(f"  {o.date} {o.dt or o.cr} | контрагент {o.cp.name} | договор {o.contract.cp.name} id {o.contract_id}")
        if apply:
            n = ops.update(contract=None, cfitem=None, cp_final=None)
            self.stdout.write(f"  сброшено: {n}, будут переразнесены")