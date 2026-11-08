# gear/app/daily_sales/ai_analysis/entity_grid.py

from __future__ import annotations

from typing import Any

import dash_ag_grid as dag


# -------------------------------------------------------------
# Палитра
# -------------------------------------------------------------
POSITIVE_COLOR = "#166534"
POSITIVE_BG = "rgba(22, 101, 52, 0.08)"

NEGATIVE_COLOR = "#B42318"
NEGATIVE_BG = "rgba(180, 35, 24, 0.08)"

WARNING_COLOR = "#B54708"
WARNING_BG = "rgba(181, 71, 8, 0.08)"

NEUTRAL_COLOR = "#667085"
NEUTRAL_BG = "#F2F4F7"

TEXT_COLOR = "#344054"
MUTED_COLOR = "#667085"

BORDER_COLOR = "#E4E7EC"
HEADER_BG = "#F8FAFC"


# -------------------------------------------------------------
# Форматтеры
#
# ВАЖНО:
# rowData остаётся числовым.
# valueFormatter меняет только отображение.
# Поэтому сортировка и фильтрация работают как по числам.
# -------------------------------------------------------------

MONEY_FORMATTER = {
    "function": """
        params.value == null
            ? ''
            : d3.format(',.2f')(params.value).replaceAll(',', ' ')
    """
}


SIGNED_MONEY_FORMATTER = {
    "function": """
        params.value == null
            ? ''
            : (
                params.value > 0
                    ? '+'
                    : params.value < 0
                        ? '−'
                        : ''
              )
              + d3.format(',.2f')(Math.abs(params.value))
                    .replaceAll(',', ' ')
    """
}


PERCENT_FORMATTER = {
    "function": """
        params.value == null
            ? ''
            : d3.format(',.2f')(params.value)
                .replaceAll(',', ' ')
                + ' %'
    """
}


SIGNED_PERCENT_FORMATTER = {
    "function": """
        params.value == null
            ? ''
            : (
                params.value > 0
                    ? '+'
                    : params.value < 0
                        ? '−'
                        : ''
              )
              + d3.format(',.2f')(Math.abs(params.value))
                    .replaceAll(',', ' ')
              + ' %'
    """
}


PERCENTAGE_POINT_FORMATTER = {
    "function": """
        params.value == null
            ? ''
            : (
                params.value > 0
                    ? '+'
                    : params.value < 0
                        ? '−'
                        : ''
              )
              + d3.format(',.2f')(Math.abs(params.value))
                    .replaceAll(',', ' ')
              + ' п.п.'
    """
}


# -------------------------------------------------------------
# Подготовка данных
# -------------------------------------------------------------
def _to_float(
    value: Any,
    default: float = 0.0,
) -> float:
    """
    Безопасное преобразование в float.
    """

    if value is None:
        return default

    if isinstance(value, str):
        value = (
            value
            .strip()
            .replace(" ", "")
            .replace(",", ".")
        )

        if not value:
            return default

    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _prepare_rows(
    rows: list[dict],
) -> list[dict]:
    """
    Подготавливает числовые данные для AG Grid.

    Значения НЕ превращаются в строки.
    Это критично для правильной сортировки.
    """

    result = []

    for row in rows:
        current_revenue = _to_float(
            row.get("current_revenue")
        )

        previous_revenue = _to_float(
            row.get("previous_revenue")
        )

        revenue_delta = _to_float(
            row.get(
                "revenue_delta",
                current_revenue - previous_revenue,
            )
        )

        revenue_change_pct = _to_float(
            row.get("revenue_change_pct")
        )

        current_return_rate = _to_float(
            row.get("current_return_rate")
        )

        previous_return_rate = _to_float(
            row.get("previous_return_rate")
        )

        return_rate_delta = _to_float(
            row.get(
                "return_rate_delta",
                (
                    current_return_rate
                    - previous_return_rate
                ),
            )
        )

        result.append(
            {
                "name": str(
                    row.get("name")
                    or "Без названия"
                ),

                # Оставляем числами.
                # round убирает артефакты binary float.
                "current_revenue": round(
                    current_revenue,
                    2,
                ),
                "previous_revenue": round(
                    previous_revenue,
                    2,
                ),
                "revenue_delta": round(
                    revenue_delta,
                    2,
                ),
                "revenue_change_pct": round(
                    revenue_change_pct,
                    2,
                ),
                "current_return_rate": round(
                    current_return_rate,
                    2,
                ),
                "previous_return_rate": round(
                    previous_return_rate,
                    2,
                ),
                "return_rate_delta": round(
                    return_rate_delta,
                    2,
                ),
            }
        )

    return sorted(
        result,
        key=lambda item: abs(
            item["revenue_delta"]
        ),
        reverse=True,
    )


