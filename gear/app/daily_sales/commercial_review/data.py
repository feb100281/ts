# gear/app/daily_sales/commercial_review/data.py
"""
Сбор данных для коммерческого обзора.

В основном своих запросов здесь нет: обзор берёт уже собранный
payload ежедневной сводки и оперативный срез заказов FBS.
Дублировать расчёты нельзя — иначе в двух отчётах появятся две
разные «выручки», и доверие к обоим кончится.

Исключение — build_wb_expenses_slice: разрез расходов WB по
неделям и статьям нигде в проекте уже не посчитан (в дневной
сводке есть только их сумма за неделю, а разбивка по статьям —
только на уровне месяца, в P&L). Здесь это не дублирование,
а единственное место, где такой разрез вообще существует.
"""

from __future__ import annotations

from datetime import date, timedelta

#: За сколько дней берём заказы FBS для раздела по сборке.
FBS_WINDOW_DAYS = 30

#: Окно для разрезов «выручка и маржинальность» по брендам
#: и категориям. 90 дней — компромисс: достаточно данных,
#: чтобы маржа не скакала от одной поставки, и достаточно
#: свежо, чтобы по этому принимать решения.
MIX_WINDOW_DAYS = 90


def build_review_payload(report_date: date) -> dict:
    """Payload ежедневной сводки — основа всех финансовых страниц."""
    from ..daily_brief.data import build_daily_brief_payload

    return build_daily_brief_payload(report_date)


def build_fbs_slice(report_date: date, window_days=FBS_WINDOW_DAYS):
    """
    Оперативный срез заказов FBS.

    Ошибка здесь не должна уносить весь отчёт: финансовые
    страницы от FBS не зависят, поэтому при сбое возвращаем
    None, и раздел показывает честную заметку.
    """
    try:
        from ..fbs_orders.data import collect_fbs_analysis

        return collect_fbs_analysis(
            start=report_date - timedelta(days=window_days - 1),
            end=report_date,
            as_of_date=report_date,
        )

    except Exception:
        return None


def build_mix_slices(report_date: date, days=MIX_WINDOW_DAYS) -> dict:
    """
    Выручка и маржинальность по брендам и категориям.

    Берём тот же расчёт, что и вкладка «Структура выручки»
    в дашборде: маржа = выручка без НДС − управленческая
    себестоимость + комиссия WB (комиссия приходит со своим
    знаком, поэтому здесь сложение). Свой вариант формулы
    заводить нельзя — иначе в двух местах получатся две разные
    маржи по одному бренду.
    """
    from .analysis import week_bounds

    start = report_date - timedelta(days=days - 1)
    bounds = week_bounds(report_date)

    try:
        from ..revenue_structure.data import get_revenue_structure

        def slice_for(date_from, date_to, dimension):
            return get_revenue_structure(
                start_date=date_from,
                end_date=date_to,
                dimension=dimension,
            ) or []

        brands = slice_for(start, report_date, "brand")
        categories = slice_for(start, report_date, "category")

        # Последняя закрытая календарная неделя — короткий
        # горизонт для тех же разрезов. Именно её обсуждают
        # на планёрке, а 90 дней нужны, чтобы маржа не скакала
        # от одной поставки.
        brands_week = slice_for(
            bounds["cur_start"], bounds["cur_end"], "brand"
        )
        categories_week = slice_for(
            bounds["cur_start"], bounds["cur_end"], "category"
        )

    except Exception:
        return {
            "available": False,
            "brands": [],
            "categories": [],
            "brands_week": [],
            "categories_week": [],
        }

    return {
        "available": bool(brands or categories),
        "days": days,
        "date_from": start.isoformat(),
        "date_to": report_date.isoformat(),
        "brands": brands,
        "categories": categories,

        "week_from": bounds["cur_start"].isoformat(),
        "week_to": bounds["cur_end"].isoformat(),
        "brands_week": brands_week,
        "categories_week": categories_week,
    }


