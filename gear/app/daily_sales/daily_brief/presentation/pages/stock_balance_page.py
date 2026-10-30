# gear/app/daily_sales/daily_brief/presentation/pages/stock_balance_page.py

from __future__ import annotations

import pandas as pd

from ...helpers import (
    fmt_money,
    fmt_number,
    fmt_pct,
    number,
)

from ..components import safe
from ..icons import icon

from .stocks_health import (
    build_stock_health,
)


TITLE = "Коммерческий обзор · запасы"

SUBTITLE = (
    "Товарный контур · WB · FBS · "
    "запас · стоимость · покрытие"
)


# =============================================================================
# FORMAT
# =============================================================================


def _format_date(
    value,
) -> str:

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


def _compact_qty(
    value,
) -> str:

    value = number(
        value
    )

    if abs(value) >= 1_000_000:
        return (
            f"{value / 1_000_000:.1f}"
            .replace(".", ",")
            + " млн"
        )

    if abs(value) >= 1_000:
        return (
            f"{value / 1_000:.1f}"
            .replace(".", ",")
            + " тыс."
        )

    return fmt_number(
        value
    )


# =============================================================================
# HEADER
# =============================================================================


def _masthead(
    payload: dict,
) -> str:

    data = (
        payload.get(
            "stock_balance"
        )
        or {}
    )

    report_date = (
        data.get(
            "report_date"
        )
        or payload.get(
            "report_date"
        )
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
                {safe(
                    _format_date(
                        report_date
                    )
                )}
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
    *,
    label: str,
    value: str,
    note: str,
    icon_name: str,
    tone: str,
) -> str:

    return f"""
    <div class="
        sb2-kpi
        sb2-kpi-{tone}
    ">

        <div class="sb2-kpi-top">

            <div class="sb2-kpi-label">
                {safe(label)}
            </div>

            <div class="sb2-kpi-icon">
                {icon(
                    icon_name,
                    28,
                )}
            </div>

        </div>

        <div class="sb2-kpi-value">
            {value}
        </div>

        <div class="sb2-kpi-note">
            {note}
        </div>

    </div>
    """


def _stock_kpis(
    data: dict,
) -> str:

    total_qty = number(
        data.get(
            "total_qty"
        )
    )

    wb_qty = number(
        data.get(
            "wb_qty"
        )
    )

    fbs_qty = number(
        data.get(
            "fbs_qty"
        )
    )

    transit_qty = number(
        data.get(
            "transit_qty"
        )
    )

    products = int(
        number(
            data.get(
                "products"
            )
        )
    )

    wb_share = number(
        data.get(
            "wb_share_pct"
        )
    )

    fbs_share = number(
        data.get(
            "fbs_share_pct"
        )
    )

    transit_share = number(
        data.get(
            "transit_share_pct"
        )
    )

    return f"""
    <div class="sb2-kpi-grid">

        {_kpi_card(
            label="Всего товара",
            value=(
                f"{fmt_number(total_qty)} шт"
            ),
            note=(
                f"{fmt_number(products)} NM ID "
                f"· весь товарный контур"
            ),
            icon_name="stock",
            tone="green",
        )}

        {_kpi_card(
            label="На складах WB",
            value=(
                f"{fmt_number(wb_qty)} шт"
            ),
            note=(
                f"{fmt_pct(wb_share)} "
                f"от общего запаса"
            ),
            icon_name="newspaper",
            tone="yellow",
        )}

        {_kpi_card(
            label="На FBS",
            value=(
                f"{fmt_number(fbs_qty)} шт"
            ),
            note=(
                f"{fmt_pct(fbs_share)} "
                f"от общего запаса"
            ),
            icon_name="units",
            tone="rose",
        )}

        {_kpi_card(
            label="В пути",
            value=(
                f"{fmt_number(transit_qty)} шт"
            ),
            note=(
                f"{fmt_pct(transit_share)} "
                f"· к клиенту и от клиента"
            ),
            icon_name="truck",
            tone="lilac",
        )}

    </div>
    """


# =============================================================================
# LEAD
# =============================================================================


