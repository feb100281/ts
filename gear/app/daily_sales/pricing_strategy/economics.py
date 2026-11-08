# gear/app/daily_sales/pricing_strategy/economics.py
"""
УДЕЛЬНАЯ ЭКОНОМИКА И МИНИМАЛЬНАЯ ЦЕНА ПРОДАЖИ.

Модуль отвечает на главный вопрос приложения:

    ниже какой цены продавать нельзя,
    чтобы не уйти в минус,
    и какая цена держит целевую маржинальность.

Здесь только чистые функции над числами — ни базы, ни dash.
Поэтому расчёт можно проверить руками на калькуляторе,
и именно так его стоит проверять при приёмке.


ЛОГИКА
------

Мы продаём на WB по своей цене. До нас доходит не вся сумма:

    1. из цены вычитается НДС;
    2. WB удерживает комиссию (процент от суммы);
    3. остаётся покрыть управленческую себестоимость товара.

Логистика WB в расчёт НЕ входит — так принято в остальных
отчётах компании, и здесь методика та же, чтобы цифры
сходились между отчётами.

Отсюда маржа на единицу при нашей цене P:

    выручка без НДС      = P * vat_ratio
    после комиссии       = P * vat_ratio * (1 + commission_ratio)
    маржа на единицу     = P * vat_ratio * (1 + commission_ratio)
                           - себестоимость

commission_ratio — доля комиссии от выручки без НДС, она
ОТРИЦАТЕЛЬНАЯ (так комиссия хранится в данных), поэтому
(1 + commission_ratio) — это доля, которая остаётся у нас.


ТОЧКА БЕЗУБЫТОЧНОСТИ
--------------------

Приравниваем маржу к нулю:

    P0 = себестоимость / (vat_ratio * (1 + commission_ratio))


ЦЕНА ПОД ЦЕЛЕВУЮ МАРЖУ
----------------------

Маржинальность в приложении считается от выручки без НДС:

    маржа % = маржа / (P * vat_ratio)

Значит для целевой маржи m:

    P = себестоимость / (vat_ratio * (1 + commission_ratio - m))

Если знаменатель <= 0, целевая маржа недостижима ни при какой
цене — комиссия съедает больше, чем мы хотим заработать.
В этом случае возвращается None, а не бесконечность.


ОТКУДА БЕРУТСЯ КОЭФФИЦИЕНТЫ
---------------------------

vat_ratio и commission_ratio считаются по ФАКТИЧЕСКИМ
продажам товара за период. Если товар не
продавался — а это как раз самый проблемный случай, ради
которого всё и затевалось, — берётся медиана по категории,
затем медиана по всей выборке. Источник всегда подписан
в колонке «Источник коэффициентов», чтобы никто не принял
оценку за факт.
"""

from __future__ import annotations


# ============================================================
# БАЗОВЫЕ ХЕЛПЕРЫ
# ============================================================

def number(value, default=0.0):
    """float без исключений: None, NaN и мусор дают default."""
    if value is None:
        return default

    try:
        value = float(value)
    except (TypeError, ValueError):
        return default

    if value != value:  # NaN
        return default

    return value


def positive(value, default=None):
    """Возвращает значение только если оно строго больше нуля."""
    result = number(value, 0.0)

    return result if result > 0 else default


# ============================================================
# КОЭФФИЦИЕНТЫ ПО ФАКТИЧЕСКИМ ПРОДАЖАМ
# ============================================================

def unit_ratios(metrics: dict) -> dict:
    """
    Коэффициенты удельной экономики по метрикам периода.

    На вход идёт словарь из period_metrics: суммы за период.
    На выходе — доли и рубли на единицу, либо None там, где
    данных не хватило.

        vat_ratio           доля выручки без НДС от нашей цены
        commission_ratio    доля комиссии от выручки без НДС
                            (отрицательная)
    """

    metrics = metrics or {}

    qty = number(metrics.get("sales_qty"))

    seller_amount = number(
        metrics.get("seller_sales_amount")
    )

    amount_vatless = number(
        metrics.get("amount_vatless")
    )

    commission = number(
        metrics.get("net_comission")
    )

    vat_ratio = None

    if seller_amount > 0 and amount_vatless > 0:
        candidate = amount_vatless / seller_amount

        # sanity: доля без НДС не может быть больше 1
        # и меньше половины цены
        if 0.5 <= candidate <= 1.0:
            vat_ratio = candidate

    commission_ratio = None

    if amount_vatless > 0 and commission != 0:
        candidate = commission / amount_vatless

        # комиссияWB в разумных пределах
        if -0.9 <= candidate <= 0.0:
            commission_ratio = candidate

    return {
        "vat_ratio": vat_ratio,
        "commission_ratio": commission_ratio,
        "ratio_qty": qty,
    }


