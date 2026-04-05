# budget/reporting/pdf/sales_kpi.py
from __future__ import annotations

from calendar import monthrange
from datetime import date, timedelta
from pathlib import Path

import duckdb
import pandas as pd
from django.conf import settings


DUCK_FILE = Path(settings.BASE_DIR) / "data" / "analytics.duckdb"


def _format_money(value):
    if value is None:
        return "—"
    return f"{value:,.2f}".replace(",", " ").replace(".00", "")


def _format_qty(value):
    if value is None:
        return "—"
    return f"{int(round(value)):,}".replace(",", " ")


def _format_percent(value):
    if value is None:
        return "—"
    return f"{value:.1f}%".replace(".", ",")


def _safe_pct_change(current, previous):
    if previous in (None, 0):
        return None
    return (current / previous - 1) * 100


def _month_start(dt: date) -> date:
    return dt.replace(day=1)


def _month_end(dt: date) -> date:
    return dt.replace(day=monthrange(dt.year, dt.month)[1])


def _same_day_or_month_end(target_month_start: date, reference_day: int) -> date:
    last_day = monthrange(target_month_start.year, target_month_start.month)[1]
    return target_month_start.replace(day=min(reference_day, last_day))


def _period_metrics(df: pd.DataFrame, start_date: date, end_date: date) -> dict:
    mask = (df["dt"] >= pd.Timestamp(start_date)) & (df["dt"] <= pd.Timestamp(end_date))
    x = df.loc[mask].copy()

    sales_amount = float(x["sales_amount"].sum())
    returns_amount = float(x["returns_amount"].sum())
    net_amount = float(x["net_amount"].sum())

    sales_qty = int(x["sales_qty"].sum())
    returns_qty = int(x["returns_qty"].sum())
    net_qty = int(x["net_qty"].sum())

    avg_price = (sales_amount / sales_qty) if sales_qty else None

    return {
        "sales_amount": sales_amount,
        "returns_amount": returns_amount,
        "net_amount": net_amount,
        "sales_qty": sales_qty,
        "returns_qty": returns_qty,
        "net_qty": net_qty,
        "avg_price": avg_price,
    }


def _trend_label(value):
    if value is None:
        return "без базы для сравнения", "flat"
    if value > 0.1:
        return f"рост на {_format_percent(value)}", "up"
    if value < -0.1:
        return f"снижение на {_format_percent(abs(value))}", "down"
    return "без существенных изменений", "flat"


def _get_daily_sales_df() -> pd.DataFrame:
    conn = duckdb.connect(str(DUCK_FILE))

    query = """
        SELECT
            CAST(date_from AS DATE) AS dt,
            SUM(CASE WHEN dtn_id = 2 AND field = 'retail_price' THEN value ELSE 0 END) / 100.0 AS sales_amount,
            SUM(CASE WHEN dtn_id = 1 AND field = 'retail_price' THEN value ELSE 0 END) / 100.0 AS returns_amount,
            COUNT(*) FILTER (WHERE dtn_id = 2 AND field = 'retail_price') AS sales_qty,
            COUNT(*) FILTER (WHERE dtn_id = 1 AND field = 'retail_price') AS returns_qty
        FROM sales
        WHERE field = 'retail_price'
        GROUP BY 1
        ORDER BY 1
    """
    df = conn.execute(query).df()
    conn.close()

    if df.empty:
        df = pd.DataFrame(columns=["dt", "sales_amount", "returns_amount", "sales_qty", "returns_qty"])

    df["dt"] = pd.to_datetime(df["dt"])
    df["sales_amount"] = df["sales_amount"].fillna(0.0)
    df["returns_amount"] = df["returns_amount"].fillna(0.0)
    df["sales_qty"] = df["sales_qty"].fillna(0).astype(int)
    df["returns_qty"] = df["returns_qty"].fillna(0).astype(int)

    df["net_amount"] = df["sales_amount"] - df["returns_amount"]
    df["net_qty"] = df["sales_qty"] - df["returns_qty"]

    return df


