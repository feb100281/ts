# budget/reporting/excel/sheets/summary_sheet.py
# from budget.reporting.excel.styles.helpers import (
#     set_column_widths,
#     draw_section_title,
# )
# from budget.reporting.excel.styles.theme import (
#     FONTS,
#     FILLS,
#     BORDERS,
#     ALIGNMENTS,
#     FORMATS,
# )


# def build_summary_sheet(wb, data):
#     ws = wb.create_sheet("SUMMARY")
#     ws.sheet_view.showGridLines = False

#     set_column_widths(ws, {
#         "A": 24,
#         "B": 30,
#         "C": 22,
#         "D": 22,
#     })

#     version = data["version"]
#     gl_rows = data["gl_rows"]

#     total_dt = sum((row["dt"] or 0) for row in gl_rows)
#     total_cr = sum((row["cr"] or 0) for row in gl_rows)
#     total_amount = sum((row["amount"] or 0) for row in gl_rows)

#     ws["A2"] = "БЮДЖЕТ"
#     ws["A3"] = "Excel-отчет по версии бюджета"

#     ws["A2"].font = FONTS["title"]
#     ws["A3"].font = FONTS["subtitle"]

#     draw_section_title(ws, 5, 1, 4, "КАРТОЧКА ВЕРСИИ")

#     rows = [
#         ("Версия бюджета", version["number"]),
#         ("Тип", version["budget_type"]),
#         ("Дата начала", version["date_from"]),
#         ("Дата окончания", version["date_to"]),
#         ("Описание", version["description"] or "—"),
#     ]

#     row_idx = 6
#     for label, value in rows:
#         ws.cell(row=row_idx, column=1, value=label).font = FONTS["bold"]
#         ws.cell(row=row_idx, column=2, value=value).font = FONTS["normal"]
#         ws.cell(row=row_idx, column=1).border = BORDERS["bottom_thin"]
#         ws.cell(row=row_idx, column=2).border = BORDERS["bottom_thin"]
#         if hasattr(value, "year"):
#             ws.cell(row=row_idx, column=2).number_format = FORMATS["date"]
#         row_idx += 1

#     draw_section_title(ws, 13, 1, 4, "СВОДКА GL")

#     stats = [
#         ("Количество строк", len(gl_rows)),
#         ("Итого дебет", total_dt),
#         ("Итого кредит", total_cr),
#         ("Итого amount", total_amount),
#     ]

#     row_idx = 14
#     for idx, (label, value) in enumerate(stats, start=1):
#         ws.cell(row=row_idx, column=1, value=label).font = FONTS["bold"] if idx == 4 else FONTS["normal"]
#         ws.cell(row=row_idx, column=2, value=value).font = FONTS["total"] if idx == 4 else FONTS["normal"]
#         ws.cell(row=row_idx, column=1).border = BORDERS["bottom_medium"] if idx == 4 else BORDERS["bottom_thin"]
#         ws.cell(row=row_idx, column=2).border = BORDERS["bottom_medium"] if idx == 4 else BORDERS["bottom_thin"]
#         ws.cell(row=row_idx, column=2).number_format = FORMATS["money"]
#         ws.cell(row=row_idx, column=2).alignment = ALIGNMENTS["right"]
#         if idx == 4:
#             ws.cell(row=row_idx, column=1).fill = FILLS["total"]
#             ws.cell(row=row_idx, column=2).fill = FILLS["total"]
#         row_idx += 1

#     draw_section_title(ws, 20, 1, 4, "ЛИСТЫ")

#     links = [
#         ("GL", "GL"),
#         ("GL_PIVOT", "GL_PIVOT"),
#         ("REVENUE_PARAMS", "REVENUE_PARAMS"),
#         ("WB_COSTS_PARAMS", "WB_COSTS_PARAMS"),
#         ("CF_PARAMS", "CF_PARAMS"),
#     ]

#     if data["report"]:
#         links.append(("REPORT", "REPORT"))

#     row_idx = 21
#     for label, target in links:
#         cell = ws.cell(row=row_idx, column=1, value=label)
#         cell.hyperlink = f"#'{target}'!A1"
#         cell.font = FONTS["back"]
#         cell.alignment = ALIGNMENTS["left"]
#         cell.border = BORDERS["bottom_thin"]
#         row_idx += 1

#     ws.freeze_panes = "A6"




# from budget.reporting.excel.styles.helpers import set_column_widths
# from budget.reporting.excel.styles.theme import (
#     FONTS,
#     FILLS,
#     BORDERS,
#     ALIGNMENTS,
#     FORMATS,
# )


# def _merge(ws, row, col_from=1, col_to=4):
#     ws.merge_cells(start_row=row, start_column=col_from, end_row=row, end_column=col_to)


