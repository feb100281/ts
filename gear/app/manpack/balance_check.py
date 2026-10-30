# gear/app/manpack/balance_check.py
"""Баланс (проверка): активы и пассивы по остаткам счетов gl.fact на дату.

Счета по первой цифре кода:
  1 — активы; 2 — обязательства; 3 — капитал;
  4, 5, 6 — P&L: накопленный финансовый результат (в капитал);
  7 — расчёты: остаток по каждому договору — дебетовый в активы
      (авансы выданные, дебиторка), кредитовый в пассивы (долги, авансы полученные);
  8 — забалансовые, не берутся.
Остаток = Σ(dt − cr): актив — плюс; обязательства и капитал показываются плюсом (cr − dt).
Контроль: активы − пассивы. Не ноль — проводки без пары; где они — лист «Контроль».
"""
from __future__ import annotations

import io
from datetime import date

import pandas as pd

TOL = 1.0

FACT_SQL = """
SELECT f.acc_id, f.contract_id AS cid, COALESCE(f.chapter, '') AS chapter,
       SUM(f.dt - f.cr) FILTER (WHERE f.date_from <= ?) / 100.0 AS b0,
       SUM(f.dt - f.cr) FILTER (WHERE f.date_from <= ?) / 100.0 AS b1
FROM pg.gl.fact f
GROUP BY 1, 2, 3
"""
COA_SQL = """
SELECT id, CAST(code AS VARCHAR) AS code, name FROM pg.public.corporate_coa
"""
CTR_SQL = """
SELECT k.id AS cid,
       COALESCE(ct.title, 'Договор') || ' № ' || COALESCE(k.number, 'б/н') || ' от '
           || COALESCE(strftime(k.date, '%d.%m.%Y'), 'б/д') || ' · id ' || CAST(k.id AS VARCHAR)
           AS contract,
       COALESCE(NULLIF(TRIM(cp.name), ''), 'Без контрагента') AS cp
FROM pg.public.contracts_contracts k
LEFT JOIN pg.public.contracts_contractstitle ct ON ct.id = k.title_id
LEFT JOIN pg.public.counterparties_counterparty cp ON cp.id = k.cp_id
"""


