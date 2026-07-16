# gear/app/costs_control/charts.py
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from .calculations import get_cost_columns
from .config import COLORS, CV_RANK_ORDER


def empty_figure(
    message: str = "Нет данных для построения графика",
    height: int = 400,
) -> go.Figure:
    fig = go.Figure()

    fig.add_annotation(
        text=message,
        x=0.5,
        y=0.5,
        xref="paper",
        yref="paper",
        showarrow=False,
        font={
            "family": "Arial",
            "size": 14,
            "color": COLORS["muted"],
        },
    )

    fig.update_layout(
        height=height,
        paper_bgcolor=COLORS["white"],
        plot_bgcolor=COLORS["white"],
        margin={
            "l": 20,
            "r": 20,
            "t": 20,
            "b": 20,
        },
        xaxis={"visible": False},
        yaxis={"visible": False},
    )

    return fig


def base_layout(
    *,
    height: int = 420,
    margin: dict | None = None,
) -> dict:
    return {
        "template": "plotly_white",
        "height": height,
        "paper_bgcolor": COLORS["white"],
        "plot_bgcolor": COLORS["white"],
        "font": {
            "family": "Arial",
            "size": 12,
            "color": COLORS["text"],
        },
        "margin": margin
        or {
            "l": 55,
            "r": 25,
            "t": 25,
            "b": 55,
        },
        "hoverlabel": {
            "bgcolor": COLORS["white"],
            "bordercolor": COLORS["border"],
            "font": {
                "family": "Arial",
                "size": 12,
                "color": COLORS["text"],
            },
        },
    }


def build_cv_distribution_chart(
    df: pd.DataFrame,
    cost_type: str,
) -> go.Figure:
    """
    Строит распределение товаров по диапазонам
    коэффициента вариации.
    """

    if df.empty:
        return empty_figure()

    columns = get_cost_columns(
        cost_type
    )

    rank_column = columns["rank"]

    if rank_column not in df.columns:
        return empty_figure()

    counts = (
        df[rank_column]
        .fillna("Нет данных")
        .value_counts()
        .reindex(
            CV_RANK_ORDER,
            fill_value=0,
        )
    )

    total = int(
        counts.sum()
    )

    if total > 0:
        shares = (
            counts
            / total
            * 100
        )
    else:
        shares = counts.astype(float)

    colors = [
        "#CBD5E1",  # Одна цена
        "#8FC3B2",  # До 25%
        "#7CA8C8",  # 25–50%
        "#DDB96B",  # 50–75%
        "#D78484",  # 75%+
    ]

    # Основная подпись:
    # количество товаров + доля от общей выборки.
    text_labels = [
        (
            f"<b>{count:,.0f}</b>"
            f"<br><span style='font-size:11px'>"
            f"{share:.1f}%</span>"
        ).replace(",", " ")
        for count, share in zip(
            counts.values,
            shares.values,
        )
    ]

    customdata = np.column_stack(
        [
            shares.values,
            np.repeat(
                total,
                len(counts),
            ),
        ]
    )

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=counts.index,
            y=counts.values,
            marker={
                "color": colors,
                "line": {
                    "color": "#FFFFFF",
                    "width": 1.5,
                },
            },
            width=0.68,
            text=text_labels,
            textposition="outside",
            textfont={
                "family": (
                    "Inter, Arial, sans-serif"
                ),
                "size": 15,
                "color": COLORS["text"],
            },
            cliponaxis=False,
            customdata=customdata,
            hovertemplate=(
                "<b>%{x}</b>"
                "<br><br>"
                "Товаров: "
                "<b>%{y:,.0f}</b>"
                "<br>"
                "Доля выборки: "
                "<b>%{customdata[0]:.1f}%</b>"
                "<br>"
                "Всего товаров: "
                "%{customdata[1]:,.0f}"
                "<extra></extra>"
            ),
        )
    )

    max_value = (
        float(counts.max())
        if not counts.empty
        else 0
    )

    # Запас сверху нужен для двухстрочных подписей.
    y_max = (
        max_value * 1.22
        if max_value > 0
        else 1
    )

    fig.update_layout(
        **base_layout(
            height=420,
            margin={
                "l": 58,
                "r": 24,
                "t": 48,
                "b": 72,
            },
        ),
        showlegend=False,
        bargap=0.18,
        hovermode="closest",
        uniformtext={
            "minsize": 11,
            "mode": "show",
        },
    )

    fig.update_xaxes(
        title=None,
        categoryorder="array",
        categoryarray=CV_RANK_ORDER,
        tickangle=0,
        tickfont={
            "family": (
                "Inter, Arial, sans-serif"
            ),
            "size": 11,
            "color": COLORS["text"],
        },
        showgrid=False,
        showline=True,
        linewidth=1,
        linecolor=COLORS["border"],
        ticks="",
        automargin=True,
    )

    fig.update_yaxes(
        title={
            "text": "Количество товаров",
            "font": {
                "family": (
                    "Inter, Arial, sans-serif"
                ),
                "size": 12,
                "color": COLORS["muted"],
            },
            "standoff": 10,
        },
        range=[
            0,
            y_max,
        ],
        rangemode="tozero",
        tickformat=",.0f",
        separatethousands=True,
        tickfont={
            "family": (
                "Inter, Arial, sans-serif"
            ),
            "size": 11,
            "color": COLORS["muted"],
        },
        showgrid=True,
        gridcolor="#E8ECEF",
        griddash="dot",
        gridwidth=1,
        zeroline=False,
        showline=False,
    )

    return fig

