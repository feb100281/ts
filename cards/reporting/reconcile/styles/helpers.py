# cards/reporting/reconcile/styles/helpers.py
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
from .theme import COLORS, FONTS, BORDERS, ALIGNMENTS, FORMATS, FILLS




def set_column_widths(ws, widths: dict):
    """Установка ширины колонок"""
    for col, width in widths.items():
        ws.column_dimensions[col].width = width


def set_row_heights(ws, heights: dict):
    """Установка высоты строк"""
    for row_idx, height in heights.items():
        ws.row_dimensions[row_idx].height = height


def apply_money(cell):
    """Применить формат денег"""
    cell.number_format = FORMATS["money"]
    cell.alignment = ALIGNMENTS["right"]


def apply_number(cell):
    """Применить формат числа"""
    cell.number_format = FORMATS["number"]
    cell.alignment = ALIGNMENTS["right"]


def apply_decimal(cell):
    """Применить формат десятичного числа"""
    cell.number_format = FORMATS["decimal"]
    cell.alignment = ALIGNMENTS["right"]


def get_status_style(status):
    """Получить стиль для статуса"""
    styles = {
        "OK": {"fill": FILLS["ok"], "font": FONTS["ok"]},
        "SUM_DIFF": {"fill": FILLS["warning"], "font": FONTS["warning"]},
        "ONLY_IN_US": {"fill": FILLS["info"], "font": FONTS["info"]},
        "ONLY_IN_1C": {"fill": FILLS["error"], "font": FONTS["error"]},
    }
    return styles.get(status, {"fill": FILLS["none"], "font": FONTS["normal"]})


def draw_toc_button(ws, cell="A1", text="← Оглавление", target_sheet="TOC"):
    """Рисует кнопку возврата к оглавлению"""
    cell_obj = ws[cell]
    cell_obj.value = text
    cell_obj.hyperlink = f"#'{target_sheet}'!A1"
    cell_obj.font = Font(name="Roboto", size=9, bold=True, color=COLORS["back_text_green"], underline="single")
    cell_obj.alignment = ALIGNMENTS["left"]
    cell_obj.fill = FILLS.get("section", FILLS["none"])
    
    thin_side = Side(style="thin", color=COLORS["border_gray"])
    cell_obj.border = Border(
        left=thin_side,
        right=thin_side,
        top=thin_side,
        bottom=thin_side
    )