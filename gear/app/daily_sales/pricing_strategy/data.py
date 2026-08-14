
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

from gear.app.data.base import DashboardData
from conns import get_duckdb_conn_with_opt

from .config import HISTORY_DAYS


def normalize_date(value) -> date:
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def clean_filter(values):
    return [
        str(value).strip()
        for value in (values or [])
        if value is not None and str(value).strip()
    ]


def get_latest_stock_date(report_date: date) -> date | None:
    report_date = normalize_date(report_date)

    with get_duckdb_conn_with_opt() as con:
        row = con.execute(
            """
            SELECT MAX(date_from)::DATE
            FROM stocks.unpacked_stocks
            WHERE date_from::DATE <= ?
            """,
            [report_date],
        ).fetchone()

    return row[0] if row and row[0] else None


def _build_filter_sql(
    brand_list,
    cat_list,
):
    clauses = []
    params = []

    brand_list = clean_filter(brand_list)
    cat_list = clean_filter(cat_list)

    if brand_list:
        placeholders = ", ".join(["?"] * len(brand_list))
        clauses.append(
            "COALESCE(NULLIF(TRIM(t.brand), ''), 'Бренд не указан') "
            f"IN ({placeholders})"
        )
        params.extend(brand_list)

    if cat_list:
        placeholders = ", ".join(["?"] * len(cat_list))
        clauses.append(
            "COALESCE(NULLIF(TRIM(t.subject_name), ''), 'Категория не указана') "
            f"IN ({placeholders})"
        )
        params.extend(cat_list)

    sql = ""
    if clauses:
        sql = " AND " + " AND ".join(clauses)

    return sql, params


