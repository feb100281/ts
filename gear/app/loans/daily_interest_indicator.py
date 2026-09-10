# # gear/app/loans/daily_interest_indicator.py
# from __future__ import annotations

# from datetime import date
# from typing import Any

# import dash_mantine_components as dmc
# import pandas as pd
# from dateutil.relativedelta import relativedelta
# from dash import Input, Output, State, html
# from dash_iconify import DashIconify
# from psycopg.rows import dict_row

# from .config import COLORS
# from .data import get_db_connection
# from .ids import DATA_SIGNAL_ID, REPORT_DATE_ID


# # =====================================================================
# # IDs
# # =====================================================================

# DAILY_INTEREST_BUTTON_ID = "loans-daily-interest-button"
# DAILY_INTEREST_VALUE_ID = "loans-daily-interest-value"
# DAILY_INTEREST_CHANGE_ID = "loans-daily-interest-change"

# DAILY_INTEREST_MODAL_ID = "loans-daily-interest-modal"
# DAILY_INTEREST_MODAL_CLOSE_ID = "loans-daily-interest-modal-close"
# DAILY_INTEREST_MODAL_DATE_ID = "loans-daily-interest-modal-date"

# DAILY_INTEREST_TODAY_ID = "loans-daily-interest-today"
# DAILY_INTEREST_YESTERDAY_ID = "loans-daily-interest-yesterday"
# DAILY_INTEREST_MONTH_ID = "loans-daily-interest-month"
# DAILY_INTEREST_YEAR_ID = "loans-daily-interest-year"

# DAILY_INTEREST_VS_YESTERDAY_ID = "loans-daily-interest-vs-yesterday"
# DAILY_INTEREST_VS_MONTH_ID = "loans-daily-interest-vs-month"
# DAILY_INTEREST_VS_YEAR_ID = "loans-daily-interest-vs-year"

# DAILY_INTEREST_DETAILS_ID = "loans-daily-interest-details"


# # =====================================================================
# # HELPERS
# # =====================================================================

# def _as_date(value: Any) -> date | None:
#     parsed = pd.to_datetime(value, errors="coerce")
#     return None if pd.isna(parsed) else parsed.date()


# def _float(value: Any) -> float:
#     try:
#         return float(value or 0)
#     except (TypeError, ValueError):
#         return 0.0


# def _money(value: Any) -> str:
#     return f"{_float(value):,.2f}".replace(",", " ")


# def _money_short(value: Any) -> str:
#     value = _float(value)
#     absolute = abs(value)

#     if absolute >= 1_000_000_000:
#         return f"{value / 1_000_000_000:,.2f}".replace(",", " ") + " млрд"
#     if absolute >= 1_000_000:
#         return f"{value / 1_000_000:,.2f}".replace(",", " ") + " млн"
#     if absolute >= 100_000:
#         return f"{value / 1_000:,.2f}".replace(",", " ") + " тыс."

#     return _money(value)


# def _pct(value: float | None) -> str:
#     if value is None:
#         return "—"
#     sign = "+" if value > 0 else ""
#     return f"{sign}{value:.1f}%".replace(".", ",")


# def _compare(current: float, previous: float) -> dict:
#     delta = current - previous

#     if abs(previous) > 0.000001:
#         percent = delta / abs(previous) * 100.0
#     elif abs(current) <= 0.000001:
#         percent = 0.0
#     else:
#         percent = None

#     if delta > 0.005:
#         direction = "up"
#     elif delta < -0.005:
#         direction = "down"
#     else:
#         direction = "flat"

#     return {
#         "delta": delta,
#         "percent": percent,
#         "direction": direction,
#     }


# def _direction_color(direction: str) -> str:
#     # Рост процентных расходов = негативный сигнал.
#     if direction == "up":
#         return COLORS.get("red", "#B91C1C")
#     if direction == "down":
#         return COLORS.get("green", "#15803D")
#     return COLORS["muted"]


# def _direction_icon(direction: str) -> str:
#     if direction == "up":
#         return "solar:arrow-up-linear"
#     if direction == "down":
#         return "solar:arrow-down-linear"
#     return "solar:minus-circle-linear"


# def _totals(df: pd.DataFrame) -> dict[str, float]:
#     if df.empty:
#         return {}

#     result = {}

#     for currency, value in (
#         df.groupby("currency", dropna=False)["interest_accrued"].sum().items()
#     ):
#         currency = (
#             str(currency)
#             if pd.notna(currency) and str(currency).strip()
#             else "—"
#         )
#         result[currency] = float(value or 0)

#     return result


# def _format_totals(values: dict[str, float], short: bool = False) -> str:
#     if not values:
#         return "0,00"

#     formatter = _money_short if short else _money

#     return " · ".join(
#         f"{formatter(amount)} {currency}".strip()
#         for currency, amount in sorted(values.items())
#     )


# def _single_currency(values: dict[str, float]) -> tuple[float, str | None]:
#     non_zero = {
#         currency: amount
#         for currency, amount in values.items()
#         if abs(amount) > 0.005
#     }

#     source = non_zero or values

#     if len(source) != 1:
#         return 0.0, None

#     currency, amount = next(iter(source.items()))
#     return float(amount), currency


# # =====================================================================
# # DATA
# # =====================================================================

# def get_daily_interest_accruals(target_dates: list[date]) -> pd.DataFrame:
#     """
#     Фактическое начисление процентов из gl.borrowings_tp.

#     interest_accrued хранится в копейках, поэтому / 100.

#     Используем psycopg cursor, а не pd.read_sql_query:
#     так здесь не будет pandas warning про SQLAlchemy.
#     """
#     if not target_dates:
#         return pd.DataFrame()

#     query = """
#         SELECT
#             t.date_from::date AS accrual_date,
#             t.contract_id,

#             c.number AS contract_number,
#             c.date::date AS contract_date,
#             cp.name AS counterparty_name,
#             COALESCE(c.currency, '') AS currency,

#             SUM(
#                 COALESCE(t.interest_accrued, 0)
#             ) / 100.0 AS interest_accrued,

#             MAX(
#                 COALESCE(t.rate, 0)
#             ) AS rate

#         FROM gl.borrowings_tp t

#         LEFT JOIN public.contracts_contracts c
#             ON c.id = t.contract_id

#         LEFT JOIN public.counterparties_counterparty cp
#             ON cp.id = c.cp_id

#         WHERE
#             t.date_from::date = ANY(%s::date[])

#         GROUP BY
#             t.date_from::date,
#             t.contract_id,
#             c.number,
#             c.date::date,
#             cp.name,
#             c.currency

