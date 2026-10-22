# gear/app/manpack/tabs/banks.py
"""Счета и остатки: остатки на дату, депозиты, баланс WB, поступления от WB."""
from __future__ import annotations

from collections import defaultdict
from datetime import date

import dash_mantine_components as dmc
import plotly.graph_objects as go
from dash import dcc, html

from .. import data
from ..config import BK_DATE_ID, BK_RESULT_ID, x_btn
from ..theme import (GREEN, MONTHS_SHORT, NEG, POS, card, col, empty, export_button, figure,
                     fmt_date, grid, kpi, money, month_title, note, num)

POP = {"zIndex": 10020}


def as_date(value, me: date) -> date:
    try:
        d = date.fromisoformat(str(value)[:10])
    except Exception:
        d = me
    return min(d, date.today())


def snapshot(as_of: date):
    """→ dict: счета, итоги по валютам, депозиты, WB, дата банка, Cash Flow по месяцам."""
    rows, deposits, last_bank = data.treasury(as_of)
    banks = [r for r in rows if r[0] == "BANK"]
    wb = next((r for r in rows if r[0] == "WB"), None)
    by_cur = defaultdict(float)
    accounts = []
    for _, name, cur, status, _inflow, _outflow, bal, *_ in banks:
        if abs(bal or 0) < 0.5 and status != "Действующий":
            continue
        accounts.append({"name": name, "cur": cur, "status": status,
                         "balance": float(bal or 0)})
        by_cur[cur] += float(bal or 0)
    accounts.sort(key=lambda a: (a["cur"] != "RUB", -a["balance"]))
    cm, cf_last = data.cf_months(as_of, 13)
    return {"as_of": as_of, "accounts": accounts, "by_cur": dict(by_cur), "deposits": deposits,
            "wb": wb, "last_bank": last_bank, "cf": cm, "cf_last": cf_last}


def reference_rows(s) -> list[dict]:
    """Справочные строки, как на листе «Остатки ДС» мэн пака."""
    wb = s["wb"]
    out = [{"name": "Бессрочные депозиты (размещены, не возвращены)", "cur": "RUB",
            "status": "Справочно", "balance": float(s["deposits"] or 0)}]
    if wb:
        out.append({"name": f"Баланс кабинета WB на {fmt_date(wb[9])}", "cur": "RUB",
                    "status": "Справочно", "balance": float(wb[6] or 0)})
        out.append({"name": "   в т.ч. деньги в пути (выведены, на счёт ещё не пришли)",
                    "cur": "RUB", "status": "Справочно", "balance": float(wb[7] or 0)})
    return out


def payouts(as_of: date):
    """Поступления от WB за месяц даты as_of → (зачислено, в пути, средний срок)."""
    p = data.wb_payouts(as_of)
    start = data.month_start(as_of)
    rec = sorted((x for x in p["pairs"] if x["in_dt"] and start <= x["in_dt"] <= as_of),
                 key=lambda x: x["in_dt"], reverse=True)
    transit = [x for x in p["pairs"] if x["in_dt"] is None and x["out_dt"] <= as_of]
    days = [x["days"] for x in rec if x["days"] is not None]
    return rec, transit, (sum(days) / len(days) if days else None), p["last_in"]


def build(me: date):
    as_of = min(me, date.today())
    return [
        html.Div(className="mp-filters flat", children=[
            dmc.DatePickerInput(id=BK_DATE_ID, label="Остатки на дату", value=as_of.isoformat(),
                                valueFormat="DD.MM.YYYY", maxDate=date.today().isoformat(),
                                radius=0, size="sm", popoverProps=POP, className="mp-f",
                                clearable=False),
        ]),
        dcc.Loading(type="dot", color="#2F6656",
                    children=html.Div(id=BK_RESULT_ID, className="mp-result")),
    ]


