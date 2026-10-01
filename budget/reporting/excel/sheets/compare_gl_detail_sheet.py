# budget/reporting/excel/sheets/compare_gl_detail_sheet.py

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


def _scenario_label(data):
    scenario_raw = (data.get("revenue_param") or {}).get("scenario", "base")
    scenario_map = {
        "base": "Базовый",
        "optimistic": "Оптимистичный",
        "conservative": "Консервативный",
    }
    return scenario_map.get(str(scenario_raw).lower(), str(scenario_raw))


def _version_label(version_data):
    version = version_data["data"]["version"]
    scenario = _scenario_label(version_data["data"])
    number = version.get("number") or "—"
    return f"{number} ({scenario})"


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


def _build_total_layout(versions_data):
    layout = []
    col = 2

    layout.append({
        "type": "base",
        "version_idx": 0,
        "label": f"База: {_version_label(versions_data[0])}",
        "col": col,
    })
    col += 1

    for idx, item in enumerate(versions_data[1:], start=1):
        layout.append({
            "type": "compare",
            "version_idx": idx,
            "label": _version_label(item),
            "col": col,
        })
        col += 1

        layout.append({
            "type": "delta_abs",
            "version_idx": idx,
            "label": "Δ к базе",
            "col": col,
        })
        col += 1

        layout.append({
            "type": "delta_pct",
            "version_idx": idx,
            "label": "Δ %",
            "col": col,
        })
        col += 1

        layout.append({
            "type": "spacer",
            "col": col,
        })
        col += 1

    return layout, col - 1


def _build_period_layout(versions_data):
    layout = []
    offset = 0

    layout.append({
        "type": "base",
        "version_idx": 0,
        "label": f"База: {_version_label(versions_data[0])}",
        "offset": offset,
    })
    offset += 1

    for idx, item in enumerate(versions_data[1:], start=1):
        layout.append({
            "type": "compare",
            "version_idx": idx,
            "label": _version_label(item),
            "offset": offset,
        })
        offset += 1

        layout.append({
            "type": "delta_abs",
            "version_idx": idx,
            "label": "Δ к базе",
            "offset": offset,
        })
        offset += 1

        layout.append({
            "type": "delta_pct",
            "version_idx": idx,
            "label": "Δ %",
            "offset": offset,
        })
        offset += 1

    return layout, offset


def _collect_compare_details(versions_data, detail_sheet_map):
    detail_map = {}

    for version_idx, item in enumerate(versions_data):
        pivot = item["data"]["compare_pivot"]

        rows_by_path = {}
        for row in pivot.get("rows", []):
            if row.get("row_type") == "item":
                rows_by_path[row["path_key"]] = row

        for detail in pivot.get("detail_sheets", []):
            path_key = detail.get("path_key")
            if not path_key or path_key not in detail_sheet_map:
                continue

            if path_key not in detail_map:
                detail_map[path_key] = {
                    "sheet_names": detail_sheet_map[path_key],
                    "path_key": path_key,
                    "item": detail.get("item") or "—",
                    "activity": detail.get("activity") or "—",
                    "operation": detail.get("operation") or "—",
                    "rows_map": {},
                    "period_values": {},
                }

            item_row = rows_by_path.get(path_key, {})
            detail_map[path_key]["period_values"][version_idx] = {
                "total": float(item_row.get("total", 0) or 0),
                "months": item_row.get("months", {}) or {},
                "quarters": item_row.get("quarters", {}) or {},
            }

            for row in detail.get("rows", []):
                label = row.get("label") or "—"

                if label not in detail_map[path_key]["rows_map"]:
                    detail_map[path_key]["rows_map"][label] = {
                        "label": label,
                        "values": {},
                    }

                detail_map[path_key]["rows_map"][label]["values"][version_idx] = {
                    "total": float(row.get("total", 0) or 0),
                    "months": row.get("months", {}) or {},
                    "quarters": row.get("quarters", {}) or {},
                }

    result = []
    for _, detail in detail_map.items():
        rows = list(detail["rows_map"].values())
        rows.sort(key=lambda x: x["label"])

        result.append({
            "sheet_names": detail["sheet_names"],
            "path_key": detail["path_key"],
            "item": detail["item"],
            "activity": detail["activity"],
            "operation": detail["operation"],
            "rows": rows,
            "period_values": detail["period_values"],
        })

    def _sheet_sort_key(x):
        total_name = x["sheet_names"]["total"]
        try:
            return int(str(total_name).split("_")[1])
        except (IndexError, ValueError, TypeError):
            return 0

    result.sort(key=_sheet_sort_key)
    return result


