# # gear/app/loans/excel.py

# from __future__ import annotations

# from io import BytesIO

# import pandas as pd


# # =====================================================================
# # HELPERS
# # =====================================================================


# def _to_float(
#     value,
# ) -> float:
#     try:
#         if value is None:
#             return 0.0

#         return float(value)

#     except (
#         TypeError,
#         ValueError,
#     ):
#         return 0.0


# def _clean_text(
#     value,
# ) -> str:
#     """
#     Убирает технические значения,
#     которые могут приходить вместо текста.
#     """

#     if value is None:
#         return ""

#     text = str(value).strip()

#     if text in {
#         "",
#         "0",
#         "0.0",
#         "None",
#         "nan",
#         "NaN",
#     }:
#         return ""

#     return text


# def _trim_empty_rows_after_zero_adjustment(
#     work: pd.DataFrame,
# ) -> pd.DataFrame:
#     """
#     Сохраняет строку ручной корректировки, которой тело и проценты
#     были приведены к нулю, и удаляет последующие пустые календарные дни.

#     Обрезание выполняется только когда после такой корректировки нет:
#     - новых выдач;
#     - погашений тела;
#     - погашений процентов;
#     - новых ручных или фактических операций;
#     - повторного возникновения задолженности.

#     Поэтому будущая выдача, оплата или следующая корректировка
#     никогда не потеряются.
#     """

#     if work.empty:
#         return work

#     required_numeric_columns = [
#         "drawdown_amount",
#         "principal_repayment",
#         "interest_accrued",
#         "interest_repayment",
#         "ending_balance",
#         "interest_balance",
#         "total_debt",
#     ]

#     for column in required_numeric_columns:
#         if column not in work.columns:
#             work[column] = 0.0

#         work[column] = pd.to_numeric(
#             work[column],
#             errors="coerce",
#         ).fillna(0.0)

#     operation_description = (
#         work.get(
#             "operation_description",
#             pd.Series(
#                 "",
#                 index=work.index,
#                 dtype="object",
#             ),
#         )
#         .fillna("")
#         .astype(str)
#         .str.strip()
#     )

#     tolerance = 0.005

#     zero_balance_mask = (
#         work["ending_balance"].abs().le(
#             tolerance
#         )
#         & work["interest_balance"].abs().le(
#             tolerance
#         )
#         & work["total_debt"].abs().le(
#             tolerance
#         )
#     )

#     adjustment_mask = (
#         operation_description
#         .str.contains(
#             "Ручная корректировка",
#             case=False,
#             na=False,
#         )
#     )

#     closing_indexes = work.index[
#         zero_balance_mask
#         & adjustment_mask
#     ].tolist()

#     if not closing_indexes:
#         return work

#     # Проверяем корректировки от более поздней к более ранней.
#     # Берём первую подходящую дату, после которой действительно
#     # отсутствуют любые значимые операции.
#     for closing_index in reversed(
#         closing_indexes
#     ):
#         future_rows = work.loc[
#             work.index > closing_index
#         ].copy()

#         if future_rows.empty:
#             return (
#                 work.loc[
#                     work.index <= closing_index
#                 ]
#                 .copy()
#                 .reset_index(
#                     drop=True
#                 )
#             )

#         future_operation_description = (
#             future_rows.get(
#                 "operation_description",
#                 pd.Series(
#                     "",
#                     index=future_rows.index,
#                     dtype="object",
#                 ),
#             )
#             .fillna("")
#             .astype(str)
#             .str.strip()
#         )

#         future_has_cash_movements = (
#             future_rows[
#                 "drawdown_amount"
#             ].abs().gt(
#                 tolerance
#             ).any()
#             or future_rows[
#                 "principal_repayment"
#             ].abs().gt(
#                 tolerance
#             ).any()
#             or future_rows[
#                 "interest_repayment"
#             ].abs().gt(
#                 tolerance
#             ).any()
#         )

#         future_has_debt = (
#             future_rows[
#                 "ending_balance"
#             ].abs().gt(
#                 tolerance
#             ).any()
#             or future_rows[
#                 "interest_balance"
#             ].abs().gt(
#                 tolerance
#             ).any()
#             or future_rows[
#                 "total_debt"
#             ].abs().gt(
#                 tolerance
#             ).any()
#         )

#         future_has_operations = (
#             future_operation_description
#             .ne("")
#             .any()
#         )

#         if (
#             not future_has_cash_movements
#             and not future_has_debt
#             and not future_has_operations
#         ):
#             return (
#                 work.loc[
#                     work.index <= closing_index
#                 ]
#                 .copy()
#                 .reset_index(
#                     drop=True
#                 )
#             )

#     return work


# # =====================================================================
# # MAIN
# # =====================================================================


# def build_reconciliation_excel(
#     *,
#     loan: dict,
#     transactions: pd.DataFrame,
#     report_date: str,
# ) -> bytes:
#     """
#     Формирует профессиональную Excel-сверку
#     по выбранному договору займа.

#     ВАЖНО:
#     сверка строится строго на report_date.

#     Все строки после report_date:
#     - не участвуют в начислении процентов;
#     - не участвуют в погашениях;
#     - не влияют на состояние задолженности;
#     - не выводятся в истории операций.

#     Листы:
#     1. Сверка
#     2. Операции
#     """

#     output = BytesIO()

#     # =================================================================
#     # Дата сверки
#     # =================================================================

#     reconciliation_date = pd.to_datetime(
#         report_date,
#         errors="coerce",
#     )

#     reconciliation_date_text = (
#         reconciliation_date.strftime(
#             "%d.%m.%Y"
#         )
#         if pd.notna(
#             reconciliation_date
#         )
#         else "—"
#     )

#     # =================================================================
#     # Договор
#     # =================================================================

#     counterparty = (
#         loan.get(
#             "counterparty_name"
#         )
#         or "Без контрагента"
#     )

#     contract_number = (
#         loan.get(
#             "contract_number"
#         )
#         or "б/н"
#     )

#     contract_date = pd.to_datetime(
#         loan.get(
#             "contract_date"
#         ),
#         errors="coerce",
#     )

#     currency = (
#         loan.get(
#             "currency"
#         )
#         or ""
#     )

#     repayment_date = pd.to_datetime(
#         loan.get(
#             "repayment_date"
#         ),
#         errors="coerce",
#     )

#     rate = _to_float(
#         loan.get(
#             "rate"
#         )
#     )

#     # =================================================================
#     # Подготовка операций
#     # =================================================================

#     work = transactions.copy()

#     numeric_columns = [
#         "drawdown_amount",
#         "principal_repayment",
#         "interest_accrued",
#         "interest_repayment",
#         "ending_balance",
#         "interest_balance",
#         "total_debt",
#         "rate",
#     ]

#     if not work.empty:

#         work["date_from"] = pd.to_datetime(
#             work["date_from"],
#             errors="coerce",
#         )

#         for column in numeric_columns:

#             if column not in work.columns:
#                 work[column] = 0.0

#             work[column] = pd.to_numeric(
#                 work[column],
#                 errors="coerce",
#             ).fillna(0)

#         # =============================================================
#         # ВТОРАЯ ЗАЩИТА ОТ БУДУЩИХ СТРОК
#         #
#         # SQL уже должен отрезать будущее,
#         # но Excel дополнительно страхуем.
#         # =============================================================

#         if pd.notna(
#             reconciliation_date
#         ):
#             work = work[
#                 work["date_from"]
#                 <= reconciliation_date
#             ].copy()

#         work = (
#             work
#             .dropna(
#                 subset=[
#                     "date_from",
#                 ]
#             )
#             .sort_values(
#                 "date_from"
#             )
#             .reset_index(
#                 drop=True
#             )
#         )

#         # =============================================================
#         # НЕ ВЫВОДИМ ПУСТЫЕ ДНИ ПОСЛЕ ЗАКРЫВАЮЩЕЙ КОРРЕКТИРОВКИ
#         #
#         # Строка самой корректировки остаётся в Excel.
#         # Последующие календарные строки с нулевым долгом удаляются.
#         # =============================================================

#         work = _trim_empty_rows_after_zero_adjustment(
#             work
#         )

#     # =================================================================
#     # СОСТОЯНИЕ РАСЧЁТОВ НА ДАТУ СВЕРКИ
#     # =================================================================

#     if not work.empty:

#         # -------------------------------------------------------------
#         # Движения
#         # -------------------------------------------------------------

#         total_drawdown = float(
#             work[
#                 "drawdown_amount"
#             ].sum()
#         )

#         total_principal_repaid = float(
#             work[
#                 "principal_repayment"
#             ].sum()
#         )

#         total_interest_accrued = float(
#             work[
#                 "interest_accrued"
#             ].sum()
#         )

#         total_interest_repaid = float(
#             work[
#                 "interest_repayment"
#             ].sum()
#         )

#         # -------------------------------------------------------------
#         # Непогашенные начисленные проценты
#         #
#         # Это именно аналитический показатель:
#         # начислено - погашено.
#         #
#         # НЕ прибавляем его повторно к total_debt,
#         # потому что проценты могут быть уже
#         # капитализированы в задолженность.
#         # -------------------------------------------------------------

#         unpaid_accrued_interest = max(
#             total_interest_accrued
#             - total_interest_repaid,
#             0.0,
#         )

#         # -------------------------------------------------------------
#         # Последнее фактическое состояние
#         # на дату сверки
#         # -------------------------------------------------------------

#         last_row = work.iloc[-1]

#         ending_balance = _to_float(
#             last_row.get(
#                 "ending_balance"
#             )
#         )

#         interest_balance = _to_float(
#             last_row.get(
#                 "interest_balance"
#             )
#         )

#         total_debt = _to_float(
#             last_row.get(
#                 "total_debt"
#             )
#         )

#         last_rate = _to_float(
#             last_row.get(
#                 "rate"
#             )
#         )

#         if last_rate:
#             rate = last_rate

#         actual_state_date = (
#             last_row["date_from"]
#         )

#     else:

#         total_drawdown = 0.0
#         total_principal_repaid = 0.0

#         total_interest_accrued = 0.0
#         total_interest_repaid = 0.0
#         unpaid_accrued_interest = 0.0

