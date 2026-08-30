# # budget/reporting/excel/data_loader.py
# from collections import defaultdict
# from django.db import connection



# def load_budget_export_data(version):
#     gl_rows = get_gl_rows(version.id)
#     fact_rows = get_fact_rows(version.date_from, version.date_to)

#     return {
#         "version": {
#             "id": version.id,
#             "number": version.number,
#             "budget_type": version.get_budget_type_display(),
#             "description": version.description,
#             "date_from": version.date_from,
#             "date_to": version.date_to,
#         },
#         "revenue_param": version.revenue_param or {},
#         "wb_costs_params": version.wb_costs_params or {},
#         "cf_params": version.cf_params or {},
#         "report": version.report or {},
#         "gl_rows": gl_rows,
#         "fact_rows": fact_rows,
#         "gl_pivot": build_gl_plan_fact_pivot(gl_rows, fact_rows),
#     }
    
    
    

# def get_gl_rows(version_id):
#     sql = """
#         SELECT
#             x.date_from,
#             (lv1.code::text || ' ' || lv1.name::text) AS activity,
#             (lv2.code::text || ' ' || lv2.name::text) AS operation,
#             (lv3.code::text || ' ' || lv3.name::text) AS item,
#             (i.code::text || ' ' || i.name::text) AS subitem,
#             x.dt,
#             x.cr,
#             x.amount,
#             x.description
#         FROM (
#             SELECT
#                 "date" AS date_from,
#                 round(dt / 100.0, 2) AS dt,
#                 round(cr / 100.0, 2) AS cr,
#                 round((dt - cr) / 100.0, 2) AS amount,
#                 subconto_id,
#                 description
#             FROM public.budget_gl
#             WHERE version_id = %s
#         ) x
#         JOIN corporate_cfitems i   ON i.id = x.subconto_id
#         JOIN corporate_cfitems lv3 ON lv3.id = i.parent_id
#         JOIN corporate_cfitems lv2 ON lv2.id = lv3.parent_id
#         JOIN corporate_cfitems lv1 ON lv1.id = lv2.parent_id
#         ORDER BY x.date_from, activity, operation, item, subitem
#     """

#     with connection.cursor() as cursor:
#         cursor.execute(sql, [version_id])
#         rows = cursor.fetchall()

#     result = []
#     for row in rows:
#         result.append({
#                 "date_from": row[0],
#                 "activity": row[1],
#                 "operation": row[2],
#                 "item": row[3],
#                 "subitem": row[4],
#                 "dt": float(row[5] or 0),
#                 "cr": float(row[6] or 0),
#                 "amount": float(row[7] or 0),
#                 "description": row[8],
#             })
#     return result





# def get_fact_rows(date_from, date_to):
#     sql = """
#         SELECT
#             x.date_from,
#             (lv1.code::text || ' ' || lv1.name::text) AS activity,
#             (lv2.code::text || ' ' || lv2.name::text) AS operation,
#             (lv3.code::text || ' ' || lv3.name::text) AS item,
#             (i.code::text || ' ' || i.name::text) AS subitem,
#             round(sum(x.amount), 2) AS amount
#         FROM public.cf_to_csv x
#         JOIN corporate_cfitems i   ON i.id = x.subconto_id
#         JOIN corporate_cfitems lv3 ON lv3.id = i.parent_id
#         JOIN corporate_cfitems lv2 ON lv2.id = lv3.parent_id
#         JOIN corporate_cfitems lv1 ON lv1.id = lv2.parent_id
#         WHERE x.date_from BETWEEN %s AND %s
#         GROUP BY
#             x.date_from,
#             lv1.code, lv1.name,
#             lv2.code, lv2.name,
#             lv3.code, lv3.name,
#             i.code, i.name
#         ORDER BY
#             x.date_from,
#             lv1.code, lv1.name,
#             lv2.code, lv2.name,
#             lv3.code, lv3.name,
#             i.code, i.name
#     """

#     with connection.cursor() as cursor:
#         cursor.execute(sql, [date_from, date_to])
#         rows = cursor.fetchall()

#     result = []
#     for row in rows:
#         result.append({
#             "date_from": row[0],
#             "activity": row[1],
#             "operation": row[2],
#             "item": row[3],
#             "subitem": row[4],
#             "amount": float(row[5] or 0),
#         })
#     return result





# def build_gl_plan_fact_pivot(gl_rows, fact_rows):
#     month_order = []
#     month_set = set()

#     month_map = {
#         1: "Янв",
#         2: "Фев",
#         3: "Мар",
#         4: "Апр",
#         5: "Май",
#         6: "Июн",
#         7: "Июл",
#         8: "Авг",
#         9: "Сен",
#         10: "Окт",
#         11: "Ноя",
#         12: "Дек",
#     }

#     tree = defaultdict(
#         lambda: {
#             "plan_months": defaultdict(float),
#             "fact_months": defaultdict(float),
#             "plan_total": 0.0,
#             "fact_total": 0.0,
#             "children": defaultdict(
#                 lambda: {
#                     "plan_months": defaultdict(float),
#                     "fact_months": defaultdict(float),
#                     "plan_total": 0.0,
#                     "fact_total": 0.0,
#                     "children": defaultdict(
#                         lambda: {
#                             "plan_months": defaultdict(float),
#                             "fact_months": defaultdict(float),
#                             "plan_total": 0.0,
#                             "fact_total": 0.0,
#                             "children": defaultdict(
#                                 lambda: {
#                                     "plan_months": defaultdict(float),
#                                     "fact_months": defaultdict(float),
#                                     "plan_total": 0.0,
#                                     "fact_total": 0.0,
#                                 }
#                             ),
#                         }
#                     ),
#                 }
#             ),
#         }
#     )

#     grand_plan_total = defaultdict(float)
#     grand_fact_total = defaultdict(float)

#     def month_label_from_date(dt):
#         return f'{month_map[dt.month]} {str(dt.year)[-2:]}'

#     # PLAN
#     for row in gl_rows:
#         dt = row["date_from"]
#         month_label = month_label_from_date(dt)

#         if month_label not in month_set:
#             month_set.add(month_label)
#             month_order.append(month_label)

#         activity = row["activity"] or "—"
#         operation = row["operation"] or "—"
#         item = row["item"] or "—"
#         subitem = row["subitem"] or "—"
#         amount = float(row["amount"] or 0)

#         tree[activity]["plan_months"][month_label] += amount
#         tree[activity]["plan_total"] += amount

#         tree[activity]["children"][operation]["plan_months"][month_label] += amount
#         tree[activity]["children"][operation]["plan_total"] += amount

#         tree[activity]["children"][operation]["children"][item]["plan_months"][month_label] += amount
#         tree[activity]["children"][operation]["children"][item]["plan_total"] += amount

#         tree[activity]["children"][operation]["children"][item]["children"][subitem]["plan_months"][month_label] += amount
#         tree[activity]["children"][operation]["children"][item]["children"][subitem]["plan_total"] += amount

#         grand_plan_total[month_label] += amount

#     # FACT
#     for row in fact_rows:
#         dt = row["date_from"]
#         month_label = month_label_from_date(dt)

#         if month_label not in month_set:
#             month_set.add(month_label)
#             month_order.append(month_label)

#         activity = row["activity"] or "—"
#         operation = row["operation"] or "—"
#         item = row["item"] or "—"
#         subitem = row["subitem"] or "—"
#         amount = float(row["amount"] or 0)

#         tree[activity]["fact_months"][month_label] += amount
#         tree[activity]["fact_total"] += amount

#         tree[activity]["children"][operation]["fact_months"][month_label] += amount
#         tree[activity]["children"][operation]["fact_total"] += amount

#         tree[activity]["children"][operation]["children"][item]["fact_months"][month_label] += amount
#         tree[activity]["children"][operation]["children"][item]["fact_total"] += amount

#         tree[activity]["children"][operation]["children"][item]["children"][subitem]["fact_months"][month_label] += amount
#         tree[activity]["children"][operation]["children"][item]["children"][subitem]["fact_total"] += amount

#         grand_fact_total[month_label] += amount

#     def is_non_zero(plan_value, fact_value):
#         return abs(float(plan_value or 0)) > 0.0001 or abs(float(fact_value or 0)) > 0.0001