def _union_period_keys_and_labels(versions_data, period_type):
    all_keys = set()
    all_labels = {}

    for item in versions_data:
        pivot = item["data"].get("compare_pivot") or {}

        if period_type == "months":
            all_keys.update(pivot.get("months", []) or [])
            all_labels.update(pivot.get("month_labels", {}) or {})
        elif period_type == "quarters":
            all_keys.update(pivot.get("quarters", []) or [])
            all_labels.update(pivot.get("quarter_labels", {}) or {})

    keys = sorted(all_keys)
    labels = {k: all_labels.get(k, k) for k in keys}
    return keys, labels


def _draw_table_header(ws, row_idx, layout, first_col_title="Субстатья"):
    first = ws.cell(row=row_idx, column=1, value=first_col_title)
    first.fill = FILLS["header"]
    first.font = FONTS["header_white"]
    first.alignment = ALIGNMENTS["center"]
    first.border = BORDERS["thin"]

    for item in layout:
        col_idx = item["col"]

        if item["type"] == "spacer":
            cell = ws.cell(row=row_idx, column=col_idx, value=None)
            cell.fill = FILLS["none"]
            cell.border = BORDERS["none"]
        else:
            cell = ws.cell(row=row_idx, column=col_idx, value=item["label"])
            cell.fill = FILLS["header"]
            cell.font = FONTS["header_white"]
            cell.alignment = ALIGNMENTS["center_wrap"]
            cell.border = BORDERS["thin"]


def _draw_period_table_header(ws, top_row, block_cols, period_keys, period_labels, block_width):
    ws.merge_cells(start_row=top_row, start_column=1, end_row=top_row + 1, end_column=1)
    first = ws.cell(row=top_row, column=1, value="Субстатья")
    first.fill = FILLS["header"]
    first.font = FONTS["header_white"]
    first.alignment = ALIGNMENTS["center"]
    first.border = BORDERS["thin"]

    current_col = 2

    for period_index, period_key in enumerate(period_keys):
        content_start_col = current_col
        content_end_col = content_start_col + block_width - 1

        ws.merge_cells(
            start_row=top_row,
            start_column=content_start_col,
            end_row=top_row,
            end_column=content_end_col,
        )

        p_cell = ws.cell(
            row=top_row,
            column=content_start_col,
            value=period_labels.get(period_key, period_key)
        )
        p_cell.fill = FILLS["header"]
        p_cell.font = FONTS["header_white"]
        p_cell.border = BORDERS["thin"]
        p_cell.alignment = ALIGNMENTS["center"]

        for col_idx in range(content_start_col, content_end_col + 1):
            cell = ws.cell(row=top_row, column=col_idx)
            cell.fill = FILLS["header"]
            cell.border = BORDERS["thin"]

        for item in block_cols:
            col_idx = content_start_col + item["offset"]
            cell = ws.cell(row=top_row + 1, column=col_idx, value=item["label"])
            cell.fill = FILLS["header"]
            cell.font = FONTS["header_white"]
            cell.border = BORDERS["thin"]
            cell.alignment = ALIGNMENTS["center_wrap"]

        current_col = content_end_col + 1

        if period_index < len(period_keys) - 1:
            spacer_top = ws.cell(row=top_row, column=current_col, value=None)
            spacer_top.fill = FILLS["none"]
            spacer_top.border = BORDERS["none"]

            spacer_bottom = ws.cell(row=top_row + 1, column=current_col, value=None)
            spacer_bottom.fill = FILLS["none"]
            spacer_bottom.border = BORDERS["none"]

            current_col += 1


