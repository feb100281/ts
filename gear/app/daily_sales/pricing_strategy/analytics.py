# gear/app/daily_sales/pricing_strategy/analytics.py

from __future__ import annotations

from datetime import timedelta

import numpy as np
import pandas as pd

from .config import (
    SALES_WINDOW_7D,
    SALES_WINDOW_30D,
    SALES_WINDOW_90D,

    MIN_ELASTICITY_DAYS,
    MIN_PRICE_CV_PCT,

    SCENARIO_MIN_PCT,
    SCENARIO_MAX_PCT,
    SCENARIO_STEP_PCT,

    LOW_STOCK_DAYS,
    TARGET_STOCK_DAYS,
    HIGH_STOCK_DAYS,
    CLEARANCE_STOCK_DAYS,

    OLD_STOCK_DAYS,
    VERY_OLD_STOCK_DAYS,

    MIN_MARGIN_PCT,
)


def number(
    value,
    default=0.0,
):
    try:
        if (
            value is None
            or pd.isna(value)
        ):
            return default

        return float(
            value
        )

    except (
        TypeError,
        ValueError,
    ):
        return default


def pct_change(
    current,
    previous,
):
    current = number(
        current
    )

    previous = number(
        previous
    )

    if previous == 0:
        return None

    return (
        current
        / previous
        - 1.0
    ) * 100.0


# ============================================================
# МЕТРИКИ ПЕРИОДА
# ============================================================

def period_metrics(
    frame: pd.DataFrame,
    report_date,
    days: int,
) -> dict:

    start = (
        report_date
        - timedelta(
            days=days - 1
        )
    )

    if frame.empty:
        work = frame

    else:
        dates = pd.to_datetime(
            frame[
                "date_from"
            ],
            errors="coerce",
        ).dt.date

        work = frame[
            dates.between(
                start,
                report_date,
            )
        ].copy()

    fields = (
        "sales_qty",
        "returns_qty",
        "net_qty",

        "seller_sales_amount",
        "wb_sales_amount",

        "amount",
        "amount_vatless",

        "cogs_man",
        "net_comission",
        "margin_man",
    )

    if work.empty:
        return {
            "days": days,

            **{
                field: 0.0
                for field in fields
            },

            "seller_price": 0.0,

            "buyer_price": 0.0,

            "wb_discount_pct": None,

            # Совместимость со старым названием:
            # отрицательное значение = покупатель платил дешевле нашей цены.
            "wb_price_delta_pct": None,

            "margin_pct": 0.0,

            "daily_sales_qty": 0.0,
        }

    sums = {}

    for field in fields:

        if field not in work.columns:
            sums[
                field
            ] = 0.0

            continue

        sums[
            field
        ] = number(
            pd.to_numeric(
                work[
                    field
                ],
                errors="coerce",
            )
            .fillna(0)
            .sum()
        )

    sales_qty = sums[
        "sales_qty"
    ]

    seller_price = (
        sums[
            "seller_sales_amount"
        ]
        / sales_qty
        if sales_qty > 0
        else 0.0
    )

    buyer_price = (
        sums[
            "wb_sales_amount"
        ]
        / sales_qty
        if sales_qty > 0
        else 0.0
    )

    wb_discount_pct = (
        (
            seller_price
            - buyer_price
        )
        / seller_price
        * 100.0
        if (
            seller_price > 0
            and buyer_price > 0
        )
        else None
    )

    # Старое техническое представление сохраняем для совместимости:
    # если WB продал покупателю дешевле нашей цены, здесь будет минус.
    wb_price_delta_pct = (
        -wb_discount_pct
        if wb_discount_pct is not None
        else None
    )

    margin_pct = (
        sums[
            "margin_man"
        ]
        / sums[
            "amount_vatless"
        ]
        * 100.0

        if sums[
            "amount_vatless"
        ]

        else 0.0
    )

    return {
        "days": days,

        **sums,

        "seller_price": (
            seller_price
        ),

        "buyer_price": (
            buyer_price
        ),

        "wb_discount_pct": (
            wb_discount_pct
        ),

        "wb_price_delta_pct": (
            wb_price_delta_pct
        ),

        "margin_pct": (
            margin_pct
        ),

        "daily_sales_qty": (
            sales_qty
            / max(
                days,
                1,
            )
        ),
    }
    
    

