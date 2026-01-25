import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv()

files = [
    '/Users/pavelustenko/Desktop/Продажи/all_2024.csv',
    '/Users/pavelustenko/Desktop/Продажи/part_1_2025.csv',
    '/Users/pavelustenko/Desktop/Продажи/part_2_2025.csv',
    '/Users/pavelustenko/Desktop/Продажи/jan_2026.csv'
    
]


ENGINE = create_engine(
    f"postgresql+psycopg://"
    f"{os.getenv('DB_USER', 'django')}:"
    f"{os.getenv('DB_PASSWORD', 'strong_password')}"
    f"@{os.getenv('DB_HOST', 'localhost')}:"
    f"{os.getenv('DB_PORT', '5432')}/"
    f"{os.getenv('DB_NAME', 'django_db')}"
)



rename_map = {
    "Дата формирования": "created_date",
    "Дата продажи": "sale_date",
    "Артикул WB": "wb_article",
    "Артикул продавца": "seller_article",
    "Баркод": "barcode",
    "Категория": "category",
    "Бренд": "brand",
    "Размер": "size",
    "Цена продажи": "amount",
    "Страна": "country",
    "Идентификатор заказа": "order_id",
    "Кол-во": "quant",
    "К перечислению": "payout_amount",
    "Тип транзакции": "transaction_type",
    "Склад": "warehouse",
}



def parse_xls(filenames: list[str]) -> pd.DataFrame:
    dfs = []

    for file in filenames:
        df = pd.read_csv(
            file,
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

        dfs.append(df)

    return pd.concat(dfs, ignore_index=True)

# df  = parse_xls(files)

# df.to_sql('fixed_bars',index=False,con=ENGINE,if_exists='replace')




