# # budget/reporting/excel/sheets/gl_detail_sheet.py
# from openpyxl.utils import get_column_letter

# from budget.reporting.excel.styles.helpers import (
#     set_column_widths,
#     set_row_heights,
#     draw_back_button,
#     draw_sheet_header,
#     get_delta_fill,
# )
# from budget.reporting.excel.styles.theme import (
#     FILLS,
#     FONTS,
#     BORDERS,
#     ALIGNMENTS,
#     FORMATS,
# )


# def _hide_fact_and_delta_columns(ws, month_layout, total_fact_col, total_delta_col):
#     ws.sheet_properties.outlinePr.summaryBelow = False
#     ws.sheet_properties.outlinePr.summaryRight = True
#     ws.sheet_view.showOutlineSymbols = True

#     for item in month_layout:
#         if item["type"] in ("fact", "delta"):
#             col_letter = get_column_letter(item["col"])
#             ws.column_dimensions[col_letter].hidden = True
#             ws.column_dimensions[col_letter].outline_level = 1

#     for col in (total_fact_col, total_delta_col):
#         col_letter = get_column_letter(col)
#         ws.column_dimensions[col_letter].hidden = True
#         ws.column_dimensions[col_letter].outline_level = 1


# def build_gl_detail_sheet(wb, detail):
#     ws = wb.create_sheet(detail["sheet_name"])
#     ws.sheet_view.showGridLines = False
#     ws.sheet_view.showOutlineSymbols = True

#     months = detail["months"]

#     # A = Статья, дальше по 3 колонки на каждый месяц + spacer
#     col = 2
#     month_layout = []
#     for month in months:
#         month_layout.append({"type": "plan", "month": month, "label": f"{month} План", "col": col})
#         col += 1
#         month_layout.append({"type": "fact", "month": month, "label": f"{month} Факт", "col": col})
#         col += 1
#         month_layout.append({"type": "delta", "month": month, "label": f"{month} Δ", "col": col})
#         col += 1
#         month_layout.append({"type": "spacer", "col": col})
#         col += 1

#     total_plan_col = col
#     col += 1
#     total_fact_col = col
#     col += 1
#     total_delta_col = col

#     widths = {"A": 54}
#     for item in month_layout:
#         col_letter = ws.cell(row=1, column=item["col"]).column_letter
#         widths[col_letter] = 16 if item["type"] != "spacer" else 3

#     widths[ws.cell(row=1, column=total_plan_col).column_letter] = 18
#     widths[ws.cell(row=1, column=total_fact_col).column_letter] = 18
#     widths[ws.cell(row=1, column=total_delta_col).column_letter] = 18

#     set_column_widths(ws, widths)
#     set_row_heights(ws, {
#         1: 20,
#         2: 26,
#         3: 18,
#         4: 18,
#         5: 10,
#         6: 24,
#     })

#     draw_back_button(ws, cell="A1", text="← БЮДЖЕТ", target_sheet="БЮДЖЕТ")
#     draw_sheet_header(
#         ws,
#         title=f'РАСШИФРОВКА {detail["note"]}',
#         subtitle=detail["item"],
#         note=f'{detail["activity"]} | {detail["operation"]}',
#     )

#     # header
#     ws["A6"] = "Статья"
#     ws["A6"].fill = FILLS["header"]
#     ws["A6"].font = FONTS["header_white"]
#     ws["A6"].alignment = ALIGNMENTS["center"]
#     ws["A6"].border = BORDERS["thin"]

#     for item in month_layout:
#         col_idx = item["col"]
#         if item["type"] == "spacer":
#             cell = ws.cell(row=6, column=col_idx, value=None)
#             cell.fill = FILLS["none"]
#             cell.border = BORDERS["none"]
#         else:
#             cell = ws.cell(row=6, column=col_idx, value=item["label"])
#             cell.fill = FILLS["header"]
#             cell.font = FONTS["header_white"]
#             cell.alignment = ALIGNMENTS["center"]
#             cell.border = BORDERS["thin"]

#     for col_idx, title in [
#         (total_plan_col, "ИТОГО План"),
#         (total_fact_col, "ИТОГО Факт"),
#         (total_delta_col, "ИТОГО Δ"),
#     ]:
#         cell = ws.cell(row=6, column=col_idx, value=title)
#         cell.fill = FILLS["header"]
#         cell.font = FONTS["header_white"]
#         cell.alignment = ALIGNMENTS["center"]
#         cell.border = BORDERS["thin"]

