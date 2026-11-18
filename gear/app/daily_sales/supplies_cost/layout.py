# gear/app/daily_sales/supplies_cost/layout.py
"""Вкладка «Поставки WB»: поставки FBW и заполненность себестоимости."""
from __future__ import annotations

import dash_ag_grid as dag
import dash_mantine_components as dmc
import pandas as pd
from dash import html
from dash_iconify import DashIconify

from ..fbs_orders.charts import (
    INK_MUTED,
    INK_PRIMARY,
    INK_SECONDARY,
    STATUS_CRITICAL,
    STATUS_GOOD,
    STATUS_SERIOUS,
)
from ..fbs_orders.layout import (
    GRID_TYPE,
    HAIRLINE,
    SEARCH_TYPE,
    SURFACE,
    _INT_FMT,
    _MONEY_FMT,
    _PCT_FMT,
    _card,
    _section,
    _stat,
    _totals_row,
)
from ..ui import excel_action_icon, loading_placeholder
from .config import (
    GRID_ARTICLES,
    GRID_BRANDS,
    GRID_SUPPLIES,
    SUPPLIES_EXPORT_BTN_ID,
    SUPPLIES_EXPORT_LOADING_ID,
)
from .data import collect

_DATE_FMT = {"function": "params.value ? params.value.split('-').reverse().join('.') : ''"}

_PCT_STYLE = {
    "styleConditions": [
        {"condition": "params.value == null", "style": {}},
        {"condition": "params.value >= 50",
         "style": {"backgroundColor": "#FDECEC", "color": "#A33A3A", "fontWeight": "600"}},
        {"condition": "params.value > 0",
         "style": {"backgroundColor": "#FFF4E6", "color": "#B35309"}},
        {"condition": "params.value == 0",
         "style": {"backgroundColor": "#E7F1ED", "color": "#2F6656"}},
    ]
}

_COST_STYLE = {
    "styleConditions": [
        {"condition": "params.value && params.value.startsWith('🔴')",
         "style": {"color": "#A33A3A", "fontWeight": "600"}},
        {"condition": "params.value && params.value.startsWith('⚠️')",
         "style": {"color": "#B35309"}},
    ]
}


def _num(v):
    try:
        return f"{int(round(float(v))):,}".replace(",", " ")
    except (TypeError, ValueError):
        return "—"


def _pct(part, whole):
    return f"{100.0 * part / whole:.1f} %" if whole else "—"


def _col(field, header, width=120, fmt=None, pinned=None, aggregate=None, style=None):
    c = {"field": field, "headerName": header, "width": width,
         "wrapHeaderText": True, "autoHeaderHeight": True}
    if fmt is not None:
        c["valueFormatter"] = fmt
        if fmt is not _DATE_FMT:
            c["type"] = "numericColumn"
    if pinned:
        c["pinned"] = pinned
    if aggregate:
        c["aggregate"] = aggregate
    if style:
        c["cellStyle"] = style
    return c


def supply_columns(has_wh, has_box):
    cols = [
        _col("sid", "Поставка", 120, pinned="left"),
        _col("created", "Создана", 105, _DATE_FMT),
        _col("planned", "Плановая дата", 110, _DATE_FMT),
        _col("fact", "Принята", 105, _DATE_FMT),
        _col("status", "Статус WB", 140),
    ]
    if has_wh:
        cols.append(_col("warehouse", "Склад", 160))
    if has_box:
        cols.append(_col("box", "Упаковка", 110))
    cols += [
        _col("brands", "Бренды", 200),
        _col("plan_qty", "План, шт", 95, _INT_FMT, aggregate="sum"),
        _col("acc_qty", "Принято, шт", 100, _INT_FMT, aggregate="sum"),
        _col("arts", "Артикулов", 95, _INT_FMT, aggregate="sum"),
        _col("ok", "✅ с/с есть", 95, _INT_FMT, aggregate="sum"),
        _col("part", "⚠️ частично", 95, _INT_FMT, aggregate="sum"),
        _col("bad", "🔴 нет с/с", 95, _INT_FMT, aggregate="sum"),
        _col("no_cost_arts_pct", "Артикулов без полной с/с, %", 120, _PCT_FMT, style=_PCT_STYLE),
        _col("no_cost_qty", "Единиц без с/с", 105, _INT_FMT, aggregate="sum"),
        _col("no_cost_qty_pct", "Единиц без с/с, %", 110, _PCT_FMT, style=_PCT_STYLE),
    ]
    return cols