#         ending_balance = 0.0
#         interest_balance = 0.0
#         total_debt = 0.0

#         actual_state_date = pd.NaT

#     actual_state_date_text = (
#         actual_state_date.strftime(
#             "%d.%m.%Y"
#         )
#         if pd.notna(
#             actual_state_date
#         )
#         else "—"
#     )

#     # =================================================================
#     # EXCEL
#     # =================================================================

#     with pd.ExcelWriter(
#         output,
#         engine="xlsxwriter",
#         datetime_format="dd.mm.yyyy",
#         date_format="dd.mm.yyyy",
#     ) as writer:

#         workbook = writer.book

#         # =============================================================
#         # Форматы
#         # =============================================================

#         title_format = (
#             workbook.add_format(
#                 {
#                     "font_name": "Arial",
#                     "font_size": 16,
#                     "bold": True,
#                     "font_color": "#111827",
#                     "align": "left",
#                     "valign": "vcenter",
#                 }
#             )
#         )

#         subtitle_format = (
#             workbook.add_format(
#                 {
#                     "font_name": "Arial",
#                     "font_size": 10,
#                     "font_color": "#6B7280",
#                     "align": "left",
#                     "valign": "vcenter",
#                 }
#             )
#         )

#         section_format = (
#             workbook.add_format(
#                 {
#                     "font_name": "Arial",
#                     "font_size": 10,
#                     "bold": True,
#                     "font_color": "#22312D",
#                     "bg_color": "#E7F1ED",

#                     "border": 1,
#                     "border_color": "#D9DEE2",

#                     "align": "left",
#                     "valign": "vcenter",
#                 }
#             )
#         )

#         label_format = (
#             workbook.add_format(
#                 {
#                     "font_name": "Arial",
#                     "font_size": 10,

#                     "font_color": "#6B7280",
#                     "bg_color": "#F8FAF9",

#                     "border": 1,
#                     "border_color": "#D9DEE2",

#                     "align": "left",
#                     "valign": "vcenter",
#                 }
#             )
#         )

#         value_format = (
#             workbook.add_format(
#                 {
#                     "font_name": "Arial",
#                     "font_size": 10,

#                     "font_color": "#111827",
#                     "bold": True,

#                     "border": 1,
#                     "border_color": "#D9DEE2",

#                     "align": "left",
#                     "valign": "vcenter",
#                 }
#             )
#         )

#         # -------------------------------------------------------------
#         # Денежный формат.
#         #
#         # Excel сам локализует разделители.
#         # -------------------------------------------------------------

#         money_format = (
#             workbook.add_format(
#                 {
#                     "font_name": "Arial",
#                     "font_size": 10,

#                     "num_format": (
#                         '#,##0.00;'
#                         '[Red]-#,##0.00'
#                     ),

#                     "border": 1,
#                     "border_color": "#D9DEE2",

#                     "align": "right",
#                     "valign": "vcenter",
#                 }
#             )
#         )

#         money_bold_format = (
#             workbook.add_format(
#                 {
#                     "font_name": "Arial",
#                     "font_size": 10,
#                     "bold": True,

#                     "font_color": "#22312D",
#                     "bg_color": "#E7F1ED",

#                     "num_format": (
#                         '#,##0.00;'
#                         '[Red]-#,##0.00'
#                     ),

#                     "border": 1,
#                     "border_color": "#D9DEE2",

#                     "align": "right",
#                     "valign": "vcenter",
#                 }
#             )
#         )

#         money_interest_format = (
#             workbook.add_format(
#                 {
#                     "font_name": "Arial",
#                     "font_size": 10,
#                     "bold": True,

#                     "font_color": "#B45309",
#                     "bg_color": "#FEF3E7",

#                     "num_format": (
#                         '#,##0.00;'
#                         '[Red]-#,##0.00'
#                     ),

#                     "border": 1,
#                     "border_color": "#D9DEE2",

#                     "align": "right",
#                     "valign": "vcenter",
#                 }
#             )
#         )

#         percent_format = (
#             workbook.add_format(
#                 {
#                     "font_name": "Arial",
#                     "font_size": 10,

#                     # rate уже 19.25,
#                     # поэтому знак % только дописываем.
#                     "num_format": '0.00"%"',

#                     "border": 1,
#                     "border_color": "#D9DEE2",

#                     "align": "right",
#                     "valign": "vcenter",
#                 }
#             )
#         )

#         date_format = (
#             workbook.add_format(
#                 {
#                     "font_name": "Arial",
#                     "font_size": 10,

#                     "num_format": "dd.mm.yyyy",

#                     "border": 1,
#                     "border_color": "#D9DEE2",

#                     "align": "left",
#                     "valign": "vcenter",
#                 }
#             )
#         )

#         header_format = (
#             workbook.add_format(
#                 {
#                     "font_name": "Arial",
#                     "font_size": 9,
#                     "bold": True,

#                     "font_color": "#FFFFFF",
#                     "bg_color": "#2F6656",

#                     "border": 1,
#                     "border_color": "#D9DEE2",

#                     "align": "center",
#                     "valign": "vcenter",

#                     "text_wrap": True,
#                 }
#             )
#         )

#         text_format = (
#             workbook.add_format(
#                 {
#                     "font_name": "Arial",
#                     "font_size": 9,

#                     "border": 1,
#                     "border_color": "#E5E7EB",

#                     "align": "left",
#                     "valign": "top",

#                     "text_wrap": True,
#                 }
#             )
#         )

#         # =============================================================
#         # ЛИСТ 1 — СВЕРКА
#         # =============================================================

#         sheet = workbook.add_worksheet(
#             "Сверка"
#         )

#         writer.sheets[
#             "Сверка"
#         ] = sheet

#         sheet.hide_gridlines(
#             2
#         )

#         sheet.set_landscape()

#         sheet.fit_to_pages(
#             1,
#             0,
#         )

#         sheet.set_margins(
#             left=0.35,
#             right=0.35,
#             top=0.45,
#             bottom=0.45,
#         )

#         # =============================================================
#         # Ширины
#         # =============================================================

#         sheet.set_column(
#             "A:A",
#             3,
#         )

#         # Длинные названия показателей
#         sheet.set_column(
#             "B:B",
#             41,
#         )

#         sheet.set_column(
#             "C:E",
#             22,
#         )

#         sheet.set_column(
#             "F:J",
#             20,
#         )

#         sheet.set_column(
#             "K:K",
#             12,
#         )

#         # =============================================================
#         # Заголовок
#         # =============================================================

#         sheet.set_row(
#             1,
#             24,
#         )

#         sheet.merge_range(
#             "B2:E2",
#             (
#                 "Сверка по договору займа "
#                 f"на {reconciliation_date_text}"
#             ),
#             title_format,
#         )

#         sheet.merge_range(
#             "B3:E3",
#             (
#                 f"{counterparty} · "
#                 f"договор № {contract_number}"
#             ),
#             subtitle_format,
#         )

#         # =============================================================
#         # Параметры договора
#         # =============================================================

#         sheet.merge_range(
#             "B5:E5",
#             "Параметры договора",
#             section_format,
#         )

#         info = [
#             (
#                 "Контрагент",
#                 counterparty,
#                 "text",
#             ),
#             (
#                 "Номер договора",
#                 contract_number,
#                 "text",
#             ),
#             (
#                 "Дата договора",
#                 contract_date,
#                 "date",
#             ),
#             (
#                 "Валюта",
#                 currency,
#                 "text",
#             ),
#             (
#                 "Процентная ставка",
#                 rate,
#                 "percent",
#             ),
#             (
#                 "Дата погашения",
#                 repayment_date,
#                 "date",
#             ),
#             (
#                 "Дата сверки",
#                 reconciliation_date,
#                 "date",
#             ),
#             (
#                 "Последнее состояние в базе",
#                 actual_state_date,
#                 "date",
#             ),
#         ]

#         row = 5

#         for (
#             label,
#             value,
#             value_type,
#         ) in info:

#             sheet.write(
#                 row,
#                 1,
#                 label,
#                 label_format,
#             )

#             if value_type == "percent":
#                 fmt = percent_format

#             elif value_type == "date":
#                 fmt = date_format

#             else:
#                 fmt = value_format

#             sheet.merge_range(
#                 row,
#                 2,
#                 row,
#                 4,
#                 "",
#                 fmt,
#             )

#             if (
#                 value_type == "date"
#                 and pd.notna(value)
#             ):

#                 sheet.write_datetime(
#                     row,
#                     2,
#                     value.to_pydatetime(),
#                     date_format,
#                 )

#             elif value_type == "percent":

#                 sheet.write_number(
#                     row,
#                     2,
#                     _to_float(
#                         value
#                     ),
#                     percent_format,
#                 )

#             else:

#                 sheet.write(
#                     row,
#                     2,
#                     (
#                         value
#                         if value not in (
#                             None,
#                             "",
#                         )
#                         else "—"
#                     ),
#                     value_format,
#                 )

#             row += 1

#         # =============================================================
#         # Состояние расчётов
#         # =============================================================

#         row += 1

#         sheet.merge_range(
#             row,
#             1,
#             row,
#             4,
#             (
#                 "Состояние расчётов "
#                 f"на {reconciliation_date_text}"
#             ),
#             section_format,
#         )

#         row += 1

#         totals = [
#             (
#                 "Всего получено по договору",
#                 total_drawdown,
#                 money_format,
#             ),

#             (
#                 "Погашено основного долга",
#                 total_principal_repaid,
#                 money_format,
#             ),

#             (
#                 (
#                     "Начислено процентов "
#                     f"по {reconciliation_date_text}"
#                 ),
#                 total_interest_accrued,
#                 money_interest_format,
#             ),

#             (
#                 (
#                     "Погашено процентов "
#                     f"по {reconciliation_date_text}"
#                 ),
#                 total_interest_repaid,
#                 money_format,
#             ),

#             # -----------------------------------------------------
#             # Самый понятный показатель:
#             # сколько начислено, но ещё не погашено платежами.
#             # -----------------------------------------------------

#             (
#                 (
#                     "Непогашенные начисленные "
#                     "проценты"
#                 ),
#                 unpaid_accrued_interest,
#                 (
#                     money_interest_format
#                     if unpaid_accrued_interest > 0
#                     else money_format
#                 ),
#             ),

