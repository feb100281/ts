"""Выгрузить определения всех представлений базы (обычных и материализованных) в один .sql файл."""

from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import connection

SQL = """
SELECT schemaname, viewname, 'VIEW' AS kind, definition FROM pg_views
WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
UNION ALL
SELECT schemaname, matviewname, 'MATERIALIZED VIEW', definition FROM pg_matviews
ORDER BY 1, 2
"""


class Command(BaseCommand):
    help = "Определения представлений базы → .sql"

    def add_arguments(self, parser):
        parser.add_argument("out")

    def handle(self, *args, out, **options):
        with connection.cursor() as cur:
            cur.execute(SQL)
            rows = cur.fetchall()
        text = "\n\n".join(f"-- {s}.{n}\nCREATE {k} {s}.{n} AS\n{d.strip()}" for s, n, k, d in rows)
        Path(out).write_text(f"-- база: {connection.settings_dict['NAME']}, представлений: {len(rows)}\n\n{text}\n",
                             encoding="utf-8")
        self.stdout.write(f"Представлений: {len(rows)} → {out}")
