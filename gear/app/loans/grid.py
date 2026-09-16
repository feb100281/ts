# # gear/app/loans/grid.py

# from __future__ import annotations

# import dash_ag_grid as dag

# from .config import COLORS, PAGE_SIZE
# from .ids import (
#     LOANS_GRID_ID,
#     TRANSACTIONS_GRID_ID,
# )


# # =====================================================================
# # FORMATTERS
# # =====================================================================

# MONEY_FORMATTER = {
#     "function": """
#     params.value == null
#         ? ''
#         : d3.format(',.2f')(params.value)
#             .replaceAll(',', ' ')
#     """
# }


# INTEGER_FORMATTER = {
#     "function": """
#     params.value == null
#         ? ''
#         : d3.format(',.0f')(params.value)
#             .replaceAll(',', ' ')
#     """
# }


# PERCENT_FORMATTER = {
#     "function": """
#     params.value == null
#         ? ''
#         : d3.format(',.2f')(params.value)
#             .replaceAll(',', ' ') + ' %'
#     """
# }


# DATE_FORMATTER = {
#     "function": """
#     if (
#         params.value === null
#         || params.value === undefined
#         || params.value === ''
#     ) {
#         return '';
#     }

#     const value = String(params.value).slice(0, 10);
#     const parts = value.split('-');

#     if (parts.length !== 3) {
#         return value;
#     }

#     return `${parts[2]}.${parts[1]}.${parts[0]}`;
#     """
# }


# BOOLEAN_FORMATTER = {
#     "function": """
#     if (
#         params.value === null
#         || params.value === undefined
#     ) {
#         return '';
#     }

#     return params.value ? 'Да' : 'Нет';
#     """
# }


# DOCUMENTS_FORMATTER = {
#     "function": """
#     if (
#         params.value === null
#         || params.value === undefined
#         || Number(params.value) === 0
#     ) {
#         return '—';
#     }

#     return '📎 ' + d3.format(',.0f')(params.value)
#         .replaceAll(',', ' ');
#     """
# }






# # =====================================================================
# # COMMON STYLES
# # =====================================================================


# RIGHT_CELL_STYLE = {
#     "textAlign": "right",
#     "fontVariantNumeric": "tabular-nums",
# }


# MONEY_CELL_STYLE = {
#     "textAlign": "right",
#     "fontVariantNumeric": "tabular-nums",
#     "color": COLORS["text"],
# }


# BOLD_MONEY_STYLE = {
#     "textAlign": "right",
#     "fontVariantNumeric": "tabular-nums",
#     "fontWeight": "600",
#     "color": COLORS["text"],
# }


# STATUS_CELL_STYLE = {
#     "styleConditions": [
#         {
#             "condition": (
#                 "params.value === 'Просрочен'"
#             ),
#             "style": {
#                 "backgroundColor": COLORS["light_red"],
#                 "color": COLORS["red"],
#                 "fontWeight": "600",
#             },
#         },
#         {
#             "condition": (
#                 "params.value === "
#                 "'Погашение ≤ 30 дней'"
#             ),
#             "style": {
#                 "backgroundColor": COLORS["light_orange"],
#                 "color": COLORS["orange"],
#                 "fontWeight": "600",
#             },
#         },
#         {
#             "condition": (
#                 "params.value === 'Активен'"
#             ),
#             "style": {
#                 "backgroundColor": COLORS["very_light_green"],
#                 "color": COLORS["dark_green"],
#                 "fontWeight": "600",
#             },
#         },
#         {
#             "condition": (
#                 "params.value === 'Погашен'"
#             ),
#             "style": {
#                 "backgroundColor": COLORS["light_gray"],
#                 "color": COLORS["gray"],
#                 "fontWeight": "500",
#             },
#         },
#     ]
# }


# MATURITY_DATE_STYLE = {
#     "styleConditions": [
#         {
#             "condition": (
#                 "params.data && "
#                 "params.data.days_to_maturity < 0 && "
#                 "params.data.total_debt > 0.01"
#             ),
#             "style": {
#                 "backgroundColor": COLORS["light_red"],
#                 "color": COLORS["red"],
#                 "fontWeight": "600",
#             },
#         },
#         {
#             "condition": (
#                 "params.data && "
#                 "params.data.days_to_maturity >= 0 && "
#                 "params.data.days_to_maturity <= 30 && "
#                 "params.data.total_debt > 0.01"
#             ),
#             "style": {
#                 "backgroundColor": COLORS["light_orange"],
#                 "color": COLORS["orange"],
#                 "fontWeight": "600",
#             },
#         },
#     ]
# }


