# reporting/excel/unit_economics_data.py
"""
1.8 Юнит-экономика продаж — два метода признания выручки.

МЕТОДОЛОГИЯ (коротко, подробно расписано на самом листе)
----------------------------------------------------------------------

КЭШ-МЕТОД (целевой оборот)
    Источник количества: сырые события WB (sales.sales_long,
    field='retail_price') — продажа и возврат — это два разных события,
    каждое признаётся на СВОЮ фактическую дату. Источник суммы после
    СПП: тот же sales.sales_long, field='retail_amount' (фактически
    причитающаяся сумма ПОСЛЕ применения скидки СПП, цена для
    покупателя) — это НЕ то же самое, что retail_price.
    "До СПП с НДС" на кэш-методе — это фактически поступившая касса по
    статье ДДС 111000 "Выручка от продажи товаров" (Postgres cf_to_csv,
    та же цифра, что на листе CF) — берётся как есть, без каких-либо
    досчётов. Сумма БЕЗ НДС получается умножением на фактическое
    НДС-соотношение того же периода (из собственных данных кэш-блока
    после СПП) — это единственный приближённый шаг во всём кэш-блоке.
    ВАЖНО: эта сумма НЕ равна "Выручка без НДС" на листе PL — там
    берётся бухгалтерское начисление (счёт 410000, метод начисления,
    признаётся на дату проводки бухгалтерии), а здесь — фактическая
    касса (метод оплаты). Небольшое расхождение между ними ожидаемо и
    не является ошибкой (см. также разницу CF vs PL по строке 4).

FIFO-МЕТОД (управленческий)
    Источник: inventories.inv_gl_final (view `base`) — тот же контур,
    что использует daily_sales/pricing_strategy/daily_brief.
    Выручка и себестоимость признаются по дате ИСХОДНОЙ продажи.
    Последующий возврат гасит именно эту продажу (строка исключается
    целиком, см. inventories.sales_gl), поэтому отдельной строки
    "возвраты" в этом контуре физически нет — гросс/нетто продажи
    ниже это расчётная величина по знаку cr_rev, а не хранящееся поле.

СЕБЕСТОИМОСТЬ (ОДИНАКОВАЯ В ОБОИХ БЛОКАХ) — управленческая FIFO-
себестоимость (adjusted_cogs_man, тот же показатель, что в daily_sales),
а не бухгалтерская. Ставка "рублей на единицу" считается по FIFO-блоку
(сумма adjusted_cogs_man за месяц / кол-во чистых продаж FIFO за тот же
месяц) и применяется к фактическому кол-ву чистых продаж каждого блока
— в кэш-блоке оно может отличаться от FIFO (см. методику на листе), а
себестоимость на единицу — нет: это одна и та же управленческая цифра.

ОБЩИЕ ДЛЯ ОБОИХ БЛОКОВ РАСХОДЫ (это расходы периода, они не зависят от
метода признания выручки, поэтому берутся из ОДНОГО источника и
применяются к обоим блокам одинаково):

    Расходы ВБ без продвижения — комплексный пул операционных расходов
                                  площадки: комиссия WB за продажу,
                                  логистика, хранение, приёмка, штрафы,
                                  удержания, программа лояльности и
                                  корректировки. Считается из СЫРЫХ
                                  данных площадки (sales.sales_long /
                                  BASE_WB_COSTS — та же методология,
                                  что в daily_sales), а НЕ из
                                  бухгалтерского ГК: проверено, что на
                                  счетах 1.4/1.5 отдельных строк по
                                  логистике/хранению/приёмке/штрафам/
                                  комиссии вообще нет — там только
                                  маркетинг, комиссия банка, аренда,
                                  цифровые сервисы, персонал, консалтинг
                                  и представительские расходы.
    Продвижение                — счета 610000+620000 (1.4/1.5),
                                  статьи с "WB" в названии группы или
                                  статьи, относящиеся к рекламе,
                                  продвижению или маркетингу.
    Прочие накладные расходы    — остаток счетов 1.4/1.5 (не про WB),
                                  плюс счёт 1.6 (420000, прочие доходы/
                                  расходы), плюс счёт 1.7 (630000,
                                  финансовые расходы). Используются
                                  только в чистой прибыли, см. ниже.

Маржинальность по валовой прибыли           = 1 - СС / Продажи до СПП без НДС
Маржинальность по маржин. прибыли (без пр.) = (ВП + Расходы ВБ без продв.) / Продажи до СПП без НДС
Маржинальность по маржин. прибыли (с пр.)   = (ВП + Расходы ВБ без продв. + продвижение) / Продажи до СПП без НДС
Чистая прибыль (управленческая)             = Маржин. прибыль (с продв.) + Прочие накладные расходы
Рентабельность по чистой прибыли            = Чистая прибыль / Продажи до СПП без НДС

Чистая прибыль здесь считается ОДИНАКОВО в обоих блоках — снизу вверх,
из показателей этого же листа, а не берётся готовой строкой с листа PL
(на листе PL учтён налог на прибыль и другая методология признания
выручки — сравнивать эти два числа напрямую некорректно). Показатель
на этом листе управленческий, налог на прибыль в нём не учтён.

Расходы (СС, Расходы ВБ, Продвижение, Прочие накладные) хранятся с тем
же знаком, что и в источнике (pl_for_csv — отрицательные), поэтому
дальше они складываются, а не вычитаются — так же, как в pl_data.py.
"""

