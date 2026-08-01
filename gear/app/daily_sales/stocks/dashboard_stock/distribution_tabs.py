"""UI-блок с вкладками: регионы, бренды, категории."""

from __future__ import annotations

import pandas as pd
import dash_mantine_components as dmc

from dash import dcc, html
from dash_iconify import DashIconify

from .distribution_charts import (
    build_regions_distribution_chart,
    build_pareto_chart,
    build_concentration_chart,
)
from .ids import (
    STOCK_DISTRIBUTION_TABS_ID,
    STOCK_REGION_CHART_ID,
    STOCK_BRAND_CHART_ID,
    STOCK_CATEGORY_CHART_ID,
)


BORDER = "#D6DFDB"
TEXT = "#18352F"
MUTED = "#60746D"


GRAPH_CONFIG = {
    "displayModeBar": True,
    "displaylogo": False,
    "responsive": True,
    "scrollZoom": False,
    "doubleClick": "reset",
    "modeBarButtonsToRemove": [
        "lasso2d",
        "select2d",
        "autoScale2d",
    ],
    "toImageButtonOptions": {
        "format": "png",
        "filename": "stock_distribution",
        "scale": 2,
    },
}


def _tab_label(
    icon: str,
    label: str,
    count: int,
):
    return dmc.Group(
        gap=8,
        wrap="nowrap",
        children=[
            DashIconify(
                icon=icon,
                width=17,
                color="#007A5E",
            ),
            dmc.Text(
                label,
                size="sm",
                fw=600,
            ),
            dmc.Badge(
                str(int(count or 0)),
                size="sm",
                radius=0,
                variant="light",
                color="gray",
            ),
        ],
    )


def _panel_header(
    title: str,
    subtitle: str,
    insight: str,
):
    return dmc.Group(
        justify="space-between",
        align="flex-start",
        mb="sm",
        gap="md",
        children=[
            html.Div(
                [
                    dmc.Text(
                        title,
                        fw=700,
                        c=TEXT,
                    ),
                    dmc.Text(
                        subtitle,
                        size="xs",
                        c="dimmed",
                        mt=2,
                    ),
                ]
            ),
            dmc.Paper(
                radius=0,
                px="sm",
                py=7,
                style={
                    "border": "1px solid #E0E7E4",
                    "background": "#F7FAF9",
                    "maxWidth": "440px",
                },
                children=dmc.Group(
                    gap=7,
                    wrap="nowrap",
                    children=[
                        DashIconify(
                            icon="material-symbols:lightbulb-outline-rounded",
                            width=17,
                            color="#C58A26",
                        ),
                        dmc.Text(
                            insight,
                            size="xs",
                            c=MUTED,
                        ),
                    ],
                ),
            ),
        ],
    )


def _top_share(
    df: pd.DataFrame,
    top_n: int,
) -> float:
    if df is None or df.empty:
        return 0.0

    values = pd.to_numeric(
        df.get(
            "on_hand",
            pd.Series(dtype=float),
        ),
        errors="coerce",
    ).fillna(0)

    total = float(
        values.sum()
    )

    if total <= 0:
        return 0.0

    return float(
        values.nlargest(top_n).sum()
        / total
        * 100
    )


