# gear/app/manpack/theme.py
"""Оформление: палитра мэн пака, форматирование чисел, типовые блоки."""
from __future__ import annotations

from datetime import date

import dash_ag_grid as dag
import dash_mantine_components as dmc
from dash import dcc, html
from dash_iconify import DashIconify

GREEN = "#2F6656"
GREEN_2 = "#3D7A67"
GREEN_DARK = "#1F5E4E"
POS = "#2F8F5B"
NEG = "#C0392B"
EXPENSE = "#A15C38"
SLATE = "#5B6770"
MUTED = "#8A8A8A"
LINE = "#E3E8E6"

MONTHS = ("январь", "февраль", "март", "апрель", "май", "июнь", "июль", "август",
          "сентябрь", "октябрь", "ноябрь", "декабрь")
MONTHS_SHORT = ("янв", "фев", "мар", "апр", "май", "июн", "июл", "авг", "сен", "окт", "ноя", "дек")


def month_title(d: date) -> str:
    return f"{MONTHS[d.month - 1].capitalize()} {d.year}"


def money(v, unit=True) -> str:
    if v is None or v != v:
        return "—"
    v = float(v)
    a = abs(v)
    if a >= 1e9:
        s = f"{v / 1e9:.2f} млрд"
    elif a >= 1e6:
        s = f"{v / 1e6:.1f} млн"
    elif a >= 1e3:
        s = f"{v / 1e3:.0f} тыс"
    else:
        s = f"{v:.0f}"
    return (s.replace(".", ",") + (" ₽" if unit else "")).replace("-", "−")


def num(v, d=0) -> str:
    if v is None or v != v:
        return "—"
    return f"{float(v):,.{d}f}".replace(",", " ").replace(".", ",").replace("-", "−")


def pct(v, d=1, sign=False) -> str:
    if v is None or v != v:
        return "—"
    s = f"{float(v):+.{d}f}" if sign else f"{float(v):.{d}f}"
    return s.replace(".", ",").replace("-", "−") + "%"


def fmt_date(d) -> str:
    try:
        return d.strftime("%d.%m.%Y")
    except Exception:
        return "—"


def icon(name, size=18, **kw):
    return DashIconify(icon=name, width=size, height=size, **kw)


def delta(cur, prev, good_up=True, as_pct=True):
    """Изменение к прошлому периоду: стрелка и цвет по смыслу."""
    if cur is None or prev is None or prev != prev or cur != cur:
        return html.Span("", className="mp-delta")
    if as_pct:
        if not prev:
            return html.Span("", className="mp-delta")
        ch = (cur - prev) / abs(prev) * 100
        txt = pct(ch, 1, sign=True)
    else:
        ch = cur - prev
        txt = pct(ch, 1, sign=True).replace("%", " п.п.")
    if abs(ch) < 0.05:
        return html.Span("без изменений", className="mp-delta")
    good = (ch > 0) == good_up
    return html.Span(
        [("▲ " if ch > 0 else "▼ ") + txt, html.Span(" к пред. месяцу", className="mp-delta-note")],
        className="mp-delta " + ("pos" if good else "neg"))


def kpi(title, value, sub=None, delta_el=None, tone=None, hint=None):
    return html.Div(className="mp-kpi" + (f" {tone}" if tone else ""), title=hint or "", children=[
        html.Div(title, className="mp-kpi-title"),
        html.Div(value, className="mp-kpi-value"),
        html.Div([delta_el or "", html.Span(sub or "", className="mp-kpi-sub")],
                 className="mp-kpi-foot"),
    ])


def card(title, children, actions=None, subtitle=None, cls=""):
    head = [html.Div([html.Span(title, className="mp-card-title"),
                      html.Span(subtitle or "", className="mp-card-sub")],
                     className="mp-card-head-text")]
    if actions:
        head.append(html.Div(actions, className="mp-card-actions"))
    return html.Div(className="mp-card " + cls, children=[
        html.Div(head, className="mp-card-head"),
        html.Div(children, className="mp-card-body"),
    ])


def export_button(btn_id, label="Excel"):
    return dmc.Button(label, id=btn_id, n_clicks=0, size="xs", radius=0, variant="default",
                      className="mp-btn", leftSection=icon("solar:download-minimalistic-linear", 15))


def note(text, tone="info"):
    return html.Div(text, className=f"mp-note {tone}")


def empty(text="Нет данных за выбранный период"):
    return html.Div(text, className="mp-empty")