from __future__ import annotations

import pandas as pd
from django.db import connection

from conns import get_duckdb_conn_with_opt

from gear.app.data.queries import BASE_QUERY, BASE_WB_COSTS


MONTH_NAMES_RU = {
    1: "Янв", 2: "Фев", 3: "Мар", 4: "Апр", 5: "Май", 6: "Июн",
    7: "Июл", 8: "Авг", 9: "Сен", 10: "Окт", 11: "Ноя", 12: "Дек",
}

PROMO_PATTERN = r"реклам|продвижен|маркетинг|advert|marketing"

ROW_SALES_QTY = "Кол-во продаж, шт"
ROW_RETURNS_QTY = "Кол-во возвратов, шт"
ROW_NET_QTY = "Кол-во чистых продаж, шт"
ROW_AMOUNT_BEFORE_SPP = "Продажи до СПП с НДС, ₽"
ROW_AMOUNT_BEFORE_SPP_VATLESS = "Продажи до СПП без НДС, ₽"
ROW_AVG_PRICE_BEFORE_SPP = "Средняя цена на ед. продаж до СПП с НДС, ₽"
ROW_AVG_PRICE_AFTER_SPP = "Средняя цена на ед. продаж после СПП с НДС (цена для покупателя), ₽"
ROW_AVG_COGS = "Средняя с/с на ед. продаж без НДС, ₽"
ROW_WB_COSTS = "Расходы ВБ без продвижения (комиссия, логистика, хранение и пр.), ₽"
ROW_PROMO = "Продвижение, ₽"
ROW_OTHER_OVERHEADS = "Прочие накладные расходы (1.4/1.5 без WB, 1.6, 1.7), ₽"
ROW_NET_PROFIT = "Чистая прибыль (управленческая, до налога на прибыль), ₽"
ROW_GROSS_MARGIN = "Маржинальность по валовой прибыли, %"
ROW_MARGIN_NO_PROMO = "Маржинальность по маржинальной прибыли (без продвижения), %"
ROW_MARGIN_WITH_PROMO = "Маржинальность по маржинальной прибыли (с продвижением), %"
ROW_NET_MARGIN = "Рентабельность по чистой прибыли, %"

ROW_ORDER = [
    ROW_SALES_QTY,
    ROW_RETURNS_QTY,
    ROW_NET_QTY,
    ROW_AMOUNT_BEFORE_SPP,
    ROW_AMOUNT_BEFORE_SPP_VATLESS,
    ROW_AVG_PRICE_BEFORE_SPP,
    ROW_AVG_PRICE_AFTER_SPP,
    ROW_AVG_COGS,
    ROW_WB_COSTS,
    ROW_PROMO,
    ROW_OTHER_OVERHEADS,
    ROW_NET_PROFIT,
    ROW_GROSS_MARGIN,
    ROW_MARGIN_NO_PROMO,
    ROW_MARGIN_WITH_PROMO,
    ROW_NET_MARGIN,
]

# Курсивом больше ничего не выделяем — единственное расчётное звено
# (доля НДС для знаменателя маржинальности в кэш-блоке) описано в
# методике на листе, а не отдельным визуальным маркером по строкам.
ESTIMATED_CASH_ROWS = set()

QTY_ROWS = {ROW_SALES_QTY, ROW_RETURNS_QTY, ROW_NET_QTY}
MONEY_ROWS = {
    ROW_AMOUNT_BEFORE_SPP, ROW_AMOUNT_BEFORE_SPP_VATLESS, ROW_AVG_PRICE_BEFORE_SPP,
    ROW_AVG_PRICE_AFTER_SPP, ROW_AVG_COGS, ROW_WB_COSTS, ROW_PROMO,
    ROW_OTHER_OVERHEADS, ROW_NET_PROFIT,
}
PERCENT_ROWS = {ROW_GROSS_MARGIN, ROW_MARGIN_NO_PROMO, ROW_MARGIN_WITH_PROMO, ROW_NET_MARGIN}

# Строки, для которых лист рисует настоящую формулу Excel (со ссылками на
# другие строки того же столбца), а не готовое число из Python. Значения
# в DataFrame всё равно считаются (они используются для взвешенных средних
# в колонках "Итого" и как самопроверка), но на лист идёт формула.
FORMULA_ROWS = {
    ROW_NET_QTY,
    ROW_AVG_PRICE_BEFORE_SPP,
    ROW_NET_PROFIT,
    ROW_GROSS_MARGIN,
    ROW_MARGIN_NO_PROMO,
    ROW_MARGIN_WITH_PROMO,
    ROW_NET_MARGIN,
}


def _period_col(year: int, month: int) -> str:
    return f"{MONTH_NAMES_RU[int(month)]} {int(year)}"


