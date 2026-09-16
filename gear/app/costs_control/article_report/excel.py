# gear/app/costs_control/article_report/excel.py
from __future__ import annotations

import io
from datetime import datetime

import pandas as pd

from .data import (
    build_article_summary,
    prepare_detail_sheet,
)


# ---------------------------------------------------------------------
# Константы
# ---------------------------------------------------------------------

SUMMARY_SHEET_NAME = "Анализ артикулов"
DETAIL_SHEET_NAME = "Детализация УПД"

EXCEL_FILENAME_PREFIX = "Анализ_закупочных_цен"


# ---------------------------------------------------------------------
# Палитра Excel
# ---------------------------------------------------------------------

EXCEL_COLORS = {
    "dark_green": "#2F6656",
    "green": "#3C7A67",
    "light_green": "#E7F1ED",
    "very_light_green": "#F3F8F6",

    "text": "#374151",
    "muted": "#6B7280",

    "border": "#D9DEE2",
    "light_border": "#E5E7EB",

    "white": "#FFFFFF",

    "success_bg": "#E7F1ED",
    "success_text": "#2F6656",

    "warning_bg": "#FFF6D8",
    "warning_text": "#9A6700",

    "error_bg": "#FDECEC",
    "error_text": "#A33A3A",
}


FONT_NAME = "Roboto"
FONT_SIZE = 10

TABLE_START_ROW = 4


# ---------------------------------------------------------------------
# Имя файла
# ---------------------------------------------------------------------

def build_report_filename() -> str:
    """
    Имя итогового Excel-файла.
    """

    return (
        f"{EXCEL_FILENAME_PREFIX}_"
        f"{datetime.now():%Y-%m-%d_%H-%M}.xlsx"
    )


# ---------------------------------------------------------------------
# Форматы
# ---------------------------------------------------------------------

