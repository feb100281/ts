# gear/app/manpack/balance_check.py
"""Баланс (проверка): активы и пассивы на дату по остаткам gl.fact, собранные по участкам.

gl.fact — не полная двойная запись, поэтому перед сборкой:
  • ST_WB (780012) не берётся: дублирует баланс WB (114001, CF_WB);
  • по каждому договору недостающая пара денег достраивается: у маркетплейса — на баланс
    WB 114001 (вывод средств уменьшает баланс), у остальных — на счёт расчётов договора;
  • запасы: товар на складах = поступило по УПД (inventories.inv_gl) − себестоимость
    (PL_write_off); оплачено поставщикам товара (130…) − УПД = аванс (актив) или долг (пассив).
Проводки без договора не достраиваются — их сумма и есть небаланс (лист «Контроль»).
Скрипт только читает базу.
"""
from __future__ import annotations

import io
from datetime import date

import pandas as pd

TOL = 1.0
DROP_CHAPTERS = ("ST_WB",)
COGS_CHAPTER = "PL_write_off"
WB_BAL = "114001"

FACT_SQL = """
SELECT f.acc_id, f.contract_id AS cid, COALESCE(f.chapter, '') AS chapter,
       f.subconto_id AS sub,
       SUM(f.dt - f.cr) FILTER (WHERE f.date_from <= ?) / 100.0 AS b0,
       SUM(f.dt - f.cr) FILTER (WHERE f.date_from <= ?) / 100.0 AS b1
FROM pg.gl.fact f
GROUP BY 1, 2, 3, 4
"""
COA_SQL = "SELECT id, CAST(code AS VARCHAR) AS code, name FROM pg.public.corporate_coa"
ITEM_SQL = """
SELECT CAST(id AS BIGINT) AS id, CAST(code AS VARCHAR) || ' ' || name AS name
FROM pg.public.corporate_cfitems
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
INV_SQL = """
SELECT SUM(dt) FILTER (WHERE date_from::DATE <= ?) / 100.0 AS i0,
       SUM(dt) FILTER (WHERE date_from::DATE <= ?) / 100.0 AS i1
FROM inventories.inv_gl
"""
UPD_SQL = """
SELECT d.contract_id AS cid,
       SUM(l.upd_amount_vatless) FILTER (WHERE d.date <= ?) AS u0,
       SUM(l.upd_amount_vatless) FILTER (WHERE d.date <= ?) AS u1