# DAYS_STYLE = {
#     "styleConditions": [
#         {
#             "condition": (
#                 "params.value < 0"
#             ),
#             "style": {
#                 "color": COLORS["red"],
#                 "fontWeight": "700",
#                 "textAlign": "right",
#             },
#         },
#         {
#             "condition": (
#                 "params.value >= 0 && "
#                 "params.value <= 30"
#             ),
#             "style": {
#                 "color": COLORS["orange"],
#                 "fontWeight": "700",
#                 "textAlign": "right",
#             },
#         },
#     ]
# }


# DOCUMENTS_STYLE = {
#     "styleConditions": [
#         {
#             "condition": (
#                 "Number(params.value) > 0"
#             ),
#             "style": {
#                 "backgroundColor": COLORS["very_light_green"],
#                 "color": COLORS["dark_green"],
#                 "fontWeight": "600",
#                 "textAlign": "center",
#             },
#         },
#     ]
# }


# # =====================================================================
# # DEFAULT COLUMN
# # =====================================================================


# DEFAULT_COL_DEF = {
#     "sortable": True,
#     "filter": True,
#     "resizable": True,

#     "minWidth": 105,

#     "wrapHeaderText": True,
#     "autoHeaderHeight": True,

#     "suppressHeaderMenuButton": True,

#     "cellDataType": False,
# }


# # =====================================================================
# # LOANS GRID
# # =====================================================================


# def loans_column_defs():
#     return [
#         # =============================================================
#         # Статус
#         # =============================================================

#         {
#             "field": "status",
#             "headerName": "Статус",

#             "pinned": "left",

#             "width": 145,
#             "minWidth": 145,

#             "cellStyle": STATUS_CELL_STYLE,
#         },

#         # =============================================================
#         # Контрагент
#         # =============================================================

#         {
#             "field": "counterparty_name",
#             "headerName": "Контрагент",

#             "pinned": "left",

#             "minWidth": 245,
#             "flex": 1.35,

#             "cellStyle": {
#                 "fontWeight": "600",
#                 "color": COLORS["text"],
#             },
#         },

#         # =============================================================
#         # Договор
#         # =============================================================

#         {
#             "field": "contract_number",
#             "headerName": "Договор",

#             "minWidth": 130,

#             "cellStyle": {
#                 "fontWeight": "500",
#             },
#         },

#         {
#             "field": "contract_date",
#             "headerName": "Дата договора",

#             "valueFormatter": DATE_FORMATTER,

#             "minWidth": 125,
#         },

#         # =============================================================
#         # Документы
#         # =============================================================

#         {
#             "field": "documents_count",
#             "headerName": "Документы",

#             "valueFormatter": DOCUMENTS_FORMATTER,

#             "width": 105,
#             "minWidth": 105,

#             "cellStyle": DOCUMENTS_STYLE,

#             "sortable": True,

#             "filter": "agNumberColumnFilter",
#         },

#         # =============================================================
#         # Тип / валюта
#         # =============================================================

#         {
#             "field": "contract_type",
#             "headerName": "Тип",

#             "minWidth": 165,
#         },

#         {
#             "field": "currency",
#             "headerName": "Валюта",

#             "width": 90,
#             "minWidth": 90,

#             "cellStyle": {
#                 "textAlign": "center",
#                 "fontWeight": "600",
#             },
#         },

#         # =============================================================
#         # Суммы
#         # =============================================================

#         {
#             "field": "contract_amount",
#             "headerName": "Сумма договора",

#             "valueFormatter": MONEY_FORMATTER,

#             "type": "rightAligned",

#             "cellStyle": MONEY_CELL_STYLE,

#             "minWidth": 150,
#         },

#         {
#             "field": "total_drawdown",
#             "headerName": "Выдано / привлечено",

#             "valueFormatter": MONEY_FORMATTER,

#             "type": "rightAligned",

#             "cellStyle": MONEY_CELL_STYLE,

#             "minWidth": 165,
#         },

#         {
#             "field": "total_repaid",
#             "headerName": "Погашено",

