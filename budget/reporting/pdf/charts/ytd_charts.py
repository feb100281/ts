# budget/reporting/pdf/charts/ytd_charts.py
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import FuncFormatter

from budget.reporting.pdf.charts.base import fig_to_base64, remove_inner_frame
from budget.reporting.pdf.charts.styles import (
    COLOR_BG, COLOR_GRID, COLOR_TEXT, COLOR_MUTED,
    COLOR_PRIMARY, COLOR_POSITIVE, COLOR_NEGATIVE, COLOR_BAR_SOFT
)


MONTH_NAMES_RU = [
    "Янв", "Фев", "Мар", "Апр", "Май", "Июн",
    "Июл", "Авг", "Сен", "Окт", "Ноя", "Дек"
]


def format_price_axis_ru(value, _=None):
    abs_value = abs(value)

    if abs_value >= 1_000_000:
        return f"{value / 1_000_000:.1f} млн"
    if abs_value >= 1_000:
        return f"{value / 1_000:.0f} тыс"
    return f"{value:,.0f}".replace(",", " ")


def format_pct(value):
    return f"{value:.0f}%"


def add_bar_labels(ax, bars, values, color, only_last=False):
    indexes = [len(values) - 1] if only_last and values else range(len(values))

    max_value = max(values) if values else 0
    offset = max_value * 0.012 if max_value else 1

    for i in indexes:
        bar = bars[i]
        value = values[i]

        ax.text(
            bar.get_x() + bar.get_width() / 2,
            value + offset,
            format_price_axis_ru(value),
            ha="center",
            va="bottom",
            fontsize=7.5,
            fontweight="normal",
            color=color,
            alpha=0.95
        )


def style_common_axes(ax):
    ax.tick_params(axis="x", colors=COLOR_TEXT, labelsize=8.5)
    ax.tick_params(axis="y", colors=COLOR_MUTED, labelsize=8.5)

    ax.grid(
        True,
        axis="y",
        linestyle="--",
        linewidth=0.6,
        alpha=0.35,
        color=COLOR_GRID
    )

    ax.set_axisbelow(True)
    remove_inner_frame(ax, keep_bottom=True)


