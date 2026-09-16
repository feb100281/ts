from __future__ import annotations

import base64
from io import BytesIO
from textwrap import shorten

import matplotlib.pyplot as plt
import pandas as pd

from budget.reporting.pdf.charts.styles import (
    COLOR_BG,
    COLOR_TEXT,
    COLOR_MUTED,
    COLOR_GRID,
    COLOR_PRIMARY,
    COLOR_NEGATIVE,
    COLOR_SCATTER_FILL,
    COLOR_SCATTER_EDGE,
    COLOR_SCATTER_LABEL_BG,
    COLOR_LINE_SOFT_BG,
)

COLOR_GOOD = COLOR_PRIMARY
COLOR_BAD = COLOR_NEGATIVE
COLOR_DOT = COLOR_SCATTER_FILL


def _to_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").fillna(0)


def _format_label(text: str, width: int = 18) -> str:
    text = str(text or "").strip()
    if not text:
        return "—"
    return shorten(text, width=width, placeholder="…")


def _size_scale(series: pd.Series) -> pd.Series:
    s = _to_numeric(series)
    if s.empty:
        return s
    min_v = float(s.min())
    max_v = float(s.max())

    if max_v <= 0:
        return pd.Series([500] * len(s), index=s.index)

    if max_v == min_v:
        return pd.Series([900] * len(s), index=s.index)

    norm = (s - min_v) / (max_v - min_v)
    return 350 + norm * 1600


def build_category_risk_matrix_chart_base64(rows: list[dict]) -> str | None:
    if not rows:
        return None

    df = pd.DataFrame(rows).copy()
    if df.empty:
        return None

    df["subject_name"] = df["subject_name"].fillna("Не указана").astype(str)
    df["revenue_share_pct"] = _to_numeric(df["revenue_share_pct"])
    df["return_rate_pct"] = _to_numeric(df["return_rate_pct"])
    df["net_amount"] = _to_numeric(df["net_amount"])

    df = df[(df["revenue_share_pct"] > 0) & (df["return_rate_pct"] >= 0)].copy()
    if df.empty:
        return None

    df["bubble_size"] = _size_scale(df["net_amount"])

    x = df["revenue_share_pct"]
    y = df["return_rate_pct"]

    x_mid = float(x.median())
    y_mid = float(y.median())

    x_min = 0
    x_max = float(x.max()) * 1.15
    y_min = 0
    y_max = float(y.max()) * 1.15

    fig, ax = plt.subplots(figsize=(10.8, 6.6), dpi=180)
    fig.patch.set_facecolor(COLOR_BG)
    ax.set_facecolor(COLOR_BG)

    # зоны
    ax.axvspan(x_min, x_mid, ymin=0, ymax=(y_mid - y_min) / (y_max - y_min + 1e-9), color="#EEF6F2", alpha=0.55, zorder=0)
    ax.axvspan(x_mid, x_max, ymin=0, ymax=(y_mid - y_min) / (y_max - y_min + 1e-9), color="#F2F7FB", alpha=0.45, zorder=0)
    ax.axvspan(x_min, x_mid, ymin=(y_mid - y_min) / (y_max - y_min + 1e-9), ymax=1, color="#FBF6EE", alpha=0.45, zorder=0)
    ax.axvspan(x_mid, x_max, ymin=(y_mid - y_min) / (y_max - y_min + 1e-9), ymax=1, color="#FBEEEE", alpha=0.42, zorder=0)

    ax.scatter(
        x,
        y,
        s=df["bubble_size"],
        c=COLOR_DOT,
        alpha=0.68,
        edgecolors=COLOR_SCATTER_EDGE,
        linewidths=1.0,
        zorder=3,
    )

    ax.axvline(x_mid, linestyle="--", linewidth=1.0, color=COLOR_GRID, zorder=2)
    ax.axhline(y_mid, linestyle="--", linewidth=1.0, color=COLOR_GRID, zorder=2)

    ax.set_title(
        "Матрица категорий: доля в выручке и возвратность",
        fontsize=14,
        fontweight="bold",
        color=COLOR_TEXT,
        pad=14,
    )
    ax.set_xlabel("Доля категории в продажах, %", fontsize=10, color=COLOR_TEXT)
    ax.set_ylabel("Возвратность, %", fontsize=10, color=COLOR_TEXT)

    ax.set_xlim(x_min, x_max)
    ax.set_ylim(y_min, y_max)

    ax.grid(True, linestyle="--", color=COLOR_GRID, alpha=0.45, zorder=1)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(COLOR_GRID)
    ax.spines["bottom"].set_color(COLOR_GRID)

    ax.tick_params(axis="x", labelsize=9, colors=COLOR_MUTED)
    ax.tick_params(axis="y", labelsize=9, colors=COLOR_MUTED)

    # подписи только важных точек
    label_df = pd.concat([
        df.sort_values("net_amount", ascending=False).head(6),
        df.sort_values("return_rate_pct", ascending=False).head(4),
    ]).drop_duplicates(subset=["subject_name"]).head(9)

    offsets = [(8, 8), (12, -10), (-16, 10), (10, 12), (-18, -10), (8, -14), (14, 6), (-20, 12), (10, 14)]

    for i, (_, row) in enumerate(label_df.iterrows()):
        dx, dy = offsets[i % len(offsets)]
        ax.annotate(
            _format_label(row["subject_name"]),
            (row["revenue_share_pct"], row["return_rate_pct"]),
            xytext=(dx, dy),
            textcoords="offset points",
            fontsize=8.5,
            color=COLOR_TEXT,
            fontweight="bold",
            bbox=dict(
                    boxstyle="round,pad=0.25",
                    fc=COLOR_SCATTER_LABEL_BG,
                    ec=COLOR_GRID,
                    alpha=0.96
                ),
            arrowprops=dict(arrowstyle="-", color=COLOR_GRID, lw=0.8, alpha=0.7),
            zorder=5,
        )

    ax.text(
        x_min + (x_mid - x_min) * 0.06,
        y_min + (y_mid - y_min) * 0.08,
        "Небольшая доля /\nнизкий риск",
        fontsize=8,
        color=COLOR_MUTED,
        ha="left",
        va="bottom",
    )
    ax.text(
        x_mid + (x_max - x_mid) * 0.06,
        y_min + (y_mid - y_min) * 0.08,
        "Ключевые категории /\nустойчивый профиль",
        fontsize=8,
        color=COLOR_MUTED,
        ha="left",
        va="bottom",
    )
    ax.text(
        x_min + (x_mid - x_min) * 0.06,
        y_mid + (y_max - y_mid) * 0.86,
        "Локальный риск",
        fontsize=8,
        color=COLOR_MUTED,
        ha="left",
        va="top",
    )
    ax.text(
        x_mid + (x_max - x_mid) * 0.06,
        y_mid + (y_max - y_mid) * 0.86,
        "Приоритетный контроль",
        fontsize=8,
        color=COLOR_BAD,
        ha="left",
        va="top",
        fontweight="bold",
    )

    ax.text(
        0.99,
        0.02,
        "Размер пузыря = чистая выручка категории",
        transform=ax.transAxes,
        fontsize=8,
        color=COLOR_MUTED,
        ha="right",
        va="bottom",
    )

    plt.tight_layout()

    buffer = BytesIO()
    fig.savefig(buffer, format="png", dpi=220, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)

    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode("utf-8")