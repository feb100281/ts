import dash_mantine_components as dmc
import dash_ag_grid as dag
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from dash import Input, Output, html, callback, no_update, dcc, State
from .grids import grid_date,grid_item


class MainWindow:
    def __init__(self):        
        self.ag_container_id = 'ag_container'
        self.date_picker_id = 'date-picker'
        self.summary_tab_id = 'summary-tab' 
        self.dates_storage_id = 'dates-storage-id'
        
        self.tabs_conteiner = dmc.Container(
            [
                dmc.Tabs(
                    [
                        dmc.TabsList(
                            [
                                dmc.TabsTab("Summary", value="1"),
                                dmc.TabsTab("По датам", value="2"),
                                dmc.TabsTab("По номенклатурам", value="3"),
                            ]
                        ),
                    ],
                    id=self.summary_tab_id,
                    value="1",
                ),
                dcc.Loading(
                    dmc.Container(
                        id=self.ag_container_id,
                        fluid=True,
                    ),
                    type="graph",
                )
                
                # dmc.Container(id=self.ag_container_id,fluid=True),
            ],
            fluid=True
        )        
        
        today = date.today()

        dpicker = dmc.DatePickerInput(
            type="range",
            allowSingleDateInRange=True,
            label="Выбор периода",
            valueFormat="dd DD, MMMM YYYY",
            placeholder="Select date",
            id = self.date_picker_id,
            minDate=date(2024,1,1),
            w=500,
            presets=[
                {
                    "value": [
                        (today - timedelta(days=2)).isoformat(),
                        today.isoformat(),
                    ],
                    "label": "Последние два дня",
                },
                {
                    "value": [
                        (
                            today
                            - timedelta(days=today.weekday() + 7)
                        ).isoformat(),
                        (
                            today
                            - timedelta(days=today.weekday() + 1)
                        ).isoformat(),
                    ],
                    "label": "Предыдущая неделя",
                },
                {
                    "value": [
                        today.replace(day=1).isoformat(),
                        today.isoformat(),
                    ],
                    "label": "Текущий месяц",
                },
                {
                    "value": [
                        (today - relativedelta(months=1)).replace(day=1).isoformat(),
                        (today.replace(day=1) - timedelta(days=1)).isoformat(),
                    ],
                    "label": "Предыдущий месяц",
                },
                {
                    "value": [
                        (
                            (
                                today.replace(
                                    month=((today.month - 1) // 3) * 3 + 1,
                                    day=1,
                                )
                                - relativedelta(months=3)
                            )
                        ).isoformat(),

                        (
                            today.replace(
                                month=((today.month - 1) // 3) * 3 + 1,
                                day=1,
                            )
                            - timedelta(days=1)
                        ).isoformat(),
                    ],
                    "label": "Предыдущий квартал",
                },
                {
                    "value": [
                        date(today.year - 1, 1, 1).isoformat(),
                        date(today.year - 1, 12, 31).isoformat(),
                    ],
                    "label": "Прошлый год",
                },
            ],
            maw=320
        )
        self.date_picker = dmc.DatesProvider(
            children=dpicker,
            settings={
                "locale": "ru",
                "firstDayOfWeek": 1,
                "weekendDays": [0, 6],
            }
        )
         
    def layout(self):
        return dmc.Container(
            [
                dmc.Title("Анализ списаний".upper(),order=2),
                dmc.Space(h=10),
                dmc.Divider(size='xs'),
                dmc.Group(
                    [
                        self.date_picker
                    ]
                    ),
                dmc.Space(h=10),
                dmc.Divider(size='xs'),                
                self.tabs_conteiner,
                dcc.Store(id=self.dates_storage_id)
                
            ],
            fluid=True
        )
    
    def registered_callbacks(self,app):
        @app.callback(
            Output(self.ag_container_id,'children'),
            Output(self.dates_storage_id,'data'),
            Input(self.summary_tab_id,'value'),
            Input(self.date_picker_id,'value'),
            State(self.dates_storage_id,'data')            
        )
        def render_dag(val,period,store_period):
            if not period and not store_period:
                start = date(2024,1,1)
                end = date.today()
            else:
                start = period[0] if period else store_period[0]
                end = period[1] if period else store_period[1]            
            store = [start,end,]
            if val == '2':
               return grid_date(start,end),store
            if val == '3':
               return  grid_item(start,end),store
            else:
                return "Not ready",store
        
        

