CREATE or replace table upd.upd_2024_adjust as
select
row_number() over () as id,
file_name,
number,
date,
supplier,
"№" as upd_pos,
COALESCE(
"Наименование товара (описание выполненных работ, оказанных услуг), имущественного права (описание выполненных работ, оказанных услуг), имущественного права",
COALESCE("Наименование товара
(описание выполненных
работ, оказанных услуг), имущественного права
(описание выполненных
работ, оказанных услуг), имущественного права",
"Наименование товара (описание выполненных работ, оказанных услуг), имущественного права")
) as upd_title,
"Артикул" as upd_sa_name,
"Цвет" as upd_color,
COALESCE("Размеры","Размер") as upd_size,
"Единица измерения" as upd_unit,
"Коли-
чество
(объем)"::double as upd_qty,
COALESCE(
"Цена (тариф) за единицу измерения
(тариф) за единицу измерения",
COALESCE(
"Цена (тариф) за единицу измерения",
"Цена (тариф)
за единицу измерения
(тариф)
за единицу измерения"
)
)::double as upd_price_vatless,
COALESCE(
"Стоимость товаров (работ, услуг), имущественных прав, без налога - всего",
"Стоимость товаров (работ, услуг), имущественных прав с налогом - всего"
)::double as upd_amount_vatless,
replace("Налоговая ставка"::text, '%', '')::double as upd_vat_rate,
COALESCE(
"Сумма налога,
предъявляемая покупателю налога,
предъявляемая покупателю",
"Стоимость товаров (работ, услуг), имущественных прав с налогом - всего"
)::double as upd_vat_amount,
"Стоимость товаров (работ, услуг), имущественных прав с налогом - всего"::double as upd_amount_vatadd,
handle_art
from upd.upd_raw_2024
order by file_name, number, date::date, upd_title;


CREATE OR REPLACE VIEW  upd.megamall_vs_cards AS WITH cards_sizes AS (SELECT t.nm_pid, list(DISTINCT uc.tech_size) FILTER (WHERE (uc.tech_size IS NOT NULL)) AS available_sizes FROM cards.pids AS t LEFT JOIN cards.unpacked_cards AS uc ON ((uc.nm_id = t.nm_pid)) GROUP BY t.nm_pid), prefin AS (SELECT t.id, t.file_name, t.number, t.date_from, concat('УПД №: ', t.number, ' от ', strftime(CAST(t.date_from AS DATE), '%d.%m.%Y')) AS full_name, t.upd_pos, t.upd_sa_name, c.sa_pid, c.brand, t.upd_title, string_agg(DISTINCT cp.title, ' | ') AS cards_titles, COALESCE("nullif"(main."trim"(CAST(t.upd_size AS VARCHAR)), ''), CASE  WHEN ((list_count(cz.available_sizes) = 1)) THEN (CAST(cz.available_sizes[1] AS VARCHAR)) ELSE '' END) AS upd_size, cz.available_sizes, t.upd_vat_rate, COALESCE(c.vat_rate, v.rate) AS card_vat_rate, c.cert_end_date, CASE  WHEN ((c.cert_end_date < t.date_from)) THEN ('Просрочен сертификат') WHEN ((c.cert_end_date IS NULL)) THEN ('Нет сертификата') ELSE 'Ok' END AS cert_status FROM upd.megamall_adjust AS t LEFT JOIN cards.product AS c ON ((c.sa_pid = t.upd_sa_name)) LEFT JOIN cards.product AS cp ON ((cp.sa_name = c.sa_pid)) LEFT JOIN cards_sizes AS cz ON ((cz.nm_pid = c.nm_id)) LEFT JOIN main.vat AS v ON (((t.date_from >= v.date_from) AND (t.date_from < v.date_to))) GROUP BY t.id, t.file_name, t.number, t.date_from, t.upd_pos, t.upd_sa_name, c.sa_pid, c.brand, t.upd_title, upd_size, cz.available_sizes, t.upd_vat_rate, c.vat_rate, c.cert_end_date, card_vat_rate)SELECT t.id, t.file_name, t.full_name, t.upd_pos, t.upd_sa_name, t.sa_pid, case when t.sa_pid is null then false else true end as match_article, t.brand, t.upd_title, t.cards_titles, (lower(t.cards_titles) ~~ (('%' || lower(regexp_extract(t.upd_title, '^([^\s]+)', 1))) || '%')) AS name_match, t.upd_size, t.available_sizes, list_contains(t.available_sizes, t.upd_size) AS size_match, t.upd_vat_rate, t.card_vat_rate, (t.upd_vat_rate = t.card_vat_rate) AS match_vats, t.cert_end_date, t.cert_status, CASE  WHEN ((t.cert_status = 'Ok')) THEN (CAST('t' AS BOOLEAN)) ELSE CAST('f' AS BOOLEAN) END AS cert_match, s.upd_unit, s.upd_qty, s.upd_price_vatless, s.upd_amount_vatless, s.upd_vat_amount, s.upd_amount_vatadd, s.supplier, s.date_from, s.number FROM prefin AS t LEFT JOIN upd.megamall_adjust AS s ON ((s.id = t.id));



SELECT

    round(sum(cr) / 100.0, 2) AS cogs

FROM inventories.inv_gl_final

WHERE date_from >= DATE '2026-03-01'

  AND date_from < DATE '2026-04-01';