#     pivot_rows = []
#     detail_sheets = []

#     activity_idx = 0

#     for activity in sorted(tree.keys()):
#         activity_node = tree[activity]
#         if not is_non_zero(activity_node["plan_total"], activity_node["fact_total"]):
#             continue

#         activity_idx += 1
#         operation_idx = 0

#         pivot_rows.append({
#             "level": 0,
#             "label": activity,
#             "plan_months": {m: activity_node["plan_months"].get(m, 0) for m in month_order},
#             "fact_months": {m: activity_node["fact_months"].get(m, 0) for m in month_order},
#             "delta_months": {
#                 m: activity_node["fact_months"].get(m, 0) - activity_node["plan_months"].get(m, 0)
#                 for m in month_order
#             },
#             "plan_total": activity_node["plan_total"],
#             "fact_total": activity_node["fact_total"],
#             "delta_total": activity_node["fact_total"] - activity_node["plan_total"],
#             "row_type": "activity",
#             "note": "",
#             "sheet_name": None,
#         })

#         for operation in sorted(activity_node["children"].keys()):
#             operation_node = activity_node["children"][operation]
#             if not is_non_zero(operation_node["plan_total"], operation_node["fact_total"]):
#                 continue

#             operation_idx += 1
#             item_idx = 0

#             pivot_rows.append({
#                 "level": 1,
#                 "label": operation,
#                 "plan_months": {m: operation_node["plan_months"].get(m, 0) for m in month_order},
#                 "fact_months": {m: operation_node["fact_months"].get(m, 0) for m in month_order},
#                 "delta_months": {
#                     m: operation_node["fact_months"].get(m, 0) - operation_node["plan_months"].get(m, 0)
#                     for m in month_order
#                 },
#                 "plan_total": operation_node["plan_total"],
#                 "fact_total": operation_node["fact_total"],
#                 "delta_total": operation_node["fact_total"] - operation_node["plan_total"],
#                 "row_type": "operation",
#                 "note": "",
#                 "sheet_name": None,
#             })

#             for item in sorted(operation_node["children"].keys()):
#                 item_node = operation_node["children"][item]
#                 if not is_non_zero(item_node["plan_total"], item_node["fact_total"]):
#                     continue

#                 item_idx += 1

#                 subitem_rows = []
#                 for subitem in sorted(item_node["children"].keys()):
#                     subitem_node = item_node["children"][subitem]
#                     if not is_non_zero(subitem_node["plan_total"], subitem_node["fact_total"]):
#                         continue

#                     subitem_rows.append({
#                         "label": subitem,
#                         "plan_months": {m: subitem_node["plan_months"].get(m, 0) for m in month_order},
#                         "fact_months": {m: subitem_node["fact_months"].get(m, 0) for m in month_order},
#                         "delta_months": {
#                             m: subitem_node["fact_months"].get(m, 0) - subitem_node["plan_months"].get(m, 0)
#                             for m in month_order
#                         },
#                         "plan_total": subitem_node["plan_total"],
#                         "fact_total": subitem_node["fact_total"],
#                         "delta_total": subitem_node["fact_total"] - subitem_node["plan_total"],
#                     })

#                 has_detail = len(subitem_rows) > 0
#                 note_code = f"{activity_idx}.{operation_idx}.{item_idx}" if has_detail else ""
#                 sheet_name = note_code if has_detail else None

#                 pivot_rows.append({
#                     "level": 2,
#                     "label": item,
#                     "plan_months": {m: item_node["plan_months"].get(m, 0) for m in month_order},
#                     "fact_months": {m: item_node["fact_months"].get(m, 0) for m in month_order},
#                     "delta_months": {
#                         m: item_node["fact_months"].get(m, 0) - item_node["plan_months"].get(m, 0)
#                         for m in month_order
#                     },
#                     "plan_total": item_node["plan_total"],
#                     "fact_total": item_node["fact_total"],
#                     "delta_total": item_node["fact_total"] - item_node["plan_total"],
#                     "row_type": "item",
#                     "note": note_code,
#                     "sheet_name": sheet_name,
#                 })

#                 if has_detail:
#                     detail_sheets.append({
#                         "note": note_code,
#                         "sheet_name": sheet_name,
#                         "activity": activity,
#                         "operation": operation,
#                         "item": item,
#                         "months": month_order,
#                         "rows": subitem_rows,
#                         "plan_total": item_node["plan_total"],
#                         "fact_total": item_node["fact_total"],
#                         "delta_total": item_node["fact_total"] - item_node["plan_total"],
#                         "total_plan_by_month": {m: item_node["plan_months"].get(m, 0) for m in month_order},
#                         "total_fact_by_month": {m: item_node["fact_months"].get(m, 0) for m in month_order},
#                         "total_delta_by_month": {
#                             m: item_node["fact_months"].get(m, 0) - item_node["plan_months"].get(m, 0)
#                             for m in month_order
#                         },
#                     })

#     return {
#         "months": month_order,
#         "rows": pivot_rows,
#         "grand_plan_total": {m: grand_plan_total.get(m, 0) for m in month_order},
#         "grand_fact_total": {m: grand_fact_total.get(m, 0) for m in month_order},
#         "grand_delta_total": {
#             m: grand_fact_total.get(m, 0) - grand_plan_total.get(m, 0)
#             for m in month_order
#         },
#         "grand_plan_sum": sum(grand_plan_total.values()),
#         "grand_fact_sum": sum(grand_fact_total.values()),
#         "grand_delta_sum": sum(grand_fact_total.values()) - sum(grand_plan_total.values()),
#         "detail_sheets": detail_sheets,
#     }







# def build_gl_pivot(gl_rows):
#     month_order = []
#     month_set = set()

#     month_map = {
#         1: "Янв",
#         2: "Фев",
#         3: "Мар",
#         4: "Апр",
#         5: "Май",
#         6: "Июн",
#         7: "Июл",
#         8: "Авг",
#         9: "Сен",
#         10: "Окт",
#         11: "Ноя",
#         12: "Дек",
#     }

#     tree = defaultdict(
#         lambda: {
#             "months": defaultdict(float),
#             "total": 0.0,
#             "children": defaultdict(
#                 lambda: {
#                     "months": defaultdict(float),
#                     "total": 0.0,
#                     "children": defaultdict(
#                         lambda: {
#                             "months": defaultdict(float),
#                             "total": 0.0,
#                             "children": defaultdict(
#                                 lambda: {
#                                     "months": defaultdict(float),
#                                     "total": 0.0,
#                                 }
#                             ),
#                         }
#                     ),
#                 }
#             ),
#         }
#     )

#     grand_total = defaultdict(float)

#     for row in gl_rows:
#         dt = row["date_from"]
#         month_label = f'{month_map[dt.month]} {str(dt.year)[-2:]}'

#         if month_label not in month_set:
#             month_set.add(month_label)
#             month_order.append(month_label)

#         activity = row["activity"] or "—"
#         operation = row["operation"] or "—"
#         item = row["item"] or "—"
#         subitem = row["subitem"] or "—"
#         amount = float(row["amount"] or 0)

#         tree[activity]["months"][month_label] += amount
#         tree[activity]["total"] += amount

#         tree[activity]["children"][operation]["months"][month_label] += amount
#         tree[activity]["children"][operation]["total"] += amount

#         tree[activity]["children"][operation]["children"][item]["months"][month_label] += amount
#         tree[activity]["children"][operation]["children"][item]["total"] += amount

#         tree[activity]["children"][operation]["children"][item]["children"][subitem]["months"][month_label] += amount
#         tree[activity]["children"][operation]["children"][item]["children"][subitem]["total"] += amount

#         grand_total[month_label] += amount

#     def is_non_zero(total_value):
#         return abs(float(total_value or 0)) > 0.0001

#     pivot_rows = []
#     detail_sheets = []

#     activity_idx = 0

#     for activity in sorted(tree.keys()):
#         activity_node = tree[activity]
#         if not is_non_zero(activity_node["total"]):
#             continue

#         activity_idx += 1
#         operation_idx = 0