def build_stock_distribution_tabs(
    regions: pd.DataFrame,
    brands: pd.DataFrame,
    categories: pd.DataFrame,
):
    """Возвращает полностью готовый аналитический блок."""
    regions = (
        regions
        if regions is not None
        else pd.DataFrame()
    )
    brands = (
        brands
        if brands is not None
        else pd.DataFrame()
    )
    categories = (
        categories
        if categories is not None
        else pd.DataFrame()
    )

    region_count = (
        regions["region"].nunique()
        if "region" in regions.columns
        else len(regions)
    )

    brand_count = (
        brands["name"].nunique()
        if "name" in brands.columns
        else len(brands)
    )

    category_count = (
        categories["name"].nunique()
        if "name" in categories.columns
        else len(categories)
    )

    top_5_brand_share = _top_share(
        brands,
        top_n=5,
    )
    top_5_category_share = _top_share(
        categories,
        top_n=5,
    )

    return dmc.Paper(
        radius=0,
        p="md",
        style={
            "border": f"1px solid {BORDER}",
            "background": "#FFFFFF",
        },
        children=[
            dmc.Group(
                justify="space-between",
                align="flex-start",
                mb="md",
                children=[
                    html.Div(
                        [
                            dmc.Text(
                                "Структура товарных остатков",
                                fw=700,
                                c=TEXT,
                            ),
                            dmc.Text(
                                (
                                    "Сравнение географии, брендов и категорий. "
                                    "Все показатели учитывают выбранные фильтры."
                                ),
                                size="xs",
                                c="dimmed",
                                mt=2,
                            ),
                        ]
                    ),
                    dmc.Text(
                        "Интерактивная аналитика",
                        size="xs",
                        c="dimmed",
                    ),
                ],
            ),

            dmc.Tabs(
                id=STOCK_DISTRIBUTION_TABS_ID,
                value="regions",
                keepMounted=True,
                variant="outline",
                radius=0,
                children=[
                    dmc.TabsList(
                        children=[
                            dmc.TabsTab(
                                _tab_label(
                                    icon="material-symbols:map-outline",
                                    label="По регионам",
                                    count=region_count,
                                ),
                                value="regions",
                            ),
                            dmc.TabsTab(
                                _tab_label(
                                    icon="material-symbols:verified-outline-rounded",
                                    label="По брендам",
                                    count=brand_count,
                                ),
                                value="brands",
                            ),
                            dmc.TabsTab(
                                _tab_label(
                                    icon="material-symbols:category-outline-rounded",
                                    label="По категориям",
                                    count=category_count,
                                ),
                                value="categories",
                            ),
                        ]
                    ),

                    dmc.TabsPanel(
                        value="regions",
                        pt="md",
                        children=[
                            _panel_header(
                                title="Распределение по регионам",
                                subtitle=(
                                    "На складе + в пути. Справа показаны "
                                    "общий объём и доля региона."
                                ),
                                insight=(
                                    "Высокая доля товара в пути помогает быстро "
                                    "увидеть регионы с незавершённым пополнением."
                                ),
                            ),
                            dcc.Graph(
                                id=STOCK_REGION_CHART_ID,
                                figure=build_regions_distribution_chart(
                                    regions
                                ),
                                config={
                                    **GRAPH_CONFIG,
                                    "toImageButtonOptions": {
                                        **GRAPH_CONFIG[
                                            "toImageButtonOptions"
                                        ],
                                        "filename": (
                                            "stock_distribution_regions"
                                        ),
                                    },
                                },
                            ),
                        ],
                    ),

                    dmc.TabsPanel(
                        value="brands",
                        pt="md",
                        children=[
                            _panel_header(
                                title="Концентрация запасов по брендам",
                                subtitle=(
                                    "Столбики показывают остаток, линия — "
                                    "накопленную долю Top-брендов."
                                ),
                                insight=(
                                    f"Top-5 брендов формируют "
                                    f"{top_5_brand_share:.1f}% "
                                    f"физического остатка."
                                ),
                            ),
                            dcc.Graph(
                                id=STOCK_BRAND_CHART_ID,
                                figure=build_pareto_chart(
                                    brands,
                                    entity_label="Бренд",
                                    top_n=20,
                                ),
                                config={
                                    **GRAPH_CONFIG,
                                    "toImageButtonOptions": {
                                        **GRAPH_CONFIG[
                                            "toImageButtonOptions"
                                        ],
                                        "filename": (
                                            "stock_distribution_brands"
                                        ),
                                    },
                                },
                            ),
                        ],
                    ),

                    dmc.TabsPanel(
                        value="categories",
                        pt="md",
                        children=[
                            _panel_header(
                                title="Крупнейшие товарные категории",
                                subtitle=(
                                    "Объём, доля в общем остатке и количество "
                                    "складов присутствия."
                                ),
                                insight=(
                                    f"Top-5 категорий формируют "
                                    f"{top_5_category_share:.1f}% "
                                    f"физического остатка."
                                ),
                            ),
                            dcc.Graph(
                                id=STOCK_CATEGORY_CHART_ID,
                                figure=build_concentration_chart(
                                    categories,
                                    entity_label="Категория",
                                    top_n=16,
                                ),
                                config={
                                    **GRAPH_CONFIG,
                                    "toImageButtonOptions": {
                                        **GRAPH_CONFIG[
                                            "toImageButtonOptions"
                                        ],
                                        "filename": (
                                            "stock_distribution_categories"
                                        ),
                                    },
                                },
                            ),
                        ],
                    ),
                ],
            ),
        ],
    )
