# gear/app/daily_sales/daily_brief/data/stock_balance.py

from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd

from conns import get_duckdb_conn_with_opt

from gear.app.daily_sales.stocks.dashboard_data import (
    get_effective_stock_date,
)

from gear.app.daily_sales.stocks.data import (
    get_stocks_summary_stats,
)

from ..helpers import (
    dataframe_records,
    number,
)


SALES_WINDOW_DAYS = 30

#: Товар моложе этого возраста (считая от первого дня, когда
#: по нему вообще видели остаток на складе) не считается
#: залежавшимся, даже если ещё ни разу не продавался -- ему
#: могло не хватить времени дойти до покупателя. Используется
#: только чтобы РАЗДЕЛИТЬ зону риска на "новое" и "старое":
#: сама зона риска (90+ дней покрытия или отсутствие продаж)
#: считается как считалась.
NEW_ARRIVAL_WINDOW_DAYS = 30


# =============================================================================
# ОБЩИЕ ФУНКЦИИ
# =============================================================================


def _pct(
    value,
    total,
) -> float:
    value = number(value)
    total = number(total)

    if total <= 0:
        return 0.0

    return (
        value
        / total
        * 100
    )


# =============================================================================
# СТРУКТУРА ЗАПАСА ПО БРЕНДАМ
#
# WB + FBS + путь
# =============================================================================


def _get_brand_stock_structure(
    report_date: str,
) -> pd.DataFrame:

    with get_duckdb_conn_with_opt() as con:
        df = con.execute(
            """
            WITH

            /*
            ================================================================
            WB
            ================================================================
            */

            wb AS (
                SELECT
                    nm_id,

                    SUM(
                        COALESCE(
                            quantity,
                            0
                        )
                    ) AS wb_qty,

                    SUM(
                        COALESCE(
                            in_way_to_client,
                            0
                        )
                        +
                        COALESCE(
                            in_way_from_client,
                            0
                        )
                    ) AS transit_qty

                FROM stocks.unpacked_stocks

                WHERE
                    date_from::DATE
                        = $report_date::DATE

                    AND nm_id IS NOT NULL

                GROUP BY
                    nm_id
            ),


            /*
            ================================================================
            FBS
            ================================================================
            */

            fbs AS (
                SELECT
                    nm_id,

                    SUM(
                        COALESCE(
                            quantity,
                            0
                        )
                    ) AS fbs_qty

                FROM stocks.unpacked_fbs_stocks

                WHERE
                    date_from::DATE
                        = $report_date::DATE

                    AND nm_id IS NOT NULL

                GROUP BY
                    nm_id
            ),


            /*
            ================================================================
            ЕДИНЫЙ ТОВАРНЫЙ КОНТУР
            ================================================================
            */

            stock AS (
                SELECT
                    COALESCE(
                        wb.nm_id,
                        fbs.nm_id
                    ) AS nm_id,

                    COALESCE(
                        wb.wb_qty,
                        0
                    ) AS wb_qty,

                    COALESCE(
                        fbs.fbs_qty,
                        0
                    ) AS fbs_qty,

                    COALESCE(
                        wb.transit_qty,
                        0
                    ) AS transit_qty

                FROM wb

                FULL OUTER JOIN fbs
                    ON wb.nm_id = fbs.nm_id
            ),


            /*
            ================================================================
            БРЕНД
            ================================================================
            */

            brands AS (
                SELECT
                    nm_id,

                    COALESCE(
                        MAX(brand),
                        'Бренд не указан'
                    ) AS brand

                FROM cards.unpacked_cards

                GROUP BY
                    nm_id
            )


            SELECT
                COALESCE(
                    b.brand,
                    'Бренд не указан'
                ) AS brand,

                SUM(
                    s.wb_qty
                ) AS wb_qty,

                SUM(
                    s.fbs_qty
                ) AS fbs_qty,

                SUM(
                    s.transit_qty
                ) AS transit_qty,

                SUM(
                    s.wb_qty
                    +
                    s.fbs_qty
                    +
                    s.transit_qty
                ) AS total_qty,

                COUNT(
                    DISTINCT CASE
                        WHEN (
                            s.wb_qty
                            +
                            s.fbs_qty
                            +
                            s.transit_qty
                        ) > 0
                        THEN s.nm_id
                    END
                ) AS products

            FROM stock s

            LEFT JOIN brands b
                ON b.nm_id = s.nm_id

            WHERE
                (
                    s.wb_qty
                    +
                    s.fbs_qty
                    +
                    s.transit_qty
                ) > 0

            GROUP BY
                COALESCE(
                    b.brand,
                    'Бренд не указан'
                )

            ORDER BY
                total_qty DESC,
                brand
            """,
            {
                "report_date": report_date,
            },
        ).df()

    if df.empty:
        return df

    numeric_columns = [
        "wb_qty",
        "fbs_qty",
        "transit_qty",
        "total_qty",
        "products",
    ]

    for column in numeric_columns:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce",
        ).fillna(0)

    total = number(
        df["total_qty"].sum()
    )

    if total > 0:
        df["share_pct"] = (
            df["total_qty"]
            / total
            * 100
        )
    else:
        df["share_pct"] = 0.0

    safe_total = (
        df["total_qty"]
        .replace(
            0,
            pd.NA,
        )
    )

    df["wb_share_inside"] = (
        df["wb_qty"]
        / safe_total
        * 100
    ).fillna(0)

    df["fbs_share_inside"] = (
        df["fbs_qty"]
        / safe_total
        * 100
    ).fillna(0)

    df["transit_share_inside"] = (
        df["transit_qty"]
        / safe_total
        * 100
    ).fillna(0)

    return df


