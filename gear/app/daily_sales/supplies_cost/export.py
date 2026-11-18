# gear/app/daily_sales/supplies_cost/export.py
"""Excel по поставкам WB и колбэки вкладки."""
from __future__ import annotations

from datetime import date, datetime
from io import BytesIO

import pandas as pd
from dash import Input, Output, State, dcc, no_update

from ..fbs_orders.layout import GRID_TYPE
from .config import (
    GRID_SUPPLIES,
    MODAL_BODY_ID,
    MODAL_EXPORT_BTN_ID,
    MODAL_EXPORT_DOWNLOAD_ID,
    MODAL_ID,
    MODAL_SID_STORE,
    SUPPLIES_EXPORT_BTN_ID,
    SUPPLIES_EXPORT_DOWNLOAD_ID,
    SUPPLIES_EXPORT_LOADING_ID,
)
from .data import collect, supply_articles

NOTES = [
    ("Источник поставок", "Поставки FBW из кабинета WB (API «Поставки»), обновляются ежедневно в 06:40 МСК."),
    ("Дата поставки", "Фактическая дата приёмки; если поставка ещё не принята — плановая, затем дата создания. "
                      "Фильтр периода применяется к этой дате."),
    ("Количество", "«Принято» — сколько WB принял; пока приёмки нет — плановое количество."),
    ("Себестоимость", "По приходным УПД, где указана цена без НДС. Количество по всем УПД артикула "
                      "закрывает его поставки от старых к новым (FIFO)."),
    ("✅ есть", "Количества по УПД хватает на эту поставку и все более ранние."),
    ("⚠️ частично", "УПД есть, но их количества хватило только на часть поставки или только на прошлые поставки."),
    ("🔴 нет УПД", "По артикулу нет ни одного приходного УПД."),
    ("🔴 УПД без цены", "УПД есть, но цена в них не заполнена."),
    ("Ограничение", "УПД закрывают и продажи FBS, а поставки вне кабинета WB здесь не видны, "
                    "поэтому оценка покрытия мягкая: реальный пробел может быть больше."),
]


def _fmt_date(v):
    if not v:
        return None
    try:
        return datetime.fromisoformat(str(v)[:10]).date()
    except ValueError:
        return None


def _rows(df, cols):
    out = []
    for r in df[[c for c, _ in cols]].itertuples(index=False):
        row = []
        for v in r:
            if v is None or v is pd.NaT or (isinstance(v, float) and pd.isna(v)):
                row.append(None)
            elif isinstance(v, pd.Timestamp):
                row.append(v.date())
            elif isinstance(v, float):
                row.append(round(v, 2))
            else:
                row.append(v.item() if hasattr(v, "item") else v)
        out.append(row)
    return out


