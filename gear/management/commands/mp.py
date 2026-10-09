# gear/management/commands/mp.pymp.py
# =============================================================================
#  Управленческий пакет (manpack) в Excel: P&L + Cash Flow + пояснения.
#
#  Весь код отчёта намеренно держится в одном файле — команда самодостаточна
#  и не требует ничего, кроме duckdb-подключения (conns.get_duckdb_conn_with_opt)
#  и openpyxl.
#
#  Запуск:
#      python manage.py mp 2026-09-30
#      python manage.py mp 2026-09-30 --start-year 2024
#      python manage.py mp 2026-09-30 --out /tmp/manpack.xlsx
# =============================================================================

from __future__ import annotations

import csv
import datetime as dt
from collections import OrderedDict, defaultdict
from datetime import date
from pathlib import Path
from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from conns import get_duckdb_conn_with_opt

from .sql.read_query import (
    read_sql,
    base,
    base_stocks,
    wb_costs,
    dayly_sales_agg,
    margin,
    opex,
    cf,
    treasury,
    deposits,
    pl_notes,
    wb_payouts,
    ensure_pl_src,
)

try:
    from openpyxl import Workbook, load_workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.formatting.rule import CellIsRule
    from openpyxl.utils import get_column_letter
    from openpyxl.worksheet.properties import PageSetupProperties
except ImportError as exc:  # pragma: no cover
    raise CommandError(
        "Для выгрузки в Excel нужен openpyxl: pip install openpyxl"
    ) from exc


# =============================================================================
#  01. ПАЛИТРА И ТИПОГРАФИКА  (перенос фирменного стиля отчётов из HTML)
# =============================================================================

# Фирменная тёмно-зелёная палитра управленческой отчётности — та же, что в
# reporting/excel/styles/theme.py, чтобы все пакеты компании выглядели
# одинаково. Имена NAVY/NAVY_2 сохранены, чтобы не переписывать разметку
# листов: это просто «основной» и «светлый» фирменный цвет.
NAVY = "2F6656"          # основной тёмно-зелёный: шапки, плашки разделов
NAVY_2 = "3D7A67"        # светлее: чередование годов, «Итого <год>»
NAVY_3 = "1F5E4E"        # темнее: «Итого за период», ссылки, кнопки
ACCENT = "1F5E4E"        # акцентная линия под заголовком листа
TEXT = "1F1F1F"          # основной текст
TEXT_2 = "4A4A4A"        # второстепенный текст
MUTED = "8A8A8A"         # коды статей, подписи, сноски
PAGE = "F7F7F7"          # фон страницы
SURFACE = "FFFFFF"       # фон карточек/таблиц
SURFACE_2 = "F3F8F6"     # чётные строки — прозрачно-зелёный
SURFACE_3 = "EDF5F1"     # колонки «Итого» — едва зелёные
TOTAL_ROW = "E7F1ED"     # строки итогов — светло-зелёные
SURFACE_4 = "E7F1ED"     # светло-зелёный: подзаголовки, кнопки навигации
SURFACE_5 = "FAFCFB"     # почти белый с зелёным подтоном
LINE = "D9D9D9"          # обычная граница
LINE_STRONG = "BFBFBF"   # граница чуть заметнее
ZEBRA_ROW = "F7F7F7"

# Смысловые цвета цифр: доходы — тёмно-серым, расходы — между коричневым
# и тёмно-красным. Знак числа при этом не перекрашивается форматом, цвет
# несёт смысл строки, а не знака.
INCOME = "3C4043"        # цифры доходов и количеств — тёмно-серый
EXPENSE = "7B4437"       # цифры расходов — приглушённый коричневый

OCCUPIED = EXPENSE       # «плохо»
OCCUPIED_BG = "F6E9E4"
FREE = "2F6656"          # «хорошо»
FREE_BG = "E7F1ED"
INFO = "2F75B5"
INFO_BG = "EAF2FB"
WARN = "9A6100"
WARN_BG = "FDF3DE"

FONT = "Helvetica Light"

# Форматы чисел: отрицательные значения — в круглых скобках (финансовый
# стандарт), без красного. Пустое значение — прочерк. Цвет цифр задаётся
# смыслом строки (доход/расход), см. INCOME и EXPENSE выше.
FMT_MONEY = '#,##0;(#,##0);"–"'
FMT_MONEY_DEC = '#,##0.00;(#,##0.00);"–"'
FMT_PCT = '#,##0.0" %";(#,##0.0" %");"–"'
FMT_QTY = '#,##0;(#,##0);"–"'
FMT_PRICE = '#,##0.00;(#,##0.00);"–"'

# Раскладка колонок: слева пустой отступ, затем код и название статьи.
COL_INDENT = 1         # колонка A — пустой отступ слева, как на оглавлении
COL_CODE = 2           # колонка B — код статьи
COL_LABEL = 3          # колонка C — название статьи
COL_NOTE = 4           # колонка D — ссылка на расшифровку (ноту)
COL_FIRST = 5          # с колонки E начинаются месяцы

MONTHS_RU = (
    "янв", "фев", "мар", "апр", "май", "июн",
    "июл", "авг", "сен", "окт", "ноя", "дек",
)


def _side(color=LINE, style="thin"):
    return Side(style=style, color=color)


B_NONE = Border()
B_BOTTOM = Border(bottom=_side())
B_BOTTOM_STRONG = Border(bottom=_side(LINE_STRONG))
B_TOP_ACCENT = Border(top=_side(NAVY, "thin"))
# итоги отбиваются тонкими линиями, а не заливкой во всю ширину
B_TOTAL = Border(top=_side(TEXT), bottom=_side(TEXT))
B_GRAND = Border(top=_side(TEXT, "medium"), bottom=_side(TEXT, "double"))
B_SECTION = Border(bottom=_side(LINE_STRONG))


def fill(color):
    return PatternFill("solid", fgColor=color)


# =============================================================================
#  02. СТРУКТУРА P&L
#      Каждая строка отчёта описывается кортежем:
#        kind  — тип строки (см. ниже)
#        code  — код/номер статьи в колонке A
#        label — название в колонке B
#        spec  — источник значения
#
#      kind:
#        'band'    — заголовок раздела (тёмно-синяя плашка)
#        'item'    — статья из данных            spec = (section, item, sign)
#        'sum'     — сумма строк раздела          spec = section
#        'calc'    — арифметика по другим строкам spec = [(ключ, знак), ...]
#        'ratio'   — отношение двух строк, %      spec = (числитель, знаменатель, знак)
#        'div'     — деление двух строк           spec = (числитель, знаменатель)
#        'tax'     — налог на прибыль из Cash Flow
#        'blank'   — пустая строка
#
#      level:
#        0 — итог/подытог (жирный), 1 — обычная статья, 2 — справочная
# =============================================================================

SEC_REVENUE = "1. ВЫРУЧКА И МАРЖИНАЛЬНОСТЬ "
SEC_UNIT = "2. ЮНИТ ЭКОНОМИКА "
SEC_SELLING = "3. РАСХОДЫ НА РЕАЛИЗАЦИЮ"
SEC_PROMO = "4. ПРОДВИЖЕНИЕ WB"
SEC_OTHER = "5. ПРОЧИЕ ДОХОДЫ И РАСХОДЫ"
SEC_OVERHEAD = "6. НАКЛАДНЫЕ РАСХОДЫ"
SEC_CORP = "7. КОРПОРАТИВНЫЕ РАСХОДЫ"
SEC_FIN = "8. ФИНАНСОВЫЕ РАСХОДЫ"

TAX_SUBITEM = "125200 Налог на прибыль"


def pl_layout():
    """Возвращает список строк P&L в порядке вывода."""
    L = []
    add = L.append

    # ------------------------------------------------ 1. Выручка и маржа
    add(("band", "1", "ВЫРУЧКА И МАРЖИНАЛЬНОСТЬ", None, 0, None))
    add(("item", "1.1", "Продажи до СПП (валовый оборот)",
         (SEC_REVENUE, "1.1. Продажи до СПП", 1), 1, FMT_MONEY))
    add(("item", "1.2", "Продажи по отчёту WB",
         (SEC_REVENUE, "1.2. Продажи по отчету WB", 1), 1, FMT_MONEY))
    add(("item", "1.3", "Продажи после СПП",
         (SEC_REVENUE, "1.3. Продажи после СПП", 1), 1, FMT_MONEY))
    add(("ratio", "1.5", "Скидка WB (СПП), %",
         ("__spp__", "1.1", -1), 2, FMT_PCT))
    add(("item", "1.4", "Продажи без НДС до СПП (чистая выручка)",
        (SEC_REVENUE, "1.4 Продажи без НДС", 1), 0, FMT_MONEY))
    add(("item", "1.6", "Себестоимость проданного товара",
         (SEC_REVENUE, "1.6. Себестоимость", -1), 1, FMT_MONEY))
    add(("calc", "1.7", "МАРЖА ПРОДАЖ (валовая прибыль)",
         [("1.4", 1), ("1.6", 1)], 0, FMT_MONEY))
    add(("ratio", "1.8", "Маржа продаж, % к выручке",
         ("1.7", "1.4", 1), 2, FMT_PCT))
    add(("item", "1.9", "Комиссия WB",
         (SEC_REVENUE, "1.9. Комиссия WB", 1), 1, FMT_MONEY))
    add(("ratio", "1.10", "Комиссия WB, % к выручке",
         ("1.9", "1.4", -1), 2, FMT_PCT))
    add(("calc", "1.11", "МАРЖА ПОСЛЕ КОМИССИИ WB",
         [("1.7", 1), ("1.9", 1)], 0, FMT_MONEY))
    add(("ratio", "1.12", "Маржа после комиссии, % к выручке",
         ("1.11", "1.4", 1), 2, FMT_PCT))
    add(("blank", None, None, None, 1, None))

    # ------------------------------------------------ 3. Расходы на реализацию
    add(("band", "3", "РАСХОДЫ НА РЕАЛИЗАЦИЮ", None, 0, None))
    add(("sum", "3", "Итого расходы на реализацию", SEC_SELLING, 0, FMT_MONEY))
    add(("calc", "GP1", "ВАЛОВАЯ ПРИБЫЛЬ ДО ПРОДВИЖЕНИЯ WB",
         [("1.11", 1), ("3", 1)], 0, FMT_MONEY))
    add(("ratio", "GP1%", "Рентабельность до продвижения, % к выручке",
         ("GP1", "1.4", 1), 2, FMT_PCT))
    add(("blank", None, None, None, 1, None))

    # ------------------------------------------------ 4. Продвижение WB
    add(("band", "4", "ПРОДВИЖЕНИЕ WB", None, 0, None))
    add(("sum", "4", "Итого продвижение WB", SEC_PROMO, 0, FMT_MONEY))
    add(("calc", "GP2", "ВАЛОВАЯ ПРИБЫЛЬ ПОСЛЕ ПРОДВИЖЕНИЯ WB",
         [("GP1", 1), ("4", 1)], 0, FMT_MONEY))
    add(("ratio", "GP2%", "Рентабельность после продвижения, % к выручке",
         ("GP2", "1.4", 1), 2, FMT_PCT))
    add(("blank", None, None, None, 1, None))

    # ------------------------------------------------ 5. Прочие доходы/расходы
    add(("band", "5", "ПРОЧИЕ ДОХОДЫ И РАСХОДЫ", None, 0, None))
    add(("sum", "5", "Итого прочие доходы и расходы", SEC_OTHER, 0, FMT_MONEY))
    add(("calc", "GP3", "ПРИБЫЛЬ ПОСЛЕ ПРОЧИХ ДОХОДОВ/РАСХОДОВ",
         [("GP2", 1), ("5", 1)], 0, FMT_MONEY))
    add(("ratio", "GP3%", "Рентабельность после прочих, % к выручке",
         ("GP3", "1.4", 1), 2, FMT_PCT))
    add(("blank", None, None, None, 1, None))

    # ------------------------------------------------ 6-7. Накладные и корп.
    add(("band", "6", "НАКЛАДНЫЕ РАСХОДЫ", None, 0, None))
    add(("sum", "6", "Итого накладные расходы", SEC_OVERHEAD, 0, FMT_MONEY))
    add(("blank", None, None, None, 1, None))
    add(("band", "7", "КОРПОРАТИВНЫЕ РАСХОДЫ", None, 0, None))
    add(("sum", "7", "Итого корпоративные расходы", SEC_CORP, 0, FMT_MONEY))
    add(("blank", None, None, None, 1, None))

    add(("calc", "EBITDA", "EBITDA (до финансовых расходов)",
         [("GP3", 1), ("6", 1), ("7", 1)], 0, FMT_MONEY))
    add(("ratio", "EBITDA%", "Рентабельность по EBITDA, % к выручке",
         ("EBITDA", "1.4", 1), 2, FMT_PCT))
    add(("blank", None, None, None, 1, None))

    # ------------------------------------------------ 8. Финансовые расходы
    add(("band", "8", "ФИНАНСОВЫЕ РАСХОДЫ", None, 0, None))
    add(("sum", "8", "Итого финансовые расходы", SEC_FIN, 0, FMT_MONEY))
    add(("calc", "EBT", "ПРИБЫЛЬ ДО НАЛОГООБЛОЖЕНИЯ (EBT)",
         [("EBITDA", 1), ("8", 1)], 0, FMT_MONEY))
    add(("tax", "TAX", "Налог на прибыль (факт оплаты, из Cash Flow)",
         None, 1, FMT_MONEY))
    add(("calc", "NP", "ЧИСТАЯ ПРИБЫЛЬ", [("EBT", 1), ("TAX", 1)], 0, FMT_MONEY))
    add(("ratio", "NP%", "Рентабельность по чистой прибыли, % к выручке",
         ("NP", "1.4", 1), 2, FMT_PCT))
    add(("blank", None, None, None, 1, None))

    # ------------------------------------------------ Справочно: юнит-экономика
    add(("band", "2", "СПРАВОЧНО: ЮНИТ-ЭКОНОМИКА", None, 0, None))
    add(("item", "2.1", "Продажи, шт.",
         (SEC_UNIT, "2.1 Продажи, шт.", 1), 1, FMT_QTY))
    add(("item", "2.2", "Продажи по отчёту WB, шт.",
         (SEC_UNIT, "2.2. Продажи по отчету WB, шт.", 1), 1, FMT_QTY))
    add(("item", "2.3", "Без себестоимости, шт.",
         (SEC_UNIT, "2.3. Без себестоимости, шт.", 1), 1, FMT_QTY))
    add(("div", "2.4", "Средняя цена продажи (до СПП)", ("1.1", "2.1"), 2, FMT_PRICE))
    add(("div", "2.5", "Средняя цена после скидки", ("1.3", "2.1"), 2, FMT_PRICE))
    add(("div", "2.6", "Средняя себестоимость единицы", ("1.6n", "2.1"), 2, FMT_PRICE))
    return L


# Разделы, детализируемые статьями (строки раскрываются под плашкой раздела).
PL_DETAIL_SECTIONS = OrderedDict([
    ("3", SEC_SELLING),
    ("4", SEC_PROMO),
    ("5", SEC_OTHER),
    ("6", SEC_OVERHEAD),
    ("7", SEC_CORP),
    ("8", SEC_FIN),
])


# =============================================================================
#  03. ТЕКСТЫ ПОЯСНЕНИЙ (листы NOTES)
#      Формат блока: (заголовок, [абзацы...])
# =============================================================================

def zup_months() -> list:
    """Месяцы, по которым есть начисления зарплаты из ЗУП (data/zup/payroll.parquet)."""
    f = Path(settings.BASE_DIR) / "data" / "zup" / "payroll.parquet"
    if not f.exists():
        return []
    try:
        import pandas as pd
        return sorted({date(d.year, d.month, 1)
                       for d in pd.read_parquet(f, columns=["period"])["period"]})
    except Exception:
        return []


def _month_ranges(months) -> str:
    """[янв, фев, мар, май] → «01.2026–03.2026, 05.2026»."""
    out, start, prev = [], None, None
    for m in months:
        nxt = date(prev.year + prev.month // 12, prev.month % 12 + 1, 1) if prev else None
        if prev and m == nxt:
            prev = m
            continue
        if start:
            out.append(f"{start:%m.%Y}" + (f"–{prev:%m.%Y}" if prev != start else ""))
        start = prev = m
    if start:
        out.append(f"{start:%m.%Y}" + (f"–{prev:%m.%Y}" if prev != start else ""))
    return ", ".join(out)


def payroll_note():
    """Пояснение к зарплате в разделе 6: какие месяцы по начислению, какие по оплате."""
    months = zup_months()
    lines = [
        "Строка «550000 Расходы на персонал»: зарплата, НДФЛ, страховые взносы, подбор, "
        "обучение и самозанятые — расшифровка по статьям в «Расшифровках P&L».",
        "За месяц, по которому есть расчётная ведомость из 1С:ЗУП, зарплата показана "
        "ПО НАЧИСЛЕНИЮ: оплата труда = начислено за месяц минус НДФЛ, НДФЛ — удержанный "
        "из начисления, страховые взносы — начисленные за месяц (единый тариф и взносы "
        "на несчастные случаи). Оплата из банка по статье 550100 за такой месяц не "
        "учитывается, чтобы не задвоить.",
        "За месяц без ведомости ЗУП зарплата показана ПО ОПЛАТЕ ИЗ БАНКА (кассовый метод): "
        "только выплаты сотрудникам по статье 550100; НДФЛ и взносы в такой месяц в "
        "отчёт не попадают.",
        "Подбор персонала, обучение и самозанятые — всегда по оплате из банка.",
        ("По начислению из ЗУП: " + _month_ranges(months) + ". Остальные месяцы — "
         "по оплате из банка.") if months else
        "Ведомостей ЗУП пока нет — все месяцы по оплате из банка.",
    ]
    return ("Зарплата в разделе 6: по начислению или по оплате", lines)


NOTES_PL = [
    ("Назначение отчёта", [
        "Управленческий отчёт о прибылях и убытках (P&L) по методу начисления. "
        "Показывает финансовый результат периода независимо от факта движения денег.",
        "Строится из двух источников: витрины продаж и удержаний маркетплейса "
        "(month_margins_wb_long) и витрины расходов из учётной системы (opex). ",
    ]),
    ("Признание выручки: почему продажи не равны деньгам", [
        "Выручка отражается по всем проданным единицам согласно отчёту маркетплейса. "
        "Себестоимость определяется по FIFO на основании приходов товара. Если "
        "складского остатка по позиции нет, используется её последняя известная "
        "себестоимость. Если приходов по позиции вообще не было, применяется "
        "расчётная себестоимость 620 ₽ за единицу. Количество таких единиц "
        "показано отдельно в строке 2.3 «Без приходов, шт.».",
        "Корректировки продаж и возвратов вынесены из выручки в раздел 5 «Прочие "
        "доходы и расходы», чтобы не искажать маржинальность основной торговой "
        "операции.",
        "Из-за этих двух правил сумма продаж за период не совпадает с денежными "
        "поступлениями из отчёта маркетплейса за тот же период. Сверять P&L и "
        "отчёт WB построчно не следует — это разные базы признания.",
    ]),
    ("Себестоимость: FIFO и пересчёт задним числом", [
        "Себестоимость списывается по FIFO.",
        "Возврат сторнируется на дату фактической продажи, а не на дату "
        "зачисления денег на баланс. Поэтому продажи и себестоимость последних "
        "месяцев ещё будут меняться по мере поступления возвратов: уже "
        "выгруженный отчёт за закрытый месяц при следующей выгрузке может "
        "показать другие цифры.",
        "Практический вывод: последние две-три недели отчёта считаются "
        "предварительными, окончательными их можно считать после того, как "
        "пройдёт основная волна возвратов.",
    ]),
    ("Номенклатура и УПД: открытая проблема", [
        "Сопоставление номенклатуры пока не решено. УПД поступают с задержкой, а "
        "связь между позицией в УПД и артикулом из отчёта продаж восстанавливается "
        "не всегда.",
        "При обновлении карточек товара и загрузке новых УПД граф FIFO "
        "перестраивается заново, и себестоимость уже закрытых периодов может "
        "измениться. Величина сдвига зависит от того, какие данные пришли.",
        "Пока проблема не закрыта, себестоимость и валовая маржа прошлых периодов "
        "не являются окончательными. Расхождения между двумя выгрузками за одну и "
        "ту же дату — ожидаемое поведение, а не ошибка.",
    ]),
    ("Расходы WB: расхождение P&L и Dashboard", [
        "Расходы маркетплейса на реализацию (раздел 3) и продвижение (раздел 4) "
        "учтены в P&L кассовым методом — в том месяце, когда площадка фактически "
        "произвела удержание.",
        "В Dashboard те же расходы разнесены на единицы товара, потому что "
        "оперативная оценка по дням требует привязки расхода к конкретной продаже. "
        "То есть в Dashboard расход «размазан» по единицам, а в P&L стоит целиком "
        "в месяце удержания.",
        "Поэтому цифры по этим статьям в P&L и в Dashboard не совпадают. "
        "За период в целом суммы сходятся, расхождение только в распределении "
        "между месяцами.",
    ]),
    ("Раздел 1. Выручка и маржинальность", [
        "1.1 Продажи до СПП — валовый оборот по ценам продавца, до скидки постоянного "
        "покупателя (СПП), финансируемой маркетплейсом.",
        "1.3 Продажи после СПП — оборот по фактическим ценам покупателя.",
        "1.5 Скидка WB (СПП), % = (1.1 − 1.3) / 1.1. Показывает глубину субсидии площадки.",
        "1.4 Продажи без НДС — чистая выручка, база для всех показателей рентабельности "
        "в этом отчёте.",
        "1.6 Себестоимость — учётная себестоимость проданного товара (COGS).",
        "1.7 Маржа продаж = 1.4 + 1.6 — валовая прибыль до удержаний маркетплейса.",
        "1.9 Комиссия WB — комиссия площадки с продаж и выкупов; 1.11 Маржа после "
        "комиссии = 1.7 + 1.9.",
    ]),
    ("Раздел 3. Расходы на реализацию", [
        "Удержания маркетплейса, связанные с физическим исполнением заказов: логистика, "
        "хранение, приёмка, штрафы, участие в программе лояльности.",
        "Источник — витрина wb_costs, все счета кроме «Other income / loss» и "
        "«WB Deduction».",
        "Суммы показаны БЕЗ НДС. Выручка (1.4) и комиссия (1.9) в этом отчёте тоже "
        "очищены от НДС, поэтому расходы считаются по тому же правилу — иначе "
        "валовая прибыль получалась бы вычитанием сумм с НДС из выручки без НДС. "
        "Эти же суммы без НДС стоят в строке 3.3 листа «Юнит-экономика».",
        "Промежуточный итог «Валовая прибыль до продвижения WB» = маржа после комиссии "
        "плюс итог раздела 3. Это результат от основной торговой операции до любых "
        "маркетинговых вложений.",
    ]),
    ("Раздел 4. Продвижение WB", [
        "Платное продвижение внутри площадки: услуги WB (реклама, буст), работа с "
        "отзывами, прочие маркетинговые удержания. Источник — wb_costs, счёт "
        "«WB Deduction».",
        "Суммы показаны БЕЗ НДС, как и весь остальной отчёт. Эти же суммы стоят "
        "в строке 3.4 листа «Юнит-экономика».",
        "Промежуточный итог «Валовая прибыль после продвижения WB» показывает, сколько "
        "остаётся от торговой операции после расходов на трафик. Ключевой показатель "
        "эффективности работы с площадкой.",
    ]),
    ("Раздел 5. Прочие доходы и расходы", [
        "Корректировки продаж и возвратов, корректировки по программам WB, досрочное "
        "снятие средств, курсовые разницы, финансовые доходы, прочие расходы.",
        "Источники: wb_costs (счёт «Other income / loss») и счета 420000 учётной "
        "системы, кроме группы 590100.",
        "Внимание: суммы по этому разделу показаны С НДС, в отличие от разделов 3 и 4. "
        "Здесь собраны разные по природе статьи — корректировки самой выручки и услуги "
        "площадки, — и единое правило по НДС к ним не применяется. Требует разбора "
        "по каждой статье.",
        "Промежуточный итог «Прибыль после прочих доходов и расходов» очищает результат "
        "от разовых и неторговых эффектов.",
    ]),
    ("Разделы 6-7. Накладные и корпоративные расходы", [
        "Раздел 6 — расходы, обеспечивающие операционную деятельность: закупочные "
        "услуги, маркетинг вне площадки, комиссии банков, аренда, цифровые сервисы, "
        "материалы, персонал. Счета 610000 (кроме статьи 540101).",
        "Раздел 7 — расходы корпоративного уровня: офис, консалтинг и профессиональные "
        "услуги, представительские. Счета 620000.",
        "EBITDA = прибыль после прочих доходов и расходов минус разделы 6 и 7. "
        "Амортизация в периметре отчёта не начисляется, поэтому показатель совпадает "
        "с операционной прибылью до финансовых расходов.",
    ]),
    ("Раздел 8, налог и чистая прибыль", [
        "Раздел 8 — проценты и комиссии по банковским кредитам, займам физических и "
        "юридических лиц, страхование по кредитам. Счета 630000.",
        "Прибыль до налогообложения (EBT) = EBITDA минус финансовые расходы.",
        "Налог на прибыль берётся из отчёта о движении денежных средств — статья "
        "«125200 Налог на прибыль», по факту оплаты (включая авансовые платежи и "
        "возвраты переплат). Это кассовый, а не начисленный налог: в отдельных месяцах "
        "он может быть положительным при возврате из бюджета.",
        "Чистая прибыль = EBT плюс налог (налог уже со знаком минус при оплате).",
    ]),
    ("Показатели рентабельности", [
        "Рентабельность по EBITDA, % = EBITDA / чистая выручка (строка 1.4).",
        "Рентабельность по чистой прибыли, % = чистая прибыль / чистая выручка.",
        "Все проценты в отчёте считаются к строке 1.4 «Продажи без НДС», чтобы "
        "показатели были сопоставимы между месяцами и с внешними бенчмарками.",
    ]),
    ("Как читать колонки", [
        "Колонка месяца — значение за календарный месяц (дата = последний день "
        "месяца).",
        "Месяцы сгруппированы по годам: завершённые годы свёрнуты, видны только их "
        "итоговые колонки «Итого <год>»; текущий год раскрыт помесячно. Развернуть "
        "год можно кнопкой «+» над таблицей.",
        "«Итого за период» — сумма годовых итогов. Для процентов и средних значений "
        "колонки итогов пересчитываются по формуле, а не суммируются.",
    ]),
]

NOTES_CF = [
    ("Назначение отчёта", [
        "Отчёт о движении денежных средств (Cash Flow) прямым методом: все поступления "
        "и платежи сгруппированы по виду деятельности, операции, статье и подстатье.",
        "Источник — витрина cf_to_csv, транзакционный уровень банковских выписок и "
        "баланса WB. ",
    ]),
    ("100000 Операционная деятельность", [
        "110000 Поступления — выручка от продажи товаров через маркетплейсы и выкуп "
        "товара маркетплейсом.",
        "120000 Платежи — закупка товара и связанные с ней расходы (121000), зачёт "
        "удержаний WB из выручки (122000), накладные и корпоративные расходы (123000), "
        "затраты на персонал (124000), налоги и сборы (125000).",
        "Блок 122000 не является денежным оттоком с расчётного счёта: это удержания "
        "площадки, которые зачитываются против выручки на балансе WB. Они показаны "
        "развёрнуто, чтобы операционный поток сходился с валовыми поступлениями.",
    ]),
    ("200000 Инвестиционная деятельность", [
        "Приобретение основных средств и вложения в инфраструктуру. ",
    ]),
    ("300000 Финансовая деятельность", [
        "310000 Поступления — взносы учредителей, привлечение кредитов и займов, "
        "проценты по депозитам, возврат размещённых средств.",
        "320000 Отток — погашение тела кредитов и займов, оплата процентов и комиссий "
        "за обслуживание, размещение средств на депозитах и выдача займов.",
        "Размещение и возврат депозитов показаны в обе стороны: это управление "
        "ликвидностью, а не финансовый результат.",
    ]),
    ("400000 Внутригрупповые транзакции", [
        "Переводы между собственными счетами, валютная конвертация и отражение курсовых "
        "разниц.",
        "Переводы между счетами взаимно погашаются и не влияют на итог. Курсовые "
        "разницы по валютным остаткам влияют на остаток денежных средств, поэтому блок "
        "включён в итоговое изменение денежных средств — иначе остаток на конец периода "
        "не сойдётся с фактическими остатками по счетам.",
    ]),
    ("Остатки и контроль", [
        "Остаток на начало периода рассчитан накопленным итогом по всем операциям до "
        "первого показанного месяца.",
        "Остаток на конец = остаток на начало плюс чистый денежный поток за период. "
        "Контроль: остаток на конец последнего месяца должен совпадать с суммой "
        "остатков по банковским счетам и балансу WB на отчётную дату.",
    ]),
    ("Связь с P&L", [
        "Cash Flow и P&L расходятся закономерно: P&L строится по начислению, Cash Flow — "
        "по факту движения денег.",
        "Основные источники разрыва: закупка товара попадает в Cash Flow в момент "
        "оплаты, а в P&L — в момент продажи через себестоимость; привлечение и "
        "погашение займов не отражается в P&L; налог в P&L взят по факту оплаты из "
        "этого отчёта.",
        "Отдельно: выручка в P&L признаётся только по сопоставленным с "
        "себестоимостью единицам, а корректировки продаж и возвратов вынесены в "
        "раздел 5. Поэтому продажи в P&L не равны поступлениям от маркетплейса в "
        "Cash Flow даже до учёта всех перечисленных факторов — подробности на "
        "листе «Пояснения P&L».",
    ]),
]


# =============================================================================
#  04. ХЕЛПЕРЫ
# =============================================================================

def month_label(d: date) -> str:
    return "%s %d" % (MONTHS_RU[d.month - 1], d.year)


def last_day(d: date) -> date:
    if d.month == 12:
        return date(d.year, 12, 31)
    return date(d.year, d.month + 1, 1) - dt.timedelta(days=1)


def write(ws, row, col, value, *, font=None, fmt=None, fillc=None,
          border=None, align=None, wrap=False, indent=0):
    c = ws.cell(row=row, column=col, value=value)
    if font is not None:
        c.font = font
    if fmt is not None:
        c.number_format = fmt
    if fillc is not None:
        c.fill = fill(fillc)
    if border is not None:
        c.border = border
    if align is not None or wrap or indent:
        c.alignment = Alignment(horizontal=align, vertical="center",
                                wrap_text=wrap, indent=indent)
    return c

def apply_zebra(ws, first_row, last_row, first_col, last_col):
    """
    Элегантная зебра для табличных строк.
    Красит только пустые ячейки и не перебивает итоги, шапки и колонки итогов.
    """
    zebra = fill(ZEBRA_ROW)

    for row in range(first_row, last_row + 1):
        if row % 2:
            continue

        for col in range(first_col, last_col + 1):
            cell = ws.cell(row=row, column=col)

            # Не перебиваем уже заданные смысловые заливки
            if cell.fill.fill_type:
                continue

            cell.fill = zebra


def apply_column_dividers(ws, first_row, last_row, first_col, last_col):
    """
    Тонкие вертикальные разделители колонок.
    Сохраняет уже заданные верхние/нижние границы строк.
    """
    for row in range(first_row, last_row + 1):
        for col in range(first_col, last_col):
            cell = ws.cell(row=row, column=col)
            old = cell.border

            cell.border = Border(
                left=old.left,
                right=_side(LINE),
                top=old.top,
                bottom=old.bottom,
            )

TOC_SHEET_NAME = "Оглавление"


def title_band(ws, title, subtitle, ncols, extra=None, show_back=True):
    """
    Шапка листа: кнопка возврата, чёрный заголовок и серые подписи на белом
    фоне, снизу — тонкая фирменная линия. Тяжёлых заливок во всю ширину
    намеренно нет: цветом выделяются только шапка таблицы и итоги.
    """
    if show_back:
        back_to_toc(ws)

    ws.merge_cells(start_row=2, start_column=COL_CODE, end_row=2, end_column=ncols)
    c = ws.cell(row=2, column=COL_CODE, value=title)
    c.font = Font(name=FONT, size=14, bold=True, color=TEXT)
    c.alignment = Alignment(horizontal="left", vertical="center")

    ws.merge_cells(start_row=3, start_column=COL_CODE, end_row=3, end_column=ncols)
    c = ws.cell(row=3, column=COL_CODE, value=subtitle)
    c.font = Font(name=FONT, size=9, color=TEXT_2)
    c.alignment = Alignment(horizontal="left", vertical="center")

    if extra:
        ws.merge_cells(start_row=4, start_column=COL_CODE, end_row=4, end_column=ncols)
        c = ws.cell(row=4, column=COL_CODE, value=extra)
        c.font = Font(name=FONT, size=9, color=MUTED)
        c.alignment = Alignment(horizontal="left", vertical="center")

    for col in range(COL_CODE, ncols + 1):
        ws.cell(row=5, column=col).border = Border(bottom=_side(NAVY))

    ws.row_dimensions[1].height = 16
    ws.row_dimensions[2].height = 24
    ws.row_dimensions[3].height = 14
    ws.row_dimensions[4].height = 14
    ws.row_dimensions[5].height = 6


def back_to_toc(ws, row=1, col_start=COL_CODE, col_end=COL_LABEL):
    """Кнопка возврата на оглавление: светло-зелёная плашка с зелёным
    текстом, без синей подчёркнутой ссылки."""
    ws.merge_cells(start_row=row, start_column=col_start,
                   end_row=row, end_column=col_end)
    c = ws.cell(row=row, column=col_start, value="\u2190  Оглавление")
    c.hyperlink = "#'%s'!A1" % TOC_SHEET_NAME
    c.font = Font(name=FONT, size=9, bold=True, color=NAVY_3, underline=None)
    c.alignment = Alignment(horizontal="left", vertical="center", indent=1)
    for cc in range(col_start, col_end + 1):
        cell = ws.cell(row=row, column=cc)
        cell.fill = fill(SURFACE_4)
        cell.border = Border(bottom=_side(LINE))
    ws.row_dimensions[row].height = 16


def sheet_setup(ws, landscape=True):
    ws.sheet_view.showGridLines = False
    ws.page_setup.orientation = "landscape" if landscape else "portrait"
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)
    ws.print_options.horizontalCentered = True


