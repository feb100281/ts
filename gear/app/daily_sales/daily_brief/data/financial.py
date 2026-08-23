# # gear/app/daily_sales/daily_brief/data/financial.py

# from __future__ import annotations

# from datetime import date, timedelta
# from typing import Any

# import pandas as pd

# from gear.app.data.base import DashboardData

# from ..helpers import dataframe_records, number


# # =============================================================================
# # ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# # =============================================================================


# def _value(
#     row: dict,
#     *keys: str,
# ) -> float:
#     """
#     Возвращает первое найденное числовое поле.

#     Несколько вариантов имени нужны потому, что финансовый грид
#     исторически менялся, а страница daily_brief не должна падать
#     из-за переименования одного столбца.
#     """

#     for key in keys:
#         if key in row and row.get(key) is not None:
#             return number(
#                 row.get(key)
#             )

#     return 0.0


# def _date_value(
#     row: dict,
# ):
#     """
#     Ищет дату строки финансового грида.
#     """

#     for key in (
#         "date_from",
#         "date",
#         "report_date",
#     ):
#         value = row.get(key)

#         if value is not None:
#             parsed = pd.to_datetime(
#                 value,
#                 errors="coerce",
#             )

#             if not pd.isna(parsed):
#                 return parsed.date()

#     return None


# def _normalise_finance_row(
#     row: dict,
# ) -> dict:
#     """
#     Приводит строку DashboardData к единому набору показателей
#     для финансовой страницы.

#     Важно:
#     - расходы здесь хранятся положительными величинами;
#     - результат и маржа сохраняют свой исходный знак;
#     - никаких повторных бухгалтерских формул здесь не строим,
#       если показатель уже рассчитан основным sales dashboard.
#     """

#     row = dict(
#         row
#         or {}
#     )

#     revenue_net = _value(
#         row,
#         "amount_vatless",
#         "revenue_vatless",
#     )

#     cogs_man = abs(
#         _value(
#             row,
#             "cogs_man",
#             "man_cogs",
#         )
#     )

#     commission = abs(
#         _value(
#             row,
#             "net_comission",
#             "net_commission",
#             "commission",
#         )
#     )

#     margin_man = _value(
#         row,
#         "margin_man",
#         "man_margin",
#     )

#     wb_costs = abs(
#         _value(
#             row,
#             "wb_costs",
#             "wb_expenses",
#         )
#     )

#     wb_result = _value(
#         row,
#         "wb_result",
#         "financial_result",
#     )

#     margin_pct = (
#         margin_man
#         / revenue_net
#         * 100
#         if revenue_net
#         else 0.0
#     )

#     result_pct = (
#         wb_result
#         / revenue_net
#         * 100
#         if revenue_net
#         else 0.0
#     )

#     cogs_share = (
#         cogs_man
#         / revenue_net
#         * 100
#         if revenue_net
#         else 0.0
#     )

#     commission_share = (
#         commission
#         / revenue_net
#         * 100
#         if revenue_net
#         else 0.0
#     )

#     wb_costs_share = (
#         wb_costs
#         / revenue_net
#         * 100
#         if revenue_net
#         else 0.0
#     )

#     row_date = _date_value(
#         row
#     )

#     return {
#         "date": (
#             row_date.isoformat()
#             if row_date
#             else None
#         ),

#         "revenue_net": revenue_net,
#         "cogs_man": cogs_man,
#         "commission": commission,
#         "margin_man": margin_man,
#         "wb_costs": wb_costs,
#         "wb_result": wb_result,

#         "margin_pct": margin_pct,
#         "result_pct": result_pct,

#         "cogs_share": cogs_share,
#         "commission_share": commission_share,
#         "wb_costs_share": wb_costs_share,
#     }


# def _change_pct(
#     current: float,
#     previous: float,
# ) -> float | None:
#     """
#     Изменение к предыдущему дню.

#     Если базы нет, возвращаем None,
#     а не искусственные 0%.
#     """

#     if not previous:
#         return None

#     return (
#         current
#         / previous
#         - 1
#     ) * 100


# # =============================================================================
# # ОСНОВНАЯ ЗАГРУЗКА
# # =============================================================================


# def get_financial_data(
#     report_date: date,
#     *,
#     history_days: int = 30,
# ) -> dict[str, Any]:
#     """
#     Собирает данные исключительно для страницы
#     «Финансовый результат».

#     Используем тот же источник DashboardData,
#     что и основной daily sales dashboard,
#     чтобы показатели страницы совпадали с операционным отчётом.
#     """

#     history_start = (
#         report_date
#         - timedelta(
#             days=max(
#                 history_days - 1,
#                 1,
#             )
#         )
#     )

#     previous_date = (
#         report_date
#         - timedelta(days=1)
#     )

#     with DashboardData() as dashboard:

#         # -----------------------------------------------------------------
#         # Текущий день
#         # -----------------------------------------------------------------

#         current_frame = (
#             dashboard
#             .get_dayly_sales_grid_data(
#                 start=report_date,
#                 end=report_date,
#             )
#         )

#         # -----------------------------------------------------------------
#         # Предыдущий день
#         # -----------------------------------------------------------------

#         previous_frame = (
#             dashboard
#             .get_dayly_sales_grid_data(
#                 start=previous_date,
#                 end=previous_date,
#             )
#         )

#         # -----------------------------------------------------------------
#         # Последние 30 дней
#         # -----------------------------------------------------------------

#         history_frame = (
#             dashboard
#             .get_dayly_sales_grid_data(
#                 start=history_start,
#                 end=report_date,
#             )
#         )

#     current_source = (
#         dataframe_records(
#             current_frame
#         )
#         or [{}]
#     )[0]

#     previous_source = (
#         dataframe_records(
#             previous_frame
#         )
#         or [{}]
#     )[0]

#     current = _normalise_finance_row(
#         current_source
#     )

#     previous = _normalise_finance_row(
#         previous_source
#     )

#     history_source = dataframe_records(
#         history_frame
#     )

#     history = [
#         _normalise_finance_row(row)
#         for row in history_source
#     ]

#     history = [
#         row
#         for row in history
#         if row.get("date")
#     ]

#     history.sort(
#         key=lambda item: item["date"]
#     )

#     # ---------------------------------------------------------------------
#     # Сравнение результата и маржи с предыдущим днём
#     # ---------------------------------------------------------------------

#     current["result_change_pct"] = (
#         _change_pct(
#             current["wb_result"],
#             previous["wb_result"],
#         )
#     )

#     current["margin_change_pct"] = (
#         _change_pct(
#             current["margin_man"],
#             previous["margin_man"],
#         )
#     )

#     # ---------------------------------------------------------------------
#     # Экономика 100 ₽ выручки
#     #
#     # Здесь специально показываем не абстрактные проценты,
#     # а рубли из каждых 100 ₽ выручки без НДС.
#     # ---------------------------------------------------------------------

#     current["economics_100"] = {
#         "cogs": current["cogs_share"],
#         "commission": current["commission_share"],
#         "wb_costs": current["wb_costs_share"],
#         "result": current["result_pct"],
#     }

#     return {
#         "current": current,
#         "previous": previous,
#         "history": history,
#     }




# # gear/app/daily_sales/daily_brief/data/financial.py

# from __future__ import annotations

# from datetime import date, timedelta
# from typing import Any

# import pandas as pd

# from gear.app.data.base import DashboardData

# from ..helpers import (
#     dataframe_records,
#     number,
# )


# # =============================================================================
# # НАСТРОЙКА ПОЛЕЙ
# # =============================================================================
# #
# # Все возможные варианты названий финансовых показателей собраны здесь.
# #
# # Это сделано специально:
# # если DashboardData позже переименует колонку, не нужно менять
# # financial_page.py, графики и всю остальную логику.
# # =============================================================================


# FIELD_ALIASES = {
#     "date": (
#         "date_from",
#         "date",
#         "report_date",
#     ),

