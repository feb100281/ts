# reports/app/slides/upd/daily_finance_result.py
import dash_mantine_components as dmc
from dash import dcc
from dash_iconify import DashIconify
from datetime import date, timedelta
import pandas as pd
import numpy as np
import locale
import plotly.express as px
import plotly.graph_objects as go
from ...misc import metric_card_adj, paper_card, fancy_table

try:
    locale.setlocale(locale.LC_TIME, "ru_RU.UTF-8")
except:
    locale.setlocale(locale.LC_TIME, "Russian_Russia.1251")

from cards.wo_app.data import get_data_by_date

# Загрузка данных
start_date = date.today() - timedelta(days=7)
end_date = date.today()- timedelta(days=1)
df = get_data_by_date(start_date, end_date)
df = df.sort_values('date_from')

# last_day = df.iloc[0]
# prev_day = df.iloc[1] if len(df) > 1 else last_day

def get_trend_color(current, previous):
    if previous == 0:
        return "gray", "minus"
    if current > previous:
        return "green", "trending-up"
    elif current < previous:
        return "red", "trending-down"
    else:
        return "gray", "minus"



# словарик с карточками
total_revenue = df['amount_vatless'].sum()  # Выручка без НДС
total_cost = df['cogs'].sum()  # Себестоимость товаров
total_net_sales = df['total_net_sales'].sum()  # Кол-во продаж всего
total_no_cost = df['no_cost'].sum()  # Кол-во продаж без себестоимости (уже готово)
total_wb_commission = df['net_comission'].sum()  # Комиссия WB
total_wb_costs = df['wb_costs'].sum()  # Расходы WB
total_result = df['day_result'].sum()  # Результат за период
margin_gross = df.margin_gross.sum()

cards_dict = {
    'card1':{
        'title':'Выручка без НДС',
        'value':f"{total_revenue:,.0f} ₽",
        'icon':'streamline-ultimate-color:accounting-bill-stack-1',
        'color':'teal',
        'subtitle':'за вычетом возвратов',        
    },
    'card2':{
        'title':'С/сть товаров',
        'value':f"{total_cost:,.0f} ₽",
        'icon':'streamline-ultimate-color:accounting-coins',
        'color':'red',
        'subtitle':f"{total_cost/total_revenue*100:,.1f}% от выручки",        
    },
    'card3':{
        'title':'Комиссия WB',
        'value':f"{-total_wb_commission:,.0f} ₽",
        'icon':'streamline-ultimate-color:align-top',
        'color':'green' if total_wb_commission > 0 else 'red',
        'subtitle':f"{total_wb_commission/total_revenue*100:,.1f}% от выручки",        
    },
    
    'card4':{
        'title':'Расходы WB',
        'value':f"{-total_wb_costs:,.0f} ₽",
        'icon':'streamline-ultimate-color:delivery-truck-cargo',
        'color':'green' if total_wb_costs > 0 else 'red',
        'subtitle':f"{total_wb_costs/total_revenue*100:,.1f}% от выручки",        
    },
    
    'card5':{
        'title':'Бух. вал. прибыль',
        'value':f"{total_result:,.0f} ₽",
        'icon':'streamline-ultimate-color:accounting-calculator-1',
        'color':'green' if total_result > 0 else 'red',
        'subtitle':f"{total_result/total_revenue*100:,.1f}% от выручки",        
    },
    
}

def make_first_raw():
    chld = []
    for cards, d in cards_dict.items():
        chld.append(
            metric_card_adj(
                title=d['title'],
                value=d['value'],
                icon=d['icon'],
                color=d['color'],
                subtitle=d['subtitle']       
            )
        )
    
    return dmc.SimpleGrid(
        cols=len(chld),  # 5 колонок
        spacing="md",
        children=chld,
    )
    

def make_timeline():
    return dmc.DatesProvider(
        dmc.MiniCalendar(
            defaultDate=start_date.isoformat(),
            value=end_date.isoformat(),
           
        ),
        settings={"locale": "ru"},
    )

    
def card1_title():
    return dmc.Group(
        [
            dmc.Group([
                DashIconify(
                    icon='streamline-stickies-color:control',
                    width=36
                ),
                dmc.Title(
                    'Бух. валовая прибыль за неделю'.upper(),
                    order=4
                ),
            ]),
            make_timeline(),
        ],
        justify="space-between",
        w="100%",
    )

ren = {
    'date_from':'Дата',
    'amount_vatless':'Выр без НДС',
    'cogs':'С/сть', 
    'total_net_sales': 'Q продаж', 
    'no_cost': 'Q без с/сти', 
    'net_comission': 'Комиссия WB', 
    'wb_costs': 'Расходы WB',
    'day_result': 'Итого'
}

keep_cols = list(ren.keys())

# Используем .copy() чтобы избежать SettingWithCopyWarning
dff = df[keep_cols].copy()


dff = dff.sort_values('date_from')

dff['Дата'] = pd.to_datetime(dff['date_from'])
dff['Дата'] = dff['Дата'].dt.strftime('%d %b %Y').str.capitalize()

dff = dff.drop(columns=['date_from'])

dff['% без с/сти'] = dff.no_cost / dff.total_net_sales * 100
dff['% без с/сти'] = dff['% без с/сти'].round(1)


dff = dff.rename(columns=ren)
dff = dff.set_index('Дата')
dff = dff[['Выр без НДС', 'С/сть', 'Q продаж', 'Q без с/сти', '% без с/сти', 'Комиссия WB', 'Расходы WB', 'Итого']]

def sparline():
    raw = dff['Выр без НДС'].to_numpy(dtype=float)

    if len(raw) == 0:
        data = []

    else:
        min_val = raw.min()
        data = raw - min_val
        if data.max() != 0:
            data = data + data.max() * 0.05

        data = data.tolist()

    return dmc.Sparkline(
        curveType="Linear",
        color="teal",
        fillOpacity=1,
        withGradient=True,
        strokeWidth=2,
        w=400,
        h=40,
        data=data,
    )


def card2_title():
    return dmc.Group(
        [
            dmc.Group([
                DashIconify(
                    icon='streamline-stickies-color:date-time-setting',
                    width=36
                ),
                dmc.Title(
                    'Детализация по дням'.upper(),
                    order=4
                ),
            ]),
            sparline(),
        ],
        justify="space-between",
        w="100%",
    )


    
def slide1_layout():
    return dmc.Container(
        [
            paper_card(
                title=card1_title(),
                content=make_first_raw(),
                
                
                ),
            dmc.Space(h=10),
            paper_card(
                title =card2_title(),
                content=fancy_table(dff,  highlight_last_col=True,)                
            )
           
           
        ],
        fluid=True,
        p=0,
        style={"width": "1280px", "height": "720px"},
    )
        
    


# ==================== ОСНОВНОЙ ЛЕЙАУТ ====================
def layout(report=None, filters=None):
    return [
        
        slide1_layout(),
       
    ]
    
