# gear/app/daily_sales/fbs_orders/layout.py
"""
Вкладка «Заказы FBS».

Сверху — из чего складывается общее число заказов, дальше
четыре блока: контроль сборки, логистика, поставки, товары.
"""

from __future__ import annotations

import dash_ag_grid as dag
import dash_mantine_components as dmc
import pandas as pd
from dash import dcc, html
from dash_iconify import DashIconify

from .charts import (
    INK_MUTED,
    INK_PRIMARY,
    INK_SECONDARY,
    SERIES_BLUE,
    STATUS_CRITICAL,
    STATUS_GOOD,
    STATUS_SERIOUS,
    assembly_buckets_figure,
    daily_orders_figure,
    logistics_figure,
    order_state_figure,
)
from .config import (
    FBS_EXPORT_BTN_ID,
    FBS_EXPORT_LOADING_ID,
    SLA_LIMIT_HOURS,
    SUPPLIER_STATUS_NAMES,
    WB_STATUS_NAMES,
)
from .data import FbsSourceMissing, collect_fbs_analysis
from .insights import (
    INTRO_SECTIONS,
    assembly_insights,
    daily_insights,
    logistics_insights,
)
from ..ui import excel_action_icon, loading_placeholder


# ============================================================
# ОФОРМЛЕНИЕ
# ============================================================

SURFACE = "#FFFFFF"
PAGE_BG = "#F8FAFC"
HAIRLINE = "#E6E8EB"
HAIRLINE_SOFT = "#EFF1F3"

# Типы id для таблиц и полей поиска: один общий колбэк
# обслуживает все таблицы вкладки.
GRID_TYPE = "fbs-grid"
SEARCH_TYPE = "fbs-grid-search"

GRAPH_CONFIG = {
    "displayModeBar": False,
    "responsive": True,
}


def _num(value):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "—"
    try:
        return f"{int(round(float(value))):,}".replace(",", " ")
    except (TypeError, ValueError):
        return "—"


def _hours(value):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "—"
    try:
        return f"{float(value):,.1f} ч".replace(",", " ")
    except (TypeError, ValueError):
        return "—"


def _money(value):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "—"

    try:
        value = float(value)
    except (TypeError, ValueError):
        return "—"

    if abs(value) >= 1_000_000_000:
        return f"{value / 1_000_000_000:,.2f} млрд ₽".replace(",", " ")

    if abs(value) >= 1_000_000:
        return f"{value / 1_000_000:,.1f} млн ₽".replace(",", " ")

    return f"{value:,.0f} ₽".replace(",", " ")


# ============================================================
# ПРОСТЫЕ БЛОКИ
# ============================================================

def _card(children, padding="16px"):
    return html.Div(
        children=children,
        style={
            "backgroundColor": SURFACE,
            "border": f"1px solid {HAIRLINE}",
            "borderRadius": "8px",
            "padding": padding,
        },
    )


def _label(text, color=INK_MUTED):
    return dmc.Text(
        text,
        size="11px",
        fw=600,
        c=color,
        tt="uppercase",
        style={"letterSpacing": "0.04em"},
        lh=1.3,
    )


def _stat(title, value, note, accent=INK_PRIMARY):
    return _card(
        [
            _label(title),
            dmc.Space(h=8),
            dmc.Text(
                value,
                size="26px",
                fw=700,
                c=accent,
                lh=1.05,
                style={"fontVariantNumeric": "tabular-nums"},
            ),
            dmc.Space(h=6),
            dmc.Text(note, size="12px", c=INK_SECONDARY, lh=1.35),
        ],
        padding="14px 16px",
    )


def _section(title, subtitle, children):
    return html.Div(
        style={"marginBottom": "16px"},
        children=[
            html.Div(
                style={"marginBottom": "10px"},
                children=[
                    dmc.Text(
                        title,
                        size="17px",
                        fw=700,
                        c=INK_PRIMARY,
                        lh=1.2,
                    ),
                    dmc.Text(
                        subtitle,
                        size="12px",
                        c=INK_SECONDARY,
                        lh=1.35,
                        mt=2,
                    ),
                ],
            ),
            html.Div(children=children),
        ],
    )