def build_ytd_plan_fact_chart_base64(monthly_data):
    """
    График YTD:
    - столбцы: накопленный план и факт
    - подписи на каждом столбике
    - линия выполнения: факт / план, %
    """
    if not monthly_data:
        return None

    months = [
        f"{MONTH_NAMES_RU[m['month_num'] - 1]} {m['year']}"
        for m in monthly_data
    ]

    running_plan = [m["running_plan"] for m in monthly_data]
    running_fact = [m["running_fact"] for m in monthly_data]

    execution_pct = [
        fact / plan * 100 if plan else 0
        for fact, plan in zip(running_fact, running_plan)
    ]

    x = np.arange(len(months))
    width = 0.34

    fig, ax = plt.subplots(figsize=(10.8, 5.4), dpi=150)
    fig.patch.set_facecolor(COLOR_BG)
    ax.set_facecolor(COLOR_BG)

    bars_plan = ax.bar(
        x - width / 2,
        running_plan,
        width,
        label="План",
        color=COLOR_POSITIVE,
        alpha=0.86,
        edgecolor=COLOR_BG,
        linewidth=0.8
    )

    bars_fact = ax.bar(
        x + width / 2,
        running_fact,
        width,
        label="Факт",
        color=COLOR_BAR_SOFT,
        alpha=0.92,
        edgecolor=COLOR_BG,
        linewidth=0.8
    )

    add_bar_labels(ax, bars_plan, running_plan, COLOR_POSITIVE)
    add_bar_labels(ax, bars_fact, running_fact, COLOR_MUTED)

    # Вторая ось для процента выполнения
    ax_pct = ax.twinx()

    ax_pct.plot(
        x,
        execution_pct,
        color=COLOR_PRIMARY,
        linewidth=2.2,
        marker="o",
        markersize=5.5,
        markerfacecolor=COLOR_BG,
        markeredgecolor=COLOR_PRIMARY,
        markeredgewidth=1.4,
        label="Выполнение, %"
    )

    ax_pct.axhline(
        100,
        color=COLOR_NEGATIVE,
        linestyle="--",
        linewidth=1.1,
        alpha=0.75
    )

    for xi, pct in zip(x, execution_pct):
        color = COLOR_POSITIVE if pct >= 100 else COLOR_NEGATIVE

        ax_pct.annotate(
            f"{pct:.1f}%",
            xy=(xi, pct),
            xytext=(0, 8 if pct < 100 else -12),
            textcoords="offset points",
            ha="center",
            va="bottom" if pct < 100 else "top",
            fontsize=7.8,
            fontweight="bold",
            color=color,
            bbox=dict(
                boxstyle="round,pad=0.22",
                facecolor=COLOR_BG,
                edgecolor=color,
                linewidth=0.6,
                alpha=0.9
            )
        )

    # Итоговая дельта
    last_plan = running_plan[-1]
    last_fact = running_fact[-1]

    diff = last_fact - last_plan
    diff_pct = diff / last_plan * 100 if last_plan else 0

    diff_color = COLOR_POSITIVE if diff >= 0 else COLOR_NEGATIVE
    diff_sign = "+" if diff >= 0 else ""

    ax.annotate(
        f"{diff_sign}{format_price_axis_ru(diff)} / {diff_sign}{diff_pct:.1f}%",
        xy=(x[-1], max(last_plan, last_fact)),
        xytext=(0, 34),
        textcoords="offset points",
        ha="center",
        va="bottom",
        fontsize=9,
        fontweight="bold",
        color=diff_color,
        bbox=dict(
            boxstyle="round,pad=0.35",
            facecolor=COLOR_BG,
            edgecolor=diff_color,
            linewidth=0.8,
            alpha=0.95
        )
    )

    ax.set_title(
        "Накопленные итоги YTD: План vs Факт",
        fontsize=12,
        fontweight="bold",
        color=COLOR_TEXT,
        pad=14
    )

    ax.set_ylabel("Сумма, руб.", fontsize=9, color=COLOR_MUTED, labelpad=8)
    ax_pct.set_ylabel("Выполнение плана, %", fontsize=9, color=COLOR_MUTED, labelpad=8)

    ax.set_xticks(x)
    ax.set_xticklabels(months, rotation=0, ha="center", fontsize=8.5, color=COLOR_TEXT)

    ax.yaxis.set_major_formatter(FuncFormatter(format_price_axis_ru))
    ax_pct.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}%"))

    max_y = max(max(running_plan), max(running_fact)) if running_plan else 0
    ax.set_ylim(0, max_y * 1.24 if max_y else 1)

    min_pct = min(execution_pct) if execution_pct else 0
    max_pct = max(execution_pct) if execution_pct else 100

    ax_pct.set_ylim(
        max(0, min_pct - 12),
        max(110, max_pct + 10)
    )

    ax_pct.tick_params(axis="y", colors=COLOR_MUTED, labelsize=8.5)
    remove_inner_frame(ax_pct, keep_bottom=False)

    # Общая легенда
    handles_1, labels_1 = ax.get_legend_handles_labels()
    handles_2, labels_2 = ax_pct.get_legend_handles_labels()

    ax.legend(
        handles_1 + handles_2,
        labels_1 + labels_2,
        loc="upper left",
        fontsize=8.5,
        frameon=True,
        fancybox=True,
        edgecolor=COLOR_GRID,
        facecolor=COLOR_BG,
        labelcolor=COLOR_TEXT
    )

    style_common_axes(ax)

    fig.tight_layout(pad=1.4)
    return fig_to_base64(fig)


