# budget/reporting/pdf/charts/weekly_avg_price_chart.py

from io import BytesIO
import base64

import matplotlib.pyplot as plt
import pandas as pd

from budget.reporting.pdf.charts.styles import (
    COLOR_TREND,
    COLOR_GRID,
    COLOR_TEXT,
    COLOR_MUTED,
    COLOR_BG,
    COLOR_BORDER,
    COLOR_PRIMARY,
)


def _fmt_price(x: float) -> str:
    return f"{x:,.0f}".replace(",", " ") + " ₽"


def build_weekly_avg_price_chart_base64(weekly_trends: list) -> str | None:
    """
    График недельной динамики средней цены продажи за единицу.
    """
    if not weekly_trends:
        return None

    df = pd.DataFrame(weekly_trends).copy()
    if df.empty or "avg_price" not in df.columns:
        return None

    df = df.tail(12).copy()

    if "week_start" in df.columns:
        df["week_start"] = pd.to_datetime(df["week_start"])
        x_labels = df["week_start"].dt.strftime("%d.%m").tolist()
    else:
        x_labels = [str(i + 1) for i in range(len(df))]

    y = df["avg_price"].fillna(0).astype(float).tolist()
    if not y:
        return None

    avg_value = sum(y) / len(y)

    plt.close("all")
    fig, ax = plt.subplots(figsize=(10.5, 3.5), dpi=180)
    fig.patch.set_facecolor(COLOR_BG)
    ax.set_facecolor(COLOR_BG)

    x = list(range(len(y)))

    ax.plot(
        x,
        y,
        color=COLOR_TREND,
        linewidth=2.2,
        marker="o",
        markersize=4.2,
        markerfacecolor=COLOR_TREND,
        markeredgecolor=COLOR_BG,
        markeredgewidth=0.9,
        zorder=3,
    )

    ax.fill_between(
        x,
        y,
        [0] * len(y),
        color=COLOR_TREND,
        alpha=0.08,
        zorder=1,
    )

    ax.axhline(
        avg_value,
        color=COLOR_PRIMARY,
        linewidth=1.2,
        linestyle="--",
        zorder=2,
    )

    ax.scatter(
        [x[-1]],
        [y[-1]],
        s=52,
        color=COLOR_PRIMARY,
        edgecolors=COLOR_BG,
        linewidths=1.0,
        zorder=4,
    )

    ax.text(
        x[-1] - 0.1,
        avg_value,
        f" Среднее: {_fmt_price(avg_value)}",
        color=COLOR_MUTED,
        fontsize=8,
        va="bottom",
        ha="left",
    )

    ax.annotate(
        _fmt_price(y[-1]),
        xy=(x[-1], y[-1]),
        xytext=(-10, 14),
        textcoords="offset points",
        ha="right",
        va="bottom",
        fontsize=8.5,
        color=COLOR_TEXT,
        bbox=dict(
            boxstyle="round,pad=0.25",
            facecolor=COLOR_BG,
            edgecolor=COLOR_BORDER,
            linewidth=0.8,
        ),
        zorder=5,
    )

    ax.set_xticks(x)
    ax.set_xticklabels(x_labels, fontsize=8, color=COLOR_MUTED)

    y_max = max(y + [avg_value]) * 1.12 if max(y + [avg_value]) > 0 else 1
    ax.set_ylim(0, y_max)

    ticks = ax.get_yticks()
    ax.set_yticks(ticks)
    ax.set_yticklabels(
        [_fmt_price(t) if t >= 0 else "" for t in ticks],
        fontsize=8,
        color=COLOR_MUTED,
    )

    ax.grid(axis="y", color=COLOR_GRID, linewidth=0.8, alpha=0.8)
    ax.grid(axis="x", visible=False)

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(COLOR_BORDER)
    ax.spines["bottom"].set_color(COLOR_BORDER)

    ax.tick_params(axis="x", length=0)
    ax.tick_params(axis="y", length=0)

    ax.set_title(
        "Недельная динамика средней цены продажи",
        loc="left",
        fontsize=12,
        fontweight="bold",
        color=COLOR_TEXT,
        pad=12,
    )

    plt.tight_layout()

    buffer = BytesIO()
    fig.savefig(
        buffer,
        format="png",
        bbox_inches="tight",
        facecolor=fig.get_facecolor(),
    )
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.read()).decode("utf-8")
    buffer.close()
    plt.close(fig)

    return image_base64