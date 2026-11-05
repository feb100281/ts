# gear/app/daily_sales/assistant/supplies.py
"""Оборачиваемость по поставкам: за сколько дней распродаётся каждая поставка.

Поставки и их состав — wb_raw.wb_supplies / wb_supply_goods (WB Supplies API,
команда wb_supplies). Выкупы — отчёт реализации WB (sales.wb_raw): продажи минус
возвраты, привязка к поставке по gi_id. Остатки — как в stocks_report.

Остаток артикула на WB раскладывается по поставкам от новых к старым. Срок
распродажи = дней с приёмки + остаток этой и более старых поставок / темп,
темп — выкупы артикула в день за последние RATE_DAYS дней.
"""
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

from conns import get_duckdb_conn_with_opt

RATE_DAYS = 14          # окно темпа выкупа
OK_DAYS, WARN_DAYS = 30, 45
MIN_DAYS = 14           # новинка без выкупов моложе — «рано оценивать»
BRAND_TOP = 12

ST_OK, ST_WARN, ST_BAD, ST_NEW, ST_STOP = "✅", "⚠️", "🔴", "⏳", "🔴 нет выкупов"
ST_DONE = "распродана"
MAX_DAYS = 999          # прогноз длиннее показываем как 999

NOT_CORR = "COALESCE(sop_name, '') NOT ILIKE '%оррекц%'"

SALES_SQL = f"""
    SELECT rr_dt::DATE AS d, nm_id AS nm, TRY_CAST(gi_id AS BIGINT) AS gi,
           SUM(CASE WHEN dtn = 'Продажа' THEN 1 ELSE -1 END) AS q
    FROM sales.wb_raw
    WHERE quantity <> 2 AND dtn IN ('Продажа', 'Возврат') AND {NOT_CORR}
      AND COALESCE(retail_price, 0) <> 0 AND rr_dt::DATE <= $end
    GROUP BY 1, 2, 3"""

PRICE_SQL = f"""
    SELECT nm_id AS nm,
           SUM(CASE WHEN dtn = 'Продажа' THEN 1 ELSE -1 END) AS q,
           SUM(CASE WHEN dtn = 'Продажа' THEN retail_price ELSE -retail_price END) AS rp,
           SUM(CASE WHEN dtn = 'Продажа' THEN retail_amount ELSE -retail_amount END) AS ra,
           AVG(sale_percent) FILTER (WHERE dtn = 'Продажа') AS disc
    FROM sales.wb_raw
    WHERE quantity <> 2 AND dtn IN ('Продажа', 'Возврат') AND {NOT_CORR}
      AND COALESCE(retail_price, 0) <> 0 AND rr_dt::DATE BETWEEN $a AND $end
    GROUP BY 1"""

SUPPLY_SQL = """
    WITH s AS (
        SELECT supply_id AS sid,
               TRY_CAST(LEFT(json_extract_string(row_json::VARCHAR, '$.factDate'), 10) AS DATE) AS fact
        FROM pg.wb_raw.wb_supplies),
    g AS (
        SELECT supply_id AS sid,
               TRY_CAST(json_extract_string(row_json::VARCHAR, '$.nmID') AS BIGINT) AS nm,
               COALESCE(TRY_CAST(json_extract_string(row_json::VARCHAR, '$.acceptedQuantity') AS DOUBLE),
                        TRY_CAST(json_extract_string(row_json::VARCHAR, '$.quantity') AS DOUBLE), 0) AS acc,
               json_extract_string(row_json::VARCHAR, '$.color') AS color
        FROM pg.wb_raw.wb_supply_goods)
    SELECT g.sid, s.fact, g.nm, SUM(g.acc) AS acc, ANY_VALUE(g.color) AS color
    FROM g JOIN s USING (sid)
    WHERE s.fact IS NOT NULL AND s.fact <= $end AND g.nm IS NOT NULL
    GROUP BY 1, 2, 3 HAVING SUM(g.acc) > 0"""

