# gear/app/daily_sales/daily_brief/presentation/pages/stocks_health.py
from __future__ import annotations

from ...helpers import (
    fmt_money,
    fmt_number,
    fmt_pct,
    number,
)
from ..components import safe


# =============================================================================
# ФОРМАТИРОВАНИЕ
# =============================================================================


def _fmt_compact_qty(
    value,
) -> str:
    value = number(
        value
    )

    if abs(value) >= 1_000_000:
        return (
            f"{value / 1_000_000:.1f}"
            .replace(".", ",")
            + " млн шт"
        )

    if abs(value) >= 1_000:
        return (
            f"{value / 1_000:.1f}"
            .replace(".", ",")
            + " тыс. шт"
        )

    return (
        f"{fmt_number(value)} шт"
    )


def _fmt_compact_money(
    value,
) -> str:
    value = number(
        value
    )

    if abs(value) >= 1_000_000_000:
        return (
            f"{value / 1_000_000_000:.1f}"
            .replace(".", ",")
            + " млрд ₽"
        )

    if abs(value) >= 1_000_000:
        return (
            f"{value / 1_000_000:.1f}"
            .replace(".", ",")
            + " млн ₽"
        )

    if abs(value) >= 1_000:
        return (
            f"{value / 1_000:.1f}"
            .replace(".", ",")
            + " тыс. ₽"
        )

    return fmt_money(
        value
    )


def _fmt_months(
    value,
) -> str:
    if value is None:
        return "—"

    value = number(
        value
    )

    return (
        f"{value:.1f}"
        .replace(".", ",")
        + " мес."
    )


# =============================================================================
# SEGMENTED BAR
# =============================================================================


def _coverage_bar(
    buckets: list[dict],
) -> str:
    if not buckets:
        return ""

    segments = []

    for bucket in buckets:
        key = safe(
            bucket.get(
                "key",
                "",
            )
        )

        share = max(
            0,
            number(
                bucket.get(
                    "share_pct"
                )
            ),
        )

        if share <= 0:
            continue

        segments.append(
            f"""
            <div
                class="
                    stocks-health-segment
                    stocks-health-segment-{key}
                "
                style="width:{share:.4f}%"
            ></div>
            """
        )

    return f"""
    <div class="stocks-health-bar">
        {''.join(segments)}
    </div>
    """


# =============================================================================
# ЛЕГЕНДА КОРЗИН
# =============================================================================


def _coverage_buckets(
    buckets: list[dict],
) -> str:
    if not buckets:
        return ""

    cards = []

    for bucket in buckets:
        key = safe(
            bucket.get(
                "key",
                "",
            )
        )

        label = safe(
            bucket.get(
                "label",
                "",
            )
        )

        share = number(
            bucket.get(
                "share_pct"
            )
        )

        qty = number(
            bucket.get(
                "qty"
            )
        )

        cards.append(
            f"""
            <div class="
                stocks-health-bucket
                stocks-health-bucket-{key}
            ">

                <div class="stocks-health-bucket-top">

                    <span class="stocks-health-dot"></span>

                    <span class="stocks-health-bucket-label">
                        {label}
                    </span>

                </div>

                <div class="stocks-health-bucket-share">
                    {fmt_pct(share)}
                </div>

                <div class="stocks-health-bucket-qty">
                    {_fmt_compact_qty(qty)}
                </div>

            </div>
            """
        )

    return f"""
    <div class="stocks-health-buckets">
        {''.join(cards)}
    </div>
    """


# =============================================================================
# KPI ПОКРЫТИЯ
# =============================================================================


def _coverage_metrics(
    health: dict,
) -> str:
    total_qty = number(
        health.get(
            "total_qty"
        )
    )

    sales_qty_30d = number(
        health.get(
            "sales_qty_30d"
        )
    )

    coverage_months = health.get(
        "coverage_months"
    )

    active_coverage_months = (
        health.get(
            "active_coverage_months"
        )
    )

    risk_share = number(
        health.get(
            "risk_share_pct"
        )
    )

    risk_qty = number(
        health.get(
            "risk_qty"
        )
    )

    risk_value = number(
        health.get(
            "risk_management_value"
        )
    )

    return f"""
    <div class="stocks-health-metrics">

        <div class="stocks-health-metric">

            <div class="stocks-health-metric-label">
                Общий запас
            </div>

            <div class="stocks-health-metric-value">
                {_fmt_compact_qty(total_qty)}
            </div>

            <div class="stocks-health-metric-note">
                весь товарный контур
            </div>

        </div>


        <div class="stocks-health-metric">

            <div class="stocks-health-metric-label">
                Темп продаж
            </div>

            <div class="stocks-health-metric-value">
                {_fmt_compact_qty(sales_qty_30d)}
            </div>

            <div class="stocks-health-metric-note">
                чистые продажи за 30 дней
            </div>

        </div>


        <div class="
            stocks-health-metric
            stocks-health-metric-accent
        ">

            <div class="stocks-health-metric-label">
                Покрытие запасом
            </div>

            <div class="stocks-health-metric-value">
                {_fmt_months(coverage_months)}
            </div>

            <div class="stocks-health-metric-note">
                при текущем темпе продаж
            </div>

        </div>


        <div class="
            stocks-health-metric
            stocks-health-metric-active
        ">

            <div class="stocks-health-metric-label">
                Активное покрытие
            </div>

            <div class="stocks-health-metric-value">
                {_fmt_months(active_coverage_months)}
            </div>

            <div class="stocks-health-metric-note">
                только позиции с продажами
            </div>

        </div>


        <div class="
            stocks-health-metric
            stocks-health-metric-risk
        ">

            <div class="stocks-health-metric-label">
                Зона риска
            </div>

            <div class="stocks-health-risk-line">

                <div class="stocks-health-metric-value">
                    {fmt_pct(risk_share)}
                </div>

                <div class="stocks-health-risk-qty">
                    {_fmt_compact_qty(risk_qty)}
                </div>

            </div>

            <div class="stocks-health-metric-note">
                {_fmt_compact_money(risk_value)}
                · по упр. себестоимости
            </div>

        </div>

    </div>
    """


