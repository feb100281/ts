# accounting_analysis/services/reports/account_45_report.py

from __future__ import annotations

import pandas as pd

from accounting_analysis.services.styles.theme import (
    FORMATS,
    ALIGNMENTS,
    FILLS,
    FONTS,
    BORDERS,
    COLORS,
)


from accounting_analysis.services.scripts.account_45_conclusions import build_account_45_conclusions

from accounting_analysis.services.styles.excel_helpers import (
    hide_grid_and_freeze,
    set_column_widths,
    set_row_heights,
    draw_sheet_header,
    draw_section_title,
    draw_table_header,
    style_data_row,
    autosize_by_content,
    apply_negative_highlight,
    apply_zero_warning,
    add_filter,
    add_back_to_summary_link,
    set_tab_color,
    insert_section_row,
    style_total_row,
    draw_conclusion_block,
)


SUMMARY_WIDTHS = {
    "A": 52,
    "B": 30,
    "C": 18,
}

ITEMS_WIDTHS = {
    "A": 40,
    "B": 16,
    "C": 18,
    "D": 18,
    "E": 16,
    "F": 18,
    "G": 18,
    "H": 18,
    "I": 18,
    "J": 16,
    "K": 16,
    "L": 18,
    "M": 18,
    "N": 14,
}


RUSSIAN_HEADERS = {
    "item_name": "Номенклатура",
    "article_candidate": "Артикул",
    "opening_qty": "Остаток на начало, кол-во",
    "opening_amount": "Остаток на начало, сумма",
    "sold_qty": "Продано, кол-во",
    "sold_amount": "Продано, сумма",
    "avg_sale_price": "Средняя цена продажи",
    "ending_qty": "Остаток на конец, кол-во",
    "ending_amount": "Остаток на конец, сумма",
    "is_negative_ending_qty": "Отрицательное кол-во",
    "is_negative_ending_amount": "Отрицательная сумма",
    "qty_exists_amount_missing_at_end": "Есть кол-во, нет суммы",
    "amount_exists_qty_missing_at_end": "Есть сумма, нет кол-ва",
    "excel_rows": "Строки Excel",
    "excel_row": "Строка Excel",
    "name": "Наименование",
    "name_filled": "Заполненное наименование",
    "indicator": "Показатель",
    "indent": "Уровень",
    "opening_debit": "Начальный остаток Дт",
    "opening_credit": "Начальный остаток Кт",
    "turnover_debit": "Оборот Дт",
    "turnover_credit": "Оборот Кт",
    "ending_debit": "Конечный остаток Дт",
    "ending_credit": "Конечный остаток Кт",
    "is_item_name": "Это номенклатура",
    "used_in_items": "Попало в итог",
}


def prettify_columns(df: pd.DataFrame) -> pd.DataFrame:
    renamed = df.copy()
    renamed.columns = [RUSSIAN_HEADERS.get(col, col) for col in renamed.columns]
    return renamed


def _prepare_sheet(writer, sheet_name: str):
    wb = writer.book

    if sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        wb.remove(ws)

    ws = wb.create_sheet(title=sheet_name)
    return ws


def _remove_default_sheet(writer):
    wb = writer.book
    if "Sheet" in wb.sheetnames and len(wb.sheetnames) > 1:
        ws = wb["Sheet"]
        wb.remove(ws)


