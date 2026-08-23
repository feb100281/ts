# # gear/app/loans/automatic_alerts.py

# from __future__ import annotations

# from datetime import date

# import dash_mantine_components as dmc
# import pandas as pd
# from dash import Input, Output, html, State
# from dash_iconify import DashIconify

# from .config import COLORS
# from .ids import DATA_SIGNAL_ID, REPORT_DATE_ID
# from .management_common import (
#     get_document_counts,
#     get_management_snapshot,
# )


# # =====================================================================
# # IDs
# # =====================================================================

# ALERTS_BUTTON_ID = "loans-alerts-button"
# ALERTS_BUTTON_COUNT_ID = "loans-alerts-button-count"

# ALERTS_MODAL_ID = "loans-alerts-modal"
# ALERTS_MODAL_CLOSE_ID = "loans-alerts-modal-close"

# ALERTS_LIST_ID = "loans-management-alerts-list"

# ALERTS_COUNT_ID = "loans-management-alerts-count"

# ALERTS_CRITICAL_COUNT_ID = (
#     "loans-management-alerts-critical-count"
# )

# ALERTS_WARNING_COUNT_ID = (
#     "loans-management-alerts-warning-count"
# )


# # =====================================================================
# # HELPERS
# # =====================================================================


# def _as_date(value):
#     parsed = pd.to_datetime(
#         value,
#         errors="coerce",
#     )

#     if pd.isna(parsed):
#         return None

#     return parsed.date()


# def _safe_float(
#     value,
#     default: float = 0.0,
# ) -> float:
#     try:
#         return float(value or 0)
#     except (TypeError, ValueError):
#         return default


# def _safe_int(
#     value,
#     default: int = 0,
# ) -> int:
#     try:
#         return int(value or 0)
#     except (TypeError, ValueError):
#         return default


# def _format_date(value) -> str:
#     parsed = _as_date(value)

#     if not parsed:
#         return "без даты"

#     return parsed.strftime(
#         "%d.%m.%Y"
#     )


# def _format_money(
#     value,
# ) -> str:
#     try:
#         return (
#             f"{float(value or 0):,.2f}"
#             .replace(",", " ")
#         )
#     except (TypeError, ValueError):
#         return "0,00"


# def _format_money_short(
#     value,
# ) -> str:
#     """
#     Компактное отображение суммы.

#     200 000 000 -> 200,00 млн
#     13 640 400  -> 13,64 млн
#     571 887     -> 571,89 тыс.
#     """

#     value = _safe_float(value)
#     abs_value = abs(value)

#     if abs_value >= 1_000_000_000:
#         return (
#             f"{value / 1_000_000_000:,.2f}"
#             .replace(",", " ")
#             + " млрд"
#         )

#     if abs_value >= 1_000_000:
#         return (
#             f"{value / 1_000_000:,.2f}"
#             .replace(",", " ")
#             + " млн"
#         )

#     if abs_value >= 100_000:
#         return (
#             f"{value / 1_000:,.2f}"
#             .replace(",", " ")
#             + " тыс."
#         )

#     return _format_money(value)


# def _plural_contracts(
#     value: int,
# ) -> str:
#     value = abs(int(value))

#     last_two = value % 100
#     last_one = value % 10

#     if 11 <= last_two <= 14:
#         return "договоров"

#     if last_one == 1:
#         return "договор"

#     if 2 <= last_one <= 4:
#         return "договора"

#     return "договоров"


# def _plural_files(
#     value: int,
# ) -> str:
#     value = abs(int(value))

#     last_two = value % 100
#     last_one = value % 10

#     if 11 <= last_two <= 14:
#         return "файлов"

#     if last_one == 1:
#         return "файл"

#     if 2 <= last_one <= 4:
#         return "файла"

#     return "файлов"


# # =====================================================================
# # BUILD ALERTS
# # =====================================================================


# def build_alerts(
#     snapshot: pd.DataFrame,
#     report_date: str,
# ) -> list[dict]:
#     """
#     Одна карточка = один договор.

#     Критично:
#     - договор просрочен;
#     - до погашения <= 7 дней.

#     Проверить:
#     - до погашения <= 30 дней;
#     - нет даты погашения;
#     - нет документов;
#     - ставка <= 0.

#     ВАЖНО:
#     документы проверяем по ВСЕМ договорам,
#     даже если долг уже погашен.
#     """

#     report = (
#         _as_date(report_date)
#         or date.today()
#     )

#     if snapshot.empty:
#         return []

#     work = snapshot.copy()

#     # =================================================================
#     # Фактическое количество документов
#     # =================================================================

#     contract_ids = [
#         int(x)
#         for x in work[
#             "contract_id"
#         ]
#         .dropna()
#         .unique()
#         .tolist()
#     ]

#     docs = get_document_counts(
#         contract_ids
#     )

#     if not docs.empty:
#         work = work.merge(
#             docs,
#             how="left",
#             on="contract_id",
#             suffixes=(
#                 "",
#                 "_actual",
#             ),
#         )

#         if (
#             "documents_count_actual"
#             in work.columns
#         ):
#             work[
#                 "documents_count"
#             ] = (
#                 work[
#                     "documents_count_actual"
#                 ]
#                 .fillna(
#                     work.get(
#                         "documents_count",
#                         0,
#                     )
#                 )
#             )

#     # =================================================================
#     # Проверка договоров
#     # =================================================================

#     alerts = []

#     for row in work.to_dict(
#         "records"
#     ):
#         contract_id = row.get(
#             "contract_id"
#         )

#         counterparty = (
#             row.get(
#                 "counterparty_name"
#             )
#             or "Контрагент не указан"
#         )

#         number = (
#             row.get(
#                 "contract_number"
#             )
#             or "б/н"
#         )

#         contract_date = _as_date(
#             row.get(
#                 "contract_date"
#             )
#         )

#         maturity = _as_date(
#             row.get(
#                 "repayment_date"
#             )
#         )

#         debt = _safe_float(
#             row.get(
#                 "total_debt"
#             )
#         )

#         principal_debt = _safe_float(
#             row.get(
#                 "ending_balance"
#             )
#         )

#         interest_debt = _safe_float(
#             row.get(
#                 "interest_balance"
#             )
#         )

#         rate = _safe_float(
#             row.get(
#                 "rate"
#             )
#         )

#         documents_count = _safe_int(
#             row.get(
#                 "documents_count"
#             )
#         )

#         currency = (
#             row.get(
#                 "currency"
#             )
#             or ""
#         )

#         issues = []

#         # =============================================================
#         # СРОК ПОГАШЕНИЯ
#         # Только по договорам, где реально есть долг.
#         # =============================================================

#         if debt > 0.01:

#             if maturity:
#                 days_to_maturity = (
#                     maturity
#                     - report
#                 ).days

#                 # -----------------------------------------------------
#                 # Просрочено
#                 # -----------------------------------------------------

#                 if days_to_maturity < 0:
#                     issues.append(
#                         {
#                             "severity": (
#                                 "critical"
#                             ),

#                             "icon": (
#                                 "solar:"
#                                 "danger-circle-linear"
#                             ),

#                             "title": (
#                                 "Просрочено "
#                                 f"на "
#                                 f"{abs(days_to_maturity)} "
#                                 "дн."
#                             ),

#                             "text": (
#                                 "Дата погашения "
#                                 f"{maturity.strftime('%d.%m.%Y')}"
#                             ),
#                         }
#                     )

#                 # -----------------------------------------------------
#                 # До 7 дней
#                 # -----------------------------------------------------

#                 elif days_to_maturity <= 7:
#                     issues.append(
#                         {
#                             "severity": (
#                                 "critical"
#                             ),

#                             "icon": (
#                                 "solar:"
#                                 "calendar-minimalistic-linear"
#                             ),

#                             "title": (
#                                 "Погашение "
#                                 f"через "
#                                 f"{days_to_maturity} "
#                                 "дн."
#                             ),

#                             "text": (
#                                 "Дата погашения "
#                                 f"{maturity.strftime('%d.%m.%Y')}"
#                             ),
#                         }
#                     )

#                 # -----------------------------------------------------
#                 # До 30 дней
#                 # -----------------------------------------------------

#                 elif days_to_maturity <= 30:
#                     issues.append(
#                         {
#                             "severity": (
#                                 "warning"
#                             ),

#                             "icon": (
#                                 "solar:"
#                                 "calendar-linear"
#                             ),

#                             "title": (
#                                 "Погашение "
#                                 f"через "
#                                 f"{days_to_maturity} "
#                                 "дн."
#                             ),

#                             "text": (
#                                 "Дата погашения "
#                                 f"{maturity.strftime('%d.%m.%Y')}"
#                             ),
#                         }
#                     )

#             else:
#                 issues.append(
#                     {
#                         "severity": (
#                             "warning"
#                         ),

#                         "icon": (
#                             "solar:"
#                             "calendar-search-linear"
#                         ),

