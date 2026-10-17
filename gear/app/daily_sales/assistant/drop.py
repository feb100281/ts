# gear/app/daily_sales/assistant/drop.py
"""Почему изменились продажи: разложение изменения по артикулам на причины.

Продажи «как на сайте WB» до СПП с НДС (без коррекций WB). Для каждого артикула:
    выручка = дни в наличии × штук в день × цена за штуку,
изменение раскладывается точно, без остатка:
    наличие   = (дни₁ − дни₀) × штук в день₀ × цена₀
    цена      = штуки₁ × (цена₁ − цена₀)
    спрос     = дни₁ × (штук в день₁ − штук в день₀) × цена₀
    возвраты  = −(возвраты₁ − возвраты₀)
Изменение спроса относим к вероятной причине: покупателю стало дороже (наша цена или
СПП WB), меньше рекламы, иначе — «спрос и прочее». Артикулы без продаж в базе — новинки.
Разная длина периодов выравнивается: база пересчитывается на длину текущего периода.

Сигналы дня — артикулы, у которых продажи за 7 дней упали к среднему за 4 недели.
"""
from __future__ import annotations

import math
from datetime import date, timedelta

import pandas as pd

BUCKETS = (  # ключ, подпись, значок
    ("stock", "Наличие на складах", "📦"),
    ("price", "Наша цена за штуку", "🏷"),
    ("our", "Цена для покупателя: наша цена", "💸"),
    ("spp", "Цена для покупателя: СПП WB", "🎁"),
    ("ads", "Реклама", "📣"),
    ("ret", "Возвраты", "🔄"),
    ("new", "Новинки и вернувшиеся", "🆕"),
    ("demand", "Спрос и прочее", "🌦"),
)
NAMES = {k: n for k, n, _ in BUCKETS}
PLAIN = {  # понятная подпись: (если минус, если плюс)
    "stock": ("Не было товара на складах", "Товар снова в наличии"),
    "price": ("Снизили цену — каждая штука дешевле", "Подняли цену — каждая проданная штука дороже"),
    "our": ("Подняли цену — купили меньше штук", "Снизили цену — купили больше штук"),
    "spp": ("WB снизил скидку СПП — купили меньше", "WB увеличил скидку СПП — купили больше"),
    "ads": ("Меньше рекламы", "Больше рекламы"),
    "ret": ("Вернули больше товара", "Вернули меньше товара"),
    "new": ("Товары, которых раньше не было в продаже", "Товары, которых раньше не было в продаже"),
    "demand": ("Спрос: покупают меньше без видимой причины", "Спрос: покупают больше без видимой причины"),
}
PRICE_KEYS = ("spp", "our", "price")


def plain(key: str, v: float) -> str:
    return PLAIN[key][0 if v < 0 else 1]
ICONS = {k: i for k, _, i in BUCKETS}

PRICE_STEP = 0.03          # цена для покупателя изменилась заметно — от 3%
ADS_STEP = 0.3             # реклама изменилась заметно — от 30%
SIG_MIN_DAY = 2000         # сигналы: артикул продавал в среднем от 2 тыс ₽ в день
SIG_DROP = 0.3             # сигналы: падение от 30%
SIG_MIN_LOSS = 10000       # сигналы: потеря за неделю от 10 тыс ₽
SIGNALS_IN_DIGEST = True
RESTOCK_MIN_DAY = 300      # «Довезти»: товар продавал хотя бы на 300 ₽ в день
RESTOCK_MIN_MARGIN = 10    # и приносил прибыль после расходов WB от 10% выручки


def _restock_base(df):
    no = df[(df["stock_now"].notna()) & (df["stock_now"] <= 0) & (df["q0"] >= 2)].copy()
    no["day_loss"] = no["v0"].fillna(0) * no["p0"].fillna(0)
    no = no[no["day_loss"] >= RESTOCK_MIN_DAY]
    no["mpct"] = no["m8"].where(no["m8"].notna(), no["pr0"] / no["rv0"].where(no["rv0"] > 0) * 100)
    # прибыль = продажи без НДС × маржа за 8 недель: одна неделя с возвратами не искажает знак
    no["day_profit"] = no["day_loss"] / VAT_K * no["mpct"] / 100
    no["note"] = no["mpct"].isna().map(
        {True: "нет себестоимости в упр. учёте — маржу не посчитать, проверьте карточку", False: ""})
    return no


VAT_K = 1.22                      # продажи до СПП с НДС → без НДС (маржа считается от выручки без НДС)
RESTOCK_MIN_WEEK_QTY = 5          # довозить, если продавался хотя бы 5 шт в неделю
RESTOCK_MIN_MONTH_PROFIT = 10000  # и приносил от 10 тыс ₽ прибыли в месяц


def _profitable(df):
    no = _restock_base(df)
    ok = no[no["mpct"].isna() | (no["mpct"] >= RESTOCK_MIN_MARGIN)].copy()
    ok["month_profit"] = ok["day_profit"] * 30                         # пусто, если маржи нет
    ok["week_qty"] = ok["v0"].fillna(0) * 7
    # без маржи судим по продажам: как если бы маржа была минимальной (10%)
    est = ok["month_profit"].fillna(ok["day_loss"] * 30 / VAT_K * RESTOCK_MIN_MARGIN / 100)
    ok["big"] = (est >= RESTOCK_MIN_MONTH_PROFIT) & (ok["week_qty"] >= RESTOCK_MIN_WEEK_QTY)
    return ok.assign(rank=est).sort_values("rank", ascending=False)


def restock(df):
    """Довезти: нет на складах, прибыльный и продавался заметно; сверху — больше прибыли в месяц."""
    ok = _profitable(df)
    return ok[ok["big"]]


def restock_small(df):
    """Прибыльный, но продавался мало — довозить не в первую очередь."""
    ok = _profitable(df)
    return ok[~ok["big"]]


def restock_skip(df):
    """Не довозить: продавался в минус или почти без прибыли (распродажа, демпинг)."""
    no = _restock_base(df)
    return no[no["mpct"].notna() & (no["mpct"] < RESTOCK_MIN_MARGIN)].sort_values("mpct")
DRR_HIGH = 9               # ДРР выше — «плохо» по шкале отчёта о рекламе (до 7% отлично, 7–9% нормально)


def _drr_high() -> float:
    """Порог «плохо» — из шкалы ДРР отчёта о рекламе, чтобы не расходиться."""
    try:
        from ..ad_campaigns_report import DRR_HIGH_THRESHOLD
        return float(DRR_HIGH_THRESHOLD)
    except Exception:
        return DRR_HIGH
MARGIN_WEEKS = 8           # маржа товара «в обычное время» — за 8 недель
LOW_STOCK_DAYS = 7         # остатка меньше чем на неделю — рекламу можно не крутить   # блок сигналов в ежедневной рассылке (если есть что показать)

COLS = {"Продажи, шт": "q", "Возвраты, шт": "rq", "До СПП: продажи, ₽": "s",
        "До СПП: возвраты, ₽": "r", "После СПП: продажи, ₽": "bs"}
INFO = {"Бренд": "brand", "Категория": "category", "Артикул продавца": "sa", "Наименование": "title"}


# ---------------------------------------------------------------- данные
def _query(sql: str, params: dict) -> pd.DataFrame:
    from conns import get_duckdb_conn_with_opt
    try:
        with get_duckdb_conn_with_opt(ro=True) as con:
            return con.execute(sql, params).df()
    except Exception as e:                     # без остатков/рекламы разбор всё равно считается
        print(f"[drop] запрос: {type(e).__name__}: {e}", flush=True)
        return pd.DataFrame()


