"""Модульный dashboard остатков."""

from .layout import StocksDashboard
from .callbacks import register_main_callbacks
from .map_modal import register_map_modal_callbacks
from .warehouse_modal import register_warehouse_modal_callbacks
from .transfer_modal import register_transfer_modal_callbacks


def register_stock_dashboard_callbacks(app):
    register_main_callbacks(app)
    register_map_modal_callbacks(app)
    register_warehouse_modal_callbacks(app)
    register_transfer_modal_callbacks(app)


__all__ = [
    "StocksDashboard",
    "register_stock_dashboard_callbacks",
]
