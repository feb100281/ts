from __future__ import annotations

from budget.reporting.pdf.services.sales_data_service import _format_money
from conns import get_duckdb_conn


def get_certificate_risks_by_category(limit: int = 10) -> list[dict]:
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
                json_extract_string(c.payload_raw, '$.subjectName') AS subject_name,
                je.value AS characteristic_json
            FROM cards_latest c,
            json_each(json_extract(c.payload_raw, '$.characteristics')) AS je
        ),
        cert_end AS (
            SELECT
                nm_id,
                COALESCE(subject_name, 'Не указана') AS subject_name,
                json_extract_string(characteristic_json, '$.name') AS char_name,
                json_extract_string(characteristic_json, '$.value[0]') AS cert_expiry_raw
            FROM exploded
        ),
        cert_filtered AS (
            SELECT
                nm_id,
                subject_name,
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
        ),
        risk_base AS (
            SELECT
                c.nm_id,
                c.subject_name,
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
        )
        SELECT
            subject_name,
            COUNT(*) AS sku_count,
            SUM(sales_amount_90d) AS sales_amount_90d,
            SUM(sales_qty_90d) AS sales_qty_90d,
            SUM(CASE WHEN days_to_expiry < 0 THEN 1 ELSE 0 END) AS expired_count,
            SUM(CASE WHEN days_to_expiry BETWEEN 0 AND 30 THEN 1 ELSE 0 END) AS critical_count,
            SUM(CASE WHEN days_to_expiry BETWEEN 31 AND 90 THEN 1 ELSE 0 END) AS high_count,
            SUM(CASE WHEN days_to_expiry BETWEEN 91 AND 180 THEN 1 ELSE 0 END) AS control_count
        FROM risk_base
        GROUP BY 1
        ORDER BY sales_amount_90d DESC
        LIMIT ?
    """

    result = conn.execute(query, [limit]).df().to_dict("records")
    conn.close()

    total_sales = sum(float(r.get("sales_amount_90d", 0) or 0) for r in result)

    for row in result:
        sales_amount = float(row.get("sales_amount_90d", 0) or 0)
        row["subject_name"] = row.get("subject_name") or "Не указана"
        row["sku_count"] = int(row.get("sku_count", 0) or 0)
        row["sales_qty_90d"] = int(row.get("sales_qty_90d", 0) or 0)

        row["sales_amount_90d_fmt"] = _format_money(sales_amount)
        row["sales_qty_90d_fmt"] = f"{int(row['sales_qty_90d']):,}".replace(",", " ")
        row["share_pct"] = round((sales_amount / total_sales * 100), 2) if total_sales else 0.0

    return result


def build_certificate_category_comment(rows: list[dict]) -> dict | None:
    if not rows:
        return None

    leader = rows[0]
    top3_share = sum(float(r.get("share_pct", 0) or 0) for r in rows[:3])

    comment = (
        f"Наибольшая концентрация риска приходится на категорию "
        f"{leader.get('subject_name')}: {leader.get('sales_amount_90d_fmt')} руб. продаж за последние 90 дней "
        f"и {leader.get('sku_count')} SKU под риском. "
        f"Суммарно три крупнейшие категории формируют {top3_share:.1f}% продаж в риск-зоне."
    )

    return {
        "comment": comment,
        "leader_category": leader.get("subject_name"),
        "leader_sales_90d_fmt": leader.get("sales_amount_90d_fmt"),
        "top3_share_pct": f"{top3_share:.1f}",
    }