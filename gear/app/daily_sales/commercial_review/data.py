# gear/app/daily_sales/commercial_review/data.py
"""
Сбор данных для коммерческого обзора.

Своих запросов здесь нет: обзор берёт уже собранный payload
ежедневной сводки и оперативный срез заказов FBS. Дублировать
расчёты нельзя — иначе в двух отчётах появятся две разные
«выручки», и доверие к обоим кончится.
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

    fbs = build_fbs_slice(report_date)

    return payload, fbs
