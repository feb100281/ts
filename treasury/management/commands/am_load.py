"""
Загрузка армянских выписок: файлы или папки (с подпапками).

    python manage.py am_load <путь> [<путь> ...] [--dry-run]

Повторная загрузка безопасна: добавляются только новые операции.
"""

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from utils.bsparsers.am.loader import load_statement, sniff
from utils.bsparsers.am.parser import StatementError


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
        files = [f for f in files if sniff(f)]
        if not files:
            raise CommandError("армянских выписок не найдено")

        total_new = errors = 0
        for f in files:
            self.stdout.write(f"— {f.name}")
            try:
                with transaction.atomic():
                    res = load_statement(f, log=self.stdout.write)
                    total_new += res["new"]
                    if dry_run:
                        raise DryRun
            except DryRun:
                pass
            except StatementError as exc:
                errors += 1
                self.stdout.write(self.style.ERROR(f"  ✗ {exc}"))

        note = " (пробный прогон, ничего не записано)" if dry_run else ""
        self.stdout.write(self.style.SUCCESS(f"Файлов: {len(files)}, новых операций: {total_new}, ошибок: {errors}{note}"))
