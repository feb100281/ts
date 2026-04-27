# budget/reporting/pdf/services/sales_kpi_service.py
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

from budget.reporting.pdf.services.sales_data_service import get_daily_sales_df
from budget.reporting.pdf.utils.date_utils import (
    month_end,
    month_start,
    same_day_or_month_end,
)
from budget.reporting.pdf.utils.formatters import (
    format_money_compact,
    format_percent_comma,
    format_qty,
)
from budget.reporting.pdf.utils.math_utils import safe_pct_change


MONTHS_RU_SHORT = {
    1: "Янв",
    2: "Фев",
    3: "Мар",
    4: "Апр",
    5: "Май",
    6: "Июн",
    7: "Июл",
    8: "Авг",
    9: "Сен",
    10: "Окт",
    11: "Ноя",
    12: "Дек",
}


def _format_month_label_ru(dt: date, is_current_month: bool = False) -> str:
    """
    date(2025, 4, 1) -> 'Апр 2025'
    для текущего месяца -> 'Апр 2025 MTD'
    """
    label = f"{MONTHS_RU_SHORT.get(dt.month, str(dt.month))} {dt.year}"
    if is_current_month:
        label += " MTD"
    return label


def _period_metrics(df: pd.DataFrame, start_date: date, end_date: date) -> dict:
    mask = (df["dt"] >= pd.Timestamp(start_date)) & (df["dt"] <= pd.Timestamp(end_date))
    x = df.loc[mask].copy()

    sales_amount = float(x["sales_amount"].sum())
    returns_amount = float(x["returns_amount"].sum())
    net_amount = float(x["net_amount"].sum())

    sales_qty = int(x["sales_qty"].sum())
    returns_qty = int(x["returns_qty"].sum())
    net_qty = int(x["net_qty"].sum())

    # ВАЖНО: среднюю цену считаем по чистой выручке, а не по обороту
    avg_price = (net_amount / net_qty) if net_qty else None

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
        return f"рост на {format_percent_comma(value)}", "up"
    if value < -0.1:
        return f"снижение на {format_percent_comma(abs(value))}", "down"
    return "без существенных изменений", "flat"


def _get_fill_level(value: float, min_value: float, max_value: float) -> int:
    """
    Возвращает уровень заливки 0..5 для таблицы по чистой выручке.
    """
    if value is None:
        return 0
    if max_value <= min_value:
        return 3

    ratio = (value - min_value) / (max_value - min_value)

    if ratio >= 0.85:
        return 5
    if ratio >= 0.65:
        return 4
    if ratio >= 0.45:
        return 3
    if ratio >= 0.25:
        return 2
    if ratio > 0:
        return 1
    return 0


def _build_12m_rows(df: pd.DataFrame, latest_date: date) -> list[dict]:
    current_month_start = month_start(latest_date)

    months = []
    for i in range(11, -1, -1):
        anchor = current_month_start - pd.DateOffset(months=i)
        anchor = pd.Timestamp(anchor).date()
        start = anchor.replace(day=1)
        end = latest_date if start == current_month_start else month_end(start)

        metrics = _period_metrics(df, start, end)

        is_current_month = start == current_month_start
        label = _format_month_label_ru(start, is_current_month=is_current_month)

        months.append({
            "month_label": label,
            "start": start,
            "end": end,
            "is_current_month": is_current_month,
            "is_closed_month": not is_current_month,
            "sales_amount": metrics["sales_amount"],
            "returns_amount": metrics["returns_amount"],
            "net_amount": metrics["net_amount"],
            "sales_qty": metrics["sales_qty"],
            "returns_qty": metrics["returns_qty"],
            "net_qty": metrics["net_qty"],
            "avg_price": metrics["avg_price"],  # уже по net_amount / net_qty
        })

    if not months:
        return months

    net_values = [float(row["net_amount"] or 0) for row in months]
    sales_values = [float(row["sales_amount"] or 0) for row in months]
    returns_values = [float(row["returns_amount"] or 0) for row in months]

    max_net = max(net_values) if net_values else 0
    min_net = min(net_values) if net_values else 0
    max_sales = max(sales_values) if sales_values else 0
    max_returns = max(returns_values) if returns_values else 0

    for i, row in enumerate(months):
        prev = months[i - 1] if i > 0 else None

        row["net_change_pct"] = safe_pct_change(
            row["net_amount"], prev["net_amount"] if prev else None
        )
        row["avg_price_change_pct"] = safe_pct_change(
            row["avg_price"], prev["avg_price"] if prev else None
        )
        # ВАЖНО: считаем динамику количества по net_qty, а не по sales_qty
        row["qty_change_pct"] = safe_pct_change(
            row["net_qty"], prev["net_qty"] if prev else None
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

        row["is_max_net"] = float(row["net_amount"] or 0) == max_net
        row["is_min_net"] = float(row["net_amount"] or 0) == min_net

        row["net_bar_pct"] = round((float(row["net_amount"] or 0) / max_net) * 100, 1) if max_net else 0
        row["sales_bar_pct"] = round((float(row["sales_amount"] or 0) / max_sales) * 100, 1) if max_sales else 0
        row["returns_bar_pct"] = round((float(row["returns_amount"] or 0) / max_returns) * 100, 1) if max_returns else 0

        row["sales_amount_fmt"] = format_money_compact(row["sales_amount"])
        row["returns_amount_fmt"] = format_money_compact(row["returns_amount"])
        row["net_amount_fmt"] = format_money_compact(row["net_amount"])
        row["sales_qty_fmt"] = format_qty(row["sales_qty"])
        row["returns_qty_fmt"] = format_qty(row["returns_qty"])
        row["net_qty_fmt"] = format_qty(row["net_qty"])
        row["avg_price_fmt"] = format_money_compact(row["avg_price"])
        row["net_change_pct_fmt"] = format_percent_comma(row["net_change_pct"])
        row["avg_price_change_pct_fmt"] = format_percent_comma(row["avg_price_change_pct"])
        row["qty_change_pct_fmt"] = format_percent_comma(row["qty_change_pct"])

        row["net_fill_level"] = _get_fill_level(
            float(row["net_amount"] or 0),
            min_net,
            max_net,
        )

    return months


def _build_driver_rows(months_12: list[dict]) -> list[dict]:
    rows = []

    for i in range(1, len(months_12)):
        prev = months_12[i - 1]
        cur = months_12[i]

        # ВАЖНО: драйверы считаем по чистым штукам и чистой средней цене
        delta_qty_pct = safe_pct_change(cur["net_qty"], prev["net_qty"])
        delta_price_pct = safe_pct_change(cur["avg_price"], prev["avg_price"])
        delta_net_pct = safe_pct_change(cur["net_amount"], prev["net_amount"])

        prev_qty = float(prev["net_qty"] or 0)
        cur_qty = float(cur["net_qty"] or 0)
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
            "delta_qty_pct_fmt": format_percent_comma(delta_qty_pct),
            "delta_price_pct_fmt": format_percent_comma(delta_price_pct),
            "delta_net_pct_fmt": format_percent_comma(delta_net_pct),
            "delta_net_abs_fmt": format_money_compact(delta_net_abs),
            "driver": driver,
            "driver_class": driver_class,
        })

    return rows


