# gear/app/daily_sales/pricing_strategy/grids.py

from __future__ import annotations

import dash_ag_grid as dag

from .theme import (
    DANGER,
    DANGER_SOFT,
    MUTED,
    PRIMARY,
    PRIMARY_SOFT,
    SUBTLE,
    SUCCESS,
    WARNING,
    WARNING_SOFT,
)


# ============================================================
# FORMATTERS
# ============================================================

MONEY_FORMATTER = {
    "function": """
    params.value == null
        ? ''
        : d3.format(',.0f')(params.value)
            .replaceAll(',', ' ') + ' ₽'
    """
}

INT_FORMATTER = {
    "function": """
    params.value == null
        ? ''
        : d3.format(',.0f')(params.value)
            .replaceAll(',', ' ')
    """
}

ONE_DECIMAL_FORMATTER = {
    "function": """
    params.value == null
        ? ''
        : d3.format(',.1f')(params.value)
            .replaceAll(',', ' ')
    """
}

TWO_DECIMAL_FORMATTER = {
    "function": """
    params.value == null
        ? ''
        : d3.format(',.2f')(params.value)
            .replaceAll(',', ' ')
    """
}

PERCENT_FORMATTER = {
    "function": """
    params.value == null
        ? ''
        : d3.format(',.1f')(params.value)
            .replaceAll(',', ' ') + ' %'
    """
}

PERCENT_INT_FORMATTER = {
    "function": """
    params.value == null
        ? ''
        : d3.format(',.0f')(params.value)
            .replaceAll(',', ' ') + ' %'
    """
}

SIGNED_PERCENT_FORMATTER = {
    "function": """
    params.value == null
        ? ''
        : (
            Number(params.value) > 0
                ? '+' + d3.format(',.0f')(Number(params.value)) + '%'
                : d3.format(',.0f')(Number(params.value)) + '%'
        )
    """
}



STATUS_FORMATTER = {
    "function": """
        params.value == null
        ? ''
        : (
            params.value === 'LOSS'
                ? 'Убыток'
                : params.value === 'CLEARANCE'
                ? 'Распродажа'
                : params.value === 'REDUCE'
                    ? 'Снизить цену'
                    : params.value === 'RAISE'
                        ? 'Повысить цену'
                        : params.value === 'TEST'
                            ? 'Тест цены'
                            : params.value === 'HOLD'
                                ? 'Оставить цену'
                                : params.value
        )
    """
}

PRIORITY_FORMATTER = {
    "function": """
    if (params.value == null) return '';

    const value = Number(params.value);

    if (!Number.isFinite(value)) return '';

    if (value >= 120) return 'Критический';
    if (value >= 90) return 'Высокий';
    if (value >= 60) return 'Средний';

    return 'Низкий';
    """
}


# ============================================================
# COLUMN HELPERS
# ============================================================

def _text_col(
    field,
    header,
    width=140,
    *,
    pinned=False,
    cell_style=None,
    flex=None,
    min_width=None,
    value_formatter=None,
):
    column = {
        "field": field,
        "headerName": header,
        "width": width,
        "cellStyle": cell_style or {},
    }

    if pinned:
        column["pinned"] = "left"
        column["lockPinned"] = True

    if flex is not None:
        column["flex"] = flex

    if min_width is not None:
        column["minWidth"] = min_width

    if value_formatter is not None:
        column["valueFormatter"] = value_formatter

    return column


def _int_col(
    field,
    header,
    width=110,
    *,
    pinned=False,
    cell_style=None,
    value_formatter=None,
):
    column = {
        "field": field,
        "headerName": header,
        "width": width,
        "type": "numericColumn",
        "valueFormatter": (
            value_formatter
            if value_formatter is not None
            else INT_FORMATTER
        ),
        "cellStyle": cell_style or {},
    }

    if pinned:
        column["pinned"] = "left"
        column["lockPinned"] = True

    return column


