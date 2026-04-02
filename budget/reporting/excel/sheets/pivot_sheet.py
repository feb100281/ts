# # budget/reporting/excel/sheets/pivot_sheet.py
# from openpyxl.styles import Alignment

# from budget.reporting.excel.styles.helpers import (
#     set_column_widths,
#     set_row_heights,
#     draw_back_button,
#     draw_sheet_header,
# )
# from budget.reporting.excel.styles.theme import (
#     FILLS,
#     FONTS,
#     BORDERS,
#     ALIGNMENTS,
#     FORMATS,
# )


# def _label_alignment(level=0):
#     return Alignment(horizontal="left", vertical="center", indent=level)


# def _draw_separator_row(ws, row_idx, last_col):
#     for col in range(1, last_col + 1):
#         cell = ws.cell(row=row_idx, column=col)
#         cell.fill = FILLS["none"]
#         cell.border = BORDERS["none"]
#     ws.row_dimensions[row_idx].height = 6


# def _build_month_layout(months):
#     layout = []
#     col = 3  # A = Статья, B = Прим.

#     for month in months:
#         layout.append({
#             "type": "month",
#             "label": month,
#             "value_col": col,
#         })
#         col += 1

#         # spacer после каждого месяца, в том числе перед ИТОГО
#         layout.append({
#             "type": "spacer",
#             "value_col": col,
#         })
#         col += 1

#     total_col = col
#     return layout, total_col


# def _draw_header(ws, row_idx, months_layout, total_col):
#     cell = ws.cell(row=row_idx, column=1, value="Статья")
#     cell.fill = FILLS["header"]
#     cell.font = FONTS["header_white"]
#     cell.border = BORDERS["thin"]
#     cell.alignment = ALIGNMENTS["center"]

#     note_cell = ws.cell(row=row_idx, column=2, value="Прим.")
#     note_cell.fill = FILLS["header"]
#     note_cell.font = FONTS["header_white"]
#     note_cell.border = BORDERS["thin"]
#     note_cell.alignment = ALIGNMENTS["center"]

#     for item in months_layout:
#         col = item["value_col"]

#         if item["type"] == "month":
#             cell = ws.cell(row=row_idx, column=col, value=item["label"])
#             cell.fill = FILLS["header"]
#             cell.font = FONTS["header_white"]
#             cell.border = BORDERS["thin"]
#             cell.alignment = ALIGNMENTS["center"]
#         else:
#             spacer = ws.cell(row=row_idx, column=col, value=None)
#             spacer.fill = FILLS["none"]
#             spacer.border = BORDERS["none"]

#     total_cell = ws.cell(row=row_idx, column=total_col, value="ИТОГО")
#     total_cell.fill = FILLS["header"]
#     total_cell.font = FONTS["header_white"]
#     total_cell.border = BORDERS["thin"]
#     total_cell.alignment = ALIGNMENTS["center"]


# def _get_value_font(value, normal_font, negative_font):
#     try:
#         if value is not None and float(value) < 0:
#             return negative_font
#     except (TypeError, ValueError):
#         pass
#     return normal_font


# def _draw_value_cell(ws, row, col, value, fill, font, negative_font, border):
#     cell = ws.cell(row=row, column=col, value=value)
#     cell.fill = fill
#     cell.font = _get_value_font(value, font, negative_font)
#     cell.border = border
#     cell.number_format = FORMATS["money_int"]
#     cell.alignment = ALIGNMENTS["right"]


# def _draw_data_row(ws, row_idx, item, months_layout, total_col):
#     row_type = item["row_type"]
#     level = item["level"]

#     if row_type == "activity":
#         fill = FILLS["total"]
#         label_font = FONTS["section"]
#         value_font = FONTS["bold"]
#         negative_value_font = FONTS["negative_bold"]
#         border = BORDERS["bottom_medium"]
#         height = 21
#         label_indent = 1

