# gear/app/costs_control/grid.py
from __future__ import annotations

from datetime import datetime
from typing import Any

import dash_ag_grid as dag
import dash_mantine_components as dmc
import pandas as pd
from dash import (
    Input,
    Output,
    State,
    dcc,
    html,
    no_update,
)
from dash_iconify import DashIconify

from .calculations import (
    filter_history_for_product,
    serialize_dataframe,
)
from .charts import (
    build_price_history_chart,
    empty_figure,
)
from .config import (
    COLORS,
    PAGE_SIZE,
)
from .data import get_price_history_data
from .filters import (
    filter_history_data,
    get_filtered_analysis_from_store,
    normalise_nm_id,
)
from .ids import (
    FILTERED_DATA_STORE_ID,
    HISTORY_GRID_DOWNLOAD_EXCEL_BTN_ID,
    HISTORY_GRID_DOWNLOAD_ID,
    HISTORY_GRID_ID,
    MAIN_GRID_DOWNLOAD_CSV_BTN_ID,
    MAIN_GRID_DOWNLOAD_EXCEL_BTN_ID,
    MAIN_GRID_DOWNLOAD_ID,
    MAIN_GRID_ID,
    PRICE_HISTORY_CHART_ID,
    SELECTED_PRODUCT_STORE_ID,
    ZERO_PRICE_PRODUCTS_FILTER_ID,
)


# ---------------------------------------------------------------------
# Форматирование значений
# ---------------------------------------------------------------------


RUBLE_FORMATTER = {
    "function": (
        "params.value == null "
        "? '' "
        ": new Intl.NumberFormat("
        "'ru-RU', "
        "{"
        "minimumFractionDigits: 2, "
        "maximumFractionDigits: 2"
        "}"
        ").format(params.value) + ' ₽'"
    )
}


PERCENT_FORMATTER = {
    "function": (
        "params.value == null "
        "? '' "
        ": new Intl.NumberFormat("
        "'ru-RU', "
        "{"
        "minimumFractionDigits: 2, "
        "maximumFractionDigits: 2"
        "}"
        ").format(params.value) + '%'"
    )
}


INTEGER_FORMATTER = {
    "function": (
        "params.value == null "
        "? '' "
        ": new Intl.NumberFormat("
        "'ru-RU'"
        ").format(params.value)"
    )
}


DATE_FORMATTER = {
    "function": (
        "params.value "
        "? new Date(params.value)"
        ".toLocaleDateString('ru-RU') "
        ": ''"
    )
}


# ---------------------------------------------------------------------
# Общие настройки колонок
# ---------------------------------------------------------------------


DEFAULT_COL_DEF = {
    "sortable": True,
    "filter": True,
    "resizable": True,
    "minWidth": 110,
    "wrapHeaderText": True,
    "autoHeaderHeight": True,
    "suppressHeaderMenuButton": True,
    "cellDataType": False,
}


# ---------------------------------------------------------------------
# Вспомогательные функции
# ---------------------------------------------------------------------


def _find_nm_id_column(
    df: pd.DataFrame,
) -> str | None:
    """
    Находит колонку с NM ID.
    """

    for column in (
        "nm_id",
        "NM ID",
        "nmId",
    ):
        if column in df.columns:
            return column

    return None


def _clean_number_series(
    series: pd.Series,
) -> pd.Series:
    """
    Приводит колонку к числовому типу.

    Поддерживает:

    - пробелы;
    - неразрывные пробелы;
    - запятые;
    - знак рубля;
    - знак процента.
    """

    if series.empty:
        return pd.Series(
            dtype="float64",
            index=series.index,
        )

    text = (
        series
        .astype(str)
        .str.replace(
            "\u00A0",
            "",
            regex=False,
        )
        .str.replace(
            " ",
            "",
            regex=False,
        )
        .str.replace(
            "₽",
            "",
            regex=False,
        )
        .str.replace(
            "%",
            "",
            regex=False,
        )
        .str.replace(
            ",",
            ".",
            regex=False,
        )
        .str.strip()
    )

    return pd.to_numeric(
        text,
        errors="coerce",
    )


def get_zero_price_product_ids(
    history_df: pd.DataFrame,
) -> set[str]:
    """
    Возвращает NM ID товаров, у которых
    хотя бы в одной строке УПД указана
    нулевая цена.

    Проверяются:

    - Цена, бух;
    - Цена, упр.
    """

    if history_df.empty:
        return set()

    nm_column = _find_nm_id_column(
        history_df
    )

    if not nm_column:
        return set()

    zero_mask = pd.Series(
        False,
        index=history_df.index,
        dtype=bool,
    )

    found_price_column = False

    for price_column in (
        "Цена, бух",
        "Цена, упр",
    ):
        if (
            price_column
            not in history_df.columns
        ):
            continue

        found_price_column = True

        numeric_price = (
            _clean_number_series(
                history_df[
                    price_column
                ]
            )
        )

        zero_mask |= numeric_price.eq(0)

    if not found_price_column:
        return set()

    zero_price_ids = (
        history_df.loc[
            zero_mask,
            nm_column,
        ]
        .dropna()
        .tolist()
    )

    return {
        normalise_nm_id(value)
        for value in zero_price_ids
        if normalise_nm_id(value)
    }


