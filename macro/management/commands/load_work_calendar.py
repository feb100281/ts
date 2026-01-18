# macro/management/commands/load_work_calendar.py
from django.core.management.base import BaseCommand, CommandError

from macro.utils.calendar_loader import load_work_calendar_for_year


class Command(BaseCommand):
    help = "Загрузить производственный календарь за указанный год в CalendarExceptions"

    def add_arguments(self, parser):
        parser.add_argument(
            "year",
            type=int,
            help="Год, для которого нужно загрузить календарь (например, 2025)",
        )

    def handle(self, *args, **options):
        year = options["year"]

        if year < 2000 or year > 2100:
            raise CommandError("Год должен быть между 2000 и 2100")

        self.stdout.write(f"Загружаю производственный календарь за {year}...")

        try:
            count = load_work_calendar_for_year(year)
        except Exception as e:
            raise CommandError(f"Ошибка при загрузке календаря: {e}")

        self.stdout.write(self.style.SUCCESS(
            f"Готово! Вставлено {count} записей за {year}."
        ))