#             # -----------------------------------------------------
#             # Это значение непосредственно из interest_balance.
#             # При капитализации процентов оно может быть 0.
#             # -----------------------------------------------------

#             (
#                 (
#                     "Отдельный процентный долг "
#                     "по данным базы"
#                 ),
#                 interest_balance,
#                 money_format,
#             ),

#             # -----------------------------------------------------
#             # Не называем EB чистым телом займа,
#             # потому что в твоих данных он может включать
#             # капитализированные проценты.
#             # -----------------------------------------------------

#             (
#                 (
#                     "Остаток задолженности "
#                     "на дату сверки"
#                 ),
#                 ending_balance,
#                 money_format,
#             ),

#             (
#                 (
#                     "Общая задолженность "
#                     "на дату сверки"
#                 ),
#                 total_debt,
#                 money_bold_format,
#             ),
#         ]

#         for (
#             label,
#             value,
#             fmt,
#         ) in totals:

#             sheet.write(
#                 row,
#                 1,
#                 label,
#                 label_format,
#             )

#             sheet.merge_range(
#                 row,
#                 2,
#                 row,
#                 4,
#                 _to_float(
#                     value
#                 ),
#                 fmt,
#             )

#             row += 1

#         # =============================================================
#         # История операций
#         # =============================================================

#         row += 2

#         sheet.merge_range(
#             row,
#             1,
#             row,
#             10,
#             (
#                 "История операций "
#                 f"по {reconciliation_date_text}"
#             ),
#             section_format,
#         )

#         row += 1

#         table_header_row = row

#         operation_headers = [
#             "Дата",
#             "Операция",
#             "Выдача / привлечение",
#             "Погашение тела",
#             "Начислено процентов",
#             "Погашено процентов",
#             "Остаток задолженности",
#             "Отдельный процентный долг",
#             "Общая задолженность",
#             "Ставка",
#         ]

#         for (
#             col,
#             header,
#         ) in enumerate(
#             operation_headers,
#             start=1,
#         ):

#             sheet.write(
#                 row,
#                 col,
#                 header,
#                 header_format,
#             )

#         sheet.set_column(
#             1,
#             1,
#             14,
#         )

#         sheet.set_column(
#             2,
#             2,
#             42,
#         )

#         sheet.set_column(
#             3,
#             9,
#             20,
#         )

#         sheet.set_column(
#             10,
#             10,
#             12,
#         )

#         row += 1

#         # =============================================================
#         # Строки истории
#         # =============================================================

#         if not work.empty:

#             for _, item in work.iterrows():

#                 current_col = 1

#                 # -----------------------------------------------------
#                 # Дата
#                 # -----------------------------------------------------

#                 current_date = item.get(
#                     "date_from"
#                 )

#                 if pd.notna(
#                     current_date
#                 ):

#                     sheet.write_datetime(
#                         row,
#                         current_col,
#                         current_date.to_pydatetime(),
#                         date_format,
#                     )

#                 else:

#                     sheet.write(
#                         row,
#                         current_col,
#                         "",
#                         text_format,
#                     )

#                 current_col += 1

#                 # -----------------------------------------------------
#                 # Операция
#                 # -----------------------------------------------------

#                 sheet.write(
#                     row,
#                     current_col,
#                     _clean_text(
#                         item.get(
#                             "operation_description"
#                         )
#                     ),
#                     text_format,
#                 )

#                 current_col += 1

#                 # -----------------------------------------------------
#                 # Деньги
#                 # -----------------------------------------------------

#                 money_columns = [
#                     "drawdown_amount",
#                     "principal_repayment",
#                     "interest_accrued",
#                     "interest_repayment",
#                     "ending_balance",
#                     "interest_balance",
#                     "total_debt",
#                 ]

#                 for column in money_columns:

#                     sheet.write_number(
#                         row,
#                         current_col,
#                         _to_float(
#                             item.get(
#                                 column
#                             )
#                         ),
#                         money_format,
#                     )

#                     current_col += 1

#                 # -----------------------------------------------------
#                 # Ставка
#                 # -----------------------------------------------------

#                 sheet.write_number(
#                     row,
#                     current_col,
#                     _to_float(
#                         item.get(
#                             "rate"
#                         )
#                     ),
#                     percent_format,
#                 )

#                 row += 1

#         # =============================================================
#         # AutoFilter
#         # =============================================================

#         if row > (
#             table_header_row + 1
#         ):

#             sheet.autofilter(
#                 table_header_row,
#                 1,
#                 row - 1,
#                 10,
#             )

#         # =============================================================
#         # Freeze
#         # =============================================================

#         sheet.freeze_panes(
#             table_header_row + 1,
#             2,
#         )

#         # =============================================================
#         # ЛИСТ 2 — ОПЕРАЦИИ
#         # =============================================================

#         operations_sheet = (
#             workbook.add_worksheet(
#                 "Операции"
#             )
#         )

#         writer.sheets[
#             "Операции"
#         ] = operations_sheet

#         operations_sheet.hide_gridlines(
#             2
#         )

#         operations_sheet.freeze_panes(
#             1,
#             2,
#         )

#         operations_sheet.set_column(
#             "A:A",
#             14,
#         )

#         operations_sheet.set_column(
#             "B:C",
#             38,
#         )

#         operations_sheet.set_column(
#             "D:J",
#             20,
#         )

#         operations_sheet.set_column(
#             "K:K",
#             12,
#         )

#         operation_sheet_headers = [
#             "Дата",
#             "Операция",
#             "Описание процентов",
#             "Выдача / привлечение",
#             "Погашение тела",
#             "Начислено процентов",
#             "Погашено процентов",
#             "Остаток задолженности",
#             "Отдельный процентный долг",
#             "Общая задолженность",
#             "Ставка",
#         ]

#         for (
#             col,
#             header,
#         ) in enumerate(
#             operation_sheet_headers
#         ):

#             operations_sheet.write(
#                 0,
#                 col,
#                 header,
#                 header_format,
#             )

#         # =============================================================
#         # Заполнение листа операций
#         # =============================================================

#         if not work.empty:

#             excel_row = 1

#             for _, item in work.iterrows():

#                 current_date = item.get(
#                     "date_from"
#                 )

#                 if pd.notna(
#                     current_date
#                 ):

#                     operations_sheet.write_datetime(
#                         excel_row,
#                         0,
#                         current_date.to_pydatetime(),
#                         date_format,
#                     )

#                 operations_sheet.write(
#                     excel_row,
#                     1,
#                     _clean_text(
#                         item.get(
#                             "operation_description"
#                         )
#                     ),
#                     text_format,
#                 )

#                 operations_sheet.write(
#                     excel_row,
#                     2,
#                     _clean_text(
#                         item.get(
#                             "interest_description"
#                         )
#                     ),
#                     text_format,
#                 )

#                 money_columns = [
#                     "drawdown_amount",
#                     "principal_repayment",
#                     "interest_accrued",
#                     "interest_repayment",
#                     "ending_balance",
#                     "interest_balance",
#                     "total_debt",
#                 ]

#                 for (
#                     offset,
#                     column,
#                 ) in enumerate(
#                     money_columns,
#                     start=3,
#                 ):

#                     operations_sheet.write_number(
#                         excel_row,
#                         offset,
#                         _to_float(
#                             item.get(
#                                 column
#                             )
#                         ),
#                         money_format,
#                     )

#                 operations_sheet.write_number(
#                     excel_row,
#                     10,
#                     _to_float(
#                         item.get(
#                             "rate"
#                         )
#                     ),
#                     percent_format,
#                 )

#                 excel_row += 1

#             operations_sheet.autofilter(
#                 0,
#                 0,
#                 excel_row - 1,
#                 10,
#             )

#     output.seek(0)

#     return output.getvalue()




# # gear/app/loans/excel.py

# from __future__ import annotations

# from io import BytesIO

# import pandas as pd


# # =====================================================================
# # HELPERS
# # =====================================================================


# def _to_float(
#     value,
# ) -> float:
#     try:
#         if value is None:
#             return 0.0

#         return float(value)

#     except (
#         TypeError,
#         ValueError,
#     ):
#         return 0.0


# def _clean_text(
#     value,
# ) -> str:
#     """
#     Убирает технические значения,
#     которые могут приходить вместо текста.
#     """

#     if value is None:
#         return ""

#     text = str(value).strip()

#     if text in {
#         "",
#         "0",
#         "0.0",
#         "None",
#         "nan",
#         "NaN",
#     }:
#         return ""

#     return text


# def _trim_empty_rows_after_zero_adjustment(
#     work: pd.DataFrame,
# ) -> pd.DataFrame:
#     """
#     Сохраняет строку ручной корректировки, которой тело и проценты
#     были приведены к нулю, и удаляет последующие пустые календарные дни.

#     Обрезание выполняется только когда после такой корректировки нет:
#     - новых выдач;
#     - погашений тела;
#     - погашений процентов;
#     - новых ручных или фактических операций;
#     - повторного возникновения задолженности.

#     Поэтому будущая выдача, оплата или следующая корректировка
#     никогда не потеряются.
#     """

#     if work.empty:
#         return work

#     required_numeric_columns = [
#         "drawdown_amount",
#         "principal_repayment",
#         "interest_accrued",
#         "interest_repayment",
#         "ending_balance",
#         "interest_balance",
#         "total_debt",
#     ]

#     for column in required_numeric_columns:
#         if column not in work.columns:
#             work[column] = 0.0

#         work[column] = pd.to_numeric(
#             work[column],
#             errors="coerce",
#         ).fillna(0.0)

#     operation_description = (
#         work.get(
#             "operation_description",
#             pd.Series(
#                 "",
#                 index=work.index,
#                 dtype="object",
#             ),
#         )
#         .fillna("")
#         .astype(str)
#         .str.strip()
#     )

#     tolerance = 0.005

#     zero_balance_mask = (
#         work["ending_balance"].abs().le(
#             tolerance
#         )
#         & work["interest_balance"].abs().le(
#             tolerance
#         )
#         & work["total_debt"].abs().le(
#             tolerance
#         )
#     )

