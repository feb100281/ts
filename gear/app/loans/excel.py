# # gear/app/loans/excel.py

# from __future__ import annotations

# from io import BytesIO

# import pandas as pd


# def build_reconciliation_excel(
#     *,
#     loan: dict,
#     transactions: pd.DataFrame,
# ) -> bytes:
#     """
#     Формирует Excel по выбранному договору.

#     Листы:
#     - Акт сверки
#     - Операции

#     Денежные показатели выводятся
#     в рублях, ставка — в процентах.
#     """

#     output = BytesIO()

#     counterparty = (
#         loan.get("counterparty_name")
#         or "Без контрагента"
#     )

#     contract_number = (
#         loan.get("contract_number")
#         or "б/н"
#     )

#     contract_date = pd.to_datetime(
#         loan.get("contract_date"),
#         errors="coerce",
#     )

#     currency = (
#         loan.get("currency")
#         or ""
#     )

#     rate = _to_float(
#         loan.get("rate")
#     )

#     ending_balance = _to_float(
#         loan.get("ending_balance")
#     )

#     interest_balance = _to_float(
#         loan.get("interest_balance")
#     )

#     total_debt = _to_float(
#         loan.get("total_debt")
#     )

#     total_drawdown = _to_float(
#         loan.get("total_drawdown")
#     )

#     total_repaid = _to_float(
#         loan.get("total_repaid")
#     )

#     repayment_date = pd.to_datetime(
#         loan.get("repayment_date"),
#         errors="coerce",
#     )

#     work = transactions.copy()

#     # =============================================================
#     # Подготовка операций
#     # =============================================================

#     if not work.empty:

#         work["date_from"] = pd.to_datetime(
#             work["date_from"],
#             errors="coerce",
#         )

#         numeric_columns = [
#             "drawdown_amount",
#             "principal_repayment",
#             "interest_accrued",
#             "interest_repayment",
#             "ending_balance",
#             "interest_balance",
#             "total_debt",
#             "rate",
#         ]

#         for column in numeric_columns:

#             if column not in work.columns:
#                 work[column] = 0.0

#             work[column] = pd.to_numeric(
#                 work[column],
#                 errors="coerce",
#             ).fillna(0)

#     # =============================================================
#     # Excel
#     # =============================================================

#     with pd.ExcelWriter(
#         output,
#         engine="xlsxwriter",
#         datetime_format="dd.mm.yyyy",
#         date_format="dd.mm.yyyy",
#     ) as writer:

#         workbook = writer.book

#         # =========================================================
#         # Форматы
#         # =========================================================

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
#                 }
#             )
#         )

#         money_format = (
#             workbook.add_format(
#                 {
#                     "font_name": "Arial",
#                     "font_size": 10,
#                     "num_format": (
#                         '# ##0.00;[Red]-# ##0.00'
#                     ),
#                     "border": 1,
#                     "border_color": "#D9DEE2",
#                     "align": "right",
#                 }
#             )
#         )

#         money_bold_format = (
#             workbook.add_format(
#                 {
#                     "font_name": "Arial",
#                     "font_size": 10,
#                     "bold": True,
#                     "num_format": (
#                         '# ##0.00;[Red]-# ##0.00'
#                     ),
#                     "bg_color": "#E7F1ED",
#                     "border": 1,
#                     "border_color": "#D9DEE2",
#                     "align": "right",
#                 }
#             )
#         )

#         percent_format = (
#             workbook.add_format(
#                 {
#                     "font_name": "Arial",
#                     "font_size": 10,
#                     "num_format": '0.00"%"',
#                     "border": 1,
#                     "border_color": "#D9DEE2",
#                     "align": "right",
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
#                     "valign": "top",
#                 }
#             )
#         )

#         # =========================================================
#         # Лист 1 — Акт сверки
#         # =========================================================

#         sheet = workbook.add_worksheet(
#             "Акт сверки"
#         )

#         writer.sheets[
#             "Акт сверки"
#         ] = sheet

#         sheet.hide_gridlines(2)

#         sheet.set_landscape()
#         sheet.fit_to_pages(1, 0)

#         sheet.set_margins(
#             left=0.35,
#             right=0.35,
#             top=0.45,
#             bottom=0.45,
#         )

#         sheet.set_column(
#             "A:A",
#             3,
#         )

#         sheet.set_column(
#             "B:B",
#             34,
#         )

#         sheet.set_column(
#             "C:C",
#             22,
#         )

#         sheet.set_column(
#             "D:D",
#             22,
#         )

#         sheet.set_column(
#             "E:E",
#             22,
#         )

#         # ---------------------------------------------------------
#         # Заголовок
#         # ---------------------------------------------------------

#         sheet.merge_range(
#             "B2:E2",
#             "Акт сверки по договору займа",
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

#         # ---------------------------------------------------------
#         # Реквизиты
#         # ---------------------------------------------------------

#         sheet.merge_range(
#             "B5:E5",
#             "Параметры договора",
#             section_format,
#         )