def _sales(a: date, b: date) -> pd.DataFrame:
    """Продажи по артикулам за период + число дней с продажами."""
    from ..wb_sales_export import fetch
    df = fetch(a, b, "nm_day", [])
    if df.empty:
        return pd.DataFrame(columns=["nm", *COLS.values(), "dsold", *INFO.values()])
    df = df.rename(columns={**COLS, **INFO, "Артикул WB": "nm"})
    df["sold_day"] = (df["q"] > 0).astype(int)
    agg = {**{c: "sum" for c in COLS.values()}, "sold_day": "sum", **{c: "first" for c in INFO.values()}}
    out = df.groupby("nm", as_index=False).agg(agg).rename(columns={"sold_day": "dsold"})
    out["nm"] = out["nm"].astype("int64")
    return out


def _stock_days(a: date, b: date) -> tuple[pd.DataFrame, int]:
    """Дни в наличии (склады WB + FBS) по артикулам и число дней со снимками остатков."""
    df = _query("""
        WITH x AS (
            SELECT date_from::DATE AS d, nm_id, SUM(COALESCE(quantity, 0)) AS q
            FROM stocks.unpacked_stocks WHERE date_from::DATE BETWEEN $a AND $b GROUP BY 1, 2
            UNION ALL
            SELECT date_from::DATE, nm_id, SUM(COALESCE(quantity, 0))
            FROM stocks.unpacked_fbs_stocks WHERE date_from::DATE BETWEEN $a AND $b GROUP BY 1, 2
        ), y AS (SELECT d, nm_id, SUM(q) AS q FROM x GROUP BY 1, 2)
        SELECT nm_id AS nm, COUNT(*) FILTER (WHERE q > 0) AS din,
               (SELECT COUNT(DISTINCT d) FROM y) AS seen
        FROM y GROUP BY nm_id""", {"a": a, "b": b})
    if df.empty:
        return pd.DataFrame(columns=["nm", "din"]), 0
    seen = int(df["seen"].iloc[0] or 0)
    df["nm"] = df["nm"].astype("int64")
    return df[["nm", "din"]], seen


def _stock_now(b: date) -> pd.DataFrame:
    """Остаток на последнюю загруженную дату (текущий день): склады WB + FBS."""
    df = _query("""
        WITH d AS (SELECT MAX(date_from::DATE) AS d FROM stocks.unpacked_stocks WHERE $b IS NOT NULL),
        x AS (
            SELECT nm_id, SUM(COALESCE(quantity, 0)) AS q FROM stocks.unpacked_stocks
            WHERE date_from::DATE = (SELECT d FROM d) GROUP BY 1
            UNION ALL
            SELECT nm_id, SUM(COALESCE(quantity, 0)) FROM stocks.unpacked_fbs_stocks
            WHERE date_from::DATE = (SELECT d FROM d) GROUP BY 1
        )
        SELECT nm_id AS nm, SUM(q) AS stock, (SELECT d FROM d) AS sd FROM x GROUP BY 1""", {"b": b})
    if df.empty:
        return pd.DataFrame(columns=["nm", "stock"])
    _STOCK_DATE["d"] = df["sd"].iloc[0]
    df = df.drop(columns=["sd"])
    df["nm"] = df["nm"].astype("int64")
    return df


_STOCK_DATE: dict = {}


def stock_label() -> str:
    d = _STOCK_DATE.get("d")
    try:
        return f"Остаток на {pd.Timestamp(d):%d.%m.%Y}, шт" if d is not None else "Остаток сейчас, шт"
    except Exception:
        return "Остаток сейчас, шт"


def cover(r, n1: int):
    """На сколько дней хватит остатка при нынешних продажах (если продаж нет — при прошлых)."""
    st = r.get("stock_now")
    if st is None or st != st:
        return None
    daily = (r["q1"] if r["q1"] > 0 else r["q0"]) / max(n1, 1)
    return round(st / daily) if daily > 0 else None


def _ads(a: date, b: date) -> pd.DataFrame:
    df = _query("""
        SELECT nm_id AS nm, SUM(spend_rub) AS ad, SUM(revenue_rub) AS adrev
        FROM ads.unpacked_ad_campaigns_stats_by_nm
        WHERE date BETWEEN $a AND $b GROUP BY 1""", {"a": a, "b": b})
    if df.empty:
        return pd.DataFrame(columns=["nm", "ad", "adrev"])
    df["nm"] = df["nm"].astype("int64")
    return df


