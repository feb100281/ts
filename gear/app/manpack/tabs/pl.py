# gear/app/manpack/tabs/pl.py
"""P&L по месяцам года — те же строки и цифры, что в мэн паке."""
from __future__ import annotations

from datetime import date

import dash_mantine_components as dmc
from dash import dcc, html

from .. import data
from ..config import PL_CP_RESULT_ID, PL_ITEM_ID, x_btn
from ..theme import MONTHS_SHORT, card, col, empty, export_button, grid, month_title, num

KEY_ROWS = [
    ("rev", "Выручка без НДС", "money", "b"),
    ("cogs", "Себестоимость", "money", ""),
    ("comm", "Комиссия WB", "money", ""),
    ("sell", "Расходы на реализацию (разд. 3)", "money", ""),
    ("promo", "Продвижение WB (разд. 4)", "money", ""),
    ("md", "Маржинальный доход", "money", "b"),
    ("kmd", "КМД, %", "pct", "i"),
    ("other", "Прочие доходы и расходы (разд. 5)", "money", ""),
    ("ovh", "Накладные расходы (разд. 6)", "money", ""),
    ("corp", "Корпоративные расходы (разд. 7)", "money", ""),
    ("fin", "Финансовые расходы (разд. 8)", "money", ""),
    ("fc", "Постоянные затраты (6 + 7 + 8)", "money", "b"),
    ("ebt", "Результат до налога", "money", "b"),
    ("tax", "Налог на прибыль", "money", ""),
    ("net", "Чистая прибыль", "money", "total"),
    ("tbu", "Точка безубыточности", "money", "i"),
    ("zfp_pct", "Запас финансовой прочности, %", "pct", "i"),
    ("tbu_ex", "ТБУ без процентов по конв. займам", "money", "i"),
]
NO_TOTAL_SECTIONS = ("1.", "2.")


def _cell(v, kind):
    if v is None or v != v:
        return html.Td("–", className="num muted")
    cls = "num" + (" neg" if v < 0 else "")
    if kind == "pct":
        return html.Td(f"{v:.1f}".replace(".", ",") + " %", className=cls)
    txt = num(abs(v)) if v >= 0 else f"({num(abs(v))})"
    return html.Td(txt, className=cls)


def table_data(me: date):
    """→ (месяцы, заголовки, ключевые строки, детальные строки) для экрана и Excel."""
    b = data.pl_bundle()
    ms = [m for m in b["months"] if m.year == me.year and m <= me]
    if not ms:
        return [], [], [], []
    ytd = data.derive_period(ms)
    hdr = [MONTHS_SHORT[m.month - 1] for m in ms] + [f"Итого {me.year}"]
    key = []
    for k, label, kind, style in KEY_ROWS:
        vals = [b["derived"][m].get(k) for m in ms] + [ytd.get(k)]
        if k == "conv" and not any(vals):
            continue
        key.append((label, kind, style, vals))

    detail = []
    sections = sorted({s for (m, s, i) in b["pl"] if m in ms})
    for sec in sections:
        items = sorted({i for (m, s, i) in b["pl"] if s == sec and m in ms})
        rows = []
        for it in items:
            vals = [b["pl"].get((m, sec, it)) for m in ms]
            if not any(vals):
                continue
            tot = sum(v or 0 for v in vals)
            is_ratio = "%" in it or sec.strip().startswith("2.")
            rows.append((it, "money", "", vals + [None if is_ratio else tot]))
        if not rows:
            continue
        detail.append((sec.strip(), "head", "", []))
        detail += rows
        if not sec.strip().startswith(NO_TOTAL_SECTIONS):
            tots = [sum((b["pl"].get((m, sec, it)) or 0) for it in items) for m in ms]
            detail.append((f"Итого {sec.strip().split('.')[0]}", "money", "b", tots + [sum(tots)]))
    return ms, hdr, key, detail


def _table(hdr, rows):
    body = []
    for label, kind, style, vals in rows:
        if kind == "head":
            body.append(html.Tr([html.Td(label, colSpan=len(hdr) + 1)], className="sec"))
            continue
        body.append(html.Tr([html.Td(label, className="name")]
                            + [_cell(v, kind) for v in vals], className=style))
    return html.Div(className="mp-table-wrap", children=html.Table(className="mp-table", children=[
        html.Thead(html.Tr([html.Th("Показатель")] + [html.Th(h) for h in hdr])),
        html.Tbody(body),
    ]))


MAX_CHILDREN = 40


