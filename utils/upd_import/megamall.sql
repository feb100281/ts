-- делаем вьюху с мегамол упд
CREATE VIEW IF NOT EXISTS upd.megamall_raw AS
    SELECT *
    FROM read_parquet('/Users/daria/Documents/Projects/ts/data/megamall/*.parquet', union_by_name=true);


-- приводим нормальные название колонок и делаем таблицу для работы
CREATE or REPLACE TABLE upd.megamall_adjust as
select 
row_number() over () as id,
"file_name",
"date"::date as date_from,
"number",
"supplier",
"1"::int as upd_pos,
"1а" as upd_title,
trim(split_part("А", ' - ', 1)) AS upd_sa_name,
null::text as upd_color,
trim(split_part("А", ' - ', 2)) AS upd_size,
trim("2а") as upd_unit,
"3"::double as upd_qty,
"4"::double as upd_price_vatless,
"5"::double as upd_amount_vatless,
REPLACE("7",'%','')::double as upd_vat_rate,
"8"::double as upd_vat_amount,
"9"::double as upd_amount_vatadd,
"10" as "Код станы",
"10а" as "Страна",
"11" as "Номер декларации",
"1б" as "Код товара"

from upd.megamall_raw
WHERE "А" not in (
    'Код товара/ работ, услуг',
    'А'
);

-- Проверяем как встали УПД
select 
"file_name",
"number",
"date_from",
max("upd_pos"),
sum("upd_qty"),
sum("upd_amount_vatless"),
sum("upd_vat_amount"),
sum("upd_amount_vatadd")
from upd.megamall_adjust 
group by "file_name",
"number",
"date_from";

-- начинаем самое интересное искать говнецо
-- SET memory_limit='4GB';

-- SET threads=2;

-- SET preserve_insertion_order=false;

CREATE OR REPLACE VIEW upd.megamall_vs_cards as 
WITH cards_sizes AS (
    SELECT
        t."nm_pid",
        list(DISTINCT uc.tech_size) FILTER (WHERE uc.tech_size IS NOT NULL) AS available_sizes
    FROM cards.pids t
    LEFT JOIN cards.unpacked_cards uc
        ON uc.nm_id = t.nm_pid
    GROUP BY
        t."nm_pid"
),
prefin as (
SELECT 
    t."id", 
    t."file_name",
    t."number",
    CONCAT(
        'УПД №: ',
        t."number",
        ' от ',
        strftime(t."date_from"::DATE, '%d.%m.%Y')
    ) AS full_name,
    t."upd_pos",
    t."upd_sa_name",
    c.sa_pid,
    t."upd_title",
    string_agg(DISTINCT cp.title, ' | ') AS cards_titles,
    t."upd_size",
    cz.available_sizes,
    t.upd_vat_rate,
    COALESCE(c.vat_rate,22) as card_vat_rate, -- нужно потом переделать !!!!
    c.cert_end_date,
    case when c.cert_end_date < t.date_from then 'Просрочен сертификат' else null end as cert_status
FROM upd.megamall_adjust t
LEFT JOIN cards.product c
    ON c.sa_pid = t.upd_sa_name
LEFT JOIN cards.product cp
    ON cp.sa_name = c.sa_pid
LEFT JOIN cards_sizes cz
    ON cz.nm_pid = c.nm_id
GROUP BY
    t."id", 
    t."file_name",
    t."number",
    t."date_from",
    t."upd_pos",
    t."upd_sa_name",
    c.sa_pid,
    t."upd_title",
    t."upd_size",
    cz.available_sizes,
    t.upd_vat_rate,
    c.vat_rate,
    c.cert_end_date
)
select 
id,
file_name,
full_name,
upd_pos,
upd_sa_name,
sa_pid,
upd_title,
cards_titles,
lower(cards_titles) LIKE
        '%' || lower(regexp_extract(upd_title, '^([^\s]+)', 1)) || '%'
        AS name_match,
upd_size,
available_sizes,
LIST_CONTAINS(available_sizes,upd_size) as size_match,
upd_vat_rate,
card_vat_rate,
upd_vat_rate = card_vat_rate as match_vats


from prefin


