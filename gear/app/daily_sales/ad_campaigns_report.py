# gear/app/daily_sales/ad_campaigns_report.py
"""
Анализ рекламных кампаний WB: аналитическая записка (PDF), детализация
(Excel) и расход по периодам (Excel). Источник — таблицы ads.*.
"""

from __future__ import annotations

import html as html_lib
import logging
from datetime import date, datetime, timedelta
from io import BytesIO

import numpy as np
import pandas as pd
import dash_mantine_components as dmc
from dash import Input, Output, State, dcc, no_update

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.properties import Outline

from . import excel_report_style as style
from .wb_expenses_excel import HISTORY_START, export_menu_item, report_menu_group
from .commercial_review import config as C
from .commercial_review.charts import (
    _fig as _cr_fig,
    _render as _cr_render,
    hbar as _cr_hbar,
    _money_formatter as _cr_money_formatter,
    _pct_formatter as _cr_pct_formatter,
    _short as _cr_short,
    _pct_label as _cr_pct_label,
)

logger = logging.getLogger(__name__)


# ================================================================ параметры
AD_CAMPAIGNS_MENU_ENABLED = True

TOP_CAMPAIGNS_N = 15
TOP_CAMPAIGN_PRODUCTS_N = 5
TOP_PRODUCTS_N = 30
TOP_CHART_N = 10

#: Шкала оценки ДРР: (верхняя граница включительно, оценка).
DRR_RATING_BANDS = [
    (7.0, "Отлично"),
    (9.0, "Нормально"),
]
DRR_RATING_WORST_LABEL = "Плохо"
DRR_HIGH_THRESHOLD = DRR_RATING_BANDS[-1][0]

#: Маржа до рекламы — ориентир для шкалы ДРР, задаётся вручную.
PRE_AD_MARGIN_REFERENCE_PCT = 28.8

DRR_TREND_DELTA = 1.5
CONCENTRATION_THRESHOLD = 50.0
BUDGET_RUNWAY_WARN_DAYS = 14
CAMPAIGN_RUNWAY_WARN_DAYS = 3
RUNWAY_LOOKBACK_DAYS = 7
RECONCILIATION_TOLERANCE_PCT = 5.0
SPIKE_RATIO = 1.25

CAMPAIGN_MIN_SPEND_TO_JUDGE = 500.0
CAMPAIGN_MIN_ORDERS_TO_JUDGE = 3
LOW_STOCK_QTY_THRESHOLD = 5

DAY_SHEET_MAX_DAYS = 366
DAY_SHEET_PRODUCTS_MAX_DAYS = 62

QUALITY_GOOD = "Эффективная"
QUALITY_BAD = "Неэффективная"
QUALITY_LOW = "Мало данных"
QUALITY_ORDER = (QUALITY_GOOD, QUALITY_BAD, QUALITY_LOW)

STATUS_ACTIVE = 9
STATUS_PAUSED = 11

BID_TYPE_NAMES = {"unified": "Единая ставка", "manual": "Ручная ставка"}
PAYMENT_TYPE_NAMES = {"cpm": "За показы (CPM)", "cpc": "За клики (CPC)"}


# ================================================================ ID
AD_CAMPAIGNS_PDF_ITEM_ID = "wb-ad-campaigns-pdf-item"
AD_CAMPAIGNS_EXCEL_ITEM_ID = "wb-ad-campaigns-excel-item"
AD_CAMPAIGNS_PERIODS_ITEM_ID = "wb-ad-campaigns-periods-item"
AD_CAMPAIGNS_PDF_DOWNLOAD_ID = "wb-ad-campaigns-pdf-download"
AD_CAMPAIGNS_EXCEL_DOWNLOAD_ID = "wb-ad-campaigns-excel-download"
AD_CAMPAIGNS_PERIODS_DOWNLOAD_ID = "wb-ad-campaigns-periods-download"
AD_CAMPAIGNS_STATUS_ID = "wb-ad-campaigns-status"
AD_CAMPAIGNS_CLICKS_ID = "wb-ad-campaigns-clicks"

AD_CAMPAIGNS_MENU_KINDS = (
    ("ad_campaigns_pdf", AD_CAMPAIGNS_PDF_ITEM_ID),
    ("ad_campaigns_excel", AD_CAMPAIGNS_EXCEL_ITEM_ID),
    ("ad_campaigns_periods", AD_CAMPAIGNS_PERIODS_ITEM_ID),
)


# ================================================================ форматирование
def _isna(v) -> bool:
    if v is None:
        return True
    try:
        return bool(pd.isna(v))
    except (TypeError, ValueError):
        return False


def _num(v, default=None):
    if _isna(v):
        return default
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _esc(text) -> str:
    return html_lib.escape("" if _isna(text) else str(text))


def _spaced(n: float, digits: int = 0) -> str:
    return f"{n:,.{digits}f}".replace(",", " ").replace(".", ",")


def _money(v, dash="—") -> str:
    v = _num(v)
    if v is None:
        return dash
    return ("−" if round(v) < 0 else "") + _spaced(abs(v)) + " ₽"


def _money_dec(v) -> str:
    v = _num(v)
    if v is None:
        return "—"
    return ("−" if v < 0 else "") + _spaced(abs(v), 2) + " ₽"


def _pct1(v) -> str:
    v = _num(v)
    return "—" if v is None else _spaced(v, 1) + " %"


def _pp(v) -> str:
    v = _num(v)
    return "—" if v is None else ("+" if v > 0 else "") + _spaced(v, 1) + " п.п."


def _signed_pct(v) -> str:
    v = _num(v)
    return "—" if v is None else ("+" if v > 0 else "") + _spaced(v, 1) + " %"


def _int(v) -> str:
    v = _num(v)
    return "—" if v is None else _spaced(round(v))


def _days(v) -> str:
    v = _num(v)
    if v is None:
        return "—"
    if v > 365:
        return "> 365"
    return _spaced(v, 1 if v < 10 else 0)


def _date(v) -> str:
    if _isna(v):
        return "—"
    try:
        return pd.Timestamp(v).strftime("%d.%m.%Y")
    except Exception:
        return "—"


def _plural(n, one: str, few: str, many: str) -> str:
    n = abs(int(n or 0)) % 100
    if 11 <= n <= 14:
        return many
    if n % 10 == 1:
        return one
    if 2 <= n % 10 <= 4:
        return few
    return many


def _period_label(start_date: str, end_date: str) -> str:
    s = pd.to_datetime(start_date).strftime("%d.%m.%Y")
    e = pd.to_datetime(end_date).strftime("%d.%m.%Y")
    return s if s == e else f"{s} – {e}"


def _prev_period_dates(start_date: str, end_date: str) -> tuple[str, str]:
    start = pd.to_datetime(start_date).date()
    end = pd.to_datetime(end_date).date()
    length = (end - start).days + 1
    prev_end = start - timedelta(days=1)
    return (prev_end - timedelta(days=length - 1)).isoformat(), prev_end.isoformat()


def _div(a, b, mult: float = 1.0):
    a, b = _num(a), _num(b)
    if a is None or not b:
        return None
    return a / b * mult


def _change_pct(cur, prev):
    cur, prev = _num(cur), _num(prev)
    if cur is None or not prev:
        return None
    return (cur - prev) / abs(prev) * 100


# ================================================================ шкала ДРР и оценки
def _drr_rating(drr) -> str | None:
    drr = _num(drr)
    if drr is None:
        return None
    for upper, label in DRR_RATING_BANDS:
        if drr <= upper:
            return label
    return DRR_RATING_WORST_LABEL


def _drr_group(drr) -> str:
    label = _drr_rating(drr)
    if label is None:
        return "unknown"
    if label == DRR_RATING_WORST_LABEL:
        return "bad"
    labels = [lbl for _, lbl in DRR_RATING_BANDS]
    return "good" if labels.index(label) < (len(labels) + 1) // 2 else "warn"


def _drr_bands_with_ranges() -> list[tuple[str, str]]:
    rows, prev = [], 0.0
    for upper, label in DRR_RATING_BANDS:
        rows.append((label, f"до {_spaced(upper)} %" if prev == 0 else f"{_spaced(prev)}–{_spaced(upper)} %"))
        prev = upper
    rows.append((DRR_RATING_WORST_LABEL, f"выше {_spaced(prev)} %"))
    return rows


def _classify_campaign(spend, orders, drr) -> str:
    spend, orders = _num(spend, 0.0), _num(orders, 0.0)
    if spend < CAMPAIGN_MIN_SPEND_TO_JUDGE:
        return QUALITY_LOW
    if orders == 0:
        return QUALITY_BAD
    if orders < CAMPAIGN_MIN_ORDERS_TO_JUDGE:
        return QUALITY_LOW
    if _num(drr) is None or drr > DRR_HIGH_THRESHOLD:
        return QUALITY_BAD
    return QUALITY_GOOD


def _quality_reason(spend, orders, revenue, drr) -> str:
    if not _num(orders):
        return f"Расход {_money(spend)}, заказов от рекламы нет."
    if _num(drr) is None:
        return f"{_int(orders)} заказ(ов), сумма заказов не определена — ДРР не рассчитан."
    return (
        f"ДРР {_pct1(drr)} выше порога {_pct1(DRR_HIGH_THRESHOLD)}: "
        f"расход {_money(spend)} при сумме заказов {_money(revenue)}."
    )


# ================================================================ доступ к данным
_METRICS = ["views", "clicks", "spend_rub", "atbs", "orders", "shks", "revenue_rub", "canceled"]
_METRICS_SQL = ",\n".join(f"SUM({m}) AS {m}" for m in _METRICS)


def _query(sql: str, params: dict | None = None, columns: list[str] | None = None,
           safe: bool = False) -> pd.DataFrame:
    from conns import get_duckdb_conn_with_opt

    try:
        with get_duckdb_conn_with_opt() as con:
            df = (con.execute(sql, params) if params else con.execute(sql)).df()
    except Exception:
        if not safe:
            raise
        logger.warning("Запрос к ads.* не выполнен", exc_info=True)
        return pd.DataFrame(columns=columns or [])

    if df is None:
        return pd.DataFrame(columns=columns or [])
    return df


def _scalar(sql: str, params: dict | None = None):
    df = _query(sql, params, safe=True)
    if df.empty:
        return None
    value = df.iloc[0, 0]
    return None if _isna(value) else value


def _fetch_campaigns_meta() -> pd.DataFrame:
    columns = ["advert_id", "name", "type_name", "status", "status_name", "payment_type",
               "bid_type", "create_time", "start_time", "end_time"]
    return _query(
        """
        SELECT advert_id, name, type_name, status, status_name, payment_type,
               bid_type, create_time, start_time, end_time
        FROM ads.unpacked_ad_campaigns
        """,
        columns=columns,
    )


def _fetch_products() -> pd.DataFrame:
    return _query(
        """
        SELECT
            card_id AS nm_id,
            MAX(title) AS product_title,
            MAX(NULLIF(TRIM(brand), '')) AS brand,
            COALESCE(NULLIF(TRIM(MAX(subject_name)), ''), 'Не указана') AS category
        FROM inventories.wb_product
        WHERE card_id IS NOT NULL
        GROUP BY card_id
        """,
        columns=["nm_id", "product_title", "brand", "category"],
        safe=True,
    )


def _fetch_stats(start_date: str, end_date: str) -> pd.DataFrame:
    return _query(
        """
        SELECT advert_id, date, views, clicks, spend_rub, atbs, orders, shks, revenue_rub, canceled
        FROM ads.unpacked_ad_campaigns_stats
        WHERE date BETWEEN $start_date AND $end_date
        """,
        {"start_date": start_date, "end_date": end_date},
        columns=["advert_id", "date", *_METRICS],
    )


def _fetch_campaign_products(start_date: str, end_date: str) -> pd.DataFrame:
    return _query(
        f"""
        SELECT
            advert_id,
            nm_id,
            ANY_VALUE(NULLIF(TRIM(title), '')) AS api_title,
            {_METRICS_SQL}
        FROM ads.unpacked_ad_campaigns_stats_by_nm
        WHERE date BETWEEN $start_date AND $end_date
        GROUP BY advert_id, nm_id
        """,
        {"start_date": start_date, "end_date": end_date},
        columns=["advert_id", "nm_id", "api_title", *_METRICS],
        safe=True,
    )


def _fetch_campaign_products_daily(start_date: str, end_date: str) -> pd.DataFrame:
    return _query(
        """
        SELECT advert_id, nm_id, date, SUM(spend_rub) AS spend_rub
        FROM ads.unpacked_ad_campaigns_stats_by_nm
        WHERE date BETWEEN $start_date AND $end_date
        GROUP BY advert_id, nm_id, date
        """,
        {"start_date": start_date, "end_date": end_date},
        columns=["advert_id", "nm_id", "date", "spend_rub"],
        safe=True,
    )


_DIRECT_CTE = """
    WITH direct_nm AS (
        SELECT advert_id, nm_id, 1 AS is_direct
        FROM ads.unpacked_ad_campaigns_stats_by_nm
        WHERE date BETWEEN $start_date AND $end_date
        GROUP BY advert_id, nm_id
        HAVING SUM(views) > 0 OR SUM(spend_rub) > 0
    )
"""

_DIRECT_SQL = """
    SUM(s.orders) FILTER (WHERE COALESCE(is_direct, 0) = 1) AS orders_direct,
    SUM(s.revenue_rub) FILTER (WHERE COALESCE(is_direct, 0) = 1) AS revenue_direct
"""


def _fetch_platforms(start_date: str, end_date: str) -> pd.DataFrame:
    metrics = ",\n".join(f"SUM(s.{m}) AS {m}" for m in _METRICS)
    return _query(
        f"""
        {_DIRECT_CTE}
        SELECT s.app_type_name AS platform, {metrics}, {_DIRECT_SQL}
        FROM ads.unpacked_ad_campaigns_stats_by_nm s
        LEFT JOIN direct_nm USING (advert_id, nm_id)
        WHERE s.date BETWEEN $start_date AND $end_date
        GROUP BY s.app_type_name
        """,
        {"start_date": start_date, "end_date": end_date},
        columns=["platform", *_METRICS, "orders_direct", "revenue_direct"],
        safe=True,
    )


def _fetch_daily_direct(start_date: str, end_date: str) -> pd.DataFrame:
    return _query(
        f"""
        {_DIRECT_CTE}
        SELECT s.date, {_DIRECT_SQL}
        FROM ads.unpacked_ad_campaigns_stats_by_nm s
        LEFT JOIN direct_nm USING (advert_id, nm_id)
        WHERE s.date BETWEEN $start_date AND $end_date
        GROUP BY s.date
        """,
        {"start_date": start_date, "end_date": end_date},
        columns=["date", "orders_direct", "revenue_direct"],
        safe=True,
    )


def _fetch_composition() -> pd.DataFrame:
    return _query(
        """
        SELECT advert_id, nm_id, subject_name, bid_search_kopecks, bid_recommendations_kopecks
        FROM ads.unpacked_ad_campaigns_nm_settings
        """,
        columns=["advert_id", "nm_id", "subject_name", "bid_search_kopecks", "bid_recommendations_kopecks"],
        safe=True,
    )


def _fetch_positions(start_date: str, end_date: str) -> pd.DataFrame:
    return _query(
        """
        SELECT advert_id, nm_id, AVG(avg_position) AS avg_position
        FROM ads.ad_campaigns_positions
        WHERE date BETWEEN $start_date AND $end_date AND avg_position > 0
        GROUP BY advert_id, nm_id
        """,
        {"start_date": start_date, "end_date": end_date},
        columns=["advert_id", "nm_id", "avg_position"],
        safe=True,
    )


def _fetch_budgets() -> pd.DataFrame:
    return _query(
        "SELECT advert_id, budget_rub, loaded_at AS budget_as_of FROM ads.unpacked_ad_campaigns_budget",
        columns=["advert_id", "budget_rub", "budget_as_of"],
        safe=True,
    )


def _fetch_expenses(start_date: str, end_date: str) -> pd.DataFrame:
    return _query(
        """
        SELECT date, upd_num, upd_time, advert_id, camp_name, advert_type_name,
               payment_source, amount_rub
        FROM ads.ad_campaigns_expenses
        WHERE date BETWEEN $start_date AND $end_date
        ORDER BY upd_time
        """,
        {"start_date": start_date, "end_date": end_date},
        columns=["date", "upd_num", "upd_time", "advert_id", "camp_name", "advert_type_name",
                 "payment_source", "amount_rub"],
        safe=True,
    )


def _fetch_payments(start_date: str, end_date: str) -> pd.DataFrame:
    return _query(
        """
        SELECT date, payment_time, payment_id, amount_rub, payment_type_name, status_id, card_status
        FROM ads.ad_campaigns_payments
        WHERE date BETWEEN $start_date AND $end_date
        ORDER BY payment_time
        """,
        {"start_date": start_date, "end_date": end_date},
        columns=["date", "payment_time", "payment_id", "amount_rub", "payment_type_name",
                 "status_id", "card_status"],
        safe=True,
    )


def _fetch_balance() -> dict | None:
    df = _query(
        "SELECT balance, net, bonus, currency, loaded_at FROM ads.ad_campaigns_balance LIMIT 1",
        safe=True,
    )
    if df.empty:
        return None
    row = df.iloc[0]
    return {
        "balance": _num(row.get("balance")),
        "net": _num(row.get("net")),
        "bonus": _num(row.get("bonus")),
        "as_of": row.get("loaded_at"),
    }


def _fetch_freshness() -> dict:
    return {
        "stats_max_date": _scalar("SELECT MAX(date) FROM ads.unpacked_ad_campaigns_stats"),
        "stats_loaded_at": _scalar("SELECT MAX(loaded_at) FROM ads.unpacked_ad_campaigns_stats"),
        "expenses_max_date": _scalar("SELECT MAX(date) FROM ads.ad_campaigns_expenses"),
    }


def _fetch_sales(start_date: str, end_date: str) -> tuple[pd.DataFrame, object]:
    as_of = _scalar(
        "SELECT MAX(date_from)::DATE FROM sales.sales_long WHERE field = 'retail_price'"
    )
    df = _query(
        """
        SELECT
            nm_id,
            (COALESCE(SUM(val) FILTER (WHERE oper = 'dt'), 0)
             - COALESCE(SUM(val) FILTER (WHERE oper = 'cr'), 0)) / 100.0 AS sales_rub,
            COUNT(*) FILTER (WHERE oper = 'dt') - COUNT(*) FILTER (WHERE oper = 'cr') AS sales_qty
        FROM sales.sales_long
        WHERE field = 'retail_price'
          AND date_from::DATE BETWEEN $start_date AND $end_date
          AND nm_id IS NOT NULL
        GROUP BY nm_id
        """,
        {"start_date": start_date, "end_date": end_date},
        columns=["nm_id", "sales_rub", "sales_qty"],
        safe=True,
    )
    return df, as_of


def _fetch_stocks() -> tuple[pd.DataFrame, object]:
    df = _query(
        """
        WITH wb AS (
            SELECT nm_id, SUM(COALESCE(quantity, 0)) AS qty
            FROM stocks.unpacked_stocks
            WHERE date_from = (SELECT MAX(date_from) FROM stocks.unpacked_stocks)
              AND nm_id IS NOT NULL
            GROUP BY nm_id
        ),
        fbs AS (
            SELECT nm_id, SUM(COALESCE(quantity, 0)) AS qty
            FROM stocks.unpacked_fbs_stocks
            WHERE date_from = (SELECT MAX(date_from) FROM stocks.unpacked_fbs_stocks)
              AND nm_id IS NOT NULL
            GROUP BY nm_id
        )
        SELECT COALESCE(wb.nm_id, fbs.nm_id) AS nm_id,
               COALESCE(wb.qty, 0) + COALESCE(fbs.qty, 0) AS stock_qty
        FROM wb FULL OUTER JOIN fbs ON wb.nm_id = fbs.nm_id
        """,
        columns=["nm_id", "stock_qty"],
        safe=True,
    )
    as_of = _scalar(
        """
        SELECT GREATEST(
            COALESCE((SELECT MAX(date_from) FROM stocks.unpacked_stocks), DATE '1900-01-01'),
            COALESCE((SELECT MAX(date_from) FROM stocks.unpacked_fbs_stocks), DATE '1900-01-01')
        )
        """
    )
    if as_of is not None and pd.Timestamp(as_of).year < 1990:
        as_of = None
    return df, as_of


