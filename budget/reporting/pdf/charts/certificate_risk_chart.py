# budget/reporting/pdf/charts/certificate_risk_chart.py
# from __future__ import annotations

# import base64
# from io import BytesIO

# import matplotlib.pyplot as plt
# import pandas as pd


# def build_certificate_risk_chart_base64(rows: list[dict], limit: int = 10) -> str | None:
#     if not rows:
#         return None

#     df = pd.DataFrame(rows).copy()
#     if df.empty:
#         return None

#     df["sales_amount_90d"] = pd.to_numeric(df["sales_amount_90d"], errors="coerce").fillna(0)
#     df["sales_qty_90d"] = pd.to_numeric(df["sales_qty_90d"], errors="coerce").fillna(0)
#     df["risk_level"] = df["risk_level"].fillna("Не определено")
#     df["product_name"] = df["product_name"].fillna("—")

#     df = df.sort_values("sales_amount_90d", ascending=False).head(limit).copy()
#     if df.empty:
#         return None

#     def short_name(x: str, max_len: int = 34) -> str:
#         x = str(x)
#         return x if len(x) <= max_len else x[:max_len - 3] + "..."

#     df["product_short"] = df["product_name"].apply(short_name)

#     color_map = {
#         "Истек": "#9A4F4F",
#         "Критично": "#C96F2D",
#         "Высокий риск": "#C9A23D",
#         "Контроль": "#6F8F86",
#         "Не определено": "#999999",
#     }

#     colors = [color_map.get(x, "#999999") for x in df["risk_level"]]

#     fig, ax = plt.subplots(figsize=(11.8, 6.0))

#     y_pos = range(len(df))
#     ax.barh(y_pos, df["sales_amount_90d"], color=colors)

#     ax.set_yticks(list(y_pos))
#     ax.set_yticklabels(df["product_short"], fontsize=9)
#     ax.invert_yaxis()

#     ax.set_title("Приоритетные SKU по риску истечения сертификатов", fontsize=15, fontweight="bold", pad=14)
#     ax.set_xlabel("Продажи за 90 дней, руб.", fontsize=10)

#     ax.grid(axis="x", linestyle="--", alpha=0.3)
#     ax.spines["top"].set_visible(False)
#     ax.spines["right"].set_visible(False)

#     max_value = float(df["sales_amount_90d"].max()) if len(df) else 0
#     offset = max_value * 0.01 if max_value else 0

#     for i, (_, row) in enumerate(df.iterrows()):
#         value = float(row["sales_amount_90d"] or 0)
#         qty = int(row["sales_qty_90d"] or 0)
#         value_label = f"{value:,.0f}".replace(",", " ")
#         qty_label = f"{qty:,}".replace(",", " ")
#         label = f"{value_label} ₽ | {qty_label} шт."
#         ax.text(value + offset, i, label, va="center", fontsize=8.8)

#     legend_items = []
#     used_levels = list(dict.fromkeys(df["risk_level"].tolist()))
#     for level in used_levels:
#         legend_items.append(
#             plt.Line2D([0], [0], color=color_map.get(level, "#999999"), lw=8, label=level)
#         )

#     if legend_items:
#         ax.legend(handles=legend_items, loc="lower right", frameon=False, fontsize=9)

#     plt.tight_layout()

#     buffer = BytesIO()
#     fig.savefig(buffer, format="png", dpi=200, bbox_inches="tight")
#     plt.close(fig)

#     buffer.seek(0)
#     return base64.b64encode(buffer.read()).decode("utf-8")



# budget/reporting/pdf/charts/certificate_risk_chart.py
from __future__ import annotations

import base64
from io import BytesIO

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.ticker import FuncFormatter

