# # gear/app/daily_sales/daily_brief/presentation/pages/demand_page.py

# from __future__ import annotations

# import pandas as pd

# from ...helpers import (
#     fmt_money,
#     number,
# )
# from ..components import safe

# from .demand_charts import (
#     brand_price_scenario_chart,
#     demand_price_index_chart,
#     monthly_drivers_chart,
# )


# TITLE = "Коммерческий обзор · спрос"
# SUBTITLE = "Спрос · цена · товарный микс · динамика"


# # =============================================================================
# # FORMATTERS
# # =============================================================================


# def _money_short(
#     value,
# ) -> str:

#     value = number(
#         value
#     )

#     sign = (
#         "−"
#         if value < 0
#         else ""
#     )

#     absolute = abs(
#         value
#     )

#     if absolute >= 1_000_000_000:
#         return (
#             f"{sign}"
#             f"{absolute / 1_000_000_000:.1f}"
#             .replace(".", ",")
#             + "\u00A0млрд\u00A0₽"
#         )

#     if absolute >= 1_000_000:
#         return (
#             f"{sign}"
#             f"{absolute / 1_000_000:.1f}"
#             .replace(".", ",")
#             + "\u00A0млн\u00A0₽"
#         )

#     if absolute >= 1_000:
#         return (
#             f"{sign}"
#             f"{absolute / 1_000:.1f}"
#             .replace(".", ",")
#             + "\u00A0тыс.\u00A0₽"
#         )

#     return fmt_money(
#         value
#     )


# def _number(
#     value,
# ) -> str:

#     return (
#         f"{number(value):,.0f}"
#         .replace(",", " ")
#     )


# def _pct(
#     value,
#     *,
#     signed: bool = False,
# ) -> str:

#     value = number(
#         value
#     )

#     sign = ""

#     if signed:
#         if value > 0:
#             sign = "+"
#         elif value < 0:
#             sign = "−"

#     elif value < 0:
#         sign = "−"

#     return (
#         f"{sign}{abs(value):.1f}%"
#         .replace(".", ",")
#     )


# def _change(
#     current: float,
#     previous: float,
# ) -> float | None:

#     current = number(
#         current
#     )

#     previous = number(
#         previous
#     )

#     if previous == 0:
#         return None

#     return (
#         current
#         / previous
#         - 1
#     ) * 100


# # =============================================================================
# # DATA
# # =============================================================================


# def _daily_frame(
#     payload: dict,
# ) -> pd.DataFrame:

#     rows = (
#         payload
#         .get(
#             "sales",
#             {},
#         )
#         .get(
#             "daily_price_rows",
#             [],
#         )
#     )

#     frame = pd.DataFrame(
#         rows or []
#     )

#     if frame.empty:
#         return frame

#     frame["date_from"] = pd.to_datetime(
#         frame.get(
#             "date_from"
#         ),
#         errors="coerce",
#     )

#     for column in (
#         "sales_qty",
#         "avg_price",
#         "net_amount",
#     ):
#         frame[column] = pd.to_numeric(
#             frame.get(
#                 column
#             ),
#             errors="coerce",
#         )

#     return (
#         frame
#         .dropna(
#             subset=[
#                 "date_from",
#             ]
#         )
#         .sort_values(
#             "date_from"
#         )
#         .reset_index(
#             drop=True
#         )
#     )


# def _period_metrics(
#     frame: pd.DataFrame,
#     start: int,
#     end: int | None = None,
# ) -> dict:

#     if frame.empty:
#         return {
#             "sales_qty": 0,
#             "avg_price": 0,
#             "net_amount": 0,
#             "days": 0,
#         }

#     subset = (
#         frame.iloc[
#             start:end
#         ]
#         .copy()
#     )

#     if subset.empty:
#         return {
#             "sales_qty": 0,
#             "avg_price": 0,
#             "net_amount": 0,
#             "days": 0,
#         }

#     sales_qty = (
#         subset[
#             "sales_qty"
#         ]
#         .fillna(0)
#         .sum()
#     )

#     # Взвешенная средняя цена.
#     #
#     # Среднее арифметическое дневных средних цен здесь было бы неверно.
#     weighted_price_numerator = (
#         subset[
#             "sales_qty"
#         ].fillna(0)
#         * subset[
#             "avg_price"
#         ].fillna(0)
#     ).sum()

#     avg_price = (
#         weighted_price_numerator
#         / sales_qty
#         if sales_qty
#         else 0
#     )

#     net_amount = (
#         subset[
#             "net_amount"
#         ]
#         .fillna(0)
#         .sum()
#     )

#     return {
#         "sales_qty": (
#             number(
#                 sales_qty
#             )
#         ),

#         "avg_price": (
#             number(
#                 avg_price
#             )
#         ),

#         "net_amount": (
#             number(
#                 net_amount
#             )
#         ),

#         "days": len(
#             subset
#         ),
#     }


# def _current_signal(
#     payload: dict,
# ) -> dict:
#     """
#     Последние 14 календарных наблюдений
#     против предыдущих 14 наблюдений.

#     Используем данные daily_price_rows,
#     которые уже построены для 90-дневного анализа.
#     """

#     frame = _daily_frame(
#         payload
#     )

#     if frame.empty:
#         return {}

#     recent_count = min(
#         14,
#         len(frame),
#     )

#     recent = _period_metrics(
#         frame,
#         -recent_count,
#         None,
#     )

#     if len(frame) > recent_count:

#         previous_count = min(
#             14,
#             len(frame)
#             - recent_count,
#         )

#         previous = _period_metrics(
#             frame,
#             -(recent_count + previous_count),
#             -recent_count,
#         )

#     else:
#         previous = {}

#     return {
#         "recent": recent,
#         "previous": previous,

#         "qty_change_pct": _change(
#             recent.get(
#                 "sales_qty"
#             ),
#             previous.get(
#                 "sales_qty"
#             ),
#         ),

#         "price_change_pct": _change(
#             recent.get(
#                 "avg_price"
#             ),
#             previous.get(
#                 "avg_price"
#             ),
#         ),

#         "revenue_change_pct": _change(
#             recent.get(
#                 "net_amount"
#             ),
#             previous.get(
#                 "net_amount"
#             ),
#         ),
#     }


# # =============================================================================
# # HEADER
# # =============================================================================


# def _masthead(
#     payload: dict,
# ) -> str:

#     return f"""
#     <header class="masthead">

#         <div>

#             <div class="brandline">
#                 ТРЕНДСЕТТЕР · АНАЛИТИКА СПРОСА
#             </div>

#             <h1>
#                 {TITLE}
#             </h1>

#             <div class="mast-subtitle">
#                 {SUBTITLE}
#             </div>

#         </div>

#         <div class="issue-meta">
#             Выпуск за
#             <b>{safe(payload.get("report_date"))}</b>
#             <br>
#             Сформирован автоматически
#         </div>

#     </header>
#     """


# # =============================================================================
# # KPI
# # =============================================================================


# def _signal_card(
#     label: str,
#     value: str,
#     note: str,
#     change,
#     *,
#     tone: str = "",
# ) -> str:

#     if change is None:

#         change_html = """
#         <span class="demand-kpi-change neutral">
#             нет базы
#         </span>
#         """

#     else:

#         change = number(
#             change
#         )

#         css = (
#             "up"
#             if change > 0
#             else "down"
#             if change < 0
#             else "neutral"
#         )

#         arrow = (
#             "▲"
#             if change > 0
#             else "▼"
#             if change < 0
#             else "•"
#         )

#         change_html = f"""
#         <span class="demand-kpi-change {css}">
#             {arrow} {_pct(abs(change))}
#         </span>
#         """

#     return f"""
#     <article class="demand-kpi {safe(tone)}">

#         <div class="demand-kpi-label">
#             {safe(label)}
#         </div>

#         <div class="demand-kpi-value">
#             {safe(value)}
#         </div>

#         <div class="demand-kpi-bottom">

#             <span>
#                 {safe(note)}
#             </span>

#             {change_html}

#         </div>

#     </article>
#     """


# def _kpi_row(
#     payload: dict,
#     signal: dict,
# ) -> str:

#     sales = payload.get(
#         "sales",
#         {},
#     )

#     kpi = sales.get(
#         "kpi",
#         {},
#     )

#     recent = signal.get(
#         "recent",
#         {},
#     )

#     return f"""
#     <div class="demand-kpi-grid">

#         {_signal_card(
#             "Спрос · 14 дней",
#             (
#                 _number(
#                     recent.get(
#                         "sales_qty"
#                     )
#                 )
#                 + " ед."
#             ),
#             "положительных продаж",
#             signal.get(
#                 "qty_change_pct"
#             ),
#             tone="demand",
#         )}

#         {_signal_card(
#             "Средняя цена · 14 дней",
#             _money_short(
#                 recent.get(
#                     "avg_price"
#                 )
#             ),
#             "взвешенная по количеству",
#             signal.get(
#                 "price_change_pct"
#             ),
#             tone="price",
#         )}

