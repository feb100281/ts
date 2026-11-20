# gear/app/daily_sales/daily_brief/presentation/pages/sales_dynamics_page.py

from __future__ import annotations

import pandas as pd

from ...helpers import fmt_money, number
from ..components import safe
from .demand_charts import (
    demand_price_index_chart,
    monthly_drivers_chart,
)


TITLE = "Коммерческий обзор · динамика продаж"
SUBTITLE = "ОБЪЁМ · СРЕДНЯЯ ЦЕНА · ТОВАРНЫЙ МИКС · ВЫРУЧКА"


# =============================================================================
# ЛОКАЛЬНЫЕ СТИЛИ СТРАНИЦЫ
# =============================================================================

SALES_DYNAMICS_CSS = r"""
<style>

/* ======================================================================
   SALES DYNAMICS PAGE
   ====================================================================== */

.sales-dynamics-page {
    --sd-navy: #14213D;
    --sd-muted: #667085;
    --sd-border: #D7DCE2;
    --sd-grid: #E8EBEF;

    --sd-coral: #E85D75;
    --sd-coral-soft: #FFF1F4;

    --sd-green: #16805E;
    --sd-green-soft: #E9F5EF;

    --sd-yellow: #E9B949;
    --sd-yellow-soft: #FFF8DF;

    --sd-blue: #4E78A8;
    --sd-blue-soft: #EDF3F9;

    color: var(--sd-navy);
}


/* ======================================================================
   KPI
   ====================================================================== */

.sd-kpi-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 7px;
    margin-bottom: 8px;
}

.sd-kpi {
    min-height: 69px;
    padding: 8px 9px;

    border: 1px solid var(--sd-border);
    border-top: 3px solid var(--sd-navy);
    background: #FFFDF7;
}

.sd-kpi.qty {
    border-top-color: var(--sd-green);
}

.sd-kpi.price {
    border-top-color: var(--sd-coral);
}

.sd-kpi.revenue {
    border-top-color: var(--sd-blue);
}

.sd-kpi.mix {
    border-top-color: var(--sd-yellow);
}

.sd-kpi-label {
    min-height: 15px;

    color: var(--sd-muted);

    font-size: 6.8px;
    line-height: 1.15;
    font-weight: 800;
    letter-spacing: .65px;
    text-transform: uppercase;
}

.sd-kpi-value {
    margin-top: 5px;

    font-family: Georgia, "Times New Roman", serif;
    font-size: 17px;
    line-height: 1;
    font-weight: 800;
    white-space: nowrap;
}

.sd-kpi-bottom {
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    gap: 6px;

    margin-top: 6px;

    color: var(--sd-muted);
    font-size: 6.4px;
    line-height: 1.15;
}

.sd-change {
    flex-shrink: 0;
    font-weight: 800;
    white-space: nowrap;
}

.sd-change.up {
    color: var(--sd-green);
}

.sd-change.down {
    color: #BD3D59;
}

.sd-change.neutral {
    color: var(--sd-muted);
}


/* ======================================================================
   COMMON
   ====================================================================== */

.sd-kicker {
    color: var(--sd-coral);

    font-size: 6.6px;
    line-height: 1;
    font-weight: 800;
    letter-spacing: 1px;
    text-transform: uppercase;
}

.sd-title {
    margin-top: 3px;

    font-family: Georgia, "Times New Roman", serif;
    font-size: 16px;
    line-height: 1.05;
    font-weight: 800;
}

.sd-title.small {
    font-size: 14px;
}

.sd-subtitle {
    margin-top: 3px;
    color: var(--sd-muted);

    font-size: 6.7px;
    line-height: 1.25;
}

.sd-block-head {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 10px;

    margin-bottom: 5px;
}

.sd-caption {
    color: var(--sd-muted);

    font-size: 6.2px;
    line-height: 1.25;
    text-align: right;
}


/* ======================================================================
   ГЛАВНЫЙ ВЫВОД
   ====================================================================== */

.sd-story {
    display: grid;
    grid-template-columns: .88fr 1.62fr;
    gap: 8px;

    margin-bottom: 8px;
}

.sd-editorial {
    min-height: 154px;
    padding: 10px 11px;

    background: var(--sd-coral-soft);
    border-left: 5px solid var(--sd-coral);
}

.sd-editorial.positive {
    background: var(--sd-green-soft);
    border-left-color: var(--sd-green);
}

.sd-editorial.warning {
    background: var(--sd-yellow-soft);
    border-left-color: var(--sd-yellow);
}

.sd-editorial.neutral {
    background: #F4F0E6;
    border-left-color: var(--sd-navy);
}

.sd-editorial-title {
    margin-top: 6px;

    font-family: Georgia, "Times New Roman", serif;
    font-size: 18px;
    line-height: 1.05;
    font-weight: 800;
}

.sd-editorial-copy {
    margin-top: 8px;

    color: #354052;

    font-family: Georgia, "Times New Roman", serif;
    font-size: 8.7px;
    line-height: 1.46;
    text-align: justify;
    hyphens: auto;
}

.sd-driver-strip {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 5px;

    margin-top: 10px;
}

.sd-driver {
    padding: 6px 7px;

    background: rgba(255, 255, 255, .56);
    border-top: 2px solid rgba(20, 33, 61, .20);
}

.sd-driver span {
    display: block;

    color: var(--sd-muted);
    font-size: 5.7px;
    line-height: 1.1;
    text-transform: uppercase;
}

.sd-driver b {
    display: block;
    margin-top: 3px;

    font-family: Georgia, serif;
    font-size: 11px;
    line-height: 1;
}

.sd-driver b.positive {
    color: var(--sd-green);
}

.sd-driver b.negative {
    color: #BD3D59;
}


/* ======================================================================
   MONTHLY
   ====================================================================== */

.sd-monthly {
    min-height: 154px;
    padding: 8px 9px 5px;

    border-top: 3px solid var(--sd-navy);
    border-bottom: 1px solid var(--sd-border);
}

.sd-monthly-chart svg {
    display: block;
    width: 100%;
    height: 119px;
}


/* ======================================================================
   90 DAYS
   ====================================================================== */

.sd-regime {
    margin-bottom: 8px;
    padding: 7px 9px 5px;

    border-top: 3px solid var(--sd-navy);
    border-bottom: 1px solid var(--sd-border);

    break-inside: avoid;
}

.sd-regime-chart svg {
    display: block;
    width: 100%;
    height: 184px;
}

.sd-chart-note {
    margin-top: 2px;

    color: var(--sd-muted);

    font-size: 5.9px;
    line-height: 1.3;
}


/* ======================================================================
   14 DAYS DETAIL
   ====================================================================== */

.sd-period-section {
    margin-bottom: 8px;
    padding-top: 6px;

    border-top: 3px solid var(--sd-navy);
}

.sd-period-grid {
    display: grid;
    grid-template-columns: 1.05fr 1fr 1fr;
    gap: 7px;

    margin-top: 6px;
}

.sd-period-card {
    padding: 8px 9px;

    border: 1px solid var(--sd-border);
    background: #FFFDF7;
}

.sd-period-card.primary {
    background: #F8FAFC;
    border-top: 3px solid var(--sd-navy);
}

.sd-period-label {
    color: var(--sd-muted);

    font-size: 6px;
    font-weight: 800;
    letter-spacing: .6px;
    text-transform: uppercase;
}

.sd-period-value {
    margin-top: 5px;

    font-family: Georgia, serif;
    font-size: 15px;
    line-height: 1;
    font-weight: 800;
}

.sd-period-copy {
    margin-top: 6px;

    color: #4B5563;
    font-size: 6.6px;
    line-height: 1.35;
}


/* ======================================================================
   METHODOLOGY
   ====================================================================== */

.sd-methodology {
    padding: 7px 8px;

    border-top: 3px solid var(--sd-yellow);
    background: #F8F5ED;
}

.sd-methodology-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 9px;

    margin-top: 5px;
}

.sd-methodology-grid > div {
    color: #4B5563;
    font-size: 6.3px;
    line-height: 1.35;
}

.sd-methodology-grid b {
    display: block;
    margin-bottom: 2px;

    color: var(--sd-navy);
    font-size: 6.6px;
}


/* ======================================================================
   FOOTER
   ====================================================================== */

.sd-footer {
    display: flex;
    justify-content: space-between;

    margin-top: 5px;

    color: #7A8492;
    font-size: 5.7px;
}

</style>
"""