#         ORDER BY
#             t.date_from::date DESC,
#             interest_accrued DESC,
#             cp.name NULLS LAST,
#             c.number NULLS LAST
#     """

#     with get_db_connection() as conn:
#         with conn.cursor(row_factory=dict_row) as cur:
#             cur.execute(query, (target_dates,))
#             rows = cur.fetchall()

#     if not rows:
#         return pd.DataFrame(
#             columns=[
#                 "accrual_date",
#                 "contract_id",
#                 "contract_number",
#                 "contract_date",
#                 "counterparty_name",
#                 "currency",
#                 "interest_accrued",
#                 "rate",
#             ]
#         )

#     df = pd.DataFrame(rows)

#     df["accrual_date"] = pd.to_datetime(
#         df["accrual_date"],
#         errors="coerce",
#     )
#     df["contract_date"] = pd.to_datetime(
#         df["contract_date"],
#         errors="coerce",
#     )
#     df["interest_accrued"] = pd.to_numeric(
#         df["interest_accrued"],
#         errors="coerce",
#     ).fillna(0.0)
#     df["rate"] = pd.to_numeric(
#         df["rate"],
#         errors="coerce",
#     ).fillna(0.0)

#     return df


# def get_daily_interest_dataset(report_date: str | date) -> dict:
#     current_date = _as_date(report_date) or date.today()

#     yesterday = current_date - relativedelta(days=1)
#     month_ago = current_date - relativedelta(months=1)
#     year_ago = current_date - relativedelta(years=1)

#     df = get_daily_interest_accruals(
#         [
#             current_date,
#             yesterday,
#             month_ago,
#             year_ago,
#         ]
#     )

#     def take(target: date) -> pd.DataFrame:
#         if df.empty:
#             return df.copy()

#         return df[
#             df["accrual_date"].dt.date == target
#         ].copy()

#     return {
#         "report_date": current_date,
#         "yesterday_date": yesterday,
#         "month_date": month_ago,
#         "year_date": year_ago,

#         "today": take(current_date),
#         "yesterday": take(yesterday),
#         "month": take(month_ago),
#         "year": take(year_ago),
#     }


# # =====================================================================
# # HEADER INDICATOR
# # =====================================================================

# def build_daily_interest_indicator():
#     """
#     Маленький показатель для шапки.
#     По клику открывается модалка.
#     """
#     return dmc.UnstyledButton(
#         id=DAILY_INTEREST_BUTTON_ID,

#         style={
#             "height": "34px",
#             "display": "flex",
#             "alignItems": "center",
#             "gap": "7px",
#             "padding": "0 9px",
#             "backgroundColor": "#FFFFFF",
#             "border": f"1px solid {COLORS['border']}",
#             "cursor": "pointer",
#         },

#         children=[
#             DashIconify(
#                 icon="solar:percent-circle-linear",
#                 width=16,
#                 color=COLORS.get("green", "#15803D"),
#             ),

#             html.Div(
#                 style={
#                     "display": "flex",
#                     "flexDirection": "column",
#                     "alignItems": "flex-start",
#                 },
#                 children=[
#                     html.Div(
#                         "Начислено за день",
#                         style={
#                             "fontSize": "9px",
#                             "lineHeight": "10px",
#                             "color": COLORS["muted"],
#                         },
#                     ),
#                     html.Div(
#                         id=DAILY_INTEREST_VALUE_ID,
#                         children="—",
#                         style={
#                             "marginTop": "2px",
#                             "fontSize": "11px",
#                             "lineHeight": "12px",
#                             "fontWeight": 700,
#                             "color": COLORS["text"],
#                             "fontVariantNumeric": "tabular-nums",
#                         },
#                     ),
#                 ],
#             ),

#             html.Div(
#                 id=DAILY_INTEREST_CHANGE_ID,
#                 children="",
#                 style={
#                     "fontSize": "9px",
#                     "fontWeight": 700,
#                     "whiteSpace": "nowrap",
#                 },
#             ),

#             DashIconify(
#                 icon="solar:info-circle-linear",
#                 width=13,
#                 color=COLORS["muted"],
#             ),
#         ],
#     )


# # =====================================================================
# # MODAL UI
# # =====================================================================

# def _summary_card(
#     *,
#     title: str,
#     value_id: str,
#     comparison_id: str | None = None,
# ):
#     children = [
#         html.Div(
#             title,
#             style={
#                 "fontSize": "9px",
#                 "color": COLORS["muted"],
#             },
#         ),
#         html.Div(
#             id=value_id,
#             children="—",
#             style={
#                 "marginTop": "4px",
#                 "fontSize": "17px",
#                 "fontWeight": 700,
#                 "color": COLORS["text"],
#                 "fontVariantNumeric": "tabular-nums",
#             },
#         ),
#     ]

#     if comparison_id:
#         children.append(
#             html.Div(
#                 id=comparison_id,
#                 children="",
#                 style={"marginTop": "5px"},
#             )
#         )

#     return html.Div(
#         style={
#             "padding": "9px 10px",
#             "backgroundColor": "#FFFFFF",
#             "border": f"1px solid {COLORS['border']}",
#         },
#         children=children,
#     )


# def _comparison_view(
#     current: float,
#     previous: float,
#     currency: str,
# ):
#     comparison = _compare(
#         current,
#         previous,
#     )

#     direction = comparison["direction"]
#     color = _direction_color(direction)
#     delta = comparison["delta"]
#     percent = comparison["percent"]

#     sign = "+" if delta > 0 else ""

#     return html.Div(
#         style={
#             "display": "flex",
#             "alignItems": "center",
#             "gap": "4px",
#         },
#         children=[
#             DashIconify(
#                 icon=_direction_icon(direction),
#                 width=12,
#                 color=color,
#             ),
#             html.Span(
#                 (
#                     f"{sign}{_money_short(delta)} "
#                     f"{currency}"
#                 ).strip(),
#                 style={
#                     "fontSize": "10px",
#                     "fontWeight": 700,
#                     "color": color,
#                 },
#             ),
#             html.Span(
#                 (
#                     f"({_pct(percent)})"
#                     if percent is not None
#                     else "(новая база)"
#                 ),
#                 style={
#                     "fontSize": "9px",
#                     "color": COLORS["muted"],
#                 },
#             ),
#         ],
#     )


# def _detail_row(row: dict):
#     counterparty = (
#         row.get("counterparty_name")
#         or "Контрагент не указан"
#     )
#     number = (
#         row.get("contract_number")
#         or "б/н"
#     )