#                         "title": (
#                             "Не указана "
#                             "дата погашения"
#                         ),

#                         "text": (
#                             "Невозможно определить "
#                             "срок возврата займа."
#                         ),
#                     }
#                 )

#         # =============================================================
#         # ДОКУМЕНТЫ
#         #
#         # Проверяем ВСЕ договоры,
#         # независимо от текущего долга.
#         # =============================================================

#         if documents_count <= 0:
#             issues.append(
#                 {
#                     "severity": (
#                         "warning"
#                     ),

#                     "icon": (
#                         "solar:"
#                         "folder-error-linear"
#                     ),

#                     "title": (
#                         "Нет документов"
#                     ),

#                     "text": (
#                         "По договору не найден "
#                         "ни один загруженный файл."
#                     ),
#                 }
#             )

#         # =============================================================
#         # СТАВКА
#         # =============================================================

#         if (
#             debt > 0.01
#             and rate <= 0
#         ):
#             issues.append(
#                 {
#                     "severity": (
#                         "warning"
#                     ),

#                     "icon": (
#                         "solar:"
#                         "percent-circle-linear"
#                     ),

#                     "title": (
#                         "Ставка не задана"
#                     ),

#                     "text": (
#                         "Проверьте процентную "
#                         "ставку договора."
#                     ),
#                 }
#             )

#         # =============================================================
#         # Нет замечаний
#         # =============================================================

#         if not issues:
#             continue

#         # =============================================================
#         # Общая критичность карточки
#         # =============================================================

#         has_critical = any(
#             issue.get(
#                 "severity"
#             )
#             == "critical"
#             for issue in issues
#         )

#         severity = (
#             "critical"
#             if has_critical
#             else "warning"
#         )

#         alerts.append(
#             {
#                 "contract_id": (
#                     contract_id
#                 ),

#                 "counterparty_name": (
#                     counterparty
#                 ),

#                 "contract_number": (
#                     number
#                 ),

#                 "contract_date": (
#                     contract_date
#                 ),

#                 "repayment_date": (
#                     maturity
#                 ),

#                 "currency": (
#                     currency
#                 ),

#                 "total_debt": (
#                     debt
#                 ),

#                 "principal_debt": (
#                     principal_debt
#                 ),

#                 "interest_debt": (
#                     interest_debt
#                 ),

#                 "documents_count": (
#                     documents_count
#                 ),

#                 "severity": (
#                     severity
#                 ),

#                 "issues": (
#                     issues
#                 ),
#             }
#         )

#     # =================================================================
#     # Сортировка
#     #
#     # 1. критичные;
#     # 2. предупреждения;
#     # 3. внутри группы — больший долг выше.
#     # =================================================================

#     severity_rank = {
#         "critical": 0,
#         "warning": 1,
#     }

#     alerts.sort(
#         key=lambda x: (
#             severity_rank.get(
#                 x.get(
#                     "severity"
#                 ),
#                 9,
#             ),

#             -_safe_float(
#                 x.get(
#                     "total_debt"
#                 )
#             ),

#             (
#                 x.get(
#                     "counterparty_name"
#                 )
#                 or ""
#             ),
#         )
#     )

#     return alerts


# # =====================================================================
# # ISSUE ROW
# # =====================================================================


# def _issue_row(
#     issue: dict,
# ):
#     severity = issue.get(
#         "severity",
#         "warning",
#     )

#     if severity == "critical":
#         color = COLORS.get(
#             "red",
#             "#B91C1C",
#         )
#     else:
#         color = COLORS.get(
#             "orange",
#             "#C2410C",
#         )

#     return html.Div(
#         style={
#             "display": "grid",

#             "gridTemplateColumns": (
#                 "16px minmax(0, 1fr)"
#             ),

#             "gap": "6px",

#             "alignItems": (
#                 "start"
#             ),
#         },

#         children=[
#             DashIconify(
#                 icon=issue.get(
#                     "icon",
#                     (
#                         "solar:"
#                         "danger-triangle-linear"
#                     ),
#                 ),

#                 width=13,
#                 height=13,

#                 color=color,

#                 style={
#                     "marginTop": "1px",
#                 },
#             ),

#             html.Div(
#                 style={
#                     "minWidth": 0,
#                 },

#                 children=[
#                     html.Div(
#                         issue.get(
#                             "title",
#                             "",
#                         ),

#                         style={
#                             "fontSize": (
#                                 "11px"
#                             ),

#                             "fontWeight": (
#                                 700
#                             ),

#                             "lineHeight": (
#                                 "14px"
#                             ),

#                             "color": (
#                                 COLORS[
#                                     "text"
#                                 ]
#                             ),
#                         },
#                     ),

#                     html.Div(
#                         issue.get(
#                             "text",
#                             "",
#                         ),

#                         style={
#                             "marginTop": (
#                                 "1px"
#                             ),

#                             "fontSize": (
#                                 "10px"
#                             ),

#                             "lineHeight": (
#                                 "13px"
#                             ),

#                             "color": (
#                                 COLORS[
#                                     "muted"
#                                 ]
#                             ),
#                         },
#                     ),
#                 ],
#             ),
#         ],
#     )


# # =====================================================================
# # SMALL METRIC
# # =====================================================================


# def _metric(
#     *,
#     icon: str,
#     value: str,
#     strong: bool = False,
# ):
#     return html.Div(
#         style={
#             "display": "flex",

#             "alignItems": (
#                 "center"
#             ),

#             "gap": "4px",

#             "whiteSpace": (
#                 "nowrap"
#             ),
#         },

#         children=[
#             DashIconify(
#                 icon=icon,

#                 width=12,
#                 height=12,

#                 color=COLORS[
#                     "muted"
#                 ],
#             ),

#             html.Span(
#                 value,

#                 style={
#                     "fontSize": (
#                         "10px"
#                     ),

#                     "fontWeight": (
#                         700
#                         if strong
#                         else 500
#                     ),

#                     "color": (
#                         COLORS[
#                             "text"
#                         ]
#                         if strong
#                         else COLORS[
#                             "muted"
#                         ]
#                     ),

#                     "fontVariantNumeric": (
#                         "tabular-nums"
#                     ),
#                 },
#             ),
#         ],
#     )


# # =====================================================================
# # CONTRACT CARD
# # =====================================================================


# def _alert_card(
#     alert: dict,
# ):
#     severity = alert.get(
#         "severity",
#         "warning",
#     )

#     # =================================================================
#     # Цвета
#     # =================================================================

#     if severity == "critical":

#         accent = COLORS.get(
#             "red",
#             "#B91C1C",
#         )

#         background = (
#             "#FFFBFB"
#         )

#         badge_background = (
#             "#FDEEEE"
#         )

#         badge_text = (
#             "Критично"
#         )

#         badge_icon = (
#             "solar:"
#             "danger-circle-linear"
#         )

#     else:

#         accent = COLORS.get(
#             "orange",
#             "#C2410C",
#         )

#         background = (
#             "#FFFCF8"
#         )

#         badge_background = (
#             "#FFF3E6"
#         )

#         badge_text = (
#             "Проверить"
#         )

#         badge_icon = (
#             "solar:"
#             "danger-triangle-linear"
#         )

#     # =================================================================
#     # Данные
#     # =================================================================

#     counterparty = (
#         alert.get(
#             "counterparty_name"
#         )
#         or "Контрагент не указан"
#     )

#     number = (
#         alert.get(
#             "contract_number"
#         )
#         or "б/н"
#     )

#     contract_date = _format_date(
#         alert.get(
#             "contract_date"
#         )
#     )

#     debt = _safe_float(
#         alert.get(
#             "total_debt"
#         )
#     )

#     principal_debt = _safe_float(
#         alert.get(
#             "principal_debt"
#         )
#     )

#     interest_debt = _safe_float(
#         alert.get(
#             "interest_debt"
#         )
#     )

#     documents_count = _safe_int(
#         alert.get(
#             "documents_count"
#         )
#     )

#     currency = (
#         alert.get(
#             "currency"
#         )
#         or ""
#     )

#     issues = (
#         alert.get(
#             "issues"
#         )
#         or []
#     )

#     # =================================================================
#     # Нижние метрики
#     # =================================================================

#     metrics = []

#     if debt > 0.01:
#         metrics.append(
#             _metric(
#                 icon=(
#                     "solar:"
#                     "wallet-money-linear"
#                 ),

#                 value=(
#                     f"{_format_money_short(debt)} "
#                     f"{currency}"
#                 ),

#                 strong=True,
#             )
#         )

#     # Тело показываем отдельно,
#     # только если общий долг отличается от тела.

#     if (
#         principal_debt > 0.01
#         and abs(
#             debt
#             - principal_debt
#         ) > 0.01
#     ):
#         metrics.append(
#             _metric(
#                 icon=(
#                     "solar:"
#                     "banknote-2-linear"
#                 ),