def _drill_table(hdr, detail, ms):
    """P&L по статьям с раскрытием: статья → подстатья (разделы 5–8)."""
    try:
        df = data.pl_detail(date(ms[0].year, 1, 1), ms[-1])
    except Exception:
        df = None
    body, sec_no, n = [], "", 0

    def vals(part):
        by = part.groupby("me")["amount"].sum()
        v = [float(by.get(m, 0.0)) or None for m in ms]
        return v + [float(part["amount"].sum())]

    def children(part, level_col, parent, level):
        out = []
        tot = part.groupby(level_col)["amount"].sum()
        names = tot.abs().sort_values(ascending=False).index.tolist()
        for k, name in enumerate(names[:MAX_CHILDREN]):
            sub = part[part[level_col] == name]
            key = f"{parent}/{level}{k}"
            deeper = False
            out.append((name, vals(sub), key, parent, level, deeper))
            if deeper:
                out += children(sub, "cp", key, "c")
        if len(names) > MAX_CHILDREN:
            rest = part[part[level_col].isin(names[MAX_CHILDREN:])]
            out.append((f"Прочие ({len(names) - MAX_CHILDREN})", vals(rest),
                        f"{parent}/{level}x", parent, level, False))
        return out

    for label, kind, style, v in detail:
        if kind == "head":
            sec_no = label.split(".")[0].strip()
            body.append(html.Tr([html.Td(label, colSpan=len(hdr) + 1)], className="sec"))
            continue
        kids = []
        if df is not None and not df.empty and style == "" and sec_no in ("5", "6", "7", "8"):
            part = df[(df["sec"] == sec_no) & (df["item"] == label)]
            if not part.empty:
                n += 1
                key = f"s{sec_no}i{n}"
                subs = part["sub"].unique().tolist()
                # раскрываем, только если внутри статьи есть другие подстатьи
                kids = [] if subs == [label] else children(part, "sub", key, "u")
        if kids:
            body.append(html.Tr([html.Td([html.Span("", className="mp-caret"), label],
                                         className="name")] + [_cell(x, kind) for x in v],
                                className=(style + " exp").strip(), **{"data-key": key}))
            for name, kv, kkey, parent, level, deeper in kids:
                cls = "child lvl-" + ("2" if level == "u" else "3") + (" exp" if deeper else "")
                body.append(html.Tr(
                    [html.Td([html.Span("", className="mp-caret") if deeper else None, name],
                             className="name")] + [_cell(x, "money") for x in kv],
                    className=cls, **{"data-key": kkey, "data-parent": parent}))
        else:
            body.append(html.Tr([html.Td(label, className="name")]
                                + [_cell(x, kind) for x in v], className=style))
    return html.Div(className="mp-table-wrap", children=html.Table(className="mp-table drill", children=[
        html.Thead(html.Tr([html.Th("Показатель")] + [html.Th(h) for h in hdr])),
        html.Tbody(body),
    ]))


SEC_NAMES = {"5": "5. Прочие доходы и расходы", "6": "6. Накладные расходы",
             "7": "7. Корпоративные расходы", "8": "8. Финансовые расходы"}


def _item_options(ms):
    """Статьи и подстатьи разделов 5–8 для расшифровки по контрагентам."""
    try:
        df = data.pl_detail(date(ms[0].year, 1, 1), ms[-1])
    except Exception:
        return []
    out = []
    for sec in sorted(df["sec"].unique()):
        items = []
        part = df[df["sec"] == sec]
        for item in sorted(part["item"].unique()):
            items.append({"value": f"{sec}|{item}|", "label": item})
            subs = sorted(part.loc[part["item"] == item, "sub"].unique())
            if subs != [item]:
                items += [{"value": f"{sec}|{item}|{u}", "label": f"   — {u}"} for u in subs]
        out.append({"group": SEC_NAMES.get(sec, sec), "items": items})
    return out


def counterparties(me: date, value):
    """Контрагенты выбранной статьи — считается только при выборе."""
    if not value:
        return empty("Выберите статью — покажем контрагентов и договоры")
    sec, item, sub = (str(value).split("|") + ["", ""])[:3]
    df = data.pl_item_counterparties(me, sec, item, sub or None)
    if df is None or df.empty:
        return empty("По этой статье начислений нет")
    rows = [{"cp": r.cp, "contract": r.contract, "sub": r.sub, "month": r.month, "ytd": r.ytd}
            for r in df.itertuples()]
    total = [{"cp": f"Итого ({len(rows)})", "month": float(df["month"].sum()),
              "ytd": float(df["ytd"].sum())}]
    return grid("mp-pl-cp-grid", rows, [
        col("cp", "Контрагент", width=280), col("contract", "Договор", width=260),
        col("sub", "Подстатья", width=260),
        col("month", month_title(me), "num", width=160),
        col("ytd", f"С начала {me.year} года", "num", width=180)],
        height=420, pinned_bottom=total)


def build(me: date):
    ms, hdr, key, detail = table_data(me)
    if not ms:
        return [empty("За этот год нет данных P&L")]
    return [
        card("Ключевые показатели", _table(hdr, key),
             subtitle=f"{me.year} год, ₽ без НДС · расходы в скобках",
             actions=export_button(x_btn("pl"), "P&L, Excel")),
        card("P&L по статьям", _drill_table(hdr, detail, ms),
             subtitle="нажмите на статью со стрелкой — раскроются подстатьи (разделы 5–8)"),
        card("Расшифровка статьи по контрагентам", [
            html.Div(className="mp-filters flat", children=[
                dmc.Select(id=PL_ITEM_ID, label="Статья или подстатья", data=_item_options(ms),
                           placeholder="Начните вводить название…", searchable=True,
                           clearable=True, radius=0, size="sm", className="mp-f grow",
                           comboboxProps={"zIndex": 10020}, maxDropdownHeight=380),
            ]),
            dcc.Loading(type="dot", color="#2F6656",
                        children=html.Div(id=PL_CP_RESULT_ID, className="mp-result",
                                          children=counterparties(me, None))),
        ], subtitle="разделы 5–8 · начисления по данным учёта, ₽"),
    ]
