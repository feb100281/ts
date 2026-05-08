-- делаем табличку upd_2025_adjust
CREATE OR REPLACE TABLE upd.upd_2025_adjust as
select 
row_number() over () as id,
"file_name",
"date"::date as date_from,
"number",
"supplier",
"№"::int as upd_pos,
"Наименование товара (описание выполненных работ, оказанных услуг), имущественного права" as upd_title,
trim("Артикул") as upd_sa_name,
p.sa_name,
"Цвет" as upd_color,
trim("Размеры") as upd_size,
"Единица измерения" as upd_unit,
"Коли-
чество
(объем)"::double as upd_qty,
"Цена (тариф) за единицу измерения"::double as upd_price_vatless,
"Стоимость товаров (работ, услуг), имущественных прав, без налога - всего"::double as upd_amount_vatless,
REPLACE("Налоговая ставка",'%','')::double as upd_vat_rate,
"Сумма налога,
предъявляемая покупателю"::double as upd_vat_amount,
"Стоимость товаров (работ, услуг), имущественных прав с налогом - всего"::double as upd_amount_vatadd,
from upd.upd_raw 
left join cards.product p on p.sa_name = trim("Артикул");



-- Находим варианты замены артиклей и меняем их нахер
update upd.upd_2025_adjust as t
set sa_name = (
    select min(pa.sa_name)
    from (
        select distinct sa_name
        from cards.product
    ) pa
    where pa.sa_name like t.upd_sa_name || '%'
)
where not exists (
    select 1
    from cards.product p
    where p.sa_name = t.upd_sa_name
)
and (
    select count(distinct pa.sa_name)
    from cards.product pa
    where pa.sa_name like t.upd_sa_name || '%'
) = 1;

select * from cards.pids where sa_name = 'MC/CC107';

select * from cards.unpacked_cards where nm_id = 884140954;

SELECT * FROM "analytics"."cards"."cards_raw" where nm_id = 884141219;

select * from cards.unpacked_cards where tech_size in ('1-2');

select * from upd.upd_2025_adjust where upd_size in ('1-2');

