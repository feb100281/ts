# gear/app/manpack/off_pl.py
"""Справочно к P&L: что прошло через деньги, но не попало в P&L.

О.1 Поступления в Cash Flow без проводки в P&L. Операция банка (gl.fact, счета денег)
    считается отражённой в P&L, если от неё по цепочке pid есть проводка на счёт
    P&L (родитель 25/26/27). Не показываются по природе: выплаты и зачёты WB
    (111…, 122…), финансирование (3…), переводы и валютные операции (41…).
О.2 Оплаты товаров на баланс (договоры со счётом 130…) без УПД: по договору
    нарастающим итогом max(оплаты − УПД, 0); в месяц — прирост, итог — остаток.
"""
from __future__ import annotations

from datetime import date

import pandas as pd

SKIP_PREFIX = (("111", "выплаты WB"), ("122", "зачёты WB"), ("3", "финансирование"),
               ("41", "переводы и валютные операции"))
PL_PARENTS = (25, 26, 27)

IN_SQL = """
WITH cash_acc AS (SELECT DISTINCT acc_id FROM pg.cf_to_csv),
pl_acc AS (SELECT id FROM pg.public.corporate_coa WHERE parent_id IN (25, 26, 27)),
lvl1 AS (SELECT id, pid, acc_id FROM pg.gl.fact WHERE pid IS NOT NULL),
linked AS (
    SELECT DISTINCT CAST(a.pid AS VARCHAR) AS cf_id FROM lvl1 a
    WHERE a.acc_id IN (SELECT id FROM pl_acc)
    UNION
    SELECT DISTINCT CAST(a.pid AS VARCHAR) FROM lvl1 a JOIN lvl1 b ON b.pid = a.id
    WHERE b.acc_id IN (SELECT id FROM pl_acc)
)
SELECT f.date_from::DATE AS d, LAST_DAY(f.date_from)::DATE AS me,
       ROUND((COALESCE(f.dt, 0) - COALESCE(f.cr, 0)) / 100.0, 2) AS amount,
       COALESCE(CAST(i.code AS VARCHAR), '') AS code,
       COALESCE(CAST(p.code AS VARCHAR) || ' ' || p.name, '') AS item,
       COALESCE(CAST(i.code AS VARCHAR) || ' ' || i.name, '') AS subitem,
       COALESCE(NULLIF(TRIM(cp.name), ''), 'Без контрагента') AS cp,
       TRY_CAST(f.contract_id AS BIGINT) AS cid,
       COALESCE(f.description, '') AS description
FROM pg.gl.fact f
LEFT JOIN pg.public.corporate_cfitems i ON i.id = f.subconto_id
LEFT JOIN pg.public.corporate_cfitems p ON p.id = i.parent_id
LEFT JOIN pg.public.contracts_contracts k ON k.id = f.contract_id
LEFT JOIN pg.public.counterparties_counterparty cp ON cp.id = k.cp_id
WHERE f.chapter IN ('CF_BA', 'MANUAL_TRS')
  AND f.acc_id IN (SELECT acc_id FROM cash_acc)
  AND COALESCE(f.dt, 0) - COALESCE(f.cr, 0) > 0
  AND f.date_from::DATE <= $date_from
  AND CAST(f.id AS VARCHAR) NOT IN (SELECT cf_id FROM linked)
ORDER BY f.date_from
"""

UPD_TOTAL = ("l.upd_amount_vatless + COALESCE(l.upd_vat_amount, "
             "l.upd_amount_vatless * COALESCE(l.upd_vat_rate, 0) / 100)")


def _goods_sql() -> str:
    from gear.management.commands.sql.read_query import read_sql
    frag = read_sql("vat_bs130.txt")
    frag = frag[:frag.index("bs130_rows AS (")].rstrip().rstrip(",")
    return "WITH\n" + frag + f""",
    g AS (
        SELECT contract_id AS cid, LAST_DAY(d)::DATE AS me, out_amt AS paid, 0.0 AS upd
        FROM bs130_pay WHERE d <= $date_from AND contract_id IN (SELECT cid FROM bs130)
        UNION ALL
        SELECT d.contract_id, LAST_DAY(d.date)::DATE, 0.0, {UPD_TOTAL}
        FROM pg.public.upd_income_lines l
        JOIN pg.public.cards_upddocument d ON d.id = l.upd_document_id
        WHERE d.date <= $date_from AND COALESCE(l.currency_code, 'RUB') = 'RUB'
          AND d.contract_id IN (SELECT cid FROM bs130)
    )
    SELECT cid, me, SUM(paid) AS paid, SUM(upd) AS upd FROM g GROUP BY 1, 2 ORDER BY 1, 2"""


