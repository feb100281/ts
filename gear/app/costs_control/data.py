# # gear/app/costs_control/data.py
# from __future__ import annotations

# import pandas as pd

# from conns import get_duckdb_conn_with_opt



# def get_price_analysis_data(
#     date_from: str | None = None,
#     date_to: str | None = None,
# ) -> pd.DataFrame:
#     """
#     Возвращает агрегированный анализ закупочных цен по NM ID.

#     Кеш действует в рамках процесса.
#     Для обновления данных вызывается clear_price_analysis_cache().
#     """
    
#     where_conditions = [
#         "t.nm_id IS NOT NULL",
#     ]

#     query_params: list[str] = []

#     if date_from:
#         where_conditions.append(
#             "u.date::DATE >= CAST(? AS DATE)"
#         )
#         query_params.append(date_from)

#     if date_to:
#         where_conditions.append(
#             "u.date::DATE <= CAST(? AS DATE)"
#         )
#         query_params.append(date_to)

#     where_sql = "\n                    AND ".join(
#         where_conditions
#     )

#     with get_duckdb_conn_with_opt() as con:
#         df = con.execute(
#             """
#             WITH products AS (
#                 SELECT
#                     card_id AS nm_id,
#                     ANY_VALUE(title) AS title
#                 FROM inventories.wb_product
#                 WHERE card_id IS NOT NULL
#                 GROUP BY card_id
#             ),

#             product_attrs AS (
#                 SELECT
#                     nm_id,
#                     ANY_VALUE(subject_name) AS subject_name
#                 FROM cards.product
#                 WHERE nm_id IS NOT NULL
#                 GROUP BY nm_id
#             ),

#             brands AS (
#                 SELECT
#                     nm_id,
#                     COALESCE(
#                         MAX(brand),
#                         'Бренд не указан'
#                     ) AS brand
#                 FROM cards.unpacked_cards
#                 WHERE nm_id IS NOT NULL
#                 GROUP BY nm_id
#             ),

#             suppliers AS (
#                 SELECT
#                     t.nm_id,

#                     STRING_AGG(
#                         DISTINCT COALESCE(
#                             cp.name,
#                             'Поставщик не указан'
#                         ),
#                         ', '
#                         ORDER BY COALESCE(
#                             cp.name,
#                             'Поставщик не указан'
#                         )
#                     ) AS suppliers

#                 FROM inventories.upd_income t

#                 LEFT JOIN inventories.upd_documents u
#                     ON u.id = t.upd_document_id

#                 LEFT JOIN pg.counterparties_counterparty cp
#                     ON cp.id = u.counterparty_id

#                 WHERE t.nm_id IS NOT NULL

#                 GROUP BY t.nm_id
#             ),

#             base AS (
#                 SELECT
#                     t.nm_id,

#                     COALESCE(
#                         p.title,
#                         'Наименование не указано'
#                     ) AS "Наименование",

#                     COALESCE(
#                         b.brand,
#                         'Бренд не указан'
#                     ) AS "Бренд",

#                     COALESCE(
#                         pa.subject_name,
#                         'Категория не указана'
#                     ) AS "Категория",

#                     COALESCE(
#                         s.suppliers,
#                         'Поставщик не указан'
#                     ) AS "Поставщики",

#                     MIN(u.date)::DATE
#                         AS "Первая дата УПД",

#                     MAX(u.date)::DATE
#                         AS "Последняя дата УПД",

#                     COUNT(*)
#                         AS "Кол-во записей",

#                     SUM(
#                         COALESCE(t.upd_qty, 0)
#                     ) AS "Кол-во, шт",

#                     COUNT(
#                         DISTINCT t.upd_document_id
#                     ) AS "Кол-во УПД",

#                     /* Бухгалтерская себестоимость */

#                     ROUND(
#                         MEDIAN(t.upd_price_vatless),
#                         2
#                     ) AS "Медиана цены, бух",

#                     ROUND(
#                         AVG(t.upd_price_vatless),
#                         2
#                     ) AS "Средняя цена, бух",

#                     ROUND(
#                         STDDEV_SAMP(t.upd_price_vatless),
#                         2
#                     ) AS "Ст. отклонение, руб., бух",

