# gear/app/daily_sales/fbs_orders/config.py
"""
Константы анализа заказов FBS.

Здесь собрано всё, что задаёт правила анализа: пороги сборки,
человеческие названия статусов WB и идентификаторы компонентов.
"""

from __future__ import annotations


# ============================================================
# ID КОМПОНЕНТОВ
# ============================================================

FBS_TAB_VALUE = "5"

FBS_EXPORT_BTN_ID = "fbs-orders-export-btn"
FBS_EXPORT_DOWNLOAD_ID = "fbs-orders-export-download"
FBS_EXPORT_LOADING_ID = "fbs-orders-export-loading"


# ============================================================
# ИСТОЧНИКИ ДАННЫХ
#
# Порядок важен: сначала ищем «распакованную» витрину,
# и только если её нет — историческую.
# ============================================================

ORDERS_SOURCES = (
    "orders.unpacked_fbs_orders",
    "orders.fbs_orders_history",
)

SUPPLIES_SOURCES = (
    "orders.unpacked_fbs_supplies",
    "orders.fbs_supplies_history",
)


# ============================================================
# СПРАВОЧНИКИ СКЛАДОВ
#
# Создаёт команда fbs_dicts_etl. Если справочников ещё нет,
# вкладка работает и показывает номера складов — это не повод
# падать.
# ============================================================

WAREHOUSES_SOURCE = "orders.fbs_warehouses"

OFFICES_SOURCE = "orders.fbs_offices"


# ============================================================
# ПОРОГИ СБОРКИ
#
# WB даёт продавцу ограниченное время на сборку заказа.
# SLA_LIMIT_HOURS — момент, после которого заказ считается
# просроченным, SLA_WARNING_HOURS — «жёлтая зона», когда
# заказ ещё в норме, но уже требует внимания.
# ============================================================

SLA_WARNING_HOURS = 36
SLA_LIMIT_HOURS = 48


# Границы корзин по часам. Последняя корзина открытая.
HOUR_BUCKETS = (
    (13, "< 13 часов"),
    (18, "13–18 часов"),
    (24, "18–24 часа"),
    (30, "24–30 часов"),
    (36, "30–36 часов"),
    (48, "36–48 часов"),
)

HOUR_BUCKET_OVERFLOW = "48+ часов"

TOTAL_ROW_LABEL = "ИТОГО"


# ============================================================
# СТАТУСЫ
#
# Названия по документации WB. Неизвестный статус не теряется:
# он показывается как есть, чтобы новый статус на стороне WB
# было видно, а не молча съедено.
# ============================================================

SUPPLIER_STATUS_NAMES = {
    "new": "Новый",
    "confirm": "На сборке",
    "complete": "Собран",
    "cancel": "Отменён продавцом",
    "deliver": "В доставке",
    "receive": "Получен",
    "reject": "Отказ покупателя",
}

WB_STATUS_NAMES = {
    "waiting": "Ожидает сборки",
    "sorted": "Отсортирован",
    "sold": "Получен покупателем",
    "canceled": "Отменён",
    "canceled_by_client": "Отменён покупателем",
    "declined_by_client": "Отклонён покупателем",
    "defect": "Брак",
    "ready_for_pickup": "Готов к выдаче",
    "has_dispute": "Спор",
    "not_in_stock": "Нет на складе",
    "canceled_by_seller": "Отменён продавцом",
}

# Статусы, при которых заказ считается отменённым
# и не участвует в расчёте сроков сборки.
CANCELLED_WB_STATUSES = (
    "canceled",
    "canceled_by_client",
    "declined_by_client",
    "canceled_by_seller",
)

# Заказ «в работе»: продавец подтвердил, WB ждёт сборку.
IN_WORK_SUPPLIER_STATUS = "confirm"
IN_WORK_WB_STATUS = "waiting"


# ============================================================
# НАЗВАНИЯ СКЛАДОВ ОТПРАВЛЕНИЯ
#
# Основной источник — таблица orders.fbs_warehouses, её
# заполняет команда fbs_dicts_etl из ручки WB
# GET /api/v3/warehouses.
#
# Этот словарь — запасной вариант: сюда можно вписать склад,
# которого в справочнике WB уже нет (удалённый или переданный
# другому продавцу), чтобы в отчёте он не остался голым
# номером.
#
# Формат: {1872288: "Основной склад, Химки"}
# ============================================================

WAREHOUSE_NAMES: dict[int, str] = {}


def warehouse_title(value) -> str:
    """Название склада, если оно известно, иначе его номер."""
    if value in (None, ""):
        return "Склад не указан"

    try:
        key = int(value)
    except (TypeError, ValueError):
        return str(value)

    name = WAREHOUSE_NAMES.get(key)

    return f"{name} ({key})" if name else f"Склад {key}"


CARGO_TYPE_NAMES = {
    1: "Обычный",
    2: "СГТ (сверхгабарит)",
    3: "КГТ (крупногабарит)",
}


# ============================================================
# ЦВЕТА
# ============================================================

TEXT_COLOR = "#212529"
MUTED_TEXT_COLOR = "#868E96"
PANEL_BORDER = "#DEE2E6"
BLOCK_BORDER = "#E9ECEF"
PAGE_BACKGROUND = "#F8FAFC"

BLUE = "#228BE6"
BLUE_BG = "#E7F5FF"

GREEN = "#2FB344"
GREEN_BG = "#EBFBEE"

ORANGE = "#F76707"
ORANGE_BG = "#FFF4E6"

RED = "#FA5252"
RED_BG = "#FFF5F5"

VIOLET = "#7950F2"
VIOLET_BG = "#F3F0FF"

TEAL = "#12B886"
TEAL_BG = "#E6FCF5"

CYAN = "#15AABF"
CYAN_BG = "#E3FAFC"

GRAY = "#868E96"
GRAY_BG = "#F1F3F5"