#         pivot_rows.append({
#             "level": 0,
#             "label": activity,
#             "months": {m: activity_node["months"].get(m, 0) for m in month_order},
#             "total": activity_node["total"],
#             "row_type": "activity",
#             "note": "",
#             "sheet_name": None,
#         })

#         for operation in sorted(activity_node["children"].keys()):
#             operation_node = activity_node["children"][operation]
#             if not is_non_zero(operation_node["total"]):
#                 continue

#             operation_idx += 1
#             item_idx = 0

#             pivot_rows.append({
#                 "level": 1,
#                 "label": operation,
#                 "months": {m: operation_node["months"].get(m, 0) for m in month_order},
#                 "total": operation_node["total"],
#                 "row_type": "operation",
#                 "note": "",
#                 "sheet_name": None,
#             })

#             for item in sorted(operation_node["children"].keys()):
#                 item_node = operation_node["children"][item]
#                 if not is_non_zero(item_node["total"]):
#                     continue

#                 item_idx += 1
#                 note_code = f"{activity_idx}.{operation_idx}.{item_idx}"
#                 sheet_name = note_code

#                 pivot_rows.append({
#                     "level": 2,
#                     "label": item,
#                     "months": {m: item_node["months"].get(m, 0) for m in month_order},
#                     "total": item_node["total"],
#                     "row_type": "item",
#                     "note": note_code if item_node["children"] else "",
#                     "sheet_name": sheet_name if item_node["children"] else None,
#                 })

#                 subitem_rows = []
#                 for subitem in sorted(item_node["children"].keys()):
#                     subitem_node = item_node["children"][subitem]
#                     if not is_non_zero(subitem_node["total"]):
#                         continue

#                     subitem_rows.append({
#                         "label": subitem,
#                         "months": {m: subitem_node["months"].get(m, 0) for m in month_order},
#                         "total": subitem_node["total"],
#                     })

#                 if subitem_rows:
#                     detail_sheets.append({
#                         "note": note_code,
#                         "sheet_name": sheet_name,
#                         "activity": activity,
#                         "operation": operation,
#                         "item": item,
#                         "months": month_order,
#                         "rows": subitem_rows,
#                         "total": item_node["total"],
#                         "total_by_month": {m: item_node["months"].get(m, 0) for m in month_order},
#                     })

#     return {
#         "months": month_order,
#         "rows": pivot_rows,
#         "grand_total": {m: grand_total.get(m, 0) for m in month_order},
#         "grand_total_sum": sum(grand_total.values()),
#         "detail_sheets": detail_sheets,
#     }







# # budget/reporting/excel/data_loader.py
# from collections import defaultdict
# from hashlib import md5
# from datetime import datetime

# from django.db import connection


# def load_budget_export_data(version):
#     gl_rows = get_gl_rows(version.id)
#     fact_rows = get_fact_rows(version.date_from, version.date_to)

#     return {
#         "version": {
#             "id": version.id,
#             "number": version.number,
#             "budget_type": version.get_budget_type_display(),
#             "description": version.description,
#             "date_from": version.date_from,
#             "date_to": version.date_to,
#             "status": getattr(version, "status", None),
#         },
#         "revenue_param": version.revenue_param or {},
#         "wb_costs_params": version.wb_costs_params or {},
#         "cf_params": version.cf_params or {},
#         "report": version.report or {},
#         "gl_rows": gl_rows,
#         "fact_rows": fact_rows,

#         # обычный экспорт бюджет/факт
#         "gl_pivot": build_gl_plan_fact_pivot(gl_rows, fact_rows),

#         # отдельная структура именно для compare версий бюджетов
#         "compare_pivot": build_budget_compare_pivot(gl_rows),
#     }


# def get_gl_rows(version_id):
#     sql = """
#         SELECT
#             x.date_from,
#             (lv1.code::text || ' ' || lv1.name::text) AS activity,
#             (lv2.code::text || ' ' || lv2.name::text) AS operation,
#             (lv3.code::text || ' ' || lv3.name::text) AS item,
#             (i.code::text || ' ' || i.name::text) AS subitem,
#             x.dt,
#             x.cr,
#             x.amount,
#             x.description
#         FROM (
#             SELECT
#                 "date" AS date_from,
#                 round(dt / 100.0, 2) AS dt,
#                 round(cr / 100.0, 2) AS cr,
#                 round((dt - cr) / 100.0, 2) AS amount,
#                 subconto_id,
#                 description
#             FROM public.budget_gl
#             WHERE version_id = %s
#         ) x
#         JOIN corporate_cfitems i   ON i.id = x.subconto_id
#         JOIN corporate_cfitems lv3 ON lv3.id = i.parent_id
#         JOIN corporate_cfitems lv2 ON lv2.id = lv3.parent_id
#         JOIN corporate_cfitems lv1 ON lv1.id = lv2.parent_id
#         ORDER BY x.date_from, activity, operation, item, subitem
#     """

#     with connection.cursor() as cursor:
#         cursor.execute(sql, [version_id])
#         rows = cursor.fetchall()

#     result = []
#     for row in rows:
#         result.append({
#             "date_from": row[0],
#             "activity": row[1],
#             "operation": row[2],
#             "item": row[3],
#             "subitem": row[4],
#             "dt": float(row[5] or 0),
#             "cr": float(row[6] or 0),
#             "amount": float(row[7] or 0),
#             "description": row[8],
#         })
#     return result


# # def get_fact_rows(date_from, date_to):
# #     sql = """
# #         SELECT
# #             x.date_from,
# #             (lv1.code::text || ' ' || lv1.name::text) AS activity,
# #             (lv2.code::text || ' ' || lv2.name::text) AS operation,
# #             (lv3.code::text || ' ' || lv3.name::text) AS item,
# #             (i.code::text || ' ' || i.name::text) AS subitem,
# #             round(sum(x.amount), 2) AS amount
# #         FROM public.cf_to_csv x
# #         JOIN corporate_cfitems i   ON i.id = x.subconto_id
# #         JOIN corporate_cfitems lv3 ON lv3.id = i.parent_id
# #         JOIN corporate_cfitems lv2 ON lv2.id = lv3.parent_id
# #         JOIN corporate_cfitems lv1 ON lv1.id = lv2.parent_id
# #         WHERE x.date_from BETWEEN %s AND %s
# #         GROUP BY
# #             x.date_from,
# #             lv1.code, lv1.name,
# #             lv2.code, lv2.name,
# #             lv3.code, lv3.name,
# #             i.code, i.name
# #         ORDER BY
# #             x.date_from,
# #             lv1.code, lv1.name,
# #             lv2.code, lv2.name,
# #             lv3.code, lv3.name,
# #             i.code, i.name
# #     """

# #     with connection.cursor() as cursor:
# #         cursor.execute(sql, [date_from, date_to])
# #         rows = cursor.fetchall()

# #     result = []
# #     for row in rows:
# #         result.append({
# #             "date_from": row[0],
# #             "activity": row[1],
# #             "operation": row[2],
# #             "item": row[3],
# #             "subitem": row[4],
# #             "amount": float(row[5] or 0),
# #         })
# #     return result




# def get_fact_rows(date_from, date_to):
#     sql = """
#         SELECT
#             x.date_from,
#             (lv1.code::text || ' ' || lv1.name::text) AS activity,
#             (lv2.code::text || ' ' || lv2.name::text) AS operation,
#             (lv3.code::text || ' ' || lv3.name::text) AS item,
#             (i.code::text || ' ' || i.name::text) AS subitem,
#             COALESCE(NULLIF(TRIM(x.cp_name), ''), 'Без контрагента') AS cp_name,
#             round(sum(x.amount), 2) AS amount
#         FROM public.cf_to_csv x
#         JOIN corporate_cfitems i   ON i.id = x.subconto_id
#         JOIN corporate_cfitems lv3 ON lv3.id = i.parent_id
#         JOIN corporate_cfitems lv2 ON lv2.id = lv3.parent_id
#         JOIN corporate_cfitems lv1 ON lv1.id = lv2.parent_id
#         WHERE x.date_from BETWEEN %s AND %s
#         GROUP BY
#             x.date_from,
#             lv1.code, lv1.name,
#             lv2.code, lv2.name,
#             lv3.code, lv3.name,
#             i.code, i.name,
#             COALESCE(NULLIF(TRIM(x.cp_name), ''), 'Без контрагента')
#         ORDER BY
#             x.date_from,
#             lv1.code, lv1.name,
#             lv2.code, lv2.name,
#             lv3.code, lv3.name,
#             i.code, i.name,
#             COALESCE(NULLIF(TRIM(x.cp_name), ''), 'Без контрагента')
#     """