#         info = [
#             (
#                 "Контрагент",
#                 counterparty,
#             ),
#             (
#                 "Номер договора",
#                 contract_number,
#             ),
#             (
#                 "Дата договора",
#                 (
#                     contract_date
#                     if pd.notna(
#                         contract_date
#                     )
#                     else None
#                 ),
#             ),
#             (
#                 "Валюта",
#                 currency,
#             ),
#             (
#                 "Процентная ставка",
#                 rate,
#             ),
#             (
#                 "Дата погашения",
#                 (
#                     repayment_date
#                     if pd.notna(
#                         repayment_date
#                     )
#                     else None
#                 ),
#             ),
#         ]

#         row = 5

#         for label, value in info:

#             sheet.write(
#                 row,
#                 1,
#                 label,
#                 label_format,
#             )

#             if isinstance(
#                 value,
#                 pd.Timestamp,
#             ):
#                 sheet.write_datetime(
#                     row,
#                     2,
#                     value.to_pydatetime(),
#                     date_format,
#                 )

#             elif label == "Процентная ставка":
#                 sheet.write_number(
#                     row,
#                     2,
#                     float(value or 0),
#                     percent_format,
#                 )

#             else:
#                 sheet.write(
#                     row,
#                     2,
#                     value if value is not None else "—",
#                     value_format,
#                 )

#             sheet.merge_range(
#                 row,
#                 2,
#                 row,
#                 4,
#                 value
#                 if (
#                     value is not None
#                     and not isinstance(
#                         value,
#                         pd.Timestamp,
#                     )
#                 )
#                 else (
#                     value.to_pydatetime()
#                     if isinstance(
#                         value,
#                         pd.Timestamp,
#                     )
#                     else "—"
#                 ),
#                 (
#                     percent_format
#                     if label
#                     == "Процентная ставка"
#                     else (
#                         date_format
#                         if isinstance(
#                             value,
#                             pd.Timestamp,
#                         )
#                         else value_format
#                     )
#                 ),
#             )

#             row += 1

#         # ---------------------------------------------------------
#         # Итоги
#         # ---------------------------------------------------------

#         row += 1

#         sheet.merge_range(
#             row,
#             1,
#             row,
#             4,
#             "Состояние расчётов",
#             section_format,
#         )

#         row += 1

#         totals = [
#             (
#                 "Всего выдано / привлечено",
#                 total_drawdown,
#                 money_format,
#             ),
#             (
#                 "Погашено основного долга",
#                 total_repaid,
#                 money_format,
#             ),
#             (
#                 "Остаток основного долга",
#                 ending_balance,
#                 money_format,
#             ),
#             (
#                 "Проценты к оплате",
#                 interest_balance,
#                 money_format,
#             ),
#             (
#                 "Общая задолженность",
#                 total_debt,
#                 money_bold_format,
#             ),
#         ]

#         for label, value, fmt in totals:

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
#                 float(value),
#                 fmt,
#             )

#             row += 1

#         # =========================================================
#         # Таблица операций
#         # =========================================================

#         row += 2

#         sheet.merge_range(
#             row,
#             1,
#             row,
#             4,
#             "История операций",
#             section_format,
#         )

#         row += 1

#         operation_headers = [
#             "Дата",
#             "Операция",
#             "Выдача / привлечение",
#             "Погашение тела",
#             "Начислено процентов",
#             "Погашено процентов",
#             "Основной долг",
#             "Проценты к оплате",
#             "Общий долг",
#             "Ставка",
#         ]

#         for col, header in enumerate(
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
#             13,
#         )
#         sheet.set_column(
#             2,
#             2,
#             32,
#         )
#         sheet.set_column(
#             3,
#             10,
#             18,
#         )

#         row += 1

#         if not work.empty:

#             for _, item in work.iterrows():

#                 current_col = 1

#                 current_date = item.get(
#                     "date_from"
#                 )

#                 if pd.notna(current_date):
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

#                 sheet.write(
#                     row,
#                     current_col,
#                     (
#                         item.get(
#                             "operation_description"
#                         )
#                         or ""
#                     ),
#                     text_format,
#                 )

#                 current_col += 1

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
#                         float(
#                             item.get(
#                                 column,
#                                 0,
#                             )
#                             or 0
#                         ),
#                         money_format,
#                     )

#                     current_col += 1

#                 sheet.write_number(
#                     row,
#                     current_col,
#                     float(
#                         item.get(
#                             "rate",
#                             0,
#                         )
#                         or 0
#                     ),
#                     percent_format,
#                 )

#                 row += 1

#         # ---------------------------------------------------------
#         # Freeze
#         # ---------------------------------------------------------

#         sheet.freeze_panes(
#             row=0,
#             col=1,
#         )

#         # =========================================================
#         # Лист 2 — только операции
#         # =========================================================

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
#             13,
#         )
#         operations_sheet.set_column(
#             "B:C",
#             30,
#         )
#         operations_sheet.set_column(
#             "D:J",
#             18,
#         )
#         operations_sheet.set_column(
#             "K:K",
#             11,
#         )

#         for col, header in enumerate(
#             [
#                 "Дата",
#                 "Операция",
#                 "Описание процентов",
#                 "Выдача / привлечение",
#                 "Погашение тела",
#                 "Начислено процентов",
#                 "Погашено процентов",
#                 "Основной долг",
#                 "Проценты к оплате",
#                 "Общий долг",
#                 "Ставка",
#             ]
#         ):
#             operations_sheet.write(
#                 0,
#                 col,
#                 header,
#                 header_format,
#             )

