import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv()

ENGINE = create_engine(
    f"postgresql+psycopg://"
    f"{os.getenv('DB_USER', 'django')}:"
    f"{os.getenv('DB_PASSWORD', 'strong_password')}"
    f"@{os.getenv('DB_HOST', 'localhost')}:"
    f"{os.getenv('DB_PORT', '5432')}/"
    f"{os.getenv('DB_NAME', 'django_db')}"
)

file24 = '/Users/pavelustenko/Desktop/Продажи/all_2024.xlsx'
file24csv = '/Users/pavelustenko/Desktop/Продажи/all_2024.csv'

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



def parse_xls(filename:str):
    df = pd.read_excel(filename)
    df = df.rename(columns=rename_map)
    df['created_date'] = pd.to_datetime(df['created_date'],errors='coerce')
    df['sale_date'] = pd.to_datetime(df['sale_date'],errors='coerce')
    cols_str = ["wb_article", "seller_article", "barcode"]
    cols_float = ['amount','quant','payout_amount']
    df[cols_str] = df[cols_str].fillna("").astype(str)
    df[cols_float] = df[cols_float].astype(float)
    
    return df

df_csv = pd.read_csv(
    file24csv,
    encoding="utf-8",
    sep=","
)

print(
    df_csv["Категория"]
    .astype("string")
    .str.contains("�", na=False)
    .sum()
)

# df = parse_xls(file24)

# print(df['category'].unique().tolist())


# df.to_sql('temp_sales',if_exists='replace',index=False,con=ENGINE)

# print('Записи:',len(df.index))
# print('Артикул WB:',df['Артикул WB'].nunique())
# print('Артикул продавца:',df['Артикул продавца'].nunique())
# print('Баркод:',df['Баркод'].nunique())
# print('Категория:',df['Категория'].nunique())
# print('Размер:',df['Размер'].nunique())



