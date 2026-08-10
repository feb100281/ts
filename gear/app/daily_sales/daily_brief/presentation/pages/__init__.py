# gear/app/daily_sales/daily_brief/presentation/pages/__init__.py

from .first_page import build_first_page
from .plans_page import build_plans_page
from .stocks_page import build_stocks_page
from .incidents_page import build_incidents_page
from .financial_page import build_financial_page
from .demand_page import build_demand_page
from .sales_dynamics_page import build_sales_dynamics_page
from .price_page import build_price_page



__all__ = [
    "build_first_page",
    "build_plans_page",
    "build_stocks_page",
    "build_incidents_page",
    "build_financial_page",
    "build_demand_page",
    "build_sales_dynamics_page",
    "build_price_page",
]