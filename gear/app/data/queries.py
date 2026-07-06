### ---------
### Сюда пихаем запросы что бы не было ада в классе dashboard
### ---------

#### БАЗОВЫЙ ЗАПРОС НА СОЗДАНИЕ ВРЕМЕННОЙ ТАБЛИЦЫ 

BASE_QUERY = """ 
CREATE OR REPLACE TEMP TABLE base as
with last_val as (
select
usk,
adjust_wo[-1] as last_cr,
adjust_man_wo[-1] as last_man_cr
from inventories.pre_wo
),
-- выбираем списания 
add_last as (select
t.*,
l.last_cr,
l.last_man_cr
from inventories.inv_gl_final t
left join last_val l on l.usk = t.usk 
where t.cr = 0 and t.oper = 'Списание'
),
wb_price as (
select 
rrd_id, val
from sales.sales_long
where field = 'retail_amount'
)

select 
yearweek(t.date_from::date) as yw,
t.*,
wb.val as retail_amount,
a.last_cr,
a.last_man_cr,
COALESCE(a.last_cr, case when t.cr=0 then 95000 else t.cr end) as adjusted_cogs,
COALESCE(a.last_man_cr, case when t.cr_man=0 then 62000 else t.cr_man end) as adjusted_cogs_man,
UPPER(w.brand) as brand,
w.subject_id,
w.subject_name,
w.title,
COALESCE(w.gender, 'Не указан') as gender,
case 
when t.cr = 0 and a.last_cr <> 0 and t.oper = 'Списание' then 'Нет на складе'
when t.cr = 0 and a.last_cr is null and t.oper = 'Списание' then 'Нет приходов'
else null
end as storage_flag
from inventories.inv_gl_final t
left join add_last a on a.rrd_id = t.rrd_id
LEFT JOIN inventories.wb_product w on w.card_id = t.usk
left join wb_price as wb on wb.rrd_id = t.rrd_id
;
"""

DAILY_SALES_AGG = """ 
with a as (
select 
rrd_id,
COALESCE(sum(val) filter (where field = 'comission' and oper = 'dt'),0) -
COALESCE(sum(val) filter (where field = 'comission' and oper = 'cr')) as gross_comission,
COALESCE(sum(val / (100+vat_rate)*100) filter (where field = 'comission' and oper = 'dt'),0) -
COALESCE(sum(val/ (100+vat_rate)*100) filter (where field = 'comission' and oper = 'cr')) as net_comission
from sales.sales_long
group by rrd_id
),
d as (
SELECT
yw,
count(cr_rev) as rev_count
from base
where cr_rev <> 0
group by yw
),
f as (
select
yw,
sum(dt / (100+vat_rate)*100) -
sum(cr / (100+vat_rate)*100)
as costs
from wb_costs
group by yw
),
g as (
select
d.yw,
abs(f.costs) / d.rev_count as cost_per_sold
from d 
left join f on f.yw = d.yw
)
select
x.date_from,
round(amount/100.00,2) as amount,
round(retail_amount/100.00,2) as retail_amount,
round((amount-retail_amount)/amount*100,2) as wb_discount,
round(vat_amount/100.00,2) as vat_amount,
round(amount_vatless/100.00,2) as amount_vatless,
round(cogs/100.00,2) as cogs,
round(cogs_man/100.00,2) as cogs_man,
round(net_comission/100.00,2) as net_comission,
round(
    (amount_vatless-cogs+net_comission)/100.00,2
) as margin,
round(
    (amount_vatless-cogs_man+net_comission)/100.00,2
) as margin_man,
total_net_sales,
no_cost,
no_stocks,
no_income,
round(cogs_man / amount_vatless * 100,2) as cogs_man_share,
round(-net_comission / amount_vatless * 100,2) as commision_percent,
round((amount_vatless-cogs_man+net_comission) / amount_vatless * 100,2) as margin_percent,
round(g.cost_per_sold/100.0,2) as cost_per_sold,
ROUND(total_net_sales*g.cost_per_sold/100.0,2) as wb_costs,
ROUND(
    ((amount_vatless-cogs_man+net_comission)-
    (total_net_sales*g.cost_per_sold)) / 100.0,2
) as wb_result


from(

select  
t.date_from,
sum(cr_rev) as amount,
sum(retail_amount) as retail_amount,
sum(cr_rev) -
sum(cr_rev / (100+vat_rate) * 100) as vat_amount,
sum(cr_rev / (100+vat_rate) * 100) as amount_vatless,
sum(adjusted_cogs) as cogs,    
sum(adjusted_cogs_man) as cogs_man,
count(cr_rev) as total_net_sales,
count(cr_rev) filter (where cr =0) as no_cost,
count(cr_rev) filter (where storage_flag ='Нет на складе') as no_stocks,
count(cr_rev) filter (where storage_flag ='Нет приходов') as no_income,
sum(a.net_comission) as net_comission,

from base t    
left join a on a.rrd_id = t.rrd_id
where cr_rev <> 0     
and date_from BETWEEN ? and ?
{filters}                  
group by t.date_from
) x
left join g on g.yw = yearweek(x.date_from::date)
order by x.date_from DESC
;
"""

