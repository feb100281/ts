# # gear/app/stats/data.py
# from __future__ import annotations

# from datetime import date

# import pandas as pd

# from conns import get_duckdb_conn_with_opt
# from ..data.base import DashboardData


# def get_stats_data(
#     date_from: str | None = None,
#     date_to: str | None = None,
# ) -> pd.DataFrame:
#     """
#     Возвращает дневную статистику:

#     - выручка;
#     - маркетинговые расходы;
#     - количество проданных единиц.

#     ВАЖНО:
#     одна строка с field='retail_price'
#     и oper='dt' считается одной проданной единицей.
#     """

#     where_conditions = [
#         "date_from IS NOT NULL",
#     ]

#     params: list[str] = []

#     if date_from:
#         where_conditions.append(
#             "date_from::DATE >= CAST(? AS DATE)"
#         )
#         params.append(
#             str(date_from)[:10]
#         )

#     if date_to:
#         where_conditions.append(
#             "date_from::DATE <= CAST(? AS DATE)"
#         )
#         params.append(
#             str(date_to)[:10]
#         )

#     where_sql = "\nAND ".join(
#         where_conditions
#     )

#     with get_duckdb_conn_with_opt(
#         ro=True
#     ) as con:
#         df = con.execute(
#             f"""
#             SELECT
#                 date_from::DATE AS date,

#                 SUM(val) FILTER (
#                     WHERE
#                         field = 'retail_price'
#                         AND oper = 'dt'
#                 ) / 100.0 AS revenue,

#                 SUM(val) FILTER (
#                     WHERE
#                         field = 'deduction'
#                         AND oper = 'cr'
#                         AND COALESCE(
#                             btn,
#                             ''
#                         ) LIKE '%Продв%'
#                 ) / 100.0 AS marketing_costs,

#                 COUNT(*) FILTER (
#                     WHERE
#                         field = 'retail_price'
#                         AND oper = 'dt'
#                 ) AS quantity

#             FROM sales.sales_long

#             WHERE
#                 {where_sql}

#             GROUP BY
#                 date_from::DATE

#             ORDER BY
#                 date_from::DATE
#             """,
#             params,
#         ).df()

#     if df.empty:
#         return df

#     df["date"] = pd.to_datetime(
#         df["date"],
#         errors="coerce",
#     )

#     numeric_columns = [
#         "revenue",
#         "marketing_costs",
#         "quantity",
#     ]

#     for column in numeric_columns:
#         df[column] = pd.to_numeric(
#             df[column],
#             errors="coerce",
#         ).fillna(0)

#     # Средняя цена реализации одной единицы.
#     df["average_price"] = (
#         df["revenue"]
#         / df["quantity"].replace(
#             0,
#             pd.NA,
#         )
#     )

#     return (
#         df.sort_values("date")
#         .reset_index(drop=True)
#     )


# def get_stats_min_date() -> date:
#     """
#     Минимальная дата в sales_long.
#     """

#     with get_duckdb_conn_with_opt(
#         ro=True
#     ) as con:
#         result = con.execute(
#             """
#             SELECT
#                 MIN(date_from)::DATE
#             FROM sales.sales_long
#             WHERE date_from IS NOT NULL
#             """
#         ).fetchone()

#     if result and result[0]:
#         return result[0]

#     return date.today()

# with DashboardData() as dd:
#     pass



# # gear/app/stats/data.py

# from __future__ import annotations

# from datetime import date

# import pandas as pd

# from conns import get_duckdb_conn_with_opt


# # =====================================================================
# # Создание временной таблицы base
# # =====================================================================

# BASE_QUERY = """
# CREATE OR REPLACE TEMP TABLE base AS

# WITH last_val AS (

#     SELECT
#         usk,

#         adjust_wo[-1]
#             AS last_cr,

#         adjust_man_wo[-1]
#             AS last_man_cr

#     FROM inventories.pre_wo
# ),


# -- ===================================================================
# -- Списания без текущей себестоимости:
# -- подставляем последнюю известную себестоимость
# -- ===================================================================

# add_last AS (

#     SELECT
#         t.*,

#         l.last_cr,

#         l.last_man_cr

#     FROM inventories.inv_gl_final t

#     LEFT JOIN last_val l
#         ON l.usk = t.usk

#     WHERE
#         t.cr = 0
#         AND t.oper = 'Списание'
# ),


# -- ===================================================================
# -- Цена реализации WB
# --
# -- retail_amount хранится в копейках и содержит НДС.
# -- Здесь пока оставляем исходное значение.
# -- Перевод в рубли и исключение НДС выполняются
# -- в итоговом статистическом запросе.
# -- ===================================================================

# wb_price AS (

#     SELECT
#         rrd_id,

#         SUM(
#             val
#         ) AS retail_amount

#     FROM sales.sales_long

#     WHERE
#         field = 'retail_amount'

#     GROUP BY
#         rrd_id
# ),


# -- ===================================================================
# -- Ставка НДС по каждой операции
# --
# -- Нам нужна одна ставка на rrd_id.
# -- Отдельный CTE нужен, чтобы НЕ размножать строки
# -- при прямом JOIN с sales.sales_long.
# -- ===================================================================

# rrd_vat AS (

#     SELECT
#         rrd_id,

#         MAX(
#             COALESCE(
#                 vat_rate,
#                 0
#             )
#         ) AS vat_rate

#     FROM sales.sales_long

#     WHERE
#         rrd_id IS NOT NULL

#     GROUP BY
#         rrd_id
# ),


# -- ===================================================================
# -- Комиссия WB
# --
# -- Повторяем методологию DAILY_SALES_AGG:
# --
# -- dt - cr
# --
# -- Комиссия сразу приводится к значению БЕЗ НДС.
# --
# -- В результате net_comission обычно отрицательная,
# -- поэтому прибыль:
# --
# -- revenue_vatless
# -- - cogs
# -- + net_comission
# -- ===================================================================

# commissions AS (

#     SELECT
#         rrd_id,

#         COALESCE(
#             SUM(
#                 val
#                 / (
#                     100
#                     +
#                     COALESCE(
#                         vat_rate,
#                         0
#                     )
#                 )
#                 * 100
#             ) FILTER (
#                 WHERE
#                     field = 'comission'
#                     AND oper = 'dt'
#             ),
#             0
#         )
#         -
#         COALESCE(
#             SUM(
#                 val
#                 / (
#                     100
#                     +
#                     COALESCE(
#                         vat_rate,
#                         0
#                     )
#                 )
#                 * 100
#             ) FILTER (
#                 WHERE
#                     field = 'comission'
#                     AND oper = 'cr'
#             ),
#             0
#         ) AS net_comission

#     FROM sales.sales_long

#     GROUP BY
#         rrd_id
# )


# SELECT

#     YEARWEEK(
#         t.date_from::DATE
#     ) AS yw,

#     t.*,


#     -- =================================================================
#     -- WB
#     -- =================================================================

#     COALESCE(
#         wb.retail_amount,
#         0
#     ) AS retail_amount,

#     COALESCE(
#         c.net_comission,
#         0
#     ) AS net_comission,

#     COALESCE(
#         rv.vat_rate,
#         0
#     ) AS vat_rate,


#     -- =================================================================
#     -- Себестоимость
#     -- =================================================================

#     a.last_cr,

#     a.last_man_cr,


#     COALESCE(
#         a.last_cr,

#         CASE
#             WHEN t.cr = 0
#                 THEN 95000

#             ELSE t.cr
#         END

#     ) AS adjusted_cogs,


#     COALESCE(
#         a.last_man_cr,

#         CASE
#             WHEN t.cr_man = 0
#                 THEN 62000

#             ELSE t.cr_man
#         END

