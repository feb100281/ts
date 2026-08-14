
from __future__ import annotations

from datetime import date

import pandas as pd
import dash_mantine_components as dmc
from dash import dcc

from .data import get_pricing_source
from .analytics import analyze_pricing
from .grid import pricing_grid


def fmt_money(value):
    try:
        value = float(value or 0)
    except (TypeError, ValueError):
        value = 0.0
    return f"{value:,.0f} ₽".replace(",", " ")


def metric_card(label, value, note=None):
    children = [
        dmc.Text(label, size="xs", c="dimmed", fw=600),
        dmc.Text(value, size="xl", fw=800),
    ]

    if note:
        children.append(
            dmc.Text(note, size="xs", c="dimmed")
        )

    return dmc.Paper(
        withBorder=True,
        radius=0,
        p="md",
        children=children,
    )


def _records(frame):
    if frame is None or frame.empty:
        return []

    safe = frame.copy()

    safe = safe.astype(object).where(
        pd.notna(safe),
        None,
    )

    records = safe.to_dict("records")

    for row in records:
        for key, value in list(row.items()):
            if (
                value is not None
                and hasattr(value, "isoformat")
                and not isinstance(value, str)
            ):
                try:
                    row[key] = value.isoformat()
                except Exception:
                    pass

    return records


class PricingStrategyDashboard:
    def layout(
        self,
        report_date,
        cat_list=None,
        brand_list=None,
        gender_list=None,
    ):
        report_date = date.fromisoformat(
            str(report_date)[:10]
        )

        source = get_pricing_source(
            report_date=report_date,
            cat_list=cat_list,
            brand_list=brand_list,
            gender_list=gender_list,
        )

        analysis = analyze_pricing(source)

        recommendations = analysis["recommendations"]
        scenarios = analysis["scenarios"]
        history = analysis["history"]
        summary = analysis.get("summary", {})

        rec_records = _records(recommendations)
        scenario_records = _records(scenarios)
        history_records = _records(history)

        store_payload = {
            "report_date": str(analysis["report_date"]),
            "history_start": str(analysis["history_start"]),
            "stock_date": (
                str(analysis["stock_date"])
                if analysis.get("stock_date")
                else None
            ),
            "recommendations": rec_records,
            "scenarios": scenario_records,
            "history": history_records,
        }

        if recommendations.empty:
            return dmc.Alert(
                title="Нет данных",
                color="yellow",
                radius=0,
                children=(
                    "Для выбранных фильтров не найдено "
                    "товаров с ценой или продажами."
                ),
            )

        stock_date_label = (
            analysis["stock_date"].strftime("%d.%m.%Y")
            if analysis.get("stock_date")
            else "—"
        )

        return dmc.Stack(
            gap="md",
            children=[
                dcc.Store(
                    id="pricing-strategy-store",
                    data=store_payload,
                ),

                dcc.Download(
                    id="pricing-strategy-download"
                ),

                dmc.Group(
                    justify="space-between",
                    align="flex-start",
                    children=[
                        dmc.Box(
                            children=[
                                dmc.Title(
                                    "Управление ценами",
                                    order=2,
                                    fw=800,
                                ),
                                dmc.Text(
                                    (
                                        "Цена покупателя · наша цена · "
                                        "FIFO-маржа · остаток · "
                                        "эластичность · рекомендация"
                                    ),
                                    size="sm",
                                    c="dimmed",
                                ),
                                dmc.Text(
                                    (
                                        f"Дата анализа: "
                                        f"{report_date:%d.%m.%Y} · "
                                        f"остатки: {stock_date_label}"
                                    ),
                                    size="xs",
                                    c="dimmed",
                                ),
                            ]
                        ),

                        dmc.Button(
                            "Выгрузить Excel",
                            id="pricing-strategy-export",
                            radius=0,
                            variant="outline",
                        ),
                    ],
                ),

                dmc.SimpleGrid(
                    cols={
                        "base": 1,
                        "sm": 2,
                        "lg": 6,
                    },
                    spacing="sm",
                    children=[
                        metric_card(
                            "Артикулов",
                            f"{summary.get('products', 0):,}".replace(",", " "),
                        ),
                        metric_card(
                            "Требуют действия",
                            f"{summary.get('action_products', 0):,}".replace(",", " "),
                        ),
                        metric_card(
                            "Clearance",
                            f"{summary.get('clearance_products', 0):,}".replace(",", " "),
                        ),
                        metric_card(
                            "Запас > 180 дней",
                            f"{summary.get('high_stock_products', 0):,}".replace(",", " "),
                        ),
                        metric_card(
                            "Остаток, шт.",
                            f"{summary.get('stock_units', 0):,.0f}".replace(",", " "),
                        ),
                        metric_card(
                            "Потенциал маржи / день",
                            fmt_money(
                                summary.get(
                                    "margin_upside_day",
                                    0,
                                )
                            ),
                            "модельный сценарий",
                        ),
                    ],
                ),

                dmc.Alert(
                    color="blue",
                    radius=0,
                    title="Методология",
                    children=(
                        "Спрос оценивается по фактической цене реализации WB "
                        "покупателю (retail_amount). Экономика — по нашей "
                        "выручке без НДС, управленческой FIFO-себестоимости "
                        "и комиссии WB. Маркетинг, штрафы и прочие недельные "
                        "расходы WB в ценовую маржу не включаются."
                    ),
                ),

                pricing_grid(rec_records),

                dmc.Divider(),

                dmc.Box(
                    id="pricing-strategy-detail",
                    children=dmc.Text(
                        (
                            "Выберите NM ID в таблице — "
                            "откроются сценарии цены и история."
                        ),
                        size="sm",
                        c="dimmed",
                    ),
                ),
            ],
        )
