# gear/app/daily_sales/stocks/dashboard_stock/incidents_panel.py

"""Панель происшествий на основной странице dashboard."""

from __future__ import annotations

import pandas as pd
import dash_mantine_components as dmc

from dash import html

from ..dashboard_data import (
    get_warehouse_incident_snapshot,
)

from .warehouse_incidents import (
    WAREHOUSE_INCIDENTS,
)

from .helpers import (
    fmt,
    fmt_money,
)


# =============================================================================
# ЦВЕТА
# =============================================================================

TEXT = "#18352F"
MUTED = "#60746D"

BORDER = "#D6DFDB"

INCIDENT_BORDER = "#E2CACA"
INCIDENT_ACCENT = "#A43E3E"
INCIDENT_BG = "#FFFDFD"

EMPTY_BG = "#F7F9F8"
EMPTY_BORDER = "#DCE4E0"


# =============================================================================
# ИНФОРМАЦИОННЫЙ БЛОК — ФИЗИЧЕСКОГО ОСТАТКА НЕТ
# =============================================================================


def _empty_stock_banner(
    snapshot_label: str,
):
    """
    Показывается вместо KPI, если на дату снимка
    физический остаток на складе равен нулю.
    """

    return dmc.Paper(
        radius=0,
        p="md",
        mt="lg",

        style={
            "background": EMPTY_BG,
            "border": f"1px solid {EMPTY_BORDER}",
        },

        children=[

            dmc.Group(
                gap=10,
                align="flex-start",

                children=[

                    html.Div(
                        style={
                            "width": "4px",
                            "minWidth": "4px",
                            "height": "40px",
                            "background": "#94A39D",
                        },
                    ),

                    html.Div(
                        style={
                            "minWidth": 0,
                        },

                        children=[

                            dmc.Text(
                                "Физический товарный остаток отсутствовал",
                                fw=600,
                                size="sm",
                                c=TEXT,
                            ),

                            dmc.Text(
                                (
                                    f"По данным на {snapshot_label} "
                                    "товар физически на складе отсутствовал. "
                                    "Оценка стоимости товарного остатка "
                                    "для данного происшествия не производится."
                                ),
                                size="xs",
                                c=MUTED,
                                mt=3,
                                style={
                                    "lineHeight": 1.5,
                                },
                            ),
                        ],
                    ),
                ],
            ),
        ],
    )


# =============================================================================
# KPI
# =============================================================================


def _metric(
    label: str,
    value: str,
    *,
    value_color: str = TEXT,
    subvalue: str | None = None,
):
    """
    Унифицированный KPI.

    subvalue используется, например, для:
        15 шт
        4 NM ID
    """

    children = [

        dmc.Text(
            label,
            size="xs",
            c="dimmed",
        ),

        dmc.Text(
            value,
            fw=700,
            size="lg",
            c=value_color,
            mt=1,
        ),
    ]

    if subvalue:
        children.append(
            dmc.Text(
                subvalue,
                size="xs",
                c="dimmed",
                mt=1,
            )
        )

    return html.Div(
        children=children,
    )


# =============================================================================
# КАРТОЧКА ПРОИСШЕСТВИЯ
# =============================================================================