def _intro():
    """
    Свёрнутое вступление: что за вкладка и как читать цифры.

    Развёрнутым по умолчанию не держим — тем, кто заходит сюда
    каждое утро, оно нужно один раз.
    """
    return dmc.Accordion(
        chevronPosition="left",
        variant="contained",
        radius="md",
        value=None,
        mb="md",
        styles={
            "item": {
                "backgroundColor": SURFACE,
                "border": f"1px solid {HAIRLINE}",
            },
            "control": {"paddingTop": 10, "paddingBottom": 10},
        },
        children=[
            dmc.AccordionItem(
                value="intro",
                children=[
                    dmc.AccordionControl(
                        dmc.Group(
                            gap=8,
                            children=[
                                DashIconify(
                                    icon="solar:info-circle-linear",
                                    width=17,
                                    height=17,
                                    color=INK_MUTED,
                                ),
                                dmc.Text(
                                    "О чём эта вкладка и как читать цифры",
                                    size="13px",
                                    fw=600,
                                    c=INK_PRIMARY,
                                ),
                            ],
                        )
                    ),
                    dmc.AccordionPanel(
                        html.Div(
                            style={
                                "display": "grid",
                                "gridTemplateColumns": (
                                    "repeat(auto-fit, minmax(280px, 1fr))"
                                ),
                                "gap": "16px",
                                "paddingBottom": "8px",
                            },
                            children=[
                                html.Div(
                                    children=[
                                        _label(title),
                                        dmc.Space(h=5),
                                        dmc.Text(
                                            text,
                                            size="13px",
                                            c=INK_SECONDARY,
                                            lh=1.5,
                                        ),
                                    ]
                                )
                                for title, text in INTRO_SECTIONS
                            ],
                        )
                    ),
                ],
            )
        ],
    )


def _insights(notes):
    """Выводы под графиком. Пусто — значит нечего сказать."""
    if not notes:
        return None

    return html.Div(
        style={
            "borderLeft": f"3px solid {SERIES_BLUE}",
            "backgroundColor": "#F7FAFD",
            "borderRadius": "0 6px 6px 0",
            "padding": "12px 16px",
            "marginTop": "10px",
        },
        children=[
            _label("Что из этого следует"),
            dmc.Space(h=8),
            html.Div(
                children=[
                    dmc.Text(
                        note,
                        size="13px",
                        c=INK_SECONDARY,
                        lh=1.5,
                        mb=6 if index < len(notes) - 1 else 0,
                    )
                    for index, note in enumerate(notes)
                ]
            ),
        ],
    )


def _graph(figure):
    return dcc.Graph(
        figure=figure,
        config=GRAPH_CONFIG,
        style={"width": "100%"},
    )


# ============================================================
# ТАБЛИЦЫ
# ============================================================

def _prepare_for_grid(df):
    """Даты — в строки: Timestamp плохо переживает сериализацию."""
    prepared = df.copy()

    for column in prepared.columns:
        if pd.api.types.is_datetime64_any_dtype(prepared[column]):
            prepared[column] = (
                prepared[column]
                .dt.strftime("%d.%m.%Y %H:%M")
                .where(prepared[column].notna(), None)
            )

    return prepared


def _totals_row(df, columns, label_field, label="ИТОГО"):
    """
    Считает закреплённую строку итогов.

    Количества складываются, часы усредняются с весом по
    количеству заказов: простое среднее по строкам дало бы
    цифру, которой в жизни не существует.
    """
    row = {label_field: label}

    weights = (
        pd.to_numeric(df["orders"], errors="coerce").fillna(0)
        if "orders" in df.columns
        else None
    )

    for column in columns:
        field = column["field"]

        if field == label_field or field not in df.columns:
            continue

        values = pd.to_numeric(df[field], errors="coerce")

        if values.notna().sum() == 0:
            continue

        if column.get("aggregate") == "wavg" and weights is not None:
            mask = values.notna() & (weights > 0)

            if weights[mask].sum():
                row[field] = round(
                    (values[mask] * weights[mask]).sum()
                    / weights[mask].sum(),
                    2,
                )
            continue

        if column.get("aggregate") == "sum":
            row[field] = round(float(values.sum()), 2)

    return [row]


