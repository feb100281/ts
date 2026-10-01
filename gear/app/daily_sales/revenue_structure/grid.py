# # gear/app/daily_sales/revenue_structure/grid.py

# from __future__ import annotations

# import dash_ag_grid as dag
# import dash_mantine_components as dmc

# from dash import dcc
# from dash_iconify import DashIconify


# # =========================================================
# # Форматтеры
# # =========================================================

# # Все денежные показатели:
# # 1 234 567
# MONEY_FORMATTER = {
#     "function": """
#         params.value == null
#             ? ''
#             : d3.format(',.0f')(
#                 params.value
#             ).replaceAll(',', ' ')
#     """
# }


# # Целые числа:
# # 1 234
# NUMBER_FORMATTER = {
#     "function": """
#         params.value == null
#             ? ''
#             : d3.format(',.0f')(
#                 params.value
#             ).replaceAll(',', ' ')
#     """
# }


# # Проценты:
# # 25 %
# PERCENT_FORMATTER = {
#     "function": """
#         params.value == null
#             ? ''
#             : d3.format(',.0f')(
#                 params.value
#             ).replaceAll(',', ' ')
#             + ' %'
#     """
# }


# # =========================================================
# # Стили
# # =========================================================

# MARGIN_STYLE = {
#     "styleConditions": [
#         {
#             "condition": (
#                 "params.value < 0"
#             ),
#             "style": {
#                 "color": "#B42318",
#                 "backgroundColor": (
#                     "rgba(180, 35, 24, 0.08)"
#                 ),
#                 "fontWeight": "700",
#             },
#         },
#         {
#             "condition": (
#                 "params.value >= 0 "
#                 "&& params.value < 20"
#             ),
#             "style": {
#                 "color": "#B54708",
#                 "backgroundColor": (
#                     "rgba(181, 71, 8, 0.08)"
#                 ),
#                 "fontWeight": "700",
#             },
#         },
#         {
#             "condition": (
#                 "params.value >= 20"
#             ),
#             "style": {
#                 "color": "#166534",
#                 "backgroundColor": (
#                     "rgba(22, 101, 52, 0.08)"
#                 ),
#                 "fontWeight": "700",
#             },
#         },
#     ],
#     "defaultStyle": {
#         "fontWeight": "700",
#     },
# }


# PROFIT_STYLE = {
#     "styleConditions": [
#         {
#             "condition": (
#                 "params.value < 0"
#             ),
#             "style": {
#                 "color": "#B42318",
#                 "backgroundColor": (
#                     "rgba(180, 35, 24, 0.06)"
#                 ),
#                 "fontWeight": "700",
#             },
#         },
#         {
#             "condition": (
#                 "params.value > 0"
#             ),
#             "style": {
#                 "color": "#166534",
#                 "fontWeight": "700",
#             },
#         },
#     ],
# }


# COMMISSION_STYLE = {
#     "styleConditions": [
#         {
#             "condition": (
#                 "params.value < 0"
#             ),
#             "style": {
#                 "color": "#B42318",
#                 "fontWeight": "600",
#             },
#         },
#     ],
# }


# CONTROL_STYLE = {
#     "styleConditions": [
#         {
#             "condition": (
#                 "params.value > 0"
#             ),
#             "style": {
#                 "color": "#B42318",
#                 "backgroundColor": (
#                     "rgba(180, 35, 24, 0.08)"
#                 ),
#                 "fontWeight": "700",
#             },
#         },
#     ],
# }


# # =========================================================
# # Таблица
# # =========================================================

# def build_revenue_grid(
#     rows: list[dict],
#     dimension_label: str,
#     grid_id: str,
#     excel_button_id: str,
#     excel_download_id: str,
# ):
#     """
#     Таблица структуры выручки и маржинальности.

#     Особенности:
#     - checkbox для выбора одной строки;
#     - выбор только через checkbox;
#     - фильтры по всем колонкам;
#     - сортировка;
#     - зебра;
#     - 0 знаков после запятой;
#     - Excel-выгрузка;
#     - комиссия WB включена в показатели.
#     """

#     column_defs = [
#         # =================================================
#         # Измерение
#         # =================================================

