# gear/app/daily_sales/pricing_strategy/layout.py
"""
ИНТЕРФЕЙС ЦЕНОВОГО АНАЛИЗА.

Структура экрана сверху вниз повторяет порядок принятия решения:

    1. что вообще происходит          — плашка с датами и охватом
    2. насколько всё плохо / хорошо   — плитки KPI
    3. где именно                     — графики
    4. в каком бренде и категории     — верхняя таблица
    5. какой конкретно артикул        — нижняя таблица
    6. что с ним делать               — карточка товара по клику

Отдельно, всегда под рукой: кнопка «Как это считается» —
полная методика без необходимости идти к аналитику.
"""

from __future__ import annotations

import pandas as pd
import dash_mantine_components as dmc
from dash import dcc

from .charts import pricing_charts_section
from .config import (
    BODY_ID,
    CLOSE_BTN_ID,
    DOWNLOAD_ID,
    EXPORT_EXCEL_ID,
    EXPORT_PRODUCT_ID,
    EXPORT_CLICKS_ID,
    EXPORT_STATUS_ID,
    EXPORT_LOSS_ID,
    EXPORT_WB_PRICES_ID,
    EXPORT_ZIP_ID,
    METHOD_BTN_ID,
    METHOD_DRAWER_ID,
    MODAL_ID,
    OPEN_BTN_ID,
    PRODUCT_DETAIL_ID,
    RISK_FILTER_ID,
    SCOPE_LABEL_ID,
    SHOW_ALL_BTN_ID,
    STORE_ID,
    TARGET_MARGIN_PCT,
)
from .grids import portfolio_grid, products_grid
from .theme import (
    DANGER,
    INK,
    LINE,
    MUTED,
    PRIMARY,
    SUCCESS,
    SURFACE,
    WARNING,
)
from .methodology import methodology_sections


# ============================================================
# ФОРМАТИРОВАНИЕ
# ============================================================

def records(frame):
    """DataFrame -> список словарей, пригодный для dcc.Store."""

    if frame is None or frame.empty:
        return []

    work = frame.astype(object).where(
        pd.notna(frame),
        None,
    )

    rows = work.to_dict("records")

    for row in rows:
        for key, value in list(row.items()):

            if (
                value is not None
                and hasattr(value, "isoformat")
                and not isinstance(value, str)
            ):
                try:
                    row[key] = value.isoformat()
                except Exception:
                    pass

    return rows


# обратная совместимость: имя использовалось в старой версии
_records = records


def fmt_number(value, digits=0):
    try:
        value = float(value or 0)
    except (TypeError, ValueError):
        value = 0.0

    return f"{value:,.{digits}f}".replace(",", " ")


def fmt_money(value):
    return f"{fmt_number(value)} ₽"


_fmt_number = fmt_number
_fmt_money = fmt_money


# ============================================================
# ПЛИТКА KPI
# ============================================================

TONES = {
    "neutral": INK,
    "danger": DANGER,
    "warning": WARNING,
    "success": SUCCESS,
    "primary": PRIMARY,
}


