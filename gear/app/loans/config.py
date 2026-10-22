# gear/app/loans/config.py
from __future__ import annotations

APP_NAME = "loans_app"
APP_TITLE = "Займы и кредиты"

PAGE_SIZE = 50

MATURITY_ORDER = [
    "Просрочено",
    "До 30 дней",
    "31–90 дней",
    "91–180 дней",
    "181–365 дней",
    "Более года",
    "Без даты",
]

STATUS_ORDER = [
    "Просрочен",
    "Погашение ≤ 30 дней",
    "Активен",
    "Погашен",
]

STATUS_OPTIONS = [
    {"label": item, "value": item}
    for item in STATUS_ORDER
]

COLORS = {
    "dark": "#22312D",
    "dark_green": "#2F6656",
    "green": "#3C7A67",
    "light_green": "#E7F1ED",
    "very_light_green": "#F3F8F6",
    "orange": "#A15C38",
    "light_orange": "#FBF5F1",
    "red": "#C0392B",
    "light_red": "#FBEFEE",
    "yellow": "#A15C38",
    "light_yellow": "#FBF5F1",
    "blue": "#5B6770",
    "light_blue": "#F7F9F8",
    "gray": "#6B7280",
    "light_gray": "#F7F9F8",
    "border": "#E3E8E6",
    "white": "#FFFFFF",
    "text": "#1F1F1F",
    "muted": "#6B7280",
}

PLOTLY_CONFIG = {
    "displaylogo": False,
    "displayModeBar": False,
    "responsive": True,
    "locale": "ru",
    "scrollZoom": False,
    "modeBarButtonsToRemove": [
        "lasso2d",
        "select2d",
    ],
}

# цвета сторон на графиках
OWE_COLOR = "#A15C38"        # мы должны
OWE_LIGHT = "#DDBFAE"
RECV_COLOR = "#2F6656"       # нам должны
RECV_LIGHT = "#A9CBBF"
