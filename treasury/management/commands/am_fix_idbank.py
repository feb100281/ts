"""
Рассрочка Айди Банка — один договор 730, статья по направлению.

    возвраты (RL gortsarq / Varki / mij het / Сделка RL): Дт — 123992 (возврат комиссии), Кт — 111300 (минус выручка)
    остальное (Loan… Merchant…):                         Дт — 111300 (продажа),          Кт — 123992 (комиссия)

Без --apply только показывает, что изменится.
"""
import re
from collections import Counter

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q

from contracts.models import CfItemAuto, ContractItems, Contracts
from corporate.models import CfItems
from counterparties.models import Counterparty
from treasury.models import CfData, CounterpartyAccount
from utils.bsparsers.am.staff import _refs

BANK, MAIN, IDRAM_ACQ, RL_CONTRACT, FEE_CONTRACT, RL_CARD = 242, 730, 531, 702, 533, 399
RET = "RL gortsarq|Varki|mij het|Сделка RL"
LOAN = "Loan|Merchant|" + RET


class Command(BaseCommand):
    help = "Рассрочка Айди Банка: операции на договор 730, статьи по направлению; без --apply только список"

    def add_arguments(self, p):
        p.add_argument("--apply", action="store_true")

    def handle(self, apply, **_):
        sale = CfItems.objects.get(code="111300")
        fee = CfItems.objects.get(code="123992")
        rx_ret, rx_loan = re.compile(RET, re.I), re.compile(LOAN, re.I)

        def is_loan(o):
            return rx_loan.search(o.temp or "") or rx_loan.search(o.temp_ru or "")

        qs = (CfData.objects.filter(contract_id__in=[MAIN, IDRAM_ACQ, RL_CONTRACT, FEE_CONTRACT], manual=False)
              .exclude(splits__isnull=False).select_related("contract", "cfitem"))
        ops = [o for o in qs if o.contract_id != IDRAM_ACQ or is_loan(o)]
        plan, pairs = [], Counter()
        for o in ops:
            ret = rx_ret.search(o.temp or "") or rx_ret.search(o.temp_ru or "")
            incoming = (o.dt or 0) > 0
            item = (fee if incoming else sale) if ret else (sale if incoming else fee)
            plan.append((o, item))
            pairs[(o.contract_id, o.cfitem.code if o.cfitem else "—", "Дт" if incoming else "Кт",
                   MAIN, item.code)] += 1
        self.stdout.write(f"Операций на договор {MAIN} (контрагент АЙДИ БАНК): {len(plan)}")
        for (c, it, d, c2, it2), n in sorted(pairs.items()):
            self.stdout.write(f"  {n:>5}  договор {c} статья {it} {d}  →  договор {c2} статья {it2}")
        left_idram = CfData.objects.filter(contract_id=IDRAM_ACQ).count() - sum(
            1 for o in ops if o.contract_id == IDRAM_ACQ)
        self.stdout.write(f"На договоре Идрама {IDRAM_ACQ} останется операций: {left_idram}")

        # счета, по которым продажи Айди Банка определялись как Идрам
        accs = Counter(o.payer_account if (o.dt or 0) > 0 else o.reciver_account for o in ops)
        links = CounterpartyAccount.objects.filter(account__in=[a for a in accs if a]).exclude(cp_id=BANK)
        for a in links:
            other = (CfData.objects.filter(Q(dt__gt=0, payer_account=a.account) | Q(cr__gt=0, reciver_account=a.account))
                     .exclude(id__in=[o.id for o in ops]).count())
            self.stdout.write(f"Счёт {a.account} привязан к {a.cp.name}: операций Айди Банка {accs[a.account]}, "
                              f"других {other}" + (" → перепривязать к АЙДИ БАНК" if not other else " — не трогаю"))

        if not apply:
            self.stdout.write("\nТолько просмотр. Записать: добавьте --apply")
            return
        with transaction.atomic():
            for o, item in plan:
                CfData.objects.filter(pk=o.pk).update(cp_id=BANK, cp_final_id=BANK, contract_id=MAIN, cfitem=item)
            for a in links:
                if not (CfData.objects.filter(Q(dt__gt=0, payer_account=a.account) | Q(cr__gt=0, reciver_account=a.account))
                        .exclude(id__in=[o.id for o in ops]).exists()):
                    a.cp_id, a.contract_id = BANK, None
                    a.save(update_fields=["cp", "contract"])
            main = Contracts.objects.get(pk=MAIN)
            main.regex = LOAN
            main.save(update_fields=["regex"])
            CfItemAuto.objects.filter(contract=main).delete()
            CfItemAuto.objects.create(contract=main, regex=RET, defaultcfdt=fee, defaultcfcr=sale)
            CfItemAuto.objects.create(contract=main, regex="", defaultcfdt=sale, defaultcfcr=fee)
            n = CfItemAuto.objects.filter(contract_id=FEE_CONTRACT, regex__iregex=r"loan|rl").delete()[0]
            self.stdout.write(f"Автоматизация {MAIN} заменена; у договора {FEE_CONTRACT} убрано строк Loan/RL: {n}")
            rl = Contracts.objects.filter(pk=RL_CONTRACT).first()
            if rl and not _refs(rl, (CfItemAuto, ContractItems)):
                rl.delete()
                self.stdout.write(f"Пустой договор {RL_CONTRACT} удалён")
            card = Counterparty.objects.filter(pk=RL_CARD).first()
            if card and not _refs(card, ()):
                card.delete()
                self.stdout.write("Карточка «ВОЗВРАТЫ ПОКУПАТЕЛЯМ — КРЕДИТЫ RL АЙДИ БАНКА» удалена")
        self.stdout.write("Готово.")
