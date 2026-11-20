from __future__ import annotations

import os
from pathlib import Path

import duckdb

from django.core.management.base import (
    BaseCommand,
    CommandError,
)

from dotenv import load_dotenv


load_dotenv()


# ============================================================
# РЕКЛАМНЫЕ КАМПАНИИ — ИСТОРИЯ
#
# Один снимок в день на кампанию (load_ad_campaigns.py пишет
# полный список кампаний каждый раз, а не только изменившиеся) --
# тот же принцип истории снимков, что и у orders.fbs_orders_history.
#
# Схема ниже соответствует ответу GET /api/advert/v2/adverts
# (актуально на 23.09.2026, сверено по официальному Swagger).
# ============================================================

AD_CAMPAIGNS_HISTORY = """
CREATE OR REPLACE TABLE
ads.ad_campaigns_history AS

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

    placement_search::BOOLEAN AS placement_search,

    placement_recommendations::BOOLEAN AS placement_recommendations,

    bid_type,

    currency,

    can_change_nms::BOOLEAN AS can_change_nms,

    create_time::TIMESTAMPTZ AS create_time,

    change_time::TIMESTAMPTZ AS change_time,

    start_time::TIMESTAMPTZ AS start_time,

    end_time::TIMESTAMPTZ AS end_time,

    payload

FROM ads.ad_campaigns_raw
"""


# ============================================================
# РЕКЛАМНЫЕ КАМПАНИИ — АКТУАЛЬНОЕ СОСТОЯНИЕ
#
# Самый свежий снимок на кампанию.
# ============================================================

UNPACKED_AD_CAMPAIGNS = """
CREATE OR REPLACE TABLE
ads.unpacked_ad_campaigns AS

SELECT
    *

FROM ads.ad_campaigns_history

QUALIFY
    ROW_NUMBER() OVER (
        PARTITION BY advert_id

        ORDER BY
            loaded_at DESC
    ) = 1
"""


# ============================================================
# ТОВАРЫ ВНУТРИ КАМПАНИЙ — ИСТОРИЯ / АКТУАЛЬНОЕ СОСТОЯНИЕ
#
# GET /api/advert/v2/adverts отдаёт для каждой кампании список
# товаров (nm_id), участвующих в ней, со своими ставками -- это
# позволит в будущем отчёте связать рекламу не только с кампанией
# целиком, но и с конкретной карточкой товара.
# ============================================================

AD_CAMPAIGNS_NM_SETTINGS_HISTORY = """
CREATE OR REPLACE TABLE
ads.ad_campaigns_nm_settings_history AS

SELECT

    _loaded_at::TIMESTAMPTZ AS loaded_at,

    advert_id::BIGINT AS advert_id,

    nm_id::BIGINT AS nm_id,

    subject_id::INTEGER AS subject_id,

    subject_name,

    COALESCE(bid_search_kopecks, 0)::BIGINT AS bid_search_kopecks,

    COALESCE(bid_recommendations_kopecks, 0)::BIGINT AS bid_recommendations_kopecks

FROM ads.ad_campaigns_nm_settings_raw
"""


UNPACKED_AD_CAMPAIGNS_NM_SETTINGS = """
CREATE OR REPLACE TABLE
ads.unpacked_ad_campaigns_nm_settings AS

SELECT
    *

FROM ads.ad_campaigns_nm_settings_history

QUALIFY
    ROW_NUMBER() OVER (
        PARTITION BY
            advert_id,
            nm_id

        ORDER BY
            loaded_at DESC
    ) = 1
"""


# ============================================================
# СТАТИСТИКА ПО ДНЯМ (НА УРОВНЕ КАМПАНИИ) — ИСТОРИЯ
#
# load_ad_campaigns.py каждый раз перезапрашивает окно в
# STATS_WINDOW_DAYS дней назад (WB может донабирать/уточнять
# статистику задним числом), поэтому на одну и ту же дату может
# быть несколько строк из разных запусков -- берём самую свежую
# ниже, в unpacked-таблице.
# ============================================================

AD_CAMPAIGNS_STATS_HISTORY = """
CREATE OR REPLACE TABLE
ads.ad_campaigns_stats_history AS

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
"""


