
from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd

from .config import (
    SALES_WINDOW_7D,
    SALES_WINDOW_30D,
    SALES_WINDOW_90D,
    MIN_ELASTICITY_DAYS,
    MIN_ELASTICITY_DAYS_AFTER_TRIM,
    MIN_PRICE_CV_PCT,
    SCENARIO_MIN_PCT,
    SCENARIO_MAX_PCT,
    SCENARIO_STEP_PCT,
    MIN_QTY_FACTOR,
    MAX_QTY_FACTOR,
    MIN_MARGIN_PCT,
    LOW_STOCK_DAYS,
    TARGET_STOCK_DAYS,
    HIGH_STOCK_DAYS,
    CLEARANCE_STOCK_DAYS,
    OLD_STOCK_DAYS,
    VERY_OLD_STOCK_DAYS,
    BALANCE_MARGIN_KEEP,
    MAX_MARGIN_LOSS_PP,
    MAX_PRIORITY,
)


def number(value, default=0.0):
    try:
        if value is None or pd.isna(value):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def pct_change(current, previous):
    current = number(current)
    previous = number(previous)

    if previous == 0:
        return None

    return (current / previous - 1.0) * 100.0


def clamp(value, low, high):
    return max(low, min(high, value))


def period_metrics(
    frame: pd.DataFrame,
    report_date: date,
    days: int,
) -> dict:
    start = report_date - timedelta(days=days - 1)

    if frame.empty:
        work = frame
    else:
        work = frame[
            pd.to_datetime(
                frame["date_from"],
                errors="coerce",
            ).dt.date.between(
                start,
                report_date,
            )
        ].copy()

    if work.empty:
        return {
            "days": days,
            "sales_qty": 0.0,
            "returns_qty": 0.0,
            "net_qty": 0.0,
            "seller_sales_amount": 0.0,
            "wb_sales_amount": 0.0,
            "amount": 0.0,
            "retail_amount": 0.0,
            "amount_vatless": 0.0,
            "cogs_man": 0.0,
            "net_comission": 0.0,
            "margin_man": 0.0,
            "seller_price": 0.0,
            "buyer_price": 0.0,
            "wb_price_delta_pct": None,
            "margin_pct": 0.0,
            "daily_sales_qty": 0.0,
        }

    sums = {}

    for field in (
        "sales_qty",
        "returns_qty",
        "net_qty",
        "seller_sales_amount",
        "wb_sales_amount",
        "amount",
        "retail_amount",
        "amount_vatless",
        "cogs_man",
        "net_comission",
        "margin_man",
    ):
        sums[field] = number(
            pd.to_numeric(
                work[field],
                errors="coerce",
            ).fillna(0).sum()
        )

    sales_qty = sums["sales_qty"]

    seller_price = (
        sums["seller_sales_amount"] / sales_qty
        if sales_qty > 0
        else 0.0
    )

    buyer_price = (
        sums["wb_sales_amount"] / sales_qty
        if sales_qty > 0
        else 0.0
    )

    wb_price_delta_pct = (
        (buyer_price / seller_price - 1.0) * 100.0
        if seller_price > 0 and buyer_price > 0
        else None
    )

    margin_pct = (
        sums["margin_man"]
        / sums["amount_vatless"]
        * 100.0
        if sums["amount_vatless"]
        else 0.0
    )

    return {
        "days": days,
        **sums,
        "seller_price": seller_price,
        "buyer_price": buyer_price,
        "wb_price_delta_pct": wb_price_delta_pct,
        "margin_pct": margin_pct,
        "daily_sales_qty": (
            sales_qty / max(days, 1)
        ),
    }