def _year_groups(years, current_year, current_month):
    groups = []
    ordered_cols = []

    for year in years:
        months = list(range(1, current_month + 1)) if year == current_year else list(range(1, 13))
        month_cols = [_period_col(year, m) for m in months]
        total_col = f"Итого {year}"

        groups.append({
            "year": year,
            "months": months,
            "month_cols": month_cols,
            "total_col": total_col,
        })

        ordered_cols.extend(month_cols)
        ordered_cols.append(total_col)

    return groups, ordered_cols


def _safe_div(a, b):
    if not b:
        return None
    return a / b * 100.0


# ============================================================
# КЭШ-МЕТОД: sales.sales_long
#   Количество — field='retail_price' (событие продажи/возврата, dt/cr).
#   Сумма "после СПП" — field='retail_amount': это фактически причитающаяся
#   сумма ПОСЛЕ применения скидки СПП (цена для покупателя). retail_price —
#   это цена ДО СПП (та же величина, что и касса по статье 111000), поэтому
#   для денежной суммы "после СПП" использовать её нельзя.
# ============================================================

def _fetch_cash_monthly(con, date_to):
    sql = """
        SELECT
            EXTRACT(YEAR FROM date_from)::INT AS year,
            EXTRACT(MONTH FROM date_from)::INT AS month,

            COUNT(*) FILTER (WHERE field = 'retail_price' AND oper = 'dt') AS sales_qty,
            COUNT(*) FILTER (WHERE field = 'retail_price' AND oper = 'cr') AS returns_qty,

            COALESCE(
                SUM(val) FILTER (WHERE field = 'retail_amount' AND oper = 'dt'), 0
            ) AS sales_amount,
            COALESCE(
                SUM(val) FILTER (WHERE field = 'retail_amount' AND oper = 'cr'), 0
            ) AS returns_amount,

            COALESCE(
                SUM(val / (100 + vat_rate) * 100)
                FILTER (WHERE field = 'retail_amount' AND oper = 'dt'), 0
            ) AS sales_amount_vatless,
            COALESCE(
                SUM(val / (100 + vat_rate) * 100)
                FILTER (WHERE field = 'retail_amount' AND oper = 'cr'), 0
            ) AS returns_amount_vatless

        FROM sales.sales_long
        WHERE field IN ('retail_price', 'retail_amount')
          AND date_from <= ?
        GROUP BY 1, 2
        ORDER BY 1, 2
    """
    df = con.execute(sql, [date_to]).df()
    if df.empty:
        return df

    df["net_qty"] = df["sales_qty"] - df["returns_qty"]
    df["amount_after_spp"] = (df["sales_amount"] - df["returns_amount"]) / 100.0
    df["amount_after_spp_vatless"] = (
        df["sales_amount_vatless"] - df["returns_amount_vatless"]
    ) / 100.0
    return df[["year", "month", "sales_qty", "returns_qty", "net_qty",
                "amount_after_spp", "amount_after_spp_vatless"]]


# ============================================================
# FIFO-МЕТОД: base (inventories.inv_gl_final), по дате исходной продажи
# ============================================================

def _fetch_fifo_monthly(con, date_to):
    sql = """
        SELECT
            EXTRACT(YEAR FROM t.date_from::DATE)::INT AS year,
            EXTRACT(MONTH FROM t.date_from::DATE)::INT AS month,

            SUM(CASE WHEN t.cr_rev > 0 THEN 1 ELSE 0 END) AS sales_qty,
            SUM(CASE WHEN t.cr_rev < 0 THEN 1 ELSE 0 END) AS returns_qty,
            SUM(
                CASE WHEN t.cr_rev > 0 THEN 1
                     WHEN t.cr_rev < 0 THEN -1
                     ELSE 0 END
            ) AS net_qty,

            SUM(t.cr_rev) AS amount_before_spp,
            SUM(t.retail_amount) AS amount_after_spp,
            SUM(t.cr_rev / (100 + t.vat_rate) * 100) AS amount_before_spp_vatless,

            SUM(t.adjusted_cogs_man) AS cogs_man

        FROM base t

        WHERE t.cr_rev <> 0
          AND t.date_from::DATE <= ?

        GROUP BY 1, 2
        ORDER BY 1, 2
    """
    df = con.execute(sql, [date_to]).df()
    if df.empty:
        return df

    for col in ("amount_before_spp", "amount_after_spp", "amount_before_spp_vatless", "cogs_man"):
        df[col] = df[col] / 100.0

    df["cogs_signed"] = -df["cogs_man"].abs()
    return df


# ============================================================
# КОМПЛЕКСНЫЙ ПУЛ ОПЕРАЦИОННЫХ РАСХОДОВ ВБ (общий для обоих блоков)
# ============================================================