def latest_sale_metrics(
    frame: pd.DataFrame,
) -> dict | None:
    """
    Последняя фактическая продажа товара.
    Используется как текущая ценовая точка.
    """

    if frame is None or frame.empty:
        return None

    work = frame.copy()

    work["date_from"] = pd.to_datetime(
        work["date_from"],
        errors="coerce",
    )

    work["sales_qty"] = pd.to_numeric(
        work["sales_qty"],
        errors="coerce",
    ).fillna(0)

    work = work[
        work["sales_qty"] > 0
    ].copy()

    if work.empty:
        return None

    work = work.sort_values(
        "date_from"
    )

    row = work.iloc[-1]

    return {
        "date_from": row.get(
            "date_from"
        ),
        "seller_price": number(
            row.get(
                "seller_price"
            )
        ),
        "buyer_price": number(
            row.get(
                "buyer_price"
            )
        ),
    }


# ============================================================
# ЭЛАСТИЧНОСТЬ
# ============================================================

def estimate_elasticity(
    frame: pd.DataFrame,
) -> dict:
    """
    ln(Q) = a + b * ln(P)

    P = фактическая цена WB покупателю.
    Q = количество положительных продаж.

    Это наблюдаемая статистическая связь,
    а не причинный эффект.
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

    work[
        "sales_qty"
    ] = pd.to_numeric(
        work[
            "sales_qty"
        ],
        errors="coerce",
    )

    work[
        "buyer_price"
    ] = pd.to_numeric(
        work[
            "buyer_price"
        ],
        errors="coerce",
    )

    work = work[
        (
            work[
                "sales_qty"
            ]
            >= 1
        )
        &
        (
            work[
                "buyer_price"
            ]
            > 0
        )
    ][
        [
            "date_from",
            "sales_qty",
            "buyer_price",
        ]
    ].dropna()

    if (
        len(work)
        < MIN_ELASTICITY_DAYS
    ):
        return {
            "elasticity": None,
            "r2": None,
            "observations": len(work),
            "price_cv_pct": 0.0,
            "confidence": "Мало наблюдений",
        }

    price_mean = float(
        work[
            "buyer_price"
        ].mean()
    )

    price_std = float(
        work[
            "buyer_price"
        ].std()
    )

    price_cv_pct = (
        price_std
        / price_mean
        * 100.0

        if price_mean
        else 0.0
    )

    if (
        price_cv_pct
        < MIN_PRICE_CV_PCT
    ):
        return {
            "elasticity": None,
            "r2": None,
            "observations": len(work),
            "price_cv_pct": price_cv_pct,
            "confidence": (
                "Цена почти не менялась"
            ),
        }

    # --------------------------------------------------------
    # убираем крайние выбросы
    # --------------------------------------------------------

    p_low = work[
        "buyer_price"
    ].quantile(
        0.025
    )

    p_high = work[
        "buyer_price"
    ].quantile(
        0.975
    )

    q_low = work[
        "sales_qty"
    ].quantile(
        0.025
    )

    q_high = work[
        "sales_qty"
    ].quantile(
        0.975
    )

    work = work[
        work[
            "buyer_price"
        ].between(
            p_low,
            p_high,
        )
        &
        work[
            "sales_qty"
        ].between(
            q_low,
            q_high,
        )
    ].copy()

    if len(work) < 10:
        return {
            "elasticity": None,
            "r2": None,
            "observations": len(work),
            "price_cv_pct": price_cv_pct,
            "confidence": "Мало наблюдений",
        }

    x = np.log(
        work[
            "buyer_price"
        ]
        .astype(float)
        .values
    )

    y = np.log(
        work[
            "sales_qty"
        ]
        .astype(float)
        .values
    )

    if (
        len(
            np.unique(x)
        )
        < 3
        or
        len(
            np.unique(y)
        )
        < 3
    ):
        return {
            "elasticity": None,
            "r2": None,
            "observations": len(work),
            "price_cv_pct": price_cv_pct,
            "confidence": (
                "Недостаточно вариации"
            ),
        }

    slope, intercept = (
        np.polyfit(
            x,
            y,
            1,
        )
    )

    predicted = (
        intercept
        + slope * x
    )

    ss_res = float(
        np.sum(
            (
                y
                - predicted
            )
            ** 2
        )
    )

    ss_tot = float(
        np.sum(
            (
                y
                - y.mean()
            )
            ** 2
        )
    )

    r2 = (
        1.0
        - ss_res
        / ss_tot

        if ss_tot
        else 0.0
    )

    elasticity = float(
        max(
            -4.0,
            min(
                4.0,
                slope,
            ),
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
        "elasticity": (
            elasticity
        ),

        "r2": r2,

        "observations": (
            len(work)
        ),

        "price_cv_pct": (
            price_cv_pct
        ),

        "confidence": (
            confidence
        ),
    }


# ============================================================
# СЦЕНАРИИ ЦЕН
# ============================================================

def build_scenarios(
    current: dict,
    elasticity_info: dict,
    stock_total: float,
) -> list[dict]:

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

    elasticity = (
        elasticity_info.get(
            "elasticity"
        )
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

    change_pct = (
        SCENARIO_MIN_PCT
    )

    while (
        change_pct
        <= SCENARIO_MAX_PCT
        + 0.0001
    ):

        price_factor = (
            1.0
            + change_pct
            / 100.0
        )

        projected_seller_price = (
            base_seller_price
            * price_factor
        )

        projected_buyer_price = (
            projected_seller_price
            * wb_factor
        )

        # ----------------------------------------------------
        # ПРОГНОЗ ОБЪЁМА
        # ----------------------------------------------------

        if (
            elasticity is not None
            and base_buyer_price > 0
        ):

            buyer_factor = (
                projected_buyer_price
                / base_buyer_price
            )

            try:
                qty_factor = (
                    buyer_factor
                    ** float(
                        elasticity
                    )
                )

            except Exception:
                qty_factor = 1.0

            qty_factor = max(
                0.25,
                min(
                    2.5,
                    qty_factor,
                ),
            )

        else:
            qty_factor = 1.0

        # ----------------------------------------------------
        # ПРОГНОЗ ОБЪЁМА НОРМАЛИЗУЕМ НА 30 ДНЕЙ
        #
        # scenario_base может быть 7-дневным или 30-дневным,
        # поэтому сначала считаем продажи в день, а затем
        # приводим прогноз к единому горизонту 30 дней.
        # ----------------------------------------------------

        current_days = max(
            number(
                current.get(
                    "days"
                ),
                30,
            ),
            1,
        )

        base_daily_qty = (
            base_qty
            / current_days
        )

        projected_daily_qty = (
            base_daily_qty
            * qty_factor
        )

        projected_qty = (
            projected_daily_qty
            * 30.0
        )

        # ----------------------------------------------------
        # ВЫРУЧКА ЗА 30 ДНЕЙ
        # ----------------------------------------------------

        projected_revenue_net = (
            projected_qty
            * revenue_net_per_unit
            * price_factor
        )

        # ----------------------------------------------------
        # COGS
        # ----------------------------------------------------

        projected_cogs = (
            projected_qty
            * cogs_per_unit
        )

        # ----------------------------------------------------
        # КОМИССИЯ
        # ----------------------------------------------------

        projected_commission = (
            projected_revenue_net
            * commission_rate
        )

        # ----------------------------------------------------
        # МАРЖА
        # ----------------------------------------------------

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

        # projected_daily_qty уже рассчитан выше
        # из актуальной скорости продаж.

        # ====================================================
        # ЗАПАС В ДНЯХ
        #
        # ВАЖНО:
        # здесь именно TOTAL STOCK:
        #
        # WB
        # + FBS
        # + к клиенту
        # + от клиента
        # ====================================================

        projected_stock_days = (
            stock_total
            / projected_daily_qty

            if projected_daily_qty > 0

            else None
        )

        scenarios.append(
            {
                "price_change_pct": (
                    round(
                        change_pct,
                        2,
                    )
                ),

                "seller_price": (
                    projected_seller_price
                ),

                "buyer_price": (
                    projected_buyer_price
                ),

                "projected_qty": (
                    projected_qty
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


# ============================================================
# ВЫБОР СЦЕНАРИЯ
# ============================================================

def choose_recommendation(
    scenarios,
    elasticity_info,
    days_of_stock,
    stock_age_days,
):

    if not scenarios:
        return None

    safe = [
        row
        for row in scenarios
        if row.get(
            "is_margin_safe"
        )
    ]

    pool = (
        safe
        or scenarios
    )

    confidence = (
        elasticity_info.get(
            "confidence"
        )
    )

    reliable = (
        confidence
        in (
            "Высокая",
            "Средняя",
        )
    )

    # --------------------------------------------------------
    # Если эластичность ненадёжна,
    # используем давление остатка
    # --------------------------------------------------------

    if not reliable:

        if (
            days_of_stock is not None
            and days_of_stock
            >= CLEARANCE_STOCK_DAYS
        ):
            target = -10.0

        elif (
            days_of_stock is not None
            and days_of_stock
            >= HIGH_STOCK_DAYS
        ):
            target = -5.0

        elif (
            days_of_stock is not None
            and days_of_stock
            <= LOW_STOCK_DAYS
        ):
            target = 5.0

        else:
            target = 0.0

        return min(
            pool,
            key=lambda row: abs(
                number(
                    row.get(
                        "price_change_pct"
                    )
                )
                - target
            ),
        )

    # --------------------------------------------------------
    # Максимальная модельная маржа
    # --------------------------------------------------------

    max_margin = max(
        pool,
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

    # сохраняем 98% максимальной маржи
    candidates = [
        row
        for row in pool
        if (
            number(
                row.get(
                    "projected_margin"
                )
            )
            >= max_margin_value
            * 0.98
        )
    ]

    if not candidates:
        candidates = [
            max_margin
        ]

    stock_pressure = (
        days_of_stock is None

        or (
            days_of_stock
            >= HIGH_STOCK_DAYS
        )

        or (
            stock_age_days is not None
            and stock_age_days
            >= OLD_STOCK_DAYS
        )
    )

    # Если запаса много —
    # среди почти максимальной маржи
    # выбираем больший объём.

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


# ============================================================
# СТАТУС
# ============================================================

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

    if (
        confidence
        not in (
            "Высокая",
            "Средняя",
        )
        and abs(
            change_pct
        )
        >= 2.5
    ):
        return "TEST"

    if change_pct <= -2.5:
        return "REDUCE"

    if change_pct >= 2.5:
        return "RAISE"

    return "HOLD"


# ============================================================
# ОБЪЯСНЕНИЕ
# ============================================================

def build_reason(
    *,
    m7,
    m30,
    elasticity_info,
    days_of_stock,
    stock_age_days,
    recommended_change_pct,
):

    parts = []

    if days_of_stock is None:

        parts.append(
            (
                "нет устойчивой скорости продаж "
                "для расчёта запаса"
            )
        )

    else:

        parts.append(
            (
                f"общий запас примерно "
                f"{days_of_stock:.0f} дн."
            )
        )

    if stock_age_days is not None:

        parts.append(
            (
                f"возраст товара "
                f"{stock_age_days:.0f} дн."
            )
        )

    speed_change = pct_change(
        m7.get(
            "daily_sales_qty"
        ),
        m30.get(
            "daily_sales_qty"
        ),
    )

    if speed_change is not None:

        if speed_change <= -20:

            parts.append(
                (
                    f"скорость 7д ниже 30д "
                    f"на {abs(speed_change):.0f}%"
                )
            )

        elif speed_change >= 20:

            parts.append(
                (
                    f"скорость 7д выше 30д "
                    f"на {speed_change:.0f}%"
                )
            )

    elasticity = (
        elasticity_info.get(
            "elasticity"
        )
    )

    if elasticity is not None:

        parts.append(
            (
                f"эластичность "
                f"{elasticity:.2f}, "
                f"R² "
                f"{number(elasticity_info.get('r2')):.2f}"
            )
        )

    else:

        parts.append(
            (
                "эластичность ненадёжна: "
                f"{elasticity_info.get('confidence')}"
            )
        )

    parts.append(
        (
            "рекомендуемое изменение цены "
            f"{recommended_change_pct:+.1f}%"
        )
    )

    return (
        "; ".join(
            parts
        )
        + "."
    )


# ============================================================
# ОСНОВНОЙ АНАЛИЗ
# ============================================================

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

            "recommendations": (
                pd.DataFrame()
            ),

            "portfolio": (
                pd.DataFrame()
            ),

            "scenarios": (
                pd.DataFrame()
            ),

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

    # ========================================================
    # ПО КАЖДОМУ NM ID
    # ========================================================

    for _, product in (
        products.iterrows()
    ):

        nm_id = product[
            "nm_id"
        ]

        history = (
            daily[
                daily[
                    "nm_id"
                ]
                == nm_id
            ].copy()

            if not daily.empty

            else pd.DataFrame()
        )

        # ----------------------------------------------------
        # 7 / 30 / 90
        # ----------------------------------------------------

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
        
        
        latest_sale = (
            latest_sale_metrics(
                history
            )
        )

        daily_qty_7 = number(
            m7.get(
                "daily_sales_qty"
            )
        )

        daily_qty_30 = number(
            m30.get(
                "daily_sales_qty"
            )
        )

        current_daily_qty = (
            daily_qty_7
            if daily_qty_7 > 0
            else daily_qty_30
        )

        elasticity_info = (
            estimate_elasticity(
                history
            )
        )

        # ====================================================
        # ОСТАТКИ
        # ====================================================

        wb_stock = number(
            product.get(
                "wb_stock"
            )
        )

        fbs_stock = number(
            product.get(
                "fbs_stock"
            )
        )

        in_way_to_client = number(
            product.get(
                "in_way_to_client"
            )
        )

        in_way_from_client = number(
            product.get(
                "in_way_from_client"
            )
        )

        in_transit = number(
            product.get(
                "in_transit"
            )
        )

        physical_stock = number(
            product.get(
                "physical_stock"
            )
        )

        # ====================================================
        # ВАЖНО
        #
        # ВСЯ МОДЕЛЬ РАБОТАЕТ ОТ TOTAL STOCK
        #
        # WB
        # + FBS
        # + к клиенту
        # + от клиента
        # ====================================================

        total_stock = number(
            product.get(
                "total_stock"
            )
        )

        days_of_stock = (
            total_stock
            / current_daily_qty

            if current_daily_qty > 0

            else None
        )

        # ----------------------------------------------------
        # ВОЗРАСТ
        # ----------------------------------------------------

        raw_income = (
            product.get(
                "last_income_date"
            )
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

        # ====================================================
        # СЦЕНАРИИ
        # ====================================================

        # Для текущей скорости берём последние 7 дней.
        # Если за 7 дней продаж не было — используем 30 дней.
        scenario_base = (
            m7.copy()
            if number(
                m7.get(
                    "sales_qty"
                )
            ) > 0
            else m30.copy()
        )

        # Базовую цену для следующего решения берём
        # из последней фактической продажи, а не из средней за период.
        if latest_sale:
            latest_seller_price = number(
                latest_sale.get(
                    "seller_price"
                )
            )

            latest_buyer_price = number(
                latest_sale.get(
                    "buyer_price"
                )
            )

            if latest_seller_price > 0:
                scenario_base[
                    "seller_price"
                ] = latest_seller_price

            if latest_buyer_price > 0:
                scenario_base[
                    "buyer_price"
                ] = latest_buyer_price

        scenarios = (
            build_scenarios(
                current=scenario_base,

                elasticity_info=(
                    elasticity_info
                ),

                stock_total=(
                    total_stock
                ),
            )
        )

        recommended = (
            choose_recommendation(
                scenarios=scenarios,

                elasticity_info=(
                    elasticity_info
                ),

                days_of_stock=(
                    days_of_stock
                ),

                stock_age_days=(
                    stock_age_days
                ),
            )
        )

        if recommended:

            recommended_change_pct = (
                number(
                    recommended.get(
                        "price_change_pct"
                    )
                )
            )

            recommended_seller_price = (
                number(
                    recommended.get(
                        "seller_price"
                    )
                )
            )

            recommended_buyer_price = (
                number(
                    recommended.get(
                        "buyer_price"
                    )
                )
            )

            recommended_margin = (
                number(
                    recommended.get(
                        "projected_margin"
                    )
                )
            )

            recommended_margin_pct = (
                number(
                    recommended.get(
                        "projected_margin_pct"
                    )
                )
            )

            recommended_sales_qty_30d = (
                number(
                    recommended.get(
                        "projected_qty"
                    )
                )
            )

            recommended_daily_sales_qty = (
                number(
                    recommended.get(
                        "projected_daily_qty"
                    )
                )
            )

            recommended_stock_days = (
                recommended.get(
                    "projected_stock_days"
                )
            )

        else:

            recommended_change_pct = (
                0.0
            )

            recommended_seller_price = (
                number(
                    product.get(
                        "current_seller_list_price"
                    )
                )
                or
                number(
                    m30.get(
                        "seller_price"
                    )
                )
            )

            recommended_buyer_price = (
                number(
                    m30.get(
                        "buyer_price"
                    )
                )
            )

            recommended_margin = (
                number(
                    m30.get(
                        "margin_man"
                    )
                )
            )

            recommended_margin_pct = (
                number(
                    m30.get(
                        "margin_pct"
                    )
                )
            )

            recommended_daily_sales_qty = (
                current_daily_qty
            )

            recommended_sales_qty_30d = (
                current_daily_qty
                * 30.0
            )

            recommended_stock_days = (
                days_of_stock
            )

        # ----------------------------------------------------
        # STATUS
        # ----------------------------------------------------

        status = (
            recommendation_status(
                change_pct=(
                    recommended_change_pct
                ),

                days_of_stock=(
                    days_of_stock
                ),

                stock_age_days=(
                    stock_age_days
                ),

                confidence=(
                    elasticity_info.get(
                        "confidence"
                    )
                ),
            )
        )

        # ----------------------------------------------------
        # ПОТЕНЦИАЛ МАРЖИ
        # ----------------------------------------------------

        margin_upside_30 = (
            recommended_margin
            - number(
                m30.get(
                    "margin_man"
                )
            )
        )

        margin_upside_day = (
            margin_upside_30
            / 30.0
        )

        speed_trend = (
            pct_change(
                m7.get(
                    "daily_sales_qty"
                ),
                m30.get(
                    "daily_sales_qty"
                ),
            )
        )

        # ----------------------------------------------------
        # PRIORITY
        # ----------------------------------------------------

        priority = {
            "CLEARANCE": 100,
            "REDUCE": 80,
            "RAISE": 70,
            "TEST": 50,
            "HOLD": 10,
        }.get(
            status,
            0,
        )

        if (
            days_of_stock
            is not None
        ):

            priority += min(
                max(
                    days_of_stock
                    - TARGET_STOCK_DAYS,
                    0,
                )
                / 10.0,
                40,
            )

        priority += min(
            max(
                margin_upside_day,
                0,
            )
            / 100.0,
            30,
        )

        reason = build_reason(
            m7=m7,

            m30=m30,

            elasticity_info=(
                elasticity_info
            ),

            days_of_stock=(
                days_of_stock
            ),

            stock_age_days=(
                stock_age_days
            ),

            recommended_change_pct=(
                recommended_change_pct
            ),
        )

        # ====================================================
        # RESULT NM ID
        # ====================================================

        recommendations.append(
            {
                "priority": round(
                    priority,
                    1,
                ),

                "status": status,

                "nm_id": nm_id,

                "sa_name": product.get(
                    "sa_name"
                ),

                "brand": product.get(
                    "brand"
                ),

                "category": product.get(
                    "category"
                ),

                "gender": product.get(
                    "gender"
                ),

                "title": product.get(
                    "title"
                ),

                # --------------------------------------------
                # PRICE
                # --------------------------------------------

                "current_seller_list_price": (
                    number(
                        product.get(
                            "current_seller_list_price"
                        )
                    )
                ),

                "last_man_cost": (
                    number(
                        product.get(
                            "last_man_cost"
                        )
                    )
                ),

                "seller_price_30d": (
                    number(
                        m30.get(
                            "seller_price"
                        )
                    )
                ),

                "buyer_price_30d": (
                    number(
                        m30.get(
                            "buyer_price"
                        )
                    )
                ),

                "wb_discount_pct_30d": (
                    number(
                        m30.get(
                            "wb_discount_pct"
                        ),
                        None,
                    )
                    if m30.get(
                        "wb_discount_pct"
                    ) is not None
                    else None
                ),

                # старое поле оставляем, чтобы не сломать Excel/старые места
                "wb_price_delta_pct_30d": (
                    number(
                        m30.get(
                            "wb_price_delta_pct"
                        ),
                        None,
                    )
                    if m30.get(
                        "wb_price_delta_pct"
                    ) is not None
                    else None
                ),

                # --------------------------------------------
                # MARGIN
                # --------------------------------------------

                "margin_man_30d": (
                    number(
                        m30.get(
                            "margin_man"
                        )
                    )
                ),

                "margin_pct_30d": (
                    number(
                        m30.get(
                            "margin_pct"
                        )
                    )
                ),

                # --------------------------------------------
                # RECOMMENDATION
                # --------------------------------------------

                "recommended_seller_price": (
                    recommended_seller_price
                ),

                "recommended_buyer_price": (
                    recommended_buyer_price
                ),

                "recommended_change_pct": (
                    recommended_change_pct
                ),

                "recommended_sales_qty_30d": (
                    recommended_sales_qty_30d
                ),

                "recommended_daily_sales_qty": (
                    recommended_daily_sales_qty
                ),

                "recommended_margin_30d": (
                    recommended_margin
                ),

                "recommended_margin_pct": (
                    recommended_margin_pct
                ),

                "margin_upside_day": (
                    margin_upside_day
                ),

                # --------------------------------------------
                # STOCKS
                # --------------------------------------------

                "wb_stock": wb_stock,

                "fbs_stock": fbs_stock,

                "in_way_to_client": (
                    in_way_to_client
                ),

                "in_way_from_client": (
                    in_way_from_client
                ),

                "in_transit": (
                    in_transit
                ),

                "physical_stock": (
                    physical_stock
                ),

                "total_stock": (
                    total_stock
                ),

                "days_of_stock": (
                    days_of_stock
                ),

                "recommended_stock_days": (
                    recommended_stock_days
                ),

                "stock_age_days": (
                    stock_age_days
                ),

                # --------------------------------------------
                # SALES
                # --------------------------------------------

                "sales_qty_7d": (
                    number(
                        m7.get(
                            "sales_qty"
                        )
                    )
                ),

                "sales_qty_30d": (
                    number(
                        m30.get(
                            "sales_qty"
                        )
                    )
                ),

                "sales_qty_90d": (
                    number(
                        m90.get(
                            "sales_qty"
                        )
                    )
                ),

                "sales_speed_trend_pct": (
                    speed_trend
                ),

                # --------------------------------------------
                # ELASTICITY
                # --------------------------------------------

                "elasticity": (
                    elasticity_info.get(
                        "elasticity"
                    )
                ),

                "elasticity_r2": (
                    elasticity_info.get(
                        "r2"
                    )
                ),

                "elasticity_confidence": (
                    elasticity_info.get(
                        "confidence"
                    )
                ),

                "reason": reason,
            }
        )

        # ====================================================
        # SCENARIO ROWS
        # ====================================================

        for scenario in scenarios:

            scenario_rows.append(
                {
                    "nm_id": nm_id,

                    "brand": product.get(
                        "brand"
                    ),

                    "category": product.get(
                        "category"
                    ),

                    **scenario,
                }
            )

    # ========================================================
    # DATAFRAMES
    # ========================================================

    rec = pd.DataFrame(
        recommendations
    )

    scenarios_df = pd.DataFrame(
        scenario_rows
    )

    # ========================================================
    # БРЕНД + КАТЕГОРИЯ
    # ========================================================

    if not rec.empty:

        rec = (
            rec
            .sort_values(
                [
                    "priority",
                    "total_stock",
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

        portfolio = (
            rec
            .groupby(
                [
                    "brand",
                    "category",
                ],
                dropna=False,
            )
            .agg(
                products=(
                    "nm_id",
                    "nunique",
                ),

                action_products=(
                    "status",
                    lambda s: (
                        s != "HOLD"
                    ).sum(),
                ),

                # ============================================
                # ВАЖНО:
                # portfolio использует TOTAL STOCK
                # ============================================

                stock_units=(
                    "total_stock",
                    "sum",
                ),

                wb_stock=(
                    "wb_stock",
                    "sum",
                ),

                fbs_stock=(
                    "fbs_stock",
                    "sum",
                ),

                in_transit=(
                    "in_transit",
                    "sum",
                ),

                sales_30d=(
                    "sales_qty_30d",
                    "sum",
                ),

                current_margin_30d=(
                    "margin_man_30d",
                    "sum",
                ),

                margin_upside_day=(
                    "margin_upside_day",
                    "sum",
                ),
            )
            .reset_index()
        )

        portfolio[
            "stock_days"
        ] = (
            portfolio[
                "stock_units"
            ]
            /
            (
                portfolio[
                    "sales_30d"
                ]
                / 30.0
            )
            .replace(
                0,
                np.nan,
            )
        )

        portfolio = (
            portfolio
            .sort_values(
                [
                    "margin_upside_day",
                    "stock_units",
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

    else:

        portfolio = (
            pd.DataFrame()
        )

    # ========================================================
    # SUMMARY
    # ========================================================

    summary = {
        "products": (
            int(
                rec[
                    "nm_id"
                ].nunique()
            )
            if not rec.empty
            else 0
        ),

        "action_products": (
            int(
                (
                    rec[
                        "status"
                    ]
                    != "HOLD"
                ).sum()
            )
            if not rec.empty
            else 0
        ),

        "clearance_products": (
            int(
                (
                    rec[
                        "status"
                    ]
                    == "CLEARANCE"
                ).sum()
            )
            if not rec.empty
            else 0
        ),

        "raise_products": (
            int(
                (
                    rec[
                        "status"
                    ]
                    == "RAISE"
                ).sum()
            )
            if not rec.empty
            else 0
        ),

        # ====================================================
        # ВАЖНО:
        # общий остаток тоже TOTAL STOCK
        # ====================================================

        "stock_units": (
            float(
                rec[
                    "total_stock"
                ].sum()
            )
            if not rec.empty
            else 0.0
        ),

        "wb_stock_units": (
            float(
                rec[
                    "wb_stock"
                ].sum()
            )
            if not rec.empty
            else 0.0
        ),

        "fbs_stock_units": (
            float(
                rec[
                    "fbs_stock"
                ].sum()
            )
            if not rec.empty
            else 0.0
        ),

        "in_transit_units": (
            float(
                rec[
                    "in_transit"
                ].sum()
            )
            if not rec.empty
            else 0.0
        ),

        "margin_upside_day": (
            float(
                rec[
                    "margin_upside_day"
                ]
                .clip(
                    lower=0
                )
                .sum()
            )
            if not rec.empty
            else 0.0
        ),
    }

    return {
        **source,

        "recommendations": (
            rec
        ),

        "portfolio": (
            portfolio
        ),

        "scenarios": (
            scenarios_df
        ),

        "history": (
            daily
        ),

        "summary": (
            summary
        ),
    }