def _build_waterfall_data(months_12: list[dict]) -> dict | None:
    if len(months_12) < 2:
        return None

    prev = months_12[-2]
    cur = months_12[-1]

    # ВАЖНО: используем чистые штуки и цену по чистой выручке
    prev_qty = float(prev["net_qty"] or 0)
    cur_qty = float(cur["net_qty"] or 0)
    prev_price = float(prev["avg_price"] or 0)
    cur_price = float(cur["avg_price"] or 0)
    prev_returns = float(prev["returns_amount"] or 0)
    cur_returns = float(cur["returns_amount"] or 0)
    prev_net = float(prev["net_amount"] or 0)
    cur_net = float(cur["net_amount"] or 0)

    volume_effect = (cur_qty - prev_qty) * prev_price if prev_price else 0.0
    price_effect = cur_qty * (cur_price - prev_price) if cur_qty else 0.0

    # Возвраты показываем отдельно как корректирующий эффект.
    returns_effect = -(cur_returns - prev_returns)
    total_change = cur_net - prev_net

    raw_steps = [
        {"label": "Эффект объема", "value": volume_effect},
        {"label": "Эффект цены", "value": price_effect},
        {"label": "Эффект возвратов", "value": returns_effect},
    ]

    return {
        "start_label": prev["month_label"],
        "end_label": cur["month_label"],
        "start_value": prev_net,
        "end_value": cur_net,
        "steps": raw_steps,

        "prev_qty": prev_qty,
        "current_qty": cur_qty,
        "prev_price": prev_price,
        "current_price": cur_price,
        "prev_returns": prev_returns,
        "current_returns": cur_returns,
        "volume_effect": volume_effect,
        "price_effect": price_effect,
        "returns_effect": returns_effect,
        "total_change": total_change,
    }


def _build_daily_rows_90(df: pd.DataFrame, latest_date: date) -> list[dict]:
    start_date = latest_date - timedelta(days=89)
    x = df[(df["dt"] >= pd.Timestamp(start_date)) & (df["dt"] <= pd.Timestamp(latest_date))].copy()

    rows = []
    for _, row in x.iterrows():
        net_qty = float(row["net_qty"] or 0)
        net_amount = float(row["net_amount"] or 0)
        avg_price = (net_amount / net_qty) if net_qty else None

        rows.append({
            "date_label": row["dt"].strftime("%d.%m"),
            "dt": row["dt"].date(),
            "sales_qty": float(row["sales_qty"] or 0),
            "sales_amount": float(row["sales_amount"] or 0),
            "returns_amount": float(row["returns_amount"] or 0),
            "net_amount": net_amount,
            "net_qty": net_qty,
            "avg_price": avg_price,  # по чистой выручке
        })

    return rows


