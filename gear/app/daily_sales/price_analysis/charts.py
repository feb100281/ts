# gear/app/daily_sales/price_analysis/charts.py
from __future__ import annotations

from io import BytesIO

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

import numpy as np
from plotly.subplots import make_subplots

from .config import CV_RANK_ORDER


PLOTLY_CONFIG = {
    "displaylogo": False,
    "responsive": True,
    "locale": "ru",
}


def _to_html(fig, title: str) -> bytes:
    html = fig.to_html(
        full_html=True,
        include_plotlyjs=True,
        config=PLOTLY_CONFIG,
    )
    return html.encode("utf-8")


def make_cv_distribution_html(df: pd.DataFrame) -> bytes:
    rows = []

    cost_types = [
        ("Бухгалтерская", "Ранг CV, бух"),
        ("Управленческая", "Ранг CV, упр"),
    ]

    for kind, col in cost_types:
        if col not in df.columns:
            continue

        counts = (
            df[col]
            .fillna("Нет данных")
            .astype(str)
            .value_counts()
            .reindex(CV_RANK_ORDER, fill_value=0)
        )

        total = int(counts.sum())

        for rank, value in counts.items():
            value = int(value)

            rows.append(
                {
                    "Тип себестоимости": kind,
                    "Ранг": rank,
                    "Количество товаров": value,
                    "Доля": value / total * 100 if total else 0,
                }
            )

    chart_df = pd.DataFrame(rows)

    if chart_df.empty:
        fig = go.Figure()

        fig.add_annotation(
            text="Нет данных для построения графика",
            x=0.5,
            y=0.5,
            xref="paper",
            yref="paper",
            showarrow=False,
            font=dict(
                family="Arial",
                size=16,
                color="#6B7280",
            ),
        )

        fig.update_layout(
            template="plotly_white",
            height=500,
            margin=dict(l=50, r=30, t=70, b=70),
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            paper_bgcolor="#FFFFFF",
            plot_bgcolor="#FFFFFF",
        )

        return _to_html(fig, "Распределение CV")

    colors = {
        "Бухгалтерская": "rgba(59, 130, 246, 0.62)",
        "Управленческая": "rgba(16, 185, 129, 0.62)",
    }

    line_colors = {
        "Бухгалтерская": "rgba(37, 99, 235, 0.95)",
        "Управленческая": "rgba(5, 150, 105, 0.95)",
    }

    fig = go.Figure()

    for kind, _ in cost_types:
        kind_df = chart_df[
            chart_df["Тип себестоимости"] == kind
        ].copy()

        if kind_df.empty:
            continue

        fig.add_trace(
            go.Bar(
                name=kind,
                x=kind_df["Ранг"],
                y=kind_df["Количество товаров"],
                customdata=kind_df[["Доля"]].to_numpy(),
                marker=dict(
                    color=colors[kind],
                    line=dict(
                        color=line_colors[kind],
                        width=1.2,
                    ),
                ),
                text=kind_df["Количество товаров"],
                texttemplate="%{text:,.0f}",
                textposition="outside",
                textfont=dict(
                    family="Arial",
                    size=11,
                    color="#374151",
                ),
                cliponaxis=False,
                hovertemplate=(
                    "<b>%{x}</b>"
                    "<br>"
                    + kind
                    + "<br>"
                    "Товаров: <b>%{y:,.0f}</b>"
                    "<br>"
                    "Доля: <b>%{customdata[0]:.1f}%</b>"
                    "<extra></extra>"
                ),
            )
        )

    fig.update_layout(
        template="plotly_white",
        height=650,
        title=dict(
            text=(
                "<b>Распределение товаров по коэффициенту вариации</b>"
                "<br>"
                "<span style='font-size:13px;color:#6B7280'>"
                "Чем выше ранг, тем сильнее менялась себестоимость товара"
                "</span>"
            ),
            x=0.01,
            xanchor="left",
            y=0.97,
            yanchor="top",
            font=dict(
                family="Arial",
                size=20,
                color="#111827",
            ),
        ),
        margin=dict(
            l=70,
            r=35,
            t=110,
            b=125,
        ),
        barmode="group",
        bargap=0.22,
        bargroupgap=0.08,
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        font=dict(
            family="Arial",
            size=12,
            color="#374151",
        ),
        legend=dict(
            title=None,
            orientation="h",
            x=0,
            xanchor="left",
            y=1.03,
            yanchor="bottom",
            font=dict(
                family="Arial",
                size=12,
                color="#374151",
            ),
            bgcolor="rgba(255,255,255,0)",
            borderwidth=0,
            itemclick="toggle",
            itemdoubleclick="toggleothers",
        ),
        hoverlabel=dict(
            bgcolor="#FFFFFF",
            bordercolor="#D1D5DB",
            font=dict(
                family="Arial",
                size=12,
                color="#111827",
            ),
            namelength=-1,
        ),
        uniformtext=dict(
            minsize=9,
            mode="hide",
        ),
    )

    fig.update_xaxes(
        title=None,
        categoryorder="array",
        categoryarray=CV_RANK_ORDER,
        tickangle=-25,
        tickfont=dict(
            family="Arial",
            size=11,
            color="#4B5563",
        ),
        showgrid=False,
        showline=True,
        linewidth=1,
        linecolor="#D1D5DB",
        ticks="outside",
        ticklen=5,
        tickcolor="#D1D5DB",
        fixedrange=True,
    )

    fig.update_yaxes(
        title=dict(
            text="Количество товаров",
            font=dict(
                family="Arial",
                size=12,
                color="#4B5563",
            ),
            standoff=12,
        ),
        tickformat=",",
        separatethousands=True,
        rangemode="tozero",
        showgrid=True,
        gridcolor="rgba(209, 213, 219, 0.55)",
        griddash="dot",
        zeroline=False,
        showline=False,
        ticks="",
        tickfont=dict(
            family="Arial",
            size=11,
            color="#6B7280",
        ),
        fixedrange=True,
    )

    return _to_html(fig, "Распределение CV")





