# gear/app/stats/profit_optimizer_data.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

import numpy as np
import pandas as pd

from conns import get_duckdb_conn_with_opt
from .data import BASE_QUERY, WB_COSTS_QUERY


@dataclass(frozen=True)
class OptimizerConfig:
    history_days: int = 180
    min_price_factor: float = 0.80
    max_price_factor: float = 1.20
    price_steps: int = 81
    min_elasticity_observations: int = 3
    stockout_days: float = 14.0
    excess_stock_days: float = 120.0
    good_margin_pct: float = 20.0
    good_roas: float = 6.0


CONFIG = OptimizerConfig()


def _as_date(value) -> date:
    if value is None:
        return date.today()
    if isinstance(value, date):
        return value
    parsed = pd.to_datetime(value, errors="coerce")
    return date.today() if pd.isna(parsed) else parsed.date()


def _safe_div(a, b):
    if isinstance(b, pd.Series):
        b = b.replace(0, np.nan)
    return a / b


def _estimate_elasticity(
    weekly: pd.DataFrame,
    config: OptimizerConfig = CONFIG,
) -> pd.DataFrame:
    if weekly.empty:
        return pd.DataFrame(
            columns=["nm_id", "price_elasticity", "elasticity_observations"]
        )

    work = weekly.copy()
    work["week"] = pd.to_datetime(work["week"], errors="coerce")
    for col in ["nm_id", "quantity", "revenue"]:
        work[col] = pd.to_numeric(work[col], errors="coerce")

    work = (
        work.dropna(subset=["nm_id", "week", "quantity", "revenue"])
        .query("quantity > 0")
        .sort_values(["nm_id", "week"])
    )

    if work.empty:
        return pd.DataFrame(
            columns=["nm_id", "price_elasticity", "elasticity_observations"]
        )

    work["average_price"] = work["revenue"] / work["quantity"]
    group = work.groupby("nm_id", group_keys=False)
    work["price_change_pct"] = group["average_price"].pct_change(fill_method=None) * 100
    work["quantity_change_pct"] = group["quantity"].pct_change(fill_method=None) * 100

    work = work[work["price_change_pct"].abs() >= 1.0].copy()
    work["elasticity"] = work["quantity_change_pct"] / work["price_change_pct"]
    work = work.replace([np.inf, -np.inf], np.nan).dropna(subset=["elasticity"])
    work["elasticity"] = work["elasticity"].clip(-4.0, 4.0)

    result = (
        work.groupby("nm_id", as_index=False)
        .agg(
            raw_elasticity=("elasticity", "median"),
            elasticity_observations=("elasticity", "count"),
        )
    )

    result["price_elasticity"] = np.where(
        (result["elasticity_observations"] >= config.min_elasticity_observations)
        & (result["raw_elasticity"] < 0),
        result["raw_elasticity"].clip(-4.0, -0.05),
        np.nan,
    )

    return result[
        ["nm_id", "price_elasticity", "elasticity_observations"]
    ]


def _simulate(
    *,
    base_quantity: float,
    base_net_price: float,
    factor: float,
    elasticity: float,
    unit_cogs: float,
    commission_rate: float,
    other_wb_rate: float,
    marketing_fixed: float,
) -> dict[str, float]:
    if base_quantity <= 0 or base_net_price <= 0 or factor <= 0:
        return {"quantity": 0.0, "revenue": 0.0, "profit": 0.0}

    quantity = base_quantity * (factor ** elasticity)
    price = base_net_price * factor
    revenue = quantity * price
    profit = (
        revenue
        - quantity * unit_cogs
        - revenue * commission_rate
        - revenue * other_wb_rate
        - marketing_fixed
    )
    return {
        "quantity": float(quantity),
        "revenue": float(revenue),
        "profit": float(profit),
    }