# =============================================================================
# FORMATTERS
# =============================================================================

def _money_short(value) -> str:
    value = number(value)
    sign = "−" if value < 0 else ""
    absolute = abs(value)

    if absolute >= 1_000_000_000:
        return (
            f"{sign}{absolute / 1_000_000_000:.1f}"
            .replace(".", ",")
            + "\u00A0млрд\u00A0₽"
        )

    if absolute >= 1_000_000:
        return (
            f"{sign}{absolute / 1_000_000:.1f}"
            .replace(".", ",")
            + "\u00A0млн\u00A0₽"
        )

    if absolute >= 1_000:
        return (
            f"{sign}{absolute / 1_000:.1f}"
            .replace(".", ",")
            + "\u00A0тыс.\u00A0₽"
        )

    return fmt_money(value)


def _number(value) -> str:
    return (
        f"{number(value):,.0f}"
        .replace(",", " ")
    )


def _pct(
    value,
    *,
    signed: bool = False,
) -> str:
    value = number(value)

    if signed:
        sign = (
            "+"
            if value > 0
            else "−"
            if value < 0
            else ""
        )
    else:
        sign = "−" if value < 0 else ""

    return (
        f"{sign}{abs(value):.1f}%"
        .replace(".", ",")
    )


def _change(
    current,
    previous,
) -> float | None:
    current = number(current)
    previous = number(previous)

    if previous == 0:
        return None

    return (
        current
        / previous
        - 1
    ) * 100


