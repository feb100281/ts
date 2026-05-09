from django_plotly_dash import DjangoDash
from dash import html, dcc, Input, Output
import dash_mantine_components as dmc
import urllib.parse
from .upd_form import UpdForm
import dash_mantine_components as dmc
from .modals import SizeModal

scripts = [
    "https://cdnjs.cloudflare.com/ajax/libs/dayjs/1.10.8/dayjs.min.js",
    "https://cdnjs.cloudflare.com/ajax/libs/dayjs/1.10.8/locale/ru.min.js",
    "/static/dash_ag_grid/dash_ag_grid.min.js",
    # "/static/js/dashapps.js"

]
    

styles = [
    # "/static/fonts/glyphs.css",
    # "/static/css/dash/clssic_tables.css",
    # "/static/css/dash/corporate_sty.css",
    "/static/css/dash/aggrid_compact.css",
]

app = DjangoDash(
    "cards_app",
    external_scripts=scripts,
    external_stylesheets=styles,
    suppress_callback_exceptions=True,    
)
sizemodal = SizeModal()
sizemodal.registered_callbacks(app)

app.layout = dmc.MantineProvider(   
    withCssVariables=True,
    withGlobalClasses=True,
    children=[
        dcc.Location(id="url"),           # триггер на загрузку не пройдет
        dmc.Container(id="page",fluid=True),    
        dcc.Store(id='id_row_store',storage_type='local'),
        dcc.Store(id='nm_id_store',storage_type='local'),
        dcc.Store(id='chrt_id_store',storage_type='local')
        
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
