# gear/app/daily_sales/stocks/excel.py
from io import BytesIO
from datetime import datetime
import re

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill
from openpyxl.utils import get_column_letter

from .styles import (
    COLORS,
    FONT_NAME,
    FONT_NAME_BOLD,
    THIN_BORDER,
    HEADER_FONT,
    BODY_FONT,
    TITLE_FONT,
    SUBTITLE_FONT,
    SMALL_MUTED_FONT,
    BUTTON_FONT,
    CENTER,
    LEFT,
)


TOC_SHEET_NAME = "Оглавление"

SHEET_TAB_COLORS = [
    "2F6656",
    "4F7F70",
    "7A9E92",
    "A33A3A",
    "8C6A3F",
    "5B6F8C",
    "6F5B8C",
]


def _safe_sheet_name(name: str) -> str:
    name = str(name or "Без названия").strip()
    name = re.sub(r"[\\/*?:\[\]]", " ", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name[:31] or "Без названия"


def _fmt_date(report_date) -> str:
    return pd.to_datetime(report_date).strftime("%d.%m.%Y")


def _prepare_stocks_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    if "Дата" in df.columns:
        df = df.drop(columns=["Дата"])

    money_cols = [
        "Бух. с/с за ед.",
        "Упр. с/с за ед.",
        "Бух. с/с всего",
        "Упр. с/с всего",
    ]

    for col in money_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0) / 100

    if {"Бух. с/с за ед.", "Упр. с/с за ед."}.issubset(df.columns):
        df["Δ с/с за ед."] = df["Упр. с/с за ед."] - df["Бух. с/с за ед."]
        df["Δ с/с за ед., %"] = df.apply(
            lambda x: (
                x["Δ с/с за ед."] / x["Бух. с/с за ед."]
                if x["Бух. с/с за ед."] else 0
            ),
            axis=1,
        )

    for col in ["USK", "NM ID", "Chrt ID"]:
        if col in df.columns:
            df[col] = df[col].astype("string").fillna("")

    preferred_order = [
        "USK",
        "Бренд",
        "Категория",
        "Пол",
        "Артикул",
        "Наименование",
        "Размер",
        "Итого количество",
        "Остаток на складе",
        "В пути от клиента",
        "В пути к клиенту",
        "Бух. с/с за ед.",
        "Упр. с/с за ед.",
        "Δ с/с за ед.",
        "Δ с/с за ед., %",
        "Бух. с/с всего",
        "Упр. с/с всего",
        "NM ID",
        "Chrt ID",
    ]

    existing_order = [col for col in preferred_order if col in df.columns]
    other_cols = [col for col in df.columns if col not in existing_order]

    df = df[existing_order + other_cols]

    sort_cols = [
        col for col in ["Бренд", "Категория", "Наименование", "Размер"]
        if col in df.columns
    ]

    if sort_cols:
        df = df.sort_values(sort_cols, na_position="last")

    return df


def _autosize_columns(ws, min_width=10, max_width=45):
    for col_idx in range(1, ws.max_column + 1):
        letter = get_column_letter(col_idx)
        max_len = 0

        for row_idx in range(1, ws.max_row + 1):
            value = ws.cell(row=row_idx, column=col_idx).value
            if value is not None:
                max_len = max(max_len, len(str(value)))

        ws.column_dimensions[letter].width = max(
            min_width,
            min(max_len + 2, max_width),
        )


def _add_back_button(ws, last_col):
    if ws.title == TOC_SHEET_NAME:
        return

    btn_last_col = min(3, last_col)

    ws.merge_cells(
        start_row=1,
        start_column=1,
        end_row=1,
        end_column=btn_last_col,
    )

    cell = ws.cell(row=1, column=1, value="← ОГЛАВЛЕНИЕ")
    cell.hyperlink = f"#'{TOC_SHEET_NAME}'!A1"
    cell.font = BUTTON_FONT
    cell.fill = PatternFill("solid", fgColor=COLORS["success"])
    cell.alignment = Alignment(horizontal="center", vertical="center")
    cell.border = THIN_BORDER

    ws.row_dimensions[1].height = 24