#                     ROUND(
#                         STDDEV_SAMP(t.upd_price_vatless)
#                         / NULLIF(
#                             AVG(t.upd_price_vatless),
#                             0
#                         )
#                         * 100,
#                         2
#                     ) AS "Коэффициент вариации, %, бух",

#                     ROUND(
#                         MIN(t.upd_price_vatless),
#                         2
#                     ) AS "Мин. цена, бух",

#                     ROUND(
#                         MAX(t.upd_price_vatless),
#                         2
#                     ) AS "Макс. цена, бух",

#                     ROUND(
#                         MAX(t.upd_price_vatless)
#                         - MIN(t.upd_price_vatless),
#                         2
#                     ) AS "Диапазон цены, бух",

#                     COUNT(
#                         DISTINCT t.upd_price_vatless
#                     ) AS "Кол-во разных цен, бух",

#                     /* Управленческая себестоимость */

#                     ROUND(
#                         MEDIAN(t.man_cost_per_unit),
#                         2
#                     ) AS "Медиана цены, упр",

#                     ROUND(
#                         AVG(t.man_cost_per_unit),
#                         2
#                     ) AS "Средняя цена, упр",

#                     ROUND(
#                         STDDEV_SAMP(t.man_cost_per_unit),
#                         2
#                     ) AS "Ст. отклонение, руб., упр",

#                     ROUND(
#                         STDDEV_SAMP(t.man_cost_per_unit)
#                         / NULLIF(
#                             AVG(t.man_cost_per_unit),
#                             0
#                         )
#                         * 100,
#                         2
#                     ) AS "Коэффициент вариации, %, упр",

#                     ROUND(
#                         MIN(t.man_cost_per_unit),
#                         2
#                     ) AS "Мин. цена, упр",

#                     ROUND(
#                         MAX(t.man_cost_per_unit),
#                         2
#                     ) AS "Макс. цена, упр",

#                     ROUND(
#                         MAX(t.man_cost_per_unit)
#                         - MIN(t.man_cost_per_unit),
#                         2
#                     ) AS "Диапазон цены, упр",

#                     COUNT(
#                         DISTINCT t.man_cost_per_unit
#                     ) AS "Кол-во разных цен, упр"

#                 FROM inventories.upd_income t

#                 LEFT JOIN inventories.upd_documents u
#                     ON u.id = t.upd_document_id

#                 LEFT JOIN products p
#                     ON p.nm_id = t.nm_id

#                 LEFT JOIN product_attrs pa
#                     ON pa.nm_id = t.nm_id

#                 LEFT JOIN brands b
#                     ON b.nm_id = t.nm_id

#                 LEFT JOIN suppliers s
#                     ON s.nm_id = t.nm_id

#                 WHERE t.nm_id IS NOT NULL

#                 GROUP BY
#                     t.nm_id,
#                     p.title,
#                     b.brand,
#                     pa.subject_name,
#                     s.suppliers
#             )

#             SELECT
#                 base.*,

#                 CASE
#                     WHEN "Кол-во разных цен, бух" <= 1
#                         THEN '0. Одна цена'

#                     WHEN "Коэффициент вариации, %, бух" < 25
#                         THEN '1. До 25%'

#                     WHEN "Коэффициент вариации, %, бух" < 50
#                         THEN '2. От 25% до 50%'

#                     WHEN "Коэффициент вариации, %, бух" < 75
#                         THEN '3. От 50% до 75%'

#                     ELSE '4. 75% и выше'
#                 END AS "Ранг CV, бух",

#                 CASE
#                     WHEN "Кол-во разных цен, упр" <= 1
#                         THEN '0. Одна цена'

#                     WHEN "Коэффициент вариации, %, упр" < 25
#                         THEN '1. До 25%'

#                     WHEN "Коэффициент вариации, %, упр" < 50
#                         THEN '2. От 25% до 50%'

#                     WHEN "Коэффициент вариации, %, упр" < 75
#                         THEN '3. От 50% до 75%'

#                     ELSE '4. 75% и выше'
#                 END AS "Ранг CV, упр",

#                 ROUND(
#                     (
#                         "Макс. цена, бух"
#                         - "Медиана цены, бух"
#                     )
#                     / NULLIF(
#                         "Медиана цены, бух",
#                         0
#                     )
#                     * 100,
#                     2
#                 ) AS "Макс. отклонение от медианы, %, бух",

