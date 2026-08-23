# gear/app/daily_sales/pricing_strategy/data.py

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

from conns import get_duckdb_conn_with_opt
from gear.app.data.base import DashboardData

from .config import HISTORY_DAYS


def normalize_date(value) -> date:
    if isinstance(value, date):
        return value

    return date.fromisoformat(
        str(value)[:10]
    )


def clean_filter(values):
    return [
        str(value).strip()
        for value in (values or [])
        if (
            value is not None
            and str(value).strip()
        )
    ]


# ============================================================
# ПОСЛЕДНИЕ ДОСТУПНЫЕ ДАТЫ ОСТАТКОВ
# ============================================================

def get_latest_stock_dates(
    report_date,
) -> dict:
    """
    Последняя доступная дата отдельно
    для WB и FBS.

    Если на дату анализа снимка нет,
    берём последний существующий
    снимок <= report_date.
    """

    report_date = normalize_date(
        report_date
    )

    with get_duckdb_conn_with_opt() as con:

        wb = con.execute(
            """
            SELECT
                MAX(date_from)::DATE

            FROM stocks.unpacked_stocks

            WHERE
                date_from::DATE <= ?
            """,
            [report_date],
        ).fetchone()

        fbs = con.execute(
            """
            SELECT
                MAX(date_from)::DATE

            FROM stocks.unpacked_fbs_stocks

            WHERE
                date_from::DATE <= ?
            """,
            [report_date],
        ).fetchone()

    return {
        "wb_date": (
            wb[0]
            if wb and wb[0]
            else None
        ),
        "fbs_date": (
            fbs[0]
            if fbs and fbs[0]
            else None
        ),
    }


# ============================================================
# ФИЛЬТРЫ
# ============================================================

def _filter_sql(
    brand_list,
    cat_list,
    gender_list,
):
    clauses = []
    params = []

    for column, values in (
        (
            "COALESCE("
            "b.brand, "
            "'Бренд не указан'"
            ")",
            clean_filter(
                brand_list
            ),
        ),
        (
            "COALESCE("
            "p.category, "
            "'Категория не указана'"
            ")",
            clean_filter(
                cat_list
            ),
        ),
        (
            "COALESCE("
            "p.gender, "
            "'Пол не указан'"
            ")",
            clean_filter(
                gender_list
            ),
        ),
    ):

        if not values:
            continue

        placeholders = ", ".join(
            ["?"] * len(values)
        )

        clauses.append(
            f"{column} "
            f"IN ({placeholders})"
        )

        params.extend(
            values
        )

    sql = ""

    if clauses:
        sql = (
            " AND "
            + " AND ".join(
                clauses
            )
        )

    return sql, params


# ============================================================
# ТОВАРНЫЙ UNIVERSE
#
# ВАЖНО:
#
# ВСЕГО ОСТАТОК =
#
# WB quantity
# + FBS quantity
# + WB inWayToClient
# + WB inWayFromClient
#
# Если total_stock > 0,
# товар участвует в ценовом анализе.
# ============================================================

