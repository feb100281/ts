# gear/app/manpack/contracts_check.py
"""Проверка списания договоров: деньги по договору → куда списаны (P&L, баланс, НДС)
и что осталось на счёте расчётов. Рядом — условия начисления договора.

Суммы — оборот gl.fact по договору, dt − cr:
  деньги (счета с parent_id = 3): + поступление, − оплата (запись без пары);
  начисления: счёт расчётов ST против P&L / баланса / НДС;
  остаток по расчётам = деньги + списано (P&L, баланс, НДС): не зависит от того,
  на каком счёте функция держит расчёты (у депозитов и займов — свои счета);
  + получили больше, чем списано (долг перед контрагентом / аванс получен),
  − заплатили больше (аванс выдан / долг контрагента).
График — gl.accural_distribution: всё, что функции начислили, в том числе после
отчётной даты; по нему видно, спишется ли остаток к концу условий.

Счета договора — как в начислениях (gl.accurals_args): ST — contracts.bs_id,
BS — условия.acc_bs_id или contracts.st_id, P&L — условия.acc_pl_id или contracts.pl_id.
"""
from __future__ import annotations

import io
import json
from datetime import date

import pandas as pd

TOL_RUB = 1000.0
WB_NAMES = ("ВАЙЛДБЕРРИЗ", "WILDBERRIES", "РВБ")
SKIP_ITEMS = (("4", "Переводы между счетами и конвертация"), ("125", "Налоги и сборы"))
CASH_PARENT, VAT_PARENT = 3, 31
GOODS_SUB, GOODS_BS = "1211", "130"     # подстатья «Закупка товара», счёт BS товара

FACT_SQL = """
SELECT f.contract_id AS cid, LAST_DAY(f.date_from)::DATE AS me, f.acc_id,
       SUM(f.dt) / 100.0 AS dt, SUM(f.cr) / 100.0 AS cr
FROM pg.gl.fact f
WHERE f.date_from <= ? AND f.contract_id IS NOT NULL
GROUP BY 1, 2, 3
"""
COA_SQL = """
SELECT id, CAST(code AS VARCHAR) AS code, name, parent_id FROM pg.public.corporate_coa
"""
CTR_SQL = """
SELECT k.id AS cid,
       COALESCE(ct.title, 'Договор') || ' № ' || COALESCE(k.number, 'б/н') || ' от '
           || COALESCE(strftime(k.date, '%d.%m.%Y'), 'б/д') || ' · id ' || CAST(k.id AS VARCHAR)
           AS contract,
       COALESCE(NULLIF(TRIM(cp.name), ''), 'Без контрагента') AS cp,
       k.bs_id AS st_acc, k.st_id AS bs_acc, k.pl_id AS pl_acc
FROM pg.public.contracts_contracts k
LEFT JOIN pg.public.contracts_contractstitle ct ON ct.id = k.title_id
LEFT JOIN pg.public.counterparties_counterparty cp ON cp.id = k.cp_id
"""
COND_SQL = """
SELECT t.id AS cond_id, t.contract_id AS cid, t.date_start, t.date_finish,
       COALESCE(t.vat_mode, 'unknown') AS vat_mode, t.fn_id, f.name AS fn,
       COALESCE(f.python_path, '') AS fn_path,
       COALESCE(am.name, am2.name) AS method,
       t.amount, t.period, t.pay_rule, t.pay_timing, t.pay_day,
       CAST(t.vat_json AS VARCHAR) AS vat_json, CAST(t.param_json AS VARCHAR) AS params,
       COALESCE(t.acc_bs_id, k.st_id) AS bs_acc, COALESCE(t.acc_pl_id, k.pl_id) AS pl_acc,
       COALESCE(t.subconto_bs_id, k.subconto_bs_id) AS sub_bs,
       COALESCE(t.subconto_pl_id, k.subconto_pl_id) AS sub_pl
FROM pg.public.contracts_conditions t
LEFT JOIN pg.public.contracts_contracts k ON k.id = t.contract_id
LEFT JOIN pg.public.contracts_accuralfn f ON f.id = t.fn_id
LEFT JOIN pg.public.contracts_accountingmethod am ON am.id = t.accounting_method_id
LEFT JOIN pg.public.contracts_accountingmethod am2 ON am2.id = f.accounting_method_id
"""
AD_SQL = """
SELECT contract_id AS cid,
       SUM(CASE WHEN acc_pl IS NOT NULL THEN dt_pl - cr_pl ELSE 0 END
           + CASE WHEN acc_bs IS NOT NULL THEN dt_bs - cr_bs ELSE 0 END
           + CASE WHEN acc_vat IS NOT NULL THEN dt_vat - cr_vat ELSE 0 END)
           FILTER (WHERE date_from > ?) / 100.0 AS future,
       MAX(date_from) AS ad_last
FROM pg.gl.accural_distribution
WHERE contract_id IS NOT NULL
GROUP BY 1
"""
ITEM_SQL = """
SELECT CAST(id AS BIGINT) AS id, CAST(code AS VARCHAR) || ' ' || name AS name
FROM pg.public.corporate_cfitems
"""
CF_SQL = """
SELECT date_from::DATE AS d, CAST(amount AS DOUBLE) AS amount, COALESCE(item, '') AS item,
       COALESCE(subitem, '') AS subitem, TRY_CAST(contract_id AS BIGINT) AS cid,
       COALESCE(NULLIF(TRIM(cp_name), ''), 'Без контрагента') AS cp_name
FROM pg.cf_to_csv
WHERE date_from::DATE <= ? AND COALESCE(amount, 0) <> 0
"""