def _fetch_wb_cost_pool_monthly(con, date_to):
    """
    "Расходы ВБ без продвижения" — общий для кэш- и FIFO-блока пул
    операционных расходов площадки (это расходы периода, они не зависят
    от способа признания выручки):

      - комиссия WB за продажу (sales.sales_long, field='comission',
        dt - cr, без НДС — та же методология, что в daily_sales;
        обычно получается отрицательной величиной);
      - логистика, хранение, приёмка, штрафы, удержания, программа
        лояльности и корректировки — BASE_WB_COSTS (та же таблица
        wb_costs, что использует daily_sales/wb_costs_by_week:
        dt - cr по каждой категории, без НДС).

    Источник — СЫРЫЕ данные площадки, а НЕ бухгалтерский ГК: проверено
    по факту сформированного отчёта, что на счетах 1.4/1.5 отдельных
    статей по логистике/хранению/приёмке/штрафам/комиссии вообще нет —
    там только маркетинг, комиссия банка, аренда, цифровые сервисы,
    персонал, консалтинг и представительские расходы. Раньше "Расходы
    ВБ без продвижения" считались только по этим трём бухгалтерским
    статьям (лояльность и комиссия банка), из-за чего практически
    совпадали с нулём и маржинальность "без продвижения" совпадала с
    валовой маржинальностью — это было исправлено.

    Итог приводится к отрицательному знаку (это расход, дальше он
    складывается с выручкой, а не вычитается — как и везде на листе).
    """
    commission_sql = """
        SELECT
            EXTRACT(YEAR FROM date_from)::INT AS year,
            EXTRACT(MONTH FROM date_from)::INT AS month,
            COALESCE(
                SUM(val / (100 + vat_rate) * 100)
                FILTER (WHERE field = 'comission' AND oper = 'dt'), 0
            )
            -
            COALESCE(
                SUM(val / (100 + vat_rate) * 100)
                FILTER (WHERE field = 'comission' AND oper = 'cr'), 0
            ) AS net_comission
        FROM sales.sales_long
        WHERE date_from <= ?
        GROUP BY 1, 2
    """
    commission_df = con.execute(commission_sql, [date_to]).df()

    con.execute(BASE_WB_COSTS)
    pool_sql = """
        SELECT
            EXTRACT(YEAR FROM date_from::DATE)::INT AS year,
            EXTRACT(MONTH FROM date_from::DATE)::INT AS month,
            SUM(dt / (100 + vat_rate) * 100) - SUM(cr / (100 + vat_rate) * 100) AS wb_pool_raw
        FROM wb_costs
        WHERE date_from::DATE <= ?
        GROUP BY 1, 2
    """
    pool_df = con.execute(pool_sql, [date_to]).df()

    if commission_df.empty and pool_df.empty:
        return pd.DataFrame(columns=["year", "month", "wb_costs"])

    merged = pd.merge(commission_df, pool_df, on=["year", "month"], how="outer").fillna(0)
    merged["net_comission"] = merged["net_comission"] / 100.0
    merged["wb_pool_raw"] = merged["wb_pool_raw"] / 100.0
    merged["wb_costs"] = merged["net_comission"] - merged["wb_pool_raw"].abs()
    return merged[["year", "month", "wb_costs"]]


# ============================================================
# ОБЩИЕ ДЛЯ ОБОИХ БЛОКОВ РАСХОДЫ ИЗ БУХГАЛТЕРСКОГО ГК (Postgres pl_for_csv)
# ============================================================