def get_stock_products(
    report_date,
    brand_list=None,
    cat_list=None,
    gender_list=None,
):
    report_date = normalize_date(
        report_date
    )

    dates = get_latest_stock_dates(
        report_date
    )

    wb_date = dates[
        "wb_date"
    ]

    fbs_date = dates[
        "fbs_date"
    ]

    filter_sql, filter_params = (
        _filter_sql(
            brand_list,
            cat_list,
            gender_list,
        )
    )

    with get_duckdb_conn_with_opt() as con:

        frame = con.execute(
            f"""
            WITH

            -- ====================================================
            -- WB ОСТАТКИ
            -- ====================================================

            wb AS (
                SELECT
                    nm_id,

                    SUM(
                        COALESCE(
                            quantity,
                            0
                        )
                    ) AS wb_stock,

                    SUM(
                        COALESCE(
                            in_way_to_client,
                            0
                        )
                    ) AS in_way_to_client,

                    SUM(
                        COALESCE(
                            in_way_from_client,
                            0
                        )
                    ) AS in_way_from_client

                FROM stocks.unpacked_stocks

                WHERE
                    ?::DATE IS NOT NULL

                    AND date_from::DATE
                        = ?::DATE

                    AND nm_id IS NOT NULL

                GROUP BY
                    nm_id
            ),


            -- ====================================================
            -- FBS ОСТАТКИ
            -- ====================================================

            fbs AS (
                SELECT
                    nm_id,

                    SUM(
                        COALESCE(
                            quantity,
                            0
                        )
                    ) AS fbs_stock

                FROM stocks.unpacked_fbs_stocks

                WHERE
                    ?::DATE IS NOT NULL

                    AND date_from::DATE
                        = ?::DATE

                    AND nm_id IS NOT NULL

                GROUP BY
                    nm_id
            ),


            -- ====================================================
            -- ОБЪЕДИНЁННЫЙ ОСТАТОК
            -- ====================================================

            stocks AS (
                SELECT
                    COALESCE(
                        wb.nm_id,
                        fbs.nm_id
                    ) AS nm_id,

                    -- ------------------------------
                    -- физически WB
                    -- ------------------------------

                    COALESCE(
                        wb.wb_stock,
                        0
                    ) AS wb_stock,

                    -- ------------------------------
                    -- физически FBS
                    -- ------------------------------

                    COALESCE(
                        fbs.fbs_stock,
                        0
                    ) AS fbs_stock,

                    -- ------------------------------
                    -- в пути к клиенту
                    -- ------------------------------

                    COALESCE(
                        wb.in_way_to_client,
                        0
                    ) AS in_way_to_client,

                    -- ------------------------------
                    -- в пути от клиента
                    -- ------------------------------

                    COALESCE(
                        wb.in_way_from_client,
                        0
                    ) AS in_way_from_client,

                    -- ------------------------------
                    -- весь путь
                    -- ------------------------------

                    (
                        COALESCE(
                            wb.in_way_to_client,
                            0
                        )
                        +
                        COALESCE(
                            wb.in_way_from_client,
                            0
                        )
                    ) AS in_transit,

                    -- ------------------------------
                    -- физический остаток
                    -- WB + FBS
                    -- ------------------------------

                    (
                        COALESCE(
                            wb.wb_stock,
                            0
                        )
                        +
                        COALESCE(
                            fbs.fbs_stock,
                            0
                        )
                    ) AS physical_stock,

                    -- ------------------------------
                    -- ВСЕГО
                    --
                    -- WB
                    -- + FBS
                    -- + к клиенту
                    -- + от клиента
                    -- ------------------------------

                    (
                        COALESCE(
                            wb.wb_stock,
                            0
                        )
                        +
                        COALESCE(
                            fbs.fbs_stock,
                            0
                        )
                        +
                        COALESCE(
                            wb.in_way_to_client,
                            0
                        )
                        +
                        COALESCE(
                            wb.in_way_from_client,
                            0
                        )
                    ) AS total_stock

                FROM wb

                FULL OUTER JOIN fbs
                    ON fbs.nm_id
                        = wb.nm_id
            ),


            -- ====================================================
            -- КАРТОЧКИ
            -- ====================================================

            products AS (
                SELECT
                    nm_id,

                    COALESCE(
                        NULLIF(
                            TRIM(
                                MAX(sa_name)
                            ),
                            ''
                        ),
                        ''
                    ) AS sa_name,

                    COALESCE(
                        NULLIF(
                            TRIM(
                                MAX(title)
                            ),
                            ''
                        ),
                        'Без наименования'
                    ) AS title,

                    COALESCE(
                        NULLIF(
                            TRIM(
                                MAX(subject_name)
                            ),
                            ''
                        ),
                        'Категория не указана'
                    ) AS category,

                    COALESCE(
                        NULLIF(
                            TRIM(
                                MAX(gender)
                            ),
                            ''
                        ),
                        'Пол не указан'
                    ) AS gender

                FROM cards.product

                WHERE
                    nm_id IS NOT NULL

                GROUP BY
                    nm_id
            ),


            -- ====================================================
            -- БРЕНД
            -- ====================================================

            brands AS (
                SELECT
                    nm_id,

                    COALESCE(
                        NULLIF(
                            TRIM(
                                MAX(brand)
                            ),
                            ''
                        ),
                        'Бренд не указан'
                    ) AS brand

                FROM cards.unpacked_cards

                WHERE
                    nm_id IS NOT NULL

                GROUP BY
                    nm_id
            ),


            -- ====================================================
            -- ТЕКУЩАЯ НАША ЦЕНА
            -- ====================================================

            prices AS (
                SELECT
                    nm_id,

                    LIST(
                        val
                        ORDER BY date_from
                    )[-1]
                    / 100.0
                        AS current_seller_list_price

                FROM sales.sales_long

                WHERE
                    field = 'retail_price'

                    AND oper = 'dt'

                    AND date_from::DATE
                        <= ?::DATE

                    AND nm_id IS NOT NULL

                GROUP BY
                    nm_id
            ),


            -- ====================================================
            -- NM ID -> USK
            -- ====================================================

            nm_usk AS (
                SELECT
                    card_id AS nm_id,
                    usk

                FROM inventories.usk

                WHERE
                    card_id IS NOT NULL
                    AND usk IS NOT NULL

                GROUP BY
                    card_id,
                    usk
            ),


            -- ====================================================
            -- ПОСЛЕДНЯЯ УПРАВЛЕНЧЕСКАЯ СЕБЕСТОИМОСТЬ
            -- ====================================================

            costs AS (
                SELECT
                    nu.nm_id,

                    MAX(
                        w.adjust_man_wo[-1]
                    )
                    / 100.0
                        AS last_man_cost

                FROM nm_usk nu

                LEFT JOIN inventories.pre_wo w
                    ON w.usk = nu.usk

                GROUP BY
                    nu.nm_id
            ),


            -- ====================================================
            -- ПОСЛЕДНИЙ ПРИХОД
            -- ====================================================

            income AS (
                SELECT
                    ui.nm_id,

                    MAX(
                        ud.date
                    )::DATE
                        AS last_income_date

                FROM inventories.upd_income ui

                INNER JOIN inventories.upd_documents ud
                    ON ud.id
                        = ui.upd_document_id

                WHERE
                    ui.nm_id IS NOT NULL

                    AND ud.date::DATE
                        <= ?::DATE

                GROUP BY
                    ui.nm_id
            )


            -- ====================================================
            -- RESULT
            -- ====================================================

            SELECT
                s.nm_id,

                COALESCE(
                    b.brand,
                    'Бренд не указан'
                ) AS brand,

                COALESCE(
                    p.category,
                    'Категория не указана'
                ) AS category,

                COALESCE(
                    p.gender,
                    'Пол не указан'
                ) AS gender,

                COALESCE(
                    p.sa_name,
                    ''
                ) AS sa_name,

                COALESCE(
                    p.title,
                    'Без наименования'
                ) AS title,

                -- ================================================
                -- ОСТАТКИ
                -- ================================================

                s.wb_stock,

                s.fbs_stock,

                s.in_way_to_client,

                s.in_way_from_client,

                s.in_transit,

                s.physical_stock,

                s.total_stock,

                -- ================================================
                -- ЦЕНА / СЕБЕСТОИМОСТЬ
                -- ================================================

                COALESCE(
                    pr.current_seller_list_price,
                    0
                ) AS current_seller_list_price,

                COALESCE(
                    c.last_man_cost,
                    0
                ) AS last_man_cost,

                i.last_income_date

            FROM stocks s

            LEFT JOIN products p
                ON p.nm_id = s.nm_id

            LEFT JOIN brands b
                ON b.nm_id = s.nm_id

            LEFT JOIN prices pr
                ON pr.nm_id = s.nm_id

            LEFT JOIN costs c
                ON c.nm_id = s.nm_id

            LEFT JOIN income i
                ON i.nm_id = s.nm_id

            WHERE
                -- ================================================
                -- ГЛАВНОЕ:
                --
                -- анализируем ВСЁ,
                -- что есть:
                --
                -- WB
                -- + FBS
                -- + в пути к клиенту
                -- + в пути от клиента
                -- ================================================

                s.total_stock > 0

                {filter_sql}

            ORDER BY
                s.total_stock DESC,
                brand,
                category,
                title
            """,
            [
                wb_date,
                wb_date,

                fbs_date,
                fbs_date,

                report_date,

                report_date,
            ]
            + filter_params,
        ).df()

    return (
        frame,
        dates,
    )


