# # gear/app/daily_sales/daily_brief/presentation/pages/financial_page.py

# from __future__ import annotations

# from ...helpers import (
#     fmt_money,
#     fmt_pct,
#     number,
# )
# from ..components import safe
# from ..icons import icon

# from .financial_charts import (
#     economics_100_chart,
#     financial_bridge_chart,
#     financial_result_trend_chart,
#     return_categories_chart,
# )


# TITLE = "Коммерческий обзор · финрезультат"
# SUBTITLE = "Выручка · себестоимость · комиссия · маржа · расходы WB"


# # =============================================================================
# # ФОРМАТИРОВАНИЕ
# # =============================================================================


# def _money_short(
#     value,
# ) -> str:
#     value = number(value)

#     if abs(value) >= 1_000_000_000:
#         text = (
#             f"{value / 1_000_000_000:.1f}"
#             .replace(".", ",")
#         )

#         return f"{text}\u00A0млрд\u00A0₽"

#     if abs(value) >= 1_000_000:
#         text = (
#             f"{value / 1_000_000:.1f}"
#             .replace(".", ",")
#         )

#         return f"{text}\u00A0млн\u00A0₽"

#     if abs(value) >= 1_000:
#         text = (
#             f"{value / 1_000:.1f}"
#             .replace(".", ",")
#         )

#         return f"{text}\u00A0тыс.\u00A0₽"

#     return fmt_money(value)


# def _pct(
#     value,
# ) -> str:
#     return (
#         f"{number(value):.1f}%"
#         .replace(".", ",")
#     )


# def _signed_pct(
#     value,
# ) -> str:
#     if value is None:
#         return "нет базы"

#     value = number(value)

#     if value > 0:
#         return (
#             "+"
#             + _pct(value)
#         )

#     return _pct(value)


# # =============================================================================
# # ШАПКА
# # =============================================================================


# def _masthead(
#     payload: dict,
# ) -> str:
#     return f"""
#     <header class="masthead">

#         <div>
#             <div class="brandline">
#                 ТРЕНДСЕТТЕР · ФИНАНСОВЫЙ РАЗВОРОТ
#             </div>

#             <h1>{TITLE}</h1>

#             <div class="mast-subtitle">
#                 {SUBTITLE}
#             </div>
#         </div>

#         <div class="issue-meta">
#             Выпуск за
#             <b>{safe(payload.get("report_date"))}</b>
#             <br>
#             Сформирован автоматически
#         </div>

#     </header>
#     """


# # =============================================================================
# # KPI
# # =============================================================================


# def _kpi_card(
#     label: str,
#     value: str,
#     note: str,
#     icon_name: str,
#     *,
#     tone: str = "",
# ) -> str:

#     return f"""
#     <div class="finance-kpi {safe(tone)}">

#         <div class="finance-kpi-top">

#             <span>
#                 {safe(label)}
#             </span>

#             <span class="finance-kpi-icon">
#                 {icon(icon_name, 22)}
#             </span>

#         </div>

#         <div class="finance-kpi-value">
#             {safe(value)}
#         </div>

#         <div class="finance-kpi-note">
#             {safe(note)}
#         </div>

#     </div>
#     """


# def _kpis(
#     payload: dict,
# ) -> str:

#     finance = (
#         payload
#         .get("financial", {})
#         .get("current", {})
#     )

#     sales_kpi = (
#         payload
#         .get("sales", {})
#         .get("kpi", {})
#     )

#     result = number(
#         finance.get("wb_result")
#     )

#     result_pct = number(
#         finance.get("result_pct")
#     )

#     margin = number(
#         finance.get("margin_man")
#     )

#     margin_pct = number(
#         finance.get("margin_pct")
#     )

#     returns_amount = number(
#         sales_kpi.get("returns_amount")
#     )

#     returns_rate = number(
#         sales_kpi.get("returns_rate")
#     )

#     result_change = finance.get(
#         "result_change_pct"
#     )

#     margin_change = finance.get(
#         "margin_change_pct"
#     )

#     return f"""
#     <div class="finance-kpi-grid">

