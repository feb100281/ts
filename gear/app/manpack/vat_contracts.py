# gear/app/manpack/vat_contracts.py
"""Сверка НДС по договорам.

По каждому договору: деньги по Cash Flow → НДС, который должен быть по режиму и
ставке условий договора, против НДС, который есть у нас (проводки НДС и УПД).
Товарные договоры сверяются по УПД, финансирование и налоги не проверяются.

Знак как на листе «НДС по операциям»: к вычету — плюс, начисленный — минус.
"""
from __future__ import annotations

import io
import json
from datetime import date

import pandas as pd

TOL_RUB = 1000.0          # меньше — не замечание
TOL_SHARE = 0.03          # и меньше 3% ожидаемого
WB_NAMES = ("ВАЙЛДБЕРРИЗ", "WILDBERRIES", "РВБ")

def is_marketplace(name) -> bool:
    """Площадка WB (ВАЙЛДБЕРРИЗ ООО, РВБ ООО), но не Вайлдберриз Банк и не МКК ВБ Финанс."""
    import re
    s = str(name or "").upper()
    if any(x in s for x in ("БАНК", "BANK", "ФИНАНС", "МКК")):
        return False
    words = set(re.findall(r"[A-ZА-ЯЁ0-9]+", s))
    return bool(words & {"ВАЙЛДБЕРРИЗ", "WILDBERRIES", "РВБ"})

GOODS_CODE = "121"        # статьи CF «Оплаты товаров для перепродажи»
SKIP_CODES = (("3", "Финансирование: займы, взносы, проценты"),
              ("125", "Налоги и сборы"))

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
           || COALESCE(strftime(k.date, '%d.%m.%Y'), 'б/д') || ' · id ' || CAST(k.id AS VARCHAR)
           AS contract,
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
             "unknown": "Не задан", "vat_only": "Только НДС", "none": "Нет условий",
             "by_payment": "По назначению платежа"}
WITH_VAT = ("included", "excluded", "vat_only")

# флаг: (короткое название, что сделать, порядок в итоге)
FLAGS = {
    "no_vat": ("НДС должен быть, а в учёте нет",
               "Проверить, проведены ли начисления по договору. Если документы без НДС — "
               "сменить режим в условиях на «Без НДС».", 1),
    "vat_exempt": ("По условиям без НДС, а в учёте НДС есть",
                   "Сверить с документами: если НДС есть — поправить режим в условиях "
                   "договора; если нет — убрать НДС из начислений.", 2),
    "diff": ("НДС в учёте не совпадает с оплатами",
             "Больше — проверить задвоенные начисления или неоплаченные акты (долг перед "
             "контрагентом это объясняет). Меньше — не все документы проведены или другая ставка.",
             3),
    "sign": ("Знак НДС не совпадает с движением денег",
             "Проверить направление начислений: вычет вместо начисленного или наоборот.", 4),
    "nodoc": ("НДС по оплатам без УПД",
              "Запросить УПД у поставщика или бухгалтерии и загрузить — НДС перейдёт из "
              "строки 2.0а листа НДС в строку 2.0.", 5),
    "goods_no_upd": ("Товар оплачен, УПД с НДС нет",
                     "Загрузить УПД поставщика. Если поставка без НДС (импорт) — указать в "
                     "условиях договора «Без НДС».", 5),
    "goods_double": ("НДС и по УПД, и в проводках",
                     "Возможен двойной вычет: товарный НДС должен быть только по УПД.", 6),
    "mode_unknown": ("Режим НДС не задан",
                     "Задать режим НДС в условиях договора (если договор без НДС — «Без НДС»).", 7),
    "vat_no_mode": ("НДС в учёте есть, режим не задан",
                    "Задать режим НДС в условиях договора.", 8),
    "no_cond": ("Нет условий договора",
                "Завести условия договора с режимом НДС.", 9),
    "no_contract": ("Платежи без договора",
                    "Привязать платежи к договору в Cash Flow.", 10),
    "wb": ("Маркетплейс WB — сверка на листе НДС", "", 90),
    "goods_ok": ("Товар — НДС по УПД", "", 95),
    "ok": ("OK", "", 99),
}


