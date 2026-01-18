from django_plotly_dash import DjangoDash
from dash import Input, Output, State, no_update

import dash_mantine_components as dmc
import locale
from datetime import datetime

# from asgiref.sync import sync_to_async
# import asyncio

locale.setlocale(locale.LC_TIME, "ru_RU.UTF-8")
TODAY = datetime.today()
TODAY_STR = TODAY.strftime("%Y-%m-%d")

scripts = [
    "https://cdnjs.cloudflare.com/ajax/libs/dayjs/1.10.8/dayjs.min.js",  # dayjs
    "https://cdnjs.cloudflare.com/ajax/libs/dayjs/1.10.8/locale/ru.min.js",  # russian locale
    "/static/js/dmc.js",
]


def get_all_dates():
    # просто синхронная обёртка над ORM-вызовом
    from macro.models import CalendarExceptions

    return {
        d["date"].isoformat(): d["is_working_day"]
        for d in CalendarExceptions.objects.values("date", "is_working_day")
    }


title = dmc.Title("Производственный календарь", order=1, c="blue")
tip = dmc.Text("Пометьте рабочие выходные или нерабочие будни соответсвенно")


make_idle = dmc.Button(
    children="Сделать выходным",
    id="btn_idle",
    disabled=True,
    variant="outline",
    color="red",
)
make_busy = dmc.Button(
    children="Сделать рабочим",
    id="btn_busy",
    disabled=True,
    variant="outline",
    color="dark",
)

main_conteiner = dmc.Container(
    children=[
        title,
        tip,
        dmc.Space(h=30),
        dmc.Center(
            dmc.DatesProvider(
                children=[
                    dmc.DatePicker(
                        id="date-picker",
                        allowDeselect=True,
                        getDayProps={
                            "function": "highlightExceptions",
                            # options будут обновляться через async колбэк
                            "options": {"exceptions": {}},
                        },
                    ),
                ],
                id="datebox",
                settings={"locale": "ru"},
            ),
        ),
        dmc.Space(h=30),
        dmc.Center(dmc.Group(children=[make_idle, make_busy])),
        dmc.Space(h=50),
        dmc.Text("Выбранная дата:", id="date-picker-out-allow-deselect"),
    ],
    fluid=True,
)


app = DjangoDash("CalApp", external_scripts=scripts)

app.layout = dmc.MantineProvider(id="mantine-provider", children=[main_conteiner])


@app.callback(
    Output("date-picker", "getDayProps"),
    Input("date-picker", "id"),  # просто триггер при старте
)
def load_exceptions(_):
    return {
        "function": "highlightExceptions",
        "options": {"exceptions": get_all_dates()},
    }


@app.callback(
    Output("btn_idle", "disabled"),
    Output("btn_busy", "disabled"),
    Input("date-picker", "value"),
    prevent_initial_call=True,
)
def enable_buttons(value, **kwargs):

    if value:
        return False, False
    else:
        return True, True


@app.callback(
    Output("datebox", "children"),
    Input("btn_idle", "n_clicks"),
    Input("btn_busy", "n_clicks"),
    State("date-picker", "value"),
    prevent_initial_call=True,
)
def update_exceptions(n1, n2, value):
    
    if not value:
        return no_update

    # Определяем, какая кнопка нажата
    button_id = None
    if n1 and (not n2 or n1 > n2):
        button_id = "btn_idle"
    elif n2 and (not n1 or n2 > n1):
        button_id = "btn_busy"

    if not button_id:
        return no_update
    from macro.models import CalendarExceptions
    from datetime import datetime

    date_obj = datetime.strptime(value, "%Y-%m-%d").date()

    if button_id == "btn_idle":
        CalendarExceptions.objects.update_or_create(
            date=date_obj, defaults={"is_working_day": False}
        )
    elif button_id == "btn_busy":
        CalendarExceptions.objects.update_or_create(
            date=date_obj, defaults={"is_working_day": True}
        )

    return [
        dmc.DatePicker(
            id="date-picker",
            allowDeselect=True,
            getDayProps={
                "function": "highlightExceptions",
                "options": {"exceptions": get_all_dates()},
            },
            defaultDate=value,
        )
    ]
