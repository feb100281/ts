from openpyxl.styles import Font, Alignment, Border, Side
from ..styles.theme import COLORS, FONTS, BORDERS, ALIGNMENTS, FORMATS, FILLS


class TableBuilder:
    def __init__(self, ws):
        self.ws = ws
    
    def draw(self, start_row, headers, data_rows, start_col=2, 
             money_cols=None, date_cols=None, center_cols=None):
        """Рисует таблицу с данными"""
        if money_cols is None:
            money_cols = []
        if date_cols is None:
            date_cols = []
        if center_cols is None:
            center_cols = []
        
        current_row = start_row
        
        # Заголовки таблицы
        for col_idx, header in enumerate(headers):
            cell = self.ws.cell(
                row=current_row,
                column=start_col + col_idx,
                value=header
            )
            cell.font = FONTS["header_white"]
            cell.alignment = ALIGNMENTS["center"]
            cell.fill = FILLS["header"]
            cell.border = BORDERS["thin"]
        
        self.ws.row_dimensions[current_row].height = 30
        current_row += 1
        data_start_row = current_row
        
        # Данные
        for row_idx, row_data in enumerate(data_rows):
            for col_idx, value in enumerate(row_data):
                cell = self.ws.cell(
                    row=current_row,
                    column=start_col + col_idx,
                    value=value
                )
                
                # Применяем форматирование в зависимости от колонки
                if col_idx in money_cols:
                    cell.font = FONTS["normal"]
                    cell.alignment = ALIGNMENTS["right"]
                    if value and value != '-':
                        cell.number_format = FORMATS["money"]
                elif col_idx in date_cols:
                    cell.font = FONTS["normal"]
                    cell.alignment = ALIGNMENTS["center"]
                    cell.number_format = FORMATS["date"]
                elif col_idx in center_cols:
                    cell.font = FONTS["normal"]
                    cell.alignment = ALIGNMENTS["center"]
                else:
                    cell.font = FONTS["normal"]
                    cell.alignment = ALIGNMENTS["left_wrap"]
                
                cell.border = BORDERS["thin"]
                
                # Чередование цвета строк
                if row_idx % 2 == 0:
                    cell.fill = FILLS["alt"]
                else:
                    cell.fill = FILLS["none"]
            
            self.ws.row_dimensions[current_row].height = 25
            current_row += 1
        
        return data_start_row, current_row - 1


def create_table(ws):
    """Создает объект построителя таблиц"""
    return TableBuilder(ws)