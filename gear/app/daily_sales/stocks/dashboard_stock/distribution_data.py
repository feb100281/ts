"""Быстрый SQL-источник для вкладок распределения остатков."""

from __future__ import annotations

import pandas as pd

from ..data import get_stock_dimension_distributions


def get_dashboard_distributions(
    report_date: str,
    brand_list=None,
    cat_list=None,
    gender_list=None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Возвращает агрегаты брендов и категорий одним SQL-запросом."""
    return get_stock_dimension_distributions(
        report_date=report_date,
        brand_list=brand_list,
        cat_list=cat_list,
        gender_list=gender_list,
    )
