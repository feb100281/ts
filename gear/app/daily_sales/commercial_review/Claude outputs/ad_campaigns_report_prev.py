# gear/app/daily_sales/ad_campaigns_report.py
"""
Отчёт по рекламным кампаниям WB: аналитическая PDF-записка (с
выводами и рекомендациями) и полная детализация в Excel. Тот же
паттерн, что и у "Штрафы / Логистика" (wb_top_cards_report.py) --
отдельная кнопка в том же меню "Экспорт", не трогает другие отчёты.

Данные -- из таблиц ads.* (management-команда ad_campaigns_etl.py на
сервере): ads.unpacked_ad_campaigns (кампании, актуальный снимок),
ads.unpacked_ad_campaigns_stats (статистика по дням на уровне
кампании), ads.unpacked_ad_campaigns_stats_by_nm (статистика по дням
и товарам) и ads.ad_campaigns_balance (баланс рекламного кабинета).
Наименование/бренд/категорию товара берём НЕ из самого рекламного
API (там поле title у карточек часто пустое), а из
inventories.wb_product -- того же источника, что использует весь
остальной дашборд.

Период -- тот же date-picker дашборда (filters.date_picker_id), не
выбран -- значит весь период (см. HISTORY_START в
wb_expenses_excel.py).

ДРР (доля рекламных расходов) считаем как расход / выручка от
рекламы * 100 -- выручка и заказы здесь ТЕ, которые WB сама
атрибutировала рекламе (поля sum_price/orders из fullstats), а не
все продажи по карточке за период -- это разные вещи, подменять
одно другим нельзя.

Для "Выводов и рекомендаций" используем простые прозрачные правила
(порог ДРР, сравнение с предыдущим периодом той же длины,
концентрация бюджета в одной кампании, кампании/товары с расходом
без единого заказа, остаток бюджета в днях при текущем темпе
расхода) -- ничего не гадаем, каждая рекомендация опирается на
конкретную цифру, которая тут же и показана.

По просьбе Дарьи текст в PDF -- максимально простым языком, термины
(ДРР, CTR, CPC, CR, баланс/net и т.п.) объясняются мелким шрифтом
внизу отдельным блоком-глоссарием, а не в основном тексте.
"""

from __future__ import annotations

import html as html_lib
import logging
from datetime import date, datetime, timedelta
from io import BytesIO

import pandas as pd
import dash_mantine_components as dmc
from dash import Input, Output, State, dcc, no_update

from openpyxl import Workbook

from . import excel_report_style as style
from .wb_expenses_excel import (
    HISTORY_START,
    export_menu_item,
    report_menu_group,
)

# Графики -- переиспользуем тот же движок (matplotlib -> SVG data-uri)
# и ту же палитру, что и в ежедневном "Коммерческом обзоре", вместо
# того чтобы городить второй с нуля: у Даши уже есть проверенный на
# печати стиль (шрифты как контуры, подписи прямо на графике, не
# больше 2 серий, только горизонтальная светлая сетка). Одно место
# правды на оба отчёта -- поправишь стиль там, он поправится и тут.
from .commercial_review import config as C
from .commercial_review.charts import (
    _fig as _cr_fig,
    _render as _cr_render,
    hbar as _cr_hbar,
    _money_formatter as _cr_money_formatter,
    _pct_formatter as _cr_pct_formatter,
    _short as _cr_short,
    _pct_label as _cr_pct_label,
)

#: Сколько кампаний/товаров показывать в топ-таблицах PDF-записки.
TOP_CAMPAIGNS_N = 15
TOP_PRODUCTS_N = 30

#: Сколько последних дней периода показывать построчно в PDF
#: (в Excel -- весь период без урезки).
DAILY_TREND_MAX_DAYS = 20

#: Отчёт ещё доделывается (визуал PDF, покрытие по датам и т.п.) --
#: пункт меню виден, но неактивен (серый, не открывается). Когда
#: отчёт будет готов -- поставить True и задеплоить файл заново.
AD_CAMPAIGNS_MENU_ENABLED = True

#: Личная шкала оценки общего ДРР за период -- по просьбе Дарьи,
#: НЕ общий отраслевой норматив, а её собственный ориентир (список
#: (верхняя_граница_включительно, ярлык), последний "хвост" -- ярлык
#: DRR_RATING_WORST_LABEL для всего, что выше последней границы).
#: Список может быть любой длины -- весь код ниже (_drr_rating,
#: _drr_scale_html, DRR_HIGH_THRESHOLD) построен по нему циклом, а не
#: по жёстко зашитым 3-4 ступеням, специально для случая, когда Дарья
#: снова поменяет число ступеней или сами границы.
#: Ориентир для этих чисел -- маржа БЕЗ учёта рекламы (см.
#: PRE_AD_MARGIN_REFERENCE_PCT ниже): чем она выше, тем больше ДРР
#: компания может себе позволить и остаться в плюсе, поэтому при
#: смене реальной маржи эти границы (и сама переменная маржи) стоит
#: пересмотреть вручную -- отчёт их сам не считает. Это ЕДИНСТВЕННОЕ
#: место, где эти границы заданы -- всё остальное в файле (в т.ч.
#: DRR_HIGH_THRESHOLD ниже) ссылается на этот список, а не дублирует
#: числа, чтобы шкала везде в отчёте была одна и та же.
DRR_RATING_BANDS = [
    (7.0, "Отлично"),
    (9.0, "Нормально"),
]
DRR_RATING_WORST_LABEL = "Плохо"

#: Маржа без учёта расходов на рекламу -- по словам Дарьи (28.8% в
#: сентябре 2026), значение задано вручную и отчёт его не считает
#: (себестоимость сюда больше не подключена -- см. историю правок).
#: Показываем как ориентир/контекст к шкале выше, а не как точную
#: посчитанную цифру -- обновлять руками при существенном изменении.
PRE_AD_MARGIN_REFERENCE_PCT = 28.8

#: Порог "хорошая/плохая" для ОТДЕЛЬНОЙ кампании (_classify_campaign),
#: для пунктирной линии на графике по неделям и для сноски ¹ в
#: глоссарии -- верхняя граница последней "хорошей" ступени личной
#: шкалы выше (сейчас "Нормально", до 9%). Всё, что хуже последней
#: ступени шкалы (то есть уже "Плохо"), считается "плохой" кампанией
#: и на уровне отдельной кампании тоже.
DRR_HIGH_THRESHOLD = DRR_RATING_BANDS[-1][0]
DRR_TREND_DELTA = 1.5
CONCENTRATION_THRESHOLD = 50.0
BUDGET_RUNWAY_WARN_DAYS = 14

#: Неделя считается всплеском расходов, если она настолько выше
#: среднего по остальным неделям окна -- тот же порог, что и в
#: WB_EXPENSES_SPIKE_RATIO у commercial_review, для единообразия.
WEEKLY_SPIKE_RATIO = 1.25

#: Сколько товаров/кампаний показывать в графиках-рейтингах (брендов,
#: хороших/плохих кампаний) -- графику больше 10-12 строк уже не
#: прочитать.
TOP_CHART_N = 10

#: Ниже этого расхода или числа заказов кампанию не судим "хорошая
#: она или плохая" -- слишком мало данных, чтобы не спутать сигнал с
#: шумом (см. _classify_campaign).
CAMPAIGN_MIN_SPEND_TO_JUDGE = 500.0
CAMPAIGN_MIN_ORDERS_TO_JUDGE = 3

#: Остаток (шт., WB-склад + FBS), ниже которого рекламу на товар
#: помечаем как рискованную -- скоро может кончиться.
LOW_STOCK_QTY_THRESHOLD = 5


# ================================================================ ID's
AD_CAMPAIGNS_PDF_ITEM_ID = "wb-ad-campaigns-pdf-item"
AD_CAMPAIGNS_EXCEL_ITEM_ID = "wb-ad-campaigns-excel-item"
AD_CAMPAIGNS_PERIODS_ITEM_ID = "wb-ad-campaigns-periods-item"
AD_CAMPAIGNS_PDF_DOWNLOAD_ID = "wb-ad-campaigns-pdf-download"
AD_CAMPAIGNS_EXCEL_DOWNLOAD_ID = "wb-ad-campaigns-excel-download"
AD_CAMPAIGNS_PERIODS_DOWNLOAD_ID = "wb-ad-campaigns-periods-download"
AD_CAMPAIGNS_STATUS_ID = "wb-ad-campaigns-status"
AD_CAMPAIGNS_CLICKS_ID = "wb-ad-campaigns-clicks"

AD_CAMPAIGNS_MENU_KINDS = (
    ("ad_campaigns_pdf", AD_CAMPAIGNS_PDF_ITEM_ID),
    ("ad_campaigns_excel", AD_CAMPAIGNS_EXCEL_ITEM_ID),
    ("ad_campaigns_periods", AD_CAMPAIGNS_PERIODS_ITEM_ID),
)

logger = logging.getLogger(__name__)


# ================================================================ форматирование
def _esc(text) -> str:
    return html_lib.escape("" if text is None else str(text))


def _money(v) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        v = 0
    v = round(float(v))
    sign = "-" if v < 0 else ""
    return f"{sign}{abs(v):,.0f}".replace(",", " ") + " ₽"


def _money_dec(v) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "—"
    v = float(v)
    sign = "-" if v < 0 else ""
    return f"{sign}{abs(v):,.2f}".replace(",", " ") + " ₽"


def _pct1(v) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "—"
    return f"{float(v):.1f}%"


def _int(v) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "—"
    return f"{int(round(float(v))):,}".replace(",", " ")


def _date(v) -> str:
    """Дата в формате дд.мм.гггг для таблиц отчёта -- "—", если даты
    нет (например, старая кампания без start_time в ответе WB)."""
    if v is None or (isinstance(v, float) and pd.isna(v)) or pd.isna(v):
        return "—"
    try:
        return pd.Timestamp(v).strftime("%d.%m.%Y")
    except Exception:
        return "—"


def _plural_ru(n: int, one: str, few: str, many: str) -> str:
    """Стандартное русское склонение по числу (то же правило, что и
    operations_text в wb_top_cards_report.py): 1 кампания, 2 кампании,
    5 кампаний."""
    n = abs(int(n)) % 100
    n1 = n % 10
    if 11 <= n <= 14:
        return many
    if n1 == 1:
        return one
    if 2 <= n1 <= 4:
        return few
    return many


def _period_label(start_date: str, end_date: str) -> str:
    start_label = pd.to_datetime(start_date).strftime("%d.%m.%Y")
    end_label = pd.to_datetime(end_date).strftime("%d.%m.%Y")
    return f"{start_label} – {end_label}" if start_date != end_date else start_label


def _prev_period_dates(start_date: str, end_date: str):
    """Предыдущий период той же длины, сразу перед текущим -- чтобы
    было с чем сравнить ДРР/расход (см. _narrative_html/_recommendations)."""
    start = pd.to_datetime(start_date).date()
    end = pd.to_datetime(end_date).date()
    length = (end - start).days + 1
    prev_end = start - timedelta(days=1)
    prev_start = prev_end - timedelta(days=length - 1)
    return prev_start.isoformat(), prev_end.isoformat()


# ================================================================ данные
def _fetch_campaigns_meta() -> pd.DataFrame:
    from conns import get_duckdb_conn_with_opt

    with get_duckdb_conn_with_opt() as con:
        return con.execute(
            """
            SELECT
                advert_id, name, type_name, status_name, payment_type
            FROM ads.unpacked_ad_campaigns
            """
        ).df()


def _fetch_products() -> pd.DataFrame:
    """nm_id -> наименование/бренд/категория -- тот же источник
    (inventories.wb_product), что и весь остальной дашборд. Наименование
    отсюда приоритетнее наименования из самого рекламного API: там
    это поле у карточек часто пустое (см. реальные ответы fullstats)."""
    from conns import get_duckdb_conn_with_opt

    with get_duckdb_conn_with_opt() as con:
        return con.execute(
            """
            SELECT
                card_id AS nm_id,
                MAX(title) AS product_title,
                MAX(NULLIF(TRIM(brand), '')) AS brand,
                COALESCE(NULLIF(TRIM(MAX(subject_name)), ''), 'Не указана') AS category
            FROM inventories.wb_product
            WHERE card_id IS NOT NULL
            GROUP BY card_id
            """
        ).df()


_STATS_COLUMNS = [
    "advert_id", "date", "views", "clicks", "spend_rub",
    "atbs", "orders", "shks", "revenue_rub", "canceled",
]


def _fetch_stats(start_date: str, end_date: str) -> pd.DataFrame:
    from conns import get_duckdb_conn_with_opt

    with get_duckdb_conn_with_opt() as con:
        df = con.execute(
            """
            SELECT
                advert_id, date, views, clicks, spend_rub,
                atbs, orders, shks, revenue_rub, canceled
            FROM ads.unpacked_ad_campaigns_stats
            WHERE date BETWEEN $start_date AND $end_date
            """,
            {"start_date": start_date, "end_date": end_date},
        ).df()

    return df if df is not None else pd.DataFrame(columns=_STATS_COLUMNS)


_STATS_BY_NM_COLUMNS = [
    "nm_id", "date", "api_title", "views", "clicks", "spend_rub",
    "atbs", "orders", "shks", "revenue_rub", "canceled",
]


def _fetch_stats_by_nm(start_date: str, end_date: str) -> pd.DataFrame:
    """Суммируем по всем площадкам (app_type) -- сами коды площадок
    WB нигде официально не расшифрованы (см. ADVERT площадка в
    load_ad_campaigns.py), показывать необъяснённые коды в отчёте
    не будем, а сумма по товару от этого не меняется."""
    from conns import get_duckdb_conn_with_opt

    with get_duckdb_conn_with_opt() as con:
        df = con.execute(
            """
            SELECT
                nm_id,
                date,
                ANY_VALUE(NULLIF(TRIM(title), '')) AS api_title,
                SUM(views) AS views,
                SUM(clicks) AS clicks,
                SUM(spend_rub) AS spend_rub,
                SUM(atbs) AS atbs,
                SUM(orders) AS orders,
                SUM(shks) AS shks,
                SUM(revenue_rub) AS revenue_rub,
                SUM(canceled) AS canceled
            FROM ads.unpacked_ad_campaigns_stats_by_nm
            WHERE date BETWEEN $start_date AND $end_date
            GROUP BY nm_id, date
            """,
            {"start_date": start_date, "end_date": end_date},
        ).df()

    return df if df is not None else pd.DataFrame(columns=_STATS_BY_NM_COLUMNS)


def _fetch_balance() -> dict:
    """Возвращает dict с полями баланса. Раньше при ЛЮБОЙ ошибке
    (включая "такой таблицы нет") молча возвращали None -- поэтому
    "Доступный бюджет (net)" мог показывать "-" без единого намёка
    на причину. Теперь всегда возвращаем dict с полем error: None,
    если всё получилось, иначе короткое понятное объяснение (его
    можно показывать прямо в отчёте) -- баланс всё равно
    дополнительная справка, отсутствие по-прежнему не должно ронять
    весь отчёт, но теперь хотя бы видно, ПОЧЕМУ его нет."""
    from conns import get_duckdb_conn_with_opt

    empty = {"balance": None, "net": None, "bonus": None, "currency": "₽"}

    try:
        with get_duckdb_conn_with_opt() as con:
            row = con.execute(
                """
                SELECT balance, net, bonus, currency
                FROM ads.ad_campaigns_balance
                LIMIT 1
                """
            ).fetchone()
    except Exception as exc:
        msg = str(exc)
        msg_low = msg.lower()
        # Вторая ветка -- отдельный случай: вьюха ads.ad_campaigns_balance
        # существует, но "зависла" на удалённый файл (если сборщик на
        # сервере запускался без DROP VIEW на отсутствующий баланс) --
        # DuckDB в этом случае бросает IOException/"No files found",
        # а не "Catalog Error"/"does not exist", и без этой ветки
        # человек видел бы сырой технический текст вместо объяснения.
        if "does not exist" in msg or "Catalog Error" in msg or "no such" in msg_low:
            reason = "таблица баланса не найдена в базе, которую читает дашборд"
        elif "no files found" in msg_low or "io error" in msg_low or "ioexception" in msg_low:
            reason = (
                "файл с балансом сейчас не найден (последний запрос за балансом на "
                "сервере не удался, а старая ссылка на файл ещё осталась) -- "
                "обновится при следующей успешной загрузке"
            )
        else:
            reason = f"{type(exc).__name__}: {msg}"[:120]
        return {**empty, "error": reason}

    if row is None:
        return {**empty, "error": "таблица баланса пуста (ни одной строки)"}

    return {
        "balance": row[0],
        "net": row[1],
        "bonus": row[2],
        "currency": row[3] or "₽",
        "error": None,
    }


