# sales/print_utils.py
import numpy as np
import pandas as pd


# ====== МАППИНГ НОВОГО ПРОЕКТА ======
# ожидаемые "сырые" поля (англ), которые приходят из get_month_data/get_ytd_data:
# date, revenue, amount, comission, quant, sales, rtr, rtr_ratio

RENAMING_COLS = {
    "revenue": "Выручка",
    "amount": "Оборот",
    "comission": "Комиссия",
    "quant": "Кол-во",
    "sales": "Продажи",
    "rtr": "Возвраты",
    "rtr_ratio": "К возвратов",
}

# обратное переименование (на случай если df уже приходит с русскими колонками)
REVERSE_RENAMING_COLS = {v: k for k, v in RENAMING_COLS.items()}

# порядок строк в таблице
ORDER_METRICS = ["Выручка", "Оборот", "Комиссия", "Кол-во", "Продажи", "Возвраты", "К возвратов"]

# числовые колонки (важно для groupby.sum)
NUM_COLS = ["revenue", "amount", "quant", "sales", "rtr"]
# comission и rtr_ratio обычно проценты/доли — их не суммируем, обработаем отдельно


def _format_money(v: float) -> str:
    return f"₽{v:,.0f}".replace(",", " ")


def _format_int(v: float) -> str:
    return f"{v:,.0f}".replace(",", " ")


def _format_pct(v: float) -> str:
    # ожидаем, что v уже в процентах (например, 35 -> "35%")
    return f"{v:,.0f}%".replace(",", " ")


def _format_pct_1(v: float) -> str:
    # если нужно 1 знак после запятой
    return f"{v:,.1f}%".replace(",", " ")