#                 value=(
#                     "тело "
#                     f"{_format_money_short(principal_debt)}"
#                 ),
#             )
#         )

#     # Нулевые проценты не показываем.

#     if interest_debt > 0.01:
#         metrics.append(
#             _metric(
#                 icon=(
#                     "solar:"
#                     "percent-circle-linear"
#                 ),

#                 value=(
#                     "проц. "
#                     f"{_format_money_short(interest_debt)}"
#                 ),
#             )
#         )

#     metrics.append(
#         _metric(
#             icon=(
#                 "solar:"
#                 "paperclip-linear"
#             ),

#             value=(
#                 f"{documents_count} "
#                 f"{_plural_files(documents_count)}"
#             ),
#         )
#     )

#     # =================================================================
#     # CARD
#     # =================================================================

#     return html.Div(
#         style={
#             # КЛЮЧЕВО:
#             # карточка имеет фиксированную ширину
#             # и не растягивается.

#             "flex": (
#                 "0 0 310px"
#             ),

#             "width": (
#                 "310px"
#             ),

#             "minWidth": (
#                 "310px"
#             ),

#             "display": (
#                 "grid"
#             ),

#             "gridTemplateColumns": (
#                 "3px minmax(0, 1fr)"
#             ),

#             "backgroundColor": (
#                 background
#             ),

#             "border": (
#                 f"1px solid "
#                 f"{COLORS['border']}"
#             ),

#             "minHeight": (
#                 "180px"
#             ),
#         },

#         children=[
#             # =========================================================
#             # Цветная вертикальная линия
#             # =========================================================

#             html.Div(
#                 style={
#                     "backgroundColor": (
#                         accent
#                     ),
#                 },
#             ),

#             # =========================================================
#             # CONTENT
#             # =========================================================

#             html.Div(
#                 style={
#                     "display": (
#                         "flex"
#                     ),

#                     "flexDirection": (
#                         "column"
#                     ),

#                     "padding": (
#                         "10px"
#                     ),

#                     "minWidth": 0,
#                 },

#                 children=[
#                     # =================================================
#                     # Верх карточки
#                     # =================================================

#                     html.Div(
#                         style={
#                             "display": (
#                                 "flex"
#                             ),

#                             "alignItems": (
#                                 "flex-start"
#                             ),

#                             "justifyContent": (
#                                 "space-between"
#                             ),

#                             "gap": "8px",
#                         },

#                         children=[
#                             # =========================================
#                             # Контрагент
#                             # =========================================

#                             html.Div(
#                                 style={
#                                     "minWidth": 0,
#                                     "flex": 1,
#                                 },

#                                 children=[
#                                     html.Div(
#                                         counterparty,

#                                         title=(
#                                             counterparty
#                                         ),

#                                         style={
#                                             "fontSize": (
#                                                 "11px"
#                                             ),

#                                             "fontWeight": (
#                                                 700
#                                             ),

#                                             "lineHeight": (
#                                                 "14px"
#                                             ),

#                                             "color": (
#                                                 COLORS[
#                                                     "text"
#                                                 ]
#                                             ),

#                                             "overflow": (
#                                                 "hidden"
#                                             ),

#                                             "textOverflow": (
#                                                 "ellipsis"
#                                             ),

#                                             "whiteSpace": (
#                                                 "nowrap"
#                                             ),
#                                         },
#                                     ),

#                                     html.Div(
#                                         (
#                                             f"Договор № {number} "
#                                             f"от {contract_date}"
#                                         ),

#                                         style={
#                                             "marginTop": (
#                                                 "2px"
#                                             ),

#                                             "fontSize": (
#                                                 "9px"
#                                             ),

#                                             "lineHeight": (
#                                                 "12px"
#                                             ),

#                                             "color": (
#                                                 COLORS[
#                                                     "muted"
#                                                 ]
#                                             ),
#                                         },
#                                     ),
#                                 ],
#                             ),

#                             # =========================================
#                             # Badge
#                             # =========================================

#                             html.Div(
#                                 style={
#                                     "display": (
#                                         "flex"
#                                     ),

#                                     "alignItems": (
#                                         "center"
#                                     ),

#                                     "gap": "3px",

#                                     "padding": (
#                                         "3px 6px"
#                                     ),

#                                     "backgroundColor": (
#                                         badge_background
#                                     ),

#                                     "whiteSpace": (
#                                         "nowrap"
#                                     ),

#                                     "color": (
#                                         accent
#                                     ),
#                                 },

#                                 children=[
#                                     DashIconify(
#                                         icon=(
#                                             badge_icon
#                                         ),

#                                         width=11,
#                                         height=11,
#                                     ),

#                                     html.Span(
#                                         badge_text,

#                                         style={
#                                             "fontSize": (
#                                                 "9px"
#                                             ),

#                                             "fontWeight": (
#                                                 700
#                                             ),
#                                         },
#                                     ),
#                                 ],
#                             ),
#                         ],
#                     ),

#                     # =================================================
#                     # Issues
#                     # =================================================

#                     html.Div(
#                         style={
#                             "display": (
#                                 "flex"
#                             ),

#                             "flexDirection": (
#                                 "column"
#                             ),

#                             "gap": "6px",

#                             "marginTop": (
#                                 "8px"
#                             ),

#                             "paddingTop": (
#                                 "7px"
#                             ),

#                             "borderTop": (
#                                 f"1px solid "
#                                 f"{COLORS['border']}"
#                             ),

#                             # проблемы занимают свободное место,
#                             # чтобы низ карточек был примерно на одном уровне

#                             "flex": 1,
#                         },

#                         children=[
#                             _issue_row(
#                                 issue
#                             )
#                             for issue
#                             in issues
#                         ],
#                     ),

#                     # =================================================
#                     # Metrics
#                     # =================================================

#                     html.Div(
#                         style={
#                             "display": (
#                                 "flex"
#                             ),

#                             "alignItems": (
#                                 "center"
#                             ),

#                             "gap": "10px",

#                             "flexWrap": (
#                                 "wrap"
#                             ),

#                             "marginTop": (
#                                 "8px"
#                             ),

#                             "paddingTop": (
#                                 "7px"
#                             ),

#                             "borderTop": (
#                                 f"1px solid "
#                                 f"{COLORS['border']}"
#                             ),
#                         },

#                         children=metrics,
#                     ),
#                 ],
#             ),
#         ],
#     )


# # =====================================================================
# # HEADER COUNTER
# # =====================================================================


# def _header_counter(
#     *,
#     icon: str,
#     label: str,
#     value_id: str,
#     color: str,
#     background: str,
# ):
#     return html.Div(
#         style={
#             "height": "28px",

#             "display": (
#                 "flex"
#             ),

#             "alignItems": (
#                 "center"
#             ),

#             "gap": "4px",

#             "padding": (
#                 "0 7px"
#             ),

#             "backgroundColor": (
#                 background
#             ),

#             "border": (
#                 f"1px solid "
#                 f"{COLORS['border']}"
#             ),
#         },

#         children=[
#             DashIconify(
#                 icon=icon,

#                 width=12,
#                 height=12,

#                 color=color,
#             ),

#             html.Span(
#                 label,

#                 style={
#                     "fontSize": "9px",
#                     "color": color,
#                 },
#             ),

#             html.Span(
#                 id=value_id,

#                 children="0",

#                 style={
#                     "fontSize": "9px",
#                     "fontWeight": 700,
#                     "color": color,
#                 },
#             ),
#         ],
#     )


# # =====================================================================
# # BUTTON IN APPLICATION HEADER
# # =====================================================================


# def build_alerts_button():
#     """
#     Кнопка в верхней панели приложения.
#     """

#     return dmc.Button(
#         id=ALERTS_BUTTON_ID,

#         radius=0,

#         variant="outline",

#         color="red",

#         h=34,

#         px=10,

#         leftSection=DashIconify(
#             icon=(
#                 "solar:"
#                 "shield-warning-linear"
#             ),

#             width=15,
#         ),

#         children=[
#             html.Span(
#                 "Требует внимания"
#             ),

#             html.Span(
#                 id=(
#                     ALERTS_BUTTON_COUNT_ID
#                 ),

#                 children="0",

#                 style={
#                     "marginLeft": (
#                         "6px"
#                     ),

#                     "fontWeight": (
#                         700
#                     ),
#                 },
#             ),
#         ],

#         styles={
#             "root": {
#                 "fontSize": "11px",
#                 "fontWeight": 600,
#             },
#         },
#     )


# # =====================================================================
# # MODAL
# # =====================================================================


# def build_alerts_modal():
#     """
#     Модальное окно.

#     Договоры идут в ОДНУ горизонтальную строку.
#     При большом количестве появляется горизонтальный scroll.
#     """

#     return dmc.Modal(
#         id=ALERTS_MODAL_ID,

#         opened=False,

#         centered=True,

#         size="90%",

#         radius=0,

#         padding=0,

