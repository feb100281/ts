# gear/app/daily_sales/pricing_strategy/callbacks.py

from __future__ import annotations

from datetime import date

import dash_mantine_components as dmc
from dash import (
    Input,
    Output,
    State,
    dcc,
    no_update,
)

from .analytics import analyze_pricing
from .data import get_pricing_source
from .excel import build_pricing_excel
from .layout import build_pricing_body


def _safe_records(frame):
    if frame is None or frame.empty:
        return []

    rows = (
        frame
        .astype(object)
        .where(
            frame.notna(),
            None,
        )
        .to_dict("records")
    )

    for row in rows:
        for key, value in list(
            row.items()
        ):
            if (
                value is not None
                and hasattr(
                    value,
                    "isoformat",
                )
                and not isinstance(
                    value,
                    str,
                )
            ):
                try:
                    row[key] = (
                        value.isoformat()
                    )
                except Exception:
                    pass

    return rows


def _fmt(
    value,
    digits=0,
):
    if value is None:
        return "—"

    try:
        return (
            f"{float(value):,.{digits}f}"
            .replace(",", " ")
        )
    except (
        TypeError,
        ValueError,
    ):
        return "—"


def _money(value):
    return (
        f"{_fmt(value, 0)} ₽"
    )


def _scenario_table(
    rows,
    recommended_change,
):
    if not rows:
        return dmc.Text(
            "Сценарии недоступны.",
            c="dimmed",
        )

    body = []

    for row in sorted(
        rows,
        key=lambda x: float(
            x.get(
                "price_change_pct"
            )
            or 0
        ),
    ):
        change = float(
            row.get(
                "price_change_pct"
            )
            or 0
        )

        recommended = (
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
                        _money(
                            row.get(
                                "seller_price"
                            )
                        )
                    ),

                    dmc.TableTd(
                        _money(
                            row.get(
                                "buyer_price"
                            )
                        )
                    ),

                    dmc.TableTd(
                        _fmt(
                            row.get(
                                "projected_daily_qty"
                            ),
                            1,
                        )
                    ),

                    dmc.TableTd(
                        _money(
                            row.get(
                                "projected_margin"
                            )
                        )
                    ),

                    dmc.TableTd(
                        (
                            f"{_fmt(row.get('projected_margin_pct'), 1)}%"
                        )
                    ),

                    dmc.TableTd(
                        _fmt(
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
                        if recommended
                        else "transparent"
                    ),
                    "fontWeight": (
                        "700"
                        if recommended
                        else "400"
                    ),
                },
            )
        )

    return dmc.Table(
        striped=True,
        withTableBorder=True,
        withColumnBorders=True,
        children=[
            dmc.TableThead(
                dmc.TableTr(
                    [
                        dmc.TableTh(
                            "Δ цены"
                        ),
                        dmc.TableTh(
                            "Наша цена"
                        ),
                        dmc.TableTh(
                            "Цена покупателя"
                        ),
                        dmc.TableTh(
                            "Продаж/день"
                        ),
                        dmc.TableTh(
                            "Маржа 30д"
                        ),
                        dmc.TableTh(
                            "Маржа %"
                        ),
                        dmc.TableTh(
                            "Запас, дн."
                        ),
                    ]
                )
            ),

            dmc.TableTbody(
                body
            ),
        ],
    )