def filter_products_with_zero_price(
    products_df: pd.DataFrame,
    history_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Оставляет только товары,
    у которых в истории выбранного периода
    есть хотя бы одна нулевая цена.
    """

    if products_df.empty:
        return products_df.copy()

    zero_price_nm_ids = (
        get_zero_price_product_ids(
            history_df
        )
    )

    if not zero_price_nm_ids:
        return (
            products_df
            .iloc[0:0]
            .copy()
        )

    nm_column = _find_nm_id_column(
        products_df
    )

    if not nm_column:
        return (
            products_df
            .iloc[0:0]
            .copy()
        )

    product_nm_ids = (
        products_df[nm_column]
        .astype(str)
        .map(normalise_nm_id)
    )

    return (
        products_df.loc[
            product_nm_ids.isin(
                zero_price_nm_ids
            )
        ]
        .copy()
        .reset_index(drop=True)
    )


def _get_product_history(
    selected_product: dict | None,
    filter_store: dict | None,
) -> tuple[str, pd.DataFrame]:
    """
    Получает историю выбранного товара.

    Учитывает:

    - NM ID;
    - выбранных поставщиков;
    - выбранный период УПД.
    """

    if not selected_product:
        return "", pd.DataFrame()

    nm_id = normalise_nm_id(
        selected_product.get(
            "nm_id"
        )
    )

    if not nm_id:
        return "", pd.DataFrame()

    history_df = (
        get_price_history_data()
        .copy()
    )

    if history_df.empty:
        return nm_id, pd.DataFrame()

    product_history = (
        filter_history_for_product(
            history_df,
            nm_id,
        )
    )

    product_history = filter_history_data(
        product_history,
        nm_ids=[nm_id],
        suppliers=(
            (filter_store or {}).get(
                "suppliers",
                [],
            )
        ),
        date_range=(
            (filter_store or {}).get(
                "date_range"
            )
        ),
    )

    return (
        nm_id,
        product_history,
    )


# ---------------------------------------------------------------------
# Серверная обработка фильтров AG Grid
# ---------------------------------------------------------------------


def _apply_text_condition(
    series: pd.Series,
    condition: dict,
) -> pd.Series:
    """
    Применяет текстовый фильтр AG Grid.
    """

    filter_type = condition.get(
        "type",
        "contains",
    )

    filter_value = str(
        condition.get(
            "filter",
            "",
        )
    )

    text_series = (
        series
        .fillna("")
        .astype(str)
    )

    normalized_series = (
        text_series.str.casefold()
    )

    normalized_filter = (
        filter_value.casefold()
    )

    if filter_type == "equals":
        return (
            normalized_series
            == normalized_filter
        )

    if filter_type == "notEqual":
        return (
            normalized_series
            != normalized_filter
        )

    if filter_type == "startsWith":
        return (
            normalized_series
            .str.startswith(
                normalized_filter,
                na=False,
            )
        )

    if filter_type == "endsWith":
        return (
            normalized_series
            .str.endswith(
                normalized_filter,
                na=False,
            )
        )

    if filter_type == "notContains":
        return (
            ~normalized_series
            .str.contains(
                normalized_filter,
                regex=False,
                na=False,
            )
        )

    if filter_type == "blank":
        return (
            text_series
            .str.strip()
            .eq("")
        )

    if filter_type == "notBlank":
        return (
            text_series
            .str.strip()
            .ne("")
        )

    return (
        normalized_series
        .str.contains(
            normalized_filter,
            regex=False,
            na=False,
        )
    )


def _apply_number_condition(
    series: pd.Series,
    condition: dict,
) -> pd.Series:
    """
    Применяет числовой фильтр AG Grid.
    """

    filter_type = condition.get(
        "type",
        "equals",
    )

    numeric_series = (
        _clean_number_series(
            series
        )
    )

    filter_value = pd.to_numeric(
        condition.get(
            "filter"
        ),
        errors="coerce",
    )

    filter_to = pd.to_numeric(
        condition.get(
            "filterTo"
        ),
        errors="coerce",
    )

    if filter_type == "blank":
        return numeric_series.isna()

    if filter_type == "notBlank":
        return numeric_series.notna()

    if pd.isna(filter_value):
        return pd.Series(
            True,
            index=series.index,
        )

    if filter_type == "notEqual":
        return numeric_series.ne(
            filter_value
        )

    if filter_type == "lessThan":
        return numeric_series.lt(
            filter_value
        )

    if filter_type == "lessThanOrEqual":
        return numeric_series.le(
            filter_value
        )

    if filter_type == "greaterThan":
        return numeric_series.gt(
            filter_value
        )

    if (
        filter_type
        == "greaterThanOrEqual"
    ):
        return numeric_series.ge(
            filter_value
        )

    if (
        filter_type == "inRange"
        and pd.notna(filter_to)
    ):
        return (
            numeric_series.ge(
                filter_value
            )
            & numeric_series.le(
                filter_to
            )
        )

    return numeric_series.eq(
        filter_value
    )


def _apply_date_condition(
    series: pd.Series,
    condition: dict,
) -> pd.Series:
    """
    Применяет фильтр даты AG Grid.
    """

    filter_type = condition.get(
        "type",
        "equals",
    )

    date_series = (
        pd.to_datetime(
            series,
            errors="coerce",
        )
        .dt.normalize()
    )

    filter_date = pd.to_datetime(
        condition.get(
            "dateFrom"
        ),
        errors="coerce",
    )

    filter_to = pd.to_datetime(
        condition.get(
            "dateTo"
        ),
        errors="coerce",
    )

    if filter_type == "blank":
        return date_series.isna()

    if filter_type == "notBlank":
        return date_series.notna()

    if pd.isna(filter_date):
        return pd.Series(
            True,
            index=series.index,
        )

    filter_date = (
        filter_date.normalize()
    )

    if filter_type == "notEqual":
        return date_series.ne(
            filter_date
        )

    if filter_type == "lessThan":
        return date_series.lt(
            filter_date
        )

    if filter_type == "greaterThan":
        return date_series.gt(
            filter_date
        )

    if (
        filter_type == "inRange"
        and pd.notna(filter_to)
    ):
        filter_to = (
            filter_to.normalize()
        )

        return (
            date_series.ge(
                filter_date
            )
            & date_series.le(
                filter_to
            )
        )

    return date_series.eq(
        filter_date
    )


def _apply_single_filter_condition(
    series: pd.Series,
    condition: dict,
) -> pd.Series:
    """
    Определяет тип фильтра
    и применяет условие.
    """

    filter_type = condition.get(
        "filterType",
        "text",
    )

    if filter_type == "number":
        return _apply_number_condition(
            series,
            condition,
        )

    if filter_type == "date":
        return _apply_date_condition(
            series,
            condition,
        )

    return _apply_text_condition(
        series,
        condition,
    )


def _apply_column_filter(
    series: pd.Series,
    model: dict,
) -> pd.Series:
    """
    Применяет фильтр одной колонки.

    Поддерживает составные условия AND/OR.
    """

    conditions = model.get(
        "conditions"
    )

    if conditions:
        masks = [
            _apply_single_filter_condition(
                series,
                condition,
            )
            for condition in conditions
        ]

        if not masks:
            return pd.Series(
                True,
                index=series.index,
            )

        operator = model.get(
            "operator",
            "AND",
        )

        result_mask = masks[0]

        for mask in masks[1:]:
            if operator == "OR":
                result_mask |= mask
            else:
                result_mask &= mask

        return result_mask

    condition_one = model.get(
        "condition1"
    )

    condition_two = model.get(
        "condition2"
    )

    if condition_one:
        first_mask = (
            _apply_single_filter_condition(
                series,
                condition_one,
            )
        )

        if not condition_two:
            return first_mask

        second_mask = (
            _apply_single_filter_condition(
                series,
                condition_two,
            )
        )

        if model.get(
            "operator"
        ) == "OR":
            return (
                first_mask
                | second_mask
            )

        return (
            first_mask
            & second_mask
        )

    return _apply_single_filter_condition(
        series,
        model,
    )


def apply_ag_grid_filter_model(
    df: pd.DataFrame,
    filter_model: dict | None,
) -> pd.DataFrame:
    """
    Применяет встроенные фильтры AG Grid
    повторно на сервере.
    """

    if (
        df.empty
        or not filter_model
    ):
        return df.copy()

    result = df.copy()

    total_mask = pd.Series(
        True,
        index=result.index,
        dtype=bool,
    )

    for (
        column,
        model,
    ) in filter_model.items():
        if column not in result.columns:
            continue

        if not isinstance(
            model,
            dict,
        ):
            continue

        column_mask = (
            _apply_column_filter(
                result[column],
                model,
            )
        )

        total_mask &= (
            column_mask.fillna(False)
        )

    return (
        result.loc[
            total_mask
        ]
        .copy()
        .reset_index(drop=True)
    )


def apply_ag_grid_sort_model(
    df: pd.DataFrame,
    sort_model: list | None,
) -> pd.DataFrame:
    """
    Применяет сортировку AG Grid
    повторно на сервере.
    """

    if (
        df.empty
        or not sort_model
    ):
        return df.copy()

    columns: list[str] = []
    ascending: list[bool] = []

    for item in sort_model:
        if not isinstance(
            item,
            dict,
        ):
            continue

        column = item.get(
            "colId"
        )

        if (
            not column
            or column not in df.columns
        ):
            continue

        columns.append(
            column
        )

        ascending.append(
            item.get(
                "sort"
            ) != "desc"
        )

    if not columns:
        return df.copy()

    try:
        return (
            df.sort_values(
                by=columns,
                ascending=ascending,
                kind="stable",
                na_position="last",
            )
            .reset_index(drop=True)
        )

    except (
        TypeError,
        ValueError,
    ):
        return (
            df.reset_index(
                drop=True
            )
        )


# ---------------------------------------------------------------------
# Получение основной таблицы
# ---------------------------------------------------------------------


def get_main_grid_dataframe(
    filter_store: dict | None,
    *,
    only_zero_price_products: bool = False,
    filter_model: dict | None = None,
    sort_model: list | None = None,
) -> pd.DataFrame:
    """
    Полностью формирует основную
    таблицу товаров на сервере.
    """

    if not filter_store:
        return pd.DataFrame()

    products_df = (
        get_filtered_analysis_from_store(
            filter_store
        )
    )

    if products_df.empty:
        return products_df

    if only_zero_price_products:
        history_df = (
            get_price_history_data()
            .copy()
        )

        history_df = filter_history_data(
            history_df,
            date_range=filter_store.get(
                "date_range"
            ),
        )

        products_df = (
            filter_products_with_zero_price(
                products_df,
                history_df,
            )
        )

    products_df = (
        apply_ag_grid_filter_model(
            products_df,
            filter_model,
        )
    )

    products_df = (
        apply_ag_grid_sort_model(
            products_df,
            sort_model,
        )
    )

    return (
        products_df
        .reset_index(drop=True)
    )


# ---------------------------------------------------------------------
# Подсветка
# ---------------------------------------------------------------------


def _rank_cell_style():
    return {
        "styleConditions": [
            {
                "condition": (
                    "params.value === "
                    "'4. 75% и выше'"
                ),
                "style": {
                    "backgroundColor": (
                        "#FDECEC"
                    ),
                    "color": "#A33A3A",
                    "fontWeight": "600",
                },
            },
            {
                "condition": (
                    "params.value === "
                    "'3. От 50% до 75%'"
                ),
                "style": {
                    "backgroundColor": (
                        "#FFF6D8"
                    ),
                    "color": "#9A6700",
                    "fontWeight": "600",
                },
            },
            {
                "condition": (
                    "params.value === "
                    "'0. Одна цена'"
                ),
                "style": {
                    "backgroundColor": (
                        "#F6F7F8"
                    ),
                    "color": "#6B7280",
                },
            },
        ],
    }


def _percent_delta_style():
    return {
        "styleConditions": [
            {
                "condition": (
                    "params.value >= 10"
                ),
                "style": {
                    "backgroundColor": (
                        "#FDECEC"
                    ),
                    "color": "#A33A3A",
                    "fontWeight": "600",
                },
            },
            {
                "condition": (
                    "params.value <= -10"
                ),
                "style": {
                    "backgroundColor": (
                        "#EDF4FA"
                    ),
                    "color": "#3B6B8F",
                    "fontWeight": "600",
                },
            },
        ],
    }


def _zero_price_cell_style():
    """
    Подсвечивает нулевую цену
    в истории УПД.
    """

    return {
        "styleConditions": [
            {
                "condition": (
                    "params.value !== null "
                    "&& params.value !== undefined "
                    "&& Number(params.value) === 0"
                ),
                "style": {
                    "backgroundColor": (
                        "#FDECEC"
                    ),
                    "color": "#A33A3A",
                    "fontWeight": "700",
                },
            },
        ],
    }


# ---------------------------------------------------------------------
# Колонки основной таблицы
# ---------------------------------------------------------------------


MAIN_COLUMN_DEFS = [
    {
        "headerName": "Товар",
        "children": [
            {
                "headerName": "NM ID",
                "field": "nm_id",
                "pinned": "left",
                "width": 100,
                "minWidth": 100,
                "cellStyle": {
                "backgroundColor": COLORS["very_light_green"],
                "fontWeight": 600,},
            },
            {
                "headerName": (
                    "Наименование"
                ),
                "field": "Наименование",
                "pinned": "left",
                "width": 380,
                "minWidth": 360,
                "tooltipField": (
                    "Наименование"
                ),
                "cellStyle": {
                "backgroundColor": COLORS["very_light_green"],
                "fontWeight": 600,},
            },
            {
                "headerName": "Бренд",
                "field": "Бренд",
                "width": 170,
            },
            {
                "headerName": "Категория",
                "field": "Категория",
                "width": 190,
            },
            {
                "headerName": (
                    "Поставщики"
                ),
                "field": "Поставщики",
                "width": 260,
                "tooltipField": (
                    "Поставщики"
                ),
            },
        ],
    },
    {
        "headerName": "Поступления",
        "children": [
            {
                "headerName": (
                    "Первая дата"
                ),
                "field": (
                    "Первая дата УПД"
                ),
                "width": 140,
                "valueFormatter": (
                    DATE_FORMATTER
                ),
                "filter": (
                    "agDateColumnFilter"
                ),
            },
            {
                "headerName": (
                    "Последняя дата"
                ),
                "field": (
                    "Последняя дата УПД"
                ),
                "width": 140,
                "valueFormatter": (
                    DATE_FORMATTER
                ),
                "filter": (
                    "agDateColumnFilter"
                ),
            },
            {
                "headerName": "УПД",
                "field": "Кол-во УПД",
                "width": 105,
                "type": "numericColumn",
                "filter": (
                    "agNumberColumnFilter"
                ),
                "valueFormatter": (
                    INTEGER_FORMATTER
                ),
            },
            {
                "headerName": (
                    "Количество"
                ),
                "field": "Кол-во, шт",
                "width": 125,
                "type": "numericColumn",
                "filter": (
                    "agNumberColumnFilter"
                ),
                "valueFormatter": (
                    INTEGER_FORMATTER
                ),
            },
        ],
    },
    {
        "headerName": (
            "Бухгалтерская себестоимость"
        ),
        "children": [
            {
                "headerName": "Ранг CV",
                "field": "Ранг CV, бух",
                "width": 170,
                "cellStyle": (
                    _rank_cell_style()
                ),
            },
            {
                "headerName": "CV",
                "field": (
                    "Коэффициент "
                    "вариации, %, бух"
                ),
                "width": 120,
                "type": "numericColumn",
                "filter": (
                    "agNumberColumnFilter"
                ),
                "valueFormatter": (
                    PERCENT_FORMATTER
                ),
            },
            {
                "headerName": "Медиана",
                "field": (
                    "Медиана цены, бух"
                ),
                "width": 130,
                "type": "numericColumn",
                "filter": (
                    "agNumberColumnFilter"
                ),
                "valueFormatter": (
                    RUBLE_FORMATTER
                ),
            },
            {
                "headerName": "Средняя",
                "field": (
                    "Средняя цена, бух"
                ),
                "width": 130,
                "type": "numericColumn",
                "filter": (
                    "agNumberColumnFilter"
                ),
                "valueFormatter": (
                    RUBLE_FORMATTER
                ),
            },
            {
                "headerName": "Мин.",
                "field": (
                    'min_acc_price'
                ),
                "width": 120,
                "type": "numericColumn",
                "filter": (
                    "agNumberColumnFilter"
                ),
                "valueFormatter": (
                    RUBLE_FORMATTER
                ),
            },
            {
                "headerName": "Макс.",
                "field": (
                    'max_acc_price'
                ),
                "width": 120,
                "type": "numericColumn",
                "filter": (
                    "agNumberColumnFilter"
                ),
                "valueFormatter": (
                    RUBLE_FORMATTER
                ),
            },
            {
                "headerName": (
                    "Диапазон"
                ),
                "field": (
                    "Диапазон цены, бух"
                ),
                "width": 130,
                "type": "numericColumn",
                "filter": (
                    "agNumberColumnFilter"
                ),
                "valueFormatter": (
                    RUBLE_FORMATTER
                ),
            },
            # {
            #     "headerName": (
            #         "Макс. отклонение"
            #     ),
            #     "field": (
            #         "Макс. отклонение "
            #         "от медианы, %, бух"
            #     ),
            #     "width": 165,
            #     "type": "numericColumn",
            #     "filter": (
            #         "agNumberColumnFilter"
            #     ),
            #     "valueFormatter": (
            #         PERCENT_FORMATTER
            #     ),
            #     "cellStyle": (
            #         _percent_delta_style()
            #     ),
            # },
            # {
            #     "headerName": (
            #         "Мин. отклонение"
            #     ),
            #     "field": (
            #         "Мин. отклонение "
            #         "от медианы, %, бух"
            #     ),
            #     "width": 165,
            #     "type": "numericColumn",
            #     "filter": (
            #         "agNumberColumnFilter"
            #     ),
            #     "valueFormatter": (
            #         PERCENT_FORMATTER
            #     ),
            #     "cellStyle": (
            #         _percent_delta_style()
            #     ),
            # },
        ],
    },
    {
        "headerName": (
            "Управленческая себестоимость"
        ),
        "children": [
            {
                "headerName": "Ранг CV",
                "field": "Ранг CV, упр",
                "width": 170,
                "cellStyle": (
                    _rank_cell_style()
                ),
            },
            {
                "headerName": "CV",
                "field": (
                    "Коэффициент "
                    "вариации, %, упр"
                ),
                "width": 120,
                "type": "numericColumn",
                "filter": (
                    "agNumberColumnFilter"
                ),
                "valueFormatter": (
                    PERCENT_FORMATTER
                ),
            },
            {
                "headerName": "Медиана",
                "field": (
                    "Медиана цены, упр"
                ),
                "width": 130,
                "type": "numericColumn",
                "filter": (
                    "agNumberColumnFilter"
                ),
                "valueFormatter": (
                    RUBLE_FORMATTER
                ),
            },
            {
                "headerName": "Средняя",
                "field": (
                    "Средняя цена, упр"
                ),
                "width": 130,
                "type": "numericColumn",
                "filter": (
                    "agNumberColumnFilter"
                ),
                "valueFormatter": (
                    RUBLE_FORMATTER
                ),
            },
            {
                "headerName": "Мин.",
                "field": (
                    'min_man_price'
                ),
                "width": 120,
                "type": "numericColumn",
                "filter": (
                    "agNumberColumnFilter"
                ),
                "valueFormatter": (
                    RUBLE_FORMATTER
                ),
            },
            {
                "headerName": "Макс.",
                "field": (
                    'max_man_price'
                ),
                "width": 120,
                "type": "numericColumn",
                "filter": (
                    "agNumberColumnFilter"
                ),
                "valueFormatter": (
                    RUBLE_FORMATTER
                ),
            },
            {
                "headerName": (
                    "Диапазон"
                ),
                "field": (
                    "Диапазон цены, упр"
                ),
                "width": 130,
                "type": "numericColumn",
                "filter": (
                    "agNumberColumnFilter"
                ),
                "valueFormatter": (
                    RUBLE_FORMATTER
                ),
            },
        ],
    },
    # {
    #     "headerName": "Сравнение",
    #     "children": [
    #         {
    #             "headerName": (
    #                 "Δ медианы, ₽"
    #             ),
    #             "field": (
    #                 "Δ медианы "
    #                 "упр-бух, руб."
    #             ),
    #             "width": 150,
    #             "type": "numericColumn",
    #             "filter": (
    #                 "agNumberColumnFilter"
    #             ),
    #             "valueFormatter": (
    #                 RUBLE_FORMATTER
    #             ),
    #         },
    #         {
    #             "headerName": (
    #                 "Δ медианы, %"
    #             ),
    #             "field": (
    #                 "Δ медианы "
    #                 "упр-бух, %"
    #             ),
    #             "width": 150,
    #             "type": "numericColumn",
    #             "filter": (
    #                 "agNumberColumnFilter"
    #             ),
    #             "valueFormatter": (
    #                 PERCENT_FORMATTER
    #             ),
    #             "cellStyle": (
    #                 _percent_delta_style()
    #             ),
    #         },
    #     ],
    # },
]


# ---------------------------------------------------------------------
# Колонки истории УПД
# ---------------------------------------------------------------------


HISTORY_COLUMN_DEFS = [
    {
        "headerName": "NM ID",
        "field": "nm_id",
        "pinned": "left",
        "width": 130,
       
    },
    {
        "headerName": "Наименование",
        "field": "Наименование",
        "pinned": "left",
        "width": 280,
        "tooltipField": "Наименование",
    },
    {
        "headerName": "Дата УПД",
        "field": "Дата УПД",
        "width": 140,
        "valueFormatter": (
            DATE_FORMATTER
        ),
        "filter": "agDateColumnFilter",
    },
    {
        "headerName": "Номер УПД",
        "field": "Номер УПД",
        "width": 175,
    },
    {
        "headerName": "Поставщик",
        "field": "Поставщик",
        "width": 250,
        "tooltipField": "Поставщик",
    },
    {
        "headerName": "Цена, бух",
        "field": "Цена, бух",
        "width": 145,
        "type": "numericColumn",
        "filter": "agNumberColumnFilter",
        "valueFormatter": (
            RUBLE_FORMATTER
        ),
        "cellStyle": (
            _zero_price_cell_style()
        ),
    },
    {
        "headerName": "Цена, упр",
        "field": "Цена, упр",
        "width": 145,
        "type": "numericColumn",
        "filter": "agNumberColumnFilter",
        "valueFormatter": (
            RUBLE_FORMATTER
        ),
        "cellStyle": (
            _zero_price_cell_style()
        ),
    },
    {
        "headerName": "Количество",
        "field": "Количество, шт",
        "width": 135,
        "type": "numericColumn",
        "filter": "agNumberColumnFilter",
        "valueFormatter": (
            INTEGER_FORMATTER
        ),
    },
]


# ---------------------------------------------------------------------
# Toolbar
# ---------------------------------------------------------------------


def _toolbar_button(
    *,
    component_id: str,
    label: str,
    icon: str,
):
    return dmc.Button(
        id=component_id,
        children=label,
        leftSection=DashIconify(
            icon=icon,
            width=15,
            height=15,
        ),
        variant="default",
        radius=0,
        size="xs",
        styles={
            "root": {
                "height": "32px",
                "fontSize": "11px",
                "fontWeight": 600,
                "borderColor": (
                    COLORS.get(
                        "border",
                        "#D9DEE2",
                    )
                ),
                "backgroundColor": (
                    "#FFFFFF"
                ),
            },
        },
    )


# ---------------------------------------------------------------------
# Стиль AG Grid
# ---------------------------------------------------------------------


def _grid_style(
    *,
    height: str,
) -> dict:
    return {
        "height": height,
        "width": "100%",

        "--ag-font-family": (
            "Inter, Arial, sans-serif"
        ),
        "--ag-font-size": "12px",

        "--ag-header-background-color": (
            COLORS["dark_green"]
        ),
        "--ag-header-foreground-color": (
            COLORS["white"]
        ),

        "--ag-border-color": (
            COLORS["border"]
        ),
        "--ag-row-border-color": (
            COLORS["border"]
        ),

        "--ag-selected-row-background-color": (
            COLORS["light_green"]
        ),
        "--ag-odd-row-background-color": (
            COLORS["light_gray"]
        ),

        "--ag-wrapper-border-radius": "0px",

        "--ag-input-text-color": "#111827",
        "--ag-input-background-color": (
            "#FFFFFF"
        ),
        "--ag-input-border-color": (
            "#CBD3D9"
        ),
        "--ag-input-focus-border-color": (
            COLORS.get(
                "green",
                "#2F6656",
            )
        ),
        "--ag-input-placeholder-text-color": (
            "#8B949E"
        ),

        "--ag-icon-color": "#334155",
        "--ag-foreground-color": "#1F2937",
        "--ag-background-color": "#FFFFFF",
    }


# ---------------------------------------------------------------------
# Основная таблица
# ---------------------------------------------------------------------


def build_main_grid():
    return dag.AgGrid(
        id=MAIN_GRID_ID,
        rowData=[],
        columnDefs=MAIN_COLUMN_DEFS,
        defaultColDef=DEFAULT_COL_DEF,
        dashGridOptions={
            "pagination": True,
            "paginationPageSize": (
                PAGE_SIZE
            ),
            "paginationPageSizeSelector": [
                25,
                50,
                100,
                250,
            ],

            "rowSelection": {
                "mode": "singleRow",
                "checkboxes": True,
                "headerCheckbox": False,

            },

            "selectionColumnDef": {
                "pinned": "left",
                "width": 48,
                "minWidth": 48,
                "maxWidth": 48,
                "resizable": False,
                "sortable": False,
                "suppressMovable": True,
            },

            "animateRows": False,
            "enableCellTextSelection": True,
            "ensureDomOrder": True,
            "tooltipShowDelay": 250,
            "rowHeight": 38,
            "headerHeight": 44,
            "groupHeaderHeight": 34,
            "suppressCellFocus": False,
        },
        className="ag-theme-quartz",
        style=_grid_style(
            height="680px",
        ),
    )


def build_main_grid_section():
    """
    Основная таблица товаров.
    """

    return html.Div(
        children=[
            dmc.Group(
                justify="space-between",
                align="center",
                gap="sm",
                mb=8,
                children=[
                    dmc.Checkbox(
                        id=(
                            ZERO_PRICE_PRODUCTS_FILTER_ID
                        ),
                        label=(
                            "Только товары "
                            "с нулевой ценой в УПД"
                        ),
                        checked=False,
                        size="xs",
                        radius=0,
                        color="red",
                        styles={
                            "label": {
                                "fontSize": "11px",
                                "fontWeight": 600,
                                "color": "#374151",
                            },
                        },
                    ),

                    dmc.Group(
                        gap="xs",
                        children=[
                            _toolbar_button(
                                component_id=(
                                    MAIN_GRID_DOWNLOAD_EXCEL_BTN_ID
                                ),
                                label="Скачать Excel",
                                icon=(
                                    "solar:"
                                    "document-add-linear"
                                ),
                            ),
                        ],
                    ),
                ],
            ),

            build_main_grid(),

            dcc.Download(
                id=MAIN_GRID_DOWNLOAD_ID
            ),
        ],
    )


# ---------------------------------------------------------------------
# История УПД
# ---------------------------------------------------------------------


def build_history_grid():
    return dag.AgGrid(
        id=HISTORY_GRID_ID,
        rowData=[],
        columnDefs=HISTORY_COLUMN_DEFS,
        defaultColDef=DEFAULT_COL_DEF,
        dashGridOptions={
            "pagination": True,
            "paginationPageSize": 50,
            "paginationPageSizeSelector": [
                25,
                50,
                100,
                250,
            ],
            "animateRows": False,
            "enableCellTextSelection": True,
            "ensureDomOrder": True,
            "tooltipShowDelay": 250,
            "rowHeight": 38,
            "headerHeight": 44,
        },
        className="ag-theme-quartz",
        style=_grid_style(
            height="520px",
        ),
    )


def build_history_grid_section():
    """
    История УПД выбранного товара.
    """

    return html.Div(
        children=[
            dmc.Group(
                justify="flex-end",
                align="center",
                gap="xs",
                mb=8,
                children=[
                    _toolbar_button(
                        component_id=(
                            HISTORY_GRID_DOWNLOAD_EXCEL_BTN_ID
                        ),
                        label=(
                            "Скачать историю"
                        ),
                        icon=(
                            "solar:"
                            "document-add-linear"
                        ),
                    ),
                ],
            ),

            build_history_grid(),

            dcc.Download(
                id=(
                    HISTORY_GRID_DOWNLOAD_ID
                )
            ),
        ],
    )


# ---------------------------------------------------------------------
# Экспорт
# ---------------------------------------------------------------------


def _prepare_export_dataframe(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Подготавливает данные для экспорта.
    """

    if df.empty:
        return df.copy()

    result = df.copy()

    technical_columns = [
        column
        for column in result.columns
        if str(column).startswith("__")
    ]

    if technical_columns:
        result = result.drop(
            columns=technical_columns,
            errors="ignore",
        )

    return result


# ---------------------------------------------------------------------
# Регистрация callbacks
# ---------------------------------------------------------------------


def register_grid_callbacks(
    app,
):
    """
    Регистрирует callbacks таблиц.
    """

    # -----------------------------------------------------------------
    # Основная таблица
    # -----------------------------------------------------------------

    @app.callback(
        Output(
            MAIN_GRID_ID,
            "rowData",
        ),
        Input(
            FILTERED_DATA_STORE_ID,
            "data",
        ),
        Input(
            ZERO_PRICE_PRODUCTS_FILTER_ID,
            "checked",
        ),
    )
    def update_main_grid_rows(
        filter_store,
        only_zero_price_products,
    ):
        """
        Формирует список товаров
        на сервере.
        """

        products_df = (
            get_main_grid_dataframe(
                filter_store,
                only_zero_price_products=bool(
                    only_zero_price_products
                ),
            )
        )

        if products_df.empty:
            return []

        return serialize_dataframe(
            products_df
        )

    # -----------------------------------------------------------------
    # Выбор товара
    # -----------------------------------------------------------------

    @app.callback(
        Output(
            SELECTED_PRODUCT_STORE_ID,
            "data",
        ),
        Input(
            MAIN_GRID_ID,
            "selectedRows",
        ),
        prevent_initial_call=True,
    )
    def select_product(
        selected_rows,
    ):
        """
        Сохраняет выбранный товар.
        """

        if not selected_rows:
            return None

        selected_row = (
            selected_rows[0]
        )

        return {
            "nm_id": normalise_nm_id(
                selected_row.get(
                    "nm_id"
                )
            ),
            "name": selected_row.get(
                "Наименование"
            ),
        }

    # -----------------------------------------------------------------
    # История выбранного товара
    # -----------------------------------------------------------------

    @app.callback(
        Output(
            PRICE_HISTORY_CHART_ID,
            "figure",
        ),
        Output(
            HISTORY_GRID_ID,
            "rowData",
        ),
        Input(
            SELECTED_PRODUCT_STORE_ID,
            "data",
        ),
        Input(
            FILTERED_DATA_STORE_ID,
            "data",
        ),
    )
    def update_product_history(
        selected_product,
        filter_store,
    ):
        """
        Загружает историю
        выбранного товара.
        """

        if not selected_product:
            return (
                empty_figure(
                    "Выберите товар "
                    "в таблице «Товары»"
                ),
                [],
            )

        nm_id, product_history = (
            _get_product_history(
                selected_product,
                filter_store,
            )
        )

        if not nm_id:
            return (
                empty_figure(
                    "Не удалось определить "
                    "NM ID товара"
                ),
                [],
            )

        if product_history.empty:
            return (
                empty_figure(
                    "По выбранному товару "
                    "история отсутствует"
                ),
                [],
            )

        return (
            build_price_history_chart(
                product_history,
                nm_id,
            ),
            serialize_dataframe(
                product_history
            ),
        )

    # -----------------------------------------------------------------
    # Excel основной таблицы
    # -----------------------------------------------------------------

    @app.callback(
        Output(
            MAIN_GRID_DOWNLOAD_ID,
            "data",
        ),
        Input(
            MAIN_GRID_DOWNLOAD_EXCEL_BTN_ID,
            "n_clicks",
        ),
        State(
            FILTERED_DATA_STORE_ID,
            "data",
        ),
        State(
            ZERO_PRICE_PRODUCTS_FILTER_ID,
            "checked",
        ),
        State(
            MAIN_GRID_ID,
            "filterModel",
        ),
        State(
            MAIN_GRID_ID,
            "sortModel",
        ),
        prevent_initial_call=True,
    )
    def download_main_grid_excel(
        n_clicks,
        filter_store,
        only_zero_price_products,
        filter_model,
        sort_model,
    ):
        """
        Скачивает Excel с учётом:

        - фильтров панели;
        - фильтра нулевой цены;
        - фильтров AG Grid;
        - сортировки AG Grid.
        """

        if not n_clicks:
            return no_update

        df = get_main_grid_dataframe(
            filter_store,
            only_zero_price_products=bool(
                only_zero_price_products
            ),
            filter_model=filter_model,
            sort_model=sort_model,
        )

        df = _prepare_export_dataframe(
            df
        )

        if df.empty:
            return no_update

        filename = (
            "cost_analysis_filtered_"
            f"{datetime.now():%Y-%m-%d_%H-%M}.xlsx"
        )

        return dcc.send_data_frame(
            df.to_excel,
            filename,
            index=False,
            sheet_name="Товары",
        )

    # -----------------------------------------------------------------
    # CSV основной таблицы
    # -----------------------------------------------------------------

    @app.callback(
        Output(
            MAIN_GRID_DOWNLOAD_ID,
            "data",
            allow_duplicate=True,
        ),
        Input(
            MAIN_GRID_DOWNLOAD_CSV_BTN_ID,
            "n_clicks",
        ),
        State(
            FILTERED_DATA_STORE_ID,
            "data",
        ),
        State(
            ZERO_PRICE_PRODUCTS_FILTER_ID,
            "checked",
        ),
        State(
            MAIN_GRID_ID,
            "filterModel",
        ),
        State(
            MAIN_GRID_ID,
            "sortModel",
        ),
        prevent_initial_call=True,
    )
    def download_main_grid_csv(
        n_clicks,
        filter_store,
        only_zero_price_products,
        filter_model,
        sort_model,
    ):
        """
        Скачивает CSV
        с учётом текущих фильтров.
        """

        if not n_clicks:
            return no_update

        df = get_main_grid_dataframe(
            filter_store,
            only_zero_price_products=bool(
                only_zero_price_products
            ),
            filter_model=filter_model,
            sort_model=sort_model,
        )

        df = _prepare_export_dataframe(
            df
        )

        if df.empty:
            return no_update

        filename = (
            "cost_analysis_filtered_"
            f"{datetime.now():%Y-%m-%d_%H-%M}.csv"
        )

        return dcc.send_data_frame(
            df.to_csv,
            filename,
            index=False,
            sep=";",
            encoding="utf-8-sig",
        )

    # -----------------------------------------------------------------
    # Excel истории УПД
    # -----------------------------------------------------------------

    @app.callback(
        Output(
            HISTORY_GRID_DOWNLOAD_ID,
            "data",
        ),
        Input(
            HISTORY_GRID_DOWNLOAD_EXCEL_BTN_ID,
            "n_clicks",
        ),
        State(
            SELECTED_PRODUCT_STORE_ID,
            "data",
        ),
        State(
            FILTERED_DATA_STORE_ID,
            "data",
        ),
        State(
            HISTORY_GRID_ID,
            "filterModel",
        ),
        State(
            HISTORY_GRID_ID,
            "sortModel",
        ),
        prevent_initial_call=True,
    )
    def download_history_grid_excel(
        n_clicks,
        selected_product,
        filter_store,
        filter_model,
        sort_model,
    ):
        """
        Скачивает историю
        выбранного товара.
        """

        if (
            not n_clicks
            or not selected_product
        ):
            return no_update

        nm_id, product_history = (
            _get_product_history(
                selected_product,
                filter_store,
            )
        )

        if (
            not nm_id
            or product_history.empty
        ):
            return no_update

        product_history = (
            apply_ag_grid_filter_model(
                product_history,
                filter_model,
            )
        )

        product_history = (
            apply_ag_grid_sort_model(
                product_history,
                sort_model,
            )
        )

        product_history = (
            _prepare_export_dataframe(
                product_history
            )
        )

        if product_history.empty:
            return no_update

        filename = (
            f"upd_price_history_{nm_id}_"
            f"{datetime.now():%Y-%m-%d_%H-%M}.xlsx"
        )

        return dcc.send_data_frame(
            product_history.to_excel,
            filename,
            index=False,
            sheet_name="История УПД",
        )