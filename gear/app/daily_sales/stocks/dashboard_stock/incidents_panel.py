# # gear/app/daily_sales/stocks/dashboard_stock/incidents_panel.py

# """Панель происшествий на основной странице dashboard."""

# from __future__ import annotations

# import pandas as pd
# import dash_mantine_components as dmc
# from dash_iconify import DashIconify

# from dash import html

# from ..dashboard_data import (
#     get_warehouse_incident_snapshot,
# )

# from ..data import get_warehouse_incident_stock_items

# from .ids import (
#     STOCK_INCIDENT_EXCEL_BTN_ID,
#     STOCK_INCIDENT_EXCEL_DOWNLOAD_ID,
#     STOCK_INCIDENT_PDF_BTN_ID,
#     STOCK_INCIDENT_PDF_DOWNLOAD_ID,
# )

# from .warehouse_incidents import (
#     WAREHOUSE_INCIDENTS,
# )

# from .helpers import (
#     fmt,
#     fmt_money,
# )


# # =============================================================================
# # ЦВЕТА
# # =============================================================================

# TEXT = "#18352F"
# MUTED = "#60746D"

# BORDER = "#D6DFDB"

# INCIDENT_BORDER = "#E2CACA"
# INCIDENT_ACCENT = "#A43E3E"
# INCIDENT_BG = "#FFFDFD"

# EMPTY_BG = "#F7F9F8"
# EMPTY_BORDER = "#DCE4E0"

# SUMMARY_BG = "#F7F9F8"
# SUMMARY_ACCENT = "#315E52"
# SUMMARY_VALUE = "#18352F"


# # =============================================================================
# # ИНФОРМАЦИОННЫЙ БЛОК — ФИЗИЧЕСКОГО ОСТАТКА НЕТ
# # =============================================================================


# def _empty_stock_banner(
#     snapshot_label: str,
# ):
#     """
#     Показывается вместо KPI, если на дату снимка
#     физический остаток на складе равен нулю.
#     """

#     return dmc.Paper(
#         radius=0,
#         p="md",
#         mt="lg",

#         style={
#             "background": EMPTY_BG,
#             "border": f"1px solid {EMPTY_BORDER}",
#         },

#         children=[

#             dmc.Group(
#                 gap=10,
#                 align="flex-start",

#                 children=[

#                     html.Div(
#                         style={
#                             "width": "4px",
#                             "minWidth": "4px",
#                             "height": "40px",
#                             "background": "#94A39D",
#                         },
#                     ),

#                     html.Div(
#                         style={
#                             "minWidth": 0,
#                         },

#                         children=[

#                             dmc.Text(
#                                 "Физический товарный остаток отсутствовал",
#                                 fw=600,
#                                 size="sm",
#                                 c=TEXT,
#                             ),

#                             dmc.Text(
#                                 (
#                                     f"По данным на {snapshot_label} "
#                                     "товар физически на складе отсутствовал. "
#                                     "Оценка стоимости товарного остатка "
#                                     "для данного происшествия не производится."
#                                 ),
#                                 size="xs",
#                                 c=MUTED,
#                                 mt=3,
#                                 style={
#                                     "lineHeight": 1.5,
#                                 },
#                             ),
#                         ],
#                     ),
#                 ],
#             ),
#         ],
#     )


# # =============================================================================
# # KPI
# # =============================================================================


# def _metric(
#     label: str,
#     value: str,
#     *,
#     value_color: str = TEXT,
#     subvalue: str | None = None,
# ):
#     """
#     Унифицированный KPI.

#     subvalue используется, например, для:

#         15 шт
#         4 NM ID
#     """

#     children = [

#         dmc.Text(
#             label,
#             size="xs",
#             c="dimmed",
#         ),

#         dmc.Text(
#             value,
#             fw=700,
#             size="lg",
#             c=value_color,
#             mt=1,
#         ),
#     ]

#     if subvalue:
#         children.append(
#             dmc.Text(
#                 subvalue,
#                 size="xs",
#                 c="dimmed",
#                 mt=1,
#             )
#         )

#     return html.Div(
#         children=children,
#     )


# # =============================================================================
# # SUMMARY ПО ВСЕМ ПРОИСШЕСТВИЯМ
# # =============================================================================


# def _build_incidents_summary(
#     prepared_events: list[dict],
# ):
#     """
#     Общая оценка товарного остатка,
#     потенциально затронутого происшествиями.

#     Для каждого события используется исторический снимок
#     на конец календарного дня, предшествующего происшествию.

#     В расчёт входит только физический остаток.

#     Товары в пути не учитываются.
#     """

#     total_events = len(
#         prepared_events
#     )

#     total_on_hand = 0.0

#     total_accounting_cost = 0.0
#     total_management_cost = 0.0

#     warehouses_with_stock = set()

#     no_accounting_cost_qty = 0
#     no_management_cost_qty = 0

#     no_snapshot_count = 0

#     # =========================================================================
#     # Собираем итог
#     # =========================================================================

#     for item in prepared_events:

#         snapshot = (
#             item.get("snapshot")
#             or {}
#         )

#         effective_date = snapshot.get(
#             "effective_date"
#         )

#         if not effective_date:
#             no_snapshot_count += 1
#             continue

#         on_hand = float(
#             snapshot.get(
#                 "on_hand",
#                 0,
#             )
#             or 0
#         )

#         accounting_cost = float(
#             snapshot.get(
#                 "accounting_cost",
#                 0,
#             )
#             or 0
#         )

#         management_cost = float(
#             snapshot.get(
#                 "management_cost",
#                 0,
#             )
#             or 0
#         )

#         total_on_hand += on_hand

#         total_accounting_cost += (
#             accounting_cost
#         )

#         total_management_cost += (
#             management_cost
#         )

#         no_accounting_cost_qty += int(
#             snapshot.get(
#                 "no_accounting_cost_qty",
#                 0,
#             )
#             or 0
#         )

#         no_management_cost_qty += int(
#             snapshot.get(
#                 "no_management_cost_qty",
#                 0,
#             )
#             or 0
#         )

#         if on_hand > 0:
#             warehouses_with_stock.add(
#                 item.get(
#                     "warehouse_name",
#                     "",
#                 )
#             )

#     warehouse_count = len(
#         warehouses_with_stock
#     )

#     # =========================================================================
#     # Дополнительное примечание
#     # =========================================================================