def build_top_cv_chart(
    df: pd.DataFrame,
    cost_type: str,
    top_n: int = 20,
) -> go.Figure:
    """
    Товары с максимальным коэффициентом вариации.

    На оси Y отображаются:
    - наименование товара;
    - NM ID с явной подписью.

    Высота фиксирована, чтобы график не накладывался
    на следующий блок в layout.
    """

    chart_height = 720

    if df.empty:
        return empty_figure(
            "Нет данных для построения графика",
            height=chart_height,
        )

    columns = get_cost_columns(
        cost_type
    )

    required_columns = [
        "nm_id",
        "Наименование",
        "Бренд",
        "Категория",
        columns["cv"],
        columns["median"],
        columns["minimum"],
        columns["maximum"],
    ]

    if any(
        column not in df.columns
        for column in required_columns
    ):
        return empty_figure(
            "Недостаточно данных для построения графика",
            height=chart_height,
        )

    work = df.copy()

    work["cv_numeric"] = pd.to_numeric(
        work[columns["cv"]],
        errors="coerce",
    )

    work["median_numeric"] = pd.to_numeric(
        work[columns["median"]],
        errors="coerce",
    )

    work["minimum_numeric"] = pd.to_numeric(
        work[columns["minimum"]],
        errors="coerce",
    )

    work["maximum_numeric"] = pd.to_numeric(
        work[columns["maximum"]],
        errors="coerce",
    )

    work["nm_id_text"] = (
        work["nm_id"]
        .fillna("")
        .astype(str)
        .str.replace(
            r"\.0$",
            "",
            regex=True,
        )
    )

    work["Наименование"] = (
        work["Наименование"]
        .fillna("Без наименования")
        .astype(str)
        .str.strip()
    )

    work["Бренд"] = (
        work["Бренд"]
        .fillna("Бренд не указан")
        .astype(str)
    )

    work["Категория"] = (
        work["Категория"]
        .fillna("Категория не указана")
        .astype(str)
    )

    work = (
        work.loc[
            work["cv_numeric"].notna()
        ]
        .nlargest(
            top_n,
            "cv_numeric",
        )
        .sort_values(
            "cv_numeric",
            ascending=True,
        )
        .reset_index(drop=True)
    )

    if work.empty:
        return empty_figure(
            "Нет данных для построения графика",
            height=chart_height,
        )

    # Сокращённое название выводим на оси,
    # полное остаётся в hover.
    work["name_label"] = (
        work["Наименование"]
        .apply(
            lambda value: (
                value
                if len(value) <= 47
                else value[:45] + "…"
            )
        )
    )

    work["axis_label"] = (
        work["name_label"]
        + "<br>"
        + "<span style='font-size:10px;color:#6B7280'>"
        + "NM ID: "
        + work["nm_id_text"]
        + "</span>"
    )

    customdata = np.column_stack(
        [
            work["Наименование"],
            work["nm_id_text"],
            work["Бренд"],
            work["Категория"],
            work["median_numeric"],
            work["minimum_numeric"],
            work["maximum_numeric"],
        ]
    )

    max_cv = float(
        work["cv_numeric"].max()
    )

    x_max = (
        max_cv * 1.08
        if max_cv > 0
        else 1
    )

    fig = go.Figure(
        go.Bar(
            x=work["cv_numeric"],
            y=work["axis_label"],
            orientation="h",
            width=0.72,

            marker={
                "color": "rgba(76, 125, 111, 0.76)",
                "line": {
                    "color": "#2F6656",
                    "width": 1,
                },
            },

            text=work["cv_numeric"].map(
                lambda value: (
                    f"{value:.1f}%"
                )
            ),

            textposition="inside",
            insidetextanchor="end",

            textfont={
                "family": (
                    "Inter, Arial, sans-serif"
                ),
                "size": 12,
                "color": "#FFFFFF",
            },

            cliponaxis=False,
            customdata=customdata,

            hovertemplate=(
                "<b>%{customdata[0]}</b>"
                "<br>"
                "NM ID: "
                "<b>%{customdata[1]}</b>"
                "<br><br>"
                "CV: "
                "<b>%{x:.2f}%</b>"
                "<br>"
                "Бренд: "
                "%{customdata[2]}"
                "<br>"
                "Категория: "
                "%{customdata[3]}"
                "<br>"
                "Медиана: "
                "%{customdata[4]:,.2f} ₽"
                "<br>"
                "Минимум: "
                "%{customdata[5]:,.2f} ₽"
                "<br>"
                "Максимум: "
                "%{customdata[6]:,.2f} ₽"
                "<extra></extra>"
            ),
        )
    )

    fig.update_layout(
        **base_layout(
            height=chart_height,
            margin={
                "l": 365,
                "r": 45,
                "t": 25,
                "b": 65,
            },
        ),

        showlegend=False,
        bargap=0.18,
        hovermode="closest",

        uniformtext={
            "minsize": 10,
            "mode": "show",
        },
    )

    fig.update_xaxes(
        title={
            "text": "Коэффициент вариации, %",
            "font": {
                "family": (
                    "Inter, Arial, sans-serif"
                ),
                "size": 12,
                "color": COLORS["muted"],
            },
            "standoff": 12,
        },

        range=[
            0,
            x_max,
        ],

        ticksuffix="%",
        tickformat=",.0f",

        tickfont={
            "family": (
                "Inter, Arial, sans-serif"
            ),
            "size": 11,
            "color": COLORS["muted"],
        },

        showgrid=True,
        gridcolor="#E5EAED",
        griddash="dot",
        gridwidth=1,

        zeroline=False,
        showline=True,
        linecolor=COLORS["border"],
    )

    fig.update_yaxes(
        title=None,
        showgrid=False,
        automargin=True,

        tickfont={
            "family": (
                "Inter, Arial, sans-serif"
            ),
            "size": 11,
            "color": COLORS["text"],
        },
    )

    return fig

