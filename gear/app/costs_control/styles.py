# gear/app/costs_control/styles.py
from .config import COLORS


PAGE_STYLE = {
    "minHeight": "100vh",
    "backgroundColor": "#F5F7F8",
    "padding": "18px 22px 32px",
    "fontFamily": "Inter, Arial, sans-serif",
}

HEADER_STYLE = {
    "backgroundColor": COLORS["white"],
    "border": f"1px solid {COLORS['border']}",
    "padding": "16px 18px",
}

PANEL_STYLE = {
    "backgroundColor": COLORS["white"],
    "border": f"1px solid {COLORS['border']}",
    "padding": "16px",
}

KPI_GRID_STYLE = {
    "display": "grid",
    "gridTemplateColumns": (
        "repeat(auto-fit, minmax(190px, 1fr))"
    ),
    "gap": "10px",
}

CHART_GRID_STYLE = {
    "display": "grid",
    "gridTemplateColumns": (
        "repeat(auto-fit, minmax(460px, 1fr))"
    ),
    "gap": "12px",
}

FILTER_GRID_STYLE = {
    "display": "grid",
    "gridTemplateColumns": (
        "repeat(auto-fit, minmax(210px, 1fr))"
    ),
    "gap": "12px",
    "alignItems": "end",
}

SECTION_TITLE_STYLE = {
    "fontSize": "15px",
    "fontWeight": 700,
    "color": COLORS["text"],
    "marginBottom": "3px",
}

SECTION_SUBTITLE_STYLE = {
    "fontSize": "12px",
    "color": COLORS["muted"],
}

GRAPH_STYLE = {
    "height": "420px",
}

FULL_GRAPH_STYLE = {
    "height": "560px",
}