#     # Выручка без НДС
#     "revenue_net": (
#         "amount_vatless",
#         "revenue_vatless",
#         "amount_without_vat",
#         "net_revenue",
#     ),

#     # Управленческая себестоимость
#     "cogs_man": (
#         "cogs_man",
#         "man_cogs",
#         "management_cogs",
#     ),

#     # Комиссия WB
#     "commission": (
#         "net_comission",
#         "net_commission",
#         "commission",
#         "wb_commission",
#     ),

#     # Управленческая маржа ДО прочих расходов WB
#     "margin_man": (
#         "margin_man",
#         "man_margin",
#         "management_margin",
#     ),

#     # Расходы WB:
#     # маркетинг, штрафы и прочие распределяемые расходы
#     "wb_costs": (
#         "wb_costs",
#         "wb_expenses",
#         "marketplace_costs",
#     ),

#     # Конечный финансовый результат
#     "wb_result": (
#         "wb_result",
#         "financial_result",
#         "result_wb",
#     ),
# }


# # =============================================================================
# # БАЗОВЫЕ ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# # =============================================================================


# def _first_value(
#     row: dict,
#     aliases: tuple[str, ...],
# ):
#     """
#     Возвращает первое существующее значение среди aliases.
#     """

#     for key in aliases:
#         if key in row:
#             value = row.get(key)

#             if value is not None:
#                 return value

#     return None


# def _numeric(
#     row: dict,
#     field: str,
# ) -> float:
#     """
#     Безопасно получает числовой показатель.
#     """

#     aliases = FIELD_ALIASES.get(
#         field,
#         (field,),
#     )

#     return number(
#         _first_value(
#             row,
#             aliases,
#         )
#     )


# def _parse_date(
#     row: dict,
# ) -> date | None:
#     """
#     Получает дату строки из одного из допустимых полей.
#     """

#     raw_value = _first_value(
#         row,
#         FIELD_ALIASES["date"],
#     )

#     parsed = pd.to_datetime(
#         raw_value,
#         errors="coerce",
#     )

#     if pd.isna(parsed):
#         return None

#     return parsed.date()


# def _safe_div(
#     numerator: float,
#     denominator: float,
#     multiplier: float = 100,
# ) -> float:
#     """
#     Безопасное деление.
#     """

#     if not denominator:
#         return 0.0

#     return (
#         numerator
#         / denominator
#         * multiplier
#     )


# def _change_pct(
#     current: float,
#     previous: float,
# ) -> float | None:
#     """
#     Процент изменения относительно базы.

#     Для отрицательного финансового результата процентное изменение
#     иногда интерпретируется плохо, поэтому на странице дополнительно
#     показываем изменение рентабельности в процентных пунктах.
#     """

#     if not previous:
#         return None

#     return (
#         current
#         / previous
#         - 1
#     ) * 100


# # =============================================================================
# # НОРМАЛИЗАЦИЯ ДНЕВНОЙ СТРОКИ
# # =============================================================================


# def _normalise_finance_row(
#     source: dict,
# ) -> dict[str, Any]:
#     """
#     Приводит исходную строку финансового грида
#     к единому формату financial-page.

#     Методология:
#     - выручка уже содержит ретроспективные корректировки возвратов;
#     - себестоимость используется управленческая FIFO;
#     - комиссия WB учитывается в базовой марже;
#     - wb_costs — маркетинг, штрафы и другие распределяемые расходы;
#     - wb_result — конечный результат после этих расходов.
#     """

#     source = dict(
#         source
#         or {}
#     )

#     row_date = _parse_date(
#         source
#     )

#     revenue_net = _numeric(
#         source,
#         "revenue_net",
#     )

#     cogs_man = abs(
#         _numeric(
#             source,
#             "cogs_man",
#         )
#     )

#     commission = abs(
#         _numeric(
#             source,
#             "commission",
#         )
#     )

#     margin_man = _numeric(
#         source,
#         "margin_man",
#     )

#     wb_costs = abs(
#         _numeric(
#             source,
#             "wb_costs",
#         )
#     )

#     wb_result = _numeric(
#         source,
#         "wb_result",
#     )

#     return {
#         "date": (
#             row_date.isoformat()
#             if row_date
#             else None
#         ),

#         "revenue_net": revenue_net,

#         "cogs_man": cogs_man,

#         "commission": commission,

#         "margin_man": margin_man,

#         "wb_costs": wb_costs,

#         "wb_result": wb_result,

#         # --------------------------------------------------------------
#         # ДОЛИ ОТ ВЫРУЧКИ БЕЗ НДС
#         # --------------------------------------------------------------

#         "cogs_share": _safe_div(
#             cogs_man,
#             revenue_net,
#         ),

#         "commission_share": _safe_div(
#             commission,
#             revenue_net,
#         ),

#         "margin_pct": _safe_div(
#             margin_man,
#             revenue_net,
#         ),

#         "wb_costs_share": _safe_div(
#             wb_costs,
#             revenue_net,
#         ),

#         "result_pct": _safe_div(
#             wb_result,
#             revenue_net,
#         ),
#     }


# # =============================================================================
# # АГРЕГАЦИЯ ПЕРИОДА
# # =============================================================================


# def _aggregate_rows(
#     rows: list[dict],
#     *,
#     date_from: date | None = None,
#     date_to: date | None = None,
# ) -> dict[str, Any]:
#     """
#     Суммирует финансовые показатели за период.

#     Важно:
#     процентные показатели НЕ суммируются.
#     Они пересчитываются заново от агрегированных сумм.
#     """

#     selected: list[dict] = []

#     for row in rows or []:
#         parsed = pd.to_datetime(
#             row.get("date"),
#             errors="coerce",
#         )

#         if pd.isna(parsed):
#             continue

#         row_date = parsed.date()

#         if (
#             date_from is not None
#             and row_date < date_from
#         ):
#             continue

#         if (
#             date_to is not None
#             and row_date > date_to
#         ):
#             continue

#         selected.append(
#             row
#         )

#     revenue_net = sum(
#         number(
#             row.get("revenue_net")
#         )
#         for row in selected
#     )

#     cogs_man = sum(
#         number(
#             row.get("cogs_man")
#         )
#         for row in selected
#     )

#     commission = sum(
#         number(
#             row.get("commission")
#         )
#         for row in selected
#     )

#     margin_man = sum(
#         number(
#             row.get("margin_man")
#         )
#         for row in selected
#     )

#     wb_costs = sum(
#         number(
#             row.get("wb_costs")
#         )
#         for row in selected
#     )

#     wb_result = sum(
#         number(
#             row.get("wb_result")
#         )
#         for row in selected
#     )

#     return {
#         "date_from": (
#             date_from.isoformat()
#             if date_from
#             else None
#         ),

#         "date_to": (
#             date_to.isoformat()
#             if date_to
#             else None
#         ),

#         "days": len(
#             selected
#         ),

#         "revenue_net": revenue_net,

#         "cogs_man": cogs_man,

#         "commission": commission,

#         "margin_man": margin_man,

#         "wb_costs": wb_costs,

#         "wb_result": wb_result,

#         "cogs_share": _safe_div(
#             cogs_man,
#             revenue_net,
#         ),

#         "commission_share": _safe_div(
#             commission,
#             revenue_net,
#         ),

#         "margin_pct": _safe_div(
#             margin_man,
#             revenue_net,
#         ),

#         "wb_costs_share": _safe_div(
#             wb_costs,
#             revenue_net,
#         ),

#         "result_pct": _safe_div(
#             wb_result,
#             revenue_net,
#         ),
#     }


# # =============================================================================
# # НЕДЕЛЬНЫЕ ГРАНИЦЫ
# # =============================================================================


# def _week_start(
#     value: date,
# ) -> date:
#     """
#     Понедельник недели.
#     """

#     return (
#         value
#         - timedelta(
#             days=value.weekday()
#         )
#     )