# -----------------------------------------------------------------------------
#  Модель колонок: месяцы сгруппированы по годам, после каждого года — колонка
#  «Итого <год>», в самом конце — «Итого за период». Завершённые годы
#  свёрнуты (видны только их итоги), текущий год раскрыт.
# -----------------------------------------------------------------------------



def make_columns(months):
    """[(kind, month, year)] — план колонок, kind: month | year | grand."""
    cols = []
    for y in sorted({m.year for m in months}):
        for m in [mm for mm in months if mm.year == y]:
            cols.append(("month", m, y))
        cols.append(("year", None, y))
    cols.append(("grand", None, None))
    return cols


def L(i):
    """Буква колонки Excel по индексу плана колонок."""
    return get_column_letter(COL_FIRST + i)


def year_span(cols, year):
    """Буквы первой и последней месячной колонки года."""
    idx = [i for i, c in enumerate(cols) if c[0] == "month" and c[2] == year]
    return L(idx[0]), L(idx[-1])


def year_total_cols(cols):
    return [i for i, c in enumerate(cols) if c[0] == "year"]


def period_formula(cols, i, row, values_by_month):
    """
    Значение ячейки строки-данных в колонке i:
      месяц  — число из данных,
      год    — SUM по месяцам этого года,
      период — сумма годовых итогов (без двойного счёта).
    """
    kind, m, y = cols[i]
    if kind == "month":
        return values_by_month(m)
    if kind == "year":
        c1, c2 = year_span(cols, y)
        return "=SUM(%s%d:%s%d)" % (c1, row, c2, row)
    return "=" + "+".join("%s%d" % (L(j), row) for j in year_total_cols(cols))


def columns_header(ws, cols, hdr_year, hdr, report_year, note_header=None):
    """
    Две строки шапки: светло-зелёная полоса года и тёмно-зелёная строка
    месяцев. Единственное «тяжёлое» место на листе — так таблица читается,
    но лист не выглядит перегруженным цветом.
    """
    f_hdr = Font(name=FONT, size=9, bold=True, color="FFFFFF")
    f_year = Font(name=FONT, size=9, bold=True, color=NAVY_3)

    for key, title in ((COL_CODE, "КОД"), (COL_LABEL, "СТАТЬЯ"),
                       (COL_NOTE, note_header or "")):
        ws.merge_cells(start_row=hdr_year, start_column=key,
                       end_row=hdr, end_column=key)
        write(ws, hdr_year, key, title, font=f_hdr, fillc=NAVY,
              align="left" if key == COL_LABEL else "center",
              indent=1 if key == COL_LABEL else 0)
        ws.cell(row=hdr, column=key).fill = fill(NAVY)

    years = sorted({c[2] for c in cols if c[2] is not None})
    for y in years:
        idx = [i for i, c in enumerate(cols) if c[2] == y]
        ws.merge_cells(start_row=hdr_year, start_column=COL_FIRST + idx[0],
                       end_row=hdr_year, end_column=COL_FIRST + idx[-1])
        write(ws, hdr_year, COL_FIRST + idx[0], str(y), font=f_year,
              fillc=SURFACE_4, align="center")
        for i in idx:
            c = ws.cell(row=hdr_year, column=COL_FIRST + i)
            c.fill = fill(SURFACE_4)
            c.border = Border(bottom=_side(LINE))

    grand = len(cols) - 1
    ws.merge_cells(start_row=hdr_year, start_column=COL_FIRST + grand,
                   end_row=hdr, end_column=COL_FIRST + grand)
    write(ws, hdr_year, COL_FIRST + grand, "ИТОГО ЗА ПЕРИОД", font=f_hdr,
          fillc=NAVY_3, align="center", wrap=True)

    for i, (kind, m, y) in enumerate(cols):
        if kind == "month":
            write(ws, hdr, COL_FIRST + i, MONTHS_RU[m.month - 1].upper(),
                  font=f_hdr, fillc=NAVY, align="center")
        elif kind == "year":
            write(ws, hdr, COL_FIRST + i, "ИТОГО %d" % y, font=f_hdr,
                  fillc=NAVY_2, align="center", wrap=True)

    ws.row_dimensions[hdr_year].height = 16
    ws.row_dimensions[hdr].height = 20


def columns_layout(ws, cols, report_year):
    """Ширины и группировка: завершённые годы сворачиваются."""
    for i, (kind, m, y) in enumerate(cols):
        ws.column_dimensions[L(i)].width = 14.5 if kind == "month" else 16.5
    ws.column_dimensions[L(len(cols) - 1)].width = 17

    ws.sheet_properties.outlinePr.summaryRight = True
    for y in sorted({c[2] for c in cols if c[2] is not None}):
        c1, c2 = year_span(cols, y)
        ws.column_dimensions.group(c1, c2, outline_level=1,
                                   hidden=(y < report_year))


# =============================================================================
#  05. ЛИСТ P&L
# =============================================================================

def build_pl(ws, pl_data, tax_by_month, months, report_date, as_of=None,
             note_anchors=None, rowmap_out=None):
    as_of = as_of or report_date
    """
    pl_data      — {(me, section, item): value}
    tax_by_month — {me: value}  (налог на прибыль из Cash Flow, знак как в CF)
    months       — список дат (последний день месяца) по возрастанию
    """
    # в детализацию попадают только статьи с движением в показанном периоде
    sections = defaultdict(set)
    for (me, sec, itm), v in pl_data.items():
        if me in months and v:
            sections[sec].add(itm)

    cols = make_columns(months)
    ncols = COL_FIRST + len(cols) - 1

    sheet_setup(ws)
    title_band(
        ws,
        "ОТЧЁТ О ПРИБЫЛЯХ И УБЫТКАХ (P&L)",
        "Управленческая отчётность (management pack) · метод начисления",
        ncols,
        extra="Российский рубль (RUB) · дата отчёта: %s · период: %s — %s · "
              "завершённые годы свёрнуты, их итоги видны"
              % (as_of.strftime("%d.%m.%Y"),
                 month_label(months[0]), month_label(months[-1])),
    )

    # ---- шапка таблицы: полоса года + месяцы
    hdr_year, hdr = 6, 7
    columns_header(ws, cols, hdr_year, hdr, report_date.year, note_header="НОТА")

    # ---- раскладка строк: сначала распределяем номера строк
    layout = pl_layout()
    plan = []          # (kind, code, label, spec, level, fmt)
    for spec in layout:
        kind, code, label, src, level, fmt = spec
        if kind == "band" and code in PL_DETAIL_SECTIONS:
            plan.append(spec)
            sec = PL_DETAIL_SECTIONS[code]
            for itm in sorted(sections.get(sec, ())):
                plan.append(("item", "", itm, (sec, itm, 1), 1, FMT_MONEY))
        else:
            plan.append(spec)

    rowmap = {}
    r = hdr + 1
    for kind, code, label, src, level, fmt in plan:
        # плашки разделов не участвуют в формулах: код раздела должен
        # указывать на строку «Итого ...», а не на заголовок
        if code and kind != "band":
            rowmap.setdefault(code, r)
        r += 1

    # ---- значения
    def val(sec, itm, m):
        return pl_data.get((m, sec, itm))

    def colletter(i):
        return get_column_letter(i)

    f_band = Font(name=FONT, size=10, bold=True, color=TEXT)
    f_label = Font(name=FONT, size=10, color=TEXT)
    f_label_total = Font(name=FONT, size=10, bold=True, color=TEXT)
    f_code = Font(name=FONT, size=8, color=MUTED)
    f_grand = Font(name=FONT, size=10, bold=True, color=TEXT)

    # цифры: доходы и количества — тёмно-серым, расходы — приглушённым
    # коричневым; отрицательные значения дополнительно в скобках
    f_income = Font(name=FONT, size=10, color=INCOME)
    f_expense = Font(name=FONT, size=10, color=EXPENSE)
    f_total_income = Font(name=FONT, size=10, bold=True, color=TEXT)
    f_total_expense = Font(name=FONT, size=10, bold=True, color=EXPENSE)

    # проценты — спокойным серым, без курсива и лишнего цвета
    f_ratio_good = Font(name=FONT, size=9, color=TEXT_2)
    f_ratio_cost = Font(name=FONT, size=9, color=TEXT_2)
    f_label_ratio = Font(name=FONT, size=9, color=TEXT_2)

    GRAND = {"EBITDA", "NP"}

    # разделы и статьи, которые по смыслу являются расходами
    EXPENSE_SECTIONS = {SEC_SELLING, SEC_PROMO, SEC_OTHER,
                        SEC_OVERHEAD, SEC_CORP, SEC_FIN}
    EXPENSE_ITEM_CODES = {"1.6", "1.9"}          # себестоимость, комиссия WB
    COST_RATIO_CODES = {"1.5", "1.10"}           # скидка СПП, комиссия WB в %
    
    
    def split_code_from_label(label):
        if not label:
            return "", label

        text = str(label).strip()
        head, sep, tail = text.partition(" ")

        if not sep:
            return "", label

        clean_head = head.rstrip(".")

        # Ловим оба варианта:
        # 3.1 Логистика
        # 3.1. Логистика
        # 590200 Курсовые разницы
        if clean_head.replace(".", "").isdigit():
            return clean_head, tail.strip()

        return "", label

    r = hdr + 1
    for kind, code, label, src, level, fmt in plan:
        stripe = (r % 2 == 0)

        if kind == "blank":
            ws.row_dimensions[r].height = 6
            r += 1
            continue

        if kind == "band":
            ws.merge_cells(start_row=r, start_column=COL_CODE,
                           end_row=r, end_column=COL_LABEL)
            write(ws, r, COL_CODE, "%s. %s" % (code, label) if code else label,
                  font=f_band, align="left", indent=1, border=B_SECTION)
            for cc in range(COL_CODE, ncols + 1):
                ws.cell(row=r, column=cc).border = B_SECTION
            ws.row_dimensions[r].height = 18
            r += 1
            continue

        is_grand = code in GRAND
        is_total = level == 0

        # расход ли это по смыслу: статья расходного раздела, итог такого
        # раздела, себестоимость, комиссия WB или налог на прибыль
        is_expense_row = (
            (kind == "item" and src and src[0] in EXPENSE_SECTIONS)
            or (kind == "sum" and src in EXPENSE_SECTIONS)
            or code in EXPENSE_ITEM_CODES
            or kind == "tax"
        )

        if is_grand:
            fnt = f_total_expense if is_expense_row else f_grand
            fnt_label = f_grand
            bg, bd = TOTAL_ROW, B_GRAND
        elif is_total:
            fnt = f_total_expense if is_expense_row else f_total_income
            fnt_label = f_label_total
            bg, bd = TOTAL_ROW, B_TOTAL
        elif kind in ("ratio", "div"):
            fnt = f_ratio_cost if code in COST_RATIO_CODES else f_ratio_good
            if kind == "div":
                fnt = Font(name=FONT, size=9, color=TEXT_2)
            fnt_label = f_label_ratio
            bg, bd = None, B_BOTTOM
        else:
            fnt = f_expense if is_expense_row else f_income
            fnt_label = f_label
            bg, bd = None, B_BOTTOM

        display_code = code if (code and code[0].isdigit()) else ""
        display_label = label

        # Для детальных строк типа "3.1. Логистика" переносим код в колонку КОД
        if not display_code and kind == "item":
            parsed_code, parsed_label = split_code_from_label(label)
            if parsed_code:
                display_code = parsed_code
                display_label = parsed_label

        write(ws, r, COL_CODE, display_code,
            font=f_code if not is_grand else f_grand,
            fillc=bg, border=bd, align="left", indent=1)

        write(ws, r, COL_LABEL, display_label, font=fnt_label, fillc=bg, border=bd,
            align="left", indent=1 if is_total else 2)

        # колонка «НОТА»: ссылка на блок расшифровки этой строки
        note_row = None
        if note_anchors:
            if kind == "sum":
                note_row = note_anchors.get((src, None))
            elif kind == "item" and src and not code:
                note_row = note_anchors.get((src[0], src[1]))
        note_cell = write(ws, r, COL_NOTE, "\u2192" if note_row else None,
                        font=Font(name=FONT, size=14, bold=True, color=NAVY_3),
                        fillc=bg, border=bd, align="center")
        if note_row:
            note_cell.hyperlink = "#'%s'!C%d" % (NOTES_SHEET_NAME, note_row)

        for i in range(len(cols)):
            col = COL_FIRST + i
            cl = L(i)
            cell_fmt = fmt or FMT_MONEY
            v = None

            if kind == "item":
                sec, itm, sign = src
                v = period_formula(
                    cols, i, r,
                    lambda m, s=sec, it=itm, sg=sign:
                        None if val(s, it, m) is None else val(s, it, m) * sg)

            elif kind == "sum":
                sec = src
                items = sorted(sections.get(sec, ()))
                if items:
                    r1 = rowmap_first(rowmap, plan, hdr, sec)
                    v = "=SUM(%s%d:%s%d)" % (cl, r1, cl, r1 + len(items) - 1)
                else:
                    v = 0

            elif kind == "calc":
                parts = []
                for key, sgn in src:
                    rr = rowmap.get(key)
                    if rr is None:
                        continue
                    parts.append("%s%s%d" % ("+" if sgn > 0 else "-", cl, rr))
                v = "=" + "".join(parts).lstrip("+")

            elif kind == "ratio":
                num, den, sgn = src
                if num == "__spp__":
                    r11, r13 = rowmap["1.1"], rowmap["1.3"]
                    rd = rowmap[den]
                    v = ("=IF(%s%d=0,\"\",(%s%d-%s%d)/%s%d*100)"
                         % (cl, rd, cl, r11, cl, r13, cl, rd))
                else:
                    rn, rd = rowmap[num], rowmap[den]
                    v = ("=IF(%s%d=0,\"\",%s%s%d/%s%d*100)"
                         % (cl, rd, "-" if sgn < 0 else "", cl, rn, cl, rd))

            elif kind == "div":
                num, den = src
                rn = rowmap[num.rstrip("n")]
                rd = rowmap[den]
                neg = "-" if num.endswith("n") else ""
                v = "=IF(%s%d=0,\"\",%s%s%d/%s%d)" % (cl, rd, neg, cl, rn, cl, rd)

            elif kind == "tax":
                v = period_formula(cols, i, r, lambda m: tax_by_month.get(m))

            fillv = bg
            if cols[i][0] != "month" and not (is_total or is_grand):
                fillv = SURFACE_3
            write(ws, r, col, v, font=fnt, fmt=cell_fmt, fillc=fillv,
                  border=bd, align="right")

        ws.row_dimensions[r].height = 17 if not (is_total or is_grand) else 19
        r += 1

    # ---- ширины, группировка и закрепление
    ws.column_dimensions["A"].width = 3
    ws.column_dimensions["B"].width = 9
    ws.column_dimensions["C"].width = 56
    ws.column_dimensions["D"].width = 7
    apply_zebra(ws, hdr + 1, r - 1, COL_CODE, ncols)
    apply_column_dividers(ws, hdr, r - 1, COL_CODE, ncols)
    columns_layout(ws, cols, report_date.year)
    ws.freeze_panes = ws.cell(row=hdr + 1, column=COL_FIRST)
    ws.print_title_rows = "1:%d" % hdr
    if rowmap_out is not None:
        rowmap_out.update(rowmap)
    return r


def rowmap_first(rowmap, plan, hdr, section):
    """Номер первой строки-детализации указанного раздела."""
    r = hdr + 1
    for kind, code, label, src, level, fmt in plan:
        if kind == "item" and src and src[0] == section and code == "":
            return r
        r += 1
    return hdr + 1


# =============================================================================
#  06. ЛИСТ CASH FLOW
# =============================================================================

def _row_ranges(first_row, last_row, exclude):
    """Непрерывные диапазоны строк [first_row..last_row] без строк exclude."""
    spans, start = [], None
    for r in range(first_row, last_row + 1):
        if r in exclude:
            if start is not None:
                spans.append((start, r - 1))
                start = None
        elif start is None:
            start = r
    if start is not None:
        spans.append((start, last_row))
    return spans


def color_amounts_by_sign(ws, spans, col_first, col_last):
    """
    Красит цифры по знаку: поступления/доходы — тёмно-серым, платежи/
    расходы — коричнево-красным. Условным форматированием, потому что
    большая часть ячеек — формулы и знак заранее неизвестен. Жирность и
    заливка строки при этом сохраняются, меняется только цвет цифр.
    """
    if not spans:
        return
    rng = " ".join(
        "%s%d:%s%d" % (get_column_letter(col_first), a,
                       get_column_letter(col_last), b)
        for a, b in spans
    )
    ws.conditional_formatting.add(
        rng, CellIsRule(operator="lessThan", formula=["0"],
                        font=Font(name=FONT, color=EXPENSE)))
    ws.conditional_formatting.add(
        rng, CellIsRule(operator="greaterThan", formula=["0"],
                        font=Font(name=FONT, color=INCOME)))


CF_TRANSFER_ACTIVITY = "400000 Внутрегрупповые трансакции"