def _write_summary_sheet(
    ws,
    summary_df: pd.DataFrame,
    items_df: pd.DataFrame,
    meta: dict | None = None,
):
    draw_sheet_header(
        ws,
        title="Анализ ОСВ счета 45",
        subtitle="Сводка по результатам анализа",
        note="Лист содержит ключевые контрольные показатели по файлу.",
        line_to_col=3,
    )

    section_row = 8
    header_row = 9
    data_start_row = 10

    draw_section_title(ws, section_row, 1, 3, "Сводные показатели")
    draw_table_header(ws, header_row, ["Показатель", "Значение", "Листы"], wrap=True)

    note_map = {
        "Полная детализация": ("0", "См. лист 0"),
        "Позиции с отрицательным количеством на конец": ("1", "См. лист 1"),
        "Сумма отрицательных остатков в штуках (abs)": ("1", "См. лист 1"),
        "Позиции, где есть количество, но нет суммы на конец": ("2", "См. лист 2"),
        "Позиции с отрицательной суммой на конец": ("3", "См. лист 3"),
        "Позиции, где есть сумма, но нет количества на конец": ("4", "См. лист 4"),
    }

    int_metrics = {
        "Количество номенклатурных позиций",
        "Позиции с отрицательным количеством на конец",
        "Позиции с отрицательной суммой на конец",
        "Позиции, где есть количество, но нет суммы на конец",
        "Позиции, где есть сумма, но нет количества на конец",
    }

    qty_metrics = {
        "Продано за период, шт",
        "Остаток на начало, всего шт",
        "Остаток на конец, всего шт",
        "Сумма отрицательных остатков в штуках (abs)",
    }

    money_metrics = {
        "Продано за период, сумма",
        "Средняя цена продажи за 1 единицу",
        "Остаток на начало, всего сумма",
        "Остаток на конец, всего сумма",
    }

    groups = [
        (
            "Общая информация",
            [
                "Компания",
                "ОСВ",
                "Контрагент",
                "Полная детализация",
            ],
        ),
        (
            "Контрольные показатели",
            [
                "Количество номенклатурных позиций",
                "Позиции с отрицательным количеством на конец",
                "Сумма отрицательных остатков в штуках (abs)",
                "Позиции с отрицательной суммой на конец",
                "Позиции, где есть количество, но нет суммы на конец",
                "Позиции, где есть сумма, но нет количества на конец",
            ],
        ),
        (
            "Продажи",
            [
                "Продано за период, шт",
                "Продано за период, сумма",
                "Средняя цена продажи за 1 единицу",
            ],
        ),
        (
            "Остатки на начало",
            [
                "Остаток на начало, всего шт",
                "Остаток на начало, всего сумма",
            ],
        ),
        (
            "Остатки на конец",
            [
                "Остаток на конец, всего шт",
                "Остаток на конец, всего сумма",
            ],
        ),
    ]

    summary_map = {
        row["Показатель"]: row["Значение"]
        for _, row in summary_df.iterrows()
    }

    current_row = data_start_row
    spacer_height = 8

    for group_title, metric_names in groups:
        # верхний пустой отступ перед блоком (кроме самого первого)
        if current_row > data_start_row:
            ws.row_dimensions[current_row].height = spacer_height
            for col_idx in range(1, 4):
                c = ws.cell(row=current_row, column=col_idx)
                c.fill = FILLS["none"]
                c.border = BORDERS["none"]
                c.value = None
            current_row += 1

        # строка заголовка блока
        insert_section_row(ws, current_row, group_title)
        current_row += 1

        # строки показателей внутри блока
        for metric_name in metric_names:
            if metric_name not in summary_map:
                continue

            metric_value = summary_map[metric_name]
            target_sheet = None
            note_text = ""

            if metric_name in note_map:
                target_sheet, note_text = note_map[metric_name]

            values = [metric_name, metric_value, note_text]
            style_data_row(ws, current_row, values, start_col=1)

            # нормальная высота строки данных
            ws.row_dimensions[current_row].height = 20

            value_cell = ws.cell(row=current_row, column=2)
            note_cell = ws.cell(row=current_row, column=3)

            if isinstance(metric_value, (int, float)):
                value_cell.alignment = ALIGNMENTS["right"]

                if metric_name in int_metrics:
                    value_cell.number_format = FORMATS["int"]
                elif metric_name in qty_metrics:
                    value_cell.number_format = FORMATS["qty"]
                elif metric_name in money_metrics:
                    value_cell.number_format = FORMATS["money"]
                else:
                    value_cell.number_format = FORMATS["int"]
            else:
                value_cell.alignment = ALIGNMENTS["left"]

            note_cell.alignment = ALIGNMENTS["left"]

            if target_sheet and note_text:
                note_cell.value = note_text
                note_cell.hyperlink = f"#{target_sheet}!A1"
                note_cell.font = FONTS["bold"]
                note_cell.fill = FILLS["back"]
                note_cell.border = BORDERS["thin"]

            if group_title == "Общая информация":
                for col_idx in range(1, 4):
                    c = ws.cell(row=current_row, column=col_idx)
                    c.fill = FILLS["summary"]
                    c.border = BORDERS["thin"]
                value_cell.font = FONTS["bold"]

            if group_title in {"Продажи", "Остатки на начало", "Остатки на конец"}:
                for col_idx in range(1, 4):
                    c = ws.cell(row=current_row, column=col_idx)
                    c.fill = FILLS["summary"]
                    c.border = BORDERS["thin"]

            if metric_name in {"Продано за период, сумма", "Остаток на конец, всего сумма"}:
                for col_idx in range(1, 4):
                    c = ws.cell(row=current_row, column=col_idx)
                    c.fill = FILLS["back"]
                    c.border = BORDERS["thin"]

            is_error_row = (
                metric_name in note_map
                and isinstance(metric_value, (int, float))
                and metric_value > 0
                and group_title == "Контрольные показатели"
            )

            if is_error_row:
                for col_idx in range(1, 4):
                    c = ws.cell(row=current_row, column=col_idx)
                    c.fill = FILLS["danger"]
                    c.border = BORDERS["thin"]
                    if col_idx != 3:
                        c.font = FONTS["danger"]

                if target_sheet and note_text:
                    note_cell.font = FONTS["danger"]
                    note_cell.fill = FILLS["danger"]
                    note_cell.border = BORDERS["thin"]

            current_row += 1

        # нижний пустой отступ после блока
        ws.row_dimensions[current_row].height = spacer_height
        for col_idx in range(1, 4):
            c = ws.cell(row=current_row, column=col_idx)
            c.fill = FILLS["none"]
            c.border = BORDERS["none"]
            c.value = None
        current_row += 1
        
        
    
    conclusions = build_account_45_conclusions(
                items_df=items_df,
                summary_df=summary_df,
                meta=meta,
            )

    if conclusions:
            ws.row_dimensions[current_row].height = 10
            current_row += 1

            current_row = draw_conclusion_block(
                ws,
                start_row=current_row,
                col_start=1,
                col_end=3,
                title="Заключение",
                conclusions=conclusions,
            )


    set_column_widths(ws, SUMMARY_WIDTHS)
    set_row_heights(ws, {2: 24, 3: 18, 4: 22, 8: 26, 9: 26})
    hide_grid_and_freeze(ws, "A10")