FROM pg.public.upd_income_lines l
JOIN pg.public.cards_upddocument d ON d.id = l.upd_document_id
WHERE d.contract_id IS NOT NULL
GROUP BY 1
"""
WB_LK_SQL = """
SELECT "Конечный баланс" AS v FROM pg.wb_balance_for_csv
WHERE date_from = (SELECT MAX(date_from) FROM pg.wb_balance_for_csv WHERE date_from <= ?)
"""

CASH_LINES = (("111", "Банковские счета"), ("112", "Касса"), ("113", "Депозиты"),
              ("114", "Баланс маркетплейса (WB)"), ("115", "Деньги в пути"))


def _q(con, sql, params, cols):
    try:
        return con.execute(sql, params).df()
    except Exception as e:                       # источник недоступен — отчёт всё равно собирается
        import logging
        logging.getLogger(__name__).warning("Баланс: %s", e)
        return pd.DataFrame(columns=cols)


def build(report_date: date, con) -> dict:
    from .contracts_check import is_marketplace

    d0 = date(report_date.year - 1, 12, 31)
    fact = con.execute(FACT_SQL, [d0, report_date]).df()
    coa = con.execute(COA_SQL).df()
    items = con.execute(ITEM_SQL).df()
    ctr = con.execute(CTR_SQL).df()
    inv_gl = _q(con, INV_SQL, [d0, report_date], ["i0", "i1"])
    upd = _q(con, UPD_SQL, [d0, report_date], ["cid", "u0", "u1"])
    wb_lk = {k: _q(con, WB_LK_SQL, [d], ["v"]) for k, d in (("b0", d0), ("b1", report_date))}

    fact[["b0", "b1"]] = fact[["b0", "b1"]].fillna(0.0)
    code_of = coa.set_index("id")["code"].fillna("").astype(str)
    name_by_code = dict(zip(coa["code"].astype(str), coa["name"]))
    item_name = items.set_index("id")["name"]
    acc_name = lambda c: f"{c} {name_by_code.get(str(c), '')}".strip()
    fact["code"] = fact["acc_id"].map(code_of).fillna("")
    fact = fact[~fact["code"].str.startswith("8")]
    dropped = fact[fact["chapter"].isin(DROP_CHAPTERS)][["b0", "b1"]].sum()
    fact = fact[~fact["chapter"].isin(DROP_CHAPTERS)].copy()
    fact["src"] = "учёт"

    ctr["mp"] = ctr["cp"].apply(is_marketplace)
    ctr["st_code"] = ctr["st_acc"].map(code_of)
    info = ctr.set_index("cid")
    label = lambda cid: (f"{info.at[cid, 'cp']} · {info.at[cid, 'contract']}"
                         if cid in info.index else f"договор id {cid}")

    # себестоимость снимается с запасов (строкой «списано в себестоимость»)
    cogs = fact[fact["chapter"] == COGS_CHAPTER]
    inv = cogs.assign(code="130001", chapter="запасы − себестоимость",
                      b0=-cogs["b0"], b1=-cogs["b1"], src="cogs", sub=None)

    # недостающая пара денег по договору
    allr = pd.concat([fact, inv], ignore_index=True)
    withc = allr[allr["cid"].notna()]
    imb = withc.groupby("cid", as_index=False)[["b0", "b1"]].sum()
    t7 = (withc[withc["code"].str.startswith("7") & ~withc["code"].str.startswith("73")]
          .assign(a=lambda x: x["b1"].abs()).sort_values("a")
          .drop_duplicates("cid", keep="last").set_index("cid")["code"])
    imb["code"] = imb["cid"].map(info["st_code"]).fillna(imb["cid"].map(t7)).fillna("7")
    imb.loc[imb["cid"].map(info["mp"]).fillna(False).astype(bool), "code"] = WB_BAL
    pair = imb.assign(b0=-imb["b0"], b1=-imb["b1"], chapter="пара к деньгам", src="pair", sub=None)
    allr = pd.concat([allr, pair], ignore_index=True)
    allr["code"] = allr["code"].astype(str)

    c = allr["code"]
    sec = pd.Series(None, index=allr.index, dtype=object)
    for pfx, nm in CASH_LINES:
        sec[c.str.startswith(pfx)] = "cash:" + nm
    sec[sec.isna() & c.str.startswith("11")] = "cash:Прочие денежные средства"
    sec[c.str.startswith("12")] = "recv"
    sec[c.str.startswith("13")] = "inv"
    sec[c.str.startswith("14")] = "fixed"
    sec[c.str.startswith("2")] = "liab"
    sec[c.str.startswith("3")] = "cap"
    sec[c.str[:1].isin(["4", "5", "6"])] = "pl"
    sec[c.str.startswith("73")] = "vat"
    sec[c.str.startswith("7") & ~c.str.startswith("73")] = "st"
    allr["sec"] = sec.fillna("other")

    rows = []

    def add(level, cd, nm, v0, v1, kind="row"):
        if isinstance(cd, float) and cd == cd:
            cd = int(cd)
        rows.append((level, "" if cd is None or (cd != cd) else str(cd), nm, float(v0),
                     float(v1), kind))

    def tot(df, sign=1):
        return float((df["b0"] * sign).sum()), float((df["b1"] * sign).sum())

    def by_contract(df, level, sign=1, only=None):
        """Строки по договорам: only='pos' — только положительные, 'neg' — отрицательные."""
        g = df.groupby("cid", dropna=False)[["b0", "b1"]].sum().reset_index()
        g["b0"], g["b1"] = g["b0"] * sign, g["b1"] * sign
        if only:
            g = g[g["b1"] > TOL] if only == "pos" else g[g["b1"] < -TOL]
        g = g[(g["b0"].abs() >= TOL) | (g["b1"].abs() >= TOL)]
        g["lbl"] = g["cid"].map(lambda x: label(x) if pd.notna(x) else "без договора")
        for r in g.sort_values("lbl", key=lambda s: s.str.upper()).itertuples(index=False):
            add(level, r.cid if pd.notna(r.cid) else "", r.lbl, r.b0, r.b1, "det")

    # ---------------------------------------------------------------- расчёты 7…
    st = allr[allr["sec"] == "st"].copy()
    st["grp"] = st["code"].str[:2] + "0000"
    # сторона — по чистому остатку договора на участке; счёт — счёт расчётов договора
    st_c = st.groupby(["grp", "cid"], dropna=False, as_index=False)[["b0", "b1"]].sum()
    main_code = (st.assign(a=st["b1"].abs()).sort_values("a")
                 .drop_duplicates(["grp", "cid"], keep="last")[["grp", "cid", "code"]])
    st_c = st_c.merge(main_code, on=["grp", "cid"], how="left")
    st_c["code"] = st_c["cid"].map(info["st_code"]).where(
        lambda x: x.astype(str).str[:2] == st_c["grp"].str[:2]).fillna(st_c["code"])
    st_c["side"] = st_c["b1"].map(lambda v: "a" if v > TOL else ("l" if v < -TOL else "z"))

    # ---------------------------------------------------------------- запасы
    i0 = float(inv_gl["i0"].iloc[0] or 0) if len(inv_gl) else 0.0
    i1 = float(inv_gl["i1"].iloc[0] or 0) if len(inv_gl) else 0.0
    cg0, cg1 = tot(allr[allr["src"] == "cogs"])
    paid = (allr[(allr["sec"] == "inv") & allr["code"].str.startswith("130001")
                 & (allr["src"] != "cogs")])
    paid_c = paid.groupby("cid", dropna=False, as_index=False)[["b0", "b1"]].sum()
    upd = upd.rename(columns={"u0": "b0", "u1": "b1"})
    upd[["b0", "b1"]] = upd[["b0", "b1"]].fillna(0.0).astype(float)
    pre = (paid_c.set_index("cid")[["b0", "b1"]]
           .sub(upd.set_index("cid")[["b0", "b1"]], fill_value=0).reset_index())
    pre_a, pre_l = pre[pre["b1"] > TOL], pre[pre["b1"] < -TOL]
    u0, u1 = float(upd["b0"].sum()), float(upd["b1"].sum())
    adj0, adj1 = u0 - i0, u1 - i1                  # УПД вне товарного учёта
    other_inv = allr[(allr["sec"] == "inv") & ~allr["code"].str.startswith("130001")]
    stock0, stock1 = i0 + cg0, i1 + cg1

    # ---------------------------------------------------------------- АКТИВЫ
    cash = allr[allr["sec"].astype(str).str.startswith("cash:")]
    recv = allr[allr["sec"] == "recv"]
    vat = allr[allr["sec"] == "vat"]
    fixed = allr[allr["sec"] == "fixed"]
    other = allr[allr["sec"] == "other"]
    v0, v1 = tot(vat)
    sta = st_c[st_c["side"] == "a"]
    stl = st_c[st_c["side"] == "l"]
    sum_side = lambda df: (float(df["b0"].sum()), float(df["b1"].sum()))
    pa0, pa1 = sum_side(pre_a)
    pl0_, pl1_ = sum_side(pre_l)
    oi0, oi1 = tot(other_inv)
    inv0 = stock0 + pa0 + adj0 + oi0
    inv1 = stock1 + pa1 + adj1 + oi1

    A = [tot(cash), tot(recv), sum_side(sta), (max(v0, 0), max(v1, 0)), (inv0, inv1),
         tot(fixed), tot(other)]
    A0, A1 = sum(a[0] for a in A), sum(a[1] for a in A)
    add(0, "", "АКТИВЫ", A0, A1, "band")

    add(1, "110000", "Денежные средства", *tot(cash), "sec")
    for pfx, nm in list(CASH_LINES) + [("11", "Прочие денежные средства")]:
        part = cash[cash["sec"] == "cash:" + nm]
        if part.empty:
            continue
        add(2, pfx.ljust(6, "0"), nm, *tot(part), "line")
        for cd, g in part.groupby("code"):
            if max(abs(g["b0"].sum()), abs(g["b1"].sum())) < TOL:
                continue
            add(3, cd, acc_name(cd), *tot(g), "acc")
            if pfx == "113":
                by_contract(g, 4)
        if pfx == "114":
            lk = [float(wb_lk[k]["v"].iloc[0]) if len(wb_lk[k]) else float("nan")
                  for k in ("b0", "b1")]
            add(3, "", "справочно: баланс в личном кабинете WB на дату (как в манпаке)",
                lk[0], lk[1], "info")

    add(1, "120000", "Дебиторская задолженность и авансы выданные",
        tot(recv)[0] + sum_side(sta)[0], tot(recv)[1] + sum_side(sta)[1], "sec")
    for cd, g in recv.groupby("code"):
        add(2, cd, acc_name(cd), *tot(g), "line")
        by_contract(g, 3)
    for grp, g in sta.groupby("grp"):
        add(2, grp, acc_name(grp), *sum_side(g), "line")
        if grp == "750000":
            _tax_detail(allr, g, add, item_name, 3)
        else:
            by_contract(g, 3)

    if v0 > 0 or v1 > 0:
        add(1, "730000", "НДС к возмещению", max(v0, 0), max(v1, 0), "sec")
        for cd, g in vat.groupby("code"):
            add(2, cd, acc_name(cd), *tot(g), "acc")

    add(1, "130000", "Запасы", inv0, inv1, "sec")
    add(2, "130001", "Товар на складах и в продаже (по УПД, по себестоимости FIFO)",
        stock0, stock1, "line")
    add(3, "", "поступило по УПД (товарный учёт)", i0, i1, "acc")
    add(3, "510000", "минус списано в себестоимость проданного", cg0, cg1, "acc")
    add(2, "", "Авансы поставщикам товара: оплачено, УПД ещё нет", pa0, pa1, "line")
    for r in pre_a.itertuples(index=False):
        add(3, r.cid if pd.notna(r.cid) else "",
            label(r.cid) if pd.notna(r.cid) else "без договора", r.b0, r.b1, "det")
    if abs(adj0) >= TOL or abs(adj1) >= TOL:
        add(2, "", "УПД вне товарного учёта (строки без карточки товара)", adj0, adj1, "line")
    for cd, g in other_inv.groupby("code"):
        add(2, cd, acc_name(cd), *tot(g), "line")
        by_contract(g, 3)

    add(1, "140000", "Внеоборотные активы", *tot(fixed), "sec")
    for cd, g in fixed.groupby("code"):
        add(2, cd, acc_name(cd), *tot(g), "line")
        by_contract(g, 3)
    if max(abs(tot(other)[0]), abs(tot(other)[1])) >= TOL:
        add(1, "", "Прочие счета", *tot(other), "sec")

    # ---------------------------------------------------------------- ПАССИВЫ
    liab = allr[allr["sec"] == "liab"]
    cap = allr[allr["sec"] == "cap"]
    plr = allr[allr["sec"] == "pl"]
    sl = stl.assign(b0=-stl["b0"], b1=-stl["b1"])
    ln = sl[sl["grp"] == "770000"]
    ot = sl[sl["grp"] != "770000"]
    vl0, vl1 = max(-v0, 0), max(-v1, 0)
    gl0, gl1 = -pl0_, -pl1_                          # долг поставщикам товара
    L0 = sum_side(sl)[0] + gl0 + vl0 - tot(liab)[0]
    L1 = sum_side(sl)[1] + gl1 + vl1 - tot(liab)[1]
    p0, p1 = tot(plr, -1)
    E0, E1 = -tot(cap)[0] + p0, -tot(cap)[1] + p1
    add(0, "", "ПАССИВЫ", L0 + E0, L1 + E1, "band")

    add(1, "770000", "Кредиты и займы полученные (тело и проценты)", *sum_side(ln), "sec")
    for r_cd, part in ln.groupby("code"):
        add(2, r_cd, acc_name(r_cd), *sum_side(part), "line")
        by_contract(part, 3)

    add(1, "720000", "Кредиторская задолженность и авансы полученные",
        sum_side(ot)[0] + gl0, sum_side(ot)[1] + gl1, "sec")
    if gl0 or gl1:
        add(2, "130001", "Поставщики товара: УПД получен, не оплачен", gl0, gl1, "line")
        for r in pre_l.itertuples(index=False):
            add(3, r.cid if pd.notna(r.cid) else "",
                label(r.cid) if pd.notna(r.cid) else "без договора", -r.b0, -r.b1, "det")
    for grp, g in ot.groupby("grp"):
        add(2, grp, acc_name(grp), *sum_side(g), "line")
        if grp == "750000":
            _tax_detail(allr, g, add, item_name, 3, sign=-1)
        else:
            by_contract(g, 3)

    if vl0 or vl1:
        add(1, "730000", "НДС к уплате", vl0, vl1, "sec")
        for cd, g in vat.groupby("code"):
            add(2, cd, acc_name(cd), *tot(g, -1), "acc")

    if not liab.empty:
        add(1, "200000", "Прочие обязательства (счета 2…)", *tot(liab, -1), "sec")
        for cd, g in liab.groupby("code"):
            add(2, cd, acc_name(cd), *tot(g, -1), "line")

    add(1, "300000", "Капитал", E0, E1, "sec")
    for cd, g in cap.groupby("code"):
        add(2, cd, acc_name(cd), *tot(g, -1), "line")
    add(2, "", f"Финансовый результат прошлых лет (до {d0:%d.%m.%Y})", p0, p0, "line")
    add(2, "", f"Финансовый результат {report_date.year} года", 0.0, p1 - p0, "line")
    add(0, "", "КОНТРОЛЬ: активы − пассивы (должно быть 0)", A0 - L0 - E0, A1 - L1 - E1, "check")

    bal = pd.DataFrame(rows, columns=["level", "code", "name", "b0", "b1", "kind"])
    bal["chg"] = bal["b1"] - bal["b0"]

    noc = allr[allr["cid"].isna() & (allr["src"] == "учёт")]
    ctl = noc.groupby(["chapter", "code"], as_index=False)[["b0", "b1"]].sum()
    ctl = ctl[(ctl["b0"].abs() >= TOL) | (ctl["b1"].abs() >= TOL)]
    ctl["acc"] = ctl["code"].map(acc_name)
    ctl = ctl.sort_values(["chapter", "code"])
    return {"bal": bal, "ctl": ctl, "d0": d0, "dropped": dropped}


def _tax_detail(allr, part, add, item_name, level, sign=1):
    """Налоги (750000): оплачено по подстатьям CF, начислено по счетам, остальное."""
    cids = set(part["cid"].dropna())
    rows = allr[allr["cid"].isin(cids)]
    shown = [0.0, 0.0]
    cash = rows[rows["code"].str.startswith("11")]
    for r in cash.groupby("sub", dropna=False)[["b0", "b1"]].sum().reset_index().itertuples(index=False):
        if max(abs(r.b0), abs(r.b1)) < TOL:
            continue
        nm = item_name.get(r.sub, "без подстатьи") if pd.notna(r.sub) else "без подстатьи"
        v0, v1 = -r.b0 * sign, -r.b1 * sign
        add(level, "", f"оплачено (−) / возвращено (+) по CF: {nm}", v0, v1, "det")
        shown[0] += v0
        shown[1] += v1
    acc = rows[rows["code"].str.startswith("75") & (rows["src"] == "учёт")]
    for cd, g in acc.groupby("code"):
        v0, v1 = g["b0"].sum() * sign, g["b1"].sum() * sign
        if max(abs(v0), abs(v1)) >= TOL:
            add(level, cd, f"начислено на {cd}", v0, v1, "det")
            shown[0] += v0
            shown[1] += v1
    t0, t1 = float(part["b0"].sum()) * sign, float(part["b1"].sum()) * sign
    if max(abs(t0 - shown[0]), abs(t1 - shown[1])) >= TOL:
        add(level, "", "прочее: проводки без пары по этим договорам", t0 - shown[0],
            t1 - shown[1], "det")


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
    M = mp.FMT_MONEY
    fmt = {
        "title": F(font_size=14, bold=True), "sub": F(font_color="#" + mp.TEXT_2),
        "hdr": F(bold=True, font_color="#FFFFFF", bg_color="#" + mp.NAVY, text_wrap=True,
                 align="center", valign="vcenter", border=1, border_color="#" + mp.NAVY_2),
        "text": F(**line), "wrap": F(**line, text_wrap=True), "money": F(**line, num_format=M),
        "lbl": F(bold=True, font_color="#" + mp.NAVY_3, **line),
    }
    styles = {
        "band": dict(bold=True, font_color="#FFFFFF", bg_color="#" + mp.NAVY_3),
        "sec": dict(bold=True, bg_color="#E8F0EC", **line),
        "line": dict(bold=True, **line),
        "acc": dict(**line),
        "det": dict(font_color="#" + mp.TEXT_2, **line),
        "info": dict(italic=True, font_color="#" + mp.MUTED, **line),
        "check": dict(bold=True, bg_color="#FFF3C4", top=1, bottom=1),
    }
    sf = {k: (F(**v), F(**v, num_format=M), F(**{**v, "font_color": "#" + mp.MUTED}))
          for k, v in styles.items()}
    sub = ("По остаткам учёта (gl.fact), собрано по участкам · «+» слева — расшифровка · "
           "сформировано " + pd.Timestamp.now().strftime("%d.%m.%Y %H:%M"))
    m = lambda v: 0.0 if (v != v) or abs(float(v or 0)) < 0.5 else float(v)

    ws = wb.add_worksheet("Баланс")
    ws.outline_settings(True, False, True, False)      # «+» над расшифровкой
    ws.set_column(0, 0, 9)
    ws.set_column(1, 1, 70)
    ws.set_column(2, 4, 17)
    ws.write(0, 0, "Баланс (проверка)", fmt["title"])
    ws.write(1, 0, sub, fmt["sub"])
    for j, h in enumerate(("КОД / ID", "СТАТЬЯ", h0.upper(), h1.upper(), "ИЗМЕНЕНИЕ, ₽")):
        ws.write(3, j, h, fmt["hdr"])
    ws.set_row(3, 30)
    for i, r in enumerate(res["bal"].itertuples(index=False), start=4):
        tf, mf, cf_ = sf[r.kind]
        ws.write(i, 0, r.code, cf_)
        ws.write(i, 1, ("   " * max(r.level - 1, 0)) + r.name, tf)
        for j, v in ((2, r.b0), (3, r.b1), (4, r.chg)):
            if r.kind == "info" and v != v:
                ws.write_blank(i, j, None, tf)
            else:
                ws.write_number(i, j, m(v), mf)
        if r.level >= 2:                                 # раздел открыт, глубже — свёрнуто
            ws.set_row(i, None, None, {"level": r.level - 1, "hidden": r.level >= 3})
    ws.freeze_panes(4, 2)

    ws = wb.add_worksheet("Контроль")
    ws.write(0, 0, "Проводки без договора — пара к ним не достраивается; их сумма = небаланс",
             fmt["title"])
    ws.write(1, 0, sub, fmt["sub"])
    for j, (h, w) in enumerate((("Раздел учёта", 24), ("Счёт", 44), (h0, 16), (h1, 16))):
        ws.write(3, j, h, fmt["hdr"])
        ws.set_column(j, j, w)
    for i, r in enumerate(res["ctl"].itertuples(index=False), start=4):
        ws.write(i, 0, r.chapter, fmt["text"])
        ws.write(i, 1, r.acc, fmt["text"])
        ws.write_number(i, 2, m(r.b0), fmt["money"])
        ws.write_number(i, 3, m(r.b1), fmt["money"])

    ws = wb.add_worksheet("Как читать")
    ws.set_column(0, 0, 22)
    ws.set_column(1, 1, 110)
    ws.write(0, 0, "Как читать", fmt["title"])
    notes = [
        ("Расшифровка", "«+» слева над строкой раскрывает её: раздел → счёт → договор "
                        "(контрагент · договор · id). Сначала видны разделы и строки."),
        ("Деньги", "Банковские счета 111…, депозиты 113… (по договорам), баланс WB, деньги в пути."),
        ("Баланс WB", "114001: начислено к перечислению минус выведено на р/с (оплаты по договорам "
                      "WB уменьшают баланс). Рядом — справочно баланс из личного кабинета WB, как "
                      "в манпаке: расхождение — повод сверить."),
        ("Расчёты", "По каждому договору: начисления плюс оплаты. Плюс — нам должны / аванс "
                    "выдан (актив), минус — мы должны / аванс получен (пассив)."),
        ("Налоги 750000", "Расчёты с ИФНС: что оплачено по подстатьям Cash Flow (НДС, НДФЛ, "
                          "взносы, прибыль…) и что начислено на 750…. НДС считается отдельно "
                          "(730…): оплаченный НДС сидит здесь, начисленный — в «НДС к уплате»."),
        ("Запасы", "Товар на складах = поступило по УПД (товарный учёт) − себестоимость проданного. "
                   "Авансы поставщикам товара = оплачено поставщику (на 130001) − УПД по договору: "
                   "оплачено, а УПД нет — это и закупки на баланс без УПД. Если УПД больше оплат "
                   "— долг поставщику, в пассивах."),
        ("Капитал", "Взносы и накопленный результат P&L: прошлых лет и текущего года."),
        ("Контроль", "Активы − пассивы. Не ноль — проводки без договора, лист «Контроль»."),
    ]
    for i, (a, b) in enumerate(notes, start=2):
        ws.write(i, 0, a, fmt["lbl"])
        ws.write(i, 1, b, fmt["wrap"])
        ws.set_row(i, 36)
    wb.close()
    return buf.getvalue()


def build_balance_workbook(report_date: date) -> tuple[bytes, str]:
    from conns import get_duckdb_conn_with_opt
    with get_duckdb_conn_with_opt(ro=True) as con:
        res = build(report_date, con)
    return to_excel(res, report_date), f"Баланс (проверка) {report_date:%Y%m%d}.xlsx"
