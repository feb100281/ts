"""Справочники для разноски зарубежных компаний: статьи CF, план счетов, типы и образцы договоров (только чтение)."""
from collections import Counter

from django.core.management.base import BaseCommand

from contracts.models import CfItemAuto, Contracts, ContractsTitle
from corporate.models import COA, CfItems, Owners
from treasury.models import CounterpartyAccount


def _c(x):
    return f"{x.code} {x.name}" if x else "—"


class Command(BaseCommand):
    help = "Выгружает справочники для разноски в текстовый файл"

    def add_arguments(self, p):
        p.add_argument("out", help="путь к файлу результата")

    def handle(self, out, **_):
        L = []
        L.append("## СТАТЬИ CF (код | название | родитель)")
        for x in CfItems.objects.select_related("parent").order_by("tree_id", "lft"):
            L.append(f"{x.code} | {x.name} | {x.parent.code if x.parent else ''}")
        L.append("\n## ПЛАН СЧЕТОВ (код | название | родитель)")
        for x in COA.objects.select_related("parent").order_by("tree_id", "lft"):
            L.append(f"{x.code} | {x.name} | {x.parent.code if x.parent else ''}")
        L.append("\n## ТИПЫ ДОГОВОРОВ")
        L += [t.title for t in ContractsTitle.objects.order_by("title")]

        def dump(qs, title):
            L.append(f"\n## {title}")
            for c in qs.select_related("title", "cp", "owner", "bs", "pl", "st", "subconto_pl", "subconto_bs"):
                autos = "; ".join(f"{a.regex} → Дт {_c(a.defaultcfdt)} / Кт {_c(a.defaultcfcr)}"
                                  for a in CfItemAuto.objects.filter(contract=c).select_related("defaultcfdt", "defaultcfcr"))
                L.append(f"[{c.pk}] {c.owner.name} | {c.title.title} | {c.cp.name} | ST {_c(c.bs)} | BS {_c(c.st)} "
                         f"| субк.BS {_c(c.subconto_bs)} | PL {_c(c.pl)} | субк.PL {_c(c.subconto_pl)} "
                         f"| RegEx {c.regex or ''} | авто: {autos}")

        foreign = Owners.objects.exclude(country="RU").exclude(country__isnull=True)
        dump(Contracts.objects.filter(owner__in=foreign).order_by("id"), "ДОГОВОРЫ ЗАРУБЕЖНЫХ КОМПАНИЙ")

        # образцы РФ: по 3 последних договора каждого типа
        ru = Contracts.objects.filter(owner__country="RU")
        ids = []
        for t in ru.values_list("title_id", flat=True).distinct():
            ids += list(ru.filter(title_id=t).order_by("-id").values_list("id", flat=True)[:3])
        dump(Contracts.objects.filter(id__in=ids).order_by("title__title", "id"), "ОБРАЗЦЫ ДОГОВОРОВ РФ (по 3 на тип)")

        L.append("\n## СЧЕТА КОНТРАГЕНТОВ ЗАРУБЕЖНЫХ (счёт | контрагент)")
        cps = CounterpartyAccount.objects.select_related("cp").filter(cp__country="AM").order_by("cp__name")
        L += [f"{a.account} | {a.cp.name}" for a in cps]

        L.append("\n## ЧАСТОТА СТАТЕЙ В ДОГОВОРАХ РФ (субк.PL)")
        cnt = Counter(ru.exclude(subconto_pl=None).values_list("subconto_pl__code", "subconto_pl__name"))
        L += [f"{n:5d} | {c} {nm}" for (c, nm), n in cnt.most_common(80)]

        with open(out, "w", encoding="utf-8") as f:
            f.write("\n".join(L) + "\n")
        self.stdout.write(f"Записано строк: {len(L)} → {out}")
