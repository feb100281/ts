# budget/reporting/pdf/services/sales_data_service.py
from __future__ import annotations

from typing import Any
import numpy as np
from pathlib import Path

import duckdb
import pandas as pd
from django.conf import settings
from conns import get_duckdb_conn


DUCK_FILE = Path(settings.BASE_DIR) / "data" / "analytics.duckdb"


def _format_money(x):
    return f"{x:,.0f}".replace(",", " ")


def _format_int(x):
    return f"{int(x):,}".replace(",", " ")


def get_daily_sales_df() -> pd.DataFrame:
    conn = get_duckdb_conn()

    query = """
        SELECT
            CAST(date_from AS DATE) AS dt,
            SUM(CASE WHEN dtn_id = 2 AND field = 'retail_price' THEN value ELSE 0 END) / 100.0 AS sales_amount,
            SUM(CASE WHEN dtn_id = 1 AND field = 'retail_price' THEN value ELSE 0 END) / 100.0 AS returns_amount,
            COUNT(*) FILTER (WHERE dtn_id = 2 AND field = 'retail_price') AS sales_qty,
            COUNT(*) FILTER (WHERE dtn_id = 1 AND field = 'retail_price') AS returns_qty
        FROM sales
        WHERE field = 'retail_price'
        GROUP BY 1
        ORDER BY 1
    """
    df = conn.execute(query).df()
    conn.close()

    if df.empty:
        df = pd.DataFrame(columns=["dt", "sales_amount", "returns_amount", "sales_qty", "returns_qty"])

    df["dt"] = pd.to_datetime(df["dt"])
    df["sales_amount"] = df["sales_amount"].fillna(0.0)
    df["returns_amount"] = df["returns_amount"].fillna(0.0)
    df["sales_qty"] = df["sales_qty"].fillna(0).astype(int)
    df["returns_qty"] = df["returns_qty"].fillna(0).astype(int)

    df["net_amount"] = df["sales_amount"] - df["returns_amount"]
    df["net_qty"] = df["sales_qty"] - df["returns_qty"]

    return df


