# gear/app/manpack/tabs/contracts.py
"""Договоры: поиск по контрагенту и номеру, открытие прикреплённых файлов."""
from __future__ import annotations

from datetime import date

import dash_mantine_components as dmc
from dash import dcc, html

from .. import data
from ..config import CT_FILES_ID, CT_RESULT_ID, CT_SEARCH_ID, CT_TYPE_ID, x_btn
from ..theme import card, col, empty, export_button, grid, icon, month_title, num

POP = {"zIndex": 10020}


def build(me: date):
    return [
        card("Договоры", [
            html.Div(className="mp-filters", children=[
                dmc.TextInput(id=CT_SEARCH_ID, label="Контрагент, номер договора или ИНН",
                              placeholder="Начните вводить…", radius=0, size="sm",
                              debounce=500, className="mp-f grow",
                              leftSection=icon("solar:magnifer-linear", 16)),
                dmc.Select(id=CT_TYPE_ID, label="Тип договора", placeholder="Все типы",
                           data=data.contract_titles(), clearable=True, searchable=True,
                           radius=0, size="sm", comboboxProps=POP, className="mp-f grow"),
                dmc.Switch(id=CT_FILES_ID, label="Только с файлами", checked=True, radius=0,
                           color="#2F6656", size="sm", className="mp-f switch"),
            ]),
            dcc.Loading(type="dot", color="#2F6656",
                        children=html.Div(id=CT_RESULT_ID, className="mp-result")),
        ], subtitle="файлы открываются по клику",
            actions=[export_button(x_btn("ct_paid"), "Платежи месяца по методам учёта, Excel"),
                     export_button(x_btn("contracts"), "Реестр, Excel")]),
    ]


def table(search, title, only_files):
    """→ (колонки, строки) для Excel."""
    items = data.contracts(search or "", title or None, bool(only_files), limit=5000)
    cols = ["Контрагент", "ИНН", "Тип договора", "Номер", "Дата", "Дата окончания",
            "Наша компания", "Валюта", "Подписан", "Доп. соглашение", "Файлов"]
    rows = [[c["cp"], c["inn"], c["type"], c["number"], c["date"], c["date_end"], c["owner"],
             c["currency"], "да" if c["signed"] else "нет", "да" if c["amendment"] else "",
             len(c["files"])]
            for c in items]
    return cols, rows


def paid_tables(me: date):
    """Договоры с платежами за месяц по методу учёта → листы Excel."""
    df = data.contracts_paid(data.month_start(me), me)
    if df.empty:
        return []
    cols = ["Контрагент", "Тип договора", "Номер", "Дата договора", "Дата окончания",
            "Функция списания", "Условий, шт", "Поступления, ₽", "Выплаты, ₽",
            "Операций, шт", "Последняя операция"]
    sub = f"{month_title(me)} · договоры с движением денег"
    out = []
    order = sorted(df["group"].unique(), key=lambda g: (g == "Без функции списания", g))
    for g in order:
        part = df[df["group"] == g].sort_values("outflow")
        rows = [[r.cp, r.type, r.number, r.date, r.date_end, r.fn or "нет", r.conditions,
                 r.inflow, r.outflow, r.n, r.last] for r in part.itertuples()]
        out.append((g[:31], g, sub, cols, rows))
    return out


def result(search, title, only_files):
    items = data.contracts(search or "", title or None, bool(only_files))
    if not items:
        return empty("Договоры не найдены")
    today = date.today()
    rows = []
    for c in items:
        files = " · ".join(f"[{f['name']}]({f['url']})" for f in c["files"][:6])
        end = c["date_end"]
        rows.append({
            "cp": c["cp"], "type": c["type"] + (" · доп. соглашение" if c["amendment"] else ""),
            "number": f"[{c['number']}](/admin/contracts/contracts/{c['id']}/change/)",
            "date": c["date"].strftime("%d.%m.%Y") if c["date"] else "",
            "end": end.strftime("%d.%m.%Y") if end else "",
            "left": (end - today).days if end else None,
            "files": files or "—",
        })
    soon = {"styleConditions": [
        {"condition": "params.data.left != null && params.data.left < 0",
         "style": {"color": "#8A8A8A"}},
        {"condition": "params.data.left != null && params.data.left >= 0 && params.data.left <= 31",
         "style": {"color": "#A15C38", "fontWeight": 700}}]}
    cols = [col("cp", "Контрагент", width=300), col("type", "Тип договора", width=230),
            col("number", "Номер", "link", width=170), col("date", "Дата", width=115),
            col("end", "Окончание", width=125, cellStyle=soon),
            col("files", "Файлы", "link", width=420)]
    with_files = sum(1 for c in items if c["files"])
    return [
        html.Div(f"Найдено договоров: {num(len(items))}, с файлами: {num(with_files)}"
                 + (" · показаны первые 500, уточните поиск" if len(items) >= 500 else "")
                 + " · окончание — последняя дата окончания условий договора",
                 className="mp-foot top"),
        grid("mp-ct-grid", rows, cols, height=560),
    ]