#         {_signal_card(
#             "Чистая выручка · 14 дней",
#             _money_short(
#                 recent.get(
#                     "net_amount"
#                 )
#             ),
#             "с учётом ретро-корректировок",
#             signal.get(
#                 "revenue_change_pct"
#             ),
#             tone="revenue",
#         )}

#         {_signal_card(
#             "Сегодня · средняя цена",
#             _money_short(
#                 kpi.get(
#                     "avg_price"
#                 )
#             ),
#             (
#                 f"{_number(kpi.get('sales_transactions'))} "
#                 "положительных продаж"
#             ),
#             kpi.get(
#                 "revenue_change_pct"
#             ),
#             tone="today",
#         )}

#     </div>
#     """


# # =============================================================================
# # EDITORIAL ANALYSIS
# # =============================================================================


# def _corr_label(
#     value,
# ) -> str:

#     if value is None:
#         return (
#             "недостаточно данных"
#         )

#     value = number(
#         value
#     )

#     absolute = abs(
#         value
#     )

#     if absolute >= 0.70:
#         strength = "сильная"

#     elif absolute >= 0.45:
#         strength = "заметная"

#     elif absolute >= 0.25:
#         strength = "умеренная"

#     else:
#         strength = "слабая"

#     direction = (
#         "обратная"
#         if value < 0
#         else "прямая"
#     )

#     return (
#         f"{strength} {direction}"
#     )


# def _build_editorial(
#     payload: dict,
#     signal: dict,
# ) -> dict:

#     sales = payload.get(
#         "sales",
#         {},
#     )

#     analysis = sales.get(
#         "price_analysis",
#         {},
#     )

#     qty_change = signal.get(
#         "qty_change_pct"
#     )

#     price_change = signal.get(
#         "price_change_pct"
#     )

#     revenue_change = signal.get(
#         "revenue_change_pct"
#     )

#     qty = number(
#         qty_change
#     )

#     price = number(
#         price_change
#     )

#     revenue = number(
#         revenue_change
#     )

#     # -----------------------------------------------------------------
#     # HEADLINE
#     # -----------------------------------------------------------------

#     if (
#         qty_change is None
#         or price_change is None
#     ):

#         title = (
#             "Недостаточно базы для оценки текущего режима спроса"
#         )

#         lead = (
#             "90-дневная история построена, однако для сопоставления "
#             "последних двух 14-дневных периодов пока недостаточно данных."
#         )

#         tone = "neutral"

#     elif qty > 5 and price < -3:

#         title = (
#             "Спрос ускорился на фоне снижения средней цены"
#         )

#         lead = (
#             "Количество проданных единиц растёт, тогда как средняя "
#             "цена снижается. Текущая динамика выручки в большей степени "
#             "поддерживается физическим спросом."
#         )

#         tone = "positive"

#     elif qty < -5 and price > 3:

#         title = (
#                 "Рост средней цены сопровождается "
#                 "ослаблением физического спроса"
#             )

#         lead = (
#                         "Средняя цена выше предыдущего периода, одновременно "
#                         "количество положительных продаж снизилось. Такая динамика "
#                         "соответствует наблюдаемой обратной связи между средней ценой "
#                         "и количеством продаж."
#                     )

#         tone = "warning"

#     elif qty > 5 and price > 3:

#         title = (
#             "Спрос и средняя цена растут одновременно"
#         )

#         lead = (
#             "Это наиболее сильная комбинация для выручки: компания "
#             "продаёт больше единиц при более высокой средней цене."
#         )

#         tone = "positive"

#     elif qty < -5 and price < -3:

#         title = (
#             "Одновременно снижаются спрос и средняя цена"
#         )

#         lead = (
#             "Снижение затронуло оба основных драйвера выручки. "
#             "Такой режим требует проверки товарного микса, наличия "
#             "и активности промо."
#         )

#         tone = "negative"

#     elif abs(qty) <= 5 and price > 3:

#         title = (
#             "Выручку сейчас больше поддерживает цена, чем объём"
#         )

#         lead = (
#             "Количество проданных единиц существенно не изменилось, "
#             "а средняя цена выросла. Динамика носит преимущественно "
#             "ценовой характер."
#         )

#         tone = "neutral"

#     elif abs(price) <= 3 and qty > 5:

#         title = (
#             "Рост обеспечен прежде всего физическим спросом"
#         )

#         lead = (
#             "Средняя цена остаётся относительно стабильной, "
#             "а количество продаж выросло. Это более чистый сигнал "
#             "увеличения спроса."
#         )

#         tone = "positive"

#     else:

#         title = (
#             "Режим спроса остаётся относительно стабильным"
#         )

#         lead = (
#             "За последние две недели нет резкого совместного изменения "
#             "количества продаж и средней цены."
#         )

#         tone = "neutral"

#     # -----------------------------------------------------------------
#     # REVENUE
#     # -----------------------------------------------------------------

#     if revenue_change is not None:

#         if revenue >= 5:
#             lead += (
#                 f" Чистая выручка за последние 14 дней выросла "
#                 f"на {_pct(revenue)} к предыдущему сопоставимому периоду."
#             )

#         elif revenue <= -5:
#             lead += (
#                 f" Чистая выручка за последние 14 дней снизилась "
#                 f"на {_pct(abs(revenue))}."
#             )

#         else:
#             lead += (
#                 " Чистая выручка при этом остаётся близкой "
#                 "к предыдущему 14-дневному периоду."
#             )

#     daily_corr = analysis.get(
#         "daily_corr"
#     )

#     monthly_corr = analysis.get(
#         "monthly_corr"
#     )

#     return {
#         "title": title,
#         "lead": lead,
#         "tone": tone,

#         "daily_corr": daily_corr,
#         "monthly_corr": monthly_corr,

#         "daily_corr_label": (
#             _corr_label(
#                 daily_corr
#             )
#         ),

#         "monthly_corr_label": (
#             _corr_label(
#                 monthly_corr
#             )
#         ),
#     }


# def _editorial_block(
#     editorial: dict,
# ) -> str:

#     return f"""
#     <section class="demand-editorial {safe(editorial.get('tone'))}">

#         <div class="demand-editorial-label">
#             ГЛАВНЫЙ СИГНАЛ
#         </div>

#         <div class="demand-editorial-title">
#             {safe(editorial.get("title"))}
#         </div>

#         <div class="demand-editorial-copy">
#             {safe(editorial.get("lead"))}
#         </div>

#         <div class="demand-corr-strip">

#             <div>
#                 <span>
#                     90 дней
#                 </span>

#                 <b>
#                     {
#                         "—"
#                         if editorial.get("daily_corr") is None
#                         else _pct(
#                             number(
#                                 editorial.get(
#                                     "daily_corr"
#                                 )
#                             )
#                             * 100
#                         )
#                     }
#                 </b>

#                 <small>
#                     {safe(editorial.get("daily_corr_label"))}
#                     связь цены и количества
#                 </small>
#             </div>

#             <div>
#                 <span>
#                     12 месяцев
#                 </span>

#                 <b>
#                     {
#                         "—"
#                         if editorial.get("monthly_corr") is None
#                         else _pct(
#                             number(
#                                 editorial.get(
#                                     "monthly_corr"
#                                 )
#                             )
#                             * 100
#                         )
#                     }
#                 </b>

#                 <small>
#                     {safe(editorial.get("monthly_corr_label"))}
#                     связь цены и количества
#                 </small>
#             </div>

#         </div>

#     </section>
#     """


# # =============================================================================
# # 90 DAY BLOCK
# # =============================================================================


# def _regime_block(
#     payload: dict,
# ) -> str:

#     rows = (
#         payload
#         .get(
#             "sales",
#             {},
#         )
#         .get(
#             "daily_price_rows",
#             [],
#         )
#     )

#     chart = demand_price_index_chart(
#         rows
#     )

#     if not chart:

#         chart = """
#         <div class="demand-empty">
#             Недостаточно данных для 90-дневной динамики.
#         </div>
#         """

#     return f"""
#     <section class="demand-regime-card">

#         <div class="demand-block-head">

#             <div>

#                 <div class="demand-kicker">
#                     РЕЖИМ СПРОСА
#                 </div>

#                 <div class="demand-block-title">
#                     Что меняется быстрее — цена или количество
#                 </div>

#                 <div class="demand-block-subtitle">
#                     7-дневные средние · индекс начала ряда = 100
#                 </div>

#             </div>

#             <div class="demand-chart-caption">
#                 последние 90 дней
#             </div>

#         </div>

#         <div class="demand-regime-chart">
#             {chart}
#         </div>

#         <div class="demand-chart-note">
#             Индекс показывает относительное изменение показателей.
#             Если линия спроса растёт при снижении цены, увеличение
#             продаж может быть связано с более доступным ценовым уровнем
#             или изменением товарного микса. Это аналитический сигнал,
#             а не оценка причинности.
#         </div>

#     </section>
#     """


# # =============================================================================
# # MONTHLY BLOCK
# # =============================================================================


# def _monthly_block(
#     payload: dict,
# ) -> str:

#     rows = (
#         payload
#         .get(
#             "sales",
#             {},
#         )
#         .get(
#             "monthly_price_rows",
#             [],
#         )
#     )

#     chart = monthly_drivers_chart(
#         rows
#     )

#     if not chart:

#         chart = """
#         <div class="demand-empty">
#             Недостаточно данных для помесячного анализа.
#         </div>
#         """

#     return f"""
#     <section class="demand-monthly-card">

#         <div class="demand-block-head">

#             <div>

#                 <div class="demand-kicker">
#                     12 МЕСЯЦЕВ
#                 </div>

#                 <div class="demand-block-title small">
#                     Из чего складывалась динамика выручки
#                 </div>

#             </div>

#             <div class="demand-chart-caption">
#                 спрос · цена · чистая выручка
#             </div>

#         </div>

#         <div class="demand-monthly-chart">
#             {chart}
#         </div>

#     </section>
#     """


# def _signed_pct(
#     value,
# ) -> str:

#     value = number(
#         value
#     )

#     if value > 0:
#         sign = "+"

#     elif value < 0:
#         sign = "−"

#     else:
#         sign = ""

#     return (
#         f"{sign}{abs(value):.1f}%"
#         .replace(".", ",")
#     )


# def _signed_pp(
#     value,
# ) -> str:

#     value = number(
#         value
#     )

#     if value > 0:
#         sign = "+"

#     elif value < 0:
#         sign = "−"

#     else:
#         sign = ""

#     return (
#         f"{sign}{abs(value):.1f} п.п."
#         .replace(".", ",")
#     )


# # =============================================================================
# # PRICE BALANCE
# # =============================================================================


# def _price_opportunity_block(
#     payload: dict,
# ) -> str:
#     """
#     Аналитический блок ценового баланса.

#     В отличие от старой матрицы чувствительности,
#     здесь пользователь получает прямой ответ:

#         - какая средняя цена сейчас;
#         - где модельный максимум маржи ₽;
#         - где находится зона баланса спроса и маржи;
#         - какой прирост количества предполагает сценарий;
#         - что происходит с выручкой и маржинальностью.

#     Это модельная оценка, а не автоматическая рекомендация
#     изменить цену.
#     """

#     analysis = (
#         payload
#         .get(
#             "sales",
#             {},
#         )
#         .get(
#             "brand_price_analysis",
#             {},
#         )
#     )

#     brands = list(
#         analysis.get(
#             "brands",
#             [],
#         )
#         or []
#     )

#     opportunities = list(
#         analysis.get(
#             "opportunities",
#             [],
#         )
#         or []
#     )

#     # =================================================================
#     # ВЫБИРАЕМ БРЕНД ДЛЯ ГЛАВНОГО РАЗБОРА
#     # =================================================================

#     #
#     # Приоритет:
#     #
#     # 1. Бренд, где модель действительно видит пространство
#     #    для дополнительного спроса.
#     #
#     # 2. Если таких нет — крупнейший по выручке бренд,
#     #    для которого вообще удалось построить сценарную модель.
#     #

#     # =================================================================
#     # ВЫБИРАЕМ ГЛАВНЫЙ КЕЙС СТРАНИЦЫ
#     #
#     # Приоритет:
#     #
#     # 1. Есть сценарий изменения цены.
#     # 2. Модель имеет среднюю / высокую надёжность.
#     # 3. Из таких брендов выбираем максимальный потенциальный
#     #    прирост количества.
#     # 4. При равном потенциале — более крупный бренд по выручке.
#     #
#     # Поэтому фокусный бренд — не случайный первый элемент,
#     # а наиболее интересный коммерческий кейс.
#     # =================================================================

#     focus_candidates = []

#     for row in brands:

#         balance_data = (
#             row.get(
#                 "balance"
#             )
#             or {}
#         )

#         if not balance_data.get(
#             "available"
#         ):
#             continue

#         confidence = (
#             row.get(
#                 "confidence"
#             )
#             or ""
#         )

#         if confidence not in (
#             "Высокая",
#             "Средняя",
#         ):
#             continue

#         balance = (
#             balance_data.get(
#                 "balance"
#             )
#             or {}
#         )

#         price_change = number(
#             balance.get(
#                 "price_change_pct"
#             )
#         )

#         qty_change = number(
#             balance.get(
#                 "qty_change_pct"
#             )
#         )

#         # Не берём кейсы, где модель фактически предлагает
#         # оставить цену без изменений.
#         if abs(
#             price_change
#         ) < 1:
#             continue

#         focus_candidates.append(
#             row
#         )


#     focus_candidates.sort(
#         key=lambda row: (
#             number(
#                 (
#                     row.get(
#                         "balance"
#                     )
#                     or {}
#                 )
#                 .get(
#                     "balance",
#                     {},
#                 )
#                 .get(
#                     "qty_change_pct"
#                 )
#             ),
#             number(
#                 row.get(
#                     "revenue_14d"
#                 )
#             ),
#         ),
#         reverse=True,
#     )


#     if focus_candidates:

#         focus = (
#             focus_candidates[0]
#         )

#     else:

#         available = [
#             row
#             for row in brands
#             if (
#                 row.get(
#                     "balance"
#                 )
#                 or {}
#             ).get(
#                 "available"
#             )
#         ]

#         available.sort(
#             key=lambda row: number(
#                 row.get(
#                     "revenue_14d"
#                 )
#             ),
#             reverse=True,
#         )

#         focus = (
#             available[0]
#             if available
#             else None
#         )

#     # =================================================================
#     # НЕТ НАДЁЖНОЙ МОДЕЛИ
#     # =================================================================

#     if focus is None:

#         return """
#         <section class="demand-price-potential">

#             <div class="demand-price-potential-head">

#                 <div>

#                     <div class="demand-kicker">
#                         ЦЕНОВОЙ ПОТЕНЦИАЛ
#                     </div>

#                     <div class="demand-block-title">
#                         Где находится баланс спроса и маржи
#                     </div>

#                     <div class="demand-block-subtitle">
#                         модельная оценка по брендам · последние 90 дней
#                     </div>

#                 </div>

#             </div>

#             <div class="demand-opportunity-empty">

#                 Для надёжной сценарной оценки пока недостаточно
#                 исторической вариации средней цены по брендам.

#                 <b>
#                     В этом случае ценовой шаг лучше не выводить:
#                     статистическая база недостаточно устойчива.
#                 </b>

#             </div>

#         </section>
#         """

#     # =================================================================
#     # МОДЕЛЬ ФОКУСНОГО БРЕНДА
#     # =================================================================

#     balance_data = (
#         focus.get(
#             "balance"
#         )
#         or {}
#     )

#     balance = (
#         balance_data.get(
#             "balance"
#         )
#         or {}
#     )

#     max_margin = (
#         balance_data.get(
#             "max_margin"
#         )
#         or {}
#     )

#     chart = (
#         brand_price_scenario_chart(
#             focus
#         )
#     )

#     if not chart:

#         chart = """
#         <div class="demand-empty">
#             Не удалось построить сценарную кривую.
#         </div>
#         """

#     # =================================================================
#     # ОСНОВНОЙ СЦЕНАРИЙ
#     # =================================================================

#     price_change = number(
#         balance.get(
#             "price_change_pct"
#         )
#     )

#     qty_change = number(
#         balance.get(
#             "qty_change_pct"
#         )
#     )

#     revenue_change = number(
#         balance.get(
#             "revenue_change_pct"
#         )
#     )

#     margin_change = number(
#         balance.get(
#             "margin_change_pct"
#         )
#     )

#     margin_delta_pp = number(
#         balance.get(
#             "margin_delta_pp"
#         )
#     )
    
#     # =================================================================
#     # ПОЧЕМУ ИМЕННО ЭТОТ БРЕНД ПОКАЗАН КРУПНО
#     # =================================================================

#     if (
#         price_change < -1
#         and qty_change > 0
#         and margin_change >= -2
#     ):

#         focus_reason = (
#             "Наиболее выраженный потенциал прироста количества "
#             "в допустимой зоне маржи."
#         )

#     elif (
#         price_change > 1
#         and margin_change > 0
#     ):

#         focus_reason = (
#             "Наиболее заметный потенциал роста маржи "
#             "без необходимости стимулировать спрос скидкой."
#         )

#     else:

#         focus_reason = (
#             "Крупнейший бренд с достаточным качеством "
#             "сценарной модели."
#         )

#     current_price = number(
#         balance_data.get(
#             "base_price"
#         )
#     )

#     balance_price = number(
#         balance.get(
#             "projected_price"
#         )
#     )

#     # =================================================================
#     # ТЕКСТ — ЧТО ДЕЛАТЬ
#     # =================================================================

#     if price_change <= -1:

#         action_title = (
#             "Есть пространство для теста более низкой цены"
#         )

#         action_copy = (
#             "Расчётная зона находится ниже текущей средней цены. "
#             "По исторической модели снижение цены может дать "
#             "дополнительный физический спрос, при этом модельная "
#             "маржа в рублях остаётся близкой к своему максимуму."
#         )

