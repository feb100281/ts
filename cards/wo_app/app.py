# cards/wo_app/app.py
from django_plotly_dash import DjangoDash
from dash import html, dcc, Input, Output, no_update
import dash_mantine_components as dmc
from .main_window import MainWindow

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
    "wo_app",
    external_scripts=scripts,
    external_stylesheets=styles,
    suppress_callback_exceptions=True,
)

MW = MainWindow()

app.layout = dmc.MantineProvider(
    withCssVariables=True,
    withGlobalClasses=True,
    children=[
        
        MW.layout()

        # dmc.NotificationContainer(
        #     id="notification-container"
        # ),

        # dcc.Location(id="url"),
        # dmc.Container(id="page", fluid=True),
        # html.Div(id="dummy", style={"display": "none"}),
    ],
)

