import pandas as pd

from .data import (
    get_stocks_by_warehouse_extended,
    get_stocks_summary_stats,
)

# ВАЖНО:
# путь поправь под свой проект, если импорт отличается
from inventories.reporting.map.russia_regions_map import build_regions_stock_map_png


def make_stocks_regions_map_png(report_date) -> bytes:
    region_stats = get_stocks_by_warehouse_extended(report_date)
    summary_stats = get_stocks_summary_stats(report_date)

    if region_stats.empty:
        return b""

    report_date_str = pd.to_datetime(report_date).strftime("%d.%m.%Y")

    buffer = build_regions_stock_map_png(
        region_stats=region_stats,
        report_date=report_date_str,
        summary_stats=summary_stats,
    )

    buffer.seek(0)
    return buffer.read()