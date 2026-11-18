# gear/app/daily_sales/supplies_cost/layout.py
"""Вкладка «Поставки WB»: поставки FBW и заполненность себестоимости."""
from __future__ import annotations

import dash_ag_grid as dag
import dash_mantine_components as dmc
import pandas as pd
from dash import dcc, html
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
    _totals_row,
)
from ..ui import excel_action_icon, loading_placeholder
from .config import (
    GRID_ARTICLES,
    GRID_BRANDS,
    GRID_SUPPLIES,
    MODAL_BODY_ID,
    MODAL_EXPORT_BTN_ID,
    MODAL_EXPORT_DOWNLOAD_ID,
    MODAL_ID,
    MODAL_SID_STORE,
    SUPPLIES_EXPORT_BTN_ID,
    SUPPLIES_EXPORT_LOADING_ID,
)
from .data import collect, supply_articles

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


_PCT1_FMT = {"function": "params.value == null ? '' : d3.format('.1f')(params.value) + ' %'"}


def _col(field, header, width=110, fmt=None, pinned=None, aggregate=None, style=None):
    c = {"field": field, "headerName": header, "width": width, "minWidth": width}
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
        _col("created", "Создана", 115, _DATE_FMT),
        _col("planned", "План. дата", 120, _DATE_FMT),
        _col("fact", "Принята", 115, _DATE_FMT),
        _col("status", "Статус WB", 160),
    ]
    if has_wh:
        cols.append(_col("warehouse", "Склад", 170))
    if has_box:
        cols.append(_col("box", "Упаковка", 125))
    cols += [
        _col("brands", "Бренды", 230),
        _col("plan_qty", "План, шт", 110, _INT_FMT, aggregate="sum"),
        _col("acc_qty", "Принято, шт", 125, _INT_FMT, aggregate="sum"),
        _col("arts", "Артикулов", 115, _INT_FMT, aggregate="sum"),
        _col("ok", "✅ есть", 105, _INT_FMT, aggregate="sum"),
        _col("part", "⚠️ частично", 125, _INT_FMT, aggregate="sum"),
        _col("bad", "🔴 нет", 100, _INT_FMT, aggregate="sum"),
        _col("no_cost_arts_pct", "Без с/с, % арт.", 140, _PCT1_FMT, style=_PCT_STYLE),
        _col("no_cost_qty", "Без с/с, шт", 125, _INT_FMT, aggregate="sum"),
        _col("no_cost_qty_pct", "Без с/с, % шт", 135, _PCT1_FMT, style=_PCT_STYLE),
    ]
    return cols


ARTICLE_COLUMNS = [
    _col("nm", "Артикул WB", 125, pinned="left"),
    _col("sa", "Артикул продавца", 170),
    _col("brand", "Бренд", 140),
    _col("category", "Категория", 160),
    _col("title", "Наименование", 240),
    _col("qty", "В поставке, шт", 140, _INT_FMT, aggregate="sum"),
    _col("cost_status", "Себестоимость", 150, style=_COST_STYLE),
    _col("no_cost_qty", "Без с/с, шт", 125, _INT_FMT, aggregate="sum"),
    _col("upd_qty", "По УПД, шт", 120, _INT_FMT),
    _col("cum_qty", "Отгружено нараст., шт", 175, _INT_FMT),
    _col("upd_last_date", "Последний УПД", 145, _DATE_FMT),
    _col("upd_last_number", "№ УПД", 120),
    _col("upd_last_price", "Цена УПД без НДС, ₽", 170, _MONEY_FMT),
]