def get_top_nm_ids() -> dict:
    conn = get_duckdb_conn()


    query_top_sales = """
        WITH product_dim AS (
            SELECT
                nm_id,
                ANY_VALUE(title) AS product_name,
                ANY_VALUE(brand) AS brand
            FROM product
            GROUP BY nm_id
        ),
        cards_latest AS (
            SELECT
                nm_id,
                json_extract_string(payload_raw, '$.subjectName') AS subject_name,
                json_extract_string(payload_raw, '$.photos[0].big') AS photo_url
            FROM (
                SELECT
                    nm_id,
                    payload_raw,
                    loaded_at,
                    ROW_NUMBER() OVER (PARTITION BY nm_id ORDER BY loaded_at DESC) AS rn
                FROM cards
            ) t
            WHERE rn = 1
        ),
        base AS (
            SELECT
                s.nm_id,
                ANY_VALUE(s.sa_name) AS sa_name,
                MIN(CAST(s.date_from AS DATE)) AS first_sale_date,
                SUM(CASE WHEN s.dtn_id = 2 AND s.field = 'retail_price' THEN s.value ELSE 0 END) / 100.0 AS sales_amount,
                SUM(CASE WHEN s.dtn_id = 1 AND s.field = 'retail_price' THEN s.value ELSE 0 END) / 100.0 AS returns_amount,
                COUNT(*) FILTER (WHERE s.dtn_id = 2 AND s.field = 'retail_price') AS sales_qty,
                COUNT(*) FILTER (WHERE s.dtn_id = 1 AND s.field = 'retail_price') AS returns_qty
            FROM sales s
            WHERE s.field = 'retail_price'
              AND s.date_from >= CURRENT_DATE - INTERVAL '90 days'
            GROUP BY s.nm_id
        ),
        total AS (
            SELECT SUM(sales_amount) AS total_sales_amount
            FROM base
        )
        SELECT
            b.nm_id,
            b.sa_name,
            b.first_sale_date,
            p.product_name,
            p.brand,
            c.subject_name,
            c.photo_url,
            b.sales_amount,
            b.returns_amount,
            b.sales_qty,
            b.returns_qty,
            ROUND(100.0 * b.sales_amount / NULLIF(t.total_sales_amount, 0), 2) AS revenue_share_pct
        FROM base b
        LEFT JOIN product_dim p
            ON b.nm_id = p.nm_id
        LEFT JOIN cards_latest c
            ON b.nm_id = c.nm_id
        CROSS JOIN total t
        WHERE b.sales_amount > 0
        ORDER BY b.sales_amount DESC
        LIMIT 5
    """

    query_top_returns = """
        WITH product_dim AS (
            SELECT
                nm_id,
                ANY_VALUE(title) AS product_name,
                ANY_VALUE(brand) AS brand
            FROM product
            GROUP BY nm_id
        ),
        cards_latest AS (
            SELECT
                nm_id,
                json_extract_string(payload_raw, '$.subjectName') AS subject_name,
                json_extract_string(payload_raw, '$.photos[0].big') AS photo_url
            FROM (
                SELECT
                    nm_id,
                    payload_raw,
                    loaded_at,
                    ROW_NUMBER() OVER (PARTITION BY nm_id ORDER BY loaded_at DESC) AS rn
                FROM cards
            ) t
            WHERE rn = 1
        ),
        base AS (
            SELECT
                s.nm_id,
                ANY_VALUE(s.sa_name) AS sa_name,
                MIN(CAST(s.date_from AS DATE)) AS first_sale_date,
                SUM(CASE WHEN s.dtn_id = 1 AND s.field = 'retail_price' THEN s.value ELSE 0 END) / 100.0 AS returns_amount,
                COUNT(*) FILTER (WHERE s.dtn_id = 1 AND s.field = 'retail_price') AS returns_qty,
                COUNT(*) FILTER (WHERE s.dtn_id = 2 AND s.field = 'retail_price') AS sales_qty,
                ROUND(
                    100.0 * COUNT(*) FILTER (WHERE s.dtn_id = 1 AND s.field = 'retail_price')
                    / NULLIF(COUNT(*) FILTER (WHERE s.dtn_id = 2 AND s.field = 'retail_price'), 0),
                    2
                ) AS return_rate_pct
            FROM sales s
            WHERE s.field = 'retail_price'
              AND s.date_from >= CURRENT_DATE - INTERVAL '90 days'
            GROUP BY s.nm_id
            HAVING COUNT(*) FILTER (WHERE s.dtn_id = 1 AND s.field = 'retail_price') > 0
        )
        SELECT
            b.nm_id,
            b.sa_name,
            b.first_sale_date,
            p.product_name,
            p.brand,
            c.subject_name,
            c.photo_url,
            b.returns_amount,
            b.returns_qty,
            b.sales_qty,
            b.return_rate_pct
        FROM base b
        LEFT JOIN product_dim p
            ON b.nm_id = p.nm_id
        LEFT JOIN cards_latest c
            ON b.nm_id = c.nm_id
        ORDER BY b.returns_amount DESC
        LIMIT 5
    """

    query_old_skus = """
        WITH product_dim AS (
            SELECT
                nm_id,
                ANY_VALUE(title) AS product_name,
                ANY_VALUE(brand) AS brand
            FROM product
            GROUP BY nm_id
        ),
        cards_latest AS (
            SELECT
                nm_id,
                json_extract_string(payload_raw, '$.subjectName') AS subject_name,
                json_extract_string(payload_raw, '$.photos[0].big') AS photo_url
            FROM (
                SELECT
                    nm_id,
                    payload_raw,
                    loaded_at,
                    ROW_NUMBER() OVER (PARTITION BY nm_id ORDER BY loaded_at DESC) AS rn
                FROM cards
            ) t
            WHERE rn = 1
        ),
        sku_lifetime AS (
            SELECT
                s.nm_id,
                ANY_VALUE(s.sa_name) AS sa_name,
                MIN(CAST(s.date_from AS DATE)) AS first_sale_date,
                SUM(
                    CASE
                        WHEN s.dtn_id = 2
                         AND s.field = 'retail_price'
                         AND s.date_from >= CURRENT_DATE - INTERVAL '90 days'
                        THEN s.value ELSE 0
                    END
                ) / 100.0 AS sales_amount_90d,
                COUNT(*) FILTER (
                    WHERE s.dtn_id = 2
                      AND s.field = 'retail_price'
                      AND s.date_from >= CURRENT_DATE - INTERVAL '90 days'
                ) AS sales_qty_90d
            FROM sales s
            WHERE s.field = 'retail_price'
            GROUP BY s.nm_id
            HAVING MIN(CAST(s.date_from AS DATE)) < DATE '2024-01-01'
        )
        SELECT
            b.nm_id,
            b.sa_name,
            b.first_sale_date,
            p.product_name,
            p.brand,
            c.subject_name,
            c.photo_url,
            b.sales_amount_90d,
            b.sales_qty_90d
        FROM sku_lifetime b
        LEFT JOIN product_dim p
            ON b.nm_id = p.nm_id
        LEFT JOIN cards_latest c
            ON b.nm_id = c.nm_id
        WHERE b.sales_amount_90d > 0
        ORDER BY b.sales_amount_90d DESC
        LIMIT 10
    """

    top_products = conn.execute(query_top_sales).df().to_dict("records")
    top_returns = conn.execute(query_top_returns).df().to_dict("records")
    old_skus = conn.execute(query_old_skus).df().to_dict("records")

    period_query = """
        SELECT
            MIN(CAST(date_from AS DATE)) AS period_from,
            MAX(CAST(date_from AS DATE)) AS period_to
        FROM sales
        WHERE field = 'retail_price'
          AND date_from >= CURRENT_DATE - INTERVAL '90 days'
    """
    period_row = conn.execute(period_query).fetchone()
    conn.close()

    period_from = period_row[0] if period_row else None
    period_to = period_row[1] if period_row else None

    def _format_sale_start(dt):
        if not dt:
            return "—"
        try:
            return pd.to_datetime(dt).strftime("%m.%Y")
        except Exception:
            return "—"

    for row in top_products:
        row["nm_id_str"] = str(row.get("nm_id") or "")
        row["sales_amount_fmt"] = _format_money(row.get("sales_amount", 0))
        row["sales_qty_fmt"] = _format_int(row.get("sales_qty", 0))
        row["revenue_share_pct"] = f"{row.get('revenue_share_pct', 0):.2f}"
        row["product_name"] = row.get("product_name") or "—"
        row["brand"] = row.get("brand") or "—"
        row["sa_name"] = row.get("sa_name") or "—"
        row["subject_name"] = row.get("subject_name") or "—"
        row["photo_url"] = row.get("photo_url") or ""
        row["first_sale_date_fmt"] = _format_sale_start(row.get("first_sale_date"))

    for row in top_returns:
        row["nm_id_str"] = str(row.get("nm_id") or "")
        row["returns_amount_fmt"] = _format_money(row.get("returns_amount", 0))
        row["returns_qty_fmt"] = _format_int(row.get("returns_qty", 0))
        row["return_rate_pct"] = f"{row.get('return_rate_pct', 0):.2f}"
        row["product_name"] = row.get("product_name") or "—"
        row["brand"] = row.get("brand") or "—"
        row["sa_name"] = row.get("sa_name") or "—"
        row["subject_name"] = row.get("subject_name") or "—"
        row["photo_url"] = row.get("photo_url") or ""
        row["first_sale_date_fmt"] = _format_sale_start(row.get("first_sale_date"))

    for row in old_skus:
        row["nm_id_str"] = str(row.get("nm_id") or "")
        row["sales_amount_90d_fmt"] = _format_money(row.get("sales_amount_90d", 0))
        row["sales_qty_90d_fmt"] = _format_int(row.get("sales_qty_90d", 0))
        row["product_name"] = row.get("product_name") or "—"
        row["brand"] = row.get("brand") or "—"
        row["sa_name"] = row.get("sa_name") or "—"
        row["subject_name"] = row.get("subject_name") or "—"
        row["photo_url"] = row.get("photo_url") or ""
        row["first_sale_date_fmt"] = _format_sale_start(row.get("first_sale_date"))

    return {
        "top_products": top_products,
        "top_returns": top_returns,
        "old_skus": old_skus,
        "top_period_from": pd.to_datetime(period_from).strftime("%d.%m.%Y") if period_from else "—",
        "top_period_to": pd.to_datetime(period_to).strftime("%d.%m.%Y") if period_to else "—",
    }
    
    

