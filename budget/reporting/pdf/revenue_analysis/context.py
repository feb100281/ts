# # budget/reporting/pdf/revenue_analysis/context.py
# from budget.reporting.pdf.revenue_analysis.service import (
#     get_revenue_analysis,
#     format_money_compact,
#     format_money_full,
# )



# def _get_weekday_ru(weekday: int) -> str:
#     """Возвращает название дня недели на русском"""
#     days = ["ПН", "ВТ", "СР", "ЧТ", "ПТ", "СБ", "ВС"]
#     return days[weekday] if 0 <= weekday < 7 else "—"


# def build_revenue_analysis_context(version, report_date=None):
#     """Строит контекст для PDF отчета по анализу выручки"""
#     data = get_revenue_analysis(version, report_date)
    
#     if not data or not data.get("semi_analysis"):
#         return {"revenue_analysis": None}
    
#     # Форматируем полугодовые данные
#     semi_analysis = []
#     for s in data["semi_analysis"]:
#         semi_analysis.append({
#             **s,
#             "plan_fmt": format_money_full(s["plan"]),
#             "fact_fmt": format_money_full(s["fact"]),
#             "remaining_fmt": format_money_full(s["remaining"]),
#             "overachievement_fmt": format_money_full(s["overachievement"]),
#             "current_daily_rate_fmt": format_money_compact(s["current_daily_rate"]),
#             "required_daily_rate_fmt": format_money_compact(s["required_daily_rate"]),
#             "gap_daily_rate_fmt": format_money_compact(s["gap_daily_rate"]),
#             "gap_total_fmt": format_money_full(s["gap_total"]),
#             "projected_end_fmt": format_money_full(s["projected_end"]),
#         })
    
#     # Форматируем дневные данные
#     daily_analysis = data.get("daily_analysis", {})
#     last_10_days_formatted = []
    
#     for day in daily_analysis.get("last_10_days", []):
#         # Используем транзакции как proxy для quantity
#         sales_transactions = day.get("sales_transactions", 0)
#         returns_transactions = day.get("returns_transactions", 0)
#         net_transactions = sales_transactions - returns_transactions
        
#         # Рассчитываем средний чек (avg_price)
#         net_amount = day.get("net_amount", 0)
#         avg_price = net_amount / net_transactions if net_transactions > 0 else 0
        
#         last_10_days_formatted.append({
#             "date": day["date"],
#             "date_str": day["date"].strftime("%d.%m.%Y"),
#             "weekday": _get_weekday_ru(day["date"].weekday()),
#             "sales_amount": day.get("sales_amount", 0),
#             "sales_amount_fmt": format_money_full(day.get("sales_amount", 0)),
#             "returns_amount": day.get("returns_amount", 0),
#             "returns_amount_fmt": format_money_full(day.get("returns_amount", 0)),
#             "net_amount": net_amount,
#             "net_amount_fmt": format_money_full(net_amount),
#             "sales_qty": sales_transactions,  # используем транзакции
#             "returns_qty": returns_transactions,  # используем транзакции
#             "net_qty": net_transactions,
#             "transactions_count": sales_transactions,
#             "avg_price": avg_price,
#             "avg_price_fmt": format_money_full(avg_price),
#             "has_sales": net_amount > 0,
#         })
    
#     return {
#         "revenue_analysis": {
#             "report_date_str": data["report_date_str"],
#             "semi_analysis": semi_analysis,
#             "totals": {
#                 "plan_fmt": format_money_full(data["totals"]["plan"]),
#                 "fact_fmt": format_money_full(data["totals"]["fact"]),
#                 "delta_fmt": format_money_full(abs(data["totals"]["delta"])),
#                 "exec_pct": data["totals"]["exec_pct"],
#                 "is_over_performed": data["totals"]["delta"] >= 0,
#             },
#             "daily_analysis": {
#                     "avg_daily_rate": daily_analysis.get("avg_daily_rate", 0),
#                     "avg_daily_rate_fmt": format_money_full(daily_analysis.get("avg_daily_rate", 0)),
#                     "total_amount": daily_analysis.get("total_amount", 0),
#                     "total_amount_fmt": format_money_full(daily_analysis.get("total_amount", 0)),
#                     "total_sales": daily_analysis.get("total_sales", 0),
#                     "total_sales_fmt": format_money_full(daily_analysis.get("total_sales", 0)),
#                     "total_returns": daily_analysis.get("total_returns", 0),
#                     "total_returns_fmt": format_money_full(daily_analysis.get("total_returns", 0)),
#                     "days_with_sales": daily_analysis.get("days_with_sales", 0),
#                     "days_count": daily_analysis.get("days_count", 0),
#                     "last_10_days": last_10_days_formatted,
#                 }
#         }
#     }


