import requests
from datetime import date, timedelta

from django.db import transaction

from macro.models import CalendarExceptions  # поправь, если модель в другом приложении

BASE_URL = "https://xmlcalendar.ru/data/ru/{year}/calendar.json"


def load_work_calendar_for_year(year: int) -> int:
    """
    Загружает производственный календарь с xmlcalendar.ru
    и записывает ТОЛЬКО ИСКЛЮЧЕНИЯ в CalendarExceptions.

    Исключения = дни, где фактический статус (рабочий/нет)
    отличается от базового правила:
      - пн–пт = рабочие,
      - сб/вс = выходные.

    Сокращённые дни (*): считаем рабочими (записи не создаём).
    """
    url = BASE_URL.format(year=year)
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    # набор НЕРАБОЧИХ дней по производственному календарю
    non_working_dates = set()

    for month_info in data.get("months", []):
        month = month_info["month"]
        days_str = month_info.get("days", "")
        if not days_str:
            continue

        for item in days_str.split(","):
            raw = item.strip()
            if not raw:
                continue

            # сокращённый день (*) — рабочий, не добавляем в выходные
            if "*" in raw:
                continue

            # вытащить только цифры номера дня
            day_digits = ""
            for ch in raw:
                if ch.isdigit():
                    day_digits += ch
                else:
                    break

            if not day_digits:
                continue

            d = date(year, month, int(day_digits))
            non_working_dates.add(d)

    start = date(year, 1, 1)
    end = date(year, 12, 31)

    objs = []
    cur = start

    with transaction.atomic():
        # чистим старые исключения за этот год
        CalendarExceptions.objects.filter(date__year=year).delete()

        while cur <= end:
            weekday = cur.weekday()  # 0=пн ... 6=вс
            # базовое правило: будни рабочие, сб/вс выходные
            default_is_work = weekday < 5
            # по производственному календарю
            actual_is_work = cur not in non_working_dates

            # если статус отличается — это ИСКЛЮЧЕНИЕ → сохраняем
            if actual_is_work != default_is_work:
                objs.append(
                    CalendarExceptions(
                        date=cur,
                        is_working_day=actual_is_work,
                    )
                )

            cur += timedelta(days=1)

        CalendarExceptions.objects.bulk_create(objs)

    return len(objs)
