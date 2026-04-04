# # budget/reporting/pdf/budget_data.py
# from budget.reporting.excel.data_loader import load_budget_export_data


# def _format_money(value):
#     if value is None:
#         return "—"
#     return f"{value:,.2f}".replace(",", " ")


# def _format_percent(value):
#     if value is None:
#         return "—"
#     return f"{value:.1f}%"


# def build_budget_pdf_context(version):
#     export_data = load_budget_export_data(version)

#     version_data = export_data["version"]
#     pivot = export_data["gl_pivot"]
#     revenue_param = export_data.get("revenue_param") or {}

#     scenario_raw = revenue_param.get("scenario", "base")
#     scenario_map = {
#         "base": "Базовый",
#         "optimistic": "Оптимистичный",
#         "conservative": "Консервативный",
#     }
#     scenario = scenario_map.get(str(scenario_raw).lower(), str(scenario_raw))

#     summary_plan = float(pivot.get("grand_plan_sum") or 0)
#     summary_fact = float(pivot.get("grand_fact_sum") or 0)
#     summary_delta = float(pivot.get("grand_delta_sum") or 0)
#     summary_execution = (summary_fact / summary_plan * 100) if abs(summary_plan) > 0.0001 else None

#     monthly_rows = []
#     for month in pivot.get("months", []):
#         plan = float(pivot["grand_plan_total"].get(month, 0) or 0)
#         fact = float(pivot["grand_fact_total"].get(month, 0) or 0)
#         delta = float(pivot["grand_delta_total"].get(month, 0) or 0)
#         execution = (fact / plan * 100) if abs(plan) > 0.0001 else None

#         monthly_rows.append({
#             "month": month,
#             "plan": _format_money(plan),
#             "fact": _format_money(fact),
#             "delta": _format_money(delta),
#             "execution": _format_percent(execution),
#             "delta_class": "negative" if delta < 0 else "positive" if delta > 0 else "",
#         })

#     detail_rows = []
#     for row in pivot.get("rows", []):
#         if row["row_type"] not in ("activity", "operation", "item"):
#             continue

#         level = int(row.get("level", 0))
#         plan_total = float(row.get("plan_total", 0) or 0)
#         fact_total = float(row.get("fact_total", 0) or 0)
#         delta_total = float(row.get("delta_total", 0) or 0)
#         execution_total = (fact_total / plan_total * 100) if abs(plan_total) > 0.0001 else None

#         detail_rows.append({
#             "label": row.get("label", "—"),
#             "level": level,
#             "row_type": row.get("row_type", ""),
#             "indent_px": 8 + level * 18,
#             "plan_total": _format_money(plan_total),
#             "fact_total": _format_money(fact_total),
#             "delta_total": _format_money(delta_total),
#             "execution_total": _format_percent(execution_total),
#             "delta_class": "negative" if delta_total < 0 else "positive" if delta_total > 0 else "",
#         })

#     comment_text = (
#         f'За период бюджет сформирован на сумму {_format_money(summary_plan)}, '
#         f'фактическое исполнение составило {_format_money(summary_fact)}, '
#         f'отклонение — {_format_money(summary_delta)}, '
#         f'исполнение бюджета — {_format_percent(summary_execution)}.'
#     )

#     return {
#         "title": "Справка по исполнению бюджета",
#         "subtitle": (
#             f'Версия бюджета: {version_data["number"]} | '
#             f'Период: {version_data["date_from"]:%d.%m.%Y} — {version_data["date_to"]:%d.%m.%Y} | '
#             f'Сценарий: {scenario}'
#         ),
#         "generated_at": version_data["date_to"].strftime("%d.%m.%Y"),
#         "summary": {
#             "plan_total": _format_money(summary_plan),
#             "fact_total": _format_money(summary_fact),
#             "delta_total": _format_money(summary_delta),
#             "execution_total": _format_percent(summary_execution),
#             "delta_class": "negative" if summary_delta < 0 else "positive" if summary_delta > 0 else "",
#         },
#         "monthly_rows": monthly_rows,
#         "detail_rows": detail_rows,
#         "comment_text": comment_text,
#     }