def _wb_card(as_of: date):
    try:
        rec, transit, avg_days, last_in = payouts(as_of)
    except Exception as e:
        return card("Поступления от WB", note(f"Не удалось получить поступления: {e}", "warn"))
    total = sum(x["out_amount"] for x in rec)
    in_transit = sum(x["out_amount"] for x in transit)
    rows = [{"in_dt": fmt_date(x["in_dt"]), "amount": x["out_amount"]} for x in rec]
    body = [
        grid("mp-wb-grid", rows, [
            col("in_dt", "Зачислено на счёт", width=220),
            col("amount", "Сумма, ₽", "num2", width=220)], height=300, fit=False,
            pinned_bottom=[{"in_dt": f"Итого ({len(rec)})", "amount": total}])
        if rows else empty("За этот месяц поступлений от WB нет"),
        html.Div(f"Деньги в пути (выведены из кабинета, на счёт ещё не пришли): "
                 f"{money(in_transit)}" if transit else "Денег в пути нет.", className="mp-foot"),
    ]
    return card("Поступления от WB", body,
                subtitle=f"{month_title(as_of)} по {fmt_date(as_of)}",
                actions=export_button(x_btn("wb"), "Поступления WB, Excel"))


def result(as_of: date):
    s = snapshot(as_of)
    wb = s["wb"]
    wb_bal = float(wb[6] or 0) if wb else 0.0
    rub = s["by_cur"].get("RUB", 0.0)
    total = rub + s["deposits"] + wb_bal
    fx_cards = [kpi(f"Счета в {c}", num(v, 2) + f" {c}") for c, v in s["by_cur"].items()
                if c != "RUB" and abs(v) > 0.5]

    cm = s["cf"]
    x = [f"{MONTHS_SHORT[m.month - 1]} {str(m.year)[2:]}" for m, *_ in cm]
    fig = go.Figure()
    fig.add_bar(x=x, y=[net for _, _, net, _, _ in cm], name="Сальдо месяца", opacity=0.55,
                marker_color=[POS if net >= 0 else NEG for _, _, net, _, _ in cm],
                hovertemplate="%{y:,.0f} ₽<extra>Сальдо</extra>")
    fig.add_scatter(x=x, y=[cl for *_, cl, _ in cm], name="Остаток на конец месяца",
                    mode="lines+markers", line=dict(color=GREEN, width=2.5),
                    hovertemplate="%{y:,.0f} ₽<extra>Остаток</extra>")

    acc_cols = [col("name", "Счёт", minWidth=420), col("cur", "Валюта", width=110),
                col("status", "Статус", width=150), col("balance", "Остаток", "num2", width=200)]
    acc_rows = s["accounts"] + reference_rows(s)
    cf_rows = [{"m": f"{m:%m.%Y}", "op": op, "net": net, "cl": cl} for m, op, net, cl, _ in cm]
    return [
        html.Div(className="mp-kpis", children=[
            kpi("Всего в рублях", money(total), sub="счета RUB + депозиты + баланс WB", tone="pos"),
            kpi("Счета в рублях", money(rub)),
            kpi("Бессрочные депозиты", money(s["deposits"]), sub="размещены, не возвращены"),
            kpi("Баланс кабинета WB", money(wb_bal),
                sub=(f"в пути {money(wb[7])} · на {fmt_date(wb[9])}" if wb else "нет данных"),
                hint="Деньги в личном кабинете WB — ещё не на расчётном счёте"),
            *fx_cards,
        ]),
        note(f"Остатки на {fmt_date(s['as_of'])}. Движения по банку загружены по "
             f"{fmt_date(s['last_bank'])}, ДДС — по {fmt_date(s['cf_last'])}."),
        card("Банковские счета, депозиты и баланс WB", grid("mp-acc-grid", acc_rows, acc_cols),
             subtitle=f"на {fmt_date(s['as_of'])} · закрытые счета с нулевым остатком скрыты",
             actions=export_button(x_btn("banks"), "Остатки, Excel")),
        _wb_card(as_of),
        html.Div(className="mp-grid-2 even stretch", children=[
            card("Остаток денег по месяцам", figure(fig, 320), subtitle="по Cash Flow, ₽"),
            card("Остаток на начало и конец месяца", grid("mp-cfm-grid", cf_rows, [
                col("m", "Месяц", width=110), col("op", "На начало", "num", width=150),
                col("net", "Сальдо", "num", width=150),
                col("cl", "На конец", "num", width=150)], height=320)),
        ]) if cm else empty("Нет данных Cash Flow"),
    ]