#         {_kpi_card(
#             "Финансовый результат WB",
#             _money_short(result),
#             (
#                 f"{_pct(result_pct)} "
#                 "от выручки без НДС · "
#                 f"{_signed_pct(result_change)} ко вчера"
#             ),
#             "revenue",
#             tone=(
#                 "positive"
#                 if result >= 0
#                 else "negative"
#             ),
#         )}

#         {_kpi_card(
#             "Управленческая маржа",
#             _money_short(margin),
#             (
#                 f"{_pct(margin_pct)} "
#                 "от выручки без НДС · "
#                 f"{_signed_pct(margin_change)} ко вчера"
#             ),
#             "margin",
#             tone=(
#                 "positive"
#                 if margin >= 0
#                 else "negative"
#             ),
#         )}

#         {_kpi_card(
#             "Расходы WB",
#             _money_short(
#                 finance.get("wb_costs")
#             ),
#             (
#                 f"{_pct(finance.get('wb_costs_share'))} "
#                 "от выручки без НДС"
#             ),
#             "price",
#             tone="cost",
#         )}

#         {_kpi_card(
#             "Возвраты",
#             _money_short(
#                 returns_amount
#             ),
#             (
#                 f"{_pct(returns_rate)} "
#                 "от числа продаж"
#             ),
#             "returns",
#             tone="returns",
#         )}

#     </div>
#     """


# # =============================================================================
# # КОНКРЕТНЫЙ АВТОМАТИЧЕСКИЙ ВЫВОД
# # =============================================================================


# def _result_comment(
#     payload: dict,
# ) -> str:
#     """
#     Не редакционный абзац «ни о чём»,
#     а короткое объяснение экономики конкретного дня.
#     """

#     finance = (
#         payload
#         .get("financial", {})
#         .get("current", {})
#     )

#     sales_kpi = (
#         payload
#         .get("sales", {})
#         .get("kpi", {})
#     )

#     revenue = number(
#         finance.get("revenue_net")
#     )

#     result = number(
#         finance.get("wb_result")
#     )

#     result_pct = number(
#         finance.get("result_pct")
#     )

#     cogs_share = number(
#         finance.get("cogs_share")
#     )

#     commission_share = number(
#         finance.get("commission_share")
#     )

#     wb_costs_share = number(
#         finance.get("wb_costs_share")
#     )

#     returns_amount = number(
#         sales_kpi.get("returns_amount")
#     )

#     sales_amount = number(
#         sales_kpi.get("sales_amount")
#     )

#     returns_sales_share = (
#         returns_amount
#         / sales_amount
#         * 100
#         if sales_amount
#         else 0
#     )

#     if revenue <= 0:
#         return """
#         <div class="finance-insight neutral">
#             <b>Недостаточно данных для разбора экономики дня.</b>
#             Выручка без НДС отсутствует либо равна нулю,
#             поэтому относительные показатели не интерпретируются.
#         </div>
#         """

#     result_phrase = (
#         "сохранила"
#         if result >= 0
#         else "потеряла"
#     )

#     result_abs_pct = abs(
#         result_pct
#     )

#     pressure_parts = []

#     pressure_parts.append(
#         f"себестоимость забрала {_pct(cogs_share)}"
#     )

#     pressure_parts.append(
#         f"комиссия WB — {_pct(commission_share)}"
#     )

#     pressure_parts.append(
#         f"прочие расходы WB — {_pct(wb_costs_share)}"
#     )

#     returns_text = ""

#     if returns_amount > 0:
#         returns_text = (
#             " Возвраты составили "
#             f"{_money_short(returns_amount)}"
#             " — это "
#             f"{_pct(returns_sales_share)} "
#             "от суммы положительных продаж."
#         )

#     tone = (
#         "positive"
#         if result >= 0
#         else "negative"
#     )

#     return f"""
#     <div class="finance-insight {tone}">

#         <div class="finance-insight-label">
#             ЧТО ОЗНАЧАЕТ РЕЗУЛЬТАТ
#         </div>

#         <div class="finance-insight-text">

#             Из каждых <b>100 ₽ выручки без НДС</b>
#             компания {result_phrase}
#             <b>{_pct(result_abs_pct)}</b>
#             в финансовом результате.

