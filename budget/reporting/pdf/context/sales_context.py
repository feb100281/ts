from budget.reporting.pdf.analytics.sales_analytics import (
    build_daily_correlation_context,
    build_qty_price_auto_comment,
    build_sales_auto_comment,
    build_sales_correlation_context,
)
from budget.reporting.pdf.charts.daily_qty_price_scatter_chart import (
    build_daily_qty_price_scatter_base64,
)
from budget.reporting.pdf.charts.qty_price_12m_chart import (
    build_qty_price_12m_chart_base64,
)
from budget.reporting.pdf.charts.qty_price_scatter_chart import (
    build_qty_price_scatter_base64,
)
from budget.reporting.pdf.charts.revenue_waterfall_chart import (
    build_revenue_waterfall_base64,
)
from budget.reporting.pdf.charts.sales_12m_chart import (
    build_sales_12m_chart_base64,
)

from budget.reporting.pdf.services.sales_data_service import (
    get_certificate_risks,
    get_sales_by_category,
    get_sales_by_country,
    get_top_nm_ids,
    get_weekly_trends,
)
from budget.reporting.pdf.charts.sales_country_map_chart import (
    build_sales_country_map_base64,
)
from budget.reporting.pdf.charts.weekly_trends_chart import (
    build_weekly_trends_chart_base64,
)
from budget.reporting.pdf.charts.weekly_qty_chart import (
    build_weekly_qty_chart_base64,
)
from budget.reporting.pdf.charts.weekly_avg_price_chart import (
    build_weekly_avg_price_chart_base64,
)

from budget.reporting.pdf.services.weekly_comment_service import (
    build_weekly_extended_comment,
)
from budget.reporting.pdf.services.monthly_comment_service import (
    build_monthly_extended_comment,
)
from budget.reporting.pdf.services.country_comment_service import (
    build_country_extended_comment,
)
from budget.reporting.pdf.services.certificate_comment_service import (
    build_certificate_risk_comment,
)
from budget.reporting.pdf.services.certificate_category_service import (
    get_certificate_risks_by_category,
    build_certificate_category_comment,
)
from budget.reporting.pdf.charts.certificate_risk_chart import (
    build_certificate_risk_chart_base64,
)
from budget.reporting.pdf.charts.certificate_category_risk_chart import (
    build_certificate_category_risk_chart_base64,
)

from budget.reporting.pdf.services.category_comment_service import build_category_summary
from budget.reporting.pdf.charts.category_revenue_chart import build_category_revenue_chart_base64
from budget.reporting.pdf.charts.category_risk_matrix_chart import build_category_risk_matrix_chart_base64
from budget.reporting.pdf.charts.category_segment_structure_chart import build_category_segment_structure_chart_base64
from budget.reporting.pdf.charts.category_gross_net_chart import (build_category_gross_net_chart_base64)

from budget.reporting.pdf.services.sales_kpi_service import build_sales_kpi_context


