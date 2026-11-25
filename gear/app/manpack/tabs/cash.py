# gear/app/manpack/tabs/cash.py
"""Движение денег: фильтры по периоду, банку, контрагенту, договору, статье."""
from __future__ import annotations

from datetime import date

import dash_mantine_components as dmc
import plotly.graph_objects as go
from dash import dcc, html

from .. import data
from ..config import (CF_BANK_ID, CF_CONTRACT_ID, CF_CP_ID, CF_DIR_ID, CF_GROUP_ID,
                      CF_ITEM_ID, CF_PERIOD_ID, CF_RESULT_ID, x_btn)
from ..theme import (NEG, POS, card, col, empty, export_button, figure, grid, kpi, money,
                     num)

GROUPS = [
    ("ops", "Операции (без группировки)"),
    ("cp", "По контрагентам"),
    ("contract", "По договорам"),
    ("item", "По статьям"),
    ("subitem", "По подстатьям"),
    ("bank", "По банковским счетам"),
    ("day", "По дням"),
    ("month", "По месяцам"),
]
POP = {"zIndex": 10020}


def _options(series, limit=3000):
    vals = sorted({v for v in series.dropna().unique() if v and v != "—"})
    return vals[:limit]


def build(me: date):
    start, end = data.month_start(me), me
    year = data.cf_frame(date(me.year, 1, 1), me)   # для списков фильтров
    with_bank = data.has_bank_dimension()
    filters = [
        dmc.DatePickerInput(id=CF_PERIOD_ID, type="range", label="Период",
                            value=[start.isoformat(), end.isoformat()],
                            valueFormat="DD.MM.YYYY", radius=0, size="sm", popoverProps=POP,
                            className="mp-f"),
        dmc.MultiSelect(id=CF_CP_ID, label="Контрагент", placeholder="Все",
                        data=_options(year["cp"]), searchable=True, clearable=True,
                        radius=0, size="sm", comboboxProps=POP, className="mp-f grow",
                        limit=200),
        dmc.MultiSelect(id=CF_CONTRACT_ID, label="Договор", placeholder="Все",
                        data=_options(year["contract"]), searchable=True, clearable=True,
                        radius=0, size="sm", comboboxProps=POP, className="mp-f grow",
                        limit=200),
        dmc.MultiSelect(id=CF_ITEM_ID, label="Статья", placeholder="Все",
                        data=_options(year["item"]), searchable=True, clearable=True,
                        radius=0, size="sm", comboboxProps=POP, className="mp-f grow"),
        dmc.MultiSelect(id=CF_BANK_ID, label="Банковский счёт", placeholder="Все",
                        data=_options(year["bank"]) if with_bank else [],
                        searchable=True, clearable=True, radius=0, size="sm",
                        comboboxProps=POP, className="mp-f grow",
                        style={} if with_bank else {"display": "none"}),
        dmc.Select(id=CF_DIR_ID, label="Направление", value="all", allowDeselect=False,
                   data=[{"value": "all", "label": "Все"},
                         {"value": "in", "label": "Поступления"},
                         {"value": "out", "label": "Выплаты"}],
                   radius=0, size="sm", comboboxProps=POP, className="mp-f"),
        dmc.Select(id=CF_GROUP_ID, label="Показать", value="ops", allowDeselect=False,
                   data=[{"value": k, "label": v} for k, v in GROUPS
                         if with_bank or k != "bank"],
                   radius=0, size="sm", comboboxProps=POP, className="mp-f"),
    ]
    return [
        card("Движение денежных средств", [
            html.Div(filters, className="mp-filters"),
            dcc.Loading(type="dot", color="#2F6656",
                        children=html.Div(id=CF_RESULT_ID, className="mp-result")),
        ], subtitle="выплаты со знаком минус",
            actions=export_button(x_btn("cash"), "Выгрузить, Excel")),
    ]


def filtered(period, cps, contracts, items, banks, direction):
    if not period or len(period) < 2 or not period[0] or not period[1]:
        return None, None, None
    start = date.fromisoformat(str(period[0])[:10])
    end = date.fromisoformat(str(period[1])[:10])
    df = data.cf_frame(start, end)
    if cps:
        df = df[df["cp"].isin(cps)]
    if contracts:
        df = df[df["contract"].isin(contracts)]
    if items:
        df = df[df["item"].isin(items)]
    if banks:
        df = df[df["bank"].isin(banks)]
    if direction == "in":
        df = df[df["amount"] > 0]
    elif direction == "out":
        df = df[df["amount"] < 0]
    return df, start, end