# def _apply_row_fill(ws, row_idx, fill, col_from=1, col_to=4):
#     for col in range(col_from, col_to + 1):
#         ws.cell(row=row_idx, column=col).fill = fill


# def _apply_row_border(ws, row_idx, border, col_from=1, col_to=4):
#     for col in range(col_from, col_to + 1):
#         ws.cell(row=row_idx, column=col).border = border


# def _draw_top_block(ws, version):
#     _merge(ws, 2, 1, 4)
#     _merge(ws, 3, 1, 4)

#     ws["A2"] = "SUMMARY"
#     ws["A3"] = "Excel-отчет по версии бюджета"

#     ws["A2"].font = FONTS["title"]
#     ws["A3"].font = FONTS["subtitle"]

#     ws["A2"].alignment = ALIGNMENTS["left"]
#     ws["A3"].alignment = ALIGNMENTS["left"]

#     _apply_row_border(ws, 4, BORDERS["bottom_medium"])

#     ws["A5"] = "Версия:"
#     ws["B5"] = version.get("number") or "—"
#     ws["A6"] = "Период:"
#     date_from = version.get("date_from")
#     date_to = version.get("date_to")
#     ws["B6"] = f"{date_from:%d.%m.%Y} – {date_to:%d.%m.%Y}" if hasattr(date_from, "year") and hasattr(date_to, "year") else "—"

#     ws["A5"].font = FONTS["bold"]
#     ws["A6"].font = FONTS["bold"]
#     ws["B5"].font = FONTS["normal"]
#     ws["B6"].font = FONTS["normal"]

#     ws["A5"].alignment = ALIGNMENTS["left"]
#     ws["A6"].alignment = ALIGNMENTS["left"]
#     ws["B5"].alignment = ALIGNMENTS["left"]
#     ws["B6"].alignment = ALIGNMENTS["left"]

#     ws["A5"].border = BORDERS["bottom_thin"]
#     ws["B5"].border = BORDERS["bottom_thin"]
#     ws["C5"].border = BORDERS["bottom_thin"]
#     ws["D5"].border = BORDERS["bottom_thin"]

#     ws["A6"].border = BORDERS["bottom_thin"]
#     ws["B6"].border = BORDERS["bottom_thin"]
#     ws["C6"].border = BORDERS["bottom_thin"]
#     ws["D6"].border = BORDERS["bottom_thin"]


# def _draw_section_header(ws, row_idx, title):
#     _merge(ws, row_idx, 1, 4)
#     cell = ws.cell(row=row_idx, column=1, value=title)
#     cell.font = FONTS["section"]
#     cell.alignment = ALIGNMENTS["left"]

#     for col in range(1, 5):
#         ws.cell(row=row_idx, column=col).fill = FILLS["total"]
#         ws.cell(row=row_idx, column=col).border = BORDERS["thin"]


# def _draw_nav_row(ws, row_idx, num, label, target_sheet):
#     num_cell = ws.cell(row=row_idx, column=1, value=num)
#     num_cell.font = FONTS["bold"]
#     num_cell.alignment = ALIGNMENTS["center"]
#     num_cell.border = BORDERS["bottom_thin"]

#     text_cell = ws.cell(row=row_idx, column=2, value=label)
#     text_cell.hyperlink = f"#'{target_sheet}'!A1"
#     text_cell.font = FONTS["back"]
#     text_cell.alignment = ALIGNMENTS["left"]
#     text_cell.border = BORDERS["bottom_thin"]

#     ws.cell(row=row_idx, column=3).border = BORDERS["bottom_thin"]
#     ws.cell(row=row_idx, column=4).border = BORDERS["bottom_thin"]


# def _draw_version_card(ws, start_row, version):
#     _draw_section_header(ws, start_row, "КАРТОЧКА ВЕРСИИ")

#     rows = [
#         ("Номер версии", version.get("number") or "—"),
#         ("Тип бюджета", version.get("budget_type") or "—"),
#         ("Дата начала", version.get("date_from") or "—"),
#         ("Дата окончания", version.get("date_to") or "—"),
#         ("Описание", version.get("description") or "—"),
#     ]

#     row_idx = start_row + 1
#     for label, value in rows:
#         l_cell = ws.cell(row=row_idx, column=1, value=label)
#         v_cell = ws.cell(row=row_idx, column=2, value=value)

#         l_cell.font = FONTS["bold"]
#         v_cell.font = FONTS["normal"]

#         l_cell.alignment = ALIGNMENTS["left"]
#         v_cell.alignment = ALIGNMENTS["left"]

#         l_cell.border = BORDERS["bottom_thin"]
#         v_cell.border = BORDERS["bottom_thin"]
#         ws.cell(row=row_idx, column=3).border = BORDERS["bottom_thin"]
#         ws.cell(row=row_idx, column=4).border = BORDERS["bottom_thin"]

