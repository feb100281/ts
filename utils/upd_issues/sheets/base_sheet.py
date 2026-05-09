# upd_issues/sheets/base_sheet.py
from openpyxl.styles import Font, Alignment


class BaseSheet:
    def __init__(self, workbook, sheet_number):
        self.wb = workbook
        self.sheet_name = str(sheet_number)
        
        if self.sheet_name in self.wb.sheetnames:
            self.ws = self.wb[self.sheet_name]
        else:
            self.ws = self.wb.create_sheet(self.sheet_name)
    
    def _format_number(self, value):
        """Форматирование чисел с пробелами как разделителями тысяч"""
        if value is None:
            return "0"
        try:
            return f"{int(value):,}".replace(",", " ")
        except (ValueError, TypeError):
            return str(value)