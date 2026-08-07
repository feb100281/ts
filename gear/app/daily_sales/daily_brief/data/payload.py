# gear/app/daily_sales/daily_brief/data/payload.py

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import pandas as pd

from ..editorial import (
    build_editorial,
    build_recommendations,
)
from ..helpers import json_safe
from .incidents import get_incidents_data
from .plan import (
    get_half_year_plan,
    get_month_plan,
    get_plan_source,
    get_prophet_plan_forecast,
)
from .sales import get_sales_data
from .stocks import get_stock_data


def build_daily_brief_payload(
    report_date: date | str,
) -> dict[str, Any]:
    parsed = pd.to_datetime(
        report_date,
        errors="coerce",
    )

    if pd.isna(parsed):
        parsed = pd.Timestamp(
            date.today()
            - timedelta(days=1)
        )

    report_date = parsed.date()

    # =====================================================================
    # ОСНОВНЫЕ ИСТОЧНИКИ
    # =====================================================================

    plan_source = get_plan_source(
        report_date
    )

    sales = get_sales_data(
        report_date,
        plan_source,
    )

    plan = get_month_plan(
        plan_source
    )

    half_year_plan = get_half_year_plan(
        report_date,
        plan_source,
    )

    stocks = get_stock_data(
        report_date
    )

    incidents = get_incidents_data(
        report_date
    )

    # =====================================================================
    # PROPHET
    #
    # Модель обучается на последних 90 календарных днях и строит прогноз
    # с даты отчёта до конца года.
    # =====================================================================

    prophet_plan = get_prophet_plan_forecast(
        report_date,
        training_days=90,
    )

    # =====================================================================
    # БАЗОВЫЙ PAYLOAD
    # =====================================================================

    payload: dict[str, Any] = {
        "report_date": (
            report_date.isoformat()
        ),
        "generated_at": (
            pd.Timestamp.now().isoformat()
        ),
        "sales": sales,
        "plan": plan,
        "half_year_wb_plan": (
            half_year_plan
        ),
        "prophet_plan": (
            prophet_plan
        ),
        "stocks": stocks,
        "incidents": incidents,
    }

    # =====================================================================
    # РЕДАКЦИОННЫЕ ТЕКСТЫ
    # =====================================================================

    payload["editorial"] = build_editorial(
        report_date,
        sales,
        plan,
        stocks,
        half_year_plan,
    )

    # =====================================================================
    # РЕКОМЕНДАЦИИ
    # =====================================================================

    payload["recommendations"] = (
        build_recommendations(
            payload
        )
    )

    return json_safe(
        payload
    )