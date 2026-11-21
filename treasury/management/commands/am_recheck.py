"""Проверка договоров зарубежных компаний: контрагенты с несколькими договорами и перенос операций по RegEx.

Без --apply — только отчёт. Данные РФ не затрагиваются.
"""
from django.core.management.base import BaseCommand
from django.db import connection
from django.db.models import Count, Q

from contracts.models import Contracts
from corporate.models import Owners
from utils.bsparsers.am.loader import reassign, regroup_contract

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