# ============================================================
# СЕБЕСТОИМОСТЬ ЕДИНИЦЫ
# ============================================================

def unit_cost(
    *,
    last_man_cost,
    metrics: dict | None = None,
):
    """
    Управленческая себестоимость единицы.

    Приоритет:

        1. цена последнего прихода УПД (last_man_cost) —
           есть у любого товара, лежащего на складе;
        2. фактическая FIFO-себестоимость проданных единиц
           за период — на случай, если приходов нет.

    Возвращает (значение, источник).
    """

    upd_cost = positive(last_man_cost)

    if upd_cost is not None:
        return upd_cost, "Приход УПД"

    metrics = metrics or {}

    qty = number(metrics.get("sales_qty"))

    cogs = abs(
        number(metrics.get("cogs_man"))
    )

    if qty > 0 and cogs > 0:
        return cogs / qty, "Списание по продажам"

    return 0.0, "Нет данных"


# ============================================================
# ГЛАВНОЕ: МИНИМАЛЬНАЯ ЦЕНА
# ============================================================

def breakeven_price(
    *,
    cost_per_unit,
    vat_ratio,
    commission_ratio,
):
    """
    Цена, при которой маржа равна нулю.

    Возвращает None, если коэффициентов не хватает —
    лучше пустая ячейка, чем красивое неправильное число.
    """

    cost_per_unit = number(cost_per_unit)

    if cost_per_unit <= 0:
        return None

    vat_ratio = positive(vat_ratio)

    if vat_ratio is None:
        return None

    keep_share = 1.0 + number(commission_ratio)

    if keep_share <= 0:
        return None

    return cost_per_unit / (vat_ratio * keep_share)


def target_margin_price(
    *,
    cost_per_unit,
    vat_ratio,
    commission_ratio,
    target_margin_pct,
):
    """
    Цена, которая даёт целевую маржинальность
    (в процентах от выручки без НДС).
    """

    cost_per_unit = number(cost_per_unit)

    if cost_per_unit <= 0:
        return None

    vat_ratio = positive(vat_ratio)

    if vat_ratio is None:
        return None

    margin_share = number(target_margin_pct) / 100.0

    keep_share = (
        1.0
        + number(commission_ratio)
        - margin_share
    )

    if keep_share <= 0:
        # целевая маржа недостижима при такой комиссии
        return None

    return cost_per_unit / (vat_ratio * keep_share)


def margin_at_price(
    price,
    *,
    cost_per_unit,
    vat_ratio,
    commission_ratio,
):
    """
    Маржа на единицу при заданной цене.
    Возвращает (маржа в рублях, маржа в % от выручки без НДС).
    """

    price = number(price)

    vat_ratio = positive(vat_ratio)

    if price <= 0 or vat_ratio is None:
        return None, None

    revenue_vatless = price * vat_ratio

    keep = revenue_vatless * (
        1.0 + number(commission_ratio)
    )

    margin = keep - number(cost_per_unit)

    margin_pct = (
        margin / revenue_vatless * 100.0
        if revenue_vatless
        else None
    )

    return margin, margin_pct


def price_headroom_pct(current_price, floor_price):
    """
    Насколько процентов можно опустить цену
    до точки безубыточности.

    Отрицательное значение = мы уже ниже безубытка.
    """

    current_price = positive(current_price)

    floor_price = positive(floor_price)

    if current_price is None or floor_price is None:
        return None

    return (
        (current_price - floor_price)
        / current_price
        * 100.0
    )
