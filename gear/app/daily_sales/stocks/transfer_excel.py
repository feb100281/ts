# gear/app/daily_sales/stocks/transfer_excel.py

from __future__ import annotations

import io
from datetime import datetime

import pandas as pd


# =============================================================================
# ОБЩИЕ ФОРМАТЫ
# =============================================================================

def _write_dataframe(
    writer,
    df: pd.DataFrame,
    sheet_name: str,
    widths: dict,
    numeric_cols: set,
):
    """
    Унифицированное аккуратное оформление листа Excel.

    Стиль:
    - Helvetica Light, 10 pt
    - закреплена шапка и первая колонка
    - лёгкая зебра
    - тонкие светло-серые границы
    - фильтры
    - без стандартной сетки Excel
    """

    workbook = writer.book

    worksheet = workbook.add_worksheet(
        sheet_name
    )

    writer.sheets[sheet_name] = worksheet

    # ================================================================
    # Общий вид
    # ================================================================
    worksheet.hide_gridlines(2)

    # Закрепляем шапку + первую колонку
    worksheet.freeze_panes(
        1,
        1,
    )

    worksheet.set_zoom(90)

    worksheet.set_row(
        0,
        28,
    )

    if len(df.columns) > 0:
        worksheet.autofilter(
            0,
            0,
            len(df),
            len(df.columns) - 1,
        )

    # ================================================================
    # Цвета / шрифт
    # ================================================================
    font_name = "Helvetica Light"
    font_size = 10

    header_bg = "#E8EFEC"
    header_font = "#203832"

    row_bg = "#FFFFFF"
    row_alt_bg = "#F7F9F8"

    border_color = "#D9DEDC"

    # ================================================================
    # Форматы
    # ================================================================
    header_format = workbook.add_format(
        {
            "font_name": font_name,
            "font_size": font_size,
            "bold": False,

            "bg_color": header_bg,
            "font_color": header_font,

            "border": 1,
            "border_color": border_color,

            "align": "center",
            "valign": "vcenter",

            "text_wrap": True,
        }
    )

    text_format = workbook.add_format(
        {
            "font_name": font_name,
            "font_size": font_size,

            "bg_color": row_bg,

            "border": 1,
            "border_color": border_color,

            "align": "left",
            "valign": "vcenter",
        }
    )

    text_alt_format = workbook.add_format(
        {
            "font_name": font_name,
            "font_size": font_size,

            "bg_color": row_alt_bg,

            "border": 1,
            "border_color": border_color,

            "align": "left",
            "valign": "vcenter",
        }
    )

    number_format = workbook.add_format(
        {
            "font_name": font_name,
            "font_size": font_size,

            "bg_color": row_bg,

            "border": 1,
            "border_color": border_color,

            "align": "right",
            "valign": "vcenter",

            "num_format": "#,##0",
        }
    )

    number_alt_format = workbook.add_format(
        {
            "font_name": font_name,
            "font_size": font_size,

            "bg_color": row_alt_bg,

            "border": 1,
            "border_color": border_color,

            "align": "right",
            "valign": "vcenter",

            "num_format": "#,##0",
        }
    )

    # ================================================================
    # Шапка
    # ================================================================
    for col_num, column in enumerate(
        df.columns
    ):
        worksheet.write(
            0,
            col_num,
            column,
            header_format,
        )

    # ================================================================
    # Данные
    # ================================================================
    for row_num, row in enumerate(
        df.itertuples(
            index=False,
            name=None,
        ),
        start=1,
    ):
        is_alt = (
            row_num % 2 == 0
        )

        worksheet.set_row(
            row_num,
            20,
        )

        for col_num, value in enumerate(row):
            column = df.columns[
                col_num
            ]

            if pd.isna(value):
                value = ""

            if column in numeric_cols:
                fmt = (
                    number_alt_format
                    if is_alt
                    else number_format
                )

                if value == "":
                    worksheet.write_blank(
                        row_num,
                        col_num,
                        None,
                        fmt,
                    )
                else:
                    worksheet.write_number(
                        row_num,
                        col_num,
                        float(value),
                        fmt,
                    )

            else:
                fmt = (
                    text_alt_format
                    if is_alt
                    else text_format
                )

                worksheet.write(
                    row_num,
                    col_num,
                    value,
                    fmt,
                )

    # ================================================================
    # Ширина колонок
    # ================================================================
    for idx, column in enumerate(
        df.columns
    ):
        worksheet.set_column(
            idx,
            idx,
            widths.get(
                column,
                16,
            ),
        )

# =============================================================================
# EXCEL ПЛАНА ПЕРЕМЕЩЕНИЯ
# =============================================================================

