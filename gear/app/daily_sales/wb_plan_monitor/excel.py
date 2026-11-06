# # gear/app/daily_sales/wb_plan_monitor/excel.py
# from __future__ import annotations

# from io import BytesIO
# from typing import Any

# import xlsxwriter


# # =====================================================================
# # Публичные функции
# # =====================================================================


# def build_wb_plan_excel(data: dict[str, Any]) -> bytes:
#     """
#     Формирует красивый Excel-отчёт по выполнению плана WB.

#     Листы:
#     1. "По месяцам" — план, факт, отклонение, выполнение,
#        накопительные показатели и диаграмма.
#    2. "По дням" — дневной план/факт за весь год,
#        накопительные показатели, продажи, возвраты и диаграмма.

#     Ожидается результат функции build_plan_analysis().
#     Возвращает готовое содержимое XLSX в bytes.
#     """
#     if not data:
#         raise ValueError("Нет данных для формирования отчёта WB.")

#     monthly_rows = data.get("monthly_rows") or []
#     current_month = data.get("current_month") or {}

#     # Для Excel берём детализацию за весь год.
#     # Если годовые строки пока не переданы,
#     # временно используем строки текущего месяца.
#     daily_rows = (
#         data.get("year_daily_rows")
#         or current_month.get("rows")
#         or []
#     )
#     report_date = data.get("report_date")

#     output = BytesIO()

#     workbook = xlsxwriter.Workbook(
#         output,
#         {
#             "in_memory": True,
#             "constant_memory": False,
#         },
#     )

#     workbook.set_properties(
#         {
#             "title": "План / факт WB",
#             "subject": "Контроль выполнения плана WB",
#             "author": "ТРЕНДСЕТТЕР",
#             "company": "ТРЕНДСЕТТЕР",
#             "comments": "Сформировано автоматически из панели ежедневных продаж.",
#         }
#     )

#     formats = _build_formats(workbook)

#     _write_monthly_sheet(
#         workbook=workbook,
#         formats=formats,
#         data=data,
#         rows=monthly_rows,
#         report_date=report_date,
#     )

#     _write_daily_sheet(
#         workbook=workbook,
#         formats=formats,
#         data=data,
#         current_month=current_month,
#         rows=daily_rows,
#         report_date=report_date,
#     )

#     workbook.close()
#     output.seek(0)

#     return output.getvalue()


# def get_wb_plan_excel_filename(data: dict[str, Any]) -> str:
#     """Возвращает имя файла с датой последней загрузки данных."""
#     report_date = data.get("report_date") if data else None

#     if report_date:
#         return f"wb_plan_fact_{report_date:%Y-%m-%d}.xlsx"

#     return "wb_plan_fact.xlsx"


# # =====================================================================
# # Форматы
# # =====================================================================


# def _build_formats(workbook: xlsxwriter.Workbook) -> dict[str, Any]:
#     base_font = "Arial"

#     return {
#         "title": workbook.add_format(
#             {
#                 "font_name": base_font,
#                 "font_size": 18,
#                 "bold": True,
#                 "font_color": "#0F172A",
#                 "align": "left",
#                 "valign": "vcenter",
#             }
#         ),
#         "subtitle": workbook.add_format(
#             {
#                 "font_name": base_font,
#                 "font_size": 10,
#                 "font_color": "#64748B",
#                 "align": "left",
#                 "valign": "vcenter",
#             }
#         ),
#         "section": workbook.add_format(
#             {
#                 "font_name": base_font,
#                 "font_size": 11,
#                 "bold": True,
#                 "font_color": "#0F172A",
#                 "bg_color": "#F8FAFC",
#                 "bottom": 1,
#                 "bottom_color": "#CBD5E1",
#                 "align": "left",
#                 "valign": "vcenter",
#             }
#         ),
#         "header": workbook.add_format(
#             {
#                 "font_name": base_font,
#                 "font_size": 10,
#                 "bold": True,
#                 "font_color": "#FFFFFF",
#                 "bg_color": "#334155",
#                 "border": 1,
#                 "border_color": "#CBD5E1",
#                 "align": "center",
#                 "valign": "vcenter",
#                 "text_wrap": True,
#             }
#         ),
#         "header_plan": workbook.add_format(
#             {
#                 "font_name": base_font,
#                 "font_size": 10,
#                 "bold": True,
#                 "font_color": "#FFFFFF",
#                 "bg_color": "#4F6BED",
#                 "border": 1,
#                 "border_color": "#CBD5E1",
#                 "align": "center",
#                 "valign": "vcenter",
#                 "text_wrap": True,
#             }
#         ),
#         "header_fact": workbook.add_format(
#             {
#                 "font_name": base_font,
#                 "font_size": 10,
#                 "bold": True,
#                 "font_color": "#FFFFFF",
#                 "bg_color": "#F97316",
#                 "border": 1,
#                 "border_color": "#CBD5E1",
#                 "align": "center",
#                 "valign": "vcenter",
#                 "text_wrap": True,
#             }
#         ),
#         "text": workbook.add_format(
#             {
#                 "font_name": base_font,
#                 "font_size": 10,
#                 "font_color": "#334155",
#                 "border": 1,
#                 "border_color": "#E2E8F0",
#                 "valign": "vcenter",
#             }
#         ),
#         "text_center": workbook.add_format(
#             {
#                 "font_name": base_font,
#                 "font_size": 10,
#                 "font_color": "#334155",
#                 "border": 1,
#                 "border_color": "#E2E8F0",
#                 "align": "center",
#                 "valign": "vcenter",
#             }
#         ),
#         "date": workbook.add_format(
#             {
#                 "font_name": base_font,
#                 "font_size": 10,
#                 "font_color": "#334155",
#                 "num_format": "dd.mm.yyyy",
#                 "border": 1,
#                 "border_color": "#E2E8F0",
#                 "align": "center",
#                 "valign": "vcenter",
#             }
#         ),
#         "money": workbook.add_format(
#             {
#                 "font_name": base_font,
#                 "font_size": 10,
#                 "font_color": "#334155",
#                 "num_format": '#,##0.00 "₽";[Red]-#,##0.00 "₽";–',
#                 "border": 1,
#                 "border_color": "#E2E8F0",
#                 "align": "right",
#                 "valign": "vcenter",
#             }
#         ),
#         "money_bold": workbook.add_format(
#             {
#                 "font_name": base_font,
#                 "font_size": 10,
#                 "bold": True,
#                 "font_color": "#0F172A",
#                 "num_format": '#,##0.00 "₽";[Red]-#,##0.00 "₽";–',
#                 "border": 1,
#                 "border_color": "#CBD5E1",
#                 "align": "right",
#                 "valign": "vcenter",
#             }
#         ),
#         "integer": workbook.add_format(
#             {
#                 "font_name": base_font,
#                 "font_size": 10,
#                 "font_color": "#334155",
#                 "num_format": '#,##0;[Red]-#,##0;–',
#                 "border": 1,
#                 "border_color": "#E2E8F0",
#                 "align": "right",
#                 "valign": "vcenter",
#             }
#         ),
#         "percent": workbook.add_format(
#             {
#                 "font_name": base_font,
#                 "font_size": 10,
#                 "font_color": "#334155",
#                 "num_format": '0.0"%"',
#                 "border": 1,
#                 "border_color": "#E2E8F0",
#                 "align": "right",
#                 "valign": "vcenter",
#             }
#         ),
#         "total_label": workbook.add_format(
#             {
#                 "font_name": base_font,
#                 "font_size": 10,
#                 "bold": True,
#                 "font_color": "#FFFFFF",
#                 "bg_color": "#0F172A",
#                 "border": 1,
#                 "border_color": "#0F172A",
#                 "align": "left",
#                 "valign": "vcenter",
#             }
#         ),
#         "total_money": workbook.add_format(
#             {
#                 "font_name": base_font,
#                 "font_size": 10,
#                 "bold": True,
#                 "font_color": "#FFFFFF",
#                 "bg_color": "#0F172A",
#                 "num_format": '#,##0.00 "₽";[Red]-#,##0.00 "₽";–',
#                 "border": 1,
#                 "border_color": "#0F172A",
#                 "align": "right",
#                 "valign": "vcenter",
#             }
#         ),
#         "total_percent": workbook.add_format(
#             {
#                 "font_name": base_font,
#                 "font_size": 10,
#                 "bold": True,
#                 "font_color": "#FFFFFF",
#                 "bg_color": "#0F172A",
#                 "num_format": '0.0"%"',
#                 "border": 1,
#                 "border_color": "#0F172A",
#                 "align": "right",
#                 "valign": "vcenter",
#             }
#         ),
#         "kpi_label": workbook.add_format(
#             {
#                 "font_name": base_font,
#                 "font_size": 9,
#                 "font_color": "#64748B",
#                 "bg_color": "#F8FAFC",
#                 "top": 1,
#                 "left": 1,
#                 "right": 1,
#                 "border_color": "#E2E8F0",
#                 "align": "left",
#                 "valign": "vcenter",
#             }
#         ),
#         "kpi_value": workbook.add_format(
#             {
#                 "font_name": base_font,
#                 "font_size": 15,
#                 "bold": True,
#                 "font_color": "#0F172A",
#                 "bg_color": "#F8FAFC",
#                 "bottom": 1,
#                 "left": 1,
#                 "right": 1,
#                 "border_color": "#E2E8F0",
#                 "align": "left",
#                 "valign": "vcenter",
#             }
#         ),
#         "kpi_money": workbook.add_format(
#             {
#                 "font_name": base_font,
#                 "font_size": 15,
#                 "bold": True,
#                 "font_color": "#0F172A",
#                 "bg_color": "#F8FAFC",
#                 "num_format": '#,##0 "₽";[Red]-#,##0 "₽";–',
#                 "bottom": 1,
#                 "left": 1,
#                 "right": 1,
#                 "border_color": "#E2E8F0",
#                 "align": "left",
#                 "valign": "vcenter",
#             }
#         ),
#         "kpi_percent": workbook.add_format(
#             {
#                 "font_name": base_font,
#                 "font_size": 15,
#                 "bold": True,
#                 "font_color": "#0F172A",
#                 "bg_color": "#F8FAFC",
#                 "num_format": '0.0"%"',
#                 "bottom": 1,
#                 "left": 1,
#                 "right": 1,
#                 "border_color": "#E2E8F0",
#                 "align": "left",
#                 "valign": "vcenter",
#             }
#         ),
#     }