#     ) AS adjusted_cogs_man,


#     -- =================================================================
#     -- Карточка товара
#     -- =================================================================

#     UPPER(
#         w.brand
#     ) AS brand,

#     w.subject_id,

#     w.subject_name,

#     w.title,

#     COALESCE(
#         w.gender,
#         'Не указан'
#     ) AS gender,


#     -- =================================================================
#     -- Контроль себестоимости
#     -- =================================================================

#     CASE

#         WHEN
#             t.cr = 0
#             AND a.last_cr <> 0
#             AND t.oper = 'Списание'
#         THEN
#             'Нет на складе'

#         WHEN
#             t.cr = 0
#             AND a.last_cr IS NULL
#             AND t.oper = 'Списание'
#         THEN
#             'Нет приходов'

#         ELSE NULL

#     END AS storage_flag


# FROM inventories.inv_gl_final t

# LEFT JOIN add_last a
#     ON a.rrd_id = t.rrd_id

# LEFT JOIN inventories.wb_product w
#     ON w.card_id = t.usk

# LEFT JOIN wb_price wb
#     ON wb.rrd_id = t.rrd_id

# LEFT JOIN commissions c
#     ON c.rrd_id = t.rrd_id

# LEFT JOIN rrd_vat rv
#     ON rv.rrd_id = t.rrd_id
# ;
# """


# # =====================================================================
# # Создание временной таблицы wb_costs
# # =====================================================================

# WB_COSTS_QUERY = """
# CREATE OR REPLACE TEMP TABLE wb_costs AS

# WITH raw_costs AS (


#     -- =================================================================
#     -- Корректировки
#     -- =================================================================

#     SELECT
#         date_from,

#         rrd_id,

#         'Other income / loss'
#             AS account,

#         sop_name
#             AS cost_item,

#         COALESCE(
#             SUM(
#                 val
#             ) FILTER (
#                 WHERE oper = 'dt'
#             ),
#             0
#         ) AS dt,

#         COALESCE(
#             SUM(
#                 val
#             ) FILTER (
#                 WHERE oper = 'cr'
#             ),
#             0
#         ) AS cr

#     FROM sales.sales_long

#     WHERE
#         field = 'retail_price'
#         AND sop_name LIKE '%оррекция%'

#     GROUP BY
#         date_from,
#         rrd_id,
#         sop_name


#     UNION ALL


#     -- =================================================================
#     -- Логистика
#     -- =================================================================

#     SELECT
#         date_from,

#         rrd_id,

#         'WB Logistic'
#             AS account,

#         COALESCE(
#             btn,
#             sop_name
#         ) AS cost_item,

#         COALESCE(
#             SUM(
#                 val
#             ) FILTER (
#                 WHERE oper = 'dt'
#             ),
#             0
#         ) AS dt,

#         COALESCE(
#             SUM(
#                 val
#             ) FILTER (
#                 WHERE oper = 'cr'
#             ),
#             0
#         ) AS cr

#     FROM sales.sales_long

#     WHERE
#         field = 'delivery_rub'

#     GROUP BY
#         date_from,
#         rrd_id,
#         COALESCE(
#             btn,
#             sop_name
#         )


#     UNION ALL


#     -- =================================================================
#     -- Хранение
#     -- =================================================================

#     SELECT
#         date_from,

#         rrd_id,

#         'WB Storage'
#             AS account,

#         sop_name
#             AS cost_item,

#         COALESCE(
#             SUM(
#                 val
#             ) FILTER (
#                 WHERE oper = 'dt'
#             ),
#             0
#         ) AS dt,

#         COALESCE(
#             SUM(
#                 val
#             ) FILTER (
#                 WHERE oper = 'cr'
#             ),
#             0
#         ) AS cr

#     FROM sales.sales_long

#     WHERE
#         field = 'storage_fee'

#     GROUP BY
#         date_from,
#         rrd_id,
#         sop_name


#     UNION ALL


#     -- =================================================================
#     -- Приёмка
#     -- =================================================================

#     SELECT
#         date_from,

#         rrd_id,

#         'WB Acceptance'
#             AS account,

#         sop_name
#             AS cost_item,

#         COALESCE(
#             SUM(
#                 val
#             ) FILTER (
#                 WHERE oper = 'dt'
#             ),
#             0
#         ) AS dt,

#         COALESCE(
#             SUM(
#                 val
#             ) FILTER (
#                 WHERE oper = 'cr'
#             ),
#             0
#         ) AS cr

#     FROM sales.sales_long

#     WHERE
#         field = 'acceptance'

#     GROUP BY
#         date_from,
#         rrd_id,
#         sop_name


#     UNION ALL


#     -- =================================================================
#     -- Штрафы
#     -- =================================================================

#     SELECT
#         date_from,

#         rrd_id,

#         'WB Penalties'
#             AS account,

#         btn
#             AS cost_item,

#         COALESCE(
#             SUM(
#                 val
#             ) FILTER (
#                 WHERE oper = 'dt'
#             ),
#             0
#         ) AS dt,

#         COALESCE(
#             SUM(
#                 val
#             ) FILTER (
#                 WHERE oper = 'cr'
#             ),
#             0
#         ) AS cr

#     FROM sales.sales_long

#     WHERE
#         field = 'penalty'

#     GROUP BY
#         date_from,
#         rrd_id,
#         btn


#     UNION ALL


#     -- =================================================================
#     -- Удержания WB
#     --
#     -- Здесь отдельно выделяем:
#     --
#     -- Продвижение
#     -- Отзывы
#     -- Услуги WB
#     -- Прочее
#     -- =================================================================

#     SELECT
#         date_from,

#         rrd_id,

#         'WB Deduction'
#             AS account,

#         CASE

#             WHEN
#                 STARTS_WITH(
#                     btn,
#                     'Списание за отзыв'
#                 )
#             THEN
#                 'Отзывы'


#             WHEN
#                 btn ILIKE '%Продв%'
#             THEN
#                 'Продвижение'


#             WHEN
#                 STARTS_WITH(
#                     btn,
#                     'Оказание услуг'
#                 )
#                 OR
#                 STARTS_WITH(
#                     btn,
#                     'Предоставление услуг'
#                 )
#                 OR
#                 STARTS_WITH(
#                     btn,
#                     'Витрина Магазина'
#                 )
#             THEN
#                 'Услуги WB'


#             ELSE
#                 'Прочее'

#         END AS cost_item,


#         COALESCE(
#             SUM(
#                 val
#             ) FILTER (
#                 WHERE oper = 'dt'
#             ),
#             0
#         ) AS dt,


#         COALESCE(
#             SUM(
#                 val
#             ) FILTER (
#                 WHERE oper = 'cr'
#             ),
#             0
#         ) AS cr


#     FROM sales.sales_long

#     WHERE
#         field = 'deduction'

#         AND btn IS NOT NULL

#         AND NOT (
#             STARTS_WITH(
#                 btn,
#                 'Платеж'
#             )
#             OR
#             STARTS_WITH(
#                 btn,
#                 'Перевод'
#             )
#         )

#     GROUP BY
#         date_from,
#         rrd_id,
#         cost_item


#     UNION ALL


#     -- =================================================================
#     -- Лояльность / кешбэк
#     -- =================================================================

#     SELECT
#         date_from,

#         rrd_id,

#         'WB Loyality'
#             AS account,

#         btn
#             AS cost_item,

#         COALESCE(
#             SUM(
#                 val
#             ) FILTER (
#                 WHERE oper = 'dt'
#             ),
#             0
#         ) AS dt,

#         COALESCE(
#             SUM(
#                 val
#             ) FILTER (
#                 WHERE oper = 'cr'
#             ),
#             0
#         ) AS cr

