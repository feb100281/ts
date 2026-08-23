# reports/app/slides/costs/agg_wb_costs.py
import dash_mantine_components as dmc
from dash import dcc
from dash_iconify import DashIconify
from datetime import date, timedelta
import pandas as pd
import numpy as np
import locale
import plotly.express as px
import plotly.graph_objects as go
from ...misc import accounting_table, costs_table

try:
    locale.setlocale(locale.LC_TIME, "ru_RU.UTF-8")
except:
    locale.setlocale(locale.LC_TIME, "Russian_Russia.1251")

from cards.wo_app.data import get_data_by_date
from .data import get_summary,get_deduction_card,get_logictic_card,get_penalty_card,get_other_card

# Загрузка данных
today = date.today()

# Текущий год
start_year = date(today.year, 1, 1)
end_date = today - timedelta(days=1)

# Прошлый год (тот же период)
past_year_start = date(today.year - 1, 1, 1)
past_year_end = date(end_date.year - 1, end_date.month, end_date.day)


# Текущий квартал
start_quarter = date(today.year, ((today.month - 1) // 3) * 3 + 1, 1)

# Аналогичный квартал прошлого года 
past_quarter_start = date(today.year - 1, start_quarter.month, start_quarter.day)
past_quarter_end = date(today.year - 1, end_date.month, end_date.day)

quarter_names = {
    'Q1': '1 кв.',
    'Q2': '2 кв.',
    'Q3': '3 кв.',
    'Q4': '4 кв.'
}

current_quarter_num = (today.month - 1) // 3 + 1
current_quarter_name = f"{quarter_names[f'Q{current_quarter_num}']} {today.year}"
past_quarter_name = f"{quarter_names[f'Q{current_quarter_num}']} {today.year - 1}"

def get_ytd_table() ->pd.DataFrame:
    fnc = {
        'Маркетинг и удерж.': get_deduction_card,
        'Логистика': get_logictic_card,
        'Штрафы': get_penalty_card,
        'Прочие': get_other_card
    }
    
    dfs = []
    for key, func in fnc.items():
        df = func(start_year, end_date)
        df['tp'] = 'YTD'
        df['cat'] = key
        dfp = func(past_year_start, past_year_end)
        dfp['tp'] = 'PY YTD'    
        dfp['cat'] = key   
        
        dfs.append(df)
        dfs.append(dfp)
    
    # Объединяем все DataFrame
    result = pd.concat(dfs, ignore_index=True)
    
    return result

def get_qrt_table():
    fnc = {
        'Маркетинг и удерж.': get_deduction_card,
        'Логистика': get_logictic_card,
        'Штрафы': get_penalty_card,
        'Прочие': get_other_card
    }
    
    dfs = []
    for key, func in fnc.items():
        # Текущий квартал (с годом)
        df = func(start_quarter, end_date)
        df['tp'] = 'QTD'  # ← меняем на QTD
        df['cat'] = key
        
        # Аналогичный квартал прошлого года (с годом)
        dfp = func(past_quarter_start, past_quarter_end)
        dfp['tp'] = 'PY QTD'  # ← меняем на PY QTD
        dfp['cat'] = key
        
        dfs.append(df)
        dfs.append(dfp)
    
    result = pd.concat(dfs, ignore_index=True)
    
    return result

print(get_ytd_table())

ytd_pivot = get_ytd_table().pivot_table(
    index=['cat','btn'],
    values='amount',
    columns='tp',
    aggfunc='sum'
)/1_000

column_order = ['YTD', 'PY YTD']
ytd_pivot = ytd_pivot[column_order]

print(ytd_pivot)





# Получаем данные
ytd_df = get_ytd_table()
qrt_df = get_qrt_table()

# Создаем таблицы
table = dmc.Stack(
    [
        costs_table(ytd_df, title="Расходы на реализацию (YTD)", unit="₽"),
        dmc.Space(h="md"),
        costs_table(qrt_df, title="Расходы на реализацию (QTD)", unit="₽"),
    ],
    gap="lg",
)

def sum_without_corrections(df: pd.DataFrame) -> float:
    return df.loc[
        df["btn"] != "Корректировки",
        "amount"
    ].sum()


def fmt_mln(value):
    return f"{value / 1_000_000:,.1f} млн ₽".replace(",", " ")


def fmt_num(value):
    return f"{value:,.0f}".replace(",", " ")


def cost_text():
    ytd_df = get_ytd_table()
    qrt_df = get_qrt_table()

    total_cur = sum_without_corrections(
        ytd_df[ytd_df["tp"] == "YTD"]
    )

    total_prev = sum_without_corrections(
        ytd_df[ytd_df["tp"] == "PY YTD"]
    )

    total_current_quarter = sum_without_corrections(
        qrt_df[qrt_df["tp"] == "QTD"]
    )

    corr_ytd = ytd_df.loc[
        (ytd_df["tp"] == "YTD")
        & (ytd_df["btn"] == "Корректировки"),
        "amount"
    ].sum()

    corr_qtd = qrt_df.loc[
        (qrt_df["tp"] == "QTD")
        & (qrt_df["btn"] == "Корректировки"),
        "amount"
    ].sum()

    diff_abs = total_cur - total_prev
    diff_pers = diff_abs / total_prev * 100 if total_prev else 0

    df_cur_reven = get_data_by_date(start=start_year, end=end_date)
    amount_vatless = df_cur_reven["amount_vatless"].sum()
    share_costs = total_cur / amount_vatless * 100 if amount_vatless else 0

    trend_word = "увеличились" if diff_abs < 0 else "уменьшились"

    return dmc.Paper(
        children=[
            dmc.Group(
                [
                    dmc.ThemeIcon(
                        DashIconify(
                            icon="streamline-stickies-color:add-device-duo",
                            width=36,
                        ),
                        size="sm",
                        radius="md",
                        color="red",
                        variant="light",
                    ),
                    dmc.Title(
                        "Расходы на реализацию".upper(),
                        order=4,
                    ),
                ],
                gap="xs",
                mb=4,
            ),

            dmc.Group(
                [
                    dmc.Stack(
                        [
                            dmc.Text(
                                fmt_mln(total_cur),
                                size="34px",
                                fw=900,
                                c="#FF4D4F",
                                style={"lineHeight": 1},
                            ),
                            dmc.Text(
                                "Расходы YTD без НДС",
                                size="xs",
                                c="dimmed",
                                tt="uppercase",
                                fw=500,
                            ),
                        ],
                        gap=4,
                        style={"minWidth": "240px"},
                    ),

                    dmc.Divider(
                        orientation="vertical",
                        size="sm",
                        style={"height": "60px"},
                    ),

                    dmc.Stack(
                        [
                            dmc.Text(
                                fmt_mln(total_current_quarter),
                                size="34px",
                                fw=900,
                                c="#FF4D4F",
                                style={"lineHeight": 1},
                            ),
                            dmc.Text(
                                "Расходы QTD без НДС",
                                size="xs",
                                c="dimmed",
                                tt="uppercase",
                                fw=500,
                            ),
                        ],
                        gap=4,
                        style={"minWidth": "240px"},
                    ),

                    dmc.Divider(
                        orientation="vertical",
                        size="sm",
                        style={"height": "60px"},
                    ),

                    dmc.Stack(
                        [
                    dmc.Text(
                            f"За период с {start_year.strftime('%d.%m.%Y')} "
                            f"по {end_date.strftime('%d.%m.%Y')} "
                            f"расходы на реализацию {trend_word} на "
                            f"{fmt_num(abs(diff_abs))} ₽ или на "
                            f"{abs(diff_pers):,.1f}%. "
                            f"Доля расходов в выручке без НДС составляет "
                            f"{abs(share_costs):,.1f}%.",
                            size="xs",
                            c="dimmed",
                            fw=400,
                            style={"lineHeight": 1.45},
                        ),
                      
                            dmc.Badge(
                                f"{'Рост' if diff_abs < 0 else 'Снижение'} к прошлому году",
                                color="red" if diff_abs < 0 else "green",
                                variant="light",
                                size="xs",
                                radius="sm",
                            ),
                        ],
                        gap=6,
                        style={
                            "flex": 1,
                            "minWidth": "360px",
                        },
                    ),
                ],
                align="center",
                gap="md",
                wrap="nowrap",
            ),

            dmc.Text(
                f"* Из анализа исключены корректировки Wildberries: "
                f"YTD {fmt_mln(corr_ytd)}, QTD {fmt_mln(corr_qtd)}.",
                size="10px",
                c="dimmed",
                ta="right",
                mt=4,
            ),
        ],
        radius="md",
        p="sm",
        shadow="xs",
        withBorder=True,
        style={
            "backgroundColor": "white",
            "marginBottom": "10px",
        },
    )


def layout(report=None, filters=None):
    ytd_df = get_ytd_table()
    ytd_df = ytd_df[ytd_df["btn"] != "Корректировки"]

    qrt_df = get_qrt_table()
    qrt_df = qrt_df[qrt_df["btn"] != "Корректировки"]

    return [
        dmc.Container(
            [
                cost_text(),
                dmc.SimpleGrid(
                    cols=2,
                    spacing="md",
                    children=[
                        costs_table(
                            ytd_df,
                            title=f"YTD {today.year} vs {today.year - 1}",
                            unit="₽",
                        ),
                        costs_table(
                            qrt_df,
                            title=f"{current_quarter_name} vs {past_quarter_name}",
                            unit="₽",
                        ),
                    ],
                ),
            ],
            fluid=True,
            p=0,
            style={
                "width": "1280px",
                "height": "720px",
                "overflow": "hidden",
            },
        ),
    ]