#         action_tone = "positive"

#         action_label = (
#             "ТЕСТ НИЖЕ"
#         )

#     elif price_change >= 1:

#         action_title = (
#             "Модель не требует отдавать цену ради объёма"
#         )

#         action_copy = (
#             "Расчётная зона находится выше текущей средней цены. "
#             "Историческая реакция количества не показывает, "
#             "что снижение цены создаёт достаточно дополнительного "
#             "спроса для компенсации потерянной маржи."
#         )

#         action_tone = "positive"

#         action_label = (
#             "ЗАЩИЩАТЬ ЦЕНУ"
#         )

#     else:

#         action_title = (
#             "Текущая цена уже близка к расчётному балансу"
#         )

#         action_copy = (
#             "Модель не показывает значимого экономического преимущества "
#             "от изменения средней цены. Текущий уровень находится "
#             "вблизи зоны эффективного сочетания спроса и маржи."
#         )

#         action_tone = "neutral"

#         action_label = (
#             "СОХРАНИТЬ"
#         )

#     # =================================================================
#     # MAX MARGIN
#     # =================================================================

#     max_margin_price_change = number(
#         max_margin.get(
#             "price_change_pct"
#         )
#     )

#     max_margin_price = number(
#         max_margin.get(
#             "projected_price"
#         )
#     )

#     max_margin_change = number(
#         max_margin.get(
#             "margin_change_pct"
#         )
#     )

#     # =================================================================
#     # ТАБЛИЦА БРЕНДОВ
#     # =================================================================

#     table_candidates = [
#         row
#         for row in brands
#         if (
#             row.get(
#                 "balance"
#             )
#             or {}
#         ).get(
#             "available"
#         )
#     ]

#     table_candidates.sort(
#         key=lambda row: number(
#             row.get(
#                 "revenue_14d"
#             )
#         ),
#         reverse=True,
#     )

#     table_rows = []

#     for row in table_candidates[:7]:

#         row_balance_data = (
#             row.get(
#                 "balance"
#             )
#             or {}
#         )

#         row_balance = (
#             row_balance_data.get(
#                 "balance"
#             )
#             or {}
#         )

#         row_current_price = number(
#             row_balance_data.get(
#                 "base_price"
#             )
#         )

#         row_balance_price = number(
#             row_balance.get(
#                 "projected_price"
#             )
#         )

#         row_price_delta = number(
#             row_balance.get(
#                 "price_change_pct"
#             )
#         )

#         row_qty_delta = number(
#             row_balance.get(
#                 "qty_change_pct"
#             )
#         )

#         row_margin_delta = number(
#             row_balance.get(
#                 "margin_change_pct"
#             )
#         )

#         row_margin_pp = number(
#             row_balance.get(
#                 "margin_delta_pp"
#             )
#         )

#         # -------------------------------------------------------------
#         # УПРАВЛЕНЧЕСКИЙ СИГНАЛ
#         # -------------------------------------------------------------

#         if row_price_delta <= -1:

#             row_action = (
#                 "Тест ниже"
#             )

#             action_class = (
#                 "positive"
#             )

#         elif row_price_delta >= 1:

#             row_action = (
#                 "Защищать цену"
#             )

#             action_class = (
#                 "positive"
#             )

#         else:

#             row_action = (
#                 "Сохранить"
#             )

#             action_class = (
#                 "neutral"
#             )

#         table_rows.append(
#             f"""
#             <div class="demand-balance-table-row">

#                 <div
#                     class="brand"
#                     title="{safe(row.get('brand'))}"
#                 >
#                     {safe(row.get("brand"))}
#                 </div>

#                 <div>
#                     {_money_short(
#                         row_current_price
#                     )}
#                 </div>

#                 <div>
#                     {_money_short(
#                         row_balance_price
#                     )}
#                 </div>

#                 <div class="{action_class}">
#                     {_signed_pct(
#                         row_price_delta
#                     )}
#                 </div>

#                 <div
#                     class="{
#                         'positive'
#                         if row_qty_delta > 0
#                         else 'negative'
#                         if row_qty_delta < 0
#                         else 'neutral'
#                     }"
#                 >
#                     {_signed_pct(
#                         row_qty_delta
#                     )}
#                 </div>

#                 <div
#                     class="{
#                         'positive'
#                         if row_margin_delta > 0
#                         else 'negative'
#                         if row_margin_delta < 0
#                         else 'neutral'
#                     }"
#                 >
#                     {_signed_pct(
#                         row_margin_delta
#                     )}
#                 </div>

#                 <div
#                     class="{
#                         'positive'
#                         if row_margin_pp > 0
#                         else 'negative'
#                         if row_margin_pp < 0
#                         else 'neutral'
#                     }"
#                 >
#                     {_signed_pp(
#                         row_margin_pp
#                     )}
#                 </div>

#                 <div class="{action_class}">
#                     {safe(row_action)}
#                 </div>

#             </div>
#             """
#         )

#     if table_rows:

#         table_html = "".join(
#             table_rows
#         )

#     else:

#         table_html = """
#         <div class="demand-opportunity-empty">
#             Нет других брендов с достаточным качеством модели.
#         </div>
#         """

#     # =================================================================
#     # RESULT
#     # =================================================================

#     return f"""
#     <section class="demand-price-potential">

#         <div class="demand-price-potential-head">

#             <div>

#                 <div class="demand-kicker">
#                     ЦЕНОВОЙ ПОТЕНЦИАЛ
#                 </div>

#                 <div class="demand-block-title">
#                     Где находится баланс спроса и маржи
#                 </div>

#                 <div class="demand-block-subtitle">
#                     сценарная модель по брендам · последние 90 дней
#                 </div>

#             </div>

#             <div class="demand-price-rule">

#                 <b>
#                     Как определяется баланс
#                 </b>

#                 Сначала модель ищет цену максимальной маржи ₽.
#                 Затем — максимальный спрос в зоне,
#                 где сохраняется не менее 98% этого максимума
#                 и маржинальность не падает более чем на 3 п.п.

#             </div>

#         </div>


#         <!-- =========================================================
#              ФОКУСНЫЙ БРЕНД
#              ========================================================= -->

#                 <div class="demand-balance-focus-label">
#                     ГЛАВНЫЙ ЦЕНОВОЙ КЕЙС
#                 </div>

#                 <div class="demand-balance-brand">
#                     {safe(focus.get("brand"))}
#                 </div>

#                 <div class="demand-balance-focus-reason">
#                     Почему выбран:
#                     <b>
#                         {safe(focus_reason)}
#                     </b>
#                 </div>

#                 <div class="demand-balance-chart-subtitle">
#                     модельная реакция количества и маржи
#                     на изменение средней цены
#                 </div>

#                 {chart}

#             </div>


#             <!-- =====================================================
#                  РАСЧЁТНАЯ ЗОНА
#                  ===================================================== -->

#             <aside class="demand-balance-summary">

#                 <div class="demand-kicker">
#                     РАСЧЁТНАЯ ЗОНА
#                 </div>

#                     <div
#                         class="
#                             demand-balance-summary-title
#                             {safe(action_tone)}
#                         "
#                     >
#                         {safe(action_title)}
#                     </div>

#                     <div class="demand-balance-summary-copy">
#                         {safe(action_copy)}
#                     </div>

#                     <div class="demand-balance-verdict">
#                         <span>
#                             МОДЕЛЬНЫЙ ЦЕНОВОЙ ШАГ
#                         </span>

#                         <b>
#                             {_signed_pct(
#                                 price_change
#                             )}
#                         </b>
#                     </div>


#                 <!-- -------------------------------------------------
#                      ТЕКУЩАЯ ЦЕНА -> БАЛАНС
#                      ------------------------------------------------- -->

#                 <div class="demand-balance-price">

#                     <div>

#                         <span>
#                             Сейчас
#                         </span>

#                         <b>
#                             {_money_short(
#                                 current_price
#                             )}
#                         </b>

#                     </div>

#                     <div class="arrow">
#                         →
#                     </div>

#                     <div>

#                         <span>
#                             Баланс
#                         </span>

#                         <b class="accent">
#                             {_money_short(
#                                 balance_price
#                             )}
#                         </b>

#                     </div>

#                 </div>



#                 <!-- -------------------------------------------------
#                      РЕЗУЛЬТАТ СЦЕНАРИЯ
#                      ------------------------------------------------- -->

#                 <div class="demand-balance-metrics">

#                     <div>

#                         <span>
#                             Количество
#                         </span>

#                         <b class="{
#                             'positive'
#                             if qty_change > 0
#                             else 'negative'
#                         }">
#                             {_signed_pct(
#                                 qty_change
#                             )}
#                         </b>

#                     </div>

#                     <div>

#                         <span>
#                             Выручка
#                         </span>

#                         <b class="{
#                             'positive'
#                             if revenue_change > 0
#                             else 'negative'
#                         }">
#                             {_signed_pct(
#                                 revenue_change
#                             )}
#                         </b>

#                     </div>

#                     <div>