#         # Используем собственную кнопку закрытия,
#         # чтобы состояние opened надёжно управлялось callback.
#         withCloseButton=False,

#         styles={
#             "content": {
#                 "maxWidth": "1500px",
#             },

#             "body": {
#                 "padding": "0",
#             },

#             "header": {
#                 "display": "none",
#             },
#         },

#         children=[
#             # =========================================================
#             # HEADER
#             # =========================================================

#             html.Div(
#                 style={
#                     "minHeight": (
#                         "56px"
#                     ),

#                     "display": (
#                         "flex"
#                     ),

#                     "alignItems": (
#                         "center"
#                     ),

#                     "justifyContent": (
#                         "space-between"
#                     ),

#                     "gap": "14px",

#                     "padding": (
#                         "10px 14px"
#                     ),

#                     "borderBottom": (
#                         f"1px solid "
#                         f"{COLORS['border']}"
#                     ),

#                     "backgroundColor": (
#                         COLORS["white"]
#                     ),
#                 },

#                 children=[
#                     # =================================================
#                     # LEFT
#                     # =================================================

#                     html.Div(
#                         style={
#                             "display": (
#                                 "flex"
#                             ),

#                             "alignItems": (
#                                 "center"
#                             ),

#                             "gap": "8px",
#                         },

#                         children=[
#                             html.Div(
#                                 style={
#                                     "width": "32px",
#                                     "height": "32px",

#                                     "display": (
#                                         "flex"
#                                     ),

#                                     "alignItems": (
#                                         "center"
#                                     ),

#                                     "justifyContent": (
#                                         "center"
#                                     ),

#                                     "backgroundColor": (
#                                         "#F8FAF9"
#                                     ),

#                                     "border": (
#                                         f"1px solid "
#                                         f"{COLORS['border']}"
#                                     ),
#                                 },

#                                 children=[
#                                     DashIconify(
#                                         icon=(
#                                             "solar:"
#                                             "shield-warning-linear"
#                                         ),

#                                         width=17,

#                                         color=(
#                                             COLORS[
#                                                 "text"
#                                             ]
#                                         ),
#                                     ),
#                                 ],
#                             ),

#                             html.Div(
#                                 children=[
#                                     html.Div(
#                                         (
#                                             "Требует "
#                                             "внимания"
#                                         ),

#                                         style={
#                                             "fontSize": (
#                                                 "15px"
#                                             ),

#                                             "fontWeight": (
#                                                 700
#                                             ),

#                                             "lineHeight": (
#                                                 "18px"
#                                             ),

#                                             "color": (
#                                                 COLORS[
#                                                     "text"
#                                                 ]
#                                             ),
#                                         },
#                                     ),

#                                     html.Div(
#                                         id=(
#                                             ALERTS_COUNT_ID
#                                         ),

#                                         children=(
#                                             "Нет замечаний"
#                                         ),

#                                         style={
#                                             "marginTop": (
#                                                 "2px"
#                                             ),

#                                             "fontSize": (
#                                                 "10px"
#                                             ),

#                                             "color": (
#                                                 COLORS[
#                                                     "muted"
#                                                 ]
#                                             ),
#                                         },
#                                     ),
#                                 ],
#                             ),
#                         ],
#                     ),

#                     # =================================================
#                     # RIGHT
#                     # =================================================

#                     html.Div(
#                         style={
#                             "display": (
#                                 "flex"
#                             ),

#                             "alignItems": (
#                                 "center"
#                             ),

#                             "gap": "6px",
#                         },

#                         children=[
#                             _header_counter(
#                                 icon=(
#                                     "solar:"
#                                     "danger-circle-linear"
#                                 ),

#                                 label=(
#                                     "Критично"
#                                 ),

#                                 value_id=(
#                                     ALERTS_CRITICAL_COUNT_ID
#                                 ),

#                                 color=(
#                                     COLORS.get(
#                                         "red",
#                                         "#B91C1C",
#                                     )
#                                 ),

#                                 background=(
#                                     "#FFF5F5"
#                                 ),
#                             ),

#                             _header_counter(
#                                 icon=(
#                                     "solar:"
#                                     "danger-triangle-linear"
#                                 ),

#                                 label=(
#                                     "Проверить"
#                                 ),

#                                 value_id=(
#                                     ALERTS_WARNING_COUNT_ID
#                                 ),

#                                 color=(
#                                     COLORS.get(
#                                         "orange",
#                                         "#C2410C",
#                                     )
#                                 ),

#                                 background=(
#                                     "#FFF8F0"
#                                 ),
#                             ),

#                             dmc.ActionIcon(
#                                 id=(
#                                     ALERTS_MODAL_CLOSE_ID
#                                 ),

#                                 variant="subtle",

#                                 color="gray",

#                                 radius=0,

#                                 size="lg",

#                                 children=DashIconify(
#                                     icon=(
#                                         "solar:"
#                                         "close-circle-linear"
#                                     ),

#                                     width=19,
#                                 ),
#                             ),
#                         ],
#                     ),
#                 ],
#             ),

#             # =========================================================
#             # INFO
#             # =========================================================

#             html.Div(
#                 style={
#                     "padding": (
#                         "8px 14px 0 14px"
#                     ),

#                     "fontSize": (
#                         "10px"
#                     ),

#                     "color": (
#                         COLORS[
#                             "muted"
#                         ]
#                     ),
#                 },

#                 children=(
#                     "Карточки отсортированы: "
#                     "сначала критичные договоры, "
#                     "затем остальные замечания."
#                 ),
#             ),

#             # =========================================================
#             # HORIZONTAL CARDS
#             # =========================================================

#             html.Div(
#                 id=ALERTS_LIST_ID,

#                 children=[],

#                 style={
#                     # ОДНА СТРОКА

#                     "display": (
#                         "flex"
#                     ),

#                     "flexWrap": (
#                         "nowrap"
#                     ),

#                     "alignItems": (
#                         "stretch"
#                     ),

#                     "gap": "8px",

#                     # HORIZONTAL SCROLL

#                     "overflowX": (
#                         "auto"
#                     ),

#                     "overflowY": (
#                         "hidden"
#                     ),

#                     "padding": (
#                         "10px 14px 16px 14px"
#                     ),

#                     "scrollBehavior": (
#                         "smooth"
#                     ),
#                 },
#             ),
#         ],
#     )


# # =====================================================================
# # CALLBACKS
# # =====================================================================


# def register_automatic_alerts_callbacks(
#     app,
# ):
#     # =================================================================
#     # Открыть / закрыть модалку
#     # =================================================================

#     @app.callback(
#         Output(
#             ALERTS_MODAL_ID,
#             "opened",
#         ),

#         Input(
#             ALERTS_BUTTON_ID,
#             "n_clicks",
#         ),

#         Input(
#             ALERTS_MODAL_CLOSE_ID,
#             "n_clicks",
#         ),

#         State(
#             ALERTS_MODAL_ID,
#             "opened",
#         ),

#         prevent_initial_call=True,
#     )
#     def toggle_alerts_modal(
#         open_clicks,
#         close_clicks,
#         opened,
#     ):
#         """
#         Любой клик:
#         - по кнопке "Требует внимания" открывает закрытую модалку;
#         - по крестику закрывает открытую.

#         ctx здесь специально не используем,
#         т.к. django_plotly_dash не всегда корректно
#         прокидывает callback_context.
#         """

#         return not bool(opened)
#     # =================================================================
#     # Данные блока
#     # =================================================================

#     @app.callback(
#         Output(
#             ALERTS_LIST_ID,
#             "children",
#         ),

#         Output(
#             ALERTS_COUNT_ID,
#             "children",
#         ),

#         Output(
#             ALERTS_CRITICAL_COUNT_ID,
#             "children",
#         ),

#         Output(
#             ALERTS_WARNING_COUNT_ID,
#             "children",
#         ),

#         Output(
#             ALERTS_BUTTON_COUNT_ID,
#             "children",
#         ),

#         Input(
#             DATA_SIGNAL_ID,
#             "data",
#         ),

#         Input(
#             REPORT_DATE_ID,
#             "value",
#         ),
#     )
#     def update_alerts(
#         _signal,
#         report_date,
#     ):
#         # =============================================================
#         # Нет даты
#         # =============================================================

#         if not report_date:
#             return (
#                 [
#                     html.Div(
#                         "Нет данных",

#                         style={
#                             "padding": (
#                                 "20px"
#                             ),

#                             "fontSize": (
#                                 "11px"
#                             ),

#                             "color": (
#                                 COLORS[
#                                     "muted"
#                                 ]
#                             ),
#                         },
#                     )
#                 ],

#                 "Нет данных",

#                 "0",

#                 "0",

#                 "0",
#             )

#         # =============================================================
#         # Snapshot
#         # =============================================================

#         snapshot = (
#             get_management_snapshot(
#                 str(
#                     report_date
#                 )[:10]
#             )
#         )

#         # =============================================================
#         # Alerts
#         # =============================================================

