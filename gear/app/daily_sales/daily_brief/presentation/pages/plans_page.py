# gear/app/daily_sales/daily_brief/presentation/pages/plans_page.py

from __future__ import annotations

from datetime import date

import pandas as pd

from ...helpers import (
    fmt_money,
    fmt_number,
    fmt_pct,
    number,
)
from ..components import safe
from ..icons import icon
from .plan_charts import (
    current_month_plan_chart,
    half_year_gauge_chart,
    half_year_trajectory_chart,
    prophet_monthly_chart,
)


TITLE = "Коммерческий обзор · план"
SUBTITLE = "Продажи · спрос · цена · план · запасы"


MONTHS_RU = {
    1: "января",
    2: "февраля",
    3: "марта",
    4: "апреля",
    5: "мая",
    6: "июня",
    7: "июля",
    8: "августа",
    9: "сентября",
    10: "октября",
    11: "ноября",
    12: "декабря",
}


MONTHS_RU_NOMINATIVE = {
    1: "январь",
    2: "февраль",
    3: "март",
    4: "апрель",
    5: "май",
    6: "июнь",
    7: "июль",
    8: "август",
    9: "сентябрь",
    10: "октябрь",
    11: "ноябрь",
    12: "декабрь",
}


# =============================================================================
# ОБЩИЕ ФУНКЦИИ
# =============================================================================


def _money_short(
    value,
) -> str:
    """
    Компактное денежное значение с неразрывными пробелами.
    """

    value = number(value)

    if abs(value) >= 1_000_000_000:
        result = (
            f"{value / 1_000_000_000:.1f}"
            .replace(".", ",")
        )

        return (
            f"{result}\u00A0млрд\u00A0₽"
        )

    if abs(value) >= 1_000_000:
        result = (
            f"{value / 1_000_000:.1f}"
            .replace(".", ",")
        )

        return (
            f"{result}\u00A0млн\u00A0₽"
        )

    if abs(value) >= 1_000:
        result = (
            f"{value / 1_000:.1f}"
            .replace(".", ",")
        )

        return (
            f"{result}\u00A0тыс.\u00A0₽"
        )

    return fmt_money(value)


def _report_month(
    payload: dict,
) -> int:
    parsed = pd.to_datetime(
        payload.get(
            "report_date"
        ),
        errors="coerce",
    )

    if pd.isna(parsed):
        return date.today().month

    return int(
        parsed.month
    )


def _date_label(
    value,
) -> str:
    parsed = pd.to_datetime(
        value,
        errors="coerce",
    )

    if pd.isna(parsed):
        return safe(
            value
            or ""
        )

    return parsed.strftime(
        "%d.%m.%Y"
    )


def _chart_or_empty(
    chart_html: str | None,
    *,
    class_name: str,
    message: str,
) -> str:
    """
    Вставляет inline SVG, который возвращает plan_charts.py.

    Никаких img, Base64, Plotly, Kaleido и внешних файлов.
    """

    if not chart_html:
        return f"""
        <div class="plans-chart-empty">
            {safe(message)}
        </div>
        """

    return f"""
    <div class="{safe(class_name)}">
        {chart_html}
    </div>
    """


def _editorial_text(
    payload: dict,
    key: str,
    fallback: str,
) -> str:
    text = (
        payload
        .get("editorial", {})
        .get(key)
    )

    return safe(
        text
        or fallback
    )


# =============================================================================
# ШАПКА СТРАНИЦЫ
# =============================================================================