def _rub(v) -> str:
    v = float(v or 0)
    a = abs(v)
    if a >= 1e6:
        s = f"{a / 1e6:.2f}".replace(".", ",") + " млн ₽"
    elif a >= 1e3:
        s = f"{a / 1e3:.0f} тыс ₽"
    else:
        s = f"{a:.0f} ₽"
    return s


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
    return 22.0 if int(y) >= 2026 else 20.0


def _skip(code: str) -> str | None:
    for pfx, name in SKIP_CODES:
        if code.startswith(pfx):
            return name
    return None


def _expected(cf: pd.DataFrame, cond: pd.DataFrame) -> pd.DataFrame:
    """К строкам CF — режим и ставка действующих условий, ожидаемый НДС."""
    cf = cf.copy()
    by_c = {c: g.sort_values("date_start", na_position="first") for c, g in cond.groupby("cid")}
    modes, rates, methods = [], [], []
    for cid, d in zip(cf["cid"], cf["d"]):
        g = by_c.get(cid) if pd.notna(cid) else None
        if g is None:
            modes.append("none"), rates.append(None), methods.append(None)
            continue
        ok = g[(g["date_start"].isna() | (g["date_start"] <= d))
               & (g["date_finish"].isna() | (g["date_finish"] > d))]
        r = (ok if len(ok) else g).iloc[-1]
        modes.append(r["vat_mode"]), methods.append(r["method"])
        rates.append(_rate(r["vat_json"], d.date()) if r["vat_mode"] in WITH_VAT else None)
    cf["vat_mode"], cf["rate"], cf["method"] = modes, rates, methods
    r = pd.to_numeric(cf["rate"], errors="coerce")
    a = cf["amount"]
    cf["exp"] = 0.0
    m = cf["vat_mode"].isin(["included", "excluded"]) & r.notna()
    cf.loc[m, "exp"] = -a[m] * r[m] / (100 + r[m])
    m = cf["vat_mode"].eq("vat_only")
    cf.loc[m, "exp"] = -a[m]
    std = cf["d"].map(lambda x: _std(x.year))
    cf["potential"] = (-a * std / (100 + std)).where(
        cf["vat_mode"].isin(["unknown", "none"]), 0.0)
    return cf


def _classify(r) -> str:
    if r["wb"]:
        return "wb"
    exp, act, gl, upd = r["exp"], r["actual"], r["gl"], r["upd"]
    if r["nodoc"] >= TOL_RUB:
        return "nodoc"
    if r["goods"]:
        if abs(gl) >= TOL_RUB and abs(upd) >= TOL_RUB:
            return "goods_double"
        if abs(upd) < TOL_RUB and r["vat_mode"] not in ("exempt",) and r["paid"] >= TOL_RUB:
            return "goods_no_upd"
        if abs(upd) >= TOL_RUB or r["vat_mode"] == "exempt":
            return "goods_ok"
    if r["vat_mode"] == "by_payment":          # ставка из назначения каждого платежа
        return "ok"
    if r["vat_mode"] in ("unknown", "none"):
        if abs(act) >= TOL_RUB:
            return "vat_no_mode"
        if abs(r["potential"]) >= TOL_RUB:
            if r["key"].startswith("cp:"):
                return "no_contract"
            return "no_cond" if r["vat_mode"] == "none" else "mode_unknown"
        return "ok"
    if abs(act - exp) < max(TOL_RUB, TOL_SHARE * abs(exp)):
        return "ok"
    if abs(exp) >= TOL_RUB and abs(act) < TOL_RUB:
        return "no_vat"
    if abs(exp) < TOL_RUB and abs(act) >= TOL_RUB:
        return "vat_exempt"
    if (exp > 0) != (act > 0):
        return "sign"
    return "diff"