#         alerts = build_alerts(
#             snapshot,
#             str(
#                 report_date
#             )[:10],
#         )

#         # =============================================================
#         # Нет замечаний
#         # =============================================================

#         if not alerts:
#             return (
#                 [
#                     html.Div(
#                         style={
#                             "display": (
#                                 "flex"
#                             ),

#                             "alignItems": (
#                                 "center"
#                             ),

#                             "justifyContent": (
#                                 "center"
#                             ),

#                             "gap": "6px",

#                             "width": (
#                                 "100%"
#                             ),

#                             "padding": (
#                                 "24px"
#                             ),
#                         },

#                         children=[
#                             DashIconify(
#                                 icon=(
#                                     "solar:"
#                                     "check-circle-linear"
#                                 ),

#                                 width=16,

#                                 color=(
#                                     COLORS.get(
#                                         "green",
#                                         "#15803D",
#                                     )
#                                 ),
#                             ),

#                             html.Span(
#                                 (
#                                     "Договоров, "
#                                     "требующих внимания, "
#                                     "не найдено"
#                                 ),

#                                 style={
#                                     "fontSize": (
#                                         "11px"
#                                     ),

#                                     "color": (
#                                         COLORS[
#                                             "muted"
#                                         ]
#                                     ),
#                                 },
#                             ),
#                         ],
#                     )
#                 ],

#                 "Нет договоров с замечаниями",

#                 "0",

#                 "0",

#                 "0",
#             )

#         # =============================================================
#         # Counters
#         # =============================================================

#         critical_count = sum(
#             1
#             for alert in alerts
#             if (
#                 alert.get(
#                     "severity"
#                 )
#                 == "critical"
#             )
#         )

#         warning_count = sum(
#             1
#             for alert in alerts
#             if (
#                 alert.get(
#                     "severity"
#                 )
#                 == "warning"
#             )
#         )

#         total_count = len(
#             alerts
#         )

#         count_text = (
#             f"{total_count} "
#             f"{_plural_contracts(total_count)} "
#             "требуют внимания"
#         )

#         # =============================================================
#         # Return
#         # =============================================================

#         return (
#             [
#                 _alert_card(
#                     alert
#                 )
#                 for alert
#                 in alerts
#             ],

#             count_text,

#             str(
#                 critical_count
#             ),

#             str(
#                 warning_count
#             ),

#             str(
#                 total_count
#             ),
#         )




# gear/app/loans/automatic_alerts.py

from __future__ import annotations

from datetime import date

import dash_mantine_components as dmc
import pandas as pd
from dash import Input, Output, html, State
from dash_iconify import DashIconify

from .config import COLORS
from .ids import DATA_SIGNAL_ID, REPORT_DATE_ID
from .management_common import (
    get_document_counts,
    get_management_snapshot,
)


# =====================================================================
# IDs
# =====================================================================

ALERTS_BUTTON_ID = "loans-alerts-button"
ALERTS_BUTTON_COUNT_ID = "loans-alerts-button-count"

ALERTS_MODAL_ID = "loans-alerts-modal"
ALERTS_MODAL_CLOSE_ID = "loans-alerts-modal-close"

ALERTS_LIST_ID = "loans-management-alerts-list"

ALERTS_COUNT_ID = "loans-management-alerts-count"

ALERTS_CRITICAL_COUNT_ID = (
    "loans-management-alerts-critical-count"
)

ALERTS_WARNING_COUNT_ID = (
    "loans-management-alerts-warning-count"
)


# =====================================================================
# HELPERS
# =====================================================================


def _as_date(value):
    parsed = pd.to_datetime(
        value,
        errors="coerce",
    )

    if pd.isna(parsed):
        return None

    return parsed.date()


def _safe_float(
    value,
    default: float = 0.0,
) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return default


def _safe_int(
    value,
    default: int = 0,
) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return default


def _format_date(value) -> str:
    parsed = _as_date(value)

    if not parsed:
        return "без даты"

    return parsed.strftime(
        "%d.%m.%Y"
    )


def _format_money(
    value,
) -> str:
    try:
        return (
            f"{float(value or 0):,.2f}"
            .replace(",", " ")
        )
    except (TypeError, ValueError):
        return "0,00"


def _format_money_short(
    value,
) -> str:
    """
    Компактное отображение суммы.

    200 000 000 -> 200,00 млн
    13 640 400  -> 13,64 млн
    571 887     -> 571,89 тыс.
    """

    value = _safe_float(value)
    abs_value = abs(value)

    if abs_value >= 1_000_000_000:
        return (
            f"{value / 1_000_000_000:,.2f}"
            .replace(",", " ")
            + " млрд"
        )

    if abs_value >= 1_000_000:
        return (
            f"{value / 1_000_000:,.2f}"
            .replace(",", " ")
            + " млн"
        )

    if abs_value >= 100_000:
        return (
            f"{value / 1_000:,.2f}"
            .replace(",", " ")
            + " тыс."
        )

    return _format_money(value)


def _plural_contracts(
    value: int,
) -> str:
    value = abs(int(value))

    last_two = value % 100
    last_one = value % 10

    if 11 <= last_two <= 14:
        return "договоров"

    if last_one == 1:
        return "договор"

    if 2 <= last_one <= 4:
        return "договора"

    return "договоров"


def _plural_files(
    value: int,
) -> str:
    value = abs(int(value))

    last_two = value % 100
    last_one = value % 10

    if 11 <= last_two <= 14:
        return "файлов"

    if last_one == 1:
        return "файл"

    if 2 <= last_one <= 4:
        return "файла"

    return "файлов"


# =====================================================================
# BUILD ALERTS
# =====================================================================


