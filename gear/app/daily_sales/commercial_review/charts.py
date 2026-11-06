# gear/app/daily_sales/commercial_review/charts.py
"""
Графики отчёта.

Рисуются matplotlib в SVG и вставляются в HTML как data-uri.
svg.fonttype = "path" превращает подписи в кривые: PDF не зависит
от шрифтов на сервере, а текст остаётся векторным и не мылится
при печати.

Правила одни на все графики:
  • у оси есть подпись и единица измерения;
  • значения подписаны прямо на элементах — чтобы не считать
    по сетке глазами;
  • не больше двух серий на одном графике;
  • сетка только горизонтальная и светлая;
  • рамки сверху и справа не рисуем;
  • если данных нет, функция возвращает None, и страница
    показывает честную заметку вместо пустой рамки.
"""

from __future__ import annotations

import base64
import io

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt

from matplotlib.ticker import FuncFormatter, MaxNLocator

from . import config as C
from .formats import as_date, month_number, num


# ============================================================
# ОБЩИЕ НАСТРОЙКИ
# ============================================================

matplotlib.rcParams.update({
    # Подписи превращаются в кривые: не нужен шрифт в системе.
    "svg.fonttype": "path",
    "font.family": "DejaVu Sans",
    "font.size": 7.4,
    "axes.linewidth": 0.6,
    "axes.edgecolor": C.AXIS,
    "axes.labelcolor": C.INK_2,
    "xtick.color": C.INK_2,
    "ytick.color": C.INK_2,
    "xtick.labelsize": 7.0,
    "ytick.labelsize": 7.0,
    "xtick.major.width": 0.5,
    "ytick.major.width": 0.5,
    "xtick.major.size": 2.0,
    "ytick.major.size": 2.0,
    "legend.frameon": False,
    "legend.fontsize": 7.2,
    "figure.dpi": 100,
    "savefig.transparent": True,
})


#: Ширина колонки контента, дюймы. A4 минус поля 16 мм.
FULL_W = 7.0
HALF_W = 3.38

NBSP = " "


# ============================================================
# ПОДПИСИ ЧИСЕЛ
# ============================================================

def _short(value, digits=None) -> str:
    """Компактное число для осей и подписей: 12,4 млн / 850 тыс."""
    v = num(value)
    if v is None:
        return "—"

    sign = "−" if v < 0 else ""
    a = abs(v)

    if a >= 1_000_000_000:
        return f"{sign}{a / 1_000_000_000:.2f}".replace(".", ",") + f"{NBSP}млрд"
    if a >= 1_000_000:
        d = 1 if digits is None else digits
        return f"{sign}{a / 1_000_000:.{d}f}".replace(".", ",") + f"{NBSP}млн"
    if a >= 10_000:
        return f"{sign}{a / 1_000:.0f}" + f"{NBSP}тыс"
    if a >= 1_000:
        return f"{sign}{a / 1_000:.1f}".replace(".", ",") + f"{NBSP}тыс"

    return f"{sign}{a:,.0f}".replace(",", NBSP)


def _short_signed(value) -> str:
    v = num(value)
    if v is None:
        return "—"
    return ("+" if v > 0 else "") + _short(v)


def _pct_label(value, digits=0) -> str:
    v = num(value)
    if v is None:
        return "—"
    return f"{v:.{digits}f}".replace(".", ",") + f"{NBSP}%"


def _money_formatter():
    return FuncFormatter(lambda x, _pos: _short(x))


def _pct_formatter(digits=0):
    return FuncFormatter(
        lambda x, _pos: f"{x:.{digits}f}".replace(".", ",") + "%"
    )


# ============================================================
# КАРКАС
# ============================================================

def _fig(width=FULL_W, height=2.5):
    fig, ax = plt.subplots(figsize=(width, height))

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(C.AXIS)
    ax.spines["bottom"].set_color(C.AXIS)

    ax.set_axisbelow(True)
    ax.yaxis.grid(True, color=C.GRID, linewidth=0.6)
    ax.xaxis.grid(False)

    ax.tick_params(length=2, pad=2)

    return fig, ax


def _render(fig) -> str:
    """Отдаёт готовый data-uri и закрывает фигуру."""
    buffer = io.BytesIO()

    fig.savefig(
        buffer,
        format="svg",
        bbox_inches="tight",
        pad_inches=0.02,
    )

    plt.close(fig)

    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")

    return f"data:image/svg+xml;base64,{encoded}"


def _thin(labels, target=12):
    """
    Оставляет не больше target подписей на оси X.

    Первая и последняя остаются всегда: без них непонятно,
    какой отрезок показан.
    """
    n = len(labels)
    if n <= target:
        return list(range(n))

    step = max(1, round(n / target))
    keep = list(range(0, n, step))

    if (n - 1) not in keep:
        # Последняя дата нужна всегда, но если предыдущая метка
        # стоит к ней вплотную, подписи налезут друг на друга.
        if keep and (n - 1) - keep[-1] < step * 0.6:
            keep.pop()
        keep.append(n - 1)

    return keep


def _legend(ax, ncol=2, y=1.06):
    ax.legend(
        loc="lower left",
        bbox_to_anchor=(0.0, y),
        ncol=ncol,
        handlelength=1.5,
        handletextpad=0.5,
        columnspacing=1.4,
        borderaxespad=0.0,
    )


def _headroom(ax, factor=1.18):
    """Место сверху под подписи значений."""
    low, high = ax.get_ylim()
    if high > 0:
        ax.set_ylim(low, high * factor)


# ============================================================
# 1. ВЫРУЧКА: ДИНАМИКА
# ============================================================

# def revenue_trend(rows, days=90, width=FULL_W, height=2.45):
#     """
#     Дневная выручка за период и её сглаженная линия.

#     Столбики — факт по дням, линия — среднее за 7 дней.
#     Одна только линия скрывает выходные провалы, одни только
#     столбики не показывают тренд: нужны оба слоя.
#     """
#     data = []

#     for row in rows or []:
#         d = as_date(row.get("date_from"))
#         v = num(row.get("net_amount"))
#         if d is None:
#             continue
#         data.append((d, v or 0.0))

#     if len(data) < 7:
#         return None

#     data.sort(key=lambda item: item[0])
#     data = data[-days:]

#     labels = [d.strftime("%d.%m") for d, _ in data]
#     values = [v for _, v in data]

#     # Среднее за 7 дней
#     ma = []
#     for i in range(len(values)):
#         window = values[max(0, i - 6): i + 1]
#         ma.append(sum(window) / len(window))

#     x = list(range(len(values)))

#     fig, ax = _fig(width, height)

#     ax.bar(
#         x,
#         values,
#         width=0.72,
#         color=C.TINT,
#         edgecolor=C.SERIES_1,
#         linewidth=0.35,
#         label="Выручка за день",
#     )

#     ax.plot(
#         x,
#         ma,
#         color=C.SERIES_1,
#         linewidth=1.7,
#         label="Среднее за день по последним 7 дням",
#     )

#     # Подписываем только последнее значение сглаженной линии:
#     # оно и есть текущий темп.
#     # Без единицы это число читают как выручку последнего дня.
#     ax.annotate(
#         f"{_short(ma[-1])} ₽ в день",
#         xy=(x[-1], ma[-1]),
#         xytext=(-2, 7),
#         textcoords="offset points",
#         ha="right",
#         color=C.SERIES_1,
#         fontweight="bold",
#         fontsize=7.4,
#     )

#     keep = _thin(labels, 14)
#     ax.set_xticks([x[i] for i in keep])
#     ax.set_xticklabels([labels[i] for i in keep])

#     ax.yaxis.set_major_formatter(_money_formatter())
#     ax.set_ylabel("Выручка, ₽")
#     ax.set_xlim(-0.8, len(values) - 0.2)
#     _headroom(ax, 1.14)
#     _legend(ax, ncol=2)

