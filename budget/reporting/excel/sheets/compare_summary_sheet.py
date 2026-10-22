# budget/reporting/excel/sheets/compare_summary_sheet.py

from openpyxl.styles import Font, PatternFill, Border, Alignment, Side

from budget.reporting.excel.styles.helpers import (
    set_column_widths,
    set_row_heights,
    apply_date,
)
from budget.reporting.excel.styles.theme import (
    FILLS,
    FONTS,
    BORDERS,
    ALIGNMENTS,
    COLORS,
)


def _scenario_label(data):
    scenario_raw = (data.get("revenue_param") or {}).get("scenario", "base")
    scenario_map = {
        "base": "Базовый",
        "optimistic": "Оптимистичный",
        "conservative": "Консервативный",
    }
    return scenario_map.get(str(scenario_raw).lower(), str(scenario_raw))


def _clear_summary_area(ws, max_row=120, max_col=8):
    merged_ranges = list(ws.merged_cells.ranges)
    for merged_range in merged_ranges:
        if merged_range.min_row <= max_row and merged_range.max_col <= max_col:
            ws.unmerge_cells(str(merged_range))

    for row in range(1, max_row + 1):
        for col in range(1, max_col + 1):
            cell = ws.cell(row=row, column=col)
            cell.value = None
            cell.fill = PatternFill(fill_type=None)
            cell.border = Border()
            cell.hyperlink = None
            cell.alignment = Alignment(horizontal="general", vertical="bottom")
            cell.number_format = "General"


def _set_link(cell, target_sheet, font_link, workbook):
    cell.hyperlink = f"#'{target_sheet}'!A1"
    cell.font = font_link


def _write_section_bar(ws, row, title, fill_section, font_section, align_left, col_from=2, col_to=6):
    for col in range(col_from, col_to + 1):
        cell = ws.cell(row=row, column=col)
        cell.fill = fill_section
        cell.border = BORDERS["bottom_thin"]
        cell.alignment = align_left
        if col == col_from:
            cell.value = title
            cell.font = font_section
        else:
            cell.value = None


def _draw_toc_item_row(
    ws,
    row,
    num,
    title,
    sheet,
    workbook,
    *,
    font_num,
    font_link,
):
    dotted_border = Border(
        bottom=Side(style="dotted", color=COLORS["border_gray"])
    )

    for col in range(2, 6):  # B:E
        cell = ws.cell(row=row, column=col)
        cell.fill = FILLS["none"]
        cell.border = dotted_border
        if col not in (2, 4):
            cell.value = None

    num_cell = ws.cell(row=row, column=2)
    title_cell = ws.cell(row=row, column=4)

    num_cell.value = str(num)
    num_cell.number_format = "@"
    num_cell.font = font_num
    num_cell.alignment = ALIGNMENTS["center"]

    title_cell.value = title
    title_cell.alignment = Alignment(horizontal="left", vertical="center")
    _set_link(title_cell, sheet, font_link, workbook)


