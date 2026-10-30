# gear/app/manpack/balance_check.py
"""Баланс (проверка): активы и пассивы на дату по остаткам gl.fact, собранные по участкам.

gl.fact — не полная двойная запись, поэтому перед сборкой:
  • ST_WB (780012) не берётся: дублирует баланс WB (114001, CF_WB);
  • себестоимость (PL_write_off) уменьшает запасы 130001 — списание с запасов в учёте нет;
  • по каждому договору недостающая пара денег (оплата без проводки по расчётам)
    достраивается на счёт расчётов договора: остаток расчётов = расчёты 7… − Σ всех
    проводок договора. Так работает для Cash Based, начислений по графику, депозитов, займов.
Проводки без договора не достраиваются — их сумма и есть небаланс (лист «Контроль»).
Скрипт только читает базу.
"""
from __future__ import annotations

import io
from datetime import date

import pandas as pd

TOL = 1.0
DROP_CHAPTERS = ("ST_WB",)          # дубль CF_WB
COGS_CHAPTER = "PL_write_off"       # себестоимость: пара — запасы
INV_CODE = "130001"

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
       COALESCE(NULLIF(TRIM(cp.name), ''), 'Без контрагента') AS cp,
       k.bs_id AS st_acc
FROM pg.public.contracts_contracts k
LEFT JOIN pg.public.contracts_contractstitle ct ON ct.id = k.title_id
LEFT JOIN pg.public.counterparties_counterparty cp ON cp.id = k.cp_id
"""

# участки баланса: (префикс кода, раздел, строка)
CASH_LINES = (("111", "Банковские счета"), ("112", "Касса"), ("113", "Депозиты"),
              ("114", "Баланс маркетплейса (WB)"), ("115", "Деньги в пути"))
ST_GROUPS = {"72": "поставщики и подрядчики", "74": "сотрудники", "75": "налоги и сборы",
             "76": "учредители", "77": "кредиты, займы, депозиты", "78": "маркетплейс WB",
             "79": "внутригрупповые и переводы", "71": "покупатели"}


def build(report_date: date, con) -> dict:
    d0 = date(report_date.year - 1, 12, 31)
    fact = con.execute(FACT_SQL, [d0, report_date]).df()
    coa = con.execute(COA_SQL).df()
    ctr = con.execute(CTR_SQL).df()

    fact[["b0", "b1"]] = fact[["b0", "b1"]].fillna(0.0)
    code_of = coa.set_index("id")["code"].fillna("").astype(str)
    name_by_code = dict(zip(coa["code"].astype(str), coa["name"]))
    acc_name = lambda c: f"{c} {name_by_code.get(c, '')}".strip()
    fact["code"] = fact["acc_id"].map(code_of).fillna("")
    fact = fact[~fact["code"].str.startswith("8")]
    dropped = fact[fact["chapter"].isin(DROP_CHAPTERS)][["b0", "b1"]].sum()
    fact = fact[~fact["chapter"].isin(DROP_CHAPTERS)].copy()
    fact["src"] = "учёт"

    # себестоимость снимается с запасов
    cogs = fact[fact["chapter"] == COGS_CHAPTER]
    inv = cogs.assign(code=INV_CODE, chapter="запасы − себестоимость",
                      b0=-cogs["b0"], b1=-cogs["b1"], src="списание себестоимости")

    # недостающая пара по договорам — на счёт расчётов договора
    ctr["st_code"] = ctr["st_acc"].map(code_of)
    st_code = ctr.set_index("cid")["st_code"]
    allr = pd.concat([fact, inv], ignore_index=True)
    withc = allr[allr["cid"].notna()]
    imb = withc.groupby("cid", as_index=False)[["b0", "b1"]].sum()
    imb["code"] = imb["cid"].map(st_code)
    # нет счёта расчётов в договоре — самый частый счёт 7… в его проводках
    t7 = (withc[withc["code"].str.startswith("7") & ~withc["code"].str.startswith("73")]
          .assign(a=lambda x: x["b1"].abs()).sort_values("a")
          .drop_duplicates("cid", keep="last").set_index("cid")["code"])
    imb["code"] = imb["code"].fillna(imb["cid"].map(t7)).fillna("7")
    pair = imb.assign(b0=-imb["b0"], b1=-imb["b1"], chapter="пара к деньгам",
                      src="достроено: оплаты по договору")
    allr = pd.concat([allr, pair], ignore_index=True)

    c = allr["code"].astype(str)
    allr["sec"] = None
    for pfx, nm in CASH_LINES:
        allr.loc[c.str.startswith(pfx), "sec"] = "cash:" + nm
    allr.loc[allr["sec"].isna() & c.str.startswith("11"), "sec"] = "cash:Прочие денежные средства"
    allr.loc[c.str.startswith("12"), "sec"] = "recv"
    allr.loc[c.str.startswith("13"), "sec"] = "inv"
    allr.loc[c.str.startswith("14"), "sec"] = "fixed"
    allr.loc[c.str.startswith("2"), "sec"] = "liab"
    allr.loc[c.str.startswith("3"), "sec"] = "cap"
    allr.loc[c.str[:1].isin(["4", "5", "6"]), "sec"] = "pl"
    allr.loc[c.str.startswith("73"), "sec"] = "vat"
    allr.loc[c.str.startswith("7") & ~c.str.startswith("73"), "sec"] = "st"
    allr.loc[allr["sec"].isna(), "sec"] = "other"

    S = lambda m, col: float(allr.loc[m, col].sum())

    # расчёты: остаток по договору (и без договора — по счёту), сторона по знаку
    st = allr[allr["sec"] == "st"].copy()
    st["grp"] = st["code"].str[:2]
    st["key"] = st["cid"].astype("Int64").astype(str).where(st["cid"].notna(), "acc:" + st["code"])
    stc = st.groupby(["key", "grp"], as_index=False).agg(
        cid=("cid", "first"), code=("code", "first"), b0=("b0", "sum"), b1=("b1", "sum"))
    stc = stc.merge(ctr[["cid", "cp", "contract"]], on="cid", how="left")
    stc["cp"] = stc["cp"].fillna("Без договора")
    stc["contract"] = stc["contract"].fillna(stc["code"].map(acc_name))
    stc["grp_name"] = stc["grp"].map(lambda g: ST_GROUPS.get(g, g))

    rows = []

    def add(level, cd, nm, v0, v1, kind="row"):
        rows.append((level, cd, nm, float(v0), float(v1), kind))

    def side(df, sign):
        return (df["b0"] * sign).clip(lower=0).sum(), (df["b1"] * sign).clip(lower=0).sum()

    # ---- АКТИВЫ
    cash_secs = [s for s in allr["sec"].unique() if str(s).startswith("cash:")]
    cash0, cash1 = S(allr["sec"].isin(cash_secs), "b0"), S(allr["sec"].isin(cash_secs), "b1")
    recv0, recv1 = S(allr["sec"] == "recv", "b0"), S(allr["sec"] == "recv", "b1")
    sta0, sta1 = side(stc, 1)
    vat0, vat1 = S(allr["sec"] == "vat", "b0"), S(allr["sec"] == "vat", "b1")
    inv0, inv1 = S(allr["sec"] == "inv", "b0"), S(allr["sec"] == "inv", "b1")
    fx0, fx1 = S(allr["sec"] == "fixed", "b0"), S(allr["sec"] == "fixed", "b1")
    oth0, oth1 = S(allr["sec"] == "other", "b0"), S(allr["sec"] == "other", "b1")
    A0 = cash0 + recv0 + sta0 + max(vat0, 0) + inv0 + fx0 + oth0
    A1 = cash1 + recv1 + sta1 + max(vat1, 0) + inv1 + fx1 + oth1
    add(0, "", "АКТИВЫ", A0, A1, "band")
    add(1, "", "Денежные средства", cash0, cash1, "grp")
    for nm in [n for _, n in CASH_LINES] + ["Прочие денежные средства"]:
        m = allr["sec"] == "cash:" + nm
        if not m.any():
            continue
        add(2, "", nm, S(m, "b0"), S(m, "b1"), "sub")
        for cd, g in allr[m].groupby("code"):
            if abs(g["b0"].sum()) >= TOL or abs(g["b1"].sum()) >= TOL:
                add(3, cd, acc_name(cd), g["b0"].sum(), g["b1"].sum())
    add(1, "", "Дебиторская задолженность и авансы выданные", recv0 + sta0, recv1 + sta1, "grp")
    for cd, g in allr[allr["sec"] == "recv"].groupby("code"):
        add(2, cd, acc_name(cd), g["b0"].sum(), g["b1"].sum())
    for gcode, g in stc.groupby("grp"):
        v0, v1 = side(g, 1)
        if v0 >= TOL or v1 >= TOL:
            add(2, gcode + "…", "Расчёты: " + ST_GROUPS.get(gcode, gcode), v0, v1)
    if vat0 > 0 or vat1 > 0:
        add(1, "73…", "НДС к возмещению (расчёты по НДС, дебет)", max(vat0, 0), max(vat1, 0), "grp")
    add(1, "", "Запасы", inv0, inv1, "grp")
    m = (allr["sec"] == "inv") & (allr["src"] == "учёт")
    add(2, "", "закуплено и прочее (счета 13…)", S(m, "b0"), S(m, "b1"))
    m = (allr["sec"] == "inv") & (allr["src"] == "списание себестоимости")
    add(2, "", "минус списано в себестоимость (510000)", S(m, "b0"), S(m, "b1"))
    add(1, "", "Внеоборотные активы", fx0, fx1, "grp")
    for cd, g in allr[allr["sec"] == "fixed"].groupby("code"):
        add(2, cd, acc_name(cd), g["b0"].sum(), g["b1"].sum())
    if abs(oth0) >= TOL or abs(oth1) >= TOL:
        add(1, "", "Прочие счета", oth0, oth1, "grp")

    # ---- ПАССИВЫ
    stl0, stl1 = side(stc, -1)
    loans = stc[stc["grp"] == "77"]
    ln0, ln1 = side(loans, -1)
    lia0, lia1 = -S(allr["sec"] == "liab", "b0"), -S(allr["sec"] == "liab", "b1")
    vl0, vl1 = max(-vat0, 0), max(-vat1, 0)
    L0, L1 = stl0 + lia0 + vl0, stl1 + lia1 + vl1
    cap0, cap1 = -S(allr["sec"] == "cap", "b0"), -S(allr["sec"] == "cap", "b1")
    pl0, pl1 = -S(allr["sec"] == "pl", "b0"), -S(allr["sec"] == "pl", "b1")
    E0, E1 = cap0 + pl0, cap1 + pl1
    add(0, "", "ПАССИВЫ", L0 + E0, L1 + E1, "band")
    add(1, "", "Обязательства", L0, L1, "grp")
    add(2, "77…", "Кредиты и займы полученные (тело и проценты)", ln0, ln1, "sub")
    oth_l = stc[stc["grp"] != "77"]
    o0, o1 = side(oth_l, -1)
    add(2, "", "Кредиторская задолженность и авансы полученные", o0, o1, "sub")
    for gcode, g in oth_l.groupby("grp"):
        v0, v1 = side(g, -1)
        if v0 >= TOL or v1 >= TOL:
            add(3, gcode + "…", "Расчёты: " + ST_GROUPS.get(gcode, gcode), v0, v1)
    if vl0 or vl1:
        add(2, "73…", "НДС к уплате (расчёты по НДС, кредит)", vl0, vl1, "sub")
    if abs(lia0) >= TOL or abs(lia1) >= TOL:
        add(2, "2…", "Прочие обязательства (счета 2…)", lia0, lia1, "sub")
    add(1, "", "Капитал", E0, E1, "grp")
    for cd, g in allr[allr["sec"] == "cap"].groupby("code"):
        add(2, cd, acc_name(cd), -g["b0"].sum(), -g["b1"].sum())
    add(2, "", f"Финансовый результат прошлых лет (до {d0:%d.%m.%Y})", pl0, pl0)
    add(2, "", f"Финансовый результат {report_date.year} года", 0.0, pl1 - pl0)
    add(0, "", "КОНТРОЛЬ: активы − пассивы (должно быть 0)", A0 - L0 - E0, A1 - L1 - E1, "check")

    bal = pd.DataFrame(rows, columns=["level", "code", "name", "b0", "b1", "kind"])
    bal["chg"] = bal["b1"] - bal["b0"]

    # контроль: проводки без договора (у них пара не достраивается)
    noc = allr[allr["cid"].isna()]
    ctl = noc.groupby(["chapter", "code"], as_index=False)[["b0", "b1"]].sum()
    ctl = ctl[(ctl["b0"].abs() >= TOL) | (ctl["b1"].abs() >= TOL)]
    ctl["acc"] = ctl["code"].map(acc_name)
    ctl = ctl.sort_values(["chapter", "code"])

    stc["side"] = stc["b1"].map(lambda v: "актив: нам должны / аванс выдан" if v > TOL
                                else "пассив: мы должны / аванс получен" if v < -TOL else "—")
    stc["acc"] = stc["code"].map(acc_name)
    stl = stc[(stc["b0"].abs() >= TOL) | (stc["b1"].abs() >= TOL)].sort_values(
        ["grp_name", "cp", "contract"], key=lambda x: x.astype(str).str.upper())

    accs = allr.groupby(["code", "src"], as_index=False)[["b0", "b1"]].sum()
    accs = accs[(accs["b0"].abs() >= TOL) | (accs["b1"].abs() >= TOL)]
    accs["acc"] = accs["code"].map(acc_name)
    accs = accs.sort_values(["code", "src"])
    return {"bal": bal, "ctl": ctl, "st": stl, "accs": accs, "d0": d0,
            "dropped": dropped}


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
        "sub_t": F(bold=True, **line), "sub_m": F(bold=True, **line, num_format=mp.FMT_MONEY),
        "check": F(bold=True, bg_color="#FFF3C4", top=1, bottom=1),
        "check_m": F(bold=True, bg_color="#FFF3C4", top=1, bottom=1, num_format=mp.FMT_MONEY),
        "lbl": F(bold=True, font_color="#" + mp.NAVY_3, **line),
    }
    sub = ("По остаткам учёта (gl.fact), собрано по участкам · сформировано "
           + pd.Timestamp.now().strftime("%d.%m.%Y %H:%M"))
    m = lambda v: 0.0 if abs(float(v or 0)) < 0.5 else float(v)

    ws = wb.add_worksheet("Баланс")
    ws.set_column(0, 0, 9)
    ws.set_column(1, 1, 62)
    ws.set_column(2, 4, 17)
    ws.write(0, 0, "Баланс (проверка)", fmt["title"])
    ws.write(1, 0, sub, fmt["sub"])
    for j, h in enumerate(("КОД", "СТАТЬЯ", h0.upper(), h1.upper(), "ИЗМЕНЕНИЕ, ₽")):
        ws.write(3, j, h, fmt["hdr"])
    ws.set_row(3, 30)
    style = {"band": ("band", "band_m"), "grp": ("grp", "grp_m"), "sub": ("sub_t", "sub_m"),
             "check": ("check", "check_m")}
    for i, r in enumerate(res["bal"].itertuples(index=False), start=4):
        tf, mf = style.get(r.kind, ("text", "money"))
        ws.write(i, 0, r.code, fmt["code"] if r.kind == "row" else fmt[tf])
        ws.write(i, 1, ("    " * max(r.level - 1, 0)) + r.name, fmt[tf])
        for j, v in ((2, r.b0), (3, r.b1), (4, r.chg)):
            ws.write_number(i, j, m(v), fmt[mf])
        if r.kind == "row" and r.level >= 3:
            ws.set_row(i, None, None, {"level": 1, "hidden": True})
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

    table("Расчёты по договорам", "Расчёты по договорам (с учётом оплат)",
          [("grp_name", "Участок", "wrap", 22), ("cp", "Контрагент", "wrap", 28),
           ("contract", "Договор", "wrap", 34), ("cid", "ID", "text", 7),
           ("b0", h0 + " (+ нам должны, − мы должны)", "money", 16), ("b1", h1, "money", 16),
           ("side", "Сторона на отчётную дату", "wrap", 26)], res["st"])
    table("Контроль", "Проводки без договора — пара к ним не достраивается; их сумма = небаланс",
          [("chapter", "Раздел учёта", "wrap", 24), ("acc", "Счёт", "wrap", 40),
           ("b0", h0, "money", 16), ("b1", h1, "money", 16)], res["ctl"])
    table("Счета", "Остатки по счетам после сборки (дебет +, кредит −)",
          [("acc", "Счёт", "wrap", 44), ("src", "Источник", "wrap", 28),
           ("b0", h0, "money", 16), ("b1", h1, "money", 16)], res["accs"])

    ws = wb.add_worksheet("Как читать")
    ws.set_column(0, 0, 22)
    ws.set_column(1, 1, 110)
    ws.write(0, 0, "Как читать", fmt["title"])
    dr = res["dropped"]
    notes = [
        ("Что это", "Баланс на конец прошлого года и на отчётную дату по остаткам учёта. "
                    "Проверочная версия: сначала выверка, потом лист в манпак."),
        ("Деньги", "Банковские счета 111…, касса, депозиты 113…, баланс WB 114001, деньги в пути."),
        ("Расчёты", "По каждому договору: проводки по счёту расчётов плюс оплаты по договору — "
                    "как в «Списании договоров». Положительный остаток — в активы (нам должны, "
                    "аванс выдан), отрицательный — в пассивы (мы должны, аванс получен). "
                    "Кредиты и займы — отдельной строкой. Подробно — «Расчёты по договорам»."),
        ("Баланс WB", "Берётся 114001. Расчёты с WB 780012 (раздел ST_WB) не берутся — они "
                      f"повторяют баланс WB ({m(dr['b1']):,.0f} ₽ на отчётную дату)."
                      .replace(",", " ")),
        ("Запасы", "Закупки на 130… минус списанная себестоимость (510000): в учёте списание "
                   "себестоимости с запасов не проводится. Сверить с остатками на складах."),
        ("НДС", "Расчёты 73…: дебет — к возмещению (актив), кредит — к уплате (пассив)."),
        ("Капитал", "Взносы (3…) плюс накопленный результат P&L (счета 4–6): прошлых лет и "
                    "текущего года."),
        ("Контроль", "Активы − пассивы. Не ноль — проводки без договора: у них нет пары. "
                     "Где именно — лист «Контроль»."),
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