#     with connection.cursor() as cursor:
#         cursor.execute(sql, [date_from, date_to])
#         rows = cursor.fetchall()

#     result = []
#     for row in rows:
#         result.append({
#             "date_from": row[0],
#             "activity": row[1],
#             "operation": row[2],
#             "item": row[3],
#             "subitem": row[4],
#             "cp_name": row[5],
#             "amount": float(row[6] or 0),
#         })
#     return result


# def build_gl_plan_fact_pivot(gl_rows, fact_rows):
#     month_order = []
#     month_set = set()

#     month_map = {
#         1: "Янв",
#         2: "Фев",
#         3: "Мар",
#         4: "Апр",
#         5: "Май",
#         6: "Июн",
#         7: "Июл",
#         8: "Авг",
#         9: "Сен",
#         10: "Окт",
#         11: "Ноя",
#         12: "Дек",
#     }

#     tree = defaultdict(
#         lambda: {
#             "plan_months": defaultdict(float),
#             "fact_months": defaultdict(float),
#             "plan_total": 0.0,
#             "fact_total": 0.0,
#             "children": defaultdict(
#                 lambda: {
#                     "plan_months": defaultdict(float),
#                     "fact_months": defaultdict(float),
#                     "plan_total": 0.0,
#                     "fact_total": 0.0,
#                     "children": defaultdict(
#                         lambda: {
#                             "plan_months": defaultdict(float),
#                             "fact_months": defaultdict(float),
#                             "plan_total": 0.0,
#                             "fact_total": 0.0,
#                             "children": defaultdict(
#                                 lambda: {
#                                     "plan_months": defaultdict(float),
#                                     "fact_months": defaultdict(float),
#                                     "plan_total": 0.0,
#                                     "fact_total": 0.0,
#                                 }
#                             ),
#                         }
#                     ),
#                 }
#             ),
#         }
#     )

#     grand_plan_total = defaultdict(float)
#     grand_fact_total = defaultdict(float)

#     def month_label_from_date(dt):
#         return f'{month_map[dt.month]} {str(dt.year)[-2:]}'

#     for row in gl_rows:
#         dt = row["date_from"]
#         month_label = month_label_from_date(dt)

#         if month_label not in month_set:
#             month_set.add(month_label)
#             month_order.append(month_label)

#         activity = row["activity"] or "—"
#         operation = row["operation"] or "—"
#         item = row["item"] or "—"
#         subitem = row["subitem"] or "—"
#         amount = float(row["amount"] or 0)
#         cp_name = row.get("cp_name") or "Без контрагента"

#         tree[activity]["plan_months"][month_label] += amount
#         tree[activity]["plan_total"] += amount

#         tree[activity]["children"][operation]["plan_months"][month_label] += amount
#         tree[activity]["children"][operation]["plan_total"] += amount

#         tree[activity]["children"][operation]["children"][item]["plan_months"][month_label] += amount
#         tree[activity]["children"][operation]["children"][item]["plan_total"] += amount

#         tree[activity]["children"][operation]["children"][item]["children"][subitem]["plan_months"][month_label] += amount
#         tree[activity]["children"][operation]["children"][item]["children"][subitem]["plan_total"] += amount

#         grand_plan_total[month_label] += amount

#     for row in fact_rows:
#         dt = row["date_from"]
#         month_label = month_label_from_date(dt)

#         if month_label not in month_set:
#             month_set.add(month_label)
#             month_order.append(month_label)

#         activity = row["activity"] or "—"
#         operation = row["operation"] or "—"
#         item = row["item"] or "—"
#         subitem = row["subitem"] or "—"
#         cp_name = row.get("cp_name") or "Без контрагента"
#         amount = float(row["amount"] or 0)

#         tree[activity]["fact_months"][month_label] += amount
#         tree[activity]["fact_total"] += amount

#         tree[activity]["children"][operation]["fact_months"][month_label] += amount
#         tree[activity]["children"][operation]["fact_total"] += amount

#         tree[activity]["children"][operation]["children"][item]["fact_months"][month_label] += amount
#         tree[activity]["children"][operation]["children"][item]["fact_total"] += amount

#         subitem_node = tree[activity]["children"][operation]["children"][item]["children"][subitem]
#         subitem_node["fact_months"][month_label] += amount
#         subitem_node["fact_total"] += amount

#         subitem_node["fact_counterparties"][cp_name]["fact_months"][month_label] += amount
#         subitem_node["fact_counterparties"][cp_name]["fact_total"] += amount

#         grand_fact_total[month_label] += amount

#     def is_non_zero(plan_value, fact_value):
#         return abs(float(plan_value or 0)) > 0.0001 or abs(float(fact_value or 0)) > 0.0001

#     pivot_rows = []
#     detail_sheets = []

#     activity_idx = 0

#     for activity in sorted(tree.keys()):
#         activity_node = tree[activity]
#         if not is_non_zero(activity_node["plan_total"], activity_node["fact_total"]):
#             continue

#         activity_idx += 1
#         operation_idx = 0

#         pivot_rows.append({
#             "level": 0,
#             "label": activity,
#             "plan_months": {m: activity_node["plan_months"].get(m, 0) for m in month_order},
#             "fact_months": {m: activity_node["fact_months"].get(m, 0) for m in month_order},
#             "delta_months": {
#                 m: activity_node["fact_months"].get(m, 0) - activity_node["plan_months"].get(m, 0)
#                 for m in month_order
#             },
#             "plan_total": activity_node["plan_total"],
#             "fact_total": activity_node["fact_total"],
#             "delta_total": activity_node["fact_total"] - activity_node["plan_total"],
#             "row_type": "activity",
#             "note": "",
#             "sheet_name": None,
#         })

#         for operation in sorted(activity_node["children"].keys()):
#             operation_node = activity_node["children"][operation]
#             if not is_non_zero(operation_node["plan_total"], operation_node["fact_total"]):
#                 continue

#             operation_idx += 1
#             item_idx = 0

#             pivot_rows.append({
#                 "level": 1,
#                 "label": operation,
#                 "plan_months": {m: operation_node["plan_months"].get(m, 0) for m in month_order},
#                 "fact_months": {m: operation_node["fact_months"].get(m, 0) for m in month_order},
#                 "delta_months": {
#                     m: operation_node["fact_months"].get(m, 0) - operation_node["plan_months"].get(m, 0)
#                     for m in month_order
#                 },
#                 "plan_total": operation_node["plan_total"],
#                 "fact_total": operation_node["fact_total"],
#                 "delta_total": operation_node["fact_total"] - operation_node["plan_total"],
#                 "row_type": "operation",
#                 "note": "",
#                 "sheet_name": None,
#             })

#             for item in sorted(operation_node["children"].keys()):
#                 item_node = operation_node["children"][item]
#                 if not is_non_zero(item_node["plan_total"], item_node["fact_total"]):
#                     continue

#                 item_idx += 1

#                 subitem_rows = []
#                 for subitem in sorted(item_node["children"].keys()):
#                     subitem_node = item_node["children"][subitem]
#                     if not is_non_zero(subitem_node["plan_total"], subitem_node["fact_total"]):
#                         continue

#                     subitem_rows.append({
#                         "label": subitem,
#                         "plan_months": {m: subitem_node["plan_months"].get(m, 0) for m in month_order},
#                         "fact_months": {m: subitem_node["fact_months"].get(m, 0) for m in month_order},
#                         "delta_months": {
#                             m: subitem_node["fact_months"].get(m, 0) - subitem_node["plan_months"].get(m, 0)
#                             for m in month_order
#                         },
#                         "plan_total": subitem_node["plan_total"],
#                         "fact_total": subitem_node["fact_total"],
#                         "delta_total": subitem_node["fact_total"] - subitem_node["plan_total"],
#                     })

