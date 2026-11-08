# gear/app/daily_sales/assistant/ops.py
"""Операционные отчёты помощника: происшествия на складах WB и заказы FBS.

Расчёты не дублируются — берутся те же функции, что в дашбордах остатков и FBS.
"""
from __future__ import annotations

from datetime import date, timedelta


def _d(v, default=None):
    return date.fromisoformat(str(v)[:10]) if v else default


def _f(v, d=0):
    try:
        return f"{float(v or 0):,.{d}f}".replace(",", " ")
    except (TypeError, ValueError):
        return "—"


# ---------------------------------------------------------------- происшествия
def incidents_report(warehouse=None) -> str:
    """Реестр происшествий (пожары и др.) и оценка товара на складе на день до события."""
    from ..stocks.dashboard_data import get_warehouse_incident_snapshot
    from ..stocks.dashboard_stock.warehouse_incidents import WAREHOUSE_INCIDENTS

    events = []
    for wh, items in WAREHOUSE_INCIDENTS.items():
        if warehouse and str(warehouse).strip().lower() not in wh.lower():
            continue
        for it in items:
            day = _d(it.get("date"))
            if day is None:
                continue
            try:
                snap = get_warehouse_incident_snapshot(
                    warehouse_name=wh,
                    incident_date=(day - timedelta(days=1)).isoformat()) or {}
            except Exception as e:                    # реестр показываем и без оценки
                snap = {"error": f"{type(e).__name__}: {e}"[:120]}
            events.append((day, wh, it, snap))
    if not events:
        return ("Происшествий по такому складу в реестре нет." if warehouse
                else "Реестр происшествий на складах пуст.")
    events.sort(key=lambda x: (x[0], x[1]))

    lines = [f"ПРОИСШЕСТВИЯ НА СКЛАДАХ WB: {len(events)}",
             "Дата\tСклад\tСобытие\tОстаток на складе, шт\tКарточек\t"
             "Бух. стоимость, ₽\tУпр. стоимость, ₽\tОстаток на дату"]
    tot = {"qty": 0, "buh": 0.0, "man": 0.0}
    gaps = []
    for day, wh, it, s in events:
        if s.get("error"):
            lines.append(f"{day:%d.%m.%Y}\t{wh}\t{it.get('title', 'Происшествие')}\t"
                         f"оценка недоступна ({s['error']})")
            continue
        eff = _d(s.get("effective_date"))
        lines.append(f"{day:%d.%m.%Y}\t{wh}\t{it.get('title', 'Происшествие')}\t"
                     f"{_f(s.get('on_hand'))}\t{_f(s.get('nm_count'))}\t"
                     f"{_f(s.get('accounting_cost'))}\t{_f(s.get('management_cost'))}\t"
                     + (f"{eff:%d.%m.%Y}" if eff else "—"))
        tot["qty"] += int(s.get("on_hand") or 0)
        tot["buh"] += float(s.get("accounting_cost") or 0)
        tot["man"] += float(s.get("management_cost") or 0)
        if s.get("no_accounting_cost_qty") or s.get("no_management_cost_qty"):
            gaps.append(f"{wh}: без бух. себестоимости {_f(s.get('no_accounting_cost_qty'))} "
                        f"шт, без упр. — {_f(s.get('no_management_cost_qty'))} шт")
    lines.append(f"ИТОГО\t\t\t{_f(tot['qty'])}\t\t{_f(tot['buh'])}\t{_f(tot['man'])}")
    if gaps:
        lines.append("Не оценено (нет себестоимости): " + "; ".join(gaps))
    lines.append("Методика: физический остаток склада на конец дня ПЕРЕД происшествием, "
                 "без товаров в пути; себестоимость без НДС — по приходным УПД. Это оценка "
                 "товара на складе, а не подтверждённый ущерб и не сумма компенсации WB. "
                 "Реестр ведётся вручную.")
    return "\n".join(lines)


