from .data import get_last_update
import dash_mantine_components as dmc
from dash_iconify import DashIconify
from dash import dcc, html, Input, Output, State, no_update, MATCH, ALL
import pandas as pd
from .filters import WbFilters
import locale

locale.setlocale(locale.LC_ALL, "ru_RU.UTF-8")
from .grids import grid_date, day_details
from ..misc.baners import in_construction_banner
from datetime import date


FILTERS = WbFilters()


def chip_maker(row):

    str_dt = row["date_from"]
    dt = pd.to_datetime(str_dt)

    label = dt.strftime("%d.%m.%Y")
    value = dt.strftime("%Y-%m-%d")

    return dmc.Chip(
        label,
        value=value,
        variant="light",
        color="blue",
        size="xs",
        radius="xs",
        checked=False,
    )


class MainWindow:
    def __init__(self):
        self.last_update = pd.to_datetime(get_last_update())
        self.summary_tab_id = "summary_tab_id"
        self.ag_container_id = "ag_container_id"
        self.selected_dates_chips_id = "selected_dates_chips_id"
        self.details_container_id = "details_container_id"

        self.tabs_bar = dmc.Grid(
            [
                dmc.GridCol(
                    [
                        dmc.Group(
                            [
                                dmc.ChipGroup(
                                    [
                                        dmc.Chip(
                                            "Статистика",
                                            value="1",
                                            variant="filled",
                                            color="orange",
                                            size="xs",
                                            radius="xs",
                                            checked=False,
                                        ),
                                        dmc.Chip(
                                            "Данные",
                                            value="2",
                                            variant="filled",
                                            color="orange",
                                            size="xs",
                                            radius="xs",
                                            checked=True,
                                        ),
                                    ],
                                    multiple=False,
                                    deselectable=False,
                                    value="2",
                                    id=self.summary_tab_id,
                                )
                            ],
                            justify="left",
                            gap=0,
                        )
                    ],
                    span=3,
                ),
                dmc.GridCol(
                    [
                        dmc.Group(
                            [
                                dmc.ChipGroup(
                                    children=[],
                                    multiple=False,
                                    deselectable=True,
                                    id=self.selected_dates_chips_id,
                                )
                            ],
                            justify="right",
                            gap=0,
                        )
                    ],
                    span=9,
                ),
            ]
        )

        self.content_container = dcc.Loading(
            dmc.Container(
                id=self.ag_container_id,
                fluid=True,
                style={"display": "block"},
            ),
            type="graph",
        )

        self.details_container = dcc.Loading(
            dmc.Container(
                id=self.details_container_id,
                fluid=True,
                style={"display": "none"},
            ),
            type="graph",
        )

    def layout(self):
        return dmc.Container(
            [
                dmc.Title("Продажи за период", order=2),
                dmc.Divider(
                    size="xs",
                    label=f"Дата обновления: {self.last_update.strftime('%d %B %Y')}",
                ),
                dmc.Space(h=20),
                dmc.Group(
                    [
                        FILTERS.get_date_filter(),
                        FILTERS.get_brand_filter(width=250),
                        FILTERS.get_cat_filter(width=250),
                        FILTERS.get_gender_filter(width=250),
                    ]
                ),
                dmc.Space(h=20),
                dmc.Divider(size="xs"),
                dmc.Space(h=20),
                self.tabs_bar,
                dmc.Divider(size="xs"),
                dmc.Space(h=20),
                self.content_container,
                self.details_container,
            ],
            fluid=True,
        )

    def register_callbacks(self, app):
        @app.callback(
            Output(self.ag_container_id, "children"),
            Input(self.summary_tab_id, "value"),
            Input(FILTERS.date_picker_id, "value"),
            Input(FILTERS.cat_multy_id, "value"),
            Input(FILTERS.brand_multy_id, "value"),
            Input(FILTERS.gender_multy_id, "value"),
        )
        def regnder_tab(tab_value, date_range, cat_list, brand_list, gender_list):
            if date_range:
                start = date_range[0]
                end = date_range[1]
            else:
                start = date(2024, 1, 1)
                end = date.today()

            if tab_value == "1":
                return in_construction_banner()
            elif tab_value == "2":
                
                return [
                    dmc.Group(
                        [
                            dmc.Button(
                                "Excel",
                                leftSection=DashIconify(icon="selfhst:microsoft-excel"),
                                variant="outline",
                                color="#5c7cfa",
                                size="xs",
                                radius="xs",
                                id = {"type":"main-dnl","index":'xls'}
                            ),
                            dmc.Button(
                                "CSV",
                                leftSection=DashIconify(icon="iwwa:file-csv"),
                                variant="outline",
                                color="#5c7cfa",
                                size="xs",
                                radius="xs",
                                id = {"type":"main-dnl","index":'csv'}
                            )
                            
                        ],
                        gap=0,
                        justify='right'
                        ),
                    grid_date(start, end, cat_list, brand_list, gender_list)
                ]
            

        @app.callback(
            Output(self.selected_dates_chips_id, "children"),
            Input({"type": "dates_grid", "index": "1"}, "selectedRows"),
            prevent_initial_call=True,
        )
        def make_chip(rows):
            if not rows:
                return []

            chips = []
            for item in rows:
                chips.append(chip_maker(item))
            return chips

        @app.callback(
            Output(self.ag_container_id, "style"),
            Output(self.details_container_id, "style"),
            Output(self.details_container_id, "children"),
            Input(self.selected_dates_chips_id, "value"),
            State(FILTERS.cat_multy_id, "value"),
            State(FILTERS.brand_multy_id, "value"),
            State(FILTERS.gender_multy_id, "value"),
            allow_duplicate=True,
            prevent_initial_call=True,
        )
        def display_details(date_value, cat, brand, gender):

            if not date_value:
                return ({"display": "block"}, {"display": "none"}, "")

            return (
                {"display": "none"},
                {"display": "block"},
                [
                    dmc.Group(
                        [
                            dmc.ActionIcon(
                                children=DashIconify(
                                    icon="catppuccin:ms-excel", width=18, height=18
                                ),
                                variant="outline",
                                id={"type": "xls-dnl", "index": date_value},
                            ),
                            dmc.ActionIcon(
                                children=DashIconify(
                                    icon="catppuccin:csv", width=18, height=18
                                ),
                                variant="outline",
                                id={"type": "csv-dnl", "index": date_value},
                            ),
                        ],
                        justify="right",
                        gap=0,
                    ),
                    day_details(date_value, cat, brand, gender),
                ],
            )

        ## Грузим дневные данные csv
        @app.callback(
            Output({"type": "dates_grid", "index": "2"}, "exportDataAsCsv"),
            Input({"type": "csv-dnl", "index": ALL}, "n_clicks"),
            prevent_initial_call=True,
        )
        def export_csv(n_clicks):
            if n_clicks:
                return True
            return False
        
        ## Грузим основную грид csv
        @app.callback(
            Output({"type": "dates_grid", "index": "1"}, "exportDataAsCsv"),
            Input({"type":"main-dnl","index":'csv'}, "n_clicks"),
            prevent_initial_call=True,
        )
        def export_csv(n_clicks):
            if n_clicks:
                return True
            return False
        
        ## Грузим дневные данные xls - Input({"type": "xls-dnl", "index": ALL}, "n_clicks"), <== такой инпут
        ## Грузим основную грид csv - Input({"type":"main-dnl","index":'чды'}, "n_clicks"), <== здесь так
        
        
        
        
