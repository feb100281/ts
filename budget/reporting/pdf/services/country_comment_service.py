from __future__ import annotations

from typing import Any

from budget.reporting.pdf.services.sales_data_service import _format_money
from conns import get_duckdb_conn


def get_country_top_categories(country_id: int, limit: int = 3) -> list[dict]:
    conn = get_duckdb_conn()

    query = """
        WITH cards_dim AS (
            SELECT
                nm_id,
                ANY_VALUE(json_extract_string(payload_raw, '$.subjectName')) AS subject_name
            FROM cards
            GROUP BY nm_id
        ),
        base AS (
            SELECT
                s.nm_id,
                SUM(CASE WHEN s.dtn_id = 2 AND s.field = 'retail_price' THEN s.value ELSE 0 END) / 100.0 AS sales_amount,
                SUM(CASE WHEN s.dtn_id = 1 AND s.field = 'retail_price' THEN s.value ELSE 0 END) / 100.0 AS returns_amount
            FROM sales s
            WHERE s.field = 'retail_price'
              AND s.date_from >= CURRENT_DATE - INTERVAL '90 days'
              AND COALESCE(s.country_id, 0) = ?
            GROUP BY s.nm_id
        )
        SELECT
            COALESCE(c.subject_name, 'Не указана') AS subject_name,
            SUM(b.sales_amount - b.returns_amount) AS net_amount
        FROM base b
        LEFT JOIN cards_dim c
            ON b.nm_id = c.nm_id
        GROUP BY 1
        HAVING SUM(b.sales_amount - b.returns_amount) > 0
        ORDER BY net_amount DESC
        LIMIT ?
    """

    rows = conn.execute(query, [country_id, limit]).df().to_dict("records")
    conn.close()

    return [
        {
            **row,
            "subject_name": row.get("subject_name") or "Не указана",
            "net_amount_fmt": _format_money(row.get("net_amount", 0)),
        }
        for row in rows
    ]


def get_country_top_products(country_id: int, limit: int = 3) -> list[dict]:
    conn = get_duckdb_conn()

    query = """
        WITH product_dim AS (
            SELECT
                nm_id,
                ANY_VALUE(title) AS product_name,
                ANY_VALUE(brand) AS brand
            FROM product
            GROUP BY nm_id
        ),
        base AS (
            SELECT
                s.nm_id,
                SUM(CASE WHEN s.dtn_id = 2 AND s.field = 'retail_price' THEN s.value ELSE 0 END) / 100.0 AS sales_amount,
                SUM(CASE WHEN s.dtn_id = 1 AND s.field = 'retail_price' THEN s.value ELSE 0 END) / 100.0 AS returns_amount
            FROM sales s
            WHERE s.field = 'retail_price'
              AND s.date_from >= CURRENT_DATE - INTERVAL '90 days'
              AND COALESCE(s.country_id, 0) = ?
            GROUP BY s.nm_id
        )
        SELECT
            b.nm_id,
            COALESCE(p.product_name, '—') AS product_name,
            COALESCE(p.brand, '—') AS brand,
            (b.sales_amount - b.returns_amount) AS net_amount
        FROM base b
        LEFT JOIN product_dim p
            ON b.nm_id = p.nm_id
        WHERE (b.sales_amount - b.returns_amount) > 0
        ORDER BY net_amount DESC
        LIMIT ?
    """

    rows = conn.execute(query, [country_id, limit]).df().to_dict("records")
    conn.close()

    return [
        {
            **row,
            "product_name": row.get("product_name") or "—",
            "brand": row.get("brand") or "—",
            "net_amount_fmt": _format_money(row.get("net_amount", 0)),
        }
        for row in rows
    ]


def build_country_comment(sales_by_country: list[dict[str, Any]]) -> dict | None:
    if not sales_by_country:
        return None

    rows = [row for row in sales_by_country if float(row.get("sales_amount", 0) or 0) > 0]
    if not rows:
        return None

    rows_sorted_net = sorted(rows, key=lambda x: float(x.get("net_amount", 0) or 0), reverse=True)
    rows_sorted_returns_amt = sorted(
        rows, key=lambda x: float(x.get("return_rate_amount_pct", 0) or 0), reverse=True
    )
    rows_sorted_returns_qty = sorted(
        rows, key=lambda x: float(x.get("return_rate_qty_pct", 0) or 0), reverse=True
    )

    leader = rows_sorted_net[0]
    top_3_share = sum(float(row.get("share_pct", 0) or 0) for row in rows_sorted_net[:3])

    worst_return_amt = rows_sorted_returns_amt[0]
    worst_return_qty = rows_sorted_returns_qty[0]
    lowest_return_amt = min(rows, key=lambda x: float(x.get("return_rate_amount_pct", 0) or 0))

    leader_name = leader.get("country_name") or "Не указана"
    leader_share = float(leader.get("share_pct", 0) or 0)

    concentration_text = (
        "География продаж остается концентрированной."
        if top_3_share >= 70
        else "География продаж остается умеренно диверсифицированной."
        if top_3_share >= 45
        else "География продаж выглядит достаточно диверсифицированной."
    )

    comment = (
        f"Лидирующей страной по чистой выручке за последние 90 дней является "
        f"{leader_name}: {leader.get('net_amount_fmt')} руб., или {leader_share:.2f}% совокупной чистой выручки. "
        f"Суммарная доля трех крупнейших стран составляет {top_3_share:.2f}%. "
        f"Наиболее высокий уровень возвратов по сумме зафиксирован по стране "
        f"{worst_return_amt.get('country_name')}: {worst_return_amt.get('return_rate_amount_pct')}% от оборота, "
        f"а по количеству — по стране {worst_return_qty.get('country_name')}: "
        f"{worst_return_qty.get('return_rate_qty_pct')}% от количества продаж. "
        f"Минимальный уровень возвратов по сумме наблюдается по стране "
        f"{lowest_return_amt.get('country_name')}: {lowest_return_amt.get('return_rate_amount_pct')}%."
    )

    return {
        "comment": comment,
        "note": concentration_text,
        "leader_country": leader_name,
        "leader_share_pct": f"{leader_share:.2f}",
        "top_3_share_pct": f"{top_3_share:.2f}",
    }


def build_country_extended_comment(sales_by_country: list[dict[str, Any]]) -> dict | None:
    base = build_country_comment(sales_by_country)
    if not base:
        return None

    rows = [row for row in sales_by_country if float(row.get("net_amount", 0) or 0) > 0]
    rows_sorted_net = sorted(rows, key=lambda x: float(x.get("net_amount", 0) or 0), reverse=True)
    top_countries = rows_sorted_net[:3]

    country_insights = []

    for row in top_countries:
        country_id = int(row.get("country_id", 0) or 0)
        country_name = row.get("country_name") or "Не указана"
        emoji_flag = row.get("emoji_flag") or ""

        top_categories = get_country_top_categories(country_id, limit=3)
        top_products = get_country_top_products(country_id, limit=3)

        country_insights.append({
            "country_id": country_id,
            "country_name": country_name,
            "emoji_flag": emoji_flag,
            "net_amount_fmt": row.get("net_amount_fmt"),
            "share_pct": row.get("share_pct"),
            "top_categories": top_categories,
            "top_products": top_products,
        })

    return {
        **base,
        "country_insights": country_insights,
    }