def build_cf(ws, cf_data, months, opening, report_date, as_of=None):
    as_of = as_of or report_date
    """
    cf_data — {(me, activity, operation, item, subitem): amount}
    opening — остаток денежных средств на начало первого показанного месяца
    """
    n_months = len(months)
    mindex = {m: i for i, m in enumerate(months)}

    # Разворачиваем транзакции в дерево вид деятельности → операция → статья →
    # подстатья и сразу считаем помесячные суммы. Ветки без движения в
    # показанном периоде в отчёт не попадают.
    # вид деятельности → операция → статья → подстатья → контрагент → договор
    tree = OrderedDict()
    for key, v in cf_data.items():
        me, act, op, itm, sub, cp, contract = key
        i = mindex.get(me)
        if i is None or not v:
            continue
        vals = (tree.setdefault(act, OrderedDict())
                    .setdefault(op, OrderedDict())
                    .setdefault(itm, OrderedDict())
                    .setdefault(sub, OrderedDict())
                    .setdefault(cp, OrderedDict())
                    .setdefault(contract, [0.0] * n_months))
        vals[i] += v

    def _prune(node):
        """Убирает ветки без движения в показанном периоде."""
        for k in list(node):
            child = node[k]
            if isinstance(child, list):
                if not any(round(x, 2) for x in child):
                    del node[k]
            else:
                _prune(child)
                if not child:
                    del node[k]

    _prune(tree)

    cols = make_columns(months)
    ncols = COL_FIRST + len(cols) - 1

    sheet_setup(ws)
    title_band(
        ws,
        "ОТЧЁТ О ДВИЖЕНИИ ДЕНЕЖНЫХ СРЕДСТВ (CASH FLOW)",
        "Управленческая отчётность (management pack) · прямой метод",
        ncols,
        extra="Российский рубль (RUB) · дата отчёта: %s · период: %s — %s "

              % (as_of.strftime("%d.%m.%Y"),
                 month_label(months[0]), month_label(months[-1])),
    )

    hdr_year, hdr = 6, 7
    columns_header(ws, cols, hdr_year, hdr, report_date.year)

    f_item = Font(name=FONT, size=9, color=TEXT)
    f_sub = Font(name=FONT, size=9, color=TEXT_2)
    f_op = Font(name=FONT, size=10, bold=True, color=TEXT)
    f_act = Font(name=FONT, size=10, bold=True, color=TEXT)
    f_total = Font(name=FONT, size=10, bold=True, color=TEXT)
    f_grand = Font(name=FONT, size=10, bold=True, color=TEXT)
    f_code = Font(name=FONT, size=8, color=MUTED)

    def code_of(s):
        return s.split(" ", 1)[0] if s else ""

    def name_of(s):
        parts = s.split(" ", 1)
        return parts[1] if len(parts) > 1 else s

    def put_row(r, code, label, font, bg, bd, values, fmt=FMT_MONEY,
                indent=1, outline=0, totals=True):
        """values — помесячные числа (или None), итоги по годам и периоду —
        формулами; totals=False оставляет колонки итогов пустыми."""
        write(ws, r, COL_CODE, code, font=f_code if font is not f_grand else font,
              fillc=bg, border=bd, align="left", indent=1)
        write(ws, r, COL_LABEL, label, font=font, fillc=bg, border=bd,
              align="left", indent=indent, wrap=False)
        for i, (kind, m, y) in enumerate(cols):
            if kind == "month":
                v = values[mindex[m]]
                bgc = bg
            elif not totals:
                v, bgc = None, (bg if bg else SURFACE_3)
            else:
                v = period_formula(cols, i, r, lambda _m: None)
                bgc = bg if bg else SURFACE_3
            write(ws, r, COL_FIRST + i, v, font=font, fmt=fmt,
                  fillc=bgc, border=bd, align="right")
        if outline:
            ws.row_dimensions[r].outlineLevel = outline
            ws.row_dimensions[r].hidden = True
        ws.row_dimensions[r].height = 17

    def fill_formula(row, make):
        """Проставляет формулу во все колонки строки: make(i) -> текст."""
        for i in range(len(cols)):
            c = ws.cell(row=row, column=COL_FIRST + i)
            c.value = make(i)
            c.number_format = FMT_MONEY

    def balance_formula(row, first_of_period):
        """
        Остаток — не сумма, а состояние на дату: в колонке года берём
        первый (или последний) месяц этого года, в колонке периода —
        первый (или последний) месяц всего отчёта.
        """
        def make(i):
            kind, m, y = cols[i]
            if kind == "month":
                return ws.cell(row=row, column=COL_FIRST + i).value
            if kind == "year":
                idx = [j for j, c in enumerate(cols)
                       if c[0] == "month" and c[2] == y]
            else:
                idx = [j for j, c in enumerate(cols) if c[0] == "month"]
            j = idx[0] if first_of_period else idx[-1]
            return "=%s%d" % (L(j), row)
        return make

    r = hdr + 1

    # ---- остаток на начало
    opening_vals = []
    run = opening
    for i in range(n_months):
        opening_vals.append(round(run, 2))
        run += sum(v for k, v in cf_data.items() if k[0] == months[i])
    put_row(r, "", "ОСТАТОК ДЕНЕЖНЫХ СРЕДСТВ НА НАЧАЛО", f_total,
            TOTAL_ROW, B_TOTAL, opening_vals, totals=False)
    fill_formula(r, balance_formula(r, first_of_period=True))
    row_open = r
    r += 2

    activity_total_rows = []

    for act in sorted(tree):
        ws.merge_cells(start_row=r, start_column=COL_CODE,
                       end_row=r, end_column=COL_LABEL)
        write(ws, r, COL_CODE, act.upper(), font=f_act, align="left", indent=1,
              border=B_SECTION)
        for cc in range(COL_CODE, ncols + 1):
            ws.cell(row=r, column=cc).border = B_SECTION
        ws.row_dimensions[r].height = 18
        r += 1

        op_total_rows = []
        for op in sorted(tree[act]):
            write(ws, r, COL_CODE, code_of(op), font=f_code,
                  border=B_BOTTOM_STRONG, align="left", indent=1)
            write(ws, r, COL_LABEL, name_of(op), font=f_op,
                  border=B_BOTTOM_STRONG, align="left", indent=1)
            for cc in range(COL_FIRST, ncols + 1):
                ws.cell(row=r, column=cc).border = B_BOTTOM_STRONG
            row_op = r
            r += 1

            def sum_of_rows(row, child_rows):
                """Итог = сумма ТОЛЬКО прямых дочерних строк. Складывать
                диапазон нельзя: внутри него лежат промежуточные итоги
                нижних уровней, и суммы задвоятся."""
                fill_formula(row, lambda i, rows=tuple(child_rows):
                             ("=" + "+".join("%s%d" % (L(i), rr) for rr in rows)
                              if rows else 0))

            item_total_rows = []
            for itm in sorted(tree[act][op]):
                row_item = r          # итог по статье — над подстатьями
                r += 1
                sub_rows = []

                for sub in sorted(tree[act][op][itm]):
                    row_sub = r
                    r += 1
                    cp_rows = []

                    for cp in sorted(tree[act][op][itm][sub]):
                        row_cp = r
                        r += 1
                        first_contract_row = r

                        contracts = tree[act][op][itm][sub][cp]
                        for contract in sorted(contracts):
                            put_row(r, "", contract, f_sub, None, B_BOTTOM,
                                    contracts[contract], indent=8, outline=4)
                            r += 1

                        # договоры — листья, тут диапазон складывать можно
                        put_row(row_cp, "", cp, f_sub, None, B_BOTTOM,
                                [None] * n_months, indent=6, outline=3)
                        fill_formula(row_cp,
                                    lambda i, a=first_contract_row, b=r - 1:
                                    "=SUM(%s%d:%s%d)" % (L(i), a, L(i), b))
                        ws.row_dimensions[row_cp].collapsed = True
                        cp_rows.append(row_cp)
                    put_row(row_sub, code_of(sub), name_of(sub), f_sub, None,
                            B_BOTTOM, [None] * n_months, indent=4, outline=2)
                    sum_of_rows(row_sub, cp_rows)
                    ws.row_dimensions[row_sub].collapsed = True
                    sub_rows.append(row_sub)

                put_row(row_item, code_of(itm), name_of(itm), f_item, None,
                        B_BOTTOM, [None] * n_months, indent=2, outline=1)
                ws.row_dimensions[row_item].hidden = False
                sum_of_rows(row_item, sub_rows)
                ws.row_dimensions[row_item].collapsed = True
                item_total_rows.append(row_item)

            # итог по операции
            fill_formula(row_op, lambda i, rows=tuple(item_total_rows):
                         ("=" + "+".join("%s%d" % (L(i), rr) for rr in rows)
                          if rows else 0))
            for i in range(len(cols)):
                c = ws.cell(row=row_op, column=COL_FIRST + i)
                c.font = f_op
                c.alignment = Alignment(horizontal="right", vertical="center")
            if item_total_rows:
                op_total_rows.append(row_op)

        # итог по виду деятельности
        put_row(r, "", "ИТОГО %s" % name_of(act).upper(), f_total,
                TOTAL_ROW, B_TOTAL, [None] * n_months, totals=False)
        fill_formula(r, lambda i, rows=tuple(op_total_rows):
                     ("=" + "+".join("%s%d" % (L(i), rr) for rr in rows)
                      if rows else 0))
        activity_total_rows.append(r)
        r += 2

    # ---- чистый денежный поток
    put_row(r, "", "ЧИСТЫЙ ДЕНЕЖНЫЙ ПОТОК ЗА ПЕРИОД", f_grand, TOTAL_ROW,
            B_TOTAL, [None] * n_months, totals=False)
    fill_formula(r, lambda i, rows=tuple(activity_total_rows):
                 ("=" + "+".join("%s%d" % (L(i), rr) for rr in rows)
                  if rows else 0))
    row_net = r
    ws.row_dimensions[r].height = 22
    r += 1

    # ---- остаток на конец
    put_row(r, "", "ОСТАТОК ДЕНЕЖНЫХ СРЕДСТВ НА КОНЕЦ", f_grand, TOTAL_ROW,
            B_GRAND, [None] * n_months, totals=False)
    for i, (kind, m, y) in enumerate(cols):
        if kind == "month":
            ws.cell(row=r, column=COL_FIRST + i).value = "=%s%d+%s%d" % (
                L(i), row_open, L(i), row_net)
    fill_formula(r, balance_formula(r, first_of_period=False))
    ws.row_dimensions[r].height = 22
    row_close = r
    r += 1

    # цвет цифр по знаку — кроме строк с белым текстом на тёмной заливке
    color_amounts_by_sign(
        ws,
        _row_ranges(hdr + 1, row_close, exclude=set()),
        COL_FIRST, ncols,
    )

    ws.column_dimensions["A"].width = 3
    ws.column_dimensions["B"].width = 10
    ws.column_dimensions["C"].width = 56
    ws.column_dimensions["D"].hidden = True
    apply_zebra(ws, hdr + 1, r - 1, COL_CODE, ncols)
    apply_column_dividers(ws, hdr, r - 1, COL_CODE, ncols)
    columns_layout(ws, cols, report_date.year)
    ws.freeze_panes = ws.cell(row=hdr + 1, column=COL_FIRST)
    ws.print_title_rows = "1:%d" % hdr
    ws.sheet_properties.outlinePr.summaryBelow = False


# =============================================================================
#  07. ЛИСТЫ ПОЯСНЕНИЙ (NOTES)
# =============================================================================

def build_notes(ws, title, subtitle, blocks):
    sheet_setup(ws, landscape=False)
    ncols = 3
    title_band(ws, title, subtitle, ncols)

    ws.column_dimensions["A"].width = 3
    ws.column_dimensions["B"].width = 108
    ws.column_dimensions["C"].width = 3

    f_h = Font(name=FONT, size=10, bold=True, color=TEXT)
    f_p = Font(name=FONT, size=10, color=TEXT_2)

    r = 7
    for num, (head, paras) in enumerate(blocks, 1):
        write(ws, r, 2, "%02d   %s" % (num, head), font=f_h,
              fillc=SURFACE_4, border=B_SECTION, align="left", indent=1)
        ws.row_dimensions[r].height = 24
        r += 1
        for p in paras:
            c = write(ws, r, 2, p, font=f_p, align="left", wrap=True, indent=1)
            c.alignment = Alignment(horizontal="left", vertical="top",
                                    wrap_text=True, indent=1)
            r += 1
        r += 1
    return r


def build_cover(ws, report_date, months, kpi, out_name, contents=None, as_of=None):
    as_of = as_of or report_date
    sheet_setup(ws, landscape=False)
    ncols = 6
    title_band(
        ws,
        "УПРАВЛЕНЧЕСКИЙ ПАКЕТ ОТЧЁТНОСТИ",
        "Управленческая отчётность (management pack)",
        ncols,
        extra="Российский рубль (RUB) · дата отчёта: %s · период: %s — %s"
              % (as_of.strftime("%d.%m.%Y"),
                 month_label(months[0]), month_label(months[-1])),
        show_back=False,
    )

    for i, w in enumerate([3, 30, 24, 22, 22, 3], start=1):
        ws.column_dimensions[get_column_letter(i)].width = w

    f_lbl = Font(name=FONT, size=8, bold=True, color=MUTED)
    f_val = Font(name=FONT, size=16, bold=True, color=NAVY_3)
    f_val_w = f_val
    f_sub = Font(name=FONT, size=9, color=TEXT_2)

    # ---- KPI-карточки
    r = 7
    cards = [
        ("ВЫРУЧКА БЕЗ НДС до СПП", kpi.get("revenue"), FMT_MONEY, True),
        ("EBITDA", kpi.get("ebitda"), FMT_MONEY, False),
        ("ЧИСТАЯ ПРИБЫЛЬ", kpi.get("net"), FMT_MONEY, False),
        ("ОСТАТОК ДС НА КОНЕЦ", kpi.get("cash"), FMT_MONEY, False),
    ]
    for i, (lbl, v, fmt, primary) in enumerate(cards):
        col = 2 + i
        bg = SURFACE_4 if primary else SURFACE
        write(ws, r, col, lbl, font=Font(name=FONT, size=8, bold=True,
                                         color=NAVY_3 if primary else MUTED),
              fillc=bg, border=Border(top=_side(NAVY), left=_side(LINE),
                                      right=_side(LINE)), align="left", indent=1)
        write(ws, r + 1, col, v, font=f_val, fmt=fmt,
              fillc=bg, border=Border(left=_side(LINE), right=_side(LINE)),
              align="left", indent=1)
        write(ws, r + 2, col, month_label(months[-1]),
              font=Font(name=FONT, size=8,
                        color=MUTED),
              fillc=bg, border=Border(bottom=_side(LINE), left=_side(LINE),
                                      right=_side(LINE)), align="left", indent=1)
    ws.row_dimensions[r].height = 16
    ws.row_dimensions[r + 1].height = 26
    ws.row_dimensions[r + 2].height = 16

    # ---- содержание
    r += 5
    write(ws, r, 2, "СОДЕРЖАНИЕ ОТЧЕТА", font=Font(name=FONT, size=11, bold=True,
                                                   color=TEXT),
          border=B_SECTION, align="left", indent=1)
    ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=5)
    ws.row_dimensions[r].height = 24
    r += 1

    write(ws, r, 2, "Щёлкните на названии листа, чтобы перейти. "
                    "На каждом листе есть кнопка возврата в оглавление.",
          font=Font(name=FONT, size=8, italic=True, color=MUTED),
          align="left", indent=1)
    ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=5)
    ws.row_dimensions[r].height = 14
    r += 1

    if contents is None:
        contents = [
            ("P&L", "Отчёт о прибылях и убытках с промежуточными итогами, "
                    "EBITDA, налогом и рентабельностью"),
            ("Cash Flow", "Отчёт о движении денежных средств прямым методом "
                          "по видам деятельности"),
            ("Пояснения P&L", "Методика расчёта каждого раздела и промежуточного итога"),
            ("Пояснения Cash Flow", "Структура потоков, остатки и связь с P&L"),
        ]

    f_link = Font(name=FONT, size=10, bold=True, color=NAVY_3)

    first_contents_row = r
    for name, descr in contents:
        c = write(ws, r, 2, "\u203a  " + name, font=f_link,
                fillc=SURFACE_4, border=B_BOTTOM, align="left", indent=1)
        c.hyperlink = "#'%s'!A1" % name
        c = write(ws, r, 3, descr, font=f_sub, border=B_BOTTOM,
                align="left", wrap=True)
        ws.merge_cells(start_row=r, start_column=3, end_row=r, end_column=5)
        ws.row_dimensions[r].height = 28
        r += 1

    last_contents_row = r - 1
    apply_zebra(ws, first_contents_row, last_contents_row, 2, 5)
    apply_column_dividers(ws, first_contents_row, last_contents_row, 2, 5)

    r += 1
    write(ws, r, 2, "Файл сформирован автоматически · %s"
          % dt.datetime.now().strftime("%d.%m.%Y %H:%M"),
          font=Font(name=FONT, size=8, color=MUTED), align="left", indent=1)
    ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=5)


# =============================================================================
#  07A. ЛИСТ «ЮНИТ-ЭКОНОМИКА» (управленческий учёт, FIFO)
#
#      Состав показателей согласован с финансовой службой: количества
#      продаж/возвратов, выручка до и после СПП, цены и себестоимость на
#      единицу, три уровня маржинальности и рентабельность по чистой
#      прибыли. Всё считается по управленческому контуру (FIFO по дате
#      исходной продажи), а не по кассе — см. лист пояснений.
# =============================================================================

# Метрики строк с данными: ключ в словаре unit_data[me] -> значение.
U_NET_QTY = "net_qty"
U_SALES_QTY = "sales_qty"
U_RETURNS_QTY = "returns_qty"
U_AMOUNT = "amount"
U_RETAIL = "retail_amount"
U_VATLESS = "amount_vatless"
U_COGS = "cogs_man"
U_COMISSION = "net_comission"
U_WB_COSTS = "wb_costs_vatless"
U_PROMO = "promo_vatless"
U_NET_PROFIT = "net_profit"


def unit_layout():
    """
    Строки листа юнит-экономики.
      kind: band | data | calc | ratio | blank
      spec: для data — (ключ метрики, знак); для calc — [(код, знак), ...];
            для ratio — (числитель, знаменатель, множитель)
      role: income | expense | total | grand | ratio_good | ratio_cost

    Отдельной строки возвратов здесь нет: в управленческом контуре возврат
    сторнируется на дату исходной продажи, то есть уже уменьшил и количество,
    и выручку того месяца, в котором товар был продан.
    """
    L = []
    add = L.append

    add(("band", "1", "ОБЪЁМЫ И ВЫРУЧКА", None, None, None))
    add(("data", "1.1", "Кол-во продаж, шт",
         (U_NET_QTY, 1), "income", FMT_QTY))
    add(("data", "1.2", "Продажи до СПП с НДС (валовый оборот)",
         (U_AMOUNT, 1), "income", FMT_MONEY))
    add(("data", "1.3", "Продажи после СПП с НДС (оплачено покупателем)",
         (U_RETAIL, 1), "income", FMT_MONEY))
    add(("ratio", "1.4", "Скидка WB (СПП), % к продажам до СПП",
         ("__spp__", "1.2", 100), "ratio_cost", FMT_PCT))
    add(("data", "1.5", "Продажи до СПП без НДС (база маржинальности)",
         (U_VATLESS, 1), "total", FMT_MONEY))
    add(("blank", None, None, None, None, None))

    add(("band", "2", "ПОКАЗАТЕЛИ НА ЕДИНИЦУ", None, None, None))
    add(("ratio", "2.1", "Средняя цена на ед. продаж до СПП с НДС, ₽",
         ("1.2", "1.1", 1), "income", FMT_PRICE))
    add(("ratio", "2.2", "Средняя цена на ед. после СПП с НДС "
                         "(цена покупателя), ₽",
         ("1.3", "1.1", 1), "income", FMT_PRICE))
    add(("ratio", "2.3", "Средняя с/с на ед. продаж без НДС, ₽",
         ("3.1", "1.1", -1), "expense", FMT_PRICE))
    add(("ratio", "2.4", "Средняя валовая прибыль на ед. продаж, ₽",
         ("4.1", "1.1", 1), "total", FMT_PRICE))
    add(("blank", None, None, None, None, None))

    add(("band", "3", "СЕБЕСТОИМОСТЬ И УДЕРЖАНИЯ ПЛОЩАДКИ (без НДС)",
         None, None, None))
    add(("data", "3.1", "Себестоимость проданного товара (FIFO)",
         (U_COGS, -1), "expense", FMT_MONEY))
    add(("data", "3.2", "Комиссия WB с продаж",
         (U_COMISSION, 1), "expense", FMT_MONEY))
    add(("data", "3.3", "Расходы ВБ без продвижения "
                        "(логистика, хранение, приёмка)",
         (U_WB_COSTS, 1), "expense", FMT_MONEY))
    add(("data", "3.4", "Продвижение WB (реклама, буст, отзывы)",
         (U_PROMO, 1), "expense", FMT_MONEY))
    add(("blank", None, None, None, None, None))

    add(("band", "4", "МАРЖИНАЛЬНОСТЬ", None, None, None))
    add(("calc", "4.1", "ВАЛОВАЯ ПРИБЫЛЬ",
         [("1.5", 1), ("3.1", 1)], "total", FMT_MONEY))
    add(("ratio", "4.2", "Маржинальность по валовой прибыли, %",
         ("4.1", "1.5", 100), "ratio_good", FMT_PCT))
    add(("calc", "4.3", "МАРЖИНАЛЬНАЯ ПРИБЫЛЬ (без продвижения)",
         [("4.1", 1), ("3.2", 1), ("3.3", 1)], "total", FMT_MONEY))
    add(("ratio", "4.4", "Маржинальность по марж. прибыли (без продвижения), %",
         ("4.3", "1.5", 100), "ratio_good", FMT_PCT))
    add(("calc", "4.5", "МАРЖИНАЛЬНАЯ ПРИБЫЛЬ (с продвижением)",
         [("4.3", 1), ("3.4", 1)], "total", FMT_MONEY))
    add(("ratio", "4.6", "Маржинальность по марж. прибыли (с продвижением), %",
         ("4.5", "1.5", 100), "ratio_good", FMT_PCT))
    add(("blank", None, None, None, None, None))

    add(("data", "4.7", "ЧИСТАЯ ПРИБЫЛЬ (из P&L, после налога)",
         (U_NET_PROFIT, 1), "grand", FMT_MONEY))
    add(("ratio", "4.8", "Рентабельность по чистой прибыли, %",
         ("4.7", "1.5", 100), "grand", FMT_PCT))
    return L


def build_unit_economics(ws, unit_data, months, report_date, as_of=None):
    as_of = as_of or report_date
    """
    unit_data — {me: {ключ метрики: значение}}
    Все производные строки (количество чистых продаж, цены на единицу,
    валовая и маржинальная прибыль, проценты) записаны формулами Excel со
    ссылками на другие строки того же столбца: любую цифру можно проверить,
    кликнув на ячейку, и колонки «Итого» пересчитываются автоматически.
    """
    cols = make_columns(months)
    ncols = COL_FIRST + len(cols) - 1

    sheet_setup(ws)
    title_band(
        ws,
        "ЮНИТ-ЭКОНОМИКА ПРОДАЖ",
        "Управленческий учёт · FIFO по дате исходной продажи",
        ncols,
        extra="Российский рубль (RUB) · дата отчёта: %s · период: %s — %s · "
            
              % (as_of.strftime("%d.%m.%Y"),
                 month_label(months[0]), month_label(months[-1])),
    )
    hdr_year, hdr = 6, 7
    columns_header(ws, cols, hdr_year, hdr, report_date.year)

    plan = unit_layout()

    # номера строк по кодам
    rowmap, r = {}, hdr + 1
    for kind, code, label, spec, role, fmt in plan:
        if code and kind != "band":
            rowmap.setdefault(code, r)
        r += 1

    f_band = Font(name=FONT, size=10, bold=True, color=TEXT)
    f_code = Font(name=FONT, size=8, color=MUTED)
    f_label = Font(name=FONT, size=10, color=TEXT)
    f_label_total = Font(name=FONT, size=10, bold=True, color=TEXT)
    f_label_ratio = Font(name=FONT, size=9, color=TEXT_2)
    f_grand = Font(name=FONT, size=10, bold=True, color=TEXT)

    NUM_FONTS = {
        "income": Font(name=FONT, size=10, color=INCOME),
        "expense": Font(name=FONT, size=10, color=EXPENSE),
        "total": Font(name=FONT, size=10, bold=True, color=TEXT),
        "grand": f_grand,
        "ratio_good": Font(name=FONT, size=9, color=TEXT_2),
        "ratio_cost": Font(name=FONT, size=9, color=TEXT_2),
    }

    r = hdr + 1
    for kind, code, label, spec, role, fmt in plan:
        stripe = (r % 2 == 0)

        if kind == "blank":
            ws.row_dimensions[r].height = 6
            r += 1
            continue

        if kind == "band":
            ws.merge_cells(start_row=r, start_column=COL_CODE,
                           end_row=r, end_column=COL_LABEL)
            write(ws, r, COL_CODE, "%s. %s" % (code, label), font=f_band,
                  align="left", indent=1, border=B_SECTION)
            for cc in range(COL_CODE, ncols + 1):
                ws.cell(row=r, column=cc).border = B_SECTION
            ws.row_dimensions[r].height = 18
            r += 1
            continue

        is_grand = role == "grand"
        is_total = role == "total"
        is_ratio = kind == "ratio" and role in ("ratio_good", "ratio_cost")

        if is_grand:
            bg, bd, fnt_label = TOTAL_ROW, B_GRAND, f_grand
        elif is_total:
            bg, bd, fnt_label = TOTAL_ROW, B_TOTAL, f_label_total
        else:
            bg = None
            bd = B_BOTTOM
            fnt_label = f_label_ratio if is_ratio else f_label

        fnt_num = NUM_FONTS[role]

        write(ws, r, COL_CODE, code, font=f_grand if is_grand else f_code,
              fillc=bg, border=bd, align="left", indent=1)
        write(ws, r, COL_LABEL, label, font=fnt_label, fillc=bg, border=bd,
              align="left", indent=1 if (is_total or is_grand) else 2)

        for i in range(len(cols)):
            cl = L(i)
            v = None

            if kind == "data":
                key, sign = spec
                v = period_formula(
                    ws and cols, i, r,
                    lambda m, k=key, sg=sign: (
                        None if unit_data.get(m, {}).get(k) is None
                        else unit_data[m][k] * sg))

            elif kind == "calc":
                parts = []
                for key, sgn in spec:
                    rr = rowmap.get(key)
                    if rr is None:
                        continue
                    parts.append("%s%s%d" % ("+" if sgn > 0 else "-", cl, rr))
                v = "=" + "".join(parts).lstrip("+")

            elif kind == "ratio":
                num, den, mult = spec
                rd = rowmap[den]
                if num == "__spp__":
                    # скидка СПП = (продажи до СПП − продажи после СПП) / до СПП
                    r1, r2 = rowmap["1.2"], rowmap["1.3"]
                    v = ("=IF(%s%d=0,\"\",(%s%d-%s%d)/%s%d*%s)"
                         % (cl, rd, cl, r1, cl, r2, cl, rd, mult))
                else:
                    rn = rowmap[num]
                    sign = "-" if mult < 0 else ""
                    k = abs(mult)
                    tail = "" if k == 1 else "*%s" % k
                    v = ("=IF(%s%d=0,\"\",%s%s%d/%s%d%s)"
                         % (cl, rd, sign, cl, rn, cl, rd, tail))

            fillv = bg
            if cols[i][0] != "month" and not (is_total or is_grand):
                fillv = SURFACE_3
            write(ws, r, COL_FIRST + i, v, font=fnt_num, fmt=fmt,
                  fillc=fillv, border=bd, align="right")

        ws.row_dimensions[r].height = 19 if (is_total or is_grand) else 17
        r += 1

    ws.column_dimensions["A"].width = 3
    ws.column_dimensions["B"].width = 9
    ws.column_dimensions["C"].width = 66
    ws.column_dimensions["D"].hidden = True
    apply_zebra(ws, hdr + 1, r - 1, COL_CODE, ncols)
    apply_column_dividers(ws, hdr, r - 1, COL_CODE, ncols)
    columns_layout(ws, cols, report_date.year)
    ws.freeze_panes = ws.cell(row=hdr + 1, column=COL_FIRST)
    ws.print_title_rows = "1:%d" % hdr
    return r


NOTES_UNIT = [
    ("Что показывает лист", [
        "Юнит-экономика продаж: сколько единиц продано, по какой цене, с какой "
        "себестоимостью и что остаётся от каждой продажи после удержаний "
        "маркетплейса и вложений в продвижение.",
    ]),
    ("Метод учёта: FIFO, а не касса", [
        "Показатели строятся по управленческому контуру: выручка и "
        "себестоимость признаются на дату исходной продажи товара, "
        "себестоимость списывается по FIFO — по партиям в порядке "
        "поступления, привязанным к конкретной продаже.",
        "Возврат отдельной строкой в отчёте не показывается: он сторнирует "
        "исходную продажу — уменьшает и количество, и выручку того месяца, в "
        "котором товар был продан. Поэтому «Кол-во продаж» здесь — это уже "
        "чистое количество, за вычетом того, что вернули.",
        "Из этого следует практический вывод: цифры последних месяцев "
        "уточняются по мере поступления возвратов. Окончательными их можно "
        "считать после того, как пройдёт основная волна возвратов (обычно "
        "две-три недели).",
        "Кассовый метод — деньги на счёте и отчёты маркетплейса о "
        "перечислениях — даёт другие числа за тот же месяц. Это не "
        "расхождение и не ошибка, а разные базы признания. Денежная картина "
        "показана на листе Cash Flow.",
    ]),
    ("Почему количество не сходится с отчётом WB", [
        "Здесь количество привязано к дате исходной продажи, а в отчёте "
        "маркетплейса и продажа, и возврат попадают в тот период, когда они "
        "фактически прошли через баланс площадки.",
        "Дополнительно в выручку периода не попадают единицы, которые не "
        "удалось сопоставить с себестоимостью, — их количество показано на "
        "листе P&L, строка 2.3 «Без себестоимости, шт.».",
        "Поэтому поштучно сверять этот лист с отчётом WB за конкретный месяц "
        "не следует: сходиться они будут на длинном горизонте.",
    ]),
    ("Раздел 1. Объёмы и выручка", [
        "1.1 Кол-во продаж — чистое количество проданных единиц за месяц по "
        "дате продажи, за вычетом сторнированных возвратов. Именно оно "
        "используется во всех показателях на единицу.",
        "1.2 Продажи до СПП с НДС — валовый оборот по ценам продавца, до "
        "скидки постоянного покупателя, которую финансирует маркетплейс.",
        "1.3 Продажи после СПП с НДС — сумма, фактически уплаченная "
        "покупателем после применения СПП.",
        "1.4 Скидка WB (СПП) = (1.2 − 1.3) / 1.2 — глубина субсидии площадки.",
        "1.5 Продажи до СПП без НДС — та же выручка 1.2, из которой по каждой "
        "продаже вычтен НДС по её фактической ставке (10 % или 22 %, известна "
        "построчно). Это база для всех процентов маржинальности ниже.",
    ]),
    ("Раздел 2. Показатели на единицу", [
        "Все средние считаются на количество продаж из строки 1.1.",
        "2.3 Средняя с/с на ед. — управленческая себестоимость FIFO без НДС, "
        "делённая на количество продаж.",
        "2.4 Средняя валовая прибыль на ед. = валовая прибыль (4.1) / "
        "количество продаж: сколько зарабатываем на одной проданной единице "
        "до удержаний площадки.",
    ]),
    ("Раздел 3. Себестоимость и удержания площадки", [
        "3.1 Себестоимость — управленческая FIFO-себестоимость проданного "
        "товара, а не бухгалтерская.",
        "3.2 Комиссия WB — комиссия площадки с продаж и выкупов.",
        "3.3 Расходы ВБ без продвижения — логистика, хранение, приёмка, "
        "штрафы и программа лояльности.",
        "3.4 Продвижение WB — платная реклама и буст внутри площадки, работа "
        "с отзывами, прочие маркетинговые удержания.",
    
    ]),
    ("Раздел 4. Маржинальность", [
        "4.1 Валовая прибыль = Продажи до СПП без НДС (1.5) − себестоимость "
        "(3.1).",
        "4.2 Маржинальность по валовой прибыли = 4.1 / 1.5 — то же самое, что "
        "1 − себестоимость / продажи до СПП без НДС.",
        "4.3 Маржинальная прибыль без продвижения = валовая прибыль минус "
        "комиссия WB (3.2) и расходы ВБ (3.3): что остаётся от торговой "
        "операции до любых вложений в трафик.",
        "4.4 Маржинальность по маржинальной прибыли (без продвижения) = "
        "4.3 / 1.5.",
        "4.5 Маржинальная прибыль с продвижением = 4.3 минус продвижение "
        "(3.4). Ключевой показатель эффективности работы с площадкой.",
        "4.6 Маржинальность по маржинальной прибыли (с продвижением) = "
        "4.5 / 1.5.",
        "4.7 Чистая прибыль берётся из P&L — после накладных и корпоративных "
        "расходов, прочих доходов и расходов, финансовых расходов и налога на "
        "прибыль. Поэтому она меньше маржинальной прибыли: в ней учтено всё, "
        "что не привязано к конкретной продаже.",
        "4.8 Рентабельность по чистой прибыли = 4.7 / 1.5 — считается к той же "
        "базе, что и остальные проценты, чтобы показатели были сопоставимы "
        "между собой и между месяцами.",
    ]),
    ("Как читать колонки", [
        "Колонка месяца — значение за календарный месяц. Завершённые годы "
        "свёрнуты, видны их итоговые колонки; текущий год раскрыт помесячно.",
        "В колонках «Итого <год>» и «Итого за период» суммы складываются, а "
        "проценты и показатели на единицу пересчитываются по формуле от "
        "годовых сумм.",
    ]),
]


