"""
Возврат договоров и статей операциям РФ из сохранённой копии gl.normalized_cf_save_20261122
(после случайной повторной обработки выписок РФ).

Сопоставление: компания, счёт учёта, валюта, дата, приход, расход и назначение.
Меняются только строки, где в копии договор или статья были, а сейчас другие. Без --apply — только отчёт.
"""
from collections import Counter, defaultdict

from django.core.management.base import BaseCommand
from django.db import connection, transaction

from contracts.models import Contracts
from treasury.models import CfData

SAVE = "gl.normalized_cf_save_20261122"


class Command(BaseCommand):
    help = "Вернуть договоры и статьи РФ из копии GL; без --apply только отчёт"

    def add_arguments(self, p):
        p.add_argument("--apply", action="store_true")

    def handle(self, apply, **_):
        with connection.cursor() as c:
            c.execute(f"""SELECT company_id, acc_id, currency, date_from, base_dt, base_cr, coalesce(description, ''),
                                 contract_id, subconto_id FROM {SAVE}""")
            saved = defaultdict(list)
            for *k, contract, item in c.fetchall():
                saved[tuple(k)].append((contract, item))
            c.execute("""
                SELECT t.id, b.corporate_id, b.bs_acc_id, b.currency, t.date,
                       ROUND(t.dt * 100, 0)::bigint, ROUND(t.cr * 100, 0)::bigint, coalesce(t.temp, ''),
                       t.contract_id, t.cfitem_id,
                       EXISTS (SELECT 1 FROM treasury_cfsplits s WHERE s.transaction_id = t.id)
                FROM treasury_cfdata t
                JOIN corporate_bankaccount b ON b.id = t.ba_id
                JOIN corporate_owners o ON o.id = b.corporate_id AND o.report_group = 'Трендсеттер РФ'
                ORDER BY t.id""")
            current = defaultdict(list)
            for i, comp, acc, cur, d, dt, cr, txt, contract, item, split in c.fetchall():
                current[(comp, acc, cur, d, dt, cr, txt)].append((i, contract, item, split))

        cps = dict(Contracts.objects.values_list("id", "cp_id"))
        stat = Counter()
        fix = []
        for k, rows in current.items():
            old = saved.get(k)
            if not old:
                stat["нет в копии (новые или изменённые после копии)"] += len(rows)
                continue
            if len(old) != len(rows):
                stat["разное число одинаковых строк — пропущено"] += len(rows)
                continue
            old = sorted(old, key=lambda x: (x[0] or 0, x[1] or 0))
            for (i, contract, item, split), (oc, oi) in zip(rows, old):
                if split:
                    stat["сплит — не трогаю"] += 1
                elif (oc, oi) == (contract, item):
                    stat["совпадает"] += 1
                elif oc is None and oi is None:
                    stat["в копии пусто"] += 1
                else:
                    fix.append((i, oc or contract, oi or item))
                    stat["будет возвращено"] += 1
        for k, n in stat.most_common():
            self.stdout.write(f"  {n:>7}  {k}")
        if not apply:
            self.stdout.write("\nТолько отчёт. Вернуть: добавьте --apply")
            return
        with transaction.atomic():
            for i, contract, item in fix:
                CfData.objects.filter(pk=i).update(contract_id=contract, cfitem_id=item,
                                                   cp_final_id=cps.get(contract))
        self.stdout.write(f"Возвращено строк: {len(fix)}")
