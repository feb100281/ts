# #  gear/app/daily_sales/wb_plan_monitor/prophet_note/builder.py
# from __future__ import annotations

# from datetime import date
# from io import BytesIO
# from typing import Any

# from reportlab.lib import colors
# from reportlab.lib.pagesizes import A4
# from reportlab.lib.units import mm
# from reportlab.platypus import (
#     BaseDocTemplate,
#     Frame,
#     Image,
#     KeepTogether,
#     PageBreak,
#     PageTemplate,
#     Paragraph,
#     Spacer,
#     Table,
#     TableStyle,
# )

# from .calculations import (
#     build_note_context,
#     conclusion_direction,
#     conclusion_status,
# )
# from .charts import (
#     build_monthly_plan_chart,
#     build_period_comparison_chart,
# )
# from .config import get_note_config
# from .formatting import (
#     format_date_ru,
#     format_date_short,
#     format_money,
#     format_money_mln,
#     format_pct,
#     signed_money,
# )
# from .styles import (
#     ACCENT,
#     BLUE_BG,
#     BORDER,
#     GREEN_BG,
#     LIGHT_BG,
#     MUTED,
#     PLAN,
#     PRIMARY,
#     RED_BG,
#     build_styles,
# )


# PAGE_WIDTH, PAGE_HEIGHT = A4
# LEFT_MARGIN = 18 * mm
# RIGHT_MARGIN = 18 * mm
# TOP_MARGIN = 17 * mm
# BOTTOM_MARGIN = 17 * mm


# def build_prophet_note_pdf(
#     result: dict[str, Any],
#     author_name: str | None = None,
#     author_position: str | None = None,
#     prepared_at: date | None = None,
# ) -> bytes:
#     """
#     Формирует пояснительную записку PDF из результата build_forecast().

#     PDF строится из уже рассчитанного result.
#     Повторный запуск Prophet не выполняется.
#     """
#     context = build_note_context(result)
#     config = get_note_config()
#     prepared_at = prepared_at or date.today()
#     author_name = author_name or config.author_name
#     author_position = (
#         author_position
#         if author_position is not None
#         else config.author_position
#     )

#     output = BytesIO()
#     styles = build_styles()

#     doc = BaseDocTemplate(
#         output,
#         pagesize=A4,
#         leftMargin=LEFT_MARGIN,
#         rightMargin=RIGHT_MARGIN,
#         topMargin=TOP_MARGIN,
#         bottomMargin=BOTTOM_MARGIN,
#         title=config.document_title,
#         author=author_name,
#         subject="Прогноз продаж Wildberries на основе Prophet",
#         creator=config.company_name,
#     )

#     frame = Frame(
#         LEFT_MARGIN,
#         BOTTOM_MARGIN,
#         PAGE_WIDTH - LEFT_MARGIN - RIGHT_MARGIN,
#         PAGE_HEIGHT - TOP_MARGIN - BOTTOM_MARGIN,
#         id="main_frame",
#     )

#     doc.addPageTemplates(
#         [
#             PageTemplate(
#                 id="main",
#                 frames=[frame],
#                 onPage=lambda canvas, current_doc: _draw_page(
#                     canvas=canvas,
#                     doc=current_doc,
#                     company_name=config.company_name,
#                     styles=styles,
#                 ),
#             )
#         ]
#     )

#     story = []

#     story.extend(
#         _build_cover_section(
#             context=context,
#             styles=styles,
#             company_name=config.company_name,
#         )
#     )

#     story.append(PageBreak())

#     story.extend(
#         _build_methodology_section(
#             context=context,
#             styles=styles,
#         )
#     )

#     story.append(PageBreak())

#     story.extend(
#         _build_monthly_section(
#             context=context,
#             styles=styles,
#         )
#     )

#     story.append(PageBreak())

#     story.extend(
#         _build_period_section(
#             context=context,
#             styles=styles,
#             author_name=author_name,
#             author_position=author_position,
#             prepared_at=prepared_at,
#         )
#     )

#     doc.build(story)
#     output.seek(0)
#     return output.getvalue()


# def get_prophet_note_filename(
#     result: dict[str, Any],
# ) -> str:
#     params = result.get("params") or {}
#     report_date = params.get("date_end")

#     if report_date:
#         return (
#             "wb_prophet_explanatory_note_"
#             f"{report_date}.pdf"
#         )

#     return "wb_prophet_explanatory_note.pdf"


# def _draw_page(
#     canvas,
#     doc,
#     company_name: str,
#     styles,
# ):
#     canvas.saveState()

#     regular = styles["font_regular"]
#     bold = styles["font_bold"]

#     canvas.setStrokeColor(BORDER)
#     canvas.setLineWidth(0.5)
#     canvas.line(
#         LEFT_MARGIN,
#         12 * mm,
#         PAGE_WIDTH - RIGHT_MARGIN,
#         12 * mm,
#     )

#     canvas.setFont(regular, 7.5)
#     canvas.setFillColor(MUTED)
#     canvas.drawString(
#         LEFT_MARGIN,
#         7.5 * mm,
#         (
#             f"{company_name} | "
#             "Прогноз продаж WB на основе Prophet"
#         ),
#     )

#     canvas.drawRightString(
#         PAGE_WIDTH - RIGHT_MARGIN,
#         7.5 * mm,
#         f"Страница {doc.page}",
#     )

#     canvas.setFont(bold, 7)
#     canvas.setFillColor(ACCENT)
#     canvas.drawRightString(
#         PAGE_WIDTH - RIGHT_MARGIN,
#         PAGE_HEIGHT - 10 * mm,
#         "УПРАВЛЕНЧЕСКИЙ АНАЛИЗ",
#     )

#     canvas.restoreState()


# def _build_cover_section(
#     context,
#     styles,
#     company_name: str,
# ):
#     params = context["params"]
#     year_period = context["year_period"]

#     elements = [
#         Spacer(1, 4 * mm),
#         Paragraph(
#             "Пояснительная записка",
#             styles["title"],
#         ),
#         Paragraph(
#             (
#                 "к прогнозу продаж Wildberries "
#                 f"на {context['year']} год"
#             ),
#             styles["title"],
#         ),
#         Paragraph(
#             (
#                 "Прогноз сформирован на основании модели "
#                 "временных рядов Prophet по дневной "
#                 "net-выручке: продажи за вычетом возвратов."
#             ),
#             styles["subtitle"],
#         ),
#         _info_table(
#             rows=[
#                 (
#                     "Дата фактических данных",
#                     format_date_short(context["date_end"]),
#                 ),
#                 (
#                     "Период обучения модели",
#                     (
#                         f"{format_date_short(context['date_start'])}"
#                         " - "
#                         f"{format_date_short(context['date_end'])}"
#                     ),
#                 ),
#                 (
#                     "Горизонт прогнозирования",
#                     (
#                         f"{format_date_short(context['date_end'])}"
#                         " - "
#                         f"{format_date_short(context['forecast_end'])}"
#                     ),
#                 ),
#                 (
#                     "Сценарная корректировка",
#                     format_pct(
#                         context["scenario_growth"],
#                         2,
#                     ),
#                 ),
#             ],
#             styles=styles,
#         ),
#         Spacer(1, 5 * mm),
#         _kpi_grid(
#             values=[
#                 (
#                     "Факт текущего года",
#                     f"{format_money_mln(year_period.fact)} млн ₽",
#                 ),
#                 (
#                     "Прогноз до конца года",
#                     f"{format_money_mln(year_period.forecast)} млн ₽",
#                 ),
#                 (
#                     "Ожидаемый итог года",
#                     f"{format_money_mln(year_period.expected)} млн ₽",
#                 ),
#                 (
#                     "Годовой план WB",
#                     f"{format_money_mln(year_period.plan)} млн ₽",
#                 ),
#                 (
#                     "Ожидаемое выполнение",
#                     format_pct(year_period.execution_pct),
#                 ),
#                 (
#                     "Отклонение от плана",
#                     (
#                         f"{signed_money(year_period.delta)} ₽"
#                     ),
#                 ),
#             ],
#             styles=styles,
#         ),
#         Spacer(1, 6 * mm),
#         Paragraph(
#             "Основной вывод",
#             styles["heading"],
#         ),
#         _conclusion_box(
#             context=context,
#             styles=styles,
#         ),
#         Spacer(1, 5 * mm),
#         Paragraph(
#             (
#                 "Настоящий прогноз является расчётной оценкой "
#                 "при сохранении выявленной динамики продаж. "
#                 "Он не является гарантией достижения указанного "
#                 "результата и должен использоваться совместно "
#                 "с операционной информацией о доступности товара, "
#                 "логистике, рекламе и работе складов WB."
#             ),
#             styles["small"],
#         ),
#     ]