def _fetch_data_as_of() -> str | None:
    """На какую дату у нас вообще есть загруженная статистика по
    кампаниям -- отдельно от "когда сформирована записка" (это
    всегда "сейчас"). Если сборщик на сервере не запускался
    несколько дней, эта дата отстанет от сегодняшней -- и это
    ровно то, что должно быть видно в отчёте."""
    from conns import get_duckdb_conn_with_opt

    try:
        with get_duckdb_conn_with_opt() as con:
            row = con.execute(
                "SELECT MAX(date) FROM ads.unpacked_ad_campaigns_stats"
            ).fetchone()
    except Exception:
        return None

    if not row or row[0] is None:
        return None

    return pd.Timestamp(row[0]).strftime("%d.%m.%Y")


def _fetch_period_to_date(end_date: str) -> dict | None:
    """Расход/выручка/заказы с начала недели, месяца, квартала и года
    -- по просьбе Дарьи ("может расходы на рекламу с начала года,
    квартала и месяца и недели"). Считаем от ДАТЫ КОНЦА ОТЧЁТА, а не
    от "сегодня" -- отчёт вполне может быть за прошлый период, и
    "с начала года" тогда должно значить "с начала того года", а не
    подмешивать сегодняшние данные, которых в остальном отчёте нет.

    Для каждого отрезка (неделя/месяц/квартал/год) считаем ещё и то
    же самое за СОПОСТАВИМЫЙ отрезок предыдущего аналогичного периода
    (то же число дней от начала предыдущей недели/месяца/квартала/
    года) -- голая сумма без этого сравнения ничего не говорит о том,
    ускорился темп расхода или замедлился.

    Один общий запрос с FILTER вместо четырёх отдельных -- быстрее и
    гарантирует, что все цифры посчитаны на один и тот же снимок
    данных."""
    from conns import get_duckdb_conn_with_opt

    sql = """
        WITH bounds AS (
            SELECT
                CAST($end_date AS DATE) AS end_date,
                DATE_TRUNC('week', CAST($end_date AS DATE)) AS week_start,
                DATE_TRUNC('month', CAST($end_date AS DATE)) AS month_start,
                DATE_TRUNC('quarter', CAST($end_date AS DATE)) AS quarter_start,
                DATE_TRUNC('year', CAST($end_date AS DATE)) AS year_start
        )
        SELECT
            b.week_start, b.month_start, b.quarter_start, b.year_start, b.end_date,
            SUM(s.spend_rub) FILTER (WHERE s.date BETWEEN b.week_start AND b.end_date) AS wtd_spend,
            SUM(s.revenue_rub) FILTER (WHERE s.date BETWEEN b.week_start AND b.end_date) AS wtd_revenue,
            SUM(s.orders) FILTER (WHERE s.date BETWEEN b.week_start AND b.end_date) AS wtd_orders,
            SUM(s.spend_rub) FILTER (
                WHERE s.date BETWEEN b.week_start - INTERVAL 7 DAY AND b.end_date - INTERVAL 7 DAY
            ) AS wtd_prev_spend,
            SUM(s.spend_rub) FILTER (WHERE s.date BETWEEN b.month_start AND b.end_date) AS mtd_spend,
            SUM(s.revenue_rub) FILTER (WHERE s.date BETWEEN b.month_start AND b.end_date) AS mtd_revenue,
            SUM(s.orders) FILTER (WHERE s.date BETWEEN b.month_start AND b.end_date) AS mtd_orders,
            SUM(s.spend_rub) FILTER (
                WHERE s.date BETWEEN b.month_start - INTERVAL 1 MONTH AND b.end_date - INTERVAL 1 MONTH
            ) AS mtd_prev_spend,
            SUM(s.spend_rub) FILTER (WHERE s.date BETWEEN b.quarter_start AND b.end_date) AS qtd_spend,
            SUM(s.revenue_rub) FILTER (WHERE s.date BETWEEN b.quarter_start AND b.end_date) AS qtd_revenue,
            SUM(s.orders) FILTER (WHERE s.date BETWEEN b.quarter_start AND b.end_date) AS qtd_orders,
            SUM(s.spend_rub) FILTER (
                WHERE s.date BETWEEN b.quarter_start - INTERVAL 3 MONTH AND b.end_date - INTERVAL 3 MONTH
            ) AS qtd_prev_spend,
            SUM(s.spend_rub) FILTER (WHERE s.date BETWEEN b.year_start AND b.end_date) AS ytd_spend,
            SUM(s.revenue_rub) FILTER (WHERE s.date BETWEEN b.year_start AND b.end_date) AS ytd_revenue,
            SUM(s.orders) FILTER (WHERE s.date BETWEEN b.year_start AND b.end_date) AS ytd_orders,
            SUM(s.spend_rub) FILTER (
                WHERE s.date BETWEEN b.year_start - INTERVAL 1 YEAR AND b.end_date - INTERVAL 1 YEAR
            ) AS ytd_prev_spend
        FROM bounds b
        LEFT JOIN ads.unpacked_ad_campaigns_stats s ON TRUE
        GROUP BY b.week_start, b.month_start, b.quarter_start, b.year_start, b.end_date
    """
    try:
        with get_duckdb_conn_with_opt() as con:
            row = con.execute(sql, {"end_date": end_date}).fetchone()
    except Exception:
        logger.exception("Не удалось посчитать расход с начала недели/месяца/квартала/года")
        return None

    if row is None:
        return None

    cols = [
        "week_start", "month_start", "quarter_start", "year_start", "end_date",
        "wtd_spend", "wtd_revenue", "wtd_orders", "wtd_prev_spend",
        "mtd_spend", "mtd_revenue", "mtd_orders", "mtd_prev_spend",
        "qtd_spend", "qtd_revenue", "qtd_orders", "qtd_prev_spend",
        "ytd_spend", "ytd_revenue", "ytd_orders", "ytd_prev_spend",
    ]
    data = dict(zip(cols, row))

    def _period(prefix: str, label: str) -> dict:
        spend = data.get(f"{prefix}_spend") or 0.0
        revenue = data.get(f"{prefix}_revenue") or 0.0
        orders = data.get(f"{prefix}_orders") or 0
        prev_spend = data.get(f"{prefix}_prev_spend")
        change_pct = ((spend - prev_spend) / prev_spend * 100) if prev_spend else None
        return {
            "label": label,
            "spend": spend,
            "revenue": revenue,
            "orders": orders,
            "drr": (spend / revenue * 100) if revenue else None,
            "prev_spend": prev_spend,
            "change_pct": change_pct,
        }

    return {
        "as_of": data["end_date"],
        "week": _period("wtd", "С начала недели"),
        "month": _period("mtd", "С начала месяца"),
        "quarter": _period("qtd", "С начала квартала"),
        "year": _period("ytd", "С начала года"),
    }


def _fetch_stocks() -> pd.DataFrame:
    """Текущий остаток (WB-склад + FBS, последний доступный снимок)
    по nm_id -- те же таблицы, что использует остальной дашборд
    (daily_brief/data/stock_balance.py), нужны здесь только чтобы
    пометить "в этот товар льётся реклама, а остаток маленький/его
    нет". Это дополнительная справка, а не главная цифра отчёта --
    если таблиц ещё нет или они пустые, просто молча возвращаем
    пустую таблицу, а не роняем отчёт (см. _safe ниже)."""
    from conns import get_duckdb_conn_with_opt

    empty = pd.DataFrame(columns=["nm_id", "stock_qty"])

    try:
        with get_duckdb_conn_with_opt() as con:
            df = con.execute(
                """
                WITH wb AS (
                    SELECT
                        nm_id,
                        SUM(COALESCE(quantity, 0)) AS wb_qty
                    FROM stocks.unpacked_stocks
                    WHERE date_from = (SELECT MAX(date_from) FROM stocks.unpacked_stocks)
                      AND nm_id IS NOT NULL
                    GROUP BY nm_id
                ),
                fbs AS (
                    SELECT
                        nm_id,
                        SUM(COALESCE(quantity, 0)) AS fbs_qty
                    FROM stocks.unpacked_fbs_stocks
                    WHERE date_from = (SELECT MAX(date_from) FROM stocks.unpacked_fbs_stocks)
                      AND nm_id IS NOT NULL
                    GROUP BY nm_id
                )
                SELECT
                    COALESCE(wb.nm_id, fbs.nm_id) AS nm_id,
                    COALESCE(wb.wb_qty, 0) + COALESCE(fbs.fbs_qty, 0) AS stock_qty
                FROM wb
                FULL OUTER JOIN fbs ON wb.nm_id = fbs.nm_id
                """
            ).df()
    except Exception:
        return empty

    return df if df is not None else empty


def _fetch_stocks_as_of() -> str | None:
    """На какую дату вообще взят остаток в _fetch_stocks() -- WB-склад
    и FBS обновляются отдельно, снимки могут быть за разные дни, а
    отчёт по рекламе часто смотрят за совсем другой период. Берём
    самую свежую из двух дат и подписываем её явно в отчёте, а не
    молчим про то, что остаток "на сейчас" на самом деле может быть
    на несколько дней старше периода отчёта."""
    from conns import get_duckdb_conn_with_opt

    try:
        with get_duckdb_conn_with_opt() as con:
            row = con.execute(
                """
                SELECT GREATEST(
                    COALESCE((SELECT MAX(date_from) FROM stocks.unpacked_stocks), DATE '1900-01-01'),
                    COALESCE((SELECT MAX(date_from) FROM stocks.unpacked_fbs_stocks), DATE '1900-01-01')
                )
                """
            ).fetchone()
    except Exception:
        return None

    if not row or row[0] is None:
        return None

    as_of = pd.Timestamp(row[0])
    if as_of.year < 1990:
        return None
    return as_of.strftime("%d.%m.%Y")


def _classify_campaign(spend_rub, orders, drr) -> str:
    """"Хорошая" / "плохая" / "мало данных" -- максимально простое,
    объяснимое одной фразой правило поверх уже посчитанных ДРР и
    заказов (тот же принцип прозрачности, что и в _recommendations
    ниже: никаких скрытых весов).

    Сначала отсеиваем совсем маленький расход -- кампания за 200 ₽
    ничего не доказывает ни в какую сторону. А вот "потратили заметно
    и НИ ОДНОГО заказа" -- это уже само по себе достаточный сигнал
    "плохая", и порог по числу заказов её не должен прятать в "мало
    данных": ноль заказов при заметном расходе -- ровно то, что эта
    метка обязана ловить (см. правило №4 в _recommendations)."""
    if spend_rub is None or spend_rub < CAMPAIGN_MIN_SPEND_TO_JUDGE:
        return "мало данных"

    if orders is None or orders == 0:
        return "плохая"

    if orders < CAMPAIGN_MIN_ORDERS_TO_JUDGE:
        return "мало данных"

    if drr is None or drr > DRR_HIGH_THRESHOLD:
        return "плохая"

    return "хорошая"


def _bad_campaign_reason(spend_rub, orders, revenue_rub, drr) -> str:
    """Человеческое объяснение, ПОЧЕМУ именно эта кампания попала в
    "плохие" -- та же логика, что в _classify_campaign, только в виде
    фразы с реальными цифрами конкретной кампании, а не общим
    правилом. Статус WB (Активна/Завершена) тут ни при чём -- плохая
    кампания разбирается одинаково, даже если уже завершена: деньги
    всё равно потрачены, и понять, что пошло не так, стоит в любом
    случае."""
    if orders is None or orders == 0:
        return (
            f"Потрачено {_money(spend_rub)}, но ни одного заказа от рекламы "
            f"не получено."
        )

    if drr is None:
        return (
            f"Заказы есть ({_int(orders)}), но WB не относит на них выручку "
            f"от рекламы -- посчитать ДРР нельзя, окупаемость не подтверждена."
        )

    return (
        f"ДРР {_pct1(drr)} -- выше нормы ({DRR_HIGH_THRESHOLD:.0f}%): на "
        f"{_money(spend_rub)} расхода пришлось только {_money(revenue_rub)} "
        f"выручки от рекламы при {_int(orders)} заказ(ах)."
    )



# ================================================================ агрегация
def _rates(g: pd.DataFrame) -> pd.DataFrame:
    """Добавляет CTR/CPC/CR/ДРР -- считаем из уже просуммированных
    показов/кликов/расхода/заказов/выручки (взвешенное среднее), а
    не усредняем построчные ctr/cr WB -- иначе короткие дни без
    показов исказили бы среднее."""
    g["ctr"] = g.apply(lambda r: (r["clicks"] / r["views"] * 100) if r["views"] else 0.0, axis=1)
    g["cpc"] = g.apply(lambda r: (r["spend_rub"] / r["clicks"]) if r["clicks"] else 0.0, axis=1)
    g["cr"] = g.apply(lambda r: (r["orders"] / r["clicks"] * 100) if r["clicks"] else 0.0, axis=1)
    g["drr"] = g.apply(lambda r: (r["spend_rub"] / r["revenue_rub"] * 100) if r["revenue_rub"] else None, axis=1)
    return g


_CAMPAIGNS_AGG_COLUMNS = [
    "advert_id", "name", "type_name", "status_name", "payment_type",
    "views", "clicks", "ctr", "cpc", "spend_rub",
    "atbs", "orders", "cr", "shks", "revenue_rub", "canceled", "drr",
    "quality",
]


def _aggregate_campaigns(stats: pd.DataFrame, meta: pd.DataFrame) -> pd.DataFrame:
    if stats is None or stats.empty:
        return pd.DataFrame(columns=_CAMPAIGNS_AGG_COLUMNS)

    g = (
        stats.groupby("advert_id", dropna=False)
        .agg(
            views=("views", "sum"), clicks=("clicks", "sum"),
            spend_rub=("spend_rub", "sum"), atbs=("atbs", "sum"),
            orders=("orders", "sum"), shks=("shks", "sum"),
            revenue_rub=("revenue_rub", "sum"), canceled=("canceled", "sum"),
        )
        .reset_index()
    )

    if meta is not None and not meta.empty:
        g = g.merge(meta, on="advert_id", how="left")
    else:
        g["name"] = None
        g["type_name"] = None
        g["status_name"] = None
        g["payment_type"] = None

    g["name"] = g["name"].fillna("(кампания удалена или переименована)")
    g["type_name"] = g["type_name"].fillna("—")
    g["status_name"] = g["status_name"].fillna("—")
    g["payment_type"] = g["payment_type"].fillna("—")

    g = _rates(g)
    g["quality"] = g.apply(
        lambda r: _classify_campaign(r["spend_rub"], r["orders"], r["drr"]), axis=1
    )
    return g[_CAMPAIGNS_AGG_COLUMNS]


_PRODUCTS_AGG_COLUMNS = [
    "nm_id", "title", "brand", "category", "stock_qty",
    "views", "clicks", "ctr", "cpc", "spend_rub",
    "atbs", "orders", "cr", "shks", "revenue_rub", "canceled", "drr",
]


def _aggregate_products(
    stats_by_nm: pd.DataFrame,
    products: pd.DataFrame,
    stocks: pd.DataFrame | None = None,
) -> pd.DataFrame:
    if stats_by_nm is None or stats_by_nm.empty:
        return pd.DataFrame(columns=_PRODUCTS_AGG_COLUMNS)

    g = (
        stats_by_nm.groupby("nm_id", dropna=False)
        .agg(
            api_title=("api_title", "first"),
            views=("views", "sum"), clicks=("clicks", "sum"),
            spend_rub=("spend_rub", "sum"), atbs=("atbs", "sum"),
            orders=("orders", "sum"), shks=("shks", "sum"),
            revenue_rub=("revenue_rub", "sum"), canceled=("canceled", "sum"),
        )
        .reset_index()
    )

    if products is not None and not products.empty:
        g = g.merge(products, on="nm_id", how="left")
    else:
        g["product_title"] = None
        g["brand"] = None
        g["category"] = None

    # inventories.wb_product приоритетнее наименования из рекламного
    # API -- там оно часто пустое (см. докстринг модуля).
    has_product_title = g["product_title"].notna() & (g["product_title"].astype(str).str.strip() != "")
    g["title"] = g["product_title"].where(has_product_title, g["api_title"])
    g["title"] = g["title"].where(
        g["title"].notna() & (g["title"].astype(str).str.strip() != ""),
        g["nm_id"].apply(lambda x: f"Товар nm_id {int(x)}"),
    )
    g["brand"] = g["brand"].fillna("Не указан")
    g["category"] = g["category"].fillna("Не указана")

    if stocks is not None and not stocks.empty:
        g = g.merge(stocks, on="nm_id", how="left")
    else:
        # None (не 0!) -- отличаем "остатков нет" от "мы их просто
        # не смогли посчитать", см. _stock_note_html.
        g["stock_qty"] = None

    g = _rates(g)
    return g[_PRODUCTS_AGG_COLUMNS]


_DAILY_AGG_COLUMNS = [
    "date", "views", "clicks", "ctr", "cpc", "spend_rub",
    "atbs", "orders", "cr", "shks", "revenue_rub", "canceled", "drr",
]