def build_alerts(
    snapshot: pd.DataFrame,
    report_date: str,
) -> list[dict]:
    """
    Одна карточка = один договор.

    Критично:
    - договор просрочен;
    - до погашения <= 7 дней.

    Проверить:
    - до погашения <= 30 дней;
    - нет даты погашения;
    - нет документов;
    - ставка <= 0.

    ВАЖНО:
    документы проверяем по ВСЕМ договорам,
    даже если долг уже погашен.
    """

    report = (
        _as_date(report_date)
        or date.today()
    )

    if snapshot.empty:
        return []

    work = snapshot.copy()

    # =================================================================
    # Фактическое количество документов
    # =================================================================

    contract_ids = [
        int(x)
        for x in work[
            "contract_id"
        ]
        .dropna()
        .unique()
        .tolist()
    ]

    docs = get_document_counts(
        contract_ids
    )

    if not docs.empty:
        work = work.merge(
            docs,
            how="left",
            on="contract_id",
            suffixes=(
                "",
                "_actual",
            ),
        )

        if (
            "documents_count_actual"
            in work.columns
        ):
            work[
                "documents_count"
            ] = (
                work[
                    "documents_count_actual"
                ]
                .fillna(
                    work.get(
                        "documents_count",
                        0,
                    )
                )
            )

    # =================================================================
    # Проверка договоров
    # =================================================================

    alerts = []

    for row in work.to_dict(
        "records"
    ):
        contract_id = row.get(
            "contract_id"
        )

        counterparty = (
            row.get(
                "counterparty_name"
            )
            or "Контрагент не указан"
        )

        number = (
            row.get(
                "contract_number"
            )
            or "б/н"
        )

        contract_date = _as_date(
            row.get(
                "contract_date"
            )
        )

        maturity = _as_date(
            row.get(
                "repayment_date"
            )
        )

        debt = _safe_float(
            row.get(
                "total_debt"
            )
        )

        principal_debt = _safe_float(
            row.get(
                "ending_balance"
            )
        )

        interest_debt = _safe_float(
            row.get(
                "interest_balance"
            )
        )

        rate = _safe_float(
            row.get(
                "rate"
            )
        )

        documents_count = _safe_int(
            row.get(
                "documents_count"
            )
        )

        currency = (
            row.get(
                "currency"
            )
            or ""
        )
        loan_direction = str(
            row.get("loan_direction")
            or "unknown"
        )
        direction_label = (
            "Мы должны"
            if loan_direction == "borrowed"
            else (
                "Нам должны"
                if loan_direction == "issued"
                else "Направление не определено"
            )
        )
        maturity_action = (
            "Платёж"
            if loan_direction == "borrowed"
            else "Ожидаемое поступление"
        )
        overdue_title = (
            "Просрочена наша оплата"
            if loan_direction == "borrowed"
            else "Просрочен возврат нам"
        )

        issues = []

        # =============================================================
        # СРОК ПОГАШЕНИЯ
        # Только по договорам, где реально есть долг.
        # =============================================================

        if debt > 0.01:

            if maturity:
                days_to_maturity = (
                    maturity
                    - report
                ).days

                # -----------------------------------------------------
                # Просрочено
                # -----------------------------------------------------

                if days_to_maturity < 0:
                    issues.append(
                        {
                            "severity": (
                                "critical"
                            ),

                            "icon": (
                                "solar:"
                                "danger-circle-linear"
                            ),

                            "title": (
                                f"{overdue_title} "
                                f"на "
                                f"{abs(days_to_maturity)} "
                                "дн."
                            ),

                            "text": (
                                "Дата погашения "
                                f"{maturity.strftime('%d.%m.%Y')}"
                            ),
                        }
                    )

                # -----------------------------------------------------
                # До 7 дней
                # -----------------------------------------------------

                elif days_to_maturity <= 7:
                    issues.append(
                        {
                            "severity": (
                                "critical"
                            ),

                            "icon": (
                                "solar:"
                                "calendar-minimalistic-linear"
                            ),

                            "title": (
                                f"{maturity_action} "
                                f"через "
                                f"{days_to_maturity} "
                                "дн."
                            ),

                            "text": (
                                "Дата погашения "
                                f"{maturity.strftime('%d.%m.%Y')}"
                            ),
                        }
                    )

                # -----------------------------------------------------
                # До 30 дней
                # -----------------------------------------------------

                elif days_to_maturity <= 30:
                    issues.append(
                        {
                            "severity": (
                                "warning"
                            ),

                            "icon": (
                                "solar:"
                                "calendar-linear"
                            ),

                            "title": (
                                f"{maturity_action} "
                                f"через "
                                f"{days_to_maturity} "
                                "дн."
                            ),

                            "text": (
                                "Дата погашения "
                                f"{maturity.strftime('%d.%m.%Y')}"
                            ),
                        }
                    )

            else:
                issues.append(
                    {
                        "severity": (
                            "warning"
                        ),

                        "icon": (
                            "solar:"
                            "calendar-search-linear"
                        ),

                        "title": (
                            "Не указана "
                            "дата погашения"
                        ),

                        "text": (
                            "Невозможно определить "
                            "срок возврата займа."
                        ),
                    }
                )

        # =============================================================
        # ДОКУМЕНТЫ
        #
        # Проверяем ВСЕ договоры,
        # независимо от текущего долга.
        # =============================================================

        if documents_count <= 0:
            issues.append(
                {
                    "severity": (
                        "warning"
                    ),

                    "icon": (
                        "solar:"
                        "folder-error-linear"
                    ),

                    "title": (
                        "Нет документов"
                    ),

                    "text": (
                        "По договору не найден "
                        "ни один загруженный файл."
                    ),
                }
            )

        # =============================================================
        # СТАВКА
        # =============================================================

        if (
            debt > 0.01
            and rate <= 0
        ):
            issues.append(
                {
                    "severity": (
                        "warning"
                    ),

                    "icon": (
                        "solar:"
                        "percent-circle-linear"
                    ),

                    "title": (
                        "Ставка не задана"
                    ),

                    "text": (
                        "Проверьте процентную "
                        "ставку договора."
                    ),
                }
            )

        # =============================================================
        # Нет замечаний
        # =============================================================

        if not issues:
            continue

        # =============================================================
        # Общая критичность карточки
        # =============================================================

        has_critical = any(
            issue.get(
                "severity"
            )
            == "critical"
            for issue in issues
        )

        severity = (
            "critical"
            if has_critical
            else "warning"
        )

        alerts.append(
            {
                "contract_id": (
                    contract_id
                ),

                "counterparty_name": (
                    counterparty
                ),

                "contract_number": (
                    number
                ),

                "contract_date": (
                    contract_date
                ),

                "repayment_date": (
                    maturity
                ),

                "currency": (
                    currency
                ),

                "loan_direction": loan_direction,
                "loan_direction_label": direction_label,

                "total_debt": (
                    debt
                ),

                "principal_debt": (
                    principal_debt
                ),

                "interest_debt": (
                    interest_debt
                ),

                "documents_count": (
                    documents_count
                ),

                "severity": (
                    severity
                ),

                "issues": (
                    issues
                ),
            }
        )

    # =================================================================
    # Сортировка
    #
    # 1. критичные;
    # 2. предупреждения;
    # 3. внутри группы — больший долг выше.
    # =================================================================

    severity_rank = {
        "critical": 0,
        "warning": 1,
    }

    alerts.sort(
        key=lambda x: (
            severity_rank.get(
                x.get(
                    "severity"
                ),
                9,
            ),

            -_safe_float(
                x.get(
                    "total_debt"
                )
            ),

            (
                x.get(
                    "counterparty_name"
                )
                or ""
            ),
        )
    )

    return alerts


# =====================================================================
# ISSUE ROW
# =====================================================================


def _issue_row(
    issue: dict,
):
    severity = issue.get(
        "severity",
        "warning",
    )

    if severity == "critical":
        color = COLORS.get(
            "red",
            "#B91C1C",
        )
    else:
        color = COLORS.get(
            "orange",
            "#C2410C",
        )

    return html.Div(
        style={
            "display": "grid",

            "gridTemplateColumns": (
                "16px minmax(0, 1fr)"
            ),

            "gap": "6px",

            "alignItems": (
                "start"
            ),
        },

        children=[
            DashIconify(
                icon=issue.get(
                    "icon",
                    (
                        "solar:"
                        "danger-triangle-linear"
                    ),
                ),

                width=13,
                height=13,

                color=color,

                style={
                    "marginTop": "1px",
                },
            ),

            html.Div(
                style={
                    "minWidth": 0,
                },

                children=[
                    html.Div(
                        issue.get(
                            "title",
                            "",
                        ),

                        style={
                            "fontSize": (
                                "11px"
                            ),

                            "fontWeight": (
                                700
                            ),

                            "lineHeight": (
                                "14px"
                            ),

                            "color": (
                                COLORS[
                                    "text"
                                ]
                            ),
                        },
                    ),

                    html.Div(
                        issue.get(
                            "text",
                            "",
                        ),

                        style={
                            "marginTop": (
                                "1px"
                            ),

                            "fontSize": (
                                "10px"
                            ),

                            "lineHeight": (
                                "13px"
                            ),

                            "color": (
                                COLORS[
                                    "muted"
                                ]
                            ),
                        },
                    ),
                ],
            ),
        ],
    )


# =====================================================================
# SMALL METRIC
# =====================================================================


def _metric(
    *,
    icon: str,
    value: str,
    strong: bool = False,
):
    return html.Div(
        style={
            "display": "flex",

            "alignItems": (
                "center"
            ),

            "gap": "4px",

            "whiteSpace": (
                "nowrap"
            ),
        },

        children=[
            DashIconify(
                icon=icon,

                width=12,
                height=12,

                color=COLORS[
                    "muted"
                ],
            ),

            html.Span(
                value,

                style={
                    "fontSize": (
                        "10px"
                    ),

                    "fontWeight": (
                        700
                        if strong
                        else 500
                    ),

                    "color": (
                        COLORS[
                            "text"
                        ]
                        if strong
                        else COLORS[
                            "muted"
                        ]
                    ),

                    "fontVariantNumeric": (
                        "tabular-nums"
                    ),
                },
            ),
        ],
    )


# =====================================================================
# CONTRACT CARD
# =====================================================================


