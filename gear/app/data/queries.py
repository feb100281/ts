# # gear/app/data/queries.py
# ### ---------
# ### Сюда пихаем запросы что бы не было ада в классе dashboard
# ### ---------

# #### БАЗОВЫЙ ЗАПРОС НА СОЗДАНИЕ ВРЕМЕННОЙ ТАБЛИЦЫ 

# BASE_QUERY = """ 
# CREATE OR REPLACE TEMP TABLE base as
# with last_val as (
# select
# usk,
# adjust_wo[-1] as last_cr,
# adjust_man_wo[-1] as last_man_cr
# from inventories.pre_wo
# ),
# -- выбираем списания 
# add_last as (select
# t.*,
# l.last_cr,
# l.last_man_cr
# from inventories.inv_gl_final t
# left join last_val l on l.usk = t.usk 
# where t.cr = 0 and t.oper = 'Списание'
# ),
# wb_price as (
# select 
# rrd_id, val
# from sales.sales_long
# where field = 'retail_amount'
# )

# select 
# yearweek(t.date_from::date) as yw,
# t.*,
# wb.val as retail_amount,
# a.last_cr,
# a.last_man_cr,
# COALESCE(a.last_cr, case when t.cr=0 then 95000 else t.cr end) as adjusted_cogs,
# COALESCE(a.last_man_cr, case when t.cr_man=0 then 62000 else t.cr_man end) as adjusted_cogs_man,
# UPPER(w.brand) as brand,
# w.subject_id,
# w.subject_name,
# w.title,
# COALESCE(w.gender, 'Не указан') as gender,
# case 
# when t.cr = 0 and a.last_cr <> 0 and t.oper = 'Списание' then 'Нет на складе'
# when t.cr = 0 and a.last_cr is null and t.oper = 'Списание' then 'Нет приходов'
# else null
# end as storage_flag
# from inventories.inv_gl_final t
# left join add_last a on a.rrd_id = t.rrd_id
# LEFT JOIN inventories.wb_product w on w.card_id = t.usk
# left join wb_price as wb on wb.rrd_id = t.rrd_id
# ;
# """


# BASE_STOCKS = """
# CREATE OR REPLACE TEMP TABLE stocks_daily AS

# SELECT
#     t.date_from::DATE AS stock_date,

#     /*
#     NM ID — основной ключ остатков.

#     Он есть в исходном отчёте WB даже тогда,
#     когда товар ещё не сопоставлен с USK.
#     */
#     t.nm_id,

#     /*
#     USK может отсутствовать.
#     Отсутствие USK не должно удалять остаток.
#     */
#     u.usk,

#     UPPER(w.brand) AS brand,
#     w.subject_id,
#     w.subject_name,
#     w.title,
#     COALESCE(w.gender, 'Не указан') AS gender,

#     SUM(
#         COALESCE(t.quantity, 0)
#         + COALESCE(t.in_way_from_client, 0)
#         + COALESCE(t.in_way_to_client, 0)
#     ) AS stock_quantity,

#     SUM(
#         COALESCE(t.quantity, 0)
#     ) AS warehouse_quantity,

#     SUM(
#         COALESCE(t.in_way_from_client, 0)
#         + COALESCE(t.in_way_to_client, 0)
#     ) AS in_transit_quantity

# FROM stocks.unpacked_stocks t

# LEFT JOIN inventories.usk u
#     ON u.card_id = t.nm_id

# LEFT JOIN inventories.wb_product w
#     ON w.card_id = t.nm_id

# /*
# ВАЖНО:

# Здесь больше нет:

#     WHERE u.usk IS NOT NULL

# Поэтому товары без USK сохраняются.
# */

# GROUP BY
#     t.date_from::DATE,
#     t.nm_id,
#     u.usk,
#     UPPER(w.brand),
#     w.subject_id,
#     w.subject_name,
#     w.title,
#     COALESCE(w.gender, 'Не указан')
# ;
# """




# DAILY_SALES_AGG = """
# WITH commissions AS (
#     SELECT
#         rrd_id,

#         COALESCE(
#             SUM(
#                 val / (100 + vat_rate) * 100
#             ) FILTER (
#                 WHERE field = 'comission'
#                   AND oper = 'dt'
#             ),
#             0
#         )
#         -
#         COALESCE(
#             SUM(
#                 val / (100 + vat_rate) * 100
#             ) FILTER (
#                 WHERE field = 'comission'
#                   AND oper = 'cr'
#             ),
#             0
#         ) AS net_comission

#     FROM sales.sales_long
#     GROUP BY rrd_id
# ),

# sales_by_day AS (
#     SELECT
#         t.date_from::DATE AS date_from,

#         SUM(t.cr_rev) AS amount,
#         SUM(t.retail_amount) AS retail_amount,

#         SUM(t.cr_rev)
#         -
#         SUM(
#             t.cr_rev / (100 + t.vat_rate) * 100
#         ) AS vat_amount,

#         SUM(
#             t.cr_rev / (100 + t.vat_rate) * 100
#         ) AS amount_vatless,

#         SUM(t.adjusted_cogs) AS cogs,
#         SUM(t.adjusted_cogs_man) AS cogs_man,

#         SUM(
#             CASE
#                 WHEN t.cr_rev > 0 THEN 1
#                 WHEN t.cr_rev < 0 THEN -1
#                 ELSE 0
#             END
#         ) AS total_net_sales,

#         COUNT(*) FILTER (
#             WHERE t.cr = 0
#         ) AS no_cost,

#         COUNT(*) FILTER (
#             WHERE t.storage_flag = 'Нет на складе'
#         ) AS no_stocks,

#         COUNT(*) FILTER (
#             WHERE t.storage_flag = 'Нет приходов'
#         ) AS no_income,

#         SUM(c.net_comission) AS net_comission

#     FROM base t

#     LEFT JOIN commissions c
#         ON c.rrd_id = t.rrd_id

#     WHERE t.cr_rev <> 0

#       AND t.date_from::DATE
#           BETWEEN ?::DATE AND ?::DATE

#       {filters}

#     GROUP BY
#         t.date_from::DATE
# ),

# sales_count_by_week AS (
#     SELECT
#         YEARWEEK(t.date_from::DATE) AS yw,

#         SUM(
#             CASE
#                 WHEN t.cr_rev > 0 THEN 1
#                 WHEN t.cr_rev < 0 THEN -1
#                 ELSE 0
#             END
#         ) AS rev_count

#     FROM base t

#     WHERE t.cr_rev <> 0

#     GROUP BY
#         YEARWEEK(t.date_from::DATE)
# ),

# wb_costs_by_week AS (
#     SELECT
#         yw,

#         SUM(
#             dt / (100 + vat_rate) * 100
#         )
#         -
#         SUM(
#             cr / (100 + vat_rate) * 100
#         ) AS costs

#     FROM wb_costs

#     GROUP BY yw
# ),

# cost_per_sale AS (
#     SELECT
#         s.yw,

#         CASE
#             WHEN COALESCE(s.rev_count, 0) = 0
#                 THEN NULL
#             ELSE ABS(w.costs) / s.rev_count
#         END AS cost_per_sold

#     FROM sales_count_by_week s

#     LEFT JOIN wb_costs_by_week w
#         ON w.yw = s.yw
# ),

# stock_by_day AS (
#     SELECT
#         t.stock_date,

#         SUM(t.stock_quantity) AS ending_stock,
#         SUM(t.warehouse_quantity) AS ending_warehouse_stock,
#         SUM(t.in_transit_quantity) AS ending_in_transit_stock

#     FROM stocks_daily t

#     WHERE t.stock_date
#           BETWEEN ?::DATE AND ?::DATE

#       {stock_filters}

#     GROUP BY t.stock_date
# )

# SELECT
#     s.date_from,

