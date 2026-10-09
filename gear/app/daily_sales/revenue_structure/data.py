# # gear/app/daily_sales/revenue_structure/data.py

# from __future__ import annotations

# from datetime import date
# from typing import Any

# from conns import get_duckdb_conn_with_opt
# from ...data.base import DashboardData


# # =========================================================
# # Настройки измерений
# # =========================================================

# DIMENSION_CONFIG = {
#     "brand": {
#         "sql": """
#             COALESCE(
#                 NULLIF(TRIM(p.brand), ''),
#                 'Не указан'
#             )
#         """,
#         "label": "Бренд",
#     },

#     "category": {
#         "sql": """
#             COALESCE(
#                 NULLIF(TRIM(p.subject_name), ''),
#                 'Не указана'
#             )
#         """,
#         "label": "Категория",
#     },

#     "gender": {
#         "sql": """
#             COALESCE(
#                 NULLIF(TRIM(p.gender), ''),
#                 'Не указан'
#             )
#         """,
#         "label": "Пол",
#     },
# }


# # =========================================================
# # Вспомогательные функции
# # =========================================================

# def normalize_date(value) -> date:
#     """
#     Приводит дату к datetime.date.

#     Работает с:
#         date
#         datetime
#         '2026-07-01'
#         '2026-07-01T00:00:00.000Z'
#     """

#     if isinstance(value, date):
#         return value

#     return date.fromisoformat(
#         str(value)[:10]
#     )


# def _normalize_filter(
#     values,
# ) -> list:
#     """
#     None -> []
#     строка -> [строка]
#     list/tuple/set -> list
#     """

#     if values is None:
#         return []

#     if isinstance(values, str):
#         value = values.strip()

#         return (
#             [value]
#             if value
#             else []
#         )

#     if isinstance(
#         values,
#         (
#             list,
#             tuple,
#             set,
#         ),
#     ):
#         return [
#             value
#             for value in values
#             if value is not None
#             and str(value).strip() != ""
#         ]

#     return [values]


# def _placeholders(
#     values: list,
# ) -> str:

#     return ", ".join(
#         "?"
#         for _ in values
#     )


# def _build_filters(
#     cat=None,
#     brand=None,
#     gender=None,
# ) -> tuple[str, list[Any]]:
#     """
#     Фильтры применяются к inventories.wb_product.

#     ВАЖНО:
#     category из WbFilters у тебя, судя по основной
#     логике DashboardData, содержит subject_id,
#     а не subject_name.

#     Поэтому фильтр категорий:
#         p.subject_id IN (...)

#     Связь:
#         inv_gl_final.usk = wb_product.card_id
#     """

#     conditions = []
#     params: list[Any] = []

#     categories = _normalize_filter(
#         cat
#     )

#     brands = _normalize_filter(
#         brand
#     )

#     genders = _normalize_filter(
#         gender
#     )

#     # -----------------------------------------------------
#     # Категории
#     # -----------------------------------------------------

#     if categories:

#         category_ids = [
#             int(value)
#             for value in categories
#         ]

#         conditions.append(
#             "p.subject_id IN "
#             f"({_placeholders(category_ids)})"
#         )

#         params.extend(
#             category_ids
#         )

#     # -----------------------------------------------------
#     # Бренды
#     # -----------------------------------------------------

#     if brands:

#         brand_values = [
#             str(value).upper()
#             for value in brands
#         ]

#         conditions.append(
#             "UPPER(p.brand) IN "
#             f"({_placeholders(brand_values)})"
#         )

#         params.extend(
#             brand_values
#         )

#     # -----------------------------------------------------
#     # Пол
#     # -----------------------------------------------------

#     if genders:

#         gender_values = [
#             str(value)
#             for value in genders
#         ]

#         conditions.append(
#             """
#             COALESCE(
#                 p.gender,
#                 'Не указан'
#             ) IN (
#             """
#             + _placeholders(
#                 gender_values
#             )
#             + ")"
#         )

#         params.extend(
#             gender_values
#         )

#     if not conditions:
#         return "", []

#     return (
#         "\nAND "
#         + "\nAND ".join(
#             conditions
#         ),
#         params,
#     )


# # =========================================================
# # Основной запрос
# # =========================================================

# def get_revenue_structure(
#     start_date,
#     end_date,
#     dimension: str,
#     cat=None,
#     brand=None,
#     gender=None,
# ) -> list[dict]:
#     """
#     Анализ выручки и валовой маржинальности.

#     Источник:
#         inventories.inv_gl_final

#     Связь:
#         inv_gl_final.usk
#             =
#         inventories.wb_product.card_id


#     Денежные поля inv_gl_final хранятся в копейках:

#         cr_rev
#             выручка с НДС

#         cr
#             бухгалтерская себестоимость без НДС

#         cr_man
#             управленческая себестоимость без НДС


#     Выручка без НДС:

#         cr_rev / (100 + vat_rate) * 100


#     Валовая прибыль бух:

#         revenue_vatless - cogs_book


#     Валовая прибыль упр:

#         revenue_vatless - cogs_man


#     Маржинальность:

#         gross_profit / revenue_vatless * 100
#     """

#     start_date = normalize_date(
#         start_date
#     )

#     end_date = normalize_date(
#         end_date
#     )

#     config = DIMENSION_CONFIG.get(
#         dimension
#     )

#     if not config:
#         raise ValueError(
#             "Unsupported dimension: "
#             f"{dimension}"
#         )

#     dimension_sql = config[
#         "sql"
#     ]

#     filter_sql, filter_params = (
#         _build_filters(
#             cat=cat,
#             brand=brand,
#             gender=gender,
#         )
#     )

#     params = [
#         start_date,
#         end_date,
#         *filter_params,
#     ]