#                         <span>
#                             Маржа ₽
#                         </span>

#                         <b class="{
#                             'positive'
#                             if margin_change > 0
#                             else 'negative'
#                         }">
#                             {_signed_pct(
#                                 margin_change
#                             )}
#                         </b>

#                     </div>

#                     <div>

#                         <span>
#                             Маржинальность
#                         </span>

#                         <b class="{
#                             'positive'
#                             if margin_delta_pp > 0
#                             else 'negative'
#                             if margin_delta_pp < 0
#                             else ''
#                         }">
#                             {_signed_pp(
#                                 margin_delta_pp
#                             )}
#                         </b>

#                     </div>

#                 </div>


#                 <!-- -------------------------------------------------
#                      MAX MARGIN
#                      ------------------------------------------------- -->

#                 <div class="demand-balance-max">
#                     <div class="demand-balance-max-label">
#                         АЛЬТЕРНАТИВА · МАКСИМУМ МАРЖИ ₽
#                     </div>

#                     <div class="demand-balance-max-main">

#                         <b>
#                             {_money_short(
#                                 max_margin_price
#                             )}
#                         </b>

#                         <span>
#                             {_signed_pct(
#                                 max_margin_price_change
#                             )}
#                             к текущей цене
#                         </span>

#                     </div>

#                     <div class="demand-balance-max-note">
#                         модельная маржа ₽
#                         {_signed_pct(
#                             max_margin_change
#                         )}
#                         к текущему уровню
#                     </div>
                    
#                     <div class="demand-balance-max-explain">
#                         Баланс допускает небольшой отказ от абсолютного
#                         максимума маржи ради большего количества продаж.
#                     </div>

#                 </div>


#                 <!-- -------------------------------------------------
#                      КАЧЕСТВО МОДЕЛИ
#                      ------------------------------------------------- -->

#                 <div class="demand-balance-model">

#                     чувствительность

#                     <b>
#                         {
#                             f"{number(focus.get('elasticity')):.2f}"
#                             .replace(".", ",")
#                         }
#                     </b>

#                     · качество

#                     <b>
#                         {safe(
#                             focus.get(
#                                 "confidence"
#                             )
#                         )}
#                     </b>

#                     · наблюдений

#                     <b>
#                         {
#                             int(
#                                 number(
#                                     focus.get(
#                                         "observations"
#                                     )
#                                 )
#                             )
#                         }
#                     </b>

#                 </div>

#                 <div class="demand-balance-action">
#                     {safe(action_label)}
#                 </div>

#             </aside>

#         </div>


#         <!-- =========================================================
#              ВСЕ БРЕНДЫ
#              ========================================================= -->

#         <div class="demand-balance-table">

#             <div class="demand-balance-table-title">
#                 БРЕНДЫ · РАСЧЁТНАЯ ЗОНА
#             </div>

#             <div class="demand-balance-table-row header">

#                 <div>
#                     Бренд
#                 </div>

#                 <div>
#                     Сейчас
#                 </div>

#                 <div>
#                     Баланс
#                 </div>

#                 <div>
#                     Δ цены
#                 </div>

#                 <div>
#                     Δ спроса
#                 </div>

#                 <div>
#                     Δ маржи ₽
#                 </div>

#                 <div>
#                     Δ маржи %
#                 </div>

#                 <div>
#                     Сигнал
#                 </div>

#             </div>

#             {table_html}

#         </div>


#         <!-- =========================================================
#              МЕТОДОЛОГИЧЕСКОЕ ОГРАНИЧЕНИЕ
#              ========================================================= -->

#         <div class="demand-price-disclaimer">

#             Сценарии являются модельной оценкой на основе исторической
#             связи средней цены и количества продаж, а не гарантированным
#             эффектом изменения цены.

#             Средняя цена зависит не только от изменения прайса,
#             но и от товарного микса бренда.

#             Маржа рассчитана после управленческой FIFO-себестоимости
#             и комиссии WB, но без маркетинга, штрафов
#             и прочих распределяемых расходов WB.

#         </div>

#     </section>
#     """
    

# def _brand_anomalies_block(
#     payload: dict,
# ) -> str:

#     anomalies = (
#         payload
#         .get(
#             "sales",
#             {},
#         )
#         .get(
#             "brand_price_analysis",
#             {},
#         )
#         .get(
#             "anomalies",
#             [],
#         )
#     )

#     if not anomalies:

#         return """
#         <section class="demand-anomalies">

#             <div class="demand-kicker">
#                 ЧТО ТРЕБУЕТ ВНИМАНИЯ
#             </div>

#             <div class="demand-anomalies-clear">
#                 Существенных ценовых сигналов
#                 по брендам за последние 14 дней не выявлено.
#             </div>

#         </section>
#         """

#     cards = []

#     for item in anomalies:

#         cards.append(
#             f"""
#             <div
#                 class="
#                     demand-anomaly
#                     {safe(item.get("tone"))}
#                 "
#             >

#                 <div class="demand-anomaly-brand">
#                     {safe(item.get("brand"))}
#                 </div>

#                 <div class="demand-anomaly-title">
#                     {safe(item.get("title"))}
#                 </div>

#                 <div class="demand-anomaly-numbers">

#                     <span>
#                         средняя цена
#                         <b>
#                             {_signed_pct(
#                                 item.get(
#                                     "price_change_pct"
#                                 )
#                             )}
#                         </b>
#                     </span>

#                     <span>
#                         количество
#                         <b>
#                             {_signed_pct(
#                                 item.get(
#                                     "qty_change_pct"
#                                 )
#                             )}
#                         </b>
#                     </span>

#                     <span>
#                         маржа
#                         <b>
#                             {_pct(
#                                 item.get(
#                                     "margin_pct"
#                                 )
#                             )}
#                         </b>
#                     </span>

#                 </div>

#             </div>
#             """
#         )

#     return f"""
#     <section class="demand-anomalies">

#         <div class="demand-anomalies-head">

#             <div>

#                 <div class="demand-kicker">
#                     ЧТО ТРЕБУЕТ ВНИМАНИЯ
#                 </div>

#                 <div class="demand-block-title small">
#                     Ценовые сигналы по брендам
#                 </div>

#             </div>

#             <div class="demand-chart-caption">
#                 последние 14 дней против предыдущих 14
#             </div>

#         </div>

#         <div class="demand-anomalies-grid">
#             {"".join(cards)}
#         </div>

#     </section>
#     """
    
    
# # =============================================================================
# # HOW TO READ
# # =============================================================================


# def _methodology_block() -> str:

#     return """
#     <section class="demand-methodology">

#         <div class="demand-kicker">
#             КАК ЧИТАТЬ СТРАНИЦУ
#         </div>

#         <div class="demand-methodology-grid">

#             <div>
#                 <b>
#                     Спрос измеряется физическими продажами.
#                 </b>

#                 Для анализа количества используются только
#                 положительные продажи. Возвраты не считаются
#                 отрицательным спросом.
#             </div>

#             <div>
#                 <b>
#                     Средняя цена взвешена количеством.
#                 </b>

#                 Поэтому изменение показателя отражает одновременно
#                 цену продажи и изменение товарного микса.
#             </div>

#             <div>
#                 <b>
#                     Чистая выручка пересчитывается ретроспективно.
#                 </b>

#                 Возврат корректирует исходную дату реализации,
#                 поэтому исторические значения страницы могут
#                 изменяться после появления новых возвратов.
#             </div>

#         </div>

#     </section>
#     """


# # =============================================================================
# # PAGE
# # =============================================================================


# def build_demand_page(
#     payload: dict,
# ) -> str:

#     signal = _current_signal(
#         payload
#     )

#     editorial = _build_editorial(
#         payload,
#         signal,
#     )

#     return f"""
#     <!-- =============================================================
#          DEMAND & PRICE PAGE
#          ============================================================= -->

#     <div class="page demand-page">

#         {_masthead(payload)}

#         {_kpi_row(
#             payload,
#             signal,
#         )}

#         <div class="demand-top-grid">

#             {_editorial_block(
#                 editorial
#             )}

#             {_monthly_block(
#                 payload
#             )}

#         </div>

#         {_regime_block(
#             payload
#         )}

#         {_price_opportunity_block(payload)}

#         {_brand_anomalies_block(payload)}

#         {_methodology_block()}

#         <div class="demand-footer-note">

#             <span>
#                 Спрос: количество положительных продаж.
#             </span>

#             <span>
#                 Горизонт анализа:
#                 14 дней · 90 дней · 12 месяцев.
#             </span>

#         </div>

#     </div>
#     """




# gear/app/daily_sales/daily_brief/presentation/pages/demand_page.py

from __future__ import annotations

import pandas as pd

from ...helpers import fmt_money, number
from ..components import safe
from .demand_charts import (
    brand_price_scenario_chart,
    demand_price_index_chart,
    monthly_drivers_chart,
)


TITLE = "Коммерческий обзор · спрос"
SUBTITLE = "Спрос · цена · товарный микс · динамика"


