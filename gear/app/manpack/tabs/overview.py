# gear/app/manpack/tabs/overview.py
"""Обзор месяца: ключевые показатели, выводы, уведомления, динамика."""
from __future__ import annotations

from datetime import date

import plotly.graph_objects as go
from dash import html

from .. import data
from ..config import x_btn
from ..insights import notifications
from ..theme import (EXPENSE, GREEN, GREEN_2, MONTHS_SHORT, NEG, POS, SLATE, card, delta,
                     empty, export_button, figure, fmt_date, icon, kpi, money, month_title,
                     note, pct)


def _kpis(me, b):
    d = b["derived"].get(me)
    prev_me = data.prev_month_end(me)
    p = b["derived"].get(prev_me)
    if not d:
        return empty("За этот месяц нет данных P&L")
    g = lambda x, k: (x or {}).get(k)

    cash_now = cash_prev = None
    try:
        cm, _ = data.cf_months(min(me, date.today()), 14)
        by = {data.month_end(m): cl for m, op, net, cl, _ in cm}
        cash_now, cash_prev = by.get(me), by.get(prev_me)
    except Exception:
        pass

    debt = None
    try:
        ln = data.loans(min(me, date.today()))
        if not ln.empty:
            debt = float(ln.loc[ln["loan_direction"] == "borrowed", "total_debt"].sum())
    except Exception:
        pass

    zfp = d.get("zfp_pct")
    conv = d.get("conv") or 0.0
    return html.Div(className="mp-kpis four", children=[
        kpi("Выручка без НДС", money(d["rev"]), delta_el=delta(d["rev"], g(p, "rev")),
            hint="Чистая выручка до СПП без НДС — строка 1.4 P&L"),
        kpi("Маржинальный доход", money(d["md"]), sub=f"КМД {pct(d.get('kmd'))}",
            delta_el=delta(d["md"], g(p, "md")),
            hint="Выручка минус переменные затраты: себестоимость, комиссия, разделы 3 и 4"),
        kpi("Постоянные затраты", money(d["fc"]), delta_el=delta(d["fc"], g(p, "fc"), good_up=True),
            tone="expense", hint="Разделы 6, 7 и 8 P&L (со знаком минус)"),
        kpi("Результат до налога", money(d["ebt"]), delta_el=delta(d["ebt"], g(p, "ebt")),
            tone="neg" if d["ebt"] < 0 else "pos"),
        kpi("Чистая прибыль", money(d["net"]), delta_el=delta(d["net"], g(p, "net")),
            sub=(f"без конв. займов {money(d['net'] - conv)}" if conv else None),
            tone="neg" if d["net"] < 0 else "pos",
            hint="С учётом всей финансовой нагрузки; ниже — без процентов по конвертируемым займам"),
        kpi("Точка безубыточности", money(d.get("tbu")),
            sub=(f"запас прочности {pct(zfp)}"
                 + (f" · без конв. займов {money(d.get('tbu_ex'))}" if conv else ""))
            if zfp is not None else "не определена",
            tone="neg" if (zfp is not None and zfp < 0) else None,
            hint="Выручка, при которой результат до налога равен нулю: постоянные затраты / КМД"),
        kpi("Деньги на конец месяца", money(cash_now), delta_el=delta(cash_now, cash_prev),
            hint="Остаток денежных средств по Cash Flow на конец месяца"),
        kpi("Долг по займам и кредитам", money(debt), sub="мы должны, с процентами",
            tone="expense", hint="Тело и начисленные проценты по полученным займам и кредитам"),
    ])


def _conclusions(me, s):
    tone = {"bad": "bad", "warn": "warn"}.get(s.get("tone"), "good")
    blocks = []
    for n, (head, paras) in enumerate(s.get("blocks", []), 1):
        blocks.append(html.Div(className="mp-concl", children=[
            html.Div(f"{n:02d}", className="mp-concl-no"),
            html.Div([html.Div(head, className="mp-concl-title"),
                      *[html.P(p) for p in paras]], className="mp-concl-body"),
        ]))
    partial = s.get("partial")
    return [
        html.Div(className=f"mp-headline {tone}", children=[
            icon("solar:flag-linear" if tone == "good" else "solar:danger-triangle-linear", 20),
            html.Div(s.get("headline", "")),
        ]),
        note("Месяц неполный: данные за %d из %d дней." % partial, "warn") if partial else None,
        html.Div(blocks, className="mp-concl-list"),
    ]


def _alerts(items):
    return html.Div(className="mp-alerts", children=[
        html.Div(className=f"mp-alert {i['tone']}", children=[
            html.Div(icon(i["icon"], 18), className="mp-alert-icon"),
            html.Div([html.Div(i["title"], className="mp-alert-title"),
                      html.Div(i["text"], className="mp-alert-text"),
                      html.Ul([html.Li(x) for x in i["items"]], className="mp-alert-list")
                      if i.get("items") else None]),
        ]) for i in items])