def _fetch_period_to_date(end_date: str) -> dict | None:
    df = _query(
        """
        WITH b AS (
            SELECT
                CAST($end_date AS DATE) AS e,
                DATE_TRUNC('week', CAST($end_date AS DATE))::DATE AS w,
                DATE_TRUNC('month', CAST($end_date AS DATE))::DATE AS m,
                DATE_TRUNC('quarter', CAST($end_date AS DATE))::DATE AS q,
                DATE_TRUNC('year', CAST($end_date AS DATE))::DATE AS y
        )
        SELECT
            b.e AS end_date,
            SUM(s.spend_rub) FILTER (WHERE s.date BETWEEN b.w AND b.e) AS week_spend,
            SUM(s.revenue_rub) FILTER (WHERE s.date BETWEEN b.w AND b.e) AS week_revenue,
            SUM(s.spend_rub) FILTER (WHERE s.date BETWEEN b.w - INTERVAL 7 DAY AND b.e - INTERVAL 7 DAY) AS week_prev,
            SUM(s.spend_rub) FILTER (WHERE s.date BETWEEN b.m AND b.e) AS month_spend,
            SUM(s.revenue_rub) FILTER (WHERE s.date BETWEEN b.m AND b.e) AS month_revenue,
            SUM(s.spend_rub) FILTER (WHERE s.date BETWEEN b.m - INTERVAL 1 MONTH AND b.e - INTERVAL 1 MONTH) AS month_prev,
            SUM(s.spend_rub) FILTER (WHERE s.date BETWEEN b.q AND b.e) AS quarter_spend,
            SUM(s.revenue_rub) FILTER (WHERE s.date BETWEEN b.q AND b.e) AS quarter_revenue,
            SUM(s.spend_rub) FILTER (WHERE s.date BETWEEN b.q - INTERVAL 3 MONTH AND b.e - INTERVAL 3 MONTH) AS quarter_prev,
            SUM(s.spend_rub) FILTER (WHERE s.date BETWEEN b.y AND b.e) AS year_spend,
            SUM(s.revenue_rub) FILTER (WHERE s.date BETWEEN b.y AND b.e) AS year_revenue,
            SUM(s.spend_rub) FILTER (WHERE s.date BETWEEN b.y - INTERVAL 1 YEAR AND b.e - INTERVAL 1 YEAR) AS year_prev
        FROM b
        LEFT JOIN ads.unpacked_ad_campaigns_stats s ON TRUE
        GROUP BY b.e
        """,
        {"end_date": end_date},
        safe=True,
    )
    if df.empty:
        return None

    row = df.iloc[0]
    labels = {
        "week": "С начала недели",
        "month": "С начала месяца",
        "quarter": "С начала квартала",
        "year": "С начала года",
    }
    result = {"as_of": row.get("end_date")}
    for key, label in labels.items():
        spend = _num(row.get(f"{key}_spend"), 0.0)
        revenue = _num(row.get(f"{key}_revenue"), 0.0)
        prev = _num(row.get(f"{key}_prev"))
        result[key] = {
            "label": label,
            "spend": spend,
            "revenue": revenue,
            "drr": _div(spend, revenue, 100),
            "prev_spend": prev,
            "change_pct": _change_pct(spend, prev),
        }
    return result


# ================================================================ расчёты
def _ratio(a, b, mult: float = 1.0) -> pd.Series:
    a = pd.to_numeric(a, errors="coerce").astype(float)
    b = pd.to_numeric(b, errors="coerce").astype(float)
    return a / b.where(b != 0) * mult


def _add_rates(df: pd.DataFrame) -> pd.DataFrame:
    if df is None:
        return df
    for m in _METRICS:
        if m not in df.columns:
            df[m] = 0
        df[m] = pd.to_numeric(df[m], errors="coerce").fillna(0)
    df["ctr"] = _ratio(df["clicks"], df["views"], 100)
    df["cpc"] = _ratio(df["spend_rub"], df["clicks"])
    df["cpm"] = _ratio(df["spend_rub"], df["views"], 1000)
    df["cart_rate"] = _ratio(df["atbs"], df["clicks"], 100)
    df["cr"] = _ratio(df["orders"], df["clicks"], 100)
    df["cpo"] = _ratio(df["spend_rub"], df["orders"])
    df["drr"] = _ratio(df["spend_rub"], df["revenue_rub"], 100)
    df["cancel_rate"] = _ratio(df["canceled"], df["orders"], 100)
    return df


def _sum_metrics(df: pd.DataFrame, by) -> pd.DataFrame:
    if df is None or df.empty:
        cols = ([by] if isinstance(by, str) else list(by)) + _METRICS
        return _add_rates(pd.DataFrame(columns=cols))
    g = df.groupby(by, dropna=False)[_METRICS].sum(min_count=1).fillna(0).reset_index()
    return _add_rates(g)


def _totals(df: pd.DataFrame) -> dict:
    base = {m: 0.0 for m in _METRICS}
    if df is not None and not df.empty:
        for m in _METRICS:
            base[m] = float(pd.to_numeric(df[m], errors="coerce").fillna(0).sum())
    s, v, c, o, r = base["spend_rub"], base["views"], base["clicks"], base["orders"], base["revenue_rub"]
    base.update({
        "ctr": _div(c, v, 100),
        "cpc": _div(s, c),
        "cpm": _div(s, v, 1000),
        "cart_rate": _div(base["atbs"], c, 100),
        "cr": _div(o, c, 100),
        "cpo": _div(s, o),
        "drr": _div(s, r, 100),
        "cancel_rate": _div(base["canceled"], o, 100),
        "avg_check": _div(r, base["shks"] or o),
    })
    return base


def _product_titles(df: pd.DataFrame, products: pd.DataFrame) -> pd.DataFrame:
    if products is not None and not products.empty:
        df = df.merge(products, on="nm_id", how="left")
    else:
        df["product_title"] = None
        df["brand"] = None
        df["category"] = None

    api_title = df["api_title"] if "api_title" in df.columns else pd.Series(None, index=df.index)
    title = df["product_title"].where(df["product_title"].fillna("").astype(str).str.strip() != "", api_title)
    fallback = df["nm_id"].apply(lambda x: f"Артикул {int(x)}" if not _isna(x) else "Без артикула")
    df["title"] = title.where(title.fillna("").astype(str).str.strip() != "", fallback)
    df["brand"] = df["brand"].fillna("Бренд не указан")
    df["category"] = df["category"].fillna("Не указана")
    return df


def _aggregate_campaigns(stats, meta, budgets, recent, charged) -> pd.DataFrame:
    g = _sum_metrics(stats, "advert_id")

    if stats is not None and not stats.empty:
        active = stats[(stats["spend_rub"] > 0) | (stats["views"] > 0)]
        span = active.groupby("advert_id")["date"].agg(first_date="min", last_date="max").reset_index()
        g = g.merge(span, on="advert_id", how="left")
    else:
        g["first_date"] = None
        g["last_date"] = None

    if meta is not None and not meta.empty:
        live_ids = meta.loc[meta["status"].isin([STATUS_ACTIVE, STATUS_PAUSED]), "advert_id"]
        missing = sorted(set(live_ids) - set(g["advert_id"]))
        if missing:
            g = pd.concat([g, _add_rates(pd.DataFrame({"advert_id": missing}))], ignore_index=True)
        g = g.merge(meta, on="advert_id", how="left")
    else:
        for col in ("name", "type_name", "status", "status_name", "payment_type", "bid_type"):
            g[col] = None

    g["name"] = g["name"].fillna("Кампания без названия")
    g["type_name"] = g["type_name"].fillna("—")
    g["status_name"] = g["status_name"].fillna("—")
    g["bid_type_name"] = g["bid_type"].map(BID_TYPE_NAMES).fillna("—")
    g["payment_name"] = g["payment_type"].map(PAYMENT_TYPE_NAMES).fillna("—")

    if budgets is not None and not budgets.empty:
        g = g.merge(budgets, on="advert_id", how="left")
    else:
        g["budget_rub"] = np.nan
        g["budget_as_of"] = None

    is_live = g["status"].isin([STATUS_ACTIVE, STATUS_PAUSED])
    g.loc[~is_live, "budget_rub"] = np.nan

    if recent is not None and not recent.empty:
        g = g.merge(recent, on="advert_id", how="left")
    else:
        g["recent_spend"] = 0.0
    g["recent_spend"] = pd.to_numeric(g["recent_spend"], errors="coerce").fillna(0.0)
    g["avg_daily_spend"] = g["recent_spend"] / RUNWAY_LOOKBACK_DAYS
    g["runway_days"] = _ratio(g["budget_rub"], g["avg_daily_spend"])
    g.loc[g["status"] != STATUS_ACTIVE, "runway_days"] = np.nan

    if charged is not None and not charged.empty:
        g = g.merge(charged, on="advert_id", how="left")
    else:
        g["charged_rub"] = np.nan

    g["quality"] = [_classify_campaign(s, o, d) for s, o, d in zip(g["spend_rub"], g["orders"], g["drr"])]
    g["drr_rating"] = g["drr"].apply(_drr_rating)
    g["reason"] = [
        _quality_reason(s, o, r, d) if q == QUALITY_BAD else ""
        for q, s, o, r, d in zip(g["quality"], g["spend_rub"], g["orders"], g["revenue_rub"], g["drr"])
    ]
    return g.sort_values(["spend_rub", "advert_id"], ascending=[False, True]).reset_index(drop=True)


def _aggregate_campaign_products(cp, products, stocks, positions, composition, campaigns) -> pd.DataFrame:
    cp = cp.copy() if cp is not None else pd.DataFrame(columns=["advert_id", "nm_id", "api_title", *_METRICS])

    if composition is not None and not composition.empty and campaigns is not None and not campaigns.empty:
        live = set(campaigns.loc[campaigns["status"].isin([STATUS_ACTIVE, STATUS_PAUSED]), "advert_id"])
        comp = composition[composition["advert_id"].isin(live)]
        cp = cp.merge(comp, on=["advert_id", "nm_id"], how="outer")
        cp["in_campaign"] = cp["bid_search_kopecks"].notna() | cp["bid_recommendations_kopecks"].notna()
    else:
        cp["bid_search_kopecks"] = np.nan
        cp["bid_recommendations_kopecks"] = np.nan
        cp["in_campaign"] = False

    cp = _add_rates(cp)
    cp = _product_titles(cp, products)

    if positions is not None and not positions.empty:
        cp = cp.merge(positions, on=["advert_id", "nm_id"], how="left")
    else:
        cp["avg_position"] = np.nan

    if stocks is not None and not stocks.empty:
        cp = cp.merge(stocks, on="nm_id", how="left")
    else:
        cp["stock_qty"] = np.nan

    cp["bid_search_rub"] = pd.to_numeric(cp["bid_search_kopecks"], errors="coerce") / 100
    cp["bid_recommendations_rub"] = pd.to_numeric(cp["bid_recommendations_kopecks"], errors="coerce") / 100
    cp["drr_rating"] = cp["drr"].apply(_drr_rating)
    cp["direct"] = (cp["views"] > 0) | (cp["spend_rub"] > 0) | cp["in_campaign"].fillna(False).astype(bool)
    return cp.sort_values(["advert_id", "spend_rub"], ascending=[True, False]).reset_index(drop=True)


def _apply_direct(campaigns: pd.DataFrame, cp: pd.DataFrame) -> pd.DataFrame:
    """Делит заказы кампании на прямые (рекламируемые товары) и связанные (другие товары продавца)."""
    g = campaigns.copy()
    cols = ["orders", "revenue_rub"]
    if cp is not None and not cp.empty:
        direct = cp[cp["direct"]].groupby("advert_id")[cols].sum()
        direct.columns = ["orders_direct", "revenue_direct"]
        assoc = cp[~cp["direct"]].groupby("advert_id").agg(
            orders_assoc=("orders", "sum"), revenue_assoc=("revenue_rub", "sum"), assoc_n=("nm_id", "nunique"),
        )
        g = g.merge(direct.reset_index(), on="advert_id", how="left").merge(assoc.reset_index(), on="advert_id", how="left")
    else:
        g["orders_direct"], g["revenue_direct"] = g["orders"], g["revenue_rub"]
        g["orders_assoc"] = g["revenue_assoc"] = g["assoc_n"] = 0

    for col in ("orders_direct", "revenue_direct", "orders_assoc", "revenue_assoc", "assoc_n"):
        g[col] = pd.to_numeric(g[col], errors="coerce").fillna(0)

    g["drr_direct"] = _ratio(g["spend_rub"], g["revenue_direct"], 100)
    g["assoc_share"] = _ratio(g["revenue_assoc"], g["revenue_direct"] + g["revenue_assoc"], 100)
    g["quality"] = [
        _classify_campaign(s, o, d) for s, o, d in zip(g["spend_rub"], g["orders_direct"], g["drr_direct"])
    ]
    g["reason"] = [
        _quality_reason(s, o, r, d) if q == QUALITY_BAD else ""
        for q, s, o, r, d in zip(g["quality"], g["spend_rub"], g["orders_direct"], g["revenue_direct"], g["drr_direct"])
    ]
    return g


def _aggregate_products(cp, sales, sales_window_cp) -> pd.DataFrame:
    if cp is None or cp.empty:
        return _add_rates(pd.DataFrame(columns=["nm_id", "title", "brand", "category", "stock_qty"]))

    active = cp[(cp["spend_rub"] > 0) | (cp["views"] > 0)]
    g = _sum_metrics(active, "nm_id")
    attrs = cp.groupby("nm_id").agg(
        title=("title", "first"), brand=("brand", "first"),
        category=("category", "first"), stock_qty=("stock_qty", "first"),
    ).reset_index()
    g = g.merge(attrs, on="nm_id", how="left")

    counts = active.groupby("nm_id")["advert_id"].nunique().rename("campaigns_n").reset_index()
    g = g.merge(counts, on="nm_id", how="left")

    if sales is not None and not sales.empty:
        g = g.merge(sales, on="nm_id", how="left")
    else:
        g["sales_rub"] = np.nan
        g["sales_qty"] = np.nan

    if sales_window_cp is not None and not sales_window_cp.empty:
        window_spend = sales_window_cp.groupby("nm_id")["spend_rub"].sum().rename("tacos_spend").reset_index()
        g = g.merge(window_spend, on="nm_id", how="left")
    else:
        g["tacos_spend"] = np.nan

    g["tacos"] = _ratio(g["tacos_spend"], g["sales_rub"], 100)
    g["drr_rating"] = g["drr"].apply(_drr_rating)
    return g.sort_values("spend_rub", ascending=False).reset_index(drop=True)


def _low_stock(cp: pd.DataFrame, campaigns: pd.DataFrame) -> pd.DataFrame:
    cols = ["nm_id", "title", "brand", "stock_qty", "spend_rub", "orders", "campaigns"]
    if cp is None or cp.empty or campaigns.empty:
        return pd.DataFrame(columns=cols)
    live = campaigns[campaigns["status"].isin([STATUS_ACTIVE, STATUS_PAUSED])]
    names = live.set_index("advert_id")["name"].to_dict()
    stock = pd.to_numeric(cp["stock_qty"], errors="coerce")
    rows = cp[cp["advert_id"].isin(names) & cp["direct"] & stock.notna() & (stock < LOW_STOCK_QTY_THRESHOLD)]
    if rows.empty:
        return pd.DataFrame(columns=cols)
    g = rows.groupby("nm_id").agg(
        title=("title", "first"), brand=("brand", "first"), stock_qty=("stock_qty", "first"),
        spend_rub=("spend_rub", "sum"), orders=("orders", "sum"),
        campaigns=("advert_id", lambda ids: ", ".join(names[i] for i in ids)),
    ).reset_index()
    return g.sort_values("spend_rub", ascending=False).reset_index(drop=True)[cols]


def _aggregate_time(stats: pd.DataFrame, freq: str) -> pd.DataFrame:
    if stats is None or stats.empty:
        return _add_rates(pd.DataFrame(columns=["period_start", "label"]))

    df = stats.copy()
    d = pd.to_datetime(df["date"])
    if freq == "day":
        df["period_start"] = d.dt.normalize()
    elif freq == "week":
        df["period_start"] = (d - pd.to_timedelta(d.dt.weekday, unit="D")).dt.normalize()
    else:
        df["period_start"] = d.dt.to_period("M").dt.to_timestamp()

    g = _sum_metrics(df, "period_start").sort_values("period_start").reset_index(drop=True)
    if freq == "day":
        g["label"] = g["period_start"].dt.strftime("%d.%m")
    elif freq == "week":
        g["label"] = g["period_start"].apply(lambda x: f"{x:%d.%m}–{x + pd.Timedelta(days=6):%d.%m}")
    else:
        g["label"] = g["period_start"].dt.strftime("%m.%Y")
    return g


def _add_direct_to_time(df: pd.DataFrame, daily_direct: pd.DataFrame, freq: str) -> pd.DataFrame:
    df = df.copy()
    if df.empty or daily_direct is None or daily_direct.empty:
        df["revenue_direct"] = np.nan
        df["drr_direct"] = np.nan
        return df
    dd = daily_direct.copy()
    d = pd.to_datetime(dd["date"])
    if freq == "day":
        dd["period_start"] = d.dt.normalize()
    elif freq == "week":
        dd["period_start"] = (d - pd.to_timedelta(d.dt.weekday, unit="D")).dt.normalize()
    else:
        dd["period_start"] = d.dt.to_period("M").dt.to_timestamp()
    g = dd.groupby("period_start")[["orders_direct", "revenue_direct"]].sum().reset_index()
    df = df.merge(g, on="period_start", how="left")
    df["drr_direct"] = _ratio(df["spend_rub"], df["revenue_direct"], 100)
    return df


def _trend_freq(period_days: int) -> str:
    if period_days <= 31:
        return "day"
    if period_days <= 190:
        return "week"
    return "month"


def _find_spike(df: pd.DataFrame) -> dict | None:
    if df is None or len(df) < 3:
        return None
    best = None
    for idx, row in df.iterrows():
        others = df.drop(idx)["spend_rub"].mean()
        if others and row["spend_rub"] >= others * SPIKE_RATIO:
            ratio = row["spend_rub"] / others
            if best is None or ratio > best["ratio"]:
                best = {"label": row["label"], "ratio": ratio}
    return best


def _group_share(campaigns: pd.DataFrame, by: str) -> pd.DataFrame:
    if campaigns is None or campaigns.empty:
        return _add_rates(pd.DataFrame(columns=[by, "campaigns_n", "share"]))
    active = campaigns[campaigns["spend_rub"] > 0]
    g = _sum_metrics(active, by)
    counts = active.groupby(by)["advert_id"].nunique().rename("campaigns_n").reset_index()
    g = g.merge(counts, on=by, how="left")
    if "revenue_direct" in active.columns:
        direct = active.groupby(by)[["orders_direct", "revenue_direct"]].sum().reset_index()
        g = g.merge(direct, on=by, how="left")
    else:
        g["orders_direct"], g["revenue_direct"] = g["orders"], g["revenue_rub"]
    g["drr_direct"] = _ratio(g["spend_rub"], g["revenue_direct"], 100)
    g["cpo_direct"] = _ratio(g["spend_rub"], g["orders_direct"])
    total = g["spend_rub"].sum()
    g["share"] = _ratio(g["spend_rub"], pd.Series(total, index=g.index), 100)
    return g.sort_values("spend_rub", ascending=False).reset_index(drop=True)


def _reconciliation_by_period(stats: pd.DataFrame, expenses: pd.DataFrame, freq: str) -> pd.DataFrame:
    frames = []
    for df, value, name in ((stats, "spend_rub", "stats_spend"), (expenses, "amount_rub", "charged")):
        if df is None or df.empty:
            continue
        d = pd.to_datetime(df["date"])
        if freq == "week":
            key = (d - pd.to_timedelta(d.dt.weekday, unit="D")).dt.normalize()
        else:
            key = d.dt.to_period("M").dt.to_timestamp()
        frames.append(df.assign(period_start=key).groupby("period_start")[value].sum().rename(name))
    if not frames:
        return pd.DataFrame(columns=["period_start", "label", "stats_spend", "charged", "diff", "diff_pct"])
    g = pd.concat(frames, axis=1).fillna(0).reset_index().sort_values("period_start")
    for col in ("stats_spend", "charged"):
        if col not in g:
            g[col] = 0.0
    g["diff"] = g["stats_spend"] - g["charged"]
    g["diff_pct"] = _ratio(g["diff"], g["charged"], 100)
    if freq == "week":
        g["label"] = g["period_start"].apply(lambda x: f"{x:%d.%m}–{x + pd.Timedelta(days=6):%d.%m.%Y}")
    else:
        g["label"] = g["period_start"].dt.strftime("%m.%Y")
    return g.reset_index(drop=True)


def _reconciliation(campaigns: pd.DataFrame, expenses: pd.DataFrame) -> dict:
    stats_spend = float(campaigns["spend_rub"].sum()) if campaigns is not None and not campaigns.empty else 0.0
    charged = float(expenses["amount_rub"].sum()) if expenses is not None and not expenses.empty else 0.0
    available = expenses is not None and not expenses.empty

    rows = pd.DataFrame()
    if campaigns is not None and not campaigns.empty:
        rows = campaigns[["advert_id", "name", "status_name", "spend_rub", "charged_rub"]].copy()
        rows["charged_rub"] = pd.to_numeric(rows["charged_rub"], errors="coerce").fillna(0.0)
        if available:
            extra_ids = set(expenses["advert_id"].dropna()) - set(rows["advert_id"])
            if extra_ids:
                extra = (
                    expenses[expenses["advert_id"].isin(extra_ids)]
                    .groupby("advert_id")
                    .agg(name=("camp_name", "first"), charged_rub=("amount_rub", "sum"))
                    .reset_index()
                )
                extra["spend_rub"] = 0.0
                extra["status_name"] = "—"
                rows = pd.concat([rows, extra], ignore_index=True)
        rows["diff_rub"] = rows["spend_rub"] - rows["charged_rub"]
        rows = rows[(rows["spend_rub"] != 0) | (rows["charged_rub"] != 0)]
        rows = rows.reindex(rows["diff_rub"].abs().sort_values(ascending=False).index).reset_index(drop=True)

    by_source = pd.DataFrame(columns=["payment_source", "amount_rub"])
    if available:
        by_source = (
            expenses.groupby(expenses["payment_source"].fillna("—"))["amount_rub"].sum()
            .rename_axis("payment_source").reset_index()
            .sort_values("amount_rub", ascending=False)
        )

    diff = stats_spend - charged
    return {
        "available": available,
        "stats_spend": stats_spend,
        "charged": charged,
        "diff": diff,
        "diff_pct": _div(diff, charged, 100),
        "rows": rows,
        "by_source": by_source,
    }


