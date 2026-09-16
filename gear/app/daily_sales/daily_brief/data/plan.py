# gear/app/daily_sales/daily_brief/data/plan.py

from __future__ import annotations

from calendar import monthrange
from datetime import date, timedelta
from typing import Any

from gear.app.daily_sales.wb_plan_monitor.data import (
    build_current_month_analysis,
    calculate_period_plan_to_date,
    get_budget_version,
    get_daily_fact,
    get_fact_for_period,
    get_monthly_plan_full_year,
    get_semi_periods,
)

from ..helpers import (
    json_safe,
    number,
)

from gear.app.daily_sales.wb_plan_monitor.prophet_forecast import (
    build_forecast,
)


MONTHS_SHORT = {
    1: "янв",
    2: "фев",
    3: "мар",
    4: "апр",
    5: "май",
    6: "июн",
    7: "июл",
    8: "авг",
    9: "сен",
    10: "окт",
    11: "ноя",
    12: "дек",
}


# =============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# =============================================================================


def _extract_month_plan(
    monthly_plan: Any,
    month_number: int,
) -> float:
    """
    Получает план конкретного месяца из monthly_plan.

    Поддерживает несколько форматов:

    1. Словарь:
       {
           1: 100_000_000,
           2: 110_000_000,
       }

    2. Словарь со строковыми ключами:
       {
           "1": 100_000_000,
           "01": 100_000_000,
           "jan": ...
       }

    3. Словарь со вложенными объектами:
       {
           1: {
               "plan": 100_000_000
           }
       }

    4. Список строк:
       [
           {
               "month": 1,
               "plan": 100_000_000
           }
       ]
    """

    if not monthly_plan:
        return 0.0

    # -------------------------------------------------------------------------
    # monthly_plan — словарь
    # -------------------------------------------------------------------------

    if isinstance(
        monthly_plan,
        dict,
    ):
        possible_keys = (
            month_number,
            str(month_number),
            f"{month_number:02d}",
            MONTHS_SHORT.get(
                month_number,
                "",
            ),
        )

        for key in possible_keys:
            if key not in monthly_plan:
                continue

            raw_value = monthly_plan.get(
                key
            )

            if isinstance(
                raw_value,
                dict,
            ):
                return number(
                    raw_value.get(
                        "plan",
                        raw_value.get(
                            "amount",
                            raw_value.get(
                                "value",
                                raw_value.get(
                                    "month_plan",
                                    0,
                                ),
                            ),
                        ),
                    )
                )

            return number(
                raw_value
            )

        # Иногда словарь может содержать список в отдельном ключе.
        for rows_key in (
            "rows",
            "months",
            "monthly_rows",
            "data",
        ):
            nested_rows = monthly_plan.get(
                rows_key
            )

            if isinstance(
                nested_rows,
                (list, tuple),
            ):
                return _extract_month_plan(
                    nested_rows,
                    month_number,
                )

        return 0.0

    # -------------------------------------------------------------------------
    # monthly_plan — список
    # -------------------------------------------------------------------------

    if isinstance(
        monthly_plan,
        (list, tuple),
    ):
        for row in monthly_plan:
            if not isinstance(
                row,
                dict,
            ):
                continue

            row_month = row.get(
                "month",
                row.get(
                    "month_number",
                    row.get(
                        "month_num",
                    ),
                ),
            )

            try:
                row_month = int(
                    row_month
                )

            except (
                TypeError,
                ValueError,
            ):
                row_month = None

            if row_month != month_number:
                continue

            return number(
                row.get(
                    "plan",
                    row.get(
                        "amount",
                        row.get(
                            "value",
                            row.get(
                                "month_plan",
                                0,
                            ),
                        ),
                    ),
                )
            )

    return 0.0


