# budget/reporting/excel/sheets/json_sheet.py
from budget.reporting.excel.json_flatten import flatten_json
from budget.reporting.excel.styles.helpers import (
    set_column_widths,
    draw_back_button,
    draw_sheet_header,
    draw_table_header,
)
from budget.reporting.excel.styles.theme import (
    FILLS,
    FONTS,
    BORDERS,
    ALIGNMENTS,
)


def build_json_sheet(wb, title, json_data, description=""):
    ws = wb.create_sheet(title)
    ws.sheet_view.showGridLines = False

    set_column_widths(ws, {
        "A": 44,
        "B": 60,
    })

    draw_back_button(ws, cell="A1", text="← SUMMARY", target_sheet="SUMMARY")
    draw_sheet_header(ws, title=title, subtitle=description, note="")
    draw_table_header(ws, row=6, headers=["Путь", "Значение"])

    flat_rows = flatten_json(json_data)
    row_idx = 7

    for idx, (path, value) in enumerate(flat_rows, start=1):
        fill = FILLS["alt"] if idx % 2 == 0 else FILLS["none"]

        c1 = ws.cell(row=row_idx, column=1, value=path)
        c2 = ws.cell(row=row_idx, column=2, value=str(value) if value is not None else "")

        for cell in (c1, c2):
            cell.fill = fill
            cell.border = BORDERS["thin"]
            cell.font = FONTS["normal"]
            cell.alignment = ALIGNMENTS["left"]

        row_idx += 1

    ws.freeze_panes = "A7"
    ws.auto_filter.ref = f"A6:B{row_idx - 1}"