#     row_idx = 7
#     for row in detail["rows"]:
#         label_cell = ws.cell(row=row_idx, column=1, value=row["label"])
#         label_cell.font = FONTS["normal"]
#         label_cell.alignment = ALIGNMENTS["left"]
#         label_cell.border = BORDERS["thin"]
#         label_cell.fill = FILLS["none"]

#         for layout_item in month_layout:
#             col_idx = layout_item["col"]

#             if layout_item["type"] == "spacer":
#                 cell = ws.cell(row=row_idx, column=col_idx, value=None)
#                 cell.fill = FILLS["none"]
#                 cell.border = BORDERS["none"]
#                 continue

#             month = layout_item["month"]
#             if layout_item["type"] == "plan":
#                 value = row["plan_months"].get(month, 0)
#             elif layout_item["type"] == "fact":
#                 value = row["fact_months"].get(month, 0)
#             else:
#                 value = row["delta_months"].get(month, 0)

#             cell = ws.cell(row=row_idx, column=col_idx, value=value)
#             cell.fill = get_delta_fill(value, FILLS["none"], FILLS) if layout_item["type"] == "delta" else FILLS["none"]
#             cell.font = FONTS["negative"] if value < 0 else FONTS["normal"]
#             cell.alignment = ALIGNMENTS["right"]
#             cell.border = BORDERS["thin"]
#             cell.number_format = FORMATS["money_int"]

#         total_plan_cell = ws.cell(row=row_idx, column=total_plan_col, value=row["plan_total"])
#         total_plan_cell.fill = FILLS["none"]
#         total_plan_cell.font = FONTS["negative"] if row["plan_total"] < 0 else FONTS["normal"]
#         total_plan_cell.alignment = ALIGNMENTS["right"]
#         total_plan_cell.border = BORDERS["thin"]
#         total_plan_cell.number_format = FORMATS["money_int"]

#         total_fact_cell = ws.cell(row=row_idx, column=total_fact_col, value=row["fact_total"])
#         total_fact_cell.fill = FILLS["none"]
#         total_fact_cell.font = FONTS["negative"] if row["fact_total"] < 0 else FONTS["normal"]
#         total_fact_cell.alignment = ALIGNMENTS["right"]
#         total_fact_cell.border = BORDERS["thin"]
#         total_fact_cell.number_format = FORMATS["money_int"]

#         total_delta_cell = ws.cell(row=row_idx, column=total_delta_col, value=row["delta_total"])
#         total_delta_cell.fill = get_delta_fill(row["delta_total"], FILLS["none"], FILLS)
#         total_delta_cell.font = FONTS["negative"] if row["delta_total"] < 0 else FONTS["normal"]
#         total_delta_cell.alignment = ALIGNMENTS["right"]
#         total_delta_cell.border = BORDERS["thin"]
#         total_delta_cell.number_format = FORMATS["money_int"]

#         row_idx += 1

#     # total row
#     total_label = ws.cell(row=row_idx, column=1, value="ИТОГО")
#     total_label.fill = FILLS["total"]
#     total_label.font = FONTS["total"]
#     total_label.alignment = ALIGNMENTS["left"]
#     total_label.border = BORDERS["bottom_medium"]

#     for layout_item in month_layout:
#         col_idx = layout_item["col"]

#         if layout_item["type"] == "spacer":
#             cell = ws.cell(row=row_idx, column=col_idx, value=None)
#             cell.fill = FILLS["none"]
#             cell.border = BORDERS["none"]
#             continue

#         month = layout_item["month"]
#         if layout_item["type"] == "plan":
#             value = detail["total_plan_by_month"].get(month, 0)
#         elif layout_item["type"] == "fact":
#             value = detail["total_fact_by_month"].get(month, 0)
#         else:
#             value = detail["total_delta_by_month"].get(month, 0)

#         cell = ws.cell(row=row_idx, column=col_idx, value=value)
#         cell.fill = get_delta_fill(value, FILLS["total"], FILLS) if layout_item["type"] == "delta" else FILLS["total"]
#         cell.font = FONTS["negative_total"] if value < 0 else FONTS["total"]
#         cell.alignment = ALIGNMENTS["right"]
#         cell.border = BORDERS["bottom_medium"]
#         cell.number_format = FORMATS["money_int"]

