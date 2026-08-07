# gear/app/daily_sales/daily_brief/data/sales.py

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import pandas as pd
import numpy as np

from gear.app.data.base import DashboardData
from gear.app.daily_sales.wb_plan_monitor.data import (
    get_daily_fact,
    get_fact_for_period,
)

from ..helpers import (
    change_pct,
    dataframe_records,
    number,
)
from .common import (
    date_range,
    find_daily_row,
    first_row,
    previous_month_same_day,
    previous_year_same_day,
)


def _daily_row(
    target: date,
    cache: dict[tuple[int, int], list[dict]],
) -> dict:
    """
    Возвращает показатели за конкретный день.

    Данные кэшируются по году и месяцу,
    чтобы повторно не запрашивать один и тот же месяц.
    """

    key = (
        target.year,
        target.month,
    )

    if key not in cache:
        cache[key] = get_daily_fact(
            year=target.year,
            month=target.month,
            up_to_day=None,
        )

    return find_daily_row(
        cache[key],
        target,
    )


def _comparison(
    label: str,
    current: float,
    previous: float,
    previous_label: str,
) -> dict:
    return {
        "label": label,
        "current": current,
        "previous": previous,
        "previous_label": previous_label,
        "change_pct": change_pct(
            current,
            previous,
        ),
        "delta": current - previous,
    }


def _corr(
    rows: list[dict],
    x_key: str,
    y_key: str,
) -> float | None:
    frame = pd.DataFrame(
        rows or []
    )

    if (
        frame.empty
        or x_key not in frame
        or y_key not in frame
    ):
        return None

    x = pd.to_numeric(
        frame[x_key],
        errors="coerce",
    )

    y = pd.to_numeric(
        frame[y_key],
        errors="coerce",
    )

    valid = (
        x.notna()
        & y.notna()
        & (x > 0)
        & (y > 0)
    )

    if (
        valid.sum() < 5
        or x[valid].nunique() < 2
        or y[valid].nunique() < 2
    ):
        return None

    return float(
        x[valid].corr(
            y[valid]
        )
    )


def _build_ytd_daily_rows(
    *,
    report_date: date,
    current_year_start: date,
    previous_year_start: date,
    previous_year_end: date,
    cache: dict[tuple[int, int], list[dict]],
) -> list[dict]:
    """
    Формирует дневные показатели для YTD-графика.

    Используется показатель fact из get_daily_fact(),
    поэтому итог графика соответствует карточке
    «С начала года».
    """

    rows: list[dict] = []

    # Текущий год
    for current_day in date_range(
        current_year_start,
        report_date,
    ):
        source = _daily_row(
            current_day,
            cache,
        )

        rows.append(
            {
                "date_from": current_day.isoformat(),
                "amount": number(
                    source.get("fact")
                ),
            }
        )

    # Сопоставимый период прошлого года
    for previous_day in date_range(
        previous_year_start,
        previous_year_end,
    ):
        source = _daily_row(
            previous_day,
            cache,
        )

        rows.append(
            {
                "date_from": previous_day.isoformat(),
                "amount": number(
                    source.get("fact")
                ),
            }
        )

    return rows



# =============================================================================
# ЦЕНОВАЯ ЧУВСТВИТЕЛЬНОСТЬ БРЕНДОВ
# =============================================================================


def _period_brand_metrics(
    frame: pd.DataFrame,
) -> dict:
    """
    Агрегирует бренд за период.

    sales_qty:
        только положительные продажи;

    amount_vatless:
        чистая выручка без НДС с учётом ретроспективных возвратов;

    margin_man:
        маржа после FIFO-себестоимости и комиссии WB,
        но ДО маркетинга, штрафов и прочих распределяемых расходов WB.
    """

    if frame.empty:
        return {
            "sales_qty": 0.0,
            "avg_price": 0.0,
            "amount_vatless": 0.0,
            "cogs_man": 0.0,
            "net_comission": 0.0,
            "margin_man": 0.0,
            "margin_pct": 0.0,
        }

    sales_qty = float(
        frame["sales_qty"]
        .fillna(0)
        .sum()
    )

    sales_amount = float(
        frame["sales_amount"]
        .fillna(0)
        .sum()
    )

    avg_price = (
        sales_amount
        / sales_qty
        if sales_qty
        else 0.0
    )

    revenue_net = float(
        frame["amount_vatless"]
        .fillna(0)
        .sum()
    )

    cogs_man = float(
        frame["cogs_man"]
        .fillna(0)
        .sum()
    )

    net_comission = float(
        frame["net_comission"]
        .fillna(0)
        .sum()
    )

    margin_man = float(
        frame["margin_man"]
        .fillna(0)
        .sum()
    )

    margin_pct = (
        margin_man
        / revenue_net
        * 100
        if revenue_net
        else 0.0
    )

    return {
        "sales_qty": sales_qty,
        "avg_price": avg_price,

        "sales_amount": sales_amount,

        "amount_vatless": revenue_net,
        "cogs_man": cogs_man,
        "net_comission": net_comission,

        "margin_man": margin_man,
        "margin_pct": margin_pct,
    }


def _pct_change(
    current: float,
    previous: float,
) -> float | None:

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
        - 1
    ) * 100