def estimate_elasticity(
    frame: pd.DataFrame,
) -> dict:
    """
    ln(Q) = a + b * ln(P)

    P = buyer_price, то есть фактическая цена реализации WB покупателю.
    Q = положительные продажи за день.

    Это наблюдаемая чувствительность, а не причинная оценка.
    """
    if frame.empty:
        return {
            "elasticity": None,
            "r2": None,
            "observations": 0,
            "price_cv_pct": 0.0,
            "confidence": "Нет данных",
        }

    work = frame.copy()

    work["sales_qty"] = pd.to_numeric(
        work["sales_qty"],
        errors="coerce",
    )

    work["buyer_price"] = pd.to_numeric(
        work["buyer_price"],
        errors="coerce",
    )

    work = work[
        (work["sales_qty"] >= 1)
        & (work["buyer_price"] > 0)
    ][
        [
            "date_from",
            "sales_qty",
            "buyer_price",
        ]
    ].dropna()

    if len(work) < MIN_ELASTICITY_DAYS:
        return {
            "elasticity": None,
            "r2": None,
            "observations": len(work),
            "price_cv_pct": 0.0,
            "confidence": "Мало наблюдений",
        }

    price_mean = float(
        work["buyer_price"].mean()
    )

    price_std = float(
        work["buyer_price"].std()
    )

    price_cv_pct = (
        price_std / price_mean * 100.0
        if price_mean
        else 0.0
    )

    if price_cv_pct < MIN_PRICE_CV_PCT:
        return {
            "elasticity": None,
            "r2": None,
            "observations": len(work),
            "price_cv_pct": price_cv_pct,
            "confidence": "Цена почти не менялась",
        }

    price_low = work[
        "buyer_price"
    ].quantile(
        0.025
    )

    price_high = work[
        "buyer_price"
    ].quantile(
        0.975
    )

    qty_low = work[
        "sales_qty"
    ].quantile(
        0.025
    )

    qty_high = work[
        "sales_qty"
    ].quantile(
        0.975
    )

    work = work[
        work["buyer_price"].between(
            price_low,
            price_high,
        )
        & work["sales_qty"].between(
            qty_low,
            qty_high,
        )
    ].copy()

    if len(work) < MIN_ELASTICITY_DAYS_AFTER_TRIM:
        return {
            "elasticity": None,
            "r2": None,
            "observations": len(work),
            "price_cv_pct": price_cv_pct,
            "confidence": "Мало наблюдений",
        }

    x = np.log(
        work["buyer_price"]
        .astype(float)
        .values
    )

    y = np.log(
        work["sales_qty"]
        .astype(float)
        .values
    )

    if (
        len(np.unique(x)) < 3
        or len(np.unique(y)) < 3
    ):
        return {
            "elasticity": None,
            "r2": None,
            "observations": len(work),
            "price_cv_pct": price_cv_pct,
            "confidence": "Недостаточно вариации",
        }

    slope, intercept = np.polyfit(
        x,
        y,
        1,
    )

    predicted = (
        intercept
        + slope * x
    )

    ss_res = float(
        np.sum(
            (y - predicted) ** 2
        )
    )

    ss_tot = float(
        np.sum(
            (y - y.mean()) ** 2
        )
    )

    r2 = (
        1.0 - ss_res / ss_tot
        if ss_tot
        else 0.0
    )

    elasticity = float(
        clamp(
            slope,
            -4.0,
            4.0,
        )
    )

    if (
        len(work) >= 30
        and r2 >= 0.35
    ):
        confidence = "Высокая"

    elif (
        len(work) >= 20
        and r2 >= 0.15
    ):
        confidence = "Средняя"

    else:
        confidence = "Низкая"

    return {
        "elasticity": elasticity,
        "r2": r2,
        "observations": len(work),
        "price_cv_pct": price_cv_pct,
        "confidence": confidence,
    }


def _qty_factor(
    buyer_price_factor,
    elasticity,
):
    if elasticity is None:
        return 1.0

    try:
        factor = (
            buyer_price_factor
            ** elasticity
        )
    except (
        ValueError,
        OverflowError,
        ZeroDivisionError,
    ):
        factor = 1.0

    return clamp(
        factor,
        MIN_QTY_FACTOR,
        MAX_QTY_FACTOR,
    )


