# budget/reporting/pdf/charts/daily_qty_price_scatter_chart.py

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
    COLOR_SCATTER_FILL,
    COLOR_SCATTER_LABEL_BG,
    COLOR_TEXT,
    COLOR_TREND,
)


def build_daily_qty_price_scatter_base64(daily_rows: list[dict]) -> str | None:
    if not daily_rows:
        return None

    qty = np.array([float(row["sales_qty"] or 0) for row in daily_rows], dtype=float)
    price = np.array([float(row["avg_price"] or 0) for row in daily_rows], dtype=float)
    labels = [row["date_label"] for row in daily_rows]

    valid = (qty > 0) & (price > 0)
    qty = qty[valid]
    price = price[valid]
    labels = [label for label, ok in zip(labels, valid) if ok]

    if len(qty) < 5:
        return None

    fig, ax = plt.subplots(figsize=(8.6, 5.5), dpi=180)
    fig.patch.set_facecolor(COLOR_BG)
    ax.set_facecolor(COLOR_BG)

    ax.scatter(qty, price, s=46, color=COLOR_SCATTER_FILL, edgecolors="white", linewidths=0.8, alpha=0.65, zorder=4)

    z = np.polyfit(qty, price, 1)
    p = np.poly1d(z)
    x_line = np.linspace(qty.min(), qty.max(), 200)
    ax.plot(x_line, p(x_line), color=COLOR_TREND, linewidth=2.2, linestyle="-", zorder=3)

    corr = np.corrcoef(qty, price)[0, 1]
    corr_text = f"Дневная корреляция: {corr:.2f}".replace(".", ",")

    idx_candidates = np.argsort(qty)[-3:].tolist() + np.argsort(price)[-3:].tolist()
    idx_candidates = sorted(set(idx_candidates))
    x_span = qty.max() - qty.min() if qty.max() != qty.min() else 1
    y_span = price.max() - price.min() if price.max() != price.min() else 1

    for idx in idx_candidates:
        ax.text(
            qty[idx] + x_span * 0.01,
            price[idx] + y_span * 0.01,
            labels[idx],
            fontsize=7.0,
            color=COLOR_MUTED,
            bbox=dict(facecolor=COLOR_SCATTER_LABEL_BG, edgecolor="none", boxstyle="round,pad=0.15", alpha=0.85),
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

    ax.set_title("Дневная корреляция количества продаж и средней цены за последние 90 дней", fontsize=12, color=COLOR_TEXT, pad=12)
    ax.set_xlabel("Количество продаж за день, шт.", fontsize=10, color=COLOR_TEXT)
    ax.set_ylabel("Средняя цена продажи за день, руб./шт.", fontsize=10, color=COLOR_TEXT)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda x, pos: f"{x:,.0f}".replace(",", " ")))
    ax.yaxis.set_major_formatter(FuncFormatter(format_price_axis_ru))
    ax.tick_params(axis="both", labelsize=8.5, colors=COLOR_TEXT)
    ax.grid(True, linestyle="-", linewidth=0.6, color=COLOR_GRID, alpha=0.42)
    remove_inner_frame(ax, keep_bottom=True)

    fig.tight_layout()
    return fig_to_base64(fig)