"""Диагностика сводных проводок по компаниям (только чтение)."""
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import connection

QUERIES = [
    ("Владельцы банковских счетов с операциями", """
        SELECT o.id, o.name, o.report_group, count(DISTINCT a.id) AS accounts,
               count(DISTINCT a.bs_acc_id) AS coa, count(t.id) AS ops
        FROM corporate_bankaccount a
        JOIN corporate_owners o ON o.id = a.corporate_id
        LEFT JOIN treasury_cfdata t ON t.ba_id = a.id
        GROUP BY 1, 2, 3 ORDER BY 1"""),
    ("Балансовые счета, общие для разных владельцев", """
        SELECT a.bs_acc_id, array_agg(DISTINCT a.corporate_id) AS owners, array_agg(a.account) AS accounts
        FROM corporate_bankaccount a WHERE a.bs_acc_id IS NOT NULL
        GROUP BY 1 HAVING count(DISTINCT a.corporate_id) > 1"""),
    ("Армянские счета: балансовый счёт", """
        SELECT a.id, a.account, a.currency, a.bs_acc_id
        FROM corporate_bankaccount a JOIN corporate_owners o ON o.id = a.corporate_id
        WHERE o.report_group <> 'Трендсеттер РФ' ORDER BY 2"""),
    ("Условия договоров по владельцу договора", """
        SELECT c.owner_id, count(*) AS conditions, count(DISTINCT c.id) AS contracts
        FROM contracts_conditions t JOIN contracts_contracts c ON c.id = t.contract_id
        GROUP BY 1 ORDER BY 1"""),
    ("Функции начислений", """
        SELECT f.id, f.server_path, count(t.id) AS conditions
        FROM contracts_accuralfn f LEFT JOIN contracts_conditions t ON t.fn_id = f.id
        GROUP BY 1, 2 ORDER BY 1"""),
    ("gl.fact по компаниям и разделам", """
        SELECT company_id, chapter, count(*) AS n, sum(dt) AS dt, sum(cr) AS cr
        FROM gl.fact GROUP BY 1, 2 ORDER BY 1, 2"""),
    ("gl.normalized_cf по компаниям", """
        SELECT company_id, count(*), sum(dt), sum(cr) FROM gl.normalized_cf GROUP BY 1 ORDER BY 1"""),
    ("Колонки gl.cash_revaluation", """
        SELECT column_name, data_type FROM information_schema.columns
        WHERE table_schema = 'gl' AND table_name = 'cash_revaluation' ORDER BY ordinal_position"""),
    ("Колонки gl.fact", """
        SELECT column_name, data_type FROM information_schema.columns
        WHERE table_schema = 'gl' AND table_name = 'fact' ORDER BY ordinal_position"""),
    ("Индексы витрин gl", """
        SELECT tablename, indexname, indexdef FROM pg_indexes WHERE schemaname = 'gl' ORDER BY 1, 2"""),
    ("Кто зависит от gl.mv_ba_distribution", """
        SELECT DISTINCT dn.nspname || '.' || dc.relname AS dependent, dc.relkind
        FROM pg_depend d
        JOIN pg_rewrite r ON r.oid = d.objid
        JOIN pg_class dc ON dc.oid = r.ev_class
        JOIN pg_namespace dn ON dn.oid = dc.relnamespace
        WHERE d.refobjid = 'gl.mv_ba_distribution'::regclass AND dc.oid <> 'gl.mv_ba_distribution'::regclass"""),
    ("Владелец таблиц gl", """
        SELECT c.relname, c.relkind, pg_get_userbyid(c.relowner) AS owner
        FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'gl' AND c.relkind IN ('r', 'v', 'm') ORDER BY 1"""),
    ("Текущий пользователь", "SELECT current_user, current_database()"),
]


class Command(BaseCommand):
    help = "Диагностика проводок по компаниям, отчёт в файл"

    def add_arguments(self, parser):
        parser.add_argument("out")

    def handle(self, *args, out, **options):
        lines = []
        for title, sql in QUERIES:
            lines.append(f"## {title}")
            try:
                with connection.cursor() as cur:
                    cur.execute(sql)
                    lines.append(" | ".join(c.name for c in cur.description))
                    for row in cur.fetchall():
                        lines.append(" | ".join("" if v is None else str(v) for v in row))
            except Exception as exc:
                lines.append(f"ошибка: {exc}")
                connection.rollback() if not connection.get_autocommit() else None
            lines.append("")
        Path(out).write_text("\n".join(lines), encoding="utf-8")
        self.stdout.write(f"Диагностика → {out}")