def build_scenarios(
    current: dict,
    elasticity_info: dict,
    stock_on_hand: float,
) -> list[dict]:
    """
    Изменяем нашу цену и условно сохраняем текущий коэффициент:

        buyer_price / seller_price.

    То есть WB/СПП в сценарии пока не прогнозируется отдельно,
    а переносится пропорционально.
    """
    base_qty = number(
        current.get(
            "sales_qty"
        )
    )

    base_seller_price = number(
        current.get(
            "seller_price"
        )
    )

    base_buyer_price = number(
        current.get(
            "buyer_price"
        )
    )

    base_revenue_net = number(
        current.get(
            "amount_vatless"
        )
    )

    base_cogs = abs(
        number(
            current.get(
                "cogs_man"
            )
        )
    )

    base_commission = number(
        current.get(
            "net_comission"
        )
    )

    base_margin = number(
        current.get(
            "margin_man"
        )
    )

    if (
        base_qty <= 0
        or base_seller_price <= 0
        or base_revenue_net <= 0
    ):
        return []

    elasticity = elasticity_info.get(
        "elasticity"
    )

    revenue_net_per_unit = (
        base_revenue_net
        / base_qty
    )

    cogs_per_unit = (
        base_cogs
        / base_qty
    )

    commission_rate = (
        base_commission
        / base_revenue_net
        if base_revenue_net
        else 0.0
    )

    wb_factor = (
        base_buyer_price
        / base_seller_price
        if (
            base_seller_price > 0
            and base_buyer_price > 0
        )
        else 1.0
    )

    scenarios = []

    change_pct = SCENARIO_MIN_PCT

    while (
        change_pct
        <= SCENARIO_MAX_PCT + 0.0001
    ):
        price_factor = (
            1.0
            + change_pct / 100.0
        )

        if price_factor <= 0:
            change_pct += (
                SCENARIO_STEP_PCT
            )
            continue

        projected_seller_price = (
            base_seller_price
            * price_factor
        )

        projected_buyer_price = (
            projected_seller_price
            * wb_factor
        )

        buyer_price_factor = (
            projected_buyer_price
            / base_buyer_price
            if base_buyer_price > 0
            else price_factor
        )

        qty_factor = _qty_factor(
            buyer_price_factor,
            elasticity,
        )

        projected_qty = (
            base_qty
            * qty_factor
        )

        projected_revenue_net_per_unit = (
            revenue_net_per_unit
            * price_factor
        )

        projected_revenue_net = (
            projected_qty
            * projected_revenue_net_per_unit
        )

        projected_cogs = (
            projected_qty
            * cogs_per_unit
        )

        projected_commission = (
            projected_revenue_net
            * commission_rate
        )

        projected_margin = (
            projected_revenue_net
            - projected_cogs
            + projected_commission
        )

        projected_margin_pct = (
            projected_margin
            / projected_revenue_net
            * 100.0
            if projected_revenue_net
            else 0.0
        )

        projected_daily_qty = (
            projected_qty
            / max(
                number(
                    current.get(
                        "days"
                    ),
                    30,
                ),
                1,
            )
        )

        projected_stock_days = (
            stock_on_hand
            / projected_daily_qty
            if projected_daily_qty > 0
            else None
        )

        scenarios.append(
            {
                "price_change_pct": round(
                    change_pct,
                    2,
                ),
                "seller_price": (
                    projected_seller_price
                ),
                "buyer_price": (
                    projected_buyer_price
                ),
                "wb_factor": wb_factor,
                "projected_qty": (
                    projected_qty
                ),
                "qty_change_pct": (
                    (
                        projected_qty
                        / base_qty
                        - 1.0
                    )
                    * 100.0
                    if base_qty
                    else 0.0
                ),
                "projected_daily_qty": (
                    projected_daily_qty
                ),
                "projected_revenue_net": (
                    projected_revenue_net
                ),
                "projected_margin": (
                    projected_margin
                ),
                "projected_margin_pct": (
                    projected_margin_pct
                ),
                "margin_change_pct": (
                    (
                        projected_margin
                        / base_margin
                        - 1.0
                    )
                    * 100.0
                    if base_margin
                    else None
                ),
                "projected_stock_days": (
                    projected_stock_days
                ),
                "is_margin_safe": (
                    projected_margin_pct
                    >= MIN_MARGIN_PCT
                ),
            }
        )

        change_pct += (
            SCENARIO_STEP_PCT
        )

    return scenarios


