# gear/app/daily_sales/pricing_strategy/analytics.py

from __future__ import annotations

from datetime import timedelta

import numpy as np
import pandas as pd

from .economics import (
    breakeven_price,
    margin_at_price,
    price_headroom_pct,
    target_margin_price,
    unit_cost,
    unit_ratios,
)

from .config import (
    LOW_HEADROOM_PCT,
    TARGET_MARGIN_PCT,

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
# УДЕЛЬНАЯ ЭКОНОМИКА ПО ВСЕЙ ВЫБОРКЕ
#
# Здесь закрывается главная дыра прежней версии: товары,
# которые ни разу не продавались, не имеют собственных
# коэффициентов НДС, комиссии и логистики. Раньше это
# означало пустую экономику, теперь — оценку по медиане
# категории с честной пометкой источника.
# ============================================================

RATIO_BOUNDS = (
    ("vat_ratio", 0.5, 1.0),
    ("commission_ratio", -0.9, 0.0),
)


def _fill_ratio(
    rec: pd.DataFrame,
    column: str,
):
    """
    Заполняет пропуски: медиана категории, затем медиана
    по всей выборке. Возвращает (значения, источник).
    """

    values = pd.to_numeric(
        rec[column],
        errors="coerce",
    )

    own = values.notna()

    by_category = (
        values
        .groupby(
            rec["category"]
        )
        .transform(
            "median"
        )
    )

    overall = values.median()

    filled = (
        values
        .fillna(by_category)
        .fillna(overall)
    )

    source = pd.Series(
        "Нет данных",
        index=rec.index,
        dtype=object,
    )

    source[filled.notna()] = "Медиана по выборке"

    source[by_category.notna()] = "Медиана категории"

    source[own] = "Свои продажи"

    return filled, source


def attach_unit_economics(
    rec: pd.DataFrame,
) -> pd.DataFrame:

    if rec is None or rec.empty:
        return rec

    rec = rec.copy()

    if "category" not in rec.columns:
        rec["category"] = "Категория не указана"

    sources = {}

    for column, low, high in RATIO_BOUNDS:

        if column not in rec.columns:
            rec[column] = None

        filled, source = _fill_ratio(
            rec,
            column,
        )

        if low is not None:
            filled = filled.clip(lower=low)

        if high is not None:
            filled = filled.clip(upper=high)

        rec[column] = filled

        sources[column] = source

    # источник считаем по самому слабому звену:
    # если хоть один коэффициент оценочный — вся строка оценочная
    priority = {
        "Свои продажи": 0,
        "Медиана категории": 1,
        "Медиана по выборке": 2,
        "Нет данных": 3,
    }

    weakest = None

    for column in (
        "vat_ratio",
        "commission_ratio",
    ):
        current = sources[column].map(
            priority
        )

        weakest = (
            current
            if weakest is None
            else weakest.combine(
                current,
                max,
            )
        )

    inverse = {
        value: key
        for key, value in priority.items()
    }

    rec["ratios_source"] = weakest.map(
        inverse
    )

    # --------------------------------------------------------
    # ПОСТРОЧНЫЙ РАСЧЁТ
    # --------------------------------------------------------

    def _row_economics(row):

        cost = number(
            row.get("unit_cogs")
        )

        vat_ratio = row.get("vat_ratio")

        commission_ratio = row.get(
            "commission_ratio"
        )

        floor_price = breakeven_price(
            cost_per_unit=cost,
            vat_ratio=vat_ratio,
            commission_ratio=commission_ratio,
        )

        target_price = target_margin_price(
            cost_per_unit=cost,
            vat_ratio=vat_ratio,
            commission_ratio=commission_ratio,
            target_margin_pct=TARGET_MARGIN_PCT,
        )

        # ТЕКУЩАЯ ЦЕНА — ОДНА НА ВЕСЬ ОТЧЁТ.
        #
        # Порядок: цена, от которой модель считала сценарии
        # (последняя фактическая продажа), затем средняя за
        # 30 дней, затем цена в карточке. Проценты изменения
        # и запас по скидке считаются от неё же, иначе
        # колонки не сходятся между собой.
        current_price = number(
            row.get("base_price_for_change")
        )

        if current_price <= 0:
            current_price = number(
                row.get("seller_price_30d")
            )

        if current_price <= 0:
            current_price = number(
                row.get(
                    "current_seller_list_price"
                )
            )

        margin_unit, margin_unit_pct = (
            margin_at_price(
                current_price,
                cost_per_unit=cost,
                vat_ratio=vat_ratio,
                commission_ratio=commission_ratio,
            )
        )

        headroom = price_headroom_pct(
            current_price,
            floor_price,
        )

        below = bool(
            floor_price
            and current_price > 0
            and current_price < floor_price
        )

        loss_per_unit = (
            floor_price - current_price
            if below
            else 0.0
        )

        total_stock = number(
            row.get("total_stock")
        )

        gap_to_target = None

        if (
            target_price
            and current_price > 0
        ):
            gap_to_target = (
                (
                    target_price
                    - current_price
                )
                / current_price
                * 100.0
            )

        return pd.Series(
            {
                "current_effective_price": (
                    current_price
                ),

                "breakeven_price": floor_price,

                "target_margin_price": (
                    target_price
                ),

                "unit_margin_now": margin_unit,

                "unit_margin_pct_now": (
                    margin_unit_pct
                ),

                "price_headroom_pct": headroom,

                "below_breakeven": below,

                "loss_per_unit": loss_per_unit,

                "stock_at_risk_value": (
                    loss_per_unit
                    * total_stock
                ),

                "gap_to_target_pct": (
                    gap_to_target
                ),

                "margin_at_risk": bool(
                    headroom is not None
                    and 0
                    <= headroom
                    < LOW_HEADROOM_PCT
                ),

                # Отдельно от точки безубыточности: цена
                # опустилась ниже самой себестоимости, ещё
                # до комиссии, НДС и логистики. Это крайний
                # случай, его видно сразу.
                "below_unit_cost": bool(
                    cost > 0
                    and current_price > 0
                    and current_price < cost
                ),
            }
        )

    economics = rec.apply(
        _row_economics,
        axis=1,
    )

    for column in economics.columns:
        rec[column] = economics[column]

    # --------------------------------------------------------
    # ЦЕНА К УСТАНОВКЕ
    #
    # Модель оптимизирует маржу, но результат нельзя ставить
    # на витрину, если он ниже точки безубыточности. Поэтому
    # рекомендацию модели оставляем как есть (её видно в
    # сценариях), а рядом даём цену, которую действительно
    # можно поставить.
    #
    # Для распродажи ограничение не применяется: там продажа
    # ниже себестоимости — осознанное решение.
    # --------------------------------------------------------

    recommended = pd.to_numeric(
        rec["recommended_seller_price"],
        errors="coerce",
    ).fillna(0.0)

    floor_price = pd.to_numeric(
        rec["breakeven_price"],
        errors="coerce",
    )

    is_clearance = (
        rec["status"] == "CLEARANCE"
    )

    action_price = recommended.where(
        is_clearance
        | floor_price.isna()
        | (recommended >= floor_price),
        floor_price,
    )

    rec["action_price"] = action_price

    current_price = pd.to_numeric(
        rec["current_effective_price"],
        errors="coerce",
    )

    rec["action_change_pct"] = (
        (
            action_price
            / current_price.replace(0, np.nan)
            - 1.0
        )
        * 100.0
    )

    rec["action_capped"] = (
        (~is_clearance)
        & floor_price.notna()
        & (recommended < floor_price)
    )

    # --------------------------------------------------------
    # СТАТУС «УБЫТОК»
    #
    # Продажа ниже точки безубыточности — это не «повысить
    # цену на 7%», это отдельная проблема, которую надо
    # увидеть первой.
    # --------------------------------------------------------

    loss_mask = (
        rec["below_breakeven"].fillna(False).astype(bool)
        & (~is_clearance)
    )

    rec.loc[loss_mask, "status"] = "LOSS"

    rec.loc[loss_mask, "priority"] = (
        pd.to_numeric(
            rec.loc[loss_mask, "priority"],
            errors="coerce",
        ).fillna(0.0)
        + 60.0
    )

    # --------------------------------------------------------
    # ДОПОЛНЯЕМ ОБЪЯСНЕНИЕ ТАМ, ГДЕ ЕГО НЕ БЫЛО
    #
    # У товаров без продаж минимальная цена появляется только
    # здесь, после расчёта по медианам. Значит и в объяснении
    # про неё надо сказать именно тут.
    # --------------------------------------------------------

    def _augment_reason(row):

        reason = str(
            row.get("reason") or ""
        )

        if "минимальная цена" in reason:
            return reason

        floor_value = row.get(
            "breakeven_price"
        )

        if not floor_value or floor_value != floor_value:
            return reason

        note = (
            "минимальная цена "
            f"{float(floor_value):,.0f} ₽"
        ).replace(",", " ")

        if row.get("ratios_source") != "Свои продажи":
            note += (
                " (оценка по медиане категории: "
                "своих продаж у товара нет)"
            )

        if row.get("below_breakeven"):
            note += (
                "; текущая цена ниже минимальной — "
                "каждая проданная единица приносит убыток"
            )

        return (
            reason.rstrip(".")
            + "; "
            + note
            + "."
        )

    rec["reason"] = rec.apply(
        _augment_reason,
        axis=1,
    )

    return rec


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
        # УДЕЛЬНАЯ ЭКОНОМИКА
        #
        # Коэффициенты (доля без НДС, доля комиссии, логистика
        # на единицу) берём по самому широкому окну, где были
        # продажи: чем больше наблюдений, тем устойчивее доли.
        #
        # Если продаж не было вовсе — оставляем пусто, ниже
        # такие товары получат медиану по категории.
        # ====================================================

        ratio_metrics = None

        for candidate in (m90, m30, m7):
            if number(
                candidate.get(
                    "sales_qty"
                )
            ) > 0:
                ratio_metrics = candidate
                break

        ratios = unit_ratios(
            ratio_metrics
            or {}
        )

        unit_cogs, unit_cogs_basis = (
            unit_cost(
                last_man_cost=product.get(
                    "last_man_cost"
                ),
                metrics=ratio_metrics or {},
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

        # ====================================================
        # РАСПРОДАЖА НЕ МОЖЕТ ОЗНАЧАТЬ ПОВЫШЕНИЕ ЦЕНЫ
        #
        # Модель максимизирует модельную маржу и на товаре
        # с надёжной эластичностью может предложить рост цены
        # даже там, где запаса на несколько лет. Для человека
        # это выглядит как противоречие: статус «Распродажа»,
        # а рядом «+20%».
        #
        # Поэтому для распродажи выбираем лучший сценарий
        # среди тех, где цена не растёт.
        # ====================================================

        if (
            status == "CLEARANCE"
            and scenarios
            and recommended_change_pct > 0
        ):

            down_scenarios = [
                row
                for row in scenarios
                if number(
                    row.get(
                        "price_change_pct"
                    )
                ) <= 0
            ]

            if down_scenarios:

                replacement = max(
                    down_scenarios,
                    key=lambda row: number(
                        row.get(
                            "projected_margin"
                        )
                    ),
                )

                recommended_change_pct = number(
                    replacement.get(
                        "price_change_pct"
                    )
                )

                recommended_seller_price = number(
                    replacement.get(
                        "seller_price"
                    )
                )

                recommended_buyer_price = number(
                    replacement.get(
                        "buyer_price"
                    )
                )

                recommended_margin = number(
                    replacement.get(
                        "projected_margin"
                    )
                )

                recommended_margin_pct = number(
                    replacement.get(
                        "projected_margin_pct"
                    )
                )

                recommended_sales_qty_30d = number(
                    replacement.get(
                        "projected_qty"
                    )
                )

                recommended_daily_sales_qty = number(
                    replacement.get(
                        "projected_daily_qty"
                    )
                )

                recommended_stock_days = (
                    replacement.get(
                        "projected_stock_days"
                    )
                )


        # ====================================================
        # ОГРАНИЧЕНИЕ СНИЗУ: НЕ РЕКОМЕНДУЕМ ЦЕНУ НИЖЕ
        # ТОЧКИ БЕЗУБЫТОЧНОСТИ
        #
        # Модель максимизирует модельную маржу и в принципе
        # может предложить цену, при которой единица продаётся
        # в минус. Для распродажи это может быть осознанным
        # решением, для всего остального — нет.
        #
        # Здесь используются СОБСТВЕННЫЕ коэффициенты товара.
        # У товаров без продаж сценариев нет вообще, поэтому
        # ограничивать нечего.
        # ====================================================

        own_breakeven = breakeven_price(
            cost_per_unit=unit_cogs,
            vat_ratio=ratios.get(
                "vat_ratio"
            ),
            commission_ratio=ratios.get(
                "commission_ratio"
            ),
        )

        capped_by_breakeven = False

        unreachable_breakeven = False

        if (
            own_breakeven
            and scenarios
            and status != "CLEARANCE"
            and recommended_seller_price > 0
            and recommended_seller_price < own_breakeven
        ):

            safe_scenarios = [
                row
                for row in scenarios
                if number(
                    row.get(
                        "seller_price"
                    )
                )
                >= own_breakeven
            ]

            if safe_scenarios:

                replacement = min(
                    safe_scenarios,
                    key=lambda row: number(
                        row.get(
                            "seller_price"
                        )
                    ),
                )

                capped_by_breakeven = True

            else:

                # даже максимальное повышение цены
                # не выводит товар в плюс
                replacement = max(
                    scenarios,
                    key=lambda row: number(
                        row.get(
                            "seller_price"
                        )
                    ),
                )

                unreachable_breakeven = True

            recommended_change_pct = number(
                replacement.get(
                    "price_change_pct"
                )
            )

            recommended_seller_price = number(
                replacement.get(
                    "seller_price"
                )
            )

            recommended_buyer_price = number(
                replacement.get(
                    "buyer_price"
                )
            )

            recommended_margin = number(
                replacement.get(
                    "projected_margin"
                )
            )

            recommended_margin_pct = number(
                replacement.get(
                    "projected_margin_pct"
                )
            )

            recommended_sales_qty_30d = number(
                replacement.get(
                    "projected_qty"
                )
            )

            recommended_daily_sales_qty = number(
                replacement.get(
                    "projected_daily_qty"
                )
            )

            recommended_stock_days = (
                replacement.get(
                    "projected_stock_days"
                )
            )

            # статус пересчитываем: изменение цены другое
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
            "LOSS": 120,
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

        # ----------------------------------------------------
        # ДОБАВЛЯЕМ В ОБЪЯСНЕНИЕ ФАКТЫ ПРО МИНИМАЛЬНУЮ ЦЕНУ.
        #
        # Коллеге важно видеть не только «снизить на 5%»,
        # но и «ниже 430 ₽ опускаться нельзя».
        # ----------------------------------------------------

        notes = []

        current_price_for_note = number(
            m30.get(
                "seller_price"
            )
        ) or number(
            product.get(
                "current_seller_list_price"
            )
        )

        if own_breakeven:

            notes.append(
                (
                    "минимальная цена "
                    f"{own_breakeven:,.0f} ₽"
                ).replace(",", " ")
            )

            if (
                current_price_for_note > 0
                and current_price_for_note
                < own_breakeven
            ):

                notes.append(
                    (
                        "текущая цена ниже минимальной на "
                        f"{(own_breakeven - current_price_for_note) / own_breakeven * 100:.0f}%"
                    )
                )

        if capped_by_breakeven:

            notes.append(
                (
                    "рекомендация поднята до минимальной цены: "
                    "более низкая цена уводит единицу в минус"
                )
            )

        if unreachable_breakeven:

            notes.append(
                (
                    "даже максимальное повышение цены в модели "
                    "не выводит товар в плюс — вопрос не в цене, "
                    "а в себестоимости или в комиссии"
                )
            )

        if notes:

            reason = (
                reason.rstrip(".")
                + "; "
                + "; ".join(notes)
                + "."
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

                # --------------------------------------------
                # УДЕЛЬНАЯ ЭКОНОМИКА
                #
                # Всё, из чего складывается минимальная цена.
                # Держим в строке целиком, чтобы любую цифру
                # можно было пересчитать руками.
                # --------------------------------------------

                "unit_cogs": unit_cogs,

                # Бухгалтерская цена последнего прихода —
                # чтобы было видно, где цена ушла ниже даже
                # учётной стоимости товара.
                "unit_acc_cost": (
                    number(
                        product.get(
                            "last_acc_cost"
                        )
                    )
                ),

                # База, от которой модель считала изменение
                # цены. Раньше проценты в таблице считались
                # от разных баз (последняя продажа против
                # средней за 30 дней) и не сходились между
                # собой — теперь база одна.
                "base_price_for_change": (
                    number(
                        scenario_base.get(
                            "seller_price"
                        )
                    )
                ),

                "unit_cogs_basis": (
                    unit_cogs_basis
                ),

                "cost_source": (
                    product.get(
                        "cost_source"
                    )
                    or "Нет данных"
                ),

                "vat_ratio": ratios.get(
                    "vat_ratio"
                ),

                "commission_ratio": (
                    ratios.get(
                        "commission_ratio"
                    )
                ),

                "capped_by_breakeven": (
                    capped_by_breakeven
                ),

                "unreachable_breakeven": (
                    unreachable_breakeven
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

    # Минимальная цена, цена под целевую маржу и запас
    # по скидке — считаются по всей выборке сразу, потому
    # что товарам без продаж нужны медианы соседей.
    rec = attach_unit_economics(
        rec
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

                below_breakeven=(
                    "below_breakeven",
                    "sum",
                ),

                stock_at_risk_value=(
                    "stock_at_risk_value",
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

        # ====================================================
        # ГЛАВНАЯ ЦИФРА ОТЧЁТА
        #
        # Сколько артикулов продаётся ниже точки
        # безубыточности и во сколько это обходится,
        # если распродать по текущей цене весь остаток.
        # ====================================================

        "below_breakeven_products": (
            int(
                rec[
                    "below_breakeven"
                ].sum()
            )
            if (
                not rec.empty
                and "below_breakeven" in rec.columns
            )
            else 0
        ),

        "margin_at_risk_products": (
            int(
                rec[
                    "margin_at_risk"
                ].sum()
            )
            if (
                not rec.empty
                and "margin_at_risk" in rec.columns
            )
            else 0
        ),

        "stock_at_risk_value": (
            float(
                rec[
                    "stock_at_risk_value"
                ].sum()
            )
            if (
                not rec.empty
                and "stock_at_risk_value" in rec.columns
            )
            else 0.0
        ),

        "no_cost_products": (
            int(
                (
                    pd.to_numeric(
                        rec["unit_cogs"],
                        errors="coerce",
                    )
                    .fillna(0)
                    <= 0
                ).sum()
            )
            if (
                not rec.empty
                and "unit_cogs" in rec.columns
            )
            else 0
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