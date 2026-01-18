# macro/services/market_ingest.py
from decimal import Decimal
from django.db import transaction
from django.utils import timezone

from macro.models import (
    MarketSource,
    MarketListing,
    MarketListingObservation,
    MarketRegion,
    MarketDistrict,
    OfficeClass,
    PropertyType,
)

OFFICE_CLASS_FALLBACK = "UNKNOWN"


def _get_or_create_region(name: str) -> MarketRegion:
    obj, _ = MarketRegion.objects.get_or_create(name=name.strip())
    return obj


def _get_or_create_district(region: MarketRegion, name: str) -> MarketDistrict:
    obj, _ = MarketDistrict.objects.get_or_create(region=region, name=name.strip())
    return obj


def _get_or_create_office_class(code: str | None) -> OfficeClass:
    code = (code or OFFICE_CLASS_FALLBACK).strip().upper()
    obj, _ = OfficeClass.objects.get_or_create(code=code, defaults={"name": code})
    return obj


def _get_or_create_property_type(code: str) -> PropertyType:
    code = code.strip().lower()
    obj, _ = PropertyType.objects.get_or_create(code=code, defaults={"name": code, "is_active": True})
    return obj


def normalize_rub_m2_month(item: dict) -> Decimal | None:
    """
    MVP-нормализация к ₽/м²/мес.
    Поддерживаем:
      - RUB + m2_month
      - RUB + m2_year
      - RUB + total_month / total_year (если есть area_m2)
    """
    try:
        currency = item.get("currency") or "RUB"
        unit = item.get("rent_rate_unit")
        val = item.get("rent_rate_value")
        area = item.get("area_m2")

        if val is None:
            return None

        if currency != "RUB":
            return None  # на MVP не конвертируем валюту

        val = Decimal(str(val))

        if unit == "m2_month":
            return val
        if unit == "m2_year":
            return val / Decimal("12")

        if unit == "total_month" and area:
            return val / Decimal(str(area))

        if unit == "total_year" and area:
            return (val / Decimal("12")) / Decimal(str(area))

        return None
    except Exception:
        return None


@transaction.atomic
def ingest_market_item(source: MarketSource, item: dict) -> MarketListing:
    """
    Upsert listing + create observation (снимок) на текущий момент.
    item — унифицированный dict (см. ниже в CSV-парсере).
    """
    region = _get_or_create_region(item["region_name"])
    district = _get_or_create_district(region, item["district_name"])
    office_class = _get_or_create_office_class(item.get("office_class_code"))
    property_type = _get_or_create_property_type(item["property_type_code"])

    listing, _ = MarketListing.objects.update_or_create(
        source=source,
        external_id=str(item["external_id"]),
        defaults={
            "url": item.get("url", ""),
            "property_type": property_type,
            "deal_type": item["deal_type"],  # "rent" / "sale"
            "region": region,
            "district": district,
            "office_class": office_class,
            "office_class_raw": item.get("office_class_raw"),
            "title": item.get("title"),
            "description": item.get("description"),
            "address_text": item.get("address_text"),
            "lat": item.get("lat"),
            "lon": item.get("lon"),
        },
    )

    norm = normalize_rub_m2_month(item)

    MarketListingObservation.objects.create(
        listing=listing,
        observed_at=timezone.now(),
        is_active=True,
        area_m2=item.get("area_m2"),
        currency=item.get("currency") or "RUB",
        price_total=item.get("price_total"),
        rent_rate_value=item.get("rent_rate_value"),
        rent_rate_unit=item.get("rent_rate_unit"),
        vat_included=item.get("vat_included"),
        opex_included=item.get("opex_included"),
        norm_rub_m2_month=norm,
        published_at=item.get("published_at"),
    )

    return listing