#         if not work.empty:

#             excel_row = 1

#             for _, item in work.iterrows():

#                 current_date = item.get(
#                     "date_from"
#                 )

#                 if pd.notna(current_date):
#                     operations_sheet.write_datetime(
#                         excel_row,
#                         0,
#                         current_date.to_pydatetime(),
#                         date_format,
#                     )

#                 operations_sheet.write(
#                     excel_row,
#                     1,
#                     item.get(
#                         "operation_description"
#                     ) or "",
#                     text_format,
#                 )

#                 operations_sheet.write(
#                     excel_row,
#                     2,
#                     item.get(
#                         "interest_description"
#                     ) or "",
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

#                 for offset, column in enumerate(
#                     money_columns,
#                     start=3,
#                 ):
#                     operations_sheet.write_number(
#                         excel_row,
#                         offset,
#                         float(
#                             item.get(
#                                 column,
#                                 0,
#                             )
#                             or 0
#                         ),
#                         money_format,
#                     )

#                 operations_sheet.write_number(
#                     excel_row,
#                     10,
#                     float(
#                         item.get(
#                             "rate",
#                             0,
#                         )
#                         or 0
#                     ),
#                     percent_format,
#                 )

#                 excel_row += 1

#     output.seek(0)

#     return output.getvalue()


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




# # gear/app/loans/excel.py

# from __future__ import annotations

# from io import BytesIO

# import pandas as pd


# def _to_float(value) -> float:
#     try:
#         if value is None:
#             return 0.0

#         return float(value)

#     except (TypeError, ValueError):
#         return 0.0


# def build_reconciliation_excel(
#     *,
#     loan: dict,
#     transactions: pd.DataFrame,
# ) -> bytes:
#     """
#     Формирует профессиональную Excel-сверку
#     по выбранному договору займа.

#     Листы:
#     - Акт сверки
#     - Операции

#     ВАЖНО:
#     Итоговое состояние расчётов определяется
#     непосредственно из истории операций:
#     - привлечено = сумма drawdown_amount;
#     - погашено тело = сумма principal_repayment;
#     - остатки = последнее состояние договора.
#     """

#     output = BytesIO()

#     # =============================================================
#     # Данные договора
#     # =============================================================

#     counterparty = (
#         loan.get("counterparty_name")
#         or "Без контрагента"
#     )

#     contract_number = (
#         loan.get("contract_number")
#         or "б/н"
#     )

#     contract_date = pd.to_datetime(
#         loan.get("contract_date"),
#         errors="coerce",
#     )

#     currency = (
#         loan.get("currency")
#         or ""
#     )

#     rate = _to_float(
#         loan.get("rate")
#     )

#     repayment_date = pd.to_datetime(
#         loan.get("repayment_date"),
#         errors="coerce",
#     )

#     # =============================================================
#     # Подготовка операций
#     # =============================================================

#     work = transactions.copy()

#     if not work.empty:

#         work["date_from"] = pd.to_datetime(
#             work["date_from"],
#             errors="coerce",
#         )

#         numeric_columns = [
#             "drawdown_amount",
#             "principal_repayment",
#             "interest_accrued",
#             "interest_repayment",
#             "ending_balance",
#             "interest_balance",
#             "total_debt",
#             "rate",
#         ]

#         for column in numeric_columns:

#             if column not in work.columns:
#                 work[column] = 0.0

#             work[column] = pd.to_numeric(
#                 work[column],
#                 errors="coerce",
#             ).fillna(0)

#         work = (
#             work
#             .dropna(
#                 subset=["date_from"]
#             )
#             .sort_values("date_from")
#             .reset_index(drop=True)
#         )

#     # =============================================================
#     # СОСТОЯНИЕ РАСЧЁТОВ
#     #
#     # Главный источник — история операций.
#     # =============================================================

#     if not work.empty:

#         total_drawdown = float(
#             work["drawdown_amount"].sum()
#         )

#         total_repaid = float(
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

#         last_row = work.iloc[-1]

#         ending_balance = float(
#             last_row[
#                 "ending_balance"
#             ]
#         )

#         interest_balance = float(
#             last_row[
#                 "interest_balance"
#             ]
#         )

#         total_debt = float(
#             last_row[
#                 "total_debt"
#             ]
#         )

#         # Последняя ставка также надёжнее
#         # берётся из истории.
#         last_rate = float(
#             last_row.get(
#                 "rate",
#                 0,
#             )
#             or 0
#         )

#         if last_rate:
#             rate = last_rate

#     else:

#         # Fallback, если истории почему-то нет.
#         total_drawdown = _to_float(
#             loan.get("total_drawdown")
#         )

#         total_repaid = _to_float(
#             loan.get("total_repaid")
#         )

#         total_interest_accrued = (
#             _to_float(
#                 loan.get(
#                     "total_interest_accrued"
#                 )
#             )
#         )

