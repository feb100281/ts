import pandas as pd
from pprint import pprint
import duckdb

conn = duckdb.connect('/Users/pavelustenko/ts/data/analytics.duckdb')

file = '/Users/pavelustenko/Downloads/ALL DATA 1 LOT.xlsx'

xls = pd.ExcelFile(file)

print(xls.sheet_names)


rename_map = {
    'код товара/ работ, услуг': 'product_code',
    'наименование товара (описание выполненных работ, оказанных услуг), имущественного права': 'product_name',
    'количество (объем)': 'qty',
    'quantity': 'qty',
    'цена (тариф) за единицу измерения': 'price',
    'стоимость товаров (работ, услуг), имущественных прав без налога всего': 'amount_without_vat',
    'налоговая ставка': 'vat_rate',
    'сумма налога, предъявляемая покупателю': 'vat_amount',
    'стоимость товаров (работ, услуг), имущественных прав с налогом всего': 'amount_with_vat',
    'страна происхождения товара': 'country',

    # твой зоопарк 👇
    '10 number': 'article',
    'article+size': 'article_size',
    'size': 'size',

    'unit cost': 'unit_cost',
    'unit cost without vat': 'unit_cost_wo_vat',
    'vat per unit': 'vat_per_unit',
    'amount goods without vat': 'amount_goods_wo_vat',
    'amount': 'amount_total',

    'invoice': 'invoice'
}
conn.execute("drop table if exists invoices_lot1")
conn.commit()
for sheet in xls.sheet_names:
    if sheet.casefold().startswith('invoice'):
        parts = sheet.split(' ')
        df = xls.parse(sheet_name=sheet,dtype=str)
        df['invoice'] = parts[1]
        
        df.columns = (
            df.columns
            .str.replace(r'\s*\n\s*', ' ', regex=True)  # убираем переносы строк
            .str.replace(r'-\s*', '', regex=True)       # убираем разрывы слов типа "имущест-\nвенных"
            .str.strip()                               # убираем лишние пробелы
            .str.lower()                               # в нижний регистр
        )
        print(parts[1])
        print(df.columns)
        
        df = df.rename(columns=rename_map)
        df = df[['invoice','product_code','product_name','article','vat_rate','qty','price','unit_cost_wo_vat']]
        
        
        print(parts[1])
        print(df.columns)
        df.to_sql('invoices_lot1',conn,index=False,if_exists='append')
        
        
        
    else:
        continue

conn.execute("delete from analytics.main.invoices_lot1 where product_code is null")
conn.commit()