#     return _render(fig)





def revenue_trend(rows, days=90, width=FULL_W, height=2.45):
    """
    Дневная выручка за период и её сглаженная линия.

    Столбики — факт по дням, линия — среднее за 7 дней.
    Максимальный и минимальный дни выделены цветом.
    """
    data = []

    for row in rows or []:
        d = as_date(row.get("date_from"))
        v = num(row.get("net_amount"))

        if d is None:
            continue

        data.append((d, v or 0.0))

    if len(data) < 7:
        return None

    data.sort(key=lambda item: item[0])
    data = data[-days:]

    labels = [d.strftime("%d.%m") for d, _ in data]
    values = [v for _, v in data]
    x = list(range(len(values)))

    # Максимальный и минимальный дни за показанный период
    max_idx = max(range(len(values)), key=lambda i: values[i])
    min_idx = min(range(len(values)), key=lambda i: values[i])

    # Среднее за 7 дней
    ma = []

    for i in range(len(values)):
        window = values[max(0, i - 6):i + 1]
        ma.append(sum(window) / len(window))

    fig, ax = _fig(width, height)

    bars = ax.bar(
        x,
        values,
        width=0.72,
        color=C.TINT,
        edgecolor=C.SERIES_1,
        linewidth=0.35,
        label="Выручка за день",
    )

    # Выделяем только максимальный и минимальный столбики
    bars[max_idx].set_facecolor(C.GOOD)
    bars[max_idx].set_edgecolor(C.GOOD)

    bars[min_idx].set_facecolor(C.CRITICAL)
    bars[min_idx].set_edgecolor(C.CRITICAL)

    ax.plot(
        x,
        ma,
        color=C.SERIES_1,
        linewidth=1.7,
        label="Среднее за день по последним 7 дням",
    )

    # Максимальная выручка
    ax.annotate(
        f"Максимум\n{labels[max_idx]} · {_short(values[max_idx])} ₽",
        xy=(x[max_idx], values[max_idx]),
        xytext=(0, 8),
        textcoords="offset points",
        ha="center",
        va="bottom",
        color=C.GOOD,
        fontweight="bold",
        fontsize=6.8,
        linespacing=1.25,
    )

    # Минимальная выручка
    ax.annotate(
        f"Минимум\n{labels[min_idx]} · {_short(values[min_idx])} ₽",
        xy=(x[min_idx], values[min_idx]),
        xytext=(0, 8),
        textcoords="offset points",
        ha="center",
        va="bottom",
        color=C.CRITICAL,
        fontweight="bold",
        fontsize=6.8,
        linespacing=1.25,
    )

    # Последнее значение сглаженной линии — текущий темп
    ax.annotate(
        f"{_short(ma[-1])} ₽ в день",
        xy=(x[-1], ma[-1]),
        xytext=(-2, 7),
        textcoords="offset points",
        ha="right",
        color=C.SERIES_1,
        fontweight="bold",
        fontsize=7.4,
    )

    keep = _thin(labels, 14)
    ax.set_xticks([x[i] for i in keep])
    ax.set_xticklabels([labels[i] for i in keep])

    ax.yaxis.set_major_formatter(_money_formatter())
    ax.set_ylabel("Выручка, ₽")
    ax.set_xlim(-0.8, len(values) - 0.2)

    # Чуть больше свободного места сверху для подписи максимума
    _headroom(ax, 1.22)

    _legend(ax, ncol=2)

    return _render(fig)


