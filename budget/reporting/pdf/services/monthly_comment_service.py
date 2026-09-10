from __future__ import annotations

from typing import Any
from calendar import monthrange

import pandas as pd

from budget.reporting.pdf.services.sales_data_service import _format_money
from conns import get_duckdb_conn


def _safe_pct_change(current: float, base: float) -> float:
    if base in (0, None):
        return 0.0
    return (current / base - 1) * 100


def _fmt_pct(x: float) -> str:
    return f"{x:+.1f}%"


def _month_start(dt) -> pd.Timestamp:
    ts = pd.to_datetime(dt)
    return pd.Timestamp(year=ts.year, month=ts.month, day=1)


def _month_end(dt) -> pd.Timestamp:
    ts = pd.to_datetime(dt)
    last_day = monthrange(ts.year, ts.month)[1]
    return pd.Timestamp(year=ts.year, month=ts.month, day=last_day)


def _get_period_label(row: pd.Series) -> str:
    start = pd.to_datetime(row["start"])
    end = pd.to_datetime(row["end"])
    return f"{start.strftime('%d.%m.%Y')} – {end.strftime('%d.%m.%Y')}"


def _normalize_months_df(months_12: list[dict[str, Any]]) -> pd.DataFrame:
    df = pd.DataFrame(months_12).copy()
    if df.empty:
        return df

    if "start" in df.columns:
        df["start"] = pd.to_datetime(df["start"])
    else:
        df["start"] = pd.to_datetime(df["month_label"].str[:7], format="%m.%Y", errors="coerce")

    if "end" in df.columns:
        df["end"] = pd.to_datetime(df["end"])
    else:
        df["end"] = df["start"].apply(_month_end)

    numeric_cols = [
        "sales_amount",
        "returns_amount",
        "net_amount",
        "sales_qty",
        "returns_qty",
        "net_qty",
        "avg_price",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    if "is_closed_month" not in df.columns:
        latest_end = df["end"].max()
        df["is_closed_month"] = df["end"] < latest_end

    if "is_current_month" not in df.columns:
        latest_start = df["start"].max()
        df["is_current_month"] = df["start"] == latest_start

    return df.sort_values("start").reset_index(drop=True)


def build_monthly_trends_comment(months_12: list[dict[str, Any]]) -> dict | None:
    """
    Комментарий строится по последнему закрытому месяцу.
    Если есть текущий MTD, он выводится только как предварительная информация.
    """

    if not months_12:
        return None

    df = _normalize_months_df(months_12)
    if df.empty:
        return None

    closed_df = df[df["is_closed_month"] == True].copy()
    if closed_df.empty or len(closed_df) < 2:
        return None

    closed_df = closed_df.tail(12).copy()

    last_closed = closed_df.iloc[-1]
    prev_closed = closed_df.iloc[-2]

    open_df = df[df["is_current_month"] == True].copy()
    has_open_month = not open_df.empty
    current_open = open_df.iloc[-1] if has_open_month else None

    last_net = float(last_closed.get("net_amount", 0) or 0)
    prev_net = float(prev_closed.get("net_amount", 0) or 0)

    last_sales_qty = float(last_closed.get("sales_qty", 0) or 0)
    prev_sales_qty = float(prev_closed.get("sales_qty", 0) or 0)

    last_returns_amount = float(last_closed.get("returns_amount", 0) or 0)
    prev_returns_amount = float(prev_closed.get("returns_amount", 0) or 0)

    last_avg_price = float(last_closed.get("avg_price", 0) or 0)
    prev_avg_price = float(prev_closed.get("avg_price", 0) or 0)

    avg_net_12m = float(closed_df["net_amount"].mean()) if "net_amount" in closed_df.columns else 0

    net_vs_prev_pct = _safe_pct_change(last_net, prev_net)
    net_vs_avg_pct = _safe_pct_change(last_net, avg_net_12m)

    qty_vs_prev_pct = _safe_pct_change(last_sales_qty, prev_sales_qty)
    price_vs_prev_pct = _safe_pct_change(last_avg_price, prev_avg_price)
    returns_vs_prev_pct = _safe_pct_change(last_returns_amount, prev_returns_amount)

    volatility = (
        float(closed_df["net_amount"].std()) / avg_net_12m
        if avg_net_12m not in (0, None) and len(closed_df) > 1
        else 0
    )

    if volatility < 0.08:
        stability_text = "Динамика чистой выручки за анализируемый период характеризуется низкой волатильностью."
    elif volatility < 0.18:
        stability_text = "Динамика чистой выручки за анализируемый период остается умеренно волатильной."
    else:
        stability_text = "Динамика чистой выручки за анализируемый период характеризуется повышенной волатильностью."

    if net_vs_prev_pct >= 5:
        trend_text = "зафиксирован заметный рост"
        trend_class = "positive"
    elif net_vs_prev_pct <= -5:
        trend_text = "зафиксировано заметное снижение"
        trend_class = "negative"
    elif net_vs_prev_pct > 0:
        trend_text = "зафиксирован умеренный рост"
        trend_class = "positive"
    elif net_vs_prev_pct < 0:
        trend_text = "зафиксировано умеренное снижение"
        trend_class = "negative"
    else:
        trend_text = "существенных изменений не зафиксировано"
        trend_class = "neutral"

    if abs(qty_vs_prev_pct) > abs(price_vs_prev_pct):
        driver_text = (
            f"Ключевым драйвером изменения выступила динамика количества продаж "
            f"({_fmt_pct(qty_vs_prev_pct)} к предыдущему закрытому месяцу), "
            f"тогда как средняя цена изменилась на {_fmt_pct(price_vs_prev_pct)}."
        )
    elif abs(price_vs_prev_pct) > abs(qty_vs_prev_pct):
        driver_text = (
            f"Ключевым драйвером изменения выступила динамика средней цены "
            f"({_fmt_pct(price_vs_prev_pct)} к предыдущему закрытому месяцу), "
            f"при изменении количества продаж на {_fmt_pct(qty_vs_prev_pct)}."
        )
    else:
        driver_text = (
            f"Изменение было сформировано сопоставимым влиянием количества продаж "
            f"({_fmt_pct(qty_vs_prev_pct)}) и средней цены ({_fmt_pct(price_vs_prev_pct)})."
        )

    if last_returns_amount > prev_returns_amount:
        returns_text = (
            f"Объем возвратов за месяц составил {_format_money(last_returns_amount)} руб., "
            f"что на {_fmt_pct(abs(returns_vs_prev_pct))} выше предыдущего закрытого месяца."
        )
    elif last_returns_amount < prev_returns_amount:
        returns_text = (
            f"Объем возвратов за месяц составил {_format_money(last_returns_amount)} руб., "
            f"что на {_fmt_pct(-abs(returns_vs_prev_pct))} ниже предыдущего закрытого месяца."
        )
    else:
        returns_text = (
            f"Объем возвратов за месяц составил {_format_money(last_returns_amount)} руб. "
            f"и остался на уровне предыдущего закрытого месяца."
        )

    comment = (
        f"По итогам закрытого месяца {_get_period_label(last_closed)} {trend_text} чистой выручки: "
        f"{_format_money(last_net)} руб. против {_format_money(prev_net)} руб. месяцем ранее "
        f"({_fmt_pct(net_vs_prev_pct)}). "
        f"Относительно среднего уровня за последние 12 закрытых месяцев "
        f"({_format_money(avg_net_12m)} руб.) показатель отклонился на {_fmt_pct(net_vs_avg_pct)}. "
        f"{driver_text} {returns_text}"
    )

    note = stability_text

    open_month_note = None
    if has_open_month and current_open is not None:
        open_net = float(current_open.get("net_amount", 0) or 0)
        open_period = _get_period_label(current_open)
        open_month_note = (
            f"По текущему незакрытому периоду {open_period} накопленная чистая выручка составляет "
            f"{_format_money(open_net)} руб. Данные предварительные и не используются "
            f"для итоговой интерпретации месячной динамики."
        )

    return {
        "value": _fmt_pct(net_vs_prev_pct),
        "comment": comment,
        "note": note,
        "open_month_note": open_month_note,
        "class": trend_class,
        "last_closed_month_start": pd.to_datetime(last_closed["start"]).date(),
        "last_closed_month_end": pd.to_datetime(last_closed["end"]).date(),
    }


def get_top_categories_for_closed_month(month_start, month_end, limit: int = 5) -> list[dict]:
    conn = get_duckdb_conn()

    query = """
        WITH cards_dim AS (
            SELECT
                nm_id,
                ANY_VALUE(json_extract_string(payload_raw, '$.subjectName')) AS subject_name
            FROM cards
            GROUP BY nm_id
        ),
        base AS (
            SELECT
                s.nm_id,
                SUM(CASE WHEN s.dtn_id = 2 AND s.field = 'retail_price' THEN s.value ELSE 0 END) / 100.0 AS sales_amount,
                SUM(CASE WHEN s.dtn_id = 1 AND s.field = 'retail_price' THEN s.value ELSE 0 END) / 100.0 AS returns_amount
            FROM sales s
            WHERE s.field = 'retail_price'
              AND CAST(s.date_from AS DATE) BETWEEN ? AND ?
            GROUP BY s.nm_id
        )
        SELECT
            COALESCE(c.subject_name, 'Не указана') AS subject_name,
            SUM(b.sales_amount - b.returns_amount) AS net_amount
        FROM base b
        LEFT JOIN cards_dim c
            ON b.nm_id = c.nm_id
        GROUP BY 1
        HAVING SUM(b.sales_amount - b.returns_amount) > 0
        ORDER BY net_amount DESC
        LIMIT ?
    """

    rows = conn.execute(query, [month_start, month_end, limit]).df().to_dict("records")
    conn.close()
    return rows


def get_top_products_for_closed_month(month_start, month_end, limit: int = 5) -> list[dict]:
    conn = get_duckdb_conn()

    query = """
        WITH product_dim AS (
            SELECT
                nm_id,
                ANY_VALUE(title) AS product_name,
                ANY_VALUE(brand) AS brand
            FROM product
            GROUP BY nm_id
        ),
        base AS (
            SELECT
                s.nm_id,
                SUM(CASE WHEN s.dtn_id = 2 AND s.field = 'retail_price' THEN s.value ELSE 0 END) / 100.0 AS sales_amount,
                SUM(CASE WHEN s.dtn_id = 1 AND s.field = 'retail_price' THEN s.value ELSE 0 END) / 100.0 AS returns_amount
            FROM sales s
            WHERE s.field = 'retail_price'
              AND CAST(s.date_from AS DATE) BETWEEN ? AND ?
            GROUP BY s.nm_id
        )
        SELECT
            b.nm_id,
            COALESCE(p.product_name, '—') AS product_name,
            COALESCE(p.brand, '—') AS brand,
            (b.sales_amount - b.returns_amount) AS net_amount
        FROM base b
        LEFT JOIN product_dim p
            ON b.nm_id = p.nm_id
        WHERE (b.sales_amount - b.returns_amount) > 0
        ORDER BY net_amount DESC
        LIMIT ?
    """

    rows = conn.execute(query, [month_start, month_end, limit]).df().to_dict("records")
    conn.close()
    return rows


def build_monthly_extended_comment(months_12: list[dict[str, Any]]) -> dict | None:
    base = build_monthly_trends_comment(months_12)
    if not base:
        return None

    month_start = base["last_closed_month_start"]
    month_end = base["last_closed_month_end"]

    top_categories = get_top_categories_for_closed_month(month_start, month_end, limit=5)
    top_products = get_top_products_for_closed_month(month_start, month_end, limit=5)

    top_categories = [
        {
            **row,
            "net_amount_fmt": _format_money(row["net_amount"])
        }
        for row in top_categories
    ]

    top_products = [
        {
            **row,
            "net_amount_fmt": _format_money(row["net_amount"])
        }
        for row in top_products
    ]

    return {
        **base,
        "top_categories": top_categories,
        "top_products": top_products,
    }