#                 has_detail = len(subitem_rows) > 0
#                 note_code = f"{activity_idx}.{operation_idx}.{item_idx}" if has_detail else ""
#                 sheet_name = note_code if has_detail else None

#                 pivot_rows.append({
#                     "level": 2,
#                     "label": item,
#                     "plan_months": {m: item_node["plan_months"].get(m, 0) for m in month_order},
#                     "fact_months": {m: item_node["fact_months"].get(m, 0) for m in month_order},
#                     "delta_months": {
#                         m: item_node["fact_months"].get(m, 0) - item_node["plan_months"].get(m, 0)
#                         for m in month_order
#                     },
#                     "plan_total": item_node["plan_total"],
#                     "fact_total": item_node["fact_total"],
#                     "delta_total": item_node["fact_total"] - item_node["plan_total"],
#                     "row_type": "item",
#                     "note": note_code,
#                     "sheet_name": sheet_name,
#                 })

#                 if has_detail:
#                     detail_sheets.append({
#                         "note": note_code,
#                         "sheet_name": sheet_name,
#                         "activity": activity,
#                         "operation": operation,
#                         "item": item,
#                         "months": month_order,
#                         "rows": subitem_rows,
#                         "plan_total": item_node["plan_total"],
#                         "fact_total": item_node["fact_total"],
#                         "delta_total": item_node["fact_total"] - item_node["plan_total"],
#                         "total_plan_by_month": {m: item_node["plan_months"].get(m, 0) for m in month_order},
#                         "total_fact_by_month": {m: item_node["fact_months"].get(m, 0) for m in month_order},
#                         "total_delta_by_month": {
#                             m: item_node["fact_months"].get(m, 0) - item_node["plan_months"].get(m, 0)
#                             for m in month_order
#                         },
#                     })

#     return {
#         "months": month_order,
#         "rows": pivot_rows,
#         "grand_plan_total": {m: grand_plan_total.get(m, 0) for m in month_order},
#         "grand_fact_total": {m: grand_fact_total.get(m, 0) for m in month_order},
#         "grand_delta_total": {
#             m: grand_fact_total.get(m, 0) - grand_plan_total.get(m, 0)
#             for m in month_order
#         },
#         "grand_plan_sum": sum(grand_plan_total.values()),
#         "grand_fact_sum": sum(grand_fact_total.values()),
#         "grand_delta_sum": sum(grand_fact_total.values()) - sum(grand_plan_total.values()),
#         "detail_sheets": detail_sheets,
#     }


# def _safe_label(value):
#     return value or "—"


# def _month_key(dt):
#     return dt.strftime("%Y-%m")


# def _month_label_by_key(month_key):
#     dt = datetime.strptime(month_key, "%Y-%m")
#     month_map = {
#         1: "Янв",
#         2: "Фев",
#         3: "Мар",
#         4: "Апр",
#         5: "Май",
#         6: "Июн",
#         7: "Июл",
#         8: "Авг",
#         9: "Сен",
#         10: "Окт",
#         11: "Ноя",
#         12: "Дек",
#     }
#     return f'{month_map[dt.month]} {str(dt.year)[-2:]}'


# def _quarter_key(dt):
#     quarter = (dt.month - 1) // 3 + 1
#     return f"{dt.year}-Q{quarter}"


# def _quarter_label_by_key(q_key):
#     year, quarter = q_key.split("-Q")
#     return f"Q{quarter} {year}"


# def _detail_key(activity, operation, item):
#     return f"{activity}|{operation}|{item}"


# def _detail_sheet_name(activity, operation, item):
#     raw = _detail_key(activity, operation, item)
#     suffix = md5(raw.encode("utf-8")).hexdigest()[:8]
#     item_part = (item or "ITEM").replace("/", "_").replace("\\", "_").replace(":", "_")
#     item_part = item_part[:15]
#     return f"DET_{item_part}_{suffix}"[:31]


# def build_budget_compare_pivot(gl_rows):
#     month_order = []
#     month_set = set()
#     quarter_order = []
#     quarter_set = set()

#     tree = defaultdict(
#         lambda: {
#             "months": defaultdict(float),
#             "quarters": defaultdict(float),
#             "total": 0.0,
#             "children": defaultdict(
#                 lambda: {
#                     "months": defaultdict(float),
#                     "quarters": defaultdict(float),
#                     "total": 0.0,
#                     "children": defaultdict(
#                         lambda: {
#                             "months": defaultdict(float),
#                             "quarters": defaultdict(float),
#                             "total": 0.0,
#                             "children": defaultdict(
#                                 lambda: {
#                                     "months": defaultdict(float),
#                                     "quarters": defaultdict(float),
#                                     "total": 0.0,
#                                 }
#                             ),
#                         }
#                     ),
#                 }
#             ),
#         }
#     )

#     grand_month_total = defaultdict(float)
#     grand_quarter_total = defaultdict(float)

#     for row in gl_rows:
#         dt = row["date_from"]
#         month_key = _month_key(dt)
#         quarter_key = _quarter_key(dt)

#         if month_key not in month_set:
#             month_set.add(month_key)
#             month_order.append(month_key)

#         if quarter_key not in quarter_set:
#             quarter_set.add(quarter_key)
#             quarter_order.append(quarter_key)

#         activity = _safe_label(row["activity"])
#         operation = _safe_label(row["operation"])
#         item = _safe_label(row["item"])
#         subitem = _safe_label(row["subitem"])
#         amount = float(row["amount"] or 0)

#         tree[activity]["months"][month_key] += amount
#         tree[activity]["quarters"][quarter_key] += amount
#         tree[activity]["total"] += amount

#         tree[activity]["children"][operation]["months"][month_key] += amount
#         tree[activity]["children"][operation]["quarters"][quarter_key] += amount
#         tree[activity]["children"][operation]["total"] += amount

#         tree[activity]["children"][operation]["children"][item]["months"][month_key] += amount
#         tree[activity]["children"][operation]["children"][item]["quarters"][quarter_key] += amount
#         tree[activity]["children"][operation]["children"][item]["total"] += amount

#         tree[activity]["children"][operation]["children"][item]["children"][subitem]["months"][month_key] += amount
#         tree[activity]["children"][operation]["children"][item]["children"][subitem]["quarters"][quarter_key] += amount
#         tree[activity]["children"][operation]["children"][item]["children"][subitem]["total"] += amount

#         grand_month_total[month_key] += amount
#         grand_quarter_total[quarter_key] += amount

#     def is_non_zero(total_value):
#         return abs(float(total_value or 0)) > 0.0001

#     pivot_rows = []
#     detail_sheets = []

#     for activity in sorted(tree.keys()):
#         activity_node = tree[activity]
#         if not is_non_zero(activity_node["total"]):
#             continue

#         pivot_rows.append({
#             "level": 0,
#             "row_type": "activity",
#             "label": activity,
#             "activity": activity,
#             "operation": "—",
#             "item": "—",
#             "path_key": f"{activity}|—|—",
#             "sheet_name": None,
#             "months": {m: activity_node["months"].get(m, 0) for m in month_order},
#             "quarters": {q: activity_node["quarters"].get(q, 0) for q in quarter_order},
#             "total": activity_node["total"],
#         })

#         for operation in sorted(activity_node["children"].keys()):
#             operation_node = activity_node["children"][operation]
#             if not is_non_zero(operation_node["total"]):
#                 continue

#             pivot_rows.append({
#                 "level": 1,
#                 "row_type": "operation",
#                 "label": operation,
#                 "activity": activity,
#                 "operation": operation,
#                 "item": "—",
#                 "path_key": f"{activity}|{operation}|—",
#                 "sheet_name": None,
#                 "months": {m: operation_node["months"].get(m, 0) for m in month_order},
#                 "quarters": {q: operation_node["quarters"].get(q, 0) for q in quarter_order},
#                 "total": operation_node["total"],
#             })

#             for item in sorted(operation_node["children"].keys()):
#                 item_node = operation_node["children"][item]
#                 if not is_non_zero(item_node["total"]):
#                     continue

#                 path_key = _detail_key(activity, operation, item)
#                 sheet_name = _detail_sheet_name(activity, operation, item)

