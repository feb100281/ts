# gear/app/daily_sales/stocks/dashboard_stock/warehouse_excel.py
"""Excel физической/логистической детализации одного склада."""

import io
from datetime import datetime

import pandas as pd


SHEET_NAME = "Остатки склада"

FONT_NAME = "Helvetica Light"
FONT_SIZE = 10

HEADER_BG = "#E8EFEC"
HEADER_FONT = "#203832"

ROW_BG = "#FFFFFF"
ROW_ALT_BG = "#F7F9F8"

BORDER_COLOR = "#D9DEDC"


def build_warehouse_stock_excel(
    df: pd.DataFrame,
    warehouse_name: str,
    report_date=None,
):
    if df is None or df.empty:
        raise ValueError(
            "Нет данных склада для выгрузки."
        )

    work = df.copy()

    # ================================================================
    # Колонки
    # ================================================================
    columns = [
        "Бренд",
        "Категория",
        "Пол",
        "Артикул",
        "Наименование",
        "Размер",
        "Остаток",
        "В пути от клиента",
        "В пути к клиенту",
        "Итого",
        "Продажи 7 дней",
        "Оборачиваемость",
        "NM ID",
        "Chrt ID",
    ]

    work = work[
        [
            col
            for col in columns
            if col in work.columns
        ]
    ].copy()

    # ================================================================
    # Числовые колонки
    # ================================================================
    integer_cols = {
        "Остаток",
        "В пути от клиента",
        "В пути к клиенту",
        "Итого",
        "Продажи 7 дней",
        "NM ID",
        "Chrt ID",
    }

    decimal_cols = {
        "Оборачиваемость",
    }

    numeric_cols = (
        integer_cols
        | decimal_cols
    )

    for col in numeric_cols:
        if col in work.columns:
            work[col] = pd.to_numeric(
                work[col],
                errors="coerce",
            )

    # ================================================================
    # Excel
    # ================================================================
    output = io.BytesIO()

    with pd.ExcelWriter(
        output,
        engine="xlsxwriter",
    ) as writer:

        workbook = writer.book

        worksheet = workbook.add_worksheet(
            SHEET_NAME
        )

        writer.sheets[SHEET_NAME] = worksheet

        # ------------------------------------------------------------
        # Общие настройки листа
        # ------------------------------------------------------------
        worksheet.hide_gridlines(2)

        # Закрепляем:
        # 1 строку — шапку
        # 1 колонку — Наимеование
        worksheet.freeze_panes(
            1,
            5,
        )

        worksheet.set_zoom(90)

        worksheet.set_row(
            0,
            28,
        )

        worksheet.autofilter(
            0,
            0,
            len(work),
            len(work.columns) - 1,
        )

        # ============================================================
        # Форматы
        # ============================================================

        # ------------------------------------------------------------
        # Шапка
        # ------------------------------------------------------------
        header_fmt = workbook.add_format(
            {
                "font_name": FONT_NAME,
                "font_size": FONT_SIZE,
                "bold": False,

                "bg_color": HEADER_BG,
                "font_color": HEADER_FONT,

                "border": 1,
                "border_color": BORDER_COLOR,

                "align": "center",
                "valign": "vcenter",

                "text_wrap": True,
            }
        )

        # ------------------------------------------------------------
        # Текст
        # ------------------------------------------------------------
        text_fmt = workbook.add_format(
            {
                "font_name": FONT_NAME,
                "font_size": FONT_SIZE,

                "bg_color": ROW_BG,

                "border": 1,
                "border_color": BORDER_COLOR,

                "align": "left",
                "valign": "vcenter",
            }
        )

        text_alt_fmt = workbook.add_format(
            {
                "font_name": FONT_NAME,
                "font_size": FONT_SIZE,

                "bg_color": ROW_ALT_BG,

                "border": 1,
                "border_color": BORDER_COLOR,

                "align": "left",
                "valign": "vcenter",
            }
        )

        # ------------------------------------------------------------
        # Целые числа
        # ------------------------------------------------------------
        integer_fmt = workbook.add_format(
            {
                "font_name": FONT_NAME,
                "font_size": FONT_SIZE,

                "bg_color": ROW_BG,

                "border": 1,
                "border_color": BORDER_COLOR,

                "align": "right",
                "valign": "vcenter",

                "num_format": "#,##0",
            }
        )

        integer_alt_fmt = workbook.add_format(
            {
                "font_name": FONT_NAME,
                "font_size": FONT_SIZE,

                "bg_color": ROW_ALT_BG,

                "border": 1,
                "border_color": BORDER_COLOR,

                "align": "right",
                "valign": "vcenter",

                "num_format": "#,##0",
            }
        )

        # ------------------------------------------------------------
        # Десятичные числа
        # ------------------------------------------------------------
        decimal_fmt = workbook.add_format(
            {
                "font_name": FONT_NAME,
                "font_size": FONT_SIZE,

                "bg_color": ROW_BG,

                "border": 1,
                "border_color": BORDER_COLOR,

                "align": "right",
                "valign": "vcenter",

                "num_format": "#,##0.0",
            }
        )

        decimal_alt_fmt = workbook.add_format(
            {
                "font_name": FONT_NAME,
                "font_size": FONT_SIZE,

                "bg_color": ROW_ALT_BG,

                "border": 1,
                "border_color": BORDER_COLOR,

                "align": "right",
                "valign": "vcenter",

                "num_format": "#,##0.0",
            }
        )

        # ============================================================
        # Шапка
        # ============================================================
        for col_idx, col in enumerate(
            work.columns
        ):
            worksheet.write(
                0,
                col_idx,
                col,
                header_fmt,
            )

        # ============================================================
        # Данные
        # ============================================================
        for row_idx, row in enumerate(
            work.itertuples(
                index=False,
                name=None,
            ),
            start=1,
        ):
            # Excel row 1 = первая строка данных.
            # Чередуем белый / очень светлый фон.
            is_alt = (
                row_idx % 2 == 0
            )

            worksheet.set_row(
                row_idx,
                20,
            )

            for col_idx, value in enumerate(row):
                col_name = work.columns[
                    col_idx
                ]

                # ----------------------------------------------------
                # Пустые значения
                # ----------------------------------------------------
                if pd.isna(value):
                    value = ""

                # ----------------------------------------------------
                # Десятичные
                # ----------------------------------------------------
                if col_name in decimal_cols:
                    fmt = (
                        decimal_alt_fmt
                        if is_alt
                        else decimal_fmt
                    )

                    if value == "":
                        worksheet.write_blank(
                            row_idx,
                            col_idx,
                            None,
                            fmt,
                        )
                    else:
                        worksheet.write_number(
                            row_idx,
                            col_idx,
                            float(value),
                            fmt,
                        )

                # ----------------------------------------------------
                # Целые
                # ----------------------------------------------------
                elif col_name in integer_cols:
                    fmt = (
                        integer_alt_fmt
                        if is_alt
                        else integer_fmt
                    )

                    if value == "":
                        worksheet.write_blank(
                            row_idx,
                            col_idx,
                            None,
                            fmt,
                        )
                    else:
                        worksheet.write_number(
                            row_idx,
                            col_idx,
                            float(value),
                            fmt,
                        )

                # ----------------------------------------------------
                # Текст
                # ----------------------------------------------------
                else:
                    fmt = (
                        text_alt_fmt
                        if is_alt
                        else text_fmt
                    )

                    worksheet.write(
                        row_idx,
                        col_idx,
                        value,
                        fmt,
                    )

        # ============================================================
        # Ширина колонок
        # ============================================================
        widths = {
            "Бренд": 18,
            "Категория": 22,
            "Пол": 12,
            "Артикул": 18,
            "Наименование": 48,
            "Размер": 12,
            "Остаток": 14,
            "В пути от клиента": 18,
            "В пути к клиенту": 18,
            "Итого": 14,
            "Продажи 7 дней": 16,
            "Оборачиваемость": 18,
            "NM ID": 16,
            "Chrt ID": 16,
        }

        for col_idx, col in enumerate(
            work.columns
        ):
            worksheet.set_column(
                col_idx,
                col_idx,
                widths.get(
                    col,
                    16,
                ),
            )

    # ================================================================
    # Имя файла
    # ================================================================
    output.seek(0)

    try:
        date_label = pd.to_datetime(
            report_date
        ).strftime("%Y-%m-%d")
    except Exception:
        date_label = datetime.now().strftime(
            "%Y-%m-%d"
        )

    safe_name = (
        str(
            warehouse_name
            or "warehouse"
        )
        .replace("/", "_")
        .replace("\\", "_")
        .replace(":", "_")
    )

    return (
        output.getvalue(),
        f"stocks_{safe_name}_{date_label}.xlsx",
    )