def _build_monthly_plan_fact_rows(
    *,
    report_date: date,
    monthly_plan: Any,
) -> list[dict[str, Any]]:
    """
    Формирует план/факт по всем 12 месяцам года.

    Для завершённых месяцев:
        факт берётся за полный месяц.

    Для текущего месяца:
        факт берётся с первого числа по report_date.

    Для будущих месяцев:
        факт равен нулю.

    Дополнительно рассчитываются:
        running_plan
        running_fact
        running_exec_pct
    """

    result: list[dict[str, Any]] = []

    running_plan = 0.0
    running_fact = 0.0

    for month_number in range(
        1,
        13,
    ):
        month_start = date(
            report_date.year,
            month_number,
            1,
        )

        month_finish = date(
            report_date.year,
            month_number,
            monthrange(
                report_date.year,
                month_number,
            )[1],
        )

        plan_amount = _extract_month_plan(
            monthly_plan,
            month_number,
        )

        # ---------------------------------------------------------------------
        # Факт месяца
        # ---------------------------------------------------------------------

        if month_start > report_date:
            # Будущий месяц.
            fact_amount = 0.0

        else:
            effective_finish = min(
                month_finish,
                report_date,
            )

            fact_amount = number(
                get_fact_for_period(
                    month_start,
                    effective_finish,
                )
            )

        running_plan += plan_amount
        running_fact += fact_amount

        running_exec_pct = (
            running_fact
            / running_plan
            * 100
            if running_plan
            else 0.0
        )

        month_exec_pct = (
            fact_amount
            / plan_amount
            * 100
            if plan_amount
            else 0.0
        )

        month_delta = (
            fact_amount
            - plan_amount
        )

        result.append(
            {
                "year": report_date.year,
                "month": month_number,
                "month_short": MONTHS_SHORT[
                    month_number
                ],
                "date_start": json_safe(
                    month_start
                ),
                "date_finish": json_safe(
                    month_finish
                ),
                "plan": plan_amount,
                "fact": fact_amount,
                "delta": month_delta,
                "month_exec_pct": (
                    month_exec_pct
                ),
                "running_plan": (
                    running_plan
                ),
                "running_fact": (
                    running_fact
                ),
                "running_exec_pct": (
                    running_exec_pct
                ),
                "is_current": (
                    month_number
                    == report_date.month
                ),
                "is_closed": (
                    month_finish
                    < report_date
                ),
                "is_future": (
                    month_start
                    > report_date
                ),
            }
        )

    return result


# =============================================================================
# ОБЩИЙ ИСТОЧНИК ПЛАНОВЫХ ДАННЫХ
# =============================================================================


def get_plan_source(
    report_date: date,
) -> dict[str, Any]:
    version = get_budget_version()

    if version is None:
        return {
            "available": False,
            "reason": (
                "Не найдена бюджетная версия."
            ),
            "daily_rows": [],
            "monthly_rows": [],
        }

    monthly_plan = (
        get_monthly_plan_full_year(
            version_id=version.id,
            year=report_date.year,
        )
    )

    daily_rows = get_daily_fact(
        year=report_date.year,
        month=report_date.month,
        up_to_day=report_date.day,
    )

    current_month = (
        build_current_month_analysis(
            report_date=report_date,
            monthly_plan=monthly_plan,
            daily_raw=daily_rows,
        )
    )

    monthly_rows = (
        _build_monthly_plan_fact_rows(
            report_date=report_date,
            monthly_plan=monthly_plan,
        )
    )

    return {
        "available": True,
        "version_id": version.id,
        "version_date": json_safe(
            version.date_from
        ),
        "daily_rows": daily_rows,
        "current_month": current_month,
        "monthly_plan": monthly_plan,
        "monthly_rows": monthly_rows,
    }


# =============================================================================
# ПЛАН ТЕКУЩЕГО МЕСЯЦА
# =============================================================================