#                 pivot_rows.append({
#                     "level": 2,
#                     "row_type": "item",
#                     "label": item,
#                     "activity": activity,
#                     "operation": operation,
#                     "item": item,
#                     "path_key": path_key,
#                     "sheet_name": sheet_name,
#                     "months": {m: item_node["months"].get(m, 0) for m in month_order},
#                     "quarters": {q: item_node["quarters"].get(q, 0) for q in quarter_order},
#                     "total": item_node["total"],
#                 })

#                 subitem_rows = []
#                 for subitem in sorted(item_node["children"].keys()):
#                     subitem_node = item_node["children"][subitem]
#                     if not is_non_zero(subitem_node["total"]):
#                         continue

#                     subitem_rows.append({
#                         "label": subitem,
#                         "months": {m: subitem_node["months"].get(m, 0) for m in month_order},
#                         "quarters": {q: subitem_node["quarters"].get(q, 0) for q in quarter_order},
#                         "total": subitem_node["total"],
#                     })

#                 if subitem_rows:
#                     detail_sheets.append({
#                         "path_key": path_key,
#                         "sheet_name": sheet_name,
#                         "activity": activity,
#                         "operation": operation,
#                         "item": item,
#                         "months": month_order,
#                         "month_labels": {m: _month_label_by_key(m) for m in month_order},
#                         "quarters": quarter_order,
#                         "quarter_labels": {q: _quarter_label_by_key(q) for q in quarter_order},
#                         "rows": subitem_rows,
#                         "total": item_node["total"],
#                         "total_by_month": {m: item_node["months"].get(m, 0) for m in month_order},
#                         "total_by_quarter": {q: item_node["quarters"].get(q, 0) for q in quarter_order},
#                     })
    
    
#     month_order = sorted(month_order)
#     quarter_order = sorted(quarter_order)

#     return {
#         "months": month_order,
#         "month_labels": {m: _month_label_by_key(m) for m in month_order},
#         "quarters": quarter_order,
#         "quarter_labels": {q: _quarter_label_by_key(q) for q in quarter_order},
#         "rows": pivot_rows,
#         "grand_month_total": {m: grand_month_total.get(m, 0) for m in month_order},
#         "grand_quarter_total": {q: grand_quarter_total.get(q, 0) for q in quarter_order},
#         "grand_total_sum": sum(grand_month_total.values()),
#         "detail_sheets": detail_sheets,
#     }





# budget/reporting/excel/data_loader.py
from collections import defaultdict
from hashlib import md5
from datetime import datetime

from django.db import connection


def load_budget_export_data(version):
    gl_rows = get_gl_rows(version.id)
    fact_rows = get_fact_rows(version.date_from, version.date_to)

    return {
        "version": {
            "id": version.id,
            "number": version.number,
            "budget_type": version.get_budget_type_display(),
            "description": version.description,
            "date_from": version.date_from,
            "date_to": version.date_to,
            "status": getattr(version, "status", None),
        },
        "revenue_param": version.revenue_param or {},
        "wb_costs_params": version.wb_costs_params or {},
        "cf_params": version.cf_params or {},
        "report": version.report or {},
        "gl_rows": gl_rows,
        "fact_rows": fact_rows,

        # обычный экспорт бюджет/факт
        "gl_pivot": build_gl_plan_fact_pivot(gl_rows, fact_rows),

        # отдельная структура именно для compare версий бюджетов
        "compare_pivot": build_budget_compare_pivot(gl_rows),
    }


def get_gl_rows(version_id):
    sql = """
        SELECT
            x.date_from,
            (lv1.code::text || ' ' || lv1.name::text) AS activity,
            (lv2.code::text || ' ' || lv2.name::text) AS operation,
            (lv3.code::text || ' ' || lv3.name::text) AS item,
            (i.code::text || ' ' || i.name::text) AS subitem,
            x.dt,
            x.cr,
            x.amount,
            x.description
        FROM (
            SELECT
                "date" AS date_from,
                round(dt / 100.0, 2) AS dt,
                round(cr / 100.0, 2) AS cr,
                round((dt - cr) / 100.0, 2) AS amount,
                subconto_id,
                description
            FROM public.budget_gl
            WHERE version_id = %s
        ) x
        JOIN corporate_cfitems i   ON i.id = x.subconto_id
        JOIN corporate_cfitems lv3 ON lv3.id = i.parent_id
        JOIN corporate_cfitems lv2 ON lv2.id = lv3.parent_id
        JOIN corporate_cfitems lv1 ON lv1.id = lv2.parent_id
        ORDER BY x.date_from, activity, operation, item, subitem
    """

    with connection.cursor() as cursor:
        cursor.execute(sql, [version_id])
        rows = cursor.fetchall()

    result = []
    for row in rows:
        result.append({
            "date_from": row[0],
            "activity": row[1],
            "operation": row[2],
            "item": row[3],
            "subitem": row[4],
            "dt": float(row[5] or 0),
            "cr": float(row[6] or 0),
            "amount": float(row[7] or 0),
            "description": row[8],
        })
    return result


def get_fact_rows(date_from, date_to):
    sql = """
        SELECT
            x.date_from,
            (lv1.code::text || ' ' || lv1.name::text) AS activity,
            (lv2.code::text || ' ' || lv2.name::text) AS operation,
            (lv3.code::text || ' ' || lv3.name::text) AS item,
            (i.code::text || ' ' || i.name::text) AS subitem,
            COALESCE(NULLIF(TRIM(x.cp_name), ''), 'Без контрагента') AS cp_name,
            round(sum(x.amount), 2) AS amount
        FROM public.cf_to_csv x
        JOIN corporate_cfitems i   ON i.id = x.subconto_id
        JOIN corporate_cfitems lv3 ON lv3.id = i.parent_id
        JOIN corporate_cfitems lv2 ON lv2.id = lv3.parent_id
        JOIN corporate_cfitems lv1 ON lv1.id = lv2.parent_id
        WHERE x.date_from BETWEEN %s AND %s
        GROUP BY
            x.date_from,
            lv1.code, lv1.name,
            lv2.code, lv2.name,
            lv3.code, lv3.name,
            i.code, i.name,
            COALESCE(NULLIF(TRIM(x.cp_name), ''), 'Без контрагента')
        ORDER BY
            x.date_from,
            lv1.code, lv1.name,
            lv2.code, lv2.name,
            lv3.code, lv3.name,
            i.code, i.name,
            COALESCE(NULLIF(TRIM(x.cp_name), ''), 'Без контрагента')
    """

    with connection.cursor() as cursor:
        cursor.execute(sql, [date_from, date_to])
        rows = cursor.fetchall()

    result = []
    for row in rows:
        result.append({
            "date_from": row[0],
            "activity": row[1],
            "operation": row[2],
            "item": row[3],
            "subitem": row[4],
            "cp_name": row[5],
            "amount": float(row[6] or 0),
        })
    return result