#     ROUND(
#         s.amount / 100.00,
#         2
#     ) AS amount,

#     ROUND(
#         s.retail_amount / 100.00,
#         2
#     ) AS retail_amount,

#     ROUND(
#         CASE
#             WHEN s.amount = 0 THEN NULL
#             ELSE (
#                 s.amount - s.retail_amount
#             ) / s.amount * 100
#         END,
#         2
#     ) AS wb_discount,

#     ROUND(
#         s.vat_amount / 100.00,
#         2
#     ) AS vat_amount,

#     ROUND(
#         s.amount_vatless / 100.00,
#         2
#     ) AS amount_vatless,

#     ROUND(
#         s.cogs / 100.00,
#         2
#     ) AS cogs,

#     ROUND(
#         s.cogs_man / 100.00,
#         2
#     ) AS cogs_man,

#     ROUND(
#         s.net_comission / 100.00,
#         2
#     ) AS net_comission,

#     ROUND(
#         (
#             s.amount_vatless
#             - s.cogs
#             + s.net_comission
#         ) / 100.00,
#         2
#     ) AS margin,

#     ROUND(
#         (
#             s.amount_vatless
#             - s.cogs_man
#             + s.net_comission
#         ) / 100.00,
#         2
#     ) AS margin_man,

#     s.total_net_sales,
#     s.no_cost,
#     s.no_stocks,
#     s.no_income,

#     ROUND(
#         CASE
#             WHEN s.amount_vatless = 0 THEN NULL
#             ELSE s.cogs_man
#                  / s.amount_vatless
#                  * 100
#         END,
#         2
#     ) AS cogs_man_share,

#     ROUND(
#         CASE
#             WHEN s.amount_vatless = 0 THEN NULL
#             ELSE -s.net_comission
#                  / s.amount_vatless
#                  * 100
#         END,
#         2
#     ) AS commision_percent,

#     ROUND(
#         CASE
#             WHEN s.amount_vatless = 0 THEN NULL
#             ELSE (
#                 s.amount_vatless
#                 - s.cogs_man
#                 + s.net_comission
#             ) / s.amount_vatless * 100
#         END,
#         2
#     ) AS margin_percent,

#     ROUND(
#         cp.cost_per_sold / 100.00,
#         2
#     ) AS cost_per_sold,

#     ROUND(
#         s.total_net_sales
#         * cp.cost_per_sold
#         / 100.00,
#         2
#     ) AS wb_costs,

#     ROUND(
#         (
#             (
#                 s.amount_vatless
#                 - s.cogs_man
#                 + s.net_comission
#             )
#             -
#             (
#                 s.total_net_sales
#                 * cp.cost_per_sold
#             )
#         ) / 100.00,
#         2
#     ) AS wb_result,

#     st.stock_date AS ending_stock_date,
#     st.ending_stock,
#     st.ending_warehouse_stock,
#     st.ending_in_transit_stock,

#     ROUND(
#         CASE
#             WHEN COALESCE(s.total_net_sales, 0) <= 0
#                 THEN NULL
#             WHEN st.ending_stock IS NULL
#                 THEN NULL
#             ELSE
#                 st.ending_stock
#                 / s.total_net_sales
#         END,
#         2
#     ) AS daily_stock_days

# FROM sales_by_day s

# LEFT JOIN cost_per_sale cp
#     ON cp.yw = YEARWEEK(s.date_from)

# LEFT JOIN stock_by_day st
#     ON st.stock_date = s.date_from

# ORDER BY s.date_from DESC
# ;
# """


# DETAILS_DAY = """
# WITH commissions AS (
#     SELECT
#         rrd_id,

#         COALESCE(
#             SUM(
#                 val / (100 + vat_rate) * 100
#             ) FILTER (
#                 WHERE field = 'comission'
#                   AND oper = 'dt'
#             ),
#             0
#         )
#         -
#         COALESCE(
#             SUM(
#                 val / (100 + vat_rate) * 100
#             ) FILTER (
#                 WHERE field = 'comission'
#                   AND oper = 'cr'
#             ),
#             0
#         ) AS net_comission

#     FROM sales.sales_long
#     GROUP BY rrd_id
# ),

# sales_agg AS (
#     SELECT
#         t.usk,
#         ANY_VALUE(t.brand) AS brand,
#         ANY_VALUE(t.subject_name) AS subject_name,
#         ANY_VALUE(t.title) AS title,

#         SUM(t.cr_rev) AS amount,
#         SUM(t.retail_amount) AS retail_amount,

#         SUM(t.cr_rev)
#         -
#         SUM(
#             t.cr_rev / (100 + t.vat_rate) * 100
#         ) AS vat_amount,

#         SUM(
#             t.cr_rev / (100 + t.vat_rate) * 100
#         ) AS amount_vatless,

#         SUM(t.adjusted_cogs) AS cogs,
#         SUM(t.adjusted_cogs_man) AS cogs_man,

#         SUM(
#             CASE
#                 WHEN t.cr_rev > 0 THEN 1
#                 WHEN t.cr_rev < 0 THEN -1
#                 ELSE 0
#             END
#         ) AS total_net_sales,

#         COUNT(*) FILTER (
#             WHERE t.cr = 0
#         ) AS no_cost,

#         COUNT(*) FILTER (
#             WHERE t.storage_flag = 'Нет на складе'
#         ) AS no_stocks,

#         COUNT(*) FILTER (
#             WHERE t.storage_flag = 'Нет приходов'
#         ) AS no_income,

#         SUM(c.net_comission) AS net_comission

#     FROM base t

#     LEFT JOIN commissions c
#         ON c.rrd_id = t.rrd_id

#     WHERE t.cr_rev <> 0
#       AND t.date_from::DATE = ?::DATE

#       {filters}

#     GROUP BY t.usk
# ),

# stock_date AS (
#     SELECT
#         MAX(t.stock_date) AS stock_date

#     FROM stocks_daily t

#     WHERE t.stock_date <= ?::DATE
# ),

# stock_end AS (
#     SELECT
#         t.usk,
#         ANY_VALUE(t.brand) AS brand,
#         ANY_VALUE(t.subject_name) AS subject_name,
#         ANY_VALUE(t.title) AS title,

#         t.stock_date AS ending_stock_date,

#         SUM(t.stock_quantity) AS ending_stock,
#         SUM(t.warehouse_quantity) AS ending_warehouse_stock,
#         SUM(t.in_transit_quantity) AS ending_in_transit_stock

#     FROM stocks_daily t

#     INNER JOIN stock_date d
#         ON d.stock_date = t.stock_date

#     WHERE 1 = 1

#       {stock_filters}

#     GROUP BY
#         t.usk,
#         t.stock_date
# ),

# product_universe AS (
#     SELECT usk FROM sales_agg
#     UNION
#     SELECT usk FROM stock_end
# )

# SELECT
#     p.usk,

#     COALESCE(
#         s.brand,
#         st.brand
#     ) AS brand,

#     COALESCE(
#         s.subject_name,
#         st.subject_name
#     ) AS subject_name,

#     COALESCE(
#         s.title,
#         st.title
#     ) AS title,

#     ROUND(
#         s.amount / 100.00,
#         2
#     ) AS amount,

#     ROUND(
#         s.retail_amount / 100.00,
#         2
#     ) AS retail_amount,

#     ROUND(
#         CASE
#             WHEN s.amount IS NULL
#               OR s.amount = 0
#                 THEN NULL
#             ELSE (
#                 s.amount - s.retail_amount
#             ) / s.amount * 100
#         END,
#         2
#     ) AS wb_discount,

#     ROUND(
#         s.vat_amount / 100.00,
#         2
#     ) AS vat_amount,

#     ROUND(
#         s.amount_vatless / 100.00,
#         2
#     ) AS amount_vatless,

