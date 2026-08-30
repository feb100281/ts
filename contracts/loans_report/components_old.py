# # contracts/loans_report/components.py
# from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
# from .styles import COLORS, FILLS, FONTS, BORDERS, ALIGNMENTS, FORMATS


# class SheetTitle:
#     """Класс для отрисовки заголовка листа"""
    
#     def __init__(self, worksheet):
#         self.ws = worksheet
    
#     def draw(self, row: int, title: str, subtitle: str = "", date_text: str = "", 
#              start_col: int = 2, end_col: int = 16) -> int:
#         """Рисует заголовок листа"""
#         # Заголовок
#         self.ws.merge_cells(
#             start_row=row, start_column=start_col, 
#             end_row=row, end_column=end_col
#         )
#         title_cell = self.ws.cell(row=row, column=start_col, value=title)
#         title_cell.font = FONTS["title"]
#         title_cell.alignment = ALIGNMENTS["left"]
#         self.ws.row_dimensions[row].height = 35
#         row += 1
        
#         # Подзаголовок
#         if subtitle:
#             self.ws.merge_cells(
#                 start_row=row, start_column=start_col,
#                 end_row=row, end_column=end_col
#             )
#             sub_cell = self.ws.cell(row=row, column=start_col, value=subtitle)
#             sub_cell.font = FONTS["subtitle"]
#             sub_cell.alignment = ALIGNMENTS["left"]
#             self.ws.row_dimensions[row].height = 22
#             row += 1
        
#         # Дата
#         if date_text:
#             self.ws.merge_cells(
#                 start_row=row, start_column=start_col,
#                 end_row=row, end_column=end_col
#             )
#             date_cell = self.ws.cell(row=row, column=start_col, value=date_text)
#             date_cell.font = FONTS["subtitle"]
#             date_cell.alignment = ALIGNMENTS["left"]
#             self.ws.row_dimensions[row].height = 20
#             row += 1
        
#         row += 1
#         return row


# class KPICards:
#     """Класс для отрисовки KPI карточек"""
    
#     def __init__(self, worksheet):
#         self.ws = worksheet
    
#     def draw_card(self, row: int, col: int, title: str, value, 
#                   subtitle: str = None, color: str = None, 
#                   width: int = 2, format_type: str = "number") -> int:
#         """Рисует одну KPI карточку"""
#         # Фон карточки
#         for r in range(row, row + 2):
#             for c in range(col, col + width):
#                 cell = self.ws.cell(row=r, column=c)
#                 cell.fill = FILLS["section"]  # ИСПРАВЛЕНО: было COLORS["primary_bg"]
#                 cell.border = BORDERS["thin"]
        
#         # Значение
#         if width > 1:
#             self.ws.merge_cells(
#                 start_row=row, start_column=col,
#                 end_row=row, end_column=col + width - 1
#             )
        
#         value_cell = self.ws.cell(row=row, column=col, value=value)
#         value_cell.font = FONTS["kpi_value"]
#         if color:
#             value_cell.font = Font(
#                 name="Roboto", size=16, bold=True, color=color
#             )
#         value_cell.alignment = ALIGNMENTS["center"]
        
#         # Форматирование значения
#         if isinstance(value, (int, float)):
#             if format_type == "currency":
#                 value_cell.number_format = FORMATS["currency"]
#             elif format_type == "percentage":
#                 value_cell.number_format = FORMATS["percentage"]
#                 value_cell.value = value / 100 if value > 1 else value
#             elif format_type == "decimal":
#                 value_cell.number_format = FORMATS["decimal"]
        
#         # Заголовок
#         if width > 1:
#             self.ws.merge_cells(
#                 start_row=row + 1, start_column=col,
#                 end_row=row + 1, end_column=col + width - 1
#             )
        
#         title_cell = self.ws.cell(row=row + 1, column=col, value=title)
#         title_cell.font = FONTS["kpi_label"]
#         title_cell.alignment = ALIGNMENTS["center"]
        
#         # Подзаголовок
#         if subtitle:
#             for c in range(col, col + width):
#                 cell = self.ws.cell(row=row + 2, column=c)
#                 cell.fill = FILLS["section"]  # ИСПРАВЛЕНО: было COLORS["primary_bg"]
#                 cell.border = BORDERS["thin"]
            
