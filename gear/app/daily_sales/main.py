# gear/app/daily_sales/main.py

from datetime import date
import locale

import pandas as pd
import dash_mantine_components as dmc
from dash import dcc, Input, Output, State, ALL
from .methodology import methodology_modal, register_methodology_callbacks

from .data import get_last_update, filters_by_brand
from .filters import WbFilters
from .grids import grid_date, day_details, period_details
from .ui import export_panel_main, export_panel_details
from ..misc.baners import in_construction_banner
from .summary import get_sales_summary
from .stat import StatWindow
from .excel_export import register_excel_export_callbacks, register_revenue_structure_excel_callbacks
from .stocks.export import register_stock_export_callbacks
from .wb_plan_monitor import register_wb_plan_callbacks
from .ai_analysis import register_ai_analysis_callbacks
from .price_analysis import register_price_analysis_export_callbacks
from .stocks.dashboard import (
    StocksDashboard,
    register_stock_dashboard_callbacks,
)

from .pricing_strategy import (
    PricingStrategyDashboard,
    register_pricing_strategy_callbacks,
)

from .daily_brief import (
    daily_brief_controls,
    register_daily_brief_callbacks,
)





try:
    locale.setlocale(locale.LC_ALL, "ru_RU.UTF-8")
except locale.Error:
    pass


FILTERS = WbFilters()
PERIOD_CHIP_VALUE = "__whole_period__"
STOCKS_DASHBOARD = StocksDashboard()
PRICING_STRATEGY_DASHBOARD = PricingStrategyDashboard()



def chip_maker(row):
    dt = pd.to_datetime(row["date_from"])

    return dmc.Chip(
        dt.strftime("%d.%m.%Y"),
        value=dt.strftime("%Y-%m-%d"),
        variant="light",
        color="blue",
        size="xs",
        radius=0,
        checked=False,
    )
    
    
def period_chip_maker(rows):
    dates = sorted(
        pd.to_datetime(row["date_from"])
        for row in rows
    )

    start = dates[0]
    end = dates[-1]

    label = (
        f"За весь период · "
        f"{start.strftime('%d.%m.%Y')}–"
        f"{end.strftime('%d.%m.%Y')}"
    )

    value = (
        f"{PERIOD_CHIP_VALUE}|"
        f"{start.strftime('%Y-%m-%d')}|"
        f"{end.strftime('%Y-%m-%d')}"
    )

    return dmc.Chip(
        label,
        value=value,
        variant="light",
        color="green",
        size="xs",
        radius=0,
        checked=False,
    )

