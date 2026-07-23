"""Компактная аналитическая карточка склада по клику на карте.

ВАЖНО:
- только аналитика;
- без таблицы товаров;
- без Excel;
- без перемещений;
- без происшествий.
"""

from __future__ import annotations

import pandas as pd
import dash_mantine_components as dmc

from dash import html, Input, Output, State, no_update

from ..dashboard_data import get_warehouse_modal_data
from .components import metric_card
from .helpers import fmt
from .ids import (
    STOCK_MAP_ID,
    STOCK_CONTEXT_ID,
    STOCK_MAP_MODAL_ID,
    STOCK_MAP_MODAL_TITLE_ID,
    STOCK_MAP_MODAL_SUBTITLE_ID,
    STOCK_MAP_MODAL_KPI_ID,
    STOCK_MAP_MODAL_BRAND_CHART_ID,
    STOCK_MAP_MODAL_CATEGORY_CHART_ID,
)


TEXT = "#18352F"
MUTED = "#60746D"
BORDER = "#D6DFDB"
PRIMARY = "#007A5E"


def _share_bar(
    label: str,
    value: float,
    total: float,
    rank: int | None = None,
):
    value = float(value or 0)
    total = float(total or 0)

    share = (
        value / total * 100
        if total > 0
        else 0
    )

    prefix = (
        f"{rank}. "
        if rank is not None
        else ""
    )

    return html.Div(
        [
            dmc.Group(
                justify="space-between",
                align="center",
                mb=5,
                children=[
                    dmc.Text(
                        f"{prefix}{label}",
                        size="sm",
                        fw=600,
                        c=TEXT,
                        style={
                            "maxWidth": "72%",
                            "overflow": "hidden",
                            "textOverflow": "ellipsis",
                            "whiteSpace": "nowrap",
                        },
                    ),
                    dmc.Text(
                        f"{fmt(value)} шт · {share:.1f}%",
                        size="xs",
                        c=MUTED,
                    ),
                ],
            ),
            html.Div(
                style={
                    "height": "8px",
                    "background": "#EEF3F1",
                    "width": "100%",
                    "overflow": "hidden",
                },
                children=[
                    html.Div(
                        style={
                            "height": "100%",
                            "width": f"{min(max(share, 0), 100):.2f}%",
                            "background": PRIMARY,
                            "opacity": 0.78,
                        }
                    )
                ],
            ),
        ],
        style={
            "marginBottom": "14px",
        },
    )


def _ranking_block(
    title: str,
    subtitle: str,
    df: pd.DataFrame,
    name_col: str,
    value_col: str,
    total: float,
    top_n: int = 7,
):
    if df is None or df.empty:
        body = dmc.Text(
            "Нет данных",
            size="sm",
            c="dimmed",
        )
    else:
        work = df.copy()

        work[value_col] = pd.to_numeric(
            work[value_col],
            errors="coerce",
        ).fillna(0)

        work = (
            work[
                work[value_col] > 0
            ]
            .sort_values(
                value_col,
                ascending=False,
            )
            .head(top_n)
            .reset_index(drop=True)
        )

        if work.empty:
            body = dmc.Text(
                "Нет физического остатка",
                size="sm",
                c="dimmed",
            )
        else:
            body = html.Div(
                [
                    _share_bar(
                        label=str(
                            row[name_col]
                        ),
                        value=row[value_col],
                        total=total,
                        rank=idx + 1,
                    )
                    for idx, row
                    in work.iterrows()
                ]
            )

    return dmc.Paper(
        radius=0,
        p="lg",
        style={
            "border": f"1px solid {BORDER}",
            "background": "#FFFFFF",
            "minHeight": "390px",
        },
        children=[
            dmc.Text(
                title,
                fw=700,
                size="md",
                c=TEXT,
            ),
            dmc.Text(
                subtitle,
                size="xs",
                c="dimmed",
                mt=3,
                mb="lg",
            ),
            body,
        ],
    )


def _stock_structure(
    on_hand: float,
    in_transit: float,
):
    total = float(on_hand or 0) + float(
        in_transit or 0
    )

    on_share = (
        on_hand / total * 100
        if total > 0
        else 0
    )

    transit_share = (
        in_transit / total * 100
        if total > 0
        else 0
    )

    return dmc.Paper(
        radius=0,
        p="lg",
        style={
            "border": f"1px solid {BORDER}",
            "background": "#F8FAF9",
        },
        children=[
            dmc.Group(
                justify="space-between",
                children=[
                    html.Div(
                        [
                            dmc.Text(
                                "Структура товарного запаса",
                                fw=700,
                                size="sm",
                                c=TEXT,
                            ),
                            dmc.Text(
                                (
                                    "Физический остаток и товар в пути "
                                    "в общем объёме выбранного склада."
                                ),
                                size="xs",
                                c="dimmed",
                                mt=2,
                            ),
                        ]
                    ),
                    dmc.Text(
                        f"{fmt(total)} шт",
                        fw=700,
                        c=TEXT,
                    ),
                ],
            ),

            html.Div(
                style={
                    "display": "flex",
                    "height": "18px",
                    "width": "100%",
                    "marginTop": "18px",
                    "background": "#EEF3F1",
                    "overflow": "hidden",
                },
                children=[
                    html.Div(
                        title=f"На складе: {fmt(on_hand)} шт",
                        style={
                            "width": f"{on_share:.3f}%",
                            "height": "100%",
                            "background": PRIMARY,
                        },
                    ),
                    html.Div(
                        title=f"В пути: {fmt(in_transit)} шт",
                        style={
                            "width": f"{transit_share:.3f}%",
                            "height": "100%",
                            "background": "#9AABA4",
                        },
                    ),
                ],
            ),

            dmc.Group(
                justify="space-between",
                mt="sm",
                children=[
                    dmc.Group(
                        gap=8,
                        children=[
                            html.Div(
                                style={
                                    "width": "10px",
                                    "height": "10px",
                                    "background": PRIMARY,
                                }
                            ),
                            dmc.Text(
                                (
                                    f"На складе · {fmt(on_hand)} шт "
                                    f"· {on_share:.1f}%"
                                ),
                                size="xs",
                                c=MUTED,
                            ),
                        ],
                    ),
                    dmc.Group(
                        gap=8,
                        children=[
                            html.Div(
                                style={
                                    "width": "10px",
                                    "height": "10px",
                                    "background": "#9AABA4",
                                }
                            ),
                            dmc.Text(
                                (
                                    f"В пути · {fmt(in_transit)} шт "
                                    f"· {transit_share:.1f}%"
                                ),
                                size="xs",
                                c=MUTED,
                            ),
                        ],
                    ),
                ],
            ),
        ],
    )


