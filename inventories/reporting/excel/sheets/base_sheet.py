from ..styles.theme import COLORS, BORDERS, ALIGNMENTS
from ..styles.helpers import draw_toc_button


class BaseSheet:
    """Базовый класс для всех листов отчета"""
    
    def __init__(self, workbook, sheet_number):
        self.wb = workbook
        self.sheet_number = str(sheet_number)
        self.ws = self.wb.create_sheet(self.sheet_number)
        
    def _draw_separator(self, row, start_col, end_col, color=COLORS["border_gray"]):
        """Рисует разделительную линию"""
        from openpyxl.styles import Border, Side
        for col in range(start_col, end_col + 1):
            cell = self.ws.cell(row=row, column=col)
            cell.border = Border(bottom=Side(style="thin", color=color))
    
    def _format_number(self, value):
        if value is None or value == 0:
            return "0"
        return f"{int(round(float(value))):,}".replace(",", " ")
    
    def _format_currency(self, value):
        if value is None or value == 0:
            return "0 ₽"
        return f"{int(round(float(value))):,} ₽".replace(",", " ")
    
    def set_column_widths(self, widths: dict):
        """Устанавливает ширину колонок"""
        for col, width in widths.items():
            self.ws.column_dimensions[col].width = width
    
    def set_row_heights(self, heights: dict):
        """Устанавливает высоту строк"""
        for row, height in heights.items():
            self.ws.row_dimensions[row].height = height