# from budget.reporting.excel.data_loader import load_budget_export_data


# def _format_money(value):
#     if value is None:
#         return "—"
#     return f"{value:,.2f}".replace(",", " ")


# def _format_percent(value):
#     if value is None:
#         return "—"
#     return f"{value:.1f}%"


# def _get_scenario_label(revenue_param):
#     scenario_raw = (revenue_param or {}).get("scenario", "base")
#     scenario_map = {
#         "base": "Базовый",
#         "optimistic": "Оптимистичный",
#         "conservative": "Консервативный",
#     }
#     return scenario_map.get(str(scenario_raw).lower(), str(scenario_raw))


# def _select_detail_month(pivot):
#     months = pivot.get("months", [])

#     if not months:
#         return None

#     # Берем последний месяц, где есть ненулевой факт
#     for month in reversed(months):
#         fact_value = float(pivot.get("grand_fact_total", {}).get(month, 0) or 0)
#         if abs(fact_value) > 0.0001:
#             return month

#     # Если факта нигде нет — берем последний месяц бюджета
#     return months[-1]


# def build_budget_pdf_context(version):
#     export_data = load_budget_export_data(version)

#     version_data = export_data["version"]
#     pivot = export_data["gl_pivot"]
#     revenue_param = export_data.get("revenue_param") or {}

#     scenario = _get_scenario_label(revenue_param)

#     # ---------------------------
#     # SUMMARY: за весь период бюджета
#     # ---------------------------
#     summary_plan = float(pivot.get("grand_plan_sum") or 0)
#     summary_fact = float(pivot.get("grand_fact_sum") or 0)
#     summary_delta = float(pivot.get("grand_delta_sum") or 0)
#     summary_execution = (
#         (summary_fact / summary_plan) * 100
#         if abs(summary_plan) > 0.0001
#         else None
#     )

#     # ---------------------------
#     # Итоги по месяцам: за весь период
#     # ---------------------------
#     monthly_rows = []
#     for month in pivot.get("months", []):
#         plan = float(pivot.get("grand_plan_total", {}).get(month, 0) or 0)
#         fact = float(pivot.get("grand_fact_total", {}).get(month, 0) or 0)
#         delta = float(pivot.get("grand_delta_total", {}).get(month, 0) or 0)
#         execution = (fact / plan * 100) if abs(plan) > 0.0001 else None

#         monthly_rows.append({
#             "month": month,
#             "plan": _format_money(plan),
#             "fact": _format_money(fact),
#             "delta": _format_money(delta),
#             "execution": _format_percent(execution),
#             "delta_class": "negative" if delta < 0 else "positive" if delta > 0 else "",
#         })

#     # ---------------------------
#     # Структура бюджета: за выбранный месяц
#     # ---------------------------
#     detail_month = _select_detail_month(pivot)

#     detail_rows = []
#     for row in pivot.get("rows", []):
#         if row.get("row_type") not in ("activity", "operation", "item"):
#             continue

#         level = int(row.get("level", 0))

#         plan_value = float(row.get("plan_months", {}).get(detail_month, 0) or 0)
#         fact_value = float(row.get("fact_months", {}).get(detail_month, 0) or 0)
#         delta_value = float(row.get("delta_months", {}).get(detail_month, 0) or 0)
#         execution_value = (fact_value / plan_value * 100) if abs(plan_value) > 0.0001 else None

#         # Можно скрыть полностью пустые строки за месяц, чтобы PDF был чище
#         if abs(plan_value) <= 0.0001 and abs(fact_value) <= 0.0001 and abs(delta_value) <= 0.0001:
#             continue

#         detail_rows.append({
#             "label": row.get("label", "—"),
#             "level": level,
#             "row_type": row.get("row_type", ""),
#             "indent_px": 8 + level * 18,
#             "plan_total": _format_money(plan_value),
#             "fact_total": _format_money(fact_value),
#             "delta_total": _format_money(delta_value),
#             "execution_total": _format_percent(execution_value),
#             "delta_class": "negative" if delta_value < 0 else "positive" if delta_value > 0 else "",
#         })