#     sql = f"""
#         WITH prepared AS (
#             SELECT

#                 t.usk,

#                 {dimension_sql}
#                     AS entity_name,

#                 COALESCE(
#                     t.cr_rev,
#                     0
#                 ) AS revenue_vat,

#                 CASE
#                     WHEN COALESCE(
#                         t.vat_rate,
#                         0
#                     ) = 0
#                     THEN COALESCE(
#                         t.cr_rev,
#                         0
#                     )

#                     ELSE
#                         COALESCE(
#                             t.cr_rev,
#                             0
#                         )
#                         /
#                         (
#                             100
#                             +
#                             t.vat_rate
#                         )
#                         * 100
#                 END AS revenue_vatless,

#                 COALESCE(
#                     t.cr,
#                     0
#                 ) AS cogs_book,

#                 COALESCE(
#                     t.cr_man,
#                     0
#                 ) AS cogs_man,

#                 CASE
#                     WHEN COALESCE(
#                         t.cr_rev,
#                         0
#                     ) > 0
#                     THEN 1

#                     WHEN COALESCE(
#                         t.cr_rev,
#                         0
#                     ) < 0
#                     THEN -1

#                     ELSE 0
#                 END AS net_qty,

#                 CASE
#                     WHEN COALESCE(
#                         t.cr,
#                         0
#                     ) = 0
#                     THEN 1

#                     ELSE 0
#                 END AS no_book_cost,

#                 CASE
#                     WHEN COALESCE(
#                         t.cr_man,
#                         0
#                     ) = 0
#                     THEN 1

#                     ELSE 0
#                 END AS no_man_cost

#             FROM base t

#             LEFT JOIN inventories.wb_product p
#                 ON p.card_id = t.usk

#             WHERE
#                 t.cr_rev <> 0

#                 AND t.date_from::DATE
#                     BETWEEN ?::DATE
#                     AND ?::DATE

#                 {filter_sql}
#         ),

#         aggregated AS (
#             SELECT

#                 entity_name,

#                 COUNT(
#                     DISTINCT usk
#                 ) AS products_count,

#                 COUNT(*) AS rows_count,

#                 SUM(
#                     net_qty
#                 ) AS net_qty,

#                 SUM(
#                     revenue_vat
#                 ) AS revenue_vat,

#                 SUM(
#                     revenue_vatless
#                 ) AS revenue_vatless,

#                 SUM(
#                     cogs_book
#                 ) AS cogs_book,

#                 SUM(
#                     cogs_man
#                 ) AS cogs_man,

#                 SUM(
#                     no_book_cost
#                 ) AS no_book_cost,

#                 SUM(
#                     no_man_cost
#                 ) AS no_man_cost

#             FROM prepared

#             GROUP BY
#                 entity_name
#         )

#         SELECT

#             entity_name,

#             products_count,

#             rows_count,

#             net_qty,

#             revenue_vat,

#             revenue_vatless,

#             cogs_book,

#             cogs_man,

#             revenue_vatless
#                 - cogs_book
#                 AS gross_profit_book,

#             revenue_vatless
#                 - cogs_man
#                 AS gross_profit_man,

#             CASE
#                 WHEN revenue_vatless = 0
#                 THEN NULL

#                 ELSE
#                     (
#                         revenue_vatless
#                         - cogs_book
#                     )
#                     /
#                     revenue_vatless
#                     * 100
#             END AS margin_book_pct,

#             CASE
#                 WHEN revenue_vatless = 0
#                 THEN NULL

#                 ELSE
#                     (
#                         revenue_vatless
#                         - cogs_man
#                     )
#                     /
#                     revenue_vatless
#                     * 100
#             END AS margin_man_pct,

#             CASE
#                 WHEN revenue_vatless = 0
#                 THEN NULL

#                 ELSE
#                     cogs_book
#                     /
#                     revenue_vatless
#                     * 100
#             END AS cogs_book_share,

#             CASE
#                 WHEN revenue_vatless = 0
#                 THEN NULL

#                 ELSE
#                     cogs_man
#                     /
#                     revenue_vatless
#                     * 100
#             END AS cogs_man_share,

#             no_book_cost,

#             no_man_cost

#         FROM aggregated

#         ORDER BY
#             revenue_vatless DESC
#     """
    
#     with DashboardData() as d:
#         rows = d.con.execute(
#             sql,
#             params,
#         ).fetchall()

#     # =====================================================
#     # Общие суммы
#     # Используем для расчёта долей
#     # =====================================================

#     total_revenue_vatless = sum(
#         float(
#             row[5]
#             or 0
#         )
#         for row in rows
#     )

#     total_gross_profit_man = sum(
#         float(
#             row[9]
#             or 0
#         )
#         for row in rows
#     )

#     result = []

#     for row in rows:

#         (
#             entity_name,
#             products_count,
#             rows_count,
#             net_qty,
#             revenue_vat,
#             revenue_vatless,
#             cogs_book,
#             cogs_man,
#             gross_profit_book,
#             gross_profit_man,
#             margin_book_pct,
#             margin_man_pct,
#             cogs_book_share,
#             cogs_man_share,
#             no_book_cost,
#             no_man_cost,
#         ) = row

#         revenue_vat = float(
#             revenue_vat or 0
#         )

#         revenue_vatless = float(
#             revenue_vatless or 0
#         )

#         cogs_book = float(
#             cogs_book or 0
#         )

#         cogs_man = float(
#             cogs_man or 0
#         )

#         gross_profit_book = float(
#             gross_profit_book or 0
#         )

#         gross_profit_man = float(
#             gross_profit_man or 0
#         )

#         net_qty = int(
#             net_qty or 0
#         )

#         # -------------------------------------------------
#         # НДС
#         # -------------------------------------------------

