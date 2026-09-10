# budget/reporting/pdf/charts/category_sales_chart.py
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
)


# ----------------------------
# Настройки цветов
# ----------------------------
COLOR_GOOD = "#6FAE95"      # низкие возвраты
COLOR_MID = "#D7B56D"       # средние возвраты
COLOR_BAD = "#C97B7B"       # высокие возвраты
COLOR_EDGE = "#6F8D86"


def _to_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").fillna(0)


def _money_tick(value: float) -> str:
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f} млн"
    return f"{value:,.0f}".replace(",", " ")


def _format_label(text: str, width: int = 18) -> str:
    text = str(text or "").strip()
    if not text:
        return "—"
    return shorten(text, width=width, placeholder="…")


def _risk_color(return_rate: float) -> str:
    if return_rate <= 10:
        return COLOR_GOOD
    if return_rate <= 15:
        return COLOR_MID
    return COLOR_BAD


def _bubble_size_scale(net_amount: pd.Series) -> pd.Series:
    """
    Масштаб пузырей:
    минимум не слишком маленький, максимум не слишком огромный.
    """
    s = _to_numeric(net_amount)
    if s.empty:
        return s

    min_v = float(s.min())
    max_v = float(s.max())

    if max_v <= 0:
        return pd.Series([700] * len(s), index=s.index)

    if max_v == min_v:
        return pd.Series([1400] * len(s), index=s.index)

    norm = (s - min_v) / (max_v - min_v)
    return 500 + norm * 2500


def _prepare_dataframe(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows).copy()
    if df.empty:
        return df

    required_cols = ["subject_name", "avg_sku_price", "return_rate_pct", "net_amount"]
    for col in required_cols:
        if col not in df.columns:
            df[col] = 0

    df["subject_name"] = df["subject_name"].fillna("Не указана").astype(str)
    df["avg_sku_price"] = _to_numeric(df["avg_sku_price"])
    df["return_rate_pct"] = _to_numeric(df["return_rate_pct"])
    df["net_amount"] = _to_numeric(df["net_amount"])
    df["sales_amount"] = _to_numeric(df["sales_amount"]) if "sales_amount" in df.columns else 0
    df["revenue_share_pct"] = _to_numeric(df["revenue_share_pct"]) if "revenue_share_pct" in df.columns else 0

    df = df[df["avg_sku_price"] > 0].copy()
    if df.empty:
        return df

    df["bubble_size"] = _bubble_size_scale(df["net_amount"])
    df["color"] = df["return_rate_pct"].apply(_risk_color)

    return df


def _select_labels(df: pd.DataFrame) -> pd.DataFrame:
    """
    Подписываем только важное:
    - топ-6 по net-выручке
    - категории с высоким возвратом
    - очень дорогие категории
    """
    if df.empty:
        return df

    top_net = df.sort_values("net_amount", ascending=False).head(6)
    high_return = df[df["return_rate_pct"] >= max(15, df["return_rate_pct"].quantile(0.75))]
    high_price = df[df["avg_sku_price"] >= df["avg_sku_price"].quantile(0.85)]

    label_df = pd.concat([top_net, high_return, high_price], axis=0)
    label_df = label_df.drop_duplicates(subset=["subject_name"]).copy()

    # чтобы подписи не разъезжались из-за слишком большого количества
    label_df = label_df.sort_values("net_amount", ascending=False).head(10)
    return label_df


def _add_quadrant_background(ax, x_mid: float, y_mid: float, x_min: float, x_max: float, y_min: float, y_max: float):
    """
    Слегка тонируем квадранты, чтобы собственнику было проще читать график.
    """
    # нижний левый — mass core
    ax.axvspan(x_min, x_mid, ymin=0, ymax=(y_mid - y_min) / (y_max - y_min), color="#EEF6F2", alpha=0.55, zorder=0)
    # нижний правый — premium core
    ax.axvspan(x_mid, x_max, ymin=0, ymax=(y_mid - y_min) / (y_max - y_min), color="#F2F7FB", alpha=0.45, zorder=0)
    # верхний левый — pressure zone
    ax.axvspan(x_min, x_mid, ymin=(y_mid - y_min) / (y_max - y_min), ymax=1, color="#FBF6EE", alpha=0.45, zorder=0)
    # верхний правый — risk zone
    ax.axvspan(x_mid, x_max, ymin=(y_mid - y_min) / (y_max - y_min), ymax=1, color="#FBEEEE", alpha=0.40, zorder=0)