#                 ROUND(
#                     (
#                         "Мин. цена, бух"
#                         - "Медиана цены, бух"
#                     )
#                     / NULLIF(
#                         "Медиана цены, бух",
#                         0
#                     )
#                     * 100,
#                     2
#                 ) AS "Мин. отклонение от медианы, %, бух",

#                 ROUND(
#                     (
#                         "Макс. цена, упр"
#                         - "Медиана цены, упр"
#                     )
#                     / NULLIF(
#                         "Медиана цены, упр",
#                         0
#                     )
#                     * 100,
#                     2
#                 ) AS "Макс. отклонение от медианы, %, упр",

#                 ROUND(
#                     (
#                         "Мин. цена, упр"
#                         - "Медиана цены, упр"
#                     )
#                     / NULLIF(
#                         "Медиана цены, упр",
#                         0
#                     )
#                     * 100,
#                     2
#                 ) AS "Мин. отклонение от медианы, %, упр",

#                 ROUND(
#                     "Медиана цены, упр"
#                     - "Медиана цены, бух",
#                     2
#                 ) AS "Δ медианы упр-бух, руб.",

#                 ROUND(
#                     (
#                         "Медиана цены, упр"
#                         - "Медиана цены, бух"
#                     )
#                     / NULLIF(
#                         "Медиана цены, бух",
#                         0
#                     )
#                     * 100,
#                     2
#                 ) AS "Δ медианы упр-бух, %"

#             FROM base

#             ORDER BY
#                 CASE
#                     WHEN "Кол-во разных цен, бух" <= 1
#                         THEN 0

#                     WHEN "Коэффициент вариации, %, бух" < 25
#                         THEN 1

#                     WHEN "Коэффициент вариации, %, бух" < 50
#                         THEN 2

#                     WHEN "Коэффициент вариации, %, бух" < 75
#                         THEN 3

#                     ELSE 4
#                 END DESC,

#                 "Коэффициент вариации, %, бух"
#                     DESC NULLS LAST,

#                 nm_id
#             """
#         ).df()

#     if df.empty:
#         return df

#     df["nm_id"] = (
#         pd.to_numeric(
#             df["nm_id"],
#             errors="coerce",
#         )
#         .astype("Int64")
#         .astype("string")
#     )

#     for column in [
#         "Первая дата УПД",
#         "Последняя дата УПД",
#     ]:
#         if column in df.columns:
#             df[column] = pd.to_datetime(
#                 df[column],
#                 errors="coerce",
#             )

#     return df



# def get_price_history_data() -> pd.DataFrame:
#     """
#     Возвращает построчную историю закупочных цен.
#     """

#     with get_duckdb_conn_with_opt() as con:
#         df = con.execute(
#             """
#             WITH products AS (
#                 SELECT
#                     card_id AS nm_id,
#                     ANY_VALUE(title) AS title
#                 FROM inventories.wb_product
#                 WHERE card_id IS NOT NULL
#                 GROUP BY card_id
#             )

#             SELECT
#                 t.nm_id,

#                 COALESCE(
#                     p.title,
#                     'Наименование не указано'
#                 ) AS "Наименование",

#                 u.date::DATE
#                     AS "Дата УПД",

#                 t.upd_document_id
#                     AS "ID УПД",

#                 COALESCE(
#                     CAST(u.number AS VARCHAR),
#                     ''
#                 ) AS "Номер УПД",

#                 COALESCE(
#                     cp.name,
#                     'Поставщик не указан'
#                 ) AS "Поставщик",

#                 ROUND(
#                     t.upd_price_vatless,
#                     2
#                 ) AS "Цена, бух",

#                 ROUND(
#                     t.man_cost_per_unit,
#                     2
#                 ) AS "Цена, упр",

#                 COALESCE(
#                     t.upd_qty,
#                     0
#                 ) AS "Количество, шт"

#             FROM inventories.upd_income t

#             LEFT JOIN inventories.upd_documents u
#                 ON u.id = t.upd_document_id

#             LEFT JOIN products p
#                 ON p.nm_id = t.nm_id

#             LEFT JOIN pg.counterparties_counterparty cp
#                 ON cp.id = u.counterparty_id

#             WHERE t.nm_id IS NOT NULL

#             ORDER BY
#                 t.nm_id,
#                 u.date,
#                 t.upd_document_id
#             """
#         ).df()