#     ROUND(
#         s.cogs / 100.00,
#         2
#     ) AS cogs,

#     ROUND(
#         s.cogs_man / 100.00,
#         2
#     ) AS cogs_man,

#     ROUND(
#         s.net_comission / 100.00,
#         2
#     ) AS net_comission,

#     ROUND(
#         (
#             s.amount_vatless
#             - s.cogs
#             + s.net_comission
#         ) / 100.00,
#         2
#     ) AS margin,

#     ROUND(
#         (
#             s.amount_vatless
#             - s.cogs_man
#             + s.net_comission
#         ) / 100.00,
#         2
#     ) AS margin_man,

#     COALESCE(
#         s.total_net_sales,
#         0
#     ) AS total_net_sales,

#     COALESCE(
#         s.no_cost,
#         0
#     ) AS no_cost,

#     COALESCE(
#         s.no_stocks,
#         0
#     ) AS no_stocks,

#     COALESCE(
#         s.no_income,
#         0
#     ) AS no_income,

#     ROUND(
#         CASE
#             WHEN s.amount_vatless IS NULL
#               OR s.amount_vatless = 0
#                 THEN NULL
#             ELSE s.cogs_man
#                  / s.amount_vatless
#                  * 100
#         END,
#         2
#     ) AS cogs_man_share,

#     ROUND(
#         CASE
#             WHEN s.amount_vatless IS NULL
#               OR s.amount_vatless = 0
#                 THEN NULL
#             ELSE -s.net_comission
#                  / s.amount_vatless
#                  * 100
#         END,
#         2
#     ) AS commision_percent,

#     ROUND(
#         CASE
#             WHEN s.amount_vatless IS NULL
#               OR s.amount_vatless = 0
#                 THEN NULL
#             ELSE (
#                 s.amount_vatless
#                 - s.cogs_man
#                 + s.net_comission
#             ) / s.amount_vatless * 100
#         END,
#         2
#     ) AS margin_percent,

#     st.ending_stock_date,
#     st.ending_stock,
#     st.ending_warehouse_stock,
#     st.ending_in_transit_stock,

#     ROUND(
#         CASE
#             WHEN COALESCE(
#                 s.total_net_sales,
#                 0
#             ) <= 0
#                 THEN NULL

#             WHEN st.ending_stock IS NULL
#                 THEN NULL

#             ELSE st.ending_stock
#                  / s.total_net_sales
#         END,
#         2
#     ) AS daily_stock_days,

#     CASE
#         WHEN COALESCE(
#             s.total_net_sales,
#             0
#         ) <= 0
#          AND COALESCE(
#             st.ending_stock,
#             0
#         ) > 0
#             THEN 'Остаток без продаж'

#         WHEN st.ending_stock IS NULL
#             THEN 'Нет данных об остатке'

#         ELSE 'Есть продажи'
#     END AS stock_status

# FROM product_universe p

# LEFT JOIN sales_agg s
#     ON s.usk = p.usk

# LEFT JOIN stock_end st
#     ON st.usk = p.usk

# ORDER BY
#     CASE
#         WHEN COALESCE(
#             s.total_net_sales,
#             0
#         ) > 0
#             THEN 0
#         ELSE 1
#     END,

#     s.amount DESC NULLS LAST,
#     st.ending_stock DESC NULLS LAST
# ;
# """


# DETAILS_PERIOD = """
# WITH commissions AS (
#     SELECT
#         rrd_id,

#         COALESCE(
#             SUM(
#                 val / (100 + vat_rate) * 100
#             ) FILTER (
#                 WHERE field = 'comission'
#                   AND oper = 'dt'
#             ),
#             0
#         )
#         -
#         COALESCE(
#             SUM(
#                 val / (100 + vat_rate) * 100
#             ) FILTER (
#                 WHERE field = 'comission'
#                   AND oper = 'cr'
#             ),
#             0
#         ) AS net_comission

#     FROM sales.sales_long
#     GROUP BY rrd_id
# ),

# sales_agg AS (
#     SELECT
#         t.usk,
#         ANY_VALUE(t.brand) AS brand,
#         ANY_VALUE(t.subject_name) AS subject_name,
#         ANY_VALUE(t.title) AS title,

#         SUM(t.cr_rev) AS amount,
#         SUM(t.retail_amount) AS retail_amount,

#         SUM(t.cr_rev)
#         -
#         SUM(
#             t.cr_rev / (100 + t.vat_rate) * 100
#         ) AS vat_amount,

#         SUM(
#             t.cr_rev / (100 + t.vat_rate) * 100
#         ) AS amount_vatless,

#         SUM(t.adjusted_cogs) AS cogs,
#         SUM(t.adjusted_cogs_man) AS cogs_man,

#         SUM(
#             CASE
#                 WHEN t.cr_rev > 0 THEN 1
#                 WHEN t.cr_rev < 0 THEN -1
#                 ELSE 0
#             END
#         ) AS total_net_sales,

#         COUNT(*) FILTER (
#             WHERE t.cr = 0
#         ) AS no_cost,

#         COUNT(*) FILTER (
#             WHERE t.storage_flag = 'Нет на складе'
#         ) AS no_stocks,

#         COUNT(*) FILTER (
#             WHERE t.storage_flag = 'Нет приходов'
#         ) AS no_income,

#         SUM(c.net_comission) AS net_comission

#     FROM base t

#     LEFT JOIN commissions c
#         ON c.rrd_id = t.rrd_id

#     WHERE t.cr_rev <> 0

#       AND t.date_from::DATE
#           BETWEEN ?::DATE AND ?::DATE

#       {filters}

#     GROUP BY t.usk
# ),

# stock_period AS (
#     SELECT
#         t.usk,

#         ANY_VALUE(t.brand) AS brand,
#         ANY_VALUE(t.subject_name) AS subject_name,
#         ANY_VALUE(t.title) AS title,

#         SUM(t.stock_quantity) AS stock_quantity_sum,

#         COUNT(
#             DISTINCT t.stock_date
#         ) AS stock_days_count,

#         MIN(t.stock_date) AS first_stock_date,
#         MAX(t.stock_date) AS last_stock_date

#     FROM stocks_daily t

#     WHERE t.stock_date
#           BETWEEN ?::DATE AND ?::DATE

#       {stock_filters}

#     GROUP BY t.usk
# ),

# stock_end_date AS (
#     SELECT
#         MAX(t.stock_date) AS stock_date

#     FROM stocks_daily t

#     WHERE t.stock_date <= ?::DATE
# ),

# stock_end AS (
#     SELECT
#         t.usk,

#         ANY_VALUE(t.brand) AS brand,
#         ANY_VALUE(t.subject_name) AS subject_name,
#         ANY_VALUE(t.title) AS title,

#         t.stock_date AS ending_stock_date,

#         SUM(t.stock_quantity) AS ending_stock,
#         SUM(t.warehouse_quantity) AS ending_warehouse_stock,
#         SUM(t.in_transit_quantity) AS ending_in_transit_stock

#     FROM stocks_daily t

#     INNER JOIN stock_end_date d
#         ON d.stock_date = t.stock_date

#     WHERE 1 = 1

#       {stock_filters}

#     GROUP BY
#         t.usk,
#         t.stock_date
# ),

# product_universe AS (
#     SELECT usk FROM sales_agg
#     UNION
#     SELECT usk FROM stock_period
#     UNION
#     SELECT usk FROM stock_end
# )

# SELECT
#     p.usk,

#     COALESCE(
#         s.brand,
#         sp.brand,
#         se.brand
#     ) AS brand,

#     COALESCE(
#         s.subject_name,
#         sp.subject_name,
#         se.subject_name
#     ) AS subject_name,

#     COALESCE(
#         s.title,
#         sp.title,
#         se.title
#     ) AS title,

