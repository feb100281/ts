# budget/reporting/pdf/charts.py
from __future__ import annotations

import base64
from io import BytesIO

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import FuncFormatter


COLOR_PRIMARY = "#1F6F5F"
COLOR_LINE = "#C08B2C"
COLOR_BAR_SOFT = "#6F8F86"
COLOR_BAR_SOFT_EDGE = "#5E7D75"
COLOR_GRID = "#D9D9D9"
COLOR_TEXT = "#1F1F1F"
COLOR_MUTED = "#666666"
COLOR_BORDER = "#BFBFBF"
COLOR_BG = "#FFFFFF"
COLOR_POSITIVE = "#1F6F5F"
COLOR_NEGATIVE = "#9A4F4F"
COLOR_NEUTRAL = "#666666"
COLOR_LINE_SOFT_BG = "#FFF8E8"
COLOR_SCATTER_FILL = "#6F8F86"
COLOR_SCATTER_EDGE = "#FFFFFF"
COLOR_SCATTER_LABEL_BG = "#F7F7F5"
COLOR_TREND = "#C08B2C"


def _fig_to_base64(fig) -> str:
    buffer = BytesIO()
    fig.savefig(buffer, format="png", bbox_inches="tight", facecolor="white")
    plt.close(fig)
    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode("utf-8")


def _remove_inner_frame(ax, keep_bottom=True):
    ax.spines["top"].set_visible(False)
    ax.spines["left"].set_visible(False)
    ax.spines["right"].set_visible(False)
    if keep_bottom:
        ax.spines["bottom"].set_visible(True)
        ax.spines["bottom"].set_color(COLOR_BORDER)
        ax.spines["bottom"].set_linewidth(0.8)
    else:
        ax.spines["bottom"].set_visible(False)


def _format_money_axis_ru(x, pos=None):
    abs_x = abs(x)
    if abs_x >= 1_000_000:
        value = x / 1_000_000
        return f"{value:,.1f} млн".replace(",", " ").replace(".", ",")
    if abs_x >= 1_000:
        value = x / 1_000
        return f"{value:,.0f} тыс".replace(",", " ")
    return f"{x:,.0f}".replace(",", " ")


def _format_price_axis_ru(x, pos=None):
    return f"{x:,.0f}".replace(",", " ")


def _calc_pct_changes(values: list[float]) -> list[float | None]:
    result = [None]
    for i in range(1, len(values)):
        prev = values[i - 1]
        cur = values[i]
        if prev is None or abs(prev) < 0.0001:
            result.append(None)
        else:
            result.append((cur / prev - 1) * 100)
    return result


def _format_pct_label(value: float | None) -> str:
    if value is None:
        return "—"
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.1f}%".replace(".", ",")


def _format_bar_label(value):
    abs_x = abs(value)
    if abs_x >= 1_000_000:
        return f"{value / 1_000_000:.1f} млн".replace(".", ",")
    if abs_x >= 1_000:
        return f"{value / 1_000:.0f} тыс".replace(".", ",")
    return f"{value:,.0f}".replace(",", " ")


