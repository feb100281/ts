# gear/app/manpack/tabs/forecast.py
"""Прогноз и точка безубыточности: сценарий «что будет, если»."""
from __future__ import annotations

from datetime import date

import dash_mantine_components as dmc
import plotly.graph_objects as go
from dash import html

from .. import data
from ..config import FC_BASE_ID, FC_CONV_ID, FC_FIX_ID, FC_KMD_ID, FC_RESULT_ID, FC_REV_ID
from ..theme import (EXPENSE, GREEN, NEG, POS, SLATE, card, col, empty, figure, grid, kpi,
                     money, month_title, note, pct)

POP = {"zIndex": 10020}
BASES = [("me", "Выбранный месяц"), ("3", "Среднее за 3 полных месяца"),
         ("6", "Среднее за 6 полных месяцев"), ("1", "Последний полный месяц")]


def base(me: date, mode: str):
    """→ (показатели среднего месяца базы, подпись периода)."""
    from gear.management.commands import mp
    b = data.pl_bundle()
    rd = b["report_date"]
    full = [m for m in b["months"] if m <= me and m <= rd]      # завершённые месяцы
    if mode == "me":
        ms = [m for m in b["months"] if m == me]
    else:
        ms = full[-int(mode):]
    if not ms:
        return None, ""
    agg = {}
    for m in ms:
        for k, v in b["base"].get(m, {}).items():
            agg[k] = agg.get(k, 0.0) + (v or 0.0)
    d = mp._derive(agg, len(ms))
    label = (month_title(ms[0]) if len(ms) == 1
             else f"{month_title(ms[0]).lower()} – {month_title(ms[-1]).lower()}")
    return d, label


def scenario(d: dict, rev_pct=0.0, kmd_pp=0.0, fix_add=0.0, ex_conv=False) -> dict:
    """Пересчёт месяца: выручка ±%, КМД ±п.п., постоянные затраты +₽ в месяц."""
    rev = d["rev"] * (1 + (rev_pct or 0) / 100)
    kmd = (d["kmd"] or 0) + (kmd_pp or 0)
    fc = d["fc"] - (fix_add or 0)                 # постоянные затраты со знаком минус
    if ex_conv:
        fc -= d.get("conv") or 0.0
    md = rev * kmd / 100
    ebt = md + fc + d.get("other", 0.0)
    tbu = max(0.0, -fc) / kmd * 100 if kmd > 0 else None
    return {"rev": rev, "kmd": kmd, "fc": fc, "md": md, "ebt": ebt, "tbu": tbu,
            "zfp_pct": (rev - tbu) / rev * 100 if tbu is not None and rev else None,
            "other": d.get("other", 0.0)}


def build(me: date):
    num_input = dict(radius=0, size="sm", className="mp-f", step=1, hideControls=False)
    return [
        card("Сценарий", [
            html.Div(className="mp-filters", children=[
                dmc.Select(id=FC_BASE_ID, label="База расчёта", value="me", allowDeselect=False,
                           data=[{"value": k, "label": v} for k, v in BASES],
                           radius=0, size="sm", comboboxProps=POP, className="mp-f grow"),
                dmc.NumberInput(id=FC_REV_ID, label="Выручка, изменение %", value=0,
                                min=-90, max=500, suffix=" %", **num_input),
                dmc.NumberInput(id=FC_KMD_ID, label="КМД, изменение п.п.", value=0,
                                min=-50, max=50, decimalScale=1, suffix=" п.п.", **num_input),
                dmc.NumberInput(id=FC_FIX_ID, label="Постоянные затраты, + ₽ в месяц", value=0,
                                thousandSeparator=" ", **{**num_input, "step": 100000}),
                dmc.Switch(id=FC_CONV_ID, label="Без процентов по конвертируемым займам",
                           checked=False, radius=0, color="#2F6656", size="sm",
                           className="mp-f switch"),
            ]),
            html.Div(id=FC_RESULT_ID, className="mp-result"),
        ], subtitle="что будет с прибылью и точкой безубыточности, если изменятся выручка, "
                    "маржа или затраты"),
    ]


def _delta(new, old, good_up=True):
    if new is None or old is None:
        return ""
    ch = new - old
    if abs(ch) < 0.5:
        return "как в базе"
    sign = "+" if ch > 0 else "−"
    return f"{sign}{money(abs(ch))} к базе"


