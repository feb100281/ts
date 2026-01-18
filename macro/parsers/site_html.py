# macro/parsers/site_html.py
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Iterator, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


@dataclass
class SiteHTMLParser:
    base_url: str
    list_path: str
    delay_sec: float = 1.0
    timeout_sec: int = 20

    def _get(self, url: str) -> str:
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; MarketBot/1.0; +https://example.com/bot)",
            "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
        }
        r = requests.get(url, headers=headers, timeout=self.timeout_sec)
        r.raise_for_status()
        return r.text

    def iter_items(self, max_pages: int = 1) -> Iterator[dict]:
        """
        MVP: парсим список объявлений по страницам и yield item-ы.
        Тут ты подставляешь CSS-селекторы под конкретный сайт.
        """
        next_url = urljoin(self.base_url, self.list_path)

        for page in range(1, max_pages + 1):
            html = self._get(next_url)
            soup = BeautifulSoup(html, "html.parser")

            cards = soup.select(".listing-card")  # TODO: СЕЛЕКТОР КАРТОЧКИ
            if not cards:
                break

            for card in cards:
                # TODO: вытащить поля из карточки (селекторы под сайт)
                external_id = card.get("data-id") or None  # например data-id
                url = card.select_one("a")["href"]
                url = urljoin(self.base_url, url)

                title = card.select_one(".title").get_text(strip=True) if card.select_one(".title") else None
                price = self._parse_number(card.select_one(".price").get_text(" ", strip=True)) if card.select_one(".price") else None
                area = self._parse_number(card.select_one(".area").get_text(" ", strip=True)) if card.select_one(".area") else None

                # ВНИМАНИЕ: это пример. Ты должна решить, что на сайте означает “ставка”
                # и в какой единице. Для офисов обычно ₽/м²/мес.
                item = {
                    "external_id": external_id or url,  # временно, если нет id
                    "url": url,
                    "deal_type": "rent",
                    "property_type_code": "office",
                    "region_name": "Москва",
                    "district_name": "ЦАО",
                    "office_class_code": "UNKNOWN",
                    "office_class_raw": None,
                    "title": title,
                    "description": None,
                    "address_text": None,
                    "lat": None,
                    "lon": None,
                    "published_at": None,
                    "area_m2": area,
                    "currency": "RUB",
                    "price_total": None,
                    "rent_rate_value": price,
                    "rent_rate_unit": "m2_month",
                    "vat_included": None,
                    "opex_included": None,
                }
                yield item

            # Пагинация (пример)
            next_link = soup.select_one("a.next")  # TODO: селектор "следующая"
            if not next_link or not next_link.get("href"):
                break

            next_url = urljoin(self.base_url, next_link["href"])
            time.sleep(self.delay_sec)

    @staticmethod
    def _parse_number(text: str) -> Optional[float]:
        if not text:
            return None
        # грубая очистка "2 500 ₽" -> "2500"
        digits = "".join(ch for ch in text if ch.isdigit() or ch in ". ,")
        digits = digits.replace(" ", "").replace(",", ".")
        try:
            return float(digits)
        except Exception:
            return None
