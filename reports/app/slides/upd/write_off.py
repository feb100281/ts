import dash_mantine_components as dmc
from dash_iconify import DashIconify
from cards.wo_app.data import get_data_by_item
from ...misc import(
    paper_card,
    fancy_numbers
)
import pandas as pd
import locale

locale.setlocale(
    locale.LC_TIME,
    "ru_RU.UTF-8"
)


""" 
Слайд со списаниями й по отработанным УПД
"""

df_list = {
2024:get_data_by_item('2024-01-01','2024-12-31'),
2025:get_data_by_item('2025-01-01','2025-12-31'),
2026:get_data_by_item('2026-01-01','2026-12-31'),
}

def make_revenue_comparison(year,df:pd.DataFrame):
    revenue = df['amount_vatless'].sum()
    comparison_revenue = df['comparison_revenue'].sum()
    diff = revenue - comparison_revenue
    total = revenue+comparison_revenue+diff
    return dmc.Group(
        [
            dmc.Title(str(year),order=4),
            dmc.ProgressRoot(
                [
                dmc.ProgressSection(
                    dmc.ProgressLabel(f"Выручка {revenue/1_000_000:,.0f}M"),
                    value = round(revenue/total*100,0),
                    color="cyan"
                ),
                dmc.ProgressSection(
                    dmc.ProgressLabel(f"Распределено {comparison_revenue/1_000_000:,.0f}M"),
                    value = round(comparison_revenue/total*100,0),
                    color="pink"
                ),
                # dmc.ProgressSection(
                #     dmc.ProgressLabel(f"Нет с/с {diff/1_000_000:,.0f}M"),
                #     value = round(diff/total*100,0),
                #     color="orange"
                # ),     
                ],
                size="20",
                style={
                "flex": 1,
                },                
            )
        ],
        align="center",
        style={
        "width": "100%",
        },
    )
    
def make_qty_comparison(year,df:pd.DataFrame):
    
    revenue = df['total_net_sales_qty'].sum()
    comparison_revenue = revenue - df['no_cost_qty'].sum()
    diff = revenue - comparison_revenue
    total = revenue+comparison_revenue+diff
    return dmc.Group(
        [
            dmc.Title(str(year),order=4),
            dmc.ProgressRoot(
                [
                dmc.ProgressSection(
                    dmc.ProgressLabel(f"Продажи {revenue/1_000:,.0f}K ед"),
                    value = round(revenue/total*100,0),
                    color="cyan"
                ),
                dmc.ProgressSection(
                    dmc.ProgressLabel(f"Распределено {comparison_revenue/1_000:,.0f}K ед"),
                    value = round(comparison_revenue/total*100,0),
                    color="pink"
                ),
                # dmc.ProgressSection(
                #     dmc.ProgressLabel(f"Нет с/с {diff/1_000_000:,.0f}M"),
                #     value = round(diff/total*100,0),
                #     color="orange"
                # ),     
                ],
                size="20",
                style={
                "flex": 1,
                },                
            )
        ],
        align="center",
        style={
        "width": "100%",
        },
    )


def make_key_comparison(year,df:pd.DataFrame):
    
    revenue = df[
    df["title"].isna()
        ]["total_net_sales_qty"].sum()
    comparison_revenue = (
            df.loc[
                df["title"].notna(),
                "no_cost_qty"
            ]
            .sum()
        )    
    total = revenue+comparison_revenue
    return dmc.Group(
        [
            dmc.Title(str(year),order=4),
            dmc.ProgressRoot(
                [
                dmc.ProgressSection(
                    dmc.ProgressLabel(f"Нет ключа {revenue/1_000:,.0f}K ед"),
                    value = round(revenue/total*100,0),
                    color="cyan"
                ),
                dmc.ProgressSection(
                    dmc.ProgressLabel(f"Нет товара {comparison_revenue/1_000:,.0f}K ед"),
                    value = round(comparison_revenue/total*100,0),
                    color="pink"
                ),
                # dmc.ProgressSection(
                #     dmc.ProgressLabel(f"Нет с/с {diff/1_000_000:,.0f}M"),
                #     value = round(diff/total*100,0),
                #     color="orange"
                # ),     
                ],
                size="20",
                style={
                "flex": 1,
                },                
            )
        ],
        align="center",
        style={
        "width": "100%",
        },
    )

revenue_card_list = []
for k,v in  df_list.items():
    revenue_card_list.append(make_revenue_comparison(k,v))
    

qty_card_list = []
for k,v in  df_list.items():
    qty_card_list.append(make_qty_comparison(k,v))
    
    
reason_card_list = []
for k,v in  df_list.items():
    reason_card_list.append(make_key_comparison(k,v))
    


process_title = dmc.Group(
    [
        DashIconify(icon='streamline-ultimate-color:cash-payment-bills-1',width=26),
        dmc.Title("Списания по выручке",order=3)
    ]
)

qty_title = dmc.Group(
    [
        DashIconify(icon='streamline-stickies-color:checking-order-duo',width=26),
        dmc.Title("Списания по количеству",order=3)
    ]
)


reason_title = dmc.Group(
    [
        DashIconify(icon='streamline-stickies-color:cancel-2',width=26),
        dmc.Title("Причины отсутствия себестоимости",order=3)
    ]
)


qty_card = paper_card(
    qty_title,
    dmc.Stack(
        children=qty_card_list,
        gap=2
    )
)

revenue_card = paper_card(
    process_title,
    dmc.Stack(
        children=revenue_card_list,
        gap=2
    )
)


reason_card = paper_card(
    reason_title,
    dmc.Stack(
        children=reason_card_list,
        gap=2
    )
)

def layout(report=None, filters=None):
    return dmc.Container(
        [
            revenue_card,
            dmc.Space(h=10),
            qty_card,
            dmc.Space(h=10),
            reason_card                 
        ],
        fluid=True
    )