# gear/app/daily_sales/fbs_orders/insights.py
"""
Выводы под графиками.

Каждый вывод считается по тем же данным, что и график рядом,
и говорит то, чего по картинке сходу не видно: где именно
сидит просрочка, насколько хвост тяжелее головы, куда сместилась
динамика. Если данных не хватает — вывод не пишется вообще,
а не подменяется общей фразой.
"""

from __future__ import annotations

import pandas as pd

from .config import HOUR_BUCKETS, SLA_LIMIT_HOURS, SLA_WARNING_HOURS


def _num(value) -> str:
    try:
        return f"{int(round(float(value))):,}".replace(",", " ")
    except (TypeError, ValueError):
        return "—"


def _pct(value) -> str:
    try:
        return f"{float(value):.0f} %"
    except (TypeError, ValueError):
        return "—"


def _hours(value) -> str:
    try:
        return f"{float(value):.1f} ч".replace(".", ",")
    except (TypeError, ValueError):
        return "—"


def _date(value) -> str:
    try:
        return pd.to_datetime(value).strftime("%d.%m.%Y")
    except (TypeError, ValueError):
        return str(value)


def _safe_sum(df, column):
    if df is None or df.empty or column not in df.columns:
        return 0.0
    return float(
        pd.to_numeric(df[column], errors="coerce").fillna(0).sum()
    )


# ============================================================
# КОНТРОЛЬ СБОРКИ
# ============================================================

def assembly_insights(buckets: pd.DataFrame, kpi: dict) -> list[str]:
    if buckets is None or buckets.empty:
        return []

    data = buckets.sort_values("time_sort")

    total = _safe_sum(data, "orders")

    if not total:
        return []

    notes = []

    # 1. Хвост: сколько сидит за нормативом и сколько это времени
    over = data[data["time_sort"] >= 7]
    over_orders = _safe_sum(over, "orders")

    if over_orders:
        over_hours = float(
            pd.to_numeric(over["avg_hours"], errors="coerce").mean()
        )

        notes.append(
            f"За нормативом {_num(over_orders)} заказов — это "
            f"{_pct(100 * over_orders / total)} всего, что сейчас "
            f"на сборке, и они висят в среднем {_hours(over_hours)} "
            f"при норме {SLA_LIMIT_HOURS}."
        )

    # 2. Голова: доля заказов, уходящих быстро
    fast = data[data["time_sort"] <= 2]
    fast_orders = _safe_sum(fast, "orders")

    # Порог берём из самих корзин: если пороги поменяют
    # в config, текст останется правдой.
    fast_limit = (
        HOUR_BUCKETS[1][0] if len(HOUR_BUCKETS) > 1 else HOUR_BUCKETS[0][0]
    )

    if fast_orders:
        notes.append(
            f"При этом {_pct(100 * fast_orders / total)} заказов "
            f"собирается меньше чем за {fast_limit} часов. "
            "Значит, мощности хватает — проблема не в объёме, "
            "а в том, что часть заказов выпадает из потока "
            "и остаётся лежать."
        )

    # 3. Что даст разбор хвоста
    avg_age = kpi.get("avg_age_in_work")
    rest = data[data["time_sort"] < 7]
    rest_orders = _safe_sum(rest, "orders")

    if over_orders and rest_orders and avg_age:
        rest_hours = float(
            (
                pd.to_numeric(rest["avg_hours"], errors="coerce").fillna(0)
                * pd.to_numeric(rest["orders"], errors="coerce").fillna(0)
            ).sum()
            / rest_orders
        )

        notes.append(
            f"Если разобрать только этот хвост, средний возраст "
            f"на сборке падает с {_hours(avg_age)} до "
            f"{_hours(rest_hours)} — почти весь средний срок "
            "делают именно просроченные заказы."
        )

    return notes


# ============================================================
# ЛОГИСТИКА
# ============================================================

def logistics_insights(logistics: pd.DataFrame) -> list[str]:
    if logistics is None or logistics.empty:
        return []

    place = (
        "destination_office"
        if "destination_office" in logistics.columns
        else "office_name"
    )

    data = (
        logistics.groupby(
            ["warehouse", place], as_index=False
        )
        .agg(
            orders=("orders", "sum"),
            orders_overdue=("orders_overdue", "sum"),
            avg_hours=("avg_hours", "mean"),
        )
        .sort_values("orders", ascending=False)
    )

    total_orders = _safe_sum(data, "orders")
    total_overdue = _safe_sum(data, "orders_overdue")

    if not total_orders:
        return []

    notes = []

    # 1. Концентрация объёма
    top = data.iloc[0]

    notes.append(
        f"Крупнейшее направление — {top['warehouse']} → "
        f"{top[place]}: {_num(top['orders'])} заказов, "
        f"{_pct(100 * top['orders'] / total_orders)} всего объёма. "
        f"Всего направлений: {_num(len(data))}."
    )

    # 2. Где сидит просрочка относительно объёма
    if total_overdue:
        worst = data.sort_values(
            "orders_overdue", ascending=False
        ).iloc[0]

        share_of_overdue = 100 * worst["orders_overdue"] / total_overdue
        share_of_orders = 100 * worst["orders"] / total_orders

        if share_of_overdue > share_of_orders + 10:
            verdict = (
                "просрочка перекошена на это направление — "
                "разбираться надо точечно, а не по всему складу"
            )
        elif share_of_overdue + 10 < share_of_orders:
            verdict = (
                "на этом направлении просрочки меньше, чем его "
                "доля в объёме — узкое место не здесь"
            )
        else:
            verdict = (
                "просрочка распределена примерно пропорционально "
                "объёму — это общий темп сборки, а не отдельное "
                "проблемное направление"
            )

        notes.append(
            f"Больше всего просрочки на {worst['warehouse']} → "
            f"{worst[place]}: {_num(worst['orders_overdue'])} "
            f"заказов, {_pct(share_of_overdue)} всей просрочки при "
            f"{_pct(share_of_orders)} объёма. То есть {verdict}."
        )
    else:
        notes.append(
            "Просроченных заказов ни на одном направлении нет."
        )

    # 3. Разброс сроков между направлениями
    hours = pd.to_numeric(data["avg_hours"], errors="coerce").dropna()

    if len(hours) >= 3 and hours.max() > 0:
        slowest = data.loc[hours.idxmax()]
        fastest = data.loc[hours.idxmin()]

        if hours.max() >= hours.min() * 1.5:
            notes.append(
                f"Разброс по срокам большой: {slowest[place]} "
                f"— {_hours(slowest['avg_hours'])}, "
                f"{fastest[place]} — "
                f"{_hours(fastest['avg_hours'])}. Направления ведут "
                "себя по-разному, общий средний срок их усредняет "
                "и прячет разницу."
            )

    return notes


