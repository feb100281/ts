# gear/app/manpack/vat_contracts.py
"""Сверка НДС по договорам: оборот Cash Flow → НДС, который должен быть по режиму
и ставке условий договора, против НДС, который есть у нас (проводки НДС и УПД).

Знак как на листе «НДС по операциям»: к вычету — плюс, начисленный — минус.
Оплата поставщику (минус в CF) даёт ожидаемый вычет (плюс), поступление
(плюс в CF) — начисленный НДС (минус).
"""
from __future__ import annotations

import io
import json
from datetime import date

import pandas as pd

TOL_RUB = 1000.0        # расхождение меньше — не считаем
TOL_SHARE = 0.03        # и меньше 3% ожидаемого
STD_RATE = {2026: 22.0}  # ставка «если бы облагалось», по году; иначе 20
WB_NAMES = ("ВАЙЛДБЕРРИЗ", "WILDBERRIES", "РВБ")

CF_SQL = """
SELECT date_from::DATE AS d, CAST(amount AS DOUBLE) AS amount,
       COALESCE(item, '') AS item, COALESCE(subitem, '') AS subitem,
       COALESCE(NULLIF(TRIM(cp_name), ''), 'Без контрагента') AS cp_name,
       COALESCE(NULLIF(TRIM(contract_name), ''), '') AS contract_name,
       TRY_CAST(contract_id AS BIGINT) AS cid
FROM pg.cf_to_csv
WHERE date_from::DATE <= ? AND COALESCE(amount, 0) <> 0
"""
COND_SQL = """
SELECT c.contract_id AS cid, c.date_start, c.date_finish,
       COALESCE(c.vat_mode, 'unknown') AS vat_mode,
       CAST(c.vat_json AS VARCHAR) AS vat_json,
       am.name AS method
FROM pg.public.contracts_conditions c
LEFT JOIN pg.public.contracts_accountingmethod am ON am.id = c.accounting_method_id
"""
CONTRACT_SQL = """
SELECT k.id AS cid,
       COALESCE(ct.title, 'Договор') || ' № ' || COALESCE(k.number, 'б/н') || ' от '
           || COALESCE(strftime(k.date, '%d.%m.%Y'), 'б/д') AS contract,
       COALESCE(NULLIF(TRIM(cp.name), ''), 'Без контрагента') AS cp
FROM pg.public.contracts_contracts k
LEFT JOIN pg.public.contracts_contractstitle ct ON ct.id = k.title_id
LEFT JOIN pg.public.counterparties_counterparty cp ON cp.id = k.cp_id
"""
GL_SQL = """
SELECT COALESCE(p.contract_id, v.contract_id) AS cid, YEAR(v.date_from) AS y,
       SUM(v.dt - v.cr) / 100.0 AS vat_gl
FROM pg.gl.fact v
LEFT JOIN pg.gl.accural_distribution p ON p.id = v.pid
WHERE v.chapter = 'VAT_ACCURALS' AND v.date_from <= ?
GROUP BY 1, 2
"""
UPD_SQL = """
SELECT d.contract_id AS cid, YEAR(d.date) AS y,
       SUM(COALESCE(l.upd_vat_amount,
                    l.upd_amount_vatless * COALESCE(l.upd_vat_rate, 0) / 100)) AS vat_upd
FROM pg.public.upd_income_lines l
JOIN pg.public.cards_upddocument d ON d.id = l.upd_document_id
WHERE d.date <= ? AND COALESCE(l.currency_code, 'RUB') = 'RUB'
GROUP BY 1, 2
"""

MODE_NAME = {"included": "НДС включён", "excluded": "НДС сверху", "exempt": "Без НДС",
             "unknown": "Не задан", "vat_only": "Только НДС", "none": "Нет условий"}


def _rate(vat_json: str | None, d: date) -> float | None:
    """Ставка из vat_json условий на дату: последняя запись с датой ≤ d."""
    try:
        m = json.loads(vat_json) if vat_json else {}
    except (TypeError, ValueError):
        return None
    best = None
    for k, v in (m or {}).items():
        try:
            kd = date.fromisoformat(str(k)[:10])
        except ValueError:
            continue
        if kd <= d and (best is None or kd > best[0]):
            best = (kd, float(v))
    return best[1] if best else None


def _std(y: int) -> float:
    return STD_RATE.get(int(y), 22.0 if int(y) > 2026 else 20.0)