# def _week_end(
#     value: date,
# ) -> date:
#     """
#     Воскресенье недели.
#     """

#     return (
#         _week_start(value)
#         + timedelta(days=6)
#     )


# # =============================================================================
# # НЕДЕЛЬНАЯ ИСТОРИЯ
# # =============================================================================


# def _build_week_rows(
#     daily_rows: list[dict],
#     report_date: date,
#     *,
#     weeks: int = 10,
# ) -> list[dict]:
#     """
#     Строит последние N недель.

#     Последняя неделя может быть незавершённой.
#     Поэтому у неё дополнительно есть:
#         is_current
#         is_complete
#     """

#     result: list[dict] = []

#     current_week_start = _week_start(
#         report_date
#     )

#     first_week_start = (
#         current_week_start
#         - timedelta(
#             weeks=max(
#                 weeks - 1,
#                 0,
#             )
#         )
#     )

#     for index in range(
#         weeks
#     ):
#         start = (
#             first_week_start
#             + timedelta(
#                 weeks=index
#             )
#         )

#         natural_end = (
#             start
#             + timedelta(days=6)
#         )

#         effective_end = min(
#             natural_end,
#             report_date,
#         )

#         aggregated = _aggregate_rows(
#             daily_rows,
#             date_from=start,
#             date_to=effective_end,
#         )

#         iso = start.isocalendar()

#         aggregated.update(
#             {
#                 "week": int(
#                     iso.week
#                 ),

#                 "year": int(
#                     iso.year
#                 ),

#                 "label": (
#                     f"W{int(iso.week):02d}"
#                 ),

#                 "is_current": (
#                     start
#                     == current_week_start
#                 ),

#                 "is_complete": (
#                     natural_end
#                     <= report_date
#                 ),

#                 "natural_date_to": (
#                     natural_end.isoformat()
#                 ),
#             }
#         )

#         result.append(
#             aggregated
#         )

#     return result


# # =============================================================================
# # КОММЕНТАРИЙ ПО НЕДЕЛЕ
# # =============================================================================


# def _build_week_comment(
#     current: dict,
#     previous: dict,
# ) -> dict:
#     """
#     Формирует содержательный газетный вывод.

#     Здесь не повторяем цифры с карточек, а пытаемся определить,
#     ЧТО именно изменило качество финансового результата.
#     """

#     current_result_pct = number(
#         current.get("result_pct")
#     )

#     previous_result_pct = number(
#         previous.get("result_pct")
#     )

#     current_margin_pct = number(
#         current.get("margin_pct")
#     )

#     previous_margin_pct = number(
#         previous.get("margin_pct")
#     )

#     current_wb_share = number(
#         current.get("wb_costs_share")
#     )

#     previous_wb_share = number(
#         previous.get("wb_costs_share")
#     )

#     current_revenue = number(
#         current.get("revenue_net")
#     )

#     previous_revenue = number(
#         previous.get("revenue_net")
#     )

#     result_delta_pp = (
#         current_result_pct
#         - previous_result_pct
#     )

#     margin_delta_pp = (
#         current_margin_pct
#         - previous_margin_pct
#     )

#     wb_delta_pp = (
#         current_wb_share
#         - previous_wb_share
#     )

#     revenue_change = _change_pct(
#         current_revenue,
#         previous_revenue,
#     )

#     # -----------------------------------------------------------------
#     # ОСНОВНАЯ ОЦЕНКА
#     # -----------------------------------------------------------------

#     if current_result_pct < 0:
#         title = (
#             "Неделя пока формирует отрицательный результат"
#         )

#         lead = (
#             "Расходы и базовая торговая маржа на текущем "
#             "этапе не обеспечивают положительный итог."
#         )

#         tone = "negative"

#     elif (
#         result_delta_pp
#         >= 2
#     ):
#         title = (
#             "Качество результата улучшилось"
#         )

#         lead = (
#             "Доля финансового результата в выручке "
#             "выше предыдущей недели."
#         )

#         tone = "positive"

#     elif (
#         result_delta_pp
#         <= -2
#     ):
#         title = (
#             "Рентабельность недели снизилась"
#         )

#         lead = (
#             "Финансовый результат остаётся положительным, "
#             "но компания сохраняет меньшую долю выручки."
#         )

#         tone = "warning"

#     else:
#         title = (
#             "Результат недели остаётся устойчивым"
#         )

#         lead = (
#             "Существенного изменения итоговой "
#             "рентабельности относительно предыдущей "
#             "недели пока нет."
#         )

#         tone = "neutral"

#     # -----------------------------------------------------------------
#     # ПРИЧИНА
#     # -----------------------------------------------------------------

#     reasons: list[str] = []

#     if margin_delta_pp <= -1:
#         reasons.append(
#             "базовая маржа до прочих расходов WB снизилась"
#         )

#     elif margin_delta_pp >= 1:
#         reasons.append(
#             "базовая маржа до прочих расходов WB выросла"
#         )

#     if wb_delta_pp >= 1:
#         reasons.append(
#             "доля распределяемых расходов WB увеличилась"
#         )

#     elif wb_delta_pp <= -1:
#         reasons.append(
#             "доля распределяемых расходов WB снизилась"
#         )

#     if (
#         revenue_change is not None
#         and revenue_change >= 10
#     ):
#         reasons.append(
#             "выручка заметно выше предыдущей недели"
#         )

#     elif (
#         revenue_change is not None
#         and revenue_change <= -10
#     ):
#         reasons.append(
#             "выручка заметно ниже предыдущей недели"
#         )

#     if reasons:
#         reason_text = (
#             " На изменение повлияли: "
#             + "; ".join(reasons)
#             + "."
#         )

#     else:
#         reason_text = (
#             " Структура выручки, маржи и расходов "
#             "пока близка к предыдущей неделе."
#         )

#     return {
#         "title": title,
#         "lead": lead + reason_text,
#         "tone": tone,

#         "result_delta_pp": (
#             result_delta_pp
#         ),

#         "margin_delta_pp": (
#             margin_delta_pp
#         ),

#         "wb_costs_delta_pp": (
#             wb_delta_pp
#         ),

#         "revenue_change_pct": (
#             revenue_change
#         ),
#     }


# # =============================================================================
# # ОСНОВНАЯ ФУНКЦИЯ
# # =============================================================================


# def get_financial_data(
#     report_date: date,
#     *,
#     history_days: int = 90,
#     weeks: int = 10,
# ) -> dict[str, Any]:
#     """
#     Собирает данные финансового разворота.

#     Почему берём 90 дней:
#     - для графика показываем последние 30 дней;
#     - для недельной аналитики нужно до 10 недель;
#     - один запрос дешевле серии отдельных запросов.
#     """

#     history_start = (
#         report_date
#         - timedelta(
#             days=max(
#                 history_days - 1,
#                 1,
#             )
#         )
#     )

#     with DashboardData() as dashboard:
#         finance_frame = (
#             dashboard
#             .get_dayly_sales_grid_data(
#                 start=history_start,
#                 end=report_date,
#             )
#         )

#     source_rows = dataframe_records(
#         finance_frame
#     )

#     daily_rows = [
#         _normalise_finance_row(
#             row
#         )
#         for row in source_rows
#     ]

#     daily_rows = [
#         row
#         for row in daily_rows
#         if row.get("date")
#     ]

#     daily_rows.sort(
#         key=lambda row: row["date"]
#     )

#     # =================================================================
#     # ТЕКУЩИЙ ДЕНЬ
#     # =================================================================

#     current_day_rows = [
#         row
#         for row in daily_rows
#         if row["date"]
#         == report_date.isoformat()
#     ]

#     current_day = (
#         current_day_rows[-1]
#         if current_day_rows
#         else _aggregate_rows(
#             [],
#             date_from=report_date,
#             date_to=report_date,
#         )
#     )