#     FROM sales.sales_long

#     WHERE
#         field IN (
#             'cashback_commission_change',
#             'cashback_amount'
#         )

#     GROUP BY
#         date_from,
#         rrd_id,
#         btn
# ),


# -- ===================================================================
# -- Одна ставка НДС на rrd_id
# --
# -- Нельзя просто JOIN sales_long по rrd_id,
# -- иначе расходы могут размножиться.
# -- ===================================================================

# rrd_vat AS (

#     SELECT
#         rrd_id,

#         MAX(
#             COALESCE(
#                 vat_rate,
#                 0
#             )
#         ) AS vat_rate

#     FROM sales.sales_long

#     WHERE
#         rrd_id IS NOT NULL

#     GROUP BY
#         rrd_id
# )


# SELECT

#     YEARWEEK(
#         t.date_from::DATE
#     ) AS yw,

#     t.*,

#     COALESCE(
#         v.vat_rate,
#         0
#     ) AS vat_rate

# FROM raw_costs t

# LEFT JOIN rrd_vat v
#     ON v.rrd_id = t.rrd_id
# ;
# """


# # =====================================================================
# # Основная функция данных статистики
# # =====================================================================

# def get_stats_data(
#     date_from: str | None = None,
#     date_to: str | None = None,
# ) -> pd.DataFrame:
#     """
#     Возвращает данные по дням для приложения
#     "Статистика и аналитика".

#     Внутри одного DuckDB-соединения:

#     1. создаётся TEMP TABLE base;
#     2. создаётся TEMP TABLE wb_costs;
#     3. формируются дневные агрегаты.

#     ---------------------------------------------------------------

#     ПРОДАЖИ

#     Источник:
#         base

#     Условие:
#         oper = 'Списание'

#     Количество:
#         одна строка списания = одна единица продажи.

#     ---------------------------------------------------------------

#     ВЫРУЧКА

#     cr_rev:
#         наша выручка с НДС,
#         исходно в копейках.

#     Формула:

#         cr_rev
#         / 100
#         / (1 + vat_rate / 100)

#     ---------------------------------------------------------------

#     RETAIL WB

#     retail_amount:
#         стоимость реализации WB с НДС,
#         исходно в копейках.

#     ---------------------------------------------------------------

#     СЕБЕСТОИМОСТЬ

#     adjusted_cogs:
#         бухгалтерская.

#     adjusted_cogs_man:
#         управленческая.

#     Обе переводятся:
#         копейки -> рубли.

#     ---------------------------------------------------------------

#     КОМИССИЯ

#     net_comission уже очищена от НДС
#     при создании таблицы base.

#     Поэтому только:
#         копейки -> рубли.

#     ---------------------------------------------------------------

#     WB COSTS

#     Расход:
#         dt - cr

#     Затем:
#         копейки -> рубли;
#         исключаем НДС.

#     ---------------------------------------------------------------
#     """

#     sales_conditions = [
#         "t.oper = 'Списание'",
#     ]

#     sales_params: list[str] = []

#     if date_from:
#         sales_conditions.append(
#             """
#             t.date_from::DATE
#             >= CAST(? AS DATE)
#             """
#         )

#         sales_params.append(
#             str(date_from)[:10]
#         )

#     if date_to:
#         sales_conditions.append(
#             """
#             t.date_from::DATE
#             <= CAST(? AS DATE)
#             """
#         )

#         sales_params.append(
#             str(date_to)[:10]
#         )

#     sales_where = (
#         "\nAND ".join(
#             sales_conditions
#         )
#     )


#     # -----------------------------------------------------------------
#     # Расходы WB
#     # -----------------------------------------------------------------

#     costs_conditions = [
#         "1 = 1",
#     ]

#     costs_params: list[str] = []

#     if date_from:
#         costs_conditions.append(
#             """
#             t.date_from::DATE
#             >= CAST(? AS DATE)
#             """
#         )

#         costs_params.append(
#             str(date_from)[:10]
#         )

#     if date_to:
#         costs_conditions.append(
#             """
#             t.date_from::DATE
#             <= CAST(? AS DATE)
#             """
#         )

#         costs_params.append(
#             str(date_to)[:10]
#         )

#     costs_where = (
#         "\nAND ".join(
#             costs_conditions
#         )
#     )


#     # -----------------------------------------------------------------
#     # Одно соединение:
#     #
#     # temp tables живут только внутри этого соединения.
#     # -----------------------------------------------------------------

#     with get_duckdb_conn_with_opt() as con:

#         # -------------------------------------------------------------
#         # Создаём base
#         # -------------------------------------------------------------

#         con.execute(
#             BASE_QUERY
#         )

#         # -------------------------------------------------------------
#         # Создаём wb_costs
#         # -------------------------------------------------------------

#         con.execute(
#             WB_COSTS_QUERY
#         )


#         # -------------------------------------------------------------
#         # Итоговая статистика
#         # -------------------------------------------------------------

#         df = con.execute(
#             f"""
#             WITH sales_daily AS (

#                 SELECT

#                     t.date_from::DATE
#                         AS date,


#                     -- =================================================
#                     -- Количество проданных единиц
#                     --
#                     -- одна строка Списания = одна единица
#                     -- =================================================

#                     COUNT(*)
#                         AS quantity,


#                     -- =================================================
#                     -- Наша выручка БЕЗ НДС, руб.
#                     --
#                     -- cr_rev:
#                     -- копейки + НДС
#                     -- =================================================

#                     SUM(

#                         COALESCE(
#                             t.cr_rev,
#                             0
#                         )

#                         / 100.0

#                         / (

#                             1

#                             +

#                             COALESCE(
#                                 t.vat_rate,
#                                 0
#                             )
#                             / 100.0

#                         )

#                     ) AS revenue,


#                     -- =================================================
#                     -- Реализация WB БЕЗ НДС, руб.
#                     -- =================================================

#                     SUM(

#                         COALESCE(
#                             t.retail_amount,
#                             0
#                         )

#                         / 100.0

#                         / (

#                             1

#                             +

#                             COALESCE(
#                                 t.vat_rate,
#                                 0
#                             )
#                             / 100.0

#                         )

#                     ) AS retail_revenue,


#                     -- =================================================
#                     -- Бухгалтерская себестоимость, руб.
#                     -- =================================================

#                     SUM(

#                         COALESCE(
#                             t.adjusted_cogs,
#                             0
#                         )

#                         / 100.0

#                     ) AS cogs,


#                     -- =================================================
#                     -- Управленческая себестоимость, руб.
#                     -- =================================================

#                     SUM(

#                         COALESCE(
#                             t.adjusted_cogs_man,
#                             0
#                         )

#                         / 100.0

#                     ) AS cogs_man,


#                     -- =================================================
#                     -- Комиссия WB без НДС, руб.
#                     --
#                     -- net_comission уже очищена от НДС
#                     -- в CTE commissions.
#                     -- =================================================

#                     SUM(

#                         COALESCE(
#                             t.net_comission,
#                             0
#                         )

#                         / 100.0

#                     ) AS net_comission


#                 FROM base t

#                 WHERE

#                     {sales_where}

#                 GROUP BY

#                     t.date_from::DATE
#             ),


#             costs_daily AS (

#                 SELECT

#                     t.date_from::DATE
#                         AS date,


#                     -- =================================================
#                     -- Все расходы WB
#                     -- БЕЗ НДС, руб.
#                     -- =================================================

#                     SUM(

#                         (

#                             COALESCE(
#                                 t.dt,
#                                 0
#                             )

#                             -

#                             COALESCE(
#                                 t.cr,
#                                 0
#                             )

#                         )

#                         / 100.0

