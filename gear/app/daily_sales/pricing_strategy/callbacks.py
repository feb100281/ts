# gear/app/daily_sales/pricing_strategy/callbacks.py
"""
ПОВЕДЕНИЕ ЭКРАНА.

Пять сценариев работы, ради которых всё писалось:

    1. открыть анализ по текущим фильтрам страницы;
    2. провалиться из бренда и категории в номенклатуры;
    3. быстро отобрать проблемные товары одним кликом;
    4. раскрыть конкретный товар и понять, откуда цифры;
    5. забрать нужный документ.

Всё тяжёлое считается один раз при открытии и лежит в Store,
поэтому фильтрация и раскрытие карточки происходят мгновенно,
без повторных обращений к базе.
"""

from __future__ import annotations

from datetime import date

import dash_mantine_components as dmc
from dash import (
    Input,
    Output,
    State,
    dcc,
    no_update,
)

from .analytics import analyze_pricing
from .config import (
    BODY_ID,
    CLOSE_BTN_ID,
    DOWNLOAD_ID,
    EXPORT_EXCEL_ID,
    EXPORT_LOSS_ID,
    EXPORT_CLICKS_ID,
    EXPORT_PRODUCT_ID,
    EXPORT_STATUS_ID,
    EXPORT_WB_PRICES_ID,
    EXPORT_ZIP_ID,
    METHOD_BTN_ID,
    METHOD_DRAWER_ID,
    MODAL_ID,
    OPEN_BTN_ID,
    PORTFOLIO_GRID_ID,
    PRODUCTS_GRID_ID,
    PRODUCT_DETAIL_ID,
    RISK_FILTER_ID,
    SCOPE_LABEL_ID,
    SHOW_ALL_BTN_ID,
    STORE_ID,
    TARGET_MARGIN_PCT,
)
from .data import get_pricing_source
from .theme import DANGER, PRIMARY, SUCCESS, WARNING
from .exports import (
    build_loss_excel,
    build_pricing_excel,
    build_product_excel,
    build_wb_price_csv,
    build_zip,
    filename,
    price_change_frame,
)
from .layout import build_pricing_body, records
from . import state


# ============================================================
# ФОРМАТИРОВАНИЕ
# ============================================================

def _fmt(value, digits=0, dash="—"):
    if value is None:
        return dash

    try:
        value = float(value)
    except (TypeError, ValueError):
        return dash

    if value != value:
        return dash

    return f"{value:,.{digits}f}".replace(",", " ")


def _money(value, digits=0):
    text = _fmt(value, digits)

    return text if text == "—" else f"{text} ₽"


def _pct(value, digits=1, signed=False):
    text = _fmt(value, digits)

    if text == "—":
        return text

    if signed and not text.startswith("-"):
        text = "+" + text

    return f"{text} %"


def _number(value, default=0.0):
    try:
        value = float(value)
    except (TypeError, ValueError):
        return default

    if value != value:
        return default

    return value


def _full_payload(payload):
    """
    Полный расчёт по ключу из Store.

    Возвращает None, если кэш промахнулся: сервер
    перезапустили или расчёт вытеснили более свежими.
    Вызывающая сторона обязана это обработать и попросить
    построить анализ заново — молча падать здесь нельзя.
    """

    if not payload:
        return None

    return state.get(
        payload.get("cache_key")
    )


STATUS_LABELS = {
    "LOSS": ("Продаём в убыток", "red"),
    "CLEARANCE": ("Распродажа", "red"),
    "REDUCE": ("Снизить цену", "orange"),
    "RAISE": ("Повысить цену", "green"),
    "TEST": ("Тест цены", "yellow"),
    "HOLD": ("Оставить цену", "gray"),
}


# ============================================================
# РАЗБОР ЦЕНЫ
#
# Главный блок карточки: из чего сложилась минимальная цена.
# Читается сверху вниз как обычная калькуляция.
# ============================================================