#     elif row_type == "operation":
#         fill = FILLS["none"]
#         label_font = FONTS["bold"]
#         value_font = FONTS["bold"]
#         negative_value_font = FONTS["negative_bold"]
#         border = BORDERS["thin"]
#         height = 19
#         label_indent = 2

#     else:  # item
#         fill = FILLS["none"]
#         label_font = FONTS["bold"]
#         value_font = FONTS["normal"]
#         negative_value_font = FONTS["negative"]
#         border = BORDERS["thin"]
#         height = 18
#         label_indent = 3

#     ws.row_dimensions[row_idx].height = height

#     ws.row_dimensions[row_idx].hidden = False




#     label = ws.cell(row=row_idx, column=1, value=item["label"])
#     label.fill = fill
#     label.font = label_font
#     label.border = border
#     label.alignment = _label_alignment(label_indent)

#     note = item.get("note", "")
#     note_cell = ws.cell(row=row_idx, column=2, value=note)
#     note_cell.fill = fill
#     note_cell.border = border
#     note_cell.alignment = ALIGNMENTS["center"]

#     if note and item.get("sheet_name"):
#         note_cell.font = FONTS["back"]
#         note_cell.hyperlink = f"#'{item['sheet_name']}'!A1"
#     else:
#         note_cell.font = FONTS["normal"]

#     for layout_item in months_layout:
#         col = layout_item["value_col"]

#         if layout_item["type"] == "month":
#             month = layout_item["label"]
#             value = item["months"].get(month, 0)
#             _draw_value_cell(
#                 ws=ws,
#                 row=row_idx,
#                 col=col,
#                 value=value,
#                 fill=fill,
#                 font=value_font,
#                 negative_font=negative_value_font,
#                 border=border,
#             )
#         else:
#             spacer = ws.cell(row=row_idx, column=col, value=None)
#             spacer.fill = FILLS["none"]
#             spacer.border = BORDERS["none"]

#     total_font = FONTS["bold"] if row_type in ("activity", "operation") else value_font
#     negative_total_font = FONTS["negative_bold"] if row_type in ("activity", "operation") else negative_value_font

#     _draw_value_cell(
#         ws=ws,
#         row=row_idx,
#         col=total_col,
#         value=item["total"],
#         fill=fill,
#         font=total_font,
#         negative_font=negative_total_font,
#         border=border,
#     )


# def build_pivot_sheet(wb, data):
#     ws = wb.create_sheet("БЮДЖЕТ")
#     ws.sheet_view.showGridLines = False
#     ws.sheet_view.showOutlineSymbols = False
#     # ws.sheet_properties.outlinePr.summaryBelow = True
#     # ws.sheet_view.showOutlineSymbols = True

#     pivot = data["gl_pivot"]
#     months = pivot["months"]
#     rows = pivot["rows"]

#     months_layout, total_col = _build_month_layout(months)
#     last_col = total_col

#     widths = {
#         "A": 52,
#         "B": 8,
#     }

#     for item in months_layout:
#         col_letter = ws.cell(row=1, column=item["value_col"]).column_letter
#         widths[col_letter] = 16 if item["type"] == "month" else 3

#     widths[ws.cell(row=1, column=total_col).column_letter] = 18

#     set_column_widths(ws, widths)
#     set_row_heights(ws, {
#         1: 20,
#         2: 26,
#         3: 18,
#         4: 18,
#         5: 10,
#         6: 6,
#         7: 24,
#     })

#     # draw_back_button(ws, cell="A1", text="← SUMMARY", target_sheet="SUMMARY")
#     draw_sheet_header(
#         ws,
#         title="БЮДЖЕТ",
#         subtitle=f'Версия: {data["version"]["number"]}',
#         note="Сводная расшифровка GL по месяцам с иерархией статей. Детализация нижнего уровня доступна по ссылкам в колонке «Прим.»",
#     )

#     _draw_separator_row(ws, 6, last_col)
#     _draw_header(ws, 7, months_layout, total_col)

