# gear/app/daily_sales/stocks/dashboard_stock/warehouse_modal.py

"""
Рабочая модалка склада.

Открывается:
- через checkbox в таблице складов;
- через быстрый Select.

Именно здесь доступны:
- просмотр товаров склада;
- выбор конкретных размеров / Chrt ID;
- скачивание остатков склада;
- добавление выбранных товаров в план перемещения.

Карта эту модалку НЕ использует.
"""

from __future__ import annotations

import pandas as pd
import dash_mantine_components as dmc

from dash import (
    dcc,
    html,
    Input,
    Output,
    State,
    no_update,
)

from ..dashboard_data import (
    get_warehouse_products,
)

from .grids import (
    products_grid,
)

from .helpers import (
    fmt,
)

from .warehouse_excel import (
    build_warehouse_stock_excel,
)

from .ids import (
    STOCK_CONTEXT_ID,
    STOCK_WAREHOUSES_GRID_ID,
    STOCK_WAREHOUSE_SELECT_ID,
    STOCK_SELECTED_WAREHOUSE_STORE_ID,

    STOCK_WAREHOUSE_MODAL_ID,
    STOCK_WAREHOUSE_MODAL_TITLE_ID,
    STOCK_WAREHOUSE_MODAL_META_ID,

    STOCK_WAREHOUSE_PRODUCTS_GRID_ID,

    STOCK_WAREHOUSE_TRANSFER_BTN_ID,

    STOCK_WAREHOUSE_DOWNLOAD_BTN_ID,
    STOCK_WAREHOUSE_DOWNLOAD_ID,
)


# =============================================================================
# MODAL
# =============================================================================


def warehouse_action_modal():
    """
    Рабочая карточка выбранного склада.
    """

    return dmc.Modal(
        id=STOCK_WAREHOUSE_MODAL_ID,

        opened=False,

        size="96%",

        radius=0,

        centered=True,

        title=dmc.Text(
            id=STOCK_WAREHOUSE_MODAL_TITLE_ID,

            children="Товары склада",

            fw=700,
        ),

        children=[

            # =================================================================
            # HEADER
            # =================================================================

            dmc.Group(
                justify="space-between",

                align="flex-end",

                mb="md",

                children=[

                    # ---------------------------------------------------------
                    # Информация
                    # ---------------------------------------------------------

                    html.Div(
                        children=[

                            dmc.Text(
                                id=STOCK_WAREHOUSE_MODAL_META_ID,

                                size="sm",

                                c="dimmed",
                            ),

                            dmc.Text(
                                (
                                    "Checkbox выбирает конкретные размеры / Chrt ID. "
                                    "В план перемещения попадут только выбранные строки."
                                ),

                                size="xs",

                                c="dimmed",

                                mt=3,
                            ),
                        ],
                    ),

                    # ---------------------------------------------------------
                    # Кнопки
                    # ---------------------------------------------------------

                    dmc.Group(
                        gap="sm",

                        children=[

                            dmc.Button(
                                "Скачать остатки склада",

                                id=STOCK_WAREHOUSE_DOWNLOAD_BTN_ID,

                                variant="outline",

                                radius=0,

                                color="green",
                            ),

                            # ВАЖНО:
                            #
                            # Не управляем disabled через callback.
                            #
                            # Кнопка всегда доступна.
                            # Наличие выбранных строк проверяется
                            # уже callback-ом transfer_modal.py.
                            #
                            # Так мы исключаем конфликт состояния
                            # между AG Grid и кнопкой.
                            dmc.Button(
                                "Добавить выбранное в план перемещения",

                                id=STOCK_WAREHOUSE_TRANSFER_BTN_ID,

                                disabled=False,

                                radius=0,

                                color="green",
                            ),
                        ],
                    ),
                ],
            ),

            # =================================================================
            # GRID
            # =================================================================

            dcc.Loading(
                type="dot",

                delay_show=250,

                delay_hide=100,

                children=products_grid(
                    pd.DataFrame(),

                    grid_id=(
                        STOCK_WAREHOUSE_PRODUCTS_GRID_ID
                    ),
                ),
            ),
        ],
    )