#     footnote_parts = [
#         (
#             "Итог рассчитан по физическому товарному остатку "
#             "на конец дня, предшествующего каждому происшествию. "
#             "Товары в пути не включены."
#         )
#     ]

#     if (
#         no_accounting_cost_qty > 0
#         or no_management_cost_qty > 0
#     ):
#         footnote_parts.append(
#             (
#                 " Позиции без определённой себестоимости "
#                 "не включены в соответствующую стоимостную оценку."
#             )
#         )

#     if no_snapshot_count > 0:
#         footnote_parts.append(
#             (
#                 f" Для {fmt(no_snapshot_count)} "
#                 f"{_event_word(no_snapshot_count)} "
#                 "исторический снимок остатков не найден."
#             )
#         )

#     # =========================================================================
#     # Карточка summary
#     # =========================================================================

#     return dmc.Paper(
#         radius=0,
#         p="md",
#         mb="md",

#         style={
#             "background": SUMMARY_BG,
#             "border": f"1px solid {BORDER}",
#             "borderLeft": (
#                 f"4px solid {SUMMARY_ACCENT}"
#             ),
#         },

#         children=[

#             # =================================================================
#             # HEADER
#             # =================================================================

#             dmc.Group(
#                 justify="space-between",
#                 align="center",
#                 gap="md",
#                 mb="md",

#                 children=[

#                     html.Div(
#                         style={
#                             "minWidth": 0,
#                         },

#                         children=[

#                             dmc.Text(
#                                 "Общая оценка товарных потерь",
#                                 fw=700,
#                                 size="sm",
#                                 c=TEXT,
#                             ),

#                             dmc.Text(
#                                 (
#                                     "Сводная оценка физического остатка "
#                                     "по зарегистрированным происшествиям"
#                                 ),
#                                 size="xs",
#                                 c="dimmed",
#                                 mt=2,
#                             ),
#                         ],
#                     ),

#                     dmc.Badge(
#                         (
#                             f"{total_events} "
#                             f"{_event_word(total_events)}"
#                         ),
#                         color="gray",
#                         variant="light",
#                         radius=0,
#                     ),
#                 ],
#             ),

#             # =================================================================
#             # KPI
#             # =================================================================

#             dmc.SimpleGrid(
#                 cols={
#                     "base": 2,
#                     "sm": 2,
#                     "lg": 4,
#                 },

#                 spacing="lg",

#                 children=[

#                     # ---------------------------------------------------------
#                     # Склады
#                     # ---------------------------------------------------------

#                     _metric(
#                         "Складов с остатком",
#                         fmt(
#                             warehouse_count
#                         ),
#                     ),

#                     # ---------------------------------------------------------
#                     # Физический остаток
#                     # ---------------------------------------------------------

#                     _metric(
#                         "Физический остаток",
#                         (
#                             f"{fmt(
#                                 total_on_hand
#                             )} шт"
#                         ),
#                     ),

#                     # ---------------------------------------------------------
#                     # Бухгалтерская себестоимость
#                     # ---------------------------------------------------------

#                     _metric(
#                         "Бухгалтерская с/с",
#                         (
#                             f"{fmt_money(
#                                 total_accounting_cost
#                             )} ₽"
#                         ),
#                         value_color=SUMMARY_VALUE,
#                     ),

#                     # ---------------------------------------------------------
#                     # Управленческая себестоимость
#                     # ---------------------------------------------------------

#                     _metric(
#                         "Управленческая с/с",
#                         (
#                             f"{fmt_money(
#                                 total_management_cost
#                             )} ₽"
#                         ),
#                         value_color=SUMMARY_VALUE,
#                     ),
#                 ],
#             ),

#             # =================================================================
#             # FOOTNOTE
#             # =================================================================

#             dmc.Text(
#                 "".join(
#                     footnote_parts
#                 ),
#                 size="xs",
#                 c="dimmed",
#                 mt="md",
#                 style={
#                     "lineHeight": 1.45,
#                 },
#             ),
#         ],
#     )


# # =============================================================================
# # КАРТОЧКА ПРОИСШЕСТВИЯ
# # =============================================================================


# def _incident_card(
#     warehouse_name: str,
#     incident: dict,
#     snapshot: dict | None = None,
# ):
#     """
#     Карточка одного происшествия.

#     incident["date"] — фактическая дата происшествия.

#     Для финансовой оценки используется исторический
#     снимок склада на конец ПРЕДЫДУЩЕГО календарного дня.

#     Например:

#         происшествие: 22.07.2026
#         снимок:       21.07.2026

#     В оценку включается только физический остаток quantity.

#     Товары в пути не учитываются.

#     snapshot можно передать извне, чтобы повторно
#     не обращаться к базе данных.
#     """

#     # =========================================================================
#     # Дата происшествия
#     # =========================================================================

#     incident_date = pd.to_datetime(
#         incident["date"]
#     )

#     event_date = incident_date.strftime(
#         "%d.%m.%Y"
#     )

#     # =========================================================================
#     # Требуемая дата снимка
#     # =========================================================================

#     requested_snapshot_date = (
#         incident_date
#         - pd.Timedelta(days=1)
#     )

#     # =========================================================================
#     # Исторический снимок
#     #
#     # Если snapshot уже был получен при построении основной панели,
#     # повторный запрос к БД не выполняем.
#     # =========================================================================

#     if snapshot is None:

#         snapshot = (
#             get_warehouse_incident_snapshot(
#                 warehouse_name=warehouse_name,

#                 incident_date=(
#                     requested_snapshot_date.strftime(
#                         "%Y-%m-%d"
#                     )
#                 ),
#             )
#         )

#     snapshot = snapshot or {}

#     # =========================================================================
#     # Фактическая дата снимка
#     # =========================================================================

#     effective_date = snapshot.get(
#         "effective_date"
#     )

#     snapshot_label = (
#         pd.to_datetime(
#             effective_date
#         ).strftime(
#             "%d.%m.%Y"
#         )
#         if effective_date
#         else "нет данных"
#     )

#     # =========================================================================
#     # Основные показатели
#     # =========================================================================

#     on_hand = float(
#         snapshot.get(
#             "on_hand",
#             0,
#         )
#         or 0
#     )

#     has_physical_stock = (
#         on_hand > 0
#     )

#     # =========================================================================
#     # Без бухгалтерской себестоимости
#     # =========================================================================

#     no_accounting_cost_qty = int(
#         snapshot.get(
#             "no_accounting_cost_qty",
#             0,
#         )
#         or 0
#     )

