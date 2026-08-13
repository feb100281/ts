
from __future__ import annotations

import dash_mantine_components as dmc
from dash import Input, Output, State, dcc

from .excel import build_pricing_excel


def fmt_money(value):
    try:
        value = float(value or 0)
    except (TypeError, ValueError):
        value = 0.0
    return f"{value:,.0f} ₽".replace(",", " ")


def fmt_number(value, digits=1):
    if value is None:
        return "—"

    try:
        return f"{float(value):,.{digits}f}".replace(",", " ")
    except (TypeError, ValueError):
        return "—"


def metric(label, value):
    return dmc.Paper(
        withBorder=True,
        radius=0,
        p="sm",
        children=[
            dmc.Text(
                label,
                size="xs",
                c="dimmed",
            ),
            dmc.Text(
                value,
                size="sm",
                fw=700,
            ),
        ],
    )


def scenario_table(
    rows,
    recommended_change,
):
    if not rows:
        return dmc.Text(
            "Сценарии недоступны.",
            c="dimmed",
            size="sm",
        )

    ordered = sorted(
        rows,
        key=lambda row: float(
            row.get(
                "price_change_pct",
                0,
            )
            or 0
        ),
    )

    body = []

    for row in ordered:
        change = float(
            row.get(
                "price_change_pct",
                0,
            )
            or 0
        )

        is_recommended = (
            abs(
                change
                - float(
                    recommended_change
                    or 0
                )
            )
            < 0.01
        )

        body.append(
            dmc.TableTr(
                [
                    dmc.TableTd(
                        f"{change:+.1f}%"
                    ),
                    dmc.TableTd(
                        fmt_money(
                            row.get(
                                "seller_price"
                            )
                        )
                    ),
                    dmc.TableTd(
                        fmt_money(
                            row.get(
                                "buyer_price"
                            )
                        )
                    ),
                    dmc.TableTd(
                        fmt_number(
                            row.get(
                                "projected_daily_qty"
                            ),
                            1,
                        )
                    ),
                    dmc.TableTd(
                        fmt_money(
                            row.get(
                                "projected_margin"
                            )
                        )
                    ),
                    dmc.TableTd(
                        (
                            f"{fmt_number(row.get('projected_margin_pct'), 1)}%"
                        )
                    ),
                    dmc.TableTd(
                        fmt_number(
                            row.get(
                                "projected_stock_days"
                            ),
                            0,
                        )
                    ),
                ],
                style={
                    "backgroundColor": (
                        "#ECFDF5"
                        if is_recommended
                        else (
                            "#F9FAFB"
                            if abs(change) < 0.01
                            else "transparent"
                        )
                    ),
                    "fontWeight": (
                        "700"
                        if is_recommended
                        else "400"
                    ),
                },
            )
        )

    return dmc.Table(
        striped=True,
        highlightOnHover=True,
        withTableBorder=True,
        withColumnBorders=True,
        horizontalSpacing="sm",
        verticalSpacing="xs",
        children=[
            dmc.TableThead(
                dmc.TableTr(
                    [
                        dmc.TableTh("Δ нашей цены"),
                        dmc.TableTh("Наша цена"),
                        dmc.TableTh("Цена покупателя"),
                        dmc.TableTh("Продаж/день"),
                        dmc.TableTh("Маржа 30д"),
                        dmc.TableTh("Маржа %"),
                        dmc.TableTh("Запас, дн."),
                    ]
                )
            ),
            dmc.TableTbody(body),
        ],
    )


def history_table(rows):
    if not rows:
        return dmc.Text(
            "История отсутствует.",
            c="dimmed",
            size="sm",
        )

    ordered = sorted(
        rows,
        key=lambda row: str(
            row.get(
                "date_from",
                "",
            )
        ),
        reverse=True,
    )[:90]

    body = [
        dmc.TableTr(
            [
                dmc.TableTd(
                    str(
                        row.get(
                            "date_from",
                            "",
                        )
                    )
                ),
                dmc.TableTd(
                    fmt_number(
                        row.get(
                            "sales_qty"
                        ),
                        0,
                    )
                ),
                dmc.TableTd(
                    fmt_money(
                        row.get(
                            "seller_price"
                        )
                    )
                ),
                dmc.TableTd(
                    fmt_money(
                        row.get(
                            "buyer_price"
                        )
                    )
                ),
                dmc.TableTd(
                    (
                        f"{fmt_number(row.get('wb_price_delta_pct'), 1)}%"
                        if row.get(
                            "wb_price_delta_pct"
                        ) is not None
                        else "—"
                    )
                ),
                dmc.TableTd(
                    fmt_money(
                        row.get(
                            "margin_man"
                        )
                    )
                ),
            ]
        )
        for row in ordered
    ]

    return dmc.Table(
        striped=True,
        withTableBorder=True,
        withColumnBorders=True,
        horizontalSpacing="sm",
        verticalSpacing="xs",
        children=[
            dmc.TableThead(
                dmc.TableTr(
                    [
                        dmc.TableTh("Дата"),
                        dmc.TableTh("Продажи"),
                        dmc.TableTh("Наша цена"),
                        dmc.TableTh("Цена покупателя"),
                        dmc.TableTh("Разница WB"),
                        dmc.TableTh("Маржа"),
                    ]
                )
            ),
            dmc.TableTbody(body),
        ],
    )


