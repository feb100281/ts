"""Один контрагент на банк: эквайринг и инкассация переносятся на основного контрагента банка.

Счета эквайринга привязываются к договору эквайринга (договор по счёту), договоры и операции
переходят на банк, пустая карточка удаляется. Без --apply — только список.
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q

from contracts.models import Contracts
from counterparties.models import Counterparty
from treasury.models import CounterpartyAccount
from utils.bsparsers.am.staff import _refs, _relink

# (откуда, куда)
PAIRS = [("AM-ACQ-ARDSHIN", "AM-ARDSHINBANK"),
         ("AM-ACQ-VTB", "AM-VTB"),
         ("AM-ARARAT-INKAS-FEE", "AM-ARARAT-INKAS")]
RENAME = {"AM-ACQ-ACBA": "АКБА БАНК"}
# у банка станет несколько договоров — комиссии ВТБ подбираются по назначению
REGEX = {("AM-VTB", "Комиссия эквайринг"): "POS"}
# счета, которые остаются у банка, но идут на свой договор
BIND = {"AM-ARARAT-INKAS": {"2470032194060000": "799100"}}


# проценты на остаток — к банку, который их платит: счёт → (ИНН-заглушка банка, название, если банка нет)
INTEREST_SRC = "AM-BANK-INTEREST"
INTEREST = {"33140620025325": ("AM-VTB", "ВТБ-АРМЕНИЯ"),
            "33140620025358": ("AM-VTB", "ВТБ-АРМЕНИЯ"),
            "1150005473033022": ("AM-AMIOBANK", "АМИО БАНК")}


class Command(BaseCommand):
    help = "Объединить карточки эквайринга/инкассации с банком; без --apply только список"

    def add_arguments(self, p):
        p.add_argument("--apply", action="store_true")

    def handle(self, apply, **_):
        with transaction.atomic():
            for src_tax, dst_tax in PAIRS:
                src = Counterparty.objects.filter(tax_id=src_tax).first()
                dst = Counterparty.objects.filter(tax_id=dst_tax).first()
                if not src or not dst:
                    self.stdout.write(f"{src_tax} → {dst_tax}: нет карточки, пропуск")
                    continue
                contracts = list(Contracts.objects.filter(cp=src).select_related("title", "owner"))
                accounts = list(CounterpartyAccount.objects.filter(cp=src))
                self.stdout.write(f"{src.name} → {dst.name}: договоров {len(contracts)}, счетов {len(accounts)}")
                for c in contracts:
                    self.stdout.write(f"    договор {c.title} id {c.pk} ({c.owner}) → {dst.name}")
                for a in accounts:
                    self.stdout.write(f"    счёт {a.account} → {dst.name}, договор по счёту id {contracts[0].pk if contracts else '—'}")
                if not apply:
                    continue
                main = contracts[0] if contracts else None
                for a in accounts:
                    a.cp, a.contract = dst, main
                    a.save(update_fields=["cp", "contract"])
                for c in contracts:
                    c.cp = dst
                    c.save(update_fields=["cp"])
                n = _relink(src, dst, (Contracts,))
                if _refs(src, ()):
                    self.stdout.write(f"    {src.name}: остались связи — карточка не удалена")
                else:
                    src.delete()
                    self.stdout.write(f"    операций и ссылок перенесено {n}, карточка {src_tax} удалена")
            for tax, name in RENAME.items():
                cp = Counterparty.objects.filter(tax_id=tax).first()
                if cp and cp.name != name:
                    self.stdout.write(f"{cp.name} → переименовать в {name}")
                    if apply:
                        cp.name = name
                        cp.save(update_fields=["name"])
            for (tax, title), rx in REGEX.items():
                empty = Q(regex__isnull=True) | Q(regex="")
                for c in Contracts.objects.filter(empty, cp__tax_id=tax, title__title=title).select_related("cp"):
                    self.stdout.write(f"{c.cp.name} | {title} id {c.pk}: RegEx «{rx}»")
                    if apply:
                        c.regex = rx
                        c.save(update_fields=["regex"])
            for tax, binds in BIND.items():
                for acc, st in binds.items():
                    a = CounterpartyAccount.objects.filter(account=acc, cp__tax_id=tax).first()
                    c = Contracts.objects.filter(cp__tax_id=tax, bs__code=st).first()
                    if a and c and a.contract_id != c.pk:
                        self.stdout.write(f"счёт {acc} → договор по счёту id {c.pk}")
                        if apply:
                            a.contract = c
                            a.save(update_fields=["contract"])
            self._interest(apply)
        if not apply:
            self.stdout.write("\nПроверка без записи. Для объединения добавьте --apply.")

    def _interest(self, apply):
        """Проценты на остаток: договор — у каждого банка, счёт процентов привязан к нему, общая карточка удаляется."""
        from contracts.models import CfItemAuto
        from treasury.models import CfData
        src = Counterparty.objects.filter(tax_id=INTEREST_SRC).first()
        if not src:
            return
        tpl = Contracts.objects.filter(cp=src).first()
        self.stdout.write(f"{src.name}: договор id {tpl.pk if tpl else '—'}")
        made = {}
        for acc, (tax, name) in INTEREST.items():
            self.stdout.write(f"    счёт {acc} → {name}, договор «Проценты на остаток»")
            if not apply or tpl is None:
                continue
            bank, _ = Counterparty.objects.get_or_create(tax_id=tax, defaults={"name": name, "country": "AM"})
            c = made.get(tax)
            if c is None:
                c = Contracts.objects.filter(cp=bank, owner=tpl.owner, bs=tpl.bs, pl=tpl.pl).first()
            if c is None:
                c = Contracts.objects.get(pk=tpl.pk)
                c.pk = c.id = None
                c.cp, c.regex = bank, None
                c.save()
                for a in CfItemAuto.objects.filter(contract=tpl):
                    a.pk = a.id = None
                    a.contract = c
                    a.save()
            made[tax] = c
            CounterpartyAccount.objects.update_or_create(account=acc, defaults={"cp": bank, "contract": c})
            n = (CfData.objects.filter(Q(cp=src) | Q(cp_final=src))
                 .filter(Q(payer_account=acc) | Q(reciver_account=acc))
                 .update(cp=bank, cp_final=bank, contract=c))
            self.stdout.write(f"      операций перенесено: {n}")
        if apply and tpl is not None:
            left = CfData.objects.filter(Q(cp=src) | Q(cp_final=src) | Q(contract=tpl)).count()
            if left or CounterpartyAccount.objects.filter(cp=src).exists():
                self.stdout.write(f"    {src.name}: остались операции ({left}) — карточка не удалена")
            else:
                src.delete()
                self.stdout.write(f"    карточка {src.name} удалена")