#     # =================================================================
#     # ПРЕДЫДУЩИЙ ДЕНЬ
#     # =================================================================

#     previous_date = (
#         report_date
#         - timedelta(days=1)
#     )

#     previous_day_rows = [
#         row
#         for row in daily_rows
#         if row["date"]
#         == previous_date.isoformat()
#     ]

#     previous_day = (
#         previous_day_rows[-1]
#         if previous_day_rows
#         else {}
#     )

#     current_day[
#         "result_change_pct"
#     ] = _change_pct(
#         number(
#             current_day.get(
#                 "wb_result"
#             )
#         ),
#         number(
#             previous_day.get(
#                 "wb_result"
#             )
#         ),
#     )

#     current_day[
#         "margin_change_pct"
#     ] = _change_pct(
#         number(
#             current_day.get(
#                 "margin_man"
#             )
#         ),
#         number(
#             previous_day.get(
#                 "margin_man"
#             )
#         ),
#     )

#     current_day[
#         "economics_100"
#     ] = {
#         "cogs": number(
#             current_day.get(
#                 "cogs_share"
#             )
#         ),

#         "commission": number(
#             current_day.get(
#                 "commission_share"
#             )
#         ),

#         "wb_costs": number(
#             current_day.get(
#                 "wb_costs_share"
#             )
#         ),

#         "result": number(
#             current_day.get(
#                 "result_pct"
#             )
#         ),
#     }

#     # =================================================================
#     # НЕДЕЛИ
#     # =================================================================

#     week_rows = _build_week_rows(
#         daily_rows,
#         report_date,
#         weeks=weeks,
#     )

#     current_week = (
#         week_rows[-1]
#         if week_rows
#         else {}
#     )

#     previous_week = (
#         week_rows[-2]
#         if len(week_rows) >= 2
#         else {}
#     )

#     current_week[
#         "result_delta_pp"
#     ] = (
#         number(
#             current_week.get(
#                 "result_pct"
#             )
#         )
#         - number(
#             previous_week.get(
#                 "result_pct"
#             )
#         )
#     )

#     current_week[
#         "margin_delta_pp"
#     ] = (
#         number(
#             current_week.get(
#                 "margin_pct"
#             )
#         )
#         - number(
#             previous_week.get(
#                 "margin_pct"
#             )
#         )
#     )

#     current_week[
#         "wb_costs_delta_pp"
#     ] = (
#         number(
#             current_week.get(
#                 "wb_costs_share"
#             )
#         )
#         - number(
#             previous_week.get(
#                 "wb_costs_share"
#             )
#         )
#     )

#     week_comment = _build_week_comment(
#         current_week,
#         previous_week,
#     )

#     return {
#         "current": current_day,

#         "previous": previous_day,

#         # На графике показываем только последние 30 дней.
#         "history_30d": (
#             daily_rows[-30:]
#         ),

#         # Весь загруженный диапазон оставляем для диагностики.
#         "history": daily_rows,

#         "weeks": week_rows,

#         "current_week": current_week,

#         "previous_week": previous_week,

#         "week_comment": week_comment,
#     }



# gear/app/daily_sales/daily_brief/data/financial.py

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import pandas as pd

from gear.app.data.base import DashboardData

from ..helpers import (
    dataframe_records,
    number,
)


# =============================================================================
# НАСТРОЙКА ПОЛЕЙ
# =============================================================================
#
# Финансовая страница работает поверх get_dayly_sales_grid_data().
#
# Все названия полей собраны здесь, чтобы presentation-слой
# не зависел от внутреннего устройства DashboardData.
# =============================================================================


FIELD_ALIASES = {
    "date": (
        "date_from",
        "date",
        "report_date",
    ),

    # Выручка без НДС
    "revenue_net": (
        "amount_vatless",
        "revenue_vatless",
        "amount_without_vat",
        "net_revenue",
    ),

    # Управленческая FIFO-себестоимость
    "cogs_man": (
        "cogs_man",
        "man_cogs",
        "management_cogs",
    ),

    # Комиссия WB.
    #
    # В DAILY_SALES_AGG net_comission обычно отрицательная,
    # поскольку она уменьшает финансовый результат.
    "commission": (
        "net_comission",
        "net_commission",
        "commission",
        "wb_commission",
    ),

    # Управленческая маржа:
    #
    # amount_vatless
    # - cogs_man
    # + net_comission
    #
    # То есть это маржа ДО распределяемых расходов WB.
    "margin_man": (
        "margin_man",
        "man_margin",
        "management_margin",
    ),

    # Распределяемые расходы WB:
    # логистика, хранение, штрафы, удержания и т.д.
    "wb_costs": (
        "wb_costs",
        "wb_expenses",
        "marketplace_costs",
    ),

    # Финансовый результат:
    #
    # margin_man - wb_costs
    "wb_result": (
        "wb_result",
        "financial_result",
        "result_wb",
    ),
}


# =============================================================================
# БАЗОВЫЕ ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# =============================================================================


def _is_missing(
    value,
) -> bool:
    """
    Проверяет именно отсутствие значения.

    Важно отличать:
        None / NaN
    от
        реального 0.
    """

    if value is None:
        return True

    try:
        return bool(
            pd.isna(value)
        )
    except (
        TypeError,
        ValueError,
    ):
        return False


def _first_value(
    row: dict,
    aliases: tuple[str, ...],
):
    """
    Возвращает первое существующее и непустое
    значение среди возможных названий поля.
    """

    for key in aliases:

        if key not in row:
            continue

        value = row.get(
            key
        )

        if not _is_missing(
            value
        ):
            return value

    return None


def _raw_value(
    row: dict,
    field: str,
):
    """
    Получает исходное значение без преобразования NULL -> 0.

    Это особенно важно для wb_costs / wb_result:
    отсутствие недельных расходов WB в SQL даёт NULL,
    но это не означает нулевую торговую маржу.
    """

    aliases = FIELD_ALIASES.get(
        field,
        (field,),
    )

    return _first_value(
        row,
        aliases,
    )


def _numeric(
    row: dict,
    field: str,
) -> float:
    """
    Получает числовое значение.

    Для обычных показателей отсутствие значения
    безопасно трактуется как 0.
    """

    return number(
        _raw_value(
            row,
            field,
        )
    )


def _parse_date(
    row: dict,
) -> date | None:
    """
    Получает дату финансовой строки.
    """

    raw_value = _first_value(
        row,
        FIELD_ALIASES["date"],
    )

    parsed = pd.to_datetime(
        raw_value,
        errors="coerce",
    )

    if pd.isna(
        parsed
    ):
        return None

    return parsed.date()


def _safe_div(
    numerator: float,
    denominator: float,
    multiplier: float = 100,
) -> float:
    """
    Безопасный расчёт доли / процента.
    """

    denominator = number(
        denominator
    )

    if denominator == 0:
        return 0.0

    return (
        number(numerator)
        / denominator
        * multiplier
    )


def _change_pct(
    current: float,
    previous: float,
) -> float | None:
    """
    Изменение относительно предыдущего значения.

    Для сравнения рентабельности на странице дополнительно
    используются процентные пункты — это методологически
    корректнее для result_pct / margin_pct.
    """

    current = number(
        current
    )

    previous = number(
        previous
    )

    if previous == 0:
        return None

    return (
        current
        / previous
        - 1
    ) * 100


# =============================================================================
# КАЛЕНДАРНЫЕ НЕДЕЛИ
# =============================================================================


def _week_start(
    value: date,
) -> date:
    """
    Начало недели — понедельник.
    """

    return (
        value
        - timedelta(
            days=value.weekday()
        )
    )


def _week_end(
    value: date,
) -> date:
    """
    Конец недели — воскресенье.
    """

    return (
        _week_start(
            value
        )
        + timedelta(
            days=6
        )
    )


# =============================================================================
# НОРМАЛИЗАЦИЯ ДНЕВНОЙ ФИНАНСОВОЙ СТРОКИ
# =============================================================================


