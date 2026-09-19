# gear/app/daily_sales/commercial_review/config.py
"""
Константы коммерческого обзора: палитра, форматы, пороги.

Палитра графиков проверена на различимость при дальтонизме
(OKLab ΔE, порог 8): синий #2A78D6, оранжевый #EB6834,
статусные цвета отдельным набором.
"""

from __future__ import annotations


# ============================================================
# ID КОМПОНЕНТОВ
# ============================================================

CR_OPEN_BTN_ID = "commercial-review-open-btn"
CR_MODAL_ID = "commercial-review-modal"
CR_CLOSE_BTN_ID = "commercial-review-close-btn"
CR_DATE_ID = "commercial-review-date"
CR_DOWNLOAD_BTN_ID = "commercial-review-download-btn"
CR_DOWNLOAD_ID = "commercial-review-download"
CR_LOADING_ID = "commercial-review-loading"


# ============================================================
# ФИРМЕННЫЕ ЦВЕТА
# ============================================================

NAVY = "#2F6656"
NAVY_2 = "#3D7A67"
NAVY_3 = "#1F5E4E"

INK = "#17211E"
INK_2 = "#4A5450"
MUTED = "#8A918E"

#: Шрифты. Заголовки серифом — так отчёт выглядит как документ,
#: а не как дашборд. Стек с запасом: на сервере Georgia может
#: не быть, Liberation и DejaVu есть почти везде.
SERIF = (
    'Georgia, "Times New Roman", "Liberation Serif", '
    '"DejaVu Serif", serif'
)
SANS = (
    'Arial, Helvetica, "Liberation Sans", "DejaVu Sans", sans-serif'
)

#: Тёплая бумага, а не белый экран: на печати и на просмотре
#: документ сразу читается как отчёт, а не как веб-страница.
PAGE_BG = "#FFFDF8"
SURFACE = "#FFFFFF"
SURFACE_SOFT = "#F7F8F5"
TINT = "#E7F1ED"
TINT_2 = "#EDF5F1"
TINT_3 = "#F3F8F6"

LINE = "#D9D9D9"
LINE_SOFT = "#E9EBEA"


# ============================================================
# ЦВЕТА ДАННЫХ
# ============================================================

#: Основная серия на графиках
SERIES_1 = "#2A78D6"
#: Вторая серия (сравнение, прошлый период)
SERIES_2 = "#EB6834"
#: Третья, если без неё никак
SERIES_3 = "#1BAF7A"

#: Состояния. Icon + подпись рядом обязательны —
#: смысл никогда не держится на одном цвете.
GOOD = "#0CA30C"
GOOD_BG = "#EBFBEE"
WARNING = "#FAB219"
WARNING_BG = "#FFF8E6"
SERIOUS = "#EC835A"
SERIOUS_BG = "#FFF4E6"
CRITICAL = "#D03B3B"
CRITICAL_BG = "#FDECEC"

#: Доходы и расходы в таблицах
INCOME = "#3C4043"
EXPENSE = "#7B4437"

GRID = "#E6E9E8"
AXIS = "#C3C6C5"

#: Шкала тепловой карты выручки, от слабого дня к сильному.
HEAT = [
    "#F1F7F3",
    "#DDEEE3",
    "#C2E2CE",
    "#9DD3B3",
    "#6FBF93",
    "#3FA673",
    "#2F8459",
]


# ============================================================
# ПОРОГИ
#
# Собраны в одном месте: по ним движок выводов решает,
# писать про отклонение или промолчать.
# ============================================================

#: Отклонение выручки, ниже которого не стоит и говорить
NOISE_PCT = 3.0

#: Отклонение, после которого это уже проблема
ALERT_PCT = 10.0

#: Выполнение плана: ниже — отстаём
PLAN_BEHIND_PCT = 95.0
PLAN_AHEAD_PCT = 105.0

#: Доля возвратов, после которой разбираются причины
RETURNS_ALERT_PCT = 10.0

#: Маржинальность, ниже которой бьём тревогу
MARGIN_ALERT_PCT = 15.0

#: Доля запаса без продаж и старше 90 дней
STOCK_RISK_ALERT_PCT = 30.0

#: Покрытие запасом: слишком мало и слишком много
COVERAGE_LOW_DAYS = 21
COVERAGE_HIGH_DAYS = 120

#: Концентрация: доля одного склада или бренда
CONCENTRATION_ALERT_PCT = 35.0

#: Сборка FBS
FBS_SLA_HOURS = 48
FBS_OVERDUE_ALERT_PCT = 10.0


# ============================================================
# ВЕСА ВАЖНОСТИ
#
# Чем выше, тем ближе к началу отчёта попадёт вывод.
# ============================================================

SEVERITY_ORDER = {
    "critical": 0,
    "serious": 1,
    "warning": 2,
    "good": 3,
    "neutral": 4,
}


SEVERITY_LABEL = {
    "critical": "Требует решения",
    "serious": "Под контроль",
    "warning": "Обратить внимание",
    "good": "Работает",
    "neutral": "К сведению",
}


SEVERITY_COLOR = {
    "critical": (CRITICAL, CRITICAL_BG),
    "serious": (SERIOUS, SERIOUS_BG),
    "warning": (WARNING, WARNING_BG),
    "good": (GOOD, GOOD_BG),
    "neutral": (MUTED, SURFACE_SOFT),
}
