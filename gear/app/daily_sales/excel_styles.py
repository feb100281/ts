from openpyxl.styles import Font, PatternFill, Border, Side, Alignment


COLORS = {
    "dark_green": "2F6656",
    "light_gray": "F7F7F7",
    "border_gray": "D9D9D9",
    "white": "FFFFFF",
    "text": "0D0D0D",
}

FILLS = {
    "header": PatternFill("solid", fgColor=COLORS["dark_green"]),
    "alt": PatternFill("solid", fgColor=COLORS["light_gray"]),
    "none": PatternFill(fill_type=None),
}

FONTS = {
    "header": Font(
        name="Roboto Light",
        size=10,
        bold=True,
        color=COLORS["white"],
    ),
    "normal": Font(
        name="Roboto Light",
        size=10,
        color=COLORS["text"],
    ),
}

thin = Side(style="thin", color=COLORS["border_gray"])

BORDERS = {
    "thin": Border(left=thin, right=thin, top=thin, bottom=thin),
}

ALIGNMENTS = {
    "left": Alignment(horizontal="left", vertical="center"),
    "center": Alignment(horizontal="center", vertical="center", wrap_text=True),
    "right": Alignment(horizontal="right", vertical="center"),
}

FORMATS = {
    "decimal": "#,##0.00",
    "date": "dd.mm.yyyy",
}


def apply_excel_style(
    ws,
    freeze_panes="B2",
    numeric_columns=None,
):
    numeric_columns = numeric_columns or set()

    ws.sheet_view.showGridLines = False
    ws.freeze_panes = freeze_panes

    max_row = ws.max_row
    max_col = ws.max_column

    for cell in ws[1]:
        cell.fill = FILLS["header"]
        cell.font = FONTS["header"]
        cell.border = BORDERS["thin"]
        cell.alignment = ALIGNMENTS["center"]

    for row_idx in range(2, max_row + 1):
        is_alt = row_idx % 2 == 0

        for col_idx in range(1, max_col + 1):
            cell = ws.cell(row=row_idx, column=col_idx)

            cell.font = FONTS["normal"]
            cell.border = BORDERS["thin"]
            cell.fill = FILLS["alt"] if is_alt else FILLS["none"]

            if col_idx in numeric_columns:
                cell.number_format = FORMATS["decimal"]
                cell.alignment = ALIGNMENTS["right"]
            else:
                cell.alignment = ALIGNMENTS["left"]

    for column_cells in ws.columns:
        max_len = 0
        column_letter = column_cells[0].column_letter

        for cell in column_cells:
            value = "" if cell.value is None else str(cell.value)
            max_len = max(max_len, len(value))

        ws.column_dimensions[column_letter].width = min(max_len + 2, 38)