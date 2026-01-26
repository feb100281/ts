# Данный скрипт парсит данные по продажам
from historical import ENGINE,rename_map
import pandas as pd


def parse_file(filename):
    df = pd.read_csv(
            filename,
            encoding="utf-8",
            sep=",",
            dtype={
                "Артикул WB": "string",
                "Артикул продавца": "string",
                "Баркод": "string",
            },
        )

    df = df.rename(columns=rename_map)

    df["created_date"] = pd.to_datetime(df["created_date"], errors="coerce")
    df["sale_date"] = pd.to_datetime(df["sale_date"], errors="coerce")

    cols_str = ["wb_article", "seller_article", "barcode"]
    cols_float = ["amount", "quant", "payout_amount"]

    df[cols_str] = df[cols_str].astype("string")
    df[cols_str] = df[cols_str].apply(lambda s: s.str.strip())

    for c in cols_float:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    
    return df

def make_temp_table(filename):    
    df = parse_file(filename)
    df.to_sql("temp_sales",con=ENGINE,index=False,if_exists='replace')
    return f"Сделана временная таблица. {len(df.index)} строк записано"

# Пишем скрипт который ловит битые символы в категориях и исправляет сомнительно но ок

# Пишем скрипт который смотрит что за новые категории появились и сравнивает со старыми и если что предлагает пользователю добавляет новые категории

# Обновляем бренды по аналогии с категориями # Не забываем про исключения

# Если появились новые wb_article вставляем 
def update_wb_articles():
    q = """
    INSERT INTO sales_product (
    wb_article
    )
    SELECT DISTINCT
    wb_article from temp_sales
    ON CONFLICT (wb_article) DO NOTHING
    RETURNING (xmax = 0) AS inserted;
    """

# Обновляем с сайта вайлдбериз фукцией из wbp

# Обязательно обновляем MVs

# Обновляем страны 

# Обновляем размеры проверяем на ��

# Обновляем склады проверяем на ��

# Обновляем закзазы orders проверяем на ��

# Обновляем баркоды orders проверяем на ��

# Обновляем sellersSku orders проверяем на ��


# ---------------------
# Обновляем таблицы m2m 
# ---------------------

# public.sales_product_barcodes

# INSERT INTO sales_product_barcodes(product_id,barcode_id)
#     select distinct
#     t.id as product_id,
#     c.id as barcode_id
#     from temp_sales as f
#     JOIN sales_product as t on t.wb_article = f.wb_article
#     join sales_barcode as c on c.barcode = f.barcode
#     ON CONFLICT (product_id,barcode_id) DO NOTHING 

# public.sales_product_brands

# INSERT INTO sales_product_barcodes(product_id,barcode_id)
#     select distinct
#     t.id as product_id,
#     c.id as barcode_id
#     from temp_sales as f
#     JOIN sales_product as t on t.wb_article = f.wb_article
#     join sales_barcode as c on c.barcode = f.barcode
#     ON CONFLICT (product_id,barcode_id) DO NOTHING 

# public.sales_product_categories

def update_product_cat():
    q = """
    INSERT INTO sales_product_categories(product_id,category_id)
    select distinct
    t.id as product_id,
    c.id as category_id
    from temp_sales as f
    JOIN sales_product as t on t.wb_article = f.wb_article
    join sales_category as c on c."name" = f.category
    ON CONFLICT (product_id,category_id) DO NOTHING    
    
    """

# public.sales_product_sellersku

# INSERT INTO sales_product_sellersku(product_id,sellersku_id)
#     select distinct
#     t.id as product_id,
#     c.id as sellersku_id
#     from fixed_bars as f
#     JOIN sales_product as t on t.wb_article = f.wb_article
#     join sales_sellersku as c on c.seller_article = f.seller_article
#     ON CONFLICT (product_id,sellersku_id) DO NOTHING    


# public.sales_product_sizes

# INSERT INTO sales_product_sizes(product_id,size_id)
#     select distinct
#     t.id as product_id,
#     c.id as size_id
#     from fixed_bars as f
#     JOIN sales_product as t on t.wb_article = f.wb_article
#     join sales_size as c on c.size = f.size
#     ON CONFLICT (product_id,size_id) DO NOTHING    


# ---------------------
# ФИНАЛЬНАЯ ТАБЛИЦА С ПРДАЖАМИ
# ---------------------


# СТИРАЕМ OVERLAPS

# ДЕЛАЕМ ЗАПРОС НА INSERT
q = """
INSERT into sales_salesdata(created_date,sale_date,product_id,
barcode_id,brand_id,size_id,country_id,order_id,warehouse_id,
amount_dt,amount_cr,quant_dt,quant_cr,dt,cr,transaction_type)
SELECT 
  t.created_date,
  t.sale_date,
  p.id  AS product_id,
  bc.id AS barcode_id,
  b.id  AS brand_id,
  s.id  AS size_id,
  c.id  AS country_id,
  o.id  AS order_id,
  w.id  AS warehouse_id,
  case when t.transaction_type != 'Возврат' then t.amount else 0 end as amount_dt,
  case when t.transaction_type = 'Возврат' then t.amount else 0 end as amount_cr,
  case when t.transaction_type != 'Возврат' then t.quant else 0 end as quant_dt,
  case when t.transaction_type = 'Возврат' then t.quant else 0 end as quant_cr,
  case when t.transaction_type != 'Возврат' then t.payout_amount else 0 end as dt,
  case when t.transaction_type = 'Возврат' then t.payout_amount else 0 end as cr,
  t.transaction_type
FROM temp_sales AS t
LEFT JOIN sales_product        AS p  ON p.wb_article = t.wb_article
LEFT JOIN sales_brand          AS b  ON b.name       = t.brand
LEFT JOIN sales_barcode        AS bc ON bc.barcode   = t.barcode
LEFT JOIN sales_size           AS s  ON s.size       = t.size
LEFT JOIN corporate_countries  AS c  ON c.regex_patterns IS NOT NULL  AND t.country ~* c.regex_patterns
LEFT JOIN sales_order          AS o  ON o.code       = t.order_id
LEFT JOIN sales_warehouse      AS w  ON w.name       = t.warehouse;
    
"""