def build_median_deviation_chart(
    df: pd.DataFrame,
    cost_type: str,
    top_n: int = 20,
) -> go.Figure:
    """
    Показывает максимальное и минимальное отклонение
    цены от медианы.

    Положительные отклонения направлены вправо,
    отрицательные — влево.

    Значения около нуля не подписываются, чтобы
    возле центральной оси не появлялись +0.0% и -0.0%.
    """

    chart_height = 720

    if df.empty:
        return empty_figure(
            "Нет данных для построения графика",
            height=chart_height,
        )

    columns = get_cost_columns(
        cost_type
    )

    required_columns = [
        "nm_id",
        "Наименование",
        "Бренд",
        "Категория",
        columns["max_deviation"],
        columns["min_deviation"],
        columns["median"],
        columns["minimum"],
        columns["maximum"],
    ]

    if any(
        column not in df.columns
        for column in required_columns
    ):
        return empty_figure(
            "Недостаточно данных для построения графика",
            height=chart_height,
        )

    work = df.copy()

    work["max_dev"] = pd.to_numeric(
        work[columns["max_deviation"]],
        errors="coerce",
    )

    work["min_dev"] = pd.to_numeric(
        work[columns["min_deviation"]],
        errors="coerce",
    )

    work["median_numeric"] = pd.to_numeric(
        work[columns["median"]],
        errors="coerce",
    )

    work["minimum_numeric"] = pd.to_numeric(
        work[columns["minimum"]],
        errors="coerce",
    )

    work["maximum_numeric"] = pd.to_numeric(
        work[columns["maximum"]],
        errors="coerce",
    )

    work["nm_id_text"] = (
        work["nm_id"]
        .fillna("")
        .astype(str)
        .str.replace(
            r"\.0$",
            "",
            regex=True,
        )
    )

    work["Наименование"] = (
        work["Наименование"]
        .fillna("Без наименования")
        .astype(str)
        .str.strip()
    )

    work["Бренд"] = (
        work["Бренд"]
        .fillna("Бренд не указан")
        .astype(str)
    )

    work["Категория"] = (
        work["Категория"]
        .fillna("Категория не указана")
        .astype(str)
    )

    work["absolute_dev"] = pd.concat(
        [
            work["max_dev"].abs(),
            work["min_dev"].abs(),
        ],
        axis=1,
    ).max(axis=1)

    work = (
        work.loc[
            work["absolute_dev"].notna()
        ]
        .nlargest(
            top_n,
            "absolute_dev",
        )
        .sort_values(
            "absolute_dev",
            ascending=True,
        )
        .reset_index(drop=True)
    )

    if work.empty:
        return empty_figure(
            "Нет данных для построения графика",
            height=chart_height,
        )

    work["name_label"] = (
        work["Наименование"]
        .apply(
            lambda value: (
                value
                if len(value) <= 47
                else value[:45] + "…"
            )
        )
    )

    work["axis_label"] = (
        work["name_label"]
        + "<br>"
        + "<span style='font-size:10px;color:#6B7280'>"
        + "NM ID: "
        + work["nm_id_text"]
        + "</span>"
    )

    # Убираем некрасивые подписи +0.0% и -0.0%.
    max_text = work["max_dev"].apply(
        lambda value: (
            f"{value:+.1f}%"
            if pd.notna(value)
            and abs(value) >= 0.05
            else ""
        )
    )

    min_text = work["min_dev"].apply(
        lambda value: (
            f"{value:+.1f}%"
            if pd.notna(value)
            and abs(value) >= 0.05
            else ""
        )
    )

    customdata = np.column_stack(
        [
            work["Наименование"],
            work["nm_id_text"],
            work["Бренд"],
            work["Категория"],
            work["median_numeric"],
            work["minimum_numeric"],
            work["maximum_numeric"],
        ]
    )

    fig = go.Figure()

    # -------------------------------------------------------------
    # Максимальная цена — положительное отклонение
    # -------------------------------------------------------------

    fig.add_trace(
        go.Bar(
            name="Максимальная цена",
            x=work["max_dev"],
            y=work["axis_label"],
            orientation="h",
            width=0.70,

            marker={
                "color": "rgba(185, 93, 93, 0.78)",
                "line": {
                    "color": "#A33A3A",
                    "width": 0.8,
                },
            },

            text=max_text,
            textposition="outside",

            textfont={
                "family": (
                    "Inter, Arial, sans-serif"
                ),
                "size": 11,
                "color": "#7F1D1D",
            },

            cliponaxis=False,
            customdata=customdata,

            hovertemplate=(
                "<b>%{customdata[0]}</b>"
                "<br>"
                "NM ID: "
                "<b>%{customdata[1]}</b>"
                "<br><br>"
                "Отклонение максимальной цены: "
                "<b>%{x:+.2f}%</b>"
                "<br>"
                "Бренд: "
                "%{customdata[2]}"
                "<br>"
                "Категория: "
                "%{customdata[3]}"
                "<br>"
                "Медиана: "
                "%{customdata[4]:,.2f} ₽"
                "<br>"
                "Минимум: "
                "%{customdata[5]:,.2f} ₽"
                "<br>"
                "Максимум: "
                "%{customdata[6]:,.2f} ₽"
                "<extra></extra>"
            ),
        )
    )

    # -------------------------------------------------------------
    # Минимальная цена — отрицательное отклонение
    # -------------------------------------------------------------

    fig.add_trace(
        go.Bar(
            name="Минимальная цена",
            x=work["min_dev"],
            y=work["axis_label"],
            orientation="h",
            width=0.70,

            marker={
                "color": "rgba(91, 137, 168, 0.78)",
                "line": {
                    "color": "#3B6B8F",
                    "width": 0.8,
                },
            },

            text=min_text,
            textposition="outside",

            textfont={
                "family": (
                    "Inter, Arial, sans-serif"
                ),
                "size": 11,
                "color": "#244A66",
            },

            cliponaxis=False,
            customdata=customdata,

            hovertemplate=(
                "<b>%{customdata[0]}</b>"
                "<br>"
                "NM ID: "
                "<b>%{customdata[1]}</b>"
                "<br><br>"
                "Отклонение минимальной цены: "
                "<b>%{x:+.2f}%</b>"
                "<br>"
                "Бренд: "
                "%{customdata[2]}"
                "<br>"
                "Категория: "
                "%{customdata[3]}"
                "<br>"
                "Медиана: "
                "%{customdata[4]:,.2f} ₽"
                "<br>"
                "Минимум: "
                "%{customdata[5]:,.2f} ₽"
                "<br>"
                "Максимум: "
                "%{customdata[6]:,.2f} ₽"
                "<extra></extra>"
            ),
        )
    )

    min_value = float(
        min(
            work["min_dev"].min(),
            0,
        )
    )

    max_value = float(
        max(
            work["max_dev"].max(),
            0,
        )
    )

    left_padding = max(
        abs(min_value) * 0.15,
        max_value * 0.03,
        5,
    )

    right_padding = max(
        max_value * 0.10,
        abs(min_value) * 0.03,
        5,
    )

    fig.update_layout(
        **base_layout(
            height=chart_height,
            margin={
                "l": 365,
                "r": 90,
                "t": 62,
                "b": 65,
            },
        ),

        # Не overlay: бары направлены от нуля
        # в противоположные стороны.
        barmode="relative",

        bargap=0.20,
        hovermode="closest",

        legend={
            "orientation": "h",
            "x": 0,
            "xanchor": "left",
            "y": 1.07,
            "yanchor": "bottom",
            "font": {
                "family": (
                    "Inter, Arial, sans-serif"
                ),
                "size": 11,
                "color": COLORS["text"],
            },
        },
    )

    fig.add_vline(
        x=0,
        line_width=1.2,
        line_color="#9CA3AF",
    )

    fig.update_xaxes(
        title={
            "text": "Отклонение от медианной цены, %",
            "font": {
                "family": (
                    "Inter, Arial, sans-serif"
                ),
                "size": 12,
                "color": COLORS["muted"],
            },
            "standoff": 12,
        },

        range=[
            min_value - left_padding,
            max_value + right_padding,
        ],

        ticksuffix="%",
        tickformat=",.0f",

        tickfont={
            "family": (
                "Inter, Arial, sans-serif"
            ),
            "size": 11,
            "color": COLORS["muted"],
        },

        showgrid=True,
        gridcolor="#E5EAED",
        griddash="dot",
        gridwidth=1,

        zeroline=False,
        showline=False,
    )

    fig.update_yaxes(
        title=None,
        showgrid=False,
        automargin=True,

        tickfont={
            "family": (
                "Inter, Arial, sans-serif"
            ),
            "size": 11,
            "color": COLORS["text"],
        },
    )

    return fig

