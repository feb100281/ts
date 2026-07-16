# # gear/app/costs_control/callbacks.py
# from __future__ import annotations

# import pandas as pd
# from dash import Input, Output, State, no_update

# from .calculations import (
#     calculate_kpis,
# )
# from .charts import (
#     build_brand_summary_chart,
#     build_cv_distribution_chart,
#     build_median_deviation_chart,
#     build_top_cv_chart,
#     empty_figure,
# )
# from .config import DEFAULT_COST_TYPE
# from .data import (
#     get_price_analysis_data,
#     get_price_history_data,
# )
# from .export import (
#     build_csv_download,
#     build_excel_download,
# )
# from .filters import (
#     apply_all_analysis_filters,
#     build_filter_store,
#     filter_history_data,
#     get_filtered_analysis_from_store,
#     normalise_nm_id,
#     register_filter_callbacks,

# )
# from .ids import (
#     BRAND_FILTER_ID,
#     BRAND_SUMMARY_CHART_ID,
#     CATEGORY_FILTER_ID,
#     COST_TYPE_FILTER_ID,
#     CV_DISTRIBUTION_CHART_ID,
#     CV_RANK_FILTER_ID,
#     DATA_STORE_ID,
#     DATE_FILTER_ID,
#     DOWNLOAD_CSV_BTN_ID,
#     DOWNLOAD_EXCEL_BTN_ID,
#     DOWNLOAD_ID,
#     FILTERED_DATA_STORE_ID,
#     KPI_AVG_CV_ID,
#     KPI_CHANGED_PRODUCTS_ID,
#     KPI_CRITICAL_PRODUCTS_ID,
#     KPI_MAX_DECREASE_ID,
#     KPI_MAX_INCREASE_ID,
#     KPI_TOTAL_PRODUCTS_ID,
#     MEDIAN_DEVIATION_CHART_ID,
#     MEDIAN_DEVIATION_FILTER_ID,
#     SUPPLIER_FILTER_ID,
#     TOP_CV_CHART_ID,

# )
# from .modal import (
#     register_chart_product_modal_callbacks,
# )
# from .grid import register_grid_callbacks



# # ---------------------------------------------------------------------
# # Форматирование KPI
# # ---------------------------------------------------------------------


# def _format_integer(
#     value: int | float | None,
# ) -> str:
#     """
#     Форматирует целое число с пробелами между разрядами.
#     """

#     if value is None:
#         return "0"

#     try:
#         if pd.isna(value):
#             return "0"
#     except (TypeError, ValueError):
#         pass

#     try:
#         return (
#             f"{int(value):,}"
#             .replace(",", " ")
#         )
#     except (TypeError, ValueError):
#         return "0"


# def _format_percent(
#     value: float | None,
# ) -> str:
#     """
#     Форматирует процент с двумя знаками после запятой.
#     """

#     if value is None:
#         return "—"

#     try:
#         if pd.isna(value):
#             return "—"
#     except (TypeError, ValueError):
#         pass

#     try:
#         return (
#             f"{float(value):,.2f}%"
#             .replace(",", " ")
#         )
#     except (TypeError, ValueError):
#         return "—"


# # ---------------------------------------------------------------------
# # Пустой dashboard
# # ---------------------------------------------------------------------


# def _empty_dashboard_response():
#     """
#     Возвращает пустые значения для dashboard callback.
#     """

#     empty_cv = empty_figure(
#         "Нет данных для построения графика"
#     )

#     empty_top = empty_figure(
#         "Нет данных для построения графика"
#     )

#     empty_deviation = empty_figure(
#         "Нет данных для построения графика"
#     )

#     empty_brand = empty_figure(
#         "Нет данных для построения графика"
#     )

#     return (
#         {},
#         "0",
#         "0",
#         "0",
#         "—",
#         "—",
#         "—",
#         empty_cv,
#         empty_top,
#         empty_deviation,
#         empty_brand,

#     )


# # ---------------------------------------------------------------------
# # Регистрация callbacks
# # ---------------------------------------------------------------------


# def register_costs_control_callbacks(
#     app,
# ):
#     """
#     Регистрирует callbacks dashboard, истории,
#     экспорта, фильтров и модального окна.
#     """

#     # -----------------------------------------------------------------
#     # KPI, графики и основная таблица
#     # -----------------------------------------------------------------