#     if df.empty:
#         return df

#     df["nm_id"] = (
#         pd.to_numeric(
#             df["nm_id"],
#             errors="coerce",
#         )
#         .astype("Int64")
#         .astype("string")
#     )

#     df["ID УПД"] = (
#         pd.to_numeric(
#             df["ID УПД"],
#             errors="coerce",
#         )
#         .astype("Int64")
#         .astype("string")
#     )

#     df["Номер УПД"] = (
#         df["Номер УПД"]
#         .astype("string")
#         .fillna("")
#     )

#     df["Поставщик"] = (
#         df["Поставщик"]
#         .fillna("Поставщик не указан")
#     )

#     df["Дата УПД"] = pd.to_datetime(
#         df["Дата УПД"],
#         errors="coerce",
#     )

#     return df


# def get_price_analysis_period(
#     df: pd.DataFrame,
# ) -> tuple:
#     """
#     Возвращает первую и последнюю даты УПД.
#     """

#     if df.empty:
#         return None, None

#     start = pd.to_datetime(
#         df["Первая дата УПД"],
#         errors="coerce",
#     ).min()

#     end = pd.to_datetime(
#         df["Последняя дата УПД"],
#         errors="coerce",
#     ).max()

#     return (
#         start.date()
#         if pd.notna(start)
#         else None,

#         end.date()
#         if pd.notna(end)
#         else None,
#     )




# gear/app/costs_control/data.py
from __future__ import annotations

import pandas as pd
from datetime import date

from conns import get_duckdb_conn_with_opt


# ---------------------------------------------------------------------
# Агрегированный анализ закупочных цен
# ---------------------------------------------------------------------


