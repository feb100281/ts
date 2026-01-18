from __future__ import annotations

import json
import re
import time
from decimal import Decimal, InvalidOperation
from typing import Optional

import requests
from bs4 import BeautifulSoup
from django.db import transaction
from django.utils import timezone

from macro.models import (
    MarketSource, PropertyType, OfficeClass, MarketRegion, MarketDistrict,
    MarketListing, MarketListingObservation
)

UA = "Mozilla/5.0 (compatible; MarketBot/1.0)"

def run_cian_import(
    *,
    list_url: str,
    region_id: int,
    district_id: int,
    office_class_id: int,
    property_type_id: int,
    deal_type: str,
    pages: int = 1,
    sleep_s: float = 1.5,
) -> dict:
    if not list_url:
        raise ValueError("Не задан cian_list_url")

    source = MarketSource.objects.get_or_create(code="cian", defaults={"name": "ЦИАН"})[0]

    region = MarketRegion.objects.get(id=region_id)
    district = MarketDistrict.objects.get(id=district_id)
    office_class = OfficeClass.objects.get(id=office_class_id)
    prop_type = PropertyType.objects.get(id=property_type_id)

    session = requests.Session()
    session.headers.update({"User-Agent": UA})

    processed = 0
    created_obs = 0
    updated_obs = 0

    for page in range(1, max(1, pages) + 1):
        url = _with_page(list_url, page)
        html = _fetch(session, url)
        
        # DEBUG: что реально пришло
        soup0 = BeautifulSoup(html, "html.parser")
        title0 = soup0.title.get_text(strip=True) if soup0.title else ""
        print(f"[CIAN] page={page} url={url}")
        print(f"[CIAN] html_len={len(html)} title={title0!r}")

        low = html.lower()
        if "captcha" in low or "доступ ограничен" in low or "are you human" in low:
            raise RuntimeError("CIAN вернул антибот/капчу. HTML выдачи не парсится обычным requests.")
        

        urls = _extract_card_urls(html, deal_type=deal_type)

        for offer_url in urls:
            time.sleep(max(0.1, sleep_s))
            offer_html = _fetch(session, offer_url)
            offer = _parse_offer_minimal(offer_url, offer_html)

            if not offer.get("external_id"):
                continue

            res = _upsert_offer(
                source=source,
                region=region,
                district=district,
                office_class=office_class,
                prop_type=prop_type,
                deal_type=deal_type,
                offer=offer,
            )
            processed += 1
            if res == "created":
                created_obs += 1
            else:
                updated_obs += 1

    return {
        "processed": processed,
        "created_obs": created_obs,
        "updated_obs": updated_obs,
    }


def _fetch(session: requests.Session, url: str) -> str:
    r = session.get(url, timeout=30)
    r.raise_for_status()
    return r.text


def _with_page(url: str, page: int) -> str:
    if page == 1:
        return url
    sep = "&" if "?" in url else "?"
    # у ЦИАН параметр пагинации может отличаться — если не работает, подстроим под твой list_url
    return f"{url}{sep}p={page}"


from urllib.parse import urljoin

def _extract_card_urls(html: str, deal_type: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    urls = set()

    for a in soup.find_all("a", href=True):
        href = (a["href"] or "").strip()
        if not href:
            continue

        # делаем абсолютным
        full = urljoin("https://www.cian.ru", href)
        full = full.split("?")[0].rstrip("/")

        # карточка почти всегда содержит числовой id (не обязательно /rent/ в URL)
        if re.search(r"/\d+$", full):
            urls.add(full)

    return sorted(urls)



def _extract_external_id(url: str) -> Optional[str]:
    m = re.search(r"/(\d+)/?$", url.split("?")[0])
    return m.group(1) if m else None


def _to_dec(x) -> Optional[Decimal]:
    if x is None:
        return None
    try:
        return Decimal(str(x))
    except (InvalidOperation, ValueError):
        return None


def _parse_offer_minimal(url: str, html: str) -> dict:
    """
    Минимально рабочий парсер:
    - external_id, title
    - попытка достать ld+json (если есть) и сохранить в raw
    - остальные поля пока None (доработаем под конкретный HTML карточки)
    """
    soup = BeautifulSoup(html, "html.parser")

    external_id = _extract_external_id(url)
    title = soup.title.get_text(strip=True) if soup.title else None

    raw_json = None
    for s in soup.find_all("script"):
        t = (s.get("type") or "").lower()
        if "ld+json" in t:
            try:
                raw_json = json.loads(s.get_text(strip=True))
                break
            except Exception:
                pass

    return {
        "external_id": external_id,
        "url": url,
        "title": title,
        "address_text": None,
        "lat": None,
        "lon": None,
        "area_m2": None,
        "price_total": None,
        "rent_rate_value": None,
        "rent_rate_unit": None,
        "vat_included": None,
        "opex_included": None,
        "office_class_raw": None,
        "published_at": None,
        "raw": raw_json,
    }


@transaction.atomic
def _upsert_offer(
    *,
    source: MarketSource,
    region: MarketRegion,
    district: MarketDistrict,
    office_class: OfficeClass,
    prop_type: PropertyType,
    deal_type: str,
    offer: dict,
) -> str:
    listing, _ = MarketListing.objects.update_or_create(
        source=source,
        external_id=offer["external_id"],
        defaults=dict(
            url=offer["url"],
            property_type=prop_type,
            deal_type=deal_type,
            region=region,
            district=district,
            office_class=office_class,
            office_class_raw=offer.get("office_class_raw"),
            title=offer.get("title"),
            description=None,
            address_text=offer.get("address_text"),
            lat=offer.get("lat"),
            lon=offer.get("lon"),
        ),
    )

    observed_date = timezone.localdate()

    defaults = dict(
        observed_at=timezone.now(),
        observed_date=observed_date,
        is_active=True,
        area_m2=_to_dec(offer.get("area_m2")),
        currency="RUB",
        price_total=_to_dec(offer.get("price_total")),
        rent_rate_value=_to_dec(offer.get("rent_rate_value")),
        rent_rate_unit=offer.get("rent_rate_unit"),
        vat_included=offer.get("vat_included"),
        opex_included=offer.get("opex_included"),
        norm_rub_m2_month=_calc_norm(offer),
        raw=offer.get("raw"),
    )

    obj, created = MarketListingObservation.objects.update_or_create(
        listing=listing,
        observed_date=observed_date,
        defaults=defaults,
    )
    return "created" if created else "updated"


def _calc_norm(offer: dict) -> Optional[Decimal]:
    v = _to_dec(offer.get("rent_rate_value"))
    u = offer.get("rent_rate_unit")
    a = _to_dec(offer.get("area_m2"))

    if v is None or not u:
        return None

    try:
        if u == "m2_month":
            return v
        if u == "m2_year":
            return v / Decimal("12")
        if u == "total_month" and a and a > 0:
            return v / a
        if u == "total_year" and a and a > 0:
            return (v / Decimal("12")) / a
    except Exception:
        return None

    return None
