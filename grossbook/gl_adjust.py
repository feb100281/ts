"""Загрузка корректировок GL (grossbook_gladjustment) в gl.fact.

ADJ_GL — проводка Дт/Кт (две строки с общим pid).
ADJ_CF — перенос между статьями Cash Flow, если стоит галочка: две строки на счёте денег
(+сумма на «откуда», −сумма на «куда» с договором), в сумме ноль.
Идемпотентно: удаляет только свои главы и вставляет заново. Другие главы не трогает.
"""

CHAPTERS = ("ADJ_GL", "ADJ_CF")

SQL = """
DELETE FROM gl.fact WHERE chapter IN ('ADJ_GL', 'ADJ_CF');

WITH a AS (
    SELECT g.*, gen_random_uuid() AS pid, ROUND(g.amount * 100)::bigint AS k,
           'Корректировка GL #' || g.id
               || COALESCE(': ' || NULLIF(TRIM(g.comment), ''), '') AS descr
    FROM public.grossbook_gladjustment g
    WHERE g.amount <> 0
)
INSERT INTO gl.fact (id, pid, date_from, acc_id, contract_id, dt, cr,
                     description, subconto_id, company_id, chapter)
SELECT gen_random_uuid(), a.pid, a.date, s.acc_id, s.contract_id, s.dt, s.cr,
       a.descr, s.sub, a.owner_id, s.chapter
FROM a
CROSS JOIN LATERAL (VALUES
    (a.dt_acc_id, a.dt_contract_id, a.dt_subconto_id, a.k, 0::bigint, 'ADJ_GL'),
    (a.cr_acc_id, a.cr_contract_id, a.cr_subconto_id, 0::bigint, a.k, 'ADJ_GL'),
    (a.cf_acc_id, NULL::bigint, a.cf_from_id, a.k, 0::bigint, 'ADJ_CF'),
    (a.cf_acc_id, COALESCE(a.dt_contract_id, a.cr_contract_id), a.cf_to_id, 0::bigint, a.k,
     'ADJ_CF')
) AS s(acc_id, contract_id, sub, dt, cr, chapter)
WHERE s.chapter = 'ADJ_GL'
   OR (a.cf AND a.cf_acc_id IS NOT NULL AND a.cf_from_id IS NOT NULL AND a.cf_to_id IS NOT NULL);
"""


def apply(cursor) -> int:
    """Перезаписать главы ADJ_GL / ADJ_CF; вернуть число строк в gl.fact."""
    cursor.execute(SQL)
    cursor.execute("SELECT count(*) FROM gl.fact WHERE chapter IN ('ADJ_GL', 'ADJ_CF')")
    n = cursor.fetchone()[0]
    # отчёт ДДС — материализованное представление: обновить, чтобы перенос был виден сразу
    cursor.execute("SELECT 1 FROM pg_matviews WHERE schemaname = 'gl' AND matviewname = 'mv_cf_report'")
    if cursor.fetchone():
        cursor.execute("REFRESH MATERIALIZED VIEW gl.mv_cf_report")
    return n