def get_price_analysis_data(
    date_from: str | None = None,
    date_to: str | None = None,
) -> pd.DataFrame:
    """
    Возвращает агрегированный анализ
    закупочных цен по NM ID.

    Если переданы date_from и date_to,
    сначала выбираются только УПД
    за указанный период.

    После фильтрации периода рассчитываются:

    - первая и последняя дата УПД;
    - количество записей и документов;
    - медианная и средняя цена;
    - стандартное отклонение;
    - коэффициент вариации;
    - минимальная и максимальная цена;
    - количество различных цен;
    - отклонение от медианы.
    """

    # -----------------------------------------------------------------
    # Условия SQL-фильтра
    # -----------------------------------------------------------------

    where_conditions = [
        "t.nm_id IS NOT NULL",
    ]

    query_params: list[str] = []

    if date_from:
        where_conditions.append(
            "u.date::DATE >= CAST(? AS DATE)"
        )
        query_params.append(
            str(date_from)[:10]
        )

    if date_to:
        where_conditions.append(
            "u.date::DATE <= CAST(? AS DATE)"
        )
        query_params.append(
            str(date_to)[:10]
        )

    where_sql = "\n                    AND ".join(
        where_conditions
    )
    
    


    # -----------------------------------------------------------------
    # Запрос
    # -----------------------------------------------------------------

    with get_duckdb_conn_with_opt() as con:
        df = con.execute(
            f"""
            WITH products AS (
                SELECT
                    card_id AS nm_id,
                    ANY_VALUE(title) AS title

                FROM inventories.wb_product

                WHERE card_id IS NOT NULL

                GROUP BY
                    card_id
            ),

            product_attrs AS (
                SELECT
                    nm_id,
                    ANY_VALUE(subject_name)
                        AS subject_name

                FROM cards.product

                WHERE nm_id IS NOT NULL

                GROUP BY
                    nm_id
            ),

            brands AS (
                SELECT
                    nm_id,

                    COALESCE(
                        MAX(brand),
                        'Бренд не указан'
                    ) AS brand

                FROM cards.unpacked_cards

                WHERE nm_id IS NOT NULL

                GROUP BY
                    nm_id
            ),

            suppliers AS (
                SELECT
                    t.nm_id,

                    STRING_AGG(
                        DISTINCT COALESCE(
                            cp.name,
                            'Поставщик не указан'
                        ),
                        ', '
                        ORDER BY COALESCE(
                            cp.name,
                            'Поставщик не указан'
                        )
                    ) AS suppliers

                FROM inventories.upd_income t

                LEFT JOIN inventories.upd_documents u
                    ON u.id = t.upd_document_id

                LEFT JOIN pg.counterparties_counterparty cp
                    ON cp.id = u.counterparty_id

                WHERE
                    {where_sql}

                GROUP BY
                    t.nm_id
            ),

            base AS (
                SELECT
                    t.nm_id,

                    COALESCE(
                        p.title,
                        'Наименование не указано'
                    ) AS "Наименование",

                    COALESCE(
                        b.brand,
                        'Бренд не указан'
                    ) AS "Бренд",

                    COALESCE(
                        pa.subject_name,
                        'Категория не указана'
                    ) AS "Категория",

                    COALESCE(
                        s.suppliers,
                        'Поставщик не указан'
                    ) AS "Поставщики",

                    MIN(u.date)::DATE
                        AS "Первая дата УПД",

                    MAX(u.date)::DATE
                        AS "Последняя дата УПД",

                    COUNT(*)
                        AS "Кол-во записей",

                    SUM(
                        COALESCE(
                            t.upd_qty,
                            0
                        )
                    ) AS "Кол-во, шт",

                    COUNT(
                        DISTINCT
                        t.upd_document_id
                    ) AS "Кол-во УПД",

                    /* ---------------------------------------------
                       Бухгалтерская себестоимость
                       --------------------------------------------- */

                    ROUND(
                        MEDIAN(
                            t.upd_price_vatless
                        ),
                        2
                    ) AS "Медиана цены, бух",

                    ROUND(
                        AVG(
                            t.upd_price_vatless
                        ),
                        2
                    ) AS "Средняя цена, бух",

                    ROUND(
                        STDDEV_SAMP(
                            t.upd_price_vatless
                        ),
                        2
                    ) AS "Ст. отклонение, руб., бух",

                    ROUND(
                        STDDEV_SAMP(
                            t.upd_price_vatless
                        )
                        / NULLIF(
                            AVG(
                                t.upd_price_vatless
                            ),
                            0
                        )
                        * 100,
                        2
                    ) AS "Коэффициент вариации, %, бух",

                    ROUND(
                        MIN(
                            t.upd_price_vatless
                        ),
                        2
                    ) AS "Мин. цена, бух",

                    ROUND(
                        MAX(
                            t.upd_price_vatless
                        ),
                        2
                    ) AS "Макс. цена, бух",

                    ROUND(
                        MAX(
                            t.upd_price_vatless
                        )
                        - MIN(
                            t.upd_price_vatless
                        ),
                        2
                    ) AS "Диапазон цены, бух",

                    COUNT(
                        DISTINCT
                        t.upd_price_vatless
                    ) AS "Кол-во разных цен, бух",

                    /* ---------------------------------------------
                       Управленческая себестоимость
                       --------------------------------------------- */

                    ROUND(
                        MEDIAN(
                            t.man_cost_per_unit
                        ),
                        2
                    ) AS "Медиана цены, упр",

                    ROUND(
                        AVG(
                            t.man_cost_per_unit
                        ),
                        2
                    ) AS "Средняя цена, упр",

                    ROUND(
                        STDDEV_SAMP(
                            t.man_cost_per_unit
                        ),
                        2
                    ) AS "Ст. отклонение, руб., упр",

                    ROUND(
                        STDDEV_SAMP(
                            t.man_cost_per_unit
                        )
                        / NULLIF(
                            AVG(
                                t.man_cost_per_unit
                            ),
                            0
                        )
                        * 100,
                        2
                    ) AS "Коэффициент вариации, %, упр",

                    ROUND(
                        MIN(
                            t.man_cost_per_unit
                        ),
                        2
                    ) AS "Мин. цена, упр",

                    ROUND(
                        MAX(
                            t.man_cost_per_unit
                        ),
                        2
                    ) AS "Макс. цена, упр",

                    ROUND(
                        MAX(
                            t.man_cost_per_unit
                        )
                        - MIN(
                            t.man_cost_per_unit
                        ),
                        2
                    ) AS "Диапазон цены, упр",

                    COUNT(
                        DISTINCT
                        t.man_cost_per_unit
                    ) AS "Кол-во разных цен, упр"

                FROM inventories.upd_income t

                LEFT JOIN inventories.upd_documents u
                    ON u.id = t.upd_document_id

                LEFT JOIN products p
                    ON p.nm_id = t.nm_id

                LEFT JOIN product_attrs pa
                    ON pa.nm_id = t.nm_id

                LEFT JOIN brands b
                    ON b.nm_id = t.nm_id

                LEFT JOIN suppliers s
                    ON s.nm_id = t.nm_id

                WHERE
                    {where_sql}

                GROUP BY
                    t.nm_id,
                    p.title,
                    b.brand,
                    pa.subject_name,
                    s.suppliers
            )

            SELECT
                base.*,
                "Мин. цена, бух" as min_acc_price,
                "Макс. цена, бух" as max_acc_price,
                "Мин. цена, упр" AS min_man_price,
                "Макс. цена, упр" as max_man_price,

                CASE
                    WHEN
                        "Кол-во разных цен, бух" <= 1
                    THEN
                        '0. Одна цена'

                    WHEN
                        "Коэффициент вариации, %, бух" < 25
                    THEN
                        '1. До 25%'

                    WHEN
                        "Коэффициент вариации, %, бух" < 50
                    THEN
                        '2. От 25% до 50%'

                    WHEN
                        "Коэффициент вариации, %, бух" < 75
                    THEN
                        '3. От 50% до 75%'

                    ELSE
                        '4. 75% и выше'
                END AS "Ранг CV, бух",

                CASE
                    WHEN
                        "Кол-во разных цен, упр" <= 1
                    THEN
                        '0. Одна цена'

                    WHEN
                        "Коэффициент вариации, %, упр" < 25
                    THEN
                        '1. До 25%'

                    WHEN
                        "Коэффициент вариации, %, упр" < 50
                    THEN
                        '2. От 25% до 50%'

                    WHEN
                        "Коэффициент вариации, %, упр" < 75
                    THEN
                        '3. От 50% до 75%'

                    ELSE
                        '4. 75% и выше'
                END AS "Ранг CV, упр",

                ROUND(
                    (
                        "Макс. цена, бух"
                        - "Медиана цены, бух"
                    )
                    / NULLIF(
                        "Медиана цены, бух",
                        0
                    )
                    * 100,
                    2
                ) AS
                    "Макс. отклонение от медианы, %, бух",

                ROUND(
                    (
                        "Мин. цена, бух"
                        - "Медиана цены, бух"
                    )
                    / NULLIF(
                        "Медиана цены, бух",
                        0
                    )
                    * 100,
                    2
                ) AS
                    "Мин. отклонение от медианы, %, бух",

                ROUND(
                    (
                        "Макс. цена, упр"
                        - "Медиана цены, упр"
                    )
                    / NULLIF(
                        "Медиана цены, упр",
                        0
                    )
                    * 100,
                    2
                ) AS
                    "Макс. отклонение от медианы, %, упр",

                ROUND(
                    (
                        "Мин. цена, упр"
                        - "Медиана цены, упр"
                    )
                    / NULLIF(
                        "Медиана цены, упр",
                        0
                    )
                    * 100,
                    2
                ) AS
                    "Мин. отклонение от медианы, %, упр",

                ROUND(
                    "Медиана цены, упр"
                    - "Медиана цены, бух",
                    2
                ) AS "Δ медианы упр-бух, руб.",

                ROUND(
                    (
                        "Медиана цены, упр"
                        - "Медиана цены, бух"
                    )
                    / NULLIF(
                        "Медиана цены, бух",
                        0
                    )
                    * 100,
                    2
                ) AS "Δ медианы упр-бух, %"

            FROM base

            ORDER BY
                CASE
                    WHEN
                        "Кол-во разных цен, бух" <= 1
                    THEN 0

                    WHEN
                        "Коэффициент вариации, %, бух" < 25
                    THEN 1

                    WHEN
                        "Коэффициент вариации, %, бух" < 50
                    THEN 2

                    WHEN
                        "Коэффициент вариации, %, бух" < 75
                    THEN 3

                    ELSE 4
                END DESC,

                "Коэффициент вариации, %, бух"
                    DESC NULLS LAST,

                nm_id
            """,
            query_params * 2,
        ).df()

    if df.empty:
        return df

    # -----------------------------------------------------------------
    # Типы данных
    # -----------------------------------------------------------------

    df["nm_id"] = (
        pd.to_numeric(
            df["nm_id"],
            errors="coerce",
        )
        .astype("Int64")
        .astype("string")
    )

    for column in (
        "Первая дата УПД",
        "Последняя дата УПД",
    ):
        if column in df.columns:
            df[column] = pd.to_datetime(
                df[column],
                errors="coerce",
            )

    df = df.fillna(0.0)
    return df