# =============================================================================
# КАТЕГОРИИ -- ВЕСЬ ТОВАРНЫЙ КОНТУР
# =============================================================================
#
# То же самое, что _get_brand_stock_structure, но в разрезе
# категории, а не бренда. Нужна отдельно от _get_fbs_categories:
# та считает только собственный склад, а здесь -- весь контур
# (WB + FBS + путь), как и в разрезе по брендам.


def _get_category_stock_structure(
    report_date: str,
) -> pd.DataFrame:

    with get_duckdb_conn_with_opt() as con:
        df = con.execute(
            """
            WITH

            wb AS (
                SELECT
                    nm_id,

                    SUM(
                        COALESCE(
                            quantity,
                            0
                        )
                    ) AS wb_qty,

                    SUM(
                        COALESCE(
                            in_way_to_client,
                            0
                        )
                        +
                        COALESCE(
                            in_way_from_client,
                            0
                        )
                    ) AS transit_qty

                FROM stocks.unpacked_stocks

                WHERE
                    date_from::DATE
                        = $report_date::DATE

                    AND nm_id IS NOT NULL

                GROUP BY
                    nm_id
            ),

            fbs AS (
                SELECT
                    nm_id,

                    SUM(
                        COALESCE(
                            quantity,
                            0
                        )
                    ) AS fbs_qty

                FROM stocks.unpacked_fbs_stocks

                WHERE
                    date_from::DATE
                        = $report_date::DATE

                    AND nm_id IS NOT NULL

                GROUP BY
                    nm_id
            ),

            stock AS (
                SELECT
                    COALESCE(
                        wb.nm_id,
                        fbs.nm_id
                    ) AS nm_id,

                    COALESCE(
                        wb.wb_qty,
                        0
                    ) AS wb_qty,

                    COALESCE(
                        fbs.fbs_qty,
                        0
                    ) AS fbs_qty,

                    COALESCE(
                        wb.transit_qty,
                        0
                    ) AS transit_qty

                FROM wb

                FULL OUTER JOIN fbs
                    ON wb.nm_id = fbs.nm_id
            ),

            products AS (
                SELECT
                    nm_id,

                    COALESCE(
                        MAX(subject_name),
                        'Категория не указана'
                    ) AS category

                FROM cards.product

                GROUP BY
                    nm_id
            )

            SELECT
                COALESCE(
                    p.category,
                    'Категория не указана'
                ) AS category,

                SUM(
                    s.wb_qty
                ) AS wb_qty,

                SUM(
                    s.fbs_qty
                ) AS fbs_qty,

                SUM(
                    s.transit_qty
                ) AS transit_qty,

                SUM(
                    s.wb_qty
                    +
                    s.fbs_qty
                    +
                    s.transit_qty
                ) AS total_qty,

                COUNT(
                    DISTINCT CASE
                        WHEN (
                            s.wb_qty
                            +
                            s.fbs_qty
                            +
                            s.transit_qty
                        ) > 0
                        THEN s.nm_id
                    END
                ) AS products

            FROM stock s

            LEFT JOIN products p
                ON p.nm_id = s.nm_id

            WHERE
                (
                    s.wb_qty
                    +
                    s.fbs_qty
                    +
                    s.transit_qty
                ) > 0

            GROUP BY
                COALESCE(
                    p.category,
                    'Категория не указана'
                )

            ORDER BY
                total_qty DESC,
                category
            """,
            {
                "report_date": report_date,
            },
        ).df()

    if df.empty:
        return df

    numeric_columns = [
        "wb_qty",
        "fbs_qty",
        "transit_qty",
        "total_qty",
        "products",
    ]

    for column in numeric_columns:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce",
        ).fillna(0)

    total = number(
        df["total_qty"].sum()
    )

    df["share_pct"] = (
        df["total_qty"] / total * 100
        if total > 0
        else 0.0
    )

    return df


# =============================================================================
# FBS — КАТЕГОРИИ
# =============================================================================


