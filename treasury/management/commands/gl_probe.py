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
    ("Владелец витрин выгрузки", """
        SELECT c.relname, pg_get_userbyid(c.relowner) FROM pg_class c
        WHERE c.relname IN ('cf_to_csv', 'pl_for_csv', 'accurals_args', 'ba_to_gl')"""),
    ("gl.ba_to_gl по компаниям", """
        SELECT company_id, chapter, count(*), sum(dt), sum(cr) FROM gl.ba_to_gl GROUP BY 1, 2 ORDER BY 1, 2"""),
    ("gl.accurals_args: компания договора", """
        SELECT * FROM (SELECT to_jsonb(a) ->> 'company_id' AS company_id, count(*) FROM gl.accurals_args a GROUP BY 1) x"""),
    ("cf_to_csv / pl_for_csv: колонка компании", """
        SELECT 'cf' AS src, to_jsonb(t) ->> 'company' AS company, count(*), sum(amount)
        FROM (SELECT * FROM cf_to_csv) t GROUP BY 1, 2
        UNION ALL
        SELECT 'pl', to_jsonb(t) ->> 'company', count(*), sum(amount)
        FROM (SELECT * FROM pl_for_csv) t GROUP BY 1, 2"""),
    ("Разнесённость операций по компаниям", """
        SELECT o.name, count(*) AS ops, count(t.contract_id) AS with_contract, count(t.cfitem_id) AS with_item,
               count(*) FILTER (WHERE t.contract_id IS NOT NULL AND t.cfitem_id IS NOT NULL) AS ready
        FROM treasury_cfdata t JOIN corporate_bankaccount a ON a.id = t.ba_id
        JOIN corporate_owners o ON o.id = a.corporate_id GROUP BY 1 ORDER BY 1"""),
    ("Соответствие полей WB счетам", """
        SELECT m.*, a.code AS pl_code, a.name AS pl_name
        FROM gl.wb_mapping m LEFT JOIN corporate_coa a ON a.id = (to_jsonb(m) ->> 'acc_pl')::bigint
        ORDER BY 1"""),
    ("План счетов: группы P&L и балансовые верхнего уровня", """
        SELECT a.id, a.code, a.name, a.parent_id, p.code AS parent_code
        FROM corporate_coa a LEFT JOIN corporate_coa p ON p.id = a.parent_id
        WHERE a.parent_id IS NULL OR a.parent_id IN (25, 26, 27) OR a.id IN (25, 26, 27)
        ORDER BY a.code"""),
    ("Обороты gl.fact по счетам P&L", """
        SELECT f.acc_id, a.code, a.name, f.chapter, count(*), sum(f.dt), sum(f.cr)
        FROM gl.fact f JOIN corporate_coa a ON a.id = f.acc_id
        WHERE a.parent_id IN (25, 26, 27) GROUP BY 1, 2, 3, 4 ORDER BY 2, 4"""),
    ("Статьи ДДС с id, верхний уровень и выручка", """
        SELECT i.id, i.code, i.name, i.parent_id FROM corporate_cfitems i
        WHERE i.parent_id IS NULL OR i.name ILIKE '%%выручк%%' OR i.name ILIKE '%%себестоим%%' OR i.name ILIKE '%%продаж%%'
        ORDER BY i.code"""),
    ("Контракт 109 и счета договора", """
        SELECT c.id, c.title_id, c.cp_id, c.owner_id, c.bs_id, c.st_id, c.pl_id, c.subconto_bs_id, c.subconto_pl_id
        FROM contracts_contracts c WHERE c.id IN (109, 122)"""),
    ("Розница в книге по месяцам", """
        SELECT date_trunc('month', f.date_from)::date AS m, f.company_id, f.chapter, a.code, sum(f.dt) / 100.0 AS dt,
               sum(f.cr) / 100.0 AS cr, count(*)
        FROM gl.fact f JOIN corporate_coa a ON a.id = f.acc_id
        WHERE f.chapter IN ('PL_RETAIL', 'BS_RETAIL') GROUP BY 1, 2, 3, 4 ORDER BY 1, 3, 4"""),
    ("Розница в pl_for_csv по компаниям", """
        SELECT to_jsonb(t) ->> 'company' AS company, t.cost_item, count(*), sum(t.amount)
        FROM pl_for_csv t WHERE t.cost_item LIKE '5_0190%%' GROUP BY 1, 2"""),
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
                if not connection.get_autocommit():
                    connection.rollback()
            lines.append("")
        Path(out).write_text("\n".join(lines), encoding="utf-8")
        self.stdout.write(f"Диагностика → {out}")
