# gear/app/daily_sales/daily_brief/presentation/pages/__init__.py

from .first_page import build_first_page
from .plans_page import build_plans_page
from .stocks_page import build_stocks_page
from .incidents_page import build_incidents_page


__all__ = [
    "build_first_page",
    "build_plans_page",
    "build_stocks_page",
    "build_incidents_page",
]