#     no_accounting_cost_nm_count = int(
#         snapshot.get(
#             "no_accounting_cost_nm_count",
#             0,
#         )
#         or 0
#     )

#     # =========================================================================
#     # Без управленческой себестоимости
#     # =========================================================================

#     no_management_cost_qty = int(
#         snapshot.get(
#             "no_management_cost_qty",
#             0,
#         )
#         or 0
#     )

#     no_management_cost_nm_count = int(
#         snapshot.get(
#             "no_management_cost_nm_count",
#             0,
#         )
#         or 0
#     )

#     # =========================================================================
#     # Нет данных вообще
#     # =========================================================================

#     no_snapshot_data = (
#         not effective_date
#     )

#     # =========================================================================
#     # KPI / информационный блок
#     # =========================================================================

#     if no_snapshot_data:

#         content_block = dmc.Paper(
#             radius=0,
#             p="md",
#             mt="lg",

#             style={
#                 "background": "#FFF8F8",
#                 "border": (
#                     f"1px solid {INCIDENT_BORDER}"
#                 ),
#             },

#             children=[

#                 dmc.Text(
#                     "Нет данных об остатках",
#                     fw=600,
#                     size="sm",
#                     c=INCIDENT_ACCENT,
#                 ),

#                 dmc.Text(
#                     (
#                         "Для даты, предшествующей происшествию, "
#                         "не найден снимок товарных остатков. "
#                         "Финансовая оценка происшествия не рассчитана."
#                     ),
#                     size="xs",
#                     c=MUTED,
#                     mt=3,
#                     style={
#                         "lineHeight": 1.5,
#                     },
#                 ),
#             ],
#         )

#     elif not has_physical_stock:

#         content_block = (
#             _empty_stock_banner(
#                 snapshot_label=snapshot_label,
#             )
#         )

#     else:

#         content_block = dmc.SimpleGrid(
#             cols={
#                 "base": 2,
#                 "sm": 3,
#                 "lg": 6,
#             },

#             spacing="lg",

#             mt="lg",

#             children=[

#                 # -------------------------------------------------------------
#                 # Физический остаток
#                 # -------------------------------------------------------------

#                 _metric(
#                     "Физический остаток",
#                     (
#                         f"{fmt(
#                             snapshot.get(
#                                 'on_hand',
#                                 0,
#                             )
#                         )} шт"
#                     ),
#                 ),

#                 # -------------------------------------------------------------
#                 # Товаров
#                 # -------------------------------------------------------------

#                 _metric(
#                     "Товаров",
#                     (
#                         f"{fmt(
#                             snapshot.get(
#                                 'nm_count',
#                                 0,
#                             )
#                         )} NM ID"
#                     ),
#                 ),

#                 # -------------------------------------------------------------
#                 # Бухгалтерская себестоимость
#                 # -------------------------------------------------------------

#                 _metric(
#                     "Бухгалтерская с/с",
#                     (
#                         f"{fmt_money(
#                             snapshot.get(
#                                 'accounting_cost',
#                                 0,
#                             )
#                         )} ₽"
#                     ),
#                 ),

#                 # -------------------------------------------------------------
#                 # Без бухгалтерской себестоимости
#                 # -------------------------------------------------------------

#                 _metric(
#                     "Без бух. с/с",
#                     (
#                         f"{fmt(
#                             no_accounting_cost_qty
#                         )} шт"
#                     ),

#                     value_color=(
#                         INCIDENT_ACCENT
#                         if no_accounting_cost_qty > 0
#                         else TEXT
#                     ),

#                     subvalue=(
#                         (
#                             f"{fmt(
#                                 no_accounting_cost_nm_count
#                             )} NM ID"
#                         )
#                         if no_accounting_cost_qty > 0
#                         else None
#                     ),
#                 ),

#                 # -------------------------------------------------------------
#                 # Управленческая себестоимость
#                 # -------------------------------------------------------------

#                 _metric(
#                     "Управленческая с/с",
#                     (
#                         f"{fmt_money(
#                             snapshot.get(
#                                 'management_cost',
#                                 0,
#                             )
#                         )} ₽"
#                     ),
#                 ),

#                 # -------------------------------------------------------------
#                 # Без управленческой себестоимости
#                 # -------------------------------------------------------------

#                 _metric(
#                     "Без упр. с/с",
#                     (
#                         f"{fmt(
#                             no_management_cost_qty
#                         )} шт"
#                     ),

#                     value_color=(
#                         INCIDENT_ACCENT
#                         if no_management_cost_qty > 0
#                         else TEXT
#                     ),

#                     subvalue=(
#                         (
#                             f"{fmt(
#                                 no_management_cost_nm_count
#                             )} NM ID"
#                         )
#                         if no_management_cost_qty > 0
#                         else None
#                     ),
#                 ),
#             ],
#         )

#     # =========================================================================
#     # Методологическое примечание
#     #
#     # Показываем только тогда, когда физический остаток реально был.
#     # При нулевом остатке пояснение уже находится внутри отдельного баннера.
#     # =========================================================================

#     if has_physical_stock:

#         footnote_parts = [
#             (
#                 "Оценка рассчитана по товару, физически находившемуся "
#                 "на складе на конец дня, предшествующего происшествию. "
#                 "Позиции в пути в расчёт не включены."
#             )
#         ]

#         if (
#             no_accounting_cost_qty > 0
#             or no_management_cost_qty > 0
#         ):
#             footnote_parts.append(
#                 (
#                     " Позиции без определённой себестоимости "
#                     "не включены в соответствующую стоимостную оценку."
#                 )
#             )

#         footnote = dmc.Text(
#             "".join(
#                 footnote_parts
#             ),

#             size="xs",

#             c="dimmed",

#             mt="md",

#             style={
#                 "lineHeight": 1.45,
#             },
#         )

#     else:

#         footnote = None

#     # =========================================================================
#     # Карточка
#     # =========================================================================

#     return dmc.Paper(
#         radius=0,
#         p="lg",

#         style={
#             "border": (
#                 f"1px solid {INCIDENT_BORDER}"
#             ),

#             "borderLeft": (
#                 f"4px solid {INCIDENT_ACCENT}"
#             ),

#             "background": INCIDENT_BG,

#             "flexShrink": 0,
#         },

#         children=[

#             # =================================================================
#             # HEADER
#             # =================================================================