def _price_breakdown(row):

    cost = _number(row.get("unit_cogs"))
    acc_cost = _number(row.get("unit_acc_cost"))
    vat_ratio = row.get("vat_ratio")
    commission_ratio = row.get("commission_ratio")

    lines = [
        (
            "Управленческая с/с единицы",
            _money(cost, 2),
            row.get("cost_source") or "—",
        ),
        (
            "Бухгалтерская с/с единицы",
            _money(acc_cost, 2),
            "цена последнего прихода УПД",
        ),
        (
            "Остаётся после НДС",
            (
                _pct(_number(vat_ratio) * 100)
                if vat_ratio
                else "—"
            ),
            "доля нашей цены",
        ),
        (
            "Забирает WB комиссией",
            (
                _pct(abs(_number(commission_ratio)) * 100)
                if commission_ratio
                else "—"
            ),
            "доля выручки без НДС",
        ),
    ]

    rows = [
        dmc.TableTr(
            [
                dmc.TableTd(label),
                dmc.TableTd(
                    dmc.Text(value, fw=700, size="sm"),
                    style={"textAlign": "right"},
                ),
                dmc.TableTd(
                    dmc.Text(note, size="xs", c="dimmed"),
                ),
            ]
        )
        for label, value, note in lines
    ]

    rows.append(
        dmc.TableTr(
            [
                dmc.TableTd(
                    dmc.Text(
                        "Минимальная цена",
                        fw=800,
                    )
                ),
                dmc.TableTd(
                    dmc.Text(
                        _money(row.get("breakeven_price")),
                        fw=800,
                        size="md",
                        style={"color": DANGER},
                    ),
                    style={"textAlign": "right"},
                ),
                dmc.TableTd(
                    dmc.Text(
                        "ниже — убыток на каждой единице",
                        size="xs",
                        c="dimmed",
                    )
                ),
            ],
            style={"backgroundColor": "#FEF2F2"},
        )
    )

    rows.append(
        dmc.TableTr(
            [
                dmc.TableTd(
                    dmc.Text(
                        f"Цена под маржу {TARGET_MARGIN_PCT:.0f}%",
                        fw=800,
                    )
                ),
                dmc.TableTd(
                    dmc.Text(
                        _money(row.get("target_margin_price")),
                        fw=800,
                        size="md",
                        style={"color": PRIMARY},
                    ),
                    style={"textAlign": "right"},
                ),
                dmc.TableTd(
                    dmc.Text(
                        "держит плановую маржинальность",
                        size="xs",
                        c="dimmed",
                    )
                ),
            ],
            style={"backgroundColor": "#EEF2FF"},
        )
    )

    return dmc.Table(
        withTableBorder=True,
        withColumnBorders=False,
        striped=False,
        children=[dmc.TableTbody(rows)],
    )


def _kpi_row(row):

    def cell(label, value, color=None, note=None):

        # ВАЖНО: цвет задаём через style, а не через проп c.
        #
        # Mantine парсит значение пропа c как цвет темы.
        # Python-овский None приезжает в браузер как null,
        # а typeof null === "object" — отсюда в консоли
        # сыпалось «Failed to parse color. Expected color to
        # be a string, instead got object». Через style такой
        # проблемы нет: это обычный CSS.
        value_style = {"lineHeight": "1.2"}

        if color:
            value_style["color"] = color

        return dmc.Paper(
            withBorder=True,
            radius="md",
            p="sm",
            children=[
                dmc.Text(
                    label,
                    size="xs",
                    c="dimmed",
                    fw=600,
                    tt="uppercase",
                ),
                dmc.Text(
                    value,
                    size="lg",
                    fw=800,
                    mt=2,
                    style=value_style,
                ),
                dmc.Text(
                    note or "",
                    size="xs",
                    c="dimmed",
                ),
            ],
        )

    headroom = row.get("price_headroom_pct")

    headroom_color = (
        DANGER
        if headroom is not None and _number(headroom) < 0
        else (
            WARNING
            if headroom is not None and _number(headroom) < 10
            else SUCCESS
        )
    )

    return dmc.SimpleGrid(
        cols={"base": 2, "md": 3, "xl": 6},
        spacing="xs",
        children=[
            cell(
                "Текущая цена",
                _money(row.get("current_effective_price")),
                note="по фактическим продажам",
            ),
            cell(
                "Цена покупателя",
                _money(row.get("buyer_price_30d")),
                note=(
                    "скидка WB "
                    + _pct(row.get("wb_discount_pct_30d"))
                ),
            ),
            cell(
                "Минимальная цена",
                _money(row.get("breakeven_price")),
                color=DANGER,
                note="точка безубыточности",
            ),
            cell(
                "Цена к установке",
                _money(row.get("action_price")),
                color=PRIMARY,
                note=_pct(
                    row.get("action_change_pct"),
                    signed=True,
                ),
            ),
            cell(
                "Запас по скидке",
                _pct(headroom),
                color=headroom_color,
                note="до точки безубыточности",
            ),
            cell(
                "Запас товара",
                f"{_fmt(row.get('days_of_stock'))} дн.",
                note=(
                    f"{_fmt(row.get('total_stock'))} шт · "
                    f"WB {_fmt(row.get('wb_stock'))} · "
                    f"FBS {_fmt(row.get('fbs_stock'))}"
                ),
            ),
        ],
    )