def build_gl_plan_fact_pivot(gl_rows, fact_rows):
    month_order = []
    month_set = set()

    month_map = {
        1: "Янв",
        2: "Фев",
        3: "Мар",
        4: "Апр",
        5: "Май",
        6: "Июн",
        7: "Июл",
        8: "Авг",
        9: "Сен",
        10: "Окт",
        11: "Ноя",
        12: "Дек",
    }

    tree = defaultdict(
        lambda: {
            "plan_months": defaultdict(float),
            "fact_months": defaultdict(float),
            "plan_total": 0.0,
            "fact_total": 0.0,
            "children": defaultdict(
                lambda: {
                    "plan_months": defaultdict(float),
                    "fact_months": defaultdict(float),
                    "plan_total": 0.0,
                    "fact_total": 0.0,
                    "children": defaultdict(
                        lambda: {
                            "plan_months": defaultdict(float),
                            "fact_months": defaultdict(float),
                            "plan_total": 0.0,
                            "fact_total": 0.0,
                            "children": defaultdict(
                                lambda: {
                                    "plan_months": defaultdict(float),
                                    "fact_months": defaultdict(float),
                                    "plan_total": 0.0,
                                    "fact_total": 0.0,
                                    "fact_counterparties": defaultdict(
                                        lambda: {
                                            "fact_months": defaultdict(float),
                                            "fact_total": 0.0,
                                        }
                                    ),
                                }
                            ),
                        }
                    ),
                }
            ),
        }
    )

    grand_plan_total = defaultdict(float)
    grand_fact_total = defaultdict(float)

    def month_label_from_date(dt):
        return f'{month_map[dt.month]} {str(dt.year)[-2:]}'

    for row in gl_rows:
        dt = row["date_from"]
        month_label = month_label_from_date(dt)

        if month_label not in month_set:
            month_set.add(month_label)
            month_order.append(month_label)

        activity = row["activity"] or "—"
        operation = row["operation"] or "—"
        item = row["item"] or "—"
        subitem = row["subitem"] or "—"
        amount = float(row["amount"] or 0)

        tree[activity]["plan_months"][month_label] += amount
        tree[activity]["plan_total"] += amount

        tree[activity]["children"][operation]["plan_months"][month_label] += amount
        tree[activity]["children"][operation]["plan_total"] += amount

        tree[activity]["children"][operation]["children"][item]["plan_months"][month_label] += amount
        tree[activity]["children"][operation]["children"][item]["plan_total"] += amount

        tree[activity]["children"][operation]["children"][item]["children"][subitem]["plan_months"][month_label] += amount
        tree[activity]["children"][operation]["children"][item]["children"][subitem]["plan_total"] += amount

        grand_plan_total[month_label] += amount

    for row in fact_rows:
        dt = row["date_from"]
        month_label = month_label_from_date(dt)

        if month_label not in month_set:
            month_set.add(month_label)
            month_order.append(month_label)

        activity = row["activity"] or "—"
        operation = row["operation"] or "—"
        item = row["item"] or "—"
        subitem = row["subitem"] or "—"
        cp_name = row.get("cp_name") or "Без контрагента"
        amount = float(row["amount"] or 0)

        tree[activity]["fact_months"][month_label] += amount
        tree[activity]["fact_total"] += amount

        tree[activity]["children"][operation]["fact_months"][month_label] += amount
        tree[activity]["children"][operation]["fact_total"] += amount

        tree[activity]["children"][operation]["children"][item]["fact_months"][month_label] += amount
        tree[activity]["children"][operation]["children"][item]["fact_total"] += amount

        subitem_node = tree[activity]["children"][operation]["children"][item]["children"][subitem]
        subitem_node["fact_months"][month_label] += amount
        subitem_node["fact_total"] += amount

        subitem_node["fact_counterparties"][cp_name]["fact_months"][month_label] += amount
        subitem_node["fact_counterparties"][cp_name]["fact_total"] += amount

        grand_fact_total[month_label] += amount

    def is_non_zero(plan_value, fact_value):
        return abs(float(plan_value or 0)) > 0.0001 or abs(float(fact_value or 0)) > 0.0001

    pivot_rows = []
    detail_sheets = []

    activity_idx = 0

    for activity in sorted(tree.keys()):
        activity_node = tree[activity]
        if not is_non_zero(activity_node["plan_total"], activity_node["fact_total"]):
            continue

        activity_idx += 1
        operation_idx = 0

        pivot_rows.append({
            "level": 0,
            "label": activity,
            "plan_months": {m: activity_node["plan_months"].get(m, 0) for m in month_order},
            "fact_months": {m: activity_node["fact_months"].get(m, 0) for m in month_order},
            "delta_months": {
                m: activity_node["fact_months"].get(m, 0) - activity_node["plan_months"].get(m, 0)
                for m in month_order
            },
            "plan_total": activity_node["plan_total"],
            "fact_total": activity_node["fact_total"],
            "delta_total": activity_node["fact_total"] - activity_node["plan_total"],
            "row_type": "activity",
            "note": "",
            "sheet_name": None,
        })

        for operation in sorted(activity_node["children"].keys()):
            operation_node = activity_node["children"][operation]
            if not is_non_zero(operation_node["plan_total"], operation_node["fact_total"]):
                continue

            operation_idx += 1
            item_idx = 0

            pivot_rows.append({
                "level": 1,
                "label": operation,
                "plan_months": {m: operation_node["plan_months"].get(m, 0) for m in month_order},
                "fact_months": {m: operation_node["fact_months"].get(m, 0) for m in month_order},
                "delta_months": {
                    m: operation_node["fact_months"].get(m, 0) - operation_node["plan_months"].get(m, 0)
                    for m in month_order
                },
                "plan_total": operation_node["plan_total"],
                "fact_total": operation_node["fact_total"],
                "delta_total": operation_node["fact_total"] - operation_node["plan_total"],
                "row_type": "operation",
                "note": "",
                "sheet_name": None,
            })

            for item in sorted(operation_node["children"].keys()):
                item_node = operation_node["children"][item]
                if not is_non_zero(item_node["plan_total"], item_node["fact_total"]):
                    continue

                item_idx += 1

                subitem_rows = []
                for subitem in sorted(item_node["children"].keys()):
                    subitem_node = item_node["children"][subitem]
                    if not is_non_zero(subitem_node["plan_total"], subitem_node["fact_total"]):
                        continue

                    counterparty_rows = []
                    for cp_name in sorted(subitem_node.get("fact_counterparties", {}).keys()):
                        cp_node = subitem_node["fact_counterparties"][cp_name]

                        if abs(float(cp_node["fact_total"] or 0)) <= 0.0001:
                            continue

                        counterparty_rows.append({
                            "label": cp_name,
                            "plan_months": {m: 0 for m in month_order},
                            "fact_months": {m: cp_node["fact_months"].get(m, 0) for m in month_order},
                            "delta_months": {m: cp_node["fact_months"].get(m, 0) for m in month_order},
                            "plan_total": 0.0,
                            "fact_total": cp_node["fact_total"],
                            "delta_total": cp_node["fact_total"],
                            "row_type": "counterparty",
                        })

                    subitem_rows.append({
                        "label": subitem,
                        "plan_months": {m: subitem_node["plan_months"].get(m, 0) for m in month_order},
                        "fact_months": {m: subitem_node["fact_months"].get(m, 0) for m in month_order},
                        "delta_months": {
                            m: subitem_node["fact_months"].get(m, 0) - subitem_node["plan_months"].get(m, 0)
                            for m in month_order
                        },
                        "plan_total": subitem_node["plan_total"],
                        "fact_total": subitem_node["fact_total"],
                        "delta_total": subitem_node["fact_total"] - subitem_node["plan_total"],
                        "row_type": "subitem",
                        "children": counterparty_rows,
                    })

                has_detail = len(subitem_rows) > 0
                note_code = f"{activity_idx}.{operation_idx}.{item_idx}" if has_detail else ""
                sheet_name = note_code if has_detail else None

                pivot_rows.append({
                    "level": 2,
                    "label": item,
                    "plan_months": {m: item_node["plan_months"].get(m, 0) for m in month_order},
                    "fact_months": {m: item_node["fact_months"].get(m, 0) for m in month_order},
                    "delta_months": {
                        m: item_node["fact_months"].get(m, 0) - item_node["plan_months"].get(m, 0)
                        for m in month_order
                    },
                    "plan_total": item_node["plan_total"],
                    "fact_total": item_node["fact_total"],
                    "delta_total": item_node["fact_total"] - item_node["plan_total"],
                    "row_type": "item",
                    "note": note_code,
                    "sheet_name": sheet_name,
                })

                if has_detail:
                    detail_sheets.append({
                        "note": note_code,
                        "sheet_name": sheet_name,
                        "activity": activity,
                        "operation": operation,
                        "item": item,
                        "months": month_order,
                        "rows": subitem_rows,
                        "plan_total": item_node["plan_total"],
                        "fact_total": item_node["fact_total"],
                        "delta_total": item_node["fact_total"] - item_node["plan_total"],
                        "total_plan_by_month": {m: item_node["plan_months"].get(m, 0) for m in month_order},
                        "total_fact_by_month": {m: item_node["fact_months"].get(m, 0) for m in month_order},
                        "total_delta_by_month": {
                            m: item_node["fact_months"].get(m, 0) - item_node["plan_months"].get(m, 0)
                            for m in month_order
                        },
                    })

    return {
        "months": month_order,
        "rows": pivot_rows,
        "grand_plan_total": {m: grand_plan_total.get(m, 0) for m in month_order},
        "grand_fact_total": {m: grand_fact_total.get(m, 0) for m in month_order},
        "grand_delta_total": {
            m: grand_fact_total.get(m, 0) - grand_plan_total.get(m, 0)
            for m in month_order
        },
        "grand_plan_sum": sum(grand_plan_total.values()),
        "grand_fact_sum": sum(grand_fact_total.values()),
        "grand_delta_sum": sum(grand_fact_total.values()) - sum(grand_plan_total.values()),
        "detail_sheets": detail_sheets,
    }