BRAND_COLUMNS = [
    _col("brand", "Бренд", 200, pinned="left"),
    _col("supplies", "Поставок", 115, _INT_FMT),
    _col("arts", "Артикулов", 115, _INT_FMT),
    _col("qty", "Единиц, шт", 130, _INT_FMT, aggregate="sum"),
    _col("no_cost_arts", "Без полной с/с, арт.", 170, _INT_FMT),
    _col("no_cost_arts_pct", "Без с/с, % арт.", 140, _PCT1_FMT, style=_PCT_STYLE),
    _col("no_cost_qty", "Без с/с, шт", 125, _INT_FMT, aggregate="sum"),
    _col("no_cost_qty_pct", "Без с/с, % шт", 135, _PCT1_FMT, style=_PCT_STYLE),
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
          search_placeholder=None, clickable=False):
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
    if clickable:
        opts["rowSelection"] = "single"
    grid = dag.AgGrid(
        id={"type": GRID_TYPE, "index": grid_id},
        rowData=_for_grid(df[[c["field"] for c in columns if c["field"] in df.columns]]),
        columnDefs=[{k: v for k, v in c.items() if k != "aggregate"} for c in columns],
        dangerously_allow_code=True,
        defaultColDef={
            "sortable": True, "filter": True, "resizable": True,
            "cellDataType": False, "minWidth": 90,
            "wrapHeaderText": True, "autoHeaderHeight": True,
            "cellStyle": {"fontSize": "13px", "lineHeight": "1.3"},
        },
        dashGridOptions=opts,
        getRowStyle={"styleConditions": [{
            "condition": "params.node.rowPinned === 'bottom'",
            "style": {"backgroundColor": "#F1F4F8", "fontWeight": "700"},
        }]},
        style={"height": height, "width": "100%", "cursor": "pointer" if clickable else "auto"},
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


def _stat(title, value, note, accent=INK_PRIMARY):
    return _card([
        dmc.Text(title, size="11px", fw=600, c=INK_MUTED, tt="uppercase",
                 style={"letterSpacing": "0.04em"}),
        dmc.Text(value, size="20px", fw=700, c=accent, lh=1.2, mt=4,
                 style={"fontVariantNumeric": "tabular-nums"}),
        dmc.Text(note, size="12px", c=INK_SECONDARY, lh=1.3, mt=2),
    ], padding="10px 14px")


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
               "gap": "10px", "marginBottom": "16px"},
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
        dcc.Store(id=MODAL_SID_STORE),
        dcc.Download(id=MODAL_EXPORT_DOWNLOAD_ID),
        dmc.Modal(id=MODAL_ID, opened=False, size="95%", centered=True, title="Поставка", children=[
            dmc.Group(justify="flex-end", mb=4, children=[
                excel_action_icon(button_id=MODAL_EXPORT_BTN_ID,
                                  tooltip="Скачать поставку в Excel"),
            ]),
            html.Div(id=MODAL_BODY_ID),
        ]),
        _toolbar(k),
        tiles,
        _section(
            "Поставки",
            "Клик по строке — состав поставки. "
            "Цвет — доля артикулов и единиц без себестоимости",
            _grid(data["supplies"], supply_columns(data["has_warehouse"], data["has_box"]),
                  GRID_SUPPLIES, height="460px", totals_field="sid",
                  search_placeholder="Номер поставки, бренд", clickable=True),
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


ARTICLE_COLUMNS_ALL = [
    _col("sid", "Поставка", 120, pinned="left"),
    _col("d", "Дата", 115, _DATE_FMT),
] + [{k: v for k, v in c.items() if k != "pinned"} for c in ARTICLE_COLUMNS]


def supply_modal(sid):
    """Заголовок и содержимое модалки поставки."""
    a = supply_articles(sid)
    if a.empty:
        return f"Поставка {sid}", dmc.Text("Состав поставки не найден", c=INK_MUTED)
    r = a.iloc[0]
    fmt = lambda v: f"{pd.Timestamp(v):%d.%m.%Y}" if v is not None and pd.notna(v) else "—"
    qty, no_cost = a["qty"].sum(), a["no_cost_qty"].sum()
    n = a["nm"].nunique()
    n_gap = a.loc[a["cost_status"] != "✅ есть", "nm"].nunique()
    head = dmc.Group(gap=24, mb=12, children=[
        dmc.Text(f"Создана {fmt(r['created'])} · план {fmt(r['planned'])} · "
                 f"принята {fmt(r['fact'])} · {r['status']}"
                 + (f" · {r['box']}" if r["box"] else ""), size="13px", c=INK_SECONDARY),
        dmc.Text(f"Артикулов {_num(n)}, без полной с/с {_num(n_gap)} ({_pct(n_gap, n)}) · "
                 f"единиц {_num(qty)}, без с/с {_num(no_cost)} ({_pct(no_cost, qty)})",
                 size="13px", fw=600, c=STATUS_CRITICAL if n_gap else STATUS_GOOD),
    ])
    body = html.Div([head, _grid(a, ARTICLE_COLUMNS, f"wbs-modal-{sid}", height="60vh",
                                 totals_field="nm",
                                 search_placeholder="Артикул, бренд, наименование")])
    return f"Поставка {sid}", body