#     return elements


# def _build_methodology_section(
#     context,
#     styles,
# ):
#     params = context["params"]
#     training_days = context["training_days"]
#     forecast_days = context["forecast_days"]

#     rows = [
#         (
#             "Метод",
#             "Prophet, линейный тренд",
#             (
#                 "Модель временных рядов с трендом "
#                 "и сезонными компонентами."
#             ),
#         ),
#         (
#             "Целевой показатель",
#             "Дневная net-выручка",
#             "Продажи минус возвраты.",
#         ),
#         (
#             "Период обучения",
#             (
#                 f"{format_date_short(context['date_start'])}"
#                 " - "
#                 f"{format_date_short(context['date_end'])}"
#             ),
#             f"{training_days} календарных дней.",
#         ),
#         (
#             "Горизонт прогноза",
#             (
#                 f"{format_date_short(context['date_end'])}"
#                 " - "
#                 f"{format_date_short(context['forecast_end'])}"
#             ),
#             f"{forecast_days} прогнозных дней.",
#         ),
#         (
#             "Гибкость тренда",
#             str(params.get("changepoint_prior_scale", "")),
#             (
#                 "Чувствительность модели к изменениям "
#                 "направления тренда."
#             ),
#         ),
#         (
#             "Сила сезонности",
#             str(params.get("seasonality_prior_scale", "")),
#             "Степень влияния сезонных колебаний.",
#         ),
#         (
#             "Тип сезонности",
#             _seasonality_label(
#                 params.get("seasonality_mode")
#             ),
#             (
#                 "Мультипликативная сезонность изменяется "
#                 "вместе с уровнем продаж."
#             ),
#         ),
#         (
#             "Доверительный интервал",
#             format_pct(
#                 float(params.get("interval_width") or 0) * 100,
#                 0,
#             ),
#             "Диапазон неопределённости прогноза.",
#         ),
#         (
#             "Сглаживание выбросов",
#             (
#                 "Да"
#                 if params.get("clip_outliers")
#                 else "Нет"
#             ),
#             (
#                 "Ограничение влияния аномально высоких "
#                 "или низких дней."
#             ),
#         ),
#         (
#             "Сценарная корректировка",
#             format_pct(
#                 float(params.get("growth_pct") or 0),
#                 2,
#             ),
#             (
#                 "Управленческая корректировка применяется "
#                 "только к будущему прогнозу."
#             ),
#         ),
#     ]

#     elements = [
#         Paragraph(
#             "1. Методология и параметры модели",
#             styles["title"],
#         ),
#         Paragraph(
#             (
#                 "Prophet - модель прогнозирования временных рядов. "
#                 "Она оценивает общий тренд и повторяющиеся "
#                 "сезонные закономерности. В расчёте используется "
#                 "дневная net-выручка, сформированная как продажи "
#                 "за вычетом возвратов."
#             ),
#             styles["body"],
#         ),
#         Paragraph(
#             (
#                 "Минимально допустимый период обучения "
#                 "в интерфейсе может быть установлен на уровне "
#                 "30 календарных дней. Для базового прогноза "
#                 "рекомендуется не менее 60 дней. Полная годовая "
#                 "сезонность оценивается только при наличии "
#                 "не менее 365 дней истории."
#             ),
#             styles["body"],
#         ),
#         Spacer(1, 3 * mm),
#         _method_table(rows, styles),
#         Spacer(1, 5 * mm),
#         Paragraph(
#             "Ограничения интерпретации",
#             styles["heading"],
#         ),
#         Paragraph(
#             (
#                 "Модель анализирует значения временного ряда, "
#                 "но не устанавливает причинно-следственные связи. "
#                 "Снижение продаж из-за перебоев в работе складов, "
#                 "дефицита товара, ограничений логистики или иных "
#                 "операционных факторов отражается в прогнозе как "
#                 "изменение динамики, если эти события уже проявились "
#                 "в фактических данных."
#             ),
#             styles["body"],
#         ),
#         Paragraph(
#             (
#                 "При резком изменении внешних условий рекомендуется "
#                 "сравнивать базовый прогноз за 60 дней с оперативным "
#                 "сценарием за 30 дней и отдельно фиксировать "
#                 "управленческую корректировку."
#             ),
#             styles["body"],
#         ),
#     ]

#     return elements


# def _build_monthly_section(
#     context,
#     styles,
# ):
#     chart = build_monthly_plan_chart(
#         context["monthly"]
#     )

#     table_rows = []
#     for row in context["monthly"]:
#         table_rows.append(
#             [
#                 str(row.get("month") or ""),
#                 format_money_mln(row.get("plan") or 0),
#                 format_money_mln(row.get("fact") or 0),
#                 format_money_mln(row.get("forecast") or 0),
#                 format_money_mln(
#                     row.get("expected_total") or 0
#                 ),
#                 format_money_mln(
#                     row.get("delta_to_plan") or 0
#                 ),
#                 format_pct(
#                     row.get("plan_exec_pct") or 0
#                 ),
#             ]
#         )

#     return [
#         Paragraph(
#             "2. Сравнение прогноза с планом WB",
#             styles["title"],
#         ),
#         Paragraph(
#             (
#                 "Для завершённых месяцев ожидаемый итог равен "
#                 "фактической выручке. Для текущего месяца он "
#                 "складывается из факта по дату отчёта и прогноза "
#                 "оставшихся дней. Для будущих месяцев ожидаемый "
#                 "итог соответствует прогнозу Prophet."
#             ),
#             styles["body"],
#         ),
#         Image(
#             chart,
#             width=172 * mm,
#             height=75 * mm,
#         ),
#         Spacer(1, 4 * mm),
#         _monthly_table(
#             table_rows,
#             styles,
#         ),
#     ]


# def _build_period_section(
#     context,
#     styles,
#     author_name: str,
#     author_position: str,
#     prepared_at: date,
# ):
#     year_period = context["year_period"]
#     half_period = context["half_period"]

#     chart = build_period_comparison_chart(
#         year_period,
#         half_period,
#     )

