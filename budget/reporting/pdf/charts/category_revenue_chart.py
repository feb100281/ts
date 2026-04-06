from __future__ import annotations

import base64
from io import BytesIO

import matplotlib.pyplot as plt
import pandas as pd

from budget.reporting.pdf.charts.styles import (
    COLOR_BG,
    COLOR_TEXT,
    COLOR_MUTED,
    COLOR_GRID,
    COLOR_PRIMARY,
    COLOR_LINE,
    COLOR_NEGATIVE,
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
        return COLOR_PRIMARY
    if return_rate <= 15:
        return COLOR_LINE
    return COLOR_NEGATIVE


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

    fig_h = max(6.2, 0.42 * len(df) + 2.4)
    fig, ax = plt.subplots(figsize=(11.6, fig_h), dpi=180)
    fig.patch.set_facecolor(COLOR_BG)
    ax.set_facecolor(COLOR_BG)

    bars = ax.barh(
        df["subject_name"],
        df["net_amount"],
        color=colors,
        edgecolor="white",
        linewidth=0.8,
        alpha=0.95,
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

    ax.grid(axis="x", linestyle="--", color=COLOR_GRID, alpha=0.45, zorder=1)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(COLOR_GRID)
    ax.spines["bottom"].set_color(COLOR_GRID)

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

    ax.text(
        0.01,
        0.02,
        "Цвет столбца показывает уровень возвратов: зеленый — низкий, желтый — средний, красный — высокий.",
        transform=ax.transAxes,
        fontsize=8,
        color=COLOR_MUTED,
        ha="left",
        va="bottom",
    )

    plt.tight_layout()

    buffer = BytesIO()
    fig.savefig(buffer, format="png", dpi=220, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)

    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode("utf-8")