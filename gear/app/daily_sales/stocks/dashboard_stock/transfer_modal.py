# gear/app/daily_sales/stocks/dashboard_stock/transfer_modal.py
"""Модалка и callbacks плана перемещения.

Ключевой принцип:
рабочая модалка склада НЕ закрывается и НЕ изменяется этим модулем.
Поэтому между warehouse_modal и transfer_modal нет duplicate-output.
"""

from __future__ import annotations

import dash_mantine_components as dmc
from dash_iconify import DashIconify

from dash import (
    dcc,
    html,
    Input,
    Output,
    State,
    no_update,
)

from ..dashboard_data import get_warehouse_options
from ..transfer_excel import build_transfer_plan_excel
from .grids import transfer_grid
from .helpers import safe_float
from .ids import (
    STOCK_CONTEXT_ID,
    STOCK_SELECTED_WAREHOUSE_STORE_ID,
    STOCK_WAREHOUSE_PRODUCTS_GRID_ID,
    STOCK_WAREHOUSE_TRANSFER_BTN_ID,

    STOCK_TRANSFER_MODAL_ID,
    STOCK_TRANSFER_GRID_ID,
    STOCK_TRANSFER_GRID_CONTAINER_ID,
    STOCK_TRANSFER_VALIDATION_ID,
    STOCK_TRANSFER_BULK_WAREHOUSE_ID,
    STOCK_TRANSFER_ALL_QTY_BTN_ID,
    STOCK_TRANSFER_DOWNLOAD_BTN_ID,
    STOCK_TRANSFER_DOWNLOAD_ID,
)


def transfer_modal():
    return dmc.Modal(
        id=STOCK_TRANSFER_MODAL_ID,
        opened=False,
        size="96%",
        radius=0,
        centered=True,
        title=dmc.Text(
            "План перемещения товаров",
            fw=700,
        ),
        children=[
            # ---------------------------------------------------------
            # Информация
            # ---------------------------------------------------------
            dmc.Alert(
                (
                    "В плане используются только выбранные строки "
                    "и только физический остаток склада."
                ),
                color="green",
                variant="light",
                radius=0,
                mb="md",
            ),

            # ---------------------------------------------------------
            # Верхняя панель управления
            # ---------------------------------------------------------
            dmc.Paper(
                radius=0,
                p="md",
                mb="md",
                style={
                    "border": "1px solid #D6DFDB",
                    "background": "#F8FAF9",
                },
                children=[
                    dmc.Group(
                        justify="space-between",
                        align="flex-end",
                        gap="md",
                        children=[
                            # Левая часть
                            html.Div(
                                [
                                    dmc.Text(
                                        "Массовое заполнение",
                                        fw=700,
                                        size="sm",
                                    ),
                                    dmc.Text(
                                        (
                                            "Выберите склад назначения, "
                                            "чтобы поставить весь доступный "
                                            "остаток во все строки."
                                        ),
                                        size="xs",
                                        c="dimmed",
                                        mt=2,
                                    ),
                                ]
                            ),

                            # Правая часть
                            dmc.Group(
                                align="flex-end",
                                gap="sm",
                                children=[
                                    dmc.Select(
                                        id=STOCK_TRANSFER_BULK_WAREHOUSE_ID,
                                        label="Склад назначения",
                                        placeholder="Выберите склад",
                                        data=[],
                                        searchable=True,
                                        clearable=True,
                                        radius=0,
                                        w=360,
                                    ),

                                    dmc.Button(
                                        "Переместить всё доступное",
                                        id=STOCK_TRANSFER_ALL_QTY_BTN_ID,
                                        disabled=True,
                                        radius=0,
                                        color="green",
                                    ),

                                    dmc.Button(
                                        "Скачать план Excel",
                                        id=STOCK_TRANSFER_DOWNLOAD_BTN_ID,
                                        leftSection=DashIconify(
                                            icon="material-symbols:download-rounded",
                                            width=18,
                                        ),
                                        radius=0,
                                        variant="light",
                                        color="green",
                                    ),
                                ],
                            ),
                        ],
                    ),
                ],
            ),

            # ---------------------------------------------------------
            # Таблица плана перемещения
            # ---------------------------------------------------------
            html.Div(
                id=STOCK_TRANSFER_GRID_CONTAINER_ID,
            ),

            # ---------------------------------------------------------
            # Валидация / статус плана
            # ---------------------------------------------------------
            dmc.Text(
                id=STOCK_TRANSFER_VALIDATION_ID,
                size="sm",
                mt="sm",
                c="dimmed",
            ),
        ],
    )