def _normalise_finance_row(
    source: dict,
) -> dict[str, Any]:
    """
    Приводит строку DAILY_SALES_AGG
    к единому формату финансовой страницы.

    МЕТОДОЛОГИЯ
    -------------------------------------------------------------------------

    1. Продажи и возвраты уже отражены источником
       по исходной дате реализации.

       То есть поздний возврат ретроспективно изменяет
       первоначальную дату продажи.

    2. Себестоимость — управленческая FIFO.

    3. Управленческая маржа:

           amount_vatless
           - cogs_man
           + net_comission

       Это результат ДО распределяемых расходов WB.

    4. Расходы WB распределяются внутри недели.

    5. Особенность текущего DAILY_SALES_AGG:

       если для недели вообще отсутствует строка расходов WB,
       cp.cost_per_sold получается NULL.

       Из-за этого SQL возвращает:

           wb_costs  = NULL
           wb_result = NULL

       При этом margin_man рассчитана совершенно нормально.

       Поскольку queries.py менять нельзя, исправляем это здесь:

           если wb_costs отсутствует:
               известные расходы WB = 0

           если wb_result отсутствует:
               актуальный известный результат = margin_man

       ВАЖНО:
       мы отдельно сохраняем признак отсутствия WB-расходов.
       Поэтому такой результат считается оперативным,
       а не окончательно закрытым.

    6. После появления новых возвратов или расходов WB
       исторические показатели могут пересчитываться.
    """

    source = dict(
        source
        or {}
    )

    row_date = _parse_date(
        source
    )

    # -------------------------------------------------------------------------
    # БАЗОВЫЕ ПОКАЗАТЕЛИ
    # -------------------------------------------------------------------------

    revenue_net = _numeric(
        source,
        "revenue_net",
    )

    cogs_man = abs(
        _numeric(
            source,
            "cogs_man",
        )
    )

    commission_raw = _numeric(
        source,
        "commission",
    )

    # Для визуального анализа расход показываем положительным числом.
    commission = abs(
        commission_raw
    )

    margin_man = _numeric(
        source,
        "margin_man",
    )

    # -------------------------------------------------------------------------
    # WB РАСХОДЫ
    #
    # Здесь нельзя использовать обычный _numeric(),
    # потому что нам необходимо отличить NULL от настоящего 0.
    # -------------------------------------------------------------------------

    wb_costs_raw = _raw_value(
        source,
        "wb_costs",
    )

    wb_result_raw = _raw_value(
        source,
        "wb_result",
    )

    wb_costs_available = (
        wb_costs_raw is not None
    )

    wb_result_available = (
        wb_result_raw is not None
    )

    # -------------------------------------------------------------------------
    # FALLBACK
    #
    # Нет строки расходов WB:
    #
    #     известные расходы = 0
    #     известный result = margin_man
    #
    # Иначе ранние недели ошибочно превращаются в 0 ₽.
    # -------------------------------------------------------------------------

    if wb_costs_available:
        wb_costs = abs(
            number(
                wb_costs_raw
            )
        )
    else:
        wb_costs = 0.0

    if wb_result_available:
        wb_result = number(
            wb_result_raw
        )
    else:
        wb_result = margin_man

    # -------------------------------------------------------------------------
    # ВОЗВРАЩАЕМ НОРМАЛИЗОВАННУЮ СТРОКУ
    # -------------------------------------------------------------------------

    return {
        "date": (
            row_date.isoformat()
            if row_date
            else None
        ),

        "has_data": (
            row_date is not None
        ),

        # -------------------------------------------------------------
        # СУММЫ
        # -------------------------------------------------------------

        "revenue_net": (
            revenue_net
        ),

        "cogs_man": (
            cogs_man
        ),

        "commission": (
            commission
        ),

        # Исходный знак комиссии сохраняем отдельно
        # для диагностики.
        "commission_raw": (
            commission_raw
        ),

        "margin_man": (
            margin_man
        ),

        "wb_costs": (
            wb_costs
        ),

        "wb_result": (
            wb_result
        ),

        # -------------------------------------------------------------
        # КАЧЕСТВО ДАННЫХ WB
        # -------------------------------------------------------------

        "wb_costs_source_available": (
            wb_costs_available
        ),

        "wb_result_source_available": (
            wb_result_available
        ),

        # -------------------------------------------------------------
        # ДОЛИ ОТ ВЫРУЧКИ БЕЗ НДС
        # -------------------------------------------------------------

        "cogs_share": _safe_div(
            cogs_man,
            revenue_net,
        ),

        "commission_share": _safe_div(
            commission,
            revenue_net,
        ),

        "margin_pct": _safe_div(
            margin_man,
            revenue_net,
        ),

        "wb_costs_share": _safe_div(
            wb_costs,
            revenue_net,
        ),

        "result_pct": _safe_div(
            wb_result,
            revenue_net,
        ),
    }


# =============================================================================
# АГРЕГАЦИЯ ПЕРИОДА
# =============================================================================


def _aggregate_rows(
    rows: list[dict],
    *,
    date_from: date | None = None,
    date_to: date | None = None,
) -> dict[str, Any]:
    """
    Агрегирует дневные показатели за период.

    Важно:

    - денежные показатели суммируются;
    - проценты рассчитываются ПОСЛЕ суммирования;
    - отсутствие данных не превращается в 0 ₽;
    - дополнительно считаем покрытие периода расходами WB.
    """

    selected: list[dict] = []

    for row in rows or []:

        parsed = pd.to_datetime(
            row.get(
                "date"
            ),
            errors="coerce",
        )

        if pd.isna(
            parsed
        ):
            continue

        row_date = (
            parsed.date()
        )

        if (
            date_from is not None
            and row_date < date_from
        ):
            continue

        if (
            date_to is not None
            and row_date > date_to
        ):
            continue

        selected.append(
            row
        )

    # =========================================================================
    # ИСТОЧНИК НЕ ВЕРНУЛ НИ ОДНОЙ СТРОКИ
    # =========================================================================

    if not selected:

        return {
            "date_from": (
                date_from.isoformat()
                if date_from
                else None
            ),

            "date_to": (
                date_to.isoformat()
                if date_to
                else None
            ),

            "days": 0,

            "has_data": False,

            "revenue_net": None,
            "cogs_man": None,
            "commission": None,
            "margin_man": None,
            "wb_costs": None,
            "wb_result": None,

            "cogs_share": None,
            "commission_share": None,
            "margin_pct": None,
            "wb_costs_share": None,
            "result_pct": None,

            "wb_costs_days": 0,

            "wb_costs_coverage_pct": 0.0,

            "wb_costs_source_available": False,

            "is_operational": True,
        }

    # =========================================================================
    # СУММЫ
    # =========================================================================

    revenue_net = sum(
        number(
            row.get(
                "revenue_net"
            )
        )
        for row in selected
    )

    cogs_man = sum(
        number(
            row.get(
                "cogs_man"
            )
        )
        for row in selected
    )

    commission = sum(
        number(
            row.get(
                "commission"
            )
        )
        for row in selected
    )

    margin_man = sum(
        number(
            row.get(
                "margin_man"
            )
        )
        for row in selected
    )

    wb_costs = sum(
        number(
            row.get(
                "wb_costs"
            )
        )
        for row in selected
    )

    wb_result = sum(
        number(
            row.get(
                "wb_result"
            )
        )
        for row in selected
    )

    # =========================================================================
    # ПОКРЫТИЕ WB РАСХОДАМИ
    # =========================================================================

    wb_costs_days = sum(
        1
        for row in selected
        if bool(
            row.get(
                "wb_costs_source_available"
            )
        )
    )

    selected_days = len(
        selected
    )

    wb_costs_coverage_pct = (
        wb_costs_days
        / selected_days
        * 100
        if selected_days
        else 0.0
    )

    # Если хотя бы в одном дне источник не отдал wb_costs,
    # период потенциально может ещё измениться.
    all_wb_costs_available = (
        wb_costs_days
        == selected_days
    )

    return {
        "date_from": (
            date_from.isoformat()
            if date_from
            else None
        ),

        "date_to": (
            date_to.isoformat()
            if date_to
            else None
        ),

        "days": (
            selected_days
        ),

        "has_data": True,

        # -------------------------------------------------------------
        # СУММЫ
        # -------------------------------------------------------------

        "revenue_net": (
            revenue_net
        ),

        "cogs_man": (
            cogs_man
        ),

        "commission": (
            commission
        ),

        "margin_man": (
            margin_man
        ),

        "wb_costs": (
            wb_costs
        ),

        "wb_result": (
            wb_result
        ),

        # -------------------------------------------------------------
        # ДОЛИ
        # -------------------------------------------------------------

        "cogs_share": _safe_div(
            cogs_man,
            revenue_net,
        ),

        "commission_share": _safe_div(
            commission,
            revenue_net,
        ),

        "margin_pct": _safe_div(
            margin_man,
            revenue_net,
        ),

        "wb_costs_share": _safe_div(
            wb_costs,
            revenue_net,
        ),

        "result_pct": _safe_div(
            wb_result,
            revenue_net,
        ),

        # -------------------------------------------------------------
        # КАЧЕСТВО ДАННЫХ
        # -------------------------------------------------------------

        "wb_costs_days": (
            wb_costs_days
        ),

        "wb_costs_coverage_pct": (
            wb_costs_coverage_pct
        ),

        "wb_costs_source_available": (
            all_wb_costs_available
        ),

        "is_operational": (
            not all_wb_costs_available
        ),
    }


