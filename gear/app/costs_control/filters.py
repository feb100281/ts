# # gear/app/costs_control/filters.py
# from __future__ import annotations

# from datetime import datetime
# from typing import Any

# import dash_mantine_components as dmc
# import pandas as pd
# from dash import (
#     Input,
#     Output,
#     State,
#     html,
#     no_update,
# )
# from dash_iconify import DashIconify

# from .calculations import (
#     apply_filters,
#     build_filter_options,
# )
# from .components import (
#     action_button,
#     section_header,
# )
# from .config import (
#     COLORS,
#     COST_TYPES,
#     CV_RANK_OPTIONS,
#     DEFAULT_COST_TYPE,
#     DEFAULT_MEDIAN_DEVIATION_LIMIT,
# )
# from .data import (
#     clear_price_analysis_cache,
#     get_price_analysis_data,
#     get_price_history_data,
# )
# from .ids import (
#     BRAND_FILTER_ID,
#     CATEGORY_FILTER_ID,
#     COST_TYPE_FILTER_ID,
#     CV_RANK_FILTER_ID,
#     DATA_STORE_ID,
#     DATE_FILTER_ID,
#     LAST_UPDATE_ID,
#     MEDIAN_DEVIATION_FILTER_ID,
#     REFRESH_DATA_BTN_ID,
#     RESET_FILTERS_BTN_ID,
#     SUPPLIER_FILTER_ID,
# )
# from .styles import (
#     FILTER_GRID_STYLE,
#     PANEL_STYLE,
# )


# # ---------------------------------------------------------------------
# # Нормализация
# # ---------------------------------------------------------------------


# def normalise_nm_id(
#     value: Any,
# ) -> str:
#     """
#     Приводит NM ID к строке без окончания .0.
#     """

#     if value is None:
#         return ""

#     text = str(value).strip()

#     if text.endswith(".0"):
#         text = text[:-2]

#     return text


# def normalise_list(
#     value,
# ) -> list:
#     """
#     Приводит значение MultiSelect к обычному списку.
#     """

#     if value is None:
#         return []

#     if isinstance(
#         value,
#         (str, int, float),
#     ):
#         return [value]

#     return list(value)


# def _clean_values(
#     values,
# ) -> list[str]:
#     """
#     Очищает список выбранных значений.
#     """

#     return [
#         str(value).strip()
#         for value in normalise_list(values)
#         if (
#             value is not None
#             and str(value).strip()
#         )
#     ]


# # ---------------------------------------------------------------------
# # Элемент одного фильтра
# # ---------------------------------------------------------------------


# def _filter_field(
#     *,
#     icon: str,
#     title: str,
#     subtitle: str,
#     component,
# ):
#     """
#     Единый визуальный контейнер фильтра.
#     """

#     return html.Div(
#         style={
#             "minWidth": 0,
#             "padding": "11px 12px 12px",
#             "backgroundColor": "#FFFFFF",
#             "border": (
#                 "1px solid "
#                 + COLORS.get(
#                     "border",
#                     "#D9DEE2",
#                 )
#             ),
#         },
#         children=[
#             html.Div(
#                 style={
#                     "display": "flex",
#                     "alignItems": "flex-start",
#                     "gap": "8px",
#                     "marginBottom": "9px",
#                 },
#                 children=[
#                     DashIconify(
#                         icon=icon,
#                         width=16,
#                         height=16,
#                         color=COLORS.get(
#                             "green",
#                             "#2F6656",
#                         ),
#                         style={
#                             "marginTop": "1px",
#                             "flex": "0 0 auto",
#                         },
#                     ),

#                     html.Div(
#                         style={
#                             "minWidth": 0,
#                         },
#                         children=[
#                             html.Div(
#                                 title,
#                                 style={
#                                     "fontSize": "12px",
#                                     "fontWeight": 700,
#                                     "lineHeight": "16px",
#                                     "color": COLORS.get(
#                                         "text",
#                                         "#111827",
#                                     ),
#                                 },
#                             ),

#                             html.Div(
#                                 subtitle,
#                                 style={
#                                     "marginTop": "1px",
#                                     "fontSize": "10px",
#                                     "lineHeight": "14px",
#                                     "color": COLORS.get(
#                                         "muted",
#                                         "#6B7280",
#                                     ),
#                                 },
#                             ),
#                         ],
#                     ),
#                 ],
#             ),

#             component,
#         ],
#     )


# # ---------------------------------------------------------------------
# # Layout панели фильтров
# # ---------------------------------------------------------------------


# def build_filter_panel():
#     """
#     Панель фильтров анализа.

#     Здесь намеренно отсутствуют:
#     - минимальный CV;
#     - поиск по NM ID или наименованию;
#     - переключатель изменения цены;
#     - переключатель отклонений.

#     Категории зависят от выбранного бренда.
#     Поставщики зависят от бренда и категории.
#     """

#     return html.Div(
#         style=PANEL_STYLE,
#         children=[
#             dmc.Group(
#                 justify="space-between",
#                 align="center",
#                 mb=14,
#                 children=[
#                     section_header(
#                         "Фильтры анализа",
#                         (
#                             "Категории и поставщики "
#                             "автоматически подстраиваются "
#                             "под выбранные значения"
#                         ),
#                     ),

#                     action_button(
#                         component_id=(
#                             RESET_FILTERS_BTN_ID
#                         ),
#                         label="Сбросить",
#                         icon="solar:restart-linear",
#                         color="gray",
#                     ),
#                 ],
#             ),

#             html.Div(
#                 style={
#                     **FILTER_GRID_STYLE,
#                     "gridTemplateColumns": (
#                         "repeat(auto-fit, "
#                         "minmax(235px, 1fr))"
#                     ),
#                     "gap": "10px",
#                 },
#                 children=[
#                     # -------------------------------------------------
#                     # Тип себестоимости
#                     # -------------------------------------------------

#                     _filter_field(
#                         icon=(
#                             "solar:"
#                             "calculator-minimalistic-linear"
#                         ),
#                         title="Тип себестоимости",
#                         subtitle=(
#                             "Показатели и графики "
#                             "будут пересчитаны"
#                         ),
#                         component=(
#                             dmc.SegmentedControl(
#                                 id=COST_TYPE_FILTER_ID,
#                                 value=DEFAULT_COST_TYPE,
#                                 data=COST_TYPES,
#                                 radius=0,
#                                 size="xs",
#                                 fullWidth=True,
#                             )
#                         ),
#                     ),

#                     # -------------------------------------------------
#                     # Бренд
#                     # -------------------------------------------------