PRODUCT_SQL = """
    SELECT card_id AS nm,
           ANY_VALUE(COALESCE(NULLIF(TRIM(UPPER(brand)), ''), 'НЕ УКАЗАН')) AS brand,
           ANY_VALUE(COALESCE(NULLIF(TRIM(subject_name), ''), 'Не указана')) AS category,
           ANY_VALUE(COALESCE(NULLIF(TRIM(gender), ''), '')) AS gender,
           ANY_VALUE(COALESCE(sa_name, '')) AS sa,
           ANY_VALUE(COALESCE(NULLIF(TRIM(title), ''), '')) AS title
    FROM inventories.wb_product GROUP BY 1"""


def _status(days_since, remaining, rate, forecast):
    if remaining <= 0:
        return ST_OK if forecast <= OK_DAYS else ST_WARN if forecast <= WARN_DAYS else ST_BAD
    if not rate:
        return ST_NEW if days_since + 1 < MIN_DAYS else ST_STOP
    return ST_OK if forecast <= OK_DAYS else ST_WARN if forecast <= WARN_DAYS else ST_BAD


def build(report_date=None, brand=None) -> dict:
    """Данные отчёта: articles, supplies (DataFrame), даты и сводка."""
    from .stocks import BASE_SQL, _last_date
    from .digest import loaded_date

    asked = (date.fromisoformat(str(report_date)[:10]) if report_date
             else date.today() - timedelta(days=1))
    end = min(asked, loaded_date() or asked)
    with get_duckdb_conn_with_opt(ro=True) as con:
        sd = _last_date(con, asked)
        if sd is None:
            return {"error": f"Остатков на {asked:%d.%m.%Y} и раньше нет."}
        st = con.execute(BASE_SQL + "SELECT * FROM s", {"d": sd}).df()
        sales = con.execute(SALES_SQL, {"end": end}).df()
        price = con.execute(PRICE_SQL, {"a": end - timedelta(days=RATE_DAYS - 1),
                                        "end": end}).df()
        sup = con.execute(SUPPLY_SQL, {"end": end}).df()
        prod = con.execute(PRODUCT_SQL).df()

    for c in ("wb_qty", "to_client", "from_client", "fbs_qty"):
        st[c] = pd.to_numeric(st[c], errors="coerce").fillna(0)
    st["total"] = st[["wb_qty", "to_client", "from_client", "fbs_qty"]].sum(axis=1)
    st = st[st["total"] > 0].copy()
    st["nm"] = st["nm_id"].astype("int64")
    art = st.merge(prod, on="nm", how="left")
    for c, v in (("brand", "НЕ УКАЗАН"), ("category", "Не указана"),
                 ("gender", ""), ("sa", ""), ("title", "")):
        art[c] = art[c].fillna(v)
    if brand:
        art = art[art["brand"].str.contains(str(brand).strip().upper(), regex=False)]
    if art.empty:
        return {"error": "Нет артикулов с остатком" + (f" по бренду «{brand}»" if brand else "") + "."}
    nms = set(art["nm"])

    sales["d"] = pd.to_datetime(sales["d"])
    sales = sales[sales["nm"].isin(nms)]
    w0 = pd.Timestamp(end - timedelta(days=RATE_DAYS - 1))

    # ---- поставки
    sup = sup[sup["nm"].isin(nms)].copy()
    sup["fact"] = pd.to_datetime(sup["fact"])
    by_key = {k: g for k, g in sales.dropna(subset=["gi"]).groupby(["nm", "gi"])}
    # фактический остаток WB (склады + в пути) — раскладываем по поставкам от новых к старым
    left = (art["wb_qty"] + art["to_client"] + art["from_client"]).groupby(art["nm"]).sum().to_dict()
    rows = []
    e = pd.Timestamp(end)
    for r in sup.sort_values(["nm", "fact", "sid"], ascending=[True, False, False]).itertuples(index=False):
        g = by_key.get((r.nm, r.sid))
        g = g[g["d"] >= r.fact].sort_values("d") if g is not None else None
        days_since = (e - r.fact).days
        sold = s30 = s45 = 0.0
        done_day = None
        if g is not None and not g.empty:
            age = (g["d"] - r.fact).dt.days
            sold = float(g["q"].sum())
            s30 = float(g.loc[age < OK_DAYS, "q"].sum())
            s45 = float(g.loc[age < WARN_DAYS, "q"].sum())
            cum = g["q"].cumsum()
            hit = g.loc[cum >= r.acc, "d"]
            if not hit.empty:
                done_day = (hit.iloc[0] - r.fact).days + 1
        calc = max(r.acc - sold, 0.0)
        remaining = min(calc, max(left.get(r.nm, 0.0), 0.0))
        left[r.nm] = left.get(r.nm, 0.0) - remaining
        rows.append({"nm": r.nm, "sid": r.sid, "fact": r.fact.date(), "acc": r.acc,
                     "color": r.color, "sold": sold, "s30": s30, "s45": s45, "calc": calc,
                     "remaining": remaining, "days": days_since + 1, "done_day": done_day})
    sp = pd.DataFrame(rows, columns=["nm", "sid", "fact", "acc", "color", "sold", "s30", "s45",
                                     "calc", "remaining", "days", "done_day"])
    # темп — выкупы артикула в день (по всем поставкам): товар на складе общий
    rate_nm = (sales[sales["d"] >= w0].groupby("nm")["q"].sum().clip(lower=0) / RATE_DAYS)
    sp["rate"] = sp["nm"].map(rate_nm).fillna(0.0)
    # очередь: сначала продаются старые поставки, потом новые
    sp = sp.sort_values(["nm", "fact", "sid"])
    sp["queue"] = sp.groupby("nm")["remaining"].cumsum()
    fc, stt = [], []
    for r in sp.itertuples(index=False):
        if r.remaining <= 0:
            fc.append(r.done_day if pd.notna(r.done_day) else None)
            stt.append(ST_DONE)
            continue
        f = min(r.days + r.queue / r.rate, MAX_DAYS) if r.rate > 0 else None
        fc.append(f)
        stt.append(_status(r.days - 1, r.remaining, r.rate, 0 if f is None else f))
    sp["forecast"], sp["status"] = fc, stt
    sp = sp.merge(art[["nm", "brand", "category", "sa", "title"]], on="nm", how="left")
    active = sp[sp["remaining"] > 0].copy()

    # ---- артикулы
    last = sp.sort_values("fact").groupby("nm").tail(1).set_index("nm")
    act = active.groupby("nm").agg(n_act=("sid", "count"), rem=("remaining", "sum"))
    win_all = sales[sales["d"] >= w0].groupby("nm")["q"].sum()
    price = price.set_index("nm") if not price.empty else pd.DataFrame(
        columns=["q", "rp", "ra", "disc"])
    a = art.set_index("nm")
    a["last_fact"] = last["fact"]
    a["last_acc"] = last["acc"]
    a["last_sold"] = last["sold"]
    a["last_forecast"] = last["forecast"]
    a["last_status"] = last["status"]
    a["color"] = last["color"]
    a["n_act"] = act["n_act"]
    a["rem"] = act["rem"]
    a["buy14"] = win_all
    a["per_day"] = a["buy14"].fillna(0) / RATE_DAYS
    a["on_hand"] = a["wb_qty"] + a["fbs_qty"]
    a["turn"] = (a["on_hand"] / a["per_day"]).where(a["per_day"] > 0)
    pq = pd.to_numeric(price.get("q"), errors="coerce").reindex(a.index)
    a["p_before"] = (price["rp"].reindex(a.index) / pq).where(pq > 0)
    a["p_after"] = (price["ra"].reindex(a.index) / pq).where(pq > 0)
    a["spp"] = ((1 - price["ra"].reindex(a.index) / price["rp"].reindex(a.index)) * 100
                ).where(price["rp"].reindex(a.index) > 0)
    a["disc"] = price["disc"].reindex(a.index)
    a = a.reset_index()

    return {"asked": asked, "stock_date": sd, "end": end, "brand": brand,
            "articles": a, "supplies": sp, "active": active,
            "no_supply": int(a["last_fact"].isna().sum())}