def get_sales_by_category() -> dict:
    conn = get_duckdb_conn()

    # ------------------------------------------------------------------
    # 1. Основная таблица категорий
    # ------------------------------------------------------------------
    category_query = """
        WITH cards_dim AS (
            SELECT
                nm_id,
                ANY_VALUE(json_extract_string(payload_raw, '$.subjectName')) AS subject_name
            FROM cards
            GROUP BY nm_id
        ),
        sku_base AS (
            SELECT
                s.nm_id,
                SUM(CASE WHEN s.dtn_id = 2 AND s.field = 'retail_price' THEN s.value ELSE 0 END) / 100.0 AS sales_amount,
                SUM(CASE WHEN s.dtn_id = 1 AND s.field = 'retail_price' THEN s.value ELSE 0 END) / 100.0 AS returns_amount,
                COUNT(*) FILTER (WHERE s.dtn_id = 2 AND s.field = 'retail_price') AS sales_qty,
                COUNT(*) FILTER (WHERE s.dtn_id = 1 AND s.field = 'retail_price') AS returns_qty
            FROM sales s
            WHERE s.field = 'retail_price'
              AND s.date_from >= CURRENT_DATE - INTERVAL '90 days'
            GROUP BY s.nm_id
        ),
        sku_metrics AS (
            SELECT
                b.nm_id,
                COALESCE(c.subject_name, 'Не указана') AS subject_name,
                b.sales_amount,
                b.returns_amount,
                b.sales_qty,
                b.returns_qty,
                (b.sales_amount - b.returns_amount) AS net_amount,
                (b.sales_qty - b.returns_qty) AS net_qty,
                CASE
                    WHEN b.sales_qty > 0 THEN b.sales_amount / b.sales_qty
                    ELSE NULL
                END AS avg_price
            FROM sku_base b
            LEFT JOIN cards_dim c
                ON b.nm_id = c.nm_id
        ),
        category_agg AS (
            SELECT
                subject_name,
                SUM(sales_amount) AS sales_amount,
                SUM(returns_amount) AS returns_amount,
                SUM(sales_qty) AS sales_qty,
                SUM(returns_qty) AS returns_qty,
                SUM(net_amount) AS net_amount,
                SUM(net_qty) AS net_qty
            FROM sku_metrics
            GROUP BY 1
        ),
        totals AS (
            SELECT SUM(sales_amount) AS total_sales_amount
            FROM category_agg
        )
        SELECT
            a.subject_name,
            a.sales_amount,
            a.returns_amount,
            a.sales_qty,
            a.returns_qty,
            a.net_amount,
            a.net_qty,
            ROUND(100.0 * a.returns_qty / NULLIF(a.sales_qty, 0), 2) AS return_rate_pct,
            ROUND(100.0 * a.sales_amount / NULLIF(t.total_sales_amount, 0), 2) AS revenue_share_pct
        FROM category_agg a
        CROSS JOIN totals t
        WHERE a.sales_amount > 0
        ORDER BY a.sales_amount DESC
        LIMIT 15
    """

    category_rows = conn.execute(category_query).df().to_dict("records")

    # ------------------------------------------------------------------
    # 2. Статистика цен внутри категорий по SKU
    # ------------------------------------------------------------------
    price_stats_query = """
        WITH cards_dim AS (
            SELECT
                nm_id,
                ANY_VALUE(json_extract_string(payload_raw, '$.subjectName')) AS subject_name
            FROM cards
            GROUP BY nm_id
        ),
        sku_base AS (
            SELECT
                s.nm_id,
                SUM(CASE WHEN s.dtn_id = 2 AND s.field = 'retail_price' THEN s.value ELSE 0 END) / 100.0 AS sales_amount,
                COUNT(*) FILTER (WHERE s.dtn_id = 2 AND s.field = 'retail_price') AS sales_qty
            FROM sales s
            WHERE s.field = 'retail_price'
              AND s.date_from >= CURRENT_DATE - INTERVAL '90 days'
            GROUP BY s.nm_id
        ),
        sku_metrics AS (
            SELECT
                b.nm_id,
                COALESCE(c.subject_name, 'Не указана') AS subject_name,
                b.sales_amount,
                b.sales_qty,
                CASE
                    WHEN b.sales_qty > 0 THEN b.sales_amount / b.sales_qty
                    ELSE NULL
                END AS avg_price
            FROM sku_base b
            LEFT JOIN cards_dim c
                ON b.nm_id = c.nm_id
            WHERE b.sales_qty > 0
        ),
        top_categories AS (
            SELECT
                subject_name
            FROM (
                SELECT
                    subject_name,
                    SUM(sales_amount) AS sales_amount
                FROM sku_metrics
                GROUP BY 1
                ORDER BY sales_amount DESC
                LIMIT 15
            )
        )
        SELECT
            subject_name,
            ROUND(AVG(avg_price), 2) AS avg_sku_price,
            ROUND(MEDIAN(avg_price), 2) AS median_sku_price,
            ROUND(MIN(avg_price), 2) AS min_sku_price,
            ROUND(MAX(avg_price), 2) AS max_sku_price,
            COUNT(*) AS sku_count
        FROM sku_metrics
        WHERE subject_name IN (SELECT subject_name FROM top_categories)
        GROUP BY 1
        ORDER BY avg_sku_price DESC
    """

    price_stats_by_category = conn.execute(price_stats_query).df().to_dict("records")

    # ------------------------------------------------------------------
    # 3. Low / Medium / High внутри каждой категории
    # ------------------------------------------------------------------
    segment_query = """
            WITH cards_dim AS (
                SELECT
                    nm_id,
                    ANY_VALUE(json_extract_string(payload_raw, '$.subjectName')) AS subject_name
                FROM cards
                GROUP BY nm_id
            ),
            sku_base AS (
                SELECT
                    s.nm_id,
                    SUM(CASE WHEN s.dtn_id = 2 AND s.field = 'retail_price' THEN s.value ELSE 0 END) / 100.0 AS sales_amount,
                    SUM(CASE WHEN s.dtn_id = 1 AND s.field = 'retail_price' THEN s.value ELSE 0 END) / 100.0 AS returns_amount,
                    COUNT(*) FILTER (WHERE s.dtn_id = 2 AND s.field = 'retail_price') AS sales_qty,
                    COUNT(*) FILTER (WHERE s.dtn_id = 1 AND s.field = 'retail_price') AS returns_qty
                FROM sales s
                WHERE s.field = 'retail_price'
                AND s.date_from >= CURRENT_DATE - INTERVAL '90 days'
                GROUP BY s.nm_id
            ),
            sku_metrics AS (
                SELECT
                    b.nm_id,
                    COALESCE(c.subject_name, 'Не указана') AS subject_name,
                    b.sales_amount,
                    b.returns_amount,
                    b.sales_qty,
                    b.returns_qty,
                    (b.sales_amount - b.returns_amount) AS net_amount,
                    (b.sales_qty - b.returns_qty) AS net_qty,
                    CASE
                        WHEN b.sales_qty > 0 THEN b.sales_amount / b.sales_qty
                        ELSE NULL
                    END AS avg_price
                FROM sku_base b
                LEFT JOIN cards_dim c
                    ON b.nm_id = c.nm_id
                WHERE b.sales_qty > 0
            ),
            top_categories AS (
                SELECT
                    subject_name
                FROM (
                    SELECT
                        subject_name,
                        SUM(sales_amount) AS sales_amount
                    FROM sku_metrics
                    GROUP BY 1
                    ORDER BY sales_amount DESC
                    LIMIT 15
                )
            ),
            ranked AS (
                SELECT
                    *,
                    NTILE(3) OVER (
                        PARTITION BY subject_name
                        ORDER BY avg_price
                    ) AS price_tile
                FROM sku_metrics
                WHERE subject_name IN (SELECT subject_name FROM top_categories)
            ),
            segment_agg AS (
                SELECT
                    subject_name,
                    CASE
                        WHEN price_tile = 1 THEN 'Low'
                        WHEN price_tile = 2 THEN 'Medium'
                        ELSE 'High'
                    END AS price_segment,
                    COUNT(*) AS sku_count,
                    SUM(sales_amount) AS sales_amount,
                    SUM(returns_amount) AS returns_amount,
                    SUM(net_amount) AS net_amount,
                    SUM(sales_qty) AS sales_qty,
                    SUM(returns_qty) AS returns_qty,
                    ROUND(AVG(avg_price), 2) AS avg_sku_price,
                    ROUND(MEDIAN(avg_price), 2) AS median_sku_price,
                    ROUND(MIN(avg_price), 2) AS min_sku_price,
                    ROUND(MAX(avg_price), 2) AS max_sku_price,
                    ROUND(MIN(avg_price), 2) AS segment_price_from,
                    ROUND(MAX(avg_price), 2) AS segment_price_to
                FROM ranked
                GROUP BY 1, 2
            )
            SELECT
                subject_name,
                price_segment,
                sku_count,
                sales_amount,
                returns_amount,
                net_amount,
                sales_qty,
                returns_qty,
                ROUND(100.0 * returns_qty / NULLIF(sales_qty, 0), 2) AS return_rate_pct,
                avg_sku_price,
                median_sku_price,
                min_sku_price,
                max_sku_price,
                segment_price_from,
                segment_price_to,
                ROUND(
                    100.0 * sales_amount
                    / NULLIF(SUM(sales_amount) OVER (PARTITION BY subject_name), 0),
                    2
                ) AS category_sales_share_pct
            FROM segment_agg
            ORDER BY subject_name, 
                    CASE price_segment
                        WHEN 'Low' THEN 1
                        WHEN 'Medium' THEN 2
                        ELSE 3
                    END
        """

    segment_rows = conn.execute(segment_query).df().to_dict("records")
    conn.close()

    # ------------------------------------------------------------------
    # Форматирование основной таблицы категорий
    # ------------------------------------------------------------------
    for row in category_rows:
        row["subject_name"] = row.get("subject_name") or "Не указана"

        sales_amount = float(row.get("sales_amount", 0) or 0)
        returns_amount = float(row.get("returns_amount", 0) or 0)
        net_amount = float(row.get("net_amount", 0) or 0)

        sales_qty = int(row.get("sales_qty", 0) or 0)
        returns_qty = int(row.get("returns_qty", 0) or 0)
        net_qty = int(row.get("net_qty", 0) or 0)

        row["sales_amount_fmt"] = _format_money(sales_amount)
        row["returns_amount_fmt"] = _format_money(returns_amount)
        row["net_amount_fmt"] = _format_money(net_amount)

        row["sales_qty_fmt"] = _format_int(sales_qty)
        row["returns_qty_fmt"] = _format_int(returns_qty)
        row["net_qty_fmt"] = _format_int(net_qty)

        row["return_rate_pct"] = f"{float(row.get('return_rate_pct', 0) or 0):.2f}"
        row["revenue_share_pct"] = f"{float(row.get('revenue_share_pct', 0) or 0):.2f}"

    # ------------------------------------------------------------------
    # Форматирование статистики цен по категориям
    # ------------------------------------------------------------------
    price_stats_map: dict[str, dict[str, Any]] = {}

    for row in price_stats_by_category:
        subject_name = row.get("subject_name") or "Не указана"

        avg_sku_price = float(row.get("avg_sku_price", 0) or 0)
        median_sku_price = float(row.get("median_sku_price", 0) or 0)
        min_sku_price = float(row.get("min_sku_price", 0) or 0)
        max_sku_price = float(row.get("max_sku_price", 0) or 0)

        row["avg_sku_price_fmt"] = _format_money(avg_sku_price)
        row["median_sku_price_fmt"] = _format_money(median_sku_price)
        row["min_sku_price_fmt"] = _format_money(min_sku_price)
        row["max_sku_price_fmt"] = _format_money(max_sku_price)

        price_stats_map[subject_name] = row

    for row in category_rows:
        subject_name = row["subject_name"]
        ps = price_stats_map.get(subject_name, {})

        row["avg_sku_price"] = float(ps.get("avg_sku_price", 0) or 0)
        row["median_sku_price"] = float(ps.get("median_sku_price", 0) or 0)
        row["min_sku_price"] = float(ps.get("min_sku_price", 0) or 0)
        row["max_sku_price"] = float(ps.get("max_sku_price", 0) or 0)
        row["sku_count"] = int(ps.get("sku_count", 0) or 0)

        row["avg_sku_price_fmt"] = ps.get("avg_sku_price_fmt", _format_money(0))
        row["median_sku_price_fmt"] = ps.get("median_sku_price_fmt", _format_money(0))
        row["min_sku_price_fmt"] = ps.get("min_sku_price_fmt", _format_money(0))
        row["max_sku_price_fmt"] = ps.get("max_sku_price_fmt", _format_money(0))
        row["sku_count_fmt"] = _format_int(row["sku_count"])

    # ------------------------------------------------------------------
    # Форматирование сегментов
    # ------------------------------------------------------------------
    for row in segment_rows:
        row["subject_name"] = row.get("subject_name") or "Не указана"
        row["price_segment"] = row.get("price_segment") or "—"

        row["sales_amount_fmt"] = _format_money(row.get("sales_amount", 0))
        row["returns_amount_fmt"] = _format_money(row.get("returns_amount", 0))
        row["net_amount_fmt"] = _format_money(row.get("net_amount", 0))

        row["avg_sku_price_fmt"] = _format_money(row.get("avg_sku_price", 0))
        row["median_sku_price_fmt"] = _format_money(row.get("median_sku_price", 0))
        row["min_sku_price_fmt"] = _format_money(row.get("min_sku_price", 0))
        row["max_sku_price_fmt"] = _format_money(row.get("max_sku_price", 0))

        row["segment_price_from_fmt"] = _format_money(row.get("segment_price_from", 0))
        row["segment_price_to_fmt"] = _format_money(row.get("segment_price_to", 0))
        row["segment_price_range_fmt"] = (
            f"{row['segment_price_from_fmt']} – {row['segment_price_to_fmt']}"
        )

        row["sales_qty_fmt"] = _format_int(row.get("sales_qty", 0))
        row["returns_qty_fmt"] = _format_int(row.get("returns_qty", 0))
        row["sku_count_fmt"] = _format_int(row.get("sku_count", 0))

        row["return_rate_pct"] = f"{float(row.get('return_rate_pct', 0) or 0):.2f}"
        row["category_sales_share_pct"] = f"{float(row.get('category_sales_share_pct', 0) or 0):.2f}"
    # ------------------------------------------------------------------
    # Общая справка по ценам
    # ------------------------------------------------------------------
    overall_price_stats = None
    category_avg_prices = [
        float(r.get("avg_sku_price", 0) or 0)
        for r in price_stats_by_category
        if float(r.get("avg_sku_price", 0) or 0) > 0
    ]

    if category_avg_prices:
        overall_price_stats = {
            "avg_category_price": _format_money(np.mean(category_avg_prices)),
            "median_category_price": _format_money(np.median(category_avg_prices)),
            "min_category_price": _format_money(np.min(category_avg_prices)),
            "max_category_price": _format_money(np.max(category_avg_prices)),
        }

    return {
        "rows": category_rows,
        "price_stats_by_category": price_stats_by_category,
        "segment_rows": segment_rows,
        "overall_price_stats": overall_price_stats,
    }

