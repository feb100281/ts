# budget/reporting/excel/sheets/summary_sheet.py
from budget.reporting.excel.styles.helpers import set_column_widths
from budget.reporting.excel.styles.theme import (
    FONTS,
    FILLS,
    BORDERS,
    ALIGNMENTS,
    FORMATS,
)


def _merge(ws, row, col_from=1, col_to=4):
    ws.merge_cells(
        start_row=row,
        start_column=col_from,
        end_row=row,
        end_column=col_to,
    )


def _set_row_border(ws, row_idx, border, col_from=1, col_to=4):
    for col in range(col_from, col_to + 1):
        ws.cell(row=row_idx, column=col).border = border


def _set_row_fill(ws, row_idx, fill, col_from=1, col_to=4):
    for col in range(col_from, col_to + 1):
        ws.cell(row=row_idx, column=col).fill = fill


# def _draw_title_block(ws, version):
#     _merge(ws, 2, 1, 4)
#     _merge(ws, 3, 1, 4)

#     title = ws["A2"]
#     title.value = "БЮДЖЕТ"
#     title.font = FONTS["title"]
#     title.alignment = ALIGNMENTS["left"]

#     subtitle = ws["A3"]
#     subtitle.value = "Сводная информация и навигация по файлу"
#     subtitle.font = FONTS["subtitle"]
#     subtitle.alignment = ALIGNMENTS["left"]

#     _set_row_border(ws, 4, BORDERS["bottom_medium"])

#     ws["A5"] = "Версия бюджета"
#     ws["A6"] = "Тип"
#     ws["A7"] = "Дата начала"
#     ws["A8"] = "Дата окончания"
#     ws["A9"] = "Описание"

#     ws["B5"] = version.get("number") or "—"
#     ws["B6"] = version.get("budget_type") or "—"
#     ws["B7"] = version.get("date_from") or "—"
#     ws["B8"] = version.get("date_to") or "—"
#     ws["B9"] = version.get("description") or "—"

#     for row_idx in range(5, 10):
#         ws.cell(row=row_idx, column=1).font = FONTS["bold"]
#         ws.cell(row=row_idx, column=2).font = FONTS["normal"]
#         ws.cell(row=row_idx, column=1).alignment = ALIGNMENTS["left"]
#         ws.cell(row=row_idx, column=2).alignment = ALIGNMENTS["left"]

#         _set_row_border(ws, row_idx, BORDERS["bottom_thin"])

#     if hasattr(ws["B7"].value, "year"):
#         ws["B7"].number_format = FORMATS["date"]

#     if hasattr(ws["B8"].value, "year"):
#         ws["B8"].number_format = FORMATS["date"]




def _draw_title_block(ws, version, revenue_param):
    _merge(ws, 2, 1, 4)
    _merge(ws, 3, 1, 4)

    title = ws["A2"]
    title.value = "БЮДЖЕТ"
    title.font = FONTS["title"]
    title.alignment = ALIGNMENTS["left"]

    subtitle = ws["A3"]
    subtitle.value = "Сводная информация и навигация по файлу"
    subtitle.font = FONTS["subtitle"]
    subtitle.alignment = ALIGNMENTS["left"]

    _set_row_border(ws, 4, BORDERS["bottom_medium"])

    scenario_raw = (revenue_param or {}).get("scenario", "base")
    scenario_map = {
        "base": "Базовый",
        "optimistic": "Оптимистичный",
        "conservative": "Консервативный",
    }
    scenario_label = scenario_map.get(str(scenario_raw).lower(), str(scenario_raw))

    ws["A5"] = "Версия бюджета"
    ws["A6"] = "Сценарий"
    ws["A7"] = "Дата начала"
    ws["A8"] = "Дата окончания"
    ws["A9"] = "Описание"

    ws["B5"] = version.get("number") or "—"
    ws["B6"] = scenario_label or "—"
    ws["B7"] = version.get("date_from") or "—"
    ws["B8"] = version.get("date_to") or "—"
    ws["B9"] = version.get("description") or "—"

    for row_idx in range(5, 10):
        ws.cell(row=row_idx, column=1).font = FONTS["bold"]
        ws.cell(row=row_idx, column=2).font = FONTS["normal"]
        ws.cell(row=row_idx, column=1).alignment = ALIGNMENTS["left"]
        ws.cell(row=row_idx, column=2).alignment = ALIGNMENTS["left"]

        _set_row_border(ws, row_idx, BORDERS["bottom_thin"])

    if hasattr(ws["B7"].value, "year"):
        ws["B7"].number_format = FORMATS["date"]

    if hasattr(ws["B8"].value, "year"):
        ws["B8"].number_format = FORMATS["date"]


def _draw_section_header(ws, row_idx, title):
    _merge(ws, row_idx, 1, 4)
    cell = ws.cell(row=row_idx, column=1, value=title)
    cell.font = FONTS["section"]
    cell.alignment = ALIGNMENTS["left"]

    _set_row_fill(ws, row_idx, FILLS["total"])
    _set_row_border(ws, row_idx, BORDERS["thin"])