#         vat_amount = (
#             revenue_vat
#             - revenue_vatless
#         )

#         # -------------------------------------------------
#         # Доля выручки
#         # -------------------------------------------------

#         revenue_share_pct = (
#             revenue_vatless
#             /
#             total_revenue_vatless
#             * 100
#             if total_revenue_vatless
#             else 0
#         )

#         # -------------------------------------------------
#         # Доля валовой прибыли
#         # -------------------------------------------------

#         profit_share_pct = (
#             gross_profit_man
#             /
#             total_gross_profit_man
#             * 100
#             if total_gross_profit_man
#             else 0
#         )

#         # -------------------------------------------------
#         # Средняя выручка за единицу
#         # -------------------------------------------------

#         average_revenue = (
#             revenue_vatless
#             /
#             net_qty
#             if net_qty > 0
#             else 0
#         )

#         result.append(
#             {
#                 "name": str(
#                     entity_name
#                     or "Не указано"
#                 ),

#                 "products_count": int(
#                     products_count
#                     or 0
#                 ),

#                 "rows_count": int(
#                     rows_count
#                     or 0
#                 ),

#                 "net_qty": net_qty,

#                 # -----------------------------------------
#                 # Выручка
#                 # -----------------------------------------

#                 "revenue_vat": round(
#                     revenue_vat
#                     / 100,
#                     2,
#                 ),

#                 "vat_amount": round(
#                     vat_amount
#                     / 100,
#                     2,
#                 ),

#                 "revenue_vatless": round(
#                     revenue_vatless
#                     / 100,
#                     2,
#                 ),

#                 "revenue_share_pct": round(
#                     revenue_share_pct,
#                     2,
#                 ),

#                 "average_revenue": round(
#                     average_revenue
#                     / 100,
#                     2,
#                 ),

#                 # -----------------------------------------
#                 # Бухгалтерская себестоимость
#                 # -----------------------------------------

#                 "cogs_book": round(
#                     cogs_book
#                     / 100,
#                     2,
#                 ),

#                 "gross_profit_book": round(
#                     gross_profit_book
#                     / 100,
#                     2,
#                 ),

#                 "margin_book_pct": round(
#                     float(
#                         margin_book_pct
#                         or 0
#                     ),
#                     2,
#                 ),

#                 "cogs_book_share": round(
#                     float(
#                         cogs_book_share
#                         or 0
#                     ),
#                     2,
#                 ),

#                 # -----------------------------------------
#                 # Управленческая себестоимость
#                 # -----------------------------------------

#                 "cogs_man": round(
#                     cogs_man
#                     / 100,
#                     2,
#                 ),

#                 "gross_profit_man": round(
#                     gross_profit_man
#                     / 100,
#                     2,
#                 ),

#                 "margin_man_pct": round(
#                     float(
#                         margin_man_pct
#                         or 0
#                     ),
#                     2,
#                 ),

#                 "cogs_man_share": round(
#                     float(
#                         cogs_man_share
#                         or 0
#                     ),
#                     2,
#                 ),

#                 # -----------------------------------------
#                 # Структура прибыли
#                 # -----------------------------------------

#                 "profit_share_pct": round(
#                     profit_share_pct,
#                     2,
#                 ),

#                 # -----------------------------------------
#                 # Контроль качества данных
#                 # -----------------------------------------

#                 "no_book_cost": int(
#                     no_book_cost
#                     or 0
#                 ),

#                 "no_man_cost": int(
#                     no_man_cost
#                     or 0
#                 ),
#             }
#         )

#     return result



# # gear/app/daily_sales/revenue_structure/data.py

# from __future__ import annotations

# from datetime import date
# from typing import Any

# from conns import get_duckdb_conn_with_opt
# from ...data.base import DashboardData


# # =========================================================
# # Настройки измерений
# # =========================================================

# DIMENSION_CONFIG = {
#     "brand": {
#         "sql": """
#             COALESCE(
#                 NULLIF(TRIM(p.brand), ''),
#                 'Не указан'
#             )
#         """,
#         "label": "Бренд",
#     },

#     "category": {
#         "sql": """
#             COALESCE(
#                 NULLIF(TRIM(p.subject_name), ''),
#                 'Не указана'
#             )
#         """,
#         "label": "Категория",
#     },

#     "gender": {
#         "sql": """
#             COALESCE(
#                 NULLIF(TRIM(p.gender), ''),
#                 'Не указан'
#             )
#         """,
#         "label": "Пол",
#     },
# }


# # =========================================================
# # Вспомогательные функции
# # =========================================================

# def normalize_date(value) -> date:
#     """
#     Приводит дату к datetime.date.

#     Работает с:
#         date
#         datetime
#         '2026-07-01'
#         '2026-07-01T00:00:00.000Z'
#     """

#     if isinstance(value, date):
#         return value

#     return date.fromisoformat(
#         str(value)[:10]
#     )


# def _normalize_filter(
#     values,
# ) -> list:
#     """
#     None -> []
#     строка -> [строка]
#     list/tuple/set -> list
#     """

#     if values is None:
#         return []

#     if isinstance(values, str):
#         value = values.strip()

#         return (
#             [value]
#             if value
#             else []
#         )

#     if isinstance(
#         values,
#         (
#             list,
#             tuple,
#             set,
#         ),
#     ):
#         return [
#             value
#             for value in values
#             if value is not None
#             and str(value).strip() != ""
#         ]

#     return [values]


# def _placeholders(
#     values: list,
# ) -> str:

#     return ", ".join(
#         "?"
#         for _ in values
#     )


# def _build_filters(
#     cat=None,
#     brand=None,
#     gender=None,
# ) -> tuple[str, list[Any]]:
#     """
#     Фильтры применяются к inventories.wb_product.