#             dmc.Group(
#                 justify="space-between",

#                 align="flex-start",

#                 gap="md",

#                 children=[

#                     # ---------------------------------------------------------
#                     # Название склада / событие
#                     # ---------------------------------------------------------

#                     html.Div(
#                         style={
#                             "minWidth": 0,
#                         },

#                         children=[

#                             dmc.Group(
#                                 gap=8,

#                                 align="center",

#                                 children=[

#                                     dmc.Text(
#                                         warehouse_name,

#                                         fw=700,

#                                         size="md",

#                                         c=TEXT,
#                                     ),

#                                     dmc.Badge(
#                                         incident.get(
#                                             "status",
#                                             "Происшествие",
#                                         ),

#                                         color="red",

#                                         variant="light",

#                                         radius=0,
#                                     ),
#                                 ],
#                             ),

#                             dmc.Text(
#                                 (
#                                     f"{incident.get(
#                                         'title',
#                                         'Происшествие',
#                                     )} · {event_date}"
#                                 ),

#                                 size="sm",

#                                 c=MUTED,

#                                 mt=2,
#                             ),
#                         ],
#                     ),

#                     # ---------------------------------------------------------
#                     # Дата остатков
#                     # ---------------------------------------------------------

#                     dmc.Text(
#                         (
#                             "Остатки на: "
#                             f"{snapshot_label}"
#                         ),

#                         size="xs",

#                         c="dimmed",

#                         style={
#                             "whiteSpace": "nowrap",
#                         },
#                     ),
#                 ],
#             ),

#             # =================================================================
#             # ОПИСАНИЕ
#             # =================================================================

#             dmc.Text(
#                 incident.get(
#                     "description",
#                     "",
#                 ),

#                 size="sm",

#                 c=TEXT,

#                 mt="md",

#                 style={
#                     "lineHeight": 1.5,
#                 },
#             ),

#             # =================================================================
#             # KPI ИЛИ БАННЕР
#             # =================================================================

#             content_block,

#             # =================================================================
#             # FOOTNOTE
#             # =================================================================

#             footnote,
#         ],
#     )


# # =============================================================================
# # ОСНОВНАЯ ПАНЕЛЬ
# # =============================================================================


# def build_incidents_panel():
#     """
#     Формирует блок происшествий на основной странице.

#     Особенности:

#     - события сортируются от новых к старым;
#     - snapshot каждого события загружается только один раз;
#     - сверху показывается общая оценка потерь;
#     - заголовок и общий итог остаются неподвижными;
#     - прокручиваются только карточки событий;
#     - при небольшом числе событий scroll не показывается;
#     - при большом числе событий dashboard не растягивается вниз.
#     """

#     # =========================================================================
#     # Собираем все события
#     #
#     # Здесь же сразу получаем snapshot, чтобы:
#     #
#     # 1. использовать его в общей summary;
#     # 2. передать его в карточку;
#     # 3. не выполнять второй одинаковый запрос к БД.
#     # =========================================================================

#     events = []

#     for warehouse_name, incidents in (
#         WAREHOUSE_INCIDENTS.items()
#     ):

#         for incident in incidents:

#             incident_date = pd.to_datetime(
#                 incident.get(
#                     "date",
#                     "",
#                 )
#             )

#             requested_snapshot_date = (
#                 incident_date
#                 - pd.Timedelta(days=1)
#             )

#             snapshot = (
#                 get_warehouse_incident_snapshot(
#                     warehouse_name=warehouse_name,

#                     incident_date=(
#                         requested_snapshot_date.strftime(
#                             "%Y-%m-%d"
#                         )
#                     ),
#                 )
#             )

#             events.append(
#                 {
#                     "date": incident.get(
#                         "date",
#                         "",
#                     ),

#                     "warehouse_name": (
#                         warehouse_name
#                     ),

#                     "incident": incident,

#                     "snapshot": (
#                         snapshot
#                         or {}
#                     ),
#                 }
#             )

#     # =========================================================================
#     # Нет происшествий
#     # =========================================================================

#     if not events:
#         return None

#     # =========================================================================
#     # Новые события сверху
#     # =========================================================================

#     events.sort(
#         key=lambda item: (
#             item.get(
#                 "date",
#                 "",
#             )
#         ),
#         reverse=True,
#     )

#     # =========================================================================
#     # Панель
#     # =========================================================================

#     return dmc.Paper(
#         radius=0,
#         p="lg",

#         style={
#             "border": (
#                 f"1px solid {BORDER}"
#             ),

#             "background": "#FFFFFF",
#         },

#         children=[

#             # =================================================================
#             # HEADER
#             # =================================================================

#             dmc.Group(
#                 justify="space-between",

#                 align="flex-end",

#                 gap="md",

#                 mb="md",

#                 children=[

#                     html.Div(
#                         children=[

#                             dmc.Text(
#                                 "Происшествия на складах",

#                                 fw=700,

#                                 size="md",

#                                 c=TEXT,
#                             ),

#                             dmc.Text(
#                                 (
#                                     "Зафиксированные события и оценка "
#                                     "товарного остатка на конец дня, "
#                                     "предшествующего происшествию."
#                                 ),

#                                 size="xs",

#                                 c="dimmed",

#                                 mt=2,
#                             ),
#                         ],
#                     ),

                    
#                 ],
#             ),

#             # =================================================================
#             # ОБЩАЯ ОЦЕНКА
#             # =================================================================

#             _build_incidents_summary(
#                 prepared_events=events,
#             ),

#             # =================================================================
#             # SCROLL
#             #
#             # Summary находится выше scroll,
#             # поэтому всегда остаётся на экране.
#             # =================================================================

#             html.Div(
#                 style={
#                     "maxHeight": "280px",

#                     "overflowY": "auto",

#                     "overflowX": "hidden",

#                     "paddingRight": "8px",

#                     "scrollbarGutter": "stable",

#                     "WebkitOverflowScrolling": "touch",
#                 },

#                 children=[

#                     dmc.Stack(
#                         gap="sm",

#                         children=[

#                             _incident_card(
#                                 warehouse_name=(
#                                     item[
#                                         "warehouse_name"
#                                     ]
#                                 ),

#                                 incident=(
#                                     item[
#                                         "incident"
#                                     ]
#                                 ),

#                                 snapshot=(
#                                     item[
#                                         "snapshot"
#                                     ]
#                                 ),
#                             )

