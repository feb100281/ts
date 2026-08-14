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