# ---------------------------------------------------------------- разложение
def analyze(a: date, b: date, pa: date, pb: date) -> dict | None:
    n1, n0 = (b - a).days + 1, (pb - pa).days + 1
    k = n1 / n0
    cur, old = _sales(a, b), _sales(pa, pb)
    if cur.empty and old.empty:
        return None
    st1, seen1 = _stock_days(a, b)
    st0, seen0 = _stock_days(pa, pb)
    stock_known = seen1 > 0 and seen0 > 0
    m = cur.merge(old, on="nm", how="outer", suffixes=("1", "0"))
    for c in INFO.values():
        m[c] = m[c + "1"].combine_first(m[c + "0"]).fillna("")
    m = (m.merge(st1.rename(columns={"din": "din1"}), on="nm", how="left")
          .merge(st0.rename(columns={"din": "din0"}), on="nm", how="left")
          .merge(_stock_now(b), on="nm", how="left")
          .merge(_ads(a, b).rename(columns={"ad": "ad1", "adrev": "adrev1"}), on="nm", how="left")
          .merge(_ads(pa, pb).rename(columns={"ad": "ad0", "adrev": "adrev0"}), on="nm", how="left"))
    num_cols = [c + s for c in (*COLS.values(), "dsold") for s in ("1", "0")] + ["din1", "din0", "ad1", "ad0", "adrev1", "adrev0"]
    m[num_cols] = m[num_cols].fillna(0).astype(float)

    rows = []
    for r in m.itertuples(index=False):
        q0, s0, rr0, bs0 = r.q0 * k, r.s0 * k, r.r0 * k, r.bs0 * k
        q1, s1, rr1, bs1 = r.q1, r.s1, r.r1, r.bs1
        if stock_known:
            d1 = max(r.din1 / seen1 * n1, r.dsold1)
            d0 = max(r.din0 / seen0 * n0, r.dsold0)
        else:
            d1, d0 = float(n1), float(n0)
        d1, d0 = min(d1, n1), min(d0, n0) * k
        a0, a1 = r.ad0 * k, r.ad1
        e = dict.fromkeys(NAMES, 0.0)
        u = dict.fromkeys(NAMES, 0.0)                              # то же в штуках
        e["ret"] = -(rr1 - rr0)
        u["ret"] = -(r.rq1 - r.rq0 * k)
        p0 = s0 / q0 if q0 > 0 else None
        p1 = s1 / q1 if q1 > 0 else None
        dpb = x = y = None
        if q0 <= 0:
            e["new"] = s1 - s0
            u["new"] = q1 - q0
            why = "new"
        else:
            v0 = q0 / d0 if d0 > 0 else 0.0
            e["stock"] = (d1 - d0) * v0 * p0
            if q1 > 0:
                e["price"] = q1 * (p1 - p0)
                dem = d1 * (q1 / d1 - v0) * p0 if d1 > 0 else -d0 * v0 * p0 - e["stock"]
                b0, b1 = bs0 / q0, bs1 / q1
                if b0 > 0 and b1 > 0:
                    x = math.log(p1 / p0)                          # наша цена
                    y = math.log((b1 / p1) / (b0 / p0))            # СПП: доля цены, которую платит покупатель
                    dpb = b1 / b0 - 1
            else:
                dem = -d1 * v0 * p0
            if dem < 0 and dpb is not None and dpb >= PRICE_STEP:
                key = "our" if x >= y else "spp"
            elif dem > 0 and dpb is not None and dpb <= -PRICE_STEP:
                key = "our" if x <= y else "spp"
            elif dem < 0 and a0 > 0 and a1 < (1 - ADS_STEP) * a0:
                key = "ads"
            elif dem > 0 and a1 > (1 + ADS_STEP) * a0 and a1 > 0:
                key = "ads"
            else:
                key = "demand"
            e[key] = dem
            u[key] = dem / p0
            u["stock"] = e["stock"] / p0
            delta = sum(e.values())
            why = (min if delta < 0 else max)(e, key=e.get)
        net0, net1 = s0 - rr0, s1 - rr1
        rows.append({
            "nm": int(r.nm), "brand": r.brand, "category": r.category, "sa": r.sa, "title": r.title,
            "net0": net0, "net1": net1, "delta": net1 - net0, **e, "why": why,
            "d0": d0 / k, "d1": d1, "n0": n0, "q0": q0, "q1": q1, "p0": p0, "p1": p1,
            "v0": q0 / d0 if d0 > 0 else None, "v1": q1 / d1 if d1 > 0 else None,
            "spp0": (1 - bs0 / s0) * 100 if s0 > 0 else None, "spp1": (1 - bs1 / s1) * 100 if s1 > 0 else None,
            "dpb": dpb * 100 if dpb is not None else None,
            "our_pct": (math.exp(x) - 1) * 100 if x is not None else None,
            **{"u_" + key: v for key, v in u.items()}, "s0": s0, "bs0": bs0, "s1": s1, "bs1": bs1,
            "adrev0": r.adrev0, "drr0": r.ad0 / r.adrev0 * 100 if r.adrev0 > 0 else None,   # как в записке: расход / заказы с рекламы
            "ad0": a0, "ad1": a1, "stock_now": float(r.stock) if r.stock == r.stock else None})
    df = pd.DataFrame(rows)
    if df.empty:
        return None
    df = _with_margin(df, a, b, pa, pb, k)
    df["kk"] = k
    tot = {key: float(df[key].sum()) for key in NAMES}
    tot_u = {key: float(df["u_" + key].sum()) for key in NAMES}
    q0, q1 = float(df["q0"].sum()), float(df["q1"].sum())
    avg = {"p0": df["s0"].sum() / q0 if q0 else None, "p1": df["s1"].sum() / q1 if q1 else None,
           "b0": df["bs0"].sum() / q0 if q0 else None, "b1": df["bs1"].sum() / q1 if q1 else None,
           "q0": q0, "q1": q1}
    return {"a": a, "b": b, "pa": pa, "pb": pb, "n1": n1, "n0": n0, "k": k, "stock_known": stock_known,
            "tot_u": tot_u, "avg": avg,
            "base": float(df["net0"].sum()), "cur": float(df["net1"].sum()), "tot": tot,
            "df": df.sort_values("delta")}


def _with_margin(df, a, b, pa, pb, k):
    """Прибыль после расходов WB по методике дашборда (упр. учёт) — было и стало."""
    try:
        from .menu import margin
        m1, m0 = margin(a, b, "nm"), margin(pa, pb, "nm")
    except Exception as e:
        print(f"[drop] маржа: {type(e).__name__}: {e}", flush=True)
        df["pr0"] = df["pr1"] = df["rv0"] = df["rv1"] = df["m8"] = float("nan")
        return df
    def prep(m, mult, sfx):
        m = m.groupby("nm_id", as_index=False)[["rev", "res"]].sum()
        m["nm_id"] = pd.to_numeric(m["nm_id"], errors="coerce")
        m = m.dropna(subset=["nm_id"]).astype({"nm_id": "int64"})
        return m.rename(columns={"nm_id": "nm", "rev": "rv" + sfx, "res": "pr" + sfx}).assign(
            **{"rv" + sfx: lambda t: t["rv" + sfx] * mult, "pr" + sfx: lambda t: t["pr" + sfx] * mult})
    out = df.merge(prep(m1, 1, "1"), on="nm", how="left").merge(prep(m0, k, "0"), on="nm", how="left")
    try:
        m8 = prep(margin(b - timedelta(days=7 * MARGIN_WEEKS - 1), b, "nm"), 1, "8")
        m8["m8"] = m8["pr8"] / m8["rv8"].where(m8["rv8"] > 0) * 100
        out = out.merge(m8[["nm", "m8"]], on="nm", how="left")
    except Exception as e:
        print(f"[drop] маржа 8 недель: {type(e).__name__}: {e}", flush=True)
        out["m8"] = float("nan")
    return out


def ads_ok(r, n1: int = 7) -> str | None:
    """Почему сократить рекламу было разумно (или None)."""
    from .menu import num
    st = r.get("stock_now")
    daily = (r["q0"] or 0) / max(n1, 1)
    if st is not None and st == st and (st <= 3 or st < daily * LOW_STOCK_DAYS):
        return f"остаток всего {num(st)} шт — рекламировать почти нечего"
    m8 = r.get("m8")
    if m8 is not None and m8 == m8 and m8 < RESTOCK_MIN_MARGIN:
        return f"маржа {num(m8)}% — реклама съедала бы прибыль"
    if (r.get("ad0") or 0) > 0 and not (r.get("adrev0") or 0):
        return "реклама не приносила заказов"
    drr = r.get("drr0")
    if drr is not None and drr == drr and drr > _drr_high():
        return f"ДРР был {num(drr, 1)}% — выше {num(_drr_high())}%, по нашей шкале это плохо"
    return None


def ads_cut(df, n1: int):
    """Артикулы, где рекламу сократили от 30%, и оценка: оправданно (причина) или нет (None)."""
    off = df[(df["ad0"] > 0) & (df["ad1"] < (1 - ADS_STEP) * df["ad0"])].copy()
    off["ok"] = [ads_ok(r, n1) for _, r in off.iterrows()] if len(off) else []
    off["ok"] = off["ok"].astype(object).where(off["ok"].notna(), None)
    return off


def _ok_kind(t: str) -> str:
    return ("мало остатка" if t.startswith("остаток") else "низкая маржа" if t.startswith("маржа")
            else "не было заказов" if t.startswith("реклама не") else "дорогая реклама")


def profit(r) -> str:
    """Как изменилась прибыль по артикулу (упр. учёт)."""
    from .menu import rub
    p0, p1 = r.get("pr0"), r.get("pr1")
    if p0 != p0 or p1 != p1 or p0 is None or p1 is None:
        return ""
    dp = p1 - p0
    if abs(dp) < 1000:
        return " · прибыль почти не изменилась"
    return f" · прибыль {'▲ +' if dp > 0 else '▼ −'}{rub(abs(dp))}" + (" ✅" if dp > 0 else "")