#                     _filter_field(
#                         icon="solar:tag-linear",
#                         title="Бренд",
#                         subtitle=(
#                             "Можно выбрать "
#                             "несколько брендов"
#                         ),
#                         component=dmc.MultiSelect(
#                             id=BRAND_FILTER_ID,
#                             placeholder="Все бренды",
#                             data=[],
#                             value=[],
#                             searchable=True,
#                             clearable=True,
#                             nothingFoundMessage=(
#                                 "Бренды не найдены"
#                             ),
#                             radius=0,
#                             size="xs",
#                             maxDropdownHeight=300,
#                         ),
#                     ),

#                     # -------------------------------------------------
#                     # Категория
#                     # -------------------------------------------------

#                     _filter_field(
#                         icon=(
#                             "solar:"
#                             "folder-with-files-linear"
#                         ),
#                         title="Категория",
#                         subtitle=(
#                             "Список зависит "
#                             "от выбранного бренда"
#                         ),
#                         component=dmc.MultiSelect(
#                             id=CATEGORY_FILTER_ID,
#                             placeholder="Все категории",
#                             data=[],
#                             value=[],
#                             searchable=True,
#                             clearable=True,
#                             nothingFoundMessage=(
#                                 "Категории не найдены"
#                             ),
#                             radius=0,
#                             size="xs",
#                             maxDropdownHeight=300,
#                         ),
#                     ),

#                     # -------------------------------------------------
#                     # Поставщик
#                     # -------------------------------------------------

#                     _filter_field(
#                         icon=(
#                             "solar:buildings-2-linear"
#                         ),
#                         title="Поставщик",
#                         subtitle=(
#                             "Список зависит от "
#                             "бренда и категории"
#                         ),
#                         component=dmc.MultiSelect(
#                             id=SUPPLIER_FILTER_ID,
#                             placeholder="Все поставщики",
#                             data=[],
#                             value=[],
#                             searchable=True,
#                             clearable=True,
#                             nothingFoundMessage=(
#                                 "Поставщики не найдены"
#                             ),
#                             radius=0,
#                             size="xs",
#                             maxDropdownHeight=300,
#                         ),
#                     ),

#                     # -------------------------------------------------
#                     # Ранг CV
#                     # -------------------------------------------------

#                     _filter_field(
#                         icon=(
#                             "solar:chart-square-linear"
#                         ),
#                         title=(
#                             "Ранг коэффициента вариации"
#                         ),
#                         subtitle=(
#                             "Уровень стабильности "
#                             "закупочной цены"
#                         ),
#                         component=dmc.MultiSelect(
#                             id=CV_RANK_FILTER_ID,
#                             placeholder="Все ранги",
#                             data=CV_RANK_OPTIONS,
#                             value=[],
#                             searchable=False,
#                             clearable=True,
#                             radius=0,
#                             size="xs",
#                             maxDropdownHeight=260,
#                         ),
#                     ),

#                     # -------------------------------------------------
#                     # Отклонение от медианы
#                     # -------------------------------------------------

#                     _filter_field(
#                         icon=(
#                             "solar:sort-by-time-linear"
#                         ),
#                         title=(
#                             "Порог отклонения от медианы"
#                         ),
#                         subtitle=(
#                             "Используется для поиска "
#                             "ценовых выбросов"
#                         ),
#                         component=dmc.NumberInput(
#                             id=(
#                                 MEDIAN_DEVIATION_FILTER_ID
#                             ),
#                             value=(
#                                 DEFAULT_MEDIAN_DEVIATION_LIMIT
#                             ),
#                             placeholder="Например, 10",
#                             min=0,
#                             decimalScale=2,
#                             allowNegative=False,
#                             hideControls=True,
#                             suffix=" %",
#                             radius=0,
#                             size="xs",
#                         ),
#                     ),

#                     # -------------------------------------------------
#                     # Период
#                     # -------------------------------------------------

#                     _filter_field(
#                         icon="solar:calendar-linear",
#                         title="Период документов УПД",
#                         subtitle=(
#                             "Ограничение по дате "
#                             "поступления товара"
#                         ),
#                         component=dmc.DatePickerInput(
#                             id=DATE_FILTER_ID,
#                             type="range",
#                             placeholder="Весь период",
#                             value=None,
#                             valueFormat="DD.MM.YYYY",
#                             clearable=True,
#                             radius=0,
#                             size="xs",
#                             leftSection=DashIconify(
#                                 icon=(
#                                     "solar:calendar-linear"
#                                 ),
#                                 width=15,
#                             ),
#                         ),
#                     ),
#                 ],
#             ),

#             # ---------------------------------------------------------
#             # Подсказка
#             # ---------------------------------------------------------

#             html.Div(
#                 style={
#                     "display": "flex",
#                     "alignItems": "center",
#                     "gap": "7px",
#                     "marginTop": "10px",
#                     "padding": "8px 10px",
#                     "backgroundColor": COLORS.get(
#                         "very_light_green",
#                         "#F3F8F6",
#                     ),
#                     "border": (
#                         "1px solid "
#                         + COLORS.get(
#                             "border",
#                             "#D9DEE2",
#                         )
#                     ),
#                     "fontSize": "10px",
#                     "lineHeight": "14px",
#                     "color": COLORS.get(
#                         "muted",
#                         "#6B7280",
#                     ),
#                 },
#                 children=[
#                     DashIconify(
#                         icon=(
#                             "solar:info-circle-linear"
#                         ),
#                         width=14,
#                         height=14,
#                         color=COLORS.get(
#                             "green",
#                             "#2F6656",
#                         ),
#                     ),

#                     html.Span(
#                         (
#                             "Для поиска конкретного товара "
#                             "используйте встроенные фильтры "
#                             "таблицы на вкладке «Товары»."
#                         )
#                     ),
#                 ],
#             ),
#         ],
#     )


# # ---------------------------------------------------------------------
# # Вспомогательная фильтрация зависимых списков
# # ---------------------------------------------------------------------


# def _filter_analysis_for_options(
#     analysis_df: pd.DataFrame,
#     *,
#     brands=None,
#     categories=None,
# ) -> pd.DataFrame:
#     """
#     Фильтрует агрегированный анализ только
#     для построения зависимых справочников.
#     """

#     if analysis_df.empty:
#         return analysis_df.copy()

#     result = analysis_df.copy()

#     selected_brands = _clean_values(
#         brands
#     )

#     selected_categories = _clean_values(
#         categories
#     )

#     if (
#         selected_brands
#         and "Бренд" in result.columns
#     ):
#         result = result.loc[
#             result["Бренд"]
#             .fillna("")
#             .astype(str)
#             .isin(selected_brands)
#         ].copy()

#     if (
#         selected_categories
#         and "Категория" in result.columns
#     ):
#         result = result.loc[
#             result["Категория"]
#             .fillna("")
#             .astype(str)
#             .isin(selected_categories)
#         ].copy()

#     return result.reset_index(
#         drop=True
#     )


# def _find_nm_id_column(
#     df: pd.DataFrame,
# ) -> str | None:
#     """
#     Находит колонку NM ID.
#     """

