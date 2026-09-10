# gear/app/daily_sales/stocks/dashboard.py
"""Точка входа dashboard остатков."""

from .dashboard_stock import (
    StocksDashboard,
    register_stock_dashboard_callbacks,
)

__all__ = [
    "StocksDashboard",
    "register_stock_dashboard_callbacks",
]