def _change_html(
    value,
) -> str:
    if value is None:
        return (
            '<span class="sd-change neutral">'
            "нет базы"
            "</span>"
        )

    value = number(value)

    css = (
        "up"
        if value > 0
        else "down"
        if value < 0
        else "neutral"
    )

    arrow = (
        "▲"
        if value > 0
        else "▼"
        if value < 0
        else "•"
    )

    return (
        f'<span class="sd-change {css}">'
        f"{arrow} {_pct(abs(value))}"
        "</span>"
    )


# =============================================================================
# DATA
# =============================================================================

def _daily_frame(
    payload: dict,
) -> pd.DataFrame:
    rows = (
        payload
        .get("sales", {})
        .get("daily_price_rows", [])
    )

    frame = pd.DataFrame(
        rows or []
    )

    if frame.empty:
        return frame

    if "date_from" not in frame:
        frame["date_from"] = None

    frame["date_from"] = pd.to_datetime(
        frame["date_from"],
        errors="coerce",
    )

    for column in (
        "sales_qty",
        "avg_price",
        "net_amount",
    ):
        if column not in frame:
            frame[column] = 0

        frame[column] = (
            pd.to_numeric(
                frame[column],
                errors="coerce",
            )
            .fillna(0)
        )

    return (
        frame
        .dropna(
            subset=["date_from"]
        )
        .sort_values("date_from")
        .reset_index(drop=True)
    )


def _period_metrics(
    frame: pd.DataFrame,
    start: int,
    end: int | None = None,
) -> dict:
    if frame.empty:
        return {
            "sales_qty": 0,
            "avg_price": 0,
            "net_amount": 0,
            "days": 0,
        }

    subset = frame.iloc[
        start:end
    ].copy()

    if subset.empty:
        return {
            "sales_qty": 0,
            "avg_price": 0,
            "net_amount": 0,
            "days": 0,
        }

    sales_qty = number(
        subset["sales_qty"].sum()
    )

    weighted_price_total = number(
        (
            subset["sales_qty"]
            * subset["avg_price"]
        ).sum()
    )

    avg_price = (
        weighted_price_total
        / sales_qty
        if sales_qty
        else 0
    )

    return {
        "sales_qty": sales_qty,
        "avg_price": avg_price,
        "net_amount": number(
            subset["net_amount"].sum()
        ),
        "days": len(subset),
    }


def _signal(
    payload: dict,
) -> dict:
    frame = _daily_frame(
        payload
    )

    if frame.empty:
        return {}

    recent_count = min(
        14,
        len(frame),
    )

    recent = _period_metrics(
        frame,
        -recent_count,
        None,
    )

    if len(frame) > recent_count:
        previous_count = min(
            14,
            len(frame) - recent_count,
        )

        previous = _period_metrics(
            frame,
            -(recent_count + previous_count),
            -recent_count,
        )
    else:
        previous = {}

    return {
        "recent": recent,
        "previous": previous,

        "qty_change_pct": _change(
            recent.get("sales_qty"),
            previous.get("sales_qty"),
        ),

        "price_change_pct": _change(
            recent.get("avg_price"),
            previous.get("avg_price"),
        ),

        "revenue_change_pct": _change(
            recent.get("net_amount"),
            previous.get("net_amount"),
        ),
    }


# =============================================================================
# HEADER
# =============================================================================

