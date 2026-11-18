# gear/app/daily_sales/supplies_cost/config.py
"""Константы вкладки «Поставки WB»."""

SUPPLIES_TAB_VALUE = "6"

SUPPLIES_EXPORT_BTN_ID = "wbs-export-btn"
SUPPLIES_EXPORT_DOWNLOAD_ID = "wbs-export-download"
SUPPLIES_EXPORT_LOADING_ID = "wbs-export-loading"

GRID_SUPPLIES = "wbs-supplies"
GRID_ARTICLES = "wbs-articles"
GRID_BRANDS = "wbs-brands"

# Статусы себестоимости артикула в поставке
COST_OK = "✅ есть"
COST_PART = "⚠️ частично"
COST_NO_UPD = "🔴 нет УПД"
COST_NO_PRICE = "🔴 УПД без цены"

# Статусы поставки WB (statusID)
WB_SUPPLY_STATUS = {
    1: "Не запланировано",
    2: "Запланировано",
    3: "Отгрузка разрешена",
    4: "Идёт приёмка",
    5: "Принято",
    6: "Отгружено на воротах",
}

# Тип упаковки (boxTypeID)
WB_BOX_TYPE = {
    2: "Короба",
    5: "Монопаллеты",
    6: "Суперсейф",
}
