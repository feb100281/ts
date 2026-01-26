# Это layout для daily sales

from django_plotly_dash import DjangoDash
from dash import Input, Output, State, no_update,dcc, MATCH, html
# import pandas as pd
# import numpy as np
from dash_iconify import DashIconify
import dash_mantine_components as dmc
from utils.dash_components.common import CommonComponents as CC  #Отсюда импортируем компоненты одинаковые для все приложений

class MainWindow:
    def __init__(self, date=None):
        pass
        
    def layout(self):
        return dmc.Container(
            CC.report_title(text='Отчет о продажах')            
        )
    
    def registered_callbacks(self,app):
        pass
        