#     for column in (
#         "nm_id",
#         "NM ID",
#         "nmId",
#     ):
#         if column in df.columns:
#             return column

#     return None


# def _build_smart_supplier_options(
#     analysis_df: pd.DataFrame,
#     history_df: pd.DataFrame,
# ) -> list:
#     """
#     Возвращает поставщиков только по NM ID,
#     которые остались после фильтра бренда
#     и категории.
#     """

#     if (
#         analysis_df.empty
#         or history_df.empty
#     ):
#         return []

#     analysis_nm_column = (
#         _find_nm_id_column(
#             analysis_df
#         )
#     )

#     history_nm_column = (
#         _find_nm_id_column(
#             history_df
#         )
#     )

#     if (
#         not analysis_nm_column
#         or not history_nm_column
#     ):
#         return build_filter_options(
#             history_df,
#             "Поставщик",
#         )

#     allowed_ids = {
#         normalise_nm_id(value)
#         for value in (
#             analysis_df[
#                 analysis_nm_column
#             ]
#             .dropna()
#             .tolist()
#         )
#         if normalise_nm_id(value)
#     }

#     if not allowed_ids:
#         return []

#     history_ids = (
#         history_df[history_nm_column]
#         .astype(str)
#         .map(normalise_nm_id)
#     )

#     filtered_history = (
#         history_df.loc[
#             history_ids.isin(
#                 allowed_ids
#             )
#         ]
#         .copy()
#         .reset_index(drop=True)
#     )

#     return build_filter_options(
#         filtered_history,
#         "Поставщик",
#     )


# def _option_values(
#     options: list,
# ) -> set[str]:
#     """
#     Получает множество value
#     из options компонента Mantine.
#     """

#     values: set[str] = set()

#     for option in options or []:
#         if isinstance(
#             option,
#             dict,
#         ):
#             value = option.get(
#                 "value"
#             )
#         else:
#             value = option

#         if value is not None:
#             values.add(
#                 str(value)
#             )

#     return values


# def _keep_available_values(
#     selected_values,
#     options: list,
# ) -> list[str]:
#     """
#     Оставляет только выбранные значения,
#     которые присутствуют в новых options.
#     """

#     available_values = (
#         _option_values(options)
#     )

#     return [
#         value
#         for value in _clean_values(
#             selected_values
#         )
#         if value in available_values
#     ]


# # ---------------------------------------------------------------------
# # Фильтр по поставщикам
# # ---------------------------------------------------------------------


# def filter_analysis_by_suppliers(
#     df: pd.DataFrame,
#     suppliers,
# ) -> pd.DataFrame:
#     """
#     Фильтрует агрегированную таблицу
#     по выбранным поставщикам.

#     В агрегированном анализе колонка
#     «Поставщики» может содержать список
#     поставщиков в одной строке.
#     """

#     selected_suppliers = (
#         _clean_values(
#             suppliers
#         )
#     )

#     if (
#         df.empty
#         or not selected_suppliers
#         or "Поставщики" not in df.columns
#     ):
#         return df.copy()

#     supplier_text = (
#         df["Поставщики"]
#         .fillna("")
#         .astype(str)
#     )

#     mask = pd.Series(
#         False,
#         index=df.index,
#     )

#     for supplier in selected_suppliers:
#         mask |= supplier_text.str.contains(
#             supplier,
#             case=False,
#             regex=False,
#             na=False,
#         )

#     return (
#         df.loc[mask]
#         .copy()
#         .reset_index(drop=True)
#     )


# # ---------------------------------------------------------------------
# # Общая фильтрация агрегированного анализа
# # ---------------------------------------------------------------------


# def apply_all_analysis_filters(
#     analysis_df: pd.DataFrame,
#     *,
#     cost_type,
#     brands,
#     categories,
#     suppliers,
#     cv_ranks,
#     median_deviation_limit,
#     date_range,
# ) -> pd.DataFrame:
#     """
#     Применяет все активные фильтры.

#     Используется:
#     - dashboard;
#     - основной таблицей;
#     - Excel;
#     - CSV.
#     """

#     if analysis_df.empty:
#         return analysis_df.copy()

#     filtered = apply_filters(
#         analysis_df,
#         cost_type=(
#             cost_type
#             or DEFAULT_COST_TYPE
#         ),
#         brands=normalise_list(
#             brands
#         ),
#         categories=normalise_list(
#             categories
#         ),

#         # Поставщики обрабатываются отдельно,
#         # потому что колонка может содержать
#         # несколько поставщиков в одной строке.
#         suppliers=None,

#         # Удалённые фильтры.
#         nm_ids=None,
#         cv_min=None,
#         only_changed=False,
#         only_anomalies=False,

#         cv_ranks=normalise_list(
#             cv_ranks
#         ),
#         date_range=date_range,
#         median_deviation_limit=(
#             median_deviation_limit
#         ),
#     )

#     return filter_analysis_by_suppliers(
#         filtered,
#         suppliers,
#     )


# # ---------------------------------------------------------------------
# # Фильтрация истории УПД
# # ---------------------------------------------------------------------


# def filter_history_data(
#     history_df: pd.DataFrame,
#     *,
#     nm_ids=None,
#     suppliers=None,
#     date_range=None,
# ) -> pd.DataFrame:
#     """
#     Фильтрует историю УПД на сервере.
#     """

#     if history_df.empty:
#         return history_df.copy()

#     result = history_df.copy()

#     # -------------------------------------------------------------
#     # NM ID
#     # -------------------------------------------------------------

#     if nm_ids is not None:
#         allowed_ids = {
#             normalise_nm_id(value)
#             for value in normalise_list(
#                 nm_ids
#             )
#             if normalise_nm_id(value)
#         }

#         nm_id_column = (
#             _find_nm_id_column(
#                 result
#             )
#         )

#         if (
#             not allowed_ids
#             or not nm_id_column
#         ):
#             return result.iloc[
#                 0:0
#             ].copy()

#         history_ids = (
#             result[nm_id_column]
#             .astype(str)
#             .map(normalise_nm_id)
#         )

#         result = result.loc[
#             history_ids.isin(
#                 allowed_ids
#             )
#         ].copy()

#     # -------------------------------------------------------------
#     # Поставщики
#     # -------------------------------------------------------------

#     selected_suppliers = (
#         _clean_values(
#             suppliers
#         )
#     )

#     if (
#         selected_suppliers
#         and "Поставщик" in result.columns
#     ):
#         result = result.loc[
#             result["Поставщик"]
#             .fillna("")
#             .astype(str)
#             .isin(selected_suppliers)
#         ].copy()

#     # -------------------------------------------------------------
#     # Период
#     # -------------------------------------------------------------

#     if (
#         date_range
#         and isinstance(
#             date_range,
#             (list, tuple),
#         )
#         and len(date_range) == 2
#         and "Дата УПД" in result.columns
#     ):
#         start_date = pd.to_datetime(
#             date_range[0],
#             errors="coerce",
#         )

