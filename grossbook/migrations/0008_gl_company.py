"""Компания в проводках: банк — по владельцу счёта, начисления — по владельцу договора,
колонки компании в выгрузках cf_to_csv и pl_for_csv. Для Трендсеттер РФ цифры не меняются."""
from django.db import migrations

FORWARD = r"""
CREATE OR REPLACE VIEW gl.accurals_args AS
SELECT t.contract_id,
    t.id AS condition_id,
    t.date_start,
    t.date_finish,
    (t.vat_mode)::text AS vat_mode,
    t.fn_id,
    f.python_path,
    f.server_path,
    c.bs_id AS acc_st_id,
    COALESCE(t.acc_bs_id, c.st_id) AS acc_bs_id,
    COALESCE(t.acc_pl_id, c.pl_id) AS acc_pl_id,
    COALESCE(t.subconto_bs_id, c.subconto_bs_id) AS subconto_bs_id,
    COALESCE(t.subconto_pl_id, c.subconto_pl_id) AS subconto_pl_id,
    (t.param_json)::json AS params_json,
    (t.vat_json)::json AS vat_json,
    c.owner_id AS company_id
   FROM ((contracts_conditions t
     LEFT JOIN contracts_contracts c ON ((c.id = t.contract_id)))
     LEFT JOIN contracts_accuralfn f ON ((f.id = t.fn_id)));

CREATE OR REPLACE VIEW gl.ba_to_gl AS
WITH cf AS (
         SELECT uuid_generate_v5('21111111-1111-1111-1111-111111111111'::uuid, concat_ws('|'::text, mv_ba_distribution.row_id, (mv_ba_distribution.date_from)::text, mv_ba_distribution.description, 'CF')) AS id,
            NULL::uuid AS pid,
            mv_ba_distribution.date_from,
            mv_ba_distribution.acc_bs AS acc_id,
            mv_ba_distribution.contract_id,
            mv_ba_distribution.dt_bs AS dt,
            mv_ba_distribution.cr_bs AS cr,
            mv_ba_distribution.description,
            mv_ba_distribution.subconto_bs AS subconto_id,
            COALESCE((SELECT ba.corporate_id FROM corporate_bankaccount ba WHERE ba.bs_acc_id = mv_ba_distribution.acc_bs ORDER BY ba.id LIMIT 1), (1)::bigint) AS company_id,
            'CF_BA'::text AS chapter
           FROM gl.mv_ba_distribution
          WHERE (mv_ba_distribution.acc_bs IS NOT NULL)
        UNION ALL
         SELECT uuid_generate_v5('21111111-1111-1111-1111-111111111111'::uuid, concat_ws('|'::text, grossbook_manual.id, (grossbook_manual.date)::text, grossbook_manual.temp, 'CF')) AS id,
            NULL::uuid AS pid,
            grossbook_manual.date AS date_from,
            grossbook_manual.acc_id,
            grossbook_manual.contract_id,
            ((grossbook_manual.dt * (100)::numeric))::bigint AS dt,
            ((grossbook_manual.cr * (100)::numeric))::bigint AS cr,
            grossbook_manual.temp AS description,
            grossbook_manual.cfitem_id AS subconto_id,
            grossbook_manual.owner_id AS company_id,
            'CF_BA'::text AS chapter
           FROM grossbook_manual
          WHERE (grossbook_manual.acc_id IN ( SELECT DISTINCT mv_ba_distribution.acc_bs
                   FROM gl.mv_ba_distribution))
        ), st AS (
         SELECT uuid_generate_v5('21111111-1111-1111-1111-111111111111'::uuid, concat_ws('|'::text, mv_ba_distribution.row_id, (mv_ba_distribution.date_from)::text, mv_ba_distribution.description, 'ST')) AS id,
            uuid_generate_v5('21111111-1111-1111-1111-111111111111'::uuid, concat_ws('|'::text, mv_ba_distribution.row_id, (mv_ba_distribution.date_from)::text, mv_ba_distribution.description, 'CF')) AS pid,
            mv_ba_distribution.date_from,
            mv_ba_distribution.acc_st AS acc_id,
            mv_ba_distribution.contract_id,
            mv_ba_distribution.dt_st AS dt,
            mv_ba_distribution.cr_st AS cr,
            concat_ws(' '::text, 'Оплата: ', 'Сч: ', mv_ba_distribution.acc_bs, ' сумма ', round((((mv_ba_distribution.dt_bs - mv_ba_distribution.cr_bs) / 100))::numeric, 2), ' руб на Сч ', mv_ba_distribution.acc_st) AS description,
            mv_ba_distribution.subconto_st AS subconto_id,
            COALESCE((SELECT ba.corporate_id FROM corporate_bankaccount ba WHERE ba.bs_acc_id = mv_ba_distribution.acc_bs ORDER BY ba.id LIMIT 1), (1)::bigint) AS company_id,
            'ST_BA'::text AS chapter
           FROM gl.mv_ba_distribution
          WHERE (mv_ba_distribution.acc_st IS NOT NULL)
        UNION ALL
         SELECT uuid_generate_v5('21111111-1111-1111-1111-111111111111'::uuid, concat_ws('|'::text, grossbook_manual.id, (grossbook_manual.date)::text, grossbook_manual.temp, 'ST')) AS id,
            uuid_generate_v5('21111111-1111-1111-1111-111111111111'::uuid, concat_ws('|'::text, grossbook_manual.id, (grossbook_manual.date)::text, grossbook_manual.temp, 'CF')) AS pid,
            grossbook_manual.date AS date_from,
            grossbook_manual.acc_id,
            grossbook_manual.contract_id,
            ((grossbook_manual.dt * ((100)::bigint)::numeric))::bigint AS dt,
            ((grossbook_manual.cr * ((100)::bigint)::numeric))::bigint AS cr,
            grossbook_manual.temp AS description,
            grossbook_manual.cfitem_id AS subconto_id,
            grossbook_manual.owner_id AS company_id,
            'ST_BA'::text AS chapter
           FROM grossbook_manual
          WHERE (grossbook_manual.acc_id IN ( SELECT DISTINCT mv_ba_distribution.acc_st
                   FROM gl.mv_ba_distribution))
        ), pl AS (
         SELECT uuid_generate_v5('21111111-1111-1111-1111-111111111111'::uuid, concat_ws('|'::text, mv_ba_distribution.row_id, (mv_ba_distribution.date_from)::text, mv_ba_distribution.description, 'PL')) AS id,
            NULL::uuid AS pid,
            mv_ba_distribution.date_from,
            mv_ba_distribution.acc_pl AS acc_id,
            mv_ba_distribution.contract_id,
            mv_ba_distribution.dt_pl AS dt,
            mv_ba_distribution.cr_pl AS cr,
            concat_ws(' '::text, 'Курсовые разницы: ', 'Сч: ', mv_ba_distribution.acc_bs, ' сумма ', round((((mv_ba_distribution.dt_pl - mv_ba_distribution.cr_pl) / 100))::numeric, 2), ' руб на Сч ', mv_ba_distribution.acc_pl) AS description,
            mv_ba_distribution.subconto_pl AS subconto_id,
            COALESCE((SELECT ba.corporate_id FROM corporate_bankaccount ba WHERE ba.bs_acc_id = mv_ba_distribution.acc_bs ORDER BY ba.id LIMIT 1), (1)::bigint) AS company_id,
            'PL_BA'::text AS chapter
           FROM gl.mv_ba_distribution
          WHERE (mv_ba_distribution.acc_pl IS NOT NULL)
        UNION ALL
         SELECT uuid_generate_v5('21111111-1111-1111-1111-111111111111'::uuid, concat_ws('|'::text, grossbook_manual.id, (grossbook_manual.date)::text, grossbook_manual.temp, 'PL')) AS id,
            NULL::uuid AS pid,
            grossbook_manual.date AS date_from,
            grossbook_manual.acc_id,
            grossbook_manual.contract_id,
            ((grossbook_manual.dt * (100)::numeric))::bigint AS dt,
            ((grossbook_manual.cr * (100)::numeric))::bigint AS cr,
            grossbook_manual.temp AS description,
            grossbook_manual.cfitem_id AS subconto_id,
            grossbook_manual.owner_id AS company_id,
            'PL_BA'::text AS chapter
           FROM grossbook_manual
          WHERE (grossbook_manual.acc_id IN ( SELECT DISTINCT mv_ba_distribution.acc_pl
                   FROM gl.mv_ba_distribution))
        )
 SELECT cf.id,
    cf.pid,
    cf.date_from,
    cf.acc_id,
    cf.contract_id,
    cf.dt,
    cf.cr,
    cf.description,
    cf.subconto_id,
    cf.company_id,
    cf.chapter
   FROM cf
UNION ALL
 SELECT pl.id,
    pl.pid,
    pl.date_from,
    pl.acc_id,
    pl.contract_id,
    pl.dt,
    pl.cr,
    pl.description,
    pl.subconto_id,
    pl.company_id,
    pl.chapter
   FROM pl;

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
"""

