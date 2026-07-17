# # gear/app/costs_control/filters.py
# from __future__ import annotations

# from datetime import date, datetime, timedelta
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
#     get_price_analysis_data,
#     get_price_history_data,
#     get_min_upd_date,
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
# # Локальные ID
# # ---------------------------------------------------------------------


# DATE_PRESET_ID = (
#     "costs-control-date-preset"
# )


# # ---------------------------------------------------------------------
# # Даты
# # ---------------------------------------------------------------------


# # def get_default_date_range() -> list[str]:
# #     """
# #     Возвращает период по умолчанию:

# #     с начала текущего года по сегодня.
# #     """

# #     today = date.today()
# #     year_start = date(
# #         year=today.year,
# #         month=1,
# #         day=1,
# #     )

# #     return [
# #         year_start.isoformat(),
# #         today.isoformat(),
# #     ]

# def get_default_date_range() -> list[str]:
#     """
#     Возвращает период по умолчанию:

#     от первой даты УПД
#     до сегодняшнего дня.
#     """

#     today = date.today()

#     return [
#         get_min_upd_date().isoformat(),
#         today.isoformat(),
#     ]






# def normalise_date_range(
#     date_range,
# ) -> tuple[str | None, str | None]:
#     """
#     Приводит значение DatePickerInput
#     к паре строк:

#     date_from, date_to

#     Формат:

#     YYYY-MM-DD
#     """

#     if not date_range:
#         return None, None

#     if not isinstance(
#         date_range,
#         (list, tuple),
#     ):
#         return None, None

#     if len(date_range) < 2:
#         return None, None

#     date_from = date_range[0]
#     date_to = date_range[1]

#     if not date_from or not date_to:
#         return None, None

#     date_from = str(date_from)[:10]
#     date_to = str(date_to)[:10]

#     if date_from > date_to:
#         date_from, date_to = (
#             date_to,
#             date_from,
#         )

#     return date_from, date_to


# def _get_quarter_start(
#     current_date: date,
# ) -> date:
#     """
#     Возвращает первый день квартала.
#     """

#     quarter_month = (
#         ((current_date.month - 1) // 3)
#         * 3
#         + 1
#     )

#     return date(
#         year=current_date.year,
#         month=quarter_month,
#         day=1,
#     )


# def _build_preset_date_range(
#     preset: str | None,
# ) -> list[str]:
#     """
#     Формирует диапазон дат
#     для выбранного пресета.
#     """

#     today = date.today()

#     if preset == "last_30_days":
#         date_from = (
#             today
#             - timedelta(days=29)
#         )

#     elif preset == "current_month":
#         date_from = date(
#             year=today.year,
#             month=today.month,
#             day=1,
#         )

#     elif preset == "current_quarter":
#         date_from = _get_quarter_start(
#             today
#         )

#     else:
#         date_from = date(
#             year=today.year,
#             month=1,
#             day=1,
#         )

#     return [
#         date_from.isoformat(),
#         today.isoformat(),
#     ]


# # ---------------------------------------------------------------------
# # Нормализация
# # ---------------------------------------------------------------------


# def normalise_nm_id(
#     value: Any,
# ) -> str:
#     """
#     Приводит NM ID к строке
#     без окончания .0.
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
#     Приводит значение MultiSelect
#     к обычному списку.
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
#         for value in normalise_list(
#             values
#         )
#         if (
#             value is not None
#             and str(value).strip()
#         )
#     ]


# # ---------------------------------------------------------------------
# # Поиск колонок
# # ---------------------------------------------------------------------


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


# def _find_history_date_column(
#     df: pd.DataFrame,
# ) -> str | None:
#     """
#     Находит колонку даты УПД
#     в таблице истории.
#     """

#     for column in (
#         "Дата УПД",
#         "date",
#         "Дата",
#         "upd_date",
#         "document_date",
#     ):
#         if column in df.columns:
#             return column

#     return None


# # ---------------------------------------------------------------------
# # Визуальный контейнер фильтра
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
# # Фильтр периода
# # ---------------------------------------------------------------------


# def _build_date_filter():
#     """
#     Строит DatePicker и быстрые пресеты.
#     """

#     return _filter_field(
#         icon="solar:calendar-date-linear",
#         title="Период УПД",
#         subtitle=(
#             "Все показатели рассчитываются "
#             "только за выбранный период"
#         ),
#         component=dmc.Stack(
#             gap=7,
#             children=[
#                 dmc.DatePickerInput(
#                     id=DATE_FILTER_ID,
#                     type="range",
#                     value=get_default_date_range(),
#                     valueFormat="DD.MM.YYYY",
#                     placeholder="Весь период",
#                     clearable=True,
#                     allowSingleDateInRange=False,
#                     firstDayOfWeek=1,
#                     radius=0,
#                     size="xs",
#                     w="100%",
#                     leftSection=DashIconify(
#                         icon=(
#                             "solar:"
#                             "calendar-linear"
#                         ),
#                         width=15,
#                         height=15,
#                     ),
#                     styles={
#                         "input": {
#                             "height": "32px",
#                             "minHeight": "32px",
#                             "fontSize": "11px",
#                             "fontWeight": 500,
#                             "borderColor": (
#                                 COLORS.get(
#                                     "border",
#                                     "#D9DEE2",
#                                 )
#                             ),
#                             "backgroundColor": (
#                                 "#FFFFFF"
#                             ),
#                         },
#                     },
#                 ),