def _style_title(ws, title, subtitle, report_date, last_col):
    ws.sheet_view.showGridLines = False

    _add_back_button(ws, last_col)

    ws.merge_cells(start_row=3, start_column=1, end_row=3, end_column=last_col)
    cell = ws.cell(row=3, column=1, value=title)
    cell.font = TITLE_FONT
    cell.alignment = LEFT
    ws.row_dimensions[3].height = 30

    ws.merge_cells(start_row=4, start_column=1, end_row=4, end_column=last_col)
    cell = ws.cell(
        row=4,
        column=1,
        value=f"{subtitle} · дата остатков: {_fmt_date(report_date)}",
    )
    cell.font = SUBTITLE_FONT
    cell.alignment = LEFT
    ws.row_dimensions[4].height = 22

    ws.merge_cells(start_row=5, start_column=1, end_row=5, end_column=last_col)
    cell = ws.cell(
        row=5,
        column=1,
        value=f"Сформировано: {datetime.now().strftime('%d.%m.%Y в %H:%M')}",
    )
    cell.font = SMALL_MUTED_FONT
    cell.alignment = LEFT
    ws.row_dimensions[5].height = 20


def _sum_col(df, col_name):
    if col_name not in df.columns:
        return 0
    return pd.to_numeric(df[col_name], errors="coerce").fillna(0).sum()