def revenue_vs_last_year(rows, width=FULL_W, height=2.3):
    """
    Накопленная выручка с начала года против прошлого года.

    Накопленным итогом, а не по дням: так видно, разрыв
    копится или уже наверстан.
    """
    by_year = {}

    for row in rows or []:
        d = as_date(row.get("date_from"))
        v = num(row.get("amount"))
        if d is None:
            continue
        by_year.setdefault(d.year, []).append((d, v or 0.0))

    if len(by_year) < 2:
        return None

    years = sorted(by_year)
    previous_year, current_year = years[-2], years[-1]

    def cumulative(year):
        items = sorted(by_year[year], key=lambda p: p[0])
        total = 0.0
        out = []
        for d, v in items:
            total += v
            out.append((d.timetuple().tm_yday, total))
        return out

    cur = cumulative(current_year)
    prev = cumulative(previous_year)

    if not cur or not prev:
        return None

    fig, ax = _fig(width, height)

    ax.plot(
        [p[0] for p in prev],
        [p[1] for p in prev],
        color=C.SERIES_2,
        linewidth=1.5,
        linestyle="--",
        label=f"{previous_year} год",
    )

    ax.plot(
        [p[0] for p in cur],
        [p[1] for p in cur],
        color=C.SERIES_1,
        linewidth=1.9,
        label=f"{current_year} год",
    )

    for series, color, dy in (
        (cur, C.SERIES_1, 8),
        (prev, C.SERIES_2, -12),
    ):
        ax.annotate(
            _short(series[-1][1]),
            xy=series[-1],
            xytext=(-3, dy),
            textcoords="offset points",
            ha="right",
            color=color,
            fontweight="bold",
        )

    month_starts = [1, 32, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    month_labels = [
        "янв", "фев", "мар", "апр", "май", "июн",
        "июл", "авг", "сен", "окт", "ноя", "дек",
    ]

    last_day = max(cur[-1][0], prev[-1][0])
    keep = [i for i, start in enumerate(month_starts) if start <= last_day + 10]

    ax.set_xticks([month_starts[i] for i in keep])
    ax.set_xticklabels([month_labels[i] for i in keep])

    ax.yaxis.set_major_formatter(_money_formatter())
    ax.set_ylabel("Накопленная выручка, ₽")
    ax.set_ylim(bottom=0)
    _legend(ax, ncol=2)

    return _render(fig)


# ============================================================
# 2. РАЗЛОЖЕНИЕ ИЗМЕНЕНИЯ ВЫРУЧКИ
# ============================================================

def revenue_waterfall(split, width=FULL_W, height=2.6,
                      prev_label=None, cur_label=None):
    """
    Из чего сложилось изменение чистой выручки.

    Слева выручка прошлой недели, справа текущей, между ними
    три столбика: количество, цена и возвраты. Их сумма точно
    равна разнице — картинку можно показывать коммерческой
    команде без оговорок.

    prev_label / cur_label — готовые подписи для крайних
    столбиков (обычно с датами периода, чтобы не гадать,
    какая именно неделя на графике). Без них — старые общие
    подписи "Прошлая неделя" / "Текущая неделя".
    """
    if not split:
        return None

    base = num(split.get("previous", {}).get("amount"))
    qty_effect = num(split.get("qty_effect"))
    price_effect = num(split.get("price_effect"))
    returns_effect = num(split.get("returns_effect"))
    final = num(split.get("current", {}).get("amount"))

    if None in (base, qty_effect, price_effect, returns_effect, final):
        return None

    fig, ax = _fig(width, height)

    labels = [
        prev_label or "Прошлая\nнеделя",
        "Количество",
        "Средняя\nцена",
        "Возвраты",
        cur_label or "Текущая\nнеделя",
    ]

    running = base
    bars = [(0, 0.0, base, C.MUTED, _short(base))]

    for index, effect in (
        (1, qty_effect),
        (2, price_effect),
        (3, returns_effect),
    ):
        bottom = running if effect >= 0 else running + effect
        color = C.GOOD if effect >= 0 else C.CRITICAL
        bars.append((index, bottom, abs(effect), color, _short_signed(effect)))
        running += effect

    bars.append((4, 0.0, final, C.SERIES_1, _short(final)))

    for index, bottom, height_value, color, label in bars:
        ax.bar(
            index,
            height_value,
            bottom=bottom,
            width=0.54,
            color=color,
            edgecolor="none",
        )

        ax.annotate(
            label,
            xy=(index, bottom + height_value),
            xytext=(0, 4),
            textcoords="offset points",
            ha="center",
            color=C.INK,
            fontweight="bold",
            fontsize=7.4,
        )

    # Соединительные линии: видно, что столбики продолжают друг друга.
    connect = [
        base,
        base + qty_effect,
        base + qty_effect + price_effect,
        base + qty_effect + price_effect + returns_effect,
    ]

    for index, level in enumerate(connect):
        ax.plot(
            [index + 0.27, index + 0.73],
            [level, level],
            color=C.LINE,
            linewidth=0.7,
            linestyle=(0, (2, 2)),
        )

    ax.set_xticks(range(5))
    ax.set_xticklabels(labels)
    ax.yaxis.set_major_formatter(_money_formatter())
    ax.set_ylabel("Чистая выручка за неделю, ₽")
    ax.set_ylim(bottom=0)
    _headroom(ax, 1.16)

    return _render(fig)


def revenue_change_trend(weeks, width=FULL_W, height=1.9):
    """
    Изменение чистой выручки к тому же отрезку прошлой недели,
    по нескольким последним неделям (см. decompose_weeks).

    Отвечает на вопрос "разовый скачок или тренд": один
    столбик над нулём или под ним ничего не говорит сам
    по себе, а несколько подряд в одну сторону — уже
    закономерность, а не шум. Недели без полных 7 дней
    (текущая, ещё не закрытая) рисуем серым — их высота
    не сравнима напрямую с полными неделями.
    """
    rows = [w for w in (weeks or []) if w.get("total") is not None]
    if len(rows) < 2:
        return None

    labels = [w["label"] for w in rows]
    values = [w["total"] for w in rows]
    full = [bool(w.get("full")) for w in rows]
    x = list(range(len(rows)))

    fig, ax = _fig(width, height)

    colors = [
        (C.GOOD if v >= 0 else C.CRITICAL) if f else C.LINE
        for v, f in zip(values, full)
    ]

    ax.bar(x, values, width=0.55, color=colors, linewidth=0)
    ax.axhline(0, color=C.AXIS, linewidth=0.6)

    for i, v in enumerate(values):
        ax.annotate(
            _short_signed(v),
            xy=(x[i], v),
            xytext=(0, 3 if v >= 0 else -11),
            textcoords="offset points",
            ha="center",
            va="bottom" if v >= 0 else "top",
            fontsize=7.0,
            fontweight="bold",
            color=C.INK if full[i] else C.MUTED,
        )

    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_xlim(-0.6, len(rows) - 0.4)
    ax.margins(y=0.22)

    ax.yaxis.set_major_formatter(_money_formatter())
    ax.set_ylabel("Изменение выручки, ₽")

    return _render(fig)


def qty_price_pair(rows, days=60, width=FULL_W, height=2.4):
    """
    Количество и средняя цена на одном поле.

    Две оси, потому что единицы разные. Смысл картинки — увидеть,
    расходятся линии или идут вместе: если цена вниз, а количество
    не вверх, скидка не сработала.
    """
    data = []

    for row in rows or []:
        d = as_date(row.get("date_from"))
        q = num(row.get("sales_qty"))
        p = num(row.get("avg_price"))
        if d is None or q is None or p is None:
            continue
        data.append((d, q, p))

    if len(data) < 10:
        return None

    data.sort(key=lambda item: item[0])
    data = data[-days:]

    labels = [d.strftime("%d.%m") for d, _, _ in data]
    x = list(range(len(data)))

    fig, ax = _fig(width, height)

    ax.bar(
        x,
        [q for _, q, _ in data],
        width=0.7,
        color=C.TINT,
        edgecolor=C.SERIES_1,
        linewidth=0.35,
        label="Продано, шт.",
    )

    ax.set_ylabel("Продано, шт.")
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _p: _short(v)))
    ax.set_xlim(-0.8, len(data) - 0.2)

    ax2 = ax.twinx()
    ax2.spines["top"].set_visible(False)
    ax2.spines["left"].set_visible(False)
    ax2.spines["right"].set_color(C.AXIS)
    ax2.grid(False)
    ax2.tick_params(length=2, pad=2, colors=C.INK_2)

    ax2.plot(
        x,
        [p for _, _, p in data],
        color=C.SERIES_2,
        linewidth=1.8,
        label="Средняя цена, ₽",
    )

    ax2.set_ylabel("Средняя цена, ₽", color=C.SERIES_2)
    ax2.yaxis.set_major_formatter(_money_formatter())
    ax2.tick_params(axis="y", labelcolor=C.SERIES_2)

    keep = _thin(labels, 12)
    ax.set_xticks([x[i] for i in keep])
    ax.set_xticklabels([labels[i] for i in keep])

    handles = ax.get_legend_handles_labels()
    handles2 = ax2.get_legend_handles_labels()

    ax.legend(
        handles[0] + handles2[0],
        handles[1] + handles2[1],
        loc="lower left",
        bbox_to_anchor=(0.0, 1.04),
        ncol=2,
        handlelength=1.5,
        handletextpad=0.5,
        columnspacing=1.4,
        borderaxespad=0.0,
    )

    return _render(fig)


# ============================================================
# 3. ПЛАН
# ============================================================

def plan_months(rows, width=FULL_W, height=2.6):
    """
    План и факт по месяцам года плюс накопленное выполнение.

    Столбики рядом, а не друг на друге: сравнивать высоту
    двух соседних столбиков глазом проще, чем вычитать.
    """
    data = [
        row for row in (rows or [])
        if num(row.get("plan")) or num(row.get("fact"))
    ]

    if not data:
        return None

    labels = [row.get("month_short") or str(row.get("month")) for row in data]
    plan = [num(row.get("plan")) or 0.0 for row in data]
    fact = [num(row.get("fact")) or 0.0 for row in data]
    running = [num(row.get("running_exec_pct")) for row in data]

    x = list(range(len(data)))
    offset = 0.2

    fig, ax = _fig(width, height)

    ax.bar(
        [i - offset for i in x],
        plan,
        width=0.38,
        color=C.LINE_SOFT,
        edgecolor=C.MUTED,
        linewidth=0.4,
        label="План",
    )

    colors = [
        C.SERIES_1 if f >= p else C.SERIOUS
        for f, p in zip(fact, plan)
    ]

    ax.bar(
        [i + offset for i in x],
        fact,
        width=0.38,
        color=colors,
        edgecolor="none",
        label="Факт",
    )

    for i, (f, p) in enumerate(zip(fact, plan)):
        if not f:
            continue
        ax.annotate(
            _short(f, digits=1),
            xy=(i + offset, f),
            xytext=(0, 3),
            textcoords="offset points",
            ha="center",
            fontsize=6.4,
            color=C.INK_2,
            rotation=90,
        )

    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.yaxis.set_major_formatter(_money_formatter())
    ax.set_ylabel("Выручка, ₽")
    _headroom(ax, 1.30)

    if any(v is not None for v in running):
        ax2 = ax.twinx()
        ax2.spines["top"].set_visible(False)
        ax2.spines["left"].set_visible(False)
        ax2.spines["right"].set_color(C.AXIS)
        ax2.grid(False)

        ax2.plot(
            x,
            [v if v is not None else float("nan") for v in running],
            color=C.SERIES_2,
            linewidth=1.6,
            marker="o",
            markersize=2.6,
            label="Выполнение накопленно, %",
        )

        ax2.axhline(100, color=C.LINE, linewidth=0.8, linestyle=(0, (3, 3)))
        ax2.set_ylabel("Выполнение накопленно, %", color=C.SERIES_2)
        ax2.yaxis.set_major_formatter(_pct_formatter())
        ax2.tick_params(axis="y", labelcolor=C.SERIES_2, length=2, pad=2)

        handles = ax.get_legend_handles_labels()
        handles2 = ax2.get_legend_handles_labels()

        ax.legend(
            handles[0] + handles2[0],
            handles[1] + handles2[1],
            loc="lower left",
            bbox_to_anchor=(0.0, 1.03),
            ncol=3,
            handlelength=1.5,
            handletextpad=0.5,
            columnspacing=1.4,
            borderaxespad=0.0,
        )
    else:
        _legend(ax, ncol=2)

    return _render(fig)


