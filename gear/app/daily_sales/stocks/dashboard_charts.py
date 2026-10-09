# gear/app/daily_sales/stocks/dashboard_charts.py

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go


COLOR_PRIMARY = "#007A5E"
COLOR_TEXT = "#18352F"
COLOR_MUTED = "#60746D"
COLOR_GRID = "#EDF1EF"


# =============================================================================
# ПУСТОЙ ГРАФИК
# =============================================================================

def empty_figure(
    message="Нет данных",
    height=520,
):
    fig = go.Figure()

    fig.add_annotation(
        text=message,

        x=0.5,
        y=0.5,

        xref="paper",
        yref="paper",

        showarrow=False,

        font=dict(
            family="Arial",
            size=15,
            color=COLOR_MUTED,
        ),
    )

    fig.update_layout(
        height=height,

        paper_bgcolor="white",
        plot_bgcolor="white",

        margin=dict(
            l=20,
            r=20,
            t=20,
            b=20,
        ),

        xaxis=dict(
            visible=False,
        ),

        yaxis=dict(
            visible=False,
        ),
    )

    return fig


# =============================================================================
# КАРТА СКЛАДОВ
# =============================================================================


def build_warehouses_map(
    df: pd.DataFrame,
):
    """
    Интерактивная карта складов.

    Логика:
    - один склад = одна точка;
    - карта занимает всю ширину контейнера;
    - размер точки слегка зависит от общего остатка;
    - клик по точке передает warehouse через customdata[0];
    - колесико мыши = масштаб;
    - перетаскивание = движение;
    - двойной клик / кнопка home = возврат общего вида;
    - визуальное выделение точки после клика не сохраняется;
    - склады без координат остаются в данных,
      но физически не отображаются на карте.
    """

    # =========================================================================
    # Пустые данные
    # =========================================================================

    if df.empty:
        return empty_figure(
            "Нет данных по складам",
            height=470,
        )

    work = df.copy()

    # =========================================================================
    # Подготовка числовых полей
    # =========================================================================

    for col in [
        "on_hand",
        "in_transit",
        "products",
        "total_qty",
        "lat",
        "lon",
    ]:
        if col in work.columns:
            work[col] = pd.to_numeric(
                work[col],
                errors="coerce",
            )

    for col in [
        "on_hand",
        "in_transit",
        "products",
        "total_qty",
    ]:
        if col in work.columns:
            work[col] = work[col].fillna(0)

    # =========================================================================
    # Координаты
    # =========================================================================

    if "has_coordinates" not in work.columns:
        work["has_coordinates"] = (
            work["lat"].notna()
            & work["lon"].notna()
        )

    total_count = int(
        len(work)
    )

    mapped_count = int(
        work["has_coordinates"]
        .fillna(False)
        .sum()
    )

    missing_count = (
        total_count
        - mapped_count
    )

    # На карту идут только склады
    # с реальными координатами.
    map_work = work[
        work["has_coordinates"].fillna(False)
    ].copy()

    map_work = map_work[
        map_work["lat"].notna()
        & map_work["lon"].notna()
    ].copy()

    if map_work.empty:
        return empty_figure(
            (
                "Нет координат складов. "
                f"Всего складов в данных: {total_count}"
            ),
            height=470,
        )

    # =========================================================================
    # Размер точек
    #
    # Размер показывает масштаб остатка,
    # но диапазон специально небольшой,
    # чтобы крупные склады не перекрывали остальные.
    # =========================================================================

    max_qty = float(
        map_work["total_qty"].max()
    )

    if max_qty > 0:
        marker_sizes = (
            10
            + (
                map_work["total_qty"]
                / max_qty
            ) ** 0.35
            * 9
        )
    else:
        marker_sizes = pd.Series(
            13,
            index=map_work.index,
        )

    # =========================================================================
    # Данные для hover / click
    #
    # customdata[0] = warehouse
    # customdata[1] = region
    # customdata[2] = on_hand
    # customdata[3] = in_transit
    # customdata[4] = products
    # customdata[5] = total_qty
    # =========================================================================

    customdata = map_work[
        [
            "warehouse",
            "region",
            "on_hand",
            "in_transit",
            "products",
            "total_qty",
        ]
    ].to_numpy()

    # =========================================================================
    # Figure
    # =========================================================================

    fig = go.Figure()

    # =========================================================================
    # Точки складов
    # =========================================================================

    fig.add_trace(
        go.Scattergeo(
            lon=map_work["lon"],
            lat=map_work["lat"],

            mode="markers",

            customdata=customdata,

            marker=dict(
                size=marker_sizes,

                color=COLOR_PRIMARY,

                opacity=0.88,

                line=dict(
                    width=1.5,
                    color="#FFFFFF",
                ),
            ),

            hovertemplate=(
                "<b>%{customdata[0]}</b>"
                "<br>"
                "%{customdata[1]}"
                "<br><br>"

                "На складе: "
                "<b>%{customdata[2]:,.0f} шт</b>"
                "<br>"

                "В пути: "
                "<b>%{customdata[3]:,.0f} шт</b>"
                "<br>"

                "Всего: "
                "<b>%{customdata[5]:,.0f} шт</b>"
                "<br>"

                "Товаров: "
                "<b>%{customdata[4]:,.0f} NM ID</b>"
                "<br><br>"

                "<b>Нажмите для детализации</b>"

                "<extra></extra>"
            ),

            showlegend=False,
        )
    )

    # =========================================================================
    # География
    #
    # ВАЖНО:
    # НЕ используем fitbounds="locations".
    #
    # Для широкого блока задаем диапазон вручную.
    # Поэтому карта России растягивается горизонтально
    # и не превращается в квадрат по центру страницы.
    # =========================================================================

    fig.update_geos(
        projection_type="natural earth",

        # Страны
        showcountries=True,
        countrycolor="#AEBDB6",
        countrywidth=0.8,

        # Региональные границы
        showsubunits=True,
        subunitcolor="#D2DDD8",
        subunitwidth=0.55,

        # Суша
        showland=True,
        landcolor="#F3F7F5",

        # Океан
        showocean=True,
        oceancolor="#FBFCFC",

        # Озера
        showlakes=True,
        lakecolor="#FBFCFC",

        # Реки
        showrivers=False,

        # Береговая линия
        showcoastlines=True,
        coastlinecolor="#80938A",
        coastlinewidth=0.8,

        resolution=50,

        # -------------------------------------------------------------
        # Широкий диапазон карты.
        #
        # Это и дает нормальную карту на всю ширину.
        # -------------------------------------------------------------

        lonaxis=dict(
            # Чуть более плотный исходный вид:
            # Россия занимает больше полезной площади,
            # но крайние склады не обрезаются.
            range=[
                25,
                150,
            ],
        ),

        lataxis=dict(
            range=[
                41,
                73,
            ],
        ),

        # Geo занимает всю доступную область figure
        domain=dict(
            x=[
                0,
                1,
            ],
            y=[
                0,
                1,
            ],
        ),

        bgcolor="white",
    )

    # =========================================================================
    # Статус карты
    # =========================================================================

    if missing_count > 0:
        map_status = (
            f"На карте: {mapped_count} из {total_count} складов"
            f"  ·  без координат: {missing_count}"
        )

    else:
        map_status = (
            f"Все склады на карте: {total_count}"
        )

    fig.add_annotation(
        x=0.012,
        y=0.018,

        xref="paper",
        yref="paper",

        xanchor="left",
        yanchor="bottom",

        text=map_status,

        showarrow=False,

        font=dict(
            family="Arial",
            size=12,
            color=COLOR_MUTED,
        ),

        bgcolor="rgba(255,255,255,0.94)",

        bordercolor="#D6DFDB",
        borderwidth=1,
        borderpad=6,
    )

    # =========================================================================
    # Layout
    # =========================================================================

    fig.update_layout(
        # Не делаем 650:
        # именно такая большая высота создавала
        # ощущение огромного пустого пространства.
        height=470,

        autosize=True,

        paper_bgcolor="white",
        plot_bgcolor="white",

        margin=dict(
            l=0,
            r=0,
            t=0,
            b=0,
        ),

        font=dict(
            family="Arial",
            color=COLOR_TEXT,
        ),

        # Нужен clickData,
        # но не нужен режим selected.
        clickmode="event",

        # Стабильное состояние карты.
        # Клики по точкам / обновление окружающих компонентов
        # не должны внезапно менять текущий вид.
        uirevision="stock-warehouses-map-v1",

        hoverlabel=dict(
            bgcolor="white",

            bordercolor="#D6DFDB",

            font=dict(
                family="Arial",
                size=12,
                color=COLOR_TEXT,
            ),

            align="left",
        ),
    )

    return fig