def _fetch_gl_costs_monthly(con, date_to):
    """
    "Продвижение" (счета 610000, 620000, статьи с "WB" в названии и
    одновременно относящиеся к рекламе/продвижению/маркетингу) —
    единственная статья, которую в этом блоке по-прежнему берём из
    бухгалтерского ГК: для рекламных расходов нет отдельного контура в
    сырых данных площадки.

    Остальные "WB"-статьи счетов 1.4/1.5 (лояльность, комиссия банка)
    здесь по-прежнему вычисляются (wb_no_promo), но только чтобы
    исключить их из "Прочих накладных расходов" и не задвоить с новым
    комплексным пулом _fetch_wb_cost_pool_monthly — самостоятельной
    строкой на листе wb_no_promo больше не является.

    1.6 (420000) и 1.7 (630000) плюс остаток не-WB статей 1.4/1.5 —
    используются в расчёте чистой прибыли (строка "Прочие накладные
    расходы").

    Себестоимость (счёт 520000, лист 1.3) здесь не участвует: для
    "Средняя с/с" в обоих блоках используется одна и та же
    управленческая FIFO-себестоимость (adjusted_cogs_man).

    Суммы сохраняют исходный знак pl_for_csv (расходы отрицательные),
    поэтому дальше они складываются, а не вычитаются — так же, как
    в pl_data.py.
    """
    sql = """
        SELECT
            EXTRACT(YEAR FROM date_from)::INT AS year,
            EXTRACT(MONTH FROM date_from)::INT AS month,
            regexp_extract(account_name, '^[0-9]+') AS acc,
            COALESCE(cost_item_group, '') AS cost_item_group,
            COALESCE(cost_item, '') AS cost_item,
            SUM(amount)::DOUBLE AS amount
        FROM pg.public.pl_for_csv
        WHERE date_from <= ?
          AND regexp_extract(account_name, '^[0-9]+')
              IN ('610000', '620000', '420000', '630000')
        GROUP BY 1, 2, 3, 4, 5
    """
    df = con.execute(sql, [date_to]).df()

    cols = ["year", "month", "wb_promo", "overhead_non_wb_remainder", "other_1_6", "financial_1_7"]

    if df.empty:
        return pd.DataFrame(columns=cols)

    is_wb = (
        df["cost_item_group"].str.contains("WB", case=False, na=False)
        | df["cost_item"].str.contains("WB", case=False, na=False)
    )
    is_promo = (
        df["cost_item_group"].str.contains(PROMO_PATTERN, case=False, na=False, regex=True)
        | df["cost_item"].str.contains(PROMO_PATTERN, case=False, na=False, regex=True)
    )
    df["is_1415"] = df["acc"].isin(["610000", "620000"])

    out = []
    for (year, month), g in df.groupby(["year", "month"]):
        wb_mask = g["is_1415"] & is_wb.loc[g.index]
        wb_rows = g[wb_mask]
        promo_mask_local = is_promo.loc[wb_rows.index]
        wb_promo = wb_rows.loc[promo_mask_local, "amount"].sum()
        wb_no_promo = wb_rows.loc[~promo_mask_local, "amount"].sum()

        overhead_total_1415 = g.loc[g["is_1415"], "amount"].sum()
        # wb_no_promo исключаем из остатка, чтобы не задваивать с новым
        # комплексным пулом _fetch_wb_cost_pool_monthly.
        overhead_non_wb_remainder = overhead_total_1415 - wb_promo - wb_no_promo

        other_1_6 = g.loc[g["acc"] == "420000", "amount"].sum()
        financial_1_7 = g.loc[g["acc"] == "630000", "amount"].sum()

        out.append({
            "year": year,
            "month": month,
            "wb_promo": wb_promo,
            "overhead_non_wb_remainder": overhead_non_wb_remainder,
            "other_1_6": other_1_6,
            "financial_1_7": financial_1_7,
        })

    return pd.DataFrame(out, columns=cols)


# ============================================================
# «ДО СПП» ДЛЯ КЭШ-БЛОКА: фактическая касса (Postgres cf_to_csv), по ДНЯМ.
# Общий источник с листом PL (см. pl_data.get_pl_report) — поэтому месячные
# суммы на 1.8 и суммы на PL всегда совпадают: это одни и те же дневные
# числа, просто сгруппированные по-разному (по месяцам здесь, по гибким
# периодам FYE/YTD/MTD на PL).
# ============================================================

CF_REVENUE_CODE = "111000"  # "Выручка от продажи товаров" в ДДС (тот же код,
                             # что использует wb_plan_monitor.REVENUE_CODE)


def get_cash_revenue_daily(date_to):
    """
    Дневная факт. касса по статье ДДС 111000 «Выручка от продажи товаров»
    (Postgres cf_to_csv) — с НДС и без НДС (приведение по фактическому
    дневному НДС-соотношению из построчных данных WB, sales.sales_long,
    field='retail_amount', где НДС известен по каждой операции).

    Это ЕДИНЫЙ источник выручки и для кэш-блока 1.8 (агрегируется здесь
    же по месяцам), и для строки «Выручка от основной деятельности» на
    листе PL (агрегируется в pl_data.py по FYE/YTD/MTD/месяцам, день-в-
    день — это нужно, чтобы сравнение YTD/MTD с прошлым годом на ту же
    календарную дату оставалось точным). Раньше PL брал бухгалтерское
    начисление (счёт 410000) — оно не совпадало с кассой на 1.8.
    """
    con = get_duckdb_conn_with_opt(with_pg=True, ro=True)
    try:
        cf_sql = """
            SELECT
                x.date_from::DATE AS rev_date,
                SUM(x.amount)::DOUBLE AS revenue_cf
            FROM pg.public.cf_to_csv x
            JOIN pg.public.corporate_cfitems i ON i.id = x.subconto_id
            JOIN pg.public.corporate_cfitems lv3 ON lv3.id = i.parent_id
            WHERE lv3.code = ?
              AND x.date_from <= ?
            GROUP BY 1
        """
        cf_df = con.execute(cf_sql, [CF_REVENUE_CODE, date_to]).df()

        vat_sql = """
            SELECT
                date_from::DATE AS rev_date,
                COALESCE(SUM(val) FILTER (WHERE oper = 'dt'), 0)
                - COALESCE(SUM(val) FILTER (WHERE oper = 'cr'), 0) AS after_spp_kop,
                COALESCE(SUM(val / (100 + vat_rate) * 100) FILTER (WHERE oper = 'dt'), 0)
                - COALESCE(SUM(val / (100 + vat_rate) * 100) FILTER (WHERE oper = 'cr'), 0) AS after_spp_vatless_kop
            FROM sales.sales_long
            WHERE field = 'retail_amount'
              AND date_from <= ?
            GROUP BY 1
        """
        vat_df = con.execute(vat_sql, [date_to]).df()
    finally:
        con.close()

    if cf_df.empty and vat_df.empty:
        return pd.DataFrame(columns=["rev_date", "revenue_with_vat", "revenue_vatless"])

    merged = pd.merge(cf_df, vat_df, on="rev_date", how="outer").fillna(0)
    merged["after_spp"] = merged["after_spp_kop"] / 100.0
    merged["after_spp_vatless"] = merged["after_spp_vatless_kop"] / 100.0

    def _row(r):
        revenue_cf = float(r.get("revenue_cf", 0.0) or 0.0)
        after_spp = float(r["after_spp"])
        after_spp_vatless = float(r["after_spp_vatless"])

        if revenue_cf <= 0:
            # нет данных ДДС за день (например, ещё не закрыт бухгалтерией) —
            # временно приравниваем «до СПП» к «после СПП», чтобы не
            # показывать пустоту
            revenue_cf = after_spp

        vat_ratio = (after_spp_vatless / after_spp) if after_spp else 0.8333
        if vat_ratio <= 0:
            vat_ratio = 0.8333

        return pd.Series({
            "revenue_with_vat": revenue_cf,
            "revenue_vatless": revenue_cf * vat_ratio,
        })

    est = merged.apply(_row, axis=1)
    out = pd.concat([merged[["rev_date"]], est], axis=1)
    return out.sort_values("rev_date").reset_index(drop=True)