#     ROUND(
#         s.amount / 100.00,
#         2
#     ) AS amount,

#     ROUND(
#         s.retail_amount / 100.00,
#         2
#     ) AS retail_amount,

#     ROUND(
#         CASE
#             WHEN s.amount IS NULL
#               OR s.amount = 0
#                 THEN NULL
#             ELSE (
#                 s.amount - s.retail_amount
#             ) / s.amount * 100
#         END,
#         2
#     ) AS wb_discount,

#     ROUND(
#         s.vat_amount / 100.00,
#         2
#     ) AS vat_amount,

#     ROUND(
#         s.amount_vatless / 100.00,
#         2
#     ) AS amount_vatless,

#     ROUND(
#         s.cogs / 100.00,
#         2
#     ) AS cogs,

#     ROUND(
#         s.cogs_man / 100.00,
#         2
#     ) AS cogs_man,

#     ROUND(
#         s.net_comission / 100.00,
#         2
#     ) AS net_comission,

#     ROUND(
#         (
#             s.amount_vatless
#             - s.cogs
#             + s.net_comission
#         ) / 100.00,
#         2
#     ) AS margin,

#     ROUND(
#         (
#             s.amount_vatless
#             - s.cogs_man
#             + s.net_comission
#         ) / 100.00,
#         2
#     ) AS margin_man,

#     COALESCE(
#         s.total_net_sales,
#         0
#     ) AS total_net_sales,

#     COALESCE(
#         s.no_cost,
#         0
#     ) AS no_cost,

#     COALESCE(
#         s.no_stocks,
#         0
#     ) AS no_stocks,

#     COALESCE(
#         s.no_income,
#         0
#     ) AS no_income,

#     ROUND(
#         CASE
#             WHEN s.amount_vatless IS NULL
#               OR s.amount_vatless = 0
#                 THEN NULL
#             ELSE s.cogs_man
#                  / s.amount_vatless
#                  * 100
#         END,
#         2
#     ) AS cogs_man_share,

#     ROUND(
#         CASE
#             WHEN s.amount_vatless IS NULL
#               OR s.amount_vatless = 0
#                 THEN NULL
#             ELSE -s.net_comission
#                  / s.amount_vatless
#                  * 100
#         END,
#         2
#     ) AS commision_percent,

#     ROUND(
#         CASE
#             WHEN s.amount_vatless IS NULL
#               OR s.amount_vatless = 0
#                 THEN NULL
#             ELSE (
#                 s.amount_vatless
#                 - s.cogs_man
#                 + s.net_comission
#             ) / s.amount_vatless * 100
#         END,
#         2
#     ) AS margin_percent,

#     sp.stock_quantity_sum,
#     sp.stock_days_count,
#     sp.first_stock_date,
#     sp.last_stock_date,

#     ROUND(
#         CASE
#             WHEN COALESCE(
#                 s.total_net_sales,
#                 0
#             ) <= 0
#                 THEN NULL

#             WHEN sp.stock_quantity_sum IS NULL
#                 THEN NULL

#             ELSE
#                 sp.stock_quantity_sum
#                 / s.total_net_sales
#         END,
#         2
#     ) AS turnover_days,

#     se.ending_stock_date,
#     se.ending_stock,
#     se.ending_warehouse_stock,
#     se.ending_in_transit_stock,

#     CASE
#         WHEN COALESCE(
#             s.total_net_sales,
#             0
#         ) <= 0
#          AND COALESCE(
#             se.ending_stock,
#             0
#         ) > 0
#             THEN 'Остаток без продаж'

#         WHEN se.ending_stock IS NULL
#             THEN 'Нет данных об остатке'

#         WHEN COALESCE(
#             sp.stock_days_count,
#             0
#         ) = 0
#             THEN 'Нет истории остатков'

#         ELSE 'Есть продажи'
#     END AS stock_status

# FROM product_universe p

# LEFT JOIN sales_agg s
#     ON s.usk = p.usk

# LEFT JOIN stock_period sp
#     ON sp.usk = p.usk

# LEFT JOIN stock_end se
#     ON se.usk = p.usk

# ORDER BY
#     CASE
#         WHEN COALESCE(
#             s.total_net_sales,
#             0
#         ) > 0
#             THEN 0
#         ELSE 1
#     END,

#     s.amount DESC NULLS LAST,
#     se.ending_stock DESC NULLS LAST
# ;
# """

# BASE_WB_COSTS = """ 
# CREATE OR REPLACE TEMP TABLE wb_costs as
# with wb_costs as (
# select
# date_from,
# rrd_id,
# 'Other income / loss' as account,
# sop_name as cost_item,
# COALESCE(sum(val) filter (where oper='dt' ),0) as dt,
# COALESCE(sum(val) filter (where oper='cr' ),0) as cr
# from sales.sales_long
# where field = 'retail_price' and sop_name like '%оррекция%'
# GROUP BY date_from, rrd_id, sop_name
# UNION ALL
# select
# date_from,
# rrd_id,
# 'WB Logistic' as account,
# COALESCE(btn,sop_name) as cost_item,
# COALESCE(sum(val) filter (where oper='dt' ),0) as dt,
# COALESCE(sum(val) filter (where oper='cr' ),0) as cr
# from sales.sales_long
# where field = 'delivery_rub' -- and sop_name like '%оррекция%'
# GROUP BY date_from, rrd_id, COALESCE(btn,sop_name)
# UNION ALL
# select
# date_from,
# rrd_id,
# 'WB Storage' as account,
# sop_name as cost_item,
# COALESCE(sum(val) filter (where oper='dt' ),0) as dt,
# COALESCE(sum(val) filter (where oper='cr' ),0) as cr
# from sales.sales_long
# where field = 'storage_fee' -- and sop_name like '%оррекция%'
# GROUP BY date_from, rrd_id, sop_name
# UNION ALL
# select
# date_from,
# rrd_id,
# 'WB Acceptance' as account,
# sop_name as cost_item,
# COALESCE(sum(val) filter (where oper='dt' ),0) as dt,
# COALESCE(sum(val) filter (where oper='cr' ),0) as cr
# from sales.sales_long
# where field = 'acceptance' -- and sop_name like '%оррекция%'
# GROUP BY date_from, rrd_id, sop_name
# UNION ALL
# select
# date_from,
# rrd_id,
# 'WB Penalties' as account,
# btn as cost_item,
# COALESCE(sum(val) filter (where oper='dt' ),0) as dt,
# COALESCE(sum(val) filter (where oper='cr' ),0) as cr
# from sales.sales_long
# where field = 'penalty' -- and sop_name like '%оррекция%'
# GROUP BY date_from, rrd_id, btn
# UNION ALL
# select
# date_from,
# rrd_id,
# 'WB Deduction' as account,
# case 
# when STARTS_WITH(btn, 'Списание за отзыв')  then 'Отзывы'
# when STARTS_WITH(btn, 'Оказание услуг') 
# or STARTS_WITH(btn,'Предоставление услуг') 
# or STARTS_WITH(btn,'Витрина Магазина') then 'Услуги WB'
# else 'Прочее' end as cost_item,
# COALESCE(sum(val) filter (where oper='dt' ),0) as dt,
# COALESCE(sum(val) filter (where oper='cr' ),0) as cr
# from sales.sales_long
# where field = 'deduction' 
# and (not STARTS_WITH(btn,'Платеж') or not STARTS_WITH(btn, 'Перевод'))
# and btn is not null
# -- and sop_name like '%оррекция%'
# GROUP BY date_from, rrd_id, cost_item
# UNION ALL
# select
# date_from,
# rrd_id,
# 'WB Loyality' as account,
# btn as cost_item,
# COALESCE(sum(val) filter (where oper='dt' ),0) as dt,
# COALESCE(sum(val) filter (where oper='cr' ),0) as cr
# from sales.sales_long
# where field in('cashback_commission_change','cashback_amount') -- and sop_name like '%оррекция%'
# GROUP BY date_from, rrd_id, btn
# )
# select 
# yearweek(t.date_from::date) as yw,
# t.*,
# s.vat_rate
# from wb_costs t
# left join sales.sales_long s on s.rrd_id = t.rrd_id;
# """