def _group_profit(part) -> tuple[float, float] | None:
    p = part.dropna(subset=["pr0", "pr1"])
    if p.empty:
        return None
    return float(p["delta"].sum()), float((p["pr1"] - p["pr0"]).sum())


# ---------------------------------------------------------------- подписи
def _pct(v, d=0):
    from .menu import num
    return ("+" if v > 0 else "−" if v < 0 else "") + num(abs(v), d) + "%"


def reason(r, n1: int) -> str:
    """Короткое объяснение главной причины по артикулу."""
    from .menu import num
    w = r["why"]
    if w == "stock":
        s = f"в наличии {num(r['d1'])} из {n1} дн. (было {num(r['d0'])} из {r['n0']})"
        if r["stock_now"] is not None and r["stock_now"] <= 0:
            s += " · сейчас 0 шт"
            m8 = r.get("m8")
            if m8 is not None and m8 == m8 and m8 < RESTOCK_MIN_MARGIN:
                s += f" · маржа {num(m8)}% — довозить не нужно"
        return s
    if w in ("our", "spp") and r["dpb"] is not None:
        parts = []
        if r["our_pct"] is not None and abs(r["our_pct"]) >= 1:
            parts.append(f"наша цена {_pct(r['our_pct'])}")
        if r["spp0"] is not None and r["spp1"] is not None and abs(r["spp1"] - r["spp0"]) >= 0.5:
            dd = r["spp1"] - r["spp0"]
            parts.append(f"СПП {'+' if dd > 0 else '−'}{num(abs(dd), 1)} п.п.")
        return f"покупателю {'дороже' if r['dpb'] > 0 else 'дешевле'} на {num(abs(r['dpb']))}%" + (
            f" ({', '.join(parts)})" if parts else "")
    if w == "ads":
        ok = ads_ok(r, n1)
        tail = f" — это нормально: {ok} ✅" if ok else " — товар есть, стоит вернуть рекламу ⚠️"
        if r["ad0"] > 0 and r["ad1"] < 1:
            return f"рекламу выключили (было {num(r['ad0'] / 1000)} тыс ₽){tail}"
        if r["ad0"] > 0:
            return f"реклама {_pct((r['ad1'] / r['ad0'] - 1) * 100)} ({num(r['ad1'] / 1000)} тыс ₽){tail}"
        return f"реклама {num(r['ad1'] / 1000)} тыс ₽ (раньше не было)"
    if w == "price" and r["p0"] and r["p1"]:
        return f"цена до СПП {_pct((r['p1'] / r['p0'] - 1) * 100)}"
    if w == "ret":
        return "больше возвратов" if r["ret"] < 0 else "меньше возвратов"
    if w == "new":
        return "новинка или вернулся в продажу"
    if r["v0"] and r["v1"] is not None:
        return f"штук в день {_pct((r['v1'] / r['v0'] - 1) * 100)} при той же цене и наличии"
    return "спрос"


def _who(r) -> str:
    from .menu import esc
    name = r["sa"] or f"nm {r['nm']}"
    title = str(r["title"] or "").strip()
    title = title if len(title) <= 34 else title[:33] + "…"
    head = f"<b>{esc(title)}</b> · " if title else ""
    return head + (f"{esc(name)} · {esc(r['brand'])}" if r["brand"] else esc(name))


def chart_reasons(tot: dict, title: str, sub: str) -> bytes:
    """Вклад причин: рост вправо, падение влево (млн или тыс ₽)."""
    from . import digest_charts as ch
    rows = sorted([(NAMES[k], v) for k, v in tot.items() if abs(v) >= 1], key=lambda x: x[1])
    plt = ch._plt()
    fig, ax = plt.subplots(figsize=(10.8, 1.7 + 0.85 * len(rows)), dpi=100)
    mx = max((abs(v) for _, v in rows), default=1) or 1
    unit, div = ("млн ₽", 1e6) if mx >= 1e6 else ("тыс ₽", 1e3)
    for i, (name, v) in enumerate(rows):
        yy = len(rows) - 1 - i
        ax.barh(yy, v, height=0.6, color=ch.GREEN if v > 0 else ch.WARM)
        lab = ("+" if v > 0 else "−") + ch._num(abs(v) / div, 1 if div == 1e6 else 0) + " " + unit
        ax.text(v + (mx * 0.03 if v > 0 else -mx * 0.03), yy, lab, va="center",
                ha="left" if v > 0 else "right", fontsize=14, fontweight="bold", color=ch.INK)
        ax.text(-mx * 0.04 if v > 0 else mx * 0.04, yy, name, va="center",
                ha="right" if v > 0 else "left", fontsize=13.5, color=ch.INK)
    ax.axvline(0, color=ch.AXIS, lw=1)
    ax.set_xlim(-mx * 2.1, mx * 2.1)
    ax.set_ylim(-0.7, len(rows) - 0.3)
    ax.axis("off")
    h = fig.get_figheight()
    ch._head(fig, title, sub, y=1 - 0.42 / h)
    fig.subplots_adjust(left=0.03, right=0.97, top=1 - 1.3 / h, bottom=0.03)
    return ch._png(plt, fig)


# ---------------------------------------------------------------- отчёт «Почему изменились продажи»
TOP = 8