def _number_col(
    field,
    header,
    width=110,
    *,
    digits=1,
    cell_style=None,
    value_formatter=None,
):
    formatter = {
        0: INT_FORMATTER,
        1: ONE_DECIMAL_FORMATTER,
        2: TWO_DECIMAL_FORMATTER,
    }.get(
        digits,
        TWO_DECIMAL_FORMATTER,
    )

    return {
        "field": field,
        "headerName": header,
        "width": width,
        "type": "numericColumn",
        "valueFormatter": (
            value_formatter
            if value_formatter is not None
            else formatter
        ),
        "cellStyle": cell_style or {},
    }


def _money_col(
    field,
    header,
    width=135,
    *,
    cell_style=None,
):
    return {
        "field": field,
        "headerName": header,
        "width": width,
        "type": "numericColumn",
        "valueFormatter": MONEY_FORMATTER,
        "cellStyle": cell_style or {},
    }


def _percent_col(
    field,
    header,
    width=105,
    *,
    digits=1,
    cell_style=None,
    signed=False,
):
    formatter = (
        SIGNED_PERCENT_FORMATTER
        if signed
        else (
            PERCENT_FORMATTER
            if digits == 1
            else PERCENT_INT_FORMATTER
        )
    )

    return {
        "field": field,
        "headerName": header,
        "width": width,
        "type": "numericColumn",
        "valueFormatter": formatter,
        "cellStyle": cell_style or {},
    }


# ============================================================
# BASE GRID
# ============================================================

def _base_grid(
    *,
    row_data,
    column_defs,
    grid_id,
    height,
    page_size,
    page_sizes=None,
):
    options = {
        "pagination": True,
        "paginationPageSize": page_size,
        "animateRows": False,
        "enableCellTextSelection": True,
        "ensureDomOrder": True,

        "rowHeight": 36,

        # Две строки заголовка:
        # 1-я — смысловой блок;
        # 2-я — конкретная колонка.
        "groupHeaderHeight": 34,
        "headerHeight": 44,

        "rowSelection": "single",
    }

    if page_sizes:
        options[
            "paginationPageSizeSelector"
        ] = page_sizes

    return dag.AgGrid(
        id=grid_id,
        rowData=row_data,
        columnDefs=column_defs,

        # Нужен для JS formatter/style functions.
        dangerously_allow_code=True,

        defaultColDef={
            "sortable": True,
            "filter": True,
            "resizable": True,
            "editable": False,
            "floatingFilter": False,
            "cellStyle": {
                "fontSize": "12px",
                "lineHeight": "1.25",
            },
        },

        dashGridOptions=options,

        style={
            "height": height,
            "width": "100%",
        },

        className=(
            "ag-theme-alpine "
            "compact-grid"
        ),
    )


# ============================================================
# STYLES
# ============================================================

# ============================================================
# ПОДСВЕТКА
#
# Правило одно: цветом отмечаем только то, что требует
# решения. Раньше была окрашена почти каждая колонка, и
# таблица рябила — глазу не за что зацепиться.
#
# Насыщенный цвет идёт в текст, очень светлый — в фон.
# Белым по красному в плотной таблице читать тяжело.
# ============================================================

def _js(body):
    return {"function": body}


def _stock_days_style():
    """Запас в днях: красим только избыточный."""

    return _js(
        f"""
        const value = Number(params.value);

        if (!Number.isFinite(value)) return {{}};

        if (value >= 365) {{
            return {{
                backgroundColor: '{DANGER_SOFT}',
                color: '{DANGER}',
                fontWeight: '700'
            }};
        }}

        if (value >= 180) {{
            return {{
                backgroundColor: '{WARNING_SOFT}',
                color: '{WARNING}',
                fontWeight: '600'
            }};
        }}

        return {{}};
        """
    )


def _status_style():
    """Статус — единственная колонка с постоянной заливкой."""

    return _js(
        f"""
        const value = params.value;

        const map = {{
            'LOSS':      ['{DANGER_SOFT}', '{DANGER}'],
            'CLEARANCE': ['{WARNING_SOFT}', '{WARNING}'],
            'REDUCE':    ['{WARNING_SOFT}', '{WARNING}'],
            'RAISE':     ['#ECFDF3', '{SUCCESS}'],
            'TEST':      ['{SUBTLE}', '#0E7490'],
            'HOLD':      ['{SUBTLE}', '{MUTED}']
        }};

        const pair = map[value];

        if (!pair) return {{}};

        return {{
            backgroundColor: pair[0],
            color: pair[1],
            fontWeight: '700'
        }};
        """
    )