def build(report_date: date, con) -> dict:
    d0 = date(report_date.year - 1, 12, 31)
    fact = con.execute(FACT_SQL, [d0, report_date]).df()
    coa = con.execute(COA_SQL).df()
    ctr = con.execute(CTR_SQL).df()

    fact[["b0", "b1"]] = fact[["b0", "b1"]].fillna(0.0)
    code = coa.set_index("id")["code"].fillna("").astype(str)
    name_by_code = dict(zip(coa["code"].astype(str), coa["name"]))
    fact["code"] = fact["acc_id"].map(code).fillna("")
    fact["kind"] = fact["code"].str[:1]
    fact["grp"] = fact["code"].str[:2] + "0000"
    fact = fact[fact["kind"] != "8"]

    acc_name = lambda c: f"{c} {name_by_code.get(c, '')}".strip()
    grp_name = lambda g: f"{g} {name_by_code.get(g, '')}".strip()

    # счета 1, 2, 3 — по счёту
    plain = (fact[fact["kind"].isin(["1", "2", "3"])]
             .groupby(["kind", "grp", "code"], as_index=False)[["b0", "b1"]].sum())

    # расчёты 7 — по договору, сторона по знаку остатка
    st = (fact[fact["kind"] == "7"].groupby(["grp", "code", "cid"], dropna=False,
                                             as_index=False)[["b0", "b1"]].sum())
    st = st.merge(ctr, on="cid", how="left")
    st["cp"] = st["cp"].fillna("Без договора")
    st["contract"] = st["contract"].fillna("без договора")
    for b in ("b0", "b1"):
        st[f"a_{b}"] = st[b].clip(lower=0)            # дебет — актив
        st[f"l_{b}"] = (-st[b]).clip(lower=0)         # кредит — пассив

    # P&L 4–6 — накопленный результат (прибыль — плюс)
    pl = fact[fact["kind"].isin(["4", "5", "6"])][["b0", "b1"]].sum()
    res_prev, res_all = -pl["b0"], -pl["b1"]

    rows = []                                       # (уровень, код, название, b0, b1, вид)

    def add(level, cd, nm, v0, v1, kind="row"):
        rows.append((level, cd, nm, float(v0), float(v1), kind))

    # ---- АКТИВЫ
    a_rows = []
    for g, gdf in plain[plain["kind"] == "1"].groupby("grp"):
        a_rows.append((g, gdf))
    st_a = st[(st["a_b0"] > TOL) | (st["a_b1"] > TOL)]
    ast0 = sum(gdf["b0"].sum() for _, gdf in a_rows) + st["a_b0"].sum()
    ast1 = sum(gdf["b1"].sum() for _, gdf in a_rows) + st["a_b1"].sum()
    add(0, "", "АКТИВЫ", ast0, ast1, "band")
    for g, gdf in a_rows:
        add(1, g, grp_name(g), gdf["b0"].sum(), gdf["b1"].sum(), "grp")
        for r in gdf.itertuples(index=False):
            if abs(r.b0) >= TOL or abs(r.b1) >= TOL:
                add(2, r.code, acc_name(r.code), r.b0, r.b1)
    add(1, "7…", "Расчёты — дебетовые остатки: авансы выданные, нам должны",
        st["a_b0"].sum(), st["a_b1"].sum(), "grp")
    for g, gdf in st_a.groupby("grp"):
        add(2, g, grp_name(g), gdf["a_b0"].sum(), gdf["a_b1"].sum())

    # ---- ПАССИВЫ
    lia = plain[plain["kind"] == "2"]
    cap = plain[plain["kind"] == "3"]
    st_l = st[(st["l_b0"] > TOL) | (st["l_b1"] > TOL)]
    l0 = -lia["b0"].sum() + st["l_b0"].sum()
    l1 = -lia["b1"].sum() + st["l_b1"].sum()
    c0 = -cap["b0"].sum() + res_prev
    c1 = -cap["b1"].sum() + res_all
    add(0, "", "ПАССИВЫ", l0 + c0, l1 + c1, "band")
    add(1, "", "Обязательства", l0, l1, "grp")
    for r in lia.itertuples(index=False):
        if abs(r.b0) >= TOL or abs(r.b1) >= TOL:
            add(2, r.code, acc_name(r.code), -r.b0, -r.b1)
    add(2, "7…", "Расчёты — кредитовые остатки: долги, авансы полученные",
        st["l_b0"].sum(), st["l_b1"].sum(), "sub")
    for g, gdf in st_l.groupby("grp"):
        add(3, g, grp_name(g), gdf["l_b0"].sum(), gdf["l_b1"].sum())
    add(1, "", "Капитал", c0, c1, "grp")
    for r in cap.itertuples(index=False):
        if abs(r.b0) >= TOL or abs(r.b1) >= TOL:
            add(2, r.code, acc_name(r.code), -r.b0, -r.b1)
    add(2, "", f"Финансовый результат прошлых лет (P&L до {d0:%d.%m.%Y})",
        res_prev, res_prev)
    add(2, "", f"Финансовый результат {report_date.year} года", 0.0, res_all - res_prev)

    # ---- контроль
    add(0, "", "КОНТРОЛЬ: активы − пассивы (должно быть 0)",
        ast0 - (l0 + c0), ast1 - (l1 + c1), "check")

    bal = pd.DataFrame(rows, columns=["level", "code", "name", "b0", "b1", "kind"])
    bal["chg"] = bal["b1"] - bal["b0"]

    # где небаланс: сумма dt − cr по разделам учёта (без забалансовых)
    ctl = fact.groupby("chapter", as_index=False)[["b0", "b1"]].sum()
    ctl = ctl[(ctl["b0"].abs() >= TOL) | (ctl["b1"].abs() >= TOL)]
    ctl = ctl.sort_values("b1", key=lambda s: -s.abs())
    ctl_acc = (fact.groupby(["chapter", "code"], as_index=False)[["b0", "b1"]].sum())
    ctl_acc = ctl_acc[ctl_acc["chapter"].isin(ctl["chapter"])
                      & ((ctl_acc["b1"].abs() >= TOL) | (ctl_acc["b0"].abs() >= TOL))]
    ctl_acc["acc"] = ctl_acc["code"].map(acc_name)
    ctl_acc = ctl_acc.sort_values(["chapter", "code"])

    # расчёты по договорам
    st["acc"] = st["code"].map(acc_name)
    st["side"] = st["b1"].map(lambda v: "дебет: нам должны / аванс выдан" if v > TOL
                              else "кредит: мы должны / аванс получен" if v < -TOL else "—")
    stl = st[(st["b0"].abs() >= TOL) | (st["b1"].abs() >= TOL)].sort_values(
        ["acc", "cp", "contract"], key=lambda x: x.astype(str).str.upper())

    accs = (fact.groupby("code", as_index=False)[["b0", "b1"]].sum())
    accs = accs[(accs["b0"].abs() >= TOL) | (accs["b1"].abs() >= TOL)]
    accs["acc"] = accs["code"].map(acc_name)
    accs = accs.sort_values("code")
    return {"bal": bal, "ctl": ctl, "ctl_acc": ctl_acc, "st": stl, "accs": accs, "d0": d0}


