# budget/reporting/pdf/charts/revenue_waterfall_chart.py

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import FuncFormatter

from budget.reporting.pdf.charts.base import fig_to_base64, remove_inner_frame
from budget.reporting.pdf.charts.helpers import format_bar_label, format_money_axis_ru
from budget.reporting.pdf.charts.styles import (
    COLOR_BAR_SOFT,
    COLOR_BG,
    COLOR_BORDER,
    COLOR_GRID,
    COLOR_NEGATIVE,
    COLOR_NEUTRAL,
    COLOR_POSITIVE,
    COLOR_TEXT,
)


def build_revenue_waterfall_base64(waterfall_data: dict | None) -> str | None:
    if not waterfall_data:
        return None

    start_value = float(waterfall_data["start_value"] or 0)
    end_value = float(waterfall_data["end_value"] or 0)
    steps = waterfall_data["steps"]

    labels = [waterfall_data["start_label"]] + [s["label"] for s in steps] + [waterfall_data["end_label"]]
    heights = [start_value] + [float(s["value"] or 0) for s in steps] + [end_value]

    colors = [COLOR_BAR_SOFT]
    for step in steps:
        v = float(step["value"] or 0)
        colors.append(COLOR_POSITIVE if v > 0 else COLOR_NEGATIVE if v < 0 else COLOR_NEUTRAL)
    colors.append(COLOR_BAR_SOFT)

    bottoms = [0]
    running = start_value
    for step in steps:
        v = float(step["value"] or 0)
        bottoms.append(running if v >= 0 else running + v)
        running += v
    bottoms.append(0)

    fig, ax = plt.subplots(figsize=(11.5, 4.8), dpi=170)
    fig.patch.set_facecolor(COLOR_BG)
    ax.set_facecolor(COLOR_BG)

    x = np.arange(len(labels))
    bars = ax.bar(x, [abs(v) for v in heights], bottom=bottoms, color=colors, width=0.72, zorder=3)

    for i in range(1, len(labels) - 1):
        ax.plot(
            [x[i - 1] + 0.36, x[i] - 0.36],
            [bottoms[i], bottoms[i]],
            color=COLOR_BORDER,
            linewidth=1.0,
            zorder=2,
        )

    ax.set_title("Waterfall: изменение чистой выручки к предыдущему месяцу", fontsize=12, color=COLOR_TEXT, pad=12)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=20, ha="right", fontsize=8.5, color=COLOR_TEXT)
    ax.yaxis.set_major_formatter(FuncFormatter(format_money_axis_ru))
    ax.tick_params(axis="y", labelsize=8.5, colors=COLOR_TEXT, length=0)
    ax.grid(axis="y", linestyle="-", linewidth=0.6, color=COLOR_GRID, alpha=0.42, zorder=0)
    remove_inner_frame(ax, keep_bottom=True)

    ymax = max([bottoms[i] + abs(heights[i]) for i in range(len(heights))] + [0])
    offset = ymax * 0.02 if ymax else 1000

    for rect, v, b in zip(bars, heights, bottoms):
        y = b + abs(v)
        ax.text(
            rect.get_x() + rect.get_width() / 2,
            y + offset,
            format_bar_label(v),
            ha="center",
            va="bottom",
            fontsize=7.8,
            color=COLOR_TEXT,
            fontweight="bold",
        )

    fig.tight_layout()
    return fig_to_base64(fig)