def build_brand_summary_chart(
    df: pd.DataFrame,
    cost_type: str,
    top_n: int = 10,
) -> go.Figure:
    """
    Строит анализ брендов по коэффициенту вариации.

    Для каждого бренда показываются:
    - средний CV;
    - количество товаров;
    - количество критических товаров;
    - доля критических товаров в hover.
    """

    if df.empty:
        return empty_figure(
            "Нет данных по брендам",
            height=430,
        )

    columns = get_cost_columns(
        cost_type
    )

    cv_column = columns["cv"]

    if (
        "Бренд" not in df.columns
        or "nm_id" not in df.columns
        or cv_column not in df.columns
    ):
        return empty_figure(
            "Нет данных по брендам",
            height=430,
        )

    work = df.copy()

    # -------------------------------------------------------------
    # Подготовка данных
    # -------------------------------------------------------------

    work["cv_numeric"] = pd.to_numeric(
        work[cv_column],
        errors="coerce",
    )

    work["Бренд"] = (
        work["Бренд"]
        .fillna("Бренд не указан")
        .astype(str)
        .str.strip()
        .replace(
            "",
            "Бренд не указан",
        )
    )

    summary = (
        work.groupby(
            "Бренд",
            dropna=False,
        )
        .agg(
            products=(
                "nm_id",
                "nunique",
            ),
            average_cv=(
                "cv_numeric",
                "mean",
            ),
            median_cv=(
                "cv_numeric",
                "median",
            ),
            critical=(
                "cv_numeric",
                lambda values: (
                    pd.to_numeric(
                        values,
                        errors="coerce",
                    )
                    .ge(75)
                    .sum()
                ),
            ),
        )
        .reset_index()
    )

    summary = (
        summary.loc[
            summary["average_cv"].notna()
        ]
        .copy()
    )

    if summary.empty:
        return empty_figure(
            "Нет данных по брендам",
            height=430,
        )

    summary["critical_share"] = np.where(
        summary["products"] > 0,
        (
            summary["critical"]
            / summary["products"]
            * 100
        ),
        0,
    )

    # Показываем бренды с максимальным средним CV.
    summary = (
        summary
        .nlargest(
            top_n,
            "average_cv",
        )
        .sort_values(
            "average_cv",
            ascending=True,
        )
        .reset_index(drop=True)
    )

    # -------------------------------------------------------------
    # Подписи брендов
    # -------------------------------------------------------------

    summary["brand_label"] = (
        summary["Бренд"]
        .astype(str)
        .apply(
            lambda value: (
                value
                if len(value) <= 24
                else value[:22] + "…"
            )
        )
    )

    max_cv = float(
        summary["average_cv"].max()
    )

    # Короткие столбики не вместят две строки текста.
    # Для них выводим подпись снаружи.
    inside_limit = max_cv * 0.18

    summary["label_position"] = np.where(
        summary["average_cv"] >= inside_limit,
        "inside",
        "outside",
    )

    # -------------------------------------------------------------
    # Текст на столбиках
    # -------------------------------------------------------------

    text_labels = []

    for row in summary.itertuples(
        index=False
    ):
        products_text = (
            f"{int(row.products):,}"
            .replace(",", " ")
        )

        critical_text = (
            f"{int(row.critical):,}"
            .replace(",", " ")
        )

        # На коротком столбике показываем только CV,
        # чтобы подпись не накладывалась на соседние элементы.
        if row.average_cv < inside_limit:
            label = (
                f"<b>{row.average_cv:.1f}%</b>"
            )
        else:
            label = (
                f"<b>{row.average_cv:.1f}%</b>"
                f"<br>"
                f"<span style='font-size:10px'>"
                f"{products_text} тов. · "
                f"{critical_text} крит."
                f"</span>"
            )

        text_labels.append(
            label
        )

    # -------------------------------------------------------------
    # Данные для hover
    # -------------------------------------------------------------

    customdata = np.column_stack(
        [
            summary["Бренд"].astype(str),
            summary["products"],
            summary["critical"],
            summary["critical_share"],
            summary["median_cv"],
        ]
    )

    # -------------------------------------------------------------
    # Цветовая шкала
    # -------------------------------------------------------------

    color_max = max(
        100.0,
        max_cv,
    )

    fig = go.Figure(
        go.Bar(
            x=summary["average_cv"],
            y=summary["brand_label"],
            orientation="h",
            width=0.68,

            marker={
                "color": summary["average_cv"],
                "colorscale": [
                    [0.00, "#8FC3B2"],
                    [0.45, "#A9C5A0"],
                    [0.70, "#D6B76F"],
                    [1.00, "#CF7B7B"],
                ],
                "cmin": 0,
                "cmax": color_max,
                "showscale": False,
                "line": {
                    "color": "rgba(47, 102, 86, 0.26)",
                    "width": 1,
                },
            },

            text=text_labels,
            textposition=summary[
                "label_position"
            ].tolist(),

            # Тёмный текст хорошо читается
            # на светлой спокойной палитре.
            textfont={
                "family": (
                    "Inter, Arial, sans-serif"
                ),
                "size": 12,
                "color": "#172033",
            },

            insidetextanchor="end",
            cliponaxis=False,

            customdata=customdata,

            hovertemplate=(
                "<b>%{customdata[0]}</b>"
                "<br><br>"
                "Средний CV: "
                "<b>%{x:.2f}%</b>"
                "<br>"
                "Медианный CV: "
                "%{customdata[4]:.2f}%"
                "<br>"
                "Товаров: "
                "%{customdata[1]:,.0f}"
                "<br>"
                "Критических: "
                "%{customdata[2]:,.0f}"
                "<br>"
                "Доля критических: "
                "%{customdata[3]:.1f}%"
                "<extra></extra>"
            ),
        )
    )

    # Дополнительное пространство справа нужно
    # для наружных подписей коротких столбиков.
    x_max = (
        max_cv * 1.12
        if max_cv > 0
        else 1
    )

    fig.update_layout(
        **base_layout(
            height=430,
            margin={
                "l": 155,
                "r": 38,
                "t": 25,
                "b": 55,
            },
        ),
        showlegend=False,
        bargap=0.25,
        hovermode="closest",
        uniformtext={
            "minsize": 9,
            "mode": "show",
        },
    )

    fig.update_xaxes(
        title={
            "text": (
                "Средний коэффициент вариации, %"
            ),
            "font": {
                "family": (
                    "Inter, Arial, sans-serif"
                ),
                "size": 11,
                "color": COLORS["muted"],
            },
            "standoff": 12,
        },
        range=[
            0,
            x_max,
        ],
        ticksuffix="%",
        tickfont={
            "family": (
                "Inter, Arial, sans-serif"
            ),
            "size": 10,
            "color": COLORS["muted"],
        },
        showgrid=True,
        gridcolor="#E5EAED",
        griddash="dot",
        gridwidth=1,
        zeroline=False,
        showline=False,
        fixedrange=False,
    )

    fig.update_yaxes(
        title=None,
        showgrid=False,
        automargin=True,
        tickfont={
            "family": (
                "Inter, Arial, sans-serif"
            ),
            "size": 11,
            "color": COLORS["text"],
        },
        fixedrange=False,
    )

    return fig