#     contract_date = pd.to_datetime(
#         row.get("contract_date"),
#         errors="coerce",
#     )

#     date_text = (
#         contract_date.strftime("%d.%m.%Y")
#         if pd.notna(contract_date)
#         else "без даты"
#     )

#     amount = _float(
#         row.get("interest_accrued")
#     )
#     rate = _float(
#         row.get("rate")
#     )
#     currency = (
#         row.get("currency")
#         or ""
#     )

#     return html.Div(
#         style={
#             "display": "grid",
#             "gridTemplateColumns": "minmax(260px, 1fr) 170px 100px",
#             "gap": "12px",
#             "alignItems": "center",
#             "padding": "8px 12px",
#             "borderBottom": f"1px solid {COLORS['border']}",
#         },

#         children=[
#             html.Div(
#                 children=[
#                     html.Div(
#                         counterparty,
#                         style={
#                             "fontSize": "11px",
#                             "fontWeight": 700,
#                             "color": COLORS["text"],
#                         },
#                     ),
#                     html.Div(
#                         f"Договор № {number} от {date_text}",
#                         style={
#                             "marginTop": "1px",
#                             "fontSize": "9px",
#                             "color": COLORS["muted"],
#                         },
#                     ),
#                 ],
#             ),

#             html.Div(
#                 f"{_money(amount)} {currency}".strip(),
#                 style={
#                     "fontSize": "11px",
#                     "fontWeight": 700,
#                     "textAlign": "right",
#                     "fontVariantNumeric": "tabular-nums",
#                 },
#             ),

#             html.Div(
#                 f"{rate:.2f}%".replace(".", ","),
#                 style={
#                     "fontSize": "10px",
#                     "textAlign": "right",
#                     "color": COLORS["muted"],
#                 },
#             ),
#         ],
#     )


# def build_daily_interest_modal():
#     return dmc.Modal(
#         id=DAILY_INTEREST_MODAL_ID,

#         opened=False,
#         centered=True,
#         size="80%",
#         radius=0,
#         padding=0,
#         withCloseButton=False,

#         styles={
#             "content": {
#                 "maxWidth": "1200px",
#             },
#             "body": {
#                 "padding": "0",
#             },
#             "header": {
#                 "display": "none",
#             },
#         },

#         children=[
#             # HEADER
#             html.Div(
#                 style={
#                     "display": "flex",
#                     "alignItems": "center",
#                     "justifyContent": "space-between",
#                     "gap": "12px",
#                     "padding": "11px 14px",
#                     "borderBottom": f"1px solid {COLORS['border']}",
#                 },

#                 children=[
#                     html.Div(
#                         style={
#                             "display": "flex",
#                             "alignItems": "center",
#                             "gap": "8px",
#                         },
#                         children=[
#                             DashIconify(
#                                 icon="solar:percent-circle-linear",
#                                 width=18,
#                                 color=COLORS.get("green", "#15803D"),
#                             ),

#                             html.Div(
#                                 children=[
#                                     html.Div(
#                                         "Процентная нагрузка за день",
#                                         style={
#                                             "fontSize": "15px",
#                                             "fontWeight": 700,
#                                             "color": COLORS["text"],
#                                         },
#                                     ),
#                                     html.Div(
#                                         id=DAILY_INTEREST_MODAL_DATE_ID,
#                                         children="",
#                                         style={
#                                             "marginTop": "2px",
#                                             "fontSize": "9px",
#                                             "color": COLORS["muted"],
#                                         },
#                                     ),
#                                 ],
#                             ),
#                         ],
#                     ),

#                     dmc.ActionIcon(
#                         id=DAILY_INTEREST_MODAL_CLOSE_ID,
#                         variant="subtle",
#                         color="gray",
#                         radius=0,
#                         size="lg",
#                         children=DashIconify(
#                             icon="solar:close-circle-linear",
#                             width=19,
#                         ),
#                     ),
#                 ],
#             ),

#             # SUMMARY
#             html.Div(
#                 style={
#                     "display": "grid",
#                     "gridTemplateColumns": "repeat(4, minmax(0, 1fr))",
#                     "gap": "7px",
#                     "padding": "10px 14px",
#                 },

#                 children=[
#                     _summary_card(
#                         title="Текущий день",
#                         value_id=DAILY_INTEREST_TODAY_ID,
#                     ),

#                     _summary_card(
#                         title="Вчера",
#                         value_id=DAILY_INTEREST_YESTERDAY_ID,
#                         comparison_id=DAILY_INTEREST_VS_YESTERDAY_ID,
#                     ),

#                     _summary_card(
#                         title="Месяц назад",
#                         value_id=DAILY_INTEREST_MONTH_ID,
#                         comparison_id=DAILY_INTEREST_VS_MONTH_ID,
#                     ),

#                     _summary_card(
#                         title="Год назад",
#                         value_id=DAILY_INTEREST_YEAR_ID,
#                         comparison_id=DAILY_INTEREST_VS_YEAR_ID,
#                     ),
#                 ],
#             ),

#             # TABLE HEADER
#             html.Div(
#                 style={
#                     "display": "grid",
#                     "gridTemplateColumns": "minmax(260px, 1fr) 170px 100px",
#                     "gap": "12px",
#                     "padding": "7px 12px",
#                     "backgroundColor": "#F8FAF9",
#                     "borderTop": f"1px solid {COLORS['border']}",
#                     "borderBottom": f"1px solid {COLORS['border']}",
#                 },

#                 children=[
#                     html.Div(
#                         "Договор",
#                         style={
#                             "fontSize": "9px",
#                             "fontWeight": 700,
#                             "color": COLORS["muted"],
#                         },
#                     ),
#                     html.Div(
#                         "Начислено за день",
#                         style={
#                             "fontSize": "9px",
#                             "fontWeight": 700,
#                             "textAlign": "right",
#                             "color": COLORS["muted"],
#                         },
#                     ),
#                     html.Div(
#                         "Ставка",
#                         style={
#                             "fontSize": "9px",
#                             "fontWeight": 700,
#                             "textAlign": "right",
#                             "color": COLORS["muted"],
#                         },
#                     ),
#                 ],
#             ),

#             # DETAILS
#             html.Div(
#                 id=DAILY_INTEREST_DETAILS_ID,
#                 children=[],
#                 style={
#                     "maxHeight": "400px",
#                     "overflowY": "auto",
#                     "overflowX": "hidden",
#                 },
#             ),
#         ],
#     )


# # =====================================================================
# # CALLBACKS
# # =====================================================================