def _add_sheet_summary_cards(ws, df, start_row, last_col):
    total_qty = _sum_col(df, "Итого количество")
    total_buh = _sum_col(df, "Бух. с/с всего")
    total_man = _sum_col(df, "Упр. с/с всего")
    delta_total = total_man - total_buh

    cards = [
        ("Строк", len(df), "SKU"),
        ("Количество", total_qty, "шт"),
        ("Бух. стоимость", total_buh, "₽"),
        ("Упр. стоимость", total_man, "₽"),
        ("Δ стоимости", delta_total, "Упр. − Бух."),
    ]

    max_cards = min(len(cards), max(1, last_col // 2))

    row = start_row
    col = 1

    for idx, (title, value, subtitle) in enumerate(cards[:max_cards]):
        c1 = col + idx * 2
        c2 = c1 + 1

        ws.merge_cells(start_row=row, start_column=c1, end_row=row, end_column=c2)
        title_cell = ws.cell(row=row, column=c1, value=title)
        title_cell.font = Font(name=FONT_NAME_BOLD, size=9, bold=True, color=COLORS["muted"])
        title_cell.fill = PatternFill("solid", fgColor=COLORS["light_green"])
        title_cell.alignment = CENTER

        ws.merge_cells(start_row=row + 1, start_column=c1, end_row=row + 1, end_column=c2)
        value_cell = ws.cell(row=row + 1, column=c1, value=value)
        value_cell.font = Font(name=FONT_NAME_BOLD, size=13, bold=True, color=COLORS["dark_green"])
        value_cell.fill = PatternFill("solid", fgColor=COLORS["light_gray"])
        value_cell.alignment = CENTER
        value_cell.number_format = '#,##0.00 ₽' if "стоимость" in title else "#,##0"

        if title == "Δ стоимости":
            value_cell.number_format = '#,##0.00 ₽'
            value_cell.fill = PatternFill(
                "solid",
                fgColor=COLORS["warning"] if value > 0 else COLORS["success"],
            )
            value_cell.font = Font(
                name=FONT_NAME_BOLD,
                size=13,
                bold=True,
                color=COLORS["discount"] if value > 0 else COLORS["dark_green"],
            )

        ws.merge_cells(start_row=row + 2, start_column=c1, end_row=row + 2, end_column=c2)
        sub_cell = ws.cell(row=row + 2, column=c1, value=subtitle)
        sub_cell.font = Font(name=FONT_NAME, size=8, color=COLORS["muted"])
        sub_cell.fill = PatternFill("solid", fgColor=COLORS["light_gray"])
        sub_cell.alignment = CENTER

        for rr in range(row, row + 3):
            for cc in range(c1, c2 + 1):
                ws.cell(rr, cc).border = THIN_BORDER

    return start_row + 5


def _style_body_cell(cell, col_name, row_idx):
    cell.font = BODY_FONT
    cell.alignment = LEFT
    cell.border = THIN_BORDER

    if col_name in ["USK", "NM ID", "Chrt ID"]:
        cell.number_format = "@"
        cell.alignment = Alignment(horizontal="left", vertical="center")

    elif col_name in [
        "Итого количество",
        "Остаток на складе",
        "В пути от клиента",
        "В пути к клиенту",
    ]:
        cell.fill = PatternFill("solid", fgColor=COLORS["qty"])
        cell.number_format = "#,##0"
        cell.alignment = Alignment(horizontal="right", vertical="center")

    elif col_name in [
        "Бух. с/с за ед.",
        "Упр. с/с за ед.",
        "Бух. с/с всего",
        "Упр. с/с всего",
        "Δ стоимости",
    ]:
        cell.fill = PatternFill("solid", fgColor=COLORS["money"])
        cell.number_format = '#,##0.00 ₽'
        cell.alignment = Alignment(horizontal="right", vertical="center")

        if col_name == "Δ стоимости":
            value = cell.value or 0
            cell.fill = PatternFill(
                "solid",
                fgColor=COLORS["warning"] if value > 0 else COLORS["success"],
            )
            cell.font = Font(
                name=FONT_NAME_BOLD,
                size=10,
                bold=True,
                color=COLORS["discount"] if value > 0 else COLORS["dark_green"],
            )

    elif col_name == "Δ с/с за ед.":
        value = cell.value or 0

        cell.fill = PatternFill(
            "solid",
            fgColor=COLORS["warning"] if value > 0 else COLORS["success"],
        )
        cell.font = Font(
            name=FONT_NAME_BOLD,
            size=10,
            bold=True,
            color=COLORS["discount"] if value > 0 else COLORS["dark_green"],
        )
        cell.number_format = '#,##0.00 ₽'
        cell.alignment = Alignment(horizontal="right", vertical="center")

    elif col_name == "Δ с/с за ед., %":
        value = cell.value or 0

        cell.fill = PatternFill(
            "solid",
            fgColor=COLORS["warning"] if value > 0 else COLORS["success"],
        )
        cell.font = Font(
            name=FONT_NAME_BOLD,
            size=10,
            bold=True,
            color=COLORS["discount"] if value > 0 else COLORS["dark_green"],
        )
        cell.number_format = '0.00%'
        cell.alignment = Alignment(horizontal="right", vertical="center")

    elif row_idx % 2 == 0:
        cell.fill = PatternFill("solid", fgColor=COLORS["light_gray"])


def _write_dataframe_sheet(
    wb,
    sheet_name,
    df,
    report_date,
    title,
    subtitle,
):
    ws = wb.create_sheet(_safe_sheet_name(sheet_name))

    df = df.copy()
    last_col = max(len(df.columns), 1)

    _style_title(ws, title, subtitle, report_date, last_col)

    header_row = _add_sheet_summary_cards(
        ws=ws,
        df=df,
        start_row=7,
        last_col=last_col,
    )

    for col_idx, col_name in enumerate(df.columns, start=1):
        cell = ws.cell(row=header_row, column=col_idx, value=col_name)
        cell.font = HEADER_FONT
        cell.fill = PatternFill("solid", fgColor=COLORS["dark_green"])
        cell.alignment = CENTER
        cell.border = THIN_BORDER

    for row_idx, row in enumerate(df.itertuples(index=False), start=header_row + 1):
        ws.row_dimensions[row_idx].height = 20

        for col_idx, value in enumerate(row, start=1):
            col_name = df.columns[col_idx - 1]
            cell = ws.cell(row=row_idx, column=col_idx, value=value)
            _style_body_cell(cell, col_name, row_idx)

    last_row = header_row + len(df)

    # замораживаем:
    # строки до таблицы включительно
    # первые 3 колонки слева
    freeze_col = 4
    ws.freeze_panes = f"{get_column_letter(freeze_col)}{header_row + 1}"
    
    if len(df) > 0:
        ws.auto_filter.ref = f"A{header_row}:{get_column_letter(last_col)}{last_row}"

    detail_cols = [
        "Остаток на складе",
        "В пути от клиента",
        "В пути к клиенту",
    ]

    detail_indexes = [
        df.columns.get_loc(col) + 1
        for col in detail_cols
        if col in df.columns
    ]

    if detail_indexes:
        first = min(detail_indexes)
        last = max(detail_indexes)

        for col_idx in range(first, last + 1):
            letter = get_column_letter(col_idx)
            ws.column_dimensions[letter].outlineLevel = 1
            ws.column_dimensions[letter].hidden = True

        ws.sheet_properties.outlinePr.summaryRight = False

    _autosize_columns(ws)

    for col_name, width in {
        "USK": 16,
        "Бренд": 20,
        "Категория": 22,
        "Пол": 12,
        "Артикул": 18,
        "Наименование": 42,
        "Размер": 14,
        "Итого количество": 15,
        "Остаток на складе": 15,
        "В пути от клиента": 15,
        "В пути к клиенту": 15,
        "Бух. с/с за ед.": 16,
        "Упр. с/с за ед.": 16,
        "Δ с/с за ед.": 16,
        "Δ с/с за ед., %": 16,
        "Бух. с/с всего": 17,
        "Упр. с/с всего": 17,
        "Δ стоимости": 17,
        "NM ID": 16,
        "Chrt ID": 16,
    }.items():
        if col_name in df.columns:
            letter = get_column_letter(df.columns.get_loc(col_name) + 1)
            ws.column_dimensions[letter].width = width

    return ws.title


def _build_summary_sheet(wb, df, report_date):
    ws = wb.create_sheet("Сводка")
    ws.sheet_view.showGridLines = False

    last_col = 9
    _add_back_button(ws, last_col)

    total_qty = _sum_col(df, "Итого количество")
    on_hand = _sum_col(df, "Остаток на складе")
    in_way_client = _sum_col(df, "В пути к клиенту")
    in_way_from = _sum_col(df, "В пути от клиента")
    total_buh = _sum_col(df, "Бух. с/с всего")
    total_man = _sum_col(df, "Упр. с/с всего")
    delta_total = total_man - total_buh

    ws.merge_cells("A3:I3")
    cell = ws["A3"]
    cell.value = "ОТЧЕТ ПО ОСТАТКАМ ТОВАРОВ"
    cell.font = Font(name=FONT_NAME_BOLD, size=18, bold=True, color=COLORS["dark_green"])
    cell.alignment = LEFT

    ws.merge_cells("A4:I4")
    cell = ws["A4"]
    cell.value = f"Дата остатков: {_fmt_date(report_date)}"
    cell.font = Font(name=FONT_NAME, size=11, bold=True, color=COLORS["muted"])

    ws.merge_cells("A5:I5")
    cell = ws["A5"]
    cell.value = f"Сформировано: {datetime.now().strftime('%d.%m.%Y в %H:%M')}"
    cell.font = SMALL_MUTED_FONT

    cards = [
        ("SKU / строк", len(df), "позиций в выгрузке"),
        ("Итого количество", total_qty, "шт"),
        ("На складе", on_hand, "шт"),
        ("В пути к клиенту", in_way_client, "шт"),
        ("В пути от клиента", in_way_from, "шт"),
        ("Бух. стоимость", total_buh, "₽"),
        ("Упр. стоимость", total_man, "₽"),
        ("Δ стоимости", delta_total, "Упр. − Бух."),
    ]

    row = 7
    col = 1

    for idx, (title, value, subtitle) in enumerate(cards):
        c1 = col + (idx % 4) * 2
        r1 = row + (idx // 4) * 4

        ws.merge_cells(start_row=r1, start_column=c1, end_row=r1, end_column=c1 + 1)
        title_cell = ws.cell(r1, c1, title)
        title_cell.font = Font(name=FONT_NAME_BOLD, size=9, bold=True, color=COLORS["muted"])
        title_cell.fill = PatternFill("solid", fgColor=COLORS["light_green"])
        title_cell.alignment = CENTER

        ws.merge_cells(start_row=r1 + 1, start_column=c1, end_row=r1 + 1, end_column=c1 + 1)
        value_cell = ws.cell(r1 + 1, c1, value)
        value_cell.font = Font(name=FONT_NAME_BOLD, size=14, bold=True, color=COLORS["dark_green"])
        value_cell.fill = PatternFill("solid", fgColor=COLORS["light_gray"])
        value_cell.alignment = CENTER
        value_cell.number_format = '#,##0.00 ₽' if "стоимость" in title else "#,##0"

        if title == "Δ стоимости":
            value_cell.number_format = '#,##0.00 ₽'
            value_cell.fill = PatternFill(
                "solid",
                fgColor=COLORS["warning"] if value > 0 else COLORS["success"],
            )
            value_cell.font = Font(
                name=FONT_NAME_BOLD,
                size=14,
                bold=True,
                color=COLORS["discount"] if value > 0 else COLORS["dark_green"],
            )

        ws.merge_cells(start_row=r1 + 2, start_column=c1, end_row=r1 + 2, end_column=c1 + 1)
        sub_cell = ws.cell(r1 + 2, c1, subtitle)
        sub_cell.font = Font(name=FONT_NAME, size=8, color=COLORS["muted"])
        sub_cell.fill = PatternFill("solid", fgColor=COLORS["light_gray"])
        sub_cell.alignment = CENTER

        for rr in range(r1, r1 + 3):
            for cc in range(c1, c1 + 2):
                ws.cell(rr, cc).border = THIN_BORDER

    ws.column_dimensions["A"].width = 18
    for col_letter in ["B", "C", "D", "E", "F", "G", "H", "I"]:
        ws.column_dimensions[col_letter].width = 16

    return ws.title


def _build_toc_sheet(wb, sheets_info, report_date):
    ws = wb.create_sheet(TOC_SHEET_NAME, 0)
    ws.sheet_view.showGridLines = False

    ws.merge_cells("B2:D2")
    cell = ws["B2"]
    cell.value = "ОГЛАВЛЕНИЕ ОТЧЕТА ПО ОСТАТКАМ"
    cell.font = Font(name=FONT_NAME_BOLD, size=18, bold=True, color=COLORS["dark_green"])

    ws.merge_cells("B3:D3")
    cell = ws["B3"]
    cell.value = f"Дата остатков: {_fmt_date(report_date)}"
    cell.font = Font(name=FONT_NAME, size=11, bold=True, color=COLORS["muted"])

    ws.merge_cells("B4:D4")
    cell = ws["B4"]
    cell.value = "Для перехода к листу нажмите на название раздела"
    cell.font = SMALL_MUTED_FONT

    headers = ["№", "Лист", "Описание"]
    start_row = 7

    for col_idx, header in enumerate(headers, start=2):
        cell = ws.cell(start_row, col_idx, header)
        cell.font = HEADER_FONT
        cell.fill = PatternFill("solid", fgColor=COLORS["dark_green"])
        cell.alignment = CENTER
        cell.border = THIN_BORDER

    row = start_row + 1

    for idx, item in enumerate(sheets_info, start=1):
        sheet_name = item["name"]

        values = [
            f"{idx:02d}",
            sheet_name,
            item.get("description", ""),
        ]

        for col_idx, value in enumerate(values, start=2):
            cell = ws.cell(row, col_idx, value)
            cell.font = BODY_FONT
            cell.border = THIN_BORDER
            cell.alignment = LEFT

            if col_idx == 3:
                cell.font = Font(name=FONT_NAME_BOLD, size=10, bold=True, color=COLORS["link"])
                cell.hyperlink = f"#'{sheet_name}'!A1"

            if idx % 2 == 0:
                cell.fill = PatternFill("solid", fgColor=COLORS["light_gray"])

        ws.row_dimensions[row].height = 26
        row += 1

    ws.column_dimensions["A"].width = 3
    ws.column_dimensions["B"].width = 8
    ws.column_dimensions["C"].width = 34
    ws.column_dimensions["D"].width = 70


def _build_category_summary(wb, df, report_date):
    group_cols = [
        col for col in ["Категория", "Бренд"]
        if col in df.columns
    ]

    if not group_cols:
        return None

    value_cols = [
        col
        for col in [
            "Итого количество",
            "Остаток на складе",
            "В пути от клиента",
            "В пути к клиенту",
            "Бух. с/с всего",
            "Упр. с/с всего",
        ]
        if col in df.columns
    ]

    summary = (
        df.groupby(group_cols, dropna=False)[value_cols]
        .sum()
        .reset_index()
        .sort_values(group_cols)
    )

    if {"Бух. с/с всего", "Упр. с/с всего"}.issubset(summary.columns):
        summary["Δ стоимости"] = summary["Упр. с/с всего"] - summary["Бух. с/с всего"]

    return _write_dataframe_sheet(
        wb=wb,
        sheet_name="По категориям",
        df=summary,
        report_date=report_date,
        title="Сводка остатков по категориям",
        subtitle="Разбивка по категориям и брендам",
    )


def _apply_sheet_tab_colors(wb):
    for idx, ws in enumerate(wb.worksheets):
        ws.sheet_properties.tabColor = SHEET_TAB_COLORS[idx % len(SHEET_TAB_COLORS)]


def make_stocks_excel(df: pd.DataFrame, report_date=None) -> bytes:
    report_date = report_date or datetime.today().date()

    df = _prepare_stocks_df(df)

    wb = Workbook()
    default_ws = wb.active
    wb.remove(default_ws)

    sheets_info = []

    summary_name = _build_summary_sheet(wb, df, report_date)
    sheets_info.append(
        {
            "name": summary_name,
            "description": "Ключевые показатели по остаткам, стоимости и дельте",
        }
    )

    all_name = _write_dataframe_sheet(
        wb=wb,
        sheet_name="Все товары",
        df=df,
        report_date=report_date,
        title="Детальные остатки товаров",
        subtitle="Все бренды, категории, размеры и себестоимость",
    )
    sheets_info.append(
        {
            "name": all_name,
            "description": "Полная детализация по всем товарам",
        }
    )

    category_name = _build_category_summary(wb, df, report_date)
    if category_name:
        sheets_info.append(
            {
                "name": category_name,
                "description": "Сводка по категориям и брендам",
            }
        )

    if "Бренд" in df.columns:
        brands = (
            df["Бренд"]
            .fillna("Бренд не указан")
            .astype(str)
            .sort_values()
            .unique()
            .tolist()
        )

        for brand in brands:
            brand_df = df[df["Бренд"].fillna("Бренд не указан").astype(str) == brand]

            sheet_name = _write_dataframe_sheet(
                wb=wb,
                sheet_name=f"Бренд_{brand}",
                df=brand_df,
                report_date=report_date,
                title=f"Остатки товаров — {brand}",
                subtitle="Детализация по категориям, товарам, размерам и себестоимости",
            )

            sheets_info.append(
                {
                    "name": sheet_name,
                    "description": f"Остатки по бренду {brand}",
                }
            )

    _build_toc_sheet(wb, sheets_info, report_date)
    _apply_sheet_tab_colors(wb)

    output = BytesIO()
    wb.save(output)
    output.seek(0)

    return output.read()