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

#: Сколько кампаний/товаров показывать в топ-таблицах PDF-записки.
TOP_CAMPAIGNS_N = 15
TOP_PRODUCTS_N = 15

#: Сколько последних дней периода показывать построчно в PDF
#: (в Excel -- весь период без урезки).
DAILY_TREND_MAX_DAYS = 20

#: Отчёт ещё доделывается (визуал PDF, покрытие по датам и т.п.) --
#: пункт меню виден, но неактивен (серый, не открывается). Когда
#: отчёт будет готов -- поставить True и задеплоить файл заново.
AD_CAMPAIGNS_MENU_ENABLED = False   # ← поменять на True

#: Пороги для правил в "Выводах и рекомендациях".
DRR_HIGH_THRESHOLD = 15.0
DRR_LOW_THRESHOLD = 5.0
DRR_TREND_DELTA = 1.5
CONCENTRATION_THRESHOLD = 50.0
BUDGET_RUNWAY_WARN_DAYS = 14


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
        if "does not exist" in msg or "Catalog Error" in msg or "no such" in msg.lower():
            reason = "таблица баланса не найдена в базе, которую читает дашборд"
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
    return g[_CAMPAIGNS_AGG_COLUMNS]


_PRODUCTS_AGG_COLUMNS = [
    "nm_id", "title", "brand", "category",
    "views", "clicks", "ctr", "cpc", "spend_rub",
    "atbs", "orders", "cr", "shks", "revenue_rub", "canceled", "drr",
]


def _aggregate_products(stats_by_nm: pd.DataFrame, products: pd.DataFrame) -> pd.DataFrame:
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

    prev_start, prev_end = _prev_period_dates(start_date, end_date)
    try:
        prev_stats = _fetch_stats(prev_start, prev_end)
    except Exception:
        prev_stats = pd.DataFrame(columns=_STATS_COLUMNS)

    campaigns_df = _aggregate_campaigns(stats, meta)
    products_df = _aggregate_products(stats_by_nm, products)
    daily_df = _aggregate_daily(stats)
    by_type_df = _aggregate_by_type(campaigns_df)

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
        "totals": _totals_from_stats(stats),
        "prev_totals": _totals_from_stats(prev_stats) if not prev_stats.empty else None,
        "balance": balance,
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

    # 1. ДРР относительно периода
    if totals["orders"] == 0 and spend > 0:
        recs.append((
            "Расход есть, заказов от рекламы нет",
            f"За период потрачено {_money(spend)}, но реклама не принесла ни одного "
            f"заказа (по данным WB). Стоит проверить кампании ниже вручную и, "
            f"возможно, приостановить их до выяснения причины."
        ))
    elif drr is not None:
        if drr > DRR_HIGH_THRESHOLD:
            recs.append((
                "ДРР выше комфортного уровня",
                f"Доля рекламных расходов за период — {_pct1(drr)}. Обычно "
                f"ориентируются на 10–15%, здесь показатель выше. Есть смысл "
                f"проверить самые дорогие кампании и товары из таблиц ниже: "
                f"часто дело в одной-двух кампаниях, где клики есть, а заказов "
                f"мало — их можно приостановить или снизить ставку."
            ))
        elif drr < DRR_LOW_THRESHOLD:
            recs.append((
                "ДРР ниже нормы — есть запас для роста",
                f"Доля рекламных расходов за период — всего {_pct1(drr)}: реклама "
                f"окупается с хорошим запасом. Если товар и так хорошо продаётся, "
                f"можно аккуратно увеличить бюджет или ставки на самые "
                f"эффективные кампании из таблицы ниже, чтобы получить больше "
                f"заказов при таком же выгодном соотношении."
            ))
        else:
            recs.append((
                "ДРР в норме",
                f"Доля рекламных расходов за период — {_pct1(drr)}, это здоровый "
                f"уровень. Явных поводов срочно что-то менять нет — стоит просто "
                f"следить за динамикой по дням (раздел ниже)."
            ))

    # 2. сравнение с предыдущим периодом такой же длины
    if prev_totals is not None and drr is not None and prev_totals["drr"] is not None:
        diff = drr - prev_totals["drr"]
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
                f"по длине предыдущим периодом ({_period_label(bundle['prev_start'], bundle['prev_end'])}, "
                f"тогда было {_pct1(prev_totals['drr'])}). {explanation}"
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

    return '<p class="narrative">' + " ".join(sentences) + "</p>"