def _aggregate_daily(stats: pd.DataFrame) -> pd.DataFrame:
    if stats is None or stats.empty:
        return pd.DataFrame(columns=_DAILY_AGG_COLUMNS)

    g = (
        stats.groupby("date", dropna=False)
        .agg(
            views=("views", "sum"), clicks=("clicks", "sum"),
            spend_rub=("spend_rub", "sum"), atbs=("atbs", "sum"),
            orders=("orders", "sum"), shks=("shks", "sum"),
            revenue_rub=("revenue_rub", "sum"), canceled=("canceled", "sum"),
        )
        .reset_index()
        .sort_values("date")
    )

    g = _rates(g)
    return g[_DAILY_AGG_COLUMNS]


_TYPE_AGG_COLUMNS = ["type_name", "spend_rub", "orders", "drr"]


def _aggregate_by_type(campaigns_df: pd.DataFrame) -> pd.DataFrame:
    if campaigns_df is None or campaigns_df.empty:
        return pd.DataFrame(columns=_TYPE_AGG_COLUMNS)

    g = (
        campaigns_df.groupby("type_name", dropna=False)
        .agg(spend_rub=("spend_rub", "sum"), orders=("orders", "sum"), revenue_rub=("revenue_rub", "sum"))
        .reset_index()
    )
    g["drr"] = g.apply(lambda r: (r["spend_rub"] / r["revenue_rub"] * 100) if r["revenue_rub"] else None, axis=1)
    return g[_TYPE_AGG_COLUMNS].sort_values("spend_rub", ascending=False)


_BRANDS_AGG_COLUMNS = [
    "brand", "views", "clicks", "ctr", "cpc", "spend_rub",
    "atbs", "orders", "cr", "shks", "revenue_rub", "canceled", "drr",
]


def _aggregate_brands(stats_by_nm: pd.DataFrame, products: pd.DataFrame) -> pd.DataFrame:
    """Тот же принцип, что и в _aggregate_products, но группируем по
    бренду -- отвечает на вопрос коллег "какой бренд реклама реально
    тянет, а какой просто ест бюджет"."""
    if stats_by_nm is None or stats_by_nm.empty:
        return pd.DataFrame(columns=_BRANDS_AGG_COLUMNS)

    brand_lookup = (
        products[["nm_id", "brand"]]
        if products is not None and not products.empty
        else pd.DataFrame(columns=["nm_id", "brand"])
    )

    merged = stats_by_nm.merge(brand_lookup, on="nm_id", how="left")
    merged["brand"] = merged["brand"].fillna("Не указан")

    g = (
        merged.groupby("brand", dropna=False)
        .agg(
            views=("views", "sum"), clicks=("clicks", "sum"),
            spend_rub=("spend_rub", "sum"), atbs=("atbs", "sum"),
            orders=("orders", "sum"), shks=("shks", "sum"),
            revenue_rub=("revenue_rub", "sum"), canceled=("canceled", "sum"),
        )
        .reset_index()
    )

    g = _rates(g)
    return g[_BRANDS_AGG_COLUMNS]


_WEEKLY_AGG_COLUMNS = [
    "week_start", "week_label", "views", "clicks", "ctr", "cpc", "spend_rub",
    "atbs", "orders", "cr", "shks", "revenue_rub", "canceled", "drr",
]


def _aggregate_weekly(stats: pd.DataFrame) -> pd.DataFrame:
    """Недели с понедельника -- отвечает на "по неделям: видно
    динамику, всплески, просадки" из списка коллег."""
    if stats is None or stats.empty:
        return pd.DataFrame(columns=_WEEKLY_AGG_COLUMNS)

    df = stats.copy()
    df["date"] = pd.to_datetime(df["date"])
    df["week_start"] = df["date"] - pd.to_timedelta(df["date"].dt.weekday, unit="D")

    g = (
        df.groupby("week_start", dropna=False)
        .agg(
            views=("views", "sum"), clicks=("clicks", "sum"),
            spend_rub=("spend_rub", "sum"), atbs=("atbs", "sum"),
            orders=("orders", "sum"), shks=("shks", "sum"),
            revenue_rub=("revenue_rub", "sum"), canceled=("canceled", "sum"),
        )
        .reset_index()
        .sort_values("week_start")
    )

    g["week_label"] = g["week_start"].apply(
        lambda d: f"{d:%d.%m}–{(d + pd.Timedelta(days=6)):%d.%m}"
    )

    g = _rates(g)
    return g[_WEEKLY_AGG_COLUMNS]


def _find_weekly_spike(weekly_df: pd.DataFrame) -> dict | None:
    """Неделя, чей расход настолько выше среднего по ОСТАЛЬНЫМ
    неделям окна, что заслуживает отдельной подписи на графике --
    тот же приём, что и _find_spike в commercial_review (WB_EXPENSES_
    SPIKE_RATIO), только на недельном расходе по рекламе."""
    if weekly_df is None or len(weekly_df) < 3:
        return None

    for idx, row in weekly_df.iterrows():
        others = weekly_df.drop(idx)
        if others.empty:
            continue
        avg_others = others["spend_rub"].mean()
        if avg_others and row["spend_rub"] >= avg_others * WEEKLY_SPIKE_RATIO:
            return {"label": row["week_label"], "ratio": row["spend_rub"] / avg_others}

    return None


def _totals_from_stats(stats: pd.DataFrame) -> dict:
    if stats is None or stats.empty:
        return {
            "views": 0, "clicks": 0, "spend_rub": 0.0, "atbs": 0, "orders": 0,
            "shks": 0, "revenue_rub": 0.0, "canceled": 0,
            "ctr": None, "cpc": None, "cr": None, "drr": None,
        }

    views = int(stats["views"].sum())
    clicks = int(stats["clicks"].sum())
    spend = float(stats["spend_rub"].sum())
    atbs = int(stats["atbs"].sum())
    orders = int(stats["orders"].sum())
    shks = int(stats["shks"].sum())
    revenue = float(stats["revenue_rub"].sum())
    canceled = int(stats["canceled"].sum())

    return {
        "views": views, "clicks": clicks, "spend_rub": spend, "atbs": atbs,
        "orders": orders, "shks": shks, "revenue_rub": revenue, "canceled": canceled,
        "ctr": (clicks / views * 100) if views else None,
        "cpc": (spend / clicks) if clicks else None,
        "cr": (orders / clicks * 100) if clicks else None,
        "drr": (spend / revenue * 100) if revenue else None,
    }


def _fetch_report_bundle(start_date: str, end_date: str) -> dict:
    """Один поход в базу на весь отчёт (и PDF, и Excel собираются
    из одного и того же bundle) -- то же соображение, что и с ДРР
    выше: чтобы суммы в записке и в детализации не могли разойтись."""
    meta = _fetch_campaigns_meta()
    products = _fetch_products()
    stats = _fetch_stats(start_date, end_date)
    stats_by_nm = _fetch_stats_by_nm(start_date, end_date)
    balance = _fetch_balance()

    try:
        data_as_of = _fetch_data_as_of()
    except Exception:
        data_as_of = None

    try:
        stocks = _fetch_stocks()
    except Exception:
        # остатки -- дополнительная справка (см. докстринг
        # _fetch_stocks), а не то, без чего весь отчёт должен упасть.
        stocks = pd.DataFrame(columns=["nm_id", "stock_qty"])

    try:
        stocks_as_of = _fetch_stocks_as_of()
    except Exception:
        stocks_as_of = None

    try:
        period_to_date = _fetch_period_to_date(end_date)
    except Exception:
        # тоже дополнительная справка -- без неё отчёт всё равно
        # собирается целиком, просто без блока "темп расходов".
        logger.exception("Не удалось посчитать расход с начала недели/месяца/квартала/года")
        period_to_date = None

    prev_start, prev_end = _prev_period_dates(start_date, end_date)
    try:
        prev_stats = _fetch_stats(prev_start, prev_end)
    except Exception:
        prev_stats = pd.DataFrame(columns=_STATS_COLUMNS)

    campaigns_df = _aggregate_campaigns(stats, meta)
    products_df = _aggregate_products(stats_by_nm, products, stocks)
    daily_df = _aggregate_daily(stats)
    by_type_df = _aggregate_by_type(campaigns_df)
    brands_df = _aggregate_brands(stats_by_nm, products)
    weekly_df = _aggregate_weekly(stats)
    weekly_spike = _find_weekly_spike(weekly_df)

    period_days = (pd.to_datetime(end_date).date() - pd.to_datetime(start_date).date()).days + 1

    return {
        "start_date": start_date,
        "end_date": end_date,
        "period_days": period_days,
        "prev_start": prev_start,
        "prev_end": prev_end,
        "campaigns": campaigns_df,
        "products": products_df,
        "daily": daily_df,
        "by_type": by_type_df,
        "brands": brands_df,
        "weekly": weekly_df,
        "weekly_spike": weekly_spike,
        "stocks_available": stocks is not None and not stocks.empty,
        "stocks_as_of": stocks_as_of,
        "period_to_date": period_to_date,
        "totals": _totals_from_stats(stats),
        "prev_totals": _totals_from_stats(prev_stats) if not prev_stats.empty else None,
        "balance": balance,
        "data_as_of": data_as_of,
    }


# ================================================================ выводы и рекомендации
def _recommendations(bundle: dict) -> list[tuple[str, str]]:
    """Правила максимально прозрачные -- каждая рекомендация тут же
    объясняет, из какой именно цифры она сделана, чтобы можно было
    самостоятельно проверить вывод, а не просто поверить на слово."""
    totals = bundle["totals"]
    prev_totals = bundle["prev_totals"]
    campaigns_df = bundle["campaigns"]
    products_df = bundle["products"]
    balance = bundle["balance"]
    period_days = bundle["period_days"] or 1

    drr = totals["drr"]
    spend = totals["spend_rub"]
    recs: list[tuple[str, str]] = []

    # 0. что сработало -- лучшая кампания периода. Добавляем её ПЕРВОЙ
    # и (в отличие от остальных пунктов) не привязываем к какой-то
    # проблеме: без этого пункта "Выводы и рекомендации" в спокойный
    # период могли состоять из одной строки про ДРР и выглядеть
    # пустыми на всю страницу.
    if campaigns_df is not None and not campaigns_df.empty:
        good = campaigns_df[campaigns_df["quality"] == "хорошая"]
        best = None
        if not good.empty:
            best = (
                good.loc[good["drr"].idxmin()]
                if good["drr"].notna().any()
                else good.loc[good["revenue_rub"].idxmax()]
            )
        if best is not None:
            recs.append((
                f"Лучше всех отработала «{_esc(best['name'])}»",
                f"ДРР {_pct1(best['drr'])}: на {_money(best['spend_rub'])} расхода — "
                f"{_money(best['revenue_rub'])} выручки от рекламы и {_int(best['orders'])} "
                f"заказ(ов). Стоит присмотреться, можно ли аккуратно увеличить её бюджет, "
                f"не теряя такую эффективность."
            ))

    # 1. ДРР относительно периода
    if totals["orders"] == 0 and spend > 0:
        recs.append((
            "Расход есть, заказов от рекламы нет",
            f"За период потрачено {_money(spend)}, но реклама не принесла ни одного "
            f"заказа (по данным WB). Стоит проверить кампании ниже вручную и, "
            f"возможно, приостановить их до выяснения причины."
        ))
    elif drr is not None:
        # Ветвим по ГРУППЕ (good/warn/bad), а не по конкретному тексту
        # ярлыка -- шкала DRR_RATING_BANDS уже дважды меняла и число
        # ступеней, и сами границы, а этот код от количества ступеней
        # не должен зависеть.
        rating = _drr_rating(drr)
        group = _drr_rating_group(rating)
        if group == "good":
            recs.append((
                f"ДРР хороший — оценка «{rating}»",
                f"Доля рекламных расходов за период — {_pct1(drr)} (по личной шкале "
                f"— «{rating}»). Явных поводов срочно что-то менять нет: если товар "
                f"и так хорошо продаётся, можно аккуратно увеличить бюджет или "
                f"ставки на самые эффективные кампании из таблицы ниже, не теряя "
                f"такую эффективность."
            ))
        elif group == "warn":
            recs.append((
                f"ДРР стоит присматривать — оценка «{rating}»",
                f"Доля рекламных расходов за период — {_pct1(drr)} (по личной шкале "
                f"— «{rating}»). При марже без учёта рекламы около "
                f"{_pct1(PRE_AD_MARGIN_REFERENCE_PCT)} реклама ещё окупается, но "
                f"запас уже не такой большой — стоит присматриваться к кампаниям с "
                f"самым высоким ДРР в таблице ниже, пока показатель не перешёл в "
                f"«{DRR_RATING_WORST_LABEL}»."
            ))
        else:
            recs.append((
                "ДРР выше комфортного уровня",
                f"Доля рекламных расходов за период — {_pct1(drr)}, это оценка "
                f"«{DRR_RATING_WORST_LABEL}» (выше {_pct1(DRR_HIGH_THRESHOLD)}). "
                f"Есть смысл проверить самые дорогие кампании и товары из таблиц "
                f"ниже: часто дело в одной-двух кампаниях, где клики есть, а "
                f"заказов мало — их можно приостановить или снизить ставку."
            ))

    # 2. сравнение с предыдущим периодом такой же длины -- показываем
    # ВСЕГДА, а не только при заметном изменении: в спокойный период
    # это тоже полезный контекст ("всё стабильно"), а не только повод
    # для тревоги -- и без этого пункта раздел слишком легко пустеет.
    if prev_totals is not None and drr is not None and prev_totals["drr"] is not None:
        diff = drr - prev_totals["drr"]
        prev_label = _period_label(bundle["prev_start"], bundle["prev_end"])
        if abs(diff) >= DRR_TREND_DELTA:
            direction = "выросла" if diff > 0 else "снизилась"
            explanation = (
                "Стоит посмотреть, что изменилось: ставки, конкуренция за показы "
                "или сезонный спрос."
                if diff > 0 else
                "Реклама стала работать эффективнее, чем в предыдущем периоде — "
                "хороший знак."
            )
            recs.append((
                "Изменение по сравнению с предыдущим периодом",
                f"ДРР {direction} на {abs(diff):.1f} п.п. по сравнению с таким же "
                f"по длине предыдущим периодом ({prev_label}, тогда было {_pct1(prev_totals['drr'])}). "
                f"{explanation}"
            ))
        else:
            recs.append((
                "По сравнению с предыдущим периодом — стабильно",
                f"ДРР почти не изменился по сравнению с таким же по длине предыдущим "
                f"периодом ({prev_label}: {_pct1(prev_totals['drr'])} тогда против {_pct1(drr)} "
                f"сейчас) — разница {abs(diff):.1f} п.п., в пределах обычных колебаний."
            ))

    # 2а. темп расходов в этом месяце -- используем уже посчитанный
    # period_to_date (см. раздел "Темп расходов" выше), но добавляем
    # только при ощутимой разнице, чтобы не дублировать тот раздел
    # один в один, если там и так всё ровно.
    ptd = bundle.get("period_to_date")
    if ptd:
        month = ptd.get("month") or {}
        change = month.get("change_pct")
        if change is not None and abs(change) >= 5:
            direction = "быстрее" if change > 0 else "медленнее"
            follow_up = (
                "Стоит убедиться, что доступного бюджета хватит до конца месяца при таком темпе."
                if change > 0 else
                "Если снижение не запланировано -- стоит проверить, не остановились ли какие-то кампании сами по себе."
            )
            recs.append((
                f"Темп расходов в этом месяце {direction} прошлого",
                f"С начала месяца потрачено {_money(month['spend'])} — это на {abs(change):.0f}% "
                f"{direction}, чем за то же число дней прошлого месяца "
                f"({_money(month.get('prev_spend') or 0)}). {follow_up}"
            ))

    # 3. концентрация бюджета в одной кампании
    if campaigns_df is not None and not campaigns_df.empty and spend > 0:
        top_row = campaigns_df.loc[campaigns_df["spend_rub"].idxmax()]
        top_share = top_row["spend_rub"] / spend * 100
        if top_share >= CONCENTRATION_THRESHOLD:
            recs.append((
                "Бюджет сосредоточен в одной кампании",
                f"Кампания «{_esc(top_row['name'])}» забирает {top_share:.0f}% всего "
                f"расхода на рекламу за период. Само по себе это не плохо, но "
                f"стоит время от времени проверять её показатели отдельно — при "
                f"просадке эффективности именно у неё сильнее всего пострадает "
                f"общий результат."
            ))

    # 4. кампании с расходом, но без единого заказа
    if campaigns_df is not None and not campaigns_df.empty:
        dead_threshold = max(1000.0, spend * 0.01)
        dead = campaigns_df[(campaigns_df["spend_rub"] >= dead_threshold) & (campaigns_df["orders"] == 0)]
        if not dead.empty and totals["orders"] > 0:
            # это отдельно от правила №1 (там речь о полном отсутствии
            # заказов ВООБЩЕ) -- здесь заказы в целом есть, но не у ЭТИХ
            # конкретных кампаний, и это стоит показать отдельно.
            names = ", ".join(f"«{_esc(n)}»" for n in dead["name"].head(5))
            wasted = dead["spend_rub"].sum()
            word = _plural_ru(len(dead), "кампания", "кампании", "кампаний")
            single = len(dead) == 1
            verb1 = "потратила" if single else "потратили"
            verb2 = "принесла" if single else "принесли"
            recs.append((
                f"{len(dead)} {word} с расходом, но без единого заказа",
                f"{names} — за период {verb1} суммарно {_money(wasted)}, но не "
                f"{verb2} ни одного заказа. Стоит проверить их вручную: возможно, "
                f"пора приостановить или пересмотреть настройки."
            ))

    # 5. товары с расходом на рекламу, но без всякой отдачи
    if products_df is not None and not products_df.empty:
        dead_threshold = max(500.0, spend * 0.005)
        dead_products = products_df[
            (products_df["spend_rub"] >= dead_threshold) & (products_df["revenue_rub"] == 0)
        ]
        if not dead_products.empty:
            names = ", ".join(f"«{_esc(t)}»" for t in dead_products["title"].head(5))
            wasted = dead_products["spend_rub"].sum()
            word = _plural_ru(len(dead_products), "товар", "товара", "товаров")
            recs.append((
                f"{len(dead_products)} {word} с рекламой без отдачи",
                f"{names} — реклама показывалась и тратила бюджет "
                f"({_money(wasted)} суммарно), но не принесла ни одной продажи, "
                f"которую WB засчитала бы этой рекламе. Возможно, дело не в самой "
                f"рекламе, а в карточке товара (цена, фото, отзывы) — стоит "
                f"проверить в первую очередь их."
            ))

    # 6. остаток бюджета в днях при текущем темпе расхода
    if balance and not balance.get("error") and balance.get("net") is not None and spend > 0:
        avg_daily_spend = spend / period_days
        if avg_daily_spend > 0:
            days_left = balance["net"] / avg_daily_spend
            if days_left < BUDGET_RUNWAY_WARN_DAYS:
                recs.append((
                    f"Доступного бюджета хватит примерно на {days_left:.0f} дн.",
                    f"При среднем расходе {_money(avg_daily_spend)} в день доступного "
                    f"бюджета (net — {_money(balance['net'])}) хватит примерно на "
                    f"{days_left:.0f} дней. Стоит запланировать пополнение заранее, "
                    f"чтобы кампании не остановились сами по себе."
                ))

    if not recs:
        recs.append((
            "Существенных поводов для тревоги не найдено",
            "Расход, отдача и структура кампаний за период выглядят ровно."
        ))

    return recs


