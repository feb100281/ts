# gear/app/daily_sales/stocks/dashboard_stock/distribution_charts.py

"""Plotly-графики для вкладок распределения остатков."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go


TEXT = "#18352F"
MUTED = "#60746D"
GRID = "#E7ECEA"
PRIMARY = "#007A5E"
SECONDARY = "#A6B6B0"
ACCENT = "#C58A26"
PAPER = "#FFFFFF"


def _empty_figure(
    title: str = "Нет данных",
    subtitle: str = "Для выбранных фильтров данные отсутствуют.",
) -> go.Figure:
    fig = go.Figure()

    fig.add_annotation(
        x=0.5,
        y=0.56,
        xref="paper",
        yref="paper",
        text=f"<b>{title}</b>",
        showarrow=False,
        font={
            "size": 17,
            "color": TEXT,
        },
    )

    fig.add_annotation(
        x=0.5,
        y=0.46,
        xref="paper",
        yref="paper",
        text=subtitle,
        showarrow=False,
        font={
            "size": 12,
            "color": MUTED,
        },
    )

    fig.update_layout(
        height=470,
        paper_bgcolor=PAPER,
        plot_bgcolor=PAPER,
        margin={
            "l": 20,
            "r": 20,
            "t": 30,
            "b": 20,
        },
        xaxis={
            "visible": False,
        },
        yaxis={
            "visible": False,
        },
    )

    return fig


def _safe_number_series(
    df: pd.DataFrame,
    column: str,
) -> pd.Series:
    if column not in df.columns:
        return pd.Series(
            0,
            index=df.index,
            dtype=float,
        )

    return pd.to_numeric(
        df[column],
        errors="coerce",
    ).fillna(0)


def _prepare_stock_columns(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Нормализует числовые показатели остатков.

    total_qty:
        физический остаток
        + в пути от клиента
        + в пути к клиенту.
    """
    work = df.copy()

    work["on_hand"] = _safe_number_series(
        work,
        "on_hand",
    )

    work["in_transit"] = _safe_number_series(
        work,
        "in_transit",
    )

    if "total_qty" in work.columns:
        work["total_qty"] = _safe_number_series(
            work,
            "total_qty",
        )
    else:
        work["total_qty"] = (
            work["on_hand"]
            + work["in_transit"]
        )

    if "warehouses" in work.columns:
        work["warehouses"] = _safe_number_series(
            work,
            "warehouses",
        )
    else:
        work["warehouses"] = 0

    if "products" in work.columns:
        work["products"] = _safe_number_series(
            work,
            "products",
        )
    else:
        work["products"] = 0

    return work


def _base_layout(
    fig: go.Figure,
    height: int,
    left_margin: int,
) -> None:
    fig.update_layout(
        height=height,
        paper_bgcolor=PAPER,
        plot_bgcolor=PAPER,
        margin={
            "l": left_margin,
            "r": 75,
            "t": 36,
            "b": 45,
        },
        font={
            "family": (
                "Inter, Arial, sans-serif"
            ),
            "color": TEXT,
        },
        hoverlabel={
            "bgcolor": "#FFFFFF",
            "bordercolor": "#D6DFDB",
            "font": {
                "family": (
                    "Inter, Arial, sans-serif"
                ),
                "color": TEXT,
            },
        },
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "left",
            "x": 0,
            "font": {
                "size": 11,
            },
        },
        bargap=0.30,
    )


