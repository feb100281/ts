# cards/reconciliation.py

import re
from decimal import Decimal
import tempfile
import os

import pandas as pd
from django.db.models import Sum

from cards.models import UpdDocument
from .reporting.reconcile.report_builder import build_reconciliation_report

# Константы и вспомогательные функции остаются теми же
IGNORE_COUNTERPARTIES = {
    "ВАЙЛДБЕРРИЗ ООО", "ЗДОРОВАЯ ВОДА ООО", "РВБ ООО",
    "ТОРГОВЫЙ ДОМ ГЛАВРУС-РЕКЛАМА ООО", "ВАНПЛАСТ ООО",
    "ООО ЛУКОЙЛ-ИНТЕР-КАРД", "СИТИЛИНК ООО", "ТКС ООО",
    "Чащина Татьяна Владимировна", "СПЕЦМОНТАЖ ТЕХНОЛОДЖИ ООО",
    "ДОМАШНИЙ ИНТЕРЬЕР ООО", "ГК ГАЛА-ПРОДЖЕКТ ООО",
    "ИП Васильев Данил Андреевич", 'ГАЛА ООО', 'ТВИНЛАЙТ ООО'
}

def normalize_number(value):
    if pd.isna(value):
        return ""
    value = str(value).strip()
    value = value.replace("№", "").replace(" ", "").replace("\u00a0", "")
    return value

def normalize_counterparty_name(value):
    if pd.isna(value):
        return ""
    value = str(value).upper().strip()
    value = value.replace('"', "").replace("«", "").replace("»", "")
    value = value.replace(".", "").replace(",", "")
    value = value.replace("(", " ").replace(")", " ")
    for word in ["ООО", "ЗАО", "АО", "ПАО", "ИП"]:
        value = re.sub(rf"\b{word}\b", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value

def clean_amount(value):
    if pd.isna(value):
        return Decimal("0")
    try:
        value = str(value).strip()
        if not value or value.lower() in ["nan", "none", "-", "—"]:
            return Decimal("0")
        value = value.replace("\u00a0", "").replace("\u202f", "")
        value = value.replace("₽", "").replace("руб.", "").replace("руб", "")
        value = value.strip()
        if "," in value and "." in value:
            value = value.replace(",", "")
        elif "," in value and "." not in value:
            value = value.replace(" ", "").replace(",", ".")
        else:
            value = value.replace(" ", "")
        value = re.sub(r"[^0-9.\-]", "", value)
        return Decimal(value)
    except:
        return Decimal("0")

def run_reconciliation(excel_file):
    """Основная функция сверки"""
    
    # Читаем файл 1С
    df_1c = pd.read_excel(excel_file, header=3)
    
    # Проверка колонок
    required_columns = ["Дата вх.", "Номер вх.", "Сумма", "Контрагент", "Счет фактура", "Вид операции"]
    missing = [col for col in required_columns if col not in df_1c.columns]
    if missing:
        raise ValueError(f'Не найдены колонки: {", ".join(missing)}')
    
    # Фильтрация
    df_1c = df_1c[
        (df_1c["Вид операции"].astype(str).str.strip() == "Товары") &
        (df_1c["Счет фактура"].astype(str).str.strip().isin(["Проведен", "Не требуется"]))
    ].copy()
    
    # Нормализация
    df_1c["date"] = pd.to_datetime(df_1c["Дата вх."], dayfirst=True, errors="coerce").dt.date
    df_1c["number_norm"] = df_1c["Номер вх."].apply(normalize_number)
    df_1c["counterparty_norm"] = df_1c["Контрагент"].apply(normalize_counterparty_name)
    
    # Исключение контрагентов
    ignore_norm = {normalize_counterparty_name(name) for name in IGNORE_COUNTERPARTIES}
    df_1c = df_1c[~df_1c["counterparty_norm"].isin(ignore_norm)].copy()
    df_1c["amount_1c"] = df_1c["Сумма"].apply(clean_amount).apply(float)
    
    # Группировка
    df_1c_grouped = df_1c.groupby(
        ["counterparty_norm", "date", "number_norm"], dropna=False
    ).agg(
        amount_1c=("amount_1c", "sum"),
        rows_1c=("amount_1c", "count"),
        counterparty_1c=("Контрагент", "first"),
    ).reset_index()
    
    # ВСЕ УПД из базы
    qs = UpdDocument.objects.select_related("counterparty").annotate(
        amount_our=Sum("income_lines__upd_amount_vatadd")
    )
    
    our_rows = []
    for upd in qs:
        counterparty_name = str(upd.counterparty) if upd.counterparty else ""
        if " (ИНН:" in counterparty_name:
            counterparty_name = counterparty_name.split(" (ИНН:")[0]
        
        our_rows.append({
            "upd_id": upd.id,
            "counterparty_our": counterparty_name,
            "counterparty_norm": normalize_counterparty_name(counterparty_name),
            "date": upd.date,
            "number_norm": normalize_number(upd.number),
            "number_our": upd.number,
            "amount_our": float(upd.amount_our) if upd.amount_our else 0,
        })
    
    df_our = pd.DataFrame(our_rows)
    
    # Дубликаты
    duplicate_keys = ["counterparty_norm", "date", "number_norm"]
    df_our_duplicates = df_our[df_our.duplicated(subset=duplicate_keys, keep=False)].copy()
    
    # Слияние
    df_result = df_our.merge(df_1c_grouped, on=duplicate_keys, how="outer", indicator=True)
    
    # Статусы
    def define_status(row):
        if row["_merge"] == "left_only":
            return "ONLY_IN_US"
        if row["_merge"] == "right_only":
            return "ONLY_IN_1C"
        amount_our = row.get("amount_our") or 0
        amount_1c = row.get("amount_1c") or 0
        diff = abs(amount_our - amount_1c)
        return "OK" if diff <= 1 else "SUM_DIFF"
    
    df_result["status"] = df_result.apply(define_status, axis=1)
    df_result["amount_our"] = df_result["amount_our"].fillna(0)
    df_result["amount_1c"] = df_result["amount_1c"].fillna(0)
    df_result["diff"] = df_result["amount_our"] - df_result["amount_1c"]
    
    # Разделяем по статусам
    df_only_in_us = df_result[df_result["status"] == "ONLY_IN_US"].copy()
    df_only_in_1c = df_result[df_result["status"] == "ONLY_IN_1C"].copy()
    df_sum_diff = df_result[df_result["status"] == "SUM_DIFF"].copy()
    
    # Статистика
    stats = df_result["status"].value_counts().to_dict()
    
    # Суммы
    total_amount_our = df_result["amount_our"].sum()
    total_amount_1c = df_result["amount_1c"].sum()
    total_diff = total_amount_our - total_amount_1c
    
    # Строим красивый отчет
    output = build_reconciliation_report(
        df_result=df_result,
        df_only_in_us=df_only_in_us,
        df_only_in_1c=df_only_in_1c,
        df_sum_diff=df_sum_diff,
        df_duplicates=df_our_duplicates,
        stats=stats,
        total_amount_our=total_amount_our,
        total_amount_1c=total_amount_1c,
        total_diff=total_diff
    )
    
    return output