REVERSE = r"""
CREATE OR REPLACE VIEW gl.accurals_args AS
SELECT t.contract_id,
    t.id AS condition_id,
    t.date_start,
    t.date_finish,
    (t.vat_mode)::text AS vat_mode,
    t.fn_id,
    f.python_path,
    f.server_path,
    c.bs_id AS acc_st_id,
    COALESCE(t.acc_bs_id, c.st_id) AS acc_bs_id,
    COALESCE(t.acc_pl_id, c.pl_id) AS acc_pl_id,
    COALESCE(t.subconto_bs_id, c.subconto_bs_id) AS subconto_bs_id,
    COALESCE(t.subconto_pl_id, c.subconto_pl_id) AS subconto_pl_id,
    (t.param_json)::json AS params_json,
    (t.vat_json)::json AS vat_json
   FROM ((contracts_conditions t
     LEFT JOIN contracts_contracts c ON ((c.id = t.contract_id)))
     LEFT JOIN contracts_accuralfn f ON ((f.id = t.fn_id)));

CREATE OR REPLACE VIEW gl.ba_to_gl AS
WITH cf AS (
         SELECT uuid_generate_v5('21111111-1111-1111-1111-111111111111'::uuid, concat_ws('|'::text, mv_ba_distribution.row_id, (mv_ba_distribution.date_from)::text, mv_ba_distribution.description, 'CF')) AS id,
            NULL::uuid AS pid,
            mv_ba_distribution.date_from,
            mv_ba_distribution.acc_bs AS acc_id,
            mv_ba_distribution.contract_id,
            mv_ba_distribution.dt_bs AS dt,
            mv_ba_distribution.cr_bs AS cr,
            mv_ba_distribution.description,
            mv_ba_distribution.subconto_bs AS subconto_id,
            (1)::bigint AS company_id,
            'CF_BA'::text AS chapter
           FROM gl.mv_ba_distribution
          WHERE (mv_ba_distribution.acc_bs IS NOT NULL)
        UNION ALL
         SELECT uuid_generate_v5('21111111-1111-1111-1111-111111111111'::uuid, concat_ws('|'::text, grossbook_manual.id, (grossbook_manual.date)::text, grossbook_manual.temp, 'CF')) AS id,
            NULL::uuid AS pid,
            grossbook_manual.date AS date_from,
            grossbook_manual.acc_id,
            grossbook_manual.contract_id,
            ((grossbook_manual.dt * (100)::numeric))::bigint AS dt,
            ((grossbook_manual.cr * (100)::numeric))::bigint AS cr,
            grossbook_manual.temp AS description,
            grossbook_manual.cfitem_id AS subconto_id,
            grossbook_manual.owner_id AS company_id,
            'CF_BA'::text AS chapter
           FROM grossbook_manual
          WHERE (grossbook_manual.acc_id IN ( SELECT DISTINCT mv_ba_distribution.acc_bs
                   FROM gl.mv_ba_distribution))
        ), st AS (
         SELECT uuid_generate_v5('21111111-1111-1111-1111-111111111111'::uuid, concat_ws('|'::text, mv_ba_distribution.row_id, (mv_ba_distribution.date_from)::text, mv_ba_distribution.description, 'ST')) AS id,
            uuid_generate_v5('21111111-1111-1111-1111-111111111111'::uuid, concat_ws('|'::text, mv_ba_distribution.row_id, (mv_ba_distribution.date_from)::text, mv_ba_distribution.description, 'CF')) AS pid,
            mv_ba_distribution.date_from,
            mv_ba_distribution.acc_st AS acc_id,
            mv_ba_distribution.contract_id,
            mv_ba_distribution.dt_st AS dt,
            mv_ba_distribution.cr_st AS cr,
            concat_ws(' '::text, 'Оплата: ', 'Сч: ', mv_ba_distribution.acc_bs, ' сумма ', round((((mv_ba_distribution.dt_bs - mv_ba_distribution.cr_bs) / 100))::numeric, 2), ' руб на Сч ', mv_ba_distribution.acc_st) AS description,
            mv_ba_distribution.subconto_st AS subconto_id,
            (1)::bigint AS company_id,
            'ST_BA'::text AS chapter
           FROM gl.mv_ba_distribution
          WHERE (mv_ba_distribution.acc_st IS NOT NULL)
        UNION ALL
         SELECT uuid_generate_v5('21111111-1111-1111-1111-111111111111'::uuid, concat_ws('|'::text, grossbook_manual.id, (grossbook_manual.date)::text, grossbook_manual.temp, 'ST')) AS id,
            uuid_generate_v5('21111111-1111-1111-1111-111111111111'::uuid, concat_ws('|'::text, grossbook_manual.id, (grossbook_manual.date)::text, grossbook_manual.temp, 'CF')) AS pid,
            grossbook_manual.date AS date_from,
            grossbook_manual.acc_id,
            grossbook_manual.contract_id,
            ((grossbook_manual.dt * ((100)::bigint)::numeric))::bigint AS dt,
            ((grossbook_manual.cr * ((100)::bigint)::numeric))::bigint AS cr,
            grossbook_manual.temp AS description,
            grossbook_manual.cfitem_id AS subconto_id,
            grossbook_manual.owner_id AS company_id,
            'ST_BA'::text AS chapter
           FROM grossbook_manual
          WHERE (grossbook_manual.acc_id IN ( SELECT DISTINCT mv_ba_distribution.acc_st
                   FROM gl.mv_ba_distribution))
        ), pl AS (
         SELECT uuid_generate_v5('21111111-1111-1111-1111-111111111111'::uuid, concat_ws('|'::text, mv_ba_distribution.row_id, (mv_ba_distribution.date_from)::text, mv_ba_distribution.description, 'PL')) AS id,
            NULL::uuid AS pid,
            mv_ba_distribution.date_from,
            mv_ba_distribution.acc_pl AS acc_id,
            mv_ba_distribution.contract_id,
            mv_ba_distribution.dt_pl AS dt,
            mv_ba_distribution.cr_pl AS cr,
            concat_ws(' '::text, 'Курсовые разницы: ', 'Сч: ', mv_ba_distribution.acc_bs, ' сумма ', round((((mv_ba_distribution.dt_pl - mv_ba_distribution.cr_pl) / 100))::numeric, 2), ' руб на Сч ', mv_ba_distribution.acc_pl) AS description,
            mv_ba_distribution.subconto_pl AS subconto_id,
            (1)::bigint AS company_id,
            'PL_BA'::text AS chapter
           FROM gl.mv_ba_distribution
          WHERE (mv_ba_distribution.acc_pl IS NOT NULL)
        UNION ALL
         SELECT uuid_generate_v5('21111111-1111-1111-1111-111111111111'::uuid, concat_ws('|'::text, grossbook_manual.id, (grossbook_manual.date)::text, grossbook_manual.temp, 'PL')) AS id,
            NULL::uuid AS pid,
            grossbook_manual.date AS date_from,
            grossbook_manual.acc_id,
            grossbook_manual.contract_id,
            ((grossbook_manual.dt * (100)::numeric))::bigint AS dt,
            ((grossbook_manual.cr * (100)::numeric))::bigint AS cr,
            grossbook_manual.temp AS description,
            grossbook_manual.cfitem_id AS subconto_id,
            grossbook_manual.owner_id AS company_id,
            'PL_BA'::text AS chapter
           FROM grossbook_manual
          WHERE (grossbook_manual.acc_id IN ( SELECT DISTINCT mv_ba_distribution.acc_pl
                   FROM gl.mv_ba_distribution))
        )
 SELECT cf.id,
    cf.pid,
    cf.date_from,
    cf.acc_id,
    cf.contract_id,
    cf.dt,
    cf.cr,
    cf.description,
    cf.subconto_id,
    cf.company_id,
    cf.chapter
   FROM cf
UNION ALL
 SELECT pl.id,
    pl.pid,
    pl.date_from,
    pl.acc_id,
    pl.contract_id,
    pl.dt,
    pl.cr,
    pl.description,
    pl.subconto_id,
    pl.company_id,
    pl.chapter
   FROM pl;

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
    (x.dt - x.cr) AS amount
   FROM ((((((((( SELECT t.date_from,
            t.acc_id,
            t.subconto_id,
            t.contract_id,
            round(((t.dt)::numeric / 100.0), 2) AS dt,
            round(((t.cr)::numeric / 100.0), 2) AS cr,
            t.description
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
     LEFT JOIN counterparties_counterparty cp ON ((cp.id = c.cp_id)));

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
    regexp_replace(p.description, '[\n\r]+'::text, ' '::text, 'g'::text) AS description
   FROM (((((((gl.fact p
     LEFT JOIN contracts_contracts c ON ((c.id = p.contract_id)))
     LEFT JOIN contracts_contractstitle ct ON ((ct.id = c.title_id)))
     LEFT JOIN counterparties_counterparty cp ON ((cp.id = c.cp_id)))
     LEFT JOIN corporate_coa a ON ((a.id = p.acc_id)))
     LEFT JOIN corporate_coa ap ON ((ap.id = a.parent_id)))
     LEFT JOIN corporate_cfitems s ON ((s.id = p.subconto_id)))
     LEFT JOIN corporate_cfitems sp ON ((sp.id = s.parent_id)))
  WHERE ((ap.id = ANY (ARRAY[(25)::bigint, (26)::bigint, (27)::bigint])) AND (p.date_from <= CURRENT_DATE));
"""


class Migration(migrations.Migration):

    dependencies = [
        ("grossbook", "0007_gladjustment_cf"),
        ("corporate", "0017_owners_reporting_bank_country"),
    ]

    operations = [migrations.RunSQL(FORWARD, REVERSE)]