#     row_idx = 8
#     prev_activity = None
#     prev_operation = None

#     for item in rows:
#         if item["row_type"] == "activity":
#             if prev_activity is not None:
#                 _draw_separator_row(ws, row_idx, last_col)
#                 row_idx += 1
#             prev_activity = item["label"]
#             prev_operation = None

#         elif item["row_type"] == "operation":
#             if prev_operation is not None:
#                 _draw_separator_row(ws, row_idx, last_col)
#                 row_idx += 1
#             prev_operation = item["label"]

#         _draw_data_row(ws, row_idx, item, months_layout, total_col)
#         row_idx += 1

#     _draw_separator_row(ws, row_idx, last_col)
#     row_idx += 1

#     gt_label = ws.cell(row=row_idx, column=1, value="ИТОГО")
#     gt_label.fill = FILLS["total"]
#     gt_label.border = BORDERS["bottom_medium"]
#     gt_label.font = FONTS["total"]
#     gt_label.alignment = ALIGNMENTS["left"]

#     gt_note = ws.cell(row=row_idx, column=2, value=None)
#     gt_note.fill = FILLS["total"]
#     gt_note.border = BORDERS["bottom_medium"]

#     for layout_item in months_layout:
#         col = layout_item["value_col"]

#         if layout_item["type"] == "month":
#             value = pivot["grand_total"].get(layout_item["label"], 0)
#             cell = ws.cell(row=row_idx, column=col, value=value)
#             cell.fill = FILLS["total"]
#             cell.border = BORDERS["bottom_medium"]
#             cell.font = _get_value_font(value, FONTS["total"], FONTS["negative_total"])
#             cell.number_format = FORMATS["money_int"]
#             cell.alignment = ALIGNMENTS["right"]
#         else:
#             spacer = ws.cell(row=row_idx, column=col, value=None)
#             spacer.fill = FILLS["none"]
#             spacer.border = BORDERS["none"]

#     gt_sum = ws.cell(row=row_idx, column=total_col, value=pivot["grand_total_sum"])
#     gt_sum.fill = FILLS["total"]
#     gt_sum.border = BORDERS["bottom_medium"]
#     gt_sum.font = _get_value_font(pivot["grand_total_sum"], FONTS["total"], FONTS["negative_total"])
#     gt_sum.number_format = FORMATS["money_int"]
#     gt_sum.alignment = ALIGNMENTS["right"]

#     ws.freeze_panes = "C8"







# budget/reporting/excel/sheets/pivot_sheet.py
from openpyxl.styles import Alignment
from openpyxl.utils import get_column_letter

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


def _label_alignment(level=0):
    return Alignment(horizontal="left", vertical="center", indent=level)


def _draw_separator_row(ws, row_idx, last_col):
    for col in range(1, last_col + 1):
        cell = ws.cell(row=row_idx, column=col)
        cell.fill = FILLS["none"]
        cell.border = BORDERS["none"]
    ws.row_dimensions[row_idx].height = 6
    
    


def _hide_fact_and_delta_columns(ws, months_layout, total_fact_col, total_delta_col):
    ws.sheet_properties.outlinePr.summaryBelow = False
    ws.sheet_properties.outlinePr.summaryRight = True

    for item in months_layout:
        if item["type"] in ("fact", "delta"):
            col_letter = get_column_letter(item["value_col"])
            ws.column_dimensions[col_letter].hidden = True
            ws.column_dimensions[col_letter].outline_level = 1

    # скрываем итоговые колонки
    for col in (total_fact_col, total_delta_col):
        col_letter = get_column_letter(col)
        ws.column_dimensions[col_letter].hidden = True
        ws.column_dimensions[col_letter].outline_level = 1


