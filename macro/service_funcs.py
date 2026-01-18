# macro/services.py

import datetime as dt
import calendar
import requests
from bs4 import BeautifulSoup
from django.conf import settings
from django.db import transaction
from .models import KeyRate, Inflation
import re






CBR_KEYRATE_URL = "https://www.cbr.ru/hd_base/KeyRate/"
CBR_INFL_URL = "https://www.cbr.ru/hd_base/infl/"
CBR_ZCYC_URL = "https://www.cbr.ru/hd_base/zcyc_params/"
FRED_API_URL = "https://api.stlouisfed.org/fred/series/observations"





#-----КЛЮЧЕВАЯ СТАВКА-----#
@transaction.atomic
def sync_keyrates_from_cbr() -> int:
    """
    Загружает историю ключевой ставки с сайта ЦБ.
    Оставляет только даты, когда ставка действительно изменялась.
    """

    # --- 1. Тянем ВСЮ историю через параметры From/To ---
    params = {
        "UniDbQuery.Posted": "True",
        "UniDbQuery.From": "01.01.2000",  # можно любую старую дату
        "UniDbQuery.To": dt.date.today().strftime("%d.%m.%Y"),
    }

    resp = requests.get(
        CBR_KEYRATE_URL,
        params=params,
        headers={"User-Agent": "Mozilla/5.0 (compatible; Django keyrate sync)"},
        timeout=10,
    )
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    # --- 2. Находим таблицу со ставками ---
    table = soup.find("table")
    if not table:
        return 0

    rows = table.find_all("tr")
    records = []

    # --- 3. Парсим строки ---
    for row in rows:
        cols = row.find_all("td")
        if len(cols) < 2:
            continue

        date_raw = cols[0].get_text(strip=True)
        rate_raw = cols[1].get_text(strip=True)

        if not date_raw or not rate_raw:
            continue

        try:
            date = dt.datetime.strptime(date_raw, "%d.%m.%Y").date()
        except ValueError:
            continue

        rate_clean = (
            rate_raw.replace("%", "")
            .replace(",", ".")
            .replace("\xa0", "")
            .strip()
        )
        try:
            rate = float(rate_clean)
        except ValueError:
            continue

        records.append({"date": date, "rate": rate})

    if not records:
        return 0

    # --- 4. Оставляем только даты, когда ставка реально менялась ---
    records.sort(key=lambda x: x["date"])  # по возрастанию

    compressed = []
    last_rate = None

    for r in records:
        if last_rate is None or r["rate"] != last_rate:
            compressed.append(r)
            last_rate = r["rate"]

    # --- 5. Сохраняем в базу ---
    created = 0

    for r in compressed:
        obj, is_created = KeyRate.objects.update_or_create(
            date=r["date"],
            defaults={"key_rate": r["rate"]},
        )
        if is_created:
            created += 1

    return created



#-----ИНФЛЯЦИЯ-----#
# @transaction.atomic
# def sync_inflation_from_cbr() -> int:
#     """
#     Синхронизирует данные по инфляции (ИПЦ) с сайта ЦБ.
#     Берём таблицу на странице hd_base/infl и заполняем модель Inflation.
#     """

#     # Тянем не "по умолчанию", а весь период через From / To — как для ключевой ставки
#     params = {
#         "UniDbQuery.Posted": "True",
#         "UniDbQuery.From": "01.01.2000",  # можно любую раннюю дату
#         "UniDbQuery.To": dt.date.today().strftime("%d.%m.%Y"),
#     }

#     resp = requests.get(
#         CBR_INFL_URL,
#         params=params,
#         headers={"User-Agent": "Mozilla/5.0 (compatible; Django inflation sync)"},
#         timeout=10,
#     )
#     resp.raise_for_status()

#     soup = BeautifulSoup(resp.text, "html.parser")

#     # Ищем таблицу, где есть колонки "Дата" и "Инфляция"
#     target_table = None
#     for table in soup.find_all("table"):
#         headers = [th.get_text(strip=True) for th in table.find_all("th")]
#         if any("Дата" in h for h in headers) and any("Инфляция" in h for h in headers):
#             target_table = table
#             break

#     if target_table is None:
#         return 0

#     body = target_table.find("tbody") or target_table
#     rows = body.find_all("tr")

#     records = []

#     for row in rows:
#         cells = row.find_all("td")
#         if len(cells) < 3:
#             continue

#         # Структура на странице:
#         # 0 - "10.2025" (месяц.год)
#         # 1 - "16,50" (ключевая ставка)
#         # 2 - "7,71" (инфляция, % г/г)
#         date_raw = cells[0].get_text(strip=True)
#         infl_raw = cells[2].get_text(strip=True)