def _narrative_html(bundle: dict) -> str:
    totals = bundle["totals"]
    campaigns_df = bundle["campaigns"]
    products_df = bundle["products"]

    if totals["spend_rub"] == 0 and totals["views"] == 0:
        return '<p class="narrative">За выбранный период данных по рекламе нет.</p>'

    order_word = _plural_ru(totals["orders"], "заказ", "заказа", "заказов")
    sentences = [
        f"За период потрачено на рекламу {_money(totals['spend_rub'])}, реклама принесла "
        f"{_int(totals['orders'])} {order_word} на сумму {_money(totals['revenue_rub'])}."
    ]

    if totals["drr"] is not None:
        sentences.append(f"Доля рекламных расходов (ДРР) за период — {_pct1(totals['drr'])}.")

    if campaigns_df is not None and not campaigns_df.empty:
        top = campaigns_df.loc[campaigns_df["spend_rub"].idxmax()]
        top_order_word = _plural_ru(top["orders"], "заказ", "заказа", "заказов")
        sentences.append(
            f"Больше всего потрачено на кампанию «{_esc(top['name'])}» — "
            f"{_money(top['spend_rub'])} ({_int(top['orders'])} {top_order_word})."
        )

    if products_df is not None and not products_df.empty:
        top_p = products_df.loc[products_df["spend_rub"].idxmax()]
        sentences.append(
            f"Среди товаров больше всего рекламного бюджета ушло на "
            f"«{_esc(top_p['title'])}» — {_money(top_p['spend_rub'])}."
        )

    if campaigns_df is not None and not campaigns_df.empty and totals["spend_rub"]:
        bad_spend = campaigns_df.loc[campaigns_df["quality"] == "плохая", "spend_rub"].sum()
        bad_share = bad_spend / totals["spend_rub"] * 100
        if bad_share >= 1:
            sentences.append(
                f"В кампаниях без окупаемости («плохие», график и таблица ниже) лежит "
                f"{_pct1(bad_share)} всего расхода за период ({_money(bad_spend)}) — "
                f"это тот бюджет, который в первую очередь стоит пересмотреть."
            )

    return '<p class="narrative">' + " ".join(sentences) + "</p>"


# ================================================================ PDF-записка
_PDF_CSS = f"""
    @page {{ size: A4; margin: 16mm 14mm; }}
    @page landscape {{ size: A4 landscape; margin: 14mm 16mm; }}
    .block.landscape {{ page: landscape; }}
    * {{ box-sizing: border-box; }}
    body {{ font-family: "Helvetica Neue", Arial, sans-serif; color: #1f2a24;
            margin: 0; font-size: 10px; }}
    h1 {{ font-size: 18px; color: #{style.NAVY_3}; margin: 0 0 4px; }}
    .period {{ color: #667; font-size: 9.5px; margin: 0 0 16px; line-height: 1.5; }}
    .block {{ margin-bottom: 20px; }}
    .block + .block {{ page-break-before: always; break-before: page; }}
    h2 {{ font-size: 14px; color: #{style.NAVY_3}; border-bottom: 2px solid #{style.NAVY};
          padding-bottom: 4px; margin: 0 0 8px;
          page-break-after: avoid; break-after: avoid; }}
    .kpi-row {{ display: flex; gap: 8px; margin-bottom: 8px;
                page-break-inside: avoid; break-inside: avoid; }}
    .kpi {{ flex: 1; background: #{style.SURFACE_3}; border-radius: 6px; padding: 7px 9px; }}
    .kpi-label {{ font-size: 8.5px; color: #667; text-transform: uppercase; }}
    .kpi-value {{ font-size: 14px; font-weight: 700; color: #{style.NAVY_3}; }}
    .kpi-value .badge {{ margin-left: 6px; vertical-align: middle; }}
    .kpi-sub {{ font-size: 7.8px; color: #889; margin-top: 1px; }}
    .budget-row {{ display: flex; gap: 8px; margin-bottom: 10px;
                   page-break-inside: avoid; break-inside: avoid; }}
    .budget {{ flex: 1; background: #{style.SURFACE_5}; border: 1px solid #{style.LINE};
               border-radius: 6px; padding: 6px 9px; }}
    .budget-label {{ font-size: 8px; color: #778; }}
    .budget-value {{ font-size: 12px; font-weight: 700; color: #{style.NAVY_3}; }}
    .narrative {{ background: #{style.SURFACE_5}; border-left: 3px solid #{style.NAVY};
                  padding: 7px 10px; margin: 0 0 10px; font-size: 9.5px; line-height: 1.5;
                  page-break-inside: avoid; break-inside: avoid; }}
    .drr-scale {{ margin: 0 0 10px; page-break-inside: avoid; break-inside: avoid; }}
    .drr-scale table {{ margin-bottom: 4px; }}
    .drr-scale td, .drr-scale th {{ padding: 3px 6px; }}
    .drr-scale tr.row-good td {{ background: #EBFBEE; }}
    .drr-scale tr.row-warn td {{ background: #FFF8E6; }}
    .drr-scale tr.row-bad td {{ background: #FDECEC; }}
    .top-products tr.row-good td {{ background: #EBFBEE; }}
    .top-products tr.row-warn td {{ background: #FFF8E6; }}
    .top-products tr.row-bad td {{ background: #FDECEC; }}
    .subhead {{ font-size: 10.5px; font-weight: 700; color: #{style.NAVY_3};
                margin: 0 0 5px;
                page-break-after: avoid; break-after: avoid; }}
    .rec-item {{ margin-bottom: 9px; page-break-inside: avoid; break-inside: avoid; }}
    .rec-num {{ display: inline-block; width: 16px; height: 16px; border-radius: 50%;
                background: #{style.NAVY}; color: #fff; font-size: 8.5px; font-weight: 700;
                text-align: center; line-height: 16px; margin-right: 5px; }}
    .rec-title {{ font-weight: 700; color: #{style.NAVY_3}; font-size: 10px; }}
    .rec-text {{ font-size: 9.3px; line-height: 1.5; color: #334; margin: 2px 0 0 21px; }}
    .bar-row {{ display: flex; align-items: center; gap: 6px; margin-bottom: 4px; }}
    .bar-label {{ width: 34%; font-size: 8.7px; overflow: hidden; text-overflow: ellipsis;
                  white-space: nowrap; }}
    .bar-track {{ flex: 1; background: #{style.SURFACE_3}; border-radius: 3px; height: 8px;
                  overflow: hidden; }}
    .bar-fill {{ height: 100%; background: #{style.NAVY}; border-radius: 3px; }}
    .bar-value {{ width: 34%; text-align: right; font-size: 8.5px; color: #445; white-space: nowrap; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 9.5px; table-layout: fixed; }}
    thead {{ display: table-header-group; }}
    tr {{ page-break-inside: avoid; break-inside: avoid; }}
    th {{ background: #{style.NAVY}; color: #fff; text-align: left; padding: 5px 6px; }}
    td {{ padding: 4px 6px; border-bottom: 1px solid #{style.LINE}; overflow: hidden;
          text-overflow: ellipsis; white-space: nowrap; }}
    td.num {{ text-align: right; white-space: nowrap; }}
    td.reason {{ white-space: normal; overflow: visible; text-overflow: clip; line-height: 1.35; }}
    td.name {{ white-space: normal; overflow: visible; text-overflow: clip;
               word-break: break-word; line-height: 1.3; }}
    tr:nth-child(even) td {{ background: #{style.SURFACE_2}; }}
    col.c-num {{ width: 5%; }}
    col.c-name {{ width: 40%; }}
    col.c-name-sm {{ width: 26%; }}
    col.c-status {{ width: 14%; }}
    col.c-brand {{ width: 18%; }}
    col.c-sum {{ width: 15%; }}
    col.c-ops {{ width: 12%; }}
    col.c-pct {{ width: 12%; }}
    col.c-stock {{ width: 9%; }}
    .empty {{ text-align: center; color: #888; padding: 8px; font-size: 9px; }}
    .top-block {{ page-break-inside: avoid; break-inside: avoid; margin-top: 4px; }}
    .footer {{ margin-top: 10px; font-size: 8px; color: #999; }}
    .section-note {{ margin-top: 10px; font-size: 8.5px; color: #999; }}
    .section-error {{ background: #FDECEC; border-left: 3px solid #D03B3B; padding: 7px 10px;
                       font-size: 9px; color: #a33; border-radius: 2px; }}
    .chart-img {{ width: 100%; display: block; margin: 4px 0 10px;
                   page-break-inside: avoid; break-inside: avoid; }}
    .badge {{ display: inline-block; padding: 1px 6px; border-radius: 3px;
               font-size: 8.2px; font-weight: 700; white-space: nowrap; }}
    .badge-good {{ background: #EBFBEE; color: #0CA30C; }}
    .badge-bad {{ background: #FDECEC; color: #D03B3B; }}
    .badge-warn {{ background: #FFF8E6; color: #9A6100; }}
    .badge-unknown {{ background: #{style.SURFACE_3}; color: #889; }}
    .glossary {{ margin-top: 16px; border-top: 1px solid #{style.LINE}; padding-top: 8px; }}
    .glossary-title {{ font-size: 8px; color: #99a; text-transform: uppercase;
                        letter-spacing: 0.03em; margin-bottom: 5px; }}
    .glossary-grid {{ display: flex; flex-wrap: wrap; gap: 3px 16px; }}
    .glossary-item {{ width: 46%; font-size: 7.6px; color: #778; line-height: 1.45; }}
    .glossary-term {{ font-weight: 700; color: #567; }}
"""


def _kpi_html(label: str, value: str, sub: str = "") -> str:
    sub_html = f'<div class="kpi-sub">{_esc(sub)}</div>' if sub else ""
    return f"""
    <div class="kpi">
        <div class="kpi-label">{_esc(label)}</div>
        <div class="kpi-value">{value}</div>
        {sub_html}
    </div>
    """


def _kpi_rows_html(bundle: dict) -> str:
    t = bundle["totals"]
    row1 = "".join([
        _kpi_html("Расход на рекламу", _money(t["spend_rub"])),
        _kpi_html("Выручка от рекламы", _money(t["revenue_rub"])),
        _kpi_html(
            "ДРР",
            _pct1(t["drr"]) + _drr_rating_badge_html(t["drr"]),
            "доля расходов от выручки рекламы¹",
        ),
        _kpi_html("Заказы", _int(t["orders"])),
    ])
    row2 = "".join([
        _kpi_html("Показы", _int(t["views"])),
        _kpi_html("Клики", _int(t["clicks"])),
        _kpi_html("CTR", _pct1(t["ctr"]), "кликабельность¹"),
        _kpi_html("CPC", _money_dec(t["cpc"]), "цена клика¹"),
    ])
    return f'<div class="kpi-row">{row1}</div><div class="kpi-row">{row2}</div>'


def _period_to_date_html(bundle: dict) -> str:
    """Темп расхода с начала недели/месяца/квартала/года -- по
    просьбе Дарьи ("может расходы на рекламу с начала года, квартала
    и месяца и недели"). Форма -- ряд карточек-цифр (как .kpi/.budget
    выше), а не новый график: здесь просто 4 итоговых числа со
    сравнением, а не распределение по времени -- под это график не
    нужен, карточка читается быстрее (см. dataviz: "форма по задаче
    данных")."""
    ptd = bundle.get("period_to_date")
    if not ptd:
        return (
            '<div class="empty">Не удалось посчитать -- остальные разделы отчёта это не затрагивает.</div>'
        )

    def _tile(period: dict) -> str:
        change = period.get("change_pct")
        if change is None:
            sub = "нет данных за сопоставимый прошлый отрезок"
        else:
            arrow = "больше" if change > 0 else ("меньше" if change < 0 else "как и было")
            sub = f"{abs(change):.0f}% {arrow}, чем тогда" if change != 0 else "столько же, сколько тогда"
        return _kpi_html(period["label"], _money(period["spend"]), sub)

    tiles = "".join(_tile(ptd[key]) for key in ("week", "month", "quarter", "year"))

    month = ptd.get("month") or {}
    change = month.get("change_pct")
    narrative = ""
    if change is not None:
        direction = "быстрее" if change > 0 else "медленнее"
        narrative = (
            f'<p class="narrative">С начала месяца реклама тратится {direction}, чем за то же число дней '
            f'прошлого месяца: {_money(month["spend"])} против {_money(month.get("prev_spend") or 0)} тогда '
            f'-- разница {abs(change):.0f}%.</p>'
        )

    as_of = _date(ptd.get("as_of"))
    note = (
        f'<div class="section-note">Расход посчитан с начала недели / месяца / квартала / года по '
        f'{as_of} включительно (дата конца этого отчёта, а не "сегодня"). Сравнение -- с тем же числом дней '
        f'от начала предыдущей недели / месяца / квартала / года соответственно.</div>'
    )
    return f'<div class="kpi-row">{tiles}</div>{narrative}{note}'


def _quality_spend_chart_html(campaigns_df: pd.DataFrame) -> str:
    """Расход на рекламу по классу кампании (хорошая / плохая / мало
    данных) -- один взгляд на то, сколько бюджета вообще лежит в
    кампаниях без окупаемости, ДО того как читатель дойдёт до
    подробных таблиц в разделах ниже. Напрямую иллюстрирует правила
    из _classify_campaign и правило №3-4 в _recommendations."""
    if campaigns_df is None or campaigns_df.empty:
        return ""

    order = ["хорошая", "плохая", "мало данных"]
    colors_map = {"хорошая": C.GOOD, "плохая": C.CRITICAL, "мало данных": C.SERIES_3}
    spend_by_quality = campaigns_df.groupby("quality")["spend_rub"].sum()
    labels = [q for q in order if q in spend_by_quality.index and spend_by_quality[q] > 0]
    if not labels:
        return ""

    values = [spend_by_quality[q] for q in labels]
    chart = _cr_hbar(
        labels=[q[0].upper() + q[1:] for q in labels],
        values=values,
        colors=[colors_map[q] for q in labels],
        axis_label="Расход на рекламу, ₽",
    )
    return _chart_img_html(chart, "Расход по классу кампании")


