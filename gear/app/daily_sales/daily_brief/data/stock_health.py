# gear/app/daily_sales/daily_brief/data/stock_health.py
from __future__ import annotations

from conns import get_duckdb_conn_with_opt


SALES_WINDOW_DAYS = 30


def get_stock_health_data(
    report_date,
) -> dict:
    """
    Аналитика здоровья товарного запаса.

    Методология
    -----------
    Остаток:
        физический остаток
        + в пути к клиенту
        + в пути от клиента.

    Продажи:
        чистые продажи за последние 30 календарных дней:
            cr_rev > 0  -> +1
            cr_rev < 0  -> -1

    Уровень расчёта:
        NM ID.

    Покрытие:
        total_qty * 30 / sales_qty_30d

    Корзины:
        <= 30 дней
        31-60 дней
        61-90 дней
        > 90 дней
        нет продаж

    Зона риска:
        покрытие > 90 дней
        ИЛИ
        продажи за 30 дней <= 0.

    Стоимость зоны риска:
        по последней управленческой себестоимости.
        Себестоимость хранится в копейках,
        поэтому переводится в рубли делением на 100.
    """

    with get_duckdb_conn_with_opt() as con:
        rows = con.execute(
            """
            WITH

            /*
            ================================================================
            ОСТАТОК НА УРОВНЕ NM ID
            ================================================================
            */

            stocks AS (
                SELECT
                    t.nm_id,

                    SUM(
                        COALESCE(
                            t.quantity,
                            0
                        )
                    ) AS on_hand,

                    SUM(
                        COALESCE(
                            t.in_way_to_client,
                            0
                        )
                        +
                        COALESCE(
                            t.in_way_from_client,
                            0
                        )
                    ) AS in_transit,

                    SUM(
                        COALESCE(
                            t.quantity,
                            0
                        )
                        +
                        COALESCE(
                            t.in_way_to_client,
                            0
                        )
                        +
                        COALESCE(
                            t.in_way_from_client,
                            0
                        )
                    ) AS total_qty

                FROM stocks.unpacked_stocks t

                WHERE
                    t.date_from::DATE
                        = $report_date::DATE

                    AND t.nm_id IS NOT NULL

                GROUP BY
                    t.nm_id
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
            ЧИСТЫЕ ПРОДАЖИ ЗА 30 ДНЕЙ НА УРОВНЕ USK
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


            /*
            ================================================================
            ПРОДАЖИ НА УРОВНЕ NM ID
            ================================================================
            */

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
            ПОСЛЕДНЯЯ УПРАВЛЕНЧЕСКАЯ СЕБЕСТОИМОСТЬ
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
            БАЗА ДЛЯ АНАЛИТИКИ
            ================================================================
            */

            base AS (
                SELECT
                    s.nm_id,

                    s.on_hand,
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

                    COALESCE(
                        c.last_man_costs,
                        0
                    ) / 100.0
                        AS man_cost_per_unit,

                    s.total_qty
                    * (
                        COALESCE(
                            c.last_man_costs,
                            0
                        )
                        / 100.0
                    ) AS management_value

                FROM stocks s

                LEFT JOIN sales_30d sl
                    ON sl.nm_id = s.nm_id

                LEFT JOIN costs c
                    ON c.nm_id = s.nm_id

                WHERE
                    s.total_qty > 0
            )


            /*
            ================================================================
            ИТОГ
            ================================================================
            */

            SELECT
                nm_id,
                on_hand,
                in_transit,
                total_qty,
                sales_qty_30d,
                coverage_days,
                management_value,

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

    if rows is None or rows.empty:
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
        .clip(lower=0)
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

    # При 30-дневном окне продаж:
    #
    # stock / sales_30d
    #
    # уже приблизительно показывает
    # количество месяцев покрытия.
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
    # КОРЗИНЫ ПОКРЫТИЯ
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
            rows["coverage_bucket"]
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
                "short_label": (
                    short_label
                ),
                "qty": qty,
                "share_pct": (
                    share_pct
                ),
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

    # -------------------------------------------------------------------------
    # 90+
    # -------------------------------------------------------------------------

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

    # -------------------------------------------------------------------------
    # Нет продаж
    # -------------------------------------------------------------------------

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

        "slow_qty": (
            slow_qty
        ),

        "slow_share_pct": (
            slow_share_pct
        ),

        "no_sales_qty": (
            no_sales_qty
        ),

        "no_sales_share_pct": (
            no_sales_share_pct
        ),
    }