def _explain(r) -> str:
    f = r["fcode"]
    money = (f"оплачено {_rub(r['paid'])}" if r["paid"] >= 1 else "") + \
            (", " if r["paid"] >= 1 and r["got"] >= 1 else "") + \
            (f"получено {_rub(r['got'])}" if r["got"] >= 1 else "")
    rate = f"{r['rate']:.0f}%" if pd.notna(r["rate"]) else ""
    eff = (f"; ставка по факту {r['eff_rate']:.1f}%".replace(".", ",")) if pd.notna(r["eff_rate"]) else ""
    if f == "no_vat":
        return (f"По Cash Flow {money}, режим «{r['mode']}» {rate}: НДС должен быть "
                f"≈ {_rub(r['exp'])}, в учёте — нет.")
    if f == "vat_exempt":
        return (f"В условиях «{r['mode']}», а в учёте НДС {_rub(r['actual'])} "
                f"(проводки {_rub(r['gl'])}, УПД {_rub(r['upd'])}){eff}. По Cash Flow {money}.")
    if f in ("diff", "sign"):
        more = "больше" if abs(r["actual"]) > abs(r["exp"]) else "меньше"
        return (f"По Cash Flow {money}, режим «{r['mode']}» {rate}: ожидаемый НДС "
                f"{_rub(r['exp'])}, в учёте {_rub(r['actual'])} — {more} на "
                f"{_rub(r['diff'])}{eff}.")
    if f == "nodoc":
        return (f"По назначению платежей НДС к вычету ≈ {_rub(r['nodoc'])} сверх УПД "
                f"(по УПД {_rub(r['upd'])}). На листе НДС — строка 2.0а.")
    if f == "goods_no_upd":
        return (f"Оплачено за товар {_rub(r['paid'])}, УПД с НДС нет. При ставке "
                f"{'22' if r['ymax'] >= 2026 else '20'}% вычет был бы ≈ {_rub(r['potential'])}.")
    if f == "goods_double":
        return f"НДС по УПД {_rub(r['upd'])} и ещё в проводках {_rub(r['gl'])}."
    if f in ("mode_unknown", "no_cond", "no_contract"):
        return (f"По Cash Flow {money}, правила НДС нет. При стандартной ставке НДС был бы "
                f"≈ {_rub(r['potential'])}.")
    if f == "vat_no_mode":
        return f"В учёте НДС {_rub(r['actual'])}, а режим НДС в условиях не задан."
    return ""


def _nodoc(con, report_date: date) -> pd.DataFrame:
    """НДС по оплатам без УПД (счёт BS 130…) — тот же расчёт, что строка 2.0а листа НДС."""
    try:
        from gear.management.commands.sql.read_query import read_sql
        frag = read_sql("vat_bs130.txt").rstrip().rstrip(",")
        sql = "WITH\n" + frag + "\nSELECT cid, SUM(vat) AS nodoc FROM bs130_vat GROUP BY 1"
        df = con.execute(sql, parameters={"date_from": report_date}).df()
    except Exception as e:                       # отчёт без этой колонки, но собирается
        import logging
        logging.getLogger(__name__).warning("Сверка НДС: оплаты без УПД: %s", e)
        df = pd.DataFrame(columns=["cid", "nodoc"])
    df["key"] = pd.to_numeric(df["cid"], errors="coerce").astype("Int64").astype(str)
    return df[["key", "nodoc"]]


def _bs130(con) -> set:
    """Договоры со счётом BS 130… (товар на баланс) — из того же фрагмента, что строка 2.0а."""
    try:
        from gear.management.commands.sql.read_query import read_sql
        frag = read_sql("vat_bs130.txt")
        frag = frag[:frag.index("bs130_pay AS (")].rstrip().rstrip(",")
        rows = con.execute("WITH\n" + frag + "\nSELECT cid FROM bs130").fetchall()
        return {int(r[0]) for r in rows}
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("Сверка НДС: договоры на баланс 130: %s", e)
        return set()


