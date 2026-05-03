from openpyxl.styles import Font, Alignment
from ..styles.theme import COLORS


class Footnote:
    def __init__(self, worksheet):
        self.ws = worksheet
    
    def draw(self, row: int, text: str, col: int = 2, font_size: int = 9) -> int:
        """Рисует сноску"""
        cell = self.ws.cell(row=row, column=col, value=text)
        cell.font = Font(name="Roboto", size=font_size, italic=True, color=COLORS["text_gray"])
        cell.alignment = Alignment(horizontal='left', vertical='center')
        return row + 1