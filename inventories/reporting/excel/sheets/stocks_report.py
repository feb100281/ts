# inventories/reporting/excel/sheets/stocks_report.py
from io import BytesIO
from openpyxl import Workbook
from .toc_sheet import TOCSheet
from .detail_sheet import DetailSheet
from .category_sheet import CategorySheet
from .gender_sheet import GenderSheet
from .warehouse_sheet import WarehouseSheet
from .brand_sheet import BrandSheet
from .turnover_sheet import TurnoverSheet
from .certificate_sheet import CertificateSheet
from ..queries import StocksQueries
from .fbs_sheet import FBSSheet


class StocksReportGenerator:
    """Генератор Excel отчета по остаткам"""
    
    def __init__(self):
        self.queries = StocksQueries()
        self.wb = Workbook()
    
    def generate(self, report_date: str) -> BytesIO:
        # Получаем данные
        df = self.queries.get_stocks_data(report_date)
        stats = self.queries.get_summary_stats(report_date)
        df_fbs = (self.queries.get_fbs_stocks_data(report_date))
        df_categories = self.queries.get_stocks_by_category(report_date)
        df_gender = self.queries.get_stocks_by_gender(report_date)
        df_warehouse = self.queries.get_stocks_by_warehouse(report_date)
        df_brands = self.queries.get_stocks_by_brand(report_date)
        turnover_days = 90
        df_turnover = self.queries.get_inventory_turnover(report_date, days=turnover_days)
        df_certificates = self.queries.get_certificates_data(report_date)


        
        if df.empty:
            raise ValueError(f"Нет данных на дату {report_date}")
        
        # Создаем оглавление
        toc = TOCSheet(self.wb)
        sheets_info = [
                {
                    "number": 1,
                    "name": "Детальные остатки",
                    "description": (
                        "Все товары: WB + FBS + товары в пути"
                    ),
                },
                {
                    "number": 2,
                    "name": "FBS",
                    "description": (
                        "Физические остатки на нашем складе FBS"
                    ),
                },
                {
                    "number": 3,
                    "name": "По категориям",
                    "description": (
                        "Остатки по категориям"
                    ),
                },
                {
                    "number": 4,
                    "name": "По полу",
                    "description": (
                        "Распределение остатков по полу товаров"
                    ),
                },
                {
                    "number": 5,
                    "name": "Остатки по складам",
                    "description": (
                        "Склады Wildberries и товары в пути"
                    ),
                },
                {
                    "number": 6,
                    "name": "По брендам",
                    "description": (
                        "WB + FBS + товары в пути по брендам"
                    ),
                },
                {
                    "number": 7,
                    "name": "Оборачиваемость",
                    "description": (
                        "Анализ скорости продаж и запаса"
                    ),
                },
                {
                    "number": 8,
                    "name": "Сертификаты",
                    "description": (
                        "Просроченные и истекающие сертификаты"
                    ),
                },
            ]
        toc.build(sheets_info, report_date)
        
        # Создаем листы
        DetailSheet(
            self.wb,
            1,
        ).build(
            df,
            stats,
            report_date,
        )

        FBSSheet(
            self.wb,
            2,
        ).build(
            df_fbs,
            stats,
            report_date,
        )

        CategorySheet(
            self.wb,
            3,
        ).build(
            df_categories,
            stats,
            report_date,
        )

        GenderSheet(
            self.wb,
            4,
        ).build(
            df_gender,
            stats,
            report_date,
        )

        WarehouseSheet(
            self.wb,
            5,
        ).build(
            df_warehouse,
            stats,
            report_date,
        )

        BrandSheet(
            self.wb,
            6,
        ).build(
            df_brands,
            stats,
            report_date,
        )

        TurnoverSheet(
            self.wb,
            7,
        ).build(
            df_turnover,
            stats,
            report_date,
            days=turnover_days,
        )

        CertificateSheet(
            self.wb,
            8,
        ).build(
            df_certificates,
            report_date,
        )


        
        # Сохраняем
        output = BytesIO()
        self.wb.save(output)
        output.seek(0)
        
        return output