# =============================================================================
# НЕДЕЛЬНАЯ ИСТОРИЯ
# =============================================================================


def _build_week_rows(
    daily_rows: list[dict],
    report_date: date,
    *,
    weeks: int = 10,
) -> list[dict]:
    """
    Формирует последние N календарных недель.

    Например для 30.07.2026:

        W22  25.05–31.05
        ...
        W30  20.07–26.07
        W31  27.07–30.07

    Текущая неделя обрезается датой отчёта.
    """

    result: list[dict] = []

    current_week_start = _week_start(
        report_date
    )

    first_week_start = (
        current_week_start
        - timedelta(
            weeks=max(
                weeks - 1,
                0,
            )
        )
    )

    for index in range(
        weeks
    ):

        start = (
            first_week_start
            + timedelta(
                weeks=index
            )
        )

        natural_end = (
            start
            + timedelta(
                days=6
            )
        )

        effective_end = min(
            natural_end,
            report_date,
        )

        aggregated = _aggregate_rows(
            daily_rows,
            date_from=start,
            date_to=effective_end,
        )

        iso = (
            start.isocalendar()
        )

        aggregated.update(
            {
                "week": (
                    int(
                        iso.week
                    )
                ),

                "year": (
                    int(
                        iso.year
                    )
                ),

                "label": (
                    f"W{int(iso.week):02d}"
                ),

                "is_current": (
                    start
                    == current_week_start
                ),

                "is_complete": (
                    natural_end
                    <= report_date
                ),

                "natural_date_to": (
                    natural_end.isoformat()
                ),
            }
        )

        # Текущая неделя всегда оперативная,
        # даже если WB-расходы уже присутствуют:
        # новые начисления и возвраты могут прийти позднее.
        if aggregated.get(
            "is_current"
        ):
            aggregated[
                "is_operational"
            ] = True

        result.append(
            aggregated
        )

    return result


# =============================================================================
# АВТОМАТИЧЕСКИЙ КОММЕНТАРИЙ ПО НЕДЕЛЕ
# =============================================================================


def _build_week_comment(
    current: dict,
    previous: dict,
) -> dict:
    """
    Формирует газетный аналитический вывод.

    Комментарий учитывает:
    - изменение рентабельности;
    - изменение базовой маржи;
    - изменение доли WB-расходов;
    - динамику выручки;
    - полноту источника WB-расходов.
    """

    # =========================================================================
    # НЕТ ТЕКУЩЕЙ НЕДЕЛИ
    # =========================================================================

    if not current.get(
        "has_data"
    ):

        return {
            "title": (
                "Нет данных по текущей неделе"
            ),

            "lead": (
                "Источник не вернул финансовые показатели "
                "для текущего периода."
            ),

            "tone": "neutral",

            "result_delta_pp": None,
            "margin_delta_pp": None,
            "wb_costs_delta_pp": None,
            "revenue_change_pct": None,
        }

    current_result_pct = number(
        current.get(
            "result_pct"
        )
    )

    current_margin_pct = number(
        current.get(
            "margin_pct"
        )
    )

    current_wb_share = number(
        current.get(
            "wb_costs_share"
        )
    )

    current_revenue = number(
        current.get(
            "revenue_net"
        )
    )

    # =========================================================================
    # НЕТ БАЗЫ СРАВНЕНИЯ
    # =========================================================================

    if not previous.get(
        "has_data"
    ):

        lead = (
            "Сопоставление с предыдущей неделей недоступно."
        )

        if current.get(
            "is_operational"
        ):
            lead += (
                " Результат является оперативным и может "
                "уточняться после появления новых возвратов "
                "и расходов WB."
            )

        return {
            "title": (
                "Текущая неделя рассчитана"
            ),

            "lead": (
                lead
            ),

            "tone": (
                "positive"
                if current_result_pct >= 0
                else "negative"
            ),

            "result_delta_pp": None,
            "margin_delta_pp": None,
            "wb_costs_delta_pp": None,
            "revenue_change_pct": None,
        }

    previous_result_pct = number(
        previous.get(
            "result_pct"
        )
    )

    previous_margin_pct = number(
        previous.get(
            "margin_pct"
        )
    )

    previous_wb_share = number(
        previous.get(
            "wb_costs_share"
        )
    )

    previous_revenue = number(
        previous.get(
            "revenue_net"
        )
    )

    result_delta_pp = (
        current_result_pct
        - previous_result_pct
    )

    margin_delta_pp = (
        current_margin_pct
        - previous_margin_pct
    )

    wb_delta_pp = (
        current_wb_share
        - previous_wb_share
    )

    revenue_change = _change_pct(
        current_revenue,
        previous_revenue,
    )

    # =========================================================================
    # ГЛАВНЫЙ ВЫВОД
    # =========================================================================

    if current_result_pct < 0:

        title = (
            "Неделя пока формирует отрицательный результат"
        )

        lead = (
            "После управленческой FIFO-себестоимости, "
            "комиссии и известных расходов WB "
            "финансовый результат остаётся отрицательным."
        )

        tone = "negative"

    elif result_delta_pp >= 2:

        title = (
            "Качество финансового результата улучшилось"
        )

        lead = (
            "В текущей неделе в финансовом результате "
            "сохраняется большая доля выручки, "
            "чем неделей ранее."
        )

        tone = "positive"

    elif result_delta_pp <= -2:

        title = (
            "Рентабельность текущей недели снизилась"
        )

        lead = (
            "Финансовый результат остаётся положительным, "
            "но после себестоимости, комиссии и известных "
            "расходов WB сохраняется меньшая доля выручки."
        )

        tone = "warning"

    else:

        title = (
            "Результат недели остаётся устойчивым"
        )

        lead = (
            "Итоговая рентабельность находится "
            "примерно на уровне предыдущей недели."
        )

        tone = "neutral"

    # =========================================================================
    # ФАКТОРЫ
    # =========================================================================

    reasons: list[str] = []

    if margin_delta_pp <= -1:

        reasons.append(
            "базовая маржа до распределяемых "
            "расходов WB снизилась"
        )

    elif margin_delta_pp >= 1:

        reasons.append(
            "базовая маржа до распределяемых "
            "расходов WB выросла"
        )

    if wb_delta_pp >= 1:

        reasons.append(
            "доля известных расходов WB увеличилась"
        )

    elif wb_delta_pp <= -1:

        reasons.append(
            "доля известных расходов WB снизилась"
        )

    if (
        revenue_change is not None
        and revenue_change >= 10
    ):

        reasons.append(
            "выручка заметно выше предыдущей недели"
        )

    elif (
        revenue_change is not None
        and revenue_change <= -10
    ):

        reasons.append(
            "выручка заметно ниже предыдущей недели"
        )

    if reasons:

        lead += (
            " На динамику повлияли: "
            + "; ".join(
                reasons
            )
            + "."
        )

    else:

        lead += (
            " Структура базовой маржи и известных "
            "расходов существенно не изменилась."
        )

    # =========================================================================
    # ПРЕДУПРЕЖДЕНИЕ ОБ ОПЕРАТИВНОСТИ
    # =========================================================================

    if current.get(
        "is_operational"
    ):

        lead += (
            " Результат текущей недели является оперативным: "
            "он может быть пересчитан после появления "
            "новых возвратов и очередных начислений WB."
        )

    if (
        previous.get(
            "has_data"
        )
        and previous.get(
            "is_operational"
        )
    ):

        lead += (
            " Для предыдущей недели источник также содержит "
            "неполное покрытие распределяемыми расходами WB."
        )

    return {
        "title": (
            title
        ),

        "lead": (
            lead
        ),

        "tone": (
            tone
        ),

        "result_delta_pp": (
            result_delta_pp
        ),

        "margin_delta_pp": (
            margin_delta_pp
        ),

        "wb_costs_delta_pp": (
            wb_delta_pp
        ),

        "revenue_change_pct": (
            revenue_change
        ),
    }


