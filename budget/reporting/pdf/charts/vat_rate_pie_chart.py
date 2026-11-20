from io import BytesIO
import base64

import matplotlib.pyplot as plt
import pandas as pd

from budget.reporting.pdf.charts.styles import (
    COLOR_TEXT,
    COLOR_MUTED,
    COLOR_BG,
    COLOR_BORDER,
    COLOR_PRIMARY,
    COLOR_SEGMENT_LOW,
    COLOR_SEGMENT_MEDIUM,
)


def _format_money(value: float) -> str:
    return f"{value:,.0f}".replace(",", " ") + " ₽"


def build_vat_rate_pie_chart_base64(
    rate_breakdown: list[dict],
    title: str = "Структура НДС по ставкам"
) -> str | None:
    """
    Строит компактную donut-диаграмму структуры НДС по ставкам.
    Возвращает PNG в base64.
    """
    if not rate_breakdown:
        return None

    # Оставляем только положительные значения НДС
    data = [row for row in rate_breakdown if float(row.get("net_vat", 0) or 0) > 0]
    if not data:
        return None

    df = pd.DataFrame(data)
    total_sum = float(df["net_vat"].sum())
    if total_sum <= 0:
        return None

    labels = []
    sizes = []
    other_sum = 0.0

    # Сортируем по убыванию
    df_sorted = df.sort_values("net_vat", ascending=False)

    for _, row in df_sorted.iterrows():
        vat = float(row["net_vat"])
        label = str(row["vat_rate_label"])

        # Мелкие сегменты объединяем в "Остальное",
        # кроме основной ставки
        if total_sum > 0 and vat / total_sum < 0.05 and "Основная" not in label:
            other_sum += vat
        else:
            if label == "Основная ставка 22%":
                label = "Основная (22%)"
            elif label == "Льготная ставка 10%":
                label = "Льготная (10%)"

            labels.append(label)
            sizes.append(vat)

    if other_sum > 0:
        labels.append("Остальное")
        sizes.append(other_sum)

    # Если сегментов больше, чем цветов, просто повторяем палитру
    base_colors = [
        COLOR_PRIMARY,
        COLOR_SEGMENT_LOW,
        COLOR_SEGMENT_MEDIUM,
        COLOR_MUTED,
    ]
    colors = [base_colors[i % len(base_colors)] for i in range(len(labels))]

    plt.close("all")

    # УМЕНЬШЕННЫЙ размер фигуры
    fig, ax = plt.subplots(figsize=(3.0, 2.35), dpi=300)
    fig.patch.set_facecolor(COLOR_BG)
    ax.set_facecolor(COLOR_BG)

    def autopct_func(pct: float) -> str:
        return f"{pct:.0f}%" if pct >= 6 else ""

    wedges, texts, autotexts = ax.pie(
        sizes,
        labels=None,  # подписи только в легенде
        autopct=autopct_func,
        colors=colors,
        startangle=90,
        explode=[0.01] * len(labels),
        pctdistance=0.80,
        textprops={
            "fontsize": 6,
            "color": COLOR_BG,
            "fontweight": "bold",
        },
        wedgeprops={
            "edgecolor": COLOR_BG,
            "linewidth": 1.0,
            "width": 0.48,  # donut
        },
    )

    # Проценты внутри сегментов
    for autotext in autotexts:
        autotext.set_fontsize(6)
        autotext.set_fontweight("bold")
        autotext.set_color(COLOR_BG)

    # Центральный текст
    total_vat = sum(sizes)
    center_text = f"{_format_money(total_vat)}\nвсего НДС"
    ax.text(
        0,
        0,
        center_text,
        ha="center",
        va="center",
        fontsize=5.8,
        color=COLOR_TEXT,
        fontweight="bold",
        linespacing=1.15,
        bbox=dict(
            boxstyle="round,pad=0.20",
            facecolor=COLOR_BG,
            edgecolor=COLOR_BORDER,
            linewidth=0.6,
        ),
    )

    # Легенда ближе к графику, чтобы не раздувать ширину
    legend_elements = [
        plt.Rectangle(
            (0, 0), 1, 1,
            facecolor=color,
            edgecolor=COLOR_BORDER,
            linewidth=0.5
        )
        for color in colors
    ]

    ax.legend(
        legend_elements,
        labels,
        loc="center left",
        bbox_to_anchor=(0.86, 0.5),
        fontsize=6,
        frameon=True,
        fancybox=False,
        edgecolor=COLOR_BORDER,
        facecolor=COLOR_BG,
        handlelength=1.0,
        handleheight=0.8,
        labelspacing=0.45,
        borderpad=0.35,
    )

    ax.set_title(
        title,
        loc="left",
        fontsize=8,
        fontweight="bold",
        color=COLOR_TEXT,
        pad=4,
    )

    ax.axis("equal")
    plt.tight_layout(pad=0.35)

    buffer = BytesIO()
    fig.savefig(
        buffer,
        format="png",
        facecolor=fig.get_facecolor(),
        transparent=False,
        dpi=300,
    )
    buffer.seek(0)

    image_base64 = base64.b64encode(buffer.read()).decode("utf-8")
    buffer.close()
    plt.close(fig)

    return image_base64