#     adjustment_mask = (
#         operation_description
#         .str.contains(
#             "Ручная корректировка",
#             case=False,
#             na=False,
#         )
#     )

#     closing_indexes = work.index[
#         zero_balance_mask
#         & adjustment_mask
#     ].tolist()

#     if not closing_indexes:
#         return work

#     # Проверяем корректировки от более поздней к более ранней.
#     # Берём первую подходящую дату, после которой действительно
#     # отсутствуют любые значимые операции.
#     for closing_index in reversed(
#         closing_indexes
#     ):
#         future_rows = work.loc[
#             work.index > closing_index
#         ].copy()

#         if future_rows.empty:
#             return (
#                 work.loc[
#                     work.index <= closing_index
#                 ]
#                 .copy()
#                 .reset_index(
#                     drop=True
#                 )
#             )

#         future_operation_description = (
#             future_rows.get(
#                 "operation_description",
#                 pd.Series(
#                     "",
#                     index=future_rows.index,
#                     dtype="object",
#                 ),
#             )
#             .fillna("")
#             .astype(str)
#             .str.strip()
#         )

#         future_has_cash_movements = (
#             future_rows[
#                 "drawdown_amount"
#             ].abs().gt(
#                 tolerance
#             ).any()
#             or future_rows[
#                 "principal_repayment"
#             ].abs().gt(
#                 tolerance
#             ).any()
#             or future_rows[
#                 "interest_repayment"
#             ].abs().gt(
#                 tolerance
#             ).any()
#         )

#         future_has_debt = (
#             future_rows[
#                 "ending_balance"
#             ].abs().gt(
#                 tolerance
#             ).any()
#             or future_rows[
#                 "interest_balance"
#             ].abs().gt(
#                 tolerance
#             ).any()
#             or future_rows[
#                 "total_debt"
#             ].abs().gt(
#                 tolerance
#             ).any()
#         )

#         future_has_operations = (
#             future_operation_description
#             .ne("")
#             .any()
#         )

#         if (
#             not future_has_cash_movements
#             and not future_has_debt
#             and not future_has_operations
#         ):
#             return (
#                 work.loc[
#                     work.index <= closing_index
#                 ]
#                 .copy()
#                 .reset_index(
#                     drop=True
#                 )
#             )

#     return work


# # =====================================================================
# # MAIN
# # =====================================================================


# def build_reconciliation_excel(
#     *,
#     loan: dict,
#     transactions: pd.DataFrame,
#     report_date: str,
# ) -> bytes:
#     """
#     Формирует профессиональную Excel-сверку
#     по выбранному договору займа.

#     ВАЖНО:
#     сверка строится строго на report_date.

#     Все строки после report_date:
#     - не участвуют в начислении процентов;
#     - не участвуют в погашениях;
#     - не влияют на состояние задолженности;
#     - не выводятся в истории операций.

#     Листы:
#     1. Саммари
#     2. Операции
#     """

#     output = BytesIO()

#     # =================================================================
#     # Дата сверки
#     # =================================================================

#     reconciliation_date = pd.to_datetime(
#         report_date,
#         errors="coerce",
#     )

#     reconciliation_date_text = (
#         reconciliation_date.strftime(
#             "%d.%m.%Y"
#         )
#         if pd.notna(
#             reconciliation_date
#         )
#         else "—"
#     )

#     # =================================================================
#     # Договор
#     # =================================================================

#     counterparty = (
#         loan.get(
#             "counterparty_name"
#         )
#         or "Без контрагента"
#     )

#     contract_number = (
#         loan.get(
#             "contract_number"
#         )
#         or "б/н"
#     )

#     contract_date = pd.to_datetime(
#         loan.get(
#             "contract_date"
#         ),
#         errors="coerce",
#     )

#     currency = (
#         loan.get(
#             "currency"
#         )
#         or ""
#     )

#     repayment_date = pd.to_datetime(
#         loan.get(
#             "repayment_date"
#         ),
#         errors="coerce",
#     )

#     rate = _to_float(
#         loan.get(
#             "rate"
#         )
#     )

#     # =================================================================
#     # Подготовка операций
#     # =================================================================

#     work = transactions.copy()

#     numeric_columns = [
#         "drawdown_amount",
#         "principal_repayment",
#         "interest_accrued",
#         "interest_repayment",
#         "ending_balance",
#         "interest_balance",
#         "total_debt",
#         "rate",
#     ]

#     if not work.empty:

#         work["date_from"] = pd.to_datetime(
#             work["date_from"],
#             errors="coerce",
#         )

#         for column in numeric_columns:

#             if column not in work.columns:
#                 work[column] = 0.0

#             work[column] = pd.to_numeric(
#                 work[column],
#                 errors="coerce",
#             ).fillna(0)

#         # =============================================================
#         # ВТОРАЯ ЗАЩИТА ОТ БУДУЩИХ СТРОК
#         #
#         # SQL уже должен отрезать будущее,
#         # но Excel дополнительно страхуем.
#         # =============================================================

#         if pd.notna(
#             reconciliation_date
#         ):
#             work = work[
#                 work["date_from"]
#                 <= reconciliation_date
#             ].copy()

#         work = (
#             work
#             .dropna(
#                 subset=[
#                     "date_from",
#                 ]
#             )
#             .sort_values(
#                 "date_from"
#             )
#             .reset_index(
#                 drop=True
#             )
#         )

#         # =============================================================
#         # НЕ ВЫВОДИМ ПУСТЫЕ ДНИ ПОСЛЕ ЗАКРЫВАЮЩЕЙ КОРРЕКТИРОВКИ
#         #
#         # Строка самой корректировки остаётся в Excel.
#         # Последующие календарные строки с нулевым долгом удаляются.
#         # =============================================================

#         work = _trim_empty_rows_after_zero_adjustment(
#             work
#         )

#     # =================================================================
#     # СОСТОЯНИЕ РАСЧЁТОВ НА ДАТУ СВЕРКИ
#     # =================================================================

#     if not work.empty:

#         # -------------------------------------------------------------
#         # Движения
#         # -------------------------------------------------------------

#         total_drawdown = float(
#             work[
#                 "drawdown_amount"
#             ].sum()
#         )

#         total_principal_repaid = float(
#             work[
#                 "principal_repayment"
#             ].sum()
#         )

#         total_interest_accrued = float(
#             work[
#                 "interest_accrued"
#             ].sum()
#         )

#         total_interest_repaid = float(
#             work[
#                 "interest_repayment"
#             ].sum()
#         )

#         # -------------------------------------------------------------
#         # Непогашенные начисленные проценты
#         #
#         # Это именно аналитический показатель:
#         # начислено - погашено.
#         #
#         # НЕ прибавляем его повторно к total_debt,
#         # потому что проценты могут быть уже
#         # капитализированы в задолженность.
#         # -------------------------------------------------------------

#         unpaid_accrued_interest = max(
#             total_interest_accrued
#             - total_interest_repaid,
#             0.0,
#         )

#         # -------------------------------------------------------------
#         # Последнее фактическое состояние
#         # на дату сверки
#         # -------------------------------------------------------------

#         last_row = work.iloc[-1]

#         ending_balance = _to_float(
#             last_row.get(
#                 "ending_balance"
#             )
#         )

#         interest_balance = _to_float(
#             last_row.get(
#                 "interest_balance"
#             )
#         )

#         total_debt = _to_float(
#             last_row.get(
#                 "total_debt"
#             )
#         )

#         last_rate = _to_float(
#             last_row.get(
#                 "rate"
#             )
#         )

#         if last_rate:
#             rate = last_rate

#         actual_state_date = (
#             last_row["date_from"]
#         )

#     else:

#         total_drawdown = 0.0
#         total_principal_repaid = 0.0

#         total_interest_accrued = 0.0
#         total_interest_repaid = 0.0
#         unpaid_accrued_interest = 0.0

#         ending_balance = 0.0
#         interest_balance = 0.0
#         total_debt = 0.0

#         actual_state_date = pd.NaT

#     actual_state_date_text = (
#         actual_state_date.strftime(
#             "%d.%m.%Y"
#         )
#         if pd.notna(
#             actual_state_date
#         )
#         else "—"
#     )

#     # =================================================================
#     # EXCEL
#     # =================================================================

#     with pd.ExcelWriter(
#         output,
#         engine="xlsxwriter",
#         datetime_format="dd.mm.yyyy",
#         date_format="dd.mm.yyyy",
#     ) as writer:

#         workbook = writer.book

#         # =============================================================
#         # Форматы
#         # =============================================================

#         title_format = (
#             workbook.add_format(
#                 {
#                     "font_name": "Helvetica Light",
#                     "font_size": 10,
#                     "bold": True,
#                     "font_color": "#111827",
#                     "align": "left",
#                     "valign": "vcenter",
#                 }
#             )
#         )

#         subtitle_format = (
#             workbook.add_format(
#                 {
#                     "font_name": "Helvetica Light",
#                     "font_size": 10,
#                     "font_color": "#6B7280",
#                     "align": "left",
#                     "valign": "vcenter",
#                 }
#             )
#         )

#         section_format = (
#             workbook.add_format(
#                 {
#                     "font_name": "Helvetica Light",
#                     "font_size": 10,
#                     "bold": True,
#                     "font_color": "#22312D",
#                     "bg_color": "#E7F1ED",

#                     "border": 1,
#                     "border_color": "#D9DEE2",

#                     "align": "left",
#                     "valign": "vcenter",
#                 }
#             )
#         )

#         label_format = (
#             workbook.add_format(
#                 {
#                     "font_name": "Helvetica Light",
#                     "font_size": 10,

#                     "font_color": "#6B7280",
#                     "bg_color": "#F8FAF9",

#                     "border": 1,
#                     "border_color": "#D9DEE2",

#                     "align": "left",
#                     "valign": "vcenter",
#                 }
#             )
#         )

#         value_format = (
#             workbook.add_format(
#                 {
#                     "font_name": "Helvetica Light",
#                     "font_size": 10,

#                     "font_color": "#111827",
#                     "bold": True,

#                     "border": 1,
#                     "border_color": "#D9DEE2",

#                     "align": "left",
#                     "valign": "vcenter",
#                 }
#             )
#         )

