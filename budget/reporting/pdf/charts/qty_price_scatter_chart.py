# budget/reporting/pdf/charts/qty_price_scatter_chart.py

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import FuncFormatter

from budget.reporting.pdf.charts.base import fig_to_base64, remove_inner_frame
from budget.reporting.pdf.charts.helpers import format_price_axis_ru
from budget.reporting.pdf.charts.styles import (
    COLOR_BG,
    COLOR_GRID,
    COLOR_LINE_SOFT_BG,
    COLOR_MUTED,
    COLOR_SCATTER_EDGE,
    COLOR_SCATTER_FILL,
    COLOR_SCATTER_LABEL_BG,
    COLOR_TEXT,
    COLOR_TREND,
)


def build_qty_price_scatter_base64(month_rows: list[dict]) -> str | None:
    if not month_rows:
        return None

    qty = np.array([float(row["sales_qty"] or 0) for row in month_rows], dtype=float)
    price = np.array([float(row["avg_price"] or 0) for row in month_rows], dtype=float)
    labels = [row["month_label"] for row in month_rows]

    valid = (qty > 0) & (price > 0)
    qty = qty[valid]
    price = price[valid]
    labels = [label for label, ok in zip(labels, valid) if ok]

    if len(qty) < 2:
        return None

    fig, ax = plt.subplots(figsize=(8.2, 5.4), dpi=180)
    fig.patch.set_facecolor(COLOR_BG)
    ax.set_facecolor(COLOR_BG)

    ax.scatter(qty, price, s=110, color=COLOR_SCATTER_FILL, edgecolors=COLOR_SCATTER_EDGE, linewidths=1.3, alpha=0.92, zorder=4)
    ax.scatter(qty, price, s=210, color=COLOR_SCATTER_FILL, alpha=0.10, edgecolors="none", zorder=3)

    z = np.polyfit(qty, price, 1)
    p = np.poly1d(z)
    x_line = np.linspace(qty.min(), qty.max(), 200)
    ax.plot(x_line, p(x_line), color=COLOR_TREND, linewidth=2.4, linestyle="-", zorder=2)

    corr = np.corrcoef(qty, price)[0, 1]
    corr_text = f"Коэффициент корреляции: {corr:.2f}".replace(".", ",")

    x_span = qty.max() - qty.min() if qty.max() != qty.min() else 1
    y_span = price.max() - price.min() if price.max() != price.min() else 1
    x_offset = x_span * 0.015
    y_offset = y_span * 0.018

    for x_val, y_val, label in zip(qty, price, labels):
        ax.text(
            x_val + x_offset,
            y_val + y_offset,
            label,
            fontsize=7.4,
            color=COLOR_MUTED,
            va="bottom",
            ha="left",
            bbox=dict(facecolor=COLOR_SCATTER_LABEL_BG, edgecolor="none", boxstyle="round,pad=0.18", alpha=0.88),
            zorder=5,
        )

    ax.text(
        0.985,
        0.96,
        corr_text,
        transform=ax.transAxes,
        ha="right",
        va="top",
        fontsize=8.2,
        color=COLOR_TEXT,
        fontweight="bold",
        bbox=dict(facecolor=COLOR_LINE_SOFT_BG, edgecolor="none", boxstyle="round,pad=0.28", alpha=0.95),
        zorder=6,
    )

    ax.set_title("Корреляция количества продаж и средней цены", fontsize=12, color=COLOR_TEXT, pad=12)
    ax.set_xlabel("Количество проданных единиц, шт.", fontsize=10, color=COLOR_TEXT)
    ax.set_ylabel("Средняя цена продажи, руб./шт.", fontsize=10, color=COLOR_TEXT)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda x, pos: f"{x:,.0f}".replace(",", " ")))
    ax.yaxis.set_major_formatter(FuncFormatter(format_price_axis_ru))
    ax.tick_params(axis="both", labelsize=8.5, colors=COLOR_TEXT)
    ax.grid(True, linestyle="-", linewidth=0.6, color=COLOR_GRID, alpha=0.42)
    remove_inner_frame(ax, keep_bottom=True)

    fig.tight_layout()
    return fig_to_base64(fig)