#         total_interest_repaid = (
#             _to_float(
#                 loan.get(
#                     "total_interest_repaid"
#                 )
#             )
#         )

#         ending_balance = _to_float(
#             loan.get("ending_balance")
#         )

#         interest_balance = _to_float(
#             loan.get("interest_balance")
#         )

#         total_debt = _to_float(
#             loan.get("total_debt")
#         )

#     # =============================================================
#     # Excel
#     # =============================================================

#     with pd.ExcelWriter(
#         output,
#         engine="xlsxwriter",
#         datetime_format="dd.mm.yyyy",
#         date_format="dd.mm.yyyy",
#     ) as writer:

#         workbook = writer.book

#         # =========================================================
#         # Форматы
#         # =========================================================

#         title_format = workbook.add_format(
#             {
#                 "font_name": "Arial",
#                 "font_size": 16,
#                 "bold": True,
#                 "font_color": "#111827",
#                 "align": "left",
#                 "valign": "vcenter",
#             }
#         )

#         subtitle_format = workbook.add_format(
#             {
#                 "font_name": "Arial",
#                 "font_size": 10,
#                 "font_color": "#6B7280",
#             }
#         )

#         section_format = workbook.add_format(
#             {
#                 "font_name": "Arial",
#                 "font_size": 10,
#                 "bold": True,
#                 "font_color": "#22312D",
#                 "bg_color": "#E7F1ED",
#                 "border": 1,
#                 "border_color": "#D9DEE2",
#                 "align": "left",
#                 "valign": "vcenter",
#             }
#         )

#         label_format = workbook.add_format(
#             {
#                 "font_name": "Arial",
#                 "font_size": 10,
#                 "font_color": "#6B7280",
#                 "bg_color": "#F8FAF9",
#                 "border": 1,
#                 "border_color": "#D9DEE2",
#                 "valign": "vcenter",
#             }
#         )

#         value_format = workbook.add_format(
#             {
#                 "font_name": "Arial",
#                 "font_size": 10,
#                 "font_color": "#111827",
#                 "bold": True,
#                 "border": 1,
#                 "border_color": "#D9DEE2",
#                 "valign": "vcenter",
#             }
#         )

#         money_format = workbook.add_format(
#             {
#                 "font_name": "Arial",
#                 "font_size": 10,
#                 "num_format": (
#                     '# ##0.00;[Red]-# ##0.00'
#                 ),
#                 "border": 1,
#                 "border_color": "#D9DEE2",
#                 "align": "right",
#                 "valign": "vcenter",
#             }
#         )

#         money_bold_format = (
#             workbook.add_format(
#                 {
#                     "font_name": "Arial",
#                     "font_size": 10,
#                     "bold": True,
#                     "num_format": (
#                         '# ##0.00;'
#                         '[Red]-# ##0.00'
#                     ),
#                     "bg_color": "#E7F1ED",
#                     "border": 1,
#                     "border_color": "#D9DEE2",
#                     "align": "right",
#                     "valign": "vcenter",
#                 }
#             )
#         )

#         percent_format = workbook.add_format(
#             {
#                 "font_name": "Arial",
#                 "font_size": 10,

#                 # ВАЖНО:
#                 # rate у нас уже 19.25,
#                 # а не 0.1925.
#                 "num_format": '0.00"%"',

#                 "border": 1,
#                 "border_color": "#D9DEE2",
#                 "align": "right",
#                 "valign": "vcenter",
#             }
#         )

#         date_format = workbook.add_format(
#             {
#                 "font_name": "Arial",
#                 "font_size": 10,
#                 "num_format": "dd.mm.yyyy",
#                 "border": 1,
#                 "border_color": "#D9DEE2",
#                 "valign": "vcenter",
#             }
#         )

#         header_format = workbook.add_format(
#             {
#                 "font_name": "Arial",
#                 "font_size": 9,
#                 "bold": True,
#                 "font_color": "#FFFFFF",
#                 "bg_color": "#2F6656",
#                 "border": 1,
#                 "border_color": "#D9DEE2",
#                 "align": "center",
#                 "valign": "vcenter",
#                 "text_wrap": True,
#             }
#         )

#         text_format = workbook.add_format(
#             {
#                 "font_name": "Arial",
#                 "font_size": 9,
#                 "border": 1,
#                 "border_color": "#E5E7EB",
#                 "valign": "top",
#             }
#         )

#         # =========================================================
#         # Лист 1
#         # =========================================================

#         sheet = workbook.add_worksheet(
#             "Акт сверки"
#         )

#         writer.sheets[
#             "Акт сверки"
#         ] = sheet

#         sheet.hide_gridlines(2)

#         sheet.set_landscape()
#         sheet.fit_to_pages(1, 0)

#         sheet.set_margins(
#             left=0.35,
#             right=0.35,
#             top=0.45,
#             bottom=0.45,
#         )

#         # =========================================================
#         # Ширины
#         # =========================================================

#         sheet.set_column(
#             "A:A",
#             3,
#         )

#         # Было 34.
#         # Теперь названия показателей
#         # помещаются полностью.
#         sheet.set_column(
#             "B:B",
#             38,
#         )

#         sheet.set_column(
#             "C:E",
#             22,
#         )