#                         / (

#                             1

#                             +

#                             COALESCE(
#                                 t.vat_rate,
#                                 0
#                             )
#                             / 100.0

#                         )

#                     ) AS wb_costs,


#                     -- =================================================
#                     -- Маркетинг / продвижение
#                     -- =================================================

#                     SUM(

#                         CASE

#                             WHEN

#                                 t.account
#                                 = 'WB Deduction'

#                                 -- AND

#                                 -- t.cost_item
#                                 -- = 'Продвижение'

#                             THEN

#                                 (

#                                     COALESCE(
#                                         t.dt,
#                                         0
#                                     )

#                                     -

#                                     COALESCE(
#                                         t.cr,
#                                         0
#                                     )

#                                 )

#                                 / 100.0

#                                 / (

#                                     1

#                                     +

#                                     COALESCE(
#                                         t.vat_rate,
#                                         0
#                                     )
#                                     / 100.0

#                                 )

#                             ELSE 0

#                         END

#                     ) AS marketing_costs,


#                     -- =================================================
#                     -- Логистика
#                     -- =================================================

#                     SUM(

#                         CASE

#                             WHEN
#                                 t.account
#                                 = 'WB Logistic'

#                             THEN

#                                 (

#                                     COALESCE(
#                                         t.dt,
#                                         0
#                                     )

#                                     -

#                                     COALESCE(
#                                         t.cr,
#                                         0
#                                     )

#                                 )

#                                 / 100.0

#                                 / (

#                                     1

#                                     +

#                                     COALESCE(
#                                         t.vat_rate,
#                                         0
#                                     )
#                                     / 100.0

#                                 )

#                             ELSE 0

#                         END

#                     ) AS logistics_costs,


#                     -- =================================================
#                     -- Хранение
#                     -- =================================================

#                     SUM(

#                         CASE

#                             WHEN
#                                 t.account
#                                 = 'WB Storage'

#                             THEN

#                                 (

#                                     COALESCE(
#                                         t.dt,
#                                         0
#                                     )

#                                     -

#                                     COALESCE(
#                                         t.cr,
#                                         0
#                                     )

#                                 )

#                                 / 100.0

#                                 / (

#                                     1

#                                     +

#                                     COALESCE(
#                                         t.vat_rate,
#                                         0
#                                     )
#                                     / 100.0

#                                 )

#                             ELSE 0

#                         END

#                     ) AS storage_costs,


#                     -- =================================================
#                     -- Приёмка
#                     -- =================================================

#                     SUM(

#                         CASE

#                             WHEN
#                                 t.account
#                                 = 'WB Acceptance'

#                             THEN

#                                 (

#                                     COALESCE(
#                                         t.dt,
#                                         0
#                                     )

#                                     -

#                                     COALESCE(
#                                         t.cr,
#                                         0
#                                     )

#                                 )

#                                 / 100.0

#                                 / (

#                                     1

#                                     +

#                                     COALESCE(
#                                         t.vat_rate,
#                                         0
#                                     )
#                                     / 100.0

#                                 )

#                             ELSE 0

#                         END

#                     ) AS acceptance_costs,


#                     -- =================================================
#                     -- Штрафы
#                     -- =================================================

#                     SUM(

#                         CASE

#                             WHEN
#                                 t.account
#                                 = 'WB Penalties'

#                             THEN

#                                 (

#                                     COALESCE(
#                                         t.dt,
#                                         0
#                                     )

#                                     -

#                                     COALESCE(
#                                         t.cr,
#                                         0
#                                     )

#                                 )

#                                 / 100.0

#                                 / (

#                                     1

#                                     +

#                                     COALESCE(
#                                         t.vat_rate,
#                                         0
#                                     )
#                                     / 100.0

#                                 )

#                             ELSE 0

#                         END

#                     ) AS penalties_costs,


#                     -- =================================================
#                     -- Отзывы
#                     -- =================================================

#                     SUM(

#                         CASE

#                             WHEN

#                                 t.account
#                                 = 'WB Deduction'

#                                 -- AND

#                                 -- t.cost_item
#                                 -- = 'Отзывы'

#                             THEN

#                                 (

#                                     COALESCE(
#                                         t.dt,
#                                         0
#                                     )

#                                     -

#                                     COALESCE(
#                                         t.cr,
#                                         0
#                                     )

#                                 )

#                                 / 100.0

#                                 / (

#                                     1

#                                     +

#                                     COALESCE(
#                                         t.vat_rate,
#                                         0
#                                     )
#                                     / 100.0

#                                 )

#                             ELSE 0

#                         END

#                     ) AS review_costs,


#                     -- =================================================
#                     -- Услуги WB
#                     -- =================================================

#                     SUM(

#                         CASE

#                             WHEN

#                                 t.account
#                                 = 'WB Deduction'

#                                 -- AND

#                                 -- t.cost_item
#                                 -- = 'Услуги WB'

#                             THEN

#                                 (

#                                     COALESCE(
#                                         t.dt,
#                                         0
#                                     )

#                                     -

#                                     COALESCE(
#                                         t.cr,
#                                         0
#                                     )

#                                 )

#                                 / 100.0

#                                 / (

#                                     1

#                                     +

#                                     COALESCE(
#                                         t.vat_rate,
#                                         0
#                                     )
#                                     / 100.0

#                                 )

#                             ELSE 0

#                         END

#                     ) AS wb_service_costs


#                 FROM wb_costs t

#                 WHERE

#                     {costs_where}

#                 GROUP BY

#                     t.date_from::DATE
#             )


#             SELECT

#                 s.date,


#                 YEARWEEK(
#                     s.date
#                 ) AS yw,


#                 -- =====================================================
#                 -- Продажи
#                 -- =====================================================

#                 s.quantity,

#                 s.revenue,

#                 s.retail_revenue,


#                 -- =====================================================
#                 -- Себестоимость
#                 -- =====================================================

#                 s.cogs,

#                 s.cogs_man,


#                 -- =====================================================
#                 -- Комиссия
#                 -- =====================================================

#                 s.net_comission,


#                 -- =====================================================
#                 -- Расходы WB
#                 -- =====================================================

#                 COALESCE(
#                     c.wb_costs,
#                     0
#                 ) AS wb_costs,


#                 COALESCE(
#                     c.marketing_costs,
#                     0
#                 ) AS marketing_costs,


#                 COALESCE(
#                     c.logistics_costs,
#                     0
#                 ) AS logistics_costs,


#                 COALESCE(
#                     c.storage_costs,
#                     0
#                 ) AS storage_costs,


#                 COALESCE(
#                     c.acceptance_costs,
#                     0
#                 ) AS acceptance_costs,


#                 COALESCE(
#                     c.penalties_costs,
#                     0
#                 ) AS penalties_costs,


#                 COALESCE(
#                     c.review_costs,
#                     0
#                 ) AS review_costs,


#                 COALESCE(
#                     c.wb_service_costs,
#                     0
#                 ) AS wb_service_costs,


#                 -- =====================================================
#                 -- Средняя наша цена реализации БЕЗ НДС
#                 -- =====================================================

#                 s.revenue

#                 / NULLIF(
#                     s.quantity,
#                     0
#                 ) AS average_price,


#                 -- =====================================================
#                 -- Средняя цена реализации WB БЕЗ НДС
#                 -- =====================================================

#                 s.retail_revenue

#                 / NULLIF(
#                     s.quantity,
#                     0
#                 ) AS average_retail_price,


#                 -- =====================================================
#                 -- Средняя бухгалтерская себестоимость
#                 -- =====================================================

#                 s.cogs

#                 / NULLIF(
#                     s.quantity,
#                     0
#                 ) AS average_cogs,