# ---------------------------------------------------------------- Excel
def to_excel(res: dict, report_date: date) -> bytes:
    from gear.management.commands import mp
    import xlsxwriter

    d0 = res["d0"]
    h0, h1 = f"на {d0:%d.%m.%Y}, ₽", f"на {report_date:%d.%m.%Y}, ₽"
    buf = io.BytesIO()
    wb = xlsxwriter.Workbook(buf, {"nan_inf_to_errors": True})
    base = {"font_name": mp.FONT, "font_size": 9, "font_color": "#" + mp.TEXT, "valign": "top"}
    line = {"bottom": 1, "bottom_color": "#" + mp.LINE}
    F = lambda **k: wb.add_format({**base, **k})
    fmt = {
        "title": F(font_size=14, bold=True), "sub": F(font_color="#" + mp.TEXT_2),
        "hdr": F(bold=True, font_color="#FFFFFF", bg_color="#" + mp.NAVY, text_wrap=True,
                 align="center", valign="vcenter", border=1, border_color="#" + mp.NAVY_2),
        "text": F(**line), "wrap": F(**line, text_wrap=True),
        "money": F(**line, num_format=mp.FMT_MONEY), "code": F(**line, font_color="#" + mp.MUTED),
        "band": F(bold=True, font_color="#FFFFFF", bg_color="#" + mp.NAVY_3),
        "band_m": F(bold=True, font_color="#FFFFFF", bg_color="#" + mp.NAVY_3,
                    num_format=mp.FMT_MONEY),
        "grp": F(bold=True, bg_color="#E8F0EC", **line),
        "grp_m": F(bold=True, bg_color="#E8F0EC", **line, num_format=mp.FMT_MONEY),
        "check": F(bold=True, bg_color="#FFF3C4", top=1, bottom=1),
        "check_m": F(bold=True, bg_color="#FFF3C4", top=1, bottom=1, num_format=mp.FMT_MONEY),
        "lbl": F(bold=True, font_color="#" + mp.NAVY_3, **line),
    }
    sub = (f"Остатки по счетам учёта (gl.fact) · сформировано "
           + pd.Timestamp.now().strftime("%d.%m.%Y %H:%M"))

    def m(v):
        v = float(v or 0)
        return 0.0 if abs(v) < 0.5 else v

    # Баланс
    ws = wb.add_worksheet("Баланс")
    ws.set_column(0, 0, 10)
    ws.set_column(1, 1, 60)
    ws.set_column(2, 4, 16)
    ws.write(0, 0, "Баланс (проверка)", fmt["title"])
    ws.write(1, 0, sub, fmt["sub"])
    for j, h in enumerate(("КОД", "СТАТЬЯ", h0.upper(), h1.upper(), "ИЗМЕНЕНИЕ, ₽")):
        ws.write(3, j, h, fmt["hdr"])
    ws.set_row(3, 30)
    for i, r in enumerate(res["bal"].itertuples(index=False), start=4):
        k = r.kind
        tf, mf = {"band": ("band", "band_m"), "grp": ("grp", "grp_m"),
                  "check": ("check", "check_m")}.get(k, ("text", "money"))
        ws.write(i, 0, r.code, fmt[tf] if k != "row" else fmt["code"])
        ws.write(i, 1, ("    " * max(r.level - 1, 0)) + r.name, fmt[tf])
        for j, v in ((2, r.b0), (3, r.b1), (4, r.chg)):
            ws.write_number(i, j, m(v), fmt[mf])
        if k == "row" and r.level >= 2:
            ws.set_row(i, None, None, {"level": 1})
    ws.freeze_panes(4, 2)

    def table(name, title, cols, df):
        ws = wb.add_worksheet(name)
        ws.write(0, 0, title, fmt["title"])
        ws.write(1, 0, sub, fmt["sub"])
        for j, (_k, h, _t, w) in enumerate(cols):
            ws.write(3, j, h, fmt["hdr"])
            ws.set_column(j, j, w)
        ws.set_row(3, 30)
        for i, row in enumerate(df[[c[0] for c in cols]].itertuples(index=False), start=4):
            for j, ((_k, _h, t, _w), v) in enumerate(zip(cols, row)):
                if t == "money":
                    ws.write_number(i, j, m(v), fmt["money"])
                elif v is None or (not isinstance(v, str) and pd.isna(v)):
                    ws.write_blank(i, j, None, fmt["text"])
                else:
                    ws.write(i, j, str(v), fmt[t])
        ws.autofilter(3, 0, max(3 + len(df), 3), len(cols) - 1)
        ws.freeze_panes(4, 0)

    table("Расчёты по договорам", "Расчёты (счета 7…) по договорам",
          [("acc", "Счёт", "wrap", 30), ("cp", "Контрагент", "wrap", 28),
           ("contract", "Договор", "wrap", 32), ("cid", "ID", "text", 7),
           ("b0", h0, "money", 15), ("b1", h1, "money", 15),
           ("side", "Сторона на отчётную дату", "wrap", 26)], res["st"])
    table("Счета", "Остатки по всем счетам (дебет +, кредит −)",
          [("acc", "Счёт", "wrap", 44), ("b0", h0, "money", 16), ("b1", h1, "money", 16)],
          res["accs"])
    table("Контроль", "Где небаланс: сумма дебет − кредит по разделам учёта",
          [("chapter", "Раздел учёта (chapter)", "wrap", 30), ("b0", h0, "money", 16),
           ("b1", h1, "money", 16)], res["ctl"])
    table("Контроль по счетам", "Разделы с небалансом — по счетам",
          [("chapter", "Раздел учёта", "wrap", 26), ("acc", "Счёт", "wrap", 40),
           ("b0", h0, "money", 16), ("b1", h1, "money", 16)], res["ctl_acc"])

    ws = wb.add_worksheet("Как читать")
    ws.set_column(0, 0, 20)
    ws.set_column(1, 1, 110)
    ws.write(0, 0, "Как читать", fmt["title"])
    notes = [
        ("Что это", "Баланс по остаткам счетов учёта на дату: на конец прошлого года и на "
                    "отчётную дату. Это проверочная версия — сначала выверка, потом лист в манпак."),
        ("Счета 1…", "Активы: деньги, депозиты, баланс WB, запасы, внеоборотные."),
        ("Счета 7…", "Расчёты: остаток считается по каждому договору. Дебетовый (нам должны, "
                     "аванс выдан) — в активы, кредитовый (мы должны, аванс получен) — в пассивы. "
                     "Подробно — лист «Расчёты по договорам»."),
        ("Счета 2…, 3…", "Обязательства и капитал."),
        ("Счета 4–6", "Доходы и расходы: их накопленный итог — финансовый результат в капитале "
                      "(прошлых лет и текущего года)."),
        ("Контроль", "Активы минус пассивы. При полной двойной записи — 0. Не ноль — есть "
                     "проводки без пары (например, движение денег без начисления). Лист "
                     "«Контроль» показывает, в каких разделах учёта сумма дебет − кредит не "
                     "ноль, «Контроль по счетам» — на каких счетах."),
        ("Забалансовые", "Счета 8… не берутся."),
    ]
    for i, (a, b) in enumerate(notes, start=2):
        ws.write(i, 0, a, fmt["lbl"])
        ws.write(i, 1, b, fmt["wrap"])
        ws.set_row(i, 32)
    wb.close()
    return buf.getvalue()


def build_balance_workbook(report_date: date) -> tuple[bytes, str]:
    from conns import get_duckdb_conn_with_opt
    with get_duckdb_conn_with_opt(ro=True) as con:
        res = build(report_date, con)
    return to_excel(res, report_date), f"Баланс (проверка) {report_date:%Y%m%d}.xlsx"
