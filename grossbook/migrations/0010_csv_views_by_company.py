"""cf_to_csv и pl_for_csv — только Трендсеттер РФ (все существующие отчёты и дашборды не меняются).
Все компании — в cf_to_csv_all и pl_for_csv_all, их читает управленческий пакет с выбором компании."""
from django.db import migrations

FORWARD = r"""
CREATE OR REPLACE VIEW public.cf_to_csv_all AS
SELECT x.date_from,
    x.acc_id,
    x.subconto_id,
    x.contract_id,
    (((((tit.title)::text || ' № '::text) || (COALESCE(c.number, 'б/н'::character varying))::text) || ' от '::text) || COALESCE((c.date)::text, 'б/д'::text)) AS contract_name,
    cp.name AS cp_name,
    b.name AS account_name,
    (((lv1.code)::text || ' '::text) || (lv1.name)::text) AS activity,
    (((lv2.code)::text || ' '::text) || (lv2.name)::text) AS operation,
    (((lv3.code)::text || ' '::text) || (lv3.name)::text) AS item,
    (((i.code)::text || ' '::text) || (i.name)::text) AS subitem,
    x.description,
    x.dt,
    x.cr,
    (x.dt - x.cr) AS amount,
    x.company_id,
    own.name AS company
   FROM ((((((((( SELECT t.date_from,
            t.acc_id,
            t.subconto_id,
            t.contract_id,
            round(((t.dt)::numeric / 100.0), 2) AS dt,
            round(((t.cr)::numeric / 100.0), 2) AS cr,
            t.description,
            t.company_id
           FROM (gl.fact t
             JOIN corporate_coa pa ON ((pa.id = t.acc_id)))
          WHERE (((pa.parent_id = 3) OR (t.acc_id = 46)) AND (t.subconto_id <> 134))) x
     JOIN corporate_coa b ON ((b.id = x.acc_id)))
     JOIN corporate_cfitems i ON ((i.id = x.subconto_id)))
     JOIN corporate_cfitems lv3 ON ((lv3.id = i.parent_id)))
     JOIN corporate_cfitems lv2 ON ((lv2.id = lv3.parent_id)))
     JOIN corporate_cfitems lv1 ON ((lv1.id = lv2.parent_id)))
     LEFT JOIN contracts_contracts c ON ((c.id = x.contract_id)))
     LEFT JOIN contracts_contractstitle tit ON ((tit.id = c.title_id)))
     LEFT JOIN counterparties_counterparty cp ON ((cp.id = c.cp_id)))
     LEFT JOIN corporate_owners own ON ((own.id = x.company_id));

CREATE OR REPLACE VIEW public.pl_for_csv_all AS
SELECT p.date_from,
    p.acc_id,
    p.subconto_id,
    p.contract_id,
    cp.id AS cp_id,
    ap.id AS pid_account,
    concat_ws(' '::text, ap.code, ap.name) AS parent_account_name,
    concat_ws(' '::text, a.code, a.name) AS account_name,
    concat_ws(' '::text, sp.code, sp.name) AS cost_item_group,
    concat_ws(' '::text, s.code, s.name) AS cost_item,
    COALESCE(concat_ws(' '::text, ct.title, '№', COALESCE(c.number, 'б/н'::character varying), 'от', COALESCE(to_char((c.date)::timestamp with time zone, 'DD.MM.YYYY'::text), 'б/д'::text)), 'без договора'::text) AS contract_name,
    cp.name AS cp_name,
    round(((p.dt)::numeric / 100.00), 2) AS dt,
    round(((p.cr)::numeric / 100.00), 2) AS cr,
    round((((p.cr - p.dt))::numeric / 100.00), 2) AS amount,
    regexp_replace(p.description, '[\n\r]+'::text, ' '::text, 'g'::text) AS description,
    p.company_id,
    own.name AS company
   FROM (((((((gl.fact p
     LEFT JOIN contracts_contracts c ON ((c.id = p.contract_id)))
     LEFT JOIN contracts_contractstitle ct ON ((ct.id = c.title_id)))
     LEFT JOIN counterparties_counterparty cp ON ((cp.id = c.cp_id)))
     LEFT JOIN corporate_coa a ON ((a.id = p.acc_id)))
     LEFT JOIN corporate_coa ap ON ((ap.id = a.parent_id)))
     LEFT JOIN corporate_cfitems s ON ((s.id = p.subconto_id)))
     LEFT JOIN corporate_cfitems sp ON ((sp.id = s.parent_id)))
     LEFT JOIN corporate_owners own ON ((own.id = p.company_id))
  WHERE ((ap.id = ANY (ARRAY[(25)::bigint, (26)::bigint, (27)::bigint])) AND (p.date_from <= CURRENT_DATE));

CREATE OR REPLACE VIEW public.cf_to_csv AS
SELECT * FROM public.cf_to_csv_all WHERE company_id IN (SELECT id FROM corporate_owners WHERE report_group = 'Трендсеттер РФ');

CREATE OR REPLACE VIEW public.pl_for_csv AS
SELECT * FROM public.pl_for_csv_all WHERE company_id IN (SELECT id FROM corporate_owners WHERE report_group = 'Трендсеттер РФ');
"""

