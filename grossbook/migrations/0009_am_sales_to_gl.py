"""Розничные продажи зарубежных компаний в главную книгу: выручка, себестоимость, возвраты.
Суммы в рублях по курсу ЦБ РФ на дату документа, по дням."""
from django.db import migrations

FORWARD = r"""
CREATE OR REPLACE VIEW gl.am_sales_to_gl AS
WITH acc AS (
    SELECT
        (SELECT id FROM corporate_coa WHERE code = '410000') AS rev,
        (SELECT id FROM corporate_coa WHERE code = '510000') AS cogs,
        (SELECT id FROM corporate_coa WHERE code = '799100') AS ar,
        (SELECT id FROM corporate_coa WHERE code = '199100') AS inv,
        (SELECT id FROM corporate_cfitems WHERE code = '510190') AS i_rev,
        (SELECT id FROM corporate_cfitems WHERE code = '520190') AS i_cogs
),
d AS (
    SELECT s.owner_id,
           (s.doc_date AT TIME ZONE 'Asia/Yerevan')::date AS day,
           sum(CASE WHEN s.kind = 'sale' THEN s.amount_novat ELSE 0 END) AS sales,
           sum(CASE WHEN s.kind <> 'sale' THEN s.amount_novat ELSE 0 END) AS returns,
           sum(CASE WHEN s.kind = 'sale' THEN s.cost_total ELSE 0 END) AS cost_sales,
           sum(CASE WHEN s.kind <> 'sale' THEN s.cost_total ELSE 0 END) AS cost_returns
    FROM sales_retailsale s
    GROUP BY 1, 2
),
r AS (
    SELECT d.*, fx.rate
    FROM d
    JOIN LATERAL (
        SELECT c.rate FROM macro_currencyrate c
        WHERE c.currency = 'AMD' AND c.base_currency = 'RUB' AND c.date <= d.day
        ORDER BY c.date DESC LIMIT 1
    ) fx ON TRUE
),
k AS (
    SELECT r.owner_id, r.day,
           round(r.sales * r.rate * 100)::bigint AS sales,
           round(r.returns * r.rate * 100)::bigint AS returns,
           round(r.cost_sales * r.rate * 100)::bigint AS cost_sales,
           round(r.cost_returns * r.rate * 100)::bigint AS cost_returns
    FROM r
),
rows AS (
    SELECT k.owner_id, k.day, a.rev AS acc_id, a.i_rev AS subconto_id, k.returns AS dt, k.sales AS cr,
           'Выручка розница'::text AS description, 'PL_RETAIL'::text AS chapter, 'REV' AS part
    FROM k, acc a
    UNION ALL
    SELECT k.owner_id, k.day, a.ar, a.i_rev, k.sales, k.returns,
           'Расчёты с покупателями розница', 'BS_RETAIL', 'AR'
    FROM k, acc a
    UNION ALL
    SELECT k.owner_id, k.day, a.cogs, a.i_cogs, k.cost_sales, k.cost_returns,
           'Себестоимость розница', 'PL_RETAIL', 'COGS'
    FROM k, acc a
    UNION ALL
    SELECT k.owner_id, k.day, a.inv, a.i_cogs, k.cost_returns, k.cost_sales,
           'Товары розница', 'BS_RETAIL', 'INV'
    FROM k, acc a
)
SELECT uuid_generate_v5('31111111-1111-1111-1111-111111111111'::uuid,
                        concat_ws('|', owner_id, day::text, part)) AS id,
       NULL::uuid AS pid,
       day AS date_from,
       acc_id,
       NULL::bigint AS contract_id,
       dt,
       cr,
       description,
       subconto_id,
       owner_id::bigint AS company_id,
       chapter
FROM rows
WHERE acc_id IS NOT NULL AND (dt <> 0 OR cr <> 0);
"""

REVERSE = "DROP VIEW IF EXISTS gl.am_sales_to_gl;"


class Migration(migrations.Migration):

    dependencies = [
        ("grossbook", "0008_gl_company"),
        ("sales", "0014_retailsale_source_sha1"),
    ]

    operations = [migrations.RunSQL(FORWARD, REVERSE)]