# ---------------------------------------------------------------- текст
def _f(v):
    v = 0 if v is None or pd.isna(v) else v
    return f"{int(round(v)):,}".replace(",", " ")


def report(report_date=None, brand=None) -> str:
    data = build(report_date, brand)
    if "error" in data:
        return data["error"]
    act, a = data["active"], data["articles"]
    lines = [f"ОБОРАЧИВАЕМОСТЬ ПОСТАВОК: остатки на {data['stock_date']:%d.%m.%Y}, "
             f"выкупы по {data['end']:%d.%m.%Y}"
             + (f", бренд содержит «{brand}»" if brand else "")]
    cnt = act["status"].value_counts()
    lines.append(f"Артикулов с остатком: {_f(len(a))}; поставок, которые ещё продаются: "
                 f"{_f(len(act))} (остаток по ним {_f(act['remaining'].sum())} шт).")
    lines.append("Статус\tПоставок\tОстаток по поставкам, шт")
    for s, name in ((ST_OK, "✅ распродастся за 30 дней"), (ST_WARN, "⚠️ за 31–45 дней"),
                    (ST_BAD, "🔴 дольше 45 дней"), (ST_STOP, "🔴 артикул не выкупался 14 дней"),
                    (ST_NEW, "⏳ новинка, выкупов ещё нет")):
        n = int(cnt.get(s, 0))
        if n:
            lines.append(f"{name}\t{n}\t{_f(act.loc[act['status'] == s, 'remaining'].sum())}")

    if not act.empty:
        g = act.assign(bad=act["status"].isin([ST_BAD, ST_STOP]),
                       ok=act["status"] == ST_OK)
        gb = g.groupby("brand").agg(n=("sid", "count"), ok=("ok", "sum"), bad=("bad", "sum"),
                                    rem=("remaining", "sum")).sort_values("rem", ascending=False)
        lines.append("\nБренд\tПоставок\t✅\t🔴\tОстаток по поставкам, шт")
        for br, r in gb.head(BRAND_TOP).iterrows():
            lines.append(f"{br}\t{int(r.n)}\t{int(r.ok)}\t{int(r.bad)}\t{_f(r.rem)}")
        if len(gb) > BRAND_TOP:
            lines.append(f"Ещё брендов: {len(gb) - BRAND_TOP} — в Excel.")
        worst = act[act["status"].isin([ST_BAD, ST_STOP])].sort_values("remaining",
                                                                         ascending=False).head(10)
        if not worst.empty:
            lines.append("\nСамые медленные поставки (по остатку)")
            lines.append("Артикул\tБренд\tДата приёмки\tПринято, шт\tОстаток, шт\tПрогноз, дней")
            for r in worst.itertuples():
                fc = ("нет выкупов" if pd.isna(r.forecast) else
                      "больше 365" if r.forecast > 365 else _f(r.forecast))
                lines.append(f"{r.sa or r.nm}\t{r.brand}\t{r.fact:%d.%m.%Y}\t{_f(r.acc)}\t"
                             f"{_f(r.remaining)}\t{fc}")
    if data["no_supply"]:
        lines.append(f"Артикулов без поставки в данных WB: {data['no_supply']} "
                     "(приёмка раньше загрузки или поставка не найдена).")
    lines.append(f"Прогноз срока = дней с приёмки + (остаток этой и более старых поставок) / "
                 f"выкупы артикула в день за {RATE_DAYS} дней. Выкупы = продажи минус возвраты по отчёту WB, "
                 "привязка к поставке по номеру. Остаток по поставке — фактический остаток WB "
                 "артикула, разложенный по поставкам от новых к старым. Полная "
                 "таблица по артикулам и поставкам — в Excel (export_excel с supply_turnover).")
    return "\n".join(lines)


