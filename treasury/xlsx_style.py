"""Оформление выгрузок казначейства в стиле управленческого пакета."""
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

NAVY = "2F6656"
NAVY_3 = "1F5E4E"
TEXT = "1F1F1F"
TEXT_2 = "4A4A4A"
MUTED = "8A8A8A"
SURFACE_2 = "F3F8F6"
SURFACE_4 = "E7F1ED"
INPUT = "FFF8E1"                    # колонки для заполнения коллегами
LINE = "D9E2DE"
FONT = "Helvetica Light"
FMT_MONEY = '#,##0.00;(#,##0.00);"–"'
FMT_DATE = "DD.MM.YYYY"

_thin = Side(style="thin", color=LINE)
B_BOTTOM = Border(bottom=_thin)


def fill(c):
    return PatternFill("solid", fgColor=c)


def f(size=10, bold=False, color=TEXT, italic=False, underline=None):
    return Font(name=FONT, size=size, bold=bold, color=color, italic=italic, underline=underline)


def cover(ws, title, subtitle, lines, link_sheet=None, link_text=None):
    """Первый лист: заголовок, текст и ссылка на лист с таблицей."""
    ws.sheet_view.showGridLines = False
    ws.column_dimensions["A"].width = 3
    ws.column_dimensions["B"].width = 110
    ws["B2"] = title
    ws["B2"].font = f(18, True, NAVY_3)
    ws["B3"] = subtitle
    ws["B3"].font = f(10, color=MUTED)
    ws["B4"].border = Border(bottom=Side(style="medium", color=NAVY_3))
    r = 6
    if link_sheet:
        c = ws.cell(row=r, column=2, value=link_text or f"→ Подробности — на листе «{link_sheet}»")
        c.font = f(11, True, NAVY_3, underline="single")
        c.hyperlink = f"#'{link_sheet}'!A1"
        c.fill = fill(SURFACE_4)
        ws.row_dimensions[r].height = 22
        c.alignment = Alignment(vertical="center", indent=1)
        r += 2
    for line in lines:
        c = ws.cell(row=r, column=2, value=line)
        c.alignment = Alignment(wrap_text=True, vertical="top")
        c.font = f(10, bold=bool(line) and not line.startswith((" ", "•")) and line.endswith(":"))
        r += 1
    ws.print_options.gridLines = False
    return r


def table(ws, headers, rows, widths, money=(), dates=(), wrap=(), inputs=(), freeze="A2"):
    """Таблица с зелёной шапкой, зеброй и автофильтром."""
    ws.sheet_view.showGridLines = False
    ws.append(headers)
    for c in ws[1]:
        c.font = f(10, True, "FFFFFF")
        c.fill = fill(NAVY)
        c.alignment = Alignment(wrap_text=True, vertical="center")
    ws.row_dimensions[1].height = 34
    for i, row in enumerate(rows, 2):
        ws.append(list(row))
        for j, c in enumerate(ws[i], 1):
            c.font = f(10)
            c.border = B_BOTTOM
            c.alignment = Alignment(vertical="top", wrap_text=j in wrap)
            if j in money:
                c.number_format = FMT_MONEY
            if j in dates:
                c.number_format = FMT_DATE
            if j in inputs:
                c.fill = fill(INPUT)
            elif i % 2 == 0:
                c.fill = fill(SURFACE_2)
    for j in inputs:
        ws.cell(row=1, column=j).fill = fill(NAVY_3)
    for j, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(j)].width = w
    ws.freeze_panes = freeze
    ws.auto_filter.ref = ws.dimensions
    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth, ws.page_setup.fitToHeight = 1, 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True