def _skip(code: str):
    code = str(code or "").strip()
    for pfx, name in SKIP_PREFIX:
        if code.startswith(pfx):
            return name
    return None


def fetch(con, date_from: date) -> dict:
    """{'inflow': DataFrame строк О.1, 'goods_m': по договору и месяцу, 'contracts': имена}."""
    from .vat_contracts import CONTRACT_SQL
    ctr = con.execute(CONTRACT_SQL).df()
    inflow = con.execute(IN_SQL, {"date_from": date_from}).df()
    if not inflow.empty:
        inflow = inflow[inflow["code"].map(_skip).isna()].reset_index(drop=True)
        names = ctr.set_index("cid")["contract"]
        inflow["contract"] = inflow["cid"].map(names).fillna("")
    goods = con.execute(_goods_sql(), {"date_from": date_from}).df()
    return {"inflow": inflow, "goods_m": goods, "contracts": ctr}


def goods_by_month(goods: pd.DataFrame) -> pd.DataFrame:
    """По договору: остаток без УПД на конец месяца и его прирост."""
    if goods.empty:
        return goods.assign(unc=[], delta=[])
    g = goods.sort_values(["cid", "me"]).copy()
    g["cum"] = (g.groupby("cid")["paid"].cumsum() - g.groupby("cid")["upd"].cumsum())
    g["unc"] = g["cum"].clip(lower=0)
    g["delta"] = g["unc"] - g.groupby("cid")["unc"].shift().fillna(0)
    return g


def pl_items(data: dict, sec: str, it_in: str, it_paid: str, it_upd: str,
             it_unc: str) -> dict:
    """{(me, sec, item): value} для листов P&L."""
    out = {}
    inflow = data["inflow"]
    if not inflow.empty:
        for me, v in inflow.groupby("me")["amount"].sum().items():
            me = me if isinstance(me, date) else pd.Timestamp(me).date()
            out[(me, sec, it_in)] = round(float(v), 2)
    g = goods_by_month(data["goods_m"])
    if not g.empty:
        m = g.groupby("me").agg(paid=("paid", "sum"), upd=("upd", "sum"),
                                delta=("delta", "sum")).sort_index()
        m["bal"] = m["delta"].cumsum()
        for me, r in m.iterrows():
            me = me if isinstance(me, date) else pd.Timestamp(me).date()
            out[(me, sec, it_paid)] = round(float(r.paid), 2)
            out[(me, sec, it_upd)] = round(float(r.upd), 2)
            out[(me, sec, it_unc)] = round(float(r.bal), 2)
    return out