#     rows = [
#         [
#             "Показатель",
#             year_period.label,
#             half_period.label,
#         ],
#         [
#             "План WB, млн ₽",
#             format_money_mln(year_period.plan),
#             format_money_mln(half_period.plan),
#         ],
#         [
#             "Факт, млн ₽",
#             format_money_mln(year_period.fact),
#             format_money_mln(half_period.fact),
#         ],
#         [
#             "Прогнозная часть, млн ₽",
#             format_money_mln(year_period.forecast),
#             format_money_mln(half_period.forecast),
#         ],
#         [
#             "Ожидаемый итог, млн ₽",
#             format_money_mln(year_period.expected),
#             format_money_mln(half_period.expected),
#         ],
#         [
#             "Выполнение плана",
#             format_pct(year_period.execution_pct),
#             format_pct(half_period.execution_pct),
#         ],
#         [
#             "Отклонение, млн ₽",
#             format_money_mln(year_period.delta),
#             format_money_mln(half_period.delta),
#         ],
#     ]

#     author_text = author_name
#     if author_position:
#         author_text += f"<br/>{author_position}"

#     return [
#         Paragraph(
#             "3. Итоги года и текущего полугодия",
#             styles["title"],
#         ),
#         Image(
#             chart,
#             width=145 * mm,
#             height=78 * mm,
#         ),
#         Spacer(1, 4 * mm),
#         _period_table(rows, styles),
#         Spacer(1, 6 * mm),
#         Paragraph(
#                 "Вывод по текущему полугодию",
#                 styles["heading"],
#             ),

#             _period_conclusion_box(
#                 half_period,
#                 styles,
#             ),
#                     Spacer(1, 8 * mm),
#         Table(
#             [
#                 [
#                     Paragraph(
#                         "<b>Подготовил анализ</b>",
#                         styles["body"],
#                     ),
#                     Paragraph(
#                         author_text,
#                         styles["body"],
#                     ),
#                 ],
#                 [
#                     Paragraph(
#                         "<b>Дата формирования</b>",
#                         styles["body"],
#                     ),
#                     Paragraph(
#                         format_date_ru(prepared_at),
#                         styles["body"],
#                     ),
#                 ],
#             ],
#             colWidths=[
#                 48 * mm,
#                 110 * mm,
#             ],
#             style=TableStyle(
#                 [
#                     (
#                         "LINEABOVE",
#                         (0, 0),
#                         (-1, 0),
#                         0.7,
#                         BORDER,
#                     ),
#                     (
#                         "TOPPADDING",
#                         (0, 0),
#                         (-1, -1),
#                         6,
#                     ),
#                     (
#                         "BOTTOMPADDING",
#                         (0, 0),
#                         (-1, -1),
#                         6,
#                     ),
#                     (
#                         "VALIGN",
#                         (0, 0),
#                         (-1, -1),
#                         "TOP",
#                     ),
#                 ]
#             ),
#         ),
#         Spacer(1, 6 * mm),
#         Paragraph(
#             (
#                 "Документ сформирован автоматически на основании "
#                 "параметров прогноза, выбранных пользователем "
#                 "в аналитической панели."
#             ),
#             styles["small"],
#         ),
#     ]


# def _conclusion_box(context, styles):
#     period = context["year_period"]
#     status = conclusion_status(period.execution_pct)
#     direction = conclusion_direction(period.delta)

#     text = (
#         f"На основании фактической динамики продаж по состоянию "
#         f"на {format_date_ru(context['date_end'])} ожидаемый объём "
#         f"продаж за {context['year']} год составляет "
#         f"<b>{format_money_mln(period.expected)} млн ₽</b>. "
#         f"При годовом плане WB "
#         f"<b>{format_money_mln(period.plan)} млн ₽</b> ожидаемое "
#         f"выполнение составляет "
#         f"<b>{format_pct(period.execution_pct)}</b>. "
#         f"Расчётное отклонение - "
#         f"<b>{signed_money(period.delta)} ₽</b>; "
#         f"ожидаемый результат {status} и {direction}."
#     )

#     background = (
#         GREEN_BG
#         if period.delta >= 0
#         else RED_BG
#     )

#     table = Table(
#         [[Paragraph(text, styles["body"])]],
#         colWidths=[166 * mm],
#     )
#     table.setStyle(
#         TableStyle(
#             [
#                 ("BACKGROUND", (0, 0), (-1, -1), background),
#                 ("BOX", (0, 0), (-1, -1), 0.7, BORDER),
#                 ("LEFTPADDING", (0, 0), (-1, -1), 10),
#                 ("RIGHTPADDING", (0, 0), (-1, -1), 10),
#                 ("TOPPADDING", (0, 0), (-1, -1), 9),
#                 ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
#             ]
#         )
#     )
#     return table




# def _period_conclusion_box(
#     period,
#     styles,
# ):
#     """
#     Выделенный управленческий вывод по году или полугодию.

#     Цвет блока зависит от ожидаемого выполнения:
#     - зелёный — план выполняется;
#     - жёлтый — выполнение близко к плану;
#     - красный — существенное недовыполнение.
#     """
#     execution_pct = float(
#         period.execution_pct or 0
#     )

#     delta = float(
#         period.delta or 0
#     )

#     if execution_pct >= 100:
#         background = GREEN_BG
#         accent_color = colors.HexColor("#15803D")
#         status_text = "ожидается выполнение или превышение плана"

#     elif execution_pct >= 95:
#         background = colors.HexColor("#FFFBEB")
#         accent_color = colors.HexColor("#D97706")
#         status_text = "результат близок к плановому уровню"

#     else:
#         background = RED_BG
#         accent_color = colors.HexColor("#B91C1C")
#         status_text = "ожидается недовыполнение плана"

#     delta_sign = (
#         "+"
#         if delta > 0
#         else ""
#     )

#     text = (
#         f"По итогам периода «{period.label}» ожидаемый объём "
#         f"продаж составляет "
#         f"<b>{format_money_mln(period.expected)} млн ₽</b> "
#         f"при плане {format_money_mln(period.plan)} млн ₽. "
#         f"Ожидаемое выполнение составляет "
#         f"<b>{format_pct(period.execution_pct)}</b>. "
#         f"Отклонение от плана — "
#         f"{delta_sign}{format_money_mln(delta)} млн ₽. "
#         f"На основании расчёта {status_text}."
#     )

#     content = Table(
#         [
#             [
#                 "",
#                 Paragraph(
#                     text,
#                     styles["body"],
#                 ),
#             ]
#         ],
#         colWidths=[
#             3 * mm,
#             163 * mm,
#         ],
#     )

#     content.setStyle(
#         TableStyle(
#             [
#                 # Цветная вертикальная полоса
#                 (
#                     "BACKGROUND",
#                     (0, 0),
#                     (0, -1),
#                     accent_color,
#                 ),

#                 # Основная подложка
#                 (
#                     "BACKGROUND",
#                     (1, 0),
#                     (1, -1),
#                     background,
#                 ),

#                 # Рамка
#                 (
#                     "BOX",
#                     (0, 0),
#                     (-1, -1),
#                     0.6,
#                     BORDER,
#                 ),

#                 (
#                     "VALIGN",
#                     (0, 0),
#                     (-1, -1),
#                     "MIDDLE",
#                 ),