# # =====================================================================
# # Лист «По месяцам»
# # =====================================================================


# def _write_monthly_sheet(
#     workbook: xlsxwriter.Workbook,
#     formats: dict[str, Any],
#     data: dict[str, Any],
#     rows: list[dict[str, Any]],
#     report_date,
# ) -> None:
#     worksheet = workbook.add_worksheet("По месяцам")

#     worksheet.hide_gridlines(2)
#     worksheet.freeze_panes(10, 1)
#     worksheet.set_tab_color("#4F6BED")
#     worksheet.set_landscape()
#     worksheet.fit_to_pages(1, 1)
#     worksheet.set_margins(0.35, 0.35, 0.45, 0.45)
#     worksheet.repeat_rows(9, 9)

#     worksheet.set_column("A:A", 15)
#     worksheet.set_column("B:D", 18)
#     worksheet.set_column("E:E", 14)
#     worksheet.set_column("F:H", 20)
#     worksheet.set_column("I:I", 19)
#     worksheet.set_column("J:J", 2)
#     worksheet.set_column("K:R", 12)

#     worksheet.set_row(0, 28)
#     worksheet.merge_range("A1:I1", "План / факт WB по месяцам", formats["title"])

#     date_text = report_date.strftime("%d.%m.%Y") if report_date else "—"
#     worksheet.merge_range(
#         "A2:I2",
#         f"Данные на дату последней загрузки: {date_text}",
#         formats["subtitle"],
#     )

#     totals = data.get("totals") or {}

#     _write_kpi(
#         worksheet,
#         formats,
#         first_col=0,
#         last_col=1,
#         label="План за год",
#         value=float(totals.get("plan") or 0),
#         value_format=formats["kpi_money"],
#     )
#     _write_kpi(
#         worksheet,
#         formats,
#         first_col=2,
#         last_col=3,
#         label="Факт на дату отчёта",
#         value=float(totals.get("fact") or 0),
#         value_format=formats["kpi_money"],
#     )
#     _write_kpi(
#         worksheet,
#         formats,
#         first_col=4,
#         last_col=5,
#         label="Отклонение",
#         value=float(totals.get("delta") or 0),
#         value_format=formats["kpi_money"],
#     )
#     _write_kpi(
#         worksheet,
#         formats,
#         first_col=6,
#         last_col=8,
#         label="Выполнение плана",
#         value=float(totals.get("exec_pct") or 0),
#         value_format=formats["kpi_percent"],
#     )

#     worksheet.merge_range("A8:I8", "Детализация по месяцам", formats["section"])

#     headers = [
#         "Месяц",
#         "План",
#         "Факт",
#         "Отклонение",
#         "Выполнение",
#         "Накопительный план",
#         "Накопительный факт",
#         "Накопительное отклонение",
#         "Накопительное выполнение",
#     ]

#     header_formats = [
#         formats["header"],
#         formats["header_plan"],
#         formats["header_fact"],
#         formats["header"],
#         formats["header"],
#         formats["header_plan"],
#         formats["header_fact"],
#         formats["header"],
#         formats["header"],
#     ]

#     header_row = 9
#     first_data_row = header_row + 1

#     for col, (header, cell_format) in enumerate(zip(headers, header_formats)):
#         worksheet.write(header_row, col, header, cell_format)

#     worksheet.set_row(header_row, 36)

#     for index, row in enumerate(rows, start=first_data_row):
#         worksheet.write(index, 0, row.get("month") or "", formats["text"])
#         worksheet.write_number(index, 1, float(row.get("plan") or 0), formats["money"])
#         worksheet.write_number(index, 2, float(row.get("fact") or 0), formats["money"])
#         worksheet.write_number(index, 3, float(row.get("delta") or 0), formats["money"])
#         worksheet.write_number(index, 4, float(row.get("exec_pct") or 0), formats["percent"])
#         worksheet.write_number(index, 5, float(row.get("running_plan") or 0), formats["money"])
#         worksheet.write_number(index, 6, float(row.get("running_fact") or 0), formats["money"])
#         worksheet.write_number(index, 7, float(row.get("running_delta") or 0), formats["money"])
#         worksheet.write_number(index, 8, float(row.get("running_exec_pct") or 0), formats["percent"])
#         worksheet.set_row(index, 21)

#     last_data_row = first_data_row + len(rows) - 1
#     total_row = last_data_row + 1

#     if rows:
#         worksheet.write(total_row, 0, "ИТОГО", formats["total_label"])
#         worksheet.write_formula(
#             total_row,
#             1,
#             f"=SUM(B{first_data_row + 1}:B{last_data_row + 1})",
#             formats["total_money"],
#         )
#         worksheet.write_formula(
#             total_row,
#             2,
#             f"=SUM(C{first_data_row + 1}:C{last_data_row + 1})",
#             formats["total_money"],
#         )
#         worksheet.write_formula(
#             total_row,
#             3,
#             f"=C{total_row + 1}-B{total_row + 1}",
#             formats["total_money"],
#         )
#         worksheet.write_formula(
#             total_row,
#             4,
#             f'=IFERROR(C{total_row + 1}/B{total_row + 1}*100,0)',
#             formats["total_percent"],
#         )
#         worksheet.write_number(
#             total_row,
#             5,
#             float(rows[-1].get("running_plan") or 0),
#             formats["total_money"],
#         )
#         worksheet.write_number(
#             total_row,
#             6,
#             float(rows[-1].get("running_fact") or 0),
#             formats["total_money"],
#         )
#         worksheet.write_number(
#             total_row,
#             7,
#             float(rows[-1].get("running_delta") or 0),
#             formats["total_money"],
#         )
#         worksheet.write_number(
#             total_row,
#             8,
#             float(rows[-1].get("running_exec_pct") or 0),
#             formats["total_percent"],
#         )