def _masthead(
    payload: dict,
) -> str:
    return f"""
    <header class="masthead">
        <div>
            <div class="brandline">
                ТРЕНДСЕТТЕР · ДРАЙВЕРЫ ПРОДАЖ
            </div>

            <h1>{TITLE}</h1>

            <div class="mast-subtitle">
                {SUBTITLE}
            </div>
        </div>

        <div class="issue-meta">
            Выпуск за
            <b>{safe(payload.get("report_date"))}</b>
            <br>
            Сформирован автоматически
        </div>
    </header>
    """


# =============================================================================
# KPI
# =============================================================================

def _kpi_card(
    label: str,
    value: str,
    note: str,
    change,
    tone: str,
) -> str:
    return f"""
    <article class="sd-kpi {safe(tone)}">
        <div class="sd-kpi-label">
            {safe(label)}
        </div>

        <div class="sd-kpi-value">
            {safe(value)}
        </div>

        <div class="sd-kpi-bottom">
            <span>{safe(note)}</span>
            {_change_html(change)}
        </div>
    </article>
    """


def _kpi_row(
    payload: dict,
    signal: dict,
) -> str:
    recent = (
        signal.get("recent", {})
    )

    kpi = (
        payload
        .get("sales", {})
        .get("kpi", {})
    )

    return f"""
    <div class="sd-kpi-grid">

        {_kpi_card(
            "Продано · 14 дней",
            _number(recent.get("sales_qty")) + " ед.",
            "положительные продажи",
            signal.get("qty_change_pct"),
            "qty",
        )}

        {_kpi_card(
            "Средняя цена · 14 дней",
            _money_short(recent.get("avg_price")),
            "взвешена количеством",
            signal.get("price_change_pct"),
            "price",
        )}

        {_kpi_card(
            "Чистая выручка · 14 дней",
            _money_short(recent.get("net_amount")),
            "с ретро-корректировками",
            signal.get("revenue_change_pct"),
            "revenue",
        )}

        {_kpi_card(
            "Последний закрытый день",
            _number(kpi.get("sales_transactions")) + " продаж",
            (
                "средняя цена "
                + _money_short(
                    kpi.get("avg_price")
                )
            ),
            kpi.get("revenue_change_pct"),
            "mix",
        )}

    </div>
    """


# =============================================================================
# EDITORIAL
# =============================================================================

def _editorial_data(
    signal: dict,
) -> dict:
    qty_change = signal.get(
        "qty_change_pct"
    )

    price_change = signal.get(
        "price_change_pct"
    )

    revenue_change = signal.get(
        "revenue_change_pct"
    )

    qty = number(qty_change)
    price = number(price_change)
    revenue = number(revenue_change)

    if (
        qty_change is None
        or price_change is None
    ):
        title = (
            "Недостаточно базы для "
            "сопоставления двух периодов"
        )

        copy = (
            "История продаж построена, "
            "но для корректного сравнения "
            "последних двух 14-дневных "
            "периодов пока недостаточно данных."
        )

        tone = "neutral"

    elif qty < -5 and price > 3:
        title = (
            "Продано меньше единиц "
            "при более высокой средней цене"
        )

        copy = (
            f"За последние 14 дней количество "
            f"положительных продаж снизилось "
            f"на {_pct(abs(qty))}, тогда как "
            f"средняя цена проданной единицы выросла "
            f"на {_pct(price)}. Рост средней цены "
            f"частично компенсирует снижение объёма, "
            f"но не означает сам по себе сокращение "
            f"рыночного спроса: на количество также "
            f"влияют наличие и товарный микс."
        )

        tone = "warning"

    elif qty > 5 and price < -3:
        title = (
            "Объём продаж вырос "
            "на фоне более низкой средней цены"
        )

        copy = (
            f"Количество продаж выросло "
            f"на {_pct(qty)}, при этом средняя цена "
            f"снизилась на {_pct(abs(price))}. "
            f"Выручка в таком режиме в большей степени "
            f"зависит от прироста физического объёма."
        )

        tone = "positive"

    elif qty > 5 and price > 3:
        title = (
            "Количество и средняя цена "
            "растут одновременно"
        )

        copy = (
            f"За последние 14 дней компания продала "
            f"больше единиц и одновременно получила "
            f"более высокую среднюю цену. Количество "
            f"выросло на {_pct(qty)}, цена — "
            f"на {_pct(price)}. Это наиболее сильное "
            f"сочетание двух основных драйверов выручки."
        )

        tone = "positive"

    elif qty < -5 and price < -3:
        title = (
            "Снизились оба основных "
            "драйвера выручки"
        )

        copy = (
            f"Количество продаж "
            f"снизилось на {_pct(abs(qty))}, "
            f"средняя цена — на {_pct(abs(price))}. "
            f"Такой режим требует отдельной проверки "
            f"наличия, товарного микса и промоактивности."
        )

        tone = "warning"

    else:
        title = (
            "Структура продаж остаётся "
            "относительно стабильной"
        )

        copy = (
            "За последние две недели нет одновременного "
            "резкого изменения количества проданных "
            "единиц и средней цены."
        )

        tone = "neutral"

    if revenue_change is not None:
        if revenue > 0:
            copy += (
                f" Чистая выручка к предыдущему "
                f"14-дневному периоду выросла "
                f"на {_pct(revenue)}."
            )
        elif revenue < 0:
            copy += (
                f" Чистая выручка к предыдущему "
                f"14-дневному периоду снизилась "
                f"на {_pct(abs(revenue))}."
            )
        else:
            copy += (
                " Чистая выручка осталась "
                "примерно на прежнем уровне."
            )

    return {
        "title": title,
        "copy": copy,
        "tone": tone,
    }