#             if width > 1:
#                 self.ws.merge_cells(
#                     start_row=row + 2, start_column=col,
#                     end_row=row + 2, end_column=col + width - 1
#                 )
            
#             sub_cell = self.ws.cell(row=row + 2, column=col, value=subtitle)
#             sub_cell.font = FONTS["subtitle"]
#             sub_cell.alignment = ALIGNMENTS["center"]
#             return 3
        
#         return 2
    
#     def draw_row(self, start_row: int, cards: list, start_col: int = 2) -> int:
#         """Рисует строку карточек"""
#         current_col = start_col
#         max_height = 2
        
#         for card in cards:
#             height = self.draw_card(
#                 row=start_row,
#                 col=current_col,
#                 title=card.get("title", ""),
#                 value=card.get("value", "—"),
#                 subtitle=card.get("subtitle"),
#                 color=card.get("color"),
#                 width=card.get("width", 2),
#                 format_type=card.get("format", "number")
#             )
#             max_height = max(max_height, height)
#             current_col += card.get("width", 2)
        
#         return start_row + max_height


# class Table:
#     """Класс для отрисовки таблиц"""
    
#     def __init__(self, worksheet):
#         self.ws = worksheet
    
#     def draw(self, start_row: int, headers: list, data_rows: list,
#              start_col: int = 2, number_format: str = '#,##0.00',
#              highlight_cols: list = None, column_widths: dict = None,
#              freeze_header: bool = True) -> int:
#         """Рисует таблицу"""
#         row = start_row
        
#         # Заголовки
#         for col_idx, header in enumerate(headers):
#             cell = self.ws.cell(
#                 row=row, column=start_col + col_idx, value=header
#             )
#             cell.font = FONTS["header"]  # ИСПРАВЛЕНО: было header_white
#             cell.fill = FILLS["header"]
#             cell.alignment = ALIGNMENTS["center"]
#             cell.border = BORDERS["thin"]
        
#         self.ws.row_dimensions[row].height = 32
#         row += 1
        
#         table_start_row = row
        
#         # Данные
#         for idx, data_row in enumerate(data_rows):
#             fill = FILLS["alt"] if idx % 2 == 1 else FILLS["none"]
            
#             for col_idx, value in enumerate(data_row):
#                 cell = self.ws.cell(
#                     row=row, column=start_col + col_idx, value=value
#                 )
#                 cell.fill = fill
#                 cell.border = BORDERS["thin"]
                
#                 # Выравнивание
#                 if col_idx == 0:
#                     cell.alignment = ALIGNMENTS["left"]
#                 elif isinstance(value, (int, float)):
#                     cell.alignment = ALIGNMENTS["right"]
#                     cell.number_format = number_format
#                 else:
#                     cell.alignment = ALIGNMENTS["center"]
                
#                 cell.font = FONTS["normal"]
                
#                 # Подсветка колонок
#                 if highlight_cols and col_idx in highlight_cols:
#                     if isinstance(value, (int, float)):
#                         if value > 0 and col_idx in [6, 7]:  # проценты/начислено
#                             cell.font = FONTS["accent"]
#                         elif value < 0:
#                             cell.font = FONTS["error"]  # ИСПРАВЛЕНО: было danger
            
#             self.ws.row_dimensions[row].height = 24
#             row += 1
        
#         # Заморозка заголовка
#         if freeze_header and row > table_start_row:
#             self.ws.freeze_panes = f'C{table_start_row}'
        
#         # Ширина колонок
#         if column_widths:
#             for col_letter, width in column_widths.items():
#                 self.ws.column_dimensions[col_letter].width = width
        
#         return row


# def create_sheet_title(worksheet):
#     """Создает экземпляр SheetTitle"""
#     return SheetTitle(worksheet)


# def create_kpi_cards(worksheet):
#     """Создает экземпляр KPICards"""
#     return KPICards(worksheet)


# def create_table(worksheet):
#     """Создает экземпляр Table"""
#     return Table(worksheet)