# ============================================================
# СТАТИСТИКА ПО ДНЯМ (НА УРОВНЕ КАМПАНИИ) — АКТУАЛЬНОЕ СОСТОЯНИЕ
#
# Самый свежий снимок на (кампания, дата) -- поздние уточнения WB
# заменяют более раннюю версию того же дня.
# ============================================================

UNPACKED_AD_CAMPAIGNS_STATS = """
CREATE OR REPLACE TABLE
ads.unpacked_ad_campaigns_stats AS

SELECT
    *

FROM ads.ad_campaigns_stats_history

QUALIFY
    ROW_NUMBER() OVER (
        PARTITION BY
            advert_id,
            date

        ORDER BY
            loaded_at DESC
    ) = 1
"""


# ============================================================
# СТАТИСТИКА ПО ДНЯМ И ТОВАРАМ — ИСТОРИЯ / АКТУАЛЬНОЕ СОСТОЯНИЕ
#
# GET /adv/v3/fullstats разбивает каждый день кампании ещё и по
# площадке размещения (app_type) и конкретному товару (nm_id) --
# это самая детальная таблица, именно она свяжет расход на рекламу
# с конкретной карточкой в других отчётах (wb_top_cards_report.py
# и т.п.).
# ============================================================

AD_CAMPAIGNS_STATS_BY_NM_HISTORY = """
CREATE OR REPLACE TABLE
ads.ad_campaigns_stats_by_nm_history AS

SELECT

    loaded_at::TIMESTAMPTZ AS loaded_at,

    advert_id::BIGINT AS advert_id,

    date::DATE AS date,

    app_type::INTEGER AS app_type,

    app_type_name,

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
"""


UNPACKED_AD_CAMPAIGNS_STATS_BY_NM = """
CREATE OR REPLACE TABLE
ads.unpacked_ad_campaigns_stats_by_nm AS

SELECT
    *

FROM ads.ad_campaigns_stats_by_nm_history

QUALIFY
    ROW_NUMBER() OVER (
        PARTITION BY
            advert_id,
            date,
            app_type,
            nm_id

        ORDER BY
            loaded_at DESC
    ) = 1
"""