def _budget_summary(campaigns: pd.DataFrame, balance: dict | None, totals: dict, period_days: int) -> dict:
    live = campaigns[campaigns["status"].isin([STATUS_ACTIVE, STATUS_PAUSED])] if not campaigns.empty else campaigns
    budgets_total = float(pd.to_numeric(live.get("budget_rub"), errors="coerce").fillna(0).sum()) if not live.empty else 0.0
    recent_daily = float(live["avg_daily_spend"].sum()) if not live.empty else 0.0
    net = balance.get("net") if balance else None
    available = (net or 0.0) + budgets_total
    return {
        "live_n": int(len(live)),
        "active_n": int((live["status"] == STATUS_ACTIVE).sum()) if not live.empty else 0,
        "paused_n": int((live["status"] == STATUS_PAUSED).sum()) if not live.empty else 0,
        "budgets_total": budgets_total,
        "budgets_known": bool(not live.empty and live["budget_rub"].notna().any()),
        "avg_daily_spend": recent_daily,
        "period_avg_daily": _div(totals["spend_rub"], period_days),
        "net": net,
        "balance": balance.get("balance") if balance else None,
        "bonus": balance.get("bonus") if balance else None,
        "balance_as_of": balance.get("as_of") if balance else None,
        "runway_days": _div(available, recent_daily) if recent_daily else None,
    }


# ================================================================ сборка данных отчёта
def _safe(func, *args, default=None, **kwargs):
    try:
        return func(*args, **kwargs)
    except Exception:
        logger.exception("Не удалось получить данные: %s", getattr(func, "__name__", func))
        return default


def _fetch_report_bundle(start_date: str, end_date: str) -> dict:
    start = pd.to_datetime(start_date).date()
    end = pd.to_datetime(end_date).date()
    period_days = (end - start).days + 1
    prev_start, prev_end = _prev_period_dates(start_date, end_date)

    meta = _fetch_campaigns_meta()
    stats = _fetch_stats(start_date, end_date)
    products = _fetch_products()
    freshness = _safe(_fetch_freshness, default={}) or {}

    as_of = freshness.get("stats_max_date")
    recent_end = min(end, pd.Timestamp(as_of).date()) if as_of is not None else end
    recent_start = recent_end - timedelta(days=RUNWAY_LOOKBACK_DAYS - 1)
    recent_stats = _safe(_fetch_stats, recent_start.isoformat(), recent_end.isoformat(),
                         default=pd.DataFrame(columns=["advert_id", "spend_rub"]))
    recent = (
        recent_stats.groupby("advert_id")["spend_rub"].sum().rename("recent_spend").reset_index()
        if not recent_stats.empty else pd.DataFrame(columns=["advert_id", "recent_spend"])
    )

    expenses = _fetch_expenses(start_date, end_date)
    charged = (
        expenses.groupby("advert_id")["amount_rub"].sum().rename("charged_rub").reset_index()
        if not expenses.empty else pd.DataFrame(columns=["advert_id", "charged_rub"])
    )

    campaigns = _aggregate_campaigns(stats, meta, _fetch_budgets(), recent, charged)

    cp_raw = _fetch_campaign_products(start_date, end_date)
    stocks, stocks_as_of = _safe(_fetch_stocks, default=(pd.DataFrame(columns=["nm_id", "stock_qty"]), None))
    campaign_products = _aggregate_campaign_products(
        cp_raw, products, stocks, _fetch_positions(start_date, end_date), _fetch_composition(), campaigns,
    )

    campaigns = _apply_direct(campaigns, campaign_products)

    sales, sales_as_of = _safe(_fetch_sales, start_date, end_date,
                               default=(pd.DataFrame(columns=["nm_id", "sales_rub", "sales_qty"]), None))
    tacos = {"available": False}
    sales_window_cp = None
    if sales_as_of is not None and not sales.empty:
        tacos_end = min(end, pd.Timestamp(sales_as_of).date())
        if tacos_end >= start:
            if tacos_end == end:
                window_stats, sales_window_cp = stats, cp_raw
            else:
                window_stats = stats[pd.to_datetime(stats["date"]).dt.date <= tacos_end]
                sales_window_cp = _fetch_campaign_products(start_date, tacos_end.isoformat())
                sales = _fetch_sales(start_date, tacos_end.isoformat())[0]
            window_spend = float(window_stats["spend_rub"].sum()) if not window_stats.empty else 0.0
            total_sales = float(sales["sales_rub"].sum())
            tacos = {
                "available": total_sales > 0,
                "end": tacos_end,
                "partial": tacos_end < end,
                "spend": window_spend,
                "sales": total_sales,
                "value": _div(window_spend, total_sales, 100),
            }

    products_df = _aggregate_products(campaign_products, sales, sales_window_cp)
    low_stock = _low_stock(campaign_products, campaigns)

    prev_stats = _safe(_fetch_stats, prev_start, prev_end, default=pd.DataFrame(columns=_METRICS))
    totals = _totals(stats)
    totals["orders_direct"] = float(campaigns["orders_direct"].sum()) if not campaigns.empty else 0.0
    totals["revenue_direct"] = float(campaigns["revenue_direct"].sum()) if not campaigns.empty else 0.0
    totals["revenue_assoc"] = float(campaigns["revenue_assoc"].sum()) if not campaigns.empty else 0.0
    totals["drr_direct"] = _div(totals["spend_rub"], totals["revenue_direct"], 100)
    totals["assoc_share"] = _div(totals["revenue_assoc"], totals["revenue_direct"] + totals["revenue_assoc"], 100)
    prev_totals = _totals(prev_stats) if prev_stats is not None and not prev_stats.empty else None
    if prev_totals is not None:
        prev_direct = _safe(_fetch_daily_direct, prev_start, prev_end, default=pd.DataFrame())
        if prev_direct is not None and not prev_direct.empty:
            prev_totals["revenue_direct"] = float(pd.to_numeric(prev_direct["revenue_direct"], errors="coerce").sum())
            prev_totals["drr_direct"] = _div(prev_totals["spend_rub"], prev_totals["revenue_direct"], 100)

    freq = _trend_freq(period_days)
    daily_direct = _safe(_fetch_daily_direct, start_date, end_date, default=pd.DataFrame())
    trend = _add_direct_to_time(_aggregate_time(stats, freq), daily_direct, freq)

    balance = _safe(_fetch_balance)
    budget = _budget_summary(campaigns, balance, totals, period_days)

    brands = _sum_metrics(
        products_df[["brand", *_METRICS]] if not products_df.empty else products_df, "brand"
    ).sort_values("spend_rub", ascending=False).reset_index(drop=True)

    platforms = _fetch_platforms(start_date, end_date)
    platforms = _add_rates(platforms) if not platforms.empty else platforms
    if not platforms.empty:
        for col in ("orders_direct", "revenue_direct"):
            platforms[col] = pd.to_numeric(platforms[col], errors="coerce").fillna(0)
        platforms["drr_direct"] = _ratio(platforms["spend_rub"], platforms["revenue_direct"], 100)
        platforms["cr_direct"] = _ratio(platforms["orders_direct"], platforms["clicks"], 100)
    if not platforms.empty:
        total = platforms["spend_rub"].sum()
        platforms["share"] = platforms["spend_rub"] / total * 100 if total else np.nan
        platforms = platforms.sort_values("spend_rub", ascending=False).reset_index(drop=True)

    return {
        "start_date": start_date,
        "end_date": end_date,
        "period_days": period_days,
        "prev_start": prev_start,
        "prev_end": prev_end,
        "generated_at": datetime.now(),
        "freshness": freshness,
        "stats": stats,
        "campaigns": campaigns,
        "campaign_products": campaign_products,
        "products": products_df,
        "trend": trend,
        "trend_freq": freq,
        "trend_spike": _find_spike(trend),
        "daily": _add_direct_to_time(_aggregate_time(stats, "day"), daily_direct, "day"),
        "weekly": _add_direct_to_time(_aggregate_time(stats, "week"), daily_direct, "week"),
        "monthly": _add_direct_to_time(_aggregate_time(stats, "month"), daily_direct, "month"),
        "by_type": _group_share(campaigns, "type_name"),
        "by_bid": _group_share(campaigns, "bid_type_name"),
        "by_payment": _group_share(campaigns, "payment_name"),
        "brands": brands,
        "platforms": platforms,
        "totals": totals,
        "prev_totals": prev_totals,
        "tacos": tacos,
        "balance": balance,
        "budget": budget,
        "expenses": expenses,
        "payments": _fetch_payments(start_date, end_date),
        "reconciliation": {
            **_reconciliation(campaigns, expenses),
            "by_period": _reconciliation_by_period(stats, expenses, "week" if period_days <= 120 else "month"),
            "by_period_freq": "week" if period_days <= 120 else "month",
        },
        "period_to_date": _safe(_fetch_period_to_date, end_date),
        "stocks_as_of": stocks_as_of,
        "low_stock": low_stock,
        "stocks_available": stocks is not None and not stocks.empty,
        "sales_as_of": sales_as_of,
    }


# ================================================================ выводы и рекомендации
def _recommendations(bundle: dict) -> list[tuple[str, str, str]]:
    """Список (уровень good|warn|bad|info, заголовок, текст)."""
    t = bundle["totals"]
    prev = bundle["prev_totals"]
    campaigns = bundle["campaigns"]
    products = bundle["products"]
    budget = bundle["budget"]
    recon = bundle["reconciliation"]
    spend = t["spend_rub"]
    drr = t["drr"]
    recs: list[tuple[str, str, str]] = []

    if spend <= 0:
        return [("info", "Расходов на рекламу за период нет",
                 "За выбранный период по статистике WB нет ни показов, ни расходов.")]

    active = campaigns[campaigns["spend_rub"] > 0] if not campaigns.empty else campaigns

    good = active[active["quality"] == QUALITY_GOOD] if not active.empty else active
    if not good.empty:
        best = good.loc[good["drr_direct"].idxmin()] if good["drr_direct"].notna().any() else good.iloc[0]
        recs.append((
            "good",
            f"Лучший результат — «{best['name']}»",
            f"ДРР по рекламируемым товарам {_pct1(best['drr_direct'])}: расход {_money(best['spend_rub'])}, "
            f"{_int(best['orders_direct'])} заказ(ов) на {_money(best['revenue_direct'])}. "
            f"Кандидат на увеличение бюджета при сохранении эффективности.",
        ))

    drr_direct = t.get("drr_direct") if t.get("drr_direct") is not None else drr
    if t["orders"] == 0:
        recs.append((
            "bad", "Расход без заказов",
            f"Потрачено {_money(spend)}, заказов от рекламы по данным WB нет. "
            f"Требуется ручная проверка кампаний и карточек.",
        ))
    elif drr_direct is not None:
        group = _drr_group(drr_direct)
        rating = _drr_rating(drr_direct)
        title = f"ДРР по рекламируемым товарам {_pct1(drr_direct)} — «{rating}»"
        if group == "good":
            recs.append(("good", title,
                         "Реклама окупается с запасом. Масштабировать стоит кампании с минимальным ДРР."))
        elif group == "warn":
            recs.append((
                "warn", title,
                f"Реклама окупается, но запас сокращается (маржа до рекламы ~{_pct1(PRE_AD_MARGIN_REFERENCE_PCT)}). "
                f"Приоритет — кампании с ДРР выше {_pct1(DRR_HIGH_THRESHOLD)}.",
            ))
        else:
            recs.append((
                "bad", title,
                f"ДРР выше порога {_pct1(DRR_HIGH_THRESHOLD)}. Проверить кампании и товары с максимальным "
                f"расходом: снизить ставки или приостановить неокупаемые.",
            ))

    if t.get("assoc_share") is not None and t["assoc_share"] >= 10:
        recs.append((
            "info", f"Связанные заказы — {_spaced(t['assoc_share'])} % суммы заказов от рекламы",
            f"WB относит к рекламе и заказы других товаров, сделанные после перехода по объявлению "
            f"({_money(t['revenue_assoc'])}). С ними ДРР — {_pct1(drr)}, без них — {_pct1(drr_direct)}. "
            f"Оценки кампаний в отчёте считаются по рекламируемым товарам.",
        ))

    cur_drr = drr_direct if drr_direct is not None else drr
    prev_drr = prev.get("drr_direct") if prev is not None else None
    if prev_drr is None and prev is not None:
        prev_drr, cur_drr = prev.get("drr"), drr
    if prev is not None and cur_drr is not None and prev_drr is not None:
        diff = cur_drr - prev_drr
        prev_label = _period_label(bundle["prev_start"], bundle["prev_end"])
        spend_chg = _change_pct(spend, prev["spend_rub"])
        orders_chg = _change_pct(t["orders"], prev["orders"])
        kind = "по рекламируемым товарам " if prev.get("drr_direct") is not None else ""
        base = (
            f"ДРР {kind}{_pct1(cur_drr)} против {_pct1(prev_drr)} за {prev_label}. "
            f"Расход {_signed_pct(spend_chg)}, заказы от рекламы {_signed_pct(orders_chg)}."
        )
        if abs(diff) >= DRR_TREND_DELTA:
            recs.append((
                "bad" if diff > 0 else "good",
                f"ДРР {'вырос' if diff > 0 else 'снизился'} на {_spaced(abs(diff), 1)} п.п.",
                base + (" Проверить ставки, конкуренцию и сезонность спроса." if diff > 0 else ""),
            ))
        else:
            recs.append(("info", "ДРР стабилен относительно предыдущего периода", base))

    ptd = bundle.get("period_to_date") or {}
    month = ptd.get("month") or {}
    if month.get("change_pct") is not None and abs(month["change_pct"]) >= 5:
        faster = month["change_pct"] > 0
        recs.append((
            "warn" if faster else "info",
            f"Темп расходов в месяце {'выше' if faster else 'ниже'} прошлого",
            f"С начала месяца {_money(month['spend'])} — на {_spaced(abs(month['change_pct']))} % "
            f"{'больше' if faster else 'меньше'}, чем за те же дни прошлого месяца "
            f"({_money(month.get('prev_spend'))}).",
        ))

    if not active.empty:
        top = active.iloc[0]
        share = top["spend_rub"] / spend * 100
        if share >= CONCENTRATION_THRESHOLD:
            recs.append((
                "warn", "Бюджет сосредоточен в одной кампании",
                f"«{top['name']}» — {_spaced(share)} % расхода. Просадка этой кампании "
                f"сильнее всего отразится на общем результате.",
            ))

        bad = active[active["quality"] == QUALITY_BAD]
        if not bad.empty:
            bad_spend = bad["spend_rub"].sum()
            no_orders = bad[bad["orders_direct"] == 0]
            ok_with_assoc = bad[bad["drr"].notna() & (bad["drr"] <= DRR_HIGH_THRESHOLD)]
            text = (
                f"{len(bad)} {_plural(len(bad), 'кампания', 'кампании', 'кампаний')} "
                f"с расходом {_money(bad_spend)} ({_spaced(bad_spend / spend * 100, 1)} % бюджета): "
                f"ДРР по рекламируемым товарам выше {_pct1(DRR_HIGH_THRESHOLD)}"
            )
            if not no_orders.empty:
                text += f", у {len(no_orders)} нет заказов рекламируемых товаров"
            if not ok_with_assoc.empty:
                text += (
                    f". С учётом связанных заказов {len(ok_with_assoc)} из них укладываются в порог — "
                    f"они приносят продажи другим товарам, но сами рекламируемые товары продаются слабо"
                )
            recs.append(("bad", "Неэффективные кампании (по рекламируемым товарам)",
                         text + ". Список — в разделе «Неэффективные кампании»."))

    if not products.empty:
        dead_threshold = max(500.0, spend * 0.005)
        dead = products[(products["spend_rub"] >= dead_threshold) & (products["orders"] == 0)]
        if not dead.empty:
            recs.append((
                "bad", f"{len(dead)} {_plural(len(dead), 'товар', 'товара', 'товаров')} с рекламой без заказов",
                f"Суммарный расход {_money(dead['spend_rub'].sum())}. Проверить карточки: цену, фото, отзывы, "
                f"релевантность запросам. Например: " + ", ".join(f"«{x}»" for x in dead["title"].head(3)) + ".",
            ))

        low = bundle.get("low_stock")
        if low is not None and not low.empty:
            recs.append((
                "warn", f"Реклама на товары с низким остатком: {len(low)}",
                f"Товары в активных и приостановленных кампаниях с остатком меньше {LOW_STOCK_QTY_THRESHOLD} шт. "
                f"(WB + FBS на {_date(bundle.get('stocks_as_of'))}); расход на них за период — "
                f"{_money(low['spend_rub'].sum())}. Пополнить остаток или исключить товар из кампании. "
                f"Список — в разделе «Товары».",
            ))

    if not campaigns.empty:
        ending = campaigns[
            (campaigns["status"] == STATUS_ACTIVE)
            & campaigns["runway_days"].notna()
            & (campaigns["runway_days"] < CAMPAIGN_RUNWAY_WARN_DAYS)
        ]
        if not ending.empty:
            recs.append((
                "warn", f"Бюджет заканчивается у {len(ending)} {_plural(len(ending), 'кампании', 'кампаний', 'кампаний')}",
                "Остатка бюджета хватит меньше чем на "
                f"{CAMPAIGN_RUNWAY_WARN_DAYS} дн.: " + ", ".join(f"«{x}»" for x in ending["name"].head(4)) + ".",
            ))

    if budget.get("runway_days") is not None and budget["runway_days"] < BUDGET_RUNWAY_WARN_DAYS:
        recs.append((
            "warn", f"Средств хватит примерно на {_days(budget['runway_days'])} дн.",
            f"Счёт и бюджеты кампаний — {_money((budget['net'] or 0) + budget['budgets_total'])} при среднем "
            f"расходе {_money(budget['avg_daily_spend'])} в день. Запланировать пополнение.",
        ))

    if recon["available"] and recon["diff_pct"] is not None and abs(recon["diff_pct"]) >= RECONCILIATION_TOLERANCE_PCT:
        recs.append((
            "info", "Расход по статистике и списания расходятся",
            f"Статистика — {_money(recon['stats_spend'])}, списано по документам — {_money(recon['charged'])} "
            f"({_signed_pct(recon['diff_pct'])}). Разница на границах периода нормальна; "
            f"детали — в разделе «Сверка».",
        ))

    platforms = bundle.get("platforms")
    if platforms is not None and not platforms.empty and drr_direct and "drr_direct" in platforms:
        worst = platforms[(platforms["share"] >= 10) & (platforms["drr_direct"] > drr_direct * 1.5)]
        for row in worst.head(1).itertuples(index=False):
            recs.append((
                "warn", f"Площадка «{row.platform}» дороже среднего",
                f"{_spaced(row.share)} % расхода, ДРР по рекламируемым товарам {_pct1(row.drr_direct)} "
                f"против {_pct1(drr_direct)} в среднем.",
            ))

    return recs


def _narrative(bundle: dict) -> str:
    t = bundle["totals"]
    if t["spend_rub"] == 0 and t["views"] == 0:
        return "За выбранный период данных по рекламе нет."

    parts = [
        f"Расход на рекламу — {_money(t['spend_rub'])}. Рекламируемые товары получили "
        f"{_int(t.get('orders_direct'))} {_plural(t.get('orders_direct') or 0, 'заказ', 'заказа', 'заказов')} на "
        f"{_money(t.get('revenue_direct'))}, ДРР по ним — {_pct1(t.get('drr_direct'))}."
    ]
    if t.get("revenue_assoc"):
        parts.append(
            f"Ещё {_money(t['revenue_assoc'])} — связанные заказы других товаров после перехода по рекламе; "
            f"с ними ДРР — {_pct1(t['drr'])}."
        )
    prev = bundle["prev_totals"]
    if prev and prev["spend_rub"]:
        parts.append(
            f"К предыдущему периоду: расход {_signed_pct(_change_pct(t['spend_rub'], prev['spend_rub']))}, "
            f"сумма заказов {_signed_pct(_change_pct(t['revenue_rub'], prev['revenue_rub']))}."
        )

    campaigns = bundle["campaigns"]
    if not campaigns.empty and campaigns["spend_rub"].sum() > 0:
        top = campaigns.iloc[0]
        parts.append(f"Крупнейшая кампания — «{top['name']}» ({_money(top['spend_rub'])}).")
        bad_spend = campaigns.loc[campaigns["quality"] == QUALITY_BAD, "spend_rub"].sum()
        if t["spend_rub"] and bad_spend / t["spend_rub"] >= 0.01:
            parts.append(
                f"На неэффективные кампании пришлось {_pct1(bad_spend / t['spend_rub'] * 100)} расхода "
                f"({_money(bad_spend)})."
            )

    tacos = bundle["tacos"]
    if tacos.get("available"):
        parts.append(
            f"Доля рекламы в продажах (ДРР от продаж) — {_pct1(tacos['value'])}"
            + (f" по {_date(tacos['end'])}." if tacos.get("partial") else ".")
        )
    return " ".join(parts)