#                 dmc.SegmentedControl(
#                     id=DATE_PRESET_ID,
#                     value="ytd",
#                     data=[
#                         {
#                             "label": "30 дней",
#                             "value": (
#                                 "last_30_days"
#                             ),
#                         },
#                         {
#                             "label": "Месяц",
#                             "value": (
#                                 "current_month"
#                             ),
#                         },
#                         {
#                             "label": "Квартал",
#                             "value": (
#                                 "current_quarter"
#                             ),
#                         },
#                         {
#                             "label": "С начала года",
#                             "value": "ytd",
#                         },
#                     ],
#                     radius=0,
#                     size="xs",
#                     fullWidth=True,
#                     styles={
#                         "label": {
#                             "fontSize": "9px",
#                             "paddingLeft": "5px",
#                             "paddingRight": "5px",
#                         },
#                     },
#                 ),
#             ],
#         ),
#     )


# # ---------------------------------------------------------------------
# # Layout панели фильтров
# # ---------------------------------------------------------------------


# def build_filter_panel():
#     """
#     Панель фильтров анализа.

#     Период УПД применяется до агрегации.
#     Поэтому MIN, MAX, MEDIAN, AVG и CV
#     рассчитываются только по выбранному периоду.
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
#                             "Показатели, графики "
#                             "и таблицы автоматически "
#                             "пересчитываются"
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
#                         "repeat("
#                         "auto-fit, "
#                         "minmax(235px, 1fr)"
#                         ")"
#                     ),
#                     "gap": "10px",
#                 },
#                 children=[
#                     # -------------------------------------------------
#                     # Период УПД
#                     # -------------------------------------------------

#                     _build_date_filter(),

#                     # -------------------------------------------------
#                     # Тип себестоимости
#                     # -------------------------------------------------

#                     _filter_field(
#                         icon=(
#                             "solar:"
#                             "calculator-"
#                             "minimalistic-linear"
#                         ),
#                         title="Тип себестоимости",
#                         subtitle=(
#                             "Показатели и графики "
#                             "будут пересчитаны"
#                         ),
#                         component=(
#                             dmc.SegmentedControl(
#                                 id=(
#                                     COST_TYPE_FILTER_ID
#                                 ),
#                                 value=(
#                                     DEFAULT_COST_TYPE
#                                 ),
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
#                             placeholder=(
#                                 "Все категории"
#                             ),
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
#                             "solar:"
#                             "buildings-2-linear"
#                         ),
#                         title="Поставщик",
#                         subtitle=(
#                             "Список зависит от "
#                             "бренда и категории"
#                         ),
#                         component=dmc.MultiSelect(
#                             id=SUPPLIER_FILTER_ID,
#                             placeholder=(
#                                 "Все поставщики"
#                             ),
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
#                             "solar:"
#                             "chart-square-linear"
#                         ),
#                         title=(
#                             "Ранг коэффициента "
#                             "вариации"
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
#                 ],
#             ),

#             # ---------------------------------------------------------
#             # Скрытый порог отклонения
#             # ---------------------------------------------------------

#             html.Div(
#                 style={
#                     "display": "none",
#                 },
#                 children=[
#                     dmc.NumberInput(
#                         id=(
#                             MEDIAN_DEVIATION_FILTER_ID
#                         ),
#                         value=(
#                             DEFAULT_MEDIAN_DEVIATION_LIMIT
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
#                     "backgroundColor": (
#                         COLORS.get(
#                             "very_light_green",
#                             "#F3F8F6",
#                         )
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
#                             "solar:"
#                             "info-circle-linear"
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
#                             "Для поиска конкретного "
#                             "товара используйте "
#                             "встроенные фильтры "
#                             "таблицы на вкладке "
#                             "«Товары»."
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
#     Фильтрует агрегированный анализ
#     для зависимых справочников.
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


# def _build_smart_supplier_options(
#     analysis_df: pd.DataFrame,
#     history_df: pd.DataFrame,
# ) -> list:
#     """
#     Возвращает поставщиков только по NM ID,
#     которые остались после фильтра бренда,
#     категории и периода.
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
#     из options Mantine.
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
#     Оставляет только значения,
#     присутствующие в новых options.
#     """

#     available_values = (
#         _option_values(
#             options
#         )
#     )

#     return [
#         value
#         for value in _clean_values(
#             selected_values
#         )
#         if value in available_values
#     ]


# # ---------------------------------------------------------------------
# # Фильтрация по поставщикам
# # ---------------------------------------------------------------------


# def filter_analysis_by_suppliers(
#     df: pd.DataFrame,
#     suppliers,
# ) -> pd.DataFrame:
#     """
#     Фильтрует агрегированную таблицу
#     по выбранным поставщикам.