# gear/app/data/queries.py
### ---------
### Сюда пихаем запросы что бы не было ада в классе dashboard
### ---------

#### БАЗОВЫЙ ЗАПРОС НА СОЗДАНИЕ ВРЕМЕННОЙ ТАБЛИЦЫ 

# BASE_QUERY = """ 
# CREATE OR REPLACE TEMP TABLE base as
# with last_val as (
# select
# usk,
# adjust_wo[-1] as last_cr,
# adjust_man_wo[-1] as last_man_cr
# from inventories.pre_wo
# ),
# -- выбираем списания 
# add_last as (select
# t.*,
# l.last_cr,
# l.last_man_cr
# from inventories.inv_gl_final t
# left join last_val l on l.usk = t.usk 
# where t.cr = 0 and t.oper = 'Списание'
# ),
# wb_price as (
# select 
# rrd_id, val
# from sales.sales_long
# where field = 'retail_amount'
# )

# select 
# yearweek(t.date_from::date) as yw,
# t.*,
# wb.val as retail_amount,
# a.last_cr,
# a.last_man_cr,
# COALESCE(a.last_cr, case when t.cr=0 then 95000 else t.cr end) as adjusted_cogs,
# COALESCE(a.last_man_cr, case when t.cr_man=0 then 62000 else t.cr_man end) as adjusted_cogs_man,
# UPPER(w.brand) as brand,
# w.subject_id,
# w.subject_name,
# w.title,
# COALESCE(w.gender, 'Не указан') as gender,
# case 
# when t.cr = 0 and a.last_cr <> 0 and t.oper = 'Списание' then 'Нет на складе'
# when t.cr = 0 and a.last_cr is null and t.oper = 'Списание' then 'Нет приходов'
# else null
# end as storage_flag
# from inventories.inv_gl_final t
# left join add_last a on a.rrd_id = t.rrd_id
# LEFT JOIN inventories.wb_product w on w.card_id = t.usk
# left join wb_price as wb on wb.rrd_id = t.rrd_id
# ;
# """

# gear/app/data/queries.py
BASE_QUERY = """
CREATE OR REPLACE TEMP TABLE base AS

WITH last_val AS (
    SELECT
        usk,
        adjust_wo[-1] AS last_cr,
        adjust_man_wo[-1] AS last_man_cr
    FROM inventories.pre_wo
),

-- =========================================================
-- Списания, для которых подставляем последнюю себестоимость
-- =========================================================

add_last AS (
    SELECT
        t.*,
        l.last_cr,
        l.last_man_cr

    FROM inventories.inv_gl_final t

    LEFT JOIN last_val l
        ON l.usk = t.usk

    WHERE t.cr = 0
      AND t.oper = 'Списание'
),

-- =========================================================
-- Розничная стоимость WB
-- ВАЖНО: одна строка на rrd_id
-- =========================================================

wb_price AS (
    SELECT
        rrd_id,

        SUM(val) AS retail_amount

    FROM sales.sales_long

    WHERE field = 'retail_amount'

    GROUP BY
        rrd_id
),

-- =========================================================
-- Комиссия WB
--
-- Повторяем ту же методологию, которая используется
-- в DAILY_SALES_AGG:
--
-- dt - cr
--
-- Комиссия приводится к значению без НДС.
--
-- В результате net_comission обычно отрицательная,
-- поэтому прибыль считается:
--
-- revenue_vatless
-- - cogs
-- + net_comission
-- =========================================================

commissions AS (
    SELECT
        rrd_id,

        COALESCE(
            SUM(
                val
                / (100 + vat_rate)
                * 100
            ) FILTER (
                WHERE field = 'comission'
                  AND oper = 'dt'
            ),
            0
        )
        -
        COALESCE(
            SUM(
                val
                / (100 + vat_rate)
                * 100
            ) FILTER (
                WHERE field = 'comission'
                  AND oper = 'cr'
            ),
            0
        ) AS net_comission

    FROM sales.sales_long

    GROUP BY
        rrd_id
)

SELECT

    YEARWEEK(
        t.date_from::DATE
    ) AS yw,

    t.*,

    -- =====================================================
    -- WB
    -- =====================================================

    COALESCE(
        wb.retail_amount,
        0
    ) AS retail_amount,

    COALESCE(
        c.net_comission,
        0
    ) AS net_comission,

    -- =====================================================
    -- Себестоимость
    -- =====================================================

    a.last_cr,

    a.last_man_cr,

    COALESCE(
        a.last_cr,

        CASE
            WHEN t.cr = 0
                THEN 95000

            ELSE t.cr
        END

    ) AS adjusted_cogs,

    COALESCE(
        a.last_man_cr,

        CASE
            WHEN t.cr_man = 0
                THEN 62000

            ELSE t.cr_man
        END

    ) AS adjusted_cogs_man,

    -- =====================================================
    -- Карточка товара
    -- =====================================================

    UPPER(
        w.brand
    ) AS brand,

    w.subject_id,

    w.subject_name,

    w.title,

    COALESCE(
        w.gender,
        'Не указан'
    ) AS gender,

    -- =====================================================
    -- Контроль себестоимости
    -- =====================================================

    CASE

        WHEN t.cr = 0
         AND a.last_cr <> 0
         AND t.oper = 'Списание'
            THEN 'Нет на складе'

        WHEN t.cr = 0
         AND a.last_cr IS NULL
         AND t.oper = 'Списание'
            THEN 'Нет приходов'

        ELSE NULL

    END AS storage_flag

FROM inventories.inv_gl_final t

LEFT JOIN add_last a
    ON a.rrd_id = t.rrd_id

LEFT JOIN inventories.wb_product w
    ON w.card_id = t.usk

LEFT JOIN wb_price wb
    ON wb.rrd_id = t.rrd_id

LEFT JOIN commissions c
    ON c.rrd_id = t.rrd_id
;
"""


BASE_STOCKS = """
CREATE OR REPLACE TEMP TABLE stocks_daily AS

SELECT
    t.date_from::DATE AS stock_date,

    /*
    Для остатков используем NM ID из исходного отчёта WB напрямую.
    Это не зависит от наличия записи в inventories.usk.
    */
    t.nm_id AS nm_id,
    t.nm_id AS usk,

    UPPER(w.brand) AS brand,
    w.subject_id,
    w.subject_name,
    w.title,
    COALESCE(w.gender, 'Не указан') AS gender,

    SUM(
        COALESCE(t.quantity, 0)
        + COALESCE(t.in_way_from_client, 0)
        + COALESCE(t.in_way_to_client, 0)
    ) AS stock_quantity,

    SUM(
        COALESCE(t.quantity, 0)
    ) AS warehouse_quantity,

    SUM(
        COALESCE(t.in_way_from_client, 0)
        + COALESCE(t.in_way_to_client, 0)
    ) AS in_transit_quantity

FROM stocks.unpacked_stocks t

LEFT JOIN inventories.wb_product w
    ON w.card_id = t.nm_id

GROUP BY
    t.date_from::DATE,
    t.nm_id,
    UPPER(w.brand),
    w.subject_id,
    w.subject_name,
    w.title,
    COALESCE(w.gender, 'Не указан')
;
"""


