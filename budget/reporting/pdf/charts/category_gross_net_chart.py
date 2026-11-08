# budget/reporting/pdf/charts/category_gross_net_chart.py
from __future__ import annotations

import base64
from io import BytesIO

import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

from matplotlib.ticker import FuncFormatter

from budget.reporting.pdf.charts.styles import (
    COLOR_BG,
    COLOR_TEXT,
    COLOR_MUTED,
    COLOR_GRID,
    COLOR_BAR_SOFT,
    COLOR_PRIMARY,
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


def build_category_gross_net_chart_base64(rows: list[dict]) -> str | None:
    if not rows:
        return None

    df = pd.DataFrame(rows).copy()
    if df.empty:
        return None

    df["subject_name"] = df["subject_name"].fillna("Не указана").astype(str)
    df["sales_amount"] = _to_numeric(df["sales_amount"])
    df["net_amount"] = _to_numeric(df["net_amount"])
    df["returns_amount"] = _to_numeric(df["returns_amount"])
    df["return_rate_pct"] = _to_numeric(df["return_rate_pct"])

    df = df.sort_values("sales_amount", ascending=True).copy()
    if df.empty:
        return None

    y = np.arange(len(df))
    h = 0.34

    fig_h = max(6.4, 0.52 * len(df) + 2.0)
    fig, ax = plt.subplots(figsize=(12.2, fig_h), dpi=180)
    fig.patch.set_facecolor(COLOR_BG)
    ax.set_facecolor(COLOR_BG)

    ax.barh(
        y + h / 2,
        df["sales_amount"],
        height=h,
        color=COLOR_BAR_SOFT,
        edgecolor="white",
        linewidth=0.8,
        label="Продажи",
        zorder=2,
    )

    ax.barh(
        y - h / 2,
        df["net_amount"],
        height=h,
        color=COLOR_PRIMARY,
        edgecolor="white",
        linewidth=0.8,
        label="Чистая выручка",
        zorder=3,
    )

    ax.set_yticks(y)
    ax.set_yticklabels(df["subject_name"], fontsize=9, color=COLOR_TEXT)

    ax.set_title(
        "Продажи и чистая выручка по категориям",
        fontsize=14,
        fontweight="bold",
        color=COLOR_TEXT,
        pad=14,
    )
    ax.set_xlabel("Рубли", fontsize=10, color=COLOR_TEXT)

    ax.grid(axis="x", linestyle="--", color=COLOR_GRID, alpha=0.45, zorder=1)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(COLOR_GRID)
    ax.spines["bottom"].set_color(COLOR_GRID)

    ax.tick_params(axis="x", labelsize=9, colors=COLOR_MUTED)
    ax.tick_params(axis="y", labelsize=9, colors=COLOR_TEXT)

    max_x = float(df["sales_amount"].max()) if not df.empty else 0
    ax.set_xlim(0, max_x * 1.30 if max_x > 0 else 1)

    ax.xaxis.set_major_formatter(
        FuncFormatter(lambda x, _: f"{int(x):,}".replace(",", " "))
    )

    for i, (_, row) in enumerate(df.iterrows()):
        sales = float(row["sales_amount"])
        net = float(row["net_amount"])
        loss = max(sales - net, 0)
        loss_pct = (loss / sales * 100) if sales else 0

        ax.text(
            sales + max_x * 0.015,
            i,
            f"объем возвратов: {_fmt_money_short(loss)} | {loss_pct:.1f}%",
            va="center",
            ha="left",
            fontsize=8.5,
            color=COLOR_NEGATIVE if loss_pct >= 15 else COLOR_MUTED,
        )

    ax.legend(loc="lower right", frameon=False, fontsize=9)

    ax.text(
        0.01,
        0.02,
        "Разрыв между валовыми продажами и чистой выручкой показывает влияние возвратов на итоговый результат категории.",
        transform=ax.transAxes,
        fontsize=8,
        color=COLOR_MUTED,
        ha="left",
        va="bottom",
    )

    plt.tight_layout()

    buffer = BytesIO()
    fig.savefig(
        buffer,
        format="png",
        dpi=220,
        bbox_inches="tight",
        facecolor=fig.get_facecolor(),
    )
    plt.close(fig)

    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode("utf-8")