def _priority_style():
    """Приоритет: без заливки, только насыщенность текста."""

    return _js(
        f"""
        const value = Number(params.value);

        if (!Number.isFinite(value)) return {{}};

        if (value >= 120) {{
            return {{color: '{DANGER}', fontWeight: '700'}};
        }}

        if (value >= 90) {{
            return {{color: '{WARNING}', fontWeight: '700'}};
        }}

        if (value >= 60) {{
            return {{color: '#0E7490', fontWeight: '600'}};
        }}

        return {{color: '{MUTED}'}};
        """
    )


def _price_change_style():
    """Направление изменения цены: цветом текста."""

    return _js(
        f"""
        const value = Number(params.value);

        if (!Number.isFinite(value)) return {{}};

        if (value < 0) {{
            return {{color: '{WARNING}', fontWeight: '700'}};
        }}

        if (value > 0) {{
            return {{color: '{SUCCESS}', fontWeight: '700'}};
        }}

        return {{color: '{MUTED}'}};
        """
    )


def _wb_discount_style():
    """Скидка WB — справочная величина, красить нечего."""

    return None


def _margin_value_style():
    return _js(
        f"""
        const value = Number(params.value);

        if (!Number.isFinite(value)) return {{}};

        if (value < 0) {{
            return {{
                backgroundColor: '{DANGER_SOFT}',
                color: '{DANGER}',
                fontWeight: '700'
            }};
        }}

        return {{}};
        """
    )


def _margin_pct_style():
    return _js(
        f"""
        const value = Number(params.value);

        if (!Number.isFinite(value)) return {{}};

        if (value < 0) {{
            return {{color: '{DANGER}', fontWeight: '700'}};
        }}

        if (value < 10) {{
            return {{color: '{WARNING}', fontWeight: '600'}};
        }}

        return {{}};
        """
    )


def _trend_style():
    return _js(
        f"""
        const value = Number(params.value);

        if (!Number.isFinite(value)) return {{}};

        if (value <= -20) {{
            return {{color: '{DANGER}', fontWeight: '600'}};
        }}

        if (value >= 20) {{
            return {{color: '{SUCCESS}', fontWeight: '600'}};
        }}

        return {{}};
        """
    )


def _headroom_style():
    """
    Запас по скидке до точки безубыточности.
    Минус — продаём в убыток, тут полутонов быть не может.
    """

    return _js(
        f"""
        const value = Number(params.value);

        if (!Number.isFinite(value)) return {{}};

        if (value < 0) {{
            return {{
                backgroundColor: '{DANGER_SOFT}',
                color: '{DANGER}',
                fontWeight: '700'
            }};
        }}

        if (value < 10) {{
            return {{color: '{WARNING}', fontWeight: '700'}};
        }}

        return {{}};
        """
    )


def _floor_price_style():
    """Минимальная цена — опорная колонка отчёта."""

    return _js(
        f"""
        if (params.value == null) {{
            return {{color: '{MUTED}'}};
        }}

        return {{
            color: '{DANGER}',
            fontWeight: '700'
        }};
        """
    )


def _action_price_style():
    """Цена к установке — то, что мы предлагаем сделать."""

    return _js(
        f"""
        if (params.value == null) return {{}};

        return {{
            backgroundColor: '{PRIMARY_SOFT}',
            color: '{PRIMARY}',
            fontWeight: '700'
        }};
        """
    )


def _cost_style():
    """
    Себестоимость: подсвечиваем, если текущая цена
    опустилась ниже неё. Сравнение делаем прямо в ячейке,
    поэтому колонка знает про соседнюю.
    """

    return _js(
        f"""
        const cost = Number(params.value);

        if (!Number.isFinite(cost) || cost <= 0) {{
            return {{color: '{MUTED}'}};
        }}

        const price = Number(
            params.data ? params.data.current_effective_price : null
        );

        if (Number.isFinite(price) && price > 0 && price < cost) {{
            return {{
                backgroundColor: '{DANGER_SOFT}',
                color: '{DANGER}',
                fontWeight: '700'
            }};
        }}

        return {{}};
        """
    )