#             "valueFormatter": MONEY_FORMATTER,

#             "type": "rightAligned",

#             "cellStyle": {
#                 **MONEY_CELL_STYLE,
#                 "color": COLORS["dark_green"],
#             },

#             "minWidth": 140,
#         },

#         {
#             "field": "ending_balance",
#             "headerName": "Основной долг",

#             "valueFormatter": MONEY_FORMATTER,

#             "type": "rightAligned",

#             "cellStyle": {
#                 **BOLD_MONEY_STYLE,
#                 "backgroundColor": COLORS[
#                     "very_light_green"
#                 ],
#             },

#             "minWidth": 150,
#         },

#         {
#             "field": "interest_balance",
#             "headerName": "Долг по процентам",

#             "valueFormatter": MONEY_FORMATTER,

#             "type": "rightAligned",

#             "cellStyle": {
#                 **MONEY_CELL_STYLE,
#                 "backgroundColor": COLORS[
#                     "light_orange"
#                 ],
#             },

#             "minWidth": 160,
#         },

#         {
#             "field": "total_debt",
#             "headerName": "Общий долг",

#             "valueFormatter": MONEY_FORMATTER,

#             "type": "rightAligned",

#             "cellStyle": {
#                 **BOLD_MONEY_STYLE,
#                 "backgroundColor": COLORS[
#                     "light_green"
#                 ],
#                 "color": COLORS["dark_green"],
#             },

#             "minWidth": 155,
#         },

#         # =============================================================
#         # Ставки
#         # =============================================================

#         {
#             "field": "rate",
#             "headerName": "Ставка",

#             "valueFormatter": PERCENT_FORMATTER,

#             "type": "rightAligned",

#             "cellStyle": RIGHT_CELL_STYLE,

#             "minWidth": 105,
#         },

#         # =============================================================
#         # Погашение
#         # =============================================================

#         {
#             "field": "repayment_date",
#             "headerName": "Дата погашения",

#             "valueFormatter": DATE_FORMATTER,

#             "cellStyle": MATURITY_DATE_STYLE,

#             "minWidth": 135,
#         },

#         {
#             "field": "days_to_maturity",
#             "headerName": "Дней до погашения",

#             "valueFormatter": INTEGER_FORMATTER,

#             "type": "rightAligned",

#             "cellStyle": DAYS_STYLE,

#             "minWidth": 140,
#         },

#         {
#             "field": "repayment_profile",
#             "headerName": "Профиль погашения",

#             "minWidth": 165,
#         },

#         {
#             "field": "compounding",
#             "headerName": "Компаундинг",

#             "valueFormatter": BOOLEAN_FORMATTER,

#             "width": 120,
#             "minWidth": 120,

#             "cellStyle": {
#                 "textAlign": "center",
#             },
#         },

#         {
#             "field": "penalty_rate",
#             "headerName": "Штрафная ставка",

#             "valueFormatter": PERCENT_FORMATTER,

#             "type": "rightAligned",

#             "cellStyle": RIGHT_CELL_STYLE,

#             "minWidth": 140,
#         },

#         # =============================================================
#         # Служебное
#         # =============================================================

#         {
#             "field": "inn",
#             "headerName": "ИНН",

#             "minWidth": 125,
#         },

#         {
#             "field": "contract_id",
#             "headerName": "ID договора",

#             "valueFormatter": INTEGER_FORMATTER,

#             "minWidth": 105,

#             "hide": True,
#         },
#     ]


# # =====================================================================
# # TRANSACTIONS GRID
# # =====================================================================


# def transactions_column_defs():
#     return [
#         {
#             "field": "date_from",
#             "headerName": "Дата",

#             "valueFormatter": DATE_FORMATTER,

#             "pinned": "left",

#             "width": 120,
#             "minWidth": 120,

#             "cellStyle": {
#                 "fontWeight": "600",
#             },
#         },

#         {
#             "field": "operation_description",
#             "headerName": "Операция",

#             "minWidth": 220,
#             "flex": 1.2,
#         },

#         {
#             "field": "interest_description",
#             "headerName": "Описание процентов",

#             "minWidth": 220,
#             "flex": 1.1,
#         },

#         {
#             "field": "drawdown_amount",
#             "headerName": "Выдача / привлечение",

