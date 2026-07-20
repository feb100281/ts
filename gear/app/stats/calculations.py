# # gear/app/stats/calculations.py
# from __future__ import annotations

# import numpy as np
# import pandas as pd

# from .config import (
#     MAX_LAG_PERIODS,
#     ROLLING_WINDOWS,
# )


# WEEKDAY_NAMES = {
#     0: "Понедельник",
#     1: "Вторник",
#     2: "Среда",
#     3: "Четверг",
#     4: "Пятница",
#     5: "Суббота",
#     6: "Воскресенье",
# }


# WEEKDAY_ORDER = [
#     "Понедельник",
#     "Вторник",
#     "Среда",
#     "Четверг",
#     "Пятница",
#     "Суббота",
#     "Воскресенье",
# ]


# MONTH_NAMES = {
#     1: "Январь",
#     2: "Февраль",
#     3: "Март",
#     4: "Апрель",
#     5: "Май",
#     6: "Июнь",
#     7: "Июль",
#     8: "Август",
#     9: "Сентябрь",
#     10: "Октябрь",
#     11: "Ноябрь",
#     12: "Декабрь",
# }


# MONTH_ORDER = [
#     "Январь",
#     "Февраль",
#     "Март",
#     "Апрель",
#     "Май",
#     "Июнь",
#     "Июль",
#     "Август",
#     "Сентябрь",
#     "Октябрь",
#     "Ноябрь",
#     "Декабрь",
# ]


# def safe_divide(
#     numerator,
#     denominator,
# ):
#     if denominator is None:
#         return np.nan

#     try:
#         if pd.isna(denominator):
#             return np.nan
#     except TypeError:
#         pass

#     if denominator == 0:
#         return np.nan

#     return numerator / denominator


# # def aggregate_data(
# #     df: pd.DataFrame,
# #     aggregation: str,
# # ) -> pd.DataFrame:
# #     """
# #     Агрегация данных:

# #     day   - день;
# #     week  - неделя с понедельника;
# #     month - календарный месяц.
# #     """

# #     if df.empty:
# #         return pd.DataFrame()

# #     work = df.copy()

# #     work["date"] = pd.to_datetime(
# #         work["date"],
# #         errors="coerce",
# #     )

# #     work = work[
# #         work["date"].notna()
# #     ].copy()

# #     if aggregation == "month":
# #         work["period"] = (
# #             work["date"]
# #             .dt.to_period("M")
# #             .dt.to_timestamp()
# #         )

# #     elif aggregation == "week":
# #         work["period"] = (
# #             work["date"]
# #             - pd.to_timedelta(
# #                 work["date"].dt.weekday,
# #                 unit="D",
# #             )
# #         )

# #     else:
# #         work["period"] = (
# #             work["date"]
# #             .dt.normalize()
# #         )

# #     result = (
# #         work.groupby(
# #             "period",
# #             as_index=False,
# #         )
# #         .agg(
# #             revenue=(
# #                 "revenue",
# #                 "sum",
# #             ),
# #             marketing_costs=(
# #                 "marketing_costs",
# #                 "sum",
# #             ),
# #             quantity=(
# #                 "quantity",
# #                 "sum",
# #             ),
# #         )
# #     )

# #     result["average_price"] = (
# #         result["revenue"]
# #         / result["quantity"].replace(
# #             0,
# #             np.nan,
# #         )
# #     )

# #     result["marketing_share"] = (
# #         result["marketing_costs"]
# #         / result["revenue"].replace(
# #             0,
# #             np.nan,
# #         )
# #         * 100
# #     )

# #     result["roas"] = (
# #         result["revenue"]
# #         / result[
# #             "marketing_costs"
# #         ].replace(
# #             0,
# #             np.nan,
# #         )
# #     )

# #     return (
# #         result.sort_values(
# #             "period"
# #         )
# #         .reset_index(drop=True)
# #     )

# def aggregate_data(
#     df: pd.DataFrame,
#     aggregation: str,
# ) -> pd.DataFrame:
#     """
#     Агрегирует дневные показатели
#     по дням, неделям или месяцам.

#     ВАЖНО:
#     средние цены НЕ суммируются.

#     Сначала суммируются:
#         выручка,
#         количество,
#         себестоимость и т.д.

#     После этого средние показатели
#     пересчитываются заново.
#     """

#     if df.empty:
#         return pd.DataFrame()

#     work = df.copy()

#     work["date"] = pd.to_datetime(
#         work["date"],
#         errors="coerce",
#     )

#     work = work[
#         work["date"].notna()
#     ].copy()

#     if aggregation == "month":
#         work["period"] = (
#             work["date"]
#             .dt.to_period("M")
#             .dt.to_timestamp()
#         )

#     elif aggregation == "week":
#         work["period"] = (
#             work["date"]
#             - pd.to_timedelta(
#                 work["date"].dt.weekday,
#                 unit="D",
#             )
#         )

#     else:
#         work["period"] = (
#             work["date"]
#             .dt.normalize()
#         )

#     result = (
#         work.groupby(
#             "period",
#             as_index=False,
#         )
#         .agg(
#             quantity=(
#                 "quantity",
#                 "sum",
#             ),

#             revenue=(
#                 "revenue",
#                 "sum",
#             ),

#             retail_revenue=(
#                 "retail_revenue",
#                 "sum",
#             ),

#             cogs=(
#                 "cogs",
#                 "sum",
#             ),

#             cogs_man=(
#                 "cogs_man",
#                 "sum",
#             ),

#             net_comission=(
#                 "net_comission",
#                 "sum",
#             ),

#             wb_costs=(
#                 "wb_costs",
#                 "sum",
#             ),

#             marketing_costs=(
#                 "marketing_costs",
#                 "sum",
#             ),

#             logistics_costs=(
#                 "logistics_costs",
#                 "sum",
#             ),

#             storage_costs=(
#                 "storage_costs",
#                 "sum",
#             ),

#             acceptance_costs=(
#                 "acceptance_costs",
#                 "sum",
#             ),

#             penalties_costs=(
#                 "penalties_costs",
#                 "sum",
#             ),
#         )
#     )

#     # =========================================================
#     # Средняя наша цена реализации БЕЗ НДС
#     # =========================================================

#     result["average_price"] = (
#         result["revenue"]
#         / result[
#             "quantity"
#         ].replace(
#             0,
#             np.nan,
#         )
#     )

#     # =========================================================
#     # Средняя цена реализации WB БЕЗ НДС
#     # =========================================================

#     result[
#         "average_retail_price"
#     ] = (
#         result["retail_revenue"]
#         / result[
#             "quantity"
#         ].replace(
#             0,
#             np.nan,
#         )
#     )

#     # =========================================================
#     # Средняя себестоимость
#     # =========================================================

#     result[
#         "average_cogs"
#     ] = (
#         result["cogs"]
#         / result[
#             "quantity"
#         ].replace(
#             0,
#             np.nan,
#         )
#     )

#     result[
#         "average_cogs_man"
#     ] = (
#         result["cogs_man"]
#         / result[
#             "quantity"
#         ].replace(
#             0,
#             np.nan,
#         )
#     )

