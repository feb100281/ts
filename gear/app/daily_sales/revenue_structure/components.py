# gear/app/daily_sales/revenue_structure/components.py

from __future__ import annotations

from datetime import date, datetime

import pandas as pd
import dash_mantine_components as dmc

from dash import dcc
from dash_iconify import DashIconify

from .charts import (
    build_revenue_margin_chart,
    build_profit_donut,
)

from .data import (
    get_revenue_structure,
)

from .grid import (
    build_revenue_grid,
)

from .ids import (
    REVENUE_STRUCTURE_TABS_ID,

    REVENUE_STRUCTURE_BRAND_CHART_ID,
    REVENUE_STRUCTURE_BRAND_DONUT_ID,
    REVENUE_STRUCTURE_BRAND_GRID_ID,

    REVENUE_STRUCTURE_CATEGORY_CHART_ID,
    REVENUE_STRUCTURE_CATEGORY_DONUT_ID,
    REVENUE_STRUCTURE_CATEGORY_GRID_ID,

    REVENUE_STRUCTURE_GENDER_CHART_ID,
    REVENUE_STRUCTURE_GENDER_DONUT_ID,
    REVENUE_STRUCTURE_GENDER_GRID_ID,

    REVENUE_STRUCTURE_BRAND_EXCEL_BTN_ID,
    REVENUE_STRUCTURE_BRAND_EXCEL_DOWNLOAD_ID,

    REVENUE_STRUCTURE_CATEGORY_EXCEL_BTN_ID,
    REVENUE_STRUCTURE_CATEGORY_EXCEL_DOWNLOAD_ID,

    REVENUE_STRUCTURE_GENDER_EXCEL_BTN_ID,
    REVENUE_STRUCTURE_GENDER_EXCEL_DOWNLOAD_ID,
)


# =========================================================
# Plotly config
# =========================================================

PLOTLY_CONFIG = {
    "displaylogo": False,

    "responsive": True,

    "modeBarButtonsToRemove": [
        "lasso2d",
        "select2d",
    ],

    "toImageButtonOptions": {
        "format": "png",

        "filename": (
            "revenue_margin_analysis"
        ),

        "height": 900,

        "width": 1600,

        "scale": 2,
    },
}


# =========================================================
# Форматирование даты
# =========================================================

def format_date(
    value,
) -> str:
    """
    Приводит дату к формату:

    18.07.2026

    Поддерживает:
    - str: 2026-07-18
    - datetime
    - date
    - pandas.Timestamp
    """

    if value is None:
        return "—"

    try:
        parsed = pd.to_datetime(
            value,
            errors="coerce",
        )

        if pd.isna(parsed):
            return "—"

        return parsed.strftime(
            "%d.%m.%Y"
        )

    except Exception:
        return str(value)


def format_period(
    start_date,
    end_date,
) -> str:
    """
    Формат периода:

    13.07.2026 — 18.07.2026
    """

    start_text = format_date(
        start_date
    )

    end_text = format_date(
        end_date
    )

    if (
        start_text == end_text
        and start_text != "—"
    ):
        return start_text

    return (
        f"{start_text} — {end_text}"
    )


# =========================================================
# Форматирование денег
# =========================================================

def format_money(
    value: float,
) -> str:

    value = float(
        value or 0
    )

    abs_value = abs(
        value
    )

    if abs_value >= 1_000_000_000:

        return (
            f"{value / 1_000_000_000:.2f}"
            .replace(
                ".",
                ",",
            )
            + " млрд ₽"
        )

    if abs_value >= 1_000_000:

        return (
            f"{value / 1_000_000:.2f}"
            .replace(
                ".",
                ",",
            )
            + " млн ₽"
        )

    return (
        f"{value:,.2f}"
        .replace(
            ",",
            " ",
        )
        .replace(
            ".",
            ",",
        )
        + " ₽"
    )


def format_pct(
    value: float,
) -> str:

    return (
        f"{float(value or 0):.2f}"
        .replace(
            ".",
            ",",
        )
        + " %"
    )


# =========================================================
# Заголовок блока
# =========================================================