#     @app.callback(
#         Output(
#             FILTERED_DATA_STORE_ID,
#             "data",
#         ),
#         Output(
#             KPI_TOTAL_PRODUCTS_ID,
#             "children",
#         ),
#         Output(
#             KPI_CHANGED_PRODUCTS_ID,
#             "children",
#         ),
#         Output(
#             KPI_CRITICAL_PRODUCTS_ID,
#             "children",
#         ),
#         Output(
#             KPI_AVG_CV_ID,
#             "children",
#         ),
#         Output(
#             KPI_MAX_INCREASE_ID,
#             "children",
#         ),
#         Output(
#             KPI_MAX_DECREASE_ID,
#             "children",
#         ),
#         Output(
#             CV_DISTRIBUTION_CHART_ID,
#             "figure",
#         ),
#         Output(
#             TOP_CV_CHART_ID,
#             "figure",
#         ),
#         Output(
#             MEDIAN_DEVIATION_CHART_ID,
#             "figure",
#         ),
#         Output(
#             BRAND_SUMMARY_CHART_ID,
#             "figure",
#         ),
       
#         Input(
#             DATA_STORE_ID,
#             "data",
#         ),
#         Input(
#             COST_TYPE_FILTER_ID,
#             "value",
#         ),
#         Input(
#             BRAND_FILTER_ID,
#             "value",
#         ),
#         Input(
#             CATEGORY_FILTER_ID,
#             "value",
#         ),
#         Input(
#             SUPPLIER_FILTER_ID,
#             "value",
#         ),
#         Input(
#             CV_RANK_FILTER_ID,
#             "value",
#         ),
#         Input(
#             MEDIAN_DEVIATION_FILTER_ID,
#             "value",
#         ),
#         Input(
#             DATE_FILTER_ID,
#             "value",
#         ),
#     )
#     def update_dashboard(
#         data_signal,
#         cost_type,
#         brands,
#         categories,
#         suppliers,
#         cv_ranks,
#         median_deviation_limit,
#         date_range,
#     ):
#         """
#         Пересчитывает dashboard на сервере.

#         DATA_STORE_ID используется как сигнал,
#         что исходные данные загружены или обновлены.
#         """

#         if not data_signal:
#             return _empty_dashboard_response()

#         selected_cost_type = (
#             cost_type
#             or DEFAULT_COST_TYPE
#         )

#         analysis_df = (
#             get_price_analysis_data()
#             .copy()
#         )

#         if analysis_df.empty:
#             return _empty_dashboard_response()

#         filtered_analysis = (
#             apply_all_analysis_filters(
#                 analysis_df,
#                 cost_type=selected_cost_type,
#                 brands=brands,
#                 categories=categories,
#                 suppliers=suppliers,
#                 cv_ranks=cv_ranks,
#                 median_deviation_limit=(
#                     median_deviation_limit
#                 ),
#                 date_range=date_range,
#             )
#         )

#         kpis = calculate_kpis(
#             filtered_analysis,
#             selected_cost_type,
#         )

#         filter_store = build_filter_store(
#             cost_type=selected_cost_type,
#             brands=brands,
#             categories=categories,
#             suppliers=suppliers,
#             cv_ranks=cv_ranks,
#             median_deviation_limit=(
#                 median_deviation_limit
#             ),
#             date_range=date_range,
#         )

#         return (
#             filter_store,

#             _format_integer(
#                 kpis.get(
#                     "total_products"
#                 )
#             ),

#             _format_integer(
#                 kpis.get(
#                     "changed_products"
#                 )
#             ),

#             _format_integer(
#                 kpis.get(
#                     "critical_products"
#                 )
#             ),

#             _format_percent(
#                 kpis.get(
#                     "average_cv"
#                 )
#             ),

#             _format_percent(
#                 kpis.get(
#                     "max_increase"
#                 )
#             ),

#             _format_percent(
#                 kpis.get(
#                     "max_decrease"
#                 )
#             ),

#             build_cv_distribution_chart(
#                 filtered_analysis,
#                 selected_cost_type,
#             ),

#             build_top_cv_chart(
#                 filtered_analysis,
#                 selected_cost_type,
#             ),

#             build_median_deviation_chart(
#                 filtered_analysis,
#                 selected_cost_type,
#             ),

#             build_brand_summary_chart(
#                 filtered_analysis,
#                 selected_cost_type,
#             ),

           
#         )
    
#     # -----------------------------------------------------------------
#     # Excel
#     # -----------------------------------------------------------------

