# macro/management/commands/crawl_cian.py
from __future__ import annotations

import re
import time
from decimal import Decimal, InvalidOperation
from dataclasses import dataclass
from typing import Optional, Iterable

import requests
from bs4 import BeautifulSoup

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction

from models import (
    MarketSource, PropertyType, OfficeClass, MarketRegion, MarketDistrict,
    MarketListing, MarketListingObservation
)

UA = "Mozilla/5.0 (compatible; MarketBot/1.0; +https://example.local)"


@dataclass
class ParsedOffer:
    external_id: str
    url: str
    title: Optional[str]
    address_text: Optional[str]
    lat: Optional[Decimal]
    lon: Optional[Decimal]
    area_m2: Optional[Decimal]
    price_total: Optional[Decimal]
    rent_rate_value: Optional[Decimal]
    rent_rate_unit: Optional[str]  # m2_month, m2_year, total_month, total_year
    vat_included: Optional[bool]
    opex_included: Optional[bool]
    office_class_raw: Optional[str]
    published_at: Optional[str]  # можно потом распарсить в datetime
    raw: Optional[dict]


def _d(s: Optional[str]) -> Optional[Decimal]:
    if not s:
        return None
    try:
        return Decimal(s)
    except (InvalidOperation, ValueError):
        return None


class Command(BaseCommand):
    help = "Crawl CIAN listings and store observations"

    def add_arguments(self, parser):
        parser.add_argument("--list-url", required=True, help="CIAN search/listing URL")
        parser.add_argument("--region", required=True, help="MarketRegion name, e.g. Москва")
        parser.add_argument("--property-type", required=True, help="PropertyType.code, e.g. office")
        parser.add_argument("--deal-type", default="rent", choices=["rent", "sale"])
        parser.add_argument("--district", default="Не определён", help="Fallback district name")
        parser.add_argument("--office-class", default="UNKNOWN", help="Default office class code")
        parser.add_argument("--pages", type=int, default=1)
        parser.add_argument("--sleep", type=float, default=1.5)

    def handle(self, *args, **opts):
        source = MarketSource.objects.get_or_create(code="cian", defaults={"name": "ЦИАН"})[0]

        region = MarketRegion.objects.get_or_create(name=opts["region"])[0]
        district = MarketDistrict.objects.get_or_create(region=region, name=opts["district"])[0]
        prop_type = PropertyType.objects.get(code=opts["property_type"])
        office_class = OfficeClass.objects.get_or_create(
            code=opts["office_class"], defaults={"name": opts["office_class"]}
        )[0]

        list_url = opts["list_url"]
        pages = opts["pages"]
        sleep_s = opts["sleep"]

        session = requests.Session()
        session.headers.update({"User-Agent": UA})

        total_new_obs = 0
        total_listings = 0

        for page in range(1, pages + 1):
            url = self._with_page(list_url, page)
            html = self._fetch(session, url)
            offers_urls = self._extract_card_urls(html)

            self.stdout.write(f"Page {page}: found {len(offers_urls)} urls")

            for offer_url in offers_urls:
                time.sleep(sleep_s)
                try:
                    offer_html = self._fetch(session, offer_url)
                    offer = self._parse_offer(offer_url, offer_html)
                    if not offer or not offer.external_id:
                        continue

                    created_obs = self._upsert_offer(
                        source=source,
                        region=region,
                        district=district,
                        office_class=office_class,
                        prop_type=prop_type,
                        deal_type=opts["deal_type"],
                        offer=offer,
                    )
                    total_listings += 1
                    total_new_obs += int(created_obs)

                except Exception as e:
                    self.stderr.write(f"Error on {offer_url}: {e}")

        self.stdout.write(self.style.SUCCESS(
            f"Done. listings processed={total_listings}, new observations={total_new_obs}"
        ))

    # ───────── helpers ─────────

    def _fetch(self, session: requests.Session, url: str) -> str:
        r = session.get(url, timeout=30)
        r.raise_for_status()
        return r.text

    def _with_page(self, url: str, page: int) -> str:
        # максимально просто: если у тебя уже есть пагинация параметром, поменяем позже
        if page == 1:
            return url
        sep = "&" if "?" in url else "?"
        return f"{url}{sep}p={page}"

    def _extract_card_urls(self, html: str) -> list[str]:
        soup = BeautifulSoup(html, "html.parser")
        urls = set()

        # Тут нужно будет подстроить под фактическую разметку выдачи ЦИАН.
        # Начнём с поиска всех ссылок, похожих на карточки.
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "cian.ru" in href and "/rent/" in href:
                urls.add(href.split("?")[0])

        return list(urls)

    def _parse_offer(self, url: str, html: str) -> Optional[ParsedOffer]:
        # Реально устойчивый способ — вытянуть встроенный JSON из страницы.
        # Конкретный ключ/скрипт у ЦИАН может меняться, поэтому начнём с "поиска JSON в script".
        soup = BeautifulSoup(html, "html.parser")

        external_id = None
        m = re.search(r"cian\.ru\/.*?\/(\d+)\/", url)
        if m:
            external_id = m.group(1)

        title = soup.title.get_text(strip=True) if soup.title else None

        # Заглушки (вставим JSON-парсинг после того как посмотрим пример HTML конкретной карточки)
        return ParsedOffer(
            external_id=external_id or "",
            url=url,
            title=title,
            address_text=None,
            lat=None,
            lon=None,
            area_m2=None,
            price_total=None,
            rent_rate_value=None,
            rent_rate_unit=None,
            vat_included=None,
            opex_included=None,
            office_class_raw=None,
            published_at=None,
            raw=None,
        )

    @transaction.atomic
    def _upsert_offer(
        self,
        source: MarketSource,
        region: MarketRegion,
        district: MarketDistrict,
        office_class: OfficeClass,
        prop_type: PropertyType,
        deal_type: str,
        offer: ParsedOffer,
    ) -> bool:
        listing, _created = MarketListing.objects.update_or_create(
            source=source,
            external_id=offer.external_id,
            defaults=dict(
                url=offer.url,
                property_type=prop_type,
                deal_type=deal_type,
                region=region,
                district=district,
                office_class=office_class,
                office_class_raw=offer.office_class_raw,
                title=offer.title,
                description=None,
                address_text=offer.address_text,
                lat=offer.lat,
                lon=offer.lon,
            ),
        )

        observed_date = timezone.localdate()

        obs, created = MarketListingObservation.objects.update_or_create(
            listing=listing,
            observed_date=observed_date,  # если добавишь это поле
            defaults=dict(
                observed_at=timezone.now(),
                is_active=True,
                area_m2=offer.area_m2,
                currency="RUB",
                price_total=offer.price_total,
                rent_rate_value=offer.rent_rate_value,
                rent_rate_unit=offer.rent_rate_unit,
                vat_included=offer.vat_included,
                opex_included=offer.opex_included,
                norm_rub_m2_month=self._calc_norm(offer),
                # published_at=...
                # raw=offer.raw
            ),
        )
        return created

    def _calc_norm(self, offer: ParsedOffer) -> Optional[Decimal]:
        v = offer.rent_rate_value
        u = offer.rent_rate_unit
        a = offer.area_m2

        if v is None or u is None:
            return None

        try:
            if u == "m2_month":
                return v
            if u == "m2_year":
                return (v / Decimal("12"))
            if u == "total_month" and a:
                return (v / a)
            if u == "total_year" and a:
                return (v / Decimal("12") / a)
        except (InvalidOperation, ZeroDivisionError):
            return None

        return None
