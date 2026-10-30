from __future__ import annotations

import os
from pathlib import Path

import duckdb
from django.core.management.base import BaseCommand, CommandError
from dotenv import load_dotenv


load_dotenv()


# ============================================================
# ИСТОЧНИКИ (parquet из utils/load_ad_campaigns.py)
# ============================================================

SOURCES = {
    "campaigns": "ad_campaigns_info_*.parquet",
    "nm_settings": "ad_campaigns_nm_settings_*.parquet",
    "stats": "ad_campaigns_stats_[0-9]*.parquet",
    "stats_by_nm": "ad_campaigns_stats_by_nm_*.parquet",
    "positions": "ad_campaigns_positions_*.parquet",
    "budget": "ad_campaigns_budget_*.parquet",
    "expenses": "ad_campaigns_expenses_*.parquet",
    "payments": "ad_campaigns_payments_*.parquet",
    "balance": "ad_campaigns_balance*.parquet",
}

REQUIRED = ("campaigns", "stats")


# ============================================================
# КАМПАНИИ
# ============================================================

AD_CAMPAIGNS_HISTORY = """
CREATE OR REPLACE TABLE ads.ad_campaigns_history AS
SELECT
    _loaded_at::TIMESTAMPTZ AS loaded_at,
    _loaded_at::DATE AS snapshot_date,
    advert_id::BIGINT AS advert_id,
    name,
    type::INTEGER AS type,
    type_name,
    status::INTEGER AS status,
    status_name,
    payment_type,
    bid_type,
    placement_search::BOOLEAN AS placement_search,
    placement_recommendations::BOOLEAN AS placement_recommendations,
    currency,
    can_change_nms::BOOLEAN AS can_change_nms,
    create_time::TIMESTAMPTZ AS create_time,
    change_time::TIMESTAMPTZ AS change_time,
    start_time::TIMESTAMPTZ AS start_time,
    end_time::TIMESTAMPTZ AS end_time,
    payload
FROM ads.ad_campaigns_raw
WHERE advert_id IS NOT NULL
"""

UNPACKED_AD_CAMPAIGNS = """
CREATE OR REPLACE TABLE ads.unpacked_ad_campaigns AS
SELECT *
FROM ads.ad_campaigns_history
QUALIFY ROW_NUMBER() OVER (PARTITION BY advert_id ORDER BY loaded_at DESC) = 1
"""


# ============================================================
# ТОВАРЫ В КАМПАНИЯХ
# ============================================================

AD_CAMPAIGNS_NM_SETTINGS_HISTORY = """
CREATE OR REPLACE TABLE ads.ad_campaigns_nm_settings_history AS
SELECT
    _loaded_at::TIMESTAMPTZ AS loaded_at,
    advert_id::BIGINT AS advert_id,
    nm_id::BIGINT AS nm_id,
    subject_id::INTEGER AS subject_id,
    subject_name,
    COALESCE(bid_search_kopecks, 0)::BIGINT AS bid_search_kopecks,
    COALESCE(bid_recommendations_kopecks, 0)::BIGINT AS bid_recommendations_kopecks
FROM ads.ad_campaigns_nm_settings_raw
WHERE advert_id IS NOT NULL AND nm_id IS NOT NULL
"""

# Состав кампании берём из последнего снимка самой кампании: товар,
# убранный из кампании, в актуальный состав не попадает.
UNPACKED_AD_CAMPAIGNS_NM_SETTINGS = """
CREATE OR REPLACE TABLE ads.unpacked_ad_campaigns_nm_settings AS
WITH last_load AS (
    SELECT advert_id, MAX(loaded_at) AS loaded_at
    FROM ads.ad_campaigns_nm_settings_history
    GROUP BY advert_id
)
SELECT h.*
FROM ads.ad_campaigns_nm_settings_history h
JOIN last_load l USING (advert_id, loaded_at)
QUALIFY ROW_NUMBER() OVER (PARTITION BY h.advert_id, h.nm_id ORDER BY h.loaded_at DESC) = 1
"""


# ============================================================
# СТАТИСТИКА: КАМПАНИЯ × ДЕНЬ
# ============================================================