#     @app.callback(
#         Output(
#             DOWNLOAD_ID,
#             "data",
#         ),
#         Input(
#             DOWNLOAD_EXCEL_BTN_ID,
#             "n_clicks",
#         ),
#         State(
#             FILTERED_DATA_STORE_ID,
#             "data",
#         ),
#         prevent_initial_call=True,
#     )
#     def download_excel_report(
#         n_clicks,
#         filter_store,
#     ):
#         """
#         Формирует Excel по текущим фильтрам.

#         Анализ и история повторно
#         фильтруются на сервере.
#         """

#         if (
#             not n_clicks
#             or not filter_store
#         ):
#             return no_update

#         filtered_analysis = (
#             get_filtered_analysis_from_store(
#                 filter_store
#             )
#         )

#         if filtered_analysis.empty:
#             return no_update

#         if "nm_id" not in filtered_analysis.columns:
#             return no_update

#         allowed_nm_ids = (
#             filtered_analysis["nm_id"]
#             .dropna()
#             .astype(str)
#             .map(normalise_nm_id)
#             .tolist()
#         )

#         history_df = (
#             get_price_history_data()
#             .copy()
#         )

#         filtered_history = filter_history_data(
#             history_df,
#             nm_ids=allowed_nm_ids,
#             suppliers=filter_store.get(
#                 "suppliers"
#             ),
#             date_range=filter_store.get(
#                 "date_range"
#             ),
#         )

#         return build_excel_download(
#             filtered_analysis,
#             filtered_history,
#         )

#     # -----------------------------------------------------------------
#     # CSV
#     # -----------------------------------------------------------------

#     @app.callback(
#         Output(
#             DOWNLOAD_ID,
#             "data",
#             allow_duplicate=True,
#         ),
#         Input(
#             DOWNLOAD_CSV_BTN_ID,
#             "n_clicks",
#         ),
#         State(
#             FILTERED_DATA_STORE_ID,
#             "data",
#         ),
#         prevent_initial_call=True,
#     )
#     def download_csv_report(
#         n_clicks,
#         filter_store,
#     ):
#         """
#         Формирует CSV по текущим фильтрам.
#         """

#         if (
#             not n_clicks
#             or not filter_store
#         ):
#             return no_update

#         filtered_analysis = (
#             get_filtered_analysis_from_store(
#                 filter_store
#             )
#         )

#         if filtered_analysis.empty:
#             return no_update

#         return build_csv_download(
#             filtered_analysis
#         )

#     # -----------------------------------------------------------------
#     # Внешние группы callbacks
#     # -----------------------------------------------------------------

#     register_filter_callbacks(app)
#     register_grid_callbacks(app)
#     register_chart_product_modal_callbacks(app)



# gear/app/costs_control/callbacks.py
from __future__ import annotations

import pandas as pd
from dash import (
    Input,
    Output,
    State,
    no_update,
)

from .calculations import calculate_kpis
from .charts import (
    build_brand_summary_chart,
    build_cv_distribution_chart,
    build_median_deviation_chart,
    build_top_cv_chart,
    empty_figure,
)
from .config import DEFAULT_COST_TYPE
from .data import (
    get_price_analysis_data,
    get_price_history_data,
)
from .export import (
    build_csv_download,
    build_excel_download,
)
from .filters import (
    apply_all_analysis_filters,
    build_filter_store,
    filter_history_data,
    get_filtered_analysis_from_store,
    normalise_nm_id,
    register_filter_callbacks,
)
from .grid import register_grid_callbacks
from .ids import (
    BRAND_FILTER_ID,
    BRAND_SUMMARY_CHART_ID,
    CATEGORY_FILTER_ID,
    COST_TYPE_FILTER_ID,
    CV_DISTRIBUTION_CHART_ID,
    CV_RANK_FILTER_ID,
    DATA_STORE_ID,
    DATE_FILTER_ID,
    DOWNLOAD_CSV_BTN_ID,
    DOWNLOAD_EXCEL_BTN_ID,
    DOWNLOAD_ID,
    FILTERED_DATA_STORE_ID,
    KPI_AVG_CV_ID,
    KPI_CHANGED_PRODUCTS_ID,
    KPI_CRITICAL_PRODUCTS_ID,
    KPI_MAX_DECREASE_ID,
    KPI_MAX_INCREASE_ID,
    KPI_TOTAL_PRODUCTS_ID,
    MEDIAN_DEVIATION_CHART_ID,
    MEDIAN_DEVIATION_FILTER_ID,
    SUPPLIER_FILTER_ID,
    TOP_CV_CHART_ID,
)
from .modal import (
    register_chart_product_modal_callbacks,
)