def get_certificate_risks() -> list:
    conn = get_duckdb_conn()


    query = """
        WITH cards_latest AS (
            SELECT *
            FROM (
                SELECT
                    nm_id,
                    payload_raw,
                    loaded_at,
                    ROW_NUMBER() OVER (PARTITION BY nm_id ORDER BY loaded_at DESC) AS rn
                FROM cards
            ) t
            WHERE rn = 1
        ),
        exploded AS (
            SELECT
                c.nm_id,
                json_extract_string(c.payload_raw, '$.title') AS product_name,
                json_extract_string(c.payload_raw, '$.brand') AS brand,
                json_extract_string(c.payload_raw, '$.subjectName') AS subject_name,
                json_extract_string(c.payload_raw, '$.vendorCode') AS vendor_code,
                json_extract_string(c.payload_raw, '$.photos[0].big') AS photo_url,
                je.value AS characteristic_json
            FROM cards_latest c,
            json_each(json_extract(c.payload_raw, '$.characteristics')) AS je
        ),
        cert_end AS (
            SELECT
                nm_id,
                product_name,
                brand,
                subject_name,
                vendor_code,
                photo_url,
                json_extract_string(characteristic_json, '$.name') AS char_name,
                json_extract_string(characteristic_json, '$.value[0]') AS cert_expiry_raw
            FROM exploded
        ),
        cert_filtered AS (
            SELECT
                nm_id,
                product_name,
                brand,
                subject_name,
                vendor_code,
                photo_url,
                cert_expiry_raw,
                TRY_STRPTIME(cert_expiry_raw, '%d.%m.%Y')::DATE AS cert_expiry_date
            FROM cert_end
            WHERE char_name = 'Дата окончания действия сертификата/декларации'
        ),
        sales_90d AS (
            SELECT
                nm_id,
                SUM(CASE WHEN dtn_id = 2 AND field = 'retail_price' THEN value ELSE 0 END) / 100.0 AS sales_amount_90d,
                COUNT(*) FILTER (WHERE dtn_id = 2 AND field = 'retail_price') AS sales_qty_90d
            FROM sales
            WHERE field = 'retail_price'
              AND date_from >= CURRENT_DATE - INTERVAL '90 days'
            GROUP BY nm_id
        )
        SELECT
            c.nm_id,
            c.product_name,
            c.brand,
            c.subject_name,
            c.vendor_code,
            c.photo_url,
            c.cert_expiry_raw,
            c.cert_expiry_date,
            DATE_DIFF('day', CURRENT_DATE, c.cert_expiry_date) AS days_to_expiry,
            s.sales_amount_90d,
            s.sales_qty_90d
        FROM cert_filtered c
        INNER JOIN sales_90d s
            ON c.nm_id = s.nm_id
        WHERE c.cert_expiry_date IS NOT NULL
          AND c.cert_expiry_date <= CURRENT_DATE + INTERVAL '180 days'
          AND COALESCE(s.sales_qty_90d, 0) > 0
        ORDER BY s.sales_amount_90d DESC, c.cert_expiry_date ASC
        LIMIT 100
    """

    result = conn.execute(query).df().to_dict("records")
    conn.close()

    for row in result:
        row["nm_id_str"] = str(row.get("nm_id") or "")
        row["product_name"] = row.get("product_name") or "—"
        row["brand"] = row.get("brand") or "—"
        row["subject_name"] = row.get("subject_name") or "—"
        row["vendor_code"] = row.get("vendor_code") or "—"
        row["cert_expiry_raw"] = row.get("cert_expiry_raw") or "—"
        row["photo_url"] = row.get("photo_url") or ""
        row["photo_label"] = "Фото" if row["photo_url"] else "—"
        row["sales_amount_90d_fmt"] = _format_money(row.get("sales_amount_90d", 0))
        row["sales_qty_90d_fmt"] = _format_int(row.get("sales_qty_90d", 0))

        days = row.get("days_to_expiry")
        if days is None:
            row["risk_level"] = "Не определено"
            row["risk_class"] = ""
        elif days < 0:
            row["risk_level"] = "Истек"
            row["risk_class"] = "negative"
        elif days <= 30:
            row["risk_level"] = "Критично"
            row["risk_class"] = "negative"
        elif days <= 90:
            row["risk_level"] = "Высокий риск"
            row["risk_class"] = "warning"
        else:
            row["risk_level"] = "Контроль"
            row["risk_class"] = "neutral"

    return result