# ---------------------------------------------------------------- Excel
ART_COLS = [
    ("brand", "Бренд"), ("category", "Категория"), ("gender", "Пол"), ("sa", "Артикул продавца"),
    ("nm", "Артикул WB"), ("title", "Наименование"), ("color", "Цвет"),
    ("wb_qty", "Склады WB, шт"), ("fbs_qty", "FBS, шт"), ("to_client", "В пути к клиенту, шт"),
    ("from_client", "В пути от клиента, шт"), ("total", "Итого остаток, шт"),
    ("last_fact", "Последняя поставка: дата"), ("last_acc", "Последняя поставка: принято, шт"),
    ("last_sold", "Последняя поставка: выкуплено, шт"),
    ("last_forecast", "Последняя поставка: прогноз, дней"), ("last_status", "Статус"),
    ("n_act", "Поставок в продаже, шт"), ("rem", "Остаток по поставкам, шт"),
    ("buy14", f"Выкупы за {RATE_DAYS} дн, шт"), ("per_day", "Выкупы в день, шт"),
    ("turn", "Оборачиваемость остатка, дней"),
    ("p_before", "Средняя цена до СПП, ₽"), ("p_after", "Средняя цена после СПП, ₽"),
    ("spp", "СПП, %"), ("disc", "Скидка продавца, %"),
]
SUP_COLS = [
    ("brand", "Бренд"), ("category", "Категория"), ("sa", "Артикул продавца"),
    ("nm", "Артикул WB"), ("title", "Наименование"), ("color", "Цвет"),
    ("sid", "Код поставки"), ("fact", "Дата приёмки"), ("days", "Дней с приёмки"),
    ("acc", "Принято, шт"), ("sold", "Выкуплено всего, шт"),
    ("s30", "Выкуплено за 30 дней, шт"), ("s45", "Выкуплено за 45 дней, шт"),
    ("calc", "Принято − выкуплено, шт"), ("remaining", "Остаток по поставке, шт"),
    ("rate", "Выкупы артикула в день, шт"),
    ("queue", "Очередь: остаток этой и более старых поставок, шт"),
    ("forecast", "Срок распродажи (прогноз), дней"), ("status", "Статус"),
]
NOTES = [
    ("Что это", "Оборачиваемость товара по поставкам: за сколько дней распродаётся каждая "
                "поставка. В отчёт попадают только артикулы с остатком на дату остатков."),
    ("Цель", f"Поставка распродаётся за {OK_DAYS}–{WARN_DAYS} дней."),
    ("Статус", f"✅ до {OK_DAYS} дней · ⚠️ {OK_DAYS + 1}–{WARN_DAYS} · 🔴 больше {WARN_DAYS} · "
               f"🔴 нет выкупов — артикул не выкупался {RATE_DAYS} дней · "
               f"⏳ новинка: меньше {MIN_DAYS} дней с приёмки и выкупов ещё нет."),
    ("Срок распродажи", "Дней с приёмки + очередь / выкупы артикула в день. Очередь — остаток этой "
                        "поставки и всех более старых поставок артикула: старые продаются первыми."),
    ("Выкупы", "Продажи минус возвраты из отчёта реализации WB (как в дашборде, с НДС). "
               "К поставке привязываются по номеру поставки в отчёте WB."),
    ("Темп", f"Выкупы артикула (по всем поставкам) за последние {RATE_DAYS} дней / {RATE_DAYS}. "
             "По номеру поставки темп не считаем: товар артикула на складе общий, и WB "
             "записывает продажи на разные поставки."),
    ("Выкуплено по поставке", "Продажи минус возвраты с номером этой поставки в отчёте WB — "
                              "справочно; на прогноз не влияет."),
    ("Остаток по поставке", "Фактический остаток артикула на WB (склады + в пути к клиенту и от "
                            "клиента) разложен по поставкам от новых к старым, но не больше, чем "
                            "«принято − выкуплено» по этой поставке. Остаток 0 — поставка распродана. "
                            "Разница «принято − выкуплено» и остатка — товар, ушедший без продажи "
                            "(возвраты поставщику, списания, утери) или проданный под другим номером "
                            "поставки."),
    ("999 дней", "Прогноз больше 999 дней показан как 999."),
    ("Оборачиваемость остатка", f"(склады WB + FBS) / выкупы в день за {RATE_DAYS} дней."),
    ("Цены", f"За последние {RATE_DAYS} дней по выкупам: до СПП — наша цена, после СПП — сколько "
             "заплатил покупатель; СПП = 1 − после / до. Скидка продавца — средняя по продажам."),
    ("Источники", "Поставки — WB API «Поставки»; продажи — отчёт реализации WB; остатки — "
                  "склады WB и FBS, как в отчёте об остатках."),
]