#     # =========================================================
#     # Доля маркетинга
#     # =========================================================

#     result[
#         "marketing_share"
#     ] = (
#         result[
#             "marketing_costs"
#         ]
#         / result[
#             "revenue"
#         ].replace(
#             0,
#             np.nan,
#         )
#         * 100
#     )

#     # =========================================================
#     # ROAS
#     # =========================================================

#     result["roas"] = (
#         result["revenue"]
#         / result[
#             "marketing_costs"
#         ].replace(
#             0,
#             np.nan,
#         )
#     )

#     # =========================================================
#     # Валовая прибыль
#     # =========================================================

#     result[
#         "gross_profit"
#     ] = (
#         result["revenue"]
#         -
#         result["cogs"]
#     )

#     result[
#         "gross_profit_man"
#     ] = (
#         result["revenue"]
#         -
#         result["cogs_man"]
#     )

#     # =========================================================
#     # Маржа после комиссии
#     # =========================================================

#     result["margin"] = (
#         result["revenue"]
#         -
#         result["cogs"]
#         +
#         result["net_comission"]
#     )

#     result["margin_man"] = (
#         result["revenue"]
#         -
#         result["cogs_man"]
#         +
#         result["net_comission"]
#     )

#     # =========================================================
#     # Финансовый результат WB
#     # =========================================================

#     result["wb_result"] = (
#         result["revenue"]
#         -
#         result["cogs_man"]
#         +
#         result["net_comission"]
#         -
#         result["wb_costs"]
#     )

#     # =========================================================
#     # Маржинальность
#     # =========================================================

#     result[
#         "margin_percent"
#     ] = (
#         result["margin"]
#         / result[
#             "revenue"
#         ].replace(
#             0,
#             np.nan,
#         )
#         * 100
#     )

#     result[
#         "margin_man_percent"
#     ] = (
#         result["margin_man"]
#         / result[
#             "revenue"
#         ].replace(
#             0,
#             np.nan,
#         )
#         * 100
#     )

#     return (
#         result.sort_values(
#             "period"
#         )
#         .reset_index(
#             drop=True
#         )
#     )

# def calculate_correlation(
#     x: pd.Series,
#     y: pd.Series,
#     method: str = "pearson",
# ) -> float:
#     """
#     Безопасный расчёт корреляции.
#     """

#     clean = pd.DataFrame(
#         {
#             "x": pd.to_numeric(
#                 x,
#                 errors="coerce",
#             ),
#             "y": pd.to_numeric(
#                 y,
#                 errors="coerce",
#             ),
#         }
#     ).dropna()

#     if len(clean) < 3:
#         return np.nan

#     if (
#         clean["x"].nunique() <= 1
#         or clean["y"].nunique() <= 1
#     ):
#         return np.nan

#     return float(
#         clean["x"].corr(
#             clean["y"],
#             method=method,
#         )
#     )


# def calculate_lag_correlations(
#     df: pd.DataFrame,
#     max_lag: int = MAX_LAG_PERIODS,
# ) -> pd.DataFrame:
#     """
#     Проверяет связь:

#     маркетинг периода T
#     с выручкой периода T + lag.

#     lag=0:
#         маркетинг сейчас -> выручка сейчас

#     lag=1:
#         маркетинг сейчас -> выручка следующего периода
#     """

#     if df.empty:
#         return pd.DataFrame()

#     work = (
#         df.copy()
#         .sort_values("period")
#         .reset_index(drop=True)
#     )

#     rows = []

#     for lag in range(
#         0,
#         max_lag + 1,
#     ):
#         future_revenue = (
#             work["revenue"]
#             .shift(-lag)
#         )

#         pearson = (
#             calculate_correlation(
#                 work[
#                     "marketing_costs"
#                 ],
#                 future_revenue,
#                 method="pearson",
#             )
#         )

#         spearman = (
#             calculate_correlation(
#                 work[
#                     "marketing_costs"
#                 ],
#                 future_revenue,
#                 method="spearman",
#             )
#         )

#         rows.append(
#             {
#                 "lag": lag,
#                 "pearson": pearson,
#                 "spearman": spearman,
#                 "r2": (
#                     pearson ** 2
#                     if pd.notna(
#                         pearson
#                     )
#                     else np.nan
#                 ),
#             }
#         )

#     return pd.DataFrame(
#         rows
#     )


# def calculate_rolling_correlation(
#     df: pd.DataFrame,
#     aggregation: str,
# ) -> pd.DataFrame:
#     """
#     Скользящая корреляция
#     маркетинг <-> выручка.
#     """

#     if df.empty:
#         return pd.DataFrame()

#     work = (
#         df.copy()
#         .sort_values("period")
#         .reset_index(drop=True)
#     )

#     window = (
#         ROLLING_WINDOWS.get(
#             aggregation,
#             8,
#         )
#     )

#     min_periods = max(
#         3,
#         window // 2,
#     )

#     work[
#         "rolling_correlation"
#     ] = (
#         work[
#             "marketing_costs"
#         ]
#         .rolling(
#             window=window,
#             min_periods=min_periods,
#         )
#         .corr(
#             work["revenue"]
#         )
#     )

#     return work


# def calculate_price_elasticity(
#     df: pd.DataFrame,
# ) -> pd.DataFrame:
#     """
#     Proxy-оценка ценовой эластичности:

#     % изменения количества
#     ----------------------
#     % изменения средней цены

#     Это не причинная оценка,
#     а аналитический индикатор.
#     """

#     if df.empty:
#         return pd.DataFrame()

#     work = (
#         df.copy()
#         .sort_values("period")
#         .reset_index(drop=True)
#     )

#     work[
#         "price_change_pct"
#     ] = (
#         work["average_price"]
#         .pct_change(
#             fill_method=None
#         )
#         * 100
#     )

#     work[
#         "quantity_change_pct"
#     ] = (
#         work["quantity"]
#         .pct_change(
#             fill_method=None
#         )
#         * 100
#     )

#     work[
#         "revenue_change_pct"
#     ] = (
#         work["revenue"]
#         .pct_change(
#             fill_method=None
#         )
#         * 100
#     )

#     work["elasticity"] = (
#         work[
#             "quantity_change_pct"
#         ]
#         / work[
#             "price_change_pct"
#         ].replace(
#             0,
#             np.nan,
#         )
#     )

#     # Убираем технически бессмысленные
#     # бесконечные значения.
#     work = work.replace(
#         [
#             np.inf,
#             -np.inf,
#         ],
#         np.nan,
#     )

#     return work


# def build_weekday_analysis(
#     daily_df: pd.DataFrame,
# ) -> pd.DataFrame:
#     """
#     Анализ сезонности по дням недели.
#     """

#     if daily_df.empty:
#         return pd.DataFrame()

#     work = daily_df.copy()

#     work["date"] = pd.to_datetime(
#         work["date"],
#         errors="coerce",
#     )

#     work = work[
#         work["date"].notna()
#     ].copy()

