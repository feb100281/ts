# app/misc.py
import dash_mantine_components as dmc
from dash_iconify import DashIconify
import pandas as pd
import numpy as np

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
    
    
    
    
def breakdown_cards(
    df:pd.DataFrame,
    title: str,  
    subtitle: str,
    total_column, 
    name_column, 
    color,
    icon
    ):
    rows = []
    for _, row in df.iterrows():
        value_str = f"{row[total_column]:,.0f}₽".replace(",", " ")
        rows.append(
            dmc.TableTr([         
                dmc.TableTd(row[name_column], style={"fontWeight": 500}),       
                dmc.TableTd(value_str, style={"textAlign": "right"}),
            ])
        )
    
    titles = dmc.Blockquote(
    children=[
        dmc.Title(title,order=2, c='red'),
        dmc.Text(subtitle, c='dimmed', size='xs')        
    ],   
    
    icon=DashIconify(icon=icon, width=30),
    color=color,
    )
    
    
    return dmc.Paper(
        p="md",
        radius="md",
        withBorder=True,
        bg="white",
        children=[
            titles,
            dmc.Divider(size="xs", mb="sm"),
            dmc.Table(
                [
          
                    dmc.TableTbody(rows),
                ],
                striped=True,
                highlightOnHover=True,
                withTableBorder=False,
            ),
            
            
            
            ],)
    
    
    


