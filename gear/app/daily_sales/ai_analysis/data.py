# gear/app/daily_sales/ai_analysis/data.py
from __future__ import annotations

from calendar import monthrange
from datetime import date, timedelta

from conns import get_duckdb_conn_with_opt


def get_last_sales_date() -> date | None:
    with get_duckdb_conn_with_opt() as con:
        row = con.execute(
            """
            SELECT MAX(date_from)::DATE
            FROM sales.sales_long
            WHERE field = 'retail_price'
            """
        ).fetchone()

    return row[0] if row and row[0] else None


def normalize_date(value) -> date:
    if isinstance(value, date):
        return value

    return date.fromisoformat(str(value)[:10])


def shift_month(value: date, months: int) -> date:
    month_index = value.year * 12 + value.month - 1 + months
    year = month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, monthrange(year, month)[1])
    return date(year, month, day)


def get_compare_period(
    start_date: date,
    end_date: date,
    compare_mode: str,
) -> tuple[date, date]:
    start_date = normalize_date(start_date)
    end_date = normalize_date(end_date)
    period_days = (end_date - start_date).days + 1

    if compare_mode == "previous_week":
        return (
            start_date - timedelta(days=7),
            end_date - timedelta(days=7),
        )

    if compare_mode == "previous_month":
        return (
            shift_month(start_date, -1),
            shift_month(end_date, -1),
        )

    if compare_mode == "previous_year":
        return (
            date(start_date.year - 1, start_date.month, start_date.day),
            date(end_date.year - 1, end_date.month, end_date.day),
        )

    compare_end = start_date - timedelta(days=1)
    compare_start = compare_end - timedelta(days=period_days - 1)
    return compare_start, compare_end


def get_period_definitions(report_date: date) -> list[dict]:
    report_date = normalize_date(report_date)

    quarter = (report_date.month - 1) // 3 + 1
    quarter_start_month = (quarter - 1) * 3 + 1

    mtd_start = report_date.replace(day=1)
    qtd_start = date(report_date.year, quarter_start_month, 1)
    ytd_start = date(report_date.year, 1, 1)

    previous_month_start = shift_month(mtd_start, -1)
    previous_month_end = shift_month(report_date, -1)

    previous_quarter_start = shift_month(qtd_start, -3)
    previous_quarter_end = shift_month(report_date, -3)

    previous_year_start = date(report_date.year - 1, 1, 1)
    previous_year_end = date(
        report_date.year - 1,
        report_date.month,
        min(
            report_date.day,
            monthrange(report_date.year - 1, report_date.month)[1],
        ),
    )

    return [
        {
            "key": "mtd",
            "label": "MTD",
            "title": "С начала месяца",
            "start": mtd_start,
            "end": report_date,
            "compare_start": previous_month_start,
            "compare_end": previous_month_end,
        },
        {
            "key": "qtd",
            "label": "QTD",
            "title": "С начала квартала",
            "start": qtd_start,
            "end": report_date,
            "compare_start": previous_quarter_start,
            "compare_end": previous_quarter_end,
        },
        {
            "key": "ytd",
            "label": "YTD",
            "title": "С начала года",
            "start": ytd_start,
            "end": report_date,
            "compare_start": previous_year_start,
            "compare_end": previous_year_end,
        },
    ]