def _alert_card(
    alert: dict,
):
    severity = alert.get(
        "severity",
        "warning",
    )

    # =================================================================
    # Цвета
    # =================================================================

    if severity == "critical":

        accent = COLORS.get(
            "red",
            "#B91C1C",
        )

        background = (
            "#FFFBFB"
        )

        badge_background = (
            "#FDEEEE"
        )

        badge_text = (
            "Критично"
        )

        badge_icon = (
            "solar:"
            "danger-circle-linear"
        )

    else:

        accent = COLORS.get(
            "orange",
            "#C2410C",
        )

        background = (
            "#FFFCF8"
        )

        badge_background = (
            "#FFF3E6"
        )

        badge_text = (
            "Проверить"
        )

        badge_icon = (
            "solar:"
            "danger-triangle-linear"
        )

    # =================================================================
    # Данные
    # =================================================================

    counterparty = (
        alert.get(
            "counterparty_name"
        )
        or "Контрагент не указан"
    )

    number = (
        alert.get(
            "contract_number"
        )
        or "б/н"
    )

    contract_date = _format_date(
        alert.get(
            "contract_date"
        )
    )

    debt = _safe_float(
        alert.get(
            "total_debt"
        )
    )

    principal_debt = _safe_float(
        alert.get(
            "principal_debt"
        )
    )

    interest_debt = _safe_float(
        alert.get(
            "interest_debt"
        )
    )

    documents_count = _safe_int(
        alert.get(
            "documents_count"
        )
    )

    currency = (
        alert.get(
            "currency"
        )
        or ""
    )

    issues = (
        alert.get(
            "issues"
        )
        or []
    )

    # =================================================================
    # Нижние метрики
    # =================================================================

    metrics = []

    if debt > 0.01:
        metrics.append(
            _metric(
                icon=(
                    "solar:"
                    "wallet-money-linear"
                ),

                value=(
                    f"{_format_money_short(debt)} "
                    f"{currency}"
                ),

                strong=True,
            )
        )

    # Тело показываем отдельно,
    # только если общий долг отличается от тела.

    if (
        principal_debt > 0.01
        and abs(
            debt
            - principal_debt
        ) > 0.01
    ):
        metrics.append(
            _metric(
                icon=(
                    "solar:"
                    "banknote-2-linear"
                ),

                value=(
                    "тело "
                    f"{_format_money_short(principal_debt)}"
                ),
            )
        )

    # Нулевые проценты не показываем.

    if interest_debt > 0.01:
        metrics.append(
            _metric(
                icon=(
                    "solar:"
                    "percent-circle-linear"
                ),

                value=(
                    "проц. "
                    f"{_format_money_short(interest_debt)}"
                ),
            )
        )

    metrics.append(
        _metric(
            icon=(
                "solar:"
                "paperclip-linear"
            ),

            value=(
                f"{documents_count} "
                f"{_plural_files(documents_count)}"
            ),
        )
    )

    # =================================================================
    # CARD
    # =================================================================

    return html.Div(
        style={
            # КЛЮЧЕВО:
            # карточка имеет фиксированную ширину
            # и не растягивается.

            "flex": (
                "0 0 310px"
            ),

            "width": (
                "310px"
            ),

            "minWidth": (
                "310px"
            ),

            "display": (
                "grid"
            ),

            "gridTemplateColumns": (
                "3px minmax(0, 1fr)"
            ),

            "backgroundColor": (
                background
            ),

            "border": (
                f"1px solid "
                f"{COLORS['border']}"
            ),

            "minHeight": (
                "180px"
            ),
        },

        children=[
            # =========================================================
            # Цветная вертикальная линия
            # =========================================================

            html.Div(
                style={
                    "backgroundColor": (
                        accent
                    ),
                },
            ),

            # =========================================================
            # CONTENT
            # =========================================================

            html.Div(
                style={
                    "display": (
                        "flex"
                    ),

                    "flexDirection": (
                        "column"
                    ),

                    "padding": (
                        "10px"
                    ),

                    "minWidth": 0,
                },

                children=[
                    # =================================================
                    # Верх карточки
                    # =================================================

                    html.Div(
                        style={
                            "display": (
                                "flex"
                            ),

                            "alignItems": (
                                "flex-start"
                            ),

                            "justifyContent": (
                                "space-between"
                            ),

                            "gap": "8px",
                        },

                        children=[
                            # =========================================
                            # Контрагент
                            # =========================================

                            html.Div(
                                style={
                                    "minWidth": 0,
                                    "flex": 1,
                                },

                                children=[
                                    html.Div(
                                        counterparty,

                                        title=(
                                            counterparty
                                        ),

                                        style={
                                            "fontSize": (
                                                "11px"
                                            ),

                                            "fontWeight": (
                                                700
                                            ),

                                            "lineHeight": (
                                                "14px"
                                            ),

                                            "color": (
                                                COLORS[
                                                    "text"
                                                ]
                                            ),

                                            "overflow": (
                                                "hidden"
                                            ),

                                            "textOverflow": (
                                                "ellipsis"
                                            ),

                                            "whiteSpace": (
                                                "nowrap"
                                            ),
                                        },
                                    ),

                                    html.Div(
                                        (
                                            f"Договор № {number} "
                                            f"от {contract_date}"
                                        ),

                                        style={
                                            "marginTop": (
                                                "2px"
                                            ),

                                            "fontSize": (
                                                "9px"
                                            ),

                                            "lineHeight": (
                                                "12px"
                                            ),

                                            "color": (
                                                COLORS[
                                                    "muted"
                                                ]
                                            ),
                                        },
                                    ),
                                ],
                            ),

                            # =========================================
                            # Badge
                            # =========================================

                            html.Div(
                                style={
                                    "display": (
                                        "flex"
                                    ),

                                    "alignItems": (
                                        "center"
                                    ),

                                    "gap": "3px",

                                    "padding": (
                                        "3px 6px"
                                    ),

                                    "backgroundColor": (
                                        badge_background
                                    ),

                                    "whiteSpace": (
                                        "nowrap"
                                    ),

                                    "color": (
                                        accent
                                    ),
                                },

                                children=[
                                    DashIconify(
                                        icon=(
                                            badge_icon
                                        ),

                                        width=11,
                                        height=11,
                                    ),

                                    html.Span(
                                        badge_text,

                                        style={
                                            "fontSize": (
                                                "9px"
                                            ),

                                            "fontWeight": (
                                                700
                                            ),
                                        },
                                    ),
                                ],
                            ),
                        ],
                    ),

                    # =================================================
                    # Issues
                    # =================================================

                    html.Div(
                        style={
                            "display": (
                                "flex"
                            ),

                            "flexDirection": (
                                "column"
                            ),

                            "gap": "6px",

                            "marginTop": (
                                "8px"
                            ),

                            "paddingTop": (
                                "7px"
                            ),

                            "borderTop": (
                                f"1px solid "
                                f"{COLORS['border']}"
                            ),

                            # проблемы занимают свободное место,
                            # чтобы низ карточек был примерно на одном уровне

                            "flex": 1,
                        },

                        children=[
                            _issue_row(
                                issue
                            )
                            for issue
                            in issues
                        ],
                    ),

                    # =================================================
                    # Metrics
                    # =================================================

                    html.Div(
                        style={
                            "display": (
                                "flex"
                            ),

                            "alignItems": (
                                "center"
                            ),

                            "gap": "10px",

                            "flexWrap": (
                                "wrap"
                            ),

                            "marginTop": (
                                "8px"
                            ),

                            "paddingTop": (
                                "7px"
                            ),

                            "borderTop": (
                                f"1px solid "
                                f"{COLORS['border']}"
                            ),
                        },

                        children=metrics,
                    ),
                ],
            ),
        ],
    )


# =====================================================================
# HEADER COUNTER
# =====================================================================


def _header_counter(
    *,
    icon: str,
    label: str,
    value_id: str,
    color: str,
    background: str,
):
    return html.Div(
        style={
            "height": "28px",

            "display": (
                "flex"
            ),

            "alignItems": (
                "center"
            ),

            "gap": "4px",

            "padding": (
                "0 7px"
            ),

            "backgroundColor": (
                background
            ),

            "border": (
                f"1px solid "
                f"{COLORS['border']}"
            ),
        },

        children=[
            DashIconify(
                icon=icon,

                width=12,
                height=12,

                color=color,
            ),

            html.Span(
                label,

                style={
                    "fontSize": "9px",
                    "color": color,
                },
            ),

            html.Span(
                id=value_id,

                children="0",

                style={
                    "fontSize": "9px",
                    "fontWeight": 700,
                    "color": color,
                },
            ),
        ],
    )


# =====================================================================
# BUTTON IN APPLICATION HEADER
# =====================================================================


def build_alerts_button():
    """
    Кнопка в верхней панели приложения.
    """

    return dmc.Button(
        id=ALERTS_BUTTON_ID,

        radius=0,

        variant="outline",

        color="red",

        h=34,

        px=10,

        leftSection=DashIconify(
            icon=(
                "solar:"
                "shield-warning-linear"
            ),

            width=15,
        ),

        children=[
            html.Span(
                "Требует внимания"
            ),

            html.Span(
                id=(
                    ALERTS_BUTTON_COUNT_ID
                ),

                children="0",

                style={
                    "marginLeft": (
                        "6px"
                    ),

                    "fontWeight": (
                        700
                    ),
                },
            ),
        ],

        styles={
            "root": {
                "fontSize": "11px",
                "fontWeight": 600,
            },
        },
    )


# =====================================================================
# MODAL
# =====================================================================


