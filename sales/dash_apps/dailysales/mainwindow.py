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
from .data import get_month_data,get_ytd_data

FORMATERS = {
    "Выручка":  lambda v: f"₽{v:,.0f}",
    "Оборот": lambda v: f"₽{v:,.0f}",
    "Комиссия":lambda v: f"{v:,.0f}%" if v > 0 else f"({abs(v):,.0f})%",
    "Кол-во": lambda v: f"{v:,.0f} ед",
    "Продажи":lambda v: f"₽{v:,.0f}",
    "Возвраты":lambda v: f"₽{v:,.0f}",
    "К возвратов":lambda v: f"{v:,.0f}%" if v > 0 else f"({abs(v):,.0f})%",   
    'Δ абс.':lambda v: f"+ {v:,.0f}" if v > 0 else f" - {abs(v):,.0f}" ,   
    'Δ отн.':lambda v: f"+ {v:,.0f}%" if v > 0 else f"- {abs(v):,.0f}%" ,   
}

RENAMING_COLS = {
    "revenue":'Выручка',
    "amount":"Оборот",
    "quant":"Кол-во",
    "sales":"Продажи",
    "rtr":"Возвраты"
    
}



class MainWindow:
    def __init__(self, date=None):
        self.date = date
        
        self.data = get_month_data(date)
        self.ytd_data = get_ytd_data(date)
        
    
    def make_dayly_summary(self):
        df =  self.data.copy(deep=True)
        df['month'] =  pd.to_datetime(df['date'],errors='coerce').dt.strftime('MTD %b %y').str.upper()
        df = df.drop(columns=['date'])
        df = df.groupby('month', as_index=False).sum()
        df['Комиссия'] = 100 - df['revenue'] / df['amount'] * 100
        df['К возвратов'] = df['rtr'] / df['sales'] * 100
        df = df.rename(columns=RENAMING_COLS)
        df_long = df.melt(
            id_vars='month',
            value_vars=['Выручка', 'Оборот','Комиссия', 'Кол-во','Продажи','Возвраты','К возвратов'],
            var_name='Метрика',
            value_name='value'
        )
        df_pivot = df_long.pivot_table(
            index='Метрика',
            columns='month',
            values='value',
            aggfunc='first'
        )
        
        c0, c1 = df_pivot.columns[:2]
        df_pivot['Δ абс.'] = df_pivot[c1] - df_pivot[c0]
        df_pivot['Δ отн.'] = df_pivot['Δ абс.'] / df_pivot[c0] * 100
        
        i_order = list(FORMATERS)
        i_order = i_order[:-2]
        
        return df_pivot.reindex(i_order)
    
    
    def make_ytd_summary(self):
        df =  self.ytd_data.copy(deep=True)
        df['month'] =  pd.to_datetime(df['date'],errors='coerce').dt.strftime('YTD %Y').str.upper()
        df = df.drop(columns=['date'])
        df = df.groupby('month', as_index=False).sum()
        df['Комиссия'] = 100 - df['revenue'] / df['amount'] * 100
        df['К возвратов'] = df['rtr'] / df['sales'] * 100
        df = df.rename(columns=RENAMING_COLS)
        df_long = df.melt(
            id_vars='month',
            value_vars=['Выручка', 'Оборот','Комиссия', 'Кол-во','Продажи','Возвраты','К возвратов'],
            var_name='Метрика',
            value_name='value'
        )
        df_pivot = df_long.pivot_table(
            index='Метрика',
            columns='month',
            values='value',
            aggfunc='first'
        )
        
        c0, c1 = df_pivot.columns[:2]
        df_pivot['Δ абс.'] = df_pivot[c1] - df_pivot[c0]
        df_pivot['Δ отн.'] = df_pivot['Δ абс.'] / df_pivot[c0] * 100
        
        i_order = list(FORMATERS)
        i_order = i_order[:-2]
        
        return df_pivot.reindex(i_order)
    
    
    
        
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
                    [
                        df_dmc_table(self.make_dayly_summary(),formaters=FORMATERS,className='classic-table'),
                        dmc.Space(h=30),
                        df_dmc_table(self.make_ytd_summary(),formaters=FORMATERS,className='classic-table')
                    ]
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
        