def plan_month_pace(rows, width=FULL_W, height=2.3):
    """
    Темп внутри месяца: накопленный факт против накопленного плана.

    Разрыв между линиями — это и есть отставание в рублях
    на каждый день, а не только на конец месяца.
    """
    data = [
        row for row in (rows or [])
        if num(row.get("running_plan")) or num(row.get("running_fact"))
    ]

    if len(data) < 3:
        return None

    labels = [
        row.get("date_label") or (as_date(row.get("date")) or "").__str__()[-5:]
        for row in data
    ]

    plan = [num(row.get("running_plan")) or 0.0 for row in data]
    fact = [num(row.get("running_fact")) or 0.0 for row in data]
    x = list(range(len(data)))

    fig, ax = _fig(width, height)

    ax.fill_between(
        x,
        fact,
        plan,
        where=[f < p for f, p in zip(fact, plan)],
        color=C.CRITICAL,
        alpha=0.10,
        linewidth=0,
        interpolate=True,
    )

    ax.fill_between(
        x,
        fact,
        plan,
        where=[f >= p for f, p in zip(fact, plan)],
        color=C.GOOD,
        alpha=0.10,
        linewidth=0,
        interpolate=True,
    )

    ax.plot(
        x, plan,
        color=C.MUTED,
        linewidth=1.4,
        linestyle="--",
        label="План накопленно",
    )

    ax.plot(
        x, fact,
        color=C.SERIES_1,
        linewidth=1.9,
        label="Факт накопленно",
    )

    gap = fact[-1] - plan[-1]

    ax.annotate(
        f"{_short_signed(gap)} к плану",
        xy=(x[-1], fact[-1]),
        xytext=(-4, 8 if gap >= 0 else -14),
        textcoords="offset points",
        ha="right",
        fontweight="bold",
        color=C.GOOD if gap >= 0 else C.CRITICAL,
    )

    keep = _thin(labels, 12)
    ax.set_xticks([x[i] for i in keep])
    ax.set_xticklabels([labels[i] for i in keep])

    ax.yaxis.set_major_formatter(_money_formatter())
    ax.set_ylabel("Накопленно за месяц, ₽")
    ax.set_ylim(bottom=0)
    _legend(ax, ncol=2)

    return _render(fig)


def forecast_months(rows, width=FULL_W, height=2.5):
    """
    Ожидаемый итог года против плана.

    Закрытые месяцы — факт, будущие — прогноз, поверх план
    линией. Видно, в каких месяцах разрыв, а не только итог.
    """
    data = [row for row in (rows or []) if row.get("month")]

    if not data:
        return None

    month_labels = {
        1: "янв", 2: "фев", 3: "мар", 4: "апр", 5: "май", 6: "июн",
        7: "июл", 8: "авг", 9: "сен", 10: "окт", 11: "ноя", 12: "дек",
    }

    labels = [
        month_labels.get(month_number(row.get("month")), "")
        for row in data
    ]
    fact = [num(row.get("fact")) or 0.0 for row in data]
    forecast = [num(row.get("forecast")) or 0.0 for row in data]
    plan = [num(row.get("plan")) or 0.0 for row in data]

    x = list(range(len(data)))

    fig, ax = _fig(width, height)

    ax.bar(
        x, fact,
        width=0.6,
        color=C.SERIES_1,
        edgecolor="none",
        label="Факт",
    )

    ax.bar(
        x, forecast,
        bottom=fact,
        width=0.6,
        color=C.TINT,
        edgecolor=C.SERIES_1,
        linewidth=0.5,
        label="Прогноз",
    )

    ax.plot(
        x, plan,
        color=C.SERIES_2,
        linewidth=1.6,
        marker="_",
        markersize=9,
        markeredgewidth=1.6,
        linestyle="none",
        label="План",
    )

    for i, (f, fc, p) in enumerate(zip(fact, forecast, plan)):
        total = f + fc
        if not total:
            continue
        behind = p and total < p * 0.95
        ax.annotate(
            _short(total, digits=1),
            xy=(i, total),
            xytext=(0, 3),
            textcoords="offset points",
            ha="center",
            fontsize=6.4,
            rotation=90,
            color=C.CRITICAL if behind else C.INK_2,
            fontweight="bold" if behind else "normal",
        )

    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.yaxis.set_major_formatter(_money_formatter())
    ax.set_ylabel("Выручка, ₽")
    _headroom(ax, 1.32)
    _legend(ax, ncol=3)

    return _render(fig)


# ============================================================
# 4. ФИНАНСОВЫЙ РЕЗУЛЬТАТ
# ============================================================

def structure_100(parts, width=FULL_W, height=1.25):
    """
    Куда уходят 100 ₽ выручки.

    Одна полоса на 100%: доли читаются как части целого,
    а не как отдельные столбики, которые надо складывать.
    """
    items = [
        (label, num(value) or 0.0, color)
        for label, value, color in parts
        if (num(value) or 0.0) > 0
    ]

    if not items:
        return None

    total = sum(value for _, value, _ in items)

    if total <= 0:
        return None

    fig, ax = plt.subplots(figsize=(width, height))

    left = 0.0

    for label, value, color in items:
        share = 100.0 * value / total

        ax.barh(
            0, share,
            left=left,
            height=0.52,
            color=color,
            edgecolor="white",
            linewidth=1.2,
        )

        if share >= 7:
            ax.text(
                left + share / 2,
                0,
                _pct_label(share, 1),
                ha="center",
                va="center",
                color="white",
                fontweight="bold",
                fontsize=7.6,
            )

        # Подпись под полосой — цвет не должен быть
        # единственным способом понять, что где.
        ax.text(
            left + share / 2,
            -0.46,
            label,
            ha="center",
            va="top",
            color=C.INK_2,
            fontsize=6.9,
        )

        left += share

    ax.set_xlim(0, 100)
    ax.set_ylim(-1.0, 0.45)
    ax.axis("off")

    return _render(fig)


def margin_history(rows, width=FULL_W, height=2.35):
    """
    Маржинальность и итоговый результат в процентах по дням.

    В процентах, а не в рублях: при разном объёме дней рубли
    скачут, а процент показывает, меняется ли экономика.
    """
    data = []

    for row in rows or []:
        d = as_date(row.get("date"))
        if d is None:
            continue
        data.append((
            d,
            num(row.get("margin_pct")),
            num(row.get("result_pct")),
        ))

    if len(data) < 5:
        return None

    data.sort(key=lambda item: item[0])

    labels = [d.strftime("%d.%m") for d, _, _ in data]
    x = list(range(len(data)))

    fig, ax = _fig(width, height)

    ax.axhline(0, color=C.AXIS, linewidth=0.8)

    ax.plot(
        x,
        [m if m is not None else float("nan") for _, m, _ in data],
        color=C.SERIES_1,
        linewidth=1.8,
        label="Маржа после себестоимости и комиссии, %",
    )

    ax.plot(
        x,
        [r if r is not None else float("nan") for _, _, r in data],
        color=C.SERIES_2,
        linewidth=1.6,
        label="Результат после расходов WB, %",
    )

    for series_index, color in ((1, C.SERIES_1), (2, C.SERIES_2)):
        last = None
        for item in data:
            if item[series_index] is not None:
                last = item[series_index]
        if last is None:
            continue
        ax.annotate(
            _pct_label(last, 1),
            xy=(x[-1], last),
            xytext=(-3, 6),
            textcoords="offset points",
            ha="right",
            color=color,
            fontweight="bold",
        )

    keep = _thin(labels, 12)
    ax.set_xticks([x[i] for i in keep])
    ax.set_xticklabels([labels[i] for i in keep])

    ax.yaxis.set_major_formatter(_pct_formatter())
    ax.set_ylabel("Доля от выручки, %")
    _legend(ax, ncol=1)

    return _render(fig)