# ================================================================ методология
def _methodology() -> list[tuple[str, list[tuple[str, str]]]]:
    bands = "; ".join(f"«{label}» — {rng}" for label, rng in _drr_bands_with_ranges())
    return [
        ("Источники данных", [
            ("Кампании", "WB API «Продвижение»: список кампаний, тип, статус, модель оплаты, тип ставки, "
                         "состав товаров и ставки. Актуальное состояние — последний снимок."),
            ("Статистика", "Метод fullstats: показы, клики, расход, корзины, заказы, сумма заказов, отмены "
                           "по кампании и дню, а также по товару и площадке (сайт, Android, iOS)."),
            ("Бюджеты", "Остаток бюджета каждой активной и приостановленной кампании на момент загрузки."),
            ("Списания", "Фактические списания по документам WB (дата списания, сумма, источник: "
                         "баланс, бонусы, счёт, кэшбэк)."),
            ("Пополнения", "История пополнений рекламного счёта."),
            ("Баланс", "Баланс рекламного кабинета: доступно к расходу (net), баланс, бонусы."),
            ("Справочники", "Наименование, бренд и категория товара — справочник товаров компании; "
                            "остатки — склады WB и FBS на последнюю дату; продажи — отчёт реализации WB."),
            ("Обновление", "Ежедневно. Статистика за последние 30 дней запрашивается повторно: "
                           "WB уточняет данные задним числом, в расчёт идёт последняя версия каждого дня."),
        ]),
        ("Показатели", [
            ("Показы / клики", "Количество показов рекламы и переходов по ней."),
            ("CTR", "Кликабельность: клики ÷ показы × 100 %."),
            ("CPC", "Средняя цена клика: расход ÷ клики."),
            ("CPM", "Стоимость 1 000 показов: расход ÷ показы × 1 000."),
            ("Корзины", "Добавления товара в корзину после перехода по рекламе."),
            ("Заказы", "Заказы, которые WB отнёс к рекламе. Заказано, шт. — число единиц товара в них."),
            ("CR", "Конверсия клика в заказ: заказы ÷ клики × 100 %."),
            ("CPO", "Стоимость заказа: расход ÷ заказы."),
            ("Сумма заказов", "Стоимость рекламных заказов по цене на момент заказа. Не равна выручке: "
                              "часть заказов будет отменена или не выкуплена."),
            ("ДРР", "Доля рекламных расходов: расход ÷ сумма заказов от рекламы × 100 %. Считается по всем "
                    "заказам, которые WB отнёс к рекламе, включая связанные."),
            ("Связанные заказы", "Заказы других товаров продавца, сделанные покупателем после перехода по рекламе. "
                                 "WB включает их в статистику кампании, хотя эти товары не рекламировались и не "
                                 "показывались. В отчёте выделены отдельно."),
            ("ДРР по рекламируемым товарам", "Расход ÷ сумма заказов только тех товаров, которые показывались в "
                                             "кампании или входят в её состав × 100 %. Основной показатель для "
                                             "оценки кампаний."),
            ("ДРР от продаж", "Расход ÷ продажи товара по всем каналам (отчёт реализации, за вычетом возвратов) "
                              "× 100 %. Считается только за дни, по которым есть отчёт реализации."),
            ("Средняя позиция", "Средняя позиция товара в выдаче; WB отдаёт её для кампаний с единой ставкой."),
            ("Площадка", "Где покупатель увидел объявление и кликнул: приложение WB на iOS или Android либо сайт. "
                         "Заказ засчитывается площадке, с которой был клик."),
            ("Остаток", "Остаток товара на складах WB и FBS на дату последнего снимка, не на конец периода."),
        ]),
        ("Расчёт и агрегация", [
            ("Средневзвешенные", "CTR, CPC, CR, ДРР за период считаются из сумм показов, кликов, расхода, заказов, "
                                 "а не как среднее дневных значений."),
            ("Кампании и товары", "Итоги по кампаниям — из статистики уровня кампании; по товарам — из "
                                  "детализации по товарам. Суммы могут незначительно расходиться из-за округлений WB."),
            ("Сравнение", "Предыдущий период — той же длины, непосредственно перед выбранным. "
                          "Темп с начала недели/месяца/квартала/года сравнивается с тем же числом дней "
                          "предыдущего отрезка."),
            ("Период", "Если период в дашборде не выбран, отчёт строится за всю историю."),
        ]),
        ("Оценки", [
            ("Шкала ДРР", f"{bands}. Внутренний ориентир компании при марже до рекламы "
                          f"~{_pct1(PRE_AD_MARGIN_REFERENCE_PCT)}; пересматривается при изменении маржи."),
            ("Оценка кампании", f"«{QUALITY_LOW}» — расход меньше {_money(CAMPAIGN_MIN_SPEND_TO_JUDGE)} "
                                f"или 1–{CAMPAIGN_MIN_ORDERS_TO_JUDGE - 1} заказа. «{QUALITY_BAD}» — заметный расход "
                                f"без заказов или ДРР выше {_pct1(DRR_HIGH_THRESHOLD)}. «{QUALITY_GOOD}» — от "
                                f"{CAMPAIGN_MIN_ORDERS_TO_JUDGE} заказов и ДРР не выше {_pct1(DRR_HIGH_THRESHOLD)}. "
                                f"Заказы и ДРР — по рекламируемым товарам, без связанных заказов."),
            ("Запас бюджета", f"Остаток бюджета кампании ÷ средний дневной расход за последние "
                              f"{RUNWAY_LOOKBACK_DAYS} дней. Для кабинета — (net + бюджеты кампаний) ÷ тот же расход."),
            ("Низкий остаток", f"Товар в рекламе с остатком меньше {LOW_STOCK_QTY_THRESHOLD} шт. (WB + FBS)."),
        ]),
        ("Сверка и ограничения", [
            ("Начислено и списано", "Начислено — расход из статистики показов и кликов. Списано — суммы из "
                                    "«Истории затрат» WB Продвижение. Списания идут с задержкой до суток, поэтому "
                                    "по дням возможна разница; расхождение больше "
                                    f"{_spaced(RECONCILIATION_TOLERANCE_PCT)} % за период выносится в выводы."),
            ("Единый счёт", "Деньги на Едином счёте — предоплата, а не расход. Расходом они становятся при списании "
                            "за рекламу. С самого счёта WB снимает накопленный расход пачкой раз в несколько дней."),
            ("Атрибуция", "Отнесение заказов к рекламе выполняет WB по своим правилам. Заказ может быть учтён "
                          "у товара без прямого расхода (например, при заказе нескольких товаров в одной сессии)."),
            ("Бюджеты", "Показываются на момент последней загрузки, не на дату окончания периода."),
            ("Удалённые кампании", "Если кампания отсутствует в справочнике, она показана как «Кампания без названия»."),
        ]),
    ]


# ================================================================ PDF: стили
_PDF_CSS = f"""
@page {{
    size: A4; margin: 15mm 13mm 15mm 13mm;
    @bottom-left {{ content: "Анализ рекламных кампаний WB"; font: 7.5px Arial, sans-serif; color: #8A918E; }}
    @bottom-right {{ content: counter(page) " / " counter(pages); font: 7.5px Arial, sans-serif; color: #8A918E; }}
}}
@page wide {{ size: A4 landscape; margin: 12mm 13mm 14mm 13mm; }}
* {{ box-sizing: border-box; }}
body {{ font-family: Arial, "Liberation Sans", "DejaVu Sans", sans-serif; color: {C.INK};
        font-size: 9.2px; line-height: 1.4; margin: 0; }}
section {{ break-before: page; }}
section.first {{ break-before: auto; }}
section.wide {{ page: wide; }}
h1 {{ font-family: {C.SERIF}; font-size: 21px; color: {C.NAVY_3}; margin: 0; font-weight: 700; }}
h2 {{ font-family: {C.SERIF}; font-size: 14.5px; color: {C.NAVY_3}; margin: 0 0 3px; font-weight: 700;
      break-after: avoid; }}
h3 {{ font-size: 10px; color: {C.NAVY_3}; margin: 12px 0 5px; text-transform: uppercase;
      letter-spacing: .04em; break-after: avoid; }}
.lead {{ color: {C.INK_2}; font-size: 8.8px; margin: 0 0 10px; padding-bottom: 6px;
         border-bottom: 1.5px solid {C.NAVY}; }}
.masthead {{ border-bottom: 2px solid {C.NAVY}; padding-bottom: 8px; margin-bottom: 10px; }}
.meta {{ display: flex; gap: 22px; margin-top: 6px; font-size: 8.4px; color: {C.INK_2}; }}
.meta b {{ display: block; color: {C.INK}; font-size: 9.2px; }}
.kpis {{ display: flex; flex-wrap: wrap; border-top: 1px solid {C.LINE};
         border-left: 1px solid {C.LINE}; margin-bottom: 10px; break-inside: avoid; }}
.kpi {{ width: 25%; padding: 6px 8px; border-right: 1px solid {C.LINE}; border-bottom: 1px solid {C.LINE}; }}
.kpi.main {{ background: {C.TINT_3}; }}
.kpi-label {{ font-size: 7.4px; color: {C.INK_2}; text-transform: uppercase; letter-spacing: .03em; }}
.kpi-value {{ font-size: 15px; font-weight: 700; color: {C.NAVY_3}; margin-top: 1px; white-space: nowrap; }}
.kpi-sub {{ font-size: 7.6px; color: {C.MUTED}; margin-top: 1px; white-space: nowrap; }}
.up-good, .down-good {{ color: {C.GOOD}; }}
.up-bad, .down-bad {{ color: {C.CRITICAL}; }}
.neutral {{ color: {C.INK_2}; }}
.summary {{ border-left: 3px solid {C.NAVY}; background: {C.TINT_3}; padding: 7px 10px; margin: 0 0 10px;
            font-size: 9.2px; break-inside: avoid; }}
.cols {{ display: flex; gap: 14px; }}
.cols > div {{ flex: 1; min-width: 0; }}
table {{ width: 100%; border-collapse: collapse; table-layout: fixed; font-size: 8.4px; margin-bottom: 4px; }}
thead {{ display: table-header-group; }}
th {{ background: {C.NAVY}; color: #fff; font-weight: 700; text-align: left; padding: 4px 5px;
      font-size: 7.8px; vertical-align: bottom; }}
td {{ padding: 3px 5px; border-bottom: 1px solid {C.LINE_SOFT}; vertical-align: top;
      overflow: hidden; text-overflow: ellipsis; }}
tr {{ break-inside: avoid; }}
.r {{ text-align: right; white-space: nowrap; }}
.c {{ text-align: center; }}
.wrap {{ white-space: normal; word-break: break-word; }}
.muted {{ color: {C.MUTED}; }}
tr.parent td {{ background: {C.TINT_2}; font-weight: 700; border-top: 1px solid {C.LINE}; }}
tr.child td {{ color: {C.INK_2}; font-size: 8px; }}
tr.child td.first {{ padding-left: 14px; }}
tr.total td {{ background: {C.TINT}; font-weight: 700; border-top: 1.5px solid {C.NAVY};
               border-bottom: 1.5px double {C.NAVY}; }}
tr.zebra:nth-child(even) td {{ background: {C.SURFACE_SOFT}; }}
.tag {{ display: inline-block; padding: 0 4px; font-size: 7.3px; font-weight: 700; white-space: nowrap;
        border: 1px solid transparent; }}
.tag.good {{ color: {C.GOOD}; background: {C.GOOD_BG}; border-color: #BFE8C6; }}
.tag.warn {{ color: #8A5A00; background: {C.WARNING_BG}; border-color: #F5DDA0; }}
.tag.bad {{ color: {C.CRITICAL}; background: {C.CRITICAL_BG}; border-color: #F2C2C2; }}
.tag.unknown, .tag.info {{ color: {C.INK_2}; background: {C.SURFACE_SOFT}; border-color: {C.LINE}; }}
.drr-good {{ color: {C.GOOD}; font-weight: 700; }}
.drr-warn {{ color: #8A5A00; font-weight: 700; }}
.drr-bad {{ color: {C.CRITICAL}; font-weight: 700; }}
.rec {{ display: flex; gap: 8px; padding: 6px 0; border-bottom: 1px solid {C.LINE_SOFT}; break-inside: avoid; }}
.rec-mark {{ width: 3px; flex: none; }}
.rec-mark.good {{ background: {C.GOOD}; }} .rec-mark.warn {{ background: {C.WARNING}; }}
.rec-mark.bad {{ background: {C.CRITICAL}; }} .rec-mark.info {{ background: {C.AXIS}; }}
.rec-title {{ font-weight: 700; color: {C.INK}; font-size: 9.4px; }}
.rec-text {{ color: {C.INK_2}; margin-top: 1px; }}
.chart {{ width: 100%; display: block; margin: 2px 0 8px; break-inside: avoid; }}
.note {{ font-size: 7.6px; color: {C.MUTED}; margin: 4px 0 8px; }}
.empty {{ color: {C.MUTED}; padding: 8px 0; font-size: 8.6px; }}
.error {{ color: {C.CRITICAL}; background: {C.CRITICAL_BG}; padding: 6px 8px; font-size: 8.4px; }}
.funnel-row {{ display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }}
.funnel-label {{ width: 18%; font-weight: 700; }}
.funnel-track {{ flex: 1; height: 13px; background: {C.SURFACE_SOFT}; }}
.funnel-fill {{ height: 13px; background: {C.NAVY_2}; }}
.funnel-value {{ width: 16%; text-align: right; font-weight: 700; }}
.funnel-conv {{ width: 26%; color: {C.INK_2}; font-size: 8px; }}
.method h3 {{ margin-top: 8px; }}
.method td {{ padding: 2px 5px; font-size: 8px; }}
.method table td:first-child {{ font-weight: 700; color: {C.NAVY_3}; }}
.scale td {{ padding: 3px 6px; }}
"""


# ================================================================ PDF: компоненты
def _table(headers: list[tuple[str, str, float]], rows: list[tuple[list[str], str]],
           cls: str = "") -> str:
    """headers: (заголовок, выравнивание l|r|c, ширина %); rows: (ячейки html, класс строки)."""
    cols = "".join(f'<col style="width:{w}%">' for _, _, w in headers)
    head = "".join(f'<th class="{a}">{_esc(h)}</th>' for h, a, _ in headers)
    body = []
    for cells, row_cls in rows:
        tds = []
        for i, (cell, (_, align, _w)) in enumerate(zip(cells, headers)):
            classes = [align] + (["first"] if i == 0 else [])
            tds.append(f'<td class="{" ".join(classes)}">{cell}</td>')
        body.append(f'<tr class="{row_cls}">{"".join(tds)}</tr>')
    return (f'<table class="{cls}"><colgroup>{cols}</colgroup><thead><tr>{head}</tr></thead>'
            f'<tbody>{"".join(body)}</tbody></table>')


def _tag(text: str, kind: str) -> str:
    return f'<span class="tag {kind}">{_esc(text)}</span>'


def _drr_cell(drr) -> str:
    group = _drr_group(drr)
    cls = f"drr-{group}" if group in ("good", "warn", "bad") else ""
    return f'<span class="{cls}">{_pct1(drr)}</span>'


def _quality_tag(q: str) -> str:
    return _tag(q, {QUALITY_GOOD: "good", QUALITY_BAD: "bad"}.get(q, "unknown"))


def _status_tag(status, name) -> str:
    kind = {STATUS_ACTIVE: "good", STATUS_PAUSED: "warn"}.get(_num(status), "unknown")
    return _tag(name or "—", kind)


def _chart(uri: str | None, caption: str = "") -> str:
    if not uri:
        return f'<div class="empty">{_esc(caption or "Недостаточно данных для графика")}</div>'
    return f'<img class="chart" src="{uri}" alt="{_esc(caption)}">'


_POLARITY = {
    "spend_rub": 0, "revenue_rub": 1, "orders": 1, "views": 1, "clicks": 1, "atbs": 1,
    "ctr": 1, "cpc": -1, "cpm": -1, "cr": 1, "cpo": -1, "drr": -1, "shks": 1,
}


def _delta_html(key: str, cur, prev, is_pct: bool = False) -> str:
    if prev is None:
        return '<span class="neutral">нет данных для сравнения</span>'
    if is_pct:
        c, p = _num(cur), _num(prev)
        if c is None or p is None:
            return '<span class="neutral">—</span>'
        diff = c - p
        text = _pp(diff)
    else:
        diff = _change_pct(cur, prev)
        if diff is None:
            return '<span class="neutral">—</span>'
        text = _signed_pct(diff)
    polarity = _POLARITY.get(key, 0)
    if abs(diff) < 0.05 or polarity == 0:
        cls = "neutral"
    else:
        cls = "up-good" if diff * polarity > 0 else "up-bad"
    return f'<span class="{cls}">{text}</span> <span class="neutral">к пред. периоду</span>'


def _kpi(label: str, value: str, sub: str = "", main: bool = False) -> str:
    return (f'<div class="kpi{" main" if main else ""}"><div class="kpi-label">{_esc(label)}</div>'
            f'<div class="kpi-value">{value}</div><div class="kpi-sub">{sub}</div></div>')


def _kpis_html(bundle: dict) -> str:
    t, p = bundle["totals"], bundle["prev_totals"]

    def pv(key):
        return p.get(key) if p else None

    drr_direct = t.get("drr_direct")
    rating = _drr_rating(drr_direct)
    drr_direct_value = _pct1(drr_direct) + (f" {_tag(rating, _drr_group(drr_direct))}" if rating else "")
    assoc_sub = (
        f"в т.ч. связанные заказы {_pct1(t.get('assoc_share'))}"
        if t.get("assoc_share") is not None else "все заказы от рекламы"
    )
    tacos = bundle["tacos"]
    tacos_sub = (
        f"по {_date(tacos['end'])}" if tacos.get("partial") else "расход ÷ продажи товаров"
    ) if tacos.get("available") else "нет данных о продажах"

    tiles = [
        _kpi("Расход на рекламу", _money(t["spend_rub"]), _delta_html("spend_rub", t["spend_rub"], pv("spend_rub")), True),
        _kpi("Сумма заказов от рекламы", _money(t["revenue_rub"]), assoc_sub, True),
        _kpi("ДРР по рекламируемым товарам", drr_direct_value, "без связанных заказов", True),
        _kpi("Заказы от рекламы", _int(t["orders"]), _delta_html("orders", t["orders"], pv("orders")), True),
        _kpi("Показы", _int(t["views"]), _delta_html("views", t["views"], pv("views"))),
        _kpi("Клики", _int(t["clicks"]), _delta_html("clicks", t["clicks"], pv("clicks"))),
        _kpi("CTR", _pct1(t["ctr"]), _delta_html("ctr", t["ctr"], pv("ctr") if p else None, True)),
        _kpi("CPC, цена клика", _money_dec(t["cpc"]), _delta_html("cpc", t["cpc"], pv("cpc"))),
        _kpi("CR, клик → заказ", _pct1(t["cr"]), _delta_html("cr", t["cr"], pv("cr") if p else None, True)),
        _kpi("CPO, цена заказа", _money(t["cpo"]), _delta_html("cpo", t["cpo"], pv("cpo"))),
        _kpi("ДРР с учётом связанных заказов", _pct1(t["drr"]), _delta_html("drr", t["drr"], pv("drr") if p else None, True)),
        _kpi("ДРР от продаж", _pct1(tacos.get("value")), tacos_sub),
    ]
    return f'<div class="kpis">{"".join(tiles)}</div>'


def _budget_html(bundle: dict) -> str:
    b = bundle["budget"]
    tiles = [
        _kpi("Доступно на счёте (net)", _money(b["net"]),
             f"на {_date(b['balance_as_of'])}" if b["balance_as_of"] is not None else "баланс не загружен"),
        _kpi("Бюджеты кампаний", _money(b["budgets_total"]) if b["budgets_known"] else "—",
             f"активных {b['active_n']}, на паузе {b['paused_n']}"),
        _kpi("Средний расход в день", _money(b["avg_daily_spend"]),
             f"за последние {RUNWAY_LOOKBACK_DAYS} дн. по живым кампаниям"),
        _kpi("Хватит средств", f"{_days(b['runway_days'])} дн." if b["runway_days"] is not None else "—",
             "(net + бюджеты) ÷ средний расход"),
    ]
    return f'<div class="kpis">{"".join(tiles)}</div>'


def _drr_scale_html() -> str:
    rows = []
    for label, rng in _drr_bands_with_ranges():
        group = "bad" if label == DRR_RATING_WORST_LABEL else _drr_group(
            next(u for u, lbl in DRR_RATING_BANDS if lbl == label))
        rows.append(([_tag(label, group), rng], ""))
    return _table([("Оценка ДРР", "l", 55), ("Диапазон", "r", 45)], rows, "scale")


def _drr_explain_html(bundle: dict) -> str:
    t = bundle["totals"]
    tacos = bundle["tacos"]
    rows = [
        (["<b>ДРР по рекламируемым товарам</b>", _drr_cell(t.get("drr_direct")),
          "Расход ÷ сумма заказов товаров, которые показывались в кампании",
          "Основной показатель: окупается ли реклама самих товаров. По нему ставятся оценки кампаний."], ""),
        (["<b>ДРР с учётом связанных заказов</b>", _pct1(t["drr"]),
          "Расход ÷ все заказы, которые WB отнёс к рекламе, включая заказы других товаров "
          "после перехода по объявлению",
          "Полный эффект рекламы на продажи магазина. Всегда ниже первого показателя."], ""),
        (["<b>ДРР от продаж</b>", _pct1(tacos.get("value")),
          "Расход ÷ фактические продажи всех товаров по отчёту реализации (за вычетом возвратов)",
          "Доля рекламы в реальной выручке — ближе всего к финансовой отчётности."], ""),
    ]
    return _table(
        [("Показатель", "l", 22), ("Значение", "r", 10), ("Как считается", "l", 36), ("Зачем смотреть", "l", 32)],
        [([f"<span class='wrap'>{c}</span>" for c in cells], cls) for cells, cls in rows],
    )


def _ptd_ranges(as_of) -> dict:
    end = pd.Timestamp(as_of).normalize()
    starts = {
        "week": end - pd.Timedelta(days=end.weekday()),
        "month": end.replace(day=1),
        "quarter": end.to_period("Q").start_time,
        "year": end.replace(month=1, day=1),
    }
    shifts = {
        "week": pd.Timedelta(days=7),
        "month": pd.DateOffset(months=1),
        "quarter": pd.DateOffset(months=3),
        "year": pd.DateOffset(years=1),
    }
    return {k: (starts[k], end, starts[k] - shifts[k], end - shifts[k]) for k in starts}