def section_header(
    title: str,
    subtitle: str,
    icon: str,
):

    return dmc.Group(
        justify="space-between",

        align="flex-start",

        mb="md",

        children=[
            dmc.Group(
                gap="sm",

                align="flex-start",

                children=[
                    dmc.ThemeIcon(
                        variant="light",

                        color="blue",

                        radius=0,

                        size=38,

                        children=(
                            DashIconify(
                                icon=icon,

                                width=21,
                            )
                        ),
                    ),

                    dmc.Stack(
                        gap=1,

                        children=[
                            dmc.Text(
                                title,

                                fw=800,

                                size="md",

                                c="#1D2939",
                            ),

                            dmc.Text(
                                subtitle,

                                size="xs",

                                c="dimmed",
                            ),
                        ],
                    ),
                ],
            ),
        ],
    )


# =========================================================
# KPI
# =========================================================

def metric_card(
    title: str,
    value: str,
    subtitle: str,
    icon: str,
):

    return dmc.Paper(
        withBorder=True,

        radius=0,

        p="sm",

        style={
            "height": "100%",
        },

        children=[
            dmc.Group(
                justify="space-between",

                align="flex-start",

                wrap="nowrap",

                children=[
                    dmc.Stack(
                        gap=3,

                        children=[
                            dmc.Text(
                                title,

                                size="xs",

                                fw=700,

                                c="dimmed",
                            ),

                            dmc.Text(
                                value,

                                size="lg",

                                fw=800,

                                c="#1D2939",

                                style={
                                    "fontVariantNumeric": (
                                        "tabular-nums"
                                    ),
                                },
                            ),

                            dmc.Text(
                                subtitle,

                                size="10px",

                                c="#98A2B3",
                            ),
                        ],
                    ),

                    dmc.ThemeIcon(
                        variant="light",

                        color="blue",

                        radius=0,

                        size=34,

                        children=(
                            DashIconify(
                                icon=icon,

                                width=18,
                            )
                        ),
                    ),
                ],
            ),
        ],
    )


# =========================================================
# Контент одного измерения
# =========================================================