#         # -------------------------------------------------------------
#         # Денежный формат.
#         #
#         # Excel сам локализует разделители.
#         # -------------------------------------------------------------

#         money_format = (
#             workbook.add_format(
#                 {
#                     "font_name": "Helvetica Light",
#                     "font_size": 10,

#                     "num_format": (
#                         '#,##0.00;'
#                         '[Red]-#,##0.00'
#                     ),

#                     "border": 1,
#                     "border_color": "#D9DEE2",

#                     "align": "right",
#                     "valign": "vcenter",
#                 }
#             )
#         )

#         money_bold_format = (
#             workbook.add_format(
#                 {
#                     "font_name": "Helvetica Light",
#                     "font_size": 10,
#                     "bold": True,

#                     "font_color": "#22312D",
#                     "bg_color": "#E7F1ED",

#                     "num_format": (
#                         '#,##0.00;'
#                         '[Red]-#,##0.00'
#                     ),

#                     "border": 1,
#                     "border_color": "#D9DEE2",

#                     "align": "right",
#                     "valign": "vcenter",
#                 }
#             )
#         )

#         money_interest_format = (
#             workbook.add_format(
#                 {
#                     "font_name": "Helvetica Light",
#                     "font_size": 10,
#                     "bold": True,

#                     "font_color": "#B45309",
#                     "bg_color": "#FEF3E7",

#                     "num_format": (
#                         '#,##0.00;'
#                         '[Red]-#,##0.00'
#                     ),

#                     "border": 1,
#                     "border_color": "#D9DEE2",

#                     "align": "right",
#                     "valign": "vcenter",
#                 }
#             )
#         )

#         percent_format = (
#             workbook.add_format(
#                 {
#                     "font_name": "Helvetica Light",
#                     "font_size": 10,

#                     # rate уже 19.25,
#                     # поэтому знак % только дописываем.
#                     "num_format": '0.00"%"',

#                     "border": 1,
#                     "border_color": "#D9DEE2",

#                     "align": "right",
#                     "valign": "vcenter",
#                 }
#             )
#         )

#         date_format = (
#             workbook.add_format(
#                 {
#                     "font_name": "Helvetica Light",
#                     "font_size": 10,

#                     "num_format": "dd.mm.yyyy",

#                     "border": 1,
#                     "border_color": "#D9DEE2",

#                     "align": "left",
#                     "valign": "vcenter",
#                 }
#             )
#         )

#         header_format = (
#             workbook.add_format(
#                 {
#                     "font_name": "Helvetica Light",
#                     "font_size": 10,
#                     "bold": True,

#                     "font_color": "#FFFFFF",
#                     "bg_color": "#2F6656",

#                     "border": 1,
#                     "border_color": "#D9DEE2",

#                     "align": "center",
#                     "valign": "vcenter",

#                     "text_wrap": True,
#                 }
#             )
#         )

#         text_format = (
#             workbook.add_format(
#                 {
#                     "font_name": "Helvetica Light",
#                     "font_size": 10,

#                     "border": 1,
#                     "border_color": "#E5E7EB",

#                     "align": "left",
#                     "valign": "top",

#                     "text_wrap": True,
#                 }
#             )
#         )

#         # =============================================================
#         # ЛИСТ 1 — САММАРИ
#         # =============================================================

#         sheet = workbook.add_worksheet(
#             "Саммари"
#         )

#         writer.sheets[
#             "Саммари"
#         ] = sheet

#         sheet.hide_gridlines(
#             2
#         )

#         sheet.set_landscape()

#         sheet.fit_to_pages(
#             1,
#             0,
#         )

#         sheet.set_margins(
#             left=0.35,
#             right=0.35,
#             top=0.45,
#             bottom=0.45,
#         )

#         # =============================================================
#         # Ширины
#         # =============================================================

#         sheet.set_column(
#             "A:A",
#             3,
#         )

#         # Длинные названия показателей
#         sheet.set_column(
#             "B:B",
#             52,
#         )

#         sheet.set_column(
#             "C:E",
#             22,
#         )

#         sheet.set_column(
#             "F:J",
#             20,
#         )

#         sheet.set_column(
#             "K:K",
#             12,
#         )

#         # =============================================================
#         # Заголовок
#         # =============================================================

#         sheet.set_row(
#             1,
#             24,
#         )

#         sheet.merge_range(
#             "B2:E2",
#             (
#                 "Сверка по договору займа "
#                 f"на {reconciliation_date_text}"
#             ),
#             title_format,
#         )

#         sheet.merge_range(
#             "B3:E3",
#             (
#                 f"{counterparty} · "
#                 f"договор № {contract_number}"
#             ),
#             subtitle_format,
#         )

#         # =============================================================
#         # Параметры договора
#         # =============================================================

#         sheet.merge_range(
#             "B5:E5",
#             "Параметры договора",
#             section_format,
#         )

#         info = [
#             (
#                 "Контрагент",
#                 counterparty,
#                 "text",
#             ),
#             (
#                 "Номер договора",
#                 contract_number,
#                 "text",
#             ),
#             (
#                 "Дата договора",
#                 contract_date,
#                 "date",
#             ),
#             (
#                 "Валюта",
#                 currency,
#                 "text",
#             ),
#             (
#                 "Процентная ставка",
#                 rate,
#                 "percent",
#             ),
#             (
#                 "Дата погашения",
#                 repayment_date,
#                 "date",
#             ),
#             (
#                 "Дата сверки",
#                 reconciliation_date,
#                 "date",
#             ),
#             (
#                 "Последнее состояние в базе",
#                 actual_state_date,
#                 "date",
#             ),
#         ]

#         row = 5

#         for (
#             label,
#             value,
#             value_type,
#         ) in info:

#             sheet.write(
#                 row,
#                 1,
#                 label,
#                 label_format,
#             )

#             if value_type == "percent":
#                 fmt = percent_format

#             elif value_type == "date":
#                 fmt = date_format

#             else:
#                 fmt = value_format

#             sheet.merge_range(
#                 row,
#                 2,
#                 row,
#                 4,
#                 "",
#                 fmt,
#             )

#             if (
#                 value_type == "date"
#                 and pd.notna(value)
#             ):

#                 sheet.write_datetime(
#                     row,
#                     2,
#                     value.to_pydatetime(),
#                     date_format,
#                 )

#             elif value_type == "percent":

#                 sheet.write_number(
#                     row,
#                     2,
#                     _to_float(
#                         value
#                     ),
#                     percent_format,
#                 )

#             else:

#                 sheet.write(
#                     row,
#                     2,
#                     (
#                         value
#                         if value not in (
#                             None,
#                             "",
#                         )
#                         else "—"
#                     ),
#                     value_format,
#                 )

#             row += 1

#         # =============================================================
#         # Состояние расчётов
#         # =============================================================

#         row += 1

#         sheet.merge_range(
#             row,
#             1,
#             row,
#             4,
#             (
#                 "Состояние расчётов "
#                 f"на {reconciliation_date_text}"
#             ),
#             section_format,
#         )

#         row += 1

#         totals = [
#             (
#                 "Всего получено по договору",
#                 total_drawdown,
#                 money_format,
#             ),

#             (
#                 "Погашено основного долга",
#                 total_principal_repaid,
#                 money_format,
#             ),

#             (
#                 (
#                     "Начислено процентов "
#                     f"по {reconciliation_date_text}"
#                 ),
#                 total_interest_accrued,
#                 money_interest_format,
#             ),

#             (
#                 (
#                     "Погашено процентов "
#                     f"по {reconciliation_date_text}"
#                 ),
#                 total_interest_repaid,
#                 money_format,
#             ),

#             # -----------------------------------------------------
#             # Самый понятный показатель:
#             # сколько начислено, но ещё не погашено платежами.
#             # -----------------------------------------------------

#             (
#                 (
#                     "Непогашенные начисленные "
#                     "проценты"
#                 ),
#                 unpaid_accrued_interest,
#                 (
#                     money_interest_format
#                     if unpaid_accrued_interest > 0
#                     else money_format
#                 ),
#             ),

#             # -----------------------------------------------------
#             # Не называем EB чистым телом займа,
#             # потому что в твоих данных он может включать
#             # капитализированные проценты.
#             # -----------------------------------------------------

#             (
#                 (
#                     "Остаток задолженности "
#                     "на дату сверки"
#                 ),
#                 ending_balance,
#                 money_format,
#             ),

#             (
#                 (
#                     "Общая задолженность "
#                     "на дату сверки"
#                 ),
#                 total_debt,
#                 money_bold_format,
#             ),
#         ]

#         for (
#             label,
#             value,
#             fmt,
#         ) in totals:

#             sheet.write(
#                 row,
#                 1,
#                 label,
#                 label_format,
#             )

#             sheet.merge_range(
#                 row,
#                 2,
#                 row,
#                 4,
#                 _to_float(
#                     value
#                 ),
#                 fmt,
#             )

#             row += 1

#         # =============================================================
#         # ЛИСТ 2 — ОПЕРАЦИИ
#         # =============================================================

#         operations_sheet = (
#             workbook.add_worksheet(
#                 "Операции"
#             )
#         )

#         writer.sheets[
#             "Операции"
#         ] = operations_sheet

#         operations_sheet.hide_gridlines(
#             2
#         )

#         operations_sheet.freeze_panes(
#             1,
#             2,
#         )

#         operations_sheet.set_column(
#             "A:A",
#             14,
#         )

#         operations_sheet.set_column(
#             "B:C",
#             38,
#         )

#         operations_sheet.set_column(
#             "D:J",
#             20,
#         )

#         operations_sheet.set_column(
#             "K:K",
#             12,
#         )

#         operation_sheet_headers = [
#             "Дата",
#             "Операция",
#             "Описание процентов",
#             "Выдача / привлечение",
#             "Погашение тела",
#             "Начислено процентов",
#             "Погашено процентов",
#             "Остаток задолженности",
#             "Отдельный процентный долг",
#             "Общая задолженность",
#             "Ставка",
#         ]

#         for (
#             col,
#             header,
#         ) in enumerate(
#             operation_sheet_headers
#         ):

#             operations_sheet.write(
#                 0,
#                 col,
#                 header,
#                 header_format,
#             )