#         {
#             "headerName": (
#                 dimension_label
#             ),
#             "field": "name",

#             "minWidth": 220,
#             "flex": 2,

#             "pinned": "left",

#             "checkboxSelection": True,

#             "headerCheckboxSelection": False,

#             "filter": (
#                 "agTextColumnFilter"
#             ),

#             "filterParams": {
#                 "buttons": [
#                     "reset",
#                 ],
#                 "closeOnApply": True,
#             },

#             "cellStyle": {
#                 "fontWeight": "700",
#                 "backgroundColor": "#F9FAFB",
#             },
#         },

#         # =================================================
#         # Выручка
#         # =================================================

#         {
#             "headerName": (
#                 "Выручка с НДС"
#             ),
#             "field": "revenue_vat",

#             "width": 145,

#             "type": "numericColumn",

#             "filter": (
#                 "agNumberColumnFilter"
#             ),

#             "valueFormatter": (
#                 MONEY_FORMATTER
#             ),
#         },

#         {
#             "headerName": "НДС",

#             "field": "vat_amount",

#             "width": 115,

#             "type": "numericColumn",

#             "filter": (
#                 "agNumberColumnFilter"
#             ),

#             "valueFormatter": (
#                 MONEY_FORMATTER
#             ),
#         },

#         {
#             "headerName": (
#                 "Выручка без НДС"
#             ),

#             "field": "revenue_vatless",

#             "width": 165,

#             "type": "numericColumn",

#             "filter": (
#                 "agNumberColumnFilter"
#             ),

#             "valueFormatter": (
#                 MONEY_FORMATTER
#             ),

#             "cellStyle": {
#                 "fontWeight": "800",
#                 "backgroundColor": "#F0F7FF",
#             },
#         },

#         {
#             "headerName": (
#                 "Доля выручки"
#             ),

#             "field": (
#                 "revenue_share_pct"
#             ),

#             "width": 130,

#             "type": "numericColumn",

#             "filter": (
#                 "agNumberColumnFilter"
#             ),

#             "valueFormatter": (
#                 PERCENT_FORMATTER
#             ),
#         },

#         # =================================================
#         # Комиссия WB
#         # =================================================

#         {
#             "headerName": (
#                 "Комиссия WB"
#             ),

#             "field": (
#                 "net_comission"
#             ),

#             "width": 145,

#             "type": "numericColumn",

#             "filter": (
#                 "agNumberColumnFilter"
#             ),

#             "valueFormatter": (
#                 MONEY_FORMATTER
#             ),

#             "cellStyle": (
#                 COMMISSION_STYLE
#             ),
#         },

#         {
#             "headerName": (
#                 "Комиссия WB, %"
#             ),

#             "field": (
#                 "commission_pct"
#             ),

#             "width": 145,

#             "type": "numericColumn",

#             "filter": (
#                 "agNumberColumnFilter"
#             ),

#             "valueFormatter": (
#                 PERCENT_FORMATTER
#             ),
#         },

#         # =================================================
#         # Бухгалтерский блок
#         # =================================================

#         {
#             "headerName": (
#                 "С/с бух."
#             ),

#             "field": "cogs_book",

#             "width": 135,

#             "type": "numericColumn",

#             "filter": (
#                 "agNumberColumnFilter"
#             ),

#             "valueFormatter": (
#                 MONEY_FORMATTER
#             ),
#         },

#         {
#             "headerName": (
#                 "Прибыль бух."
#             ),

#             "field": (
#                 "gross_profit_book"
#             ),

#             "width": 150,

#             "type": "numericColumn",

#             "filter": (
#                 "agNumberColumnFilter"
#             ),

#             "valueFormatter": (
#                 MONEY_FORMATTER
#             ),

#             "cellStyle": (
#                 PROFIT_STYLE
#             ),
#         },

#         {
#             "headerName": (
#                 "Маржа бух., %"
#             ),

#             "field": (
#                 "margin_book_pct"
#             ),

#             "width": 140,

#             "type": "numericColumn",

#             "filter": (
#                 "agNumberColumnFilter"
#             ),

#             "valueFormatter": (
#                 PERCENT_FORMATTER
#             ),

#             "cellStyle": (
#                 MARGIN_STYLE
#             ),
#         },