#     work["weekday_number"] = (
#         work["date"].dt.weekday
#     )

#     result = (
#         work.groupby(
#             "weekday_number",
#             as_index=False,
#         )
#         .agg(
#             average_revenue=(
#                 "revenue",
#                 "mean",
#             ),
#             median_revenue=(
#                 "revenue",
#                 "median",
#             ),
#             average_marketing=(
#                 "marketing_costs",
#                 "mean",
#             ),
#             average_quantity=(
#                 "quantity",
#                 "mean",
#             ),
#             days_count=(
#                 "date",
#                 "count",
#             ),
#         )
#     )

#     result["weekday"] = (
#         result[
#             "weekday_number"
#         ].map(
#             WEEKDAY_NAMES
#         )
#     )

#     overall_average = (
#         work["revenue"].mean()
#     )

#     if overall_average:
#         result[
#             "revenue_deviation_pct"
#         ] = (
#             (
#                 result[
#                     "average_revenue"
#                 ]
#                 / overall_average
#             )
#             - 1
#         ) * 100
#     else:
#         result[
#             "revenue_deviation_pct"
#         ] = np.nan

#     result["roas"] = (
#         result[
#             "average_revenue"
#         ]
#         / result[
#             "average_marketing"
#         ].replace(
#             0,
#             np.nan,
#         )
#     )

#     return result


# def build_month_analysis(
#     daily_df: pd.DataFrame,
# ) -> pd.DataFrame:
#     """
#     Средняя статистика календарных месяцев.

#     То есть все январские дни
#     сравниваются со всеми февральскими и т.д.
#     """

#     if daily_df.empty:
#         return pd.DataFrame()

#     work = daily_df.copy()

#     work["date"] = pd.to_datetime(
#         work["date"],
#         errors="coerce",
#     )

#     work = work[
#         work["date"].notna()
#     ].copy()

#     work["month_number"] = (
#         work["date"].dt.month
#     )

#     result = (
#         work.groupby(
#             "month_number",
#             as_index=False,
#         )
#         .agg(
#             average_revenue=(
#                 "revenue",
#                 "mean",
#             ),
#             median_revenue=(
#                 "revenue",
#                 "median",
#             ),
#             average_marketing=(
#                 "marketing_costs",
#                 "mean",
#             ),
#             average_quantity=(
#                 "quantity",
#                 "mean",
#             ),
#             days_count=(
#                 "date",
#                 "count",
#             ),
#         )
#     )

#     result["month"] = (
#         result[
#             "month_number"
#         ].map(
#             MONTH_NAMES
#         )
#     )

#     overall_average = (
#         work["revenue"].mean()
#     )

#     if overall_average:
#         result[
#             "revenue_deviation_pct"
#         ] = (
#             (
#                 result[
#                     "average_revenue"
#                 ]
#                 / overall_average
#             )
#             - 1
#         ) * 100
#     else:
#         result[
#             "revenue_deviation_pct"
#         ] = np.nan

#     result["roas"] = (
#         result[
#             "average_revenue"
#         ]
#         / result[
#             "average_marketing"
#         ].replace(
#             0,
#             np.nan,
#         )
#     )

#     return result


# def calculate_correlation_matrix(
#     df: pd.DataFrame,
#     method: str = "pearson",
# ) -> pd.DataFrame:
#     """
#     Корреляционная матрица
#     числовых факторов.
#     """

#     if df.empty:
#         return pd.DataFrame()

#     columns = [
#     "revenue",
#     "quantity",
#     "average_price",
#     "average_retail_price",
#     "marketing_costs",
#     "logistics_costs",
#     "net_comission",
#     "cogs_man",
#     "margin_man",
#     "wb_result",
#     "roas",
# ]
#     available_columns = [
#         column
#         for column in columns
#         if column in df.columns
#     ]

#     if len(
#         available_columns
#     ) < 2:
#         return pd.DataFrame()

#     return (
#         df[
#             available_columns
#         ]
#         .corr(
#             method=method
#         )
#     )


# def detect_anomalies(
#     df: pd.DataFrame,
# ) -> pd.DataFrame:
#     """
#     Находит интересные периоды:

#     1. маркетинг вырос >20%,
#        выручка упала;

#     2. маркетинг вырос >30%,
#        выручка изменилась менее чем на 5%;

#     3. цена выросла >10%,
#        количество упало >15%;

#     4. выручка выросла >20%
#        без существенного роста маркетинга.
#     """

#     if df.empty:
#         return pd.DataFrame()

#     work = (
#         df.copy()
#         .sort_values("period")
#         .reset_index(drop=True)
#     )

#     work[
#         "marketing_change_pct"
#     ] = (
#         work[
#             "marketing_costs"
#         ]
#         .pct_change(
#             fill_method=None
#         )
#         * 100
#     )

#     work[
#         "revenue_change_pct"
#     ] = (
#         work["revenue"]
#         .pct_change(
#             fill_method=None
#         )
#         * 100
#     )

#     work[
#         "price_change_pct"
#     ] = (
#         work["average_price"]
#         .pct_change(
#             fill_method=None
#         )
#         * 100
#     )

#     work[
#         "quantity_change_pct"
#     ] = (
#         work["quantity"]
#         .pct_change(
#             fill_method=None
#         )
#         * 100
#     )

#     work["anomaly_type"] = None

#     condition_1 = (
#         (
#             work[
#                 "marketing_change_pct"
#             ] > 20
#         )
#         &
#         (
#             work[
#                 "revenue_change_pct"
#             ] < 0
#         )
#     )

#     condition_2 = (
#         (
#             work[
#                 "marketing_change_pct"
#             ] > 30
#         )
#         &
#         (
#             work[
#                 "revenue_change_pct"
#             ].abs() < 5
#         )
#     )

#     condition_3 = (
#         (
#             work[
#                 "price_change_pct"
#             ] > 10
#         )
#         &
#         (
#             work[
#                 "quantity_change_pct"
#             ] < -15
#         )
#     )

#     condition_4 = (
#         (
#             work[
#                 "revenue_change_pct"
#             ] > 20
#         )
#         &
#         (
#             work[
#                 "marketing_change_pct"
#             ].fillna(0) < 5
#         )
#     )

#     work.loc[
#         condition_1,
#         "anomaly_type",
#     ] = (
#         "Маркетинг вырос, "
#         "выручка снизилась"
#     )

#     work.loc[
#         condition_2,
#         "anomaly_type",
#     ] = (
#         "Маркетинг вырос, "
#         "выручка почти не изменилась"
#     )

#     work.loc[
#         condition_3,
#         "anomaly_type",
#     ] = (
#         "Цена выросла, "
#         "количество снизилось"
#     )

#     work.loc[
#         condition_4,
#         "anomaly_type",
#     ] = (
#         "Выручка выросла "
#         "без роста маркетинга"
#     )

#     return (
#         work[
#             work[
#                 "anomaly_type"
#             ].notna()
#         ]
#         .reset_index(drop=True)
#     )