def _ptd_html(bundle: dict) -> str:
    ptd = bundle.get("period_to_date")
    if not ptd or ptd.get("as_of") is None:
        return '<div class="empty">Нет данных.</div>'
    ranges = _ptd_ranges(ptd["as_of"])
    tiles = []
    for key in ("week", "month", "quarter", "year"):
        p = ptd[key]
        s, e, ps, pe = ranges[key]
        prev_label = f"{ps:%d.%m}–{pe:%d.%m.%Y}"
        if p["change_pct"] is None:
            sub = f'<span class="neutral">нет данных за {prev_label}</span>'
        else:
            sub = (f'{_delta_html("spend_rub", p["spend"], p["prev_spend"]).split(" <span")[0]} '
                   f'<span class="neutral">к {prev_label}</span>')
        tiles.append(_kpi(f"{p['label']} ({s:%d.%m}–{e:%d.%m})", _money(p["spend"]), sub))
    return (f'<div class="kpis">{"".join(tiles)}</div>'
            f'<div class="note">Расход с начала недели, месяца, квартала и года по {_date(ptd.get("as_of"))} '
            f'включительно — в сравнении с тем же числом дней предыдущей недели, месяца, квартала и года.</div>')


def _recommendations_html(bundle: dict) -> str:
    items = []
    for level, title, text in _recommendations(bundle):
        items.append(
            f'<div class="rec"><div class="rec-mark {level}"></div><div>'
            f'<div class="rec-title">{_esc(title)}</div><div class="rec-text">{_esc(text)}</div></div></div>'
        )
    return "".join(items)


# ================================================================ PDF: графики
_FREQ_WORDS = {
    "day": ("по дням", "в день", "день", ("день", "дня", "дней")),
    "week": ("по неделям", "в неделю", "неделя", ("неделя", "недели", "недель")),
    "month": ("по месяцам", "в месяц", "месяц", ("месяц", "месяца", "месяцев")),
}


def _spend_conclusion(df: pd.DataFrame, freq: str) -> str:
    _, per, unit, _ = _FREQ_WORDS[freq]
    values = df["spend_rub"].astype(float)
    parts = [f"В среднем реклама тратила {_money(values.mean())} {per}."]
    if len(df) >= 4:
        half = len(df) // 2
        first, second = values.iloc[:half].mean(), values.iloc[half:].mean()
        chg = _change_pct(second, first)
        if chg is not None and abs(chg) >= 5:
            parts.append(
                f"Во второй половине периода расход {'вырос' if chg > 0 else 'снизился'} на "
                f"{_spaced(abs(chg))} % ({_money(first)} → {_money(second)} {per})."
            )
        else:
            parts.append("Темп расходов в течение периода был ровным.")
    top = df.loc[values.idxmax()]
    parts.append(f"Самый дорогой {unit} — {top['label']}: {_money(top['spend_rub'])}.")
    return " ".join(parts)


def _drr_conclusion(df: pd.DataFrame, freq: str) -> str:
    _, _, _, forms = _FREQ_WORDS[freq]
    direct = df[df["drr_direct"].notna()] if "drr_direct" in df else df.iloc[0:0]
    parts = []
    if not direct.empty:
        lo, hi = direct.loc[direct["drr_direct"].idxmin()], direct.loc[direct["drr_direct"].idxmax()]
        parts.append(
            f"ДРР по рекламируемым товарам менялся от {_pct1(lo['drr_direct'])} ({lo['label']}) "
            f"до {_pct1(hi['drr_direct'])} ({hi['label']})."
        )
        over = int((direct["drr_direct"] > DRR_HIGH_THRESHOLD).sum())
        if over:
            parts.append(f"Выше порога {_pct1(DRR_HIGH_THRESHOLD)} — {over} {_plural(over, *forms)} из {len(direct)}.")
        else:
            parts.append(f"Ни разу не поднимался выше порога {_pct1(DRR_HIGH_THRESHOLD)}.")
    total = df[df["drr"].notna()]
    if not total.empty:
        parts.append(
            f"С учётом связанных заказов ДРР держался в диапазоне {_pct1(total['drr'].min())}–"
            f"{_pct1(total['drr'].max())}."
        )
    return " ".join(parts)