def _expected(cf: pd.DataFrame, cond: pd.DataFrame) -> pd.DataFrame:
    """К строкам CF — режим и ставка действующих условий, ожидаемый НДС."""
    cf = cf.copy()
    cf["vat_mode"], cf["rate"], cf["method"] = "none", None, None
    by_c = {c: g.sort_values("date_start", na_position="first")
            for c, g in cond.groupby("cid")}
    modes, rates, methods = [], [], []
    for cid, d in zip(cf["cid"], cf["d"]):
        g = by_c.get(cid)
        if g is None:
            modes.append("none"), rates.append(None), methods.append(None)
            continue
        ok = g[(g["date_start"].isna() | (g["date_start"] <= d))
               & (g["date_finish"].isna() | (g["date_finish"] > d))]
        r = (ok if len(ok) else g).iloc[-1]
        modes.append(r["vat_mode"]), methods.append(r["method"])
        rates.append(_rate(r["vat_json"], d.date()))
    cf["vat_mode"], cf["rate"], cf["method"] = modes, rates, methods
    r = pd.to_numeric(cf["rate"], errors="coerce")
    a = cf["amount"]
    cf["exp"] = 0.0
    m = cf["vat_mode"].isin(["included", "excluded"]) & r.notna()
    cf.loc[m, "exp"] = -a[m] * r[m] / (100 + r[m])
    m = cf["vat_mode"].eq("vat_only")
    cf.loc[m, "exp"] = -a[m]
    std = cf["d"].map(lambda x: _std(x.year))
    cf["potential"] = (-a * std / (100 + std)).where(cf["vat_mode"].isin(["unknown", "none"]), 0.0)
    return cf


def _flag(r) -> str:
    if r["wb"]:
        return "Маркетплейс: НДС по отчёту WB, сверка на листе НДС"
    exp, act, diff = r["exp"], r["actual"], r["diff"]
    big = abs(diff) >= max(TOL_RUB, TOL_SHARE * abs(exp))
    if r["vat_mode"] in ("unknown", "none"):
        if abs(act) >= TOL_RUB:
            return "НДС в учёте есть, а режим НДС в договоре не задан"
        if abs(r["potential"]) >= TOL_RUB:
            return ("Нет договора" if pd.isna(r["cid"]) else
                    "Нет условий договора" if r["vat_mode"] == "none" else "Режим НДС не задан")
        return "OK"
    if not big:
        return "OK"
    if abs(exp) >= TOL_RUB and abs(act) < TOL_RUB:
        return "НДС по договору должен быть, в учёте нет"
    if abs(exp) < TOL_RUB and abs(act) >= TOL_RUB:
        return "По договору без НДС, а в учёте НДС есть"
    if exp and act and (exp > 0) != (act > 0):
        return "Знак НДС в учёте не совпадает с движением денег"
    return "Расхождение суммы"


