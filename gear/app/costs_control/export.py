# gear/app/costs_contol/export.py
from __future__ import annotations

from datetime import date, datetime
from io import BytesIO
from typing import Any

import pandas as pd
from dash import dcc

from .config import (
    COLORS,
    PRICE_ANALYSIS_EXCEL_PREFIX,
)


# ---------------------------------------------------------------------
# Названия листов
# ---------------------------------------------------------------------


ANALYSIS_SHEET_NAME = "Анализ"
HISTORY_SHEET_NAME = "История цен"


# ---------------------------------------------------------------------
# Группы колонок
# ---------------------------------------------------------------------


DATE_COLUMNS = {
    "Первая дата УПД",
    "Последняя дата УПД",
    "Дата УПД",
}


INTEGER_COLUMNS = {
    "nm_id",
    "Кол-во записей",
    "Кол-во, шт",
    "Кол-во УПД",
    "Кол-во разных цен, бух",
    "Кол-во разных цен, упр",
    "Количество, шт",
    "ID УПД",
}


PERCENT_COLUMNS = {
    "Коэффициент вариации, %, бух",
    "Коэффициент вариации, %, упр",
    "Макс. отклонение от медианы, %, бух",
    "Мин. отклонение от медианы, %, бух",
    "Макс. отклонение от медианы, %, упр",
    "Мин. отклонение от медианы, %, упр",
    "Δ медианы упр-бух, %",
}


MONEY_COLUMNS = {
    "Медиана цены, бух",
    "Средняя цена, бух",
    "Ст. отклонение, руб., бух",
    "Мин. цена, бух",
    "Макс. цена, бух",
    "Диапазон цены, бух",
    "Медиана цены, упр",
    "Средняя цена, упр",
    "Ст. отклонение, руб., упр",
    "Мин. цена, упр",
    "Макс. цена, упр",
    "Диапазон цены, упр",
    "Δ медианы упр-бух, руб.",
    "Цена, бух",
    "Цена, упр",
    "Сумма, бух",
    "Сумма, упр",
}


TEXT_WIDE_COLUMNS = {
    "Наименование",
    "Поставщик",
    "Поставщики",
}


TEXT_MEDIUM_COLUMNS = {
    "Бренд",
    "Категория",
    "Номер УПД",
    "Документ",
    "Ранг CV, бух",
    "Ранг CV, упр",
}


# ---------------------------------------------------------------------
# Служебные функции
# ---------------------------------------------------------------------


def _build_filename(
    extension: str,
) -> str:
    """
    Формирует имя экспортируемого файла.
    """

    timestamp = datetime.now().strftime(
        "%Y-%m-%d_%H-%M"
    )

    return (
        f"{PRICE_ANALYSIS_EXCEL_PREFIX}_"
        f"{timestamp}.{extension}"
    )


def _normalise_nm_id(
    value: Any,
) -> str | None:
    """
    Приводит NM ID к строке без окончания .0.
    """

    if value is None:
        return None

    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    text = str(value).strip()

    if text.endswith(".0"):
        text = text[:-2]

    return text or None


def _prepare_dataframe(
    df: pd.DataFrame | None,
) -> pd.DataFrame:
    """
    Подготавливает DataFrame для записи в Excel или CSV.

    - копирует исходный DataFrame;
    - нормализует NM ID;
    - преобразует даты;
    - заменяет бесконечности и NaN.
    """

    if df is None or df.empty:
        if df is None:
            return pd.DataFrame()

        return df.copy()

    work = df.copy()

    if "nm_id" in work.columns:
        work["nm_id"] = work["nm_id"].apply(
            _normalise_nm_id
        )

    for column in DATE_COLUMNS:
        if column in work.columns:
            work[column] = pd.to_datetime(
                work[column],
                errors="coerce",
            )

    work = work.replace(
        {
            float("inf"): None,
            float("-inf"): None,
        }
    )

    return work


def _safe_numeric_value(
    value: Any,
) -> float | int | None:
    """
    Преобразует значение в число для корректной записи в Excel.
    """

    if value is None:
        return None

    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    number = pd.to_numeric(
        value,
        errors="coerce",
    )

    if pd.isna(number):
        return None

    return number.item() if hasattr(number, "item") else number


