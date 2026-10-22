# contracts/loans_report/sheets/base_sheet.py
from openpyxl.worksheet.worksheet import Worksheet
from openpyxl import Workbook


class BaseSheet:
    """Базовый класс для всех листов отчета"""
    
    def __init__(self, workbook: Workbook, sheet_number: int):
        self.wb = workbook
        self.sheet_number = sheet_number
        sheet_title = str(sheet_number)
        
        if sheet_title in self.wb.sheetnames:
            self.ws = self.wb[sheet_title]
        else:
            self.ws = self.wb.create_sheet(title=sheet_title)
    
    def _format_number(self, value, decimals: int = 0) -> str:
        """Форматирует число для отображения"""
        if value is None:
            return "—"
        try:
            if decimals == 0:
                return f"{int(value):,}".replace(",", " ")
            else:
                return f"{value:,.{decimals}f}".replace(",", " ")
        except (ValueError, TypeError):
            return str(value)