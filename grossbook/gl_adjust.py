"""Загрузка корректировок GL (grossbook_gladjustment) в gl.fact главой ADJ_GL.

Идемпотентно: удаляет только свою главу и вставляет заново — две строки
(Дт и Кт) на каждую корректировку с общим pid. Другие главы не трогает.
"""

CHAPTER = "ADJ_GL"

SQL = """
DELETE FROM gl.fact WHERE chapter = 'ADJ_GL';

INSERT INTO gl.fact (id, pid, date_from, acc_id, contract_id, dt, cr,
                     description, subconto_id, company_id, chapter)
SELECT gen_random_uuid(), a.pid, a.date, s.acc_id, s.contract_id, s.dt, s.cr,
       a.descr, s.sub, a.owner_id, 'ADJ_GL'
FROM (
    SELECT g.*, gen_random_uuid() AS pid, ROUND(g.amount * 100)::bigint AS k,
           'Корректировка GL #' || g.id
               || COALESCE(': ' || NULLIF(TRIM(g.comment), ''), '') AS descr
    FROM public.grossbook_gladjustment g
    WHERE g.amount <> 0
) a
CROSS JOIN LATERAL (VALUES
    (a.dt_acc_id, a.dt_contract_id, a.dt_subconto_id, a.k, 0::bigint),
    (a.cr_acc_id, a.cr_contract_id, a.cr_subconto_id, 0::bigint, a.k)
) AS s(acc_id, contract_id, sub, dt, cr);
"""


def apply(cursor) -> int:
    """Перезаписать главу ADJ_GL; вернуть число строк в gl.fact."""
    cursor.execute(SQL)
    cursor.execute("SELECT count(*) FROM gl.fact WHERE chapter = 'ADJ_GL'")
    return cursor.fetchone()[0]