#             Основное распределение выручки:
#             {", ".join(pressure_parts)}.

#             {returns_text}

#         </div>

#     </div>
#     """


# # =============================================================================
# # ОСНОВНОЙ МОСТ
# # =============================================================================


# def _bridge_block(
#     payload: dict,
# ) -> str:

#     finance = (
#         payload
#         .get("financial", {})
#         .get("current", {})
#     )

#     chart = financial_bridge_chart(
#         finance
#     )

#     return f"""
#     <section class="finance-main-card">

#         <div class="finance-block-head">

#             <div>
#                 <div class="finance-kicker">
#                     ЭКОНОМИКА ДНЯ
#                 </div>

#                 <div class="finance-block-title">
#                     Как выручка превращается
#                     в финансовый результат
#                 </div>
#             </div>

#             <div class="finance-block-note">
#                 показатели за один закрытый день
#             </div>

#         </div>

#         <div class="finance-bridge-chart">
#             {chart}
#         </div>

#     </section>
#     """


# # =============================================================================
# # 100 ₽
# # =============================================================================


# def _economics_block(
#     payload: dict,
# ) -> str:

#     finance = (
#         payload
#         .get("financial", {})
#         .get("current", {})
#     )

#     chart = economics_100_chart(
#         finance
#     )

#     return f"""
#     <section class="finance-side-card">

#         <div class="finance-kicker">
#             UNIT ECONOMICS
#         </div>

#         <div class="finance-side-title">
#             Куда уходят 100 ₽
#         </div>

#         <div class="finance-side-subtitle">
#             доли рассчитаны от выручки без НДС
#         </div>

#         <div class="finance-economics-chart">
#             {chart}
#         </div>

#     </section>
#     """


# # =============================================================================
# # 30 ДНЕЙ
# # =============================================================================


# def _trend_block(
#     payload: dict,
# ) -> str:

#     rows = (
#         payload
#         .get("financial", {})
#         .get("history", [])
#     )

#     chart = financial_result_trend_chart(
#         rows
#     )

#     if not chart:
#         chart = """
#         <div class="finance-empty">
#             Нет данных для динамики финансового результата.
#         </div>
#         """

#     return f"""
#     <section class="finance-trend-card">

#         <div class="finance-block-head">

#             <div>
#                 <div class="finance-kicker">
#                     УСТОЙЧИВОСТЬ РЕЗУЛЬТАТА
#                 </div>

#                 <div class="finance-block-title small">
#                     Финансовый результат · последние 30 дней
#                 </div>
#             </div>

#             <div class="finance-legend">
#                 <span class="finance-dot positive"></span>
#                 прибыль

#                 <span class="finance-dot negative"></span>
#                 убыток
#             </div>

#         </div>

#         <div class="finance-trend-chart">
#             {chart}
#         </div>

#     </section>
#     """


# # =============================================================================
# # ВОЗВРАТЫ
# # =============================================================================


# def _returns_block(
#     payload: dict,
# ) -> str:

#     sales = payload.get(
#         "sales",
#         {},
#     )

#     rows = sales.get(
#         "return_categories",
#         [],
#     )

#     chart = return_categories_chart(
#         rows,
#         limit=5,
#     )

#     if not chart:
#         chart = """
#         <div class="finance-empty">
#             Возвратов по категориям за день нет.
#         </div>
#         """

#     return f"""
#     <section class="finance-returns-card">

#         <div class="finance-kicker">
#             ДАВЛЕНИЕ НА РЕЗУЛЬТАТ
#         </div>

#         <div class="finance-block-title small">
#             Где сосредоточены возвраты
#         </div>

#         <div class="finance-side-subtitle">
#             категории с максимальной суммой возврата
#         </div>

#         <div class="finance-returns-chart">
#             {chart}
#         </div>

#     </section>
#     """


# # =============================================================================
# # СБОРКА СТРАНИЦЫ
# # =============================================================================


# def build_financial_page(
#     payload: dict,
# ) -> str:

#     return f"""
#     <!-- =============================================================
#          СТРАНИЦА — ФИНАНСОВЫЙ РЕЗУЛЬТАТ
#          ============================================================= -->