def build(report_date: date, con) -> dict[str, pd.DataFrame]:
    cf = con.execute(CF_SQL, [report_date]).df()
    cond = con.execute(COND_SQL).df()
    ctr = con.execute(CONTRACT_SQL).df()
    gl = con.execute(GL_SQL, [report_date]).df()
    upd = con.execute(UPD_SQL, [report_date]).df()

    cf["d"] = pd.to_datetime(cf["d"])
    for c in ("date_start", "date_finish"):
        cond[c] = pd.to_datetime(cond[c])
    cond["cid"] = cond["cid"].astype("Int64")
    cf["cid"] = cf["cid"].astype("Int64")
    cf = _expected(cf, cond)
    cf["y"] = [d.year for d in cf["d"]]
    # без договора — по контрагенту
    cf["key"] = cf["cid"].astype(str).where(cf["cid"].notna(), "cp:" + cf["cp_name"])

    def agg(df, keys):
        g = df.groupby(keys, dropna=False)
        out = g.agg(paid=("amount", lambda s: abs(s[s < 0].sum())),
                    got=("amount", lambda s: s[s > 0].sum()),
                    net=("amount", "sum"), exp=("exp", "sum"), potential=("potential", "sum"),
                    cid=("cid", "first"), cp_cf=("cp_name", "first"),
                    contract_cf=("contract_name", "first"),
                    vat_mode=("vat_mode", "last"), rate=("rate", "last"),
                    method=("method", "last")).reset_index()
        top = (df.assign(a=df["amount"].abs()).groupby(keys + ["item"], dropna=False)["a"].sum()
               .reset_index().sort_values("a").drop_duplicates(keys, keep="last")
               .set_index(keys)["item"])
        out["item"] = out.set_index(keys).index.map(top)
        return out

    acc = pd.concat([gl.rename(columns={"vat_gl": "v"}).assign(src="gl"),
                     upd.rename(columns={"vat_upd": "v"}).assign(src="upd")])
    acc["cid"] = acc["cid"].astype("Int64")
    acc["key"] = acc["cid"].astype(str).where(acc["cid"].notna(), "cp:Без договора (учёт)")
    acc_y = acc.pivot_table(index=["key", "y"], columns="src", values="v", aggfunc="sum").reset_index()
    acc_t = acc.pivot_table(index="key", columns="src", values="v", aggfunc="sum").reset_index()
    for t in (acc_y, acc_t):
        for c in ("gl", "upd"):
            if c not in t:
                t[c] = 0.0

    info = ctr.assign(key=ctr["cid"].astype(str)).set_index("key")

    def finish(df, accd, keys):
        df = df.merge(accd, on=keys, how="outer")
        for c in ("paid", "got", "net", "exp", "potential", "gl", "upd"):
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)
        df["vat_mode"] = df["vat_mode"].fillna("none")
        idx = df["key"]
        df["cid"] = pd.to_numeric(idx.where(~idx.str.startswith("cp:")),
                                  errors="coerce").astype("Int64")
        df["cp"] = idx.map(info["cp"]).fillna(df["cp_cf"])
        df["cp"] = df["cp"].fillna(idx.where(idx.str.startswith("cp:"))
                                   .str.replace("cp:", "", regex=False)).fillna(
            "Договора нет в справочнике")
        df["contract"] = idx.map(info["contract"]).fillna(df["contract_cf"]).fillna("")
        df.loc[df["key"].str.startswith("cp:"), "contract"] = "без договора"
        df["actual"] = df["gl"] + df["upd"]
        df["diff"] = df["actual"] - df["exp"]
        base = df["net"].abs() - df["actual"].abs()
        df["eff_rate"] = (df["actual"].abs() / base.where(base > 0) * 100).where(
            df["actual"].abs() >= 1)
        up = df["cp"].astype(str).str.upper()
        df["wb"] = up.apply(lambda s: any(n in s for n in WB_NAMES))
        df["flag"] = df.apply(_flag, axis=1)
        df.loc[df["wb"], "potential"] = 0.0
        df["mode"] = df["vat_mode"].map(MODE_NAME).fillna(df["vat_mode"])
        df["weight"] = pd.concat([df["diff"].abs(), df["potential"].abs()], axis=1).max(axis=1)
        df.loc[df["wb"], "weight"] = 0
        return df

    tot = finish(agg(cf, ["key"]), acc_t, ["key"])
    tot = tot.sort_values(["weight"], ascending=False)
    yr = finish(agg(cf, ["key", "y"]), acc_y, ["key", "y"])
    yr = yr.sort_values(["cp", "contract", "y"])
    bad = set(tot.loc[~tot["flag"].eq("OK") & ~tot["wb"], "key"])
    ops = cf[cf["key"].isin(bad)].copy()
    ops["cp"] = ops["key"].map(tot.set_index("key")["cp"])
    ops["contract"] = ops["key"].map(tot.set_index("key")["contract"])
    ops["mode"] = ops["vat_mode"].map(MODE_NAME)
    ops = ops.sort_values(["cp", "contract", "d"])
    return {"tot": tot, "yr": yr, "ops": ops}


# ---------------------------------------------------------------- Excel
TOT_COLS = [
    ("flag", "Флаг", "wrap", 34), ("cp", "Контрагент", "text", 30),
    ("contract", "Договор", "wrap", 32), ("cid", "ID договора", "id", 9),
    ("method", "Метод учёта", "text", 16), ("mode", "Режим НДС", "text", 13),
    ("rate", "Ставка по договору, %", "dec", 9), ("item", "Основная статья CF", "text", 26),
    ("paid", "Оплачено, ₽", "money", 14), ("got", "Получено, ₽", "money", 14),
    ("exp", "НДС ожидаемый по CF и режиму, ₽", "money", 15),
    ("gl", "НДС в проводках, ₽", "money", 14), ("upd", "НДС по УПД, ₽", "money", 13),
    ("actual", "НДС у нас итого, ₽", "money", 14),
    ("diff", "Разница: у нас − ожидаемый, ₽", "money", 15),
    ("eff_rate", "Ставка по факту, %", "dec", 9),
    ("potential", "НДС при стандартной ставке (режим не задан), ₽", "money", 16),
]
YR_COLS = [("cp", "Контрагент", "text", 30), ("contract", "Договор", "wrap", 32),
           ("cid", "ID договора", "id", 9), ("y", "Год", "id", 7), ("mode", "Режим НДС", "text", 13),
           ("paid", "Оплачено, ₽", "money", 14), ("got", "Получено, ₽", "money", 14),
           ("exp", "НДС ожидаемый, ₽", "money", 14), ("actual", "НДС у нас, ₽", "money", 14),
           ("diff", "Разница, ₽", "money", 14), ("flag", "Флаг", "wrap", 34)]