def map_info_modal():
    return dmc.Modal(
        id=STOCK_MAP_MODAL_ID,
        opened=False,
        size="xl",
        radius=0,
        centered=True,
        title=dmc.Text(
            id=STOCK_MAP_MODAL_TITLE_ID,
            children="Склад",
            fw=700,
            size="lg",
        ),
        children=[
            dmc.Text(
                id=STOCK_MAP_MODAL_SUBTITLE_ID,
                size="sm",
                c="dimmed",
                mb="lg",
            ),

            html.Div(
                id=STOCK_MAP_MODAL_KPI_ID,
            ),

            dmc.SimpleGrid(
                cols={
                    "base": 1,
                    "lg": 2,
                },
                spacing="md",
                mt="md",
                children=[
                    html.Div(
                        id=STOCK_MAP_MODAL_BRAND_CHART_ID,
                    ),
                    html.Div(
                        id=STOCK_MAP_MODAL_CATEGORY_CHART_ID,
                    ),
                ],
            ),
        ],
    )


def register_map_modal_callbacks(app):
    @app.callback(
        Output(
            STOCK_MAP_MODAL_ID,
            "opened",
        ),
        Output(
            STOCK_MAP_MODAL_TITLE_ID,
            "children",
        ),
        Output(
            STOCK_MAP_MODAL_SUBTITLE_ID,
            "children",
        ),
        Output(
            STOCK_MAP_MODAL_KPI_ID,
            "children",
        ),
        Output(
            STOCK_MAP_MODAL_BRAND_CHART_ID,
            "children",
        ),
        Output(
            STOCK_MAP_MODAL_CATEGORY_CHART_ID,
            "children",
        ),

        Input(
            STOCK_MAP_ID,
            "clickData",
        ),

        State(
            STOCK_CONTEXT_ID,
            "data",
        ),

        prevent_initial_call=True,
    )
    def open_map_info_modal(
        click_data,
        context,
    ):
        if (
            not click_data
            or not click_data.get("points")
        ):
            return (
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
            )

        customdata = (
            click_data["points"][0]
            .get("customdata")
        )

        if not customdata:
            return (
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
            )

        warehouse_name = str(
            customdata[0]
        ).strip()

        context = context or {}
        report_date = context.get(
            "report_date"
        )

        payload = get_warehouse_modal_data(
            report_date=report_date,
            warehouse_name=warehouse_name,
            brand_list=context.get("brand_list"),
            cat_list=context.get("cat_list"),
            gender_list=context.get("gender_list"),
        )

        summary = payload["summary"]

        region = ""
        for row in context.get("warehouses") or []:
            if row.get("warehouse") == warehouse_name:
                region = (
                    row.get("region")
                    or ""
                )
                break

        date_label = (
            pd.to_datetime(
                report_date
            ).strftime("%d.%m.%Y")
            if report_date
            else ""
        )

        kpi = dmc.Stack(
            gap="md",
            children=[
                dmc.SimpleGrid(
                    cols={
                        "base": 2,
                        "sm": 3,
                        "lg": 5,
                    },
                    spacing="sm",
                    children=[
                        metric_card(
                            "На складе",
                            summary["on_hand"],
                        ),
                        metric_card(
                            "В пути",
                            summary["in_transit"],
                        ),
                        metric_card(
                            "Всего",
                            summary["total"],
                        ),
                        metric_card(
                            "Товаров",
                            summary["nm_count"],
                            "NM ID",
                        ),
                        metric_card(
                            "Размеров / Chrt ID",
                            summary["sizes_count"],
                            "",
                        ),
                    ],
                ),
                _stock_structure(
                    summary["on_hand"],
                    summary["in_transit"],
                ),
            ],
        )

        brand_block = _ranking_block(
            title="Крупнейшие бренды",
            subtitle=(
                "Top брендов по физическому остатку "
                "на выбранном складе."
            ),
            df=payload["brands"],
            name_col="brand",
            value_col="on_hand",
            total=summary["on_hand"],
            top_n=7,
        )

        category_block = _ranking_block(
            title="Крупнейшие категории",
            subtitle=(
                "Top категорий по физическому остатку "
                "на выбранном складе."
            ),
            df=payload["categories"],
            name_col="category",
            value_col="on_hand",
            total=summary["on_hand"],
            top_n=7,
        )

        subtitle = " · ".join(
            value
            for value in [
                region,
                (
                    f"остатки на {date_label}"
                    if date_label
                    else ""
                ),
            ]
            if value
        )

        return (
            True,
            warehouse_name,
            subtitle,
            kpi,
            brand_block,
            category_block,
        )
