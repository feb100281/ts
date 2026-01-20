# Парсер банковских выписок для TS

import numpy as np
import pandas as pd


# Поля выписок
FIELDS_LIST = {
    "СекцияДокумент": "doc_type",
    "Номер": "doc_numner",
    "Дата": "doc_date",
    "Сумма": "amount",
    #'ПлательщикСчет':'payer_account',
    "Плательщик": "payer",
    "ПлательщикИНН": "payer_tax_id",
    "Плательщик1": "payer1",
    #'ПлательщикРасчСчет':'payer_account',
    "ПлательщикБанк1": "payer_bank1",
    "ПлательщикБанк2": "payer_bank2",
    "ПлательщикБИК": "payer_bik",
    "ПлательщикКорсчет": "payer_corr_acount",
    #'ПолучательСчет':'reciver_account',
    "ДатаПоступило": "recieve_date",
    "Получатель": "reciver",
    "ПолучательИНН": "reciver_tax_id",
    "Получатель1": "reciver1",
    #'ПолучательРасчСчет':'reciver_account',
    "ПолучательБанк1": "reciver_bank1",
    "ПолучательБанк2": "reciver_bank2",
    "ПолучательБИК": "reciver_bik",
    "ПолучательКорсчет": "reciver_corr_acount",
    "ВидОплаты": "payment_type",
    "СтатусСоставителя": "status_pmt",
    "ПоказательОснования": "usless_field",
    "ПоказательПериода": "usless_field2",
    "ПоказательНомера": "usless_field3",
    "ДатаСписано": "date_paid",
    "КодНазПлатежа": "pmt_code",
    "НазначениеПлатежа": "temp",  # оставим legacy name что бы не заморачиваться
}

# Поля которые нам нужны

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


# для теста передаем

wb = "/Users/pavelustenko/Desktop/Банковские_счета/Вайлдберриз.txt"
bk = "/Users/pavelustenko/Desktop/Банковские_счета/Банк Казани.txt"
sb = "/Users/pavelustenko/Desktop/Банковские_счета/Хлынов 293.txt"
sb1 = "/Users/pavelustenko/Desktop/Банковские_счета/Хлынов 370.txt"
ab = '/Users/pavelustenko/Desktop/Банковские_счета/Выписка_40702810802430004523_01.01.2024–18.01.2026.txt'

# Очень важно брать в дальнейшем из БД
ts_inn_default = ["9719052621"]
ts_banks_accounts = [
    "40702810300000000394",
    "40702810000010018499",
    "40702810200009105293",
    "40702810000009105370",
]


# Функция декодирования выписок 1С
def bs_decode(filepath) -> str:
    """
    Args:
        file (str): путь к файлу
    """
    try:
        with open(filepath, "r", encoding="windows-1251") as f:
            lines = f.readlines()
    except UnicodeDecodeError:
        with open(filepath, "r", encoding="cp866") as f:
            lines = f.readlines()

    return lines


# Функция которая делает словарь из декодированных выписок 1С
def bs_to_dict(filepath: str) -> pd.DataFrame:
    """
    Args:
        filepath (str): путь к файлу выписок
    Returns:
        df: df для работы
    """

    doc_index = []
    init_dic_list = []

    lines = bs_decode(filepath)

    # Находим номер манковского счета
    def get_bank_account(lines) -> str:
        account_id = ""
        for line in lines:
            line = line.strip()
            if "РасчСчет" in line:
                part = line.split("=")
                account_id = part[1].strip()
                break
        return account_id
    
    def get_bb(lines) -> float:
        b_ballance = 0.00
        for line in lines:
            line = line.strip()  
            if 'НачальныйОстаток' in line:
                part = line.split('=')
                try:
                    b_ballance = float(part[1].strip())
                except:
                    b_ballance = 0.00
                break
        return b_ballance
    
    def get_eb(lines) -> float:
        b_ballance = 0.00
        for line in lines:
            line = line.strip()  
            if 'КонечныйОстаток' in line:
                part = line.split('=')
                try:
                    b_ballance = float(part[1].strip())
                except:
                    b_ballance = 0.00
                break
        return b_ballance
    
    def get_start_date(lines) -> str:        
        date_start = ''
        for line in lines:
            line = line.strip()  
            if 'ДатаНачала' in line:
                part = line.split('=')
                date_start = part[1].strip()
                break
        return  pd.to_datetime(date_start,errors='coerce',dayfirst=True)
    
    def get_end_date(lines) -> str:
        date_start = ''
        for line in lines:
            line = line.strip()  
            if 'ДатаКонца' in line:
                part = line.split('=')
                date_start = part[1].strip()
                break
        return  pd.to_datetime(date_start,errors='coerce',dayfirst=True)

    for index, line in enumerate(lines):
        line = line.strip()
        if "СекцияДокумент" in line:
            doc_index.append(index)

    for index in doc_index:
        entry = {}
        for i in range(500):
            line = lines[int(index) + i].strip()
            if "КонецДокумента" in line:
                break
            if line == "":
                continue
            parts = line.split("=")
            entry[parts[0]] = parts[1]
        init_dic_list.append(entry)

    return pd.DataFrame(init_dic_list), get_bank_account(lines), get_start_date(lines), get_end_date(lines),get_bb(lines),get_eb(lines)