# =============================================================================
# ПУСТАЯ СТРОКА ТЕКУЩЕГО ДНЯ
# =============================================================================


def _empty_current_day(
    report_date: date,
) -> dict[str, Any]:
    """
    Формирует безопасную структуру текущего дня,
    если продаж на дату отчёта нет.
    """

    return {
        "date": (
            report_date.isoformat()
        ),

        "has_data": False,

        "revenue_net": 0.0,
        "cogs_man": 0.0,
        "commission": 0.0,
        "commission_raw": 0.0,
        "margin_man": 0.0,
        "wb_costs": 0.0,
        "wb_result": 0.0,

        "wb_costs_source_available": False,
        "wb_result_source_available": False,

        "cogs_share": 0.0,
        "commission_share": 0.0,
        "margin_pct": 0.0,
        "wb_costs_share": 0.0,
        "result_pct": 0.0,

        "is_operational": True,
    }


# =============================================================================
# ОСНОВНАЯ ФУНКЦИЯ
# =============================================================================

def _get_cost_quality(
    dashboard: DashboardData,
    report_date: date,
) -> dict[str, Any]:
    """
    Контроль качества исходной себестоимости.

    Одна строка base = одна товарная единица.

    В знаменателе используем только положительные продажи:
        cr_rev > 0

    Возвраты в denominator не включаем, поскольку задача блока —
    показать долю реализованных единиц, для которых на момент
    формирования отчёта отсутствует исходная себестоимость.

    no_cost:
        t.cr = 0

    no_stocks / no_income:
        используем существующий storage_flag из base.
    """

    week_start = _week_start(
        report_date
    )

    quarter_month = (
        (
            report_date.month - 1
        )
        // 3
        * 3
        + 1
    )

    quarter_start = date(
        report_date.year,
        quarter_month,
        1,
    )

    year_start = date(
        report_date.year,
        1,
        1,
    )

    def get_period(
        date_from: date,
        date_to: date,
    ) -> dict[str, Any]:

        row = (
            dashboard
            .con
            .execute(
                """
                SELECT
                    COUNT(*) FILTER (
                        WHERE t.cr_rev > 0
                    ) AS sales_units,

                    COUNT(*) FILTER (
                        WHERE t.cr_rev > 0
                          AND t.cr = 0
                    ) AS no_cost_units,

                    COUNT(*) FILTER (
                        WHERE t.cr_rev > 0
                          AND t.storage_flag = 'Нет на складе'
                    ) AS no_stocks_units,

                    COUNT(*) FILTER (
                        WHERE t.cr_rev > 0
                          AND t.storage_flag = 'Нет приходов'
                    ) AS no_income_units

                FROM base t

                WHERE
                    t.date_from::DATE
                    BETWEEN ?::DATE AND ?::DATE
                """,
                [
                    date_from,
                    date_to,
                ],
            )
            .fetchone()
        )

        sales_units = int(
            row[0] or 0
        )

        no_cost_units = int(
            row[1] or 0
        )

        no_stocks_units = int(
            row[2] or 0
        )

        no_income_units = int(
            row[3] or 0
        )

        no_cost_pct = (
            no_cost_units
            / sales_units
            * 100
            if sales_units
            else 0.0
        )

        no_stocks_pct = (
            no_stocks_units
            / sales_units
            * 100
            if sales_units
            else 0.0
        )

        no_income_pct = (
            no_income_units
            / sales_units
            * 100
            if sales_units
            else 0.0
        )

        return {
            "date_from": (
                date_from.isoformat()
            ),

            "date_to": (
                date_to.isoformat()
            ),

            "sales_units": (
                sales_units
            ),

            "no_cost_units": (
                no_cost_units
            ),

            "no_cost_pct": (
                no_cost_pct
            ),

            "no_stocks_units": (
                no_stocks_units
            ),

            "no_stocks_pct": (
                no_stocks_pct
            ),

            "no_income_units": (
                no_income_units
            ),

            "no_income_pct": (
                no_income_pct
            ),
        }

    return {
        "day": get_period(
            report_date,
            report_date,
        ),

        "week": get_period(
            week_start,
            report_date,
        ),

        "quarter": get_period(
            quarter_start,
            report_date,
        ),

        "ytd": get_period(
            year_start,
            report_date,
        ),
    }