#         end_date = pd.to_datetime(
#             date_range[1],
#             errors="coerce",
#         )

#         history_dates = pd.to_datetime(
#             result["Дата УПД"],
#             errors="coerce",
#         )

#         date_mask = pd.Series(
#             True,
#             index=result.index,
#         )

#         if pd.notna(start_date):
#             date_mask &= (
#                 history_dates
#                 >= start_date
#             )

#         if pd.notna(end_date):
#             date_mask &= (
#                 history_dates
#                 < end_date
#                 + pd.Timedelta(days=1)
#             )

#         result = result.loc[
#             date_mask
#         ].copy()

#     return result.reset_index(
#         drop=True
#     )


# # ---------------------------------------------------------------------
# # Store параметров фильтров
# # ---------------------------------------------------------------------


# def build_filter_store(
#     *,
#     cost_type,
#     brands,
#     categories,
#     suppliers,
#     cv_ranks,
#     median_deviation_limit,
#     date_range,
# ) -> dict:
#     """
#     Создаёт небольшой Store
#     только с параметрами фильтров.
#     """

#     return {
#         "cost_type": (
#             cost_type
#             or DEFAULT_COST_TYPE
#         ),

#         "brands": normalise_list(
#             brands
#         ),

#         "categories": normalise_list(
#             categories
#         ),

#         "suppliers": normalise_list(
#             suppliers
#         ),

#         "cv_ranks": normalise_list(
#             cv_ranks
#         ),

#         "median_deviation_limit": (
#             median_deviation_limit
#         ),

#         "date_range": (
#             list(date_range)
#             if isinstance(
#                 date_range,
#                 (list, tuple),
#             )
#             else None
#         ),
#     }


# def get_filtered_analysis_from_store(
#     filter_store: dict | None,
# ) -> pd.DataFrame:
#     """
#     Получает агрегированный анализ
#     и применяет параметры из Store.

#     Используется при формировании
#     Excel и CSV.
#     """

#     if not filter_store:
#         return pd.DataFrame()

#     analysis_df = (
#         get_price_analysis_data()
#         .copy()
#     )

#     if analysis_df.empty:
#         return analysis_df

#     return apply_all_analysis_filters(
#         analysis_df,
#         cost_type=filter_store.get(
#             "cost_type"
#         ),
#         brands=filter_store.get(
#             "brands"
#         ),
#         categories=filter_store.get(
#             "categories"
#         ),
#         suppliers=filter_store.get(
#             "suppliers"
#         ),
#         cv_ranks=filter_store.get(
#             "cv_ranks"
#         ),
#         median_deviation_limit=(
#             filter_store.get(
#                 "median_deviation_limit"
#             )
#         ),
#         date_range=filter_store.get(
#             "date_range"
#         ),
#     )


# # ---------------------------------------------------------------------
# # Регистрация callbacks фильтров
# # ---------------------------------------------------------------------


# def register_filter_callbacks(
#     app,
# ):
#     """
#     Регистрирует все callbacks,
#     относящиеся к фильтрам:

#     1. загрузку и обновление данных;
#     2. зависимые списки;
#     3. сброс фильтров.
#     """

#     # -----------------------------------------------------------------
#     # Загрузка данных и обновление кеша
#     # -----------------------------------------------------------------

#     @app.callback(
#         Output(
#             DATA_STORE_ID,
#             "data",
#         ),
#         Output(
#             LAST_UPDATE_ID,
#             "children",
#         ),
#         Input(
#             REFRESH_DATA_BTN_ID,
#             "n_clicks",
#         ),
#         prevent_initial_call=False,
#     )
#     def load_filter_data(
#         refresh_clicks,
#     ):
#         """
#         Загружает данные и передаёт
#         сигнал для зависимых фильтров.
#         """

#         if refresh_clicks:
#             clear_price_analysis_cache()

#         # Прогреваем кеш анализа.
#         get_price_analysis_data()

#         now = datetime.now()

#         return (
#             {
#                 "version": (
#                     now.isoformat()
#                 ),
#             },
#             now.strftime(
#                 "%d.%m.%Y %H:%M"
#             ),
#         )

#     # -----------------------------------------------------------------
#     # Умные категории и поставщики
#     # -----------------------------------------------------------------

#     @app.callback(
#         Output(
#             BRAND_FILTER_ID,
#             "data",
#         ),
#         Output(
#             CATEGORY_FILTER_ID,
#             "data",
#         ),
#         Output(
#             CATEGORY_FILTER_ID,
#             "value",
#         ),
#         Output(
#             SUPPLIER_FILTER_ID,
#             "data",
#         ),
#         Output(
#             SUPPLIER_FILTER_ID,
#             "value",
#         ),
#         Input(
#             DATA_STORE_ID,
#             "data",
#         ),
#         Input(
#             BRAND_FILTER_ID,
#             "value",
#         ),
#         Input(
#             CATEGORY_FILTER_ID,
#             "value",
#         ),
#         State(
#             SUPPLIER_FILTER_ID,
#             "value",
#         ),
#         prevent_initial_call=False,
#     )
#     def update_smart_filter_options(
#         data_signal,
#         selected_brands,
#         selected_categories,
#         selected_suppliers,
#     ):
#         """
#         Обновляет зависимые справочники.

#         Бренд:
#             показывает все бренды.

#         Категория:
#             зависит от выбранного бренда.

#         Поставщик:
#             зависит от выбранного бренда
#             и выбранной категории.
#         """

#         if not data_signal:
#             return (
#                 [],
#                 [],
#                 [],
#                 [],
#                 [],
#             )

#         analysis_df = (
#             get_price_analysis_data()
#             .copy()
#         )

#         history_df = (
#             get_price_history_data()
#             .copy()
#         )

#         if analysis_df.empty:
#             return (
#                 [],
#                 [],
#                 [],
#                 [],
#                 [],
#             )

#         # -------------------------------------------------------------
#         # Все бренды
#         # -------------------------------------------------------------

#         brand_options = (
#             build_filter_options(
#                 analysis_df,
#                 "Бренд",
#             )
#         )

#         # -------------------------------------------------------------
#         # Категории выбранных брендов
#         # -------------------------------------------------------------

#         brand_filtered_df = (
#             _filter_analysis_for_options(
#                 analysis_df,
#                 brands=selected_brands,
#             )
#         )

#         category_options = (
#             build_filter_options(
#                 brand_filtered_df,
#                 "Категория",
#             )
#         )

#         clean_categories = (
#             _keep_available_values(
#                 selected_categories,
#                 category_options,
#             )
#         )

#         # -------------------------------------------------------------
#         # Поставщики выбранных брендов и категорий
#         # -------------------------------------------------------------