REVERSE = r"""
CREATE OR REPLACE VIEW public.cf_to_csv AS
SELECT x.date_from,
    x.acc_id,
    x.subconto_id,
    x.contract_id,
    (((((tit.title)::text || ' № '::text) || (COALESCE(c.number, 'б/н'::character varying))::text) || ' от '::text) || COALESCE((c.date)::text, 'б/д'::text)) AS contract_name,
    cp.name AS cp_name,
    b.name AS account_name,
    (((lv1.code)::text || ' '::text) || (lv1.name)::text) AS activity,
    (((lv2.code)::text || ' '::text) || (lv2.name)::text) AS operation,
    (((lv3.code)::text || ' '::text) || (lv3.name)::text) AS item,
    (((i.code)::text || ' '::text) || (i.name)::text) AS subitem,
    x.description,
    x.dt,
    x.cr,
    (x.dt - x.cr) AS amount,
    x.company_id,
    own.name AS company
   FROM ((((((((( SELECT t.date_from,
            t.acc_id,
            t.subconto_id,
            t.contract_id,
            round(((t.dt)::numeric / 100.0), 2) AS dt,
            round(((t.cr)::numeric / 100.0), 2) AS cr,
            t.description,
            t.company_id
           FROM (gl.fact t
             JOIN corporate_coa pa ON ((pa.id = t.acc_id)))
          WHERE (((pa.parent_id = 3) OR (t.acc_id = 46)) AND (t.subconto_id <> 134))) x
     JOIN corporate_coa b ON ((b.id = x.acc_id)))
     JOIN corporate_cfitems i ON ((i.id = x.subconto_id)))
     JOIN corporate_cfitems lv3 ON ((lv3.id = i.parent_id)))
     JOIN corporate_cfitems lv2 ON ((lv2.id = lv3.parent_id)))
     JOIN corporate_cfitems lv1 ON ((lv1.id = lv2.parent_id)))
     LEFT JOIN contracts_contracts c ON ((c.id = x.contract_id)))
     LEFT JOIN contracts_contractstitle tit ON ((tit.id = c.title_id)))
     LEFT JOIN counterparties_counterparty cp ON ((cp.id = c.cp_id)))
     LEFT JOIN corporate_owners own ON ((own.id = x.company_id));

CREATE OR REPLACE VIEW public.pl_for_csv AS
SELECT p.date_from,
    p.acc_id,
    p.subconto_id,
    p.contract_id,
    cp.id AS cp_id,
    ap.id AS pid_account,
    concat_ws(' '::text, ap.code, ap.name) AS parent_account_name,
    concat_ws(' '::text, a.code, a.name) AS account_name,
    concat_ws(' '::text, sp.code, sp.name) AS cost_item_group,
    concat_ws(' '::text, s.code, s.name) AS cost_item,
    COALESCE(concat_ws(' '::text, ct.title, '№', COALESCE(c.number, 'б/н'::character varying), 'от', COALESCE(to_char((c.date)::timestamp with time zone, 'DD.MM.YYYY'::text), 'б/д'::text)), 'без договора'::text) AS contract_name,
    cp.name AS cp_name,
    round(((p.dt)::numeric / 100.00), 2) AS dt,
    round(((p.cr)::numeric / 100.00), 2) AS cr,
    round((((p.cr - p.dt))::numeric / 100.00), 2) AS amount,
    regexp_replace(p.description, '[\n\r]+'::text, ' '::text, 'g'::text) AS description,
    p.company_id,
    own.name AS company
   FROM (((((((gl.fact p
     LEFT JOIN contracts_contracts c ON ((c.id = p.contract_id)))
     LEFT JOIN contracts_contractstitle ct ON ((ct.id = c.title_id)))
     LEFT JOIN counterparties_counterparty cp ON ((cp.id = c.cp_id)))
     LEFT JOIN corporate_coa a ON ((a.id = p.acc_id)))
     LEFT JOIN corporate_coa ap ON ((ap.id = a.parent_id)))
     LEFT JOIN corporate_cfitems s ON ((s.id = p.subconto_id)))
     LEFT JOIN corporate_cfitems sp ON ((sp.id = s.parent_id)))
     LEFT JOIN corporate_owners own ON ((own.id = p.company_id))
  WHERE ((ap.id = ANY (ARRAY[(25)::bigint, (26)::bigint, (27)::bigint])) AND (p.date_from <= CURRENT_DATE));

DROP VIEW IF EXISTS public.cf_to_csv_all;
DROP VIEW IF EXISTS public.pl_for_csv_all;
"""


class Migration(migrations.Migration):

    dependencies = [("grossbook", "0009_am_sales_to_gl")]

    operations = [migrations.RunSQL(FORWARD, REVERSE)]