def _metric_card(
    *,
    label,
    value,
    tone="neutral",
    note=None,
    tooltip=None,
):
    """
    Плитка показателя.

    Все плитки одной высоты и одной структуры: подпись,
    крупное число, пояснение в две строки. Разной высоты
    они получались раньше из-за того, что пояснение
    переносилось на вторую строку не у всех.

    Цветом выделено только число и только там, где это
    сигнал. Остальное — нейтральное.
    """

    color = TONES.get(tone, INK)

    card = dmc.Card(
        withBorder=True,
        radius="md",
        padding="md",
        style={
            "height": "128px",
            "backgroundColor": SURFACE,
            "borderColor": LINE,
            "borderLeft": (
                f"3px solid {color}"
                if tone != "neutral"
                else f"3px solid {LINE}"
            ),
        },
        children=dmc.Stack(
            gap=0,
            justify="space-between",
            style={"height": "100%"},
            children=[
                # Цвета задаём через style, а не через проп c:
                # Mantine парсит c как цвет темы и падает на
                # неожиданных значениях. CSS ничего не парсит.
                dmc.Text(
                    label,
                    size="11px",
                    fw=600,
                    tt="uppercase",
                    lineClamp=1,
                    style={
                        "letterSpacing": "0.05em",
                        "color": MUTED,
                    },
                ),

                dmc.Text(
                    value,
                    fw=700,
                    style={
                        "fontSize": "26px",
                        "lineHeight": "1.1",
                        "whiteSpace": "nowrap",
                        "overflow": "hidden",
                        "textOverflow": "ellipsis",
                        "color": color,
                    },
                ),

                dmc.Text(
                    note or "",
                    size="11px",
                    lineClamp=2,
                    style={
                        "minHeight": "30px",
                        "lineHeight": "1.35",
                        "color": MUTED,
                    },
                ),
            ],
        ),
    )

    if not tooltip:
        return card

    return dmc.Tooltip(
        label=tooltip,
        multiline=True,
        w=320,
        withArrow=True,
        openDelay=300,
        children=card,
    )


# ============================================================
# МЕТОДИКА
# ============================================================

def _methodology_drawer():
    """
    Панель «Как это считается».

    Содержимое собирается из methodology.py — того же
    источника, что идёт в Excel и README. Разъезжаться
    версиям методики просто негде.
    """

    blocks = []

    for section in methodology_sections():

        items = [
            dmc.Box(
                mb=10,
                children=[
                    dmc.Text(
                        term,
                        size="sm",
                        fw=700,
                    ),
                    dmc.Text(
                        text,
                        size="sm",
                        c="dimmed",
                        style={"lineHeight": "1.5"},
                    ),
                ],
            )
            for term, text in section["items"]
        ]

        if section["formula"]:
            items.append(
                dmc.Code(
                    section["formula"],
                    block=True,
                    style={
                        "whiteSpace": "pre-wrap",
                        "fontSize": "12px",
                    },
                )
            )

        blocks.append(
            dmc.AccordionItem(
                value=section["key"],
                children=[
                    dmc.AccordionControl(
                        dmc.Text(
                            section["title"],
                            fw=700,
                        )
                    ),
                    dmc.AccordionPanel(
                        [
                            dmc.Text(
                                section["lead"],
                                size="sm",
                                mb=12,
                                style={
                                    "lineHeight": "1.55",
                                },
                            ),
                            *items,
                        ]
                    ),
                ],
            )
        )

    return dmc.Drawer(
        id=METHOD_DRAWER_ID,
        opened=False,
        position="right",
        size="42%",
        padding="lg",
        zIndex=10001,
        title=dmc.Text(
            "Как считается этот отчёт",
            fw=800,
            size="lg",
        ),
        children=dmc.ScrollArea(
            h="calc(100vh - 120px)",
            type="auto",
            children=dmc.Accordion(
                multiple=True,
                value=[
                    "purpose",
                    "breakeven",
                ],
                children=blocks,
            ),
        ),
    )


# ============================================================
# ВЕРХНЯЯ ПАНЕЛЬ
# ============================================================