#     total_plan_sum_cell = ws.cell(row=row_idx, column=total_plan_col, value=detail["plan_total"])
#     total_plan_sum_cell.fill = FILLS["total"]
#     total_plan_sum_cell.font = FONTS["negative_total"] if detail["plan_total"] < 0 else FONTS["total"]
#     total_plan_sum_cell.alignment = ALIGNMENTS["right"]
#     total_plan_sum_cell.border = BORDERS["bottom_medium"]
#     total_plan_sum_cell.number_format = FORMATS["money_int"]

#     total_fact_sum_cell = ws.cell(row=row_idx, column=total_fact_col, value=detail["fact_total"])
#     total_fact_sum_cell.fill = FILLS["total"]
#     total_fact_sum_cell.font = FONTS["negative_total"] if detail["fact_total"] < 0 else FONTS["total"]
#     total_fact_sum_cell.alignment = ALIGNMENTS["right"]
#     total_fact_sum_cell.border = BORDERS["bottom_medium"]
#     total_fact_sum_cell.number_format = FORMATS["money_int"]

#     total_delta_sum_cell = ws.cell(row=row_idx, column=total_delta_col, value=detail["delta_total"])
#     total_delta_sum_cell.fill = get_delta_fill(detail["delta_total"], FILLS["total"], FILLS)
#     total_delta_sum_cell.font = FONTS["negative_total"] if detail["delta_total"] < 0 else FONTS["total"]
#     total_delta_sum_cell.alignment = ALIGNMENTS["right"]
#     total_delta_sum_cell.border = BORDERS["bottom_medium"]
#     total_delta_sum_cell.number_format = FORMATS["money_int"]

#     _hide_fact_and_delta_columns(ws, month_layout, total_fact_col, total_delta_col)

#     ws.freeze_panes = "B7"





# budget/reporting/excel/sheets/gl_detail_sheet.py

from copy import copy
from openpyxl.utils import get_column_letter

from budget.reporting.excel.styles.helpers import (
    set_column_widths,
    set_row_heights,
    draw_back_button,
    draw_sheet_header,
    get_delta_fill,
)
from budget.reporting.excel.styles.theme import (
    FILLS,
    FONTS,
    BORDERS,
    ALIGNMENTS,
    FORMATS,
)


def _hide_fact_and_delta_columns(ws, month_layout, total_fact_col, total_delta_col):
    ws.sheet_properties.outlinePr.summaryBelow = False
    ws.sheet_properties.outlinePr.summaryRight = True
    ws.sheet_view.showOutlineSymbols = True

    for item in month_layout:
        if item["type"] in ("fact", "delta"):
            col_letter = get_column_letter(item["col"])
            ws.column_dimensions[col_letter].hidden = True
            ws.column_dimensions[col_letter].outline_level = 1

    for col in (total_fact_col, total_delta_col):
        col_letter = get_column_letter(col)
        ws.column_dimensions[col_letter].hidden = True
        ws.column_dimensions[col_letter].outline_level = 1


def _get_row_font(value, is_child=False):
    if is_child:
        return FONTS["counterparty_negative"] if value < 0 else FONTS["counterparty"]
    return FONTS["negative"] if value < 0 else FONTS["normal"]


def _get_label_alignment(is_child=False):
    alignment = copy(ALIGNMENTS["left"])
    if is_child:
        alignment.indent = 2
    return alignment


