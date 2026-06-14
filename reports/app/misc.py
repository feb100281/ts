# app/misc.py
import dash_mantine_components as dmc
from dash_iconify import DashIconify
import pandas as pd

""" 
Сюда давай пихать функции которые используют все слайды
"""




# Напимер карточки c paper
def metric_card_adj(title, value, icon, color, subtitle=None, badge=None, badge_color="green"):
    return dmc.Paper(
        p="md",
        radius="md",
        withBorder=True,
        shadow="xs",
        bg="white",
        children=[
            dmc.Group(
                justify="space-between",
                mb="xs",
                children=[
                    dmc.Text(title, size="xs", fw=600, c="dimmed", tt="uppercase"),
                    dmc.ThemeIcon(
                        size="lg", 
                        radius="md", 
                        variant="light", 
                        color=color,
                        children=[DashIconify(icon=icon, width=26)]
                    )
                ]
            ),
            dmc.Text(value, size="xl", fw=800, c=color),
            dmc.Text(subtitle, size="xs", c="dimmed", mt="xs") if subtitle else None,
            dmc.Badge(
                badge,
                color=badge_color,
                variant="light",
                size="sm",
                mt="xs"
            ) if badge else None
        ]
    )

def paper_card(
    title,
    content=None,
    **kwargs,
):

    children = [
        dmc.Group(
            [title],
        ),
        dmc.Space(h=5),
        dmc.Divider(size="xs"),
        dmc.Space(h=10),
    ]

    if content is not None:
        children.append(content)

    return dmc.Paper(
        p="sm",
        radius="md",
        shadow="xs",
        withBorder=True,
        children=children,
        **kwargs,
    )


def fancy_numbers(
    big_number, description, icon: DashIconify = None, badge=None, **kwargs
):
    children = [
        icon,
        dmc.Stack(
            [
                dmc.Group(
                    [
                        dmc.Text(
                            big_number,
                            size="lg",
                        ),
                        badge,
                    ],
                    align="flex-start",
                    gap=2,
                ),
                dmc.Text(description, size="xs", c="dimmed"),
            ],
            gap=0,
        ),
    ]
    return dmc.Group(
        children=children,
        # justify="space-between",
        align="flex-start",
        **kwargs,
    )
    
    








# def fancy_table(
#     df: pd.DataFrame,
#     title: str = None,
#     precision: int = 0,
#     highlight_last_col: bool = False,
# ):

#     table_df = df.copy().reset_index()

#     table_df = table_df.fillna(0)

#     for col in table_df.columns:

#         if pd.api.types.is_numeric_dtype(
#             table_df[col]
#         ):
#             table_df[col] = table_df[col].map(
#                 lambda x:
#                 f"{x:,.{precision}f}"
#             )

#     header = dmc.TableThead(
#         dmc.TableTr(
#             [
#                 dmc.TableTh(str(col))
#                 for col in table_df.columns
#             ]
#         )
#     )

#     body = dmc.TableTbody(
#         [
#             dmc.TableTr(
#                 [
#                     dmc.TableTd(value)
#                     for value in row
#                 ]
#             )
#             for row in table_df.values
#         ]
#     )

#     table = dmc.Table(
#         [
#             header,
#             body,
#         ],
#         striped=True,
#         highlightOnHover=True,
#         withTableBorder=True,
#         withColumnBorders=True,
#         horizontalSpacing="md",
#         verticalSpacing="2",

#     )

#     if title:
#         return dmc.Stack(
#             [
#                 dmc.Title(
#                     title,
#                     order=4,
#                 ),
#                 table,
#             ],
#             gap="xs",
#         )

#     return table