def _ensure_raw_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Нормализуем входной df:
    - должен содержать: date + англ. колонки из RENAMING_COLS
    - если вместо них уже русские колонки — переведем обратно.
    """
    out = df.copy()

    # если нет "amount", но есть "Оборот" — значит df уже с русскими колонками
    if "amount" not in out.columns and "Оборот" in out.columns:
        cols_to_rename = {c: REVERSE_RENAMING_COLS[c] for c in out.columns if c in REVERSE_RENAMING_COLS}
        out = out.rename(columns=cols_to_rename)

    return out


def _coerce_numeric(df: pd.DataFrame) -> pd.DataFrame:
    """
    Приводим ключевые метрики к числовому типу.
    """
    out = df.copy()
    for c in (NUM_COLS + ["comission", "rtr_ratio"]):
        if c in out.columns:
            out[c] = pd.to_numeric(out[c], errors="coerce")
    return out


def _prev_missing(prev_val) -> bool:
    return pd.isna(prev_val) or float(prev_val) == 0.0


def _to_print_table(df_pivot: pd.DataFrame, title_left: str, title_right: str) -> dict:
    """
    df_pivot: index = Метрика
              columns = [title_left, title_right, Δ абс., Δ отн.]
    Возвращает {"html": "..."}
    """
    out = df_pivot.copy()
    base_cols = [c for c in [title_left, title_right] if c in out.columns]

    # формат базовых значений
    def fmt_value(metric: str, v) -> str:
        if pd.isna(v):
            return "—"
        v = float(v)

        if metric in ("Выручка", "Оборот", "Продажи", "Возвраты"):
            return _format_money(v)

        if metric == "Кол-во":
            return f"{_format_int(v)} ед"

        if metric == "Комиссия":
            # комиссия — процент
            return _format_pct(v)

        if metric == "К возвратов":
            # доля возвратов — процент
            return _format_pct(v)

        return str(v)

    for metric in out.index:
        for c in base_cols:
            out.loc[metric, c] = fmt_value(metric, df_pivot.loc[metric, c])

    abs_cls: dict[str, str] = {}
    pct_cls: dict[str, str] = {}

    def fmt_delta_abs(metric: str, v) -> str:
        if pd.isna(v):
            return "—"
        v = float(v)
        sign = "+" if v > 0 else "−" if v < 0 else ""
        vv = abs(v)

        if metric in ("Выручка", "Оборот", "Продажи", "Возвраты"):
            return f"{sign}{_format_money(vv)}"

        if metric == "Кол-во":
            return f"{sign}{_format_int(vv)}"

        if metric in ("Комиссия", "К возвратов"):
            # в абс. разнице показываем п.п.
            return f"{sign}{_format_int(vv)}"

        return f"{sign}{vv}"

    def fmt_delta_pct(v) -> str:
        if pd.isna(v):
            return "—"
        v = float(v)
        sign = "+" if v > 0 else "−" if v < 0 else ""
        return f"{sign}{_format_pct_1(abs(v))}"

    # Δ с правилом: если в предыдущем периоде нет значения — Δ = —
    if "Δ абс." in out.columns or "Δ отн." in out.columns:
        for metric in out.index:
            prev_val = df_pivot.loc[metric, title_left] if title_left in df_pivot.columns else np.nan

            if _prev_missing(prev_val):
                if "Δ абс." in out.columns:
                    out.loc[metric, "Δ абс."] = "—"
                    abs_cls[metric] = ""
                if "Δ отн." in out.columns:
                    out.loc[metric, "Δ отн."] = "—"
                    pct_cls[metric] = ""
                continue

            if "Δ абс." in out.columns:
                vabs = df_pivot.loc[metric, "Δ абс."]
                out.loc[metric, "Δ абс."] = fmt_delta_abs(metric, vabs)
                abs_cls[metric] = (
                    "pos" if (not pd.isna(vabs) and float(vabs) > 0) else
                    "neg" if (not pd.isna(vabs) and float(vabs) < 0) else
                    ""
                )

            if "Δ отн." in out.columns:
                vpct = df_pivot.loc[metric, "Δ отн."]
                out.loc[metric, "Δ отн."] = fmt_delta_pct(vpct)
                pct_cls[metric] = (
                    "pos" if (not pd.isna(vpct) and float(vpct) > 0) else
                    "neg" if (not pd.isna(vpct) and float(vpct) < 0) else
                    ""
                )

    cols = [c for c in [title_left, title_right, "Δ абс.", "Δ отн."] if c in out.columns]

    rows_html = []
    for metric in out.index:
        tds = [f"<td class='metric'>{metric}</td>"]
        for c in cols:
            if c == "Δ абс.":
                cls = abs_cls.get(metric, "")
                tds.append(f"<td class='num {cls}'>{out.loc[metric, c]}</td>")
            elif c == "Δ отн.":
                cls = pct_cls.get(metric, "")
                tds.append(f"<td class='num {cls}'>{out.loc[metric, c]}</td>")
            else:
                tds.append(f"<td class='num'>{out.loc[metric, c]}</td>")
        rows_html.append("<tr>" + "".join(tds) + "</tr>")

    thead = (
        "<thead><tr>"
        "<th>Метрика</th>"
        + "".join(f"<th>{c}</th>" for c in cols)
        + "</tr></thead>"
    )

    html = "<table class='tbl'>" + thead + "<tbody>" + "".join(rows_html) + "</tbody></table>"
    return {"html": html}


def _aggregate_period(df: pd.DataFrame, period_col: str) -> pd.DataFrame:
    """
    Аггрегация по периоду:
    - суммируем денежные/кол-во (NUM_COLS)
    - по комиссии и доле возвратов считаем средневзвешенно:
        comission: вес = amount (оборот) или revenue (выручка) — выбираем amount если есть
        rtr_ratio: вес = sales или amount (в зависимости от смысла) — выберем sales если есть
    """
    out = df.copy()

    # базовая сумма
    g = out.drop(columns=["date"]).groupby(period_col, as_index=False)[[c for c in NUM_COLS if c in out.columns]].sum()

    # комиссии: средневзвешенная по amount (если нет — по revenue)
    if "comission" in out.columns:
        w_col = "amount" if "amount" in out.columns else ("revenue" if "revenue" in out.columns else None)
        if w_col:
            tmp = out[[period_col, "comission", w_col]].copy()
            tmp = tmp.dropna(subset=["comission", w_col])
            tmp["w"] = tmp[w_col].fillna(0)
            tmp["wx"] = tmp["comission"] * tmp["w"]
            com = tmp.groupby(period_col, as_index=False).agg(w=("w", "sum"), wx=("wx", "sum"))
            com["comission"] = (com["wx"] / com["w"].replace(0, np.nan)).fillna(0)
            g = g.merge(com[[period_col, "comission"]], on=period_col, how="left")
        else:
            g["comission"] = 0

    # доля возвратов: если есть rtr_ratio уже готовая — средняя взвешенная по sales (или amount)
    if "rtr_ratio" in out.columns:
        w_col = "sales" if "sales" in out.columns else ("amount" if "amount" in out.columns else None)
        if w_col:
            tmp = out[[period_col, "rtr_ratio", w_col]].copy()
            tmp = tmp.dropna(subset=["rtr_ratio", w_col])
            tmp["w"] = tmp[w_col].fillna(0)
            tmp["wx"] = tmp["rtr_ratio"] * tmp["w"]
            rr = tmp.groupby(period_col, as_index=False).agg(w=("w", "sum"), wx=("wx", "sum"))
            rr["rtr_ratio"] = (rr["wx"] / rr["w"].replace(0, np.nan)).fillna(0)
            g = g.merge(rr[[period_col, "rtr_ratio"]], on=period_col, how="left")
        else:
            g["rtr_ratio"] = 0

    return g


def build_mtd_table(df_raw: pd.DataFrame) -> dict:
    df = _ensure_raw_columns(df_raw)

    required = {"date", "revenue", "amount", "comission", "quant", "sales", "rtr", "rtr_ratio"}
    if not required.issubset(set(df.columns)):
        missing = sorted(list(required - set(df.columns)))
        return {"html": f"<div class='note'>Нет колонок для отчёта: {', '.join(missing)}</div>"}

    df = _coerce_numeric(df)

    df["month"] = pd.to_datetime(df["date"], errors="coerce").dt.strftime("MTD %b %y").str.upper()
    df = df.dropna(subset=["month"])

    df_agg = _aggregate_period(df, "month")
    if df_agg.empty:
        return {"html": "<div class='note'>Нет данных за период MTD</div>"}

    df_agg = df_agg.rename(columns=RENAMING_COLS)

    # собираем pivot
    df_long = df_agg.melt(
        id_vars="month",
        value_vars=ORDER_METRICS,
        var_name="Метрика",
        value_name="value",
    )
    pivot = df_long.pivot_table(index="Метрика", columns="month", values="value", aggfunc="first")

    if pivot.shape[1] < 2:
        return {"html": "<div class='note'>Недостаточно данных для сравнения (нужно 2 периода)</div>"}

    c0, c1 = pivot.columns[:2]
    pivot["Δ абс."] = pivot[c1] - pivot[c0]

    # Δ отн. для % метрик считаем как относительное изменение (в %), но на скрине у тебя выглядит как обычная %
    # поэтому оставляем формулу как раньше (Δ/база*100) для всех строк — будет одинаково.
    pivot["Δ отн."] = pivot["Δ абс."] / pivot[c0].replace(0, pd.NA) * 100

    pivot = pivot.reindex(ORDER_METRICS)
    return _to_print_table(pivot, c0, c1)


def build_ytd_table(df_raw: pd.DataFrame) -> dict:
    df = _ensure_raw_columns(df_raw)

    required = {"date", "revenue", "amount", "comission", "quant", "sales", "rtr", "rtr_ratio"}
    if not required.issubset(set(df.columns)):
        missing = sorted(list(required - set(df.columns)))
        return {"html": f"<div class='note'>Нет колонок для отчёта: {', '.join(missing)}</div>"}

    df = _coerce_numeric(df)

    df["period"] = pd.to_datetime(df["date"], errors="coerce").dt.strftime("YTD %Y").str.upper()
    df = df.dropna(subset=["period"])

    df_agg = _aggregate_period(df, "period")
    if df_agg.empty:
        return {"html": "<div class='note'>Нет данных за период YTD</div>"}

    df_agg = df_agg.rename(columns=RENAMING_COLS)

    df_long = df_agg.melt(
        id_vars="period",
        value_vars=ORDER_METRICS,
        var_name="Метрика",
        value_name="value",
    )
    pivot = df_long.pivot_table(index="Метрика", columns="period", values="value", aggfunc="first")

    if pivot.shape[1] < 2:
        return {"html": "<div class='note'>Недостаточно данных для сравнения (нужно 2 периода)</div>"}

    c0, c1 = pivot.columns[:2]
    pivot["Δ абс."] = pivot[c1] - pivot[c0]
    pivot["Δ отн."] = pivot["Δ абс."] / pivot[c0].replace(0, pd.NA) * 100

    pivot = pivot.reindex(ORDER_METRICS)
    return _to_print_table(pivot, c0, c1)