def _trend_charts_html(bundle: dict) -> str:
    df = bundle["trend"]
    if df is None or df.empty:
        return '<div class="empty">Нет данных.</div>'

    freq = bundle["trend_freq"]
    unit = _FREQ_WORDS[freq][0]
    spike = bundle.get("trend_spike")
    labels = df["label"].tolist()
    values = df["spend_rub"].astype(float).tolist()
    x = list(range(len(labels)))
    step = max(1, -(-len(labels) // 14))
    annotate = len(labels) <= 16
    peak = int(np.argmax(values)) if values else None

    fig, ax = _cr_fig(height=2.9)
    colors = [C.CRITICAL if spike and lbl == spike["label"] else C.SERIES_1 for lbl in labels]
    ax.bar(x, values, width=0.62, color=colors, linewidth=0)
    for i, v in enumerate(values):
        if annotate or i == peak:
            ax.annotate(_cr_short(v), xy=(i, v), xytext=(0, 2), textcoords="offset points",
                        ha="center", fontsize=6.8, fontweight="bold", color=C.INK)
    ax.set_xticks(x[::step])
    ax.set_xticklabels(labels[::step], fontsize=6.6)
    ax.set_xlim(-0.6, len(labels) - 0.4)
    ax.yaxis.set_major_formatter(_cr_money_formatter())
    ax.set_ylabel("Расход, ₽")
    ax.set_ylim(0, (max(values) or 1) * 1.2)
    spend_uri = _cr_render(fig)

    drr_uri = None
    has_direct = "drr_direct" in df and df["drr_direct"].notna().sum() >= 2
    main_col = "drr_direct" if has_direct else "drr"
    drr_df = df[df[main_col].notna()]
    if len(drr_df) >= 2:
        fig2, ax2 = _cr_fig(height=2.5)
        dx = [labels.index(lbl) for lbl in drr_df["label"]]
        dv = drr_df[main_col].astype(float).tolist()
        ax2.plot(dx, dv, color=C.SERIES_1, linewidth=1.6, marker="o", markersize=2.8,
                 label="по рекламируемым товарам" if has_direct else "ДРР")
        if has_direct:
            tdf = df[df["drr"].notna()]
            ax2.plot([labels.index(lbl) for lbl in tdf["label"]], tdf["drr"].astype(float).tolist(),
                     color=C.AXIS, linewidth=1.2, linestyle=(0, (2, 1.5)), label="с учётом связанных заказов")
        over = [(i, v) for i, v in zip(dx, dv) if v > DRR_HIGH_THRESHOLD]
        if over:
            ax2.scatter([i for i, _ in over], [v for _, v in over], color=C.CRITICAL, s=12, zorder=3)
        ax2.axhline(DRR_HIGH_THRESHOLD, color=C.CRITICAL, linewidth=0.7, linestyle=(0, (3, 2)))
        ax2.annotate(f"порог {_cr_pct_label(DRR_HIGH_THRESHOLD, 0)}", xy=(len(labels) - 0.5, DRR_HIGH_THRESHOLD),
                     xytext=(0, 3), textcoords="offset points", ha="right", fontsize=6.4, color=C.CRITICAL)
        if annotate:
            for i, v in zip(dx, dv):
                ax2.annotate(_cr_pct_label(v, 1), xy=(i, v), xytext=(0, 4), textcoords="offset points",
                             ha="center", fontsize=6.3, color=C.INK)
        ax2.set_xticks(x[::step])
        ax2.set_xticklabels(labels[::step], fontsize=6.6)
        ax2.set_xlim(-0.6, len(labels) - 0.4)
        ax2.yaxis.set_major_formatter(_cr_pct_formatter(0))
        ax2.set_ylabel("ДРР, %")
        ax2.set_ylim(0, max(max(dv) * 1.25, DRR_HIGH_THRESHOLD * 1.35))
        if has_direct:
            ax2.legend(loc="upper left", ncol=2, fontsize=6.6)
        drr_uri = _cr_render(fig2)

    parts = [f"<h3>Расход {unit}</h3>", _chart(spend_uri),
             f'<div class="summary">{_esc(_spend_conclusion(df, freq))}</div>']
    if drr_uri:
        parts += [f"<h3>ДРР {unit}</h3>", _chart(drr_uri),
                  f'<div class="summary">{_esc(_drr_conclusion(df, freq))}</div>']
    return "".join(parts)


def _quality_block_html(bundle: dict) -> str:
    campaigns = bundle["campaigns"]
    if campaigns.empty or campaigns["spend_rub"].sum() <= 0:
        return '<div class="empty">Нет данных.</div>'
    active = campaigns[campaigns["spend_rub"] > 0]
    q = active.groupby("quality")["spend_rub"].sum().reindex(list(QUALITY_ORDER)).fillna(0).reset_index()
    q = q[q["spend_rub"] > 0]
    uri = _cr_hbar(
        labels=q["quality"].tolist(), values=q["spend_rub"].tolist(),
        colors=[{QUALITY_GOOD: C.GOOD, QUALITY_BAD: C.CRITICAL}.get(x, C.AXIS) for x in q["quality"]],
        axis_label="Расход, ₽", height=1.5,
    )
    total = active["spend_rub"].sum()
    counts = active["quality"].value_counts()
    bad = active[active["quality"] == QUALITY_BAD]
    parts = [
        f"Из {len(active)} кампаний с расходом {int(counts.get(QUALITY_GOOD, 0))} окупаются в пределах порога, "
        f"{int(counts.get(QUALITY_BAD, 0))} — нет, по {int(counts.get(QUALITY_LOW, 0))} данных пока мало."
    ]
    if not bad.empty:
        rescued = bad[bad["drr"].notna() & (bad["drr"] <= DRR_HIGH_THRESHOLD)]
        parts.append(
            f"На неэффективные ушло {_pct1(bad['spend_rub'].sum() / total * 100)} бюджета. "
            f"Оценка строгая — только по рекламируемым товарам."
        )
        if not rescued.empty:
            parts.append(
                f"Если учитывать связанные заказы, {len(rescued)} из {len(bad)} таких кампаний укладываются в порог: "
                f"они приводят покупателей в магазин, но сами рекламируемые товары покупают реже, чем хотелось бы."
            )
    return _chart(uri) + f'<div class="summary">{_esc(" ".join(parts))}</div>'


def _hbar_html(df: pd.DataFrame, label_col: str, caption: str, colors=None, n: int = TOP_CHART_N) -> str:
    if df is None or df.empty:
        return ""
    top = df[df["spend_rub"] > 0].head(n)
    if top.empty:
        return ""
    uri = _cr_hbar(
        labels=[str(x)[:48] for x in top[label_col]],
        values=top["spend_rub"].tolist(),
        colors=colors[: len(top)] if colors else None,
        axis_label="Расход, ₽",
    )
    return _chart(uri, caption)


def _funnel_html(t: dict) -> str:
    steps = [
        ("Показы", t["views"], ""),
        ("Клики", t["clicks"], f"CTR {_pct1(t['ctr'])} от показов"),
        ("Корзины", t["atbs"], f"{_pct1(t['cart_rate'])} от кликов"),
        ("Заказы", t["orders"], f"CR {_pct1(t['cr'])} от кликов"),
    ]
    top = max(t["views"], 1)
    rows = []
    for label, value, conv in steps:
        width = 0 if not value else max(2.0, np.log10(value + 1) / np.log10(top + 1) * 100)
        rows.append(
            f'<div class="funnel-row"><div class="funnel-label">{label}</div>'
            f'<div class="funnel-track"><div class="funnel-fill" style="width:{width:.1f}%"></div></div>'
            f'<div class="funnel-value">{_int(value)}</div><div class="funnel-conv">{conv}</div></div>'
        )
    extra = (f'<div class="note">Заказано {_int(t["shks"])} шт., отменено {_int(t["canceled"])} '
             f'({_pct1(t["cancel_rate"])} заказов). Длина полос — в логарифмической шкале.</div>')
    return "".join(rows) + extra


# ================================================================ PDF: разделы
def _metrics_row(r, first: str, extra: list[str] | None = None) -> list[str]:
    return [first, *(extra or []), _money(r.spend_rub), _int(r.orders), _money(r.revenue_rub), _drr_cell(r.drr)]


def _group_table_html(df: pd.DataFrame, col: str, title: str, compact: bool = False) -> str:
    if df is None or df.empty:
        return '<div class="empty">Нет данных.</div>'
    if compact:
        rows = [([_esc(getattr(r, col)), _pct1(r.share), _money(r.spend_rub), _int(r.orders_direct),
                  _drr_cell(r.drr_direct)], "zebra")
                for r in df.itertuples(index=False)]
        return _table([(title, "l", 34), ("Доля", "r", 15), ("Расход", "r", 20), ("Заказы*", "r", 14),
                       ("ДРР*", "r", 17)], rows)
    rows = [
        ([_esc(getattr(r, col)), _int(r.campaigns_n), _pct1(r.share), _money(r.spend_rub), _int(r.orders_direct),
          _money(r.cpo_direct), _drr_cell(r.drr_direct), _pct1(r.drr)], "zebra")
        for r in df.itertuples(index=False)
    ]
    return _table(
        [(title, "l", 25), ("Кампаний", "r", 9), ("Доля", "r", 9), ("Расход", "r", 14),
         ("Заказы*", "r", 10), ("CPO*", "r", 11), ("ДРР*", "r", 11), ("ДРР всех заказов", "r", 11)],
        rows,
    )


def _platforms_html(bundle: dict) -> str:
    df = bundle["platforms"]
    if df is None or df.empty:
        return '<div class="empty">Нет детализации по площадкам.</div>'
    df = df[df["spend_rub"] > 0]
    has_direct = "drr_direct" in df.columns
    rows = [
        ([_esc(r.platform), _pct1(r.share), _int(r.views), _pct1(r.ctr), _money_dec(r.cpc),
          _money(r.spend_rub),
          _int(r.orders_direct if has_direct else r.orders),
          _pct1(r.cr_direct if has_direct else r.cr),
          _drr_cell(r.drr_direct if has_direct else r.drr), _pct1(r.drr)], "zebra")
        for r in df.itertuples(index=False)
    ]
    table = _table(
        [("Площадка", "l", 12), ("Доля расхода", "r", 10), ("Показы", "r", 11), ("CTR", "r", 7),
         ("CPC", "r", 9), ("Расход", "r", 12), ("Заказы*", "r", 9), ("CR*", "r", 8), ("ДРР*", "r", 10),
         ("ДРР всех заказов", "r", 12)],
        rows,
    )
    note = ('<div class="note">Площадка — где покупатель увидел рекламу и кликнул по ней: в приложении WB на '
            'iOS или Android либо на сайте wildberries.ru. Заказ засчитывается площадке, с которой был клик. '
            '* По рекламируемым товарам.</div>')
    parts = []
    if has_direct and len(df) >= 2:
        best = df.loc[df["drr_direct"].idxmin()] if df["drr_direct"].notna().any() else None
        worst = df.loc[df["drr_direct"].idxmax()] if df["drr_direct"].notna().any() else None
        main = df.iloc[0]
        parts.append(f"Больше всего бюджета приходится на {main['platform']} — {_pct1(main['share'])} расхода.")
        if best is not None and worst is not None and best["platform"] != worst["platform"]:
            parts.append(
                f"Лучше всего реклама окупается на {best['platform']}: ДРР {_pct1(best['drr_direct'])} "
                f"против {_pct1(worst['drr_direct'])} на {worst['platform']}. "
                + (
                    f"Из 100 кликов на {best['platform']} получается {_spaced(best['cr_direct'], 1)} заказа, "
                    f"на {worst['platform']} — {_spaced(worst['cr_direct'], 1)}; "
                    f"клик стоит {_money_dec(best['cpc'])} и {_money_dec(worst['cpc'])}."
                    if pd.notna(best["cr_direct"]) and pd.notna(worst["cr_direct"]) else ""
                )
            )
            parts.append(
                "Ставка в кампании одна для всех площадок, WB сам распределяет показы между ними. "
                "Разница в ДРР — от поведения покупателей, а не от разных расценок: где чаще кликают, "
                "там клик дешевле (при оплате за показы), где чаще заказывают — там выше отдача."
            )
    conclusion = f'<div class="summary">{_esc(" ".join(parts))}</div>' if parts else ""
    return table + note + conclusion


def _brands_html(bundle: dict) -> str:
    df = bundle["brands"]
    if df is None or df.empty:
        return '<div class="empty">Нет данных по брендам.</div>'
    top = df[df["spend_rub"] > 0].head(TOP_CHART_N)
    total = df["spend_rub"].sum()
    rows = [
        ([_esc(r.brand), _pct1(r.spend_rub / total * 100 if total else None), _money(r.spend_rub),
          _int(r.orders), _money(r.revenue_rub), _drr_cell(r.drr)], "zebra")
        for r in top.itertuples(index=False)
    ]
    table = _table(
        [("Бренд", "l", 30), ("Доля", "r", 10), ("Расход", "r", 15), ("Заказы*", "r", 11),
         ("Сумма заказов*", "r", 17), ("ДРР*", "r", 17)],
        rows,
    )
    parts = []
    if not top.empty and total:
        lead = top.iloc[0]
        parts.append(f"Основной бюджет — {lead['brand']}: {_pct1(lead['spend_rub'] / total * 100)} расхода, "
                     f"ДРР {_pct1(lead['drr'])}.")
        judged = top[top["drr"].notna()]
        if len(judged) >= 2:
            best, worst = judged.loc[judged["drr"].idxmin()], judged.loc[judged["drr"].idxmax()]
            if best["brand"] != worst["brand"]:
                parts.append(f"Эффективнее всего реклама работает у {best['brand']} ({_pct1(best['drr'])}), "
                             f"хуже всего — у {worst['brand']} ({_pct1(worst['drr'])}).")
    note = '<div class="note">* По рекламируемым товарам бренда, без связанных заказов.</div>'
    summary = f'<div class="summary">{_esc(" ".join(parts))}</div>' if parts else ""
    return _hbar_html(top, "brand", "По брендам") + table + note + summary


def _campaign_budgets_html(bundle: dict) -> str:
    df = bundle["campaigns"]
    live = df[df["status"].isin([STATUS_ACTIVE, STATUS_PAUSED])] if not df.empty else df
    if live.empty:
        return '<div class="empty">Активных и приостановленных кампаний нет.</div>'
    live = live.sort_values(["status", "runway_days"], ascending=[True, True], na_position="last")
    rows = []
    for r in live.itertuples(index=False):
        runway = _num(r.runway_days)
        runway_html = _days(runway)
        if runway is not None and runway < CAMPAIGN_RUNWAY_WARN_DAYS:
            runway_html = _tag(f"{_days(runway)} дн.", "bad")
        rows.append(([
            f"{_esc(r.name)}<div class='muted'>{int(r.advert_id)} · {_esc(r.type_name)} · {_esc(r.bid_type_name)}</div>",
            _status_tag(r.status, r.status_name),
            _money(r.budget_rub), _money(r.avg_daily_spend), runway_html,
            _money(r.spend_rub), _int(r.orders_direct), _drr_cell(r.drr_direct), _pct1(r.drr),
        ], "zebra"))
    return _table(
        [("Кампания", "l", 32), ("Статус", "l", 8), ("Бюджет", "r", 9), ("Расход/день (7 дн.)", "r", 10),
         ("Хватит, дн.", "r", 8), ("Расход за период", "r", 10), ("Заказы*", "r", 7), ("ДРР*", "r", 8),
         ("ДРР всех заказов", "r", 8)],
        rows,
    ) + ('<div class="note">Бюджет — остаток на момент последней загрузки. «Хватит, дн.» — бюджет ÷ средний '
         f'расход за последние {RUNWAY_LOOKBACK_DAYS} дней. «Расход за период», «Заказы*», «ДРР*» — за выбранный '
         'в отчёте период. * По рекламируемым товарам. «ДРР всех заказов» — с учётом связанных заказов; '
         'рассчитан по статистике WB (WB отдаёт расход и заказы, ДРР считаем сами).</div>')


def _campaigns_tree_html(bundle: dict) -> str:
    df = bundle["campaigns"]
    cp = bundle["campaign_products"]
    top = df[df["spend_rub"] > 0].head(TOP_CAMPAIGNS_N) if not df.empty else df
    if top.empty:
        return '<div class="empty">Нет кампаний с расходом за период.</div>'

    rows = []
    for r in top.itertuples(index=False):
        rows.append(([
            f"▾ {_esc(r.name)}<div class='muted' style='font-weight:400'>{int(r.advert_id)} · {_esc(r.type_name)} · "
            f"{_esc(r.payment_name)}</div>",
            _status_tag(r.status, r.status_name), _quality_tag(r.quality),
            _int(r.views), _pct1(r.ctr), _money(r.spend_rub),
            _int(r.orders_direct), _money(r.revenue_direct), _money(_div(r.spend_rub, r.orders_direct)),
            _drr_cell(r.drr_direct),
        ], "parent"))
        children = cp[(cp["advert_id"] == r.advert_id) & ((cp["spend_rub"] > 0) | (cp["views"] > 0))] if not cp.empty else cp
        shown = children.head(TOP_CAMPAIGN_PRODUCTS_N)
        for c in shown.itertuples(index=False):
            rows.append(([
                f"↳ {_esc(c.title)} <span class='muted'>· {int(c.nm_id)}</span>",
                "", "", _int(c.views), _pct1(c.ctr), _money(c.spend_rub),
                _int(c.orders), _money(c.revenue_rub), _money(c.cpo), _drr_cell(c.drr),
            ], "child"))
        if len(children) > len(shown):
            rest = children.iloc[len(shown):]
            rows.append(([
                f"<span class='muted'>ещё {len(rest)} {_plural(len(rest), 'товар', 'товара', 'товаров')}</span>",
                "", "", _int(rest["views"].sum()), "", _money(rest["spend_rub"].sum()),
                _int(rest["orders"].sum()), _money(rest["revenue_rub"].sum()), "", "",
            ], "child"))
        if _num(r.revenue_assoc):
            rows.append(([
                f"<span class='muted'>+ связанные заказы других товаров: {_int(r.assoc_n)} арт.</span>",
                "", "", "", "", "", _int(r.orders_assoc),
                f"<span class='muted'>{_money(r.revenue_assoc)}</span>", "", "",
            ], "child"))

    return _table(
        [("Кампания / товар", "l", 30), ("Статус", "l", 8), ("Оценка", "l", 9), ("Показы", "r", 8),
         ("CTR", "r", 6), ("Расход", "r", 9), ("Заказы*", "r", 6), ("Сумма заказов*", "r", 10),
         ("CPO*", "r", 7), ("ДРР*", "r", 7)],
        rows,
    ) + ('<div class="note">* По рекламируемым товарам: заказы, их сумма по цене заказа, стоимость заказа и ДРР. '
         'Связанные заказы других товаров показаны отдельной строкой и в ДРР* не входят.</div>')


def _quality_html(bundle: dict, quality: str) -> str:
    df = bundle["campaigns"]
    subset = df[(df["quality"] == quality) & (df["spend_rub"] > 0)] if not df.empty else df
    if subset.empty:
        return '<div class="empty">Нет кампаний в этой группе.</div>'
    sort_col = "revenue_direct" if quality == QUALITY_GOOD else "spend_rub"
    top = subset.sort_values(sort_col, ascending=False).head(TOP_CAMPAIGNS_N)
    is_bad = quality == QUALITY_BAD
    headers = [("Кампания", "l", 30 if is_bad else 42), ("Статус", "l", 9), ("Расход", "r", 10),
               ("Заказы*", "r", 7), ("Сумма заказов*", "r", 11), ("ДРР*", "r", 8)]
    if is_bad:
        headers.append(("Причина", "l", 25))
    rows = []
    for r in top.itertuples(index=False):
        cells = [f"{_esc(r.name)}<div class='muted'>{int(r.advert_id)}</div>", _status_tag(r.status, r.status_name),
                 _money(r.spend_rub), _int(r.orders_direct), _money(r.revenue_direct), _drr_cell(r.drr_direct)]
        if is_bad:
            cells.append(f"<span class='wrap'>{_esc(r.reason)}</span>")
        rows.append((cells, "zebra"))
    total = subset["spend_rub"].sum()
    note = (f'<div class="note">Всего в группе: {len(subset)} {_plural(len(subset), "кампания", "кампании", "кампаний")}, '
            f'расход {_money(total)}. Показаны первые {len(top)}. * По рекламируемым товарам, '
            f'без связанных заказов.</div>')
    return _table(headers, rows) + note


def _stock_html(qty) -> str:
    q = _num(qty)
    if q is None:
        return '<span class="muted">—</span>'
    if q <= 0:
        return _tag("нет", "bad")
    if q < LOW_STOCK_QTY_THRESHOLD:
        return _tag(f"{_int(q)} шт.", "warn")
    return _int(q)


def _products_html(bundle: dict) -> str:
    df = bundle["products"]
    top = df[df["spend_rub"] > 0].head(TOP_PRODUCTS_N) if not df.empty else df
    if top.empty:
        return '<div class="empty">Нет данных по товарам.</div>'
    rows = [
        ([f"{_esc(r.title)}<div class='muted'>{int(r.nm_id)} · {_esc(r.brand)}</div>",
          _int(r.campaigns_n), _int(r.views), _money(r.spend_rub), _int(r.orders), _money(r.revenue_rub),
          _drr_cell(r.drr), _money(r.sales_rub), _pct1(r.tacos), _stock_html(r.stock_qty)], "zebra")
        for r in top.itertuples(index=False)
    ]
    tacos = bundle["tacos"]
    sales_to = _date(tacos.get("end")) if tacos.get("available") else "—"
    note = (
        '<div class="note">Все показатели — за выбранный период. «Заказы», «Сумма заказов» и «ДРР» — по рекламе '
        'этого товара (заказы после клика по его объявлению, по цене заказа). «Продажи» — фактические продажи '
        f'товара по всем каналам из отчёта реализации WB, за вычетом возвратов, по {sales_to}. «ДРР от продаж» — '
        'расход на рекламу товара ÷ его продажи: какая доля реальной выручки товара ушла на рекламу. '
        f'«Остаток» — WB + FBS на {_date(bundle.get("stocks_as_of"))}.</div>'
    )
    return _table(
        [("Товар", "l", 27), ("Кампаний", "r", 6), ("Показы", "r", 8), ("Расход", "r", 8), ("Заказы", "r", 6),
         ("Сумма заказов", "r", 9), ("ДРР", "r", 6), ("Продажи", "r", 9), ("ДРР от продаж", "r", 7),
         ("Остаток", "r", 8)],
        rows,
    ) + note


def _low_stock_html(bundle: dict) -> str:
    df = bundle.get("low_stock")
    if df is None or df.empty:
        return '<div class="empty">Товаров с остатком меньше {} шт. в активных кампаниях нет.</div>'.format(
            LOW_STOCK_QTY_THRESHOLD)
    rows = [
        ([f"{_esc(r.title)}<div class='muted'>{int(r.nm_id)} · {_esc(r.brand)}</div>", _stock_html(r.stock_qty),
          _money(r.spend_rub), _int(r.orders), f"<span class='wrap'>{_esc(r.campaigns)}</span>"], "zebra")
        for r in df.itertuples(index=False)
    ]
    return _table(
        [("Товар", "l", 32), ("Остаток", "r", 9), ("Расход за период", "r", 12), ("Заказы", "r", 8),
         ("В кампаниях", "l", 39)],
        rows,
    )


def _reconciliation_html(bundle: dict) -> str:
    rec = bundle["reconciliation"]
    if not rec["available"]:
        return ('<div class="empty">Данных о списаниях за период нет. Они появятся после загрузки '
                'истории списаний.</div>')

    intro = (
        '<div class="summary">Зачем эта страница: проверить, что расход в отчёте совпадает с деньгами, которые WB '
        'реально списал. <b>Начислено</b> — расход из статистики показов и кликов (то, что считает отчёт). '
        '<b>Списано</b> — суммы из «Истории затрат» в кабинете WB Продвижение: WB списывает их документами, '
        'обычно в течение суток после показов. Поэтому по отдельным дням и неделям цифры могут немного '
        'расходиться, а за месяц должны почти совпадать.</div>'
    )

    diff_pct = rec["diff_pct"]
    if diff_pct is None:
        verdict = "Сравнить не с чем."
    elif abs(diff_pct) < RECONCILIATION_TOLERANCE_PCT:
        verdict = (f"Расхождение {_pct1(abs(diff_pct))} — в пределах нормы (до "
                   f"{_spaced(RECONCILIATION_TOLERANCE_PCT)} %). Расход в отчёте подтверждается списаниями WB.")
    else:
        verdict = (f"Расхождение {_pct1(abs(diff_pct))} — больше обычного. Чаще всего это значит, что WB ещё не "
                   f"выставил документы за последние дни периода; стоит сверить после следующей загрузки.")

    tiles = [
        _kpi("Начислено по статистике", _money(rec["stats_spend"]), "расход по показам и кликам", True),
        _kpi("Списано WB", _money(rec["charged"]), "история затрат в кабинете", True),
        _kpi("Разница", _money(rec["diff"]), _signed_pct(diff_pct) + " к списанному"),
        _kpi("Пополнения счёта", _money(bundle["payments"]["amount_rub"].sum() if not bundle["payments"].empty else 0),
             f"{len(bundle['payments'])} операций за период"),
    ]

    period_df = rec.get("by_period")
    period_html = ""
    if period_df is not None and not period_df.empty:
        title = "По неделям" if rec.get("by_period_freq") == "week" else "По месяцам"
        rows = [
            ([_esc(r.label), _money(r.stats_spend), _money(r.charged), _money(r.diff), _signed_pct(r.diff_pct)], "zebra")
            for r in period_df.itertuples(index=False)
        ]
        period_html = f"<h3>{title}</h3>" + _table(
            [("Период", "l", 28), ("Начислено", "r", 18), ("Списано WB", "r", 18), ("Разница", "r", 18),
             ("Разница, %", "r", 18)],
            rows,
        )

    by_source = rec["by_source"]
    source_html = ""
    if not by_source.empty:
        total = by_source["amount_rub"].sum()
        source_html = "<h3>Из каких средств списано</h3>" + _table(
            [("Источник", "l", 50), ("Сумма", "r", 25), ("Доля", "r", 25)],
            [([_esc(r.payment_source), _money(r.amount_rub), _pct1(r.amount_rub / total * 100 if total else None)], "zebra")
             for r in by_source.itertuples(index=False)],
        ) + ('<div class="note">«Баланс» — Единый счёт WB Продвижение, «Промобонусы» — бонусы WB. '
             'Расхождения по отдельным кампаниям — в Excel-детализации, лист «Сверка».</div>')

    return (intro + f'<div class="kpis">{"".join(tiles)}</div>' + f'<div class="summary">{_esc(verdict)}</div>'
            + period_html + source_html)


def _methodology_html() -> str:
    parts = []
    for title, items in _methodology():
        parts.append(f"<h3>{_esc(title)}</h3>")
        parts.append(_table([("Параметр", "l", 22), ("Описание", "l", 78)],
                            [([_esc(k), f"<span class='wrap'>{_esc(v)}</span>"], "") for k, v in items]))
    return '<div class="method">' + "".join(parts) + "</div>"


def _safe_html(builder, *args, **kwargs) -> str:
    try:
        return builder(*args, **kwargs)
    except Exception as exc:
        logger.exception("Раздел PDF не собран: %s", getattr(builder, "__name__", builder))
        return f'<div class="error">Раздел не сформирован: {_esc(type(exc).__name__)}.</div>'


def build_ad_campaigns_html(bundle: dict) -> str:
    period = _period_label(bundle["start_date"], bundle["end_date"])
    prev = _period_label(bundle["prev_start"], bundle["prev_end"])
    fresh = bundle["freshness"]
    stats_to = _date(fresh.get("stats_max_date"))
    generated = bundle["generated_at"].strftime("%d.%m.%Y %H:%M")
    campaigns = bundle["campaigns"]
    active_n = int((campaigns["spend_rub"] > 0).sum()) if not campaigns.empty else 0
    stocks_note = (f"Остатки на {_date(bundle['stocks_as_of'])}." if bundle.get("stocks_as_of") else "Остатки недоступны.")

    by_type = bundle["by_type"]
    type_chart = (
        _hbar_html(by_type, "type_name", "По типам кампаний")
        if by_type is not None and (by_type["spend_rub"] > 0).sum() > 1 else ""
    )

    return f"""<!doctype html>
<html lang="ru"><head><meta charset="utf-8"><title>Анализ рекламных кампаний WB</title>
<style>{_PDF_CSS}</style></head>
<body>

<section class="first">
  <div class="masthead">
    <h1>Анализ рекламных кампаний Wildberries</h1>
    <div class="meta">
      <div>Период<b>{period}</b></div>
      <div>Сравнение с<b>{prev}</b></div>
      <div>Статистика по<b>{stats_to}</b></div>
      <div>Кампаний с расходом<b>{active_n}</b></div>
      <div>Сформировано<b>{generated}</b></div>
    </div>
  </div>
  <div class="summary">{_esc(_safe_html(_narrative, bundle))}</div>
  <h3>Ключевые показатели</h3>
  {_safe_html(_kpis_html, bundle)}
  <h3>Бюджет и запас средств</h3>
  {_safe_html(_budget_html, bundle)}
  <div class="cols">
    <div><h3>Воронка</h3>{_safe_html(_funnel_html, bundle["totals"])}</div>
    <div style="flex:.6"><h3>Шкала ДРР</h3>{_safe_html(_drr_scale_html)}
      <div class="note">Внутренний ориентир; маржа до рекламы ~{_pct1(PRE_AD_MARGIN_REFERENCE_PCT)}.
      Применяется к ДРР по рекламируемым товарам.</div></div>
  </div>
  <h3>Три показателя ДРР — в чём разница</h3>
  {_safe_html(_drr_explain_html, bundle)}
</section>

<section>
  <h2>Выводы и рекомендации</h2>
  <div class="lead">Каждый вывод основан на показателе, приведённом в тексте; правила — в разделе «Методология».</div>
  {_safe_html(_recommendations_html, bundle)}
  <h3>Темп расходов</h3>
  {_safe_html(_ptd_html, bundle)}
</section>

<section>
  <h2>Динамика</h2>
  <div class="lead">Расход и ДРР во времени; пунктир — порог ДРР {_pct1(DRR_HIGH_THRESHOLD)}.</div>
  {_safe_html(_trend_charts_html, bundle)}
  <h3>Расход по оценке кампаний (по рекламируемым товарам)</h3>
  {_safe_html(_quality_block_html, bundle)}
</section>

<section>
  <h2>Структура расходов</h2>
  <div class="lead">Типы кампаний, модели оплаты, типы ставок и площадки показа.</div>
  {type_chart}
  {_safe_html(_group_table_html, bundle["by_type"], "type_name", "Тип кампании")}
  <div class="cols">
    <div><h3>Модель оплаты</h3>{_safe_html(_group_table_html, bundle["by_payment"], "payment_name", "Оплата", True)}</div>
    <div><h3>Тип ставки</h3>{_safe_html(_group_table_html, bundle["by_bid"], "bid_type_name", "Ставка", True)}</div>
  </div>
  <h3>Площадки</h3>
  {_safe_html(_platforms_html, bundle)}
  <h3>Бренды</h3>
  {_safe_html(_brands_html, bundle)}
</section>

<section class="wide">
  <h2>Бюджеты активных кампаний</h2>
  <div class="lead">Остаток бюджета на момент последней загрузки и прогноз по среднему расходу за {RUNWAY_LOOKBACK_DAYS} дней.</div>
  {_safe_html(_campaign_budgets_html, bundle)}
</section>

<section class="wide">
  <h2>Кампании и товары</h2>
  <div class="lead">Топ-{TOP_CAMPAIGNS_N} кампаний по расходу, под каждой — товары с наибольшим расходом.
  Полный состав — в Excel-детализации (строки раскрываются кнопкой «+»).</div>
  {_safe_html(_campaigns_tree_html, bundle)}
</section>

<section class="wide">
  <h2>Эффективные кампании</h2>
  <div class="lead">Окупаются в пределах порога ДРР — кандидаты на масштабирование.</div>
  {_safe_html(_quality_html, bundle, QUALITY_GOOD)}
  <h2 style="margin-top:14px">Неэффективные кампании</h2>
  <div class="lead">Заметный расход без окупаемости — кандидаты на пересмотр ставок или отключение.</div>
  {_safe_html(_quality_html, bundle, QUALITY_BAD)}
</section>

<section class="wide">
  <h2>Товары</h2>
  <div class="lead">Топ-{TOP_PRODUCTS_N} товаров по расходу на рекламу. {stocks_note}</div>
  {_safe_html(_products_html, bundle)}
  <h3>Реклама на товары с низким остатком</h3>
  <div class="note" style="margin-top:0">Товары в активных и приостановленных кампаниях, у которых осталось меньше
  {LOW_STOCK_QTY_THRESHOLD} шт. Реклама на них может закончиться отказами и пустыми показами.</div>
  {_safe_html(_low_stock_html, bundle)}
</section>

<section>
  <h2>Сверка: начислено и списано</h2>
  <div class="lead">Проверка, что расход в отчёте совпадает с реальными списаниями WB.</div>
  {_safe_html(_reconciliation_html, bundle)}
</section>

<section>
  <h2>Методология</h2>
  <div class="lead">Источники, формулы и правила, по которым построен отчёт.</div>
  {_methodology_html()}
</section>

</body></html>
"""


def build_ad_campaigns_pdf(bundle: dict) -> bytes:
    try:
        from weasyprint import HTML
    except ImportError as exc:
        raise RuntimeError("Для PDF требуется WeasyPrint: pip install weasyprint") from exc
    buffer = BytesIO()
    HTML(string=build_ad_campaigns_html(bundle)).write_pdf(buffer)
    return buffer.getvalue()


def build_ad_campaigns_pdf_bytes(start_date: str, end_date: str) -> bytes:
    return build_ad_campaigns_pdf(_fetch_report_bundle(start_date, end_date))


# ================================================================ Excel: общие элементы
_XL_FMT = {
    "text": None,
    "id": "0",
    "int": style.FMT_QTY,
    "money": style.FMT_MONEY,
    "money2": style.FMT_MONEY_DEC,
    "pct": style.FMT_PCT,
    "num1": '#,##0.0;(#,##0.0);"—"',
    "date": style.FMT_DATE,
    "datetime": style.FMT_DATETIME,
}

_XL_GROUP_COLOR = {"good": "0B7A0B", "warn": "9A6100", "bad": "B42318"}
_XL_QUALITY_COLOR = {QUALITY_GOOD: "0B7A0B", QUALITY_BAD: "B42318", QUALITY_LOW: style.MUTED}
_FILL_PARENT = PatternFill("solid", fgColor=style.SURFACE_3)
_FILL_GROUP = PatternFill("solid", fgColor=style.SURFACE_4)


def _xl_value(v, fmt: str):
    if _isna(v):
        return None
    if isinstance(v, str) and fmt != "text":
        return v
    if fmt in ("date", "datetime"):
        ts = pd.Timestamp(v)
        if ts.tzinfo is not None:
            ts = ts.tz_convert("Europe/Moscow").tz_localize(None)
        return ts.date() if fmt == "date" else ts.to_pydatetime()
    if fmt == "text":
        return str(v)
    try:
        f = float(v)
    except (TypeError, ValueError):
        return str(v)
    if fmt in ("int", "id"):
        return int(round(f))
    return round(f, 2)


def _xl_params(bundle: dict) -> str:
    return (f"Период: {_period_label(bundle['start_date'], bundle['end_date'])} · "
            f"статистика по {_date(bundle['freshness'].get('stats_max_date'))} · "
            f"сформировано {bundle['generated_at']:%d.%m.%Y %H:%M}")


def _xl_sheet(wb, name: str, title: str, subtitle: str, params: str, width: int, landscape: bool = True):
    ws = wb.create_sheet(name)
    row = style.write_sheet_header(ws, title, subtitle, params, width, landscape=landscape)
    ws.sheet_properties.outlinePr = Outline(summaryBelow=False, summaryRight=False)
    return ws, row


def _xl_block_title(ws, row: int, text: str, width: int) -> int:
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=width)
    c = ws.cell(row=row, column=1, value=text)
    c.font = Font(name=style.FONT, size=11, bold=True, color=style.NAVY_3)
    c.alignment = style.ALIGN_LEFT
    ws.row_dimensions[row].height = 20
    return row + 1


def _xl_table(ws, row: int, cols: list[tuple], rows: list[dict], *, total: dict | None = None,
              freeze_col: int | None = None, autofilter: bool = True, collapsed: bool = True,
              set_widths: bool = True) -> int:
    """cols: (заголовок, ключ, ширина, формат). rows: {"v": {...}, "level": 0|1|2, "kind": ...}."""
    header_row = row
    style.write_table_header(ws, header_row, 1, [c[0] for c in cols])
    width = len(cols)
    numeric = {i for i, c in enumerate(cols, start=1) if c[3] not in ("text",)}
    formats = {i: _XL_FMT[c[3]] for i, c in enumerate(cols, start=1) if _XL_FMT.get(c[3])}
    keys = [c[1] for c in cols]

    r = header_row + 1
    first = r
    has_outline = any(x.get("level", 0) for x in rows)

    for item in rows:
        values = item["v"]
        level = item.get("level", 0)
        kind = item.get("kind", "row")

        for col, (key, (_h, _k, _w, fmt)) in enumerate(zip(keys, cols), start=1):
            ws.cell(row=r, column=col, value=_xl_value(values.get(key), fmt))
        style.style_data_row(ws, r, 1, width, numeric_cols=numeric, formats=formats)

        if kind in ("parent", "group"):
            fill = _FILL_GROUP if kind == "group" else _FILL_PARENT
            for col in range(1, width + 1):
                cell = ws.cell(row=r, column=col)
                cell.fill = fill
                cell.font = Font(name=style.FONT, size=10, bold=True, color=style.TEXT)
        elif level > 0:
            for col in range(1, width + 1):
                ws.cell(row=r, column=col).font = Font(name=style.FONT, size=9, color=style.TEXT_2)

        for col, key in enumerate(keys, start=1):
            cell = ws.cell(row=r, column=col)
            if key in ("name", "title", "label") and level > 0:
                cell.alignment = Alignment(horizontal="left", vertical="center", indent=2 * level)
            basis = values.get("rating_basis", values.get("drr")) if key == "drr_rating" else values.get(key)
            if key in ("drr", "drr_direct", "drr_rating") and not _isna(basis):
                color = _XL_GROUP_COLOR.get(_drr_group(basis))
                if color:
                    cell.font = Font(name=style.FONT, size=cell.font.size, bold=True, color=color)
            if key == "quality" and values.get("quality") in _XL_QUALITY_COLOR:
                cell.font = Font(name=style.FONT, size=cell.font.size, bold=True,
                                 color=_XL_QUALITY_COLOR[values["quality"]])

        if level > 0:
            ws.row_dimensions[r].outline_level = level
            ws.row_dimensions[r].hidden = collapsed
        r += 1

    last = r - 1
    if not rows:
        ws.cell(row=r, column=1, value="Нет данных за выбранный период")
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=width)
        ws.cell(row=r, column=1).font = style.FONT_FOOTNOTE
        last = r
        r += 1

    if total:
        for col, (key, (_h, _k, _w, fmt)) in enumerate(zip(keys, cols), start=1):
            cell = ws.cell(row=r, column=col, value=_xl_value(total.get(key), fmt))
            if col in formats:
                cell.number_format = formats[col]
            cell.alignment = style.ALIGN_RIGHT if col in numeric else style.ALIGN_LEFT
        style.style_total_row(ws, r, 1, width)
        last = r
        r += 1

    if not has_outline and rows:
        style.apply_zebra(ws, first, first + len(rows) - 1, 1, width)
    style.apply_column_dividers(ws, header_row, last, 1, width)

    if set_widths:
        from openpyxl.utils import get_column_letter
        for i, c in enumerate(cols, start=1):
            ws.column_dimensions[get_column_letter(i)].width = c[2]
    if freeze_col:
        style.freeze_table(ws, header_row, first_col=freeze_col)
    if autofilter and rows:
        style.enable_autofilter(ws, header_row, 1, width, first + len(rows) - 1)
    return r