ARTICLE_COLUMNS = [
    _col("sid", "Поставка", 115, pinned="left"),
    _col("d", "Дата", 100, _DATE_FMT),
    _col("nm", "Артикул WB", 115),
    _col("sa", "Артикул продавца", 150),
    _col("brand", "Бренд", 130),
    _col("category", "Категория", 150),
    _col("title", "Наименование", 220),
    _col("qty", "В поставке, шт", 100, _INT_FMT, aggregate="sum"),
    _col("cost_status", "Себестоимость", 130, style=_COST_STYLE),
    _col("no_cost_qty", "Без с/с, шт", 95, _INT_FMT, aggregate="sum"),
    _col("upd_qty", "По УПД с ценой всего, шт", 115, _INT_FMT),
    _col("cum_qty", "Отгружено на WB нарастающим, шт", 125, _INT_FMT),
    _col("upd_last_date", "Последний УПД", 110, _DATE_FMT),
    _col("upd_last_number", "№ УПД", 110),
    _col("upd_last_price", "Цена по УПД без НДС, ₽", 115, _MONEY_FMT),
]

BRAND_COLUMNS = [
    _col("brand", "Бренд", 180, pinned="left"),
    _col("supplies", "Поставок", 95, _INT_FMT),
    _col("arts", "Артикулов", 95, _INT_FMT),
    _col("qty", "Единиц в поставках", 115, _INT_FMT, aggregate="sum"),
    _col("no_cost_arts", "Артикулов без полной с/с", 120, _INT_FMT),
    _col("no_cost_arts_pct", "Артикулов без полной с/с, %", 120, _PCT_FMT, style=_PCT_STYLE),
    _col("no_cost_qty", "Единиц без с/с", 105, _INT_FMT, aggregate="sum"),
    _col("no_cost_qty_pct", "Единиц без с/с, %", 110, _PCT_FMT, style=_PCT_STYLE),
]


def _for_grid(df):
    out = df.copy()
    for c in out.columns:
        if pd.api.types.is_datetime64_any_dtype(out[c]) or out[c].dtype == object and \
                out[c].map(lambda v: hasattr(v, "isoformat")).any():
            out[c] = pd.to_datetime(out[c], errors="coerce").dt.strftime("%Y-%m-%d")
            out[c] = out[c].where(out[c].notna(), None)
    out = out.astype(object).where(out.notna(), None)
    return out.to_dict(orient="records")


def _grid(df, columns, grid_id, height="440px", totals_field=None,
          search_placeholder=None, selectable=False):
    pinned = _totals_row(df, columns, totals_field) if totals_field else None
    opts = {
        "pagination": len(df) > 50,
        "paginationPageSize": 50,
        "enableCellTextSelection": True,
        "ensureDomOrder": True,
        "rowHeight": 34,
        "suppressCellFocus": True,
    }
    if pinned:
        opts["pinnedBottomRowData"] = pinned
    if selectable:
        opts["rowSelection"] = "single"
    grid = dag.AgGrid(
        id={"type": GRID_TYPE, "index": grid_id},
        rowData=_for_grid(df[[c["field"] for c in columns if c["field"] in df.columns]]),
        columnDefs=[{k: v for k, v in c.items() if k != "aggregate"} for c in columns],
        dangerously_allow_code=True,
        defaultColDef={
            "sortable": True, "filter": True, "resizable": True,
            "cellDataType": False, "minWidth": 90,
            "cellStyle": {"fontSize": "13px", "lineHeight": "1.3"},
        },
        columnSize="responsiveSizeToFit",
        dashGridOptions=opts,
        getRowStyle={"styleConditions": [{
            "condition": "params.node.rowPinned === 'bottom'",
            "style": {"backgroundColor": "#F1F4F8", "fontWeight": "700"},
        }]},
        style={"height": height, "width": "100%"},
        className="ag-theme-alpine",
    )
    box = html.Div(
        style={"border": f"1px solid {HAIRLINE}", "borderRadius": "8px",
               "overflow": "hidden", "backgroundColor": SURFACE},
        children=grid,
    )
    if not search_placeholder:
        return box
    return html.Div([
        dmc.TextInput(
            id={"type": SEARCH_TYPE, "index": grid_id},
            placeholder=search_placeholder, size="sm", radius="sm", mb=8, w=360,
            debounce=250,
            leftSection=DashIconify(icon="solar:magnifer-linear", width=15, height=15),
        ),
        box,
    ])