def build_category_sales_chart_base64(rows: list[dict]) -> str | None:
    """
    Bubble chart:
    X = средняя цена SKU внутри категории
    Y = возвратность, %
    Размер пузыря = чистая выручка категории

    Логика:
    - подписи не у всех, а только у важных категорий;
    - цвет показывает риск возвратов;
    - медианные линии делят поле на 4 управленческие зоны.
    """
    if not rows:
        return None

    df = _prepare_dataframe(rows)
    if df.empty:
        return None

    label_df = _select_labels(df)

    x = df["avg_sku_price"]
    y = df["return_rate_pct"]
    s = df["bubble_size"]

    x_mid = float(x.median())
    y_mid = float(y.median())

    x_min = max(0, float(x.min()) * 0.75)
    x_max = float(x.max()) * 1.10
    y_min = max(0, float(y.min()) * 0.85)
    y_max = float(y.max()) * 1.12

    fig, ax = plt.subplots(figsize=(11.2, 6.8), dpi=180)
    fig.patch.set_facecolor(COLOR_BG)
    ax.set_facecolor(COLOR_BG)

    _add_quadrant_background(ax, x_mid, y_mid, x_min, x_max, y_min, y_max)

    # Пузырьки
    ax.scatter(
        x,
        y,
        s=s,
        c=df["color"],
        alpha=0.62,
        edgecolors=COLOR_EDGE,
        linewidths=1.1,
        zorder=3,
    )

    # Линии медиан
    ax.axvline(x=x_mid, linestyle="--", linewidth=1.1, color=COLOR_GRID, alpha=0.95, zorder=2)
    ax.axhline(y=y_mid, linestyle="--", linewidth=1.1, color=COLOR_GRID, alpha=0.95, zorder=2)

    # Заголовок и подписи
    ax.set_title(
        "Позиционирование категорий: цена / возврат / чистая выручка",
        fontsize=14,
        fontweight="bold",
        color=COLOR_TEXT,
        pad=14,
    )
    ax.set_xlabel("Средняя цена SKU внутри категории, руб.", fontsize=10, color=COLOR_TEXT)
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

    # Форматируем X
    xticks = ax.get_xticks()
    ax.set_xticklabels([_money_tick(v) for v in xticks])

    # Подписи зон
    ax.text(
        x_min + (x_mid - x_min) * 0.05,
        y_min + (y_max - y_min) * 0.95,
        "Массовый сегмент\nс повышенным риском",
        fontsize=8,
        color=COLOR_MUTED,
        ha="left",
        va="top",
        zorder=4,
    )
    ax.text(
        x_mid + (x_max - x_mid) * 0.05,
        y_min + (y_max - y_min) * 0.95,
        "Премиум-сегмент\nс повышенным риском",
        fontsize=8,
        color=COLOR_MUTED,
        ha="left",
        va="top",
        zorder=4,
    )
    ax.text(
        x_min + (x_mid - x_min) * 0.05,
        y_min + (y_mid - y_min) * 0.08,
        "Массовое ядро\nнизкий возврат",
        fontsize=8,
        color=COLOR_MUTED,
        ha="left",
        va="bottom",
        zorder=4,
    )
    ax.text(
        x_mid + (x_max - x_mid) * 0.05,
        y_min + (y_mid - y_min) * 0.08,
        "Премиальное ядро\nнизкий возврат",
        fontsize=8,
        color=COLOR_MUTED,
        ha="left",
        va="bottom",
        zorder=4,
    )

    # Подписи пузырей
    # Чтобы было читаемо, используем заранее заданные смещения
    offsets = [
        (8, 8),
        (10, -12),
        (-14, 10),
        (12, 12),
        (-18, -10),
        (8, -16),
        (14, 6),
        (-20, 12),
        (10, 14),
        (-16, 8),
    ]

    for i, (_, row) in enumerate(label_df.iterrows()):
        dx, dy = offsets[i % len(offsets)]

        ax.annotate(
            _format_label(row["subject_name"], width=18),
            (row["avg_sku_price"], row["return_rate_pct"]),
            xytext=(dx, dy),
            textcoords="offset points",
            fontsize=8.5,
            color=COLOR_TEXT,
            fontweight="bold",
            bbox=dict(
                boxstyle="round,pad=0.25",
                fc="white",
                ec=COLOR_GRID,
                alpha=0.92,
            ),
            arrowprops=dict(
                arrowstyle="-",
                color=COLOR_GRID,
                lw=0.8,
                alpha=0.7,
                shrinkA=2,
                shrinkB=4,
            ),
            zorder=5,
        )

    # Легенда по риску возвратов
    legend_x = 0.015
    legend_y = 0.02
    ax.text(
        legend_x,
        legend_y + 0.10,
        "Цвет пузыря:",
        transform=ax.transAxes,
        fontsize=8,
        color=COLOR_TEXT,
        ha="left",
        va="bottom",
    )
    ax.text(
        legend_x,
        legend_y + 0.065,
        "● низкий возврат (≤10%)",
        transform=ax.transAxes,
        fontsize=8,
        color=COLOR_GOOD,
        ha="left",
        va="bottom",
    )
    ax.text(
        legend_x,
        legend_y + 0.035,
        "● средний возврат (10–15%)",
        transform=ax.transAxes,
        fontsize=8,
        color=COLOR_MID,
        ha="left",
        va="bottom",
    )
    ax.text(
        legend_x,
        legend_y + 0.005,
        "● высокий возврат (>15%)",
        transform=ax.transAxes,
        fontsize=8,
        color=COLOR_BAD,
        ha="left",
        va="bottom",
    )

    # Легенда по размеру
    ax.text(
        0.985,
        0.02,
        "Размер пузыря = чистая выручка",
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