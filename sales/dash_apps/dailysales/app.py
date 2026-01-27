from django_plotly_dash import DjangoDash
from .mainwindow import MainWindow
from utils.dash_components.common import THEME
from dash_mantine_components import MantineProvider, Container
from dash import html, dcc, Input, Output
import urllib.parse

scripts = [
    "https://cdnjs.cloudflare.com/ajax/libs/dayjs/1.10.8/dayjs.min.js",
    "https://cdnjs.cloudflare.com/ajax/libs/dayjs/1.10.8/locale/ru.min.js",
    "/static/js/dashapps.js"
]
styles = [
    "/static/fonts/glyphs.css",
    "/static/css/dashapps.css",
    "/static/css/dash/clssic_tables.css"
]

app = DjangoDash(
    "dailysales_app",
    external_scripts=scripts,
    external_stylesheets=styles,
    suppress_callback_exceptions=True,
)

app.layout = MantineProvider(
    forceColorScheme="light",
    theme=THEME,
    withCssVariables=True,
    withGlobalClasses=True,
    children=[
        dcc.Location(id="url"),           # триггер на загрузку
        Container(id="page",fluid=True),              # сюда отрисуем окно
    ],
)

@app.callback(
    Output("page", "children"),
    Input("url", "search"),
)
def update_from_url(search):
    if not search:
        return "NOT FOUND"

    params = urllib.parse.parse_qs(search.lstrip("?"))
    object_id = params.get("object_id", [None])[0]

    if not object_id:
        return "NOT FOUND"

    content = MainWindow(object_id)

    return content.layout()