#     Колонка «Поставщики» может содержать
#     несколько поставщиков в одной строке.
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
#     cost_type=None,
#     brands=None,
#     categories=None,
#     suppliers=None,
#     cv_ranks=None,
#     median_deviation_limit=None,
#     date_range=None,
# ) -> pd.DataFrame:
#     """
#     Применяет фильтры к уже рассчитанной
#     агрегированной таблице.

#     Важно:
#     период здесь повторно не применяется.

#     Период должен передаваться непосредственно
#     в get_price_analysis_data(), чтобы SQL
#     сначала отобрал УПД, а затем рассчитал
#     MIN, MAX, MEDIAN, AVG и CV.
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

#         # Поставщики обрабатываются отдельно.
#         suppliers=None,

#         # Удалённые фильтры.
#         nm_ids=None,
#         cv_min=None,
#         only_changed=False,
#         only_anomalies=False,

#         cv_ranks=normalise_list(
#             cv_ranks
#         ),

#         # Дата уже применена в SQL.
#         date_range=None,

#         # Порог скрыт и данные не фильтрует.
#         median_deviation_limit=None,
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
#     Фильтрует историю УПД:

#     - по NM ID;
#     - по поставщикам;
#     - по выбранному периоду.
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
#             return (
#                 result
#                 .iloc[0:0]
#                 .copy()
#             )

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
#     # Период УПД
#     # -------------------------------------------------------------

#     date_from, date_to = (
#         normalise_date_range(
#             date_range
#         )
#     )

#     date_column = (
#         _find_history_date_column(
#             result
#         )
#     )

#     if (
#         date_column
#         and (
#             date_from
#             or date_to
#         )
#     ):
#         result[date_column] = (
#             pd.to_datetime(
#                 result[date_column],
#                 errors="coerce",
#             )
#         )

#         if date_from:
#             result = result.loc[
#                 result[date_column]
#                 >= pd.Timestamp(date_from)
#             ].copy()

#         if date_to:
#             result = result.loc[
#                 result[date_column]
#                 < (
#                     pd.Timestamp(date_to)
#                     + pd.Timedelta(days=1)
#                 )
#             ].copy()

#     return result.reset_index(
#         drop=True
#     )


# # ---------------------------------------------------------------------
# # Store параметров фильтров
# # ---------------------------------------------------------------------


# def build_filter_store(
#     *,
#     cost_type=None,
#     brands=None,
#     categories=None,
#     suppliers=None,
#     cv_ranks=None,
#     median_deviation_limit=None,
#     date_range=None,
# ) -> dict:
#     """
#     Создаёт Store с параметрами
#     активных фильтров.
#     """

#     date_from, date_to = (
#         normalise_date_range(
#             date_range
#         )
#     )

#     normalised_range = None

#     if date_from and date_to:
#         normalised_range = [
#             date_from,
#             date_to,
#         ]

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

#         "median_deviation_limit": None,

#         "date_range": normalised_range,
#     }


# def get_filtered_analysis_from_store(
#     filter_store: dict | None,
# ) -> pd.DataFrame:
#     """
#     Повторно получает агрегированный
#     анализ на сервере.

#     Используется при формировании
#     таблиц, Excel и CSV.
#     """

#     if not filter_store:
#         date_range = (
#             get_default_date_range()
#         )
#     else:
#         date_range = (
#             filter_store.get(
#                 "date_range"
#             )
#             or get_default_date_range()
#         )

#     date_from, date_to = (
#         normalise_date_range(
#             date_range
#         )
#     )

#     analysis_df = (
#         get_price_analysis_data(
#             date_from=date_from,
#             date_to=date_to,
#         )
#         .copy()
#     )

#     if analysis_df.empty:
#         return analysis_df

#     if not filter_store:
#         return analysis_df

#     return apply_all_analysis_filters(
#         analysis_df,
#         cost_type=filter_store.get(
#             "cost_type",
#             DEFAULT_COST_TYPE,
#         ),
#         brands=filter_store.get(
#             "brands",
#             [],
#         ),
#         categories=filter_store.get(
#             "categories",
#             [],
#         ),
#         suppliers=filter_store.get(
#             "suppliers",
#             [],
#         ),
#         cv_ranks=filter_store.get(
#             "cv_ranks",
#             [],
#         ),
#         median_deviation_limit=None,

#         # Период уже применён в SQL.
#         date_range=None,
#     )


# # ---------------------------------------------------------------------
# # Регистрация callbacks фильтров
# # ---------------------------------------------------------------------


# def register_filter_callbacks(
#     app,
# ):
#     """
#     Регистрирует callbacks фильтров.
#     """

#     # -----------------------------------------------------------------
#     # Быстрые периоды
#     # -----------------------------------------------------------------

#     @app.callback(
#         Output(
#             DATE_FILTER_ID,
#             "value",
#         ),
#         Input(
#             DATE_PRESET_ID,
#             "value",
#         ),
#         prevent_initial_call=True,
#     )
#     def apply_date_preset(
#         preset,
#     ):
#         """
#         Применяет выбранный
#         быстрый период.
#         """

