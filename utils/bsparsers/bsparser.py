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
    "reciver_account",
]


# для теста передаем

wb = "/Users/pavelustenko/Desktop/Банковские_счета/Вайлдберриз.txt"
bk = "/Users/pavelustenko/Desktop/Банковские_счета/Банк Казани.txt"
sb = "/Users/pavelustenko/Desktop/Банковские_счета/Хлынов 293.txt"
sb1 = "/Users/pavelustenko/Desktop/Банковские_счета/Хлынов 370.txt"

# Очень важно брать в дальнейшем из БД
ts_inn = "9719052621"
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

    return pd.DataFrame(init_dic_list), get_bank_account(lines)


# Здесь основная функция которая делает df для дальнейшей загрузки в базу данных
# В дальнейшем подставляем id из связанных моделей. НЕ ЗАБЫТЬ
def make_final_statemens(filepath: str) -> pd.DataFrame:

    init_df, account_id = bs_to_dict(filepath)

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

    # print(init_df.columns)
    # print(account_id)

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
    df["intercompany"] = np.where(df.tax_id == ts_inn, True, False)

    # Выделяем контрагента по выписки
    df["cp_bs_name"] = np.where(df.dt == 0, df.reciver1, df.payer1)

    return df[FIELDS_TO_KEEP]

# для экселя
ls = [wb, bk, sb, sb1]


dfs = []
for l in ls:
    df = make_final_statemens(l)
    dfs.append(df)

dff = pd.concat(dfs)

n_contr = dff["tax_id"].nunique()
print(n_contr)


dff.to_excel("tr.xlsx")
