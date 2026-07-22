# # gear/app/daily_sales/stocks/transfer_excel.py
# from __future__ import annotations

# import io
# from datetime import datetime

# import pandas as pd


# def build_transfer_plan_excel(rows):
#     """
#     Excel-план перемещения.
#     Ничего в БД не записывает.
#     """
#     df = pd.DataFrame(rows or [])

#     if df.empty:
#         raise ValueError("Нет строк для формирования плана.")

#     if "Переместить" not in df:
#         raise ValueError("Нет колонки 'Переместить'.")

#     df["Переместить"] = pd.to_numeric(
#         df["Переместить"],
#         errors="coerce",
#     ).fillna(0)

#     df["Доступно"] = pd.to_numeric(
#         df.get("Доступно"),
#         errors="coerce",
#     ).fillna(0)

#     df = df[df["Переместить"] > 0].copy()

#     if df.empty:
#         raise ValueError("Не указано количество для перемещения.")

#     if (df["Переместить"] > df["Доступно"]).any():
#         raise ValueError(
#             "Количество перемещения превышает доступный остаток."
#         )

#     if df["Куда"].isna().any() or (
#         df["Куда"].astype(str).str.strip() == ""
#     ).any():
#         raise ValueError("Не для всех строк выбран склад назначения.")

#     columns = [
#         "Откуда",
#         "Регион откуда",
#         "Куда",
#         "Бренд",
#         "Категория",
#         "Артикул",
#         "Наименование",
#         "Размер",
#         "Доступно",
#         "Переместить",
#         "NM ID",
#         "Chrt ID",
#     ]
#     columns = [col for col in columns if col in df.columns]
#     df = df[columns]

#     output = io.BytesIO()

#     with pd.ExcelWriter(
#         output,
#         engine="xlsxwriter",
#     ) as writer:
#         df.to_excel(
#             writer,
#             sheet_name="План перемещения",
#             index=False,
#         )

#         workbook = writer.book
#         worksheet = writer.sheets["План перемещения"]

#         worksheet.hide_gridlines(2)
#         worksheet.freeze_panes(1, 0)
#         worksheet.autofilter(
#             0,
#             0,
#             len(df),
#             len(df.columns) - 1,
#         )

#         header_format = workbook.add_format(
#             {
#                 "bold": True,
#                 "font_name": "Arial",
#                 "font_size": 10,
#                 "bg_color": "#E3ECE8",
#                 "font_color": "#18352F",
#                 "border": 1,
#                 "border_color": "#C5D2CC",
#                 "align": "center",
#                 "valign": "vcenter",
#             }
#         )

#         text_format = workbook.add_format(
#             {
#                 "font_name": "Arial",
#                 "font_size": 10,
#                 "border": 1,
#                 "border_color": "#E2E8E5",
#             }
#         )

#         number_format = workbook.add_format(
#             {
#                 "font_name": "Arial",
#                 "font_size": 10,
#                 "border": 1,
#                 "border_color": "#E2E8E5",
#                 "num_format": "#,##0",
#             }
#         )

#         for col_num, value in enumerate(df.columns):
#             worksheet.write(
#                 0,
#                 col_num,
#                 value,
#                 header_format,
#             )

#         numeric_cols = {
#             "Доступно",
#             "Переместить",
#             "NM ID",
#             "Chrt ID",
#         }

#         for row_num in range(1, len(df) + 1):
#             for col_num, column in enumerate(df.columns):
#                 value = df.iloc[row_num - 1, col_num]
#                 fmt = (
#                     number_format
#                     if column in numeric_cols
#                     else text_format
#                 )

#                 if pd.isna(value):
#                     value = ""

#                 worksheet.write(
#                     row_num,
#                     col_num,
#                     value,
#                     fmt,
#                 )

#         widths = {
#             "Откуда": 28,
#             "Регион откуда": 28,
#             "Куда": 28,
#             "Бренд": 18,
#             "Категория": 22,
#             "Артикул": 18,
#             "Наименование": 45,
#             "Размер": 12,
#             "Доступно": 14,
#             "Переместить": 14,
#             "NM ID": 16,
#             "Chrt ID": 16,
#         }

#         for idx, column in enumerate(df.columns):
#             worksheet.set_column(
#                 idx,
#                 idx,
#                 widths.get(column, 16),
#             )

#     output.seek(0)

#     filename = (
#         "transfer_plan_"
#         f"{datetime.now():%Y-%m-%d_%H-%M}.xlsx"
#     )

#     return output.getvalue(), filename


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
    Унифицированное оформление листа Excel.
    """

    df.to_excel(
        writer,
        sheet_name=sheet_name,
        index=False,
    )

    workbook = writer.book
    worksheet = writer.sheets[
        sheet_name
    ]

    # -------------------------------------------------------------------------
    # Вид
    # -------------------------------------------------------------------------

    worksheet.hide_gridlines(2)

    worksheet.freeze_panes(
        1,
        0,
    )

    if len(df.columns) > 0:
        worksheet.autofilter(
            0,
            0,
            len(df),
            len(df.columns) - 1,
        )

    worksheet.set_row(
        0,
        24,
    )

    # -------------------------------------------------------------------------
    # Форматы
    # -------------------------------------------------------------------------

    header_format = (
        workbook.add_format(
            {
                "bold": True,

                "font_name": "Arial",
                "font_size": 10,

                "bg_color": "#E3ECE8",
                "font_color": "#18352F",

                "border": 1,
                "border_color": "#C5D2CC",

                "align": "center",
                "valign": "vcenter",
            }
        )
    )

    text_format = (
        workbook.add_format(
            {
                "font_name": "Arial",
                "font_size": 10,

                "border": 1,
                "border_color": "#E2E8E5",

                "valign": "vcenter",
            }
        )
    )

    number_format = (
        workbook.add_format(
            {
                "font_name": "Arial",
                "font_size": 10,

                "border": 1,
                "border_color": "#E2E8E5",

                "num_format": "#,##0",

                "valign": "vcenter",
            }
        )
    )

    decimal_format = (
        workbook.add_format(
            {
                "font_name": "Arial",
                "font_size": 10,

                "border": 1,
                "border_color": "#E2E8E5",

                "num_format": "#,##0.00",

                "valign": "vcenter",
            }
        )
    )

    # -------------------------------------------------------------------------
    # Header
    # -------------------------------------------------------------------------

    for col_num, value in enumerate(
        df.columns
    ):
        worksheet.write(
            0,
            col_num,
            value,
            header_format,
        )

    # -------------------------------------------------------------------------
    # Данные
    # -------------------------------------------------------------------------

    decimal_cols = set()

    for row_num in range(
        1,
        len(df) + 1,
    ):
        for col_num, column in enumerate(
            df.columns
        ):
            value = df.iloc[
                row_num - 1,
                col_num,
            ]

            if pd.isna(value):
                value = ""

            if column in decimal_cols:
                fmt = decimal_format

            elif column in numeric_cols:
                fmt = number_format

            else:
                fmt = text_format

            worksheet.write(
                row_num,
                col_num,
                value,
                fmt,
            )

    # -------------------------------------------------------------------------
    # Ширины
    # -------------------------------------------------------------------------

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
