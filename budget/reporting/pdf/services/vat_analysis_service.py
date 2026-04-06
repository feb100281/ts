# budget/reporting/pdf/services/vat_analysis_service.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

import pandas as pd
from django.db import connection

from budget.reporting.pdf.services.sales_data_service import get_duckdb_conn


# =========================
# Форматирование
# =========================

def _format_money(value: float | int | None) -> str:
    value = float(value or 0)
    return f"{value:,.0f}".replace(",", " ")


def _fmt_pct(value: float | int | None) -> str:
    value = float(value or 0)
    return f"{value:+.1f}%"


def _safe_pct_change(current: float | int | None, base: float | int | None) -> float:
    current = float(current or 0)
    base = float(base or 0)
    if base == 0:
        return 0.0
    return (current / base - 1) * 100


# =========================
# Вспомогательные структуры
# =========================

@dataclass
class VatRateInterval:
    start_date: pd.Timestamp
    end_date: pd.Timestamp | None
    rate: float


# =========================
# Загрузка ставок НДС из Postgres
# =========================

def _load_standard_vat_intervals() -> list[VatRateInterval]:
    """
    Забираем из Postgres историю ставок по налогу НДС.
    Используем только налог 'НДС' из macro_taxeslist + macro_taxrates.

    Логика:
    - tax_name = 'НДС'
    - rate действует начиная с даты date
    - до следующей даты изменения
    """
    query = """
        SELECT
            tr.date::date AS start_date,
            tr.rate::double precision AS rate
        FROM public.macro_taxrates tr
        JOIN public.macro_taxeslist tl
            ON tl.id = tr.tax_id
        WHERE tl.tax_name = 'НДС'
        ORDER BY tr.date ASC
    """

    df = pd.read_sql(query, connection)
    if df.empty:
        raise ValueError("В public.macro_taxrates не найдены ставки для налога 'НДС'.")

    df["start_date"] = pd.to_datetime(df["start_date"])
    df["rate"] = df["rate"].astype(float)

    intervals: list[VatRateInterval] = []

    for i in range(len(df)):
        start_date = df.iloc[i]["start_date"]
        rate = float(df.iloc[i]["rate"])
        end_date = None

        if i < len(df) - 1:
            next_start = df.iloc[i + 1]["start_date"]
            end_date = next_start - pd.Timedelta(days=1)

        intervals.append(
            VatRateInterval(
                start_date=start_date,
                end_date=end_date,
                rate=rate,
            )
        )

    return intervals


def _resolve_standard_vat_rate(dt: pd.Timestamp, intervals: list[VatRateInterval]) -> float:
    """
    Ищем обычную ставку НДС, действующую на дату.
    """
    for interval in intervals:
        if interval.end_date is None:
            if dt >= interval.start_date:
                return interval.rate
        else:
            if interval.start_date <= dt <= interval.end_date:
                return interval.rate

    # Если дата раньше первой ставки — на всякий случай берём самую раннюю
    return float(intervals[0].rate)


# =========================
# База продаж по дням
# =========================

def _get_latest_sales_date() -> pd.Timestamp | None:
    """
    Возвращает последнюю дату, по которой есть данные по продажам/возвратам
    в таблице sales для retail_price.
    """
    conn = get_duckdb_conn()

    query = """
        SELECT MAX(CAST(date_from AS DATE)) AS max_dt
        FROM sales
        WHERE field = 'retail_price'
          AND dtn_id IN (1, 2)
          AND value IS NOT NULL
    """

    df = conn.execute(query).df()
    conn.close()

    if df.empty or pd.isna(df.loc[0, "max_dt"]):
        return None

    return pd.Timestamp(df.loc[0, "max_dt"]).normalize()