# ---------------------------------------------------------------- заказы FBS
def fbs_orders_report(date_from=None, date_to=None, brand=None, view="summary",
                      top=20) -> str:
    """Заказы FBS: сколько на сборке, сколько за нормативом WB, сроки, отмены."""
    from ..fbs_orders.config import SLA_LIMIT_HOURS
    from ..fbs_orders.data import collect_fbs_analysis
    from ..fbs_orders.insights import assembly_insights, daily_insights

    end = _d(date_to, date.today() - timedelta(days=1))
    start = _d(date_from, end - timedelta(days=29))
    top = max(1, min(int(top or 20), 60))
    p = collect_fbs_analysis(start=start, end=end,
                             brand_list=[brand] if brand else None)
    k = p.get("kpi") or {}
    if not k.get("orders_total"):
        return f"Заказов FBS за {start:%d.%m.%Y}–{end:%d.%m.%Y} нет."
    in_work, overdue = int(k.get("orders_in_work") or 0), int(k.get("orders_overdue") or 0)
    in_time = 100 * (in_work - overdue) / in_work if in_work else None
    as_of = p.get("as_of")
    lines = [
        f"ЗАКАЗЫ FBS за {start:%d.%m.%Y}–{end:%d.%m.%Y}"
        + (f", бренд «{brand}»" if brand else "")
        + (f"; данные на {as_of:%d.%m.%Y %H:%M}" if hasattr(as_of, "strftime") else ""),
        "Показатель\tЗначение",
        f"Всего заказов\t{_f(k.get('orders_total'))}",
        f"Собрано и передано (закрыто)\t{_f(k.get('orders_closed'))}",
        f"Отменено\t{_f(k.get('orders_cancelled'))}",
        f"Сейчас на сборке\t{_f(in_work)}",
        f"Из них за нормативом WB ({SLA_LIMIT_HOURS} ч)\t{_f(overdue)}",
        "Доля заказов на сборке в нормативе\t"
        + (f"{_f(in_time, 1)}%" if in_time is not None else "на сборке заказов нет"),
        f"Средний возраст заказа на сборке, ч\t{_f(k.get('avg_age_in_work'), 1)}",
        f"Самый старый заказ на сборке, ч\t{_f(k.get('max_age_in_work'), 1)}",
        f"Среднее время до закрытия поставки, ч\t{_f(k.get('avg_hours_to_close'), 1)}",
        f"Сумма заказов, ₽\t{_f(k.get('amount'))}",
        f"Поставок\t{_f(k.get('supplies_total'))}; карточек\t{_f(k.get('nm_count'))}",
    ]
    b = p.get("buckets_in_work")
    if b is not None and not b.empty:
        lines.append("\nСЕЙЧАС НА СБОРКЕ — по времени ожидания")
        lines.append("Сколько ждёт\tЗаказов\tДоля, %\tСредний срок, ч")
        for r in b.itertuples():
            lines.append(f"{r.time_group}\t{_f(r.orders)}\t{_f(r.share_pct, 1)}\t"
                         f"{_f(r.avg_hours, 1)}")
    notes = (assembly_insights(b, k) if b is not None else []) + \
        (daily_insights(p.get("daily")) if view == "daily" else [])
    if notes:
        lines.append("\nВЫВОДЫ: " + " ".join(notes))
    o = p.get("overdue")
    if view == "overdue" and o is not None and not o.empty:
        lines.append(f"\nПРОСРОЧЕННЫЕ ЗАКАЗЫ (первые {min(top, len(o))} из {len(o)})")
        lines.append("Заказ\tСоздан\tВисит, ч\tАртикул\tБренд\tСумма, ₽")
        for r in o.head(top).itertuples():
            created = r.created_at.strftime("%d.%m %H:%M") if hasattr(
                r.created_at, "strftime") else str(r.created_at)[:16]
            lines.append(f"{r.order_id}\t{created}\t{_f(r.age_hours, 1)}\t{r.article or ''}\t"
                         f"{r.brand or ''}\t{_f(r.amount)}")
    d = p.get("daily")
    if view == "daily" and d is not None and not d.empty:
        lines.append("\nПО ДНЯМ (последние 14)")
        lines.append("Дата\tЗаказов\tОтменено\tЗакрыто")
        for r in d.sort_values("order_date").tail(14).itertuples():
            day = r.order_date.strftime("%d.%m.%Y") if hasattr(
                r.order_date, "strftime") else str(r.order_date)[:10]
            lines.append(f"{day}\t{_f(r.orders)}\t{_f(r.cancelled_orders)}\t"
                         f"{_f(r.closed_orders)}")
    lines.append(f"Норматив: WB даёт {SLA_LIMIT_HOURS} часов на сборку заказа FBS; возраст "
                 "заказа считается на момент выгрузки данных. Период — по дате создания "
                 "заказа. Планов продаж в данных нет — «выполнение» здесь означает "
                 "соблюдение норматива сборки.")
    return "\n".join(lines)