# =============================================================================
#  07B. ЛИСТ «ОСТАТКИ ДЕНЕЖНЫХ СРЕДСТВ»
#
#      Сводка: банковские счета, деньги в пути, баланс маркетплейса,
#      бессрочные депозиты и общий итог. Ниже — расшифровка по каждому
#      счёту и состав баланса WB.
#      Источник — витрина treasury (см. sql/treasury.txt), собирается тем
#      же способом, что и остальные витрины пакета.
# =============================================================================

def split_treasury(rows):
    """Делит строки витрины treasury на банковские счета и баланс WB."""
    banks = [r for r in rows if r and r[0] == "BANK"]
    wb_row = next((r for r in rows if r and r[0] == "WB"), None)
    return banks, wb_row


def _f(value):
    """Денежное значение для управленческого отчёта: округляем до целых рублей."""
    try:
        v = Decimal(str(value or 0))
    except Exception:
        return 0.0

    if abs(v) < Decimal("0.5"):
        return 0.0

    return float(v.quantize(Decimal("1"), rounding=ROUND_HALF_UP))



def build_treasury(ws, bank_rows, wb_row, report_date, as_of=None, deposit_balance=0.0):
    as_of = as_of or report_date
    """
    bank_rows — строки витрины treasury с block='BANK'
    wb_row    — строка витрины treasury с block='WB' (или None)
    Поля строки: block, name, currency, status, inflow, outflow, balance,
                 transit, balance_no_transit, as_of
    """
    sheet_setup(ws, landscape=False)
    ncols = 8
    
    def status_rank(row):
        status = str(row[3] or "").lower()
        return 0 if "действ" in status else 1

    bank_rows = sorted(
        bank_rows,
        key=lambda row: (status_rank(row), -abs(_f(row[6])), str(row[1] or "")),
    )

    title_band(
        ws,
        "ОСТАТКИ ДЕНЕЖНЫХ СРЕДСТВ",
        "Управленческая отчётность (management pack)",
        ncols,
        extra="Российский рубль (RUB) · состояние на %s"
              % as_of.strftime("%d.%m.%Y"),
    )

    for i, w in enumerate([3, 44, 16, 30, 16, 16, 16, 4], start=1):
        ws.column_dimensions[get_column_letter(i)].width = w

    f_section = Font(name=FONT, size=10, bold=True, color=TEXT)
    f_hdr = Font(name=FONT, size=9, bold=True, color="FFFFFF")
    f_label = Font(name=FONT, size=10, color=TEXT)
    f_label_b = Font(name=FONT, size=10, bold=True, color=TEXT)
    f_income = Font(name=FONT, size=10, color=INCOME)
    f_expense = Font(name=FONT, size=10, color=EXPENSE)
    f_bold_num = Font(name=FONT, size=10, bold=True, color=TEXT)
    f_note = Font(name=FONT, size=8, color=MUTED)

    def section(r, text):
        write(ws, r, 2, text, font=f_section, align="left", border=B_SECTION)
        for cc in range(3, ncols + 1):
            ws.cell(row=r, column=cc).border = B_SECTION
        ws.row_dimensions[r].height = 18
        return r + 1

    # ------------------------------------------------------------- сводка
    bank_total = sum(_f(r[6]) for r in bank_rows)
    transit = _f(wb_row[7]) if wb_row else 0.0
    wb_balance = _f(wb_row[6]) if wb_row else 0.0

    r = 7
    r = section(r, "СВОДКА ПО ОСТАТКАМ")

    summary = [
        ("Банковские счета", bank_total,
         "Сумма остатков по всем счетам из расшифровки ниже"),
        ("Баланс WB", wb_balance,
         "На балансе площадки, ещё не выведено"),
        ("Деньги в пути (ДВП)", transit,
         "Выведены с WB, но ещё не пришли на расчётный счёт"),
        # ("Банковские депозиты", _f(deposit_balance),
        #     "Справочно: размещены под проценты, в итог денежных средств не включаются"),
    ]
    

    
    first_sum_row = r
    for lbl, v, hint in summary:
        write(ws, r, 2, lbl, font=f_label, border=B_BOTTOM,
              align="left", indent=1)
        write(ws, r, 3, v, font=f_income, fmt=FMT_MONEY, border=B_BOTTOM,
              align="right")
        write(ws, r, 4, hint, font=f_note, border=B_BOTTOM,
              align="left", indent=1)
        ws.merge_cells(start_row=r, start_column=4, end_row=r, end_column=ncols)
        for cc in range(5, ncols + 1):
            ws.cell(row=r, column=cc).border = B_BOTTOM
        ws.row_dimensions[r].height = 17
        r += 1

    write(ws, r, 2, "ИТОГО ДЕНЕЖНЫХ СРЕДСТВ", font=f_label_b, fillc=TOTAL_ROW,
          border=B_GRAND, align="left", indent=1)
    write(ws, r, 3, "=SUM(C%d:C%d)" % (first_sum_row, first_sum_row + 2),
      font=f_bold_num, fmt=FMT_MONEY, fillc=TOTAL_ROW, border=B_GRAND,
      align="right")
    for cc in range(4, ncols + 1):
        ws.cell(row=r, column=cc).fill = fill(TOTAL_ROW)
        ws.cell(row=r, column=cc).border = B_GRAND
    ws.merge_cells(start_row=r, start_column=4, end_row=r, end_column=ncols)
    ws.row_dimensions[r].height = 20
    r += 2
    
    
    r = section(r, "СПРАВОЧНО")

    write(ws, r, 2, "Банковские депозиты", font=f_label, border=B_BOTTOM,
        align="left", indent=1)
    write(ws, r, 3, _f(deposit_balance), font=f_income, fmt=FMT_MONEY,
        border=B_BOTTOM, align="right")
    write(ws, r, 4, "Размещены под проценты; не включаются в итог денежных средств",
        font=f_note, border=B_BOTTOM, align="left", indent=1)
    ws.merge_cells(start_row=r, start_column=4, end_row=r, end_column=ncols)
    for cc in range(5, ncols + 1):
        ws.cell(row=r, column=cc).border = B_BOTTOM
    ws.row_dimensions[r].height = 17

    r += 2

    # -------------------------------------------- расшифровка по счетам
    r = section(r, "РАСШИФРОВКА ПО БАНКОВСКИМ СЧЕТАМ")

    headers = [(2, "Банковский счёт"), (3, "Валюта"), (4, "Статус"),
               (5, "Поступления"), (6, "Расход"), (7, "Остаток")]
    for col, h in headers:
        align = "left" if col == 2 else ("center" if col in (3, 4) else "right")
        write(ws, r, col, h, font=f_hdr, fillc=NAVY, align=align,
              indent=1 if col == 2 else 0, wrap=True)
    ws.cell(row=r, column=ncols).fill = fill(NAVY)
    ws.row_dimensions[r].height = 20
    r += 1

    first_bank_row = r
    if bank_rows:
        for row in bank_rows:
            write(ws, r, 2, row[1], font=f_label, border=B_BOTTOM,
                  align="left", indent=1)
            write(ws, r, 3, row[2] or "", font=f_label, border=B_BOTTOM,
                  align="center")
            status = row[3] or ""
            if "закрыт" in str(status).lower():
                status = "Закрыт  🔒"

            write(ws, r, 4, status, font=f_label, border=B_BOTTOM,
                align="center")
            write(ws, r, 5, _f(row[4]), font=f_income, fmt=FMT_MONEY,
                  border=B_BOTTOM, align="right")
            write(ws, r, 6, _f(row[5]), font=f_expense, fmt=FMT_MONEY,
                  border=B_BOTTOM, align="right")
            write(ws, r, 7, _f(row[6]), font=f_bold_num, fmt=FMT_MONEY,
                  border=B_BOTTOM, align="right")
            ws.cell(row=r, column=ncols).border = B_BOTTOM
            ws.row_dimensions[r].height = 17
            r += 1
    else:
        write(ws, r, 2, "Нет данных по банковским счетам на отчётную дату",
              font=f_note, border=B_BOTTOM, align="left", indent=1)
        r += 1

    last_bank_row = r - 1
    write(ws, r, 2, "ИТОГО ПО СЧЕТАМ", font=f_label_b, fillc=TOTAL_ROW,
          border=B_TOTAL, align="left", indent=1)
    for cc in (3, 4, ncols):
        ws.cell(row=r, column=cc).fill = fill(TOTAL_ROW)
        ws.cell(row=r, column=cc).border = B_TOTAL
    for col, colour in ((5, INCOME), (6, EXPENSE), (7, TEXT)):
        formula = ("=SUM(%s%d:%s%d)" % (get_column_letter(col), first_bank_row,
                                        get_column_letter(col), last_bank_row)
                   if bank_rows else 0)
        write(ws, r, col, formula,
              font=Font(name=FONT, size=10, bold=True, color=colour),
              fmt=FMT_MONEY, fillc=TOTAL_ROW, border=B_TOTAL, align="right")
    ws.row_dimensions[r].height = 19
    bank_total_row = r
    r += 2

    # сводка ссылается на итог расшифровки — цифры не разъезжаются
    ws.cell(row=first_sum_row, column=3).value = "=G%d" % bank_total_row

    # ----------------------------------------------------- баланс WB
    wb_as_of = wb_row[9] if wb_row else None
    head = "БАЛАНС МАРКЕТПЛЕЙСА WB"
    if wb_as_of and hasattr(wb_as_of, "strftime") and wb_as_of != as_of:
        head += " · выгрузка площадки на %s" % wb_as_of.strftime("%d.%m.%Y")
    r = section(r, head)

    f_link = Font(name=FONT, size=9, bold=True, color=NAVY_3)

    # последний элемент — подпись-ссылка на лист с расшифровкой выводов
    wb_lines = [
        ("К перечислению продавцу, всего",
         _f(wb_row[4]) if wb_row else 0.0, f_income, False, None),
        ("Выведено средств, всего",
         _f(wb_row[5]) if wb_row else 0.0, f_expense, False,
         "\u2192  поступления от площадки на расчётный счёт по датам"),
        ("Конечный баланс без денег в пути",
         _f(wb_row[8]) if wb_row else 0.0, f_label, False, None),
        ("Деньги в пути (ДВП)", transit, f_label, False, None),
        ("Конечный баланс WB", wb_balance, f_bold_num, True, None),
    ]
    for lbl, v, fnt, is_last, link in wb_lines:
        write(ws, r, 2, lbl, font=f_label_b if is_last else f_label,
              fillc=TOTAL_ROW if is_last else None,
              border=B_TOTAL if is_last else B_BOTTOM, align="left", indent=1)
        write(ws, r, 3, v, font=fnt, fmt=FMT_MONEY,
              fillc=TOTAL_ROW if is_last else None,
              border=B_TOTAL if is_last else B_BOTTOM, align="right")
        for cc in range(4, ncols + 1):
            cell = ws.cell(row=r, column=cc)
            if is_last:
                cell.fill = fill(TOTAL_ROW)
            cell.border = B_TOTAL if is_last else B_BOTTOM
        if link:
            c = write(ws, r, 4, link, font=f_link, border=B_BOTTOM,
                      align="left", indent=1)
            c.hyperlink = "#'%s'!A1" % PAYOUTS_SHEET_NAME
        ws.merge_cells(start_row=r, start_column=4, end_row=r, end_column=ncols)
        ws.row_dimensions[r].height = 17
        r += 1

    r += 1
    note = ("Первые две строки — накопительные итоги за всё время работы с "
            "площадкой, их разница и даёт конечный баланс. ")
    write(ws, r, 2, note, font=f_note, align="left", wrap=True, indent=1)
    ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=ncols)
    ws.row_dimensions[r].height = 44
    apply_zebra(ws, 8, r - 1, 2, ncols)
    ws.freeze_panes = ws.cell(row=7, column=1)
    return r


# =============================================================================
#  07C. ЛИСТ «ПОСТУПЛЕНИЯ ОТ WB»
#
#      Зачисления от площадки на расчётный счёт: дата, сумма, плательщик.
#      На листе только факты учёта, ничего не достраивается и не
#      сопоставляется с выводами площадки.
#
#      Данные — витрина wb_payouts (sql/wb_payouts.txt): поступления из
#      движения денежных средств по статье выручки от маркетплейса,
#      плюс итог списаний с баланса WB для строки сводки «Разница».
# =============================================================================

PAYOUTS_SHEET_NAME = "Поступления от WB"

FMT_DATE = "DD.MM.YYYY"


def split_payouts(payout_rows):
    """Делит витрину wb_payouts на списания с баланса WB и поступления."""
    outs, ins = [], []
    for side, dt, amount, cp_name in payout_rows:
        dt = dt if isinstance(dt, date) else date.fromisoformat(str(dt))
        value = round(abs(float(amount or 0)), 2)
        if not value:
            continue
        row = {"dt": dt, "amount": value, "cp_name": (cp_name or "").strip()}
        (outs if side == "OUT" else ins).append(row)
    outs.sort(key=lambda x: x["dt"])
    ins.sort(key=lambda x: x["dt"])
    return outs, ins


PAYOUT_MATCH_DAYS = 15      # окно поиска поступления после вывода
PAYOUT_MATCH_EPS = 1.0      # допуск по сумме, рублей


def match_wb_payouts(outs, ins):
    """Сопоставляет вывод с баланса WB и поступление на расчётный счёт.

    Проход первый — по совпадению суммы: поступление ищется в окне
    PAYOUT_MATCH_DAYS дней после вывода, берётся самое раннее подходящее.
    Проход второй — остаток по порядку: деньги приходят в той же
    последовательности, в которой выводились.

    Нужно только для того, чтобы у каждой суммы вывода была дата, которой
    деньги реально пришли на расчётный счёт. Пара без поступления
    (kind = transit) на лист не попадает: это деньги в пути.
    """
    used = [False] * len(ins)
    pairs = []

    def take(i, out, kind):
        used[i] = True
        inc = ins[i]
        pairs.append({
            "out_dt": out["dt"], "out_amount": out["amount"],
            "in_dt": inc["dt"], "in_amount": inc["amount"],
            "cp_name": inc["cp_name"],
            "days": (inc["dt"] - out["dt"]).days,
            "kind": kind,
        })

    rest = []
    for out in outs:
        hit = None
        for i, inc in enumerate(ins):
            if inc["dt"] < out["dt"]:
                continue
            if (inc["dt"] - out["dt"]).days > PAYOUT_MATCH_DAYS:
                break
            if used[i]:
                continue
            if abs(inc["amount"] - out["amount"]) <= PAYOUT_MATCH_EPS:
                hit = i
                break
        if hit is None:
            rest.append(out)
        else:
            take(hit, out, "exact")

    for out in rest:
        hit = None
        for i, inc in enumerate(ins):
            if not used[i] and inc["dt"] >= out["dt"]:
                hit = i
                break
        if hit is None:
            pairs.append({
                "out_dt": out["dt"], "out_amount": out["amount"],
                "in_dt": None, "in_amount": 0.0, "cp_name": "",
                "days": None, "kind": "transit",
            })
        else:
            take(hit, out, "order")

    pairs.sort(key=lambda p: (p["out_dt"], p["in_dt"] or date.max))
    return pairs


def build_wb_payouts(ws, receipts, withdrawn_total, report_date, as_of=None):
    """Лист «Поступления от WB»: зачисления от площадки на расчётный счёт.

    receipts — строки поступлений (дата, сумма, контрагент) из витрины
    движения денежных средств. Ничего не сопоставляется и не достраивается:
    на листе только то, что реально прошло по расчётному счёту.
    """
    as_of = as_of or report_date

    sheet_setup(ws, landscape=False)
    ncols = 6

    title_band(
        ws,
        "ПОСТУПЛЕНИЯ ОТ МАРКЕТПЛЕЙСА",
        "Поступления от площадки на расчётный счёт: даты и суммы",
        ncols,
        extra="Российский рубль (RUB) · нарастающим итогом за всё время "
              "работы с площадкой по %s · месяцы раскрываются кнопкой «+» "
              "слева" % as_of.strftime("%d.%m.%Y"),
    )

    for i, w in enumerate([3, 34, 22, 40, 22, 4], start=1):
        ws.column_dimensions[get_column_letter(i)].width = w

    f_section = Font(name=FONT, size=10, bold=True, color=TEXT)
    f_hdr = Font(name=FONT, size=9, bold=True, color="FFFFFF")
    f_label = Font(name=FONT, size=10, color=TEXT)
    f_label_b = Font(name=FONT, size=10, bold=True, color=TEXT)
    f_month = Font(name=FONT, size=10, bold=True, color=TEXT)
    f_date = Font(name=FONT, size=9, color=TEXT_2)
    f_income = Font(name=FONT, size=9, color=INCOME)
    f_income_b = Font(name=FONT, size=10, bold=True, color=INCOME)
    f_bold_num = Font(name=FONT, size=10, bold=True, color=TEXT)
    f_note = Font(name=FONT, size=8, color=MUTED)

    def section(r, text):
        write(ws, r, 2, text, font=f_section, align="left", border=B_SECTION)
        for cc in range(3, ncols + 1):
            ws.cell(row=r, column=cc).border = B_SECTION
        ws.row_dimensions[r].height = 18
        return r + 1

    total_in = round(sum(x["amount"] for x in receipts), 2)

    # ------------------------------------------------------------- сводка
    r = 7
    r = section(r, "СВОДКА")

    summary = [
        ("Поступило на расчётный счёт", total_in, f_income_b,
         "Поступления от площадки за всё время работы, %d %s"
         % (len(receipts),
            "поступление" if len(receipts) == 1 else "поступлений")),
        ("Списано с баланса WB, всего", withdrawn_total, f_label_b,
         "Та же строка «Выведено средств, всего» на листе «Остатки ДС»"),
        ("Разница", round(withdrawn_total - total_in, 2), f_bold_num,
         "Списано площадкой, но на счёт ещё не зачислено — деньги в пути"),
    ]
    first_sum_row = r
    for lbl, value, fnt, hint in summary:
        write(ws, r, 2, lbl, font=f_label, border=B_BOTTOM,
              align="left", indent=1)
        write(ws, r, 3, value, font=fnt, fmt=FMT_MONEY,
              border=B_BOTTOM, align="right")
        write(ws, r, 4, hint, font=f_note, border=B_BOTTOM, align="left")
        ws.merge_cells(start_row=r, start_column=4, end_row=r, end_column=ncols)
        for cc in range(5, ncols + 1):
            ws.cell(row=r, column=cc).border = B_BOTTOM
        ws.row_dimensions[r].height = 17
        r += 1

    r += 1

    # ------------------------------------------ расшифровка по поступлениям
    r = section(r, "РАСШИФРОВКА ПО ДАТАМ ПОСТУПЛЕНИЯ")

    headers = [
        (2, "Дата поступления на счёт", "left"),
        (3, "Сумма поступления", "right"),
        (4, "Плательщик", "left"),
    ]
    for col, text, align in headers:
        write(ws, r, col, text, font=f_hdr, fillc=NAVY, align=align,
              indent=1 if align == "left" else 0, wrap=True)
    for cc in (5, ncols):
        ws.cell(row=r, column=cc).fill = fill(NAVY)
    ws.row_dimensions[r].height = 22
    hdr_row = r
    r += 1

    months = OrderedDict()
    for x in sorted(receipts, key=lambda x: x["dt"]):
        months.setdefault((x["dt"].year, x["dt"].month), []).append(x)

    month_rows = []
    for (year, month), group in months.items():
        month_row = r
        r += 1
        first_detail = r

        for x in group:
            write(ws, r, 2, x["dt"], font=f_date, fmt=FMT_DATE,
                  border=B_BOTTOM, align="left", indent=1)
            write(ws, r, 3, x["amount"], font=f_income, fmt=FMT_MONEY,
                  border=B_BOTTOM, align="right")
            write(ws, r, 4, x["cp_name"] or "Маркетплейс", font=f_date,
                  border=B_BOTTOM, align="left", indent=1)
            for cc in (5, ncols):
                ws.cell(row=r, column=cc).border = B_BOTTOM
            ws.row_dimensions[r].outlineLevel = 1
            ws.row_dimensions[r].hidden = True
            ws.row_dimensions[r].height = 16
            r += 1

        last_detail = r - 1
        write(ws, month_row, 2, "%s %d" % (MONTHS_RU[month - 1], year),
              font=f_month, fillc=SURFACE_2, border=B_BOTTOM_STRONG,
              align="left", indent=1)
        write(ws, month_row, 3, "=SUM(C%d:C%d)" % (first_detail, last_detail),
              font=f_income_b, fmt=FMT_MONEY, fillc=SURFACE_2,
              border=B_BOTTOM_STRONG, align="right")
        write(ws, month_row, 4, "поступлений: %d" % len(group), font=f_note,
              fillc=SURFACE_2, border=B_BOTTOM_STRONG, align="left", indent=1)
        for cc in (5, ncols):
            ws.cell(row=month_row, column=cc).fill = fill(SURFACE_2)
            ws.cell(row=month_row, column=cc).border = B_BOTTOM_STRONG
        ws.row_dimensions[month_row].height = 18
        month_rows.append(month_row)

    # итог — сумма только строк месяцев: складывать диапазон нельзя,
    # внутри него лежат и месячные итоги, и сами поступления
    write(ws, r, 2, "ИТОГО ЗА ВСЁ ВРЕМЯ", font=f_label_b, fillc=TOTAL_ROW,
          border=B_TOTAL, align="left", indent=1)
    formula = ("=" + "+".join("C%d" % rr for rr in month_rows)
               if month_rows else 0)
    write(ws, r, 3, formula, font=f_income_b, fmt=FMT_MONEY, fillc=TOTAL_ROW,
          border=B_TOTAL, align="right")
    write(ws, r, 4, "поступлений всего: %d" % len(receipts), font=f_note,
          fillc=TOTAL_ROW, border=B_TOTAL, align="left", indent=1)
    for cc in (5, ncols):
        ws.cell(row=r, column=cc).fill = fill(TOTAL_ROW)
        ws.cell(row=r, column=cc).border = B_TOTAL
    ws.row_dimensions[r].height = 20
    total_row = r
    r += 2

    # сводка ссылается на итог расшифровки — цифры не разъезжаются
    ws.cell(row=first_sum_row, column=3).value = "=C%d" % total_row

    note = (
        "Что на листе. Каждая строка — поступление от маркетплейса на "
        "расчётный счёт: дата, сумма и плательщик, всё по данным учёта. "
        "Месяцы свёрнуты, в строке месяца — сумма за месяц и количество "
        "поступлений; раскрываются кнопкой «+» слева.\n"
       
    )
    write(ws, r, 2, note, font=f_note, align="left", wrap=True, indent=1)
    ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=ncols)
    ws.row_dimensions[r].height = 58

    ws.freeze_panes = ws.cell(row=hdr_row + 1, column=1)
    ws.print_title_rows = "1:%d" % hdr_row
    ws.sheet_properties.outlinePr.summaryBelow = False
    return r


# =============================================================================
#  07D. ЛИСТ «РАСШИФРОВКИ P&L» (ноты)
#
#      Каждая строка разделов 3-8 раскрывается на три уровня вниз:
#      статья → контрагент → договор (для удержаний площадки — настолько,
#      насколько позволяет витрина WB). Из P&L в колонке «НОТА» стоит
#      ссылка, которая ведёт ровно на нужный блок этого листа.
#
#      Лист заменил прежнюю сводную по P&L: та строилась на бухгалтерской
#      витрине и не сходилась с нашим управленческим P&L.
# =============================================================================

NOTES_SHEET_NAME = "Расшифровки P&L"