MODE = {"included": "НДС включён", "excluded": "НДС сверху", "exempt": "Без НДС",
        "unknown": "Не задан", "vat_only": "Только НДС",
        "by_payment": "По назначению платежа"}
PERIOD = {"week": "Неделя", "month": "Месяц", "quarter": "Квартал", "year": "Год"}
PAY_RULE = {"month": "За месяц", "quarter": "За квартал", "half_year": "За полугодие",
            "year": "За год", "m2": "За 2 месяца", "m3": "За 3 месяца", "m4": "За 4 месяца",
            "custom": "Другое"}
PAY_TIMING = {"prepay": "Предоплата", "postpay": "Постоплата"}

# код: (название, что сделать, порядок)
FLAGS = {
    "no_contract": ("Платежи без договора — никуда не списываются",
                    "Привязать платежи к договору в Cash Flow, у договора завести условия.", 0),
    "no_cond": ("Нет условий начисления",
                "Завести условия договора: функцию начисления, счёт P&L или BS, НДС. Без них "
                "деньги остаются на расчётах и никуда не списываются.", 1),
    "no_fn": ("Условия без функции начисления",
              "Выбрать функцию начисления в условиях — без неё GL ETL условия пропускает.", 2),
    "no_target": ("Не указан ни счёт P&L, ни счёт BS",
                  "Указать в условиях или в договоре, куда списывать: счёт P&L (расход сразу) "
                  "или счёт BS (на баланс).", 3),
    "both": ("Списание и в P&L, и на баланс",
             "Проверить, нет ли двойного списания: обычно указывают что-то одно — P&L или BS.", 4),
    "goods_pl": ("Закупка товара списывается в P&L",
                 "Если это товар — в условиях указать счёт BS 130001 вместо P&L (в себестоимость "
                 "он попадёт при продаже). Если это не товар (услуги, логистика) — поменять "
                 "подстатью в Cash Flow.", 5),
    "plan": ("Списано не по графику условий",
             "Сравнить начисления с условиями: сумма в месяц, даты, НДС сверху/внутри. Частая "
             "причина — после правки условий не запущен GL ETL или условия пересекаются.", 6),
    "outside": ("Платежи вне сроков условий",
                "Продлить или добавить условия на эти даты — иначе платежи не списываются.", 6),
    "unwritten": ("Не всё списано: остаток на расчётах",
                  "Метод Cash Based должен списывать каждый платёж. Остаток — платежи вне "
                  "условий, не запущен GL ETL или ошибка в условиях.", 7),
    "balance": ("Остаток на расчётах (аванс / долг)",
                "Справочно: при начислениях по актам остаток — это аванс или долг. Сверить с "
                "актом сверки, если сумма неожиданная.", 8),
    "nowhere": ("Деньги есть, никуда не списано",
                "Условия есть, а начислений нет: запустить GL ETL; проверить даты условий и "
                "параметры (например, сумму в месяц).", 4),
    "skip": ("Не проверяется", "", 98),
    "ok": ("OK", "", 99),
}


def _json(v) -> dict:
    try:
        return json.loads(v) if isinstance(v, str) and v else (v or {})
    except (TypeError, ValueError):
        return {}


def _rate_on(vat_json, d) -> float:
    best = None
    for k, v in _json(vat_json).items():
        try:
            kd = pd.Timestamp(k)
        except (TypeError, ValueError):
            continue
        if kd <= d and (best is None or kd > best[0]):
            best = (kd, float(v))
    return best[1] if best else 0.0


def plan_fixed(r, report_date: date) -> tuple[float, float] | None:
    """Фикс. сумма в месяц (fixed_monthly_sums): (всего за срок условий, на отчётную дату),
    с НДС, как в начислениях — помесячно, неполный месяц по дням."""
    amt = _json(r.params).get("Сумма по договору")
    if amt in (None, "") or pd.isna(r.date_start) or pd.isna(r.date_finish):
        return None
    amt = float(amt)
    start, end = pd.Timestamp(r.date_start).normalize(), pd.Timestamp(r.date_finish).normalize()
    if end < start:
        return None
    rep = pd.Timestamp(report_date)
    total = to_date = 0.0
    for ms in pd.date_range(start.to_period("M").to_timestamp(), end.to_period("M").to_timestamp(),
                            freq="MS"):
        dim = ms.days_in_month
        a, b = max(ms, start), min(ms + pd.offsets.MonthEnd(0), end)
        gross = amt * (1 + _rate_on(r.vat_json, a) / 100) if r.vat_mode == "excluded" else amt
        v = gross / dim * ((b - a).days + 1)
        total += v
        if b <= rep:                     # начисление датировано концом месяца или концом срока
            to_date += v
    return total, to_date


def _rub(v) -> str:
    v = float(v or 0)
    a = abs(v)
    if a >= 1e6:
        return f"{a / 1e6:.2f}".replace(".", ",") + " млн ₽"
    if a >= 1e3:
        return f"{a / 1e3:.0f} тыс ₽"
    return f"{a:.0f} ₽"