# =============================================================================
# FORMATTERS
# =============================================================================


def _money_short(value) -> str:
    value = number(value)
    sign = "−" if value < 0 else ""
    absolute = abs(value)

    if absolute >= 1_000_000_000:
        return f"{sign}{absolute / 1_000_000_000:.1f}".replace(".", ",") + "\u00A0млрд\u00A0₽"
    if absolute >= 1_000_000:
        return f"{sign}{absolute / 1_000_000:.1f}".replace(".", ",") + "\u00A0млн\u00A0₽"
    if absolute >= 1_000:
        return f"{sign}{absolute / 1_000:.1f}".replace(".", ",") + "\u00A0тыс.\u00A0₽"
    return fmt_money(value)


def _number(value) -> str:
    return f"{number(value):,.0f}".replace(",", " ")


def _pct(value, *, signed: bool = False) -> str:
    value = number(value)
    if signed:
        sign = "+" if value > 0 else "−" if value < 0 else ""
    else:
        sign = "−" if value < 0 else ""
    return f"{sign}{abs(value):.1f}%".replace(".", ",")


def _signed_pct(value) -> str:
    return _pct(value, signed=True)


def _signed_pp(value) -> str:
    value = number(value)
    sign = "+" if value > 0 else "−" if value < 0 else ""
    return f"{sign}{abs(value):.1f} п.п.".replace(".", ",")


def _change(current: float, previous: float) -> float | None:
    current = number(current)
    previous = number(previous)
    if previous == 0:
        return None
    return (current / previous - 1) * 100


def _tone_class(value: float) -> str:
    value = number(value)
    if value > 0:
        return "positive"
    if value < 0:
        return "negative"
    return "neutral"


# =============================================================================
# DATA
# =============================================================================


def _daily_frame(payload: dict) -> pd.DataFrame:
    rows = payload.get("sales", {}).get("daily_price_rows", [])
    frame = pd.DataFrame(rows or [])
    if frame.empty:
        return frame

    if "date_from" not in frame.columns:
        frame["date_from"] = None

    frame["date_from"] = pd.to_datetime(frame["date_from"], errors="coerce")

    for column in ("sales_qty", "avg_price", "net_amount"):
        if column not in frame.columns:
            frame[column] = 0
        frame[column] = pd.to_numeric(frame[column], errors="coerce").fillna(0)

    return (
        frame.dropna(subset=["date_from"])
        .sort_values("date_from")
        .reset_index(drop=True)
    )


def _period_metrics(frame: pd.DataFrame, start: int, end: int | None = None) -> dict:
    if frame.empty:
        return {"sales_qty": 0, "avg_price": 0, "net_amount": 0, "days": 0}

    subset = frame.iloc[start:end].copy()
    if subset.empty:
        return {"sales_qty": 0, "avg_price": 0, "net_amount": 0, "days": 0}

    sales_qty = number(subset["sales_qty"].sum())
    weighted_price = number((subset["sales_qty"] * subset["avg_price"]).sum())
    avg_price = weighted_price / sales_qty if sales_qty else 0

    return {
        "sales_qty": sales_qty,
        "avg_price": avg_price,
        "net_amount": number(subset["net_amount"].sum()),
        "days": len(subset),
    }


def _current_signal(payload: dict) -> dict:
    frame = _daily_frame(payload)
    if frame.empty:
        return {}

    recent_count = min(14, len(frame))
    recent = _period_metrics(frame, -recent_count, None)

    if len(frame) > recent_count:
        previous_count = min(14, len(frame) - recent_count)
        previous = _period_metrics(
            frame,
            -(recent_count + previous_count),
            -recent_count,
        )
    else:
        previous = {}

    return {
        "recent": recent,
        "previous": previous,
        "qty_change_pct": _change(recent.get("sales_qty"), previous.get("sales_qty")),
        "price_change_pct": _change(recent.get("avg_price"), previous.get("avg_price")),
        "revenue_change_pct": _change(recent.get("net_amount"), previous.get("net_amount")),
    }


# =============================================================================
# HEADER / KPI
# =============================================================================


def _masthead(payload: dict) -> str:
    return f"""
    <header class="masthead">
        <div>
            <div class="brandline">ТРЕНДСЕТТЕР · АНАЛИТИКА СПРОСА</div>
            <h1>{TITLE}</h1>
            <div class="mast-subtitle">{SUBTITLE}</div>
        </div>

        <div class="issue-meta">
            Выпуск за <b>{safe(payload.get("report_date"))}</b><br>
            Сформирован автоматически
        </div>
    </header>
    """


def _signal_card(label: str, value: str, note: str, change, *, tone: str = "") -> str:
    if change is None:
        change_html = '<span class="demand-kpi-change neutral">нет базы</span>'
    else:
        change = number(change)
        css = "up" if change > 0 else "down" if change < 0 else "neutral"
        arrow = "▲" if change > 0 else "▼" if change < 0 else "•"
        change_html = f'<span class="demand-kpi-change {css}">{arrow} {_pct(abs(change))}</span>'

    return f"""
    <article class="demand-kpi {safe(tone)}">
        <div class="demand-kpi-label">{safe(label)}</div>
        <div class="demand-kpi-value">{safe(value)}</div>
        <div class="demand-kpi-bottom">
            <span>{safe(note)}</span>
            {change_html}
        </div>
    </article>
    """


def _kpi_row(payload: dict, signal: dict) -> str:
    sales = payload.get("sales", {})
    kpi = sales.get("kpi", {})
    recent = signal.get("recent", {})

    return f"""
    <div class="demand-kpi-grid">
        {_signal_card(
            "Спрос · 14 дней",
            _number(recent.get("sales_qty")) + " ед.",
            "положительных продаж",
            signal.get("qty_change_pct"),
            tone="demand",
        )}

        {_signal_card(
            "Средняя цена · 14 дней",
            _money_short(recent.get("avg_price")),
            "взвешенная по количеству",
            signal.get("price_change_pct"),
            tone="price",
        )}

        {_signal_card(
            "Чистая выручка · 14 дней",
            _money_short(recent.get("net_amount")),
            "с учётом ретро-корректировок",
            signal.get("revenue_change_pct"),
            tone="revenue",
        )}

        {_signal_card(
            "Сегодня · средняя цена",
            _money_short(kpi.get("avg_price")),
            f"{_number(kpi.get('sales_transactions'))} положительных продаж",
            kpi.get("revenue_change_pct"),
            tone="today",
        )}
    </div>
    """


# =============================================================================
# EDITORIAL
# =============================================================================


def _corr_label(value) -> str:
    if value is None:
        return "недостаточно данных"

    value = number(value)
    absolute = abs(value)
    if absolute >= 0.70:
        strength = "сильная"
    elif absolute >= 0.45:
        strength = "заметная"
    elif absolute >= 0.25:
        strength = "умеренная"
    else:
        strength = "слабая"

    direction = "обратная" if value < 0 else "прямая"
    return f"{strength} {direction}"


def _build_editorial(payload: dict, signal: dict) -> dict:
    analysis = payload.get("sales", {}).get("price_analysis", {})

    qty_change = signal.get("qty_change_pct")
    price_change = signal.get("price_change_pct")
    revenue_change = signal.get("revenue_change_pct")

    qty = number(qty_change)
    price = number(price_change)
    revenue = number(revenue_change)

    if qty_change is None or price_change is None:
        title = "Недостаточно базы для оценки текущего режима спроса"
        lead = (
            "90-дневная история построена, однако для сопоставления последних двух "
            "14-дневных периодов пока недостаточно данных."
        )
        tone = "neutral"
    elif qty > 5 and price < -3:
        title = "Спрос ускорился на фоне снижения средней цены"
        lead = (
            "Количество проданных единиц растёт, одновременно средняя цена снижается. "
            "Текущая динамика выручки в большей степени поддерживается физическим спросом."
        )
        tone = "positive"
    elif qty < -5 and price > 3:
        title = "Рост средней цены сопровождается ослаблением физического спроса"
        lead = (
            "Средняя цена выше предыдущего периода, одновременно количество положительных "
            "продаж снизилось. Такая динамика соответствует наблюдаемой обратной связи "
            "между средней ценой и количеством продаж."
        )
        tone = "warning"
    elif qty > 5 and price > 3:
        title = "Спрос и средняя цена растут одновременно"
        lead = (
            "Компания продаёт больше единиц при более высокой средней цене — сильная "
            "комбинация для выручки, которую стоит проверить на уровне товарного микса."
        )
        tone = "positive"
    elif qty < -5 and price < -3:
        title = "Одновременно снижаются спрос и средняя цена"
        lead = (
            "Снижение затронуло оба основных драйвера выручки. Такой режим требует проверки "
            "товарного микса, наличия и активности промо."
        )
        tone = "negative"
    elif abs(qty) <= 5 and price > 3:
        title = "Выручку сейчас больше поддерживает цена, чем объём"
        lead = (
            "Количество проданных единиц существенно не изменилось, а средняя цена выросла. "
            "Динамика носит преимущественно ценовой характер."
        )
        tone = "neutral"
    elif abs(price) <= 3 and qty > 5:
        title = "Рост обеспечен прежде всего физическим спросом"
        lead = (
            "Средняя цена остаётся относительно стабильной, а количество продаж выросло. "
            "Это более чистый сигнал увеличения физического спроса."
        )
        tone = "positive"
    else:
        title = "Режим спроса остаётся относительно стабильным"
        lead = (
            "За последние две недели нет резкого совместного изменения количества продаж "
            "и средней цены."
        )
        tone = "neutral"

    if revenue_change is not None:
        if revenue >= 5:
            lead += f" Чистая выручка за последние 14 дней выросла на {_pct(revenue)}."
        elif revenue <= -5:
            lead += f" Чистая выручка за последние 14 дней снизилась на {_pct(abs(revenue))}."
        else:
            lead += " Чистая выручка остаётся близкой к предыдущему 14-дневному периоду."

    daily_corr = analysis.get("daily_corr")
    monthly_corr = analysis.get("monthly_corr")

    return {
        "title": title,
        "lead": lead,
        "tone": tone,
        "daily_corr": daily_corr,
        "monthly_corr": monthly_corr,
        "daily_corr_label": _corr_label(daily_corr),
        "monthly_corr_label": _corr_label(monthly_corr),
    }