def _draw_compare_row(ws, row_idx, label, values_map, layout, fill=FILLS["none"], border=None, bold=False):
    border = border or BORDERS["thin"]
    value_font = FONTS["bold"] if bold else FONTS["normal"]
    negative_font = FONTS["negative_bold"] if bold else FONTS["negative"]

    label_cell = ws.cell(row=row_idx, column=1, value=label)
    label_cell.font = FONTS["bold"] if bold else FONTS["normal"]
    label_cell.alignment = ALIGNMENTS["left"]
    label_cell.border = border
    label_cell.fill = fill

    base_value = float(values_map.get(0, 0) or 0)

    for layout_item in layout:
        col_idx = layout_item["col"]

        if layout_item["type"] == "spacer":
            cell = ws.cell(row=row_idx, column=col_idx, value=None)
            cell.fill = FILLS["none"]
            cell.border = BORDERS["none"]
            continue

        if layout_item["type"] == "base":
            value = base_value
            is_delta = False
            is_percent = False
        else:
            compare_value = float(values_map.get(layout_item["version_idx"], 0) or 0)

            if layout_item["type"] == "compare":
                value = compare_value
                is_delta = False
                is_percent = False
            elif layout_item["type"] == "delta_abs":
                value = compare_value - base_value
                is_delta = True
                is_percent = False
            else:
                value = (compare_value - base_value) / base_value if abs(base_value) > 0.0001 else None
                is_delta = True
                is_percent = True

        cell = ws.cell(row=row_idx, column=col_idx, value=value)
        cell.fill = _get_delta_fill(value, fill) if is_delta else fill
        cell.font = _get_value_font(value, value_font, negative_font)
        cell.alignment = ALIGNMENTS["right"]
        cell.border = border
        cell.number_format = "0.0%;[Red]-0.0%" if is_percent else FORMATS["money_int"]


def _draw_period_compare_row(
    ws,
    row_idx,
    label,
    values_map,
    block_cols,
    period_keys,
    period_type,
    block_width,
    fill=FILLS["none"],
    border=None,
    bold=False,
):
    border = border or BORDERS["thin"]
    value_font = FONTS["bold"] if bold else FONTS["normal"]
    negative_font = FONTS["negative_bold"] if bold else FONTS["negative"]

    label_cell = ws.cell(row=row_idx, column=1, value=label)
    label_cell.font = FONTS["bold"] if bold else FONTS["normal"]
    label_cell.alignment = ALIGNMENTS["left"]
    label_cell.border = border
    label_cell.fill = fill

    current_col = 2

    for period_index, period_key in enumerate(period_keys):
        base_value = float(
            (values_map.get(0, {}).get(period_type, {}) or {}).get(period_key, 0) or 0
        )

        for layout_item in block_cols:
            col_idx = current_col + layout_item["offset"]

            if layout_item["type"] == "base":
                value = base_value
                is_delta = False
                is_percent = False
            else:
                compare_value = float(
                    (values_map.get(layout_item["version_idx"], {}).get(period_type, {}) or {}).get(period_key, 0) or 0
                )

                if layout_item["type"] == "compare":
                    value = compare_value
                    is_delta = False
                    is_percent = False
                elif layout_item["type"] == "delta_abs":
                    value = compare_value - base_value
                    is_delta = True
                    is_percent = False
                else:
                    value = (compare_value - base_value) / base_value if abs(base_value) > 0.0001 else None
                    is_delta = True
                    is_percent = True

            cell = ws.cell(row=row_idx, column=col_idx, value=value)
            cell.fill = _get_delta_fill(value, fill) if is_delta else fill
            cell.font = _get_value_font(value, value_font, negative_font)
            cell.alignment = ALIGNMENTS["right"]
            cell.border = border
            cell.number_format = "0.0%;[Red]-0.0%" if is_percent else FORMATS["money_int"]

        current_col += block_width

        if period_index < len(period_keys) - 1:
            spacer = ws.cell(row=row_idx, column=current_col, value=None)
            spacer.fill = FILLS["none"]
            spacer.border = BORDERS["none"]
            current_col += 1