#             "valueFormatter": MONEY_FORMATTER,

#             "type": "rightAligned",

#             "cellStyle": {
#                 **MONEY_CELL_STYLE,
#                 "backgroundColor": COLORS[
#                     "light_blue"
#                 ],
#             },

#             "minWidth": 160,
#         },

#         {
#             "field": "principal_repayment",
#             "headerName": "Погашение тела",

#             "valueFormatter": MONEY_FORMATTER,

#             "type": "rightAligned",

#             "cellStyle": {
#                 **MONEY_CELL_STYLE,
#                 "backgroundColor": COLORS[
#                     "very_light_green"
#                 ],
#             },

#             "minWidth": 150,
#         },

#         {
#             "field": "interest_accrued",
#             "headerName": "Начислено процентов",

#             "valueFormatter": MONEY_FORMATTER,

#             "type": "rightAligned",

#             "cellStyle": {
#                 **MONEY_CELL_STYLE,
#                 "backgroundColor": COLORS[
#                     "light_orange"
#                 ],
#             },

#             "minWidth": 160,
#         },

#         {
#             "field": "interest_repayment",
#             "headerName": "Погашено процентов",

#             "valueFormatter": MONEY_FORMATTER,

#             "type": "rightAligned",

#             "cellStyle": {
#                 **MONEY_CELL_STYLE,
#                 "backgroundColor": COLORS[
#                     "very_light_green"
#                 ],
#             },

#             "minWidth": 160,
#         },

#         {
#             "field": "ending_balance",
#             "headerName": "Основной долг",

#             "valueFormatter": MONEY_FORMATTER,

#             "type": "rightAligned",

#             "cellStyle": BOLD_MONEY_STYLE,

#             "minWidth": 150,
#         },

#         {
#             "field": "interest_balance",
#             "headerName": "Проценты к оплате",

#             "valueFormatter": MONEY_FORMATTER,

#             "type": "rightAligned",

#             "cellStyle": MONEY_CELL_STYLE,

#             "minWidth": 150,
#         },

#         {
#             "field": "total_debt",
#             "headerName": "Общий долг",

#             "valueFormatter": MONEY_FORMATTER,

#             "type": "rightAligned",

#             "cellStyle": {
#                 **BOLD_MONEY_STYLE,
#                 "backgroundColor": COLORS[
#                     "light_green"
#                 ],
#                 "color": COLORS["dark_green"],
#             },

#             "minWidth": 150,
#         },

#         {
#             "field": "rate",
#             "headerName": "Ставка",

#             "valueFormatter": PERCENT_FORMATTER,

#             "type": "rightAligned",

#             "cellStyle": RIGHT_CELL_STYLE,

#             "minWidth": 105,
#         },
#     ]


# # =====================================================================
# # BUILD MAIN GRID
# # =====================================================================


# def build_loans_grid():
#     return dag.AgGrid(
#         id=LOANS_GRID_ID,

#         columnDefs=loans_column_defs(),
#         dangerously_allow_code=True,

#         rowData=[],

#         defaultColDef=DEFAULT_COL_DEF,

#         dashGridOptions={
#             # =====================================================
#             # Pagination
#             # =====================================================

#             "pagination": True,

#             "paginationPageSize": PAGE_SIZE,

#             "paginationPageSizeSelector": [
#                 25,
#                 50,
#                 100,
#                 250,
#             ],

#             # =====================================================
#             # Checkbox — отдельная первая колонка
#             # =====================================================

#             "rowSelection": {
#                 "mode": "singleRow",

#                 "checkboxes": True,

#                 "headerCheckbox": False,

#                 # Клик по строке НЕ выбирает её.
#                 # Только checkbox.
#                 "enableClickSelection": False,
#             },

#             # Оформление автоматически создаваемой
#             # selection-колонки.
#             "selectionColumnDef": {
#                 "pinned": "left",

#                 "width": 46,
#                 "minWidth": 46,
#                 "maxWidth": 46,

#                 "resizable": False,
#                 "sortable": False,

#                 "suppressHeaderMenuButton": True,
#             },

#             # =====================================================
#             # Поведение
#             # =====================================================

#             "animateRows": False,

#             "suppressCellFocus": True,

#             "rowHeight": 38,

#             "headerHeight": 42,

#             "ensureDomOrder": True,
#         },

