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

FUNC_SQL = """
SELECT n.nspname, p.proname, pg_get_functiondef(p.oid)
FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
WHERE n.nspname NOT IN ('pg_catalog', 'information_schema') AND n.nspname NOT LIKE 'pg_%'
  AND p.prokind IN ('f', 'p')
  AND NOT EXISTS (SELECT 1 FROM pg_depend d WHERE d.objid = p.oid AND d.deptype = 'e')
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
            cur.execute(FUNC_SQL)
            funcs = cur.fetchall()
        text = "\n\n".join(f"-- {s}.{n}\nCREATE {k} {s}.{n} AS\n{d.strip()}" for s, n, k, d in rows)
        ftext = "\n\n".join(f"-- {s}.{n}\n{d.strip()};" for s, n, d in funcs)
        Path(out).write_text(f"-- база: {connection.settings_dict['NAME']}, представлений: {len(rows)}, функций: {len(funcs)}"
                             f"\n\n{text}\n\n-- ===== ФУНКЦИИ =====\n\n{ftext}\n", encoding="utf-8")
        self.stdout.write(f"Представлений: {len(rows)}, функций: {len(funcs)} → {out}")