def get_sales_metrics(start_date: date, end_date: date) -> dict:
    start_date = normalize_date(start_date)
    end_date = normalize_date(end_date)

    with get_duckdb_conn_with_opt() as con:
        row = con.execute(
            """
            SELECT
                COALESCE(
                    SUM(CASE WHEN oper = 'dt' THEN val ELSE 0 END),
                    0
                ) / 100.0 AS sales_amount,

                COALESCE(
                    SUM(CASE WHEN oper = 'cr' THEN val ELSE 0 END),
                    0
                ) / 100.0 AS returns_amount,

                COUNT(CASE WHEN oper = 'dt' THEN 1 END)
                    AS sales_transactions,

                COUNT(CASE WHEN oper = 'cr' THEN 1 END)
                    AS returns_transactions

            FROM sales.sales_long
            WHERE date_from BETWEEN ? AND ?
              AND field = 'retail_price'
            """,
            [start_date, end_date],
        ).fetchone()

    sales_amount = float(row[0] or 0)
    returns_amount = float(row[1] or 0)
    sales_transactions = int(row[2] or 0)
    returns_transactions = int(row[3] or 0)

    revenue = sales_amount - returns_amount
    quantity = sales_transactions - returns_transactions
    average_price = revenue / quantity if quantity > 0 else 0
    return_rate = returns_amount / sales_amount * 100 if sales_amount else 0
    days = max((end_date - start_date).days + 1, 1)
    daily_revenue = revenue / days

    return {
        "start_date": start_date,
        "end_date": end_date,
        "days": days,
        "sales_amount": sales_amount,
        "returns_amount": returns_amount,
        "revenue": revenue,
        "sales_transactions": sales_transactions,
        "returns_transactions": returns_transactions,
        "quantity": quantity,
        "average_price": average_price,
        "return_rate": return_rate,
        "daily_revenue": daily_revenue,
    }


def get_daily_metrics(start_date: date, end_date: date) -> list[dict]:
    start_date = normalize_date(start_date)
    end_date = normalize_date(end_date)

    with get_duckdb_conn_with_opt() as con:
        rows = con.execute(
            """
            SELECT
                date_from::DATE AS date_from,

                COALESCE(
                    SUM(CASE WHEN oper = 'dt' THEN val ELSE 0 END),
                    0
                ) / 100.0 AS sales_amount,

                COALESCE(
                    SUM(CASE WHEN oper = 'cr' THEN val ELSE 0 END),
                    0
                ) / 100.0 AS returns_amount,

                COUNT(CASE WHEN oper = 'dt' THEN 1 END)
                    AS sales_transactions,

                COUNT(CASE WHEN oper = 'cr' THEN 1 END)
                    AS returns_transactions

            FROM sales.sales_long
            WHERE date_from BETWEEN ? AND ?
              AND field = 'retail_price'

            GROUP BY date_from::DATE
            ORDER BY date_from::DATE
            """,
            [start_date, end_date],
        ).fetchall()

    result = []

    for row in rows:
        sales_amount = float(row[1] or 0)
        returns_amount = float(row[2] or 0)
        sales_transactions = int(row[3] or 0)
        returns_transactions = int(row[4] or 0)

        revenue = sales_amount - returns_amount
        quantity = sales_transactions - returns_transactions

        result.append(
            {
                "date": row[0],
                "sales_amount": sales_amount,
                "returns_amount": returns_amount,
                "revenue": revenue,
                "sales_transactions": sales_transactions,
                "returns_transactions": returns_transactions,
                "quantity": quantity,
                "average_price": revenue / quantity if quantity > 0 else 0,
                "return_rate": (
                    returns_amount / sales_amount * 100
                    if sales_amount
                    else 0
                ),
            }
        )

    return result


def get_period_comparison(
    start_date: date,
    end_date: date,
    compare_start: date,
    compare_end: date,
) -> dict:
    return {
        "current": get_sales_metrics(start_date, end_date),
        "previous": get_sales_metrics(compare_start, compare_end),
        "daily": get_daily_metrics(start_date, end_date),
        "daily_previous": get_daily_metrics(compare_start, compare_end),
    }


def get_mtd_qtd_ytd(report_date: date) -> list[dict]:
    rows = []

    for period in get_period_definitions(report_date):
        current = get_sales_metrics(period["start"], period["end"])
        previous = get_sales_metrics(
            period["compare_start"],
            period["compare_end"],
        )

        rows.append(
            {
                **period,
                "current": current,
                "previous": previous,
            }
        )

    return rows



# ---------------------------------------------------------------------
# Анализ брендов, категорий, товаров и запасов
# ---------------------------------------------------------------------