def _get_vat_daily_base(
    date_from: date | str,
    date_to: date | str,
) -> pd.DataFrame:
    """
    Забираем из DuckDB продажи / возвраты по дням, ставке vat_rate из product
    и категории subjectName из cards.

    ВАЖНО:
    - sales.value по retail_price трактуем как сумму с НДС
    - dtn_id = 2 -> продажа
    - dtn_id = 1 -> возврат
    """
    conn = get_duckdb_conn()

    query = """
        WITH product_dim AS (
            SELECT
                nm_id,
                ANY_VALUE(vat_rate) AS vat_rate
            FROM product
            GROUP BY nm_id
        ),
        cards_dim AS (
            SELECT
                nm_id,
                ANY_VALUE(json_extract_string(payload_raw, '$.subjectName')) AS subject_name
            FROM cards
            GROUP BY nm_id
        )
        SELECT
            CAST(s.date_from AS DATE) AS dt,
            p.vat_rate AS vat_rate,
            COALESCE(c.subject_name, 'Не указана') AS subject_name,
            SUM(CASE WHEN s.dtn_id = 2 AND s.field = 'retail_price' THEN s.value ELSE 0 END) / 100.0 AS sales_gross,
            SUM(CASE WHEN s.dtn_id = 1 AND s.field = 'retail_price' THEN s.value ELSE 0 END) / 100.0 AS returns_gross
        FROM sales s
        LEFT JOIN product_dim p
            ON p.nm_id = s.nm_id
        LEFT JOIN cards_dim c
            ON c.nm_id = s.nm_id
        WHERE s.field = 'retail_price'
          AND CAST(s.date_from AS DATE) BETWEEN ? AND ?
        GROUP BY 1, 2, 3
        ORDER BY 1, 2, 3
    """

    df = conn.execute(query, [date_from, date_to]).df()
    conn.close()

    if df.empty:
        return pd.DataFrame(
            columns=[
                "dt",
                "vat_rate",
                "subject_name",
                "sales_gross",
                "returns_gross",
            ]
        )

    df["dt"] = pd.to_datetime(df["dt"])
    df["sales_gross"] = df["sales_gross"].astype(float)
    df["returns_gross"] = df["returns_gross"].astype(float)
    df["subject_name"] = df["subject_name"].fillna("Не указана")

    return df


def _apply_effective_vat_rate(df: pd.DataFrame) -> pd.DataFrame:
    """
    Подставляем ставку НДС:
    - если vat_rate заполнен в product -> берём его
    - если vat_rate NULL -> берём стандартную ставку по дате из Postgres
    """
    if df.empty:
        return df

    intervals = _load_standard_vat_intervals()
    df = df.copy()

    def pick_rate(row) -> float:
        explicit_rate = row.get("vat_rate")
        if pd.notna(explicit_rate):
            return float(explicit_rate)
        return _resolve_standard_vat_rate(pd.to_datetime(row["dt"]), intervals)

    df["effective_vat_rate"] = df.apply(pick_rate, axis=1)

    def rate_label(rate: float) -> str:
        rate = float(rate or 0)
        if abs(rate - 10) < 1e-9:
            return "Льготная ставка 10%"
        return f"Основная ставка {rate:.0f}%"

    df["vat_rate_label"] = df["effective_vat_rate"].apply(rate_label)
    return df


