# budget/reporting/pdf/charts/certificate_category_risk_chart.py
# budget/reporting/pdf/charts/certificate_category_risk_chart.py
from __future__ import annotations

import base64
from io import BytesIO

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import FuncFormatter

from budget.reporting.pdf.charts.styles import (
    COLOR_BG,
    COLOR_BAR_SOFT,
    COLOR_BAR_SOFT_EDGE,
    COLOR_BORDER,
    COLOR_GRID,
    COLOR_LINE_SOFT_BG,
    COLOR_MUTED,
    COLOR_PRIMARY,
    COLOR_TEXT,
)


def _format_money(value: float) -> str:
    return f"{float(value):,.0f}".replace(",", " ")


def _format_money_tick(value: float, _pos=None) -> str:
    value = float(value or 0)

    if value >= 1_000_000_000:
        return f"{value / 1_000_000_000:.1f} млрд"
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f} млн"
    if value >= 1_000:
        return f"{value / 1_000:.0f} тыс"
    return f"{value:,.0f}".replace(",", " ")


def _short_name(x: str, max_len: int = 34) -> str:
    x = str(x or "").strip()
    if len(x) <= max_len:
        return x
    return x[: max_len - 3].rstrip() + "..."


def build_certificate_category_risk_chart_base64(
    rows: list[dict],
    limit: int = 8,
) -> str | None:
    if not rows:
        return None

    df = pd.DataFrame(rows).copy()
    if df.empty:
        return None

    df["sales_amount_90d"] = pd.to_numeric(
        df.get("sales_amount_90d"), errors="coerce"
    ).fillna(0)

    df["subject_name"] = df.get("subject_name", pd.Series(dtype="object")).fillna("Не указана")

    # Только значимые строки
    df = df[df["sales_amount_90d"] > 0].copy()
    if df.empty:
        return None

    # Топ категорий по риску
    df = df.sort_values("sales_amount_90d", ascending=False).head(limit).copy()
    if df.empty:
        return None

    df["label"] = df["subject_name"].map(lambda x: _short_name(x, max_len=34))

    # Чтобы самый большой столбец был сверху
    df = df.iloc[::-1].copy()

    n = len(df)
    fig_height = max(4.8, 0.72 * n + 1.6)

    fig, ax = plt.subplots(figsize=(11.6, fig_height), dpi=180)
    fig.patch.set_facecolor(COLOR_BG)
    ax.set_facecolor(COLOR_BG)

    values = df["sales_amount_90d"].tolist()
    labels = df["label"].tolist()

    bars = ax.barh(
        labels,
        values,
        height=0.62,
        color=COLOR_BAR_SOFT,
        edgecolor=COLOR_BAR_SOFT_EDGE,
        linewidth=0.9,
        zorder=3,
    )

    max_value = max(values) if values else 0
    x_pad = max_value * 0.16 if max_value > 0 else 1
    ax.set_xlim(0, max_value + x_pad)

    ax.set_title(
        "Риск по категориям: продажи SKU в зоне сертификационного риска",
        fontsize=14,
        fontweight="bold",
        color=COLOR_TEXT,
        pad=16,
    )

    ax.set_xlabel(
        "Продажи за 90 дней, ₽",
        fontsize=10,
        color=COLOR_TEXT,
        labelpad=10,
    )

    ax.xaxis.set_major_formatter(FuncFormatter(_format_money_tick))

    ax.grid(
        axis="x",
        linestyle="--",
        linewidth=0.8,
        color=COLOR_GRID,
        alpha=0.75,
        zorder=1,
    )
    ax.grid(axis="y", visible=False)

    # Оси
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(COLOR_BORDER)
    ax.spines["bottom"].set_color(COLOR_BORDER)
    ax.spines["left"].set_linewidth(0.8)
    ax.spines["bottom"].set_linewidth(0.8)

    ax.tick_params(axis="x", labelsize=9, colors=COLOR_MUTED)
    ax.tick_params(axis="y", labelsize=9.5, colors=COLOR_TEXT, length=0)

    # Подписи значений справа от баров
    for bar, value in zip(bars, values):
        ax.text(
            bar.get_width() + max_value * 0.012,
            bar.get_y() + bar.get_height() / 2,
            f"{_format_money(value)} ₽",
            va="center",
            ha="left",
            fontsize=9,
            color=COLOR_TEXT,
            fontweight="semibold",
            zorder=5,
            bbox=dict(
                boxstyle="round,pad=0.18,rounding_size=0.12",
                facecolor=COLOR_BG,
                edgecolor="none",
                alpha=0.92,
            ),
        )

    # Мягкий акцент слева — в фирменном стиле
    ax.axvline(
        x=0,
        color=COLOR_PRIMARY,
        linewidth=2.0,
        alpha=0.95,
        zorder=4,
    )

    # Комментарий снизу
    subtitle = (
        "График показывает категории с наибольшим объемом продаж SKU, "
        "находящихся в зоне сертификационного риска за последние 90 дней."
    )

    ax.text(
        0.0,
        -0.14,
        subtitle,
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=8.8,
        color=COLOR_MUTED,
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