# ================================================================ PDF-записка
_PDF_CSS = f"""
    @page {{ size: A4; margin: 16mm 14mm; }}
    * {{ box-sizing: border-box; }}
    body {{ font-family: "Helvetica Neue", Arial, sans-serif; color: #1f2a24;
            margin: 0; font-size: 10px; }}
    h1 {{ font-size: 18px; color: #{style.NAVY_3}; margin: 0 0 4px; }}
    .period {{ color: #667; font-size: 9.5px; margin: 0 0 16px; line-height: 1.5; }}
    .block {{ margin-bottom: 20px; }}
    .block + .block {{ page-break-before: always; break-before: page; }}
    h2 {{ font-size: 14px; color: #{style.NAVY_3}; border-bottom: 2px solid #{style.NAVY};
          padding-bottom: 4px; margin: 0 0 8px; }}
    .kpi-row {{ display: flex; gap: 8px; margin-bottom: 8px;
                page-break-inside: avoid; break-inside: avoid; }}
    .kpi {{ flex: 1; background: #{style.SURFACE_3}; border-radius: 6px; padding: 7px 9px; }}
    .kpi-label {{ font-size: 8.5px; color: #667; text-transform: uppercase; }}
    .kpi-value {{ font-size: 14px; font-weight: 700; color: #{style.NAVY_3}; }}
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
    .subhead {{ font-size: 10.5px; font-weight: 700; color: #{style.NAVY_3};
                margin: 0 0 5px; }}
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
    th {{ background: #{style.NAVY}; color: #fff; text-align: left; padding: 5px 6px; }}
    td {{ padding: 4px 6px; border-bottom: 1px solid #{style.LINE}; overflow: hidden;
          text-overflow: ellipsis; white-space: nowrap; }}
    td.num {{ text-align: right; white-space: nowrap; }}
    tr:nth-child(even) td {{ background: #{style.SURFACE_2}; }}
    col.c-num {{ width: 5%; }}
    col.c-name {{ width: 40%; }}
    col.c-status {{ width: 15%; }}
    col.c-brand {{ width: 18%; }}
    col.c-sum {{ width: 15%; }}
    col.c-ops {{ width: 12%; }}
    col.c-pct {{ width: 12%; }}
    .empty {{ text-align: center; color: #888; padding: 8px; font-size: 9px; }}
    .top-block {{ page-break-inside: avoid; break-inside: avoid; margin-top: 4px; }}
    .footer {{ margin-top: 10px; font-size: 8px; color: #999; }}
    .section-note {{ margin-top: 10px; font-size: 8.5px; color: #999; }}
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
        _kpi_html("ДРР", _pct1(t["drr"]), "доля расходов от выручки рекламы¹"),
        _kpi_html("Заказы", _int(t["orders"])),
    ])
    row2 = "".join([
        _kpi_html("Показы", _int(t["views"])),
        _kpi_html("Клики", _int(t["clicks"])),
        _kpi_html("CTR", _pct1(t["ctr"]), "кликабельность¹"),
        _kpi_html("CPC", _money_dec(t["cpc"]), "цена клика¹"),
    ])
    return f'<div class="kpi-row">{row1}</div><div class="kpi-row">{row2}</div>'


def _budget_html(balance) -> str:
    if not balance:
        return ""

    if balance.get("error"):
        return f"""
        <div class="budget-row">
            <div class="budget" style="flex: none; width: 100%;">
                <div class="budget-label">Доступно для рекламы (net)¹ -- нет данных</div>
                <div class="budget-value" style="font-size: 9.5px; font-weight: 400; color: #889;">
                    {_esc(balance["error"])}
                </div>
            </div>
        </div>
        """

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


def _type_breakdown_html(by_type_df: pd.DataFrame) -> str:
    if by_type_df is None or by_type_df.empty:
        return '<div class="empty">Данных нет</div>'

    max_spend = by_type_df["spend_rub"].max() or 1.0
    items = []
    for r in by_type_df.itertuples(index=False):
        pct = min(100.0, (r.spend_rub / max_spend * 100)) if max_spend else 0.0
        items.append(f"""
        <div class="bar-row">
            <div class="bar-label" title="{_esc(r.type_name)}">{_esc(r.type_name)}</div>
            <div class="bar-track"><div class="bar-fill" style="width:{pct:.1f}%"></div></div>
            <div class="bar-value">{_money(r.spend_rub)} · {_int(r.orders)} зак. · ДРР {_pct1(r.drr)}</div>
        </div>
        """)
    return "".join(items)


def _campaigns_table_html(campaigns_df: pd.DataFrame, top_n: int = TOP_CAMPAIGNS_N) -> str:
    if campaigns_df is None or campaigns_df.empty:
        return '<div class="empty">Операций за период нет</div>'

    top = campaigns_df.sort_values("spend_rub", ascending=False).head(top_n)
    rows = "".join(
        f"""
        <tr>
            <td class="num">{i + 1}</td>
            <td>{_esc(r.name)}</td>
            <td>{_esc(r.status_name)}</td>
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
            <col class="c-num"><col class="c-name"><col class="c-status">
            <col class="c-sum"><col class="c-ops"><col class="c-pct">
        </colgroup>
        <thead>
            <tr><th>#</th><th>Кампания</th><th>Статус</th>
                <th>Расход, ₽</th><th>Заказы</th><th>ДРР</th></tr>
        </thead>
        <tbody>{rows}</tbody>
    </table>
    """


def _products_table_html(products_df: pd.DataFrame, top_n: int = TOP_PRODUCTS_N) -> str:
    if products_df is None or products_df.empty:
        return '<div class="empty">Операций за период нет</div>'

    top = products_df.sort_values("spend_rub", ascending=False).head(top_n)
    rows = "".join(
        f"""
        <tr>
            <td class="num">{i + 1}</td>
            <td>{_esc(r.title)}</td>
            <td>{_esc(r.brand)}</td>
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
            <col class="c-num"><col class="c-name"><col class="c-brand">
            <col class="c-sum"><col class="c-ops"><col class="c-pct">
        </colgroup>
        <thead>
            <tr><th>#</th><th>Товар</th><th>Бренд</th>
                <th>Расход, ₽</th><th>Заказы</th><th>ДРР</th></tr>
        </thead>
        <tbody>{rows}</tbody>
    </table>
    """


def _daily_trend_html(daily_df: pd.DataFrame, max_days: int = DAILY_TREND_MAX_DAYS) -> str:
    if daily_df is None or daily_df.empty:
        return '<div class="empty">Данных нет</div>', ""

    shown = daily_df.tail(max_days)
    truncated_note = ""
    if len(daily_df) > max_days:
        truncated_note = f"Показаны последние {max_days} дней из {len(daily_df)} -- полный ряд по дням смотрите в Excel-детализации."

    max_spend = shown["spend_rub"].max() or 1.0
    items = []
    for r in shown.itertuples(index=False):
        pct = min(100.0, (r.spend_rub / max_spend * 100)) if max_spend else 0.0
        label = pd.to_datetime(r.date).strftime("%d.%m")
        items.append(f"""
        <div class="bar-row">
            <div class="bar-label">{label}</div>
            <div class="bar-track"><div class="bar-fill" style="width:{pct:.1f}%"></div></div>
            <div class="bar-value">{_money(r.spend_rub)} · {_int(r.orders)} зак. · ДРР {_pct1(r.drr)}</div>
        </div>
        """)
    return "".join(items), truncated_note


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
    ("Net (доступный бюджет)", "реальная сумма, которую можно потратить на рекламу прямо сейчас."),
    ("Баланс", "отдельный технический остаток на рекламном кошельке WB (обычно не совпадает с net)."),
    ("Бонусы", "бонусные средства WB, которые тоже можно тратить на рекламу."),
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


def build_ad_campaigns_html(bundle: dict) -> str:
    period_label = _period_label(bundle["start_date"], bundle["end_date"])
    trend_html, trend_note = _daily_trend_html(bundle["daily"])

    body = f"""
    <section class="block">
        <h2>Итоги за период</h2>
        {_kpi_rows_html(bundle)}
        {_budget_html(bundle["balance"])}
        {_narrative_html(bundle)}
        <div class="section-note">{_esc(period_label)}</div>
    </section>

    <section class="block">
        <h2>Выводы и рекомендации</h2>
        {_recommendations_html(bundle)}
    </section>

    <section class="block">
        <h2>По типам кампаний</h2>
        <div class="subhead">Расход и отдача по типу размещения (каталог, поиск, автоматическая, аукцион и т.п.)</div>
        {_type_breakdown_html(bundle["by_type"])}
    </section>

    <section class="block">
        <div class="top-block">
            <h2>Топ-{TOP_CAMPAIGNS_N} кампаний по расходу</h2>
            {_campaigns_table_html(bundle["campaigns"])}
        </div>
    </section>

    <section class="block">
        <div class="top-block">
            <h2>Топ-{TOP_PRODUCTS_N} товаров по расходу на рекламу</h2>
            {_products_table_html(bundle["products"])}
        </div>
    </section>

    <section class="block">
        <h2>Динамика по дням</h2>
        {trend_html}
        {f'<div class="section-note">{_esc(trend_note)}</div>' if trend_note else ""}
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
<p class="period">{_esc(period_label)} · данные и атрибуция заказов -- по статистике WB Продвижение.</p>
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
    "nm_id", "Наименование", "Бренд", "Категория",
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
    style.freeze_table(ws, header_row, first_col=2)
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
        5: style.FMT_QTY, 6: style.FMT_QTY, 7: style.FMT_PCT, 8: style.FMT_MONEY_DEC,
        9: style.FMT_MONEY, 10: style.FMT_QTY, 11: style.FMT_QTY, 12: style.FMT_PCT,
        13: style.FMT_QTY, 14: style.FMT_MONEY, 15: style.FMT_QTY, 16: style.FMT_PCT,
    }

    sub = products_df.sort_values("spend_rub", ascending=False) if not products_df.empty else products_df
    for _, r in sub.iterrows():
        ws.cell(row=row, column=1, value=int(r["nm_id"]))
        ws.cell(row=row, column=2, value=r["title"])
        ws.cell(row=row, column=3, value=r["brand"])
        ws.cell(row=row, column=4, value=r["category"])
        ws.cell(row=row, column=5, value=int(r["views"]))
        ws.cell(row=row, column=6, value=int(r["clicks"]))
        ws.cell(row=row, column=7, value=round(float(r["ctr"]), 2))
        ws.cell(row=row, column=8, value=round(float(r["cpc"]), 2))
        ws.cell(row=row, column=9, value=round(float(r["spend_rub"]), 2))
        ws.cell(row=row, column=10, value=int(r["atbs"]))
        ws.cell(row=row, column=11, value=int(r["orders"]))
        ws.cell(row=row, column=12, value=round(float(r["cr"]), 2))
        ws.cell(row=row, column=13, value=int(r["shks"]))
        ws.cell(row=row, column=14, value=round(float(r["revenue_rub"]), 2))
        ws.cell(row=row, column=15, value=int(r["canceled"]))
        ws.cell(row=row, column=16, value=round(float(r["drr"]), 2) if pd.notna(r["drr"]) else None)

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
            "nm_id": 12, "Наименование": 38, "Бренд": 16, "Категория": 22,
            "Показы": 12, "Клики": 10, "CTR, %": 10, "CPC, ₽": 10, "Расход, ₽": 14,
            "Корзины": 10, "Заказы": 10, "CR, %": 9, "Штук": 9, "Выручка, ₽": 14,
            "Отменено": 10, "ДРР, %": 9,
        },
        header_row,
    )
    style.freeze_table(ws, header_row, first_col=2)
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
    # disabled=True только на группе не мешало клику по самим пунктам
    # внутри подменю -- наведение на серую группу всё равно раскрывало
    # список, а сами export_menu_item оставались активными и скачивали файл.
    # Поэтому disabled передаём ЕЩЁ и в каждый пункт подменю отдельно.
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