DAILY_SALES_AGG = """
WITH commissions AS (
    SELECT
        rrd_id,

        COALESCE(
            SUM(
                val / (100 + vat_rate) * 100
            ) FILTER (
                WHERE field = 'comission'
                  AND oper = 'dt'
            ),
            0
        )
        -
        COALESCE(
            SUM(
                val / (100 + vat_rate) * 100
            ) FILTER (
                WHERE field = 'comission'
                  AND oper = 'cr'
            ),
            0
        ) AS net_comission

    FROM sales.sales_long
    GROUP BY rrd_id
),

sales_by_day AS (
    SELECT
        t.date_from::DATE AS date_from,

        SUM(t.cr_rev) AS amount,
        SUM(t.retail_amount) AS retail_amount,

        SUM(t.cr_rev)
        -
        SUM(
            t.cr_rev / (100 + t.vat_rate) * 100
        ) AS vat_amount,

        SUM(
            t.cr_rev / (100 + t.vat_rate) * 100
        ) AS amount_vatless,

        SUM(t.adjusted_cogs) AS cogs,
        SUM(t.adjusted_cogs_man) AS cogs_man,

        SUM(
            CASE
                WHEN t.cr_rev > 0 THEN 1
                WHEN t.cr_rev < 0 THEN -1
                ELSE 0
            END
        ) AS total_net_sales,

        COUNT(*) FILTER (
            WHERE t.cr = 0
        ) AS no_cost,

        COUNT(*) FILTER (
            WHERE t.storage_flag = 'Нет на складе'
        ) AS no_stocks,

        COUNT(*) FILTER (
            WHERE t.storage_flag = 'Нет приходов'
        ) AS no_income,

        SUM(c.net_comission) AS net_comission

    FROM base t

    LEFT JOIN commissions c
        ON c.rrd_id = t.rrd_id

    WHERE t.cr_rev <> 0

      AND t.date_from::DATE
          BETWEEN ?::DATE AND ?::DATE

      {filters}

    GROUP BY
        t.date_from::DATE
),

sales_count_by_week AS (
    SELECT
        YEARWEEK(t.date_from::DATE) AS yw,

        SUM(
            CASE
                WHEN t.cr_rev > 0 THEN 1
                WHEN t.cr_rev < 0 THEN -1
                ELSE 0
            END
        ) AS rev_count

    FROM base t

    WHERE t.cr_rev <> 0

    GROUP BY
        YEARWEEK(t.date_from::DATE)
),

wb_costs_by_week AS (
    SELECT
        yw,

        SUM(
            dt / (100 + vat_rate) * 100
        )
        -
        SUM(
            cr / (100 + vat_rate) * 100
        ) AS costs

    FROM wb_costs

    GROUP BY yw
),

cost_per_sale AS (
    SELECT
        s.yw,

        CASE
            WHEN COALESCE(s.rev_count, 0) = 0
                THEN NULL
            ELSE ABS(w.costs) / s.rev_count
        END AS cost_per_sold

    FROM sales_count_by_week s

    LEFT JOIN wb_costs_by_week w
        ON w.yw = s.yw
),

stock_by_day AS (
    SELECT
        t.stock_date,

        SUM(t.stock_quantity) AS ending_stock,
        SUM(t.warehouse_quantity) AS ending_warehouse_stock,
        SUM(t.in_transit_quantity) AS ending_in_transit_stock

    FROM stocks_daily t

    WHERE t.stock_date
          BETWEEN ?::DATE AND ?::DATE

      {stock_filters}

    GROUP BY t.stock_date
)

SELECT
    s.date_from,

    ROUND(
        s.amount / 100.00,
        2
    ) AS amount,

    ROUND(
        s.retail_amount / 100.00,
        2
    ) AS retail_amount,

    ROUND(
        CASE
            WHEN s.amount = 0 THEN NULL
            ELSE (
                s.amount - s.retail_amount
            ) / s.amount * 100
        END,
        2
    ) AS wb_discount,

    ROUND(
        s.vat_amount / 100.00,
        2
    ) AS vat_amount,

    ROUND(
        s.amount_vatless / 100.00,
        2
    ) AS amount_vatless,

    ROUND(
        s.cogs / 100.00,
        2
    ) AS cogs,

    ROUND(
        s.cogs_man / 100.00,
        2
    ) AS cogs_man,

    ROUND(
        s.net_comission / 100.00,
        2
    ) AS net_comission,

    ROUND(
        (
            s.amount_vatless
            - s.cogs
            + s.net_comission
        ) / 100.00,
        2
    ) AS margin,

    ROUND(
        (
            s.amount_vatless
            - s.cogs_man
            + s.net_comission
        ) / 100.00,
        2
    ) AS margin_man,

    s.total_net_sales,
    s.no_cost,
    s.no_stocks,
    s.no_income,

    ROUND(
        CASE
            WHEN s.amount_vatless = 0 THEN NULL
            ELSE s.cogs_man
                 / s.amount_vatless
                 * 100
        END,
        2
    ) AS cogs_man_share,

    ROUND(
        CASE
            WHEN s.amount_vatless = 0 THEN NULL
            ELSE -s.net_comission
                 / s.amount_vatless
                 * 100
        END,
        2
    ) AS commision_percent,

    ROUND(
        CASE
            WHEN s.amount_vatless = 0 THEN NULL
            ELSE (
                s.amount_vatless
                - s.cogs_man
                + s.net_comission
            ) / s.amount_vatless * 100
        END,
        2
    ) AS margin_percent,

    ROUND(
        cp.cost_per_sold / 100.00,
        2
    ) AS cost_per_sold,

    ROUND(
        s.total_net_sales
        * cp.cost_per_sold
        / 100.00,
        2
    ) AS wb_costs,

    ROUND(
        (
            (
                s.amount_vatless
                - s.cogs_man
                + s.net_comission
            )
            -
            (
                s.total_net_sales
                * cp.cost_per_sold
            )
        ) / 100.00,
        2
    ) AS wb_result,

    st.stock_date AS ending_stock_date,
    st.ending_stock,
    st.ending_warehouse_stock,
    st.ending_in_transit_stock,

    ROUND(
        CASE
            WHEN COALESCE(s.total_net_sales, 0) <= 0
                THEN NULL
            WHEN st.ending_stock IS NULL
                THEN NULL
            ELSE
                st.ending_stock
                / s.total_net_sales
        END,
        2
    ) AS daily_stock_days

FROM sales_by_day s

LEFT JOIN cost_per_sale cp
    ON cp.yw = YEARWEEK(s.date_from)

LEFT JOIN stock_by_day st
    ON st.stock_date = s.date_from

ORDER BY s.date_from DESC
;
"""