AD_CAMPAIGNS_STATS_HISTORY = """
CREATE OR REPLACE TABLE ads.ad_campaigns_stats_history AS
SELECT
    loaded_at::TIMESTAMPTZ AS loaded_at,
    advert_id::BIGINT AS advert_id,
    date::DATE AS date,
    COALESCE(views, 0)::BIGINT AS views,
    COALESCE(clicks, 0)::BIGINT AS clicks,
    COALESCE(ctr, 0)::DOUBLE AS ctr,
    COALESCE(cpc, 0)::DOUBLE AS cpc,
    COALESCE(sum, 0)::DOUBLE AS spend_rub,
    COALESCE(atbs, 0)::BIGINT AS atbs,
    COALESCE(orders, 0)::BIGINT AS orders,
    COALESCE(cr, 0)::DOUBLE AS cr,
    COALESCE(shks, 0)::BIGINT AS shks,
    COALESCE(sum_price, 0)::DOUBLE AS revenue_rub,
    COALESCE(canceled, 0)::BIGINT AS canceled,
    currency,
    payload
FROM ads.ad_campaigns_stats_raw
WHERE advert_id IS NOT NULL AND date IS NOT NULL
"""

UNPACKED_AD_CAMPAIGNS_STATS = """
CREATE OR REPLACE TABLE ads.unpacked_ad_campaigns_stats AS
SELECT *
FROM ads.ad_campaigns_stats_history
QUALIFY ROW_NUMBER() OVER (PARTITION BY advert_id, date ORDER BY loaded_at DESC) = 1
"""


# ============================================================
# СТАТИСТИКА: КАМПАНИЯ × ДЕНЬ × ПЛАТФОРМА × ТОВАР
# ============================================================

AD_CAMPAIGNS_STATS_BY_NM_HISTORY = """
CREATE OR REPLACE TABLE ads.ad_campaigns_stats_by_nm_history AS
SELECT
    loaded_at::TIMESTAMPTZ AS loaded_at,
    advert_id::BIGINT AS advert_id,
    date::DATE AS date,
    app_type::INTEGER AS app_type,
    CASE app_type::INTEGER
        WHEN 1 THEN 'Сайт'
        WHEN 32 THEN 'Android'
        WHEN 64 THEN 'iOS'
        ELSE 'Другое'
    END AS app_type_name,
    nm_id::BIGINT AS nm_id,
    title,
    COALESCE(views, 0)::BIGINT AS views,
    COALESCE(clicks, 0)::BIGINT AS clicks,
    COALESCE(ctr, 0)::DOUBLE AS ctr,
    COALESCE(cpc, 0)::DOUBLE AS cpc,
    COALESCE(sum, 0)::DOUBLE AS spend_rub,
    COALESCE(atbs, 0)::BIGINT AS atbs,
    COALESCE(orders, 0)::BIGINT AS orders,
    COALESCE(cr, 0)::DOUBLE AS cr,
    COALESCE(shks, 0)::BIGINT AS shks,
    COALESCE(sum_price, 0)::DOUBLE AS revenue_rub,
    COALESCE(canceled, 0)::BIGINT AS canceled
FROM ads.ad_campaigns_stats_by_nm_raw
WHERE advert_id IS NOT NULL AND date IS NOT NULL AND nm_id IS NOT NULL
"""

UNPACKED_AD_CAMPAIGNS_STATS_BY_NM = """
CREATE OR REPLACE TABLE ads.unpacked_ad_campaigns_stats_by_nm AS
SELECT *
FROM ads.ad_campaigns_stats_by_nm_history
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY advert_id, date, app_type, nm_id
    ORDER BY loaded_at DESC
) = 1
"""


# ============================================================
# СРЕДНЯЯ ПОЗИЦИЯ (кампании с единой ставкой)
# ============================================================

AD_CAMPAIGNS_POSITIONS = """
CREATE OR REPLACE TABLE ads.ad_campaigns_positions AS
SELECT
    loaded_at::TIMESTAMPTZ AS loaded_at,
    advert_id::BIGINT AS advert_id,
    date::DATE AS date,
    nm_id::BIGINT AS nm_id,
    avg_position::DOUBLE AS avg_position
FROM ads.ad_campaigns_positions_raw
WHERE advert_id IS NOT NULL AND date IS NOT NULL AND nm_id IS NOT NULL
QUALIFY ROW_NUMBER() OVER (PARTITION BY advert_id, date, nm_id ORDER BY loaded_at DESC) = 1
"""