def _calculate_vat_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Из суммы с НДС выделяем:
    - НДС
    - выручку без НДС
    """
    if df.empty:
        return df

    df = df.copy()

    rate_factor = df["effective_vat_rate"] / (100.0 + df["effective_vat_rate"])

    df["sales_vat"] = df["sales_gross"] * rate_factor
    df["returns_vat"] = df["returns_gross"] * rate_factor

    df["sales_net_no_vat"] = df["sales_gross"] - df["sales_vat"]
    df["returns_net_no_vat"] = df["returns_gross"] - df["returns_vat"]

    df["net_gross"] = df["sales_gross"] - df["returns_gross"]
    df["net_vat"] = df["sales_vat"] - df["returns_vat"]
    df["net_no_vat"] = df["sales_net_no_vat"] - df["returns_net_no_vat"]

    return df


# =========================
# Агрегации
# =========================

def _aggregate_period(df: pd.DataFrame) -> dict[str, float]:
    if df.empty:
        return {
            "sales_gross": 0.0,
            "returns_gross": 0.0,
            "sales_vat": 0.0,
            "returns_vat": 0.0,
            "sales_net_no_vat": 0.0,
            "returns_net_no_vat": 0.0,
            "net_gross": 0.0,
            "net_vat": 0.0,
            "net_no_vat": 0.0,
        }

    numeric_cols = [
        "sales_gross",
        "returns_gross",
        "sales_vat",
        "returns_vat",
        "sales_net_no_vat",
        "returns_net_no_vat",
        "net_gross",
        "net_vat",
        "net_no_vat",
    ]

    sums = df[numeric_cols].sum()
    return {col: float(sums[col]) for col in numeric_cols}


def _add_format_fields(row: dict[str, Any]) -> dict[str, Any]:
    row = dict(row)

    for key in [
        "sales_gross",
        "returns_gross",
        "sales_vat",
        "returns_vat",
        "sales_net_no_vat",
        "returns_net_no_vat",
        "net_gross",
        "net_vat",
        "net_no_vat",
    ]:
        row[f"{key}_fmt"] = _format_money(row.get(key))

    return row


def _build_comparison(current_row: dict[str, Any], prev_row: dict[str, Any]) -> dict[str, Any]:
    current_row = dict(current_row)
    prev_row = dict(prev_row)

    net_vat_change_pct = _safe_pct_change(
        current_row.get("net_vat", 0),
        prev_row.get("net_vat", 0),
    )
    net_no_vat_change_pct = _safe_pct_change(
        current_row.get("net_no_vat", 0),
        prev_row.get("net_no_vat", 0),
    )
    net_gross_change_pct = _safe_pct_change(
        current_row.get("net_gross", 0),
        prev_row.get("net_gross", 0),
    )

    out = {
        "current": _add_format_fields(current_row),
        "previous": _add_format_fields(prev_row),
        "net_vat_change_pct": net_vat_change_pct,
        "net_vat_change_pct_fmt": _fmt_pct(net_vat_change_pct),
        "net_no_vat_change_pct": net_no_vat_change_pct,
        "net_no_vat_change_pct_fmt": _fmt_pct(net_no_vat_change_pct),
        "net_gross_change_pct": net_gross_change_pct,
        "net_gross_change_pct_fmt": _fmt_pct(net_gross_change_pct),
    }
    return out


def _build_rate_breakdown(df: pd.DataFrame) -> list[dict[str, Any]]:
    if df.empty:
        return []

    grouped = (
        df.groupby("vat_rate_label", dropna=False)[
            ["sales_gross", "returns_gross", "sales_vat", "returns_vat", "net_gross", "net_vat", "net_no_vat"]
        ]
        .sum()
        .reset_index()
        .sort_values("net_gross", ascending=False)
    )

    total_net_vat = float(grouped["net_vat"].sum()) or 0.0

    rows: list[dict[str, Any]] = []
    for _, row in grouped.iterrows():
        net_vat = float(row["net_vat"] or 0)
        share_pct = (net_vat / total_net_vat * 100.0) if total_net_vat else 0.0

        item = {
            "vat_rate_label": row["vat_rate_label"],
            "sales_gross": float(row["sales_gross"] or 0),
            "returns_gross": float(row["returns_gross"] or 0),
            "sales_vat": float(row["sales_vat"] or 0),
            "returns_vat": float(row["returns_vat"] or 0),
            "net_gross": float(row["net_gross"] or 0),
            "net_vat": net_vat,
            "net_no_vat": float(row["net_no_vat"] or 0),
            "share_pct": share_pct,
            "share_pct_fmt": f"{share_pct:.2f}%",
        }
        rows.append(_add_format_fields(item))

    return rows


def _build_category_breakdown(
    df: pd.DataFrame,
    vat_rate: float | None = None,
) -> list[dict[str, Any]]:
    """
    Разбивка по категориям subject_name.
    Если vat_rate передан, оставляем только строки с этой эффективной ставкой НДС.
    Возвращаем все категории без ограничения top_n.
    """
    if df.empty:
        return []

    df = df.copy()

    if vat_rate is not None:
        df = df[df["effective_vat_rate"] == vat_rate].copy()

    if df.empty:
        return []

    grouped_all = (
        df.groupby("subject_name", dropna=False)[
            ["sales_gross", "returns_gross", "sales_vat", "returns_vat", "net_gross", "net_vat", "net_no_vat"]
        ]
        .sum()
        .reset_index()
        .sort_values("net_gross", ascending=False)
    )

    total_net_gross = float(grouped_all["net_gross"].sum()) or 0.0
    total_net_vat = float(grouped_all["net_vat"].sum()) or 0.0

    rows: list[dict[str, Any]] = []
    for _, row in grouped_all.iterrows():
        net_gross = float(row["net_gross"] or 0)
        net_vat = float(row["net_vat"] or 0)

        revenue_share_pct = (net_gross / total_net_gross * 100.0) if total_net_gross else 0.0
        vat_share_pct = (net_vat / total_net_vat * 100.0) if total_net_vat else 0.0

        item = {
            "subject_name": row["subject_name"] or "Не указана",
            "sales_gross": float(row["sales_gross"] or 0),
            "returns_gross": float(row["returns_gross"] or 0),
            "sales_vat": float(row["sales_vat"] or 0),
            "returns_vat": float(row["returns_vat"] or 0),
            "net_gross": net_gross,
            "net_vat": net_vat,
            "net_no_vat": float(row["net_no_vat"] or 0),
            "revenue_share_pct": revenue_share_pct,
            "revenue_share_pct_fmt": f"{revenue_share_pct:.2f}%",
            "vat_share_pct": vat_share_pct,
            "vat_share_pct_fmt": f"{vat_share_pct:.2f}%",
        }
        rows.append(_add_format_fields(item))

    return rows

# =========================
# Основной публичный метод
# =========================

def get_vat_analysis_context(report_date: date | None = None) -> dict[str, Any]:
    """
    Возвращает контекст для раздела анализа НДС:
    - MTD
    - YTD
    - кварталы текущего года и прошлого года
    - разбивка по ставкам для MTD / YTD
    - разбивка по категориям для MTD / YTD

    Логика определения даты отчета:
    - если report_date передан -> используем его
    - если не передан -> берём последнюю дату, по которой есть продажи/возвраты
    """
    if report_date is not None:
        as_of = pd.Timestamp(report_date).normalize()
    else:
        latest_sales_date = _get_latest_sales_date()
        if latest_sales_date is None:
            return {
                "as_of_date": None,
                "mtd": None,
                "ytd": None,
                "quarter_rows": [],
                "mtd_rate_breakdown": [],
                "ytd_rate_breakdown": [],
                "mtd_category_breakdown": [],
                "ytd_category_breakdown": [],
                "vat_comment": None,
                "vat_category_comment": None,
            }
        as_of = latest_sales_date

    current_year_start = pd.Timestamp(year=as_of.year, month=1, day=1)
    prev_year_same_day = as_of - pd.DateOffset(years=1)
    prev_year_start = pd.Timestamp(year=prev_year_same_day.year, month=1, day=1)

    current_month_start = pd.Timestamp(year=as_of.year, month=as_of.month, day=1)
    prev_month_same_start = current_month_start - pd.DateOffset(years=1)

    load_from = min(prev_year_start, prev_month_same_start).date()
    load_to = as_of.date()

    base_df = _get_vat_daily_base(load_from, load_to)
    base_df = _apply_effective_vat_rate(base_df)
    base_df = _calculate_vat_columns(base_df)

    if base_df.empty:
        return {
            "as_of_date": as_of.date(),
            "mtd": None,
            "ytd": None,
            "quarter_rows": [],
            "mtd_rate_breakdown": [],
            "ytd_rate_breakdown": [],
            "mtd_category_breakdown": [],
            "ytd_category_breakdown": [],
            "vat_comment": None,
            "vat_category_comment": None,
        }

    # ============
    # MTD
    # ============
    current_mtd_df = base_df[
        (base_df["dt"] >= current_month_start) &
        (base_df["dt"] <= as_of)
    ].copy()

    prev_mtd_end = prev_month_same_start + pd.Timedelta(days=as_of.day - 1)
    prev_mtd_df = base_df[
        (base_df["dt"] >= prev_month_same_start) &
        (base_df["dt"] <= prev_mtd_end)
    ].copy()

    current_mtd = _aggregate_period(current_mtd_df)
    prev_mtd = _aggregate_period(prev_mtd_df)
    mtd = _build_comparison(current_mtd, prev_mtd)

    # ============
    # YTD
    # ============
    current_ytd_df = base_df[
        (base_df["dt"] >= current_year_start) &
        (base_df["dt"] <= as_of)
    ].copy()

    prev_ytd_end = prev_year_start + (as_of - current_year_start)
    prev_ytd_df = base_df[
        (base_df["dt"] >= prev_year_start) &
        (base_df["dt"] <= prev_ytd_end)
    ].copy()

    current_ytd = _aggregate_period(current_ytd_df)
    prev_ytd = _aggregate_period(prev_ytd_df)
    ytd = _build_comparison(current_ytd, prev_ytd)

    # ============
    # Кварталы
    # ============
    quarter_rows: list[dict[str, Any]] = []

    for q in [1, 2, 3, 4]:
        month_from = (q - 1) * 3 + 1
        month_to = month_from + 2

        q_start = pd.Timestamp(year=as_of.year, month=month_from, day=1)
        q_end = (pd.Timestamp(year=as_of.year, month=month_to, day=1) + pd.offsets.MonthEnd(1)).normalize()

        prev_q_start = q_start - pd.DateOffset(years=1)
        prev_q_end = q_end - pd.DateOffset(years=1)

        current_q_df = base_df[
            (base_df["dt"] >= q_start) &
            (base_df["dt"] <= min(q_end, as_of))
        ].copy()

        prev_q_df = base_df[
            (base_df["dt"] >= prev_q_start) &
            (base_df["dt"] <= min(prev_q_end, prev_year_same_day))
        ].copy()

        current_q = _aggregate_period(current_q_df)
        prev_q = _aggregate_period(prev_q_df)

        net_vat_change_pct = _safe_pct_change(current_q["net_vat"], prev_q["net_vat"])
        net_no_vat_change_pct = _safe_pct_change(current_q["net_no_vat"], prev_q["net_no_vat"])

        row = {
            "quarter": f"Q{q}",
            "year": as_of.year,
            "current_start": q_start.date(),
            "current_end": min(q_end, as_of).date(),
            "previous_start": prev_q_start.date(),
            "previous_end": min(prev_q_end, prev_year_same_day).date(),

            "current_sales_gross": current_q["sales_gross"],
            "current_returns_gross": current_q["returns_gross"],
            "current_net_gross": current_q["net_gross"],
            "current_net_vat": current_q["net_vat"],
            "current_net_no_vat": current_q["net_no_vat"],

            "previous_sales_gross": prev_q["sales_gross"],
            "previous_returns_gross": prev_q["returns_gross"],
            "previous_net_gross": prev_q["net_gross"],
            "previous_net_vat": prev_q["net_vat"],
            "previous_net_no_vat": prev_q["net_no_vat"],

            "net_vat_change_pct": net_vat_change_pct,
            "net_vat_change_pct_fmt": _fmt_pct(net_vat_change_pct),
            "net_no_vat_change_pct": net_no_vat_change_pct,
            "net_no_vat_change_pct_fmt": _fmt_pct(net_no_vat_change_pct),
        }

        row["current_sales_gross_fmt"] = _format_money(row["current_sales_gross"])
        row["current_returns_gross_fmt"] = _format_money(row["current_returns_gross"])
        row["current_net_gross_fmt"] = _format_money(row["current_net_gross"])
        row["current_net_vat_fmt"] = _format_money(row["current_net_vat"])
        row["current_net_no_vat_fmt"] = _format_money(row["current_net_no_vat"])

        row["previous_sales_gross_fmt"] = _format_money(row["previous_sales_gross"])
        row["previous_returns_gross_fmt"] = _format_money(row["previous_returns_gross"])
        row["previous_net_gross_fmt"] = _format_money(row["previous_net_gross"])
        row["previous_net_vat_fmt"] = _format_money(row["previous_net_vat"])
        row["previous_net_no_vat_fmt"] = _format_money(row["previous_net_no_vat"])

        quarter_rows.append(row)

    mtd_rate_breakdown = _build_rate_breakdown(current_mtd_df)
    ytd_rate_breakdown = _build_rate_breakdown(current_ytd_df)

    mtd_category_breakdown = _build_category_breakdown(
    current_mtd_df,
    vat_rate=10,
)

    ytd_category_breakdown = _build_category_breakdown(
        current_ytd_df,
        vat_rate=10,
    )
    
    vat_comment = build_vat_comment(
        mtd=mtd,
        ytd=ytd,
        mtd_rate_breakdown=mtd_rate_breakdown,
        ytd_rate_breakdown=ytd_rate_breakdown,
        as_of=as_of,
    )

    vat_category_comment = build_vat_category_comment(
        mtd_category_breakdown=mtd_category_breakdown,
        ytd_category_breakdown=ytd_category_breakdown,
    )

    return {
        "as_of_date": as_of.date(),
        "mtd": mtd,
        "ytd": ytd,
        "quarter_rows": quarter_rows,
        "mtd_rate_breakdown": mtd_rate_breakdown,
        "ytd_rate_breakdown": ytd_rate_breakdown,
        "mtd_category_breakdown": mtd_category_breakdown,
        "ytd_category_breakdown": ytd_category_breakdown,
        "vat_comment": vat_comment,
        "vat_category_comment": vat_category_comment,
    }


# =========================
# Комментарии
# =========================

def build_vat_comment(
    mtd: dict[str, Any] | None,
    ytd: dict[str, Any] | None,
    mtd_rate_breakdown: list[dict[str, Any]] | None,
    ytd_rate_breakdown: list[dict[str, Any]] | None,
    as_of: pd.Timestamp,
) -> dict[str, Any] | None:
    if not mtd or not ytd:
        return None

    mtd_current = mtd["current"]
    mtd_prev = mtd["previous"]
    ytd_current = ytd["current"]
    ytd_prev = ytd["previous"]

    mtd_vat = float(mtd_current.get("net_vat", 0) or 0)
    mtd_vat_prev = float(mtd_prev.get("net_vat", 0) or 0)
    ytd_vat = float(ytd_current.get("net_vat", 0) or 0)
    ytd_vat_prev = float(ytd_prev.get("net_vat", 0) or 0)

    mtd_change = _safe_pct_change(mtd_vat, mtd_vat_prev)
    ytd_change = _safe_pct_change(ytd_vat, ytd_vat_prev)

    if mtd_change >= 5:
        trend_class = "positive"
        trend_text = "наблюдается рост"
    elif mtd_change <= -5:
        trend_class = "negative"
        trend_text = "наблюдается снижение"
    else:
        trend_class = "neutral"
        trend_text = "существенных изменений не наблюдается"

    mtd_top_rate = mtd_rate_breakdown[0] if mtd_rate_breakdown else None
    ytd_top_rate = ytd_rate_breakdown[0] if ytd_rate_breakdown else None

    mtd_rate_text = ""
    if mtd_top_rate:
        mtd_rate_text = (
            f"Наибольшая доля НДС в MTD приходится на сегмент "
            f"«{mtd_top_rate['vat_rate_label']}» — {mtd_top_rate['net_vat_fmt']} руб. "
            f"({mtd_top_rate['share_pct_fmt']})."
        )

    ytd_rate_text = ""
    if ytd_top_rate:
        ytd_rate_text = (
            f"По YTD максимальный вклад также формирует сегмент "
            f"«{ytd_top_rate['vat_rate_label']}» — {ytd_top_rate['net_vat_fmt']} руб."
        )

    comment = (
        f"По состоянию на {as_of.strftime('%d.%m.%Y')} по MTD {trend_text} суммы НДС к начислению: "
        f"{_format_money(mtd_vat)} руб. против {_format_money(mtd_vat_prev)} руб. "
        f"за аналогичный период прошлого года ({_fmt_pct(mtd_change)}). "
        f"Чистая выручка без НДС за MTD составила {_format_money(mtd_current.get('net_no_vat'))} руб. "
        f"при валовой выручке {_format_money(mtd_current.get('net_gross'))} руб. "
        f"{mtd_rate_text} "
        f"По YTD сумма НДС составляет {_format_money(ytd_vat)} руб. против "
        f"{_format_money(ytd_vat_prev)} руб. годом ранее ({_fmt_pct(ytd_change)}). "
        f"Чистая выручка без НДС за YTD составила {_format_money(ytd_current.get('net_no_vat'))} руб. "
        f"{ytd_rate_text}"
    )

    return {
        "value": _fmt_pct(mtd_change),
        "comment": comment,
        "class": trend_class,
    }


def build_vat_category_comment(
    mtd_category_breakdown: list[dict[str, Any]] | None,
    ytd_category_breakdown: list[dict[str, Any]] | None,
) -> str | None:
    if not mtd_category_breakdown and not ytd_category_breakdown:
        return None

    parts: list[str] = []

    if mtd_category_breakdown:
        top_mtd = mtd_category_breakdown[0]
        parts.append(
            f"В MTD наибольший вклад в выручку формирует категория "
            f"«{top_mtd['subject_name']}» — {top_mtd['net_gross_fmt']} руб. "
            f"({top_mtd['revenue_share_pct_fmt']} от выручки топ-категорий) и "
            f"{top_mtd['net_vat_fmt']} руб. НДС ({top_mtd['vat_share_pct_fmt']})."
        )

    if ytd_category_breakdown:
        top_ytd = ytd_category_breakdown[0]
        parts.append(
            f"По YTD лидирующей категорией также является "
            f"«{top_ytd['subject_name']}» — {top_ytd['net_gross_fmt']} руб. "
            f"и {top_ytd['net_vat_fmt']} руб. НДС."
        )

    return " ".join(parts) if parts else None