def _safe_label(value):
    return value or "—"


def _month_key(dt):
    return dt.strftime("%Y-%m")


def _month_label_by_key(month_key):
    dt = datetime.strptime(month_key, "%Y-%m")
    month_map = {
        1: "Янв",
        2: "Фев",
        3: "Мар",
        4: "Апр",
        5: "Май",
        6: "Июн",
        7: "Июл",
        8: "Авг",
        9: "Сен",
        10: "Окт",
        11: "Ноя",
        12: "Дек",
    }
    return f'{month_map[dt.month]} {str(dt.year)[-2:]}'


def _quarter_key(dt):
    quarter = (dt.month - 1) // 3 + 1
    return f"{dt.year}-Q{quarter}"


def _quarter_label_by_key(q_key):
    year, quarter = q_key.split("-Q")
    return f"Q{quarter} {year}"


def _detail_key(activity, operation, item):
    return f"{activity}|{operation}|{item}"


def _detail_sheet_name(activity, operation, item):
    raw = _detail_key(activity, operation, item)
    suffix = md5(raw.encode("utf-8")).hexdigest()[:8]
    item_part = (item or "ITEM").replace("/", "_").replace("\\", "_").replace(":", "_")
    item_part = item_part[:15]
    return f"DET_{item_part}_{suffix}"[:31]


def build_budget_compare_pivot(gl_rows):
    month_order = []
    month_set = set()
    quarter_order = []
    quarter_set = set()

    tree = defaultdict(
        lambda: {
            "months": defaultdict(float),
            "quarters": defaultdict(float),
            "total": 0.0,
            "children": defaultdict(
                lambda: {
                    "months": defaultdict(float),
                    "quarters": defaultdict(float),
                    "total": 0.0,
                    "children": defaultdict(
                        lambda: {
                            "months": defaultdict(float),
                            "quarters": defaultdict(float),
                            "total": 0.0,
                            "children": defaultdict(
                                lambda: {
                                    "months": defaultdict(float),
                                    "quarters": defaultdict(float),
                                    "total": 0.0,
                                }
                            ),
                        }
                    ),
                }
            ),
        }
    )

    grand_month_total = defaultdict(float)
    grand_quarter_total = defaultdict(float)

    for row in gl_rows:
        dt = row["date_from"]
        month_key = _month_key(dt)
        quarter_key = _quarter_key(dt)

        if month_key not in month_set:
            month_set.add(month_key)
            month_order.append(month_key)

        if quarter_key not in quarter_set:
            quarter_set.add(quarter_key)
            quarter_order.append(quarter_key)

        activity = _safe_label(row["activity"])
        operation = _safe_label(row["operation"])
        item = _safe_label(row["item"])
        subitem = _safe_label(row["subitem"])
        amount = float(row["amount"] or 0)

        tree[activity]["months"][month_key] += amount
        tree[activity]["quarters"][quarter_key] += amount
        tree[activity]["total"] += amount

        tree[activity]["children"][operation]["months"][month_key] += amount
        tree[activity]["children"][operation]["quarters"][quarter_key] += amount
        tree[activity]["children"][operation]["total"] += amount

        tree[activity]["children"][operation]["children"][item]["months"][month_key] += amount
        tree[activity]["children"][operation]["children"][item]["quarters"][quarter_key] += amount
        tree[activity]["children"][operation]["children"][item]["total"] += amount

        tree[activity]["children"][operation]["children"][item]["children"][subitem]["months"][month_key] += amount
        tree[activity]["children"][operation]["children"][item]["children"][subitem]["quarters"][quarter_key] += amount
        tree[activity]["children"][operation]["children"][item]["children"][subitem]["total"] += amount

        grand_month_total[month_key] += amount
        grand_quarter_total[quarter_key] += amount

    month_order = sorted(month_order)
    quarter_order = sorted(quarter_order)

    def is_non_zero(total_value):
        return abs(float(total_value or 0)) > 0.0001

    pivot_rows = []
    detail_sheets = []

    for activity in sorted(tree.keys()):
        activity_node = tree[activity]
        if not is_non_zero(activity_node["total"]):
            continue

        pivot_rows.append({
            "level": 0,
            "row_type": "activity",
            "label": activity,
            "activity": activity,
            "operation": "—",
            "item": "—",
            "path_key": f"{activity}|—|—",
            "sheet_name": None,
            "months": {m: activity_node["months"].get(m, 0) for m in month_order},
            "quarters": {q: activity_node["quarters"].get(q, 0) for q in quarter_order},
            "total": activity_node["total"],
        })

        for operation in sorted(activity_node["children"].keys()):
            operation_node = activity_node["children"][operation]
            if not is_non_zero(operation_node["total"]):
                continue

            pivot_rows.append({
                "level": 1,
                "row_type": "operation",
                "label": operation,
                "activity": activity,
                "operation": operation,
                "item": "—",
                "path_key": f"{activity}|{operation}|—",
                "sheet_name": None,
                "months": {m: operation_node["months"].get(m, 0) for m in month_order},
                "quarters": {q: operation_node["quarters"].get(q, 0) for q in quarter_order},
                "total": operation_node["total"],
            })

            for item in sorted(operation_node["children"].keys()):
                item_node = operation_node["children"][item]
                if not is_non_zero(item_node["total"]):
                    continue

                path_key = _detail_key(activity, operation, item)
                sheet_name = _detail_sheet_name(activity, operation, item)

                pivot_rows.append({
                    "level": 2,
                    "row_type": "item",
                    "label": item,
                    "activity": activity,
                    "operation": operation,
                    "item": item,
                    "path_key": path_key,
                    "sheet_name": sheet_name,
                    "months": {m: item_node["months"].get(m, 0) for m in month_order},
                    "quarters": {q: item_node["quarters"].get(q, 0) for q in quarter_order},
                    "total": item_node["total"],
                })

                subitem_rows = []
                for subitem in sorted(item_node["children"].keys()):
                    subitem_node = item_node["children"][subitem]
                    if not is_non_zero(subitem_node["total"]):
                        continue

                    subitem_rows.append({
                        "label": subitem,
                        "months": {m: subitem_node["months"].get(m, 0) for m in month_order},
                        "quarters": {q: subitem_node["quarters"].get(q, 0) for q in quarter_order},
                        "total": subitem_node["total"],
                    })

                if subitem_rows:
                    detail_sheets.append({
                        "path_key": path_key,
                        "sheet_name": sheet_name,
                        "activity": activity,
                        "operation": operation,
                        "item": item,
                        "months": month_order,
                        "month_labels": {m: _month_label_by_key(m) for m in month_order},
                        "quarters": quarter_order,
                        "quarter_labels": {q: _quarter_label_by_key(q) for q in quarter_order},
                        "rows": subitem_rows,
                        "total": item_node["total"],
                        "total_by_month": {m: item_node["months"].get(m, 0) for m in month_order},
                        "total_by_quarter": {q: item_node["quarters"].get(q, 0) for q in quarter_order},
                    })

    return {
        "months": month_order,
        "month_labels": {m: _month_label_by_key(m) for m in month_order},
        "quarters": quarter_order,
        "quarter_labels": {q: _quarter_label_by_key(q) for q in quarter_order},
        "rows": pivot_rows,
        "grand_month_total": {m: grand_month_total.get(m, 0) for m in month_order},
        "grand_quarter_total": {q: grand_quarter_total.get(q, 0) for q in quarter_order},
        "grand_total_sum": sum(grand_month_total.values()),
        "detail_sheets": detail_sheets,
    }