#         style={
#             "height": "620px",
#             "width": "100%",
#         },

#         className="ag-theme-quartz",
#     )


# # =====================================================================
# # BUILD TRANSACTIONS GRID
# # =====================================================================


# def build_transactions_grid():
#     return dag.AgGrid(
#         id=TRANSACTIONS_GRID_ID,

#         columnDefs=transactions_column_defs(),
#         dangerously_allow_code=True,

#         rowData=[],

#         defaultColDef=DEFAULT_COL_DEF,

#         dashGridOptions={
#             "pagination": True,

#             "paginationPageSize": 50,

#             "paginationPageSizeSelector": [
#                 25,
#                 50,
#                 100,
#                 250,
#             ],

#             "animateRows": False,

#             "suppressCellFocus": True,

#             "rowHeight": 38,

#             "headerHeight": 42,

#             "ensureDomOrder": True,
#         },

#         style={
#             "height": "500px",
#             "width": "100%",
#         },

#         className="ag-theme-quartz",
#     )




# gear/app/loans/grid.py

from __future__ import annotations

import dash_ag_grid as dag

from .config import COLORS, PAGE_SIZE
from .ids import (
    LOANS_GRID_ID,
    TRANSACTIONS_GRID_ID,
)


# =====================================================================
# FORMATTERS
# =====================================================================

MONEY_FORMATTER = {
    "function": """
    params.value == null
        ? ''
        : d3.format(',.2f')(params.value)
            .replaceAll(',', ' ')
    """
}


INTEGER_FORMATTER = {
    "function": """
    params.value == null
        ? ''
        : d3.format(',.0f')(params.value)
            .replaceAll(',', ' ')
    """
}


PERCENT_FORMATTER = {
    "function": """
    params.value == null
        ? ''
        : d3.format(',.2f')(params.value)
            .replaceAll(',', ' ') + ' %'
    """
}


DATE_FORMATTER = {
    "function": """
    if (
        params.value === null
        || params.value === undefined
        || params.value === ''
    ) {
        return '';
    }

    const value = String(params.value).slice(0, 10);
    const parts = value.split('-');

    if (parts.length !== 3) {
        return value;
    }

    return `${parts[2]}.${parts[1]}.${parts[0]}`;
    """
}


BOOLEAN_FORMATTER = {
    "function": """
    if (
        params.value === null
        || params.value === undefined
    ) {
        return '';
    }

    return params.value ? 'Да' : 'Нет';
    """
}


DOCUMENTS_FORMATTER = {
    "function": """
    if (
        params.value === null
        || params.value === undefined
        || Number(params.value) === 0
    ) {
        return '—';
    }

    return '📎 ' + d3.format(',.0f')(params.value)
        .replaceAll(',', ' ');
    """
}






# =====================================================================
# COMMON STYLES
# =====================================================================


RIGHT_CELL_STYLE = {
    "textAlign": "right",
    "fontVariantNumeric": "tabular-nums",
}


MONEY_CELL_STYLE = {
    "textAlign": "right",
    "fontVariantNumeric": "tabular-nums",
    "color": COLORS["text"],
}


BOLD_MONEY_STYLE = {
    "textAlign": "right",
    "fontVariantNumeric": "tabular-nums",
    "fontWeight": "600",
    "color": COLORS["text"],
}


STATUS_CELL_STYLE = {
    "styleConditions": [
        {
            "condition": (
                "params.value === 'Просрочен'"
            ),
            "style": {
                "backgroundColor": COLORS["light_red"],
                "color": COLORS["red"],
                "fontWeight": "600",
            },
        },
        {
            "condition": (
                "params.value === "
                "'Погашение ≤ 30 дней'"
            ),
            "style": {
                "backgroundColor": COLORS["light_orange"],
                "color": COLORS["orange"],
                "fontWeight": "600",
            },
        },
        {
            "condition": (
                "params.value === 'Активен'"
            ),
            "style": {
                "backgroundColor": COLORS["very_light_green"],
                "color": COLORS["dark_green"],
                "fontWeight": "600",
            },
        },
        {
            "condition": (
                "params.value === 'Погашен'"
            ),
            "style": {
                "backgroundColor": COLORS["light_gray"],
                "color": COLORS["gray"],
                "fontWeight": "500",
            },
        },
    ]
}