#         worksheet.autofilter(header_row, 0, last_data_row, len(headers) - 1)

#         worksheet.conditional_format(
#             first_data_row,
#             3,
#             last_data_row,
#             3,
#             {
#                 "type": "cell",
#                 "criteria": ">=",
#                 "value": 0,
#                 "format": workbook.add_format(
#                     {
#                         "font_color": "#047857",
#                         "bg_color": "#ECFDF5",
#                     }
#                 ),
#             },
#         )
#         worksheet.conditional_format(
#             first_data_row,
#             3,
#             last_data_row,
#             3,
#             {
#                 "type": "cell",
#                 "criteria": "<",
#                 "value": 0,
#                 "format": workbook.add_format(
#                     {
#                         "font_color": "#B91C1C",
#                         "bg_color": "#FEF2F2",
#                     }
#                 ),
#             },
#         )
#         worksheet.conditional_format(
#             first_data_row,
#             4,
#             last_data_row,
#             4,
#             {
#                 "type": "3_color_scale",
#                 "min_color": "#FECACA",
#                 "mid_color": "#FEF3C7",
#                 "max_color": "#D1FAE5",
#                 "min_type": "num",
#                 "min_value": 0,
#                 "mid_type": "num",
#                 "mid_value": 100,
#                 "max_type": "num",
#                 "max_value": 120,
#             },
#         )

#         chart = workbook.add_chart({"type": "column"})

#         chart.add_series(
#             {
#                 "name": "План",
#                 "categories": ["По месяцам", first_data_row, 0, last_data_row, 0],
#                 "values": ["По месяцам", first_data_row, 1, last_data_row, 1],
#                 "fill": {"color": "#4F6BED", "transparency": 8},
#                 "border": {"none": True},
#                 "gap": 55,
#             }
#         )
#         chart.add_series(
#             {
#                 "name": "Факт",
#                 "categories": ["По месяцам", first_data_row, 0, last_data_row, 0],
#                 "values": ["По месяцам", first_data_row, 2, last_data_row, 2],
#                 "fill": {"color": "#F97316", "transparency": 5},
#                 "border": {"none": True},
#             }
#         )

#         line_chart = workbook.add_chart({"type": "line"})
#         line_chart.add_series(
#             {
#                 "name": "Накопительное выполнение",
#                 "categories": ["По месяцам", first_data_row, 0, last_data_row, 0],
#                 "values": ["По месяцам", first_data_row, 8, last_data_row, 8],
#                 "y2_axis": True,
#                 "line": {"color": "#0F766E", "width": 2.5},
#                 "marker": {
#                     "type": "circle",
#                     "size": 6,
#                     "border": {"color": "#0F766E"},
#                     "fill": {"color": "#FFFFFF"},
#                 },
#             }
#         )
#         chart.combine(line_chart)

#         chart.set_title(
#             {
#                 "name": "План / факт по месяцам",
#                 "name_font": {"name": "Arial", "size": 13, "bold": True},
#             }
#         )
#         chart.set_legend({"position": "top"})
#         chart.set_chartarea({"border": {"none": True}, "fill": {"color": "#FFFFFF"}})
#         chart.set_plotarea(
#             {
#                 "border": {"none": True},
#                 "fill": {"color": "#FFFFFF"},
#             }
#         )
#         chart.set_x_axis(
#             {
#                 "label_position": "low",
#                 "major_tick_mark": "none",
#                 "line": {"color": "#CBD5E1"},
#             }
#         )
#         chart.set_y_axis(
#             {
#                 "name": "Сумма, ₽",
#                 "num_format": '#,##0,," млн"',
#                 "major_gridlines": {"visible": True, "line": {"color": "#E2E8F0"}},
#                 "line": {"none": True},
#             }
#         )
#         chart.set_y2_axis(
#             {
#                 "name": "Выполнение, %",
#                 "num_format": '0"%"',
#                 "min": 0,
#                 "major_gridlines": {"visible": False},
#                 "line": {"none": True},
#             }
#         )
#         chart.set_size({"width": 820, "height": 390})

#         worksheet.insert_chart("K2", chart, {"x_offset": 8, "y_offset": 4})

#     worksheet.set_footer(
#         "&LТРЕНДСЕТТЕР&RСтраница &P из &N",
#         {"margin": 0.25},
#     )


# # =====================================================================
# # Лист «По дням»
# # =====================================================================


# def _write_daily_sheet(
#     workbook: xlsxwriter.Workbook,
#     formats: dict[str, Any],
#     data: dict[str, Any],
#     current_month: dict[str, Any],
#     rows: list[dict[str, Any]],
#     report_date,
# ) -> None:
#     worksheet = workbook.add_worksheet("По дням")

#     worksheet.hide_gridlines(2)
#     worksheet.freeze_panes(10, 2)
#     worksheet.set_tab_color("#F97316")
#     worksheet.set_landscape()
#     worksheet.fit_to_pages(1, 0)
#     worksheet.set_margins(0.30, 0.30, 0.45, 0.45)
#     worksheet.repeat_rows(9, 9)

#     widths = {
#         "A:A": 12,
#         "B:B": 10,
#         "C:E": 18,
#         "F:F": 14,
#         "G:I": 18,
#         "J:K": 15,
#         "L:L": 18,
#         "M:N": 15,
#         "O:O": 2,
#         "P:W": 12,
#     }
#     for column_range, width in widths.items():
#         worksheet.set_column(column_range, width)

#     worksheet.set_row(0, 28)
#     report_year = report_date.year if report_date else ""

#     worksheet.merge_range(
#         "A1:N1",
#         f"План / факт WB по дням — {report_year} год",
#         formats["title"],
#     )

#     date_text = report_date.strftime("%d.%m.%Y") if report_date else "—"
#     worksheet.merge_range(
#         "A2:N2",
#         f"Данные на дату последней загрузки: {date_text}",
#         formats["subtitle"],
#     )

#     _write_kpi(
#         worksheet,
#         formats,
#         first_col=0,
#         last_col=2,
#         label="План месяца",
#         value=float(current_month.get("month_plan") or 0),
#         value_format=formats["kpi_money"],
#     )
#     _write_kpi(
#         worksheet,
#         formats,
#         first_col=3,
#         last_col=5,
#         label="Факт месяца",
#         value=float(current_month.get("fact_to_date") or 0),
#         value_format=formats["kpi_money"],
#     )
#     _write_kpi(
#         worksheet,
#         formats,
#         first_col=6,
#         last_col=8,
#         label="План на текущую дату",
#         value=float(current_month.get("plan_to_date") or 0),
#         value_format=formats["kpi_money"],
#     )
#     _write_kpi(
#         worksheet,
#         formats,
#         first_col=9,
#         last_col=10,
#         label="Выполнение к дате",
#         value=float(current_month.get("exec_to_date_pct") or 0),
#         value_format=formats["kpi_percent"],
#     )
#     _write_kpi(
#         worksheet,
#         formats,
#         first_col=11,
#         last_col=13,
#         label="Отклонение от графика",
#         value=float(current_month.get("delta_to_date") or 0),
#         value_format=formats["kpi_money"],
#     )