def fancy_table(
    df: pd.DataFrame,
    title: str = None,
    precision: int = 0,
    highlight_last_col: bool = False,
):

    table_df = df.copy().reset_index()
    table_df = table_df.fillna(0)

    for col in table_df.columns:
        if pd.api.types.is_numeric_dtype(table_df[col]):
            table_df[col] = table_df[col].map(
                lambda x: f"{x:,.{precision}f}"
            )

    last_col_idx = len(table_df.columns) - 1

    header = dmc.TableThead(
        dmc.TableTr(
            [
                dmc.TableTh(
                    str(col),
                    style={
                        "backgroundColor": "#E7F1ED",
                        "fontWeight": 800,
                    } if highlight_last_col and i == last_col_idx else {},
                )
                for i, col in enumerate(table_df.columns)
            ]
        )
    )

    body = dmc.TableTbody(
        [
            dmc.TableTr(
                [
                    dmc.TableTd(
                        value,
                        style={
                            "backgroundColor": "#E7F1ED",
                            "fontWeight": 700,
                        } if highlight_last_col and i == last_col_idx else {},
                    )
                    for i, value in enumerate(row)
                ]
            )
            for row in table_df.values
        ]
    )

    table = dmc.Table(
        [
            header,
            body,
        ],
        striped=True,
        highlightOnHover=True,
        withTableBorder=True,
        withColumnBorders=True,
        horizontalSpacing="md",
        verticalSpacing="2",
    )

    if title:
        return dmc.Stack(
            [
                dmc.Title(
                    title,
                    order=4,
                ),
                table,
            ],
            gap="xs",
        )

    return table



def accounting_table(
    df: pd.DataFrame,
    title: str = "Сводный финансовый результат",
):
    table_df = df.copy().reset_index()

    first_col = table_df.columns[0]
    table_df = table_df.rename(columns={first_col: "Показатель"})

    expense_rows = ["НДС", "С/сть", "Комиссия WB", "Расходы WB"]
    profit_rows = ["Валовая прибыль"]

    def fmt_num(value):
        if pd.isna(value):
            return "—"
        return f"{value:,.2f}".replace(",", " ")

    def fmt_pct(value):
        if pd.isna(value):
            return "—"
        return f"{value:,.1f}%".replace(",", " ")

    def cell_style(row_name, col_name, value):
        style = {
            "textAlign": "right",
            "fontVariantNumeric": "tabular-nums",
            "whiteSpace": "nowrap",
        }

        if col_name == "Показатель":
            style.update({
                "textAlign": "left",
                "fontWeight": 600,
            })

        if row_name in expense_rows and col_name != "Показатель":
            style["color"] = "#B42318"

        if row_name in profit_rows:
            style["fontWeight"] = 700

        if str(col_name).startswith("Δ") and pd.notna(value):
            style["fontWeight"] = 700
            style["color"] = "#067647" if value >= 0 else "#B42318"

        return style

    header = dmc.TableThead(
        dmc.TableTr(
            [
                dmc.TableTh(
                    col,
                    style={
                        "textAlign": "left" if col == "Показатель" else "right",
                        "fontWeight": 700,
                        "backgroundColor": "#E7F1ED",
                        "color": "#1F5E4E",
                        "whiteSpace": "nowrap",
                    },
                )
                for col in table_df.columns
            ]
        )
    )

    body_rows = []

    for _, row in table_df.iterrows():
        row_name = row["Показатель"]

        cells = []

        for col in table_df.columns:
            value = row[col]

            if col == "Показатель":
                display_value = value
            elif str(col).startswith("%"):
                display_value = fmt_pct(value)
            else:
                display_value = fmt_num(value)

            cells.append(
                dmc.TableTd(
                    display_value,
                    style=cell_style(row_name, col, value),
                )
            )

        row_style = {}

        if row_name in profit_rows:
            row_style = {
                "backgroundColor": "#DCECE6",
                "borderTop": "2px solid #2F6656",
            }

        body_rows.append(
            dmc.TableTr(cells, style=row_style)
        )

    return dmc.Paper(
        children=[
            dmc.Group(
                [
                    DashIconify(
                        icon="solar:calculator-bold-duotone",
                        width=28,
                    ),
                    dmc.Title(title, order=4, c="#1F5E4E"),
                ],
                gap="sm",
                mb="md",
            ),
            dmc.Table(
                [header, dmc.TableTbody(body_rows)],
                striped=True,
                highlightOnHover=True,
                withTableBorder=True,
                withColumnBorders=False,
                verticalSpacing="2",
                horizontalSpacing="xs",
            ),
            dmc.Text(
                "Суммы указаны в млн ₽",
                size="xs",
                c="dimmed",
                mt="xs",
                ta="right",
            ),
        ],
        p="lg",
        radius="md",
        withBorder=True,
        shadow="xs",
        style={"backgroundColor": "white"},
    )