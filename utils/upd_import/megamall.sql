-- делаем вьюху с мегамол упд
-- CREATE VIEW IF NOT EXISTS upd.megamall_raw AS
--     SELECT *
--     FROM read_parquet('/Users/daria/Documents/Projects/ts/data/megamall/*.parquet', union_by_name=true);


-- приводим нормальные название колонок и делаем таблицу для работы
DROP TABLE IF EXISTS upd.megamall_adjust;
CREATE or REPLACE VIEW upd.megamall_adjust as
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
        t.nm_pid,
        list(DISTINCT uc.tech_size)
            FILTER (WHERE uc.tech_size IS NOT NULL) AS available_sizes
    FROM cards.pids AS t
    LEFT JOIN cards.unpacked_cards AS uc
        ON uc.nm_id = t.nm_pid
    GROUP BY t.nm_pid
),

prefin AS (
    SELECT
        t.id,
        t.file_name,
        t.number,
        t.date_from,

        concat(
            'УПД №: ',
            t.number,
            ' от ',
            strftime(CAST(t.date_from AS DATE), '%d.%m.%Y')
        ) AS full_name,

        t.upd_pos,
        t.upd_sa_name,

        c.sa_pid,
        c.brand,

        t.upd_title,

        string_agg(DISTINCT cp.title, ' | ') AS cards_titles,

        COALESCE(
            nullif(trim(CAST(t.upd_size AS VARCHAR)), ''),
            CASE
                WHEN list_count(cz.available_sizes) = 1
                    THEN CAST(cz.available_sizes[1] AS VARCHAR)
                ELSE ''
            END
        ) AS upd_size,

        cz.available_sizes,

        t.upd_vat_rate,

        COALESCE(c.vat_rate, v.rate) AS card_vat_rate,

        c.cert_end_date,

        CASE
            WHEN c.cert_end_date < t.date_from
                THEN 'Просрочен сертификат'
            WHEN c.cert_end_date IS NULL
                THEN 'Нет сертификата'
            ELSE 'Ok'
        END AS cert_status

    FROM upd.megamall_adjust AS t

    LEFT JOIN cards.product AS c
        ON c.sa_pid = t.upd_sa_name

    LEFT JOIN cards.product AS cp
        ON cp.sa_name = c.sa_pid

    LEFT JOIN cards_sizes AS cz
        ON cz.nm_pid = c.nm_id

    LEFT JOIN main.vat AS v
        ON t.date_from >= v.date_from
       AND t.date_from < v.date_to

    GROUP BY
        t.id,
        t.file_name,
        t.number,
        t.date_from,
        t.upd_pos,
        t.upd_sa_name,
        c.sa_pid,
        c.brand,
        t.upd_title,
        upd_size,
        cz.available_sizes,
        t.upd_vat_rate,
        c.vat_rate,
        c.cert_end_date,
        card_vat_rate
)


SELECT
    t.id,
    t.file_name,
    t.full_name,

    t.upd_pos,
    t.upd_sa_name,
    t.sa_pid,

    CASE
        WHEN t.sa_pid IS NULL THEN FALSE
        ELSE TRUE
    END AS match_article,

    t.brand,

    t.upd_title,
    t.cards_titles,

    (
        lower(t.cards_titles) LIKE
        (
            '%' ||
            lower(regexp_extract(t.upd_title, '^([^\s]+)', 1))
            || '%'
        )
    ) AS name_match,

    t.upd_size,
    t.available_sizes,

    list_contains(t.available_sizes, t.upd_size) AS size_match,

    t.upd_vat_rate,
    t.card_vat_rate,

    (t.upd_vat_rate = t.card_vat_rate) AS match_vats,

    t.cert_end_date,
    t.cert_status,

    CASE
        WHEN t.cert_status = 'Ok'
            THEN CAST('t' AS BOOLEAN)
        ELSE CAST('f' AS BOOLEAN)
    END AS cert_match,

    s.upd_unit,
    s.upd_qty,
    s.upd_price_vatless,
    s.upd_amount_vatless,
    s.upd_vat_amount,
    s.upd_amount_vatadd,

    s.supplier,
    s.date_from,
    s.number