def build_sales_pdf_block() -> dict:
    sales_context = build_sales_kpi_context()
    sales_block = sales_context.get("sales_block")

    sales_chart_base64 = None
    qty_price_chart_base64 = None
    qty_price_combo_chart_base64 = None
    qty_price_daily_chart_base64 = None
    revenue_waterfall_base64 = None
    sales_correlations = None
    daily_correlation = None
    sales_auto_comment = None
    qty_price_auto_comment = None
    monthly_comment = None

    if sales_block and sales_block.get("months_12"):
        months_12 = sales_block["months_12"]

        sales_chart_base64 = build_sales_12m_chart_base64(months_12)
        qty_price_chart_base64 = build_qty_price_scatter_base64(months_12)
        qty_price_combo_chart_base64 = build_qty_price_12m_chart_base64(months_12)
        revenue_waterfall_base64 = build_revenue_waterfall_base64(
            sales_block.get("waterfall_data")
        )

        sales_correlations = build_sales_correlation_context(months_12)
        sales_auto_comment = build_sales_auto_comment(months_12)
        qty_price_auto_comment = build_qty_price_auto_comment(months_12)
        monthly_comment = build_monthly_extended_comment(months_12)

    if sales_block and sales_block.get("daily_rows_90"):
        daily_rows_90 = sales_block["daily_rows_90"]
        qty_price_daily_chart_base64 = build_daily_qty_price_scatter_base64(daily_rows_90)
        daily_correlation = build_daily_correlation_context(daily_rows_90)

    top_data = get_top_nm_ids()
    top_products = top_data.get("top_products", [])
    top_returns = top_data.get("top_returns", [])
    old_skus = top_data.get("old_skus", [])
    top_period_from = top_data.get("top_period_from", "—")
    top_period_to = top_data.get("top_period_to", "—")

    category_data = get_sales_by_category()
    category_rows = category_data.get("rows", [])
    segment_rows = category_data.get("segment_rows", [])
    price_stats_by_category = category_data.get("price_stats_by_category", [])
    overall_price_stats = category_data.get("overall_price_stats")

    category_summary = build_category_summary(
        category_rows,
        segment_rows=segment_rows,
    )

    category_revenue_chart_base64 = build_category_revenue_chart_base64(category_rows)
    category_risk_matrix_chart_base64 = build_category_risk_matrix_chart_base64(category_rows)
    category_segment_structure_chart_base64 = build_category_segment_structure_chart_base64(segment_rows)
    category_gross_net_chart_base64 = build_category_gross_net_chart_base64(category_rows)

    certificate_risks = get_certificate_risks()
    certificate_comment = build_certificate_risk_comment(certificate_risks)
    certificate_risk_chart_base64 = build_certificate_risk_chart_base64(certificate_risks)

    certificate_risk_categories = get_certificate_risks_by_category(limit=8)
    certificate_category_comment = build_certificate_category_comment(certificate_risk_categories)
    certificate_category_risk_chart_base64 = build_certificate_category_risk_chart_base64(
        certificate_risk_categories
    )

    sales_by_country = get_sales_by_country()
    country_comment = build_country_extended_comment(sales_by_country)

    weekly_trends = get_weekly_trends()
    weekly_comment = build_weekly_extended_comment(weekly_trends)
    weekly_trends_chart_base64 = build_weekly_trends_chart_base64(weekly_trends)
    weekly_qty_chart_base64 = build_weekly_qty_chart_base64(weekly_trends)
    weekly_avg_price_chart_base64 = build_weekly_avg_price_chart_base64(weekly_trends)

    sales_country_map_base64 = build_sales_country_map_base64(
        sales_by_country,
        label_mode="share",
    )

    return {
        "sales_block": sales_block,
        "sales_chart_base64": sales_chart_base64,
        "qty_price_chart_base64": qty_price_chart_base64,
        "qty_price_combo_chart_base64": qty_price_combo_chart_base64,
        "qty_price_daily_chart_base64": qty_price_daily_chart_base64,
        "revenue_waterfall_base64": revenue_waterfall_base64,
        "sales_correlations": sales_correlations,
        "daily_correlation": daily_correlation,
        "sales_auto_comment": sales_auto_comment,
        "qty_price_auto_comment": qty_price_auto_comment,
        "monthly_comment": monthly_comment,

        "top_products": top_products,
        "top_returns": top_returns,
        "old_skus": old_skus,
        "top_period_from": top_period_from,
        "top_period_to": top_period_to,

        "category_rows": category_rows,
        "segment_rows": segment_rows,
        "price_stats_by_category": price_stats_by_category,
        "overall_price_stats": overall_price_stats,
        "category_summary": category_summary,
        "category_revenue_chart_base64": category_revenue_chart_base64,
        "category_risk_matrix_chart_base64": category_risk_matrix_chart_base64,
        "category_segment_structure_chart_base64": category_segment_structure_chart_base64,
        "category_gross_net_chart_base64": category_gross_net_chart_base64,

        "certificate_risks": certificate_risks,
        "certificate_comment": certificate_comment,
        "certificate_risk_chart_base64": certificate_risk_chart_base64,
        "certificate_risk_categories": certificate_risk_categories,
        "certificate_category_comment": certificate_category_comment,
        "certificate_category_risk_chart_base64": certificate_category_risk_chart_base64,

        "sales_by_country": sales_by_country,
        "country_comment": country_comment,
        "weekly_trends": weekly_trends,
        "weekly_comment": weekly_comment,
        "weekly_trends_chart_base64": weekly_trends_chart_base64,
        "weekly_qty_chart_base64": weekly_qty_chart_base64,
        "weekly_avg_price_chart_base64": weekly_avg_price_chart_base64,
        "sales_country_map_base64": sales_country_map_base64,
    }