# ============================================================
# 5. ЦЕНА И СКИДКА
# ============================================================

def price_and_discount(rows, days=60, width=FULL_W, height=2.45):
    """
    Цена продавца, цена покупателя и скидка WB между ними.

    Заливка между линиями — это и есть скидка WB в рублях
    на единицу. Её не надо считать, она видна. Подписи у пика,
    у минимума и в конце графика дают скидку сразу и в рублях,
    и в процентах от цены до скидки WB — одни рубли легко
    прочитать неверно (624 ₽ скидки при цене 1800 ₽ и при цене
    900 ₽ — совсем разная по силе скидка).
    """
    data = []

    for row in rows or []:
        d = as_date(row.get("date_from"))
        seller = num(row.get("seller_avg_price"))
        buyer = num(row.get("buyer_avg_price"))
        if d is None or not seller:
            continue
        data.append((d, seller, buyer or 0.0))

    if len(data) < 10:
        return None

    data.sort(key=lambda item: item[0])
    data = data[-days:]

    labels = [d.strftime("%d.%m") for d, _, _ in data]
    seller = [s for _, s, _ in data]
    buyer = [b for _, _, b in data]
    x = list(range(len(data)))

    fig, ax = _fig(width, height)

    ax.fill_between(
        x, buyer, seller,
        color=C.SERIES_2,
        alpha=0.13,
        linewidth=0,
        label="Скидка WB",
    )

    ax.plot(
        x, seller,
        color=C.SERIES_1,
        linewidth=1.8,
        label="Цена до скидки WB",
    )

    ax.plot(
        x, buyer,
        color=C.SERIES_2,
        linewidth=1.6,
        label="Цена покупателя",
    )

    for series, color, dy in ((seller, C.SERIES_1, 7), (buyer, C.SERIES_2, -13)):
        ax.annotate(
            _short(series[-1]),
            xy=(x[-1], series[-1]),
            xytext=(-3, dy),
            textcoords="offset points",
            ha="right",
            color=color,
            fontweight="bold",
        )

    # Скидка отдельно: конец периода, максимум и минимум --
    # в рублях и в процентах от цены до скидки WB. Без этого
    # разницу между линиями нужно было бы прикидывать на глаз
    # по заливке -- а её как раз спрашивают чаще всего.
    discount = [s - b for s, b in zip(seller, buyer)]
    discount_pct = [
        (value / s * 100) if s else 0.0
        for value, s in zip(discount, seller)
    ]

    end_discount = discount[-1]
    end_pct = discount_pct[-1]
    max_i = max(range(len(discount)), key=lambda i: discount[i])
    min_i = min(range(len(discount)), key=lambda i: discount[i])

    ax.annotate(
        f"скидка {_short(end_discount)} · {_pct_label(end_pct, 0)}",
        xy=(x[-1], (seller[-1] + buyer[-1]) / 2),
        xytext=(-8, 0),
        textcoords="offset points",
        ha="right",
        va="center",
        fontsize=6.8,
        fontweight="bold",
        color=C.MUTED,
    )

    # Максимум и минимум не подписываем, когда они совпадают
    # с концом периода -- подпись уже стоит рядом, вторая
    # только наложится на первую. Красный/зелёный -- та же
    # логика цвета, что и в остальном отчёте: где скидка
    # съедала больше всего маржи и где меньше всего.
    for i, tag, color in (
        (max_i, "макс.", C.CRITICAL),
        (min_i, "мин.", C.GOOD),
    ):
        if i in (len(discount) - 1, 0):
            continue

        mid_y = (seller[i] + buyer[i]) / 2
        above = i == max_i

        ax.plot(
            [x[i]], [mid_y],
            marker="o", markersize=3.2,
            color=color, linewidth=0,
            zorder=5,
        )
        ax.annotate(
            f"{tag} скидка {_short(discount[i])} "
            f"· {_pct_label(discount_pct[i], 0)}",
            xy=(x[i], mid_y),
            xytext=(0, 10 if above else -12),
            textcoords="offset points",
            ha="center",
            va="bottom" if above else "top",
            fontsize=6.8,
            fontweight="bold",
            color=color,
        )

    ax.margins(y=0.17)

    keep = _thin(labels, 12)
    ax.set_xticks([x[i] for i in keep])
    ax.set_xticklabels([labels[i] for i in keep])

    ax.yaxis.set_major_formatter(_money_formatter())
    ax.set_ylabel("Цена за единицу, ₽")
    _legend(ax, ncol=3)

    return _render(fig)


def brand_price_scatter(brands, width=FULL_W, height=2.7):
    """
    Бренды в координатах «изменение цены — изменение количества».

    Четыре четверти читаются сразу: справа вверху цену подняли
    и не потеряли объём, слева внизу потеряли и то и другое.
    """
    points = []

    for row in brands or []:
        price = num(row.get("price_change_pct"))
        qty = num(row.get("qty_change_pct"))
        revenue = (
            num(row.get("revenue_14d"))
            or num(row.get("revenue"))
            or num(row.get("amount_vatless"))
            or 0.0
        )
        name = row.get("brand") or row.get("name")

        if price is None or qty is None or not name:
            continue

        points.append((price, qty, abs(revenue), str(name)))

    if len(points) < 3:
        return None

    points.sort(key=lambda p: -p[2])
    points = points[:12]

    max_revenue = max(p[2] for p in points) or 1.0

    fig, ax = _fig(width, height)

    ax.axhline(0, color=C.AXIS, linewidth=0.8)
    ax.axvline(0, color=C.AXIS, linewidth=0.8)
    ax.xaxis.grid(True, color=C.GRID, linewidth=0.6)

    for price, qty, revenue, name in points:
        good = qty >= 0
        ax.scatter(
            price,
            qty,
            s=40 + 260 * (revenue / max_revenue),
            color=C.SERIES_1 if good else C.SERIES_2,
            alpha=0.55,
            edgecolor="white",
            linewidth=0.8,
            zorder=3,
        )

        ax.annotate(
            name[:18],
            xy=(price, qty),
            xytext=(0, 9),
            textcoords="offset points",
            ha="center",
            fontsize=6.6,
            color=C.INK,
            zorder=4,
        )

    ax.set_xlabel("Изменение средней цены, %")
    ax.set_ylabel("Изменение количества, %")
    ax.xaxis.set_major_formatter(_pct_formatter())
    ax.yaxis.set_major_formatter(_pct_formatter())

    # Немного воздуха, чтобы подписи не срезались.
    for setter, getter in ((ax.set_xlim, ax.get_xlim), (ax.set_ylim, ax.get_ylim)):
        low, high = getter()
        span = (high - low) or 1.0
        setter(low - span * 0.12, high + span * 0.18)

    ax.annotate(
        "размер круга — выручка бренда",
        xy=(0.99, 1.02),
        xycoords="axes fraction",
        ha="right",
        fontsize=6.6,
        color=C.MUTED,
    )

    return _render(fig)


# ============================================================
# 6. ЗАПАСЫ
# ============================================================