def _ratios_source_style():
    """Оценка по медиане — не факт, это должно быть видно."""

    return _js(
        f"""
        const value = params.value;

        if (value === 'Свои продажи') {{
            return {{color: '{MUTED}'}};
        }}

        return {{
            color: '{WARNING}',
            fontStyle: 'italic'
        }};
        """
    )


def _risk_value_style():
    return _js(
        f"""
        const value = Number(params.value);

        if (!Number.isFinite(value) || value <= 0) {{
            return {{color: '{MUTED}'}};
        }}

        return {{
            backgroundColor: '{DANGER_SOFT}',
            color: '{DANGER}',
            fontWeight: '700'
        }};
        """
    )


# ============================================================
# 1. BRAND × CATEGORY
# ============================================================

def _portfolio_columns():
    return [
        _text_col(
            "brand",
            "Бренд",
            155,
            pinned=True,
            cell_style={
                "backgroundColor": "#F8FAFC",
                "fontWeight": "700",
            },
        ),

        _text_col(
            "category",
            "Категория",
            205,
            pinned=True,
            cell_style={
                "backgroundColor": "#F8FAFC",
                "borderRight": "1px solid #E5E7EB",
            },
        ),

        _int_col(
            "products",
            "Артикулов",
            105,
        ),

        _int_col(
            "action_products",
            "Требуют действия",
            135,
            cell_style={
                "fontWeight": "700",
            },
        ),

        _int_col(
            "stock_units",
            "Остаток всего",
            125,
            cell_style={
                "fontWeight": "700",
            },
        ),

        _int_col(
            "wb_stock",
            "WB",
            90,
            cell_style=None,
        ),

        _int_col(
            "fbs_stock",
            "FBS",
            90,
            cell_style=None,
        ),

        _int_col(
            "in_transit",
            "В пути",
            100,
            cell_style=None,
        ),

        _int_col(
            "sales_30d",
            "Продажи 30д",
            120,
        ),

        _number_col(
            "stock_days",
            "Запас, дн.",
            110,
            digits=0,
            cell_style=_stock_days_style(),
        ),

        _int_col(
            "below_breakeven",
            "Ниже минимальной цены",
            160,
            cell_style=_risk_value_style(),
        ),

        _money_col(
            "stock_at_risk_value",
            "Потенциальный убыток на остатке",
            195,
            cell_style=_risk_value_style(),
        ),

        _money_col(
            "current_margin_30d",
            "Маржа факт 30д",
            140,
            cell_style={
                "fontWeight": "700",
            },
        ),


        _money_col(
            "margin_upside_day",
            "+ маржа / день, прогноз",
            165,
            cell_style={
                "fontWeight": "700",
                "color": "#047857",
            },
        ),
    ]


def portfolio_grid(records):
    return _base_grid(
        row_data=records,
        column_defs=_portfolio_columns(),
        grid_id="pricing-portfolio-grid",
        height="390px",
        page_size=20,
        page_sizes=[
            20,
            50,
            100,
        ],
    )


# ============================================================
# 2. NM ID — ОСНОВНАЯ ТАБЛИЦА
# ============================================================

# Колонки второго плана: они нужны при разборе конкретного
# товара, но в обычном просмотре только мешают. AG Grid
# показывает их по стрелке на заголовке группы.
SECONDARY_FIELDS = {
    "wb_discount_pct_30d",
    "last_man_cost",
    "unit_acc_cost",
    "ratios_source",
    "recommended_seller_price",
    "recommended_change_pct",
    "recommended_buyer_price",
    "recommended_sales_qty_30d",
    "recommended_margin_30d",
    "margin_upside_day",
    "sales_qty_7d",
    "elasticity",
    "elasticity_confidence",
}