def _row_values(r, extra: dict | None = None) -> dict:
    d = r._asdict() if hasattr(r, "_asdict") else dict(r)
    if extra:
        d.update(extra)
    return d


_XL_METRIC_COLS = [
    ("Показы", "views", 11, "int"),
    ("Клики", "clicks", 9, "int"),
    ("CTR, %", "ctr", 8, "pct"),
    ("CPC, ₽", "cpc", 9, "money2"),
    ("CPM, ₽", "cpm", 9, "money2"),
    ("Корзины", "atbs", 9, "int"),
    ("Заказы", "orders", 9, "int"),
    ("Заказано, шт.", "shks", 10, "int"),
    ("CR, %", "cr", 8, "pct"),
    ("CPO, ₽", "cpo", 10, "money"),
    ("Расход, ₽", "spend_rub", 13, "money"),
    ("Сумма заказов, ₽", "revenue_rub", 14, "money"),
    ("Отмены", "canceled", 9, "int"),
    ("ДРР, %", "drr", 9, "pct"),
    ("Оценка ДРР", "drr_rating", 11, "text"),
]


def _totals_row(t: dict, label: str = "ИТОГО", key: str = "name") -> dict:
    row = dict(t)
    row[key] = label
    row["drr_rating"] = _drr_rating(t.get("drr"))
    return row


# ================================================================ Excel: листы детализации
def _xl_summary_sheet(wb, bundle, params):
    ws, row = _xl_sheet(wb, "Сводка", "Ключевые показатели",
                        "Текущий период против предыдущего такой же длины", params, 6, landscape=False)
    t, p = bundle["totals"], bundle["prev_totals"] or {}
    metrics = [
        ("Расход на рекламу, ₽", "spend_rub", "money", False),
        ("Сумма заказов от рекламы, ₽", "revenue_rub", "money", False),
        ("ДРР с учётом связанных заказов, %", "drr", "pct", True),
        ("Заказы от рекламы", "orders", "int", False),
        ("Заказано, шт.", "shks", "int", False),
        ("Показы", "views", "int", False),
        ("Клики", "clicks", "int", False),
        ("CTR, %", "ctr", "pct", True),
        ("CPC, ₽", "cpc", "money2", False),
        ("CPM, ₽", "cpm", "money2", False),
        ("Корзины", "atbs", "int", False),
        ("Клик → корзина, %", "cart_rate", "pct", True),
        ("CR, клик → заказ, %", "cr", "pct", True),
        ("CPO, ₽", "cpo", "money", False),
        ("Отмены", "canceled", "int", False),
        ("Сумма заказов рекламируемых товаров, ₽", "revenue_direct", "money", False),
        ("Связанные заказы других товаров, ₽", "revenue_assoc", "money", False),
        ("ДРР по рекламируемым товарам, %", "drr_direct", "pct", True),
    ]
    rows = []
    for label, key, fmt, is_pct in metrics:
        cur, prev = t.get(key), p.get(key)
        diff = (_num(cur) - _num(prev)) if _num(cur) is not None and _num(prev) is not None else None
        rows.append({"v": {
            "label": label, "cur": cur, "prev": prev,
            "diff": diff, "diff_pct": None if is_pct else _change_pct(cur, prev),
        }, "fmt": fmt})

    cols = [("Показатель", "label", 34, "text"), ("Текущий период", "cur", 18, "num1"),
            ("Предыдущий период", "prev", 18, "num1"), ("Изменение", "diff", 16, "num1"),
            ("Изменение, %", "diff_pct", 14, "pct")]
    end = _xl_table(ws, row, cols, rows, autofilter=False)
    for i, item in enumerate(rows):
        fmt = _XL_FMT[item["fmt"]]
        for col in (2, 3, 4):
            ws.cell(row=row + 1 + i, column=col).number_format = fmt if item["fmt"] != "pct" else '#,##0.0" %";-#,##0.0" %";"—"'
        if item["fmt"] == "pct":
            ws.cell(row=row + 1 + i, column=4).number_format = '+#,##0.0" п.п.";-#,##0.0" п.п.";"—"'

    b = bundle["budget"]
    tacos = bundle["tacos"]
    end = _xl_block_title(ws, end + 1, "Бюджет и продажи", 5)
    extra = [
        {"v": {"label": "Доступно на счёте (net), ₽", "cur": b["net"]}},
        {"v": {"label": "Бонусы, ₽", "cur": b["bonus"]}},
        {"v": {"label": "Бюджеты активных и приостановленных кампаний, ₽", "cur": b["budgets_total"] if b["budgets_known"] else None}},
        {"v": {"label": f"Средний расход в день за {RUNWAY_LOOKBACK_DAYS} дн., ₽", "cur": b["avg_daily_spend"]}},
        {"v": {"label": "Хватит средств, дней", "cur": b["runway_days"]}},
        {"v": {"label": "Продажи товаров (отчёт реализации), ₽", "cur": tacos.get("sales")}},
        {"v": {"label": "ДРР от продаж, %", "cur": tacos.get("value")}},
    ]
    _xl_table(ws, end, [("Показатель", "label", 34, "text"), ("Значение", "cur", 18, "num1")],
              extra, autofilter=False, set_widths=False)
    style.freeze_table(ws, row, first_col=2)


def _xl_campaigns_sheet(wb, bundle, params):
    cols = [
        ("ID / артикул", "id", 13, "id"),
        ("Кампания / товар", "name", 44, "text"),
        ("Строка", "level_name", 11, "text"),
        ("Тип", "type_name", 18, "text"),
        ("Оплата", "payment_name", 17, "text"),
        ("Ставка", "bid_type_name", 15, "text"),
        ("Статус", "status_name", 12, "text"),
        ("Оценка", "quality", 14, "text"),
        ("Бюджет, ₽", "budget_rub", 12, "money"),
        ("Расход/день (7 дн.), ₽", "avg_daily_spend", 13, "money"),
        ("Хватит, дн.", "runway_days", 10, "num1"),
        *_XL_METRIC_COLS[:-2],
        ("ДРР с учётом связанных, %", "drr", 12, "pct"),
        ("Заказы рекл. товаров", "orders_direct", 11, "int"),
        ("Сумма заказов рекл. товаров, ₽", "revenue_direct", 15, "money"),
        ("ДРР рекл. товаров, %", "drr_direct", 11, "pct"),
        ("Оценка ДРР", "drr_rating", 11, "text"),
        ("Связанные заказы, ₽", "revenue_assoc", 13, "money"),
        ("Списано, ₽", "charged_rub", 12, "money"),
        ("Ставка поиск, ₽", "bid_search_rub", 11, "money2"),
        ("Ставка реком., ₽", "bid_recommendations_rub", 11, "money2"),
        ("Ср. позиция", "avg_position", 10, "num1"),
        ("Остаток, шт.", "stock_qty", 10, "int"),
        ("Первый день", "first_date", 12, "date"),
        ("Последний день", "last_date", 12, "date"),
        ("Причина оценки", "reason", 50, "text"),
    ]
    ws, row = _xl_sheet(
        wb, "Кампании", "Кампании и товары",
        "Строка кампании — итог; рекламируемые товары раскрываются кнопкой «+». Связанные заказы других "
        "товаров — отдельной строкой, в ДРР рекламируемых товаров не входят", params, len(cols),
    )
    campaigns = bundle["campaigns"]
    cp = bundle["campaign_products"]
    rows = []
    for r in campaigns.itertuples(index=False):
        rows.append({"v": _row_values(r, {
            "id": r.advert_id, "level_name": "Кампания",
            "drr_rating": _drr_rating(r.drr_direct), "rating_basis": r.drr_direct,
        }), "kind": "parent"})
        children = cp[cp["advert_id"] == r.advert_id] if not cp.empty else cp
        direct = children[children["direct"]] if not children.empty else children
        for c in direct.itertuples(index=False):
            v = _row_values(c, {
                "id": c.nm_id, "name": f"{c.title} · {c.brand}", "level_name": "Товар",
                "status_name": "в составе" if getattr(c, "in_campaign", False) else "",
                "orders_direct": c.orders, "revenue_direct": c.revenue_rub, "drr_direct": c.drr,
            })
            rows.append({"v": v, "level": 1})
        assoc = children[~children["direct"]] if not children.empty else children
        if not assoc.empty and (assoc["orders"].sum() or assoc["revenue_rub"].sum()):
            rows.append({"v": {
                "name": f"Связанные заказы других товаров ({assoc['nm_id'].nunique()} арт.)",
                "level_name": "Связанные",
                "orders": assoc["orders"].sum(), "shks": assoc["shks"].sum(),
                "revenue_rub": assoc["revenue_rub"].sum(), "canceled": assoc["canceled"].sum(),
                "revenue_assoc": assoc["revenue_rub"].sum(),
            }, "level": 1})
    t = bundle["totals"]
    total = _totals_row(t)
    total.update({"orders_direct": t.get("orders_direct"), "revenue_direct": t.get("revenue_direct"),
                  "drr_direct": t.get("drr_direct"), "revenue_assoc": t.get("revenue_assoc"),
                  "drr_rating": _drr_rating(t.get("drr_direct")), "rating_basis": t.get("drr_direct")})
    total["charged_rub"] = bundle["reconciliation"]["charged"] if bundle["reconciliation"]["available"] else None
    _xl_table(ws, row, cols, rows, total=total, freeze_col=3)


def _xl_products_sheet(wb, bundle, params):
    cols = [
        ("Артикул / ID", "id", 13, "id"),
        ("Товар / кампания", "name", 46, "text"),
        ("Строка", "level_name", 11, "text"),
        ("Бренд", "brand", 16, "text"),
        ("Категория", "category", 20, "text"),
        ("Остаток, шт.", "stock_qty", 10, "int"),
        ("Кампаний", "campaigns_n", 9, "int"),
        *_XL_METRIC_COLS,
        ("Продажи, ₽", "sales_rub", 13, "money"),
        ("Продажи, шт.", "sales_qty", 10, "int"),
        ("ДРР от продаж, %", "tacos", 11, "pct"),
    ]
    ws, row = _xl_sheet(
        wb, "Товары", "Товары и кампании",
        "Строка товара — итог по всем кампаниям; кампании раскрываются кнопкой «+»", params, len(cols),
    )
    products = bundle["products"]
    cp = bundle["campaign_products"]
    names = bundle["campaigns"].set_index("advert_id")["name"].to_dict() if not bundle["campaigns"].empty else {}
    rows = []
    for r in products.itertuples(index=False):
        rows.append({"v": _row_values(r, {"id": r.nm_id, "name": r.title, "level_name": "Товар"}), "kind": "parent"})
        children = cp[(cp["nm_id"] == r.nm_id) & ((cp["spend_rub"] > 0) | (cp["views"] > 0))]
        for c in children.sort_values("spend_rub", ascending=False).itertuples(index=False):
            v = _row_values(c, {"id": c.advert_id, "name": names.get(c.advert_id, f"Кампания {int(c.advert_id)}"),
                                "level_name": "Кампания", "brand": None, "category": None, "stock_qty": None})
            rows.append({"v": v, "level": 1})
    total = _totals_row(_totals(products), key="name") if not products.empty else None
    _xl_table(ws, row, cols, rows, total=total, freeze_col=3)


def _xl_budgets_sheet(wb, bundle, params):
    cols = [
        ("ID", "advert_id", 12, "id"), ("Кампания", "name", 44, "text"), ("Тип", "type_name", 18, "text"),
        ("Ставка", "bid_type_name", 15, "text"), ("Статус", "status_name", 12, "text"),
        ("Бюджет, ₽", "budget_rub", 13, "money"), ("На дату", "budget_as_of", 16, "datetime"),
        ("Расход за 7 дн., ₽", "recent_spend", 14, "money"), ("Расход/день, ₽", "avg_daily_spend", 13, "money"),
        ("Хватит, дн.", "runway_days", 11, "num1"), ("Расход за период, ₽", "spend_rub", 15, "money"),
        ("Заказы рекл. товаров", "orders_direct", 11, "int"), ("ДРР рекл. товаров, %", "drr_direct", 11, "pct"),
        ("ДРР с учётом связанных, %", "drr", 12, "pct"),
    ]
    ws, row = _xl_sheet(wb, "Бюджеты", "Бюджеты активных кампаний",
                        f"Остаток бюджета и прогноз по среднему расходу за {RUNWAY_LOOKBACK_DAYS} дней",
                        params, len(cols))
    df = bundle["campaigns"]
    live = df[df["status"].isin([STATUS_ACTIVE, STATUS_PAUSED])].sort_values(
        ["status", "runway_days"], na_position="last") if not df.empty else df
    rows = [{"v": _row_values(r)} for r in live.itertuples(index=False)]
    total = {"name": "ИТОГО", "budget_rub": live["budget_rub"].sum() if not live.empty else None,
             "recent_spend": live["recent_spend"].sum() if not live.empty else None,
             "avg_daily_spend": live["avg_daily_spend"].sum() if not live.empty else None,
             "spend_rub": live["spend_rub"].sum() if not live.empty else None,
             "orders_direct": live["orders_direct"].sum() if not live.empty else None}
    total["runway_days"] = _div(total["budget_rub"], total["avg_daily_spend"])
    end = _xl_table(ws, row, cols, rows, total=total, freeze_col=3)

    b = bundle["budget"]
    end = _xl_block_title(ws, end + 1, "Рекламный кабинет", len(cols))
    ws.cell(row=end, column=2, value="Доступно на счёте (net)")
    ws.cell(row=end, column=6, value=_xl_value(b["net"], "money")).number_format = style.FMT_MONEY
    ws.cell(row=end + 1, column=2, value="Хватит средств (net + бюджеты), дней")
    ws.cell(row=end + 1, column=10, value=_xl_value(b["runway_days"], "num1")).number_format = _XL_FMT["num1"]


def _xl_time_sheet(wb, name, title, df, params, label_header):
    cols = [(label_header, "label", 14, "text"), *_XL_METRIC_COLS]
    ws, row = _xl_sheet(wb, name, title, "Все кампании, статистика WB", params, len(cols))
    rows = [{"v": _row_values(r, {"drr_rating": _drr_rating(r.drr)})} for r in df.itertuples(index=False)]
    _xl_table(ws, row, cols, rows, total=_totals_row(_totals(df), key="label") if not df.empty else None,
              freeze_col=2)


def _xl_structure_sheet(wb, bundle, params):
    width = 10
    ws, row = _xl_sheet(wb, "Структура", "Структура расходов",
                        "Типы кампаний, модели оплаты, типы ставок, площадки, бренды", params, width)
    def group_cols(header, key):
        return [
            (header, key, 30, "text"), ("Кампаний", "campaigns_n", 10, "int"), ("Доля, %", "share", 9, "pct"),
            ("Показы", "views", 12, "int"), ("CTR, %", "ctr", 9, "pct"), ("Расход, ₽", "spend_rub", 14, "money"),
            ("Заказы рекл. товаров", "orders_direct", 10, "int"), ("CPO, ₽", "cpo_direct", 11, "money"),
            ("Сумма заказов рекл. товаров, ₽", "revenue_direct", 15, "money"),
            ("ДРР рекл. товаров, %", "drr_direct", 9, "pct"),
        ]

    first = True
    for title, df, key in (
        ("Типы кампаний", bundle["by_type"], "type_name"),
        ("Модель оплаты", bundle["by_payment"], "payment_name"),
        ("Тип ставки", bundle["by_bid"], "bid_type_name"),
    ):
        row = _xl_block_title(ws, row if first else row + 1, title, width)
        row = _xl_table(ws, row, group_cols(title, key), [{"v": _row_values(r)} for r in df.itertuples(index=False)],
                        autofilter=False, set_widths=first)
        first = False

    platforms = bundle["platforms"]
    row = _xl_block_title(ws, row + 1, "Площадки", width)
    pcols = [("Площадка", "platform", 30, "text"), ("Клики", "clicks", 10, "int"), ("Доля, %", "share", 9, "pct"),
             ("Показы", "views", 12, "int"), ("CTR, %", "ctr", 9, "pct"), ("Расход, ₽", "spend_rub", 14, "money"),
             ("Заказы", "orders", 10, "int"), ("CPO, ₽", "cpo", 11, "money"),
             ("Сумма заказов, ₽", "revenue_rub", 15, "money"), ("ДРР, %", "drr", 9, "pct")]
    row = _xl_table(ws, row, pcols, [{"v": _row_values(r)} for r in platforms.itertuples(index=False)]
                    if platforms is not None and not platforms.empty else [], autofilter=False, set_widths=False)

    brands = bundle["brands"]
    total = brands["spend_rub"].sum() if not brands.empty else 0
    row = _xl_block_title(ws, row + 1, "Бренды", width)
    bcols = [("Бренд", "brand", 30, "text"), ("Клики", "clicks", 10, "int"), ("Доля, %", "share", 9, "pct"),
             ("Показы", "views", 12, "int"), ("CTR, %", "ctr", 9, "pct"), ("Расход, ₽", "spend_rub", 14, "money"),
             ("Заказы", "orders", 10, "int"), ("CPO, ₽", "cpo", 11, "money"),
             ("Сумма заказов, ₽", "revenue_rub", 15, "money"), ("ДРР, %", "drr", 9, "pct")]
    _xl_table(ws, row, bcols,
              [{"v": _row_values(r, {"share": r.spend_rub / total * 100 if total else None})}
               for r in brands.itertuples(index=False)],
              autofilter=False, set_widths=False)
    style.freeze_table(ws, 6, first_col=2)


def _xl_reconciliation_sheet(wb, bundle, params):
    rec = bundle["reconciliation"]
    width = 8
    ws, row = _xl_sheet(wb, "Сверка", "Сверка: начислено и списано",
                        "Начислено — расход по статистике показов и кликов; списано — «История затрат» "
                        "WB Продвижение. По дням возможна разница из-за задержки списаний", params, width)
    cols = [("ID", "advert_id", 12, "id"), ("Кампания", "name", 44, "text"), ("Статус", "status_name", 12, "text"),
            ("Статистика, ₽", "spend_rub", 15, "money"), ("Списано, ₽", "charged_rub", 15, "money"),
            ("Разница, ₽", "diff_rub", 14, "money"), ("Разница, %", "diff_pct", 12, "pct"),
            ("", "blank", 16, "text")]
    period_df = rec.get("by_period")
    if period_df is not None and not period_df.empty:
        pcols = [("Период", "label", 12, "text"), ("", "blank0", 44, "text"), ("", "blank1", 12, "text"),
                 ("Начислено, ₽", "stats_spend", 15, "money"), ("Списано WB, ₽", "charged", 15, "money"),
                 ("Разница, ₽", "diff", 14, "money"), ("Разница, %", "diff_pct", 12, "pct"), ("", "blank2", 16, "text")]
        row = _xl_block_title(ws, row, "По периодам" , width)
        row = _xl_table(ws, row, pcols, [{"v": _row_values(r)} for r in period_df.itertuples(index=False)],
                        autofilter=False, set_widths=False)
        row = _xl_block_title(ws, row + 1, "По кампаниям", width)

    rows = []
    if not rec["rows"].empty:
        for r in rec["rows"].itertuples(index=False):
            rows.append({"v": _row_values(r, {"diff_pct": _div(r.diff_rub, r.charged_rub, 100)})})
    total = {"name": "ИТОГО", "spend_rub": rec["stats_spend"], "charged_rub": rec["charged"],
             "diff_rub": rec["diff"], "diff_pct": rec["diff_pct"]}
    row = _xl_table(ws, row, cols, rows, total=total)

    expenses = bundle["expenses"]
    row = _xl_block_title(ws, row + 1, "Списания по документам", width)
    ecols = [("Дата", "date", 12, "date"), ("Кампания", "camp_name", 44, "text"),
             ("Источник", "payment_source", 12, "text"), ("Сумма, ₽", "amount_rub", 15, "money"),
             ("Документ", "upd_num", 15, "id"), ("ID кампании", "advert_id", 14, "id"),
             ("Тип", "advert_type_name", 12, "text"), ("Время списания", "upd_time", 16, "datetime")]
    row = _xl_table(ws, row, ecols, [{"v": _row_values(r)} for r in expenses.itertuples(index=False)],
                    autofilter=False, set_widths=False,
                    total={"date": "ИТОГО", "amount_rub": expenses["amount_rub"].sum() if not expenses.empty else 0})

    payments = bundle["payments"]
    row = _xl_block_title(ws, row + 1, "Пополнения рекламного счёта", width)
    pcols = [("Дата", "date", 12, "date"), ("Способ", "payment_type_name", 44, "text"),
             ("Статус", "status_name", 12, "text"), ("Сумма, ₽", "amount_rub", 15, "money"),
             ("ID платежа", "payment_id", 15, "id"), ("Статус карты", "card_status", 14, "text"),
             ("", "blank", 12, "text"), ("Время", "payment_time", 16, "datetime")]
    _xl_table(ws, row, pcols,
              [{"v": _row_values(r, {"status_name": "проведён" if _num(r.status_id) == 1 else "ошибка"})}
               for r in payments.itertuples(index=False)],
              autofilter=False, set_widths=False,
              total={"date": "ИТОГО", "amount_rub": payments["amount_rub"].sum() if not payments.empty else 0})