def _grid(
    df,
    column_defs,
    grid_id,
    height="360px",
    totals_field=None,
    filters=True,
    page_size=25,
    auto_height=False,
    search=False,
    search_placeholder="Поиск по таблице",
):
    if df is None or df.empty:
        return _card(
            dmc.Text(
                "Нет данных по выбранным фильтрам",
                size="13px",
                c=INK_MUTED,
            ),
            padding="20px",
        )

    prepared = _prepare_for_grid(df)

    # 'aggregate' — наша пометка для расчёта итогов,
    # в AG Grid её отдавать не надо.
    grid_columns = [
        {k: v for k, v in column.items() if k != "aggregate"}
        for column in column_defs
    ]

    pinned = (
        _totals_row(df, column_defs, totals_field)
        if totals_field
        else None
    )

    grid_options = {
        "pagination": len(prepared) > page_size,
        "paginationPageSize": page_size,
        "enableCellTextSelection": True,
        "ensureDomOrder": True,
        "rowHeight": 34,
        "headerHeight": 38,
        "suppressCellFocus": True,
    }

    if pinned:
        grid_options["pinnedBottomRowData"] = pinned

    if auto_height:
        # Небольшая таблица занимает ровно свою высоту:
        # ни пустого места снизу, ни строки, срезанной
        # закреплённым итогом.
        grid_options["domLayout"] = "autoHeight"

    grid = dag.AgGrid(
            id={"type": GRID_TYPE, "index": grid_id},
            rowData=prepared.to_dict(orient="records"),
            columnDefs=grid_columns,
            dangerously_allow_code=True,
            defaultColDef={
                "sortable": True,
                "filter": filters,
                "resizable": True,
                "editable": False,
                "suppressMenu": not filters,
                "suppressHeaderMenuButton": not filters,
                # AG Grid угадывает тип колонки по первой строке
                # данных. Из-за этого слово «ИТОГО» в числовой
                # колонке показывалось как «Invalid Number».
                # Отключаем угадывание — значения выводятся
                # как есть, форматированием управляем сами.
                "cellDataType": False,
                "minWidth": 110,
                "cellStyle": {
                    "fontSize": "13px",
                    "lineHeight": "1.3",
                },
            },
            # Колонки растягиваются на всю ширину таблицы
            # и пересчитываются при изменении размера окна —
            # иначе справа остаётся пустое поле.
            columnSize="responsiveSizeToFit",
            columnSizeOptions={"defaultMinWidth": 110},
            dashGridOptions=grid_options,
            getRowStyle={
                "styleConditions": [
                    {
                        "condition": "params.node.rowPinned === 'bottom'",
                        "style": {
                            "backgroundColor": "#F1F4F8",
                            "fontWeight": "700",
                            "borderTop": f"1px solid {HAIRLINE}",
                        },
                    }
                ]
            },
            style=(
                {"width": "100%"}
                if auto_height
                else {"height": height, "width": "100%"}
            ),
            className="ag-theme-alpine",
        )

    box = html.Div(
        style={
            "border": f"1px solid {HAIRLINE}",
            "borderRadius": "8px",
            "overflow": "hidden",
            "backgroundColor": SURFACE,
        },
        children=grid,
    )

    if not search:
        return box

    # Одно поле на таблицу вместо набора кнопок: ищет сразу
    # по всем колонкам, поэтому годится и для артикула, и для
    # номера заказа, и для названия поставки.
    return html.Div(
        children=[
            dmc.TextInput(
                id={"type": SEARCH_TYPE, "index": grid_id},
                placeholder=search_placeholder,
                size="sm",
                radius="sm",
                mb=8,
                w=340,
                debounce=250,
                leftSection=DashIconify(
                    icon="solar:magnifer-linear",
                    width=15,
                    height=15,
                ),
            ),
            box,
        ]
    )


# ============================================================
# КОЛОНКИ
# ============================================================

_INT_FMT = {
    "function": """
    params.value == null
        ? ''
        : d3.format(',.0f')(params.value)
            .replaceAll(',', ' ')
    """
}

_NUM_FMT = {
    "function": """
    params.value == null
        ? ''
        : d3.format(',.1f')(params.value)
            .replaceAll(',', ' ')
    """
}

_MONEY_FMT = {
    "function": """
    params.value == null
        ? ''
        : d3.format(',.0f')(params.value)
            .replaceAll(',', ' ')
    """
}

_PCT_FMT = {
    "function": """
    params.value == null
        ? ''
        : d3.format(',.2f')(params.value)
            .replaceAll(',', ' ') + ' %'
    """
}


def _col(field, header, width=140, fmt=None, pinned=None, aggregate=None):
    column = {
        "field": field,
        "headerName": header,
        "width": width,
    }

    if fmt is not None:
        column["type"] = "numericColumn"
        column["valueFormatter"] = fmt

    if pinned:
        column["pinned"] = pinned

    if aggregate:
        column["aggregate"] = aggregate

    return column