def _toolbar(kpi):
    period = (f"{kpi['d_min']:%d.%m.%Y} – {kpi['d_max']:%d.%m.%Y}"
              if pd.notna(kpi["d_min"]) else "—")
    return html.Div(
        style={"display": "flex", "justifyContent": "space-between", "alignItems": "center",
               "gap": "16px", "padding": "12px 16px", "marginBottom": "16px",
               "backgroundColor": SURFACE, "border": f"1px solid {HAIRLINE}",
               "borderRadius": "8px", "flexWrap": "wrap"},
        children=[
            html.Div([
                dmc.Text(f"Поставки FBW · {period}", size="13px", fw=600, c=INK_PRIMARY),
                dmc.Text(
                    "Дата поставки — фактическая приёмка, до приёмки — плановая. "
                    "Себестоимость — по приходным УПД с ценой",
                    size="12px", c=INK_MUTED, mt=2),
            ]),
            dmc.Group(gap=8, children=[
                excel_action_icon(button_id=SUPPLIES_EXPORT_BTN_ID,
                                  tooltip="Скачать поставки в Excel"),
                loading_placeholder(component_id=SUPPLIES_EXPORT_LOADING_ID, color=STATUS_GOOD),
            ]),
        ],
    )


def _empty():
    return _card(dmc.Text("Поставок по выбранным фильтрам нет", size="13px", c=INK_MUTED),
                 padding="20px")


def supplies_layout(start=None, end=None, cat_list=None, brand_list=None, gender_list=None):
    data = collect(start, end, cat_list, brand_list, gender_list)
    if data.get("empty"):
        return _empty()
    k = data["kpi"]

    tiles = html.Div(
        style={"display": "grid", "gridTemplateColumns": "repeat(auto-fit, minmax(215px, 1fr))",
               "gap": "12px", "marginBottom": "20px"},
        children=[
            _stat("Поставок", _num(k["supplies"]),
                  f"с пробелами в себестоимости: {_num(k['supplies_with_gap'])}"),
            _stat("Единиц в поставках", _num(k["qty"]),
                  f"артикулов: {_num(k['arts'])}"),
            _stat("Артикулов без полной с/с", _num(k["arts_no_cost"]),
                  f"{_pct(k['arts_no_cost'], k['arts'])} артикулов · "
                  f"без УПД с ценой: {_num(k['arts_no_upd'])}",
                  accent=STATUS_CRITICAL if k["arts_no_cost"] else STATUS_GOOD),
            _stat("Единиц без с/с", _num(k["no_cost_qty"]),
                  f"{_pct(k['no_cost_qty'], k['qty'])} от единиц в поставках",
                  accent=STATUS_SERIOUS if k["no_cost_qty"] else STATUS_GOOD),
        ],
    )

    return html.Div([
        _toolbar(k),
        tiles,
        _section(
            "Поставки",
            "Клик по строке — состав поставки в таблице ниже. "
            "Цвет — доля артикулов и единиц без себестоимости",
            _grid(data["supplies"], supply_columns(data["has_warehouse"], data["has_box"]),
                  GRID_SUPPLIES, height="460px", totals_field="sid",
                  search_placeholder="Номер поставки, бренд, склад", selectable=True),
        ),
        _section(
            "Артикулы в поставках",
            "Количество по УПД с ценой закрывает поставки артикула от старых к новым; "
            "что не закрыто — без себестоимости",
            _grid(data["articles"], ARTICLE_COLUMNS, GRID_ARTICLES, height="520px",
                  totals_field="sid",
                  search_placeholder="Поставка, артикул, бренд, наименование"),
        ),
        _section(
            "По брендам",
            "Сколько поставлено и какая часть без себестоимости",
            _grid(data["brands"], BRAND_COLUMNS, GRID_BRANDS, height="380px",
                  totals_field="brand"),
        ),
        dmc.Text(
            "✅ есть — количество по УПД покрывает эту поставку; ⚠️ частично — покрывает часть "
            "или УПД пришли только на прошлые поставки; 🔴 нет УПД / УПД без цены — "
            "себестоимости нет. УПД покрывают и продажи FBS, поэтому оценка мягкая.",
            size="12px", c=INK_SECONDARY, mt=4,
        ),
    ])
