# # budget/reporting/pdf/revenue_analysis/charts.py
# import matplotlib
# matplotlib.use("Agg")

# import matplotlib.pyplot as plt
# import matplotlib.dates as mdates
# from matplotlib.ticker import FuncFormatter
# from datetime import timedelta
# import io
# import numpy as np


# GREEN = "#1B8A5A"
# RED = "#C0392B"
# BLUE = "#2F5DA8"
# ORANGE = "#D9822B"
# GRID = "#D9DEE7"
# TEXT = "#1F2937"
# MUTED = "#6B7280"


# def _format_money_axis(x, _):
#     x = float(x)
#     if abs(x) >= 1_000_000:
#         return f"{x / 1_000_000:.1f} млн"
#     if abs(x) >= 1_000:
#         return f"{x / 1_000:.0f} тыс"
#     return f"{x:.0f}"


# def _format_money_label(value):
#     value = float(value or 0)
#     if abs(value) >= 1_000_000:
#         return f"{value / 1_000_000:.1f} млн"
#     if abs(value) >= 1_000:
#         return f"{value / 1_000:.0f} тыс"
#     return f"{value:.0f}"


# def generate_revenue_chart_svg(last_10_days, current_semi_analysis=None, report_date=None):
#     """
#     PDF-график:
#     - столбцы: чистая выручка за последние 10 дней;
#     - линия: средняя дневная выручка;
#     - при наличии текущего полугодия: необходимый дневной темп.
#     """

#     plt.rcParams["font.family"] = "DejaVu Sans"
#     plt.rcParams["axes.unicode_minus"] = False
#     plt.rcParams["svg.fonttype"] = "none"

#     dates = [day["date"] for day in last_10_days]
#     revenues = [float(day.get("net_amount", 0) or 0) for day in last_10_days]

#     if not dates:
#         return None

#     avg_revenue = sum(revenues) / len(revenues) if revenues else 0

#     fig, ax = plt.subplots(figsize=(9.2, 3.4))
#     fig.patch.set_facecolor("white")
#     ax.set_facecolor("white")

#     colors = [GREEN if value >= 0 else RED for value in revenues]

#     bars = ax.bar(
#         dates,
#         revenues,
#         width=0.62,
#         color=colors,
#         alpha=0.92,
#         label="Факт за день",
#         zorder=3,
#     )

#     # Средняя линия за 10 дней
#     ax.axhline(
#         avg_revenue,
#         color=BLUE,
#         linewidth=2.2,
#         linestyle="-",
#         label=f"Средняя за 10 дней: {_format_money_label(avg_revenue)} ₽/день",
#         zorder=4,
#     )

#     # Необходимый темп по текущему полугодию
#     required_daily_rate = 0
#     current_daily_rate = 0

#     if current_semi_analysis and current_semi_analysis.get("is_current"):
#         required_daily_rate = float(current_semi_analysis.get("required_daily_rate", 0) or 0)
#         current_daily_rate = float(current_semi_analysis.get("current_daily_rate", 0) or 0)

#         if required_daily_rate > 0:
#             ax.axhline(
#                 required_daily_rate,
#                 color=ORANGE,
#                 linewidth=2.2,
#                 linestyle="--",
#                 label=f"Необходимый темп: {_format_money_label(required_daily_rate)} ₽/день",
#                 zorder=4,
#             )

#     # Подписи над столбцами
#     max_abs = max([abs(v) for v in revenues] + [abs(avg_revenue), abs(required_daily_rate), 1])
#     label_offset = max_abs * 0.035

#     for bar, value in zip(bars, revenues):
#         if value == 0:
#             continue

#         y = value + label_offset if value > 0 else value - label_offset
#         va = "bottom" if value > 0 else "top"

#         ax.text(
#             bar.get_x() + bar.get_width() / 2,
#             y,
#             _format_money_label(value),
#             ha="center",
#             va=va,
#             fontsize=8.5,
#             color=TEXT,
#             zorder=5,
#         )

