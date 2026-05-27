from django_plotly_dash import DjangoDash
from dash import html, dcc, Input, Output
import dash_mantine_components as dmc
import urllib.parse

from .builder import ReportBuilder


scripts = [
    "https://cdnjs.cloudflare.com/ajax/libs/dayjs/1.10.8/dayjs.min.js",
    "https://cdnjs.cloudflare.com/ajax/libs/dayjs/1.10.8/locale/ru.min.js",
    "/static/js/dmc.js",
]


app = DjangoDash(
    "rpt_app",
    external_scripts=scripts,
    suppress_callback_exceptions=True,
)


app.layout = dmc.MantineProvider(
    withCssVariables=True,
    withGlobalClasses=True,
    children=[

        dcc.Location(
            id="url",
            refresh=False,
        ),

        html.Div(
            id="page"
        ),
    ],
)

@app.callback(
    Output("page", "children"),
    Input("url", "search"),
)
def update_from_url(search):

    if not search:
        return "NOT FOUND"

    params = urllib.parse.parse_qs(
        search.lstrip("?")
    )

    object_id = params.get(
        "object_id",
        [None]
    )[0]

    if not object_id:
        return "NOT FOUND"

    ctx = ReportBuilder(object_id)

    return ctx.layout()