def choose_recommendation(
    scenarios,
    elasticity_info,
    days_of_stock,
    stock_age_days,
):
    if not scenarios:
        return None

    current = min(
        scenarios,
        key=lambda row: abs(
            number(
                row.get(
                    "price_change_pct"
                )
            )
        ),
    )

    safe = [
        row
        for row in scenarios
        if row.get(
            "is_margin_safe"
        )
    ]

    if not safe:
        return current

    confidence = elasticity_info.get(
        "confidence"
    )

    low_confidence = confidence in (
        "Нет данных",
        "Мало наблюдений",
        "Цена почти не менялась",
        "Недостаточно вариации",
        "Низкая",
    )

    if low_confidence:
        if days_of_stock is None:
            target = -10.0
        elif (
            days_of_stock
            >= CLEARANCE_STOCK_DAYS
        ):
            target = -15.0
        elif (
            days_of_stock
            >= HIGH_STOCK_DAYS
        ):
            target = -10.0
        elif (
            days_of_stock
            <= LOW_STOCK_DAYS
        ):
            target = 5.0
        else:
            target = 0.0

        return min(
            safe,
            key=lambda row: abs(
                number(
                    row.get(
                        "price_change_pct"
                    )
                )
                - target
            ),
        )

    max_margin = max(
        safe,
        key=lambda row: number(
            row.get(
                "projected_margin"
            )
        ),
    )

    max_margin_value = number(
        max_margin.get(
            "projected_margin"
        )
    )

    current_margin_pct = number(
        current.get(
            "projected_margin_pct"
        )
    )

    candidates = [
        row
        for row in safe
        if (
            number(
                row.get(
                    "projected_margin"
                )
            )
            >= max_margin_value
            * BALANCE_MARGIN_KEEP
        )
        and (
            number(
                row.get(
                    "projected_margin_pct"
                )
            )
            >= current_margin_pct
            - MAX_MARGIN_LOSS_PP
        )
    ]

    if not candidates:
        candidates = [
            max_margin
        ]

    stock_pressure = (
        days_of_stock is None
        or days_of_stock >= HIGH_STOCK_DAYS
        or (
            stock_age_days is not None
            and stock_age_days
            >= OLD_STOCK_DAYS
        )
    )

    if stock_pressure:
        return max(
            candidates,
            key=lambda row: (
                number(
                    row.get(
                        "projected_daily_qty"
                    )
                ),
                number(
                    row.get(
                        "projected_margin"
                    )
                ),
            ),
        )

    return max(
        candidates,
        key=lambda row: number(
            row.get(
                "projected_margin"
            )
        ),
    )


def recommendation_status(
    change_pct,
    days_of_stock,
    stock_age_days,
    confidence,
):
    change_pct = number(
        change_pct
    )

    if (
        days_of_stock is not None
        and days_of_stock
        >= CLEARANCE_STOCK_DAYS
    ):
        return "CLEARANCE"

    if (
        stock_age_days is not None
        and stock_age_days
        >= VERY_OLD_STOCK_DAYS
        and (
            days_of_stock is None
            or days_of_stock
            >= HIGH_STOCK_DAYS
        )
    ):
        return "CLEARANCE"

    if confidence in (
        "Нет данных",
        "Мало наблюдений",
        "Цена почти не менялась",
        "Недостаточно вариации",
        "Низкая",
    ):
        if abs(change_pct) >= 2.5:
            return "TEST"

    if change_pct <= -2.5:
        return "REDUCE"

    if change_pct >= 2.5:
        return "RAISE"

    return "HOLD"