def _write_table_sheet(
    ws,
    df: pd.DataFrame,
    title: str,
    subtitle: str,
    note: str,
    money_cols: set[str] | None = None,
    qty_cols: set[str] | None = None,
    int_cols: set[str] | None = None,
    highlight_negative_cols: set[str] | None = None,
    paired_warning_cols: list[tuple[str, str]] | None = None,
):
    money_cols = money_cols or set()
    qty_cols = qty_cols or set()
    int_cols = int_cols or set()
    highlight_negative_cols = highlight_negative_cols or set()
    paired_warning_cols = paired_warning_cols or []

    pretty_df = prettify_columns(df)

    draw_sheet_header(
        ws,
        title=title,
        subtitle=subtitle,
        note=note,
        line_to_col=len(pretty_df.columns),
    )

    add_back_to_summary_link(ws, col=1, row=1)

    section_row = 8
    header_row = 9
    data_start_row = 10

    draw_section_title(ws, section_row, 1, len(pretty_df.columns), "Детализация")
    draw_table_header(ws, header_row, list(pretty_df.columns), wrap=True)

    original_col_index = {col: idx + 1 for idx, col in enumerate(df.columns)}

    current_row = data_start_row
    for _, row in df.iterrows():
        values = row.tolist()
        style_data_row(ws, current_row, values)

        for col_name, idx in original_col_index.items():
            cell = ws.cell(row=current_row, column=idx)

            if col_name in money_cols:
                cell.number_format = FORMATS["money"]
            elif col_name in qty_cols:
                cell.number_format = FORMATS["qty"]
            elif col_name in int_cols:
                cell.number_format = FORMATS["int"]

        current_row += 1

    end_row = current_row - 1
    
    # === ИТОГОВАЯ СТРОКА ===
    total_row = current_row

    totals = []

    for col_name in df.columns:
        if col_name in money_cols or col_name in qty_cols:
            total_value = df[col_name].sum()
            totals.append(total_value)
        else:
            totals.append("")

    # первый столбец — подпись
    if totals:
        totals[0] = "ИТОГО"

    style_total_row(ws, total_row, totals)

    # форматирование чисел
    for col_name, idx in original_col_index.items():
        cell = ws.cell(row=total_row, column=idx)

        if col_name in money_cols:
            cell.number_format = FORMATS["money"]
        elif col_name in qty_cols:
            cell.number_format = FORMATS["qty"]
        elif col_name in int_cols:
            cell.number_format = FORMATS["int"]

    current_row += 1
    

    for col_name in highlight_negative_cols:
        if col_name in original_col_index:
            apply_negative_highlight(ws, data_start_row, end_row, original_col_index[col_name])

    for qty_col, amount_col in paired_warning_cols:
        if qty_col in original_col_index and amount_col in original_col_index:
            apply_zero_warning(
                ws,
                data_start_row,
                end_row,
                qty_col_idx=original_col_index[qty_col],
                amount_col_idx=original_col_index[amount_col],
            )

    add_filter(ws, header_row, len(pretty_df.columns))
    autosize_by_content(ws, min_width=10, max_width=45)
    hide_grid_and_freeze(ws, "C10")
    set_row_heights(ws, {2: 24, 3: 18, 4: 24, 9: 30})

    if ws.title == "All_Items":
        for col, width in ITEMS_WIDTHS.items():
            ws.column_dimensions[col].width = width


