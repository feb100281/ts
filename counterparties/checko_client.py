# checko_client.py

import os
import time
import requests
from typing import Optional, Dict, Any




BASE = "https://api.checko.ru/v2"
API_KEY = os.getenv("CHECKO_API_KEY")  
DEFAULT_TIMEOUT = 12
USER_AGENT = "Manufaktura-Offices/auto-fill (contact: admin@manu)"

class CheckoError(Exception):
    pass

_session = requests.Session()
_session.headers.update({"User-Agent": USER_AGENT})

def _get(endpoint: str, retries: int = 2, backoff: float = 0.7, **params) -> Dict[str, Any]:
    key = params.pop("key", None) or API_KEY
    if not key:
        raise CheckoError("API KEY не задан")

    params["key"] = key
    url = f"{BASE}/{endpoint}"

    for attempt in range(retries + 1):
        try:
            r = _session.get(url, params=params, timeout=DEFAULT_TIMEOUT)
            if r.status_code in (429,) or r.status_code >= 500:
                if attempt < retries:
                    time.sleep(backoff * (2 ** attempt))
                    continue
            r.raise_for_status()

            return r.json()
        except requests.RequestException as e:
            if attempt < retries:
                time.sleep(backoff * (2 ** attempt))
                continue
            raise CheckoError(f"Сетевая ошибка: {e}") from e

    raise CheckoError("Не удалось получить данные")


def company_by_inn(inn: str, kpp: Optional[str] = None, key: Optional[str] = None) -> dict:
    params = {"inn": str(inn)}
    if kpp:
        params["kpp"] = str(kpp)  
    if key:
        params["key"] = key

    return _get("company", **params)


def entrepreneur_by_inn(inn: str, key: Optional[str] = None) -> dict:
    params = {"inn": str(inn)}
    if key:
        params["key"] = key
    return _get("entrepreneur", **params)


# ======  парсинг ответа для Django-формы ======

class PhysicalPersonNotFound(Exception):
    """
    Случай, когда по ИНН не нашли ни организацию, ни ИП –
    считаем, что это физлицо.
    """
    def __init__(self, message="По данным ФНС организация или ИП не найдены"):
        self.message = message
        super().__init__(message)


def g(d, *path, default=""):
    cur = d
    for p in path:
        if not isinstance(cur, dict) or p not in cur:
            return default
        cur = cur[p]
    return cur if cur is not None else default


def first_str(x):
    if isinstance(x, (list, tuple)):
        for v in x:
            if isinstance(v, str) and v.strip():
                return v.strip()
    if isinstance(x, str) and x.strip():
        return x.strip()
    return ""