#     ВАЖНО:
#     category из WbFilters у тебя, судя по основной
#     логике DashboardData, содержит subject_id,
#     а не subject_name.

#     Поэтому фильтр категорий:
#         p.subject_id IN (...)

#     Связь:
#         inv_gl_final.usk = wb_product.card_id
#     """

#     conditions = []
#     params: list[Any] = []

#     categories = _normalize_filter(
#         cat
#     )

#     brands = _normalize_filter(
#         brand
#     )

#     genders = _normalize_filter(
#         gender
#     )

#     # -----------------------------------------------------
#     # Категории
#     # -----------------------------------------------------

#     if categories:

#         category_ids = [
#             int(value)
#             for value in categories
#         ]

#         conditions.append(
#             "p.subject_id IN "
#             f"({_placeholders(category_ids)})"
#         )

#         params.extend(
#             category_ids
#         )

#     # -----------------------------------------------------
#     # Бренды
#     # -----------------------------------------------------

#     if brands:

#         brand_values = [
#             str(value).upper()
#             for value in brands
#         ]

#         conditions.append(
#             "UPPER(p.brand) IN "
#             f"({_placeholders(brand_values)})"
#         )

#         params.extend(
#             brand_values
#         )

#     # -----------------------------------------------------
#     # Пол
#     # -----------------------------------------------------

#     if genders:

#         gender_values = [
#             str(value)
#             for value in genders
#         ]

#         conditions.append(
#             """
#             COALESCE(
#                 p.gender,
#                 'Не указан'
#             ) IN (
#             """
#             + _placeholders(
#                 gender_values
#             )
#             + ")"
#         )

#         params.extend(
#             gender_values
#         )

#     if not conditions:
#         return "", []

#     return (
#         "\nAND "
#         + "\nAND ".join(
#             conditions
#         ),
#         params,
#     )


# # =========================================================
# # Основной запрос
# # =========================================================

# def get_revenue_structure(
#     start_date,
#     end_date,
#     dimension: str,
#     cat=None,
#     brand=None,
#     gender=None,
# ) -> list[dict]:
#     """
#     Анализ выручки и маржинальности с учётом комиссии WB.

#     Логика комиссии полностью совпадает с основной таблицей продаж:

#         1. Комиссия агрегируется в sales.sales_long по rrd_id.
#         2. Связывается с продажей через:
#                commissions.rrd_id = base.rrd_id
#         3. net_comission считается без НДС.
#         4. Маржинальная прибыль считается как:

#                revenue_vatless
#                - cogs
#                + net_comission

#            Здесь используется именно "+ net_comission", потому что
#            знак комиссии уже формируется в CTE commissions так же,
#            как в DAILY_SALES_AGG.

#     Денежные поля до финального формирования результата находятся
#     в копейках и переводятся в рубли только при создании result.
#     """

#     start_date = normalize_date(
#         start_date
#     )

#     end_date = normalize_date(
#         end_date
#     )

#     config = DIMENSION_CONFIG.get(
#         dimension
#     )

#     if not config:
#         raise ValueError(
#             "Unsupported dimension: "
#             f"{dimension}"
#         )

#     dimension_sql = config[
#         "sql"
#     ]

#     filter_sql, filter_params = (
#         _build_filters(
#             cat=cat,
#             brand=brand,
#             gender=gender,
#         )
#     )

#     params = [
#         start_date,
#         end_date,
#         *filter_params,
#     ]

#     sql = f"""
#         WITH commissions AS (
#             SELECT
#                 rrd_id,

#                 COALESCE(
#                     SUM(
#                         val
#                         / (100 + vat_rate)
#                         * 100
#                     ) FILTER (
#                         WHERE field = 'comission'
#                           AND oper = 'dt'
#                     ),
#                     0
#                 )
#                 -
#                 COALESCE(
#                     SUM(
#                         val
#                         / (100 + vat_rate)
#                         * 100
#                     ) FILTER (
#                         WHERE field = 'comission'
#                           AND oper = 'cr'
#                     ),
#                     0
#                 ) AS net_comission

#             FROM sales.sales_long

#             GROUP BY
#                 rrd_id
#         ),

#         prepared AS (
#             SELECT

#                 t.usk,

#                 {dimension_sql}
#                     AS entity_name,

#                 COALESCE(
#                     t.cr_rev,
#                     0
#                 ) AS revenue_vat,

#                 CASE
#                     WHEN COALESCE(
#                         t.vat_rate,
#                         0
#                     ) = 0
#                     THEN COALESCE(
#                         t.cr_rev,
#                         0
#                     )

#                     ELSE
#                         COALESCE(
#                             t.cr_rev,
#                             0
#                         )
#                         /
#                         (
#                             100
#                             +
#                             t.vat_rate
#                         )
#                         * 100
#                 END AS revenue_vatless,

#                 COALESCE(
#                     t.cr,
#                     0
#                 ) AS cogs_book,

#                 COALESCE(
#                     t.cr_man,
#                     0
#                 ) AS cogs_man,

#                 COALESCE(
#                     c.net_comission,
#                     0
#                 ) AS net_comission,

#                 CASE
#                     WHEN COALESCE(
#                         t.cr_rev,
#                         0
#                     ) > 0
#                     THEN 1

#                     WHEN COALESCE(
#                         t.cr_rev,
#                         0
#                     ) < 0
#                     THEN -1

#                     ELSE 0
#                 END AS net_qty,

#                 CASE
#                     WHEN COALESCE(
#                         t.cr,
#                         0
#                     ) = 0
#                     THEN 1

#                     ELSE 0
#                 END AS no_book_cost,

#                 CASE
#                     WHEN COALESCE(
#                         t.cr_man,
#                         0
#                     ) = 0
#                     THEN 1