#: Категории расходов WB и поля sales_long, из которых они
#: собираются. Категоризация и НДС-логика зеркалят
#: management/commands/sql/wb_costs.sql и opex.sql (счита
#: без НДС, дефолт ставки 20%, если она не указана) —
#: те файлы не трогаем, здесь тот же подход, но по неделям
#: и только за окно отчёта, а не за всю историю.
WB_EXPENSE_CATEGORIES = (
    ("Логистика", "field = 'delivery_rub'"),
    ("Хранение", "field = 'storage_fee'"),
    ("Приёмка", "field = 'acceptance'"),
    ("Штрафы", "field = 'penalty'"),
    (
        "Программа лояльности",
        "field IN ('cashback_commission_change', 'cashback_amount')",
    ),
    (
        "Продвижение и услуги WB",
        "field = 'deduction' "
        "AND btn IS NOT NULL "
        "AND NOT STARTS_WITH(btn, 'Платеж') "
        "AND NOT STARTS_WITH(btn, 'Перевод')",
    ),
)


def _wb_expenses_sql() -> str:
    branches = []
    for category, condition in WB_EXPENSE_CATEGORIES:
        branches.append(
            f"""
            SELECT
                date_from,
                rrd_id,
                '{category}' AS category,

                COALESCE(SUM(val) FILTER (WHERE oper = 'dt'), 0) AS dt,
                COALESCE(SUM(val) FILTER (WHERE oper = 'cr'), 0) AS cr,
                MAX(vat_rate) AS vat_rate

            FROM sales.sales_long

            WHERE {condition}
              AND date_from::DATE BETWEEN $start_date AND $end_date

            GROUP BY
                date_from,
                rrd_id
            """
        )

    union = "\n\nUNION ALL\n".join(branches)

    return f"""
        WITH costs AS ({union})

        SELECT
            date_from::DATE AS day,
            category,

            SUM(
                (dt - cr)
                / (100 + COALESCE(vat_rate, 20))
                * 100
            ) / 100 AS amount

        FROM costs

        GROUP BY
            day,
            category

        ORDER BY
            day,
            category
    """


