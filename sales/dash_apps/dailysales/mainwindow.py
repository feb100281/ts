# Это layout для daily sales

from django_plotly_dash import DjangoDash
from dash import Input, Output, State, no_update,dcc, MATCH, html
import pandas as pd
import numpy as np
from dash_iconify import DashIconify
import dash_mantine_components as dmc
from utils.dash_components.common import CommonComponents as CC  #Отсюда импортируем компоненты одинаковые для все приложений
from utils.dash_components.dftotable import df_dmc_table
import locale
locale.setlocale(locale.LC_TIME, "ru_RU.UTF-8")
from .data import get_month_data

FORMATERS = {
    "revenue":  lambda v: f"₽{v:,.0f}",
    "amount": lambda v: f"₽{v:,.0f}",
    "quant": lambda v: f"{v:,.0f} ед",
    'var':lambda v: f"+ {v:,.0f}" if v > 0 else f"({abs(v):,.0f})" ,   
    'var_pct':lambda v: f"+ {v:,.0f}%" if v > 0 else f"({abs(v):,.0f})%" ,   
}



class MainWindow:
    def __init__(self, date=None):
        self.date = date
        
        self.data = get_month_data(date)
        
        
    def make_summary(self):
        df =  self.data.copy(deep=True)
        df['date'] = pd.to_datetime(df['date'],errors='coerce')
        df['month'] =  pd.to_datetime(df['date'],errors='coerce').dt.strftime('%b %y').str.capitalize()
        df_long = df.melt(
            id_vars='month',
            value_vars=['amount', 'revenue', 'quant','sales','rtr'],
            var_name='metric',
            value_name='value'
        )
        
        df_pivot = df_long.pivot_table(
            index='metric',
            columns='month',
            values='value',
            aggfunc='sum'
        )
        c0, c1 = df_pivot.columns[:2]
        df_pivot['var'] = df_pivot[c1] - df_pivot[c0]
        df_pivot['var_pct'] = df_pivot['var'] / df_pivot[c0] * 100
        
        
        return df_pivot
                
        
        
        
    def layout(self):
        dt = pd.to_datetime(self.date)
        str_date = f"{dt.day} {dt.strftime('%B %Y')}"
        
        la = dmc.AppShell(
            [
                dmc.AppShellHeader(
                dmc.Group(
                    [
                        DashIconify(icon='streamline-freehand:cash-payment-bag-1',width=40,color='blue'),
                        CC.report_title(f"ОТЧЕТ ПО ПРОДАЖАМ ЗА {str_date.upper()}")
                    ],
                h="100%",
                px="md",
                mb='lg',
                
                )
                ),
                dmc.AppShellMain(
                    df_dmc_table(self.make_summary(),formaters=FORMATERS,className='classic-table')
                    
                    ),
            ],
            header={"height": 60},
            padding="md",
        )
        
        
        
        
        
        
        return dmc.Container(
            [
            la
            
            ],
            fluid=True           
        )
    
    def registered_callbacks(self,app):
        pass
        