def build_regions_distribution_chart(
    df: pd.DataFrame,
    top_n: int = 18,
) -> go.Figure:
    """
    Распределение общего количества товара по регионам.

    Столбик:
        физический остаток + товар в пути.

    Доля региона рассчитывается по total_qty.
    """
    if df is None or df.empty:
        return _empty_figure()

    if "region" not in df.columns:
        return _empty_figure(
            title="Нет колонки region",
            subtitle=(
                "Проверьте результат "
                "get_stock_regions()."
            ),
        )

    work = _prepare_stock_columns(
        df
    )

    work["region"] = (
        work["region"]
        .fillna("Не определено")
        .astype(str)
        .str.strip()
        .replace(
            "",
            "Не определено",
        )
    )

    work = (
        work[
            work["total_qty"] > 0
        ]
        .sort_values(
            "total_qty",
            ascending=False,
        )
        .head(top_n)
        .sort_values(
            "total_qty",
            ascending=True,
        )
        .reset_index(drop=True)
    )

    if work.empty:
        return _empty_figure()

    displayed_total = float(
        work["total_qty"].sum()
    )

    if displayed_total > 0:
        work["share_pct"] = (
            work["total_qty"]
            / displayed_total
            * 100
        )
    else:
        work["share_pct"] = 0.0

    work["transit_pct"] = (
        work["in_transit"]
        / work["total_qty"].replace(
            0,
            pd.NA,
        )
        * 100
    ).fillna(0)

    work["right_label"] = work.apply(
        lambda row: (
            f"<b>{row['total_qty']:,.0f}</b> "
            f"· {row['share_pct']:.1f}%"
        ).replace(
            ",",
            " ",
        ),
        axis=1,
    )

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            name="На складе",
            x=work["on_hand"],
            y=work["region"],
            orientation="h",
            marker={
                "color": PRIMARY,
                "opacity": 0.88,
            },
            customdata=work[
                [
                    "in_transit",
                    "total_qty",
                    "share_pct",
                    "transit_pct",
                ]
            ],
            hovertemplate=(
                "<b>%{y}</b><br>"
                "На складе: "
                "<b>%{x:,.0f} шт</b><br>"
                "В пути: "
                "%{customdata[0]:,.0f} шт<br>"
                "Всего товара: "
                "<b>%{customdata[1]:,.0f} шт</b><br>"
                "Доля показанных регионов: "
                "%{customdata[2]:.1f}%<br>"
                "Доля товара в пути: "
                "%{customdata[3]:.1f}%"
                "<extra></extra>"
            ),
        )
    )

    fig.add_trace(
        go.Bar(
            name="В пути",
            x=work["in_transit"],
            y=work["region"],
            orientation="h",
            marker={
                "color": SECONDARY,
                "opacity": 0.82,
            },
            customdata=work[
                [
                    "on_hand",
                    "total_qty",
                    "share_pct",
                    "transit_pct",
                ]
            ],
            hovertemplate=(
                "<b>%{y}</b><br>"
                "На складе: "
                "%{customdata[0]:,.0f} шт<br>"
                "В пути: "
                "<b>%{x:,.0f} шт</b><br>"
                "Всего товара: "
                "<b>%{customdata[1]:,.0f} шт</b><br>"
                "Доля показанных регионов: "
                "%{customdata[2]:.1f}%<br>"
                "Доля товара в пути: "
                "%{customdata[3]:.1f}%"
                "<extra></extra>"
            ),
        )
    )

    fig.add_trace(
        go.Scatter(
            x=work["total_qty"],
            y=work["region"],
            mode="text",
            text=work["right_label"],
            textposition="middle right",
            textfont={
                "size": 11,
                "color": TEXT,
            },
            hoverinfo="skip",
            cliponaxis=False,
            showlegend=False,
        )
    )

    _base_layout(
        fig,
        height=max(
            470,
            76 + len(work) * 31,
        ),
        left_margin=145,
    )

    fig.update_layout(
        barmode="stack",
    )

    fig.update_xaxes(
        title="Общее количество товара, шт",
        showgrid=True,
        gridcolor=GRID,
        zeroline=False,
        tickformat=",.0f",
        separatethousands=True,
        fixedrange=True,
    )

    fig.update_yaxes(
        title=None,
        showgrid=False,
        fixedrange=True,
        automargin=True,
    )

    return fig


