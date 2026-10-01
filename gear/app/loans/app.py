from __future__ import annotations

from django_plotly_dash import DjangoDash

from .callbacks import register_loans_callbacks
from .config import APP_NAME
from .layout import layout


scripts = [
    (
        "https://cdnjs.cloudflare.com/"
        "ajax/libs/dayjs/1.10.8/"
        "dayjs.min.js"
    ),
    (
        "https://cdnjs.cloudflare.com/"
        "ajax/libs/dayjs/1.10.8/"
        "locale/ru.min.js"
    ),
    "/static/js/dashapps.js",
]


styles = [
    "/static/css/dash/aggrid_compact.css",
    "/static/css/dash/compact_tree.css",
]


app = DjangoDash(
    APP_NAME,
    external_scripts=scripts,
    external_stylesheets=styles,
    suppress_callback_exceptions=True,
)


app.layout = layout


register_loans_callbacks(app)