def build_ytd_daily_chart_base64(daily_analysis):
    """Строит график дневного выполнения плана по каждому дню."""
    if not daily_analysis or not daily_analysis.get("days"):
        return None

    days_data = daily_analysis["days"]

    days = [d["day"] for d in days_data]
    daily_pct = [d["exec_day_pct"] for d in days_data]

    fig, ax = plt.subplots(figsize=(10.8, 4.8), dpi=150)
    fig.patch.set_facecolor(COLOR_BG)
    ax.set_facecolor(COLOR_BG)

    ax.plot(
        days,
        daily_pct,
        linewidth=2.2,
        color=COLOR_PRIMARY,
        marker="o",
        markersize=5.5,
        markerfacecolor=COLOR_BG,
        markeredgewidth=1.5,
        markeredgecolor=COLOR_PRIMARY,
        zorder=3
    )

    daily_pct_arr = np.array(daily_pct)

    ax.fill_between(
        days,
        daily_pct_arr,
        100,
        where=daily_pct_arr >= 100,
        color=COLOR_POSITIVE,
        alpha=0.14,
        interpolate=True
    )

    ax.fill_between(
        days,
        daily_pct_arr,
        100,
        where=daily_pct_arr < 100,
        color=COLOR_NEGATIVE,
        alpha=0.12,
        interpolate=True
    )

    ax.axhline(
        y=100,
        color=COLOR_NEGATIVE,
        linestyle="--",
        linewidth=1.2,
        alpha=0.85,
        label="План 100%"
    )

    ax.text(
        max(days),
        100,
        " 100%",
        va="center",
        ha="left",
        fontsize=8,
        fontweight="bold",
        color=COLOR_NEGATIVE
    )

    label_indexes = {0, len(days) - 1}

    if len(days) > 6:
        label_indexes.update(range(4, len(days), 5))
    else:
        label_indexes.update(range(len(days)))

    for i in sorted(label_indexes):
        day = days[i]
        pct = daily_pct[i]

        offset = 8 if pct < 100 else -12
        va = "bottom" if pct < 100 else "top"

        ax.annotate(
            format_pct(pct),
            xy=(day, pct),
            xytext=(0, offset),
            textcoords="offset points",
            ha="center",
            va=va,
            fontsize=7.5,
            fontweight="bold",
            color=COLOR_TEXT,
            zorder=4
        )

    last_day = days[-1]
    last_pct = daily_pct[-1]

    final_color = COLOR_POSITIVE if last_pct >= 100 else COLOR_NEGATIVE
    final_sign = "+" if last_pct >= 100 else ""

    ax.annotate(
        f"Последний день: {last_pct:.1f}%\n{final_sign}{last_pct - 100:.1f} п.п. к плану",
        xy=(last_day, last_pct),
        xytext=(-16, 28),
        textcoords="offset points",
        ha="right",
        va="bottom",
        fontsize=8.5,
        fontweight="bold",
        color=final_color,
        bbox=dict(
            boxstyle="round,pad=0.4",
            facecolor=COLOR_BG,
            edgecolor=final_color,
            linewidth=0.8,
            alpha=0.95
        ),
        arrowprops=dict(
            arrowstyle="-",
            color=final_color,
            linewidth=0.8,
            alpha=0.8
        )
    )

    month_name = daily_analysis.get("month_name", "")

    ax.set_title(
        f"Дневное выполнение плана: {month_name}",
        fontsize=12,
        fontweight="bold",
        color=COLOR_TEXT,
        pad=14
    )

    ax.set_xlabel("День месяца", fontsize=9, color=COLOR_MUTED, labelpad=8)
    ax.set_ylabel("Выполнение дневного плана, %", fontsize=9, color=COLOR_MUTED, labelpad=8)

    max_pct = max(daily_pct) if daily_pct else 100
    min_pct = min(daily_pct) if daily_pct else 0

    y_min = max(0, min_pct - 12)
    y_max = max(110, max_pct * 1.14)

    ax.set_ylim(y_min, y_max)
    ax.set_xlim(min(days) - 0.6, max(days) + 0.9)

    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}%"))

    if len(days) > 24:
        step = 3
    elif len(days) > 15:
        step = 2
    else:
        step = 1

    ax.set_xticks(days[::step])

    ax.legend(
        loc="lower right",
        fontsize=8.5,
        frameon=True,
        fancybox=True,
        edgecolor=COLOR_GRID,
        facecolor=COLOR_BG,
        labelcolor=COLOR_TEXT
    )

    style_common_axes(ax)

    fig.tight_layout(pad=1.4)
    return fig_to_base64(fig)





