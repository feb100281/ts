# gear/app/stats/config.py
from __future__ import annotations


APP_NAME = "stats_app"
APP_TITLE = "Статистика и аналитика продаж"


COLORS = {
    "dark": "#22312D",
    "dark_green": "#2F6656",
    "green": "#3C7A67",
    "light_green": "#E7F1ED",
    "very_light_green": "#F3F8F6",

    "orange": "#B45309",
    "light_orange": "#FEF3E7",

    "red": "#A33A3A",
    "light_red": "#FDECEC",

    "yellow": "#9A6700",
    "light_yellow": "#FFF6D8",

    "blue": "#3B6B8F",
    "light_blue": "#EDF4FA",

    "purple": "#7C3AED",
    "light_purple": "#F3EEFF",

    "gray": "#6B7280",
    "light_gray": "#F6F7F8",

    "border": "#D9DEE2",
    "white": "#FFFFFF",
    "text": "#111827",
    "muted": "#6B7280",
}


AGGREGATION_OPTIONS = [
    {
        "label": "По дням",
        "value": "day",
    },
    {
        "label": "По неделям",
        "value": "week",
    },
    {
        "label": "По месяцам",
        "value": "month",
    },
]


DEFAULT_AGGREGATION = "week"


MAX_LAG_PERIODS = 8


ROLLING_WINDOWS = {
    "day": 30,
    "week": 8,
    "month": 4,
}


PLOTLY_CONFIG = {
    "displaylogo": False,
    "responsive": True,
    "locale": "ru",
    "scrollZoom": False,
    "modeBarButtonsToRemove": [
        "lasso2d",
        "select2d",
    ],
    "toImageButtonOptions": {
        "format": "png",
        "filename": "statistics_analysis",
        "height": 1400,
        "width": 2200,
        "scale": 3,
    },
}