# def register_daily_interest_callbacks(app):
#     # ---------------------------------------------------------------
#     # OPEN / CLOSE
#     # Не используем dash.ctx из-за django_plotly_dash.
#     # ---------------------------------------------------------------
#     @app.callback(
#         Output(
#             DAILY_INTEREST_MODAL_ID,
#             "opened",
#         ),
#         Input(
#             DAILY_INTEREST_BUTTON_ID,
#             "n_clicks",
#         ),
#         Input(
#             DAILY_INTEREST_MODAL_CLOSE_ID,
#             "n_clicks",
#         ),
#         State(
#             DAILY_INTEREST_MODAL_ID,
#             "opened",
#         ),
#         prevent_initial_call=True,
#     )
#     def toggle_daily_interest_modal(
#         open_clicks,
#         close_clicks,
#         opened,
#     ):
#         return not bool(opened)

#     # ---------------------------------------------------------------
#     # DATA
#     # ---------------------------------------------------------------
#     @app.callback(
#         Output(
#             DAILY_INTEREST_VALUE_ID,
#             "children",
#         ),
#         Output(
#             DAILY_INTEREST_CHANGE_ID,
#             "children",
#         ),
#         Output(
#             DAILY_INTEREST_CHANGE_ID,
#             "style",
#         ),

#         Output(
#             DAILY_INTEREST_MODAL_DATE_ID,
#             "children",
#         ),

#         Output(
#             DAILY_INTEREST_TODAY_ID,
#             "children",
#         ),
#         Output(
#             DAILY_INTEREST_YESTERDAY_ID,
#             "children",
#         ),
#         Output(
#             DAILY_INTEREST_MONTH_ID,
#             "children",
#         ),
#         Output(
#             DAILY_INTEREST_YEAR_ID,
#             "children",
#         ),

#         Output(
#             DAILY_INTEREST_VS_YESTERDAY_ID,
#             "children",
#         ),
#         Output(
#             DAILY_INTEREST_VS_MONTH_ID,
#             "children",
#         ),
#         Output(
#             DAILY_INTEREST_VS_YEAR_ID,
#             "children",
#         ),

#         Output(
#             DAILY_INTEREST_DETAILS_ID,
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
#     def update_daily_interest(
#         _signal,
#         report_date,
#     ):
#         base_change_style = {
#             "fontSize": "9px",
#             "fontWeight": 700,
#             "whiteSpace": "nowrap",
#         }

#         if not report_date:
#             return (
#                 "—",
#                 "",
#                 base_change_style,
#                 "",
#                 "—",
#                 "—",
#                 "—",
#                 "—",
#                 "",
#                 "",
#                 "",
#                 [],
#             )

#         data = get_daily_interest_dataset(
#             str(report_date)[:10]
#         )

#         today_df = data["today"]
#         yesterday_df = data["yesterday"]
#         month_df = data["month"]
#         year_df = data["year"]

#         today_totals = _totals(today_df)
#         yesterday_totals = _totals(yesterday_df)
#         month_totals = _totals(month_df)
#         year_totals = _totals(year_df)

#         today_value, currency = _single_currency(
#             today_totals
#         )

#         # -----------------------------------------------------------
#         # Маленький индикатор
#         # -----------------------------------------------------------
#         if currency:
#             indicator_value = (
#                 f"{_money_short(today_value)} "
#                 f"{currency}"
#             ).strip()

#             yesterday_value = float(
#                 yesterday_totals.get(
#                     currency,
#                     0.0,
#                 )
#             )

#             comp = _compare(
#                 today_value,
#                 yesterday_value,
#             )

#             indicator_change = _pct(
#                 comp["percent"]
#             )

#             indicator_style = {
#                 **base_change_style,
#                 "color": _direction_color(
#                     comp["direction"]
#                 ),
#             }

#         elif len(today_totals) > 1:
#             indicator_value = (
#                 f"{len(today_totals)} валюты"
#             )
#             indicator_change = ""
#             indicator_style = {
#                 **base_change_style,
#                 "color": COLORS["muted"],
#             }

#         else:
#             indicator_value = "0,00"
#             indicator_change = ""
#             indicator_style = {
#                 **base_change_style,
#                 "color": COLORS["muted"],
#             }

#         # -----------------------------------------------------------
#         # Сравнения
#         # Валюты между собой не складываем.
#         # -----------------------------------------------------------
#         if currency:
#             current = float(
#                 today_totals.get(
#                     currency,
#                     0.0,
#                 )
#             )

#             vs_yesterday = _comparison_view(
#                 current,
#                 float(
#                     yesterday_totals.get(
#                         currency,
#                         0.0,
#                     )
#                 ),
#                 currency,
#             )

#             vs_month = _comparison_view(
#                 current,
#                 float(
#                     month_totals.get(
#                         currency,
#                         0.0,
#                     )
#                 ),
#                 currency,
#             )

#             vs_year = _comparison_view(
#                 current,
#                 float(
#                     year_totals.get(
#                         currency,
#                         0.0,
#                     )
#                 ),
#                 currency,
#             )

#         else:
#             multi_note = html.Span(
#                 "Несколько валют — сравнение % не суммируется",
#                 style={
#                     "fontSize": "9px",
#                     "color": COLORS["muted"],
#                 },
#             )

#             vs_yesterday = multi_note
#             vs_month = multi_note
#             vs_year = multi_note

#         # -----------------------------------------------------------
#         # Детализация текущего дня
#         # -----------------------------------------------------------
#         details = []

#         if not today_df.empty:
#             work = today_df.sort_values(
#                 [
#                     "currency",
#                     "interest_accrued",
#                     "counterparty_name",
#                 ],
#                 ascending=[
#                     True,
#                     False,
#                     True,
#                 ],
#             )

#             details = [
#                 _detail_row(row)
#                 for row in work.to_dict("records")
#                 if abs(
#                     _float(
#                         row.get(
#                             "interest_accrued"
#                         )
#                     )
#                 ) > 0.005
#             ]

#         if not details:
#             details = [
#                 html.Div(
#                     "За выбранный день начислений процентов нет",
#                     style={
#                         "padding": "22px",
#                         "fontSize": "11px",
#                         "textAlign": "center",
#                         "color": COLORS["muted"],
#                     },
#                 )
#             ]

#         report = data["report_date"]
#         yesterday = data["yesterday_date"]
#         month_date = data["month_date"]
#         year_date = data["year_date"]

#         modal_date = (
#             f"{report.strftime('%d.%m.%Y')} · "
#             f"вчера {yesterday.strftime('%d.%m.%Y')} · "
#             f"месяц назад {month_date.strftime('%d.%m.%Y')} · "
#             f"год назад {year_date.strftime('%d.%m.%Y')}"
#         )