#     <div class="page financial-page">

#         {_masthead(payload)}

#         {_kpis(payload)}

#         <div class="finance-main-grid">

#             {_bridge_block(payload)}

#             {_economics_block(payload)}

#         </div>

#         {_result_comment(payload)}

#         <div class="finance-bottom-grid">

#             {_trend_block(payload)}

#             {_returns_block(payload)}

#         </div>

#         <div class="finance-footer-note">

#             <span>
#                 Финансовый результат показан
#                 по управленческой методологии daily sales.
#             </span>

#             <span>
#                 Возвраты относятся к дате исходной продажи.
#             </span>

#         </div>

#     </div>
#     """



# gear/app/daily_sales/daily_brief/presentation/pages/financial_page.py

from __future__ import annotations

import pandas as pd

from ...helpers import (
    fmt_money,
    number,
)
from ..components import safe
from ..icons import icon

from .financial_charts import (
    economics_100_chart,
    financial_bridge_chart,
    financial_result_trend_chart,
    weekly_result_strip,
)


TITLE = (
    "Коммерческий обзор · финрезультат"
)

SUBTITLE = (
    "Выручка · себестоимость · комиссия · маржа · расходы WB"
)


# =============================================================================
# FORMATTERS
# =============================================================================


def _money_short(
    value,
) -> str:

    value = number(
        value
    )

    sign = (
        "−"
        if value < 0
        else ""
    )

    absolute = abs(
        value
    )

    if absolute >= 1_000_000_000:
        text = (
            f"{absolute / 1_000_000_000:.1f}"
            .replace(".", ",")
        )

        return (
            f"{sign}{text}\u00A0млрд\u00A0₽"
        )

    if absolute >= 1_000_000:
        text = (
            f"{absolute / 1_000_000:.1f}"
            .replace(".", ",")
        )

        return (
            f"{sign}{text}\u00A0млн\u00A0₽"
        )

    if absolute >= 1_000:
        text = (
            f"{absolute / 1_000:.1f}"
            .replace(".", ",")
        )

        return (
            f"{sign}{text}\u00A0тыс.\u00A0₽"
        )

    return fmt_money(
        value
    )


def _pct(
    value,
    *,
    signed: bool = False,
) -> str:

    value = number(
        value
    )

    sign = ""

    if signed:
        if value > 0:
            sign = "+"
        elif value < 0:
            sign = "−"

    elif value < 0:
        sign = "−"

    return (
        f"{sign}{abs(value):.1f}%"
        .replace(".", ",")
    )


def _pp(
    value,
) -> str:

    value = number(
        value
    )

    if value > 0:
        sign = "+"

    elif value < 0:
        sign = "−"

    else:
        sign = ""

    return (
        f"{sign}{abs(value):.1f} п.п."
        .replace(".", ",")
    )


def _period_label(
    value_from,
    value_to,
) -> str:

    start = pd.to_datetime(
        value_from,
        errors="coerce",
    )

    end = pd.to_datetime(
        value_to,
        errors="coerce",
    )

    if (
        pd.isna(start)
        or pd.isna(end)
    ):
        return ""

    return (
        f"{start:%d.%m}"
        f"–"
        f"{end:%d.%m.%Y}"
    )


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
                ТРЕНДСЕТТЕР · ФИНАНСОВЫЙ РАЗВОРОТ
            </div>

            <h1>
                {TITLE}
            </h1>

            <div class="mast-subtitle">
                {SUBTITLE}
            </div>

        </div>

        <div class="issue-meta">
            Выпуск за
            <b>
                {safe(payload.get("report_date"))}
            </b>
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
    icon_name: str,
    *,
    tone: str = "",
) -> str:

    return f"""
    <article class="finance-kpi {safe(tone)}">

        <div class="finance-kpi-top">

            <span>
                {safe(label)}
            </span>

            <span class="finance-kpi-icon">
                {icon(icon_name, 22)}
            </span>

        </div>

        <div class="finance-kpi-value">
            {safe(value)}
        </div>

        <div class="finance-kpi-note">
            {safe(note)}
        </div>

    </article>
    """