def _dynamics(me, b):
    ms = [m for m in b["months"] if m <= me][-13:]
    x = [f"{MONTHS_SHORT[m.month - 1]} {str(m.year)[2:]}" for m in ms]
    der = [b["derived"][m] for m in ms]
    fig = go.Figure()
    fig.add_bar(x=x, y=[d["rev"] for d in der], name="Выручка без НДС", marker_color=GREEN_2,
                hovertemplate="%{y:,.0f} ₽<extra>Выручка</extra>")
    fig.add_bar(x=x, y=[d["md"] for d in der], name="Маржинальный доход", marker_color="#A9CBBF",
                hovertemplate="%{y:,.0f} ₽<extra>МД</extra>")
    fig.add_scatter(x=x, y=[d["net"] for d in der], name="Чистая прибыль", mode="lines+markers",
                    line=dict(color=SLATE, width=2),
                    marker=dict(size=7, color=[POS if d["net"] >= 0 else NEG for d in der]),
                    hovertemplate="%{y:,.0f} ₽<extra>Чистая прибыль</extra>")
    has_conv = any(d.get("conv") for d in der)
    if has_conv:
        # проценты по конвертируемым займам — расход (со знаком минус): без них прибыль выше
        net_ex = [d["net"] - (d.get("conv") or 0.0) for d in der]
        fig.add_scatter(x=x, y=net_ex, name="Чистая прибыль без конв. займов",
                        mode="lines+markers", line=dict(color=GREEN, width=2, dash="dash"),
                        marker=dict(size=6, symbol="diamond",
                                    color=[POS if v >= 0 else NEG for v in net_ex]),
                        hovertemplate="%{y:,.0f} ₽<extra>Чистая прибыль без конв. займов</extra>")
    # ТБУ при околонулевой марже уходит в сотни миллионов и сплющивает график
    cap = 3 * max([abs(d["rev"] or 0) for d in der] or [0])
    clip = lambda v: v if v is not None and v == v and 0 <= v <= cap else None
    fig.add_scatter(x=x, y=[clip(d.get("tbu")) for d in der], name="Точка безубыточности",
                    mode="lines", line=dict(color=EXPENSE, width=1.5, dash="dot"),
                    hovertemplate="%{y:,.0f} ₽<extra>ТБУ</extra>")
    if has_conv:
        fig.add_scatter(x=x, y=[clip(d.get("tbu_ex")) for d in der], name="ТБУ без конв. займов",
                        mode="lines", line=dict(color="#C9A28F", width=1.5, dash="dot"),
                        hovertemplate="%{y:,.0f} ₽<extra>ТБУ без конв. займов</extra>")
    fig.update_layout(barmode="group", bargap=0.25)
    return figure(fig, 360)


def _cash_chart(me):
    try:
        cm, _ = data.cf_months(min(me, date.today()), 13)
    except Exception:
        return empty("Нет данных Cash Flow")
    cm = [r for r in cm if data.month_end(r[0]) <= me]
    if not cm:
        return empty("Нет данных Cash Flow")
    x = [f"{MONTHS_SHORT[m.month - 1]} {str(m.year)[2:]}" for m, *_ in cm]
    fig = go.Figure()
    fig.add_bar(x=x, y=[net for _, _, net, _, _ in cm], name="Сальдо месяца",
                marker_color=[POS if net >= 0 else NEG for _, _, net, _, _ in cm],
                opacity=0.55, hovertemplate="%{y:,.0f} ₽<extra>Сальдо</extra>")
    fig.add_scatter(x=x, y=[cl for *_, cl, _ in cm], name="Остаток на конец", mode="lines+markers",
                    line=dict(color=GREEN, width=2.5),
                    hovertemplate="%{y:,.0f} ₽<extra>Остаток</extra>")
    return figure(fig, 360)


def _cost_changes(me):
    try:
        rows = data.cost_changes(me)
    except Exception as e:
        return note(f"Не удалось посчитать изменения затрат: {e}", "warn")
    if not rows:
        return empty("Заметных изменений затрат к прошлому месяцу нет")
    cell = lambda v: html.Td(f"({money(abs(v), unit=False)})" if v < 0 else money(v, unit=False),
                             className="num" + (" neg" if v < 0 else ""))
    body = []
    for r in rows:
        worse = r["diff"] < 0                      # расход вырос или доход упал
        body.append(html.Tr([
            html.Td([html.Span(f"разд. {r['sec']} ", className="mp-sec-tag"), r["item"]],
                    className="name"),
            cell(r["prev"]), cell(r["cur"]),
            html.Td(("−" if worse else "+") + money(abs(r["diff"]), unit=False),
                    className="num " + ("bad" if worse else "good")),
        ]))
    return html.Div(className="mp-table-wrap plain", children=html.Table(
        className="mp-table compact", children=[
            html.Thead(html.Tr([html.Th("Статья"), html.Th("Прошлый месяц"),
                                html.Th("Этот месяц"), html.Th("Влияние на прибыль")])),
            html.Tbody(body)]))


def build(me: date):
    b = data.pl_bundle()
    try:
        s = data.month_summary(me)
    except Exception as e:
        s = {"headline": f"Выводы за месяц недоступны: {e}", "tone": "warn", "blocks": []}
    return [
        html.Div(className="mp-section-head", children=[
            html.Div([html.Span(month_title(me), className="mp-h1"),
                      html.Span(f"данные на {fmt_date(b['report_date'])}",
                                className="mp-h1-sub")]),
        ]),
        _kpis(me, b),
        html.Div(className="mp-grid-2", children=[
            card("Выводы за месяц", _conclusions(me, s),
                 actions=export_button(x_btn("summary"), "Выводы, Excel")),
            card("Важное в этом месяце", _alerts(notifications(me)),
                 ),
        ]),
        card("Что изменилось в затратах", _cost_changes(me),
             subtitle="10 статей с наибольшим изменением к прошлому месяцу, ₽"),
        html.Div(className="mp-grid-2 even stretch", children=[
            card("Выручка, маржа и прибыль", _dynamics(me, b), subtitle="13 месяцев, ₽ без НДС"),
            card("Деньги: остаток и сальдо", _cash_chart(me), subtitle="по Cash Flow, ₽"),
        ]),
    ]