#                             for item in events
#                         ],
#                     ),
#                 ],
#             ),
#         ],
#     )


# # =============================================================================
# # СКЛОНЕНИЕ "СОБЫТИЕ / СОБЫТИЯ / СОБЫТИЙ"
# # =============================================================================


# def _event_word(
#     count: int,
# ) -> str:
#     """
#     1 событие
#     2 события
#     5 событий
#     21 событие
#     23 события
#     27 событий
#     """

#     count = abs(
#         int(
#             count
#             or 0
#         )
#     )

#     last_two = (
#         count
#         % 100
#     )

#     last_one = (
#         count
#         % 10
#     )

#     if (
#         11
#         <= last_two
#         <= 14
#     ):
#         return "событий"

#     if last_one == 1:
#         return "событие"

#     if last_one in {
#         2,
#         3,
#         4,
#     }:
#         return "события"

#     return "событий"





# gear/app/daily_sales/stocks/dashboard_stock/incidents_panel.py

"""Панель происшествий на основной странице dashboard."""

from __future__ import annotations

import pandas as pd
import dash_mantine_components as dmc
from dash_iconify import DashIconify

from dash import dcc, html

from ..dashboard_data import (
    get_warehouse_incident_snapshot,
)

from ..data import get_warehouse_incident_stock_items

from .ids import (
    STOCK_INCIDENT_EXCEL_BTN_ID,
    STOCK_INCIDENT_EXCEL_DOWNLOAD_ID,
    STOCK_INCIDENT_PDF_BTN_ID,
    STOCK_INCIDENT_PDF_DOWNLOAD_ID,
)

from .warehouse_incidents import (
    WAREHOUSE_INCIDENTS,
)

from .helpers import (
    fmt,
    fmt_money,
)


# =============================================================================
# ЦВЕТА
# =============================================================================

TEXT = "#18352F"
MUTED = "#60746D"

BORDER = "#D6DFDB"

INCIDENT_BORDER = "#E2CACA"
INCIDENT_ACCENT = "#A43E3E"
INCIDENT_BG = "#FFFDFD"

EMPTY_BG = "#F7F9F8"
EMPTY_BORDER = "#DCE4E0"

SUMMARY_BG = "#F7F9F8"
SUMMARY_ACCENT = "#315E52"
SUMMARY_VALUE = "#18352F"


# =============================================================================
# ИНФОРМАЦИОННЫЙ БЛОК — ФИЗИЧЕСКОГО ОСТАТКА НЕТ
# =============================================================================


def _empty_stock_banner(
    snapshot_label: str,
):
    """
    Показывается вместо KPI, если на дату снимка
    физический остаток на складе равен нулю.
    """

    return dmc.Paper(
        radius=0,
        p="md",
        mt="lg",

        style={
            "background": EMPTY_BG,
            "border": f"1px solid {EMPTY_BORDER}",
        },

        children=[

            dmc.Group(
                gap=10,
                align="flex-start",

                children=[

                    html.Div(
                        style={
                            "width": "4px",
                            "minWidth": "4px",
                            "height": "40px",
                            "background": "#94A39D",
                        },
                    ),

                    html.Div(
                        style={
                            "minWidth": 0,
                        },

                        children=[

                            dmc.Text(
                                "Физический товарный остаток отсутствовал",
                                fw=600,
                                size="sm",
                                c=TEXT,
                            ),

                            dmc.Text(
                                (
                                    f"По данным на {snapshot_label} "
                                    "товар физически на складе отсутствовал. "
                                    "Оценка стоимости товарного остатка "
                                    "для данного происшествия не производится."
                                ),
                                size="xs",
                                c=MUTED,
                                mt=3,
                                style={
                                    "lineHeight": 1.5,
                                },
                            ),
                        ],
                    ),
                ],
            ),
        ],
    )


# =============================================================================
# KPI
# =============================================================================


def _metric(
    label: str,
    value: str,
    *,
    value_color: str = TEXT,
    subvalue: str | None = None,
):
    """
    Унифицированный KPI.

    subvalue используется, например, для:

        15 шт
        4 NM ID
    """

    children = [

        dmc.Text(
            label,
            size="xs",
            c="dimmed",
        ),

        dmc.Text(
            value,
            fw=700,
            size="lg",
            c=value_color,
            mt=1,
        ),
    ]

    if subvalue:
        children.append(
            dmc.Text(
                subvalue,
                size="xs",
                c="dimmed",
                mt=1,
            )
        )

    return html.Div(
        children=children,
    )


# =============================================================================
# СБОР СОБЫТИЙ
#
# Переиспользуется:
#   1. панелью происшествий на dashboard (build_incidents_panel);
#   2. экспортом в Excel/PDF (callbacks.py).
#
# Snapshot и постатейная детализация (items) запрашиваются один раз
# на событие, чтобы не дублировать обращения к БД.
# =============================================================================


def get_incident_events() -> list[dict]:
    events = []

    for warehouse_name, incidents in WAREHOUSE_INCIDENTS.items():
        for incident in incidents:
            incident_date = pd.to_datetime(
                incident.get("date", "")
            )

            requested_snapshot_date = (
                incident_date
                - pd.Timedelta(days=1)
            )

            snapshot_date_str = (
                requested_snapshot_date.strftime("%Y-%m-%d")
            )

            snapshot = get_warehouse_incident_snapshot(
                warehouse_name=warehouse_name,
                incident_date=snapshot_date_str,
            )

            items = get_warehouse_incident_stock_items(
                warehouse_name=warehouse_name,
                report_date=snapshot_date_str,
            )

            events.append(
                {
                    "date": incident.get("date", ""),
                    "warehouse_name": warehouse_name,
                    "incident": incident,
                    "snapshot": snapshot or {},
                    "items": items,
                }
            )

    events.sort(
        key=lambda item: item.get("date", ""),
        reverse=True,
    )

    return events


# =============================================================================
# SUMMARY ПО ВСЕМ ПРОИСШЕСТВИЯМ
# =============================================================================