def build_monthly_plan_fact_chart_base64(monthly_data, title="Помесячное выполнение плана: План vs Факт"):
    """
    Помесячный график:
    - столбцы: план и факт за каждый месяц отдельно
    - линия: выполнение месячного плана, %
    """
    if not monthly_data:
        return None

    months = [
        f"{MONTH_NAMES_RU[m['month_num'] - 1]} {m['year']}"
        for m in monthly_data
    ]

    plan_values = [float(m["plan"]) for m in monthly_data]
    fact_values = [float(m["fact"]) for m in monthly_data]

    execution_pct = [
        fact / plan * 100 if plan else 0
        for fact, plan in zip(fact_values, plan_values)
    ]

    x = np.arange(len(months))
    width = 0.34

    fig, ax = plt.subplots(figsize=(10.8, 5.2), dpi=150)
    fig.patch.set_facecolor(COLOR_BG)
    ax.set_facecolor(COLOR_BG)

    bars_plan = ax.bar(
        x - width / 2,
        plan_values,
        width,
        label="План",
        color=COLOR_POSITIVE,
        alpha=0.78,
        edgecolor=COLOR_BG,
        linewidth=0.8
    )

    bars_fact = ax.bar(
        x + width / 2,
        fact_values,
        width,
        label="Факт",
        color=COLOR_BAR_SOFT,
        alpha=0.92,
        edgecolor=COLOR_BG,
        linewidth=0.8
    )

    add_bar_labels(ax, bars_plan, plan_values, COLOR_POSITIVE)
    add_bar_labels(ax, bars_fact, fact_values, COLOR_MUTED)

    ax_pct = ax.twinx()

    ax_pct.plot(
        x,
        execution_pct,
        color=COLOR_PRIMARY,
        linewidth=2.2,
        marker="o",
        markersize=5.5,
        markerfacecolor=COLOR_BG,
        markeredgecolor=COLOR_PRIMARY,
        markeredgewidth=1.4,
        label="Выполнение, %"
    )

    ax_pct.axhline(
        100,
        color=COLOR_NEGATIVE,
        linestyle="--",
        linewidth=1.1,
        alpha=0.75
    )

    for xi, pct in zip(x, execution_pct):
        color = COLOR_POSITIVE if pct >= 100 else COLOR_NEGATIVE

        ax_pct.annotate(
            f"{pct:.1f}%",
            xy=(xi, pct),
            xytext=(0, 8 if pct < 100 else -12),
            textcoords="offset points",
            ha="center",
            va="bottom" if pct < 100 else "top",
            fontsize=7.8,
            fontweight="bold",
            color=color,
            bbox=dict(
                boxstyle="round,pad=0.22",
                facecolor=COLOR_BG,
                edgecolor=color,
                linewidth=0.6,
                alpha=0.9
            )
        )

    ax.set_title(
        title,
        fontsize=12,
        fontweight="bold",
        color=COLOR_TEXT,
        pad=14
    )

    ax.set_ylabel("Сумма, руб.", fontsize=9, color=COLOR_MUTED, labelpad=8)
    ax_pct.set_ylabel("Выполнение месячного плана, %", fontsize=9, color=COLOR_MUTED, labelpad=8)

    ax.set_xticks(x)
    ax.set_xticklabels(months, rotation=0, ha="center", fontsize=8.5, color=COLOR_TEXT)

    ax.yaxis.set_major_formatter(FuncFormatter(format_price_axis_ru))
    ax_pct.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}%"))

    max_y = max(max(plan_values), max(fact_values)) if plan_values else 0
    ax.set_ylim(0, max_y * 1.26 if max_y else 1)

    min_pct = min(execution_pct) if execution_pct else 0
    max_pct = max(execution_pct) if execution_pct else 100

    ax_pct.set_ylim(
        max(0, min_pct - 12),
        max(110, max_pct + 12)
    )

    ax_pct.tick_params(axis="y", colors=COLOR_MUTED, labelsize=8.5)
    remove_inner_frame(ax_pct, keep_bottom=False)

    handles_1, labels_1 = ax.get_legend_handles_labels()
    handles_2, labels_2 = ax_pct.get_legend_handles_labels()

    ax.legend(
        handles_1 + handles_2,
        labels_1 + labels_2,
        loc="upper left",
        fontsize=8.5,
        frameon=True,
        fancybox=True,
        edgecolor=COLOR_GRID,
        facecolor=COLOR_BG,
        labelcolor=COLOR_TEXT
    )

    style_common_axes(ax)

    fig.tight_layout(pad=1.4)
    return fig_to_base64(fig)