def _budget_html(balance) -> str:
    if not balance:
        return ""

    if balance.get("error"):
        # Баланс за рекламный счёт сейчас не работает вовсе (запрос на
        # сервере стабильно падает) -- по просьбе Дарьи в отчёте об этом
        # ничего не пишем: раздел просто не появляется, пока это не
        # починится, без изменений кода на будущее (когда баланс снова
        # начнёт приходить, секция сама появится через ветку ниже).
        return ""

    parts = [
        f"""
        <div class="budget">
            <div class="budget-label">Доступно для рекламы (net)¹</div>
            <div class="budget-value">{_money(balance['net'])}</div>
        </div>
        """,
    ]
    if balance.get("bonus"):
        parts.append(f"""
        <div class="budget">
            <div class="budget-label">Бонусы WB¹</div>
            <div class="budget-value">{_money(balance['bonus'])}</div>
        </div>
        """)
    if balance.get("balance"):
        parts.append(f"""
        <div class="budget">
            <div class="budget-label">Баланс (отдельно от net)¹</div>
            <div class="budget-value">{_money(balance['balance'])}</div>
        </div>
        """)
    return f'<div class="budget-row">{"".join(parts)}</div>'


def _recommendations_html(bundle: dict) -> str:
    items = []
    for i, (title, text) in enumerate(_recommendations(bundle), start=1):
        items.append(f"""
        <div class="rec-item">
            <div><span class="rec-num">{i}</span><span class="rec-title">{_esc(title)}</span></div>
            <div class="rec-text">{text}</div>
        </div>
        """)
    return "".join(items)


def _chart_img_html(data_uri: str | None, caption: str = "") -> str:
    """Общая обёртка для любого графика-картинки (matplotlib -> SVG
    data-uri, см. импорт из commercial_review.charts вверху файла).
    Если строить было не из чего -- честная текстовая заметка вместо
    пустой рамки (тот же принцип, что в commercial_review/charts.py:
    функция вернула None -- значит, данных не хватило)."""
    if not data_uri:
        return f'<div class="empty">{_esc(caption or "Недостаточно данных для графика")}</div>'
    return f'<img class="chart-img" src="{data_uri}" alt="{_esc(caption)}">'


def _quality_badge_html(quality: str) -> str:
    css_class = {
        "хорошая": "badge-good",
        "плохая": "badge-bad",
    }.get(quality, "badge-unknown")
    return f'<span class="badge {css_class}">{_esc(quality)}</span>'


def _drr_rating(drr) -> str | None:
    """Личная шкала оценки ДРР Дарьи (DRR_RATING_BANDS) -- None, если
    ДРР посчитать не из чего (нет выручки от рекламы)."""
    if drr is None or (isinstance(drr, float) and pd.isna(drr)):
        return None
    for upper, label in DRR_RATING_BANDS:
        if drr <= upper:
            return label
    return DRR_RATING_WORST_LABEL


def _drr_rating_group(label: str | None) -> str:
    """"good" / "warn" / "bad" по ПОЛОЖЕНИЮ ярлыка в личной шкале
    Дарьи (DRR_RATING_BANDS), а не по конкретному тексту ярлыка --
    шкала в этом отчёте уже дважды менялась (число ступеней и сами
    границы), так что цвет не должен быть завязан на слова "Хорошо"
    или "Проверить" конкретно. Правило: первая половина "хороших"
    ступеней -- зелёная, вторая половина -- жёлтая, а худшая ступень
    (DRR_RATING_WORST_LABEL) -- всегда красная."""
    if label is None:
        return "unknown"
    if label == DRR_RATING_WORST_LABEL:
        return "bad"
    labels = [lbl for _, lbl in DRR_RATING_BANDS]
    if label not in labels:
        return "unknown"
    half = (len(labels) + 1) // 2
    return "good" if labels.index(label) < half else "warn"


_DRR_RATING_BADGE_CLASS = {"good": "badge-good", "warn": "badge-warn", "bad": "badge-bad", "unknown": "badge-unknown"}
_DRR_RATING_ROW_CLASS = {"good": "row-good", "warn": "row-warn", "bad": "row-bad", "unknown": ""}


def _drr_rating_badge_html(drr) -> str:
    label = _drr_rating(drr)
    if label is None:
        return ""
    css_class = _DRR_RATING_BADGE_CLASS[_drr_rating_group(label)]
    return f'<span class="badge {css_class}">{_esc(label)}</span>'


def _drr_rating_bands_with_ranges() -> list[tuple[str, str]]:
    """[(ярлык, текст диапазона)] по DRR_RATING_BANDS -- общий строитель
    для таблицы-легенды в _drr_scale_html и для текстовой сноски в
    глоссарии, чтобы обе версии шкалы всегда были построены по одним и
    тем же границам и не могли разъехаться при правке DRR_RATING_BANDS."""
    rows_data = []
    prev = 0.0
    for upper, label in DRR_RATING_BANDS:
        rng = f"до {upper:.0f}%" if prev == 0 else f"{prev:.0f}–{upper:.0f}%"
        rows_data.append((label, rng))
        prev = upper
    rows_data.append((DRR_RATING_WORST_LABEL, f"выше {prev:.0f}%"))
    return rows_data


def _drr_scale_html() -> str:
    """Компактная таблица-легенда для личной шкалы ДРР -- напечатана
    один раз в "Итогах за период", рядом с самим ДРР, чтобы бейдж
    "Отлично"/"Нормально"/... был понятен без похода в глоссарий.
    Каждая строка окрашена в цвет своей оценки (тот же зелёный/жёлтый/
    красный, что и у бейджа рядом с цифрой ДРР) -- это не просто
    список чисел, а раскрашенный светофор, как и просила Дарья.
    Строится циклом по DRR_RATING_BANDS, а не по жёстко зашитому
    числу строк -- шкала уже дважды меняла число ступеней."""
    rows_data = _drr_rating_bands_with_ranges()

    rows = "".join(
        f'<tr class="{_DRR_RATING_ROW_CLASS[_drr_rating_group(label)]}">'
        f'<td><span class="badge {_DRR_RATING_BADGE_CLASS[_drr_rating_group(label)]}">{_esc(label)}</span></td>'
        f'<td class="num">{_esc(rng)}</td></tr>'
        for label, rng in rows_data
    )
    return f"""
    <div class="drr-scale">
        <div class="subhead">Шкала оценки ДРР -- личный ориентир Дарьи, не общий норматив</div>
        <table>
            <colgroup><col style="width:70%"><col style="width:30%"></colgroup>
            <thead><tr><th>Оценка</th><th>ДРР</th></tr></thead>
            <tbody>{rows}</tbody>
        </table>
        <div class="section-note">
            Ориентир: маржа без учёта рекламы -- {_pct1(PRE_AD_MARGIN_REFERENCE_PCT)}
            (по словам Дарьи, отчёт эту цифру сам не считает). Кампании и недели с ДРР выше
            {_pct1(DRR_HIGH_THRESHOLD)} (оценка «{DRR_RATING_WORST_LABEL}») в остальных разделах
            отчёта уже считаются «плохими» -- см. сноску ¹ в глоссарии.
        </div>
    </div>
    """


def _type_breakdown_html(by_type_df: pd.DataFrame) -> str:
    if by_type_df is None or by_type_df.empty:
        return '<div class="empty">Данных нет</div>'

    top = by_type_df.sort_values("spend_rub", ascending=False).head(TOP_CHART_N)
    chart = _cr_hbar(
        labels=top["type_name"].tolist(),
        values=top["spend_rub"].tolist(),
        axis_label="Расход на рекламу, ₽",
    )
    rows = "".join(
        f"""
        <tr>
            <td>{_esc(r.type_name)}</td>
            <td class="num">{_money(r.spend_rub)}</td>
            <td class="num">{_int(r.orders)}</td>
            <td class="num">{_pct1(r.drr)}</td>
        </tr>
        """
        for r in top.itertuples(index=False)
    )
    table = f"""
    <table>
        <colgroup><col class="c-name"><col class="c-sum"><col class="c-ops"><col class="c-pct"></colgroup>
        <thead><tr><th>Тип размещения</th><th>Расход, ₽</th><th>Заказы</th><th>ДРР</th></tr></thead>
        <tbody>{rows}</tbody>
    </table>
    """
    return _chart_img_html(chart, "По типам кампаний") + table


def _brands_section_html(bundle: dict, top_n: int = TOP_CHART_N, part: str = "all") -> str:
    """Сводка по брендам -- п.1 из списка коллег: "видно, какой бренд
    реклама реально тянет, а какой просто жрёт бюджет". part -- см.
    докстринг _campaigns_quality_section_html: та же схема разделения
    заголовок+график / таблица, чтобы график не резался переносом
    страницы."""
    brands_df = bundle.get("brands")
    if brands_df is None or brands_df.empty:
        msg = '<div class="empty">Данных по брендам нет (не найден бренд ни у одного товара из рекламы)</div>'
        return msg if part != "table" else ""

    top = brands_df.sort_values("spend_rub", ascending=False).head(top_n)
    chart = _cr_hbar(
        labels=top["brand"].tolist(),
        values=top["spend_rub"].tolist(),
        axis_label="Расход на рекламу, ₽",
    )
    if part == "chart":
        return _chart_img_html(chart, "По брендам")

    rows = "".join(
        f"""
        <tr>
            <td class="num">{i + 1}</td>
            <td class="name">{_esc(r.brand)}</td>
            <td class="num">{_money(r.spend_rub)}</td>
            <td class="num">{_int(r.orders)}</td>
            <td class="num">{_money(r.revenue_rub)}</td>
            <td class="num">{_pct1(r.drr)}</td>
        </tr>
        """
        for i, r in enumerate(top.itertuples(index=False))
    )
    table = f"""
    <table>
        <colgroup><col class="c-num"><col class="c-name"><col class="c-sum">
                  <col class="c-ops"><col class="c-sum"><col class="c-pct"></colgroup>
        <thead><tr><th>#</th><th>Бренд</th><th>Расход, ₽</th><th>Заказы</th>
                   <th>Выручка от рекламы, ₽</th><th>ДРР</th></tr></thead>
        <tbody>{rows}</tbody>
    </table>
    """
    if part == "table":
        return table
    return _chart_img_html(chart, "По брендам") + table


def _brands_narrative_html(bundle: dict) -> str:
    """Короткие выводы по разделу "Сводка по брендам" -- раньше там
    были только график и таблица без единого слова текста. Заодно
    честно объясняем частый вопрос по этой таблице: почему у бренда
    может быть расход 0 ₽, но при этом есть заказы и выручка (см.
    ниже) -- это не ошибка сборки отчёта, а особенность того, как WB
    атрибутирует заказы рекламе."""
    brands_df = bundle.get("brands")
    if brands_df is None or brands_df.empty:
        return ""

    sentences = []
    with_spend = brands_df[brands_df["spend_rub"] > 0]
    if not with_spend.empty:
        top = with_spend.loc[with_spend["spend_rub"].idxmax()]
        sentences.append(
            f"Больше всего тратит на рекламу бренд «{_esc(top['brand'])}» — {_money(top['spend_rub'])} "
            f"при ДРР {_pct1(top['drr'])}."
        )
        if with_spend["drr"].notna().any():
            best = with_spend.loc[with_spend["drr"].idxmin()]
            if best["brand"] != top["brand"]:
                sentences.append(
                    f"Эффективнее всех расходует бюджет «{_esc(best['brand'])}» — ДРР всего "
                    f"{_pct1(best['drr'])}: стоит присмотреться, можно ли отдать этому бренду "
                    f"больше бюджета."
                )

    zero_spend = brands_df[(brands_df["spend_rub"] == 0) & (brands_df["orders"] > 0)]
    if not zero_spend.empty:
        names = ", ".join(f"«{_esc(b)}»" for b in zero_spend["brand"].head(4))
        sentences.append(
            f"У {names} расход на рекламу за период — 0 ₽, но заказы и выручка есть: это не "
            f"ошибка. WB иногда относит заказ на рекламу, даже если прямого расхода именно на "
            f"этот товар не было -- например, если его добавили в корзину вместе с рекламируемым "
            f"товаром в той же сессии, или расход в автоматической кампании считался по кампании "
            f"в целом, а не по каждому товару отдельно. ДРР 0.0% в этих строках не значит "
            f"«бесплатная реклама» — значит «расход не относится именно к этому товару»."
        )

    if not sentences:
        return ""
    return '<p class="narrative">' + " ".join(sentences) + "</p>"


def _weekly_section_html(bundle: dict) -> str:
    """Динамика по неделям -- п. "по неделям: видно динамику,
    всплески, просадки" из списка коллег. Два отдельных графика
    (расход и ДРР), не один с двумя осями -- см. правило "одна ось"."""
    weekly_df = bundle.get("weekly")
    if weekly_df is None or weekly_df.empty:
        return '<div class="empty">Данных нет</div>'

    spike = bundle.get("weekly_spike")

    labels = weekly_df["week_label"].tolist()
    spend_values = weekly_df["spend_rub"].tolist()
    x = list(range(len(labels)))

    fig, ax = _cr_fig(height=2.3)
    colors = [C.CRITICAL if spike and lbl == spike["label"] else C.SERIES_1 for lbl in labels]
    ax.bar(x, spend_values, width=0.6, color=colors, linewidth=0)
    for i, v in enumerate(spend_values):
        ax.annotate(_cr_short(v), xy=(x[i], v), xytext=(0, 3), textcoords="offset points",
                    ha="center", fontsize=7.0, fontweight="bold", color=C.INK)
    if spike:
        spike_i = labels.index(spike["label"])
        ax.annotate(
            f"пик: +{_cr_pct_label(100 * (spike['ratio'] - 1), 0)} к среднему по остальным неделям",
            xy=(x[spike_i], spend_values[spike_i]), xytext=(0, 17), textcoords="offset points",
            ha="center", fontsize=7.0, fontweight="bold", color=C.CRITICAL,
            arrowprops=dict(arrowstyle="-", color=C.CRITICAL, linewidth=0.8, shrinkA=0, shrinkB=2),
        )
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=7.0)
    ax.set_xlim(-0.6, len(labels) - 0.4)
    ax.yaxis.set_major_formatter(_cr_money_formatter())
    ax.set_ylabel("Расход на рекламу, ₽")
    ymax = max(spend_values) if spend_values else 0
    ax.set_ylim(0, ymax * 1.3 if ymax else 1)
    spend_chart = _cr_render(fig)

    drr_data = weekly_df[weekly_df["drr"].notna()]
    drr_chart = None
    if len(drr_data) >= 2:
        d_labels = drr_data["week_label"].tolist()
        d_values = drr_data["drr"].tolist()
        dx = list(range(len(d_labels)))
        fig2, ax2 = _cr_fig(height=1.8)
        d_colors = [C.WARNING if v > DRR_HIGH_THRESHOLD else C.SERIES_1 for v in d_values]
        ax2.bar(dx, d_values, width=0.55, color=d_colors, linewidth=0)
        for i, v in enumerate(d_values):
            ax2.annotate(_cr_pct_label(v, 1), xy=(dx[i], v), xytext=(0, 3), textcoords="offset points",
                         ha="center", fontsize=7.0, fontweight="bold", color=C.INK)
        ax2.axhline(DRR_HIGH_THRESHOLD, color=C.AXIS, linewidth=0.7, linestyle=(0, (3, 2)))
        ax2.set_xticks(dx)
        ax2.set_xticklabels(d_labels, fontsize=7.0)
        ax2.set_xlim(-0.6, len(d_labels) - 0.4)
        ax2.yaxis.set_major_formatter(_cr_pct_formatter(1))
        ax2.set_ylabel("ДРР, %")
        d_ymax = max(d_values) if d_values else 0
        ax2.set_ylim(0, max(d_ymax * 1.3, DRR_HIGH_THRESHOLD * 1.3))
        drr_chart = _cr_render(fig2)

    parts = [_chart_img_html(spend_chart, "Расход по неделям")]
    if drr_chart:
        parts.append(
            f'<div class="subhead" style="margin-top:10px;">ДРР по неделям '
            f'(пунктир -- порог {_pct1(DRR_HIGH_THRESHOLD)}, выше него неделя подсвечена)</div>'
        )
        parts.append(_chart_img_html(drr_chart, "ДРР по неделям"))
    return "".join(parts)


def _quality_counts_note(campaigns_df: pd.DataFrame) -> str:
    """Раньше каждая секция ("хорошие"/"плохие") показывала только
    СВОЙ счётчик ("хорошая: 46 из 48") -- и было не видно, что
    случилось с остальными 2: то ли они "плохие", то ли просто "мало
    данных". Теперь показываем все три числа вместе и в той, и в
    другой секции, чтобы сумма всегда сходилась на виду."""
    counts = campaigns_df["quality"].value_counts()
    total = len(campaigns_df)
    parts = ", ".join(
        f"{label}: {int(counts.get(label, 0))}"
        for label in ("хорошая", "плохая", "мало данных")
    )
    return (
        f'<div class="section-note">Всего кампаний за период: {total} -- {parts}. '
        f'Как считаем -- см. сноску ¹ в глоссарии в конце записки.</div>'
    )


