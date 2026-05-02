# ### ЭТО ПО ГОРОДАМ 
# import io
# from datetime import datetime

# import pandas as pd

# from ..excel.queries.stocks_queries import StocksQueries
# from .russia_warehouses_map import build_warehouses_stock_map_png


# class StockMapGenerator:
#     """Генератор карты остатков по складам"""

#     def __init__(self):
#         self.queries = StocksQueries()

#     def load_data(self, report_date: str) -> pd.DataFrame:
#         """Загружает данные по складам"""
#         df = self.queries.get_stocks_by_warehouse(report_date)

#         warehouse_stats = (
#             df
#             .groupby("склад", as_index=False)
#             .agg({"итого": "sum"})
#             .sort_values("итого", ascending=False)
#         )

#         return warehouse_stats

#     def generate_png(self, report_date: str) -> io.BytesIO:
#         warehouse_stats = self.load_data(report_date)

#         date_obj = datetime.strptime(report_date, "%Y-%m-%d")
#         formatted_date = date_obj.strftime("%d.%m.%Y")

#         return build_warehouses_stock_map_png(
#             warehouse_stats=warehouse_stats,
#             report_date=formatted_date,
#         )




# # inventories/reporting/map/stock_map_generator.py
# import io
# from datetime import datetime
# import pandas as pd

# from ..excel.queries.stocks_queries import StocksQueries
# from .russia_regions_map import build_russia_regions_map


# class StockMapGenerator:
#     """Генератор карты остатков по регионам"""
    
#     def __init__(self):
#         self.queries = StocksQueries()
    
#     def load_data(self, report_date: str) -> pd.DataFrame:
#         df = self.queries.get_stocks_by_warehouse(report_date)

#         region_stats = (
#             df
#             .groupby("регион", as_index=False)
#             .agg({"итого": "sum"})
#             .sort_values("итого", ascending=False)
#         )

#         return region_stats
    
#     def generate_png(self, report_date: str) -> io.BytesIO:
#         """Генерирует карту остатков по регионам"""
#         # Загружаем данные
#         region_stats = self.load_data(report_date)
        
#         # Форматируем дату
#         date_obj = datetime.strptime(report_date, '%Y-%m-%d')
#         formatted_date = date_obj.strftime('%d.%m.%Y')
        
#         # Строим карту
#         return build_russia_regions_map(region_stats, formatted_date)



# # inventories/reporting/map/stock_map_generator.py
# import io
# from datetime import datetime
# import pandas as pd

# from ..excel.queries.stocks_queries import StocksQueries
# from .russia_regions_map import build_russia_regions_map


# class StockMapGenerator:
#     """Генератор карты остатков по регионам"""
    
#     def __init__(self):
#         self.queries = StocksQueries()
    
#     def load_data(self, report_date: str) -> pd.DataFrame:
#         # Используем расширенный запрос вместо старого
#         df = self.queries.get_stocks_by_warehouse_extended(report_date)
#         return df
    
#     def generate_png(self, report_date: str) -> io.BytesIO:
#         """Генерирует карту остатков по регионам"""
#         # Загружаем расширенные данные
#         region_stats = self.load_data(report_date)
        
#         # Форматируем дату
#         date_obj = datetime.strptime(report_date, '%Y-%m-%d')
#         formatted_date = date_obj.strftime('%d.%m.%Y')
        
#         # Строим карту
#         return build_russia_regions_map(region_stats, formatted_date)


# inventories/reporting/map/stock_map_generator.py
import io
from datetime import datetime
import pandas as pd

from ..excel.queries.stocks_queries import StocksQueries
from .russia_regions_map import build_russia_regions_map


class StockMapGenerator:
    """Генератор карты остатков по регионам"""

    def __init__(self):
        self.queries = StocksQueries()

    def load_data(self, report_date: str) -> pd.DataFrame:
        return self.queries.get_stocks_by_warehouse_extended(report_date)

    def generate_png(self, report_date: str) -> io.BytesIO:
        region_stats = self.load_data(report_date)

        date_obj = datetime.strptime(report_date, "%Y-%m-%d")
        formatted_date = date_obj.strftime("%d.%m.%Y")

        return build_russia_regions_map(region_stats, formatted_date)