# gear/app/daily_sales/stocks/data.py

from datetime import date, timedelta

from conns import get_duckdb_conn_with_opt


def get_default_stocks_date():
    return date.today() - timedelta(days=1)


def get_stocks_export_data(report_date):
    """
    Детальная выгрузка остатков для Excel.

    Важно:
    - себестоимость приходит в копейках;
    - в рубли переводим уже в excel.py;
    - NM ID и Chrt ID оставляем, но в Excel переносим в конец.
    """
    with get_duckdb_conn_with_opt() as con:
        df = con.execute(
            """
            WITH stocks AS (
                SELECT
                    t.date_from::DATE AS date_from,
                    u.usk,
                    t.nm_id,
                    t.chrt_id,

                    SUM(COALESCE(t.quantity, 0)) AS quantity_on_hand,
                    SUM(COALESCE(t.in_way_from_client, 0)) AS in_way_from_client,
                    SUM(COALESCE(t.in_way_to_client, 0)) AS in_way_to_client,
                    SUM(
                        COALESCE(t.quantity, 0)
                        + COALESCE(t.in_way_from_client, 0)
                        + COALESCE(t.in_way_to_client, 0)
                    ) AS total_quantity,

                    MAX(w.adjust_wo[-1]) AS last_costs,
                    MAX(w.adjust_man_wo[-1]) AS last_man_costs

                FROM stocks.unpacked_stocks t
                LEFT JOIN inventories.usk u
                    ON u.card_id = t.nm_id
                LEFT JOIN inventories.pre_wo w
                    ON w.usk = u.usk

                WHERE t.date_from::DATE = $report_date::DATE

                GROUP BY
                    t.date_from::DATE,
                    u.usk,
                    t.nm_id,
                    t.chrt_id
            ),

            brands AS (
                SELECT
                    nm_id,
                    COALESCE(MAX(brand), 'Бренд не указан') AS brand
                FROM cards.unpacked_cards
                GROUP BY nm_id
            )

            SELECT
                s.date_from AS "Дата",

                s.usk AS "USK",

                COALESCE(b.brand, 'Бренд не указан') AS "Бренд",
                COALESCE(p.subject_name, 'Категория не указана') AS "Категория",
                COALESCE(p.gender, 'Пол не указан') AS "Пол",
                COALESCE(p.sa_name, '') AS "Артикул",
                COALESCE(p.title, '') AS "Наименование",
                COALESCE(sz.tech_size, '') AS "Размер",

                s.total_quantity AS "Итого количество",
                s.quantity_on_hand AS "Остаток на складе",
                s.in_way_from_client AS "В пути от клиента",
                s.in_way_to_client AS "В пути к клиенту",

                s.last_costs AS "Бух. с/с за ед.",
                s.last_man_costs AS "Упр. с/с за ед.",

                s.total_quantity * COALESCE(s.last_costs, 0) AS "Бух. с/с всего",
                s.total_quantity * COALESCE(s.last_man_costs, 0) AS "Упр. с/с всего",

                s.nm_id AS "NM ID",
                s.chrt_id AS "Chrt ID"

            FROM stocks s
            LEFT JOIN cards.product p
                ON p.nm_id = s.nm_id
            LEFT JOIN brands b
                ON b.nm_id = s.nm_id
            LEFT JOIN cards.sizes sz
                ON sz.chrt_id = s.chrt_id

            WHERE s.total_quantity > 0

            ORDER BY
                COALESCE(b.brand, 'Бренд не указан'),
                COALESCE(p.subject_name, 'Категория не указана'),
                COALESCE(p.title, ''),
                COALESCE(sz.tech_size, '')
            """,
            {"report_date": report_date},
        ).df()

    return df


def get_stocks_summary_stats(report_date):
    with get_duckdb_conn_with_opt() as con:
        warehouse_row = con.execute(
            """
            SELECT 
                COUNT(DISTINCT warehouse_name) AS total_warehouses,
                SUM(COALESCE(quantity, 0)) AS total_on_hand,
                SUM(
                    COALESCE(in_way_to_client, 0)
                    + COALESCE(in_way_from_client, 0)
                ) AS total_in_transit,
                SUM(
                    COALESCE(quantity, 0)
                    + COALESCE(in_way_to_client, 0)
                    + COALESCE(in_way_from_client, 0)
                ) AS total_quantity
            FROM stocks.unpacked_stocks
            WHERE date_from::DATE = $report_date::DATE
            """,
            {"report_date": report_date},
        ).fetchone()

        product_row = con.execute(
            """
            WITH stocks AS (
                SELECT
                    t.nm_id,
                    t.chrt_id,
                    SUM(
                        COALESCE(t.quantity, 0)
                        + COALESCE(t.in_way_to_client, 0)
                        + COALESCE(t.in_way_from_client, 0)
                    ) AS qty
                FROM stocks.unpacked_stocks t
                WHERE t.date_from::DATE = $report_date::DATE
                GROUP BY
                    t.nm_id,
                    t.chrt_id
            ),

            brands AS (
                SELECT
                    nm_id,
                    COALESCE(MAX(brand), 'Бренд не указан') AS brand
                FROM cards.unpacked_cards
                GROUP BY nm_id
            )

            SELECT
                COUNT(DISTINCT s.nm_id) AS total_products,
                COUNT(DISTINCT b.brand) AS total_brands,
                COUNT(*) AS total_positions,
                COUNT(DISTINCT p.subject_name) AS total_categories
            FROM stocks s
            LEFT JOIN cards.product p
                ON p.nm_id = s.nm_id
            LEFT JOIN brands b
                ON b.nm_id = s.nm_id
            WHERE s.qty > 0
            """,
            {"report_date": report_date},
        ).fetchone()

    return {
        "total_warehouses": warehouse_row[0] or 0,
        "total_on_hand": warehouse_row[1] or 0,
        "total_in_transit": warehouse_row[2] or 0,
        "total_quantity": warehouse_row[3] or 0,

        "total_products": product_row[0] or 0,
        "total_brands": product_row[1] or 0,
        "total_positions": product_row[2] or 0,
        "total_categories": product_row[3] or 0,

        "report_date": report_date,
    }


def get_stocks_by_warehouse_extended(report_date):
    with get_duckdb_conn_with_opt() as con:
        df = con.execute(
            """
            SELECT 
                COALESCE(region_name, 'Регион не указан') AS "регион",
                COUNT(DISTINCT warehouse_name) AS "складов",
                SUM(COALESCE(quantity, 0)) AS "на_складе",
                SUM(
                    COALESCE(in_way_to_client, 0)
                    + COALESCE(in_way_from_client, 0)
                ) AS "в_пути",
                SUM(
                    COALESCE(quantity, 0)
                    + COALESCE(in_way_to_client, 0)
                    + COALESCE(in_way_from_client, 0)
                ) AS "итого"
            FROM stocks.unpacked_stocks
            WHERE date_from::DATE = $report_date::DATE
            GROUP BY COALESCE(region_name, 'Регион не указан')
            ORDER BY "итого" DESC
            """,
            {"report_date": report_date},
        ).df()

    return df