#         return (
#             indicator_value,
#             indicator_change,
#             indicator_style,

#             modal_date,

#             _format_totals(today_totals),
#             _format_totals(yesterday_totals),
#             _format_totals(month_totals),
#             _format_totals(year_totals),

#             vs_yesterday,
#             vs_month,
#             vs_year,

#             details,
#         )




# gear/app/loans/daily_interest_indicator.py
from __future__ import annotations

from datetime import date
from typing import Any

import dash_mantine_components as dmc
import pandas as pd
from dateutil.relativedelta import relativedelta
from dash import Input, Output, State, html
from dash_iconify import DashIconify
from psycopg.rows import dict_row

from .config import COLORS
from .data import get_db_connection
from .ids import DATA_SIGNAL_ID, REPORT_DATE_ID


# =====================================================================
# IDs
# =====================================================================

DAILY_INTEREST_BUTTON_ID = "loans-daily-interest-button"
DAILY_INTEREST_VALUE_ID = "loans-daily-interest-value"
DAILY_INTEREST_CHANGE_ID = "loans-daily-interest-change"

DAILY_INTEREST_MODAL_ID = "loans-daily-interest-modal"
DAILY_INTEREST_MODAL_CLOSE_ID = "loans-daily-interest-modal-close"
DAILY_INTEREST_MODAL_DATE_ID = "loans-daily-interest-modal-date"

DAILY_INTEREST_TODAY_ID = "loans-daily-interest-today"
DAILY_INTEREST_YESTERDAY_ID = "loans-daily-interest-yesterday"
DAILY_INTEREST_MONTH_ID = "loans-daily-interest-month"
DAILY_INTEREST_YEAR_ID = "loans-daily-interest-year"

DAILY_INTEREST_VS_YESTERDAY_ID = "loans-daily-interest-vs-yesterday"
DAILY_INTEREST_VS_MONTH_ID = "loans-daily-interest-vs-month"
DAILY_INTEREST_VS_YEAR_ID = "loans-daily-interest-vs-year"

DAILY_INTEREST_DETAILS_ID = "loans-daily-interest-details"


# =====================================================================
# HELPERS
# =====================================================================

def _as_date(value: Any) -> date | None:
    parsed = pd.to_datetime(value, errors="coerce")
    return None if pd.isna(parsed) else parsed.date()


def _float(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _money(value: Any) -> str:
    return f"{_float(value):,.2f}".replace(",", " ")


def _money_short(value: Any) -> str:
    value = _float(value)
    absolute = abs(value)

    if absolute >= 1_000_000_000:
        return f"{value / 1_000_000_000:,.2f}".replace(",", " ") + " млрд"
    if absolute >= 1_000_000:
        return f"{value / 1_000_000:,.2f}".replace(",", " ") + " млн"
    if absolute >= 100_000:
        return f"{value / 1_000:,.2f}".replace(",", " ") + " тыс."

    return _money(value)


def _pct(value: float | None) -> str:
    if value is None:
        return "—"
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.1f}%".replace(".", ",")


def _compare(current: float, previous: float) -> dict:
    delta = current - previous

    if abs(previous) > 0.000001:
        percent = delta / abs(previous) * 100.0
    elif abs(current) <= 0.000001:
        percent = 0.0
    else:
        percent = None

    if delta > 0.005:
        direction = "up"
    elif delta < -0.005:
        direction = "down"
    else:
        direction = "flat"

    return {
        "delta": delta,
        "percent": percent,
        "direction": direction,
    }


def _direction_color(direction: str) -> str:
    # Рост процентных расходов = негативный сигнал.
    if direction == "up":
        return COLORS.get("red", "#B91C1C")
    if direction == "down":
        return COLORS.get("green", "#15803D")
    return COLORS["muted"]


def _direction_icon(direction: str) -> str:
    if direction == "up":
        return "solar:arrow-up-linear"
    if direction == "down":
        return "solar:arrow-down-linear"
    return "solar:minus-circle-linear"


def _totals(df: pd.DataFrame) -> dict[str, float]:
    if df.empty:
        return {}

    result = {}

    for currency, value in (
        df.groupby("currency", dropna=False)["interest_accrued"].sum().items()
    ):
        currency = (
            str(currency)
            if pd.notna(currency) and str(currency).strip()
            else "—"
        )
        result[currency] = float(value or 0)

    return result


def _format_totals(values: dict[str, float], short: bool = False) -> str:
    if not values:
        return "0,00"

    formatter = _money_short if short else _money

    return " · ".join(
        f"{formatter(amount)} {currency}".strip()
        for currency, amount in sorted(values.items())
    )


def _direction_totals_text(df: pd.DataFrame, short: bool = False) -> str:
    """Процентный расход и доход никогда не складываются между собой."""
    if df.empty:
        return "Расход 0,00 · Доход 0,00"

    parts = []
    for direction, title in (
        ("borrowed", "Расход"),
        ("issued", "Доход"),
    ):
        part = df[df.get("loan_direction", "unknown").astype(str).eq(direction)]
        totals = _totals(part)
        parts.append(f"{title} {_format_totals(totals, short=short)}")
    return " · ".join(parts)


def _single_currency(values: dict[str, float]) -> tuple[float, str | None]:
    non_zero = {
        currency: amount
        for currency, amount in values.items()
        if abs(amount) > 0.005
    }

    source = non_zero or values

    if len(source) != 1:
        return 0.0, None

    currency, amount = next(iter(source.items()))
    return float(amount), currency


# =====================================================================
# DATA
# =====================================================================