def _build_incidents_summary(
    prepared_events: list[dict],
):
    """
    Общая оценка товарного остатка,
    потенциально затронутого происшествиями.

    Для каждого события используется исторический снимок
    на конец календарного дня, предшествующего происшествию.

    В расчёт входит только физический остаток.

    Товары в пути не учитываются.
    """

    total_events = len(
        prepared_events
    )

    total_on_hand = 0.0

    total_accounting_cost = 0.0
    total_management_cost = 0.0

    warehouses_with_stock = set()

    no_accounting_cost_qty = 0
    no_management_cost_qty = 0

    no_snapshot_count = 0

    # =========================================================================
    # Собираем итог
    # =========================================================================

    for item in prepared_events:

        snapshot = (
            item.get("snapshot")
            or {}
        )

        effective_date = snapshot.get(
            "effective_date"
        )

        if not effective_date:
            no_snapshot_count += 1
            continue

        on_hand = float(
            snapshot.get(
                "on_hand",
                0,
            )
            or 0
        )

        accounting_cost = float(
            snapshot.get(
                "accounting_cost",
                0,
            )
            or 0
        )

        management_cost = float(
            snapshot.get(
                "management_cost",
                0,
            )
            or 0
        )

        total_on_hand += on_hand

        total_accounting_cost += (
            accounting_cost
        )

        total_management_cost += (
            management_cost
        )

        no_accounting_cost_qty += int(
            snapshot.get(
                "no_accounting_cost_qty",
                0,
            )
            or 0
        )

        no_management_cost_qty += int(
            snapshot.get(
                "no_management_cost_qty",
                0,
            )
            or 0
        )

        if on_hand > 0:
            warehouses_with_stock.add(
                item.get(
                    "warehouse_name",
                    "",
                )
            )

    warehouse_count = len(
        warehouses_with_stock
    )

    # =========================================================================
    # Дополнительное примечание
    # =========================================================================

    footnote_parts = [
        (
            "Итог рассчитан по физическому товарному остатку "
            "на конец дня, предшествующего каждому происшествию. "
            "Товары в пути не включены."
        )
    ]

    if (
        no_accounting_cost_qty > 0
        or no_management_cost_qty > 0
    ):
        footnote_parts.append(
            (
                " Позиции без определённой себестоимости "
                "не включены в соответствующую стоимостную оценку."
            )
        )

    if no_snapshot_count > 0:
        footnote_parts.append(
            (
                f" Для {fmt(no_snapshot_count)} "
                f"{_event_word(no_snapshot_count)} "
                "исторический снимок остатков не найден."
            )
        )

    # =========================================================================
    # Карточка summary
    # =========================================================================

    return dmc.Paper(
        radius=0,
        p="md",
        mb="md",

        style={
            "background": SUMMARY_BG,
            "border": f"1px solid {BORDER}",
            "borderLeft": (
                f"4px solid {SUMMARY_ACCENT}"
            ),
        },

        children=[

            # =================================================================
            # HEADER
            # =================================================================

            dmc.Group(
                justify="space-between",
                align="center",
                gap="md",
                mb="md",

                children=[

                    html.Div(
                        style={
                            "minWidth": 0,
                        },

                        children=[

                            dmc.Text(
                                "Общая оценка товарных потерь",
                                fw=700,
                                size="sm",
                                c=TEXT,
                            ),

                            dmc.Text(
                                (
                                    "Сводная оценка физического остатка "
                                    "по зарегистрированным происшествиям"
                                ),
                                size="xs",
                                c="dimmed",
                                mt=2,
                            ),
                        ],
                    ),

                    dmc.Badge(
                        (
                            f"{total_events} "
                            f"{_event_word(total_events)}"
                        ),
                        color="gray",
                        variant="light",
                        radius=0,
                    ),
                ],
            ),

            # =================================================================
            # KPI
            # =================================================================

            dmc.SimpleGrid(
                cols={
                    "base": 2,
                    "sm": 2,
                    "lg": 4,
                },

                spacing="lg",

                children=[

                    # ---------------------------------------------------------
                    # Склады
                    # ---------------------------------------------------------

                    _metric(
                        "Складов с остатком",
                        fmt(
                            warehouse_count
                        ),
                    ),

                    # ---------------------------------------------------------
                    # Физический остаток
                    # ---------------------------------------------------------

                    _metric(
                        "Физический остаток",
                        (
                            f"{fmt(
                                total_on_hand
                            )} шт"
                        ),
                    ),

                    # ---------------------------------------------------------
                    # Бухгалтерская себестоимость
                    # ---------------------------------------------------------

                    _metric(
                        "Бухгалтерская с/с",
                        (
                            f"{fmt_money(
                                total_accounting_cost
                            )} ₽"
                        ),
                        value_color=SUMMARY_VALUE,
                    ),

                    # ---------------------------------------------------------
                    # Управленческая себестоимость
                    # ---------------------------------------------------------

                    _metric(
                        "Управленческая с/с",
                        (
                            f"{fmt_money(
                                total_management_cost
                            )} ₽"
                        ),
                        value_color=SUMMARY_VALUE,
                    ),
                ],
            ),

            # =================================================================
            # FOOTNOTE
            # =================================================================

            dmc.Text(
                "".join(
                    footnote_parts
                ),
                size="xs",
                c="dimmed",
                mt="md",
                style={
                    "lineHeight": 1.45,
                },
            ),
        ],
    )


# =============================================================================
# КАРТОЧКА ПРОИСШЕСТВИЯ
# =============================================================================