# def calculate_kpis(
#     daily_df: pd.DataFrame,
#     aggregated_df: pd.DataFrame,
# ) -> dict:
#     """
#     Основные KPI приложения.
#     """

#     if daily_df.empty:
#         return {}

#     revenue = float(
#         daily_df[
#             "revenue"
#         ].sum()
#     )

#     marketing = float(
#         daily_df[
#             "marketing_costs"
#         ].sum()
#     )

#     marketing_share = (
#         safe_divide(
#             marketing,
#             revenue,
#         )
#     )

#     if pd.notna(
#         marketing_share
#     ):
#         marketing_share *= 100

#     roas = safe_divide(
#         revenue,
#         marketing,
#     )

#     marketing_corr = (
#         calculate_correlation(
#             aggregated_df[
#                 "marketing_costs"
#             ],
#             aggregated_df[
#                 "revenue"
#             ],
#             method="pearson",
#         )
#     )

#     price_corr = (
#         calculate_correlation(
#             aggregated_df[
#                 "average_price"
#             ],
#             aggregated_df[
#                 "quantity"
#             ],
#             method="pearson",
#         )
#     )

#     lag_df = (
#         calculate_lag_correlations(
#             aggregated_df
#         )
#     )

#     best_lag = None
#     best_lag_corr = None

#     if not lag_df.empty:
#         valid_lags = (
#             lag_df.dropna(
#                 subset=[
#                     "pearson"
#                 ]
#             )
#             .copy()
#         )

#         if not valid_lags.empty:
#             best_index = (
#                 valid_lags[
#                     "pearson"
#                 ]
#                 .abs()
#                 .idxmax()
#             )

#             best_row = (
#                 valid_lags.loc[
#                     best_index
#                 ]
#             )

#             best_lag = int(
#                 best_row[
#                     "lag"
#                 ]
#             )

#             best_lag_corr = float(
#                 best_row[
#                     "pearson"
#                 ]
#             )

#     weekday_df = (
#         build_weekday_analysis(
#             daily_df
#         )
#     )

#     best_weekday = None

#     if not weekday_df.empty:
#         best_index = (
#             weekday_df[
#                 "average_revenue"
#             ].idxmax()
#         )

#         best_weekday = (
#             weekday_df.loc[
#                 best_index,
#                 "weekday",
#             ]
#         )

#     return {
#         "revenue": revenue,
#         "marketing": marketing,
#         "marketing_share": (
#             marketing_share
#         ),
#         "roas": roas,
#         "marketing_corr": (
#             marketing_corr
#         ),
#         "price_corr": (
#             price_corr
#         ),
#         "best_lag": (
#             best_lag
#         ),
#         "best_lag_corr": (
#             best_lag_corr
#         ),
#         "best_weekday": (
#             best_weekday
#         ),
#     }


# def correlation_strength(
#     value: float | None,
# ) -> str:
#     if value is None:
#         return "не определена"

#     if pd.isna(value):
#         return "не определена"

#     absolute = abs(
#         value
#     )

#     if absolute < 0.2:
#         return "очень слабая"

#     if absolute < 0.4:
#         return "слабая"

#     if absolute < 0.6:
#         return "умеренная"

#     if absolute < 0.8:
#         return "сильная"

#     return "очень сильная"


# def build_insights(
#     daily_df: pd.DataFrame,
#     aggregated_df: pd.DataFrame,
#     aggregation: str,
# ) -> list[str]:
#     """
#     Автоматические аналитические наблюдения.
#     """

#     if (
#         daily_df.empty
#         or aggregated_df.empty
#     ):
#         return [
#             "Недостаточно данных для анализа."
#         ]

#     insights = []

#     marketing_pearson = (
#         calculate_correlation(
#             aggregated_df[
#                 "marketing_costs"
#             ],
#             aggregated_df[
#                 "revenue"
#             ],
#             method="pearson",
#         )
#     )

#     marketing_spearman = (
#         calculate_correlation(
#             aggregated_df[
#                 "marketing_costs"
#             ],
#             aggregated_df[
#                 "revenue"
#             ],
#             method="spearman",
#         )
#     )

#     if pd.notna(
#         marketing_pearson
#     ):
#         direction = (
#             "положительная"
#             if marketing_pearson >= 0
#             else "отрицательная"
#         )

#         insights.append(
#             (
#                 f"Связь маркетинговых расходов "
#                 f"с выручкой — "
#                 f"{correlation_strength(marketing_pearson)} "
#                 f"{direction}: "
#                 f"Pearson r = "
#                 f"{marketing_pearson:.2f}."
#             )
#         )

#     if pd.notna(
#         marketing_spearman
#     ):
#         insights.append(
#             (
#                 "Ранговая корреляция Spearman "
#                 f"маркетинга и выручки составляет "
#                 f"{marketing_spearman:.2f}."
#             )
#         )

#     lag_df = (
#         calculate_lag_correlations(
#             aggregated_df
#         )
#     )

#     valid_lags = (
#         lag_df.dropna(
#             subset=[
#                 "pearson"
#             ]
#         )
#         if not lag_df.empty
#         else pd.DataFrame()
#     )

#     if not valid_lags.empty:
#         best_index = (
#             valid_lags[
#                 "pearson"
#             ]
#             .abs()
#             .idxmax()
#         )

#         best_row = (
#             valid_lags.loc[
#                 best_index
#             ]
#         )

#         lag = int(
#             best_row[
#                 "lag"
#             ]
#         )

#         corr = float(
#             best_row[
#                 "pearson"
#             ]
#         )

#         period_word = {
#             "day": "дн.",
#             "week": "нед.",
#             "month": "мес.",
#         }.get(
#             aggregation,
#             "период.",
#         )

#         insights.append(
#             (
#                 "Максимальная наблюдаемая связь "
#                 "маркетинга с последующей выручкой "
#                 f"достигается при лаге "
#                 f"{lag} {period_word}: "
#                 f"r = {corr:.2f}."
#             )
#         )

#     price_corr = (
#         calculate_correlation(
#             aggregated_df[
#                 "average_price"
#             ],
#             aggregated_df[
#                 "quantity"
#             ],
#         )
#     )

#     if pd.notna(
#         price_corr
#     ):
#         insights.append(
#             (
#                 "Связь средней цены реализации "
#                 "с количеством продаж составляет "
#                 f"r = {price_corr:.2f}. "
#                 "Это статистическая связь, "
#                 "а не доказательство причинности."
#             )
#         )

#     weekday_df = (
#         build_weekday_analysis(
#             daily_df
#         )
#     )

#     if not weekday_df.empty:
#         best = weekday_df.loc[
#             weekday_df[
#                 "average_revenue"
#             ].idxmax()
#         ]

#         worst = weekday_df.loc[
#             weekday_df[
#                 "average_revenue"
#             ].idxmin()
#         ]

#         insights.append(
#             (
#                 f"Наиболее сильный день недели — "
#                 f"{best['weekday']}: "
#                 f"{best['revenue_deviation_pct']:+.1f}% "
#                 "к среднему дневному уровню."
#             )
#         )