def _editorial_block(editorial: dict) -> str:
    daily_corr = "—" if editorial.get("daily_corr") is None else _pct(number(editorial.get("daily_corr")) * 100)
    monthly_corr = "—" if editorial.get("monthly_corr") is None else _pct(number(editorial.get("monthly_corr")) * 100)

    return f"""
    <section class="demand-editorial {safe(editorial.get('tone'))}">
        <div class="demand-editorial-label">ГЛАВНЫЙ СИГНАЛ</div>
        <div class="demand-editorial-title">{safe(editorial.get("title"))}</div>
        <div class="demand-editorial-copy">{safe(editorial.get("lead"))}</div>

        <div class="demand-corr-strip">
            <div>
                <span>90 дней</span>
                <b>{daily_corr}</b>
                <small>{safe(editorial.get("daily_corr_label"))} связь средней цены и количества</small>
            </div>
            <div>
                <span>12 месяцев</span>
                <b>{monthly_corr}</b>
                <small>{safe(editorial.get("monthly_corr_label"))} связь средней цены и количества</small>
            </div>
        </div>
    </section>
    """


# =============================================================================
# CHART BLOCKS
# =============================================================================


def _regime_block(payload: dict) -> str:
    rows = payload.get("sales", {}).get("daily_price_rows", [])
    chart = demand_price_index_chart(rows)
    if not chart:
        chart = '<div class="demand-empty">Недостаточно данных для 90-дневной динамики.</div>'

    return f"""
    <section class="demand-regime-card">
        <div class="demand-block-head">
            <div>
                <div class="demand-kicker">РЕЖИМ СПРОСА</div>
                <div class="demand-block-title">Что меняется быстрее — цена или количество</div>
                <div class="demand-block-subtitle">7-дневные средние · индекс начала ряда = 100</div>
            </div>
            <div class="demand-chart-caption">последние 90 дней</div>
        </div>

        <div class="demand-regime-chart">{chart}</div>

        <div class="demand-chart-note">
            Индекс показывает относительное изменение показателей. Средняя цена зависит и от
            товарного микса, поэтому график показывает совместную динамику, а не причинный эффект цены.
        </div>
    </section>
    """


def _monthly_block(payload: dict) -> str:
    rows = payload.get("sales", {}).get("monthly_price_rows", [])
    chart = monthly_drivers_chart(rows)
    if not chart:
        chart = '<div class="demand-empty">Недостаточно данных для помесячного анализа.</div>'

    return f"""
    <section class="demand-monthly-card">
        <div class="demand-block-head">
            <div>
                <div class="demand-kicker">12 МЕСЯЦЕВ</div>
                <div class="demand-block-title small">Из чего складывалась динамика выручки</div>
            </div>
            <div class="demand-chart-caption">спрос · цена · чистая выручка</div>
        </div>
        <div class="demand-monthly-chart">{chart}</div>
    </section>
    """


# =============================================================================
# PRICE BALANCE
# =============================================================================


def _focus_brand(brands: list[dict]) -> dict | None:
    """Выбираем самый интересный ценовой кейс, а не первый элемент списка."""

    candidates = []

    for row in brands:
        balance_data = row.get("balance") or {}
        if not balance_data.get("available"):
            continue

        if (row.get("confidence") or "") not in ("Высокая", "Средняя"):
            continue

        balance = balance_data.get("balance") or {}
        price_change = number(balance.get("price_change_pct"))
        qty_change = number(balance.get("qty_change_pct"))

        if abs(price_change) < 1:
            continue

        candidates.append((row, qty_change, number(row.get("revenue_14d"))))

    if candidates:
        candidates.sort(key=lambda item: (item[1], item[2]), reverse=True)
        return candidates[0][0]

    available = [
        row
        for row in brands
        if (row.get("balance") or {}).get("available")
    ]
    available.sort(key=lambda row: number(row.get("revenue_14d")), reverse=True)
    return available[0] if available else None