def _add_price_scenarios(
    df: pd.DataFrame,
    config: OptimizerConfig = CONFIG,
) -> pd.DataFrame:
    work = df.copy()
    factors = np.linspace(
        config.min_price_factor,
        config.max_price_factor,
        config.price_steps,
    )

    suggested_price = []
    suggested_profit = []
    opportunity = []

    for row in work.to_dict("records"):
        current_gross = float(row.get("current_price_gross") or 0)
        base_net = float(row.get("average_price_30d") or 0)
        base_qty = float(row.get("quantity_30d") or 0)
        elasticity = row.get("price_elasticity")
        obs = int(row.get("elasticity_observations") or 0)
        current_profit = float(row.get("estimated_profit_30d") or 0)

        if (
            current_gross <= 0
            or base_net <= 0
            or base_qty <= 0
            or elasticity is None
            or pd.isna(elasticity)
            or obs < config.min_elasticity_observations
        ):
            suggested_price.append(current_gross)
            suggested_profit.append(current_profit)
            opportunity.append(0.0)
            continue

        best_factor = 1.0
        best_profit = current_profit

        for factor in factors:
            scenario = _simulate(
                base_quantity=base_qty,
                base_net_price=base_net,
                factor=float(factor),
                elasticity=float(elasticity),
                unit_cogs=float(row.get("average_cogs_man_30d") or 0),
                commission_rate=float(row.get("commission_rate_30d") or 0),
                other_wb_rate=float(row.get("other_wb_rate_30d") or 0),
                marketing_fixed=float(row.get("marketing_spend_30d") or 0),
            )
            if scenario["profit"] > best_profit:
                best_profit = scenario["profit"]
                best_factor = float(factor)

        suggested_price.append(current_gross * best_factor)
        suggested_profit.append(best_profit)
        opportunity.append(max(0.0, best_profit - current_profit))

    work["suggested_price"] = suggested_price
    work["suggested_profit_30d"] = suggested_profit
    work["profit_opportunity_30d"] = opportunity
    return work


def _add_recommendations(
    df: pd.DataFrame,
    config: OptimizerConfig = CONFIG,
) -> pd.DataFrame:
    work = df.copy()
    actions = []
    reasons = []
    priorities = []

    for row in work.to_dict("records"):
        stock_days = row.get("stock_days")
        margin = float(row.get("profit_margin_pct_30d") or 0)
        roas = row.get("roas_30d")
        qty30 = float(row.get("quantity_30d") or 0)
        stock = float(row.get("stock_on_hand") or 0)
        current_price = float(row.get("current_price_gross") or 0)
        suggested = float(row.get("suggested_price") or 0)
        opportunity = float(row.get("profit_opportunity_30d") or 0)
        obs = int(row.get("elasticity_observations") or 0)

        if pd.notna(stock_days) and stock_days <= config.stockout_days and qty30 > 0:
            actions.append("Пополнить остаток")
            reasons.append(
                f"Запаса примерно на {stock_days:.0f} дн.; есть риск потерять продажи из-за дефицита."
            )
            priorities.append("Критический")

        elif margin < 0:
            actions.append("Пересмотреть экономику")
            reasons.append(
                f"Оценочная прибыльность за 30 дней {margin:.1f}%. Проверьте цену, себестоимость и расходы WB."
            )
            priorities.append("Критический")

        elif pd.notna(stock_days) and stock_days >= config.excess_stock_days and stock > 0:
            actions.append("Снизить запас / ускорить продажи")
            reasons.append(
                f"Остатка примерно на {stock_days:.0f} дн.; товар замораживает оборотный капитал."
            )
            priorities.append("Высокий")

        elif (
            current_price > 0
            and suggested >= current_price * 1.05
            and obs >= config.min_elasticity_observations
            and opportunity > 0
        ):
            delta = (suggested / current_price - 1) * 100
            actions.append("Рассмотреть повышение цены")
            reasons.append(
                f"Симуляция даёт ориентир +{delta:.1f}% к цене и потенциал около {opportunity:,.0f} ₽ прибыли за 30 дней."
            )
            priorities.append("Высокий")

        elif (
            current_price > 0
            and suggested <= current_price * 0.95
            and obs >= config.min_elasticity_observations
            and opportunity > 0
        ):
            delta = (suggested / current_price - 1) * 100
            actions.append("Рассмотреть снижение цены")
            reasons.append(
                f"Историческая ценовая реакция даёт ориентир {delta:.1f}% к цене; рост объёма может увеличить прибыль."
            )
            priorities.append("Средний")

        elif (
            margin >= config.good_margin_pct
            and roas is not None
            and pd.notna(roas)
            and roas >= config.good_roas
            and (pd.isna(stock_days) or stock_days >= 45)
        ):
            actions.append("Тестировать усиление маркетинга")
            reasons.append(
                f"Прибыльность {margin:.1f}%, ROAS {roas:.2f}; запас позволяет проверить масштабирование."
            )
            priorities.append("Средний")

        elif qty30 <= 0 and stock > 0:
            actions.append("Проверить товар без продаж")
            reasons.append("Есть остаток, но за последние 30 дней продажи отсутствуют.")
            priorities.append("Высокий")

        else:
            actions.append("Оставить / наблюдать")
            reasons.append("Явного действия с высоким ожидаемым эффектом по текущим правилам не обнаружено.")
            priorities.append("Низкий")

    work["recommendation"] = actions
    work["recommendation_reason"] = reasons
    work["priority"] = priorities

    gain = work["profit_opportunity_30d"].fillna(0).clip(lower=0)
    gain_score = (
        (gain - gain.min()) / (gain.max() - gain.min()) * 50
        if gain.max() > gain.min()
        else pd.Series(0.0, index=work.index)
    )
    margin_score = work["profit_margin_pct_30d"].fillna(0).clip(0, 40) / 40 * 20
    demand = work["quantity_30d"].fillna(0).clip(lower=0)
    demand_score = (
        (demand - demand.min()) / (demand.max() - demand.min()) * 20
        if demand.max() > demand.min()
        else pd.Series(0.0, index=work.index)
    )
    urgency = work["priority"].map(
        {"Критический": 10, "Высокий": 8, "Средний": 5, "Низкий": 0}
    ).fillna(0)

    work["opportunity_score"] = (
        gain_score + margin_score + demand_score + urgency
    ).clip(0, 100).round(1)

    priority_order = {"Критический": 0, "Высокий": 1, "Средний": 2, "Низкий": 3}
    work["_priority"] = work["priority"].map(priority_order).fillna(9)
    return (
        work.sort_values(
            ["_priority", "opportunity_score", "profit_opportunity_30d"],
            ascending=[True, False, False],
        )
        .drop(columns="_priority")
        .reset_index(drop=True)
    )