# ============================================================
# ТАБЛИЦЫ КАРТОЧКИ
# ============================================================

def _scenario_table(rows, recommended_change, breakeven=None):

    if not rows:
        return dmc.Text("Сценарии недоступны.", c="dimmed")

    body = []

    for row in sorted(
        rows,
        key=lambda item: _number(
            item.get("price_change_pct")
        ),
    ):

        change = _number(row.get("price_change_pct"))

        seller_price = _number(row.get("seller_price"))

        recommended = (
            abs(change - _number(recommended_change))
            < 0.01
        )

        below = bool(
            breakeven
            and seller_price
            and seller_price < breakeven
        )

        if recommended:
            background = "#ECFDF5"
        elif below:
            background = "#FEF2F2"
        else:
            background = "transparent"

        body.append(
            dmc.TableTr(
                [
                    dmc.TableTd(f"{change:+.1f}%"),
                    dmc.TableTd(_money(seller_price)),
                    dmc.TableTd(_money(row.get("buyer_price"))),
                    dmc.TableTd(
                        _fmt(
                            row.get("projected_daily_qty"),
                            1,
                        )
                    ),
                    dmc.TableTd(
                        _money(row.get("projected_margin"))
                    ),
                    dmc.TableTd(
                        _pct(row.get("projected_margin_pct"))
                    ),
                    dmc.TableTd(
                        _fmt(row.get("projected_stock_days"))
                    ),
                    dmc.TableTd(
                        dmc.Badge(
                            "ниже минимальной",
                            color="red",
                            variant="light",
                            size="sm",
                        )
                        if below
                        else ""
                    ),
                ],
                style={
                    "backgroundColor": background,
                    "fontWeight": "700" if recommended else "400",
                },
            )
        )

    return dmc.Table(
        striped=False,
        withTableBorder=True,
        withColumnBorders=True,
        children=[
            dmc.TableThead(
                dmc.TableTr(
                    [
                        dmc.TableTh("Δ цены"),
                        dmc.TableTh("Наша цена"),
                        dmc.TableTh("Цена покупателя"),
                        dmc.TableTh("Продаж/день"),
                        dmc.TableTh("Маржа 30д"),
                        dmc.TableTh("Маржа %"),
                        dmc.TableTh("Запас, дн."),
                        dmc.TableTh(""),
                    ]
                )
            ),
            dmc.TableTbody(body),
        ],
    )


