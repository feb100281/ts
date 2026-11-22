"""
Разноска зарубежных компаний по «Правилам разноски».

    am_resolve --build            завести правила из текущих договоров (RegEx и автоматизация);
                                  повторный запуск только дописывает недостающие строки
    am_resolve                    сверка: что изменится, без записи (+ Excel «было/стало» в media/am_reports)
    am_resolve --apply            пересобрать разноску и включить «Правила разноски» для компании
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
from treasury.models import AmResolver, AmRule, CfData, CounterpartyAccount
from utils.bsparsers.am.resolve import resolve


def _and(a: str, b: str) -> str:
    """Оба условия: и RegEx договора, и RegEx автоматизации."""
    a, b = (a or "").strip(), (b or "").strip()
    if b in ("", "."):
        return a
    if a in ("", "."):
        return b
    return f"(?s)(?=.*(?:{a}))(?=.*(?:{b}))"


class Command(BaseCommand):
    help = "Разноска зарубежных компаний по правилам: --build, сверка, --apply"

    def add_arguments(self, p):
        p.add_argument("--build", action="store_true", help="завести правила из текущих договоров")
        p.add_argument("--apply", action="store_true", help="пересобрать разноску")
        p.add_argument("--off", action="store_true", help="вернуть прежний механизм")
        p.add_argument("--owner", type=int, help="только эта компания (id)")

    def handle(self, build, apply, off, owner=None, **_):
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
            if build:
                self._build(owner)
                continue
            res = resolve(owner.pk, dry=True, log=self.stdout.write)
            self._report(owner, res["changes"])
            if apply:
                keep = [i for i, old, new, _ in res["changes"] if old[2] and not new[2]]
                with transaction.atomic():
                    CfData.objects.filter(id__in=keep).update(manual=True)
                    resolve(owner.pk, log=self.stdout.write)
                    AmMode.objects.update_or_create(owner=owner, defaults={"on": True, "switched_at": timezone.now()})
                self.stdout.write("  включены «Правила разноски»")
                self.stdout.write(f"  оставлено как было (договор есть, правила нет), помечено «руками»: {len(keep)}")
        if not build and not apply:
            self.stdout.write("\nСверка без записи. Для пересборки добавьте --apply.")

    # ---------------- правила из договоров ----------------

    def _build(self, owner):
        """Правила из договоров. Повторный запуск только дописывает недостающие строки в конец —
        строки, заведённые или исправленные руками, не меняются."""
        bound = set(CounterpartyAccount.objects.exclude(contract__isnull=True).values_list("contract_id", flat=True))
        contracts = list(Contracts.objects.filter(owner=owner).select_related("cp", "title"))
        by_cp: dict = {}
        for c in contracts:
            by_cp.setdefault(c.cp_id, []).append(c)
        autos: dict = {}
        for a in CfItemAuto.objects.filter(contract__owner=owner).order_by("id"):
            if a.defaultcfdt_id or a.defaultcfcr_id:
                autos.setdefault(a.contract_id, []).append(a)

        def rules_of(c, rx):
            items = sorted(autos.get(c.pk, []), key=lambda a: -len((a.regex or "").strip(". ")))
            return [(_and(rx, a.regex), c, a.defaultcfdt_id, a.defaultcfcr_id) for a in items]

        def catch_all(c):
            """Всё остальное — на договор; статьи из автоматизации (сначала строки без RegEx)."""
            items = sorted(autos.get(c.pk, []), key=lambda a: len((a.regex or "").strip(". ")))
            d = next((a.defaultcfdt_id for a in items if a.defaultcfdt_id), None)
            k = next((a.defaultcfcr_id for a in items if a.defaultcfcr_id), None)
            return [("", c, d, k)] if d or k else []

        def is_labor(c):
            return "трудов" in (c.title.title if c.title_id else "").lower()

        made_r = made_rules = 0

        def put(cp_id, plan, comment=""):
            nonlocal made_r, made_rules
            if not plan:
                return
            r, new = AmResolver.objects.get_or_create(owner=owner, cp_id=cp_id, defaults={"comment": comment})
            made_r += new
            have = set(r.rules.values_list("text_regex", "contract_id"))
            order = max(r.rules.values_list("order", flat=True), default=0)
            for rx, c, d, k in plan:
                if (rx, c.pk) in have:
                    continue
                have.add((rx, c.pk))
                order += 10
                AmRule.objects.create(resolver=r, order=order, text_regex=rx, contract=c, cf_item_dt_id=d,
                                      cf_item_cr_id=k)
                made_rules += 1

        general = []
        for cp_id, cs in by_cp.items():
            free = [c for c in cs if c.pk not in bound]
            if not free or cp_id is None:
                continue
            with_rx = sorted([c for c in free if (c.regex or "").strip()], key=lambda c: -len(c.regex))
            general += [(len(c.regex), x) for c in with_rx for x in rules_of(c, c.regex)]
            plan = [x for c in with_rx for x in rules_of(c, c.regex)]
            if len(free) == 1:                           # единственный договор: без RegEx или трудовой
                c = free[0]
                if not (c.regex or "").strip():
                    plan += rules_of(c, "") + catch_all(c)
                elif is_labor(c):
                    plan += catch_all(c)
            put(cp_id, plan)
        # контрагент не найден по счёту и ИНН — договоры по RegEx назначения, длинные RegEx первыми
        put(None, [x for _, x in sorted(general, key=lambda t: -t[0])], "операции без контрагента")

        self.stdout.write(f"  новых контрагентов с правилами: {made_r}, добавлено правил: {made_rules}")
        no_rules = [c for cs in by_cp.values() for c in cs if c.pk not in bound
                    and not AmRule.objects.filter(contract=c).exists()]
        if no_rules:
            self.stdout.write(f"  договоров без правил (по ним автоматически ничего не встанет): {len(no_rules)}")
            for c in no_rules[:40]:
                self.stdout.write(f"    {c.cp.name if c.cp_id else '—'} | {c.title} id {c.pk}")

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