def build_supplies_excel(date_range=None, cat_list=None, brand_list=None,
                         gender_list=None) -> tuple[bytes, str] | None:
    from openpyxl import Workbook
    from openpyxl.styles import Font
    from gear.management.commands import mp
    from ..assistant.excel import _write_table

    start = end = None
    if date_range and len(date_range) == 2:
        start, end = _fmt_date(date_range[0]), _fmt_date(date_range[1])
    if not (start and end):
        start = end = None

    data = collect(start, end, cat_list, brand_list, gender_list)
    if data.get("empty"):
        return None
    k = data["kpi"]
    sub = (f"Поставки FBW {k['d_min']:%d.%m.%Y} – {k['d_max']:%d.%m.%Y}"
           + (f" · бренды: {', '.join(brand_list)}" if brand_list else ""))
    pct = mp.FMT_PCT

    s_cols = [("sid", "Поставка"), ("created", "Создана"), ("planned", "Плановая дата"),
              ("fact", "Принята"), ("status", "Статус WB")]
    if data["has_warehouse"]:
        s_cols.append(("warehouse", "Склад"))
    if data["has_box"]:
        s_cols.append(("box", "Упаковка"))
    s_cols += [("brands", "Бренды"), ("plan_qty", "План, шт"), ("acc_qty", "Принято, шт"),
               ("arts", "Артикулов, шт"), ("ok", "✅ с/с есть, артикулов"),
               ("part", "⚠️ частично, артикулов"), ("bad", "🔴 нет с/с, артикулов"),
               ("no_cost_arts_pct", "Артикулов без полной с/с, %"),
               ("no_cost_qty", "Единиц без с/с, шт"), ("no_cost_qty_pct", "Единиц без с/с, %")]

    a_cols = [("sid", "Поставка"), ("d", "Дата поставки"), ("nm", "Артикул WB"),
              ("sa", "Артикул продавца"), ("brand", "Бренд"), ("category", "Категория"),
              ("title", "Наименование"), ("qty", "В поставке, шт"),
              ("cost_status", "Себестоимость"), ("no_cost_qty", "Без с/с, шт"),
              ("upd_qty", "По УПД с ценой всего, шт"),
              ("cum_qty", "Отгружено на WB нарастающим, шт"),
              ("upd_last_date", "Последний УПД"), ("upd_last_number", "№ УПД"),
              ("upd_last_price", "Цена по УПД без НДС, ₽")]

    b_cols = [("brand", "Бренд"), ("supplies", "Поставок"), ("arts", "Артикулов"),
              ("qty", "Единиц в поставках, шт"), ("no_cost_arts", "Артикулов без полной с/с"),
              ("no_cost_arts_pct", "Артикулов без полной с/с, %"),
              ("no_cost_qty", "Единиц без с/с, шт"), ("no_cost_qty_pct", "Единиц без с/с, %")]

    def idx(cols, key):
        return [c for c, _ in cols].index(key)

    wb = Workbook()
    ws = wb.active
    ws.title = "Поставки"
    _write_table(ws, mp, "Поставки WB и себестоимость", sub, "Одна строка — поставка",
                 [n for _, n in s_cols], _rows(data["supplies"], s_cols), totals=True,
                 freeze_cols=1, header_max=14,
                 col_formats={idx(s_cols, "sid"): "0",
                              idx(s_cols, "no_cost_arts_pct"): pct,
                              idx(s_cols, "no_cost_qty_pct"): pct})

    ws = wb.create_sheet("Артикулы в поставках")
    _write_table(ws, mp, "Артикулы в поставках", sub, "Поставка × артикул",
                 [n for _, n in a_cols], _rows(data["articles"], a_cols), totals=True,
                 freeze_cols=idx(a_cols, "nm") + 1, header_max=14,
                 col_formats={idx(a_cols, "sid"): "0", idx(a_cols, "nm"): "0",
                              idx(a_cols, "upd_qty"): "#,##0",
                              idx(a_cols, "cum_qty"): "#,##0",
                              idx(a_cols, "upd_last_price"): mp.FMT_MONEY_DEC})

    ws = wb.create_sheet("По брендам")
    _write_table(ws, mp, "По брендам", sub, "Поставлено и без себестоимости",
                 [n for _, n in b_cols], _rows(data["brands"], b_cols), totals=True,
                 freeze_cols=1, header_max=14,
                 col_formats={idx(b_cols, "no_cost_arts_pct"): pct,
                              idx(b_cols, "no_cost_qty_pct"): pct})

    ws = wb.create_sheet("Как читать")
    mp.sheet_setup(ws, landscape=False)
    mp.title_band(ws, "Как читать", "Поставки WB и себестоимость", 4, show_back=False)
    ws.column_dimensions["A"].width = 2
    ws.column_dimensions["B"].width = 24
    ws.column_dimensions["C"].width = 100
    for i, (t, v) in enumerate(NOTES):
        mp.write(ws, 7 + i, 2, t, font=Font(name=mp.FONT, size=9, bold=True, color=mp.NAVY_3),
                 align="left", border=mp.B_BOTTOM)
        mp.write(ws, 7 + i, 3, v, font=Font(name=mp.FONT, size=9, color=mp.TEXT),
                 align="left", wrap=True, border=mp.B_BOTTOM)

    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue(), f"wb_supplies_cost_{date.today():%Y-%m-%d}.xlsx"


