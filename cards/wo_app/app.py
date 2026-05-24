# cards/wo_app/app.py
from django_plotly_dash import DjangoDash
from dash import html, dcc, Input, Output, no_update
import dash_mantine_components as dmc


scripts = [
    "https://cdnjs.cloudflare.com/ajax/libs/dayjs/1.10.8/dayjs.min.js",
    "https://cdnjs.cloudflare.com/ajax/libs/dayjs/1.10.8/locale/ru.min.js",
    "/static/dash_ag_grid/dash_ag_grid.min.js",
    "/static/js/dashapps.js",
]

styles = [
    "/static/css/dash/aggrid_compact.css",
]

app = DjangoDash(
    "cards_app",
    external_scripts=scripts,
    external_stylesheets=styles,
    suppress_callback_exceptions=True,
)