def build_transfer_plan_excel(
    rows,
):
    """
    Excel-план перемещения.

    Ничего в БД не записывает.
    """

    df = pd.DataFrame(
        rows or []
    )

    if df.empty:
        raise ValueError(
            "Нет строк для формирования плана."
        )

    if "Переместить" not in df.columns:
        raise ValueError(
            "Нет колонки 'Переместить'."
        )

    # -------------------------------------------------------------------------
    # Числа
    # -------------------------------------------------------------------------

    df["Переместить"] = (
        pd.to_numeric(
            df["Переместить"],
            errors="coerce",
        ).fillna(0)
    )

    if "Доступно" not in df.columns:
        df["Доступно"] = 0

    df["Доступно"] = (
        pd.to_numeric(
            df["Доступно"],
            errors="coerce",
        ).fillna(0)
    )

    # -------------------------------------------------------------------------
    # Только реально перемещаемые строки
    # -------------------------------------------------------------------------

    df = df[
        df["Переместить"] > 0
    ].copy()

    if df.empty:
        raise ValueError(
            "Не указано количество для перемещения."
        )

    # -------------------------------------------------------------------------
    # Проверка количества
    # -------------------------------------------------------------------------

    if (
        df["Переместить"]
        > df["Доступно"]
    ).any():
        raise ValueError(
            "Количество перемещения "
            "превышает доступный остаток."
        )

    # -------------------------------------------------------------------------
    # Проверка склада назначения
    # -------------------------------------------------------------------------

    if "Куда" not in df.columns:
        raise ValueError(
            "Нет склада назначения."
        )

    destination_empty = (
        df["Куда"].isna()
        |
        (
            df["Куда"]
            .astype(str)
            .str.strip()
            == ""
        )
    )

    if destination_empty.any():
        raise ValueError(
            "Не для всех строк выбран "
            "склад назначения."
        )

    # -------------------------------------------------------------------------
    # Колонки
    # -------------------------------------------------------------------------

    columns = [
        "Откуда",
        "Регион откуда",
        "Куда",
        "Бренд",
        "Категория",
        "Артикул",
        "Наименование",
        "Размер",
        "Доступно",
        "Переместить",
        "NM ID",
        "Chrt ID",
    ]

    columns = [
        col
        for col in columns
        if col in df.columns
    ]

    df = df[
        columns
    ].copy()

    # -------------------------------------------------------------------------
    # Excel
    # -------------------------------------------------------------------------

    output = io.BytesIO()

    with pd.ExcelWriter(
        output,
        engine="xlsxwriter",
    ) as writer:

        widths = {
            "Откуда": 28,
            "Регион откуда": 28,
            "Куда": 28,

            "Бренд": 18,
            "Категория": 22,

            "Артикул": 18,
            "Наименование": 45,
            "Размер": 12,

            "Доступно": 14,
            "Переместить": 14,

            "NM ID": 16,
            "Chrt ID": 16,
        }

        numeric_cols = {
            "Доступно",
            "Переместить",
            "NM ID",
            "Chrt ID",
        }

        _write_dataframe(
            writer=writer,

            df=df,

            sheet_name=(
                "План перемещения"
            ),

            widths=widths,

            numeric_cols=numeric_cols,
        )

    output.seek(0)

    filename = (
        "transfer_plan_"
        f"{datetime.now():%Y-%m-%d_%H-%M}.xlsx"
    )

    return (
        output.getvalue(),
        filename,
    )


# =============================================================================
# EXCEL ТАБЛИЦЫ СКЛАДОВ
# =============================================================================

def build_warehouses_excel(
    rows,
    report_date=None,
):
    """
    Excel таблицы складов.

    rows приходят из AG Grid virtualRowData,
    поэтому Excel содержит только строки,
    которые остались после встроенных фильтров
    и сортировки пользователя.
    """

    df = pd.DataFrame(
        rows or []
    )

    if df.empty:
        raise ValueError(
            "Нет складов для выгрузки."
        )

    # -------------------------------------------------------------------------
    # Переименовываем технические названия
    # -------------------------------------------------------------------------

    rename_map = {
        "region": "Регион",
        "warehouse": "Склад",
        "products": "NM ID",
        "on_hand": "На складе",
        "in_transit": "В пути",
        "total_qty": "Итого",
    }

    df = df.rename(
        columns=rename_map
    )

    # -------------------------------------------------------------------------
    # Оставляем только бизнес-колонки.
    #
    # lon / lat / map_excluded / has_coordinates
    # в Excel пользователю не нужны.
    # -------------------------------------------------------------------------

    columns = [
        "Регион",
        "Склад",
        "NM ID",
        "На складе",
        "В пути",
        "Итого",
    ]

    columns = [
        col
        for col in columns
        if col in df.columns
    ]

    df = df[
        columns
    ].copy()

    if df.empty:
        raise ValueError(
            "Нет колонок для выгрузки."
        )

    # -------------------------------------------------------------------------
    # Числа
    # -------------------------------------------------------------------------

    numeric_cols = {
        "NM ID",
        "На складе",
        "В пути",
        "Итого",
    }

    for column in numeric_cols:
        if column in df.columns:
            df[column] = (
                pd.to_numeric(
                    df[column],
                    errors="coerce",
                ).fillna(0)
            )

    # -------------------------------------------------------------------------
    # Excel
    # -------------------------------------------------------------------------

    output = io.BytesIO()

    with pd.ExcelWriter(
        output,
        engine="xlsxwriter",
    ) as writer:

        widths = {
            "Регион": 28,
            "Склад": 32,
            "NM ID": 14,
            "На складе": 16,
            "В пути": 16,
            "Итого": 16,
        }

        _write_dataframe(
            writer=writer,

            df=df,

            sheet_name="Склады",

            widths=widths,

            numeric_cols=numeric_cols,
        )

    output.seek(0)

    # -------------------------------------------------------------------------
    # Имя файла
    # -------------------------------------------------------------------------

    if report_date:
        try:
            date_label = (
                pd.to_datetime(
                    report_date
                ).strftime(
                    "%Y-%m-%d"
                )
            )
        except Exception:
            date_label = (
                datetime.now().strftime(
                    "%Y-%m-%d"
                )
            )

    else:
        date_label = (
            datetime.now().strftime(
                "%Y-%m-%d"
            )
        )

    filename = (
        f"warehouses_{date_label}.xlsx"
    )

    return (
        output.getvalue(),
        filename,
    )