# =============================================================================
# ДЕТАЛИ РИСКА
# =============================================================================


def _risk_details(
    health: dict,
) -> str:
    slow_qty = number(
        health.get(
            "slow_qty"
        )
    )

    slow_share = number(
        health.get(
            "slow_share_pct"
        )
    )

    no_sales_qty = number(
        health.get(
            "no_sales_qty"
        )
    )

    no_sales_share = number(
        health.get(
            "no_sales_share_pct"
        )
    )

    return f"""
    <div class="stocks-health-risk-details">

        <div class="stocks-health-risk-item">

            <div class="stocks-health-risk-item-label">
                Медленный запас
            </div>

            <div class="stocks-health-risk-item-main">
                {_fmt_compact_qty(slow_qty)}
                <span>
                    {fmt_pct(slow_share)}
                </span>
            </div>

            <div class="stocks-health-risk-item-note">
                покрытие более 90 дней
            </div>

        </div>


        <div class="stocks-health-risk-divider"></div>


        <div class="stocks-health-risk-item">

            <div class="stocks-health-risk-item-label">
                Без продаж
            </div>

            <div class="stocks-health-risk-item-main">
                {_fmt_compact_qty(no_sales_qty)}
                <span>
                    {fmt_pct(no_sales_share)}
                </span>
            </div>

            <div class="stocks-health-risk-item-note">
                чистых продаж за последние 30 дней нет
            </div>

        </div>

    </div>
    """


# =============================================================================
# ПОЛНЫЙ БЛОК
# =============================================================================


def build_stock_health(
    data: dict,
) -> str:
    """
    Блок здоровья товарного запаса.

    На вход получает ВЕСЬ stocks payload.
    Сам забирает data["health"].
    """

    health = (
        data.get("health")
        or {}
    )

    # ================================================================
    # НИКОГДА НЕ ВОЗВРАЩАЕМ ПУСТУЮ СТРОКУ
    # ================================================================

    if not health:
        return """
        <section
            class="stocks-health"
            style="
                margin-top:8px;
                padding:10px;
                border-top:4px solid #14213D;
                background:#FFF8F8;
            "
        >
            <div
                style="
                    color:#E85D75;
                    font-size:7px;
                    font-weight:800;
                    letter-spacing:1px;
                "
            >
                ЗДОРОВЬЕ ТОВАРНОГО ЗАПАСА
            </div>

            <div
                style="
                    margin-top:4px;
                    color:#14213D;
                    font-family:Georgia,serif;
                    font-size:15px;
                    font-weight:700;
                "
            >
                Данные для расчёта не переданы
            </div>
        </section>
        """

    if not health.get("available"):
        reason = safe(
            health.get("reason")
            or "Расчёт здоровья запаса недоступен"
        )

        return f"""
        <section
            class="stocks-health"
            style="
                margin-top:8px;
                padding:10px;
                border-top:4px solid #14213D;
                background:#FFF8F8;
            "
        >
            <div
                style="
                    color:#E85D75;
                    font-size:7px;
                    font-weight:800;
                    letter-spacing:1px;
                "
            >
                ЗДОРОВЬЕ ТОВАРНОГО ЗАПАСА
            </div>

            <div
                style="
                    margin-top:4px;
                    color:#14213D;
                    font-family:Georgia,serif;
                    font-size:15px;
                    font-weight:700;
                "
            >
                Расчёт недоступен
            </div>

            <div
                style="
                    margin-top:4px;
                    color:#667085;
                    font-size:7px;
                "
            >
                {reason}
            </div>
        </section>
        """

    buckets = (
        health.get("buckets")
        or []
    )

    return f"""
    <section class="stocks-health">

        <div class="stocks-health-head">

            <div>

                <div class="stocks-health-kicker">
                    ЗДОРОВЬЕ ТОВАРНОГО ЗАПАСА
                </div>

                <div class="stocks-health-title">
                    Покрытие текущего спроса
                </div>

            </div>

            <div class="stocks-health-period">
                темп продаж · последние 30 дней
            </div>

        </div>


        {_coverage_bar(
            buckets
        )}


        {_coverage_buckets(
            buckets
        )}


        {_coverage_metrics(
            health
        )}


        {_risk_details(
            health
        )}

    </section>
    """