MATURITY_DATE_STYLE = {
    "styleConditions": [
        {
            "condition": (
                "params.data && "
                "params.data.days_to_maturity < 0 && "
                "params.data.total_debt > 0.01"
            ),
            "style": {
                "backgroundColor": COLORS["light_red"],
                "color": COLORS["red"],
                "fontWeight": "600",
            },
        },
        {
            "condition": (
                "params.data && "
                "params.data.days_to_maturity >= 0 && "
                "params.data.days_to_maturity <= 30 && "
                "params.data.total_debt > 0.01"
            ),
            "style": {
                "backgroundColor": COLORS["light_orange"],
                "color": COLORS["orange"],
                "fontWeight": "600",
            },
        },
    ]
}


DAYS_STYLE = {
    "styleConditions": [
        {
            "condition": (
                "params.value < 0"
            ),
            "style": {
                "color": COLORS["red"],
                "fontWeight": "700",
                "textAlign": "right",
            },
        },
        {
            "condition": (
                "params.value >= 0 && "
                "params.value <= 30"
            ),
            "style": {
                "color": COLORS["orange"],
                "fontWeight": "700",
                "textAlign": "right",
            },
        },
    ]
}


DOCUMENTS_STYLE = {
    "styleConditions": [
        {
            "condition": (
                "Number(params.value) > 0"
            ),
            "style": {
                "backgroundColor": COLORS["very_light_green"],
                "color": COLORS["dark_green"],
                "fontWeight": "600",
                "textAlign": "center",
            },
        },
    ]
}


# =====================================================================
# DEFAULT COLUMN
# =====================================================================


DEFAULT_COL_DEF = {
    "sortable": True,
    "filter": True,
    "resizable": True,

    "minWidth": 105,

    "wrapHeaderText": True,
    "autoHeaderHeight": True,

    "suppressHeaderMenuButton": True,

    "cellDataType": False,
}


# =====================================================================
# LOANS GRID
# =====================================================================