def build(report_date: date, con) -> dict:
    cf = con.execute(CF_SQL, [report_date]).df()
    cond = con.execute(COND_SQL).df()
    ctr = con.execute(CONTRACT_SQL).df()
    gl = con.execute(GL_SQL, [report_date]).df()
    upd = con.execute(UPD_SQL, [report_date]).df()
    nodoc = _nodoc(con, report_date)
    bs130_ids = _bs130(con)

    cf["d"] = pd.to_datetime(cf["d"])
    for c in ("date_start", "date_finish"):
        cond[c] = pd.to_datetime(cond[c])
    cond["cid"] = cond["cid"].astype("Int64")
    cf["cid"] = cf["cid"].astype("Int64")
    cf["code"] = cf["item"].str.split().str[0].fillna("")
    cf["skip"] = cf["code"].map(_skip)

    skipped = (cf[cf["skip"].notna()]
               .assign(paid=lambda x: x["amount"].where(x["amount"] < 0, 0).abs(),
                       got=lambda x: x["amount"].where(x["amount"] > 0, 0))
               .groupby(["skip", "item"], as_index=False)[["paid", "got"]].sum()
               .sort_values(["skip", "item"]))
    cf = _expected(cf[cf["skip"].isna()], cond)
    cf["y"] = [d.year for d in cf["d"]]
    cf["key"] = cf["cid"].astype(str).where(cf["cid"].notna(), "cp:" + cf["cp_name"])

    def agg(df, keys):
        g = df.groupby(keys, dropna=False)
        out = g.agg(paid=("amount", lambda s: abs(s[s < 0].sum())),
                    got=("amount", lambda s: s[s > 0].sum()),
                    net=("amount", "sum"), exp=("exp", "sum"), potential=("potential", "sum"),
                    cp_cf=("cp_name", "first"), vat_mode=("vat_mode", "last"),
                    rate=("rate", "last"), method=("method", "last"),
                    ymax=("y", "max")).reset_index()
        w = df.assign(a=df["amount"].abs())
        top = (w.groupby(keys + ["item"], dropna=False)["a"].sum().reset_index()
               .sort_values("a").drop_duplicates(keys, keep="last"))
        goods = (w[w["code"].str.startswith(GOODS_CODE)].groupby(keys, dropna=False)["a"].sum()
                 .rename("goods_turn").reset_index())
        out = out.merge(top[keys + ["item"]], on=keys, how="left")
        return out.merge(goods, on=keys, how="left")

    acc = pd.concat([gl.rename(columns={"vat_gl": "v"}).assign(src="gl"),
                     upd.rename(columns={"vat_upd": "v"}).assign(src="upd")])
    acc["cid"] = acc["cid"].astype("Int64")
    acc["key"] = acc["cid"].astype(str).where(acc["cid"].notna(), "cp:Без договора (учёт)")
    acc_y = acc.pivot_table(index=["key", "y"], columns="src", values="v",
                            aggfunc="sum").reset_index()
    acc_t = acc.pivot_table(index="key", columns="src", values="v", aggfunc="sum").reset_index()
    for t in (acc_y, acc_t):
        for c in ("gl", "upd"):
            if c not in t:
                t[c] = 0.0

    info = ctr.assign(key=ctr["cid"].astype(str)).set_index("key")

    def finish(df, accd, keys):
        df = df.merge(accd, on=keys, how="outer")
        if keys == ["key"]:
            df = df.merge(nodoc, on="key", how="left")
        else:
            df["nodoc"] = 0.0
        for c in ("paid", "got", "net", "exp", "potential", "gl", "upd", "goods_turn", "nodoc"):
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)
        df["ymax"] = pd.to_numeric(df["ymax"], errors="coerce").fillna(report_date.year)
        df["vat_mode"] = df["vat_mode"].fillna("none")
        idx = df["key"]
        df["cid"] = pd.to_numeric(idx.where(~idx.str.startswith("cp:")),
                                  errors="coerce").astype("Int64")
        df["cp"] = idx.map(info["cp"]).fillna(df["cp_cf"])
        df["cp"] = df["cp"].fillna(idx.where(idx.str.startswith("cp:"))
                                   .str.replace("cp:", "", regex=False)).fillna(
            "Договора нет в справочнике")
        df["contract"] = idx.map(info["contract"]).fillna("")
        df.loc[idx.str.startswith("cp:"), "contract"] = "без договора"
        df["actual"] = df["gl"] + df["upd"]
        # товар — есть УПД или договор идёт на баланс 130001
        df["goods"] = (df["upd"].abs() >= TOL_RUB) | df["cid"].isin(bs130_ids)
        df["goods"] = df["goods"].fillna(False).astype(bool)
        base = df["net"].abs() - df["actual"].abs()
        df["eff_rate"] = (df["actual"].abs() / base.where(base > 0) * 100).where(
            df["actual"].abs() >= 1)
        df["wb"] = df["cp"].apply(is_marketplace)
        df["fcode"] = df.apply(_classify, axis=1)
        # для товара сверка по УПД, ожидаемый по оплатам не показываем
        df.loc[df["goods"] | df["wb"] | df["vat_mode"].eq("by_payment"), ["exp"]] = float("nan")
        df["diff"] = (df["actual"] - df["exp"]).where(df["exp"].notna())
        df.loc[df["fcode"].isin(["wb", "goods_ok", "goods_double", "nodoc"]), "potential"] = 0.0
        df.loc[df["fcode"].eq("goods_no_upd"), "potential"] = (
            df["paid"] * df["ymax"].map(_std) / (100 + df["ymax"].map(_std)))
        df["flag"] = df["fcode"].map(lambda f: FLAGS[f][0])
        df["todo"] = df["fcode"].map(lambda f: FLAGS[f][1])
        df["mode"] = df["vat_mode"].map(MODE_NAME).fillna(df["vat_mode"])
        df["weight"] = pd.concat([df["diff"].abs().fillna(0), df["potential"].abs(),
                                  df["nodoc"].where(df["fcode"].eq("nodoc"), 0),
                                  df["gl"].abs().where(df["fcode"].eq("goods_double"), 0)],
                                 axis=1).max(axis=1)
        df.loc[df["fcode"].isin(["ok", "wb", "goods_ok"]), "weight"] = 0.0
        df["why"] = df.apply(_explain, axis=1)
        return df

    tot = finish(agg(cf, ["key"]), acc_t, ["key"])
    tot = tot.sort_values(["cp", "contract"], key=lambda x: x.astype(str).str.upper() if x.dtype == object else x)
    yr = finish(agg(cf, ["key", "y"]), acc_y, ["key", "y"])
    yr = yr.sort_values(["cp", "contract", "y"])
    issues = tot[tot["weight"] > 0].copy()
    issues.insert(0, "n", range(1, len(issues) + 1))      # по алфавиту, как остальные листы
    ops = cf[cf["key"].isin(set(issues["key"]))].copy()
    ops["cp"] = ops["key"].map(tot.set_index("key")["cp"])
    ops["contract"] = ops["key"].map(tot.set_index("key")["contract"])
    ops["mode"] = ops["vat_mode"].map(MODE_NAME)
    ops["n"] = ops["key"].map(issues.set_index("key")["n"])
    ops = ops.sort_values(["cp", "contract", "d"], key=lambda x: x.astype(str).str.upper() if x.dtype == object else x)
    return {"tot": tot, "yr": yr, "issues": issues, "ops": ops, "skipped": skipped}