DETAILS_DAY = """ 
with a as (
select 
rrd_id,
COALESCE(sum(val) filter (where field = 'comission' and oper = 'dt'),0) -
COALESCE(sum(val) filter (where field = 'comission' and oper = 'cr')) as gross_comission,
COALESCE(sum(val / (100+vat_rate)*100) filter (where field = 'comission' and oper = 'dt'),0) -
COALESCE(sum(val/ (100+vat_rate)*100) filter (where field = 'comission' and oper = 'cr')) as net_comission
from sales.sales_long
group by rrd_id
)
select
x.usk,
brand,
subject_name,
title,
round(amount/100.00,2) as amount,
round(retail_amount/100.00,2) as retail_amount,
round((amount-retail_amount)/amount*100,2) as wb_discount,
round(vat_amount/100.00,2) as vat_amount,
round(amount_vatless/100.00,2) as amount_vatless,
round(cogs/100.00,2) as cogs,
round(cogs_man/100.00,2) as cogs_man,
round(net_comission/100.00,2) as net_comission,
round(
    (amount_vatless-cogs+net_comission)/100.00,2
) as margin,
round(
    (amount_vatless-cogs_man+net_comission)/100.00,2
) as margin_man,
total_net_sales,
no_cost,
no_stocks,
no_income,
round(cogs_man / amount_vatless * 100,2) as cogs_man_share,
round(-net_comission / amount_vatless * 100,2) as commision_percent,
round((amount_vatless-cogs_man+net_comission) / amount_vatless * 100,2) as margin_percent

from(

select  
usk,
brand,
subject_name,
title,
sum(cr_rev) as amount,
sum(retail_amount) as retail_amount,
sum(cr_rev) -
sum(cr_rev / (100+vat_rate) * 100) as vat_amount,
sum(cr_rev / (100+vat_rate) * 100) as amount_vatless,
sum(adjusted_cogs) as cogs,    
sum(adjusted_cogs_man) as cogs_man,
count(cr_rev) as total_net_sales,
count(cr_rev) filter (where cr =0) as no_cost,
count(cr_rev) filter (where storage_flag ='Нет на складе') as no_stocks,
count(cr_rev) filter (where storage_flag ='Нет приходов') as no_income,
sum(a.net_comission) as net_comission,

from base t    
left join a on a.rrd_id = t.rrd_id
where cr_rev <> 0     
and date_from = ?  
{filters}                
group by usk,
brand,
subject_name,
title
) x
ORDER BY x.amount DESC
;
"""

BASE_WB_COSTS = """ 
CREATE OR REPLACE TEMP TABLE wb_costs as
with wb_costs as (
select
date_from,
rrd_id,
'Other income / loss' as account,
sop_name as cost_item,
COALESCE(sum(val) filter (where oper='dt' ),0) as dt,
COALESCE(sum(val) filter (where oper='cr' ),0) as cr
from sales.sales_long
where field = 'retail_price' and sop_name like '%оррекция%'
GROUP BY date_from, rrd_id, sop_name
UNION ALL
select
date_from,
rrd_id,
'WB Logistic' as account,
COALESCE(btn,sop_name) as cost_item,
COALESCE(sum(val) filter (where oper='dt' ),0) as dt,
COALESCE(sum(val) filter (where oper='cr' ),0) as cr
from sales.sales_long
where field = 'delivery_rub' -- and sop_name like '%оррекция%'
GROUP BY date_from, rrd_id, COALESCE(btn,sop_name)
UNION ALL
select
date_from,
rrd_id,
'WB Storage' as account,
sop_name as cost_item,
COALESCE(sum(val) filter (where oper='dt' ),0) as dt,
COALESCE(sum(val) filter (where oper='cr' ),0) as cr
from sales.sales_long
where field = 'storage_fee' -- and sop_name like '%оррекция%'
GROUP BY date_from, rrd_id, sop_name
UNION ALL
select
date_from,
rrd_id,
'WB Acceptance' as account,
sop_name as cost_item,
COALESCE(sum(val) filter (where oper='dt' ),0) as dt,
COALESCE(sum(val) filter (where oper='cr' ),0) as cr
from sales.sales_long
where field = 'acceptance' -- and sop_name like '%оррекция%'
GROUP BY date_from, rrd_id, sop_name
UNION ALL
select
date_from,
rrd_id,
'WB Penalties' as account,
btn as cost_item,
COALESCE(sum(val) filter (where oper='dt' ),0) as dt,
COALESCE(sum(val) filter (where oper='cr' ),0) as cr
from sales.sales_long
where field = 'penalty' -- and sop_name like '%оррекция%'
GROUP BY date_from, rrd_id, btn
UNION ALL
select
date_from,
rrd_id,
'WB Deduction' as account,
case 
when STARTS_WITH(btn, 'Списание за отзыв')  then 'Отзывы'
when STARTS_WITH(btn, 'Оказание услуг') 
or STARTS_WITH(btn,'Предоставление услуг') 
or STARTS_WITH(btn,'Витрина Магазина') then 'Услуги WB'
else 'Прочее' end as cost_item,
COALESCE(sum(val) filter (where oper='dt' ),0) as dt,
COALESCE(sum(val) filter (where oper='cr' ),0) as cr
from sales.sales_long
where field = 'deduction' 
and (not STARTS_WITH(btn,'Платеж') or not STARTS_WITH(btn, 'Перевод'))
and btn is not null
-- and sop_name like '%оррекция%'
GROUP BY date_from, rrd_id, cost_item
UNION ALL
select
date_from,
rrd_id,
'WB Loyality' as account,
btn as cost_item,
COALESCE(sum(val) filter (where oper='dt' ),0) as dt,
COALESCE(sum(val) filter (where oper='cr' ),0) as cr
from sales.sales_long
where field in('cashback_commission_change','cashback_amount') -- and sop_name like '%оррекция%'
GROUP BY date_from, rrd_id, btn
)
select 
yearweek(t.date_from::date) as yw,
t.*,
s.vat_rate
from wb_costs t
left join sales.sales_long s on s.rrd_id = t.rrd_id;
"""