# gear/app/daily_sales/assistant/reports_panel.py
"""Готовые отчёты в окне ИИ-помощника (дашборд продаж): те же, что на кнопках бота.

Выбор отчёта и периода → карточка в ленте чата (цифры, график, таблицы) и ссылки
на Excel/PDF. ИИ не вызывается, в контекст разговора отчёты не попадают.
"""
from __future__ import annotations

import base64
import html as _html
import re
import time
from datetime import date
from urllib.parse import urlencode

from dash import dcc, html
from dash_iconify import DashIconify

REP_ID = "assistant-rep"
PRESET_ID = "assistant-rep-preset"
RANGE_ID = "assistant-rep-range"
RANGE_BOX_ID = "assistant-rep-range-box"
SHOW_ID = "assistant-rep-show"
CUSTOM = "custom"
MAX_ROWS = 12


def _menu():
    from . import menu
    return menu


# ------------------------------------------------------------------ панель выбора
def preset_options(rep: str) -> list[dict]:
    m = _menu()
    if rep == "n":
        items = m.WEEK_PRESETS
    elif rep in m.SINGLE_DAY:
        items = (("y", "Вчера"),)
    else:
        items = m.PRESETS
    label = "Другая дата" if rep in m.SINGLE_DAY else "Свой период"
    return [{"label": t, "value": c} for c, t in items] + [{"label": "📅 " + label, "value": CUSTOM}]


def report_bar():
    m = _menu()
    reps = [{"label": t, "value": k} for k, t in m.REPORTS.items()]
    first = reps[0]["value"]
    opts = preset_options(first)
    return html.Div(className="asst-reports", children=[
        html.Div([DashIconify(icon="solar:chart-square-linear", width=14),
                  html.Span("Готовые отчёты · без ИИ")], className="asst-rep-label"),
        html.Div(className="asst-rep-row", children=[
            dcc.Dropdown(id=REP_ID, options=reps, value=first, clearable=False, searchable=False,
                         className="asst-rep-dd asst-rep-main", optionHeight=34, maxHeight=260),
            dcc.Dropdown(id=PRESET_ID, options=opts, value=opts[0]["value"], clearable=False,
                         searchable=False, className="asst-rep-dd asst-rep-period", optionHeight=34),
            html.Button("Показать", id=SHOW_ID, className="asst-rep-btn"),
        ]),
        html.Div(id=RANGE_BOX_ID, className="asst-rep-range", style={"display": "none"}, children=[
            dcc.DatePickerRange(id=RANGE_ID, display_format="DD.MM.YYYY", first_day_of_week=1,
                                min_date_allowed=m.DATA_START, start_date_placeholder_text="с",
                                end_date_placeholder_text="по", minimum_nights=0,
                                number_of_months_shown=1, with_portal=False),
        ]),
    ])


# ------------------------------------------------------------------ расчёт
def _d(v) -> date | None:
    try:
        return date.fromisoformat(str(v or "")[:10])
    except ValueError:
        return None


def run_report(rep: str, code: str, start, end) -> dict:
    """Сообщение ленты чата с отчётом (или с ошибкой)."""
    m = _menu()
    if rep not in m.REPORTS:
        return _err("Выберите отчёт.")
    hi = m.loaded()
    if code and code != CUSTOM:
        a, b = m.preset(code, hi)
    else:
        a, b = _d(start), _d(end) or _d(start)
        if not a:
            return _err("Укажите даты в календаре.")
        a, b = sorted((max(a, m.DATA_START), min(b, hi)))
        if rep in m.SINGLE_DAY:
            a = b
    t0 = time.time()
    label = f"{m.REPORTS[rep]} · {m.span(a, b)}"
    print(f"[assistant] отчёт: {label}", flush=True)
    try:
        res = m.build(rep, a, b)
    except Exception as e:
        print(f"[assistant] отчёт {rep}: {type(e).__name__}: {e}", flush=True)
        return _err(f"{label}: не получилось посчитать — попробуйте позже.")
    print(f"[assistant] отчёт за {time.time() - t0:.1f} c", flush=True)
    if not res:
        return _err(f"{label}: за этот период данных нет.")
    photo = res.get("photo")
    return {"role": "assistant", "content": res["text"], "meta": {
        "report": rep, "a": a.isoformat(), "b": b.isoformat(), "label": label,
        "img": base64.b64encode(photo).decode() if isinstance(photo, (bytes, bytearray)) else None,
        "files": [list(f) for f in res.get("files") or ()],
        "tables": _plain(res.get("tables") or [])[:3]}}


def _err(text):
    return {"role": "assistant", "content": text, "meta": {"error": True, "report": "-"}}


def _plain(v):
    from gear.tgapp import _clean
    return _clean(v)


# ------------------------------------------------------------------ отрисовка
def _md(s: str) -> str:
    """Telegram HTML → Markdown одной строки."""
    s = re.sub(r"</?b>", "**", s or "")
    s = re.sub(r"</?i>", "_", s)
    s = re.sub(r"</?code>", "`", s)
    s = re.sub(r"<[^>]+>", "", s)
    return _html.unescape(s).replace("****", "")


def _txt(s: str) -> str:
    return _html.unescape(re.sub(r"<[^>]+>", "", s or ""))