#         # Таблица операций идёт дальше вправо.
#         sheet.set_column(
#             "F:J",
#             19,
#         )

#         sheet.set_column(
#             "K:K",
#             12,
#         )

#         # =========================================================
#         # Заголовок
#         # =========================================================

#         sheet.merge_range(
#             "B2:E2",
#             "Акт сверки по договору займа",
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

#         # =========================================================
#         # Параметры договора
#         # =========================================================

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
#         ]

#         row = 5

#         for label, value, value_type in info:

#             sheet.write(
#                 row,
#                 1,
#                 label,
#                 label_format,
#             )

#             # Сначала создаём объединённую
#             # область C:E.
#             sheet.merge_range(
#                 row,
#                 2,
#                 row,
#                 4,
#                 "",
#                 (
#                     percent_format
#                     if value_type == "percent"
#                     else (
#                         date_format
#                         if value_type == "date"
#                         else value_format
#                     )
#                 ),
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
#                     float(value or 0),
#                     percent_format,
#                 )

#             else:
#                 sheet.write(
#                     row,
#                     2,
#                     (
#                         value
#                         if value is not None
#                         else "—"
#                     ),
#                     value_format,
#                 )

#             row += 1

#         # =========================================================
#         # Состояние расчётов
#         # =========================================================

#         row += 1

#         sheet.merge_range(
#             row,
#             1,
#             row,
#             4,
#             "Состояние расчётов",
#             section_format,
#         )

#         row += 1

#         totals = [
#             (
#                 "Всего выдано / привлечено",
#                 total_drawdown,
#                 money_format,
#             ),
#             (
#                 "Погашено основного долга",
#                 total_repaid,
#                 money_format,
#             ),
#             (
#                 "Начислено процентов",
#                 total_interest_accrued,
#                 money_format,
#             ),
#             (
#                 "Погашено процентов",
#                 total_interest_repaid,
#                 money_format,
#             ),
#             (
#                 "Остаток основного долга",
#                 ending_balance,
#                 money_format,
#             ),
#             (
#                 "Проценты к оплате",
#                 interest_balance,
#                 money_format,
#             ),
#             (
#                 "Общая задолженность",
#                 total_debt,
#                 money_bold_format,
#             ),
#         ]

#         for label, value, fmt in totals:

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
#                 float(value),
#                 fmt,
#             )

#             row += 1

#         # =========================================================
#         # История операций
#         # =========================================================

#         row += 2

#         history_header_row = row

#         sheet.merge_range(
#             row,
#             1,
#             row,
#             10,
#             "История операций",
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
#             "Основной долг",
#             "Проценты к оплате",
#             "Общий долг",
#             "Ставка",
#         ]

#         for col, header in enumerate(
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
#             40,
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

#         # =========================================================
#         # Операции
#         # =========================================================

#         if not work.empty:

#             for _, item in work.iterrows():

#                 current_col = 1

#                 current_date = item.get(
#                     "date_from"
#                 )

#                 if pd.notna(current_date):
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

#                 operation_description = (
#                     item.get(
#                         "operation_description"
#                     )
#                     or ""
#                 )

#                 # Иногда из БД приходит 0.
#                 if str(
#                     operation_description
#                 ).strip() in {
#                     "0",
#                     "0.0",
#                     "None",
#                     "nan",
#                 }:
#                     operation_description = ""

#                 sheet.write(
#                     row,
#                     current_col,
#                     operation_description,
#                     text_format,
#                 )

#                 current_col += 1

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
#                         float(
#                             item.get(
#                                 column,
#                                 0,
#                             )
#                             or 0
#                         ),
#                         money_format,
#                     )

#                     current_col += 1

#                 sheet.write_number(
#                     row,
#                     current_col,
#                     float(
#                         item.get(
#                             "rate",
#                             0,
#                         )
#                         or 0
#                     ),
#                     percent_format,
#                 )

#                 row += 1

#         # =========================================================
#         # Автофильтр
#         # =========================================================

#         if row > table_header_row + 1:

#             sheet.autofilter(
#                 table_header_row,
#                 1,
#                 row - 1,
#                 10,
#             )

#         # =========================================================
#         # Freeze
#         # =========================================================

#         sheet.freeze_panes(
#             table_header_row + 1,
#             2,
#         )

#         # =========================================================
#         # Лист 2 — Операции
#         # =========================================================

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
#             36,
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
#             "Основной долг",
#             "Проценты к оплате",
#             "Общий долг",
#             "Ставка",
#         ]

#         for col, header in enumerate(
#             operation_sheet_headers
#         ):
#             operations_sheet.write(
#                 0,
#                 col,
#                 header,
#                 header_format,
#             )

#         if not work.empty:

#             excel_row = 1

#             for _, item in work.iterrows():

#                 current_date = item.get(
#                     "date_from"
#                 )

#                 if pd.notna(current_date):
#                     operations_sheet.write_datetime(
#                         excel_row,
#                         0,
#                         current_date.to_pydatetime(),
#                         date_format,
#                     )

#                 operation_description = (
#                     item.get(
#                         "operation_description"
#                     )
#                     or ""
#                 )

