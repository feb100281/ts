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

    price = pd.to_numeric(df["upd_price_vatless"], errors="coerce").dropna()
    qty = pd.to_numeric(df["upd_qty"], errors="coerce").fillna(0)
    amount_vatadd = pd.to_numeric(df["upd_amount_vatadd"], errors="coerce").fillna(0)

    total_qty = qty.sum()
    total_amount_vatadd = amount_vatadd.sum()

    if price.empty:
        min_price = avg_price = median_price = max_price = 0
    else:
        min_price = price.min()
        avg_price = price.mean()
        median_price = price.median()
        max_price = price.max()

    return dmc.Stack(
        [
            dmc.Group(
                [
                    dmc.Title("Сводка по УПД", order=4),
                    
                ],
                justify="space-between",
                align="center",
            ),

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
                        title="Количество товаров",
                        value=fmt_int(total_qty),
                        subtitle="единиц",
                        accent=True,
                    ),
                    metric_card(
                        title="Мин. цена",
                        value=f"{fmt_money(min_price)} ₽",
                        subtitle="за единицу без НДС",
                    ),
                    metric_card(
                        title="Средняя цена",
                        value=f"{fmt_money(avg_price)} ₽",
                        subtitle="за единицу без НДС",
                    ),
                    metric_card(
                        title="Медианная цена",
                        value=f"{fmt_money(median_price)} ₽",
                        subtitle="за единицу без НДС",
                    ),
                    metric_card(
                        title="Макс. цена",
                        value=f"{fmt_money(max_price)} ₽",
                        subtitle="за единицу без НДС",
                    ),
                ],
            ),
        ],
        gap="sm",
        mb="md",
    )