def _fmt(v, kind):
    if v is None or v == "":
        return "—"
    if kind == "text" or not isinstance(v, (int, float)):
        return str(v)
    if kind == "pct":
        return f"{v:.1f} %".replace(".", ",")
    s = f"{abs(v):,.0f}".replace(",", " ")
    sign = "−" if v < 0 else ("+" if kind == "signed" and v > 0 else "")
    return sign + s + (" ₽" if kind == "rub" else "")


def _table(t: dict):
    cols, kinds, rows = t.get("cols") or [], t.get("kinds") or [], t.get("rows") or []
    more = len(rows) - MAX_ROWS
    return html.Div(className="asst-rep-table", children=[
        html.Div(t.get("title") or "", className="asst-rep-ttl"),
        html.Div(className="asst-rep-scroll", children=html.Table([
            html.Thead(html.Tr([html.Th(c, className="" if k == "text" else "num")
                                for c, k in zip(cols, kinds)])),
            html.Tbody([html.Tr([html.Td(_fmt(v, k), className="" if k == "text" else "num")
                                 for v, k in zip(r, kinds)]) for r in rows[:MAX_ROWS]]),
        ])),
        html.Div(f"…ещё {more} строк — в Excel", className="asst-rep-more") if more > 0 else None,
    ])


def _file(meta, code, label):
    q = urlencode({"rep": meta["report"], "code": code, "a": meta["a"], "b": meta["b"]})
    pdf = "pdf" in label.lower()
    return html.A(href=f"/admin/assistant/report-file/?{q}", className="asst-file", target="_blank",
                  children=[
                      html.Div(DashIconify(icon="vscode-icons:file-type-pdf2" if pdf
                                           else "vscode-icons:file-type-excel", width=24),
                               className="asst-file-icon"),
                      html.Div(className="asst-file-text", children=[
                          html.Div(label.replace("Excel: ", "").replace("PDF: ", ""),
                                   className="asst-file-name"),
                          html.Div("PDF" if pdf else "Excel", className="asst-file-sub")]),
                      DashIconify(icon="solar:download-minimalistic-bold", width=20,
                                  className="asst-file-dl")])


def report_bubble(msg: dict):
    from gear.tgapp import blocks
    meta = msg.get("meta") or {}
    b = blocks(msg["content"])
    body = [html.Div(_txt(b["title"]), className="asst-rep-title")]
    if b["sub"]:
        body.append(html.Div(_txt(b["sub"]), className="asst-rep-sub"))
    if b["kpis"]:
        body.append(html.Div(className="asst-kpis", children=[
            html.Div(className="asst-kpi", children=[
                html.Div(_txt(k["label"]), className="asst-kpi-l"),
                html.Div(_txt(k["value"]), className="asst-kpi-v"),
                html.Div(_txt(k["rest"]).strip(" ·,()"), className="asst-kpi-r") if k["rest"] else None,
            ]) for k in b["kpis"]]))
    if meta.get("img"):
        body.append(html.Img(src="data:image/png;base64," + meta["img"], className="asst-rep-img"))
    for s in b["sections"]:
        parts = []
        if s["title"]:
            parts.append(html.Div(_txt(s["title"]), className="asst-rep-h"))
        if s["text"]:
            parts.append(dcc.Markdown("  \n".join(_md(x) for x in s["text"]), className="asst-md"))
        if s["rows"]:
            parts.append(dcc.Markdown("\n".join("- " + _md(x) for x in s["rows"]), className="asst-md"))
        body.append(html.Div(parts, className="asst-rep-sec"))
    for t in meta.get("tables") or ():
        body.append(_table(t))
    for n in b["notes"]:
        body.append(html.Div(_txt(n), className="asst-rep-note"))
    if meta.get("files"):
        body.append(html.Div([_file(meta, c, lbl) for c, lbl in meta["files"]], className="asst-rep-files"))
    return html.Div(className="asst-row bot", children=[
        html.Div(DashIconify(icon="solar:chart-square-bold", width=14), className="asst-mini-avatar"),
        html.Div(body, className="asst-msg bot asst-rep-card"),
    ])


# ------------------------------------------------------------------ файл (Django view)
def report_file(request):
    """Excel/PDF отчёта по кнопке — только сотрудникам (admin_view)."""
    from urllib.parse import quote
    from django.http import HttpResponse
    m = _menu()
    g = request.GET
    rep, code, a, b = g.get("rep", ""), g.get("code", ""), _d(g.get("a")), _d(g.get("b"))
    if rep not in m.REPORTS or not a or not b:
        return HttpResponse("Нет такого отчёта.", status=400, content_type="text/plain; charset=utf-8")
    try:
        f = m.file(rep, code, a, b)
    except Exception as e:
        print(f"[assistant] файл {rep}/{code}: {type(e).__name__}: {e}", flush=True)
        f = None
    if not f:
        return HttpResponse("Данных для файла нет.", status=404, content_type="text/plain; charset=utf-8")
    name, data, mime = f
    resp = HttpResponse(data, content_type=mime)
    resp["Content-Disposition"] = f"attachment; filename*=UTF-8''{quote(name)}"
    return resp