#         category_filtered_df = (
#             _filter_analysis_for_options(
#                 brand_filtered_df,
#                 categories=clean_categories,
#             )
#         )

#         supplier_options = (
#             _build_smart_supplier_options(
#                 category_filtered_df,
#                 history_df,
#             )
#         )

#         clean_suppliers = (
#             _keep_available_values(
#                 selected_suppliers,
#                 supplier_options,
#             )
#         )

#         return (
#             brand_options,
#             category_options,
#             clean_categories,
#             supplier_options,
#             clean_suppliers,
#         )

#     # -----------------------------------------------------------------
#     # Сброс фильтров
#     # -----------------------------------------------------------------

#     @app.callback(
#         Output(
#             COST_TYPE_FILTER_ID,
#             "value",
#         ),
#         Output(
#             BRAND_FILTER_ID,
#             "value",
#             allow_duplicate=True,
#         ),
#         Output(
#             CATEGORY_FILTER_ID,
#             "value",
#             allow_duplicate=True,
#         ),
#         Output(
#             SUPPLIER_FILTER_ID,
#             "value",
#             allow_duplicate=True,
#         ),
#         Output(
#             CV_RANK_FILTER_ID,
#             "value",
#         ),
#         Output(
#             MEDIAN_DEVIATION_FILTER_ID,
#             "value",
#         ),
#         Output(
#             DATE_FILTER_ID,
#             "value",
#         ),
#         Input(
#             RESET_FILTERS_BTN_ID,
#             "n_clicks",
#         ),
#         prevent_initial_call=True,
#     )
#     def reset_filters(
#         n_clicks,
#     ):
#         """
#         Возвращает фильтры
#         к исходным значениям.
#         """

#         if not n_clicks:
#             return (
#                 no_update,
#                 no_update,
#                 no_update,
#                 no_update,
#                 no_update,
#                 no_update,
#                 no_update,
#             )

#         return (
#             DEFAULT_COST_TYPE,
#             [],
#             [],
#             [],
#             [],
#             DEFAULT_MEDIAN_DEVIATION_LIMIT,
#             None,
#         )
# gear/app/costs_control/filters.py
from __future__ import annotations

from datetime import datetime
from typing import Any

import dash_mantine_components as dmc
import pandas as pd
from dash import (
    Input,
    Output,
    State,
    ctx,
    html,
    no_update,
)
from dash_iconify import DashIconify

from .calculations import (
    apply_filters,
    build_filter_options,
)
from .components import (
    action_button,
    section_header,
)
from .config import (
    COLORS,
    COST_TYPES,
    CV_RANK_OPTIONS,
    DEFAULT_COST_TYPE,
    DEFAULT_MEDIAN_DEVIATION_LIMIT,
)
from .data import (
    clear_price_analysis_cache,
    get_price_analysis_data,
    get_price_history_data,
)
from .ids import (
    BRAND_FILTER_ID,
    CATEGORY_FILTER_ID,
    COST_TYPE_FILTER_ID,
    CV_RANK_FILTER_ID,
    DATA_STORE_ID,
    DATE_FILTER_ID,
    LAST_UPDATE_ID,
    MEDIAN_DEVIATION_FILTER_ID,
    REFRESH_DATA_BTN_ID,
    RESET_FILTERS_BTN_ID,
    SUPPLIER_FILTER_ID,
)
from .styles import (
    FILTER_GRID_STYLE,
    PANEL_STYLE,
)


# ---------------------------------------------------------------------
# Нормализация
# ---------------------------------------------------------------------


def normalise_nm_id(value: Any) -> str:
    """
    Приводит NM ID к строке без окончания .0.
    """

    if value is None:
        return ""

    text = str(value).strip()

    if text.endswith(".0"):
        text = text[:-2]

    return text


def normalise_list(value) -> list:
    """
    Приводит значение MultiSelect к обычному списку.
    """

    if value is None:
        return []

    if isinstance(value, (str, int, float)):
        return [value]

    return list(value)


def _clean_values(values) -> list[str]:
    """
    Очищает список выбранных значений.
    """

    return [
        str(value).strip()
        for value in normalise_list(values)
        if value is not None
        and str(value).strip()
    ]


# ---------------------------------------------------------------------
# Визуальный контейнер фильтра
# ---------------------------------------------------------------------


def _filter_field(
    *,
    icon: str,
    title: str,
    subtitle: str,
    component,
):
    """
    Единый визуальный контейнер фильтра.
    """

    return html.Div(
        style={
            "minWidth": 0,
            "padding": "11px 12px 12px",
            "backgroundColor": "#FFFFFF",
            "border": (
                "1px solid "
                + COLORS.get(
                    "border",
                    "#D9DEE2",
                )
            ),
        },
        children=[
            html.Div(
                style={
                    "display": "flex",
                    "alignItems": "flex-start",
                    "gap": "8px",
                    "marginBottom": "9px",
                },
                children=[
                    DashIconify(
                        icon=icon,
                        width=16,
                        height=16,
                        color=COLORS.get(
                            "green",
                            "#2F6656",
                        ),
                        style={
                            "marginTop": "1px",
                            "flex": "0 0 auto",
                        },
                    ),
                    html.Div(
                        style={
                            "minWidth": 0,
                        },
                        children=[
                            html.Div(
                                title,
                                style={
                                    "fontSize": "12px",
                                    "fontWeight": 700,
                                    "lineHeight": "16px",
                                    "color": COLORS.get(
                                        "text",
                                        "#111827",
                                    ),
                                },
                            ),
                            html.Div(
                                subtitle,
                                style={
                                    "marginTop": "1px",
                                    "fontSize": "10px",
                                    "lineHeight": "14px",
                                    "color": COLORS.get(
                                        "muted",
                                        "#6B7280",
                                    ),
                                },
                            ),
                        ],
                    ),
                ],
            ),
            component,
        ],
    )


# ---------------------------------------------------------------------
# Layout панели фильтров
# ---------------------------------------------------------------------