#                     ELSE 0
#                 END AS no_man_cost

#             FROM base t

#             LEFT JOIN inventories.wb_product p
#                 ON p.card_id = t.usk

#             LEFT JOIN commissions c
#                 ON c.rrd_id = t.rrd_id

#             WHERE
#                 t.cr_rev <> 0

#                 AND t.date_from::DATE
#                     BETWEEN ?::DATE
#                     AND ?::DATE

#                 {filter_sql}
#         ),

#         aggregated AS (
#             SELECT

#                 entity_name,

#                 COUNT(
#                     DISTINCT usk
#                 ) AS products_count,

#                 COUNT(*) AS rows_count,

#                 SUM(
#                     net_qty
#                 ) AS net_qty,

#                 SUM(
#                     revenue_vat
#                 ) AS revenue_vat,

#                 SUM(
#                     revenue_vatless
#                 ) AS revenue_vatless,

#                 SUM(
#                     cogs_book
#                 ) AS cogs_book,

#                 SUM(
#                     cogs_man
#                 ) AS cogs_man,

#                 SUM(
#                     net_comission
#                 ) AS net_comission,

#                 SUM(
#                     no_book_cost
#                 ) AS no_book_cost,

#                 SUM(
#                     no_man_cost
#                 ) AS no_man_cost

#             FROM prepared

#             GROUP BY
#                 entity_name
#         )

#         SELECT

#             entity_name,

#             products_count,

#             rows_count,

#             net_qty,

#             revenue_vat,

#             revenue_vatless,

#             cogs_book,

#             cogs_man,

#             net_comission,

#             revenue_vatless
#                 - cogs_book
#                 + net_comission
#                 AS gross_profit_book,

#             revenue_vatless
#                 - cogs_man
#                 + net_comission
#                 AS gross_profit_man,

#             CASE
#                 WHEN revenue_vatless = 0
#                 THEN NULL

#                 ELSE
#                     (
#                         revenue_vatless
#                         - cogs_book
#                         + net_comission
#                     )
#                     /
#                     revenue_vatless
#                     * 100
#             END AS margin_book_pct,

#             CASE
#                 WHEN revenue_vatless = 0
#                 THEN NULL

#                 ELSE
#                     (
#                         revenue_vatless
#                         - cogs_man
#                         + net_comission
#                     )
#                     /
#                     revenue_vatless
#                     * 100
#             END AS margin_man_pct,

#             CASE
#                 WHEN revenue_vatless = 0
#                 THEN NULL

#                 ELSE
#                     cogs_book
#                     /
#                     revenue_vatless
#                     * 100
#             END AS cogs_book_share,

#             CASE
#                 WHEN revenue_vatless = 0
#                 THEN NULL

#                 ELSE
#                     cogs_man
#                     /
#                     revenue_vatless
#                     * 100
#             END AS cogs_man_share,

#             CASE
#                 WHEN revenue_vatless = 0
#                 THEN NULL

#                 ELSE
#                     -net_comission
#                     /
#                     revenue_vatless
#                     * 100
#             END AS commission_pct,

#             no_book_cost,

#             no_man_cost

#         FROM aggregated

#         ORDER BY
#             revenue_vatless DESC
#     """

#     with DashboardData() as d:
#         rows = d.con.execute(
#             sql,
#             params,
#         ).fetchall()

#     # =====================================================
#     # Общие суммы
#     # Используем для расчёта долей
#     # =====================================================

#     total_revenue_vatless = sum(
#         float(
#             row[5]
#             or 0
#         )
#         for row in rows
#     )

#     total_gross_profit_man = sum(
#         float(
#             row[10]
#             or 0
#         )
#         for row in rows
#     )

#     result = []

#     for row in rows:

#         (
#             entity_name,
#             products_count,
#             rows_count,
#             net_qty,
#             revenue_vat,
#             revenue_vatless,
#             cogs_book,
#             cogs_man,
#             net_comission,
#             gross_profit_book,
#             gross_profit_man,
#             margin_book_pct,
#             margin_man_pct,
#             cogs_book_share,
#             cogs_man_share,
#             commission_pct,
#             no_book_cost,
#             no_man_cost,
#         ) = row

#         revenue_vat = float(
#             revenue_vat or 0
#         )

#         revenue_vatless = float(
#             revenue_vatless or 0
#         )

#         cogs_book = float(
#             cogs_book or 0
#         )

#         cogs_man = float(
#             cogs_man or 0
#         )

#         net_comission = float(
#             net_comission or 0
#         )

#         gross_profit_book = float(
#             gross_profit_book or 0
#         )

#         gross_profit_man = float(
#             gross_profit_man or 0
#         )

#         net_qty = int(
#             net_qty or 0
#         )

#         # -------------------------------------------------
#         # НДС
#         # -------------------------------------------------

#         vat_amount = (
#             revenue_vat
#             - revenue_vatless
#         )

#         # -------------------------------------------------
#         # Доля выручки
#         # -------------------------------------------------

#         revenue_share_pct = (
#             revenue_vatless
#             /
#             total_revenue_vatless
#             * 100
#             if total_revenue_vatless
#             else 0
#         )

#         # -------------------------------------------------
#         # Доля прибыли после комиссии
#         # -------------------------------------------------

#         profit_share_pct = (
#             gross_profit_man
#             /
#             total_gross_profit_man
#             * 100
#             if total_gross_profit_man
#             else 0
#         )

#         # -------------------------------------------------
#         # Средняя выручка за единицу
#         # -------------------------------------------------

#         average_revenue = (
#             revenue_vatless
#             /
#             net_qty
#             if net_qty > 0
#             else 0
#         )