def _build_transfer_rows(
    selected_rows,
    source_warehouse,
    context,
):
    if not selected_rows:
        return None

    source_warehouse = str(
        source_warehouse
        or ""
    ).strip()

    if not source_warehouse:
        return None

    context = context or {}
    report_date = context.get(
        "report_date"
    )

    warehouses = [
        warehouse
        for warehouse
        in get_warehouse_options(
            report_date
        )
        if warehouse != source_warehouse
    ]

    source_region = ""

    for warehouse_row in (
        context.get("warehouses")
        or []
    ):
        if (
            warehouse_row.get("warehouse")
            == source_warehouse
        ):
            source_region = (
                warehouse_row.get("region")
                or ""
            )
            break

    rows = []

    for row in selected_rows:
        rows.append(
            {
                "Откуда": source_warehouse,
                "Регион откуда": source_region,
                "Куда": None,

                "Бренд": row.get("Бренд"),
                "Категория": row.get("Категория"),
                "Артикул": row.get("Артикул"),
                "Наименование": row.get("Наименование"),
                "Размер": row.get("Размер"),

                # Для перемещения доступен только
                # физический остаток.
                "Доступно": safe_float(
                    row.get("Остаток")
                ),

                "Переместить": 0,

                "NM ID": row.get("NM ID"),
                "Chrt ID": row.get("Chrt ID"),
            }
        )

    return (
        rows,
        warehouses,
    )


def _validation_text(rows):
    rows = rows or []

    if not rows:
        return "Нет строк в плане."

    problems = []

    for index, row in enumerate(
        rows,
        start=1,
    ):
        destination = str(
            row.get("Куда")
            or ""
        ).strip()

        available = safe_float(
            row.get("Доступно")
        )

        move_qty = safe_float(
            row.get("Переместить")
        )

        if not destination:
            problems.append(
                f"строка {index}: не выбран склад"
            )

        if move_qty <= 0:
            problems.append(
                f"строка {index}: количество = 0"
            )

        if move_qty > available:
            problems.append(
                f"строка {index}: превышен остаток"
            )

    if problems:
        text = "; ".join(
            problems[:6]
        )

        if len(problems) > 6:
            text += "…"

        return (
            "Проверьте план: "
            + text
        )

    total_qty = sum(
        safe_float(
            row.get("Переместить")
        )
        for row in rows
    )

    return (
        f"План готов: {len(rows)} позиций · "
        f"{total_qty:,.0f} шт"
    ).replace(",", " ")


