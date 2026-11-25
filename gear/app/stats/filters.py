# gear/app/stats/filters.py
from __future__ import annotations

from datetime import date, timedelta

import dash_mantine_components as dmc

from .config import (
    AGGREGATION_OPTIONS,
    DEFAULT_AGGREGATION,
)
from .data import get_stats_min_date
from .ids import (
    AGGREGATION_FILTER_ID,
    DATE_FILTER_ID,
)
from .styles import (
    FILTER_PANEL_STYLE,
)


def get_default_date_range() -> list[str]:
    """
    Период по умолчанию:
    весь доступный период от минимальной даты до сегодня.
    """
    start_date = get_stats_min_date()
    end_date = date.today()

    return [
        start_date.isoformat(),
        end_date.isoformat(),
    ]


def get_date_presets() -> list[dict]:
    """
    Быстрые пресеты для выбора периода анализа.
    """
    today = date.today()
    min_date = get_stats_min_date()

    # С начала текущего года
    year_start = date(
        today.year,
        1,
        1,
    )

    # С начала текущего квартала
    quarter_start_month = (
        ((today.month - 1) // 3) * 3 + 1
    )

    quarter_start = date(
        today.year,
        quarter_start_month,
        1,
    )

    # Прошлый месяц
    current_month_start = date(
        today.year,
        today.month,
        1,
    )

    previous_month_end = (
        current_month_start
        - timedelta(days=1)
    )

    previous_month_start = date(
        previous_month_end.year,
        previous_month_end.month,
        1,
    )

    return [
    {
        "label": "Текущий месяц",
        "value": [
            current_month_start.isoformat(),
            today.isoformat(),
        ],
    },
    {
        "label": "Прошлый месяц",
        "value": [
            previous_month_start.isoformat(),
            previous_month_end.isoformat(),
        ],
    },
    {
        "label": "С начала квартала",
        "value": [
            quarter_start.isoformat(),
            today.isoformat(),
        ],
    },
    {
        "label": "С начала года",
        "value": [
            year_start.isoformat(),
            today.isoformat(),
        ],
    },
    {
        "label": "Весь период",
        "value": [
            min_date.isoformat(),
            today.isoformat(),
        ],
    },
]

def build_filter_panel():
    default_dates = get_default_date_range()
    date_presets = get_date_presets()

    return dmc.Paper(
        radius=0,
        style=FILTER_PANEL_STYLE,
        children=[
            dmc.DatePickerInput(
                id=DATE_FILTER_ID,
                label="Период анализа",
                description="Выберите диапазон дат",
                type="range",
                value=default_dates,
                presets=date_presets,
                valueFormat="DD.MM.YYYY",
                clearable=True,
                radius=0,
            ),

            dmc.Select(
                id=AGGREGATION_FILTER_ID,
                label="Уровень агрегации",
                description=(
                    "Для корреляций и lag-анализа"
                ),
                data=AGGREGATION_OPTIONS,
                value=DEFAULT_AGGREGATION,
                clearable=False,
                allowDeselect=False,
                radius=0,
            ),
        ],
    )