def _stock_lead(
    data: dict,
) -> str:

    total_qty = number(
        data.get(
            "total_qty"
        )
    )

    wb_qty = number(
        data.get(
            "wb_qty"
        )
    )

    fbs_qty = number(
        data.get(
            "fbs_qty"
        )
    )

    transit_qty = number(
        data.get(
            "transit_qty"
        )
    )

    fbs_share = number(
        data.get(
            "fbs_share_pct"
        )
    )

    fbs_products = int(
        number(
            data.get(
                "fbs_products"
            )
        )
    )

    only_products = int(
        number(
            data.get(
                "fbs_only_products"
            )
        )
    )

    only_text = ""

    if only_products > 0:
        only_text = (
            f"<b>{fmt_number(only_products)} NM ID</b> "
            f"представлены только на FBS."
        )

    return f"""
    <div class="sb2-lead">

        <div class="sb2-lead-icon">
            {icon(
                "focus",
                29,
            )}
        </div>


        <div class="sb2-lead-body">

            <div class="sb2-lead-kicker">
                СТРУКТУРА ЗАПАСА
            </div>

            <div class="sb2-lead-text">

                Общий товарный контур составляет
                <b>{fmt_number(total_qty)} шт</b>.

                На складах Wildberries находится
                <b>{fmt_number(wb_qty)} шт</b>,
                на собственном складе FBS —
                <b>{fmt_number(fbs_qty)} шт</b>,
                ещё
                <b>{fmt_number(transit_qty)} шт</b>
                находятся в пути.

                FBS формирует
                <b>{fmt_pct(fbs_share)}</b>
                общего товарного запаса
                и содержит
                <b>{fmt_number(fbs_products)} NM ID</b>.

                {only_text}

            </div>

        </div>

    </div>
    """


# =============================================================================
# CONTOUR
# =============================================================================


def _stock_structure(
    data: dict,
) -> str:

    wb_share = max(
        0,
        number(
            data.get(
                "wb_share_pct"
            )
        ),
    )

    fbs_share = max(
        0,
        number(
            data.get(
                "fbs_share_pct"
            )
        ),
    )

    transit_share = max(
        0,
        number(
            data.get(
                "transit_share_pct"
            )
        ),
    )

    return f"""
    <section class="sb2-section">

        <div class="sb2-section-head">

            <div>

                <div class="sb2-kicker">
                    ТОВАРНЫЙ КОНТУР
                </div>

                <div class="sb2-title">
                    Где находится запас
                </div>

            </div>

            <div class="sb2-head-note">
                WB · FBS · логистика
            </div>

        </div>


        <div class="sb2-contour">

            <div
                class="
                    sb2-contour-part
                    sb2-contour-wb
                "
                style="
                    width:{wb_share:.4f}%;
                "
            ></div>

            <div
                class="
                    sb2-contour-part
                    sb2-contour-fbs
                "
                style="
                    width:{fbs_share:.4f}%;
                "
            ></div>

            <div
                class="
                    sb2-contour-part
                    sb2-contour-transit
                "
                style="
                    width:{transit_share:.4f}%;
                "
            ></div>

        </div>


        <div class="sb2-contour-legend">

            {_contour_legend_item(
                "Склады WB",
                data.get("wb_qty"),
                wb_share,
                "wb",
            )}

            {_contour_legend_item(
                "Собственный склад FBS",
                data.get("fbs_qty"),
                fbs_share,
                "fbs",
            )}

            {_contour_legend_item(
                "Товар в пути",
                data.get("transit_qty"),
                transit_share,
                "transit",
            )}

        </div>

    </section>
    """


def _contour_legend_item(
    label,
    qty,
    share,
    tone,
) -> str:

    return f"""
    <div class="sb2-contour-item">

        <span class="
            sb2-contour-dot
            sb2-dot-{tone}
        "></span>

        <div>

            <div class="sb2-contour-label">
                {safe(label)}
            </div>

            <div class="sb2-contour-number">

                {fmt_number(qty)} шт

                <span>
                    {fmt_pct(share)}
                </span>

            </div>

        </div>

    </div>
    """


# =============================================================================
# MINI RANKING
# =============================================================================


def _mini_ranking(
    rows: list[dict],
    *,
    name_key: str,
    value_key: str,
    total: float,
    tone: str,
    limit: int = 5,
) -> str:

    rows = list(
        rows
        or []
    )[:limit]

    if not rows:
        return """
        <div class="sb2-empty-mini">
            Нет данных
        </div>
        """

    max_value = max(
        (
            number(
                row.get(
                    value_key
                )
            )
            for row in rows
        ),
        default=0,
    )

    blocks = []

    for row in rows:

        name = (
            row.get(
                name_key
            )
            or row.get(
                "name"
            )
            or "Не указано"
        )

        value = number(
            row.get(
                value_key
            )
        )

        share = (
            value
            / total
            * 100
            if total > 0
            else 0
        )

        width = (
            value
            / max_value
            * 100
            if max_value > 0
            else 0
        )

        blocks.append(
            f"""
            <div class="sb2-rank-row">

                <div
                    class="sb2-rank-name"
                    title="{safe(name)}"
                >
                    {safe(name)}
                </div>

                <div class="sb2-rank-track">

                    <div
                        class="
                            sb2-rank-fill
                            sb2-rank-{tone}
                        "
                        style="
                            width:{width:.4f}%;
                        "
                    ></div>

                </div>

                <div class="sb2-rank-value">

                    {fmt_number(value)}

                    <span>
                        {fmt_pct(share)}
                    </span>

                </div>

            </div>
            """
        )

    return "".join(
        blocks
    )