def get_daily_interest_accruals(target_dates: list[date]) -> pd.DataFrame:
    """
    Фактическое начисление процентов из gl.borrowings_tp.

    interest_accrued хранится в копейках, поэтому / 100.

    Используем psycopg cursor, а не pd.read_sql_query:
    так здесь не будет pandas warning про SQLAlchemy.
    """
    if not target_dates:
        return pd.DataFrame()

    query = """
        SELECT
            t.date_from::date AS accrual_date,
            t.contract_id,

            c.number AS contract_number,
            c.date::date AS contract_date,
            cp.name AS counterparty_name,
            COALESCE(c.currency, '') AS currency,
            CASE
                WHEN af.fn_id = 6 THEN 'borrowed'
                WHEN af.fn_id = 9 THEN 'issued'
                ELSE 'unknown'
            END AS loan_direction,

            SUM(
                COALESCE(t.interest_accrued, 0)
            ) / 100.0 AS interest_accrued,

            MAX(
                COALESCE(t.rate, 0)
            ) AS rate

        FROM gl.borrowings_tp t

        LEFT JOIN public.contracts_contracts c
            ON c.id = t.contract_id

        LEFT JOIN public.counterparties_counterparty cp
            ON cp.id = c.cp_id

        LEFT JOIN LATERAL (
                SELECT
                    CASE
                        WHEN COUNT(DISTINCT aa.fn_id) = 1
                            THEN MIN(aa.fn_id)
                        ELSE NULL
                    END AS fn_id
                FROM gl.accurals_args aa
                WHERE aa.contract_id = t.contract_id
            ) af ON TRUE

        WHERE
            t.date_from::date = ANY(%s::date[])

        GROUP BY
            t.date_from::date,
            t.contract_id,
            c.number,
            c.date::date,
            cp.name,
            c.currency,
            af.fn_id

        ORDER BY
            t.date_from::date DESC,
            interest_accrued DESC,
            cp.name NULLS LAST,
            c.number NULLS LAST
    """

    with get_db_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(query, (target_dates,))
            rows = cur.fetchall()

    if not rows:
        return pd.DataFrame(
            columns=[
                "accrual_date",
                "contract_id",
                "contract_number",
                "contract_date",
                "counterparty_name",
                "currency",
                "interest_accrued",
                "rate",
                "loan_direction",
            ]
        )

    df = pd.DataFrame(rows)

    df["accrual_date"] = pd.to_datetime(
        df["accrual_date"],
        errors="coerce",
    )
    df["contract_date"] = pd.to_datetime(
        df["contract_date"],
        errors="coerce",
    )
    df["interest_accrued"] = pd.to_numeric(
        df["interest_accrued"],
        errors="coerce",
    ).fillna(0.0)
    df["rate"] = pd.to_numeric(
        df["rate"],
        errors="coerce",
    ).fillna(0.0)

    return df


def get_daily_interest_dataset(report_date: str | date) -> dict:
    current_date = _as_date(report_date) or date.today()

    yesterday = current_date - relativedelta(days=1)
    month_ago = current_date - relativedelta(months=1)
    year_ago = current_date - relativedelta(years=1)

    df = get_daily_interest_accruals(
        [
            current_date,
            yesterday,
            month_ago,
            year_ago,
        ]
    )

    def take(target: date) -> pd.DataFrame:
        if df.empty:
            return df.copy()

        return df[
            df["accrual_date"].dt.date == target
        ].copy()

    return {
        "report_date": current_date,
        "yesterday_date": yesterday,
        "month_date": month_ago,
        "year_date": year_ago,

        "today": take(current_date),
        "yesterday": take(yesterday),
        "month": take(month_ago),
        "year": take(year_ago),
    }


# =====================================================================
# HEADER INDICATOR
# =====================================================================

def build_daily_interest_indicator():
    """
    Маленький показатель для шапки.
    По клику открывается модалка.
    """
    return dmc.UnstyledButton(
        id=DAILY_INTEREST_BUTTON_ID,

        style={
            "height": "34px",
            "display": "flex",
            "alignItems": "center",
            "gap": "7px",
            "padding": "0 9px",
            "backgroundColor": "#FFFFFF",
            "border": f"1px solid {COLORS['border']}",
            "cursor": "pointer",
        },

        children=[
            DashIconify(
                icon="solar:percent-circle-linear",
                width=16,
                color=COLORS.get("green", "#15803D"),
            ),

            html.Div(
                style={
                    "display": "flex",
                    "flexDirection": "column",
                    "alignItems": "flex-start",
                },
                children=[
                    html.Div(
                        "Проценты за день: расход / доход",
                        style={
                            "fontSize": "9px",
                            "lineHeight": "10px",
                            "color": COLORS["muted"],
                        },
                    ),
                    html.Div(
                        id=DAILY_INTEREST_VALUE_ID,
                        children="—",
                        style={
                            "marginTop": "2px",
                            "fontSize": "11px",
                            "lineHeight": "12px",
                            "fontWeight": 700,
                            "color": COLORS["text"],
                            "fontVariantNumeric": "tabular-nums",
                        },
                    ),
                ],
            ),

            html.Div(
                id=DAILY_INTEREST_CHANGE_ID,
                children="",
                style={
                    "fontSize": "9px",
                    "fontWeight": 700,
                    "whiteSpace": "nowrap",
                },
            ),

            DashIconify(
                icon="solar:info-circle-linear",
                width=13,
                color=COLORS["muted"],
            ),
        ],
    )


# =====================================================================
# MODAL UI
# =====================================================================

def _summary_card(
    *,
    title: str,
    value_id: str,
    comparison_id: str | None = None,
):
    children = [
        html.Div(
            title,
            style={
                "fontSize": "9px",
                "color": COLORS["muted"],
            },
        ),
        html.Div(
            id=value_id,
            children="—",
            style={
                "marginTop": "4px",
                "fontSize": "17px",
                "fontWeight": 700,
                "color": COLORS["text"],
                "fontVariantNumeric": "tabular-nums",
            },
        ),
    ]

    if comparison_id:
        children.append(
            html.Div(
                id=comparison_id,
                children="",
                style={"marginTop": "5px"},
            )
        )

    return html.Div(
        style={
            "padding": "9px 10px",
            "backgroundColor": "#FFFFFF",
            "border": f"1px solid {COLORS['border']}",
        },
        children=children,
    )


def _comparison_view(
    current: float,
    previous: float,
    currency: str,
):
    comparison = _compare(
        current,
        previous,
    )

    direction = comparison["direction"]
    color = _direction_color(direction)
    delta = comparison["delta"]
    percent = comparison["percent"]

    sign = "+" if delta > 0 else ""

    return html.Div(
        style={
            "display": "flex",
            "alignItems": "center",
            "gap": "4px",
        },
        children=[
            DashIconify(
                icon=_direction_icon(direction),
                width=12,
                color=color,
            ),
            html.Span(
                (
                    f"{sign}{_money_short(delta)} "
                    f"{currency}"
                ).strip(),
                style={
                    "fontSize": "10px",
                    "fontWeight": 700,
                    "color": color,
                },
            ),
            html.Span(
                (
                    f"({_pct(percent)})"
                    if percent is not None
                    else "(новая база)"
                ),
                style={
                    "fontSize": "9px",
                    "color": COLORS["muted"],
                },
            ),
        ],
    )