def _incident_card(
    warehouse_name: str,
    incident: dict,
):
    """
    Карточка одного происшествия.

    incident["date"] — фактическая дата происшествия.

    Для финансовой оценки используется исторический
    снимок склада на конец ПРЕДЫДУЩЕГО календарного дня.

    Например:

        происшествие: 22.07.2026
        снимок:       21.07.2026

    В оценку включается только физический остаток quantity.

    Товары в пути не учитываются.
    """

    # =========================================================================
    # Дата происшествия
    # =========================================================================

    incident_date = pd.to_datetime(
        incident["date"]
    )

    event_date = incident_date.strftime(
        "%d.%m.%Y"
    )

    # =========================================================================
    # Требуемая дата снимка
    # =========================================================================

    requested_snapshot_date = (
        incident_date
        - pd.Timedelta(days=1)
    )

    # =========================================================================
    # Исторический снимок
    # =========================================================================

    snapshot = (
        get_warehouse_incident_snapshot(
            warehouse_name=warehouse_name,

            incident_date=(
                requested_snapshot_date.strftime(
                    "%Y-%m-%d"
                )
            ),
        )
    )

    # =========================================================================
    # Фактическая дата снимка
    # =========================================================================

    effective_date = snapshot.get(
        "effective_date"
    )

    snapshot_label = (
        pd.to_datetime(
            effective_date
        ).strftime(
            "%d.%m.%Y"
        )
        if effective_date
        else "нет данных"
    )

    # =========================================================================
    # Основные показатели
    # =========================================================================

    on_hand = float(
        snapshot.get(
            "on_hand",
            0,
        )
        or 0
    )

    has_physical_stock = (
        on_hand > 0
    )

    # =========================================================================
    # Без бухгалтерской себестоимости
    # =========================================================================

    no_accounting_cost_qty = int(
        snapshot.get(
            "no_accounting_cost_qty",
            0,
        )
        or 0
    )

    no_accounting_cost_nm_count = int(
        snapshot.get(
            "no_accounting_cost_nm_count",
            0,
        )
        or 0
    )

    # =========================================================================
    # Без управленческой себестоимости
    # =========================================================================

    no_management_cost_qty = int(
        snapshot.get(
            "no_management_cost_qty",
            0,
        )
        or 0
    )

    no_management_cost_nm_count = int(
        snapshot.get(
            "no_management_cost_nm_count",
            0,
        )
        or 0
    )

    # =========================================================================
    # Нет данных вообще
    # =========================================================================

    no_snapshot_data = (
        not effective_date
    )

    # =========================================================================
    # KPI / информационный блок
    # =========================================================================

    if no_snapshot_data:

        content_block = dmc.Paper(
            radius=0,
            p="md",
            mt="lg",

            style={
                "background": "#FFF8F8",
                "border": f"1px solid {INCIDENT_BORDER}",
            },

            children=[

                dmc.Text(
                    "Нет данных об остатках",
                    fw=600,
                    size="sm",
                    c=INCIDENT_ACCENT,
                ),

                dmc.Text(
                    (
                        "Для даты, предшествующей происшествию, "
                        "не найден снимок товарных остатков. "
                        "Финансовая оценка происшествия не рассчитана."
                    ),
                    size="xs",
                    c=MUTED,
                    mt=3,
                    style={
                        "lineHeight": 1.5,
                    },
                ),
            ],
        )

    elif not has_physical_stock:

        content_block = (
            _empty_stock_banner(
                snapshot_label=snapshot_label,
            )
        )

    else:

        content_block = dmc.SimpleGrid(
            cols={
                "base": 2,
                "sm": 3,
                "lg": 6,
            },

            spacing="lg",

            mt="lg",

            children=[

                # -------------------------------------------------------------
                # Физический остаток
                # -------------------------------------------------------------

                _metric(
                    "Физический остаток",
                    (
                        f"{fmt(
                            snapshot.get(
                                'on_hand',
                                0,
                            )
                        )} шт"
                    ),
                ),

                # -------------------------------------------------------------
                # Товаров
                # -------------------------------------------------------------

                _metric(
                    "Товаров",
                    (
                        f"{fmt(
                            snapshot.get(
                                'nm_count',
                                0,
                            )
                        )} NM ID"
                    ),
                ),

                # -------------------------------------------------------------
                # Бухгалтерская себестоимость
                # -------------------------------------------------------------

                _metric(
                    "Бухгалтерская с/с",
                    (
                        f"{fmt_money(
                            snapshot.get(
                                'accounting_cost',
                                0,
                            )
                        )} ₽"
                    ),
                ),

                # -------------------------------------------------------------
                # Без бухгалтерской себестоимости
                # -------------------------------------------------------------

                _metric(
                    "Без бух. с/с",
                    (
                        f"{fmt(
                            no_accounting_cost_qty
                        )} шт"
                    ),
                    value_color=(
                        INCIDENT_ACCENT
                        if no_accounting_cost_qty > 0
                        else TEXT
                    ),
                    subvalue=(
                        (
                            f"{fmt(
                                no_accounting_cost_nm_count
                            )} NM ID"
                        )
                        if no_accounting_cost_qty > 0
                        else None
                    ),
                ),

                # -------------------------------------------------------------
                # Управленческая себестоимость
                # -------------------------------------------------------------

                _metric(
                    "Управленческая с/с",
                    (
                        f"{fmt_money(
                            snapshot.get(
                                'management_cost',
                                0,
                            )
                        )} ₽"
                    ),
                ),

                # -------------------------------------------------------------
                # Без управленческой себестоимости
                # -------------------------------------------------------------

                _metric(
                    "Без упр. с/с",
                    (
                        f"{fmt(
                            no_management_cost_qty
                        )} шт"
                    ),
                    value_color=(
                        INCIDENT_ACCENT
                        if no_management_cost_qty > 0
                        else TEXT
                    ),
                    subvalue=(
                        (
                            f"{fmt(
                                no_management_cost_nm_count
                            )} NM ID"
                        )
                        if no_management_cost_qty > 0
                        else None
                    ),
                ),
            ],
        )

    # =========================================================================
    # Методологическое примечание
    #
    # Показываем только тогда, когда физический остаток реально был.
    # При нулевом остатке пояснение уже находится внутри отдельного баннера.
    # =========================================================================

    if has_physical_stock:

        footnote_parts = [
            (
                "Оценка рассчитана по товару, физически находившемуся "
                "на складе на конец дня, предшествующего происшествию. "
                "Позиции в пути в расчёт не включены."
            )
        ]

        if (
            no_accounting_cost_qty > 0
            or no_management_cost_qty > 0
        ):
            footnote_parts.append(
                (
                    " Позиции без определённой себестоимости "
                    "не включены в соответствующую стоимостную оценку."
                )
            )

        footnote = dmc.Text(
            "".join(
                footnote_parts
            ),

            size="xs",

            c="dimmed",

            mt="md",

            style={
                "lineHeight": 1.45,
            },
        )

    else:

        footnote = None

    # =========================================================================
    # Карточка
    # =========================================================================

    return dmc.Paper(
        radius=0,
        p="lg",

        style={
            "border": (
                f"1px solid {INCIDENT_BORDER}"
            ),

            "borderLeft": (
                f"4px solid {INCIDENT_ACCENT}"
            ),

            "background": INCIDENT_BG,

            "flexShrink": 0,
        },

        children=[

            # =================================================================
            # HEADER
            # =================================================================

            dmc.Group(
                justify="space-between",

                align="flex-start",

                gap="md",

                children=[

                    # ---------------------------------------------------------
                    # Название склада / событие
                    # ---------------------------------------------------------

                    html.Div(
                        style={
                            "minWidth": 0,
                        },

                        children=[

                            dmc.Group(
                                gap=8,

                                align="center",

                                children=[

                                    dmc.Text(
                                        warehouse_name,

                                        fw=700,

                                        size="md",

                                        c=TEXT,
                                    ),

                                    dmc.Badge(
                                        incident.get(
                                            "status",
                                            "Происшествие",
                                        ),

                                        color="red",

                                        variant="light",

                                        radius=0,
                                    ),
                                ],
                            ),

                            dmc.Text(
                                (
                                    f"{incident.get(
                                        'title',
                                        'Происшествие',
                                    )} · {event_date}"
                                ),

                                size="sm",

                                c=MUTED,

                                mt=2,
                            ),
                        ],
                    ),

                    # ---------------------------------------------------------
                    # Дата остатков
                    # ---------------------------------------------------------

                    dmc.Text(
                        (
                            "Остатки на: "
                            f"{snapshot_label}"
                        ),

                        size="xs",

                        c="dimmed",

                        style={
                            "whiteSpace": "nowrap",
                        },
                    ),
                ],
            ),

            # =================================================================
            # ОПИСАНИЕ
            # =================================================================

            dmc.Text(
                incident.get(
                    "description",
                    "",
                ),

                size="sm",

                c=TEXT,

                mt="md",

                style={
                    "lineHeight": 1.5,
                },
            ),

            # =================================================================
            # KPI ИЛИ БАННЕР
            # =================================================================

            content_block,

            # =================================================================
            # FOOTNOTE
            # =================================================================

            footnote,
        ],
    )