def get_profit_optimizer_data(
    date_to: str | date | None = None,
    *,
    config: OptimizerConfig = CONFIG,
) -> pd.DataFrame:
    """
    Данные для таба "Оптимизация прибыли" на уровне NM_ID.

    ВАЖНО:
    - окончание периода берётся из date_to;
    - метрики считаются за 7/30/90 дней до date_to;
    - для proxy-эластичности используется до 180 дней истории;
    - остаток берётся на последнюю доступную дату <= date_to;
    - SKU-расходы WB учитываются только там, где расход можно
      связать с rrd_id и затем с NM_ID.

    Поэтому это decision-support модель, а не бухгалтерский P&L.
    """

    report_date = _as_date(date_to)
    history_start = report_date - timedelta(days=config.history_days - 1)

    with get_duckdb_conn_with_opt(ro=True) as con:
        con.execute(BASE_QUERY)
        con.execute(WB_COSTS_QUERY)

        summary = con.execute(
            """
            WITH
            usk_to_nm AS (
                SELECT usk, MAX(card_id) AS nm_id
                FROM inventories.usk
                WHERE usk IS NOT NULL AND card_id IS NOT NULL
                GROUP BY usk
            ),

            sales_product AS (
                SELECT
                    m.nm_id,

                    COUNT(*) FILTER (
                        WHERE t.date_from::DATE BETWEEN
                            $report_date::DATE - INTERVAL 6 DAY
                            AND $report_date::DATE
                    ) AS quantity_7d,

                    COUNT(*) FILTER (
                        WHERE t.date_from::DATE BETWEEN
                            $report_date::DATE - INTERVAL 29 DAY
                            AND $report_date::DATE
                    ) AS quantity_30d,

                    COUNT(*) FILTER (
                        WHERE t.date_from::DATE BETWEEN
                            $report_date::DATE - INTERVAL 59 DAY
                            AND $report_date::DATE - INTERVAL 30 DAY
                    ) AS quantity_prev_30d,

                    COUNT(*) FILTER (
                        WHERE t.date_from::DATE BETWEEN
                            $report_date::DATE - INTERVAL 89 DAY
                            AND $report_date::DATE
                    ) AS quantity_90d,

                    SUM(
                        COALESCE(t.cr_rev, 0) / 100.0
                        / (1 + COALESCE(t.vat_rate, 0) / 100.0)
                    ) FILTER (
                        WHERE t.date_from::DATE BETWEEN
                            $report_date::DATE - INTERVAL 29 DAY
                            AND $report_date::DATE
                    ) AS revenue_30d,

                    SUM(
                        COALESCE(t.cr_rev, 0) / 100.0
                        / (1 + COALESCE(t.vat_rate, 0) / 100.0)
                    ) FILTER (
                        WHERE t.date_from::DATE BETWEEN
                            $report_date::DATE - INTERVAL 89 DAY
                            AND $report_date::DATE
                    ) AS revenue_90d,

                    SUM(COALESCE(t.adjusted_cogs_man, 0) / 100.0) FILTER (
                        WHERE t.date_from::DATE BETWEEN
                            $report_date::DATE - INTERVAL 29 DAY
                            AND $report_date::DATE
                    ) AS cogs_man_30d,

                    SUM(COALESCE(t.net_comission, 0) / 100.0) FILTER (
                        WHERE t.date_from::DATE BETWEEN
                            $report_date::DATE - INTERVAL 29 DAY
                            AND $report_date::DATE
                    ) AS net_commission_30d

                FROM base t
                INNER JOIN usk_to_nm m ON m.usk = t.usk
                WHERE
                    t.oper = 'Списание'
                    AND t.date_from::DATE BETWEEN
                        $history_start::DATE AND $report_date::DATE
                GROUP BY m.nm_id
            ),

            rrd_nm AS (
                SELECT t.rrd_id, MAX(m.nm_id) AS nm_id
                FROM base t
                INNER JOIN usk_to_nm m ON m.usk = t.usk
                WHERE t.rrd_id IS NOT NULL
                GROUP BY t.rrd_id
            ),

            costs_product AS (
                SELECT
                    m.nm_id,

                    SUM(
                        (COALESCE(c.dt, 0) - COALESCE(c.cr, 0)) / 100.0
                        / (1 + COALESCE(c.vat_rate, 0) / 100.0)
                    ) FILTER (
                        WHERE c.date_from::DATE BETWEEN
                            $report_date::DATE - INTERVAL 29 DAY
                            AND $report_date::DATE
                    ) AS wb_costs_30d,

                    SUM(
                        CASE
                            WHEN c.account = 'WB Deduction'
                            THEN
                                (COALESCE(c.dt, 0) - COALESCE(c.cr, 0)) / 100.0
                                / (1 + COALESCE(c.vat_rate, 0) / 100.0)
                            ELSE 0
                        END
                    ) FILTER (
                        WHERE c.date_from::DATE BETWEEN
                            $report_date::DATE - INTERVAL 29 DAY
                            AND $report_date::DATE
                    ) AS marketing_costs_30d

                FROM wb_costs c
                INNER JOIN rrd_nm m ON m.rrd_id = c.rrd_id
                WHERE c.date_from::DATE BETWEEN
                    $history_start::DATE AND $report_date::DATE
                GROUP BY m.nm_id
            ),

            stock_date AS (
                SELECT MAX(date_from::DATE) AS report_stock_date
                FROM stocks.unpacked_stocks
                WHERE date_from::DATE <= $report_date::DATE
            ),

            stocks AS (
                SELECT
                    s.nm_id,
                    SUM(COALESCE(s.quantity, 0)) AS stock_on_hand,
                    SUM(
                        COALESCE(s.in_way_from_client, 0)
                        + COALESCE(s.in_way_to_client, 0)
                    ) AS stock_in_transit
                FROM stocks.unpacked_stocks s
                CROSS JOIN stock_date d
                WHERE s.date_from::DATE = d.report_stock_date
                GROUP BY s.nm_id
            ),

            current_price AS (
                SELECT
                    nm_id,
                    ARG_MAX(val, date_from) / 100.0 AS current_price_gross,
                    ARG_MAX(COALESCE(vat_rate, 0), date_from) AS current_vat_rate
                FROM sales.sales_long
                WHERE
                    field = 'retail_price'
                    AND oper = 'dt'
                    AND nm_id IS NOT NULL
                    AND date_from::DATE <= $report_date::DATE
                GROUP BY nm_id
            ),

            brands AS (
                SELECT nm_id, COALESCE(MAX(brand), 'Бренд не указан') AS brand
                FROM cards.unpacked_cards
                GROUP BY nm_id
            ),

            universe AS (
                SELECT nm_id FROM sales_product
                UNION
                SELECT nm_id FROM stocks
            )

            SELECT
                u.nm_id,
                COALESCE(b.brand, 'Бренд не указан') AS brand,
                COALESCE(p.subject_name, 'Категория не указана') AS subject_name,
                COALESCE(p.title, '') AS title,

                COALESCE(s.quantity_7d, 0) AS quantity_7d,
                COALESCE(s.quantity_30d, 0) AS quantity_30d,
                COALESCE(s.quantity_prev_30d, 0) AS quantity_prev_30d,
                COALESCE(s.quantity_90d, 0) AS quantity_90d,
                COALESCE(s.revenue_30d, 0) AS revenue_30d,
                COALESCE(s.revenue_90d, 0) AS revenue_90d,
                COALESCE(s.cogs_man_30d, 0) AS cogs_man_30d,
                COALESCE(s.net_commission_30d, 0) AS net_commission_30d,
                COALESCE(c.wb_costs_30d, 0) AS wb_costs_30d,
                COALESCE(c.marketing_costs_30d, 0) AS marketing_costs_30d,
                COALESCE(st.stock_on_hand, 0) AS stock_on_hand,
                COALESCE(st.stock_in_transit, 0) AS stock_in_transit,
                COALESCE(cp.current_price_gross, 0) AS current_price_gross,
                COALESCE(cp.current_vat_rate, 0) AS current_vat_rate

            FROM universe u
            LEFT JOIN sales_product s ON s.nm_id = u.nm_id
            LEFT JOIN costs_product c ON c.nm_id = u.nm_id
            LEFT JOIN stocks st ON st.nm_id = u.nm_id
            LEFT JOIN current_price cp ON cp.nm_id = u.nm_id
            LEFT JOIN cards.product p ON p.nm_id = u.nm_id
            LEFT JOIN brands b ON b.nm_id = u.nm_id
            """,
            {
                "report_date": report_date,
                "history_start": history_start,
            },
        ).df()

        weekly = con.execute(
            """
            WITH usk_to_nm AS (
                SELECT usk, MAX(card_id) AS nm_id
                FROM inventories.usk
                WHERE usk IS NOT NULL AND card_id IS NOT NULL
                GROUP BY usk
            )
            SELECT
                m.nm_id,
                DATE_TRUNC('week', t.date_from::DATE)::DATE AS week,
                COUNT(*) AS quantity,
                SUM(
                    COALESCE(t.cr_rev, 0) / 100.0
                    / (1 + COALESCE(t.vat_rate, 0) / 100.0)
                ) AS revenue
            FROM base t
            INNER JOIN usk_to_nm m ON m.usk = t.usk
            WHERE
                t.oper = 'Списание'
                AND t.date_from::DATE BETWEEN
                    $history_start::DATE AND $report_date::DATE
            GROUP BY m.nm_id, week
            ORDER BY m.nm_id, week
            """,
            {
                "report_date": report_date,
                "history_start": history_start,
            },
        ).df()

    if summary.empty:
        return summary

    numeric = [
        "nm_id",
        "quantity_7d",
        "quantity_30d",
        "quantity_prev_30d",
        "quantity_90d",
        "revenue_30d",
        "revenue_90d",
        "cogs_man_30d",
        "net_commission_30d",
        "wb_costs_30d",
        "marketing_costs_30d",
        "stock_on_hand",
        "stock_in_transit",
        "current_price_gross",
        "current_vat_rate",
    ]
    for col in numeric:
        summary[col] = pd.to_numeric(summary[col], errors="coerce").fillna(0)

    summary["average_price_30d"] = _safe_div(
        summary["revenue_30d"], summary["quantity_30d"]
    )
    summary["average_cogs_man_30d"] = _safe_div(
        summary["cogs_man_30d"], summary["quantity_30d"]
    )

    summary["commission_cost_30d"] = summary["net_commission_30d"].abs()
    summary["wb_costs_abs_30d"] = summary["wb_costs_30d"].abs()
    summary["marketing_spend_30d"] = summary["marketing_costs_30d"].abs()
    summary["other_wb_costs_30d"] = (
        summary["wb_costs_abs_30d"] - summary["marketing_spend_30d"]
    ).clip(lower=0)

    summary["commission_rate_30d"] = _safe_div(
        summary["commission_cost_30d"], summary["revenue_30d"]
    ).fillna(0)
    summary["other_wb_rate_30d"] = _safe_div(
        summary["other_wb_costs_30d"], summary["revenue_30d"]
    ).fillna(0)

    summary["estimated_profit_30d"] = (
        summary["revenue_30d"]
        - summary["cogs_man_30d"]
        - summary["commission_cost_30d"]
        - summary["wb_costs_abs_30d"]
    )
    summary["profit_margin_pct_30d"] = (
        _safe_div(summary["estimated_profit_30d"], summary["revenue_30d"]) * 100
    )
    summary["roas_30d"] = _safe_div(
        summary["revenue_30d"], summary["marketing_spend_30d"]
    )
    summary["sales_growth_30d_pct"] = (
        (_safe_div(summary["quantity_30d"], summary["quantity_prev_30d"]) - 1)
        * 100
    )
    summary["stock_days"] = np.where(
        summary["quantity_7d"] > 0,
        summary["stock_on_hand"] * 7.0 / summary["quantity_7d"],
        np.nan,
    )

    elasticity = _estimate_elasticity(weekly, config)
    summary = summary.merge(elasticity, on="nm_id", how="left")
    summary["elasticity_observations"] = (
        summary["elasticity_observations"].fillna(0).astype(int)
    )

    summary = _add_price_scenarios(summary, config)
    summary = _add_recommendations(summary, config)
    return summary