# -------------------------------------------------------------
# Стили изменений
# -------------------------------------------------------------
POSITIVE_NEGATIVE_STYLE = {
    "styleConditions": [
        {
            "condition": "params.value > 0",
            "style": {
                "color": POSITIVE_COLOR,
                "backgroundColor": POSITIVE_BG,
                "fontWeight": "700",
            },
        },
        {
            "condition": "params.value < 0",
            "style": {
                "color": NEGATIVE_COLOR,
                "backgroundColor": NEGATIVE_BG,
                "fontWeight": "700",
            },
        },
    ],
    "defaultStyle": {
        "color": NEUTRAL_COLOR,
        "backgroundColor": NEUTRAL_BG,
        "fontWeight": "700",
        "fontVariantNumeric": "tabular-nums",
    },
}


# Для динамики возвратов логика обратная:
# уменьшение возвратов — хорошо,
# увеличение — плохо.
INVERSE_POSITIVE_NEGATIVE_STYLE = {
    "styleConditions": [
        {
            "condition": "params.value < 0",
            "style": {
                "color": POSITIVE_COLOR,
                "backgroundColor": POSITIVE_BG,
                "fontWeight": "700",
            },
        },
        {
            "condition": "params.value > 0",
            "style": {
                "color": NEGATIVE_COLOR,
                "backgroundColor": NEGATIVE_BG,
                "fontWeight": "700",
            },
        },
    ],
    "defaultStyle": {
        "color": NEUTRAL_COLOR,
        "backgroundColor": NEUTRAL_BG,
        "fontWeight": "700",
        "fontVariantNumeric": "tabular-nums",
    },
}


RETURN_RATE_STYLE = {
    "styleConditions": [
        {
            "condition": "params.value >= 20",
            "style": {
                "color": NEGATIVE_COLOR,
                "backgroundColor": NEGATIVE_BG,
                "fontWeight": "700",
            },
        },
        {
            "condition": (
                "params.value >= 15 "
                "&& params.value < 20"
            ),
            "style": {
                "color": WARNING_COLOR,
                "backgroundColor": WARNING_BG,
                "fontWeight": "700",
            },
        },
    ],
    "defaultStyle": {
        "color": TEXT_COLOR,
        "fontVariantNumeric": "tabular-nums",
    },
}


# -------------------------------------------------------------
# Вспомогательные колонки
# -------------------------------------------------------------
def _money_col(
    field: str,
    header: str,
    min_width: int = 165,
    flex: float = 1,
    cell_style=None,
):
    return {
        "field": field,
        "headerName": header,
        "minWidth": min_width,
        "flex": flex,
        "type": "numericColumn",
        "filter": "agNumberColumnFilter",
        "valueFormatter": MONEY_FORMATTER,
        "cellStyle": cell_style or {
            "fontVariantNumeric": "tabular-nums",
        },
    }


def _signed_money_col(
    field: str,
    header: str,
    min_width: int = 175,
    flex: float = 1,
):
    return {
        "field": field,
        "headerName": header,
        "minWidth": min_width,
        "flex": flex,
        "type": "numericColumn",
        "filter": "agNumberColumnFilter",
        "valueFormatter": SIGNED_MONEY_FORMATTER,
        "cellStyle": POSITIVE_NEGATIVE_STYLE,
    }


def _percent_col(
    field: str,
    header: str,
    min_width: int = 130,
    flex: float = 0.8,
    cell_style=None,
):
    return {
        "field": field,
        "headerName": header,
        "minWidth": min_width,
        "flex": flex,
        "type": "numericColumn",
        "filter": "agNumberColumnFilter",
        "valueFormatter": PERCENT_FORMATTER,
        "cellStyle": cell_style or {
            "fontVariantNumeric": "tabular-nums",
        },
    }


def _signed_percent_col(
    field: str,
    header: str,
    min_width: int = 130,
    flex: float = 0.8,
):
    return {
        "field": field,
        "headerName": header,
        "minWidth": min_width,
        "flex": flex,
        "type": "numericColumn",
        "filter": "agNumberColumnFilter",
        "valueFormatter": SIGNED_PERCENT_FORMATTER,
        "cellStyle": POSITIVE_NEGATIVE_STYLE,
    }