def _build_formats(
    workbook,
) -> dict:
    """
    Все основные форматы Excel.
    """

    return {
        # -------------------------------------------------------------
        # Заголовок страницы
        # -------------------------------------------------------------

        "page_title": workbook.add_format(
            {
                "font_name": FONT_NAME,
                "font_size": 18,
                "bold": True,
                "font_color": EXCEL_COLORS[
                    "dark_green"
                ],
                "align": "left",
                "valign": "vcenter",
            }
        ),

        "page_subtitle": workbook.add_format(
            {
                "font_name": FONT_NAME,
                "font_size": 9,
                "font_color": EXCEL_COLORS[
                    "muted"
                ],
                "align": "left",
                "valign": "vcenter",
            }
        ),

        # -------------------------------------------------------------
        # Заголовки таблицы
        # -------------------------------------------------------------

        "header": workbook.add_format(
            {
                "font_name": FONT_NAME,
                "font_size": FONT_SIZE,
                "bold": True,
                "font_color": EXCEL_COLORS[
                    "white"
                ],
                "bg_color": EXCEL_COLORS[
                    "dark_green"
                ],
                "border": 1,
                "border_color": EXCEL_COLORS[
                    "border"
                ],
                "align": "center",
                "valign": "vcenter",
                "text_wrap": True,
            }
        ),

        # -------------------------------------------------------------
        # Обычный текст
        # -------------------------------------------------------------

        "text": workbook.add_format(
            {
                "font_name": FONT_NAME,
                "font_size": FONT_SIZE,
                "font_color": EXCEL_COLORS[
                    "text"
                ],
                "border": 1,
                "border_color": EXCEL_COLORS[
                    "light_border"
                ],
                "align": "left",
                "valign": "vcenter",
            }
        ),

        "text_center": workbook.add_format(
            {
                "font_name": FONT_NAME,
                "font_size": FONT_SIZE,
                "font_color": EXCEL_COLORS[
                    "text"
                ],
                "border": 1,
                "border_color": EXCEL_COLORS[
                    "light_border"
                ],
                "align": "center",
                "valign": "vcenter",
            }
        ),

        # -------------------------------------------------------------
        # Идентификаторы
        # -------------------------------------------------------------

        "id": workbook.add_format(
            {
                "font_name": FONT_NAME,
                "font_size": FONT_SIZE,
                "font_color": EXCEL_COLORS[
                    "text"
                ],
                "border": 1,
                "border_color": EXCEL_COLORS[
                    "light_border"
                ],
                "num_format": "@",
                "align": "left",
                "valign": "vcenter",
            }
        ),

        # -------------------------------------------------------------
        # Целые значения
        # -------------------------------------------------------------

        "integer": workbook.add_format(
            {
                "font_name": FONT_NAME,
                "font_size": FONT_SIZE,
                "font_color": EXCEL_COLORS[
                    "text"
                ],
                "border": 1,
                "border_color": EXCEL_COLORS[
                    "light_border"
                ],
                "num_format": "#,##0",
                "align": "right",
                "valign": "vcenter",
            }
        ),

        # -------------------------------------------------------------
        # Обычные числа
        # -------------------------------------------------------------

        "number": workbook.add_format(
            {
                "font_name": FONT_NAME,
                "font_size": FONT_SIZE,
                "font_color": EXCEL_COLORS[
                    "text"
                ],
                "border": 1,
                "border_color": EXCEL_COLORS[
                    "light_border"
                ],
                "num_format": "#,##0.00",
                "align": "right",
                "valign": "vcenter",
            }
        ),

        # -------------------------------------------------------------
        # Денежные значения
        # -------------------------------------------------------------

        "money": workbook.add_format(
            {
                "font_name": FONT_NAME,
                "font_size": FONT_SIZE,
                "font_color": EXCEL_COLORS[
                    "text"
                ],
                "border": 1,
                "border_color": EXCEL_COLORS[
                    "light_border"
                ],
                "num_format": '#,##0.00 "₽"',
                "align": "right",
                "valign": "vcenter",
            }
        ),

        # -------------------------------------------------------------
        # Даты
        # -------------------------------------------------------------

        "date": workbook.add_format(
            {
                "font_name": FONT_NAME,
                "font_size": FONT_SIZE,
                "font_color": EXCEL_COLORS[
                    "text"
                ],
                "border": 1,
                "border_color": EXCEL_COLORS[
                    "light_border"
                ],
                "num_format": "dd.mm.yyyy",
                "align": "center",
                "valign": "vcenter",
            }
        ),

        # -------------------------------------------------------------
        # Выделение Article / NM ID
        # -------------------------------------------------------------

        "id_highlight": workbook.add_format(
            {
                "font_name": FONT_NAME,
                "font_size": FONT_SIZE,
                "font_color": EXCEL_COLORS[
                    "dark_green"
                ],
                "bg_color": EXCEL_COLORS[
                    "very_light_green"
                ],
                "border": 1,
                "border_color": EXCEL_COLORS[
                    "light_border"
                ],
                "num_format": "@",
                "align": "left",
                "valign": "vcenter",
            }
        ),
    }


# ---------------------------------------------------------------------
# Заголовок листа
# ---------------------------------------------------------------------

def _write_report_title(
    worksheet,
    formats: dict,
    title: str,
    subtitle: str,
    last_column: int,
):
    """
    Верхняя часть Excel-листа.
    """

    worksheet.merge_range(
        0,
        0,
        0,
        last_column,
        title.upper(),
        formats[
            "page_title"
        ],
    )

    worksheet.merge_range(
        1,
        0,
        1,
        last_column,
        subtitle,
        formats[
            "page_subtitle"
        ],
    )

    worksheet.set_row(
        0,
        30,
    )

    worksheet.set_row(
        1,
        20,
    )

    # Небольшой воздух
    # между заголовком и таблицей.
    worksheet.set_row(
        2,
        8,
    )

    worksheet.set_row(
        3,
        8,
    )


# ---------------------------------------------------------------------
# Запись DataFrame вручную
# ---------------------------------------------------------------------