def _mark_secondary(columns):
    """
    Проставляет columnGroupShow там, где колонка
    второстепенная. Первичные колонки видны всегда.
    """

    for group in columns:

        children = group.get("children")

        if not children:
            continue

        has_secondary = any(
            child.get("field") in SECONDARY_FIELDS
            for child in children
        )

        if not has_secondary:
            continue

        for child in children:

            child["columnGroupShow"] = (
                "open"
                if child.get("field") in SECONDARY_FIELDS
                else None
            )

            if child["columnGroupShow"] is None:
                child.pop("columnGroupShow")

    return columns


def _products_columns():
    columns = [

        # ====================================================
        # РЕШЕНИЕ
        # ====================================================

        {
            "headerName": "Решение",
            "marryChildren": True,
            "children": [

                _text_col(
                    "status",
                    "Что делать",
                    135,
                    pinned=True,
                    value_formatter=STATUS_FORMATTER,
                    cell_style=_status_style(),
                ),

                _number_col(
                    "priority",
                    "Приоритет",
                    115,
                    digits=0,
                    cell_style=_priority_style(),
                    value_formatter=PRIORITY_FORMATTER,
                ),
            ],
        },

        # ====================================================
        # ТОВАР
        # ====================================================

        {
            "headerName": "Товар",
            "marryChildren": True,
            "children": [

                _text_col(
                    "nm_id",
                    "NM ID",
                    125,
                    pinned=True,
                    cell_style={
                        "backgroundColor": "#F8FAFC",
                        "fontWeight": "700",
                    },
                ),

                _text_col(
                    "brand",
                    "Бренд",
                    145,
                ),

                _text_col(
                    "category",
                    "Категория",
                    175,
                ),

                _text_col(
                    "title",
                    "Наименование",
                    290,
                    min_width=260,
                    flex=1,
                ),
            ],
        },

        # ====================================================
        # ТЕКУЩАЯ ЦЕНА
        # ====================================================

        {
            "headerName": "Текущая цена",
            "marryChildren": True,
            "children": [

                _money_col(
                    "current_seller_list_price",
                    "Наша цена сейчас",
                    135,
                    cell_style={
                        "fontWeight": "700",
                    },
                ),

                _money_col(
                    "seller_price_30d",
                    "Наша факт. 30д",
                    130,
                ),

                _money_col(
                    "buyer_price_30d",
                    "Покупатель 30д",
                    130,
                ),

                _percent_col(
                    "wb_discount_pct_30d",
                    "Скидка WB 30д",
                    120,
                    digits=1,
                    cell_style=_wb_discount_style(),
                ),

                _money_col(
                    "last_man_cost",
                    "Упр. с/с",
                    110,
                    cell_style=None,
                ),
            ],
        },

        # ====================================================
        # ГРАНИЦА ЦЕНЫ
        #
        # Ради этих колонок отчёт и существует: ниже
        # минимальной цены продавать нельзя, ниже целевой —
        # можно, но с потерей плановой маржинальности.
        # ====================================================

        {
            "headerName": "Граница цены",
            "marryChildren": True,
            "children": [

                _money_col(
                    "breakeven_price",
                    "Минимальная цена",
                    145,
                    cell_style=_floor_price_style(),
                ),

                _money_col(
                    "target_margin_price",
                    "Цена под целевую маржу",
                    170,
                    cell_style={
                        "fontWeight": "700",
                    },
                ),

                _percent_col(
                    "price_headroom_pct",
                    "Запас по скидке",
                    130,
                    digits=1,
                    cell_style=_headroom_style(),
                ),

                # Обе себестоимости рядом: сразу видно,
                # где цена ушла ниже управленческой, а где
                # уже и ниже бухгалтерской. Подсветка
                # включается, когда текущая цена ниже
                # значения в ячейке.
                _money_col(
                    "unit_cogs",
                    "Упр. с/с",
                    115,
                    cell_style=_cost_style(),
                ),

                _money_col(
                    "unit_acc_cost",
                    "Бух. с/с",
                    115,
                    cell_style=_cost_style(),
                ),

                _text_col(
                    "ratios_source",
                    "Источник коэффициентов",
                    175,
                    cell_style=_ratios_source_style(),
                ),
            ],
        },

        # ====================================================
        # РЕКОМЕНДАЦИЯ
        # ====================================================

        {
            "headerName": "Рекомендация",
            "marryChildren": True,
            "children": [

                _money_col(
                    "action_price",
                    "Цена к установке",
                    145,
                    cell_style=_action_price_style(),
                ),

                _percent_col(
                    "action_change_pct",
                    "Изменение, %",
                    130,
                    digits=1,
                    signed=True,
                    cell_style=_price_change_style(),
                ),

                # Цена по модели и её процент — второй план.
                # На первом плане только «Цена к установке»
                # и её изменение, иначе рядом стоят два
                # похожих процента и непонятно, какой из них
                # решение.
                _money_col(
                    "recommended_seller_price",
                    "Цена по модели",
                    140,
                ),

                _percent_col(
                    "recommended_change_pct",
                    "Изменение по модели, %",
                    175,
                    digits=1,
                    signed=True,
                    cell_style=_price_change_style(),
                ),

                _money_col(
                    "recommended_buyer_price",
                    "Прогноз покупателю",
                    145,
                ),

                _number_col(
                    "recommended_sales_qty_30d",
                    "Прогноз продаж 30д",
                    150,
                    digits=0,
                    cell_style={
                        "fontWeight": "700",
                    },
                ),
            ],
        },

        # ====================================================
        # ЭКОНОМИКА
        # ====================================================

        {
            "headerName": "Экономика",
            "marryChildren": True,
            "children": [

                _money_col(
                    "margin_man_30d",
                    "Маржа факт 30д",
                    130,
                    cell_style=_margin_value_style(),
                ),

                _percent_col(
                    "margin_pct_30d",
                    "Маржа %",
                    95,
                    digits=1,
                    cell_style=_margin_pct_style(),
                ),

                _money_col(
                    "recommended_margin_30d",
                    "Маржа прогноз 30д",
                    145,
                    cell_style={
                        "fontWeight": "700",
                    },
                ),

                _money_col(
                    "margin_upside_day",
                    "+ маржа / день",
                    130,
                    cell_style={
                        "fontWeight": "700",
                        "color": "#047857",
                    },
                ),
            ],
        },

        # ====================================================
        # ЗАПАС И ПРОДАЖИ
        #
        # В основной таблице показываем только ИТОГО.
        # WB/FBS/к клиенту/от клиента уже есть в rowData и могут
        # показываться в карточке выбранного NM ID.
        # ====================================================

        {
            "headerName": "Запас и продажи",
            "marryChildren": True,
            "children": [

                _int_col(
                    "total_stock",
                    "Остаток всего",
                    115,
                    cell_style={
                        "fontWeight": "700",
                    },
                ),

                _number_col(
                    "days_of_stock",
                    "Запас, дн.",
                    105,
                    digits=0,
                    cell_style=_stock_days_style(),
                ),

                _int_col(
                    "sales_qty_7d",
                    "Продажи 7д",
                    100,
                ),

                _int_col(
                    "sales_qty_30d",
                    "Продажи 30д",
                    105,
                ),

                _percent_col(
                    "sales_speed_trend_pct",
                    "Тренд",
                    95,
                    digits=0,
                    cell_style=_trend_style(),
                ),
            ],
        },

        # ====================================================
        # МОДЕЛЬ
        # ====================================================

        {
            "headerName": "Модель",
            "marryChildren": True,
            "children": [

                _number_col(
                    "elasticity",
                    "Эластичность",
                    105,
                    digits=2,
                ),

                _text_col(
                    "elasticity_confidence",
                    "Надёжность",
                    145,
                ),

                {
                    "field": "reason",
                    "headerName": "Почему",
                    "minWidth": 360,
                    "flex": 1,
                    "wrapText": True,
                    "autoHeight": True,
                    "cellStyle": {
                        "fontSize": "11px",
                        "lineHeight": "1.35",
                        "color": "#475569",
                        "whiteSpace": "normal",
                    },
                },
            ],
        },
    ]

    return _mark_secondary(columns)


def products_grid(records):
    return _base_grid(
        row_data=records,
        column_defs=_products_columns(),
        grid_id="pricing-products-grid",
        height="660px",
        page_size=50,
        page_sizes=[
            25,
            50,
            100,
            250,
        ],
    )