#         # =================================================
#         # Управленческий блок
#         # =================================================

#         {
#             "headerName": (
#                 "С/с упр."
#             ),

#             "field": "cogs_man",

#             "width": 135,

#             "type": "numericColumn",

#             "filter": (
#                 "agNumberColumnFilter"
#             ),

#             "valueFormatter": (
#                 MONEY_FORMATTER
#             ),
#         },

#         {
#             "headerName": (
#                 "Прибыль упр."
#             ),

#             "field": (
#                 "gross_profit_man"
#             ),

#             "width": 150,

#             "type": "numericColumn",

#             "filter": (
#                 "agNumberColumnFilter"
#             ),

#             "valueFormatter": (
#                 MONEY_FORMATTER
#             ),

#             "cellStyle": (
#                 PROFIT_STYLE
#             ),
#         },

#         {
#             "headerName": (
#                 "Маржа упр., %"
#             ),

#             "field": (
#                 "margin_man_pct"
#             ),

#             "width": 140,

#             "type": "numericColumn",

#             "filter": (
#                 "agNumberColumnFilter"
#             ),

#             "valueFormatter": (
#                 PERCENT_FORMATTER
#             ),

#             "cellStyle": (
#                 MARGIN_STYLE
#             ),
#         },

#         # =================================================
#         # Количество
#         # =================================================

#         {
#             "headerName": (
#                 "Кол-во нетто"
#             ),

#             "field": "net_qty",

#             "width": 125,

#             "type": "numericColumn",

#             "filter": (
#                 "agNumberColumnFilter"
#             ),

#             "valueFormatter": (
#                 NUMBER_FORMATTER
#             ),
#         },

#         {
#             "headerName": (
#                 "Ср. выручка / ед."
#             ),

#             "field": (
#                 "average_revenue"
#             ),

#             "width": 155,

#             "type": "numericColumn",

#             "filter": (
#                 "agNumberColumnFilter"
#             ),

#             "valueFormatter": (
#                 MONEY_FORMATTER
#             ),
#         },

#         {
#             "headerName": (
#                 "Товаров"
#             ),

#             "field": (
#                 "products_count"
#             ),

#             "width": 105,

#             "type": "numericColumn",

#             "filter": (
#                 "agNumberColumnFilter"
#             ),

#             "valueFormatter": (
#                 NUMBER_FORMATTER
#             ),
#         },

#         # =================================================
#         # Контроль качества данных
#         # =================================================

#         {
#             "headerName": (
#                 "Без бух. с/с"
#             ),

#             "field": (
#                 "no_book_cost"
#             ),

#             "width": 120,

#             "type": "numericColumn",

#             "filter": (
#                 "agNumberColumnFilter"
#             ),

#             "valueFormatter": (
#                 NUMBER_FORMATTER
#             ),

#             "cellStyle": (
#                 CONTROL_STYLE
#             ),
#         },

#         {
#             "headerName": (
#                 "Без упр. с/с"
#             ),

#             "field": (
#                 "no_man_cost"
#             ),

#             "width": 120,

#             "type": "numericColumn",

#             "filter": (
#                 "agNumberColumnFilter"
#             ),

#             "valueFormatter": (
#                 NUMBER_FORMATTER
#             ),

#             "cellStyle": (
#                 CONTROL_STYLE
#             ),
#         },
#     ]

#     grid = dag.AgGrid(
#         id=grid_id,

#         rowData=rows,

#         columnDefs=column_defs,

#         defaultColDef={
#             "sortable": True,
#             "resizable": True,
#             "filter": True,

#             # Не показываем отдельную строку
#             # фильтров под заголовком.
#             "floatingFilter": False,
#         },

#         dashGridOptions={
#             "animateRows": False,

#             "rowSelection": {
#                 "mode": "singleRow",

#                 # Выбор только checkbox.
#                 "enableClickSelection": False,
#             },

#             "suppressCellFocus": True,

#             "ensureDomOrder": True,

#             "getRowId": {
#                 "function": (
#                     "params.data.name"
#                 ),
#             },

#             # Зебра.
#             "getRowStyle": {
#                 "styleConditions": [
#                     {
#                         "condition": (
#                             "params.node.rowIndex % 2 === 1"
#                         ),

