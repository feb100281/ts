# gear/app/daily_sales/stocks/export.py

from io import BytesIO
from zipfile import ZipFile, ZIP_DEFLATED

import pandas as pd
from dash import dcc, Input, Output, State, no_update

from .data import (
    get_default_stocks_date,
    get_stocks_export_data,
    get_stocks_by_warehouse_products,
)
from .excel import make_stocks_excel
from .maps import make_stocks_regions_map_png
from .charts import (
    make_stocks_sunburst_qty_html,
    make_stocks_treemap_qty_html,
    make_stocks_treemap_man_cost_html,
)

from ..ui import (
    STOCKS_DATE_PICKER_ID,
    STOCKS_EXPORT_BTN_ID,
    STOCKS_EXPORT_DOWNLOAD_ID,
    STOCKS_EXPORT_LOADING_ID,
)


def _make_stocks_zip(report_date) -> bytes:
    """
    Формирует ZIP-архив отчёта по остаткам.

    В архив входят:
    - Excel с общей детализацией и детализацией по складам;
    - карта остатков по регионам;
    - HTML-графики остатков.
    """

    report_date = pd.to_datetime(
        report_date
    ).date()

    file_date = report_date.strftime(
        "%Y-%m-%d"
    )

    # --------------------------------------------------------------
    # Основная детализация остатков
    #
    # Уровень:
    # nm_id + chrt_id
    # --------------------------------------------------------------
    stocks_df = get_stocks_export_data(
        report_date
    )

    # --------------------------------------------------------------
    # Детализация фактических остатков по складам
    #
    # Уровень:
    # регион + склад + nm_id + chrt_id
    # --------------------------------------------------------------
    warehouse_products_df = (
        get_stocks_by_warehouse_products(
            report_date
        )
    )

    # --------------------------------------------------------------
    # Excel
    # --------------------------------------------------------------
    excel_content = make_stocks_excel(
        df=stocks_df,
        report_date=report_date,
        warehouse_products_df=warehouse_products_df,
    )

    # --------------------------------------------------------------
    # Карта регионов
    # --------------------------------------------------------------
    map_content = make_stocks_regions_map_png(
        report_date
    )

    # --------------------------------------------------------------
    # Интерактивные HTML-графики
    # --------------------------------------------------------------
    sunburst_qty_content = (
        make_stocks_sunburst_qty_html(
            stocks_df,
            report_date,
        )
    )

    treemap_qty_content = (
        make_stocks_treemap_qty_html(
            stocks_df,
            report_date,
        )
    )

    treemap_man_cost_content = (
        make_stocks_treemap_man_cost_html(
            stocks_df,
            report_date,
        )
    )

    # --------------------------------------------------------------
    # ZIP
    # --------------------------------------------------------------
    zip_buffer = BytesIO()

    folder_name = (
        f"stocks_report_{file_date}"
    )

    with ZipFile(
        zip_buffer,
        mode="w",
        compression=ZIP_DEFLATED,
    ) as zip_file:

        zip_file.writestr(
            (
                f"{folder_name}/"
                f"stocks_{file_date}.xlsx"
            ),
            excel_content,
        )

        if map_content:
            zip_file.writestr(
                (
                    f"{folder_name}/"
                    f"map_regions_{file_date}.png"
                ),
                map_content,
            )

        if sunburst_qty_content:
            zip_file.writestr(
                (
                    f"{folder_name}/"
                    f"stocks_sunburst_qty_"
                    f"{file_date}.html"
                ),
                sunburst_qty_content,
            )

        if treemap_qty_content:
            zip_file.writestr(
                (
                    f"{folder_name}/"
                    f"stocks_treemap_qty_"
                    f"{file_date}.html"
                ),
                treemap_qty_content,
            )

        if treemap_man_cost_content:
            zip_file.writestr(
                (
                    f"{folder_name}/"
                    f"stocks_treemap_man_cost_"
                    f"{file_date}.html"
                ),
                treemap_man_cost_content,
            )

    zip_buffer.seek(0)

    return zip_buffer.read()


def register_stock_export_callbacks(app):
    """
    Регистрирует callback скачивания отчёта по остаткам.
    """

    @app.callback(
        Output(
            STOCKS_EXPORT_DOWNLOAD_ID,
            "data",
        ),
        Output(
            STOCKS_EXPORT_LOADING_ID,
            "children",
        ),
        Input(
            STOCKS_EXPORT_BTN_ID,
            "n_clicks",
        ),
        State(
            STOCKS_DATE_PICKER_ID,
            "value",
        ),
        prevent_initial_call=True,
    )
    def export_stocks_report(
        n_clicks,
        report_date,
    ):
        if not n_clicks:
            return no_update, no_update

        if not report_date:
            report_date = (
                get_default_stocks_date()
            )

        report_date = pd.to_datetime(
            report_date
        ).date()

        content = _make_stocks_zip(
            report_date
        )

        file_date = report_date.strftime(
            "%Y-%m-%d"
        )

        return (
            dcc.send_bytes(
                content,
                filename=(
                    f"stocks_report_"
                    f"{file_date}.zip"
                ),
            ),
            "",
        )