def make_top_cv_products_html(
    df: pd.DataFrame,
    top_n: int = 30,
) -> bytes:
    work = df.copy()

    # ------------------------------------------------------------------
    # Вспомогательные функции
    # ------------------------------------------------------------------

    def safe_numeric(column: str) -> pd.Series:
        """
        Безопасно преобразует колонку в число.
        Если колонки нет, возвращает пустую числовую серию.
        """
        if column not in work.columns:
            return pd.Series(
                np.nan,
                index=work.index,
                dtype="float64",
            )

        return pd.to_numeric(
            work[column],
            errors="coerce",
        )

    def format_number(value, decimals: int = 2) -> str:
        if pd.isna(value):
            return "—"

        return f"{value:,.{decimals}f}".replace(",", " ")

    def format_integer(value) -> str:
        if pd.isna(value):
            return "—"

        return f"{int(value):,}".replace(",", " ")

    def shorten_text(value, max_length: int = 52) -> str:
        if pd.isna(value):
            return "Без наименования"

        text = str(value).strip()

        if not text:
            return "Без наименования"

        if len(text) <= max_length:
            return text

        return text[: max_length - 1].rstrip() + "…"

    def make_product_label(row: pd.Series) -> str:
        name = shorten_text(
            row.get("Наименование"),
            max_length=48,
        )

        nm_id = row.get("nm_id")

        if pd.isna(nm_id):
            return name

        try:
            nm_id_text = str(int(float(nm_id)))
        except (TypeError, ValueError):
            nm_id_text = str(nm_id)

        return f"{name}<br><span style='font-size:10px;color:#9CA3AF'>NM {nm_id_text}</span>"

    # ------------------------------------------------------------------
    # Подготовка данных
    # ------------------------------------------------------------------

    work["CV бух"] = safe_numeric(
        "Коэффициент вариации, %, бух"
    )

    work["CV упр"] = safe_numeric(
        "Коэффициент вариации, %, упр"
    )

    # Цены для бухгалтерской себестоимости
    work["Медиана бух"] = safe_numeric(
        "Медиана цены, бух"
    )
    work["Средняя бух"] = safe_numeric(
        "Средняя цена, бух"
    )
    work["Мин бух"] = safe_numeric(
        "Минимальная цена, бух"
    )
    work["Макс бух"] = safe_numeric(
        "Максимальная цена, бух"
    )

    # На случай, если колонки названы короче
    if work["Мин бух"].isna().all():
        work["Мин бух"] = safe_numeric("Мин. цена, бух")

    if work["Макс бух"].isna().all():
        work["Макс бух"] = safe_numeric("Макс. цена, бух")

    # Цены для управленческой себестоимости
    work["Медиана упр"] = safe_numeric(
        "Медиана цены, упр"
    )
    work["Средняя упр"] = safe_numeric(
        "Средняя цена, упр"
    )
    work["Мин упр"] = safe_numeric(
        "Минимальная цена, упр"
    )
    work["Макс упр"] = safe_numeric(
        "Максимальная цена, упр"
    )

    if work["Мин упр"].isna().all():
        work["Мин упр"] = safe_numeric("Мин. цена, упр")

    if work["Макс упр"].isna().all():
        work["Макс упр"] = safe_numeric("Макс. цена, упр")

    work["Кол-во УПД numeric"] = safe_numeric(
        "Кол-во УПД"
    )

    # Исключаем строки, где CV отсутствует.
    # nlargest автоматически вернёт меньше top_n,
    # если подходящих товаров меньше.
    top_buh = (
        work.loc[work["CV бух"].notna()]
        .nlargest(top_n, "CV бух")
        .copy()
    )

    top_upr = (
        work.loc[work["CV упр"].notna()]
        .nlargest(top_n, "CV упр")
        .copy()
    )

    top_buh["Тип"] = "Бухгалтерская"
    top_buh["CV"] = top_buh["CV бух"]
    top_buh["Медиана"] = top_buh["Медиана бух"]
    top_buh["Средняя"] = top_buh["Средняя бух"]
    top_buh["Минимум"] = top_buh["Мин бух"]
    top_buh["Максимум"] = top_buh["Макс бух"]

    top_upr["Тип"] = "Управленческая"
    top_upr["CV"] = top_upr["CV упр"]
    top_upr["Медиана"] = top_upr["Медиана упр"]
    top_upr["Средняя"] = top_upr["Средняя упр"]
    top_upr["Минимум"] = top_upr["Мин упр"]
    top_upr["Максимум"] = top_upr["Макс упр"]

    # Для горизонтального графика сортируем по возрастанию,
    # чтобы максимальное значение оказалось сверху.
    top_buh = top_buh.sort_values(
        "CV",
        ascending=True,
    )

    top_upr = top_upr.sort_values(
        "CV",
        ascending=True,
    )

    for frame in [top_buh, top_upr]:
        if not frame.empty:
            frame["Товар"] = frame.apply(
                make_product_label,
                axis=1,
            )

            frame["Диапазон цены"] = (
                frame["Минимум"]
                .apply(lambda value: format_number(value))
                + "–"
                + frame["Максимум"]
                .apply(lambda value: format_number(value))
                + " ₽"
            )

            frame["Подпись"] = frame.apply(
                lambda row: (
                    f"<b>{format_number(row['CV'], 1)}%</b>"
                    + (
                        f"<br><span style='font-size:10px'>"
                        f"медиана {format_number(row['Медиана'])} ₽"
                        f"</span>"
                        if pd.notna(row["Медиана"])
                        else ""
                    )
                ),
                axis=1,
            )

            frame["Бренд hover"] = frame.get(
                "Бренд",
                pd.Series("—", index=frame.index),
            ).fillna("—").astype(str)

            frame["Категория hover"] = frame.get(
                "Категория",
                pd.Series("—", index=frame.index),
            ).fillna("—").astype(str)

            frame["УПД hover"] = frame[
                "Кол-во УПД numeric"
            ].apply(format_integer)

            frame["Медиана hover"] = frame[
                "Медиана"
            ].apply(format_number)

            frame["Средняя hover"] = frame[
                "Средняя"
            ].apply(format_number)

            frame["Минимум hover"] = frame[
                "Минимум"
            ].apply(format_number)

            frame["Максимум hover"] = frame[
                "Максимум"
            ].apply(format_number)

    # ------------------------------------------------------------------
    # Обработка полностью пустых данных
    # ------------------------------------------------------------------

    if top_buh.empty and top_upr.empty:
        fig = go.Figure()

        fig.add_annotation(
            text=(
                "<b>Нет данных для построения графика</b>"
                "<br>"
                "<span style='font-size:13px;color:#6B7280'>"
                "Для товаров не рассчитан коэффициент вариации"
                "</span>"
            ),
            x=0.5,
            y=0.5,
            xref="paper",
            yref="paper",
            showarrow=False,
            align="center",
            font=dict(
                family="Arial",
                size=17,
                color="#374151",
            ),
        )

        fig.update_layout(
            template="plotly_white",
            height=460,
            margin=dict(
                l=40,
                r=40,
                t=80,
                b=40,
            ),
            paper_bgcolor="#FFFFFF",
            plot_bgcolor="#FFFFFF",
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
        )

        return _to_html(fig, "Топ CV")

    # ------------------------------------------------------------------
    # Динамическая компоновка
    # ------------------------------------------------------------------

    buh_count = len(top_buh)
    upr_count = len(top_upr)

    # Пустой блок вообще не создаём.
    active_blocks = []

    if buh_count:
        active_blocks.append(
            (
                "Бухгалтерская себестоимость",
                top_buh,
                "rgba(59, 130, 246, 0.68)",
                "rgba(37, 99, 235, 0.95)",
            )
        )

    if upr_count:
        active_blocks.append(
            (
                "Управленческая себестоимость",
                top_upr,
                "rgba(16, 185, 129, 0.68)",
                "rgba(5, 150, 105, 0.95)",
            )
        )

    row_heights = [
        max(len(frame), 3)
        for _, frame, _, _ in active_blocks
    ]

    total_rows = sum(row_heights)

    normalized_row_heights = [
        value / total_rows
        for value in row_heights
    ]

    subplot_titles = [
        (
            f"<b>{title}</b>"
            f"<span style='font-size:11px;color:#6B7280'>"
            f" · показано {len(frame)} из {top_n}"
            f"</span>"
        )
        for title, frame, _, _ in active_blocks
    ]

    fig = make_subplots(
        rows=len(active_blocks),
        cols=1,
        shared_xaxes=False,
        vertical_spacing=(
            0.11
            if len(active_blocks) > 1
            else 0.04
        ),
        row_heights=normalized_row_heights,
        subplot_titles=subplot_titles,
    )

    # ------------------------------------------------------------------
    # Добавление столбцов
    # ------------------------------------------------------------------

    for row_number, (
        title,
        frame,
        fill_color,
        line_color,
    ) in enumerate(active_blocks, start=1):

        customdata = np.column_stack(
            [
                frame["Бренд hover"],
                frame["Категория hover"],
                frame["УПД hover"],
                frame["Медиана hover"],
                frame["Средняя hover"],
                frame["Минимум hover"],
                frame["Максимум hover"],
            ]
        )

        fig.add_trace(
            go.Bar(
                x=frame["CV"],
                y=frame["Товар"],
                orientation="h",
                marker=dict(
                    color=fill_color,
                    line=dict(
                        color=line_color,
                        width=1,
                    ),
                ),
                customdata=customdata,
                text=frame["Подпись"],
                texttemplate="%{text}",
                textposition="inside",
                insidetextanchor="end",
                textfont=dict(
                    family="Arial",
                    size=11,
                    color="#FFFFFF",
                ),
                constraintext="none",
                cliponaxis=False,
                hovertemplate=(
                    "<b>%{y}</b>"
                    "<br><br>"
                    "Коэффициент вариации: "
                    "<b>%{x:.2f}%</b>"
                    "<br>"
                    "Бренд: %{customdata[0]}"
                    "<br>"
                    "Категория: %{customdata[1]}"
                    "<br>"
                    "Количество УПД: %{customdata[2]}"
                    "<br><br>"
                    "Медианная цена: "
                    "<b>%{customdata[3]} ₽</b>"
                    "<br>"
                    "Средняя цена: %{customdata[4]} ₽"
                    "<br>"
                    "Минимальная цена: %{customdata[5]} ₽"
                    "<br>"
                    "Максимальная цена: %{customdata[6]} ₽"
                    "<extra></extra>"
                ),
                showlegend=False,
                name=title,
            ),
            row=row_number,
            col=1,
        )

        fig.update_xaxes(
            title=dict(
                text="Коэффициент вариации, %",
                font=dict(
                    family="Arial",
                    size=11,
                    color="#6B7280",
                ),
                standoff=10,
            ),
            rangemode="tozero",
            showgrid=True,
            gridcolor="rgba(209, 213, 219, 0.55)",
            griddash="dot",
            zeroline=False,
            showline=True,
            linecolor="#D1D5DB",
            linewidth=1,
            ticks="outside",
            tickcolor="#D1D5DB",
            tickfont=dict(
                family="Arial",
                size=10,
                color="#6B7280",
            ),
            tickformat=".0f",
            ticksuffix="%",
            fixedrange=True,
            row=row_number,
            col=1,
        )

        fig.update_yaxes(
            title="",
            showgrid=False,
            showline=False,
            ticks="",
            automargin=True,
            tickfont=dict(
                family="Arial",
                size=11,
                color="#374151",
            ),
            fixedrange=True,
            row=row_number,
            col=1,
        )

    # ------------------------------------------------------------------
    # Динамическая высота без пустоты
    # ------------------------------------------------------------------

    max_rows_in_block = max(
        len(frame)
        for _, frame, _, _ in active_blocks
    )

    total_product_rows = sum(
        len(frame)
        for _, frame, _, _ in active_blocks
    )

    chart_height = (
        210
        + total_product_rows * 34
        + len(active_blocks) * 75
    )

    chart_height = max(
        520,
        min(chart_height, 2450),
    )

    actual_top = max(buh_count, upr_count)

    fig.update_layout(
        template="plotly_white",
        height=chart_height,
        title=dict(
            text=(
                "<b>Товары с максимальной вариативностью себестоимости</b>"
                "<br>"
                "<span style='font-size:13px;color:#6B7280'>"
                "Высокий CV означает значительное изменение цены "
                "между поступлениями"
                "</span>"
            ),
            x=0.01,
            xanchor="left",
            y=0.99,
            yanchor="top",
            font=dict(
                family="Arial",
                size=20,
                color="#111827",
            ),
        ),
        margin=dict(
            l=330,
            r=70,
            t=125,
            b=55,
        ),
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        font=dict(
            family="Arial",
            size=12,
            color="#374151",
        ),
        bargap=0.24,
        showlegend=False,
        hoverlabel=dict(
            bgcolor="#FFFFFF",
            bordercolor="#D1D5DB",
            font=dict(
                family="Arial",
                size=12,
                color="#111827",
            ),
            align="left",
            namelength=-1,
        ),
        uniformtext=dict(
            minsize=8,
            mode="hide",
        ),
    )

    # Оформление заголовков отдельных блоков
    for annotation in fig.layout.annotations:
        annotation.update(
            x=0,
            xanchor="left",
            font=dict(
                family="Arial",
                size=14,
                color="#1F2937",
            ),
        )

    return _to_html(fig, "Топ CV")