def hbar(
    labels,
    values,
    value_labels=None,
    colors=None,
    axis_label="",
    width=FULL_W,
    height=None,
    percent=False,
):
    """
    Горизонтальные полосы с подписанными значениями.

    Для названий брендов и складов — единственный читаемый
    вариант: вертикальные подписи под столбиками приходится
    поворачивать, и их перестают читать.
    """
    rows = [
        (str(label), num(value) or 0.0)
        for label, value in zip(labels or [], values or [])
    ]

    if not rows:
        return None

    if height is None:
        height = max(1.1, 0.26 * len(rows) + 0.55)

    fig, ax = plt.subplots(figsize=(width, height))

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(False)
    ax.spines["bottom"].set_color(C.AXIS)

    ax.set_axisbelow(True)
    ax.xaxis.grid(True, color=C.GRID, linewidth=0.6)
    ax.yaxis.grid(False)
    ax.tick_params(length=0, pad=3)

    y = list(range(len(rows)))[::-1]

    bar_colors = colors or [C.SERIES_1] * len(rows)

    ax.barh(
        y,
        [value for _, value in rows],
        height=0.62,
        color=bar_colors,
        edgecolor="none",
    )

    span = max(abs(value) for _, value in rows) or 1.0

    for position, (label, value), index in zip(y, rows, range(len(rows))):
        text = (
            value_labels[index]
            if value_labels and index < len(value_labels)
            else (_pct_label(value, 1) if percent else _short(value))
        )

        ax.annotate(
            text,
            xy=(value, position),
            xytext=(4 if value >= 0 else -4, 0),
            textcoords="offset points",
            va="center",
            ha="left" if value >= 0 else "right",
            fontsize=7.0,
            fontweight="bold",
            color=C.INK,
        )

    ax.set_yticks(y)
    ax.set_yticklabels([label for label, _ in rows], fontsize=7.0)

    ax.xaxis.set_major_formatter(
        _pct_formatter() if percent else _money_formatter()
    )

    if axis_label:
        ax.set_xlabel(axis_label)

    low = min(0.0, min(value for _, value in rows))
    ax.set_xlim(low * 1.05 if low < 0 else 0, span * 1.22)

    return _render(fig)


def coverage_buckets(buckets, width=FULL_W, height=2.15):
    """
    Запас по группам покрытия.

    Цвет идёт от нормального к проблемному слева направо,
    поэтому «красный справа» — это буквально то, что залежалось.
    """
    order_colors = {
        "0_30": C.GOOD,
        "30_60": C.SERIES_3,
        "60_90": C.WARNING,
        "90_plus": C.SERIOUS,
        "no_sales": C.CRITICAL,
    }

    rows = [
        row for row in (buckets or [])
        if (num(row.get("qty")) or 0) > 0
    ]

    if not rows:
        return None

    labels = [row.get("short_label") or row.get("label") or "" for row in rows]
    values = [num(row.get("qty")) or 0.0 for row in rows]
    colors = [order_colors.get(row.get("key"), C.SERIES_1) for row in rows]

    value_labels = [
        f"{_short(num(row.get('qty')))} шт. · "
        f"{_pct_label(num(row.get('share_pct')), 1)} · "
        f"{_short(num(row.get('management_value')))} ₽"
        for row in rows
    ]

    fig, ax = plt.subplots(figsize=(width, height))

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(False)
    ax.spines["bottom"].set_color(C.AXIS)
    ax.set_axisbelow(True)
    ax.xaxis.grid(True, color=C.GRID, linewidth=0.6)
    ax.tick_params(length=0, pad=3)

    y = list(range(len(rows)))[::-1]

    ax.barh(y, values, height=0.6, color=colors, edgecolor="none")

    for position, value, text in zip(y, values, value_labels):
        ax.annotate(
            text,
            xy=(value, position),
            xytext=(5, 0),
            textcoords="offset points",
            va="center",
            fontsize=6.9,
            color=C.INK,
        )

    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=7.1)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _p: _short(v)))
    ax.set_xlabel("Запас, шт.")
    ax.set_xlim(0, max(values) * 1.58)

    return _render(fig)


# ============================================================
# 7. ЗАКАЗЫ FBS
# ============================================================

def fbs_daily(rows, width=FULL_W, height=2.3):
    """
    Заказы FBS по дням: сколько пришло и на какую сумму.

    Столбики — количество, линия — деньги. Расхождение линий
    означает, что изменился средний чек.
    """
    data = []

    for row in rows or []:
        d = as_date(
            row.get("order_date")
            or row.get("day")
            or row.get("date")
            or row.get("date_from")
        )
        orders = num(row.get("orders")) or num(row.get("orders_total"))
        amount = num(row.get("amount")) or num(row.get("order_amount")) or 0.0
        if d is None or orders is None:
            continue
        data.append((d, orders, amount))

    if len(data) < 3:
        return None

    data.sort(key=lambda item: item[0])
    data = data[-45:]

    labels = [d.strftime("%d.%m") for d, _, _ in data]
    x = list(range(len(data)))

    fig, ax = _fig(width, height)

    ax.bar(
        x,
        [o for _, o, _ in data],
        width=0.7,
        color=C.TINT,
        edgecolor=C.SERIES_1,
        linewidth=0.4,
        label="Заказов, шт.",
    )

    ax.set_ylabel("Заказов, шт.")
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _p: _short(v)))
    ax.set_xlim(-0.8, len(data) - 0.2)

    ax2 = ax.twinx()
    ax2.spines["top"].set_visible(False)
    ax2.spines["left"].set_visible(False)
    ax2.spines["right"].set_color(C.AXIS)
    ax2.grid(False)
    ax2.tick_params(length=2, pad=2)

    ax2.plot(
        x,
        [a for _, _, a in data],
        color=C.SERIES_2,
        linewidth=1.7,
        label="Сумма заказов, ₽",
    )

    ax2.set_ylabel("Сумма заказов, ₽", color=C.SERIES_2)
    ax2.yaxis.set_major_formatter(_money_formatter())
    ax2.tick_params(axis="y", labelcolor=C.SERIES_2)

    keep = _thin(labels, 12)
    ax.set_xticks([x[i] for i in keep])
    ax.set_xticklabels([labels[i] for i in keep])

    handles = ax.get_legend_handles_labels()
    handles2 = ax2.get_legend_handles_labels()

    ax.legend(
        handles[0] + handles2[0],
        handles[1] + handles2[1],
        loc="lower left",
        bbox_to_anchor=(0.0, 1.04),
        ncol=2,
        handlelength=1.5,
        handletextpad=0.5,
        columnspacing=1.4,
        borderaxespad=0.0,
    )

    return _render(fig)


def fbs_assembly_buckets(rows, width=FULL_W, height=1.95):
    """
    Сколько заказов сколько часов ждёт сборки.

    Группы за нормативом покрашены в красное: очередь
    читается как «сколько уже поздно», а не просто гистограмма.
    """
    data = [
        row for row in (rows or [])
        if (num(row.get("orders")) or 0) > 0
    ]

    if not data:
        return None

    labels = []
    values = []
    colors = []

    for row in data:
        label = str(
            row.get("time_group")
            or row.get("bucket")
            or row.get("bucket_label")
            or ""
        )
        labels.append(label)
        values.append(num(row.get("orders")) or 0.0)

        # За нормативом — красным. Норматив берём по среднему
        # возрасту заказов в корзине.
        age = num(row.get("avg_hours")) or 0.0
        colors.append(
            C.CRITICAL if age >= C.FBS_SLA_HOURS else C.SERIES_1
        )

    value_labels = []

    for row, value in zip(data, values):
        amount = num(row.get("amount"))
        share = num(row.get("share_pct"))
        age = num(row.get("avg_hours"))

        text = f"{_short(value)} шт."
        if share is not None:
            text += f" · {_pct_label(share, 1)}"
        if amount:
            text += f" · {_short(amount)} ₽"
        if age is not None:
            text += f" · в среднем {age:.0f} ч".replace(".", ",")

        value_labels.append(text)

    fig, ax = plt.subplots(figsize=(width, height))

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(False)
    ax.spines["bottom"].set_color(C.AXIS)
    ax.set_axisbelow(True)
    ax.xaxis.grid(True, color=C.GRID, linewidth=0.6)
    ax.tick_params(length=0, pad=3)

    y = list(range(len(values)))[::-1]

    ax.barh(y, values, height=0.6, color=colors, edgecolor="none")

    for position, value, text in zip(y, values, value_labels):
        ax.annotate(
            text,
            xy=(value, position),
            xytext=(5, 0),
            textcoords="offset points",
            va="center",
            fontsize=6.9,
            color=C.INK,
        )

    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=7.1)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _p: _short(v)))
    ax.set_xlabel("Заказов в работе, шт.")
    ax.set_xlim(0, max(values) * 1.6)

    return _render(fig)


