# budget/reporting/excel/data_loader.py
from collections import defaultdict
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
        },
        "revenue_param": version.revenue_param or {},
        "wb_costs_params": version.wb_costs_params or {},
        "cf_params": version.cf_params or {},
        "report": version.report or {},
        "gl_rows": gl_rows,
        "fact_rows": fact_rows,
        "gl_pivot": build_gl_plan_fact_pivot(gl_rows, fact_rows),
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
            i.code, i.name
        ORDER BY
            x.date_from,
            lv1.code, lv1.name,
            lv2.code, lv2.name,
            lv3.code, lv3.name,
            i.code, i.name
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
            "amount": float(row[5] or 0),
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

    # PLAN
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

    # FACT
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
        amount = float(row["amount"] or 0)

        tree[activity]["fact_months"][month_label] += amount
        tree[activity]["fact_total"] += amount

        tree[activity]["children"][operation]["fact_months"][month_label] += amount
        tree[activity]["children"][operation]["fact_total"] += amount

        tree[activity]["children"][operation]["children"][item]["fact_months"][month_label] += amount
        tree[activity]["children"][operation]["children"][item]["fact_total"] += amount

        tree[activity]["children"][operation]["children"][item]["children"][subitem]["fact_months"][month_label] += amount
        tree[activity]["children"][operation]["children"][item]["children"][subitem]["fact_total"] += amount

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







def build_gl_pivot(gl_rows):
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
            "months": defaultdict(float),
            "total": 0.0,
            "children": defaultdict(
                lambda: {
                    "months": defaultdict(float),
                    "total": 0.0,
                    "children": defaultdict(
                        lambda: {
                            "months": defaultdict(float),
                            "total": 0.0,
                            "children": defaultdict(
                                lambda: {
                                    "months": defaultdict(float),
                                    "total": 0.0,
                                }
                            ),
                        }
                    ),
                }
            ),
        }
    )

    grand_total = defaultdict(float)

    for row in gl_rows:
        dt = row["date_from"]
        month_label = f'{month_map[dt.month]} {str(dt.year)[-2:]}'

        if month_label not in month_set:
            month_set.add(month_label)
            month_order.append(month_label)

        activity = row["activity"] or "—"
        operation = row["operation"] or "—"
        item = row["item"] or "—"
        subitem = row["subitem"] or "—"
        amount = float(row["amount"] or 0)

        tree[activity]["months"][month_label] += amount
        tree[activity]["total"] += amount

        tree[activity]["children"][operation]["months"][month_label] += amount
        tree[activity]["children"][operation]["total"] += amount

        tree[activity]["children"][operation]["children"][item]["months"][month_label] += amount
        tree[activity]["children"][operation]["children"][item]["total"] += amount

        tree[activity]["children"][operation]["children"][item]["children"][subitem]["months"][month_label] += amount
        tree[activity]["children"][operation]["children"][item]["children"][subitem]["total"] += amount

        grand_total[month_label] += amount

    def is_non_zero(total_value):
        return abs(float(total_value or 0)) > 0.0001

    pivot_rows = []
    detail_sheets = []

    activity_idx = 0

    for activity in sorted(tree.keys()):
        activity_node = tree[activity]
        if not is_non_zero(activity_node["total"]):
            continue

        activity_idx += 1
        operation_idx = 0

        pivot_rows.append({
            "level": 0,
            "label": activity,
            "months": {m: activity_node["months"].get(m, 0) for m in month_order},
            "total": activity_node["total"],
            "row_type": "activity",
            "note": "",
            "sheet_name": None,
        })

        for operation in sorted(activity_node["children"].keys()):
            operation_node = activity_node["children"][operation]
            if not is_non_zero(operation_node["total"]):
                continue

            operation_idx += 1
            item_idx = 0

            pivot_rows.append({
                "level": 1,
                "label": operation,
                "months": {m: operation_node["months"].get(m, 0) for m in month_order},
                "total": operation_node["total"],
                "row_type": "operation",
                "note": "",
                "sheet_name": None,
            })

            for item in sorted(operation_node["children"].keys()):
                item_node = operation_node["children"][item]
                if not is_non_zero(item_node["total"]):
                    continue

                item_idx += 1
                note_code = f"{activity_idx}.{operation_idx}.{item_idx}"
                sheet_name = note_code

                pivot_rows.append({
                    "level": 2,
                    "label": item,
                    "months": {m: item_node["months"].get(m, 0) for m in month_order},
                    "total": item_node["total"],
                    "row_type": "item",
                    "note": note_code if item_node["children"] else "",
                    "sheet_name": sheet_name if item_node["children"] else None,
                })

                subitem_rows = []
                for subitem in sorted(item_node["children"].keys()):
                    subitem_node = item_node["children"][subitem]
                    if not is_non_zero(subitem_node["total"]):
                        continue

                    subitem_rows.append({
                        "label": subitem,
                        "months": {m: subitem_node["months"].get(m, 0) for m in month_order},
                        "total": subitem_node["total"],
                    })

                if subitem_rows:
                    detail_sheets.append({
                        "note": note_code,
                        "sheet_name": sheet_name,
                        "activity": activity,
                        "operation": operation,
                        "item": item,
                        "months": month_order,
                        "rows": subitem_rows,
                        "total": item_node["total"],
                        "total_by_month": {m: item_node["months"].get(m, 0) for m in month_order},
                    })

    return {
        "months": month_order,
        "rows": pivot_rows,
        "grand_total": {m: grand_total.get(m, 0) for m in month_order},
        "grand_total_sum": sum(grand_total.values()),
        "detail_sheets": detail_sheets,
    }