def _get_column_width(
    column: str,
    series: pd.Series,
) -> int:
    """
    Рассчитывает ширину Excel-колонки.
    """

    if column == "nm_id":
        return 15

    if column in TEXT_WIDE_COLUMNS:
        return 34

    if column in TEXT_MEDIUM_COLUMNS:
        return 22

    if column in DATE_COLUMNS:
        return 14

    if column in MONEY_COLUMNS:
        return 17

    if column in PERCENT_COLUMNS:
        return 18

    if column in INTEGER_COLUMNS:
        return 15

    header_length = len(str(column))

    if series.empty:
        return min(
            max(header_length + 2, 12),
            24,
        )

    try:
        values_length = (
            series
            .dropna()
            .astype(str)
            .str.len()
        )

        max_value_length = (
            int(values_length.max())
            if not values_length.empty
            else 0
        )
    except Exception:
        max_value_length = 0

    return min(
        max(
            header_length + 2,
            max_value_length + 2,
            12,
        ),
        28,
    )


# ---------------------------------------------------------------------
# Форматы Excel
# ---------------------------------------------------------------------


def _build_formats(
    workbook,
) -> dict[str, Any]:
    """
    Создаёт все используемые форматы XlsxWriter.
    """

    border_color = COLORS.get(
        "border",
        "#D9DEE2",
    )

    text_color = COLORS.get(
        "text",
        "#111827",
    )

    muted_color = COLORS.get(
        "muted",
        "#6B7280",
    )

    green = COLORS.get(
        "green",
        "#3C7A67",
    )

    light_green = COLORS.get(
        "light_green",
        "#E7F1ED",
    )

    light_red = COLORS.get(
        "light_red",
        "#FDECEC",
    )

    red = COLORS.get(
        "red",
        "#A33A3A",
    )

    light_yellow = COLORS.get(
        "light_yellow",
        "#FFF6D8",
    )

    yellow = COLORS.get(
        "yellow",
        "#9A6700",
    )

    light_blue = COLORS.get(
        "light_blue",
        "#EDF4FA",
    )

    blue = COLORS.get(
        "blue",
        "#3B6B8F",
    )

    header = workbook.add_format(
        {
            "font_name": "Arial",
            "font_size": 10,
            "bold": True,
            "font_color": "#FFFFFF",
            "bg_color": green,
            "border": 1,
            "border_color": green,
            "align": "center",
            "valign": "vcenter",
            "text_wrap": True,
        }
    )

    text = workbook.add_format(
        {
            "font_name": "Arial",
            "font_size": 10,
            "font_color": text_color,
            "border": 1,
            "border_color": border_color,
            "align": "left",
            "valign": "vcenter",
        }
    )

    text_wrap = workbook.add_format(
        {
            "font_name": "Arial",
            "font_size": 10,
            "font_color": text_color,
            "border": 1,
            "border_color": border_color,
            "align": "left",
            "valign": "top",
            "text_wrap": True,
        }
    )

    center = workbook.add_format(
        {
            "font_name": "Arial",
            "font_size": 10,
            "font_color": text_color,
            "border": 1,
            "border_color": border_color,
            "align": "center",
            "valign": "vcenter",
        }
    )

    integer = workbook.add_format(
        {
            "font_name": "Arial",
            "font_size": 10,
            "font_color": text_color,
            "border": 1,
            "border_color": border_color,
            "align": "right",
            "valign": "vcenter",
            "num_format": "#,##0",
        }
    )

    money = workbook.add_format(
        {
            "font_name": "Arial",
            "font_size": 10,
            "font_color": text_color,
            "border": 1,
            "border_color": border_color,
            "align": "right",
            "valign": "vcenter",
            "num_format": '#,##0.00" ₽"',
        }
    )

    percent = workbook.add_format(
        {
            "font_name": "Arial",
            "font_size": 10,
            "font_color": text_color,
            "border": 1,
            "border_color": border_color,
            "align": "right",
            "valign": "vcenter",
            "num_format": '0.00"%"',
        }
    )

    date_format = workbook.add_format(
        {
            "font_name": "Arial",
            "font_size": 10,
            "font_color": text_color,
            "border": 1,
            "border_color": border_color,
            "align": "center",
            "valign": "vcenter",
            "num_format": "dd.mm.yyyy",
        }
    )

    empty = workbook.add_format(
        {
            "font_name": "Arial",
            "font_size": 10,
            "font_color": muted_color,
            "italic": True,
            "align": "left",
            "valign": "vcenter",
        }
    )

    critical_rank = workbook.add_format(
        {
            "font_name": "Arial",
            "font_size": 10,
            "bold": True,
            "font_color": red,
            "bg_color": light_red,
            "border": 1,
            "border_color": border_color,
            "align": "left",
            "valign": "vcenter",
        }
    )

    high_rank = workbook.add_format(
        {
            "font_name": "Arial",
            "font_size": 10,
            "bold": True,
            "font_color": yellow,
            "bg_color": light_yellow,
            "border": 1,
            "border_color": border_color,
            "align": "left",
            "valign": "vcenter",
        }
    )

    one_price_rank = workbook.add_format(
        {
            "font_name": "Arial",
            "font_size": 10,
            "font_color": muted_color,
            "bg_color": "#F6F7F8",
            "border": 1,
            "border_color": border_color,
            "align": "left",
            "valign": "vcenter",
        }
    )

    positive_deviation = workbook.add_format(
        {
            "font_name": "Arial",
            "font_size": 10,
            "bold": True,
            "font_color": red,
            "bg_color": light_red,
            "border": 1,
            "border_color": border_color,
            "align": "right",
            "valign": "vcenter",
            "num_format": '0.00"%"',
        }
    )

    negative_deviation = workbook.add_format(
        {
            "font_name": "Arial",
            "font_size": 10,
            "bold": True,
            "font_color": blue,
            "bg_color": light_blue,
            "border": 1,
            "border_color": border_color,
            "align": "right",
            "valign": "vcenter",
            "num_format": '0.00"%"',
        }
    )

    title = workbook.add_format(
        {
            "font_name": "Arial",
            "font_size": 14,
            "bold": True,
            "font_color": text_color,
            "align": "left",
            "valign": "vcenter",
        }
    )

    subtitle = workbook.add_format(
        {
            "font_name": "Arial",
            "font_size": 9,
            "font_color": muted_color,
            "align": "left",
            "valign": "vcenter",
        }
    )

    return {
        "header": header,
        "text": text,
        "text_wrap": text_wrap,
        "center": center,
        "integer": integer,
        "money": money,
        "percent": percent,
        "date": date_format,
        "empty": empty,
        "critical_rank": critical_rank,
        "high_rank": high_rank,
        "one_price_rank": one_price_rank,
        "positive_deviation": positive_deviation,
        "negative_deviation": negative_deviation,
        "title": title,
        "subtitle": subtitle,
    }


