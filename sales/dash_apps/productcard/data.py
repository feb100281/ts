from django.db import connection
import pandas as pd
import numpy as np
from dateutil.relativedelta import relativedelta


def dictfetchone(cursor):
    columns = [col[0] for col in cursor.description]
    row = cursor.fetchone()
    return dict(zip(columns, row)) if row else None

def get_product_info(product_id):
    q  =  """
    SELECT
	product_id AS id,
    imt_name AS "Наименование",
    nm_id AS "WB Артикль",
    subj_root_name AS "Группа",
    subj_name AS "Категория",
    vendor_code AS "Код поставщика",
    brand_name AS "Брэнд",
    create_date AS "Создано",
    update_date AS "Обновлено",
    contents AS "Кр описание",
    composition AS "Состав",
    country AS "Страна",
    sex AS "Пол",
    kit AS "Комплект",
    nm_colors_names AS "Цвета",
    description AS "Описание"
FROM mv_sales_productdata
WHERE product_id = %(id)s;   
    """
    with connection.cursor() as cursor:
        cursor.execute(q, {"id": product_id})
        return dictfetchone(cursor)
        
        
        
        