def _join(vals) -> str:
    vals = [str(v) for v in vals if v is not None and str(v) != "" and not pd.isna(v)]
    return "; ".join(dict.fromkeys(vals))


def build(report_date: date, con) -> dict:
    fact = con.execute(FACT_SQL, [report_date]).df()
    coa = con.execute(COA_SQL).df()
    ctr = con.execute(CTR_SQL).df()
    cond = con.execute(COND_SQL).df()
    items = con.execute(ITEM_SQL).df()
    cf = con.execute(CF_SQL, [report_date]).df()
    try:
        ad = con.execute(AD_SQL, [report_date]).df()
    except Exception as e:                       # без графика — отчёт всё равно собирается
        import logging
        logging.getLogger(__name__).warning("Списание договоров: график: %s", e)
        ad = pd.DataFrame(columns=["cid", "future", "ad_last"])

    coa = coa.set_index("id")
    acc_name = (coa["code"].fillna("") + " " + coa["name"].fillna("")).str.strip()
    cash_ids = set(coa.index[coa["parent_id"] == CASH_PARENT])
    vat_ids = set(coa.index[coa["parent_id"] == VAT_PARENT])
    item_name = items.set_index("id")["name"]
    for c in ("date_start", "date_finish"):
        cond[c] = pd.to_datetime(cond[c])
    cf["d"] = pd.to_datetime(cf["d"])
    noc = cf[cf["cid"].isna()].copy()
    cf = cf[cf["cid"].notna()].copy()
    cf["cid"] = cf["cid"].astype("int64")

    # счета договора: ST — из договора, P&L и BS — договор плюс все условия
    st_of = ctr.set_index("cid")["st_acc"].to_dict()
    pl_of, bs_of = {}, {}
    for r in ctr.itertuples(index=False):
        pl_of[r.cid] = {r.pl_acc} - {None} if pd.notna(r.pl_acc) else set()
        bs_of[r.cid] = {r.bs_acc} if pd.notna(r.bs_acc) else set()
    for r in cond.itertuples(index=False):
        if pd.notna(r.pl_acc):
            pl_of.setdefault(r.cid, set()).add(r.pl_acc)
        if pd.notna(r.bs_acc):
            bs_of.setdefault(r.cid, set()).add(r.bs_acc)

    def kind(cid, acc):
        if acc in cash_ids:
            return "cash"
        if acc in vat_ids:
            return "vat"
        if pd.notna(st_of.get(cid)) and acc == st_of.get(cid):
            return "st"
        if acc in pl_of.get(cid, ()):
            return "pl"
        if acc in bs_of.get(cid, ()):
            return "bs"
        return "other"

    fact["k"] = [kind(c, a) for c, a in zip(fact["cid"], fact["acc_id"])]
    fact["v"] = fact["dt"] - fact["cr"]
    m = fact.pivot_table(index=["cid", "me"], columns="k", values="v", aggfunc="sum",
                         fill_value=0.0).reset_index()
    cash_io = (fact[fact["k"] == "cash"].groupby("cid")
               .agg(got=("dt", "sum"), paid=("cr", "sum")).reset_index())
    t = m.drop(columns="me").groupby("cid").sum().reset_index()
    for c in ("cash", "st", "pl", "bs", "vat", "other"):
        for df in (m, t):
            if c not in df:
                df[c] = 0.0
    t = t.merge(cash_io, on="cid", how="left")
    # оборот списаний (dt + cr): у депозита размещение и возврат на балансе дают ноль в сумме,
    # но списание было
    wo = fact[fact["k"].isin(["pl", "bs", "vat"])]
    t = t.merge((wo["dt"] + wo["cr"]).groupby(wo["cid"]).sum().rename("wo_turn").reset_index(),
                on="cid", how="left")

    # условия по договору
    cg = cond.groupby("cid")
    cinfo = pd.DataFrame({
        "n_cond": cg.size(),
        "n_fn": cg["fn_id"].count(),
        "fn": cg["fn"].agg(_join),
        "method": cg["method"].agg(_join),
        "vat_modes": cg["vat_mode"].agg(lambda s: _join(MODE.get(x, x) for x in s)),
        "start": cg["date_start"].min(),
        "finish": cg["date_finish"].agg(lambda s: pd.NaT if s.isna().any() else s.max()),
    }).reset_index()

    # план по условиям: фиксированная сумма в месяц — по графику, Cash Based — по оплатам
    plans = [plan_fixed(r, report_date) if "fixed_monthly" in r.fn_path else None
             for r in cond.itertuples(index=False)]
    cond["plan_total"] = [p[0] if p else None for p in plans]
    cond["plan_date"] = [p[1] if p else None for p in plans]
    pg_ = cond.groupby("cid")
    cplan = pd.DataFrame({
        "plan_total": pg_["plan_total"].sum(min_count=1),
        "plan_date": pg_["plan_date"].sum(min_count=1),
        "plan_all": pg_["plan_total"].apply(lambda s: s.notna().all()),
    }).reset_index()

    # оплаты вне сроков условий; доля товара в оборотах
    def outside(r):
        g = by_c.get(r.cid)
        if g is None:
            return False
        ok = ((g["date_start"].isna() | (g["date_start"] <= r.d))
              & (g["date_finish"].isna() | (g["date_finish"] > r.d)))
        return not ok.any()
    by_c = {c: g for c, g in cond.groupby("cid")}
    cf["outside"] = [outside(r) for r in cf.itertuples(index=False)]
    cf["goods"] = cf["subitem"].str.startswith(GOODS_SUB)
    cf["a"] = cf["amount"].abs()
    cfa = cf.groupby("cid").agg(
        turn=("a", "sum"),
        goods=("a", lambda s: s[cf.loc[s.index, "goods"]].sum()),
        out_sum=("a", lambda s: s[cf.loc[s.index, "outside"]].sum()),
        out_n=("outside", "sum"),
        item=("item", lambda s: s.value_counts().index[0] if len(s) else ""),
    ).reset_index()

    df = (ctr.merge(t, on="cid", how="left").merge(cinfo, on="cid", how="left")
          .merge(cfa, on="cid", how="left").merge(cplan, on="cid", how="left")
          .merge(ad, on="cid", how="left"))
    num = ["cash", "st", "pl", "bs", "vat", "other", "got", "paid", "turn", "goods", "out_sum",
           "out_n", "n_cond", "n_fn", "future", "wo_turn"]
    df[num] = df[num].apply(pd.to_numeric, errors="coerce").fillna(0.0)
    moved = (df["got"] + df["paid"] + df["turn"] + df["pl"].abs() + df["bs"].abs()
             + df["st"].abs()) > 0
    df = df[moved | (df["n_cond"] > 0)].copy()

    df["st_name"] = df["st_acc"].map(acc_name)
    df["pl_name"] = df["cid"].map(lambda c: _join(acc_name.get(a) for a in pl_of.get(c, ())))
    df["bs_name"] = df["cid"].map(lambda c: _join(acc_name.get(a) for a in bs_of.get(c, ())))
    bs_codes = df["cid"].map(lambda c: [str(coa["code"].get(a, "")) for a in bs_of.get(c, ())])
    df["bs_goods"] = bs_codes.map(lambda cs: any(x.startswith(GOODS_BS) for x in cs))
    df["cash_based"] = df["method"].fillna("").str.contains("cash", case=False)
    df["written"] = df["pl"] + df["bs"] + df["vat"]
    df["bal"] = df["cash"] + df["written"]      # остаток по расчётам
    # аванс закрывается будущими начислениями; долг — оплатой
    df["final"] = (df["bal"] + df["future"]).where(df["bal"] < 0, df["bal"])

    def outcome(r):
        bal, fut = r["bal"], r["future"]
        end = f" к {_d(r['ad_last'])}" if pd.notna(r["ad_last"]) else ""
        if abs(bal) < TOL_RUB:
            if abs(fut) >= TOL_RUB:
                return f"Остатка нет; по графику ещё начислится {_rub(fut)}{end}"
            return "Закрыт: остатка нет"
        if bal > 0:
            return f"Долг перед контрагентом / аванс получен {_rub(bal)}"
        left = bal + fut
        if left >= -TOL_RUB:
            tail = f", дальше к оплате {_rub(left)}" if left >= TOL_RUB else ""
            return f"Аванс {_rub(bal)} спишется по графику{end}{tail}"
        if abs(fut) >= TOL_RUB:
            return (f"Аванс {_rub(bal)}: по графику спишется {_rub(fut)}, останется "
                    f"{_rub(left)} — разобрать")
        return f"Аванс {_rub(bal)}: графика нет — разобрать"
    df["outcome"] = df.apply(outcome, axis=1)

    def skip_reason(r):
        if any(n in str(r["cp"]).upper() for n in WB_NAMES):
            return "Маркетплейс WB — по отчёту WB"
        code = str(r["item"] or "").split(" ")[0]
        for pfx, name in SKIP_ITEMS:
            if code.startswith(pfx):
                return name
        return ""
    df["skip"] = df.apply(skip_reason, axis=1)
    cb = df["cash_based"] & df["plan_total"].isna()
    df.loc[cb, "plan_date"] = df.loc[cb, "paid"] - df.loc[cb, "got"]   # списывается по оплатам
    df.loc[cb, "plan_total"] = df.loc[cb, "plan_date"]
    df["plan_how"] = ""
    df.loc[df["plan_total"].notna(), "plan_how"] = "по графику условий"
    df.loc[cb, "plan_how"] = "по оплатам (Cash Based)"
    df.loc[df["plan_all"].eq(False) & ~cb, "plan_how"] = "часть условий без графика"
    df["plan_diff"] = (df["written"].abs() - df["plan_date"].abs()).where(df["plan_date"].notna())
    df["plan_left"] = (df["plan_total"].abs() - df["written"].abs()).where(df["plan_total"].notna())

    def classify(r):
        money = max(r["got"] + r["paid"], r["turn"])
        if r["skip"]:
            return "skip"
        if money < TOL_RUB and abs(r["bal"]) < TOL_RUB:
            return "ok"
        if r["n_cond"] == 0:
            return "no_cond"
        if r["n_fn"] == 0:
            return "no_fn"
        if not r["pl_name"] and not r["bs_name"]:
            return "no_target"
        if money >= TOL_RUB and r["wo_turn"] < TOL_RUB:
            return "nowhere"
        if abs(r["pl"]) >= TOL_RUB and abs(r["bs"]) >= TOL_RUB:
            return "both"
        if r["goods"] >= 0.5 * r["turn"] > 0 and abs(r["pl"]) >= TOL_RUB and abs(r["bs"]) < TOL_RUB:
            return "goods_pl"
        if (pd.notna(r["plan_diff"]) and r["plan_how"] == "по графику условий"
                and abs(r["plan_diff"]) >= max(TOL_RUB, 0.02 * abs(r["plan_date"]))):
            return "plan"
        if r["out_sum"] >= TOL_RUB:
            return "outside"
        if abs(r["bal"]) >= max(TOL_RUB, 0.01 * money):
            return "unwritten" if r["cash_based"] else "balance"
        return "ok"

    def weight(r):
        f = r["fcode"]
        if f in ("no_cond", "no_fn", "no_target", "nowhere"):
            return max(r["paid"], r["got"], r["turn"])
        if f == "both":
            return min(abs(r["pl"]), abs(r["bs"]))
        if f == "goods_pl":
            return abs(r["pl"])
        if f == "outside":
            return r["out_sum"]
        if f == "plan":
            return abs(r["plan_diff"])
        if f == "unwritten":
            return abs(r["bal"])
        return 0.0                               # «balance» — справочно, не замечание

    def explain(r):
        f = r["fcode"]
        money = ", ".join(x for x in (f"оплачено {_rub(r['paid'])}" if r["paid"] >= 1 else "",
                                      f"получено {_rub(r['got'])}" if r["got"] >= 1 else "") if x)
        wo = (f"в P&L {_rub(r['pl'])}, на баланс {_rub(r['bs'])}, НДС {_rub(r['vat'])}")
        st = (f"{'долг перед контрагентом / аванс получен' if r['bal'] > 0 else 'аванс выдан / контрагент должен нам'} "
              f"{_rub(r['bal'])}")
        if not money and r["turn"] >= 1:
            money = f"оборот по Cash Flow {_rub(r['turn'])}"
        if f == "no_cond":
            return f"Деньги по договору: {money}. Условий начисления нет — никуда не списано."
        if f == "nowhere":
            return (f"Деньги: {money}. Условия есть (функция «{r['fn']}», "
                    f"{_d(r['start'])} — {_d(r['finish'])}), а списаний нет.")
        if f == "no_fn":
            return f"Деньги: {money}. Условий {int(r['n_cond'])}, ни в одном нет функции."
        if f == "no_target":
            return f"Деньги: {money}. Функция «{r['fn']}», но нет ни счёта P&L, ни BS."
        if f == "both":
            return f"Деньги: {money}. Списано {wo}. Счета: P&L {r['pl_name']}; BS {r['bs_name']}."
        if f == "goods_pl":
            return (f"Платежи по подстатье «Закупка товара» (1211…) — {_rub(r['goods'])} из "
                    f"{_rub(r['turn'])}, а списываются в P&L ({r['pl_name']}) — "
                    f"{_rub(r['pl'])}, на баланс 130… — ничего.")
        if f == "plan":
            more = "больше" if r["plan_diff"] > 0 else "меньше"
            return (f"По условиям на отчётную дату должно быть списано {_rub(r['plan_date'])} "
                    f"(с НДС), списано {_rub(r['written'])} — {more} на {_rub(r['plan_diff'])}. "
                    f"Всего за срок условий {_rub(r['plan_total'])}, осталось "
                    f"{_rub(r['plan_left'])}.")
        if f == "outside":
            return (f"{int(r['out_n'])} платежей на {_rub(r['out_sum'])} вне дат условий "
                    f"(условия: {_d(r['start'])} — {_d(r['finish'])}).")
        if f in ("unwritten", "balance"):
            return f"Деньги: {money}. Списано: {wo}. На расчётах осталось: {st}."
        return ""

    df["fcode"] = df.apply(classify, axis=1)
    df.loc[df["fcode"].eq("skip"), "flag_skip"] = "Не проверяется: " + df["skip"]
    df["weight"] = df.apply(weight, axis=1)
    df["flag"] = df["fcode"].map(lambda f: FLAGS[f][0])
    df.loc[df["fcode"].eq("skip"), "flag"] = df["flag_skip"]
    df["todo"] = df["fcode"].map(lambda f: FLAGS[f][1])
    df["why"] = df.apply(explain, axis=1)
    df["item_name"] = df["item"].fillna("")
    if len(noc):
        noc["a"] = noc["amount"].abs()
        nc = noc.groupby("cp_name").agg(
            paid=("amount", lambda x: abs(x[x < 0].sum())), got=("amount", lambda x: x[x > 0].sum()),
            turn=("a", "sum"), n=("a", "size"), d0=("d", "min"), d1=("d", "max"),
            item=("item", lambda x: x.value_counts().index[0])).reset_index()
        nc = nc[(nc["turn"] >= TOL_RUB)
                & ~nc["item"].str.split(" ").str[0].fillna("").str.startswith(
                    tuple(p for p, _ in SKIP_ITEMS))]
        add = pd.DataFrame({
            "cid": pd.NA, "cp": nc["cp_name"], "contract": "без договора", "fcode": "no_contract",
            "weight": nc["turn"], "paid": nc["paid"], "got": nc["got"], "turn": nc["turn"],
            "item_name": nc["item"],
            "why": [f"Платежей: {int(r.n)}, с {r.d0:%d.%m.%Y} по {r.d1:%d.%m.%Y}: оплачено "
                    f"{_rub(r.paid)}, получено {_rub(r.got)}. Основная статья: {r.item}."
                    for r in nc.itertuples(index=False)]})
        add["flag"], add["todo"] = FLAGS["no_contract"][0], FLAGS["no_contract"][1]
        df = pd.concat([df, add], ignore_index=True)
    alpha = lambda x: x.astype(str).str.upper()
    issues = df[df["weight"] >= TOL_RUB].sort_values(["cp", "contract"], key=alpha).copy()
    issues.insert(0, "n", range(1, len(issues) + 1))
    key = lambda d: d["cid"].astype(str).where(d["cid"].notna(), "cp:" + d["cp"].astype(str))
    df["n"] = key(df).map(dict(zip(key(issues), issues["n"])))
    df = df.sort_values(["cp", "contract"], key=lambda x: x.astype(str).str.upper())

    # условия построчно
    cn = cond.merge(ctr[["cid", "cp", "contract"]], on="cid", how="left")
    cn["mode"] = cn["vat_mode"].map(MODE).fillna(cn["vat_mode"])
    cn["period_n"] = cn["period"].map(PERIOD).fillna(cn["period"])
    cn["pay_rule_n"] = cn["pay_rule"].map(PAY_RULE).fillna(cn["pay_rule"])
    cn["pay_timing_n"] = cn["pay_timing"].map(PAY_TIMING).fillna(cn["pay_timing"])
    cn["bs_n"] = cn["bs_acc"].map(acc_name)
    cn["pl_n"] = cn["pl_acc"].map(acc_name)
    cn["sub_bs_n"] = cn["sub_bs"].map(item_name)
    cn["sub_pl_n"] = cn["sub_pl"].map(item_name)
    nmap = issues.dropna(subset=["cid"]).set_index("cid")["n"]
    cn["n"] = cn["cid"].map(nmap)
    cn = cn.sort_values(["cp", "contract", "date_start"], na_position="first")

    # по месяцам — договоры с замечаниями
    mm = m[m["cid"].isin(set(issues["cid"]))].merge(ctr[["cid", "cp", "contract"]], on="cid")
    mm["n"] = mm["cid"].map(nmap)
    mm = mm.sort_values(["cp", "contract", "me"], key=lambda x: x.astype(str).str.upper()
                        if x.dtype == object else x)
    return {"all": df, "issues": issues, "cond": cn, "months": mm}