NUM_FMT = {"function": "params.value == null ? '' : Number(params.value).toLocaleString('ru-RU', {maximumFractionDigits: 0})"}
NUM2_FMT = {"function": "params.value == null ? '' : Number(params.value).toLocaleString('ru-RU', {minimumFractionDigits: 2, maximumFractionDigits: 2})"}
PCT_FMT = {"function": "params.value == null ? '' : Number(params.value).toLocaleString('ru-RU', {minimumFractionDigits: 1, maximumFractionDigits: 1}) + ' %'"}
NEG_STYLE = {"styleConditions": [{"condition": "params.value < 0", "style": {"color": NEG}}]}


def col(field, header, kind="text", width=None, **kw):
    c = {"field": field, "headerName": header, "sortable": True, "filter": True,
         "resizable": True}
    if kind in ("num", "num2", "pct"):
        c.update({"type": "rightAligned", "filter": "agNumberColumnFilter",
                  "valueFormatter": {"num": NUM_FMT, "num2": NUM2_FMT, "pct": PCT_FMT}[kind],
                  "cellStyle": NEG_STYLE})
    elif kind == "link":
        c.update({"cellRenderer": "markdown", "linkTarget": "_blank", "filter": False,
                  "sortable": False})
    if width:
        c["width"] = width
    else:
        c["flex"] = 1
        c["minWidth"] = 110
    c.update(kw)
    return c


AUTO_HEIGHT_ROWS = 14        # до стольких строк таблица растёт по содержимому


def grid(grid_id, rows, cols, height=460, pinned_bottom=None, pin=True, fit=True):
    """pin: True — закрепить первую колонку; имя поля — закрепить её; False — не закреплять."""
    if pin and cols and not any(c.get("pinned") for c in cols):
        target = cols[0]["field"] if pin is True else pin

        def _pin(c):
            c = dict(c, pinned="left", lockPinned=True)
            if c.pop("flex", None):                 # у закреплённой колонки ширина фиксированная
                c["width"] = max(c.get("minWidth") or 0, 220)
            return c
        cols = [_pin(c) if c.get("field") == target else c for c in cols]

    free = [c for c in cols if not c.get("pinned")]
    has_text = any(c.get("type") != "rightAligned" for c in free)

    def _stretch(c):
        # свободное место делят текстовые колонки; числовые остаются по своей ширине
        if c.get("pinned"):
            return c
        numeric = c.get("type") == "rightAligned"
        if numeric and has_text:
            if c.get("width"):
                return c
            c = dict(c)
            c.pop("flex", None)
            c["width"] = max(c.get("minWidth") or 0, 130)
            return c
        c = dict(c)
        w = c.pop("width", None) or c.get("minWidth") or 110
        c.update(minWidth=min(w, 160), flex=w)
        return c
    if fit:
        cols = [_stretch(c) for c in cols]

    opts = {"animateRows": False, "rowHeight": 32, "headerHeight": 36,
            "suppressCellFocus": True, "enableCellTextSelection": True}
    if pinned_bottom:
        opts["pinnedBottomRowData"] = pinned_bottom
    n = len(rows) + len(pinned_bottom or [])
    auto = n <= AUTO_HEIGHT_ROWS
    if auto:
        opts["domLayout"] = "autoHeight"
    return dag.AgGrid(
        id=grid_id, rowData=rows, columnDefs=cols,
        defaultColDef={"sortable": True, "resizable": True},
        dashGridOptions=opts, dangerously_allow_code=True,
        style={"height": None if auto else f"{height}px",
               "width": "100%" if fit else f"{sum(c.get('width') or 150 for c in cols) + 4}px",
               "maxWidth": "100%"},
        className="ag-theme-alpine compact-grid mp-grid",
    )


def figure(fig, height=300):
    fig.update_layout(
        height=height, margin=dict(l=8, r=8, t=8, b=8), paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)", font=dict(family="Inter, Helvetica, Arial", size=12,
                                                 color="#3A3F44"),
        legend=dict(orientation="h", y=-0.14, yanchor="top", x=0, font=dict(size=11.5)),
        hovermode="x unified",
        xaxis=dict(showgrid=False, linecolor=LINE),
        yaxis=dict(gridcolor="#EEF1F0", zerolinecolor="#C9D2CE"),
        separators=", ",
    )
    return dcc.Graph(figure=fig, config={"displayModeBar": False}, style={"height": f"{height}px"})