# ============================================================
# 8. ВЫРУЧКА ПРОТИВ МАРЖИНАЛЬНОСТИ
# ============================================================

def revenue_vs_margin(rows, limit=12, width=FULL_W, height=None):
    """
    Выручка и маржинальность в одном разрезе.

    Две панели с общей осью подписей вместо двух шкал на одном
    поле: смешивать рубли и проценты в одних координатах —
    верный способ, чтобы длинную полосу приняли за высокую
    маржу. Слева деньги, справа процент, строки одни и те же.

    Средняя маржинальность нарисована вертикальной линией:
    вопрос «кто ниже среднего» — это первое, что спрашивают.
    """
    data = [
        row for row in (rows or [])
        if (num(row.get("revenue_vatless")) or 0) != 0
    ]

    if not data:
        return None

    data.sort(key=lambda row: -(num(row.get("revenue_vatless")) or 0))
    data = data[:limit]
    data.reverse()

    names = [str(row.get("name") or "—")[:22] for row in data]
    revenue = [num(row.get("revenue_vatless")) or 0.0 for row in data]
    margin = [num(row.get("margin_man_pct")) for row in data]
    profit = [num(row.get("gross_profit_man")) or 0.0 for row in data]

    total_revenue = sum(revenue)
    total_profit = sum(profit)

    average_margin = (
        100.0 * total_profit / total_revenue if total_revenue else None
    )

    if height is None:
        height = max(1.8, 0.30 * len(data) + 0.85)

    fig, (ax_left, ax_right) = plt.subplots(
        1, 2,
        figsize=(width, height),
        gridspec_kw={"width_ratios": [1.55, 1.0], "wspace": 0.04},
    )

    y = list(range(len(data)))

    # ---- слева: выручка ------------------------------------
    for axis in (ax_left, ax_right):
        axis.spines["top"].set_visible(False)
        axis.spines["right"].set_visible(False)
        axis.spines["left"].set_visible(False)
        axis.spines["bottom"].set_color(C.AXIS)
        axis.set_axisbelow(True)
        axis.xaxis.grid(True, color=C.GRID, linewidth=0.6)
        axis.tick_params(length=0, pad=3)
        axis.set_ylim(-0.7, len(data) - 0.3)

    ax_left.barh(
        y, revenue,
        height=0.62,
        color=C.SERIES_1,
        edgecolor="none",
    )

    for position, value in zip(y, revenue):
        ax_left.annotate(
            _short(value),
            xy=(value, position),
            xytext=(4, 0),
            textcoords="offset points",
            va="center",
            fontsize=6.9,
            fontweight="bold",
            color=C.INK,
        )

    ax_left.set_yticks(y)
    ax_left.set_yticklabels(names, fontsize=7.0)
    ax_left.xaxis.set_major_formatter(_money_formatter())
    ax_left.set_xlabel("Выручка без НДС, ₽")
    ax_left.set_xlim(0, (max(revenue) or 1) * 1.26)

    # Панель узкая (меньше половины ширины фигуры), а разброс
    # выручки между брендами обычно большой -- дефолтный локатор
    # matplotlib расставляет тик через каждые 20 млн и подписи
    # наезжают друг на друга. Ограничиваем число тиков явно,
    # чтобы они гарантированно помещались.
    ax_left.xaxis.set_major_locator(MaxNLocator(nbins=5))

    # ---- справа: маржинальность ----------------------------
    colors = []
    values = []

    for value in margin:
        v = 0.0 if value is None else value
        values.append(v)

        if v < 0:
            colors.append(C.CRITICAL)
        elif average_margin is not None and v < average_margin:
            colors.append(C.WARNING)
        else:
            colors.append(C.SERIES_3)

    ax_right.barh(
        y, values,
        height=0.62,
        color=colors,
        edgecolor="none",
    )

    if average_margin is not None:
        ax_right.axvline(
            average_margin,
            color=C.INK_2,
            linewidth=1.0,
            linestyle=(0, (3, 2)),
            zorder=4,
        )

        ax_right.annotate(
            f"в среднем {_pct_label(average_margin, 1)}",
            xy=(average_margin, len(data) - 0.35),
            xytext=(3, 0),
            textcoords="offset points",
            va="center",
            fontsize=6.6,
            color=C.INK_2,
        )

    for position, value, raw in zip(y, values, margin):
        ax_right.annotate(
            "—" if raw is None else _pct_label(raw, 1),
            xy=(value, position),
            xytext=(4 if value >= 0 else -4, 0),
            textcoords="offset points",
            va="center",
            ha="left" if value >= 0 else "right",
            fontsize=6.9,
            fontweight="bold",
            color=C.INK,
        )

    ax_right.set_yticks([])
    ax_right.xaxis.set_major_formatter(_pct_formatter())
    ax_right.set_xlabel("Маржинальность, %")

    low = min(0.0, min(values))
    high = max(values + ([average_margin] if average_margin else []))
    span = (high - low) or 1.0
    ax_right.set_xlim(low - span * 0.05, high + span * 0.30)
    ax_right.axvline(0, color=C.AXIS, linewidth=0.8)

    return _render(fig)


# ============================================================
# РАСХОДЫ WB ПО НЕДЕЛЯМ
# ============================================================

#: Свой набор цветов на 6 статей: заёмных из палитры данных
#: не хватает (там всего три серии), поэтому берём весь
#: фирменный набор -- он проверен на различимость.
EXPENSE_PALETTE = [
    C.SERIES_1, C.SERIES_2, C.SERIES_3,
    C.WARNING, C.NAVY_2, C.MUTED,
]


def discount_weekly(weeks, width=FULL_W, height=1.7):
    """
    Скидка WB по неделям — столбики с процентом сверху.

    Та же разбивка по неделям, что и в календаре выручки —
    читаются вместе: там сумма, здесь доля, которую забирает
    скидка. Недели без полных 7 дней данных рисуем светлее
    и без подписи "макс/мин", чтобы не сравнивать их как
    полноценные.
    """
    rows = [w for w in (weeks or []) if w.get("discount_pct") is not None]
    if len(rows) < 2:
        return None

    labels = [w["label"] for w in rows]
    values = [w["discount_pct"] for w in rows]
    full = [bool(w.get("full")) for w in rows]
    x = list(range(len(rows)))

    fig, ax = _fig(width, height)

    full_values = [v for v, f in zip(values, full) if f]
    max_i = (
        max((i for i in x if full[i]), key=lambda i: values[i])
        if full_values else None
    )
    min_i = (
        min((i for i in x if full[i]), key=lambda i: values[i])
        if full_values else None
    )

    colors = []
    for i in x:
        if not full[i]:
            colors.append(C.LINE)
        elif i == max_i:
            colors.append(C.CRITICAL)
        elif i == min_i:
            colors.append(C.SERIES_1)
        else:
            colors.append(C.SERIES_2)

    ax.bar(x, values, width=0.55, color=colors, linewidth=0)

    for i, v in enumerate(values):
        ax.annotate(
            _pct_label(v, 1),
            xy=(x[i], v),
            xytext=(0, 3),
            textcoords="offset points",
            ha="center",
            fontsize=7.0,
            fontweight="bold",
            color=C.INK if full[i] else C.MUTED,
        )

    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_xlim(-0.6, len(rows) - 0.4)

    ax.yaxis.set_major_formatter(_pct_formatter(0))
    ax.set_ylabel("Скидка WB")
    _headroom(ax, 1.22)

    return _render(fig)