def get_financial_data(
    report_date: date,
    *,
    history_days: int | None = None,
    weeks: int = 10,
    chart_days: int = 30,
) -> dict[str, Any]:
    """
    Собирает данные для финансового разворота.

    -------------------------------------------------------------------------
    ВАЖНО ПРО history_days
    -------------------------------------------------------------------------

    Параметр оставлен для обратной совместимости.

    Если payload.py сейчас вызывает:

        get_financial_data(
            report_date,
            history_days=90,
            weeks=10,
        )

    ничего менять в payload.py НЕ НУЖНО.

    Но диапазон теперь не зависит только от history_days.

    Мы всегда гарантированно загружаем:

        1. все недели, которые показываем на weekly strip;
        2. весь диапазон 30-дневного графика;
        3. при наличии history_days — не меньший диапазон,
           чем указан старым кодом.

    Поэтому ситуация:

        рисуем 10 недель
        но загрузили только последние 30 дней

    больше невозможна.
    """

    # =========================================================================
    # НОРМАЛИЗАЦИЯ ПАРАМЕТРОВ
    # =========================================================================

    weeks = max(
        int(
            weeks
            or 1
        ),
        1,
    )

    chart_days = max(
        int(
            chart_days
            or 1
        ),
        1,
    )

    # =========================================================================
    # ДИАПАЗОН НЕДЕЛЬ
    # =========================================================================

    current_week_start = _week_start(
        report_date
    )

    first_week_start = (
        current_week_start
        - timedelta(
            weeks=weeks - 1
        )
    )

    # =========================================================================
    # ДИАПАЗОН 30-ДНЕВНОГО ГРАФИКА
    # =========================================================================

    chart_start = (
        report_date
        - timedelta(
            days=chart_days - 1
        )
    )

    required_starts = [
        first_week_start,
        chart_start,
    ]

    # =========================================================================
    # ОБРАТНАЯ СОВМЕСТИМОСТЬ С history_days
    # =========================================================================

    if history_days is not None:

        try:
            safe_history_days = max(
                int(
                    history_days
                ),
                1,
            )

            required_starts.append(
                report_date
                - timedelta(
                    days=safe_history_days - 1
                )
            )

        except (
            TypeError,
            ValueError,
        ):
            pass

    history_start = min(
        required_starts
    )

    # =========================================================================
    # ЗАГРУЗКА
    #
    # get_dayly_sales_grid_data() принимает start / end,
    # поэтому одним запросом получаем всю необходимую историю.
    # =========================================================================

    with DashboardData() as dashboard:

        finance_frame = (
            dashboard
            .get_dayly_sales_grid_data(
                start=history_start,
                end=report_date,
            )
        )

        # ================================================================
        # КОНТРОЛЬ КАЧЕСТВА СЕБЕСТОИМОСТИ
        #
        # Считаем отдельно по продажам:
        # день / текущая неделя / квартал / YTD.
        # ================================================================

        cost_quality = _get_cost_quality(
            dashboard,
            report_date,
        )

    source_rows = dataframe_records(
        finance_frame
    )

    # =========================================================================
    # НОРМАЛИЗАЦИЯ
    # =========================================================================

    daily_rows = [
        _normalise_finance_row(
            row
        )
        for row in source_rows
    ]

    daily_rows = [
        row
        for row in daily_rows
        if row.get(
            "date"
        )
    ]

    daily_rows.sort(
        key=lambda row: row[
            "date"
        ]
    )

    # =========================================================================
    # ТЕКУЩИЙ ДЕНЬ
    # =========================================================================

    current_date_key = (
        report_date.isoformat()
    )

    current_day_rows = [
        row
        for row in daily_rows
        if row.get(
            "date"
        )
        == current_date_key
    ]

    current_day = (
        current_day_rows[-1]
        if current_day_rows
        else _empty_current_day(
            report_date
        )
    )

    # Текущий день всегда считается оперативным:
    # новые возвраты / расходы ещё могут изменить историю.
    current_day[
        "is_operational"
    ] = True

    # =========================================================================
    # ПРЕДЫДУЩИЙ ДЕНЬ
    # =========================================================================

    previous_date = (
        report_date
        - timedelta(
            days=1
        )
    )

    previous_date_key = (
        previous_date.isoformat()
    )

    previous_day_rows = [
        row
        for row in daily_rows
        if row.get(
            "date"
        )
        == previous_date_key
    ]

    previous_day = (
        previous_day_rows[-1]
        if previous_day_rows
        else {}
    )

    # =========================================================================
    # ДНЕВНЫЕ СРАВНЕНИЯ
    # =========================================================================

    current_day[
        "result_change_pct"
    ] = _change_pct(
        current_day.get(
            "wb_result"
        ),
        previous_day.get(
            "wb_result"
        ),
    )

    current_day[
        "margin_change_pct"
    ] = _change_pct(
        current_day.get(
            "margin_man"
        ),
        previous_day.get(
            "margin_man"
        ),
    )

    # =========================================================================
    # UNIT ECONOMICS — 100 ₽
    # =========================================================================

    current_day[
        "economics_100"
    ] = {
        "cogs": number(
            current_day.get(
                "cogs_share"
            )
        ),

        "commission": number(
            current_day.get(
                "commission_share"
            )
        ),

        "wb_costs": number(
            current_day.get(
                "wb_costs_share"
            )
        ),

        "result": number(
            current_day.get(
                "result_pct"
            )
        ),
    }

    # =========================================================================
    # НЕДЕЛЬНАЯ ИСТОРИЯ
    # =========================================================================

    week_rows = _build_week_rows(
        daily_rows,
        report_date,
        weeks=weeks,
    )

    current_week = (
        week_rows[-1]
        if week_rows
        else {}
    )

    previous_week = (
        week_rows[-2]
        if len(
            week_rows
        ) >= 2
        else {}
    )

    # =========================================================================
    # СРАВНЕНИЕ НЕДЕЛЬ
    # =========================================================================

    if (
        current_week.get(
            "has_data"
        )
        and previous_week.get(
            "has_data"
        )
    ):

        current_week[
            "result_delta_pp"
        ] = (
            number(
                current_week.get(
                    "result_pct"
                )
            )
            - number(
                previous_week.get(
                    "result_pct"
                )
            )
        )

        current_week[
            "margin_delta_pp"
        ] = (
            number(
                current_week.get(
                    "margin_pct"
                )
            )
            - number(
                previous_week.get(
                    "margin_pct"
                )
            )
        )

        current_week[
            "wb_costs_delta_pp"
        ] = (
            number(
                current_week.get(
                    "wb_costs_share"
                )
            )
            - number(
                previous_week.get(
                    "wb_costs_share"
                )
            )
        )

    else:

        current_week[
            "result_delta_pp"
        ] = None

        current_week[
            "margin_delta_pp"
        ] = None

        current_week[
            "wb_costs_delta_pp"
        ] = None

    # =========================================================================
    # АВТОМАТИЧЕСКИЙ НЕДЕЛЬНЫЙ ВЫВОД
    # =========================================================================

    week_comment = (
        _build_week_comment(
            current_week,
            previous_week,
        )
    )

    # =========================================================================
    # ПОСЛЕДНИЕ N КАЛЕНДАРНЫХ ДНЕЙ
    #
    # Не используем daily_rows[-30:].
    #
    # В источнике может не быть строки за день без продаж,
    # поэтому "последние 30 строк" не обязательно равны
    # "последним 30 календарным дням".
    # =========================================================================

    chart_date_from = (
        report_date
        - timedelta(
            days=chart_days - 1
        )
    )

    history_30d: list[dict] = []

    for row in daily_rows:

        parsed = pd.to_datetime(
            row.get(
                "date"
            ),
            errors="coerce",
        )

        if pd.isna(
            parsed
        ):
            continue

        row_date = (
            parsed.date()
        )

        if (
            chart_date_from
            <= row_date
            <= report_date
        ):
            history_30d.append(
                row
            )

    # =========================================================================
    # ДОПОЛНИТЕЛЬНАЯ ДИАГНОСТИКА ДИАПАЗОНА
    #
    # Эти значения можно оставить в payload.
    # На страницу они не выводятся, но очень помогают при проверке.
    # =========================================================================

    source_min_date = (
        daily_rows[0].get(
            "date"
        )
        if daily_rows
        else None
    )

    source_max_date = (
        daily_rows[-1].get(
            "date"
        )
        if daily_rows
        else None
    )

    # =========================================================================
    # PAYLOAD
    # =========================================================================

    return {
        # -------------------------------------------------------------
        # Диагностика
        # -------------------------------------------------------------

        "history_start": (
            history_start.isoformat()
        ),

        "history_end": (
            report_date.isoformat()
        ),

        "source_min_date": (
            source_min_date
        ),

        "source_max_date": (
            source_max_date
        ),

        "source_rows": len(
            daily_rows
        ),

        # -------------------------------------------------------------
        # День
        # -------------------------------------------------------------

        "current": (
            current_day
        ),

        "previous": (
            previous_day
        ),

        # -------------------------------------------------------------
        # 30-дневный график
        # -------------------------------------------------------------

        "history_30d": (
            history_30d
        ),

        # -------------------------------------------------------------
        # Полная загруженная история
        # -------------------------------------------------------------

        "history": (
            daily_rows
        ),

        # -------------------------------------------------------------
        # Недели
        # -------------------------------------------------------------

        "weeks": (
            week_rows
        ),

        "current_week": (
            current_week
        ),

        "previous_week": (
            previous_week
        ),

        # -------------------------------------------------------------
        # Газетный вывод
        # -------------------------------------------------------------

        "week_comment": (
            week_comment
        ),
        
        "cost_quality": (
                cost_quality
            ),
    }