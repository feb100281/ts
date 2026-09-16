# reports/app/slides/costs/wb_costs.py
import dash_mantine_components as dmc
from dash_iconify import DashIconify
from datetime import date, timedelta
import pandas as pd
import numpy as np
import locale
from ...misc import breakdown_cards, paper_card
from cards.wo_app.data import get_data_by_date
from utils.wb_fields import WB_FIELDS


try:
    locale.setlocale(locale.LC_TIME, "ru_RU.UTF-8")
except:
    locale.setlocale(locale.LC_TIME, "Russian_Russia.1251")

# from cards.wo_app.data import get_data_by_date

from .data import get_summary, get_deduction_card, get_logictic_card, get_penalty_card, get_other_card


# Загрузка данных
today = date.today()


# Прошлая неделя (основной период)
start_week = today - timedelta(days=7)
end_week = today - timedelta(days=1)

# Позапрошлая неделя (для сравнения)
start_prev_week = start_week - timedelta(days=7)
end_prev_week = end_week - timedelta(days=7)

df_weekly = get_summary(start_week, end_week)

df_weekly=df_weekly.set_index('field')
df_weekly.rename(index=WB_FIELDS,inplace=True)
df_weekly = df_weekly.sort_values(by='amount',ascending=True)
print(df_weekly)


def deduction_card():
    df = get_deduction_card(start_week,end_week)
    total = df['amount'].sum()
    return breakdown_cards(
        df=df,
        title=f"{total:,.0f} ₽",
        subtitle=f"Маркетинг и удержания",
        total_column='amount',
        name_column='btn',
        color='teal',
        icon = 'icon-park-outline:sales-report'
    )
    


def delivery_card():
    df = get_logictic_card(start_week, end_week)
    total = df['amount'].sum()
    return breakdown_cards(
        df=df,
        title=f"{total:,.0f} ₽",
        subtitle=f"Логистика",
        total_column='amount',
        name_column='btn',
        color='grape',
        icon = 'tabler:truck'
    )
    
    
    
def penalty_card():
    df = get_penalty_card(start_week, end_week)
    total = df['amount'].sum()
    return breakdown_cards(
        df=df,
        title=f"{total:,.0f} ₽",
        subtitle=f"Штрафы",
        total_column='amount',
        name_column='btn',
        color='orange',
        icon = 'material-symbols:feed-outline-rounded'
    )
    
    

def other_card():
    df = get_other_card(start_week, end_week)
    total = df['amount'].sum()
    return breakdown_cards(
        df=df,
        title=f"{total:,.0f} ₽",
        subtitle=f"Прочие расходы",
        total_column='amount',
        name_column='btn',
        color='yellow',
        icon = 'carbon:cost'
    )
    

def make_timeline():
    return dmc.DatesProvider(
        dmc.MiniCalendar(
            defaultDate=start_week.isoformat(),
            value=end_week.isoformat(),
           
        ),
        settings={"locale": "ru"},
    )

caption = dmc.Group(
    [
    DashIconify(icon='streamline-stickies-color:qr-code-duo',width=36),
    dmc.Title('Расходы на реализацию за неделю'.upper(),order=4)
    ]
)



def cost_text():
    df = get_summary(start_week,end_week)
    total_cur = df['amount'].sum()
    df_prev = get_summary(start_prev_week, end_prev_week)
    total_prev = df_prev['amount'].sum()
    diff_abs =  total_prev - total_cur
    diff_pers = diff_abs/total_prev * 100
    df_cur_reven = get_data_by_date(start=start_week, end = end_week)
    amount_vatless = df_cur_reven['amount_vatless'].sum()
    share_costs = total_cur / amount_vatless * 100
    big_number = f"{total_cur:,.0f}₽"
    text_comments = f""" 
    За период с {start_week.strftime('%d %b %Y')} по {end_week.strftime('%d %b %Y')} совокупные расходы на реализацию 
    {'уменьшились' if total_cur >total_prev else 'увеличились' } на {abs(diff_abs):,.0f} рублей или на {abs(diff_pers):,.1f}%
    по сравнению с показателями предыдущей недели.
    Доля расходов в выручке составляет {abs(share_costs):,.1f}%.
    
    """
    return dmc.Paper(
    children=[
        dmc.Group(
            [
                dmc.Stack(
                    [
                        dmc.Text(
                            big_number,
                            size="56px",
                            fw=900,
                            c="red",  # красный для расходов
                            style={"lineHeight": 1.2},
                        ),
                        dmc.Text(
                            "Общие расходы, без НДС",
                            size="xs",
                            c="dimmed",
                            tt="uppercase",
                            fw=600,
                        ),
                    ],
                    gap="0",
                    style={"minWidth": "250px"},
                ),
                dmc.Divider(orientation="vertical", size="sm"),
                dmc.Text(
                    text_comments, 
                    size='sm', 
                    c='dimmed',
                    style={"flex": 1, "textAlign": "left"}
                ),
            ],
            align="center",
            gap="xl",
            wrap="nowrap",
        ),
    ],
    radius="sm",
    p="lg",
    shadow="sm",
    withBorder=True,
)
    
    
    
    
    
   
def card1_title():
    return dmc.Group(
        [
            dmc.Group([
                DashIconify(
                    icon='streamline-stickies-color:qr-code-duo',
                    width=36
                ),
                dmc.Title(
                    'Расходы на реализацию за неделю'.upper(),
                    order=4
                ),
            ]),
            make_timeline(),
        ],
        justify="space-between",
        w="100%",
    )


card_layout = paper_card(
    title=card1_title(),
    
    content= dmc.Stack(
        [
            cost_text(),
            dmc.Grid(
        [
            dmc.GridCol(deduction_card(), span=3),   # 3 из 12 = 25% ширины
            dmc.GridCol(delivery_card(), span=3),
            dmc.GridCol(penalty_card(), span=3),
            dmc.GridCol(other_card(), span=3),
        ],
        gutter="md",  # отступы между карточками
        grow=True,    # заставляет все колонки быть одинаковой высоты
    )
            
        ]
    )
    )



def layout(report=None, filters=None):
    return [
        dmc.Container(
            [
            
                card_layout
            ],
            fluid=True,
            p=0,
            style={"width": "1280px", "height": "720px"},
            
            ),

        
       
    ]



