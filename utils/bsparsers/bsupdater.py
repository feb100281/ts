# Скрипты для апдейта выписок

from django.conf import settings
from django.db import connection
import locale
locale.setlocale(locale.LC_TIME, "ru_RU.UTF-8")
import pandas as pd
import numpy as np
import re

from .bsparser import make_final_statemens, get_bs_details
from treasury.models import CfData
from corporate.models import Owners,BankAccount


# Грузим паттерны для выделения ставки НДС
from .vat_patterns import NO_VAT, VAT_RATE

from counterparties.models import Counterparty


 
# --------------------------
# Это последняя функция которая вставляет данные в модель CfData 
# --------------------------

def upsert_cf_data(df:pd.DataFrame) -> str:
    
    
    df = df.where(df.notna(), None)

    sql = """
        INSERT INTO treasury_cfdata (
            bs_id, doc_type, doc_numner, doc_date, date,
            dt, cr, tax_id, temp, cp_bs_name, intercompany,
            payer_account, reciver_account, vat_rate,
            cp_id, cp_final_id, owner_id, contract_id, cfitem_id, ba_id
        )
        VALUES (
            %(bs_id)s, %(doc_type)s, %(doc_numner)s, %(doc_date)s, %(date)s,
            %(dt)s, %(cr)s, %(tax_id)s, %(temp)s, %(cp_bs_name)s, %(intercompany)s,
            %(payer_account)s, %(reciver_account)s, %(vat_rate)s,
            %(cp_id)s, %(cp_final_id)s, %(owner_id)s, %(contract_id)s, %(cfitem_id)s, %(ba_id)s
        )
        ON CONFLICT (bs_id, doc_numner, date, dt, cr)
        DO UPDATE SET
            doc_type = EXCLUDED.doc_type,
            doc_date = EXCLUDED.doc_date,
            tax_id = EXCLUDED.tax_id,
            temp = EXCLUDED.temp,
            cp_bs_name = EXCLUDED.cp_bs_name,
            intercompany = EXCLUDED.intercompany,
            payer_account = EXCLUDED.payer_account,
            reciver_account = EXCLUDED.reciver_account,
            vat_rate = EXCLUDED.vat_rate,
            cp_id = EXCLUDED.cp_id,
            cp_final_id = EXCLUDED.cp_final_id,
            owner_id = EXCLUDED.owner_id,
            contract_id = EXCLUDED.contract_id,
            cfitem_id = EXCLUDED.cfitem_id,
            ba_id = EXCLUDED.ba_id
    """

    rows = df.to_dict(orient="records")

    with connection.cursor() as cursor:
        cursor.executemany(sql, rows)
    
    return f"Загружено {len(df)} операций"
    
    
# --------------------------
# Тут магия и геморой начинается ниже функции для авторазностки выписок 
# --------------------------
   
#Находим ставку НДС !!!! НУЖНО ДОДЕЛАТЬ ЭТО ГЕМОР
def find_vat_rate(df:pd.DataFrame)->pd.DataFrame:
    df = df.copy()
    s = df["temp"].fillna("").str.lower()
    
    #Выделяем ставку НДС
    df["vat_rate"] = None

    # без НДС → 0
    mask_no_vat = s.str.contains(NO_VAT, regex=True, flags=re.VERBOSE)
    df.loc[mask_no_vat, "vat_rate"] = 0

    # НДС со ставкой → число
    rates = s.str.extract(VAT_RATE, flags=re.VERBOSE)[0]
    mask_rate = rates.notna()
    df.loc[mask_rate, "vat_rate"] = rates[mask_rate].astype(int)
    
    return df

def find_contract():
    pass

def find_final_cp():
    pass

def find_cf_item():
    pass


# --------------------------
# Это основныя функция которая вызывается по кнопке migrate из админки и готовит df для записи в CfData
# --------------------------


def update_cf_data(filename,bs_id):
    
    bank, start_date,end_date,bb,eb = get_bs_details(filepath=filename)
    account_number = bank
    df = make_final_statemens(filename)   
    
    
    notifications = []
    
    company_name = "не найдено"
    bank_name = "не найдено"

    if account_number:
        ba = (
            BankAccount.objects
            .select_related("corporate", "bank")
            .filter(account=account_number)
            .first()
        )
        if ba:
            company_name = ba.corporate.name
            bank_name = ba.bank.name if ba.bank else "—"
            ba_id = ba.id
            owner_id = ba.corporate_id
    
    df = find_vat_rate(df).copy(deep=True)
    
    
    df['bs_id'] = int(bs_id)
    df['ba_id'] = int(ba_id)
    df['owner_id'] = int(owner_id)
    df['contract_id'] = None
    
    #Мапим cp по ИНН
    cp_map = dict(
        Counterparty.objects
        .values_list("tax_id", "id")
    )
    df["cp_id"] = df["tax_id"].map(cp_map).astype("Int64")
    df["cp_id"] = df["cp_id"].where(df["cp_id"].notna(), None)
    
    df['cp_final_id'] = None
    df['cfitem_id'] = None
    
    notifications.append(f"Компания: {company_name}; {bank_name} Расчетный счет № ...{account_number[-4:]} ")
    notifications.append(f"Период выписки с {start_date.strftime("%d.%m.%Y")} по {end_date.strftime("%d.%m.%Y")}")
    notifications.append(f"Исх остаток {bb:,.2f} рублей; остаток {eb:,.2f}")
    notifications.append(f"Обороты по dt {df.dt.sum():,.2f}; Обороты по cr {df.cr.sum():,.2f}")
    notifications.append(f"Количество операций по выписке: {len(df.index)}")
    notifications.append(upsert_cf_data(df))
    
    login_text =  '<br>'.join(notifications)
    
    return login_text
    