#         # =============================================================
#         # Заполнение листа операций
#         # =============================================================

#         if not work.empty:

#             excel_row = 1

#             for _, item in work.iterrows():

#                 current_date = item.get(
#                     "date_from"
#                 )

#                 if pd.notna(
#                     current_date
#                 ):

#                     operations_sheet.write_datetime(
#                         excel_row,
#                         0,
#                         current_date.to_pydatetime(),
#                         date_format,
#                     )

#                 operations_sheet.write(
#                     excel_row,
#                     1,
#                     _clean_text(
#                         item.get(
#                             "operation_description"
#                         )
#                     ),
#                     text_format,
#                 )

#                 operations_sheet.write(
#                     excel_row,
#                     2,
#                     _clean_text(
#                         item.get(
#                             "interest_description"
#                         )
#                     ),
#                     text_format,
#                 )

#                 money_columns = [
#                     "drawdown_amount",
#                     "principal_repayment",
#                     "interest_accrued",
#                     "interest_repayment",
#                     "ending_balance",
#                     "interest_balance",
#                     "total_debt",
#                 ]

#                 for (
#                     offset,
#                     column,
#                 ) in enumerate(
#                     money_columns,
#                     start=3,
#                 ):

#                     operations_sheet.write_number(
#                         excel_row,
#                         offset,
#                         _to_float(
#                             item.get(
#                                 column
#                             )
#                         ),
#                         money_format,
#                     )

#                 operations_sheet.write_number(
#                     excel_row,
#                     10,
#                     _to_float(
#                         item.get(
#                             "rate"
#                         )
#                     ),
#                     percent_format,
#                 )

#                 excel_row += 1

#             operations_sheet.autofilter(
#                 0,
#                 0,
#                 excel_row - 1,
#                 10,
#             )

#     output.seek(0)

#     return output.getvalue()




# gear/app/loans/excel.py

from __future__ import annotations

from io import BytesIO

import pandas as pd


RU_MONTHS = (
    "",
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
)


# =====================================================================
# HELPERS
# =====================================================================


def _to_float(
    value,
) -> float:
    try:
        if value is None:
            return 0.0

        return float(value)

    except (
        TypeError,
        ValueError,
    ):
        return 0.0


def _clean_text(
    value,
) -> str:
    """
    Убирает технические значения,
    которые могут приходить вместо текста.
    """

    if value is None:
        return ""

    text = str(value).strip()

    if text in {
        "",
        "0",
        "0.0",
        "None",
        "nan",
        "NaN",
    }:
        return ""

    return text


def _format_month(
    value,
) -> str:
    """Возвращает название месяца без зависимости от locale сервера."""

    parsed = pd.to_datetime(
        value,
        errors="coerce",
    )

    if pd.isna(parsed):
        return "—"

    return (
        f"{RU_MONTHS[parsed.month]} "
        f"{parsed.year}"
    )


def _trim_empty_rows_after_zero_adjustment(
    work: pd.DataFrame,
) -> pd.DataFrame:
    """
    Сохраняет строку ручной корректировки, которой тело и проценты
    были приведены к нулю, и удаляет последующие пустые календарные дни.

    Обрезание выполняется только когда после такой корректировки нет:
    - новых выдач;
    - погашений тела;
    - погашений процентов;
    - новых ручных или фактических операций;
    - повторного возникновения задолженности.

    Поэтому будущая выдача, оплата или следующая корректировка
    никогда не потеряются.
    """

    if work.empty:
        return work

    required_numeric_columns = [
        "drawdown_amount",
        "principal_repayment",
        "interest_accrued",
        "interest_repayment",
        "ending_balance",
        "interest_balance",
        "total_debt",
    ]

    for column in required_numeric_columns:
        if column not in work.columns:
            work[column] = 0.0

        work[column] = pd.to_numeric(
            work[column],
            errors="coerce",
        ).fillna(0.0)

    operation_description = (
        work.get(
            "operation_description",
            pd.Series(
                "",
                index=work.index,
                dtype="object",
            ),
        )
        .fillna("")
        .astype(str)
        .str.strip()
    )

    tolerance = 0.005

    zero_balance_mask = (
        work["ending_balance"].abs().le(
            tolerance
        )
        & work["interest_balance"].abs().le(
            tolerance
        )
        & work["total_debt"].abs().le(
            tolerance
        )
    )

    adjustment_mask = (
        operation_description
        .str.contains(
            "Ручная корректировка",
            case=False,
            na=False,
        )
    )

    closing_indexes = work.index[
        zero_balance_mask
        & adjustment_mask
    ].tolist()

    if not closing_indexes:
        return work

    # Проверяем корректировки от более поздней к более ранней.
    # Берём первую подходящую дату, после которой действительно
    # отсутствуют любые значимые операции.
    for closing_index in reversed(
        closing_indexes
    ):
        future_rows = work.loc[
            work.index > closing_index
        ].copy()

        if future_rows.empty:
            return (
                work.loc[
                    work.index <= closing_index
                ]
                .copy()
                .reset_index(
                    drop=True
                )
            )

        future_operation_description = (
            future_rows.get(
                "operation_description",
                pd.Series(
                    "",
                    index=future_rows.index,
                    dtype="object",
                ),
            )
            .fillna("")
            .astype(str)
            .str.strip()
        )

        future_has_cash_movements = (
            future_rows[
                "drawdown_amount"
            ].abs().gt(
                tolerance
            ).any()
            or future_rows[
                "principal_repayment"
            ].abs().gt(
                tolerance
            ).any()
            or future_rows[
                "interest_repayment"
            ].abs().gt(
                tolerance
            ).any()
        )

        future_has_debt = (
            future_rows[
                "ending_balance"
            ].abs().gt(
                tolerance
            ).any()
            or future_rows[
                "interest_balance"
            ].abs().gt(
                tolerance
            ).any()
            or future_rows[
                "total_debt"
            ].abs().gt(
                tolerance
            ).any()
        )

        future_has_operations = (
            future_operation_description
            .ne("")
            .any()
        )

        if (
            not future_has_cash_movements
            and not future_has_debt
            and not future_has_operations
        ):
            return (
                work.loc[
                    work.index <= closing_index
                ]
                .copy()
                .reset_index(
                    drop=True
                )
            )

    return work


# =====================================================================
# MAIN
# =====================================================================