def _write_dataframe(
    worksheet,
    df: pd.DataFrame,
    formats: dict,
    start_row: int,
):
    """
    Записывает DataFrame с контролируемым
    форматированием каждой ячейки.

    Благодаря этому оформление применяется
    только к реальным строкам данных.
    """

    # -------------------------------------------------------------
    # Заголовки
    # -------------------------------------------------------------

    for col_idx, column in enumerate(
        df.columns
    ):
        worksheet.write(
            start_row,
            col_idx,
            column,
            formats[
                "header"
            ],
        )

    # -------------------------------------------------------------
    # Данные
    # -------------------------------------------------------------

    for row_offset, (_, row) in enumerate(
        df.iterrows(),
        start=1,
    ):
        excel_row = (
            start_row
            + row_offset
        )

        # Более аккуратная высота строки.
        worksheet.set_row(
            excel_row,
            22,
        )

        for col_idx, column in enumerate(
            df.columns
        ):
            value = row[
                column
            ]

            column_lower = (
                column.lower()
            )

            # -----------------------------------------------------
            # NaN / NaT
            # -----------------------------------------------------

            if pd.isna(
                value
            ):
                worksheet.write_blank(
                    excel_row,
                    col_idx,
                    None,
                    formats[
                        "text"
                    ],
                )
                continue

            # -----------------------------------------------------
            # Article / NM ID
            # -----------------------------------------------------

            if column in (
                "Article",
                "NM ID",
            ):
                worksheet.write_string(
                    excel_row,
                    col_idx,
                    str(
                        value
                    ),
                    formats[
                        "id_highlight"
                    ],
                )

            # -----------------------------------------------------
            # ID УПД
            # -----------------------------------------------------

            elif column == "ID УПД":
                worksheet.write_string(
                    excel_row,
                    col_idx,
                    str(
                        value
                    ),
                    formats[
                        "id"
                    ],
                )

            # -----------------------------------------------------
            # Даты
            # -----------------------------------------------------

            elif (
                "дата"
                in column_lower
                and isinstance(
                    value,
                    (
                        pd.Timestamp,
                        datetime,
                    ),
                )
            ):
                worksheet.write_datetime(
                    excel_row,
                    col_idx,
                    value.to_pydatetime()
                    if isinstance(
                        value,
                        pd.Timestamp,
                    )
                    else value,
                    formats[
                        "date"
                    ],
                )

            # -----------------------------------------------------
            # Денежные поля
            # -----------------------------------------------------

            elif (
                "цена"
                in column_lower
                or "сумма"
                in column_lower
            ):
                worksheet.write_number(
                    excel_row,
                    col_idx,
                    float(
                        value
                    ),
                    formats[
                        "money"
                    ],
                )

            # -----------------------------------------------------
            # Количество
            # -----------------------------------------------------

            elif (
                "количество"
                in column_lower
            ):
                worksheet.write_number(
                    excel_row,
                    col_idx,
                    float(
                        value
                    ),
                    formats[
                        "integer"
                    ],
                )

            # -----------------------------------------------------
            # Остальное
            # -----------------------------------------------------

            else:
                worksheet.write(
                    excel_row,
                    col_idx,
                    value,
                    formats[
                        "text"
                    ],
                )


# ---------------------------------------------------------------------
# Ширины колонок
# ---------------------------------------------------------------------

def _set_column_widths(
    worksheet,
    df: pd.DataFrame,
):
    """
    Профессиональные ширины колонок.
    """

    widths = {
        "Article": 18,
        "NM ID": 15,
        "Наименование": 48,

        "Первая дата УПД": 16,
        "Последняя дата УПД": 16,

        "Количество УПД": 15,
        "Количество, шт": 17,

        "Минимальная цена, бух": 20,
        "Максимальная цена, бух": 20,
        "Средняя цена, бух": 19,
        "Медиана цены, бух": 19,

        "Минимальная цена, упр": 20,
        "Максимальная цена, упр": 20,
        "Средняя цена, упр": 19,
        "Медиана цены, упр": 19,

        "Дата УПД": 14,
        "Номер УПД": 20,
        "ID УПД": 16,

        "Поставщик": 34,

        "Цена, бух": 17,
        "Цена, упр": 17,

        "Сумма без НДС": 20,

        "Статус": 25,
    }

    for col_idx, column in enumerate(
        df.columns
    ):
        worksheet.set_column(
            col_idx,
            col_idx,
            widths.get(
                column,
                16,
            ),
        )


# ---------------------------------------------------------------------
# Базовое оформление листа
# ---------------------------------------------------------------------