def _masthead(
    payload: dict,
) -> str:
    return f"""
    <header class="masthead">
        <div>
            <div class="brandline">
                ТРЕНДСЕТТЕР · ПЛАНОВЫЙ РАЗВОРОТ
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


def _metric(
    label: str,
    value: str,
    note: str,
    icon_name: str,
    *,
    tone: str = "",
) -> str:
    return f"""
    <div class="plans-metric {safe(tone)}">
        <div class="plans-metric-head">
            <span>
                {safe(label)}
            </span>

            <span class="plans-metric-icon">
                {icon(icon_name, 23)}
            </span>
        </div>

        <div class="plans-metric-value">
            {safe(value)}
        </div>

        <div class="plans-metric-note">
            {safe(note)}
        </div>
    </div>
    """


# =============================================================================
# ТАБЛИЦА ПОСЛЕДНИХ СЕМИ ДНЕЙ
# =============================================================================


def _prepare_daily_plan_rows(
    plan: dict,
) -> list[dict]:
    """
    Добавляет дневной план ко всем строкам месяца.

    Важно сначала рассчитать разницу накопительного плана
    на полном наборе строк, а уже затем брать последние семь дней.
    """

    source_rows = list(
        plan.get(
            "rows",
            [],
        )
        or []
    )

    prepared_rows: list[dict] = []

    for index, source_row in enumerate(
        source_rows
    ):
        row = dict(
            source_row
            or {}
        )

        current_running_plan = number(
            row.get(
                "running_plan"
            )
        )

        previous_running_plan = (
            number(
                source_rows[index - 1].get(
                    "running_plan"
                )
            )
            if index > 0
            else 0.0
        )

        daily_plan = max(
            current_running_plan
            - previous_running_plan,
            0.0,
        )

        prepared_rows.append(
            {
                **row,
                "daily_plan": daily_plan,
            }
        )

    return prepared_rows


def _last_seven_days_table(
    plan: dict,
) -> str:
    all_rows = _prepare_daily_plan_rows(
        plan
    )

    rows = all_rows[-7:]

    if not rows:
        return """
        <div class="plans-chart-empty">
            Нет данных по последним семи дням
        </div>
        """

    table_rows: list[str] = []

    total_fact = 0.0
    total_plan = 0.0

    for row in rows:
        fact = number(
            row.get(
                "fact"
            )
        )

        daily_plan = number(
            row.get(
                "daily_plan"
            )
        )

        delta = (
            fact
            - daily_plan
        )

        execution = (
            fact
            / daily_plan
            * 100
            if daily_plan
            else 0.0
        )

        total_fact += fact
        total_plan += daily_plan

        delta_class = (
            "positive"
            if delta >= 0
            else "negative"
        )

        delta_sign = (
            "+"
            if delta > 0
            else "−"
            if delta < 0
            else ""
        )

        table_rows.append(
            f"""
            <tr>
                <td>
                    {safe(row.get("date_label"))}
                </td>

                <td class="numeric">
                    {fmt_money(fact)}
                </td>

                <td class="numeric muted">
                    {fmt_money(daily_plan)}
                </td>

                <td class="numeric {delta_class}">
                    {delta_sign}{fmt_money(abs(delta))}
                </td>

                <td class="numeric">
                    {fmt_pct(execution)}
                </td>
            </tr>
            """
        )

    row_count = len(rows)

    average_fact = (
        total_fact
        / row_count
        if row_count
        else 0.0
    )

    average_plan = (
        total_plan
        / row_count
        if row_count
        else 0.0
    )

    average_delta = (
        average_fact
        - average_plan
    )

    average_execution = (
        average_fact
        / average_plan
        * 100
        if average_plan
        else 0.0
    )

    average_class = (
        "positive"
        if average_delta >= 0
        else "negative"
    )

    average_sign = (
        "+"
        if average_delta > 0
        else "−"
        if average_delta < 0
        else ""
    )

    return f"""
    <div class="plans-seven-days">
        <div class="plans-small-head">
            <div>
                <div class="plans-small-kicker">
                    ОПЕРАЦИОННЫЙ ТЕМП
                </div>

                <div class="plans-small-title">
                    Последние семь закрытых дней
                </div>
            </div>

            <div class="plans-seven-average">
                <span>
                    Средний факт
                </span>

                <b>
                    {fmt_money(average_fact)}
                </b>
            </div>
        </div>

        <table class="plans-seven-table">
            <thead>
                <tr>
                    <th>Дата</th>
                    <th>Факт</th>
                    <th>План дня</th>
                    <th>Отклонение</th>
                    <th>Выполнение</th>
                </tr>
            </thead>

            <tbody>
                {"".join(table_rows)}
            </tbody>

            <tfoot>
                <tr>
                    <td>
                        Среднее
                    </td>

                    <td class="numeric">
                        {fmt_money(average_fact)}
                    </td>

                    <td class="numeric">
                        {fmt_money(average_plan)}
                    </td>

                    <td class="numeric {average_class}">
                        {average_sign}{fmt_money(abs(average_delta))}
                    </td>

                    <td class="numeric">
                        {fmt_pct(average_execution)}
                    </td>
                </tr>
            </tfoot>
        </table>
    </div>
    """


# =============================================================================
# ЛЕВАЯ КОЛОНКА — ТЕКУЩИЙ МЕСЯЦ
# =============================================================================


def _month_column(
    payload: dict,
) -> str:
    plan = payload.get(
        "plan",
        {},
    )

    available = bool(
        plan.get(
            "available"
        )
    )

    chart_html = (
        current_month_plan_chart(
            plan
        )
        if available
        else None
    )

    delta = number(
        plan.get(
            "delta_to_date"
        )
    )

    delta_tone = (
        "positive"
        if delta >= 0
        else "negative"
    )

    fallback_text = (
        "Месячный план не рассчитан. "
        "Необходимо проверить активную бюджетную версию "
        "и распределение плана по календарным дням."
        if not available
        else (
            "Накопительный план-факт показывает, соответствует ли "
            "текущая выручка распределённому плану месяца. "
            "Таблица последних семи дней позволяет отделить "
            "разовый результат от устойчивого дневного темпа."
        )
    )

    return f"""
    <section class="plans-column plans-month-column">
        <header class="plans-column-head">
            <div>
                <div class="plans-column-kicker">
                    ПЛАН-ФАКТ
                </div>

                <h2>
                    Идём ли по графику
                </h2>

                <div class="plans-column-subtitle">
                    {safe(plan.get("label", ""))}
                </div>
            </div>

            <div class="plans-column-icon">
                {icon("plan", 31)}
            </div>
        </header>

        <div class="plans-metric-grid">
            {_metric(
                "Выполнение к дате",
                fmt_pct(
                    plan.get(
                        "exec_to_date_pct"
                    )
                ),
                (
                    "Факт "
                    f"{fmt_money(plan.get('fact_to_date'))}"
                ),
                "plan",
                tone="accent",
            )}

            {_metric(
                "Отклонение",
                fmt_money(delta),
                (
                    "План "
                    f"{fmt_money(plan.get('plan_to_date'))}"
                ),
                "margin",
                tone=delta_tone,
            )}

            {_metric(
                "Нужный темп",
                fmt_money(
                    plan.get(
                        "required_daily_rate"
                    )
                ),
                (
                    "Осталось "
                    f"{fmt_number(plan.get('remaining_days'))} дн."
                ),
                "focus",
            )}

            {_metric(
                "Выполнение месяца",
                fmt_pct(
                    plan.get(
                        "month_exec_pct"
                    )
                ),
                (
                    "Полный план "
                    f"{fmt_money(plan.get('month_plan'))}"
                ),
                "calendar",
            )}
        </div>



        {_last_seven_days_table(plan)}

        <div class="plans-editorial-copy dropcap">
            {_editorial_text(
                payload,
                "plan",
                fallback_text,
            )}
        </div>
    </section>
    """


# =============================================================================
# ПРОГРЕСС ПОЛУГОДИЯ
# =============================================================================


def _half_year_progress(
    data: dict,
) -> str:
    execution = number(
        data.get(
            "execution_pct"
        )
    )

    calendar = number(
        data.get(
            "calendar_pct"
        )
    )

    execution_width = max(
        0.0,
        min(
            execution,
            100.0,
        ),
    )

    calendar_width = max(
        0.0,
        min(
            calendar,
            100.0,
        ),
    )

    gap = (
        execution
        - calendar
    )

    gap_class = (
        "positive"
        if gap >= 0
        else "negative"
    )

    gap_arrow = (
        "▲"
        if gap >= 0
        else "▼"
    )

    gap_text = (
        "опережает календарь"
        if gap >= 0
        else "отстаёт от календаря"
    )

    return f"""
    <div class="plans-progress-card">
        <div class="plans-progress-item">
            <div>
                <span>
                    Выполнено плана
                </span>

                <b>
                    {fmt_pct(execution)}
                </b>
            </div>

            <div class="plans-progress-track">
                <span
                    class="execution"
                    style="width:{execution_width:.2f}%"
                ></span>
            </div>
        </div>

        <div class="plans-progress-item">
            <div>
                <span>
                    Прошло времени
                </span>

                <b>
                    {fmt_pct(calendar)}
                </b>
            </div>

            <div class="plans-progress-track">
                <span
                    class="calendar"
                    style="width:{calendar_width:.2f}%"
                ></span>
            </div>
        </div>

        <div class="plans-progress-result {gap_class}">
            {gap_arrow}
            {fmt_pct(abs(gap))}
            · выполнение {gap_text}
        </div>
    </div>
    """


# =============================================================================
# ТАБЛИЦА PROPHET
# =============================================================================


def _prophet_table(
    prophet: dict,
) -> str:
    rows = list(
        prophet.get(
            "monthly",
            [],
        )
        or []
    )

    if not rows:
        return """
        <div class="plans-chart-empty">
            Месячный прогноз Prophet не рассчитан
        </div>
        """

    visible_rows = [
        row
        for row in rows
        if (
            number(
                row.get(
                    "forecast"
                )
            ) > 0
            or number(
                row.get(
                    "fact"
                )
            ) > 0
        )
    ]

    if not visible_rows:
        return """
        <div class="plans-chart-empty">
            В прогнозе отсутствуют месячные значения
        </div>
        """

    table_rows: list[str] = []

    for row in visible_rows[-6:]:
        parsed_month = pd.to_datetime(
            (
                str(
                    row.get(
                        "month",
                        "",
                    )
                )
                + "-01"
            ),
            errors="coerce",
        )

        if pd.isna(parsed_month):
            month_label = safe(
                row.get(
                    "month"
                )
            )

        else:
            month_label = (
                MONTHS_RU_NOMINATIVE.get(
                    int(
                        parsed_month.month
                    ),
                    "",
                )
                .capitalize()
            )

        delta = number(
            row.get(
                "delta_to_plan"
            )
        )

        delta_class = (
            "positive"
            if delta >= 0
            else "negative"
        )

        delta_sign = (
            "+"
            if delta > 0
            else "−"
            if delta < 0
            else ""
        )

        table_rows.append(
            f"""
            <tr>
                <td>
                    {month_label}
                </td>

                <td class="numeric">
                    {_money_short(row.get("plan"))}
                </td>

                <td class="numeric">
                    {_money_short(row.get("fact"))}
                </td>

                <td class="numeric forecast">
                    {_money_short(row.get("forecast"))}
                </td>

                <td class="numeric">
                    {_money_short(row.get("expected_total"))}
                </td>

                <td class="numeric {delta_class}">
                    {delta_sign}{_money_short(abs(delta))}
                </td>
            </tr>
            """
        )

    return f"""
    <table class="plans-prophet-table">
        <thead>
            <tr>
                <th>Месяц</th>
                <th>План</th>
                <th>Факт</th>
                <th>Прогноз</th>
                <th>Ожидаемо</th>
                <th>Отклонение</th>
            </tr>
        </thead>

        <tbody>
            {"".join(table_rows)}
        </tbody>
    </table>
    """


# =============================================================================
# БЛОК PROPHET
# =============================================================================


def _prophet_block(
    payload: dict,
) -> str:
    prophet = payload.get(
        "prophet_plan",
        {},
    )

    if not prophet.get(
        "available"
    ):
        reason = prophet.get(
            "reason",
            "Прогноз не рассчитан.",
        )

        return f"""
        <section class="plans-prophet-section">
            <div class="plans-prophet-head">
                <div>
                    <div class="plans-column-kicker">
                        МОДЕЛЬНЫЙ ВЗГЛЯД
                    </div>

                    <h2>
                        Что показывает Prophet
                    </h2>

                    <div class="plans-column-subtitle">
                        Автоматический прогноз на основе
                        дневной чистой выручки
                    </div>
                </div>

                <div class="plans-prophet-badge">
                    PROPHET
                </div>
            </div>

            <div class="plans-chart-empty">
                {safe(reason)}
            </div>
        </section>
        """

    metrics = prophet.get(
        "metrics",
        {},
    )

    chart_html = prophet_monthly_chart(
        prophet.get(
            "monthly",
            [],
        )
    )

    execution = number(
        metrics.get(
            "projected_plan_exec_pct"
        )
    )

    delta = number(
        metrics.get(
            "projected_plan_delta"
        )
    )

    delta_class = (
        "positive"
        if delta >= 0
        else "negative"
    )

    delta_word = (
        "выше"
        if delta >= 0
        else "ниже"
    )

    return f"""
    <section class="plans-prophet-section">

        <div class="plans-prophet-layout">

            <div class="plans-prophet-summary">

                <div class="plans-prophet-head">
                    <div>
                        <div class="plans-column-kicker">
                            МОДЕЛЬНЫЙ ВЗГЛЯД
                        </div>

                        <h2>
                            Что показывает Prophet
                        </h2>

                        <div class="plans-column-subtitle">
                            Автоматический прогноз на основе
                            дневной чистой выручки
                        </div>
                    </div>
                </div>

                <div class="plans-prophet-kpis plans-prophet-kpis-compact">

                    <div>
                        <span>
                            Факт года
                        </span>

                        <b>
                            {_money_short(
                                metrics.get(
                                    "year_fact_total"
                                )
                            )}
                        </b>
                    </div>

                    <div>
                        <span>
                            Прогноз до конца года
                        </span>

                        <b>
                            {_money_short(
                                metrics.get(
                                    "forecast_to_year_end"
                                )
                            )}
                        </b>
                    </div>

                    <div>
                        <span>
                            Ожидаемый итог года
                        </span>

                        <b>
                            {_money_short(
                                metrics.get(
                                    "projected_year_total"
                                )
                            )}
                        </b>
                    </div>

                    <div class="{delta_class}">
                        <span>
                            Ожидаемое выполнение годового плана
                        </span>

                        <b>
                            {fmt_pct(execution)}
                        </b>
                    </div>

                </div>

                <div class="plans-prophet-conclusion {delta_class}">
                    При сохранении текущей динамики ожидаемый итог
                    будет {delta_word} годового плана на
                    <b>{_money_short(abs(delta))}</b>.
                </div>

            </div>

            <div class="plans-prophet-chart-side">

                <div class="plans-prophet-chart-head">
                    <div class="plans-chart-title">
                        План, факт и прогноз по месяцам
                    </div>

                   
                </div>

                {_chart_or_empty(
                    chart_html,
                    class_name="plans-svg-chart prophet-chart",
                    message=(
                        "Нет данных для построения "
                        "графика Prophet."
                    ),
                )}

            </div>

        </div>

        <div class="plans-prophet-table-wrap">
            {_prophet_table(prophet)}
        </div>

        <div class="plans-method-note">
            Прогноз не является утверждённым планом и не гарантирует
            будущий результат. Он показывает модельный сценарий при
            сохранении найденных трендов и сезонных закономерностей.
        </div>

    </section>
    """


# =============================================================================
# ПРАВАЯ КОЛОНКА — ПОЛУГОДИЕ
# =============================================================================


def _half_year_column(
    payload: dict,
) -> str:
    data = payload.get(
        "half_year_wb_plan",
        {},
    )

    available = bool(
        data.get(
            "available"
        )
    )

    gauge_html = (
        half_year_gauge_chart(
            data
        )
        if available
        else None
    )

    trajectory_html = (
            half_year_trajectory_chart(
                data
            )
            if available
            else None
        )

    remaining = number(
        data.get(
            "remaining_amount"
        )
    )

    fallback_text = (
        "Полугодовой план не рассчитан. "
        "Необходимо проверить период действия соглашения "
        "и плановые суммы по месяцам."
        if not available
        else (
            "Полугодовой блок сравнивает две разные величины: "
            "долю выполненного плана и долю прошедшего времени. "
            "Основным операционным ориентиром остаётся выполнение "
            "распределённого плана к выбранной дате."
        )
    )

    return f"""
    <section class="plans-column plans-half-year-column">
        <header class="plans-column-head">
            <div>
                <div class="plans-column-kicker">
                    СОГЛАШЕНИЕ С WILDBERRIES
                </div>

                <h2>
                    Темп полугодия
                </h2>

                <div class="plans-column-subtitle">
                    {_date_label(data.get("date_start"))}
                    —
                    {_date_label(data.get("date_finish"))}
                </div>
            </div>

            <div class="plans-column-icon">
                {icon("focus", 31)}
            </div>
        </header>

        <div class="plans-half-top">
            <div class="plans-gauge-wrap">
                {_chart_or_empty(
                    gauge_html,
                    class_name="plans-svg-chart gauge-chart",
                    message=(
                        "Нет данных для спидометра "
                        "полугодового плана."
                    ),
                )}
            </div>

            <div class="plans-half-stats">
                <div>
                    <span>
                        Полный план
                    </span>

                    <b>
                        {_money_short(
                            data.get(
                                "plan_amount"
                            )
                        )}
                    </b>
                </div>

                <div>
                    <span>
                        Выполнено
                    </span>

                    <b>
                        {_money_short(
                            data.get(
                                "fact_amount"
                            )
                        )}
                    </b>
                </div>

                <div>
                    <span>
                        Осталось
                    </span>

                    <b>
                        {_money_short(
                            remaining
                        )}
                    </b>
                </div>

                <div>
                    <span>
                        План к дате
                    </span>

                    <b>
                        {_money_short(
                            data.get(
                                "plan_to_date"
                            )
                        )}
                    </b>
                </div>

                <div>
                    <span>
                        Нужный темп
                    </span>

                    <b>
                        {_money_short(
                            data.get(
                                "required_daily_rate"
                            )
                        )}
                    </b>
                </div>
            </div>
        </div>

                {_half_year_progress(data)}

                        <div class="plans-half-trajectory-card">
                            {_chart_or_empty(
                                trajectory_html,
                                class_name="plans-svg-chart half-trajectory-chart",
                                message="Нет данных для траектории полугодия.",
                            )}
                        </div>

                        <div class="plans-editorial-copy half-copy dropcap">
                            {_editorial_text(
                                payload,
                                "half_year",
                                fallback_text,
                            )}
                        </div>

        
    </section>
    """


# =============================================================================
# СБОРКА СТРАНИЦЫ
# =============================================================================


def build_plans_page(
    payload: dict,
) -> str:
    return f"""
    <!-- =============================================================
         СТРАНИЦА — ГАЗЕТНЫЙ ПЛАНОВЫЙ РАЗВОРОТ
         ============================================================= -->

    <div class="page plans-page">
        {_masthead(payload)}

        <div class="plans-newspaper-grid">
            <div class="plans-newspaper-left">
                {_month_column(payload)}
            </div>

            <div class="plans-newspaper-right">
                {_half_year_column(payload)}
            </div>
        </div>

        {_prophet_block(payload)}

        
    </div>
    """