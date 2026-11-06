# gear/app/manpack/off_pl.py
"""Справочно к P&L: что прошло через деньги, но не попало в P&L.

О.1 Поступления по доходным статьям CF (11…) без проводки в P&L. Операция банка (gl.fact, счета денег)
    считается отражённой в P&L, если от неё по цепочке pid есть проводка на счёт
    P&L (родитель 25/26/27). Не показываются по природе: выплаты и зачёты WB
    (111…, 122…), финансирование (3…), переводы и валютные операции (41…), налоги
    (125…: налог на прибыль — строкой P&L, НДС — в справочном блоке НДС).
О.2 Оплаты товаров на баланс (договоры со счётом 130…) без УПД: по договору
    нарастающим итогом max(оплаты − УПД, 0); в месяц — прирост, итог — остаток.
"""
from __future__ import annotations

from datetime import date

import pandas as pd

SKIP_PREFIX = (("111", "выплаты WB"), ("122", "зачёты WB"), ("3", "финансирование"),
               ("41", "переводы и валютные операции"),
               ("125", "налоги: в P&L строкой налога на прибыль и в блоке НДС"))
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
    """Причина не показывать; None — показать. В О.1 только доходные статьи 11…:
    поступления по статьям расходов (12…) — это возвраты оплат, а не доход."""
    code = str(code or "").strip()
    for pfx, name in SKIP_PREFIX:
        if code.startswith(pfx):
            return name
    if not code.startswith("11"):
        return "не доходная статья (возврат оплаты)"
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


def _d(v) -> date:
    return pd.Timestamp(v).date()


def pl_items(data: dict, sec: str, it_in: str, it_paid: str, it_upd: str,
             it_unc: str) -> dict:
    """{(me, sec, item): value} для листов P&L."""
    out = {}
    inflow = data["inflow"]
    if not inflow.empty:
        for me, v in inflow.groupby("me")["amount"].sum().items():
            out[(_d(me), sec, it_in)] = round(float(v), 2)
    g = goods_by_month(data["goods_m"])
    if not g.empty:
        m = g.groupby("me").agg(paid=("paid", "sum"), upd=("upd", "sum"),
                                delta=("delta", "sum")).sort_index()
        m["bal"] = m["delta"].cumsum()
        for me, r in m.iterrows():
            me = _d(me)
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
    c0 = mp.COL_CODE
    widths = [12, 32, 34, 52, 17, 17, 17, 70]
    ncols = c0 + len(widths) - 1
    mp.title_band(ws, "Вне P&L: расшифровка",
                  f"Данные на {as_of:%d.%m.%Y} · справочно, P&L не меняет", ncols,
                  extra="О.1 — доходы, поступившие деньгами без проводки в P&L; О.2 — оплаты "
                        "товаров на баланс (130…), по которым нет УПД")
    ws.column_dimensions["A"].width = 2
    for i, w in enumerate(widths):
        ws.column_dimensions[get_column_letter(c0 + i)].width = w
    f_h = Font(name=mp.FONT, size=9, bold=True, color="FFFFFF")
    f_c = Font(name=mp.FONT, size=9, color=mp.TEXT)
    f_b = Font(name=mp.FONT, size=9, bold=True, color=mp.TEXT)
    f_s = Font(name=mp.FONT, size=11, bold=True, color=mp.NAVY_3)
    f_n = Font(name=mp.FONT, size=9, color=mp.TEXT_2)

    def table(r, title, note, cols, rows, money, empty):
        """cols: [(название, формат)]; rows: списки значений; money — индексы с итогом."""
        mp.write(ws, r, c0, title, font=f_s)
        mp.write(ws, r + 1, c0, note, font=f_n)
        r += 2
        for i, (name, _) in enumerate(cols):
            mp.write(ws, r, c0 + i, name, font=f_h, fillc=mp.NAVY, align="center", wrap=True)
        ws.row_dimensions[r].height = 28
        first = r + 1
        if not rows:
            r += 1
            mp.write(ws, r, c0, empty, font=f_n)
        for row in rows:
            r += 1
            for i, v in enumerate(row):
                fmt = cols[i][1]
                mp.write(ws, r, c0 + i, v, font=f_c, fmt=fmt, border=mp.B_BOTTOM,
                         align="right" if fmt in (mp.FMT_MONEY,) else
                         "center" if fmt else "left")
        r += 1
        for i in range(len(cols)):
            v = None
            if i == 0:
                v = "Итого"
            elif i in money and rows:
                L = get_column_letter(c0 + i)
                v = f"=SUM({L}{first}:{L}{r - 1})"
            mp.write(ws, r, c0 + i, v, font=f_b, fmt=mp.FMT_MONEY if i in money else None,
                     border=mp.B_TOTAL, align="right" if i in money else "left")
        return r

    inflow = data["inflow"]
    rows1 = [[_d(x.d), x.subitem or x.item or "без статьи", x.cp,
              x.contract or "без договора", float(x.amount), str(x.description)[:250]]
             for x in inflow.itertuples()]
    r = table(7, "О.1 Доходы, поступившие деньгами, без проводки в P&L",
              "Поступления по доходным статьям Cash Flow (11…), от которых нет проводки в P&L. "
              "Не показываются: выплаты WB (выручка — через продажи), возвраты оплат по статьям "
              "расходов, финансирование, переводы, валютные операции и налоги.",
              [("Дата", mp.FMT_DATE), ("Статья CF", None), ("Контрагент", None),
               ("Договор", None), ("Сумма, ₽", mp.FMT_MONEY), ("Назначение", None)],
              rows1, {4}, "Нет таких поступлений — все доходы отражены в P&L.")

    g = goods_by_month(data["goods_m"])
    rows2 = []
    if not g.empty:
        tot = g.groupby("cid").agg(paid=("paid", "sum"), upd=("upd", "sum"),
                                   unc=("unc", "last"))
        last_pay = g[g["paid"] != 0].groupby("cid")["me"].max()
        tot = tot[tot["unc"] > 0.5].sort_values("unc", ascending=False)
        names = data["contracts"].set_index("cid")
        for cid, x in tot.iterrows():
            lp = last_pay.get(cid)
            rows2.append([_d(lp) if lp is not None else None,
                          names["cp"].get(cid, "") if cid in names.index else "",
                          names["contract"].get(cid, f"id {cid}") if cid in names.index
                          else f"id {cid}",
                          float(x.paid), float(x.upd), float(x.unc)])
    r = table(r + 3, f"О.2 Оплаты товаров на баланс без УПД — по договорам на {as_of:%d.%m.%Y}",
              "Договоры со счётом 130… Оплачено — платежи поставщику минус возвраты (выписки и "
              "сплиты); по УПД — сумма УПД с НДС, только в рублях. Без УПД = оплачено − по УПД, "
              "если больше нуля. Последняя оплата — месяц.",
              [("Последняя оплата", "MM.YYYY"), ("Контрагент", None), ("Договор", None),
               ("Оплачено, ₽", mp.FMT_MONEY), ("По УПД, ₽", mp.FMT_MONEY),
               ("Без УПД, ₽", mp.FMT_MONEY)],
              rows2, {3, 4, 5}, "Нет оплат без УПД.")
    ws.freeze_panes = ws.cell(row=6, column=c0 + 1)