#                 (
#                     "LEFTPADDING",
#                     (0, 0),
#                     (0, -1),
#                     0,
#                 ),
#                 (
#                     "RIGHTPADDING",
#                     (0, 0),
#                     (0, -1),
#                     0,
#                 ),

#                 (
#                     "LEFTPADDING",
#                     (1, 0),
#                     (1, -1),
#                     10,
#                 ),
#                 (
#                     "RIGHTPADDING",
#                     (1, 0),
#                     (1, -1),
#                     10,
#                 ),
#                 (
#                     "TOPPADDING",
#                     (1, 0),
#                     (1, -1),
#                     9,
#                 ),
#                 (
#                     "BOTTOMPADDING",
#                     (1, 0),
#                     (1, -1),
#                     9,
#                 ),
#             ]
#         )
#     )

#     return content


# def _info_table(rows, styles):
#     data = [
#         [
#             Paragraph(label, styles["table_cell"]),
#             Paragraph(value, styles["table_cell_right"]),
#         ]
#         for label, value in rows
#     ]

#     table = Table(
#         data,
#         colWidths=[
#             78 * mm,
#             88 * mm,
#         ],
#     )
#     table.setStyle(
#         TableStyle(
#             [
#                 ("BACKGROUND", (0, 0), (0, -1), LIGHT_BG),
#                 ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
#                 ("INNERGRID", (0, 0), (-1, -1), 0.4, BORDER),
#                 ("LEFTPADDING", (0, 0), (-1, -1), 7),
#                 ("RIGHTPADDING", (0, 0), (-1, -1), 7),
#                 ("TOPPADDING", (0, 0), (-1, -1), 6),
#                 ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
#             ]
#         )
#     )
#     return table


# def _kpi_grid(values, styles):
#     """
#     Формирует KPI-карточки строго по ширине основной таблицы.

#     Общая ширина блока:
#         166 мм

#     Между карточками:
#         3 мм

#     Ширина одной карточки:
#         (166 - 3 - 3) / 3 = 53,33 мм
#     """

#     total_width = 166 * mm
#     gap_width = 3 * mm

#     card_width = (
#         total_width
#         - gap_width * 2
#     ) / 3

#     # Цвет верхней линии и мягкий фон карточек.
#     card_themes = [
#         {
#             "accent": colors.HexColor("#2563EB"),
#             "background": colors.HexColor("#F8FAFF"),
#         },
#         {
#             "accent": colors.HexColor("#0F766E"),
#             "background": colors.HexColor("#F5FBFA"),
#         },
#         {
#             "accent": colors.HexColor("#334155"),
#             "background": colors.HexColor("#F8FAFC"),
#         },
#         {
#             "accent": colors.HexColor("#F97316"),
#             "background": colors.HexColor("#FFF9F5"),
#         },
#         {
#             "accent": colors.HexColor("#15803D"),
#             "background": colors.HexColor("#F5FBF6"),
#         },
#         {
#             "accent": colors.HexColor("#B91C1C"),
#             "background": colors.HexColor("#FFF7F7"),
#         },
#     ]

#     rows = []

#     for row_start in range(
#         0,
#         len(values),
#         3,
#     ):
#         row_values = values[
#             row_start:row_start + 3
#         ]

#         row = []

#         for local_index, item in enumerate(
#             row_values
#         ):
#             label, value = item

#             theme_index = (
#                 row_start
#                 + local_index
#             )

#             theme = card_themes[
#                 theme_index
#                 % len(card_themes)
#             ]

#             card = Table(
#                 [
#                     [
#                         Paragraph(
#                             label,
#                             styles["kpi_label"],
#                         )
#                     ],
#                     [
#                         Paragraph(
#                             value,
#                             styles["kpi_value"],
#                         )
#                     ],
#                 ],
#                 colWidths=[
#                     card_width,
#                 ],
#                 rowHeights=[
#                     11 * mm,
#                     16 * mm,
#                 ],
#             )

#             card.setStyle(
#                 TableStyle(
#                     [
#                         # Основной фон карточки
#                         (
#                             "BACKGROUND",
#                             (0, 0),
#                             (-1, -1),
#                             theme["background"],
#                         ),

#                         # Общая рамка
#                         (
#                             "BOX",
#                             (0, 0),
#                             (-1, -1),
#                             0.6,
#                             BORDER,
#                         ),

#                         # Цветная верхняя линия
#                         (
#                             "LINEABOVE",
#                             (0, 0),
#                             (-1, 0),
#                             2.4,
#                             theme["accent"],
#                         ),

#                         # Выравнивание
#                         (
#                             "ALIGN",
#                             (0, 0),
#                             (-1, -1),
#                             "CENTER",
#                         ),
#                         (
#                             "VALIGN",
#                             (0, 0),
#                             (-1, -1),
#                             "MIDDLE",
#                         ),

#                         # Отступы внутри карточки
#                         (
#                             "LEFTPADDING",
#                             (0, 0),
#                             (-1, -1),
#                             6,
#                         ),
#                         (
#                             "RIGHTPADDING",
#                             (0, 0),
#                             (-1, -1),
#                             6,
#                         ),
#                         (
#                             "TOPPADDING",
#                             (0, 0),
#                             (-1, 0),
#                             7,
#                         ),
#                         (
#                             "BOTTOMPADDING",
#                             (0, 0),
#                             (-1, 0),
#                             3,
#                         ),
#                         (
#                             "TOPPADDING",
#                             (0, 1),
#                             (-1, 1),
#                             3,
#                         ),
#                         (
#                             "BOTTOMPADDING",
#                             (0, 1),
#                             (-1, 1),
#                             7,
#                         ),
#                     ]
#                 )
#             )

#             row.append(card)

#             # Добавляем промежуток только между карточками.
#             if local_index < 2:
#                 row.append("")

#         # Если карточек в последнем ряду меньше трёх,
#         # достраиваем пустые колонки.
#         while len(row) < 5:
#             row.append("")

#         rows.append(row)

#     grid = Table(
#         rows,
#         colWidths=[
#             card_width,
#             gap_width,
#             card_width,
#             gap_width,
#             card_width,
#         ],
#         hAlign="LEFT",
#     )

#     grid.setStyle(
#         TableStyle(
#             [
#                 (
#                     "VALIGN",
#                     (0, 0),
#                     (-1, -1),
#                     "TOP",
#                 ),

#                 # У внешней таблицы не должно быть
#                 # собственных внутренних отступов.
#                 (
#                     "LEFTPADDING",
#                     (0, 0),
#                     (-1, -1),
#                     0,
#                 ),
#                 (
#                     "RIGHTPADDING",
#                     (0, 0),
#                     (-1, -1),
#                     0,
#                 ),
#                 (
#                     "TOPPADDING",
#                     (0, 0),
#                     (-1, -1),
#                     0,
#                 ),
#                 (
#                     "BOTTOMPADDING",
#                     (0, 0),
#                     (-1, -1),
#                     3 * mm,
#                 ),
#             ]
#         )
#     )

#     return grid

# def _method_table(rows, styles):
#     data = [
#         [
#             Paragraph("Параметр", styles["table_header"]),
#             Paragraph("Значение", styles["table_header"]),
#             Paragraph("Пояснение", styles["table_header"]),
#         ]
#     ]

#     for label, value, explanation in rows:
#         data.append(
#             [
#                 Paragraph(label, styles["table_cell"]),
#                 Paragraph(str(value), styles["table_cell"]),
#                 Paragraph(
#                     explanation,
#                     styles["table_cell"],
#                 ),
#             ]
#         )

