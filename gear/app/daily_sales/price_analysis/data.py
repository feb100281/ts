# gear/app/daily_sales/price_analysis/data.py
from __future__ import annotations

import pandas as pd

from conns import get_duckdb_conn_with_opt


def get_price_analysis_data() -> pd.DataFrame:
    """Возвращает анализ бухгалтерской и управленческой себестоимости по NM ID."""

    with get_duckdb_conn_with_opt() as con:
        df = con.execute(
            """
            WITH products AS (
                SELECT
                    card_id AS nm_id,
                    ANY_VALUE(title) AS title
                FROM inventories.wb_product
                WHERE card_id IS NOT NULL
                GROUP BY card_id
            ),

            product_attrs AS (
                SELECT
                    nm_id,
                    ANY_VALUE(subject_name) AS subject_name
                FROM cards.product
                WHERE nm_id IS NOT NULL
                GROUP BY nm_id
            ),

            brands AS (
                SELECT
                    nm_id,
                    COALESCE(MAX(brand), 'Бренд не указан') AS brand
                FROM cards.unpacked_cards
                WHERE nm_id IS NOT NULL
                GROUP BY nm_id
            ),

            base AS (
                SELECT
                    t.nm_id,
                    p.title AS "Наименование",
                    COALESCE(b.brand, 'Бренд не указан') AS "Бренд",
                    COALESCE(pa.subject_name, 'Категория не указана') AS "Категория",

                    MIN(u.date)::DATE AS "Первая дата УПД",
                    MAX(u.date)::DATE AS "Последняя дата УПД",

                    COUNT(*) AS "Кол-во записей",
                    SUM(COALESCE(t.upd_qty, 0)) AS "Кол-во, шт",
                    COUNT(DISTINCT t.upd_document_id) AS "Кол-во УПД",

                    ROUND(MEDIAN(t.upd_price_vatless), 2)
                        AS "Медиана цены, бух",

                    ROUND(AVG(t.upd_price_vatless), 2)
                        AS "Средняя цена, бух",

                    ROUND(STDDEV_SAMP(t.upd_price_vatless), 2)
                        AS "Ст. отклонение, руб., бух",

                    ROUND(
                        STDDEV_SAMP(t.upd_price_vatless)
                        / NULLIF(AVG(t.upd_price_vatless), 0)
                        * 100,
                        2
                    ) AS "Коэффициент вариации, %, бух",

                    ROUND(MIN(t.upd_price_vatless), 2)
                        AS "Мин. цена, бух",

                    ROUND(MAX(t.upd_price_vatless), 2)
                        AS "Макс. цена, бух",

                    ROUND(
                        MAX(t.upd_price_vatless)
                        - MIN(t.upd_price_vatless),
                        2
                    ) AS "Диапазон цены, бух",

                    COUNT(DISTINCT t.upd_price_vatless)
                        AS "Кол-во разных цен, бух",

                    LIST(
                        ROUND(t.upd_price_vatless, 2)
                        ORDER BY u.date, t.upd_document_id
                    ) AS "История цен, бух",

                    ROUND(MEDIAN(t.man_cost_per_unit), 2)
                        AS "Медиана цены, упр",

                    ROUND(AVG(t.man_cost_per_unit), 2)
                        AS "Средняя цена, упр",

                    ROUND(STDDEV_SAMP(t.man_cost_per_unit), 2)
                        AS "Ст. отклонение, руб., упр",

                    ROUND(
                        STDDEV_SAMP(t.man_cost_per_unit)
                        / NULLIF(AVG(t.man_cost_per_unit), 0)
                        * 100,
                        2
                    ) AS "Коэффициент вариации, %, упр",

                    ROUND(MIN(t.man_cost_per_unit), 2)
                        AS "Мин. цена, упр",

                    ROUND(MAX(t.man_cost_per_unit), 2)
                        AS "Макс. цена, упр",

                    ROUND(
                        MAX(t.man_cost_per_unit)
                        - MIN(t.man_cost_per_unit),
                        2
                    ) AS "Диапазон цены, упр",

                    COUNT(DISTINCT t.man_cost_per_unit)
                        AS "Кол-во разных цен, упр",

                    LIST(
                        ROUND(t.man_cost_per_unit, 2)
                        ORDER BY u.date, t.upd_document_id
                    ) AS "История цен, упр"

                FROM inventories.upd_income t

                LEFT JOIN inventories.upd_documents u
                    ON u.id = t.upd_document_id

                LEFT JOIN products p
                    ON p.nm_id = t.nm_id

                LEFT JOIN product_attrs pa
                    ON pa.nm_id = t.nm_id

                LEFT JOIN brands b
                    ON b.nm_id = t.nm_id

                WHERE t.nm_id IS NOT NULL

                GROUP BY
                    t.nm_id,
                    p.title,
                    b.brand,
                    pa.subject_name
            )

            SELECT
                base.*,

                CASE
                    WHEN "Кол-во разных цен, бух" <= 1
                        THEN '0. Одна цена'
                    WHEN "Коэффициент вариации, %, бух" < 25
                        THEN '1. До 25%'
                    WHEN "Коэффициент вариации, %, бух" < 50
                        THEN '2. От 25% до 50%'
                    WHEN "Коэффициент вариации, %, бух" < 75
                        THEN '3. От 50% до 75%'
                    ELSE '4. 75% и выше'
                END AS "Ранг CV, бух",

                CASE
                    WHEN "Кол-во разных цен, упр" <= 1
                        THEN '0. Одна цена'
                    WHEN "Коэффициент вариации, %, упр" < 25
                        THEN '1. До 25%'
                    WHEN "Коэффициент вариации, %, упр" < 50
                        THEN '2. От 25% до 50%'
                    WHEN "Коэффициент вариации, %, упр" < 75
                        THEN '3. От 50% до 75%'
                    ELSE '4. 75% и выше'
                END AS "Ранг CV, упр",

                ROUND(
                    ("Макс. цена, бух" - "Медиана цены, бух")
                    / NULLIF("Медиана цены, бух", 0)
                    * 100,
                    2
                ) AS "Макс. отклонение от медианы, %, бух",

                ROUND(
                    ("Мин. цена, бух" - "Медиана цены, бух")
                    / NULLIF("Медиана цены, бух", 0)
                    * 100,
                    2
                ) AS "Мин. отклонение от медианы, %, бух",

                ROUND(
                    ("Макс. цена, упр" - "Медиана цены, упр")
                    / NULLIF("Медиана цены, упр", 0)
                    * 100,
                    2
                ) AS "Макс. отклонение от медианы, %, упр",

                ROUND(
                    ("Мин. цена, упр" - "Медиана цены, упр")
                    / NULLIF("Медиана цены, упр", 0)
                    * 100,
                    2
                ) AS "Мин. отклонение от медианы, %, упр",

                ROUND(
                    "Медиана цены, упр" - "Медиана цены, бух",
                    2
                ) AS "Δ медианы упр-бух, руб.",

                ROUND(
                    ("Медиана цены, упр" - "Медиана цены, бух")
                    / NULLIF("Медиана цены, бух", 0)
                    * 100,
                    2
                ) AS "Δ медианы упр-бух, %"

            FROM base

            ORDER BY
                CASE
                    WHEN "Кол-во разных цен, бух" <= 1 THEN 0
                    WHEN "Коэффициент вариации, %, бух" < 25 THEN 1
                    WHEN "Коэффициент вариации, %, бух" < 50 THEN 2
                    WHEN "Коэффициент вариации, %, бух" < 75 THEN 3
                    ELSE 4
                END DESC,
                "Коэффициент вариации, %, бух" DESC NULLS LAST
            """
        ).df()

    if df.empty:
        return df

    df["nm_id"] = df["nm_id"].astype("int64")
    df["nm_id"] = df["nm_id"].astype("string")

    for col in ["История цен, бух", "История цен, упр"]:
        if col in df.columns:
            df[col] = df[col].apply(_history_to_text)

    return df