# ---------------------------------------------------------------------
# Выбор формата ячейки
# ---------------------------------------------------------------------


def _get_rank_format(
    value: Any,
    formats: dict[str, Any],
):
    """
    Возвращает цветной формат ранга CV.
    """

    text = str(value or "")

    if text == "4. 75% и выше":
        return formats["critical_rank"]

    if text == "3. От 50% до 75%":
        return formats["high_rank"]

    if text == "0. Одна цена":
        return formats["one_price_rank"]

    return formats["text"]


def _get_percent_format(
    column: str,
    value: float | int | None,
    formats: dict[str, Any],
):
    """
    Для колонок отклонений применяет цветное выделение.
    """

    if value is None:
        return formats["percent"]

    is_deviation_column = (
        "отклонение" in column.lower()
        or column == "Δ медианы упр-бух, %"
    )

    if not is_deviation_column:
        return formats["percent"]

    if value >= 10:
        return formats["positive_deviation"]

    if value <= -10:
        return formats["negative_deviation"]

    return formats["percent"]


# ---------------------------------------------------------------------
# Запись листа Excel
# ---------------------------------------------------------------------


def _write_dataframe_sheet(
    *,
    writer: pd.ExcelWriter,
    sheet_name: str,
    df: pd.DataFrame,
    report_title: str,
    formats: dict[str, Any],
) -> None:
    """
    Записывает один DataFrame на отдельный Excel-лист.
    """

    workbook = writer.book
    worksheet = workbook.add_worksheet(
        sheet_name
    )

    writer.sheets[sheet_name] = worksheet

    column_count = max(
        len(df.columns),
        1,
    )

    last_column_index = max(
        column_count - 1,
        0,
    )

    worksheet.merge_range(
        0,
        0,
        0,
        last_column_index,
        report_title,
        formats["title"],
    )

    worksheet.merge_range(
        1,
        0,
        1,
        last_column_index,
        (
            "Дата формирования: "
            f"{datetime.now():%d.%m.%Y %H:%M}"
        ),
        formats["subtitle"],
    )

    header_row = 3
    data_start_row = header_row + 1

    if df.empty:
        worksheet.write(
            header_row,
            0,
            "Нет данных",
            formats["header"],
        )

        worksheet.write(
            data_start_row,
            0,
            (
                "По выбранным фильтрам данные "
                "для выгрузки отсутствуют."
            ),
            formats["empty"],
        )

        worksheet.set_column(
            0,
            0,
            40,
        )

        worksheet.set_row(
            0,
            24,
        )

        worksheet.set_row(
            header_row,
            30,
        )

        worksheet.hide_gridlines(2)

        return

    # Заголовки
    for column_index, column in enumerate(
        df.columns
    ):
        worksheet.write(
            header_row,
            column_index,
            column,
            formats["header"],
        )

    # Данные
    for row_offset, row in enumerate(
        df.itertuples(
            index=False,
            name=None,
        )
    ):
        excel_row = data_start_row + row_offset

        for column_index, value in enumerate(row):
            column = df.columns[column_index]

            if value is None:
                worksheet.write_blank(
                    excel_row,
                    column_index,
                    None,
                    formats["text"],
                )
                continue

            try:
                if pd.isna(value):
                    worksheet.write_blank(
                        excel_row,
                        column_index,
                        None,
                        formats["text"],
                    )
                    continue
            except (TypeError, ValueError):
                pass

            if column in DATE_COLUMNS:
                parsed_date = pd.to_datetime(
                    value,
                    errors="coerce",
                )

                if pd.isna(parsed_date):
                    worksheet.write_blank(
                        excel_row,
                        column_index,
                        None,
                        formats["date"],
                    )
                else:
                    worksheet.write_datetime(
                        excel_row,
                        column_index,
                        parsed_date.to_pydatetime(),
                        formats["date"],
                    )

                continue

            if column.startswith("Ранг CV"):
                worksheet.write(
                    excel_row,
                    column_index,
                    str(value),
                    _get_rank_format(
                        value,
                        formats,
                    ),
                )

                continue

            if column in PERCENT_COLUMNS:
                numeric_value = _safe_numeric_value(
                    value
                )

                if numeric_value is None:
                    worksheet.write_blank(
                        excel_row,
                        column_index,
                        None,
                        formats["percent"],
                    )
                else:
                    worksheet.write_number(
                        excel_row,
                        column_index,
                        float(numeric_value),
                        _get_percent_format(
                            column,
                            numeric_value,
                            formats,
                        ),
                    )

                continue

            if column in MONEY_COLUMNS:
                numeric_value = _safe_numeric_value(
                    value
                )

                if numeric_value is None:
                    worksheet.write_blank(
                        excel_row,
                        column_index,
                        None,
                        formats["money"],
                    )
                else:
                    worksheet.write_number(
                        excel_row,
                        column_index,
                        float(numeric_value),
                        formats["money"],
                    )

                continue

            if column in INTEGER_COLUMNS:
                if column == "nm_id":
                    worksheet.write(
                        excel_row,
                        column_index,
                        _normalise_nm_id(value) or "",
                        formats["center"],
                    )
                else:
                    numeric_value = _safe_numeric_value(
                        value
                    )

                    if numeric_value is None:
                        worksheet.write_blank(
                            excel_row,
                            column_index,
                            None,
                            formats["integer"],
                        )
                    else:
                        worksheet.write_number(
                            excel_row,
                            column_index,
                            float(numeric_value),
                            formats["integer"],
                        )

                continue

            if column in TEXT_WIDE_COLUMNS:
                worksheet.write(
                    excel_row,
                    column_index,
                    str(value),
                    formats["text_wrap"],
                )

                continue

            worksheet.write(
                excel_row,
                column_index,
                str(value),
                formats["text"],
            )

    last_data_row = (
        data_start_row
        + len(df)
        - 1
    )

    # Автофильтр
    worksheet.autofilter(
        header_row,
        0,
        last_data_row,
        len(df.columns) - 1,
    )

    # Закрепляем заголовок и первые две колонки.
    worksheet.freeze_panes(
        data_start_row,
        min(2, len(df.columns)),
    )

    # Высоты строк
    worksheet.set_row(
        0,
        25,
    )

    worksheet.set_row(
        1,
        18,
    )

    worksheet.set_row(
        header_row,
        38,
    )

    worksheet.set_default_row(
        19,
    )

    # Ширины колонок
    for column_index, column in enumerate(
        df.columns
    ):
        width = _get_column_width(
            column,
            df[column],
        )

        default_format = None

        if column in DATE_COLUMNS:
            default_format = formats["date"]

        elif column in MONEY_COLUMNS:
            default_format = formats["money"]

        elif column in PERCENT_COLUMNS:
            default_format = formats["percent"]

        elif (
            column in INTEGER_COLUMNS
            and column != "nm_id"
        ):
            default_format = formats["integer"]

        elif column in TEXT_WIDE_COLUMNS:
            default_format = formats["text_wrap"]

        elif column == "nm_id":
            default_format = formats["center"]

        else:
            default_format = formats["text"]

        worksheet.set_column(
            column_index,
            column_index,
            width,
            default_format,
        )

    worksheet.hide_gridlines(2)

    worksheet.set_landscape()
    worksheet.fit_to_pages(
        1,
        0,
    )

    worksheet.set_margins(
        left=0.25,
        right=0.25,
        top=0.5,
        bottom=0.5,
    )

    worksheet.repeat_rows(
        header_row,
        header_row,
    )

    worksheet.set_header(
        "&CКонтроль закупочных цен"
    )

    worksheet.set_footer(
        "&LСтраница &P из &N"
        "&RСформировано &D &T"
    )


