# cards/upd_app/app.py
from django_plotly_dash import DjangoDash
from dash import html, dcc, Input, Output, no_update
import dash_mantine_components as dmc
import urllib.parse

from .upd_form import UpdForm
from .modals import SizeModal
from .callbacks import register_callbacks


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

register_callbacks(app)

size_modal = SizeModal()
size_modal.registered_callbacks(app)

app.layout = dmc.MantineProvider(
    withCssVariables=True,
    withGlobalClasses=True,
    children=[
        dcc.Location(id="url"),
        dmc.Container(id="page", fluid=True),
        html.Div(id="dummy", style={"display": "none"}),
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

    content = UpdForm(object_id)

    return content.layout()