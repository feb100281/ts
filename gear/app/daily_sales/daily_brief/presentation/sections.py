# gear/app/daily_sales/daily_brief/presentation/sections.py
from __future__ import annotations

import pandas as pd

from ..helpers import (
    fmt_money,
    fmt_number,
    number,
)
from .charts import (
    daily_qty_price_scatter,
    sales_12m_chart,

)
from .components import (
    bar_chart,
    prose,
    safe,
    section,
)
from .icons import icon



TITLE = "Коммерческий обзор"
SUBTITLE = "Продажи · спрос · цена · план · запасы"

def format_date(
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


def masthead(
    payload: dict,
    page_label: str = "ЕЖЕДНЕВНЫЙ ВЫПУСК",
) -> str:
    return f'''
    <header class="masthead">
        <div>
            <div class="brandline">
                ТРЕНДСЕТТЕР · {safe(page_label)}
            </div>
            <h1>{TITLE}</h1>
            <div class="mast-subtitle">{SUBTITLE}</div>
        </div>
        <div class="issue-meta">
            Выпуск за <b>{safe(payload.get("report_date"))}</b><br>
            Сформирован автоматически
        </div>
    </header>
    '''



def quality(payload: dict) -> str:
    returns = payload.get("sales", {}).get("return_categories", [])
    body = prose(
        payload.get("editorial", {}).get("quality", ""),
        True,
    )

    if returns:
        body += (
            '<div class="mini-title">'
            "Категории с наибольшей суммой возвратов"
            "</div>"
            + bar_chart(
                returns,
                "returns_amount",
                "₽",
                5,
            )
        )

    return section(
        "КАЧЕСТВО ПРОДАЖ",
        "Маржа и возвраты",
        body,
        "Где результат требует дополнительной проверки",
        "returns",
    )


def price_analysis(payload: dict) -> str:
    sales = payload.get("sales", {})
    daily_chart = daily_qty_price_scatter(
        sales.get("daily_price_rows", [])
    )
    monthly_chart = sales_12m_chart(
        sales.get("monthly_price_rows", [])
    )

    body = prose(
        payload.get("editorial", {}).get("price", ""),
        True,
    )

    if monthly_chart:
        body += (
            f'<img class="chart-image wide" '
            f'src="{monthly_chart}">'
        )

    if daily_chart:
        body += (
            f'<img class="chart-image wide" '
            f'src="{daily_chart}">'
        )

    body += '''
    <div class="analysis-notes">
        <div>
            <b>Как читать диаграмму</b>
            <p>
                Каждая точка — один день. Движение вправо означает рост
                количества проданных единиц, движение вверх — повышение
                средней цены. Линия показывает общее направление связи.
            </p>
        </div>
        <div>
            <b>Что проверить в выбросах</b>
            <p>
                Отдельно изучите дни, удалённые от основной группы:
                там могли действовать акции, измениться товарный микс,
                возникнуть крупные возвраты или закончиться наличие лидеров.
            </p>
        </div>
    </div>
    '''

    return section(
        "СПРОС И ЦЕНА",
        "Что двигало выручку",
        body,
        "Количество продаж и средняя цена рассматриваются вместе",
        "price",
        "feature",
    )





def recommendations(payload: dict) -> str:
    cards = "".join(
        f'''
        <div class="recommendation {safe(item.get("level"))}">
            <b>{safe(item.get("title"))}</b>
            <div>{safe(item.get("text"))}</div>
        </div>
        '''
        for item in payload.get("recommendations", [])
    )

    return section(
        "ФОКУС НА СЕГОДНЯ",
        "Что сделать после прочтения",
        cards,
        "Автоматические рекомендации по найденным отклонениям",
        "focus",
    )
    
    
def incidents_section(
    payload: dict,
) -> str:
    """
    Компактный газетный блок происшествий.

    Раздел полностью скрывается, если на дату выпуска
    зарегистрированных происшествий нет.
    """

    incidents = payload.get(
        "incidents",
        {},
    )

    events = incidents.get(
        "events",
        [],
    ) or []

    if (
        not incidents.get("available")
        or not events
    ):
        return ""

    def incident_metric(
        label: str,
        value: str,
        note: str,
        icon_name: str,
        tone: str = "",
    ) -> str:
        """
        Компактная метрика специально для блока происшествий.

        Не использует общий component metric(), потому что
        обычные KPI-карточки слишком крупные для газетного блока.
        """

        return f"""
        <div class="incident-kpi {safe(tone)}">
            <div class="incident-kpi-icon">
                {icon(icon_name, 27)}
            </div>

            <div class="incident-kpi-content">
                <div class="incident-kpi-label">
                    {safe(label)}
                </div>

                <div class="incident-kpi-value">
                    {safe(value)}
                </div>

                <div class="incident-kpi-note">
                    {safe(note)}
                </div>
            </div>
        </div>
        """

    cards: list[str] = []

    for event in events:
        warehouse_name = safe(
            event.get(
                "warehouse_name",
                "Склад не указан",
            )
        )

        title = safe(
            event.get(
                "title",
                "Происшествие",
            )
        )

        status = safe(
            event.get(
                "status",
                "Происшествие",
            )
        )

        event_date = format_date(
            event.get("date")
        )

        requested_snapshot_date = format_date(
            event.get(
                "requested_snapshot_date"
            )
        )

        effective_snapshot_date = format_date(
            event.get(
                "effective_date"
            )
        )

        snapshot_date = (
            effective_snapshot_date
            or requested_snapshot_date
        )

        description = safe(
            event.get(
                "description",
                "",
            )
        )

        on_hand = number(
            event.get("on_hand")
        )

        nm_count = number(
            event.get("nm_count")
        )

        accounting_cost = number(
            event.get(
                "accounting_cost"
            )
        )

        management_cost = number(
            event.get(
                "management_cost"
            )
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

        # --------------------------------------------------------------
        # Левая колонка с датами
        # --------------------------------------------------------------

        dates_html = f"""
        <div class="incident-dates">
            <div class="incident-date-row">
                <div class="incident-date-icon">
                    {icon("calendar", 21)}
                </div>

                <div>
                    <div class="incident-date-label">
                        Дата события
                    </div>

                    <div class="incident-date-value">
                        {safe(event_date or "не указана")}
                    </div>
                </div>
            </div>

            <div class="incident-date-row">
                <div class="incident-date-icon">
                    {icon("snapshot", 21)}
                </div>

                <div>
                    <div class="incident-date-label">
                        Снимок остатков
                    </div>

                    <div class="incident-date-value">
                        на конец {safe(snapshot_date or "нет данных")}
                    </div>
                </div>
            </div>
        </div>
        """

        # --------------------------------------------------------------
        # Основное описание
        # --------------------------------------------------------------

        description_html = f"""
        <div class="incident-event-description">
            <p>
                {description}
            </p>

            <p>
                Оценка ниже рассчитана по физическому товарному
                остатку на конец календарного дня,
                предшествующего происшествию.
            </p>

            <p>
                Позиции в пути к клиенту и от клиента
                в расчёт не включены.
            </p>
        </div>
        """

        # --------------------------------------------------------------
        # Метрики
        # --------------------------------------------------------------

        if on_hand > 0:
            metrics_html = f"""
            <div class="incident-kpi-row">
                {incident_metric(
                    label="Физический остаток",
                    value=f"{fmt_number(on_hand)} шт",
                    note=f"{fmt_number(nm_count)} NM ID",
                    icon_name="stock",
                    tone="stock-tone",
                )}

                {incident_metric(
                    label="Бухгалтерская с/с",
                    value=fmt_money(accounting_cost),
                    note="предварительная оценка",
                    icon_name="revenue",
                    tone="accounting-tone",
                )}

                {incident_metric(
                    label="Управленческая с/с",
                    value=fmt_money(management_cost),
                    note="предварительная оценка",
                    icon_name="margin",
                    tone="management-tone",
                )}
            </div>
            """

        else:
            metrics_html = """
            <div class="incident-no-stock">
                По историческому снимку физический товарный
                остаток на складе отсутствовал.
                Стоимостная оценка не рассчитывается.
            </div>
            """

        # --------------------------------------------------------------
        # Примечание о недостающей себестоимости
        # --------------------------------------------------------------

        missing_cost_parts = []

        if no_accounting_cost_qty > 0:
            missing_cost_parts.append(
                "без бухгалтерской себестоимости — "
                f"<b>{fmt_number(no_accounting_cost_qty)} шт</b>"
            )

        if no_management_cost_qty > 0:
            missing_cost_parts.append(
                "без управленческой себестоимости — "
                f"<b>{fmt_number(no_management_cost_qty)} шт</b>"
            )

        missing_cost_html = ""

        if missing_cost_parts:
            missing_cost_html = f"""
            <div class="incident-info-note">
                <div class="incident-note-symbol">i</div>

                <div>
                    Часть физического остатка не вошла
                    в соответствующую стоимостную оценку:
                    {"; ".join(missing_cost_parts)}.
                </div>
            </div>
            """

        # --------------------------------------------------------------
        # Методологическое предупреждение
        # --------------------------------------------------------------

        disclaimer_html = """
        <div class="incident-risk-note">
            <div class="incident-risk-symbol">!</div>

            <div>
                Указанная стоимость не является подтверждённым
                размером ущерба. Это предварительная оценка
                товарного остатка, который физически находился
                на складе до события и потенциально мог оказаться
                в зоне риска.
            </div>
        </div>
        """

        cards.append(
            f"""
            <article class="incident-event">
                <header class="incident-event-head">
                    <div class="incident-event-main">
                        <div class="incident-fire-icon">
                            {icon("fire", 30)}
                        </div>

                        <div>
                            <div class="incident-warehouse-name">
                                {warehouse_name}
                            </div>

                            <div class="incident-event-meta">
                                {title}
                                <span>·</span>
                                {safe(event_date)}
                            </div>
                        </div>
                    </div>

                    <div class="incident-status">
                        {status}
                    </div>
                </header>

                <div class="incident-event-details">
                    {dates_html}
                    {description_html}
                </div>

                {metrics_html}

                {missing_cost_html}

                {disclaimer_html}
            </article>
            """
        )

    count = len(events)

    return f"""
    <section class="section incidents-section">
        <header class="section-head incident-section-head">
            <div>
                <div class="kicker">
                    ПРОИСШЕСТВИЯ НА СКЛАДАХ
                </div>

                <h2>
                    События, требующие внимания
                </h2>

                <div class="section-subtitle">
                    Зафиксировано событий: {count}
                </div>
            </div>

            <div class="incident-header-icon">
                {icon("fire", 34)}
            </div>
        </header>

        <div class="incident-method-note">
            <div class="incident-note-symbol">i</div>

            <div>
                В выпуск включены только происшествия,
                фактическая дата которых совпадает с датой отчёта.
                Оценка выполнена по физическому остатку
                на конец предшествующего календарного дня.
                Товары в пути в расчёт не включены.
            </div>
        </div>

        {''.join(cards)}
    </section>
    """