def report(a: date, b: date) -> dict | None:
    from .menu import _files_kb, _photo, chg, esc, num, prev_range, rub, span, table
    pa, pb = prev_range(a, b)
    res = analyze(a, b, pa, pb)
    if not res or not (res["base"] or res["cur"]):
        return None
    _CACHE[(a, b)] = res
    base, cur, tot, df = res["base"], res["cur"], res["tot"], res["df"]
    d = cur - base
    down = d < 0
    lines = [f"<b>🔎 Почему {'упали' if down else 'выросли'} продажи · {span(a, b)}</b>",
             f"<i>к {span(pa, pb)} · до СПП с НДС, без коррекций WB"
             + (" · прошлый период пересчитан на ту же длину" if res["k"] != 1 else "") + "</i>", "",
             f"Было: <b>{rub(base)}</b> → стало: <b>{rub(cur)}</b>",
             f"Изменение: <b>{'+' if d >= 0 else '−'}{rub(abs(d))}</b>  {chg(cur, base)}",
             ""]
    lim = max(abs(d) * 0.02, 1000)
    sg = lambda v: ("+" if v > 0 else "−") + rub(abs(v))  # noqa: E731
    prices = sum(tot[k] for k in PRICE_KEYS)
    groups = [("prices", prices)] + [(k, v) for k, v in tot.items() if k not in PRICE_KEYS]
    groups = [g for g in groups if abs(g[1]) >= lim]
    groups.sort(key=lambda g: g[1] if down else -g[1])
    av, tu = res["avg"], res["tot_u"]
    if groups:
        k0, v0 = groups[0]
        what = "цены для покупателя" if k0 == "prices" else plain(k0, v0).lower()
        lines.append(f"Главное: <b>{what}</b> — {sg(v0)} из {sg(d)}.")
    if av["b0"] and av["b1"] and av["p0"] and av["p1"]:
        spp0, spp1 = (1 - av["b0"] / av["p0"]) * 100, (1 - av["b1"] / av["p1"]) * 100
        lines += [f"Средняя цена для покупателя: {rub(av['b0'])} → <b>{rub(av['b1'])}</b> ({chg(av['b1'], av['b0'])})",
                  f"Наша цена до СПП: {rub(av['p0'])} → <b>{rub(av['p1'])}</b> ({chg(av['p1'], av['p0'])}) · "
                  f"СПП {num(spp0, 1)}% → <b>{num(spp1, 1)}%</b>",
                  f"Продано штук: {num(av['q0'])} → <b>{num(av['q1'])}</b> ({chg(av['q1'], av['q0'])})"]
    pp = df.dropna(subset=["pr0", "pr1"])
    if not pp.empty:
        P0, P1 = float(pp["pr0"].sum()), float(pp["pr1"].sum())
        lines.append(f"Прибыль после расходов WB*: {rub(P0)} → <b>{rub(P1)}</b> ({chg(P1, P0)})")
    lines += ["", "<b>Из чего сложилось</b> — сколько это дало продажам, ₽"]
    pcs = lambda v: f" ({'+' if v > 0 else '−'}{num(abs(v))} шт)" if abs(v) >= 1 else ""  # noqa: E731
    for key, v in groups:
        if key != "prices":
            lines.append(f"{ICONS[key]} {plain(key, v)} — <b>{sg(v)}</b>{pcs(tu[key])}")
            continue
        lines.append(f"💰 Цены — <b>{sg(v)}</b>")
        for k in PRICE_KEYS:
            if abs(tot[k]) >= lim:
                lines.append(f"    · {plain(k, tot[k])} — {sg(tot[k])}{pcs(tu[k])}")
    worst = df.head(TOP) if down else df.sort_values("delta", ascending=False).head(TOP)
    worst = worst[(worst["delta"] < 0) if down else (worst["delta"] > 0)]
    if len(worst):
        lines += ["", f"<b>Где {'потеряли' if down else 'выросли'} больше всего</b>"]
        for _, r in worst.iterrows():
            lines.append(f"• {_who(r)} — <b>{'+' if r['delta'] > 0 else '−'}{rub(abs(r['delta']))}</b>"
                         f" · {ICONS[r['why']]} {reason(r, res['n1'])}{profit(r)}")
    checks = []
    up = df[df["our_pct"].fillna(0) >= PRICE_STEP * 100]
    g = _group_profit(up)
    if g and len(up):
        ds, dp = g
        checks.append(f"🏷 Подняли цену на <b>{num(len(up))}</b> арт.: продажи {'+' if ds >= 0 else '−'}{rub(abs(ds))}, "
                      f"прибыль {'+' if dp >= 0 else '−'}{rub(abs(dp))} — "
                      + ("повышение окупилось ✅" if dp >= 0 else "повышение не окупилось ⚠️"))
    off = ads_cut(df, res["n1"])
    if len(off):
        good, bad = off[off["ok"].notna()], off[off["ok"].isna()]
        line = f"📣 Сократили рекламу (от 30%) на <b>{num(len(off))}</b> арт."
        if len(good):
            kinds = good["ok"].map(_ok_kind).value_counts()
            line += (f"\n    · <b>{num(len(good))}</b> — правильно ✅: "
                     + ", ".join(f"{k} — {num(v)}" for k, v in kinds.items()))
        if len(bad):
            g = _group_profit(bad)
            line += (f"\n    · <b>{num(len(bad))}</b> — зря: товар есть, маржа нормальная, реклама окупалась")
            if g:
                ds, dp = g
                line += (f". По ним продажи {'+' if ds >= 0 else '−'}{rub(abs(ds))} "
                         f"({'+' if bad['q1'].sum() >= bad['q0'].sum() else '−'}"
                         f"{num(abs(bad['q1'].sum() - bad['q0'].sum()))} шт), прибыль "
                         f"{'+' if dp >= 0 else '−'}{rub(abs(dp))} — "
                         + ("но прибыль выросла, экономия оправдана ✅" if dp >= 0 else "стоит вернуть рекламу ⚠️"))
        checks.append(line)
    if checks:
        lines += ["", "<b>Правильно ли сделали — по прибыли*</b>"] + checks
    todo = _todo(df, res)
    if todo:
        lines += ["", "<b>Что сделать</b>"] + todo
    if not res["stock_known"]:
        lines += ["", "<i>Нет данных об остатках за период — наличие не учтено.</i>"]
    lines += ["", "<i>Как читать: каждая строка — на сколько рублей эта причина изменила продажи, вместе они "
                  "дают общее изменение. Продажи считаем за вычетом возвратов, поэтому «вернули меньше» — плюс. "
                  "«Товары, которых раньше не было в продаже» — новинки и товары, вернувшиеся после паузы. "
                  "Цена или реклама считаются причиной, если изменились заметно: цена от 3%, реклама от 30%. "
                  "Подробно по каждому артикулу — в Excel.</i>",
              "<i>* Прибыль — управленческий учёт, как в дашборде продаж: выручка без НДС минус себестоимость "
              "(FIFO), комиссия и расходы WB.</i>"]
    photo = _photo(lambda: chart_reasons(tot, f"{'−' if down else '+'}{rub(abs(d))} к прошлому периоду",
                                         f"из чего сложилось · {span(a, b)} к {span(pa, pb)}"))
    rows = sorted([(NAMES[key], v) for key, v in tot.items() if abs(v) >= lim], key=lambda x: x[1])
    chart = {"type": "hbar", "title": "Из чего сложилось изменение, ₽",
             "labels": [n for n, _ in rows], "values": [round(v) for _, v in rows]}
    top_t = table("Артикулы", ["Артикул", "Бренд", "Изменение", "Причина"],
                  [[r["sa"] or str(r["nm"]), r["brand"], r["delta"], f"{NAMES[r['why']]}: {reason(r, res['n1'])}"]
                   for _, r in worst.iterrows()], ["text", "text", "rub", "text"])
    files = (("xl", "Excel: разбор по артикулам"), ("el", "Excel: реакция на цену"))
    return {"text": "\n".join(lines), "photo": photo, "auto": "xl", "chart": chart, "charts": [chart],
            "files": files, "tables": [top_t], "kb": _files_kb("z", a, b, files)}


def _todo(df, res) -> list[str]:
    from .menu import num, rub
    out = []
    no, skip = restock(df), restock_skip(df)
    if len(no):
        prof = no["day_profit"].dropna()
        nm_ = int(no["mpct"].isna().sum())
        out.append(f"📦 Довезти: <b>{num(len(no))}</b> артикулов без остатка — прибыльные и продавались от "
                   f"{RESTOCK_MIN_WEEK_QTY} шт в неделю. Теряем около {rub(no['day_loss'].sum() * 30)} продаж и "
                   f"{rub(no['month_profit'].sum())} прибыли в месяц, лист «Довезти» (сверху — больше прибыли)."
                   + (f" У {num(nm_)} нет себестоимости — маржу не посчитать, см. примечание." if nm_ else ""))
    small = restock_small(df)
    if len(small):
        out.append(f"🐢 Мало продавались: <b>{num(len(small))}</b> прибыльных артикулов без остатка, но меньше "
                   f"{RESTOCK_MIN_WEEK_QTY} шт в неделю или меньше {rub(RESTOCK_MIN_MONTH_PROFIT)} прибыли в месяц — "
                   "не в первую очередь, лист «Мало продавались».")
    if len(skip):
        out.append(f"🚫 Не довозить: <b>{num(len(skip))}</b> артикулов без остатка были убыточными или почти без "
                   f"прибыли (маржа ниже {RESTOCK_MIN_MARGIN}%) — в «Довезти» их нет, список на листе «Не довозить».")
    pr = df[(df["our"] + df["spp"]) < 0]
    if len(pr):
        out.append(f"💸 Цены: <b>{num(len(pr))}</b> артикулов, где покупателю стало дороже и штуки упали — "
                   f"{rub(-(pr['our'] + pr['spp']).sum())}, лист «Цена».")
    off = ads_cut(df, res["n1"])
    bad = off[off["ok"].isna()] if len(off) else off
    if len(bad):
        out.append(f"📣 Вернуть рекламу: <b>{num(len(bad))}</b> арт. — сократили зря (товар есть, маржа нормальная, "
                   f"реклама окупалась), лист «Реклама», они сверху.")
    return out