def _d(v) -> str:
    return "…" if v is None or pd.isna(v) else pd.Timestamp(v).strftime("%d.%m.%Y")


# ---------------------------------------------------------------- Excel
ISSUE_COLS = [
    ("n", "№", "id", 5), ("flag", "Что не так", "flag", 26), ("cp", "Контрагент", "wrap", 26),
    ("contract", "Договор", "wrap", 28), ("cid", "ID", "id", 7),
    ("weight", "Сумма вопроса, ₽", "money", 14), ("why", "Пояснение", "wrap", 60),
    ("todo", "Что сделать", "wrap", 44),
]
ALL_COLS = [
    ("cp", "Контрагент", "wrap", 26), ("contract", "Договор", "wrap", 30), ("cid", "ID", "id", 7),
    ("flag", "Статус", "flag", 22), ("n", "№ в «Что проверить»", "id", 9),
    ("outcome", "Итог по графику", "wrap", 30),
    ("paid", "Оплачено, ₽", "money", 13), ("got", "Получено, ₽", "money", 13),
    ("pl", "Списано в P&L, ₽", "money", 13), ("bs", "Списано на баланс, ₽", "money", 13),
    ("vat", "НДС, ₽", "money", 12),
    ("bal", "Остаток сейчас (+ долг наш, − аванс выдан), ₽", "money", 14),
    ("future", "Спишется по графику после отчётной даты, ₽", "money", 14),
    ("final", "Останется после графика (без новых оплат), ₽", "money", 14),
    ("why", "Пояснение", "wrap", 44),
    # подробности — свёрнуты, «+» над колонками
    ("method", "Метод учёта", "wrap", 13, 1), ("fn", "Функция начисления", "wrap", 20, 1),
    ("vat_modes", "Режим НДС", "wrap", 12, 1), ("start", "Условия с", "date", 10, 1),
    ("finish", "Условия по", "date", 10, 1), ("ad_last", "График до", "date", 10, 1),
    ("item_name", "Основная статья CF", "wrap", 24, 1),
    ("st_name", "Счёт расчётов (ST)", "wrap", 20, 1), ("pl_name", "Счёт P&L", "wrap", 20, 1),
    ("bs_name", "Счёт BS", "wrap", 20, 1), ("other", "Прочие счета, ₽", "money", 12, 1),
    ("plan_how", "Проверка по условиям", "wrap", 16, 1),
    ("plan_total", "По условиям за весь срок, ₽", "money", 14, 1),
    ("plan_date", "По условиям на отчётную дату, ₽", "money", 14, 1),
    ("plan_diff", "Списано сверх условий (+) / меньше (−), ₽", "money", 14, 1),
]
COND_COLS = [
    ("n", "№ замечания", "id", 8), ("cp", "Контрагент", "wrap", 26),
    ("contract", "Договор", "wrap", 28), ("cid", "ID договора", "id", 8),
    ("cond_id", "ID условия", "id", 8), ("date_start", "С", "date", 10),
    ("date_finish", "По", "date", 10), ("fn", "Функция начисления", "wrap", 20),
    ("method", "Метод учёта", "wrap", 13), ("amount", "Сумма по условию, ₽", "money", 13),
    ("period_n", "Период начисления", "text", 11), ("pay_rule_n", "Период оплаты", "text", 12),
    ("pay_timing_n", "Тип оплаты", "text", 11), ("pay_day", "День оплаты", "id", 8),
    ("mode", "Режим НДС", "text", 12), ("vat_json", "Ставки НДС", "wrap", 22),
    ("pl_n", "Счёт P&L", "wrap", 20), ("sub_pl_n", "Статья P&L", "wrap", 22),
    ("bs_n", "Счёт BS", "wrap", 20), ("sub_bs_n", "Субконто BS", "wrap", 22),
    ("plan_total", "План за срок условия, ₽", "money", 14),
    ("plan_date", "План на отчётную дату, ₽", "money", 14),
    ("params", "Параметры", "wrap", 30),
]
MONTH_COLS = [
    ("n", "№ замечания", "id", 8), ("cp", "Контрагент", "wrap", 26),
    ("contract", "Договор", "wrap", 28), ("cid", "ID договора", "id", 8),
    ("me", "Месяц", "month", 10),
    ("cash", "Деньги, ₽", "money", 13), ("st", "Расчёты, ₽", "money", 13),
    ("pl", "P&L, ₽", "money", 13), ("bs", "Баланс, ₽", "money", 13), ("vat", "НДС, ₽", "money", 12),
    ("other", "Прочие, ₽", "money", 12),
]
NOTES = [
    ("Без договора", "Платежи в Cash Flow без договора — их некуда списать: ни в P&L, ни на "
                     "баланс. Они в «Что проверить» по контрагенту."),
    ("С чего начать", "Лист «Что проверить»: замечания по убыванию суммы. Условия договора — "
                      "на листе «Условия», движение по месяцам — «По месяцам» (фильтр по №)."),
    ("Откуда суммы", "Проводки gl.fact по договору до отчётной даты. Счета договора — как в "
                     "начислениях: расчёты (ST) из договора, P&L и BS — из условий, а если в "
                     "условиях пусто — из договора."),
    ("Остаток сейчас", "Деньги плюс списания по договору. «+» — денег получили больше, чем "
                       "списано (или заплатили меньше): долг перед контрагентом. «−» — заплатили "
                       "больше, чем списано: аванс выдан. При Cash Based — около нуля."),
    ("Итог по графику", "Начисления функций уже рассчитаны до конца условий "
                        "(gl.accural_distribution). «Спишется после отчётной даты» — их сумма "
                        "после отчётной даты, «Останется после графика» — остаток, когда всё "
                        "спишется. Ноль — аванс или долг закроется сам (например, лицензия, "
                        "оплаченная вперёд). Не ноль — реальный долг или аванс к разбору."),
    ("Не проверяется", "Переводы между своими счетами и конвертация (статьи 4…), налоги (125…) и "
                       "WB — их списание идёт не через условия договоров."),
    ("Знаки", "Оплачено и получено — положительные суммы. Списано: + расход, актив, вычет НДС; "
              "− доход, начисленный НДС."),
    ("Cash Based", "Каждый платёж сразу списывается в P&L или на баланс — остаток на расчётах "
                   "должен быть около нуля. По актам (Accural) остаток — нормальный аванс или долг."),
    ("Прочие счета", "Проводки по договору на счета, которых нет ни в договоре, ни в условиях: "
                     "например, условия меняли, а старые начисления остались."),
    ("План списания", "Для условий «фиксированная сумма в месяц» — по графику, как считают "
                      "начисления: сумма × дни / дней в месяце, НДС сверху добавляется. «Всего за "
                      "срок» — с начала по конец условий, «на отчётную дату» — месяцы, начисление "
                      "по которым уже должно быть. Cash Based — сумма оплат. Остальные функции "
                      "(аренда, займы, депозиты) пока без плана."),
    ("Порог", "Суммы меньше 1 000 ₽ — не замечание; расхождение с планом — меньше 2%."),
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
        "month": F(**line, num_format="mm.yyyy", align="center"),
        "money": F(**line, num_format=mp.FMT_MONEY),
        "lbl": F(bold=True, font_color="#" + mp.NAVY_3, **line),
        "bad": F(**line, text_wrap=True, bg_color="#F8D7D3"),
        "warn": F(**line, text_wrap=True, bg_color="#FCEBCF"),
        "ok": F(**line, text_wrap=True, font_color="#" + mp.MUTED),
        "kpi_l": F(bold=True, font_color="#" + mp.NAVY_3, **line),
        "kpi_v": F(bold=True, font_size=11, **line, num_format=mp.FMT_MONEY),
        "tot": F(bold=True, top=1, bottom=1, num_format=mp.FMT_MONEY),
        "tot_l": F(bold=True, top=1, bottom=1),
    }
    sub = (f"Отчётная дата {report_date:%d.%m.%Y} · проводки по договорам до неё · сформировано "
           + pd.Timestamp.now().strftime("%d.%m.%Y %H:%M"))
    WARN = {FLAGS[k][0] for k in ("balance", "outside")}

    def flag_fmt(v):
        if v == "OK" or str(v).startswith("Не проверяется"):
            return fmt["ok"]
        return fmt["warn"] if v in WARN else fmt["bad"]

    def table(name, title, cols, df, total=False, freeze=2):
        ws = wb.add_worksheet(name)
        ws.write(0, 0, title, fmt["title"])
        ws.write(1, 0, sub, fmt["sub"])
        r0 = 3
        for j, (_k, h, _t, w, *lvl) in enumerate(cols):
            ws.write(r0, j, h, fmt["hdr"])
            if lvl:
                ws.set_column(j, j, w, None, {"level": lvl[0], "hidden": True})
            else:
                ws.set_column(j, j, w)
        ws.set_row(r0, 40)
        for i, row in enumerate(df[[c[0] for c in cols]].itertuples(index=False), start=r0 + 1):
            for j, ((k, _h, t, _w, *_l), v) in enumerate(zip(cols, row)):
                if v is None or (not isinstance(v, str) and pd.isna(v)) or v == "":
                    ws.write_blank(i, j, None, fmt["text"])
                elif t == "flag":
                    ws.write(i, j, v, flag_fmt(v))
                elif t in ("money", "id"):
                    v = float(v)
                    if t == "money" and abs(v) < 0.5:   # копейки и хвосты округления — прочерк
                        v = 0.0
                    ws.write_number(i, j, v, fmt[t])
                elif t in ("date", "month"):
                    ws.write_datetime(i, j, pd.Timestamp(v).to_pydatetime(), fmt[t])
                else:
                    ws.write(i, j, str(v), fmt[t])
        last = r0 + len(df)
        if total and len(df):
            ws.write(last + 1, 0, "Итого", fmt["tot_l"])
            for j, (k, _h, t, _w, *_l) in enumerate(cols):
                if t == "money":
                    ws.write_number(last + 1, j, float(df[k].sum()), fmt["tot"])
        ws.autofilter(r0, 0, max(last, r0), len(cols) - 1)
        ws.freeze_panes(r0 + 1, freeze)

    alld, issues = res["all"], res["issues"]
    ws = wb.add_worksheet("Итог")
    ws.set_column(0, 0, 46)
    ws.set_column(1, 2, 16)
    ws.write(0, 0, "Списание договоров: P&L / баланс", fmt["title"])
    ws.write(1, 0, sub, fmt["sub"])
    for r, (lbl, v) in enumerate((("Договоров проверено", len(alld)),
                                  ("Замечаний (лист «Что проверить»)", len(issues)),
                                  ("Сумма вопросов, ₽", float(issues["weight"].sum()))), start=3):
        ws.write(r, 0, lbl, fmt["kpi_l"])
        ws.write_number(r, 1, v, fmt["kpi_v"])
    steps = ("Как работать: 1) «Что проверить» — список задач, сверху самое крупное. "
             "2) По строке: что не так и что сделать. 3) Чтобы посмотреть условия договора — "
             "лист «Условия», движение по месяцам — «По месяцам» (фильтр по № или ID). "
             "«Договоры» — справочник всех договоров по алфавиту.")
    ws.merge_range(6, 0, 6, 2, steps, fmt["wrap"])
    ws.set_row(6, 48)
    r = 8
    for j, h in enumerate(("ЗАМЕЧАНИЕ", "ДОГОВОРОВ", "СУММА ВОПРОСА, ₽")):
        ws.write(r, j, h, fmt["hdr"])
    order = {v[0]: v[2] for v in FLAGS.values()}
    g = alld.groupby("flag").agg(n=("contract", "size"), w=("weight", "sum")).reset_index()
    g = g.sort_values("flag", key=lambda s: s.map(lambda f: order.get(f, 98)))
    for r, row in enumerate(g.itertuples(index=False), start=r + 1):
        ws.write(r, 0, row.flag, flag_fmt(row.flag))
        ws.write_number(r, 1, int(row.n), fmt["id"])
        ws.write_number(r, 2, float(row.w), fmt["money"])

    table("Что проверить", "Что проверить — по убыванию суммы", ISSUE_COLS, issues)
    table("Договоры", "Все договоры по алфавиту — справочник. Подробности (счета, функция, "
          "план) — «+» над колонками справа", ALL_COLS, alld, total=False, freeze=3)
    table("Условия", "Условия договоров", COND_COLS, res["cond"], freeze=3)
    table("По месяцам", "Движение по месяцам — договоры с замечаниями", MONTH_COLS,
          res["months"], freeze=3)

    ws = wb.add_worksheet("Как читать")
    ws.set_column(0, 0, 18)
    ws.set_column(1, 1, 110)
    ws.write(0, 0, "Как читать", fmt["title"])
    for i, (a, b) in enumerate(NOTES, start=2):
        ws.write(i, 0, a, fmt["lbl"])
        ws.write(i, 1, b, fmt["wrap"])
        ws.set_row(i, 36)
    wb.close()
    return buf.getvalue()


def build_contracts_check_workbook(report_date: date) -> tuple[bytes, str]:
    from conns import get_duckdb_conn_with_opt
    with get_duckdb_conn_with_opt(ro=True) as con:
        res = build(report_date, con)
    return to_excel(res, report_date), f"Списание договоров {report_date:%Y%m%d}.xlsx"