def build_dimension_content(
    rows: list[dict],

    dimension_label: str,
    dimension_count_label: str,

    chart_id: str,
    donut_id: str,
    grid_id: str,

    excel_button_id: str,
    excel_download_id: str,

    start_date=None,
    end_date=None,
):

    if not rows:

        return dmc.Alert(
            (
                "По выбранным фильтрам "
                "данных нет."
            ),

            title="Нет данных",

            color="gray",

            variant="light",

            radius=0,
        )

    # =====================================================
    # Выручка
    # =====================================================

    total_revenue = sum(
        float(
            row.get(
                "revenue_vatless"
            )
            or 0
        )
        for row in rows
    )

    # =====================================================
    # Комиссия WB
    # =====================================================

    total_commission = sum(
        float(
            row.get(
                "net_comission"
            )
            or 0
        )
        for row in rows
    )

    commission_pct = (
        -total_commission
        /
        total_revenue
        * 100
        if total_revenue
        else 0
    )

    # =====================================================
    # Себестоимость
    # =====================================================

    total_cogs_book = sum(
        float(
            row.get(
                "cogs_book"
            )
            or 0
        )
        for row in rows
    )

    total_cogs_man = sum(
        float(
            row.get(
                "cogs_man"
            )
            or 0
        )
        for row in rows
    )

    # =====================================================
    # Маржа в рублях
    #
    # ВАЖНО:
    #
    # gross_profit_book / gross_profit_man —
    # исторические названия полей.
    #
    # Фактически здесь:
    #
    # Выручка без НДС
    # - Себестоимость
    # - Комиссия WB
    #
    # Не входят:
    # - маркетинг
    # - логистика
    # - штрафы
    # - прочие расходы WB
    # =====================================================

    total_margin_book = sum(
        float(
            row.get(
                "gross_profit_book"
            )
            or 0
        )
        for row in rows
    )

    total_margin_man = sum(
        float(
            row.get(
                "gross_profit_man"
            )
            or 0
        )
        for row in rows
    )

    # =====================================================
    # Маржинальность %
    # =====================================================

    margin_book_pct = (
        total_margin_book
        /
        total_revenue
        * 100
        if total_revenue
        else 0
    )

    margin_man_pct = (
        total_margin_man
        /
        total_revenue
        * 100
        if total_revenue
        else 0
    )

    # =====================================================
    # Контроль себестоимости
    # =====================================================

    no_book_cost = sum(
        int(
            row.get(
                "no_book_cost"
            )
            or 0
        )
        for row in rows
    )

    no_man_cost = sum(
        int(
            row.get(
                "no_man_cost"
            )
            or 0
        )
        for row in rows
    )

    # =====================================================
    # Контент
    # =====================================================

    return dmc.Stack(
        gap="md",

        children=[
            # =================================================
            # KPI
            # =================================================

            dmc.SimpleGrid(
                cols={
                    "base": 1,
                    "sm": 2,
                    "lg": 5,
                },

                spacing="sm",

                children=[
                    # =========================================
                    # Выручка
                    # =========================================

                    metric_card(
                        "Выручка без НДС",

                        format_money(
                            total_revenue
                        ),

                        (
                            "База для расчёта "
                            "маржинальности"
                        ),

                        (
                            "solar:"
                            "wallet-money-bold-duotone"
                        ),
                    ),

                    # =========================================
                    # Комиссия WB
                    # =========================================

                    metric_card(
                        "Комиссия WB",

                        format_money(
                            total_commission
                        ),

                        (
                            "Доля от выручки "
                            f"{format_pct(commission_pct)}"
                        ),

                        (
                            "solar:"
                            "hand-money-bold-duotone"
                        ),
                    ),

                    # =========================================
                    # Бухгалтерская маржа
                    # =========================================

                    metric_card(
                        "Маржа, бух.",

                        format_money(
                            total_margin_book
                        ),

                        (
                            "Маржинальность "
                            f"{format_pct(margin_book_pct)}"
                        ),

                        (
                            "solar:"
                            "calculator-bold-duotone"
                        ),
                    ),

                    # =========================================
                    # Управленческая маржа
                    # =========================================

                    metric_card(
                        "Маржа, упр.",

                        format_money(
                            total_margin_man
                        ),

                        (
                            "Маржинальность "
                            f"{format_pct(margin_man_pct)}"
                        ),

                        (
                            "solar:"
                            "chart-2-bold-duotone"
                        ),
                    ),

                    # =========================================
                    # Количество
                    # =========================================

                    metric_card(
                        dimension_count_label,

                        (
                            f"{len(rows):,}"
                            .replace(
                                ",",
                                " ",
                            )
                        ),

                        (
                            f"Без с/с: "
                            f"бух. {no_book_cost:,}, "
                            f"упр. {no_man_cost:,}"
                        ).replace(
                            ",",
                            " ",
                        ),

                        (
                            "solar:"
                            "layers-bold-duotone"
                        ),
                    ),
                ],
            ),

            # =================================================
            # Графики
            # =================================================

            dmc.Grid(
                gutter="md",

                children=[
                    # =========================================
                    # Основной график
                    # =========================================

                    dmc.GridCol(
                        span={
                            "base": 12,
                            "lg": 8,
                        },

                        children=(
                            dmc.Paper(
                                withBorder=True,

                                radius=0,

                                p="md",

                                children=[
                                    section_header(
                                        (
                                            "Выручка и "
                                            "маржинальность"
                                        ),

                                        (
                                            "TOP-15 по выручке "
                                            "без НДС. "
                                            "Столбцы — выручка, "
                                            "точки — управленческая "
                                            "маржинальность."
                                        ),

                                        (
                                            "solar:"
                                            "chart-square-bold-duotone"
                                        ),
                                    ),

                                    dcc.Graph(
                                        id=chart_id,

                                        figure=(
                                            build_revenue_margin_chart(
                                                rows=rows,

                                                date_from=(
                                                    start_date
                                                ),

                                                date_to=(
                                                    end_date
                                                ),
                                            )
                                        ),

                                        config=(
                                            PLOTLY_CONFIG
                                        ),

                                        style={
                                            "width": "100%",
                                        },
                                    ),
                                ],
                            )
                        ),
                    ),

                    # =========================================
                    # Donut
                    # =========================================

                    dmc.GridCol(
                        span={
                            "base": 12,
                            "lg": 4,
                        },

                        children=(
                            dmc.Paper(
                                withBorder=True,

                                radius=0,

                                p="md",

                                children=[
                                    section_header(
                                        (
                                            "Структура "
                                            "управленческой маржи"
                                        ),

                                        (
                                            "TOP-8 по "
                                            "положительной "
                                            "управленческой марже."
                                        ),

                                        (
                                            "solar:"
                                            "pie-chart-2-"
                                            "bold-duotone"
                                        ),
                                    ),

                                    dcc.Graph(
                                        id=donut_id,

                                        figure=(
                                            build_profit_donut(
                                                rows=rows,

                                                date_from=(
                                                    start_date
                                                ),

                                                date_to=(
                                                    end_date
                                                ),
                                            )
                                        ),

                                        config=(
                                            PLOTLY_CONFIG
                                        ),

                                        style={
                                            "width": "100%",
                                        },
                                    ),
                                ],
                            )
                        ),
                    ),
                ],
            ),

            # =================================================
            # Таблица
            # =================================================

            dmc.Paper(
                withBorder=True,

                radius=0,

                p="md",

                children=[
                    section_header(
                        (
                            "Детальная "
                            "маржинальность"
                        ),

                        (
                            "Выручка, себестоимость, "
                            "маржа и маржинальность по "
                            f"{dimension_label.lower()}."
                        ),

                        (
                            "solar:"
                            "document-text-"
                            "bold-duotone"
                        ),
                    ),

                    build_revenue_grid(
                        rows=rows,

                        dimension_label=(
                            dimension_label
                        ),

                        grid_id=grid_id,

                        excel_button_id=(
                            excel_button_id
                        ),

                        excel_download_id=(
                            excel_download_id
                        ),
                    ),
                ],
            ),
        ],
    )