#     worksheet.merge_range("A8:N8", "Детализация по дням", formats["section"])

#     headers = [
#         "Дата",
#         "День недели",
#         "План за день",
#         "Факт за день",
#         "Отклонение за день",
#         "Выполнение дня",
#         "План к дате",
#         "Факт к дате",
#         "Отклонение к дате",
#         "Выполнение к дате",
#         "Продажи",
#         "Возвраты",
#         "Количество net",
#         "Средняя цена",
#     ]

#     header_formats = [
#         formats["header"],
#         formats["header"],
#         formats["header_plan"],
#         formats["header_fact"],
#         formats["header"],
#         formats["header"],
#         formats["header_plan"],
#         formats["header_fact"],
#         formats["header"],
#         formats["header"],
#         formats["header_fact"],
#         formats["header"],
#         formats["header"],
#         formats["header"],
#     ]

#     header_row = 9
#     first_data_row = header_row + 1

#     for col, (header, cell_format) in enumerate(zip(headers, header_formats)):
#         worksheet.write(header_row, col, header, cell_format)

#     worksheet.set_row(header_row, 42)

#     for index, row in enumerate(rows, start=first_data_row):
#         daily_plan = float(row.get("daily_plan") or 0)
#         fact = float(row.get("fact") or 0)
#         running_plan = float(row.get("running_plan") or 0)
#         running_fact = float(row.get("running_fact") or 0)

#         daily_delta = fact - daily_plan
#         daily_exec_pct = fact / daily_plan * 100 if daily_plan else 0
#         running_delta = running_fact - running_plan
#         running_exec_pct = float(row.get("exec_to_date_pct") or 0)

#         worksheet.write_datetime(index, 0, row["date"], formats["date"])
#         worksheet.write(index, 1, row.get("weekday") or "", formats["text_center"])
#         worksheet.write_number(index, 2, daily_plan, formats["money"])
#         worksheet.write_number(index, 3, fact, formats["money"])
#         worksheet.write_number(index, 4, daily_delta, formats["money"])
#         worksheet.write_number(index, 5, daily_exec_pct, formats["percent"])
#         worksheet.write_number(index, 6, running_plan, formats["money"])
#         worksheet.write_number(index, 7, running_fact, formats["money"])
#         worksheet.write_number(index, 8, running_delta, formats["money"])
#         worksheet.write_number(index, 9, running_exec_pct, formats["percent"])
#         worksheet.write_number(index, 10, float(row.get("sales_amount") or 0), formats["money"])
#         worksheet.write_number(index, 11, float(row.get("returns_amount") or 0), formats["money"])
#         worksheet.write_number(index, 12, int(row.get("qty") or 0), formats["integer"])
#         worksheet.write_number(index, 13, float(row.get("avg_price") or 0), formats["money"])
#         worksheet.set_row(index, 21)

#     last_data_row = first_data_row + len(rows) - 1
#     total_row = last_data_row + 1

#     if rows:
#         worksheet.write(total_row, 0, "ИТОГО", formats["total_label"])
#         worksheet.write(total_row, 1, "", formats["total_label"])
#         worksheet.write_formula(
#             total_row,
#             2,
#             f"=SUM(C{first_data_row + 1}:C{last_data_row + 1})",
#             formats["total_money"],
#         )
#         worksheet.write_formula(
#             total_row,
#             3,
#             f"=SUM(D{first_data_row + 1}:D{last_data_row + 1})",
#             formats["total_money"],
#         )
#         worksheet.write_formula(
#             total_row,
#             4,
#             f"=D{total_row + 1}-C{total_row + 1}",
#             formats["total_money"],
#         )
#         worksheet.write_formula(
#             total_row,
#             5,
#             f'=IFERROR(D{total_row + 1}/C{total_row + 1}*100,0)',
#             formats["total_percent"],
#         )
#         worksheet.write_number(
#             total_row,
#             6,
#             float(rows[-1].get("running_plan") or 0),
#             formats["total_money"],
#         )
#         worksheet.write_number(
#             total_row,
#             7,
#             float(rows[-1].get("running_fact") or 0),
#             formats["total_money"],
#         )
#         worksheet.write_formula(
#             total_row,
#             8,
#             f"=H{total_row + 1}-G{total_row + 1}",
#             formats["total_money"],
#         )
#         worksheet.write_number(
#             total_row,
#             9,
#             float(rows[-1].get("exec_to_date_pct") or 0),
#             formats["total_percent"],
#         )
#         worksheet.write_formula(
#             total_row,
#             10,
#             f"=SUM(K{first_data_row + 1}:K{last_data_row + 1})",
#             formats["total_money"],
#         )
#         worksheet.write_formula(
#             total_row,
#             11,
#             f"=SUM(L{first_data_row + 1}:L{last_data_row + 1})",
#             formats["total_money"],
#         )
#         worksheet.write_formula(
#             total_row,
#             12,
#             f"=SUM(M{first_data_row + 1}:M{last_data_row + 1})",
#             formats["total_money"],
#         )
#         worksheet.write_formula(
#             total_row,
#             13,
#             f'=IFERROR(D{total_row + 1}/M{total_row + 1},0)',
#             formats["total_money"],
#         )

#         worksheet.autofilter(header_row, 0, last_data_row, len(headers) - 1)

#         for col in (4, 8):
#             worksheet.conditional_format(
#                 first_data_row,
#                 col,
#                 last_data_row,
#                 col,
#                 {
#                     "type": "cell",
#                     "criteria": ">=",
#                     "value": 0,
#                     "format": workbook.add_format(
#                         {
#                             "font_color": "#047857",
#                             "bg_color": "#ECFDF5",
#                         }
#                     ),
#                 },
#             )
#             worksheet.conditional_format(
#                 first_data_row,
#                 col,
#                 last_data_row,
#                 col,
#                 {
#                     "type": "cell",
#                     "criteria": "<",
#                     "value": 0,
#                     "format": workbook.add_format(
#                         {
#                             "font_color": "#B91C1C",
#                             "bg_color": "#FEF2F2",
#                         }
#                     ),
#                 },
#             )

#         worksheet.conditional_format(
#             first_data_row,
#             9,
#             last_data_row,
#             9,
#             {
#                 "type": "3_color_scale",
#                 "min_color": "#FECACA",
#                 "mid_color": "#FEF3C7",
#                 "max_color": "#D1FAE5",
#                 "min_type": "num",
#                 "min_value": 0,
#                 "mid_type": "num",
#                 "mid_value": 100,
#                 "max_type": "num",
#                 "max_value": 120,
#             },
#         )

#         chart = workbook.add_chart({"type": "line"})

#         chart.add_series(
#             {
#                 "name": "План к дате",
#                 "categories": ["По дням", first_data_row, 0, last_data_row, 0],
#                 "values": ["По дням", first_data_row, 6, last_data_row, 6],
#                 "line": {"color": "#F97316", "width": 2.25, "dash_type": "dash"},
#                 "marker": {"type": "none"},
#             }
#         )
#         chart.add_series(
#             {
#                 "name": "Факт к дате",
#                 "categories": ["По дням", first_data_row, 0, last_data_row, 0],
#                 "values": ["По дням", first_data_row, 7, last_data_row, 7],
#                 "line": {"color": "#2563EB", "width": 2.75},
#                 "marker": {
#                     "type": "circle",
#                     "size": 4,
#                     "border": {"color": "#2563EB"},
#                     "fill": {"color": "#FFFFFF"},
#                 },
#             }
#         )

