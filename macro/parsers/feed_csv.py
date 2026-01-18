# macro/parsers/feed_csv.py
import csv
from datetime import datetime
from typing import Iterator, Optional


def _to_float(v: Optional[str]):
    if v is None:
        return None
    v = str(v).strip().replace(",", ".")
    return float(v) if v else None


def _to_bool(v: Optional[str]):
    if v is None:
        return None
    s = str(v).strip().lower()
    return s in ("1", "true", "yes", "y", "да")


class CSVFeedParser:
    """
    MVP: читаем CSV и возвращаем dict'ы объявлений в едином формате.
    """

    def __init__(self, path: str):
        self.path = path

    def iter_items(self) -> Iterator[dict]:
        with open(self.path, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)

            required = {
                "external_id", "url", "deal_type",
                "property_type_code", "region_name", "district_name"
            }
            missing = required - set(reader.fieldnames or [])
            if missing:
                raise ValueError(f"CSV missing required columns: {sorted(missing)}")

            for row in reader:
                yield {
                    "external_id": row["external_id"],
                    "url": row["url"],
                    "deal_type": row["deal_type"].strip().lower(),  # rent/sale

                    "property_type_code": row["property_type_code"].strip().lower(),
                    "region_name": row["region_name"].strip(),
                    "district_name": row["district_name"].strip(),

                    "office_class_code": (row.get("office_class_code") or "UNKNOWN").strip().upper(),
                    "office_class_raw": (row.get("office_class_raw") or "").strip() or None,

                    "title": (row.get("title") or "").strip() or None,
                    "description": (row.get("description") or "").strip() or None,
                    "address_text": (row.get("address_text") or "").strip() or None,

                    "lat": _to_float(row.get("lat")),
                    "lon": _to_float(row.get("lon")),

                    "published_at": None,  # можно добавить потом

                    "area_m2": _to_float(row.get("area_m2")),
                    "currency": (row.get("currency") or "RUB").strip().upper(),

                    "price_total": _to_float(row.get("price_total")),
                    "rent_rate_value": _to_float(row.get("rent_rate_value")),
                    "rent_rate_unit": (row.get("rent_rate_unit") or "").strip() or None,

                    "vat_included": _to_bool(row.get("vat_included")),
                    "opex_included": _to_bool(row.get("opex_included")),
                }
