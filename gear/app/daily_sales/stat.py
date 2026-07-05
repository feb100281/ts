from datetime import date
import locale

import pandas as pd
import dash_mantine_components as dmc
from dash_iconify import DashIconify
from dash import dcc, Input, Output, State, ALL

from .data import get_last_update
from .filters import WbFilters
from .grids import grid_date, day_details
from .ui import export_buttons_main, export_buttons_details
from ..misc.baners import in_construction_widjet
from .summary import get_sales_summary
from ..data.base import DashboardData


try:
    locale.setlocale(locale.LC_ALL, "ru_RU.UTF-8")
except locale.Error:
    pass


## Делаем PL виджет




def wrap_in_paper(icon,title,content):
    return dmc.Paper(
        withBorder=True,
        shadow="md",
        radius="md",
        p="xl",
        children = dmc.Stack(
            [
                dmc.Group(
                    [
                        icon,
                        dmc.Title(title,order=4)
                    ]
                ),
                content
            ]
        )
    )
    

class StatWindow:
    def __init__(self, 
                 date_range = [date(2024,1,1),date.today()],
                 cat = None,
                 brand = None,
                 gender = None
                 ):
        dr = [date(2024,1,1),date.today()] if not date_range else date_range
        self.start, self.end = dr
        self.cat = cat
        self.brand = brand
        self.gender = gender    
        
        self.stat_container_id = 'stat_container_id'
        
    
    
    def layout(self):
        return dmc.Container(
            [
                dmc.Stack(
                    [
                        dmc.Grid(
                            [
                                dmc.GridCol(
                                    [
                                        wrap_in_paper(
                                            DashIconify(icon='streamline-ultimate:accounting-calculator-1',width=24),
                                            'P&L по выбраным фильтрам',
                                            in_construction_widjet()
                                        )
                                    ],
                                    span=4
                                ),
                                dmc.GridCol(
                                    [
                                        wrap_in_paper(
                                            DashIconify(icon='material-symbols-light:area-chart-outline',width=24),
                                            'График динамики показателей',
                                            in_construction_widjet()
                                        )
                                    ],
                                    span=8
                                ),
                                
                            ]
                            
                        ),
                        dmc.SimpleGrid(
                            [
                                wrap_in_paper(
                                            DashIconify(icon='ri:pie-chart-fill',width=24),
                                            'Структура доходов',
                                            in_construction_widjet()
                                        ),
                                wrap_in_paper(
                                            DashIconify(icon='ri:pie-chart-line',width=24),
                                            'Структура расходов',
                                            in_construction_widjet()
                                        )
                            ],
                            cols=2
                        )
                    ]
                )
            ],
            fluid=True,
            id = self.stat_container_id,
            # style={"display": "none"}
        )

# with DashboardData() as d:
#     rel = d.con.register('daily_sales',d.get_dayly_sales_grid_data())
#     rel.sql('select * from daily_sales').show()