OPS_COLS = [("cp", "Контрагент", "text", 30), ("contract", "Договор", "wrap", 32),
            ("d", "Дата", "date", 11), ("item", "Статья CF", "text", 26),
            ("subitem", "Подстатья CF", "text", 26), ("amount", "Сумма CF, ₽", "money", 14),
            ("mode", "Режим НДС", "text", 13), ("rate", "Ставка, %", "dec", 8),
            ("exp", "НДС ожидаемый, ₽", "money", 14)]
NOTES = [
    ("Что это", "По каждому договору: сколько денег прошло по Cash Flow, какой НДС должен "
                "быть при режиме и ставке из условий договора, и какой НДС есть у нас — "
                "проводки НДС (начисления) и УПД поставщиков товаров."),
    ("Знаки", "Как на листе «НДС по операциям»: к вычету — плюс, начисленный — минус. "
              "Оплата поставщику даёт ожидаемый вычет, поступление — начисленный НДС."),
    ("Ожидаемый НДС", "«НДС включён» и «НДС сверху» — сумма платежа × ставка / (100 + "
                      "ставка): в платеже уже есть НДС. «Только НДС» — вся сумма. «Без НДС» и "
                      "«Не задан» — ноль. Ставка — из условий договора на дату платежа."),
    ("Флаги", "«НДС по договору должен быть, в учёте нет» — платим с НДС, а вычета нет. "
              "«По договору без НДС, а в учёте НДС есть» — режим договора не совпадает с учётом. "
              "«Режим НДС не задан» / «Нет условий» / «Нет договора» — оборот есть, а правила НДС "
              "нет; сколько мог бы быть НДС — в колонке «при стандартной ставке». "
              "Расхождение меньше 1 000 ₽ или 3% не считается."),
    ("Порядок", "Сверху — договоры с наибольшей разницей (для договоров без режима — с "
                "наибольшим возможным НДС). Обычно первые 10–20 строк объясняют основную часть."),
    ("Ограничения", "Деньги и начисления расходятся по времени: аванс оплачен, а акт ещё нет, "
                    "или наоборот. Поэтому сверка — за весь период до отчётной даты; по годам "
                    "разница может быть из-за переходящих сумм. УПД — только в рублях. "
                    "НДС с продаж и услуг WB считается по отчёту WB, здесь не сверяется."),
]


