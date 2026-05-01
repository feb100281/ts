from pathlib import Path
from pprint import pprint
import pandas as pd

p = Path("/Users/pavelustenko/Downloads/delivery")

FIELDS = {'Артикул':'sa_pid', 
          'Наименование':'name_file', 
          'Штрихкод/ EAN13':'barcode', 
          'Datamatrix':'datamatrix', 
          'Бренд':'brend',
          'Цвет':'color_file', 
          'Размер':'size_file', 
          'Пол':'gender_file', 
          'Количество':'qty', 
          'Цена':'price', 
          'Страна':'county', 
          'Состав':'composition',
          'Нетто за ед/кг':'netto_per_pack', 
          'Итого нетто /кг':'total_netto', 
          'Итого брутто /кг':'bruto_per_pack',
          'Номер коробки':'pack_id', 
          'Входящий документ':'document'
          }


d = {'Отгрузка_№_32_H&M_WB_1_ая_фура_001_3333_26471_ед_;_22_поддона_от.xlsx':'32', 
     'Отгрузка_№_35_H&M_WB_3_яя_фура_003_3333_38168_ед_32_поддона_от_15.xlsx':'35', 
     'Отгрузка_№_37_H&M_WB_3333_4_ая_002_7371_ед_и_5_ая_005.xlsx':'37', 
     'Отгрузка_№_44_H&M_WB_ДИСКОКЛАБ_1_ая_фура_и_H&M_WB_6_ой_Лот_остаток.xlsx':'44', 
     'Отгрузка_№_43_H^0M_WB_1_4_фуры_6_ЛОТ_3333_остаток_на_складе_7_под.xlsx':'43', 
     'Отгрузка_№_42_HM_WB_Банг_;_HM_WB_6_ой_ЛОТ;_MS_WB_Итого_15391ед_32.xlsx':'42', 
     'Отгрузка_№_34_H&M_WB_2_ая_фура_004_3333_13634_ед_15_поддонов_от.xlsx':'34', 
     'Отгрузка_№_33_H&M_WB_1_ая_фура_001_17751_ед_;_2_ая_фура_004_21348.xlsx':'33', 
     'Отгрузка_№_36_H&M_WB_3333_3_яя_003_4411_ед_и_4_ая_002_28433_ед_32.xlsx':'36'}

for i,v in d.items():
    print(i)
    xls = pd.ExcelFile(p/i)
    sheets = xls.sheet_names
    if 'Лист1' in sheets:
        df = xls.parse(sheet_name='Лист1',dtype=str,skiprows=3,usecols='A:Q')
    else:
        df =  df = xls.parse(sheet_name='Sheet1',dtype=str,skiprows=3,usecols='A:Q')
    df = df[df["Артикул"].notna() & (df["Артикул"].str.strip() != "")]
    df = df.rename(columns=FIELDS)
    df = df.apply(lambda col: col.str.strip())
    df.to_csv(p/f"lot6_{v}.csv")
    
    