def build_alerts_modal():
    """
    Модальное окно.

    Договоры идут в ОДНУ горизонтальную строку.
    При большом количестве появляется горизонтальный scroll.
    """

    return dmc.Modal(
        id=ALERTS_MODAL_ID,

        opened=False,

        centered=True,

        size="90%",

        radius=0,

        padding=0,

        # Используем собственную кнопку закрытия,
        # чтобы состояние opened надёжно управлялось callback.
        withCloseButton=False,

        styles={
            "content": {
                "maxWidth": "1500px",
            },

            "body": {
                "padding": "0",
            },

            "header": {
                "display": "none",
            },
        },

        children=[
            # =========================================================
            # HEADER
            # =========================================================

            html.Div(
                style={
                    "minHeight": (
                        "56px"
                    ),

                    "display": (
                        "flex"
                    ),

                    "alignItems": (
                        "center"
                    ),

                    "justifyContent": (
                        "space-between"
                    ),

                    "gap": "14px",

                    "padding": (
                        "10px 14px"
                    ),

                    "borderBottom": (
                        f"1px solid "
                        f"{COLORS['border']}"
                    ),

                    "backgroundColor": (
                        COLORS["white"]
                    ),
                },

                children=[
                    # =================================================
                    # LEFT
                    # =================================================

                    html.Div(
                        style={
                            "display": (
                                "flex"
                            ),

                            "alignItems": (
                                "center"
                            ),

                            "gap": "8px",
                        },

                        children=[
                            html.Div(
                                style={
                                    "width": "32px",
                                    "height": "32px",

                                    "display": (
                                        "flex"
                                    ),

                                    "alignItems": (
                                        "center"
                                    ),

                                    "justifyContent": (
                                        "center"
                                    ),

                                    "backgroundColor": (
                                        "#F8FAF9"
                                    ),

                                    "border": (
                                        f"1px solid "
                                        f"{COLORS['border']}"
                                    ),
                                },

                                children=[
                                    DashIconify(
                                        icon=(
                                            "solar:"
                                            "shield-warning-linear"
                                        ),

                                        width=17,

                                        color=(
                                            COLORS[
                                                "text"
                                            ]
                                        ),
                                    ),
                                ],
                            ),

                            html.Div(
                                children=[
                                    html.Div(
                                        (
                                            "Требует "
                                            "внимания"
                                        ),

                                        style={
                                            "fontSize": (
                                                "15px"
                                            ),

                                            "fontWeight": (
                                                700
                                            ),

                                            "lineHeight": (
                                                "18px"
                                            ),

                                            "color": (
                                                COLORS[
                                                    "text"
                                                ]
                                            ),
                                        },
                                    ),

                                    html.Div(
                                        id=(
                                            ALERTS_COUNT_ID
                                        ),

                                        children=(
                                            "Нет замечаний"
                                        ),

                                        style={
                                            "marginTop": (
                                                "2px"
                                            ),

                                            "fontSize": (
                                                "10px"
                                            ),

                                            "color": (
                                                COLORS[
                                                    "muted"
                                                ]
                                            ),
                                        },
                                    ),
                                ],
                            ),
                        ],
                    ),

                    # =================================================
                    # RIGHT
                    # =================================================

                    html.Div(
                        style={
                            "display": (
                                "flex"
                            ),

                            "alignItems": (
                                "center"
                            ),

                            "gap": "6px",
                        },

                        children=[
                            _header_counter(
                                icon=(
                                    "solar:"
                                    "danger-circle-linear"
                                ),

                                label=(
                                    "Критично"
                                ),

                                value_id=(
                                    ALERTS_CRITICAL_COUNT_ID
                                ),

                                color=(
                                    COLORS.get(
                                        "red",
                                        "#B91C1C",
                                    )
                                ),

                                background=(
                                    "#FFF5F5"
                                ),
                            ),

                            _header_counter(
                                icon=(
                                    "solar:"
                                    "danger-triangle-linear"
                                ),

                                label=(
                                    "Проверить"
                                ),

                                value_id=(
                                    ALERTS_WARNING_COUNT_ID
                                ),

                                color=(
                                    COLORS.get(
                                        "orange",
                                        "#C2410C",
                                    )
                                ),

                                background=(
                                    "#FFF8F0"
                                ),
                            ),

                            dmc.ActionIcon(
                                id=(
                                    ALERTS_MODAL_CLOSE_ID
                                ),

                                variant="subtle",

                                color="gray",

                                radius=0,

                                size="lg",

                                children=DashIconify(
                                    icon=(
                                        "solar:"
                                        "close-circle-linear"
                                    ),

                                    width=19,
                                ),
                            ),
                        ],
                    ),
                ],
            ),

            # =========================================================
            # INFO
            # =========================================================

            html.Div(
                style={
                    "padding": (
                        "8px 14px 0 14px"
                    ),

                    "fontSize": (
                        "10px"
                    ),

                    "color": (
                        COLORS[
                            "muted"
                        ]
                    ),
                },

                children=(
                    "Карточки отсортированы: "
                    "сначала критичные договоры, "
                    "затем остальные замечания."
                ),
            ),

            # =========================================================
            # HORIZONTAL CARDS
            # =========================================================

            html.Div(
                id=ALERTS_LIST_ID,

                children=[],

                style={
                    # ОДНА СТРОКА

                    "display": (
                        "flex"
                    ),

                    "flexWrap": (
                        "nowrap"
                    ),

                    "alignItems": (
                        "stretch"
                    ),

                    "gap": "8px",

                    # HORIZONTAL SCROLL

                    "overflowX": (
                        "auto"
                    ),

                    "overflowY": (
                        "hidden"
                    ),

                    "padding": (
                        "10px 14px 16px 14px"
                    ),

                    "scrollBehavior": (
                        "smooth"
                    ),
                },
            ),
        ],
    )


# =====================================================================
# CALLBACKS
# =====================================================================


def register_automatic_alerts_callbacks(
    app,
):
    # =================================================================
    # Открыть / закрыть модалку
    # =================================================================

    @app.callback(
        Output(
            ALERTS_MODAL_ID,
            "opened",
        ),

        Input(
            ALERTS_BUTTON_ID,
            "n_clicks",
        ),

        Input(
            ALERTS_MODAL_CLOSE_ID,
            "n_clicks",
        ),

        State(
            ALERTS_MODAL_ID,
            "opened",
        ),

        prevent_initial_call=True,
    )
    def toggle_alerts_modal(
        open_clicks,
        close_clicks,
        opened,
    ):
        """
        Любой клик:
        - по кнопке "Требует внимания" открывает закрытую модалку;
        - по крестику закрывает открытую.

        ctx здесь специально не используем,
        т.к. django_plotly_dash не всегда корректно
        прокидывает callback_context.
        """

        return not bool(opened)
    # =================================================================
    # Данные блока
    # =================================================================

    @app.callback(
        Output(
            ALERTS_LIST_ID,
            "children",
        ),

        Output(
            ALERTS_COUNT_ID,
            "children",
        ),

        Output(
            ALERTS_CRITICAL_COUNT_ID,
            "children",
        ),

        Output(
            ALERTS_WARNING_COUNT_ID,
            "children",
        ),

        Output(
            ALERTS_BUTTON_COUNT_ID,
            "children",
        ),

        Input(
            DATA_SIGNAL_ID,
            "data",
        ),

        Input(
            REPORT_DATE_ID,
            "value",
        ),
    )
    def update_alerts(
        _signal,
        report_date,
    ):
        # =============================================================
        # Нет даты
        # =============================================================

        if not report_date:
            return (
                [
                    html.Div(
                        "Нет данных",

                        style={
                            "padding": (
                                "20px"
                            ),

                            "fontSize": (
                                "11px"
                            ),

                            "color": (
                                COLORS[
                                    "muted"
                                ]
                            ),
                        },
                    )
                ],

                "Нет данных",

                "0",

                "0",

                "0",
            )

        # =============================================================
        # Snapshot
        # =============================================================

        snapshot = (
            get_management_snapshot(
                str(
                    report_date
                )[:10]
            )
        )

        # =============================================================
        # Alerts
        # =============================================================

        alerts = build_alerts(
            snapshot,
            str(
                report_date
            )[:10],
        )

        # =============================================================
        # Нет замечаний
        # =============================================================

        if not alerts:
            return (
                [
                    html.Div(
                        style={
                            "display": (
                                "flex"
                            ),

                            "alignItems": (
                                "center"
                            ),

                            "justifyContent": (
                                "center"
                            ),

                            "gap": "6px",

                            "width": (
                                "100%"
                            ),

                            "padding": (
                                "24px"
                            ),
                        },

                        children=[
                            DashIconify(
                                icon=(
                                    "solar:"
                                    "check-circle-linear"
                                ),

                                width=16,

                                color=(
                                    COLORS.get(
                                        "green",
                                        "#15803D",
                                    )
                                ),
                            ),

                            html.Span(
                                (
                                    "Договоров, "
                                    "требующих внимания, "
                                    "не найдено"
                                ),

                                style={
                                    "fontSize": (
                                        "11px"
                                    ),

                                    "color": (
                                        COLORS[
                                            "muted"
                                        ]
                                    ),
                                },
                            ),
                        ],
                    )
                ],

                "Нет договоров с замечаниями",

                "0",

                "0",

                "0",
            )

        # =============================================================
        # Counters
        # =============================================================

        critical_count = sum(
            1
            for alert in alerts
            if (
                alert.get(
                    "severity"
                )
                == "critical"
            )
        )

        warning_count = sum(
            1
            for alert in alerts
            if (
                alert.get(
                    "severity"
                )
                == "warning"
            )
        )

        total_count = len(
            alerts
        )

        count_text = (
            f"{total_count} "
            f"{_plural_contracts(total_count)} "
            "требуют внимания"
        )

        # =============================================================
        # Return
        # =============================================================

        return (
            [
                _alert_card(
                    alert
                )
                for alert
                in alerts
            ],

            count_text,

            str(
                critical_count
            ),

            str(
                warning_count
            ),

            str(
                total_count
            ),
        )