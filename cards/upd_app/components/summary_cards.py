# cards/upd_app/components/summary_cards.py
import pandas as pd
import dash_mantine_components as dmc


def fmt_money(value):
    if pd.isna(value):
        return "0.00"
    return f"{value:,.2f}".replace(",", " ")


def fmt_int(value):
    if pd.isna(value):
        return "0"
    return f"{int(value):,}".replace(",", " ")


def metric_card(title, value, subtitle=None, accent=False):
    return dmc.Paper(
        [
            dmc.Text(
                title,
                size="sm",
                fw=600,
                c="#5f6b7a",
                style={
                    "whiteSpace": "nowrap",
                    "overflow": "hidden",
                    "textOverflow": "ellipsis",
                },
            ),
            dmc.Text(
                value,
                fw=800,
                style={
                    "fontSize": "20px",
                    "lineHeight": "1.15",
                    "letterSpacing": "-0.5px",
                    "whiteSpace": "nowrap",
                },
            ),
            dmc.Text(
                subtitle,
                size="xs",
                c="#7b8794",
                style={
                    "whiteSpace": "nowrap",
                    "overflow": "hidden",
                    "textOverflow": "ellipsis",
                },
            ) if subtitle else None,
        ],
        p="md",
        radius="xs",
        withBorder=True,
        shadow="xs",
        style={
            "height": "112px",
            "background": "#f8fafc" if not accent else "#f1f5f9",
            "border": "1px solid #d9e1ea",
            "display": "flex",
            "flexDirection": "column",
            "justifyContent": "center",
            "gap": "6px",
        },
    )


def build_upd_summary_cards(df: pd.DataFrame):
    # Данные по обычной себестоимости
    price = pd.to_numeric(df["upd_price_vatless"], errors="coerce").dropna()
    qty = pd.to_numeric(df["upd_qty"], errors="coerce").fillna(0)
    amount_vatadd = pd.to_numeric(df["upd_amount_vatadd"], errors="coerce").fillna(0)
    amount_vatless = pd.to_numeric(df["upd_amount_vatless"], errors="coerce").fillna(0)
    

    total_qty = qty.sum()
    total_amount_vatadd = amount_vatadd.sum()
    total_amount_vatless = amount_vatless.sum()

    if price.empty:
        min_price = avg_price = median_price = max_price = 0
    else:
        min_price = price.min()
        avg_price = price.mean()
        median_price = price.median()
        max_price = price.max()

    # Данные по управленческой себестоимости
    man_cost = pd.to_numeric(df["man_cost_per_unit"], errors="coerce").dropna()
    
    if man_cost.empty:
        min_man_cost = avg_man_cost = median_man_cost = max_man_cost = 0
    else:
        min_man_cost = man_cost.min()
        avg_man_cost = man_cost.mean()
        median_man_cost = man_cost.median()
        max_man_cost = man_cost.max()

    # Рассчитаем общую управленческую себестоимость
    total_man_cost = (man_cost * qty.loc[man_cost.index]).sum() if not man_cost.empty else 0

    return dmc.Stack(
        [
            dmc.Group(
                [
                    dmc.Title("Сводка по УПД", order=4),
                ],
                justify="space-between",
                align="center",
            ),

            # Ряд 1: Обычная себестоимость
            dmc.SimpleGrid(
                cols={"base": 1, "sm": 2, "lg": 3, "xl": 6},
                spacing="md",
                children=[
                    metric_card(
                        title="Общая сумма УПД",
                        value=f"{fmt_money(total_amount_vatadd)} ₽",
                        subtitle="с НДС",
                        accent=True,
                    ),
                    
                    
                    metric_card(
                        title="Общая сумма УПД",
                        value=f"{fmt_money(total_amount_vatless)} ₽",
                        subtitle="без НДС",
                        accent=True,
                    ),
                    
               
                    metric_card(
                        title="Мин. цена (бух)",
                        value=f"{fmt_money(min_price)} ₽",
                        subtitle="за единицу без НДС",
                    ),
                    metric_card(
                        title="Средняя цена (бух)",
                        value=f"{fmt_money(avg_price)} ₽",
                        subtitle="за единицу без НДС",
                    ),
                    metric_card(
                        title="Медианная цена (бух)",
                        value=f"{fmt_money(median_price)} ₽",
                        subtitle="за единицу без НДС",
                    ),
                    metric_card(
                        title="Макс. цена (бух)",
                        value=f"{fmt_money(max_price)} ₽",
                        subtitle="за единицу без НДС",
                    ),
                ],
            ),

            # Ряд 2: Управленческая себестоимость
            dmc.SimpleGrid(
                cols={"base": 1, "sm": 2, "lg": 3, "xl": 6},
                spacing="md",
                children=[
                    metric_card(
                        title="Общая упр. себестоимость",
                        value=f"{fmt_money(total_man_cost)} ₽",
                        subtitle="по всем позициям",
                        accent=True,
                    ),
                    metric_card(
                        title="Количество товаров",
                        value=fmt_int(total_qty),
                        subtitle="единиц",
                        accent=True,
                    ),
                    
                    metric_card(
                        title="Мин. упр. себес.",
                        value=f"{fmt_money(min_man_cost)} ₽",
                        subtitle="за единицу",
                    ),
                    metric_card(
                        title="Средняя упр. себес.",
                        value=f"{fmt_money(avg_man_cost)} ₽",
                        subtitle="за единицу",
                    ),
                    metric_card(
                        title="Медианная упр. себес.",
                        value=f"{fmt_money(median_man_cost)} ₽",
                        subtitle="за единицу",
                    ),
                    metric_card(
                        title="Макс. упр. себес.",
                        value=f"{fmt_money(max_man_cost)} ₽",
                        subtitle="за единицу",
                    ),
                ],
            ),
        ],
        gap="sm",
        mb="md",
    )