#                 -- =====================================================
#                 -- Средняя управленческая себестоимость
#                 -- =====================================================

#                 s.cogs_man

#                 / NULLIF(
#                     s.quantity,
#                     0
#                 ) AS average_cogs_man,


#                 -- =====================================================
#                 -- Валовая прибыль бухгалтерская
#                 -- =====================================================

#                 (

#                     s.revenue

#                     -

#                     s.cogs

#                 ) AS gross_profit,


#                 -- =====================================================
#                 -- Валовая прибыль управленческая
#                 -- =====================================================

#                 (

#                     s.revenue

#                     -

#                     s.cogs_man

#                 ) AS gross_profit_man,


#                 -- =====================================================
#                 -- Маржа бухгалтерская после комиссии
#                 --
#                 -- net_comission обычно отрицательная
#                 -- =====================================================

#                 (

#                     s.revenue

#                     -

#                     s.cogs

#                     +

#                     s.net_comission

#                 ) AS margin,


#                 -- =====================================================
#                 -- Маржа управленческая после комиссии
#                 -- =====================================================

#                 (

#                     s.revenue

#                     -

#                     s.cogs_man

#                     +

#                     s.net_comission

#                 ) AS margin_man,


#                 -- =====================================================
#                 -- Финансовый результат WB
#                 --
#                 -- Управленческая методология
#                 -- =====================================================

#                 (

#                     s.revenue

#                     -

#                     s.cogs_man

#                     +

#                     s.net_comission

#                     -

#                     COALESCE(
#                         c.wb_costs,
#                         0
#                     )

#                 ) AS wb_result


#             FROM sales_daily s

#             LEFT JOIN costs_daily c
#                 ON c.date = s.date

#             ORDER BY

#                 s.date
#             """,

#             [
#                 *sales_params,
#                 *costs_params,
#             ],

#         ).df()


#     # =================================================================
#     # Пустой результат
#     # =================================================================

#     if df.empty:
#         return df


#     # =================================================================
#     # Типы данных
#     # =================================================================

#     df["date"] = pd.to_datetime(
#         df["date"],
#         errors="coerce",
#     )


#     numeric_columns = [

#         "quantity",

#         "revenue",

#         "retail_revenue",

#         "cogs",

#         "cogs_man",

#         "net_comission",

#         "wb_costs",

#         "marketing_costs",

#         "logistics_costs",

#         "storage_costs",

#         "acceptance_costs",

#         "penalties_costs",

#         "review_costs",

#         "wb_service_costs",

#         "average_price",

#         "average_retail_price",

#         "average_cogs",

#         "average_cogs_man",

#         "gross_profit",

#         "gross_profit_man",

#         "margin",

#         "margin_man",

#         "wb_result",

#     ]


#     for column in numeric_columns:

#         if column in df.columns:

#             df[column] = pd.to_numeric(
#                 df[column],
#                 errors="coerce",
#             )


#     return (

#         df.sort_values(
#             "date"
#         )

#         .reset_index(
#             drop=True
#         )

#     )


# # =====================================================================
# # Минимальная дата
# # =====================================================================

# def get_stats_min_date() -> date:
#     """
#     Минимальная дата продаж.

#     Отдельные TEMP TABLE здесь создавать не нужно.
#     Достаточно посмотреть минимальную дату
#     списания в inventories.inv_gl_final.
#     """

#     with get_duckdb_conn_with_opt(
#         ro=True
#     ) as con:

#         result = con.execute(
#             """
#             SELECT
#                 MIN(
#                     date_from::DATE
#                 )

#             FROM inventories.inv_gl_final

#             WHERE
#                 oper = 'Списание'
#             """
#         ).fetchone()


#     if (
#         result
#         and result[0]
#     ):
#         return result[0]


#     return date.today()




# gear/app/stats/data.py

from __future__ import annotations

from datetime import date

import pandas as pd

from conns import get_duckdb_conn_with_opt


# =====================================================================
# TEMP TABLE: base
# =====================================================================

BASE_QUERY = """
CREATE OR REPLACE TEMP TABLE base AS

WITH last_val AS (

    SELECT
        usk,
        adjust_wo[-1] AS last_cr,
        adjust_man_wo[-1] AS last_man_cr

    FROM inventories.pre_wo
),


-- ===================================================================
-- Списания без текущей себестоимости.
-- Подставляем последнюю известную себестоимость.
-- ===================================================================

add_last AS (

    SELECT
        t.*,
        l.last_cr,
        l.last_man_cr

    FROM inventories.inv_gl_final t

    LEFT JOIN last_val l
        ON l.usk = t.usk

    WHERE
        t.cr = 0
        AND t.oper = 'Списание'
),


-- ===================================================================
-- Цена реализации WB.
--
-- Одна строка на rrd_id.
-- Значение остаётся в копейках и с НДС.
-- В рубли без НДС переводим уже в статистическом запросе.
-- ===================================================================

wb_price AS (

    SELECT
        rrd_id,
        SUM(val) AS retail_amount

    FROM sales.sales_long

    WHERE
        field = 'retail_amount'

    GROUP BY
        rrd_id
),


-- ===================================================================
-- Ставка НДС.
--
-- Делаем одну строку на rrd_id,
-- чтобы при JOIN не размножать данные.
-- ===================================================================

rrd_vat AS (

    SELECT
        rrd_id,

        MAX(
            COALESCE(
                vat_rate,
                0
            )
        ) AS vat_rate

    FROM sales.sales_long

    WHERE
        rrd_id IS NOT NULL

    GROUP BY
        rrd_id
),


-- ===================================================================
-- Комиссия WB.
--
-- Методология:
--
-- dt - cr
--
-- Комиссия сразу приводится к значению без НДС.
--
-- net_comission обычно отрицательная.
-- ===================================================================

commissions AS (

    SELECT
        rrd_id,

        COALESCE(
            SUM(
                val
                / (
                    100
                    +
                    COALESCE(
                        vat_rate,
                        0
                    )
                )
                * 100
            ) FILTER (
                WHERE
                    field = 'comission'
                    AND oper = 'dt'
            ),
            0
        )

        -

        COALESCE(
            SUM(
                val
                / (
                    100
                    +
                    COALESCE(
                        vat_rate,
                        0
                    )
                )
                * 100
            ) FILTER (
                WHERE
                    field = 'comission'
                    AND oper = 'cr'
            ),
            0
        )

        AS net_comission

    FROM sales.sales_long

    GROUP BY
        rrd_id
)


SELECT

    YEARWEEK(
        t.date_from::DATE
    ) AS yw,

    t.*,


    -- =================================================================
    -- WB
    -- =================================================================

    COALESCE(
        wb.retail_amount,
        0
    ) AS retail_amount,


    COALESCE(
        c.net_comission,
        0
    ) AS net_comission,


    COALESCE(
        rv.vat_rate,
        0
    ) AS vat_rate,


    -- =================================================================
    -- Себестоимость
    -- =================================================================

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


    -- =================================================================
    -- Карточка товара
    -- =================================================================

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


    -- =================================================================
    -- Контроль себестоимости
    -- =================================================================

    CASE

        WHEN
            t.cr = 0
            AND a.last_cr <> 0
            AND t.oper = 'Списание'

        THEN
            'Нет на складе'


        WHEN
            t.cr = 0
            AND a.last_cr IS NULL
            AND t.oper = 'Списание'

        THEN
            'Нет приходов'


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


LEFT JOIN rrd_vat rv
    ON rv.rrd_id = t.rrd_id
;
"""


# =====================================================================
# TEMP TABLE: wb_costs
# =====================================================================