def _build_month_layout(months):
    layout = []
    col = 3  # A = Статья, B = Прим.

    for month in months:
        layout.append({
            "type": "plan",
            "month": month,
            "label": f"{month} План",
            "value_col": col,
        })
        col += 1

        layout.append({
            "type": "fact",
            "month": month,
            "label": f"{month} Факт",
            "value_col": col,
        })
        col += 1

        layout.append({
            "type": "delta",
            "month": month,
            "label": f"{month} Δ",
            "value_col": col,
        })
        col += 1

        layout.append({
            "type": "spacer",
            "value_col": col,
        })
        col += 1

    total_plan_col = col
    col += 1
    total_fact_col = col
    col += 1
    total_delta_col = col

    return layout, total_plan_col, total_fact_col, total_delta_col


def _draw_header(ws, row_idx, months_layout, total_plan_col, total_fact_col, total_delta_col):
    cell = ws.cell(row=row_idx, column=1, value="Статья")
    cell.fill = FILLS["header"]
    cell.font = FONTS["header_white"]
    cell.border = BORDERS["thin"]
    cell.alignment = ALIGNMENTS["center"]

    note_cell = ws.cell(row=row_idx, column=2, value="Прим.")
    note_cell.fill = FILLS["header"]
    note_cell.font = FONTS["header_white"]
    note_cell.border = BORDERS["thin"]
    note_cell.alignment = ALIGNMENTS["center"]

    for item in months_layout:
        col = item["value_col"]

        if item["type"] == "spacer":
            spacer = ws.cell(row=row_idx, column=col, value=None)
            spacer.fill = FILLS["none"]
            spacer.border = BORDERS["none"]
        else:
            cell = ws.cell(row=row_idx, column=col, value=item["label"])
            cell.fill = FILLS["header"]
            cell.font = FONTS["header_white"]
            cell.border = BORDERS["thin"]
            cell.alignment = ALIGNMENTS["center"]

    for col, title in [
        (total_plan_col, "ИТОГО План"),
        (total_fact_col, "ИТОГО Факт"),
        (total_delta_col, "ИТОГО Δ"),
    ]:
        total_cell = ws.cell(row=row_idx, column=col, value=title)
        total_cell.fill = FILLS["header"]
        total_cell.font = FONTS["header_white"]
        total_cell.border = BORDERS["thin"]
        total_cell.alignment = ALIGNMENTS["center"]


def _get_value_font(value, normal_font, negative_font):
    try:
        if value is not None and float(value) < 0:
            return negative_font
    except (TypeError, ValueError):
        pass
    return normal_font


def _get_delta_fill(value, default_fill):
    try:
        value = float(value or 0)
    except (TypeError, ValueError):
        return default_fill

    if value < 0:
        return FILLS["delta_red"]
    elif value > 0:
        return FILLS["delta_green"]
    return default_fill


def _draw_value_cell(ws, row, col, value, fill, font, negative_font, border, is_delta=False):
    cell = ws.cell(row=row, column=col, value=value)
    cell.fill = _get_delta_fill(value, fill) if is_delta else fill
    cell.font = _get_value_font(value, font, negative_font)
    cell.border = border
    cell.number_format = FORMATS["money_int"]
    cell.alignment = ALIGNMENTS["right"]