#                 if str(
#                     operation_description
#                 ).strip() in {
#                     "0",
#                     "0.0",
#                     "None",
#                     "nan",
#                 }:
#                     operation_description = ""

#                 interest_description = (
#                     item.get(
#                         "interest_description"
#                     )
#                     or ""
#                 )

#                 if str(
#                     interest_description
#                 ).strip() in {
#                     "0",
#                     "0.0",
#                     "None",
#                     "nan",
#                 }:
#                     interest_description = ""

#                 operations_sheet.write(
#                     excel_row,
#                     1,
#                     operation_description,
#                     text_format,
#                 )

#                 operations_sheet.write(
#                     excel_row,
#                     2,
#                     interest_description,
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

#                 for offset, column in enumerate(
#                     money_columns,
#                     start=3,
#                 ):

#                     operations_sheet.write_number(
#                         excel_row,
#                         offset,
#                         float(
#                             item.get(
#                                 column,
#                                 0,
#                             )
#                             or 0
#                         ),
#                         money_format,
#                     )

#                 operations_sheet.write_number(
#                     excel_row,
#                     10,
#                     float(
#                         item.get(
#                             "rate",
#                             0,
#                         )
#                         or 0
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
# # Helpers
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
#     которые иногда приходят из БД
#     вместо нормального текста.
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


# # =====================================================================
# # Main
# # =====================================================================


# def build_reconciliation_excel(
#     *,
#     loan: dict,
#     transactions: pd.DataFrame,
# ) -> bytes:
#     """
#     Формирует профессиональную Excel-сверку
#     по выбранному договору займа.

#     Листы:
#     1. Акт сверки
#     2. Операции

#     Источник итоговых показателей:
#     история операций по выбранному договору.
#     """

#     output = BytesIO()

#     # =================================================================
#     # Данные договора
#     # =================================================================

#     counterparty = (
#         loan.get("counterparty_name")
#         or "Без контрагента"
#     )

#     contract_number = (
#         loan.get("contract_number")
#         or "б/н"
#     )

#     contract_date = pd.to_datetime(
#         loan.get("contract_date"),
#         errors="coerce",
#     )

#     currency = (
#         loan.get("currency")
#         or ""
#     )

#     repayment_date = pd.to_datetime(
#         loan.get("repayment_date"),
#         errors="coerce",
#     )

#     rate = _to_float(
#         loan.get("rate")
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

#         work = (
#             work
#             .dropna(
#                 subset=["date_from"]
#             )
#             .sort_values("date_from")
#             .reset_index(drop=True)
#         )

#     # =================================================================
#     # Состояние расчётов
#     # =================================================================

#     if not work.empty:

#         # -------------------------------------------------------------
#         # Обороты
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
#         # Это аналитическая величина:
#         # начислено минус фактически погашено.
#         # -------------------------------------------------------------

#         unpaid_accrued_interest = max(
#             total_interest_accrued
#             - total_interest_repaid,
#             0.0,
#         )

#         # -------------------------------------------------------------
#         # Последнее состояние
#         # -------------------------------------------------------------

#         last_row = work.iloc[-1]

#         ending_balance = float(
#             last_row[
#                 "ending_balance"
#             ]
#         )

#         interest_balance = float(
#             last_row[
#                 "interest_balance"
#             ]
#         )

#         total_debt = float(
#             last_row[
#                 "total_debt"
#             ]
#         )

#         last_rate = float(
#             last_row.get(
#                 "rate",
#                 0,
#             )
#             or 0
#         )

#         if last_rate:
#             rate = last_rate

#     else:

#         total_drawdown = _to_float(
#             loan.get(
#                 "total_drawdown"
#             )
#         )

#         total_principal_repaid = _to_float(
#             loan.get(
#                 "total_repaid"
#             )
#         )

#         total_interest_accrued = _to_float(
#             loan.get(
#                 "total_interest_accrued"
#             )
#         )

#         total_interest_repaid = _to_float(
#             loan.get(
#                 "total_interest_repaid"
#             )
#         )

#         unpaid_accrued_interest = max(
#             total_interest_accrued
#             - total_interest_repaid,
#             0.0,
#         )

#         ending_balance = _to_float(
#             loan.get(
#                 "ending_balance"
#             )
#         )

#         interest_balance = _to_float(
#             loan.get(
#                 "interest_balance"
#             )
#         )

#         total_debt = _to_float(
#             loan.get(
#                 "total_debt"
#             )
#         )

#     # =================================================================
#     # Excel
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

#         title_format = workbook.add_format(
#             {
#                 "font_name": "Arial",
#                 "font_size": 16,
#                 "bold": True,
#                 "font_color": "#111827",
#                 "align": "left",
#                 "valign": "vcenter",
#             }
#         )

#         subtitle_format = workbook.add_format(
#             {
#                 "font_name": "Arial",
#                 "font_size": 10,
#                 "font_color": "#6B7280",
#                 "align": "left",
#                 "valign": "vcenter",
#             }
#         )

#         section_format = workbook.add_format(
#             {
#                 "font_name": "Arial",
#                 "font_size": 10,
#                 "bold": True,
#                 "font_color": "#22312D",
#                 "bg_color": "#E7F1ED",

