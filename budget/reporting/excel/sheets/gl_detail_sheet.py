# budget/reporting/excel/sheets/gl_detail_sheet.py
from budget.reporting.excel.styles.helpers import (
    set_column_widths,
    set_row_heights,
    draw_back_button,
    draw_sheet_header,
)
from budget.reporting.excel.styles.theme import (
    FILLS,
    FONTS,
    BORDERS,
    ALIGNMENTS,
    FORMATS,
)


def build_gl_detail_sheet(wb, detail):
    ws = wb.create_sheet(detail["sheet_name"])
    ws.sheet_view.showGridLines = False

    months = detail["months"]
    total_col = len(months) + 2

    widths = {"A": 54}
    col_letters = [
        "B", "C", "D", "E", "F", "G", "H", "I",
        "J", "K", "L", "M", "N", "O", "P", "Q"
    ]

    for idx in range(len(months)):
        widths[col_letters[idx]] = 16

    widths[col_letters[len(months)]] = 18

    set_column_widths(ws, widths)
    set_row_heights(ws, {
        1: 20,
        2: 26,
        3: 18,
        4: 18,
        5: 10,
        6: 24,
    })

    draw_back_button(ws, cell="A1", text="← БЮДЖЕТ", target_sheet="БЮДЖЕТ")
    draw_sheet_header(
        ws,
        title=f'РАСШИФРОВКА {detail["note"]}',
        subtitle=detail["item"],
        note=f'{detail["activity"]} | {detail["operation"]}',
    )

    # header
    ws["A6"] = "Статья"
    ws["A6"].fill = FILLS["header"]
    ws["A6"].font = FONTS["header_white"]
    ws["A6"].alignment = ALIGNMENTS["center"]
    ws["A6"].border = BORDERS["thin"]

    for col_idx, month in enumerate(months, start=2):
        cell = ws.cell(row=6, column=col_idx, value=month)
        cell.fill = FILLS["header"]
        cell.font = FONTS["header_white"]
        cell.alignment = ALIGNMENTS["center"]
        cell.border = BORDERS["thin"]

    total_header = ws.cell(row=6, column=total_col, value="ИТОГО")
    total_header.fill = FILLS["header"]
    total_header.font = FONTS["header_white"]
    total_header.alignment = ALIGNMENTS["center"]
    total_header.border = BORDERS["thin"]

    row_idx = 7
    for row in detail["rows"]:
        label_cell = ws.cell(row=row_idx, column=1, value=row["label"])
        label_cell.font = FONTS["normal"]
        label_cell.alignment = ALIGNMENTS["left"]
        label_cell.border = BORDERS["thin"]

        for col_idx, month in enumerate(months, start=2):
            value = row["months"].get(month, 0)
            cell = ws.cell(row=row_idx, column=col_idx, value=value)
            cell.font = FONTS["negative"] if value < 0 else FONTS["normal"]
            cell.alignment = ALIGNMENTS["right"]
            cell.border = BORDERS["thin"]
            cell.number_format = FORMATS["money_int"]

        total_value = row["total"]
        total_cell = ws.cell(row=row_idx, column=total_col, value=total_value)
        total_cell.font = FONTS["negative"] if total_value < 0 else FONTS["normal"]
        total_cell.alignment = ALIGNMENTS["right"]
        total_cell.border = BORDERS["thin"]
        total_cell.number_format = FORMATS["money_int"]

        row_idx += 1

    # total row
    total_label = ws.cell(row=row_idx, column=1, value="ИТОГО")
    total_label.fill = FILLS["total"]
    total_label.font = FONTS["total"]
    total_label.alignment = ALIGNMENTS["left"]
    total_label.border = BORDERS["bottom_medium"]

    for col_idx, month in enumerate(months, start=2):
        value = detail["total_by_month"].get(month, 0)
        cell = ws.cell(row=row_idx, column=col_idx, value=value)
        cell.fill = FILLS["total"]
        cell.font = FONTS["negative_total"] if value < 0 else FONTS["total"]
        cell.alignment = ALIGNMENTS["right"]
        cell.border = BORDERS["bottom_medium"]
        cell.number_format = FORMATS["money_int"]

    total_sum_cell = ws.cell(row=row_idx, column=total_col, value=detail["total"])
    total_sum_cell.fill = FILLS["total"]
    total_sum_cell.font = FONTS["negative_total"] if detail["total"] < 0 else FONTS["total"]
    total_sum_cell.alignment = ALIGNMENTS["right"]
    total_sum_cell.border = BORDERS["bottom_medium"]
    total_sum_cell.number_format = FORMATS["money_int"]

    ws.freeze_panes = "B7"