def build_pl_notes(ws, note_rows, months, report_date, as_of=None):
    """
    note_rows — строки витрины pl_notes:
                (section, item, lvl1, lvl2, lvl3, me, amount)

    Возвращает словарь якорей для ссылок из P&L:
        {("section", None): строка раздела,
         ("section", "item"): строка статьи}
    """
    as_of = as_of or report_date

    # ---- дерево: раздел → статья → уровень 1 → уровень 2 → уровень 3
    tree = OrderedDict()
    for section, item, lvl1, lvl2, lvl3, me, amount in note_rows:
        me = me if isinstance(me, date) else date.fromisoformat(str(me))
        if me not in months or not amount:
            continue
        node = tree.setdefault(section, OrderedDict()).setdefault(item, OrderedDict())
        node = node.setdefault(lvl1 or "", OrderedDict())
        node = node.setdefault(lvl2 or "", OrderedDict())
        vals = node.setdefault(lvl3 or "", {})
        vals[me] = vals.get(me, 0.0) + float(amount)

    cols = make_columns(months)
    ncols = COL_FIRST + len(cols) - 1

    sheet_setup(ws)
    title_band(
        ws,
        "РАСШИФРОВКИ К ОТЧЁТУ О ПРИБЫЛЯХ И УБЫТКАХ",
        "Статья → контрагент → договор",
        ncols,
        extra="Российский рубль (RUB) · дата отчёта: %s · период: %s — %s · "
              "уровни ниже третьего раскрываются кнопкой «+» слева"
              % (as_of.strftime("%d.%m.%Y"),
                 month_label(months[0]), month_label(months[-1])),
    )

    hdr_year, hdr = 6, 7
    columns_header(ws, cols, hdr_year, hdr, report_date.year)
    


    f_band = Font(name=FONT, size=10, bold=True, color=TEXT)
    f_item = Font(name=FONT, size=10, bold=True, color=TEXT)
    f_lvl = Font(name=FONT, size=9, color=TEXT)
    f_lvl_deep = Font(name=FONT, size=9, color=TEXT_2)
    f_num = Font(name=FONT, size=9, color=EXPENSE)
    f_num_bold = Font(name=FONT, size=10, bold=True, color=EXPENSE)
    f_total = Font(name=FONT, size=10, bold=True, color=TEXT)

    anchors = {}
    r = hdr + 1
    
    
    def split_code_from_label(label):
        if not label:
            return "", label

        text = str(label).strip()
        head, sep, tail = text.partition(" ")

        if not sep:
            return "", label

        clean_head = head.rstrip(".")

        if clean_head.replace(".", "").isdigit():
            return clean_head, tail.strip()

        return "", label

    def money_row(row, label, values_by_month, *, font, num_font, bg, bd,
                  indent, outline):
        display_code, display_label = split_code_from_label(label)

        write(ws, row, COL_CODE, display_code, font=f_lvl, fillc=bg, border=bd,
            align="left", indent=1)
        write(ws, row, COL_LABEL, display_label, font=font, fillc=bg, border=bd,
            align="left", indent=indent)
        for i in range(len(cols)):
            v = period_formula(cols, i, row,
                               lambda m: values_by_month.get(m))
            fillv = bg if bg else (SURFACE_3 if cols[i][0] != "month" else None)
            write(ws, row, COL_FIRST + i, v, font=num_font, fmt=FMT_MONEY,
                  fillc=fillv, border=bd, align="right")
        if outline:
            ws.row_dimensions[row].outlineLevel = outline
            ws.row_dimensions[row].hidden = (outline >= 2)
        ws.row_dimensions[row].height = 16

    def agg(node):
        """Суммы по месяцам для узла дерева.

        Лист — это уже готовый словарь {месяц: сумма}; ветка — словарь
        подузлов. Всё складывается здесь, в python, поэтому в ячейках
        уровней стоят числа, а не формулы по диапазону строк: диапазон
        захватывал бы промежуточные итоги контрагентов и договоров и
        задваивал суммы.
        """
        if not isinstance(node, OrderedDict):
            return node
        out = {}
        for child in node.values():
            for m, v in agg(child).items():
                out[m] = out.get(m, 0.0) + v
        return out

    def collapse(node):
        """Именованные подуровни текущего узла.

        Пустой ключ «» означает, что детализации на этом уровне нет.
        Если кроме него ничего нет — уровень схлопывается в родителя.
        Если он соседствует с именованными — показываем его отдельной
        строкой, иначе его сумма выпала бы из итога.
        """
        named = [(k, v) for k, v in node.items() if k]
        if named and "" in node:
            named.append(("Без детализации", node[""]))
        return named

    for section in sorted(tree):
        ws.merge_cells(start_row=r, start_column=COL_CODE,
                       end_row=r, end_column=COL_LABEL)
        write(ws, r, COL_CODE, section, font=f_band, align="left", indent=1,
              border=B_SECTION)
        for cc in range(COL_CODE, ncols + 1):
            ws.cell(row=r, column=cc).border = B_SECTION
        ws.row_dimensions[r].height = 18
        anchors[(section, None)] = r
        r += 1

        for item, lvl1_node in tree[section].items():
            item_row = r
            anchors[(section, item)] = item_row
            money_row(item_row, item, agg(lvl1_node), font=f_item,
                      num_font=f_num_bold, bg=SURFACE_2, bd=B_BOTTOM_STRONG,
                      indent=1, outline=0)
            r += 1

            for lvl1, lvl2_node in lvl1_node.items():
                money_row(r, lvl1 or "Без детализации", agg(lvl2_node),
                          font=f_lvl, num_font=f_num, bg=None,
                          bd=B_BOTTOM, indent=3, outline=1)
                r += 1

                for lvl2, lvl3_node in collapse(lvl2_node):
                    money_row(r, lvl2, agg(lvl3_node), font=f_lvl_deep,
                              num_font=f_num, bg=None, bd=B_BOTTOM,
                              indent=5, outline=2)
                    r += 1

                    for lvl3, vals in collapse(lvl3_node):
                        money_row(r, lvl3, vals, font=f_lvl_deep, num_font=f_num,
                                  bg=None, bd=B_BOTTOM, indent=7, outline=3)
                        r += 1

        # итог раздела — сумма его статей
        write(ws, r, COL_CODE, "", font=f_total, fillc=TOTAL_ROW, border=B_TOTAL)
        write(ws, r, COL_LABEL, "ИТОГО %s" % section.split(". ", 1)[-1],
              font=f_total, fillc=TOTAL_ROW, border=B_TOTAL,
              align="left", indent=1)
        section_vals = agg(tree[section])
        for i in range(len(cols)):
            v = period_formula(cols, i, r, lambda m: section_vals.get(m))
            write(ws, r, COL_FIRST + i, v, font=f_total, fmt=FMT_MONEY,
                  fillc=TOTAL_ROW, border=B_TOTAL, align="right")
        ws.row_dimensions[r].height = 18
        r += 2

    ws.column_dimensions["A"].width = 3
    ws.column_dimensions["B"].width = 12
    ws.column_dimensions["C"].width = 62
    ws.column_dimensions[get_column_letter(COL_NOTE)].hidden = True
    apply_zebra(ws, hdr + 1, r - 1, COL_CODE, ncols)
    apply_column_dividers(ws, hdr, r - 1, COL_CODE, ncols)
    columns_layout(ws, cols, report_date.year)
    ws.freeze_panes = ws.cell(row=hdr + 1, column=COL_FIRST)
    ws.print_title_rows = "1:%d" % hdr
    ws.sheet_properties.outlinePr.summaryBelow = False
    return anchors


# =============================================================================
#  07E. ЛИСТ «ТОЧКА БЕЗУБЫТОЧНОСТИ»
#
#      Модель «затраты — объём — прибыль» поверх P&L: затраты делятся на
#      переменные и постоянные, ТБУ = постоянные затраты / КМД.
#      Все значения — ссылки на P&L и формулы Excel; колонки совпадают с P&L.
#      Годовые и итоговые колонки считаются от сумм периода, а не как сумма
#      помесячных ТБУ.
# =============================================================================

BREAKEVEN_SHEET_NAME = "Точка безубыточности"
BE_NOTES_SHEET_NAME = "Пояснения ТБУ"
PL_SHEET_NAME = "P&L"

BE_DELTA_DEFAULT = 100_000       # прирост постоянных затрат в месяц, ₽
BE_KMD_STEPS = (-2, -1, 1, 2)    # шаги чувствительности КМД, п.п.
CONV_LOAN_TITLE_ID = 27          # тип договора «Договор конвертируемого займа»
BE_INPUT_ROW = 6
BE_INPUT_CELL = "$D$%d" % BE_INPUT_ROW
BE_KMD_FOOTNOTE = (
    "* КМД — коэффициент маржинального дохода: какая доля каждого рубля выручки "
    "остаётся после переменных затрат (себестоимость, комиссия WB, логистика, "
    "хранение, реклама) на покрытие постоянных затрат и прибыль.\n"
    "КМД = Маржинальный доход / Чистая выручка без НДС × 100 % (строка 3.1 / строка 1.2).\n"
    "Пример: продали на 100 ₽, переменные затраты — 70 ₽ → маржинальный доход 30 ₽, КМД = 30 %."
)


def _be_tbu(fc, k):
    """ТБУ = −постоянные / КМД; пусто без выручки, «н/д» при КМД ≤ 0."""
    return ('IF(ISNUMBER({k}),IF({k}>0,MAX(0,-({fc}))/{k}*100,"н/д"),"")'
            .format(fc=fc, k=k))


def be_layout():
    """
    Строки листа: (kind, code, label, spec, role, fmt, source).
      link  — ссылка на строку P&L, spec = код строки P&L
      calc  — сумма строк листа, spec = [(код, знак), ...]
      ratio — отношение, spec = (числитель, знаменатель, множитель)
      expr  — формула, spec = f(ref) -> текст формулы; ref(код) -> адрес ячейки
      count — служебный счётчик, spec = 'months' | 'days'
      input — сценарный прирост из ячейки ввода
    """
    L = []
    add = L.append
    blank = ("blank", None, None, None, None, None, None)

    add(("band", "1", "ВЫРУЧКА", None, None, None, None))
    add(("link", "1.1", "Продажи до СПП с НДС (валовый оборот WB), справочно",
         "1.1", "ref", FMT_MONEY, "P&L 1.1"))
    add(("link", "1.2", "ЧИСТАЯ ВЫРУЧКА БЕЗ НДС — база расчёта",
         "1.4", "total", FMT_MONEY, "P&L 1.4"))
    add(("link", "1.3", "Продажи, шт", "2.1", "ref", FMT_QTY, "P&L 2.1"))
    add(("ratio", "1.4", "Средняя цена продажи без НДС, ₽",
         ("1.2", "1.3", 1), "ref", FMT_PRICE, "= 1.2 / 1.3"))
    add(blank)

    add(("band", "2", "ПЕРЕМЕННЫЕ ЗАТРАТЫ — растут вместе с продажами",
         None, None, None, None))
    add(("link", "2.1", "Себестоимость проданного товара (FIFO)",
         "1.6", "expense", FMT_MONEY, "P&L 1.6"))
    add(("link", "2.2", "Комиссия WB", "1.9", "expense", FMT_MONEY, "P&L 1.9"))
    add(("link", "2.3", "Расходы на реализацию WB (логистика, хранение)",
         "3", "expense", FMT_MONEY, "P&L разд. 3"))
    add(("link", "2.4", "Продвижение WB (реклама, буст, отзывы)",
         "4", "expense", FMT_MONEY, "P&L разд. 4"))
    add(("calc", "2.5", "ИТОГО ПЕРЕМЕННЫЕ ЗАТРАТЫ",
         [("2.1", 1), ("2.2", 1), ("2.3", 1), ("2.4", 1)],
         "total_expense", FMT_MONEY, "= 2.1 + 2.2 + 2.3 + 2.4"))
    add(("ratio", "2.6", "Переменные затраты, % к чистой выручке",
         ("2.5", "1.2", -100), "ratio", FMT_PCT, "= −2.5 / 1.2"))
    add(blank)

    add(("band", "3", "МАРЖИНАЛЬНЫЙ ДОХОД — покрывает постоянные затраты",
         None, None, None, None))
    add(("calc", "3.1", "МАРЖИНАЛЬНЫЙ ДОХОД",
         [("1.2", 1), ("2.5", 1)], "total", FMT_MONEY, "= 1.2 + 2.5  (= P&L GP2)"))
    add(("ratio", "3.2", "КОЭФФИЦИЕНТ МАРЖИНАЛЬНОГО ДОХОДА (КМД)*, %",
         ("3.1", "1.2", 100), "key", FMT_PCT, "= 3.1 / 1.2"))
    add(("expr", "3.3", "Выручка, нужная на каждый 1 ₽ постоянных затрат, ₽",
         lambda r: 'IF(ISNUMBER({k}),IF({k}>0,100/{k},"н/д"),"")'.format(k=r("3.2")),
         "ref", FMT_PRICE, "= 1 / КМД"))
    add(blank)

    add(("band", "4", "ПОСТОЯННЫЕ ЗАТРАТЫ — не зависят от объёма продаж",
         None, None, None, None))
    add(("link", "4.1", "Накладные расходы", "6", "expense", FMT_MONEY,
         "P&L разд. 6"))
    add(("link", "4.2", "Корпоративные расходы", "7", "expense", FMT_MONEY,
         "P&L разд. 7"))
    add(("link", "4.3", "Финансовые расходы (проценты по кредитам и займам)",
         "8", "expense", FMT_MONEY, "P&L разд. 8"))
    add(("calc", "4.4", "ИТОГО ПОСТОЯННЫЕ ЗАТРАТЫ",
         [("4.1", 1), ("4.2", 1), ("4.3", 1)],
         "total_expense", FMT_MONEY, "= 4.1 + 4.2 + 4.3"))
    add(("data", "4.5", "из них проценты по договорам конвертируемого займа",
         "conv", "expense", FMT_MONEY, "учёт, тип дог. %d" % CONV_LOAN_TITLE_ID))
    add(("calc", "4.6", "Постоянные затраты без процентов по конвертируемым займам",
         [("4.4", 1), ("4.5", -1)], "ref", FMT_MONEY, "= 4.4 − 4.5"))
    add(blank)

    add(("band", "5", "ТОЧКА БЕЗУБЫТОЧНОСТИ", None, None, None, None))
    add(("expr", "5.1", "ТБУ по EBITDA (без финансовых расходов), ₽",
         lambda r: _be_tbu("%s+%s" % (r("4.1"), r("4.2")), r("3.2")),
         "ref", FMT_MONEY, "= −(4.1 + 4.2) / КМД"))
    add(("expr", "5.2", "ТОЧКА БЕЗУБЫТОЧНОСТИ — прибыль до налога = 0, ₽",
         lambda r: _be_tbu(r("4.4"), r("3.2")),
         "grand", FMT_MONEY, "= −4.4 / КМД"))
    add(("expr", "5.3", "Точка безубыточности в штуках",
         lambda r: 'IF(AND(ISNUMBER({t}),ISNUMBER({p})),{t}/{p},"")'
                   .format(t=r("5.2"), p=r("1.4")),
         "ref", FMT_QTY, "= 5.2 / 1.4"))
    add(("expr", "5.4", "ТБУ в среднем за месяц, ₽",
         lambda r: 'IF(ISNUMBER({t}),{t}/{m},{t})'.format(t=r("5.2"), m=r("10.1")),
         "ref", FMT_MONEY, "= 5.2 / 10.1"))
    add(("expr", "5.5", "ТБУ в среднем за день, ₽",
         lambda r: 'IF(ISNUMBER({t}),{t}/{d},{t})'.format(t=r("5.2"), d=r("10.2")),
         "ref", FMT_MONEY, "= 5.2 / 10.2"))
    add(("expr", "5.6", "ЗАПАС ФИНАНСОВОЙ ПРОЧНОСТИ, ₽",
         lambda r: 'IF(ISNUMBER({t}),{v}-{t},"")'.format(t=r("5.2"), v=r("1.2")),
         "total", FMT_MONEY, "= 1.2 − 5.2"))
    add(("expr", "5.7", "Запас финансовой прочности, % к чистой выручке",
         lambda r: 'IF(AND(ISNUMBER({z}),{v}<>0),{z}/{v}*100,"")'
                   .format(z=r("5.6"), v=r("1.2")),
         "ratio", FMT_PCT, "= 5.6 / 1.2"))
    add(("expr", "5.8", "Статус: выручка выше или ниже ТБУ",
         lambda r: ('IF(NOT(ISNUMBER({k})),"",IF({k}<=0,"КМД ≤ 0",'
                    'IF({v}>={t},"выше ТБУ","ниже ТБУ")))'
                    .format(k=r("3.2"), v=r("1.2"), t=r("5.2"))),
         "status", None, "факт 1.2 против 5.2"))
    add(blank)

    add(("band", "6", "ТОЧКА БЕЗУБЫТОЧНОСТИ БЕЗ ПРОЦЕНТОВ ПО КОНВЕРТИРУЕМЫМ ЗАЙМАМ",
         None, None, None, None))
    add(("expr", "6.1", "ТБУ БЕЗ ПРОЦЕНТОВ ПО КОНВ. ЗАЙМАМ — прибыль до налога = 0, ₽",
         lambda r: _be_tbu(r("4.6"), r("3.2")),
         "grand", FMT_MONEY, "= −4.6 / КМД"))
    add(("expr", "6.2", "Точка безубыточности в штуках",
         lambda r: 'IF(AND(ISNUMBER({t}),ISNUMBER({p})),{t}/{p},"")'
                   .format(t=r("6.1"), p=r("1.4")),
         "ref", FMT_QTY, "= 6.1 / 1.4"))
    add(("expr", "6.3", "ТБУ в среднем за месяц, ₽",
         lambda r: 'IF(ISNUMBER({t}),{t}/{m},{t})'.format(t=r("6.1"), m=r("10.1")),
         "ref", FMT_MONEY, "= 6.1 / 10.1"))
    add(("expr", "6.4", "ТБУ в среднем за день, ₽",
         lambda r: 'IF(ISNUMBER({t}),{t}/{d},{t})'.format(t=r("6.1"), d=r("10.2")),
         "ref", FMT_MONEY, "= 6.1 / 10.2"))
    add(("expr", "6.5", "ЗАПАС ФИНАНСОВОЙ ПРОЧНОСТИ, ₽",
         lambda r: 'IF(ISNUMBER({t}),{v}-{t},"")'.format(t=r("6.1"), v=r("1.2")),
         "total", FMT_MONEY, "= 1.2 − 6.1"))
    add(("expr", "6.6", "Запас финансовой прочности, % к чистой выручке",
         lambda r: 'IF(AND(ISNUMBER({z}),{v}<>0),{z}/{v}*100,"")'
                   .format(z=r("6.5"), v=r("1.2")),
         "ratio", FMT_PCT, "= 6.5 / 1.2"))
    add(("expr", "6.7", "Статус: выручка выше или ниже ТБУ",
         lambda r: ('IF(NOT(ISNUMBER({k})),"",IF({k}<=0,"КМД ≤ 0",'
                    'IF({v}>={t},"выше ТБУ","ниже ТБУ")))'
                    .format(k=r("3.2"), v=r("1.2"), t=r("6.1"))),
         "status", None, "факт 1.2 против 6.1"))
    add(("expr", "6.8", "Разница с ТБУ из 5.2 — выручка на проценты по конв. займам, ₽",
         lambda r: 'IF(AND(ISNUMBER({a}),ISNUMBER({b})),{a}-{b},"")'
                   .format(a=r("5.2"), b=r("6.1")),
         "ref", FMT_MONEY, "= 5.2 − 6.1"))
    add(blank)

    add(("band", "7", "СЦЕНАРИЙ: РОСТ ПОСТОЯННЫХ ЗАТРАТ (сумма — в ячейке D6)",
         None, None, None, None))
    add(("input", "7.1", "Прирост постоянных затрат, ₽", None,
         "expense", FMT_MONEY, "= D6 × 10.1"))
    add(("expr", "7.2", "НУЖНЫЙ ПРИРОСТ ЧИСТОЙ ВЫРУЧКИ БЕЗ НДС, ₽",
         lambda r: 'IF(ISNUMBER({k}),IF({k}>0,{x}/{k}*100,"н/д"),"")'
                   .format(k=r("3.2"), x=r("7.1")),
         "key", FMT_MONEY, "= 7.1 / КМД"))
    add(("expr", "7.3", "То же в продажах до СПП с НДС (как в отчёте WB), ₽",
         lambda r: 'IF(AND(ISNUMBER({y}),{v}<>0),{y}*{g}/{v},"")'
                   .format(y=r("7.2"), g=r("1.1"), v=r("1.2")),
         "ref", FMT_MONEY, "= 7.2 × 1.1 / 1.2"))
    add(("expr", "7.4", "Нужный прирост выручки, % к факту",
         lambda r: 'IF(AND(ISNUMBER({y}),{v}<>0),{y}/{v}*100,"")'
                   .format(y=r("7.2"), v=r("1.2")),
         "ratio", FMT_PCT, "= 7.2 / 1.2"))
    add(("expr", "7.5", "Нужный прирост продаж, шт",
         lambda r: 'IF(AND(ISNUMBER({y}),ISNUMBER({p})),{y}/{p},"")'
                   .format(y=r("7.2"), p=r("1.4")),
         "ref", FMT_QTY, "= 7.2 / 1.4"))
    add(("expr", "7.6", "Новая точка безубыточности, ₽",
         lambda r: 'IF(AND(ISNUMBER({t}),ISNUMBER({y})),{t}+{y},"")'
                   .format(t=r("5.2"), y=r("7.2")),
         "total", FMT_MONEY, "= 5.2 + 7.2"))
    add(blank)

    add(("band", "8", "ЧУВСТВИТЕЛЬНОСТЬ: ТБУ ПРИ ИЗМЕНЕНИИ КМД", None, None, None, None))
    for n, step in enumerate(BE_KMD_STEPS, 1):
        add(("expr", "8.%d" % n,
             "ТБУ при КМД %s%d п.п., ₽" % ("+" if step > 0 else "−", abs(step)),
             lambda r, s=step: ('IF(ISNUMBER({k}),IF({k}+({s})>0,MAX(0,-{fc})/({k}+({s}))*100,'
                                '"н/д"),"")'.format(k=r("3.2"), s=s, fc=r("4.4"))),
             "ref", FMT_MONEY,
             "= −4.4 / (КМД %s%d)" % ("+" if step > 0 else "−", abs(step))))
    add(blank)

    add(("band", "9", "СВЕРКА С P&L", None, None, None, None))
    add(("calc", "9.1", "Прибыль по модели ТБУ (маржинальный доход − постоянные)",
         [("3.1", 1), ("4.4", 1)], "total", FMT_MONEY, "= 3.1 + 4.4"))
    add(("link", "9.2", "Прочие доходы и расходы — в модель ТБУ не входят",
         "5", "ref", FMT_MONEY, "P&L разд. 5"))
    add(("link", "9.3", "Прибыль до налогообложения по P&L (EBT)",
         "EBT", "total", FMT_MONEY, "P&L EBT"))
    add(("expr", "9.4", "Контроль: 9.1 + 9.2 − 9.3, должно быть 0",
         lambda r: 'ROUND({a}+{b}-{c},0)'.format(a=r("9.1"), b=r("9.2"), c=r("9.3")),
         "check", FMT_MONEY, "= 9.1 + 9.2 − 9.3"))
    add(blank)

    add(("band", "10", "СЛУЖЕБНЫЕ СТРОКИ", None, None, None, None))
    add(("count", "10.1", "Месяцев в колонке", "months", "ref", FMT_QTY, "календарь"))
    add(("count", "10.2", "Календарных дней в колонке (по дату отчёта)", "days",
         "ref", FMT_QTY, "календарь"))
    return L


def build_breakeven(ws, pl_rowmap, months, report_date, as_of=None,
                    conv_by_month=None):
    """
    pl_rowmap     — {код строки P&L: номер строки на листе P&L}.
    conv_by_month — {me: проценты по конвертируемым займам}, знак как в P&L.
    Колонки листа совпадают с колонками P&L, поэтому ссылки идут в ту же букву.
    """
    as_of = as_of or report_date
    cols = make_columns(months)
    ncols = COL_FIRST + len(cols) - 1

    sheet_setup(ws)
    title_band(
        ws,
        "ТОЧКА БЕЗУБЫТОЧНОСТИ (ТБУ)",
        "Модель «затраты — объём — прибыль» на данных P&L · "
        "ТБУ = постоянные затраты / коэффициент маржинального дохода (КМД)",
        ncols,
        extra="Российский рубль (RUB) · выручка без НДС · дата отчёта: %s · "
              "период: %s — %s"
              % (as_of.strftime("%d.%m.%Y"),
                 month_label(months[0]), month_label(months[-1])),
    )

    # ---- ячейка ввода сценария
    ri = BE_INPUT_ROW
    ws.merge_cells(start_row=ri, start_column=COL_CODE, end_row=ri, end_column=COL_LABEL)
    write(ws, ri, COL_CODE,
          "СЦЕНАРИЙ · прирост постоянных затрат в месяц, ₽  →",
          font=Font(name=FONT, size=10, bold=True, color=NAVY_3),
          fillc=SURFACE_4, align="left", indent=1)
    ws.cell(row=ri, column=COL_LABEL).fill = fill(SURFACE_4)
    box = Border(left=_side(WARN), right=_side(WARN),
                 top=_side(WARN), bottom=_side(WARN))
    write(ws, ri, COL_NOTE, BE_DELTA_DEFAULT,
          font=Font(name=FONT, size=11, bold=True, color=TEXT),
          fmt=FMT_MONEY, fillc=WARN_BG, border=box, align="center")
    ws.row_dimensions[ri].height = 22

    ws.merge_cells(start_row=ri + 1, start_column=COL_CODE,
                   end_row=ri + 1, end_column=COL_NOTE)
    c = write(ws, ri + 1, COL_CODE,
              "Жёлтую ячейку можно менять — раздел 7 пересчитается. "
              "Методика и пример — лист «%s» →" % BE_NOTES_SHEET_NAME,
              font=Font(name=FONT, size=8, italic=True, color=NAVY_3),
              align="left", indent=1)
    c.hyperlink = "#'%s'!A1" % BE_NOTES_SHEET_NAME
    ws.row_dimensions[ri + 1].height = 14

    hdr_year, hdr = ri + 2, ri + 3
    columns_header(ws, cols, hdr_year, hdr, report_date.year,
                   note_header="ИСТОЧНИК / ФОРМУЛА")

    plan = be_layout()
    rowmap, r = {}, hdr + 1
    for kind, code, *_ in plan:
        if code and kind != "band":
            rowmap.setdefault(code, r)
        r += 1

    f_band = Font(name=FONT, size=10, bold=True, color=TEXT)
    f_code = Font(name=FONT, size=8, color=MUTED)
    f_src = Font(name=FONT, size=8, color=MUTED)
    f_label = Font(name=FONT, size=10, color=TEXT)
    f_label_b = Font(name=FONT, size=10, bold=True, color=TEXT)
    f_label_key = Font(name=FONT, size=10, bold=True, color=NAVY_3)
    f_label_small = Font(name=FONT, size=9, color=TEXT_2)

    # role -> (шрифт цифр, шрифт подписи, заливка, граница)
    STYLES = {
        "ref": (Font(name=FONT, size=10, color=INCOME), f_label, None, B_BOTTOM),
        "expense": (Font(name=FONT, size=10, color=EXPENSE), f_label, None, B_BOTTOM),
        "total": (Font(name=FONT, size=10, bold=True, color=TEXT), f_label_b,
                  TOTAL_ROW, B_TOTAL),
        "total_expense": (Font(name=FONT, size=10, bold=True, color=EXPENSE),
                          f_label_b, TOTAL_ROW, B_TOTAL),
        "grand": (Font(name=FONT, size=11, bold=True, color=TEXT), f_label_b,
                  TOTAL_ROW, B_GRAND),
        "key": (Font(name=FONT, size=10, bold=True, color=NAVY_3), f_label_key,
                SURFACE_4, B_TOTAL),
        "ratio": (Font(name=FONT, size=9, color=TEXT_2), f_label_small, None, B_BOTTOM),
        "status": (Font(name=FONT, size=9, bold=True, color=TEXT_2), f_label_small,
                   None, B_BOTTOM),
        "check": (Font(name=FONT, size=9, color=MUTED), f_label_small, None, B_BOTTOM),
    }

    def days_in(m):
        first = date(m.year, m.month, 1)
        end = min(m, as_of) if as_of >= first else m
        return (end - first).days + 1

    r = hdr + 1
    for kind, code, label, spec, role, fmt, source in plan:
        if kind == "blank":
            ws.row_dimensions[r].height = 6
            r += 1
            continue

        if kind == "band":
            ws.merge_cells(start_row=r, start_column=COL_CODE,
                           end_row=r, end_column=COL_NOTE)
            write(ws, r, COL_CODE, "%s. %s" % (code, label), font=f_band,
                  align="left", indent=1, border=B_SECTION)
            for cc in range(COL_CODE, ncols + 1):
                ws.cell(row=r, column=cc).border = B_SECTION
            ws.row_dimensions[r].height = 18
            r += 1
            continue

        f_num, f_lbl, bg, bd = STYLES[role]
        strong = role in ("total", "total_expense", "grand", "key")

        write(ws, r, COL_CODE, code, font=f_code, fillc=bg, border=bd,
              align="left", indent=1)
        write(ws, r, COL_LABEL, label, font=f_lbl, fillc=bg, border=bd,
              align="left", indent=1 if strong else 2)
        c = write(ws, r, COL_NOTE, source, font=f_src, fillc=bg, border=bd,
                  align="left", indent=1)
        c.data_type = "s"      # подсказка «= …» — текст, не формула

        for i in range(len(cols)):
            cl = L(i)

            def ref(key, cl=cl):
                return "%s%d" % (cl, rowmap[key])

            v = None
            if kind == "link":
                pr = pl_rowmap.get(spec)
                v = "='%s'!%s%d" % (PL_SHEET_NAME, cl, pr) if pr else 0
            elif kind == "calc":
                v = "=" + "".join("%s%s" % ("+" if s > 0 else "-", ref(k))
                                  for k, s in spec).lstrip("+")
            elif kind == "ratio":
                num, den, mult = spec
                sign = "-" if mult < 0 else ""
                tail = "" if abs(mult) == 1 else "*%d" % abs(mult)
                v = '=IF(%s=0,"",%s%s/%s%s)' % (ref(den), sign, ref(num),
                                                ref(den), tail)
            elif kind == "expr":
                v = "=" + spec(ref)
            elif kind == "data":
                src = conv_by_month or {}
                v = period_formula(cols, i, rowmap[code], lambda m: src.get(m))
            elif kind == "count":
                v = period_formula(
                    cols, i, rowmap[code],
                    (lambda m: 1) if spec == "months" else days_in)
            elif kind == "input":
                v = period_formula(cols, i, rowmap[code],
                                   lambda m: "=%s" % BE_INPUT_CELL)

            fillv = bg
            if cols[i][0] != "month" and not strong:
                fillv = SURFACE_3
            write(ws, r, COL_FIRST + i, v, font=f_num, fmt=fmt, fillc=fillv,
                  border=bd, align="center" if role == "status" else "right")

        ws.row_dimensions[r].height = 19 if strong else 17
        r += 1
    last_row = r - 1

    # ---- сноска к КМД
    fr = last_row + 2
    ws.merge_cells(start_row=fr, start_column=COL_CODE, end_row=fr, end_column=COL_NOTE)
    c = write(ws, fr, COL_CODE, BE_KMD_FOOTNOTE,
              font=Font(name=FONT, size=9, color=TEXT_2), fillc=SURFACE_5,
              border=Border(top=_side(NAVY)))
    c.alignment = Alignment(horizontal="left", vertical="top", wrap_text=True, indent=1)
    ws.row_dimensions[fr].height = 64

    # ---- условное форматирование
    first_col, last_col = L(0), L(len(cols) - 1)

    def rng(code):
        return "%s%d:%s%d" % (first_col, rowmap[code], last_col, rowmap[code])

    bad_font = Font(name=FONT, bold=True, color=EXPENSE)
    good_font = Font(name=FONT, bold=True, color=FREE)
    for code in ("5.6", "5.7", "6.5", "6.6"):
        ws.conditional_formatting.add(
            rng(code), CellIsRule(operator="lessThan", formula=["0"], font=bad_font))
    for code in ("5.8", "6.7"):
        ws.conditional_formatting.add(
            rng(code), CellIsRule(operator="equal", formula=['"выше ТБУ"'],
                                  font=good_font, fill=fill(FREE_BG)))
        for txt in ("ниже ТБУ", "КМД ≤ 0"):
            ws.conditional_formatting.add(
                rng(code), CellIsRule(operator="equal", formula=['"%s"' % txt],
                                      font=bad_font, fill=fill(OCCUPIED_BG)))
    ws.conditional_formatting.add(
        rng("9.4"), CellIsRule(operator="notEqual", formula=["0"],
                               font=Font(name=FONT, bold=True, color=WARN),
                               fill=fill(WARN_BG)))

    ws.column_dimensions["A"].width = 3
    ws.column_dimensions["B"].width = 7
    ws.column_dimensions["C"].width = 64
    ws.column_dimensions["D"].width = 22
    apply_zebra(ws, hdr + 1, last_row, COL_CODE, ncols)
    apply_column_dividers(ws, hdr, last_row, COL_CODE, ncols)
    columns_layout(ws, cols, report_date.year)
    ws.freeze_panes = ws.cell(row=hdr + 1, column=COL_FIRST)
    ws.print_title_rows = "1:%d" % hdr
    return last_row