def get_price_history_data() -> pd.DataFrame:
    """
    Детальная история себестоимости для:
    - листа Excel «История цен»;
    - интерактивного графика истории цен.
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
                GROUP BY card_id
            )

            SELECT
                t.nm_id,
                COALESCE(p.title, '') AS "Наименование",

                u.date::DATE AS "Дата УПД",
                t.upd_document_id AS "ID УПД",
                COALESCE(u.number, '') AS "Номер УПД",
                COALESCE(cp.name, 'Поставщик не указан') AS "Поставщик",

                ROUND(t.upd_price_vatless, 2) AS "Цена, бух",
                ROUND(t.man_cost_per_unit, 2) AS "Цена, упр",

                COALESCE(t.upd_qty, 0) AS "Количество, шт"

            FROM inventories.upd_income t

            LEFT JOIN inventories.upd_documents u
                ON u.id = t.upd_document_id

            LEFT JOIN products p
                ON p.nm_id = t.nm_id

            LEFT JOIN pg.counterparties_counterparty cp
                ON cp.id = u.counterparty_id

            WHERE t.nm_id IS NOT NULL

            ORDER BY
                t.nm_id,
                u.date,
                t.upd_document_id
            """
        ).df()

    if df.empty:
        return df

    df["nm_id"] = df["nm_id"].astype("string")
    df["ID УПД"] = df["ID УПД"].astype("string")
    df["Номер УПД"] = df["Номер УПД"].astype("string").fillna("")
    df["Поставщик"] = df["Поставщик"].fillna("Поставщик не указан")

    return df


def get_price_analysis_period(df: pd.DataFrame) -> tuple:
    if df.empty:
        return None, None

    start = pd.to_datetime(df["Первая дата УПД"], errors="coerce").min()
    end = pd.to_datetime(df["Последняя дата УПД"], errors="coerce").max()

    return (
        start.date() if pd.notna(start) else None,
        end.date() if pd.notna(end) else None,
    )


def _history_to_text(value) -> str:
    if value is None:
        return ""

    if isinstance(value, (list, tuple)):
        return " → ".join(
            f"{float(item):,.2f}".replace(",", " ")
            for item in value
            if item is not None
        )

    return str(value)