def build_account_45_report(
    writer,
    summary_df: pd.DataFrame,
    items_df: pd.DataFrame,
    meta: dict | None,
    items_output: pd.DataFrame,
    negative_output: pd.DataFrame,
    qty_no_amount_output: pd.DataFrame,
    negative_amount_output: pd.DataFrame,
    amount_no_qty_output: pd.DataFrame,
):
    ws_summary = _prepare_sheet(writer, "Summary")
    ws_all_items = _prepare_sheet(writer, "0")
    ws_negative_qty = _prepare_sheet(writer, "1")
    ws_qty_no_amount = _prepare_sheet(writer, "2")
    ws_negative_amount = _prepare_sheet(writer, "3")
    ws_amount_no_qty = _prepare_sheet(writer, "4")

    set_tab_color(ws_summary, COLORS["dark_green"])
    set_tab_color(ws_all_items, COLORS["tab_light_green"])
    set_tab_color(ws_negative_qty, COLORS["tab_light_green"])
    set_tab_color(ws_qty_no_amount, COLORS["tab_light_green"])
    set_tab_color(ws_negative_amount, COLORS["tab_light_green"])
    set_tab_color(ws_amount_no_qty, COLORS["tab_light_green"])

    _remove_default_sheet(writer)

    _write_summary_sheet(
        ws_summary,
        summary_df=summary_df,
        items_df=items_df,
        meta=meta,
    )

    _write_table_sheet(
        ws_all_items,
        items_output,
        title="Анализ ОСВ счета 45 — вся номенклатура",
        subtitle="Все выявленные номенклатурные позиции",
        note="Основной аналитический лист по остаткам, продажам и контрольным признакам.",
        money_cols={"opening_amount", "sold_amount", "avg_sale_price", "ending_amount"},
        qty_cols={"opening_qty", "sold_qty", "ending_qty"},
        highlight_negative_cols={"ending_qty", "ending_amount"},
        paired_warning_cols=[("ending_qty", "ending_amount")],
    )

    _write_table_sheet(
        ws_negative_qty,
        negative_output,
        title="Отрицательные остатки по количеству",
        subtitle="Позиции с отрицательным количеством на конец периода",
        note="Требуют отдельной проверки учетной логики и документов движения.",
        money_cols={"ending_amount"},
        qty_cols={"ending_qty"},
        highlight_negative_cols={"ending_qty"},
    )

    _write_table_sheet(
        ws_qty_no_amount,
        qty_no_amount_output,
        title="Есть количество, но нет суммы",
        subtitle="Контроль расхождений по остаткам",
        note="Позиции, где на конец есть количество, но сумма равна нулю.",
        money_cols={"ending_amount"},
        qty_cols={"ending_qty"},
        paired_warning_cols=[("ending_qty", "ending_amount")],
    )

    _write_table_sheet(
        ws_negative_amount,
        negative_amount_output,
        title="Отрицательные остатки по сумме",
        subtitle="Позиции с отрицательной суммой на конец периода",
        note="Потенциальные аномалии стоимостного учета.",
        money_cols={"ending_amount"},
        qty_cols={"ending_qty"},
        highlight_negative_cols={"ending_amount"},
    )

    _write_table_sheet(
        ws_amount_no_qty,
        amount_no_qty_output,
        title="Есть сумма, но нет количества",
        subtitle="Контроль расхождений по остаткам",
        note="Позиции, где есть сумма на конец, но количество равно нулю.",
        money_cols={"ending_amount"},
        qty_cols={"ending_qty"},
        paired_warning_cols=[("ending_qty", "ending_amount")],
    )