#         insights.append(
#             (
#                 f"Наиболее слабый день недели — "
#                 f"{worst['weekday']}: "
#                 f"{worst['revenue_deviation_pct']:+.1f}% "
#                 "к среднему дневному уровню."
#             )
#         )

#     month_df = (
#         build_month_analysis(
#             daily_df
#         )
#     )

#     if not month_df.empty:
#         best_month = month_df.loc[
#             month_df[
#                 "average_revenue"
#             ].idxmax()
#         ]

#         insights.append(
#             (
#                 f"Наиболее сильный календарный месяц "
#                 f"в выборке — "
#                 f"{best_month['month']}: "
#                 f"{best_month['revenue_deviation_pct']:+.1f}% "
#                 "к среднему дневному уровню."
#             )
#         )

#     anomalies = (
#         detect_anomalies(
#             aggregated_df
#         )
#     )

#     if not anomalies.empty:
#         insights.append(
#             (
#                 f"Обнаружено {len(anomalies)} "
#                 "аномальных периодов, "
#                 "где динамика маркетинга, "
#                 "выручки или цены расходится "
#                 "с ожидаемым поведением."
#             )
#         )

#     return insights




# gear/app/stats/calculations.py
from __future__ import annotations

import numpy as np
import pandas as pd

from .config import (
    MAX_LAG_PERIODS,
    ROLLING_WINDOWS,
)


WEEKDAY_NAMES = {
    0: "Понедельник",
    1: "Вторник",
    2: "Среда",
    3: "Четверг",
    4: "Пятница",
    5: "Суббота",
    6: "Воскресенье",
}


WEEKDAY_ORDER = [
    "Понедельник",
    "Вторник",
    "Среда",
    "Четверг",
    "Пятница",
    "Суббота",
    "Воскресенье",
]


MONTH_NAMES = {
    1: "Январь",
    2: "Февраль",
    3: "Март",
    4: "Апрель",
    5: "Май",
    6: "Июнь",
    7: "Июль",
    8: "Август",
    9: "Сентябрь",
    10: "Октябрь",
    11: "Ноябрь",
    12: "Декабрь",
}


MONTH_ORDER = [
    "Январь",
    "Февраль",
    "Март",
    "Апрель",
    "Май",
    "Июнь",
    "Июль",
    "Август",
    "Сентябрь",
    "Октябрь",
    "Ноябрь",
    "Декабрь",
]


def safe_divide(
    numerator,
    denominator,
):
    if denominator is None:
        return np.nan

    try:
        if pd.isna(denominator):
            return np.nan
    except TypeError:
        pass

    if denominator == 0:
        return np.nan

    return numerator / denominator


# def aggregate_data(
#     df: pd.DataFrame,
#     aggregation: str,
# ) -> pd.DataFrame:
#     """
#     Агрегация данных:

#     day   - день;
#     week  - неделя с понедельника;
#     month - календарный месяц.
#     """

#     if df.empty:
#         return pd.DataFrame()

#     work = df.copy()

#     work["date"] = pd.to_datetime(
#         work["date"],
#         errors="coerce",
#     )

#     work = work[
#         work["date"].notna()
#     ].copy()

#     if aggregation == "month":
#         work["period"] = (
#             work["date"]
#             .dt.to_period("M")
#             .dt.to_timestamp()
#         )

#     elif aggregation == "week":
#         work["period"] = (
#             work["date"]
#             - pd.to_timedelta(
#                 work["date"].dt.weekday,
#                 unit="D",
#             )
#         )

#     else:
#         work["period"] = (
#             work["date"]
#             .dt.normalize()
#         )

#     result = (
#         work.groupby(
#             "period",
#             as_index=False,
#         )
#         .agg(
#             revenue=(
#                 "revenue",
#                 "sum",
#             ),
#             marketing_costs=(
#                 "marketing_costs",
#                 "sum",
#             ),
#             quantity=(
#                 "quantity",
#                 "sum",
#             ),
#         )
#     )

#     result["average_price"] = (
#         result["revenue"]
#         / result["quantity"].replace(
#             0,
#             np.nan,
#         )
#     )

#     result["marketing_share"] = (
#         result["marketing_costs"]
#         / result["revenue"].replace(
#             0,
#             np.nan,
#         )
#         * 100
#     )

#     result["roas"] = (
#         result["revenue"]
#         / result[
#             "marketing_costs"
#         ].replace(
#             0,
#             np.nan,
#         )
#     )

#     return (
#         result.sort_values(
#             "period"
#         )
#         .reset_index(drop=True)
#     )