def build_filter_panel():
    """
    Панель фильтров анализа.

    В интерфейсе показываются:

    - тип себестоимости;
    - бренд;
    - категория;
    - поставщик;
    - ранг CV.

    Фильтры периода УПД и порога отклонения
    от медианы скрыты, но компоненты оставлены
    в layout для совместимости с callbacks.py
    и export.py.
    """

    return html.Div(
        style=PANEL_STYLE,
        children=[
            dmc.Group(
                justify="space-between",
                align="center",
                mb=14,
                children=[
                    section_header(
                        "Фильтры анализа",
                        (
                            "Категории и поставщики "
                            "автоматически подстраиваются "
                            "под выбранные значения"
                        ),
                    ),
                    action_button(
                        component_id=RESET_FILTERS_BTN_ID,
                        label="Сбросить",
                        icon="solar:restart-linear",
                        color="gray",
                    ),
                ],
            ),

            html.Div(
                style={
                    **FILTER_GRID_STYLE,
                    "gridTemplateColumns": (
                        "repeat(auto-fit, minmax(235px, 1fr))"
                    ),
                    "gap": "10px",
                },
                children=[
                    # -------------------------------------------------
                    # Тип себестоимости
                    # -------------------------------------------------

                    _filter_field(
                        icon=(
                            "solar:"
                            "calculator-minimalistic-linear"
                        ),
                        title="Тип себестоимости",
                        subtitle=(
                            "Показатели и графики "
                            "будут пересчитаны"
                        ),
                        component=dmc.SegmentedControl(
                            id=COST_TYPE_FILTER_ID,
                            value=DEFAULT_COST_TYPE,
                            data=COST_TYPES,
                            radius=0,
                            size="xs",
                            fullWidth=True,
                        ),
                    ),

                    # -------------------------------------------------
                    # Бренд
                    # -------------------------------------------------

                    _filter_field(
                        icon="solar:tag-linear",
                        title="Бренд",
                        subtitle=(
                            "Можно выбрать "
                            "несколько брендов"
                        ),
                        component=dmc.MultiSelect(
                            id=BRAND_FILTER_ID,
                            placeholder="Все бренды",
                            data=[],
                            value=[],
                            searchable=True,
                            clearable=True,
                            nothingFoundMessage=(
                                "Бренды не найдены"
                            ),
                            radius=0,
                            size="xs",
                            maxDropdownHeight=300,
                        ),
                    ),

                    # -------------------------------------------------
                    # Категория
                    # -------------------------------------------------

                    _filter_field(
                        icon=(
                            "solar:"
                            "folder-with-files-linear"
                        ),
                        title="Категория",
                        subtitle=(
                            "Список зависит "
                            "от выбранного бренда"
                        ),
                        component=dmc.MultiSelect(
                            id=CATEGORY_FILTER_ID,
                            placeholder="Все категории",
                            data=[],
                            value=[],
                            searchable=True,
                            clearable=True,
                            nothingFoundMessage=(
                                "Категории не найдены"
                            ),
                            radius=0,
                            size="xs",
                            maxDropdownHeight=300,
                        ),
                    ),

                    # -------------------------------------------------
                    # Поставщик
                    # -------------------------------------------------

                    _filter_field(
                        icon="solar:buildings-2-linear",
                        title="Поставщик",
                        subtitle=(
                            "Список зависит от "
                            "бренда и категории"
                        ),
                        component=dmc.MultiSelect(
                            id=SUPPLIER_FILTER_ID,
                            placeholder="Все поставщики",
                            data=[],
                            value=[],
                            searchable=True,
                            clearable=True,
                            nothingFoundMessage=(
                                "Поставщики не найдены"
                            ),
                            radius=0,
                            size="xs",
                            maxDropdownHeight=300,
                        ),
                    ),

                    # -------------------------------------------------
                    # Ранг CV
                    # -------------------------------------------------

                    _filter_field(
                        icon="solar:chart-square-linear",
                        title=(
                            "Ранг коэффициента вариации"
                        ),
                        subtitle=(
                            "Уровень стабильности "
                            "закупочной цены"
                        ),
                        component=dmc.MultiSelect(
                            id=CV_RANK_FILTER_ID,
                            placeholder="Все ранги",
                            data=CV_RANK_OPTIONS,
                            value=[],
                            searchable=False,
                            clearable=True,
                            radius=0,
                            size="xs",
                            maxDropdownHeight=260,
                        ),
                    ),
                ],
            ),

            # ---------------------------------------------------------
            # Скрытые компоненты
            # ---------------------------------------------------------
            #
            # Они не отображаются пользователю.
            #
            # Но их нельзя полностью удалять, пока callbacks.py
            # и export.py используют эти ID в Input или State.
            # Иначе Dash не сможет запустить основной callback.
            # ---------------------------------------------------------

            html.Div(
                style={
                    "display": "none",
                },
                children=[
                    dmc.NumberInput(
                        id=MEDIAN_DEVIATION_FILTER_ID,
                        value=DEFAULT_MEDIAN_DEVIATION_LIMIT,
                    ),
                    dmc.DatePickerInput(
                        id=DATE_FILTER_ID,
                        type="range",
                        value=None,
                    ),
                ],
            ),

            # ---------------------------------------------------------
            # Подсказка
            # ---------------------------------------------------------

            html.Div(
                style={
                    "display": "flex",
                    "alignItems": "center",
                    "gap": "7px",
                    "marginTop": "10px",
                    "padding": "8px 10px",
                    "backgroundColor": COLORS.get(
                        "very_light_green",
                        "#F3F8F6",
                    ),
                    "border": (
                        "1px solid "
                        + COLORS.get(
                            "border",
                            "#D9DEE2",
                        )
                    ),
                    "fontSize": "10px",
                    "lineHeight": "14px",
                    "color": COLORS.get(
                        "muted",
                        "#6B7280",
                    ),
                },
                children=[
                    DashIconify(
                        icon="solar:info-circle-linear",
                        width=14,
                        height=14,
                        color=COLORS.get(
                            "green",
                            "#2F6656",
                        ),
                    ),
                    html.Span(
                        (
                            "Для поиска конкретного товара "
                            "используйте встроенные фильтры "
                            "таблицы на вкладке «Товары»."
                        )
                    ),
                ],
            ),
        ],
    )


# ---------------------------------------------------------------------
# Вспомогательная фильтрация зависимых списков
# ---------------------------------------------------------------------


def _filter_analysis_for_options(
    analysis_df: pd.DataFrame,
    *,
    brands=None,
    categories=None,
) -> pd.DataFrame:
    """
    Фильтрует агрегированный анализ только
    для построения зависимых справочников.
    """

    if analysis_df.empty:
        return analysis_df.copy()

    result = analysis_df.copy()

    selected_brands = _clean_values(brands)
    selected_categories = _clean_values(categories)

    if (
        selected_brands
        and "Бренд" in result.columns
    ):
        result = result.loc[
            result["Бренд"]
            .fillna("")
            .astype(str)
            .isin(selected_brands)
        ].copy()

    if (
        selected_categories
        and "Категория" in result.columns
    ):
        result = result.loc[
            result["Категория"]
            .fillna("")
            .astype(str)
            .isin(selected_categories)
        ].copy()

    return result.reset_index(drop=True)


def _find_nm_id_column(
    df: pd.DataFrame,
) -> str | None:
    """
    Находит колонку NM ID.
    """

    for column in (
        "nm_id",
        "NM ID",
        "nmId",
    ):
        if column in df.columns:
            return column

    return None