def build_pareto_chart(
    df: pd.DataFrame,
    entity_label: str,
    top_n: int = 20,
) -> go.Figure:
    """
    Pareto-график по общему количеству товара.

    Использует total_qty:
        на складе + в пути.

    Линия показывает накопленную долю
    выбранных Top-позиций.
    """
    if df is None or df.empty:
        return _empty_figure()

    required_columns = {
        "name",
        "total_qty",
    }

    if not required_columns.issubset(
        df.columns
    ):
        return _empty_figure(
            title="Недостаточно данных",
            subtitle=(
                "Для графика нужны колонки "
                "name и total_qty."
            ),
        )

    work = _prepare_stock_columns(
        df
    )

    work["name"] = (
        work["name"]
        .fillna("Не указано")
        .astype(str)
        .str.strip()
        .replace(
            "",
            "Не указано",
        )
    )

    work = (
        work[
            work["total_qty"] > 0
        ]
        .sort_values(
            "total_qty",
            ascending=False,
        )
        .head(top_n)
        .reset_index(drop=True)
    )

    if work.empty:
        return _empty_figure()

    displayed_total = float(
        work["total_qty"].sum()
    )

    if displayed_total > 0:
        work[
            "display_share_pct"
        ] = (
            work["total_qty"]
            / displayed_total
            * 100
        )
    else:
        work[
            "display_share_pct"
        ] = 0.0

    work[
        "display_cumulative_pct"
    ] = (
        work["display_share_pct"]
        .cumsum()
    )

    if "share_pct" not in work.columns:
        work["share_pct"] = (
            work["display_share_pct"]
        )
    else:
        work["share_pct"] = pd.to_numeric(
            work["share_pct"],
            errors="coerce",
        ).fillna(
            work["display_share_pct"]
        )

    work["bar_label"] = work.apply(
        lambda row: (
            f"{row['total_qty']:,.0f} · "
            f"{row['share_pct']:.1f}%"
        ).replace(
            ",",
            " ",
        ),
        axis=1,
    )

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            name="Всего товара",
            x=work["name"],
            y=work["total_qty"],
            marker={
                "color": PRIMARY,
                "opacity": 0.84,
            },
            text=work["bar_label"],
            textposition="outside",
            textfont={
                "size": 10,
                "color": TEXT,
            },
            cliponaxis=False,
            customdata=work[
                [
                    "on_hand",
                    "in_transit",
                    "share_pct",
                    "warehouses",
                    "products",
                ]
            ],
            hovertemplate=(
                f"<b>{entity_label}: "
                "%{x}</b><br>"
                "Всего товара: "
                "<b>%{y:,.0f} шт</b><br>"
                "На складе: "
                "%{customdata[0]:,.0f} шт<br>"
                "В пути: "
                "%{customdata[1]:,.0f} шт<br>"
                "Доля общего количества: "
                "%{customdata[2]:.1f}%<br>"
                "Складов присутствия: "
                "%{customdata[3]:,.0f}<br>"
                "Уникальных NM ID: "
                "%{customdata[4]:,.0f}"
                "<extra></extra>"
            ),
        )
    )

    fig.add_trace(
        go.Scatter(
            name="Накопленная доля Top",
            x=work["name"],
            y=work[
                "display_cumulative_pct"
            ],
            yaxis="y2",
            mode="lines+markers",
            line={
                "color": ACCENT,
                "width": 2.5,
            },
            marker={
                "size": 7,
                "color": ACCENT,
                "line": {
                    "color": "#FFFFFF",
                    "width": 1.5,
                },
            },
            hovertemplate=(
                f"<b>{entity_label}: "
                "%{x}</b><br>"
                "Накопленная доля среди "
                "показанных позиций: "
                "<b>%{y:.1f}%</b>"
                "<extra></extra>"
            ),
        )
    )

    fig.add_hline(
        y=80,
        yref="y2",
        line={
            "color": "#9AABA4",
            "width": 1,
            "dash": "dot",
        },
        annotation_text="80%",
        annotation_position="top right",
        annotation_font={
            "size": 10,
            "color": MUTED,
        },
    )

    _base_layout(
        fig,
        height=520,
        left_margin=55,
    )

    fig.update_layout(
        yaxis2={
            "title": (
                "Накопленная доля, %"
            ),
            "overlaying": "y",
            "side": "right",
            "range": [
                0,
                108,
            ],
            "showgrid": False,
            "ticksuffix": "%",
            "fixedrange": True,
        },
    )

    fig.update_xaxes(
        title=None,
        tickangle=-35,
        showgrid=False,
        fixedrange=True,
        tickfont={
            "size": 10,
        },
    )

    fig.update_yaxes(
        title="Общее количество товара, шт",
        showgrid=True,
        gridcolor=GRID,
        zeroline=False,
        tickformat=",.0f",
        fixedrange=True,
    )

    return fig