def build_sales_12m_chart_base64(month_rows: list[dict]) -> str | None:
    if not month_rows:
        return None

    labels = [row["month_label"] for row in month_rows]
    net_values = [float(row["net_amount"] or 0) for row in month_rows]
    avg_prices = [float(row["avg_price"] or 0) for row in month_rows]
    pct_changes = _calc_pct_changes(net_values)

    fig, ax1 = plt.subplots(figsize=(12.5, 5.2), dpi=170)
    fig.patch.set_facecolor(COLOR_BG)
    ax1.set_facecolor(COLOR_BG)
    x = np.arange(len(labels))

    bars = ax1.bar(
        x, net_values,
        color=COLOR_BAR_SOFT,
        edgecolor=COLOR_BAR_SOFT_EDGE,
        linewidth=0.8,
        width=0.74,
        zorder=3,
    )

    ax1.set_title("Динамика чистой выручки и средней цены продажи за 12 месяцев", fontsize=12, color=COLOR_TEXT, pad=14)
    ax1.set_ylabel("Чистая выручка, руб.", fontsize=10, color=COLOR_TEXT)
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, rotation=35, ha="right", fontsize=8.5, color=COLOR_TEXT)
    ax1.yaxis.set_major_formatter(FuncFormatter(_format_money_axis_ru))
    ax1.tick_params(axis="y", labelsize=8.5, colors=COLOR_TEXT, length=0)
    ax1.grid(axis="y", linestyle="-", linewidth=0.6, color=COLOR_GRID, alpha=0.45, zorder=0)
    _remove_inner_frame(ax1, keep_bottom=True)

    max_val = max(net_values) if net_values else 0
    offset_main = max_val * 0.015 if max_val else 1000
    offset_delta = max_val * 0.08 if max_val else 4000

    for rect, val in zip(bars, net_values):
        ax1.text(
            rect.get_x() + rect.get_width() / 2,
            rect.get_height() + offset_main,
            _format_bar_label(val),
            ha="center", va="bottom", fontsize=8, color=COLOR_TEXT, fontweight="bold",
        )

    for rect, pct in zip(bars, pct_changes):
        if pct is None:
            continue
        pct_color = COLOR_POSITIVE if pct > 0.1 else COLOR_NEGATIVE if pct < -0.1 else COLOR_NEUTRAL
        ax1.text(
            rect.get_x() + rect.get_width() / 2,
            rect.get_height() + offset_delta,
            f"Δ {_format_pct_label(pct)}",
            ha="center", va="bottom", fontsize=7.4, color=pct_color, fontweight="bold",
            bbox=dict(facecolor="white", edgecolor="none", boxstyle="round,pad=0.20", alpha=0.88),
        )

    ax2 = ax1.twinx()
    ax2.plot(
        x, avg_prices,
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
    ax2.yaxis.set_major_formatter(FuncFormatter(_format_price_axis_ru))
    ax2.tick_params(axis="y", labelsize=8.5, colors=COLOR_TEXT)
    ax2.spines["top"].set_visible(False)
    ax2.spines["left"].set_visible(False)
    ax2.spines["bottom"].set_visible(False)
    ax2.spines["right"].set_visible(False)

    if avg_prices:
        price_offset = (max(avg_prices) - min(avg_prices)) * 0.04 if max(avg_prices) != min(avg_prices) else 50
        for xi, yi in zip(x, avg_prices):
            ax2.text(
                xi, yi + price_offset,
                f"{yi:,.0f}".replace(",", " "),
                ha="center", va="bottom", fontsize=8, color=COLOR_TEXT, fontweight="bold",
                bbox=dict(facecolor=COLOR_LINE_SOFT_BG, edgecolor="none", boxstyle="round,pad=0.20", alpha=0.95),
            )

    fig.tight_layout()
    return _fig_to_base64(fig)


def build_qty_price_12m_chart_base64(month_rows: list[dict]) -> str | None:
    if not month_rows:
        return None

    labels = [row["month_label"] for row in month_rows]
    qty_values = [float(row["sales_qty"] or 0) for row in month_rows]
    avg_prices = [float(row["avg_price"] or 0) for row in month_rows]
    qty_pct_changes = _calc_pct_changes(qty_values)

    fig, ax1 = plt.subplots(figsize=(12.5, 5.2), dpi=170)
    fig.patch.set_facecolor(COLOR_BG)
    ax1.set_facecolor(COLOR_BG)
    x = np.arange(len(labels))

    bars = ax1.bar(
        x, qty_values,
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
    _remove_inner_frame(ax1, keep_bottom=True)

    max_qty = max(qty_values) if qty_values else 0
    offset_main = max_qty * 0.015 if max_qty else 10
    offset_delta = max_qty * 0.08 if max_qty else 50

    for rect, val in zip(bars, qty_values):
        ax1.text(
            rect.get_x() + rect.get_width() / 2,
            rect.get_height() + offset_main,
            f"{val:,.0f}".replace(",", " "),
            ha="center", va="bottom", fontsize=8, color=COLOR_TEXT, fontweight="bold",
        )

    for rect, pct in zip(bars, qty_pct_changes):
        if pct is None:
            continue
        pct_color = COLOR_POSITIVE if pct > 0.1 else COLOR_NEGATIVE if pct < -0.1 else COLOR_NEUTRAL
        ax1.text(
            rect.get_x() + rect.get_width() / 2,
            rect.get_height() + offset_delta,
            f"Δ {_format_pct_label(pct)}",
            ha="center", va="bottom", fontsize=7.4, color=pct_color, fontweight="bold",
            bbox=dict(facecolor="white", edgecolor="none", boxstyle="round,pad=0.20", alpha=0.88),
        )

    ax2 = ax1.twinx()
    ax2.plot(
        x, avg_prices,
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
    ax2.yaxis.set_major_formatter(FuncFormatter(_format_price_axis_ru))
    ax2.tick_params(axis="y", labelsize=8.5, colors=COLOR_TEXT)
    ax2.spines["top"].set_visible(False)
    ax2.spines["left"].set_visible(False)
    ax2.spines["bottom"].set_visible(False)
    ax2.spines["right"].set_visible(False)

    if avg_prices:
        price_offset = (max(avg_prices) - min(avg_prices)) * 0.04 if max(avg_prices) != min(avg_prices) else 50
        for xi, yi in zip(x, avg_prices):
            ax2.text(
                xi, yi + price_offset,
                f"{yi:,.0f}".replace(",", " "),
                ha="center", va="bottom", fontsize=8, color=COLOR_TEXT, fontweight="bold",
                bbox=dict(facecolor=COLOR_LINE_SOFT_BG, edgecolor="none", boxstyle="round,pad=0.20", alpha=0.95),
            )

    fig.tight_layout()
    return _fig_to_base64(fig)


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
            x_val + x_offset, y_val + y_offset, label,
            fontsize=7.4, color=COLOR_MUTED, va="bottom", ha="left",
            bbox=dict(facecolor=COLOR_SCATTER_LABEL_BG, edgecolor="none", boxstyle="round,pad=0.18", alpha=0.88),
            zorder=5,
        )

    ax.text(
        0.985, 0.96, corr_text,
        transform=ax.transAxes, ha="right", va="top",
        fontsize=8.2, color=COLOR_TEXT, fontweight="bold",
        bbox=dict(facecolor=COLOR_LINE_SOFT_BG, edgecolor="none", boxstyle="round,pad=0.28", alpha=0.95),
        zorder=6,
    )

    ax.set_title("Корреляция количества продаж и средней цены", fontsize=12, color=COLOR_TEXT, pad=12)
    ax.set_xlabel("Количество проданных единиц, шт.", fontsize=10, color=COLOR_TEXT)
    ax.set_ylabel("Средняя цена продажи, руб./шт.", fontsize=10, color=COLOR_TEXT)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda x, pos: f"{x:,.0f}".replace(",", " ")))
    ax.yaxis.set_major_formatter(FuncFormatter(_format_price_axis_ru))
    ax.tick_params(axis="both", labelsize=8.5, colors=COLOR_TEXT)
    ax.grid(True, linestyle="-", linewidth=0.6, color=COLOR_GRID, alpha=0.42)
    _remove_inner_frame(ax, keep_bottom=True)

    fig.tight_layout()
    return _fig_to_base64(fig)


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

    # Подписываем только экстремумы, чтобы не перегружать
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
        0.985, 0.96, corr_text,
        transform=ax.transAxes, ha="right", va="top",
        fontsize=8.2, color=COLOR_TEXT, fontweight="bold",
        bbox=dict(facecolor=COLOR_LINE_SOFT_BG, edgecolor="none", boxstyle="round,pad=0.28", alpha=0.95),
        zorder=6,
    )

    ax.set_title("Дневная корреляция количества продаж и средней цены за последние 90 дней", fontsize=12, color=COLOR_TEXT, pad=12)
    ax.set_xlabel("Количество продаж за день, шт.", fontsize=10, color=COLOR_TEXT)
    ax.set_ylabel("Средняя цена продажи за день, руб./шт.", fontsize=10, color=COLOR_TEXT)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda x, pos: f"{x:,.0f}".replace(",", " ")))
    ax.yaxis.set_major_formatter(FuncFormatter(_format_price_axis_ru))
    ax.tick_params(axis="both", labelsize=8.5, colors=COLOR_TEXT)
    ax.grid(True, linestyle="-", linewidth=0.6, color=COLOR_GRID, alpha=0.42)
    _remove_inner_frame(ax, keep_bottom=True)

    fig.tight_layout()
    return _fig_to_base64(fig)