def _kpi_row(
    payload: dict,
) -> str:

    finance = (
        payload
        .get(
            "financial",
            {},
        )
        .get(
            "current",
            {},
        )
    )

    sales_kpi = (
        payload
        .get(
            "sales",
            {},
        )
        .get(
            "kpi",
            {},
        )
    )

    result = number(
        finance.get(
            "wb_result"
        )
    )

    margin = number(
        finance.get(
            "margin_man"
        )
    )

    return f"""
    <div class="finance-kpi-grid">

        {_kpi_card(
            "Финансовый результат WB",
            _money_short(result),
            (
                f"{_pct(finance.get('result_pct'))} "
                "от выручки без НДС"
            ),
            "revenue",
            tone=(
                "positive"
                if result >= 0
                else "negative"
            ),
        )}

        {_kpi_card(
            "Управленческая маржа",
            _money_short(margin),
            (
                f"{_pct(finance.get('margin_pct'))} "
                "от выручки без НДС"
            ),
            "margin",
            tone=(
                "positive"
                if margin >= 0
                else "negative"
            ),
        )}

        {_kpi_card(
            "Расходы WB",
            _money_short(
                finance.get(
                    "wb_costs"
                )
            ),
            (
                f"{_pct(finance.get('wb_costs_share'))} "
                "от выручки без НДС"
            ),
            "price",
            tone="cost",
        )}

        {_kpi_card(
            "Возвраты",
            _money_short(
                sales_kpi.get(
                    "returns_amount"
                )
            ),
            (
                f"{_pct(sales_kpi.get('returns_rate'))} "
                "от числа продаж"
            ),
            "returns",
            tone="returns",
        )}

    </div>
    """


# =============================================================================
# MAIN DAY BRIDGE
# =============================================================================


def _bridge_block(
    payload: dict,
) -> str:

    finance = (
        payload
        .get(
            "financial",
            {},
        )
        .get(
            "current",
            {},
        )
    )

    return f"""
    <section class="finance-main-card">

        <div class="finance-block-head">

            <div>

                <div class="finance-kicker">
                    ЭКОНОМИКА ДНЯ
                </div>

                <div class="finance-block-title">
                    Как выручка превращается
                    в финансовый результат
                </div>

            </div>

            <div class="finance-block-note">
                актуальное состояние пересчитанной даты
            </div>

        </div>

        <div class="finance-bridge-chart">
            {financial_bridge_chart(finance)}
        </div>

    </section>
    """


def _economics_block(
    payload: dict,
) -> str:

    finance = (
        payload
        .get(
            "financial",
            {},
        )
        .get(
            "current",
            {},
        )
    )

    return f"""
    <section class="finance-side-card">

        <div class="finance-kicker">
            UNIT ECONOMICS
        </div>

        <div class="finance-side-title">
            Куда уходят 100 ₽
        </div>

        <div class="finance-side-subtitle">
            доли от выручки без НДС
        </div>

        <div class="finance-economics-chart">
            {economics_100_chart(finance)}
        </div>

    </section>
    """


# =============================================================================
# DAILY COMMENT
# =============================================================================


def _day_comment(
    payload: dict,
) -> str:

    finance = (
        payload
        .get(
            "financial",
            {},
        )
        .get(
            "current",
            {},
        )
    )

    sales_kpi = (
        payload
        .get(
            "sales",
            {},
        )
        .get(
            "kpi",
            {},
        )
    )

    result_pct = number(
        finance.get(
            "result_pct"
        )
    )

    cogs_share = number(
        finance.get(
            "cogs_share"
        )
    )

    commission_share = number(
        finance.get(
            "commission_share"
        )
    )

    wb_costs_share = number(
        finance.get(
            "wb_costs_share"
        )
    )

    returns = number(
        sales_kpi.get(
            "returns_amount"
        )
    )

    result_word = (
        "сохраняется"
        if result_pct >= 0
        else "теряется"
    )

    return f"""
    <section class="finance-insight">

        <div class="finance-insight-label">
            ЧТО ОЗНАЧАЕТ РЕЗУЛЬТАТ
        </div>

        <div class="finance-insight-text">

            Из каждых
            <b>100 ₽ выручки без НДС</b>
            в текущем финансовом результате
            {result_word}
            <b>{_pct(abs(result_pct))}</b>.

            Управленческая FIFO-себестоимость
            занимает
            <b>{_pct(cogs_share)}</b>,
            комиссия WB —
            <b>{_pct(commission_share)}</b>,
            распределённые расходы WB —
            <b>{_pct(wb_costs_share)}</b>.

            Известные на дату формирования отчёта возвраты,
            относимые к этой дате реализации,
            составляют
            <b>{_money_short(returns)}</b>.

        </div>

    </section>
    """


