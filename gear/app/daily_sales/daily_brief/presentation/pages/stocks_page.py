# gear/app/daily_sales/daily_brief/presentation/pages/stocks_page.py

from __future__ import annotations

import pandas as pd

from ...helpers import (
    fmt_money,
    fmt_number,
    fmt_pct,
    number,
)
from ..components import (
    bar_chart,
    metric,
    safe,
)
from .stocks_charts import stock_map
from .stocks_health import (
    build_stock_health,
)


TITLE = "Коммерческий обзор · запасы"
SUBTITLE = "Структура · география · склады · ассортимент · стоимость"


# =============================================================================
# ОБЩИЕ ФУНКЦИИ
# =============================================================================


def _format_date(
    value,
) -> str:
    """
    Дата для пользовательского отображения.
    """

    parsed = pd.to_datetime(
        value,
        errors="coerce",
    )

    if pd.isna(parsed):
        return str(
            value
            or ""
        )

    return parsed.strftime(
        "%d.%m.%Y"
    )


def _masthead(
    payload: dict,
) -> str:
    """
    Шапка товарного разворота.
    """

    stocks = payload.get(
        "stocks",
        {},
    )

    report_date = (
        stocks.get("report_date")
        or payload.get("report_date")
    )

    return f"""
    <header class="masthead">

        <div>

            <div class="brandline">
                ТРЕНДСЕТТЕР · ТОВАРНЫЙ РАЗВОРОТ
            </div>

            <h1>
                {TITLE}
            </h1>

            <div class="mast-subtitle">
                {SUBTITLE}
            </div>

        </div>

        <div class="issue-meta">

            Снимок на
            <b>
                {safe(_format_date(report_date))}
            </b>

            <br>

            Сформирован автоматически

        </div>

    </header>
    """
    