def _format_excel_sheet(
    workbook,
    worksheet,
    df: pd.DataFrame,
    title: str,
    subtitle: str,
):
    """
    Оформляет лист.
    """

    if len(
        df.columns
    ) == 0:
        return

    formats = (
        _build_formats(
            workbook
        )
    )

    last_column = (
        len(
            df.columns
        )
        - 1
    )

    _write_report_title(
        worksheet=worksheet,
        formats=formats,
        title=title,
        subtitle=subtitle,
        last_column=last_column,
    )

    _write_dataframe(
        worksheet=worksheet,
        df=df,
        formats=formats,
        start_row=TABLE_START_ROW,
    )

    _set_column_widths(
        worksheet,
        df,
    )

    # -------------------------------------------------------------
    # Высота строки заголовков
    # -------------------------------------------------------------

    worksheet.set_row(
        TABLE_START_ROW,
        34,
    )

    # -------------------------------------------------------------
    # Закрепление
    #
    # Таблица начинается с 5-й строки Excel,
    # поэтому закрепляем после строки заголовка.
    # -------------------------------------------------------------

    worksheet.freeze_panes(
        TABLE_START_ROW + 1,
        2,
    )

    # -------------------------------------------------------------
    # Автофильтр только на реальном диапазоне.
    # Никаких лишних строк вниз.
    # -------------------------------------------------------------

    if not df.empty:
        worksheet.autofilter(
            TABLE_START_ROW,
            0,
            TABLE_START_ROW
            + len(
                df
            ),
            last_column,
        )

    # -------------------------------------------------------------
    # Убираем стандартную сетку Excel.
    # Границы есть только у таблицы.
    # Поэтому после окончания данных
    # лист остаётся чистым.
    # -------------------------------------------------------------

    worksheet.hide_gridlines(
        2
    )

    # -------------------------------------------------------------
    # Масштаб
    # -------------------------------------------------------------

    worksheet.set_zoom(
        90
    )

    # -------------------------------------------------------------
    # Печать
    # -------------------------------------------------------------

    worksheet.set_landscape()

    worksheet.fit_to_pages(
        1,
        0,
    )

    worksheet.set_margins(
        left=0.3,
        right=0.3,
        top=0.5,
        bottom=0.5,
    )


# ---------------------------------------------------------------------
# Статусы
# ---------------------------------------------------------------------

def _apply_status_formatting(
    workbook,
    worksheet,
    summary_df: pd.DataFrame,
):
    """
    Подсвечивает статус.
    """

    if (
        summary_df.empty
        or "Статус"
        not in summary_df.columns
    ):
        return

    status_col = (
        summary_df.columns.get_loc(
            "Статус"
        )
    )

    first_data_row = (
        TABLE_START_ROW
        + 1
    )

    last_data_row = (
        TABLE_START_ROW
        + len(
            summary_df
        )
    )

    success_format = (
        workbook.add_format(
            {
                "font_name": FONT_NAME,
                "font_size": FONT_SIZE,
                "font_color": EXCEL_COLORS[
                    "success_text"
                ],
                "bg_color": EXCEL_COLORS[
                    "success_bg"
                ],
                "border": 1,
                "border_color": EXCEL_COLORS[
                    "light_border"
                ],
                "align": "center",
                "valign": "vcenter",
            }
        )
    )

    warning_format = (
        workbook.add_format(
            {
                "font_name": FONT_NAME,
                "font_size": FONT_SIZE,
                "font_color": EXCEL_COLORS[
                    "warning_text"
                ],
                "bg_color": EXCEL_COLORS[
                    "warning_bg"
                ],
                "border": 1,
                "border_color": EXCEL_COLORS[
                    "light_border"
                ],
                "align": "center",
                "valign": "vcenter",
            }
        )
    )

    error_format = (
        workbook.add_format(
            {
                "font_name": FONT_NAME,
                "font_size": FONT_SIZE,
                "font_color": EXCEL_COLORS[
                    "error_text"
                ],
                "bg_color": EXCEL_COLORS[
                    "error_bg"
                ],
                "border": 1,
                "border_color": EXCEL_COLORS[
                    "light_border"
                ],
                "align": "center",
                "valign": "vcenter",
            }
        )
    )

    worksheet.conditional_format(
        first_data_row,
        status_col,
        last_data_row,
        status_col,
        {
            "type": "text",
            "criteria": "containing",
            "value": "Данные найдены",
            "format": success_format,
        },
    )

    worksheet.conditional_format(
        first_data_row,
        status_col,
        last_data_row,
        status_col,
        {
            "type": "text",
            "criteria": "containing",
            "value": "УПД не найдены",
            "format": warning_format,
        },
    )

    worksheet.conditional_format(
        first_data_row,
        status_col,
        last_data_row,
        status_col,
        {
            "type": "text",
            "criteria": "containing",
            "value": "Артикул не сопоставлен",
            "format": error_format,
        },
    )