def _build_total_detail_sheet(wb, detail, versions_data):
    ws = wb.create_sheet(detail["sheet_names"]["total"])
    ws.sheet_view.showGridLines = False

    layout, _ = _build_total_layout(versions_data)

    widths = {"A": 54}
    for item in layout:
        col_letter = ws.cell(row=1, column=item["col"]).column_letter
        widths[col_letter] = 18 if item["type"] != "spacer" else 3

    set_column_widths(ws, widths)
    set_row_heights(ws, {
        1: 20,
        2: 26,
        3: 18,
        4: 18,
        5: 10,
        6: 24,
    })

    draw_back_button(ws, cell="A1", text="← ARTICLES_COMPARE", target_sheet="ARTICLES_COMPARE")
    draw_sheet_header(
        ws,
        title=f'РАСШИФРОВКА № {detail["sheet_names"]["total"]}',
        subtitle=detail["item"],
        note=f'{detail["activity"]} | {detail["operation"]}',
    )

    row_idx = 6
    _draw_table_header(ws, row_idx, layout, first_col_title="Субстатья")
    row_idx += 1

    for row in detail["rows"]:
        values_map = {
            version_idx: float(v.get("total", 0) or 0)
            for version_idx, v in row["values"].items()
        }
        _draw_compare_row(ws, row_idx, row["label"], values_map, layout)
        row_idx += 1

    total_values = {
        version_idx: float(v.get("total", 0) or 0)
        for version_idx, v in detail["period_values"].items()
    }
    _draw_compare_row(
        ws,
        row_idx,
        "ИТОГО ПО СТАТЬЕ",
        total_values,
        layout,
        fill=FILLS["total"],
        border=BORDERS["bottom_medium"],
        bold=True,
    )

    ws.freeze_panes = "B7"


def _build_period_detail_sheet(
    wb,
    detail,
    versions_data,
    period_type,
    period_keys,
    period_labels,
    target_sheet,
    title_prefix,
):
    sheet_name = detail["sheet_names"][period_type]

    ws = wb.create_sheet(sheet_name)
    ws.sheet_view.showGridLines = False

    block_cols, block_width = _build_period_layout(versions_data)

    widths = {"A": 54}
    current_col = 2

    for period_index in range(len(period_keys)):
        for item in block_cols:
            col_idx = current_col + item["offset"]
            col_letter = ws.cell(row=1, column=col_idx).column_letter
            widths[col_letter] = 18

        current_col += block_width

        if period_index < len(period_keys) - 1:
            col_letter = ws.cell(row=1, column=current_col).column_letter
            widths[col_letter] = 3
            current_col += 1

    set_column_widths(ws, widths)
    set_row_heights(ws, {
        1: 20,
        2: 26,
        3: 18,
        4: 18,
        5: 10,
        6: 24,
        7: 28,
    })

    draw_back_button(ws, cell="A1", text=f"← {target_sheet}", target_sheet=target_sheet)
    draw_sheet_header(
        ws,
        title=f'{title_prefix} № {sheet_name}',
        subtitle=detail["item"],
        note=f'{detail["activity"]} | {detail["operation"]}',
    )

    row_idx = 6
    _draw_period_table_header(
        ws,
        top_row=row_idx,
        block_cols=block_cols,
        period_keys=period_keys,
        period_labels=period_labels,
        block_width=block_width,
    )
    row_idx += 2

    for row in detail["rows"]:
        _draw_period_compare_row(
            ws=ws,
            row_idx=row_idx,
            label=row["label"],
            values_map=row["values"],
            block_cols=block_cols,
            period_keys=period_keys,
            period_type=period_type,
            block_width=block_width,
        )
        row_idx += 1

    _draw_period_compare_row(
        ws=ws,
        row_idx=row_idx,
        label="ИТОГО ПО СТАТЬЕ",
        values_map=detail["period_values"],
        block_cols=block_cols,
        period_keys=period_keys,
        period_type=period_type,
        block_width=block_width,
        fill=FILLS["total"],
        border=BORDERS["bottom_medium"],
        bold=True,
    )

    ws.freeze_panes = "B8"


def build_compare_gl_detail_sheets(wb, versions_data, detail_sheet_map):
    details = _collect_compare_details(versions_data, detail_sheet_map)

    month_keys, month_labels = _union_period_keys_and_labels(versions_data, "months")
    quarter_keys, quarter_labels = _union_period_keys_and_labels(versions_data, "quarters")

    for detail in details:
        _build_total_detail_sheet(wb, detail, versions_data)

        _build_period_detail_sheet(
            wb=wb,
            detail=detail,
            versions_data=versions_data,
            period_type="months",
            period_keys=month_keys,
            period_labels=month_labels,
            target_sheet="MONTHS_COMPARE",
            title_prefix="РАСШИФРОВКА ПО МЕСЯЦАМ",
        )

        _build_period_detail_sheet(
            wb=wb,
            detail=detail,
            versions_data=versions_data,
            period_type="quarters",
            period_keys=quarter_keys,
            period_labels=quarter_labels,
            target_sheet="QUARTERS_COMPARE",
            title_prefix="РАСШИФРОВКА ПО КВАРТАЛАМ",
        )