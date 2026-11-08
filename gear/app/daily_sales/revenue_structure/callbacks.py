# gear/app/daily_sales/revenue_structure/callbacks.py

from __future__ import annotations

from dash import (
    Input,
    Output,
    State,
    dcc,
)

from .export import (
    build_revenue_excel,
)

from .ids import (
    REVENUE_STRUCTURE_BRAND_GRID_ID,
    REVENUE_STRUCTURE_BRAND_EXCEL_BTN_ID,
    REVENUE_STRUCTURE_BRAND_EXCEL_DOWNLOAD_ID,

    REVENUE_STRUCTURE_CATEGORY_GRID_ID,
    REVENUE_STRUCTURE_CATEGORY_EXCEL_BTN_ID,
    REVENUE_STRUCTURE_CATEGORY_EXCEL_DOWNLOAD_ID,

    REVENUE_STRUCTURE_GENDER_GRID_ID,
    REVENUE_STRUCTURE_GENDER_EXCEL_BTN_ID,
    REVENUE_STRUCTURE_GENDER_EXCEL_DOWNLOAD_ID,
)


def register_revenue_structure_callbacks(
    app,
):
    """
    Регистрирует Excel-экспорт таблиц
    структуры выручки.
    """

    # =====================================================
    # Бренды
    # =====================================================

    @app.callback(
        Output(
            REVENUE_STRUCTURE_BRAND_EXCEL_DOWNLOAD_ID,
            "data",
        ),

        Input(
            REVENUE_STRUCTURE_BRAND_EXCEL_BTN_ID,
            "n_clicks",
        ),

        State(
            REVENUE_STRUCTURE_BRAND_GRID_ID,
            "virtualRowData",
        ),

        State(
            REVENUE_STRUCTURE_BRAND_GRID_ID,
            "rowData",
        ),

        prevent_initial_call=True,
    )
    def export_brand_excel(
        n_clicks,
        virtual_rows,
        all_rows,
    ):

        rows = (
            virtual_rows
            if virtual_rows is not None
            else all_rows
        )

        content = build_revenue_excel(
            rows=rows or [],

            sheet_name="Бренды",
        )

        return dcc.send_bytes(
            content,

            "revenue_structure_brands.xlsx",
        )

    # =====================================================
    # Категории
    # =====================================================

    @app.callback(
        Output(
            REVENUE_STRUCTURE_CATEGORY_EXCEL_DOWNLOAD_ID,
            "data",
        ),

        Input(
            REVENUE_STRUCTURE_CATEGORY_EXCEL_BTN_ID,
            "n_clicks",
        ),

        State(
            REVENUE_STRUCTURE_CATEGORY_GRID_ID,
            "virtualRowData",
        ),

        State(
            REVENUE_STRUCTURE_CATEGORY_GRID_ID,
            "rowData",
        ),

        prevent_initial_call=True,
    )
    def export_category_excel(
        n_clicks,
        virtual_rows,
        all_rows,
    ):

        rows = (
            virtual_rows
            if virtual_rows is not None
            else all_rows
        )

        content = build_revenue_excel(
            rows=rows or [],

            sheet_name="Категории",
        )

        return dcc.send_bytes(
            content,

            "revenue_structure_categories.xlsx",
        )

    # =====================================================
    # Пол
    # =====================================================

    @app.callback(
        Output(
            REVENUE_STRUCTURE_GENDER_EXCEL_DOWNLOAD_ID,
            "data",
        ),

        Input(
            REVENUE_STRUCTURE_GENDER_EXCEL_BTN_ID,
            "n_clicks",
        ),

        State(
            REVENUE_STRUCTURE_GENDER_GRID_ID,
            "virtualRowData",
        ),

        State(
            REVENUE_STRUCTURE_GENDER_GRID_ID,
            "rowData",
        ),

        prevent_initial_call=True,
    )
    def export_gender_excel(
        n_clicks,
        virtual_rows,
        all_rows,
    ):

        rows = (
            virtual_rows
            if virtual_rows is not None
            else all_rows
        )

        content = build_revenue_excel(
            rows=rows or [],

            sheet_name="Пол",
        )

        return dcc.send_bytes(
            content,

            "revenue_structure_gender.xlsx",
        )