def _build_smart_supplier_options(
    analysis_df: pd.DataFrame,
    history_df: pd.DataFrame,
) -> list:
    """
    Возвращает поставщиков только по NM ID,
    которые остались после фильтра бренда
    и категории.
    """

    if (
        analysis_df.empty
        or history_df.empty
    ):
        return []

    analysis_nm_column = _find_nm_id_column(
        analysis_df
    )

    history_nm_column = _find_nm_id_column(
        history_df
    )

    if (
        not analysis_nm_column
        or not history_nm_column
    ):
        return build_filter_options(
            history_df,
            "Поставщик",
        )

    allowed_ids = {
        normalise_nm_id(value)
        for value in (
            analysis_df[analysis_nm_column]
            .dropna()
            .tolist()
        )
        if normalise_nm_id(value)
    }

    if not allowed_ids:
        return []

    history_ids = (
        history_df[history_nm_column]
        .astype(str)
        .map(normalise_nm_id)
    )

    filtered_history = (
        history_df.loc[
            history_ids.isin(allowed_ids)
        ]
        .copy()
        .reset_index(drop=True)
    )

    return build_filter_options(
        filtered_history,
        "Поставщик",
    )


def _option_values(
    options: list,
) -> set[str]:
    """
    Получает множество value из options Mantine.
    """

    values: set[str] = set()

    for option in options or []:
        if isinstance(option, dict):
            value = option.get("value")
        else:
            value = option

        if value is not None:
            values.add(str(value))

    return values


def _keep_available_values(
    selected_values,
    options: list,
) -> list[str]:
    """
    Оставляет только выбранные значения,
    присутствующие в новых options.
    """

    available_values = _option_values(
        options
    )

    return [
        value
        for value in _clean_values(
            selected_values
        )
        if value in available_values
    ]


# ---------------------------------------------------------------------
# Фильтрация по поставщикам
# ---------------------------------------------------------------------


def filter_analysis_by_suppliers(
    df: pd.DataFrame,
    suppliers,
) -> pd.DataFrame:
    """
    Фильтрует агрегированную таблицу
    по выбранным поставщикам.

    В агрегированном анализе колонка
    «Поставщики» может содержать несколько
    поставщиков в одной строке.
    """

    selected_suppliers = _clean_values(
        suppliers
    )

    if (
        df.empty
        or not selected_suppliers
        or "Поставщики" not in df.columns
    ):
        return df.copy()

    supplier_text = (
        df["Поставщики"]
        .fillna("")
        .astype(str)
    )

    mask = pd.Series(
        False,
        index=df.index,
    )

    for supplier in selected_suppliers:
        mask |= supplier_text.str.contains(
            supplier,
            case=False,
            regex=False,
            na=False,
        )

    return (
        df.loc[mask]
        .copy()
        .reset_index(drop=True)
    )


# ---------------------------------------------------------------------
# Общая фильтрация агрегированного анализа
# ---------------------------------------------------------------------


def apply_all_analysis_filters(
    analysis_df: pd.DataFrame,
    *,
    cost_type=None,
    brands=None,
    categories=None,
    suppliers=None,
    cv_ranks=None,
    median_deviation_limit=None,
    date_range=None,
) -> pd.DataFrame:
    """
    Применяет активные фильтры.

    median_deviation_limit и date_range оставлены
    в сигнатуре для совместимости с остальными файлами,
    но пользователь не управляет ими через интерфейс.
    """

    if analysis_df.empty:
        return analysis_df.copy()

    filtered = apply_filters(
        analysis_df,
        cost_type=(
            cost_type
            or DEFAULT_COST_TYPE
        ),
        brands=normalise_list(
            brands
        ),
        categories=normalise_list(
            categories
        ),

        # Поставщики фильтруются отдельно.
        suppliers=None,

        # Удалённые фильтры.
        nm_ids=None,
        cv_min=None,
        only_changed=False,
        only_anomalies=False,

        cv_ranks=normalise_list(
            cv_ranks
        ),

        # Период в интерфейсе отключён.
        date_range=None,

        # Порог отклонения в интерфейсе отключён.
        # Оставляем None, чтобы он не фильтровал данные.
        median_deviation_limit=None,
    )

    return filter_analysis_by_suppliers(
        filtered,
        suppliers,
    )


# ---------------------------------------------------------------------
# Фильтрация истории УПД
# ---------------------------------------------------------------------


def filter_history_data(
    history_df: pd.DataFrame,
    *,
    nm_ids=None,
    suppliers=None,
    date_range=None,
) -> pd.DataFrame:
    """
    Фильтрует историю УПД на сервере.

    Фильтр периода в интерфейсе отключён,
    но параметр оставлен для совместимости.
    """

    if history_df.empty:
        return history_df.copy()

    result = history_df.copy()

    # -------------------------------------------------------------
    # NM ID
    # -------------------------------------------------------------

    if nm_ids is not None:
        allowed_ids = {
            normalise_nm_id(value)
            for value in normalise_list(
                nm_ids
            )
            if normalise_nm_id(value)
        }

        nm_id_column = _find_nm_id_column(
            result
        )

        if (
            not allowed_ids
            or not nm_id_column
        ):
            return result.iloc[0:0].copy()

        history_ids = (
            result[nm_id_column]
            .astype(str)
            .map(normalise_nm_id)
        )

        result = result.loc[
            history_ids.isin(allowed_ids)
        ].copy()

    # -------------------------------------------------------------
    # Поставщики
    # -------------------------------------------------------------

    selected_suppliers = _clean_values(
        suppliers
    )

    if (
        selected_suppliers
        and "Поставщик" in result.columns
    ):
        result = result.loc[
            result["Поставщик"]
            .fillna("")
            .astype(str)
            .isin(selected_suppliers)
        ].copy()

    # Период УПД намеренно не применяется.

    return result.reset_index(drop=True)


# ---------------------------------------------------------------------
# Store параметров фильтров
# ---------------------------------------------------------------------


def build_filter_store(
    *,
    cost_type=None,
    brands=None,
    categories=None,
    suppliers=None,
    cv_ranks=None,
    median_deviation_limit=None,
    date_range=None,
) -> dict:
    """
    Создаёт Store с параметрами активных фильтров.

    Скрытые фильтры записываются как None,
    чтобы они не влияли на результат.
    """

    return {
        "cost_type": (
            cost_type
            or DEFAULT_COST_TYPE
        ),
        "brands": normalise_list(
            brands
        ),
        "categories": normalise_list(
            categories
        ),
        "suppliers": normalise_list(
            suppliers
        ),
        "cv_ranks": normalise_list(
            cv_ranks
        ),

        # Отключённые фильтры.
        "median_deviation_limit": None,
        "date_range": None,
    }