def _build_12m_rows(df: pd.DataFrame, latest_date: date) -> list[dict]:
    current_month_start = _month_start(latest_date)

    months = []
    for i in range(11, -1, -1):
        anchor = current_month_start - pd.DateOffset(months=i)
        anchor = pd.Timestamp(anchor).date()
        start = anchor.replace(day=1)
        end = latest_date if start == current_month_start else _month_end(start)

        metrics = _period_metrics(df, start, end)

        label = start.strftime("%m.%Y")
        if start == current_month_start:
            label += " MTD"

        months.append({
            "month_label": label,
            "start": start,
            "end": end,
            "sales_amount": metrics["sales_amount"],
            "returns_amount": metrics["returns_amount"],
            "net_amount": metrics["net_amount"],
            "sales_qty": metrics["sales_qty"],
            "returns_qty": metrics["returns_qty"],
            "net_qty": metrics["net_qty"],
            "avg_price": metrics["avg_price"],
        })

    for i, row in enumerate(months):
        prev = months[i - 1] if i > 0 else None

        row["net_change_pct"] = _safe_pct_change(
            row["net_amount"], prev["net_amount"] if prev else None
        )
        row["avg_price_change_pct"] = _safe_pct_change(
            row["avg_price"], prev["avg_price"] if prev else None
        )
        row["qty_change_pct"] = _safe_pct_change(
            row["sales_qty"], prev["sales_qty"] if prev else None
        )

        if row["net_change_pct"] is None:
            row["net_trend"] = "→"
            row["net_trend_class"] = "flat"
        elif row["net_change_pct"] > 0.1:
            row["net_trend"] = "▲"
            row["net_trend_class"] = "up"
        elif row["net_change_pct"] < -0.1:
            row["net_trend"] = "▼"
            row["net_trend_class"] = "down"
        else:
            row["net_trend"] = "→"
            row["net_trend_class"] = "flat"

        row["sales_amount_fmt"] = _format_money(row["sales_amount"])
        row["returns_amount_fmt"] = _format_money(row["returns_amount"])
        row["net_amount_fmt"] = _format_money(row["net_amount"])
        row["sales_qty_fmt"] = _format_qty(row["sales_qty"])
        row["returns_qty_fmt"] = _format_qty(row["returns_qty"])
        row["net_qty_fmt"] = _format_qty(row["net_qty"])
        row["avg_price_fmt"] = _format_money(row["avg_price"])
        row["net_change_pct_fmt"] = _format_percent(row["net_change_pct"])
        row["avg_price_change_pct_fmt"] = _format_percent(row["avg_price_change_pct"])
        row["qty_change_pct_fmt"] = _format_percent(row["qty_change_pct"])

    return months


def _build_driver_rows(months_12: list[dict]) -> list[dict]:
    rows = []

    for i in range(1, len(months_12)):
        prev = months_12[i - 1]
        cur = months_12[i]

        delta_qty_pct = _safe_pct_change(cur["sales_qty"], prev["sales_qty"])
        delta_price_pct = _safe_pct_change(cur["avg_price"], prev["avg_price"])
        delta_net_pct = _safe_pct_change(cur["net_amount"], prev["net_amount"])

        prev_qty = float(prev["sales_qty"] or 0)
        cur_qty = float(cur["sales_qty"] or 0)
        prev_price = float(prev["avg_price"] or 0)
        cur_price = float(cur["avg_price"] or 0)
        prev_net = float(prev["net_amount"] or 0)
        cur_net = float(cur["net_amount"] or 0)

        delta_qty_abs = cur_qty - prev_qty
        delta_price_abs = cur_price - prev_price
        delta_net_abs = cur_net - prev_net

        if abs(delta_qty_pct or 0) > abs(delta_price_pct or 0) * 1.2:
            driver = "Объем"
            driver_class = "up" if delta_qty_abs > 0 else "down" if delta_qty_abs < 0 else "flat"
        elif abs(delta_price_pct or 0) > abs(delta_qty_pct or 0) * 1.2:
            driver = "Цена"
            driver_class = "up" if delta_price_abs > 0 else "down" if delta_price_abs < 0 else "flat"
        else:
            driver = "Смешанный эффект"
            driver_class = "flat"

        if (delta_qty_pct or 0) < -0.1 and (delta_price_pct or 0) < -0.1:
            driver = "Двойной негативный эффект"
            driver_class = "down"
        elif (delta_qty_pct or 0) > 0.1 and (delta_price_pct or 0) > 0.1:
            driver = "Двойной позитивный эффект"
            driver_class = "up"

        rows.append({
            "month_label": cur["month_label"],
            "delta_qty_pct_fmt": _format_percent(delta_qty_pct),
            "delta_price_pct_fmt": _format_percent(delta_price_pct),
            "delta_net_pct_fmt": _format_percent(delta_net_pct),
            "delta_net_abs_fmt": _format_money(delta_net_abs),
            "driver": driver,
            "driver_class": driver_class,
        })

    return rows