def get_month_plan(
    plan_source: dict[str, Any],
) -> dict[str, Any]:
    if not plan_source.get(
        "available"
    ):
        return {
            "available": False,
            "reason": plan_source.get(
                "reason"
            ),
            "rows": [],
            "monthly_rows": [],
        }

    analysis = plan_source.get(
        "current_month",
        {},
    )

    return {
        "available": True,
        "label": analysis.get(
            "label"
        ),
        "month_plan": number(
            analysis.get(
                "month_plan"
            )
        ),
        "daily_plan": number(
            analysis.get(
                "daily_plan"
            )
        ),
        "plan_to_date": number(
            analysis.get(
                "plan_to_date"
            )
        ),
        "fact_to_date": number(
            analysis.get(
                "fact_to_date"
            )
        ),
        "exec_to_date_pct": number(
            analysis.get(
                "exec_to_date_pct"
            )
        ),
        "month_exec_pct": number(
            analysis.get(
                "month_exec_pct"
            )
        ),
        "delta_to_date": number(
            analysis.get(
                "delta_to_date"
            )
        ),
        "remaining_month": number(
            analysis.get(
                "remaining_month"
            )
        ),
        "required_daily_rate": number(
            analysis.get(
                "required_daily_rate"
            )
        ),
        "remaining_days": int(
            number(
                analysis.get(
                    "remaining_days"
                )
            )
        ),
        "rows": [
            {
                "date": json_safe(
                    row.get(
                        "date"
                    )
                ),
                "date_label": row.get(
                    "date_label"
                ),
                "fact": number(
                    row.get(
                        "fact"
                    )
                ),
                "running_fact": number(
                    row.get(
                        "running_fact"
                    )
                ),
                "running_plan": number(
                    row.get(
                        "running_plan"
                    )
                ),
                "exec_to_date_pct": number(
                    row.get(
                        "exec_to_date_pct"
                    )
                ),
            }
            for row in analysis.get(
                "rows",
                [],
            )
        ],
        # Эти данные нужны для графика январь–декабрь.
        "monthly_rows": (
            plan_source.get(
                "monthly_rows",
                [],
            )
        ),
    }


# =============================================================================
# ПЛАН ПОЛУГОДИЯ
# =============================================================================


def get_half_year_plan(
    report_date: date,
    plan_source: dict[str, Any],
) -> dict[str, Any]:
    if not plan_source.get(
        "available"
    ):
        return {
            "available": False,
            "reason": plan_source.get(
                "reason"
            ),
            "monthly_rows": [],
        }

    monthly_plan = plan_source.get(
        "monthly_plan",
        {},
    )

    periods = get_semi_periods(
        report_date.year,
        monthly_plan,
    )

    current_period = next(
        (
            period
            for period in periods
            if (
                period["start"]
                <= report_date
                <= period["end"]
            )
        ),
        None,
    )

    if current_period is None:
        return {
            "available": False,
            "reason": (
                "Не найден план полугодия."
            ),
            "monthly_rows": (
                plan_source.get(
                    "monthly_rows",
                    [],
                )
            ),
        }

    effective_date = min(
        report_date,
        current_period["end"],
    )

    plan_amount = number(
        current_period.get(
            "plan"
        )
    )

    fact_amount = number(
        get_fact_for_period(
            current_period["start"],
            effective_date,
        )
    )

    plan_to_date = number(
        calculate_period_plan_to_date(
            period=current_period,
            monthly_plan=monthly_plan,
            report_date=effective_date,
        )
    )

    execution_pct = (
        fact_amount
        / plan_amount
        * 100
        if plan_amount
        else 0.0
    )

    execution_to_date_pct = (
        fact_amount
        / plan_to_date
        * 100
        if plan_to_date
        else 0.0
    )

    remaining_amount = max(
        plan_amount
        - fact_amount,
        0,
    )

    total_days = (
        current_period["end"]
        - current_period["start"]
    ).days + 1

    elapsed_days = (
        effective_date
        - current_period["start"]
    ).days + 1

    calendar_pct = (
        elapsed_days
        / total_days
        * 100
        if total_days
        else 0.0
    )

    days_remaining = max(
        (
            current_period["end"]
            - effective_date
        ).days,
        0,
    )

    required_daily_rate = (
        remaining_amount
        / days_remaining
        if days_remaining
        else 0.0
    )

    # -------------------------------------------------------------------------
    # Все месяцы года
    # -------------------------------------------------------------------------

    all_monthly_rows = list(
        plan_source.get(
            "monthly_rows",
            [],
        )
        or []
    )

    # -------------------------------------------------------------------------
    # Месяцы только текущего полугодия
    # -------------------------------------------------------------------------

    period_monthly_rows = [
        row
        for row in all_monthly_rows
        if (
            current_period["start"].month
            <= int(
                number(
                    row.get(
                        "month"
                    )
                )
            )
            <= current_period["end"].month
        )
    ]

    return {
        "available": True,
        "label": current_period[
            "label"
        ],
        "date_start": json_safe(
            current_period["start"]
        ),
        "date_finish": json_safe(
            current_period["end"]
        ),
        "plan_amount": plan_amount,
        "fact_amount": fact_amount,
        "plan_to_date": plan_to_date,
        "execution_pct": (
            execution_pct
        ),
        "execution_to_date_pct": (
            execution_to_date_pct
        ),
        "remaining_amount": (
            remaining_amount
        ),
        "calendar_pct": (
            calendar_pct
        ),
        "pace_delta_pp": (
            execution_pct
            - calendar_pct
        ),
        "days_remaining": (
            days_remaining
        ),
        "required_daily_rate": (
            required_daily_rate
        ),
        "status": (
            "ahead"
            if execution_to_date_pct >= 100
            else "behind"
        ),

        # Все 12 месяцев — для газетного графика январь–декабрь.
        "monthly_rows": (
            all_monthly_rows
        ),

        # Только месяцы текущего полугодия —
        # пригодятся для дополнительной аналитики.
        "period_monthly_rows": (
            period_monthly_rows
        ),
    }
    
    

