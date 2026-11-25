from django.core.management.base import BaseCommand
from django.db import connection, transaction

from grossbook.gl_adjust import apply


class Command(BaseCommand):
    help = "Загрузить корректировки GL в gl.fact (глава ADJ_GL). Запускать после GL ETL."

    def handle(self, *args, **opts):
        with transaction.atomic(), connection.cursor() as cur:
            n = apply(cur)
        self.stdout.write(self.style.SUCCESS(f"ADJ_GL: {n} строк в gl.fact"))
