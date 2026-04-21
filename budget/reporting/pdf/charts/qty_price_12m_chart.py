# budget/reporting/pdf/charts/qty_price_12m_chart.py

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import FuncFormatter

from budget.reporting.pdf.charts.base import fig_to_base64, remove_inner_frame
from budget.reporting.pdf.charts.helpers import (
    calc_pct_changes,
    format_pct_label,
    format_price_axis_ru,
)
from budget.reporting.pdf.charts.styles import (
    COLOR_BAR_SOFT,
    COLOR_BAR_SOFT_EDGE,
    COLOR_BG,
    COLOR_GRID,
    COLOR_LINE,
    COLOR_LINE_SOFT_BG,
    COLOR_NEGATIVE,
    COLOR_NEUTRAL,
    COLOR_POSITIVE,
    COLOR_TEXT,
)


def build_qty_price_12m_chart_base64(month_rows: list[dict]) -> str | None:
    if not month_rows:
        return None

    labels = [row["month_label"] for row in month_rows]
    qty_values = [float(row["sales_qty"] or 0) for row in month_rows]
    avg_prices = [float(row["avg_price"] or 0) for row in month_rows]
    qty_pct_changes = calc_pct_changes(qty_values)

    fig, ax1 = plt.subplots(figsize=(12.5, 5.2), dpi=170)
    fig.patch.set_facecolor(COLOR_BG)
    ax1.set_facecolor(COLOR_BG)
    x = np.arange(len(labels))

    bars = ax1.bar(
        x,
        qty_values,
        color=COLOR_BAR_SOFT,
        edgecolor=COLOR_BAR_SOFT_EDGE,
        linewidth=0.8,
        width=0.74,
        zorder=3,
    )

    ax1.set_title("Динамика количества продаж и средней цены за 12 месяцев", fontsize=12, color=COLOR_TEXT, pad=14)
    ax1.set_ylabel("Количество продаж, шт.", fontsize=10, color=COLOR_TEXT)
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, rotation=35, ha="right", fontsize=8.5, color=COLOR_TEXT)
    ax1.tick_params(axis="y", labelsize=8.5, colors=COLOR_TEXT, length=0)
    ax1.yaxis.set_major_formatter(FuncFormatter(lambda y, pos: f"{y:,.0f}".replace(",", " ")))
    ax1.grid(axis="y", linestyle="-", linewidth=0.6, color=COLOR_GRID, alpha=0.45, zorder=0)
    remove_inner_frame(ax1, keep_bottom=True)

    max_qty = max(qty_values) if qty_values else 0
    offset_main = max_qty * 0.015 if max_qty else 10
    offset_delta = max_qty * 0.08 if max_qty else 50

    for rect, val in zip(bars, qty_values):
        ax1.text(
            rect.get_x() + rect.get_width() / 2,
            rect.get_height() + offset_main,
            f"{val:,.0f}".replace(",", " "),
            ha="center",
            va="bottom",
            fontsize=8,
            color=COLOR_TEXT,
            fontweight="bold",
        )

    for rect, pct in zip(bars, qty_pct_changes):
        if pct is None:
            continue

        pct_color = COLOR_POSITIVE if pct > 0.1 else COLOR_NEGATIVE if pct < -0.1 else COLOR_NEUTRAL
        ax1.text(
            rect.get_x() + rect.get_width() / 2,
            rect.get_height() + offset_delta,
            f"Δ {format_pct_label(pct)}",
            ha="center",
            va="bottom",
            fontsize=7.4,
            color=pct_color,
            fontweight="bold",
            bbox=dict(facecolor="white", edgecolor="none", boxstyle="round,pad=0.20", alpha=0.88),
        )

    ax2 = ax1.twinx()
    ax2.plot(
        x,
        avg_prices,
        color=COLOR_LINE,
        marker="o",
        markerfacecolor=COLOR_LINE,
        markeredgecolor="white",
        markeredgewidth=1.1,
        linewidth=2.5,
        markersize=6.4,
        zorder=4,
    )
    ax2.set_ylabel("Средняя цена, руб./шт.", fontsize=10, color=COLOR_TEXT)
    ax2.yaxis.set_major_formatter(FuncFormatter(format_price_axis_ru))
    ax2.tick_params(axis="y", labelsize=8.5, colors=COLOR_TEXT)
    ax2.spines["top"].set_visible(False)
    ax2.spines["left"].set_visible(False)
    ax2.spines["bottom"].set_visible(False)
    ax2.spines["right"].set_visible(False)

    if avg_prices:
        price_offset = (max(avg_prices) - min(avg_prices)) * 0.04 if max(avg_prices) != min(avg_prices) else 50
        for xi, yi in zip(x, avg_prices):
            ax2.text(
                xi,
                yi + price_offset,
                f"{yi:,.0f}".replace(",", " "),
                ha="center",
                va="bottom",
                fontsize=8,
                color=COLOR_TEXT,
                fontweight="bold",
                bbox=dict(facecolor=COLOR_LINE_SOFT_BG, edgecolor="none", boxstyle="round,pad=0.20", alpha=0.95),
            )

    fig.tight_layout()
    return fig_to_base64(fig)