# ============================================================
# ПРОДАЖИ / ЦЕНЫ / МАРЖА
# ============================================================

def get_pricing_source(
    report_date,
    cat_list=None,
    brand_list=None,
    gender_list=None,
    history_days=HISTORY_DAYS,
) -> dict:

    report_date = normalize_date(
        report_date
    )

    history_days = max(
        int(history_days),
        30,
    )

    history_start = (
        report_date
        - timedelta(
            days=history_days - 1
        )
    )

    # ========================================================
    # UNIVERSE = ТОВАРЫ С ЛЮБЫМ ОСТАТКОМ
    # ========================================================

    products, dates = (
        get_stock_products(
            report_date=report_date,
            brand_list=brand_list,
            cat_list=cat_list,
            gender_list=gender_list,
        )
    )

    if products.empty:
        return {
            "report_date": report_date,
            "history_start": history_start,
            **dates,
            "products": products,
            "daily": pd.DataFrame(),
        }

    universe = (
        products[
            ["nm_id"]
        ]
        .drop_duplicates()
        .reset_index(
            drop=True
        )
    )

    # ========================================================
    # ИСТОРИЯ ПРОДАЖ
    # ========================================================

    with DashboardData() as dashboard:

        dashboard.con.register(
            "pricing_nm_universe",
            universe,
        )

        daily = (
            dashboard
            .con
            .execute(
                """
                WITH

                sku_map AS (
                    SELECT
                        usk,

                        MAX(
                            card_id
                        ) AS nm_id

                    FROM inventories.usk

                    WHERE
                        usk IS NOT NULL
                        AND card_id IS NOT NULL

                    GROUP BY
                        usk
                ),


                commissions AS (
                    SELECT
                        rrd_id,

                        COALESCE(
                            SUM(
                                val
                                / (
                                    100
                                    + COALESCE(
                                        vat_rate,
                                        0
                                    )
                                )
                                * 100
                            )
                            FILTER (
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
                                    + COALESCE(
                                        vat_rate,
                                        0
                                    )
                                )
                                * 100
                            )
                            FILTER (
                                WHERE
                                    field = 'comission'
                                    AND oper = 'cr'
                            ),
                            0
                        ) AS net_comission

                    FROM sales.sales_long

                    GROUP BY
                        rrd_id
                ),


                daily AS (
                    SELECT
                        t.date_from::DATE
                            AS date_from,

                        sm.nm_id,

                        -- ========================================
                        -- ПРОДАЖИ
                        -- ========================================

                        SUM(
                            CASE
                                WHEN t.cr_rev > 0
                                    THEN 1
                                ELSE 0
                            END
                        ) AS sales_qty,

                        -- ========================================
                        -- ВОЗВРАТЫ
                        -- ========================================

                        SUM(
                            CASE
                                WHEN t.cr_rev < 0
                                    THEN 1
                                ELSE 0
                            END
                        ) AS returns_qty,

                        -- ========================================
                        -- NET QTY
                        -- ========================================

                        SUM(
                            CASE
                                WHEN t.cr_rev > 0
                                    THEN 1

                                WHEN t.cr_rev < 0
                                    THEN -1

                                ELSE 0
                            END
                        ) AS net_qty,

                        -- ========================================
                        -- НАША ВЫРУЧКА ПО ПРОДАЖАМ
                        -- ========================================

                        SUM(
                            CASE
                                WHEN t.cr_rev > 0
                                    THEN t.cr_rev
                                ELSE 0
                            END
                        ) AS seller_sales_amount,

                        -- ========================================
                        -- РЕАЛИЗАЦИЯ WB ПОКУПАТЕЛЮ
                        -- ========================================

                        SUM(
                            CASE
                                WHEN t.cr_rev > 0
                                    THEN COALESCE(
                                        t.retail_amount,
                                        0
                                    )
                                ELSE 0
                            END
                        ) AS wb_sales_amount,

                        -- ========================================
                        -- NET ВЫРУЧКА
                        -- ========================================

                        SUM(
                            t.cr_rev
                        ) AS amount,

                        -- ========================================
                        -- БЕЗ НДС
                        -- ========================================

                        SUM(
                            t.cr_rev
                            / (
                                100
                                + COALESCE(
                                    t.vat_rate,
                                    0
                                )
                            )
                            * 100
                        ) AS amount_vatless,

                        -- ========================================
                        -- FIFO УПР. СЕБЕСТОИМОСТЬ
                        -- ========================================

                        SUM(
                            COALESCE(
                                t.adjusted_cogs_man,
                                0
                            )
                        ) AS cogs_man,

                        -- ========================================
                        -- КОМИССИЯ WB
                        -- ========================================

                        SUM(
                            COALESCE(
                                c.net_comission,
                                0
                            )
                        ) AS net_comission

                    FROM base t

                    INNER JOIN sku_map sm
                        ON sm.usk = t.usk

                    INNER JOIN pricing_nm_universe u
                        ON u.nm_id = sm.nm_id

                    LEFT JOIN commissions c
                        ON c.rrd_id = t.rrd_id

                    WHERE
                        t.cr_rev <> 0

                        AND t.date_from::DATE
                            BETWEEN ?::DATE
                            AND ?::DATE

                    GROUP BY
                        t.date_from::DATE,
                        sm.nm_id
                )


                SELECT
                    date_from,

                    nm_id,

                    sales_qty,

                    returns_qty,

                    net_qty,

                    ROUND(
                        seller_sales_amount
                        / 100.0,
                        2
                    ) AS seller_sales_amount,

                    ROUND(
                        wb_sales_amount
                        / 100.0,
                        2
                    ) AS wb_sales_amount,

                    ROUND(
                        amount
                        / 100.0,
                        2
                    ) AS amount,

                    ROUND(
                        amount_vatless
                        / 100.0,
                        2
                    ) AS amount_vatless,

                    ROUND(
                        cogs_man
                        / 100.0,
                        2
                    ) AS cogs_man,

                    ROUND(
                        net_comission
                        / 100.0,
                        2
                    ) AS net_comission,

                    ROUND(
                        (
                            amount_vatless
                            - cogs_man
                            + net_comission
                        )
                        / 100.0,
                        2
                    ) AS margin_man,

                    ROUND(
                        seller_sales_amount
                        / 100.0
                        / NULLIF(
                            sales_qty,
                            0
                        ),
                        2
                    ) AS seller_price,

                    ROUND(
                        wb_sales_amount
                        / 100.0
                        / NULLIF(
                            sales_qty,
                            0
                        ),
                        2
                    ) AS buyer_price

                FROM daily

                ORDER BY
                    nm_id,
                    date_from
                """,
                [
                    history_start,
                    report_date,
                ],
            )
            .df()
        )

        try:
            dashboard.con.unregister(
                "pricing_nm_universe"
            )
        except Exception:
            pass

    return {
        "report_date": report_date,

        "history_start": (
            history_start
        ),

        **dates,

        "products": products,

        "daily": daily,
    }