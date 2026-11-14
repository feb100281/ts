"""
Загрузка армянских выписок: файлы или папки (с подпапками).

    python manage.py am_load <путь> [<путь> ...] [--dry-run]

Повторная загрузка безопасна: добавляются только новые операции.
"""

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from utils.bsparsers.am.loader import load_statement, reassign, retranslate, sniff
from utils.bsparsers.am.parser import StatementError
from utils.bsparsers.am.sales import SalesError, is_sales_file
from utils.bsparsers.am.sales_loader import load_sales


class DryRun(Exception):
    pass


class Command(BaseCommand):
    help = "Загрузить армянские выписки (Америабанк, Банк-клиент)"

    def add_arguments(self, parser):
        parser.add_argument("paths", nargs="+")
        parser.add_argument("--dry-run", action="store_true", help="разобрать и проверить, в базу не писать")

    def handle(self, *args, paths, dry_run, **options):
        files = []
        for p in map(Path, paths):
            if p.is_dir():
                files += sorted(f for f in p.rglob("*") if f.is_file()
                                and not any(part.startswith(("_", ".")) for part in f.relative_to(p).parts))
            elif p.is_file():
                files.append(p)
            else:
                raise CommandError(f"нет такого пути: {p}")
        sales_files = [f for f in files if f.suffix.lower() == ".xlsx" and is_sales_file(f)]
        files = [f for f in files if f not in sales_files and sniff(f)]
        if not files and not sales_files:
            raise CommandError("армянских выписок и продаж не найдено")

        total_new = errors = 0
        owners = set()
        for f in files:
            self.stdout.write(f"— {f.name}")
            try:
                with transaction.atomic():
                    res = load_statement(f, log=self.stdout.write)
                    total_new += res["new"]
                    owners.add(res["owner_id"])
                    if dry_run:
                        raise DryRun
            except DryRun:
                pass
            except StatementError as exc:
                errors += 1
                self.stdout.write(self.style.ERROR(f"  ✗ {exc}"))

        for f in sales_files:
            self.stdout.write(f"— {f.name} (продажи)")
            try:
                with transaction.atomic():
                    load_sales(f, log=self.stdout.write)
                    if dry_run:
                        raise DryRun
            except DryRun:
                pass
            except Exception as exc:                        # ошибка одного файла не останавливает остальные
                errors += 1
                self.stdout.write(self.style.ERROR(f"  ✗ {exc}"))

        if not dry_run:
            for owner_id in owners:
                reassign(owner_id, log=self.stdout.write)
            retranslate(log=self.stdout.write)

        note = " (пробный прогон, ничего не записано)" if dry_run else ""
        self.stdout.write(self.style.SUCCESS(f"Выписок: {len(files)}, новых операций: {total_new}, "
                                             f"файлов продаж: {len(sales_files)}, ошибок: {errors}{note}"))