#         chart.set_title(
#             {
#                 "name": "Накопительный план / факт текущего месяца",
#                 "name_font": {"name": "Arial", "size": 13, "bold": True},
#             }
#         )
#         chart.set_legend({"position": "top"})
#         chart.set_chartarea({"border": {"none": True}, "fill": {"color": "#FFFFFF"}})
#         chart.set_plotarea({"border": {"none": True}, "fill": {"color": "#FFFFFF"}})
#         chart.set_x_axis(
#             {
#                 "num_format": "dd.mm",
#                 "date_axis": True,
#                 "label_position": "low",
#                 "major_tick_mark": "none",
#                 "line": {"color": "#CBD5E1"},
#             }
#         )
#         chart.set_y_axis(
#             {
#                 "name": "Сумма, ₽",
#                 "num_format": '#,##0,," млн"',
#                 "major_gridlines": {"visible": True, "line": {"color": "#E2E8F0"}},
#                 "line": {"none": True},
#             }
#         )
#         chart.set_size({"width": 820, "height": 390})

#         worksheet.insert_chart("P2", chart, {"x_offset": 8, "y_offset": 4})

#     worksheet.set_footer(
#         "&LТРЕНДСЕТТЕР&RСтраница &P из &N",
#         {"margin": 0.25},
#     )


# # =====================================================================
# # Вспомогательные функции
# # =====================================================================


# def _write_kpi(
#     worksheet,
#     formats: dict[str, Any],
#     first_col: int,
#     last_col: int,
#     label: str,
#     value: float,
#     value_format,
# ) -> None:
#     worksheet.merge_range(3, first_col, 3, last_col, label, formats["kpi_label"])
#     worksheet.merge_range(4, first_col, 5, last_col, value, value_format)
#     worksheet.set_row(3, 18)
#     worksheet.set_row(4, 22)
#     worksheet.set_row(5, 10)





# gear/app/daily_sales/wb_plan_monitor/excel.py
from __future__ import annotations

from io import BytesIO
from typing import Any

import xlsxwriter


# =====================================================================
# Публичные функции
# =====================================================================


def build_wb_plan_excel(data: dict[str, Any]) -> bytes:
    """
    Формирует красивый Excel-отчёт по выполнению плана WB.

    Листы:
    1. "По месяцам" — план, факт, отклонение, выполнение,
       накопительные показатели и диаграмма.
   2. "По дням" — дневной план/факт за весь год,
       накопительные показатели, продажи, возвраты и диаграмма.

    Ожидается результат функции build_plan_analysis().
    Возвращает готовое содержимое XLSX в bytes.
    """
    if not data:
        raise ValueError("Нет данных для формирования отчёта WB.")

    monthly_rows = data.get("monthly_rows") or []
    current_month = data.get("current_month") or {}

    # Для Excel берём детализацию за весь год.
    # Если годовые строки пока не переданы,
    # временно используем строки текущего месяца.
    daily_rows = (
        data.get("year_daily_rows")
        or data.get("daily_rows")
        or current_month.get("rows")
        or []
    )
    report_date = data.get("report_date")

    output = BytesIO()

    workbook = xlsxwriter.Workbook(
        output,
        {
            "in_memory": True,
            "constant_memory": False,
        },
    )

    workbook.set_properties(
        {
            "title": "План / факт WB",
            "subject": "Контроль выполнения плана WB",
            "author": "ТРЕНДСЕТТЕР",
            "company": "ТРЕНДСЕТТЕР",
            "comments": "Сформировано автоматически из панели ежедневных продаж.",
        }
    )

    formats = _build_formats(workbook)

    _write_monthly_sheet(
        workbook=workbook,
        formats=formats,
        data=data,
        rows=monthly_rows,
        report_date=report_date,
    )

    _write_daily_sheet(
        workbook=workbook,
        formats=formats,
        data=data,
        current_month=current_month,
        rows=daily_rows,
        report_date=report_date,
    )

    workbook.close()
    output.seek(0)

    return output.getvalue()


def get_wb_plan_excel_filename(data: dict[str, Any]) -> str:
    """Возвращает имя файла с датой последней загрузки данных."""
    report_date = data.get("report_date") if data else None

    if report_date:
        return f"wb_plan_fact_{report_date:%Y-%m-%d}.xlsx"

    return "wb_plan_fact.xlsx"


# =====================================================================
# Форматы
# =====================================================================


def _build_formats(workbook: xlsxwriter.Workbook) -> dict[str, Any]:
    base_font = "Arial"

    return {
        "title": workbook.add_format(
            {
                "font_name": base_font,
                "font_size": 18,
                "bold": True,
                "font_color": "#0F172A",
                "align": "left",
                "valign": "vcenter",
            }
        ),
        "subtitle": workbook.add_format(
            {
                "font_name": base_font,
                "font_size": 10,
                "font_color": "#64748B",
                "align": "left",
                "valign": "vcenter",
            }
        ),
        "section": workbook.add_format(
            {
                "font_name": base_font,
                "font_size": 11,
                "bold": True,
                "font_color": "#0F172A",
                "bg_color": "#F8FAFC",
                "bottom": 1,
                "bottom_color": "#CBD5E1",
                "align": "left",
                "valign": "vcenter",
            }
        ),
        "header": workbook.add_format(
            {
                "font_name": base_font,
                "font_size": 10,
                "bold": True,
                "font_color": "#FFFFFF",
                "bg_color": "#334155",
                "border": 1,
                "border_color": "#CBD5E1",
                "align": "center",
                "valign": "vcenter",
                "text_wrap": True,
            }
        ),
        "header_plan": workbook.add_format(
            {
                "font_name": base_font,
                "font_size": 10,
                "bold": True,
                "font_color": "#FFFFFF",
                "bg_color": "#4F6BED",
                "border": 1,
                "border_color": "#CBD5E1",
                "align": "center",
                "valign": "vcenter",
                "text_wrap": True,
            }
        ),
        "header_fact": workbook.add_format(
            {
                "font_name": base_font,
                "font_size": 10,
                "bold": True,
                "font_color": "#FFFFFF",
                "bg_color": "#F97316",
                "border": 1,
                "border_color": "#CBD5E1",
                "align": "center",
                "valign": "vcenter",
                "text_wrap": True,
            }
        ),
        "text": workbook.add_format(
            {
                "font_name": base_font,
                "font_size": 10,
                "font_color": "#334155",
                "border": 1,
                "border_color": "#E2E8F0",
                "valign": "vcenter",
            }
        ),
        "text_center": workbook.add_format(
            {
                "font_name": base_font,
                "font_size": 10,
                "font_color": "#334155",
                "border": 1,
                "border_color": "#E2E8F0",
                "align": "center",
                "valign": "vcenter",
            }
        ),
        "date": workbook.add_format(
            {
                "font_name": base_font,
                "font_size": 10,
                "font_color": "#334155",
                "num_format": "dd.mm.yyyy",
                "border": 1,
                "border_color": "#E2E8F0",
                "align": "center",
                "valign": "vcenter",
            }
        ),
        "money": workbook.add_format(
            {
                "font_name": base_font,
                "font_size": 10,
                "font_color": "#334155",
                "num_format": '#,##0.00 "₽";[Red]-#,##0.00 "₽";–',
                "border": 1,
                "border_color": "#E2E8F0",
                "align": "right",
                "valign": "vcenter",
            }
        ),
        "money_bold": workbook.add_format(
            {
                "font_name": base_font,
                "font_size": 10,
                "bold": True,
                "font_color": "#0F172A",
                "num_format": '#,##0.00 "₽";[Red]-#,##0.00 "₽";–',
                "border": 1,
                "border_color": "#CBD5E1",
                "align": "right",
                "valign": "vcenter",
            }
        ),
        "integer": workbook.add_format(
            {
                "font_name": base_font,
                "font_size": 10,
                "font_color": "#334155",
                "num_format": '#,##0;[Red]-#,##0;–',
                "border": 1,
                "border_color": "#E2E8F0",
                "align": "right",
                "valign": "vcenter",
            }
        ),
        "percent": workbook.add_format(
            {
                "font_name": base_font,
                "font_size": 10,
                "font_color": "#334155",
                "num_format": '0.0"%"',
                "border": 1,
                "border_color": "#E2E8F0",
                "align": "right",
                "valign": "vcenter",
            }
        ),
        "total_label": workbook.add_format(
            {
                "font_name": base_font,
                "font_size": 10,
                "bold": True,
                "font_color": "#FFFFFF",
                "bg_color": "#0F172A",
                "border": 1,
                "border_color": "#0F172A",
                "align": "left",
                "valign": "vcenter",
            }
        ),
        "total_money": workbook.add_format(
            {
                "font_name": base_font,
                "font_size": 10,
                "bold": True,
                "font_color": "#FFFFFF",
                "bg_color": "#0F172A",
                "num_format": '#,##0.00 "₽";[Red]-#,##0.00 "₽";–',
                "border": 1,
                "border_color": "#0F172A",
                "align": "right",
                "valign": "vcenter",
            }
        ),
        "total_percent": workbook.add_format(
            {
                "font_name": base_font,
                "font_size": 10,
                "bold": True,
                "font_color": "#FFFFFF",
                "bg_color": "#0F172A",
                "num_format": '0.0"%"',
                "border": 1,
                "border_color": "#0F172A",
                "align": "right",
                "valign": "vcenter",
            }
        ),
        "kpi_label": workbook.add_format(
            {
                "font_name": base_font,
                "font_size": 9,
                "font_color": "#64748B",
                "bg_color": "#F8FAFC",
                "top": 1,
                "left": 1,
                "right": 1,
                "border_color": "#E2E8F0",
                "align": "left",
                "valign": "vcenter",
            }
        ),
        "kpi_value": workbook.add_format(
            {
                "font_name": base_font,
                "font_size": 15,
                "bold": True,
                "font_color": "#0F172A",
                "bg_color": "#F8FAFC",
                "bottom": 1,
                "left": 1,
                "right": 1,
                "border_color": "#E2E8F0",
                "align": "left",
                "valign": "vcenter",
            }
        ),
        "kpi_money": workbook.add_format(
            {
                "font_name": base_font,
                "font_size": 15,
                "bold": True,
                "font_color": "#0F172A",
                "bg_color": "#F8FAFC",
                "num_format": '#,##0 "₽";[Red]-#,##0 "₽";–',
                "bottom": 1,
                "left": 1,
                "right": 1,
                "border_color": "#E2E8F0",
                "align": "left",
                "valign": "vcenter",
            }
        ),
        "kpi_percent": workbook.add_format(
            {
                "font_name": base_font,
                "font_size": 15,
                "bold": True,
                "font_color": "#0F172A",
                "bg_color": "#F8FAFC",
                "num_format": '0.0"%"',
                "bottom": 1,
                "left": 1,
                "right": 1,
                "border_color": "#E2E8F0",
                "align": "left",
                "valign": "vcenter",
            }
        ),
    }