def get_sales_by_country() -> list:
    conn = get_duckdb_conn()

    query = """
        WITH country_sales AS (
            SELECT
                COALESCE(country_id, 0) AS country_id,
                SUM(
                    CASE
                        WHEN dtn_id = 2 AND field = 'retail_price'
                        THEN value
                        ELSE 0
                    END
                ) / 100.0 AS sales_amount,
                SUM(
                    CASE
                        WHEN dtn_id = 1 AND field = 'retail_price'
                        THEN value
                        ELSE 0
                    END
                ) / 100.0 AS returns_amount,
                COUNT(*) FILTER (
                    WHERE dtn_id = 2 AND field = 'retail_price'
                ) AS sales_qty,
                COUNT(*) FILTER (
                    WHERE dtn_id = 1 AND field = 'retail_price'
                ) AS returns_qty
            FROM sales
            WHERE field = 'retail_price'
              AND date_from >= CURRENT_DATE - INTERVAL '90 days'
            GROUP BY COALESCE(country_id, 0)
        ),
        prepared AS (
            SELECT
                country_id,
                sales_amount,
                returns_amount,
                sales_qty,
                returns_qty,
                (sales_amount - returns_amount) AS net_amount,
                (sales_qty - returns_qty) AS net_qty,
                ROUND(100.0 * returns_amount / NULLIF(sales_amount, 0), 2) AS return_rate_amount_pct,
                ROUND(100.0 * returns_qty / NULLIF(sales_qty, 0), 2) AS return_rate_qty_pct
            FROM country_sales
        ),
        total AS (
            SELECT SUM(net_amount) AS total_net_amount
            FROM prepared
        )
        SELECT
            p.country_id,
            cc.name AS country_name,
            cc.code AS country_code,
            cc.emojy_flag AS emoji_flag,
            p.sales_amount,
            p.returns_amount,
            p.net_amount,
            p.sales_qty,
            p.returns_qty,
            p.net_qty,
            p.return_rate_amount_pct,
            p.return_rate_qty_pct,
            ROUND(
                100.0 * p.net_amount / NULLIF(t.total_net_amount, 0),
                2
            ) AS share_pct
        FROM prepared p
        LEFT JOIN pg.public.corporate_countries cc
            ON p.country_id = cc.id
        CROSS JOIN total t
        WHERE p.sales_amount > 0
        ORDER BY p.net_amount DESC
        LIMIT 10
    """

    result = conn.execute(query).df().to_dict("records")
    conn.close()

    for row in result:
        row["country_name"] = row.get("country_name") or "Не указана"
        row["country_code"] = row.get("country_code") or ""
        row["emoji_flag"] = row.get("emoji_flag") or ""

        row["sales_amount_fmt"] = _format_money(row.get("sales_amount", 0))
        row["returns_amount_fmt"] = _format_money(row.get("returns_amount", 0))
        row["net_amount_fmt"] = _format_money(row.get("net_amount", 0))

        row["sales_qty_fmt"] = _format_int(row.get("sales_qty", 0))
        row["returns_qty_fmt"] = _format_int(row.get("returns_qty", 0))
        row["net_qty_fmt"] = _format_int(row.get("net_qty", 0))

        row["share_pct"] = f"{row.get('share_pct', 0):.2f}"
        row["return_rate_amount_pct"] = f"{row.get('return_rate_amount_pct', 0):.2f}"
        row["return_rate_qty_pct"] = f"{row.get('return_rate_qty_pct', 0):.2f}"

    return result


