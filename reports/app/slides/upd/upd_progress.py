# reports/app/slides/upd/upd_progress.py
import dash_mantine_components as dmc
from dash_iconify import DashIconify
from .data import get_upd_data
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
Слайд с статистикой по отработанным УПД
"""
df = get_upd_data()
df_match = df.dropna(subset=["usk"])

#Ддвнные для карточек
min_date = pd.to_datetime(df['date'].min())
max_date = pd.to_datetime(df['date'].max())
upd_number = df['upd_document_id'].nunique()
upd_amount_vatless = df['upd_amount_vatless'].sum()
upd_qty = df['upd_qty'].sum()
upd_acc_vatless = df_match['upd_amount_vatless'].sum()
upd_acc_qty = df_match['upd_qty'].sum()
acc_share = upd_acc_vatless / upd_amount_vatless * 100
qty_share = upd_acc_qty / upd_qty * 100
nrows_income = len(df)
nrows_acc = len(df_match)
nrows_share = nrows_acc/nrows_income*100

df_chart = (
    df.groupby("name", as_index=False)
    ["upd_amount_vatless"]
    .sum()
    .sort_values(
        "upd_amount_vatless",
        ascending=False,
    )
)

df_acc_chart = (
    df_match.groupby("name", as_index=False)
    ["upd_amount_vatless"]
    .sum()
    .sort_values(
        "upd_amount_vatless",
        ascending=False,
    )
)




income_chart = dmc.BarChart(
    h = 200,
    w="70%",
    
    data=df_chart.to_dict("records"),

    dataKey="name",

    series=[
        {
            "name": "upd_amount_vatless",
            "label": "Сумма",
        }
    ],

    orientation="vertical",
    type="stacked",
    withBarValueLabel=True,
    withTooltip=False,

    tickLine="y",
    withLegend=False,
    withXAxis=False,
    gridAxis="none",
    # gridAxis="x",
    valueFormatter={"function": "formatMillions"},
)


acc_chart = dmc.BarChart(
    h = 200,
    w="70%",
    
    data=df_acc_chart.to_dict("records"),

    dataKey="name",

    series=[
        {
            "name": "upd_amount_vatless",
            "label": "Сумма",
        }
    ],

    orientation="vertical",
    type="stacked",
    withBarValueLabel=True,
    withTooltip=False,

    tickLine="y",
    withLegend=False,
    withXAxis=False,
    gridAxis="none",
    # gridAxis="x",
    valueFormatter={"function": "formatMillions"},
)



def get_badge(content):
    return dmc.Badge(
        content,
        size = 'xs',
        radius='sm',
        # variant='outline',
        color="orange"
    )

acc_share_badge = get_badge(f"{acc_share:,.1f}%")
qty_share_badge = get_badge(f"{qty_share:,.1f}%")
nrows_badge = get_badge(f"{nrows_share:,.1f}%")





process_title = dmc.Group(
    [
        DashIconify(icon='vscode-icons:file-type-excel2',width=26),
        dmc.Title("Обработано УПД",order=3)
    ]
)


processed_card_content = dmc.Stack(
    [
        fancy_numbers(f"{upd_number:,.0f} документов",
                      f"отработано в период с {min_date.strftime('%d.%m.%Y')} по {max_date.strftime('%d.%m.%Y')} ",
                      DashIconify(icon='oui:documents',width=26)
                      ),
        fancy_numbers(
            f"{upd_amount_vatless/1_000_000:,.0f} млн руб",
            "Приходы по УПД без НДС",
            DashIconify(icon='tdesign:money',width=26)
        ),
        fancy_numbers(
            f"{upd_qty:,.0f} единиц товара",
            "было куплено в соответсвии с УПД",
            DashIconify(icon='ion:shirt-outline',width=26)
        ),
        dmc.Space(h=20),
        dmc.Divider(
            label="Топ поставщиков",
            labelPosition="left",
        ),
        dmc.Space(h=10),
        dmc.Center(
            income_chart,
            ),
        
    ],
    gap=2
)

process_card = paper_card(
    process_title,
    processed_card_content
)


acc_title = dmc.Group(
    [
        DashIconify(icon='streamline-color:database-check',width=26),
        dmc.Title("Принято к учету",order=3)
    ]
)

acc_card_content = dmc.Stack(
    [
        fancy_numbers(f"{nrows_acc/1_000:,.0f}K позиций",
                      f"Принято к учету из УПД. {(nrows_income - nrows_acc):,.0f} позиций осталось",
                      DashIconify(icon='oui:documents',width=26),
                      nrows_badge
                      
                      ),
        fancy_numbers(
            f"{upd_acc_vatless/1_000_000:,.0f} млн руб",
            f"Принято к учету. {(upd_amount_vatless-upd_acc_vatless)/1_000_000:,.2f} млн руб осталось",
            DashIconify(icon='tdesign:money',width=26),
            acc_share_badge
        ),
        fancy_numbers(
            f"{upd_acc_qty:,.0f} единиц товара",
            f"Принято по УПД. {(upd_qty-upd_acc_qty):,.0f} ед осталось",
            DashIconify(icon='ion:shirt-outline',width=26),
            qty_share_badge
        ),
        dmc.Space(h=20),
        dmc.Divider(
            label="Топ поставщиков",
            labelPosition="left",
        ),
        dmc.Space(h=10),
        dmc.Center(
            acc_chart,
            ),       
    ],
    gap=2
)


acc_card = paper_card(
    acc_title,
    acc_card_content
)





def layout(report=None, filters=None):
    return dmc.Container(
        [
            dmc.SimpleGrid(
                cols=2,
                spacing="lg",
                children=[
                    process_card,
                    acc_card                    
                ]
                )
        ],
        fluid=True
        
    )