# ---------------------------------------------------------------------
# Форматирование KPI
# ---------------------------------------------------------------------


def _format_integer(
    value: int | float | None,
) -> str:
    """
    Форматирует целое число
    с пробелами между разрядами.
    """

    if value is None:
        return "0"

    try:
        if pd.isna(value):
            return "0"
    except (TypeError, ValueError):
        pass

    try:
        return (
            f"{int(value):,}"
            .replace(",", " ")
        )
    except (TypeError, ValueError):
        return "0"


def _format_percent(
    value: float | None,
) -> str:
    """
    Форматирует процент
    с двумя знаками после запятой.
    """

    if value is None:
        return "—"

    try:
        if pd.isna(value):
            return "—"
    except (TypeError, ValueError):
        pass

    try:
        return (
            f"{float(value):,.2f}%"
            .replace(",", " ")
        )
    except (TypeError, ValueError):
        return "—"


# ---------------------------------------------------------------------
# Пустой dashboard
# ---------------------------------------------------------------------


def _empty_dashboard_response():
    """
    Возвращает пустые значения
    для dashboard callback.

    Количество значений должно совпадать
    с количеством Output основного callback.
    """

    empty_cv = empty_figure(
        "Нет данных для построения графика"
    )

    empty_top = empty_figure(
        "Нет данных для построения графика"
    )

    empty_deviation = empty_figure(
        "Нет данных для построения графика"
    )

    empty_brand = empty_figure(
        "Нет данных для построения графика"
    )

    return (
        {},
        "0",
        "0",
        "0",
        "—",
        "—",
        "—",
        empty_cv,
        empty_top,
        empty_deviation,
        empty_brand,
    )


# ---------------------------------------------------------------------
# Регистрация callbacks
# ---------------------------------------------------------------------