def build_sheet(ws, data: dict, report_date: date, as_of: date | None = None):
    """Лист-расшифровка: О.1 по операциям, О.2 по договорам на дату."""
    from openpyxl.styles import Font
    from openpyxl.utils import get_column_letter
    from gear.management.commands import mp

    as_of = as_of or report_date
    mp.sheet_setup(ws)
    ncols = 9
    mp.title_band(ws, "Вне P&L: расшифровка",
                  f"Данные на {as_of:%d.%m.%Y} · справочно, P&L не меняет", ncols,
                  extra="О.1 — поступления без проводки в P&L; О.2 — оплаты товаров на "
                        "баланс (130…), по которым нет УПД")
    ws.column_dimensions["A"].width = 2
    widths = {2: 12, 3: 30, 4: 34, 5: 40, 6: 18, 7: 18, 8: 18, 9: 50}
    for c, w in widths.items():
        ws.column_dimensions[get_column_letter(c)].width = w
    f_h = Font(name=mp.FONT, size=9, bold=True, color="FFFFFF")
    f_c = Font(name=mp.FONT, size=9, color=mp.TEXT)
    f_b = Font(name=mp.FONT, size=9, bold=True, color=mp.TEXT)
    f_s = Font(name=mp.FONT, size=11, bold=True, color=mp.NAVY_3)
    f_n = Font(name=mp.FONT, size=9, color=mp.TEXT_2)

    def header(r, cols):
        for i, name in enumerate(cols):
            mp.write(ws, r, 2 + i, name, font=f_h, fillc=mp.NAVY, align="center", wrap=True)
        ws.row_dimensions[r].height = 28

    def cell(r, c, v, fmt=None, bold=False, align=None):
        return mp.write(ws, r, c, v, font=f_b if bold else f_c, fmt=fmt,
                        border=mp.B_BOTTOM, align=align or ("right" if fmt else "left"))

    # ---- О.1
    r = 7
    mp.write(ws, r, 2, "О.1 Поступления в Cash Flow, не отражённые в P&L", font=f_s)
    r += 1
    mp.write(ws, r, 2, "Не показываются: выплаты и зачёты WB (выручка — через продажи), "
                       "займы, кредиты, депозиты и проценты, переводы между своими счетами и "
                       "валютные операции.", font=f_n)
    r += 1
    header(r, ["Дата", "Статья CF", "Контрагент", "Договор", "Сумма, ₽", "", "", "Назначение"])
    inflow = data["inflow"]
    first = r + 1
    for x in inflow.itertuples():
        r += 1
        cell(r, 2, x.d if isinstance(x.d, date) else pd.Timestamp(x.d).date(),
             fmt=mp.FMT_DATE, align="center")
        cell(r, 3, x.subitem or x.item)
        cell(r, 4, x.cp)
        cell(r, 5, x.contract or "без договора")
        cell(r, 6, float(x.amount), fmt=mp.FMT_MONEY)
        cell(r, 9, str(x.description)[:200])
    r += 1
    mp.write(ws, r, 2, "Итого", font=f_b, border=mp.B_TOTAL)
    mp.write(ws, r, 6, f"=SUM(F{first}:F{r - 1})" if r - 1 >= first else 0,
             font=f_b, fmt=mp.FMT_MONEY, border=mp.B_TOTAL, align="right")

    # ---- О.2
    r += 3
    mp.write(ws, r, 2, f"О.2 Оплаты товаров на баланс без УПД — по договорам на {as_of:%d.%m.%Y}",
             font=f_s)
    r += 1
    mp.write(ws, r, 2, "Договоры со счётом 130… Оплачено — платежи поставщику минус возвраты "
                       "(выписки и сплиты); по УПД — сумма УПД с НДС, только рубли. Без УПД = "
                       "оплачено − по УПД, если больше нуля.", font=f_n)
    r += 1
    header(r, ["Последняя оплата", "Контрагент", "Договор", "", "Оплачено, ₽",
               "По УПД, ₽", "Без УПД, ₽", ""])
    g = goods_by_month(data["goods_m"])
    first = r + 1
    if not g.empty:
        tot = g.groupby("cid").agg(paid=("paid", "sum"), upd=("upd", "sum"),
                                   unc=("unc", "last"))
        last_pay = g[g["paid"] != 0].groupby("cid")["me"].max()
        tot = tot[tot["unc"] > 0.5].sort_values("unc", ascending=False)
        names = data["contracts"].set_index("cid")
        for cid, x in tot.iterrows():
            r += 1
            lp = last_pay.get(cid)
            cell(r, 2, pd.Timestamp(lp).strftime("%m.%Y") if lp is not None else "",
                 align="center")
            cell(r, 3, names["cp"].get(cid, "") if cid in names.index else "")
            cell(r, 4, names["contract"].get(cid, f"id {cid}") if cid in names.index
                 else f"id {cid}")
            cell(r, 6, float(x.paid), fmt=mp.FMT_MONEY)
            cell(r, 7, float(x.upd), fmt=mp.FMT_MONEY)
            cell(r, 8, float(x.unc), fmt=mp.FMT_MONEY, bold=True)
    r += 1
    mp.write(ws, r, 2, "Итого", font=f_b, border=mp.B_TOTAL)
    for c, L in ((6, "F"), (7, "G"), (8, "H")):
        mp.write(ws, r, c, f"=SUM({L}{first}:{L}{r - 1})" if r - 1 >= first else 0,
                 font=f_b, fmt=mp.FMT_MONEY, border=mp.B_TOTAL, align="right")
    ws.freeze_panes = "C6"