BUCKET_COLUMNS = [
    _col("time_group", "Время в работе", 160, pinned="left"),
    _col("orders", "Заказов", 110, _INT_FMT, aggregate="sum"),
    _col("share_pct", "Доля", 100, _PCT_FMT, aggregate="sum"),
    _col("avg_hours", "Средние часы", 130, _NUM_FMT, aggregate="wavg"),
    _col("amount", "Сумма, ₽", 150, _MONEY_FMT, aggregate="sum"),
]

OVERDUE_COLUMNS = [
    _col("order_id", "Заказ", 130, pinned="left"),
    _col("age_hours", "Часов в работе", 140, _NUM_FMT),
    _col("created_at", "Создан", 150),
    _col("article", "Артикул", 150),
    _col("title", "Наименование", 250),
    _col("brand", "Бренд", 140),
    _col("office_name", "Пункт выдачи", 160),
    _col("warehouse_id", "Склад", 110),
    _col("supply_name", "Поставка", 200),
    _col("amount", "Сумма, ₽", 130, _MONEY_FMT, aggregate="sum"),
]

LOGISTICS_COLUMNS = [
    _col("warehouse", "Склад отправления", 170, pinned="left"),
    _col("office_name", "Пункт выдачи", 180),
    _col("destination_office", "Склад WB назначения", 200),
    _col("orders", "Заказов", 110, _INT_FMT, aggregate="sum"),
    _col("orders_in_work", "На сборке", 120, _INT_FMT, aggregate="sum"),
    _col("orders_overdue", "Просрочено", 120, _INT_FMT, aggregate="sum"),
    _col("supplies", "Поставок", 110, _INT_FMT, aggregate="sum"),
    _col("avg_hours", "Средние часы", 130, _NUM_FMT, aggregate="wavg"),
    _col("amount", "Сумма, ₽", 150, _MONEY_FMT, aggregate="sum"),
]

SUPPLIES_COLUMNS = [
    _col("supply_id", "Поставка", 160, pinned="left"),
    _col("supply_name", "Название", 230),
    _col("created_at", "Создана", 145),
    _col("closed_at", "Закрыта", 145),
    _col("scan_dt", "Скан", 145),
    _col("orders", "Заказов", 110, _INT_FMT, aggregate="sum"),
    _col("cancelled_orders", "Отменено", 110, _INT_FMT, aggregate="sum"),
    _col(
        "avg_hours_to_close",
        "Часов до закрытия",
        160,
        _NUM_FMT,
        aggregate="wavg",
    ),
    _col(
        "avg_hours_to_scan",
        "Часов до скана",
        150,
        _NUM_FMT,
        aggregate="wavg",
    ),
    _col("amount", "Сумма, ₽", 150, _MONEY_FMT, aggregate="sum"),
]

PRODUCTS_COLUMNS = [
    _col("article", "Артикул", 160, pinned="left"),
    _col("title", "Наименование", 270),
    _col("brand", "Бренд", 140),
    _col("subject_name", "Категория", 160),
    _col("orders", "Заказов", 110, _INT_FMT, aggregate="sum"),
    _col("orders_in_work", "На сборке", 120, _INT_FMT, aggregate="sum"),
    _col("cancelled_orders", "Отменено", 110, _INT_FMT, aggregate="sum"),
    _col("avg_hours", "Средние часы", 130, _NUM_FMT, aggregate="wavg"),
    _col("amount", "Сумма, ₽", 150, _MONEY_FMT, aggregate="sum"),
]

STATUS_COLUMNS = [
    _col("supplier_status_name", "Статус продавца", 190, pinned="left"),
    _col("wb_status_name", "Статус WB", 200),
    _col("orders", "Заказов", 110, _INT_FMT, aggregate="sum"),
    _col("avg_hours", "Средние часы", 130, _NUM_FMT, aggregate="wavg"),
    _col("amount", "Сумма, ₽", 150, _MONEY_FMT, aggregate="sum"),
]


# ============================================================
# ШАПКА
# ============================================================

def _toolbar(as_of, amount_source):
    return html.Div(
        style={
            "display": "flex",
            "justifyContent": "space-between",
            "alignItems": "center",
            "gap": "16px",
            "padding": "12px 16px",
            "marginBottom": "16px",
            "backgroundColor": SURFACE,
            "border": f"1px solid {HAIRLINE}",
            "borderRadius": "8px",
            "flexWrap": "wrap",
        },
        children=[
            html.Div(
                children=[
                    dmc.Text(
                        f"Данные на {as_of:%d.%m.%Y %H:%M}",
                        size="13px",
                        fw=600,
                        c=INK_PRIMARY,
                        lh=1.3,
                    ),
                    dmc.Text(
                        (
                            "Возраст заказов считается на этот момент, "
                            "а не на текущее время · сумма заказа: "
                            f"{amount_source}"
                        ),
                        size="12px",
                        c=INK_MUTED,
                        lh=1.3,
                        mt=2,
                    ),
                ]
            ),
            dmc.Group(
                gap=8,
                children=[
                    excel_action_icon(
                        button_id=FBS_EXPORT_BTN_ID,
                        tooltip="Скачать анализ заказов в Excel",
                    ),
                    loading_placeholder(
                        component_id=FBS_EXPORT_LOADING_ID,
                        color=STATUS_GOOD,
                    ),
                ],
            ),
        ],
    )


