# corporate/services/checko_company.py

import requests
from django.conf import settings


class CheckoCompanyClientError(Exception):
    pass


def get_company_data_by_inn(inn: str) -> dict | None:


    api_key = getattr(settings, "CHECKO_API_KEY", None)
    if not api_key:
        raise CheckoCompanyClientError("CHECKO_API_KEY не настроен в settings")

    base_url = getattr(
        settings,
        "CHECKO_API_COMPANY_URL",
        "https://api.checko.ru/v2/company",
    )

    try:
        resp = requests.get(
            base_url,
            params={"key": api_key, "inn": inn},
            timeout=10,
        )
    except requests.RequestException as e:
        raise CheckoCompanyClientError(f"Ошибка сети при обращении к Checko: {e}")

    resp.raise_for_status()
    payload = resp.json() or {}

    meta = payload.get("meta") or {}
    status = meta.get("status")
    if status and status != "ok":
        message = meta.get("message") or "Неизвестная ошибка Checko"
        raise CheckoCompanyClientError(message)

    data = payload.get("data") or {}
    if not data:
        return None

    # ---- Адрес ----
    jur_addr = data.get("ЮрАдрес") or {}
    address = ""
    if isinstance(jur_addr, dict):
        address = (
            jur_addr.get("АдресРФ")
            or jur_addr.get("Адрес")
            or ""
        )

    # ---- Контакты ----
    contacts = data.get("Контакты") or {}
    phones = contacts.get("Телефон") or contacts.get("Телефоны") or []
    if isinstance(phones, list):
        phone = phones[0] if phones else ""
    else:
        phone = phones or ""

    emails = contacts.get("Email") or contacts.get("Емэйл") or []
    if isinstance(emails, list):
        email = emails[0] if emails else ""
    else:
        email = emails or ""

    sites = contacts.get("Сайты") or contacts.get("Сайт") or contacts.get("ВебСайт") or []
    if isinstance(sites, list):
        website = sites[0] if sites else ""
    else:
        website = sites or ""

    # ---- Руководитель ----
    ruk_list = data.get("Руковод") or []
    ceo_name = ""
    ceo_post = ""
    ceo_record_date = ""

    if isinstance(ruk_list, list) and ruk_list:
        open_entries = [x for x in ruk_list if not x.get("ОгрДоступ")]
        cand = open_entries[0] if open_entries else ruk_list[0]

        ceo_name = (cand.get("ФИО") or "").strip()
        ceo_post = (
            (cand.get("НаимДолжн")
             or cand.get("ВидДолжн")
             or "")
            .strip()
        )
        ceo_record_date = (cand.get("ДатаЗаписи") or "").strip()

    result = {
        "name": data.get("НаимСокр") or data.get("НаимПолн") or "",
        "full_name": data.get("НаимПолн") or "",
        "inn": data.get("ИНН") or inn,
        "kpp": data.get("КПП") or "",
        "ogrn": data.get("ОГРН") or "",
        "address": address,
        "phone": phone,
        "email": email,
        "website": website,
        "ceo_name": ceo_name,
        "ceo_post": ceo_post,
        "ceo_record_date": ceo_record_date,
    }

    if not (result["full_name"] or result["name"]):
        return None

    return result