NOTES_BE = [
    ("Что такое точка безубыточности", [
        "Точка безубыточности (ТБУ) — выручка, при которой компания работает в ноль: "
        "маржинальный доход от продаж ровно покрывает постоянные затраты, прибыль "
        "до налога равна нулю. Каждый рубль выручки сверх ТБУ приносит прибыль, "
        "каждый рубль ниже — убыток.",
        "Лист отвечает на три вопроса: сколько нужно продавать, чтобы не терять деньги; "
        "насколько фактические продажи выше этого уровня (запас прочности); на сколько "
        "должна вырасти выручка, если вырастут затраты.",
    ]),
    ("Главная формула", [
        "ТБУ, ₽ = Постоянные затраты / КМД.",
        "КМД (коэффициент маржинального дохода) = Маржинальный доход / Чистая выручка — "
        "сколько копеек с каждого рубля выручки остаётся после переменных затрат.",
        "Маржинальный доход = Чистая выручка без НДС − Переменные затраты.",
        "Чистая выручка — строка 1.4 P&L «Продажи без НДС». Та же база, что и для всех "
        "процентов рентабельности в пакете, поэтому КМД напрямую сопоставим с "
        "показателями P&L и юнит-экономики.",
        "Все цифры листа — формулы со ссылками на ячейки P&L: любую можно проверить, "
        "кликнув на ячейку. Колонка «Источник / формула» подсказывает, откуда взята "
        "строка или как она посчитана.",
    ]),
    ("Переменные затраты (раздел 2 листа)", [
        "Переменные — затраты, которые растут пропорционально продажам: нет продажи — "
        "нет затраты.",
        "2.1 Себестоимость проданного товара (P&L 1.6) — FIFO.",
        "2.2 Комиссия WB (P&L 1.9) — процент от каждой продажи.",
        "2.3 Расходы на реализацию WB (P&L раздел 3) — логистика, хранение, приёмка, "
        "штрафы. Хранение формально зависит от остатков, а не от продаж, но на "
        "маркетплейсе остатки планируются под объём продаж, поэтому статья отнесена "
        "к переменным.",
        "2.4 Продвижение WB (P&L раздел 4) — отнесено к переменным, потому что бюджет "
        "рекламы на площадке управляется как доля от выручки (ДРР) и без него продажи "
        "не удерживаются. Если рекламный бюджет фиксирован независимо от продаж, "
        "его прирост удобнее считать через сценарий раздела 7 как рост постоянных затрат.",
        "Итог 3.1 «Маржинальный доход» совпадает со строкой P&L GP2 «Валовая прибыль "
        "после продвижения WB».",
    ]),
    ("Постоянные затраты (раздел 4 листа)", [
        "Постоянные — затраты, которые не зависят от объёма продаж в пределах месяца: "
        "их нужно оплатить, даже если продаж не было.",
        "4.1 Накладные расходы (P&L раздел 6): персонал, аренда, сервисы, банковские "
        "комиссии, закупочные услуги.",
        "4.2 Корпоративные расходы (P&L раздел 7): офис, консалтинг, профессиональные "
        "услуги.",
        "4.3 Финансовые расходы (P&L раздел 8): проценты и комиссии по кредитам и займам.",
        "Не входят в расчёт: раздел 5 P&L «Прочие доходы и расходы» — разовые и "
        "неторговые статьи (корректировки продаж, курсовые разницы, досрочное снятие "
        "средств). Их нельзя планировать как регулярную нагрузку, а включение сделало "
        "бы ТБУ случайной величиной. Их фактическое влияние показано в сверке "
        "(раздел 9 листа).",
        "Налог на прибыль тоже не входит: в точке безубыточности прибыли нет, "
        "значит нет и налога.",
    ]),
    ("Уровни точки безубыточности", [
        "5.1 ТБУ по EBITDA = (накладные + корпоративные) / КМД. Выручка, при которой "
        "бизнес покрывает операционные затраты и выходит в ноль по EBITDA, без учёта "
        "долговой нагрузки.",
        "5.2 ТОЧКА БЕЗУБЫТОЧНОСТИ = (накладные + корпоративные + финансовые) / КМД. "
        "Основной показатель: выручка, при которой прибыль до налога равна нулю. "
        "Разница между 5.2 и 5.1 — сколько выручки нужно, чтобы обслуживать кредиты "
        "и займы.",
        "5.3 ТБУ в штуках = ТБУ, ₽ / средняя цена продажи без НДС (1.4).",
        "5.4 и 5.5 — та же ТБУ в среднем за месяц и за день. В месячной колонке 5.4 "
        "совпадает с 5.2; в годовой показывает среднемесячную планку. Дневная ТБУ — "
        "удобный ориентир для ежедневного контроля продаж по дашборду.",
    ]),
    ("ТБУ без процентов по конвертируемым займам (раздел 6 листа)", [
        "4.5 — проценты по договорам конвертируемого займа (тип договора %d в "
        "справочнике договоров): та часть финансовых расходов раздела 8 P&L, которая "
        "начислена по таким договорам. Допсоглашения учитываются по типу основного "
        "договора. Источник — витрина pl_for_csv, запрос sql/conv_loans.txt." % CONV_LOAN_TITLE_ID,
        "4.6 = 4.4 − 4.5 — постоянные затраты без этих процентов.",
        "Раздел 6 повторяет все показатели раздела 5, но от постоянных затрат 4.6: "
        "ТБУ в рублях, в штуках, в среднем за месяц и за день, запас финансовой "
        "прочности в рублях и процентах, статус. Считается по тем же формулам и с тем "
        "же КМД — отличаются только постоянные затраты.",
        "Зачем: проценты по конвертируемым займам, как правило, не выплачиваются "
        "деньгами, а при конвертации займа в долю перестают быть обязательством "
        "компании. Раздел 6 показывает, какая выручка нужна без этой нагрузки.",
        "6.8 = 5.2 − 6.1 — сколько выручки в месяц «съедают» проценты по "
        "конвертируемым займам.",
        "ТБУ по EBITDA (5.1) отдельно не повторяется: финансовые расходы в неё не "
        "входят, поэтому без процентов по конвертируемым займам она та же.",
    ]),
    ("Запас финансовой прочности и статус", [
        "5.6 Запас финансовой прочности, ₽ = Фактическая чистая выручка − ТБУ. "
        "На сколько могут упасть продажи, прежде чем компания уйдёт в убыток.",
        "5.7 Запас, % = 5.6 / выручка. Ориентиры: выше 20 % — комфортно; 10–20 % — "
        "умеренно; ниже 10 % — любое колебание спроса или рост ставок WB уводит в "
        "убыток; отрицательный — месяц ниже точки безубыточности.",
        "5.8 Статус: «выше ТБУ» (зелёный) или «ниже ТБУ» (красный). «КМД ≤ 0» — "
        "переменные затраты съели всю выручку: каждая продажа убыточна, и увеличение "
        "объёма проблему не решит, ТБУ в этом случае не существует (в ячейках — «н/д»).",
    ]),
    ("Как считается по месяцам", [
        "В колонке месяца все показатели считаются только по данным этого месяца: "
        "ТБУ месяца = постоянные затраты месяца / КМД месяца.",
        "Помесячная ТБУ колеблется сильнее годовой, и это нормально. Причины: "
        "расходы WB в P&L учтены кассовым методом — в месяце удержания, а не продажи "
        "(см. «Пояснения P&L»); отдельные постоянные расходы приходятся на один месяц "
        "(годовые подписки, консалтинг, разовые платежи); себестоимость последних "
        "месяцев уточняется по мере поступления возвратов.",
        "Поэтому для решений опирайтесь на годовую колонку или на несколько месяцев "
        "подряд, а отдельный месяц используйте как сигнал: запас прочности меньше "
        "10 % или статус «ниже ТБУ» — повод разобраться в причинах.",
        "Текущий месяц, если отчёт сформирован не на последний день, неполный: дней "
        "в нём считается по дату отчёта (строка 10.2), и дневная ТБУ корректна, а "
        "месячные суммы ещё будут расти.",
    ]),
    ("Как считается за год и за весь период", [
        "Годовая ТБУ = постоянные затраты за год / КМД за год, где КМД за год = "
        "маржинальный доход за год / выручка за год. Колонка «Итого за период» "
        "считается так же — по суммам всего периода.",
        "Годовая ТБУ НЕ равна сумме помесячных. В месяцы с низким КМД помесячная ТБУ "
        "резко растёт, и простое сложение переоценивало бы годовую планку. Расчёт от "
        "годовых сумм взвешивает каждый месяц по его фактической выручке — это "
        "корректный метод.",
        "Для текущего (незавершённого) года в годовой колонке — данные с января по "
        "отчётный месяц включительно. Строка 5.4 «ТБУ в среднем за месяц» даёт "
        "сопоставимую с месяцами планку: годовая ТБУ / число месяцев (строка 10.1).",
    ]),
    ("Сценарий: что будет, если затраты вырастут на 100 000 ₽", [
        "Нужный прирост выручки = Прирост постоянных затрат / КМД. Чем ниже КМД, тем "
        "больше выручки нужно, чтобы «отбить» каждый новый рубль затрат. Строка 3.3 "
        "показывает этот множитель: сколько рублей выручки нужно на 1 ₽ постоянных затрат.",
        "Сумма прироста задаётся в жёлтой ячейке D6 (по умолчанию 100 000 ₽ в месяц). "
        "Её можно поменять — весь раздел 7 пересчитается. В годовой колонке прирост "
        "умножается на число месяцев: 100 000 ₽ в месяц за 9 месяцев = 900 000 ₽.",
        "7.2 — сколько дополнительной чистой выручки (без НДС) нужно, чтобы прибыль "
        "осталась прежней. 7.3 — то же в продажах до СПП с НДС, в тех цифрах, которые "
        "видны в отчётах WB. 7.4 — на сколько процентов должна вырасти выручка. "
        "7.5 — сколько дополнительных единиц нужно продать. 7.6 — новая ТБУ.",
        "Сценарий применим к любому росту затрат фиксированной суммой: новый сотрудник, "
        "рост аренды, новый сервис, проценты по новому кредиту, фиксированный "
        "рекламный бюджет. Если растут затраты, которые идут процентом от продаж "
        "(комиссия WB, логистика), меняется КМД — для этого раздел 8.",
    ]),
    ("Чувствительность к КМД (раздел 8)", [
        "Показывает, как сдвинется ТБУ, если КМД изменится на 1–2 процентных пункта "
        "при тех же постоянных затратах: ТБУ = постоянные затраты / (КМД ± Δ).",
        "Типичные причины падения КМД: рост комиссии или тарифов логистики WB, "
        "увеличение ДРР, рост закупочных цен, более глубокие скидки. Рост КМД — "
        "повышение цен, снижение себестоимости, смещение продаж в более маржинальный "
        "ассортимент.",
        "Раздел наглядно показывает, что на ТБУ сильнее всего влияет именно маржа: "
        "потеря 1 п.п. КМД часто обходится дороже, чем рост постоянных затрат на "
        "заметную сумму.",
    ]),
    ("Сверка с P&L (раздел 9)", [
        "Прибыль по модели ТБУ = маржинальный доход − постоянные затраты.",
        "Прибыль по модели + прочие доходы и расходы (P&L раздел 5) = прибыль до "
        "налогообложения по P&L (EBT). Строка 9.4 проверяет это равенство и должна "
        "быть равна нулю во всех колонках; ненулевое значение подсвечивается.",
        "Если раздел 5 в каком-то месяце крупный, фактическая прибыль P&L отличается "
        "от модельной — это эффект разовых статей, а не ошибка расчёта ТБУ.",
    ]),
    ("Пример расчёта", [
        "Чистая выручка без НДС — 10 000 000 ₽, переменные затраты (себестоимость, "
        "комиссия, логистика, реклама) — 7 000 000 ₽.",
        "Маржинальный доход = 10 000 000 − 7 000 000 = 3 000 000 ₽; "
        "КМД = 3 000 000 / 10 000 000 = 30 %.",
        "Постоянные затраты — 2 400 000 ₽. ТБУ = 2 400 000 / 0,30 = 8 000 000 ₽. "
        "На 1 ₽ постоянных затрат нужно 1 / 0,30 = 3,33 ₽ выручки.",
        "Запас прочности = 10 000 000 − 8 000 000 = 2 000 000 ₽, или 20 % выручки: "
        "продажи могут упасть на 20 %, прежде чем появится убыток.",
        "Постоянные затраты выросли на 100 000 ₽ в месяц → выручка должна вырасти на "
        "100 000 / 0,30 = 333 333 ₽ (+3,3 %). При средней цене 1 000 ₽ без НДС это "
        "334 дополнительные единицы. Новая ТБУ — 8 333 333 ₽.",
        "КМД снизился на 1 п.п. (с 30 % до 29 %) → ТБУ = 2 400 000 / 0,29 = "
        "8 275 862 ₽, то есть +275 862 ₽ — почти столько же, сколько рост "
        "постоянных затрат на 100 000 ₽.",
    ]),
    ("Допущения и ограничения", [
        "Структура продаж считается неизменной: КМД — средний по всему ассортименту. "
        "Если сместить продажи в товары с другой маржой, КМД и ТБУ изменятся.",
        "Переменные затраты считаются строго пропорциональными выручке, постоянные — "
        "неизменными при росте объёма. На больших скачках объёма это не так: "
        "понадобятся склад, люди, оборотные деньги.",
        "ТБУ — показатель прибыли, а не денег. Выход в ноль по P&L не означает "
        "положительный денежный поток: закупка товара, выплаты по телу кредитов и "
        "задержки выплат WB видны только в Cash Flow.",
        "Данные последних месяцев предварительные (возвраты, пересчёт FIFO, поступление "
        "УПД) — см. «Пояснения P&L». Вместе с ними может сдвинуться и ТБУ.",
    ]),
    ("Как читать колонки", [
        "Колонки те же, что в P&L: месяц — значения за календарный месяц; завершённые "
        "годы свёрнуты (развернуть — кнопкой «+» над таблицей), текущий раскрыт.",
        "В колонках «Итого <год>» и «Итого за период» суммы складываются, а КМД, ТБУ, "
        "запас прочности и сценарии пересчитываются по формуле от сумм периода.",
    ]),
]


# =============================================================================
#  07F. ЛИСТ «ВЫВОДЫ» — резюме отчётного месяца для собственника
#
#      Тексты собираются по тем же данным и правилам, что листы P&L и
#      «Точка безубыточности», поэтому цифры в выводах совпадают с листами.
# =============================================================================

SUMMARY_SHEET_NAME = "Выводы"

MONTHS_NOM = ("январь", "февраль", "март", "апрель", "май", "июнь", "июль",
              "август", "сентябрь", "октябрь", "ноябрь", "декабрь")
MONTHS_PREP = ("январе", "феврале", "марте", "апреле", "мае", "июне", "июле",
               "августе", "сентябре", "октябре", "ноябре", "декабре")

SUM_LOOKBACK = 3          # база сравнения: среднее за N предыдущих месяцев
SUM_PP_THRESHOLD = 1.0    # заметный сдвиг доли затрат в выручке, п.п.
SUM_ITEM_MIN = 300_000    # порог отклонения статьи, ₽
SUM_ITEM_REL = 0.30       # порог отклонения статьи, доля от среднего
SUM_ITEMS_TOP = 4
SUM_WIDTH_CHARS = 105     # символов в строке абзаца (для высоты строк)

FMT_MLN = '#,##0.0,,;(#,##0.0,,);"–"'
NB = " "


def _num(x, d=0):
    return "{:,.{d}f}".format(abs(x), d=d).replace(",", NB).replace(".", ",")


def _rub(x):
    if x is None:
        return "—"
    a, sign = abs(x), ("−" if x < 0 else "")
    if a >= 1e6:
        return "%s%s%sмлн%s₽" % (sign, _num(a / 1e6, 1), NB, NB)
    if a >= 1e3:
        return "%s%s%sтыс.%s₽" % (sign, _num(a / 1e3, 0), NB, NB)
    return "%s%s%s₽" % (sign, _num(a, 0), NB)


def _pct(x, d=1):
    return "—" if x is None else "%s%s%s%%" % ("−" if x < 0 else "", _num(x, d), NB)


def _chg(x, unit="%", d=1):
    return "—" if x is None else "%s%s%s%s" % ("+" if x >= 0 else "−", _num(x, d), NB, unit)


def _res(x):
    """Результат словами: «прибыль 1,2 млн ₽» / «убыток 1,2 млн ₽»."""
    return "—" if x is None else ("прибыль " if x >= 0 else "убыток ") + _rub(abs(x))


def _rel(a, b):
    return (a / b - 1) * 100 if b else None


def _derive(b, n=1):
    """Показатели периода по базовым суммам; n — делитель для среднего."""
    d = {k: v / n for k, v in b.items()}
    rev = d["rev"]
    d["var"] = d["cogs"] + d["comm"] + d["sell"] + d["promo"]
    d["md"] = rev + d["var"]
    d["kmd"] = d["md"] / rev * 100 if rev else None
    d["fc"] = d["ovh"] + d["corp"] + d["fin"]
    d["ebt_model"] = d["md"] + d["fc"]
    d["ebt"] = d["ebt_model"] + d["other"]
    d["net"] = d["ebt"] + d["tax"]
    if d["kmd"] is not None and d["kmd"] > 0:
        d["tbu"] = max(0.0, -d["fc"]) / d["kmd"] * 100
        d["zfp"] = rev - d["tbu"]
        d["zfp_pct"] = d["zfp"] / rev * 100
    else:
        d["tbu"] = d["zfp"] = d["zfp_pct"] = None
    conv = d.get("conv", 0.0)
    if d["tbu"] is not None:
        d["tbu_ex"] = max(0.0, -(d["fc"] - conv)) / d["kmd"] * 100
        d["zfp_ex"] = rev - d["tbu_ex"]
        d["zfp_ex_pct"] = d["zfp_ex"] / rev * 100
    else:
        d["tbu_ex"] = d["zfp_ex"] = d["zfp_ex_pct"] = None
    for k in ("cogs", "comm", "sell", "promo"):
        d[k + "_pct"] = -d[k] / rev * 100 if rev else None
    return d


def _base(pl_data, tax_by_month, me):
    def g(sec, itm):
        return pl_data.get((me, sec, itm)) or 0.0
    return {
        "rev": g(SEC_REVENUE, "1.4 Продажи без НДС"),
        "qty": g(SEC_UNIT, "2.1 Продажи, шт."),
        "cogs": -g(SEC_REVENUE, "1.6. Себестоимость"),
        "comm": g(SEC_REVENUE, "1.9. Комиссия WB"),
        "sell": section_sum(pl_data, me, SEC_SELLING),
        "promo": section_sum(pl_data, me, SEC_PROMO),
        "other": section_sum(pl_data, me, SEC_OTHER),
        "ovh": section_sum(pl_data, me, SEC_OVERHEAD),
        "corp": section_sum(pl_data, me, SEC_CORP),
        "fin": section_sum(pl_data, me, SEC_FIN),
        "tax": tax_by_month.get(me, 0.0),
    }