def result(me: date, mode, rev_pct, kmd_pp, fix_add, ex_conv):
    d, label = base(me, mode or "me")
    if not d or not d.get("rev"):
        return empty("Нет данных P&L для расчёта")
    b0 = scenario(d, ex_conv=ex_conv)
    s = scenario(d, rev_pct, kmd_pp, fix_add, ex_conv)

    # график безубыточности: выручка против полных затрат
    top = max(s["rev"], b0["rev"], s["tbu"] or 0, b0["tbu"] or 0) * 1.25 or 1
    xs = [0, top]
    var_share = 1 - s["kmd"] / 100
    fig = go.Figure()
    fig.add_scatter(x=xs, y=xs, name="Выручка", mode="lines", line=dict(color=GREEN, width=2.2),
                    hovertemplate="%{y:,.0f} ₽<extra>Выручка</extra>")
    fig.add_scatter(x=xs, y=[-s["fc"] + x * var_share for x in xs], name="Затраты всего",
                    mode="lines", line=dict(color=EXPENSE, width=2.2),
                    hovertemplate="%{y:,.0f} ₽<extra>Затраты</extra>")
    fig.add_scatter(x=xs, y=[-s["fc"]] * 2, name="Постоянные затраты", mode="lines",
                    line=dict(color=SLATE, width=1.3, dash="dot"),
                    hovertemplate="%{y:,.0f} ₽<extra>Постоянные</extra>")
    if s["tbu"] is not None and s["tbu"] <= top:
        fig.add_scatter(x=[s["tbu"]], y=[s["tbu"]], name="Точка безубыточности",
                        mode="markers", marker=dict(size=11, color=EXPENSE, symbol="diamond"),
                        hovertemplate="%{x:,.0f} ₽<extra>ТБУ</extra>")
    fig.add_scatter(x=[s["rev"]], y=[s["rev"]], name="Выручка по сценарию", mode="markers",
                    marker=dict(size=11, color=POS if s["ebt"] >= 0 else NEG),
                    hovertemplate="%{x:,.0f} ₽<extra>Сценарий</extra>")
    fig.update_layout(hovermode="closest")
    fig.update_xaxes(title_text="Выручка без НДС в месяц, ₽", title_font=dict(size=11))

    # чувствительность к выручке
    sens = []
    for p in (-30, -20, -10, 0, 10, 20, 30, 50):
        x = scenario(d, (rev_pct or 0) + p, kmd_pp, fix_add, ex_conv)
        sens.append({"p": f"{p:+d} %".replace("+0", "0"), "rev": x["rev"], "md": x["md"],
                     "ebt": x["ebt"], "year": x["ebt"] * 12})

    gap = (s["tbu"] - s["rev"]) if s["tbu"] is not None else None
    if s["tbu"] is None:
        verdict = note("При таком КМД маржинальный доход не покрывает даже переменные затраты — "
                       "точки безубыточности нет: рост выручки убыток не закроет.", "bad")
    elif gap > 0:
        verdict = note(f"До безубыточности не хватает {money(gap)} выручки в месяц "
                       f"(+{pct(gap / s['rev'] * 100)} к сценарию). Убыток до налога — "
                       f"{money(s['ebt'])} в месяц, {money(s['ebt'] * 12)} в год.", "warn")
    else:
        verdict = note(f"Выручка выше точки безубыточности на {money(-gap)} "
                       f"(запас прочности {pct(s['zfp_pct'])}). Результат до налога — "
                       f"{money(s['ebt'])} в месяц, {money(s['ebt'] * 12)} в год.", "good")
    return [
        html.Div(className="mp-kpis", children=[
            kpi("Выручка в месяц", money(s["rev"]), sub=_delta(s["rev"], b0["rev"])),
            kpi("Маржинальный доход", money(s["md"]),
                sub=f"КМД {pct(s['kmd'])} · {_delta(s['md'], b0['md'])}"),
            kpi("Постоянные затраты", money(s["fc"]), sub=_delta(s["fc"], b0["fc"]),
                tone="expense"),
            kpi("Результат до налога", money(s["ebt"]), sub=_delta(s["ebt"], b0["ebt"]),
                tone="neg" if s["ebt"] < 0 else "pos"),
            kpi("Точка безубыточности", money(s["tbu"]) if s["tbu"] is not None else "нет",
                sub=_delta(s["tbu"], b0["tbu"]) if s["tbu"] is not None else "КМД ≤ 0"),
            kpi("Запас прочности", pct(s["zfp_pct"]) if s["zfp_pct"] is not None else "—",
                tone="neg" if (s["zfp_pct"] or 0) < 0 else None),
        ]),
        verdict,
        html.Div(className="mp-grid-2 even stretch", children=[
            card("График безубыточности", figure(fig, 360),
                 subtitle="где линия выручки выше затрат — прибыль"),
            card("Если выручка изменится", grid("mp-fc-grid", sens, [
                col("p", "Выручка", width=110), col("rev", "Выручка, ₽", "num", width=150),
                col("md", "Маржинальный доход", "num", width=170),
                col("ebt", "Результат в месяц", "num", width=160),
                col("year", "За 12 месяцев", "num", width=160)], height=360),
                 subtitle="при тех же КМД и постоянных затратах"),
        ]),
        html.Div(f"База: {label}, в среднем за месяц. Прочие доходы и расходы (раздел 5) — "
                 f"как в базе: {money(s['other'])}. Расчёт линейный: КМД и постоянные затраты "
                 f"не зависят от объёма продаж.", className="mp-foot"),
    ]
