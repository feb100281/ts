# gear/app/daily_sales/assistant/interest.py
"""Начисленные проценты по кредитам и займам (данные P&L мэн пака: pl_for_csv).

К уплате — наш расход (мы заёмщик): счёт 630000, раздел 8 P&L.
К получению — наш доход (мы займодавец): статьи с «процент» в прочих доходах.
Знак как в P&L: расход < 0, доход > 0. Имена ИП и физлиц маскируются.
"""
from __future__ import annotations

from datetime import date

from django.db import connection

SQL = """
    SELECT
        COALESCE(NULLIF(TRIM(p.cp_name), ''), 'Без контрагента') AS cp_name,
        cp.tax_id,
        COALESCE(NULLIF(TRIM(p.contract_name), ''), 'Без договора') AS contract_name,
        COALESCE(ct.title, '') AS contract_type,
        COALESCE(NULLIF(TRIM(p.cost_item), ''), '') AS cost_item,
        SUM(p.amount)::float AS amount,
        COUNT(*) AS n,
        BOOL_OR(o.id IS NOT NULL) AS is_group
    FROM public.pl_for_csv p
    LEFT JOIN public.contracts_contracts c ON c.id = p.contract_id
    LEFT JOIN public.contracts_contracts pc ON pc.id = c.pid_id
    LEFT JOIN public.contracts_contractstitle ct ON ct.id = COALESCE(pc.title_id, c.title_id)
    LEFT JOIN public.counterparties_counterparty cp ON cp.id = c.cp_id
    LEFT JOIN public.corporate_owners o ON o.inn = cp.tax_id
    WHERE p.date_from::date BETWEEN %s AND %s
      AND (
            p.account_name LIKE '630000%%'
         OR p.cost_item ILIKE '%%процент%%'
         OR p.cost_item_group ILIKE '%%процент%%'
      )
    GROUP BY 1, 2, 3, 4, 5
    HAVING ABS(SUM(p.amount)) > 0.005
    ORDER BY ABS(SUM(p.amount)) DESC
"""


def _name(cp, inn):
    inn = (inn or "").strip()
    if len(inn) == 12 and inn.isdigit():
        return f"ИП/физлицо (ИНН …{inn[-4:]})"
    return cp


def _fmt(v):
    return f"{v:,.0f}".replace(",", " ")


def interest_report(date_from=None, date_to=None, direction="all") -> str:
    end = date.fromisoformat(str(date_to)[:10]) if date_to else date.today()
    start = date.fromisoformat(str(date_from)[:10]) if date_from else end.replace(day=1)
    with connection.cursor() as cur:
        cur.execute(SQL, [start, end])
        rows = cur.fetchall()
    if not rows:
        return f"Начислений процентов за {start:%d.%m.%Y}–{end:%d.%m.%Y} нет."

    pay = [r for r in rows if r[5] < 0]
    rec = [r for r in rows if r[5] > 0]
    out = [f"Начисленные проценты {start:%d.%m.%Y}–{end:%d.%m.%Y} (по данным P&L, метод начисления)."]

    def block(title, data):
        if not data:
            out.append(f"\n{title}: нет.")
            return
        out.append(f"\n{title}: итого {_fmt(sum(r[5] for r in data))} ₽")
        grp = sum(r[5] for r in data if r[7])
        if grp:
            out.append(f"в т.ч. внутри группы (между нашими компаниями): {_fmt(grp)} ₽")
        out.append("Контрагент\tДоговор\tТип договора\tСтатья\tСумма, ₽\tВнутригрупповой")
        for cp, inn, contract, ctype, item, amt, n, is_group in data[:60]:
            out.append(f"{_name(cp, inn)}\t{contract}\t{ctype}\t{item}\t{_fmt(amt)}\t"
                       f"{'да' if is_group else ''}")
        if len(data) > 60:
            out.append(f"…ещё {len(data) - 60} строк")

    if direction in ("all", "pay"):
        block("К УПЛАТЕ (наш расход, мы заёмщик)", pay)
    if direction in ("all", "receive"):
        block("К ПОЛУЧЕНИЮ (наш доход, мы займодавец)", rec)
    out.append("\nЭто начисления, а не оплата. Для фактически уплаченных/полученных "
               "процентов — ДДС (cf_report, search «процент»).")
    return "\n".join(out)