DETAILS_DAY = """
WITH commissions AS (
    SELECT
        rrd_id,

        COALESCE(
            SUM(
                val / (100 + vat_rate) * 100
            ) FILTER (
                WHERE field = 'comission'
                  AND oper = 'dt'
            ),
            0
        )
        -
        COALESCE(
            SUM(
                val / (100 + vat_rate) * 100
            ) FILTER (
                WHERE field = 'comission'
                  AND oper = 'cr'
            ),
            0
        ) AS net_comission

    FROM sales.sales_long
    GROUP BY rrd_id
),

sales_agg AS (
    SELECT
        t.usk AS nm_id,
        t.usk,

        ANY_VALUE(t.brand) AS brand,
        ANY_VALUE(t.subject_name) AS subject_name,
        ANY_VALUE(t.title) AS title,

        SUM(t.cr_rev) AS amount,
        SUM(t.retail_amount) AS retail_amount,

        SUM(t.cr_rev)
        -
        SUM(
            t.cr_rev / (100 + t.vat_rate) * 100
        ) AS vat_amount,

        SUM(
            t.cr_rev / (100 + t.vat_rate) * 100
        ) AS amount_vatless,

        SUM(t.adjusted_cogs) AS cogs,
        SUM(t.adjusted_cogs_man) AS cogs_man,

        SUM(
            CASE
                WHEN t.cr_rev > 0 THEN 1
                WHEN t.cr_rev < 0 THEN -1
                ELSE 0
            END
        ) AS total_net_sales,

        COUNT(*) FILTER (
            WHERE t.cr = 0
        ) AS no_cost,

        COUNT(*) FILTER (
            WHERE t.storage_flag = 'Нет на складе'
        ) AS no_stocks,

        COUNT(*) FILTER (
            WHERE t.storage_flag = 'Нет приходов'
        ) AS no_income,

        SUM(c.net_comission) AS net_comission

    FROM base t

    LEFT JOIN commissions c
        ON c.rrd_id = t.rrd_id

    WHERE t.cr_rev <> 0
      AND t.date_from::DATE = ?::DATE

      {filters}

    GROUP BY
        t.usk
),

stock_date AS (
    SELECT
        MAX(t.stock_date) AS stock_date

    FROM stocks_daily t

    WHERE t.stock_date <= ?::DATE
),

stock_end AS (
    SELECT
        t.nm_id,

        ANY_VALUE(t.usk) AS usk,
        ANY_VALUE(t.brand) AS brand,
        ANY_VALUE(t.subject_name) AS subject_name,
        ANY_VALUE(t.title) AS title,

        t.stock_date AS ending_stock_date,

        SUM(t.stock_quantity) AS ending_stock,
        SUM(t.warehouse_quantity) AS ending_warehouse_stock,
        SUM(t.in_transit_quantity) AS ending_in_transit_stock

    FROM stocks_daily t

    INNER JOIN stock_date d
        ON d.stock_date = t.stock_date

    WHERE 1 = 1

      {stock_filters}

    GROUP BY
        t.nm_id,
        t.stock_date
),

product_universe AS (
    SELECT nm_id
    FROM sales_agg
    WHERE nm_id IS NOT NULL

    UNION

    SELECT nm_id
    FROM stock_end
    WHERE nm_id IS NOT NULL
)

SELECT
    p.nm_id,

    COALESCE(
        s.usk,
        st.usk
    ) AS usk,

    COALESCE(
        s.brand,
        st.brand
    ) AS brand,

    COALESCE(
        s.subject_name,
        st.subject_name
    ) AS subject_name,

    COALESCE(
        s.title,
        st.title,
        'Без наименования'
    ) AS title,

    ROUND(
        COALESCE(s.amount, 0) / 100.00,
        2
    ) AS amount,

    ROUND(
        COALESCE(s.retail_amount, 0) / 100.00,
        2
    ) AS retail_amount,

    ROUND(
        CASE
            WHEN COALESCE(s.amount, 0) = 0
                THEN NULL
            ELSE (
                s.amount - s.retail_amount
            ) / s.amount * 100
        END,
        2
    ) AS wb_discount,

    ROUND(
        COALESCE(s.vat_amount, 0) / 100.00,
        2
    ) AS vat_amount,

    ROUND(
        COALESCE(s.amount_vatless, 0) / 100.00,
        2
    ) AS amount_vatless,

    ROUND(
        COALESCE(s.cogs, 0) / 100.00,
        2
    ) AS cogs,

    ROUND(
        COALESCE(s.cogs_man, 0) / 100.00,
        2
    ) AS cogs_man,

    ROUND(
        COALESCE(s.net_comission, 0) / 100.00,
        2
    ) AS net_comission,

    ROUND(
        (
            COALESCE(s.amount_vatless, 0)
            - COALESCE(s.cogs, 0)
            + COALESCE(s.net_comission, 0)
        ) / 100.00,
        2
    ) AS margin,

    ROUND(
        (
            COALESCE(s.amount_vatless, 0)
            - COALESCE(s.cogs_man, 0)
            + COALESCE(s.net_comission, 0)
        ) / 100.00,
        2
    ) AS margin_man,

    COALESCE(
        s.total_net_sales,
        0
    ) AS total_net_sales,

    COALESCE(
        s.no_cost,
        0
    ) AS no_cost,

    COALESCE(
        s.no_stocks,
        0
    ) AS no_stocks,

    COALESCE(
        s.no_income,
        0
    ) AS no_income,

    ROUND(
        CASE
            WHEN COALESCE(s.amount_vatless, 0) = 0
                THEN NULL
            ELSE s.cogs_man
                 / s.amount_vatless
                 * 100
        END,
        2
    ) AS cogs_man_share,

    ROUND(
        CASE
            WHEN COALESCE(s.amount_vatless, 0) = 0
                THEN NULL
            ELSE -s.net_comission
                 / s.amount_vatless
                 * 100
        END,
        2
    ) AS commision_percent,

    ROUND(
        CASE
            WHEN COALESCE(s.amount_vatless, 0) = 0
                THEN NULL
            ELSE (
                s.amount_vatless
                - s.cogs_man
                + s.net_comission
            ) / s.amount_vatless * 100
        END,
        2
    ) AS margin_percent,

    st.ending_stock_date,
    st.ending_stock,
    st.ending_warehouse_stock,
    st.ending_in_transit_stock,

    ROUND(
        CASE
            WHEN COALESCE(
                s.total_net_sales,
                0
            ) <= 0
                THEN NULL

            WHEN st.ending_stock IS NULL
                THEN NULL

            ELSE st.ending_stock
                 / s.total_net_sales
        END,
        2
    ) AS daily_stock_days,

    CASE
        WHEN st.ending_stock IS NULL
            THEN 'Нет данных об остатке'

        WHEN st.ending_stock > 0
         AND COALESCE(s.total_net_sales, 0) <= 0
         AND COALESCE(s.usk, st.usk) IS NULL
            THEN 'Остаток без продаж и USK'

        WHEN st.ending_stock > 0
         AND COALESCE(s.total_net_sales, 0) <= 0
            THEN 'Остаток без продаж'

        WHEN st.ending_stock > 0
         AND COALESCE(s.usk, st.usk) IS NULL
            THEN 'Нет USK'

        ELSE 'Есть продажи'
    END AS stock_status

FROM product_universe p

LEFT JOIN sales_agg s
    ON s.nm_id = p.nm_id

LEFT JOIN stock_end st
    ON st.nm_id = p.nm_id

ORDER BY
    CASE
        WHEN COALESCE(
            s.total_net_sales,
            0
        ) > 0
            THEN 0
        ELSE 1
    END,

    s.amount DESC NULLS LAST,
    st.ending_stock DESC NULLS LAST
;
"""