WB_COSTS_QUERY = """
CREATE OR REPLACE TEMP TABLE wb_costs AS

WITH raw_costs AS (


    -- =================================================================
    -- Корректировки
    -- =================================================================

    SELECT
        date_from,
        rrd_id,

        'Other income / loss'
            AS account,

        sop_name
            AS cost_item,

        COALESCE(
            SUM(val) FILTER (
                WHERE oper = 'dt'
            ),
            0
        ) AS dt,

        COALESCE(
            SUM(val) FILTER (
                WHERE oper = 'cr'
            ),
            0
        ) AS cr

    FROM sales.sales_long

    WHERE
        field = 'retail_price'
        AND sop_name LIKE '%оррекция%'

    GROUP BY
        date_from,
        rrd_id,
        sop_name


    UNION ALL


    -- =================================================================
    -- Логистика
    -- =================================================================

    SELECT
        date_from,
        rrd_id,

        'WB Logistic'
            AS account,

        COALESCE(
            btn,
            sop_name
        ) AS cost_item,

        COALESCE(
            SUM(val) FILTER (
                WHERE oper = 'dt'
            ),
            0
        ) AS dt,

        COALESCE(
            SUM(val) FILTER (
                WHERE oper = 'cr'
            ),
            0
        ) AS cr

    FROM sales.sales_long

    WHERE
        field = 'delivery_rub'

    GROUP BY
        date_from,
        rrd_id,
        COALESCE(
            btn,
            sop_name
        )


    UNION ALL


    -- =================================================================
    -- Хранение
    -- =================================================================

    SELECT
        date_from,
        rrd_id,

        'WB Storage'
            AS account,

        sop_name
            AS cost_item,

        COALESCE(
            SUM(val) FILTER (
                WHERE oper = 'dt'
            ),
            0
        ) AS dt,

        COALESCE(
            SUM(val) FILTER (
                WHERE oper = 'cr'
            ),
            0
        ) AS cr

    FROM sales.sales_long

    WHERE
        field = 'storage_fee'

    GROUP BY
        date_from,
        rrd_id,
        sop_name


    UNION ALL


    -- =================================================================
    -- Приёмка
    -- =================================================================

    SELECT
        date_from,
        rrd_id,

        'WB Acceptance'
            AS account,

        sop_name
            AS cost_item,

        COALESCE(
            SUM(val) FILTER (
                WHERE oper = 'dt'
            ),
            0
        ) AS dt,

        COALESCE(
            SUM(val) FILTER (
                WHERE oper = 'cr'
            ),
            0
        ) AS cr

    FROM sales.sales_long

    WHERE
        field = 'acceptance'

    GROUP BY
        date_from,
        rrd_id,
        sop_name


    UNION ALL


    -- =================================================================
    -- Штрафы
    -- =================================================================

    SELECT
        date_from,
        rrd_id,

        'WB Penalties'
            AS account,

        btn
            AS cost_item,

        COALESCE(
            SUM(val) FILTER (
                WHERE oper = 'dt'
            ),
            0
        ) AS dt,

        COALESCE(
            SUM(val) FILTER (
                WHERE oper = 'cr'
            ),
            0
        ) AS cr

    FROM sales.sales_long

    WHERE
        field = 'penalty'

    GROUP BY
        date_from,
        rrd_id,
        btn


    UNION ALL


    -- =================================================================
    -- Удержания WB.
    --
    -- В нашем анализе ВЕСЬ WB Deduction считается маркетингом.
    --
    -- При этом сохраняем детализацию:
    --
    -- Продвижение
    -- Отзывы
    -- Услуги WB
    -- Прочее
    -- =================================================================

    SELECT
        date_from,
        rrd_id,

        'WB Deduction'
            AS account,

        CASE

            WHEN STARTS_WITH(
                btn,
                'Списание за отзыв'
            )
            THEN
                'Отзывы'


            WHEN btn ILIKE '%Продв%'
            THEN
                'Продвижение'


            WHEN
                STARTS_WITH(
                    btn,
                    'Оказание услуг'
                )

                OR STARTS_WITH(
                    btn,
                    'Предоставление услуг'
                )

                OR STARTS_WITH(
                    btn,
                    'Витрина Магазина'
                )

            THEN
                'Услуги WB'


            ELSE
                'Прочее'

        END AS cost_item,


        COALESCE(
            SUM(val) FILTER (
                WHERE oper = 'dt'
            ),
            0
        ) AS dt,


        COALESCE(
            SUM(val) FILTER (
                WHERE oper = 'cr'
            ),
            0
        ) AS cr


    FROM sales.sales_long

    WHERE
        field = 'deduction'

        AND btn IS NOT NULL

        AND NOT (

            STARTS_WITH(
                btn,
                'Платеж'
            )

            OR STARTS_WITH(
                btn,
                'Перевод'
            )

        )

    GROUP BY
        date_from,
        rrd_id,
        cost_item


    UNION ALL


    -- =================================================================
    -- Лояльность / кешбэк
    -- =================================================================

    SELECT
        date_from,
        rrd_id,

        'WB Loyality'
            AS account,

        btn
            AS cost_item,

        COALESCE(
            SUM(val) FILTER (
                WHERE oper = 'dt'
            ),
            0
        ) AS dt,

        COALESCE(
            SUM(val) FILTER (
                WHERE oper = 'cr'
            ),
            0
        ) AS cr

    FROM sales.sales_long

    WHERE
        field IN (
            'cashback_commission_change',
            'cashback_amount'
        )

    GROUP BY
        date_from,
        rrd_id,
        btn
),


-- ===================================================================
-- Ставка НДС.
--
-- Одна строка на rrd_id.
-- ===================================================================

rrd_vat AS (

    SELECT
        rrd_id,

        MAX(
            COALESCE(
                vat_rate,
                0
            )
        ) AS vat_rate

    FROM sales.sales_long

    WHERE
        rrd_id IS NOT NULL

    GROUP BY
        rrd_id
)


SELECT

    YEARWEEK(
        t.date_from::DATE
    ) AS yw,

    t.*,

    COALESCE(
        v.vat_rate,
        0
    ) AS vat_rate


FROM raw_costs t


LEFT JOIN rrd_vat v
    ON v.rrd_id = t.rrd_id
;
"""


# =====================================================================
# Основные данные статистики
# =====================================================================