# def make_price_history_html(
#     history_df: pd.DataFrame,
#     analysis_df: pd.DataFrame,
#     max_products: int = 50,
# ) -> bytes:
#     if history_df.empty or analysis_df.empty:
#         fig = go.Figure()
#         fig.add_annotation(
#             text="Нет данных для построения истории цен",
#             showarrow=False,
#         )
#         return _to_html(fig, "История цен")

#     ranked = analysis_df.copy()
#     ranked["_sort_cv"] = pd.to_numeric(
#         ranked["Коэффициент вариации, %, бух"],
#         errors="coerce",
#     ).fillna(-1)

#     product_ids = (
#         ranked.sort_values("_sort_cv", ascending=False)["nm_id"]
#         .astype(str)
#         .drop_duplicates()
#         .head(max_products)
#         .tolist()
#     )

#     history = history_df[
#         history_df["nm_id"].astype(str).isin(product_ids)
#     ].copy()

#     history["Дата УПД"] = pd.to_datetime(history["Дата УПД"], errors="coerce")

#     fig = go.Figure()

#     buttons = []
#     traces_per_product = 4

#     for product_index, nm_id in enumerate(product_ids):
#         product_history = history[
#             history["nm_id"].astype(str) == str(nm_id)
#         ].sort_values("Дата УПД")