def _draw_data_row(ws, row_idx, item, months_layout, total_plan_col, total_fact_col, total_delta_col):
    row_type = item["row_type"]

    if row_type == "activity":
        fill = FILLS["total"]
        label_font = FONTS["section"]
        value_font = FONTS["bold"]
        negative_value_font = FONTS["negative_bold"]
        border = BORDERS["bottom_medium"]
        height = 21
        label_indent = 1

    elif row_type == "operation":
        fill = FILLS["none"]
        label_font = FONTS["bold"]
        value_font = FONTS["bold"]
        negative_value_font = FONTS["negative_bold"]
        border = BORDERS["thin"]
        height = 19
        label_indent = 2

    else:  # item
        fill = FILLS["none"]
        label_font = FONTS["bold"]
        value_font = FONTS["normal"]
        negative_value_font = FONTS["negative"]
        border = BORDERS["thin"]
        height = 18
        label_indent = 3

    ws.row_dimensions[row_idx].height = height
    ws.row_dimensions[row_idx].hidden = False

    label = ws.cell(row=row_idx, column=1, value=item["label"])
    label.fill = fill
    label.font = label_font
    label.border = border
    label.alignment = _label_alignment(label_indent)

    note = item.get("note", "")
    note_cell = ws.cell(row=row_idx, column=2, value=note)
    note_cell.fill = fill
    note_cell.border = border
    note_cell.alignment = ALIGNMENTS["center"]

    if note and item.get("sheet_name"):
        note_cell.font = FONTS["back"]
        note_cell.hyperlink = f"#'{item['sheet_name']}'!A1"
    else:
        note_cell.font = FONTS["normal"]

    for layout_item in months_layout:
        col = layout_item["value_col"]

        if layout_item["type"] == "spacer":
            spacer = ws.cell(row=row_idx, column=col, value=None)
            spacer.fill = FILLS["none"]
            spacer.border = BORDERS["none"]
            continue

        month = layout_item["month"]

        if layout_item["type"] == "plan":
            value = item["plan_months"].get(month, 0)
            is_delta = False
        elif layout_item["type"] == "fact":
            value = item["fact_months"].get(month, 0)
            is_delta = False
        else:  # delta
            value = item["delta_months"].get(month, 0)
            is_delta = True

        _draw_value_cell(
            ws=ws,
            row=row_idx,
            col=col,
            value=value,
            fill=fill,
            font=value_font,
            negative_font=negative_value_font,
            border=border,
            is_delta=is_delta,
        )

    total_font = FONTS["bold"] if row_type in ("activity", "operation") else value_font
    negative_total_font = FONTS["negative_bold"] if row_type in ("activity", "operation") else negative_value_font

    _draw_value_cell(
        ws=ws,
        row=row_idx,
        col=total_plan_col,
        value=item["plan_total"],
        fill=fill,
        font=total_font,
        negative_font=negative_total_font,
        border=border,
    )

    _draw_value_cell(
        ws=ws,
        row=row_idx,
        col=total_fact_col,
        value=item["fact_total"],
        fill=fill,
        font=total_font,
        negative_font=negative_total_font,
        border=border,
    )

    _draw_value_cell(
            ws=ws,
            row=row_idx,
            col=total_delta_col,
            value=item["delta_total"],
            fill=fill,
            font=total_font,
            negative_font=negative_total_font,
            border=border,
            is_delta=True,
        )