#                         "style": {
#                             "backgroundColor": (
#                                 "#F9FAFB"
#                             ),
#                         },
#                     },
#                 ],
#             },

#             # Более компактная таблица.
#             "rowHeight": 38,

#             "headerHeight": 44,

#             # Фиксируем высоту,
#             # чтобы заголовок оставался виден.
#             "domLayout": "normal",
#         },

#         style={
#             "height": "520px",
#             "width": "100%",
#         },

#         className=(
#             "ag-theme-quartz"
#         ),
#     )

#     return dmc.Stack(
#         gap="xs",

#         children=[
#             # =============================================
#             # Действия над таблицей
#             # =============================================

#             dmc.Group(
#                 justify="flex-end",

#                 children=[
#                     dmc.Button(
#                         "Скачать Excel",

#                         id=excel_button_id,

#                         variant="light",

#                         radius=0,

#                         size="xs",

#                         leftSection=(
#                             DashIconify(
#                                 icon=(
#                                     "solar:"
#                                     "file-download-"
#                                     "bold-duotone"
#                                 ),

#                                 width=17,
#                             )
#                         ),
#                     ),

#                     dcc.Download(
#                         id=excel_download_id
#                     ),
#                 ],
#             ),

#             grid,
#         ],
#     )



# gear/app/daily_sales/revenue_structure/grid.py

from __future__ import annotations

import dash_ag_grid as dag
import dash_mantine_components as dmc

from dash import dcc
from dash_iconify import DashIconify


# =========================================================
# Форматтеры
# =========================================================

# Денежные показатели:
# 1 234 567
MONEY_FORMATTER = {
    "function": """
        params.value == null
            ? ''
            : d3.format(',.0f')(
                params.value
            ).replaceAll(',', ' ')
    """
}


# Целые числа:
# 1 234
NUMBER_FORMATTER = {
    "function": """
        params.value == null
            ? ''
            : d3.format(',.0f')(
                params.value
            ).replaceAll(',', ' ')
    """
}


# Проценты:
# 25 %
PERCENT_FORMATTER = {
    "function": """
        params.value == null
            ? ''
            : d3.format(',.2f')(
                params.value
            ).replaceAll(',', ' ')
            + ' %'
    """
}


# =========================================================
# Базовые стили ячеек
# =========================================================

TEXT_CELL_STYLE = {
    "fontSize": "12px",
    "fontWeight": "500",
    "color": "#1F2937",
    "display": "flex",
    "alignItems": "center",
}


NUMERIC_CELL_STYLE = {
    "fontSize": "12px",
    "fontWeight": "400",
    "color": "#374151",
    "fontVariantNumeric": "tabular-nums",
}


# =========================================================
# Условное форматирование
# =========================================================

# ---------------------------------------------------------
# Маржинальность
#
# < 0%        — красный
# 0–20%       — нейтральный оранжевый
# >= 20%      — зелёный
# ---------------------------------------------------------

MARGIN_STYLE = {
    "styleConditions": [
        {
            "condition": "params.value < 0",
            "style": {
                "color": "#B42318",
                "backgroundColor": "rgba(180, 35, 24, 0.08)",
                "fontWeight": "600",
                "fontSize": "12px",
                "fontVariantNumeric": "tabular-nums",
            },
        },
        {
            "condition": (
                "params.value >= 0 "
                "&& params.value < 20"
            ),
            "style": {
                "color": "#B54708",
                "backgroundColor": "rgba(181, 71, 8, 0.06)",
                "fontWeight": "600",
                "fontSize": "12px",
                "fontVariantNumeric": "tabular-nums",
            },
        },
        {
            "condition": "params.value >= 20",
            "style": {
                "color": "#166534",
                "backgroundColor": "rgba(22, 101, 52, 0.07)",
                "fontWeight": "600",
                "fontSize": "12px",
                "fontVariantNumeric": "tabular-nums",
            },
        },
    ],
    "defaultStyle": {
        "fontSize": "12px",
        "fontWeight": "500",
        "fontVariantNumeric": "tabular-nums",
    },
}