#         result.append(
#             {
#                 "name": str(
#                     entity_name
#                     or "Не указано"
#                 ),

#                 "products_count": int(
#                     products_count
#                     or 0
#                 ),

#                 "rows_count": int(
#                     rows_count
#                     or 0
#                 ),

#                 "net_qty": net_qty,

#                 # -----------------------------------------
#                 # Выручка
#                 # -----------------------------------------

#                 "revenue_vat": round(
#                     revenue_vat
#                     / 100,
#                     2,
#                 ),

#                 "vat_amount": round(
#                     vat_amount
#                     / 100,
#                     2,
#                 ),

#                 "revenue_vatless": round(
#                     revenue_vatless
#                     / 100,
#                     2,
#                 ),

#                 "revenue_share_pct": round(
#                     revenue_share_pct,
#                     2,
#                 ),

#                 "average_revenue": round(
#                     average_revenue
#                     / 100,
#                     2,
#                 ),

#                 # -----------------------------------------
#                 # Комиссия WB
#                 # -----------------------------------------

#                 "net_comission": round(
#                     net_comission
#                     / 100,
#                     2,
#                 ),

#                 "commission_pct": round(
#                     float(
#                         commission_pct
#                         or 0
#                     ),
#                     2,
#                 ),

#                 # -----------------------------------------
#                 # Бухгалтерская себестоимость
#                 # Прибыль уже после комиссии WB
#                 # -----------------------------------------

#                 "cogs_book": round(
#                     cogs_book
#                     / 100,
#                     2,
#                 ),

#                 "gross_profit_book": round(
#                     gross_profit_book
#                     / 100,
#                     2,
#                 ),

#                 "margin_book_pct": round(
#                     float(
#                         margin_book_pct
#                         or 0
#                     ),
#                     2,
#                 ),

#                 "cogs_book_share": round(
#                     float(
#                         cogs_book_share
#                         or 0
#                     ),
#                     2,
#                 ),

#                 # -----------------------------------------
#                 # Управленческая себестоимость
#                 # Прибыль уже после комиссии WB
#                 # -----------------------------------------

#                 "cogs_man": round(
#                     cogs_man
#                     / 100,
#                     2,
#                 ),

#                 "gross_profit_man": round(
#                     gross_profit_man
#                     / 100,
#                     2,
#                 ),

#                 "margin_man_pct": round(
#                     float(
#                         margin_man_pct
#                         or 0
#                     ),
#                     2,
#                 ),

#                 "cogs_man_share": round(
#                     float(
#                         cogs_man_share
#                         or 0
#                     ),
#                     2,
#                 ),

#                 # -----------------------------------------
#                 # Структура прибыли
#                 # -----------------------------------------

#                 "profit_share_pct": round(
#                     profit_share_pct,
#                     2,
#                 ),

#                 # -----------------------------------------
#                 # Контроль качества данных
#                 # -----------------------------------------

#                 "no_book_cost": int(
#                     no_book_cost
#                     or 0
#                 ),

#                 "no_man_cost": int(
#                     no_man_cost
#                     or 0
#                 ),
#             }
#         )

#     return result




# gear/app/daily_sales/revenue_structure/data.py

from __future__ import annotations

from datetime import date
from typing import Any

from ...data.base import DashboardData


# =========================================================
# Настройки измерений
# =========================================================

DIMENSION_CONFIG = {
    "brand": {
        "sql": """
            COALESCE(
                NULLIF(
                    TRIM(t.brand),
                    ''
                ),
                'Не указан'
            )
        """,
        "label": "Бренд",
    },

    "category": {
        "sql": """
            COALESCE(
                NULLIF(
                    TRIM(t.subject_name),
                    ''
                ),
                'Не указана'
            )
        """,
        "label": "Категория",
    },

    "gender": {
        "sql": """
            COALESCE(
                NULLIF(
                    TRIM(t.gender),
                    ''
                ),
                'Не указан'
            )
        """,
        "label": "Пол",
    },
}


# =========================================================
# Вспомогательные функции
# =========================================================

def normalize_date(
    value,
) -> date:
    """
    Приводит значение к datetime.date.

    Поддерживает:

    - date;
    - datetime;
    - '2026-07-01';
    - '2026-07-01T00:00:00.000Z'.
    """

    if isinstance(
        value,
        date,
    ):
        return value

    return date.fromisoformat(
        str(value)[:10]
    )


def _normalize_filter(
    values,
) -> list:
    """
    Приводит фильтр к списку.

    None -> []
    строка -> [строка]
    list/tuple/set -> list
    """

    if values is None:
        return []

    if isinstance(
        values,
        str,
    ):

        value = values.strip()

        return (
            [value]
            if value
            else []
        )

    if isinstance(
        values,
        (
            list,
            tuple,
            set,
        ),
    ):
        return [
            value
            for value in values
            if value is not None
            and str(value).strip() != ""
        ]

    return [values]


def _placeholders(
    values: list,
) -> str:
    """
    Создаёт SQL-плейсхолдеры:

    ?, ?, ?
    """

    return ", ".join(
        "?"
        for _ in values
    )