def grouped(df, group):
    """→ (колонки, строки) для экрана и Excel."""
    import pandas as pd
    if group == "ops":
        d = df.sort_values(["d", "amount"], ascending=[False, True])
        cols = ["Дата", "Банковский счёт", "Контрагент", "Договор", "Статья", "Подстатья",
                "Сумма, ₽"]
        rows = [[r.d, r.bank, r.cp, r.contract, r.item, r.subitem, round(r.amount, 2)]
                for r in d.itertuples()]
        return cols, rows
    key = {"cp": "cp", "contract": "contract", "item": "item", "subitem": "subitem",
           "bank": "bank", "day": "d"}.get(group)
    d = df.copy()
    if group == "month":
        d["m"] = pd.to_datetime(d["d"]).dt.strftime("%Y-%m")
        key = "m"
    g = d.groupby(key).agg(
        inflow=("amount", lambda s: s[s > 0].sum()),
        outflow=("amount", lambda s: s[s < 0].sum()),
        net=("amount", "sum"), n=("amount", "size"),
        first=("d", "min"), last=("d", "max")).reset_index()
    g = g.sort_values(key) if group in ("day", "month") else g.reindex(
        g["net"].abs().sort_values(ascending=False).index)
    label = dict(GROUPS)[group].replace("По ", "").capitalize()
    cols = [label, "Поступления, ₽", "Выплаты, ₽", "Сальдо, ₽", "Операций",
            "Первая операция", "Последняя операция"]
    rows = [[getattr(r, key), round(r.inflow, 2), round(r.outflow, 2), round(r.net, 2),
             int(r.n), r.first, r.last] for r in g.itertuples()]
    return cols, rows


def result(period, cps, contracts, items, banks, direction, group):
    df, start, end = filtered(period, cps, contracts, items, banks, direction)
    if df is None:
        return empty("Выберите период")
    if df.empty:
        return empty("По выбранным условиям движений нет")
    inflow = df.loc[df["amount"] > 0, "amount"].sum()
    outflow = df.loc[df["amount"] < 0, "amount"].sum()

    by_day = df.groupby("d")["amount"].agg(
        inflow=lambda s: s[s > 0].sum(), outflow=lambda s: s[s < 0].sum()).reset_index()
    fig = go.Figure()
    fig.add_bar(x=by_day["d"], y=by_day["inflow"], name="Поступления", marker_color=POS,
                hovertemplate="%{y:,.0f} ₽<extra>Поступления</extra>")
    fig.add_bar(x=by_day["d"], y=by_day["outflow"], name="Выплаты", marker_color=NEG,
                hovertemplate="%{y:,.0f} ₽<extra>Выплаты</extra>")
    fig.update_layout(barmode="relative")

    cols, rows = grouped(df, group or "ops")
    fields = [f"c{i}" for i in range(len(cols))]
    row_data = [{f: (v.strftime("%d.%m.%Y") if hasattr(v, "strftime") else v)
                 for f, v in zip(fields, r)} for r in rows[:20000]]
    defs = []
    for f, c in zip(fields, cols):
        if c.endswith("₽"):
            defs.append(col(f, c, "num2", width=150))
        elif c == "Операций":
            defs.append(col(f, c, "num", width=110))
        elif "дата" in c.lower() or "операция" in c.lower() or c == "Дата":
            defs.append(col(f, c, width=125))
        else:
            defs.append(col(f, c, width={"Контрагент": 240, "Договор": 240, "Статья": 220,
                                         "Подстатья": 260, "Банковский счёт": 230}.get(c, 220),
                            tooltipField=f))
    return [
        html.Div(className="mp-kpis compact", children=[
            kpi("Поступления", money(inflow), tone="pos"),
            kpi("Выплаты", money(outflow), tone="expense"),
            kpi("Сальдо", money(inflow + outflow), tone="neg" if inflow + outflow < 0 else None),
            kpi("Операций", num(len(df)), sub=f"{start:%d.%m.%Y} – {end:%d.%m.%Y}"),
        ]),
        figure(fig, 220),
        grid("mp-cf-grid", row_data, defs, height=520),
        html.Div(f"Показано строк: {num(len(row_data))} из {num(len(rows))}",
                 className="mp-foot") if len(rows) > len(row_data) else None,
    ]