def _detail_row(row: dict):
    counterparty = (
        row.get("counterparty_name")
        or "Контрагент не указан"
    )
    number = (
        row.get("contract_number")
        or "б/н"
    )

    contract_date = pd.to_datetime(
        row.get("contract_date"),
        errors="coerce",
    )

    date_text = (
        contract_date.strftime("%d.%m.%Y")
        if pd.notna(contract_date)
        else "без даты"
    )

    amount = _float(
        row.get("interest_accrued")
    )
    rate = _float(
        row.get("rate")
    )
    currency = (
        row.get("currency")
        or ""
    )
    direction_label = (
        "Процентный расход"
        if row.get("loan_direction") == "borrowed"
        else (
            "Процентный доход"
            if row.get("loan_direction") == "issued"
            else "Направление не определено"
        )
    )

    return html.Div(
        style={
            "display": "grid",
            "gridTemplateColumns": "minmax(260px, 1fr) 170px 100px",
            "gap": "12px",
            "alignItems": "center",
            "padding": "8px 12px",
            "borderBottom": f"1px solid {COLORS['border']}",
        },

        children=[
            html.Div(
                children=[
                    html.Div(
                        counterparty,
                        style={
                            "fontSize": "11px",
                            "fontWeight": 700,
                            "color": COLORS["text"],
                        },
                    ),
                    html.Div(
                        (
                            f"{direction_label} · "
                            f"договор № {number} от {date_text}"
                        ),
                        style={
                            "marginTop": "1px",
                            "fontSize": "9px",
                            "color": COLORS["muted"],
                        },
                    ),
                ],
            ),

            html.Div(
                f"{_money(amount)} {currency}".strip(),
                style={
                    "fontSize": "11px",
                    "fontWeight": 700,
                    "textAlign": "right",
                    "fontVariantNumeric": "tabular-nums",
                },
            ),

            html.Div(
                f"{rate:.2f}%".replace(".", ","),
                style={
                    "fontSize": "10px",
                    "textAlign": "right",
                    "color": COLORS["muted"],
                },
            ),
        ],
    )


def build_daily_interest_modal():
    return dmc.Modal(
        id=DAILY_INTEREST_MODAL_ID,

        opened=False,
        centered=True,
        size="80%",
        radius=0,
        padding=0,
        withCloseButton=False,

        styles={
            "content": {
                "maxWidth": "1200px",
            },
            "body": {
                "padding": "0",
            },
            "header": {
                "display": "none",
            },
        },

        children=[
            # HEADER
            html.Div(
                style={
                    "display": "flex",
                    "alignItems": "center",
                    "justifyContent": "space-between",
                    "gap": "12px",
                    "padding": "11px 14px",
                    "borderBottom": f"1px solid {COLORS['border']}",
                },

                children=[
                    html.Div(
                        style={
                            "display": "flex",
                            "alignItems": "center",
                            "gap": "8px",
                        },
                        children=[
                            DashIconify(
                                icon="solar:percent-circle-linear",
                                width=18,
                                color=COLORS.get("green", "#15803D"),
                            ),

                            html.Div(
                                children=[
                                    html.Div(
                                        "Процентная нагрузка за день",
                                        style={
                                            "fontSize": "15px",
                                            "fontWeight": 700,
                                            "color": COLORS["text"],
                                        },
                                    ),
                                    html.Div(
                                        id=DAILY_INTEREST_MODAL_DATE_ID,
                                        children="",
                                        style={
                                            "marginTop": "2px",
                                            "fontSize": "9px",
                                            "color": COLORS["muted"],
                                        },
                                    ),
                                ],
                            ),
                        ],
                    ),

                    dmc.ActionIcon(
                        id=DAILY_INTEREST_MODAL_CLOSE_ID,
                        variant="subtle",
                        color="gray",
                        radius=0,
                        size="lg",
                        children=DashIconify(
                            icon="solar:close-circle-linear",
                            width=19,
                        ),
                    ),
                ],
            ),

            # SUMMARY
            html.Div(
                style={
                    "display": "grid",
                    "gridTemplateColumns": "repeat(4, minmax(0, 1fr))",
                    "gap": "7px",
                    "padding": "10px 14px",
                },

                children=[
                    _summary_card(
                        title="Текущий день",
                        value_id=DAILY_INTEREST_TODAY_ID,
                    ),

                    _summary_card(
                        title="Вчера",
                        value_id=DAILY_INTEREST_YESTERDAY_ID,
                        comparison_id=DAILY_INTEREST_VS_YESTERDAY_ID,
                    ),

                    _summary_card(
                        title="Месяц назад",
                        value_id=DAILY_INTEREST_MONTH_ID,
                        comparison_id=DAILY_INTEREST_VS_MONTH_ID,
                    ),

                    _summary_card(
                        title="Год назад",
                        value_id=DAILY_INTEREST_YEAR_ID,
                        comparison_id=DAILY_INTEREST_VS_YEAR_ID,
                    ),
                ],
            ),

            # TABLE HEADER
            html.Div(
                style={
                    "display": "grid",
                    "gridTemplateColumns": "minmax(260px, 1fr) 170px 100px",
                    "gap": "12px",
                    "padding": "7px 12px",
                    "backgroundColor": "#F8FAF9",
                    "borderTop": f"1px solid {COLORS['border']}",
                    "borderBottom": f"1px solid {COLORS['border']}",
                },

                children=[
                    html.Div(
                        "Договор",
                        style={
                            "fontSize": "9px",
                            "fontWeight": 700,
                            "color": COLORS["muted"],
                        },
                    ),
                    html.Div(
                        "Расход / доход за день",
                        style={
                            "fontSize": "9px",
                            "fontWeight": 700,
                            "textAlign": "right",
                            "color": COLORS["muted"],
                        },
                    ),
                    html.Div(
                        "Ставка",
                        style={
                            "fontSize": "9px",
                            "fontWeight": 700,
                            "textAlign": "right",
                            "color": COLORS["muted"],
                        },
                    ),
                ],
            ),

            # DETAILS
            html.Div(
                id=DAILY_INTEREST_DETAILS_ID,
                children=[],
                style={
                    "maxHeight": "400px",
                    "overflowY": "auto",
                    "overflowX": "hidden",
                },
            ),
        ],
    )


# =====================================================================
# CALLBACKS
# =====================================================================