# ---------------------------------------------------------------- Excel
ISSUE_COLS = [
    ("n", "№", "id", 5), ("flag", "Что не так", "wrap", 26), ("cp", "Контрагент", "wrap", 26),
    ("contract", "Договор", "wrap", 28), ("cid", "ID", "id", 7),
    ("weight", "Сумма вопроса, ₽", "money", 14), ("why", "Пояснение", "wrap", 60),
    ("todo", "Что сделать", "wrap", 44),
]
ALL_COLS = [
    ("cp", "Контрагент", "wrap", 28), ("contract", "Договор", "wrap", 30), ("cid", "ID", "id", 7),
    ("flag", "Статус", "wrap", 26), ("method", "Метод учёта", "text", 13),
    ("mode", "Режим НДС", "text", 12), ("rate", "Ставка, %", "dec", 8),
    ("item", "Основная статья CF", "wrap", 26),
    ("paid", "Оплачено, ₽", "money", 14), ("got", "Получено, ₽", "money", 14),
    ("exp", "НДС ожидаемый по оплатам, ₽", "money", 14),
    ("gl", "НДС в проводках, ₽", "money", 14), ("upd", "НДС по УПД, ₽", "money", 13),
    ("actual", "НДС в учёте итого, ₽", "money", 14),
    ("diff", "Разница: учёт − ожидаемый, ₽", "money", 14),
    ("eff_rate", "Ставка по факту, %", "dec", 8),
    ("nodoc", "НДС по оплатам без УПД, ₽", "money", 14),
]
YR_COLS = [("cp", "Контрагент", "wrap", 28), ("contract", "Договор", "wrap", 30),
           ("cid", "ID", "id", 7), ("y", "Год", "id", 6), ("mode", "Режим НДС", "text", 12),
           ("paid", "Оплачено, ₽", "money", 14), ("got", "Получено, ₽", "money", 14),
           ("exp", "НДС ожидаемый, ₽", "money", 14), ("gl", "НДС в проводках, ₽", "money", 14),
           ("upd", "НДС по УПД, ₽", "money", 13), ("diff", "Разница, ₽", "money", 14)]