def _incident_card(
    warehouse_name: str,
    incident: dict,
    snapshot: dict | None = None,
):
    """
    Карточка одного происшествия.

    incident["date"] — фактическая дата происшествия.

    Для финансовой оценки используется исторический
    снимок склада на конец ПРЕДЫДУЩЕГО календарного дня.

    Например:

        происшествие: 22.07.2026
        снимок:       21.07.2026

    В оценку включается только физический остаток quantity.

    Товары в пути не учитываются.

    snapshot можно передать извне, чтобы повторно
    не обращаться к базе данных.
    """

    # =========================================================================
    # Дата происшествия
    # =========================================================================

    incident_date = pd.to_datetime(
        incident["date"]
    )

    event_date = incident_date.strftime(
        "%d.%m.%Y"
    )

    # =========================================================================
    # Требуемая дата снимка
    # =========================================================================

    requested_snapshot_date = (
        incident_date
        - pd.Timedelta(days=1)
    )

    # =========================================================================
    # Исторический снимок
    #
    # Если snapshot уже был получен при построении основной панели,
    # повторный запрос к БД не выполняем.
    # =========================================================================

    if snapshot is None:

        snapshot = (
            get_warehouse_incident_snapshot(
                warehouse_name=warehouse_name,

                incident_date=(
                    requested_snapshot_date.strftime(
                        "%Y-%m-%d"
                    )
                ),
            )
        )

    snapshot = snapshot or {}

    # =========================================================================
    # Фактическая дата снимка
    # =========================================================================

    effective_date = snapshot.get(
        "effective_date"
    )

    snapshot_label = (
        pd.to_datetime(
            effective_date
        ).strftime(
            "%d.%m.%Y"
        )
        if effective_date
        else "нет данных"
    )

    # =========================================================================
    # Основные показатели
    # =========================================================================

    on_hand = float(
        snapshot.get(
            "on_hand",
            0,
        )
        or 0
    )

    has_physical_stock = (
        on_hand > 0
    )

    # =========================================================================
    # Без бухгалтерской себестоимости
    # =========================================================================

    no_accounting_cost_qty = int(
        snapshot.get(
            "no_accounting_cost_qty",
            0,
        )
        or 0
    )

    no_accounting_cost_nm_count = int(
        snapshot.get(
            "no_accounting_cost_nm_count",
            0,
        )
        or 0
    )

    # =========================================================================
    # Без управленческой себестоимости
    # =========================================================================

    no_management_cost_qty = int(
        snapshot.get(
            "no_management_cost_qty",
            0,
        )
        or 0
    )

    no_management_cost_nm_count = int(
        snapshot.get(
            "no_management_cost_nm_count",
            0,
        )
        or 0
    )

    # =========================================================================
    # Нет данных вообще
    # =========================================================================

    no_snapshot_data = (
        not effective_date
    )

    # =========================================================================
    # KPI / информационный блок
    # =========================================================================

    if no_snapshot_data:

        content_block = dmc.Paper(
            radius=0,
            p="md",
            mt="lg",

            style={
                "background": "#FFF8F8",
                "border": (
                    f"1px solid {INCIDENT_BORDER}"
                ),
            },

            children=[

                dmc.Text(
                    "Нет данных об остатках",
                    fw=600,
                    size="sm",
                    c=INCIDENT_ACCENT,
                ),

                dmc.Text(
                    (
                        "Для даты, предшествующей происшествию, "
                        "не найден снимок товарных остатков. "
                        "Финансовая оценка происшествия не рассчитана."
                    ),
                    size="xs",
                    c=MUTED,
                    mt=3,
                    style={
                        "lineHeight": 1.5,
                    },
                ),
            ],
        )

    elif not has_physical_stock:

        content_block = (
            _empty_stock_banner(
                snapshot_label=snapshot_label,
            )
        )

    else:

        content_block = dmc.SimpleGrid(
            cols={
                "base": 2,
                "sm": 3,
                "lg": 6,
            },

            spacing="lg",

            mt="lg",

            children=[

                # -------------------------------------------------------------
                # Физический остаток
                # -------------------------------------------------------------

                _metric(
                    "Физический остаток",
                    (
                        f"{fmt(
                            snapshot.get(
                                'on_hand',
                                0,
                            )
                        )} шт"
                    ),
                ),

                # -------------------------------------------------------------
                # Товаров
                # -------------------------------------------------------------

                _metric(
                    "Товаров",
                    (
                        f"{fmt(
                            snapshot.get(
                                'nm_count',
                                0,
                            )
                        )} NM ID"
                    ),
                ),

                # -------------------------------------------------------------
                # Бухгалтерская себестоимость
                # -------------------------------------------------------------

                _metric(
                    "Бухгалтерская с/с",
                    (
                        f"{fmt_money(
                            snapshot.get(
                                'accounting_cost',
                                0,
                            )
                        )} ₽"
                    ),
                ),

                # -------------------------------------------------------------
                # Без бухгалтерской себестоимости
                # -------------------------------------------------------------

                _metric(
                    "Без бух. с/с",
                    (
                        f"{fmt(
                            no_accounting_cost_qty
                        )} шт"
                    ),

                    value_color=(
                        INCIDENT_ACCENT
                        if no_accounting_cost_qty > 0
                        else TEXT
                    ),

                    subvalue=(
                        (
                            f"{fmt(
                                no_accounting_cost_nm_count
                            )} NM ID"
                        )
                        if no_accounting_cost_qty > 0
                        else None
                    ),
                ),

                # -------------------------------------------------------------
                # Управленческая себестоимость
                # -------------------------------------------------------------

                _metric(
                    "Управленческая с/с",
                    (
                        f"{fmt_money(
                            snapshot.get(
                                'management_cost',
                                0,
                            )
                        )} ₽"
                    ),
                ),

                # -------------------------------------------------------------
                # Без управленческой себестоимости
                # -------------------------------------------------------------

                _metric(
                    "Без упр. с/с",
                    (
                        f"{fmt(
                            no_management_cost_qty
                        )} шт"
                    ),

                    value_color=(
                        INCIDENT_ACCENT
                        if no_management_cost_qty > 0
                        else TEXT
                    ),

                    subvalue=(
                        (
                            f"{fmt(
                                no_management_cost_nm_count
                            )} NM ID"
                        )
                        if no_management_cost_qty > 0
                        else None
                    ),
                ),
            ],
        )

    # =========================================================================
    # Методологическое примечание
    #
    # Показываем только тогда, когда физический остаток реально был.
    # При нулевом остатке пояснение уже находится внутри отдельного баннера.
    # =========================================================================

    if has_physical_stock:

        footnote_parts = [
            (
                "Оценка рассчитана по товару, физически находившемуся "
                "на складе на конец дня, предшествующего происшествию. "
                "Позиции в пути в расчёт не включены."
            )
        ]

        if (
            no_accounting_cost_qty > 0
            or no_management_cost_qty > 0
        ):
            footnote_parts.append(
                (
                    " Позиции без определённой себестоимости "
                    "не включены в соответствующую стоимостную оценку."
                )
            )

        footnote = dmc.Text(
            "".join(
                footnote_parts
            ),

            size="xs",

            c="dimmed",

            mt="md",

            style={
                "lineHeight": 1.45,
            },
        )

    else:

        footnote = None

    # =========================================================================
    # Карточка
    # =========================================================================

    return dmc.Paper(
        radius=0,
        p="lg",

        style={
            "border": (
                f"1px solid {INCIDENT_BORDER}"
            ),

            "borderLeft": (
                f"4px solid {INCIDENT_ACCENT}"
            ),

            "background": INCIDENT_BG,

            "flexShrink": 0,
        },

        children=[

            # =================================================================
            # HEADER
            # =================================================================

            dmc.Group(
                justify="space-between",

                align="flex-start",

                gap="md",

                children=[

                    # ---------------------------------------------------------
                    # Название склада / событие
                    # ---------------------------------------------------------

                    html.Div(
                        style={
                            "minWidth": 0,
                        },

                        children=[

                            dmc.Group(
                                gap=8,

                                align="center",

                                children=[

                                    dmc.Text(
                                        warehouse_name,

                                        fw=700,

                                        size="md",

                                        c=TEXT,
                                    ),

                                    dmc.Badge(
                                        incident.get(
                                            "status",
                                            "Происшествие",
                                        ),

                                        color="red",

                                        variant="light",

                                        radius=0,
                                    ),
                                ],
                            ),

                            dmc.Text(
                                (
                                    f"{incident.get(
                                        'title',
                                        'Происшествие',
                                    )} · {event_date}"
                                ),

                                size="sm",

                                c=MUTED,

                                mt=2,
                            ),
                        ],
                    ),

                    # ---------------------------------------------------------
                    # Дата остатков
                    # ---------------------------------------------------------

                    dmc.Text(
                        (
                            "Остатки на: "
                            f"{snapshot_label}"
                        ),

                        size="xs",

                        c="dimmed",

                        style={
                            "whiteSpace": "nowrap",
                        },
                    ),
                ],
            ),

            # =================================================================
            # ОПИСАНИЕ
            # =================================================================

            dmc.Text(
                incident.get(
                    "description",
                    "",
                ),

                size="sm",

                c=TEXT,

                mt="md",

                style={
                    "lineHeight": 1.5,
                },
            ),

            # =================================================================
            # KPI ИЛИ БАННЕР
            # =================================================================

            content_block,

            # =================================================================
            # FOOTNOTE
            # =================================================================

            footnote,
        ],
    )


