# Парсим xls
import numpy as np
import pandas as pd

file = '/Users/pavelustenko/Desktop/Банковские_счета/БЖФ.xlsx'
file1 = '/Users/pavelustenko/Desktop/Банковские_счета/Совкомбанк.xlsx'

FIELDS_TO_KEEP = [
    "doc_type",
    "doc_numner",
    "doc_date",
    "date",
    "dt",
    "cr",
    "tax_id",
    "temp",
    "cp_bs_name",
    "intercompany",
    "payer_account",
    "reciver_account"
    
]


def get_acc(filename):
    df = pd.read_excel(filename, nrows=10,header=None)
    acc:str = df.iloc[5, 0]
    acc = acc.replace('Отбор: Банковские счета Равно "',"").replace(', АО "Банк БЖФ""','').replace(', Филиал "Корпоративный" ПАО "Совкомбанк""','').strip()
    # Отбор: Банковские счета Равно "40702810410000104161, АО "Банк БЖФ""
    return acc

def get_bb(filename):
    df = pd.read_excel(filename, nrows=11,header=None)
    return df.iloc[9, 11]

def make_df(filename)->pd.DataFrame:
    df = pd.read_excel(
    filename,
    skiprows=9,   # пропустить первые 10 строк
    skipfooter=1,  # пропустить последнюю строку
    names=["date", "_temp", "_anal_dt", "_anal_cr","_dt_acc","dt","_cr_acc","_cr",'cr','col10','col11','col12']
    )
    
    return df[['date','_temp','_anal_dt','_anal_cr','dt','cr']]