def build_pivot_sheet(wb, data):
    ws = wb.create_sheet("БЮДЖЕТ")
    ws.sheet_view.showGridLines = False
    ws.sheet_view.showOutlineSymbols = True

    pivot = data["gl_pivot"]
    months = pivot["months"]
    rows = pivot["rows"]

    months_layout, total_plan_col, total_fact_col, total_delta_col = _build_month_layout(months)
    last_col = total_delta_col

    widths = {
        "A": 52,
        "B": 8,
    }

    for item in months_layout:
        col_letter = ws.cell(row=1, column=item["value_col"]).column_letter
        widths[col_letter] = 16 if item["type"] != "spacer" else 3

    widths[ws.cell(row=1, column=total_plan_col).column_letter] = 18
    widths[ws.cell(row=1, column=total_fact_col).column_letter] = 18
    widths[ws.cell(row=1, column=total_delta_col).column_letter] = 18

    set_column_widths(ws, widths)
    set_row_heights(ws, {
        1: 20,
        2: 26,
        3: 18,
        4: 18,
        5: 10,
        6: 6,
        7: 24,
    })

    # draw_back_button(ws, cell="A1", text="← SUMMARY", target_sheet="SUMMARY")
    draw_sheet_header(
        ws,
        title="БЮДЖЕТ",
        subtitle=f'Версия: {data["version"]["number"]}',
        note="Сводная расшифровка по месяцам: План / Факт / Δ.",
    )

    _draw_separator_row(ws, 6, last_col)
    _draw_header(ws, 7, months_layout, total_plan_col, total_fact_col, total_delta_col)

    row_idx = 8
    prev_activity = None
    prev_operation = None

    for item in rows:
        if item["row_type"] == "activity":
            if prev_activity is not None:
                _draw_separator_row(ws, row_idx, last_col)
                row_idx += 1
            prev_activity = item["label"]
            prev_operation = None

        elif item["row_type"] == "operation":
            if prev_operation is not None:
                _draw_separator_row(ws, row_idx, last_col)
                row_idx += 1
            prev_operation = item["label"]

        _draw_data_row(
            ws,
            row_idx,
            item,
            months_layout,
            total_plan_col,
            total_fact_col,
            total_delta_col,
        )
        row_idx += 1

    _draw_separator_row(ws, row_idx, last_col)
    row_idx += 1

    gt_label = ws.cell(row=row_idx, column=1, value="ИТОГО")
    gt_label.fill = FILLS["total"]
    gt_label.border = BORDERS["bottom_medium"]
    gt_label.font = FONTS["total"]
    gt_label.alignment = ALIGNMENTS["left"]

    gt_note = ws.cell(row=row_idx, column=2, value=None)
    gt_note.fill = FILLS["total"]
    gt_note.border = BORDERS["bottom_medium"]

    for layout_item in months_layout:
        col = layout_item["value_col"]

        if layout_item["type"] == "spacer":
            spacer = ws.cell(row=row_idx, column=col, value=None)
            spacer.fill = FILLS["none"]
            spacer.border = BORDERS["none"]
            continue

        month = layout_item["month"]

        if layout_item["type"] == "plan":
            value = pivot["grand_plan_total"].get(month, 0)
        elif layout_item["type"] == "fact":
            value = pivot["grand_fact_total"].get(month, 0)
        else:
            value = pivot["grand_delta_total"].get(month, 0)

        cell = ws.cell(row=row_idx, column=col, value=value)

        if layout_item["type"] == "delta":
            cell.fill = _get_delta_fill(value, FILLS["total"])
        else:
            cell.fill = FILLS["total"]

        cell.border = BORDERS["bottom_medium"]
        cell.font = _get_value_font(value, FONTS["total"], FONTS["negative_total"])
        cell.number_format = FORMATS["money_int"]
        cell.alignment = ALIGNMENTS["right"]

    gt_plan = ws.cell(row=row_idx, column=total_plan_col, value=pivot["grand_plan_sum"])
    gt_plan.fill = FILLS["total"]
    gt_plan.border = BORDERS["bottom_medium"]
    gt_plan.font = _get_value_font(pivot["grand_plan_sum"], FONTS["total"], FONTS["negative_total"])
    gt_plan.number_format = FORMATS["money_int"]
    gt_plan.alignment = ALIGNMENTS["right"]

    gt_fact = ws.cell(row=row_idx, column=total_fact_col, value=pivot["grand_fact_sum"])
    gt_fact.fill = FILLS["total"]
    gt_fact.border = BORDERS["bottom_medium"]
    gt_fact.font = _get_value_font(pivot["grand_fact_sum"], FONTS["total"], FONTS["negative_total"])
    gt_fact.number_format = FORMATS["money_int"]
    gt_fact.alignment = ALIGNMENTS["right"]

    gt_delta = ws.cell(row=row_idx, column=total_delta_col, value=pivot["grand_delta_sum"])
    gt_delta.fill = _get_delta_fill(pivot["grand_delta_sum"], FILLS["total"])
    gt_delta.border = BORDERS["bottom_medium"]
    gt_delta.font = _get_value_font(pivot["grand_delta_sum"], FONTS["total"], FONTS["negative_total"])
    gt_delta.number_format = FORMATS["money_int"]
    gt_delta.alignment = ALIGNMENTS["right"]

    _hide_fact_and_delta_columns(ws, months_layout, total_fact_col, total_delta_col)
    ws.freeze_panes = "C8"