def confidence_score(
    elasticity_info,
    sales_qty_30,
):
    label = elasticity_info.get(
        "confidence"
    )

    score = {
        "Высокая": 90,
        "Средняя": 70,
        "Низкая": 45,
        "Цена почти не менялась": 35,
        "Недостаточно вариации": 30,
        "Мало наблюдений": 25,
        "Нет данных": 10,
    }.get(
        label,
        20,
    )

    if sales_qty_30 < 10:
        score = min(
            score,
            30,
        )

    return score


def priority_score(
    status,
    days_of_stock,
    stock_age_days,
    recommended_change_pct,
    margin_upside_day,
):
    score = {
        "CLEARANCE": 35,
        "REDUCE": 25,
        "TEST": 15,
        "RAISE": 12,
        "HOLD": 0,
    }.get(
        status,
        0,
    )

    if days_of_stock is None:
        score += 20
    else:
        score += min(
            max(
                days_of_stock
                - TARGET_STOCK_DAYS,
                0,
            )
            / 8.0,
            30,
        )

    if stock_age_days is not None:
        score += min(
            stock_age_days / 25.0,
            15,
        )

    score += min(
        abs(
            number(
                recommended_change_pct
            )
        ),
        15,
    )

    if margin_upside_day > 0:
        score += min(
            margin_upside_day / 1000.0,
            10,
        )

    return round(
        min(
            score,
            MAX_PRIORITY,
        ),
        1,
    )


def build_reason(
    change_pct,
    days_of_stock,
    stock_age_days,
    m7,
    m30,
    elasticity_info,
    recommended_buyer_price,
):
    parts = []

    if days_of_stock is None:
        parts.append(
            "нет устойчивой скорости продаж для расчёта запаса"
        )
    elif (
        days_of_stock
        >= CLEARANCE_STOCK_DAYS
    ):
        parts.append(
            f"запас около {days_of_stock:.0f} дней"
        )
    elif (
        days_of_stock
        >= HIGH_STOCK_DAYS
    ):
        parts.append(
            f"повышенный запас: {days_of_stock:.0f} дней"
        )
    elif (
        days_of_stock
        <= LOW_STOCK_DAYS
    ):
        parts.append(
            f"низкий запас: {days_of_stock:.0f} дней"
        )
    else:
        parts.append(
            f"запас: {days_of_stock:.0f} дней"
        )

    if (
        stock_age_days is not None
        and stock_age_days
        >= OLD_STOCK_DAYS
    ):
        parts.append(
            f"возраст остатка {stock_age_days} дней"
        )

    elasticity = elasticity_info.get(
        "elasticity"
    )

    if elasticity is not None:
        parts.append(
            (
                f"эластичность по цене покупателя "
                f"{elasticity:.2f}, "
                f"R² {number(elasticity_info.get('r2')):.2f}"
            )
        )
    else:
        parts.append(
            (
                "эластичность пока ненадёжна: "
                f"{elasticity_info.get('confidence')}"
            )
        )

    speed_change = pct_change(
        number(
            m7.get(
                "daily_sales_qty"
            )
        ),
        number(
            m30.get(
                "daily_sales_qty"
            )
        ),
    )

    if (
        speed_change is not None
        and speed_change <= -20
    ):
        parts.append(
            (
                f"скорость 7д ниже 30д "
                f"на {abs(speed_change):.0f}%"
            )
        )

    elif (
        speed_change is not None
        and speed_change >= 20
    ):
        parts.append(
            (
                f"скорость 7д выше 30д "
                f"на {speed_change:.0f}%"
            )
        )

    current_buyer = number(
        m30.get(
            "buyer_price"
        )
    )

    if (
        current_buyer > 0
        and recommended_buyer_price > 0
    ):
        parts.append(
            (
                f"цена покупателя "
                f"{current_buyer:.0f} → "
                f"{recommended_buyer_price:.0f} ₽"
            )
        )

    if change_pct:
        parts.append(
            (
                f"рекомендованное изменение нашей цены "
                f"{change_pct:+.1f}%"
            )
        )
    else:
        parts.append(
            "текущая цена близка к выбранному балансу"
        )

    return "; ".join(
        parts
    ) + "."