def _fmt_stock_money(
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
# KPI
# =============================================================================


def _stock_kpis(
    data: dict,
) -> str:
    """
    Верхние четыре KPI страницы.
    """

    total_qty = number(
        data.get("total_qty")
    )

    on_hand = number(
        data.get("on_hand")
    )

    in_transit = number(
        data.get("in_transit")
    )

    products = int(
        number(
            data.get("products")
        )
    )

    warehouses = int(
        number(
            data.get("warehouses")
        )
    )

    transit_share = number(
        data.get("transit_share")
    )

    on_hand_share = (
        on_hand
        / total_qty
        * 100
        if total_qty > 0
        else 0
    )

    return f"""
    <div class="stocks-kpi-grid">

        {metric(
            "Всего товара",
            f"{fmt_number(total_qty)} шт",
            (
                f"{fmt_number(products)} NM ID"
            ),
            "stock",
        )}

        {metric(
            "На складах",
            f"{fmt_number(on_hand)} шт",
            (
                f"{fmt_pct(on_hand_share)} "
                f"· {fmt_number(warehouses)} складов"
            ),
            "warehouse",
        )}

        {metric(
            "В пути",
            f"{fmt_number(in_transit)} шт",
            "к клиенту и от клиента",
            "truck",
        )}

        {metric(
            "Доля в пути",
            fmt_pct(
                transit_share
            ),
            "от общего товарного контура",
            "map",
        )}

    </div>
    """


# =============================================================================
# АНАЛИТИЧЕСКИЙ ВЫВОД
# =============================================================================


def _stock_analysis(
    data: dict,
) -> str:
    """
    Автоматический управленческий вывод по запасам.

    Не использует заранее написанный editorial.
    Все цифры рассчитываются непосредственно из payload.
    """

    total_qty = number(
        data.get("total_qty")
    )

    in_transit = number(
        data.get("in_transit")
    )

    transit_share = number(
        data.get("transit_share")
    )

    regions = list(
        data.get("top_regions")
        or data.get("regions")
        or []
    )

    warehouses = list(
        data.get("top_warehouses")
        or []
    )

    brands = list(
        data.get("brands")
        or []
    )

    categories = list(
        data.get("categories")
        or []
    )

    sentences: list[str] = []

    # -------------------------------------------------------------------------
    # Крупнейший регион
    # -------------------------------------------------------------------------

    if regions:
        top_region = regions[0]

        region_name = (
            top_region.get("region")
            or top_region.get("name")
            or "не указан"
        )

        region_qty = number(
            top_region.get("total_qty")
        )

        region_share = (
            region_qty
            / total_qty
            * 100
            if total_qty > 0
            else 0
        )

        sentences.append(
            (
                f"Основная концентрация товарного запаса "
                f"приходится на <b>{safe(region_name)}</b> — "
                f"<b>{fmt_number(region_qty)} шт</b>, "
                f"или <b>{fmt_pct(region_share)}</b> "
                f"общего товарного контура."
            )
        )

    # -------------------------------------------------------------------------
    # Крупнейший склад + Top-3
    # -------------------------------------------------------------------------

    if warehouses:
        top_warehouse = warehouses[0]

        warehouse_name = (
            top_warehouse.get("warehouse")
            or top_warehouse.get("warehouse_name")
            or top_warehouse.get("name")
            or "не указан"
        )

        warehouse_qty = number(
            top_warehouse.get("total_qty")
        )

        warehouse_share = (
            warehouse_qty
            / total_qty
            * 100
            if total_qty > 0
            else 0
        )

        top3_qty = sum(
            number(
                row.get("total_qty")
            )
            for row in warehouses[:3]
        )

        top3_share = (
            top3_qty
            / total_qty
            * 100
            if total_qty > 0
            else 0
        )

        sentences.append(
            (
                f"Крупнейшая складская площадка — "
                f"<b>{safe(warehouse_name)}</b>: "
                f"<b>{fmt_number(warehouse_qty)} шт</b> "
                f"(<b>{fmt_pct(warehouse_share)}</b>). "
                f"На три крупнейших склада приходится "
                f"<b>{fmt_pct(top3_share)}</b> общего запаса."
            )
        )

    # -------------------------------------------------------------------------
    # Товар в пути
    # -------------------------------------------------------------------------

    if in_transit > 0:
        sentences.append(
            (
                f"В логистическом контуре находится "
                f"<b>{fmt_number(in_transit)} шт</b>, "
                f"что составляет "
                f"<b>{fmt_pct(transit_share)}</b> "
                f"от общего количества."
            )
        )

    # -------------------------------------------------------------------------
    # Крупнейший бренд
    # -------------------------------------------------------------------------

    if brands:
        top_brand = brands[0]

        brand_name = (
            top_brand.get("name")
            or top_brand.get("brand")
            or "не указан"
        )

        brand_qty = number(
            top_brand.get("total_qty")
        )

        brand_share = top_brand.get(
            "share_pct"
        )

        if brand_share is None:
            brand_share = (
                brand_qty
                / total_qty
                * 100
                if total_qty > 0
                else 0
            )

        sentences.append(
            (
                f"Наибольший вклад в структуру запаса "
                f"среди брендов формирует "
                f"<b>{safe(brand_name)}</b> — "
                f"<b>{fmt_pct(number(brand_share))}</b>."
            )
        )

    # -------------------------------------------------------------------------
    # Крупнейшая категория
    # -------------------------------------------------------------------------

    if categories:
        top_category = categories[0]

        category_name = (
            top_category.get("name")
            or top_category.get("category")
            or "не указана"
        )

        category_qty = number(
            top_category.get("total_qty")
        )

        category_share = top_category.get(
            "share_pct"
        )

        if category_share is None:
            category_share = (
                category_qty
                / total_qty
                * 100
                if total_qty > 0
                else 0
            )

        sentences.append(
            (
                f"Крупнейшая товарная категория — "
                f"<b>{safe(category_name)}</b>: "
                f"<b>{fmt_pct(number(category_share))}</b> "
                f"товарного контура."
            )
        )

    if not sentences:
        return ""

    return f"""
    <div class="stocks-analysis">

        <div class="stocks-analysis-label">
            СТРУКТУРА ЗАПАСА
        </div>

        <div class="stocks-analysis-text">
            {' '.join(sentences)}
        </div>

    </div>
    """


# =============================================================================
# КАРТА
# =============================================================================

def _stock_map_block(
    data: dict,
) -> str:
    """
    Розовая карта распределения общего запаса
    по укрупнённым регионам.

    Используется именно наша карта daily_brief,
    а НЕ точечная карта конкретных складов.
    """

    map_uri = stock_map(
        data.get(
            "regions",
            [],
        ),
        str(
            data.get(
                "report_date"
            )
            or ""
        ),
        data,
    )

    if not map_uri:
        return ""

    return f"""
    <div class="stocks-map-wrap">

        <div class="stocks-map-head">

            <div>
                <div class="stocks-block-kicker">
                    ГЕОГРАФИЯ
                </div>

                <div class="stocks-block-title">
                    Распределение товарного запаса
                </div>
            </div>

            <div class="stocks-map-caption">
                общий запас по регионам · физический остаток + товар в пути
            </div>

        </div>

        <div class="stocks-map-block">

            <img
                class="stocks-map-image"
                src="{map_uri}"
                alt="Распределение товарного запаса по регионам"
            >

        </div>

    </div>
    """


# =============================================================================
# РЕГИОНЫ И СКЛАДЫ
# =============================================================================


def _geography_rankings(
    data: dict,
) -> str:
    """
    Два рейтинга:
    - регионы;
    - конкретные склады.
    """

    total_qty = number(
        data.get("total_qty")
    )

    regions = (
        data.get("top_regions")
        or data.get("regions")
        or []
    )

    warehouses = (
        data.get("top_warehouses")
        or []
    )

    return f"""
    <div class="stocks-ranking-grid">

        <div class="stocks-ranking-card">

            <div class="stocks-ranking-head">

                <div>
                    <div class="stocks-block-kicker">
                        РЕГИОНЫ
                    </div>

                    <div class="stocks-block-title">
                        География запаса
                    </div>
                </div>

                <div class="stocks-ranking-unit">
                    доля · шт.
                </div>

            </div>

            {bar_chart(
                regions,
                "total_qty",
                "шт",
                5,
                tone="coral",
                show_share=True,
                total=total_qty,
            )}

        </div>


        <div class="stocks-ranking-card">

            <div class="stocks-ranking-head">

                <div>
                    <div class="stocks-block-kicker lilac">
                        СКЛАДЫ
                    </div>

                    <div class="stocks-block-title">
                        Крупнейшие площадки
                    </div>
                </div>

                <div class="stocks-ranking-unit">
                    доля · шт.
                </div>

            </div>

            {bar_chart(
                warehouses,
                "total_qty",
                "шт",
                5,
                tone="lilac",
                show_share=True,
                total=total_qty,
            )}

        </div>

    </div>
    """


# =============================================================================
# БРЕНДЫ И КАТЕГОРИИ
# =============================================================================


def _assortment_rankings(
    data: dict,
) -> str:
    """
    Компактная структура остатков по ассортименту.
    """

    total_qty = number(
        data.get("total_qty")
    )

    categories = (
        data.get("categories")
        or []
    )

    brands = (
        data.get("brands")
        or []
    )

    if (
        not categories
        and not brands
    ):
        return ""

    return f"""
    <div class="
        stocks-ranking-grid
        stocks-ranking-grid-secondary
    ">

        <div class="
            stocks-ranking-card
            compact
        ">

            <div class="stocks-ranking-head">

                <div>
                    <div class="stocks-block-kicker rose">
                        КАТЕГОРИИ
                    </div>

                    <div class="stocks-block-title">
                        Товарная структура
                    </div>
                </div>

                <div class="stocks-ranking-unit">
                    доля · шт.
                </div>

            </div>

            {bar_chart(
                categories,
                "total_qty",
                "шт",
                5,
                tone="rose",
                show_share=True,
                total=total_qty,
            )}

        </div>


        <div class="
            stocks-ranking-card
            compact
        ">

            <div class="stocks-ranking-head">

                <div>
                    <div class="stocks-block-kicker lilac">
                        БРЕНДЫ
                    </div>

                    <div class="stocks-block-title">
                        Концентрация запаса
                    </div>
                </div>

                <div class="stocks-ranking-unit">
                    доля · шт.
                </div>

            </div>

            {bar_chart(
                brands,
                "total_qty",
                "шт",
                5,
                tone="lilac",
                show_share=True,
                total=total_qty,
            )}

        </div>

    </div>
    """


# =============================================================================
# СТОИМОСТНАЯ ОЦЕНКА
# =============================================================================


def _cost_strip(
    data: dict,
) -> str:
    """
    Бухгалтерская и управленческая стоимость товарного контура.
    """

    accounting = number(
        data.get(
            "accounting_cost"
        )
    )

    management = number(
        data.get(
            "management_cost"
        )
    )

    delta = (
        management
        - accounting
    )

    delta_pct = (
        delta
        / abs(accounting)
        * 100
        if accounting
        else None
    )

    # Если в payload уже рассчитана разница,
    # используем её.
    if data.get("cost_delta") is not None:
        delta = number(
            data.get("cost_delta")
        )

    if data.get("cost_delta_pct") is not None:
        delta_pct = number(
            data.get("cost_delta_pct")
        )

    if delta > 0:
        delta_class = "positive"
        delta_sign = "+"

    elif delta < 0:
        delta_class = "negative"
        delta_sign = "−"

    else:
        delta_class = "neutral"
        delta_sign = ""

    if delta_pct is None:
        delta_pct_text = "нет базы"

    else:
        delta_pct_text = (
            f"{delta_sign}"
            f"{fmt_pct(abs(delta_pct))}"
        )

    return f"""
    <div class="stocks-cost-section">

        <div class="stocks-cost-head">

            <div>
                <div class="stocks-block-kicker lilac">
                    СТОИМОСТНАЯ ОЦЕНКА
                </div>

                <div class="stocks-block-title">
                    Запас в двух контурах себестоимости
                </div>
            </div>

            <div class="stocks-cost-head-note">
                включая товар в пути
            </div>

        </div>


        <div class="stocks-cost-strip">

            <div class="stocks-cost-card accounting">

                <div class="stocks-cost-label">
                    Бухгалтерская стоимость
                </div>

                <div class="stocks-cost-value">
                   {_fmt_stock_money(accounting)}
                </div>

                <div class="stocks-cost-note">
                    оценка по бухгалтерской с/с
                </div>

            </div>


            <div class="stocks-cost-card management">

                <div class="stocks-cost-label">
                    Управленческая стоимость
                </div>

                <div class="stocks-cost-value">
                    {_fmt_stock_money(management)}
                </div>

                <div class="stocks-cost-note">
                    оценка по управленческой с/с
                </div>

            </div>


            <div class="stocks-cost-card difference">

                <div class="stocks-cost-label">
                    Разница оценок
                </div>

                <div class="
                    stocks-cost-value
                    {delta_class}
                ">
                    {delta_sign}{_fmt_stock_money(abs(delta))}
                </div>

                <div class="
                    stocks-cost-note
                    {delta_class}
                ">
                    {delta_pct_text}
                    к бухгалтерской оценке
                </div>

            </div>

        </div>

    </div>
    """


# =============================================================================
# МЕТОДОЛОГИЯ
# =============================================================================


def _method_note(
    data: dict,
) -> str:
    """
    Короткая служебная подпись страницы.
    """

    report_date = _format_date(
        data.get("report_date")
    )

    used_previous = bool(
        data.get(
            "used_previous_snapshot"
        )
    )

    snapshot_note = (
        (
            "Использован последний доступный "
            f"снимок на {report_date}."
        )
        if used_previous
        else (
            f"Снимок остатков на {report_date}."
            if report_date
            else ""
        )
    )

    return f"""
    <div class="stocks-method-note">

        <span>
            {safe(snapshot_note)}
        </span>

        <span>
            Общий запас = физический остаток + товар в пути.
            Стоимость рассчитана по последней доступной
            бухгалтерской и управленческой себестоимости.
        </span>

    </div>
    """


# =============================================================================
# ПУСТАЯ СТРАНИЦА
# =============================================================================


def _empty_stocks_page(
    payload: dict,
    data: dict,
) -> str:
    reason = (
        data.get("reason")
        or "Данные товарных остатков отсутствуют."
    )

    return f"""
    <div class="page stocks-page">

        {_masthead(payload)}

        <div class="stocks-empty">

            <div class="stocks-empty-title">
                Нет данных по остаткам
            </div>

            <div class="stocks-empty-text">
                {safe(reason)}
            </div>

        </div>

    </div>
    """


# =============================================================================
# СБОРКА СТРАНИЦЫ
# =============================================================================


def build_stocks_page(
    payload: dict,
) -> str:
    """
    Товарный разворот.

    Содержит только аналитику товарного запаса.

    Происшествия здесь намеренно НЕ выводятся:
    для них будет отдельная страница incidents_page.py.
    """

    data = payload.get(
        "stocks",
        {},
    )

    if not data.get(
        "available"
    ):
        return _empty_stocks_page(
            payload,
            data,
        )

    return f"""
    <!-- =============================================================
         ТОВАРНЫЙ РАЗВОРОТ
         ============================================================= -->

    <div class="page stocks-page">

        {_masthead(payload)}

        {_stock_kpis(data)}

        {_stock_analysis(data)}

        {_stock_map_block(data)}

        {_geography_rankings(data)}

        {_assortment_rankings(data)}

        {_cost_strip(data)}

        {build_stock_health(data)}

        {_method_note(data)}

    </div>
    """