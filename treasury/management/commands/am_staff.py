"""Сотрудники зарубежной компании: контрагент, счёт и договор по образцу на каждого получателя зарплаты."""
from django.core.management.base import BaseCommand, CommandError

from contracts.models import Contracts
from corporate.models import Owners
from utils.bsparsers.am.staff import (_name, create_staff, existing_staff, find_staff, match_staff, merge_staff,
                                      staff_duplicates, staff_template)


class Command(BaseCommand):
    help = "Создаёт контрагента, счёт и договор на каждого получателя зарплаты; без --apply только список"

    def add_arguments(self, p):
        p.add_argument("--template", type=int, help="id договора-образца; по умолчанию — последний трудовой")
        p.add_argument("--apply", action="store_true", help="записать в базу")
        p.add_argument("--merge", action="store_true", help="объединить дубли сотрудников (с --apply — записать)")

    def handle(self, template, apply, merge=False, **_):
        if merge:
            return self._merge(apply)
        if template:
            tpl = Contracts.objects.select_related("owner").filter(pk=template).first()
            if tpl is None:
                raise CommandError(f"договор {template} не найден")
            owners = [tpl.owner]
        else:
            owners = list(Owners.objects.exclude(country="RU").exclude(country__isnull=True))
        for owner in owners:
            if (owner.country or "RU") == "RU":
                raise CommandError("образец должен принадлежать зарубежной компании")
            tpl = Contracts.objects.get(pk=template) if template else staff_template(owner.id)
            people = find_staff(owner.id)
            if not people:
                self.stdout.write(f"{owner}: новых получателей зарплаты нет.")
                continue
            if tpl is None:
                self.stdout.write(f"{owner}: нет трудового договора-образца, получателей {len(people)}.")
                continue
            self.stdout.write(f"{owner}; образец: {tpl} (id {tpl.pk})")
            staff = existing_staff(owner.id)
            new = 0
            for acc, p in sorted(people.items(), key=lambda x: _name(x[1]["names"])):
                found = match_staff(_name(p["names"]), staff)
                if len(found) > 1:
                    mark = "пропуск, похожих несколько: " + "; ".join(f"{c.name} (id {c.pk})" for c in found)
                else:
                    mark = f"→ уже есть: {found[0].name}" if found else "НОВЫЙ"
                new += not found
                self.stdout.write(f"  {_name(p['names'])} | {acc} | операций {len(p['ids'])} | {mark}")
            self.stdout.write(f"  итого счетов: {len(people)}, из них новых сотрудников: {new}")
            if apply:
                made = create_staff(tpl, people, lambda *_: None)
                self.stdout.write(f"  новых договоров: {made}, операции разнесены")
        if not apply:
            self.stdout.write("Проверка без записи. Для создания добавьте --apply.")

    def _merge(self, apply):
        groups = staff_duplicates()
        self.stdout.write(f"Групп дублей сотрудников (все компании): {len(groups)}")
        for main, *dups in groups:
            self.stdout.write(f"  основная: {main} (id {main.pk}); дубли: "
                              + "; ".join(f"{d} (id {d.pk})" for d in dups))
            if apply:
                for d in dups:
                    merge_staff(None, main, d, self.stdout.write)
        if not apply:
            self.stdout.write("Проверка без записи. Для объединения добавьте --apply.")