def wb_expenses_weekly(weeks, categories, total_spike=None,
                        width=FULL_W, height=2.7):
    """
    Расходы WB по неделям, с разбивкой по статьям.

    Столбик — сумма за неделю, цвет внутри — статья. Если среди
    недель есть явный всплеск (см. _find_spike в data.py),
    отмечаем его подписью прямо над столбиком, а не оставляем
    искать глазами.
    """
    if not weeks or not categories:
        return None

    labels = [w["label"] for w in weeks]
    x = list(range(len(weeks)))

    fig, ax = _fig(width, height)

    bottoms = [0.0] * len(weeks)
    for i, cat in enumerate(categories):
        values = [w["by_category"].get(cat, 0.0) for w in weeks]
        color = EXPENSE_PALETTE[i % len(EXPENSE_PALETTE)]

        ax.bar(
            x, values,
            bottom=bottoms,
            width=0.6,
            color=color,
            label=cat,
            linewidth=0,
        )
        bottoms = [b + v for b, v in zip(bottoms, values)]

    totals = [w["total"] for w in weeks]
    for i, total in enumerate(totals):
        ax.annotate(
            _short(total),
            xy=(x[i], totals[i]),
            xytext=(0, 3),
            textcoords="offset points",
            ha="center",
            fontsize=7.0,
            fontweight="bold",
            color=C.INK,
        )

    if total_spike:
        spike_i = next(
            (i for i, l in enumerate(labels) if l == total_spike["label"]),
            None,
        )
        if spike_i is not None:
            ax.annotate(
                f"пик: {_pct_label(100 * (total_spike['ratio'] - 1), 0)} "
                f"к среднему по остальным неделям",
                xy=(x[spike_i], totals[spike_i]),
                xytext=(0, 17),
                textcoords="offset points",
                ha="center",
                fontsize=7.0,
                fontweight="bold",
                color=C.CRITICAL,
                arrowprops=dict(
                    arrowstyle="-",
                    color=C.CRITICAL,
                    linewidth=0.8,
                    shrinkA=0, shrinkB=2,
                ),
            )

    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_xlim(-0.6, len(weeks) - 0.4)

    ax.yaxis.set_major_formatter(_money_formatter())
    ax.set_ylabel("Расходы WB, ₽")
    _headroom(ax, 1.28)
    _legend(ax, ncol=3, y=1.1)

    return _render(fig)


def wb_costs_share_weekly(rows, width=FULL_W, height=1.7):
    """
    Расходы WB как доля чистой выручки, по неделям.

    В разделе "Финансовый результат" эта доля есть только за
    одну неделю. Здесь -- несколько подряд, чтобы увидеть, растут
    расходы WB быстрее выручки или вместе с ней (если столбики
    примерно на одном уровне -- это пропорциональный рост,
    а не ухудшение экономики).
    """
    data = [r for r in (rows or []) if r.get("wb_costs_share") is not None]
    if len(data) < 2:
        return None

    labels = [r["label"] for r in data]
    values = [r["wb_costs_share"] for r in data]
    closed = [bool(r.get("is_closed")) for r in data]
    x = list(range(len(data)))

    fig, ax = _fig(width, height)

    colors = [C.WARNING if c else C.LINE for c in closed]

    ax.bar(x, values, width=0.55, color=colors, linewidth=0)

    for i, v in enumerate(values):
        ax.annotate(
            _pct_label(v, 1),
            xy=(x[i], v),
            xytext=(0, 3),
            textcoords="offset points",
            ha="center",
            fontsize=7.0,
            fontweight="bold",
            color=C.INK if closed[i] else C.MUTED,
        )

    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_xlim(-0.6, len(data) - 0.4)

    ax.yaxis.set_major_formatter(_pct_formatter(0))
    ax.set_ylabel("Расходы WB, % от выручки без НДС")
    _headroom(ax, 1.25)

    return _render(fig)


def wb_expenses_category_trend(weeks, category, spike=None,
                                width=FULL_W, height=1.7):
    """
    Одна статья расходов WB по неделям, отдельно от остальных.

    На общем стеке (wb_expenses_weekly) статья вроде штрафов --
    тонкая полоска на фоне рекламы и логистики, почти не видно.
    А именно штрафы чаще всего можно оспорить у WB, а не просто
    принять как данность -- поэтому им отдельный, крупный график.
    Неделю со всплеском (см. category_spikes в data.py)
    подсвечиваем отдельным цветом.
    """
    rows = [
        w for w in (weeks or [])
        if category in (w.get("by_category") or {})
    ]
    if len(rows) < 2:
        return None

    labels = [w["label"] for w in rows]
    values = [w["by_category"].get(category, 0.0) for w in rows]
    closed = [bool(w.get("is_closed")) for w in rows]
    x = list(range(len(rows)))

    fig, ax = _fig(width, height)

    spike_label = spike["label"] if spike else None
    colors = [
        (C.CRITICAL if lbl == spike_label else C.SERIES_2)
        if is_closed else C.LINE
        for lbl, is_closed in zip(labels, closed)
    ]

    ax.bar(x, values, width=0.55, color=colors, linewidth=0)
    ax.axhline(0, color=C.AXIS, linewidth=0.6)

    for i, v in enumerate(values):
        ax.annotate(
            _short(v),
            xy=(x[i], v),
            xytext=(0, -11 if v < 0 else 3),
            textcoords="offset points",
            ha="center",
            va="top" if v < 0 else "bottom",
            fontsize=7.0,
            fontweight="bold",
            color=C.INK if closed[i] else C.MUTED,
        )

    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_xlim(-0.6, len(rows) - 0.4)
    ax.margins(y=0.22)

    ax.yaxis.set_major_formatter(_money_formatter())
    ax.set_ylabel(f"{category}, ₽")

    return _render(fig)


def wb_expenses_category_share(weeks, categories, width=FULL_W, height=1.9):
    """
    Доля каждой статьи в расходах WB, по неделям -- 100%-стек.

    wb_expenses_weekly() показывает суммы: там видно, где расходы
    выросли в деньгах. Здесь то же самое в процентах -- видно,
    куда сместилась структура, даже если общая сумма почти
    не изменилась (например, доля рекламы выросла за счёт доли
    логистики при том же итоге).
    """
    rows = [w for w in (weeks or []) if w.get("by_category")]
    if len(rows) < 2 or not categories:
        return None

    labels = [w["label"] for w in rows]
    x = list(range(len(rows)))

    totals_abs = [
        sum(abs(v) for v in w["by_category"].values()) for w in rows
    ]

    fig, ax = _fig(width, height)

    bottoms = [0.0] * len(rows)
    for i, cat in enumerate(categories):
        shares = [
            100 * abs(w["by_category"].get(cat, 0.0)) / total_abs
            if total_abs else 0.0
            for w, total_abs in zip(rows, totals_abs)
        ]
        color = EXPENSE_PALETTE[i % len(EXPENSE_PALETTE)]

        ax.bar(
            x, shares,
            bottom=bottoms,
            width=0.6,
            color=color,
            label=cat,
            linewidth=0,
        )
        bottoms = [b + v for b, v in zip(bottoms, shares)]

    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_xlim(-0.6, len(rows) - 0.4)
    ax.set_ylim(0, 100)

    ax.yaxis.set_major_formatter(_pct_formatter(0))
    ax.set_ylabel("Доля от расходов WB за неделю")
    _legend(ax, ncol=3, y=1.12)

    return _render(fig)

