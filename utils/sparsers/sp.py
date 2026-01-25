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

# Пишем скрипт который ловит битые символы в категориях и исправляет

# Пишем скрипт который смотрит что за новые категории появились и сравнивает со старыми и если что предлагает пользователю добавляет новые категории

# Обновляем бренды по аналогии с категориями

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

# Обновляем таблицы m2m 

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

    
    