def _draw_detail_value_row(
    ws,
    row_idx,
    row,
    month_layout,
    total_plan_col,
    total_fact_col,
    total_delta_col,
    is_child=False,
):
    label_value = row.get("label", "—")

    label_cell = ws.cell(row=row_idx, column=1, value=label_value)
    label_cell.fill = FILLS["none"]
    label_cell.border = BORDERS["thin"]
    label_cell.font = FONTS["counterparty"] if is_child else FONTS["normal"]
    label_cell.alignment = _get_label_alignment(is_child=is_child)
    


    for layout_item in month_layout:
        col_idx = layout_item["col"]

        if layout_item["type"] == "spacer":
            cell = ws.cell(row=row_idx, column=col_idx, value=None)
            cell.fill = FILLS["none"]
            cell.border = BORDERS["none"]
            continue

        month = layout_item["month"]

        if layout_item["type"] == "plan":
            value = row["plan_months"].get(month, 0)
        elif layout_item["type"] == "fact":
            value = row["fact_months"].get(month, 0)
        else:
            value = row["delta_months"].get(month, 0)

        cell = ws.cell(row=row_idx, column=col_idx, value=value)
        cell.fill = get_delta_fill(value, FILLS["none"], FILLS) if layout_item["type"] == "delta" else FILLS["none"]
        cell.font = _get_row_font(value, is_child=is_child)
        cell.alignment = ALIGNMENTS["right"]
        cell.border = BORDERS["thin"]
        cell.number_format = FORMATS["money_int"]

    total_plan_value = row["plan_total"]
    total_plan_cell = ws.cell(row=row_idx, column=total_plan_col, value=total_plan_value)
    total_plan_cell.fill = FILLS["none"]
    total_plan_cell.font = _get_row_font(total_plan_value, is_child=is_child)
    total_plan_cell.alignment = ALIGNMENTS["right"]
    total_plan_cell.border = BORDERS["thin"]
    total_plan_cell.number_format = FORMATS["money_int"]

    total_fact_value = row["fact_total"]
    total_fact_cell = ws.cell(row=row_idx, column=total_fact_col, value=total_fact_value)
    total_fact_cell.fill = FILLS["none"]
    total_fact_cell.font = _get_row_font(total_fact_value, is_child=is_child)
    total_fact_cell.alignment = ALIGNMENTS["right"]
    total_fact_cell.border = BORDERS["thin"]
    total_fact_cell.number_format = FORMATS["money_int"]

    total_delta_value = row["delta_total"]
    total_delta_cell = ws.cell(row=row_idx, column=total_delta_col, value=total_delta_value)
    total_delta_cell.fill = get_delta_fill(total_delta_value, FILLS["none"], FILLS)
    total_delta_cell.font = _get_row_font(total_delta_value, is_child=is_child)
    total_delta_cell.alignment = ALIGNMENTS["right"]
    total_delta_cell.border = BORDERS["thin"]
    total_delta_cell.number_format = FORMATS["money_int"]

    ws.row_dimensions[row_idx].height = 18 if not is_child else 17