DETAILS_PERIOD = """
WITH commissions AS (
    SELECT
        rrd_id,

        COALESCE(
            SUM(
                val / (100 + vat_rate) * 100
            ) FILTER (
                WHERE field = 'comission'
                  AND oper = 'dt'
            ),
            0
        )
        -
        COALESCE(
            SUM(
                val / (100 + vat_rate) * 100
            ) FILTER (
                WHERE field = 'comission'
                  AND oper = 'cr'
            ),
            0
        ) AS net_comission

    FROM sales.sales_long
    GROUP BY rrd_id
),

sales_agg AS (
    SELECT
        t.usk AS nm_id,
        t.usk,

        ANY_VALUE(t.brand) AS brand,
        ANY_VALUE(t.subject_name) AS subject_name,
        ANY_VALUE(t.title) AS title,

        SUM(t.cr_rev) AS amount,
        SUM(t.retail_amount) AS retail_amount,

        SUM(t.cr_rev)
        -
        SUM(
            t.cr_rev / (100 + t.vat_rate) * 100
        ) AS vat_amount,

        SUM(
            t.cr_rev / (100 + t.vat_rate) * 100
        ) AS amount_vatless,

        SUM(t.adjusted_cogs) AS cogs,
        SUM(t.adjusted_cogs_man) AS cogs_man,

        SUM(
            CASE
                WHEN t.cr_rev > 0 THEN 1
                WHEN t.cr_rev < 0 THEN -1
                ELSE 0
            END
        ) AS total_net_sales,

        COUNT(*) FILTER (
            WHERE t.cr = 0
        ) AS no_cost,

        COUNT(*) FILTER (
            WHERE t.storage_flag = 'Нет на складе'
        ) AS no_stocks,

        COUNT(*) FILTER (
            WHERE t.storage_flag = 'Нет приходов'
        ) AS no_income,

        SUM(c.net_comission) AS net_comission

    FROM base t

    LEFT JOIN commissions c
        ON c.rrd_id = t.rrd_id

    WHERE t.cr_rev <> 0

      AND t.date_from::DATE
          BETWEEN ?::DATE AND ?::DATE

      {filters}

    GROUP BY
        t.usk
),

stock_period AS (
    SELECT
        t.nm_id,

        ANY_VALUE(t.usk) AS usk,
        ANY_VALUE(t.brand) AS brand,
        ANY_VALUE(t.subject_name) AS subject_name,
        ANY_VALUE(t.title) AS title,

        SUM(t.stock_quantity) AS stock_quantity_sum,

        COUNT(
            DISTINCT t.stock_date
        ) AS stock_days_count,

        MIN(t.stock_date) AS first_stock_date,
        MAX(t.stock_date) AS last_stock_date

    FROM stocks_daily t

    WHERE t.stock_date
          BETWEEN ?::DATE AND ?::DATE

      {stock_filters}

    GROUP BY
        t.nm_id
),

stock_end_date AS (
    SELECT
        MAX(t.stock_date) AS stock_date

    FROM stocks_daily t

    WHERE t.stock_date <= ?::DATE
),

stock_end AS (
    SELECT
        t.nm_id,

        ANY_VALUE(t.usk) AS usk,
        ANY_VALUE(t.brand) AS brand,
        ANY_VALUE(t.subject_name) AS subject_name,
        ANY_VALUE(t.title) AS title,

        t.stock_date AS ending_stock_date,

        SUM(t.stock_quantity) AS ending_stock,
        SUM(t.warehouse_quantity) AS ending_warehouse_stock,
        SUM(t.in_transit_quantity) AS ending_in_transit_stock

    FROM stocks_daily t

    INNER JOIN stock_end_date d
        ON d.stock_date = t.stock_date

    WHERE 1 = 1

      {stock_filters}

    GROUP BY
        t.nm_id,
        t.stock_date
),

product_universe AS (
    SELECT nm_id
    FROM sales_agg
    WHERE nm_id IS NOT NULL

    UNION

    SELECT nm_id
    FROM stock_period
    WHERE nm_id IS NOT NULL

    UNION

    SELECT nm_id
    FROM stock_end
    WHERE nm_id IS NOT NULL
)

SELECT
    p.nm_id,

    COALESCE(
        s.usk,
        sp.usk,
        se.usk
    ) AS usk,

    COALESCE(
        s.brand,
        sp.brand,
        se.brand
    ) AS brand,

    COALESCE(
        s.subject_name,
        sp.subject_name,
        se.subject_name
    ) AS subject_name,

    COALESCE(
        s.title,
        sp.title,
        se.title,
        'Без наименования'
    ) AS title,

    ROUND(
        COALESCE(s.amount, 0) / 100.00,
        2
    ) AS amount,

    ROUND(
        COALESCE(s.retail_amount, 0) / 100.00,
        2
    ) AS retail_amount,

    ROUND(
        CASE
            WHEN COALESCE(s.amount, 0) = 0
                THEN NULL
            ELSE (
                s.amount - s.retail_amount
            ) / s.amount * 100
        END,
        2
    ) AS wb_discount,

    ROUND(
        COALESCE(s.vat_amount, 0) / 100.00,
        2
    ) AS vat_amount,

    ROUND(
        COALESCE(s.amount_vatless, 0) / 100.00,
        2
    ) AS amount_vatless,

    ROUND(
        COALESCE(s.cogs, 0) / 100.00,
        2
    ) AS cogs,

    ROUND(
        COALESCE(s.cogs_man, 0) / 100.00,
        2
    ) AS cogs_man,

    ROUND(
        COALESCE(s.net_comission, 0) / 100.00,
        2
    ) AS net_comission,

    ROUND(
        (
            COALESCE(s.amount_vatless, 0)
            - COALESCE(s.cogs, 0)
            + COALESCE(s.net_comission, 0)
        ) / 100.00,
        2
    ) AS margin,

    ROUND(
        (
            COALESCE(s.amount_vatless, 0)
            - COALESCE(s.cogs_man, 0)
            + COALESCE(s.net_comission, 0)
        ) / 100.00,
        2
    ) AS margin_man,

    COALESCE(
        s.total_net_sales,
        0
    ) AS total_net_sales,

    COALESCE(
        s.no_cost,
        0
    ) AS no_cost,

    COALESCE(
        s.no_stocks,
        0
    ) AS no_stocks,

    COALESCE(
        s.no_income,
        0
    ) AS no_income,

    ROUND(
        CASE
            WHEN COALESCE(s.amount_vatless, 0) = 0
                THEN NULL
            ELSE s.cogs_man
                 / s.amount_vatless
                 * 100
        END,
        2
    ) AS cogs_man_share,

    ROUND(
        CASE
            WHEN COALESCE(s.amount_vatless, 0) = 0
                THEN NULL
            ELSE -s.net_comission
                 / s.amount_vatless
                 * 100
        END,
        2
    ) AS commision_percent,

    ROUND(
        CASE
            WHEN COALESCE(s.amount_vatless, 0) = 0
                THEN NULL
            ELSE (
                s.amount_vatless
                - s.cogs_man
                + s.net_comission
            ) / s.amount_vatless * 100
        END,
        2
    ) AS margin_percent,

    sp.stock_quantity_sum,
    sp.stock_days_count,
    sp.first_stock_date,
    sp.last_stock_date,

    ROUND(
        CASE
            WHEN COALESCE(
                s.total_net_sales,
                0
            ) <= 0
                THEN NULL

            WHEN sp.stock_quantity_sum IS NULL
                THEN NULL

            ELSE
                sp.stock_quantity_sum
                / s.total_net_sales
        END,
        2
    ) AS turnover_days,

    se.ending_stock_date,
    se.ending_stock,
    se.ending_warehouse_stock,
    se.ending_in_transit_stock,

    CASE
        WHEN se.ending_stock IS NULL
            THEN 'Нет данных об остатке'

        WHEN se.ending_stock > 0
         AND COALESCE(s.total_net_sales, 0) <= 0
         AND COALESCE(s.usk, sp.usk, se.usk) IS NULL
            THEN 'Остаток без продаж и USK'

        WHEN se.ending_stock > 0
         AND COALESCE(s.total_net_sales, 0) <= 0
            THEN 'Остаток без продаж'

        WHEN se.ending_stock > 0
         AND COALESCE(s.usk, sp.usk, se.usk) IS NULL
            THEN 'Нет USK'

        WHEN COALESCE(
            sp.stock_days_count,
            0
        ) = 0
            THEN 'Нет истории остатков'

        ELSE 'Есть продажи'
    END AS stock_status

FROM product_universe p

LEFT JOIN sales_agg s
    ON s.nm_id = p.nm_id

LEFT JOIN stock_period sp
    ON sp.nm_id = p.nm_id

LEFT JOIN stock_end se
    ON se.nm_id = p.nm_id

ORDER BY
    CASE
        WHEN COALESCE(
            s.total_net_sales,
            0
        ) > 0
            THEN 0
        ELSE 1
    END,

    s.amount DESC NULLS LAST,
    se.ending_stock DESC NULLS LAST
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
AND NOT STARTS_WITH(btn, 'Платеж')
AND NOT STARTS_WITH(btn, 'Перевод')
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