def _xl_methodology_sheet(wb):
    ws, row = _xl_sheet(wb, "Методология", "Методология",
                        "Источники данных, формулы и правила оценки", "", 2, landscape=False)
    ws.column_dimensions["A"].width = 28
    ws.column_dimensions["B"].width = 110
    for title, items in _methodology():
        row = _xl_block_title(ws, row + 1, title, 2)
        style.write_table_header(ws, row, 1, ["Параметр", "Описание"])
        row += 1
        for term, text in items:
            ws.cell(row=row, column=1, value=term)
            ws.cell(row=row, column=2, value=text)
            style.style_data_row(ws, row, 1, 2)
            ws.cell(row=row, column=1).font = Font(name=style.FONT, size=10, bold=True, color=style.NAVY_3)
            ws.cell(row=row, column=1).alignment = Alignment(horizontal="left", vertical="top", wrap_text=True)
            ws.cell(row=row, column=2).alignment = Alignment(horizontal="left", vertical="top", wrap_text=True)
            ws.row_dimensions[row].height = max(16, 14 * (len(text) // 105 + 1))
            row += 1


def _xl_toc(wb, bundle, sheets: list[tuple[str, str]], title: str):
    ws = wb.create_sheet(style.TOC_SHEET_NAME)
    width = 8
    style.sheet_base_setup(ws, landscape=True)

    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=width)
    c = ws.cell(row=1, column=1, value=title)
    c.font = style.FONT_SHEET_TITLE
    ws.row_dimensions[1].height = 28
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=width)
    ws.cell(row=2, column=1, value=_xl_params(bundle)).font = style.FONT_SHEET_SUBTITLE

    t = bundle["totals"]
    p = bundle["prev_totals"]
    b = bundle["budget"]

    def delta(key, is_pct=False):
        if not p:
            return ""
        if is_pct:
            c_, p_ = _num(t.get(key)), _num(p.get(key))
            return f"{_pp(c_ - p_)} к пред. периоду" if c_ is not None and p_ is not None else ""
        chg = _change_pct(t.get(key), p.get(key))
        return f"{_signed_pct(chg)} к пред. периоду" if chg is not None else ""

    cards_1 = [
        ("Расход на рекламу", _money(t["spend_rub"]), delta("spend_rub")),
        ("Сумма заказов от рекламы", _money(t["revenue_rub"]), delta("revenue_rub")),
        ("ДРР по рекламируемым товарам",
         _pct1(t.get("drr_direct")) + (f" · {_drr_rating(t.get('drr_direct'))}" if _drr_rating(t.get("drr_direct")) else ""),
         f"с учётом связанных заказов — {_pct1(t['drr'])}"),
        ("Заказы от рекламы", _int(t["orders"]), delta("orders")),
    ]
    cards_2 = [
        ("CTR / CR", f"{_pct1(t['ctr'])} / {_pct1(t['cr'])}", "клики/показы, заказы/клики"),
        ("CPC / CPO", f"{_money_dec(t['cpc'])} / {_money(t['cpo'])}", "цена клика / заказа"),
        ("Доступно + бюджеты", _money((b["net"] or 0) + b["budgets_total"]), f"хватит на {_days(b['runway_days'])} дн."),
        ("ДРР от продаж", _pct1(bundle["tacos"].get("value")), "расход ÷ продажи товаров"),
    ]
    style.write_kpi_cards(ws, 4, cards_1, col_start=1, card_width=2)
    style.write_kpi_cards(ws, 8, cards_2, col_start=1, card_width=2)

    row = 12
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=width)
    ws.cell(row=row, column=1, value="Листы").font = Font(name=style.FONT, size=11, bold=True, color=style.NAVY_3)
    row = style.write_toc_links(ws, row + 1, sheets, col_label=1, col_desc=3, desc_span=width - 2)

    style.write_footer_note(
        ws, row + 1, width,
        "Строки с «+» слева раскрываются: кампания → товары, товар → кампании. "
        "Формулы и правила оценки — на листе «Методология».",
    )
    for letter in "ABCDEFGH":
        ws.column_dimensions[letter].width = 16
    return ws


def _assemble_excel(bundle: dict) -> bytes:
    params = _xl_params(bundle)
    wb = Workbook()
    wb.remove(wb.active)

    sheets = [
        ("Сводка", "Ключевые показатели и сравнение с предыдущим периодом"),
        ("Кампании", "Все кампании за период; под каждой — товары (раскрываются «+»)"),
        ("Товары", "Все товары в рекламе; под каждым — кампании; остатки и ДРР от продаж"),
        ("Бюджеты", "Остатки бюджетов активных кампаний и прогноз, на сколько дней хватит"),
        ("Структура", "Типы кампаний, модели оплаты, ставки, площадки, бренды"),
        ("По дням", "Динамика по дням"),
        ("По неделям", "Динамика по неделям (с понедельника)"),
        ("По месяцам", "Динамика по месяцам"),
        ("Сверка", "Расход по статистике против фактических списаний; пополнения счёта"),
        ("Методология", "Источники, формулы, правила оценки и ограничения"),
    ]

    _xl_summary_sheet(wb, bundle, params)
    _xl_campaigns_sheet(wb, bundle, params)
    _xl_products_sheet(wb, bundle, params)
    _xl_budgets_sheet(wb, bundle, params)
    _xl_structure_sheet(wb, bundle, params)
    _xl_time_sheet(wb, "По дням", "Динамика по дням", bundle["daily"], params, "Дата")
    _xl_time_sheet(wb, "По неделям", "Динамика по неделям", bundle["weekly"], params, "Неделя")
    _xl_time_sheet(wb, "По месяцам", "Динамика по месяцам", bundle["monthly"], params, "Месяц")
    _xl_reconciliation_sheet(wb, bundle, params)
    _xl_methodology_sheet(wb)
    _xl_toc(wb, bundle, sheets, "Анализ рекламных кампаний WB — детализация")

    style.finalize_workbook(wb, order=[style.TOC_SHEET_NAME] + [name for name, _ in sheets])
    output = BytesIO()
    wb.save(output)
    return output.getvalue()


def build_ad_campaigns_excel(start_date: str, end_date: str) -> bytes:
    return _assemble_excel(_fetch_report_bundle(start_date, end_date))


# ================================================================ Excel: расход по периодам
def _with_period_labels(df: pd.DataFrame) -> pd.DataFrame:
    d = pd.to_datetime(df["date"])
    week = (d - pd.to_timedelta(d.dt.weekday, unit="D")).dt.normalize()
    month = d.dt.to_period("M").dt.to_timestamp()
    return df.assign(
        day_key=d.dt.normalize(), day_label=d.dt.strftime("%d.%m.%Y"),
        week_key=week, week_label=week.apply(lambda x: f"{x:%d.%m}–{x + pd.Timedelta(days=6):%d.%m.%y}"),
        month_key=month, month_label=month.dt.strftime("%m.%Y"),
    )


def _prepare_period_frames(stats, meta, nm_daily, products):
    camp = stats[["advert_id", "date", "spend_rub", "orders", "revenue_rub"]].copy() if not stats.empty else \
        pd.DataFrame(columns=["advert_id", "date", "spend_rub", "orders", "revenue_rub"])
    names = meta[["advert_id", "name", "type_name"]] if meta is not None and not meta.empty else \
        pd.DataFrame(columns=["advert_id", "name", "type_name"])
    camp = camp.merge(names, on="advert_id", how="left")
    camp["name"] = camp["name"].fillna("Кампания без названия")
    camp["type_name"] = camp["type_name"].fillna("—")

    prod = nm_daily.copy() if nm_daily is not None and not nm_daily.empty else \
        pd.DataFrame(columns=["advert_id", "nm_id", "date", "spend_rub"])
    if not prod.empty:
        prod["api_title"] = None
        prod = _product_titles(prod, products)
    else:
        prod["title"] = None

    if not camp.empty:
        camp = _with_period_labels(camp)
    if not prod.empty:
        prod = _with_period_labels(prod)
    return camp, prod


def _write_period_sheet(wb, name, title, params, camp, prod, key_col, label_col, include_products, note=""):
    periods = (
        camp[[key_col, label_col]].drop_duplicates().sort_values(key_col)[label_col].tolist()
        if not camp.empty else []
    )
    width = 3 + len(periods)
    ws, row = _xl_sheet(wb, name, title, note or "Тип кампании → кампания → товар; уровни раскрываются «+»",
                        params, max(width, 4))
    header = ["Тип / кампания / товар", "ID / артикул", *periods, "Итого, ₽"]
    style.write_table_header(ws, row, 1, header)
    header_row = row
    row += 1

    if camp.empty:
        ws.cell(row=row, column=1, value="Нет данных за выбранный период").font = style.FONT_FOOTNOTE
        return ws

    camp_pivot = camp.pivot_table(index="advert_id", columns=label_col, values="spend_rub",
                                  aggfunc="sum", fill_value=0.0).reindex(columns=periods, fill_value=0.0)
    prod_pivot = None
    if include_products and not prod.empty:
        prod_pivot = prod.pivot_table(index=["advert_id", "nm_id"], columns=label_col, values="spend_rub",
                                      aggfunc="sum", fill_value=0.0).reindex(columns=periods, fill_value=0.0)
        titles = prod.groupby("nm_id")["title"].first().to_dict()

    info = camp.groupby("advert_id").agg(name=("name", "first"), type_name=("type_name", "first"))
    info["total"] = camp_pivot.sum(axis=1)
    type_totals = info.groupby("type_name")["total"].sum().sort_values(ascending=False)

    def write_values(r, values, total, bold=False, fill=None, level=0, font_color=style.TEXT, size=10):
        for i, v in enumerate(values, start=3):
            c = ws.cell(row=r, column=i, value=round(float(v), 2) if v else None)
            c.number_format = style.FMT_MONEY
        c = ws.cell(row=r, column=width, value=round(float(total), 2))
        c.number_format = style.FMT_MONEY
        for col in range(1, width + 1):
            cell = ws.cell(row=r, column=col)
            cell.border = style.BORDER_THIN
            cell.font = Font(name=style.FONT, size=size, bold=bold or col == width, color=font_color)
            if col >= 2:
                cell.alignment = style.ALIGN_RIGHT
            if fill:
                cell.fill = fill
        ws.cell(row=r, column=1).alignment = Alignment(horizontal="left", vertical="center", indent=2 * level)
        if level:
            ws.row_dimensions[r].outline_level = level
            ws.row_dimensions[r].hidden = level > 1

    for type_name, type_total in type_totals.items():
        ids = info[info["type_name"] == type_name].sort_values("total", ascending=False).index
        ws.cell(row=row, column=1, value=type_name)
        write_values(row, camp_pivot.loc[ids].sum(axis=0).tolist(), type_total, bold=True, fill=_FILL_GROUP)
        row += 1
        for advert_id in ids:
            ws.cell(row=row, column=1, value=info.at[advert_id, "name"])
            ws.cell(row=row, column=2, value=int(advert_id))
            write_values(row, camp_pivot.loc[advert_id].tolist(), info.at[advert_id, "total"],
                         bold=True, fill=_FILL_PARENT, level=1)
            row += 1
            if prod_pivot is not None and advert_id in prod_pivot.index.get_level_values(0):
                sub = prod_pivot.loc[advert_id]
                sub = sub.assign(_t=sub.sum(axis=1)).sort_values("_t", ascending=False)
                for nm_id, values in sub.iterrows():
                    total = values.pop("_t")
                    if not total:
                        continue
                    ws.cell(row=row, column=1, value=titles.get(nm_id) or f"Артикул {int(nm_id)}")
                    ws.cell(row=row, column=2, value=int(nm_id))
                    write_values(row, values.tolist(), total, level=2, font_color=style.TEXT_2, size=9)
                    row += 1

    ws.cell(row=row, column=1, value="ИТОГО")
    for i, p in enumerate(periods, start=3):
        ws.cell(row=row, column=i, value=round(float(camp_pivot[p].sum()), 2)).number_format = style.FMT_MONEY
    ws.cell(row=row, column=width, value=round(float(info["total"].sum()), 2)).number_format = style.FMT_MONEY
    style.style_total_row(ws, row, 1, width)
    style.apply_column_dividers(ws, header_row, row, 1, width)

    from openpyxl.utils import get_column_letter
    ws.column_dimensions["A"].width = 46
    ws.column_dimensions["B"].width = 12
    for i in range(3, width + 1):
        ws.column_dimensions[get_column_letter(i)].width = 13 if i < width else 15
    style.freeze_table(ws, header_row, first_col=3)
    return ws


def _assemble_periods_excel(bundle_like: dict) -> bytes:
    camp, prod = bundle_like["camp"], bundle_like["prod"]
    params = bundle_like["params"]
    period_days = bundle_like["period_days"]

    wb = Workbook()
    wb.remove(wb.active)

    day_camp, day_prod, day_note = camp, prod, ""
    if period_days > DAY_SHEET_MAX_DAYS and not camp.empty:
        cutoff = pd.to_datetime(camp["date"]).max() - pd.Timedelta(days=DAY_SHEET_MAX_DAYS - 1)
        day_camp = camp[pd.to_datetime(camp["date"]) >= cutoff]
        day_prod = prod[pd.to_datetime(prod["date"]) >= cutoff] if not prod.empty else prod
        day_note = f"Последние {DAY_SHEET_MAX_DAYS} дней периода; полный период — на листах недель и месяцев"

    _write_period_sheet(wb, "По дням", "Расход на рекламу по дням", params, day_camp, day_prod,
                        "day_key", "day_label", include_products=period_days <= DAY_SHEET_PRODUCTS_MAX_DAYS,
                        note=day_note)
    _write_period_sheet(wb, "По неделям", "Расход на рекламу по неделям", params, camp, prod,
                        "week_key", "week_label", include_products=True)
    _write_period_sheet(wb, "По месяцам", "Расход на рекламу по месяцам", params, camp, prod,
                        "month_key", "month_label", include_products=True)
    _xl_methodology_sheet(wb)

    ws = wb.create_sheet(style.TOC_SHEET_NAME)
    width = 8
    style.sheet_base_setup(ws, landscape=True)
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=width)
    ws.cell(row=1, column=1, value="Рекламные кампании WB — расход по периодам").font = style.FONT_SHEET_TITLE
    ws.row_dimensions[1].height = 28
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=width)
    ws.cell(row=2, column=1, value=params).font = style.FONT_SHEET_SUBTITLE

    spend = float(camp["spend_rub"].sum()) if not camp.empty else 0.0
    revenue = float(camp["revenue_rub"].sum()) if not camp.empty else 0.0
    orders = float(camp["orders"].sum()) if not camp.empty else 0.0
    top_type = (camp.groupby("type_name")["spend_rub"].sum().idxmax() if not camp.empty and spend else "—")
    style.write_kpi_cards(ws, 4, [
        ("Расход за период", _money(spend), "все кампании"),
        ("Заказы от рекламы", _int(orders), f"на {_money(revenue)}"),
        ("ДРР", _pct1(_div(spend, revenue, 100)), "расход ÷ сумма заказов"),
        ("Крупнейший тип", str(top_type), "по расходу"),
    ], col_start=1, card_width=2)

    row = style.write_toc_links(ws, 9, [
        ("По дням", "Расход по дням: тип → кампания → товар"),
        ("По неделям", "Расход по неделям (с понедельника)"),
        ("По месяцам", "Расход по календарным месяцам"),
        ("Методология", "Источники, формулы и правила"),
    ], col_label=1, col_desc=3, desc_span=width - 2)
    style.write_footer_note(ws, row + 1, width,
                            "Строки кампаний раскрываются «+» до товаров. Итог кампании — из статистики "
                            "уровня кампании, строки товаров — из детализации по товарам.")
    for letter in "ABCDEFGH":
        ws.column_dimensions[letter].width = 16

    style.finalize_workbook(wb, order=[style.TOC_SHEET_NAME, "По дням", "По неделям", "По месяцам", "Методология"])
    output = BytesIO()
    wb.save(output)
    return output.getvalue()


def build_ad_campaigns_periods_excel(start_date: str, end_date: str) -> bytes:
    stats = _fetch_stats(start_date, end_date)
    camp, prod = _prepare_period_frames(
        stats, _fetch_campaigns_meta(), _fetch_campaign_products_daily(start_date, end_date), _fetch_products(),
    )
    period_days = (pd.to_datetime(end_date) - pd.to_datetime(start_date)).days + 1
    params = (f"Период: {_period_label(start_date, end_date)} · "
              f"сформировано {datetime.now():%d.%m.%Y %H:%M}")
    return _assemble_periods_excel({"camp": camp, "prod": prod, "params": params, "period_days": period_days})


# ================================================================ меню «Экспорт»
def ad_campaigns_menu_items():
    disabled = not AD_CAMPAIGNS_MENU_ENABLED
    return [
        report_menu_group(
            "Анализ рекламных кампаний",
            [
                export_menu_item(
                    "Аналитическая записка, PDF",
                    "Итоги, выводы, бюджеты, кампании и товары, сверка, методология",
                    AD_CAMPAIGNS_PDF_ITEM_ID,
                    disabled=disabled,
                ),
                export_menu_item(
                    "Детализация, Excel",
                    "Кампании → товары, товары → кампании, бюджеты, структура, сверка",
                    AD_CAMPAIGNS_EXCEL_ITEM_ID,
                    disabled=disabled,
                ),
                export_menu_item(
                    "Расход по периодам, Excel",
                    "Дни, недели, месяцы: тип → кампания → товар",
                    AD_CAMPAIGNS_PERIODS_ITEM_ID,
                    disabled=disabled,
                ),
            ],
            disabled=disabled,
        ),
    ]


# ================================================================ callback
def _resolve_period(date_range) -> tuple[str, str] | None:
    if date_range and len(date_range) == 2:
        start, end = date_range
        if start and end:
            return str(start)[:10], str(end)[:10]
        if start or end:
            return None
    return HISTORY_START.isoformat(), date.today().isoformat()


def _ready_alert(filename: str, content: bytes, period_note: str):
    return dmc.Alert(
        title="Файл готов", color="teal", withCloseButton=True,
        children=dmc.Text(f"{filename} · {len(content) / 1_000_000:.1f} МБ · период {period_note}", size="sm"),
    )


def register_ad_campaigns_callbacks(app, filters):

    @app.callback(
        Output(AD_CAMPAIGNS_PDF_DOWNLOAD_ID, "data"),
        Output(AD_CAMPAIGNS_EXCEL_DOWNLOAD_ID, "data"),
        Output(AD_CAMPAIGNS_PERIODS_DOWNLOAD_ID, "data"),
        Output(AD_CAMPAIGNS_STATUS_ID, "children"),
        Output(AD_CAMPAIGNS_CLICKS_ID, "data"),
        Input(AD_CAMPAIGNS_PDF_ITEM_ID, "n_clicks"),
        Input(AD_CAMPAIGNS_EXCEL_ITEM_ID, "n_clicks"),
        Input(AD_CAMPAIGNS_PERIODS_ITEM_ID, "n_clicks"),
        State(filters.date_picker_id, "value"),
        State(AD_CAMPAIGNS_CLICKS_ID, "data"),
        prevent_initial_call=True,
    )
    def export_ad_campaigns(pdf_clicks, excel_clicks, periods_clicks, date_range, seen_clicks):
        counts = {
            "ad_campaigns_pdf": int(pdf_clicks or 0),
            "ad_campaigns_excel": int(excel_clicks or 0),
            "ad_campaigns_periods": int(periods_clicks or 0),
        }
        seen = seen_clicks or {}
        changed = [k for k, _ in AD_CAMPAIGNS_MENU_KINDS if counts.get(k, 0) != int(seen.get(k) or 0)]
        if not changed:
            return no_update, no_update, no_update, no_update, counts

        period = _resolve_period(date_range)
        if period is None:
            return no_update, no_update, no_update, no_update, counts
        start_date, end_date = period
        period_note = _period_label(start_date, end_date)
        kind = changed[0]

        try:
            if kind == "ad_campaigns_pdf":
                content = build_ad_campaigns_pdf_bytes(start_date, end_date)
                filename = f"WB_реклама_записка_{start_date}_{end_date}.pdf"
                return (dcc.send_bytes(content, filename=filename), no_update, no_update,
                        _ready_alert(filename, content, period_note), counts)

            if kind == "ad_campaigns_excel":
                content = build_ad_campaigns_excel(start_date, end_date)
                filename = f"WB_реклама_детализация_{start_date}_{end_date}.xlsx"
                return (no_update, dcc.send_bytes(content, filename=filename), no_update,
                        _ready_alert(filename, content, period_note), counts)

            content = build_ad_campaigns_periods_excel(start_date, end_date)
            filename = f"WB_реклама_по_периодам_{start_date}_{end_date}.xlsx"
            return (no_update, no_update, dcc.send_bytes(content, filename=filename),
                    _ready_alert(filename, content, period_note), counts)

        except Exception as exc:
            logger.exception("Отчёт по рекламе не сформирован")
            return (
                no_update, no_update, no_update,
                dmc.Alert(
                    title="Не удалось сформировать отчёт", color="red", withCloseButton=True,
                    children=dmc.Text(f"{type(exc).__name__}: {exc} (период {period_note})", size="sm"),
                ),
                counts,
            )