from budget.reporting.pdf.charts.styles import (
    COLOR_BG,
    COLOR_BORDER,
    COLOR_GRID,
    COLOR_MUTED,
    COLOR_NEGATIVE,
    COLOR_PRIMARY,
    COLOR_SCATTER_EDGE,
    COLOR_SCATTER_LABEL_BG,
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


def _short_name(x: str, max_len: int = 38) -> str:
    x = str(x or "").strip()
    return x if len(x) <= max_len else x[: max_len - 3].rstrip() + "..."


def build_certificate_risk_chart_base64(rows: list[dict], limit: int = 10) -> str | None:
    if not rows:
        return None

    df = pd.DataFrame(rows).copy()
    if df.empty:
        return None

    df["sales_amount_90d"] = pd.to_numeric(df.get("sales_amount_90d"), errors="coerce").fillna(0)
    df["sales_qty_90d"] = pd.to_numeric(df.get("sales_qty_90d"), errors="coerce").fillna(0)
    df["risk_level"] = df.get("risk_level", pd.Series(dtype="object")).fillna("Не определено")
    df["product_name"] = df.get("product_name", pd.Series(dtype="object")).fillna("—")

    df = df[df["sales_amount_90d"] > 0].copy()
    if df.empty:
        return None

    df = df.sort_values("sales_amount_90d", ascending=False).head(limit).copy()
    if df.empty:
        return None

    df["product_short"] = df["product_name"].apply(_short_name)

    # Более спокойная и благородная палитра риска
    color_map = {
        "Истек": COLOR_NEGATIVE,   # #9A4F4F
        "Критично": "#B96A4A",
        "Высокий риск": "#A88A4B",
        "Контроль": COLOR_PRIMARY,  # #1F6F5F
        "Не определено": "#8C8C8C",
    }

    df["color"] = df["risk_level"].map(lambda x: color_map.get(x, "#8C8C8C"))

    # Разворачиваем, чтобы самый крупный был сверху
    df = df.iloc[::-1].copy()

    n = len(df)
    fig_height = max(5.4, 0.62 * n + 1.8)

    fig, ax = plt.subplots(figsize=(12.2, fig_height), dpi=180)
    fig.patch.set_facecolor(COLOR_BG)
    ax.set_facecolor(COLOR_BG)

    y_pos = list(range(len(df)))
    values = df["sales_amount_90d"].tolist()
    labels = df["product_short"].tolist()
    colors = df["color"].tolist()

    max_value = max(values) if values else 0
    x_pad = max_value * 0.19 if max_value > 0 else 1

    # Линии lollipop
    for y, value, color in zip(y_pos, values, colors):
        ax.hlines(
            y=y,
            xmin=0,
            xmax=value,
            color=color,
            linewidth=2.0,
            alpha=0.42,
            zorder=2,
        )

    # Точки
    ax.scatter(
        values,
        y_pos,
        s=170,
        c=colors,
        edgecolors=COLOR_SCATTER_EDGE,
        linewidths=1.4,
        zorder=4,
    )

    # Маленькая точка в начале — чтобы линия не выглядела оборванной
    ax.scatter(
        [0] * len(y_pos),
        y_pos,
        s=18,
        c=COLOR_BORDER,
        edgecolors="none",
        zorder=3,
        alpha=0.9,
    )

    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels, fontsize=9.3, color=COLOR_TEXT)

    ax.set_title(
        "Приоритетные SKU по риску истечения сертификатов",
        fontsize=15,
        fontweight="bold",
        color=COLOR_TEXT,
        pad=14,
    )

    ax.set_xlabel(
        "Продажи за 90 дней, ₽",
        fontsize=10,
        color=COLOR_TEXT,
        labelpad=10,
    )

    ax.xaxis.set_major_formatter(FuncFormatter(_format_money_tick))
    ax.set_xlim(0, max_value + x_pad)

    # Сетка и оси
    ax.grid(
        axis="x",
        linestyle="--",
        linewidth=0.8,
        color=COLOR_GRID,
        alpha=0.75,
        zorder=1,
    )
    ax.grid(axis="y", visible=False)

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(False)
    ax.spines["bottom"].set_color(COLOR_BORDER)
    ax.spines["bottom"].set_linewidth(0.8)

    ax.tick_params(axis="x", labelsize=9, colors=COLOR_MUTED)
    ax.tick_params(axis="y", length=0, pad=8)

    # Подписи справа от точек
    for y, (_, row) in enumerate(df.iterrows()):
        value = float(row["sales_amount_90d"] or 0)
        qty = int(row["sales_qty_90d"] or 0)

        value_label = _format_money(value)
        qty_label = f"{qty:,}".replace(",", " ")
        label = f"{value_label} ₽ | {qty_label} шт."

        ax.text(
            value + max_value * 0.014,
            y,
            label,
            va="center",
            ha="left",
            fontsize=8.7,
            color=COLOR_TEXT,
            zorder=5,
            bbox=dict(
                boxstyle="round,pad=0.18,rounding_size=0.10",
                facecolor=COLOR_SCATTER_LABEL_BG,
                edgecolor="none",
                alpha=0.96,
            ),
        )

    # Легкий вертикальный акцент слева
    ax.axvline(
        x=0,
        color=COLOR_PRIMARY,
        linewidth=1.8,
        alpha=0.95,
        zorder=2,
    )

    # Легенда
    used_levels = [x for x in ["Истек", "Критично", "Высокий риск", "Контроль", "Не определено"] if x in set(df["risk_level"])]
    legend_items = [
        Line2D(
            [0],
            [0],
            marker="o",
            color="none",
            markerfacecolor=color_map[level],
            markeredgecolor=COLOR_SCATTER_EDGE,
            markeredgewidth=1.0,
            markersize=8.5,
            label=level,
        )
        for level in used_levels
    ]

    if legend_items:
        ax.legend(
            handles=legend_items,
            loc="lower right",
            frameon=False,
            fontsize=9,
            ncol=min(3, len(legend_items)),
            handletextpad=0.6,
            columnspacing=1.2,
        )

    subtitle = (
        "График показывает SKU с наибольшим объемом продаж в зоне сертификационного риска "
        "за последние 90 дней. Цвет точки отражает уровень риска."
    )

    ax.text(
        0.0,
        -0.12,
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