#         if not preset:
#             return no_update

#         return _build_preset_date_range(
#             preset
#         )

#     # -----------------------------------------------------------------
#     # Загрузка данных
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
#         Создаёт сигнал загрузки данных.

#         Кэш здесь не очищается.
#         Данные запрашиваются заново
#         при выполнении callbacks.
#         """

#         now = datetime.now()

#         return (
#             {
#                 "version": (
#                     now.isoformat()
#                 ),
#                 "refresh_clicks": (
#                     int(
#                         refresh_clicks
#                         or 0
#                     )
#                 ),
#             },

#             now.strftime(
#                 "%d.%m.%Y %H:%M"
#             ),
#         )

#     # -----------------------------------------------------------------
#     # Обновление зависимых options
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
#             SUPPLIER_FILTER_ID,
#             "data",
#         ),
#         Input(
#             DATA_STORE_ID,
#             "data",
#         ),
#         Input(
#             DATE_FILTER_ID,
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
#         prevent_initial_call=False,
#     )
#     def update_smart_filter_options(
#         data_signal,
#         date_range,
#         selected_brands,
#         selected_categories,
#     ):
#         """
#         Обновляет списки брендов,
#         категорий и поставщиков.

#         Списки учитывают выбранный
#         период УПД.
#         """

#         if not data_signal:
#             return [], [], []

#         date_from, date_to = (
#             normalise_date_range(
#                 date_range
#             )
#         )

#         analysis_df = (
#             get_price_analysis_data(
#                 date_from=date_from,
#                 date_to=date_to,
#             )
#             .copy()
#         )

#         history_df = (
#             get_price_history_data()
#             .copy()
#         )

#         history_df = filter_history_data(
#             history_df,
#             date_range=date_range,
#         )

#         if analysis_df.empty:
#             return [], [], []

#         # -------------------------------------------------------------
#         # Все бренды за выбранный период
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
#         # Поставщики выбранных брендов
#         # и категорий
#         # -------------------------------------------------------------

#         category_filtered_df = (
#             _filter_analysis_for_options(
#                 brand_filtered_df,
#                 categories=(
#                     clean_categories
#                 ),
#             )
#         )

#         supplier_options = (
#             _build_smart_supplier_options(
#                 category_filtered_df,
#                 history_df,
#             )
#         )

#         return (
#             brand_options,
#             category_options,
#             supplier_options,
#         )

#     # -----------------------------------------------------------------
#     # Очистка недоступных категорий
#     # -----------------------------------------------------------------

#     @app.callback(
#         Output(
#             CATEGORY_FILTER_ID,
#             "value",
#             allow_duplicate=True,
#         ),
#         Input(
#             CATEGORY_FILTER_ID,
#             "data",
#         ),
#         State(
#             CATEGORY_FILTER_ID,
#             "value",
#         ),
#         prevent_initial_call=True,
#     )
#     def clean_category_values(
#         category_options,
#         selected_categories,
#     ):
#         """
#         Удаляет категории,
#         которых больше нет в options.
#         """

#         current_values = (
#             _clean_values(
#                 selected_categories
#             )
#         )

#         clean_values = (
#             _keep_available_values(
#                 current_values,
#                 category_options,
#             )
#         )

#         if clean_values == current_values:
#             return no_update

#         return clean_values

#     # -----------------------------------------------------------------
#     # Очистка недоступных поставщиков
#     # -----------------------------------------------------------------

#     @app.callback(
#         Output(
#             SUPPLIER_FILTER_ID,
#             "value",
#             allow_duplicate=True,
#         ),
#         Input(
#             SUPPLIER_FILTER_ID,
#             "data",
#         ),
#         State(
#             SUPPLIER_FILTER_ID,
#             "value",
#         ),
#         prevent_initial_call=True,
#     )
#     def clean_supplier_values(
#         supplier_options,
#         selected_suppliers,
#     ):
#         """
#         Удаляет поставщиков,
#         которых больше нет в options.
#         """

#         current_values = (
#             _clean_values(
#                 selected_suppliers
#             )
#         )

#         clean_values = (
#             _keep_available_values(
#                 current_values,
#                 supplier_options,
#             )
#         )

#         if clean_values == current_values:
#             return no_update

#         return clean_values

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
#             DATE_FILTER_ID,
#             "value",
#             allow_duplicate=True,
#         ),
#         Output(
#             DATE_PRESET_ID,
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
#         Сбрасывает все фильтры.

#         Период возвращается к значению:
#         с начала года по сегодня.
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
#             get_default_date_range(),
#             "ytd",
#         )



# gear/app/costs_control/filters.py
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

