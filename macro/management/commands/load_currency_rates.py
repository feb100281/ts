import datetime
import logging
from decimal import Decimal

import requests
import xml.etree.ElementTree as ET

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from macro.models import CurrencyRate
from utils.choises import CURRENCY_CHOISE

logger = logging.getLogger(__name__)

CBR_DAILY_URL = settings.CBR_DAILY_URL


def fetch_cbr_rates_for_date(date: datetime.date) -> dict:
    """
    Получить курсы ЦБ РФ на конкретную дату.
    Возвращает словарь: { 'USD': Decimal('92.5000'), 'EUR': ... }
    """
    # ЦБ ожидает дату в формате dd/mm/yyyy
    params = {"date_req": date.strftime("%d/%m/%Y")}
    resp = requests.get(CBR_DAILY_URL, params=params, timeout=10)
    resp.raise_for_status()

    result = {}
    root = ET.fromstring(resp.content)

    for valute in root.findall("Valute"):
        char_code = valute.find("CharCode").text.strip()
        nominal_text = valute.find("Nominal").text.strip()
        value_text = valute.find("Value").text.strip()

        # Пример: nominal=1, value='92,5000'
        try:
            nominal = Decimal(nominal_text.replace(",", "."))
            value = Decimal(value_text.replace(",", "."))
            rate = (value / nominal).quantize(Decimal("0.0001"))
        except Exception as e:
            logger.warning("Ошибка парсинга курса %s: %s", char_code, e)
            continue

        result[char_code] = rate

    # Для RUB курса не приходит — считаем 1.0
    result.setdefault("RUB", Decimal("1"))

    return result


class Command(BaseCommand):
    help = (
        "Загрузить курсы валют по данным ЦБ РФ "
        "(в модель CurrencyRate). "
        "Пример: python manage.py load_currency_rates "
        "--from 2024-01-01 --to 2024-01-31 "
        "--currencies USD,EUR,CNY,HKD,AED"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--from",
            dest="date_from",
            help="Дата начала диапазона (YYYY-MM-DD). По умолчанию: сегодня.",
        )
        parser.add_argument(
            "--to",
            dest="date_to",
            help="Дата окончания диапазона (YYYY-MM-DD). По умолчанию: date_from.",
        )
        parser.add_argument(
            "--currencies",
            dest="currencies",
            help=(
                "Список валют через запятую (например: USD,EUR,CNY,HKD,AED). "
                "Если не указано — по умолчанию USD,EUR,CNY,HKD,AED."
            ),
        )
        parser.add_argument(
            "--base",
            dest="base_currency",
            default="RUB",
            help="Базовая валюта (по умолчанию RUB).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Только показать, что будет загружено, без сохранения в БД.",
        )

    def handle(self, *args, **options):
        # --- разбор дат ---
        today = datetime.date.today()

        if options["date_from"]:
            try:
                date_from = datetime.datetime.strptime(
                    options["date_from"], "%Y-%m-%d"
                ).date()
            except ValueError:
                raise CommandError("Неверный формат --from (ожидается YYYY-MM-DD)")
        else:
            date_from = today

        if options["date_to"]:
            try:
                date_to = datetime.datetime.strptime(
                    options["date_to"], "%Y-%m-%d"
                ).date()
            except ValueError:
                raise CommandError("Неверный формат --to (ожидается YYYY-MM-DD)")
        else:
            date_to = date_from

        if date_to < date_from:
            raise CommandError("--to не может быть меньше, чем --from")

        # --- допустимые валюты и базовая валюта ---
        valid_currencies = {code for code, _ in CURRENCY_CHOISE}

        base_currency = options["base_currency"].upper()
        if base_currency not in valid_currencies:
            raise CommandError(
                f"Базовая валюта {base_currency} не входит в CURRENCY_CHOISE."
            )

        # --- разбор списка валют ---
        if options["currencies"]:
            currencies = [c.strip().upper() for c in options["currencies"].split(",")]
        else:
            # по умолчанию — наши 5 основных валют
            currencies = ["USD", "EUR", "CNY", "HKD", "AED"]

        for c in currencies:
            if c not in valid_currencies:
                self.stdout.write(
                    self.style.WARNING(
                        f"Валюта {c} не входит в CURRENCY_CHOISE и может не сохраниться корректно."
                    )
                )

        dry_run = options["dry_run"]

        self.stdout.write(
            self.style.NOTICE(
                f"Загружаем курсы ЦБ: {', '.join(currencies)} к {base_currency} "
                f"за период с {date_from} по {date_to}. "
                f"{'(DRY RUN)' if dry_run else ''}"
            )
        )

        # --- основной цикл по датам ---
        current_date = date_from
        created = 0
        updated = 0

        while current_date <= date_to:
            try:
                cbr_rates = fetch_cbr_rates_for_date(current_date)
            except requests.RequestException as e:
                self.stdout.write(
                    self.style.ERROR(f"[{current_date}] Ошибка запроса к ЦБ: {e}")
                )
                current_date += datetime.timedelta(days=1)
                continue

            for cur in currencies:
                if cur == base_currency:
                    rate_value = Decimal("1")
                else:
                    if cur not in cbr_rates:
                        self.stdout.write(
                            self.style.WARNING(
                                f"[{current_date}] Нет курса для {cur} в ответе ЦБ."
                            )
                        )
                        continue
                    # Курс, который отдаёт ЦБ — всегда к RUB.
                    # Если базовая валюта RUB — берём как есть.
                    if base_currency == "RUB":
                        rate_value = cbr_rates[cur]
                    else:
                        # Если базовая валюта не RUB, то:
                        # курс(cur/base) = курс(cur/RUB) / курс(base/RUB)
                        if base_currency not in cbr_rates:
                            self.stdout.write(
                                self.style.WARNING(
                                    f"[{current_date}] Нет курса для базовой валюты "
                                    f"{base_currency} в ответе ЦБ."
                                )
                            )
                            continue
                        rate_value = (cbr_rates[cur] / cbr_rates[base_currency]).quantize(
                            Decimal("0.0001")
                        )

                if dry_run:
                    self.stdout.write(
                        f"[DRY RUN] {current_date} {cur}/{base_currency} = {rate_value}"
                    )
                    continue

                obj, created_flag = CurrencyRate.objects.update_or_create(
                    date=current_date,
                    base_currency=base_currency,
                    currency=cur,
                    defaults={
                        "rate": rate_value,
                        "source": "ЦБ РФ",
                    },
                )

                if created_flag:
                    created += 1
                else:
                    updated += 1

            current_date += datetime.timedelta(days=1)

        if not dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Готово. Создано записей: {created}, обновлено: {updated}."
                )
            )
        else:
            self.stdout.write(self.style.SUCCESS("DRY RUN завершён."))
