import dash_mantine_components as dmc
from datetime import date
from dash_iconify import DashIconify
from cards.wo_app.data import get_data_by_date
from ...misc import(
    paper_card,
    fancy_numbers,
    fancy_table
)
import pandas as pd
import locale

locale.setlocale(
    locale.LC_TIME,
    "ru_RU.UTF-8"
)

df = get_data_by_date(date(2024,1,1),date.today())

df['sales_date'] = pd.to_datetime(df['sales_date'])
df['year'] = df['sales_date'].dt.year.astype(str)
df['qrt'] = df['sales_date'].dt.quarter
df['qrt'] = "Q" + df['qrt'].astype(str)

pvt = df.pivot_table(
    index='year',
    columns='qrt',
    values='dt',
    aggfunc='sum'
)/1_000_000

pvt['FYE'] = pvt.sum(axis=1)

costs_tbl = fancy_table(
    pvt,
    # title="Выручка по кварталам",
    precision=2,
)


table_title = dmc.Group(
    [
        DashIconify(icon='streamline-stickies-color:reciept-1',width=26),
        dmc.Title("Бухгалтерская себестоимость",order=3)
    ]
)


costs_card = paper_card(
    table_title,
    dmc.Stack(
        children=costs_tbl,
        gap=2
    )
)

def layout(report=None, filters=None):
    return dmc.Container(
        [
            costs_card
        ],
        fluid=True
    )