def get_bs_details(filepath):
    df, bank, start_date,end_date,bb,eb = bs_to_dict(filepath)
    return bank, start_date,end_date,bb,eb
    

# Здесь основная функция которая делает df для дальнейшей загрузки в базу данных
# В дальнейшем подставляем id из связанных моделей. НЕ ЗАБЫТЬ
def make_final_statemens(filepath: str, ts_inn=None, ts_banks_accounts=None):
    
    init_df, account_id, start_date, end_date,bb,eb = bs_to_dict(filepath)
    
    ts_inn = ts_inn if ts_inn else ts_inn_default

    payer_src = (
        "ПлательщикСчет"
        if "ПлательщикСчет" in init_df.columns
        else "ПлательщикРасчСчет"
    )
    reciver_src = (
        "ПолучательСчет"
        if "ПолучательСчет" in init_df.columns
        else "ПолучательРасчСчет"
    )

    init_df["payer_account"] = init_df[payer_src]
    init_df["reciver_account"] = init_df[reciver_src]

    init_df = init_df.rename(columns=FIELDS_LIST)

    def fix_str_amount(df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df["amount"] = (
            df["amount"]
            .astype(str)
            .str.replace(",", ".", regex=False)
            .str.replace("-", ".", regex=False)
            .str.strip()
            .astype(float)
        )
        return df

    # проверяем на float
    try:
        init_df["amount"] = init_df["amount"].astype(float)
    except (ValueError, TypeError):
        init_df = fix_str_amount(init_df)

    df = init_df.copy(deep=True)

    # делаем dt / cr
    df["dt"] = np.where(df.payer_account != account_id, df.amount, 0.0)
    df["cr"] = np.where(df.payer_account == account_id, df.amount, 0.0)

    # Конвертируем даты
    df["date"] = np.where(df["date_paid"].isna(), df.recieve_date, df.date_paid)

    s = df["date"]

    # если строки/объекты — чистим пробелы и превращаем пустые в NA
    s = s.astype("string").str.replace("\xa0", " ", regex=False).str.strip()
    s = s.replace({"": pd.NA, "nan": pd.NA, "None": pd.NA})

    df["date"] = s.combine_first(df["doc_date"].astype("string"))
    df.date = pd.to_datetime(df.date, errors="coerce", dayfirst=True)

    # ИНН Контрагента проставляем
    df["tax_id"] = np.where(df.dt == 0, df.reciver_tax_id, df.payer_tax_id)

    # Выделям intercompany trasactions
    df["intercompany"] = np.where(df["tax_id"].isin(ts_inn), True, False)

    # Выделяем контрагента по выписки
    if 'reciver1' in df.columns:
        df["cp_bs_name"] = np.where(df.dt == 0, df.reciver1, df.payer1)
    if 'reciver' in df.columns:
        df["cp_bs_name"] = np.where(df.dt == 0, df.reciver, df.payer)
    
    
    s = df["temp"].fillna("").str.lower()
    
    
        

    return df[FIELDS_TO_KEEP]


# df = make_final_statemens(sb)
# df.to_excel('tr.xlsx')
# print(df.columns)


# df, bank, start_date,end_date,bb,eb = make_final_statemens(ab)

# print(bank,start_date,end_date,bb,eb)
# # @property
#     def from_date(self):
#         date_start = ''
#         for line in self.lines:
#             line = line.strip()  
#             if 'ДатаНачала' in line:
#                 part = line.split('=')
#                 date_start = part[1].strip()
#                 break
#         return  datetime.strptime(date_start, "%d.%m.%Y").date()
    
#     @property
#     def to_date(self):
#         to_date = ''
#         for line in self.lines:
#             line = line.strip()  
#             if 'ДатаКонца' in line:
#                 part = line.split('=')
#                 to_date = part[1].strip()
#                 break
#         return  datetime.strptime(to_date, "%d.%m.%Y").date()
    
#     @property
#     def begining_ballance(self):
        # b_ballance = 0.00
        # for line in self.lines:
        #     line = line.strip()  
        #     if 'НачальныйОстаток' in line:
        #         part = line.split('=')
        #         try:
        #             b_ballance = float(part[1].strip())
        #         except:
        #             b_ballance = 0.00
        #         break
        # return b_ballance
    
#     @property
#     def end_ballance(self):
#         b_ballance = 0.00
#         for line in self.lines:
#             line = line.strip()  
#             if 'КонечныйОстаток' in line:
#                 part = line.split('=')
#                 try:
#                     b_ballance = float(part[1].strip())
#                 except:
#                     b_ballance = 0.00                
#         return b_ballance
    
#     @property
#     def get_bank_id(self):
#         bank_account = BankAccounts.objects.filter(account_id=self.account_id).values_list('id', flat=True).first()
#         return bank_account
    
#     @property
#     def get_company_id(self):
#         comp_account = BankAccounts.objects.filter(account_id=self.account_id).values_list('company_id', flat=True).first()
#         return comp_account



# df, bank_id = make_final_statemens(ab)



# print(df)
# print(bank_id)

# df.to_excel("tr.xlsx")
# для экселя
# ls = [wb, bk, sb, sb1]


# dfs = []
# for l in ls:
#     df = make_final_statemens(l)
#     dfs.append(df)

# dff = pd.concat(dfs)

# n_contr = dff["tax_id"].nunique()
# print(n_contr)


# dff.to_excel("tr.xlsx")