def _build_filters(
    cat=None,
    brand=None,
    gender=None,
) -> tuple[str, list[Any]]:
    """
    Формирует фильтры для временной таблицы base.

    ВАЖНО:

    После изменения BASE_QUERY в base уже находятся:

    - brand;
    - subject_id;
    - subject_name;
    - gender.

    Поэтому повторно подключать inventories.wb_product
    здесь больше не нужно.
    """

    conditions: list[str] = []
    params: list[Any] = []

    categories = _normalize_filter(
        cat
    )

    brands = _normalize_filter(
        brand
    )

    genders = _normalize_filter(
        gender
    )

    # -----------------------------------------------------
    # Категории
    # -----------------------------------------------------

    if categories:

        category_ids = [
            int(value)
            for value in categories
        ]

        conditions.append(
            "t.subject_id IN "
            f"({_placeholders(category_ids)})"
        )

        params.extend(
            category_ids
        )

    # -----------------------------------------------------
    # Бренды
    # -----------------------------------------------------

    if brands:

        brand_values = [
            str(value).upper()
            for value in brands
        ]

        conditions.append(
            "UPPER(t.brand) IN "
            f"({_placeholders(brand_values)})"
        )

        params.extend(
            brand_values
        )

    # -----------------------------------------------------
    # Пол
    # -----------------------------------------------------

    if genders:

        gender_values = [
            str(value)
            for value in genders
        ]

        conditions.append(
            """
            COALESCE(
                t.gender,
                'Не указан'
            ) IN (
            """
            + _placeholders(
                gender_values
            )
            + ")"
        )

        params.extend(
            gender_values
        )

    if not conditions:
        return "", []

    return (
        "\nAND "
        + "\nAND ".join(
            conditions
        ),
        params,
    )


# =========================================================
# Основной запрос
# =========================================================

