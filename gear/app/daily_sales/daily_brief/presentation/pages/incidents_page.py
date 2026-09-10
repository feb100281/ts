# gear/app/daily_sales/daily_brief/presentation/pages/incidents_page.py

from __future__ import annotations

import pandas as pd

from ...helpers import (
    fmt_money,
    fmt_number,
    number,
)
from ..components import safe
from ..icons import icon


TITLE = "Происшествия на складах"
SUBTITLE = "События · товарный остаток · предварительная оценка риска"


# =============================================================================
# ФОРМАТИРОВАНИЕ
# =============================================================================


def _format_date(
    value,
) -> str:
    parsed = pd.to_datetime(
        value,
        errors="coerce",
    )

    if pd.isna(parsed):
        return ""

    return parsed.strftime(
        "%d.%m.%Y"
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


# =============================================================================
# ШАПКА
# =============================================================================


def _masthead(
    payload: dict,
    count: int,
) -> str:
    report_date = _format_date(
        payload.get("report_date")
    )

    return f"""
    <header class="masthead incidents-page-masthead">

        <div>

            <div class="brandline">
                ТРЕНДСЕТТЕР · КОНТРОЛЬ СОБЫТИЙ
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
                {safe(report_date)}
            </b>

            <br>

            Событий:
            <b>
                {fmt_number(count)}
            </b>

        </div>

    </header>
    """


# =============================================================================
# KPI
# =============================================================================


def _summary(
    events: list[dict],
) -> str:
    warehouses = {
        str(
            event.get("warehouse_name")
            or "Склад не указан"
        )
        for event in events
    }

    total_on_hand = sum(
        number(
            event.get("on_hand")
        )
        for event in events
    )

    total_nm = sum(
        number(
            event.get("nm_count")
        )
        for event in events
    )

    accounting_cost = sum(
        number(
            event.get("accounting_cost")
        )
        for event in events
    )

    management_cost = sum(
        number(
            event.get("management_cost")
        )
        for event in events
    )

    return f"""
    <div class="incidents-summary">

        <div class="incidents-summary-card danger">

            <div class="incidents-summary-label">
                Зафиксировано событий
            </div>

            <div class="incidents-summary-value">
                {fmt_number(len(events))}
            </div>

            <div class="incidents-summary-note">
                на дату отчёта
            </div>

        </div>


        <div class="incidents-summary-card">

            <div class="incidents-summary-label">
                Затронуто складов
            </div>

            <div class="incidents-summary-value">
                {fmt_number(len(warehouses))}
            </div>

            <div class="incidents-summary-note">
                уникальных площадок
            </div>

        </div>


        <div class="incidents-summary-card">

            <div class="incidents-summary-label">
                Физический остаток
            </div>

            <div class="incidents-summary-value">
                {fmt_number(total_on_hand)} шт
            </div>

            <div class="incidents-summary-note">
                {fmt_number(total_nm)} NM ID
            </div>

        </div>


        <div class="incidents-summary-card accounting">

            <div class="incidents-summary-label">
                Бухгалтерская оценка
            </div>

            <div class="incidents-summary-value">
                {_fmt_compact_money(accounting_cost)}
            </div>

            <div class="incidents-summary-note">
                предварительная стоимость
            </div>

        </div>


        <div class="incidents-summary-card management">

            <div class="incidents-summary-label">
                Управленческая оценка
            </div>

            <div class="incidents-summary-value">
                {_fmt_compact_money(management_cost)}
            </div>

            <div class="incidents-summary-note">
                предварительная стоимость
            </div>

        </div>

    </div>
    """


# =============================================================================
# МЕТОДОЛОГИЯ
# =============================================================================


def _method_note() -> str:
    return """
    <div class="incidents-method">

        <div class="incidents-method-icon">
            i
        </div>

        <div>
            В выпуск включены только происшествия,
            фактическая дата которых совпадает с датой отчёта.
            Оценка товарного контура выполнена по физическому
            остатку на конец предшествующего календарного дня.
            Товар в пути в расчёт не включается.
        </div>

    </div>
    """


# =============================================================================
# МЕТРИКА ОДНОГО СОБЫТИЯ
# =============================================================================


def _incident_metric(
    label: str,
    value: str,
    note: str,
    *,
    tone: str = "",
) -> str:
    return f"""
    <div class="incident-page-metric {safe(tone)}">

        <div class="incident-page-metric-label">
            {safe(label)}
        </div>

        <div class="incident-page-metric-value">
            {safe(value)}
        </div>

        <div class="incident-page-metric-note">
            {safe(note)}
        </div>

    </div>
    """


# =============================================================================
# ОДНО СОБЫТИЕ
# =============================================================================


def _event_card(
    event: dict,
    index: int,
) -> str:
    warehouse_name = safe(
        event.get("warehouse_name")
        or "Склад не указан"
    )

    title = safe(
        event.get("title")
        or "Происшествие"
    )

    status = safe(
        event.get("status")
        or "Зафиксировано"
    )

    event_date = _format_date(
        event.get("date")
    )

    requested_snapshot_date = _format_date(
        event.get(
            "requested_snapshot_date"
        )
    )

    effective_snapshot_date = _format_date(
        event.get(
            "effective_date"
        )
    )

    snapshot_date = (
        effective_snapshot_date
        or requested_snapshot_date
    )

    description = safe(
        event.get("description")
        or ""
    )

    on_hand = number(
        event.get("on_hand")
    )

    nm_count = number(
        event.get("nm_count")
    )

    accounting_cost = number(
        event.get("accounting_cost")
    )

    management_cost = number(
        event.get("management_cost")
    )

    no_accounting_cost_qty = int(
        number(
            event.get(
                "no_accounting_cost_qty"
            )
        )
    )

    no_management_cost_qty = int(
        number(
            event.get(
                "no_management_cost_qty"
            )
        )
    )

    # -------------------------------------------------------------------------
    # Метрики
    # -------------------------------------------------------------------------

    if on_hand > 0:
        metrics_html = f"""
        <div class="incident-page-metrics">

            {_incident_metric(
                "Физический остаток",
                f"{fmt_number(on_hand)} шт",
                f"{fmt_number(nm_count)} NM ID",
                tone="stock",
            )}

            {_incident_metric(
                "Бухгалтерская с/с",
                _fmt_compact_money(
                    accounting_cost
                ),
                "предварительная оценка",
                tone="accounting",
            )}

            {_incident_metric(
                "Управленческая с/с",
                _fmt_compact_money(
                    management_cost
                ),
                "предварительная оценка",
                tone="management",
            )}

        </div>
        """

    else:
        metrics_html = """
        <div class="incident-page-no-stock">
            По историческому снимку физический товарный
            остаток на складе отсутствовал.
            Стоимостная оценка не рассчитывается.
        </div>
        """

    # -------------------------------------------------------------------------
    # Неполная себестоимость
    # -------------------------------------------------------------------------

    missing = []

    if no_accounting_cost_qty > 0:
        missing.append(
            (
                "без бухгалтерской себестоимости — "
                f"<b>{fmt_number(no_accounting_cost_qty)} шт</b>"
            )
        )

    if no_management_cost_qty > 0:
        missing.append(
            (
                "без управленческой себестоимости — "
                f"<b>{fmt_number(no_management_cost_qty)} шт</b>"
            )
        )

    missing_html = ""

    if missing:
        missing_html = f"""
        <div class="incident-page-info">

            <div class="incident-page-info-symbol">
                i
            </div>

            <div>
                Часть физического остатка не вошла
                в соответствующую стоимостную оценку:
                {'; '.join(missing)}.
            </div>

        </div>
        """

    # -------------------------------------------------------------------------
    # Карточка
    # -------------------------------------------------------------------------

    return f"""
    <article class="incident-page-event">

        <div class="incident-page-event-number">
            {index:02d}
        </div>


        <header class="incident-page-event-head">

            <div class="incident-page-event-main">

                <div class="incident-page-fire">
                    {icon("fire", 31)}
                </div>

                <div>

                    <div class="incident-page-warehouse">
                        {warehouse_name}
                    </div>

                    <div class="incident-page-event-title">
                        {title}
                    </div>

                </div>

            </div>


            <div class="incident-page-status">
                {status}
            </div>

        </header>


        <div class="incident-page-event-body">

            <div class="incident-page-dates">

                <div class="incident-page-date">

                    <div class="incident-page-date-label">
                        Дата события
                    </div>

                    <div class="incident-page-date-value">
                        {safe(event_date or "не указана")}
                    </div>

                </div>


                <div class="incident-page-date">

                    <div class="incident-page-date-label">
                        Снимок остатков
                    </div>

                    <div class="incident-page-date-value">
                        {(
                            "на конец "
                            + safe(snapshot_date)
                            if snapshot_date
                            else "нет данных"
                        )}
                    </div>

                </div>

            </div>


            <div class="incident-page-description">

                <div class="incident-page-description-label">
                    Что произошло
                </div>

                <div class="incident-page-description-text">
                    {
                        description
                        or "Описание события не указано."
                    }
                </div>

            </div>

        </div>


        {metrics_html}

        {missing_html}


        <div class="incident-page-warning">

            <div class="incident-page-warning-symbol">
                !
            </div>

            <div>
                Указанная стоимость не является подтверждённым
                размером ущерба. Это предварительная оценка
                товарного остатка, который физически находился
                на складе до события и потенциально мог оказаться
                в зоне риска.
            </div>

        </div>

    </article>
    """


# =============================================================================
# СТРАНИЦА
# =============================================================================


def build_incidents_page(
    payload: dict,
) -> str:
    """
    Отдельная страница происшествий.

    ВАЖНО:
    если событий нет, возвращает пустую строку.
    Поэтому отдельный PDF-лист не создаётся.
    """

    incidents = payload.get(
        "incidents",
        {},
    )

    events = (
        incidents.get("events")
        or []
    )

    # =========================================================================
    # НЕТ ПРОИСШЕСТВИЙ -> НЕТ СТРАНИЦЫ
    # =========================================================================

    if (
        not incidents.get("available")
        or not events
    ):
        return ""

    cards = "".join(
        _event_card(
            event,
            index,
        )
        for index, event in enumerate(
            events,
            start=1,
        )
    )

    return f"""
    <!-- =============================================================
         СТРАНИЦА — ПРОИСШЕСТВИЯ НА СКЛАДАХ
         ============================================================= -->

    <div class="page incidents-page">

        {_masthead(
            payload,
            len(events),
        )}

        {_summary(events)}

        {_method_note()}

        <div class="incidents-page-list">
            {cards}
        </div>

        <div class="incidents-page-footer">

            <span>
                Предварительная оценка товарного остатка
                до события
            </span>

            <span>
                Товары в пути исключены
            </span>

        </div>

    </div>
    """