def register_daily_interest_callbacks(app):
    # ---------------------------------------------------------------
    # OPEN / CLOSE
    # Не используем dash.ctx из-за django_plotly_dash.
    # ---------------------------------------------------------------
    @app.callback(
        Output(
            DAILY_INTEREST_MODAL_ID,
            "opened",
        ),
        Input(
            DAILY_INTEREST_BUTTON_ID,
            "n_clicks",
        ),
        Input(
            DAILY_INTEREST_MODAL_CLOSE_ID,
            "n_clicks",
        ),
        State(
            DAILY_INTEREST_MODAL_ID,
            "opened",
        ),
        prevent_initial_call=True,
    )
    def toggle_daily_interest_modal(
        open_clicks,
        close_clicks,
        opened,
    ):
        return not bool(opened)

    # ---------------------------------------------------------------
    # DATA
    # ---------------------------------------------------------------
    @app.callback(
        Output(
            DAILY_INTEREST_VALUE_ID,
            "children",
        ),
        Output(
            DAILY_INTEREST_CHANGE_ID,
            "children",
        ),
        Output(
            DAILY_INTEREST_CHANGE_ID,
            "style",
        ),

        Output(
            DAILY_INTEREST_MODAL_DATE_ID,
            "children",
        ),

        Output(
            DAILY_INTEREST_TODAY_ID,
            "children",
        ),
        Output(
            DAILY_INTEREST_YESTERDAY_ID,
            "children",
        ),
        Output(
            DAILY_INTEREST_MONTH_ID,
            "children",
        ),
        Output(
            DAILY_INTEREST_YEAR_ID,
            "children",
        ),

        Output(
            DAILY_INTEREST_VS_YESTERDAY_ID,
            "children",
        ),
        Output(
            DAILY_INTEREST_VS_MONTH_ID,
            "children",
        ),
        Output(
            DAILY_INTEREST_VS_YEAR_ID,
            "children",
        ),

        Output(
            DAILY_INTEREST_DETAILS_ID,
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
    def update_daily_interest(
        _signal,
        report_date,
    ):
        base_change_style = {
            "fontSize": "9px",
            "fontWeight": 700,
            "whiteSpace": "nowrap",
        }

        if not report_date:
            return (
                "—",
                "",
                base_change_style,
                "",
                "—",
                "—",
                "—",
                "—",
                "",
                "",
                "",
                [],
            )

        data = get_daily_interest_dataset(
            str(report_date)[:10]
        )

        today_df = data["today"]
        yesterday_df = data["yesterday"]
        month_df = data["month"]
        year_df = data["year"]

        today_totals = _totals(today_df)
        yesterday_totals = _totals(yesterday_df)
        month_totals = _totals(month_df)
        year_totals = _totals(year_df)

        today_value, currency = _single_currency(
            today_totals
        )

        # -----------------------------------------------------------
        # Маленький индикатор
        # -----------------------------------------------------------
        if currency:
            indicator_value = (
                f"{_money_short(today_value)} "
                f"{currency}"
            ).strip()

            yesterday_value = float(
                yesterday_totals.get(
                    currency,
                    0.0,
                )
            )

            comp = _compare(
                today_value,
                yesterday_value,
            )

            indicator_change = _pct(
                comp["percent"]
            )

            indicator_style = {
                **base_change_style,
                "color": _direction_color(
                    comp["direction"]
                ),
            }

        elif len(today_totals) > 1:
            indicator_value = (
                f"{len(today_totals)} валюты"
            )
            indicator_change = ""
            indicator_style = {
                **base_change_style,
                "color": COLORS["muted"],
            }

        else:
            indicator_value = "0,00"
            indicator_change = ""
            indicator_style = {
                **base_change_style,
                "color": COLORS["muted"],
            }

        # -----------------------------------------------------------
        # Сравнения
        # Валюты между собой не складываем.
        # -----------------------------------------------------------
        if currency:
            current = float(
                today_totals.get(
                    currency,
                    0.0,
                )
            )

            vs_yesterday = _comparison_view(
                current,
                float(
                    yesterday_totals.get(
                        currency,
                        0.0,
                    )
                ),
                currency,
            )

            vs_month = _comparison_view(
                current,
                float(
                    month_totals.get(
                        currency,
                        0.0,
                    )
                ),
                currency,
            )

            vs_year = _comparison_view(
                current,
                float(
                    year_totals.get(
                        currency,
                        0.0,
                    )
                ),
                currency,
            )

        else:
            multi_note = html.Span(
                "Несколько валют — сравнение % не суммируется",
                style={
                    "fontSize": "9px",
                    "color": COLORS["muted"],
                },
            )

            vs_yesterday = multi_note
            vs_month = multi_note
            vs_year = multi_note

        # -----------------------------------------------------------
        # Детализация текущего дня
        # -----------------------------------------------------------
        details = []

        if not today_df.empty:
            work = today_df.sort_values(
                [
                    "currency",
                    "interest_accrued",
                    "counterparty_name",
                ],
                ascending=[
                    True,
                    False,
                    True,
                ],
            )

            details = [
                _detail_row(row)
                for row in work.to_dict("records")
                if abs(
                    _float(
                        row.get(
                            "interest_accrued"
                        )
                    )
                ) > 0.005
            ]

        if not details:
            details = [
                html.Div(
                    "За выбранный день начислений процентов нет",
                    style={
                        "padding": "22px",
                        "fontSize": "11px",
                        "textAlign": "center",
                        "color": COLORS["muted"],
                    },
                )
            ]

        report = data["report_date"]
        yesterday = data["yesterday_date"]
        month_date = data["month_date"]
        year_date = data["year_date"]

        modal_date = (
            f"{report.strftime('%d.%m.%Y')} · "
            f"вчера {yesterday.strftime('%d.%m.%Y')} · "
            f"месяц назад {month_date.strftime('%d.%m.%Y')} · "
            f"год назад {year_date.strftime('%d.%m.%Y')}"
        )

        # Расход по полученным и доход по выданным займам показываем
        # раздельно. Процент изменения для их общей суммы не имеет
        # экономического смысла, поэтому в общем индикаторе его убираем.
        indicator_value = _direction_totals_text(
            today_df,
            short=True,
        )
        indicator_change = ""
        indicator_style = {
            **base_change_style,
            "color": COLORS["muted"],
        }

        direction_note = html.Span(
            "Расход и доход показаны раздельно",
            style={
                "fontSize": "9px",
                "color": COLORS["muted"],
            },
        )
        vs_yesterday = direction_note
        vs_month = direction_note
        vs_year = direction_note

        return (
            indicator_value,
            indicator_change,
            indicator_style,

            modal_date,

            _direction_totals_text(today_df),
            _direction_totals_text(yesterday_df),
            _direction_totals_text(month_df),
            _direction_totals_text(year_df),

            vs_yesterday,
            vs_month,
            vs_year,

            details,
        )