def _history_table(history, breakeven=None):

    if not history:
        return dmc.Text("История отсутствует.", c="dimmed")

    body = []

    for item in history:

        seller_price = _number(item.get("seller_price"))

        buyer_price = _number(item.get("buyer_price"))

        discount = (
            (1 - buyer_price / seller_price) * 100
            if seller_price > 0 and buyer_price > 0
            else None
        )

        below = bool(
            breakeven
            and seller_price
            and seller_price < breakeven
        )

        body.append(
            dmc.TableTr(
                [
                    dmc.TableTd(
                        str(item.get("date_from", ""))[:10]
                    ),
                    dmc.TableTd(_fmt(item.get("sales_qty"))),
                    dmc.TableTd(_money(seller_price)),
                    dmc.TableTd(_pct(discount)),
                    dmc.TableTd(_money(buyer_price)),
                    dmc.TableTd(_money(item.get("margin_man"))),
                ],
                style={
                    "backgroundColor": (
                        "#FEF2F2" if below else "transparent"
                    ),
                },
            )
        )

    return dmc.Table(
        striped=True,
        withTableBorder=True,
        withColumnBorders=True,
        children=[
            dmc.TableThead(
                dmc.TableTr(
                    [
                        dmc.TableTh("Дата"),
                        dmc.TableTh("Продажи"),
                        dmc.TableTh("Наша цена"),
                        dmc.TableTh("Скидка WB"),
                        dmc.TableTh("Цена покупателя"),
                        dmc.TableTh("Маржа"),
                    ]
                )
            ),
            dmc.TableTbody(body),
        ],
    )


def _product_charts(history, scenarios, row):
    """
    Графики карточки. Если версия DMC без графиков —
    просто не показываем их, таблицы остаются.
    """

    try:
        from .charts_dmc import (
            charts_available,
            product_history_chart,
            scenarios_chart,
        )

        if not charts_available():
            return None

        breakeven = row.get("breakeven_price")

        return dmc.SimpleGrid(
            cols={"base": 1, "xl": 2},
            spacing="md",
            children=[
                dmc.Paper(
                    withBorder=True,
                    radius="md",
                    p="md",
                    children=[
                        dmc.Text(
                            "Цена и продажи по дням",
                            fw=700,
                        ),
                        dmc.Text(
                            "Красная линия — минимальная цена. "
                            "Всё, что под ней, продавалось в убыток.",
                            size="xs",
                            c="dimmed",
                            mb=8,
                        ),
                        product_history_chart(
                            history,
                            breakeven=breakeven,
                        ),
                    ],
                ),
                dmc.Paper(
                    withBorder=True,
                    radius="md",
                    p="md",
                    children=[
                        dmc.Text(
                            "Сценарии изменения цены",
                            fw=700,
                        ),
                        dmc.Text(
                            "Как модель видит маржу и объём при "
                            "разной цене.",
                            size="xs",
                            c="dimmed",
                            mb=8,
                        ),
                        scenarios_chart(
                            scenarios,
                            recommended_change=row.get(
                                "action_change_pct"
                            ),
                        ),
                    ],
                ),
            ],
        )

    except Exception:
        return None


# ============================================================
# ФИЛЬТРАЦИЯ
# ============================================================

def _apply_risk_filter(rows, mode):

    if not mode or mode == "all":
        return rows

    if mode == "loss":
        return [
            row
            for row in rows
            if row.get("below_breakeven")
        ]

    if mode == "risk":
        return [
            row
            for row in rows
            if row.get("margin_at_risk")
        ]

    if mode == "clearance":
        return [
            row
            for row in rows
            if row.get("status") == "CLEARANCE"
        ]

    if mode == "raise":
        return [
            row
            for row in rows
            if row.get("status") == "RAISE"
        ]

    return rows


RISK_LABELS = {
    "all": "все товары",
    "loss": "продаём в убыток",
    "risk": "на грани",
    "clearance": "распродажа",
    "raise": "можно повышать",
}


# ============================================================
# РЕГИСТРАЦИЯ
# ============================================================

