import dash_mantine_components as dmc
from datetime import date
from dash_iconify import DashIconify
from cards.wo_app.data import get_data_by_date
from .data import get_inventorie
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

df['date_from'] = pd.to_datetime(df['date_from'])
df['year'] = df['date_from'].dt.year.astype(str)
df['qrt'] = df['date_from'].dt.quarter
df['qrt'] = "Q" + df['qrt'].astype(str)

pvt = df.pivot_table(
    index='year',
    columns='qrt',
    values='cogs',
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


inv_chart_df = get_inventorie(date(2023,1,1))
inv_chart_df = inv_chart_df[inv_chart_df['year'] > 2023].copy()
chart_df = inv_chart_df[['period','inventories']]

inventory_chart = dmc.AreaChart(
    h=220,
    w="95%",

    data=chart_df.to_dict("records"),

    dataKey="period",

    series=[
        {
            "name": "inventories",
            "label": "Запасы",
            "color": "grape",
        }
    ],

    curveType="Step",

    withDots=False,
    withLegend=False,

    gridAxis="y",

    tickLine="x",

    withXAxis=True,
    withYAxis=True,

    withTooltip=False,

    yAxisLabel="млн ₽",
    withPointLabels=True,

    valueFormatter={"function": "formatMillions"},
)


chart_title = dmc.Group(
    [
        DashIconify(icon='streamline-stickies-color:refund-product-reciept',width=26),
        dmc.Title("Изменения запасов",order=3)
    ]
)

chart_card = paper_card(
    chart_title,
    inventory_chart
)


def layout(report=None, filters=None):
    return dmc.Container(
        [
            costs_card,
            dmc.Space(h=10),
            chart_card
        ],
        fluid=True
    )