def _download_menu():
    """
    Меню выгрузок.

    Каждый пункт — документ, который реально используют:
    один для разбора, один для действия, один для загрузки
    цен, один чтобы отдать целиком.
    """

    def item(label, description, component_id):
        return dmc.MenuItem(
            dmc.Box(
                children=[
                    dmc.Text(label, size="sm", fw=600),
                    dmc.Text(
                        description,
                        size="xs",
                        c="dimmed",
                    ),
                ]
            ),
            id=component_id,
            n_clicks=0,
        )

    return dmc.Menu(
        trigger="click",
        position="bottom-end",
        withArrow=True,
        zIndex=10002,
        children=[
            dmc.MenuTarget(
                dmc.Button(
                    "Скачать",
                    variant="filled",
                    color="indigo",
                    radius="md",
                )
            ),
            dmc.MenuDropdown(
                [
                    dmc.MenuLabel("Документы"),

                    item(
                        "Ценовые решения, Excel",
                        "Полный отчёт: сводка, товары, сценарии, методика",
                        EXPORT_EXCEL_ID,
                    ),

                    item(
                        "Продаём в убыток, Excel",
                        "Короткий список к действию: цена ниже минимальной",
                        EXPORT_LOSS_ID,
                    ),

                    dmc.MenuDivider(),
                    dmc.MenuLabel("Для загрузки"),

                    item(
                        "Новые цены, CSV",
                        "nmID и цена к установке — для загрузки на WB",
                        EXPORT_WB_PRICES_ID,
                    ),

                    item(
                        "Разбор выбранного товара, Excel",
                        "Решение, сценарии и история по одному NM ID",
                        EXPORT_PRODUCT_ID,
                    ),

                    dmc.MenuDivider(),

                    item(
                        "Всё вместе, ZIP",
                        "Все файлы и README с методикой",
                        EXPORT_ZIP_ID,
                    ),
                ]
            ),
        ],
    )


def pricing_strategy_controls():
    """Кнопка на странице + модальное окно + панель методики."""

    return dmc.Group(
        gap="xs",
        children=[
            dmc.Button(
                "Управление ценами",
                id=OPEN_BTN_ID,
                radius="md",
                variant="filled",
                color="indigo",
                leftSection=dmc.Text("₽", fw=900),
            ),

            dcc.Store(id=STORE_ID),
            dcc.Store(id=EXPORT_CLICKS_ID),
            dcc.Download(id=DOWNLOAD_ID),

            _methodology_drawer(),

            dmc.Modal(
                id=MODAL_ID,
                opened=False,
                withCloseButton=False,
                fullScreen=True,
                padding="md",
                zIndex=10000,
                children=[
                    dmc.Group(
                        justify="space-between",
                        align="center",
                        mb="sm",
                        children=[
                            dmc.Box(
                                children=[
                                    dmc.Title(
                                        "Управление ценами и маржой",
                                        order=2,
                                        fw=800,
                                    ),
                                    dmc.Text(
                                        "Остатки → спрос → минимальная цена → "
                                        "цена к установке",
                                        size="sm",
                                        c="dimmed",
                                    ),
                                ]
                            ),

                            dmc.Group(
                                gap="xs",
                                children=[
                                    dmc.Button(
                                        "Как это считается",
                                        id=METHOD_BTN_ID,
                                        radius="md",
                                        variant="light",
                                        color="yellow",
                                        leftSection=dmc.Text(
                                            "💡",
                                            size="lg",
                                        ),
                                    ),

                                    _download_menu(),

                                    dmc.Button(
                                        "Закрыть",
                                        id=CLOSE_BTN_ID,
                                        radius="md",
                                        color="gray",
                                        variant="subtle",
                                    ),
                                ],
                            ),
                        ],
                    ),

                    # Сообщения о выгрузках. Пусто, пока
                    # ничего не скачивают.
                    dmc.Box(
                        id=EXPORT_STATUS_ID,
                        mb="xs",
                    ),

                    dmc.Divider(mb="md"),

                    dmc.Box(
                        id=BODY_ID,
                        children=dmc.Text(
                            "Нажмите «Управление ценами», "
                            "чтобы построить анализ.",
                            c="dimmed",
                        ),
                    ),
                ],
            ),
        ],
    )


# ============================================================
# ТЕЛО ОТЧЁТА
# ============================================================

def _section_title(title, subtitle, extra=None):
    return dmc.Group(
        justify="space-between",
        align="flex-end",
        children=[
            dmc.Box(
                children=[
                    dmc.Title(title, order=3, fw=800),
                    dmc.Text(
                        subtitle,
                        size="sm",
                        c="dimmed",
                        mt=2,
                    ),
                ]
            ),
            extra or dmc.Box(),
        ],
    )