def _brand_elasticity(
    frame: pd.DataFrame,
) -> dict:
    """
    Оценивает историческую чувствительность количества
    к средней цене бренда:

        ln(Q) = a + b * ln(P)

    b — наблюдаемая ценовая чувствительность.

    Например:
        b = -1.4

    означает, что исторически изменение средней цены на +1%
    сопровождалось примерно -1.4% изменения количества.

    Это НЕ причинная эластичность и НЕ обещание результата.
    """

    if frame.empty:
        return {
            "elasticity": None,
            "r2": None,
            "observations": 0,
            "price_cv_pct": 0.0,
            "confidence": "Нет данных",
        }

    work = frame[
        (frame["sales_qty"] > 0)
        & (frame["avg_price"] > 0)
    ][
        [
            "sales_qty",
            "avg_price",
        ]
    ].copy()

    # Слишком малые дни создают огромный шум.
    work = work[
        work["sales_qty"] >= 3
    ]

    if len(work) < 15:
        return {
            "elasticity": None,
            "r2": None,
            "observations": len(work),
            "price_cv_pct": 0.0,
            "confidence": "Мало наблюдений",
        }

    # -----------------------------------------------------------------
    # Убираем крайние дневные выбросы.
    # -----------------------------------------------------------------

    price_low = work[
        "avg_price"
    ].quantile(
        0.025
    )

    price_high = work[
        "avg_price"
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
        work["avg_price"].between(
            price_low,
            price_high,
        )
        & work["sales_qty"].between(
            qty_low,
            qty_high,
        )
    ].copy()

    if len(work) < 12:
        return {
            "elasticity": None,
            "r2": None,
            "observations": len(work),
            "price_cv_pct": 0.0,
            "confidence": "Мало наблюдений",
        }

    price_mean = float(
        work["avg_price"].mean()
    )

    price_std = float(
        work["avg_price"].std()
    )

    price_cv_pct = (
        price_std
        / price_mean
        * 100
        if price_mean
        else 0.0
    )

    # Если цена почти не менялась,
    # оценивать чувствительность бессмысленно.
    if price_cv_pct < 3:
        return {
            "elasticity": None,
            "r2": None,
            "observations": len(work),
            "price_cv_pct": price_cv_pct,
            "confidence": "Цена почти не менялась",
        }

    x = np.log(
        work["avg_price"]
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
            (
                y
                - predicted
            ) ** 2
        )
    )

    ss_tot = float(
        np.sum(
            (
                y
                - y.mean()
            ) ** 2
        )
    )

    r2 = (
        1
        - ss_res / ss_tot
        if ss_tot
        else 0.0
    )

    elasticity = float(
        slope
    )

    # Ограничиваем совсем дикие оценки.
    elasticity = max(
        min(
            elasticity,
            4.0,
        ),
        -4.0,
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


# =============================================================================
# МОДЕЛЬНЫЙ БАЛАНС ЦЕНЫ / СПРОСА / МАРЖИ
# =============================================================================


def _brand_balance_scenario(
    current: dict,
    elasticity: float | None,
) -> dict:
    """
    Строит модельную кривую:
        цена -> количество -> выручка -> маржа ₽ -> маржинальность.

    Используется статистическая чувствительность:

        Q1 / Q0 = (P1 / P0) ** elasticity

    ВАЖНО:
    это модельный сценарий, а не причинная оценка.

    Допущения:
    - FIFO-себестоимость единицы условно постоянна;
    - доля комиссии WB в выручке условно постоянна;
    - маркетинг, штрафы и прочие распределяемые расходы WB
      НЕ входят в расчёт;
    - анализируем цену в диапазоне -15% ... +15%.

    Точки:
    1. max_margin:
       сценарий максимальной маржи в рублях.

    2. balance:
       максимальный спрос среди сценариев, которые:
       - сохраняют >= 98% максимальной модельной маржи ₽;
       - не снижают текущую маржинальность более чем на 3 п.п.
    """

    if elasticity is None:
        return {
            "available": False,
            "reason": "Нет оценки чувствительности",
        }

    elasticity = float(
        elasticity
    )

    # Для ценового оптимума нас интересует обратная связь.
    # При положительной эластичности цена и количество двигались
    # в одну сторону — это чаще сигнал изменения микса,
    # а не надёжная база для ценового сценария.
    if elasticity >= -0.15:
        return {
            "available": False,
            "reason": (
                "Нет устойчивой обратной реакции "
                "количества на среднюю цену"
            ),
        }

    base_qty = number(
        current.get(
            "sales_qty"
        )
    )

    base_revenue = number(
        current.get(
            "amount_vatless"
        )
    )

    base_cogs = number(
        current.get(
            "cogs_man"
        )
    )

    base_commission = abs(
        number(
            current.get(
                "net_comission"
            )
        )
    )

    base_margin = number(
        current.get(
            "margin_man"
        )
    )

    base_margin_pct = number(
        current.get(
            "margin_pct"
        )
    )

    base_price = number(
        current.get(
            "avg_price"
        )
    )

    if (
        base_qty <= 0
        or base_revenue <= 0
        or base_price <= 0
        or base_margin <= 0
    ):
        return {
            "available": False,
            "reason": "Недостаточно текущих финансовых данных",
        }

    # -----------------------------------------------------------------
    # ЭКОНОМИКА ЕДИНИЦЫ
    # -----------------------------------------------------------------

    revenue_per_unit = (
        base_revenue
        / base_qty
    )

    cogs_per_unit = (
        base_cogs
        / base_qty
    )

    commission_rate = (
        base_commission
        / base_revenue
        if base_revenue
        else 0.0
    )

    # -----------------------------------------------------------------
    # ПЛОТНАЯ СЕТКА ЦЕНОВЫХ СЦЕНАРИЕВ
    #
    # Шаг 0.25 п.п. вместо старых грубых 2.5 п.п.
    # -----------------------------------------------------------------

    scenarios: list[dict] = []

    price_change_pct = -15.0

    while price_change_pct <= 15.0001:

        price_factor = (
            1
            + price_change_pct
            / 100
        )

        if price_factor <= 0:
            price_change_pct += 0.25
            continue

        qty_factor = (
            price_factor
            ** elasticity
        )

        projected_qty = (
            base_qty
            * qty_factor
        )

        projected_revenue_per_unit = (
            revenue_per_unit
            * price_factor
        )

        projected_revenue = (
            projected_qty
            * projected_revenue_per_unit
        )

        projected_cogs = (
            projected_qty
            * cogs_per_unit
        )

        projected_commission = (
            projected_revenue
            * commission_rate
        )

        projected_margin = (
            projected_revenue
            - projected_cogs
            - projected_commission
        )

        projected_margin_pct = (
            projected_margin
            / projected_revenue
            * 100
            if projected_revenue
            else 0.0
        )

        qty_change_pct = (
            (
                projected_qty
                / base_qty
            )
            - 1
        ) * 100

        revenue_change_pct = (
            (
                projected_revenue
                / base_revenue
            )
            - 1
        ) * 100

        margin_change_pct = (
            (
                projected_margin
                / base_margin
            )
            - 1
        ) * 100

        margin_delta_pp = (
            projected_margin_pct
            - base_margin_pct
        )

        scenarios.append(
            {
                "price_change_pct": (
                    round(
                        price_change_pct,
                        2,
                    )
                ),

                "projected_price": (
                    base_price
                    * price_factor
                ),

                "projected_qty": (
                    projected_qty
                ),

                "qty_change_pct": (
                    qty_change_pct
                ),

                "projected_revenue": (
                    projected_revenue
                ),

                "revenue_change_pct": (
                    revenue_change_pct
                ),

                "projected_margin": (
                    projected_margin
                ),

                "margin_change_pct": (
                    margin_change_pct
                ),

                "projected_margin_pct": (
                    projected_margin_pct
                ),

                "margin_delta_pp": (
                    margin_delta_pp
                ),
            }
        )

        price_change_pct += 0.25

    if not scenarios:
        return {
            "available": False,
            "reason": "Не удалось построить сценарии",
        }

    # -----------------------------------------------------------------
    # ТОЧКА МАКСИМАЛЬНОЙ МАРЖИ ₽
    # -----------------------------------------------------------------

    max_margin = max(
        scenarios,
        key=lambda row: row[
            "projected_margin"
        ],
    )

    max_margin_value = number(
        max_margin.get(
            "projected_margin"
        )
    )

    # -----------------------------------------------------------------
    # ЗОНА БАЛАНСА
    #
    # Допускаем потерять максимум 2% от лучшей возможной маржи ₽,
    # но получаем максимально возможное количество.
    #
    # Дополнительно не разрешаем маржинальности упасть
    # более чем на 3 п.п. от текущей.
    # -----------------------------------------------------------------

    balance_candidates = [
        row
        for row in scenarios
        if (
            number(
                row.get(
                    "projected_margin"
                )
            )
            >= max_margin_value * 0.98
        )
        and (
            number(
                row.get(
                    "projected_margin_pct"
                )
            )
            >= base_margin_pct - 3.0
        )
    ]

    if balance_candidates:

        balance = max(
            balance_candidates,
            key=lambda row: (
                row[
                    "projected_qty"
                ],
                row[
                    "projected_margin"
                ],
            ),
        )

    else:

        balance = max_margin

    # -----------------------------------------------------------------
    # ТЕКУЩАЯ ТОЧКА 0%
    # -----------------------------------------------------------------

    current_scenario = min(
        scenarios,
        key=lambda row: abs(
            row[
                "price_change_pct"
            ]
        ),
    )

    return {
        "available": True,

        "elasticity": (
            elasticity
        ),

        "base_price": (
            base_price
        ),

        "base_qty": (
            base_qty
        ),

        "base_revenue": (
            base_revenue
        ),

        "base_margin": (
            base_margin
        ),

        "base_margin_pct": (
            base_margin_pct
        ),

        "current": (
            current_scenario
        ),

        "max_margin": (
            max_margin
        ),

        "balance": (
            balance
        ),

        # -------------------------------------------------------------
        # Для обратной совместимости со старой страницей
        # -------------------------------------------------------------

        "recommended_price_change_pct": (
            balance[
                "price_change_pct"
            ]
        ),

        "projected_price": (
            balance[
                "projected_price"
            ]
        ),

        "projected_qty": (
            balance[
                "projected_qty"
            ]
        ),

        "projected_qty_change_pct": (
            balance[
                "qty_change_pct"
            ]
        ),

        "projected_revenue": (
            balance[
                "projected_revenue"
            ]
        ),

        "projected_revenue_change_pct": (
            balance[
                "revenue_change_pct"
            ]
        ),

        "projected_margin": (
            balance[
                "projected_margin"
            ]
        ),

        "projected_margin_change_pct": (
            balance[
                "margin_change_pct"
            ]
        ),

        "projected_margin_pct": (
            balance[
                "projected_margin_pct"
            ]
        ),

        "projected_margin_delta_pp": (
            balance[
                "margin_delta_pp"
            ]
        ),

        "scenarios": (
            scenarios
        ),
    }
    
# =============================================================================
# АНАЛИЗ БРЕНДОВ
# =============================================================================


def _build_brand_price_analysis(
    rows: list[dict],
    report_date: date,
) -> dict:
    """
    Строит:
        - матрицу чувствительности;
        - модельные ценовые сценарии;
        - аномалии последних 14 дней.
    """

    frame = pd.DataFrame(
        rows
        or []
    )

    if frame.empty:
        return {
            "brands": [],
            "opportunities": [],
            "anomalies": [],
        }

    frame["date_from"] = pd.to_datetime(
        frame["date_from"],
        errors="coerce",
    )

    numeric_columns = (
        "sales_qty",
        "sales_amount",
        "avg_price",
        "amount_vatless",
        "cogs_man",
        "net_comission",
        "margin_man",
    )

    for column in numeric_columns:

        frame[column] = pd.to_numeric(
            frame[column],
            errors="coerce",
        ).fillna(0)

    frame = frame[
        frame["date_from"].notna()
    ].copy()

    recent_start = pd.Timestamp(
        report_date
        - timedelta(
            days=13
        )
    )

    previous_start = pd.Timestamp(
        report_date
        - timedelta(
            days=27
        )
    )

    previous_end = (
        recent_start
        - pd.Timedelta(
            days=1
        )
    )

    brand_rows = []

    for brand, brand_frame in frame.groupby(
        "brand",
        dropna=False,
    ):

        brand_name = (
            str(
                brand
                or "Бренд не указан"
            )
            .strip()
        )

        full_metrics = _period_brand_metrics(
            brand_frame
        )

        # Не анализируем микроскопические бренды.
        if (
            full_metrics[
                "sales_qty"
            ]
            < 50
        ):
            continue

        recent_frame = brand_frame[
            brand_frame[
                "date_from"
            ]
            >= recent_start
        ]

        previous_frame = brand_frame[
            (
                brand_frame[
                    "date_from"
                ]
                >= previous_start
            )
            & (
                brand_frame[
                    "date_from"
                ]
                <= previous_end
            )
        ]

        recent = _period_brand_metrics(
            recent_frame
        )

        previous = _period_brand_metrics(
            previous_frame
        )

        if recent[
            "sales_qty"
        ] <= 0:
            continue

        elasticity_info = (
            _brand_elasticity(
                brand_frame
            )
        )

        elasticity = (
            elasticity_info.get(
                "elasticity"
            )
        )

        price_change_pct = (
            _pct_change(
                recent[
                    "avg_price"
                ],
                previous[
                    "avg_price"
                ],
            )
        )

        qty_change_pct = (
            _pct_change(
                recent[
                    "sales_qty"
                ],
                previous[
                    "sales_qty"
                ],
            )
        )

        revenue_change_pct = (
            _pct_change(
                recent[
                    "amount_vatless"
                ],
                previous[
                    "amount_vatless"
                ],
            )
        )

        balance = (
            _brand_balance_scenario(
                recent,
                elasticity,
            )
        )

        brand_rows.append(
            {
                "brand": brand_name,

                "elasticity": elasticity,

                "sensitivity": (
                    abs(
                        elasticity
                    )
                    if elasticity is not None
                    else None
                ),

                "r2": (
                    elasticity_info.get(
                        "r2"
                    )
                ),

                "confidence": (
                    elasticity_info.get(
                        "confidence"
                    )
                ),

                "observations": (
                    elasticity_info.get(
                        "observations"
                    )
                ),

                "price_cv_pct": (
                    elasticity_info.get(
                        "price_cv_pct"
                    )
                ),

                "sales_qty_14d": (
                    recent[
                        "sales_qty"
                    ]
                ),

                "avg_price_14d": (
                    recent[
                        "avg_price"
                    ]
                ),

                "revenue_14d": (
                    recent[
                        "amount_vatless"
                    ]
                ),

                "margin_14d": (
                    recent[
                        "margin_man"
                    ]
                ),

                "margin_pct": (
                    recent[
                        "margin_pct"
                    ]
                ),

                "price_change_pct": (
                    price_change_pct
                ),

                "qty_change_pct": (
                    qty_change_pct
                ),

                "revenue_change_pct": (
                    revenue_change_pct
                ),

                "balance": (
                    balance
                ),
            }
        )

    if not brand_rows:
        return {
            "brands": [],
            "opportunities": [],
            "anomalies": [],
        }

    # -----------------------------------------------------------------
    # Убираем бренды с совсем слабой моделью из матрицы.
    # -----------------------------------------------------------------

    matrix_rows = [
        row
        for row in brand_rows
        if (
            row.get(
                "elasticity"
            )
            is not None
            and row.get(
                "confidence"
            )
            in (
                "Высокая",
                "Средняя",
            )
        )
    ]

    # -----------------------------------------------------------------
    # Возможности.
    #
    # Нам интересны только сценарии, которые:
    # - увеличивают количество;
    # - не требуют повышения цены;
    # - сохраняют маржу по заданным ограничениям.
    # -----------------------------------------------------------------

    opportunities = []

    for row in matrix_rows:

        balance = (
            row.get(
                "balance"
            )
            or {}
        )

        if not balance.get(
            "available"
        ):
            continue

        price_change = number(
            balance.get(
                "recommended_price_change_pct"
            )
        )

        qty_change = number(
            balance.get(
                "projected_qty_change_pct"
            )
        )

        if (
            price_change < 0
            and qty_change > 1
        ):
            opportunities.append(
                row
            )

    opportunities.sort(
        key=lambda row: (
            number(
                row[
                    "balance"
                ].get(
                    "projected_qty_change_pct"
                )
            ),
            number(
                row.get(
                    "revenue_14d"
                )
            ),
        ),
        reverse=True,
    )

    opportunities = (
        opportunities[:5]
    )

    # -----------------------------------------------------------------
    # Аномалии / сигналы
    # -----------------------------------------------------------------

    anomalies = []

    for row in brand_rows:

        price_change = row.get(
            "price_change_pct"
        )

        qty_change = row.get(
            "qty_change_pct"
        )

        if (
            price_change is None
            or qty_change is None
        ):
            continue

        price_change = number(
            price_change
        )

        qty_change = number(
            qty_change
        )

        anomaly = None

        # Снизили среднюю цену,
        # но заметного прироста количества не получили.
        if (
            price_change <= -5
            and qty_change <= 5
        ):

            anomaly = {
                "type": "ineffective_discount",
                "tone": "warning",

                "title": (
                    "Снижение цены пока "
                    "не дало прироста спроса"
                ),
            }

        # Цена растёт, количество падает.
        elif (
            price_change >= 5
            and qty_change <= -10
        ):

            anomaly = {
                "type": "price_pressure",
                "tone": "negative",

                "title": (
                    "Рост средней цены "
                    "сопровождается снижением спроса"
                ),
            }

        # Цена снизилась и количество резко выросло.
        elif (
            price_change <= -5
            and qty_change >= 15
        ):

            anomaly = {
                "type": "responsive_demand",
                "tone": "positive",

                "title": (
                    "Спрос заметно вырос "
                    "при более низкой средней цене"
                ),
            }

        # Цена и спрос растут одновременно —
        # возможный pricing power / сильный микс.
        elif (
            price_change >= 5
            and qty_change >= 10
        ):

            anomaly = {
                "type": "pricing_power",
                "tone": "positive",

                "title": (
                    "Цена и физический спрос "
                    "растут одновременно"
                ),
            }

        if anomaly:

            anomaly.update(
                {
                    "brand": (
                        row[
                            "brand"
                        ]
                    ),

                    "price_change_pct": (
                        price_change
                    ),

                    "qty_change_pct": (
                        qty_change
                    ),

                    "margin_pct": (
                        row[
                            "margin_pct"
                        ]
                    ),

                    "revenue_14d": (
                        row[
                            "revenue_14d"
                        ]
                    ),
                }
            )

            anomalies.append(
                anomaly
            )

    anomalies.sort(
        key=lambda row: abs(
            number(
                row.get(
                    "price_change_pct"
                )
            )
        )
        + abs(
            number(
                row.get(
                    "qty_change_pct"
                )
            )
        ),
        reverse=True,
    )

    return {
        "brands": matrix_rows,

        "opportunities": (
            opportunities
        ),

        "anomalies": (
            anomalies[:4]
        ),
    }



def get_sales_data(
    report_date: date,
    plan_source: dict[str, Any],
) -> dict[str, Any]:
    previous_date = (
        report_date
        - timedelta(days=1)
    )

    previous_month_date = previous_month_same_day(
        report_date
    )

    previous_year_date = previous_year_same_day(
        report_date
    )

    cache: dict[
        tuple[int, int],
        list[dict],
    ] = {}

    current_month_rows = plan_source.get(
        "daily_rows",
        [],
    )

    if current_month_rows:
        cache[
            (
                report_date.year,
                report_date.month,
            )
        ] = list(
            current_month_rows
        )

    # ================================================================
    # ДЕНЬ И СРАВНИТЕЛЬНЫЕ ДАТЫ
    # ================================================================

    current_sales = _daily_row(
        report_date,
        cache,
    )

    previous_sales = _daily_row(
        previous_date,
        cache,
    )

    previous_month_sales = _daily_row(
        previous_month_date,
        cache,
    )

    previous_year_sales = _daily_row(
        previous_year_date,
        cache,
    )

    # ================================================================
    # ТЕПЛОВОЙ КАЛЕНДАРЬ — ПОСЛЕДНИЕ 35 ДНЕЙ
    # ================================================================

    trend_rows: list[dict] = []

    for current_day in date_range(
        report_date - timedelta(days=34),
        report_date,
    ):
        source = _daily_row(
            current_day,
            cache,
        )

        trend_rows.append(
            {
                "date_from": current_day.isoformat(),
                "amount": number(
                    source.get("fact")
                ),
                "sales_amount": number(
                    source.get("sales_amount")
                ),
                "returns_amount": number(
                    source.get("returns_amount")
                ),
            }
        )

    # ================================================================
    # ПЕРИОДЫ
    # ================================================================

    month_start = report_date.replace(
        day=1
    )

    prior_month_end = previous_month_same_day(
        report_date
    )

    prior_month_start = prior_month_end.replace(
        day=1
    )

    year_start = date(
        report_date.year,
        1,
        1,
    )

    prior_year_start = date(
        report_date.year - 1,
        1,
        1,
    )

    prior_year_end = previous_year_same_day(
        report_date
    )

    # ================================================================
    # MTD / YTD
    # ================================================================

    mtd = number(
        get_fact_for_period(
            month_start,
            report_date,
        )
    )

    prior_mtd = number(
        get_fact_for_period(
            prior_month_start,
            prior_month_end,
        )
    )

    ytd = number(
        get_fact_for_period(
            year_start,
            report_date,
        )
    )

    prior_ytd = number(
        get_fact_for_period(
            prior_year_start,
            prior_year_end,
        )
    )

    ytd_daily_rows = _build_ytd_daily_rows(
        report_date=report_date,
        current_year_start=year_start,
        previous_year_start=prior_year_start,
        previous_year_end=prior_year_end,
        cache=cache,
    )

    # ================================================================
    # ДАННЫЕ ИЗ DASHBOARD
    # ================================================================

    with DashboardData() as dashboard:
        daily_finance = (
            dashboard
            .get_dayly_sales_grid_data(
                start=report_date,
                end=report_date,
            )
        )

        previous_finance = (
            dashboard
            .get_dayly_sales_grid_data(
                start=previous_date,
                end=previous_date,
            )
        )

        # ============================================================
        # ТОП-5 БРЕНДОВ
        #
        # revenue:
        # чистая выручка с учётом возвратов;
        #
        # sold_units:
        # количество положительных продаж;
        #
        # avg_price:
        # средняя цена только по положительным продажам.
        # ============================================================

        top_brands = dashboard.con.execute(
            """
            SELECT
                COALESCE(
                    NULLIF(
                        TRIM(t.brand),
                        ''
                    ),
                    'Бренд не указан'
                ) AS name,

                ROUND(
                    SUM(t.cr_rev) / 100.0,
                    2
                ) AS revenue,

                SUM(
                    CASE
                        WHEN t.cr_rev > 0 THEN 1
                        ELSE 0
                    END
                ) AS sold_units,

                SUM(
                    CASE
                        WHEN t.cr_rev < 0 THEN 1
                        ELSE 0
                    END
                ) AS returned_units,

                SUM(
                    CASE
                        WHEN t.cr_rev > 0 THEN 1
                        WHEN t.cr_rev < 0 THEN -1
                        ELSE 0
                    END
                ) AS net_units,

                ROUND(
                    SUM(
                        CASE
                            WHEN t.cr_rev > 0
                            THEN t.cr_rev
                            ELSE 0
                        END
                    ) / 100.0,
                    2
                ) AS sales_amount,

                ABS(
                    ROUND(
                        SUM(
                            CASE
                                WHEN t.cr_rev < 0
                                THEN t.cr_rev
                                ELSE 0
                            END
                        ) / 100.0,
                        2
                    )
                ) AS returns_amount,

                ROUND(
                    SUM(
                        CASE
                            WHEN t.cr_rev > 0
                            THEN t.cr_rev
                            ELSE 0
                        END
                    ) / 100.0
                    /
                    NULLIF(
                        SUM(
                            CASE
                                WHEN t.cr_rev > 0 THEN 1
                                ELSE 0
                            END
                        ),
                        0
                    ),
                    2
                ) AS avg_price

            FROM base t

            WHERE
                t.date_from::DATE = ?::DATE
                AND t.cr_rev <> 0

            GROUP BY
                1

            HAVING
                SUM(t.cr_rev) > 0

            ORDER BY
                revenue DESC

            LIMIT 5
            """,
            [
                report_date,
            ],
        ).df()

        # ============================================================
        # ТОП-5 КАТЕГОРИЙ
        # ============================================================

        top_categories = dashboard.con.execute(
            """
            SELECT
                COALESCE(
                    NULLIF(
                        TRIM(t.subject_name),
                        ''
                    ),
                    'Категория не указана'
                ) AS name,

                ROUND(
                    SUM(t.cr_rev) / 100.0,
                    2
                ) AS revenue,

                SUM(
                    CASE
                        WHEN t.cr_rev > 0 THEN 1
                        ELSE 0
                    END
                ) AS sold_units,

                SUM(
                    CASE
                        WHEN t.cr_rev < 0 THEN 1
                        ELSE 0
                    END
                ) AS returned_units,

                SUM(
                    CASE
                        WHEN t.cr_rev > 0 THEN 1
                        WHEN t.cr_rev < 0 THEN -1
                        ELSE 0
                    END
                ) AS net_units,

                ROUND(
                    SUM(
                        CASE
                            WHEN t.cr_rev > 0
                            THEN t.cr_rev
                            ELSE 0
                        END
                    ) / 100.0,
                    2
                ) AS sales_amount,

                ABS(
                    ROUND(
                        SUM(
                            CASE
                                WHEN t.cr_rev < 0
                                THEN t.cr_rev
                                ELSE 0
                            END
                        ) / 100.0,
                        2
                    )
                ) AS returns_amount,

                ROUND(
                    SUM(
                        CASE
                            WHEN t.cr_rev > 0
                            THEN t.cr_rev
                            ELSE 0
                        END
                    ) / 100.0
                    /
                    NULLIF(
                        SUM(
                            CASE
                                WHEN t.cr_rev > 0 THEN 1
                                ELSE 0
                            END
                        ),
                        0
                    ),
                    2
                ) AS avg_price

            FROM base t

            WHERE
                t.date_from::DATE = ?::DATE
                AND t.cr_rev <> 0

            GROUP BY
                1

            HAVING
                SUM(t.cr_rev) > 0

            ORDER BY
                revenue DESC

            LIMIT 5
            """,
            [
                report_date,
            ],
        ).df()

        # ============================================================
        # ДНЕВНАЯ ЦЕНА — 90 ДНЕЙ
        # ============================================================

        daily_price = dashboard.con.execute(
            """
            SELECT
                t.date_from::DATE AS date_from,

                STRFTIME(
                    t.date_from::DATE,
                    '%d.%m'
                ) AS date_label,

                SUM(
                    CASE
                        WHEN t.cr_rev > 0 THEN 1
                        ELSE 0
                    END
                ) AS sales_qty,

                ROUND(
                    SUM(
                        CASE
                            WHEN t.cr_rev > 0
                            THEN t.cr_rev
                            ELSE 0
                        END
                    ) / 100.0
                    /
                    NULLIF(
                        SUM(
                            CASE
                                WHEN t.cr_rev > 0 THEN 1
                                ELSE 0
                            END
                        ),
                        0
                    ),
                    2
                ) AS avg_price,

                ROUND(
                    SUM(t.cr_rev) / 100.0,
                    2
                ) AS net_amount

            FROM base t

            WHERE
                t.date_from::DATE
                BETWEEN ?::DATE AND ?::DATE

            GROUP BY
                1,
                2

            ORDER BY
                1
            """,
            [
                report_date - timedelta(days=89),
                report_date,
            ],
        ).df()

        # ============================================================
        # МЕСЯЧНАЯ ЦЕНА — 12 МЕСЯЦЕВ
        # ============================================================

        monthly_price = dashboard.con.execute(
            """
            SELECT
                DATE_TRUNC(
                    'month',
                    t.date_from::DATE
                )::DATE AS month_date,

                STRFTIME(
                    DATE_TRUNC(
                        'month',
                        t.date_from::DATE
                    ),
                    '%m.%Y'
                ) AS month_label,

                SUM(
                    CASE
                        WHEN t.cr_rev > 0 THEN 1
                        ELSE 0
                    END
                ) AS sales_qty,

                ROUND(
                    SUM(
                        CASE
                            WHEN t.cr_rev > 0
                            THEN t.cr_rev
                            ELSE 0
                        END
                    ) / 100.0
                    /
                    NULLIF(
                        SUM(
                            CASE
                                WHEN t.cr_rev > 0 THEN 1
                                ELSE 0
                            END
                        ),
                        0
                    ),
                    2
                ) AS avg_price,

                ROUND(
                    SUM(t.cr_rev) / 100.0,
                    2
                ) AS net_amount

            FROM base t

            WHERE
                t.date_from::DATE
                BETWEEN ?::DATE AND ?::DATE

            GROUP BY
                1,
                2

            ORDER BY
                1
            """,
            [
                report_date.replace(day=1)
                - pd.DateOffset(months=11),
                report_date,
            ],
        ).df()

        # ============================================================
        # КАТЕГОРИИ ВОЗВРАТОВ
        # ============================================================

        return_categories = dashboard.con.execute(
            """
            SELECT
                COALESCE(
                    NULLIF(
                        TRIM(t.subject_name),
                        ''
                    ),
                    'Категория не указана'
                ) AS name,

                ABS(
                    ROUND(
                        SUM(
                            CASE
                                WHEN t.cr_rev < 0
                                THEN t.cr_rev
                                ELSE 0
                            END
                        ) / 100.0,
                        2
                    )
                ) AS returns_amount,

                SUM(
                    CASE
                        WHEN t.cr_rev < 0 THEN 1
                        ELSE 0
                    END
                ) AS returns_qty

            FROM base t

            WHERE
                t.date_from::DATE = ?::DATE

            GROUP BY
                1

            HAVING
                SUM(
                    CASE
                        WHEN t.cr_rev < 0 THEN 1
                        ELSE 0
                    END
                ) > 0

            ORDER BY
                returns_amount DESC

            LIMIT 5
            """,
            [
                report_date,
            ],
        ).df()
        
        
        
        # ============================================================
        # ЦЕНОВАЯ ЧУВСТВИТЕЛЬНОСТЬ БРЕНДОВ — 90 ДНЕЙ
        #
        # Используется только для аналитического листа спроса.
        #
        # margin_man:
        #   выручка без НДС
        #   - управленческая FIFO-себестоимость
        #   + комиссия WB
        #
        # Маркетинг, штрафы и прочие распределяемые расходы WB
        # здесь НЕ учитываются.
        # ============================================================

        brand_price_daily = (
            dashboard
            .con
            .execute(
                """
                WITH commissions AS (

                    SELECT
                        rrd_id,

                        COALESCE(
                            SUM(
                                val
                                / (
                                    100 + vat_rate
                                )
                                * 100
                            ) FILTER (
                                WHERE
                                    field = 'comission'
                                    AND oper = 'dt'
                            ),
                            0
                        )
                        -
                        COALESCE(
                            SUM(
                                val
                                / (
                                    100 + vat_rate
                                )
                                * 100
                            ) FILTER (
                                WHERE
                                    field = 'comission'
                                    AND oper = 'cr'
                            ),
                            0
                        ) AS net_comission

                    FROM sales.sales_long

                    GROUP BY
                        rrd_id
                )

                SELECT
                    t.date_from::DATE
                        AS date_from,

                    COALESCE(
                        NULLIF(
                            TRIM(t.brand),
                            ''
                        ),
                        'Бренд не указан'
                    ) AS brand,

                    SUM(
                        CASE
                            WHEN t.cr_rev > 0
                                THEN 1
                            ELSE 0
                        END
                    ) AS sales_qty,

                    ROUND(
                        SUM(
                            CASE
                                WHEN t.cr_rev > 0
                                    THEN t.cr_rev
                                ELSE 0
                            END
                        ) / 100.0,
                        2
                    ) AS sales_amount,

                    ROUND(
                        SUM(
                            CASE
                                WHEN t.cr_rev > 0
                                    THEN t.cr_rev
                                ELSE 0
                            END
                        )
                        / 100.0
                        /
                        NULLIF(
                            SUM(
                                CASE
                                    WHEN t.cr_rev > 0
                                        THEN 1
                                    ELSE 0
                                END
                            ),
                            0
                        ),
                        2
                    ) AS avg_price,

                    ROUND(
                        SUM(
                            t.cr_rev
                            / (
                                100 + t.vat_rate
                            )
                            * 100
                        )
                        / 100.0,
                        2
                    ) AS amount_vatless,

                    ROUND(
                        SUM(
                            t.adjusted_cogs_man
                        )
                        / 100.0,
                        2
                    ) AS cogs_man,

                    ROUND(
                        SUM(
                            COALESCE(
                                c.net_comission,
                                0
                            )
                        )
                        / 100.0,
                        2
                    ) AS net_comission,

                    ROUND(
                        (
                            SUM(
                                t.cr_rev
                                / (
                                    100 + t.vat_rate
                                )
                                * 100
                            )
                            -
                            SUM(
                                t.adjusted_cogs_man
                            )
                            +
                            SUM(
                                COALESCE(
                                    c.net_comission,
                                    0
                                )
                            )
                        )
                        / 100.0,
                        2
                    ) AS margin_man

                FROM base t

                LEFT JOIN commissions c
                    ON c.rrd_id = t.rrd_id

                WHERE
                    t.cr_rev <> 0

                    AND t.date_from::DATE
                        BETWEEN ?::DATE
                        AND ?::DATE

                GROUP BY
                    1,
                    2

                ORDER BY
                    2,
                    1
                """,
                [
                    (
                        report_date
                        - timedelta(
                            days=89
                        )
                    ),
                    report_date,
                ],
            )
            .df()
        )
    

    # ================================================================
    # ИТОГОВЫЙ PAYLOAD
    # ================================================================

    finance_row = first_row(
        daily_finance
    )

    previous_finance_row = first_row(
        previous_finance
    )

    fact = number(
        current_sales.get("fact")
    )

    sales_transactions = number(
        current_sales.get(
            "sales_transactions"
        )
    )

    returns_transactions = number(
        current_sales.get(
            "returns_transactions"
        )
    )

    returns_rate = (
        returns_transactions
        / sales_transactions
        * 100
        if sales_transactions
        else 0
    )

    comparisons = {
        "previous_day": _comparison(
            "К предыдущему дню",
            fact,
            number(
                previous_sales.get("fact")
            ),
            previous_date.strftime(
                "%d.%m.%Y"
            ),
        ),

        "previous_month_day": _comparison(
            "К аналогичному дню прошлого месяца",
            fact,
            number(
                previous_month_sales.get("fact")
            ),
            previous_month_date.strftime(
                "%d.%m.%Y"
            ),
        ),

        "previous_year_day": _comparison(
            "К аналогичному дню прошлого года",
            fact,
            number(
                previous_year_sales.get("fact")
            ),
            previous_year_date.strftime(
                "%d.%m.%Y"
            ),
        ),

        "mtd": _comparison(
            "С начала месяца",
            mtd,
            prior_mtd,
            (
                f"{prior_month_start:%d.%m}"
                f"-{prior_month_end:%d.%m.%Y}"
            ),
        ),

        "ytd": _comparison(
            "С начала года",
            ytd,
            prior_ytd,
            (
                f"{prior_year_start:%d.%m}"
                f"-{prior_year_end:%d.%m.%Y}"
            ),
        ),
    }

    daily_rows = dataframe_records(
        daily_price
    )

    monthly_rows = dataframe_records(
        monthly_price
    )
    
    brand_price_analysis = (
        _build_brand_price_analysis(
            dataframe_records(
                brand_price_daily
            ),
            report_date,
        )
    )

    return {
        "kpi": {
            **finance_row,

            "amount": fact,

            "sales_amount": number(
                current_sales.get(
                    "sales_amount"
                )
            ),

            "returns_amount": number(
                current_sales.get(
                    "returns_amount"
                )
            ),

            "sales_transactions": (
                sales_transactions
            ),

            "returns_transactions": (
                returns_transactions
            ),

            "total_net_sales": number(
                current_sales.get("qty")
            ),

            "avg_price": number(
                current_sales.get("avg_price")
            ),

            "returns_rate": returns_rate,

            "revenue_change_pct": (
                comparisons[
                    "previous_day"
                ][
                    "change_pct"
                ]
            ),

            "margin_change_pct": change_pct(
                number(
                    finance_row.get(
                        "margin_man"
                    )
                ),
                number(
                    previous_finance_row.get(
                        "margin_man"
                    )
                ),
            ),
        },

        "comparisons": comparisons,

        "trend": trend_rows,

        "ytd_daily_rows": ytd_daily_rows,

        "top_brands": dataframe_records(
            top_brands
        ),

        "top_categories": dataframe_records(
            top_categories
        ),

        "return_categories": dataframe_records(
            return_categories
        ),

        "daily_price_rows": daily_rows,

        "monthly_price_rows": monthly_rows,
        
        "brand_price_analysis": (
            brand_price_analysis
        ),

        "price_analysis": {
            "daily_corr": _corr(
                daily_rows,
                "sales_qty",
                "avg_price",
            ),

            "monthly_corr": _corr(
                monthly_rows,
                "sales_qty",
                "avg_price",
            ),
        },
    }