_CACHE: dict = {}


def _res(a, b):
    from .menu import prev_range
    res = _CACHE.get((a, b))
    if res is None:
        pa, pb = prev_range(a, b)
        res = analyze(a, b, pa, pb)
    return res


def file(code: str, a: date, b: date):
    from .menu import XLSX, _book, num, span
    if code == "el":
        return file_elasticity(a, b)
    res = _res(a, b)
    if not res:
        return None
    df, n1 = res["df"], res["n1"]
    sub = f"{span(a, b)} к {span(res['pa'], res['pb'])} · до СПП с НДС"
    base, d = res["base"], res["cur"] - res["base"]
    s_rows = [["Продажи в прошлом периоде", base, None]]
    s_rows += [[plain(k, v), v, v / d * 100 if d else None]
               for k, v in sorted(res["tot"].items(), key=lambda x: x[1]) if abs(v) >= 1]
    s_rows += [["Изменение продаж, всего", d, 100.0], ["Продажи в текущем периоде", res["cur"], None]]
    pp = df.dropna(subset=["pr0", "pr1"])
    if not pp.empty:
        s_rows += [["Прибыль после расходов WB, прошлый период*", float(pp["pr0"].sum()), None],
                   ["Прибыль после расходов WB, текущий период*", float(pp["pr1"].sum()), None]]
    head = ["Бренд", "Категория", "Артикул продавца", "Артикул WB", "Наименование"]
    info = lambda r: [r["brand"], r["category"], r["sa"], r["nm"], r["title"]]  # noqa: E731
    nz = lambda v: None if v != v else v  # noqa: E731
    main = [info(r) + [r["q0"], r["q1"], r["net0"], r["net1"], r["delta"], nz(r["pr0"]), nz(r["pr1"]),
                       nz(r["pr1"] - r["pr0"]), *[r[k] for k in NAMES], plain(r["why"], r[r["why"]]),
                       reason(r, n1), r["d0"], r["d1"], r["stock_now"], cover(r, n1), r["p0"], r["p1"], r["spp0"], r["spp1"],
                       r["ad0"], r["ad1"]] for _, r in df.iterrows()]
    main_cols = head + ["Продано было, шт", "Продано стало, шт", "Продажи было, ₽", "Продажи стало, ₽", "Изменение продаж, ₽", "Прибыль было*, ₽",
                        "Прибыль стало*, ₽", "Изменение прибыли*, ₽", *[NAMES[k] + ", ₽" for k in NAMES],
                        "Главная причина", "Пояснение", "Дней в наличии (было)", "Дней в наличии (стало)",
                        stock_label(), "Хватит остатка, дней", "Наша цена до СПП было, ₽", "Наша цена до СПП стало, ₽", "СПП было, %",
                        "СПП стало, %", "Реклама было, ₽", "Реклама стало, ₽"]
    no = restock(df)
    nz = lambda v: None if v != v else v  # noqa: E731
    rs_row = lambda r: info(r) + [nz(r["month_profit"]), nz(r["mpct"]), r["day_loss"] * 30,  # noqa: E731
                                  round(r["week_qty"], 1), r["p0"], r["stock_now"], r["d0"], r["d1"], r["note"]]
    no_rows = [rs_row(r) for _, r in no.iterrows()]
    sm_rows = [rs_row(r) for _, r in restock_small(df).iterrows()]
    sk = restock_skip(df)
    sk_rows = [info(r) + [nz(r["mpct"]), nz(r["day_profit"] * 30), r["day_loss"] * 30,
                          round(r["v0"] * 7, 1) if r["v0"] == r["v0"] and r["v0"] else 0, r["p0"], r["net0"]]
               for _, r in sk.iterrows()]
    bp = lambda r, i: (r["bs" + i] / r["q" + i]) if r["q" + i] else None  # noqa: E731
    pr = df[(df["our"] + df["spp"]) < 0].assign(x=lambda t: t["our"] + t["spp"],
                                                 xu=lambda t: t["u_our"] + t["u_spp"]).sort_values("x")
    pr_rows = [info(r) + [r["x"], r["xu"], r["q0"], r["q1"], bp(r, "0"), bp(r, "1"), r["dpb"], r["p0"], r["p1"],
                          r["our_pct"], r["spp0"], r["spp1"], r["stock_now"], cover(r, n1),
                          nz(r["pr1"] - r["pr0"])] for _, r in pr.iterrows()]
    ad = ads_cut(df, n1)
    if len(ad):
        ad = ad.assign(bad=ad["ok"].isna()).sort_values(["bad", "delta"], ascending=[False, True])
    ad_rows = []
    for _, r in ad.iterrows():
        ok = r["ok"] if isinstance(r["ok"], str) else None
        ad_rows.append(info(r) + [("правильно: " + ok) if ok else "зря — стоит вернуть рекламу",
                                  r["ad0"], r["ad1"], nz(r["drr0"]), r["q0"], r["q1"], r["delta"], r["ads"],
                                  r["stock_now"], cover(r, n1), nz(r["m8"]), nz(r["pr1"] - r["pr0"])])
    rs_cols = ["Прибыль в месяц*, ₽", f"Маржа за {MARGIN_WEEKS} недель*, %", "Продажи в месяц, ₽",
               "Продавали шт в неделю", "Цена до СПП, ₽", stock_label(),
               f"Дней в наличии {span(res['pa'], res['pb'])}", f"Дней в наличии {span(a, b)}", "Примечание"]
    sheets = [("Итог", ["Показатель", "Сумма, ₽", "Доля в изменении продаж, %"], s_rows, {"totals": False}),
              ("Артикулы", main_cols, main),
              ("Довезти", head + rs_cols, no_rows),
              ("Мало продавались", head + rs_cols, sm_rows),
              ("Не довозить", head + [f"Маржа за {MARGIN_WEEKS} недель*, %", "Прибыль в месяц*, ₽",
                                     "Продажи в месяц, ₽", "Продавали шт в неделю", "Цена до СПП, ₽", f"Продажи {span(res['pa'], res['pb'])}, ₽"], sk_rows),
              ("Цена", head + ["Потеря продаж из-за цены, ₽", "Потеря, шт", "Продано было, шт", "Продано стало, шт",
                               "Покупатель платил за шт, ₽", "Покупатель платит за шт, ₽",
                               "Цена для покупателя, изм. %", "Наша цена до СПП было, ₽", "Наша цена до СПП стало, ₽",
                               "Наша цена, изм. %", "СПП было, %", "СПП стало, %", stock_label(),
                               "Хватит остатка, дней", "Изменение прибыли*, ₽"], pr_rows),
              ("Реклама", head + ["Оценка", "Реклама было, ₽", "Реклама стало, ₽",
                                  "ДРР был (по рекламируемым товарам), %", "Продано было, шт", "Продано стало, шт",
                                  "Изменение продаж, ₽", "из них из-за рекламы, ₽", stock_label(),
                                  "Хватит остатка, дней", f"Маржа за {MARGIN_WEEKS} недель*, %",
                                  "Изменение прибыли*, ₽"], ad_rows)]
    notes = [
        ("Продажи", "Как на сайте WB: до СПП, с НДС, по дате операции в отчёте реализации; без коррекций WB."),
        ("Итог", "Каждая строка — на сколько рублей эта причина изменила продажи. Минус (в скобках) — уменьшила. "
                 "Доля в изменении — какая часть общего изменения пришлась на причину; у причин, которые "
                 "работали в обратную сторону, доля со знаком минус."),
        ("Остаток", "Остаток на последний загруженный день: склады WB + наш склад FBS. «Хватит остатка» — на "
                    "сколько дней его хватит при продажах текущего периода (если их нет — при прошлых)."),
        ("Довезти", f"Товары, которых сейчас нет на складах WB и FBS, хотя раньше они продавались. "
                    "Если дней в наличии в текущем периоде почти столько же, сколько в прошлом, — товар "
                    "закончился только что, и потери впереди. «Прибыль / продажи в месяц» — сколько товар приносил, "
                    "пока был в наличии, в пересчёте на 30 дней. Только прибыльные (маржа после расходов WB от 10%) и "
                    f"заметные: от {RESTOCK_MIN_WEEK_QTY} шт в неделю и от {RESTOCK_MIN_MONTH_PROFIT // 1000} тыс ₽ прибыли "
                    "в месяц. Остальные прибыльные — на листе «Мало продавались». Сверху — больше прибыли. "
                    "Прибыль в месяц = продажи в месяц без НДС × маржа за 8 недель. Если себестоимости нет, "
                    "маржа и прибыль пустые, а товар оценивается по продажам — см. «Примечание». "
                    "Продажи — за вычетом возвратов: число в скобках (минус) — вернули больше, чем продали."),
        ("Не довозить", "Товары без остатка, которые продавались в минус или с маржой ниже 10%: распродажа, "
                        "демпинг или высокие расходы WB. В «Довезти» они не попадают. Везти их по прежней цене "
                        "убыточно."),
        ("Цены", "Покупатель платит за шт — средняя цена после СПП (что реально платит покупатель на WB). "
                  "Наша цена до СПП — цена, которую ставим мы. СПП — скидка, которую даёт WB за свой счёт. "
                  "Изм. % — на сколько процентов цена стала выше (+) или ниже (−) по сравнению с прошлым периодом."),
        ("Реклама", "Все артикулы, где расход на рекламу снизился от 30%. Сверху — где сократили зря. "
                    "«Изменение продаж» — общее изменение по товару, «из них из-за рекламы» — часть, которую "
                    "разбор относит именно к рекламе (если одновременно выросла цена, падение уходит в цену). "
                    "«Правильно» — рекламу сократили, когда товара почти не осталось (меньше чем на неделю), "
                    f"маржа за {MARGIN_WEEKS} недель ниже {RESTOCK_MIN_MARGIN}% или ДРР был выше {num(_drr_high())}% "
                    "(шкала из отчёта о рекламе: до 7% — отлично, 7–9% — нормально, выше 9% — плохо). "
                    "или реклама не приносила заказов. Иначе — «зря — стоит вернуть рекламу»."),
        ("Маржа", f"Для решений «довезти / не довозить» берём маржу за {MARGIN_WEEKS} недель — так распродажа или "
                  "одна неудачная неделя не искажают картину."),
        ("Прибыль*", "Управленческий учёт, как в дашборде продаж: выручка без НДС минус себестоимость (FIFO), "
                     "комиссия и расходы WB, распределённые на штуки по неделям."),
        ("Разложение", "Выручка = дни в наличии × штук в день × цена. Наличие = (дни₁ − дни₀) × штук в день₀ "
                       "× цена₀; цена = штуки₁ × (цена₁ − цена₀); спрос = дни₁ × (штук в день₁ − штук в день₀)"
                       " × цена₀; возвраты — изменение суммы возвратов со знаком минус. Сумма причин = изменение."),
        ("Цена для покупателя", "Если покупателю стало дороже от 3% (наша цена или СПП WB) и штук в день стало "
                                "меньше — спрос относим к цене. Что сильнее изменилось, наша цена или СПП, — туда."),
        ("Реклама", "Если расходы на рекламу артикула упали от 30% и штук в день стало меньше — спрос относим "
                    "к рекламе (если цена не менялась)."),
        ("Наличие", "Дни, когда на складах WB или FBS был остаток больше нуля. Нехватка отдельных размеров "
                    "здесь не видна — артикул считается в наличии."),
        ("Разная длина", "Если периоды разной длины, прошлый пересчитывается на длину текущего."),
    ]
    data = _book("Почему изменились продажи", sub, sheets, notes=notes)
    return f"Почему изменились продажи {span(a, b)}.xlsx", data, XLSX