#         if product_history.empty:
#             continue

#         title = product_history["Наименование"].iloc[0] or ""
#         visible = product_index == 0

#         median_buh = pd.to_numeric(
#             product_history["Цена, бух"],
#             errors="coerce",
#         ).median()

#         median_upr = pd.to_numeric(
#             product_history["Цена, упр"],
#             errors="coerce",
#         ).median()

#         fig.add_trace(
#             go.Scatter(
#                 x=product_history["Дата УПД"],
#                 y=product_history["Цена, бух"],
#                 mode="lines+markers",
#                 name="Цена, бух",
#                 visible=visible,
#                 customdata=product_history[["ID УПД", "Количество, шт"]],
#                 hovertemplate=(
#                     "Дата: %{x|%d.%m.%Y}<br>"
#                     "Цена, бух: %{y:,.2f} ₽<br>"
#                     "ID УПД: %{customdata[0]}<br>"
#                     "Количество: %{customdata[1]:,.0f} шт"
#                     "<extra></extra>"
#                 ),
#             )
#         )

#         fig.add_trace(
#             go.Scatter(
#                 x=product_history["Дата УПД"],
#                 y=product_history["Цена, упр"],
#                 mode="lines+markers",
#                 name="Цена, упр",
#                 visible=visible,
#                 customdata=product_history[["ID УПД", "Количество, шт"]],
#                 hovertemplate=(
#                     "Дата: %{x|%d.%m.%Y}<br>"
#                     "Цена, упр: %{y:,.2f} ₽<br>"
#                     "ID УПД: %{customdata[0]}<br>"
#                     "Количество: %{customdata[1]:,.0f} шт"
#                     "<extra></extra>"
#                 ),
#             )
#         )