# =====================================================================
# Лист «По месяцам»
# =====================================================================


def _write_monthly_sheet(
    workbook: xlsxwriter.Workbook,
    formats: dict[str, Any],
    data: dict[str, Any],
    rows: list[dict[str, Any]],
    report_date,
) -> None:
    worksheet = workbook.add_worksheet("По месяцам")

    worksheet.hide_gridlines(2)
    worksheet.freeze_panes(10, 1)
    worksheet.set_tab_color("#4F6BED")
    worksheet.set_landscape()
    worksheet.fit_to_pages(1, 1)
    worksheet.set_margins(0.35, 0.35, 0.45, 0.45)
    worksheet.repeat_rows(9, 9)

    worksheet.set_column("A:A", 15)
    worksheet.set_column("B:D", 18)
    worksheet.set_column("E:E", 14)
    worksheet.set_column("F:H", 20)
    worksheet.set_column("I:I", 19)
    worksheet.set_column("J:J", 2)
    worksheet.set_column("K:R", 12)

    worksheet.set_row(0, 28)
    worksheet.merge_range("A1:I1", "План / факт WB по месяцам", formats["title"])

    date_text = report_date.strftime("%d.%m.%Y") if report_date else "—"
    worksheet.merge_range(
        "A2:I2",
        f"Данные на дату последней загрузки: {date_text}",
        formats["subtitle"],
    )

    totals = data.get("totals") or {}

    _write_kpi(
        worksheet,
        formats,
        first_col=0,
        last_col=1,
        label="План за год",
        value=float(totals.get("plan") or 0),
        value_format=formats["kpi_money"],
    )
    _write_kpi(
        worksheet,
        formats,
        first_col=2,
        last_col=3,
        label="Факт на дату отчёта",
        value=float(totals.get("fact") or 0),
        value_format=formats["kpi_money"],
    )
    _write_kpi(
        worksheet,
        formats,
        first_col=4,
        last_col=5,
        label="Отклонение",
        value=float(totals.get("delta") or 0),
        value_format=formats["kpi_money"],
    )
    _write_kpi(
        worksheet,
        formats,
        first_col=6,
        last_col=8,
        label="Выполнение плана",
        value=float(totals.get("exec_pct") or 0),
        value_format=formats["kpi_percent"],
    )

    worksheet.merge_range("A8:I8", "Детализация по месяцам", formats["section"])

    headers = [
        "Месяц",
        "План",
        "Факт",
        "Отклонение",
        "Выполнение",
        "Накопительный план",
        "Накопительный факт",
        "Накопительное отклонение",
        "Накопительное выполнение",
    ]

    header_formats = [
        formats["header"],
        formats["header_plan"],
        formats["header_fact"],
        formats["header"],
        formats["header"],
        formats["header_plan"],
        formats["header_fact"],
        formats["header"],
        formats["header"],
    ]

    header_row = 9
    first_data_row = header_row + 1

    for col, (header, cell_format) in enumerate(zip(headers, header_formats)):
        worksheet.write(header_row, col, header, cell_format)

    worksheet.set_row(header_row, 36)

    for index, row in enumerate(rows, start=first_data_row):
        worksheet.write(index, 0, row.get("month") or "", formats["text"])
        worksheet.write_number(index, 1, float(row.get("plan") or 0), formats["money"])
        worksheet.write_number(index, 2, float(row.get("fact") or 0), formats["money"])
        worksheet.write_number(index, 3, float(row.get("delta") or 0), formats["money"])
        worksheet.write_number(index, 4, float(row.get("exec_pct") or 0), formats["percent"])
        worksheet.write_number(index, 5, float(row.get("running_plan") or 0), formats["money"])
        worksheet.write_number(index, 6, float(row.get("running_fact") or 0), formats["money"])
        worksheet.write_number(index, 7, float(row.get("running_delta") or 0), formats["money"])
        worksheet.write_number(index, 8, float(row.get("running_exec_pct") or 0), formats["percent"])
        worksheet.set_row(index, 21)

    last_data_row = first_data_row + len(rows) - 1
    total_row = last_data_row + 1

    if rows:
        worksheet.write(total_row, 0, "ИТОГО", formats["total_label"])
        worksheet.write_formula(
            total_row,
            1,
            f"=SUM(B{first_data_row + 1}:B{last_data_row + 1})",
            formats["total_money"],
        )
        worksheet.write_formula(
            total_row,
            2,
            f"=SUM(C{first_data_row + 1}:C{last_data_row + 1})",
            formats["total_money"],
        )
        worksheet.write_formula(
            total_row,
            3,
            f"=C{total_row + 1}-B{total_row + 1}",
            formats["total_money"],
        )
        worksheet.write_formula(
            total_row,
            4,
            f'=IFERROR(C{total_row + 1}/B{total_row + 1}*100,0)',
            formats["total_percent"],
        )
        worksheet.write_number(
            total_row,
            5,
            float(rows[-1].get("running_plan") or 0),
            formats["total_money"],
        )
        worksheet.write_number(
            total_row,
            6,
            float(rows[-1].get("running_fact") or 0),
            formats["total_money"],
        )
        worksheet.write_number(
            total_row,
            7,
            float(rows[-1].get("running_delta") or 0),
            formats["total_money"],
        )
        worksheet.write_number(
            total_row,
            8,
            float(rows[-1].get("running_exec_pct") or 0),
            formats["total_percent"],
        )

        worksheet.autofilter(header_row, 0, last_data_row, len(headers) - 1)

        worksheet.conditional_format(
            first_data_row,
            3,
            last_data_row,
            3,
            {
                "type": "cell",
                "criteria": ">=",
                "value": 0,
                "format": workbook.add_format(
                    {
                        "font_color": "#047857",
                        "bg_color": "#ECFDF5",
                    }
                ),
            },
        )
        worksheet.conditional_format(
            first_data_row,
            3,
            last_data_row,
            3,
            {
                "type": "cell",
                "criteria": "<",
                "value": 0,
                "format": workbook.add_format(
                    {
                        "font_color": "#B91C1C",
                        "bg_color": "#FEF2F2",
                    }
                ),
            },
        )
        worksheet.conditional_format(
            first_data_row,
            4,
            last_data_row,
            4,
            {
                "type": "3_color_scale",
                "min_color": "#FECACA",
                "mid_color": "#FEF3C7",
                "max_color": "#D1FAE5",
                "min_type": "num",
                "min_value": 0,
                "mid_type": "num",
                "mid_value": 100,
                "max_type": "num",
                "max_value": 120,
            },
        )

        chart = workbook.add_chart({"type": "column"})

        chart.add_series(
            {
                "name": "План",
                "categories": ["По месяцам", first_data_row, 0, last_data_row, 0],
                "values": ["По месяцам", first_data_row, 1, last_data_row, 1],
                "fill": {"color": "#4F6BED", "transparency": 8},
                "border": {"none": True},
                "gap": 55,
            }
        )
        chart.add_series(
            {
                "name": "Факт",
                "categories": ["По месяцам", first_data_row, 0, last_data_row, 0],
                "values": ["По месяцам", first_data_row, 2, last_data_row, 2],
                "fill": {"color": "#F97316", "transparency": 5},
                "border": {"none": True},
            }
        )

        line_chart = workbook.add_chart({"type": "line"})
        line_chart.add_series(
            {
                "name": "Накопительное выполнение",
                "categories": ["По месяцам", first_data_row, 0, last_data_row, 0],
                "values": ["По месяцам", first_data_row, 8, last_data_row, 8],
                "y2_axis": True,
                "line": {"color": "#0F766E", "width": 2.5},
                "marker": {
                    "type": "circle",
                    "size": 6,
                    "border": {"color": "#0F766E"},
                    "fill": {"color": "#FFFFFF"},
                },
            }
        )
        chart.combine(line_chart)

        chart.set_title(
            {
                "name": "План / факт по месяцам",
                "name_font": {"name": "Arial", "size": 13, "bold": True},
            }
        )
        chart.set_legend({"position": "top"})
        chart.set_chartarea({"border": {"none": True}, "fill": {"color": "#FFFFFF"}})
        chart.set_plotarea(
            {
                "border": {"none": True},
                "fill": {"color": "#FFFFFF"},
            }
        )
        chart.set_x_axis(
            {
                "label_position": "low",
                "major_tick_mark": "none",
                "line": {"color": "#CBD5E1"},
            }
        )
        chart.set_y_axis(
            {
                "name": "Сумма, ₽",
                "num_format": '#,##0,," млн"',
                "major_gridlines": {"visible": True, "line": {"color": "#E2E8F0"}},
                "line": {"none": True},
            }
        )
        chart.set_y2_axis(
            {
                "name": "Выполнение, %",
                "num_format": '0"%"',
                "min": 0,
                "major_gridlines": {"visible": False},
                "line": {"none": True},
            }
        )
        chart.set_size({"width": 820, "height": 390})

        worksheet.insert_chart("K2", chart, {"x_offset": 8, "y_offset": 4})

    worksheet.set_footer(
        "&LТРЕНДСЕТТЕР&RСтраница &P из &N",
        {"margin": 0.25},
    )