def _banner(title, text):
    return html.Div(
        style={
            "border": f"1px solid {STATUS_SERIOUS}55",
            "borderRadius": "8px",
            "backgroundColor": "#FFF4E6",
            "padding": "18px",
            "display": "flex",
            "gap": "12px",
            "alignItems": "flex-start",
        },
        children=[
            DashIconify(
                icon="solar:database-linear",
                width=22,
                height=22,
                color=STATUS_SERIOUS,
            ),
            html.Div(
                children=[
                    dmc.Text(title, fw=700, size="14px", c=STATUS_SERIOUS),
                    dmc.Space(h=4),
                    dmc.Text(text, size="13px", c=INK_SECONDARY),
                ]
            ),
        ],
    )


# ============================================================
# ОСНОВНОЙ МАКЕТ
# ============================================================

def fbs_orders_layout(
    start=None,
    end=None,
    cat_list=None,
    brand_list=None,
    gender_list=None,
    period_selected=True,
):
    try:
        payload = collect_fbs_analysis(
            start=start,
            end=end,
            cat_list=cat_list,
            brand_list=brand_list,
            gender_list=gender_list,
        )
    except FbsSourceMissing as error:
        return _banner(
            "Витрина заказов FBS не найдена",
            (
                f"{error} Загрузите заказы FBS в analytics.duckdb — "
                "после этого вкладка заработает без правок кода."
            ),
        )

    kpi = payload["kpi"]
    as_of = payload["as_of"]

    total = kpi.get("orders_total") or 0
    in_work = kpi.get("orders_in_work") or 0
    overdue = kpi.get("orders_overdue") or 0
    open_orders = kpi.get("orders_open") or 0

    overdue_share = (
        f"{100.0 * overdue / in_work:.1f} % от того, что на сборке"
        if in_work
        else "на сборке сейчас пусто"
    )

    # ---------------------------------------------------------
    # Из чего складывается общее число
    # ---------------------------------------------------------
    hero = _card(
        [
            html.Div(
                style={
                    "display": "flex",
                    "gap": "28px",
                    "alignItems": "flex-start",
                    "flexWrap": "wrap",
                },
                children=[
                    html.Div(
                        style={"minWidth": "190px"},
                        children=[
                            _label("Заказов в срезе"),
                            dmc.Space(h=6),
                            dmc.Text(
                                _num(total),
                                size="42px",
                                fw=700,
                                c=INK_PRIMARY,
                                lh=1.0,
                                style={
                                    "fontVariantNumeric": "tabular-nums"
                                },
                            ),
                            dmc.Space(h=6),
                            dmc.Text(
                                (
                                    f"{_num(kpi.get('nm_count'))} артикулов · "
                                    f"{_num(kpi.get('supplies_total'))} поставок"
                                ),
                                size="12px",
                                c=INK_SECONDARY,
                                lh=1.35,
                            ),
                        ],
                    ),
                    html.Div(
                        style={"flex": "1 1 420px", "minWidth": "320px"},
                        children=_graph(order_state_figure(kpi)),
                    ),
                ],
            )
        ]
    )

    tiles = html.Div(
        style={
            "display": "grid",
            "gridTemplateColumns": (
                "repeat(auto-fit, minmax(215px, 1fr))"
            ),
            "gap": "12px",
            "marginTop": "12px",
            "marginBottom": "20px",
        },
        children=[
            _stat(
                "На сборке сейчас",
                _num(in_work),
                (
                    f"из {_num(open_orders)} открытых · средний возраст "
                    f"{_hours(kpi.get('avg_age_in_work'))}"
                ),
                accent=SERIES_BLUE,
            ),
            _stat(
                f"Просрочено, свыше {SLA_LIMIT_HOURS} ч",
                _num(overdue),
                (
                    f"{overdue_share} · самый старый "
                    f"{_hours(kpi.get('max_age_in_work'))}"
                ),
                accent=STATUS_CRITICAL if overdue else STATUS_GOOD,
            ),
            _stat(
                "Сумма заказов",
                _money(kpi.get("amount")),
                f"средний чек {_money((kpi.get('amount') or 0) / total if total else 0)}",
                accent=INK_PRIMARY,
            ),
            _stat(
                "Срок закрытия поставки",
                _hours(kpi.get("avg_hours_to_close")),
                (
                    f"по {_num(kpi.get('orders_closed'))} заказам, "
                    "вошедшим в закрытые поставки"
                ),
                accent=INK_PRIMARY,
            ),
        ],
    )

    # ---------------------------------------------------------
    # Статусы человеческими словами
    # ---------------------------------------------------------
    statuses = payload["statuses"].copy()

    if not statuses.empty:
        statuses["supplier_status_name"] = statuses[
            "supplier_status"
        ].map(lambda v: SUPPLIER_STATUS_NAMES.get(v, v))

        statuses["wb_status_name"] = statuses["wb_status"].map(
            lambda v: WB_STATUS_NAMES.get(v, v)
        )

    return html.Div(
        children=[
            _toolbar(as_of, payload.get("amount_source", "—")),
            _intro(),
            hero,
            tiles,

            _section(
                "Контроль сборки",
                (
                    "Сколько заказов сейчас на сборке и как давно. "
                    f"Норматив — {SLA_LIMIT_HOURS} часов, "
                    "жёлтая зона начинается с 36"
                ),
                [
                    _card(_graph(assembly_buckets_figure(
                        payload["buckets_in_work"]
                    ))),
                    _insights(
                        assembly_insights(payload["buckets_in_work"], kpi)
                    ),
                    dmc.Space(h=12),
                    _grid(
                        payload["buckets_in_work"],
                        BUCKET_COLUMNS,
                        "fbs-buckets-grid",
                        totals_field="time_group",
                        filters=False,
                        auto_height=True,
                    ),
                    dmc.Space(h=16),
                    dmc.Text(
                        "Заказы сверх норматива",
                        size="14px",
                        fw=700,
                        c=STATUS_CRITICAL if overdue else INK_SECONDARY,
                    ),
                    dmc.Space(h=8),
                    _grid(
                        payload["overdue"],
                        OVERDUE_COLUMNS,
                        "fbs-overdue-grid",
                        height="380px",
                        totals_field="order_id",
                        search=True,
                        search_placeholder=(
                            "Заказ, артикул, склад, поставка"
                        ),
                    ),
                ],
            ),

            _section(
                "Логистика: откуда и куда",
                "Крупнейшие направления «склад отправления → пункт выдачи»",
                [
                    _card(_graph(logistics_figure(payload["logistics"]))),
                    _insights(logistics_insights(payload["logistics"])),
                    dmc.Space(h=12),
                    _grid(
                        payload["logistics"],
                        LOGISTICS_COLUMNS,
                        "fbs-logistics-grid",
                        height="420px",
                        totals_field="warehouse",
                        search=True,
                        search_placeholder="Склад или пункт назначения",
                    ),
                ],
            ),

            _section(
                "Заказы по дате создания",
                (
                    "Сколько заказов покупатели создали в этот день — "
                    "не сколько собрано. Последние 60 дней"
                ),
                [
                    _card(_graph(daily_orders_figure(payload["daily"]))),
                    _insights(daily_insights(payload["daily"])),
                ],
            ),

            _section(
                "Поставки: сборка и отгрузка",
                "От создания поставки до скана на складе WB",
                _grid(
                    payload["supplies"],
                    SUPPLIES_COLUMNS,
                    "fbs-supplies-grid",
                    height="420px",
                    totals_field="supply_id",
                    search=True,
                    search_placeholder="Номер или название поставки",
                ),
            ),

            _section(
                "Товары и деньги в заказах",
                "Что заказывают и на какую сумму",
                _grid(
                    payload["products"],
                    PRODUCTS_COLUMNS,
                    "fbs-products-grid",
                    height="420px",
                    totals_field="article",
                    search=True,
                    search_placeholder="Артикул, название, категория",
                ),
            ),

            _section(
                "Статусы заказов",
                "Пары «статус продавца — статус WB»",
                _grid(
                    statuses,
                    STATUS_COLUMNS,
                    "fbs-statuses-grid",
                    totals_field="supplier_status_name",
                    filters=False,
                    auto_height=True,
                ),
            ),
        ]
    )