def get_pricing_source(
    report_date,
    cat_list=None,
    brand_list=None,
    gender_list=None,
    history_days: int = HISTORY_DAYS,
) -> dict:
    """
    Сырые данные для вкладки управления ценами.

    buyer_price:
        фактическая цена реализации WB покупателю =
        retail_amount / число положительных продаж.

    seller_price:
        наша фактическая цена по положительным продажам =
        cr_rev / число положительных продаж.

    Финансовая маржа:
        amount_vatless - adjusted_cogs_man + net_comission.

    Возвраты участвуют в финансовом результате,
    но эластичность оценивается по положительным продажам.
    """
    report_date = normalize_date(report_date)
    history_days = max(int(history_days), 30)
    history_start = report_date - timedelta(days=history_days - 1)

    stock_date = get_latest_stock_date(report_date)

    base_filter_sql, filter_params = _build_filter_sql(
        brand_list=brand_list,
        cat_list=cat_list,
    )

    gender_list = clean_filter(gender_list)

    with DashboardData() as dashboard:
        daily_sql = f"""
            WITH
            sku_map AS (
                SELECT
                    usk,
                    MAX(card_id) AS nm_id
                FROM inventories.usk
                WHERE usk IS NOT NULL
                  AND card_id IS NOT NULL
                GROUP BY usk
            ),

            product_gender AS (
                SELECT
                    nm_id,
                    COALESCE(
                        NULLIF(TRIM(MAX(gender)), ''),
                        'Пол не указан'
                    ) AS gender
                FROM cards.product
                WHERE nm_id IS NOT NULL
                GROUP BY nm_id
            ),

            commissions AS (
                SELECT
                    rrd_id,

                    COALESCE(
                        SUM(
                            val
                            / (100 + COALESCE(vat_rate, 0))
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
                            / (100 + COALESCE(vat_rate, 0))
                            * 100
                        ) FILTER (
                            WHERE field = 'comission'
                              AND oper = 'cr'
                        ),
                        0
                    ) AS net_comission

                FROM sales.sales_long
                GROUP BY rrd_id
            ),

            daily AS (
                SELECT
                    t.date_from::DATE AS date_from,
                    sm.nm_id,

                    ANY_VALUE(
                        COALESCE(
                            NULLIF(TRIM(t.brand), ''),
                            'Бренд не указан'
                        )
                    ) AS brand,

                    ANY_VALUE(
                        COALESCE(
                            NULLIF(TRIM(t.subject_name), ''),
                            'Категория не указана'
                        )
                    ) AS category,

                    ANY_VALUE(
                        COALESCE(
                            NULLIF(TRIM(t.title), ''),
                            'Без наименования'
                        )
                    ) AS title,

                    ANY_VALUE(
                        COALESCE(
                            pg.gender,
                            'Пол не указан'
                        )
                    ) AS gender,

                    SUM(
                        CASE
                            WHEN t.cr_rev > 0 THEN 1
                            ELSE 0
                        END
                    ) AS sales_qty,

                    SUM(
                        CASE
                            WHEN t.cr_rev < 0 THEN 1
                            ELSE 0
                        END
                    ) AS returns_qty,

                    SUM(
                        CASE
                            WHEN t.cr_rev > 0 THEN 1
                            WHEN t.cr_rev < 0 THEN -1
                            ELSE 0
                        END
                    ) AS net_qty,

                    SUM(
                        CASE
                            WHEN t.cr_rev > 0
                                THEN t.cr_rev
                            ELSE 0
                        END
                    ) AS seller_sales_amount,

                    SUM(
                        CASE
                            WHEN t.cr_rev > 0
                                THEN COALESCE(t.retail_amount, 0)
                            ELSE 0
                        END
                    ) AS wb_sales_amount,

                    SUM(t.cr_rev) AS amount,

                    SUM(
                        CASE
                            WHEN t.cr_rev > 0
                                THEN COALESCE(t.retail_amount, 0)
                            WHEN t.cr_rev < 0
                                THEN -ABS(COALESCE(t.retail_amount, 0))
                            ELSE 0
                        END
                    ) AS retail_amount,

                    SUM(
                        t.cr_rev
                        / (100 + COALESCE(t.vat_rate, 0))
                        * 100
                    ) AS amount_vatless,

                    SUM(
                        COALESCE(t.adjusted_cogs_man, 0)
                    ) AS cogs_man,

                    SUM(
                        COALESCE(c.net_comission, 0)
                    ) AS net_comission

                FROM base t

                INNER JOIN sku_map sm
                    ON sm.usk = t.usk

                LEFT JOIN product_gender pg
                    ON pg.nm_id = sm.nm_id

                LEFT JOIN commissions c
                    ON c.rrd_id = t.rrd_id

                WHERE
                    t.cr_rev <> 0
                    AND t.date_from::DATE
                        BETWEEN ?::DATE AND ?::DATE
                    {base_filter_sql}

                GROUP BY
                    t.date_from::DATE,
                    sm.nm_id
            )

            SELECT
                date_from,
                nm_id,
                brand,
                category,
                title,
                gender,

                sales_qty,
                returns_qty,
                net_qty,

                ROUND(
                    seller_sales_amount / 100.0,
                    2
                ) AS seller_sales_amount,

                ROUND(
                    wb_sales_amount / 100.0,
                    2
                ) AS wb_sales_amount,

                ROUND(
                    amount / 100.0,
                    2
                ) AS amount,

                ROUND(
                    retail_amount / 100.0,
                    2
                ) AS retail_amount,

                ROUND(
                    amount_vatless / 100.0,
                    2
                ) AS amount_vatless,

                ROUND(
                    cogs_man / 100.0,
                    2
                ) AS cogs_man,

                ROUND(
                    net_comission / 100.0,
                    2
                ) AS net_comission,

                ROUND(
                    (
                        amount_vatless
                        - cogs_man
                        + net_comission
                    ) / 100.0,
                    2
                ) AS margin_man,

                ROUND(
                    seller_sales_amount
                    / 100.0
                    / NULLIF(sales_qty, 0),
                    2
                ) AS seller_price,

                ROUND(
                    wb_sales_amount
                    / 100.0
                    / NULLIF(sales_qty, 0),
                    2
                ) AS buyer_price,

                ROUND(
                    CASE
                        WHEN seller_sales_amount = 0
                            THEN NULL
                        ELSE
                            (
                                wb_sales_amount
                                - seller_sales_amount
                            )
                            / seller_sales_amount
                            * 100
                    END,
                    2
                ) AS wb_price_delta_pct,

                ROUND(
                    CASE
                        WHEN amount_vatless = 0
                            THEN NULL
                        ELSE
                            (
                                amount_vatless
                                - cogs_man
                                + net_comission
                            )
                            / amount_vatless
                            * 100
                    END,
                    2
                ) AS margin_pct

            FROM daily

            ORDER BY
                nm_id,
                date_from
        """

        daily = dashboard.con.execute(
            daily_sql,
            [history_start, report_date] + filter_params,
        ).df()

        products_sql = f"""
            WITH
            sku_map AS (
                SELECT
                    usk,
                    MAX(card_id) AS nm_id
                FROM inventories.usk
                WHERE usk IS NOT NULL
                  AND card_id IS NOT NULL
                GROUP BY usk
            ),

            cards AS (
                SELECT
                    p.nm_id,

                    COALESCE(
                        NULLIF(TRIM(MAX(p.sa_name)), ''),
                        ''
                    ) AS sa_name,

                    COALESCE(
                        NULLIF(TRIM(MAX(p.title)), ''),
                        'Без наименования'
                    ) AS title,

                    COALESCE(
                        NULLIF(TRIM(MAX(p.subject_name)), ''),
                        'Категория не указана'
                    ) AS category,

                    COALESCE(
                        NULLIF(TRIM(MAX(p.gender)), ''),
                        'Пол не указан'
                    ) AS gender

                FROM cards.product p

                WHERE p.nm_id IS NOT NULL

                GROUP BY
                    p.nm_id
            ),

            brands AS (
                SELECT
                    nm_id,

                    COALESCE(
                        NULLIF(TRIM(MAX(brand)), ''),
                        'Бренд не указан'
                    ) AS brand

                FROM cards.unpacked_cards

                WHERE nm_id IS NOT NULL

                GROUP BY
                    nm_id
            ),

            current_list_price AS (
                SELECT
                    nm_id,

                    LIST(
                        val
                        ORDER BY date_from
                    )[-1] / 100.0
                        AS current_seller_list_price

                FROM sales.sales_long

                WHERE
                    field = 'retail_price'
                    AND oper = 'dt'
                    AND date_from::DATE <= ?::DATE
                    AND nm_id IS NOT NULL

                GROUP BY
                    nm_id
            ),

            latest_sale AS (
                SELECT
                    sm.nm_id,

                    LIST(
                        t.cr_rev / 100.0
                        ORDER BY t.date_from
                    ) FILTER (
                        WHERE t.cr_rev > 0
                    )[-1]
                        AS latest_seller_realized_price,

                    LIST(
                        COALESCE(t.retail_amount, 0) / 100.0
                        ORDER BY t.date_from
                    ) FILTER (
                        WHERE
                            t.cr_rev > 0
                            AND COALESCE(t.retail_amount, 0) > 0
                    )[-1]
                        AS latest_buyer_price

                FROM base t

                INNER JOIN sku_map sm
                    ON sm.usk = t.usk

                WHERE
                    t.date_from::DATE <= ?::DATE
                    AND t.cr_rev > 0
                    {base_filter_sql}

                GROUP BY
                    sm.nm_id
            )

            SELECT
                c.nm_id,
                c.sa_name,
                c.title,
                COALESCE(
                    b.brand,
                    'Бренд не указан'
                ) AS brand,
                c.category,
                c.gender,

                COALESCE(
                    clp.current_seller_list_price,
                    0
                ) AS current_seller_list_price,

                COALESCE(
                    ls.latest_seller_realized_price,
                    0
                ) AS latest_seller_realized_price,

                COALESCE(
                    ls.latest_buyer_price,
                    0
                ) AS latest_buyer_price

            FROM cards c

            LEFT JOIN brands b
                ON b.nm_id = c.nm_id

            LEFT JOIN current_list_price clp
                ON clp.nm_id = c.nm_id

            LEFT JOIN latest_sale ls
                ON ls.nm_id = c.nm_id

            WHERE
                (
                    COALESCE(
                        clp.current_seller_list_price,
                        0
                    ) > 0
                    OR
                    COALESCE(
                        ls.latest_seller_realized_price,
                        0
                    ) > 0
                )
        """

        products = dashboard.con.execute(
            products_sql,
            [report_date, report_date] + filter_params,
        ).df()

    if gender_list and not products.empty:
        products = products[
            products["gender"]
            .astype(str)
            .isin(gender_list)
        ].copy()

    if not products.empty:
        allowed_nm = set(
            products["nm_id"].tolist()
        )

        daily = daily[
            daily["nm_id"].isin(
                allowed_nm
            )
        ].copy()

    stocks = pd.DataFrame()

    if stock_date:
        with get_duckdb_conn_with_opt() as con:
            stocks = con.execute(
                """
                SELECT
                    nm_id,

                    SUM(
                        COALESCE(quantity, 0)
                    ) AS stock_on_hand,

                    SUM(
                        COALESCE(in_way_from_client, 0)
                        +
                        COALESCE(in_way_to_client, 0)
                    ) AS stock_in_transit,

                    SUM(
                        COALESCE(quantity, 0)
                        +
                        COALESCE(in_way_from_client, 0)
                        +
                        COALESCE(in_way_to_client, 0)
                    ) AS stock_total

                FROM stocks.unpacked_stocks

                WHERE
                    date_from::DATE = ?
                    AND nm_id IS NOT NULL

                GROUP BY
                    nm_id
                """,
                [stock_date],
            ).df()

    with get_duckdb_conn_with_opt() as con:
        income = con.execute(
            """
            SELECT
                ui.nm_id,
                MAX(ud.date)::DATE
                    AS last_income_date

            FROM inventories.upd_income ui

            INNER JOIN inventories.upd_documents ud
                ON ud.id = ui.upd_document_id

            WHERE
                ui.nm_id IS NOT NULL
                AND ud.date::DATE <= ?

            GROUP BY
                ui.nm_id
            """,
            [report_date],
        ).df()

    if not products.empty:
        if not stocks.empty:
            products = products.merge(
                stocks,
                on="nm_id",
                how="left",
            )
        else:
            products["stock_on_hand"] = 0
            products["stock_in_transit"] = 0
            products["stock_total"] = 0

        if not income.empty:
            products = products.merge(
                income,
                on="nm_id",
                how="left",
            )
        else:
            products["last_income_date"] = None

        for column in (
            "stock_on_hand",
            "stock_in_transit",
            "stock_total",
        ):
            products[column] = (
                pd.to_numeric(
                    products[column],
                    errors="coerce",
                )
                .fillna(0)
            )

    return {
        "report_date": report_date,
        "history_start": history_start,
        "stock_date": stock_date,
        "products": products,
        "daily": daily,
    }