# ============================================================
# СБОРКА БЛОКА (кэш или FIFO) В ТАБЛИЦУ ПОКАЗАТЕЛЕЙ
# ============================================================

def _build_block(merged_df, period_cols_by_ym):
    """
    merged_df — по строке на (year, month), уже содержит:
        sales_qty, returns_qty, net_qty,
        amount_before_spp, amount_before_spp_vatless, amount_after_spp,
        cogs_signed, wb_costs, wb_promo,
        overhead_non_wb_remainder, other_1_6, financial_1_7.

    Чистая прибыль считается ОДИНАКОВО для обоих блоков (кэш и FIFO) —
    снизу вверх, из показателей этого же листа, а не из готовой строки
    листа PL (см. методику в начале файла).
    """
    data = {col: {} for col in ROW_ORDER}

    for _, row in merged_df.iterrows():
        col = period_cols_by_ym.get((int(row["year"]), int(row["month"])))
        if col is None:
            continue

        net_qty = row["net_qty"]
        amount_before_spp = row["amount_before_spp"]
        amount_before_spp_vatless = row["amount_before_spp_vatless"]
        amount_after_spp = row["amount_after_spp"]
        cogs_signed = row["cogs_signed"]
        wb_costs = row.get("wb_costs", 0.0) or 0.0
        wb_promo = row.get("wb_promo", 0.0) or 0.0
        other_overheads = (
            (row.get("overhead_non_wb_remainder", 0.0) or 0.0)
            + (row.get("other_1_6", 0.0) or 0.0)
            + (row.get("financial_1_7", 0.0) or 0.0)
        )

        gross_profit = amount_before_spp_vatless + cogs_signed
        margin_no_promo_abs = gross_profit + wb_costs
        margin_with_promo_abs = margin_no_promo_abs + wb_promo
        net_profit = margin_with_promo_abs + other_overheads

        data[ROW_SALES_QTY][col] = row["sales_qty"]
        data[ROW_RETURNS_QTY][col] = row["returns_qty"]
        data[ROW_NET_QTY][col] = net_qty
        data[ROW_AMOUNT_BEFORE_SPP][col] = amount_before_spp
        data[ROW_AMOUNT_BEFORE_SPP_VATLESS][col] = amount_before_spp_vatless
        data[ROW_AVG_PRICE_BEFORE_SPP][col] = amount_before_spp / net_qty if net_qty else None
        data[ROW_AVG_PRICE_AFTER_SPP][col] = amount_after_spp / net_qty if net_qty else None
        data[ROW_AVG_COGS][col] = abs(cogs_signed) / net_qty if net_qty else None
        data[ROW_WB_COSTS][col] = wb_costs
        data[ROW_PROMO][col] = wb_promo
        data[ROW_OTHER_OVERHEADS][col] = other_overheads
        data[ROW_NET_PROFIT][col] = net_profit
        data[ROW_GROSS_MARGIN][col] = _safe_div(gross_profit, amount_before_spp_vatless)
        data[ROW_MARGIN_NO_PROMO][col] = _safe_div(margin_no_promo_abs, amount_before_spp_vatless)
        data[ROW_MARGIN_WITH_PROMO][col] = _safe_div(margin_with_promo_abs, amount_before_spp_vatless)
        data[ROW_NET_MARGIN][col] = _safe_div(net_profit, amount_before_spp_vatless)

    return pd.DataFrame(data).T.reindex(ROW_ORDER)