def _build_waterfall_data(months_12: list[dict]) -> dict | None:
    if len(months_12) < 2:
        return None

    prev = months_12[-2]
    cur = months_12[-1]

    prev_qty = float(prev["sales_qty"] or 0)
    cur_qty = float(cur["sales_qty"] or 0)
    prev_price = float(prev["avg_price"] or 0)
    cur_price = float(cur["avg_price"] or 0)
    prev_returns = float(prev["returns_amount"] or 0)
    cur_returns = float(cur["returns_amount"] or 0)
    prev_net = float(prev["net_amount"] or 0)
    cur_net = float(cur["net_amount"] or 0)

    qty_effect = (cur_qty - prev_qty) * prev_price if prev_price else 0.0
    price_effect = cur_qty * (cur_price - prev_price) if cur_qty else 0.0
    returns_effect = -(cur_returns - prev_returns)

    bridge_total = qty_effect + price_effect + returns_effect
    residual = (cur_net - prev_net) - bridge_total

    return {
        "start_label": prev["month_label"],
        "end_label": cur["month_label"],
        "start_value": prev_net,
        "end_value": cur_net,
        "steps": [
            {"label": "Эффект объема", "value": qty_effect},
            {"label": "Эффект цены", "value": price_effect},
            {"label": "Эффект возвратов", "value": returns_effect},
            {"label": "Прочие/округление", "value": residual},
        ],
    }


def _build_daily_rows_90(df: pd.DataFrame, latest_date: date) -> list[dict]:
    start_date = latest_date - timedelta(days=89)
    x = df[(df["dt"] >= pd.Timestamp(start_date)) & (df["dt"] <= pd.Timestamp(latest_date))].copy()

    rows = []
    for _, row in x.iterrows():
        sales_qty = float(row["sales_qty"] or 0)
        sales_amount = float(row["sales_amount"] or 0)
        avg_price = (sales_amount / sales_qty) if sales_qty else None

        rows.append({
            "date_label": row["dt"].strftime("%d.%m"),
            "dt": row["dt"].date(),
            "sales_qty": sales_qty,
            "sales_amount": sales_amount,
            "returns_amount": float(row["returns_amount"] or 0),
            "net_amount": float(row["net_amount"] or 0),
            "avg_price": avg_price,
        })

    return rows