def aggregate_data(
    df: pd.DataFrame,
    aggregation: str,
) -> pd.DataFrame:
    """
    Агрегирует дневные показатели
    по дням, неделям или месяцам.

    ВАЖНО:
    средние цены НЕ суммируются.

    Сначала суммируются:
        выручка,
        количество,
        себестоимость и т.д.

    После этого средние показатели
    пересчитываются заново.
    """

    if df.empty:
        return pd.DataFrame()

    work = df.copy()

    work["date"] = pd.to_datetime(
        work["date"],
        errors="coerce",
    )

    work = work[
        work["date"].notna()
    ].copy()

    if aggregation == "month":
        work["period"] = (
            work["date"]
            .dt.to_period("M")
            .dt.to_timestamp()
        )

    elif aggregation == "week":
        work["period"] = (
            work["date"]
            - pd.to_timedelta(
                work["date"].dt.weekday,
                unit="D",
            )
        )

    else:
        work["period"] = (
            work["date"]
            .dt.normalize()
        )

    result = (
        work.groupby(
            "period",
            as_index=False,
        )
        .agg(
            quantity=(
                "quantity",
                "sum",
            ),

            revenue=(
                "revenue",
                "sum",
            ),

            retail_revenue=(
                "retail_revenue",
                "sum",
            ),

            cogs=(
                "cogs",
                "sum",
            ),

            cogs_man=(
                "cogs_man",
                "sum",
            ),

            net_comission=(
                "net_comission",
                "sum",
            ),

            wb_costs=(
                "wb_costs",
                "sum",
            ),

            marketing_costs=(
                "marketing_costs",
                "sum",
            ),

            logistics_costs=(
                "logistics_costs",
                "sum",
            ),

            storage_costs=(
                "storage_costs",
                "sum",
            ),

            acceptance_costs=(
                "acceptance_costs",
                "sum",
            ),

            penalties_costs=(
                "penalties_costs",
                "sum",
            ),
        )
    )

    # =========================================================
    # Аналитическое представление маркетинговых расходов
    #
    # marketing_costs сохраняет исходный экономический знак:
    #   расход  -> отрицательное значение;
    #   возврат -> положительное значение.
    #
    # marketing_spend используется только для аналитики:
    #   чистый расход  -> положительное значение;
    #   чистый возврат -> отрицательное значение.
    #
    # ВАЖНО: abs() не используем, чтобы не потерять смысл возвратов.
    # =========================================================

    result["marketing_spend"] = (
        -result["marketing_costs"]
    )

    # =========================================================
    # Средняя наша цена реализации БЕЗ НДС
    # =========================================================

    result["average_price"] = (
        result["revenue"]
        / result[
            "quantity"
        ].replace(
            0,
            np.nan,
        )
    )

    # =========================================================
    # Средняя цена реализации WB БЕЗ НДС
    # =========================================================

    result[
        "average_retail_price"
    ] = (
        result["retail_revenue"]
        / result[
            "quantity"
        ].replace(
            0,
            np.nan,
        )
    )

    # =========================================================
    # Средняя себестоимость
    # =========================================================

    result[
        "average_cogs"
    ] = (
        result["cogs"]
        / result[
            "quantity"
        ].replace(
            0,
            np.nan,
        )
    )

    result[
        "average_cogs_man"
    ] = (
        result["cogs_man"]
        / result[
            "quantity"
        ].replace(
            0,
            np.nan,
        )
    )

    # =========================================================
    # Доля маркетинга
    # =========================================================

    result[
        "marketing_share"
    ] = (
        result[
            "marketing_spend"
        ]
        / result[
            "revenue"
        ].replace(
            0,
            np.nan,
        )
        * 100
    )

    # =========================================================
    # ROAS
    # =========================================================

    result["roas"] = (
        result["revenue"]
        / result[
            "marketing_spend"
        ].replace(
            0,
            np.nan,
        )
    )

    # =========================================================
    # Валовая прибыль
    # =========================================================

    result[
        "gross_profit"
    ] = (
        result["revenue"]
        -
        result["cogs"]
    )

    result[
        "gross_profit_man"
    ] = (
        result["revenue"]
        -
        result["cogs_man"]
    )

    # =========================================================
    # Маржа после комиссии
    # =========================================================

    result["margin"] = (
        result["revenue"]
        -
        result["cogs"]
        +
        result["net_comission"]
    )

    result["margin_man"] = (
        result["revenue"]
        -
        result["cogs_man"]
        +
        result["net_comission"]
    )

    # =========================================================
    # Финансовый результат WB
    # =========================================================

    result["wb_result"] = (
        result["revenue"]
        -
        result["cogs_man"]
        +
        result["net_comission"]
        -
        result["wb_costs"]
    )

    # =========================================================
    # Маржинальность
    # =========================================================

    result[
        "margin_percent"
    ] = (
        result["margin"]
        / result[
            "revenue"
        ].replace(
            0,
            np.nan,
        )
        * 100
    )

    result[
        "margin_man_percent"
    ] = (
        result["margin_man"]
        / result[
            "revenue"
        ].replace(
            0,
            np.nan,
        )
        * 100
    )

    return (
        result.sort_values(
            "period"
        )
        .reset_index(
            drop=True
        )
    )

def calculate_correlation(
    x: pd.Series,
    y: pd.Series,
    method: str = "pearson",
) -> float:
    """
    Безопасный расчёт корреляции.
    """

    clean = pd.DataFrame(
        {
            "x": pd.to_numeric(
                x,
                errors="coerce",
            ),
            "y": pd.to_numeric(
                y,
                errors="coerce",
            ),
        }
    ).dropna()

    if len(clean) < 3:
        return np.nan

    if (
        clean["x"].nunique() <= 1
        or clean["y"].nunique() <= 1
    ):
        return np.nan

    return float(
        clean["x"].corr(
            clean["y"],
            method=method,
        )
    )


def calculate_lag_correlations(
    df: pd.DataFrame,
    max_lag: int = MAX_LAG_PERIODS,
) -> pd.DataFrame:
    """
    Проверяет связь:

    маркетинг периода T
    с выручкой периода T + lag.

    lag=0:
        маркетинг сейчас -> выручка сейчас

    lag=1:
        маркетинг сейчас -> выручка следующего периода
    """

    if df.empty:
        return pd.DataFrame()

    work = (
        df.copy()
        .sort_values("period")
        .reset_index(drop=True)
    )

    rows = []

    for lag in range(
        0,
        max_lag + 1,
    ):
        future_revenue = (
            work["revenue"]
            .shift(-lag)
        )

        pearson = (
            calculate_correlation(
                work[
                    "marketing_spend"
                ],
                future_revenue,
                method="pearson",
            )
        )

        spearman = (
            calculate_correlation(
                work[
                    "marketing_spend"
                ],
                future_revenue,
                method="spearman",
            )
        )

        rows.append(
            {
                "lag": lag,
                "pearson": pearson,
                "spearman": spearman,
                "r2": (
                    pearson ** 2
                    if pd.notna(
                        pearson
                    )
                    else np.nan
                ),
            }
        )

    return pd.DataFrame(
        rows
    )


def calculate_rolling_correlation(
    df: pd.DataFrame,
    aggregation: str,
) -> pd.DataFrame:
    """
    Скользящая корреляция
    маркетинг <-> выручка.
    """

    if df.empty:
        return pd.DataFrame()

    work = (
        df.copy()
        .sort_values("period")
        .reset_index(drop=True)
    )

    window = (
        ROLLING_WINDOWS.get(
            aggregation,
            8,
        )
    )

    min_periods = max(
        3,
        window // 2,
    )

    work[
        "rolling_correlation"
    ] = (
        work[
            "marketing_spend"
        ]
        .rolling(
            window=window,
            min_periods=min_periods,
        )
        .corr(
            work["revenue"]
        )
    )

    return work


