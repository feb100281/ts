# gear/app/daily_sales/pricing_strategy/layout.py

from __future__ import annotations

import pandas as pd
import dash_mantine_components as dmc
from dash import dcc

from .charts import pricing_charts_section
from .grids import portfolio_grid, products_grid


def _records(frame):
    if frame is None or frame.empty:
        return []
    work = frame.astype(object).where(pd.notna(frame), None)
    records = work.to_dict("records")
    for row in records:
        for key, value in list(row.items()):
            if value is not None and hasattr(value, "isoformat") and not isinstance(value, str):
                try:
                    row[key] = value.isoformat()
                except Exception:
                    pass
    return records


def _fmt_number(value, digits=0):
    try:
        value = float(value or 0)
    except (TypeError, ValueError):
        value = 0.0
    return f"{value:,.{digits}f}".replace(",", " ")


def _fmt_money(value):
    return f"{_fmt_number(value)} ₽"


def _metric_card(*, label, value, icon, accent, note=None):
    children = [
        dmc.Group(
            justify="space-between",
            align="flex-start",
            wrap="nowrap",
            children=[
                dmc.Box(
                    style={"minWidth": 0},
                    children=[
                        dmc.Text(
                            label,
                            size="xs",
                            fw=700,
                            c="dimmed",
                            tt="uppercase",
                            style={"letterSpacing": "0.04em"},
                        ),
                        dmc.Text(
                            value,
                            size="28px",
                            fw=800,
                            mt=4,
                            style={"lineHeight":"1.05", "whiteSpace":"nowrap"},
                        ),
                    ],
                ),
                dmc.Box(
                    style={
                        "width":"42px",
                        "height":"42px",
                        "minWidth":"42px",
                        "display":"flex",
                        "alignItems":"center",
                        "justifyContent":"center",
                        "backgroundColor":f"{accent}14",
                        "border":f"1px solid {accent}35",
                        "color":accent,
                        "fontSize":"19px",
                        "fontWeight":"800",
                    },
                    children=icon,
                ),
            ],
        )
    ]
    if note:
        children.append(dmc.Text(note, size="xs", c="dimmed", mt=7))

    return dmc.Paper(
        withBorder=True,
        radius=0,
        p="md",
        style={
            "minHeight":"126px",
            "borderTop":f"4px solid {accent}",
            "background":f"linear-gradient(135deg,#FFFFFF 0%,{accent}0D 100%)",
        },
        children=children,
    )


def pricing_strategy_controls():
    return dmc.Group(
        gap="xs",
        children=[
            dmc.Button(
                "Управление ценами",
                id="pricing-strategy-open",
                radius=0,
                variant="filled",
                color="indigo",
                leftSection=dmc.Text("₽", fw=900),
            ),
            dcc.Store(id="pricing-strategy-store"),
            dcc.Download(id="pricing-strategy-download"),
            dmc.Modal(
                id="pricing-strategy-modal",
                opened=False,
                withCloseButton=False,
                fullScreen=True,
                padding="md",
                zIndex=10000,
                children=[
                    dmc.Group(
                        justify="space-between",
                        align="center",
                        mb="sm",
                        children=[
                            dmc.Box(
                                children=[
                                    dmc.Title("Управление ценами и маржой", order=2, fw=800),
                                    dmc.Text(
                                        "Остатки → спрос → FIFO-маржа → рекомендованная цена",
                                        size="sm",
                                        c="dimmed",
                                    ),
                                ]
                            ),
                            dmc.Group(
                                gap="xs",
                                children=[
                                    dmc.Button(
                                        "Выгрузить Excel",
                                        id="pricing-strategy-export",
                                        radius=0,
                                        variant="outline",
                                    ),
                                    dmc.Button(
                                        "Закрыть",
                                        id="pricing-strategy-close",
                                        radius=0,
                                        color="gray",
                                        variant="light",
                                    ),
                                ],
                            ),
                        ],
                    ),
                    dmc.Divider(mb="md"),
                    dmc.Box(
                        id="pricing-strategy-body",
                        children=dmc.Text(
                            "Нажмите «Управление ценами», чтобы построить анализ.",
                            c="dimmed",
                        ),
                    ),
                ],
            ),
        ],
    )