# =====================================================================
# Лист «По дням»
# =====================================================================


def _write_daily_sheet(
    workbook: xlsxwriter.Workbook,
    formats: dict[str, Any],
    data: dict[str, Any],
    current_month: dict[str, Any],
    rows: list[dict[str, Any]],
    report_date,
) -> None:
    worksheet = workbook.add_worksheet("По дням")

    worksheet.hide_gridlines(2)
    worksheet.freeze_panes(10, 2)
    worksheet.set_tab_color("#F97316")
    worksheet.set_landscape()
    worksheet.fit_to_pages(1, 0)
    worksheet.set_margins(0.30, 0.30, 0.45, 0.45)
    worksheet.repeat_rows(9, 9)

    widths = {
        "A:A": 12,
        "B:B": 10,
        "C:E": 18,
        "F:F": 14,
        "G:I": 18,
        "J:K": 15,
        "L:L": 18,
        "M:N": 15,
        "O:O": 2,
        "P:W": 12,
    }
    for column_range, width in widths.items():
        worksheet.set_column(column_range, width)

    worksheet.set_row(0, 28)
    report_year = report_date.year if report_date else ""

    worksheet.merge_range(
        "A1:N1",
        f"План / факт WB по дням — {report_year} год",
        formats["title"],
    )

    date_text = report_date.strftime("%d.%m.%Y") if report_date else "—"
    worksheet.merge_range(
        "A2:N2",
        f"Данные на дату последней загрузки: {date_text}",
        formats["subtitle"],
    )

    _write_kpi(
        worksheet,
        formats,
        first_col=0,
        last_col=2,
        label="План текущего месяца",
        value=float(current_month.get("month_plan") or 0),
        value_format=formats["kpi_money"],
    )
    _write_kpi(
        worksheet,
        formats,
        first_col=3,
        last_col=5,
        label="Факт текущего месяца",
        value=float(current_month.get("fact_to_date") or 0),
        value_format=formats["kpi_money"],
    )
    _write_kpi(
        worksheet,
        formats,
        first_col=6,
        last_col=8,
        label="План на текущую дату",
        value=float(current_month.get("plan_to_date") or 0),
        value_format=formats["kpi_money"],
    )
    _write_kpi(
        worksheet,
        formats,
        first_col=9,
        last_col=10,
        label="Выполнение к дате",
        value=float(current_month.get("exec_to_date_pct") or 0),
        value_format=formats["kpi_percent"],
    )
    _write_kpi(
        worksheet,
        formats,
        first_col=11,
        last_col=13,
        label="Отклонение от графика",
        value=float(current_month.get("delta_to_date") or 0),
        value_format=formats["kpi_money"],
    )

    worksheet.merge_range("A8:N8", "Детализация по дням", formats["section"])

    headers = [
        "Дата",
        "День недели",
        "План за день",
        "Факт за день",
        "Отклонение за день",
        "Выполнение дня",
        "План к дате",
        "Факт к дате",
        "Отклонение к дате",
        "Выполнение к дате",
        "Продажи",
        "Возвраты",
        "Количество net",
        "Средняя цена",
    ]

    header_formats = [
        formats["header"],
        formats["header"],
        formats["header_plan"],
        formats["header_fact"],
        formats["header"],
        formats["header"],
        formats["header_plan"],
        formats["header_fact"],
        formats["header"],
        formats["header"],
        formats["header_fact"],
        formats["header"],
        formats["header"],
        formats["header"],
    ]

    header_row = 9
    first_data_row = header_row + 1

    for col, (header, cell_format) in enumerate(zip(headers, header_formats)):
        worksheet.write(header_row, col, header, cell_format)

    worksheet.set_row(header_row, 42)

    for index, row in enumerate(rows, start=first_data_row):
        daily_plan = float(row.get("daily_plan") or 0)
        fact = float(row.get("fact") or 0)
        running_plan = float(row.get("running_plan") or 0)
        running_fact = float(row.get("running_fact") or 0)

        daily_delta = fact - daily_plan
        daily_exec_pct = fact / daily_plan * 100 if daily_plan else 0
        running_delta = running_fact - running_plan
        running_exec_pct = float(row.get("exec_to_date_pct") or 0)

        worksheet.write_datetime(index, 0, row["date"], formats["date"])
        worksheet.write(index, 1, row.get("weekday") or "", formats["text_center"])
        worksheet.write_number(index, 2, daily_plan, formats["money"])
        worksheet.write_number(index, 3, fact, formats["money"])
        worksheet.write_number(index, 4, daily_delta, formats["money"])
        worksheet.write_number(index, 5, daily_exec_pct, formats["percent"])
        worksheet.write_number(index, 6, running_plan, formats["money"])
        worksheet.write_number(index, 7, running_fact, formats["money"])
        worksheet.write_number(index, 8, running_delta, formats["money"])
        worksheet.write_number(index, 9, running_exec_pct, formats["percent"])
        worksheet.write_number(index, 10, float(row.get("sales_amount") or 0), formats["money"])
        worksheet.write_number(index, 11, float(row.get("returns_amount") or 0), formats["money"])
        worksheet.write_number(index, 12, int(row.get("qty") or 0), formats["integer"])
        worksheet.write_number(index, 13, float(row.get("avg_price") or 0), formats["money"])
        worksheet.set_row(index, 21)

    last_data_row = first_data_row + len(rows) - 1
    total_row = last_data_row + 1

    if rows:
        worksheet.write(total_row, 0, "ИТОГО", formats["total_label"])
        worksheet.write(total_row, 1, "", formats["total_label"])
        worksheet.write_formula(
            total_row,
            2,
            f"=SUM(C{first_data_row + 1}:C{last_data_row + 1})",
            formats["total_money"],
        )
        worksheet.write_formula(
            total_row,
            3,
            f"=SUM(D{first_data_row + 1}:D{last_data_row + 1})",
            formats["total_money"],
        )
        worksheet.write_formula(
            total_row,
            4,
            f"=D{total_row + 1}-C{total_row + 1}",
            formats["total_money"],
        )
        worksheet.write_formula(
            total_row,
            5,
            f'=IFERROR(D{total_row + 1}/C{total_row + 1}*100,0)',
            formats["total_percent"],
        )
        worksheet.write_number(
            total_row,
            6,
            float(rows[-1].get("running_plan") or 0),
            formats["total_money"],
        )
        worksheet.write_number(
            total_row,
            7,
            float(rows[-1].get("running_fact") or 0),
            formats["total_money"],
        )
        worksheet.write_formula(
            total_row,
            8,
            f"=H{total_row + 1}-G{total_row + 1}",
            formats["total_money"],
        )
        worksheet.write_number(
            total_row,
            9,
            float(rows[-1].get("exec_to_date_pct") or 0),
            formats["total_percent"],
        )
        worksheet.write_formula(
            total_row,
            10,
            f"=SUM(K{first_data_row + 1}:K{last_data_row + 1})",
            formats["total_money"],
        )
        worksheet.write_formula(
            total_row,
            11,
            f"=SUM(L{first_data_row + 1}:L{last_data_row + 1})",
            formats["total_money"],
        )
        worksheet.write_formula(
            total_row,
            12,
            f"=SUM(M{first_data_row + 1}:M{last_data_row + 1})",
            formats["total_money"],
        )
        worksheet.write_formula(
            total_row,
            13,
            f'=IFERROR(D{total_row + 1}/M{total_row + 1},0)',
            formats["total_money"],
        )

        worksheet.autofilter(header_row, 0, last_data_row, len(headers) - 1)

        for col in (4, 8):
            worksheet.conditional_format(
                first_data_row,
                col,
                last_data_row,
                col,
                {
                    "type": "cell",
                    "criteria": ">=",
                    "value": 0,
                    "format": workbook.add_format(
                        {
                            "font_color": "#047857",
                            "bg_color": "#ECFDF5",
                        }
                    ),
                },
            )
            worksheet.conditional_format(
                first_data_row,
                col,
                last_data_row,
                col,
                {
                    "type": "cell",
                    "criteria": "<",
                    "value": 0,
                    "format": workbook.add_format(
                        {
                            "font_color": "#B91C1C",
                            "bg_color": "#FEF2F2",
                        }
                    ),
                },
            )

        worksheet.conditional_format(
            first_data_row,
            9,
            last_data_row,
            9,
            {
                "type": "3_color_scale",
                "min_color": "#FECACA",
                "mid_color": "#FEF3C7",
                "max_color": "#D1FAE5",
                "min_type": "num",
                "min_value": 0,
                "mid_type": "num",
                "mid_value": 100,
                "max_type": "num",
                "max_value": 120,
            },
        )

        chart = workbook.add_chart({"type": "line"})

        chart.add_series(
            {
                "name": "План к дате",
                "categories": ["По дням", first_data_row, 0, last_data_row, 0],
                "values": ["По дням", first_data_row, 6, last_data_row, 6],
                "line": {"color": "#F97316", "width": 2.25, "dash_type": "dash"},
                "marker": {"type": "none"},
            }
        )
        chart.add_series(
            {
                "name": "Факт к дате",
                "categories": ["По дням", first_data_row, 0, last_data_row, 0],
                "values": ["По дням", first_data_row, 7, last_data_row, 7],
                "line": {"color": "#2563EB", "width": 2.75},
                "marker": {
                    "type": "circle",
                    "size": 4,
                    "border": {"color": "#2563EB"},
                    "fill": {"color": "#FFFFFF"},
                },
            }
        )

        chart.set_title(
            {
                "name": f"Накопительный план / факт за {report_year} год",
                "name_font": {"name": "Arial", "size": 13, "bold": True},
            }
        )
        chart.set_legend({"position": "top"})
        chart.set_chartarea({"border": {"none": True}, "fill": {"color": "#FFFFFF"}})
        chart.set_plotarea({"border": {"none": True}, "fill": {"color": "#FFFFFF"}})
        chart.set_x_axis(
            {
                "num_format": "dd.mm",
                "date_axis": True,
                "label_position": "low",
                "major_tick_mark": "none",
                "line": {"color": "#CBD5E1"},
            }
        )
        chart.set_y_axis(
            {
                "name": "Сумма, ₽",
                "num_format": '#,##0,," млн"',
                "major_gridlines": {"visible": True, "line": {"color": "#E2E8F0"}},
                "line": {"none": True},
            }
        )
        chart.set_size({"width": 820, "height": 390})

        worksheet.insert_chart("P2", chart, {"x_offset": 8, "y_offset": 4})

    worksheet.set_footer(
        "&LТРЕНДСЕТТЕР&RСтраница &P из &N",
        {"margin": 0.25},
    )


# =====================================================================
# Вспомогательные функции
# =====================================================================


def _write_kpi(
    worksheet,
    formats: dict[str, Any],
    first_col: int,
    last_col: int,
    label: str,
    value: float,
    value_format,
) -> None:
    worksheet.merge_range(3, first_col, 3, last_col, label, formats["kpi_label"])
    worksheet.merge_range(4, first_col, 5, last_col, value, value_format)
    worksheet.set_row(3, 18)
    worksheet.set_row(4, 22)
    worksheet.set_row(5, 10)