# =============================================================================
# 30 DAYS
# =============================================================================


def _trend_block(
    payload: dict,
) -> str:

    financial = payload.get(
        "financial",
        {},
    )

    chart = financial_result_trend_chart(
        financial.get(
            "history_30d",
            [],
        )
    )

    if not chart:
        chart = """
        <div class="finance-empty">
            Нет данных для 30-дневной динамики.
        </div>
        """

    return f"""
    <section class="finance-trend-card">

        <div class="finance-block-head">

            <div>

                <div class="finance-kicker">
                    ПЕРЕСЧИТАННАЯ ИСТОРИЯ
                </div>

                <div class="finance-block-title small">
                    Финансовый результат · последние 30 дней
                </div>

            </div>

            <div class="finance-legend">
                <i class="finance-dot positive"></i>
                прибыль

                <i class="finance-dot negative"></i>
                убыток
            </div>

        </div>

        <div class="finance-trend-chart">
            {chart}
        </div>

    </section>
    """


# =============================================================================
# CURRENT WEEK
# =============================================================================


def _week_metric(
    label: str,
    value: str,
    *,
    tone: str = "",
) -> str:

    return f"""
    <div class="finance-week-metric">

        <span>
            {safe(label)}
        </span>

        <b class="{safe(tone)}">
            {safe(value)}
        </b>

    </div>
    """


def _week_summary(
    payload: dict,
) -> str:

    financial = payload.get(
        "financial",
        {},
    )

    current = financial.get(
        "current_week",
        {},
    )

    previous = financial.get(
        "previous_week",
        {},
    )

    current_period = _period_label(
        current.get(
            "date_from"
        ),
        current.get(
            "date_to"
        ),
    )

    previous_period = _period_label(
        previous.get(
            "date_from"
        ),
        previous.get(
            "date_to"
        ),
    )

    result = number(
        current.get(
            "wb_result"
        )
    )

    previous_result = number(
        previous.get(
            "wb_result"
        )
    )

    delta_pp = number(
        current.get(
            "result_delta_pp"
        )
    )

    result_tone = (
        "positive"
        if result >= 0
        else "negative"
    )

    return f"""
    <section class="finance-week-card">

        <div class="finance-kicker">
            ТЕКУЩАЯ НЕДЕЛЯ
        </div>

        <div class="finance-week-period">
            {safe(current_period)}
        </div>

        <div class="finance-week-status">
            ОПЕРАТИВНЫЙ РЕЗУЛЬТАТ
        </div>

        <div class="finance-week-result {result_tone}">
            {_money_short(result)}
        </div>

        <div class="finance-week-result-caption">
            {_pct(current.get("result_pct"))}
            от выручки без НДС
        </div>

        <div class="finance-week-metrics">

            {_week_metric(
                "Выручка",
                _money_short(
                    current.get(
                        "revenue_net"
                    )
                ),
            )}

            {_week_metric(
                "Маржа",
                _money_short(
                    current.get(
                        "margin_man"
                    )
                ),
            )}

            {_week_metric(
                "WB расходы",
                _money_short(
                    current.get(
                        "wb_costs"
                    )
                ),
            )}

        </div>

        <div class="finance-week-comparison">

            <div class="finance-week-comparison-label">
                к предыдущей неделе
            </div>

            <div class="finance-week-comparison-main">
                {_pp(delta_pp)}
            </div>

            <div class="finance-week-comparison-base">
                {safe(previous_period)}
                · {_money_short(previous_result)}
                · {_pct(previous.get("result_pct"))}
            </div>

        </div>

        <div class="finance-week-warning">
            Показатель может уточняться после загрузки
            очередных расходов WB и новых возвратов.
        </div>

    </section>
    """