def build_monthly_delta_waterfall_chart_base64(
    monthly_data,
    title="Вклад месяцев в отклонение от плана"
):
    """
    Waterfall-график помесячных отклонений:
    показывает, какие месяцы увеличили или снизили итоговое отклонение YTD.
    """
    if not monthly_data:
        return None

    months = [
        f"{MONTH_NAMES_RU[m['month_num'] - 1]} {m['year']}"
        for m in monthly_data
    ]

    deltas = [float(m["delta"]) for m in monthly_data]
    cumulative = np.cumsum(deltas)

    starts = [0] + list(cumulative[:-1])
    colors = [
        COLOR_POSITIVE if delta >= 0 else COLOR_NEGATIVE
        for delta in deltas
    ]

    x = np.arange(len(months))

    fig, ax = plt.subplots(figsize=(10.8, 5.2), dpi=150)
    fig.patch.set_facecolor(COLOR_BG)
    ax.set_facecolor(COLOR_BG)

    bars = ax.bar(
        x,
        deltas,
        bottom=starts,
        color=colors,
        alpha=0.82,
        edgecolor=COLOR_BG,
        linewidth=0.9
    )

    # Соединительные линии между столбцами
    for i in range(len(x) - 1):
        ax.plot(
            [x[i] + 0.38, x[i + 1] - 0.38],
            [cumulative[i], cumulative[i]],
            color=COLOR_MUTED,
            linewidth=0.8,
            alpha=0.65
        )

    ax.axhline(
        y=0,
        color=COLOR_MUTED,
        linewidth=1.0,
        alpha=0.7
    )

    # Подписи отклонений
    for i, (bar, delta, start, end) in enumerate(zip(bars, deltas, starts, cumulative)):
        label_y = end
        offset = max(abs(max(cumulative, key=abs)), abs(max(deltas, key=abs))) * 0.035 if deltas else 1

        va = "bottom" if delta >= 0 else "top"
        y_text = label_y + offset if delta >= 0 else label_y - offset

        sign = "+" if delta >= 0 else ""

        ax.text(
            bar.get_x() + bar.get_width() / 2,
            y_text,
            f"{sign}{format_price_axis_ru(delta)}",
            ha="center",
            va=va,
            fontsize=8,
            fontweight="bold",
            color=COLOR_TEXT
        )

    # Итоговая аннотация
    total_delta = cumulative[-1]
    total_color = COLOR_POSITIVE if total_delta >= 0 else COLOR_NEGATIVE
    total_sign = "+" if total_delta >= 0 else ""

    ax.annotate(
        f"Итог YTD: {total_sign}{format_price_axis_ru(total_delta)}",
        xy=(x[-1], cumulative[-1]),
        xytext=(-10, 28 if total_delta >= 0 else -34),
        textcoords="offset points",
        ha="right",
        va="bottom" if total_delta >= 0 else "top",
        fontsize=9,
        fontweight="bold",
        color=total_color,
        bbox=dict(
            boxstyle="round,pad=0.35",
            facecolor=COLOR_BG,
            edgecolor=total_color,
            linewidth=0.8,
            alpha=0.95
        ),
        arrowprops=dict(
            arrowstyle="-",
            color=total_color,
            linewidth=0.8,
            alpha=0.8
        )
    )

    ax.set_title(
        title,
        fontsize=12,
        fontweight="bold",
        color=COLOR_TEXT,
        pad=14
    )

    ax.set_ylabel("Накопленное отклонение, руб.", fontsize=9, color=COLOR_MUTED, labelpad=8)

    ax.set_xticks(x)
    ax.set_xticklabels(months, rotation=0, ha="center", fontsize=8.5, color=COLOR_TEXT)

    ax.yaxis.set_major_formatter(FuncFormatter(format_price_axis_ru))

    y_values = list(cumulative) + starts + [0]
    y_min = min(y_values)
    y_max = max(y_values)

    padding = (y_max - y_min) * 0.22 if y_max != y_min else max(abs(y_max), 1) * 0.25

    ax.set_ylim(y_min - padding, y_max + padding)

    style_common_axes(ax)

    fig.tight_layout(pad=1.4)
    return fig_to_base64(fig)