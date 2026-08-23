# inventories/reporting/map/__init__.py
from .stock_map_generator import StockMapGenerator
from .russia_regions_map import build_russia_regions_map

__all__ = ['StockMapGenerator', 'build_russia_regions_map']