class Command(BaseCommand):

    help = (
        "Initialize DuckDB tables "
        "for WB advertising campaigns "
        "and daily stats parquet"
    )


    def handle(
        self,
        *args,
        **options,
    ):

        # ====================================================
        # ENV
        # ====================================================

        db_path = os.getenv(
            "DUCKDB_PATH"
        )

        parquet_path = os.getenv(
            "PARQUET_PATH"
        )


        if not db_path:

            raise CommandError(
                "DUCKDB_PATH is not set"
            )


        if not parquet_path:

            raise CommandError(
                "PARQUET_PATH is not set"
            )


        # ====================================================
        # ПАПКА
        # ====================================================

        ads_dir = (
            Path(parquet_path)
            / "ad_campaigns"
        )


        file_globs = {
            "campaigns": (
                f"{ads_dir}/ad_campaigns_info_*.parquet"
            ),
            "nm_settings": (
                f"{ads_dir}/ad_campaigns_nm_settings_*.parquet"
            ),
            "stats": (
                f"{ads_dir}/ad_campaigns_stats_*.parquet"
            ),
            "stats_by_nm": (
                f"{ads_dir}/ad_campaigns_stats_by_nm_*.parquet"
            ),
        }

        # ad_campaigns_stats_*.parquet должен НЕ ловить файлы
        # ad_campaigns_stats_by_nm_*.parquet -- поэтому для "stats"
        # ниже отдельно исключаем "by_nm" при подсчёте файлов
        # (сам read_parquet с звёздочкой их всё равно перепутает,
        # поэтому используем более узкий шаблон при чтении).
        file_globs["stats"] = (
            f"{ads_dir}/ad_campaigns_stats_[0-9]*.parquet"
        )


        found_files = {
            key: list(
                ads_dir.glob(
                    Path(pattern).name
                )
            )
            for key, pattern in file_globs.items()
        }

        # баланс -- один-единственный файл без даты в имени (каждый
        # запуск load_ad_campaigns.py перезаписывает его текущим
        # снимком), поэтому не через glob, а обычной проверкой на
        # существование.
        balance_file = (
            ads_dir
            / "ad_campaigns_balance.parquet"
        )

        have_balance = balance_file.exists()


        if not found_files["campaigns"]:

            raise CommandError(
                "Не найдены parquet кампаний: "
                f"{file_globs['campaigns']}"
            )


        if not found_files["stats"]:

            raise CommandError(
                "Не найдены parquet статистики: "
                f"{file_globs['stats']}"
            )


        self.stdout.write(
            f"DuckDB: {db_path}"
        )

        self.stdout.write(
            f"Ad campaigns parquet path: "
            f"{ads_dir}"
        )

        for key, files in found_files.items():

            self.stdout.write(
                f"{key}: "
                f"{len(files):,} файл(ов)"
            )

        self.stdout.write(
            f"balance: "
            f"{'найден' if have_balance else 'не найден'}"
        )


        try:

            with duckdb.connect(
                db_path
            ) as con:


                # ====================================================
                # SCHEMA
                # ====================================================

                con.execute("""
                    CREATE SCHEMA
                    IF NOT EXISTS ads;
                """)


                # ====================================================
                # RAW VIEWS
                # ====================================================

                con.execute(f"""
                    CREATE OR REPLACE VIEW
                    ads.ad_campaigns_raw AS

                    SELECT *
                    FROM read_parquet(
                        '{file_globs["campaigns"]}',
                        union_by_name=true
                    );
                """)

                con.execute(f"""
                    CREATE OR REPLACE VIEW
                    ads.ad_campaigns_stats_raw AS

                    SELECT *
                    FROM read_parquet(
                        '{file_globs["stats"]}',
                        union_by_name=true
                    );
                """)

                if found_files["nm_settings"]:

                    con.execute(f"""
                        CREATE OR REPLACE VIEW
                        ads.ad_campaigns_nm_settings_raw AS

                        SELECT *
                        FROM read_parquet(
                            '{file_globs["nm_settings"]}',
                            union_by_name=true
                        );
                    """)

                if found_files["stats_by_nm"]:

                    con.execute(f"""
                        CREATE OR REPLACE VIEW
                        ads.ad_campaigns_stats_by_nm_raw AS

                        SELECT *
                        FROM read_parquet(
                            '{file_globs["stats_by_nm"]}',
                            union_by_name=true
                        );
                    """)

                if have_balance:

                    # один файл, всегда текущий снимок -- отдельной
                    # истории здесь не нужно, просто читаем как есть.
                    con.execute(f"""
                        CREATE OR REPLACE VIEW
                        ads.ad_campaigns_balance AS

                        SELECT *
                        FROM read_parquet(
                            '{balance_file}'
                        );
                    """)


                # ====================================================
                # HISTORY / CURRENT — КАМПАНИИ
                # ====================================================

                con.execute(
                    AD_CAMPAIGNS_HISTORY
                )

                con.execute(
                    UNPACKED_AD_CAMPAIGNS
                )


                # ====================================================
                # HISTORY / CURRENT — ТОВАРЫ ВНУТРИ КАМПАНИЙ
                # ====================================================

                have_nm_settings = bool(
                    found_files["nm_settings"]
                )

                if have_nm_settings:

                    con.execute(
                        AD_CAMPAIGNS_NM_SETTINGS_HISTORY
                    )

                    con.execute(
                        UNPACKED_AD_CAMPAIGNS_NM_SETTINGS
                    )

                else:

                    self.stdout.write(
                        self.style.WARNING(
                            "Нет parquet nm_settings (старая версия "
                            "load_ad_campaigns.py?) -- пропускаю эти "
                            "таблицы."
                        )
                    )


                # ====================================================
                # HISTORY / CURRENT — СТАТИСТИКА (КАМПАНИЯ x ДЕНЬ)
                # ====================================================

                con.execute(
                    AD_CAMPAIGNS_STATS_HISTORY
                )

                con.execute(
                    UNPACKED_AD_CAMPAIGNS_STATS
                )


                # ====================================================
                # HISTORY / CURRENT — СТАТИСТИКА (КАМПАНИЯ x ДЕНЬ x ТОВАР)
                # ====================================================

                have_stats_by_nm = bool(
                    found_files["stats_by_nm"]
                )

                if have_stats_by_nm:

                    con.execute(
                        AD_CAMPAIGNS_STATS_BY_NM_HISTORY
                    )

                    con.execute(
                        UNPACKED_AD_CAMPAIGNS_STATS_BY_NM
                    )

                else:

                    self.stdout.write(
                        self.style.WARNING(
                            "Нет parquet stats_by_nm (старая версия "
                            "load_ad_campaigns.py?) -- пропускаю эти "
                            "таблицы."
                        )
                    )


                # ====================================================
                # ДИАГНОСТИКА — КАМПАНИИ
                # ====================================================

                campaigns_count = con.execute("""
                    SELECT
                        COUNT(*)

                    FROM ads.unpacked_ad_campaigns
                """).fetchone()[0]


                active_campaigns = con.execute("""
                    SELECT
                        COUNT(*)

                    FROM ads.unpacked_ad_campaigns

                    WHERE
                        status_name = 'Активна'
                """).fetchone()[0]


                unknown_type = con.execute("""
                    SELECT
                        COUNT(*)

                    FROM ads.unpacked_ad_campaigns

                    WHERE
                        type_name = '—'
                """).fetchone()[0]


                unknown_status = con.execute("""
                    SELECT
                        COUNT(*)

                    FROM ads.unpacked_ad_campaigns

                    WHERE
                        status_name = '—'
                """).fetchone()[0]


                by_payment_type = con.execute("""
                    SELECT
                        COALESCE(payment_type, '—'),
                        COUNT(*)

                    FROM ads.unpacked_ad_campaigns

                    WHERE
                        status_name = 'Активна'

                    GROUP BY
                        1

                    ORDER BY
                        2 DESC
                """).fetchall()


                # ====================================================
                # ДИАГНОСТИКА — СТАТИСТИКА
                # ====================================================

                stats_rows = con.execute("""
                    SELECT
                        COUNT(*)

                    FROM ads.unpacked_ad_campaigns_stats
                """).fetchone()[0]


                stats_date_range = con.execute("""
                    SELECT
                        MIN(date),
                        MAX(date)

                    FROM ads.unpacked_ad_campaigns_stats
                """).fetchone()


                totals_last_30d = con.execute("""
                    SELECT
                        COALESCE(SUM(views), 0),
                        COALESCE(SUM(clicks), 0),
                        COALESCE(SUM(spend_rub), 0),
                        COALESCE(SUM(orders), 0),
                        COALESCE(SUM(revenue_rub), 0)

                    FROM ads.unpacked_ad_campaigns_stats

                    WHERE
                        date >= CURRENT_DATE - INTERVAL 30 DAY
                """).fetchone()


                (
                    views_30d,
                    clicks_30d,
                    spend_30d,
                    orders_30d,
                    revenue_30d,
                ) = totals_last_30d


                drr_30d = (
                    (spend_30d / revenue_30d * 100)
                    if revenue_30d
                    else None
                )

                drr_text = (
                    f"{drr_30d:,.1f}"
                    if drr_30d is not None
                    else "— (нет выручки за период)"
                )


                # ====================================================
                # ДИАГНОСТИКА — СТАТИСТИКА ПО ТОВАРАМ
                # ====================================================

                if have_stats_by_nm:

                    stats_by_nm_rows = con.execute("""
                        SELECT
                            COUNT(*)

                        FROM ads.unpacked_ad_campaigns_stats_by_nm
                    """).fetchone()[0]

                    distinct_nm_advertised = con.execute("""
                        SELECT
                            COUNT(DISTINCT nm_id)

                        FROM ads.unpacked_ad_campaigns_stats_by_nm

                        WHERE
                            date >= CURRENT_DATE - INTERVAL 30 DAY
                    """).fetchone()[0]

                    top_nm_by_spend = con.execute("""
                        SELECT
                            nm_id,
                            ANY_VALUE(title),
                            SUM(spend_rub) AS spend

                        FROM ads.unpacked_ad_campaigns_stats_by_nm

                        WHERE
                            date >= CURRENT_DATE - INTERVAL 30 DAY

                        GROUP BY
                            nm_id

                        ORDER BY
                            spend DESC

                        LIMIT 5
                    """).fetchall()

                else:

                    stats_by_nm_rows = 0
                    distinct_nm_advertised = 0
                    top_nm_by_spend = []


                # ====================================================
                # ДИАГНОСТИКА — БАЛАНС
                # ====================================================

                if have_balance:

                    balance_row = con.execute("""
                        SELECT
                            balance,
                            net,
                            bonus,
                            currency

                        FROM ads.ad_campaigns_balance

                        LIMIT 1
                    """).fetchone()

                else:

                    balance_row = None


                # ====================================================
                # RESULT
                # ====================================================

                payment_type_lines = "\n".join(
                    f"  {name}: {count:,}"
                    for name, count in by_payment_type
                ) or "  (нет активных кампаний)"

                top_nm_lines = "\n".join(
                    f"  nm_id {nm_id} ({title or '—'}): "
                    f"{spend:,.0f} ₽"
                    for nm_id, title, spend in top_nm_by_spend
                ) or "  (нет данных по товарам за 30 дней)"

                self.stdout.write(
                    self.style.SUCCESS(
                        "\n"
                        "ALL AD CAMPAIGNS UNPACKED\n"
                        "----------------------------------------\n"
                        f"Campaigns (current): "
                        f"{campaigns_count:,}\n"
                        f"Active campaigns: "
                        f"{active_campaigns:,}\n"
                        f"Unknown type_name (проверь "
                        f"ADVERT_TYPE_NAMES): "
                        f"{unknown_type:,}\n"
                        f"Unknown status_name (проверь "
                        f"ADVERT_STATUS_NAMES): "
                        f"{unknown_status:,}\n"
                        "\n"
                        "ACTIVE CAMPAIGNS BY PAYMENT TYPE\n"
                        "----------------------------------------\n"
                        f"{payment_type_lines}\n"
                        "\n"
                        "STATS (campaign x day)\n"
                        "----------------------------------------\n"
                        f"Rows: "
                        f"{stats_rows:,}\n"
                        f"Date range: "
                        f"{stats_date_range[0]} .. "
                        f"{stats_date_range[1]}\n"
                        "\n"
                        "STATS BY PRODUCT (campaign x day x nm_id)\n"
                        "----------------------------------------\n"
                        f"Rows: "
                        f"{stats_by_nm_rows:,}\n"
                        f"Distinct nm_id advertised (30d): "
                        f"{distinct_nm_advertised:,}\n"
                        "Top-5 nm_id by ad spend (30d):\n"
                        f"{top_nm_lines}\n"
                        "\n"
                        "LAST 30 DAYS (campaign-level totals)\n"
                        "----------------------------------------\n"
                        f"Views: "
                        f"{views_30d:,.0f}\n"
                        f"Clicks: "
                        f"{clicks_30d:,.0f}\n"
                        f"Spend, ₽: "
                        f"{spend_30d:,.0f}\n"
                        f"Orders (from ads): "
                        f"{orders_30d:,.0f}\n"
                        f"Revenue (from ads), ₽: "
                        f"{revenue_30d:,.0f}\n"
                        f"ДРР (spend/revenue), %: "
                        f"{drr_text}\n"
                        "\n"
                        "BALANCE\n"
                        "----------------------------------------\n"
                        + (
                            f"Net (доступный бюджет): "
                            f"{balance_row[1]:,.0f} {balance_row[3] or ''}\n"
                            f"Balance: "
                            f"{balance_row[0]:,.0f} {balance_row[3] or ''}\n"
                            f"Bonus: "
                            f"{balance_row[2]}\n"
                            if balance_row is not None
                            else "нет файла баланса\n"
                        )
                        + "----------------------------------------"
                    )
                )


        except Exception as e:

            raise CommandError(
                f"DuckDB error: {e}"
            )
