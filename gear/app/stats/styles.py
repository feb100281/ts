# gear/app/stats/styles.py
from __future__ import annotations

from .config import COLORS


PAGE_STYLE = {
    "backgroundColor": "#F8F9FA",
    "minHeight": "100vh",
    "padding": "18px 22px 28px",
}


HEADER_STYLE = {
    "backgroundColor": COLORS[
        "white"
    ],
    "border": (
        f"1px solid "
        f"{COLORS['border']}"
    ),
    "padding": "14px 16px",
}


PANEL_STYLE = {
    "backgroundColor": COLORS[
        "white"
    ],
    "border": (
        f"1px solid "
        f"{COLORS['border']}"
    ),
    "padding": "14px",
    "minWidth": 0,
}


FILTER_PANEL_STYLE = {
    **PANEL_STYLE,
    "display": "grid",
    "gridTemplateColumns": (
        "minmax(300px, 1.4fr) "
        "minmax(180px, 0.7fr)"
    ),
    "gap": "12px",
    "alignItems": "end",
}


KPI_GRID_STYLE = {
    "display": "grid",
    "gridTemplateColumns": (
        "repeat("
        "4, "
        "minmax(180px, 1fr)"
        ")"
    ),
    "gap": "10px",
}


CHART_GRID_STYLE = {
    "display": "grid",
    "gridTemplateColumns": (
        "repeat("
        "2, "
        "minmax(0, 1fr)"
        ")"
    ),
    "gap": "14px",
}


FULL_WIDTH_STYLE = {
    "marginTop": "14px",
}