def _add_year_totals(df, year_groups):
    """«Итого {год}»: суммы для количеств/сумм и расходных строк —
    простое сложение месяцев; средние ставки (цена после СПП, с/с) —
    средневзвешенное по нетто-штукам; прибыль и % маржинальности —
    пересчитываются из сложенных за год абсолютных сумм — той же
    формулой, что использует лист (и что будет записано в Excel как
    формула), поэтому колонка "Итого" всегда сходится с формулами."""
    if df.empty:
        return df

    for group in year_groups:
        total_col = group["total_col"]
        month_cols = [c for c in group["month_cols"] if c in df.columns]
        if not month_cols:
            continue

        def _sum(row_name):
            return df.loc[row_name, month_cols].astype(float).sum()

        sales_qty = _sum(ROW_SALES_QTY)
        returns_qty = _sum(ROW_RETURNS_QTY)
        net_qty = _sum(ROW_NET_QTY)
        amount_before_spp = _sum(ROW_AMOUNT_BEFORE_SPP)
        amount_before_spp_vatless = _sum(ROW_AMOUNT_BEFORE_SPP_VATLESS)
        wb_costs = _sum(ROW_WB_COSTS)
        wb_promo = _sum(ROW_PROMO)
        other_overheads = _sum(ROW_OTHER_OVERHEADS)

        df.loc[ROW_SALES_QTY, total_col] = sales_qty
        df.loc[ROW_RETURNS_QTY, total_col] = returns_qty
        df.loc[ROW_NET_QTY, total_col] = net_qty
        df.loc[ROW_AMOUNT_BEFORE_SPP, total_col] = amount_before_spp
        df.loc[ROW_AMOUNT_BEFORE_SPP_VATLESS, total_col] = amount_before_spp_vatless
        df.loc[ROW_WB_COSTS, total_col] = wb_costs
        df.loc[ROW_PROMO, total_col] = wb_promo
        df.loc[ROW_OTHER_OVERHEADS, total_col] = other_overheads

        df.loc[ROW_AVG_PRICE_BEFORE_SPP, total_col] = (
            amount_before_spp / net_qty if net_qty else None
        )

        # средневзвешенная цена после СПП и с/с — по нетто-штукам месяцев
        # года (не среднее арифметическое):
        for row_name in (ROW_AVG_PRICE_AFTER_SPP, ROW_AVG_COGS):
            weighted = 0.0
            for mc in month_cols:
                qty = df.loc[ROW_NET_QTY, mc]
                val = df.loc[row_name, mc]
                if qty and val is not None:
                    weighted += float(qty) * float(val)
            df.loc[row_name, total_col] = weighted / net_qty if net_qty else None

        avg_cogs_total = df.loc[ROW_AVG_COGS, total_col]
        avg_cogs_total = float(avg_cogs_total) if avg_cogs_total is not None else 0.0

        gross_profit = amount_before_spp_vatless - avg_cogs_total * net_qty
        margin_no_promo_abs = gross_profit + wb_costs
        margin_with_promo_abs = margin_no_promo_abs + wb_promo
        net_profit = margin_with_promo_abs + other_overheads

        df.loc[ROW_NET_PROFIT, total_col] = net_profit
        df.loc[ROW_GROSS_MARGIN, total_col] = _safe_div(gross_profit, amount_before_spp_vatless)
        df.loc[ROW_MARGIN_NO_PROMO, total_col] = _safe_div(margin_no_promo_abs, amount_before_spp_vatless)
        df.loc[ROW_MARGIN_WITH_PROMO, total_col] = _safe_div(margin_with_promo_abs, amount_before_spp_vatless)
        df.loc[ROW_NET_MARGIN, total_col] = _safe_div(net_profit, amount_before_spp_vatless)

    return df