# =============================================================================
# FBS
# =============================================================================


def _fbs_feature(
    data: dict,
) -> str:

    fbs_qty = number(
        data.get(
            "fbs_qty"
        )
    )

    fbs_share = number(
        data.get(
            "fbs_share_pct"
        )
    )

    fbs_products = int(
        number(
            data.get(
                "fbs_products"
            )
        )
    )

    only_products = int(
        number(
            data.get(
                "fbs_only_products"
            )
        )
    )

    only_qty = number(
        data.get(
            "fbs_only_qty"
        )
    )

    concentration = number(
        data.get(
            "fbs_top5_share_pct"
        )
    )

    return f"""
    <div class="sb2-fbs-feature">

        <div class="sb2-feature-head">

            <div>

                <div class="sb2-kicker rose">
                    СОБСТВЕННЫЙ СКЛАД
                </div>

                <div class="sb2-title">
                    FBS под лупой
                </div>

            </div>

            <div>
                {icon(
                    "focus",
                    29,
                )}
            </div>

        </div>


        <div class="sb2-fbs-hero">

            <div class="sb2-fbs-number">
                {fmt_number(fbs_qty)} шт
            </div>

            <div class="sb2-fbs-caption">
                физически находится
                на складе продавца
            </div>

        </div>


        <div class="sb2-fbs-stats">

            <div class="sb2-fbs-stat">

                <div class="sb2-fbs-stat-label">
                    Доля запаса
                </div>

                <div class="sb2-fbs-stat-value">
                    {fmt_pct(fbs_share)}
                </div>

            </div>


            <div class="sb2-fbs-stat">

                <div class="sb2-fbs-stat-label">
                    NM ID
                </div>

                <div class="sb2-fbs-stat-value">
                    {fmt_number(
                        fbs_products
                    )}
                </div>

            </div>


            <div class="sb2-fbs-stat">

                <div class="sb2-fbs-stat-label">
                    Только FBS
                </div>

                <div class="sb2-fbs-stat-value">
                    {fmt_number(
                        only_products
                    )} NM
                </div>

            </div>

        </div>


        <div class="sb2-fbs-copy">

            На FBS сосредоточено
            <b>{fmt_pct(fbs_share)}</b>
            всего товарного контура.

            Положительный остаток имеют
            <b>{fmt_number(fbs_products)} NM ID</b>.

            {
                (
                    f"Исключительно на FBS представлены "
                    f"<b>{fmt_number(only_products)} NM ID</b> "
                    f"в количестве "
                    f"<b>{fmt_number(only_qty)} шт</b>."
                )
                if only_products > 0
                else (
                    "Позиций, представленных "
                    "только на FBS, нет."
                )
            }

            На пять крупнейших брендов приходится
            <b>{fmt_pct(concentration)}</b>
            FBS-запаса.

        </div>

    </div>
    """


def _fbs_assortment(
    data: dict,
) -> str:

    fbs_qty = number(
        data.get(
            "fbs_qty"
        )
    )

    brands = (
        data.get(
            "fbs_brands"
        )
        or []
    )

    categories = (
        data.get(
            "fbs_categories"
        )
        or []
    )

    return f"""
    <div class="sb2-fbs-assortment">

        <div class="sb2-assortment-block">

            <div class="sb2-assortment-head">

                <div>

                    <div class="sb2-kicker lilac">
                        БРЕНДЫ FBS
                    </div>

                    <div class="sb2-mini-title">
                        Концентрация собственного склада
                    </div>

                </div>

                {icon(
                    "brand",
                    22,
                )}

            </div>

            {_mini_ranking(
                brands,
                name_key="brand",
                value_key="fbs_qty",
                total=fbs_qty,
                tone="lilac",
            )}

        </div>


        <div class="sb2-assortment-divider"></div>


        <div class="sb2-assortment-block">

            <div class="sb2-assortment-head">

                <div>

                    <div class="sb2-kicker rose">
                        КАТЕГОРИИ FBS
                    </div>

                    <div class="sb2-mini-title">
                        Что лежит на собственном складе
                    </div>

                </div>

                {icon(
                    "category",
                    22,
                )}

            </div>

            {_mini_ranking(
                categories,
                name_key="category",
                value_key="fbs_qty",
                total=fbs_qty,
                tone="rose",
            )}

        </div>

    </div>
    """