def _get_fbs_categories(
    report_date: str,
) -> pd.DataFrame:

    with get_duckdb_conn_with_opt() as con:
        df = con.execute(
            """
            WITH

            fbs AS (
                SELECT
                    nm_id,

                    SUM(
                        COALESCE(
                            quantity,
                            0
                        )
                    ) AS fbs_qty

                FROM stocks.unpacked_fbs_stocks

                WHERE
                    date_from::DATE
                        = $report_date::DATE

                    AND nm_id IS NOT NULL

                GROUP BY
                    nm_id
            ),


            products AS (
                SELECT
                    nm_id,

                    COALESCE(
                        MAX(subject_name),
                        'Категория не указана'
                    ) AS category

                FROM cards.product

                GROUP BY
                    nm_id
            )


            SELECT
                COALESCE(
                    p.category,
                    'Категория не указана'
                ) AS category,

                SUM(
                    f.fbs_qty
                ) AS fbs_qty,

                COUNT(
                    DISTINCT CASE
                        WHEN f.fbs_qty > 0
                        THEN f.nm_id
                    END
                ) AS products

            FROM fbs f

            LEFT JOIN products p
                ON p.nm_id = f.nm_id

            WHERE
                f.fbs_qty > 0

            GROUP BY
                COALESCE(
                    p.category,
                    'Категория не указана'
                )

            ORDER BY
                fbs_qty DESC,
                category
            """,
            {
                "report_date": report_date,
            },
        ).df()

    if df.empty:
        return df

    df["fbs_qty"] = pd.to_numeric(
        df["fbs_qty"],
        errors="coerce",
    ).fillna(0)

    df["products"] = pd.to_numeric(
        df["products"],
        errors="coerce",
    ).fillna(0)

    total = number(
        df["fbs_qty"].sum()
    )

    if total > 0:
        df["share_pct"] = (
            df["fbs_qty"]
            / total
            * 100
        )
    else:
        df["share_pct"] = 0.0

    return df


# =============================================================================
# FBS — ДОПОЛНИТЕЛЬНЫЕ ПОКАЗАТЕЛИ
# =============================================================================


def _get_fbs_stats(
    report_date: str,
) -> dict:

    with get_duckdb_conn_with_opt() as con:
        row = con.execute(
            """
            WITH

            wb AS (
                SELECT
                    nm_id,

                    SUM(
                        COALESCE(
                            quantity,
                            0
                        )
                    ) AS wb_qty,

                    SUM(
                        COALESCE(
                            in_way_to_client,
                            0
                        )
                        +
                        COALESCE(
                            in_way_from_client,
                            0
                        )
                    ) AS transit_qty

                FROM stocks.unpacked_stocks

                WHERE
                    date_from::DATE
                        = $report_date::DATE

                    AND nm_id IS NOT NULL

                GROUP BY
                    nm_id
            ),


            fbs AS (
                SELECT
                    nm_id,

                    SUM(
                        COALESCE(
                            quantity,
                            0
                        )
                    ) AS fbs_qty

                FROM stocks.unpacked_fbs_stocks

                WHERE
                    date_from::DATE
                        = $report_date::DATE

                    AND nm_id IS NOT NULL

                GROUP BY
                    nm_id
            ),


            stock AS (
                SELECT
                    COALESCE(
                        wb.nm_id,
                        fbs.nm_id
                    ) AS nm_id,

                    COALESCE(
                        wb.wb_qty,
                        0
                    ) AS wb_qty,

                    COALESCE(
                        wb.transit_qty,
                        0
                    ) AS transit_qty,

                    COALESCE(
                        fbs.fbs_qty,
                        0
                    ) AS fbs_qty

                FROM wb

                FULL OUTER JOIN fbs
                    ON wb.nm_id = fbs.nm_id
            )


            SELECT
                COUNT(
                    DISTINCT CASE
                        WHEN fbs_qty > 0
                        THEN nm_id
                    END
                ) AS fbs_products,

                COUNT(
                    DISTINCT CASE
                        WHEN
                            fbs_qty > 0
                            AND wb_qty <= 0
                            AND transit_qty <= 0
                        THEN nm_id
                    END
                ) AS fbs_only_products,

                SUM(
                    CASE
                        WHEN
                            fbs_qty > 0
                            AND wb_qty <= 0
                            AND transit_qty <= 0
                        THEN fbs_qty

                        ELSE 0
                    END
                ) AS fbs_only_qty

            FROM stock
            """,
            {
                "report_date": report_date,
            },
        ).fetchone()

    return {
        "fbs_products": int(
            number(
                row[0]
                if row
                else 0
            )
        ),
        "fbs_only_products": int(
            number(
                row[1]
                if row
                else 0
            )
        ),
        "fbs_only_qty": number(
            row[2]
            if row
            else 0
        ),
    }


# =============================================================================
# СТОИМОСТЬ ВСЕГО ТОВАРНОГО КОНТУРА
#
# ВАЖНО:
# WB + FBS + товар в пути
#
# То есть здесь больше НЕТ старой проблемы,
# когда стоимость считалась только по WB.
# =============================================================================


