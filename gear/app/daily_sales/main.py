from .data import get_last_update
import dash_mantine_components as dmc
from dash_iconify import DashIconify
from dash import dcc, html, Input, Output, State, no_update
import pandas as pd
from .filters import WbFilters
import locale
locale.setlocale(locale.LC_ALL, 'ru_RU.UTF-8') 
from .grids import grid_date
from ..misc.baners import in_construction_banner
from datetime import date

FILTERS = WbFilters()

class MainWindow:
    def __init__(self):
        self.last_update = pd.to_datetime(get_last_update())
        self.summary_tab_id = 'summary_tab_id'
        self.ag_container_id = 'ag_container_id'
        self.tabs_conteiner = dmc.Container(
            [
                dmc.Tabs(
                    [
                        dmc.TabsList(
                            [
                                dmc.TabsTab("Summary", value="1"),
                                dmc.TabsTab("По датам", value="2"),
                                
                            ]
                        ),
                    ],
                    id=self.summary_tab_id,
                    value="2",
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
        
        
    
    def layout(self):
        return dmc.Container(
            [
                dmc.Title('Продажи за период',order=2),
                dmc.Divider(size='xs',label=f"Дата обновления: {self.last_update.strftime('%d %B %Y')}"),
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
                dmc.Divider(size='xs'),
                dmc.Space(h=20),
                self.tabs_conteiner,
                
                
            ],
            fluid=True
        )
    
    def register_callbacks(self,app):
        @app.callback(
            Output(self.ag_container_id,'children'),
            
            Input(self.summary_tab_id,'value'),
            Input(FILTERS.date_picker_id,'value'),
            Input(FILTERS.cat_multy_id,'value'),
            Input(FILTERS.brand_multy_id,'value'),
            Input(FILTERS.gender_multy_id,'value'),
            
          
        )
        def regnder_tab(tab_value,date_range,cat_list, brand_list,gender_list):
            if date_range:
               start = date_range[0]
               end = date_range[1]
            else:
                start = date(2024,1,1)
                end = date.today()
            
            if tab_value == '1':
               return  in_construction_banner()
            elif tab_value == '2':
               print(date_range) 
               return  grid_date(start,end,cat_list,brand_list,gender_list)
            