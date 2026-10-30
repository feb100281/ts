# gear/app/daily_sales/assistant/treasury.py
"""Остатки денежных средств — как листы «Остатки ДС» и Cash Flow мэн пака.

Банковские счета, баланс WB и депозиты — запросы treasury.txt / deposits.txt
мэн пака. Остатки на начало и конец месяца — из ДДС (cf_to_csv): остаток на
начало = сумма всех движений до месяца, на конец = начало + сальдо месяца.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date

from django.db import connection

from conns import get_duckdb_conn_with_opt


def _fmt(v):
    return "—" if v is None else f"{float(v):,.0f}".replace(",", " ")


def _treasury(as_of: date):
    from gear.management.commands import mp
    with get_duckdb_conn_with_opt(ro=True) as con:
        p = {"date_from": as_of}
        con.execute(mp.read_sql("treasury.txt"), parameters=p)
        rows = con.execute("SELECT * FROM treasury").fetchall()
        con.execute(mp.read_sql("deposits.txt"), parameters=p)
        dep = con.execute("SELECT balance FROM deposits").fetchone()
        last_bank = con.execute(
            "SELECT MAX(date_from)::DATE FROM pg.ba_balance_csv WHERE date_from <= ?",
            [as_of]).fetchone()[0]
    return rows, float(dep[0] or 0) if dep else 0.0, last_bank


def _cf_months(as_of: date, months: int):
    with connection.cursor() as cur:
        cur.execute("""
            SELECT date_trunc('month', date_from::date)::date AS m, SUM(amount)::float, MAX(date_from::date)
            FROM public.cf_to_csv WHERE date_from::date <= %s
            GROUP BY 1 ORDER BY 1
        """, [as_of])
        rows = cur.fetchall()
    out, run = [], 0.0
    for m, net, last in rows:
        opening = run
        run += float(net or 0)
        out.append((m, opening, float(net or 0), run, last))
    return out[-months:], (rows[-1][2] if rows else None)


def cash_report(as_of=None, months=6) -> str:
    as_of = date.fromisoformat(str(as_of)[:10]) if as_of else date.today()
    rows, deposits, last_bank = _treasury(as_of)
    lines = [f"ОСТАТКИ ДЕНЕЖНЫХ СРЕДСТВ на {as_of:%d.%m.%Y} "
             f"(движения по банку загружены по {last_bank:%d.%m.%Y})" if last_bank else
             f"ОСТАТКИ ДЕНЕЖНЫХ СРЕДСТВ на {as_of:%d.%m.%Y}"]

    banks = [r for r in rows if r[0] == "BANK"]
    wb = next((r for r in rows if r[0] == "WB"), None)
    by_cur = defaultdict(float)
    lines.append("\nБанковские счета (Счёт\tВалюта\tСтатус\tОстаток):")
    for _, name, cur, status, inflow, outflow, bal, *_ in banks:
        if status != "Действующий" and abs(bal or 0) < 0.5:
            continue
        lines.append(f"{name}\t{cur}\t{status}\t{_fmt(bal)}")
        by_cur[cur] += float(bal or 0)
    lines.append("Итого на счетах: " + "; ".join(f"{_fmt(v)} {c}" for c, v in by_cur.items()))
    lines.append(f"Бессрочные депозиты: {_fmt(deposits)} RUB")
    if wb:
        _, _, _, _, payable, withdrawn, bal, transit, no_transit, wb_date = wb
        lines.append(f"Баланс WB на {wb_date:%d.%m.%Y}: {_fmt(bal)} RUB "
                     f"(без денег в пути {_fmt(no_transit)}, в пути {_fmt(transit)})")
    rub_total = by_cur.get("RUB", 0) + deposits + (float(wb[6] or 0) if wb else 0)
    lines.append(f"ВСЕГО в рублях (счета RUB + депозиты + баланс WB): {_fmt(rub_total)} RUB")

    cf, cf_last = _cf_months(as_of, int(months or 6))
    if cf:
        lines.append(f"\nCASH FLOW по месяцам (ДДС загружен по {cf_last:%d.%m.%Y}):")
        lines.append("Месяц\tОстаток на начало\tСальдо месяца\tОстаток на конец")
        for m, op, net, cl, _ in cf:
            lines.append(f"{m:%m.%Y}\t{_fmt(op)}\t{_fmt(net)}\t{_fmt(cl)}")
    lines.append("\nИсточник — листы «Остатки ДС» и Cash Flow мэн пака. Остаток Cash Flow "
                 "считается по движениям ДДС и может отличаться от суммы по счетам, "
                 "если не все счета/валюты разнесены в ДДС.")
    return "\n".join(lines)