#     if detail_month:
#         comment_text = (
#             f'За весь период бюджет сформирован на сумму {_format_money(summary_plan)}, '
#             f'фактическое исполнение составило {_format_money(summary_fact)}, '
#             f'отклонение — {_format_money(summary_delta)}, '
#             f'исполнение бюджета — {_format_percent(summary_execution)}. '
#             f'Структура бюджета в таблице ниже показана за {detail_month}.'
#         )
#     else:
#         comment_text = (
#             f'За весь период бюджет сформирован на сумму {_format_money(summary_plan)}, '
#             f'фактическое исполнение составило {_format_money(summary_fact)}, '
#             f'отклонение — {_format_money(summary_delta)}, '
#             f'исполнение бюджета — {_format_percent(summary_execution)}.'
#         )

#     return {
#         "title": "Справка по исполнению бюджета",
#         "subtitle": (
#             f'Версия бюджета: {version_data["number"]} | '
#             f'Период: {version_data["date_from"]:%d.%m.%Y} — {version_data["date_to"]:%d.%m.%Y} | '
#             f'Сценарий: {scenario}'
#         ),
#         "generated_at": version_data["date_to"].strftime("%d.%m.%Y"),
#         "summary": {
#             "plan_total": _format_money(summary_plan),
#             "fact_total": _format_money(summary_fact),
#             "delta_total": _format_money(summary_delta),
#             "execution_total": _format_percent(summary_execution),
#             "delta_class": "negative" if summary_delta < 0 else "positive" if summary_delta > 0 else "",
#         },
#         "monthly_rows": monthly_rows,
#         "detail_month": detail_month,
#         "detail_rows": detail_rows,
#         "comment_text": comment_text,
#     }




from budget.reporting.excel.data_loader import load_budget_export_data


def _format_money(value):
    if value is None:
        return "—"
    return f"{value:,.2f}".replace(",", " ")


def _format_percent(value):
    if value is None:
        return "—"
    return f"{value:.1f}%"


def _get_scenario_label(revenue_param):
    scenario_raw = (revenue_param or {}).get("scenario", "base")
    scenario_map = {
        "base": "Базовый",
        "optimistic": "Оптимистичный",
        "conservative": "Консервативный",
    }
    return scenario_map.get(str(scenario_raw).lower(), str(scenario_raw))


def _select_detail_month(pivot):
    months = pivot.get("months", [])

    if not months:
        return None

    for month in reversed(months):
        fact_value = float(pivot.get("grand_fact_total", {}).get(month, 0) or 0)
        if abs(fact_value) > 0.0001:
            return month

    return months[-1]


def _build_detail_rows_total(pivot):
    rows_out = []

    for row in pivot.get("rows", []):
        if row.get("row_type") not in ("activity", "operation", "item"):
            continue

        level = int(row.get("level", 0))

        plan_value = float(row.get("plan_total", 0) or 0)
        fact_value = float(row.get("fact_total", 0) or 0)
        delta_value = float(row.get("delta_total", 0) or 0)
        execution_value = (fact_value / plan_value * 100) if abs(plan_value) > 0.0001 else None

        if abs(plan_value) <= 0.0001 and abs(fact_value) <= 0.0001 and abs(delta_value) <= 0.0001:
            continue

        rows_out.append({
            "label": row.get("label", "—"),
            "level": level,
            "row_type": row.get("row_type", ""),
            "indent_px": 8 + level * 18,
            "plan_total": _format_money(plan_value),
            "fact_total": _format_money(fact_value),
            "delta_total": _format_money(delta_value),
            "execution_total": _format_percent(execution_value),
            "delta_class": "negative" if delta_value < 0 else "positive" if delta_value > 0 else "",
        })

    return rows_out