# ---------------------------------------------------------------------
# История закупочных цен
# ---------------------------------------------------------------------


def get_price_history_data() -> pd.DataFrame:
    """
    Возвращает построчную историю
    закупочных цен.

    Фильтрация по периоду выполняется
    позднее в filter_history_data().
    """

    with get_duckdb_conn_with_opt() as con:
        df = con.execute(
            """
            WITH products AS (
                SELECT
                    card_id AS nm_id,
                    ANY_VALUE(title) AS title

                FROM inventories.wb_product

                WHERE card_id IS NOT NULL

                GROUP BY
                    card_id
            )

            SELECT
                t.nm_id,

                COALESCE(
                    p.title,
                    'Наименование не указано'
                ) AS "Наименование",

                u.date::DATE
                    AS "Дата УПД",

                t.upd_document_id
                    AS "ID УПД",

                COALESCE(
                    CAST(
                        u.number AS VARCHAR
                    ),
                    ''
                ) AS "Номер УПД",

                COALESCE(
                    cp.name,
                    'Поставщик не указан'
                ) AS "Поставщик",

                ROUND(
                    t.upd_price_vatless,
                    2
                ) AS "Цена, бух",

                ROUND(
                    t.man_cost_per_unit,
                    2
                ) AS "Цена, упр",

                COALESCE(
                    t.upd_qty,
                    0
                ) AS "Количество, шт"

            FROM inventories.upd_income t

            LEFT JOIN inventories.upd_documents u
                ON u.id = t.upd_document_id

            LEFT JOIN products p
                ON p.nm_id = t.nm_id

            LEFT JOIN pg.counterparties_counterparty cp
                ON cp.id = u.counterparty_id

            WHERE
                t.nm_id IS NOT NULL

            ORDER BY
                t.nm_id,
                u.date,
                t.upd_document_id
            """
        ).df()

    if df.empty:
        return df

    # -----------------------------------------------------------------
    # Типы данных
    # -----------------------------------------------------------------

    df["nm_id"] = (
        pd.to_numeric(
            df["nm_id"],
            errors="coerce",
        )
        .astype("Int64")
        .astype("string")
    )

    df["ID УПД"] = (
        pd.to_numeric(
            df["ID УПД"],
            errors="coerce",
        )
        .astype("Int64")
        .astype("string")
    )

    df["Номер УПД"] = (
        df["Номер УПД"]
        .astype("string")
        .fillna("")
    )

    df["Поставщик"] = (
        df["Поставщик"]
        .fillna(
            "Поставщик не указан"
        )
    )

    df["Дата УПД"] = pd.to_datetime(
        df["Дата УПД"],
        errors="coerce",
    )

    return df