def build_price_history_chart(
    history_df: pd.DataFrame,
    nm_id: str | None,
) -> go.Figure:
    if history_df.empty or not nm_id:
        return empty_figure(
            "Выберите товар в таблице, чтобы увидеть историю цен",
            height=430,
        )

    work = history_df[
        history_df["nm_id"].astype(str)
        == str(nm_id)
    ].copy()

    if work.empty:
        return empty_figure(
            "Для выбранного товара история цен не найдена",
            height=430,
        )

    work["Дата УПД"] = pd.to_datetime(
        work["Дата УПД"],
        errors="coerce",
    )

    work = work.sort_values(
        [
            "Дата УПД",
            "ID УПД",
        ]
    )

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=work["Дата УПД"],
            y=work["Цена, бух"],
            name="Бухгалтерская",
            mode="lines+markers",
            line={
                "color": COLORS["blue"],
                "width": 2,
            },
            marker={
                "size": 7,
            },
            customdata=np.column_stack(
                [
                    work["Номер УПД"].astype(str),
                    work["Поставщик"].astype(str),
                    work["Количество, шт"],
                ]
            ),
            hovertemplate=(
                "<b>%{x|%d.%m.%Y}</b>"
                "<br>Цена, бух: %{y:,.2f} ₽"
                "<br>УПД: %{customdata[0]}"
                "<br>Поставщик: %{customdata[1]}"
                "<br>Количество: %{customdata[2]:,.0f}"
                "<extra></extra>"
            ),
        )
    )

    fig.add_trace(
        go.Scatter(
            x=work["Дата УПД"],
            y=work["Цена, упр"],
            name="Управленческая",
            mode="lines+markers",
            line={
                "color": COLORS["dark_green"],
                "width": 2,
            },
            marker={
                "size": 7,
            },
            customdata=np.column_stack(
                [
                    work["Номер УПД"].astype(str),
                    work["Поставщик"].astype(str),
                    work["Количество, шт"],
                ]
            ),
            hovertemplate=(
                "<b>%{x|%d.%m.%Y}</b>"
                "<br>Цена, упр: %{y:,.2f} ₽"
                "<br>УПД: %{customdata[0]}"
                "<br>Поставщик: %{customdata[1]}"
                "<br>Количество: %{customdata[2]:,.0f}"
                "<extra></extra>"
            ),
        )
    )

    fig.update_layout(
        **base_layout(
            height=430,
            margin={
                "l": 65,
                "r": 30,
                "t": 35,
                "b": 55,
            },
        ),
        hovermode="x unified",
        legend={
            "orientation": "h",
            "x": 0,
            "y": 1.06,
        },
    )

    fig.update_xaxes(
        title=None,
        showgrid=False,
        linecolor=COLORS["border"],
    )

    fig.update_yaxes(
        title="Цена за единицу, ₽",
        tickformat=",.2f",
        showgrid=True,
        gridcolor="#E5E7EB",
        griddash="dot",
        zeroline=False,
    )

    return fig