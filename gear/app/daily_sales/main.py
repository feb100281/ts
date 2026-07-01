from .data import get_last_update
import dash_mantine_components as dmc
from dash_iconify import DashIconify
from dash import dcc, html, Input, Output, State, no_update
import pandas as pd
from .filters import WbFilters

import locale
locale.setlocale(locale.LC_ALL, 'ru_RU.UTF-8') 

FILTERS = WbFilters()


class MainWindow:
    def __init__(self):
        self.last_update = pd.to_datetime(get_last_update())
    
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
                        FILTERS.get_gender_filter(width=250)      
                    ]
                    ),
                          
                
            ],
            fluid=True
        )
    
    def register_callbacks(self,app):
        pass