FROM prefin AS t

LEFT JOIN upd.megamall_adjust AS s
    ON s.id = t.id;



select
date_from,
field,
btn,
val / 100 as amount
 from sales.sales_long
where field = 'deduction'
and date_from <= '2025-01-01' and val < 0
order by date_from;


-- нормализированные упд для импорта в базу данных
select distinct nm_id, chrt_id, tech_size from cards.sizes;

select distinct 
"date_from",
"number",

from upd.megamall_vs_cards;


with a as 
(
select id, number, date
from read_csv('/Users/pavelustenko/Downloads/cards_upddocument.csv')
)
select 

t.upd_pos::int as upd_pos,
t.brand,
t."upd_sa_name",
t.upd_title,
null as proposed_articles, -- это список
t.name_match,
t."upd_size",
t.available_sizes,
t.upd_vat_rate,
t.card_vat_rate,
t.upd_unit,
t.upd_qty::double as upd_qty,
t.upd_price_vatless::double as upd_price_vatless,
t.upd_amount_vatless::double as upd_amount_vatless,
t.upd_vat_amount::double as upd_vat_amount,
t.upd_amount_vatadd::double as upd_amount_vatadd,
null::double as man_cost_per_unit,
'RUB'::text as currency_code,
s."chrt_id",
c."nm_id"::bigint as nm_id,
a.id::bigint as upd_document_id
from upd.megamall_vs_cards t
left join cards.product as c on c.sa_name = t.upd_sa_name
left join cards.sizes s on s.nm_id = c.nm_id and s.tech_size = t.upd_size
left join a on a.number = t.number and a.date = t.date_from;

ATTACH '
dbname=ts_db
host=127.0.0.1
port=5433
user=ts_user
password=Dec8108079
' AS pg (TYPE postgres);


-- INSERT INTO pg.public.upd_income_lines (

--     upd_pos,
--     brand,
--     upd_sa_name,
--     upd_title,
--     proposed_articles,
--     name_match,
--     upd_size,
--     available_sizes,
--     upd_vat_rate,
--     card_vat_rate,
--     upd_unit,
--     upd_qty,
--     upd_price_vatless,
--     upd_amount_vatless,
--     upd_vat_amount,
--     upd_amount_vatadd,
--     man_cost_per_unit,
--     currency_code,
--     chrt_id,
--     nm_id,
--     upd_document_id

-- )

-- WITH a AS (

--     SELECT
--         id,
--         number,
--         date

--     FROM read_csv(
--         '/Users/pavelustenko/Downloads/cards_upddocument.csv',
--         AUTO_DETECT=TRUE
--     )

-- )

-- SELECT

--     t.upd_pos::int as upd_pos,

--     t.brand,

--     t.upd_sa_name,

--     t.upd_title,

--     null as proposed_articles,

--     t.name_match,

--     t.upd_size,

--     t.available_sizes,

--     t.upd_vat_rate::double as upd_vat_rate,

--     t.card_vat_rate::double as card_vat_rate,

--     t.upd_unit,

--     t.upd_qty::double as upd_qty,

--     t.upd_price_vatless::double as upd_price_vatless,

--     t.upd_amount_vatless::double as upd_amount_vatless,

--     t.upd_vat_amount::double as upd_vat_amount,

--     t.upd_amount_vatadd::double as upd_amount_vatadd,

--     null::double as man_cost_per_unit,

--     'RUB'::text as currency_code,

--     s.chrt_id,

--     c.nm_id::bigint as nm_id,

--     a.id::bigint as upd_document_id

-- FROM upd.megamall_vs_cards t

-- LEFT JOIN cards.product c
--     ON c.sa_name = t.upd_sa_name

-- LEFT JOIN cards.sizes s
--     ON s.nm_id = c.nm_id
--    AND s.tech_size = t.upd_size

-- LEFT JOIN a
--     ON a.number = t.number
--    AND a.date = t.date_from;