def _fbs_block(
    data: dict,
) -> str:

    return f"""
    <section class="sb2-section">

        <div class="sb2-section-head">

            <div>

                <div class="sb2-kicker">
                    FBS
                </div>

                <div class="sb2-title">
                    Управляемый запас продавца
                </div>

            </div>

            <div class="sb2-head-note">
                отдельный анализ собственного склада
            </div>

        </div>


        <div class="sb2-fbs-grid">

            {_fbs_feature(
                data
            )}

            {_fbs_assortment(
                data
            )}

        </div>

    </section>
    """


# =============================================================================
# БОЛЬШОЙ ГРАФИК БРЕНДОВ
#
# НЕ ТЁМНЫЙ:
# WB    = мягкий зелёный
# FBS   = розовый
# ПУТЬ  = сиреневый
# =============================================================================


def _brand_structure_chart(
    data: dict,
) -> str:

    rows = list(
        data.get(
            "brands"
        )
        or []
    )

    if not rows:
        return ""

    maximum = max(
        (
            number(
                row.get(
                    "total_qty"
                )
            )
            for row in rows
        ),
        default=0,
    )

    html = []

    for row in rows:

        brand = (
            row.get(
                "brand"
            )
            or "Бренд не указан"
        )

        total = number(
            row.get(
                "total_qty"
            )
        )

        wb = number(
            row.get(
                "wb_qty"
            )
        )

        fbs = number(
            row.get(
                "fbs_qty"
            )
        )

        transit = number(
            row.get(
                "transit_qty"
            )
        )

        outer_width = (
            total
            / maximum
            * 100
            if maximum > 0
            else 0
        )

        wb_inside = (
            wb
            / total
            * 100
            if total > 0
            else 0
        )

        fbs_inside = (
            fbs
            / total
            * 100
            if total > 0
            else 0
        )

        transit_inside = (
            transit
            / total
            * 100
            if total > 0
            else 0
        )

        html.append(
            f"""
            <div class="sb2-brand-row">

                <div
                    class="sb2-brand-name"
                    title="{safe(brand)}"
                >
                    {safe(brand)}
                </div>


                <div class="sb2-brand-track">

                    <div
                        class="sb2-brand-total"
                        style="
                            width:{outer_width:.4f}%;
                        "
                    >

                        <div
                            class="sb2-brand-wb"
                            style="
                                width:{wb_inside:.4f}%;
                            "
                        ></div>

                        <div
                            class="sb2-brand-fbs"
                            style="
                                width:{fbs_inside:.4f}%;
                            "
                        ></div>

                        <div
                            class="sb2-brand-transit"
                            style="
                                width:{transit_inside:.4f}%;
                            "
                        ></div>

                    </div>

                </div>


                <div class="sb2-brand-value">
                    {_compact_qty(total)}
                </div>

            </div>
            """
        )

    return f"""
    <section class="
        sb2-section
        sb2-brand-section
    ">

        <div class="sb2-section-head">

            <div>

                <div class="sb2-kicker lilac">
                    СТРУКТУРА БРЕНДОВ
                </div>

                <div class="sb2-title">
                    Как размещён запас крупнейших брендов
                </div>

            </div>

            <div class="sb2-head-note">
                длина полосы — общий запас бренда
            </div>

        </div>


        <div class="sb2-brand-chart">

            {''.join(html)}

        </div>


        <div class="sb2-brand-legend">

            <div>
                <span class="
                    sb2-brand-legend-dot
                    wb
                "></span>
                Склады WB
            </div>

            <div>
                <span class="
                    sb2-brand-legend-dot
                    fbs
                "></span>
                FBS
            </div>

            <div>
                <span class="
                    sb2-brand-legend-dot
                    transit
                "></span>
                В пути
            </div>

        </div>

    </section>
    """


# =============================================================================
# COST
# =============================================================================