#     table = Table(
#         data,
#         colWidths=[
#             43 * mm,
#             46 * mm,
#             77 * mm,
#         ],
#         repeatRows=1,
#     )
#     table.setStyle(
#         TableStyle(
#             [
#                 ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
#                 ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
#                 ("INNERGRID", (0, 0), (-1, -1), 0.4, BORDER),
#                 ("VALIGN", (0, 0), (-1, -1), "TOP"),
#                 ("LEFTPADDING", (0, 0), (-1, -1), 5),
#                 ("RIGHTPADDING", (0, 0), (-1, -1), 5),
#                 ("TOPPADDING", (0, 0), (-1, -1), 5),
#                 ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
#             ]
#         )
#     )
#     return table


# def _monthly_table(rows, styles):
#     header = [
#         "Месяц",
#         "План",
#         "Факт",
#         "Прогноз",
#         "Итог",
#         "Отклонение",
#         "Выполнение",
#     ]

#     data = [
#         [
#             Paragraph(value, styles["table_header"])
#             for value in header
#         ]
#     ]

#     for row in rows:
#         data.append(
#             [
#                 Paragraph(
#                     str(value),
#                     (
#                         styles["table_cell"]
#                         if index == 0
#                         else styles["table_cell_right"]
#                     ),
#                 )
#                 for index, value in enumerate(row)
#             ]
#         )

#     table = Table(
#         data,
#         colWidths=[
#             22 * mm,
#             24 * mm,
#             24 * mm,
#             24 * mm,
#             24 * mm,
#             27 * mm,
#             25 * mm,
#         ],
#         repeatRows=1,
#     )
#     table.setStyle(
#         TableStyle(
#             [
#                 ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
#                 ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
#                 ("INNERGRID", (0, 0), (-1, -1), 0.35, BORDER),
#                 ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
#                 ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_BG]),
#                 ("LEFTPADDING", (0, 0), (-1, -1), 4),
#                 ("RIGHTPADDING", (0, 0), (-1, -1), 4),
#                 ("TOPPADDING", (0, 0), (-1, -1), 4),
#                 ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
#             ]
#         )
#     )
#     return table


# def _period_table(rows, styles):
#     data = []

#     for row_index, row in enumerate(rows):
#         data.append(
#             [
#                 Paragraph(
#                     str(value),
#                     (
#                         styles["table_header"]
#                         if row_index == 0
#                         else (
#                             styles["table_cell"]
#                             if column_index == 0
#                             else styles["table_cell_right"]
#                         )
#                     ),
#                 )
#                 for column_index, value in enumerate(row)
#             ]
#         )

#     table = Table(
#         data,
#         colWidths=[
#             68 * mm,
#             49 * mm,
#             49 * mm,
#         ],
#     )
#     table.setStyle(
#         TableStyle(
#             [
#                 ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
#                 ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
#                 ("INNERGRID", (0, 0), (-1, -1), 0.4, BORDER),
#                 ("BACKGROUND", (0, 1), (0, -1), LIGHT_BG),
#                 ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
#                 ("LEFTPADDING", (0, 0), (-1, -1), 6),
#                 ("RIGHTPADDING", (0, 0), (-1, -1), 6),
#                 ("TOPPADDING", (0, 0), (-1, -1), 6),
#                 ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
#             ]
#         )
#     )
#     return table


# def _period_conclusion_text(period):
#     status = conclusion_status(period.execution_pct)
#     direction = conclusion_direction(period.delta)

#     return (
#         f"По итогам периода «{period.label}» ожидаемый объём "
#         f"продаж составляет "
#         f"<b>{format_money_mln(period.expected)} млн ₽</b> "
#         f"при плане "
#         f"<b>{format_money_mln(period.plan)} млн ₽</b>. "
#         f"Ожидаемое выполнение - "
#         f"<b>{format_pct(period.execution_pct)}</b>, "
#         f"отклонение - "
#         f"<b>{format_money_mln(period.delta)} млн ₽</b>. "
#         f"Расчётный результат {status} и {direction}."
#     )


# def _seasonality_label(value) -> str:
#     if value == "multiplicative":
#         return "Мультипликативная"

#     if value == "additive":
#         return "Аддитивная"

#     return str(value or "")




#  gear/app/daily_sales/wb_plan_monitor/prophet_note/builder.py
from __future__ import annotations

from datetime import date
from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    Image,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from .calculations import (
    build_note_context,
    conclusion_direction,
    conclusion_status,
)
from .charts import (
    build_monthly_plan_chart,
    build_period_comparison_chart,
)
from .config import get_note_config
from .formatting import (
    format_date_ru,
    format_date_short,
    format_money,
    format_money_mln,
    format_pct,
    signed_money,
)
from .styles import (
    ACCENT,
    ACCENT_BG,
    BLUE,
    BLUE_BG,
    BORDER,
    DANGER,
    GREEN_BG,
    LIGHT_BG,
    MUTED,
    PLAN,
    PLAN_BG,
    PRIMARY,
    RED_BG,
    SUCCESS,
    WARNING,
    WARNING_BG,
    build_styles,
)


PAGE_WIDTH, PAGE_HEIGHT = A4
LEFT_MARGIN = 18 * mm
RIGHT_MARGIN = 18 * mm
TOP_MARGIN = 17 * mm
BOTTOM_MARGIN = 17 * mm


def build_prophet_note_pdf(
    result: dict[str, Any],
    author_name: str | None = None,
    author_position: str | None = None,
    prepared_at: date | None = None,
) -> bytes:
    """
    Формирует пояснительную записку PDF из результата build_forecast().

    PDF строится из уже рассчитанного result.
    Повторный запуск Prophet не выполняется.
    """
    context = build_note_context(result)
    config = get_note_config()
    prepared_at = prepared_at or date.today()
    author_name = author_name or config.author_name
    author_position = (
        author_position
        if author_position is not None
        else config.author_position
    )

    output = BytesIO()
    styles = build_styles()

    doc = BaseDocTemplate(
        output,
        pagesize=A4,
        leftMargin=LEFT_MARGIN,
        rightMargin=RIGHT_MARGIN,
        topMargin=TOP_MARGIN,
        bottomMargin=BOTTOM_MARGIN,
        title=config.document_title,
        author=author_name,
        subject="Прогноз продаж Wildberries на основе Prophet",
        creator=config.company_name,
    )

    frame = Frame(
        LEFT_MARGIN,
        BOTTOM_MARGIN,
        PAGE_WIDTH - LEFT_MARGIN - RIGHT_MARGIN,
        PAGE_HEIGHT - TOP_MARGIN - BOTTOM_MARGIN,
        id="main_frame",
    )

    doc.addPageTemplates(
        [
            PageTemplate(
                id="main",
                frames=[frame],
                onPage=lambda canvas, current_doc: _draw_page(
                    canvas=canvas,
                    doc=current_doc,
                    company_name=config.company_name,
                    styles=styles,
                ),
            )
        ]
    )

    story = []

    story.extend(
        _build_cover_section(
            context=context,
            styles=styles,
            company_name=config.company_name,
        )
    )

    story.append(PageBreak())

    story.extend(
        _build_methodology_section(
            context=context,
            styles=styles,
        )
    )

    story.append(PageBreak())

    story.extend(
        _build_monthly_section(
            context=context,
            styles=styles,
        )
    )

    story.append(PageBreak())

    story.extend(
        _build_period_section(
            context=context,
            styles=styles,
            author_name=author_name,
            author_position=author_position,
            prepared_at=prepared_at,
        )
    )

    doc.build(story)
    output.seek(0)
    return output.getvalue()