def register_transfer_modal_callbacks(app):

    # -----------------------------------------------------------------
    # Открываем план.
    #
    # ОДИН Input:
    #     кнопка "Добавить выбранное в план"
    #
    # Никаких ctx / timestamp / duplicate output.
    # -----------------------------------------------------------------
    @app.callback(
        Output(
            STOCK_TRANSFER_MODAL_ID,
            "opened",
        ),
        Output(
            STOCK_TRANSFER_GRID_CONTAINER_ID,
            "children",
        ),
        Output(
            STOCK_TRANSFER_VALIDATION_ID,
            "children",
        ),
        Output(
            STOCK_TRANSFER_BULK_WAREHOUSE_ID,
            "data",
        ),
        Output(
            STOCK_TRANSFER_BULK_WAREHOUSE_ID,
            "value",
        ),

        Input(
            STOCK_WAREHOUSE_TRANSFER_BTN_ID,
            "n_clicks",
        ),

        State(
            STOCK_WAREHOUSE_PRODUCTS_GRID_ID,
            "selectedRows",
        ),
        State(
            STOCK_SELECTED_WAREHOUSE_STORE_ID,
            "data",
        ),
        State(
            STOCK_CONTEXT_ID,
            "data",
        ),

        prevent_initial_call=True,
    )
    def open_transfer_modal(
        n_clicks,
        selected_rows,
        source_warehouse,
        context,
    ):
        if not n_clicks:
            return (
                False,
                no_update,
                no_update,
                no_update,
                no_update,
            )

        payload = _build_transfer_rows(
            selected_rows=selected_rows,
            source_warehouse=source_warehouse,
            context=context,
        )

        if payload is None:
            return (
                False,
                no_update,
                "Сначала выберите хотя бы одну строку товара.",
                no_update,
                no_update,
            )

        rows, warehouses = payload

        options = [
            {
                "label": warehouse,
                "value": warehouse,
            }
            for warehouse
            in warehouses
        ]

        return (
            True,

            transfer_grid(
                rows,
                warehouses,
            ),

            (
                f"Выбрано позиций: {len(rows)}. "
                "Укажите склад назначения и количество."
            ),

            options,

            None,
        )

    # -----------------------------------------------------------------
    # Массовая кнопка доступна только после выбора склада.
    # -----------------------------------------------------------------
    @app.callback(
        Output(
            STOCK_TRANSFER_ALL_QTY_BTN_ID,
            "disabled",
        ),

        Input(
            STOCK_TRANSFER_BULK_WAREHOUSE_ID,
            "value",
        ),
    )
    def toggle_bulk_button(
        destination,
    ):
        return not bool(destination)

    # -----------------------------------------------------------------
    # Заполнить весь доступный остаток.
    # -----------------------------------------------------------------
    @app.callback(
        Output(
            STOCK_TRANSFER_GRID_ID,
            "rowData",
        ),
        Output(
            STOCK_TRANSFER_VALIDATION_ID,
            "children",
            allow_duplicate=True,
        ),

        Input(
            STOCK_TRANSFER_ALL_QTY_BTN_ID,
            "n_clicks",
        ),

        State(
            STOCK_TRANSFER_BULK_WAREHOUSE_ID,
            "value",
        ),
        State(
            STOCK_TRANSFER_GRID_ID,
            "rowData",
        ),

        prevent_initial_call=True,
    )
    def fill_all_available(
        n_clicks,
        destination,
        rows,
    ):
        if (
            not n_clicks
            or not destination
            or not rows
        ):
            return (
                no_update,
                no_update,
            )

        result = []

        for row in rows:
            item = dict(row)

            item["Куда"] = (
                destination
            )

            item["Переместить"] = (
                safe_float(
                    item.get("Доступно")
                )
            )

            result.append(
                item
            )

        return (
            result,
            _validation_text(
                result
            ),
        )

    # -----------------------------------------------------------------
    # Валидация ручных изменений.
    # -----------------------------------------------------------------
    @app.callback(
        Output(
            STOCK_TRANSFER_VALIDATION_ID,
            "children",
            allow_duplicate=True,
        ),

        Input(
            STOCK_TRANSFER_GRID_ID,
            "cellValueChanged",
        ),

        State(
            STOCK_TRANSFER_GRID_ID,
            "rowData",
        ),

        prevent_initial_call=True,
    )
    def validate_manual_changes(
        cell_value_changed,
        rows,
    ):
        if not cell_value_changed:
            return no_update

        return _validation_text(
            rows
        )

    # -----------------------------------------------------------------
    # Excel плана.
    # -----------------------------------------------------------------
    @app.callback(
        Output(
            STOCK_TRANSFER_DOWNLOAD_ID,
            "data",
        ),

        Input(
            STOCK_TRANSFER_DOWNLOAD_BTN_ID,
            "n_clicks",
        ),

        State(
            STOCK_TRANSFER_GRID_ID,
            "rowData",
        ),

        prevent_initial_call=True,
    )
    def download_transfer_plan(
        n_clicks,
        rows,
    ):
        if not n_clicks:
            return no_update

        try:
            content, filename = (
                build_transfer_plan_excel(
                    rows
                )
            )

        except ValueError:
            return no_update

        return dcc.send_bytes(
            content,
            filename,
        )