def build_counterparty_payload(inn: str) -> Dict[str, Any]:
    """
    Делает запрос к Checko/ФНС, парсит ответ и возвращает payload
    для заполнения формы контрагента.

    НИЧЕГО не знает про Django и JsonResponse.
    """
    inn = (inn or "").strip()
    if not inn:
        raise ValueError("ИНН пустой")

    try_ip = len(inn) == 12
    try_co = len(inn) == 10

    # --- запрос к Checko / ФНС ---
    try:
        if try_ip:
            raw = entrepreneur_by_inn(inn, key="SIwfo6CFilGM4fUX")
        elif try_co:
            raw = company_by_inn(inn, key="SIwfo6CFilGM4fUX")
        else:
            # длина ИНН странная – пробуем оба варианта на всякий случай
            try:
                raw = entrepreneur_by_inn(inn, key="SIwfo6CFilGM4fUX")
            except Exception:
                raw = company_by_inn(inn, key="SIwfo6CFilGM4fUX")
    except CheckoError as e:
        # Любая ошибка от Checko — считаем, что по ИНН никого не нашли → физлицо
        raise PhysicalPersonNotFound(str(e))
    # остальные Exception пусть летят дальше – их поймает admin

    # --- если структура ответа странная / пустая, тоже считаем, что никого не нашли ---
    root = (raw.get("data") or {}) if isinstance(raw, dict) else {}
    if not root:
        raise PhysicalPersonNotFound("Нет данных в ответе Checko/ФНС")

    # --- ОКВЭД ---
    okved = g(root, "ОКВЭД", default={}) or {}
    okved_code    = (okved.get("Код")    or "").strip()
    okved_name    = (okved.get("Наим")   or "").strip()
    okved_version = (okved.get("Версия") or "").strip()

    # --- ОКОПФ ---
    okopf_code = (
        (g(root, "ОКОПФ", "Код", default="") or
         g(root, "ОргПравФорма", "ОКОПФ", "Код", default="") or
         g(root, "ОргПравФорма", "Код", default="") or
         g(root, "ОКОПФ", default={}).get("Код", "")) or ""
    ).strip()

    okopf_name = (
        (g(root, "ОКОПФ", "Наим", default="") or
         g(root, "ОргПравФорма", "ОКОПФ", "Наим", default="") or
         g(root, "ОргПравФорма", "Наим", default="") or
         g(root, "ОКОПФ", default={}).get("Наим", "")) or ""
    ).strip()

    # --- Риски / факторы ---
    ndob = g(root, "НедобПостЗап", default=[]) or []
    risk_disq_persons        = bool(g(root, "ДисквЛица", default=False))
    risk_mass_directors      = bool(g(root, "МассРуковод", default=False))
    risk_mass_founders       = bool(g(root, "МассУчред", default=False))
    risk_illegal_fin         = bool(g(root, "НелегалФин", default=False))
    risk_illegal_fin_status  = (g(root, "НелегалФинСтатус", default="") or "").strip()
    risk_sanctions           = bool(g(root, "Санкции", default=False))
    risk_sanctions_countries = g(root, "СанкцииСтраны", default=[]) or []
    risk_sanctioned_founder  = bool(g(root, "СанкцУчр", default=False))

    risks_raw = {
        "НедобПостЗап": ndob,
        "ДисквЛица": risk_disq_persons,
        "МассРуковод": risk_mass_directors,
        "МассУчред": risk_mass_founders,
        "НелегалФин": risk_illegal_fin,
        "НелегалФинСтатус": risk_illegal_fin_status,
        "Санкции": risk_sanctions,
        "СанкцииСтраны": risk_sanctions_countries,
        "СанкцУчр": risk_sanctioned_founder,
    }

    typ      = (g(root, "Тип", default="") or "").strip()
    tip_sokr = (g(root, "ТипСокр", default="") or "").strip()
    fio_ip   = (g(root, "ФИО", default="") or "").strip()
    is_ip    = (len(inn) == 12) or typ.upper().startswith("ИП") or "ПРЕДПРИНИМАТЕЛ" in typ.upper()

    # --- Руководители ---
    ruk = g(root, "Руковод", default=[])
    ceo_name_co, ceo_post_co, ceo_record_date, ceo_restricted = "", "", "", False
    open_entries = []
    if isinstance(ruk, list) and ruk:
        open_entries = [x for x in ruk if not x.get("ОгрДоступ")]
        ceo_restricted = (len(open_entries) == 0)
        cand = open_entries[0] if open_entries else ruk[0]
        ceo_name_co = (cand.get("ФИО") or "").strip()
        ceo_post_co = (cand.get("НаимДолжн") or (cand.get("ВидДолжн") or "")).strip()
        ceo_record_date = (cand.get("ДатаЗаписи") or "").strip()

    # --- Управляющая организация ---
    upr = g(root, "УпрОрг", default={}) or {}
    upr_name = (upr.get("НаимПолн") or upr.get("НаимСокр") or "").strip()
    upr_record_date = (upr.get("ДатаЗаписи") or "").strip()
    upr_restricted = bool(upr.get("ОгрДоступ"))

    # --- Идентификаторы/адреса/контакты ---
    ogrn = g(root, "ОГРНИП", default="") or g(root, "ОГРН", default="")
    raw_kpp  = "" if is_ip else (g(root, "КПП", default="") or "").strip()
    okpo = (g(root, "ОКПО", default="") or g(root, "Коды", "ОКПО", default="") or "").strip()

    if is_ip:
        kpp_display = okpo
    else:
        parts = []
        if raw_kpp:
            parts.append(raw_kpp)
        if okpo and okpo != raw_kpp:
            parts.append(okpo)
        kpp_display = " / ".join(parts)

    address = (
        g(root, "ЮрАдрес", "АдресРФ", default="") or
        g(root, "ЮрАдрес", "НасПункт", default="") or
        g(root, "Адрес", default="")
    )
    region  = g(root, "Регион", "Наим", default="") or g(root, "Регион", default="")
    website = g(root, "Контакты", "ВебСайт", default="")
    email   = first_str(g(root, "Контакты", "Емэйл", default=[]))
    tel     = first_str(g(root, "Контакты", "Тел", default=[]))
    taxregime = ", ".join([
        s for s in (g(root, "Налоги", "ОсобРежим", default=[]) or [])
        if isinstance(s, str) and s.strip()
    ])

    if is_ip:
        fullname   = f"{tip_sokr} {fio_ip}".strip()
        ceo_final  = fio_ip
        name_short = fio_ip
        ceo_post   = ""
        ceo_record = ""
        manager_is_org = False
        ceo_restricted = False
    else:
        if open_entries:
            ceo_final  = ceo_name_co
            ceo_post   = ceo_post_co
            ceo_record = ceo_record_date
            manager_is_org = False
        elif upr_name:
            ceo_final  = upr_name
            ceo_post   = "Управляющая организация"
            ceo_record = upr_record_date
            manager_is_org = True
            ceo_restricted = upr_restricted
        else:
            ceo_final  = ceo_name_co
            ceo_post   = ceo_post_co
            ceo_record = ceo_record_date
            manager_is_org = False

        fullname   = g(root, "НаимПолн", default="") or g(root, "НаимСокр", default="")
        name_short = g(root, "НаимСокр", default="")

    payload = {
        "fullname":  fullname,
        "kpp":       kpp_display,
        "address":   address,
        "region":    region,
        "website":   website,
        "country":   "RU",

        "name":      name_short,
        "ogrn":      ogrn,
        "email":     email,
        "tel":       tel,
        "taxregime": taxregime,

        "ceo":       ceo_final,
        "ceo_name":  ceo_final,
        "ceo_post":  ceo_post,
        "ceo_record_date": ceo_record,
        "manager_is_org": bool(manager_is_org),

        "is_ip":     bool(is_ip),
        "tip_sokr":  tip_sokr,
        "typ":       typ,

        "ceo_restricted": bool(ceo_restricted),

        "okved_code": okved_code,
        "okved_name": okved_name,
        "okved_version": okved_version,

        "okopf_code": okopf_code,
        "okopf_name": okopf_name,

        "risk_disq_persons": risk_disq_persons,
        "risk_mass_directors": risk_mass_directors,
        "risk_mass_founders": risk_mass_founders,
        "risk_illegal_fin": risk_illegal_fin,
        "risk_illegal_fin_status": risk_illegal_fin_status,
        "risk_sanctions": risk_sanctions,
        "risk_sanctions_countries": ", ".join([
            s for s in risk_sanctions_countries if isinstance(s, str)
        ]),
        "risk_sanctioned_founder": risk_sanctioned_founder,
        "risk_json": risks_raw,
    }

    return payload

def finances_by_inn(inn: str, kpp: Optional[str] = None, extended: bool = True, key: Optional[str] = None) -> dict:
    """
    Финпоказатели по годам (бух. формы) — предпочтительно extended.
    """
    params = {"inn": str(inn)}
    if kpp:
        params["kpp"] = str(kpp)
    if extended:
        params["extended"] = "true"
    if key:
        params["key"] = key
    return _get("finances", **params)
