# gear/app/daily_sales/assistant/stocks.py
"""Товарные остатки для помощника: склады WB, в пути и наш склад FBS — всегда вместе.

Методика та же, что в дашборде остатков: итог = склады WB + FBS + в пути к клиенту
+ в пути от клиента. Источники: stocks.unpacked_stocks, stocks.unpacked_fbs_stocks.
"""
from __future__ import annotations

from datetime import date, timedelta

from conns import get_duckdb_conn_with_opt

GROUPS = {
    "brand": ("COALESCE(b.brand, 'Бренд не указан')", "Бренд"),
    "category": ("COALESCE(p.subject_name, 'Категория не указана')", "Категория"),
    "article": ("COALESCE(NULLIF(p.sa_name, ''), 'nm ' || CAST(s.nm_id AS VARCHAR))", "Артикул"),
}

BASE_SQL = """
WITH wb AS (
    SELECT nm_id,
           SUM(COALESCE(quantity, 0))           AS wb_qty,
           SUM(COALESCE(in_way_to_client, 0))   AS to_client,
           SUM(COALESCE(in_way_from_client, 0)) AS from_client
    FROM stocks.unpacked_stocks
    WHERE date_from::DATE = $d::DATE
    GROUP BY nm_id
),
fbs AS (
    SELECT nm_id, SUM(COALESCE(quantity, 0)) AS fbs_qty
    FROM stocks.unpacked_fbs_stocks
    WHERE date_from::DATE = $d::DATE
    GROUP BY nm_id
),
s AS (
    SELECT COALESCE(wb.nm_id, fbs.nm_id) AS nm_id,
           COALESCE(wb.wb_qty, 0)      AS wb_qty,
           COALESCE(wb.to_client, 0)   AS to_client,
           COALESCE(wb.from_client, 0) AS from_client,
           COALESCE(fbs.fbs_qty, 0)    AS fbs_qty
    FROM wb FULL OUTER JOIN fbs ON wb.nm_id = fbs.nm_id
),
b AS (SELECT nm_id, MAX(brand) AS brand FROM cards.unpacked_cards GROUP BY nm_id)
"""


def _f(v):
    return f"{int(v or 0):,}".replace(",", " ")


def _last_date(con, d: date):
    """Последняя дата с остатками не позже запрошенной."""
    row = con.execute(
        "SELECT MAX(date_from::DATE) FROM stocks.unpacked_stocks WHERE date_from::DATE <= ?",
        [d]).fetchone()
    return row[0] if row and row[0] else None


def stocks_report(report_date=None, by="total", brand=None, top=30) -> str:
    asked = (date.fromisoformat(str(report_date)[:10]) if report_date
             else date.today() - timedelta(days=1))
    top = max(1, min(int(top or 30), 100))
    with get_duckdb_conn_with_opt(ro=True) as con:
        d = _last_date(con, asked)
        if d is None:
            return f"Данных об остатках на {asked:%d.%m.%Y} и раньше нет."
        where, params = "", {"d": d}
        if brand:
            where = "WHERE LOWER(COALESCE(b.brand, '')) LIKE '%' || LOWER($brand) || '%'"
            params["brand"] = str(brand).strip()
        tot = con.execute(BASE_SQL + f"""
            SELECT SUM(s.wb_qty), SUM(s.to_client), SUM(s.from_client), SUM(s.fbs_qty),
                   COUNT(DISTINCT CASE WHEN s.wb_qty + s.to_client + s.from_client
                                            + s.fbs_qty > 0 THEN s.nm_id END)
            FROM s LEFT JOIN b ON b.nm_id = s.nm_id {where}""", params).fetchone()
        rows, label = [], ""
        if by in GROUPS:
            expr, label = GROUPS[by]
            rows = con.execute(BASE_SQL + f"""
                SELECT {expr} AS g, SUM(s.wb_qty), SUM(s.to_client), SUM(s.from_client),
                       SUM(s.fbs_qty),
                       SUM(s.wb_qty + s.to_client + s.from_client + s.fbs_qty) AS total
                FROM s
                LEFT JOIN b ON b.nm_id = s.nm_id
                LEFT JOIN cards.product p ON p.nm_id = s.nm_id
                {where}
                GROUP BY 1 HAVING total > 0 ORDER BY total DESC LIMIT {top}""",
                params).fetchall()
        elif by == "warehouse":
            label = "Склад WB"
            wh_where = where.replace("WHERE", "AND") if where else ""
            rows = con.execute(f"""
                WITH b AS (SELECT nm_id, MAX(brand) AS brand
                           FROM cards.unpacked_cards GROUP BY nm_id)
                SELECT COALESCE(t.warehouse_name, 'Склад не указан') AS g,
                       SUM(COALESCE(t.quantity, 0)),
                       SUM(COALESCE(t.in_way_to_client, 0)),
                       SUM(COALESCE(t.in_way_from_client, 0)), 0,
                       SUM(COALESCE(t.quantity, 0) + COALESCE(t.in_way_to_client, 0)
                           + COALESCE(t.in_way_from_client, 0)) AS total
                FROM stocks.unpacked_stocks t LEFT JOIN b ON b.nm_id = t.nm_id
                WHERE t.date_from::DATE = $d::DATE {wh_where}
                GROUP BY 1 HAVING total > 0 ORDER BY total DESC LIMIT {top}""",
                params).fetchall()

    wb, to_c, from_c, fbs, cards = (int(x or 0) for x in tot)
    total = wb + to_c + from_c + fbs
    head = f"ТОВАРНЫЕ ОСТАТКИ на {d:%d.%m.%Y}" + (f", бренд содержит «{brand}»" if brand else "")
    lines = [head]
    if d != asked:
        lines.append(f"На {asked:%d.%m.%Y} данных нет — показана последняя доступная дата.")
    lines += [
        "Где\tШтук",
        f"На складах WB\t{_f(wb)}",
        f"В пути к клиенту\t{_f(to_c)}",
        f"В пути от клиента (возвраты)\t{_f(from_c)}",
        f"На нашем складе FBS\t{_f(fbs)}",
        f"ИТОГО\t{_f(total)}",
        f"Карточек с остатком: {_f(cards)}",
    ]
    if rows:
        lines.append(f"\n{label}\tСклады WB\tВ пути к клиенту\tВ пути от клиента\tFBS\tИтого")
        for g, a, b_, c, f_, t in rows:
            lines.append(f"{g}\t{_f(a)}\t{_f(b_)}\t{_f(c)}\t{_f(f_)}\t{_f(t)}")
        if len(rows) == top:
            lines.append(f"Показаны первые {top} строк по убыванию. Полный список — в Excel.")
        if by == "warehouse":
            lines.append("Склад FBS — наш, в разбивке по складам WB его нет: он в итоге выше.")
    lines.append("Итог = склады WB + в пути к клиенту + в пути от клиента + FBS. В ответе "
                 "ВСЕГДА показывай все четыре строки и итог, даже если где-то ноль.")
    return "\n".join(lines)