def build_wb_expenses_slice(report_date: date, weeks: int = None) -> dict:
    """
    Расходы WB по неделям и статьям: логистика, хранение,
    приёмка, штрафы, программа лояльности, продвижение и услуги.

    Показываем последние N закрытых календарных недель (те же
    границы, что и week_bounds для остального отчёта) плюс
    текущую, ещё не закрытую неделю отдельной строкой — её
    сравнивать с полными неделями напрямую нельзя (меньше дней),
    но и молчать о ней не стоит: часть расходов там уже есть.
    """
    import pandas as pd

    from . import config as C
    from .analysis import week_bounds

    weeks = weeks or C.WB_EXPENSES_WEEKS
    bounds = week_bounds(report_date)
    closed_end = bounds["cur_end"]
    start = closed_end - timedelta(days=7 * weeks - 1)
    end = report_date

    empty = {
        "available": False,
        "date_from": start.isoformat(),
        "date_to": end.isoformat(),
        "categories": [],
        "weeks": [],
        "category_spikes": [],
        "total_spike": None,
    }

    try:
        from conns import get_duckdb_conn_with_opt

        with get_duckdb_conn_with_opt() as con:
            df = con.execute(
                _wb_expenses_sql(),
                {
                    "start_date": start.isoformat(),
                    "end_date": end.isoformat(),
                },
            ).df()

    except Exception:
        return empty

    if df is None or df.empty:
        return empty

    df["day"] = pd.to_datetime(df["day"]).dt.date
    df["week_start"] = df["day"].apply(
        lambda d: d - timedelta(days=d.weekday())
    )

    pivot = (
        df.groupby(["week_start", "category"], as_index=False)["amount"]
        .sum()
    )

    week_starts = sorted(pivot["week_start"].unique())

    # Расходы -- отрицательные суммы (та же управленческая
    # конвенция, что и везде в отчёте: минус в скобках). Ранжировать
    # и искать всплески нужно по МОДУЛЮ, а не по значению со знаком --
    # иначе "крупнейшей" оказывается статья ближе всего к нулю.
    category_totals = pivot.groupby("category")["amount"].sum()
    categories = list(
        category_totals.abs().sort_values(ascending=False).index
    )
    grand_total_all = float(category_totals.sum())

    week_rows = []
    for ws in week_starts:
        we = ws + timedelta(days=6)
        is_closed = we <= closed_end
        days_covered = (min(end, we) - ws).days + 1

        by_category = {
            cat: float(
                pivot.loc[
                    (pivot["week_start"] == ws) & (pivot["category"] == cat),
                    "amount",
                ].sum()
            )
            for cat in categories
        }
        week_rows.append({
            "week_start": ws.isoformat(),
            "week_end": we.isoformat(),
            "label": f"{ws.strftime('%d.%m')}–{we.strftime('%d.%m')}",
            "total": sum(by_category.values()),
            "by_category": by_category,
            "is_closed": is_closed,
            "days_covered": days_covered,
        })

    closed_rows = [w for w in week_rows if w["is_closed"]]
    grand_total = sum(w["total"] for w in closed_rows)

    # --- пики: где неделя заметно выше остальных в этом же окне ---
    # Сравниваем только ЗАКРЫТЫЕ недели: текущая неполная неделя
    # почти всегда даёт меньшую сумму просто из-за нехватки дней,
    # и это не всплеск, а недостаток данных -- сравнивать её
    # с полными неделями нечестно в обе стороны.
    def _find_spike(values_by_week):
        """
        values_by_week — [(label, value), ...] по закрытым неделям.

        Пик — неделя, которая настолько выше среднего по
        ОСТАЛЬНЫМ неделям, что это не обычный разброс, а именно
        всплеск. Сравнение идёт по модулю суммы (расходы
        отрицательные), знак сохраняется только для отображения.
        """
        if len(values_by_week) < 3:
            return None

        best = None
        for i, (wk_label, value) in enumerate(values_by_week):
            others = [v for j, v in enumerate(
                x[1] for x in values_by_week
            ) if j != i]
            baseline = sum(others) / len(others) if others else 0

            mag_value = abs(value)
            mag_baseline = abs(baseline)

            if mag_baseline <= 0 or mag_value <= 0:
                continue

            ratio = mag_value / mag_baseline
            if ratio >= C.WB_EXPENSES_SPIKE_RATIO:
                if best is None or ratio > best["ratio"]:
                    best = {
                        "label": wk_label,
                        "value": value,
                        "baseline": baseline,
                        "ratio": ratio,
                    }
        return best

    total_series = [(w["label"], w["total"]) for w in closed_rows]
    total_spike = _find_spike(total_series)

    category_spikes = []
    for cat in categories:
        share_pct = (
            100.0 * category_totals[cat] / grand_total_all
            if grand_total_all else 0
        )
        if share_pct < C.WB_EXPENSES_SPIKE_MIN_SHARE_PCT:
            continue

        series = [(w["label"], w["by_category"].get(cat, 0.0)) for w in closed_rows]
        spike = _find_spike(series)
        if spike:
            category_spikes.append({"category": cat, **spike})

    category_spikes.sort(key=lambda s: -s["ratio"])

    return {
        "available": True,
        "date_from": start.isoformat(),
        "date_to": end.isoformat(),
        "categories": categories,
        "weeks": week_rows,
        "weeks_closed_count": len(closed_rows),
        "category_spikes": category_spikes,
        "total_spike": total_spike,
        "grand_total": grand_total,
        "grand_total_all": grand_total_all,
    }


def build_review_data(report_date: date) -> tuple[dict, dict | None]:
    """
    Возвращает (payload, fbs).

    Порядок важен: сначала закрываем соединения сводки,
    потом открываем срез FBS. DuckDB не любит двух писателей
    одновременно, и параллельные подключения к одному файлу
    здесь ничего не ускоряют.
    """
    payload = build_review_payload(report_date)

    # Разрезы считаются отдельно и не должны ронять отчёт.
    try:
        payload["mix"] = build_mix_slices(report_date)
    except Exception:
        payload["mix"] = {"available": False, "brands": [], "categories": []}

    try:
        payload["wb_expenses"] = build_wb_expenses_slice(report_date)
    except Exception:
        payload["wb_expenses"] = {"available": False, "weeks": [], "categories": []}

    fbs = build_fbs_slice(report_date)

    return payload, fbs
