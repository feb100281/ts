# gear/app/daily_sales/daily_brief/data/sales.py

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import pandas as pd

from gear.app.data.base import DashboardData
from gear.app.daily_sales.wb_plan_monitor.data import (
    get_daily_fact,
    get_fact_for_period,
)

from ..helpers import (
    change_pct,
    dataframe_records,
    number,
)
from .common import (
    date_range,
    find_daily_row,
    first_row,
    previous_month_same_day,
    previous_year_same_day,
)


def _daily_row(
    target: date,
    cache: dict[tuple[int, int], list[dict]],
) -> dict:
    """
    Возвращает показатели за конкретный день.

    Данные кэшируются по году и месяцу,
    чтобы повторно не запрашивать один и тот же месяц.
    """

    key = (
        target.year,
        target.month,
    )

    if key not in cache:
        cache[key] = get_daily_fact(
            year=target.year,
            month=target.month,
            up_to_day=None,
        )

    return find_daily_row(
        cache[key],
        target,
    )


def _comparison(
    label: str,
    current: float,
    previous: float,
    previous_label: str,
) -> dict:
    return {
        "label": label,
        "current": current,
        "previous": previous,
        "previous_label": previous_label,
        "change_pct": change_pct(
            current,
            previous,
        ),
        "delta": current - previous,
    }


def _corr(
    rows: list[dict],
    x_key: str,
    y_key: str,
) -> float | None:
    frame = pd.DataFrame(
        rows or []
    )

    if (
        frame.empty
        or x_key not in frame
        or y_key not in frame
    ):
        return None

    x = pd.to_numeric(
        frame[x_key],
        errors="coerce",
    )

    y = pd.to_numeric(
        frame[y_key],
        errors="coerce",
    )

    valid = (
        x.notna()
        & y.notna()
        & (x > 0)
        & (y > 0)
    )

    if (
        valid.sum() < 5
        or x[valid].nunique() < 2
        or y[valid].nunique() < 2
    ):
        return None

    return float(
        x[valid].corr(
            y[valid]
        )
    )


def _build_ytd_daily_rows(
    *,
    report_date: date,
    current_year_start: date,
    previous_year_start: date,
    previous_year_end: date,
    cache: dict[tuple[int, int], list[dict]],
) -> list[dict]:
    """
    Формирует дневные показатели для YTD-графика.

    Используется показатель fact из get_daily_fact(),
    поэтому итог графика соответствует карточке
    «С начала года».
    """

    rows: list[dict] = []

    # Текущий год
    for current_day in date_range(
        current_year_start,
        report_date,
    ):
        source = _daily_row(
            current_day,
            cache,
        )

        rows.append(
            {
                "date_from": current_day.isoformat(),
                "amount": number(
                    source.get("fact")
                ),
            }
        )

    # Сопоставимый период прошлого года
    for previous_day in date_range(
        previous_year_start,
        previous_year_end,
    ):
        source = _daily_row(
            previous_day,
            cache,
        )

        rows.append(
            {
                "date_from": previous_day.isoformat(),
                "amount": number(
                    source.get("fact")
                ),
            }
        )

    return rows