def loans_column_defs():
    return [
        # =============================================================
        # Статус
        # =============================================================

        {
            "field": "status",
            "headerName": "Статус",

            "pinned": "left",

            "width": 145,
            "minWidth": 145,

            "cellStyle": STATUS_CELL_STYLE,
        },

        # =============================================================
        # Контрагент
        # =============================================================

        {
            "field": "counterparty_name",
            "headerName": "Контрагент",

            "pinned": "left",

            "minWidth": 245,
            "flex": 1.35,

            "cellStyle": {
                "fontWeight": "600",
                "color": COLORS["text"],
            },
        },

        # =============================================================
        # Договор
        # =============================================================

        {
            "field": "contract_number",
            "headerName": "Договор",

            "minWidth": 130,

            "cellStyle": {
                "fontWeight": "500",
            },
        },

        {
            "field": "contract_date",
            "headerName": "Дата договора",

            "valueFormatter": DATE_FORMATTER,

            "minWidth": 125,
        },

        # =============================================================
        # Документы
        # =============================================================

        {
            "field": "documents_count",
            "headerName": "Документы",

            "valueFormatter": DOCUMENTS_FORMATTER,

            "width": 105,
            "minWidth": 105,

            "cellStyle": DOCUMENTS_STYLE,

            "sortable": True,

            "filter": "agNumberColumnFilter",
        },

        # =============================================================
        # Тип / валюта
        # =============================================================

        {
            "field": "contract_type",
            "headerName": "Тип",

            "minWidth": 165,
        },

        {
            "field": "loan_direction_label",
            "headerName": "Направление",
            "minWidth": 175,
            "cellStyle": {
                "fontWeight": "600",
                "color": COLORS["dark"],
            },
        },

        {
            "field": "currency",
            "headerName": "Валюта",

            "width": 90,
            "minWidth": 90,

            "cellStyle": {
                "textAlign": "center",
                "fontWeight": "600",
            },
        },

        # =============================================================
        # Суммы
        # =============================================================

        {
            "field": "contract_amount",
            "headerName": "Сумма договора",

            "valueFormatter": MONEY_FORMATTER,

            "type": "rightAligned",

            "cellStyle": MONEY_CELL_STYLE,

            "minWidth": 150,
        },

        {
            "field": "total_drawdown",
            "headerName": "Выдано / привлечено",

            "valueFormatter": MONEY_FORMATTER,

            "type": "rightAligned",

            "cellStyle": MONEY_CELL_STYLE,

            "minWidth": 165,
        },

        {
            "field": "total_repaid",
            "headerName": "Погашено",

            "valueFormatter": MONEY_FORMATTER,

            "type": "rightAligned",

            "cellStyle": {
                **MONEY_CELL_STYLE,
                "color": COLORS["dark_green"],
            },

            "minWidth": 140,
        },

        {
            "field": "ending_balance",
            "headerName": "Основной долг",

            "valueFormatter": MONEY_FORMATTER,

            "type": "rightAligned",

            "cellStyle": {
                **BOLD_MONEY_STYLE,
                "backgroundColor": COLORS[
                    "very_light_green"
                ],
            },

            "minWidth": 150,
        },

        {
            "field": "interest_balance",
            "headerName": "Долг по процентам",

            "valueFormatter": MONEY_FORMATTER,

            "type": "rightAligned",

            "cellStyle": {
                **MONEY_CELL_STYLE,
                "backgroundColor": COLORS[
                    "light_orange"
                ],
            },

            "minWidth": 160,
        },

        {
            "field": "total_debt",
            "headerName": "Общий долг",

            "valueFormatter": MONEY_FORMATTER,

            "type": "rightAligned",

            "cellStyle": {
                **BOLD_MONEY_STYLE,
                "backgroundColor": COLORS[
                    "light_green"
                ],
                "color": COLORS["dark_green"],
            },

            "minWidth": 155,
        },

        # =============================================================
        # Ставки
        # =============================================================

        {
            "field": "rate",
            "headerName": "Ставка",

            "valueFormatter": PERCENT_FORMATTER,

            "type": "rightAligned",

            "cellStyle": RIGHT_CELL_STYLE,

            "minWidth": 105,
        },

        # =============================================================
        # Погашение
        # =============================================================

        {
            "field": "repayment_date",
            "headerName": "Дата погашения",

            "valueFormatter": DATE_FORMATTER,

            "cellStyle": MATURITY_DATE_STYLE,

            "minWidth": 135,
        },

        {
            "field": "days_to_maturity",
            "headerName": "Дней до погашения",

            "valueFormatter": INTEGER_FORMATTER,

            "type": "rightAligned",

            "cellStyle": DAYS_STYLE,

            "minWidth": 140,
        },

        {
            "field": "repayment_profile",
            "headerName": "Профиль погашения",

            "minWidth": 165,
        },

        {
            "field": "compounding",
            "headerName": "Компаундинг",

            "valueFormatter": BOOLEAN_FORMATTER,

            "width": 120,
            "minWidth": 120,

            "cellStyle": {
                "textAlign": "center",
            },
        },

        {
            "field": "penalty_rate",
            "headerName": "Штрафная ставка",

            "valueFormatter": PERCENT_FORMATTER,

            "type": "rightAligned",

            "cellStyle": RIGHT_CELL_STYLE,

            "minWidth": 140,
        },

        # =============================================================
        # Служебное
        # =============================================================

        {
            "field": "inn",
            "headerName": "ИНН",

            "minWidth": 125,
        },

        {
            "field": "contract_id",
            "headerName": "ID договора",

            "valueFormatter": INTEGER_FORMATTER,

            "minWidth": 105,

            "hide": True,
        },
    ]


# =====================================================================
# TRANSACTIONS GRID
# =====================================================================