#                 "border": 1,
#                 "border_color": "#D9DEE2",

#                 "align": "left",
#                 "valign": "vcenter",
#             }
#         )

#         label_format = workbook.add_format(
#             {
#                 "font_name": "Arial",
#                 "font_size": 10,

#                 "font_color": "#6B7280",

#                 "bg_color": "#F8FAF9",

#                 "border": 1,
#                 "border_color": "#D9DEE2",

#                 "align": "left",
#                 "valign": "vcenter",
#             }
#         )

#         value_format = workbook.add_format(
#             {
#                 "font_name": "Arial",
#                 "font_size": 10,

#                 "font_color": "#111827",
#                 "bold": True,

#                 "border": 1,
#                 "border_color": "#D9DEE2",

#                 "align": "left",
#                 "valign": "vcenter",
#             }
#         )

#         # -------------------------------------------------------------
#         # ВАЖНО:
#         # Используем Excel grouping separator.
#         #
#         # НЕ '# ##0.00'
#         #
#         # Именно '#,##0.00' Excel корректно
#         # локализует сам.
#         # -------------------------------------------------------------

#         money_format = workbook.add_format(
#             {
#                 "font_name": "Arial",
#                 "font_size": 10,

#                 "num_format": (
#                     '#,##0.00;'
#                     '[Red]-#,##0.00'
#                 ),

#                 "border": 1,
#                 "border_color": "#D9DEE2",

#                 "align": "right",
#                 "valign": "vcenter",
#             }
#         )

#         money_bold_format = (
#             workbook.add_format(
#                 {
#                     "font_name": "Arial",
#                     "font_size": 10,
#                     "bold": True,

#                     "num_format": (
#                         '#,##0.00;'
#                         '[Red]-#,##0.00'
#                     ),

#                     "font_color": "#22312D",
#                     "bg_color": "#E7F1ED",

#                     "border": 1,
#                     "border_color": "#D9DEE2",

#                     "align": "right",
#                     "valign": "vcenter",
#                 }
#             )
#         )

#         money_warning_format = (
#             workbook.add_format(
#                 {
#                     "font_name": "Arial",
#                     "font_size": 10,
#                     "bold": True,

#                     "num_format": (
#                         '#,##0.00;'
#                         '[Red]-#,##0.00'
#                     ),

#                     "font_color": "#B45309",
#                     "bg_color": "#FEF3E7",

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

#                     # rate уже равен 19.25,
#                     # поэтому % только дописываем.
#                     "num_format": '0.00"%"',

#                     "border": 1,
#                     "border_color": "#D9DEE2",

#                     "align": "right",
#                     "valign": "vcenter",
#                 }
#             )
#         )

#         date_format = workbook.add_format(
#             {
#                 "font_name": "Arial",
#                 "font_size": 10,

#                 "num_format": "dd.mm.yyyy",

#                 "border": 1,
#                 "border_color": "#D9DEE2",

#                 "align": "left",
#                 "valign": "vcenter",
#             }
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

#         text_format = workbook.add_format(
#             {
#                 "font_name": "Arial",
#                 "font_size": 9,

#                 "border": 1,
#                 "border_color": "#E5E7EB",

#                 "align": "left",
#                 "valign": "top",

#                 "text_wrap": True,
#             }
#         )

#         # =============================================================
#         # Лист 1 — Сверка
#         # =============================================================

#         sheet = workbook.add_worksheet(
#             "Акт сверки"
#         )

#         writer.sheets[
#             "Акт сверки"
#         ] = sheet

#         sheet.hide_gridlines(2)

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
#         # Размеры колонок
#         # =============================================================

#         sheet.set_column(
#             "A:A",
#             3,
#         )

#         # Названия показателей
#         sheet.set_column(
#             "B:B",
#             39,
#         )

#         # Значения
#         sheet.set_column(
#             "C:E",
#             22,
#         )

#         # История операций
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
#             "Акт сверки по договору займа",
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

#             format_to_use = (
#                 percent_format
#                 if value_type == "percent"
#                 else (
#                     date_format
#                     if value_type == "date"
#                     else value_format
#                 )
#             )

#             sheet.merge_range(
#                 row,
#                 2,
#                 row,
#                 4,
#                 "",
#                 format_to_use,
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
#                     float(value or 0),
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
#             "Состояние расчётов",
#             section_format,
#         )

#         row += 1

#         totals = [
#             (
#                 "Всего выдано / привлечено",
#                 total_drawdown,
#                 money_format,
#             ),

#             (
#                 "Погашено основного долга",
#                 total_principal_repaid,
#                 money_format,
#             ),

#             (
#                 "Начислено процентов",
#                 total_interest_accrued,
#                 money_format,
#             ),

#             (
#                 "Погашено процентов",
#                 total_interest_repaid,
#                 money_format,
#             ),

#             # -----------------------------------------------------
#             # Вот эта строка отвечает на вопрос:
#             # сколько начисленных процентов ещё
#             # не было погашено платежами.
#             # -----------------------------------------------------

