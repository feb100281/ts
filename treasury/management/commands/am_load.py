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
        parser.add_argument("--force", action="store_true", help="перечитать и уже загруженные файлы")
        parser.add_argument("--lock", help="файл блокировки: параллельные запуски ждут очереди")

    def handle(self, *args, paths, dry_run, force=False, **options):
        if options.get("lock"):
            import fcntl
            self._lock = open(options["lock"], "a")
            fcntl.flock(self._lock, fcntl.LOCK_EX)   # снимается при выходе из процесса
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

        total_new = errors = skipped = 0
        owners = set()
        for f in files:
            try:
                with transaction.atomic():
                    lines = []
                    res = load_statement(f, log=lines.append, force=force)
                    if res.get("skipped"):
                        skipped += 1
                    else:
                        self.stdout.write(f"— {f.name}")
                        for line in lines:
                            self.stdout.write(line)
                    total_new += res["new"]
                    if res["new"] or force:
                        owners.add(res["owner_id"])
                    if dry_run:
                        raise DryRun
            except DryRun:
                pass
            except StatementError as exc:
                errors += 1
                self.stdout.write(f"— {f.name}")
                self.stdout.write(self.style.ERROR(f"  ✗ {exc}"))

        for f in sales_files:
            try:
                with transaction.atomic():
                    lines = []
                    res = load_sales(f, log=lines.append, force=force)
                    if res.get("skipped"):
                        skipped += 1
                    else:
                        self.stdout.write(f"— {f.name} (продажи)")
                        for line in lines:
                            self.stdout.write(line)
                    if dry_run:
                        raise DryRun
            except DryRun:
                pass
            except Exception as exc:                        # ошибка одного файла не останавливает остальные
                errors += 1
                self.stdout.write(f"— {f.name} (продажи)")
                self.stdout.write(self.style.ERROR(f"  ✗ {exc}"))

        if not dry_run and owners:                          # разноска только при новых операциях или --force
            for owner_id in owners:
                reassign(owner_id, log=self.stdout.write)
            retranslate(log=self.stdout.write)

        note = " (пробный прогон, ничего не записано)" if dry_run else ""
        self.stdout.write(self.style.SUCCESS(f"Выписок: {len(files)}, файлов продаж: {len(sales_files)}, "
                                             f"без изменений: {skipped}, новых операций: {total_new}, "
                                             f"ошибок: {errors}{note}"))