def get_stats_data(
    date_from: str | None = None,
    date_to: str | None = None,
) -> pd.DataFrame:
    """
    Возвращает дневные данные для приложения
    "Статистика и аналитика".

    Внутри одного DuckDB-соединения:

    1. создаётся TEMP TABLE base;
    2. создаётся TEMP TABLE wb_costs;
    3. рассчитываются дневные показатели.

    ПРОДАЖИ:
        base.oper = 'Списание'

    КОЛИЧЕСТВО:
        одна строка списания = одна проданная единица.

    ДЕНЕЖНЫЕ ДАННЫЕ:
        исходно в копейках.

    НДС:
        исключается из:
        - выручки;
        - retail WB;
        - расходов WB.

    МАРКЕТИНГ:
        весь account = 'WB Deduction'.

    Дополнительно отдельно считаются:
        - promotion_costs;
        - review_costs;
        - wb_service_costs;
        - other_marketing_costs.
    """

    # =================================================================
    # Фильтр продаж
    # =================================================================

    sales_conditions = [
        "t.oper = 'Списание'",
    ]

    sales_params: list[str] = []


    if date_from:

        sales_conditions.append(
            """
            t.date_from::DATE
            >= CAST(? AS DATE)
            """
        )

        sales_params.append(
            str(date_from)[:10]
        )


    if date_to:

        sales_conditions.append(
            """
            t.date_from::DATE
            <= CAST(? AS DATE)
            """
        )

        sales_params.append(
            str(date_to)[:10]
        )


    sales_where = (
        "\nAND ".join(
            sales_conditions
        )
    )


    # =================================================================
    # Фильтр расходов
    # =================================================================

    costs_conditions = [
        "1 = 1",
    ]

    costs_params: list[str] = []


    if date_from:

        costs_conditions.append(
            """
            t.date_from::DATE
            >= CAST(? AS DATE)
            """
        )

        costs_params.append(
            str(date_from)[:10]
        )


    if date_to:

        costs_conditions.append(
            """
            t.date_from::DATE
            <= CAST(? AS DATE)
            """
        )

        costs_params.append(
            str(date_to)[:10]
        )


    costs_where = (
        "\nAND ".join(
            costs_conditions
        )
    )


    # =================================================================
    # Одно соединение DuckDB.
    #
    # TEMP TABLE должны создаваться и использоваться
    # в одном и том же соединении.
    # =================================================================

    with get_duckdb_conn_with_opt() as con:

        # -------------------------------------------------------------
        # Создаём base
        # -------------------------------------------------------------

        con.execute(
            BASE_QUERY
        )


        # -------------------------------------------------------------
        # Создаём wb_costs
        # -------------------------------------------------------------

        con.execute(
            WB_COSTS_QUERY
        )


        # -------------------------------------------------------------
        # Основной запрос
        # -------------------------------------------------------------

        df = con.execute(
            f"""
            WITH sales_daily AS (

                SELECT

                    t.date_from::DATE
                        AS date,


                    -- =================================================
                    -- Количество проданных единиц
                    -- =================================================

                    COUNT(*)
                        AS quantity,


                    -- =================================================
                    -- Наша выручка без НДС, руб.
                    --
                    -- cr_rev:
                    -- копейки + НДС
                    -- =================================================

                    SUM(

                        COALESCE(
                            t.cr_rev,
                            0
                        )

                        / 100.0

                        / (

                            1

                            +

                            COALESCE(
                                t.vat_rate,
                                0
                            )
                            / 100.0

                        )

                    ) AS revenue,


                    -- =================================================
                    -- Реализация WB без НДС, руб.
                    -- =================================================

                    SUM(

                        COALESCE(
                            t.retail_amount,
                            0
                        )

                        / 100.0

                        / (

                            1

                            +

                            COALESCE(
                                t.vat_rate,
                                0
                            )
                            / 100.0

                        )

                    ) AS retail_revenue,


                    -- =================================================
                    -- Бухгалтерская себестоимость, руб.
                    -- =================================================

                    SUM(

                        COALESCE(
                            t.adjusted_cogs,
                            0
                        )

                        / 100.0

                    ) AS cogs,


                    -- =================================================
                    -- Управленческая себестоимость, руб.
                    -- =================================================

                    SUM(

                        COALESCE(
                            t.adjusted_cogs_man,
                            0
                        )

                        / 100.0

                    ) AS cogs_man,


                    -- =================================================
                    -- Комиссия WB без НДС, руб.
                    -- =================================================

                    SUM(

                        COALESCE(
                            t.net_comission,
                            0
                        )

                        / 100.0

                    ) AS net_comission


                FROM base t


                WHERE

                    {sales_where}


                GROUP BY

                    t.date_from::DATE
            ),


            costs_daily AS (

                SELECT

                    t.date_from::DATE
                        AS date,


                    -- =================================================
                    -- ВСЕ расходы WB
                    --
                    -- Здесь входят все account:
                    -- Logistic
                    -- Storage
                    -- Acceptance
                    -- Penalties
                    -- Deduction
                    -- Loyality
                    -- Other income / loss
                    -- =================================================

                    SUM(

                        (

                            COALESCE(
                                t.dt,
                                0
                            )

                            -

                            COALESCE(
                                t.cr,
                                0
                            )

                        )

                        / 100.0

                        / (

                            1

                            +

                            COALESCE(
                                t.vat_rate,
                                0
                            )
                            / 100.0

                        )

                    ) AS wb_costs,


                    -- =================================================
                    -- ВЕСЬ МАРКЕТИНГ
                    --
                    -- По твоей методологии:
                    --
                    -- весь WB Deduction = marketing_costs
                    -- =================================================

                    SUM(

                        CASE

                            WHEN
                                t.account
                                = 'WB Deduction'

                            THEN

                                (

                                    COALESCE(
                                        t.dt,
                                        0
                                    )

                                    -

                                    COALESCE(
                                        t.cr,
                                        0
                                    )

                                )

                                / 100.0

                                / (

                                    1

                                    +

                                    COALESCE(
                                        t.vat_rate,
                                        0
                                    )
                                    / 100.0

                                )

                            ELSE 0

                        END

                    ) AS marketing_costs,


                    -- =================================================
                    -- Только продвижение
                    -- =================================================

                    SUM(

                        CASE

                            WHEN
                                t.account
                                = 'WB Deduction'

                                AND

                                t.cost_item
                                = 'Продвижение'

                            THEN

                                (

                                    COALESCE(
                                        t.dt,
                                        0
                                    )

                                    -

                                    COALESCE(
                                        t.cr,
                                        0
                                    )

                                )

                                / 100.0

                                / (

                                    1

                                    +

                                    COALESCE(
                                        t.vat_rate,
                                        0
                                    )
                                    / 100.0

                                )

                            ELSE 0

                        END

                    ) AS promotion_costs,


                    -- =================================================
                    -- Отзывы
                    -- =================================================

                    SUM(

                        CASE

                            WHEN
                                t.account
                                = 'WB Deduction'

                                AND

                                t.cost_item
                                = 'Отзывы'

                            THEN

                                (

                                    COALESCE(
                                        t.dt,
                                        0
                                    )

                                    -

                                    COALESCE(
                                        t.cr,
                                        0
                                    )

                                )

                                / 100.0

                                / (

                                    1

                                    +

                                    COALESCE(
                                        t.vat_rate,
                                        0
                                    )
                                    / 100.0

                                )

                            ELSE 0

                        END

                    ) AS review_costs,


                    -- =================================================
                    -- Услуги WB
                    -- =================================================

                    SUM(

                        CASE

                            WHEN
                                t.account
                                = 'WB Deduction'

                                AND

                                t.cost_item
                                = 'Услуги WB'

                            THEN

                                (

                                    COALESCE(
                                        t.dt,
                                        0
                                    )

                                    -

                                    COALESCE(
                                        t.cr,
                                        0
                                    )

                                )

                                / 100.0

                                / (

                                    1

                                    +

                                    COALESCE(
                                        t.vat_rate,
                                        0
                                    )
                                    / 100.0

                                )

                            ELSE 0

                        END

                    ) AS wb_service_costs,


                    -- =================================================
                    -- Прочий маркетинг
                    -- =================================================

                    SUM(

                        CASE

                            WHEN
                                t.account
                                = 'WB Deduction'

                                AND

                                t.cost_item
                                = 'Прочее'

                            THEN

                                (

                                    COALESCE(
                                        t.dt,
                                        0
                                    )

                                    -

                                    COALESCE(
                                        t.cr,
                                        0
                                    )

                                )

                                / 100.0

                                / (

                                    1

                                    +

                                    COALESCE(
                                        t.vat_rate,
                                        0
                                    )
                                    / 100.0

                                )

                            ELSE 0

                        END

                    ) AS other_marketing_costs,


                    -- =================================================
                    -- Логистика
                    -- =================================================

                    SUM(

                        CASE

                            WHEN
                                t.account
                                = 'WB Logistic'

                            THEN

                                (

                                    COALESCE(
                                        t.dt,
                                        0
                                    )

                                    -

                                    COALESCE(
                                        t.cr,
                                        0
                                    )

                                )

                                / 100.0

                                / (

                                    1

                                    +

                                    COALESCE(
                                        t.vat_rate,
                                        0
                                    )
                                    / 100.0

                                )

                            ELSE 0

                        END

                    ) AS logistics_costs,


                    -- =================================================
                    -- Хранение
                    -- =================================================

                    SUM(

                        CASE

                            WHEN
                                t.account
                                = 'WB Storage'

                            THEN

                                (

                                    COALESCE(
                                        t.dt,
                                        0
                                    )

                                    -

                                    COALESCE(
                                        t.cr,
                                        0
                                    )

                                )

                                / 100.0

                                / (

                                    1

                                    +

                                    COALESCE(
                                        t.vat_rate,
                                        0
                                    )
                                    / 100.0

                                )

                            ELSE 0

                        END

                    ) AS storage_costs,


                    -- =================================================
                    -- Приёмка
                    -- =================================================

                    SUM(

                        CASE

                            WHEN
                                t.account
                                = 'WB Acceptance'

                            THEN

                                (

                                    COALESCE(
                                        t.dt,
                                        0
                                    )

                                    -

                                    COALESCE(
                                        t.cr,
                                        0
                                    )

                                )

                                / 100.0

                                / (

                                    1

                                    +

                                    COALESCE(
                                        t.vat_rate,
                                        0
                                    )
                                    / 100.0

                                )

                            ELSE 0

                        END

                    ) AS acceptance_costs,


                    -- =================================================
                    -- Штрафы
                    -- =================================================

                    SUM(

                        CASE

                            WHEN
                                t.account
                                = 'WB Penalties'

                            THEN

                                (

                                    COALESCE(
                                        t.dt,
                                        0
                                    )

                                    -

                                    COALESCE(
                                        t.cr,
                                        0
                                    )

                                )

                                / 100.0

                                / (

                                    1

                                    +

                                    COALESCE(
                                        t.vat_rate,
                                        0
                                    )
                                    / 100.0

                                )

                            ELSE 0

                        END

                    ) AS penalties_costs


                FROM wb_costs t


                WHERE

                    {costs_where}


                GROUP BY

                    t.date_from::DATE
            )


            SELECT

                s.date,


                YEARWEEK(
                    s.date
                ) AS yw,


                -- =====================================================
                -- Продажи
                -- =====================================================

                s.quantity,

                s.revenue,

                s.retail_revenue,


                -- =====================================================
                -- Себестоимость
                -- =====================================================

                s.cogs,

                s.cogs_man,


                -- =====================================================
                -- Комиссия
                -- =====================================================

                s.net_comission,


                -- =====================================================
                -- Все расходы WB
                -- =====================================================

                COALESCE(
                    c.wb_costs,
                    0
                ) AS wb_costs,


                -- =====================================================
                -- Весь маркетинг
                -- =====================================================

                COALESCE(
                    c.marketing_costs,
                    0
                ) AS marketing_costs,


                -- =====================================================
                -- Детализация маркетинга
                -- =====================================================

                COALESCE(
                    c.promotion_costs,
                    0
                ) AS promotion_costs,


                COALESCE(
                    c.review_costs,
                    0
                ) AS review_costs,


                COALESCE(
                    c.wb_service_costs,
                    0
                ) AS wb_service_costs,


                COALESCE(
                    c.other_marketing_costs,
                    0
                ) AS other_marketing_costs,


                -- =====================================================
                -- Остальные расходы WB
                -- =====================================================

                COALESCE(
                    c.logistics_costs,
                    0
                ) AS logistics_costs,


                COALESCE(
                    c.storage_costs,
                    0
                ) AS storage_costs,


                COALESCE(
                    c.acceptance_costs,
                    0
                ) AS acceptance_costs,


                COALESCE(
                    c.penalties_costs,
                    0
                ) AS penalties_costs,


                -- =====================================================
                -- Средняя наша цена без НДС
                -- =====================================================

                s.revenue

                / NULLIF(
                    s.quantity,
                    0
                ) AS average_price,


                -- =====================================================
                -- Средняя цена WB без НДС
                -- =====================================================

                s.retail_revenue

                / NULLIF(
                    s.quantity,
                    0
                ) AS average_retail_price,


                -- =====================================================
                -- Средняя бухгалтерская себестоимость
                -- =====================================================

                s.cogs

                / NULLIF(
                    s.quantity,
                    0
                ) AS average_cogs,


                -- =====================================================
                -- Средняя управленческая себестоимость
                -- =====================================================

                s.cogs_man

                / NULLIF(
                    s.quantity,
                    0
                ) AS average_cogs_man,


                -- =====================================================
                -- Валовая прибыль бухгалтерская
                -- =====================================================

                (

                    s.revenue

                    -

                    s.cogs

                ) AS gross_profit,


                -- =====================================================
                -- Валовая прибыль управленческая
                -- =====================================================

                (

                    s.revenue

                    -

                    s.cogs_man

                ) AS gross_profit_man,


                -- =====================================================
                -- Маржа после комиссии
                -- бухгалтерская
                -- =====================================================

                (

                    s.revenue

                    -

                    s.cogs

                    +

                    s.net_comission

                ) AS margin,


                -- =====================================================
                -- Маржа после комиссии
                -- управленческая
                -- =====================================================

                (

                    s.revenue

                    -

                    s.cogs_man

                    +

                    s.net_comission

                ) AS margin_man,


                -- =====================================================
                -- Финансовый результат WB
                --
                -- Управленческая себестоимость
                -- + комиссия
                -- - все расходы WB
                -- =====================================================

                (

                    s.revenue

                    -

                    s.cogs_man

                    +

                    s.net_comission

                    -

                    COALESCE(
                        c.wb_costs,
                        0
                    )

                ) AS wb_result


            FROM sales_daily s


            LEFT JOIN costs_daily c
                ON c.date = s.date


            ORDER BY

                s.date
            """,

            [
                *sales_params,
                *costs_params,
            ],

        ).df()


    # =================================================================
    # Пустой результат
    # =================================================================

    if df.empty:
        return df


    # =================================================================
    # Дата
    # =================================================================

    df["date"] = pd.to_datetime(
        df["date"],
        errors="coerce",
    )


    # =================================================================
    # Числовые колонки
    # =================================================================

    numeric_columns = [

        "quantity",

        "revenue",

        "retail_revenue",

        "cogs",

        "cogs_man",

        "net_comission",

        "wb_costs",

        "marketing_costs",

        "promotion_costs",

        "review_costs",

        "wb_service_costs",

        "other_marketing_costs",

        "logistics_costs",

        "storage_costs",

        "acceptance_costs",

        "penalties_costs",

        "average_price",

        "average_retail_price",

        "average_cogs",

        "average_cogs_man",

        "gross_profit",

        "gross_profit_man",

        "margin",

        "margin_man",

        "wb_result",

    ]


    for column in numeric_columns:

        if column in df.columns:

            df[column] = pd.to_numeric(
                df[column],
                errors="coerce",
            )


    return (

        df.sort_values(
            "date"
        )

        .reset_index(
            drop=True
        )

    )


# =====================================================================
# Минимальная дата продаж
# =====================================================================

def get_stats_min_date() -> date:
    """
    Минимальная дата продажи.

    Продажа определяется как:
        oper = 'Списание'
    """

    with get_duckdb_conn_with_opt(
        ro=True
    ) as con:

        result = con.execute(
            """
            SELECT

                MIN(
                    date_from::DATE
                )

            FROM inventories.inv_gl_final

            WHERE

                oper = 'Списание'
            """
        ).fetchone()


    if (
        result
        and result[0]
    ):
        return result[0]


    return date.today()