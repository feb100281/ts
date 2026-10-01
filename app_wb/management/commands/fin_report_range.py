from datetime import date, timedelta

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Run fin_report for date range"

    def add_arguments(self, parser):
        parser.add_argument("date_from", type=str, help="YYYY-MM-DD")
        parser.add_argument("date_to", type=str, help="YYYY-MM-DD")
        parser.add_argument("--overwrite", action="store_true")

    def handle(self, *args, **options):
        try:
            date_from = date.fromisoformat(options["date_from"])
            date_to = date.fromisoformat(options["date_to"])
        except ValueError:
            raise CommandError("Dates must be YYYY-MM-DD")

        if date_from > date_to:
            raise CommandError("date_from must be <= date_to")

        d = date_from

        while d <= date_to:
            self.stdout.write("")
            self.stdout.write(f"=== FIN REPORT {d} ===")

            call_command(
                "fin_report",
                d.isoformat(),
                overwrite=options["overwrite"],
            )

            d += timedelta(days=1)

        self.stdout.write(self.style.SUCCESS("FIN REPORT RANGE DONE"))