# =============================================================================
# ОСНОВНАЯ ПАНЕЛЬ
# =============================================================================


def build_incidents_panel():
    """
    Формирует блок происшествий на основной странице.

    Особенности:

    - события сортируются от новых к старым;
    - snapshot и постатейная детализация каждого события
      загружаются только один раз (через get_incident_events);
    - сверху показывается общая оценка потерь;
    - заголовок и общий итог остаются неподвижными;
    - прокручиваются только карточки событий;
    - при небольшом числе событий scroll не показывается;
    - при большом числе событий dashboard не растягивается вниз;
    - в шапке — кнопки скачивания остатков (Excel) и
      сопроводительного письма (PDF) для оценки ущерба.
    """

    # =========================================================================
    # Собираем все события
    # =========================================================================

    events = get_incident_events()

    # =========================================================================
    # Нет происшествий
    # =========================================================================

    if not events:
        return None

    # =========================================================================
    # Панель
    # =========================================================================

    return dmc.Paper(
        radius=0,
        p="lg",

        style={
            "border": (
                f"1px solid {BORDER}"
            ),

            "background": "#FFFFFF",
        },

        children=[

            # =================================================================
            # HEADER
            # =================================================================

            dmc.Group(
                justify="space-between",

                align="flex-end",

                gap="md",

                mb="md",

                children=[

                    html.Div(
                        children=[

                            dmc.Text(
                                "Происшествия на складах",

                                fw=700,

                                size="md",

                                c=TEXT,
                            ),

                            dmc.Text(
                                (
                                    "Зафиксированные события и оценка "
                                    "товарного остатка на конец дня, "
                                    "предшествующего происшествию."
                                ),

                                size="xs",

                                c="dimmed",

                                mt=2,
                            ),
                        ],
                    ),

                    dmc.Group(
                        gap="xs",

                        children=[

                            dcc.Download(
                                id=STOCK_INCIDENT_EXCEL_DOWNLOAD_ID
                            ),

                            dcc.Download(
                                id=STOCK_INCIDENT_PDF_DOWNLOAD_ID
                            ),

                            dmc.Button(
                                "Остатки для оценки ущерба (Excel)",
                                id=STOCK_INCIDENT_EXCEL_BTN_ID,
                                leftSection=DashIconify(
                                    icon=(
                                        "material-symbols:"
                                        "download-rounded"
                                    ),
                                    width=16,
                                ),
                                variant="outline",
                                color="red",
                                radius=0,
                                size="xs",
                            ),

                            dmc.Button(
                                "Сопроводительное письмо (PDF)",
                                id=STOCK_INCIDENT_PDF_BTN_ID,
                                leftSection=DashIconify(
                                    icon=(
                                        "material-symbols:"
                                        "picture-as-pdf-outline"
                                    ),
                                    width=16,
                                ),
                                variant="outline",
                                color="red",
                                radius=0,
                                size="xs",
                            ),
                        ],
                    ),
                ],
            ),

            # =================================================================
            # ОБЩАЯ ОЦЕНКА
            # =================================================================

            _build_incidents_summary(
                prepared_events=events,
            ),

            # =================================================================
            # SCROLL
            #
            # Summary находится выше scroll,
            # поэтому всегда остаётся на экране.
            # =================================================================

            html.Div(
                style={
                    "maxHeight": "280px",

                    "overflowY": "auto",

                    "overflowX": "hidden",

                    "paddingRight": "8px",

                    "scrollbarGutter": "stable",

                    "WebkitOverflowScrolling": "touch",
                },

                children=[

                    dmc.Stack(
                        gap="sm",

                        children=[

                            _incident_card(
                                warehouse_name=(
                                    item[
                                        "warehouse_name"
                                    ]
                                ),

                                incident=(
                                    item[
                                        "incident"
                                    ]
                                ),

                                snapshot=(
                                    item[
                                        "snapshot"
                                    ]
                                ),
                            )

                            for item in events
                        ],
                    ),
                ],
            ),
        ],
    )


# =============================================================================
# СКЛОНЕНИЕ "СОБЫТИЕ / СОБЫТИЯ / СОБЫТИЙ"
# =============================================================================


def _event_word(
    count: int,
) -> str:
    """
    1 событие
    2 события
    5 событий
    21 событие
    23 события
    27 событий
    """

    count = abs(
        int(
            count
            or 0
        )
    )

    last_two = (
        count
        % 100
    )

    last_one = (
        count
        % 10
    )

    if (
        11
        <= last_two
        <= 14
    ):
        return "событий"

    if last_one == 1:
        return "событие"

    if last_one in {
        2,
        3,
        4,
    }:
        return "события"

    return "событий"