from __future__ import annotations

from datetime import datetime
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

from dash import Input, Output, dcc, no_update

from .charts import (

    make_cv_distribution_html,
  
    # make_price_history_html,
    make_top_cv_products_html,
)
from .config import (
    PRICE_ANALYSIS_DOWNLOAD_ID,
    PRICE_ANALYSIS_EXCEL_PREFIX,
    PRICE_ANALYSIS_EXPORT_BTN_ID,
    PRICE_ANALYSIS_FOLDER_PREFIX,
    PRICE_ANALYSIS_LOADING_ID,
)
from .data import (
    get_price_analysis_data,
    get_price_analysis_period,
    get_price_history_data,
)
from .excel import make_price_analysis_excel


def _make_price_analysis_zip() -> bytes:
    analysis_df = get_price_analysis_data()
    history_df = get_price_history_data()

    if analysis_df.empty:
        raise ValueError("Нет данных для формирования анализа себестоимости.")

    start_date, end_date = get_price_analysis_period(analysis_df)
    file_date = datetime.now().strftime("%Y-%m-%d")
    folder_name = f"{PRICE_ANALYSIS_FOLDER_PREFIX}_{file_date}"

    excel_content = make_price_analysis_excel(
        analysis_df=analysis_df,
        history_df=history_df,
        start_date=start_date,
        end_date=end_date,
    )

    cv_distribution_html = make_cv_distribution_html(analysis_df)
    top_cv_html = make_top_cv_products_html(analysis_df)
    # history_html = make_price_history_html(
    #     history_df=history_df,
    #     analysis_df=analysis_df,
    # )
  

    buffer = BytesIO()

    with ZipFile(buffer, "w", ZIP_DEFLATED) as zip_file:
        zip_file.writestr(
            f"{folder_name}/"
            f"{PRICE_ANALYSIS_EXCEL_PREFIX}_{file_date}.xlsx",
            excel_content,
        )

        zip_file.writestr(
            f"{folder_name}/charts/"
            f"01_cv_distribution_{file_date}.html",
            cv_distribution_html,
        )

        zip_file.writestr(
            f"{folder_name}/charts/"
            f"02_top_cv_products_{file_date}.html",
            top_cv_html,
        )

        

        # zip_file.writestr(
        #     f"{folder_name}/charts/"
        #     f"03_price_history_{file_date}.html",
        #     history_html,
        # )

        

        readme = (
            "АНАЛИЗ СЕБЕСТОИМОСТИ\n\n"
            "Состав отчета:\n"
            "1. Excel — сводка, критические товары, все товары и история цен.\n"
            "2. HTML-графики — интерактивные, открываются обычным браузером.\n"
            f"Период УПД: {start_date} — {end_date}.\n"
        )

        zip_file.writestr(
            f"{folder_name}/README.txt",
            readme.encode("utf-8"),
        )

    buffer.seek(0)
    return buffer.read()


def register_price_analysis_export_callbacks(app):
    @app.callback(
        Output(PRICE_ANALYSIS_DOWNLOAD_ID, "data"),
        Output(PRICE_ANALYSIS_LOADING_ID, "children"),
        Input(PRICE_ANALYSIS_EXPORT_BTN_ID, "n_clicks"),
        prevent_initial_call=True,
    )
    def export_price_analysis(n_clicks):
        if not n_clicks:
            return no_update, no_update

        content = _make_price_analysis_zip()
        file_date = datetime.now().strftime("%Y-%m-%d")

        return (
            dcc.send_bytes(
                content,
                filename=(
                    f"{PRICE_ANALYSIS_FOLDER_PREFIX}_{file_date}.zip"
                ),
            ),
            "",
        )
