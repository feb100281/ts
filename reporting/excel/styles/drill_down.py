from openpyxl.styles import Font
from reporting.excel.styles.style_helpers import draw_sheet_header

def style_drilldown_sheet(ws, title, subtitle, date_to=None):
    # убрать сетку
    ws.sheet_view.showGridLines = False

    # заголовок
    currency = "Российский рубль (RUB)"
    draw_sheet_header(
        ws,
        title=title,
        subtitle=subtitle,
        currency=currency,
    )

    # freeze
    ws.freeze_panes = "A4"

    # ширины
    ws.column_dimensions["A"].width = 40
    ws.column_dimensions["B"].width = 18
    ws.column_dimensions["C"].width = 18

    # формат чисел
    for row in ws.iter_rows(min_row=4):
        for cell in row:
            if isinstance(cell.value, (int, float)):
                cell.number_format = '#,##0;(#,##0)'