def _campaigns_quality_section_html(
    campaigns_df: pd.DataFrame, quality: str, top_n: int = TOP_CHART_N, part: str = "all"
) -> str:
    """Таблица + график по кампаниям одного класса ("хорошая" / "плохая")
    -- п.4-5 из списка коллег.

    part управляет тем, какой кусок вернуть -- "chart" (заголовок уже
    печатает вызывающий код, здесь только картинка), "table" (таблица
    + примечание про счётчики) или "all" (как раньше, всё вместе).
    Разделение нужно, чтобы в PDF можно было держать вместе только
    заголовок+график (маленький, стабильно влезает на страницу) и
    отдельно от него -- таблицу, которой разрешено переноситься на
    следующую страницу самой, без утаскивания графика за собой
    (см. .top-block в _PDF_CSS и как это используется в
    build_ad_campaigns_html)."""
    if campaigns_df is None or campaigns_df.empty:
        msg = '<div class="empty">Операций за период нет</div>'
        return msg if part != "table" else ""

    counts_note = _quality_counts_note(campaigns_df)
    subset = campaigns_df[campaigns_df["quality"] == quality]
    if subset.empty:
        good_msg = "Ни одна кампания пока не набрала достаточно данных, чтобы уверенно назвать её хорошей."
        bad_msg = "Явно убыточных кампаний (с заметным расходом и без окупаемости) за период не найдено -- хороший знак."
        msg = f'<div class="empty">{good_msg if quality == "хорошая" else bad_msg}</div>'
        if part == "chart":
            return msg
        if part == "table":
            return counts_note
        return msg + counts_note

    sort_col = "revenue_rub" if quality == "хорошая" else "spend_rub"
    top = subset.sort_values(sort_col, ascending=False).head(top_n)

    chart = _cr_hbar(
        labels=top["name"].tolist(),
        values=top["spend_rub"].tolist(),
        colors=[C.GOOD if quality == "хорошая" else C.CRITICAL] * len(top),
        axis_label="Расход на рекламу, ₽",
    )
    chart_html = _chart_img_html(chart, f"Кампании: {quality}")
    if part == "chart":
        return chart_html

    is_bad = quality != "хорошая"

    reason_cell = (
        lambda r: f'<td class="reason">{_esc(_bad_campaign_reason(r.spend_rub, r.orders, r.revenue_rub, r.drr))}</td>'
        if is_bad else ""
    )

    rows = "".join(
        f"""
        <tr>
            <td class="num">{i + 1}</td>
            <td class="name">{_esc(r.name)}</td>
            <td>{_esc(r.status_name)}</td>
            <td class="num">{_money(r.spend_rub)}</td>
            <td class="num">{_int(r.orders)}</td>
            <td class="num">{_money(r.revenue_rub)}</td>
            <td class="num">{_pct1(r.drr)}</td>
            {reason_cell(r)}
        </tr>
        """
        for i, r in enumerate(top.itertuples(index=False))
    )
    # ширины колонок считаем инлайново (а не общими col.c-* классами) --
    # у этой таблицы своя раскладка (статус+причина), и делить классы
    # с другими таблицами отчёта было бы риском случайно сломать им
    # пропорции. "Начало"/"Конец" по просьбе Дарьи убраны -- статус
    # WB и так показывает, активна кампания или нет, а даты только
    # захламляли таблицу.
    name_w = 26 if is_bad else 51
    reason_col = '<col style="width:25%">' if is_bad else ""
    reason_th = "<th>Почему плохая</th>" if is_bad else ""
    table = f"""
    <table>
        <colgroup>
            <col style="width:3%"><col style="width:{name_w}%"><col style="width:10%">
            <col style="width:11%"><col style="width:7%"><col style="width:11%"><col style="width:7%">
            {reason_col}
        </colgroup>
        <thead><tr><th>#</th><th>Кампания</th><th>Статус WB</th>
                   <th>Расход, ₽</th><th>Заказы</th>
                   <th>Выручка от рекламы, ₽</th><th>ДРР</th>{reason_th}</tr></thead>
        <tbody>{rows}</tbody>
    </table>
    """
    if part == "table":
        return table + counts_note
    return chart_html + table + counts_note


def _campaigns_table_html(campaigns_df: pd.DataFrame, top_n: int = TOP_CAMPAIGNS_N) -> str:
    if campaigns_df is None or campaigns_df.empty:
        return '<div class="empty">Операций за период нет</div>'

    top = campaigns_df.sort_values("spend_rub", ascending=False).head(top_n)
    rows = "".join(
        f"""
        <tr>
            <td class="num">{i + 1}</td>
            <td class="name">{_esc(r.name)}</td>
            <td>{_esc(r.status_name)}</td>
            <td>{_quality_badge_html(r.quality)}</td>
            <td class="num">{_money(r.spend_rub)}</td>
            <td class="num">{_int(r.orders)}</td>
            <td class="num">{_pct1(r.drr)}</td>
        </tr>
        """
        for i, r in enumerate(top.itertuples(index=False))
    )
    return f"""
    <table>
        <colgroup>
            <col style="width:3%"><col style="width:33%"><col style="width:14%"><col style="width:12%">
            <col style="width:14%"><col style="width:12%"><col style="width:12%">
        </colgroup>
        <thead>
            <tr><th>#</th><th>Кампания</th><th>Статус WB</th><th>Оценка¹</th>
                <th>Расход, ₽</th><th>Заказы</th><th>ДРР</th></tr>
        </thead>
        <tbody>{rows}</tbody>
    </table>
    """


def _stock_flag_html(stock_qty) -> str:
    if stock_qty is None or (isinstance(stock_qty, float) and pd.isna(stock_qty)):
        return '<span class="badge badge-unknown">нет данных</span>'
    qty = int(stock_qty)
    if qty <= 0:
        return f'<span class="badge badge-bad">0 шт -- остатка нет!</span>'
    if qty < LOW_STOCK_QTY_THRESHOLD:
        return f'<span class="badge badge-warn">{qty} шт -- заканчивается</span>'
    return f'{qty} шт'


def _products_table_html(products_df: pd.DataFrame, top_n: int = TOP_PRODUCTS_N) -> str:
    """Маржу от рекламы (оценку по последней закупочной цене) убрали
    из отчёта по просьбе Дарьи -- оценочная цифра выглядела как
    точная и путала. Строки подсвечены по личной шкале оценки ДРР
    (DRR_RATING_BANDS/_drr_rating_group) -- тот же зелёный/жёлтый/
    красный, что и в легенде "Итогов за период" и у бейджа рядом с
    ДРР-KPI, чтобы самые дорогие и при этом неэффективные товары были
    видны с первого взгляда, не читая колонку ДРР построчно."""
    if products_df is None or products_df.empty:
        return '<div class="empty">Операций за период нет</div>'

    top = products_df.sort_values("spend_rub", ascending=False).head(top_n)
    rows = "".join(
        f"""
        <tr class="{_DRR_RATING_ROW_CLASS[_drr_rating_group(_drr_rating(r.drr))]}">
            <td class="num">{i + 1}</td>
            <td class="num">{int(r.nm_id)}</td>
            <td class="name">{_esc(r.title)}</td>
            <td>{_esc(r.brand)}</td>
            <td class="num">{_money(r.spend_rub)}</td>
            <td class="num">{_int(r.orders)}</td>
            <td class="num">{_pct1(r.drr)}</td>
            <td>{_stock_flag_html(r.stock_qty)}</td>
        </tr>
        """
        for i, r in enumerate(top.itertuples(index=False))
    )
    return f"""
    <div class="top-products">
        <table>
            <colgroup>
                <col style="width:3%"><col style="width:10%"><col style="width:27%"><col style="width:14%">
                <col style="width:12%"><col style="width:9%"><col style="width:9%">
                <col style="width:16%">
            </colgroup>
            <thead>
                <tr><th>#</th><th>nm_id</th><th>Товар</th><th>Бренд</th>
                    <th>Расход, ₽</th><th>Заказы</th><th>ДРР³</th>
                    <th>Остаток²</th></tr>
            </thead>
            <tbody>{rows}</tbody>
        </table>
        <div class="section-note">Строка подсвечена по личной шкале оценки ДРР -- см. "Итоги за период" выше или сноску ³ в глоссарии.</div>
    </div>
    """


# _daily_trend_html (CSS-полоски по дням) убран из PDF-записки --
# "Динамика по неделям" (_weekly_section_html, настоящие графики)
# теперь закрывает ту же задачу компактнее, по просьбе Дарьи не
# делать записку слишком объёмной. Помесячный/понедельный разрез
# по-прежнему весь доступен в Excel-детализации без урезки.


_GLOSSARY = [
    ("Показы", "сколько раз объявление увидели покупатели."),
    ("Клики", "сколько раз по объявлению кликнули."),
    ("CTR (кликабельность)", "доля показов, ставших кликом: клики ÷ показы × 100%."),
    ("CPC (цена клика)", "сколько в среднем стоил один клик: расход ÷ клики."),
    ("Корзины (ATBS)", "сколько раз товар из рекламы добавили в корзину."),
    ("Заказы", "сколько заказов оформили после клика по рекламе (в пределах окна учёта WB)."),
    ("Отменённые", "сколько из этих заказов затем отменили."),
    ("CR (конверсия)", "доля кликов, ставших заказом: заказы ÷ клики × 100%."),
    ("ДРР (доля рекламных расходов)", "сколько процентов от выручки, которую принесла реклама, "
        "ушло на саму рекламу: расход ÷ выручка × 100%. Чем меньше — тем выгоднее реклама."),
    ("¹ Оценка кампании", f"потратила меньше {_money(CAMPAIGN_MIN_SPEND_TO_JUDGE)} -- «мало данных», рано судить. "
        f"Потратила больше, но не принесла ни одного заказа -- «плохая» сразу. Принесла хоть один заказ, но "
        f"меньше {int(CAMPAIGN_MIN_ORDERS_TO_JUDGE)} -- снова «мало данных» (слишком маленькая выборка для ДРР). "
        f"От {int(CAMPAIGN_MIN_ORDERS_TO_JUDGE)} заказов и больше -- «хорошая» при ДРР до "
        f"{_pct1(DRR_HIGH_THRESHOLD)} включительно, иначе «плохая»."),
    ("² Остаток", "сколько штук товара сейчас есть на складе WB и в FBS вместе. Если он маленький "
        "или нулевой, а реклама на товар продолжает литься -- бюджет рискует уйти впустую: товар "
        "может закончиться раньше, чем окупится показ."),
    ("³ Оценка ДРР товара", "строка в таблице товаров подсвечена по личной шкале Дарьи: " + ", ".join(
        f"«{label}» -- {rng}" for label, rng in _drr_rating_bands_with_ranges()
    ) + ". Подробнее и с объяснением ориентира -- в разделе «Итоги за период»."),
]


def _glossary_html() -> str:
    items = "".join(
        f'<div class="glossary-item"><span class="glossary-term">{_esc(term)}</span> — {_esc(text)}</div>'
        for term, text in _GLOSSARY
    )
    return f"""
    <div class="glossary">
        <div class="glossary-title">¹ Пояснения к терминам</div>
        <div class="glossary-grid">{items}</div>
    </div>
    """


def _safe_section_html(builder, *args, **kwargs) -> str:
    """Один раздел не должен ронять всю записку -- тот же приём
    (и по той же причине), что и _safe в commercial_review/report.py:
    при ошибке -- честная заметка с типом ошибки вместо пустой или
    битой PDF-страницы, а остальные разделы собираются как обычно."""
    try:
        return builder(*args, **kwargs)
    except Exception as exc:
        logger.exception("Не собрался раздел записки по рекламе (%s)", getattr(builder, "__name__", builder))
        return (
            f'<div class="section-error">Раздел не собрался: '
            f'{_esc(type(exc).__name__)}: {_esc(str(exc))[:200]}. '
            f'Остальные разделы отчёта это не затронуло.</div>'
        )


def build_ad_campaigns_html(bundle: dict) -> str:
    period_label = _period_label(bundle["start_date"], bundle["end_date"])
    data_as_of = bundle.get("data_as_of")
    freshness_html = (
        f" Данные загружены по {_esc(data_as_of)} включительно."
        if data_as_of
        else ' <span style="color:#c33;">Не удалось определить, на какую дату загружены данные -- '
             "проверьте, что сборщик на сервере запускался в последние дни.</span>"
    )

    stocks_as_of = bundle.get("stocks_as_of")
    if bundle.get("stocks_available"):
        as_of_part = f" Остаток показан по последним доступным данным -- на {_esc(stocks_as_of)}." if stocks_as_of else ""
        stock_note = f'<div class="section-note">Остаток -- WB-склад + FBS.{as_of_part} Дата остатка может не совпадать с периодом отчёта -- это нормально, берём последний известный снимок.</div>'
    else:
        stock_note = (
            '<div class="section-note">Остатки сейчас недоступны -- колонка "Остаток" показывает "нет данных", '
            "остальные цифры в таблице это не затрагивает.</div>"
        )

    body = f"""
    <section class="block">
        <h2>Итоги за период</h2>
        {_safe_section_html(_kpi_rows_html, bundle)}
        {_safe_section_html(_budget_html, bundle["balance"])}
        {_safe_section_html(_narrative_html, bundle)}
        {_safe_section_html(_drr_scale_html)}
        {_safe_section_html(_quality_spend_chart_html, bundle["campaigns"])}
        <div class="section-note">{_esc(period_label)}</div>
    </section>

    <section class="block">
        <h2>Темп расходов: неделя, месяц, квартал, год</h2>
        <div class="subhead">Сколько уже потрачено с начала каждого отрезка и быстрее или медленнее, чем на том же отрезке времени в предыдущем аналогичном периоде</div>
        {_safe_section_html(_period_to_date_html, bundle)}
    </section>

    <section class="block">
        <h2>Выводы и рекомендации</h2>
        {_safe_section_html(_recommendations_html, bundle)}
    </section>

    <section class="block">
        <h2>Динамика по неделям</h2>
        <div class="subhead">Расход на рекламу и ДРР по неделям -- видно рост, просадки и всплески расхода</div>
        {_safe_section_html(_weekly_section_html, bundle)}
    </section>

    <section class="block">
        <div class="top-block">
            <h2>Сводка по брендам</h2>
            <div class="subhead">Какой бренд реклама реально тянет, а какой просто ест бюджет</div>
            {_safe_section_html(_brands_section_html, bundle, part="chart")}
        </div>
        {_safe_section_html(_brands_section_html, bundle, part="table")}
        {_safe_section_html(_brands_narrative_html, bundle)}
    </section>

    <section class="block">
        <h2>По типам кампаний</h2>
        <div class="subhead">Расход и отдача по типу размещения (каталог, поиск, автоматическая, аукцион и т.п.)</div>
        {_safe_section_html(_type_breakdown_html, bundle["by_type"])}
    </section>

    <section class="block landscape">
        <div class="top-block">
            <h2>Хорошие кампании</h2>
            <div class="subhead">Окупаются с запасом -- кандидаты на масштабирование</div>
            {_safe_section_html(_campaigns_quality_section_html, bundle["campaigns"], "хорошая", part="chart")}
        </div>
        {_safe_section_html(_campaigns_quality_section_html, bundle["campaigns"], "хорошая", part="table")}
    </section>

    <section class="block landscape">
        <div class="top-block">
            <h2>Плохие кампании</h2>
            <div class="subhead">Тратят заметно, а окупаемости нет -- кандидаты на отключение (показаны и уже завершённые: деньги потрачены в любом случае, разбор одинаковый)</div>
            {_safe_section_html(_campaigns_quality_section_html, bundle["campaigns"], "плохая", part="chart")}
        </div>
        {_safe_section_html(_campaigns_quality_section_html, bundle["campaigns"], "плохая", part="table")}
    </section>

    <section class="block landscape">
        <h2>Топ-{TOP_CAMPAIGNS_N} кампаний по расходу</h2>
        {_safe_section_html(_campaigns_table_html, bundle["campaigns"])}
    </section>

    <section class="block landscape">
        <h2>Топ-{TOP_PRODUCTS_N} товаров по расходу на рекламу</h2>
        {_safe_section_html(_products_table_html, bundle["products"])}
        {stock_note}
        {_glossary_html()}
    </section>
    """

    return f"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<title>Анализ рекламных кампаний -- записка</title>