def get_prophet_note_filename(
    result: dict[str, Any],
) -> str:
    params = result.get("params") or {}
    report_date = params.get("date_end")

    if report_date:
        return (
            "wb_prophet_explanatory_note_"
            f"{report_date}.pdf"
        )

    return "wb_prophet_explanatory_note.pdf"



def _draw_page(
    canvas,
    doc,
    company_name: str,
    styles,
):
    canvas.saveState()

    regular = styles["font_regular"]
    bold = styles["font_bold"]

    # Верхняя служебная метка.
    canvas.setFont(bold, 7.2)
    canvas.setFillColor(ACCENT)
    canvas.drawRightString(
        PAGE_WIDTH - RIGHT_MARGIN,
        PAGE_HEIGHT - 9.5 * mm,
        "УПРАВЛЕНЧЕСКИЙ АНАЛИЗ",
    )

    # Нижний колонтитул.
    canvas.setStrokeColor(BORDER)
    canvas.setLineWidth(0.55)
    canvas.line(
        LEFT_MARGIN,
        12 * mm,
        PAGE_WIDTH - RIGHT_MARGIN,
        12 * mm,
    )

    canvas.setFont(regular, 7.2)
    canvas.setFillColor(MUTED)
    canvas.drawString(
        LEFT_MARGIN,
        7.3 * mm,
        f"{company_name} | Прогноз продаж WB на основе Prophet",
    )
    canvas.drawRightString(
        PAGE_WIDTH - RIGHT_MARGIN,
        7.3 * mm,
        f"Страница {doc.page}",
    )

    canvas.restoreState()


def _build_cover_section(
    context,
    styles,
    company_name: str,
):
    params = context["params"]
    year_period = context["year_period"]

    elements = [
        Spacer(1, 4 * mm),
        Paragraph(
            "Пояснительная записка",
            styles["title"],
        ),
        Paragraph(
            (
                "к прогнозу продаж Wildberries "
                f"на {context['year']} год"
            ),
            styles["title"],
        ),
        Paragraph(
            (
                "Прогноз сформирован на основании модели "
                "временных рядов Prophet по дневной "
                "net-выручке: продажи за вычетом возвратов."
            ),
            styles["subtitle"],
        ),
        _info_table(
            rows=[
                (
                    "Дата фактических данных",
                    format_date_short(context["date_end"]),
                ),
                (
                    "Период обучения модели",
                    (
                        f"{format_date_short(context['date_start'])}"
                        " - "
                        f"{format_date_short(context['date_end'])}"
                    ),
                ),
                (
                    "Горизонт прогнозирования",
                    (
                        f"{format_date_short(context['date_end'])}"
                        " - "
                        f"{format_date_short(context['forecast_end'])}"
                    ),
                ),
                (
                    "Сценарная корректировка",
                    format_pct(
                        context["scenario_growth"],
                        2,
                    ),
                ),
            ],
            styles=styles,
        ),
        Spacer(1, 5 * mm),
        _kpi_grid(
            values=[
                (
                    "Факт текущего года",
                    f"{format_money_mln(year_period.fact)} млн ₽",
                ),
                (
                    "Прогноз до конца года",
                    f"{format_money_mln(year_period.forecast)} млн ₽",
                ),
                (
                    "Ожидаемый итог года",
                    f"{format_money_mln(year_period.expected)} млн ₽",
                ),
                (
                    "Годовой план WB",
                    f"{format_money_mln(year_period.plan)} млн ₽",
                ),
                (
                    "Ожидаемое выполнение",
                    format_pct(year_period.execution_pct),
                ),
                (
                    "Недовыполнение плана",
                    format_pct(max(100.0 - year_period.execution_pct, 0.0)),
                ),
            ],
            styles=styles,
        ),
        Spacer(1, 6 * mm),
        Paragraph(
            "Основной вывод",
            styles["heading"],
        ),
        _conclusion_box(
            context=context,
            styles=styles,
        ),
        Spacer(1, 5 * mm),
        Paragraph(
            (
                "Настоящий прогноз является расчётной оценкой "
                "при сохранении выявленной динамики продаж. "
                "Он не является гарантией достижения указанного "
                "результата и должен использоваться совместно "
                "с операционной информацией о доступности товара, "
                "логистике, рекламе и работе складов WB."
            ),
            styles["small"],
        ),
    ]

    return elements


def _build_methodology_section(
    context,
    styles,
):
    params = context["params"]
    training_days = context["training_days"]
    forecast_days = context["forecast_days"]

    rows = [
        (
            "Метод",
            "Prophet, линейный тренд",
            (
                "Модель временных рядов с трендом "
                "и сезонными компонентами."
            ),
        ),
        (
            "Целевой показатель",
            "Дневная net-выручка",
            "Продажи минус возвраты.",
        ),
        (
            "Период обучения",
            (
                f"{format_date_short(context['date_start'])}"
                " - "
                f"{format_date_short(context['date_end'])}"
            ),
            f"{training_days} календарных дней.",
        ),
        (
            "Горизонт прогноза",
            (
                f"{format_date_short(context['date_end'])}"
                " - "
                f"{format_date_short(context['forecast_end'])}"
            ),
            f"{forecast_days} прогнозных дней.",
        ),
        (
            "Гибкость тренда",
            str(params.get("changepoint_prior_scale", "")),
            (
                "Чувствительность модели к изменениям "
                "направления тренда."
            ),
        ),
        (
            "Сила сезонности",
            str(params.get("seasonality_prior_scale", "")),
            "Степень влияния сезонных колебаний.",
        ),
        (
            "Тип сезонности",
            _seasonality_label(
                params.get("seasonality_mode")
            ),
            (
                "Мультипликативная сезонность изменяется "
                "вместе с уровнем продаж."
            ),
        ),
        (
            "Доверительный интервал",
            format_pct(
                float(params.get("interval_width") or 0) * 100,
                0,
            ),
            "Диапазон неопределённости прогноза.",
        ),
        (
            "Сглаживание выбросов",
            (
                "Да"
                if params.get("clip_outliers")
                else "Нет"
            ),
            (
                "Ограничение влияния аномально высоких "
                "или низких дней."
            ),
        ),
        (
            "Сценарная корректировка",
            format_pct(
                float(params.get("growth_pct") or 0),
                2,
            ),
            (
                "Управленческая корректировка применяется "
                "только к будущему прогнозу."
            ),
        ),
    ]

    elements = [
        Paragraph(
            "1. Методология и параметры модели",
            styles["title"],
        ),
        Paragraph(
            (
                "Prophet - модель прогнозирования временных рядов. "
                "Она оценивает общий тренд и повторяющиеся "
                "сезонные закономерности. В расчёте используется "
                "дневная net-выручка, сформированная как продажи "
                "за вычетом возвратов."
            ),
            styles["body"],
        ),
        Paragraph(
            (
                "Минимально допустимый период обучения "
                "в интерфейсе может быть установлен на уровне "
                "30 календарных дней. Для базового прогноза "
                "рекомендуется не менее 60 дней. Полная годовая "
                "сезонность оценивается только при наличии "
                "не менее 365 дней истории."
            ),
            styles["body"],
        ),
        Spacer(1, 3 * mm),
        _method_table(rows, styles),
        Spacer(1, 5 * mm),
        Paragraph(
            "Ограничения интерпретации",
            styles["heading"],
        ),
        Paragraph(
            (
                "Модель анализирует значения временного ряда, "
                "но не устанавливает причинно-следственные связи. "
                "Снижение продаж из-за перебоев в работе складов, "
                "дефицита товара, ограничений логистики или иных "
                "операционных факторов отражается в прогнозе как "
                "изменение динамики, если эти события уже проявились "
                "в фактических данных."
            ),
            styles["body"],
        ),
        Paragraph(
            (
                "При резком изменении внешних условий рекомендуется "
                "сравнивать базовый прогноз за 60 дней с оперативным "
                "сценарием за 30 дней и отдельно фиксировать "
                "управленческую корректировку."
            ),
            styles["body"],
        ),
    ]

    return elements