def get_prophet_plan_forecast(
    report_date: date,
    *,
    training_days: int = 90,
) -> dict[str, Any]:
    """
    Автоматический газетный прогноз Prophet.

    Модель обучается на последних 90 календарных днях
    и строит прогноз до конца года.

    Параметры соответствуют базовому сценарию:
        growth_pct = 0
        changepoint_prior_scale = 0.05
        seasonality_prior_scale = 10
        interval_width = 0.80
        seasonality_mode = multiplicative
        clip_outliers = True
    """

    date_start = (
        report_date
        - timedelta(
            days=max(
                training_days - 1,
                29,
            )
        )
    )

    forecast_end = date(
        report_date.year,
        12,
        31,
    )

    try:
        result = build_forecast(
            date_start=date_start,
            date_end=report_date,
            forecast_end=forecast_end,
            growth_pct=0.0,
            changepoint_prior_scale=0.05,
            seasonality_prior_scale=10.0,
            interval_width=0.80,
            seasonality_mode="multiplicative",
            clip_outliers=True,
        )

    except Exception as exc:
        return {
            "available": False,
            "reason": str(exc),
            "params": {
                "training_days": training_days,
                "date_start": json_safe(
                    date_start
                ),
                "date_end": json_safe(
                    report_date
                ),
                "forecast_end": json_safe(
                    forecast_end
                ),
            },
            "metrics": {},
            "monthly": [],
        }

    metrics = dict(
        result.get(
            "metrics",
            {},
        )
        or {}
    )

    monthly = list(
        result.get(
            "monthly",
            [],
        )
        or []
    )

    return {
        "available": True,
        "params": {
            **dict(
                result.get(
                    "params",
                    {},
                )
                or {}
            ),
            "training_days": (
                training_days
            ),
        },
        "metrics": {
            key: number(value)
            for key, value in metrics.items()
        },
        "monthly": [
            {
                "month": row.get(
                    "month"
                ),
                "plan": number(
                    row.get(
                        "plan"
                    )
                ),
                "fact": number(
                    row.get(
                        "fact"
                    )
                ),
                "forecast": number(
                    row.get(
                        "forecast"
                    )
                ),
                "expected_total": number(
                    row.get(
                        "expected_total"
                    )
                ),
                "expected_lower": number(
                    row.get(
                        "expected_lower"
                    )
                ),
                "expected_upper": number(
                    row.get(
                        "expected_upper"
                    )
                ),
                "delta_to_plan": number(
                    row.get(
                        "delta_to_plan"
                    )
                ),
                "plan_exec_pct": number(
                    row.get(
                        "plan_exec_pct"
                    )
                ),
            }
            for row in monthly
        ],
    }