import dash_mantine_components as dmc
import pandas as pd
from dash import (
    Input,
    Output,
    State,
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
    get_price_analysis_data,
    get_price_history_data,
    get_min_upd_date,
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
# Локальные ID
# ---------------------------------------------------------------------


DATE_PRESET_ID = (
    "costs-control-date-preset"
)


# ---------------------------------------------------------------------
# Даты
# ---------------------------------------------------------------------


# def get_default_date_range() -> list[str]:
#     """
#     Возвращает период по умолчанию:

#     с начала текущего года по сегодня.
#     """

#     today = date.today()
#     year_start = date(
#         year=today.year,
#         month=1,
#         day=1,
#     )

#     return [
#         year_start.isoformat(),
#         today.isoformat(),
#     ]

def get_default_date_range() -> list[str]:
    """
    Возвращает период по умолчанию:

    от первой даты УПД
    до сегодняшнего дня.
    """

    today = date.today()

    return [
        get_min_upd_date().isoformat(),
        today.isoformat(),
    ]






def normalise_date_range(
    date_range,
) -> tuple[str | None, str | None]:
    """
    Приводит значение DatePickerInput
    к паре строк:

    date_from, date_to

    Формат:

    YYYY-MM-DD
    """

    if not date_range:
        return None, None

    if not isinstance(
        date_range,
        (list, tuple),
    ):
        return None, None

    if len(date_range) < 2:
        return None, None

    date_from = date_range[0]
    date_to = date_range[1]

    if not date_from or not date_to:
        return None, None

    date_from = str(date_from)[:10]
    date_to = str(date_to)[:10]

    if date_from > date_to:
        date_from, date_to = (
            date_to,
            date_from,
        )

    return date_from, date_to


def _get_quarter_start(
    current_date: date,
) -> date:
    """
    Возвращает первый день квартала.
    """

    quarter_month = (
        ((current_date.month - 1) // 3)
        * 3
        + 1
    )

    return date(
        year=current_date.year,
        month=quarter_month,
        day=1,
    )


def _build_preset_date_range(
    preset: str | None,
) -> list[str]:
    """
    Формирует диапазон дат
    для выбранного пресета.
    """

    today = date.today()

    if preset == "all":
        return get_default_date_range()

    if preset == "last_30_days":
        date_from = (
            today
            - timedelta(days=29)
        )

    elif preset == "current_month":
        date_from = date(
            year=today.year,
            month=today.month,
            day=1,
        )

    elif preset == "current_quarter":
        date_from = _get_quarter_start(
            today
        )

    elif preset == "ytd":
        date_from = date(
            year=today.year,
            month=1,
            day=1,
        )

    else:
        return get_default_date_range()

    return [
        date_from.isoformat(),
        today.isoformat(),
    ]


# ---------------------------------------------------------------------
# Нормализация
# ---------------------------------------------------------------------


def normalise_nm_id(
    value: Any,
) -> str:
    """
    Приводит NM ID к строке
    без окончания .0.
    """

    if value is None:
        return ""

    text = str(value).strip()

    if text.endswith(".0"):
        text = text[:-2]

    return text


def normalise_list(
    value,
) -> list:
    """
    Приводит значение MultiSelect
    к обычному списку.
    """

    if value is None:
        return []

    if isinstance(
        value,
        (str, int, float),
    ):
        return [value]

    return list(value)


def _clean_values(
    values,
) -> list[str]:
    """
    Очищает список выбранных значений.
    """

    return [
        str(value).strip()
        for value in normalise_list(
            values
        )
        if (
            value is not None
            and str(value).strip()
        )
    ]


# ---------------------------------------------------------------------
# Поиск колонок
# ---------------------------------------------------------------------


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


def _find_history_date_column(
    df: pd.DataFrame,
) -> str | None:
    """
    Находит колонку даты УПД
    в таблице истории.
    """

    for column in (
        "Дата УПД",
        "date",
        "Дата",
        "upd_date",
        "document_date",
    ):
        if column in df.columns:
            return column

    return None


# ---------------------------------------------------------------------
# Визуальный контейнер фильтра
# ---------------------------------------------------------------------


def _filter_field(
    *,
    icon: str,
    title: str,
    subtitle: str,
    component,
    style: dict | None = None,
):
    """
    Единый компактный контейнер фильтра.
    """

    return html.Div(
        style={
            "minWidth": 0,
            "height": "100%",
            "padding": "10px 11px",
            "backgroundColor": "#FFFFFF",
            "border": (
                "1px solid "
                + COLORS.get(
                    "border",
                    "#D9DEE2",
                )
            ),
            **(style or {}),
        },
        children=[
            html.Div(
                style={
                    "display": "flex",
                    "alignItems": "flex-start",
                    "gap": "7px",
                    "marginBottom": "8px",
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
                                title=title,
                                style={
                                    "fontSize": "12px",
                                    "fontWeight": 700,
                                    "lineHeight": "16px",
                                    "color": COLORS.get(
                                        "text",
                                        "#111827",
                                    ),
                                    "whiteSpace": "nowrap",
                                    "overflow": "hidden",
                                    "textOverflow": "ellipsis",
                                },
                            ),

                            html.Div(
                                subtitle,
                                title=subtitle,
                                style={
                                    "marginTop": "1px",
                                    "fontSize": "9px",
                                    "lineHeight": "13px",
                                    "color": COLORS.get(
                                        "muted",
                                        "#6B7280",
                                    ),
                                    "whiteSpace": "nowrap",
                                    "overflow": "hidden",
                                    "textOverflow": "ellipsis",
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
# Фильтр периода
# ---------------------------------------------------------------------


def _build_date_filter():
    """
    Строит DatePicker и быстрые пресеты.
    """

    return _filter_field(
        icon="solar:calendar-date-linear",
        title="Период УПД",
        subtitle=(
            "Показатели рассчитываются "
            "за выбранный период"
        ),
        style={
            "flex": "1.65 1 350px",
        },
        component=dmc.Stack(
            gap=6,
            children=[
                dmc.DatePickerInput(
                    id=DATE_FILTER_ID,
                    type="range",
                    value=get_default_date_range(),
                    valueFormat="DD.MM.YYYY",
                    placeholder="Весь период",
                    clearable=False,
                    allowSingleDateInRange=False,
                    firstDayOfWeek=1,
                    radius=0,
                    size="xs",
                    w="100%",
                    leftSection=DashIconify(
                        icon=(
                            "solar:"
                            "calendar-linear"
                        ),
                        width=15,
                        height=15,
                    ),
                    styles={
                        "input": {
                            "height": "32px",
                            "minHeight": "32px",
                            "fontSize": "11px",
                            "fontWeight": 500,
                            "borderColor": (
                                COLORS.get(
                                    "border",
                                    "#D9DEE2",
                                )
                            ),
                            "backgroundColor": "#FFFFFF",
                        },
                    },
                ),

                dmc.SegmentedControl(
                    id=DATE_PRESET_ID,
                    value="all",
                    data=[
                        {
                            "label": "Весь",
                            "value": "all",
                        },
                        {
                            "label": "30 дней",
                            "value": "last_30_days",
                        },
                        {
                            "label": "Месяц",
                            "value": "current_month",
                        },
                        {
                            "label": "Квартал",
                            "value": "current_quarter",
                        },
                        {
                            "label": "С начала года",
                            "value": "ytd",
                        },
                    ],
                    radius=0,
                    size="xs",
                    fullWidth=True,
                    styles={
                        "root": {
                            "minHeight": "30px",
                        },
                        "label": {
                            "fontSize": "8.5px",
                            "paddingLeft": "4px",
                            "paddingRight": "4px",
                            "whiteSpace": "nowrap",
                        },
                    },
                ),
            ],
        ),
    )


# ---------------------------------------------------------------------
# Layout панели фильтров
# ---------------------------------------------------------------------


def build_filter_panel():
    """
    Панель фильтров анализа.

    На широком экране фильтры располагаются
    в одну строку. При недостатке ширины
    они аккуратно переносятся ниже.
    """

    common_multiselect_styles = {
        "input": {
            "minHeight": "32px",
            "fontSize": "11px",
        },
        "pill": {
            "fontSize": "9px",
        },
    }

    regular_filter_style = {
        "flex": "1 1 185px",
    }

    return html.Div(
        style=PANEL_STYLE,
        children=[
            dmc.Group(
                justify="space-between",
                align="center",
                mb=12,
                children=[
                    section_header(
                        "Фильтры анализа",
                        (
                            "Показатели, графики "
                            "и таблицы автоматически "
                            "пересчитываются"
                        ),
                    ),

                    action_button(
                        component_id=(
                            RESET_FILTERS_BTN_ID
                        ),
                        label="Сбросить",
                        icon="solar:restart-linear",
                        color="gray",
                    ),
                ],
            ),

            html.Div(
                style={
                    "display": "flex",
                    "flexWrap": "wrap",
                    "alignItems": "stretch",
                    "gap": "10px",
                    "width": "100%",
                },
                children=[
                    _build_date_filter(),

                    _filter_field(
                        icon=(
                            "solar:"
                            "calculator-"
                            "minimalistic-linear"
                        ),
                        title="Тип себестоимости",
                        subtitle=(
                            "Бухгалтерская или "
                            "управленческая"
                        ),
                        style={
                            "flex": "1.2 1 255px",
                        },
                        component=dmc.SegmentedControl(
                            id=COST_TYPE_FILTER_ID,
                            value=DEFAULT_COST_TYPE,
                            data=COST_TYPES,
                            radius=0,
                            size="xs",
                            fullWidth=True,
                            styles={
                                "root": {
                                    "minHeight": "32px",
                                },
                                "label": {
                                    "fontSize": "10px",
                                    "whiteSpace": "nowrap",
                                },
                            },
                        ),
                    ),

                    _filter_field(
                        icon="solar:tag-linear",
                        title="Бренд",
                        subtitle="Можно выбрать несколько",
                        style=regular_filter_style,
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
                            styles=common_multiselect_styles,
                        ),
                    ),

                    _filter_field(
                        icon=(
                            "solar:"
                            "folder-with-files-linear"
                        ),
                        title="Категория",
                        subtitle="Зависит от бренда",
                        style=regular_filter_style,
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
                            styles=common_multiselect_styles,
                        ),
                    ),

                    _filter_field(
                        icon=(
                            "solar:"
                            "buildings-2-linear"
                        ),
                        title="Поставщик",
                        subtitle="Зависит от фильтров",
                        style=regular_filter_style,
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
                            styles=common_multiselect_styles,
                        ),
                    ),

                    _filter_field(
                        icon=(
                            "solar:"
                            "chart-square-linear"
                        ),
                        title="Ранг CV",
                        subtitle="Стабильность цены",
                        style=regular_filter_style,
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
                            styles=common_multiselect_styles,
                        ),
                    ),
                ],
            ),

            html.Div(
                style={
                    "display": "none",
                },
                children=[
                    dmc.NumberInput(
                        id=(
                            MEDIAN_DEVIATION_FILTER_ID
                        ),
                        value=(
                            DEFAULT_MEDIAN_DEVIATION_LIMIT
                        ),
                    ),
                ],
            ),

            html.Div(
                style={
                    "display": "flex",
                    "alignItems": "center",
                    "gap": "7px",
                    "marginTop": "10px",
                    "padding": "7px 10px",
                    "backgroundColor": (
                        COLORS.get(
                            "very_light_green",
                            "#F3F8F6",
                        )
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
                        icon=(
                            "solar:"
                            "info-circle-linear"
                        ),
                        width=14,
                        height=14,
                        color=COLORS.get(
                            "green",
                            "#2F6656",
                        ),
                    ),

                    html.Span(
                        (
                            "Для поиска конкретного "
                            "товара используйте "
                            "встроенные фильтры "
                            "таблицы на вкладке "
                            "«Товары»."
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
    Фильтрует агрегированный анализ
    для зависимых справочников.
    """

    if analysis_df.empty:
        return analysis_df.copy()

    result = analysis_df.copy()

    selected_brands = _clean_values(
        brands
    )

    selected_categories = _clean_values(
        categories
    )

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

    return result.reset_index(
        drop=True
    )


def _build_smart_supplier_options(
    analysis_df: pd.DataFrame,
    history_df: pd.DataFrame,
) -> list:
    """
    Возвращает поставщиков только по NM ID,
    которые остались после фильтра бренда,
    категории и периода.
    """

    if (
        analysis_df.empty
        or history_df.empty
    ):
        return []

    analysis_nm_column = (
        _find_nm_id_column(
            analysis_df
        )
    )

    history_nm_column = (
        _find_nm_id_column(
            history_df
        )
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
            analysis_df[
                analysis_nm_column
            ]
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
            history_ids.isin(
                allowed_ids
            )
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
    Получает множество value
    из options Mantine.
    """

    values: set[str] = set()

    for option in options or []:
        if isinstance(
            option,
            dict,
        ):
            value = option.get(
                "value"
            )
        else:
            value = option

        if value is not None:
            values.add(
                str(value)
            )

    return values


def _keep_available_values(
    selected_values,
    options: list,
) -> list[str]:
    """
    Оставляет только значения,
    присутствующие в новых options.
    """

    available_values = (
        _option_values(
            options
        )
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

    Колонка «Поставщики» может содержать
    несколько поставщиков в одной строке.
    """

    selected_suppliers = (
        _clean_values(
            suppliers
        )
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
    Применяет фильтры к уже рассчитанной
    агрегированной таблице.

    Важно:
    период здесь повторно не применяется.

    Период должен передаваться непосредственно
    в get_price_analysis_data(), чтобы SQL
    сначала отобрал УПД, а затем рассчитал
    MIN, MAX, MEDIAN, AVG и CV.
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

        # Поставщики обрабатываются отдельно.
        suppliers=None,

        # Удалённые фильтры.
        nm_ids=None,
        cv_min=None,
        only_changed=False,
        only_anomalies=False,

        cv_ranks=normalise_list(
            cv_ranks
        ),

        # Дата уже применена в SQL.
        date_range=None,

        # Порог скрыт и данные не фильтрует.
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
    Фильтрует историю УПД:

    - по NM ID;
    - по поставщикам;
    - по выбранному периоду.
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

        nm_id_column = (
            _find_nm_id_column(
                result
            )
        )

        if (
            not allowed_ids
            or not nm_id_column
        ):
            return (
                result
                .iloc[0:0]
                .copy()
            )

        history_ids = (
            result[nm_id_column]
            .astype(str)
            .map(normalise_nm_id)
        )

        result = result.loc[
            history_ids.isin(
                allowed_ids
            )
        ].copy()

    # -------------------------------------------------------------
    # Поставщики
    # -------------------------------------------------------------

    selected_suppliers = (
        _clean_values(
            suppliers
        )
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

    # -------------------------------------------------------------
    # Период УПД
    # -------------------------------------------------------------

    date_from, date_to = (
        normalise_date_range(
            date_range
        )
    )

    date_column = (
        _find_history_date_column(
            result
        )
    )

    if (
        date_column
        and (
            date_from
            or date_to
        )
    ):
        result[date_column] = (
            pd.to_datetime(
                result[date_column],
                errors="coerce",
            )
        )

        if date_from:
            result = result.loc[
                result[date_column]
                >= pd.Timestamp(date_from)
            ].copy()

        if date_to:
            result = result.loc[
                result[date_column]
                < (
                    pd.Timestamp(date_to)
                    + pd.Timedelta(days=1)
                )
            ].copy()

    return result.reset_index(
        drop=True
    )


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
    Создаёт Store с параметрами
    активных фильтров.
    """

    date_from, date_to = (
        normalise_date_range(
            date_range
        )
    )

    normalised_range = None

    if date_from and date_to:
        normalised_range = [
            date_from,
            date_to,
        ]

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

        "median_deviation_limit": None,

        "date_range": normalised_range,
    }


def get_filtered_analysis_from_store(
    filter_store: dict | None,
) -> pd.DataFrame:
    """
    Повторно получает агрегированный
    анализ на сервере.

    Используется при формировании
    таблиц, Excel и CSV.
    """

    if not filter_store:
        date_range = (
            get_default_date_range()
        )
    else:
        date_range = (
            filter_store.get(
                "date_range"
            )
            or get_default_date_range()
        )

    date_from, date_to = (
        normalise_date_range(
            date_range
        )
    )

    analysis_df = (
        get_price_analysis_data(
            date_from=date_from,
            date_to=date_to,
        )
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

        # Период уже применён в SQL.
        date_range=None,
    )


# ---------------------------------------------------------------------
# Регистрация callbacks фильтров
# ---------------------------------------------------------------------


def register_filter_callbacks(
    app,
):
    """
    Регистрирует callbacks фильтров.
    """

    # -----------------------------------------------------------------
    # Быстрые периоды
    # -----------------------------------------------------------------

    @app.callback(
        Output(
            DATE_FILTER_ID,
            "value",
        ),
        Input(
            DATE_PRESET_ID,
            "value",
        ),
        prevent_initial_call=True,
    )
    def apply_date_preset(
        preset,
    ):
        """
        Применяет выбранный
        быстрый период.
        """

        if not preset:
            return no_update

        return _build_preset_date_range(
            preset
        )

    # -----------------------------------------------------------------
    # Загрузка данных
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
    def load_filter_data(
        refresh_clicks,
    ):
        """
        Создаёт сигнал загрузки данных.

        Кэш здесь не очищается.
        Данные запрашиваются заново
        при выполнении callbacks.
        """

        now = datetime.now()

        return (
            {
                "version": (
                    now.isoformat()
                ),
                "refresh_clicks": (
                    int(
                        refresh_clicks
                        or 0
                    )
                ),
            },

            now.strftime(
                "%d.%m.%Y %H:%M"
            ),
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
            DATE_FILTER_ID,
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
        prevent_initial_call=False,
    )
    def update_smart_filter_options(
        data_signal,
        date_range,
        selected_brands,
        selected_categories,
    ):
        """
        Обновляет списки брендов,
        категорий и поставщиков.

        Списки учитывают выбранный
        период УПД.
        """

        if not data_signal:
            return [], [], []

        date_from, date_to = (
            normalise_date_range(
                date_range
            )
        )

        analysis_df = (
            get_price_analysis_data(
                date_from=date_from,
                date_to=date_to,
            )
            .copy()
        )

        history_df = (
            get_price_history_data()
            .copy()
        )

        history_df = filter_history_data(
            history_df,
            date_range=date_range,
        )

        if analysis_df.empty:
            return [], [], []

        # -------------------------------------------------------------
        # Все бренды за выбранный период
        # -------------------------------------------------------------

        brand_options = (
            build_filter_options(
                analysis_df,
                "Бренд",
            )
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

        category_options = (
            build_filter_options(
                brand_filtered_df,
                "Категория",
            )
        )

        clean_categories = (
            _keep_available_values(
                selected_categories,
                category_options,
            )
        )

        # -------------------------------------------------------------
        # Поставщики выбранных брендов
        # и категорий
        # -------------------------------------------------------------

        category_filtered_df = (
            _filter_analysis_for_options(
                brand_filtered_df,
                categories=(
                    clean_categories
                ),
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
        Удаляет категории,
        которых больше нет в options.
        """

        current_values = (
            _clean_values(
                selected_categories
            )
        )

        clean_values = (
            _keep_available_values(
                current_values,
                category_options,
            )
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
        Удаляет поставщиков,
        которых больше нет в options.
        """

        current_values = (
            _clean_values(
                selected_suppliers
            )
        )

        clean_values = (
            _keep_available_values(
                current_values,
                supplier_options,
            )
        )

        if clean_values == current_values:
            return no_update

        return clean_values

    # -----------------------------------------------------------------
    # Сброс фильтров
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
        Output(
            DATE_FILTER_ID,
            "value",
            allow_duplicate=True,
        ),
        Output(
            DATE_PRESET_ID,
            "value",
        ),
        Input(
            RESET_FILTERS_BTN_ID,
            "n_clicks",
        ),
        prevent_initial_call=True,
    )
    def reset_filters(
        n_clicks,
    ):
        """
        Сбрасывает все фильтры.

        Период возвращается ко всему
        доступному периоду УПД.
        """

        if not n_clicks:
            return (
                no_update,
                no_update,
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
            get_default_date_range(),
            "all",
        )