def get_revenue_structure(
    start_date,
    end_date,
    dimension: str,
    cat=None,
    brand=None,
    gender=None,
) -> list[dict]:
    """
    Анализ выручки и маржинальности.

    Все основные данные берутся из временной таблицы base.

    В base уже находятся:

    - cr_rev;
    - cr;
    - cr_man;
    - adjusted_cogs;
    - adjusted_cogs_man;
    - retail_amount;
    - net_comission;
    - brand;
    - subject_id;
    - subject_name;
    - gender.

    Комиссия WB уже рассчитана в BASE_QUERY
    и связана с продажей по rrd_id.

    Формула бухгалтерской прибыли:

        revenue_vatless
        - cogs_book
        + net_comission

    Формула управленческой прибыли:

        revenue_vatless
        - cogs_man
        + net_comission

    Так как net_comission уже имеет правильный знак,
    здесь используется именно сложение.
    """

    start_date = normalize_date(
        start_date
    )

    end_date = normalize_date(
        end_date
    )

    config = DIMENSION_CONFIG.get(
        dimension
    )

    if not config:
        raise ValueError(
            "Unsupported dimension: "
            f"{dimension}"
        )

    dimension_sql = config[
        "sql"
    ]

    filter_sql, filter_params = (
        _build_filters(
            cat=cat,
            brand=brand,
            gender=gender,
        )
    )

    params = [
        start_date,
        end_date,
        *filter_params,
    ]

    sql = f"""
        WITH prepared AS (
            SELECT

                t.usk,

                {dimension_sql}
                    AS entity_name,



                COALESCE(
                    t.cr_rev,
                    0
                ) AS revenue_vat,

      

                CASE

                    WHEN COALESCE(
                        t.vat_rate,
                        0
                    ) = 0

                    THEN COALESCE(
                        t.cr_rev,
                        0
                    )

                    ELSE
                        COALESCE(
                            t.cr_rev,
                            0
                        )
                        /
                        (
                            100
                            +
                            t.vat_rate
                        )
                        * 100

                END AS revenue_vatless,


                COALESCE(
                    t.adjusted_cogs,
                    0
                ) AS cogs_book,

                COALESCE(
                    t.adjusted_cogs_man,
                    0
                ) AS cogs_man,


                COALESCE(
                    t.net_comission,
                    0
                ) AS net_comission,



                CASE

                    WHEN COALESCE(
                        t.cr_rev,
                        0
                    ) > 0
                        THEN 1

                    WHEN COALESCE(
                        t.cr_rev,
                        0
                    ) < 0
                        THEN -1

                    ELSE 0

                END AS net_qty,

     

                CASE

                    WHEN COALESCE(
                        t.cr,
                        0
                    ) = 0
                        THEN 1

                    ELSE 0

                END AS no_book_cost,

                CASE

                    WHEN COALESCE(
                        t.cr_man,
                        0
                    ) = 0
                        THEN 1

                    ELSE 0

                END AS no_man_cost

            FROM base t

            WHERE
                t.cr_rev <> 0

                AND t.date_from::DATE
                    BETWEEN ?::DATE
                    AND ?::DATE

                {filter_sql}
        ),

        aggregated AS (
            SELECT

                entity_name,

                COUNT(
                    DISTINCT usk
                ) AS products_count,

                COUNT(*) AS rows_count,

                SUM(
                    net_qty
                ) AS net_qty,

                SUM(
                    revenue_vat
                ) AS revenue_vat,

                SUM(
                    revenue_vatless
                ) AS revenue_vatless,

                SUM(
                    cogs_book
                ) AS cogs_book,

                SUM(
                    cogs_man
                ) AS cogs_man,

                SUM(
                    net_comission
                ) AS net_comission,

                SUM(
                    no_book_cost
                ) AS no_book_cost,

                SUM(
                    no_man_cost
                ) AS no_man_cost

            FROM prepared

            GROUP BY
                entity_name
        )

        SELECT

            entity_name,

            products_count,

            rows_count,

            net_qty,

            revenue_vat,

            revenue_vatless,

            cogs_book,

            cogs_man,

            net_comission,

          

            revenue_vatless
                - cogs_book
                + net_comission
                AS gross_profit_book,



            revenue_vatless
                - cogs_man
                + net_comission
                AS gross_profit_man,

     
            CASE

                WHEN revenue_vatless = 0
                    THEN NULL

                ELSE
                    (
                        revenue_vatless
                        - cogs_book
                        + net_comission
                    )
                    /
                    revenue_vatless
                    * 100

            END AS margin_book_pct,



            CASE

                WHEN revenue_vatless = 0
                    THEN NULL

                ELSE
                    (
                        revenue_vatless
                        - cogs_man
                        + net_comission
                    )
                    /
                    revenue_vatless
                    * 100

            END AS margin_man_pct,

 

            CASE

                WHEN revenue_vatless = 0
                    THEN NULL

                ELSE
                    cogs_book
                    /
                    revenue_vatless
                    * 100

            END AS cogs_book_share,



            CASE

                WHEN revenue_vatless = 0
                    THEN NULL

                ELSE
                    cogs_man
                    /
                    revenue_vatless
                    * 100

            END AS cogs_man_share,

          

            CASE

                WHEN revenue_vatless = 0
                    THEN NULL

                ELSE
                    -net_comission
                    /
                    revenue_vatless
                    * 100

            END AS commission_pct,

            no_book_cost,

            no_man_cost

        FROM aggregated

        ORDER BY
            revenue_vatless DESC
    """

    # =====================================================
    # Выполнение запроса
    # =====================================================

    with DashboardData() as d:

        rows = d.con.execute(
            sql,
            params,
        ).fetchall()

    # =====================================================
    # Общие суммы
    # =====================================================

    total_revenue_vatless = sum(
        float(
            row[5]
            or 0
        )
        for row in rows
    )

    total_gross_profit_man = sum(
        float(
            row[10]
            or 0
        )
        for row in rows
    )

    # =====================================================
    # Результат
    # =====================================================

    result: list[dict] = []

    for row in rows:

        (
            entity_name,
            products_count,
            rows_count,
            net_qty,
            revenue_vat,
            revenue_vatless,
            cogs_book,
            cogs_man,
            net_comission,
            gross_profit_book,
            gross_profit_man,
            margin_book_pct,
            margin_man_pct,
            cogs_book_share,
            cogs_man_share,
            commission_pct,
            no_book_cost,
            no_man_cost,
        ) = row

        revenue_vat = float(
            revenue_vat
            or 0
        )

        revenue_vatless = float(
            revenue_vatless
            or 0
        )

        cogs_book = float(
            cogs_book
            or 0
        )

        cogs_man = float(
            cogs_man
            or 0
        )

        net_comission = float(
            net_comission
            or 0
        )

        gross_profit_book = float(
            gross_profit_book
            or 0
        )

        gross_profit_man = float(
            gross_profit_man
            or 0
        )

        net_qty = int(
            net_qty
            or 0
        )

        # -------------------------------------------------
        # НДС
        # -------------------------------------------------

        vat_amount = (
            revenue_vat
            - revenue_vatless
        )

        # -------------------------------------------------
        # Доля выручки
        # -------------------------------------------------

        revenue_share_pct = (
            revenue_vatless
            /
            total_revenue_vatless
            * 100

            if total_revenue_vatless

            else 0
        )

        # -------------------------------------------------
        # Доля управленческой прибыли
        # -------------------------------------------------

        profit_share_pct = (
            gross_profit_man
            /
            total_gross_profit_man
            * 100

            if total_gross_profit_man

            else 0
        )

        # -------------------------------------------------
        # Средняя выручка на единицу
        # -------------------------------------------------

        average_revenue = (
            revenue_vatless
            /
            net_qty

            if net_qty > 0

            else 0
        )

        # -------------------------------------------------
        # Формируем результат
        # -------------------------------------------------

        result.append(
            {
                "name": str(
                    entity_name
                    or "Не указано"
                ),

                "products_count": int(
                    products_count
                    or 0
                ),

                "rows_count": int(
                    rows_count
                    or 0
                ),

                "net_qty": net_qty,

                # =========================================
                # Выручка
                # =========================================

                "revenue_vat": round(
                    revenue_vat
                    / 100,
                    2,
                ),

                "vat_amount": round(
                    vat_amount
                    / 100,
                    2,
                ),

                "revenue_vatless": round(
                    revenue_vatless
                    / 100,
                    2,
                ),

                "revenue_share_pct": round(
                    revenue_share_pct,
                    2,
                ),

                "average_revenue": round(
                    average_revenue
                    / 100,
                    2,
                ),

                # =========================================
                # Комиссия WB
                # =========================================

                "net_comission": round(
                    net_comission
                    / 100,
                    2,
                ),

                "commission_pct": round(
                    float(
                        commission_pct
                        or 0
                    ),
                    2,
                ),

                # =========================================
                # Бухгалтерская себестоимость
                # =========================================

                "cogs_book": round(
                    cogs_book
                    / 100,
                    2,
                ),

                "gross_profit_book": round(
                    gross_profit_book
                    / 100,
                    2,
                ),

                "margin_book_pct": round(
                    float(
                        margin_book_pct
                        or 0
                    ),
                    2,
                ),

                "cogs_book_share": round(
                    float(
                        cogs_book_share
                        or 0
                    ),
                    2,
                ),

                # =========================================
                # Управленческая себестоимость
                # =========================================

                "cogs_man": round(
                    cogs_man
                    / 100,
                    2,
                ),

                "gross_profit_man": round(
                    gross_profit_man
                    / 100,
                    2,
                ),

                "margin_man_pct": round(
                    float(
                        margin_man_pct
                        or 0
                    ),
                    2,
                ),

                "cogs_man_share": round(
                    float(
                        cogs_man_share
                        or 0
                    ),
                    2,
                ),

                # =========================================
                # Структура прибыли
                # =========================================

                "profit_share_pct": round(
                    profit_share_pct,
                    2,
                ),

                # =========================================
                # Контроль качества данных
                # =========================================

                "no_book_cost": int(
                    no_book_cost
                    or 0
                ),

                "no_man_cost": int(
                    no_man_cost
                    or 0
                ),
            }
        )

    return result