OPS_COLS = [("n", "№ замечания", "id", 8), ("cp", "Контрагент", "wrap", 26),
            ("contract", "Договор", "wrap", 28), ("cid", "ID", "id", 7), ("d", "Дата", "date", 11),
            ("item", "Статья CF", "wrap", 26), ("subitem", "Подстатья CF", "wrap", 26),
            ("amount", "Сумма CF, ₽", "money", 14), ("mode", "Режим НДС", "text", 12),
            ("rate", "Ставка, %", "dec", 8), ("exp", "НДС ожидаемый, ₽", "money", 14)]
SKIP_COLS = [("skip", "Почему не проверяется", "wrap", 34), ("item", "Статья CF", "wrap", 40),
             ("paid", "Оплачено, ₽", "money", 16), ("got", "Получено, ₽", "money", 16)]
NOTES = [
    ("С чего начать", "Лист «Что проверить»: замечания по убыванию суммы. По каждому — что не "
                      "так, цифры и что сделать. Операции по замечанию — на листе «Операции» "
                      "(фильтр по №)."),
    ("Ожидаемый НДС", "Оплаты по Cash Flow × ставка / (100 + ставка) по режиму и ставке из "
                      "условий договора на дату платежа. «Только НДС» — вся сумма. «Без НДС» и "
                      "«Не задан» — ноль."),
    ("НДС в учёте", "Проводки НДС (начисления по договору) плюс НДС по УПД поставщиков товаров."),
    ("Оплаты без УПД", "Договоры со счётом BS 130…: НДС из назначения платежей минус НДС по УПД, "
                       "нарастающим итогом, не меньше нуля — то же, что строка 2.0а листа НДС. "
                       "Это оценка: вычет возможен только по УПД, поэтому их надо запросить."),
    ("Товарные договоры", "Договоры с УПД или со счётом BS 130001 (товар на баланс): НДС "
                          "по ним — по УПД и строке 2.0а, с оплатами по ставке не сравнивается "
                          "(поставки и оплаты идут в разное время)."),
    ("Не проверяется", "Финансирование (займы, взносы, проценты — статьи 3…) и налоги (125…): "
                       "НДС в них нет. Суммы — на листе «Не проверялось». WB сверяется на листе "
                       "НДС манпака."),
    ("Знаки", "К вычету — плюс, начисленный — минус, как на листе «НДС по операциям»."),
    ("Порог", "Расхождение меньше 1 000 ₽ или 3% ожидаемого — не замечание."),
    ("Ограничения", "Оплаты и начисления расходятся по времени: аванс оплачен, а акт ещё нет, "
                    "или наоборот — часть разницы может объясняться долгом или авансом. "
                    "УПД — только в рублях."),
]


