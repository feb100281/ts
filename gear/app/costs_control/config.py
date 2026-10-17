# gear/app/costs_control/config.py
from __future__ import annotations


APP_NAME = "costs_control_app"
APP_TITLE = "Контроль закупочных цен"

DEFAULT_COST_TYPE = "Бухгалтерская"

COST_TYPES = [
    {
        "label": "Бухгалтерская",
        "value": "Бухгалтерская",
    },
    {
        "label": "Управленческая",
        "value": "Управленческая",
    },
]

CV_RANK_ORDER = [
    "0. Одна цена",
    "1. До 25%",
    "2. От 25% до 50%",
    "3. От 50% до 75%",
    "4. 75% и выше",
]

CV_RANK_OPTIONS = [
    {
        "label": item,
        "value": item,
    }
    for item in CV_RANK_ORDER
]

CRITICAL_CV_LIMIT = 75.0
DEFAULT_MEDIAN_DEVIATION_LIMIT = 10.0

PRICE_ANALYSIS_FOLDER_PREFIX = "cost_price_analysis"
PRICE_ANALYSIS_EXCEL_PREFIX = "cost_price_analysis"

PAGE_SIZE = 50

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
    "gray": "#6B7280",
    "light_gray": "#F6F7F8",
    "border": "#D9DEE2",
    "white": "#FFFFFF",
    "text": "#111827",
    "muted": "#6B7280",
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
}