# ---------------------------------------------------------
# Прибыль
#
# Отрицательная — красная
# Положительная — зелёная
# ---------------------------------------------------------

PROFIT_STYLE = {
    "styleConditions": [
        {
            "condition": "params.value < 0",
            "style": {
                "color": "#B42318",
                "backgroundColor": "rgba(180, 35, 24, 0.06)",
                "fontWeight": "600",
                "fontSize": "12px",
                "fontVariantNumeric": "tabular-nums",
            },
        },
        {
            "condition": "params.value > 0",
            "style": {
                "color": "#166534",
                "fontWeight": "600",
                "fontSize": "12px",
                "fontVariantNumeric": "tabular-nums",
            },
        },
    ],
    "defaultStyle": {
        "fontSize": "12px",
        "fontWeight": "400",
        "color": "#374151",
        "fontVariantNumeric": "tabular-nums",
    },
}


# ---------------------------------------------------------
# Комиссия WB
#
# Отрицательные значения выделяем красным,
# но без лишней заливки.
# ---------------------------------------------------------

COMMISSION_STYLE = {
    "styleConditions": [
        {
            "condition": "params.value < 0",
            "style": {
                "color": "#B42318",
                "fontWeight": "600",
                "fontSize": "12px",
                "fontVariantNumeric": "tabular-nums",
            },
        },
    ],
    "defaultStyle": {
        "fontSize": "12px",
        "fontWeight": "400",
        "color": "#374151",
        "fontVariantNumeric": "tabular-nums",
    },
}


# ---------------------------------------------------------
# Контроль качества данных
#
# Если есть товары без себестоимости —
# выделяем красным.
# ---------------------------------------------------------

CONTROL_STYLE = {
    "styleConditions": [
        {
            "condition": "params.value > 0",
            "style": {
                "color": "#B42318",
                "backgroundColor": "rgba(180, 35, 24, 0.08)",
                "fontWeight": "600",
                "fontSize": "12px",
                "fontVariantNumeric": "tabular-nums",
            },
        },
    ],
    "defaultStyle": {
        "fontSize": "12px",
        "fontWeight": "400",
        "color": "#6B7280",
        "fontVariantNumeric": "tabular-nums",
    },
}


# =========================================================
# Вспомогательная функция для числовой колонки
# =========================================================

def numeric_column(
    header_name: str,
    field: str,
    width: int,
    value_formatter: dict,
    cell_style: dict | None = None,
) -> dict:
    """
    Создаёт стандартную числовую колонку.

    Все числовые колонки имеют единый:
    - размер шрифта;
    - формат;
    - выравнивание;
    - стиль.
    """

    return {
        "headerName": header_name,
        "field": field,
        "width": width,
        "minWidth": width,
        "type": "numericColumn",
        "filter": "agNumberColumnFilter",
        "valueFormatter": value_formatter,
        "cellStyle": (
            cell_style
            if cell_style is not None
            else NUMERIC_CELL_STYLE
        ),
    }


# =========================================================
# Таблица
# =========================================================