# ---------------------------------------------------------------------
# Создание Excel
# ---------------------------------------------------------------------

def build_excel_report(
    articles: list[str],
    history_df: pd.DataFrame,
) -> bytes:
    """
    Формирует профессионально
    оформленный Excel-отчёт.
    """

    summary_df = (
        build_article_summary(
            articles,
            history_df,
        )
    )

    detail_df = (
        prepare_detail_sheet(
            history_df
        )
    )

    output = (
        io.BytesIO()
    )

    with pd.ExcelWriter(
        output,
        engine="xlsxwriter",
        datetime_format="dd.mm.yyyy",
        date_format="dd.mm.yyyy",
    ) as writer:

        # Создаём пустые листы.
        summary_worksheet = (
            writer.book.add_worksheet(
                SUMMARY_SHEET_NAME
            )
        )

        detail_worksheet = (
            writer.book.add_worksheet(
                DETAIL_SHEET_NAME
            )
        )

        writer.sheets[
            SUMMARY_SHEET_NAME
        ] = summary_worksheet

        writer.sheets[
            DETAIL_SHEET_NAME
        ] = detail_worksheet

        workbook = (
            writer.book
        )

        now_text = (
            datetime.now()
            .strftime(
                "%d.%m.%Y %H:%M"
            )
        )

        found_count = int(
            summary_df[
                "Статус"
            ]
            .eq(
                "Данные найдены"
            )
            .sum()
        )

        mapped_without_upd = int(
            summary_df[
                "Статус"
            ]
            .eq(
                (
                    "NM ID найден, "
                    "УПД не найдены"
                )
            )
            .sum()
        )

        not_mapped = int(
            summary_df[
                "Статус"
            ]
            .eq(
                "Артикул не сопоставлен"
            )
            .sum()
        )

        summary_subtitle = (
            f"Артикулов загружено: "
            f"{len(articles):,}   |   "
            f"С данными УПД: "
            f"{found_count:,}   |   "
            f"NM ID без УПД: "
            f"{mapped_without_upd:,}   |   "
            f"Не сопоставлено: "
            f"{not_mapped:,}   |   "
            f"Сформировано: "
            f"{now_text}"
        ).replace(
            ",",
            " ",
        )

        detail_subtitle = (
            f"Строк детализации: "
            f"{len(detail_df):,}   |   "
            f"Сформировано: "
            f"{now_text}"
        ).replace(
            ",",
            " ",
        )

        # ---------------------------------------------------------
        # Первый лист
        # ---------------------------------------------------------

        _format_excel_sheet(
            workbook=workbook,
            worksheet=summary_worksheet,
            df=summary_df,
            title=(
                "Сводный анализ "
                "по артикулам"
            ),
            subtitle=(
                summary_subtitle
            ),
        )

        # ---------------------------------------------------------
        # Детализация
        # ---------------------------------------------------------

        _format_excel_sheet(
            workbook=workbook,
            worksheet=detail_worksheet,
            df=detail_df,
            title=(
                "Детализация "
                "закупочных цен по УПД"
            ),
            subtitle=(
                detail_subtitle
            ),
        )

        # ---------------------------------------------------------
        # Статусы
        # ---------------------------------------------------------

        _apply_status_formatting(
            workbook=workbook,
            worksheet=summary_worksheet,
            summary_df=summary_df,
        )

        # ---------------------------------------------------------
        # Активный лист при открытии
        # ---------------------------------------------------------

        summary_worksheet.activate()

        summary_worksheet.select()

    output.seek(
        0
    )

    return output.getvalue()