#         if hasattr(value, "year"):
#             v_cell.number_format = FORMATS["date"]

#         row_idx += 1

#     return row_idx


# def _draw_gl_summary(ws, start_row, gl_rows):
#     total_dt = sum((row.get("dt") or 0) for row in gl_rows)
#     total_cr = sum((row.get("cr") or 0) for row in gl_rows)
#     total_amount = sum((row.get("amount") or 0) for row in gl_rows)

#     _draw_section_header(ws, start_row, "КРАТКАЯ СВОДКА")

#     stats = [
#         ("Количество строк GL", len(gl_rows), False, False),
#         ("Итого дебет", total_dt, True, False),
#         ("Итого кредит", total_cr, True, False),
#         ("Итого amount", total_amount, True, True),
#     ]

#     row_idx = start_row + 1
#     for label, value, is_money, is_total in stats:
#         l_cell = ws.cell(row=row_idx, column=1, value=label)
#         v_cell = ws.cell(row=row_idx, column=2, value=value)

#         l_cell.font = FONTS["bold"] if is_total else FONTS["normal"]
#         v_cell.font = FONTS["total"] if is_total else FONTS["normal"]

#         l_cell.alignment = ALIGNMENTS["left"]
#         v_cell.alignment = ALIGNMENTS["right"]

#         border = BORDERS["bottom_medium"] if is_total else BORDERS["bottom_thin"]
#         l_cell.border = border
#         v_cell.border = border
#         ws.cell(row=row_idx, column=3).border = border
#         ws.cell(row=row_idx, column=4).border = border

#         if is_money:
#             v_cell.number_format = FORMATS["money"]

#         if is_total:
#             l_cell.fill = FILLS["total"]
#             v_cell.fill = FILLS["total"]
#             ws.cell(row=row_idx, column=3).fill = FILLS["total"]
#             ws.cell(row=row_idx, column=4).fill = FILLS["total"]

#         row_idx += 1

#     return row_idx


# def build_summary_sheet(wb, data):
#     ws = wb.create_sheet("БЮДЖЕТ")
#     ws.sheet_view.showGridLines = False

#     set_column_widths(ws, {
#         "A": 14,
#         "B": 52,
#         "C": 16,
#         "D": 16,
#     })

#     ws.row_dimensions[1].height = 10
#     ws.row_dimensions[2].height = 30
#     ws.row_dimensions[3].height = 22
#     ws.row_dimensions[4].height = 8
#     ws.row_dimensions[5].height = 21
#     ws.row_dimensions[6].height = 21
#     ws.row_dimensions[7].height = 10
#     ws.row_dimensions[8].height = 24
#     ws.row_dimensions[13].height = 24
#     ws.row_dimensions[20].height = 24

#     version = data["version"]
#     gl_rows = data["gl_rows"]

#     _draw_top_block(ws, version)

#     # СОДЕРЖАНИЕ
#     _draw_section_header(ws, 8, "СОДЕРЖАНИЕ")
#     _draw_nav_row(ws, 9, "1", "Сводная расшифровка бюджета", "GL_PIVOT")

#     # РАСШИФРОВКИ
#     _draw_section_header(ws, 13, "РАСШИФРОВКИ")

#     row_idx = 14
#     detail_sheets = data["gl_pivot"].get("detail_sheets", [])

#     if detail_sheets:
#         for idx, detail in enumerate(detail_sheets, start=1):
#             _draw_nav_row(
#                 ws=ws,
#                 row_idx=row_idx,
#                 num=f"1.{idx}",
#                 label=detail.get("title") or detail.get("sheet_name") or f"Расшифровка {idx}",
#                 target_sheet=detail["sheet_name"],
#             )
#             row_idx += 1
#     else:
#         cell = ws.cell(row=row_idx, column=1, value="Расшифровки отсутствуют")
#         cell.font = FONTS["normal"]
#         cell.alignment = ALIGNMENTS["left"]
#         cell.border = BORDERS["bottom_thin"]
#         ws.cell(row=row_idx, column=2).border = BORDERS["bottom_thin"]
#         ws.cell(row=row_idx, column=3).border = BORDERS["bottom_thin"]
#         ws.cell(row=row_idx, column=4).border = BORDERS["bottom_thin"]
#         row_idx += 1

#     row_idx += 1
#     _draw_gl_summary(ws, row_idx, gl_rows)

#     ws.freeze_panes = "A8"




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


def _draw_title_block(ws, version):
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

    ws["A5"] = "Версия бюджета"
    ws["A6"] = "Тип"
    ws["A7"] = "Дата начала"
    ws["A8"] = "Дата окончания"
    ws["A9"] = "Описание"

    ws["B5"] = version.get("number") or "—"
    ws["B6"] = version.get("budget_type") or "—"
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

    _draw_title_block(ws, version)

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