"""
Разноска зарубежных компаний по карточкам договоров (RegEx договора и автоматизация).

    am_resolve                    сверка: что изменится, без записи (+ Excel «было/стало» в media/am_reports)
    am_resolve --apply            пересобрать разноску и включить новый режим для компании
    am_resolve --off              вернуть прежний механизм (правила и отметки «руками» остаются)

При --apply операции, у которых сейчас есть договор, а по правилам договора нет,
помечаются «разнесено руками» и остаются как есть — ничего не теряется.
"""
from collections import Counter
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from contracts.models import CfItemAuto, Contracts
from corporate.models import CfItems, Owners
from counterparties.models import Counterparty
from treasury.models import CfData
from utils.bsparsers.am.resolve import resolve


class Command(BaseCommand):
    help = "Разноска зарубежных компаний: сверка, --apply, --off"

    def add_arguments(self, p):
        p.add_argument("--apply", action="store_true", help="пересобрать разноску")
        p.add_argument("--off", action="store_true", help="вернуть прежний механизм")
        p.add_argument("--owner", type=int, help="только эта компания (id)")

    def handle(self, apply, off, owner=None, **_):
        from django.utils import timezone
        from treasury.models import AmMode
        owners = Owners.objects.exclude(country="RU").exclude(country__isnull=True)
        if owner:
            owners = owners.filter(pk=owner)
        if off:
            for o in owners:
                AmMode.objects.update_or_create(owner=o, defaults={"on": False, "switched_at": timezone.now()})
                self.stdout.write(f"{o}: прежний механизм")
            return
        for owner in owners:
            self.stdout.write(f"\n{owner}")
            res = resolve(owner.pk, dry=True, log=self.stdout.write)
            self._report(owner, res["changes"])
            if apply:
                keep = [i for i, old, new, _ in res["changes"] if old[2] and not new[2]]
                with transaction.atomic():
                    CfData.objects.filter(id__in=keep).update(manual=True)
                    resolve(owner.pk, log=self.stdout.write)
                    AmMode.objects.update_or_create(owner=owner, defaults={"on": True, "switched_at": timezone.now()})
                self.stdout.write("  включена разноска по карточкам договоров")
                self.stdout.write(f"  оставлено как было (договор есть, правила нет), помечено «руками»: {len(keep)}")
        if not apply:
            self.stdout.write("\nСверка без записи. Для пересборки добавьте --apply.")

    # ---------------- сверка ----------------

    def _report(self, owner, changes):
        cps = dict(Counterparty.objects.values_list("id", "name"))
        cts = {i: f"{t} id {i}" for i, t in Contracts.objects.values_list("id", "title__title")}
        its = {i: f"{c} {n}" for i, c, n in CfItems.objects.values_list("id", "code", "name")}
        pairs, lost = Counter(), Counter()
        for _, old, new, how in changes:
            if old[2] and not new[2]:
                if not new[0]:
                    why = "контрагент по счёту/ИНН не найден"
                elif new[0] != old[0]:
                    why = f"по счёту/ИНН это {cps.get(new[0], new[0])}"
                else:
                    why = "нет подходящей строки в правилах"
                lost[(cps.get(old[0], "—"), cts.get(old[2], "—"), why)] += 1
                continue
            pairs[(cts.get(old[2], "—"), cts.get(new[2], "—"))] += 1
        self.stdout.write(f"  изменится операций: {len(changes) - sum(lost.values())}; "
                          f"останутся как есть (правила нет): {sum(lost.values())}")
        for (a, b), n in pairs.most_common(40):
            self.stdout.write(f"    {n:>6}  {a}  →  {b}")
        if lost:
            self.stdout.write("  правило не повторяет разноску (было: контрагент | договор — причина):")
            for (cp, c, why), n in lost.most_common(40):
                self.stdout.write(f"    {n:>6}  {cp} | {c} — {why}")
        try:
            from openpyxl import Workbook
        except ImportError:
            return
        ops = {o.id: o for o in CfData.objects.filter(id__in=[c[0] for c in changes]).select_related("ba")}
        wb = Workbook()
        ws = wb.active
        ws.title = "Было-стало"
        ws.append(["id", "Дата", "Поступление", "Списание", "Счёт", "Имя в выписке", "Назначение",
                   "Контрагент было", "Договор было", "Статья было",
                   "Контрагент стало", "Договор стало", "Статья стало", "Как определено", "Итог"])
        for i, old, new, how in changes:
            o = ops.get(i)
            if o is None:
                continue
            ws.append([i, o.date, o.dt, o.cr, o.ba.account if o.ba else "", o.cp_bs_name, o.temp_ru or o.temp,
                       cps.get(old[1], ""), cts.get(old[2], ""), its.get(old[3], ""),
                       cps.get(new[1], ""), cts.get(new[2], ""), its.get(new[3], ""), how,
                       "останется как было (руками)" if old[2] and not new[2] else "изменится"])
        folder = Path(settings.MEDIA_ROOT) / "am_reports"
        folder.mkdir(parents=True, exist_ok=True)
        name = f"resolve_{owner.pk}_{datetime.now():%Y%m%d_%H%M}.xlsx"
        wb.save(folder / name)
        self.stdout.write(f"  файл сверки: {settings.MEDIA_URL}am_reports/{name}")