def adjust_df(filename)->pd.DataFrame:
    
    
    acc_number = get_acc(filename)
    bb = get_bb(filename)
    
    
    df:pd.DataFrame = make_df(filename)
    
    df[["_doc", "temp"]] = (
        df["_temp"]
        .str.split("\n", n=1, expand=True)
        .apply(lambda x: x.str.strip())
    )
    
    
    df['_len_dt'] = df["_anal_dt"].str.split("\n").str.len().fillna(0).astype(int)
    df['_len_cr'] = df["_anal_cr"].str.split("\n").str.len().fillna(0).astype(int)
    
    
    parts_cr = (
    df["_anal_cr"]
    .fillna("")
    .astype("string")                 # <-- важно
    .str.split("\n", n=2, expand=True)
    .reindex(columns=[0, 1, 2])
)

    parts_cr = parts_cr.astype("string").apply(lambda c: c.str.strip())
    parts_cr = parts_cr.replace({"": None, pd.NA: None})

    df[["_cp_name_cr", "_contract_number_cr", "_justification_cr"]] = parts_cr
    # df[['_cp_name_cr','_contract_number_cr','_justification_cr']] = (df['_anal_cr']
    #    .str.split("\n", n=2, expand=True)
    #    .apply(lambda x: x.str.strip())
    # )
    
    # df[['_cp_name_dt','_contract_number_dt','_justification_dt']] = (df['_anal_dt']
    #    .str.split("\n", n=2, expand=True)
    #    .apply(lambda x: x.str.strip())
    # )
    
    parts_dt = (
    df["_anal_dt"]
    .fillna("")
    .astype("string")                 # <-- важно
    .str.split("\n", n=2, expand=True)
    .reindex(columns=[0, 1, 2])
)

    parts_dt = parts_dt.astype("string").apply(lambda c: c.str.strip())
    parts_dt = parts_dt.replace({"": None, pd.NA: None})

    df[["_cp_name_dt", "_contract_number_dt", "_justification_dt"]] = parts_dt
    
    
    #Парсим контрагента где 3 и 3 
    
    df["cp_name"] = np.where(
    df["_len_cr"].to_numpy() == 3,
    df["_cp_name_cr"].to_numpy(),
    np.where(
        df["_len_dt"].to_numpy() == 3,
        df["_cp_name_dt"].to_numpy(),
        np.nan
        )
    )
    
    #Парсим внутреннии перемещения
    df["tax_id"] = None
    df["tax_id"] = np.where(
    df["_contract_number_dt"].str.startswith("Внутреннее", na=False)
    | df["_contract_number_cr"].str.startswith("Внутреннее", na=False),
    "9719052621",
    df["tax_id"]
    )
    
    df["cp_name"] = np.where(
    df["_contract_number_dt"].str.startswith("Внутреннее", na=False)
    | df["_contract_number_cr"].str.startswith("Внутреннее", na=False),
    "Трендсеттер ООО",
    df["cp_name"]
    )
    
    df["tax_id"] = np.where(
    df["_contract_number_dt"].str.startswith("Конвертация валюты", na=False),
    
    "9719052621",
    df["tax_id"]
    )
    
    df["cp_name"] = np.where(
    df["_contract_number_dt"].str.startswith("Конвертация валюты", na=False),
   
    "Трендсеттер ООО",
    df["cp_name"]
    )
    
    
    df["cp_name"] = np.where(
        df["_contract_number_cr"].isin(['Расходы на услуги банков']),
        df['_cp_name_cr'], df["cp_name"]
    )
    
    df["cp_name"] = np.where(
    df["_contract_number_cr"].isin(["Прочие налоги и сборы"])
    & df["_cp_name_dt"].isna(),
    "ИФНС",
    df["cp_name"]
    )
    
    df["cp_name"] = np.where(
    df["_contract_number_cr"].isin(["Прочие налоги и сборы"])
    & df["_cp_name_dt"].isin(['Налог (взносы): начислено / уплачено']),
    "ФСС",
    df["cp_name"]
    )
    
    df["tax_id"] = np.where(
    df["_contract_number_cr"].isin(["Прочие налоги и сборы"])
    & df["_cp_name_dt"].isna(),
    "7727406020",
    df["tax_id"]
    )
    
    df["tax_id"] = np.where(
    df["_contract_number_cr"].isin(["Прочие налоги и сборы"])
    & df["_cp_name_dt"].isin(['Налог (взносы): начислено / уплачено']),
    "7703363868",
    df["tax_id"]
    )
    
    df["employee_name"] = (
    df["temp"]
    .str.extract(r"на счет\s+([А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ][а-яё]+){2})",
                 expand=False)
    )
    
    
    rpc = {
        'Мурадяна Каринэ Арутюновны':"Мурадян Каринэ Арутюновна", 
           'Бердникова Сергея Алексеевича':'Бердников Сергей Алексеевич', 
           'Гавшина Богдана Сергеевича':'Гавшин Богдан Сергеевич', 
           'Юдиной Елены Геннадиевны':'Юдина Елена Геннадиевна', 
           'Амунца Александра Дмитриевича':'Амунц Александр Дмитриевич', 
           'Малая Максима Александровича':'Малай Максим Александрович', 
           'Сидоровой Ксении Дмитриевны':'Сидорова Ксения Дмитриевна', 
           'Котовской Карины Владимировны':'Котовская Карина Владимировна', 
           'Ромашенко Виктории Владимировны':'Ромашенко Виктория Владимировна', 
           'Переверзева Дмитрия Владимировича':'Переверзев Дмитрий Владимирович', 
           'Кузина Максима Евгеньевича':'Кузин Максим Евгеньевич'
           }
    
    df["cp_name"] = df["cp_name"].fillna(
        df["employee_name"].map(rpc)
        )
    
    
    df["cp_name"] = np.where(
        df['_contract_number_cr'].isin(['Выдача подотчетных сумм']),
        df['_cp_name_dt'],
        df["cp_name"]
    )
    
    df["cp_name"] = np.where(
        df['_contract_number_dt'].isin(['Получение кредитов и займов','Поступления от погашения займов']),
        df['_cp_name_cr'],
        df["cp_name"]
    )
    
    df["cp_name"] = np.where(
        df['_contract_number_cr'].isin(['Погашение кредитов и займов',"Выплата процентов по кредитам и займам"]),
        df['_cp_name_dt'],
        df["cp_name"]
    )
    
    df["cp_name"] = np.where(
    df["_cp_name_cr"].str.startswith("Проценты к получению, уплате", na=False),
   
    df['_cp_name_dt'],
    df["cp_name"]
    )
    
    
    rpls = {     
        '40702810512010618308, Филиал "Корпоративный" ПАО "Совкомбанк"':"СОВКОМБАНК ПАО","Хримян Артур Гагикович":"ХРИМЯН АРТУР ГАГИКОВИЧ",   
        "Трендсеттер ООО":"ТРЕНДСЕТТЕР OOO","ИФНС":"ИФНС","ФСС":"ФСС ПО Г. МОСКВЕ И МОСКОВСКОЙ ОБЛАСТИ",'40702810410000104161, АО "Банк БЖФ"':'БАНК БЖФ АО','ВАЙЛДБЕРРИЗ ООО':'ВАЙЛДБЕРРИЗ ООО','Мурадян Каринэ Арутюновна':'МУРАДЯН КАРИНЭ АРТЮНОВНА','Бердников Сергей Алексеевич':'БЕРДНИКОВ СЕРГЕЙ АЛЕКСЕЕВИЧ','Талипова Галия Гаяновна':'ТАЛИПОВА ГАЛИЯ ГАЯНОВНА ИП','ЗАО "Экспорт Файненс"':'ЭКСПОРТ ФИНАНС ЗАО','МОДУЛЬ-СОФТ ООО':'МОДУЛЬ-СОФТ ООО','Волга-Созь-Сервис ООО':'ВОЛГА-СВЯЗЬ-СЕРВИС ООО','ПРОИЗВОДСТВЕННАЯ ФИРМА СКБ КОНТУР НАО':'СКБ КОНТУР ПФ АО','Халипский Сергей Николаевич (ИП)':'ХАЛИПСКИЙ СЕРГЕЙ НИКОЛАЕВИЧ ИП','СПЕЦГАЗСТРОЙ ООО':'СПЕЦГАЗСТРОЙ ООО','Окишев Евгений Александрович (ИП)':'ОКИШЕВ ЕВГЕНИЙ АЛЕКСАНДРОВИЧ ИП','ЗАО "Арминвест"':'АРМИНВЕСТ ЗАО','БЕЛЫЙ МЕДВЕДЬ ООО':'БЕЛЫЙ МЕДВЕДЬ ООО','ОПЕРАТОР-ЦРПТ ООО':'ОПЕРАТОР-ЦРПТ ООО','НЬЮ РИВЕР ООО':'НЬЮ РИВЕР ООО','ЭР Софт ООО':'ЭР СОФТ ООО','Юридическая фирма Априори ООО':'ЮРИДИЧЕСКАЯ ФИРМА АПРИОРИ ООО','Межрегиональное операционное УФК (Федеральная служба по интеллектуальной собственности)':'ФЕДЕРАЛЬНАЯ СЛУЖБА ПО ИНТЕЛЛЕКТУАЛЬНОЙ СОБСТВЕННОСТИ','ГК ГАЛА-ПРОДЖЕКТ ООО':'ГК ГАЛА-ПРОДЖЕКТ ООО','МФ КАПИТАЛ ООО':'МФ КАПИТАЛ ООО','МЕГАМОЛСТРОЙ ООО':'МЕГАМОЛСТРОЙ ООО','РВБ ООО':'РВБ ООО','МИНАСЯН МАКСИМ ВАДИМОВИЧ':'МИНАСЯН МАКСИМ ВАДИМОВИЧ','Мосолов Артём Сергеевич':'МОСОЛОВ АРТЁМ СЕРГЕЕВИЧ','БРУНОЯМ ООО':'БРУНОЯМ ООО','СУ-43 ООО':'СУ-43 ООО','Гавшин Богдан Сергеевич':'ГАВШИН БОГДАН СЕРГЕЕВИЧ','Юдина Елена Геннадиевна':'ЮДИНА ЕЛЕНА ГЕННАДИЕВНАЯ','ЗАО "БРЕНДДЕВЕЛОПМЕНТ"':'БРЕНДДЕВЕЛОПМЕНТ ЗАО','СИТИЛИНК ООО':'СИТИЛИНК ООО','ООО ЛУКОЙЛ-ИНТЕР-КАРД':'ЛУКОЙЛ-ИНТЕР-КАРД ООО','УК ПРОМИНВЕСТ ГРУПП ООО':'УК ПРОМИНВЕСТ ГРУПП ООО','Кириченко Денис Владимирович':'КИРИЧЕНКО ДЕНИС ВЛАДИМИРОВИЧ','МПСТАТС ООО':'МПСТАТС ООО','ХЭДХАНТЕР ООО':'ХЭДХАНТЕР ООО','МИКРОКРЕДИТНАЯ КОМПАНИЯ ВБ ФИНАНС ООО':'МКК ВБ ФИНАНС ООО','СОЮЗ ЗАСТРОЙЩИКОВ МСК ООО':'СОЮЗ ЗАСТРОЙЩИКОВ МСК ООО','Амунц Александр Дмитриевич':'АМУНЦ АЛЕКСАНДР ДМИТРИЕВИЧ','Малай Максим Александрович':'МАЛАЙ МАКСИМ АЛЕКСАНДРОВИЧ','ИП Васильев Данил Андреевич':'ВАСИЛЬЕВ ДАНИЛА АНДРЕЕВИЧ ИП','Сидорова Ксения Дмитриевна':'СИДОРОВА КСЕНИЯ ДМИТРИЕВНА','Котовская Карина Владимировна':'КОТОВСКАЯ КАРИНА ВЛАДИМИРОВНА','КМТ-СЕРВИС ООО':'КМТ СЕРВИС ООО','ФЕДЕРАЛЬНАЯ ТАМОЖЕННАЯ СЛУЖБА ФГКУ':'ФЕДЕРАЛЬНАЯ ТАМОЖЕННАЯ СЛУЖБА','ГС1 РУС':'ЮНИСКАН/ГС1 РУС','Шерстнева Татьяна Анатольевна':'ШЕРСТНЕВА ТАТЬЯНА АНАТОЛЬЕВНА ИП','ВАКА ООО':'ВАКА ООО','Новосибирское карьероуправление АО':'НОВОСИБИРСКОЕ КАРЬЕРОУПРАВЛЕНИЕ АО','АВТОКОМ ООО':'АВТОКОМ ООО','ГАЛА ООО':'ГК ГАЛА-ПРОДЖЕКТ ООО','АМЕРИАБАНК ЗАО':'АМЕРИАБАНК ЗАО','ИП Соколова Евгения Геннадьевна':'СОКОЛОВА ЕВГЕНИЯ ГЕННАДЬЕВНА ИП','Ромашенко Виктория Владимировна':'РОМАШЕНКО ВИКТОРИЯ ВЛАДИМИРОВНА','Валовая Юлия Игоревна':'ВАЛОВАЯ ЮЛИЯ ИГОРЕВНА','АИ ВЭЙ ООО':'АИ ВЭЙ ООО','Гостев Михаил Алексеевич':'ГОСТЕВ МИХАИЛ АЛЕКСЕЕВИЧ ИП','ПРОАКТИОН ООО':'ПРОАКТИОН ООО','Тимохина Виктория Викторовна':'ТИМОХИНА ВИКТОРИЯ ВИКТОРОВНА ИП','НДЛ ООО':'НДЛ ООО','ПРОГРЕСС-ГРУПП ООО':'ПРОГРЕСС-ГРУПП ООО','Нотариус Булатова Ирина Борисовна':'НОТАРИУС БУЛАТОВА И. Б.','ФЭШН ФЭКТОРИ ШКОЛА ЛЮДМИЛЫ НОРСОЯН ООО':'ФЭШН ФЭКТОРИ ШКОЛА ЛЮДМИЛЫ НОРСОЯН ООО','Переверзев Дмитрий Владимирович':'ПЕРЕВЕРЗЕВ ДМИТРИЙ ВЛАДИМИРОВИЧ','ЭКО НЭЙЧЕР ПРОДАКТС ООО':'ЭКО НЭЙЧЕР ПРОДАКТС ООО','Кузин Максим Евгеньевич':'КУЗИН МАКСИМ ЕВГЕНЬЕВИЧ','ВИИИК ООО':'ВИИИК ООО'
    
    }
    df["cp_name_final"] = df["cp_name"].map(rpls)
    
    df['dt'] = df['dt'].fillna(0).astype(float)
    df['cr'] = df['cr'].fillna(0).astype(float)
    
    def find_doc_number(text:str)->str:
        parts = text.split('от')
        part:str = parts[0]
        part = part.replace("Списание с расчетного счета",'').replace('Поступление на расчетный счет','').strip()
        return part
    
    df['doc_type'] = np.where(
        df['_doc'].str.startswith("Списание"),"Списание","Поступление"
    )
    df['doc_numner'] = df['_doc'].apply(find_doc_number)
    
    df['doc_numner'] = df['doc_numner'] + '-'+df['dt'].astype(str)+df['cr'].astype(str)
    
    df['doc_date'] = df['date']
    
    df['date'] = pd.to_datetime(df['date'],dayfirst=True,errors='coerce')
    
    df['cp_bs_name'] = df['cp_name_final']
    
    df['intercompany'] = np.where(
        df['cp_name_final'] == 'ТРЕНДСЕТТЕР OOO',True,False
    )
    
    df['payer_account'] = None
    df['reciver_account'] = None
    
    # df[["_doc", "temp"]] = (
    #     df["_temp"]
    #     .str.split("\n", n=1, expand=True)
    #     .apply(lambda x: x.str.strip())
    # )
    
    eb = round(df['dt'].sum() - df['cr'].sum() + bb,0)
    
    
    return df[FIELDS_TO_KEEP],acc_number,df['date'].min(),df['date'].max(),bb,eb