#         if not date_raw or not infl_raw:
#             continue

#         # "10.2025" -> последний день месяца (31.10.2025)
#         try:
#             dt_month = dt.datetime.strptime(date_raw, "%m.%Y")
#         except ValueError:
#             continue

#         year = dt_month.year
#         month = dt_month.month
#         last_day = calendar.monthrange(year, month)[1]
#         date = dt.date(year, month, last_day)

#         # "7,71" -> 7.71
#         infl_clean = (
#             infl_raw.replace("%", "")
#             .replace("\xa0", "")
#             .replace(",", ".")
#             .replace("%", "")
#             .strip()
#         )
#         try:
#             infl_value = float(infl_clean)
#         except ValueError:
#             continue

#         records.append(
#             {
#                 "date": date,
#                 "inflation": infl_value,
#             }
#         )

#     if not records:
#         return 0

#     # Сортируем по дате, чтобы было аккуратно
#     records.sort(key=lambda x: x["date"])

#     created = 0
#     for r in records:
#         obj, is_created = Inflation.objects.update_or_create(
#             date=r["date"],
#             defaults={
#                 "inflation_rate": r["inflation"],
#             },
#         )
#         if is_created:
#             created += 1

#     return created



@transaction.atomic
def sync_inflation_from_cbr() -> int:
    """
    Синхронизирует данные по инфляции (ИПЦ) с сайта ЦБ.
    Берём таблицу на странице hd_base/infl и заполняем модель Inflation.
    """

    # --- 1. Параметры запроса: тянем всю историю ---
    params = {
        "UniDbQuery.Posted": "True",
        "UniDbQuery.From": "01.01.2000",  # можно любую раннюю дату
        "UniDbQuery.To": dt.date.today().strftime("%d.%m.%Y"),
    }

    # --- 2. Создаём сессию, чтобы получить cookies и прикинуться браузером ---
    session = requests.Session()
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ru-RU,ru;q=0.9",
        "Referer": "https://www.cbr.ru/hd_base/infl/",
    })

    # заход на главную страницу, чтобы получить cookies
    home_resp = session.get("https://www.cbr.ru/", timeout=10)
    home_resp.raise_for_status()

    # --- 3. Основной запрос за инфляцией (ВАЖНО: POST, не GET) ---
    resp = session.post(
        CBR_INFL_URL,
        data=params,
        timeout=10,
    )
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    # --- 4. Ищем таблицу, где есть колонки "Дата" и "Инфляция" ---
    target_table = None
    for table in soup.find_all("table"):
        headers = [th.get_text(strip=True) for th in table.find_all("th")]
        if any("Дата" in h for h in headers) and any("Инфляция" in h for h in headers):
            target_table = table
            break

    if target_table is None:
        return 0

    body = target_table.find("tbody") or target_table
    rows = body.find_all("tr")

    records = []

    # --- 5. Парсим строки таблицы ---
    for row in rows:
        cells = row.find_all("td")
        if len(cells) < 3:
            continue

        # Структура на странице:
        # 0 - "10.2025" (месяц.год)
        # 1 - "16,50" (ключевая ставка)
        # 2 - "7,71" (инфляция, % г/г)
        date_raw = cells[0].get_text(strip=True)
        infl_raw = cells[2].get_text(strip=True)

        if not date_raw or not infl_raw:
            continue

        # "10.2025" -> последний день месяца (31.10.2025)
        try:
            dt_month = dt.datetime.strptime(date_raw, "%m.%Y")
        except ValueError:
            continue

        year = dt_month.year
        month = dt_month.month
        last_day = calendar.monthrange(year, month)[1]
        date = dt.date(year, month, last_day)

        # "7,71" -> 7.71
        infl_clean = (
            infl_raw.replace("%", "")
            .replace("\xa0", "")
            .replace(",", ".")
            .strip()
        )
        try:
            infl_value = float(infl_clean)
        except ValueError:
            continue

        records.append(
            {
                "date": date,
                "inflation": infl_value,
            }
        )

    if not records:
        return 0

    # --- 6. Сортируем по дате, чтобы было аккуратно ---
    records.sort(key=lambda x: x["date"])

    # --- 7. Записываем в базу ---
    created = 0
    for r in records:
        obj, is_created = Inflation.objects.update_or_create(
            date=r["date"],
            defaults={
                "inflation_rate": r["inflation"],
            },
        )
        if is_created:
            created += 1

    return created