#     # Блок KPI справа сверху
#     if current_semi_analysis and current_semi_analysis.get("is_current"):
#         exec_pct = float(current_semi_analysis.get("exec_pct", 0) or 0)
#         days_remaining = int(current_semi_analysis.get("days_remaining", 0) or 0)
#         gap_daily_rate = float(current_semi_analysis.get("gap_daily_rate", 0) or 0)

#         kpi_text = (
#             f"Выполнение полугодия: {exec_pct:.1f}%\n"
#             f"Осталось дней: {days_remaining}\n"
#             f"Разрыв: {_format_money_label(gap_daily_rate)} ₽/день"
#         )

#         ax.text(
#             0.985,
#             0.965,
#             kpi_text,
#             transform=ax.transAxes,
#             ha="right",
#             va="top",
#             fontsize=9,
#             color=TEXT,
#             bbox=dict(
#                 boxstyle="round,pad=0.55,rounding_size=0.12",
#                 facecolor="#F8FAFC",
#                 edgecolor="#CBD5E1",
#                 linewidth=0.8,
#             ),
#             zorder=6,
#         )

#     # Заголовок
#     ax.set_title(
#         "Динамика дневной выручки и требуемый темп выполнения плана",
#         fontsize=14,
#         fontweight="bold",
#         color=TEXT,
#         pad=16,
#     )

#     ax.set_ylabel("Выручка, ₽", fontsize=10.5, color=MUTED)
#     ax.set_xlabel("Дата", fontsize=10.5, color=MUTED)

#     # Оси
#     ax.xaxis.set_major_formatter(mdates.DateFormatter("%d.%m"))
#     ax.xaxis.set_major_locator(mdates.DayLocator(interval=1))
#     plt.setp(ax.get_xticklabels(), rotation=0, ha="center", fontsize=9, color=MUTED)

#     ax.yaxis.set_major_formatter(FuncFormatter(_format_money_axis))
#     plt.setp(ax.get_yticklabels(), fontsize=9, color=MUTED)

#     # Сетка и рамки
#     ax.grid(axis="y", color=GRID, linestyle="-", linewidth=0.8, alpha=0.9, zorder=1)
#     ax.grid(axis="x", visible=False)

#     for spine in ["top", "right"]:
#         ax.spines[spine].set_visible(False)

#     ax.spines["left"].set_color("#CBD5E1")
#     ax.spines["bottom"].set_color("#CBD5E1")

#     # Корректный диапазон Y
#     y_values = revenues + [avg_revenue]
#     if required_daily_rate > 0:
#         y_values.append(required_daily_rate)

#     y_min = min(y_values + [0])
#     y_max = max(y_values + [0])
#     y_range = y_max - y_min if y_max != y_min else max(abs(y_max), 1)

#     ax.set_ylim(y_min - y_range * 0.15, y_max + y_range * 0.22)

#     # Легенда снизу
#     ax.legend(
#         loc="upper center",
#         bbox_to_anchor=(0.5, -0.12),
#         ncol=2,
#         frameon=False,
#         fontsize=7.5,
#     )

#     plt.tight_layout(rect=[0, 0.04, 1, 1])

#     svg_buffer = io.BytesIO()
#     plt.savefig(svg_buffer, format="svg", bbox_inches="tight")
#     plt.close(fig)

#     svg_buffer.seek(0)
#     return svg_buffer.getvalue().decode("utf-8")


# def generate_simple_compact_chart(last_10_days):
#     return generate_revenue_chart_svg(last_10_days)



import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import FuncFormatter
import io


GREEN = "#2F7D5C"
BLUE = "#2F5DA8"
ORANGE = "#D9822B"
GRID = "#E5E7EB"
TEXT = "#1F2937"
MUTED = "#6B7280"


def _format_axis(value, _):
    value = float(value or 0)
    if abs(value) >= 1_000_000:
        return f"{value / 1_000_000:.1f}"
    if abs(value) >= 1_000:
        return f"{value / 1_000:.0f} тыс"
    return f"{value:.0f}"