def build_revenue_waterfall_base64(waterfall_data: dict | None) -> str | None:
    if not waterfall_data:
        return None

    start_value = float(waterfall_data["start_value"] or 0)
    end_value = float(waterfall_data["end_value"] or 0)
    steps = waterfall_data["steps"]

    labels = [waterfall_data["start_label"]] + [s["label"] for s in steps] + [waterfall_data["end_label"]]
    values = [start_value] + [float(s["value"] or 0) for s in steps] + [end_value]

    cumulative = [0]
    running = start_value
    for step in steps:
        cumulative.append(running)
        running += float(step["value"] or 0)
    cumulative.append(0)

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
        ax.plot([x[i - 1] + 0.36, x[i] - 0.36], [bottoms[i], bottoms[i]], color=COLOR_BORDER, linewidth=1.0, zorder=2)

    ax.set_title("Waterfall: изменение чистой выручки к предыдущему месяцу", fontsize=12, color=COLOR_TEXT, pad=12)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=20, ha="right", fontsize=8.5, color=COLOR_TEXT)
    ax.yaxis.set_major_formatter(FuncFormatter(_format_money_axis_ru))
    ax.tick_params(axis="y", labelsize=8.5, colors=COLOR_TEXT, length=0)
    ax.grid(axis="y", linestyle="-", linewidth=0.6, color=COLOR_GRID, alpha=0.42, zorder=0)
    _remove_inner_frame(ax, keep_bottom=True)

    ymax = max([bottoms[i] + abs(heights[i]) for i in range(len(heights))] + [0])
    offset = ymax * 0.02 if ymax else 1000

    for rect, v, b in zip(bars, heights, bottoms):
        y = b + abs(v)
        ax.text(
            rect.get_x() + rect.get_width() / 2,
            y + offset,
            _format_bar_label(v),
            ha="center",
            va="bottom",
            fontsize=7.8,
            color=COLOR_TEXT,
            fontweight="bold",
        )

    fig.tight_layout()
    return _fig_to_base64(fig)