# -------------------------------------------------------------
# Основная таблица
# -------------------------------------------------------------
def entity_table(
    rows: list[dict],
    entity_label: str,
):
    row_data = _prepare_rows(rows)

    column_defs = [
        {
            "field": "name",
            "headerName": entity_label,

            "pinned": "left",
            "lockPinned": True,

            "minWidth": 220,
            "maxWidth": 380,
            "flex": 1.35,

            "tooltipField": "name",

            "filter": "agTextColumnFilter",

            "cellStyle": {
                "fontWeight": "700",
                "color": TEXT_COLOR,
                "backgroundColor": "#FFFFFF",
                "borderRight": (
                    f"1px solid {BORDER_COLOR}"
                ),
            },
        },

        _money_col(
            field="current_revenue",
            header="Текущая выручка",
            min_width=175,
            flex=1,
            cell_style={
                "fontWeight": "700",
                "color": TEXT_COLOR,
                "fontVariantNumeric": "tabular-nums",
            },
        ),

        _money_col(
            field="previous_revenue",
            header="Предыдущая выручка",
            min_width=185,
            flex=1,
            cell_style={
                "color": MUTED_COLOR,
                "fontVariantNumeric": "tabular-nums",
            },
        ),

        _signed_money_col(
            field="revenue_delta",
            header="Вклад в изменение",
            min_width=190,
            flex=1,
        ),

        _signed_percent_col(
            field="revenue_change_pct",
            header="Δ выручки",
            min_width=140,
            flex=0.8,
        ),

        _percent_col(
            field="current_return_rate",
            header="Возвраты",
            min_width=130,
            flex=0.75,
            cell_style=RETURN_RATE_STYLE,
        ),

        _percent_col(
            field="previous_return_rate",
            header="Возвраты ранее",
            min_width=155,
            flex=0.85,
            cell_style={
                "color": MUTED_COLOR,
                "fontVariantNumeric": "tabular-nums",
            },
        ),

        {
            "field": "return_rate_delta",
            "headerName": "Δ доли",

            "minWidth": 140,
            "flex": 0.8,

            "type": "numericColumn",
            "filter": "agNumberColumnFilter",

            "valueFormatter": (
                PERCENTAGE_POINT_FORMATTER
            ),

            "cellStyle": (
                INVERSE_POSITIVE_NEGATIVE_STYLE
            ),
        },
    ]

    return dag.AgGrid(
        rowData=row_data,
        columnDefs=column_defs,

        # Обязательно для d3-format и JS formatter.
        dangerously_allow_code=True,

        defaultColDef={
            "sortable": True,
            "filter": True,
            "resizable": True,
            "editable": False,

            "suppressMovable": True,
            "floatingFilter": False,

            "wrapHeaderText": True,
            "autoHeaderHeight": True,

            "cellStyle": {
                "fontSize": "13px",
                "lineHeight": "1.25",
            },
        },

        dashGridOptions={
            "pagination": True,
            "paginationPageSize": 15,

            "paginationPageSizeSelector": [
                10,
                15,
                25,
                50,
            ],

            "enableCellTextSelection": True,
            "ensureDomOrder": True,

            "rowHeight": 42,
            "headerHeight": 48,

            "suppressCellFocus": True,
            "animateRows": False,

            "tooltipShowDelay": 200,
            "tooltipHideDelay": 5000,
        },

        style={
            "height": "575px",
            "width": "100%",

            "--ag-font-family": (
                "Inter, -apple-system, BlinkMacSystemFont, "
                "'Segoe UI', sans-serif"
            ),

            "--ag-font-size": "13px",

            "--ag-foreground-color": TEXT_COLOR,
            "--ag-secondary-foreground-color": MUTED_COLOR,

            "--ag-header-foreground-color": TEXT_COLOR,
            "--ag-header-background-color": HEADER_BG,

            "--ag-background-color": "#FFFFFF",
            "--ag-odd-row-background-color": "#FCFCFD",
            "--ag-row-hover-color": "#F8FAFC",

            "--ag-border-color": BORDER_COLOR,
            "--ag-row-border-color": "#EAECF0",

            "--ag-header-column-separator-color": (
                BORDER_COLOR
            ),
            "--ag-header-column-separator-display": (
                "block"
            ),

            "--ag-wrapper-border-radius": "3px",
            "--ag-cell-horizontal-padding": "12px",

            "--ag-selected-row-background-color": (
                "rgba(79, 70, 229, 0.06)"
            ),
        },

        className="ag-theme-quartz",
    )