def _build_monthly_section(
    context,
    styles,
):
    chart = build_monthly_plan_chart(
        context["monthly"]
    )

    table_rows = []
    for row in context["monthly"]:
        table_rows.append(
            [
                str(row.get("month") or ""),
                format_money_mln(row.get("plan") or 0),
                format_money_mln(row.get("fact") or 0),
                format_money_mln(row.get("forecast") or 0),
                format_money_mln(
                    row.get("expected_total") or 0
                ),
                format_money_mln(
                    row.get("delta_to_plan") or 0
                ),
                format_pct(
                    row.get("plan_exec_pct") or 0
                ),
            ]
        )

    return [
        Paragraph(
            "2. Сравнение прогноза с планом WB",
            styles["title"],
        ),
        Paragraph(
            (
                "Для завершённых месяцев ожидаемый итог равен "
                "фактической выручке. Для текущего месяца он "
                "складывается из факта по дату отчёта и прогноза "
                "оставшихся дней. Для будущих месяцев ожидаемый "
                "итог соответствует прогнозу Prophet."
            ),
            styles["body"],
        ),
        Image(
            chart,
            width=172 * mm,
            height=75 * mm,
        ),
        Spacer(1, 4 * mm),
        _monthly_table(
            table_rows,
            styles,
        ),
    ]



def _build_period_section(
    context,
    styles,
    author_name: str,
    author_position: str,
    prepared_at: date,
):
    year_period = context["year_period"]
    half_period = context["half_period"]

    chart = build_period_comparison_chart(
        year_period,
        half_period,
    )

    rows = [
        ["Показатель", year_period.label, half_period.label],
        ["План WB, млн ₽", format_money_mln(year_period.plan), format_money_mln(half_period.plan)],
        ["Факт, млн ₽", format_money_mln(year_period.fact), format_money_mln(half_period.fact)],
        ["Прогнозная часть, млн ₽", format_money_mln(year_period.forecast), format_money_mln(half_period.forecast)],
        ["Ожидаемый итог, млн ₽", format_money_mln(year_period.expected), format_money_mln(half_period.expected)],
        ["Выполнение плана", format_pct(year_period.execution_pct), format_pct(half_period.execution_pct)],
        ["Разница с планом, млн ₽", format_money_mln(year_period.delta), format_money_mln(half_period.delta)],
    ]

    author_text = author_name
    if author_position:
        author_text += f"<br/><font color='#6B7280'>{author_position}</font>"

    return [
        Paragraph("3. Итоги года и текущего полугодия", styles["title"]),
        Paragraph(
            "Сводная оценка показывает ожидаемый результат относительно утверждённого плана WB.",
            styles["subtitle"],
        ),
        Image(chart, width=145 * mm, height=76 * mm),
        Spacer(1, 3 * mm),
        _period_table(rows, styles),
        Spacer(1, 5 * mm),
        Paragraph("Управленческий вывод", styles["heading"]),
        _period_conclusion_box(half_period, styles),
        Spacer(1, 7 * mm),
        Table(
            [
                [
                    Paragraph("<b>Подготовил анализ</b>", styles["body_left"]),
                    Paragraph(author_text, styles["body_left"]),
                ],
                [
                    Paragraph("<b>Дата формирования</b>", styles["body_left"]),
                    Paragraph(format_date_ru(prepared_at), styles["body_left"]),
                ],
            ],
            colWidths=[48 * mm, 118 * mm],
            style=TableStyle(
                [
                    ("LINEABOVE", (0, 0), (-1, 0), 0.7, BORDER),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ]
            ),
        ),
        Spacer(1, 4 * mm),
        Paragraph(
            "Документ сформирован автоматически на основании параметров прогноза, "
            "выбранных пользователем в аналитической панели.",
            styles["small"],
        ),
    ]



def _conclusion_box(context, styles):
    period = context["year_period"]
    execution_pct = float(period.execution_pct or 0)
    shortfall_pct = max(100.0 - execution_pct, 0.0)
    gap_mln = abs(float(period.delta or 0)) / 1_000_000

    if execution_pct >= 100:
        accent = SUCCESS
        status_text = "план выполняется"
        detail = (
            f"Превышение плана составляет "
            f"<b>{format_pct(execution_pct - 100.0)}</b>."
        )
    else:
        accent = DANGER
        status_text = "ожидается недовыполнение плана"
        detail = (
            f"Недовыполнение составляет <b>{format_pct(shortfall_pct)}</b>. "
            f"Ожидаемый результат ниже плана на "
            f"<b>{format_money_mln(gap_mln * 1_000_000)} млн ₽</b>."
        )

    text = (
        f"По состоянию на {format_date_ru(context['date_end'])} ожидаемый объём продаж "
        f"за {context['year']} год составляет "
        f"<b>{format_money_mln(period.expected)} млн ₽</b> при плане "
        f"<b>{format_money_mln(period.plan)} млн ₽</b>. "
        f"План выполнен на <b>{format_pct(execution_pct)}</b>. "
        f"{detail} Итоговая оценка: <b>{status_text}</b>."
    )

    # Тонкая статусная линия 0,8 мм. Без цветной заливки блока.
    table = Table(
        [["", Paragraph(text, styles["body_left"])]],
        colWidths=[0.8 * mm, 165.2 * mm],
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), accent),
                ("BACKGROUND", (1, 0), (1, -1), colors.white),
                ("BOX", (0, 0), (-1, -1), 0.45, BORDER),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (0, -1), 0),
                ("RIGHTPADDING", (0, 0), (0, -1), 0),
                ("LEFTPADDING", (1, 0), (1, -1), 9),
                ("RIGHTPADDING", (1, 0), (1, -1), 9),
                ("TOPPADDING", (1, 0), (1, -1), 8),
                ("BOTTOMPADDING", (1, 0), (1, -1), 8),
            ]
        )
    )
    return table