# =============================================================================
# WEEK STRIP
# =============================================================================


def _weeks_block(
    payload: dict,
) -> str:

    financial = payload.get(
        "financial",
        {},
    )

    weeks = financial.get(
        "weeks",
        [],
    )

    chart = weekly_result_strip(
        weeks
    )

    if not chart:
        chart = """
        <div class="finance-empty">
            Нет данных для недельной истории.
        </div>
        """

    return f"""
    <section class="finance-weeks-strip-card">

        <div class="finance-block-head">

            <div>

                <div class="finance-kicker">
                    НЕДЕЛЯ ЗА НЕДЕЛЕЙ
                </div>

                <div class="finance-block-title small">
                    Финансовый результат и рентабельность
                </div>

            </div>

            <div class="finance-block-note">
                насыщенность фона отражает качество результата
            </div>

        </div>

        <div class="finance-weeks-strip">
            {chart}
        </div>

    </section>
    """


# =============================================================================
# EDITORIAL WEEK COMMENT
# =============================================================================


def _week_editorial(
    payload: dict,
) -> str:

    comment = (
        payload
        .get(
            "financial",
            {},
        )
        .get(
            "week_comment",
            {},
        )
    )

    title = (
        comment.get(
            "title"
        )
        or "Недостаточно данных"
    )

    lead = (
        comment.get(
            "lead"
        )
        or (
            "Сравнение с предыдущей неделей "
            "пока недоступно."
        )
    )

    tone = (
        comment.get(
            "tone"
        )
        or "neutral"
    )

    return f"""
    <section class="finance-editorial {safe(tone)}">

        <div class="finance-kicker">
            РЕДАКЦИОННЫЙ ВЫВОД
        </div>

        <div class="finance-editorial-title">
            {safe(title)}
        </div>

        <div class="finance-editorial-text">
            {safe(lead)}
        </div>

        <div class="finance-editorial-deltas">

            <div>
                <span>
                    Результат
                </span>

                <b>
                    {_pp(
                        comment.get(
                            "result_delta_pp"
                        )
                    )}
                </b>
            </div>

            <div>
                <span>
                    Базовая маржа
                </span>

                <b>
                    {_pp(
                        comment.get(
                            "margin_delta_pp"
                        )
                    )}
                </b>
            </div>

            <div>
                <span>
                    Расходы WB
                </span>

                <b>
                    {_pp(
                        comment.get(
                            "wb_costs_delta_pp"
                        )
                    )}
                </b>
            </div>

        </div>

    </section>
    """


# =============================================================================
# METHODOLOGY
# =============================================================================


def _methodology_block() -> str:

    return """
    <section class="finance-methodology">

        <div class="finance-methodology-title">
            КАК ЧИТАТЬ ПЕРЕСЧИТАННЫЙ РЕЗУЛЬТАТ
        </div>

        <div class="finance-methodology-grid">

            <div>

                <b>
                    Возвраты корректируют исходную реализацию.
                </b>

                Продажа и её последующий возврат отражаются
                по первоначальной дате реализации.
                После появления возврата историческая выручка,
                себестоимость и связанные показатели
                соответствующего дня пересчитываются.

            </div>

            <div>

                <b>
                    Расходы WB поступают неравномерно.
                </b>

                Маркетинг, штрафы и другие начисления
                могут поступать отдельными недельными пакетами.
                После загрузки они распределяются на реализованные
                единицы, поэтому текущая и историческая
                недельная рентабельность может уточняться.

            </div>

            <div>

                <b>
                    История показывает актуальное состояние.
                </b>

                Графики отражают не сохранённый снимок результата
                на дату прошлого отчёта, а показатели,
                пересчитанные по всей информации,
                доступной на момент формирования текущего выпуска.

            </div>

        </div>

    </section>
    """


# =============================================================================
# PAGE
# =============================================================================

