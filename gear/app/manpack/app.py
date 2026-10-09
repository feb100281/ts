# gear/app/manpack/app.py
from __future__ import annotations

from django_plotly_dash import DjangoDash

from .callbacks import register_manpack_callbacks
from .config import APP_NAME
from .layout import layout
from ..daily_sales.assistant import register_assistant_callbacks

scripts = [
    "https://cdnjs.cloudflare.com/ajax/libs/dayjs/1.10.8/dayjs.min.js",
    "https://cdnjs.cloudflare.com/ajax/libs/dayjs/1.10.8/locale/ru.min.js",
    "/static/js/dashapps.js",
    "/static/js/manpack.js",
]
styles = [
    "/static/css/dash/aggrid_compact.css",
    "/static/css/dash/daily_sales_panel.css",
    "/static/css/dash/assistant.css",
    "/static/css/dash/manpack.css",
]

app = DjangoDash(
    APP_NAME,
    external_scripts=scripts,
    external_stylesheets=styles,
    suppress_callback_exceptions=True,
)
app.layout = layout

register_manpack_callbacks(app)
register_assistant_callbacks(app, profile="finance")