def register_pricing_strategy_callbacks(app):
    @app.callback(
        Output(
            "pricing-strategy-download",
            "data",
        ),
        Input(
            "pricing-strategy-export",
            "n_clicks",
        ),
        State(
            "pricing-strategy-store",
            "data",
        ),
        prevent_initial_call=True,
    )
    def export_excel(
        n_clicks,
        payload,
    ):
        if not n_clicks or not payload:
            return None

        content = build_pricing_excel(
            payload
        )

        report_date = payload.get(
            "report_date",
            "report",
        )

        return dcc.send_bytes(
            content,
            filename=(
                f"pricing_strategy_"
                f"{report_date}.xlsx"
            ),
        )

    @app.callback(
        Output(
            "pricing-strategy-detail",
            "children",
        ),
        Input(
            "pricing-strategy-grid",
            "selectedRows",
        ),
        State(
            "pricing-strategy-store",
            "data",
        ),
        prevent_initial_call=True,
    )
    def open_detail(
        selected_rows,
        payload,
    ):
        if (
            not selected_rows
            or not payload
        ):
            return dmc.Text(
                "Выберите артикул.",
                c="dimmed",
                size="sm",
            )

        row = selected_rows[0]
        nm_id = row.get(
            "nm_id"
        )

        scenarios = [
            item
            for item in (
                payload.get(
                    "scenarios"
                )
                or []
            )
            if str(
                item.get(
                    "nm_id"
                )
            )
            == str(
                nm_id
            )
        ]

        history = [
            item
            for item in (
                payload.get(
                    "history"
                )
                or []
            )
            if str(
                item.get(
                    "nm_id"
                )
            )
            == str(
                nm_id
            )
        ]

        return dmc.Stack(
            gap="md",
            children=[
                dmc.Group(
                    justify="space-between",
                    align="flex-start",
                    children=[
                        dmc.Box(
                            children=[
                                dmc.Title(
                                    (
                                        f"{row.get('brand', '')} · "
                                        f"{row.get('title', '')}"
                                    ),
                                    order=3,
                                    fw=800,
                                ),
                                dmc.Text(
                                    (
                                        f"NM ID {nm_id} · "
                                        f"{row.get('category', '')}"
                                    ),
                                    size="sm",
                                    c="dimmed",
                                ),
                            ]
                        ),
                        dmc.Badge(
                            row.get(
                                "status",
                                "HOLD",
                            ),
                            radius=0,
                            size="lg",
                            variant="light",
                        ),
                    ],
                ),

                dmc.SimpleGrid(
                    cols={
                        "base": 2,
                        "md": 4,
                        "lg": 8,
                    },
                    spacing="xs",
                    children=[
                        metric(
                            "Цена в карточке",
                            fmt_money(
                                row.get(
                                    "current_seller_list_price"
                                )
                            ),
                        ),
                        metric(
                            "Наша факт. 30д",
                            fmt_money(
                                row.get(
                                    "seller_price_30d"
                                )
                            ),
                        ),
                        metric(
                            "Покупатель 30д",
                            fmt_money(
                                row.get(
                                    "buyer_price_30d"
                                )
                            ),
                        ),
                        metric(
                            "Рекоменд. наша",
                            fmt_money(
                                row.get(
                                    "recommended_seller_price"
                                )
                            ),
                        ),
                        metric(
                            "Рекоменд. покупателю",
                            fmt_money(
                                row.get(
                                    "recommended_buyer_price"
                                )
                            ),
                        ),
                        metric(
                            "Запас",
                            (
                                f"{fmt_number(row.get('days_of_stock'), 0)} дн."
                            ),
                        ),
                        metric(
                            "Эластичность",
                            fmt_number(
                                row.get(
                                    "elasticity"
                                ),
                                2,
                            ),
                        ),
                        metric(
                            "Confidence",
                            (
                                f"{fmt_number(row.get('confidence_score'), 0)}%"
                            ),
                        ),
                    ],
                ),

                dmc.Alert(
                    color="gray",
                    radius=0,
                    title="Почему",
                    children=row.get(
                        "reason",
                        "",
                    ),
                ),

                dmc.Title(
                    "Сценарии цены",
                    order=4,
                    fw=700,
                ),

                dmc.ScrollArea(
                    scenario_table(
                        scenarios,
                        row.get(
                            "recommended_change_pct",
                            0,
                        ),
                    ),
                    type="auto",
                ),

                dmc.Title(
                    "Дневная история · последние 90 строк",
                    order=4,
                    fw=700,
                ),

                dmc.ScrollArea(
                    history_table(
                        history
                    ),
                    h=420,
                    type="auto",
                ),
            ],
        )