def get_filtered_analysis_from_store(
    filter_store: dict | None,
) -> pd.DataFrame:
    """
    Получает агрегированный анализ
    и применяет параметры из Store.

    Используется при формировании Excel и CSV.
    """

    analysis_df = (
        get_price_analysis_data()
        .copy()
    )

    if analysis_df.empty:
        return analysis_df

    if not filter_store:
        return analysis_df

    return apply_all_analysis_filters(
        analysis_df,
        cost_type=filter_store.get(
            "cost_type",
            DEFAULT_COST_TYPE,
        ),
        brands=filter_store.get(
            "brands",
            [],
        ),
        categories=filter_store.get(
            "categories",
            [],
        ),
        suppliers=filter_store.get(
            "suppliers",
            [],
        ),
        cv_ranks=filter_store.get(
            "cv_ranks",
            [],
        ),
        median_deviation_limit=None,
        date_range=None,
    )


# ---------------------------------------------------------------------
# Регистрация callbacks фильтров
# ---------------------------------------------------------------------


def register_filter_callbacks(app):
    """
    Регистрирует callbacks фильтров.

    Важно:

    - DATA_STORE_ID меняется один раз при загрузке;
    - options зависимых фильтров обновляются отдельно;
    - value фильтров меняется только тогда,
      когда выбранное значение действительно стало недоступно;
    - одинаковые значения не возвращаются повторно;
    - поэтому таблицы не должны перерисовываться
      несколько раз без необходимости.
    """

    # -----------------------------------------------------------------
    # Загрузка данных и обновление кеша
    # -----------------------------------------------------------------

    @app.callback(
        Output(
            DATA_STORE_ID,
            "data",
        ),
        Output(
            LAST_UPDATE_ID,
            "children",
        ),
        Input(
            REFRESH_DATA_BTN_ID,
            "n_clicks",
        ),
        prevent_initial_call=False,
    )
    def load_filter_data(refresh_clicks):
        """
        Загружает данные один раз.

        При нажатии на кнопку обновления:
        - очищает кеш;
        - заново получает данные;
        - обновляет сигнал DATA_STORE_ID.
        """

        if refresh_clicks:
            clear_price_analysis_cache()

        analysis_df = get_price_analysis_data()

        now = datetime.now()

        return (
            {
                "version": now.isoformat(),
                "rows": int(len(analysis_df)),
            },
            now.strftime("%d.%m.%Y %H:%M"),
        )

    # -----------------------------------------------------------------
    # Обновление зависимых options
    # -----------------------------------------------------------------

    @app.callback(
        Output(
            BRAND_FILTER_ID,
            "data",
        ),
        Output(
            CATEGORY_FILTER_ID,
            "data",
        ),
        Output(
            SUPPLIER_FILTER_ID,
            "data",
        ),
        Input(
            DATA_STORE_ID,
            "data",
        ),
        Input(
            BRAND_FILTER_ID,
            "value",
        ),
        Input(
            CATEGORY_FILTER_ID,
            "value",
        ),
        prevent_initial_call=False,
    )
    def update_smart_filter_options(
        data_signal,
        selected_brands,
        selected_categories,
    ):
        """
        Обновляет только списки options.

        Этот callback не меняет value фильтров,
        поэтому сам по себе не вызывает повторную
        перерисовку таблиц.
        """

        if not data_signal:
            return [], [], []

        analysis_df = (
            get_price_analysis_data()
            .copy()
        )

        history_df = (
            get_price_history_data()
            .copy()
        )

        if analysis_df.empty:
            return [], [], []

        # -------------------------------------------------------------
        # Все бренды
        # -------------------------------------------------------------

        brand_options = build_filter_options(
            analysis_df,
            "Бренд",
        )

        # -------------------------------------------------------------
        # Категории выбранных брендов
        # -------------------------------------------------------------

        brand_filtered_df = (
            _filter_analysis_for_options(
                analysis_df,
                brands=selected_brands,
            )
        )

        category_options = build_filter_options(
            brand_filtered_df,
            "Категория",
        )

        clean_categories = (
            _keep_available_values(
                selected_categories,
                category_options,
            )
        )

        # -------------------------------------------------------------
        # Поставщики выбранных брендов и категорий
        # -------------------------------------------------------------

        category_filtered_df = (
            _filter_analysis_for_options(
                brand_filtered_df,
                categories=clean_categories,
            )
        )

        supplier_options = (
            _build_smart_supplier_options(
                category_filtered_df,
                history_df,
            )
        )

        return (
            brand_options,
            category_options,
            supplier_options,
        )

    # -----------------------------------------------------------------
    # Очистка недоступных категорий
    # -----------------------------------------------------------------

    @app.callback(
        Output(
            CATEGORY_FILTER_ID,
            "value",
            allow_duplicate=True,
        ),
        Input(
            CATEGORY_FILTER_ID,
            "data",
        ),
        State(
            CATEGORY_FILTER_ID,
            "value",
        ),
        prevent_initial_call=True,
    )
    def clean_category_values(
        category_options,
        selected_categories,
    ):
        """
        Удаляет только те выбранные категории,
        которых больше нет в options.

        Если список не изменился, возвращает no_update.
        """

        current_values = _clean_values(
            selected_categories
        )

        clean_values = _keep_available_values(
            current_values,
            category_options,
        )

        if clean_values == current_values:
            return no_update

        return clean_values

    # -----------------------------------------------------------------
    # Очистка недоступных поставщиков
    # -----------------------------------------------------------------

    @app.callback(
        Output(
            SUPPLIER_FILTER_ID,
            "value",
            allow_duplicate=True,
        ),
        Input(
            SUPPLIER_FILTER_ID,
            "data",
        ),
        State(
            SUPPLIER_FILTER_ID,
            "value",
        ),
        prevent_initial_call=True,
    )
    def clean_supplier_values(
        supplier_options,
        selected_suppliers,
    ):
        """
        Удаляет только тех поставщиков,
        которых больше нет в options.

        Если список не изменился, возвращает no_update.
        """

        current_values = _clean_values(
            selected_suppliers
        )

        clean_values = _keep_available_values(
            current_values,
            supplier_options,
        )

        if clean_values == current_values:
            return no_update

        return clean_values

    # -----------------------------------------------------------------
    # Сброс видимых фильтров
    # -----------------------------------------------------------------

    @app.callback(
        Output(
            COST_TYPE_FILTER_ID,
            "value",
        ),
        Output(
            BRAND_FILTER_ID,
            "value",
        ),
        Output(
            CATEGORY_FILTER_ID,
            "value",
            allow_duplicate=True,
        ),
        Output(
            SUPPLIER_FILTER_ID,
            "value",
            allow_duplicate=True,
        ),
        Output(
            CV_RANK_FILTER_ID,
            "value",
        ),
        Input(
            RESET_FILTERS_BTN_ID,
            "n_clicks",
        ),
        prevent_initial_call=True,
    )
    def reset_filters(n_clicks):
        """
        Полностью сбрасывает все видимые фильтры.
        """

        if not n_clicks:
            return (
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
            )

        return (
            DEFAULT_COST_TYPE,
            [],
            [],
            [],
            [],
        )