def build_compare_summary_sheet(wb, versions_data):
    ws = wb.create_sheet("SUMMARY_COMPARE")
    ws.sheet_view.showGridLines = False
    ws.freeze_panes = None

    _clear_summary_area(ws)

    align_left = ALIGNMENTS["left"]

    fill_section = FILLS["section"] if "section" in FILLS else FILLS["total"]
    fill_summary = FILLS["summary"] if "summary" in FILLS else FILLS["none"]

    font_title = Font(name="Roboto", size=18, bold=True, color=COLORS["black"])
    font_subtitle = FONTS["subtitle"]
    font_section = Font(name="Roboto", size=13, bold=True, color=COLORS["black"])

    font_meta_label = Font(name="Roboto", size=10, bold=True, color=COLORS["black"])
    font_meta_value = Font(name="Roboto", size=10, bold=False, color=COLORS["black"])

    font_num_main = Font(name="Roboto", size=11, bold=True, color=COLORS["black"])
    font_link_main = Font(
        name="Roboto",
        size=11,
        bold=True,
        color="1F6F43",
        underline="single",
    )

    set_column_widths(ws, {
        "A": 4,
        "B": 9,
        "C": 18,
        "D": 28,
        "E": 18,
        "F": 18,
        "G": 12,
        "H": 12,
    })

    set_row_heights(ws, {
        1: 30,
        2: 22,
        3: 20,
        4: 10,
        5: 20,
        6: 20,
        7: 12,
        8: 25,
        9: 22,
        10: 20,
        11: 20,
        12: 20,
        13: 12,
        14: 25,
        15: 24,
        16: 24,
        17: 24,
        18: 12,
        19: 25,
        20: 20,
        21: 20,
        22: 20,
        23: 20,
    })

    ws["B1"] = "ТРЕНДСЕТТЕР"
    ws["B1"].font = font_title
    ws["B1"].alignment = align_left

    ws["B2"] = "Управленческая отчетность"
    ws["B2"].font = font_subtitle
    ws["B2"].alignment = align_left

    ws["B3"] = "Сравнение бюджетов"
    ws["B3"].font = Font(name="Roboto", size=12, bold=True, color=COLORS["black"])
    ws["B3"].alignment = align_left

    for col in range(2, 7):  # B:F
        ws.cell(row=4, column=col).border = BORDERS["bottom_medium"]

    for cell_ref in ["B5", "C5", "D5", "E5", "F5", "B6", "C6", "D6", "E6", "F6"]:
        ws[cell_ref].fill = fill_summary
        ws[cell_ref].alignment = align_left

    if versions_data:
        base_version = versions_data[0]["data"]["version"]
        base_label = base_version.get("number") or "—"
    else:
        base_label = "—"

    ws["B5"] = "База:"
    ws["B5"].font = font_meta_label

    ws["D5"] = base_label
    ws["D5"].font = font_meta_value

    ws["B6"] = "Версий:"
    ws["B6"].font = font_meta_label

    ws["D6"] = len(versions_data)
    ws["D6"].font = font_meta_value

    current_row = 8
    _write_section_bar(ws, current_row, "ВЫБРАННЫЕ ВЕРСИИ", fill_section, font_section, align_left)
    current_row += 1

    headers = ["#", "Версия", "Сценарий", "Дата начала", "Дата окончания"]
    header_cols = [2, 3, 4, 5, 6]  # B:F

    for col_idx, header in zip(header_cols, headers):
        cell = ws.cell(row=current_row, column=col_idx, value=header)
        cell.fill = FILLS["header"]
        cell.font = FONTS["header_white"]
        cell.border = BORDERS["thin"]
        cell.alignment = ALIGNMENTS["center_wrap"]

    current_row += 1

    for idx, item in enumerate(versions_data, start=1):
        version = item["data"]["version"]

        values = [
            "База" if idx == 1 else str(idx),
            version.get("number") or "—",
            _scenario_label(item["data"]),
            version.get("date_from"),
            version.get("date_to"),
        ]

        for excel_col, value in zip(header_cols, values):
            cell = ws.cell(row=current_row, column=excel_col, value=value)
            cell.border = BORDERS["thin"]

            if excel_col == 2:
                cell.font = FONTS["bold"]
                cell.alignment = ALIGNMENTS["left"]
            elif excel_col in (5, 6):
                cell.font = FONTS["normal"]
                cell.alignment = ALIGNMENTS["center"]
                if hasattr(value, "year"):
                    apply_date(cell)
            else:
                cell.font = FONTS["normal"]
                cell.alignment = ALIGNMENTS["left"]

        current_row += 1

    current_row += 1
    _write_section_bar(ws, current_row, "СОДЕРЖАНИЕ", fill_section, font_section, align_left)
    ws.row_dimensions[current_row].height = 25
    current_row += 2

    toc_items = [
        {"num": "1", "title": "Сравнение по статьям — итог за период", "sheet": "ARTICLES_COMPARE"},
        {"num": "2", "title": "Сравнение по статьям — по месяцам", "sheet": "MONTHS_COMPARE"},
        {"num": "3", "title": "Сравнение по статьям — по кварталам", "sheet": "QUARTERS_COMPARE"},
    ]

    for item in toc_items:
        _draw_toc_item_row(
            ws,
            current_row,
            item["num"],
            item["title"],
            item["sheet"],
            ws.parent,
            font_num=font_num_main,
            font_link=font_link_main,
        )
        ws.row_dimensions[current_row].height = 24
        current_row += 1

    current_row += 1
    _write_section_bar(ws, current_row, "КАК ЧИТАТЬ ОТЧЕТ", fill_section, font_section, align_left)
    ws.row_dimensions[current_row].height = 25
    current_row += 1

    tips = [
        ("База", "Версия, с которой сравниваются остальные"),
        ("Δ к базе", "Отклонение версии от базы в рублях"),
        ("Δ %", "Отклонение версии от базы в процентах"),
        ("Прим.", "Номер листа с детальной расшифровкой"),
    ]

    dotted_border = Border(
        bottom=Side(style="dotted", color=COLORS["border_gray"])
    )

    for label, value in tips:
        for col in range(2, 6):  # B:E
            cell = ws.cell(row=current_row, column=col)
            cell.border = dotted_border
            cell.fill = FILLS["none"]

        l_cell = ws.cell(row=current_row, column=2, value=label)
        v_cell = ws.cell(row=current_row, column=4, value=value)

        l_cell.font = FONTS["bold"]
        v_cell.font = FONTS["normal"]

        l_cell.alignment = ALIGNMENTS["left"]
        v_cell.alignment = ALIGNMENTS["left"]

        current_row += 1

    ws.freeze_panes = "A1"