def _editorial_block(
    signal: dict,
) -> str:
    data = _editorial_data(
        signal
    )

    return f"""
    <section class="sd-editorial {safe(data.get('tone'))}">
        <div class="sd-kicker">
            ГЛАВНЫЙ ВЫВОД
        </div>

        <div class="sd-editorial-title">
            {safe(data.get("title"))}
        </div>

        <div class="sd-editorial-copy">
            {safe(data.get("copy"))}
        </div>

        <div class="sd-driver-strip">

            <div class="sd-driver">
                <span>Количество</span>
                <b class="{
                    'positive'
                    if number(signal.get('qty_change_pct')) > 0
                    else 'negative'
                    if number(signal.get('qty_change_pct')) < 0
                    else ''
                }">
                    {_pct(
                        signal.get("qty_change_pct"),
                        signed=True,
                    )}
                </b>
            </div>

            <div class="sd-driver">
                <span>Средняя цена</span>
                <b class="{
                    'positive'
                    if number(signal.get('price_change_pct')) > 0
                    else 'negative'
                    if number(signal.get('price_change_pct')) < 0
                    else ''
                }">
                    {_pct(
                        signal.get("price_change_pct"),
                        signed=True,
                    )}
                </b>
            </div>

            <div class="sd-driver">
                <span>Выручка</span>
                <b class="{
                    'positive'
                    if number(signal.get('revenue_change_pct')) > 0
                    else 'negative'
                    if number(signal.get('revenue_change_pct')) < 0
                    else ''
                }">
                    {_pct(
                        signal.get("revenue_change_pct"),
                        signed=True,
                    )}
                </b>
            </div>

        </div>
    </section>
    """


# =============================================================================
# MONTHLY
# =============================================================================

def _monthly_block(
    payload: dict,
) -> str:
    rows = (
        payload
        .get("sales", {})
        .get("monthly_price_rows", [])
    )

    chart = monthly_drivers_chart(
        rows
    )

    if not chart:
        chart = (
            '<div class="empty">'
            "Недостаточно данных"
            "</div>"
        )

    return f"""
    <section class="sd-monthly">

        <div class="sd-block-head">
            <div>
                <div class="sd-kicker">
                    12 МЕСЯЦЕВ
                </div>

                <div class="sd-title small">
                    Из чего складывалась динамика выручки
                </div>

                <div class="sd-subtitle">
                    чистая выручка · изменение количества · изменение средней цены
                </div>
            </div>
        </div>

        <div class="sd-monthly-chart">
            {chart}
        </div>

    </section>
    """


# =============================================================================
# 90 DAYS
# =============================================================================

def _regime_block(
    payload: dict,
) -> str:
    rows = (
        payload
        .get("sales", {})
        .get("daily_price_rows", [])
    )

    chart = demand_price_index_chart(
        rows
    )

    if not chart:
        chart = (
            '<div class="empty">'
            "Недостаточно данных"
            "</div>"
        )

    return f"""
    <section class="sd-regime">

        <div class="sd-block-head">
            <div>
                <div class="sd-kicker">
                    90 ДНЕЙ
                </div>

                <div class="sd-title">
                    Количество продаж и средняя цена
                </div>

                <div class="sd-subtitle">
                    7-дневные средние · показатели приведены к единой базе 100
                </div>
            </div>

            <div class="sd-caption">
                Сравниваем относительную динамику,<br>
                а не абсолютные единицы
            </div>
        </div>

        <div class="sd-regime-chart">
            {chart}
        </div>

        <div class="sd-chart-note">
            Количество — положительные продажи.
            Средняя цена зависит как от фактических цен,
            так и от товарного микса. График показывает
            совместную динамику показателей и не доказывает
            причинное влияние цены на продажи.
        </div>

    </section>
    """