def _format_label(value):
    value = float(value or 0)
    if abs(value) >= 1_000_000:
        return f"{value / 1_000_000:.1f}"
    if abs(value) >= 1_000:
        return f"{value / 1_000:.0f} тыс"
    return f"{value:.0f}"


def generate_revenue_chart_svg(last_10_days, current_semi_analysis=None, report_date=None):
    plt.rcParams["font.family"] = "DejaVu Sans"
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["svg.fonttype"] = "none"

    dates = [day["date"] for day in last_10_days]
    revenues = [float(day.get("net_amount", 0) or 0) for day in last_10_days]

    if not dates:
        return None

    avg_revenue = sum(revenues) / len(revenues)

    required_daily_rate = 0
    if current_semi_analysis and current_semi_analysis.get("is_current"):
        required_daily_rate = float(current_semi_analysis.get("required_daily_rate", 0) or 0)

    fig, ax = plt.subplots(figsize=(8.4, 2.55))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    bars = ax.bar(
        dates,
        revenues,
        width=0.58,
        color=GREEN,
        alpha=0.95,
        label="Факт",
        zorder=3,
    )

    ax.axhline(
        avg_revenue,
        color=BLUE,
        linewidth=1.6,
        linestyle="-",
        label=f"Средняя: {_format_label(avg_revenue)} млн ₽/день",
        zorder=4,
    )

    if required_daily_rate > 0:
        ax.axhline(
            required_daily_rate,
            color=ORANGE,
            linewidth=1.6,
            linestyle="--",
            label=f"Необходимый темп: {_format_label(required_daily_rate)} млн ₽/день",
            zorder=4,
        )

    max_value = max(revenues + [avg_revenue, required_daily_rate, 1])
    label_offset = max_value * 0.025

    for bar, value in zip(bars, revenues):
        if value <= 0:
            continue

        ax.text(
            bar.get_x() + bar.get_width() / 2,
            value + label_offset,
            f"{value / 1_000_000:.1f}",
            ha="center",
            va="bottom",
            fontsize=6.8,
            color=TEXT,
        )

    ax.set_title(
        "Динамика выручки за последние 10 дней",
        fontsize=10.5,
        fontweight="bold",
        color=TEXT,
        pad=8,
    )

    ax.set_ylabel("млн ₽", fontsize=7.5, color=MUTED, labelpad=4)
    ax.set_xlabel("")

    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d.%m"))
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=1))
    plt.setp(ax.get_xticklabels(), rotation=0, ha="center", fontsize=7, color=MUTED)

    ax.yaxis.set_major_formatter(FuncFormatter(_format_axis))
    plt.setp(ax.get_yticklabels(), fontsize=7, color=MUTED)

    ax.grid(axis="y", color=GRID, linestyle="-", linewidth=0.6, alpha=0.9, zorder=1)
    ax.grid(axis="x", visible=False)

    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)

    ax.spines["left"].set_color("#CBD5E1")
    ax.spines["bottom"].set_color("#CBD5E1")
    ax.spines["left"].set_linewidth(0.6)
    ax.spines["bottom"].set_linewidth(0.6)

    y_max = max(revenues + [avg_revenue, required_daily_rate, 1])
    ax.set_ylim(0, y_max * 1.18)

    ax.legend(
        loc="upper center",
        bbox_to_anchor=(0.5, -0.13),
        ncol=3,
        frameon=False,
        fontsize=6.6,
        handlelength=1.6,
        columnspacing=1.2,
    )

    plt.tight_layout(rect=[0.01, 0.05, 0.99, 1])

    svg_buffer = io.BytesIO()
    plt.savefig(svg_buffer, format="svg", bbox_inches="tight")
    plt.close(fig)

    svg_buffer.seek(0)
    return svg_buffer.getvalue().decode("utf-8")


def generate_simple_compact_chart(last_10_days):
    return generate_revenue_chart_svg(last_10_days)