# budget/reporting/pdf/revenue_analysis/context.py
from budget.reporting.pdf.revenue_analysis.service import (
    get_revenue_analysis,
    format_money_compact,
    format_money_full,
)
from budget.reporting.pdf.revenue_analysis.charts import generate_revenue_chart_svg


def _get_weekday_ru(weekday: int) -> str:
    days = ["ПН", "ВТ", "СР", "ЧТ", "ПТ", "СБ", "ВС"]
    return days[weekday] if 0 <= weekday < 7 else "—"


def build_revenue_analysis_context(version, report_date=None):
    """Строит контекст для PDF отчета по анализу выручки"""
    data = get_revenue_analysis(version, report_date)
    
    if not data or not data.get("semi_analysis"):
        return {"revenue_analysis": None}
    
    # Находим текущее полугодие для графика
    current_semi = None
    for s in data["semi_analysis"]:
        if s.get("is_current") and not s.get("is_completed"):
            current_semi = s
            break
    
    # Форматируем полугодовые данные
    semi_analysis = []
    for s in data["semi_analysis"]:
        semi_analysis.append({
            **s,
            "plan_fmt": format_money_full(s["plan"]),
            "fact_fmt": format_money_full(s["fact"]),
            "remaining_fmt": format_money_full(s["remaining"]),
            "overachievement_fmt": format_money_full(s["overachievement"]),
            "current_daily_rate_fmt": format_money_compact(s["current_daily_rate"]),
            "required_daily_rate_fmt": format_money_compact(s["required_daily_rate"]),
            "gap_daily_rate_fmt": format_money_compact(s["gap_daily_rate"]),
            "gap_total_fmt": format_money_full(s["gap_total"]),
            "projected_end_fmt": format_money_full(s["projected_end"]),
        })
    
    # Форматируем дневные данные
    daily_analysis = data.get("daily_analysis", {})
    last_10_days_formatted = []
    
    for day in daily_analysis.get("last_10_days", []):
        sales_transactions = day.get("sales_transactions", 0)
        returns_transactions = day.get("returns_transactions", 0)
        net_transactions = sales_transactions - returns_transactions
        net_amount = day.get("net_amount", 0)
        avg_price = net_amount / net_transactions if net_transactions > 0 else 0
        
        last_10_days_formatted.append({
            "date": day["date"],
            "date_str": day["date"].strftime("%d.%m.%Y"),
            "weekday": _get_weekday_ru(day["date"].weekday()),
            "sales_amount": day.get("sales_amount", 0),
            "sales_amount_fmt": format_money_full(day.get("sales_amount", 0)),
            "returns_amount": day.get("returns_amount", 0),
            "returns_amount_fmt": format_money_full(day.get("returns_amount", 0)),
            "net_amount": net_amount,
            "net_amount_fmt": format_money_full(net_amount),
            "sales_qty": sales_transactions,
            "returns_qty": returns_transactions,
            "net_qty": net_transactions,
            "transactions_count": sales_transactions,
            "avg_price": avg_price,
            "avg_price_fmt": format_money_full(avg_price),
            "has_sales": net_amount > 0,
        })
    
    # Генерируем SVG график
    chart_svg = None
    if last_10_days_formatted:
        try:
            chart_svg = generate_revenue_chart_svg(
                last_10_days_formatted,
                current_semi,
                data["report_date"]
            )
        except Exception as e:
            print(f"Ошибка генерации графика: {e}")
            chart_svg = None
    
    return {
        "revenue_analysis": {
            "report_date_str": data["report_date_str"],
            "semi_analysis": semi_analysis,
            "chart_svg": chart_svg,  # добавляем SVG график
            "totals": {
                "plan_fmt": format_money_full(data["totals"]["plan"]),
                "fact_fmt": format_money_full(data["totals"]["fact"]),
                "delta_fmt": format_money_full(abs(data["totals"]["delta"])),
                "exec_pct": data["totals"]["exec_pct"],
                "is_over_performed": data["totals"]["delta"] >= 0,
            },
            "daily_analysis": {
                "avg_daily_rate": daily_analysis.get("avg_daily_rate", 0),
                "avg_daily_rate_fmt": format_money_full(daily_analysis.get("avg_daily_rate", 0)),
                "total_amount": daily_analysis.get("total_amount", 0),
                "total_amount_fmt": format_money_full(daily_analysis.get("total_amount", 0)),
                "total_sales": daily_analysis.get("total_sales", 0),
                "total_sales_fmt": format_money_full(daily_analysis.get("total_sales", 0)),
                "total_returns": daily_analysis.get("total_returns", 0),
                "total_returns_fmt": format_money_full(daily_analysis.get("total_returns", 0)),
                "days_with_sales": daily_analysis.get("days_with_sales", 0),
                "days_count": daily_analysis.get("days_count", 0),
                "last_10_days": last_10_days_formatted,
            }
        }
    }