def _build_detail_rows_month(pivot, detail_month):
    rows_out = []

    if not detail_month:
        return rows_out

    for row in pivot.get("rows", []):
        if row.get("row_type") not in ("activity", "operation", "item"):
            continue

        level = int(row.get("level", 0))

        plan_value = float(row.get("plan_months", {}).get(detail_month, 0) or 0)
        fact_value = float(row.get("fact_months", {}).get(detail_month, 0) or 0)
        delta_value = float(row.get("delta_months", {}).get(detail_month, 0) or 0)
        execution_value = (fact_value / plan_value * 100) if abs(plan_value) > 0.0001 else None

        if abs(plan_value) <= 0.0001 and abs(fact_value) <= 0.0001 and abs(delta_value) <= 0.0001:
            continue

        rows_out.append({
            "label": row.get("label", "—"),
            "level": level,
            "row_type": row.get("row_type", ""),
            "indent_px": 8 + level * 18,
            "plan_total": _format_money(plan_value),
            "fact_total": _format_money(fact_value),
            "delta_total": _format_money(delta_value),
            "execution_total": _format_percent(execution_value),
            "delta_class": "negative" if delta_value < 0 else "positive" if delta_value > 0 else "",
        })

    return rows_out


def build_budget_pdf_context(version):
    export_data = load_budget_export_data(version)

    version_data = export_data["version"]
    pivot = export_data["gl_pivot"]
    revenue_param = export_data.get("revenue_param") or {}

    scenario = _get_scenario_label(revenue_param)

    # Summary за весь период
    summary_plan = float(pivot.get("grand_plan_sum") or 0)
    summary_fact = float(pivot.get("grand_fact_sum") or 0)
    summary_delta = float(pivot.get("grand_delta_sum") or 0)
    summary_execution = (
        (summary_fact / summary_plan) * 100
        if abs(summary_plan) > 0.0001
        else None
    )

    # Таблица по месяцам за весь период
    monthly_rows = []
    for month in pivot.get("months", []):
        plan = float(pivot.get("grand_plan_total", {}).get(month, 0) or 0)
        fact = float(pivot.get("grand_fact_total", {}).get(month, 0) or 0)
        delta = float(pivot.get("grand_delta_total", {}).get(month, 0) or 0)
        execution = (fact / plan * 100) if abs(plan) > 0.0001 else None

        monthly_rows.append({
            "month": month,
            "plan": _format_money(plan),
            "fact": _format_money(fact),
            "delta": _format_money(delta),
            "execution": _format_percent(execution),
            "delta_class": "negative" if delta < 0 else "positive" if delta > 0 else "",
        })

    # Структура за месяц
    detail_month = _select_detail_month(pivot)
    detail_rows_month = _build_detail_rows_month(pivot, detail_month)

    # Структура за весь период
    detail_rows_total = _build_detail_rows_total(pivot)

    if detail_month:
        comment_text = (
            f'За весь период бюджет сформирован на сумму {_format_money(summary_plan)}, '
            f'фактическое исполнение составило {_format_money(summary_fact)}, '
            f'отклонение — {_format_money(summary_delta)}, '
            f'исполнение бюджета — {_format_percent(summary_execution)}. '
            f'Ниже приведена структура бюджета за {detail_month} и за весь период.'
        )
    else:
        comment_text = (
            f'За весь период бюджет сформирован на сумму {_format_money(summary_plan)}, '
            f'фактическое исполнение составило {_format_money(summary_fact)}, '
            f'отклонение — {_format_money(summary_delta)}, '
            f'исполнение бюджета — {_format_percent(summary_execution)}.'
        )

    return {
        "title": "Справка по исполнению бюджета",
        "subtitle": (
            f'Версия бюджета: {version_data["number"]} | '
            f'Период: {version_data["date_from"]:%d.%m.%Y} — {version_data["date_to"]:%d.%m.%Y} | '
            f'Сценарий: {scenario}'
        ),
        "generated_at": version_data["date_to"].strftime("%d.%m.%Y"),
        "summary": {
            "plan_total": _format_money(summary_plan),
            "fact_total": _format_money(summary_fact),
            "delta_total": _format_money(summary_delta),
            "execution_total": _format_percent(summary_execution),
            "delta_class": "negative" if summary_delta < 0 else "positive" if summary_delta > 0 else "",
        },
        "monthly_rows": monthly_rows,
        "detail_month": detail_month,
        "detail_rows_month": detail_rows_month,
        "detail_rows_total": detail_rows_total,
        "comment_text": comment_text,
    }