def _period_conclusion_box(period, styles):
    execution_pct = float(period.execution_pct or 0)
    shortfall_pct = max(100.0 - execution_pct, 0.0)
    gap_mln = abs(float(period.delta or 0)) / 1_000_000

    if execution_pct >= 100:
        accent = SUCCESS
        status_text = "ожидается выполнение или превышение плана"
        detail = (
            f"Превышение плана составляет "
            f"<b>{format_pct(execution_pct - 100.0)}</b>."
        )
    else:
        accent = DANGER
        status_text = "ожидается недовыполнение плана"
        detail = (
            f"Недовыполнение составляет <b>{format_pct(shortfall_pct)}</b>. "
            f"Ожидаемый результат ниже плана на "
            f"<b>{format_money_mln(gap_mln * 1_000_000)} млн ₽</b>."
        )

    text = (
        f"По итогам периода «{period.label}» ожидаемый объём продаж составляет "
        f"<b>{format_money_mln(period.expected)} млн ₽</b> при плане "
        f"<b>{format_money_mln(period.plan)} млн ₽</b>. "
        f"План выполнен на <b>{format_pct(execution_pct)}</b>. "
        f"{detail} На основании расчёта <b>{status_text}</b>."
    )

    content = Table(
        [["", Paragraph(text, styles["body_left"])]],
        colWidths=[0.8 * mm, 165.2 * mm],
    )
    content.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), accent),
                ("BACKGROUND", (1, 0), (1, -1), colors.white),
                ("BOX", (0, 0), (-1, -1), 0.45, BORDER),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (0, -1), 0),
                ("RIGHTPADDING", (0, 0), (0, -1), 0),
                ("LEFTPADDING", (1, 0), (1, -1), 9),
                ("RIGHTPADDING", (1, 0), (1, -1), 9),
                ("TOPPADDING", (1, 0), (1, -1), 8),
                ("BOTTOMPADDING", (1, 0), (1, -1), 8),
            ]
        )
    )
    return content


def _info_table(rows, styles):
    data = [
        [
            Paragraph(label, styles["table_cell"]),
            Paragraph(value, styles["table_cell_right"]),
        ]
        for label, value in rows
    ]

    table = Table(
        data,
        colWidths=[
            78 * mm,
            88 * mm,
        ],
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), LIGHT_BG),
                ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
                ("INNERGRID", (0, 0), (-1, -1), 0.4, BORDER),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return table


def _kpi_grid(values, styles):
    """
    Единый KPI-блок без разноцветных карточек.

    Все карточки имеют одинаковый фон и рамку. Цвет используется только
    для одной тонкой линии над блоком, поэтому показатели воспринимаются
    как единая сводка, а не как набор несвязанных виджетов.
    """
    total_width = 166 * mm
    gap = 3 * mm
    card_width = (total_width - gap * 2) / 3

    rows = []
    for row_start in range(0, len(values), 3):
        row_values = values[row_start:row_start + 3]
        row = []
        for local_index, (label, value) in enumerate(row_values):
            card = Table(
                [
                    [Paragraph(label, styles["kpi_label"])],
                    [Paragraph(value, styles["kpi_value"])],
                ],
                colWidths=[card_width],
                rowHeights=[10 * mm, 15 * mm],
            )
            card.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), LIGHT_BG),
                        ("BOX", (0, 0), (-1, -1), 0.45, BORDER),
                        ("LINEABOVE", (0, 0), (-1, 0), 1.0, ACCENT),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 8),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                        ("TOPPADDING", (0, 0), (-1, 0), 5),
                        ("BOTTOMPADDING", (0, 0), (-1, 0), 2),
                        ("TOPPADDING", (0, 1), (-1, 1), 2),
                        ("BOTTOMPADDING", (0, 1), (-1, 1), 6),
                    ]
                )
            )
            row.append(card)
            if local_index < 2:
                row.append("")
        while len(row) < 5:
            row.append("")
        rows.append(row)

    grid = Table(
        rows,
        colWidths=[card_width, gap, card_width, gap, card_width],
        hAlign="LEFT",
    )
    grid.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3 * mm),
            ]
        )
    )
    return grid

def _method_table(rows, styles):
    data = [
        [
            Paragraph("Параметр", styles["table_header"]),
            Paragraph("Значение", styles["table_header"]),
            Paragraph("Пояснение", styles["table_header"]),
        ]
    ]

    for label, value, explanation in rows:
        data.append(
            [
                Paragraph(label, styles["table_cell"]),
                Paragraph(str(value), styles["table_cell"]),
                Paragraph(
                    explanation,
                    styles["table_cell"],
                ),
            ]
        )

    table = Table(
        data,
        colWidths=[
            43 * mm,
            46 * mm,
            77 * mm,
        ],
        repeatRows=1,
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), BLUE),
                ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
                ("INNERGRID", (0, 0), (-1, -1), 0.4, BORDER),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


def _monthly_table(rows, styles):
    header = [
        "Месяц",
        "План",
        "Факт",
        "Прогноз",
        "Итог",
        "Разница",
        "Выполнение",
    ]

    data = [
        [
            Paragraph(value, styles["table_header"])
            for value in header
        ]
    ]

    for row in rows:
        data.append(
            [
                Paragraph(
                    str(value),
                    (
                        styles["table_cell"]
                        if index == 0
                        else styles["table_cell_right"]
                    ),
                )
                for index, value in enumerate(row)
            ]
        )

    table = Table(
        data,
        colWidths=[
            22 * mm,
            24 * mm,
            24 * mm,
            24 * mm,
            24 * mm,
            27 * mm,
            25 * mm,
        ],
        repeatRows=1,
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), BLUE),
                ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
                ("INNERGRID", (0, 0), (-1, -1), 0.35, BORDER),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_BG]),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table



def _period_table(rows, styles):
    data = []
    for row_index, row in enumerate(rows):
        current = []
        for column_index, value in enumerate(row):
            if row_index == 0:
                style = (
                    styles["table_header_left"]
                    if column_index == 0
                    else styles["table_header"]
                )
            elif column_index == 0:
                style = (
                    styles["table_cell_bold"]
                    if row_index in (4, 5, 6)
                    else styles["table_cell"]
                )
            else:
                style = (
                    styles["table_cell_right_bold"]
                    if row_index in (4, 5, 6)
                    else styles["table_cell_right"]
                )
            current.append(Paragraph(str(value), style))
        data.append(current)

    table = Table(
        data,
        colWidths=[68 * mm, 49 * mm, 49 * mm],
        repeatRows=1,
    )

    commands = [
        ("BACKGROUND", (0, 0), (-1, 0), BLUE),
        ("BOX", (0, 0), (-1, -1), 0.55, BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.35, BORDER),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_BG]),
        ("BACKGROUND", (0, 4), (-1, 4), BLUE_BG),
        ("BACKGROUND", (0, 5), (-1, 5), ACCENT_BG),
        ("LINEABOVE", (0, 6), (-1, 6), 0.8, BORDER),
        ("TEXTCOLOR", (1, 6), (-1, 6), DANGER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]
    table.setStyle(TableStyle(commands))
    return table


def _period_conclusion_text(period):
    status = conclusion_status(period.execution_pct)
    direction = conclusion_direction(period.delta)

    return (
        f"По итогам периода «{period.label}» ожидаемый объём "
        f"продаж составляет "
        f"<b>{format_money_mln(period.expected)} млн ₽</b> "
        f"при плане "
        f"<b>{format_money_mln(period.plan)} млн ₽</b>. "
        f"Ожидаемое выполнение - "
        f"<b>{format_pct(period.execution_pct)}</b>, "
        f"отклонение - "
        f"<b>{format_money_mln(period.delta)} млн ₽</b>. "
        f"Расчётный результат {status} и {direction}."
    )


def _seasonality_label(value) -> str:
    if value == "multiplicative":
        return "Мультипликативная"

    if value == "additive":
        return "Аддитивная"

    return str(value or "")