def _draw_link_row(ws, row_idx, num, label, target_sheet):
    num_cell = ws.cell(row=row_idx, column=1, value=num)
    num_cell.font = FONTS["bold"]
    num_cell.alignment = ALIGNMENTS["center"]
    num_cell.border = BORDERS["bottom_thin"]

    text_cell = ws.cell(row=row_idx, column=2, value=label)
    text_cell.hyperlink = f"#'{target_sheet}'!A1"
    text_cell.font = FONTS["back"]
    text_cell.alignment = ALIGNMENTS["left"]
    text_cell.border = BORDERS["bottom_thin"]

    ws.cell(row=row_idx, column=3).border = BORDERS["bottom_thin"]
    ws.cell(row=row_idx, column=4).border = BORDERS["bottom_thin"]


def _draw_empty_row(ws, row_idx):
    for col in range(1, 5):
        ws.cell(row=row_idx, column=col).border = BORDERS["none"]
        ws.cell(row=row_idx, column=col).fill = FILLS["none"]


def _draw_kpi_block(ws, start_row, data):
    gl_rows = data["gl_rows"]
    detail_sheets = data["gl_pivot"].get("detail_sheets", [])

    total_dt = sum((row.get("dt") or 0) for row in gl_rows)
    total_cr = sum((row.get("cr") or 0) for row in gl_rows)
    total_amount = sum((row.get("amount") or 0) for row in gl_rows)

    _draw_section_header(ws, start_row, "КЛЮЧЕВЫЕ ПОКАЗАТЕЛИ")

    stats = [
        ("Количество строк GL", len(gl_rows), False, False),
        ("Количество расшифровок", len(detail_sheets), False, False),
        ("Итого дебет (поступление)", total_dt, True, False),
        ("Итого кредит (оплаты)", total_cr, True, False),
        ("Итого amount", total_amount, True, True),
    ]

    row_idx = start_row + 1
    for label, value, is_money, is_total in stats:
        l_cell = ws.cell(row=row_idx, column=1, value=label)
        v_cell = ws.cell(row=row_idx, column=2, value=value)

        l_cell.font = FONTS["bold"] if is_total else FONTS["normal"]
        v_cell.font = FONTS["total"] if is_total else FONTS["normal"]

        l_cell.alignment = ALIGNMENTS["left"]
        v_cell.alignment = ALIGNMENTS["right"]

        border = BORDERS["bottom_medium"] if is_total else BORDERS["bottom_thin"]
        l_cell.border = border
        v_cell.border = border
        ws.cell(row=row_idx, column=3).border = border
        ws.cell(row=row_idx, column=4).border = border

        if is_money:
            v_cell.number_format = FORMATS["money"]

        if is_total:
            l_cell.fill = FILLS["total"]
            v_cell.fill = FILLS["total"]
            ws.cell(row=row_idx, column=3).fill = FILLS["total"]
            ws.cell(row=row_idx, column=4).fill = FILLS["total"]

        row_idx += 1

    return row_idx


def build_summary_sheet(wb, data):
    ws = wb.create_sheet("SUMMARY")
    ws.sheet_view.showGridLines = False

    set_column_widths(ws, {
        "A": 28,
        "B": 44,
        "C": 18,
        "D": 18,
    })

    ws.row_dimensions[1].height = 8
    ws.row_dimensions[2].height = 30
    ws.row_dimensions[3].height = 22
    ws.row_dimensions[4].height = 8
    ws.row_dimensions[5].height = 20
    ws.row_dimensions[6].height = 20
    ws.row_dimensions[7].height = 20
    ws.row_dimensions[8].height = 20
    ws.row_dimensions[9].height = 24
    ws.row_dimensions[11].height = 10
    ws.row_dimensions[12].height = 24
    ws.row_dimensions[16].height = 24

    version = data["version"]
    detail_sheets = data["gl_pivot"].get("detail_sheets", [])

    # _draw_title_block(ws, version)
    _draw_title_block(ws, version, data.get("revenue_param", {}))

    # Содержание
    _draw_section_header(ws, 12, "СОДЕРЖАНИЕ")
    _draw_link_row(ws, 13, "1", "Бюджет", "БЮДЖЕТ")

    # Расшифровки
    _draw_section_header(ws, 16, "РАСШИФРОВКИ")
    row_idx = 17

    if detail_sheets:
        for idx, detail in enumerate(detail_sheets, start=1):
            _draw_link_row(
                ws=ws,
                row_idx=row_idx,
                num=f"1.{idx}",
                label=detail.get("title") or detail.get("sheet_name") or f"Расшифровка {idx}",
                target_sheet=detail["sheet_name"],
            )
            row_idx += 1
    else:
        ws.cell(row=row_idx, column=1, value="—").border = BORDERS["bottom_thin"]
        ws.cell(row=row_idx, column=2, value="Детальные расшифровки отсутствуют").border = BORDERS["bottom_thin"]
        ws.cell(row=row_idx, column=1).font = FONTS["normal"]
        ws.cell(row=row_idx, column=2).font = FONTS["normal"]
        ws.cell(row=row_idx, column=1).alignment = ALIGNMENTS["center"]
        ws.cell(row=row_idx, column=2).alignment = ALIGNMENTS["left"]
        ws.cell(row=row_idx, column=3).border = BORDERS["bottom_thin"]
        ws.cell(row=row_idx, column=4).border = BORDERS["bottom_thin"]
        row_idx += 1

    row_idx += 2
    _draw_kpi_block(ws, row_idx, data)

    ws.freeze_panes = "A12"