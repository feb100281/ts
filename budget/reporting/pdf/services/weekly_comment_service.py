# budget/reporting/pdf/services/weekly_comment_service.py

from __future__ import annotations

from typing import Any
import pandas as pd

from budget.reporting.pdf.services.sales_data_service import _format_money


def _safe_pct_change(current: float, base: float) -> float:
    if base in (0, None):
        return 0.0
    return (current / base - 1) * 100


def _fmt_pct(x: float) -> str:
    return f"{x:+.1f}%"


def _get_period_label(row: pd.Series) -> str:
    return (
        pd.to_datetime(row["week_start"]).strftime("%d.%m.%Y")
        + " – " +
        pd.to_datetime(row["week_end"]).strftime("%d.%m.%Y")
    )


def build_weekly_trends_comment(weekly_trends: list[dict[str, Any]]) -> dict | None:
    """
    Комментарий строится только по последней закрытой неделе.
    Если есть незакрытая неделя, она выводится только как предварительная информация.
    """

    if not weekly_trends:
        return None

    df = pd.DataFrame(weekly_trends).copy()
    if df.empty:
        return None

    df["week_start"] = pd.to_datetime(df["week_start"])
    df["week_end"] = pd.to_datetime(df["week_end"])

    today = pd.Timestamp.today().normalize()

    # закрытые недели
    closed_df = df[df["week_end"] < today].copy()
    if closed_df.empty or len(closed_df) < 2:
        return None

    closed_df = closed_df.sort_values("week_start").tail(12).copy()

    last_closed = closed_df.iloc[-1]
    prev_closed = closed_df.iloc[-2]

    # есть ли незакрытая неделя
    open_df = df[df["week_end"] >= today].copy()
    has_open_week = not open_df.empty
    current_open = open_df.sort_values("week_start").iloc[-1] if has_open_week else None

    # показатели
    last_net = float(last_closed.get("net_amount", 0) or 0)
    prev_net = float(prev_closed.get("net_amount", 0) or 0)
    last_sales_qty = float(last_closed.get("sales_qty", 0) or 0)
    prev_sales_qty = float(prev_closed.get("sales_qty", 0) or 0)
    last_returns_amount = float(last_closed.get("returns_amount", 0) or 0)
    prev_returns_amount = float(prev_closed.get("returns_amount", 0) or 0)
    last_avg_price = float(last_closed.get("avg_price", 0) or 0)
    prev_avg_price = float(prev_closed.get("avg_price", 0) or 0)

    avg_net_12w = float(closed_df["net_amount"].mean()) if "net_amount" in closed_df.columns else 0

    net_vs_prev_pct = _safe_pct_change(last_net, prev_net)
    net_vs_avg_pct = _safe_pct_change(last_net, avg_net_12w)

    qty_vs_prev_pct = _safe_pct_change(last_sales_qty, prev_sales_qty)
    price_vs_prev_pct = _safe_pct_change(last_avg_price, prev_avg_price)
    returns_vs_prev_pct = _safe_pct_change(last_returns_amount, prev_returns_amount)

    # волатильность
    volatility = (
        float(closed_df["net_amount"].std()) / avg_net_12w
        if avg_net_12w not in (0, None) and len(closed_df) > 1
        else 0
    )

    if volatility < 0.08:
        stability_text = "Динамика чистой выручки за анализируемый период характеризуется низкой волатильностью."
    elif volatility < 0.18:
        stability_text = "Динамика чистой выручки за анализируемый период остается умеренно волатильной."
    else:
        stability_text = "Динамика чистой выручки за анализируемый период характеризуется повышенной волатильностью."

    # основной вектор
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

    # драйвер
    if abs(qty_vs_prev_pct) > abs(price_vs_prev_pct):
        driver_text = (
            f"Ключевым драйвером изменения выступила динамика количества продаж "
            f"({_fmt_pct(qty_vs_prev_pct)} к предыдущей закрытой неделе), "
            f"тогда как средняя цена изменилась на {_fmt_pct(price_vs_prev_pct)}."
        )
    elif abs(price_vs_prev_pct) > abs(qty_vs_prev_pct):
        driver_text = (
            f"Ключевым драйвером изменения выступила динамика средней цены "
            f"({_fmt_pct(price_vs_prev_pct)} к предыдущей закрытой неделе), "
            f"при изменении количества продаж на {_fmt_pct(qty_vs_prev_pct)}."
        )
    else:
        driver_text = (
            f"Изменение было сформировано сопоставимым влиянием количества продаж "
            f"({_fmt_pct(qty_vs_prev_pct)}) и средней цены ({_fmt_pct(price_vs_prev_pct)})."
        )

    # возвраты
    if last_returns_amount > prev_returns_amount:
        returns_text = (
            f"Объем возвратов за неделю составил {_format_money(last_returns_amount)} руб., "
            f"что на {_fmt_pct(abs(returns_vs_prev_pct))} выше предыдущей закрытой недели."
        )
    elif last_returns_amount < prev_returns_amount:
        returns_text = (
            f"Объем возвратов за неделю составил {_format_money(last_returns_amount)} руб., "
            f"что на {_fmt_pct(-abs(returns_vs_prev_pct))} ниже предыдущей закрытой недели."
        )
    else:
        returns_text = (
            f"Объем возвратов за неделю составил {_format_money(last_returns_amount)} руб. "
            f"и остался на уровне предыдущей закрытой недели."
        )

    # вводный комментарий
    comment = (
        f"По итогам закрытой недели { _get_period_label(last_closed) } {trend_text} чистой выручки: "
        f"{_format_money(last_net)} руб. против {_format_money(prev_net)} руб. неделей ранее "
        f"({_fmt_pct(net_vs_prev_pct)}). "
        f"Относительно среднего уровня за последние 12 закрытых недель "
        f"({_format_money(avg_net_12w)} руб.) показатель отклонился на {_fmt_pct(net_vs_avg_pct)}. "
        f"{driver_text} {returns_text}"
    )

    note = stability_text

    open_week_note = None
    if has_open_week and current_open is not None:
        open_net = float(current_open.get("net_amount", 0) or 0)
        open_period = _get_period_label(current_open)
        open_week_note = (
            f"По текущей незакрытой неделе {open_period} накопленная чистая выручка составляет "
            f"{_format_money(open_net)} руб. Данные предварительные и не используются "
            f"для итоговой интерпретации недельной динамики."
        )

    return {
        "value": _fmt_pct(net_vs_prev_pct),
        "comment": comment,
        "note": note,
        "open_week_note": open_week_note,
        "class": trend_class,
        "last_closed_week_start": pd.to_datetime(last_closed["week_start"]).date(),
        "last_closed_week_end": pd.to_datetime(last_closed["week_end"]).date(),
    }
    
    
    
from budget.reporting.pdf.services.sales_data_service import get_duckdb_conn


def get_top_categories_for_closed_week(week_start, week_end, limit: int = 3) -> list[dict]:
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

    rows = conn.execute(query, [week_start, week_end, limit]).df().to_dict("records")
    conn.close()
    return rows


def get_top_products_for_closed_week(week_start, week_end, limit: int = 3) -> list[dict]:
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

    rows = conn.execute(query, [week_start, week_end, limit]).df().to_dict("records")
    conn.close()
    return rows


def build_weekly_extended_comment(weekly_trends: list[dict]) -> dict | None:
    base = build_weekly_trends_comment(weekly_trends)
    if not base:
        return None

    week_start = base["last_closed_week_start"]
    week_end = base["last_closed_week_end"]

    top_categories = get_top_categories_for_closed_week(week_start, week_end, limit=5)
    top_products = get_top_products_for_closed_week(week_start, week_end, limit=5)

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