# =============================================================================
# ГРАФИК ПО РЕГИОНАМ
# =============================================================================

def build_regions_chart(
    df: pd.DataFrame,
):
    """
    Профессиональный stacked bar по регионам.

    Показывает:
    - физический остаток;
    - товары в пути;
    - общий объём;
    - долю региона в общем объёме;
    - число складов в hover.
    """
    if df.empty:
        return empty_figure(
            "Нет данных по регионам",
            height=430,
        )

    work = df.copy()

    for col in [
        "on_hand",
        "in_transit",
        "warehouses",
        "total_qty",
    ]:
        work[col] = pd.to_numeric(
            work[col],
            errors="coerce",
        ).fillna(0)

    grand_total = float(
        work["total_qty"].sum()
    )

    work["share_pct"] = (
        work["total_qty"]
        / grand_total
        * 100
        if grand_total > 0
        else 0
    )

    work = work.sort_values(
        "total_qty",
        ascending=True,
    )

    customdata = work[
        [
            "region",
            "warehouses",
            "total_qty",
            "share_pct",
        ]
    ].to_numpy()

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            y=work["region"],
            x=work["on_hand"],
            name="На складе",
            orientation="h",
            marker=dict(
                color="rgba(0,122,94,0.82)",
            ),
            customdata=customdata,
            hovertemplate=(
                "<b>%{customdata[0]}</b><br><br>"
                "На складе: <b>%{x:,.0f} шт</b><br>"
                "Всего: <b>%{customdata[2]:,.0f} шт</b><br>"
                "Доля: <b>%{customdata[3]:.1f}%</b><br>"
                "Складов: <b>%{customdata[1]:,.0f}</b>"
                "<extra></extra>"
            ),
        )
    )

    fig.add_trace(
        go.Bar(
            y=work["region"],
            x=work["in_transit"],
            name="В пути",
            orientation="h",
            marker=dict(
                color="rgba(96,116,109,0.28)",
            ),
            customdata=customdata,
            hovertemplate=(
                "<b>%{customdata[0]}</b><br><br>"
                "В пути: <b>%{x:,.0f} шт</b><br>"
                "Всего: <b>%{customdata[2]:,.0f} шт</b><br>"
                "Доля: <b>%{customdata[3]:.1f}%</b>"
                "<extra></extra>"
            ),
        )
    )

    # Подпись справа от суммарного столбика.
    fig.add_trace(
        go.Scatter(
            x=work["total_qty"],
            y=work["region"],
            mode="text",
            text=[
                (
                    f"{value:,.0f}".replace(",", " ")
                    + f" · {share:.1f}%"
                )
                for value, share
                in zip(
                    work["total_qty"],
                    work["share_pct"],
                )
            ],
            textposition="middle right",
            textfont=dict(
                family="Arial",
                size=11,
                color=COLOR_TEXT,
            ),
            hoverinfo="skip",
            showlegend=False,
            cliponaxis=False,
        )
    )

    height = max(
        420,
        95 + len(work) * 48,
    )

    max_total = float(
        work["total_qty"].max()
    ) if not work.empty else 0

    fig.update_layout(
        height=height,
        barmode="stack",
        paper_bgcolor="white",
        plot_bgcolor="white",
        margin=dict(
            l=10,
            r=110,
            t=25,
            b=35,
        ),
        legend=dict(
            orientation="h",
            y=1.08,
            x=0,
        ),
        xaxis=dict(
            showgrid=True,
            gridcolor=COLOR_GRID,
            zeroline=False,
            title=None,
            range=[
                0,
                max_total * 1.16
                if max_total > 0
                else 1,
            ],
            tickformat=",.0f",
        ),
        yaxis=dict(
            title=None,
            showgrid=False,
            automargin=True,
        ),
        font=dict(
            family="Arial",
            color=COLOR_TEXT,
        ),
        clickmode="none",
        hoverlabel=dict(
            bgcolor="white",
            bordercolor="#D6DFDB",
            font=dict(
                family="Arial",
                size=12,
                color=COLOR_TEXT,
            ),
            align="left",
        ),
    )

    return fig