def build_concentration_chart(
    df: pd.DataFrame,
    entity_label: str,
    top_n: int = 14,
) -> go.Figure:
    """
    Горизонтальный рейтинг по общему количеству товара.

    Использует total_qty:
        на складе + в пути.

    Дополнительно показывает:
    - долю общего количества;
    - количество складов;
    - количество уникальных NM ID.
    """
    if df is None or df.empty:
        return _empty_figure()

    required_columns = {
        "name",
        "total_qty",
    }

    if not required_columns.issubset(
        df.columns
    ):
        return _empty_figure(
            title="Недостаточно данных",
            subtitle=(
                "Для графика нужны колонки "
                "name и total_qty."
            ),
        )

    work = _prepare_stock_columns(
        df
    )

    work["name"] = (
        work["name"]
        .fillna("Не указано")
        .astype(str)
        .str.strip()
        .replace(
            "",
            "Не указано",
        )
    )

    if "share_pct" not in work.columns:
        total_quantity = float(
            work["total_qty"].sum()
        )

        if total_quantity > 0:
            work["share_pct"] = (
                work["total_qty"]
                / total_quantity
                * 100
            )
        else:
            work["share_pct"] = 0.0
    else:
        work["share_pct"] = pd.to_numeric(
            work["share_pct"],
            errors="coerce",
        ).fillna(0)

    work = (
        work[
            work["total_qty"] > 0
        ]
        .sort_values(
            "total_qty",
            ascending=False,
        )
        .head(top_n)
        .sort_values(
            "total_qty",
            ascending=True,
        )
        .reset_index(drop=True)
    )

    if work.empty:
        return _empty_figure()

    work["label"] = work.apply(
        lambda row: (
            f"<b>{row['total_qty']:,.0f}</b> "
            f"· {row['share_pct']:.1f}% "
            f"· {int(row['warehouses'])} скл."
        ).replace(
            ",",
            " ",
        ),
        axis=1,
    )

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=work["total_qty"],
            y=work["name"],
            orientation="h",
            marker={
                "color": PRIMARY,
                "opacity": 0.84,
            },
            customdata=work[
                [
                    "on_hand",
                    "in_transit",
                    "share_pct",
                    "warehouses",
                    "products",
                ]
            ],
            hovertemplate=(
                f"<b>{entity_label}: "
                "%{y}</b><br>"
                "Всего товара: "
                "<b>%{x:,.0f} шт</b><br>"
                "На складе: "
                "%{customdata[0]:,.0f} шт<br>"
                "В пути: "
                "%{customdata[1]:,.0f} шт<br>"
                "Доля общего количества: "
                "%{customdata[2]:.1f}%<br>"
                "Складов присутствия: "
                "%{customdata[3]:,.0f}<br>"
                "Уникальных NM ID: "
                "%{customdata[4]:,.0f}"
                "<extra></extra>"
            ),
            showlegend=False,
        )
    )

    fig.add_trace(
        go.Scatter(
            x=work["total_qty"],
            y=work["name"],
            mode="text",
            text=work["label"],
            textposition="middle right",
            textfont={
                "size": 11,
                "color": TEXT,
            },
            hoverinfo="skip",
            cliponaxis=False,
            showlegend=False,
        )
    )

    _base_layout(
        fig,
        height=max(
            470,
            90 + len(work) * 31,
        ),
        left_margin=190,
    )

    fig.update_xaxes(
        title="Общее количество товара, шт",
        showgrid=True,
        gridcolor=GRID,
        zeroline=False,
        tickformat=",.0f",
        fixedrange=True,
    )

    fig.update_yaxes(
        title=None,
        showgrid=False,
        fixedrange=True,
        automargin=True,
    )

    return fig
