# budget/reporting/pdf/charts/category_revenue_chart.py
from __future__ import annotations

import base64
from io import BytesIO

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import FuncFormatter  # 👈 добавили

from budget.reporting.pdf.charts.styles import (
    COLOR_BG,
    COLOR_TEXT,
    COLOR_MUTED,
    COLOR_GRID,
    COLOR_PRIMARY,
    COLOR_NEGATIVE,
    COLOR_CATEGORY_LOW_RISK,      
    COLOR_CATEGORY_MEDIUM_RISK,  
    COLOR_CATEGORY_HIGH_RISK, 
)


def _to_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").fillna(0)


def _fmt_money_short(v: float) -> str:
    if v >= 1_000_000:
        return f"{v / 1_000_000:.1f} млн ₽"
    if v >= 1_000:
        return f"{v / 1_000:.0f} тыс ₽"
    return f"{v:,.0f} ₽".replace(",", " ")


def _risk_color(return_rate: float) -> str:
    if return_rate <= 10:
        return COLOR_CATEGORY_LOW_RISK
    if return_rate <= 18:
        return COLOR_CATEGORY_MEDIUM_RISK
    return COLOR_CATEGORY_HIGH_RISK


def build_category_revenue_chart_base64(rows: list[dict]) -> str | None:
    if not rows:
        return None

    df = pd.DataFrame(rows).copy()
    if df.empty:
        return None

    df["subject_name"] = df["subject_name"].fillna("Не указана").astype(str)
    df["net_amount"] = _to_numeric(df["net_amount"])
    df["return_rate_pct"] = _to_numeric(df["return_rate_pct"])
    df["revenue_share_pct"] = _to_numeric(df["revenue_share_pct"])
    df["avg_sku_price"] = _to_numeric(df["avg_sku_price"])

    df = df.sort_values("net_amount", ascending=True).copy()
    if df.empty:
        return None

    colors = df["return_rate_pct"].apply(_risk_color).tolist()

    fig_h = max(4.5, 0.30 * len(df) + 2.4)
    fig, ax = plt.subplots(figsize=(11.6, fig_h), dpi=180)
    fig.patch.set_facecolor(COLOR_BG)
    ax.set_facecolor(COLOR_BG)

    bars = ax.barh(
        df["subject_name"],
        df["net_amount"],
        color=colors,
        edgecolor="white",
        linewidth=0.8,
        alpha=0.92,
        zorder=3,
    )

    ax.set_title(
        "Категории по чистой выручке",
        fontsize=14,
        fontweight="bold",
        color=COLOR_TEXT,
        pad=14,
    )
    ax.set_xlabel("Чистая выручка, руб.", fontsize=10, color=COLOR_TEXT)

    # 🔥 ВАЖНО: убираем экспоненту и задаём свой формат
    ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _: _fmt_money_short(x)))

    ax.grid(axis="x", linestyle="-", linewidth=0.5, color=COLOR_GRID, alpha=0.35, zorder=1)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(COLOR_GRID)
    ax.spines["left"].set_linewidth(0.5)
    ax.spines["bottom"].set_color(COLOR_GRID)
    ax.spines["bottom"].set_linewidth(0.5)

    ax.tick_params(axis="x", labelsize=9, colors=COLOR_MUTED)
    ax.tick_params(axis="y", labelsize=9, colors=COLOR_TEXT)

    max_x = float(df["net_amount"].max()) if not df.empty else 0
    ax.set_xlim(0, max_x * 1.28 if max_x > 0 else 1)

    for bar, (_, row) in zip(bars, df.iterrows()):
        x = float(bar.get_width())
        y = bar.get_y() + bar.get_height() / 2

        label = (
            f"{_fmt_money_short(row['net_amount'])}   "
            f"| доля {row['revenue_share_pct']:.1f}%   "
            f"| возвраты {row['return_rate_pct']:.1f}%"
        )

        ax.text(
            x + max_x * 0.015,
            y,
            label,
            va="center",
            ha="left",
            fontsize=8.5,
            color=COLOR_TEXT,
        )

    legend_elements = [
        plt.Rectangle((0, 0), 1, 1, facecolor=COLOR_CATEGORY_LOW_RISK, edgecolor='none', alpha=0.88, label='≤10% — низкая возвратность'),
        plt.Rectangle((0, 0), 1, 1, facecolor=COLOR_CATEGORY_MEDIUM_RISK, edgecolor='none', alpha=0.88, label='11-18% — средняя возвратность'),
        plt.Rectangle((0, 0), 1, 1, facecolor=COLOR_CATEGORY_HIGH_RISK, edgecolor='none', alpha=0.88, label='>18% — высокая возвратность'),
    ]

    ax.legend(
        handles=legend_elements,
        loc='lower center',
        bbox_to_anchor=(0.5, -0.1),
        ncol=3,
        fontsize=7.5,
        frameon=False,
    )

    plt.tight_layout()

    buffer = BytesIO()
    fig.savefig(buffer, format="png", dpi=220, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)

    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode("utf-8")