# ---------------------------------------------------------------- реакция продаж на цену
WEEKS = 12


def file_elasticity(a: date, b: date):
    """По неделям за 12 недель: как штуки в день реагируют на цену для покупателя."""
    from ..wb_sales_export import fetch
    from .menu import XLSX, _book, span
    start = b - timedelta(days=7 * WEEKS - 1)
    df = fetch(start, b, "nm_day", [])
    if df.empty:
        return None
    df = df.rename(columns={**COLS, **INFO, "Артикул WB": "nm", "Дата": "d"})
    df["d"] = pd.to_datetime(df["d"]).dt.date
    df["w"] = df["d"].map(lambda d: (b - d).days // 7)
    st = _query("""
        WITH x AS (
            SELECT date_from::DATE AS d, nm_id, SUM(COALESCE(quantity, 0)) AS q
            FROM stocks.unpacked_stocks WHERE date_from::DATE BETWEEN $a AND $b GROUP BY 1, 2
            UNION ALL
            SELECT date_from::DATE, nm_id, SUM(COALESCE(quantity, 0))
            FROM stocks.unpacked_fbs_stocks WHERE date_from::DATE BETWEEN $a AND $b GROUP BY 1, 2
        )
        SELECT d, nm_id AS nm FROM x GROUP BY 1, 2 HAVING SUM(q) > 0""", {"a": start, "b": b})
    wk = df.groupby(["nm", "w"], as_index=False).agg(q=("q", "sum"), s=("s", "sum"), bs=("bs", "sum"),
                                                    dsold=("q", lambda x: int((x > 0).sum())))
    if not st.empty:
        st["d"] = pd.to_datetime(st["d"]).dt.date
        st["w"] = st["d"].map(lambda d: (b - d).days // 7)
        din = st.groupby(["nm", "w"]).size().rename("din").reset_index()
        din["nm"] = din["nm"].astype("int64")
        wk["nm"] = wk["nm"].astype("int64")
        wk = wk.merge(din, on=["nm", "w"], how="left").fillna({"din": 0})
    else:
        wk["din"] = 7
    wk["days"] = wk[["din", "dsold"]].max(axis=1).clip(upper=7)
    info = df.groupby("nm")[list(INFO.values())].first()
    info.index = info.index.astype("int64")
    rows = []
    for nm, g in wk[(wk["q"] > 0) & (wk["days"] >= 3)].groupby("nm"):
        if len(g) < 6:
            continue
        x = (g["bs"] / g["q"]).map(math.log)
        yv = (g["q"] / g["days"]).map(math.log)
        if x.std() < 0.03:
            continue
        xm, ym = x.mean(), yv.mean()
        cov = ((x - xm) * (yv - ym)).sum()
        var = ((x - xm) ** 2).sum()
        el = cov / var
        r2 = cov * cov / (var * ((yv - ym) ** 2).sum()) if ((yv - ym) ** 2).sum() else 0
        pb = g["bs"] / g["q"]
        word = ("сильно реагирует" if el <= -1.5 else "заметно реагирует" if el <= -0.7
                else "слабо реагирует" if el < -0.2 else "почти не реагирует / другие факторы сильнее")
        i = info.loc[nm] if nm in info.index else {}
        rows.append([i.get("brand", ""), i.get("category", ""), i.get("sa", ""), int(nm), i.get("title", ""),
                     len(g), float(g["s"].sum()), float(pb.min()), float(pb.max()), el, r2, word])
    if not rows:
        return None
    rows.sort(key=lambda r: -r[6])
    cols = ["Бренд", "Категория", "Артикул продавца", "Артикул WB", "Наименование", "Недель",
            "Продажи за 12 недель, ₽", "Цена покупателя мин, ₽", "Цена покупателя макс, ₽",
            "Эластичность", "Надёжность (R²)", "Вывод"]
    notes = [("Что это", "На сколько процентов меняются продажи в штуках в день при изменении цены для "
                         "покупателя на 1%. −1,5 — при росте цены на 10% штук становится на 15% меньше."),
             ("Как считаем", "Недели за 12 недель, где артикул был в наличии от 3 дней и продавался; "
                             "нужно от 6 недель и разброс цены от 3%. Наклон регрессии log(штук в день) "
                             "на log(цены покупателя)."),
             ("Надёжность", "R² от 0 до 1: чем ближе к 1, тем больше изменения продаж объясняются ценой. "
                            "Ниже 0,3 — на продажи больше влияли другие факторы (сезон, реклама, остатки)."),
             ("Как использовать", "Где реакция слабая — есть запас поднять цену; где сильная — повышение цены "
                                  "быстро съедает штуки, а снижение их возвращает.")]
    data = _book("Реакция продаж на цену", f"12 недель по {b:%d.%m.%Y} · цена для покупателя (после СПП)",
                 [("Артикулы", cols, rows)], notes=notes)
    return f"Реакция на цену {span(start, b)}.xlsx", data, XLSX


# ---------------------------------------------------------------- 🚨 сигналы
def signals(day: date) -> dict | None:
    """7 дней по day к среднему за 4 недели до них: заметно просевшие артикулы."""
    a, pa, pb = day - timedelta(days=6), day - timedelta(days=34), day - timedelta(days=7)
    res = analyze(a, day, pa, pb)
    if not res:
        return None
    df = res["df"]
    hit = df[(df["net0"] >= SIG_MIN_DAY * 7) & (df["delta"] <= -SIG_MIN_LOSS)
             & (df["delta"] <= -SIG_DROP * df["net0"])].copy()
    res["hit"] = hit.sort_values("delta")
    return res


def signals_text(res: dict, top: int = 10, short: bool = False) -> str | None:
    from .menu import num, rub, span
    hit = res["hit"]
    if hit.empty:
        return None
    lines = [f"<b>🚨 Сигналы · 7 дней по {res['b']:%d.%m}</b>",
             f"<i>{span(res['a'], res['b'])} к среднему за 4 недели до этого · до СПП с НДС</i>", "",
             f"Заметно просели <b>{num(len(hit))}</b> артикулов, вместе "
             f"<b>−{rub(-hit['delta'].sum())}</b> за неделю:"]
    for i, (_, r) in enumerate(hit.head(top).iterrows(), 1):
        pct = max(r["delta"] / r["net0"] * 100, -100)
        v1 = r["q1"] / 7 if r["q1"] == r["q1"] else 0.0
        qty = f" · продавали {num(r['q0'] / 7, 1)} → {num(v1, 1)} шт в день" if r["q0"] > 0 else ""
        lines.append(f"{i}. {_who(r)}\n    <b>{_pct(pct)}</b> (−{rub(-r['delta'])}){qty}"
                     f" · {ICONS[r['why']]} {reason(r, 7)}{profit(r)}")
    if len(hit) > top:
        lines.append(f"…ещё {len(hit) - top} — " + ("кнопка «🚨 Сигналы» в боте." if short else "в Excel."))
    by = hit.groupby("why")["delta"].agg(["sum", "size"]).sort_values("sum")
    lines += ["", "<b>Почему просели — по всем этим товарам</b>"] + [
        f"{ICONS[k]} {plain(k, r['sum'])} — <b>−{rub(-r['sum'])}</b> · {num(r['size'])} арт."
        for k, r in by.iterrows() if r["sum"] < 0]
    return "\n".join(lines)


def report_signals(a: date, b: date) -> dict | None:
    from .menu import _files_kb, span, table
    res = signals(b)
    if not res:
        return None
    _CACHE[("sig", b)] = res
    text = signals_text(res)
    files = (("sig", "Excel: все сигналы"),)
    if not text:
        text = (f"<b>🚨 Сигналы · 7 дней по {b:%d.%m}</b>\n<i>{span(res['a'], b)} к среднему за 4 недели</i>\n\n"
                "✅ Резко просевших артикулов нет.")
        return {"text": text, "photo": None, "auto": None, "files": (), "kb": _files_kb("g", b, b, ())}
    hit = res["hit"]
    t = table("Сигналы", ["Артикул", "Бренд", "Изменение", "Причина"],
              [[r["sa"] or str(r["nm"]), r["brand"], r["delta"], f"{NAMES[r['why']]}: {reason(r, 7)}"]
               for _, r in hit.head(30).iterrows()], ["text", "text", "rub", "text"])
    return {"text": text, "photo": None, "auto": None, "files": files, "tables": [t],
            "kb": _files_kb("g", b, b, files)}


def file_signals(b: date):
    from .menu import XLSX, _book, span
    res = _CACHE.get(("sig", b)) or signals(b)
    if not res or res["hit"].empty:
        return None
    rows = [[r["brand"], r["category"], r["sa"], r["nm"], r["title"], r["net0"], r["net1"], r["delta"],
             r["delta"] / r["net0"] * 100, NAMES[r["why"]], reason(r, 7), r["stock_now"], cover(r, 7)]
            for _, r in res["hit"].iterrows()]
    cols = ["Бренд", "Категория", "Артикул продавца", "Артикул WB", "Наименование", "В среднем за неделю (4 недели до), ₽",
            "Последние 7 дней, ₽", "Изменение, ₽", "Изменение, %", "Главная причина", "Пояснение",
            stock_label(), "Хватит остатка, дней"]
    data = _book("Сигналы", f"{span(res['a'], b)} к среднему за 4 недели", [("Сигналы", cols, rows)])
    return f"Сигналы {b:%d.%m.%Y}.xlsx", data, XLSX


def digest_block(day: date) -> dict | None:
    """Блок для ежедневной рассылки: только если есть просевшие артикулы."""
    if not SIGNALS_IN_DIGEST:
        return None
    res = signals(day)
    text = signals_text(res, top=7, short=True) if res else None
    return {"text": text, "photo": None} if text else None