def _price_opportunity_block(payload: dict) -> str:
    analysis = payload.get("sales", {}).get("brand_price_analysis", {})
    brands = list(analysis.get("brands", []) or [])
    focus = _focus_brand(brands)

    if focus is None:
        return """
        <section class="demand-price-potential">
            <div class="demand-kicker">ЦЕНОВОЙ ПОТЕНЦИАЛ</div>
            <div class="demand-block-title">Где находится баланс спроса и маржи</div>
            <div class="demand-opportunity-empty">
                Для надёжной сценарной оценки пока недостаточно исторической вариации
                средней цены по брендам.
            </div>
        </section>
        """

    balance_data = focus.get("balance") or {}
    balance = balance_data.get("balance") or {}
    max_margin = balance_data.get("max_margin") or {}

    chart = brand_price_scenario_chart(focus)
    if not chart:
        chart = '<div class="demand-empty compact">Не удалось построить сценарную кривую.</div>'

    price_change = number(balance.get("price_change_pct"))
    qty_change = number(balance.get("qty_change_pct"))
    revenue_change = number(balance.get("revenue_change_pct"))
    margin_change = number(balance.get("margin_change_pct"))
    margin_delta_pp = number(balance.get("margin_delta_pp"))

    current_price = number(balance_data.get("base_price"))
    balance_price = number(balance.get("projected_price"))

    max_margin_price = number(max_margin.get("projected_price"))
    max_margin_price_change = number(max_margin.get("price_change_pct"))
    max_margin_change = number(max_margin.get("margin_change_pct"))

    if price_change <= -1:
        action_title = "Есть пространство для теста более низкой цены"
        action_copy = (
            "Расчётная зона находится ниже текущей средней цены. По исторической модели "
            "это может дать дополнительный объём при сохранении маржи вблизи её максимума."
        )
        action_label = "ТЕСТ НИЖЕ"
        action_tone = "positive"
    elif price_change >= 1:
        action_title = "Снижение цены не выглядит необходимым"
        action_copy = (
            "Модельная зона находится выше текущей средней цены: история бренда не показывает, "
            "что скидка создаёт достаточно дополнительного объёма для компенсации маржи."
        )
        action_label = "ЗАЩИЩАТЬ ЦЕНУ"
        action_tone = "positive"
    else:
        action_title = "Текущая цена близка к расчётному балансу"
        action_copy = (
            "Существенного ценового шага модель не требует: текущий уровень уже находится "
            "вблизи эффективного сочетания спроса и маржи."
        )
        action_label = "СОХРАНИТЬ"
        action_tone = "neutral"

    if price_change < -1 and qty_change > 0:
        focus_reason = "максимальный модельный прирост спроса среди надёжных сценариев"
    elif price_change > 1 and margin_change > 0:
        focus_reason = "заметный потенциал роста маржи без стимулирования скидкой"
    else:
        focus_reason = "крупнейший бренд с достаточным качеством сценарной модели"

    # -------------------------------------------------------------------------
    # Компактная таблица: максимум 5 брендов.
    # -------------------------------------------------------------------------

    table_candidates = [
        row for row in brands if (row.get("balance") or {}).get("available")
    ]
    table_candidates.sort(key=lambda row: number(row.get("revenue_14d")), reverse=True)

    table_rows = []

    for row in table_candidates[:5]:
        row_balance_data = row.get("balance") or {}
        row_balance = row_balance_data.get("balance") or {}

        row_price_delta = number(row_balance.get("price_change_pct"))
        row_qty_delta = number(row_balance.get("qty_change_pct"))
        row_margin_delta = number(row_balance.get("margin_change_pct"))
        row_margin_pp = number(row_balance.get("margin_delta_pp"))

        if row_price_delta <= -1:
            row_action = "Тест ниже"
            action_class = "positive"
        elif row_price_delta >= 1:
            row_action = "Защищать"
            action_class = "positive"
        else:
            row_action = "Сохранить"
            action_class = "neutral"

        table_rows.append(
            f"""
            <div class="demand-balance-table-row">
                <div class="brand" title="{safe(row.get('brand'))}">{safe(row.get('brand'))}</div>
                <div>{_money_short(row_balance_data.get('base_price'))}</div>
                <div>{_money_short(row_balance.get('projected_price'))}</div>
                <div class="{action_class}">{_signed_pct(row_price_delta)}</div>
                <div class="{_tone_class(row_qty_delta)}">{_signed_pct(row_qty_delta)}</div>
                <div class="{_tone_class(row_margin_delta)}">{_signed_pct(row_margin_delta)}</div>
                <div class="{_tone_class(row_margin_pp)}">{_signed_pp(row_margin_pp)}</div>
                <div class="{action_class}">{safe(row_action)}</div>
            </div>
            """
        )

    table_html = "".join(table_rows) or (
        '<div class="demand-opportunity-empty">Нет других брендов с достаточным качеством модели.</div>'
    )

    return f"""
    <section class="demand-price-potential">
        <div class="demand-price-potential-head">
            <div>
                <div class="demand-kicker">ЦЕНОВОЙ ПОТЕНЦИАЛ</div>
                <div class="demand-block-title">Где находится баланс спроса и маржи</div>
                <div class="demand-block-subtitle">сценарная модель по брендам · последние 90 дней</div>
            </div>

            <div class="demand-price-rule">
                <b>Как определяется баланс</b>
                Сначала ищем максимум маржи ₽, затем — максимальный спрос в зоне,
                где сохраняется ≥98% этого максимума и маржинальность не падает более чем на 3 п.п.
            </div>
        </div>

        <div class="demand-balance-focus">
            <div class="demand-balance-chart">
                <div class="demand-balance-focus-label">ГЛАВНЫЙ ЦЕНОВОЙ КЕЙС</div>
                <div class="demand-balance-brand">{safe(focus.get("brand"))}</div>
                <div class="demand-balance-focus-reason">
                    Почему выбран: <b>{safe(focus_reason)}</b>
                </div>
                <div class="demand-balance-chart-subtitle">
                    модельная реакция количества и маржи на изменение средней цены
                </div>
                {chart}
            </div>

            <aside class="demand-balance-summary">
                <div class="demand-kicker">РАСЧЁТНАЯ ЗОНА</div>
                <div class="demand-balance-summary-title {safe(action_tone)}">{safe(action_title)}</div>
                <div class="demand-balance-summary-copy">{safe(action_copy)}</div>

                <div class="demand-balance-verdict">
                    <span>МОДЕЛЬНЫЙ ЦЕНОВОЙ ШАГ</span>
                    <b>{_signed_pct(price_change)}</b>
                </div>

                <div class="demand-balance-price">
                    <div>
                        <span>Сейчас</span>
                        <b>{_money_short(current_price)}</b>
                    </div>
                    <div class="arrow">→</div>
                    <div>
                        <span>Баланс</span>
                        <b class="accent">{_money_short(balance_price)}</b>
                    </div>
                </div>

                <div class="demand-balance-metrics">
                    <div><span>Количество</span><b class="{_tone_class(qty_change)}">{_signed_pct(qty_change)}</b></div>
                    <div><span>Выручка</span><b class="{_tone_class(revenue_change)}">{_signed_pct(revenue_change)}</b></div>
                    <div><span>Маржа ₽</span><b class="{_tone_class(margin_change)}">{_signed_pct(margin_change)}</b></div>
                    <div><span>Маржинальность</span><b class="{_tone_class(margin_delta_pp)}">{_signed_pp(margin_delta_pp)}</b></div>
                </div>

                <div class="demand-balance-max">
                    <div class="demand-balance-max-label">АЛЬТЕРНАТИВА · MAX МАРЖИ ₽</div>
                    <div class="demand-balance-max-main">
                        <b>{_money_short(max_margin_price)}</b>
                        <span>{_signed_pct(max_margin_price_change)} к текущей цене</span>
                    </div>
                    <div class="demand-balance-max-note">
                        модельная маржа ₽ {_signed_pct(max_margin_change)} к текущему уровню
                    </div>
                    <div class="demand-balance-max-explain">
                        Баланс допускает небольшой отказ от абсолютного максимума маржи ради большего объёма.
                    </div>
                </div>

                <div class="demand-balance-model">
                    чувствительность <b>{f"{number(focus.get('elasticity')):.2f}".replace('.', ',')}</b>
                    · качество <b>{safe(focus.get('confidence'))}</b>
                    · наблюдений <b>{int(number(focus.get('observations')))}</b>
                </div>

                <div class="demand-balance-action">{safe(action_label)}</div>
            </aside>
        </div>

        <div class="demand-balance-table">
            <div class="demand-balance-table-title">БРЕНДЫ · РАСЧЁТНАЯ ЗОНА</div>
            <div class="demand-balance-table-row header">
                <div>Бренд</div>
                <div>Сейчас</div>
                <div>Баланс</div>
                <div>Δ цены</div>
                <div>Δ спроса</div>
                <div>Δ маржи ₽</div>
                <div>Δ маржи %</div>
                <div>Сигнал</div>
            </div>
            {table_html}
        </div>

        <div class="demand-price-disclaimer">
            Сценарии — модельная оценка статистической связи средней цены и количества, а не гарантия эффекта.
            Средняя цена зависит от товарного микса. Маржа рассчитана после управленческой FIFO-себестоимости
            и комиссии WB, но без маркетинга, штрафов и прочих распределяемых расходов WB.
        </div>
    </section>
    """


# =============================================================================
# BRAND SIGNALS
# =============================================================================


def _brand_anomalies_block(payload: dict) -> str:
    anomalies = (
        payload.get("sales", {})
        .get("brand_price_analysis", {})
        .get("anomalies", [])
    )

    anomalies = list(anomalies or [])[:4]

    if not anomalies:
        return """
        <section class="demand-anomalies">
            <div class="demand-kicker">ЦЕНОВЫЕ СИГНАЛЫ</div>
            <div class="demand-anomalies-clear">
                Существенных ценовых сигналов по брендам за последние 14 дней не выявлено.
            </div>
        </section>
        """

    cards = []
    for item in anomalies:
        cards.append(
            f"""
            <div class="demand-anomaly {safe(item.get('tone'))}">
                <div class="demand-anomaly-brand">{safe(item.get("brand"))}</div>
                <div class="demand-anomaly-title">{safe(item.get("title"))}</div>
                <div class="demand-anomaly-numbers">
                    <span>средняя цена <b>{_signed_pct(item.get("price_change_pct"))}</b></span>
                    <span>количество <b>{_signed_pct(item.get("qty_change_pct"))}</b></span>
                    <span>маржа <b>{_pct(item.get("margin_pct"))}</b></span>
                </div>
            </div>
            """
        )

    return f"""
    <section class="demand-anomalies">
        <div class="demand-anomalies-head">
            <div>
                <div class="demand-kicker">ЦЕНОВЫЕ СИГНАЛЫ</div>
                <div class="demand-block-title small">Что изменилось вместе с ценой</div>
            </div>
            <div class="demand-chart-caption">последние 14 дней против предыдущих 14</div>
        </div>
        <div class="demand-anomalies-grid">{"".join(cards)}</div>
    </section>
    """


# =============================================================================
# METHODOLOGY
# =============================================================================


def _methodology_block() -> str:
    return """
    <section class="demand-methodology">
        <div class="demand-kicker">КАК ЧИТАТЬ СТРАНИЦУ</div>
        <div class="demand-methodology-grid">
            <div>
                <b>Спрос измеряется физическими продажами.</b>
                Для анализа количества используются только положительные продажи;
                возвраты не считаются отрицательным спросом.
            </div>
            <div>
                <b>Средняя цена взвешена количеством.</b>
                Поэтому её изменение отражает одновременно уровень цены продажи
                и изменение товарного микса.
            </div>
            <div>
                <b>Чистая выручка пересчитывается ретроспективно.</b>
                Возврат корректирует исходную дату реализации, поэтому исторические
                значения могут изменяться после появления новых возвратов.
            </div>
        </div>
    </section>
    """


# =============================================================================
# PAGE
# =============================================================================


def build_demand_page(payload: dict) -> str:
    signal = _current_signal(payload)
    editorial = _build_editorial(payload, signal)

    return f"""
    <!-- =============================================================
         DEMAND & PRICE PAGE
         ============================================================= -->

    <div class="page demand-page">
        {_masthead(payload)}
        {_kpi_row(payload, signal)}

        <div class="demand-top-grid">
            {_editorial_block(editorial)}
            {_monthly_block(payload)}
        </div>

        {_regime_block(payload)}
        {_price_opportunity_block(payload)}
        {_brand_anomalies_block(payload)}
        {_methodology_block()}

        <div class="demand-footer-note">
            <span>Спрос: количество положительных продаж.</span>
            <span>Горизонт анализа: 14 дней · 90 дней · 12 месяцев.</span>
        </div>
    </div>
    """