def build_pricing_body(analysis):
    rec = analysis["recommendations"]
    portfolio = analysis["portfolio"]
    summary = analysis.get("summary", {})

    if rec.empty:
        return dmc.Alert(
            title="Нет данных",
            color="yellow",
            radius=0,
            children="Для выбранных фильтров нет товаров с общим остатком WB + FBS + в пути.",
        )

    report_date = analysis["report_date"]
    wb_date = analysis.get("wb_date")
    fbs_date = analysis.get("fbs_date")
    stale = (
        (wb_date is not None and wb_date < report_date)
        or (fbs_date is not None and fbs_date < report_date)
    )
    wb_label = wb_date.strftime("%d.%m.%Y") if wb_date else "нет данных"
    fbs_label = fbs_date.strftime("%d.%m.%Y") if fbs_date else "нет данных"

    products_count = int(summary.get("products", 0) or 0)
    action_products = int(summary.get("action_products", 0) or 0)
    clearance_products = int(summary.get("clearance_products", 0) or 0)
    raise_products = int(summary.get("raise_products", 0) or 0)
    total_stock = float(summary.get("stock_units", 0) or 0)
    margin_upside = float(summary.get("margin_upside_day", 0) or 0)
    wb_stock = float(summary.get("wb_stock_units", rec["wb_stock"].sum() if "wb_stock" in rec.columns else 0) or 0)
    fbs_stock = float(summary.get("fbs_stock_units", rec["fbs_stock"].sum() if "fbs_stock" in rec.columns else 0) or 0)
    transit_stock = float(summary.get("in_transit_units", rec["in_transit"].sum() if "in_transit" in rec.columns else 0) or 0)
    action_share = action_products / products_count * 100 if products_count else 0

    return dmc.Stack(
        gap="lg",
        children=[
            dmc.Alert(
                title="Использованы последние доступные остатки" if stale else "Дата остатков",
                color="yellow" if stale else "blue",
                radius=0,
                children=(
                    f"Дата анализа: {report_date:%d.%m.%Y} · "
                    f"WB: {wb_label} · FBS: {fbs_label}. "
                    "В модели используется весь товарный запас: "
                    "WB + FBS + в пути к клиенту + в пути от клиента."
                ),
            ),
            dmc.SimpleGrid(
                cols={"base":2, "md":3, "xl":6},
                spacing="sm",
                children=[
                    _metric_card(
                        label="Артикулов с остатком",
                        value=_fmt_number(products_count),
                        icon="▦",
                        accent="#2563EB",
                        note=f"WB {_fmt_number(wb_stock)} · FBS {_fmt_number(fbs_stock)}",
                    ),
                    _metric_card(
                        label="Требуют действия",
                        value=_fmt_number(action_products),
                        icon="!",
                        accent="#F59E0B",
                        note=f"{action_share:.0f}% ассортимента",
                    ),
                    _metric_card(
                        label="Распродажа",
                        value=_fmt_number(clearance_products),
                        icon="↓",
                        accent="#DC2626",
                        note="Избыточный / старый запас",
                    ),
                    _metric_card(
                        label="Можно повышать",
                        value=_fmt_number(raise_products),
                        icon="↑",
                        accent="#16A34A",
                        note="Есть потенциал цены",
                    ),
                    _metric_card(
                        label="Общий остаток",
                        value=_fmt_number(total_stock),
                        icon="▤",
                        accent="#7C3AED",
                        note=f"В пути {_fmt_number(transit_stock)}",
                    ),
                    _metric_card(
                        label="Потенциал маржи / день",
                        value=_fmt_money(margin_upside),
                        icon="₽",
                        accent="#0F766E",
                        note="Модельный сценарий",
                    ),
                ],
            ),
            dmc.Box(
                mt="xs",
                children=[
                    dmc.Title("Карта возможностей", order=3, fw=800),
                    dmc.Text(
                        "Где сосредоточен запас, где есть давление на цену и где изменение цены может дать максимальный эффект.",
                        size="sm",
                        c="dimmed",
                    ),
                ],
            ),
            pricing_charts_section(portfolio=portfolio, recommendations=rec),
            dmc.Box(
                mt="md",
                children=[
                    dmc.Title("1. Бренды и категории", order=3, fw=800),
                    dmc.Text(
                        "Выберите строку — ниже останутся только номенклатуры этого бренда и категории.",
                        size="sm",
                        c="dimmed",
                        mt=4,
                    ),
                ],
            ),
            portfolio_grid(_records(portfolio)),
            dmc.Group(
                justify="space-between",
                align="flex-end",
                mt="md",
                children=[
                    dmc.Box(
                        children=[
                            dmc.Title("2. Номенклатуры", order=3, fw=800),
                            dmc.Text(
                                "Конкретные NM ID, остатки, экономика и рекомендуемое ценовое действие.",
                                size="sm",
                                c="dimmed",
                            ),
                        ],
                    ),
                    dmc.Button(
                        "Показать все",
                        id="pricing-show-all",
                        radius=0,
                        variant="subtle",
                        size="xs",
                    ),
                ],
            ),
            products_grid(_records(rec)),
            dmc.Divider(),
            dmc.Box(
                id="pricing-product-detail",
                children=dmc.Text(
                    "Выберите NM ID — здесь откроются сценарии цены и история.",
                    c="dimmed",
                    size="sm",
                ),
            ),
        ],
    )