def build_reconciliation_excel(
    *,
    loan: dict,
    transactions: pd.DataFrame,
    report_date: str,
) -> bytes:
    """
    Формирует профессиональную Excel-сверку
    по выбранному договору займа.

    ВАЖНО:
    сверка строится строго на report_date.

    Все строки после report_date:
    - не участвуют в начислении процентов;
    - не участвуют в погашениях;
    - не влияют на состояние задолженности;
    - не выводятся в истории операций.

    Листы:
    1. Саммари
    2. Операции
    """

    output = BytesIO()

    # =================================================================
    # Дата сверки
    # =================================================================

    reconciliation_date = pd.to_datetime(
        report_date,
        errors="coerce",
    )

    reconciliation_date_text = (
        reconciliation_date.strftime(
            "%d.%m.%Y"
        )
        if pd.notna(
            reconciliation_date
        )
        else "—"
    )

    # =================================================================
    # Договор
    # =================================================================

    counterparty = (
        loan.get(
            "counterparty_name"
        )
        or "Без контрагента"
    )

    contract_number = (
        loan.get(
            "contract_number"
        )
        or "б/н"
    )

    contract_date = pd.to_datetime(
        loan.get(
            "contract_date"
        ),
        errors="coerce",
    )

    currency = (
        loan.get(
            "currency"
        )
        or ""
    )

    repayment_date = pd.to_datetime(
        loan.get(
            "repayment_date"
        ),
        errors="coerce",
    )

    rate = _to_float(
        loan.get(
            "rate"
        )
    )

    # =================================================================
    # Подготовка операций
    # =================================================================

    work = transactions.copy()

    numeric_columns = [
        "drawdown_amount",
        "principal_repayment",
        "interest_accrued",
        "interest_repayment",
        "ending_balance",
        "interest_balance",
        "total_debt",
        "rate",
    ]

    if not work.empty:

        work["date_from"] = pd.to_datetime(
            work["date_from"],
            errors="coerce",
        )

        for column in numeric_columns:

            if column not in work.columns:
                work[column] = 0.0

            work[column] = pd.to_numeric(
                work[column],
                errors="coerce",
            ).fillna(0)

        # =============================================================
        # ВТОРАЯ ЗАЩИТА ОТ БУДУЩИХ СТРОК
        #
        # SQL уже должен отрезать будущее,
        # но Excel дополнительно страхуем.
        # =============================================================

        if pd.notna(
            reconciliation_date
        ):
            work = work[
                work["date_from"]
                <= reconciliation_date
            ].copy()

        work = (
            work
            .dropna(
                subset=[
                    "date_from",
                ]
            )
            .sort_values(
                "date_from"
            )
            .reset_index(
                drop=True
            )
        )

        # =============================================================
        # НЕ ВЫВОДИМ ПУСТЫЕ ДНИ ПОСЛЕ ЗАКРЫВАЮЩЕЙ КОРРЕКТИРОВКИ
        #
        # Строка самой корректировки остаётся в Excel.
        # Последующие календарные строки с нулевым долгом удаляются.
        # =============================================================

        work = _trim_empty_rows_after_zero_adjustment(
            work
        )

    # =================================================================
    # ПОМЕСЯЧНОЕ ДВИЖЕНИЕ ДЛЯ ЛИСТА «САММАРИ»
    # =================================================================

    if not work.empty:
        monthly_summary = (
            work.assign(
                month_start=(
                    work["date_from"]
                    .dt.to_period("M")
                    .dt.to_timestamp()
                )
            )
            .groupby(
                "month_start",
                as_index=False,
            )
            .agg(
                drawdown_amount=(
                    "drawdown_amount",
                    "sum",
                ),
                principal_repayment=(
                    "principal_repayment",
                    "sum",
                ),
                interest_accrued=(
                    "interest_accrued",
                    "sum",
                ),
                interest_repayment=(
                    "interest_repayment",
                    "sum",
                ),
                total_debt=(
                    "total_debt",
                    "last",
                ),
            )
            .sort_values(
                "month_start"
            )
            .reset_index(
                drop=True
            )
        )

        monthly_summary["net_change"] = (
            monthly_summary[
                "drawdown_amount"
            ]
            - monthly_summary[
                "principal_repayment"
            ]
            + monthly_summary[
                "interest_accrued"
            ]
            - monthly_summary[
                "interest_repayment"
            ]
        )

    else:
        monthly_summary = pd.DataFrame(
            columns=[
                "month_start",
                "drawdown_amount",
                "principal_repayment",
                "interest_accrued",
                "interest_repayment",
                "net_change",
                "total_debt",
            ]
        )

    # =================================================================
    # СОСТОЯНИЕ РАСЧЁТОВ НА ДАТУ СВЕРКИ
    # =================================================================

    if not work.empty:

        # -------------------------------------------------------------
        # Движения
        # -------------------------------------------------------------

        total_drawdown = float(
            work[
                "drawdown_amount"
            ].sum()
        )

        total_principal_repaid = float(
            work[
                "principal_repayment"
            ].sum()
        )

        total_interest_accrued = float(
            work[
                "interest_accrued"
            ].sum()
        )

        total_interest_repaid = float(
            work[
                "interest_repayment"
            ].sum()
        )

        # -------------------------------------------------------------
        # Непогашенные начисленные проценты
        #
        # Это именно аналитический показатель:
        # начислено - погашено.
        #
        # НЕ прибавляем его повторно к total_debt,
        # потому что проценты могут быть уже
        # капитализированы в задолженность.
        # -------------------------------------------------------------

        unpaid_accrued_interest = max(
            total_interest_accrued
            - total_interest_repaid,
            0.0,
        )

        # -------------------------------------------------------------
        # Последнее фактическое состояние
        # на дату сверки
        # -------------------------------------------------------------

        last_row = work.iloc[-1]

        ending_balance = _to_float(
            last_row.get(
                "ending_balance"
            )
        )

        interest_balance = _to_float(
            last_row.get(
                "interest_balance"
            )
        )

        total_debt = _to_float(
            last_row.get(
                "total_debt"
            )
        )

        last_rate = _to_float(
            last_row.get(
                "rate"
            )
        )

        if last_rate:
            rate = last_rate

        actual_state_date = (
            last_row["date_from"]
        )

    else:

        total_drawdown = 0.0
        total_principal_repaid = 0.0

        total_interest_accrued = 0.0
        total_interest_repaid = 0.0
        unpaid_accrued_interest = 0.0

        ending_balance = 0.0
        interest_balance = 0.0
        total_debt = 0.0

        actual_state_date = pd.NaT

    actual_state_date_text = (
        actual_state_date.strftime(
            "%d.%m.%Y"
        )
        if pd.notna(
            actual_state_date
        )
        else "—"
    )

    # =================================================================
    # EXCEL
    # =================================================================

    with pd.ExcelWriter(
        output,
        engine="xlsxwriter",
        datetime_format="dd.mm.yyyy",
        date_format="dd.mm.yyyy",
    ) as writer:

        workbook = writer.book

        # =============================================================
        # Форматы
        # =============================================================

        title_format = (
            workbook.add_format(
                {
                    "font_name": "Helvetica Light",
                    "font_size": 10,
                    "bold": True,
                    "font_color": "#111827",
                    "align": "left",
                    "valign": "vcenter",
                }
            )
        )

        subtitle_format = (
            workbook.add_format(
                {
                    "font_name": "Helvetica Light",
                    "font_size": 10,
                    "font_color": "#6B7280",
                    "align": "left",
                    "valign": "vcenter",
                }
            )
        )

        section_format = (
            workbook.add_format(
                {
                    "font_name": "Helvetica Light",
                    "font_size": 10,
                    "bold": True,
                    "font_color": "#22312D",
                    "bg_color": "#E7F1ED",

                    "border": 1,
                    "border_color": "#D9DEE2",

                    "align": "left",
                    "valign": "vcenter",
                }
            )
        )

        label_format = (
            workbook.add_format(
                {
                    "font_name": "Helvetica Light",
                    "font_size": 10,

                    "font_color": "#6B7280",
                    "bg_color": "#F8FAF9",

                    "border": 1,
                    "border_color": "#D9DEE2",

                    "align": "left",
                    "valign": "vcenter",
                }
            )
        )

        value_format = (
            workbook.add_format(
                {
                    "font_name": "Helvetica Light",
                    "font_size": 10,

                    "font_color": "#111827",
                    "bold": True,

                    "border": 1,
                    "border_color": "#D9DEE2",

                    "align": "left",
                    "valign": "vcenter",
                }
            )
        )

        # -------------------------------------------------------------
        # Денежный формат.
        #
        # Excel сам локализует разделители.
        # -------------------------------------------------------------

        money_format = (
            workbook.add_format(
                {
                    "font_name": "Helvetica Light",
                    "font_size": 10,

                    "num_format": (
                        '#,##0.00;'
                        '[Red]-#,##0.00'
                    ),

                    "border": 1,
                    "border_color": "#D9DEE2",

                    "align": "right",
                    "valign": "vcenter",
                }
            )
        )

        money_bold_format = (
            workbook.add_format(
                {
                    "font_name": "Helvetica Light",
                    "font_size": 10,
                    "bold": True,

                    "font_color": "#22312D",
                    "bg_color": "#E7F1ED",

                    "num_format": (
                        '#,##0.00;'
                        '[Red]-#,##0.00'
                    ),

                    "border": 1,
                    "border_color": "#D9DEE2",

                    "align": "right",
                    "valign": "vcenter",
                }
            )
        )

        money_interest_format = (
            workbook.add_format(
                {
                    "font_name": "Helvetica Light",
                    "font_size": 10,
                    "bold": True,

                    "font_color": "#B45309",
                    "bg_color": "#FEF3E7",

                    "num_format": (
                        '#,##0.00;'
                        '[Red]-#,##0.00'
                    ),

                    "border": 1,
                    "border_color": "#D9DEE2",

                    "align": "right",
                    "valign": "vcenter",
                }
            )
        )

        percent_format = (
            workbook.add_format(
                {
                    "font_name": "Helvetica Light",
                    "font_size": 10,

                    # rate уже 19.25,
                    # поэтому знак % только дописываем.
                    "num_format": '0.00"%"',

                    "border": 1,
                    "border_color": "#D9DEE2",

                    "align": "right",
                    "valign": "vcenter",
                }
            )
        )

        date_format = (
            workbook.add_format(
                {
                    "font_name": "Helvetica Light",
                    "font_size": 10,

                    "num_format": "dd.mm.yyyy",

                    "border": 1,
                    "border_color": "#D9DEE2",

                    "align": "left",
                    "valign": "vcenter",
                }
            )
        )

        header_format = (
            workbook.add_format(
                {
                    "font_name": "Helvetica Light",
                    "font_size": 10,
                    "bold": True,

                    "font_color": "#FFFFFF",
                    "bg_color": "#2F6656",

                    "border": 1,
                    "border_color": "#D9DEE2",

                    "align": "center",
                    "valign": "vcenter",

                    "text_wrap": True,
                }
            )
        )

        text_format = (
            workbook.add_format(
                {
                    "font_name": "Helvetica Light",
                    "font_size": 10,

                    "border": 1,
                    "border_color": "#E5E7EB",

                    "align": "left",
                    "valign": "top",

                    "text_wrap": True,
                }
            )
        )

        month_format = (
            workbook.add_format(
                {
                    "font_name": "Helvetica Light",
                    "font_size": 10,
                    "font_color": "#22312D",
                    "border": 1,
                    "border_color": "#E5E7EB",
                    "align": "left",
                    "valign": "vcenter",
                }
            )
        )

        money_paid_format = (
            workbook.add_format(
                {
                    "font_name": "Helvetica Light",
                    "font_size": 10,
                    "font_color": "#166534",
                    "bg_color": "#F0FDF4",
                    "num_format": (
                        '#,##0.00;'
                        '[Red]-#,##0.00'
                    ),
                    "border": 1,
                    "border_color": "#E5E7EB",
                    "align": "right",
                    "valign": "vcenter",
                }
            )
        )

        money_positive_delta_format = (
            workbook.add_format(
                {
                    "font_name": "Helvetica Light",
                    "font_size": 10,
                    "bold": True,
                    "font_color": "#B45309",
                    "bg_color": "#FFF7ED",
                    "num_format": (
                        '+#,##0.00;'
                        '[Red]-#,##0.00;'
                        '0.00'
                    ),
                    "border": 1,
                    "border_color": "#E5E7EB",
                    "align": "right",
                    "valign": "vcenter",
                }
            )
        )

        money_negative_delta_format = (
            workbook.add_format(
                {
                    "font_name": "Helvetica Light",
                    "font_size": 10,
                    "bold": True,
                    "font_color": "#166534",
                    "bg_color": "#F0FDF4",
                    "num_format": (
                        '+#,##0.00;'
                        '-#,##0.00;'
                        '0.00'
                    ),
                    "border": 1,
                    "border_color": "#E5E7EB",
                    "align": "right",
                    "valign": "vcenter",
                }
            )
        )

        monthly_total_label_format = (
            workbook.add_format(
                {
                    "font_name": "Helvetica Light",
                    "font_size": 10,
                    "bold": True,
                    "font_color": "#22312D",
                    "bg_color": "#E7F1ED",
                    "top": 2,
                    "top_color": "#2F6656",
                    "bottom": 1,
                    "bottom_color": "#D9DEE2",
                    "left": 1,
                    "left_color": "#D9DEE2",
                    "right": 1,
                    "right_color": "#D9DEE2",
                    "align": "left",
                    "valign": "vcenter",
                }
            )
        )

        # =============================================================
        # ЛИСТ 1 — САММАРИ
        # =============================================================

        sheet = workbook.add_worksheet(
            "Саммари"
        )

        writer.sheets[
            "Саммари"
        ] = sheet

        sheet.hide_gridlines(
            2
        )

        sheet.set_landscape()

        sheet.fit_to_pages(
            1,
            0,
        )

        sheet.set_margins(
            left=0.35,
            right=0.35,
            top=0.45,
            bottom=0.45,
        )

        # =============================================================
        # Ширины
        # =============================================================

        sheet.set_column(
            "A:A",
            3,
        )

        # Длинные названия показателей
        sheet.set_column(
            "B:B",
            52,
        )

        sheet.set_column(
            "C:E",
            22,
        )

        sheet.set_column(
            "F:J",
            20,
        )

        sheet.set_column(
            "K:K",
            12,
        )

        # =============================================================
        # Заголовок
        # =============================================================

        sheet.set_row(
            1,
            24,
        )

        sheet.merge_range(
            "B2:E2",
            (
                "Сверка по договору займа "
                f"на {reconciliation_date_text}"
            ),
            title_format,
        )

        sheet.merge_range(
            "B3:E3",
            (
                f"{counterparty} · "
                f"договор № {contract_number}"
            ),
            subtitle_format,
        )

        # =============================================================
        # Параметры договора
        # =============================================================

        sheet.merge_range(
            "B5:E5",
            "Параметры договора",
            section_format,
        )

        info = [
            (
                "Контрагент",
                counterparty,
                "text",
            ),
            (
                "Номер договора",
                contract_number,
                "text",
            ),
            (
                "Дата договора",
                contract_date,
                "date",
            ),
            (
                "Валюта",
                currency,
                "text",
            ),
            (
                "Процентная ставка",
                rate,
                "percent",
            ),
            (
                "Дата погашения",
                repayment_date,
                "date",
            ),
            (
                "Дата сверки",
                reconciliation_date,
                "date",
            ),
            (
                "Последнее состояние в базе",
                actual_state_date,
                "date",
            ),
        ]

        row = 5

        for (
            label,
            value,
            value_type,
        ) in info:

            sheet.write(
                row,
                1,
                label,
                label_format,
            )

            if value_type == "percent":
                fmt = percent_format

            elif value_type == "date":
                fmt = date_format

            else:
                fmt = value_format

            sheet.merge_range(
                row,
                2,
                row,
                4,
                "",
                fmt,
            )

            if (
                value_type == "date"
                and pd.notna(value)
            ):

                sheet.write_datetime(
                    row,
                    2,
                    value.to_pydatetime(),
                    date_format,
                )

            elif value_type == "percent":

                sheet.write_number(
                    row,
                    2,
                    _to_float(
                        value
                    ),
                    percent_format,
                )

            else:

                sheet.write(
                    row,
                    2,
                    (
                        value
                        if value not in (
                            None,
                            "",
                        )
                        else "—"
                    ),
                    value_format,
                )

            row += 1

        # =============================================================
        # ДВИЖЕНИЕ ПО ЗАЙМУ ПО МЕСЯЦАМ
        # =============================================================

        row += 2

        sheet.merge_range(
            row,
            1,
            row,
            7,
            "Движение по займу по месяцам",
            section_format,
        )

        row += 1

        monthly_headers = [
            "Месяц",
            "Выдано / привлечено",
            "Погашено тело",
            "Начислено процентов",
            "Оплачено процентов",
            "Чистое изменение",
            "Долг на конец месяца",
        ]

        sheet.set_row(
            row,
            32,
        )

        for col, header in enumerate(
            monthly_headers,
            start=1,
        ):
            sheet.write(
                row,
                col,
                header,
                header_format,
            )

        row += 1

        if monthly_summary.empty:
            sheet.merge_range(
                row,
                1,
                row,
                7,
                "На выбранную дату операций нет",
                subtitle_format,
            )

        else:
            for _, month_item in (
                monthly_summary.iterrows()
            ):
                net_change = _to_float(
                    month_item.get(
                        "net_change"
                    )
                )

                sheet.write(
                    row,
                    1,
                    _format_month(
                        month_item.get(
                            "month_start"
                        )
                    ),
                    month_format,
                )

                sheet.write_number(
                    row,
                    2,
                    _to_float(
                        month_item.get(
                            "drawdown_amount"
                        )
                    ),
                    money_format,
                )

                sheet.write_number(
                    row,
                    3,
                    _to_float(
                        month_item.get(
                            "principal_repayment"
                        )
                    ),
                    money_paid_format,
                )

                sheet.write_number(
                    row,
                    4,
                    _to_float(
                        month_item.get(
                            "interest_accrued"
                        )
                    ),
                    money_interest_format,
                )

                sheet.write_number(
                    row,
                    5,
                    _to_float(
                        month_item.get(
                            "interest_repayment"
                        )
                    ),
                    money_paid_format,
                )

                sheet.write_number(
                    row,
                    6,
                    net_change,
                    (
                        money_positive_delta_format
                        if net_change > 0
                        else money_negative_delta_format
                    ),
                )

                sheet.write_number(
                    row,
                    7,
                    _to_float(
                        month_item.get(
                            "total_debt"
                        )
                    ),
                    money_bold_format,
                )

                row += 1

            total_net_change = _to_float(
                monthly_summary[
                    "net_change"
                ].sum()
            )

            sheet.write(
                row,
                1,
                "Итого",
                monthly_total_label_format,
            )

            total_columns = [
                "drawdown_amount",
                "principal_repayment",
                "interest_accrued",
                "interest_repayment",
            ]

            for col, column in enumerate(
                total_columns,
                start=2,
            ):
                sheet.write_number(
                    row,
                    col,
                    _to_float(
                        monthly_summary[
                            column
                        ].sum()
                    ),
                    money_bold_format,
                )

            sheet.write_number(
                row,
                6,
                total_net_change,
                money_bold_format,
            )

            sheet.write_number(
                row,
                7,
                _to_float(
                    monthly_summary.iloc[-1][
                        "total_debt"
                    ]
                ),
                money_bold_format,
            )

        # =============================================================
        # Состояние расчётов
        # =============================================================

        row += 1

        sheet.merge_range(
            row,
            1,
            row,
            4,
            (
                "Состояние расчётов "
                f"на {reconciliation_date_text}"
            ),
            section_format,
        )

        row += 1

        totals = [
            (
                "Всего получено по договору",
                total_drawdown,
                money_format,
            ),

            (
                "Погашено основного долга",
                total_principal_repaid,
                money_format,
            ),

            (
                (
                    "Начислено процентов "
                    f"по {reconciliation_date_text}"
                ),
                total_interest_accrued,
                money_interest_format,
            ),

            (
                (
                    "Погашено процентов "
                    f"по {reconciliation_date_text}"
                ),
                total_interest_repaid,
                money_format,
            ),

            # -----------------------------------------------------
            # Самый понятный показатель:
            # сколько начислено, но ещё не погашено платежами.
            # -----------------------------------------------------

            (
                (
                    "Непогашенные начисленные "
                    "проценты"
                ),
                unpaid_accrued_interest,
                (
                    money_interest_format
                    if unpaid_accrued_interest > 0
                    else money_format
                ),
            ),

            # -----------------------------------------------------
            # Не называем EB чистым телом займа,
            # потому что в твоих данных он может включать
            # капитализированные проценты.
            # -----------------------------------------------------

            (
                (
                    "Остаток задолженности "
                    "на дату сверки"
                ),
                ending_balance,
                money_format,
            ),

            (
                (
                    "Общая задолженность "
                    "на дату сверки"
                ),
                total_debt,
                money_bold_format,
            ),
        ]

        for (
            label,
            value,
            fmt,
        ) in totals:

            sheet.write(
                row,
                1,
                label,
                label_format,
            )

            sheet.merge_range(
                row,
                2,
                row,
                4,
                _to_float(
                    value
                ),
                fmt,
            )

            row += 1

        # =============================================================
        # ЛИСТ 2 — ОПЕРАЦИИ
        # =============================================================

        operations_sheet = (
            workbook.add_worksheet(
                "Операции"
            )
        )

        writer.sheets[
            "Операции"
        ] = operations_sheet

        operations_sheet.hide_gridlines(
            2
        )

        operations_sheet.freeze_panes(
            1,
            2,
        )

        operations_sheet.set_column(
            "A:A",
            14,
        )

        operations_sheet.set_column(
            "B:C",
            38,
        )

        operations_sheet.set_column(
            "D:J",
            20,
        )

        operations_sheet.set_column(
            "K:K",
            12,
        )

        operation_sheet_headers = [
            "Дата",
            "Операция",
            "Описание процентов",
            "Выдача / привлечение",
            "Погашение тела",
            "Начислено процентов",
            "Погашено процентов",
            "Остаток задолженности",
            "Отдельный процентный долг",
            "Общая задолженность",
            "Ставка",
        ]

        for (
            col,
            header,
        ) in enumerate(
            operation_sheet_headers
        ):

            operations_sheet.write(
                0,
                col,
                header,
                header_format,
            )

        # =============================================================
        # Заполнение листа операций
        # =============================================================

        if not work.empty:

            excel_row = 1

            for _, item in work.iterrows():

                current_date = item.get(
                    "date_from"
                )

                if pd.notna(
                    current_date
                ):

                    operations_sheet.write_datetime(
                        excel_row,
                        0,
                        current_date.to_pydatetime(),
                        date_format,
                    )

                operations_sheet.write(
                    excel_row,
                    1,
                    _clean_text(
                        item.get(
                            "operation_description"
                        )
                    ),
                    text_format,
                )

                operations_sheet.write(
                    excel_row,
                    2,
                    _clean_text(
                        item.get(
                            "interest_description"
                        )
                    ),
                    text_format,
                )

                money_columns = [
                    "drawdown_amount",
                    "principal_repayment",
                    "interest_accrued",
                    "interest_repayment",
                    "ending_balance",
                    "interest_balance",
                    "total_debt",
                ]

                for (
                    offset,
                    column,
                ) in enumerate(
                    money_columns,
                    start=3,
                ):

                    operations_sheet.write_number(
                        excel_row,
                        offset,
                        _to_float(
                            item.get(
                                column
                            )
                        ),
                        money_format,
                    )

                operations_sheet.write_number(
                    excel_row,
                    10,
                    _to_float(
                        item.get(
                            "rate"
                        )
                    ),
                    percent_format,
                )

                excel_row += 1

            operations_sheet.autofilter(
                0,
                0,
                excel_row - 1,
                10,
            )

    output.seek(0)

    return output.getvalue()