def month_summary(pl_data, tax_by_month, months, as_of, conv_by_month=None):
    """Цифры и тексты выводов за последний месяц отчёта."""
    me = months[-1]
    i = len(months) - 1
    first = date(me.year, me.month, 1)
    elapsed = (min(me, as_of) - first).days + 1
    total = me.day
    partial = elapsed < total

    def agg(ms):
        out = defaultdict(float)
        for m in ms:
            for k, v in _base(pl_data, tax_by_month, m).items():
                out[k] += v
            out["conv"] += (conv_by_month or {}).get(m, 0.0)
        return dict(out)

    cur = _derive(agg([me]))
    pm = months[i - 1] if i >= 1 else None
    prev = _derive(agg([pm])) if pm else None
    base_ms = months[max(0, i - SUM_LOOKBACK):i]
    avg = _derive(agg(base_ms), len(base_ms)) if base_ms else None
    lym = last_day(date(me.year - 1, me.month, 1))
    ly = _derive(agg([lym])) if lym in months else None
    if ly and not ly["rev"]:
        ly = None
    ytd_ms = [m for m in months if m.year == me.year]
    ytd = _derive(agg(ytd_ms))
    per_month = [(m, _derive(agg([m]))) for m in ytd_ms]

    M = MONTHS_NOM[me.month - 1]
    Mp = MONTHS_PREP[me.month - 1]
    mtitle = "%s %d" % (M, me.year)
    days_txt = " за %d из %d дней" % (elapsed, total) if partial else ""
    k = cur["kmd"]
    rev = cur["rev"]

    # ---- главное
    if not rev:
        tone = "warn"
        head = "В %s нет продаж — точку безубыточности посчитать нельзя." % Mp
    elif k is None or k <= 0:
        tone = "bad"
        head = ("В %s продажи убыточны уже на уровне маржи: переменные затраты "
                "(себестоимость, комиссия, логистика, реклама) больше выручки. "
                "Точки безубыточности нет — рост продаж при такой марже только "
                "увеличит убыток. Результат до налога — %s." % (Mp, _res(cur["ebt"])))
    elif cur["zfp"] < 0:
        tone = "bad"
        head = ("%s — ниже точки безубыточности. Чистая выручка%s — %s, а чтобы "
                "выйти в ноль, нужно %s: не хватило %s (%s выручки). Результат до "
                "налога — %s."
                % (mtitle.capitalize(), days_txt, _rub(rev), _rub(cur["tbu"]),
                   _rub(-cur["zfp"]), _pct(-cur["zfp_pct"]), _res(cur["ebt"])))
    elif cur["zfp_pct"] < 10:
        tone = "warn"
        head = ("%s — в плюсе, но запас минимальный: выручка%s %s выше точки "
                "безубыточности (%s) всего на %s (%s). Небольшое падение продаж "
                "или рост тарифов WB уведёт месяц в убыток. Результат до налога — %s."
                % (mtitle.capitalize(), days_txt, _rub(rev), _rub(cur["tbu"]),
                   _rub(cur["zfp"]), _pct(cur["zfp_pct"]), _res(cur["ebt"])))
    else:
        tone = "good"
        mood = "уверенно в плюсе" if cur["zfp_pct"] >= 20 else "в плюсе с умеренным запасом"
        head = ("%s — %s: выручка%s %s, это на %s (%s) выше точки "
                "безубыточности %s. Результат до налога — %s."
                % (mtitle.capitalize(), mood, days_txt, _rub(rev), _rub(cur["zfp"]),
                   _pct(cur["zfp_pct"]), _rub(cur["tbu"]), _res(cur["ebt"])))
    if partial:
        head += " Месяц ещё не закрыт — итог уточнится."

    blocks = []

    # ---- продажи и маржа
    p = []
    s = "Чистая выручка без НДС — %s" % _rub(rev)
    if cur["qty"]:
        s += ", продано %s шт. по средней цене %s%s₽ без НДС" % (
            _num(cur["qty"]), _num(rev / cur["qty"]), NB)
    p.append(s + ".")

    def cmp(other, m_other, where):
        if not other or not other["rev"]:
            return None
        if partial:
            a, b = rev / elapsed, other["rev"] / m_other.day
            return ("Среднедневная выручка — %s против %s %s (%s)."
                    % (_rub(a), _rub(b), where, _chg(_rel(a, b))))
        return ("Выручка — %s против %s %s (%s)."
                % (_rub(rev), _rub(other["rev"]), where, _chg(_rel(rev, other["rev"]))))

    for line in (cmp(prev, pm, "в %s %d" % (MONTHS_PREP[pm.month - 1], pm.year) if pm else ""),
                 cmp(ly, lym, "в %s %d" % (Mp, lym.year))):
        if line:
            p.append(line)
    if k is not None and rev:
        s = ("КМД — %s: с каждого рубля выручки после себестоимости, комиссии, "
             "логистики и рекламы остаётся %s коп." % (_pct(k), _num(k)))
        if avg and avg["kmd"] is not None:
            s += " В среднем за %d предыдущих месяца — %s (%s)." % (
                len(base_ms), _pct(avg["kmd"]), _chg(k - avg["kmd"], "п.п."))
        p.append(s)
    shifts = []
    if avg and rev:
        for key, name in (("cogs", "Себестоимость"), ("comm", "Комиссия WB"),
                          ("sell", "Логистика, хранение и приёмка WB"),
                          ("promo", "Реклама и продвижение WB")):
            a, b = cur[key + "_pct"], avg[key + "_pct"]
            if a is not None and b is not None and abs(a - b) >= SUM_PP_THRESHOLD:
                shifts.append((key, a - b))
                p.append("•  %s — %s выручки (%s к среднему за %d мес.)."
                         % (name, _pct(a), _chg(a - b, "п.п."), len(base_ms)))
        if not shifts:
            p.append("Доли переменных затрат стабильны: ни одна не сдвинулась больше "
                     "чем на %s п.п. к среднему за %d мес." % (_num(SUM_PP_THRESHOLD), len(base_ms)))
    blocks.append(("Продажи и маржа", p))

    # ---- постоянные затраты
    p = ["Постоянные затраты — %s: накладные %s, корпоративные %s, финансовые %s."
         % (_rub(-cur["fc"]), _rub(-cur["ovh"]), _rub(-cur["corp"]), _rub(-cur["fin"]))]
    if avg and avg["fc"]:
        p.append("В среднем за %d предыдущих месяца — %s в месяц (%s)."
                 % (len(base_ms), _rub(-avg["fc"]), _chg(_rel(cur["fc"], avg["fc"]))))
    spikes = []
    if base_ms:
        names = {"6": "накладные", "7": "корпоративные", "8": "финансовые", "5": "прочие"}
        for code, sec in (("6", SEC_OVERHEAD), ("7", SEC_CORP), ("8", SEC_FIN), ("5", SEC_OTHER)):
            items = {it for (m, s_, it) in pl_data
                     if s_ == sec and (m == me or m in base_ms)}
            for it in items:
                c = pl_data.get((me, sec, it)) or 0.0
                b = sum(pl_data.get((m, sec, it)) or 0.0 for m in base_ms) / len(base_ms)
                worse = b - c          # > 0 — расход вырос или доход упал
                if worse >= SUM_ITEM_MIN and (not b or worse / abs(b) >= SUM_ITEM_REL):
                    spikes.append((worse, code, names[code], it, c, b))
        spikes.sort(reverse=True)
        spikes = spikes[:SUM_ITEMS_TOP]
    if spikes:
        p.append("Сильнее всего выросли:")
        for worse, code, sname, it, c, b in spikes:
            if code == "5":
                p.append("•  «%s» (прочие): результат %s против %s в среднем — хуже на %s."
                         % (it, _rub(c), _rub(b), _rub(worse)))
            else:
                p.append("•  «%s» (%s): %s против %s в среднем — больше на %s."
                         % (it, sname, _rub(-c), _rub(-b), _rub(worse)))
    elif base_ms:
        p.append("Крупных отклонений по отдельным статьям нет (порог — %s и %d %% "
                 "к среднему за %d мес.)." % (_rub(SUM_ITEM_MIN), SUM_ITEM_REL * 100, len(base_ms)))
    if partial:
        p.append("Месяц неполный: часть постоянных затрат начисляется сразу за весь "
                 "месяц, а выручка — только за %d дней, поэтому результат месяца пока "
                 "выглядит хуже, чем будет по итогу." % elapsed)
    blocks.append(("Постоянные затраты", p))

    # ---- точка безубыточности
    p = []
    if cur["tbu"] is not None:
        s = "Точка безубыточности — %s в месяц" % _rub(cur["tbu"])
        if cur["qty"]:
            s += " (≈ %s шт.)" % _num(cur["tbu"] / (rev / cur["qty"]))
        s += (": при КМД %s столько выручки нужно, чтобы покрыть все постоянные "
              "затраты %s, включая финансовые расходы %s"
              % (_pct(k), _rub(-cur["fc"]), _rub(-cur["fin"])))
        if cur.get("conv"):
            s += " (из них проценты по конвертируемым займам %s)" % _rub(-cur["conv"])
        p.append(s + ".")
        if cur["zfp"] >= 0:
            p.append("Фактическая выручка — %s: запас финансовой прочности %s (%s). "
                     "На столько могут упасть продажи до выхода в убыток."
                     % (_rub(rev), _rub(cur["zfp"]), _pct(cur["zfp_pct"])))
        else:
            p.append("Фактическая выручка — %s: до точки безубыточности не хватает %s "
                     "(%s выручки)." % (_rub(rev), _rub(-cur["zfp"]), _pct(-cur["zfp_pct"])))
        s = ("Каждые 100 000 ₽ новых постоянных затрат в месяц требуют ещё %s выручки"
             % _rub(100000 / k * 100))
        if k > 1:
            s += "; снижение КМД на 1 п.п. поднимает ТБУ на %s" % _rub(
                max(0.0, -cur["fc"]) / (k - 1) * 100 - cur["tbu"])
        p.append(s + ".")
        if avg and avg["tbu"] is not None:
            p.append("В среднем за %d предыдущих месяца ТБУ была %s в месяц (КМД %s, "
                     "постоянные затраты %s)."
                     % (len(base_ms), _rub(avg["tbu"]), _pct(avg["kmd"]), _rub(-avg["fc"])))
    else:
        p.append("Точку безубыточности посчитать нельзя: КМД не положительный.")
    if abs(cur["other"]) >= SUM_ITEM_MIN:
        p.append("Прочие доходы и расходы (раздел 5 P&L) дали %s — в расчёт ТБУ они не "
                 "входят, но влияют на итоговую прибыль." % _rub(cur["other"]))
    blocks.append(("Точка безубыточности с учётом всей финансовой нагрузки", p))

    # ---- точка безубыточности без процентов по конвертируемым займам
    p = []
    if cur["tbu_ex"] is None:
        p.append("Точку безубыточности посчитать нельзя: КМД не положительный.")
    elif not cur.get("conv"):
        p.append("В %s процентов по договорам конвертируемого займа не начислено, "
                 "поэтому точка безубыточности та же, что в предыдущем разделе: %s."
                 % (Mp, _rub(cur["tbu_ex"])))
    else:
        s = ("Если не считать проценты по договорам конвертируемого займа (%s), "
             "постоянные затраты составят %s, и при том же КМД %s точка "
             "безубыточности — %s в месяц"
             % (_rub(-cur["conv"]), _rub(-(cur["fc"] - cur["conv"])), _pct(k),
                _rub(cur["tbu_ex"])))
        if cur["qty"]:
            s += " (≈ %s шт.)" % _num(cur["tbu_ex"] / (rev / cur["qty"]))
        p.append(s + ".")
        if cur["zfp_ex"] >= 0:
            p.append("Фактическая выручка — %s: запас финансовой прочности %s (%s), "
                     "месяц выше этой точки безубыточности."
                     % (_rub(rev), _rub(cur["zfp_ex"]), _pct(cur["zfp_ex_pct"])))
        else:
            p.append("Фактическая выручка — %s: до этой точки безубыточности не "
                     "хватает %s (%s выручки)."
                     % (_rub(rev), _rub(-cur["zfp_ex"]), _pct(-cur["zfp_ex_pct"])))
        p.append("Проценты по конвертируемым займам поднимают точку безубыточности "
                 "на %s в месяц (строка 6.8 листа «%s»)."
                 % (_rub(cur["tbu"] - cur["tbu_ex"]), BREAKEVEN_SHEET_NAME))
        if avg and avg["tbu_ex"] is not None:
            p.append("В среднем за %d предыдущих месяца эта ТБУ была %s в месяц."
                     % (len(base_ms), _rub(avg["tbu_ex"])))
    blocks.append(("Точка безубыточности без процентов по конвертируемым займам", p))

    # ---- прогноз до конца месяца
    if partial and rev:
        rem = total - elapsed
        day = rev / elapsed
        rf = day * total
        p = ["Прошло %d из %d дней. Средняя выручка — %s в день; если темп "
             "сохранится, за месяц выйдет около %s." % (elapsed, total, _rub(day), _rub(rf))]
        if k is not None and k > 0:
            ebt_f = rf * k / 100 + cur["fc"] + cur["other"]
            p.append("При текущей марже и уже учтённых постоянных затратах за месяц "
                     "ожидается %s до налога (оценка)." % _res(ebt_f))
            gap = cur["tbu"] - rev
            if gap <= 0:
                p.append("Точка безубыточности уже пройдена: каждый следующий рубль "
                         "выручки приносит около %s коп. прибыли." % _num(k))
            elif rem > 0:
                need = gap / rem
                s = ("Чтобы выйти в ноль, в оставшиеся %d дн. нужно продавать по %s в "
                     "день — в %s раза больше текущего темпа."
                     % (rem, _rub(need), _num(need / day, 1)))
                if need / day > 1.5:
                    s += " Это нереалистично: месяц почти наверняка закроется в минусе."
                p.append(s)
        p.append("Прогноз линейный: не учитывает возвраты, которые ещё поступят, и "
                 "расходы, которые начислят в конце месяца.")
        blocks.append(("Прогноз до конца месяца", p))

    # ---- с начала года
    per = ("%s–%s %d" % (MONTHS_NOM[0], M, me.year)) if me.month > 1 else mtitle
    p = ["За %s: выручка %s, маржинальный доход %s (КМД %s), постоянные затраты %s; "
         "до налога — %s, после налога — %s."
         % (per, _rub(ytd["rev"]), _rub(ytd["md"]), _pct(ytd["kmd"]), _rub(-ytd["fc"]),
            _res(ytd["ebt"]), _res(ytd["net"]))]
    if ytd["tbu"] is not None:
        s = ("Точка безубыточности с учётом всей финансовой нагрузки — %s, в среднем %s в месяц; "
             % (_rub(ytd["tbu"]), _rub(ytd["tbu"] / len(ytd_ms))))
        s += ("запас прочности %s." % _pct(ytd["zfp_pct"]) if ytd["zfp"] >= 0
              else "выручки не хватает до неё %s (%s)." % (_rub(-ytd["zfp"]), _pct(-ytd["zfp_pct"])))
        p.append(s)
    if ytd["tbu_ex"] is not None and ytd.get("conv"):
        s = ("Без процентов по конвертируемым займам (%s за период) точка "
             "безубыточности — %s, в среднем %s в месяц; "
             % (_rub(-ytd["conv"]), _rub(ytd["tbu_ex"]), _rub(ytd["tbu_ex"] / len(ytd_ms))))
        s += ("запас прочности %s." % _pct(ytd["zfp_ex_pct"]) if ytd["zfp_ex"] >= 0
              else "выручки не хватает до неё %s (%s)."
              % (_rub(-ytd["zfp_ex"]), _pct(-ytd["zfp_ex_pct"])))
        p.append(s)
    below = [MONTHS_NOM[m.month - 1] for m, d in per_month
             if d["rev"] and (d["zfp"] is None or d["zfp"] < 0)]
    n_ok = sum(1 for m, d in per_month if d["rev"]) - len(below)
    s = ("Выше точки безубыточности (с учётом всей финансовой нагрузки) — %d из %d мес."
         % (n_ok, n_ok + len(below)))
    if below:
        s += " Ниже: %s." % ", ".join(below)
    p.append(s)
    blocks.append(("С начала года", p))

    # ---- вопросы для обсуждения
    p = []
    for worse, code, sname, it, c, b in spikes[:2]:
        p.append("•  Разобраться, почему «%s» в %s выше обычного на %s: разовое "
                 "начисление или новая постоянная нагрузка." % (it, Mp, _rub(worse)))
    tips = {
        "promo": "Доля рекламы выросла — проверить окупаемость кампаний (ДРР по артикулам).",
        "cogs": "Себестоимость в выручке выросла — проверить закупочные цены и не было "
                "ли продаж со сниженной наценкой.",
        "sell": "Логистика и хранение в выручке выросли — проверить тарифы WB, долю "
                "возвратов и коэффициенты складов.",
        "comm": "Комиссия WB выросла — проверить изменения тарифов по категориям.",
    }
    for key, delta in shifts:
        if delta > 0:
            p.append("•  " + tips[key])
    if cur["zfp"] is not None and cur["zfp"] < 0:
        p.append("•  Решить, что даёт больший эффект: поднять маржу (цены, закупка, "
                 "реклама) или сократить постоянные затраты — см. разделы 7–8 листа "
                 "«%s»." % BREAKEVEN_SHEET_NAME)
    if partial:
        p.append("•  Вернуться к выводам после закрытия месяца — данные предварительные.")
    if not p:
        p.append("Существенных отклонений нет.")
    blocks.append(("Что обсудить", p))

    cols = [("%s %d%s" % (MONTHS_RU[me.month - 1].capitalize(), me.year,
                          "\n%d из %d дн." % (elapsed, total) if partial else ""), cur)]
    if prev:
        cols.append(("%s %d" % (MONTHS_RU[pm.month - 1].capitalize(), pm.year), prev))
    if avg:
        cols.append(("Среднее\nза %d мес." % len(base_ms), avg))
    if ly:
        cols.append(("%s %d" % (MONTHS_RU[lym.month - 1].capitalize(), lym.year), ly))
    cols.append(("С начала\n%d года" % me.year, ytd))

    return {"title": mtitle, "headline": head, "tone": tone, "blocks": blocks,
            "columns": cols, "partial": (elapsed, total) if partial else None}


SUMMARY_KPI = (
    ("rev", "Чистая выручка без НДС", FMT_MLN),
    ("md", "Маржинальный доход", FMT_MLN),
    ("kmd", "КМД*, %", FMT_PCT),
    ("fc", "Постоянные затраты", FMT_MLN),
    ("ebt", "Прибыль (убыток) до налога", FMT_MLN),
    ("net", "Чистая прибыль", FMT_MLN),
    ("tbu", "Точка безубыточности", FMT_MLN),
    ("tbu_ex", "ТБУ без процентов по конв. займам", FMT_MLN),
    ("zfp_ex_pct", "Запас прочности без конв. займов, %", FMT_PCT),
    ("zfp_pct", "Запас финансовой прочности, %", FMT_PCT),
)