<style>{_PDF_CSS}</style>
</head>
<body>
<h1>Анализ рекламных кампаний WB</h1>
<p class="period">{_esc(period_label)} · данные и атрибуция заказов -- по статистике WB Продвижение.{freshness_html}</p>
{body}
<div class="footer">Сформировано {datetime.now():%d.%m.%Y %H:%M}</div>
</body>
</html>
"""


def build_ad_campaigns_pdf(bundle: dict) -> bytes:
    try:
        from weasyprint import HTML
    except ImportError as exc:
        raise RuntimeError(
            "Для PDF установите WeasyPrint: pip install weasyprint"
        ) from exc

    buffer = BytesIO()
    HTML(string=build_ad_campaigns_html(bundle)).write_pdf(buffer)
    return buffer.getvalue()


def build_ad_campaigns_pdf_bytes(start_date: str, end_date: str) -> bytes:
    bundle = _fetch_report_bundle(start_date, end_date)
    return build_ad_campaigns_pdf(bundle)


# ================================================================ Excel-детализация
CAMPAIGNS_HEADERS = [
    "advert_id", "Название", "Тип", "Статус", "Способ оплаты",
    "Показы", "Клики", "CTR, %", "CPC, ₽", "Расход, ₽",
    "Корзины", "Заказы", "CR, %", "Штук", "Выручка, ₽", "Отменено", "ДРР, %",
]

PRODUCTS_HEADERS = [
    "nm_id", "Наименование", "Бренд", "Категория", "Остаток",
    "Показы", "Клики", "CTR, %", "CPC, ₽", "Расход, ₽",
    "Корзины", "Заказы", "CR, %", "Штук", "Выручка, ₽", "Отменено", "ДРР, %",
]

DAILY_HEADERS = [
    "Дата", "Показы", "Клики", "CTR, %", "CPC, ₽", "Расход, ₽",
    "Корзины", "Заказы", "CR, %", "Штук", "Выручка, ₽", "Отменено", "ДРР, %",
]


def _write_campaigns_sheet(wb, title, subtitle, params, campaigns_df):
    ws = wb.create_sheet("Кампании")
    col_end = len(CAMPAIGNS_HEADERS)
    header_row = style.write_sheet_header(ws, title, subtitle, params, col_end, landscape=True)
    style.write_table_header(ws, header_row, 1, CAMPAIGNS_HEADERS)

    row = header_row + 1
    first_data_row = row
    numeric_cols = tuple(range(6, col_end + 1))
    formats = {
        6: style.FMT_QTY, 7: style.FMT_QTY, 8: style.FMT_PCT, 9: style.FMT_MONEY_DEC,
        10: style.FMT_MONEY, 11: style.FMT_QTY, 12: style.FMT_QTY, 13: style.FMT_PCT,
        14: style.FMT_QTY, 15: style.FMT_MONEY, 16: style.FMT_QTY, 17: style.FMT_PCT,
    }

    sub = campaigns_df.sort_values("spend_rub", ascending=False) if not campaigns_df.empty else campaigns_df
    for _, r in sub.iterrows():
        ws.cell(row=row, column=1, value=int(r["advert_id"]))
        ws.cell(row=row, column=2, value=r["name"])
        ws.cell(row=row, column=3, value=r["type_name"])
        ws.cell(row=row, column=4, value=r["status_name"])
        ws.cell(row=row, column=5, value=r["payment_type"])
        ws.cell(row=row, column=6, value=int(r["views"]))
        ws.cell(row=row, column=7, value=int(r["clicks"]))
        ws.cell(row=row, column=8, value=round(float(r["ctr"]), 2))
        ws.cell(row=row, column=9, value=round(float(r["cpc"]), 2))
        ws.cell(row=row, column=10, value=round(float(r["spend_rub"]), 2))
        ws.cell(row=row, column=11, value=int(r["atbs"]))
        ws.cell(row=row, column=12, value=int(r["orders"]))
        ws.cell(row=row, column=13, value=round(float(r["cr"]), 2))
        ws.cell(row=row, column=14, value=int(r["shks"]))
        ws.cell(row=row, column=15, value=round(float(r["revenue_rub"]), 2))
        ws.cell(row=row, column=16, value=int(r["canceled"]))
        ws.cell(row=row, column=17, value=round(float(r["drr"]), 2) if pd.notna(r["drr"]) else None)

        style.style_data_row(ws, row, 1, col_end, numeric_cols=numeric_cols, formats=formats)
        row += 1

    last_row = max(row - 1, first_data_row)
    if campaigns_df.empty:
        ws.cell(row=row, column=1, value="Нет операций за выбранный период")
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=col_end)
        last_row = row

    style.apply_zebra(ws, first_data_row, last_row, 1, col_end)
    style.apply_column_dividers(ws, header_row, last_row, 1, col_end)
    style.apply_column_widths(
        ws,
        {
            "advert_id": 12, "Название": 38, "Тип": 22, "Статус": 14, "Способ оплаты": 16,
            "Показы": 12, "Клики": 10, "CTR, %": 10, "CPC, ₽": 10, "Расход, ₽": 14,
            "Корзины": 10, "Заказы": 10, "CR, %": 9, "Штук": 9, "Выручка, ₽": 14,
            "Отменено": 10, "ДРР, %": 9,
        },
        header_row,
    )
    # первые 2 колонки (advert_id + Название) -- по просьбе Дарьи.
    style.freeze_table(ws, header_row, first_col=3)
    if not campaigns_df.empty:
        style.enable_autofilter(ws, header_row, 1, col_end, last_row)

    return ws


def _write_products_sheet(wb, title, subtitle, params, products_df):
    ws = wb.create_sheet("По товарам")
    col_end = len(PRODUCTS_HEADERS)
    header_row = style.write_sheet_header(ws, title, subtitle, params, col_end, landscape=True)
    style.write_table_header(ws, header_row, 1, PRODUCTS_HEADERS)

    row = header_row + 1
    first_data_row = row
    numeric_cols = tuple(range(5, col_end + 1))
    formats = {
        5: style.FMT_QTY, 6: style.FMT_QTY, 7: style.FMT_QTY, 8: style.FMT_PCT,
        9: style.FMT_MONEY_DEC, 10: style.FMT_MONEY, 11: style.FMT_QTY, 12: style.FMT_QTY,
        13: style.FMT_PCT, 14: style.FMT_QTY, 15: style.FMT_MONEY, 16: style.FMT_QTY,
        17: style.FMT_PCT,
    }

    sub = products_df.sort_values("spend_rub", ascending=False) if not products_df.empty else products_df
    for _, r in sub.iterrows():
        ws.cell(row=row, column=1, value=int(r["nm_id"]))
        ws.cell(row=row, column=2, value=r["title"])
        ws.cell(row=row, column=3, value=r["brand"])
        ws.cell(row=row, column=4, value=r["category"])
        ws.cell(row=row, column=5, value=int(r["stock_qty"]) if pd.notna(r.get("stock_qty")) else None)
        ws.cell(row=row, column=6, value=int(r["views"]))
        ws.cell(row=row, column=7, value=int(r["clicks"]))
        ws.cell(row=row, column=8, value=round(float(r["ctr"]), 2))
        ws.cell(row=row, column=9, value=round(float(r["cpc"]), 2))
        ws.cell(row=row, column=10, value=round(float(r["spend_rub"]), 2))
        ws.cell(row=row, column=11, value=int(r["atbs"]))
        ws.cell(row=row, column=12, value=int(r["orders"]))
        ws.cell(row=row, column=13, value=round(float(r["cr"]), 2))
        ws.cell(row=row, column=14, value=int(r["shks"]))
        ws.cell(row=row, column=15, value=round(float(r["revenue_rub"]), 2))
        ws.cell(row=row, column=16, value=int(r["canceled"]))
        ws.cell(row=row, column=17, value=round(float(r["drr"]), 2) if pd.notna(r["drr"]) else None)

        style.style_data_row(ws, row, 1, col_end, numeric_cols=numeric_cols, formats=formats)
        row += 1

    last_row = max(row - 1, first_data_row)
    if products_df.empty:
        ws.cell(row=row, column=1, value="Нет операций за выбранный период")
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=col_end)
        last_row = row

    style.apply_zebra(ws, first_data_row, last_row, 1, col_end)
    style.apply_column_dividers(ws, header_row, last_row, 1, col_end)
    style.apply_column_widths(
        ws,
        {
            "nm_id": 12, "Наименование": 38, "Бренд": 16, "Категория": 22, "Остаток": 10,
            "Показы": 12, "Клики": 10, "CTR, %": 10, "CPC, ₽": 10, "Расход, ₽": 14,
            "Корзины": 10, "Заказы": 10, "CR, %": 9, "Штук": 9, "Выручка, ₽": 14,
            "Отменено": 10, "ДРР, %": 9,
        },
        header_row,
    )
    # первые 2 колонки (nm_id + Наименование), а не только nm_id -- по
    # просьбе Дарьи: с ID без названия таблица неудобно листать вбок.
    style.freeze_table(ws, header_row, first_col=3)
    if not products_df.empty:
        style.enable_autofilter(ws, header_row, 1, col_end, last_row)

    return ws


def _write_daily_sheet(wb, title, subtitle, params, daily_df):
    ws = wb.create_sheet("По дням")
    col_end = len(DAILY_HEADERS)
    header_row = style.write_sheet_header(ws, title, subtitle, params, col_end, landscape=False)
    style.write_table_header(ws, header_row, 1, DAILY_HEADERS)

    row = header_row + 1
    first_data_row = row
    numeric_cols = tuple(range(2, col_end + 1))
    formats = {
        2: style.FMT_QTY, 3: style.FMT_QTY, 4: style.FMT_PCT, 5: style.FMT_MONEY_DEC,
        6: style.FMT_MONEY, 7: style.FMT_QTY, 8: style.FMT_QTY, 9: style.FMT_PCT,
        10: style.FMT_QTY, 11: style.FMT_MONEY, 12: style.FMT_QTY, 13: style.FMT_PCT,
    }

    sub = daily_df.sort_values("date") if not daily_df.empty else daily_df
    for _, r in sub.iterrows():
        ws.cell(row=row, column=1, value=r["date"])
        ws.cell(row=row, column=1).number_format = style.FMT_DATE
        ws.cell(row=row, column=2, value=int(r["views"]))
        ws.cell(row=row, column=3, value=int(r["clicks"]))
        ws.cell(row=row, column=4, value=round(float(r["ctr"]), 2))
        ws.cell(row=row, column=5, value=round(float(r["cpc"]), 2))
        ws.cell(row=row, column=6, value=round(float(r["spend_rub"]), 2))
        ws.cell(row=row, column=7, value=int(r["atbs"]))
        ws.cell(row=row, column=8, value=int(r["orders"]))
        ws.cell(row=row, column=9, value=round(float(r["cr"]), 2))
        ws.cell(row=row, column=10, value=int(r["shks"]))
        ws.cell(row=row, column=11, value=round(float(r["revenue_rub"]), 2))
        ws.cell(row=row, column=12, value=int(r["canceled"]))
        ws.cell(row=row, column=13, value=round(float(r["drr"]), 2) if pd.notna(r["drr"]) else None)

        style.style_data_row(ws, row, 1, col_end, numeric_cols=numeric_cols, formats=formats)
        row += 1

    last_row = max(row - 1, first_data_row)
    if daily_df.empty:
        ws.cell(row=row, column=1, value="Нет операций за выбранный период")
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=col_end)
        last_row = row

    style.apply_zebra(ws, first_data_row, last_row, 1, col_end)
    style.apply_column_dividers(ws, header_row, last_row, 1, col_end)
    style.apply_column_widths(ws, {"Дата": 12}, header_row)
    style.freeze_table(ws, header_row, first_col=2)
    if not daily_df.empty:
        style.enable_autofilter(ws, header_row, 1, col_end, last_row)

    return ws


def _write_glossary_sheet(wb):
    ws = wb.create_sheet("Глоссарий")
    col_end = 2
    header_row = style.write_sheet_header(
        ws, "Глоссарий", "Пояснения к терминам отчёта -- простым языком", "", col_end, landscape=False,
    )
    style.write_table_header(ws, header_row, 1, ["Термин", "Что означает"])

    row = header_row + 1
    first_data_row = row
    for term, text in _GLOSSARY:
        ws.cell(row=row, column=1, value=term)
        ws.cell(row=row, column=2, value=text)
        style.style_data_row(ws, row, 1, col_end)
        ws.cell(row=row, column=2).alignment = style.ALIGN_LEFT_WRAP
        ws.row_dimensions[row].height = 28
        row += 1

    last_row = row - 1
    style.apply_zebra(ws, first_data_row, last_row, 1, col_end)
    style.apply_column_dividers(ws, header_row, last_row, 1, col_end)
    ws.column_dimensions["A"].width = 30
    ws.column_dimensions["B"].width = 90
    style.freeze_table(ws, header_row, first_col=1)

    return ws


def _write_toc(wb, bundle, params):
    ws = wb.create_sheet(style.TOC_SHEET_NAME)
    col_end = 6
    style.sheet_base_setup(ws, landscape=True)

    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=col_end)
    c = ws.cell(row=1, column=1, value="Анализ рекламных кампаний WB")
    c.font = style.FONT_SHEET_TITLE
    c.alignment = style.ALIGN_LEFT
    ws.row_dimensions[1].height = 28

    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=col_end)
    c = ws.cell(row=2, column=1, value=_period_label(bundle["start_date"], bundle["end_date"]))
    c.font = style.FONT_SHEET_SUBTITLE
    c.alignment = style.ALIGN_LEFT

    t = bundle["totals"]
    balance = bundle["balance"]
    if balance and not balance.get("error"):
        budget_value, budget_sub = _money(balance["net"]), ""
    elif balance and balance.get("error"):
        budget_value, budget_sub = "—", balance["error"]
    else:
        budget_value, budget_sub = "—", "нет данных"
    cards = [
        ("Расход на рекламу", _money(t["spend_rub"]),
         f"{_int(t['orders'])} {_plural_ru(t['orders'], 'заказ', 'заказа', 'заказов')}"),
        ("Выручка от рекламы", _money(t["revenue_rub"]), ""),
        ("ДРР", _pct1(t["drr"]), "расход / выручка"),
        ("Доступный бюджет (net)", budget_value, budget_sub),
    ]

    row = 4
    style.write_kpi_cards(ws, row, cards, col_start=1, card_width=1, gap_after=0)
    ws.merge_cells(start_row=row, start_column=5, end_row=row + 2, end_column=6)
    row += 4

    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=col_end)
    ws.cell(row=row, column=1, value="Листы").font = style.FONT_TABLE_HEADER
    row += 1
    row = style.write_toc_links(
        ws, row,
        [
            ("Кампании", "По каждой рекламной кампании: показы, клики, расход, заказы, ДРР"),
            ("По товарам", "По каждому товару (nm_id): показы, клики, расход, заказы, ДРР"),
            ("По дням", "Динамика по дням за весь период (без урезки)"),
            ("Глоссарий", "Пояснения к терминам -- CTR, CPC, CR, ДРР и т.д."),
        ],
        col_label=1, col_desc=2, desc_span=col_end - 1,
    )
    row += 1

    style.write_footer_note(
        ws, row, col_end,
        f"Полная детализация по рекламным кампаниям WB за выбранный период. "
        f"Сформировано {datetime.now():%d.%m.%Y %H:%M}.",
    )

    style.apply_column_widths(ws, {}, header_row=row, default_max=30)
    for letter in ("A", "B", "C", "D", "E", "F"):
        if ws.column_dimensions[letter].width is None or ws.column_dimensions[letter].width < 14:
            ws.column_dimensions[letter].width = 18

    return ws


def _assemble_excel(bundle: dict) -> bytes:
    period_label = _period_label(bundle["start_date"], bundle["end_date"])
    params = f"Период: {period_label} · сформировано {datetime.now():%d.%m.%Y %H:%M}"

    wb = Workbook()
    wb.remove(wb.active)

    _write_campaigns_sheet(
        wb, "Рекламные кампании WB: по кампаниям",
        "Построчная детализация по каждой кампании за выбранный период",
        params, bundle["campaigns"],
    )
    _write_products_sheet(
        wb, "Рекламные кампании WB: по товарам",
        "Построчная детализация по каждому товару (nm_id) за выбранный период",
        params, bundle["products"],
    )
    _write_daily_sheet(
        wb, "Рекламные кампании WB: по дням",
        "Динамика по дням за весь выбранный период",
        params, bundle["daily"],
    )
    _write_glossary_sheet(wb)
    _write_toc(wb, bundle, params)

    style.finalize_workbook(
        wb,
        order=[style.TOC_SHEET_NAME, "Кампании", "По товарам", "По дням", "Глоссарий"],
    )

    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return output.read()


def build_ad_campaigns_excel(start_date: str, end_date: str) -> bytes:
    bundle = _fetch_report_bundle(start_date, end_date)
    return _assemble_excel(bundle)


# ================================================================ Excel "По дням/неделям/месяцам"
#
# Та же структура, что и у "Анализ расходов WB" (wb_expenses_excel.py):
# три листа-пивота (день/неделя/месяц), где строки -- иерархия (там
# "Раздел/Статья", здесь "Тип кампании/Кампания"), колонки -- периоды,
# значение в ячейке -- расход. Дарья попросила именно такую же
# структуру, как в уже привычном ей отчёте -- поэтому строим по
# точному образцу тех же функций (_hierarchy_order/_pivot_amounts/
# _write_pivot_sheet), просто с другими именами колонок иерархии и
# с "spend_rub" вместо "amount_rub".
def _prepare_period_df(stats: pd.DataFrame, meta: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "advert_id", "type_name", "name", "date", "spend_rub", "orders", "revenue_rub",
        "day_key", "day_label", "week_key", "week_label", "month_key", "month_label", "year_label",
    ]
    if stats is None or stats.empty:
        return pd.DataFrame(columns=cols)

    df = stats.copy()
    if meta is not None and not meta.empty:
        df = df.merge(meta[["advert_id", "type_name", "name"]], on="advert_id", how="left")
    else:
        df["type_name"] = None
        df["name"] = None

    df["type_name"] = df["type_name"].fillna("—")
    df["name"] = df["name"].fillna("(кампания удалена или переименована)")

    d = pd.to_datetime(df["date"]).dt.date
    df["day_key"] = d
    df["day_label"] = d.apply(lambda x: x.strftime("%d.%m.%Y"))

    week_start = d.apply(lambda x: x - timedelta(days=x.weekday()))
    df["week_key"] = week_start
    df["week_label"] = week_start.apply(
        lambda ws: f"{ws.strftime('%d.%m')}–{(ws + timedelta(days=6)).strftime('%d.%m')}"
    )

    df["month_key"] = d.apply(lambda x: date(x.year, x.month, 1))
    df["month_label"] = df["month_key"].apply(lambda m: m.strftime("%m.%Y"))
    df["year_label"] = d.apply(lambda x: str(x.year))

    return df[cols]


def _period_hierarchy_order(df: pd.DataFrame, value_col: str = "spend_rub"):
    """Порядок "Тип кампании -> [Кампания, ...]" по убыванию |расхода|
    -- крупнейшие типы и кампании сверху, тот же принцип, что и у
    account -> cost_item в "Анализ расходов WB"."""
    if df.empty:
        return []

    by_type = df.groupby("type_name")[value_col].sum().abs().sort_values(ascending=False)

    order = []
    for type_name in by_type.index:
        sub = df.loc[df["type_name"] == type_name]
        by_campaign = sub.groupby("name")[value_col].sum().abs().sort_values(ascending=False)
        order.append((type_name, list(by_campaign.index)))

    return order


def _period_columns(df: pd.DataFrame, key_col: str, label_col: str):
    if df.empty:
        return []
    pairs = df[[key_col, label_col]].drop_duplicates().sort_values(key_col)
    return list(pairs[label_col])


def _period_pivot_amounts(df: pd.DataFrame, label_col: str, value_col: str = "spend_rub"):
    """{(type_name, name, период): сумма}."""
    if df.empty:
        return {}
    g = df.groupby(["type_name", "name", label_col])[value_col].sum()
    return {key: float(v) for key, v in g.items()}


def _write_period_pivot_sheet(wb, sheet_name, title, subtitle, params, hierarchy, period_labels, amounts):
    ws = wb.create_sheet(sheet_name)

    col_end = 2 + len(period_labels) + 1  # Тип / Кампания + периоды + Итого
    header_row = style.write_sheet_header(ws, title, subtitle, params, col_end)

    headers = ["Тип кампании", "Кампания"] + list(period_labels) + ["Итого, ₽"]
    style.write_table_header(ws, header_row, 1, headers)

    row = header_row + 1
    first_data_row = row
    period_cols = list(range(3, 3 + len(period_labels)))
    total_col = col_end
    numeric_cols = tuple(period_cols) + (total_col,)
    formats = {c: style.FMT_MONEY for c in numeric_cols}

    grand_by_period = {p: 0.0 for p in period_labels}
    grand_total = 0.0

    for type_name, campaigns in hierarchy:
        type_row = row
        row += 1

        type_by_period = {p: 0.0 for p in period_labels}
        type_total = 0.0

        for campaign_name in campaigns:
            ws.cell(row=row, column=1, value="")
            ws.cell(row=row, column=2, value=campaign_name)

            item_total = 0.0
            for offset, period in enumerate(period_labels):
                value = amounts.get((type_name, campaign_name, period), 0.0)
                ws.cell(row=row, column=3 + offset, value=round(value, 2))
                item_total += value
                type_by_period[period] += value
                grand_by_period[period] += value

            ws.cell(row=row, column=total_col, value=round(item_total, 2))
            type_total += item_total
            grand_total += item_total

            style.style_data_row(ws, row, 1, col_end, numeric_cols=numeric_cols, formats=formats)
            row += 1

        ws.cell(row=type_row, column=1, value=type_name)
        for offset, period in enumerate(period_labels):
            ws.cell(row=type_row, column=3 + offset, value=round(type_by_period[period], 2))
            ws.cell(row=type_row, column=3 + offset).number_format = style.FMT_MONEY
        ws.cell(row=type_row, column=total_col, value=round(type_total, 2))
        ws.cell(row=type_row, column=total_col).number_format = style.FMT_MONEY

        style.style_level_row(ws, type_row, 1, col_end, level=0)

    ws.cell(row=row, column=1, value="ИТОГО")
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=2)
    for offset, period in enumerate(period_labels):
        ws.cell(row=row, column=3 + offset, value=round(grand_by_period[period], 2))
        ws.cell(row=row, column=3 + offset).number_format = style.FMT_MONEY
    ws.cell(row=row, column=total_col, value=round(grand_total, 2))
    ws.cell(row=row, column=total_col).number_format = style.FMT_MONEY
    style.style_total_row(ws, row, 1, col_end)
    last_row = row

    style.apply_zebra(ws, first_data_row, last_row - 1, 1, col_end)
    style.apply_column_dividers(ws, header_row, last_row, 1, col_end)
    style.apply_column_widths(
        ws,
        {"Тип кампании": 26, "Кампания": 34, "Итого, ₽": 15},
        header_row,
        default_max=14,
    )
    style.freeze_table(ws, header_row, first_col=3)
    # Без автофильтра: это иерархия с промежуточными итогами
    # (тип -> кампания), а не плоская таблица -- та же логика, что и
    # у пивот-листов "Анализ расходов WB".

    return ws


def _write_periods_toc(wb, period_df: pd.DataFrame, params: str):
    ws = wb.create_sheet(style.TOC_SHEET_NAME)
    col_end = 6
    style.sheet_base_setup(ws, landscape=True)

    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=col_end)
    c = ws.cell(row=1, column=1, value="Рекламные кампании WB по дням, неделям и месяцам")
    c.font = style.FONT_SHEET_TITLE
    c.alignment = style.ALIGN_LEFT
    ws.row_dimensions[1].height = 28

    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=col_end)
    c = ws.cell(row=2, column=1, value=params)
    c.font = style.FONT_SHEET_SUBTITLE
    c.alignment = style.ALIGN_LEFT

    total_spend = float(period_df["spend_rub"].sum()) if not period_df.empty else 0.0
    total_orders = int(period_df["orders"].sum()) if not period_df.empty else 0
    total_revenue = float(period_df["revenue_rub"].sum()) if not period_df.empty else 0.0
    drr = (total_spend / total_revenue * 100) if total_revenue else None
    days_n = int(period_df["day_key"].nunique()) if not period_df.empty else 0

    top_type = ""
    if not period_df.empty:
        by_type = period_df.groupby("type_name")["spend_rub"].sum().abs()
        if not by_type.empty:
            top_type = by_type.sort_values(ascending=False).index[0]

    cards = [
        ("Расход на рекламу за период", _money(total_spend), "по всем типам кампаний"),
        ("Заказы", _int(total_orders), "по данным WB"),
        ("ДРР", _pct1(drr), "расход / выручка"),
        ("Дней в периоде", str(days_n), "с показами или расходом"),
    ]
    row = 4
    style.write_kpi_cards(ws, row, cards, col_start=1, card_width=1, gap_after=0)
    row += 4

    if top_type:
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=col_end)
        ws.cell(row=row, column=1, value=f"Крупнейший тип кампаний за период: {top_type}").font = style.FONT_SHEET_SUBTITLE
        row += 2

    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=col_end)
    ws.cell(row=row, column=1, value="Листы").font = style.FONT_TABLE_HEADER
    row += 1
    row = style.write_toc_links(
        ws, row,
        [
            ("По дням", "Ежедневный расход по типам кампаний и кампаниям"),
            ("По неделям", "Понедельный расход по типам кампаний и кампаниям"),
            ("По месяцам", "Помесячный расход по типам кампаний и кампаниям"),
        ],
        col_label=1, col_desc=2, desc_span=col_end - 1,
    )
    row += 1

    style.write_footer_note(
        ws, row, col_end,
        f"Та же структура, что и в 'Анализ расходов WB': иерархия тип кампании / кампания, "
        f"колонки -- периоды. Сформировано {datetime.now():%d.%m.%Y %H:%M}.",
    )

    style.apply_column_widths(ws, {}, header_row=row, default_max=30)
    for letter in ("A", "B", "C", "D", "E", "F"):
        if ws.column_dimensions[letter].width is None or ws.column_dimensions[letter].width < 14:
            ws.column_dimensions[letter].width = 18

    return ws


def _assemble_periods_excel(period_df: pd.DataFrame, start_date: str, end_date: str) -> bytes:
    period_label = _period_label(start_date, end_date)
    params = f"Период: {period_label} · сформировано {datetime.now():%d.%m.%Y %H:%M}"

    wb = Workbook()
    wb.remove(wb.active)

    hierarchy = _period_hierarchy_order(period_df)

    day_labels = _period_columns(period_df, "day_key", "day_label")
    day_amounts = _period_pivot_amounts(period_df, "day_label")
    _write_period_pivot_sheet(
        wb, "По дням", "Рекламные кампании WB по дням", "", params,
        hierarchy, day_labels, day_amounts,
    )

    week_labels = _period_columns(period_df, "week_key", "week_label")
    week_amounts = _period_pivot_amounts(period_df, "week_label")
    _write_period_pivot_sheet(
        wb, "По неделям", "Рекламные кампании WB по неделям", "", params,
        hierarchy, week_labels, week_amounts,
    )

    month_labels = _period_columns(period_df, "month_key", "month_label")
    month_amounts = _period_pivot_amounts(period_df, "month_label")
    _write_period_pivot_sheet(
        wb, "По месяцам", "Рекламные кампании WB по месяцам", "", params,
        hierarchy, month_labels, month_amounts,
    )

    _write_periods_toc(wb, period_df, params)

    style.finalize_workbook(
        wb,
        order=[style.TOC_SHEET_NAME, "По дням", "По неделям", "По месяцам"],
    )

    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return output.read()


def build_ad_campaigns_periods_excel(start_date: str, end_date: str) -> bytes:
    meta = _fetch_campaigns_meta()
    stats = _fetch_stats(start_date, end_date)
    period_df = _prepare_period_df(stats, meta)
    return _assemble_periods_excel(period_df, start_date, end_date)


# ================================================================ UI: пункты меню "Экспорт"
def ad_campaigns_menu_items():
    # disabled=True только на группе (report_menu_group) не мешало
    # клику по самим пунктам ВНУТРИ подменю -- наведение на серую
    # группу всё равно раскрывало список, а сами export_menu_item
    # оставались активными и скачивали файл. Поэтому disabled
    # передаём ЕЩЁ и в каждый пункт подменю отдельно.
    items_disabled = not AD_CAMPAIGNS_MENU_ENABLED
    return [
        report_menu_group(
            "Анализ рекламных кампаний",
            [
                export_menu_item(
                    "Записка, PDF",
                    "Итоги, выводы и рекомендации, топ кампаний и товаров",
                    AD_CAMPAIGNS_PDF_ITEM_ID,
                    disabled=items_disabled,
                ),
                export_menu_item(
                    "Детализация, Excel",
                    "По кампаниям, по товарам и по дням -- построчно",
                    AD_CAMPAIGNS_EXCEL_ITEM_ID,
                    disabled=items_disabled,
                ),
                export_menu_item(
                    "По дням / неделям / месяцам, Excel",
                    "Расход по типам и кампаниям -- та же структура, что в 'Анализ расходов WB'",
                    AD_CAMPAIGNS_PERIODS_ITEM_ID,
                    disabled=items_disabled,
                ),
            ],
            disabled=items_disabled,
        ),
    ]


# ================================================================ callback
def register_ad_campaigns_callbacks(app, filters):
    """Тот же паттерн, что и у register_top_cards_callbacks: один
    callback на все пункты меню, счётчик нажатий в Store вместо
    ctx.triggered_id (под django-plotly-dash не работает), период --
    тот же date-picker дашборда (период не выбран -- весь период)."""

    @app.callback(
        Output(AD_CAMPAIGNS_PDF_DOWNLOAD_ID, "data"),
        Output(AD_CAMPAIGNS_EXCEL_DOWNLOAD_ID, "data"),
        Output(AD_CAMPAIGNS_PERIODS_DOWNLOAD_ID, "data"),
        Output(AD_CAMPAIGNS_STATUS_ID, "children"),
        Output(AD_CAMPAIGNS_CLICKS_ID, "data"),

        Input(AD_CAMPAIGNS_PDF_ITEM_ID, "n_clicks"),
        Input(AD_CAMPAIGNS_EXCEL_ITEM_ID, "n_clicks"),
        Input(AD_CAMPAIGNS_PERIODS_ITEM_ID, "n_clicks"),

        State(filters.date_picker_id, "value"),
        State(AD_CAMPAIGNS_CLICKS_ID, "data"),

        prevent_initial_call=True,
    )
    def export_ad_campaigns(pdf_clicks, excel_clicks, periods_clicks, date_range, seen_clicks):
        counts = {
            "ad_campaigns_pdf": int(pdf_clicks or 0),
            "ad_campaigns_excel": int(excel_clicks or 0),
            "ad_campaigns_periods": int(periods_clicks or 0),
        }
        seen = seen_clicks or {}

        changed = [
            kind for kind, _ in AD_CAMPAIGNS_MENU_KINDS
            if counts.get(kind, 0) != int(seen.get(kind) or 0)
        ]
        if not changed:
            return no_update, no_update, no_update, no_update, counts
        kind = changed[0]

        if date_range and len(date_range) == 2:
            picked_start, picked_end = date_range
            if picked_start and picked_end:
                start_date, end_date = picked_start, picked_end
            elif picked_start or picked_end:
                return no_update, no_update, no_update, no_update, counts
            else:
                start_date = HISTORY_START.isoformat()
                end_date = date.today().isoformat()
        else:
            start_date = HISTORY_START.isoformat()
            end_date = date.today().isoformat()

        period_note = (
            f"{start_date} – {end_date}" if start_date != end_date
            else start_date
        )

        try:
            if kind == "ad_campaigns_pdf":
                content = build_ad_campaigns_pdf_bytes(start_date, end_date)
                filename = f"wb_ad_campaigns_{start_date}_{end_date}.pdf"
                status = dmc.Alert(
                    title="Записка готова", color="teal", withCloseButton=True,
                    children=dmc.Text(
                        f"{filename} · {len(content) / 1_000_000:.1f} МБ · "
                        f"период {period_note}",
                        size="sm",
                    ),
                )
                return dcc.send_bytes(content, filename=filename), no_update, no_update, status, counts

            if kind == "ad_campaigns_excel":
                content = build_ad_campaigns_excel(start_date, end_date)
                filename = f"wb_ad_campaigns_detail_{start_date}_{end_date}.xlsx"
                status = dmc.Alert(
                    title="Файл готов", color="teal", withCloseButton=True,
                    children=dmc.Text(
                        f"{filename} · {len(content) / 1_000_000:.1f} МБ · "
                        f"период {period_note}",
                        size="sm",
                    ),
                )
                return no_update, dcc.send_bytes(content, filename=filename), no_update, status, counts

            content = build_ad_campaigns_periods_excel(start_date, end_date)
            filename = f"wb_ad_campaigns_periods_{start_date}_{end_date}.xlsx"
            status = dmc.Alert(
                title="Файл готов", color="teal", withCloseButton=True,
                children=dmc.Text(
                    f"{filename} · {len(content) / 1_000_000:.1f} МБ · "
                    f"период {period_note}",
                    size="sm",
                ),
            )
            return no_update, no_update, dcc.send_bytes(content, filename=filename), status, counts

        except Exception as exc:
            return (
                no_update, no_update, no_update,
                dmc.Alert(
                    title="Не удалось собрать файл", color="red", withCloseButton=True,
                    children=dmc.Text(
                        f"{type(exc).__name__}: {exc} (период запроса: {period_note})",
                        size="sm",
                    ),
                ),
                counts,
            )