# =============================================================================
# PERIOD DETAILS
# =============================================================================

def _period_block(
    signal: dict,
) -> str:
    recent = signal.get(
        "recent",
        {},
    )

    previous = signal.get(
        "previous",
        {},
    )

    return f"""
    <section class="sd-period-section">

        <div class="sd-kicker">
            ДВА СОПОСТАВИМЫХ ПЕРИОДА
        </div>

        <div class="sd-title small">
            Что изменилось за последние 14 дней
        </div>

        <div class="sd-period-grid">

            <div class="sd-period-card primary">
                <div class="sd-period-label">
                    ПОСЛЕДНИЕ 14 ДНЕЙ
                </div>

                <div class="sd-period-value">
                    {_number(recent.get("sales_qty"))} ед.
                </div>

                <div class="sd-period-copy">
                    Средняя цена:
                    <b>{_money_short(recent.get("avg_price"))}</b>
                    <br>
                    Чистая выручка:
                    <b>{_money_short(recent.get("net_amount"))}</b>
                </div>
            </div>

            <div class="sd-period-card">
                <div class="sd-period-label">
                    ПРЕДЫДУЩИЕ 14 ДНЕЙ
                </div>

                <div class="sd-period-value">
                    {_number(previous.get("sales_qty"))} ед.
                </div>

                <div class="sd-period-copy">
                    Средняя цена:
                    <b>{_money_short(previous.get("avg_price"))}</b>
                    <br>
                    Чистая выручка:
                    <b>{_money_short(previous.get("net_amount"))}</b>
                </div>
            </div>

            <div class="sd-period-card">
                <div class="sd-period-label">
                    ИЗМЕНЕНИЕ
                </div>

                <div class="sd-period-value">
                    {_pct(
                        signal.get("qty_change_pct"),
                        signed=True,
                    )}
                </div>

                <div class="sd-period-copy">
                    Цена:
                    <b>
                        {_pct(
                            signal.get("price_change_pct"),
                            signed=True,
                        )}
                    </b>
                    <br>
                    Выручка:
                    <b>
                        {_pct(
                            signal.get("revenue_change_pct"),
                            signed=True,
                        )}
                    </b>
                </div>
            </div>

        </div>

    </section>
    """


# =============================================================================
# METHODOLOGY
# =============================================================================

def _methodology_block() -> str:
    return """
    <section class="sd-methodology">

        <div class="sd-kicker">
            КАК ЧИТАТЬ СТРАНИЦУ
        </div>

        <div class="sd-methodology-grid">

            <div>
                <b>Количество — не абсолютный рыночный спрос.</b>
                Используются положительные продажи.
                На объём также влияют наличие, карточка товара,
                продвижение и ассортимент.
            </div>

            <div>
                <b>Средняя цена взвешена количеством.</b>
                Поэтому её изменение отражает одновременно
                ценовой уровень реализации и изменение
                товарного микса.
            </div>

            <div>
                <b>Чистая выручка пересчитывается.</b>
                Возврат относится к исходной дате реализации,
                поэтому исторические значения могут уточняться
                ретроспективно.
            </div>

        </div>

    </section>
    """


# =============================================================================
# PAGE
# =============================================================================

def build_sales_dynamics_page(
    payload: dict,
) -> str:
    signal = _signal(
        payload
    )

    return f"""
    {SALES_DYNAMICS_CSS}

    <!-- =============================================================
         SALES DYNAMICS PAGE
         ============================================================= -->

    <div class="page sales-dynamics-page">

        {_masthead(payload)}

        {_kpi_row(
            payload,
            signal,
        )}

        <div class="sd-story">
            {_editorial_block(signal)}
            {_monthly_block(payload)}
        </div>

        {_regime_block(payload)}

        {_period_block(signal)}

        {_methodology_block()}

        <div class="sd-footer">
            <span>
                Источник: WB и управленческий контур
            </span>

            <span>
                Горизонт: 14 дней · 90 дней · 12 месяцев
            </span>
        </div>

    </div>
    """