def build_sales_kpi_context() -> dict:
    df = _get_daily_sales_df()

    if df.empty:
        return {"sales_block": None}

    latest_date = df["dt"].max().date()
    day_num = latest_date.day

    mtd_start = _month_start(latest_date)
    mtd_end = latest_date
    mtd = _period_metrics(df, mtd_start, mtd_end)

    prev_month_anchor = mtd_start - timedelta(days=1)
    prev_month_start = _month_start(prev_month_anchor)
    prev_month_end = _same_day_or_month_end(prev_month_start, day_num)
    prev_mtd = _period_metrics(df, prev_month_start, prev_month_end)

    ly_month_start = mtd_start.replace(year=mtd_start.year - 1)
    ly_month_end = _same_day_or_month_end(ly_month_start, day_num)
    ly_mtd = _period_metrics(df, ly_month_start, ly_month_end)

    ytd_start = date(latest_date.year, 1, 1)
    ytd = _period_metrics(df, ytd_start, latest_date)

    ly_ytd_end = latest_date.replace(year=latest_date.year - 1)
    ly_ytd_start = date(ly_ytd_end.year, 1, 1)
    ly_ytd = _period_metrics(df, ly_ytd_start, ly_ytd_end)

    vs_prev_month_pct = _safe_pct_change(mtd["net_amount"], prev_mtd["net_amount"])
    vs_ly_pct = _safe_pct_change(mtd["net_amount"], ly_mtd["net_amount"])
    ytd_vs_ly_pct = _safe_pct_change(ytd["net_amount"], ly_ytd["net_amount"])

    vs_prev_month_text, vs_prev_month_class = _trend_label(vs_prev_month_pct)
    vs_ly_text, vs_ly_class = _trend_label(vs_ly_pct)
    ytd_vs_ly_text, ytd_vs_ly_class = _trend_label(ytd_vs_ly_pct)

    months_12 = _build_12m_rows(df, latest_date)
    driver_rows = _build_driver_rows(months_12)
    waterfall_data = _build_waterfall_data(months_12)
    daily_rows_90 = _build_daily_rows_90(df, latest_date)

    narrative = (
        f"По состоянию на {latest_date:%d.%m.%Y} оборот с начала месяца составил "
        f"{_format_money(mtd['sales_amount'])} руб. ({_format_qty(mtd['sales_qty'])} шт.), "
        f"возвраты — {_format_money(mtd['returns_amount'])} руб. "
        f"({_format_qty(mtd['returns_qty'])} шт.), "
        f"чистая выручка — {_format_money(mtd['net_amount'])} руб. "
        f"({_format_qty(mtd['net_qty'])} шт.). "
        f"Средняя цена продажи составила {_format_money(mtd['avg_price'])} руб./шт. "
        f"Относительно аналогичного периода прошлого месяца — {vs_prev_month_text}, "
        f"относительно аналогичного периода прошлого года — {vs_ly_text}. "
        f"С начала года (YTD) чистая выручка составила {_format_money(ytd['net_amount'])} руб.; "
        f"год к году — {ytd_vs_ly_text}."
    )

    return {
        "sales_block": {
            "latest_date": latest_date,
            "narrative": narrative,
            "mtd": {
                "sales_amount": _format_money(mtd["sales_amount"]),
                "returns_amount": _format_money(mtd["returns_amount"]),
                "net_amount": _format_money(mtd["net_amount"]),
                "sales_qty": _format_qty(mtd["sales_qty"]),
                "returns_qty": _format_qty(mtd["returns_qty"]),
                "net_qty": _format_qty(mtd["net_qty"]),
                "avg_price": _format_money(mtd["avg_price"]),
            },
            "compare": {
                "prev_month_period": f"{prev_month_start:%d.%m.%Y} — {prev_month_end:%d.%m.%Y}",
                "ly_period": f"{ly_month_start:%d.%m.%Y} — {ly_month_end:%d.%m.%Y}",
                "vs_prev_month_pct": _format_percent(vs_prev_month_pct),
                "vs_prev_month_class": vs_prev_month_class,
                "vs_ly_pct": _format_percent(vs_ly_pct),
                "vs_ly_class": vs_ly_class,
                "ytd_vs_ly_pct": _format_percent(ytd_vs_ly_pct),
                "ytd_vs_ly_class": ytd_vs_ly_class,
            },
            "ytd": {
                "net_amount": _format_money(ytd["net_amount"]),
                "sales_amount": _format_money(ytd["sales_amount"]),
                "returns_amount": _format_money(ytd["returns_amount"]),
                "sales_qty": _format_qty(ytd["sales_qty"]),
                "returns_qty": _format_qty(ytd["returns_qty"]),
                "net_qty": _format_qty(ytd["net_qty"]),
                "avg_price": _format_money(ytd["avg_price"]),
            },
            "months_12": months_12,
            "driver_rows": driver_rows,
            "waterfall_data": waterfall_data,
            "daily_rows_90": daily_rows_90,
        }
    }