def build_supply_excel(sid) -> tuple[bytes, str] | None:
    """Одна поставка: шапка и полный состав по артикулам."""
    from openpyxl import Workbook
    from openpyxl.styles import Font
    from gear.management.commands import mp
    from ..assistant.excel import _write_table

    a = supply_articles(sid)
    if a.empty:
        return None
    r = a.iloc[0]
    fd = lambda v: f"{pd.Timestamp(v):%d.%m.%Y}" if v is not None and pd.notna(v) else "—"
    qty, no_cost = a["qty"].sum(), a["no_cost_qty"].sum()
    n = a["nm"].nunique()
    n_gap = a.loc[a["cost_status"] != "✅ есть", "nm"].nunique()
    sub = (f"Создана {fd(r['created'])} · план {fd(r['planned'])} · принята {fd(r['fact'])}"
           f" · {r['status']}" + (f" · {r['box']}" if r["box"] else ""))
    extra = (f"Артикулов {n}, без полной с/с {n_gap} · единиц {qty:,.0f}, "
             f"без с/с {no_cost:,.0f}").replace(",", " ")

    cols = [("nm", "Артикул WB"), ("sa", "Артикул продавца"), ("brand", "Бренд"),
            ("category", "Категория"), ("title", "Наименование"),
            ("plan_qty", "План, шт"), ("acc_qty", "Принято, шт"), ("qty", "В поставке, шт"),
            ("cost_status", "Себестоимость"), ("no_cost_qty", "Без с/с, шт"),
            ("upd_qty", "По УПД с ценой всего, шт"),
            ("cum_qty", "Отгружено на WB нарастающим, шт"),
            ("upd_last_date", "Последний УПД"), ("upd_last_number", "№ УПД"),
            ("upd_last_price", "Цена по УПД без НДС, ₽")]
    idx = [c for c, _ in cols].index

    wb = Workbook()
    ws = wb.active
    ws.title = f"Поставка {sid}"[:31]
    _write_table(ws, mp, f"Поставка {sid}", sub, extra,
                 [t for _, t in cols], _rows(a, cols), totals=True,
                 freeze_cols=2, header_max=14,
                 col_formats={idx("nm"): "0", idx("upd_qty"): "#,##0",
                              idx("cum_qty"): "#,##0",
                              idx("upd_last_price"): mp.FMT_MONEY_DEC})

    ws = wb.create_sheet("Как читать")
    mp.sheet_setup(ws, landscape=False)
    mp.title_band(ws, "Как читать", f"Поставка {sid}", 4, show_back=False)
    ws.column_dimensions["A"].width = 2
    ws.column_dimensions["B"].width = 24
    ws.column_dimensions["C"].width = 100
    for i, (t, v) in enumerate(NOTES):
        mp.write(ws, 7 + i, 2, t, font=Font(name=mp.FONT, size=9, bold=True, color=mp.NAVY_3),
                 align="left", border=mp.B_BOTTOM)
        mp.write(ws, 7 + i, 3, v, font=Font(name=mp.FONT, size=9, color=mp.TEXT),
                 align="left", wrap=True, border=mp.B_BOTTOM)

    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue(), f"wb_supply_{sid}.xlsx"


def register_supplies_callbacks(app, date_picker_id, cat_multy_id, brand_multy_id,
                                gender_multy_id):
    @app.callback(
        Output(SUPPLIES_EXPORT_DOWNLOAD_ID, "data"),
        Output(SUPPLIES_EXPORT_LOADING_ID, "children"),
        Input(SUPPLIES_EXPORT_BTN_ID, "n_clicks"),
        State(date_picker_id, "value"),
        State(cat_multy_id, "value"),
        State(brand_multy_id, "value"),
        State(gender_multy_id, "value"),
        prevent_initial_call=True,
    )
    def export_supplies(n_clicks, date_range, cat_list, brand_list, gender_list):
        if not n_clicks:
            return no_update, no_update
        res = build_supplies_excel(date_range, cat_list, brand_list, gender_list)
        if res is None:
            return no_update, ""
        content, name = res
        return dcc.send_bytes(content, filename=name), ""

    @app.callback(
        Output(MODAL_ID, "opened"),
        Output(MODAL_ID, "title"),
        Output(MODAL_BODY_ID, "children"),
        Output(MODAL_SID_STORE, "data"),
        Output({"type": GRID_TYPE, "index": GRID_SUPPLIES}, "selectedRows"),
        Input({"type": GRID_TYPE, "index": GRID_SUPPLIES}, "selectedRows"),
        prevent_initial_call=True,
    )
    def open_supply(rows):
        from .layout import supply_modal
        sid = (rows or [{}])[0].get("sid")
        if not sid or not str(sid).isdigit():
            return no_update, no_update, no_update, no_update, no_update
        title, body = supply_modal(int(sid))
        # снимаем выделение, чтобы повторный клик по той же строке снова открывал окно
        return True, title, body, int(sid), []

    @app.callback(
        Output(MODAL_EXPORT_DOWNLOAD_ID, "data"),
        Input(MODAL_EXPORT_BTN_ID, "n_clicks"),
        State(MODAL_SID_STORE, "data"),
        prevent_initial_call=True,
    )
    def export_supply(n_clicks, sid):
        if not n_clicks or not sid:
            return no_update
        res = build_supply_excel(sid)
        if res is None:
            return no_update
        content, name = res
        return dcc.send_bytes(content, filename=name)