def to_excel(res: dict, report_date: date) -> bytes:
    from gear.management.commands import mp
    import xlsxwriter

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
        "id": F(**line, num_format="0", align="center"),
        "date": F(**line, num_format="dd.mm.yyyy", align="center"),
        "money": F(**line, num_format=mp.FMT_MONEY), "dec": F(**line, num_format="0.0"),
        "lbl": F(bold=True, font_color="#" + mp.NAVY_3, **line),
        "bad": F(**line, text_wrap=True, bg_color="#F8D7D3"),
        "warn": F(**line, text_wrap=True, bg_color="#FCEBCF"),
        "ok": F(**line, text_wrap=True, font_color="#" + mp.MUTED),
        "kpi_l": F(bold=True, font_color="#" + mp.NAVY_3, **line),
        "kpi_v": F(bold=True, font_size=11, **line, num_format=mp.FMT_MONEY),
        "tot": F(bold=True, top=1, bottom=1, num_format=mp.FMT_MONEY),
        "tot_l": F(bold=True, top=1, bottom=1),
    }
    sub = (f"Отчётная дата {report_date:%d.%m.%Y} · весь период до неё · к вычету +, "
           "начисленный − · сформировано " + pd.Timestamp.now().strftime("%d.%m.%Y %H:%M"))
    WARN = {FLAGS[k][0] for k in ("mode_unknown", "vat_no_mode", "no_cond", "no_contract")}
    OKS = {FLAGS[k][0] for k in ("ok", "wb", "goods_ok")}

    def flag_fmt(v):
        return fmt["ok"] if v in OKS else fmt["warn"] if v in WARN else fmt["bad"]

    def head(ws, title, r=0):
        ws.write(r, 0, title, fmt["title"])
        ws.write(r + 1, 0, sub, fmt["sub"])

    def table(name, title, cols, df, total=False, freeze=2):
        ws = wb.add_worksheet(name)
        head(ws, title)
        r0 = 3
        for j, (_k, h, _t, w) in enumerate(cols):
            ws.write(r0, j, h, fmt["hdr"])
            ws.set_column(j, j, w)
        ws.set_row(r0, 40)
        for i, row in enumerate(df[[c[0] for c in cols]].itertuples(index=False), start=r0 + 1):
            for j, ((k, _h, t, _w), v) in enumerate(zip(cols, row)):
                if v is None or (not isinstance(v, str) and pd.isna(v)):
                    ws.write_blank(i, j, None, fmt["text"])
                elif k in ("flag",):
                    ws.write(i, j, v, flag_fmt(v))
                elif t in ("money", "dec", "id"):
                    v = float(v)
                    if t == "money" and abs(v) < 0.5:   # копейки и хвосты округления — прочерк
                        v = 0.0
                    ws.write_number(i, j, v, fmt[t])
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
        ws.freeze_panes(r0 + 1, freeze)
        return ws

    # Итог
    tot, issues = res["tot"], res["issues"]
    ws = wb.add_worksheet("Итог")
    ws.set_column(0, 0, 50)
    ws.set_column(1, 2, 16)
    head(ws, "Сверка НДС по договорам")
    ws.write(3, 0, "Договоров проверено", fmt["kpi_l"])
    ws.write_number(3, 1, int(len(tot)), fmt["kpi_v"])
    ws.write(4, 0, "Замечаний (лист «Что проверить»)", fmt["kpi_l"])
    ws.write_number(4, 1, int(len(issues)), fmt["kpi_v"])
    ws.write(5, 0, "Сумма вопросов, ₽", fmt["kpi_l"])
    ws.write_number(5, 1, float(issues["weight"].sum()), fmt["kpi_v"])
    r = 7
    for j, h in enumerate(("ЗАМЕЧАНИЕ", "ДОГОВОРОВ", "СУММА ВОПРОСА, ₽")):
        ws.write(r, j, h, fmt["hdr"])
    r += 1
    order = {v[0]: v[2] for v in FLAGS.values()}
    g = tot.groupby("flag").agg(n=("key", "size"), w=("weight", "sum")).reset_index()
    g = g.sort_values("flag", key=lambda s: s.map(order))
    for row in g.itertuples(index=False):
        ws.write(r, 0, row.flag, flag_fmt(row.flag))
        ws.write_number(r, 1, int(row.n), fmt["id"])
        ws.write_number(r, 2, float(row.w), fmt["money"])
        r += 1
    r += 1
    ws.write(r, 0, "Сумма вопроса — расхождение НДС; где режима НДС нет — сколько НДС было бы "
                   "при стандартной ставке. Это ориентир, где искать, а не сумма ошибки.",
             fmt["sub"])

    table("Что проверить", "Что проверить — по убыванию суммы", ISSUE_COLS, issues, freeze=2)
    table("Все договоры", "Все договоры", ALL_COLS, tot, total=True, freeze=2)
    table("По годам", "Договоры по годам", YR_COLS, res["yr"], freeze=2)
    table("Операции", "Операции Cash Flow по замечаниям", OPS_COLS, res["ops"], freeze=1)
    table("Не проверялось", "Не проверялось: в этих операциях НДС нет", SKIP_COLS,
          res["skipped"], total=True, freeze=0)

    ws = wb.add_worksheet("Как читать")
    ws.set_column(0, 0, 20)
    ws.set_column(1, 1, 110)
    ws.write(0, 0, "Как читать", fmt["title"])
    for i, (a, b) in enumerate(NOTES, start=2):
        ws.write(i, 0, a, fmt["lbl"])
        ws.write(i, 1, b, fmt["wrap"])
        ws.set_row(i, 36)
    wb.close()
    return buf.getvalue()


def build_vat_contracts_workbook(report_date: date) -> tuple[bytes, str]:
    from conns import get_duckdb_conn_with_opt
    with get_duckdb_conn_with_opt(ro=True) as con:
        res = build(report_date, con)
    return to_excel(res, report_date), f"Сверка НДС по договорам {report_date:%Y%m%d}.xlsx"
