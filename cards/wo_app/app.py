# cards/wo_app/app.py
from django_plotly_dash import DjangoDash
from dash import html, dcc, Input, Output, no_update
import dash_mantine_components as dmc
from .main_window import MainWindow
from django.templatetags.static import static

scripts = [
    # static("js/ag-grid-enterprise.min.js"),
   
    "https://cdnjs.cloudflare.com/ajax/libs/dayjs/1.10.8/dayjs.min.js",
    "https://cdnjs.cloudflare.com/ajax/libs/dayjs/1.10.8/locale/ru.min.js",
    # "/static/dash_ag_grid/dash_ag_grid.min.js",
    # "https://cdn.jsdelivr.net/npm/ag-grid-enterprise@32.3.4/dist/ag-grid-enterprise.min.js",
    "/static/js/dashapps.js",
]

styles = [
    "/static/css/dash/aggrid_compact.css",
]

app = DjangoDash(
    "wo_app",
    external_scripts=scripts,
    external_stylesheets=styles,
    suppress_callback_exceptions=True,
)

MW = MainWindow()

MW.registered_callbacks(app)

app.layout = dmc.MantineProvider(
    withCssVariables=True,
    withGlobalClasses=True,
    children=[
        
        MW.layout()

        
    ],
)