#             (
#                 "Непогашено начисленных процентов",
#                 unpaid_accrued_interest,
#                 (
#                     money_warning_format
#                     if unpaid_accrued_interest > 0
#                     else money_format
#                 ),
#             ),

#             (
#                 "Остаток долга",
#                 ending_balance,
#                 money_format,
#             ),

#             # -----------------------------------------------------
#             # Отдельный interest_balance из базы.
#             #
#             # При капитализации процентов он может
#             # абсолютно корректно быть равен 0.
#             # -----------------------------------------------------

#             (
#                 "в т.ч. отдельный процентный долг",
#                 interest_balance,
#                 money_format,
#             ),

#             (
#                 "Общая задолженность",
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
#                 float(value),
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
#             "История операций",
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
#             "Основной долг",
#             "Проценты к оплате",
#             "Общий долг",
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

#         # Отдельные ширины именно
#         # для таблицы истории.
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
#         # Заполняем историю
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
#                 # Денежные показатели
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
#                         item.get("rate")
#                     ),
#                     percent_format,
#                 )

#                 row += 1

#         # =============================================================
#         # Фильтр
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

#         # =================================================================
#         # Лист 2 — Операции
#         # =================================================================

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
#             "Основной долг",
#             "Проценты к оплате",
#             "Общий долг",
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

#         # =================================================================
#         # Данные листа операций
#         # =================================================================

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
#                         item.get("rate")
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
    1. Сверка
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
                    "font_name": "Arial",
                    "font_size": 16,
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
                    "font_name": "Arial",
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
                    "font_name": "Arial",
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
                    "font_name": "Arial",
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
                    "font_name": "Arial",
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
                    "font_name": "Arial",
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
                    "font_name": "Arial",
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
                    "font_name": "Arial",
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
                    "font_name": "Arial",
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
                    "font_name": "Arial",
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
                    "font_name": "Arial",
                    "font_size": 9,
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
                    "font_name": "Arial",
                    "font_size": 9,

                    "border": 1,
                    "border_color": "#E5E7EB",

                    "align": "left",
                    "valign": "top",

                    "text_wrap": True,
                }
            )
        )

        # =============================================================
        # ЛИСТ 1 — СВЕРКА
        # =============================================================

        sheet = workbook.add_worksheet(
            "Сверка"
        )

        writer.sheets[
            "Сверка"
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
            41,
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
            # Это значение непосредственно из interest_balance.
            # При капитализации процентов оно может быть 0.
            # -----------------------------------------------------

            (
                (
                    "Отдельный процентный долг "
                    "по данным базы"
                ),
                interest_balance,
                money_format,
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
        # История операций
        # =============================================================

        row += 2

        sheet.merge_range(
            row,
            1,
            row,
            10,
            (
                "История операций "
                f"по {reconciliation_date_text}"
            ),
            section_format,
        )

        row += 1

        table_header_row = row

        operation_headers = [
            "Дата",
            "Операция",
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
            operation_headers,
            start=1,
        ):

            sheet.write(
                row,
                col,
                header,
                header_format,
            )

        sheet.set_column(
            1,
            1,
            14,
        )

        sheet.set_column(
            2,
            2,
            42,
        )

        sheet.set_column(
            3,
            9,
            20,
        )

        sheet.set_column(
            10,
            10,
            12,
        )

        row += 1

        # =============================================================
        # Строки истории
        # =============================================================

        if not work.empty:

            for _, item in work.iterrows():

                current_col = 1

                # -----------------------------------------------------
                # Дата
                # -----------------------------------------------------

                current_date = item.get(
                    "date_from"
                )

                if pd.notna(
                    current_date
                ):

                    sheet.write_datetime(
                        row,
                        current_col,
                        current_date.to_pydatetime(),
                        date_format,
                    )

                else:

                    sheet.write(
                        row,
                        current_col,
                        "",
                        text_format,
                    )

                current_col += 1

                # -----------------------------------------------------
                # Операция
                # -----------------------------------------------------

                sheet.write(
                    row,
                    current_col,
                    _clean_text(
                        item.get(
                            "operation_description"
                        )
                    ),
                    text_format,
                )

                current_col += 1

                # -----------------------------------------------------
                # Деньги
                # -----------------------------------------------------

                money_columns = [
                    "drawdown_amount",
                    "principal_repayment",
                    "interest_accrued",
                    "interest_repayment",
                    "ending_balance",
                    "interest_balance",
                    "total_debt",
                ]

                for column in money_columns:

                    sheet.write_number(
                        row,
                        current_col,
                        _to_float(
                            item.get(
                                column
                            )
                        ),
                        money_format,
                    )

                    current_col += 1

                # -----------------------------------------------------
                # Ставка
                # -----------------------------------------------------

                sheet.write_number(
                    row,
                    current_col,
                    _to_float(
                        item.get(
                            "rate"
                        )
                    ),
                    percent_format,
                )

                row += 1

        # =============================================================
        # AutoFilter
        # =============================================================

        if row > (
            table_header_row + 1
        ):

            sheet.autofilter(
                table_header_row,
                1,
                row - 1,
                10,
            )

        # =============================================================
        # Freeze
        # =============================================================

        sheet.freeze_panes(
            table_header_row + 1,
            2,
        )

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