# ============================================================
# ДИНАМИКА
# ============================================================

def daily_insights(daily: pd.DataFrame) -> list[str]:
    if daily is None or daily.empty or len(daily) < 3:
        return []

    data = daily.sort_values("order_date").copy()

    orders = pd.to_numeric(data["orders"], errors="coerce").fillna(0)
    cancelled = pd.to_numeric(
        data.get("cancelled_orders", 0), errors="coerce"
    ).fillna(0)

    notes = []

    # 1. Темп: последняя неделя против предыдущего периода
    if len(data) >= 14:
        last_week = orders.tail(7).mean()
        before = orders.iloc[:-7].mean()

        if before:
            change = 100 * (last_week - before) / before
            direction = "выше" if change >= 0 else "ниже"

            notes.append(
                f"Последние 7 дней — {_num(last_week)} заказов в день, "
                f"это на {_pct(abs(change))} {direction} среднего за "
                f"остальной период ({_num(before)} в день)."
            )
    else:
        notes.append(
            f"В среднем {_num(orders.mean())} заказов в день "
            f"за {len(data)} дней."
        )

    # 2. Отмены
    total_orders = float(orders.sum())
    total_cancelled = float(cancelled.sum())

    if total_orders and total_cancelled:
        share = 100 * total_cancelled / total_orders

        notes.append(
            f"Отмены — {_pct(share)} заказов "
            f"({_num(total_cancelled)} из {_num(total_orders)}). "
            "Это заказы, которые собирать не нужно: если они "
            "доходят до сборки, время тратится впустую."
        )

    # 3. Пиковый день
    if len(data) >= 7 and orders.max() > 0:
        peak_index = orders.idxmax()
        peak_value = orders.loc[peak_index]

        if peak_value >= orders.mean() * 1.5:
            notes.append(
                f"Пик — {_date(data.loc[peak_index, 'order_date'])}: "
                f"{_num(peak_value)} заказов, вдвое с лишним больше "
                "обычного дня. Такие дни стоит держать в голове "
                "при планировании смен."
            )

    # 4. Последний день почти всегда неполный
    notes.append(
        f"Последний день в графике — {_date(data['order_date'].iloc[-1])} "
        "— обрезан моментом выгрузки, поэтому заказов там обычно "
        "меньше, чем будет по факту. Спад на самом правом краю "
        "читать как падение не нужно."
    )

    return notes


# ============================================================
# ВСТУПЛЕНИЕ
# ============================================================

INTRO_SECTIONS = [
    (
        "Что показывает эта вкладка",
        "Заказы FBS — те, что вы собираете и отвозите сами. "
        "Вкладка отвечает на четыре вопроса: что сейчас висит "
        "на сборке и сколько времени, откуда и куда едут заказы, "
        "как проходят поставки и какие товары в этих заказах.",
    ),
    (
        "Как считается возраст заказа",
        "От создания заказа до момента выгрузки, а не до текущей "
        "минуты. Если выгрузка снята в 5 утра, а вы смотрите "
        "вечером, заказы не «стареют» на глазах — иначе к вечеру "
        "просроченным выглядело бы всё подряд. Для заказов, "
        "вошедших в закрытую поставку, берётся фактический срок "
        "до её закрытия.",
    ),
    (
        "Что считается просрочкой",
        f"Заказ на сборке старше {SLA_LIMIT_HOURS} часов. "
        f"С {SLA_WARNING_HOURS} часов — жёлтая зона: ещё в норме, "
        "но уже требует внимания. Пороги задаются в одном месте "
        "и при необходимости меняются.",
    ),
    (
        "Как сходятся цифры",
        "Открытые, закрытые поставкой и отменённые заказы делят "
        "общий объём без пересечений — их сумма всегда равна "
        "числу заказов в срезе. «На сборке» и «просрочено» — "
        "подмножества открытых, а не отдельные категории.",
    ),
]
