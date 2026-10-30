import pandas as pd
from conns import ENGINE

file1 = '/Users/pavelustenko/Downloads/CALCULATION COST-DISKO CLUB 1-я фура.xlsx' 
file2 = '/Users/pavelustenko/Downloads/ФУРА 1 ДИСКО.xlsx'

sheets_list = ['Выехало из Армении', 
               'Промежуточные подсчеты', 
               'Сопоставление',
               'Sheet1', 
               'Sheet2', 
               'Sheet7', 
               'COST', 
               'Sheet6']

def parce_xls(file,sheet)->pd.DataFrame:
    
   
    df = pd.read_excel(
        file,
        sheet_name=sheet,
        dtype={
            "Артикул": str,
            "Штрихкод/ EAN13": str
        }
    )
    return df
    
df = parce_xls(file2,'Выехало из Армении')
c = ['Артикул', 'Наименование', 'Штрихкод/ EAN13', 'Бренд', 'Цвет', 'Размер', 'Пол', 'Количество', 'Цена', 'Страна', 'Состав', 'Входящий документ']

print(df['Артикул'].nunique())
print(df['Штрихкод/ EAN13'].nunique())
print(len(
    df[['Артикул', 'Штрихкод/ EAN13']]
    .drop_duplicates()
))
print(len(df))

dff = df.pivot_table(
    index=['Артикул','Наименование'],
    values='Количество',
    aggfunc='sum'
).reset_index()

dff['Артикул инвойс'] = (
    dff['Артикул']
    .astype(str)
    .str[1:7] + '72023'
)

reconsile = dff.pivot_table(
    index=['Артикул инвойс','Артикул','Наименование'],
    values='Количество',
    aggfunc='sum'
)

tmp = reconsile.reset_index()

problem_rows = tmp[
    tmp.groupby('Артикул инвойс')['Артикул']
       .transform('nunique') > 1
]

problem_rows = problem_rows.set_index(['Артикул инвойс','Артикул'])

problem_rows.to_excel('1.xlsx')

dfff = dff.reset_index()

dfff = dfff.pivot_table(
    index='Артикул инвойс',
    values='Количество',
    aggfunc='sum'
)



df_recon = pd.read_excel(
        file2,
        sheet_name='Сопоставление',
        dtype={
            "Инвойс Артикул": str,            
        }
    )

df_recon = df_recon.rename(columns={'Инвойс Артикул':"Артикул инвойс"})

df_final = pd.merge(
    dfff,
    df_recon,
    how='outer',
    on='Артикул инвойс'
)
df_fin = df_final[["Артикул инвойс","Количество","Фактичкский qty","Инвойс qty"]].fillna(0)
df_fin['∆ Кол-во - Факт qty'] = df_fin['Количество'] - df_fin['Фактичкский qty']
df_fin['∆ Факт qty - Инвойс qty'] = df_fin['Фактичкский qty'] - df_fin['Инвойс qty']

print(dff['Артикул инвойс'].nunique())
print(df_recon['Артикул инвойс'].nunique())
# print(df_fin)

init = set(dff['Артикул инвойс'])
target = set(df_recon['Артикул инвойс'])

print("Совпадают полностью:", init == target)
print("Нет в target:", len(init - target))
print("Лишние в target:", len(target - init))


# df_fin.to_excel('1.xlsx')

costs_cols = ['N', 'Артикул', 'Статус проверки подбора', 'Номенклатура', 
              'Вид номенклатуры', 'Код ТНВЭД', 'GGG', 'Код ТН ВЭД', 'Характеристика', 
              'EAN', 'Размер', 'Цвет', 'GTIN, записываемый эмитентом в КиЗ ГИСМ', 
              'Количество', 'Упаковка', 'Ед. изм.', 'Вид цены', 'Цена', 'Сумма', 
              'Ставка НДС', 'НДС', 'Сумма с НДС', 'Сумма взаиморасчетов', 
              'Страна происхождения', 'Склад', 'Подразделение', 
              'ooo', 5875.513555876647, 
              'kk', 'kk.1', 'kk.2', 6616.999999999419, 
              1.126199427006976, 'Unnamed: 33', 
              'Цена/ на единицу', 'Цена/ обший', 
              'Транспорт до Армения/ на единицу', 
              'Транспорт до Армения/ обший', 
              'НДС/на единицу', 'НДС/обший', 
              'Маркировка/UNIT', 'Маркировка/Обший', 
              'Страховка импорт/ на единицу', 
              'Страховка импорт/ обший', 
              'Декларация /на единицу', 'Декларация/обший', 'Страховка експорт/на единицу', 
              'Страховка експорт/обший', 'Брокерские экспорт/на единицу', 
              'Брокерские услуги экспорт/ на единицу', 
              'Грузия, Ларс/на единицу', 'Грузия, Ларс/обший', 
              'Маркирова ЧЗ/на единицу', 'Маркирова ЧЗ/Обший', 
              'Транспорт до РФ/ на единицу', 'Транспорт до РФ/ обший', 
              'COST/на единицу', 'COST/обший']


df_cost = pd.read_excel(
        file1,
        sheet_name='COST',
        skiprows=1,
        skipfooter=1,
        dtype={
            "Артикул": str,   
            "Код ТНВЭД":str,
            "Код ТН ВЭД":str,
            "EAN":str 
        }
    )

print(df_cost['Артикул'].nunique())
print(len(df_cost))

costs_art = set(df_cost['Артикул'])
target_art = set(df_fin['Артикул инвойс'])

print("Нет в target:", len(costs_art - target))
print("Лишние в target:", len(costs_art - init))


print("Нет в Промежуточные подсчёты:", len(init - costs_art))
print("Нет в Cопоставлении:", len(target - costs_art))
print("Нет в Объедененной таблицы:", len(target_art - costs_art))

print("Лишние артикли в COSTS:", len(costs_art-target_art))

q = """
select 
 nm_id,
 payload_raw ->> 'vendorCode' as vendorCode

from wb_raw.raw_cards 
"""

cards = pd.read_sql(q,ENGINE)
vendor_code = set(cards['vendorcode'].astype(str))

a = missing = set(map(str, costs_art)) - vendor_code
print(len(a))