def to_excel(res: dict, report_date: date) -> bytes:
    from gear.management.commands import mp
    import xlsxwriter

    buf = io.BytesIO()
    wb = xlsxwriter.Workbook(buf, {"nan_inf_to_errors": True})
    base = {"font_name": mp.FONT, "font_size": 9, "font_color": "#" + mp.TEXT, "valign": "vcenter"}
    line = {"bottom": 1, "bottom_color": "#" + mp.LINE}
    F = lambda **k: wb.add_format({**base, **k})
    fmt = {
        "title": F(font_size=14, bold=True), "sub": F(font_color="#" + mp.TEXT_2),
        "hdr": F(bold=True, font_color="#FFFFFF", bg_color="#" + mp.NAVY, text_wrap=True,
                 align="center", border=1, border_color="#" + mp.NAVY_2),
        "text": F(**line), "wrap": F(**line, text_wrap=True),
        "id": F(**line, num_format="0", align="center"),
        "date": F(**line, num_format="dd.mm.yyyy", align="center"),
        "money": F(**line, num_format=mp.FMT_MONEY), "dec": F(**line, num_format="0.0"),
        "lbl": F(bold=True, font_color="#" + mp.NAVY_3, valign="top", **line),
        "flag_bad": F(**line, text_wrap=True, bg_color="#F8D7D3"),
        "flag_warn": F(**line, text_wrap=True, bg_color="#FCEBCF"),
        "flag_ok": F(**line, text_wrap=True, font_color="#" + mp.MUTED),
        "tot": F(bold=True, top=1, bottom=1, num_format=mp.FMT_MONEY),
        "tot_l": F(bold=True, top=1, bottom=1),
    }
    sub = (f"Отчётная дата {report_date:%d.%m.%Y} · весь период до неё · знак: к вычету +, "
           "начисленный − · сформировано " + pd.Timestamp.now().strftime("%d.%m.%Y %H:%M"))

    def flag_fmt(v):
        v = str(v)
        if v == "OK" or v.startswith("Маркетплейс"):
            return fmt["flag_ok"]
        if v.startswith(("Режим", "Нет")):
            return fmt["flag_warn"]
        return fmt["flag_bad"]

    def sheet(name, title, cols, df, total=False):
        ws = wb.add_worksheet(name)
        ws.write(0, 0, title, fmt["title"])
        ws.write(1, 0, sub, fmt["sub"])
        r0 = 3
        for j, (_k, h, _t, w) in enumerate(cols):
            ws.write(r0, j, h, fmt["hdr"])
            ws.set_column(j, j, w)
        ws.set_row(r0, 42)
        for i, row in enumerate(df[[c[0] for c in cols]].itertuples(index=False), start=r0 + 1):
            for j, ((k, _h, t, _w), v) in enumerate(zip(cols, row)):
                if v is None or (not isinstance(v, str) and pd.isna(v)):
                    ws.write_blank(i, j, None, fmt["text"])
                elif k == "flag":
                    ws.write(i, j, v, flag_fmt(v))
                elif t in ("money", "dec", "id"):
                    ws.write_number(i, j, float(v), fmt[t])
                elif t == "date":
                    ws.write_datetime(i, j, pd.Timestamp(v).to_pydatetime(), fmt["date"])
                else:
                    ws.write(i, j, str(v), fmt[t])
        last = r0 + len(df)
        if total and len(df):
            ws.write(last + 1, 0, "Итого", fmt["tot_l"])
            for j, (k, _h, t, _w) in enumerate(cols):
                if t == "money":
                    ws.write_number(last + 1, j, float(df[k].sum()), fmt["tot"])
        ws.autofilter(r0, 0, max(last, r0), len(cols) - 1)
        ws.freeze_panes(r0 + 1, 3 if name != "Операции CF" else 2)
        return ws

    tot = res["tot"]
    ws = wb.add_worksheet("Итог")
    ws.set_column(0, 0, 54)
    ws.set_column(1, 3, 18)
    ws.write(0, 0, "Сверка НДС по договорам", fmt["title"])
    ws.write(1, 0, sub, fmt["sub"])
    for j, h in enumerate(("ФЛАГ", "ДОГОВОРОВ", "РАЗНИЦА, ₽", "ВОЗМОЖНЫЙ НДС, ₽")):
        ws.write(3, j, h, fmt["hdr"])
    g = (tot.groupby("flag").agg(n=("key", "size"), diff=("diff", "sum"),
                                 pot=("potential", "sum"), w=("weight", "sum"))
         .sort_values("w", ascending=False))
    r = 4
    for flag, row in g.iterrows():
        ws.write(r, 0, flag, flag_fmt(flag))
        ws.write_number(r, 1, int(row["n"]), fmt["id"])
        ws.write_number(r, 2, float(row["diff"]), fmt["money"])
        ws.write_number(r, 3, float(row["pot"]), fmt["money"])
        r += 1
    r += 1
    ws.write(r, 0, "Разница — НДС у нас минус ожидаемый по Cash Flow. Возможный НДС — "
                   "сколько НДС было бы при стандартной ставке там, где режим НДС не задан.",
             fmt["sub"])

    sheet("По договорам", "НДС по договорам", TOT_COLS, tot, total=True)
    sheet("По годам", "НДС по договорам и годам", YR_COLS, res["yr"])
    sheet("Операции CF", "Операции Cash Flow по договорам с флагом", OPS_COLS, res["ops"])

    ws = wb.add_worksheet("Как читать")
    ws.set_column(0, 0, 18)
    ws.set_column(1, 1, 110)
    ws.write(0, 0, "Как читать", fmt["title"])
    for i, (a, b) in enumerate(NOTES, start=2):
        ws.write(i, 0, a, fmt["lbl"])
        ws.write(i, 1, b, fmt["wrap"])
        ws.set_row(i, 44)
    wb.close()
    return buf.getvalue()


def build_vat_contracts_workbook(report_date: date) -> tuple[bytes, str]:
    from conns import get_duckdb_conn_with_opt
    with get_duckdb_conn_with_opt(ro=True) as con:
        res = build(report_date, con)
    return to_excel(res, report_date), f"Сверка НДС по договорам {report_date:%Y%m%d}.xlsx"