def register_pricing_strategy_callbacks(app, filters):

    # ========================================================
    # ОТКРЫТИЕ АНАЛИЗА
    # ========================================================

    @app.callback(
        Output(MODAL_ID, "opened"),
        Output(BODY_ID, "children"),
        Output(STORE_ID, "data"),

        Input(OPEN_BTN_ID, "n_clicks"),

        State(filters.date_picker_id, "value"),
        State(filters.cat_multy_id, "value"),
        State(filters.brand_multy_id, "value"),
        State(filters.gender_multy_id, "value"),

        prevent_initial_call=True,
    )
    def open_pricing(
        open_clicks,
        date_range,
        cat_list,
        brand_list,
        gender_list,
    ):

        if not open_clicks:
            return no_update, no_update, no_update

        if date_range and len(date_range) == 2:
            report_date = date_range[1]
        else:
            report_date = date.today()

        try:
            source = get_pricing_source(
                report_date=report_date,
                cat_list=cat_list,
                brand_list=brand_list,
                gender_list=gender_list,
            )

            analysis = analyze_pricing(source)

            # Полный расчёт — на сервер.
            full_payload = {
                "report_date": str(analysis["report_date"]),

                "history_start": str(
                    analysis["history_start"]
                ),

                "wb_date": (
                    str(analysis["wb_date"])
                    if analysis.get("wb_date")
                    else None
                ),

                "fbs_date": (
                    str(analysis["fbs_date"])
                    if analysis.get("fbs_date")
                    else None
                ),

                "summary": analysis.get("summary") or {},

                "recommendations": records(
                    analysis["recommendations"]
                ),

                "portfolio": records(
                    analysis["portfolio"]
                ),

                "scenarios": records(
                    analysis["scenarios"]
                ),

                "history": records(
                    analysis["history"]
                ),
            }

            cache_key = state.put(full_payload)

            # В браузер — только ключ и несколько чисел
            # для шапки. Всё остальное остаётся на сервере.
            #
            # Сами строки таблиц уже отрисованы в разметке,
            # второй раз возить их через Store незачем: Store
            # отправляется серверу при каждом обращении
            # callback-а, а это мегабайты на каждый клик.
            light_payload = {
                key: full_payload[key]
                for key in (
                    "report_date",
                    "history_start",
                    "wb_date",
                    "fbs_date",
                    "summary",
                )
            }

            light_payload["cache_key"] = cache_key

            return (
                True,
                build_pricing_body(analysis),
                light_payload,
            )

        except Exception as exc:

            return (
                True,
                dmc.Alert(
                    title="Ошибка расчёта управления ценами",
                    color="red",
                    radius="md",
                    children=[
                        dmc.Text(str(exc), size="sm"),
                        dmc.Text(
                            "Проверьте, что за выбранный период "
                            "есть остатки и продажи. Если ошибка "
                            "повторяется — покажите этот текст "
                            "разработчику.",
                            size="xs",
                            c="dimmed",
                            mt=8,
                        ),
                    ],
                ),
                None,
            )

    # ========================================================
    # ЗАКРЫТИЕ
    # ========================================================

    @app.callback(
        Output(MODAL_ID, "opened", allow_duplicate=True),
        Input(CLOSE_BTN_ID, "n_clicks"),
        prevent_initial_call=True,
    )
    def close_pricing(close_clicks):

        if not close_clicks:
            return no_update

        return False

    # ========================================================
    # МЕТОДИКА
    # ========================================================

    @app.callback(
        Output(METHOD_DRAWER_ID, "opened"),
        Input(METHOD_BTN_ID, "n_clicks"),
        prevent_initial_call=True,
    )
    def open_methodology(n_clicks):

        if not n_clicks:
            return no_update

        return True

    # ========================================================
    # ФИЛЬТРАЦИЯ НОМЕНКЛАТУР
    #
    # Один callback на оба среза — бренд с категорией и
    # быстрый фильтр по риску. Иначе они начинают спорить
    # друг с другом за rowData.
    # ========================================================

    @app.callback(
        Output(PRODUCTS_GRID_ID, "rowData"),
        Output(SCOPE_LABEL_ID, "children"),

        Input(PORTFOLIO_GRID_ID, "selectedRows"),
        Input(RISK_FILTER_ID, "value"),

        State(STORE_ID, "data"),

        prevent_initial_call=True,
    )
    def filter_products(selected_rows, risk_mode, payload):

        full = _full_payload(payload)

        if full is None:
            return no_update, no_update

        rows = full.get("recommendations") or []

        scope_parts = []

        if selected_rows:

            selected = selected_rows[0]

            brand = selected.get("brand")

            category = selected.get("category")

            rows = [
                row
                for row in rows
                if (
                    row.get("brand") == brand
                    and row.get("category") == category
                )
            ]

            scope_parts.append(f"{brand} · {category}")

        rows = _apply_risk_filter(rows, risk_mode)

        if risk_mode and risk_mode != "all":
            scope_parts.append(
                RISK_LABELS.get(risk_mode, risk_mode)
            )

        total = len(full.get("recommendations") or [])

        scope = (
            "Показано "
            f"{len(rows)} из {total} артикулов"
        )

        if scope_parts:
            scope += " · " + " · ".join(scope_parts)

        return rows, scope

    # ========================================================
    # СБРОС ФИЛЬТРА
    # ========================================================

    @app.callback(
        Output(RISK_FILTER_ID, "value"),
        Output(PORTFOLIO_GRID_ID, "selectedRows"),

        Input(SHOW_ALL_BTN_ID, "n_clicks"),

        prevent_initial_call=True,
    )
    def reset_filters(n_clicks):

        if not n_clicks:
            return no_update, no_update

        return "all", []

    # ========================================================
    # КАРТОЧКА ТОВАРА
    # ========================================================

    @app.callback(
        Output(PRODUCT_DETAIL_ID, "children"),

        Input(PRODUCTS_GRID_ID, "selectedRows"),

        State(STORE_ID, "data"),

        prevent_initial_call=True,
    )
    def product_detail(selected_rows, payload):

        # ВАЖНО. Здесь стоит no_update, а не заглушка.
        #
        # AG Grid сбрасывает selectedRows в пустой список при
        # любом перерисовывании таблицы — после пересчёта
        # высоты строк, смены страницы, обновления rowData.
        # Раньше карточка из-за этого появлялась на пару
        # секунд и пропадала сама.
        #
        # Пустой выбор теперь просто игнорируется: последний
        # разбор остаётся на экране, пока не выбран другой
        # товар.
        if not selected_rows or not payload:
            return no_update

        row = selected_rows[0]

        nm_id = row.get("nm_id")

        # Сценарии и история лежат на сервере, в Store их нет.
        full = _full_payload(payload)

        if full is None:
            return dmc.Alert(
                title="Расчёт устарел",
                color="yellow",
                radius="md",
                children=(
                    "Данные анализа больше не в памяти сервера — "
                    "скорее всего, его перезапустили. Закройте "
                    "окно и постройте анализ заново."
                ),
            )

        scenarios = [
            item
            for item in (full.get("scenarios") or [])
            if str(item.get("nm_id")) == str(nm_id)
        ]

        history = [
            item
            for item in (full.get("history") or [])
            if str(item.get("nm_id")) == str(nm_id)
        ]

        history = sorted(
            history,
            key=lambda item: str(item.get("date_from", "")),
            reverse=True,
        )[:90]

        status = row.get("status", "HOLD")

        status_label, status_color = STATUS_LABELS.get(
            status,
            (status, "gray"),
        )

        ratios_source = row.get("ratios_source")

        blocks = [
            dmc.Group(
                justify="space-between",
                align="flex-start",
                children=[
                    dmc.Box(
                        children=[
                            dmc.Title(
                                (
                                    f"{row.get('brand', '')} · "
                                    f"{row.get('title', '')}"
                                ),
                                order=3,
                                fw=800,
                            ),
                            dmc.Text(
                                (
                                    f"NM ID {nm_id} · "
                                    f"{row.get('category', '')} · "
                                    f"артикул "
                                    f"{row.get('sa_name') or '—'}"
                                ),
                                size="sm",
                                c="dimmed",
                            ),
                        ]
                    ),
                    dmc.Group(
                        gap="xs",
                        align="center",
                        children=[
                            dmc.Badge(
                                status_label,
                                color=status_color,
                                radius="sm",
                                size="lg",
                                variant="filled",
                            ),
                            dmc.Text(
                                "Разбор по этому товару можно "
                                "скачать в меню «Скачать»",
                                size="xs",
                                c="dimmed",
                            ),
                        ],
                    ),
                ],
            ),

            _kpi_row(row),
        ]

        if row.get("below_breakeven"):
            blocks.append(
                dmc.Alert(
                    title="Товар продаётся ниже точки безубыточности",
                    color="red",
                    radius="md",
                    children=(
                        "Убыток "
                        f"{_money(row.get('loss_per_unit'), 2)} "
                        "на каждой проданной единице. "
                        "На всём остатке это "
                        f"{_money(row.get('stock_at_risk_value'))}."
                    ),
                )
            )

        if ratios_source and ratios_source != "Свои продажи":
            blocks.append(
                dmc.Alert(
                    title="Расчёт по оценке, а не по фактам товара",
                    color="yellow",
                    radius="md",
                    children=(
                        "У товара нет собственных продаж, поэтому "
                        "доли НДС, комиссии и логистики взяты как "
                        f"{ratios_source.lower()}. Минимальную цену "
                        "стоит перепроверить перед решением."
                    ),
                )
            )

        blocks.extend(
            [
                dmc.Title("Из чего сложилась цена", order=4, fw=700),
                _price_breakdown(row),

                dmc.Alert(
                    title="Почему такое решение",
                    color="gray",
                    radius="md",
                    children=row.get("reason", ""),
                ),
            ]
        )

        charts = _product_charts(history, scenarios, row)

        if charts is not None:
            blocks.append(charts)

        blocks.extend(
            [
                dmc.Title("Сценарии цены", order=4, fw=700),
                dmc.ScrollArea(
                    _scenario_table(
                        scenarios,
                        row.get("action_change_pct"),
                        breakeven=row.get("breakeven_price"),
                    ),
                    type="auto",
                ),

                dmc.Title(
                    "История цены и продаж · последние 90 дней",
                    order=4,
                    fw=700,
                ),
                dmc.ScrollArea(
                    _history_table(
                        history,
                        breakeven=row.get("breakeven_price"),
                    ),
                    h=420,
                    type="auto",
                ),
            ]
        )

        return dmc.Stack(gap="md", children=blocks)

    # ========================================================
    # ВЫГРУЗКИ
    #
    # ОДИН callback на все кнопки и РОВНО ОДИН Output на
    # dcc.Download.
    #
    # История вопроса. Сначала здесь был один обработчик,
    # который определял нажатую кнопку через ctx.triggered_id
    # — под django-plotly-dash контекста callback-а нет, и он
    # падал. Потом я развела кнопки по отдельным callback-ам
    # с allow_duplicate на общий Output — файл начал
    # собираться (запрос думал несколько секунд), но в
    # браузер не доезжал: дублирующиеся Output на один
    # компонент этот стек обрабатывает ненадёжно.
    #
    # Рабочий вариант без обеих проблем: слушаем все кнопки
    # сразу и сравниваем счётчики нажатий с предыдущими,
    # которые храним в отдельном Store. Изменился счётчик —
    # значит, нажали эту кнопку. Никакого контекста и
    # никаких дублей.
    # ========================================================

    EXPORT_KINDS = (
        ("excel", EXPORT_EXCEL_ID),
        ("loss", EXPORT_LOSS_ID),
        ("csv", EXPORT_WB_PRICES_ID),
        ("zip", EXPORT_ZIP_ID),
        ("product", EXPORT_PRODUCT_ID),
    )

    def _error_alert(title, message):
        return dmc.Alert(
            title=title,
            color="red",
            radius="md",
            withCloseButton=True,
            children=[
                dmc.Text(message, size="sm"),
                dmc.Text(
                    "Покажите этот текст разработчику — "
                    "по нему видно, на чём именно сломалось.",
                    size="xs",
                    c="dimmed",
                    mt=6,
                ),
            ],
        )

    def _info_alert(title, message, color="yellow"):
        return dmc.Alert(
            title=title,
            color=color,
            radius="md",
            withCloseButton=True,
            children=message,
        )

    def _build(kind, payload, selected_rows):
        """
        Собирает файл. Возвращает (содержимое, имя файла)
        или (None, сообщение), если собирать нечего.
        """

        if kind == "excel":
            return (
                build_pricing_excel(payload),
                filename("excel", payload),
            )

        if kind == "loss":
            return (
                build_loss_excel(payload),
                filename("loss", payload),
            )

        if kind == "zip":
            return (
                build_zip(payload),
                filename("zip", payload),
            )

        if kind == "csv":

            changes = price_change_frame(payload)

            if changes is None or changes.empty:
                return (
                    None,
                    "Нет артикулов, где цену нужно изменить "
                    "хотя бы на 1%.",
                )

            return (
                build_wb_price_csv(payload),
                filename("csv", payload),
            )

        if kind == "product":

            if not selected_rows:
                return (
                    None,
                    "Сначала выберите товар в таблице "
                    "«Номенклатуры».",
                )

            nm_id = selected_rows[0].get("nm_id")

            return (
                build_product_excel(payload, nm_id),
                filename(
                    "product",
                    payload,
                    nm_id=nm_id,
                ),
            )

        return None, "Неизвестный тип файла."

    @app.callback(
        Output(DOWNLOAD_ID, "data"),
        Output(EXPORT_STATUS_ID, "children"),
        Output(EXPORT_CLICKS_ID, "data"),

        Input(EXPORT_EXCEL_ID, "n_clicks"),
        Input(EXPORT_LOSS_ID, "n_clicks"),
        Input(EXPORT_WB_PRICES_ID, "n_clicks"),
        Input(EXPORT_ZIP_ID, "n_clicks"),
        Input(EXPORT_PRODUCT_ID, "n_clicks"),

        State(STORE_ID, "data"),
        State(PRODUCTS_GRID_ID, "selectedRows"),
        State(EXPORT_CLICKS_ID, "data"),

        prevent_initial_call=True,
    )
    def export_documents(
        excel_clicks,
        loss_clicks,
        csv_clicks,
        zip_clicks,
        product_clicks,
        payload,
        selected_rows,
        seen_clicks,
    ):

        counts = {
            "excel": int(excel_clicks or 0),
            "loss": int(loss_clicks or 0),
            "csv": int(csv_clicks or 0),
            "zip": int(zip_clicks or 0),
            "product": int(product_clicks or 0),
        }

        seen = seen_clicks or {}

        changed = [
            kind
            for kind, _ in EXPORT_KINDS
            if counts[kind] != int(seen.get(kind) or 0)
        ]

        if not changed:
            return no_update, no_update, counts

        kind = changed[0]

        if not payload:
            return (
                no_update,
                _info_alert(
                    "Анализ ещё не построен",
                    "Закройте окно, нажмите «Управление "
                    "ценами» и дождитесь расчёта.",
                ),
                counts,
            )

        full = _full_payload(payload)

        if full is None:
            return (
                no_update,
                _info_alert(
                    "Расчёт устарел",
                    "Данные анализа больше не в памяти "
                    "сервера — скорее всего, его "
                    "перезапустили. Постройте анализ заново.",
                ),
                counts,
            )

        try:
            content, label = _build(
                kind,
                full,
                selected_rows,
            )

        except Exception as exc:
            return (
                no_update,
                _error_alert(
                    "Не удалось собрать файл",
                    f"{type(exc).__name__}: {exc}",
                ),
                counts,
            )

        if not content:
            return (
                no_update,
                _info_alert("Скачивать нечего", label),
                counts,
            )

        size_mb = len(content) / 1_000_000

        return (
            dcc.send_bytes(content, filename=label),
            _info_alert(
                "Файл готов",
                (
                    f"{label} · {size_mb:.1f} МБ. "
                    "Если он не открылся сам, посмотрите в "
                    "загрузках браузера."
                ),
                color="teal",
            ),
            counts,
        )