def costs_table(
    df: pd.DataFrame,
    title: str = "Расходы на реализацию",
    value_prefix: str = "₽",
    unit: str = "₽",
    show_percent: bool = False,
):
    table_df = df.copy()

    pivot = table_df.pivot_table(
        index=["cat", "btn"],
        values="amount",
        columns="tp",
        aggfunc="sum",
    ).fillna(0)

    if "YTD" in pivot.columns and "PY YTD" in pivot.columns:
        pivot["Δ YTD"] = pivot["YTD"] - pivot["PY YTD"]
        if show_percent:
            pivot["% YTD"] = (pivot["Δ YTD"] / pivot["PY YTD"].replace(0, np.nan)) * 100

    if "QTD" in pivot.columns and "PY QTD" in pivot.columns:
        pivot["Δ QTD"] = pivot["QTD"] - pivot["PY QTD"]
        if show_percent:
            pivot["% QTD"] = (pivot["Δ QTD"] / pivot["PY QTD"].replace(0, np.nan)) * 100
            
            
    
    
    # правильный порядок колонок
    wanted_order = [
        "YTD",
        "PY YTD",
        "Δ YTD",
        "% YTD",
        "QTD",
        "PY QTD",
        "Δ QTD",
        "% QTD",
    ]

    existing_order = [col for col in wanted_order if col in pivot.columns]
    other_cols = [col for col in pivot.columns if col not in existing_order]

    pivot = pivot[existing_order + other_cols]

    table_df_reset = pivot.reset_index()



    table_df_reset = table_df_reset.rename(
        columns={
            "cat": "Категория",
            "btn": "Статья расходов",
            "YTD": f"YTD, {unit}",
            "PY YTD": f"PY YTD, {unit}",
            "Δ YTD": f"Δ YTD, {unit}",
            "QTD": f"QTD, {unit}",
            "PY QTD": f"PY QTD, {unit}",
            "Δ QTD": f"Δ QTD, {unit}",
        }
    )

    if not show_percent:
        table_df_reset = table_df_reset.drop(
            columns=[c for c in table_df_reset.columns if str(c).startswith("%")],
            errors="ignore",
        )

    def fmt_num(value):
        if pd.isna(value):
            return "—"
        if value == 0:
            return "0"
        return f"{value:,.0f}".replace(",", " ")

    def fmt_pct(value):
        if pd.isna(value):
            return "—"
        return f"{value:,.1f}%".replace(",", " ")

    def is_number(value):
        return isinstance(value, (int, float, np.integer, np.floating))

    text_cols = [
        col for col in table_df_reset.columns
        if not pd.api.types.is_numeric_dtype(table_df_reset[col])
    ]

    percent_cols = [
        col for col in table_df_reset.columns
        if str(col).startswith("%")
    ]

    first_text_col = text_cols[0] if len(text_cols) > 0 else table_df_reset.columns[0]
    second_text_col = text_cols[1] if len(text_cols) > 1 else None

    header = dmc.TableThead(
        dmc.TableTr(
            [
                dmc.TableTh(
                    col,
                    style = {
                            "textAlign": "left" if col in text_cols else "right",
                            "fontVariantNumeric": "tabular-nums",
                            "whiteSpace": "nowrap" if col not in text_cols else "normal",
                            "overflowWrap": "break-word",
                        }
                )
                for col in table_df_reset.columns
            ]
        )
    )

    body_rows = []

    for category, group in table_df_reset.groupby(first_text_col):
        if body_rows:
            body_rows.append(
                dmc.TableTr(
                    [
                        dmc.TableTd(
                            "",
                            style={"borderTop": "1px solid #E7F1ED"},
                        )
                        for _ in table_df_reset.columns
                    ]
                )
            )

        for idx, (_, row) in enumerate(group.iterrows()):
            cells = []

            for col in table_df_reset.columns:
                value = row[col]

                if col in percent_cols:
                    display_value = fmt_pct(value)
                elif is_number(value):
                    display_value = fmt_num(value)
                else:
                    display_value = value

                style = {
                    "textAlign": "left" if col in text_cols else "right",
                    "fontVariantNumeric": "tabular-nums",
                    "whiteSpace": "nowrap",
                }

                if col == first_text_col:
                    style.update(
                        {
                            "fontWeight": 600,
                            "backgroundColor": "#F8F9FA",
                        }
                    )

                    if idx != 0:
                        display_value = ""

                if col in percent_cols and is_number(value):
                    if value > 0:
                        style["color"] = "#067647"
                        style["fontWeight"] = 600
                    elif value < 0:
                        style["color"] = "#B42318"
                        style["fontWeight"] = 600

                if str(col).startswith("Δ") and is_number(value):
                    style["fontWeight"] = 700
                    style["color"] = "#067647" if value >= 0 else "#B42318"

                elif is_number(value) and value < 0 and col not in percent_cols:
                    style["color"] = "#B42318"

                cells.append(dmc.TableTd(display_value, style=style))

            body_rows.append(dmc.TableTr(cells))

    total_cells = []

    for col in table_df_reset.columns:
        style = {
            "fontWeight": 800,
            "borderTop": "2px solid #2F6656",
            "textAlign": "left" if col in text_cols else "right",
        }

        if col == first_text_col:
            total_cells.append(dmc.TableTd("ИТОГО", style=style))

        elif col in text_cols or col in percent_cols:
            total_cells.append(dmc.TableTd("", style=style))

        else:
            col_sum = pd.to_numeric(table_df_reset[col], errors="coerce").sum()
            total_cells.append(dmc.TableTd(fmt_num(col_sum), style=style))

    body_rows.append(dmc.TableTr(total_cells))

    return dmc.Paper(
        children=[
            dmc.Group(
                [
                    DashIconify(
                        icon="solar:graph-bold-duotone",
                        width=22,
                        color="#1F5E4E",
                    ),
                    dmc.Title(title, order=5, c="#1F5E4E"),
                ],
                gap="xs",
                mb="xs",
            ),
            dmc.Table(
                [header, dmc.TableTbody(body_rows)],
                striped=False,
                highlightOnHover=True,
                withTableBorder=True,
                withColumnBorders=False,
                verticalSpacing=2,
                horizontalSpacing=4,
                style={
                    "fontSize": "11px",
                    "tableLayout": "fixed",
                    "width": "100%",
                },
            ),
            dmc.Text(
                f"Суммы указаны в {unit}",
                size="xs",
                c="dimmed",
                mt="xs",
                ta="right",
            ),
        ],
        p="sm",
        radius="md",
        withBorder=True,
        shadow="xs",
        style={
            "backgroundColor": "white",
            "height": "100%",
            "overflow": "hidden",
        },
    )