#         fig.add_trace(
#             go.Scatter(
#                 x=product_history["Дата УПД"],
#                 y=[median_buh] * len(product_history),
#                 mode="lines",
#                 name="Медиана, бух",
#                 line=dict(dash="dot", width=1),
#                 visible=visible,
#                 hovertemplate="Медиана, бух: %{y:,.2f} ₽<extra></extra>",
#             )
#         )

#         fig.add_trace(
#             go.Scatter(
#                 x=product_history["Дата УПД"],
#                 y=[median_upr] * len(product_history),
#                 mode="lines",
#                 name="Медиана, упр",
#                 line=dict(dash="dot", width=1),
#                 visible=visible,
#                 hovertemplate="Медиана, упр: %{y:,.2f} ₽<extra></extra>",
#             )
#         )

#         visibility = [False] * (len(product_ids) * traces_per_product)
#         start = product_index * traces_per_product

#         for trace_index in range(start, start + traces_per_product):
#             if trace_index < len(visibility):
#                 visibility[trace_index] = True

#         buttons.append(
#             {
#                 "label": f"{title[:45]} · {nm_id}",
#                 "method": "update",
#                 "args": [
#                     {"visible": visibility},
#                     {
#                         "title": (
#                             "История себестоимости — "
#                             f"{title} · NM {nm_id}"
#                         )
#                     },
#                 ],
#             }
#         )

#     fig.update_layout(
#         template="plotly_white",
#         height=720,
#         margin=dict(l=70, r=40, t=150, b=70),
#         title=(
#             "История себестоимости — "
#             + (buttons[0]["label"] if buttons else "")
#         ),
#         xaxis_title="Дата УПД",
#         yaxis_title="Себестоимость, ₽",
#         hovermode="x unified",
#         font=dict(family="Arial", size=12),
#         updatemenus=[
#             {
#                 "buttons": buttons,
#                 "direction": "down",
#                 "showactive": True,
#                 "x": 0,
#                 "xanchor": "left",
#                 "y": 1.16,
#                 "yanchor": "top",
#             }
#         ],
#     )

#     return _to_html(fig, "История себестоимости")