def get_weekly_trends() -> list:
    conn = get_duckdb_conn()

    query = """
        SELECT
            DATE_TRUNC('week', CAST(date_from AS DATE)) AS week_start,
            SUM(CASE WHEN dtn_id = 2 AND field = 'retail_price' THEN value ELSE 0 END) / 100.0 AS sales_amount,
            SUM(CASE WHEN dtn_id = 1 AND field = 'retail_price' THEN value ELSE 0 END) / 100.0 AS returns_amount,
            COUNT(*) FILTER (WHERE dtn_id = 2 AND field = 'retail_price') AS sales_qty,
            COUNT(*) FILTER (WHERE dtn_id = 1 AND field = 'retail_price') AS returns_qty
        FROM sales
        WHERE field = 'retail_price'
          AND CAST(date_from AS DATE) >= CURRENT_DATE - INTERVAL '90 days'
        GROUP BY 1
        ORDER BY 1
    """
    df = conn.execute(query).df()
    conn.close()

    if df.empty:
        return []

    df["week_start"] = pd.to_datetime(df["week_start"])
    df["week_end"] = df["week_start"] + pd.Timedelta(days=6)

    df["sales_amount"] = df["sales_amount"].fillna(0.0)
    df["returns_amount"] = df["returns_amount"].fillna(0.0)
    df["sales_qty"] = df["sales_qty"].fillna(0).astype(int)
    df["returns_qty"] = df["returns_qty"].fillna(0).astype(int)

    df["net_amount"] = df["sales_amount"] - df["returns_amount"]
    df["net_qty"] = df["sales_qty"] - df["returns_qty"]

    df["avg_price"] = 0.0
    mask = df["sales_qty"] > 0
    df.loc[mask, "avg_price"] = df.loc[mask, "sales_amount"] / df.loc[mask, "sales_qty"]

    df["week_label"] = (
        df["week_start"].dt.strftime("%d.%m.%Y")
        + " – " +
        df["week_end"].dt.strftime("%d.%m.%Y")
    )

    # Для блока берем последние 12 недель
    df = df.tail(12).copy()

    max_net = df["net_amount"].max() if not df.empty else 0
    df["net_fill_pct"] = ((df["net_amount"] / max_net) * 100).round(1) if max_net else 0

    result = df.to_dict("records")

    for row in result:
        row["sales_amount_fmt"] = _format_money(row.get("sales_amount", 0))
        row["returns_amount_fmt"] = _format_money(row.get("returns_amount", 0))
        row["net_amount_fmt"] = _format_money(row.get("net_amount", 0))

        row["sales_qty_fmt"] = _format_int(row.get("sales_qty", 0))
        row["returns_qty_fmt"] = _format_int(row.get("returns_qty", 0))
        row["net_qty_fmt"] = _format_int(row.get("net_qty", 0))

        row["avg_price_fmt"] = _format_money(row.get("avg_price", 0))

    return result