def register_pricing_strategy_callbacks(
    app,
    filters,
):

    # ============================================================
    # ОТКРЫТИЕ АНАЛИЗА
    # ============================================================

    @app.callback(
        Output(
            "pricing-strategy-modal",
            "opened",
        ),
        Output(
            "pricing-strategy-body",
            "children",
        ),
        Output(
            "pricing-strategy-store",
            "data",
        ),

        Input(
            "pricing-strategy-open",
            "n_clicks",
        ),

        State(
            filters.date_picker_id,
            "value",
        ),
        State(
            filters.cat_multy_id,
            "value",
        ),
        State(
            filters.brand_multy_id,
            "value",
        ),
        State(
            filters.gender_multy_id,
            "value",
        ),

        prevent_initial_call=True,
    )
    def open_pricing(
        open_clicks,
        date_range,
        cat_list,
        brand_list,
        gender_list,
    ):
        if not open_clicks:
            return (
                no_update,
                no_update,
                no_update,
            )

        if (
            date_range
            and len(date_range) == 2
        ):
            report_date = (
                date_range[1]
            )
        else:
            report_date = (
                date.today()
            )

        try:

            source = (
                get_pricing_source(
                    report_date=report_date,
                    cat_list=cat_list,
                    brand_list=brand_list,
                    gender_list=gender_list,
                )
            )

            analysis = (
                analyze_pricing(
                    source
                )
            )

            payload = {
                "report_date": str(
                    analysis[
                        "report_date"
                    ]
                ),

                "history_start": str(
                    analysis[
                        "history_start"
                    ]
                ),

                "wb_date": (
                    str(
                        analysis[
                            "wb_date"
                        ]
                    )
                    if analysis.get(
                        "wb_date"
                    )
                    else None
                ),

                "fbs_date": (
                    str(
                        analysis[
                            "fbs_date"
                        ]
                    )
                    if analysis.get(
                        "fbs_date"
                    )
                    else None
                ),

                "recommendations": (
                    _safe_records(
                        analysis[
                            "recommendations"
                        ]
                    )
                ),

                "portfolio": (
                    _safe_records(
                        analysis[
                            "portfolio"
                        ]
                    )
                ),

                "scenarios": (
                    _safe_records(
                        analysis[
                            "scenarios"
                        ]
                    )
                ),

                "history": (
                    _safe_records(
                        analysis[
                            "history"
                        ]
                    )
                ),
            }

            return (
                True,
                build_pricing_body(
                    analysis
                ),
                payload,
            )

        except Exception as exc:

            return (
                True,

                dmc.Alert(
                    title=(
                        "Ошибка расчёта "
                        "управления ценами"
                    ),
                    color="red",
                    radius=0,
                    children=str(exc),
                ),

                None,
            )


    # ============================================================
    # ЗАКРЫТИЕ MODAL
    # ============================================================

    @app.callback(
        Output(
            "pricing-strategy-modal",
            "opened",
            allow_duplicate=True,
        ),

        Input(
            "pricing-strategy-close",
            "n_clicks",
        ),

        prevent_initial_call=True,
    )
    def close_pricing(
        close_clicks,
    ):
        if not close_clicks:
            return no_update

        return False


    # ============================================================
    # ПРОВАЛИВАНИЕ:
    # БРЕНД + КАТЕГОРИЯ -> NM ID
    # ============================================================

    @app.callback(
        Output(
            "pricing-products-grid",
            "rowData",
        ),

        Input(
            "pricing-portfolio-grid",
            "selectedRows",
        ),

        State(
            "pricing-strategy-store",
            "data",
        ),

        prevent_initial_call=True,
    )
    def filter_products(
        selected_rows,
        payload,
    ):
        if not payload:
            return no_update

        all_rows = (
            payload.get(
                "recommendations"
            )
            or []
        )

        if not selected_rows:
            return all_rows

        selected = (
            selected_rows[0]
        )

        brand = selected.get(
            "brand"
        )

        category = selected.get(
            "category"
        )

        return [
            row
            for row in all_rows
            if (
                row.get(
                    "brand"
                )
                == brand
                and
                row.get(
                    "category"
                )
                == category
            )
        ]


    # ============================================================
    # ПОКАЗАТЬ ВСЕ NM ID
    # ============================================================

    @app.callback(
        Output(
            "pricing-products-grid",
            "rowData",
            allow_duplicate=True,
        ),

        Input(
            "pricing-show-all",
            "n_clicks",
        ),

        State(
            "pricing-strategy-store",
            "data",
        ),

        prevent_initial_call=True,
    )
    def show_all_products(
        n_clicks,
        payload,
    ):
        if (
            not n_clicks
            or not payload
        ):
            return no_update

        return (
            payload.get(
                "recommendations"
            )
            or []
        )


    # ============================================================
    # ДЕТАЛИ ПО NM ID
    # ============================================================

    @app.callback(
        Output(
            "pricing-product-detail",
            "children",
        ),

        Input(
            "pricing-products-grid",
            "selectedRows",
        ),

        State(
            "pricing-strategy-store",
            "data",
        ),

        prevent_initial_call=True,
    )
    def product_detail(
        selected_rows,
        payload,
    ):
        if (
            not selected_rows
            or not payload
        ):
            return dmc.Text(
                "Выберите NM ID.",
                c="dimmed",
            )

        row = (
            selected_rows[0]
        )

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

        history = sorted(
            history,
            key=lambda item: str(
                item.get(
                    "date_from",
                    "",
                )
            ),
            reverse=True,
        )[:90]

        history_rows = []

        for item in history:
            seller_price = item.get(
                "seller_price"
            )

            buyer_price = item.get(
                "buyer_price"
            )

            wb_discount_pct = None

            try:
                seller_price_value = float(
                    seller_price
                    or 0
                )

                buyer_price_value = float(
                    buyer_price
                    or 0
                )

                if seller_price_value > 0:
                    wb_discount_pct = (
                        (
                            1
                            - (
                                buyer_price_value
                                / seller_price_value
                            )
                        )
                        * 100
                    )

            except (
                TypeError,
                ValueError,
                ZeroDivisionError,
            ):
                wb_discount_pct = None

            history_rows.append(
                dmc.TableTr(
                    [
                        dmc.TableTd(
                            item.get(
                                "date_from",
                                ""
                            )
                        ),

                        dmc.TableTd(
                            _fmt(
                                item.get(
                                    "sales_qty"
                                ),
                                0,
                            )
                        ),

                        dmc.TableTd(
                            _money(
                                seller_price
                            )
                        ),

                        dmc.TableTd(
                            (
                                f"{_fmt(wb_discount_pct, 1)}%"
                                if wb_discount_pct is not None
                                else "—"
                            )
                        ),

                        dmc.TableTd(
                            _money(
                                buyer_price
                            )
                        ),

                        dmc.TableTd(
                            _money(
                                item.get(
                                    "margin_man"
                                )
                            )
                        ),
                    ]
                )
            )

        history_table = (
            dmc.Table(
                striped=True,
                withTableBorder=True,
                withColumnBorders=True,
                children=[
                    dmc.TableThead(
                        dmc.TableTr(
                            [
                                dmc.TableTh(
                                    "Дата"
                                ),

                                dmc.TableTh(
                                    "Продажи"
                                ),

                                dmc.TableTh(
                                    "Наша цена"
                                ),

                                dmc.TableTh(
                                    "Скидка WB, %"
                                ),

                                dmc.TableTh(
                                    "Цена покупателя"
                                ),

                                dmc.TableTh(
                                    "Маржа"
                                ),
                            ]
                        )
                    ),

                    dmc.TableTbody(
                        history_rows
                    ),
                ],
            )
            if history_rows
            else dmc.Text(
                "История отсутствует.",
                c="dimmed",
            )
        )

        
        return dmc.Stack(
            gap="md",
            children=[

                # ----------------------------------------------------
                # HEADER
                # ----------------------------------------------------

                dmc.Group(
                    justify=(
                        "space-between"
                    ),
                    align=(
                        "flex-start"
                    ),
                    children=[

                        dmc.Box(
                            children=[

                                dmc.Title(
                                    (
                                        f"{row.get('brand', '')}"
                                        f" · "
                                        f"{row.get('title', '')}"
                                    ),
                                    order=3,
                                    fw=800,
                                ),

                                dmc.Text(
                                    (
                                        f"NM ID {nm_id}"
                                        f" · "
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


                # ----------------------------------------------------
                # KPI
                # ----------------------------------------------------

                dmc.SimpleGrid(
                    cols={
                        "base": 2,
                        "md": 4,
                        "lg": 8,
                    },
                    spacing="xs",
                    children=[

                        dmc.Text(
                            (
                                "Цена в карточке: "
                                f"{_money(row.get('current_seller_list_price'))}"
                            )
                        ),

                        dmc.Text(
                            (
                                "Наша факт. 30д: "
                                f"{_money(row.get('seller_price_30d'))}"
                            )
                        ),

                        dmc.Text(
                            (
                                "Покупатель 30д: "
                                f"{_money(row.get('buyer_price_30d'))}"
                            )
                        ),

                        dmc.Text(
                            (
                                "Рекоменд.: "
                                f"{_money(row.get('recommended_seller_price'))}"
                            )
                        ),

                        dmc.Text(
                            (
                                "WB: "
                                f"{_fmt(row.get('wb_stock'), 0)}"
                            )
                        ),

                        dmc.Text(
                            (
                                "FBS: "
                                f"{_fmt(row.get('fbs_stock'), 0)}"
                            )
                        ),

                        dmc.Text(
                            (
                                "Запас: "
                                f"{_fmt(row.get('days_of_stock'), 0)} дн."
                            )
                        ),

                        dmc.Text(
                            (
                                "Эластичность: "
                                f"{_fmt(row.get('elasticity'), 2)}"
                            )
                        ),
                    ],
                ),


                # ----------------------------------------------------
                # REASON
                # ----------------------------------------------------

                dmc.Alert(
                    title="Почему",
                    color="gray",
                    radius=0,
                    children=row.get(
                        "reason",
                        "",
                    ),
                ),


                # ----------------------------------------------------
                # SCENARIOS
                # ----------------------------------------------------

                dmc.Title(
                    "Сценарии цены",
                    order=4,
                    fw=700,
                ),

                dmc.ScrollArea(
                    _scenario_table(
                        scenarios,
                        row.get(
                            "recommended_change_pct"
                        ),
                    ),
                    type="auto",
                ),


                # ----------------------------------------------------
                # HISTORY
                # ----------------------------------------------------

                dmc.Title(
                    (
                        "История цены и продаж "
                        "· последние 90 дней"
                    ),
                    order=4,
                    fw=700,
                ),

                dmc.ScrollArea(
                    history_table,
                    h=420,
                    type="auto",
                ),
            ],
        )


    # ============================================================
    # EXCEL
    # ============================================================

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
        if (
            not n_clicks
            or not payload
        ):
            return None

        content = (
            build_pricing_excel(
                payload
            )
        )

        report_date = (
            payload.get(
                "report_date",
                "report",
            )
        )

        return dcc.send_bytes(
            content,
            filename=(
                f"pricing_strategy_"
                f"{report_date}.xlsx"
            ),
        )