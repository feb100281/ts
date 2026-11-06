# gear/app/manpack/tabs/fx.py
"""Курсы валют: курс на дату, изменение за месяц и с начала года."""
from __future__ import annotations

from datetime import date, timedelta

import dash_mantine_components as dmc
import plotly.graph_objects as go
from dash import html

from .. import data
from ..config import FX_ALERT_PCT, FX_CUR_ID, FX_CURRENCIES, FX_RESULT_ID, x_btn
from ..theme import (EXPENSE, GREEN, GREEN_2, SLATE, card, empty, export_button, figure,
                     fmt_date, kpi, month_title, note, num, pct)

NAMES = {"USD": "Доллар США", "EUR": "Евро", "CNY": "Китайский юань", "AMD": "Армянский драм"}
COLORS = {"USD": GREEN, "EUR": SLATE, "CNY": EXPENSE, "AMD": GREEN_2}


def stats(me: date):
    """→ [{cur, rate, date, m_ch, y_ch, m0, y0}] и DataFrame за 13 месяцев."""
    end = min(me, date.today())
    start = date(end.year - 1, end.month, 1)
    df = data.fx(start, end)
    out = []
    for cur in FX_CURRENCIES:
        r1, d1 = data.fx_at(df, cur, end)
        if not r1:
            continue
        m0, _ = data.fx_at(df, cur, data.month_start(me) - timedelta(days=1))
        y0, _ = data.fx_at(df, cur, date(me.year, 1, 1) - timedelta(days=1))
        out.append({"cur": cur, "rate": r1, "date": d1, "m0": m0, "y0": y0,
                    "m_ch": (r1 - m0) / m0 * 100 if m0 else None,
                    "y_ch": (r1 - y0) / y0 * 100 if y0 else None})
    return out, df


def chart(me: date, currencies=None):
    """Одна валюта — курс в рублях; несколько — индекс (начало периода = 100)."""
    st, df = stats(me)
    picked = [s for s in st if not currencies or s["cur"] in currencies]
    if not picked:
        return empty("Выберите хотя бы одну валюту")
    single = len(picked) == 1
    fig = go.Figure()
    for s in picked:
        d = df[df["currency"] == s["cur"]]
        if d.empty:
            continue
        if single:
            fig.add_scatter(x=d["date"], y=d["rate"], name=s["cur"], mode="lines",
                            line=dict(color=COLORS.get(s["cur"], GREEN), width=2.2),
                            hovertemplate="%{y:.4f} ₽<extra>" + s["cur"] + "</extra>")
        else:
            base = float(d.iloc[0]["rate"]) or 1.0
            fig.add_scatter(x=d["date"], y=d["rate"] / base * 100, name=s["cur"], mode="lines",
                            line=dict(color=COLORS.get(s["cur"], GREEN), width=2),
                            customdata=d["rate"],
                            hovertemplate="%{customdata:.4f} ₽ (%{y:.1f})<extra>"
                                          + s["cur"] + "</extra>")
    fig.update_xaxes(tickformat="%d.%m.%y", hoverformat="%d.%m.%Y")
    cap = (f"{picked[0]['cur']}: курс в рублях" if single
           else "индекс: начало периода = 100 · при наведении — курс в рублях")
    return [html.Div(cap, className="mp-foot top"), figure(fig, 360)]


def build(me: date):
    st, df = stats(me)
    if not st:
        return [empty("В справочнике «Макро» нет курсов USD, EUR, CNY, AMD за этот период")]
    cards = []
    for s in st:
        ch = s["m_ch"]
        tone = "warn" if ch is not None and abs(ch) >= FX_ALERT_PCT else None
        arrow = "" if ch is None else ("▲ " if ch > 0 else "▼ ")
        cards.append(kpi(
            f"{s['cur']} · {NAMES.get(s['cur'], '')}", num(s["rate"], 4) + " ₽",
            sub=f"на {fmt_date(s['date'])} · за месяц {arrow}{pct(ch, 1, sign=True)} · "
                f"с начала года {pct(s['y_ch'], 1, sign=True)}", tone=tone))

    kr, kr_date = data.key_rate(min(me, date.today()))
    big = [s for s in st if s["m_ch"] is not None and abs(s["m_ch"]) >= FX_ALERT_PCT]
    last = max(s["date"] for s in st)
    return [
        html.Div(className="mp-kpis", children=[
            *cards,
            kpi("Ключевая ставка ЦБ", pct(kr, 2) if kr is not None else "—",
                sub=f"действует с {fmt_date(kr_date)}" if kr_date else ""),
        ]),
        note(f"Курсы из справочника «Макро» на {fmt_date(last)} (последняя загруженная дата "
             f"не позже {fmt_date(min(me, date.today()))}). «За месяц» — к курсу на "
             f"{fmt_date(data.month_start(me) - timedelta(days=1))}, «с начала года» — к курсу на "
             f"{fmt_date(date(me.year, 1, 1) - timedelta(days=1))}."),
        note("Резкое изменение за месяц: " + "; ".join(
            f"{s['cur']} {'вырос' if s['m_ch'] > 0 else 'упал'} на {pct(abs(s['m_ch']))}"
            for s in big) + ".", "warn") if big else
        note(f"За {month_title(me).lower()} резких изменений курсов (больше "
             f"{FX_ALERT_PCT:.0f}%) нет."),
        card("Динамика курсов", [
            dmc.ChipGroup(id=FX_CUR_ID, multiple=True, value=[s["cur"] for s in st],
                          children=dmc.Group(gap=8, children=[
                              dmc.Chip(s["cur"], value=s["cur"], radius=0, size="sm",
                                       color="#2F6656", variant="outline") for s in st])),
            html.Div(id=FX_RESULT_ID, className="mp-result", children=chart(me)),
        ], subtitle="13 месяцев · выберите валюты",
            actions=export_button(x_btn("fx"), "Курсы, Excel")),
    ]
