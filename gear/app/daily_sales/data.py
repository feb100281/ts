# gear/app/daily_sales/data.py
from conns import get_duckdb_conn_with_opt

# Запрос даты обновления
def get_last_update():
    with get_duckdb_conn_with_opt() as con:
        result = con.execute(
            """ 
            select max(date_from) from sales.sales_long
            where field = 'retail_price'
            """
        ).fetchone()
        return result[0] if result else None
    
# --------
# Фильтры
# --------

def cat_filter():
    """
    Категория
    """
    with get_duckdb_conn_with_opt() as con:
        rows = con.execute(
            "SELECT DISTINCT subject_id, subject_name FROM inventories.wb_product order by 2"
        ).fetchall()
        data = [{"value": str(row[0]), "label": row[1]} for row in rows]
    return data

def brand_filter():
    """
    Бренд
    """
    with get_duckdb_conn_with_opt() as con:
        rows = con.execute(
            "select DISTINCT UPPER(brand) as brand_is, UPPER(brand) as brand_name from inventories.wb_product order by 1;"
        ).fetchall()
        data = [{"value": row[0], "label": row[1]} for row in rows]
    return data

def gender_filter():
    """
    Пол
    """
    with get_duckdb_conn_with_opt() as con:
        rows = con.execute(
            "select DISTINCT COALESCE(gender,'Не указан') as brand_is, COALESCE(gender,'Не указан') as brand_name from inventories.wb_product ;"
        ).fetchall()
        data = [{"value": row[0], "label": row[1]} for row in rows]
    return data

### ------------
#.  Умные фильтры
### ------------

def filters_by_brand(brand_list=None):
    where = ""
    params = []

    if brand_list:
        placeholders = ", ".join(["?"] * len(brand_list))
        where = f"WHERE UPPER(brand) IN ({placeholders})"
        params = brand_list

    with get_duckdb_conn_with_opt() as con:
        cats = con.execute(
            f"""
            SELECT DISTINCT subject_id, subject_name
            FROM inventories.wb_product
            {where}
            ORDER BY 2
            """,
            params,
        ).fetchall()

        genders = con.execute(
            f"""
            SELECT DISTINCT 
                COALESCE(gender, 'Не указан') AS gender_value,
                COALESCE(gender, 'Не указан') AS gender_label
            FROM inventories.wb_product
            {where}
            ORDER BY 1
            """,
            params,
        ).fetchall()

    return {
        "cats": [{"value": str(row[0]), "label": row[1]} for row in cats],
        "genders": [{"value": row[0], "label": row[1]} for row in genders],
    }

### ------------
#.  Остатки товаров с с/стью
### ------------

from datetime import date, timedelta
import pandas as pd
from conns import get_duckdb_conn_with_opt


def get_default_stocks_date():
    return date.today() - timedelta(days=1)


def get_stocks_export_data(report_date):
    """
    Остатки товаров на выбранную дату.
    По умолчанию дату передаем из DatePicker, обычно вчера.
    """
    with get_duckdb_conn_with_opt() as con:
        df = con.execute(
            """
            WITH stocks AS (
                SELECT 
                    t.date_from::DATE AS date_from,
                    u.usk,
                    t.nm_id,
                    p.title,
                    t.chrt_id,
                    s.tech_size,

                    SUM(COALESCE(t.quantity, 0)) AS quantity,
                    SUM(COALESCE(t.in_way_from_client, 0)) AS in_way_from_client,
                    SUM(COALESCE(t.in_way_to_client, 0)) AS in_way_to_client,

                    SUM(
                        COALESCE(t.quantity, 0)
                        + COALESCE(t.in_way_from_client, 0)
                        + COALESCE(t.in_way_to_client, 0)
                    ) AS total_quantity,

                    MAX(w.adjust_wo[-1]) AS last_costs,
                    MAX(w.adjust_man_wo[-1]) AS last_man_costs

                FROM stocks.unpacked_stocks t
                LEFT JOIN inventories.usk u 
                    ON u.card_id = t.nm_id
                LEFT JOIN cards.sizes s 
                    ON s.chrt_id = t.chrt_id
                LEFT JOIN inventories.pre_wo w 
                    ON w.usk = u.usk
                LEFT JOIN inventories.wb_product p 
                    ON p.card_id = t.nm_id

                WHERE t.date_from::DATE = $report_date::DATE

                GROUP BY
                    t.date_from::DATE,
                    u.usk,
                    t.nm_id,
                    p.title,
                    t.chrt_id,
                    s.tech_size
            )

            SELECT
                date_from AS "Дата",
                usk AS "USK",
                nm_id AS "NM ID",
                title AS "Наименование",
                chrt_id AS "Chrt ID",
                tech_size AS "Размер",

                quantity AS "Остаток на складе",
                in_way_from_client AS "В пути от клиента",
                in_way_to_client AS "В пути к клиенту",
                total_quantity AS "Итого количество",

                last_costs AS "Бух. с/с за ед.",
                last_man_costs AS "Упр. с/с за ед.",

                ROUND(total_quantity * COALESCE(last_costs, 0), 2) AS "Бух. с/с всего",
                ROUND(total_quantity * COALESCE(last_man_costs, 0), 2) AS "Упр. с/с всего"

            FROM stocks
            ORDER BY
                "Итого количество" DESC,
                "Наименование",
                "Размер"
            """,
            {"report_date": report_date},
        ).df()

    return df

