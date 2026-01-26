from django_plotly_dash import DjangoDash
from .mainwindow import MainWindow
from utils.dash_components.common import THEME
from dash_mantine_components import MantineProvider

scripts = [
    "https://cdnjs.cloudflare.com/ajax/libs/dayjs/1.10.8/dayjs.min.js",
    "https://cdnjs.cloudflare.com/ajax/libs/dayjs/1.10.8/locale/ru.min.js",
    "/Users/pavelustenko/ts/static/js/dashapps.js"
]
styles = [
    "/static/fonts/glyphs.css",
    "/static/css/dashapps.css"
]

app = DjangoDash(
    "dailysales_app",
    external_scripts=scripts,
    external_stylesheets=styles,
    suppress_callback_exceptions=True,
)

window = MainWindow()

app.layout = MantineProvider(    
    forceColorScheme="light",
    theme=THEME,
    withCssVariables=True,
    withGlobalClasses=True,
    children=[
        window.layout(), 
            ]  
)

window.registered_callbacks(app)