def simulate_product_price(
    product: dict[str, Any],
    new_gross_price: float,
) -> dict[str, float | str]:
    current = float(product.get("current_price_gross") or 0)
    base_net = float(product.get("average_price_30d") or 0)
    base_qty = float(product.get("quantity_30d") or 0)
    elasticity = product.get("price_elasticity")
    obs = int(product.get("elasticity_observations") or 0)

    if current <= 0 or base_net <= 0 or base_qty <= 0 or new_gross_price <= 0:
        return {
            "status": "Недостаточно данных для симуляции",
            "quantity": 0.0,
            "revenue": 0.0,
            "profit": 0.0,
            "profit_change": 0.0,
            "profit_change_pct": 0.0,
        }

    if elasticity is None or pd.isna(elasticity) or obs < CONFIG.min_elasticity_observations:
        return {
            "status": "Недостаточно истории изменения цены для надёжной симуляции",
            "quantity": base_qty,
            "revenue": float(product.get("revenue_30d") or 0),
            "profit": float(product.get("estimated_profit_30d") or 0),
            "profit_change": 0.0,
            "profit_change_pct": 0.0,
        }

    factor = new_gross_price / current
    scenario = _simulate(
        base_quantity=base_qty,
        base_net_price=base_net,
        factor=factor,
        elasticity=float(elasticity),
        unit_cogs=float(product.get("average_cogs_man_30d") or 0),
        commission_rate=float(product.get("commission_rate_30d") or 0),
        other_wb_rate=float(product.get("other_wb_rate_30d") or 0),
        marketing_fixed=float(product.get("marketing_spend_30d") or 0),
    )

    current_profit = float(product.get("estimated_profit_30d") or 0)
    delta = scenario["profit"] - current_profit
    delta_pct = delta / abs(current_profit) * 100 if current_profit else 0.0

    return {
        "status": "Расчёт выполнен",
        **scenario,
        "profit_change": delta,
        "profit_change_pct": delta_pct,
    }