def _get_full_stock_costs(
    report_date: str,
) -> dict:

    with get_duckdb_conn_with_opt() as con:
        row = con.execute(
            """
            WITH

            /*
            ================================================================
            WB
            ================================================================
            */

            wb AS (
                SELECT
                    nm_id,

                    SUM(
                        COALESCE(
                            quantity,
                            0
                        )
                        +
                        COALESCE(
                            in_way_to_client,
                            0
                        )
                        +
                        COALESCE(
                            in_way_from_client,
                            0
                        )
                    ) AS qty

                FROM stocks.unpacked_stocks

                WHERE
                    date_from::DATE
                        = $report_date::DATE

                    AND nm_id IS NOT NULL

                GROUP BY
                    nm_id
            ),


            /*
            ================================================================
            FBS
            ================================================================
            */

            fbs AS (
                SELECT
                    nm_id,

                    SUM(
                        COALESCE(
                            quantity,
                            0
                        )
                    ) AS qty

                FROM stocks.unpacked_fbs_stocks

                WHERE
                    date_from::DATE
                        = $report_date::DATE

                    AND nm_id IS NOT NULL

                GROUP BY
                    nm_id
            ),


            /*
            ================================================================
            ЕДИНЫЙ ЗАПАС ПО NM ID
            ================================================================
            */

            stock AS (
                SELECT
                    COALESCE(
                        wb.nm_id,
                        fbs.nm_id
                    ) AS nm_id,

                    COALESCE(
                        wb.qty,
                        0
                    )
                    +
                    COALESCE(
                        fbs.qty,
                        0
                    ) AS qty

                FROM wb

                FULL OUTER JOIN fbs
                    ON wb.nm_id = fbs.nm_id
            ),


            /*
            ================================================================
            NM ID -> USK
            ================================================================
            */

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


            /*
            ================================================================
            ПОСЛЕДНЯЯ СЕБЕСТОИМОСТЬ
            ================================================================
            */

            costs AS (
                SELECT
                    nu.nm_id,

                    MAX(
                        w.adjust_wo[-1]
                    ) AS accounting_cost,

                    MAX(
                        w.adjust_man_wo[-1]
                    ) AS management_cost

                FROM nm_usk nu

                LEFT JOIN inventories.pre_wo w
                    ON w.usk = nu.usk

                GROUP BY
                    nu.nm_id
            )


            SELECT
                SUM(
                    s.qty
                    *
                    (
                        COALESCE(
                            c.accounting_cost,
                            0
                        )
                        / 100.0
                    )
                ) AS accounting_value,

                SUM(
                    s.qty
                    *
                    (
                        COALESCE(
                            c.management_cost,
                            0
                        )
                        / 100.0
                    )
                ) AS management_value,

                SUM(
                    CASE
                        WHEN
                            s.qty > 0
                            AND c.accounting_cost IS NULL
                        THEN s.qty
                        ELSE 0
                    END
                ) AS no_accounting_cost_qty,

                SUM(
                    CASE
                        WHEN
                            s.qty > 0
                            AND c.management_cost IS NULL
                        THEN s.qty
                        ELSE 0
                    END
                ) AS no_management_cost_qty

            FROM stock s

            LEFT JOIN costs c
                ON c.nm_id = s.nm_id

            WHERE
                s.qty > 0
            """,
            {
                "report_date": report_date,
            },
        ).fetchone()

    accounting = number(
        row[0]
        if row
        else 0
    )

    management = number(
        row[1]
        if row
        else 0
    )

    delta = (
        management
        - accounting
    )

    delta_pct = (
        delta
        / abs(accounting)
        * 100
        if accounting
        else None
    )

    return {
        "accounting_cost": accounting,
        "management_cost": management,
        "cost_delta": delta,
        "cost_delta_pct": delta_pct,

        "no_accounting_cost_qty": int(
            number(
                row[2]
                if row
                else 0
            )
        ),

        "no_management_cost_qty": int(
            number(
                row[3]
                if row
                else 0
            )
        ),
    }


# =============================================================================
# ЗДОРОВЬЕ ТОВАРНОГО ЗАПАСА
#
# ВАЖНО:
# stocks = WB + FBS + путь.
#
# Раньше old stock_health использовал только unpacked_stocks.
# Здесь FBS включён прямо в базовый stock CTE.
# =============================================================================


