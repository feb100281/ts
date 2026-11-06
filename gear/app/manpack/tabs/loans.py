# gear/app/manpack/tabs/loans.py
"""Займы и кредиты: кто кому должен, тело и проценты, ставки, сроки."""
from __future__ import annotations

from datetime import date

from dash import html

from .. import data
from ..config import LOANS_APP_URL, x_btn
from ..theme import card, col, empty, export_button, fmt_date, grid, kpi, money, note


def rows(me: date):
    df = data.loans(min(me, date.today()))
    if df.empty:
        return []
    out = []
    for r in df.sort_values("total_debt", ascending=False).itertuples():
        if abs(r.total_debt or 0) < 1:      # погашенные договоры не показываем
            continue
        rep = getattr(r, "repayment_date", None)
        cd = getattr(r, "contract_date", None)
        out.append({
            "side": r.loan_direction_label, "cp": r.counterparty_name or "—",
            "contract": f"{r.contract_type or 'Договор'} № {r.contract_number or 'б/н'}"
                        + (f" от {cd:%d.%m.%Y}" if cd is not None and cd == cd else ""),
            "cur": r.currency or "RUB", "rate": float(r.rate or 0),
            "drawdown": float(r.total_drawdown or 0), "repaid": float(r.total_repaid or 0),
            "principal": float(r.ending_balance or 0), "interest": float(r.interest_balance or 0),
            "debt": float(r.total_debt or 0),
            "due": rep.strftime("%d.%m.%Y") if rep is not None and rep == rep else "",
            "docs": int(r.documents_count or 0),
            "direction": r.loan_direction,
        })
    return out


def build(me: date):
    data_rows = rows(me)
    if not data_rows:
        return [empty("На эту дату займов и кредитов нет")]
    we = [r for r in data_rows if r["direction"] == "borrowed"]
    they = [r for r in data_rows if r["direction"] == "issued"]
    s = lambda rs, k: sum(r[k] for r in rs)
    cols = [col("cp", "Контрагент", width=280), col("side", "Сторона", width=130),
            col("contract", "Договор", minWidth=260), col("cur", "Валюта", width=90),
            col("rate", "Ставка, %", "pct", width=110),
            col("principal", "Основной долг", "num", width=150),
            col("interest", "Проценты к уплате", "num", width=160),
            col("debt", "Всего долг", "num", width=150),
            col("due", "Срок погашения", width=140), col("docs", "Файлов", "num", width=90)]
    return [
        html.Div(className="mp-kpis", children=[
            kpi("Мы должны", money(s(we, "debt")),
                sub=f"тело {money(s(we, 'principal'))} · проценты {money(s(we, 'interest'))}",
                tone="expense"),
            kpi("Нам должны", money(s(they, "debt")),
                sub=f"тело {money(s(they, 'principal'))} · проценты {money(s(they, 'interest'))}",
                tone="pos"),
            kpi("Чистая позиция", money(s(they, "debt") - s(we, "debt")),
                sub="нам должны − мы должны",
                tone="neg" if s(they, "debt") - s(we, "debt") < 0 else None),
            kpi("Договоров с остатком", str(len(data_rows))),
        ]),
        note(f"Задолженность на {fmt_date(min(me, date.today()))}: основной долг и начисленные, "
             "но не уплаченные проценты. Суммы в валюте договора."),
        card("Займы и кредиты", grid("mp-loans-grid", data_rows, cols, height=480),
             subtitle="только договоры с остатком долга",
             actions=[html.A("Подробный дашборд займов →", href=LOANS_APP_URL, target="_blank",
                             className="mp-link"),
                      export_button(x_btn("loans"), "Займы, Excel")]),
    ]