# =========================================================
# Главный компонент
# =========================================================

def build_revenue_structure(
    start_date,
    end_date,
    cat=None,
    brand=None,
    gender=None,
):

    # =====================================================
    # Бренды
    # =====================================================

    brand_rows = (
        get_revenue_structure(
            start_date=start_date,

            end_date=end_date,

            dimension="brand",

            cat=cat,

            brand=brand,

            gender=gender,
        )
    )

    # =====================================================
    # Категории
    # =====================================================

    category_rows = (
        get_revenue_structure(
            start_date=start_date,

            end_date=end_date,

            dimension="category",

            cat=cat,

            brand=brand,

            gender=gender,
        )
    )

    # =====================================================
    # Пол
    # =====================================================

    gender_rows = (
        get_revenue_structure(
            start_date=start_date,

            end_date=end_date,

            dimension="gender",

            cat=cat,

            brand=brand,

            gender=gender,
        )
    )

    # =====================================================
    # Красивое отображение периода
    #
    # Было:
    # 2026-07-18 — 2026-07-18
    #
    # Стало:
    # 18.07.2026
    #
    # или:
    # 13.07.2026 — 18.07.2026
    # =====================================================

    period_text = format_period(
        start_date=start_date,
        end_date=end_date,
    )

    return dmc.Stack(
        gap="md",

        children=[
            # =================================================
            # Заголовок
            # =================================================

            dmc.Group(
                justify="space-between",

                align="flex-end",

                children=[
                    dmc.Stack(
                        gap=2,

                        children=[
                            dmc.Title(
                                (
                                    "Доходы и "
                                    "маржинальность"
                                ),

                                order=3,

                                fw=800,
                            ),

                            dmc.Text(
                                (
                                    "Анализ выручки без НДС, "
                                    "бухгалтерской и "
                                    "управленческой "
                                    "себестоимости, маржи "
                                    "и маржинальности."
                                ),

                                size="sm",

                                c="dimmed",
                            ),
                        ],
                    ),

                    # =========================================
                    # Период
                    #
                    # Например:
                    # 13.07.2026 — 18.07.2026
                    # =========================================

                    dmc.Badge(
                        period_text,

                        variant="light",

                        color="blue",

                        radius=0,

                        size="lg",
                    ),
                ],
            ),

            # =================================================
            # Табы
            # =================================================

            dmc.Tabs(
                id=(
                    REVENUE_STRUCTURE_TABS_ID
                ),

                value="brand",

                variant="outline",

                radius=0,

                children=[
                    # =========================================
                    # Шапка табов
                    # =========================================

                    dmc.TabsList(
                        children=[
                            dmc.TabsTab(
                                "По брендам",

                                value="brand",

                                leftSection=(
                                    DashIconify(
                                        icon=(
                                            "solar:"
                                            "tag-bold-duotone"
                                        ),

                                        width=17,
                                    )
                                ),
                            ),

                            dmc.TabsTab(
                                "По категориям",

                                value="category",

                                leftSection=(
                                    DashIconify(
                                        icon=(
                                            "solar:"
                                            "widget-5-"
                                            "bold-duotone"
                                        ),

                                        width=17,
                                    )
                                ),
                            ),

                            dmc.TabsTab(
                                "По полу",

                                value="gender",

                                leftSection=(
                                    DashIconify(
                                        icon=(
                                            "solar:"
                                            "users-group-rounded-"
                                            "bold-duotone"
                                        ),

                                        width=17,
                                    )
                                ),
                            ),
                        ],
                    ),

                    # =========================================
                    # Бренды
                    # =========================================

                    dmc.TabsPanel(
                        value="brand",

                        pt="md",

                        children=(
                            build_dimension_content(
                                rows=brand_rows,

                                dimension_label=(
                                    "Бренд"
                                ),

                                dimension_count_label=(
                                    "Брендов"
                                ),

                                chart_id=(
                                    REVENUE_STRUCTURE_BRAND_CHART_ID
                                ),

                                donut_id=(
                                    REVENUE_STRUCTURE_BRAND_DONUT_ID
                                ),

                                grid_id=(
                                    REVENUE_STRUCTURE_BRAND_GRID_ID
                                ),

                                excel_button_id=(
                                    REVENUE_STRUCTURE_BRAND_EXCEL_BTN_ID
                                ),

                                excel_download_id=(
                                    REVENUE_STRUCTURE_BRAND_EXCEL_DOWNLOAD_ID
                                ),

                                start_date=start_date,

                                end_date=end_date,
                            )
                        ),
                    ),

                    # =========================================
                    # Категории
                    # =========================================

                    dmc.TabsPanel(
                        value="category",

                        pt="md",

                        children=(
                            build_dimension_content(
                                rows=category_rows,

                                dimension_label=(
                                    "Категория"
                                ),

                                dimension_count_label=(
                                    "Категорий"
                                ),

                                chart_id=(
                                    REVENUE_STRUCTURE_CATEGORY_CHART_ID
                                ),

                                donut_id=(
                                    REVENUE_STRUCTURE_CATEGORY_DONUT_ID
                                ),

                                grid_id=(
                                    REVENUE_STRUCTURE_CATEGORY_GRID_ID
                                ),

                                excel_button_id=(
                                    REVENUE_STRUCTURE_CATEGORY_EXCEL_BTN_ID
                                ),

                                excel_download_id=(
                                    REVENUE_STRUCTURE_CATEGORY_EXCEL_DOWNLOAD_ID
                                ),

                                start_date=start_date,

                                end_date=end_date,
                            )
                        ),
                    ),

                    # =========================================
                    # Пол
                    # =========================================

                    dmc.TabsPanel(
                        value="gender",

                        pt="md",

                        children=(
                            build_dimension_content(
                                rows=gender_rows,

                                dimension_label=(
                                    "Пол"
                                ),

                                dimension_count_label=(
                                    "Групп"
                                ),

                                chart_id=(
                                    REVENUE_STRUCTURE_GENDER_CHART_ID
                                ),

                                donut_id=(
                                    REVENUE_STRUCTURE_GENDER_DONUT_ID
                                ),

                                grid_id=(
                                    REVENUE_STRUCTURE_GENDER_GRID_ID
                                ),

                                excel_button_id=(
                                    REVENUE_STRUCTURE_GENDER_EXCEL_BTN_ID
                                ),

                                excel_download_id=(
                                    REVENUE_STRUCTURE_GENDER_EXCEL_DOWNLOAD_ID
                                ),

                                start_date=start_date,

                                end_date=end_date,
                            )
                        ),
                    ),
                ],
            ),
        ],
    )