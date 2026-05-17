# cards/reporting/reconcile/components/tables.py
from openpyxl.styles import Font, Alignment, Border, Side
from ..styles.theme import COLORS, ALIGNMENTS, BORDERS, FILLS, FONTS
from ..styles.helpers import get_status_style, apply_money, apply_number


class TableComponent:
    """Класс для отрисовки таблиц"""
    
    def __init__(self, worksheet):
        self.ws = worksheet
    
    def draw(self, start_row, headers, data_rows, start_col=2, 
             status_col=None, money_cols=None, number_cols=None, 
             column_widths=None, highlight_status=True):
        """Рисует таблицу"""
        row = start_row
        
        # Заголовки
        for col_idx, header in enumerate(headers):
            cell = self.ws.cell(row=row, column=start_col + col_idx, value=header)
            cell.font = FONTS["header_white"]
            cell.fill = FILLS["header"]
            cell.alignment = ALIGNMENTS["center_wrap"]
            cell.border = BORDERS["thin"]
        
        self.ws.row_dimensions[row].height = 35
        row += 1
        
        # Данные
        for idx, data_row in enumerate(data_rows):
            fill = FILLS["alt"] if idx % 2 == 1 else FILLS["none"]
            
            for col_idx, value in enumerate(data_row):
                cell = self.ws.cell(row=row, column=start_col + col_idx, value=value)
                cell.fill = fill
                cell.border = BORDERS["thin"]
                cell.font = FONTS["normal"]
                
                # Применяем стили в зависимости от колонки
                if status_col is not None and col_idx == status_col:
                    style = get_status_style(value)
                    cell.fill = style["fill"]
                    cell.font = style["font"]
                    cell.alignment = ALIGNMENTS["center"]
                elif money_cols and col_idx in money_cols:
                    apply_money(cell)
                elif number_cols and col_idx in number_cols:
                    apply_number(cell)
                elif isinstance(value, (int, float)):
                    apply_number(cell)
                else:
                    cell.alignment = ALIGNMENTS["left"]
            
            self.ws.row_dimensions[row].height = 22
            row += 1
        
        # Настройка ширины колонок
        if column_widths:
            for col_letter, width in column_widths.items():
                self.ws.column_dimensions[col_letter].width = width
        
        return row


def create_table(worksheet):
    """Создает экземпляр TableComponent"""
    return TableComponent(worksheet)