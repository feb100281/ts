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


SEGMENT_COLORS = {
    "Low": COLOR_PRIMARY,
    "Medium": COLOR_LINE,
    "High": COLOR_NEGATIVE,
}


def _to_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").fillna(0)


def _format_money(v: float) -> str:
    return f"{v:,.0f} ₽".replace(",", " ")


def build_category_segment_structure_chart_base64(segment_rows: list[dict]) -> str | None:
    if not segment_rows:
        return None

    df = pd.DataFrame(segment_rows).copy()
    if df.empty:
        return None

    df["subject_name"] = df["subject_name"].fillna("Не указана").astype(str)
    df["price_segment"] = df["price_segment"].fillna("—").astype(str)
    df["category_sales_share_pct"] = _to_numeric(df["category_sales_share_pct"])
    df["sales_amount"] = _to_numeric(df["sales_amount"])
    df["segment_price_from"] = _to_numeric(df["segment_price_from"])
    df["segment_price_to"] = _to_numeric(df["segment_price_to"])

    pivot = (
        df.pivot_table(
            index="subject_name",
            columns="price_segment",
            values="category_sales_share_pct",
            aggfunc="sum",
            fill_value=0,
        )
        .reset_index()
    )

    sales_totals = (
        df.groupby("subject_name", as_index=False)["sales_amount"]
        .sum()
        .sort_values("sales_amount", ascending=False)
    )

    pivot = pivot.merge(sales_totals, on="subject_name", how="left")
    pivot = pivot.sort_values("sales_amount", ascending=True)

    for col in ["Low", "Medium", "High"]:
        if col not in pivot.columns:
            pivot[col] = 0.0

    dominant_meta = (
    df.sort_values(["subject_name", "category_sales_share_pct"], ascending=[True, False])
    .groupby("subject_name", as_index=False)
    .apply(lambda x: x.loc[x["category_sales_share_pct"].idxmax()])
)

    dominant_map = {}
    for _, row in dominant_meta.iterrows():
        dominant_map[row["subject_name"]] = {
            "segment": row["price_segment"],
            "from": row["segment_price_from"],
            "to": row["segment_price_to"],
            "share": row["category_sales_share_pct"],
        }

    fig_h = max(6.2, 0.52 * len(pivot) + 2.0)
    fig, ax = plt.subplots(figsize=(12.4, fig_h), dpi=180)
    fig.patch.set_facecolor(COLOR_BG)
    ax.set_facecolor(COLOR_BG)

    left = pd.Series([0.0] * len(pivot))
    for seg in ["Low", "Medium", "High"]:
        values = pivot[seg]
        ax.barh(
            pivot["subject_name"],
            values,
            left=left,
            color=SEGMENT_COLORS[seg],
            edgecolor="white",
            linewidth=0.8,
            label=seg,
            zorder=3,
        )
        left += values

    ax.set_title(
        "Какие ценовые слои формируют продажи внутри категорий",
        fontsize=14,
        fontweight="bold",
        color=COLOR_TEXT,
        pad=14,
    )
    ax.set_xlabel("Доля сегмента в продажах категории, %", fontsize=10, color=COLOR_TEXT)

    ax.grid(axis="x", linestyle="--", color=COLOR_GRID, alpha=0.45, zorder=1)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(COLOR_GRID)
    ax.spines["bottom"].set_color(COLOR_GRID)

    ax.tick_params(axis="x", labelsize=9, colors=COLOR_MUTED)
    ax.tick_params(axis="y", labelsize=9, colors=COLOR_TEXT)

    ax.legend(
        loc="lower right",
        frameon=False,
        fontsize=9,
        title="Сегмент",
        title_fontsize=9,
    )

    for _, row in pivot.iterrows():
        subject_name = row["subject_name"]
        meta = dominant_map.get(subject_name)

        if not meta:
            continue

        seg = meta["segment"]
        seg_share = float(meta["share"] or 0)
        seg_from = _format_money(float(meta["from"] or 0))
        seg_to = _format_money(float(meta["to"] or 0))

        ax.text(
            101.2,
            subject_name,
            f"{seg}: {seg_share:.1f}% | {seg_from} – {seg_to}",
            va="center",
            ha="left",
            fontsize=8.2,
            color=COLOR_TEXT,
        )

    ax.set_xlim(0, 128)

    ax.text(
        0.01,
        0.02,
        "Подпись справа показывает доминирующий ценовой слой и его фактический ценовой коридор внутри категории.",
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