def calculate_price_elasticity(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Proxy-оценка ценовой эластичности:

    % изменения количества
    ----------------------
    % изменения средней цены

    Это не причинная оценка,
    а аналитический индикатор.
    """

    if df.empty:
        return pd.DataFrame()

    work = (
        df.copy()
        .sort_values("period")
        .reset_index(drop=True)
    )

    work[
        "price_change_pct"
    ] = (
        work["average_price"]
        .pct_change(
            fill_method=None
        )
        * 100
    )

    work[
        "quantity_change_pct"
    ] = (
        work["quantity"]
        .pct_change(
            fill_method=None
        )
        * 100
    )

    work[
        "revenue_change_pct"
    ] = (
        work["revenue"]
        .pct_change(
            fill_method=None
        )
        * 100
    )

    work["elasticity"] = (
        work[
            "quantity_change_pct"
        ]
        / work[
            "price_change_pct"
        ].replace(
            0,
            np.nan,
        )
    )

    # Убираем технически бессмысленные
    # бесконечные значения.
    work = work.replace(
        [
            np.inf,
            -np.inf,
        ],
        np.nan,
    )

    return work


def build_weekday_analysis(
    daily_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Анализ сезонности по дням недели.
    """

    if daily_df.empty:
        return pd.DataFrame()

    work = daily_df.copy()

    # Для аналитики переводим signed-маркетинг
    # в направление чистого расхода.
    work["marketing_spend"] = (
        -pd.to_numeric(
            work["marketing_costs"],
            errors="coerce",
        )
    )

    work["date"] = pd.to_datetime(
        work["date"],
        errors="coerce",
    )

    work = work[
        work["date"].notna()
    ].copy()

    work["weekday_number"] = (
        work["date"].dt.weekday
    )

    result = (
        work.groupby(
            "weekday_number",
            as_index=False,
        )
        .agg(
            average_revenue=(
                "revenue",
                "mean",
            ),
            median_revenue=(
                "revenue",
                "median",
            ),
            average_marketing=(
                "marketing_spend",
                "mean",
            ),
            average_quantity=(
                "quantity",
                "mean",
            ),
            days_count=(
                "date",
                "count",
            ),
        )
    )

    result["weekday"] = (
        result[
            "weekday_number"
        ].map(
            WEEKDAY_NAMES
        )
    )

    overall_average = (
        work["revenue"].mean()
    )

    if overall_average:
        result[
            "revenue_deviation_pct"
        ] = (
            (
                result[
                    "average_revenue"
                ]
                / overall_average
            )
            - 1
        ) * 100
    else:
        result[
            "revenue_deviation_pct"
        ] = np.nan

    result["roas"] = (
        result[
            "average_revenue"
        ]
        / result[
            "average_marketing"
        ].replace(
            0,
            np.nan,
        )
    )

    return result


def build_month_analysis(
    daily_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Средняя статистика календарных месяцев.

    То есть все январские дни
    сравниваются со всеми февральскими и т.д.
    """

    if daily_df.empty:
        return pd.DataFrame()

    work = daily_df.copy()

    # Для аналитики переводим signed-маркетинг
    # в направление чистого расхода.
    work["marketing_spend"] = (
        -pd.to_numeric(
            work["marketing_costs"],
            errors="coerce",
        )
    )

    work["date"] = pd.to_datetime(
        work["date"],
        errors="coerce",
    )

    work = work[
        work["date"].notna()
    ].copy()

    work["month_number"] = (
        work["date"].dt.month
    )

    result = (
        work.groupby(
            "month_number",
            as_index=False,
        )
        .agg(
            average_revenue=(
                "revenue",
                "mean",
            ),
            median_revenue=(
                "revenue",
                "median",
            ),
            average_marketing=(
                "marketing_spend",
                "mean",
            ),
            average_quantity=(
                "quantity",
                "mean",
            ),
            days_count=(
                "date",
                "count",
            ),
        )
    )

    result["month"] = (
        result[
            "month_number"
        ].map(
            MONTH_NAMES
        )
    )

    overall_average = (
        work["revenue"].mean()
    )

    if overall_average:
        result[
            "revenue_deviation_pct"
        ] = (
            (
                result[
                    "average_revenue"
                ]
                / overall_average
            )
            - 1
        ) * 100
    else:
        result[
            "revenue_deviation_pct"
        ] = np.nan

    result["roas"] = (
        result[
            "average_revenue"
        ]
        / result[
            "average_marketing"
        ].replace(
            0,
            np.nan,
        )
    )

    return result


def calculate_correlation_matrix(
    df: pd.DataFrame,
    method: str = "pearson",
) -> pd.DataFrame:
    """
    Корреляционная матрица
    числовых факторов.

    other_wb_costs:
    все расходы WB за исключением маркетинга.
    """

    if df.empty:
        return pd.DataFrame()

    work = df.copy()

    # ================================================================
    # Все остальные расходы WB без маркетинга
    # ================================================================

    if (
        "wb_costs" in work.columns
        and "marketing_spend" in work.columns
    ):
        work["other_wb_costs"] = (
            pd.to_numeric(
                work["wb_costs"],
                errors="coerce",
            ).fillna(0)
            -
            pd.to_numeric(
                work["marketing_spend"],
                errors="coerce",
            ).fillna(0)
        )

    # ================================================================
    # Показатели корреляционной матрицы
    # ================================================================

    columns = [
        "revenue",
        "quantity",
        "average_price",
        "average_retail_price",
        "marketing_spend",
        "other_wb_costs",
        "net_comission",
        "cogs_man",
        "margin_man",
        "wb_result",
        "roas",
    ]

    available_columns = [
        column
        for column in columns
        if column in work.columns
    ]

    if len(available_columns) < 2:
        return pd.DataFrame()

    return (
        work[
            available_columns
        ]
        .corr(
            method=method
        )
    )
    
    

def detect_anomalies(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Находит интересные периоды:

    1. маркетинг вырос >20%,
       выручка упала;

    2. маркетинг вырос >30%,
       выручка изменилась менее чем на 5%;

    3. цена выросла >10%,
       количество упало >15%;

    4. выручка выросла >20%
       без существенного роста маркетинга.
    """

    if df.empty:
        return pd.DataFrame()

    work = (
        df.copy()
        .sort_values("period")
        .reset_index(drop=True)
    )

    work[
        "marketing_change_pct"
    ] = (
        work[
            "marketing_spend"
        ]
        .pct_change(
            fill_method=None
        )
        * 100
    )

    work[
        "revenue_change_pct"
    ] = (
        work["revenue"]
        .pct_change(
            fill_method=None
        )
        * 100
    )

    work[
        "price_change_pct"
    ] = (
        work["average_price"]
        .pct_change(
            fill_method=None
        )
        * 100
    )

    work[
        "quantity_change_pct"
    ] = (
        work["quantity"]
        .pct_change(
            fill_method=None
        )
        * 100
    )

    work["anomaly_type"] = None

    condition_1 = (
        (
            work[
                "marketing_change_pct"
            ] > 20
        )
        &
        (
            work[
                "revenue_change_pct"
            ] < 0
        )
    )

    condition_2 = (
        (
            work[
                "marketing_change_pct"
            ] > 30
        )
        &
        (
            work[
                "revenue_change_pct"
            ].abs() < 5
        )
    )

    condition_3 = (
        (
            work[
                "price_change_pct"
            ] > 10
        )
        &
        (
            work[
                "quantity_change_pct"
            ] < -15
        )
    )

    condition_4 = (
        (
            work[
                "revenue_change_pct"
            ] > 20
        )
        &
        (
            work[
                "marketing_change_pct"
            ].fillna(0) < 5
        )
    )

    work.loc[
        condition_1,
        "anomaly_type",
    ] = (
        "Маркетинг вырос, "
        "выручка снизилась"
    )

    work.loc[
        condition_2,
        "anomaly_type",
    ] = (
        "Маркетинг вырос, "
        "выручка почти не изменилась"
    )

    work.loc[
        condition_3,
        "anomaly_type",
    ] = (
        "Цена выросла, "
        "количество снизилось"
    )

    work.loc[
        condition_4,
        "anomaly_type",
    ] = (
        "Выручка выросла "
        "без роста маркетинга"
    )

    return (
        work[
            work[
                "anomaly_type"
            ].notna()
        ]
        .reset_index(drop=True)
    )


def calculate_kpis(
    daily_df: pd.DataFrame,
    aggregated_df: pd.DataFrame,
) -> dict:
    """
    Основные KPI приложения.
    """

    if daily_df.empty:
        return {}

    revenue = float(
        daily_df[
            "revenue"
        ].sum()
    )

    # Исходный signed-показатель сохраняем отдельно.
    # Расход отрицательный, возврат положительный.
    marketing_signed = float(
        daily_df[
            "marketing_costs"
        ].sum()
    )

    # Для KPI отображаем направление чистого расхода.
    # Расход становится положительным, чистый возврат — отрицательным.
    marketing = (
        -marketing_signed
    )

    marketing_share = (
        safe_divide(
            marketing,
            revenue,
        )
    )

    if pd.notna(
        marketing_share
    ):
        marketing_share *= 100

    roas = safe_divide(
        revenue,
        marketing,
    )

    marketing_corr = (
        calculate_correlation(
            aggregated_df[
                "marketing_spend"
            ],
            aggregated_df[
                "revenue"
            ],
            method="pearson",
        )
    )

    price_corr = (
        calculate_correlation(
            aggregated_df[
                "average_price"
            ],
            aggregated_df[
                "quantity"
            ],
            method="pearson",
        )
    )

    lag_df = (
        calculate_lag_correlations(
            aggregated_df
        )
    )

    best_lag = None
    best_lag_corr = None

    if not lag_df.empty:
        valid_lags = (
            lag_df.dropna(
                subset=[
                    "pearson"
                ]
            )
            .copy()
        )

        if not valid_lags.empty:
            best_index = (
                valid_lags[
                    "pearson"
                ]
                .abs()
                .idxmax()
            )

            best_row = (
                valid_lags.loc[
                    best_index
                ]
            )

            best_lag = int(
                best_row[
                    "lag"
                ]
            )

            best_lag_corr = float(
                best_row[
                    "pearson"
                ]
            )

    weekday_df = (
        build_weekday_analysis(
            daily_df
        )
    )

    best_weekday = None

    if not weekday_df.empty:
        best_index = (
            weekday_df[
                "average_revenue"
            ].idxmax()
        )

        best_weekday = (
            weekday_df.loc[
                best_index,
                "weekday",
            ]
        )

    return {
        "revenue": revenue,
        "marketing": marketing,
        "marketing_share": (
            marketing_share
        ),
        "roas": roas,
        "marketing_corr": (
            marketing_corr
        ),
        "price_corr": (
            price_corr
        ),
        "best_lag": (
            best_lag
        ),
        "best_lag_corr": (
            best_lag_corr
        ),
        "best_weekday": (
            best_weekday
        ),
    }


def correlation_strength(
    value: float | None,
) -> str:
    if value is None:
        return "не определена"

    if pd.isna(value):
        return "не определена"

    absolute = abs(
        value
    )

    if absolute < 0.2:
        return "очень слабая"

    if absolute < 0.4:
        return "слабая"

    if absolute < 0.6:
        return "умеренная"

    if absolute < 0.8:
        return "сильная"

    return "очень сильная"


def build_insights(
    daily_df: pd.DataFrame,
    aggregated_df: pd.DataFrame,
    aggregation: str,
) -> list[str]:
    """
    Автоматические аналитические наблюдения.
    """

    if (
        daily_df.empty
        or aggregated_df.empty
    ):
        return [
            "Недостаточно данных для анализа."
        ]

    insights = []

    marketing_pearson = (
        calculate_correlation(
            aggregated_df[
                "marketing_spend"
            ],
            aggregated_df[
                "revenue"
            ],
            method="pearson",
        )
    )

    marketing_spearman = (
        calculate_correlation(
            aggregated_df[
                "marketing_spend"
            ],
            aggregated_df[
                "revenue"
            ],
            method="spearman",
        )
    )

    if pd.notna(
        marketing_pearson
    ):
        direction = (
            "положительная"
            if marketing_pearson >= 0
            else "отрицательная"
        )

        insights.append(
            (
                f"Связь маркетинговых расходов "
                f"с выручкой — "
                f"{correlation_strength(marketing_pearson)} "
                f"{direction}: "
                f"Pearson r = "
                f"{marketing_pearson:.2f}."
            )
        )

    if pd.notna(
        marketing_spearman
    ):
        insights.append(
            (
                "Ранговая корреляция Spearman "
                f"маркетинга и выручки составляет "
                f"{marketing_spearman:.2f}."
            )
        )

    lag_df = (
        calculate_lag_correlations(
            aggregated_df
        )
    )

    valid_lags = (
        lag_df.dropna(
            subset=[
                "pearson"
            ]
        )
        if not lag_df.empty
        else pd.DataFrame()
    )

    if not valid_lags.empty:
        best_index = (
            valid_lags[
                "pearson"
            ]
            .abs()
            .idxmax()
        )

        best_row = (
            valid_lags.loc[
                best_index
            ]
        )

        lag = int(
            best_row[
                "lag"
            ]
        )

        corr = float(
            best_row[
                "pearson"
            ]
        )

        period_word = {
            "day": "дн.",
            "week": "нед.",
            "month": "мес.",
        }.get(
            aggregation,
            "период.",
        )

        insights.append(
            (
                "Максимальная наблюдаемая связь "
                "маркетинга с последующей выручкой "
                f"достигается при лаге "
                f"{lag} {period_word}: "
                f"r = {corr:.2f}."
            )
        )

    price_corr = (
        calculate_correlation(
            aggregated_df[
                "average_price"
            ],
            aggregated_df[
                "quantity"
            ],
        )
    )

    if pd.notna(
        price_corr
    ):
        insights.append(
            (
                "Связь средней цены реализации "
                "с количеством продаж составляет "
                f"r = {price_corr:.2f}. "
                "Это статистическая связь, "
                "а не доказательство причинности."
            )
        )

    weekday_df = (
        build_weekday_analysis(
            daily_df
        )
    )

    if not weekday_df.empty:
        best = weekday_df.loc[
            weekday_df[
                "average_revenue"
            ].idxmax()
        ]

        worst = weekday_df.loc[
            weekday_df[
                "average_revenue"
            ].idxmin()
        ]

        insights.append(
            (
                f"Наиболее сильный день недели — "
                f"{best['weekday']}: "
                f"{best['revenue_deviation_pct']:+.1f}% "
                "к среднему дневному уровню."
            )
        )

        insights.append(
            (
                f"Наиболее слабый день недели — "
                f"{worst['weekday']}: "
                f"{worst['revenue_deviation_pct']:+.1f}% "
                "к среднему дневному уровню."
            )
        )

    month_df = (
        build_month_analysis(
            daily_df
        )
    )

    if not month_df.empty:
        best_month = month_df.loc[
            month_df[
                "average_revenue"
            ].idxmax()
        ]

        insights.append(
            (
                f"Наиболее сильный календарный месяц "
                f"в выборке — "
                f"{best_month['month']}: "
                f"{best_month['revenue_deviation_pct']:+.1f}% "
                "к среднему дневному уровню."
            )
        )

    anomalies = (
        detect_anomalies(
            aggregated_df
        )
    )

    if not anomalies.empty:
        insights.append(
            (
                f"Обнаружено {len(anomalies)} "
                "аномальных периодов, "
                "где динамика маркетинга, "
                "выручки или цены расходится "
                "с ожидаемым поведением."
            )
        )

    return insights