def get_sales_data(
    report_date: date,
    plan_source: dict[str, Any],
) -> dict[str, Any]:
    previous_date = (
        report_date
        - timedelta(days=1)
    )

    previous_month_date = previous_month_same_day(
        report_date
    )

    previous_year_date = previous_year_same_day(
        report_date
    )

    cache: dict[
        tuple[int, int],
        list[dict],
    ] = {}

    current_month_rows = plan_source.get(
        "daily_rows",
        [],
    )

    if current_month_rows:
        cache[
            (
                report_date.year,
                report_date.month,
            )
        ] = list(
            current_month_rows
        )

    # ================================================================
    # ДЕНЬ И СРАВНИТЕЛЬНЫЕ ДАТЫ
    # ================================================================

    current_sales = _daily_row(
        report_date,
        cache,
    )

    previous_sales = _daily_row(
        previous_date,
        cache,
    )

    previous_month_sales = _daily_row(
        previous_month_date,
        cache,
    )

    previous_year_sales = _daily_row(
        previous_year_date,
        cache,
    )

    # ================================================================
    # ТЕПЛОВОЙ КАЛЕНДАРЬ — ПОСЛЕДНИЕ 35 ДНЕЙ
    # ================================================================

    trend_rows: list[dict] = []

    for current_day in date_range(
        report_date - timedelta(days=34),
        report_date,
    ):
        source = _daily_row(
            current_day,
            cache,
        )

        trend_rows.append(
            {
                "date_from": current_day.isoformat(),
                "amount": number(
                    source.get("fact")
                ),
                "sales_amount": number(
                    source.get("sales_amount")
                ),
                "returns_amount": number(
                    source.get("returns_amount")
                ),
            }
        )

    # ================================================================
    # ПЕРИОДЫ
    # ================================================================

    month_start = report_date.replace(
        day=1
    )

    prior_month_end = previous_month_same_day(
        report_date
    )

    prior_month_start = prior_month_end.replace(
        day=1
    )

    year_start = date(
        report_date.year,
        1,
        1,
    )

    prior_year_start = date(
        report_date.year - 1,
        1,
        1,
    )

    prior_year_end = previous_year_same_day(
        report_date
    )

    # ================================================================
    # MTD / YTD
    # ================================================================

    mtd = number(
        get_fact_for_period(
            month_start,
            report_date,
        )
    )

    prior_mtd = number(
        get_fact_for_period(
            prior_month_start,
            prior_month_end,
        )
    )

    ytd = number(
        get_fact_for_period(
            year_start,
            report_date,
        )
    )

    prior_ytd = number(
        get_fact_for_period(
            prior_year_start,
            prior_year_end,
        )
    )

    ytd_daily_rows = _build_ytd_daily_rows(
        report_date=report_date,
        current_year_start=year_start,
        previous_year_start=prior_year_start,
        previous_year_end=prior_year_end,
        cache=cache,
    )

    # ================================================================
    # ДАННЫЕ ИЗ DASHBOARD
    # ================================================================

    with DashboardData() as dashboard:
        daily_finance = (
            dashboard
            .get_dayly_sales_grid_data(
                start=report_date,
                end=report_date,
            )
        )

        previous_finance = (
            dashboard
            .get_dayly_sales_grid_data(
                start=previous_date,
                end=previous_date,
            )
        )

        # ============================================================
        # ТОП-5 БРЕНДОВ
        #
        # revenue:
        # чистая выручка с учётом возвратов;
        #
        # sold_units:
        # количество положительных продаж;
        #
        # avg_price:
        # средняя цена только по положительным продажам.
        # ============================================================

        top_brands = dashboard.con.execute(
            """
            SELECT
                COALESCE(
                    NULLIF(
                        TRIM(t.brand),
                        ''
                    ),
                    'Бренд не указан'
                ) AS name,

                ROUND(
                    SUM(t.cr_rev) / 100.0,
                    2
                ) AS revenue,

                SUM(
                    CASE
                        WHEN t.cr_rev > 0 THEN 1
                        ELSE 0
                    END
                ) AS sold_units,

                SUM(
                    CASE
                        WHEN t.cr_rev < 0 THEN 1
                        ELSE 0
                    END
                ) AS returned_units,

                SUM(
                    CASE
                        WHEN t.cr_rev > 0 THEN 1
                        WHEN t.cr_rev < 0 THEN -1
                        ELSE 0
                    END
                ) AS net_units,

                ROUND(
                    SUM(
                        CASE
                            WHEN t.cr_rev > 0
                            THEN t.cr_rev
                            ELSE 0
                        END
                    ) / 100.0,
                    2
                ) AS sales_amount,

                ABS(
                    ROUND(
                        SUM(
                            CASE
                                WHEN t.cr_rev < 0
                                THEN t.cr_rev
                                ELSE 0
                            END
                        ) / 100.0,
                        2
                    )
                ) AS returns_amount,

                ROUND(
                    SUM(
                        CASE
                            WHEN t.cr_rev > 0
                            THEN t.cr_rev
                            ELSE 0
                        END
                    ) / 100.0
                    /
                    NULLIF(
                        SUM(
                            CASE
                                WHEN t.cr_rev > 0 THEN 1
                                ELSE 0
                            END
                        ),
                        0
                    ),
                    2
                ) AS avg_price

            FROM base t

            WHERE
                t.date_from::DATE = ?::DATE
                AND t.cr_rev <> 0

            GROUP BY
                1

            HAVING
                SUM(t.cr_rev) > 0

            ORDER BY
                revenue DESC

            LIMIT 5
            """,
            [
                report_date,
            ],
        ).df()

        # ============================================================
        # ТОП-5 КАТЕГОРИЙ
        # ============================================================

        top_categories = dashboard.con.execute(
            """
            SELECT
                COALESCE(
                    NULLIF(
                        TRIM(t.subject_name),
                        ''
                    ),
                    'Категория не указана'
                ) AS name,

                ROUND(
                    SUM(t.cr_rev) / 100.0,
                    2
                ) AS revenue,

                SUM(
                    CASE
                        WHEN t.cr_rev > 0 THEN 1
                        ELSE 0
                    END
                ) AS sold_units,

                SUM(
                    CASE
                        WHEN t.cr_rev < 0 THEN 1
                        ELSE 0
                    END
                ) AS returned_units,

                SUM(
                    CASE
                        WHEN t.cr_rev > 0 THEN 1
                        WHEN t.cr_rev < 0 THEN -1
                        ELSE 0
                    END
                ) AS net_units,

                ROUND(
                    SUM(
                        CASE
                            WHEN t.cr_rev > 0
                            THEN t.cr_rev
                            ELSE 0
                        END
                    ) / 100.0,
                    2
                ) AS sales_amount,

                ABS(
                    ROUND(
                        SUM(
                            CASE
                                WHEN t.cr_rev < 0
                                THEN t.cr_rev
                                ELSE 0
                            END
                        ) / 100.0,
                        2
                    )
                ) AS returns_amount,

                ROUND(
                    SUM(
                        CASE
                            WHEN t.cr_rev > 0
                            THEN t.cr_rev
                            ELSE 0
                        END
                    ) / 100.0
                    /
                    NULLIF(
                        SUM(
                            CASE
                                WHEN t.cr_rev > 0 THEN 1
                                ELSE 0
                            END
                        ),
                        0
                    ),
                    2
                ) AS avg_price

            FROM base t

            WHERE
                t.date_from::DATE = ?::DATE
                AND t.cr_rev <> 0

            GROUP BY
                1

            HAVING
                SUM(t.cr_rev) > 0

            ORDER BY
                revenue DESC

            LIMIT 5
            """,
            [
                report_date,
            ],
        ).df()

        # ============================================================
        # ДНЕВНАЯ ЦЕНА — 90 ДНЕЙ
        # ============================================================

        daily_price = dashboard.con.execute(
            """
            SELECT
                t.date_from::DATE AS date_from,

                STRFTIME(
                    t.date_from::DATE,
                    '%d.%m'
                ) AS date_label,

                SUM(
                    CASE
                        WHEN t.cr_rev > 0 THEN 1
                        ELSE 0
                    END
                ) AS sales_qty,

                ROUND(
                    SUM(
                        CASE
                            WHEN t.cr_rev > 0
                            THEN t.cr_rev
                            ELSE 0
                        END
                    ) / 100.0
                    /
                    NULLIF(
                        SUM(
                            CASE
                                WHEN t.cr_rev > 0 THEN 1
                                ELSE 0
                            END
                        ),
                        0
                    ),
                    2
                ) AS avg_price,

                ROUND(
                    SUM(t.cr_rev) / 100.0,
                    2
                ) AS net_amount

            FROM base t

            WHERE
                t.date_from::DATE
                BETWEEN ?::DATE AND ?::DATE

            GROUP BY
                1,
                2

            ORDER BY
                1
            """,
            [
                report_date - timedelta(days=89),
                report_date,
            ],
        ).df()

        # ============================================================
        # МЕСЯЧНАЯ ЦЕНА — 12 МЕСЯЦЕВ
        # ============================================================

        monthly_price = dashboard.con.execute(
            """
            SELECT
                DATE_TRUNC(
                    'month',
                    t.date_from::DATE
                )::DATE AS month_date,

                STRFTIME(
                    DATE_TRUNC(
                        'month',
                        t.date_from::DATE
                    ),
                    '%m.%Y'
                ) AS month_label,

                SUM(
                    CASE
                        WHEN t.cr_rev > 0 THEN 1
                        ELSE 0
                    END
                ) AS sales_qty,

                ROUND(
                    SUM(
                        CASE
                            WHEN t.cr_rev > 0
                            THEN t.cr_rev
                            ELSE 0
                        END
                    ) / 100.0
                    /
                    NULLIF(
                        SUM(
                            CASE
                                WHEN t.cr_rev > 0 THEN 1
                                ELSE 0
                            END
                        ),
                        0
                    ),
                    2
                ) AS avg_price,

                ROUND(
                    SUM(t.cr_rev) / 100.0,
                    2
                ) AS net_amount

            FROM base t

            WHERE
                t.date_from::DATE
                BETWEEN ?::DATE AND ?::DATE

            GROUP BY
                1,
                2

            ORDER BY
                1
            """,
            [
                report_date.replace(day=1)
                - pd.DateOffset(months=11),
                report_date,
            ],
        ).df()

        # ============================================================
        # КАТЕГОРИИ ВОЗВРАТОВ
        # ============================================================

        return_categories = dashboard.con.execute(
            """
            SELECT
                COALESCE(
                    NULLIF(
                        TRIM(t.subject_name),
                        ''
                    ),
                    'Категория не указана'
                ) AS name,

                ABS(
                    ROUND(
                        SUM(
                            CASE
                                WHEN t.cr_rev < 0
                                THEN t.cr_rev
                                ELSE 0
                            END
                        ) / 100.0,
                        2
                    )
                ) AS returns_amount,

                SUM(
                    CASE
                        WHEN t.cr_rev < 0 THEN 1
                        ELSE 0
                    END
                ) AS returns_qty

            FROM base t

            WHERE
                t.date_from::DATE = ?::DATE

            GROUP BY
                1

            HAVING
                SUM(
                    CASE
                        WHEN t.cr_rev < 0 THEN 1
                        ELSE 0
                    END
                ) > 0

            ORDER BY
                returns_amount DESC

            LIMIT 5
            """,
            [
                report_date,
            ],
        ).df()

    # ================================================================
    # ИТОГОВЫЙ PAYLOAD
    # ================================================================

    finance_row = first_row(
        daily_finance
    )

    previous_finance_row = first_row(
        previous_finance
    )

    fact = number(
        current_sales.get("fact")
    )

    sales_transactions = number(
        current_sales.get(
            "sales_transactions"
        )
    )

    returns_transactions = number(
        current_sales.get(
            "returns_transactions"
        )
    )

    returns_rate = (
        returns_transactions
        / sales_transactions
        * 100
        if sales_transactions
        else 0
    )

    comparisons = {
        "previous_day": _comparison(
            "К предыдущему дню",
            fact,
            number(
                previous_sales.get("fact")
            ),
            previous_date.strftime(
                "%d.%m.%Y"
            ),
        ),

        "previous_month_day": _comparison(
            "К аналогичному дню прошлого месяца",
            fact,
            number(
                previous_month_sales.get("fact")
            ),
            previous_month_date.strftime(
                "%d.%m.%Y"
            ),
        ),

        "previous_year_day": _comparison(
            "К аналогичному дню прошлого года",
            fact,
            number(
                previous_year_sales.get("fact")
            ),
            previous_year_date.strftime(
                "%d.%m.%Y"
            ),
        ),

        "mtd": _comparison(
            "С начала месяца",
            mtd,
            prior_mtd,
            (
                f"{prior_month_start:%d.%m}"
                f"-{prior_month_end:%d.%m.%Y}"
            ),
        ),

        "ytd": _comparison(
            "С начала года",
            ytd,
            prior_ytd,
            (
                f"{prior_year_start:%d.%m}"
                f"-{prior_year_end:%d.%m.%Y}"
            ),
        ),
    }

    daily_rows = dataframe_records(
        daily_price
    )

    monthly_rows = dataframe_records(
        monthly_price
    )

    return {
        "kpi": {
            **finance_row,

            "amount": fact,

            "sales_amount": number(
                current_sales.get(
                    "sales_amount"
                )
            ),

            "returns_amount": number(
                current_sales.get(
                    "returns_amount"
                )
            ),

            "sales_transactions": (
                sales_transactions
            ),

            "returns_transactions": (
                returns_transactions
            ),

            "total_net_sales": number(
                current_sales.get("qty")
            ),

            "avg_price": number(
                current_sales.get("avg_price")
            ),

            "returns_rate": returns_rate,

            "revenue_change_pct": (
                comparisons[
                    "previous_day"
                ][
                    "change_pct"
                ]
            ),

            "margin_change_pct": change_pct(
                number(
                    finance_row.get(
                        "margin_man"
                    )
                ),
                number(
                    previous_finance_row.get(
                        "margin_man"
                    )
                ),
            ),
        },

        "comparisons": comparisons,

        "trend": trend_rows,

        "ytd_daily_rows": ytd_daily_rows,

        "top_brands": dataframe_records(
            top_brands
        ),

        "top_categories": dataframe_records(
            top_categories
        ),

        "return_categories": dataframe_records(
            return_categories
        ),

        "daily_price_rows": daily_rows,

        "monthly_price_rows": monthly_rows,

        "price_analysis": {
            "daily_corr": _corr(
                daily_rows,
                "sales_qty",
                "avg_price",
            ),

            "monthly_corr": _corr(
                monthly_rows,
                "sales_qty",
                "avg_price",
            ),
        },
    }