class MainWindow:
    def __init__(self):
        self.last_update = pd.to_datetime(get_last_update())

        self.summary_tab_id = "summary_tab_id"
        self.ag_container_id = "ag_container_id"
        self.selected_dates_chips_id = "selected_dates_chips_id"
        self.details_container_id = "details_container_id"

        

        self.tabs_bar = dmc.Box(
            mb="md",
            children=[
                dmc.Group(
                    justify="flex-start",
                    align="center",
                    mb="xs",
                    children=[
                        dmc.SegmentedControl(
                            id=self.summary_tab_id,
                            value="2",
                           data=[
                                    {
                                        "label": "Статистика",
                                        "value": "1",
                                    },
                                    {
                                        "label": "Данные",
                                        "value": "2",
                                    },
                                    {
                                        "label": "Остатки",
                                        "value": "3",
                                    },
                                    {
                                        "label": "Цены",
                                        "value": "4",
                                    },
                                ],
                            radius=0,
                            size="sm",
                            color="blue",
                        ),
                    ],
                ),

                dmc.Group(
                    justify="flex-end",
                    mt="xs",
                    mb="xs",
                    children=[
                        dmc.ChipGroup(
                            children=[],
                            multiple=False,
                            deselectable=True,
                            id=self.selected_dates_chips_id,
                        )
                    ],
                ),

                dmc.Divider(mt="sm"),
            ],
        )

        # self.content_container = dcc.Loading(
        #     dmc.Container(
        #         id=self.ag_container_id,
        #         fluid=True,
        #         px=0,
        #         style={"display": "block"},
        #     ),
        #     type="graph",
        # )
        
        
        self.content_container = dcc.Loading(
    type="dot",

    delay_show=150,
    delay_hide=100,

    children=dmc.Container(
        id=self.ag_container_id,

        fluid=True,

        px=0,

        style={
            "display": "block",

            # В момент переключения вкладки
            # создаём нормальную область под loader.
            "minHeight": "320px",
        },
    ),
)

        self.details_container = dcc.Loading(
            dmc.Container(
                id=self.details_container_id,
                fluid=True,
                px=0,
                style={"display": "none"},
            ),
            type="graph",
        )
        
        
        

    def layout(self):
        return dmc.Container(
            fluid=True,
            px="xl",
            py="lg",
            style={
                "maxWidth": "100%",
                "backgroundColor": "#ffffff",
            },
            children=[
               dmc.Group(
                        justify="space-between",
                        align="center",
                        mb=6,
                        children=[
                            dmc.Title(
                                "Продажи за период",
                                order=1,
                                fw=800,
                            ),
                            daily_brief_controls(),
                        ],
                    ),

                dmc.Divider(
                    size="xs",
                    mb="md",
                    label=dmc.Text(
                        f"Последнее обновление • {self.last_update.strftime('%d %B %Y')}",
                        size="sm",
                        c="dimmed",
                        fw=500,
                    ),
                    labelPosition="center",
                ),
                
                methodology_modal(),

                FILTERS.get_filters_panel(),

                self.tabs_bar,

                self.content_container,
                self.details_container,
            ],
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
        def render_tab(
            tab_value,
            date_range,
            cat_list,
            brand_list,
            gender_list,
        ):
            if date_range and len(date_range) == 2:
                start = date_range[0]
                end = date_range[1]
            else:
                start = date(2024, 1, 1)
                end = date.today()

            if tab_value == "1":
                stat_container = StatWindow(
                    date_range,
                    cat_list,
                    brand_list,
                    gender_list,
                )
                return stat_container.layout()

            if tab_value == "3":
                return STOCKS_DASHBOARD.layout(
                    report_date=end,
                    cat_list=cat_list,
                    brand_list=brand_list,
                    gender_list=gender_list,
                )
            
            if tab_value == "4":
                return PRICING_STRATEGY_DASHBOARD.layout(
                    report_date=end,
                    cat_list=cat_list,
                    brand_list=brand_list,
                    gender_list=gender_list,
                )

            return [
                get_sales_summary(
                    start,
                    end,
                    cat_list,
                    brand_list,
                    gender_list,
                ),
                export_panel_main(),
                grid_date(
                    start,
                    end,
                    cat_list,
                    brand_list,
                    gender_list,
                ),
            ]
        @app.callback(
            Output(self.selected_dates_chips_id, "children"),
            Input({"type": "dates_grid", "index": "1"}, "selectedRows"),
            prevent_initial_call=True,
        )
        def make_chip(rows):
            if not rows:
                return []

            chips = [
                 period_chip_maker(rows),
            ]

            chips.extend(
                chip_maker(item)
                for item in rows
            )

            return chips
        
        @app.callback(
            Output(self.ag_container_id, "style"),
            Output(self.details_container_id, "style"),
            Output(self.details_container_id, "children"),
            Input(self.selected_dates_chips_id, "value"),
            State(FILTERS.date_picker_id, "value"),
            State(FILTERS.cat_multy_id, "value"),
            State(FILTERS.brand_multy_id, "value"),
            State(FILTERS.gender_multy_id, "value"),
            allow_duplicate=True,
            prevent_initial_call=True,
        )
        def display_details(
            date_value,
            date_range,
            cat,
            brand,
            gender,
        ):
            """
            Переключает основную таблицу и детализацию.

            Обычный чип:
                детализация за один день.

            Зелёный чип:
                детализация за период между выбранными строками.
            """

            # Чип не выбран — возвращаем основную таблицу
            if not date_value:
                return (
                    {"display": "block"},
                    {"display": "none"},
                    [],
                )

            # Детализация за период выбранных строк
            if (
                isinstance(date_value, str)
                and date_value.startswith(f"{PERIOD_CHIP_VALUE}|")
            ):
                value_parts = date_value.split("|", 2)

                if len(value_parts) != 3:
                    return (
                        {"display": "block"},
                        {"display": "none"},
                        [],
                    )

                _, start, end = value_parts

                return (
                    {"display": "none"},
                    {"display": "block"},
                    [
                        export_panel_details(
                            date_value=PERIOD_CHIP_VALUE,
                            start_date=start,
                            end_date=end,
                        ),
                        period_details(
                            start=start,
                            end=end,
                            cat=cat,
                            brand=brand,
                            gender=gender,
                        ),
                    ],
                )

            # Детализация за один выбранный день
            selected_date = pd.to_datetime(
                date_value,
                errors="coerce",
            )

            if pd.isna(selected_date):
                return (
                    {"display": "block"},
                    {"display": "none"},
                    [],
                )

            selected_date = selected_date.strftime("%Y-%m-%d")

            return (
                {"display": "none"},
                {"display": "block"},
                [
                    export_panel_details(
                        date_value=selected_date,
                    ),
                    day_details(
                        date=selected_date,
                        cat=cat,
                        brand=brand,
                        gender=gender,
                    ),
                ],
            )
        
        @app.callback(
            Output({"type": "dates_grid", "index": "2"}, "exportDataAsCsv"),
            Input({"type": "csv-dnl", "index": ALL}, "n_clicks"),
            prevent_initial_call=True,
        )
        def export_day_csv(n_clicks):
            return bool(n_clicks)

        @app.callback(
            Output({"type": "dates_grid", "index": "1"}, "exportDataAsCsv"),
            Input({"type": "main-dnl", "index": "csv"}, "n_clicks"),
            prevent_initial_call=True,
        )
        def export_main_csv(n_clicks):
            return bool(n_clicks)
        
        ###---Для умного фильтра---###
        @app.callback(
            Output(FILTERS.cat_multy_id, "data"),
            Output(FILTERS.gender_multy_id, "data"),
            Output(FILTERS.cat_multy_id, "value"),
            Output(FILTERS.gender_multy_id, "value"),
            Input(FILTERS.brand_multy_id, "value"),
            State(FILTERS.cat_multy_id, "value"),
            State(FILTERS.gender_multy_id, "value"),
            prevent_initial_call=True,
        )
        def update_filters_by_brand(brand_list, cat_value, gender_value):
            opts = filters_by_brand(brand_list)

            cats = opts["cats"]
            genders = opts["genders"]

            valid_cat_values = {x["value"] for x in cats}
            valid_gender_values = {x["value"] for x in genders}

            cat_value = [
                x for x in (cat_value or [])
                if x in valid_cat_values
            ]

            gender_value = [
                x for x in (gender_value or [])
                if x in valid_gender_values
            ]

            return cats, genders, cat_value, gender_value
        ###-------------------###
        
        register_excel_export_callbacks(app,self.selected_dates_chips_id,)
        register_revenue_structure_excel_callbacks(app)
        register_stock_export_callbacks(app)
        register_methodology_callbacks(app)
        register_wb_plan_callbacks(app)
        register_ai_analysis_callbacks(app)
        register_price_analysis_export_callbacks(app)
        register_stock_dashboard_callbacks(app)
        register_daily_brief_callbacks(app)
        register_pricing_strategy_callbacks(app)