def _rows(df, cols):
    out = []
    for r in df[[c for c, _ in cols]].itertuples(index=False):
        row = []
        for v in r:
            if v is None or (isinstance(v, float) and pd.isna(v)) or v is pd.NaT:
                row.append(None)
            elif hasattr(v, "date") and not isinstance(v, date):
                row.append(v.date())
            elif isinstance(v, float):
                row.append(round(v, 1))
            else:
                row.append(v.item() if hasattr(v, "item") else v)
        out.append(row)
    return out


def excel(path, title: str, report_date=None, brand=None) -> int:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font
    from gear.management.commands import mp
    from .excel import _write_table

    data = build(report_date, brand)
    if "error" in data:
        raise ValueError(data["error"])
    a = data["articles"].sort_values(["brand", "category", "turn"], ascending=[True, True, False])
    sp = data["supplies"].sort_values(["brand", "nm", "fact"])
    act = data["active"]
    sub = (f"Остатки на {data['stock_date']:%d.%m.%Y} · выкупы по {data['end']:%d.%m.%Y}"
           + (f" · бренд «{brand}»" if brand else ""))

    wb = Workbook()
    ws = wb.active
    ws.title = "Сводка"
    g = act.assign(ok=act["status"] == ST_OK, warn=act["status"] == ST_WARN,
                   bad=act["status"].isin([ST_BAD, ST_STOP]), new=act["status"] == ST_NEW)
    gs = g.groupby(["brand", "category"]).agg(
        n=("sid", "count"), ok=("ok", "sum"), warn=("warn", "sum"), bad=("bad", "sum"),
        new=("new", "sum"), rem=("remaining", "sum"), fc=("forecast", "median")).reset_index()
    ag = a.groupby(["brand", "category"]).agg(arts=("nm", "count"), stock=("total", "sum"),
                                              on_hand=("on_hand", "sum"),
                                              pd_=("per_day", "sum")).reset_index()
    gs = ag.merge(gs, on=["brand", "category"], how="left")
    gs["turn"] = (gs["on_hand"] / gs["pd_"]).where(gs["pd_"] > 0)
    s_cols = [("brand", "Бренд"), ("category", "Категория"), ("arts", "Артикулов с остатком, шт"),
              ("stock", "Остаток всего, шт"), ("n", "Поставок в продаже, шт"),
              ("ok", "✅ до 30 дней, шт"), ("warn", "⚠️ 31–45 дней, шт"),
              ("bad", "🔴 дольше 45 дней, шт"), ("new", "⏳ новые, шт"),
              ("rem", "Остаток по поставкам, шт"),
              ("fc", "Медианный срок распродажи, дней"), ("turn", "Оборачиваемость остатка, дней")]
    gs = gs.sort_values("stock", ascending=False)
    _write_table(ws, mp, title, sub, "Бренд → категория; поставки, которые ещё продаются",
                 [n for _, n in s_cols], _rows(gs, s_cols), totals=False)

    ws = wb.create_sheet("По артикулам")
    _write_table(ws, mp, "По артикулам", sub, "Одна строка — артикул WB с остатком",
                 [n for _, n in ART_COLS], _rows(a, ART_COLS), totals=False)
    ws = wb.create_sheet("По поставкам")
    _write_table(ws, mp, "По поставкам", sub, "Артикул × поставка",
                 [n for _, n in SUP_COLS], _rows(sp, SUP_COLS), totals=False)

    ws = wb.create_sheet("Как читать")
    mp.sheet_setup(ws, landscape=False)
    mp.title_band(ws, "Как читать", title, 4, show_back=False)
    ws.column_dimensions["A"].width = 2
    ws.column_dimensions["B"].width = 26
    ws.column_dimensions["C"].width = 100
    for i, (k, v) in enumerate(NOTES):
        mp.write(ws, 7 + i, 2, k, font=Font(name=mp.FONT, size=9, bold=True, color=mp.NAVY_3),
                 align="left", border=mp.B_BOTTOM)
        mp.write(ws, 7 + i, 3, v, font=Font(name=mp.FONT, size=9, color=mp.TEXT),
                 align="left", wrap=True, border=mp.B_BOTTOM)
    wb.save(path)
    return len(a)
