# gear/app/manpack/config.py
APP_NAME = "manpack_app"
APP_URL = "/apps/app/manpack_app/"
LOANS_APP_URL = "/apps/app/loans_app/"

FX_CURRENCIES = ("USD", "EUR", "CNY", "AMD")
FX_ALERT_PCT = 3.0          # изменение курса за месяц, при котором предупреждаем
BANK_LAG_DAYS = 4           # данные банка старше — предупреждение
LOAN_DUE_DAYS = 60          # погашение займа ближе — предупреждение
CACHE_TTL = 15 * 60

# Новые сотрудники определяются по ПОДСТАТЬЕ ДДС (нижний уровень), а не по
# группе «124000 Затраты на персонал»: в группе есть обучение, ДМС и т. п.
SALARY_SUBITEM_CODES = ("124100",)      # 124100 Заработная плата

# id компонентов
MONTH_ID = "mp-month"
TAB_ID = "mp-tab"
CONTENT_ID = "mp-content"
PACK_BTN_ID = "mp-pack-btn"
PACK_DL_ID = "mp-pack-dl"
PACK_STATUS_ID = "mp-pack-status"

CF_PERIOD_ID = "mp-cf-period"
CF_BANK_ID = "mp-cf-bank"
CF_CP_ID = "mp-cf-cp"
CF_CONTRACT_ID = "mp-cf-contract"
CF_ITEM_ID = "mp-cf-item"
CF_DIR_ID = "mp-cf-dir"
CF_GROUP_ID = "mp-cf-group"
CF_RESULT_ID = "mp-cf-result"

CT_SEARCH_ID = "mp-ct-search"
CT_TYPE_ID = "mp-ct-type"
CT_FILES_ID = "mp-ct-files"
CT_RESULT_ID = "mp-ct-result"

PL_ITEM_ID = "mp-pl-item"
PL_CP_RESULT_ID = "mp-pl-cp-result"
BK_DATE_ID = "mp-bk-date"
BK_RESULT_ID = "mp-bk-result"
FX_CUR_ID = "mp-fx-cur"
FX_RESULT_ID = "mp-fx-result"
FC_BASE_ID = "mp-fc-base"
FC_REV_ID = "mp-fc-rev"
FC_KMD_ID = "mp-fc-kmd"
FC_FIX_ID = "mp-fc-fix"
FC_CONV_ID = "mp-fc-conv"
FC_RESULT_ID = "mp-fc-result"
METHOD_BTN_ID = "mp-method-btn"
METHOD_MODAL_ID = "mp-method-modal"

TABS = [
    ("overview", "Обзор", "solar:home-smile-linear"),
    ("pl", "P&L", "solar:chart-2-linear"),
    ("forecast", "Прогноз и ТБУ", "solar:graph-up-linear"),
    ("cash", "Движение денег", "solar:transfer-horizontal-linear"),
    ("banks", "Счета и остатки", "solar:wallet-money-linear"),
    ("loans", "Займы и кредиты", "solar:hand-money-linear"),
    ("contracts", "Договоры", "solar:document-text-linear"),
    ("upd", "Приходы (УПД)", "solar:box-linear"),
    ("fx", "Курсы валют", "solar:dollar-minimalistic-linear"),
]
EXPORTS = ["summary", "pl", "cash", "banks", "wb", "loans", "contracts", "ct_paid", "upd",
           "fx"]


def x_btn(key):
    return f"mp-x-{key}-btn"


def x_dl(key):
    return f"mp-x-{key}-dl"