def get_entity_analysis(
    start_date: date,
    end_date: date,
    compare_start: date,
    compare_end: date,
    dimension: str,
) -> list[dict]:
    """
    dimension:
        brand    -> p.brand
        category -> p.subject_name
    """
    start_date = normalize_date(start_date)
    end_date = normalize_date(end_date)
    compare_start = normalize_date(compare_start)
    compare_end = normalize_date(compare_end)

    dimension_sql = {
        "brand": "COALESCE(NULLIF(TRIM(p.brand), ''), 'Не указан')",
        "category": "COALESCE(NULLIF(TRIM(p.subject_name), ''), 'Не указана')",
    }.get(dimension)

    if not dimension_sql:
        raise ValueError(f"Unsupported dimension: {dimension}")

    sql = f"""
        WITH prepared AS (
            SELECT
                {dimension_sql} AS entity_name,
                s.date_from::DATE AS date_from,
                s.oper,
                s.val
            FROM sales.sales_long s
            LEFT JOIN inventories.wb_product p
                ON p.card_id = s.nm_id
            WHERE s.field = 'retail_price'
              AND s.date_from BETWEEN ? AND ?
        ),
        aggregated AS (
            SELECT
                entity_name,

                COALESCE(SUM(
                    CASE
                        WHEN date_from BETWEEN ? AND ? AND oper = 'dt'
                        THEN val ELSE 0
                    END
                ), 0) / 100.0 AS current_sales,

                COALESCE(SUM(
                    CASE
                        WHEN date_from BETWEEN ? AND ? AND oper = 'cr'
                        THEN val ELSE 0
                    END
                ), 0) / 100.0 AS current_returns,

                COUNT(
                    CASE
                        WHEN date_from BETWEEN ? AND ? AND oper = 'dt'
                        THEN 1
                    END
                ) AS current_sales_qty,

                COUNT(
                    CASE
                        WHEN date_from BETWEEN ? AND ? AND oper = 'cr'
                        THEN 1
                    END
                ) AS current_returns_qty,

                COALESCE(SUM(
                    CASE
                        WHEN date_from BETWEEN ? AND ? AND oper = 'dt'
                        THEN val ELSE 0
                    END
                ), 0) / 100.0 AS previous_sales,

                COALESCE(SUM(
                    CASE
                        WHEN date_from BETWEEN ? AND ? AND oper = 'cr'
                        THEN val ELSE 0
                    END
                ), 0) / 100.0 AS previous_returns,

                COUNT(
                    CASE
                        WHEN date_from BETWEEN ? AND ? AND oper = 'dt'
                        THEN 1
                    END
                ) AS previous_sales_qty,

                COUNT(
                    CASE
                        WHEN date_from BETWEEN ? AND ? AND oper = 'cr'
                        THEN 1
                    END
                ) AS previous_returns_qty

            FROM prepared
            GROUP BY entity_name
        )
        SELECT *
        FROM aggregated
    """

    full_start = min(start_date, compare_start)
    full_end = max(end_date, compare_end)

    params = [
        full_start, full_end,

        start_date, end_date,
        start_date, end_date,
        start_date, end_date,
        start_date, end_date,

        compare_start, compare_end,
        compare_start, compare_end,
        compare_start, compare_end,
        compare_start, compare_end,
    ]

    with get_duckdb_conn_with_opt() as con:
        rows = con.execute(sql, params).fetchall()

    result = []

    for row in rows:
        (
            entity_name,
            current_sales,
            current_returns,
            current_sales_qty,
            current_returns_qty,
            previous_sales,
            previous_returns,
            previous_sales_qty,
            previous_returns_qty,
        ) = row

        current_sales = float(current_sales or 0)
        current_returns = float(current_returns or 0)
        previous_sales = float(previous_sales or 0)
        previous_returns = float(previous_returns or 0)

        current_qty = int(current_sales_qty or 0) - int(current_returns_qty or 0)
        previous_qty = int(previous_sales_qty or 0) - int(previous_returns_qty or 0)

        current_revenue = current_sales - current_returns
        previous_revenue = previous_sales - previous_returns

        result.append(
            {
                "name": entity_name,
                "current_revenue": current_revenue,
                "previous_revenue": previous_revenue,
                "revenue_delta": current_revenue - previous_revenue,
                "current_sales": current_sales,
                "current_returns": current_returns,
                "previous_sales": previous_sales,
                "previous_returns": previous_returns,
                "current_qty": current_qty,
                "previous_qty": previous_qty,
                "current_avg_price": (
                    current_revenue / current_qty if current_qty > 0 else 0
                ),
                "previous_avg_price": (
                    previous_revenue / previous_qty if previous_qty > 0 else 0
                ),
                "current_return_rate": (
                    current_returns / current_sales * 100
                    if current_sales else 0
                ),
                "previous_return_rate": (
                    previous_returns / previous_sales * 100
                    if previous_sales else 0
                ),
            }
        )

    return result


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