def build_revenue_grid(
    rows: list[dict],
    dimension_label: str,
    grid_id: str,
    excel_button_id: str,
    excel_download_id: str,
):
    """
    Таблица структуры выручки и маржинальности.

    Особенности:
    - компактный профессиональный вид;
    - без checkbox;
    - без выбора строк;
    - компактный шрифт;
    - строгая заливка заголовка;
    - закреплённая первая колонка;
    - фильтры в заголовках;
    - сортировка;
    - аккуратная зебра;
    - красно-зелёная индикация показателей;
    - Excel-выгрузка.
    """

    # =====================================================
    # Колонки
    # =====================================================

    column_defs = [

        # =================================================
        # Измерение
        # =================================================

        {
            "headerName": dimension_label,
            "field": "name",

            "minWidth": 210,
            "flex": 2,

            "pinned": "left",

            "filter": "agTextColumnFilter",

            "filterParams": {
                "buttons": [
                    "reset",
                ],
                "closeOnApply": True,
            },

            "cellStyle": {
                **TEXT_CELL_STYLE,
                "fontWeight": "600",
                "backgroundColor": "#F8FAFC",
                "borderRight": "1px solid #E5E7EB",
            },
        },

        # =================================================
        # Выручка
        # =================================================

        numeric_column(
            header_name="Выручка с НДС",
            field="revenue_vat",
            width=135,
            value_formatter=MONEY_FORMATTER,
        ),

        numeric_column(
            header_name="НДС",
            field="vat_amount",
            width=105,
            value_formatter=MONEY_FORMATTER,
        ),

        numeric_column(
            header_name="Выручка без НДС",
            field="revenue_vatless",
            width=145,
            value_formatter=MONEY_FORMATTER,
            cell_style={
                "fontSize": "12px",
                "fontWeight": "600",
                "color": "#1D4ED8",
                "backgroundColor": "#F4F8FF",
                "fontVariantNumeric": "tabular-nums",
            },
        ),

        numeric_column(
            header_name="Доля выручки",
            field="revenue_share_pct",
            width=120,
            value_formatter=PERCENT_FORMATTER,
        ),

        # =================================================
        # Комиссия WB
        # =================================================

        numeric_column(
            header_name="Комиссия WB",
            field="net_comission",
            width=130,
            value_formatter=MONEY_FORMATTER,
            cell_style=COMMISSION_STYLE,
        ),

        numeric_column(
            header_name="Комиссия WB, %",
            field="commission_pct",
            width=130,
            value_formatter=PERCENT_FORMATTER,
        ),

        # =================================================
        # Бухгалтерский блок
        # =================================================

        numeric_column(
            header_name="С/с бух.",
            field="cogs_book",
            width=120,
            value_formatter=MONEY_FORMATTER,
        ),

        numeric_column(
            header_name="Прибыль бух.",
            field="gross_profit_book",
            width=135,
            value_formatter=MONEY_FORMATTER,
            cell_style=PROFIT_STYLE,
        ),

        numeric_column(
            header_name="Маржа бух., %",
            field="margin_book_pct",
            width=125,
            value_formatter=PERCENT_FORMATTER,
            cell_style=MARGIN_STYLE,
        ),

        # =================================================
        # Управленческий блок
        # =================================================

        numeric_column(
            header_name="С/с упр.",
            field="cogs_man",
            width=120,
            value_formatter=MONEY_FORMATTER,
        ),

        numeric_column(
            header_name="Прибыль упр.",
            field="gross_profit_man",
            width=135,
            value_formatter=MONEY_FORMATTER,
            cell_style=PROFIT_STYLE,
        ),

        numeric_column(
            header_name="Маржа упр., %",
            field="margin_man_pct",
            width=125,
            value_formatter=PERCENT_FORMATTER,
            cell_style=MARGIN_STYLE,
        ),

        # =================================================
        # Количество
        # =================================================

        numeric_column(
            header_name="Кол-во нетто",
            field="net_qty",
            width=115,
            value_formatter=NUMBER_FORMATTER,
        ),

        numeric_column(
            header_name="Ср. выручка / ед.",
            field="average_revenue",
            width=140,
            value_formatter=MONEY_FORMATTER,
        ),

        numeric_column(
            header_name="Товаров",
            field="products_count",
            width=95,
            value_formatter=NUMBER_FORMATTER,
        ),

        # =================================================
        # Контроль качества данных
        # =================================================

        numeric_column(
            header_name="Без бух. с/с",
            field="no_book_cost",
            width=110,
            value_formatter=NUMBER_FORMATTER,
            cell_style=CONTROL_STYLE,
        ),

        numeric_column(
            header_name="Без упр. с/с",
            field="no_man_cost",
            width=110,
            value_formatter=NUMBER_FORMATTER,
            cell_style=CONTROL_STYLE,
        ),
    ]


    # =====================================================
    # AG Grid
    # =====================================================

    grid = dag.AgGrid(
        id=grid_id,

        rowData=rows,

        columnDefs=column_defs,

        # =================================================
        # Общие настройки колонок
        # =================================================

        defaultColDef={
            "sortable": True,
            "resizable": True,
            "filter": True,

            # Убираем строку поиска под заголовком.
            "floatingFilter": False,

            # Более аккуратные заголовки.
            "wrapHeaderText": False,

            # Убираем меню, появляющееся постоянно.
            # Иконка фильтра появляется по hover.
            "suppressHeaderMenuButton": False,
        },

        # =================================================
        # Опции таблицы
        # =================================================

        dashGridOptions={

            # Без анимации при обновлении данных.
            "animateRows": False,

            # Checkbox и выбор строк полностью убраны.
            "rowSelection": None,

            # При клике на ячейку строка не выделяется.
            "suppressRowClickSelection": True,

            # Не показываем рамку активной ячейки.
            "suppressCellFocus": True,

            # Более стабильный DOM.
            "ensureDomOrder": True,

            # Уникальный ID строки.
            "getRowId": {
                "function": "params.data.name",
            },

            # ---------------------------------------------
            # Зебра
            # ---------------------------------------------

            "getRowStyle": {
                "styleConditions": [
                    {
                        "condition": (
                            "params.node.rowIndex % 2 === 1"
                        ),
                        "style": {
                            "backgroundColor": "#FAFBFC",
                        },
                    },
                ],
            },

            # ---------------------------------------------
            # Компактная таблица
            # ---------------------------------------------

            "rowHeight": 32,

            "headerHeight": 38,

            # Заголовок остаётся сверху внутри контейнера.
            "domLayout": "normal",

            # Не растягиваем текст по вертикали.
            "suppressRowTransform": False,

            # Убираем лишний горизонтальный bounce.
            "alwaysShowHorizontalScroll": False,

            # Tooltip без задержки.
            "tooltipShowDelay": 300,
        },

        # =================================================
        # Размер и CSS-переменные AG Grid Quartz
        # =================================================

        style={
            "height": "520px",
            "width": "100%",

            # ---------------------------------------------
            # Основной шрифт
            # ---------------------------------------------

            "--ag-font-family": (
                "Inter, -apple-system, BlinkMacSystemFont, "
                "'Segoe UI', Arial, sans-serif"
            ),

            "--ag-font-size": "12px",

            # ---------------------------------------------
            # Фон таблицы
            # ---------------------------------------------

            "--ag-background-color": "#FFFFFF",

            "--ag-foreground-color": "#374151",

            # ---------------------------------------------
            # Шапка
            # ---------------------------------------------

            "--ag-header-background-color": "#F1F3F5",

            "--ag-header-foreground-color": "#1F2937",

            "--ag-header-font-weight": "600",

            # ---------------------------------------------
            # Границы
            # ---------------------------------------------

            "--ag-border-color": "#E5E7EB",

            "--ag-row-border-color": "#EEF0F2",

            "--ag-secondary-border-color": "#E5E7EB",

            "--ag-wrapper-border-radius": "0px",

            "--ag-border-radius": "0px",

            # ---------------------------------------------
            # Hover
            # ---------------------------------------------

            "--ag-row-hover-color": "#F3F6F9",

            # ---------------------------------------------
            # Выделение
            # ---------------------------------------------

            "--ag-selected-row-background-color": (
                "transparent"
            ),

            # ---------------------------------------------
            # Spacing
            # ---------------------------------------------

            "--ag-cell-horizontal-padding": "10px",

            "--ag-grid-size": "4px",

            # ---------------------------------------------
            # Иконки
            # ---------------------------------------------

            "--ag-icon-size": "13px",

            "--ag-icon-font-color": "#6B7280",
        },

        className="ag-theme-quartz",
    )


    # =====================================================
    # Панель + таблица
    # =====================================================

    return dmc.Stack(
        gap=8,

        children=[

            # =================================================
            # Действия над таблицей
            # =================================================

            dmc.Group(
                justify="flex-end",

                children=[
                    dmc.Button(
                        "Скачать Excel",

                        id=excel_button_id,

                        variant="light",

                        radius=0,

                        size="xs",

                        leftSection=(
                            DashIconify(
                                icon=(
                                    "solar:"
                                    "file-download-"
                                    "bold-duotone"
                                ),
                                width=16,
                            )
                        ),

                        styles={
                            "root": {
                                "height": "30px",
                                "fontSize": "12px",
                                "fontWeight": "500",
                            },
                        },
                    ),

                    dcc.Download(
                        id=excel_download_id
                    ),
                ],
            ),

            # =================================================
            # Таблица
            # =================================================

            grid,
        ],
    )