def build_gl_detail_sheet(wb, detail):
    ws = wb.create_sheet(detail["sheet_name"])
    ws.sheet_view.showGridLines = False
    ws.sheet_view.showOutlineSymbols = True

    months = detail["months"]

    col = 2
    month_layout = []
    for month in months:
        month_layout.append({"type": "plan", "month": month, "label": f"{month} План", "col": col})
        col += 1
        month_layout.append({"type": "fact", "month": month, "label": f"{month} Факт", "col": col})
        col += 1
        month_layout.append({"type": "delta", "month": month, "label": f"{month} Δ", "col": col})
        col += 1
        month_layout.append({"type": "spacer", "col": col})
        col += 1

    total_plan_col = col
    col += 1
    total_fact_col = col
    col += 1
    total_delta_col = col

    widths = {"A": 54}
    for item in month_layout:
        col_letter = ws.cell(row=1, column=item["col"]).column_letter
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
        6: 24,
    })

    draw_back_button(ws, cell="A1", text="← БЮДЖЕТ", target_sheet="БЮДЖЕТ")
    draw_sheet_header(
        ws,
        title=f'РАСШИФРОВКА {detail["note"]}',
        subtitle=detail["item"],
        note=f'{detail["activity"]} | {detail["operation"]}',
    )

    ws["A6"] = "Статья"
    ws["A6"].fill = FILLS["header"]
    ws["A6"].font = FONTS["header_white"]
    ws["A6"].alignment = ALIGNMENTS["center"]
    ws["A6"].border = BORDERS["thin"]

    for item in month_layout:
        col_idx = item["col"]
        if item["type"] == "spacer":
            cell = ws.cell(row=6, column=col_idx, value=None)
            cell.fill = FILLS["none"]
            cell.border = BORDERS["none"]
        else:
            cell = ws.cell(row=6, column=col_idx, value=item["label"])
            cell.fill = FILLS["header"]
            cell.font = FONTS["header_white"]
            cell.alignment = ALIGNMENTS["center"]
            cell.border = BORDERS["thin"]

    for col_idx, title in [
        (total_plan_col, "ИТОГО План"),
        (total_fact_col, "ИТОГО Факт"),
        (total_delta_col, "ИТОГО Δ"),
    ]:
        cell = ws.cell(row=6, column=col_idx, value=title)
        cell.fill = FILLS["header"]
        cell.font = FONTS["header_white"]
        cell.alignment = ALIGNMENTS["center"]
        cell.border = BORDERS["thin"]

    row_idx = 7
    for row in detail["rows"]:
        _draw_detail_value_row(
            ws=ws,
            row_idx=row_idx,
            row=row,
            month_layout=month_layout,
            total_plan_col=total_plan_col,
            total_fact_col=total_fact_col,
            total_delta_col=total_delta_col,
            is_child=False,
        )

        row_idx += 1

        for child in row.get("children", []):
            _draw_detail_value_row(
                ws=ws,
                row_idx=row_idx,
                row=child,
                month_layout=month_layout,
                total_plan_col=total_plan_col,
                total_fact_col=total_fact_col,
                total_delta_col=total_delta_col,
                is_child=True,
            )
            ws.row_dimensions[row_idx].hidden = True
            ws.row_dimensions[row_idx].outline_level = 1
            row_idx += 1

    total_label = ws.cell(row=row_idx, column=1, value="ИТОГО")
    total_label.fill = FILLS["total"]
    total_label.font = FONTS["total"]
    total_label.alignment = ALIGNMENTS["left"]
    total_label.border = BORDERS["bottom_medium"]

    for layout_item in month_layout:
        col_idx = layout_item["col"]

        if layout_item["type"] == "spacer":
            cell = ws.cell(row=row_idx, column=col_idx, value=None)
            cell.fill = FILLS["none"]
            cell.border = BORDERS["none"]
            continue

        month = layout_item["month"]
        if layout_item["type"] == "plan":
            value = detail["total_plan_by_month"].get(month, 0)
        elif layout_item["type"] == "fact":
            value = detail["total_fact_by_month"].get(month, 0)
        else:
            value = detail["total_delta_by_month"].get(month, 0)

        cell = ws.cell(row=row_idx, column=col_idx, value=value)
        cell.fill = get_delta_fill(value, FILLS["total"], FILLS) if layout_item["type"] == "delta" else FILLS["total"]
        cell.font = FONTS["negative_total"] if value < 0 else FONTS["total"]
        cell.alignment = ALIGNMENTS["right"]
        cell.border = BORDERS["bottom_medium"]
        cell.number_format = FORMATS["money_int"]

    total_plan_sum_cell = ws.cell(row=row_idx, column=total_plan_col, value=detail["plan_total"])
    total_plan_sum_cell.fill = FILLS["total"]
    total_plan_sum_cell.font = FONTS["negative_total"] if detail["plan_total"] < 0 else FONTS["total"]
    total_plan_sum_cell.alignment = ALIGNMENTS["right"]
    total_plan_sum_cell.border = BORDERS["bottom_medium"]
    total_plan_sum_cell.number_format = FORMATS["money_int"]

    total_fact_sum_cell = ws.cell(row=row_idx, column=total_fact_col, value=detail["fact_total"])
    total_fact_sum_cell.fill = FILLS["total"]
    total_fact_sum_cell.font = FONTS["negative_total"] if detail["fact_total"] < 0 else FONTS["total"]
    total_fact_sum_cell.alignment = ALIGNMENTS["right"]
    total_fact_sum_cell.border = BORDERS["bottom_medium"]
    total_fact_sum_cell.number_format = FORMATS["money_int"]

    total_delta_sum_cell = ws.cell(row=row_idx, column=total_delta_col, value=detail["delta_total"])
    total_delta_sum_cell.fill = get_delta_fill(detail["delta_total"], FILLS["total"], FILLS)
    total_delta_sum_cell.font = FONTS["negative_total"] if detail["delta_total"] < 0 else FONTS["total"]
    total_delta_sum_cell.alignment = ALIGNMENTS["right"]
    total_delta_sum_cell.border = BORDERS["bottom_medium"]
    total_delta_sum_cell.number_format = FORMATS["money_int"]

    _hide_fact_and_delta_columns(ws, month_layout, total_fact_col, total_delta_col)

    ws.freeze_panes = "B7"