# ---------------------------------------------------------------------
# Excel
# ---------------------------------------------------------------------


def build_excel_download(
    analysis_df: pd.DataFrame,
    history_df: pd.DataFrame,
):
    """
    Формирует Excel-файл для dcc.Download.

    Листы:
    - Анализ;
    - История цен.
    """

    prepared_analysis = _prepare_dataframe(
        analysis_df
    )

    prepared_history = _prepare_dataframe(
        history_df
    )

    filename = _build_filename(
        "xlsx"
    )

    def write_excel(
        buffer: BytesIO,
    ) -> None:
        with pd.ExcelWriter(
            buffer,
            engine="xlsxwriter",
            datetime_format="dd.mm.yyyy",
            date_format="dd.mm.yyyy",
        ) as writer:
            formats = _build_formats(
                writer.book
            )

            _write_dataframe_sheet(
                writer=writer,
                sheet_name=ANALYSIS_SHEET_NAME,
                df=prepared_analysis,
                report_title=(
                    "Контроль закупочных цен — "
                    "анализ по товарам"
                ),
                formats=formats,
            )

            _write_dataframe_sheet(
                writer=writer,
                sheet_name=HISTORY_SHEET_NAME,
                df=prepared_history,
                report_title=(
                    "Контроль закупочных цен — "
                    "история поступлений"
                ),
                formats=formats,
            )

            writer.book.set_properties(
                {
                    "title": (
                        "Контроль закупочных цен"
                    ),
                    "subject": (
                        "Анализ изменения "
                        "закупочной себестоимости"
                    ),
                    "author": "ТРЕНДСЕТТЕР",
                    "company": "ТРЕНДСЕТТЕР",
                    "comments": (
                        "Автоматически сформированный "
                        "отчёт"
                    ),
                    "created": datetime.now(),
                }
            )

    return dcc.send_bytes(
        write_excel,
        filename,
    )


# ---------------------------------------------------------------------
# CSV
# ---------------------------------------------------------------------


def build_csv_download(
    analysis_df: pd.DataFrame,
):
    """
    Формирует CSV-файл с основной таблицей анализа.

    Используется:
    - разделитель `;`;
    - кодировка UTF-8 with BOM;
    - даты в формате ДД.ММ.ГГГГ;
    - десятичный разделитель `,`.
    """

    prepared_analysis = _prepare_dataframe(
        analysis_df
    )

    csv_df = prepared_analysis.copy()

    for column in DATE_COLUMNS:
        if column in csv_df.columns:
            csv_df[column] = pd.to_datetime(
                csv_df[column],
                errors="coerce",
            ).dt.strftime(
                "%d.%m.%Y"
            )

    if "nm_id" in csv_df.columns:
        csv_df["nm_id"] = (
            csv_df["nm_id"]
            .apply(_normalise_nm_id)
            .fillna("")
        )

    filename = _build_filename(
        "csv"
    )

    return dcc.send_data_frame(
        csv_df.to_csv,
        filename,
        index=False,
        sep=";",
        encoding="utf-8-sig",
        decimal=",",
        na_rep="",
        lineterminator="\n",
    )