def analyze_pricing(
    source: dict,
) -> dict:
    products = source[
        "products"
    ].copy()

    daily = source[
        "daily"
    ].copy()

    report_date = source[
        "report_date"
    ]

    if products.empty:
        return {
            **source,
            "recommendations": pd.DataFrame(),
            "scenarios": pd.DataFrame(),
            "history": daily,
            "summary": {},
        }

    if not daily.empty:
        daily[
            "date_from"
        ] = pd.to_datetime(
            daily[
                "date_from"
            ],
            errors="coerce",
        ).dt.date

    recommendations = []
    scenario_rows = []

    for _, product in products.iterrows():
        nm_id = product[
            "nm_id"
        ]

        history = (
            daily[
                daily["nm_id"]
                == nm_id
            ].copy()
            if not daily.empty
            else pd.DataFrame()
        )

        m7 = period_metrics(
            history,
            report_date,
            SALES_WINDOW_7D,
        )

        m30 = period_metrics(
            history,
            report_date,
            SALES_WINDOW_30D,
        )

        m90 = period_metrics(
            history,
            report_date,
            SALES_WINDOW_90D,
        )

        elasticity_info = estimate_elasticity(
            history
        )

        stock_on_hand = number(
            product.get(
                "stock_on_hand"
            )
        )

        stock_in_transit = number(
            product.get(
                "stock_in_transit"
            )
        )

        stock_total = number(
            product.get(
                "stock_total"
            )
        )

        daily_qty_30 = number(
            m30.get(
                "daily_sales_qty"
            )
        )

        days_of_stock = (
            stock_on_hand
            / daily_qty_30
            if daily_qty_30 > 0
            else None
        )

        raw_income = product.get(
            "last_income_date"
        )

        stock_age_days = None

        if (
            raw_income is not None
            and not pd.isna(
                raw_income
            )
        ):
            parsed = pd.to_datetime(
                raw_income,
                errors="coerce",
            )

            if not pd.isna(
                parsed
            ):
                stock_age_days = (
                    report_date
                    - parsed.date()
                ).days

        scenarios = build_scenarios(
            current=m30,
            elasticity_info=elasticity_info,
            stock_on_hand=stock_on_hand,
        )

        recommended = choose_recommendation(
            scenarios=scenarios,
            elasticity_info=elasticity_info,
            days_of_stock=days_of_stock,
            stock_age_days=stock_age_days,
        )

        if recommended:
            recommended_change_pct = number(
                recommended.get(
                    "price_change_pct"
                )
            )

            recommended_seller_price = number(
                recommended.get(
                    "seller_price"
                )
            )

            recommended_buyer_price = number(
                recommended.get(
                    "buyer_price"
                )
            )

            recommended_margin = number(
                recommended.get(
                    "projected_margin"
                )
            )

            recommended_margin_pct = number(
                recommended.get(
                    "projected_margin_pct"
                )
            )

            recommended_stock_days = (
                recommended.get(
                    "projected_stock_days"
                )
            )

        else:
            recommended_change_pct = 0.0
            recommended_seller_price = number(
                m30.get(
                    "seller_price"
                )
            )
            recommended_buyer_price = number(
                m30.get(
                    "buyer_price"
                )
            )
            recommended_margin = number(
                m30.get(
                    "margin_man"
                )
            )
            recommended_margin_pct = number(
                m30.get(
                    "margin_pct"
                )
            )
            recommended_stock_days = days_of_stock

        current_margin = number(
            m30.get(
                "margin_man"
            )
        )

        margin_upside_30d = (
            recommended_margin
            - current_margin
        )

        margin_upside_day = (
            margin_upside_30d
            / SALES_WINDOW_30D
        )

        status = recommendation_status(
            change_pct=(
                recommended_change_pct
            ),
            days_of_stock=days_of_stock,
            stock_age_days=stock_age_days,
            confidence=elasticity_info.get(
                "confidence"
            ),
        )

        confidence = confidence_score(
            elasticity_info,
            number(
                m30.get(
                    "sales_qty"
                )
            ),
        )

        priority = priority_score(
            status=status,
            days_of_stock=days_of_stock,
            stock_age_days=stock_age_days,
            recommended_change_pct=(
                recommended_change_pct
            ),
            margin_upside_day=(
                margin_upside_day
            ),
        )

        reason = build_reason(
            change_pct=(
                recommended_change_pct
            ),
            days_of_stock=days_of_stock,
            stock_age_days=stock_age_days,
            m7=m7,
            m30=m30,
            elasticity_info=elasticity_info,
            recommended_buyer_price=(
                recommended_buyer_price
            ),
        )

        speed_trend = pct_change(
            number(
                m7.get(
                    "daily_sales_qty"
                )
            ),
            number(
                m30.get(
                    "daily_sales_qty"
                )
            ),
        )

        wb_delta = m30.get(
            "wb_price_delta_pct"
        )

        recommendations.append(
            {
                "priority": priority,
                "status": status,
                "confidence_score": (
                    confidence
                ),

                "nm_id": (
                    int(nm_id)
                    if pd.notna(nm_id)
                    else nm_id
                ),

                "sa_name": product.get(
                    "sa_name",
                    "",
                ),
                "brand": product.get(
                    "brand",
                    "",
                ),
                "category": product.get(
                    "category",
                    "",
                ),
                "gender": product.get(
                    "gender",
                    "",
                ),
                "title": product.get(
                    "title",
                    "",
                ),

                "current_seller_list_price": round(
                    number(
                        product.get(
                            "current_seller_list_price"
                        )
                    ),
                    2,
                ),

                "seller_price_30d": round(
                    number(
                        m30.get(
                            "seller_price"
                        )
                    ),
                    2,
                ),

                "buyer_price_30d": round(
                    number(
                        m30.get(
                            "buyer_price"
                        )
                    ),
                    2,
                ),

                "wb_price_delta_pct_30d": (
                    round(
                        number(
                            wb_delta
                        ),
                        2,
                    )
                    if wb_delta is not None
                    else None
                ),

                "latest_seller_realized_price": round(
                    number(
                        product.get(
                            "latest_seller_realized_price"
                        )
                    ),
                    2,
                ),

                "latest_buyer_price": round(
                    number(
                        product.get(
                            "latest_buyer_price"
                        )
                    ),
                    2,
                ),

                "recommended_change_pct": round(
                    recommended_change_pct,
                    1,
                ),

                "recommended_seller_price": round(
                    recommended_seller_price,
                    2,
                ),

                "recommended_buyer_price": round(
                    recommended_buyer_price,
                    2,
                ),

                "amount_vatless_30d": round(
                    number(
                        m30.get(
                            "amount_vatless"
                        )
                    ),
                    2,
                ),

                "cogs_man_30d": round(
                    number(
                        m30.get(
                            "cogs_man"
                        )
                    ),
                    2,
                ),

                "net_comission_30d": round(
                    number(
                        m30.get(
                            "net_comission"
                        )
                    ),
                    2,
                ),

                "margin_man_30d": round(
                    current_margin,
                    2,
                ),

                "margin_pct_30d": round(
                    number(
                        m30.get(
                            "margin_pct"
                        )
                    ),
                    2,
                ),

                "recommended_margin_30d": round(
                    recommended_margin,
                    2,
                ),

                "recommended_margin_pct": round(
                    recommended_margin_pct,
                    2,
                ),

                "margin_upside_30d": round(
                    margin_upside_30d,
                    2,
                ),

                "margin_upside_day": round(
                    margin_upside_day,
                    2,
                ),

                "stock_on_hand": round(
                    stock_on_hand,
                    0,
                ),

                "stock_in_transit": round(
                    stock_in_transit,
                    0,
                ),

                "stock_total": round(
                    stock_total,
                    0,
                ),

                "days_of_stock": (
                    round(
                        days_of_stock,
                        1,
                    )
                    if days_of_stock is not None
                    else None
                ),

                "recommended_stock_days": (
                    round(
                        number(
                            recommended_stock_days
                        ),
                        1,
                    )
                    if recommended_stock_days is not None
                    else None
                ),

                "stock_age_days": (
                    int(
                        stock_age_days
                    )
                    if stock_age_days is not None
                    else None
                ),

                "last_income_date": raw_income,

                "sales_qty_7d": round(
                    number(
                        m7.get(
                            "sales_qty"
                        )
                    ),
                    0,
                ),

                "sales_qty_30d": round(
                    number(
                        m30.get(
                            "sales_qty"
                        )
                    ),
                    0,
                ),

                "sales_qty_90d": round(
                    number(
                        m90.get(
                            "sales_qty"
                        )
                    ),
                    0,
                ),

                "daily_sales_qty_30d": round(
                    daily_qty_30,
                    2,
                ),

                "sales_speed_trend_pct": (
                    round(
                        speed_trend,
                        1,
                    )
                    if speed_trend is not None
                    else None
                ),

                "elasticity": (
                    round(
                        number(
                            elasticity_info.get(
                                "elasticity"
                            )
                        ),
                        3,
                    )
                    if elasticity_info.get(
                        "elasticity"
                    ) is not None
                    else None
                ),

                "elasticity_r2": (
                    round(
                        number(
                            elasticity_info.get(
                                "r2"
                            )
                        ),
                        3,
                    )
                    if elasticity_info.get(
                        "r2"
                    ) is not None
                    else None
                ),

                "elasticity_observations": int(
                    elasticity_info.get(
                        "observations",
                        0,
                    )
                ),

                "price_cv_pct": round(
                    number(
                        elasticity_info.get(
                            "price_cv_pct"
                        )
                    ),
                    2,
                ),

                "elasticity_confidence": (
                    elasticity_info.get(
                        "confidence"
                    )
                ),

                "reason": reason,
            }
        )

        for scenario in scenarios:
            scenario_rows.append(
                {
                    "nm_id": (
                        int(nm_id)
                        if pd.notna(nm_id)
                        else nm_id
                    ),
                    "brand": product.get(
                        "brand",
                        "",
                    ),
                    "title": product.get(
                        "title",
                        "",
                    ),
                    **scenario,
                }
            )

    recommendations_df = pd.DataFrame(
        recommendations
    )

    if not recommendations_df.empty:
        recommendations_df = (
            recommendations_df
            .sort_values(
                by=[
                    "priority",
                    "stock_on_hand",
                ],
                ascending=[
                    False,
                    False,
                ],
            )
            .reset_index(
                drop=True
            )
        )

    scenarios_df = pd.DataFrame(
        scenario_rows
    )

    if recommendations_df.empty:
        summary = {}

    else:
        summary = {
            "products": int(
                len(
                    recommendations_df
                )
            ),

            "action_products": int(
                recommendations_df[
                    "status"
                ].isin(
                    [
                        "CLEARANCE",
                        "REDUCE",
                        "RAISE",
                        "TEST",
                    ]
                ).sum()
            ),

            "clearance_products": int(
                (
                    recommendations_df[
                        "status"
                    ]
                    == "CLEARANCE"
                ).sum()
            ),

            "high_stock_products": int(
                (
                    pd.to_numeric(
                        recommendations_df[
                            "days_of_stock"
                        ],
                        errors="coerce",
                    )
                    >= HIGH_STOCK_DAYS
                ).sum()
            ),

            "stock_units": float(
                pd.to_numeric(
                    recommendations_df[
                        "stock_on_hand"
                    ],
                    errors="coerce",
                )
                .fillna(0)
                .sum()
            ),

            "margin_upside_day": float(
                pd.to_numeric(
                    recommendations_df[
                        "margin_upside_day"
                    ],
                    errors="coerce",
                )
                .fillna(0)
                .clip(
                    lower=0
                )
                .sum()
            ),
        }

    return {
        **source,
        "recommendations": recommendations_df,
        "scenarios": scenarios_df,
        "history": daily,
        "summary": summary,
    }