def register_costs_control_callbacks(
    app,
):
    """
    Регистрирует:

    - основной dashboard;
    - общий Excel и CSV;
    - callbacks фильтров;
    - callbacks таблиц;
    - callbacks модального окна.
    """

    # -----------------------------------------------------------------
    # KPI и графики
    # -----------------------------------------------------------------

    @app.callback(
        Output(
            FILTERED_DATA_STORE_ID,
            "data",
        ),
        Output(
            KPI_TOTAL_PRODUCTS_ID,
            "children",
        ),
        Output(
            KPI_CHANGED_PRODUCTS_ID,
            "children",
        ),
        Output(
            KPI_CRITICAL_PRODUCTS_ID,
            "children",
        ),
        Output(
            KPI_AVG_CV_ID,
            "children",
        ),
        Output(
            KPI_MAX_INCREASE_ID,
            "children",
        ),
        Output(
            KPI_MAX_DECREASE_ID,
            "children",
        ),
        Output(
            CV_DISTRIBUTION_CHART_ID,
            "figure",
        ),
        Output(
            TOP_CV_CHART_ID,
            "figure",
        ),
        Output(
            MEDIAN_DEVIATION_CHART_ID,
            "figure",
        ),
        Output(
            BRAND_SUMMARY_CHART_ID,
            "figure",
        ),
        Input(
            DATA_STORE_ID,
            "data",
        ),
        Input(
            COST_TYPE_FILTER_ID,
            "value",
        ),
        Input(
            BRAND_FILTER_ID,
            "value",
        ),
        Input(
            CATEGORY_FILTER_ID,
            "value",
        ),
        Input(
            SUPPLIER_FILTER_ID,
            "value",
        ),
        Input(
            CV_RANK_FILTER_ID,
            "value",
        ),
        Input(
            MEDIAN_DEVIATION_FILTER_ID,
            "value",
        ),
        Input(
            DATE_FILTER_ID,
            "value",
        ),
    )
    def update_dashboard(
        data_signal,
        cost_type,
        brands,
        categories,
        suppliers,
        cv_ranks,
        median_deviation_limit,
        date_range,
    ):
        """
        Пересчитывает KPI и графики.

        В FILTERED_DATA_STORE_ID записывается
        только маленький словарь параметров фильтров.

        Полная таблица товаров здесь
        в браузер не передаётся.
        """

        if not data_signal:
            return _empty_dashboard_response()

        selected_cost_type = (
            cost_type
            or DEFAULT_COST_TYPE
        )

        analysis_df = (
            get_price_analysis_data()
            .copy()
        )

        if analysis_df.empty:
            return _empty_dashboard_response()

        filtered_analysis = (
            apply_all_analysis_filters(
                analysis_df,
                cost_type=selected_cost_type,
                brands=brands,
                categories=categories,
                suppliers=suppliers,
                cv_ranks=cv_ranks,
                median_deviation_limit=(
                    median_deviation_limit
                ),
                date_range=date_range,
            )
        )

        filter_store = build_filter_store(
            cost_type=selected_cost_type,
            brands=brands,
            categories=categories,
            suppliers=suppliers,
            cv_ranks=cv_ranks,
            median_deviation_limit=(
                median_deviation_limit
            ),
            date_range=date_range,
        )

        if filtered_analysis.empty:
            empty_response = (
                _empty_dashboard_response()
            )

            return (
                filter_store,
                *empty_response[1:],
            )

        kpis = calculate_kpis(
            filtered_analysis,
            selected_cost_type,
        )

        return (
            filter_store,

            _format_integer(
                kpis.get(
                    "total_products"
                )
            ),

            _format_integer(
                kpis.get(
                    "changed_products"
                )
            ),

            _format_integer(
                kpis.get(
                    "critical_products"
                )
            ),

            _format_percent(
                kpis.get(
                    "average_cv"
                )
            ),

            _format_percent(
                kpis.get(
                    "max_increase"
                )
            ),

            _format_percent(
                kpis.get(
                    "max_decrease"
                )
            ),

            build_cv_distribution_chart(
                filtered_analysis,
                selected_cost_type,
            ),

            build_top_cv_chart(
                filtered_analysis,
                selected_cost_type,
            ),

            build_median_deviation_chart(
                filtered_analysis,
                selected_cost_type,
            ),

            build_brand_summary_chart(
                filtered_analysis,
                selected_cost_type,
            ),
        )

    # -----------------------------------------------------------------
    # Общий Excel
    # -----------------------------------------------------------------

    @app.callback(
        Output(
            DOWNLOAD_ID,
            "data",
        ),
        Input(
            DOWNLOAD_EXCEL_BTN_ID,
            "n_clicks",
        ),
        State(
            FILTERED_DATA_STORE_ID,
            "data",
        ),
        prevent_initial_call=True,
    )
    def download_excel_report(
        n_clicks,
        filter_store,
    ):
        """
        Формирует полный Excel:

        - анализ товаров;
        - история УПД.

        Данные повторно формируются на сервере.
        """

        if (
            not n_clicks
            or not filter_store
        ):
            return no_update

        filtered_analysis = (
            get_filtered_analysis_from_store(
                filter_store
            )
        )

        if filtered_analysis.empty:
            return no_update

        if (
            "nm_id"
            not in filtered_analysis.columns
        ):
            return no_update

        allowed_nm_ids = (
            filtered_analysis["nm_id"]
            .dropna()
            .astype(str)
            .map(normalise_nm_id)
            .tolist()
        )

        if not allowed_nm_ids:
            return no_update

        history_df = (
            get_price_history_data()
            .copy()
        )

        filtered_history = filter_history_data(
            history_df,
            nm_ids=allowed_nm_ids,
            suppliers=filter_store.get(
                "suppliers"
            ),
            date_range=None,
        )

        return build_excel_download(
            filtered_analysis,
            filtered_history,
        )

    # -----------------------------------------------------------------
    # Общий CSV
    # -----------------------------------------------------------------

    @app.callback(
        Output(
            DOWNLOAD_ID,
            "data",
            allow_duplicate=True,
        ),
        Input(
            DOWNLOAD_CSV_BTN_ID,
            "n_clicks",
        ),
        State(
            FILTERED_DATA_STORE_ID,
            "data",
        ),
        prevent_initial_call=True,
    )
    def download_csv_report(
        n_clicks,
        filter_store,
    ):
        """
        Формирует CSV анализа товаров.

        Данные повторно фильтруются на сервере.
        """

        if (
            not n_clicks
            or not filter_store
        ):
            return no_update

        filtered_analysis = (
            get_filtered_analysis_from_store(
                filter_store
            )
        )

        if filtered_analysis.empty:
            return no_update

        return build_csv_download(
            filtered_analysis
        )

    # -----------------------------------------------------------------
    # Внешние группы callbacks
    # -----------------------------------------------------------------

    register_filter_callbacks(app)
    register_grid_callbacks(app)
    register_chart_product_modal_callbacks(app)