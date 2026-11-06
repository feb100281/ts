# budget/reporting/excel/sheets/gl_sheet.py
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
    FORMATS,
)


def build_gl_sheet(wb, data):
    ws = wb.create_sheet("GL")
    ws.sheet_view.showGridLines = False

    set_column_widths(ws, {
        "A": 14,
        "B": 28,
        "C": 28,
        "D": 28,
        "E": 34,
        "F": 14,
        "G": 14,
        "H": 14,
        "I": 42,
    })

    draw_back_button(ws, cell="A1", text="← SUMMARY", target_sheet="SUMMARY")
    draw_sheet_header(
        ws,
        title="ПРОВОДКИ БЮДЖЕТА",
        subtitle=f'Версия: {data["version"]["number"]}',
        note=f'Период: {data["version"]["date_from"]:%d.%m.%Y} - {data["version"]["date_to"]:%d.%m.%Y}',
    )

    headers = [
        "Дата",
        "Activity",
        "Operation",
        "Item",
        "Subitem",
        "Dt",
        "Cr",
        "Amount",
        "Description",
    ]
    draw_table_header(ws, row=6, headers=headers)

    rows = data["gl_rows"]
    row_idx = 7

    for idx, row in enumerate(rows, start=1):
        zebra = idx % 2 == 0
        fill = FILLS["alt"] if zebra else FILLS["none"]

        values = [
            row["date_from"],
            row["activity"],
            row["operation"],
            row["item"],
            row["subitem"],
            row["dt"],
            row["cr"],
            row["amount"],
            row["description"],
        ]

        for col_idx, value in enumerate(values, start=1):
            cell = ws.cell(row=row_idx, column=col_idx, value=value)
            cell.fill = fill
            cell.border = BORDERS["thin"]
            cell.font = FONTS["normal"]

            if col_idx == 1:
                cell.number_format = FORMATS["date"]
                cell.alignment = ALIGNMENTS["center"]
            elif col_idx in (6, 7, 8):
                cell.number_format = FORMATS["money"]
                cell.alignment = ALIGNMENTS["right"]
            else:
                cell.alignment = ALIGNMENTS["left"]

        row_idx += 1

    total_row = row_idx
    totals = [
        "ИТОГО",
        "",
        "",
        "",
        "",
        sum((r["dt"] or 0) for r in rows),
        sum((r["cr"] or 0) for r in rows),
        sum((r["amount"] or 0) for r in rows),
        "",
    ]

    for col_idx, value in enumerate(totals, start=1):
        cell = ws.cell(row=total_row, column=col_idx, value=value)
        cell.fill = FILLS["total"]
        cell.border = BORDERS["bottom_medium"]
        cell.font = FONTS["total"]
        if col_idx in (6, 7, 8):
            cell.number_format = FORMATS["money"]
            cell.alignment = ALIGNMENTS["right"]
        else:
            cell.alignment = ALIGNMENTS["left"]

    ws.freeze_panes = "A7"
    ws.auto_filter.ref = f"A6:I{total_row}"