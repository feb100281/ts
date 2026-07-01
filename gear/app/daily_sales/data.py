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
            "SELECT DISTINCT subject_id, subject_name FROM inventories.wb_product"
        ).fetchall()
        data = [{"value": str(row[0]), "label": row[1]} for row in rows]
    return data

def brand_filter():
    """
    Бренд
    """
    with get_duckdb_conn_with_opt() as con:
        rows = con.execute(
            "select DISTINCT UPPER(brand) as brand_is, UPPER(brand) as brand_name from inventories.wb_product;"
        ).fetchall()
        data = [{"value": row[0], "label": row[1]} for row in rows]
    return data

def gender_filter():
    """
    Пол
    """
    with get_duckdb_conn_with_opt() as con:
        rows = con.execute(
            "select DISTINCT COALESCE(gender,'Не указан') as brand_is, COALESCE(gender,'Не указан') as brand_name from inventories.wb_product;"
        ).fetchall()
        data = [{"value": row[0], "label": row[1]} for row in rows]
    return data

      