# ---------------------------------------------------------------------
# Минимальная дата УПД
# ---------------------------------------------------------------------


def get_min_upd_date() -> date:
    """
    Возвращает самую раннюю дату УПД
    в базе данных.
    """

    with get_duckdb_conn_with_opt() as con:
        result = con.execute(
            """
            SELECT
                MIN(date)::DATE
            FROM inventories.upd_documents
            """
        ).fetchone()

    if result and result[0]:
        return result[0]

    return date.today()

# ---------------------------------------------------------------------
# Период анализа
# ---------------------------------------------------------------------


def get_price_analysis_period(
    df: pd.DataFrame,
) -> tuple:
    """
    Возвращает первую и последнюю
    даты УПД в DataFrame.
    """

    if df.empty:
        return None, None

    if (
        "Первая дата УПД"
        not in df.columns
        or "Последняя дата УПД"
        not in df.columns
    ):
        return None, None

    start = pd.to_datetime(
        df["Первая дата УПД"],
        errors="coerce",
    ).min()

    end = pd.to_datetime(
        df["Последняя дата УПД"],
        errors="coerce",
    ).max()

    return (
        (
            start.date()
            if pd.notna(start)
            else None
        ),
        (
            end.date()
            if pd.notna(end)
            else None
        ),
    )

