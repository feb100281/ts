# gear/app/daily_sales/assistant/wb_payouts.py
"""Поступления от WB — как лист «Поступления от WB» мэн пака.

Вывод средств с баланса WB (wb_balance_for_csv) сопоставляется с поступлением
на расчётный счёт (ДДС, статья «111000 Выручка от продажи товаров») функцией
mp.match_wb_payouts. Вывод без поступления — деньги в пути.
"""
from __future__ import annotations

from datetime import date

from conns import get_duckdb_conn_with_opt


def _fmt(v):
    return f"{float(v or 0):,.0f}".replace(",", " ")


def wb_payouts_report(date_from=None, date_to=None, details=True) -> str:
    from gear.management.commands import mp

    end = date.fromisoformat(str(date_to)[:10]) if date_to else date.today()
    start = date.fromisoformat(str(date_from)[:10]) if date_from else end.replace(day=1)
    with get_duckdb_conn_with_opt(ro=True) as con:
        con.execute(mp.read_sql("wb_payouts.txt"), parameters={"date_from": end})
        rows = con.execute("SELECT * FROM wb_payouts").fetchall()
    outs, ins = mp.split_payouts(rows)
    # как на листе мэн пака: сумма — из баланса WB (вывод средств),
    # дата — день поступления на расчётный счёт; вывод без поступления — в пути
    pairs = mp.match_wb_payouts(outs, ins)
    rec = [p for p in pairs if p["in_dt"] and start <= p["in_dt"] <= end]
    transit = [p for p in pairs if p["in_dt"] is None and p["out_dt"] <= end]
    days = [p["days"] for p in rec if p["days"] is not None]
    last_in = max((i["dt"] for i in ins), default=None)

    total = sum(p["out_amount"] for p in rec)
    lines = [
        f"ПОСТУПЛЕНИЯ ОТ WB НА РАСЧЁТНЫЙ СЧЁТ {start:%d.%m.%Y}–{end:%d.%m.%Y}"
        + (f" (банк загружен по {last_in:%d.%m.%Y})" if last_in else ""),
        f"Зачислено: {_fmt(total)} ₽, {len(rec)} поступлений",
    ]
    if transit:
        lines.append(f"Деньги в пути (выведены из кабинета WB, на счёт ещё не пришли): "
                     f"{_fmt(sum(p['out_amount'] for p in transit))} ₽, {len(transit)} шт.")
    else:
        lines.append("Денег в пути нет.")
    if days:
        lines.append(f"Срок зачисления после вывода из кабинета: в среднем "
                     f"{sum(days) / len(days):.1f} дн., максимум {max(days)} дн.")
    if details and rec:
        lines.append("\nДата зачисления\tСумма, ₽\tВывод из кабинета WB\tДней")
        for p in sorted(rec, key=lambda x: x["in_dt"])[-40:]:
            lines.append(f"{p['in_dt']:%d.%m.%Y}\t{_fmt(p['out_amount'])}\t"
                         f"{p['out_dt']:%d.%m.%Y}\t{p['days']}")
    if transit:
        lines.append("\nВ пути: " + "; ".join(
            f"вывод {p['out_dt']:%d.%m.%Y} — {_fmt(p['out_amount'])} ₽" for p in transit[-10:]))
    lines.append("\nИсточник — лист «Поступления от WB» мэн пака (кассовый метод). "
                 "Это деньги на счёт, а не продажи: выручка WB — wb_sales / pl_report.")
    return "\n".join(lines)