def get_unit_economics_report(date_to=None):
    if date_to is None:
        with connection.cursor() as cur:
            cur.execute("SELECT MAX(date_from)::date FROM public.pl_for_csv")
            date_to = cur.fetchone()[0]

    date_to = pd.to_datetime(date_to).date()

    con = get_duckdb_conn_with_opt(with_pg=True, ro=True)
    try:
        # Используем боевой BASE_QUERY (тот же, что в daily_sales) вместо
        # собственной сборки - только там есть adjusted_cogs/adjusted_cogs_man
        # (управленческая FIFO-себестоимость с фоллбэком по inventories.pre_wo).
        con.execute(BASE_QUERY)

        cash_raw = _fetch_cash_monthly(con, date_to)
        fifo_raw = _fetch_fifo_monthly(con, date_to)
        gl_df = _fetch_gl_costs_monthly(con, date_to)
        wb_cost_pool_df = _fetch_wb_cost_pool_monthly(con, date_to)
    finally:
        con.close()

    # Дневная касса (общий источник с PL, см. get_cash_revenue_daily) —
    # агрегируем до месяцев здесь же, чтобы месячные суммы «Продажи до
    # СПП» на этом листе гарантированно совпадали с суммами на PL (это
    # одни и те же дневные числа, просто сгруппированные по-разному).
    cash_rev_daily = get_cash_revenue_daily(date_to)
    if not cash_rev_daily.empty:
        cash_rev_daily = cash_rev_daily.copy()
        cash_rev_daily["year"] = pd.to_datetime(cash_rev_daily["rev_date"]).dt.year
        cash_rev_daily["month"] = pd.to_datetime(cash_rev_daily["rev_date"]).dt.month
        cf_revenue_df = cash_rev_daily.groupby(["year", "month"], as_index=False)[
            ["revenue_with_vat", "revenue_vatless"]
        ].sum()
    else:
        cf_revenue_df = pd.DataFrame(columns=["year", "month", "revenue_with_vat", "revenue_vatless"])

    if fifo_raw.empty and cash_raw.empty:
        empty = pd.DataFrame(index=ROW_ORDER)
        return {"date_to": date_to, "year_groups": [], "cash": empty, "fifo": empty}

    years = sorted(set(fifo_raw.get("year", pd.Series(dtype=int))).union(
        set(cash_raw.get("year", pd.Series(dtype=int)))
    ))
    year_groups, ordered_cols = _year_groups(years, date_to.year, date_to.month)
    period_cols_by_ym = {
        (group["year"], m): col
        for group in year_groups
        for m, col in zip(group["months"], group["month_cols"])
    }

    gl_cash = gl_df[["year", "month", "wb_promo"]] if not gl_df.empty else gl_df
    gl_fifo = gl_df[["year", "month", "wb_promo",
                      "overhead_non_wb_remainder", "other_1_6", "financial_1_7"]] if not gl_df.empty else gl_df

    # ---------- Управленческая FIFO-с/с на единицу, по месяцам ----------
    # «Средняя с/с на ед. продаж» считается ОДИНАКОВО в обоих блоках — это
    # одна и та же управленческая себестоимость (adjusted_cogs_man), а не
    # бухгалтерская. Берём готовую пару (сумма FIFO-себестоимости, кол-во
    # чистых продаж FIFO) за месяц и получаем ставку "рублей на единицу",
    # которую затем применяем к фактическому кол-ву чистых продаж КАЖДОГО
    # блока (в кэш-блоке это кол-во может отличаться от FIFO — см.
    # методику на листе).
    fifo_unit_cost_by_ym = {}
    fallback_unit_cost = 0.0
    if not fifo_raw.empty:
        total_cogs_abs = fifo_raw["cogs_man"].abs().sum()
        total_qty = fifo_raw["net_qty"].sum()
        fallback_unit_cost = (total_cogs_abs / total_qty) if total_qty else 0.0
        for r in fifo_raw.itertuples():
            qty = float(r.net_qty)
            fifo_unit_cost_by_ym[(int(r.year), int(r.month))] = (
                abs(float(r.cogs_man)) / qty if qty else fallback_unit_cost
            )

    if not cash_raw.empty:
        cash_merged = cash_raw.merge(gl_cash, on=["year", "month"], how="left")
        cash_merged = cash_merged.merge(cf_revenue_df, on=["year", "month"], how="left")
        cash_merged = cash_merged.merge(wb_cost_pool_df, on=["year", "month"], how="left")
        cash_merged = cash_merged.fillna(0)

        def _cash_cogs(r):
            unit_cost = fifo_unit_cost_by_ym.get(
                (int(r["year"]), int(r["month"])), fallback_unit_cost
            )
            return -abs(unit_cost * float(r.get("net_qty", 0.0) or 0.0))

        cash_merged["cogs_signed"] = cash_merged.apply(_cash_cogs, axis=1)

        # ---------- «До СПП» на кэш-методе: та же дневная касса, что и PL ----------
        # revenue_with_vat / revenue_vatless — месячные суммы дневной кассы
        # по статье 111000 «Выручка от продажи товаров» (получены выше через
        # get_cash_revenue_daily, общую с PL). Никакого отдельного досчёта
        # здесь больше не требуется — только переименование колонок.
        cash_merged["amount_before_spp"] = cash_merged["revenue_with_vat"]
        cash_merged["amount_before_spp_vatless"] = cash_merged["revenue_vatless"]

        cash_df = _build_block(cash_merged, period_cols_by_ym)
    else:
        cash_df = pd.DataFrame(index=ROW_ORDER)

    if not fifo_raw.empty:
        fifo_merged = fifo_raw.merge(gl_fifo, on=["year", "month"], how="left")
        fifo_merged = fifo_merged.merge(wb_cost_pool_df, on=["year", "month"], how="left")
        fifo_merged = fifo_merged.fillna(0)
        fifo_df = _build_block(fifo_merged, period_cols_by_ym)
    else:
        fifo_df = pd.DataFrame(index=ROW_ORDER)

    if not cash_df.empty:
        for c in ordered_cols:
            if c not in cash_df.columns:
                cash_df[c] = None
        cash_df = cash_df.reindex(columns=ordered_cols)

    if not fifo_df.empty:
        for c in ordered_cols:
            if c not in fifo_df.columns:
                fifo_df[c] = None
        fifo_df = fifo_df.reindex(columns=ordered_cols)

    cash_df = _add_year_totals(cash_df, year_groups)
    fifo_df = _add_year_totals(fifo_df, year_groups)

    return {
        "date_to": date_to,
        "year_groups": year_groups,
        "cash": cash_df,
        "fifo": fifo_df,
    }