def _cost_strip(
    data: dict,
) -> str:

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

    delta = number(
        data.get(
            "cost_delta"
        )
    )

    delta_pct = (
        data.get(
            "cost_delta_pct"
        )
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
        delta_pct_text = (
            "нет базы"
        )
    else:
        delta_pct_text = (
            f"{delta_sign}"
            f"{fmt_pct(abs(number(delta_pct)))}"
        )

    return f"""
    <section class="
        sb2-section
        sb2-cost-section
    ">

        <div class="sb2-section-head">

            <div>

                <div class="sb2-kicker lilac">
                    СТОИМОСТНАЯ ОЦЕНКА
                </div>

                <div class="sb2-title">
                    Запас в двух контурах себестоимости
                </div>

            </div>

            <div class="sb2-head-note">
                WB + FBS + товар в пути
            </div>

        </div>


        <div class="sb2-cost-grid">

            <div class="
                sb2-cost-card
                accounting
            ">

                <div class="sb2-cost-icon">
                    {icon(
                        "margin",
                        25,
                    )}
                </div>

                <div>

                    <div class="sb2-cost-label">
                        Бухгалтерская стоимость
                    </div>

                    <div class="sb2-cost-value">
                        {_fmt_stock_money(
                            accounting
                        )}
                    </div>

                    <div class="sb2-cost-note">
                        WB + FBS + путь
                        · бухгалтерская с/с
                    </div>

                </div>

            </div>


            <div class="
                sb2-cost-card
                management
            ">

                <div class="sb2-cost-icon">
                    {icon(
                        "price",
                        25,
                    )}
                </div>

                <div>

                    <div class="sb2-cost-label">
                        Управленческая стоимость
                    </div>

                    <div class="sb2-cost-value">
                        {_fmt_stock_money(
                            management
                        )}
                    </div>

                    <div class="sb2-cost-note">
                        WB + FBS + путь
                        · управленческая с/с
                    </div>

                </div>

            </div>


            <div class="
                sb2-cost-card
                difference
            ">

                <div class="sb2-cost-icon">
                    {icon(
                        "focus",
                        25,
                    )}
                </div>

                <div>

                    <div class="sb2-cost-label">
                        Разница оценок
                    </div>

                    <div class="
                        sb2-cost-value
                        {delta_class}
                    ">
                        {delta_sign}{
                            _fmt_stock_money(
                                abs(delta)
                            )
                        }
                    </div>

                    <div class="
                        sb2-cost-note
                        {delta_class}
                    ">
                        {delta_pct_text}
                        к бухгалтерской оценке
                    </div>

                </div>

            </div>

        </div>

    </section>
    """


# =============================================================================
# METHOD
# =============================================================================


def _method_note(
    data: dict,
) -> str:

    report_date = _format_date(
        data.get(
            "report_date"
        )
    )

    used_previous = bool(
        data.get(
            "used_previous_snapshot"
        )
    )

    if used_previous:
        snapshot = (
            "Использован последний "
            "доступный снимок на "
            f"{report_date}."
        )
    else:
        snapshot = (
            f"Снимок остатков "
            f"на {report_date}."
        )

    return f"""
    <div class="sb2-method">

        <span>
            {safe(snapshot)}
        </span>

        <span>
            Общий товарный контур =
            склад WB + FBS + товар в пути.
            Стоимость и здоровье запаса
            рассчитаны по всему контуру.
        </span>

    </div>
    """


# =============================================================================
# EMPTY
# =============================================================================


def _empty_page(
    payload: dict,
    data: dict,
) -> str:

    reason = (
        data.get(
            "reason"
        )
        or
        "Данные товарных остатков отсутствуют."
    )

    return f"""
    <div class="
        page
        stock-balance-page
    ">

        {_masthead(
            payload
        )}

        <div class="sb2-empty">

            {icon(
                "stock",
                42,
            )}

            <div class="sb2-empty-title">
                Нет данных по остаткам
            </div>

            <div class="sb2-empty-text">
                {safe(reason)}
            </div>

        </div>

    </div>
    """


# =============================================================================
# PAGE
# =============================================================================


def build_stock_balance_page(
    payload: dict,
) -> str:

    data = (
        payload.get(
            "stock_balance"
        )
        or {}
    )

    if not data.get(
        "available"
    ):
        return _empty_page(
            payload,
            data,
        )

    # build_stock_health ожидает словарь,
    # содержащий ключ health.
    health_payload = {
        "health": (
            data.get(
                "health"
            )
            or {}
        )
    }

    return f"""
    <div class="
        page
        stock-balance-page
    ">

        {_masthead(
            payload
        )}

        {_stock_kpis(
            data
        )}

        {_stock_lead(
            data
        )}

        {_stock_structure(
            data
        )}
        
        {_brand_structure_chart(
            data
            )}

        {_fbs_block(
            data
        )}


        {_cost_strip(
            data
        )}

        {build_stock_health(
            health_payload
        )}

        {_method_note(
            data
        )}

    </div>
    """