def get_product_analysis(
    start_date: date,
    end_date: date,
    compare_start: date,
    compare_end: date,
) -> list[dict]:
    """
    Объединяет продажи по nm_id с последним доступным остатком на дату end_date.

    ВАЖНО:
    количество продаж пока считается количеством строк dt минус cr,
    как и в wb_plan_monitor. Если в sales_long есть qty, замените COUNT на SUM(qty).
    """
    start_date = normalize_date(start_date)
    end_date = normalize_date(end_date)
    compare_start = normalize_date(compare_start)
    compare_end = normalize_date(compare_end)

    stock_date = get_latest_stock_date(end_date)

    if not stock_date:
        return []

    current_days = max((end_date - start_date).days + 1, 1)

    sql = """
        WITH sales_agg AS (
            SELECT
                s.nm_id,

                COALESCE(SUM(
                    CASE
                        WHEN s.date_from BETWEEN ? AND ? AND s.oper = 'dt'
                        THEN s.val ELSE 0
                    END
                ), 0) / 100.0 AS current_sales,

                COALESCE(SUM(
                    CASE
                        WHEN s.date_from BETWEEN ? AND ? AND s.oper = 'cr'
                        THEN s.val ELSE 0
                    END
                ), 0) / 100.0 AS current_returns,

                COUNT(
                    CASE
                        WHEN s.date_from BETWEEN ? AND ? AND s.oper = 'dt'
                        THEN 1
                    END
                ) AS current_sales_qty,

                COUNT(
                    CASE
                        WHEN s.date_from BETWEEN ? AND ? AND s.oper = 'cr'
                        THEN 1
                    END
                ) AS current_returns_qty,

                COALESCE(SUM(
                    CASE
                        WHEN s.date_from BETWEEN ? AND ? AND s.oper = 'dt'
                        THEN s.val ELSE 0
                    END
                ), 0) / 100.0 AS previous_sales,

                COALESCE(SUM(
                    CASE
                        WHEN s.date_from BETWEEN ? AND ? AND s.oper = 'cr'
                        THEN s.val ELSE 0
                    END
                ), 0) / 100.0 AS previous_returns,

                COUNT(
                    CASE
                        WHEN s.date_from BETWEEN ? AND ? AND s.oper = 'dt'
                        THEN 1
                    END
                ) AS previous_sales_qty,

                COUNT(
                    CASE
                        WHEN s.date_from BETWEEN ? AND ? AND s.oper = 'cr'
                        THEN 1
                    END
                ) AS previous_returns_qty

            FROM sales.sales_long s
            WHERE s.field = 'retail_price'
              AND s.date_from BETWEEN ? AND ?
            GROUP BY s.nm_id
        ),

        stock_agg AS (
            SELECT
                st.nm_id,
                SUM(
                    COALESCE(st.quantity, 0)
                    + COALESCE(st.in_way_from_client, 0)
                    + COALESCE(st.in_way_to_client, 0)
                ) AS stock_qty
            FROM stocks.unpacked_stocks st
            WHERE st.date_from::DATE = ?
            GROUP BY st.nm_id
        ),

        product_cost AS (
            SELECT
                p.card_id AS nm_id,
                MAX(w.adjust_man_wo[-1]) / 100.0 AS man_cost,
                MAX(w.adjust_wo[-1]) AS book_cost
               

            FROM inventories.wb_product p
            LEFT JOIN inventories.usk u
                ON u.card_id = p.card_id
            LEFT JOIN inventories.pre_wo w
                ON w.usk = u.usk
            GROUP BY p.card_id
        )

        SELECT
            COALESCE(sa.nm_id, st.nm_id) AS nm_id,
            COALESCE(NULLIF(TRIM(p.title), ''), 'Без наименования') AS title,
            COALESCE(NULLIF(TRIM(p.brand), ''), 'Не указан') AS brand,
            COALESCE(NULLIF(TRIM(p.subject_name), ''), 'Не указана') AS category,

            COALESCE(sa.current_sales, 0) AS current_sales,
            COALESCE(sa.current_returns, 0) AS current_returns,
            COALESCE(sa.current_sales_qty, 0) AS current_sales_qty,
            COALESCE(sa.current_returns_qty, 0) AS current_returns_qty,

            COALESCE(sa.previous_sales, 0) AS previous_sales,
            COALESCE(sa.previous_returns, 0) AS previous_returns,
            COALESCE(sa.previous_sales_qty, 0) AS previous_sales_qty,
            COALESCE(sa.previous_returns_qty, 0) AS previous_returns_qty,

            COALESCE(st.stock_qty, 0) AS stock_qty,
            COALESCE(pc.man_cost, 0) AS man_cost,
            COALESCE(pc.book_cost, 0) AS book_cost

        FROM sales_agg sa
        FULL OUTER JOIN stock_agg st
            ON st.nm_id = sa.nm_id
        LEFT JOIN inventories.wb_product p
            ON p.card_id = COALESCE(sa.nm_id, st.nm_id)
        LEFT JOIN product_cost pc
            ON pc.nm_id = COALESCE(sa.nm_id, st.nm_id)
    """

    full_start = min(start_date, compare_start)
    full_end = max(end_date, compare_end)

    params = [
        start_date, end_date,
        start_date, end_date,
        start_date, end_date,
        start_date, end_date,

        compare_start, compare_end,
        compare_start, compare_end,
        compare_start, compare_end,
        compare_start, compare_end,

        full_start, full_end,
        stock_date,
    ]

    with get_duckdb_conn_with_opt() as con:
        rows = con.execute(sql, params).fetchall()

    result = []

    for row in rows:
        (
            nm_id,
            title,
            brand,
            category,
            current_sales,
            current_returns,
            current_sales_qty,
            current_returns_qty,
            previous_sales,
            previous_returns,
            previous_sales_qty,
            previous_returns_qty,
            stock_qty,
            man_cost,
            book_cost,
        ) = row

        current_sales = float(current_sales or 0)
        current_returns = float(current_returns or 0)
        previous_sales = float(previous_sales or 0)
        previous_returns = float(previous_returns or 0)

        current_qty = int(current_sales_qty or 0) - int(current_returns_qty or 0)
        previous_qty = int(previous_sales_qty or 0) - int(previous_returns_qty or 0)

        current_revenue = current_sales - current_returns
        previous_revenue = previous_sales - previous_returns

        stock_qty = float(stock_qty or 0)
        avg_daily_sales_qty = max(current_qty, 0) / current_days

        if avg_daily_sales_qty > 0:
            days_of_stock = stock_qty / avg_daily_sales_qty
        elif stock_qty > 0:
            days_of_stock = None
        else:
            days_of_stock = 0.0

        man_cost = float(man_cost or 0)
        book_cost = float(book_cost or 0)

        result.append(
            {
                "nm_id": nm_id,
                "title": title,
                "brand": brand,
                "category": category,
                "stock_date": stock_date,
                "stock_qty": stock_qty,
                "man_cost": man_cost,
                "book_cost": book_cost,
                "stock_man_value": stock_qty * man_cost,
                "stock_book_value": stock_qty * book_cost,

                "current_sales": current_sales,
                "current_returns": current_returns,
                "current_revenue": current_revenue,
                "current_qty": current_qty,
                "current_avg_price": (
                    current_revenue / current_qty if current_qty > 0 else 0
                ),
                "current_return_rate": (
                    current_returns / current_sales * 100
                    if current_sales else 0
                ),

                "previous_sales": previous_sales,
                "previous_returns": previous_returns,
                "previous_revenue": previous_revenue,
                "previous_qty": previous_qty,
                "previous_avg_price": (
                    previous_revenue / previous_qty if previous_qty > 0 else 0
                ),
                "previous_return_rate": (
                    previous_returns / previous_sales * 100
                    if previous_sales else 0
                ),

                "avg_daily_sales_qty": avg_daily_sales_qty,
                "days_of_stock": days_of_stock,
            }
        )

    return result