AD_CAMPAIGNS_POSITIONS_EMPTY = """
CREATE OR REPLACE TABLE ads.ad_campaigns_positions (
    loaded_at TIMESTAMPTZ, advert_id BIGINT, date DATE, nm_id BIGINT, avg_position DOUBLE
)
"""


# ============================================================
# БЮДЖЕТЫ КАМПАНИЙ
# ============================================================

AD_CAMPAIGNS_BUDGET_HISTORY = """
CREATE OR REPLACE TABLE ads.ad_campaigns_budget_history AS
SELECT
    loaded_at::TIMESTAMPTZ AS loaded_at,
    loaded_at::DATE AS snapshot_date,
    advert_id::BIGINT AS advert_id,
    budget_total::DOUBLE AS budget_rub,
    currency
FROM ads.ad_campaigns_budget_raw
WHERE advert_id IS NOT NULL
"""

AD_CAMPAIGNS_BUDGET_HISTORY_EMPTY = """
CREATE OR REPLACE TABLE ads.ad_campaigns_budget_history (
    loaded_at TIMESTAMPTZ, snapshot_date DATE, advert_id BIGINT,
    budget_rub DOUBLE, currency VARCHAR
)
"""

UNPACKED_AD_CAMPAIGNS_BUDGET = """
CREATE OR REPLACE TABLE ads.unpacked_ad_campaigns_budget AS
SELECT *
FROM ads.ad_campaigns_budget_history
QUALIFY ROW_NUMBER() OVER (PARTITION BY advert_id ORDER BY loaded_at DESC) = 1
"""


# ============================================================
# ФАКТИЧЕСКИЕ СПИСАНИЯ И ПОПОЛНЕНИЯ
# ============================================================

AD_CAMPAIGNS_EXPENSES = """
CREATE OR REPLACE TABLE ads.ad_campaigns_expenses AS
SELECT
    loaded_at::TIMESTAMPTZ AS loaded_at,
    upd_num::BIGINT AS upd_num,
    upd_time::TIMESTAMPTZ AS upd_time,
    COALESCE(upd_date::DATE, (upd_time::TIMESTAMPTZ AT TIME ZONE 'Europe/Moscow')::DATE) AS date,
    COALESCE(upd_sum, 0)::DOUBLE AS amount_rub,
    advert_id::BIGINT AS advert_id,
    camp_name,
    advert_type::INTEGER AS advert_type,
    advert_type_name,
    payment_source,
    advert_status::INTEGER AS advert_status
FROM ads.ad_campaigns_expenses_raw
WHERE upd_time IS NOT NULL
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY upd_num, advert_id, upd_time, payment_source
    ORDER BY loaded_at DESC
) = 1
"""

AD_CAMPAIGNS_EXPENSES_EMPTY = """
CREATE OR REPLACE TABLE ads.ad_campaigns_expenses (
    loaded_at TIMESTAMPTZ, upd_num BIGINT, upd_time TIMESTAMPTZ, date DATE,
    amount_rub DOUBLE, advert_id BIGINT, camp_name VARCHAR, advert_type INTEGER,
    advert_type_name VARCHAR, payment_source VARCHAR, advert_status INTEGER
)
"""

AD_CAMPAIGNS_PAYMENTS = """
CREATE OR REPLACE TABLE ads.ad_campaigns_payments AS
SELECT
    loaded_at::TIMESTAMPTZ AS loaded_at,
    payment_id::BIGINT AS payment_id,
    payment_date::TIMESTAMPTZ AS payment_time,
    (payment_date::TIMESTAMPTZ AT TIME ZONE 'Europe/Moscow')::DATE AS date,
    COALESCE(payment_sum, 0)::DOUBLE AS amount_rub,
    payment_type::INTEGER AS payment_type,
    payment_type_name,
    status_id::INTEGER AS status_id,
    card_status,
    currency
FROM ads.ad_campaigns_payments_raw
WHERE payment_id IS NOT NULL
QUALIFY ROW_NUMBER() OVER (PARTITION BY payment_id ORDER BY loaded_at DESC) = 1
"""

AD_CAMPAIGNS_PAYMENTS_EMPTY = """
CREATE OR REPLACE TABLE ads.ad_campaigns_payments (
    loaded_at TIMESTAMPTZ, payment_id BIGINT, payment_time TIMESTAMPTZ, date DATE,
    amount_rub DOUBLE, payment_type INTEGER, payment_type_name VARCHAR,
    status_id INTEGER, card_status VARCHAR, currency VARCHAR
)
"""


