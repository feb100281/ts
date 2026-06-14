# reports/app/slides/upd/agg_results.py
import dash_mantine_components as dmc
from dash import dcc
from dash_iconify import DashIconify
from datetime import date, timedelta
import pandas as pd
import numpy as np
import locale
import plotly.express as px
import plotly.graph_objects as go
from ...misc import accounting_table

try:
    locale.setlocale(locale.LC_TIME, "ru_RU.UTF-8")
except:
    locale.setlocale(locale.LC_TIME, "Russian_Russia.1251")

from cards.wo_app.data import get_data_by_date

# Загрузка данных
today = date.today()

# Текущий год
start_year = date(today.year, 1, 1)
end_date = today - timedelta(days=1)

# Прошлый год (тот же период)
past_year_start = date(today.year - 1, 1, 1)
past_year_end = date(end_date.year - 1, end_date.month, end_date.day)

# Текущий квартал
start_quarter = date(today.year,((today.month - 1) // 3) * 3 + 1,1)

# Аналогичный квартал прошлого года
past_quarter_start = date(start_quarter.year - 1, start_quarter.month, start_quarter.day)
past_quarter_end = date(end_date.year - 1, end_date.month, end_date.day)


df_year = get_data_by_date(start_year, end_date)
df_quarter = get_data_by_date(start_quarter, end_date)

df_past_year = get_data_by_date(past_year_start, past_year_end)
df_past_quarter = get_data_by_date(past_quarter_start, past_quarter_end)

df_year['tp'] ='YTD'
df_past_year['tp'] = 'PY YTD'

df_quarter['tp'] ='QTD'
df_qrt = df_quarter.copy()
df_past_quarter['tp'] = 'PY QTD'
df_qrt_past = df_past_quarter.copy()
df_anual = pd.concat([df_year,df_past_year],ignore_index=True)
df_quarter = pd.concat([df_quarter, df_past_quarter], ignore_index=True)
cols = {
    'date_from':'date_from',
    'tp':'tp',
    'amount':'Выручка с НДС',
    'vat_amount':'НДС',
    'amount_vatless':'Выручка без НДС',
    'cogs':'С/сть',
    'net_comission':'Комиссия WB',
    'wb_costs':'Расходы WB',
    'day_result':'Валовая прибыль',
}

cols_to_keep = list(cols.keys())

df_anual = df_anual[cols_to_keep]
df_quarter = df_quarter[cols_to_keep]

df_anual.rename(columns=cols,inplace=True)
df_quarter.rename(columns=cols, inplace=True)


df_anual_long = df_anual.melt(
    id_vars=['date_from', 'tp'],
    var_name='metric',
    value_name='value'
)

df_quarter_long = df_quarter.melt(
    id_vars=['date_from', 'tp'],
    var_name='metric',
    value_name='value'
    
)

metric_order = [
    'Выручка с НДС',
    'НДС',
    'Выручка без НДС',
    'С/сть',
    'Комиссия WB',
    'Расходы WB',
    'Валовая прибыль',
]

df_anual_long['metric'] = pd.Categorical(
    df_anual_long['metric'],
    categories=metric_order,
    ordered=True
)

df_quarter_long['metric'] = pd.Categorical(
    df_quarter_long['metric'],
    categories=metric_order,
    ordered=True
)

df_pivot_year = df_anual_long.pivot_table(
    index='metric',
    columns='tp',
    values='value',
    aggfunc='sum'
) / 1_000_000

df_pivot_quarter = df_quarter_long.pivot_table(
    index='metric',
    columns='tp',
    values='value',
    aggfunc='sum'
) / 1_000_000


df_pivot_year.loc['НДС']*=-1
df_pivot_year.loc['С/сть']*=-1
df_pivot_quarter.loc['НДС']*=-1
df_pivot_quarter.loc['С/сть']*=-1



df_pivot_year['Δ'] = (df_pivot_year['YTD'] - df_pivot_year['PY YTD'])
df_pivot_year['Δ'] = df_pivot_year['Δ'].round(2)
df_pivot_year['%'] = (df_pivot_year['YTD'] - df_pivot_year['PY YTD']) / df_pivot_year['PY YTD'] * 100
df_pivot_year['%'] = df_pivot_year['%'].round(1)
df_pivot_year['YTD']= df_pivot_year['YTD'].round(2)
df_pivot_year['PY YTD']= df_pivot_year['PY YTD'].round(2)

df_pivot_year = df_pivot_year[['YTD', 'PY YTD', 'Δ', '%']]

df_pivot_quarter['Δ'] = (df_pivot_quarter['QTD'] - df_pivot_quarter['PY QTD'])
df_pivot_quarter['Δ'] = df_pivot_quarter['Δ'].round(2)
df_pivot_quarter['%'] = (df_pivot_quarter['QTD'] - df_pivot_quarter['PY QTD']) / df_pivot_quarter['PY QTD'] * 100
df_pivot_quarter['%'] = df_pivot_quarter['%'].round(1)
df_pivot_quarter['QTD']= df_pivot_quarter['QTD'].round(2)
df_pivot_quarter['PY QTD']= df_pivot_quarter['PY QTD'].round(2)

df_pivot_quarter = df_pivot_quarter[['QTD', 'PY QTD', 'Δ', '%']]

print(df_pivot_quarter)



def ring_progress(df_current:pd.DataFrame, df_past:pd.DataFrame):
    net_sales_current = df_current['total_net_sales'].sum()
    abs_net_sales_current = net_sales_current
    net_sales_past = df_past['total_net_sales'].sum()
    abs_net_sales_past = net_sales_past
    tot_sales = net_sales_current + net_sales_past
    net_sales_current = round(net_sales_current/tot_sales*100,0)
    net_sales_past = 100 - net_sales_current
    
       
    no_costs_current = df_current['no_cost'].sum()
    no_costs_past = df_past['no_cost'].sum() 
    
    abs_no_costs_current = no_costs_current
    abs_no_costs_past = no_costs_past
    
    total_no_costs = no_costs_current + no_costs_past
    no_costs_current = round(no_costs_current / total_no_costs * 100, 0)
    
    no_costs_past = 100 - no_costs_current
    
    
    return dmc.Group(
    [
        dmc.Group(
            [
                dmc.RingProgress(
                    sections=[
                        {"value": net_sales_current, "color": "teal"},
                        {"value": net_sales_past, "color": "gray"},
                    ],
                    label=dmc.Text(
                        "Кол-во продаж",
                        size="xs",
                        ta="center"
                    ),
                    size=120,
                    thickness=10,
                    roundCaps=True,
                ),

                dmc.List(
                    [
                        dmc.ListItem(
                            f"{start_year.year} - {abs_net_sales_current/1_000:,.0f}K",
                            icon=DashIconify(
                                icon="material-symbols:circle",
                                color="teal",
                                width=8,
                            ),
                        ),
                        dmc.ListItem(
                            f"{past_year_start.year} - {abs_net_sales_past/1_000:,.0f}K",
                            icon=DashIconify(
                                icon="material-symbols:circle",
                                color="gray",
                                width=8,
                            ),
                        ),
                    ],
                    size="xs",
                ),
            ],
            gap="xs",
            wrap="nowrap",
        ),

        dmc.Group(
            [
                dmc.RingProgress(
                    sections=[
                        {"value": no_costs_current, "color": "indigo"},
                        {"value": no_costs_past, "color": "gray"},
                    ],
                    label=dmc.Text(
                        "Без с/сти",
                        size="xs",
                        ta="center"
                    ),
                    size=120,
                    thickness=10,
                    roundCaps=True,
                ),

                dmc.List(
                    [
                        dmc.ListItem(
                            f"{start_year.year} - {abs_no_costs_current/1_000:,.0f}K",
                            icon=DashIconify(
                                icon="material-symbols:circle",
                                color="indigo",
                                width=8,
                            ),
                        ),
                        dmc.ListItem(
                            f"{past_year_start.year} - {abs_no_costs_past/1_000:,.0f}K",
                            icon=DashIconify(
                                icon="material-symbols:circle",
                                color="gray",
                                width=8,
                            ),
                        ),
                    ],
                    size="xs",
                ),
            ],
            gap="xs",
            wrap="nowrap",
        ),
    ],
    justify="center",
    gap="lg",
)

card_body = dmc.SimpleGrid(
    cols=2,
    spacing='md',
    children=[
        dmc.Stack([
        accounting_table(
            df_pivot_year,
            title="Финансовый результат с начала года (YTD)"
        ),
        ring_progress(df_year, df_past_year),
        ]),
        dmc.Stack([
            accounting_table(
            df_pivot_quarter,
            title="Финансовый результат с начала квартала (QTD)"
        ),
          ring_progress(df_qrt, df_qrt_past),  
            
        ])     
        
    ]
)
    


def layout(report=None, filters=None):
    return [
        dmc.Container(
            [
                card_body,
                
            ],
            fluid=True,
            p=0,
            style={"width": "1280px", "height": "720px"},
            
            ),

        
       
    ]



# def get_trend_color(current, previous):
#     if previous == 0:
#         return "gray", "minus"
#     if current > previous:
#         return "green", "trending-up"
#     elif current < previous:
#         return "red", "trending-down"
#     else:
#         return "gray", "minus"





# # словарик с карточками
# total_revenue = df['amount_vatless'].sum()  # Выручка без НДС
# total_cost = df['cogs'].sum()  # Себестоимость товаров
# total_net_sales = df['total_net_sales'].sum()  # Кол-во продаж всего
# total_no_cost = df['no_cost'].sum()  # Кол-во продаж без себестоимости (уже готово)
# total_wb_commission = df['net_comission'].sum()  # Комиссия WB
# total_wb_costs = df['wb_costs'].sum()  # Расходы WB
# total_result = df['day_result'].sum()  # Результат за период
# margin_gross = df.margin_gross.sum()

# cards_dict = {
#     'card1':{
#         'title':'Выручка без НДС',
#         'value':f"{total_revenue:,.0f} ₽",
#         'icon':'streamline-ultimate-color:accounting-bill-stack-1',
#         'color':'teal',
#         'subtitle':'за вычетом возвратов',        
#     },
#     'card2':{
#         'title':'С/сть товаров',
#         'value':f"{total_cost:,.0f} ₽",
#         'icon':'streamline-ultimate-color:accounting-coins',
#         'color':'red',
#         'subtitle':f"{total_cost/total_revenue*100:,.1f}% от выручки",        
#     },
#     'card3':{
#         'title':'Комиссия WB',
#         'value':f"{-total_wb_commission:,.0f} ₽",
#         'icon':'streamline-ultimate-color:align-top',
#         'color':'green' if total_wb_commission > 0 else 'red',
#         'subtitle':f"{total_wb_commission/total_revenue*100:,.1f}% от выручки",        
#     },
    
#     'card4':{
#         'title':'Расходы WB',
#         'value':f"{-total_wb_costs:,.0f} ₽",
#         'icon':'streamline-ultimate-color:delivery-truck-cargo',
#         'color':'green' if total_wb_costs > 0 else 'red',
#         'subtitle':f"{total_wb_costs/total_revenue*100:,.1f}% от выручки",        
#     },
    
#     'card5':{
#         'title':'Бух. вал. прибыль',
#         'value':f"{total_result:,.0f} ₽",
#         'icon':'streamline-ultimate-color:accounting-calculator-1',
#         'color':'green' if total_result > 0 else 'red',
#         'subtitle':f"{total_result/total_revenue*100:,.1f}% от выручки",        
#     },
    
# }

# def make_first_raw():
#     chld = []
#     for cards, d in cards_dict.items():
#         chld.append(
#             metric_card_adj(
#                 title=d['title'],
#                 value=d['value'],
#                 icon=d['icon'],
#                 color=d['color'],
#                 subtitle=d['subtitle']       
#             )
#         )
    
#     return dmc.SimpleGrid(
#         cols=len(chld),  # 5 колонок
#         spacing="md",
#         children=chld,
#     )
    

# def make_timeline():
#     return dmc.DatesProvider(
#         dmc.MiniCalendar(
#             defaultDate=start_date.isoformat(),
#             value=end_date.isoformat(),
           
#         ),
#         settings={"locale": "ru"},
#     )

    
# def card1_title():
#     return dmc.Group(
#         [
#             dmc.Group([
#                 DashIconify(
#                     icon='streamline-stickies-color:control',
#                     width=36
#                 ),
#                 dmc.Title(
#                     'Бух. валовая прибыль за неделю'.upper(),
#                     order=4
#                 ),
#             ]),
#             make_timeline(),
#         ],
#         justify="space-between",
#         w="100%",
#     )

# ren = {
#     'date_from':'Дата',
#     'amount_vatless':'Выр без НДС',
#     'cogs':'С/сть', 
#     'total_net_sales': 'Q продаж', 
#     'no_cost': 'Q без с/сти', 
#     'net_comission': 'Комиссия WB', 
#     'wb_costs': 'Расходы WB',
#     'day_result': 'Итого'
# }

# keep_cols = list(ren.keys())

# # Используем .copy() чтобы избежать SettingWithCopyWarning
# dff = df[keep_cols].copy()


# dff = dff.sort_values('date_from')

# dff['Дата'] = pd.to_datetime(dff['date_from'])
# dff['Дата'] = dff['Дата'].dt.strftime('%d %b %Y').str.capitalize()

# dff = dff.drop(columns=['date_from'])

# dff['% без с/сти'] = dff.no_cost / dff.total_net_sales * 100
# dff['% без с/сти'] = dff['% без с/сти'].round(1)


# dff = dff.rename(columns=ren)
# dff = dff.set_index('Дата')
# dff = dff[['Выр без НДС', 'С/сть', 'Q продаж', 'Q без с/сти', '% без с/сти', 'Комиссия WB', 'Расходы WB', 'Итого']]

# def sparline():
#     raw = dff['Выр без НДС'].to_numpy(dtype=float)

#     if len(raw) == 0:
#         data = []

#     else:
#         min_val = raw.min()
#         data = raw - min_val
#         if data.max() != 0:
#             data = data + data.max() * 0.05

#         data = data.tolist()

#     return dmc.Sparkline(
#         curveType="Linear",
#         color="teal",
#         fillOpacity=1,
#         withGradient=True,
#         strokeWidth=2,
#         w=400,
#         h=40,
#         data=data,
#     )


# def card2_title():
#     return dmc.Group(
#         [
#             dmc.Group([
#                 DashIconify(
#                     icon='streamline-stickies-color:date-time-setting',
#                     width=36
#                 ),
#                 dmc.Title(
#                     'Детализация по дням'.upper(),
#                     order=4
#                 ),
#             ]),
#             sparline(),
#         ],
#         justify="space-between",
#         w="100%",
#     )


    
# def slide1_layout():
#     return dmc.Container(
#         [
#             paper_card(
#                 title=card1_title(),
#                 content=make_first_raw(),
                
                
#                 ),
#             dmc.Space(h=10),
#             paper_card(
#                 title =card2_title(),
#                 content=fancy_table(dff,  highlight_last_col=True,)                
#             )
           
           
#         ],
#         fluid=True,
#         p=0,
#         style={"width": "1280px", "height": "720px"},
#     )
        
    


# # ==================== ОСНОВНОЙ ЛЕЙАУТ ====================
# def layout(report=None, filters=None):
#     return [
        
#         slide1_layout(),
       
#     ]