def _text_height(text, size=10):
    lines = sum(max(1, -(-len(part) // SUM_WIDTH_CHARS)) for part in text.split("\n"))
    return max(16, lines * (size + 5) + 4)


def build_summary(ws, s, report_date, as_of=None):
    as_of = as_of or report_date
    sheet_setup(ws, landscape=False)
    last = 7                                  # колонки B..G
    extra = "Российский рубль (RUB) · выручка без НДС · дата отчёта: %s" % (
        as_of.strftime("%d.%m.%Y"))
    if s["partial"]:
        extra += " · месяц неполный: %d из %d дней" % s["partial"]
    title_band(ws, "ВЫВОДЫ ЗА %s" % s["title"].upper(),
               "Резюме отчётного месяца для собственника: результат, точка "
               "безубыточности, отклонения и прогноз", last, extra=extra)
    for col, w in zip("ABCDEFGH", (3, 44, 15, 15, 15, 15, 15, 3)):
        ws.column_dimensions[col].width = w

    def merged(r, value, font, fillc=None, border=None, height=None, indent=1):
        ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=last)
        c = write(ws, r, 2, value, font=font, fillc=fillc, border=border)
        c.alignment = Alignment(horizontal="left", vertical="top", wrap_text=True,
                                indent=indent)
        for cc in range(3, last + 1):
            cell = ws.cell(row=r, column=cc)
            if fillc:
                cell.fill = fill(fillc)
            if border:
                cell.border = border
        ws.row_dimensions[r].height = height or _text_height(str(value), font.sz or 10)
        return c

    # ---- главное
    r = 7
    fg, bg = {"good": (FREE, FREE_BG), "bad": (EXPENSE, OCCUPIED_BG),
              "warn": (WARN, WARN_BG)}[s["tone"]]
    write(ws, r, 2, "ГЛАВНОЕ", font=Font(name=FONT, size=8, bold=True, color=fg),
          fillc=bg, align="left", indent=1)
    ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=last)
    for cc in range(3, last + 1):
        ws.cell(row=r, column=cc).fill = fill(bg)
    ws.row_dimensions[r].height = 16
    r += 1
    merged(r, s["headline"], Font(name=FONT, size=11, bold=True, color=TEXT),
           fillc=bg, border=Border(bottom=_side(fg)),
           height=_text_height(s["headline"], 12) + 6)
    r += 2

    # ---- ключевые цифры
    cols = s["columns"]
    f_hdr = Font(name=FONT, size=9, bold=True, color="FFFFFF")
    write(ws, r, 2, "КЛЮЧЕВЫЕ ЦИФРЫ · млн ₽", font=f_hdr, fillc=NAVY, align="left", indent=1)
    for j, (title, _d) in enumerate(cols):
        write(ws, r, 3 + j, title, font=f_hdr, fillc=NAVY_3 if j == 0 else NAVY,
              align="center", wrap=True)
    ws.row_dimensions[r].height = 30
    first = r + 1
    r += 1
    for key, label, fmt in SUMMARY_KPI:
        strong = key in ("ebt", "tbu")
        write(ws, r, 2, label, font=Font(name=FONT, size=10, bold=strong, color=TEXT),
              border=B_BOTTOM, align="left", indent=1)
        for j, (_t, d) in enumerate(cols):
            v = d.get(key)
            color = EXPENSE if (v is not None and v < 0) else INCOME
            write(ws, r, 3 + j, v, fmt=fmt, border=B_BOTTOM, align="right",
                  font=Font(name=FONT, size=10, bold=(j == 0 or strong), color=color),
                  fillc=SURFACE_4 if j == 0 else None)
        ws.row_dimensions[r].height = 18
        r += 1
    apply_zebra(ws, first, r - 1, 2, 2 + len(cols))
    apply_column_dividers(ws, first - 1, r - 1, 2, 2 + len(cols))
    merged(r, "* КМД — коэффициент маржинального дохода: доля выручки, которая остаётся "
              "после переменных затрат. КМД = маржинальный доход / чистая выручка без НДС. "
              "Среднее за месяцы и «с начала года» считаются от сумм периода.",
           Font(name=FONT, size=8, italic=True, color=MUTED))
    r += 2

    # ---- разделы выводов
    f_h = Font(name=FONT, size=10, bold=True, color=TEXT)
    f_p = Font(name=FONT, size=10, color=TEXT_2)
    for num, (head, paras) in enumerate(s["blocks"], 1):
        merged(r, "%02d   %s" % (num, head), f_h, fillc=SURFACE_4, border=B_SECTION,
               height=22)
        ws.cell(row=r, column=2).alignment = Alignment(horizontal="left",
                                                       vertical="center", indent=1)
        r += 1
        for para in paras:
            bullet = para.startswith("•")
            merged(r, para, f_p, indent=3 if bullet else 1)
            r += 1
        r += 1

    merged(r, "Выводы сформированы автоматически по данным пакета; цифры совпадают с "
              "листами P&L и «%s»." % BREAKEVEN_SHEET_NAME,
           Font(name=FONT, size=8, color=MUTED))
    ws.print_area = "A1:%s%d" % (get_column_letter(last + 1), r)
    return r


# =============================================================================
#  08. СБОРКА ПАКЕТА (вызывается и из команды, и из админки)
# =============================================================================

DEFAULT_START_YEAR = 2025


def fetch_pack_data(con, date_from):
    """Готовит витрины в DuckDB и забирает строки P&L и Cash Flow."""
    # Запросы перечитываются с диска на каждый запуск. Без этого правка
    # файла в sql/*.txt не доезжает до уже запущенного сервера: read_query
    # читает файлы один раз, при импорте модуля, и дальше держит их в памяти.
    base = read_sql("base.txt")
    base_stocks = read_sql("base_stocks.txt")
    wb_costs = read_sql("wb_costs.txt")
    dayly_sales_agg = read_sql("dayly_sales_agg.txt")
    margin = read_sql("margin.txt")
    opex = read_sql("opex.txt")
    cf = read_sql("cf.txt")
    treasury = read_sql("treasury.txt")
    deposits = read_sql("deposits.txt")
    pl_notes = read_sql("pl_notes.txt")
    wb_payouts = read_sql("wb_payouts.txt")
    conv_loans = read_sql("conv_loans.txt")

    con.execute(base)
    con.execute(base_stocks)
    con.execute(wb_costs)
    con.execute(dayly_sales_agg)
    con.execute(margin, parameters={"date_from": date_from})
    ensure_pl_src(con)                    # зарплата по начислению из ЗУП, если есть
    con.execute(opex, parameters={"date_from": date_from})
    con.execute(cf, parameters={"date_from": date_from})
    con.execute(conv_loans, parameters={"date_from": date_from,
                                        "title_id": CONV_LOAN_TITLE_ID})
    conv_rows = con.execute("SELECT me, value FROM conv_loans").fetchall()

    pl_rows = con.execute("""
        SELECT me, section, item, value
        FROM month_margins_wb_long
        UNION ALL
        SELECT me, section, item, value
        FROM opex
    """).fetchall()

    cf_rows = con.execute("""
        SELECT
            LAST_DAY(date_from)::date AS me,
            activity,
            operation,
            item,
            subitem,
            COALESCE(NULLIF(TRIM(cp_name), ''), 'Без контрагента') AS cp_name,
            COALESCE(NULLIF(TRIM(contract_name), ''), 'Без договора') AS contract_name,
            SUM(amount) AS amount
        FROM cf
        GROUP BY 1, 2, 3, 4, 5, 6, 7
    """).fetchall()

    unit_rows = con.execute(UNIT_ECONOMICS_SQL,
                            parameters={"date_from": date_from}).fetchall()

    con.execute(treasury, parameters={"date_from": date_from})
    treasury_rows = con.execute("SELECT * FROM treasury").fetchall()

    con.execute(deposits, parameters={"date_from": date_from})
    deposit_row = con.execute("SELECT balance FROM deposits").fetchone()
    deposit_balance = float(deposit_row[0] or 0) if deposit_row else 0.0

    con.execute(pl_notes, parameters={"date_from": date_from})
    note_rows = con.execute("SELECT * FROM pl_notes").fetchall()

    con.execute(wb_payouts, parameters={"date_from": date_from})
    payout_rows = con.execute("SELECT * FROM wb_payouts").fetchall()

    return (pl_rows, cf_rows, unit_rows, treasury_rows,
        deposit_balance, note_rows, payout_rows, conv_rows)


# Данные листа «Юнит-экономика». Считаются по тем же витринам, что и P&L,
# но с двумя отличиями, которых в P&L нет:
#   1) количество продаж и возвратов раздельно (в P&L есть только нетто);
#   2) удержания площадки приведены БЕЗ НДС — маржинальность сопоставляется
#      с выручкой без НДС (в P&L те же статьи показаны с НДС, суммой
#      фактического удержания). Ставка НДС берётся построчно из витрины
#      продаж, для строк без ставки принимается 20 %.
UNIT_ECONOMICS_SQL = """
    WITH qty AS (
        SELECT
            LAST_DAY(date_from::DATE) AS me,
            SUM(CASE WHEN cr_rev > 0 THEN 1 ELSE 0 END) AS sales_qty,
            SUM(CASE WHEN cr_rev < 0 THEN 1 ELSE 0 END) AS returns_qty
        FROM base
        WHERE cr_rev <> 0
          AND date_from::DATE <= $date_from
        GROUP BY 1
    ),

    sales AS (
        SELECT
            me,
            SUM(amount) AS amount,
            SUM(retail_amount) AS retail_amount,
            SUM(amount_vatless) AS amount_vatless,
            SUM(cogs_man) AS cogs_man,
            SUM(net_comission) AS net_comission
        FROM pl_sales
        WHERE date_from <= $date_from
        GROUP BY me
    ),

    wb AS (
        SELECT
            me,
            SUM(
                CASE WHEN account NOT IN ('Other income / loss', 'WB Deduction')
                     THEN (dt - cr) / (100 + COALESCE(vat_rate, 20)) * 100
                     ELSE 0 END
            ) / 100 AS wb_costs_vatless,
            SUM(
                CASE WHEN account = 'WB Deduction'
                     THEN (dt - cr) / (100 + COALESCE(vat_rate, 20)) * 100
                     ELSE 0 END
            ) / 100 AS promo_vatless
        FROM wb_costs
        WHERE date_from::DATE <= $date_from
        GROUP BY me
    )

    SELECT
        s.me,
        COALESCE(q.sales_qty, 0),
        COALESCE(q.returns_qty, 0),
        s.amount,
        s.retail_amount,
        s.amount_vatless,
        s.cogs_man,
        s.net_comission,
        COALESCE(w.wb_costs_vatless, 0),
        COALESCE(w.promo_vatless, 0)
    FROM sales s
    LEFT JOIN qty q ON q.me = s.me
    LEFT JOIN wb  w ON w.me = s.me
    ORDER BY s.me
"""


def section_sum(pl_data, me, section):
    return sum(v for (m, s, _i), v in pl_data.items()
               if m == me and s == section and v is not None)


def ebitda_of(pl_data, me):
    g = pl_data.get((me, SEC_REVENUE, "1.11. Маржа после комиссии")) or 0.0
    for sec in (SEC_SELLING, SEC_PROMO, SEC_OTHER, SEC_OVERHEAD, SEC_CORP):
        g += section_sum(pl_data, me, sec)
    return g


def net_profit_of(pl_data, tax_by_month, me):
    v = ebitda_of(pl_data, me) + section_sum(pl_data, me, SEC_FIN)
    return v + tax_by_month.get(me, 0.0)


def month_columns(start_year, report_date):
    """Непрерывный ряд месяцев с января start_year по отчётный месяц."""
    months = []
    y, m = start_year, 1
    while True:
        me = last_day(date(y, m, 1))
        if me > report_date:
            break
        months.append(me)
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return months


def build_management_pack(date_from, start_year=DEFAULT_START_YEAR, out_path=None):
    """
    Собирает управленческий пакет (Титул + P&L + Cash Flow + пояснения)
    и сохраняет xlsx. Возвращает (путь, статистика).

    Вызывается и management-командой `manage.py mp`, и view админки
    (ts/admin_exports.export_management_pack) — логика одна и та же,
    чтобы файл из браузера и из консоли был идентичным.
    """
    if isinstance(date_from, str):
        date_from = date.fromisoformat(date_from)

    with get_duckdb_conn_with_opt(ro=True) as con:
        (pl_rows, cf_rows, unit_rows, treasury_rows,
        deposit_balance, note_rows, payout_rows,
        conv_rows) = fetch_pack_data(con, date_from)

    if not pl_rows:
        raise ValueError("Запросы P&L не вернули данных.")

    pl_data = {}
    for me, section, item, value in pl_rows:
        me = me if isinstance(me, date) else date.fromisoformat(str(me))
        pl_data[(me, section, item)] = (round(float(value), 2)
                                        if value is not None else None)

    cf_data = {}
    for me, act, op, itm, sub, cp, contract, amount in cf_rows:
        me = me if isinstance(me, date) else date.fromisoformat(str(me))
        key = (me, act or "", op or "", itm or "", sub or "",
               cp or "", contract or "")
        cf_data[key] = round(cf_data.get(key, 0.0) + float(amount or 0), 2)

    conv_by_month = {}
    for me, value in conv_rows:
        me = me if isinstance(me, date) else date.fromisoformat(str(me))
        conv_by_month[me] = round(float(value or 0), 2)

    unit_data = {}
    for row in unit_rows:
        me = row[0] if isinstance(row[0], date) else date.fromisoformat(str(row[0]))
        unit_data[me] = {
            U_SALES_QTY: float(row[1] or 0),
            U_RETURNS_QTY: float(row[2] or 0),
            # возвраты по FIFO сторнируют исходную продажу, поэтому на лист
            # выводится только чистое количество
            U_NET_QTY: float(row[1] or 0) - float(row[2] or 0),
            U_AMOUNT: float(row[3] or 0),
            U_RETAIL: float(row[4] or 0),
            U_VATLESS: float(row[5] or 0),
            U_COGS: float(row[6] or 0),
            U_COMISSION: float(row[7] or 0),
            U_WB_COSTS: float(row[8] or 0),
            U_PROMO: float(row[9] or 0),
        }

    report_date = last_day(date_from)
    if report_date.year < start_year:
        raise ValueError(
            "Отчётная дата %s раньше начала периода (%d год)."
            % (report_date, start_year))

    months = month_columns(start_year, report_date)

    # налог на прибыль из Cash Flow
    tax_by_month = defaultdict(float)
    for key, v in cf_data.items():
        if key[4] == TAX_SUBITEM:
            tax_by_month[key[0]] += v

    # чистая прибыль для листа юнит-экономики — тот же каскад, что в P&L,
    # чтобы рентабельность по чистой прибыли сходилась между листами
    for me in months:
        unit_data.setdefault(me, {})[U_NET_PROFIT] = net_profit_of(
            pl_data, tax_by_month, me)

    # остаток ДС на начало первого показанного месяца
    first = months[0]
    opening = round(sum(v for k, v in cf_data.items() if k[0] < first), 2)

    # ------------------------------------------------------------- excel
    # книга собирается с нуля: сводных таблиц и листов с сырыми строками
    # в пакете больше нет, эти данные выгружаются отдельными csv из админки
    wb = Workbook()
    ws_cover = wb.active
    ws_cover.title = TOC_SHEET_NAME
    ws_sum = wb.create_sheet(SUMMARY_SHEET_NAME)
    ws_pl = wb.create_sheet("P&L")
    ws_notes_pl = wb.create_sheet(NOTES_SHEET_NAME)
    ws_unit = wb.create_sheet("Юнит-экономика")
    ws_be = wb.create_sheet(BREAKEVEN_SHEET_NAME)
    ws_cf = wb.create_sheet("Cash Flow")
    ws_cash = wb.create_sheet("Остатки ДС")
    ws_payouts = wb.create_sheet(PAYOUTS_SHEET_NAME)
    ws_npl = wb.create_sheet("Пояснения P&L")
    ws_nunit = wb.create_sheet("Пояснения Юнит-экономика")
    ws_nbe = wb.create_sheet(BE_NOTES_SHEET_NAME)
    ws_ncf = wb.create_sheet("Пояснения Cash Flow")

    note_anchors = build_pl_notes(ws_notes_pl, note_rows, months, report_date,
                                  as_of=date_from)
    pl_rowmap = {}
    build_pl(ws_pl, pl_data, tax_by_month, months, report_date,
             as_of=date_from, note_anchors=note_anchors, rowmap_out=pl_rowmap)
    build_unit_economics(ws_unit, unit_data, months, report_date, as_of=date_from)
    build_breakeven(ws_be, pl_rowmap, months, report_date, as_of=date_from,
                    conv_by_month=conv_by_month)
    build_summary(ws_sum, month_summary(pl_data, tax_by_month, months, date_from,
                                        conv_by_month=conv_by_month),
                  report_date, as_of=date_from)
    build_cf(ws_cf, cf_data, months, opening, report_date, as_of=date_from)

    bank_rows, wb_row = split_treasury(treasury_rows)

    build_treasury(
    ws_cash,
    bank_rows,
    wb_row,
    report_date,
    as_of=date_from,
    deposit_balance=deposit_balance,
)

    outs, ins = split_payouts(payout_rows)
    # сумма берётся из баланса площадки (там она верная), а дата — та,
    # которой деньги пришли на расчётный счёт; выводы без поступления
    # на лист не попадают, они и есть деньги в пути
    payout_receipts = [
        {"dt": p["in_dt"], "amount": p["out_amount"], "cp_name": p["cp_name"]}
        for p in match_wb_payouts(outs, ins) if p["in_dt"] is not None
    ]
    build_wb_payouts(ws_payouts, payout_receipts,
                     round(sum(x["amount"] for x in outs), 2),
                     report_date, as_of=date_from)

    build_notes(ws_npl, "ПОЯСНЕНИЯ К ОТЧЁТУ О ПРИБЫЛЯХ И УБЫТКАХ",
                "Методика расчёта разделов, промежуточных итогов и "
                "показателей рентабельности", NOTES_PL + [payroll_note()])
    build_notes(ws_nunit, "ПОЯСНЕНИЯ К ЮНИТ-ЭКОНОМИКЕ",
                "Что показывает каждый показатель, как считается и почему "
                "не сходится с кассой и отчётом WB", NOTES_UNIT)
    build_notes(ws_nbe, "ПОЯСНЕНИЯ К РАСЧЁТУ ТОЧКИ БЕЗУБЫТОЧНОСТИ",
                "Методика, классификация затрат, расчёт по месяцам и за год, "
                "сценарии роста затрат и пример", NOTES_BE)
    build_notes(ws_ncf, "ПОЯСНЕНИЯ К ОТЧЁТУ О ДВИЖЕНИИ ДЕНЕЖНЫХ СРЕДСТВ",
                "Структура денежных потоков, остатки и сверка с P&L", NOTES_CF)

    last = months[-1]
    rev = pl_data.get((last, SEC_REVENUE, "1.4 Продажи без НДС")) or 0.0
    kpi = {
        "revenue": rev,
        "ebitda": ebitda_of(pl_data, last),
        "net": net_profit_of(pl_data, tax_by_month, last),
        "cash": opening + sum(v for k, v in cf_data.items()
                              if first <= k[0] <= last),
    }

    if out_path:
        path = Path(out_path).expanduser().resolve()
    else:
        path = (Path(settings.BASE_DIR) / "reports" /
                ("manpack_%s.xlsx" % report_date.isoformat()))
    path.parent.mkdir(parents=True, exist_ok=True)

    contents = [
        (SUMMARY_SHEET_NAME, "Главное за отчётный месяц простым языком: результат, "
                             "точка безубыточности, отклонения, прогноз"),
        ("P&L", "Отчёт о прибылях и убытках с промежуточными итогами, "
                "EBITDA, налогом и рентабельностью"),
        (NOTES_SHEET_NAME, "Расшифровка каждой строки P&L: статья, "
                           "контрагент, договор"),
        ("Юнит-экономика", "Количества, цены и себестоимость на единицу, "
                           "три уровня маржинальности и рентабельность"),
        (BREAKEVEN_SHEET_NAME, "Точка безубыточности (ТБУ) по месяцам и за год, "
                               "запас прочности, сценарий роста затрат "
                               "и чувствительность к марже"),
        ("Cash Flow", "Отчёт о движении денежных средств прямым методом "
                      "по видам деятельности"),
        ("Остатки ДС", "Банковские счета, деньги в пути, баланс WB "
                       "и депозиты с расшифровкой по счетам"),
        (PAYOUTS_SHEET_NAME, "Поступления от площадки на расчётный счёт: "
                             "даты, суммы и количество по месяцам"),
        ("Пояснения P&L", "Методика расчёта каждого раздела и промежуточного итога"),
        ("Пояснения Юнит-экономика", "Как считается каждый показатель "
                                     "и почему он не равен кассе"),
        (BE_NOTES_SHEET_NAME, "Методика ТБУ: какие затраты переменные и "
                              "постоянные, помесячный и годовой расчёт, пример"),
        ("Пояснения Cash Flow", "Структура потоков, остатки и связь с P&L"),
    ]
    contents = [c for c in contents if c[0] in wb.sheetnames]
    build_cover(ws_cover, report_date, months, kpi, path.name,
                contents=contents, as_of=date_from)

    # Ни один лист не должен быть «выделен» кроме первого: иначе Excel
    # открывает книгу в режиме группового редактирования, и правка на одном
    # листе молча уходит сразу на все выделенные.
    for sheet in wb.worksheets:
        for view in sheet.views.sheetView:
            view.tabSelected = False
    wb.active = 0

    # порядок листов: отчёты, затем пояснения
    order = [TOC_SHEET_NAME, SUMMARY_SHEET_NAME, "P&L", NOTES_SHEET_NAME, "Юнит-экономика",
             BREAKEVEN_SHEET_NAME, "Cash Flow", "Остатки ДС", PAYOUTS_SHEET_NAME,
             "Пояснения P&L", "Пояснения Юнит-экономика", BE_NOTES_SHEET_NAME,
             "Пояснения Cash Flow"]
    ordered = [wb[n] for n in order if n in wb.sheetnames]
    ordered += [ws for ws in wb.worksheets if ws not in ordered]
    wb._sheets = ordered
    wb.save(path)

    stats = {
        "report_date": report_date,
        "months": len(months),
        "first_month": month_label(months[0]),
        "last_month": month_label(months[-1]),
        "pl_rows": len(pl_data),
        "cf_rows": len(cf_data),
    }
    return path, stats


# =============================================================================
#  09. КОМАНДА
# =============================================================================

# =============================================================================
#  09. ВЫГРУЗКА ВИТРИН В CSV
#
#      Сводных таблиц в пакете больше нет. Вместо них из админки выгружаются
#      те же витрины, на которых они строились, — и сводную можно собрать
#      у себя как удобно. Разделитель — вертикальная черта, кодировка
#      utf-8 с BOM (Excel открывает такой файл без вопросов).
# =============================================================================

CSV_DELIMITER = "|"

CSV_SOURCES = {
    "cf": (
        "cash_flow",
        "SELECT * FROM pg.cf_to_csv WHERE date_from <= $date_from "
        "ORDER BY date_from",
    ),
    "pl": (
        "pl",
        "SELECT * FROM pg.pl_for_csv WHERE date_from <= $date_from "
        "ORDER BY date_from",
    ),
}


def _csv_value(v):
    """Приводит значение к одной строке, пригодной для файла с «|».

    В описаниях проводок встречаются переносы строк, сама вертикальная
    черта и кавычки. Любой из этих символов разрывает запись при импорте:
    остаток строки уезжает в следующую и текст оказывается в колонке
    с датой. Поэтому чистим их здесь, до записи.
    """
    if v is None:
        return ""
    if not isinstance(v, str):
        return v
    text = v.replace("\r\n", " ").replace("\n", " ").replace("\r", " ")
    text = text.replace(CSV_DELIMITER, "/").replace('"', "'")
    return " ".join(text.split())


def export_raw_csv(kind, date_from, out_path=None):
    """Выгружает витрину «cf» или «pl» в csv. Возвращает (путь, число строк)."""
    if kind not in CSV_SOURCES:
        raise ValueError("Неизвестная выгрузка: %s" % kind)

    if isinstance(date_from, str):
        date_from = date.fromisoformat(date_from)

    prefix, sql = CSV_SOURCES[kind]

    with get_duckdb_conn_with_opt(ro=True) as con:
        cur = con.execute(sql, parameters={"date_from": date_from})
        columns = [d[0] for d in cur.description]
        rows = cur.fetchall()

    path = Path(out_path) if out_path else Path(
        "%s_%s.csv" % (prefix, date_from.isoformat()))
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.writer(fh, delimiter=CSV_DELIMITER,
                            quoting=csv.QUOTE_MINIMAL, lineterminator="\r\n")
        writer.writerow(columns)
        for row in rows:
            writer.writerow([_csv_value(v) for v in row])

    return path, len(rows)


# =============================================================================
#  10. КНИГА СО СВОДНЫМИ (нативные сводные таблицы Excel)
#
#      Отдельный файл: два листа со сводными — по движению денежных средств
#      и по P&L — и два листа-источника с сырыми строками витрин.
#
#      Команда только наполняет источники и раздвигает диапазоны «умных
#      таблиц»; сами сводные Excel пересчитывает при открытии файла
#      (refreshOnLoad). Макросов и VBA нет.
#
#      Раскладка задана в скелете assets/pivots_skeleton.xlsx и собирается
#      скриптом assets/build_pivots_skeleton.py — руками в Excel скелет
#      править нельзя, Excel переписывает его по-своему.
# =============================================================================

PIVOTS_SKELETON = Path(__file__).resolve().parent / "assets" / "pivots_skeleton.xlsx"

PIVOT_SOURCES = {
    "raw_cf": "SELECT * FROM pg.cf_to_csv WHERE date_from <= $date_from "
              "ORDER BY date_from",
}

# Сверка сводной P&L с листом P&L: (месяц, раздел) -> сумма.
PIVOT_PL_CHECK_SQL = """
    WITH pl AS (
        SELECT me, TRIM(section) AS section,
               CASE WHEN item = '1.6. Себестоимость' THEN -value ELSE value END AS value
        FROM month_margins_wb_long
        WHERE item IN ('1.4 Продажи без НДС', '1.6. Себестоимость', '1.9. Комиссия WB')
        UNION ALL
        SELECT me, section, value FROM opex
        UNION ALL
        SELECT LAST_DAY(date_from)::DATE, '9. НАЛОГ НА ПРИБЫЛЬ', amount
        FROM cf WHERE subitem = '125200 Налог на прибыль'
    ),
    a AS (SELECT me, section, SUM(value) AS v FROM pl GROUP BY 1, 2),
    b AS (SELECT LAST_DAY(date_from)::DATE AS me, parent_account_name AS section,
                 SUM(amount) AS v
          FROM pivot_pl GROUP BY 1, 2)
    SELECT COALESCE(a.me, b.me), COALESCE(a.section, b.section),
           COALESCE(a.v, 0), COALESCE(b.v, 0)
    FROM a FULL JOIN b ON a.me = b.me AND a.section = b.section
    WHERE ABS(COALESCE(a.v, 0) - COALESCE(b.v, 0)) > 1
    ORDER BY 1, 2
"""


def pivot_pl_source(con, date_from):
    """Источник сводной P&L по правилам листа P&L управленческого пакета.

    Возвращает (колонки, строки, расхождения со сверкой). Расхождения —
    список (месяц, раздел, P&L, сводная), пустой при полном совпадении.
    """
    params = {"date_from": date_from}
    con.execute(read_sql("base.txt"))
    con.execute(read_sql("base_stocks.txt"))
    con.execute(read_sql("wb_costs.txt"))
    con.execute(read_sql("dayly_sales_agg.txt"))
    con.execute(read_sql("cf.txt"), parameters=params)
    ensure_pl_src(con)
    con.execute(read_sql("pivot_pl.txt"), parameters=params)

    cur = con.execute("SELECT * FROM pivot_pl ORDER BY date_from")
    columns = [d[0] for d in cur.description]
    rows = cur.fetchall()

    con.execute(read_sql("margin.txt"), parameters=params)
    con.execute(read_sql("opex.txt"), parameters=params)
    mismatches = con.execute(PIVOT_PL_CHECK_SQL).fetchall()
    return columns, rows, mismatches


def _pivot_cell(value):
    """Приводит значение из витрины к типу, который принимает openpyxl."""
    if value is None or isinstance(value, (int, float, str, bool)):
        return value
    if isinstance(value, dt.datetime):
        return value.replace(tzinfo=None)
    if isinstance(value, date):
        return value
    try:
        return float(value)
    except (TypeError, ValueError):
        return str(value)


def fill_pivot_source(ws, table_name, columns, rows):
    """Наполняет лист-источник и раздвигает диапазон «умной таблицы».

    Колонки раскладываются по заголовкам, которые уже лежат в скелете:
    поля сводной привязаны к позициям, и менять порядок нельзя, даже
    если витрина однажды вернёт колонки в другом порядке.
    """
    header = [ws.cell(row=1, column=i).value
              for i in range(1, ws.max_column + 1)]
    header = [h for h in header if h]
    if not header:
        header = list(columns)

    order = []
    for name in header:
        order.append(columns.index(name) if name in columns else None)

    if ws.max_row > 1:
        ws.delete_rows(2, ws.max_row)

    for i, row in enumerate(rows, start=2):
        for j, src in enumerate(order, start=1):
            if src is None:
                continue
            ws.cell(row=i, column=j, value=_pivot_cell(row[src]))

    last_row = max(2, 1 + len(rows))
    ref = "A1:%s%d" % (get_column_letter(len(header)), last_row)

    table = ws.tables.get(table_name)
    if table is not None:
        table.ref = ref
        if table.autoFilter is not None:
            table.autoFilter.ref = ref

    return len(rows)


PIVOT_LAYOUT = {
    "xl/pivotTables/pivotTable1.xml": {
        "cache": "xl/pivotCache/pivotCacheDefinition1.xml",
        "source": "raw_cf",
        "rows": ["activity", "operation", "item", "subitem",
                 "cp_name", "contract_name"],
    },
    "xl/pivotTables/pivotTable2.xml": {
        "cache": "xl/pivotCache/pivotCacheDefinition2.xml",
        "source": "raw_pl",
        "rows": ["parent_account_name", "account_name", "cost_item_group",
                 "cost_item", "cp_name", "contract_name"],
        # раскрыты только разделы P&L; строки P&L свёрнуты под «+»
        "open_levels": 1,
        "row_stripes": False,
    },
}

# сколько верхних уровней открыто при открытии файла
PIVOT_OPEN_LEVELS = 2


def sync_pivot_items(path, data):
    """Переписывает справочники значений сводных под фактические данные.

    Зачем. Уровень сводной свёрнут, если у КАЖДОГО его элемента стоит
    признак «не раскрывать». Признак живёт у конкретного значения, а не у
    поля целиком, поэтому значение, которого не было в справочнике,
    Excel после обновления показывает раскрытым. Появилась новая статья
    или контрагент — и ветка открывается сама.

    Поэтому перед выдачей файла складываем в справочники ровно те
    значения, которые лежат в источнике, и всем уровням ниже
    PIVOT_OPEN_LEVELS проставляем «свёрнуто».
    """
    import xml.etree.ElementTree as ET
    import shutil
    import tempfile
    import zipfile

    ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    ET.register_namespace("", ns)
    tag = lambda name: "{%s}%s" % (ns, name)

    def distinct(columns, rows, name):
        if name not in columns:
            return [], False
        i = columns.index(name)
        seen, blank = set(), False
        for row in rows:
            value = row[i]
            text = "" if value is None else str(value).strip()
            if text:
                seen.add(text)
            else:
                blank = True
        return sorted(seen), blank

    src = zipfile.ZipFile(path)
    parts = {}

    for table_part, cfg in PIVOT_LAYOUT.items():
        if table_part not in src.namelist() or cfg["source"] not in data:
            continue

        columns, rows = data[cfg["source"]]
        cache = ET.fromstring(src.read(cfg["cache"]))
        table = ET.fromstring(src.read(table_part))

        cache_fields = list(cache.find(tag("cacheFields")))
        pivot_fields = list(table.find(tag("pivotFields")))
        names = [f.get("name") for f in cache_fields]

        for level, name in enumerate(cfg["rows"]):
            if name not in names:
                continue
            index = names.index(name)
            values, blank = distinct(columns, rows, name)
            if not values and not blank:
                continue

            collapsed = level >= cfg.get("open_levels", PIVOT_OPEN_LEVELS)

            shared = ET.SubElement(cache_fields[index], tag("sharedItems"))
            cache_fields[index].remove(shared)
            shared = ET.Element(tag("sharedItems"))
            shared.set("count", str(len(values) + (1 if blank else 0)))
            if blank:
                shared.set("containsBlank", "1")
            for value in values:
                ET.SubElement(shared, tag("s")).set("v", value)
            if blank:
                ET.SubElement(shared, tag("m"))

            old = cache_fields[index].find(tag("sharedItems"))
            if old is not None:
                cache_fields[index].remove(old)
            cache_fields[index].insert(0, shared)

            items = ET.Element(tag("items"))
            total = len(values) + (1 if blank else 0)
            items.set("count", str(total + 1))
            for i in range(total):
                item = ET.SubElement(items, tag("item"))
                item.set("x", str(i))
                if collapsed:
                    item.set("sd", "0")
            default = ET.SubElement(items, tag("item"))
            default.set("t", "default")
            if collapsed:
                default.set("sd", "0")

            old = pivot_fields[index].find(tag("items"))
            if old is not None:
                pivot_fields[index].remove(old)
            pivot_fields[index].append(items)

        if "row_stripes" in cfg:
            style = table.find(tag("pivotTableStyleInfo"))
            if style is not None:
                style.set("showRowStripes", "1" if cfg["row_stripes"] else "0")

        parts[cfg["cache"]] = ET.tostring(cache, encoding="UTF-8",
                                          xml_declaration=True)
        parts[table_part] = ET.tostring(table, encoding="UTF-8",
                                        xml_declaration=True)

    if not parts:
        src.close()
        return 0

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
    tmp.close()

    out = zipfile.ZipFile(tmp.name, "w", zipfile.ZIP_DEFLATED)
    for info in src.infolist():
        out.writestr(info, parts.get(info.filename) or src.read(info.filename))
    out.close()
    src.close()

    shutil.move(tmp.name, path)
    return len(parts) // 2


PIVOT_NUMBER_FORMAT = ('<numFmt numFmtId="171" '
                       'formatCode="#,##0;(#,##0);&quot;–&quot;"/>')


def restore_pivot_number_format(path):
    """Возвращает в файл формат чисел сводных.

    Формат 171 («в скобках, разделители тысяч») нужен только сводным, ни
    одна обычная ячейка на него не ссылается — и openpyxl при сохранении
    выбрасывает его из styles.xml как неиспользуемый. Тогда Excel показывает
    суммы как есть, без разделителей и со знаком минус. Возвращаем запись
    прямо в сохранённый файл.
    """
    import re
    import shutil
    import tempfile
    import zipfile

    src = zipfile.ZipFile(path)
    styles = src.read("xl/styles.xml").decode("utf-8")

    if 'numFmtId="171"' in styles:
        src.close()
        return False

    if "<numFmts" in styles:
        styles = re.sub(
            r'<numFmts count="(\d+)">',
            lambda m: ('<numFmts count="%d">' % (int(m.group(1)) + 1)
                       + PIVOT_NUMBER_FORMAT),
            styles, count=1)
    else:
        styles = styles.replace(
            "<fonts",
            '<numFmts count="1">%s</numFmts><fonts' % PIVOT_NUMBER_FORMAT, 1)

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
    tmp.close()

    out = zipfile.ZipFile(tmp.name, "w", zipfile.ZIP_DEFLATED)
    for info in src.infolist():
        data = (styles.encode("utf-8") if info.filename == "xl/styles.xml"
                else src.read(info.filename))
        out.writestr(info, data)
    out.close()
    src.close()

    shutil.move(tmp.name, path)
    return True


PIVOT_STYLE_NAME = "ManpackPivotGreen"
PIVOT_GRID = "FFDDDDDD"        # светло-серая сетка
PIVOT_FONT = "Roboto"


def _pivot_dxf(bold=False, color=TEXT, fill_rgb=None, border=None):
    font = '<font>%s<sz val="10"/><color rgb="FF%s"/><name val="%s"/></font>' % (
        "<b/>" if bold else "", color, PIVOT_FONT)
    out = "<dxf>" + font
    if fill_rgb:
        out += ('<fill><patternFill patternType="solid"><fgColor rgb="FF%s"/>'
                '<bgColor rgb="FF%s"/></patternFill></fill>' % (fill_rgb, fill_rgb))
    if border:
        out += "<border>%s</border>" % "".join(
            '<%s style="%s"><color rgb="%s"/></%s>' % (side, st, col, side)
            for side, st, col in border)
    return out + "</dxf>"


def polish_pivot_style(path):
    """Оформление сводных: сетка, выделение разделов, итоговая строка.

    Переписывает табличный стиль сводных прямо в сохранённом файле.
    Строки разделов при промежуточных итогах «вверху» Excel оформляет
    элементами Row Subheading, поэтому заданы и они, и Subtotal Row.
    """
    import re
    import shutil
    import tempfile
    import zipfile

    grid = [("left", "thin", PIVOT_GRID), ("right", "thin", PIVOT_GRID),
            ("top", "thin", PIVOT_GRID), ("bottom", "thin", PIVOT_GRID),
            ("vertical", "thin", PIVOT_GRID), ("horizontal", "thin", PIVOT_GRID)]
    elements = [
        ("wholeTable", None, _pivot_dxf(border=grid)),
        ("headerRow", None, _pivot_dxf(True, "FFFFFF", NAVY, [
            ("left", "thin", "FF" + NAVY_2), ("right", "thin", "FF" + NAVY_2),
            ("vertical", "thin", "FF" + NAVY_2)])),
        ("totalRow", None, _pivot_dxf(True, TEXT, SURFACE_4, [
            ("top", "medium", "FF" + NAVY), ("bottom", "double", "FF" + NAVY)])),
        ("firstRowSubheading", 1, _pivot_dxf(True, NAVY_3, "D5E8E0", [
            ("top", "thin", "FF" + NAVY_2)])),
        ("firstSubtotalRow", 1, _pivot_dxf(True, NAVY_3, "D5E8E0", [
            ("top", "thin", "FF" + NAVY_2)])),
        ("secondRowSubheading", 1, _pivot_dxf(False, TEXT, "F3F8F6")),
        ("secondSubtotalRow", 1, _pivot_dxf(False, TEXT, "F3F8F6")),
        ("firstRowStripe", 1, _pivot_dxf(fill_rgb="FAFAFA")),
    ]

    src = zipfile.ZipFile(path)
    styles = src.read("xl/styles.xml").decode("utf-8")

    m = re.search(r'<dxfs count="(\d+)"\s*/>|<dxfs count="(\d+)">(.*?)</dxfs>',
                  styles, re.S)
    if m:
        base = int(m.group(1) or m.group(2))
        body = (m.group(3) or "") + "".join(e[2] for e in elements)
        styles = (styles[:m.start()]
                  + '<dxfs count="%d">%s</dxfs>' % (base + len(elements), body)
                  + styles[m.end():])
    else:
        base = 0
        styles = styles.replace(
            "<tableStyles", '<dxfs count="%d">%s</dxfs><tableStyles'
            % (len(elements), "".join(e[2] for e in elements)), 1)

    items = "".join(
        '<tableStyleElement type="%s"%s dxfId="%d"/>'
        % (kind, ' size="%d"' % size if size else "", base + i)
        for i, (kind, size, _x) in enumerate(elements))
    block = ('<tableStyles count="1" defaultTableStyle="TableStyleMedium2"'
             ' defaultPivotStyle="%s"><tableStyle name="%s" pivot="1"'
             ' count="%d">%s</tableStyle></tableStyles>'
             % (PIVOT_STYLE_NAME, PIVOT_STYLE_NAME, len(elements), items))
    if "<tableStyles" in styles:
        styles = re.sub(r'<tableStyles.*?</tableStyles>|<tableStyles[^>]*/>',
                        block, styles, count=1, flags=re.S)
    else:
        styles = styles.replace("</styleSheet>", block + "</styleSheet>", 1)

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
    tmp.close()
    out = zipfile.ZipFile(tmp.name, "w", zipfile.ZIP_DEFLATED)
    for info in src.infolist():
        data = (styles.encode("utf-8") if info.filename == "xl/styles.xml"
                else src.read(info.filename))
        out.writestr(info, data)
    out.close()
    src.close()
    shutil.move(tmp.name, path)
    return True


def build_pivots_workbook(date_from, out_path=None):
    """Собирает книгу со сводными на отчётную дату."""
    if isinstance(date_from, str):
        date_from = date.fromisoformat(date_from)

    if not PIVOTS_SKELETON.exists():
        raise ValueError(
            "Не найден скелет сводных: %s. Соберите его скриптом "
            "assets/build_pivots_skeleton.py" % PIVOTS_SKELETON.name)

    data = {}
    with get_duckdb_conn_with_opt(ro=True) as con:
        for name, sql in PIVOT_SOURCES.items():
            cur = con.execute(sql, parameters={"date_from": date_from})
            data[name] = ([d[0] for d in cur.description], cur.fetchall())
        pl_columns, pl_rows, mismatches = pivot_pl_source(con, date_from)
        data["raw_pl"] = (pl_columns, pl_rows)

    wb = load_workbook(PIVOTS_SKELETON)

    counts = {}
    for name, (columns, rows) in data.items():
        if name in wb.sheetnames:
            counts[name] = fill_pivot_source(wb[name], name, columns, rows)

    # сводные обновятся сами при открытии файла
    for sheet in wb.worksheets:
        for pivot in getattr(sheet, "_pivots", []):
            pivot.cache.refreshOnLoad = True
        for view in sheet.views.sheetView:
            view.tabSelected = False
    wb.active = 0

    # порядок листов: сначала обе сводные, источники — в конец
    order = ["Сводная CF", "Сводная P&L", "raw_cf", "raw_pl"]
    ordered = [wb[n] for n in order if n in wb.sheetnames]
    ordered += [ws for ws in wb.worksheets if ws not in ordered]
    wb._sheets = ordered

    path = Path(out_path) if out_path else Path(
        "pivots_%s.xlsx" % date_from.isoformat())
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)

    restore_pivot_number_format(path)
    sync_pivot_items(path, data)
    polish_pivot_style(path)

    if mismatches:
        print("Сводная P&L не сходится с P&L по %d позициям (месяц, раздел, "
              "P&L, сводная):" % len(mismatches))
        for row in mismatches[:20]:
            print("  ", row)
    counts["pl_check"] = mismatches
    return path, counts


class Command(BaseCommand):
    help = "Формирует управленческий пакет (P&L + Cash Flow + пояснения) в Excel."

    def add_arguments(self, parser):
        parser.add_argument("date_from", type=date.fromisoformat)
        parser.add_argument(
            "--start-year", type=int, default=DEFAULT_START_YEAR, dest="start_year",
            help="С какого года начинать колонки отчёта (по умолчанию %d)."
                 % DEFAULT_START_YEAR,
        )
        parser.add_argument(
            "--out", type=str, default=None,
            help="Путь к xlsx. По умолчанию <BASE_DIR>/reports/manpack_<дата>.xlsx",
        )

    def handle(self, *args, **options):
        try:
            path, stats = build_management_pack(
                options["date_from"],
                start_year=options["start_year"],
                out_path=options["out"],
            )
        except ValueError as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(self.style.SUCCESS("Пакет сохранён: %s" % path))
        self.stdout.write(
            "Месяцев в отчёте: %d (%s — %s) · строк P&L: %d · строк CF: %d"
            % (stats["months"], stats["first_month"], stats["last_month"],
               stats["pl_rows"], stats["cf_rows"])
        )