# =============================================================================
# ОСНОВНАЯ ПАНЕЛЬ
# =============================================================================


def build_incidents_panel():
    """
    Формирует блок происшествий на основной странице.

    Особенности:

    - события сортируются от новых к старым;
    - заголовок блока остаётся неподвижным;
    - прокручиваются только карточки событий;
    - при небольшом числе событий scroll не показывается;
    - при большом числе событий dashboard не растягивается вниз.
    """

    # =========================================================================
    # Собираем все события
    # =========================================================================

    events = []

    for warehouse_name, incidents in (
        WAREHOUSE_INCIDENTS.items()
    ):

        for incident in incidents:

            events.append(
                (
                    incident.get(
                        "date",
                        "",
                    ),

                    warehouse_name,

                    incident,
                )
            )

    # =========================================================================
    # Нет происшествий
    # =========================================================================

    if not events:
        return None

    # =========================================================================
    # Новые события сверху
    # =========================================================================

    events.sort(
        key=lambda item: item[0],
        reverse=True,
    )

    # =========================================================================
    # Панель
    # =========================================================================

    return dmc.Paper(
        radius=0,
        p="lg",

        style={
            "border": (
                f"1px solid {BORDER}"
            ),

            "background": "#FFFFFF",
        },

        children=[

            # =================================================================
            # HEADER
            # =================================================================

            dmc.Group(
                justify="space-between",

                align="flex-end",

                gap="md",

                mb="md",

                children=[

                    html.Div(
                        children=[

                            dmc.Text(
                                "Происшествия на складах",

                                fw=700,

                                size="md",

                                c=TEXT,
                            ),

                            dmc.Text(
                                (
                                    "Зафиксированные события и оценка "
                                    "товарного остатка на конец дня, "
                                    "предшествующего происшествию."
                                ),

                                size="xs",

                                c="dimmed",

                                mt=2,
                            ),
                        ],
                    ),

                    dmc.Badge(
                        (
                            f"{len(events)} "
                            f"{_event_word(len(events))}"
                        ),

                        color="red",

                        variant="light",

                        radius=0,
                    ),
                ],
            ),

            # =================================================================
            # SCROLL
            # =================================================================

            html.Div(
                style={
                    "maxHeight": "520px",

                    "overflowY": "auto",

                    "overflowX": "hidden",

                    "paddingRight": "8px",

                    "scrollbarGutter": "stable",

                    "WebkitOverflowScrolling": "touch",
                },

                children=[

                    dmc.Stack(
                        gap="sm",

                        children=[

                            _incident_card(
                                warehouse_name=warehouse_name,
                                incident=incident,
                            )

                            for (
                                _,
                                warehouse_name,
                                incident,
                            )
                            in events
                        ],
                    ),
                ],
            ),
        ],
    )


# =============================================================================
# СКЛОНЕНИЕ "СОБЫТИЕ / СОБЫТИЯ / СОБЫТИЙ"
# =============================================================================


def _event_word(
    count: int,
) -> str:
    """
    1 событие
    2 события
    5 событий
    21 событие
    23 события
    27 событий
    """

    count = abs(
        int(
            count
            or 0
        )
    )

    last_two = (
        count
        % 100
    )

    last_one = (
        count
        % 10
    )

    if (
        11
        <= last_two
        <= 14
    ):
        return "событий"

    if last_one == 1:
        return "событие"

    if last_one in {
        2,
        3,
        4,
    }:
        return "события"

    return "событий"