def _get_full_stock_health(
    report_date: str,
) -> dict:

    with get_duckdb_conn_with_opt() as con:
        rows = con.execute(
            """
            WITH

            /*
            ================================================================
            WB НА УРОВНЕ NM ID
            ================================================================
            */

            wb AS (
                SELECT
                    nm_id,

                    SUM(
                        COALESCE(
                            quantity,
                            0
                        )
                    ) AS wb_qty,

                    SUM(
                        COALESCE(
                            in_way_to_client,
                            0
                        )
                        +
                        COALESCE(
                            in_way_from_client,
                            0
                        )
                    ) AS transit_qty

                FROM stocks.unpacked_stocks

                WHERE
                    date_from::DATE
                        = $report_date::DATE

                    AND nm_id IS NOT NULL

                GROUP BY
                    nm_id
            ),


            /*
            ================================================================
            FBS НА УРОВНЕ NM ID
            ================================================================
            */

            fbs AS (
                SELECT
                    nm_id,

                    SUM(
                        COALESCE(
                            quantity,
                            0
                        )
                    ) AS fbs_qty

                FROM stocks.unpacked_fbs_stocks

                WHERE
                    date_from::DATE
                        = $report_date::DATE

                    AND nm_id IS NOT NULL

                GROUP BY
                    nm_id
            ),


            /*
            ================================================================
            ЕДИНЫЙ ТОВАРНЫЙ КОНТУР
            ================================================================
            */

            stocks AS (
                SELECT
                    COALESCE(
                        wb.nm_id,
                        fbs.nm_id
                    ) AS nm_id,

                    COALESCE(
                        wb.wb_qty,
                        0
                    ) AS wb_qty,

                    COALESCE(
                        fbs.fbs_qty,
                        0
                    ) AS fbs_qty,

                    COALESCE(
                        wb.transit_qty,
                        0
                    ) AS in_transit,

                    COALESCE(
                        wb.wb_qty,
                        0
                    )
                    +
                    COALESCE(
                        fbs.fbs_qty,
                        0
                    )
                    +
                    COALESCE(
                        wb.transit_qty,
                        0
                    ) AS total_qty

                FROM wb

                FULL OUTER JOIN fbs
                    ON wb.nm_id = fbs.nm_id
            ),


            /*
            ================================================================
            USK -> NM ID
            ================================================================
            */

            usk_to_nm AS (
                SELECT
                    usk,
                    MAX(card_id) AS nm_id

                FROM inventories.usk

                WHERE
                    usk IS NOT NULL
                    AND card_id IS NOT NULL

                GROUP BY
                    usk
            ),


            /*
            ================================================================
            ЧИСТЫЕ ПРОДАЖИ ЗА 30 ДНЕЙ
            ================================================================
            */

            sales_30d_by_usk AS (
                SELECT
                    t.usk,

                    SUM(
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
                        END
                    ) AS sales_qty_30d

                FROM inventories.inv_gl_final t

                WHERE
                    COALESCE(
                        t.cr_rev,
                        0
                    ) <> 0

                    AND t.date_from::DATE
                        BETWEEN
                        (
                            $report_date::DATE
                            - INTERVAL 29 DAY
                        )
                        AND $report_date::DATE

                GROUP BY
                    t.usk
            ),


            sales_30d AS (
                SELECT
                    m.nm_id,

                    SUM(
                        s.sales_qty_30d
                    ) AS sales_qty_30d

                FROM sales_30d_by_usk s

                INNER JOIN usk_to_nm m
                    ON m.usk = s.usk

                WHERE
                    m.nm_id IS NOT NULL

                GROUP BY
                    m.nm_id
            ),


            /*
            ================================================================
            УПРАВЛЕНЧЕСКАЯ СЕБЕСТОИМОСТЬ
            ================================================================
            */

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


            costs AS (
                SELECT
                    nu.nm_id,

                    MAX(
                        w.adjust_man_wo[-1]
                    ) AS last_man_costs

                FROM nm_usk nu

                LEFT JOIN inventories.pre_wo w
                    ON w.usk = nu.usk

                GROUP BY
                    nu.nm_id
            ),


            /*
            ================================================================
            ПЕРВЫЙ ДЕНЬ, КОГДА ПО NM ID ВООБЩЕ ВИДЕЛИ ОСТАТОК
            ================================================================

            Нужно, чтобы отличить новый товар (который просто
            ещё не успел продаться) от залежавшегося. Дата
            прихода как отдельная сущность в контуре не хранится,
            поэтому берём самый ранний день в истории остатков,
            где по nm_id было хоть что-то на складе.
            */

            first_seen AS (
                SELECT
                    nm_id,
                    MIN(stock_date) AS first_seen_date

                FROM (
                    SELECT
                        nm_id,
                        date_from::DATE AS stock_date
                    FROM stocks.unpacked_stocks
                    WHERE nm_id IS NOT NULL
                      AND COALESCE(quantity, 0) > 0

                    UNION ALL

                    SELECT
                        nm_id,
                        date_from::DATE AS stock_date
                    FROM stocks.unpacked_fbs_stocks
                    WHERE nm_id IS NOT NULL
                      AND COALESCE(quantity, 0) > 0
                ) seen

                GROUP BY
                    nm_id
            ),


            /*
            ================================================================
            ГЛУБИНА ИСТОРИИ ОСТАТКОВ
            ================================================================

            Если сама история остатков короче, чем окно "новый
            товар", first_seen_date ничего не докажет: старый
            товар будет неотличим от нового просто потому, что
            снимков раньше этой даты нет. В таком случае деление
            на новое/старое честно помечается как ненадёжное.
            */

            history_span AS (
                SELECT
                    MIN(stock_date) AS earliest_date
                FROM (
                    SELECT date_from::DATE AS stock_date
                    FROM stocks.unpacked_stocks
                    UNION ALL
                    SELECT date_from::DATE AS stock_date
                    FROM stocks.unpacked_fbs_stocks
                ) history
            ),


            /*
            ================================================================
            БАЗА
            ================================================================
            */

            base AS (
                SELECT
                    s.nm_id,

                    s.wb_qty,
                    s.fbs_qty,
                    s.in_transit,
                    s.total_qty,

                    COALESCE(
                        sl.sales_qty_30d,
                        0
                    ) AS sales_qty_30d,

                    CASE
                        WHEN COALESCE(
                            sl.sales_qty_30d,
                            0
                        ) > 0

                        THEN
                            s.total_qty
                            * 30.0
                            /
                            sl.sales_qty_30d

                        ELSE NULL
                    END AS coverage_days,

                    (
                        COALESCE(
                            c.last_man_costs,
                            0
                        )
                        / 100.0
                    ) AS man_cost_per_unit,

                    s.total_qty
                    *
                    (
                        COALESCE(
                            c.last_man_costs,
                            0
                        )
                        / 100.0
                    ) AS management_value,

                    fs.first_seen_date,

                    date_diff(
                        'day',
                        fs.first_seen_date,
                        $report_date::DATE
                    ) AS days_since_first_seen,

                    date_diff(
                        'day',
                        hs.earliest_date,
                        $report_date::DATE
                    ) AS history_days

                FROM stocks s

                LEFT JOIN sales_30d sl
                    ON sl.nm_id = s.nm_id

                LEFT JOIN costs c
                    ON c.nm_id = s.nm_id

                LEFT JOIN first_seen fs
                    ON fs.nm_id = s.nm_id

                CROSS JOIN history_span hs

                WHERE
                    s.total_qty > 0
            )


            SELECT
                nm_id,
                wb_qty,
                fbs_qty,
                in_transit,
                total_qty,
                sales_qty_30d,
                coverage_days,
                management_value,
                days_since_first_seen,
                history_days,

                CASE
                    WHEN sales_qty_30d <= 0
                    THEN 'no_sales'

                    WHEN coverage_days <= 30
                    THEN '0_30'

                    WHEN coverage_days <= 60
                    THEN '30_60'

                    WHEN coverage_days <= 90
                    THEN '60_90'

                    ELSE '90_plus'

                END AS coverage_bucket

            FROM base
            """,
            {
                "report_date": report_date,
            },
        ).df()

    if (
        rows is None
        or rows.empty
    ):
        return {
            "available": False,
            "reason": (
                "Нет данных для анализа "
                "здоровья товарного запаса."
            ),
        }

    # =========================================================================
    # ОБЩИЕ ИТОГИ
    # =========================================================================

    total_qty = float(
        rows["total_qty"].sum()
    )

    sales_30d = float(
        rows["sales_qty_30d"]
        .clip(
            lower=0
        )
        .sum()
    )

    active_rows = rows[
        rows["sales_qty_30d"] > 0
    ].copy()

    active_stock_qty = float(
        active_rows[
            "total_qty"
        ].sum()
    )

    overall_coverage_months = (
        total_qty
        / sales_30d
        if sales_30d > 0
        else None
    )

    active_coverage_months = (
        active_stock_qty
        / sales_30d
        if sales_30d > 0
        else None
    )

    average_daily_sales = (
        sales_30d
        / SALES_WINDOW_DAYS
        if sales_30d > 0
        else 0
    )

    coverage_days_total = (
        total_qty
        / average_daily_sales
        if average_daily_sales > 0
        else None
    )

    # =========================================================================
    # КОРЗИНЫ
    # =========================================================================

    bucket_config = [
        (
            "0_30",
            "До 30 дней",
            "до 30",
        ),
        (
            "30_60",
            "30–60 дней",
            "30–60",
        ),
        (
            "60_90",
            "60–90 дней",
            "60–90",
        ),
        (
            "90_plus",
            "90+ дней",
            "90+",
        ),
        (
            "no_sales",
            "Нет продаж",
            "нет продаж",
        ),
    ]

    buckets = []

    for (
        bucket_key,
        label,
        short_label,
    ) in bucket_config:

        bucket_rows = rows[
            rows[
                "coverage_bucket"
            ]
            == bucket_key
        ]

        qty = float(
            bucket_rows[
                "total_qty"
            ].sum()
        )

        management_value = float(
            bucket_rows[
                "management_value"
            ].sum()
        )

        share_pct = (
            qty
            / total_qty
            * 100
            if total_qty > 0
            else 0
        )

        products = int(
            bucket_rows[
                "nm_id"
            ].nunique()
        )

        buckets.append(
            {
                "key": bucket_key,
                "label": label,
                "short_label": short_label,
                "qty": qty,
                "share_pct": share_pct,
                "products": products,
                "management_value": (
                    management_value
                ),
            }
        )

    # =========================================================================
    # ЗОНА РИСКА
    # =========================================================================

    risk_rows = rows[
        rows[
            "coverage_bucket"
        ].isin(
            [
                "90_plus",
                "no_sales",
            ]
        )
    ].copy()

    risk_qty = float(
        risk_rows[
            "total_qty"
        ].sum()
    )

    risk_share_pct = (
        risk_qty
        / total_qty
        * 100
        if total_qty > 0
        else 0
    )

    risk_management_value = float(
        risk_rows[
            "management_value"
        ].sum()
    )

    risk_products = int(
        risk_rows[
            "nm_id"
        ].nunique()
    )

    # -------------------------------------------------------------------
    # НОВОЕ VS ЗАЛЕЖАВШЕЕСЯ ВНУТРИ ЗОНЫ РИСКА
    #
    # "Не продавалось 90 дней" и "приехало неделю назад" --
    # в остатках выглядят одинаково, а решения по ним разные:
    # по первому нужна уценка или списание, по второму -- просто
    # подождать. Делим по факту истории остатков, а не по вере
    # на слово, поэтому сначала проверяем, что самой истории
    # хватает, чтобы это деление вообще что-то доказывало.
    # -------------------------------------------------------------------

    history_days_value = (
        float(rows["history_days"].max())
        if "history_days" in rows and not rows["history_days"].isna().all()
        else None
    )

    arrival_data_reliable = (
        history_days_value is not None
        and history_days_value >= NEW_ARRIVAL_WINDOW_DAYS
    )

    if arrival_data_reliable:
        # Без даты первого появления (первая продажа была
        # раньше, чем есть история остатков) считаем товар
        # старым: недостаток данных не должен маскировать
        # реально залежавшийся товар под новый.
        is_new_arrival = (
            risk_rows["days_since_first_seen"].notna()
            & (risk_rows["days_since_first_seen"] < NEW_ARRIVAL_WINDOW_DAYS)
        )
    else:
        is_new_arrival = pd.Series(False, index=risk_rows.index)

    risk_new_rows = risk_rows[is_new_arrival]
    risk_stale_rows = risk_rows[~is_new_arrival]

    risk_new_qty = float(risk_new_rows["total_qty"].sum())
    risk_new_management_value = float(
        risk_new_rows["management_value"].sum()
    )
    risk_new_products = int(risk_new_rows["nm_id"].nunique())
    risk_new_share_pct = (
        risk_new_qty / total_qty * 100 if total_qty > 0 else 0
    )

    risk_stale_qty = float(risk_stale_rows["total_qty"].sum())
    risk_stale_management_value = float(
        risk_stale_rows["management_value"].sum()
    )
    risk_stale_products = int(risk_stale_rows["nm_id"].nunique())
    risk_stale_share_pct = (
        risk_stale_qty / total_qty * 100 if total_qty > 0 else 0
    )

    # =========================================================================
    # 90+
    # =========================================================================

    slow_rows = rows[
        rows[
            "coverage_bucket"
        ]
        == "90_plus"
    ]

    slow_qty = float(
        slow_rows[
            "total_qty"
        ].sum()
    )

    slow_share_pct = (
        slow_qty
        / total_qty
        * 100
        if total_qty > 0
        else 0
    )

    # =========================================================================
    # БЕЗ ПРОДАЖ
    # =========================================================================

    no_sales_rows = rows[
        rows[
            "coverage_bucket"
        ]
        == "no_sales"
    ]

    no_sales_qty = float(
        no_sales_rows[
            "total_qty"
        ].sum()
    )

    no_sales_share_pct = (
        no_sales_qty
        / total_qty
        * 100
        if total_qty > 0
        else 0
    )

    return {
        "available": True,

        "sales_window_days": (
            SALES_WINDOW_DAYS
        ),

        "total_qty": total_qty,

        "sales_qty_30d": (
            sales_30d
        ),

        "average_daily_sales": (
            average_daily_sales
        ),

        "coverage_days": (
            coverage_days_total
        ),

        "coverage_months": (
            overall_coverage_months
        ),

        "active_coverage_months": (
            active_coverage_months
        ),

        "active_stock_qty": (
            active_stock_qty
        ),

        "buckets": buckets,

        "risk_qty": risk_qty,
        "risk_share_pct": (
            risk_share_pct
        ),

        "risk_management_value": (
            risk_management_value
        ),

        "risk_products": (
            risk_products
        ),

        "slow_qty": slow_qty,
        "slow_share_pct": (
            slow_share_pct
        ),

        "no_sales_qty": (
            no_sales_qty
        ),

        "no_sales_share_pct": (
            no_sales_share_pct
        ),

        # -----------------------------------------------------------
        # НОВОЕ VS ЗАЛЕЖАВШЕЕСЯ (только внутри зоны риска)
        # -----------------------------------------------------------

        "new_arrival_window_days": NEW_ARRIVAL_WINDOW_DAYS,
        "arrival_data_reliable": arrival_data_reliable,
        "history_days": history_days_value,

        "risk_new_qty": risk_new_qty,
        "risk_new_share_pct": risk_new_share_pct,
        "risk_new_management_value": risk_new_management_value,
        "risk_new_products": risk_new_products,

        "risk_stale_qty": risk_stale_qty,
        "risk_stale_share_pct": risk_stale_share_pct,
        "risk_stale_management_value": risk_stale_management_value,
        "risk_stale_products": risk_stale_products,
    }


