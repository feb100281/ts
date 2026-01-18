# corporate/services/checko_bank.py
import requests
from django.conf import settings


class CheckoBankClientError(Exception):
    pass


def get_bank_data_by_bik(bik: str) -> dict | None:

    if not settings.CHECKO_API_KEY:
        raise CheckoBankClientError("CHECKO_API_KEY не указан в settings.py")

    url = settings.CHECKO_API_BANK_URL
    params = {
        "key": settings.CHECKO_API_KEY,
        "bic": bik,
    }

    response = requests.get(url, params=params, timeout=5)
    response.raise_for_status()

    payload = response.json()

    meta = payload.get("meta") or {}
    status = meta.get("status")

    if status != "ok":
        message = meta.get("message") or "Неизвестная ошибка Checko"
        raise CheckoBankClientError(message)

    data = payload.get("data") or {}

    # Если вдруг data пустое
    if not data:
        return None

    # Русские ключи из формата Checko
    corr_info = data.get("КорСчет") or {}
    corr_account_number = corr_info.get("Номер")

    result = {
        "name": data.get("Наим"),
        "name_eng": data.get("НаимАнгл"),
        "bik": data.get("БИК"),
        "address": data.get("Адрес"),
        "type": data.get("Тип"),
        "corr_account": corr_account_number,
    }

    return result