def _cost_control(
    payload: dict,
) -> str:
    """
    Контроль качества исходной себестоимости.

    Основной показатель — доля проданных единиц,
    для которых отсутствует исходная себестоимость.

    Дополнительно показываем динамику накопленным итогом:
    текущая неделя / квартал / с начала года.
    """

    quality = (
        payload
        .get(
            "financial",
            {},
        )
        .get(
            "cost_quality",
            {},
        )
    )

    day = quality.get(
        "day",
        {},
    )

    week = quality.get(
        "week",
        {},
    )

    quarter = quality.get(
        "quarter",
        {},
    )

    ytd = quality.get(
        "ytd",
        {},
    )

    day_pct = number(
        day.get(
            "no_cost_pct"
        )
    )

    no_cost = int(
        number(
            day.get(
                "no_cost_units"
            )
        )
    )

    sales_units = int(
        number(
            day.get(
                "sales_units"
            )
        )
    )

    no_stocks = int(
        number(
            day.get(
                "no_stocks_units"
            )
        )
    )

    no_income = int(
        number(
            day.get(
                "no_income_units"
            )
        )
    )

    if no_cost == 0:

        tone = "ok"

        title = (
            "Все продажи дня обеспечены исходной себестоимостью"
        )

    else:

        tone = "warning"

        title = (
            "Часть продаж требует проверки себестоимости"
        )

    def period_card(
        label: str,
        data: dict,
    ) -> str:

        pct = number(
            data.get(
                "no_cost_pct"
            )
        )

        missing = int(
            number(
                data.get(
                    "no_cost_units"
                )
            )
        )

        total = int(
            number(
                data.get(
                    "sales_units"
                )
            )
        )

        return f"""
        <div class="finance-cost-period">

            <span class="finance-cost-period-label">
                {safe(label)}
            </span>

            <b class="finance-cost-period-pct">
                {_pct(pct)}
            </b>

            <span class="finance-cost-period-count">
                {missing:,}
                из
                {total:,}
                ед.
            </span>

        </div>
        """.replace(
            ",",
            " "
        )

    return f"""
    <section class="finance-cost-control {safe(tone)}">

        <div class="finance-cost-day">

            <div class="finance-kicker">
                КОНТРОЛЬ СЕБЕСТОИМОСТИ
            </div>

            <div class="finance-cost-control-title">
                {safe(title)}
            </div>

            <div class="finance-cost-day-main">

                <div class="finance-cost-day-percent">
                    {_pct(day_pct)}
                </div>

                <div class="finance-cost-day-caption">

                    продаж без исходной с/с

                    <b>
                        {no_cost:,}
                        из
                        {sales_units:,}
                        ед.
                    </b>

                </div>

            </div>

            <div class="finance-cost-day-details">

                <span>
                    Нет на складе
                    <b>{no_stocks:,} ед.</b>
                </span>

                <span>
                    Нет приходов
                    <b>{no_income:,} ед.</b>
                </span>

            </div>

        </div>

        <div class="finance-cost-history">

            {period_card(
                "Текущая неделя",
                week,
            )}

            {period_card(
                "С начала квартала",
                quarter,
            )}

            {period_card(
                "С начала года",
                ytd,
            )}

        </div>

    </section>
    """.replace(
        ",",
        " "
    )

def build_financial_page(
    payload: dict,
) -> str:

    return f"""
    <!-- =============================================================
         FINANCIAL PAGE
         ============================================================= -->

    <div class="page financial-page">

        {_masthead(payload)}

        {_kpi_row(payload)}

        <div class="finance-main-grid">

            {_bridge_block(payload)}

            {_economics_block(payload)}

        </div>

        {_day_comment(payload)}

        <div class="finance-mid-grid">

            {_trend_block(payload)}

            {_week_summary(payload)}

        </div>

        {_weeks_block(payload)}

        <div class="finance-lower-grid">

            {_week_editorial(payload)}

            {_methodology_block()}

        </div>
        
        {_cost_control(payload)}

        <div class="finance-footer-note">

            <span>
                Себестоимость:
                управленческий FIFO.
            </span>

            <span>
                Исторические показатели
                могут пересчитываться ретроспективно.
            </span>

        </div>

    </div>
    """