# ============================================================
# БАЛАНС КАБИНЕТА
# ============================================================

AD_CAMPAIGNS_BALANCE_HISTORY = """
CREATE OR REPLACE TABLE ads.ad_campaigns_balance_history AS
SELECT
    loaded_at::TIMESTAMPTZ AS loaded_at,
    balance::DOUBLE AS balance,
    net::DOUBLE AS net,
    bonus::DOUBLE AS bonus,
    currency,
    cashbacks_total::DOUBLE AS cashbacks_total
FROM ads.ad_campaigns_balance_raw
QUALIFY ROW_NUMBER() OVER (PARTITION BY loaded_at ORDER BY loaded_at) = 1
"""

AD_CAMPAIGNS_BALANCE = """
CREATE OR REPLACE TABLE ads.ad_campaigns_balance AS
SELECT *
FROM ads.ad_campaigns_balance_history
ORDER BY loaded_at DESC
LIMIT 1
"""


class Command(BaseCommand):

    help = "Сборка таблиц ads.* из parquet рекламных кампаний WB"

    def handle(self, *args, **options):
        db_path = os.getenv("DUCKDB_PATH")
        parquet_path = os.getenv("PARQUET_PATH")

        if not db_path:
            raise CommandError("DUCKDB_PATH is not set")
        if not parquet_path:
            raise CommandError("PARQUET_PATH is not set")

        ads_dir = Path(parquet_path) / "ad_campaigns"
        files = {key: sorted(ads_dir.glob(pattern)) for key, pattern in SOURCES.items()}

        for key in REQUIRED:
            if not files[key]:
                raise CommandError(f"Нет parquet: {ads_dir / SOURCES[key]}")

        self.stdout.write(f"DuckDB: {db_path}")
        self.stdout.write(f"Parquet: {ads_dir}")
        for key, found in files.items():
            self.stdout.write(f"  {key}: {len(found):,}")

        try:
            with duckdb.connect(db_path) as con:
                con.execute("CREATE SCHEMA IF NOT EXISTS ads")

                def raw_view(name: str, key: str) -> bool:
                    if not files[key]:
                        con.execute(f"DROP VIEW IF EXISTS ads.{name}")
                        return False
                    paths = ", ".join(f"'{p}'" for p in files[key])
                    con.execute(f"""
                        CREATE OR REPLACE VIEW ads.{name} AS
                        SELECT * FROM read_parquet([{paths}], union_by_name = true)
                    """)
                    return True

                raw_view("ad_campaigns_raw", "campaigns")
                raw_view("ad_campaigns_stats_raw", "stats")

                con.execute(AD_CAMPAIGNS_HISTORY)
                con.execute(UNPACKED_AD_CAMPAIGNS)
                con.execute(AD_CAMPAIGNS_STATS_HISTORY)
                con.execute(UNPACKED_AD_CAMPAIGNS_STATS)

                if raw_view("ad_campaigns_nm_settings_raw", "nm_settings"):
                    con.execute(AD_CAMPAIGNS_NM_SETTINGS_HISTORY)
                    con.execute(UNPACKED_AD_CAMPAIGNS_NM_SETTINGS)

                if raw_view("ad_campaigns_stats_by_nm_raw", "stats_by_nm"):
                    con.execute(AD_CAMPAIGNS_STATS_BY_NM_HISTORY)
                    con.execute(UNPACKED_AD_CAMPAIGNS_STATS_BY_NM)

                con.execute(
                    AD_CAMPAIGNS_POSITIONS
                    if raw_view("ad_campaigns_positions_raw", "positions")
                    else AD_CAMPAIGNS_POSITIONS_EMPTY
                )

                con.execute(
                    AD_CAMPAIGNS_BUDGET_HISTORY
                    if raw_view("ad_campaigns_budget_raw", "budget")
                    else AD_CAMPAIGNS_BUDGET_HISTORY_EMPTY
                )
                con.execute(UNPACKED_AD_CAMPAIGNS_BUDGET)

                con.execute(
                    AD_CAMPAIGNS_EXPENSES
                    if raw_view("ad_campaigns_expenses_raw", "expenses")
                    else AD_CAMPAIGNS_EXPENSES_EMPTY
                )

                con.execute(
                    AD_CAMPAIGNS_PAYMENTS
                    if raw_view("ad_campaigns_payments_raw", "payments")
                    else AD_CAMPAIGNS_PAYMENTS_EMPTY
                )

                con.execute("DROP VIEW IF EXISTS ads.ad_campaigns_balance")
                if raw_view("ad_campaigns_balance_raw", "balance"):
                    con.execute(AD_CAMPAIGNS_BALANCE_HISTORY)
                    con.execute(AD_CAMPAIGNS_BALANCE)
                else:
                    con.execute("DROP TABLE IF EXISTS ads.ad_campaigns_balance")

                self._report(con)

        except CommandError:
            raise
        except Exception as exc:
            raise CommandError(f"DuckDB error: {exc}")

    def _report(self, con):
        def one(sql):
            return con.execute(sql).fetchone()

        def exists(table):
            return one(f"""
                SELECT COUNT(*) FROM information_schema.tables
                WHERE table_schema = 'ads' AND table_name = '{table}'
            """)[0] > 0

        campaigns, active, paused, unknown = one("""
            SELECT
                COUNT(*),
                COUNT(*) FILTER (WHERE status = 9),
                COUNT(*) FILTER (WHERE status = 11),
                COUNT(*) FILTER (WHERE type_name = '—' OR status_name = '—')
            FROM ads.unpacked_ad_campaigns
        """)

        stats_rows, date_min, date_max = one("""
            SELECT COUNT(*), MIN(date), MAX(date) FROM ads.unpacked_ad_campaigns_stats
        """)

        spend_30, revenue_30, orders_30 = one("""
            SELECT COALESCE(SUM(spend_rub), 0), COALESCE(SUM(revenue_rub), 0), COALESCE(SUM(orders), 0)
            FROM ads.unpacked_ad_campaigns_stats
            WHERE date >= CURRENT_DATE - INTERVAL 30 DAY
        """)

        charged_30 = one("""
            SELECT COALESCE(SUM(amount_rub), 0) FROM ads.ad_campaigns_expenses
            WHERE date >= CURRENT_DATE - INTERVAL 30 DAY
        """)[0]

        topups_30 = one("""
            SELECT COALESCE(SUM(amount_rub), 0) FROM ads.ad_campaigns_payments
            WHERE date >= CURRENT_DATE - INTERVAL 30 DAY
        """)[0]

        budgets_n, budgets_sum = one("""
            SELECT COUNT(*), COALESCE(SUM(budget_rub), 0) FROM ads.unpacked_ad_campaigns_budget
        """)

        nm_rows = (
            one("SELECT COUNT(*) FROM ads.unpacked_ad_campaigns_stats_by_nm")[0]
            if exists("unpacked_ad_campaigns_stats_by_nm") else 0
        )

        balance = (
            one("SELECT net, balance, bonus FROM ads.ad_campaigns_balance")
            if exists("ad_campaigns_balance") else None
        )

        drr = f"{spend_30 / revenue_30 * 100:.1f} %" if revenue_30 else "—"
        gap = spend_30 - charged_30

        lines = [
            "",
            "ADS UNPACKED",
            "-" * 48,
            f"Кампаний: {campaigns:,} (активных {active:,}, на паузе {paused:,})",
            f"Без расшифровки типа/статуса: {unknown:,}",
            f"Статистика кампания×день: {stats_rows:,} ({date_min} .. {date_max})",
            f"Статистика товар×день: {nm_rows:,}",
            "",
            "ПОСЛЕДНИЕ 30 ДНЕЙ",
            "-" * 48,
            f"Расход по статистике: {spend_30:,.0f} ₽",
            f"Списано по документам: {charged_30:,.0f} ₽ (разница {gap:,.0f} ₽)",
            f"Пополнения счёта: {topups_30:,.0f} ₽",
            f"Заказы: {orders_30:,.0f}, сумма заказов {revenue_30:,.0f} ₽, ДРР {drr}",
            "",
            "БЮДЖЕТЫ И БАЛАНС",
            "-" * 48,
            f"Бюджеты кампаний: {budgets_n:,} шт., {budgets_sum:,.0f} ₽",
            (
                f"Баланс кабинета: net {balance[0] or 0:,.0f} ₽, "
                f"balance {balance[1] or 0:,.0f} ₽, бонусы {balance[2] or 0:,.0f} ₽"
                if balance else "Баланс кабинета: нет данных"
            ),
            "-" * 48,
        ]

        self.stdout.write(self.style.SUCCESS("\n".join(lines)))