# =============================================================================
# ОПРЕДЕЛЕНИЕ СКЛАДА
# =============================================================================


def _warehouse_from_inputs(
    selected_rows,
    quick_select,
):
    """
    Определяет склад для открытия рабочей карточки.

    Приоритет:

    1. checkbox таблицы складов;
    2. быстрый Select.
    """

    # -------------------------------------------------------------------------
    # Таблица складов
    # -------------------------------------------------------------------------

    if selected_rows:

        first_row = (
            selected_rows[0]
            or {}
        )

        value = first_row.get(
            "warehouse"
        )

        if value:

            return str(
                value
            ).strip()

    # -------------------------------------------------------------------------
    # Быстрый Select
    # -------------------------------------------------------------------------

    if quick_select:

        return str(
            quick_select
        ).strip()

    return ""


# =============================================================================
# CALLBACKS
# =============================================================================


def register_warehouse_modal_callbacks(
    app,
):

    # =========================================================================
    # 1. ОТКРЫТИЕ РАБОЧЕЙ КАРТОЧКИ СКЛАДА
    # =========================================================================

    @app.callback(

        Output(
            STOCK_WAREHOUSE_MODAL_ID,
            "opened",
        ),

        Output(
            STOCK_WAREHOUSE_MODAL_TITLE_ID,
            "children",
        ),

        Output(
            STOCK_WAREHOUSE_MODAL_META_ID,
            "children",
        ),

        Output(
            STOCK_WAREHOUSE_PRODUCTS_GRID_ID,
            "rowData",
        ),

        Output(
            STOCK_WAREHOUSE_PRODUCTS_GRID_ID,
            "selectedRows",
        ),

        Output(
            STOCK_SELECTED_WAREHOUSE_STORE_ID,
            "data",
        ),

        # ---------------------------------------------------------------------
        # Inputs
        # ---------------------------------------------------------------------

        Input(
            STOCK_WAREHOUSES_GRID_ID,
            "selectedRows",
        ),

        Input(
            STOCK_WAREHOUSE_SELECT_ID,
            "value",
        ),

        # ---------------------------------------------------------------------
        # State
        # ---------------------------------------------------------------------

        State(
            STOCK_CONTEXT_ID,
            "data",
        ),

        prevent_initial_call=True,
    )
    def open_warehouse_action_modal(
        selected_rows,
        quick_select,
        context,
    ):
        """
        Загружает товары выбранного склада.

        Важно:
        при каждом новом открытии selectedRows товаров
        принудительно очищается.
        """

        # ---------------------------------------------------------------------
        # Определяем склад
        # ---------------------------------------------------------------------

        warehouse_name = (
            _warehouse_from_inputs(
                selected_rows=selected_rows,
                quick_select=quick_select,
            )
        )

        # ---------------------------------------------------------------------
        # Склад не выбран
        # ---------------------------------------------------------------------

        if not warehouse_name:

            return (
                False,      # modal opened

                no_update,  # title

                no_update,  # meta

                [],         # rowData

                [],         # selectedRows

                None,       # selected warehouse store
            )

        # ---------------------------------------------------------------------
        # Контекст dashboard
        # ---------------------------------------------------------------------

        context = (
            context
            or {}
        )

        report_date = context.get(
            "report_date"
        )

        # ---------------------------------------------------------------------
        # Получаем товары склада
        # ---------------------------------------------------------------------

        df = get_warehouse_products(
            report_date=report_date,

            warehouse_name=warehouse_name,

            brand_list=context.get(
                "brand_list"
            ),

            cat_list=context.get(
                "cat_list"
            ),

            gender_list=context.get(
                "gender_list"
            ),
        )

        # ---------------------------------------------------------------------
        # Нет товаров
        # ---------------------------------------------------------------------

        if df.empty:

            meta = (
                "По текущим фильтрам "
                "товаров на складе нет."
            )

        # ---------------------------------------------------------------------
        # Summary склада
        # ---------------------------------------------------------------------

        else:

            # На складе
            on_hand = (
                pd.to_numeric(
                    df["Остаток"],

                    errors="coerce",
                )
                .fillna(0)
                .sum()
            )

            # В пути от клиента
            in_way_from_client = (
                pd.to_numeric(
                    df[
                        "В пути от клиента"
                    ],

                    errors="coerce",
                )
                .fillna(0)
                .sum()
            )

            # В пути к клиенту
            in_way_to_client = (
                pd.to_numeric(
                    df[
                        "В пути к клиенту"
                    ],

                    errors="coerce",
                )
                .fillna(0)
                .sum()
            )

            # Всего в пути
            in_transit = (
                in_way_from_client
                +
                in_way_to_client
            )

            # Общий товарный запас
            total = (
                pd.to_numeric(
                    df["Итого"],

                    errors="coerce",
                )
                .fillna(0)
                .sum()
            )

            # Уникальные NM ID
            nm_count = (
                df["NM ID"]
                .dropna()
                .nunique()
            )

            # Количество строк / Chrt ID
            chrt_count = (
                df["Chrt ID"]
                .dropna()
                .nunique()
            )

            meta = (
                f"На складе: {fmt(on_hand)} шт"
                f" · в пути: {fmt(in_transit)} шт"
                f" · всего: {fmt(total)} шт"
                f" · товаров: {fmt(nm_count)} NM ID"
                f" · размеров: {fmt(chrt_count)} Chrt ID"
            )

        # ---------------------------------------------------------------------
        # Открываем карточку
        # ---------------------------------------------------------------------

        return (
            True,

            warehouse_name,

            meta,

            df.to_dict(
                "records"
            ),

            # При новом открытии никакое
            # старое выделение не сохраняем.
            [],

            warehouse_name,
        )


    # =========================================================================
    # 2. СКАЧИВАНИЕ ОСТАТКОВ КОНКРЕТНОГО СКЛАДА
    # =========================================================================

    @app.callback(

        Output(
            STOCK_WAREHOUSE_DOWNLOAD_ID,
            "data",
        ),

        # ---------------------------------------------------------------------
        # Один Input.
        # Никакого ctx.
        # Никаких timestamp.
        # ---------------------------------------------------------------------

        Input(
            STOCK_WAREHOUSE_DOWNLOAD_BTN_ID,
            "n_clicks",
        ),

        # ---------------------------------------------------------------------
        # State
        # ---------------------------------------------------------------------

        State(
            STOCK_SELECTED_WAREHOUSE_STORE_ID,
            "data",
        ),

        State(
            STOCK_CONTEXT_ID,
            "data",
        ),

        State(
            STOCK_WAREHOUSE_PRODUCTS_GRID_ID,
            "rowData",
        ),

        prevent_initial_call=True,
    )
    def download_warehouse(
        n_clicks,
        warehouse_name,
        context,
        rows,
    ):
        """
        Скачивает текущую таблицу товаров склада.

        Используем уже загруженный rowData AG Grid,
        поэтому повторный SQL-запрос не требуется.
        """

        # ---------------------------------------------------------------------
        # Ничего не нажато
        # ---------------------------------------------------------------------

        if not n_clicks:

            return no_update

        # ---------------------------------------------------------------------
        # Не определён склад
        # ---------------------------------------------------------------------

        warehouse_name = str(
            warehouse_name
            or ""
        ).strip()

        if not warehouse_name:

            return no_update

        # ---------------------------------------------------------------------
        # Нет строк
        # ---------------------------------------------------------------------

        if not rows:

            return no_update

        # ---------------------------------------------------------------------
        # Контекст
        # ---------------------------------------------------------------------

        context = (
            context
            or {}
        )

        report_date = context.get(
            "report_date"
        )

        # ---------------------------------------------------------------------
        # DataFrame
        # ---------------------------------------------------------------------

        df = pd.DataFrame(
            rows
        )

        if df.empty:

            return no_update

        # ---------------------------------------------------------------------
        # Excel
        # ---------------------------------------------------------------------

        try:

            content, filename = (
                build_warehouse_stock_excel(
                    df=df,

                    warehouse_name=(
                        warehouse_name
                    ),

                    report_date=(
                        report_date
                    ),
                )
            )

        except ValueError:

            return no_update

        # ---------------------------------------------------------------------
        # Download
        # ---------------------------------------------------------------------

        return dcc.send_bytes(
            content,
            filename,
        )