# =============================================================================
# ОСНОВНАЯ ФУНКЦИЯ
# =============================================================================


def get_stock_balance_data(
    report_date: date,
) -> dict[str, Any]:

    requested_date = (
        report_date.isoformat()
    )

    effective_date = (
        get_effective_stock_date(
            requested_date
        )
    )

    if not effective_date:
        return {
            "available": False,
            "requested_date": requested_date,
            "report_date": None,
            "reason": (
                "Не найден доступный снимок "
                "товарных остатков."
            ),
        }

    parsed = pd.to_datetime(
        effective_date,
        errors="coerce",
    )

    if pd.isna(parsed):
        return {
            "available": False,
            "requested_date": requested_date,
            "report_date": None,
            "reason": (
                "Дата снимка товарных остатков "
                "не распознана."
            ),
        }

    effective_date_string = (
        parsed.date().isoformat()
    )

    # =========================================================================
    # ОСНОВНЫЕ ИТОГИ
    # =========================================================================

    summary = (
        get_stocks_summary_stats(
            effective_date_string
        )
    )

    wb_qty = number(
        summary.get(
            "total_on_hand"
        )
    )

    fbs_qty = number(
        summary.get(
            "total_fbs"
        )
    )

    transit_qty = number(
        summary.get(
            "total_in_transit"
        )
    )

    total_qty = number(
        summary.get(
            "total_quantity"
        )
    )

    products = int(
        number(
            summary.get(
                "total_products"
            )
        )
    )

    brands_count = int(
        number(
            summary.get(
                "total_brands"
            )
        )
    )

    categories_count = int(
        number(
            summary.get(
                "total_categories"
            )
        )
    )

    # =========================================================================
    # СТРУКТУРА
    # =========================================================================

    brand_df = (
        _get_brand_stock_structure(
            effective_date_string
        )
    )

    category_df = (
        _get_category_stock_structure(
            effective_date_string
        )
    )

    fbs_categories_df = (
        _get_fbs_categories(
            effective_date_string
        )
    )

    fbs_stats = (
        _get_fbs_stats(
            effective_date_string
        )
    )

    # =========================================================================
    # FBS BRANDS
    # =========================================================================

    if not brand_df.empty:
        fbs_brands = (
            brand_df[
                brand_df[
                    "fbs_qty"
                ] > 0
            ]
            .sort_values(
                "fbs_qty",
                ascending=False,
            )
            .copy()
        )

        fbs_total = number(
            fbs_brands[
                "fbs_qty"
            ].sum()
        )

        top5_fbs_qty = number(
            fbs_brands
            .head(5)[
                "fbs_qty"
            ]
            .sum()
        )

        top5_fbs_share = _pct(
            top5_fbs_qty,
            fbs_total,
        )

    else:
        fbs_brands = (
            pd.DataFrame()
        )

        top5_fbs_share = 0.0

    # =========================================================================
    # СТОИМОСТЬ — WB + FBS + ПУТЬ
    # =========================================================================

    costs = (
        _get_full_stock_costs(
            effective_date_string
        )
    )

    # =========================================================================
    # HEALTH — WB + FBS + ПУТЬ
    # =========================================================================

    health = (
        _get_full_stock_health(
            effective_date_string
        )
    )

    # =========================================================================
    # PAYLOAD
    # =========================================================================

    return {
        "available": True,

        "requested_date": requested_date,

        "report_date": (
            effective_date_string
        ),

        "used_previous_snapshot": (
            effective_date_string
            != requested_date
        ),

        # ---------------------------------------------------------------------
        # KPI
        # ---------------------------------------------------------------------

        "total_qty": total_qty,
        "wb_qty": wb_qty,
        "fbs_qty": fbs_qty,
        "transit_qty": transit_qty,

        "wb_share_pct": _pct(
            wb_qty,
            total_qty,
        ),

        "fbs_share_pct": _pct(
            fbs_qty,
            total_qty,
        ),

        "transit_share_pct": _pct(
            transit_qty,
            total_qty,
        ),

        "products": products,
        "brands_count": brands_count,
        "categories_count": (
            categories_count
        ),

        # ---------------------------------------------------------------------
        # БОЛЬШОЙ ГРАФИК БРЕНДОВ
        # ---------------------------------------------------------------------

        "brands": dataframe_records(
            brand_df,
            limit=9,
        ),

        "categories": dataframe_records(
            category_df,
            limit=9,
        ),

        # ---------------------------------------------------------------------
        # FBS
        # ---------------------------------------------------------------------

        "fbs_products": (
            fbs_stats[
                "fbs_products"
            ]
        ),

        "fbs_only_products": (
            fbs_stats[
                "fbs_only_products"
            ]
        ),

        "fbs_only_qty": (
            fbs_stats[
                "fbs_only_qty"
            ]
        ),

        "fbs_top5_share_pct": (
            top5_fbs_share
        ),

        "fbs_brands": dataframe_records(
            fbs_brands,
            limit=5,
        ),

        "fbs_categories": (
            dataframe_records(
                fbs_categories_df,
                limit=5,
            )
        ),

        # ---------------------------------------------------------------------
        # СТОИМОСТЬ
        # ---------------------------------------------------------------------

        **costs,

        # ---------------------------------------------------------------------
        # HEALTH
        # ---------------------------------------------------------------------

        "health": health,
    }