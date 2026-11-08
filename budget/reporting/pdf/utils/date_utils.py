# budget/reporting/pdf/utils/date_utils.py

from calendar import monthrange
from datetime import date


def month_start(dt: date) -> date:
    return dt.replace(day=1)


def month_end(dt: date) -> date:
    return dt.replace(day=monthrange(dt.year, dt.month)[1])


def same_day_or_month_end(target_month_start: date, reference_day: int) -> date:
    last_day = monthrange(target_month_start.year, target_month_start.month)[1]
    return target_month_start.replace(day=min(reference_day, last_day))