def build_sales_kpi_context() -> dict:
    df = get_daily_sales_df()

    if df.empty:
        return {"sales_block": None}

    latest_date = df["dt"].max().date()
    day_num = latest_date.day

    mtd_start = month_start(latest_date)
    mtd_end = latest_date
    mtd = _period_metrics(df, mtd_start, mtd_end)

    prev_month_anchor = mtd_start - timedelta(days=1)
    prev_month_start = month_start(prev_month_anchor)
    prev_month_end = same_day_or_month_end(prev_month_start, day_num)
    prev_mtd = _period_metrics(df, prev_month_start, prev_month_end)

    ly_month_start = mtd_start.replace(year=mtd_start.year - 1)
    ly_month_end = same_day_or_month_end(ly_month_start, day_num)
    ly_mtd = _period_metrics(df, ly_month_start, ly_month_end)

    ytd_start = date(latest_date.year, 1, 1)
    ytd = _period_metrics(df, ytd_start, latest_date)

    ly_ytd_end = latest_date.replace(year=latest_date.year - 1)
    ly_ytd_start = date(ly_ytd_end.year, 1, 1)
    ly_ytd = _period_metrics(df, ly_ytd_start, ly_ytd_end)

    vs_prev_month_pct = safe_pct_change(mtd["net_amount"], prev_mtd["net_amount"])
    vs_ly_pct = safe_pct_change(mtd["net_amount"], ly_mtd["net_amount"])
    ytd_vs_ly_pct = safe_pct_change(ytd["net_amount"], ly_ytd["net_amount"])

    vs_prev_month_text, vs_prev_month_class = _trend_label(vs_prev_month_pct)
    vs_ly_text, vs_ly_class = _trend_label(vs_ly_pct)
    ytd_vs_ly_text, ytd_vs_ly_class = _trend_label(ytd_vs_ly_pct)

    months_12 = _build_12m_rows(df, latest_date)
    driver_rows = _build_driver_rows(months_12)
    waterfall_data = _build_waterfall_data(months_12)
    daily_rows_90 = _build_daily_rows_90(df, latest_date)

    narrative = (
        f"По состоянию на {latest_date:%d.%m.%Y} оборот с начала месяца составил "
        f"{format_money_compact(mtd['sales_amount'])} руб. ({format_qty(mtd['sales_qty'])} шт.), "
        f"возвраты — {format_money_compact(mtd['returns_amount'])} руб. "
        f"({format_qty(mtd['returns_qty'])} шт.), "
        f"чистая выручка — {format_money_compact(mtd['net_amount'])} руб. "
        f"({format_qty(mtd['net_qty'])} шт.). "
        f"Средняя цена по чистой выручке составила {format_money_compact(mtd['avg_price'])} руб./шт. "
        f"Относительно аналогичного периода прошлого месяца — {vs_prev_month_text}, "
        f"относительно аналогичного периода прошлого года — {vs_ly_text}. "
        f"С начала года (YTD) чистая выручка составила {format_money_compact(ytd['net_amount'])} руб.; "
        f"год к году — {ytd_vs_ly_text}."
    )

    return {
        "sales_block": {
            "latest_date": latest_date,
            "narrative": narrative,
            "mtd": {
                "sales_amount": format_money_compact(mtd["sales_amount"]),
                "returns_amount": format_money_compact(mtd["returns_amount"]),
                "net_amount": format_money_compact(mtd["net_amount"]),
                "sales_qty": format_qty(mtd["sales_qty"]),
                "returns_qty": format_qty(mtd["returns_qty"]),
                "net_qty": format_qty(mtd["net_qty"]),
                "avg_price": format_money_compact(mtd["avg_price"]),
            },
            "compare": {
                "prev_month_period": f"{prev_month_start:%d.%m.%Y} — {prev_month_end:%d.%m.%Y}",
                "ly_period": f"{ly_month_start:%d.%m.%Y} — {ly_month_end:%d.%m.%Y}",
                "vs_prev_month_pct": format_percent_comma(vs_prev_month_pct),
                "vs_prev_month_class": vs_prev_month_class,
                "vs_ly_pct": format_percent_comma(vs_ly_pct),
                "vs_ly_class": vs_ly_class,
                "ytd_vs_ly_pct": format_percent_comma(ytd_vs_ly_pct),
                "ytd_vs_ly_class": ytd_vs_ly_class,
            },
            "ytd": {
                "net_amount": format_money_compact(ytd["net_amount"]),
                "sales_amount": format_money_compact(ytd["sales_amount"]),
                "returns_amount": format_money_compact(ytd["returns_amount"]),
                "sales_qty": format_qty(ytd["sales_qty"]),
                "returns_qty": format_qty(ytd["returns_qty"]),
                "net_qty": format_qty(ytd["net_qty"]),
                "avg_price": format_money_compact(ytd["avg_price"]),
            },
            "months_12": months_12,
            "driver_rows": driver_rows,
            "waterfall_data": waterfall_data,
            "daily_rows_90": daily_rows_90,
        }
    }