def transactions_column_defs():
    return [
        {
            "field": "date_from",
            "headerName": "Дата",

            "valueFormatter": DATE_FORMATTER,

            "pinned": "left",

            "width": 120,
            "minWidth": 120,

            "cellStyle": {
                "fontWeight": "600",
            },
        },

        {
            "field": "operation_description",
            "headerName": "Операция",

            "minWidth": 220,
            "flex": 1.2,
        },

        {
            "field": "interest_description",
            "headerName": "Описание процентов",

            "minWidth": 220,
            "flex": 1.1,
        },

        {
            "field": "drawdown_amount",
            "headerName": "Выдача / привлечение",

            "valueFormatter": MONEY_FORMATTER,

            "type": "rightAligned",

            "cellStyle": {
                **MONEY_CELL_STYLE,
                "backgroundColor": COLORS[
                    "light_blue"
                ],
            },

            "minWidth": 160,
        },

        {
            "field": "principal_repayment",
            "headerName": "Погашение тела",

            "valueFormatter": MONEY_FORMATTER,

            "type": "rightAligned",

            "cellStyle": {
                **MONEY_CELL_STYLE,
                "backgroundColor": COLORS[
                    "very_light_green"
                ],
            },

            "minWidth": 150,
        },

        {
            "field": "interest_accrued",
            "headerName": "Начислено процентов",

            "valueFormatter": MONEY_FORMATTER,

            "type": "rightAligned",

            "cellStyle": {
                **MONEY_CELL_STYLE,
                "backgroundColor": COLORS[
                    "light_orange"
                ],
            },

            "minWidth": 160,
        },

        {
            "field": "interest_repayment",
            "headerName": "Погашено процентов",

            "valueFormatter": MONEY_FORMATTER,

            "type": "rightAligned",

            "cellStyle": {
                **MONEY_CELL_STYLE,
                "backgroundColor": COLORS[
                    "very_light_green"
                ],
            },

            "minWidth": 160,
        },

        {
            "field": "ending_balance",
            "headerName": "Основной долг",

            "valueFormatter": MONEY_FORMATTER,

            "type": "rightAligned",

            "cellStyle": BOLD_MONEY_STYLE,

            "minWidth": 150,
        },

        {
            "field": "interest_balance",
            "headerName": "Проценты к оплате",

            "valueFormatter": MONEY_FORMATTER,

            "type": "rightAligned",

            "cellStyle": MONEY_CELL_STYLE,

            "minWidth": 150,
        },

        {
            "field": "total_debt",
            "headerName": "Общий долг",

            "valueFormatter": MONEY_FORMATTER,

            "type": "rightAligned",

            "cellStyle": {
                **BOLD_MONEY_STYLE,
                "backgroundColor": COLORS[
                    "light_green"
                ],
                "color": COLORS["dark_green"],
            },

            "minWidth": 150,
        },

        {
            "field": "rate",
            "headerName": "Ставка",

            "valueFormatter": PERCENT_FORMATTER,

            "type": "rightAligned",

            "cellStyle": RIGHT_CELL_STYLE,

            "minWidth": 105,
        },
    ]


# =====================================================================
# BUILD MAIN GRID
# =====================================================================


def build_loans_grid():
    return dag.AgGrid(
        id=LOANS_GRID_ID,

        columnDefs=loans_column_defs(),
        dangerously_allow_code=True,

        rowData=[],

        defaultColDef=DEFAULT_COL_DEF,

        dashGridOptions={
            # =====================================================
            # Pagination
            # =====================================================

            "pagination": True,

            "paginationPageSize": PAGE_SIZE,

            "paginationPageSizeSelector": [
                25,
                50,
                100,
                250,
            ],

            # =====================================================
            # Checkbox — отдельная первая колонка
            # =====================================================

            "rowSelection": {
                "mode": "singleRow",

                "checkboxes": True,

                "headerCheckbox": False,

                # Клик по строке НЕ выбирает её.
                # Только checkbox.
                "enableClickSelection": False,
            },

            # Оформление автоматически создаваемой
            # selection-колонки.
            "selectionColumnDef": {
                "pinned": "left",

                "width": 46,
                "minWidth": 46,
                "maxWidth": 46,

                "resizable": False,
                "sortable": False,

                "suppressHeaderMenuButton": True,
            },

            # =====================================================
            # Поведение
            # =====================================================

            "animateRows": False,

            "suppressCellFocus": True,

            "rowHeight": 38,

            "headerHeight": 42,

            "ensureDomOrder": True,
        },

        style={
            "height": "620px",
            "width": "100%",
        },

        className="ag-theme-quartz",
    )


# =====================================================================
# BUILD TRANSACTIONS GRID
# =====================================================================


def build_transactions_grid():
    return dag.AgGrid(
        id=TRANSACTIONS_GRID_ID,

        columnDefs=transactions_column_defs(),
        dangerously_allow_code=True,

        rowData=[],

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

            "suppressCellFocus": True,

            "rowHeight": 38,

            "headerHeight": 42,

            "ensureDomOrder": True,
        },

        style={
            "height": "500px",
            "width": "100%",
        },

        className="ag-theme-quartz",
    )