def _risk_filter():
    """
    Быстрые срезы вместо ручной фильтрации таблицы.

    Формулировки — на языке решения, а не на языке модели.
    """

    return dmc.SegmentedControl(
        id=RISK_FILTER_ID,
        value="all",
        radius="md",
        size="xs",
        data=[
            {"label": "Все товары", "value": "all"},
            {"label": "Продаём в убыток", "value": "loss"},
            {"label": "На грани", "value": "risk"},
            {"label": "Распродажа", "value": "clearance"},
            {"label": "Можно повышать", "value": "raise"},
        ],
    )


def build_pricing_body(analysis):

    rec = analysis["recommendations"]
    portfolio = analysis["portfolio"]
    summary = analysis.get("summary", {})

    if rec is None or rec.empty:
        return dmc.Alert(
            title="Нет данных",
            color="yellow",
            radius="md",
            children=(
                "Для выбранных фильтров нет товаров с остатком "
                "WB + FBS + в пути."
            ),
        )

    report_date = analysis["report_date"]
    wb_date = analysis.get("wb_date")
    fbs_date = analysis.get("fbs_date")

    stale = (
        (wb_date is not None and wb_date < report_date)
        or (fbs_date is not None and fbs_date < report_date)
    )

    wb_label = (
        wb_date.strftime("%d.%m.%Y")
        if wb_date
        else "нет данных"
    )

    fbs_label = (
        fbs_date.strftime("%d.%m.%Y")
        if fbs_date
        else "нет данных"
    )

    products_count = int(summary.get("products", 0) or 0)
    action_products = int(summary.get("action_products", 0) or 0)
    clearance_products = int(summary.get("clearance_products", 0) or 0)
    raise_products = int(summary.get("raise_products", 0) or 0)
    below_products = int(summary.get("below_breakeven_products", 0) or 0)
    at_risk_products = int(summary.get("margin_at_risk_products", 0) or 0)
    no_cost_products = int(summary.get("no_cost_products", 0) or 0)

    total_stock = float(summary.get("stock_units", 0) or 0)
    wb_stock = float(summary.get("wb_stock_units", 0) or 0)
    fbs_stock = float(summary.get("fbs_stock_units", 0) or 0)
    transit_stock = float(summary.get("in_transit_units", 0) or 0)

    margin_upside = float(summary.get("margin_upside_day", 0) or 0)
    stock_at_risk = float(summary.get("stock_at_risk_value", 0) or 0)

    action_share = (
        action_products / products_count * 100
        if products_count
        else 0
    )

    below_share = (
        below_products / products_count * 100
        if products_count
        else 0
    )

    notes = [
        f"Дата анализа: {report_date:%d.%m.%Y} · "
        f"остатки WB: {wb_label} · FBS: {fbs_label}. "
        "В расчёт входит весь запас: WB + FBS + в пути к клиенту "
        "+ в пути от клиента."
    ]

    if no_cost_products:
        notes.append(
            f"У {no_cost_products} артикулов нет ни прихода по УПД, "
            f"ни списаний — минимальная цена для них не посчитана."
        )

    return dmc.Stack(
        gap="lg",
        children=[

            dmc.Alert(
                title=(
                    "Использованы последние доступные остатки"
                    if stale
                    else "Дата остатков и охват"
                ),
                color="yellow" if stale else "blue",
                radius="md",
                children=dmc.Stack(
                    gap=4,
                    children=[
                        dmc.Text(note, size="sm")
                        for note in notes
                    ],
                ),
            ),

            # ------------------------------------------------
            # KPI
            # ------------------------------------------------

            dmc.SimpleGrid(
                cols={"base": 2, "md": 3, "xl": 6},
                spacing="sm",
                children=[
                    _metric_card(
                        label="Артикулов с остатком",
                        value=fmt_number(products_count),
                        note=(
                            f"WB {fmt_number(wb_stock)} шт · "
                            f"FBS {fmt_number(fbs_stock)} шт · "
                            f"в пути {fmt_number(transit_stock)} шт"
                        ),
                        tooltip=(
                            "Товары, у которых есть физический "
                            "остаток или товар в пути. Только они "
                            "участвуют в ценовом анализе."
                        ),
                    ),

                    _metric_card(
                        label="Продаём в убыток",
                        value=fmt_number(below_products),
                        tone="danger" if below_products else "neutral",
                        note=(
                            f"{below_share:.0f}% ассортимента · "
                            "цена ниже точки безубыточности"
                        ),
                        tooltip=(
                            "Текущая цена ниже точки "
                            "безубыточности: каждая проданная "
                            "единица уменьшает прибыль."
                        ),
                    ),

                    _metric_card(
                        label="Убыток на остатке",
                        value=fmt_money(stock_at_risk),
                        tone="danger" if stock_at_risk else "neutral",
                        note=(
                            "Столько потеряем, если распродадим "
                            "этот остаток по текущей цене"
                        ),
                        tooltip=(
                            "Разница между минимальной и текущей "
                            "ценой, умноженная на весь остаток "
                            "убыточных товаров."
                        ),
                    ),

                    _metric_card(
                        label="На грани",
                        value=fmt_number(at_risk_products),
                        tone="warning" if at_risk_products else "neutral",
                        note=(
                            "До точки безубыточности осталось "
                            "меньше 10% цены"
                        ),
                        tooltip=(
                            "Любая скидка или акция уводит эти "
                            "товары в минус."
                        ),
                    ),

                    _metric_card(
                        label="Требуют действия",
                        value=fmt_number(action_products),
                        tone="primary",
                        note=(
                            f"{action_share:.0f}% ассортимента · "
                            f"распродажа {clearance_products} · "
                            f"повышение {raise_products}"
                        ),
                        tooltip=(
                            "Все статусы, кроме «Оставить цену»."
                        ),
                    ),

                    _metric_card(
                        label="Потенциал маржи в день",
                        value=fmt_money(margin_upside),
                        tone="success" if margin_upside > 0 else "neutral",
                        note=(
                            "Модельная оценка при изменении цен "
                            "по рекомендации"
                        ),
                        tooltip=(
                            "Насколько выросла бы суммарная маржа "
                            "в день, если бы цены изменили по "
                            "рекомендации. Это сценарий, а не "
                            "обещание."
                        ),
                    ),
                ],
            ),

            # ------------------------------------------------
            # ГРАФИКИ
            # ------------------------------------------------

            _section_title(
                "Карта возможностей",
                "Где сосредоточен запас, где мы уже теряем деньги "
                "и где изменение цены даст эффект.",
            ),

            pricing_charts_section(
                portfolio=portfolio,
                recommendations=rec,
            ),

            # ------------------------------------------------
            # БРЕНДЫ И КАТЕГОРИИ
            # ------------------------------------------------

            _section_title(
                "1. Бренды и категории",
                "Выберите строку — ниже останутся только "
                "номенклатуры этого бренда и категории.",
            ),

            portfolio_grid(records(portfolio)),

            # ------------------------------------------------
            # НОМЕНКЛАТУРЫ
            # ------------------------------------------------

            _section_title(
                "2. Номенклатуры",
                (
                    "Минимальная цена — граница, ниже которой "
                    "продажа единицы убыточна. Цена под целевую "
                    f"маржу держит {TARGET_MARGIN_PCT:.0f}% "
                    "маржинальности."
                ),
                extra=dmc.Group(
                    gap="xs",
                    children=[
                        _risk_filter(),
                        dmc.Button(
                            "Сбросить фильтр",
                            id=SHOW_ALL_BTN_ID,
                            radius="md",
                            variant="subtle",
                            size="xs",
                        ),
                    ],
                ),
            ),

            dmc.Text(
                "",
                id=SCOPE_LABEL_ID,
                size="xs",
                c="dimmed",
            ),

            products_grid(records(rec)),

            dmc.Divider(),

            dmc.Box(
                id=PRODUCT_DETAIL_ID,
                children=dmc.Alert(
                    title="Выберите товар",
                    color="gray",
                    radius="md",
                    children=(
                        "Нажмите на строку в таблице — здесь "
                        "откроется разбор: из чего сложилась "
                        "минимальная цена, сценарии и история "
                        "цены и продаж."
                    ),
                ),
            ),
        ],
    )
