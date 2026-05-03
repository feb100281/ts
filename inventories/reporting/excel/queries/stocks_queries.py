# inventories/reporting/excel/queries/stocks_queries.py
import os
import duckdb
from dotenv import load_dotenv
from typing import Dict
import pandas as pd

load_dotenv()
db_path = os.getenv("DUCKDB_PATH")

class StocksQueries:
    """Запросы к DuckDB для отчета по остаткам"""
    
    def __init__(self):
        self.db_path = db_path
    
    
    def get_stocks_data(self, report_date: str) -> pd.DataFrame:
        """Детальная информация по остаткам на дату с брендом и размерами"""
        con = duckdb.connect(self.db_path)

        query = """
                WITH x AS (
                    SELECT
                        t.date_from,
                        t.nm_id,
                        t.chrt_id,
                        SUM(COALESCE(t.quantity, 0)) AS quantity_on_hand,
                        SUM(COALESCE(t.in_way_to_client, 0) + COALESCE(t.in_way_from_client, 0)) AS quantity_in_transit,
                        SUM(
                            COALESCE(t.quantity, 0)
                            + COALESCE(t.in_way_to_client, 0)
                            + COALESCE(t.in_way_from_client, 0)
                        ) AS qty
                    FROM stocks.unpacked_stocks t
                    WHERE t.date_from = $date
                    GROUP BY
                        t.date_from,
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
                    x.nm_id AS nm_id,
                    COALESCE(b.brand, 'Бренд не указан') AS бренд,
                    p.sa_name AS артикул,
                    p.subject_name AS категория,
                    p.gender AS пол,
                    p.title AS наименование,
                    LIST(CONCAT(x.qty::text, ' шт -> ', s.tech_size)) AS доступные_размеры,
                    SUM(x.quantity_on_hand) AS на_складе,
                    SUM(x.quantity_in_transit) AS в_пути,
                    SUM(x.qty) AS количество
                FROM x
                LEFT JOIN cards.product p ON p.nm_id = x.nm_id
                LEFT JOIN brands b ON b.nm_id = x.nm_id
                LEFT JOIN cards.sizes s ON s.chrt_id = x.chrt_id
                WHERE x.qty > 0
                GROUP BY
                    x.nm_id,
                    b.brand,
                    p.sa_name,
                    p.subject_name,
                    p.gender,
                    p.title
                ORDER BY
                    SUM(x.qty) DESC,
                    COALESCE(b.brand, 'Бренд не указан'),
                    p.title
            """

        try:
            df = con.execute(query, {"date": report_date}).df()

            if 'доступные_размеры' in df.columns:
                df['доступные_размеры'] = df['доступные_размеры'].apply(
                    lambda x: ', '.join(str(v) for v in x)
                    if hasattr(x, '__iter__') and not isinstance(x, str)
                    else str(x) if x else ''
                )

            return df
        finally:
            con.close()

    
    
    def get_stocks_by_category(self, report_date: str) -> pd.DataFrame:
        """Получить остатки по категориям с разбивкой по полу"""
        con = duckdb.connect(self.db_path)
        
        query = f"""
            WITH a AS (
                SELECT 
                    COALESCE(gender, 'Пол не указан') as gender,
                    subject_name,
                    SUM(qty) AS qty
                FROM reports_stocks.stocks_by_product
                WHERE date_from = '{report_date}'
                GROUP BY 
                    gender,
                    subject_name
            )
            SELECT 
                subject_name as 'категория',
                LIST(
                    CONCAT(
                        gender,
                        ' -> ',
                        qty::text,
                        ' шт'
                    )
                ) AS 'разбивка_по_полу',
                SUM(qty) as 'всего'
            FROM a
            GROUP BY subject_name
            ORDER BY SUM(qty) DESC
        """
        
        try:
            df = con.execute(query).df()
            
            # Преобразуем список/массив в строку
            if 'разбивка_по_полу' in df.columns:
                df['разбивка_по_полу'] = df['разбивка_по_полу'].apply(
                    lambda x: '\n'.join(str(v) for v in x) if hasattr(x, '__iter__') and not isinstance(x, str) else str(x) if x else ''
                )
            
            return df
        finally:
            con.close()
        
    
    def get_summary_stats(self, report_date: str) -> Dict:
        """Получить сводную статистику"""
        con = duckdb.connect(self.db_path)
    
        query_warehouse = """
            SELECT 
                COUNT(DISTINCT warehouse_name) as total_warehouses,
                SUM(quantity) as total_on_hand,
                SUM(in_way_to_client + in_way_from_client) as total_in_transit,
                SUM(quantity + in_way_to_client + in_way_from_client) as total_all
            FROM stocks.unpacked_stocks
            WHERE date_from = $date
        """
        
        # Статистика по товарам (для других отчетов, не для карты)
        query_products = """
            SELECT 
                COUNT(DISTINCT nm_id) as total_products,
                COUNT(DISTINCT sa_name) as total_brands,
                COUNT(*) as total_positions,
                COUNT(DISTINCT subject_name) as total_categories
            FROM reports_stocks.stocks_by_product 
            WHERE date_from = $date
            AND qty > 0
        """
        
        try:
            warehouse_result = con.execute(query_warehouse, {"date": report_date}).fetchone()
            products_result = con.execute(query_products, {"date": report_date}).fetchone()
            
            return {
                # Данные для карты (из warehouse)
                'total_warehouses': warehouse_result[0] or 0,
                'total_on_hand': warehouse_result[1] or 0,      # на складах
                'total_in_transit': warehouse_result[2] or 0,   # в пути
                'total_quantity': warehouse_result[3] or 0,     # всего
                
                # Данные для других отчетов (из products)
                'total_products': products_result[0] or 0,
                'total_brands': products_result[1] or 0,
                'total_positions': products_result[2] or 0,
                'total_categories': products_result[3] or 0,
                
                'report_date': report_date
            }
        finally:
            con.close()
        
        
    def get_stocks_by_gender(self, report_date: str) -> pd.DataFrame:
        """Получить остатки по полу"""
        con = duckdb.connect(self.db_path)
        query = """
            SELECT 
                COALESCE(gender, 'не указан') as пол,
                SUM(qty) as количество,
                COUNT(DISTINCT nm_id) as товаров
            FROM reports_stocks.stocks_by_product 
            WHERE date_from = $date
              AND qty > 0
            GROUP BY gender
            ORDER BY количество DESC
        """
        try:
            df = con.execute(query, {"date": report_date}).df()
            return df
        finally:
            con.close()
            

    def get_stocks_by_warehouse(self, report_date: str) -> pd.DataFrame:
        """Получить остатки по складам из stocks.unpacked_stocks"""
        con = duckdb.connect(self.db_path)
        query = """
            SELECT 
                warehouse_name,
                region_name,
                SUM(quantity) as quantity_on_hand,
                SUM(in_way_to_client) as in_way_to_client,
                SUM(in_way_from_client) as in_way_from_client,
                SUM(quantity + in_way_to_client + in_way_from_client) as total
            FROM stocks.unpacked_stocks
            WHERE date_from = $date
            GROUP BY warehouse_name, region_name
            ORDER BY total DESC
        """
        try:
            df = con.execute(query, {"date": report_date}).df()
            # Переименовываем колонки для читаемости
            df.columns = ['склад', 'регион', 'на_складе', 'в_пути_к_клиенту', 'в_пути_от_клиента', 'итого']
            return df
        finally:
            con.close()
            
            
    def get_stocks_by_warehouse_extended(self, report_date: str) -> pd.DataFrame:
        """Расширенная версия: возвращает регион, итого, в пути, количество складов"""
        con = duckdb.connect(self.db_path)
        query = """
            SELECT 
                region_name,
                COUNT(DISTINCT warehouse_name) as warehouses_count,
                SUM(quantity) as total_on_hand,
                SUM(in_way_to_client + in_way_from_client) as total_in_transit,
                SUM(quantity + in_way_to_client + in_way_from_client) as total
            FROM stocks.unpacked_stocks
            WHERE date_from = $date
            GROUP BY region_name
            ORDER BY total DESC
        """
        try:
            df = con.execute(query, {"date": report_date}).df()
            # Переименовываем колонки
            df.columns = ['регион', 'складов', 'на_складе', 'в_пути', 'итого']
            return df
        finally:
            con.close()
            
                  
    def get_stocks_by_brand(self, report_date: str) -> pd.DataFrame:
        """Анализ остатков по брендам без использования view"""
        con = duckdb.connect(self.db_path)

        query = """
            WITH x AS (
                SELECT
                    t.date_from,
                    t.nm_id,
                    SUM(COALESCE(t.quantity, 0)) AS quantity_on_hand,
                    SUM(COALESCE(t.in_way_to_client, 0) + COALESCE(t.in_way_from_client, 0)) AS quantity_in_transit,
                    SUM(
                        COALESCE(t.quantity, 0)
                        + COALESCE(t.in_way_to_client, 0)
                        + COALESCE(t.in_way_from_client, 0)
                    ) AS qty
                FROM stocks.unpacked_stocks t
                WHERE t.date_from = $date
                GROUP BY
                    t.date_from,
                    t.nm_id
            ),

            brands AS (
                SELECT
                    nm_id,
                    COALESCE(MAX(brand), 'Бренд не указан') AS brand
                FROM cards.unpacked_cards
                GROUP BY nm_id
            ),

            brand_stats AS (
                SELECT
                    b.brand AS бренд,
                    COUNT(DISTINCT x.nm_id) AS товаров,
                    SUM(x.quantity_on_hand) AS на_складе,
                    SUM(x.quantity_in_transit) AS в_пути,
                    SUM(x.qty) AS итого
                FROM x
                LEFT JOIN brands b ON b.nm_id = x.nm_id
                WHERE x.qty > 0
                GROUP BY b.brand
            )

            SELECT
                бренд,
                товаров,
                на_складе,
                в_пути,
                итого,
                ROUND(
                    итого * 100.0 / NULLIF(SUM(итого) OVER (), 0),
                    2
                ) AS доля_остатков_проц
            FROM brand_stats
            ORDER BY итого DESC
        """

        try:
            return con.execute(query, {"date": report_date}).df()
        finally:
            con.close()
            
            
    
    
    
    def get_inventory_turnover(self, report_date: str, days: int = 90, min_sales_days: int = 60) -> pd.DataFrame:
        """Расчет оборачиваемости остатков за последние N дней + диагностика продаж.

        Логика:
        - Продано за период = продажи за последние `days` дней до даты отчета включительно.
        - Дней без продаж = разница между датой отчета и последней продажей.
        - Новый товар = первая продажа была менее `min_sales_days` дней назад.
        - Для новых товаров запас в днях/месяцах не рассчитывается.
        """
        con = duckdb.connect(self.db_path)

        query = """
            WITH stocks AS (
                SELECT
                    t.nm_id,
                    SUM(
                        COALESCE(t.quantity, 0)
                        + COALESCE(t.in_way_to_client, 0)
                        + COALESCE(t.in_way_from_client, 0)
                    ) AS stock_qty
                FROM stocks.unpacked_stocks t
                WHERE t.date_from = $date
                GROUP BY t.nm_id
            ),

            sales_period AS (
                SELECT
                    nm_id,
                    SUM(
                        CASE
                            WHEN oper = 'dt' THEN 1
                            WHEN oper = 'cr' THEN -1
                            ELSE 0
                        END
                    ) AS sold_qty_period
                FROM sales.sales_long
                WHERE field = 'retail_price'
                AND date_from BETWEEN ($date::DATE - ($days::INTEGER - 1)) AND $date::DATE
                GROUP BY nm_id
            ),

            sales_history AS (
                SELECT
                    nm_id,
                    MIN(date_from) AS first_sale_date,
                    MAX(date_from) AS last_sale_date,
                    SUM(
                        CASE
                            WHEN oper = 'dt' THEN 1
                            WHEN oper = 'cr' THEN -1
                            ELSE 0
                        END
                    ) AS sold_qty_lifetime
                FROM sales.sales_long
                WHERE field = 'retail_price'
                GROUP BY nm_id
            ),

            brands AS (
                SELECT
                    nm_id,
                    COALESCE(MAX(brand), 'Бренд не указан') AS brand
                FROM cards.unpacked_cards
                GROUP BY nm_id
            ),

            base AS (
                SELECT
                    s.nm_id,
                    COALESCE(b.brand, 'Бренд не указан') AS бренд,
                    p.sa_name AS артикул,
                    p.subject_name AS категория,
                    p.gender AS пол,
                    p.title AS наименование,
                    ARRAY_TO_STRING(p.available_sizes, ', ') AS доступные_размеры,

                    s.stock_qty AS остаток,

                    COALESCE(sp.sold_qty_period, 0) AS продано_за_период,
                    COALESCE(sh.sold_qty_lifetime, 0) AS продано_за_все_время,

                    ($date::DATE - ($days::INTEGER - 1)) AS начало_периода_продаж,
                    $date::DATE AS конец_периода_продаж,

                    sh.first_sale_date AS первая_продажа,
                    sh.last_sale_date AS последняя_продажа,

                    CASE
                        WHEN sh.last_sale_date IS NULL THEN NULL
                        ELSE ($date::DATE - sh.last_sale_date)
                    END AS дней_с_последней_продажи,

                    CASE
                        WHEN sh.first_sale_date IS NULL THEN NULL
                        ELSE ($date::DATE - sh.first_sale_date)
                    END AS возраст_продаж_дней,

                    CASE
                        WHEN sh.first_sale_date IS NULL THEN NULL
                        ELSE LEAST($days::INTEGER, ($date::DATE - sh.first_sale_date) + 1)
                    END AS дней_наблюдения,

                    CASE
                        WHEN sh.first_sale_date IS NOT NULL
                        AND (($date::DATE - sh.first_sale_date) < $min_sales_days::INTEGER)
                        THEN TRUE
                        ELSE FALSE
                    END AS новый_товар

                FROM stocks s
                LEFT JOIN sales_period sp ON sp.nm_id = s.nm_id
                LEFT JOIN sales_history sh ON sh.nm_id = s.nm_id
                LEFT JOIN cards.product p ON p.nm_id = s.nm_id
                LEFT JOIN brands b ON b.nm_id = s.nm_id
                WHERE s.stock_qty > 0
            )

            SELECT
                *,

                CASE
                    WHEN новый_товар THEN NULL
                    WHEN COALESCE(продано_за_период, 0) <= 0 THEN NULL
                    ELSE ROUND(продано_за_период / NULLIF(дней_наблюдения, 0), 2)
                END AS средние_продажи_в_день,

                CASE
                    WHEN новый_товар THEN NULL
                    WHEN COALESCE(продано_за_период, 0) <= 0 THEN NULL
                    ELSE ROUND(продано_за_период / NULLIF(дней_наблюдения, 0) * 30, 2)
                END AS средние_продажи_в_месяц,

                CASE
                    WHEN новый_товар THEN NULL
                    WHEN COALESCE(продано_за_период, 0) <= 0 THEN NULL
                    ELSE ROUND(остаток / NULLIF(продано_за_период / NULLIF(дней_наблюдения, 0), 0), 0)::INTEGER
                END AS дней_остатка,

                CASE
                    WHEN новый_товар THEN NULL
                    WHEN COALESCE(продано_за_период, 0) <= 0 THEN NULL
                    ELSE ROUND(остаток / NULLIF(продано_за_период / NULLIF(дней_наблюдения, 0) * 30, 0), 2)
                END AS месяцев_остатка,

                CASE
                    WHEN первая_продажа IS NULL THEN 'NO SALES EVER'
                    WHEN новый_товар THEN 'NEW ITEM'
                    WHEN COALESCE(продано_за_период, 0) <= 0 THEN 'NO SALES PERIOD'
                    WHEN дней_с_последней_продажи >= 60 THEN 'STALE'
                    WHEN остаток / NULLIF(продано_за_период / NULLIF(дней_наблюдения, 0), 0) <= 14 THEN 'RISK OOS'
                    WHEN остаток / NULLIF(продано_за_период / NULLIF(дней_наблюдения, 0), 0) > 90 THEN 'SLOW STOCK'
                    ELSE 'ACTIVE'
                END AS статус_остатка

            FROM base
            ORDER BY дней_остатка DESC NULLS LAST
        """

        try:
            return con.execute(
                query,
                {
                    "date": report_date,
                    "days": days,
                    "min_sales_days": min_sales_days,
                },
            ).df()
        finally:
            con.close()
            
            
    

    # def get_certificates_data(self, report_date: str) -> pd.DataFrame:
    #     """Получить товары с проблемами по сертификатам."""
    #     con = duckdb.connect(self.db_path)

    #     query = """
    #         WITH current_stocks AS (
    #             SELECT
    #                 t.nm_id,
    #                 t.chrt_id,
    #                 SUM(
    #                     COALESCE(t.quantity, 0)
    #                     + COALESCE(t.in_way_to_client, 0)
    #                     + COALESCE(t.in_way_from_client, 0)
    #                 ) AS qty
    #             FROM stocks.unpacked_stocks t
    #             WHERE t.date_from = $date
    #             GROUP BY t.nm_id, t.chrt_id
    #             HAVING SUM(
    #                 COALESCE(t.quantity, 0)
    #                 + COALESCE(t.in_way_to_client, 0)
    #                 + COALESCE(t.in_way_from_client, 0)
    #             ) > 0
    #         ),

    #         brands AS (
    #             SELECT
    #                 nm_id,
    #                 COALESCE(MAX(brand), 'Бренд не указан') AS brand
    #             FROM cards.unpacked_cards
    #             GROUP BY nm_id
    #         ),

    #         product_data AS (
    #             SELECT
    #                 cs.nm_id,
    #                 COALESCE(b.brand, 'Бренд не указан') AS бренд,
    #                 p.sa_name AS артикул,
    #                 p.subject_name AS категория,
    #                 p.gender AS пол,
    #                 p.title AS наименование,
    #                 s.tech_size AS размер,
    #                 cs.qty AS количество,
    #                 p.cert_end_date AS дата_окончания_сертификата
    #             FROM current_stocks cs
    #             LEFT JOIN cards.product p ON p.nm_id = cs.nm_id
    #             LEFT JOIN brands b ON b.nm_id = cs.nm_id
    #             LEFT JOIN cards.sizes s ON s.chrt_id = cs.chrt_id
    #         ),

    #         grouped AS (
    #             SELECT
    #                 nm_id,
    #                 COALESCE(MAX(бренд), 'Бренд не указан') AS бренд,
    #                 COALESCE(MAX(артикул), 'Артикул не указан') AS артикул,
    #                 COALESCE(MAX(категория), 'Категория не указана') AS категория,
    #                 COALESCE(MAX(пол), 'не указан') AS пол,
    #                 COALESCE(MAX(наименование), 'Наименование не указано') AS наименование,

    #                 string_agg(
    #                     COALESCE(CAST(размер AS VARCHAR), 'без размера')
    #                     || ' - '
    #                     || CAST(CAST(количество AS BIGINT) AS VARCHAR)
    #                     || ' шт',
    #                     ', '
    #                     ORDER BY размер
    #                 ) AS размер,

    #                 SUM(количество) AS количество,
    #                 MAX(дата_окончания_сертификата) AS дата_окончания_сертификата
    #             FROM product_data
    #             GROUP BY nm_id
    #         )

    #         SELECT
    #             nm_id,
    #             бренд,
    #             артикул,
    #             категория,
    #             пол,
    #             наименование,
    #             размер,
    #             количество,
    #             дата_окончания_сертификата,

    #             CASE
    #                 WHEN дата_окончания_сертификата IS NULL THEN 'Нет сертификата'
    #                 WHEN дата_окончания_сертификата < $date THEN 'Просрочен'
    #                 WHEN дата_окончания_сертификата BETWEEN $date AND ($date::DATE + INTERVAL 30 DAYS)
    #                     THEN 'Истекает в ближайшие 30 дней'
    #                 ELSE 'Действителен'
    #             END AS статус_сертификата,

    #             CASE
    #                 WHEN дата_окончания_сертификата IS NULL THEN NULL
    #                 WHEN дата_окончания_сертификата < $date THEN ($date::DATE - дата_окончания_сертификата)
    #                 ELSE (дата_окончания_сертификата - $date::DATE)
    #             END AS дней_до_окончания

    #         FROM grouped
    #         WHERE
    #             дата_окончания_сертификата IS NULL
    #             OR дата_окончания_сертификата < $date
    #             OR дата_окончания_сертификата BETWEEN $date AND ($date::DATE + INTERVAL 30 DAYS)

    #         ORDER BY
    #             CASE
    #                 WHEN дата_окончания_сертификата IS NULL THEN 1
    #                 WHEN дата_окончания_сертификата < $date THEN 2
    #                 ELSE 3
    #             END,
    #             дней_до_окончания,
    #             бренд,
    #             наименование
    #     """

    #     try:
    #         df = con.execute(query, {"date": report_date}).df()

    #         if "дата_окончания_сертификата" in df.columns:
    #             df["дата_окончания_сертификата"] = pd.to_datetime(
    #                 df["дата_окончания_сертификата"],
    #                 errors="coerce",
    #             ).dt.strftime("%d.%m.%Y")

    #         df = df.where(pd.notnull(df), None)

    #         return df

    #     finally:
    #         con.close()
    
    
    
    def get_certificates_data(self, report_date: str) -> pd.DataFrame:
        con = duckdb.connect(self.db_path)

        query = """
            WITH problem_products AS (
                SELECT
                    nm_id,
                    MAX(sa_name) AS артикул,
                    MAX(subject_name) AS категория,
                    MAX(gender) AS пол,
                    MAX(title) AS наименование,
                    MAX(cert_end_date) AS дата_окончания_сертификата
                FROM cards.product
                WHERE
                    cert_end_date IS NULL
                    OR cert_end_date < $date::DATE
                    OR cert_end_date BETWEEN $date::DATE AND ($date::DATE + INTERVAL 30 DAYS)
                GROUP BY nm_id
            ),

            current_stocks AS (
                SELECT
                    t.nm_id,
                    t.chrt_id,
                    SUM(
                        COALESCE(t.quantity, 0)
                        + COALESCE(t.in_way_to_client, 0)
                        + COALESCE(t.in_way_from_client, 0)
                    ) AS qty
                FROM stocks.unpacked_stocks t
                INNER JOIN problem_products pp ON pp.nm_id = t.nm_id
                WHERE t.date_from = $date
                GROUP BY t.nm_id, t.chrt_id
                HAVING qty > 0
            ),

            brands AS (
                SELECT
                    nm_id,
                    COALESCE(MAX(brand), 'Бренд не указан') AS бренд
                FROM cards.unpacked_cards
                GROUP BY nm_id
            ),

            sizes AS (
                SELECT
                    chrt_id,
                    MAX(tech_size) AS tech_size
                FROM cards.sizes
                GROUP BY chrt_id
            )

            SELECT
                cs.nm_id,
                COALESCE(MAX(b.бренд), 'Бренд не указан') AS бренд,
                COALESCE(MAX(pp.артикул), 'Артикул не указан') AS артикул,
                COALESCE(MAX(pp.категория), 'Категория не указана') AS категория,
                COALESCE(MAX(pp.пол), 'не указан') AS пол,
                COALESCE(MAX(pp.наименование), 'Наименование не указано') AS наименование,

                string_agg(
                    COALESCE(CAST(s.tech_size AS VARCHAR), 'без размера')
                    || ' - '
                    || CAST(CAST(cs.qty AS BIGINT) AS VARCHAR)
                    || ' шт',
                    ', '
                    ORDER BY s.tech_size
                ) AS размер,

                SUM(cs.qty) AS количество,
                MAX(pp.дата_окончания_сертификата) AS дата_окончания_сертификата,

                CASE
                    WHEN MAX(pp.дата_окончания_сертификата) IS NULL THEN 'Нет сертификата'
                    WHEN MAX(pp.дата_окончания_сертификата) < $date::DATE THEN 'Просрочен'
                    ELSE 'Истекает в ближайшие 30 дней'
                END AS статус_сертификата,

                CASE
                    WHEN MAX(pp.дата_окончания_сертификата) IS NULL THEN NULL
                    WHEN MAX(pp.дата_окончания_сертификата) < $date::DATE
                        THEN $date::DATE - MAX(pp.дата_окончания_сертификата)
                    ELSE MAX(pp.дата_окончания_сертификата) - $date::DATE
                END AS дней_до_окончания

            FROM current_stocks cs
            LEFT JOIN problem_products pp ON pp.nm_id = cs.nm_id
            LEFT JOIN brands b ON b.nm_id = cs.nm_id
            LEFT JOIN sizes s ON s.chrt_id = cs.chrt_id

            GROUP BY cs.nm_id

            ORDER BY
                CASE
                    WHEN MAX(pp.дата_окончания_сертификата) IS NULL THEN 1
                    WHEN MAX(pp.дата_окончания_сертификата) < $date::DATE THEN 2
                    ELSE 3
                END,
                дней_до_окончания,
                бренд,
                наименование
        """

        try:
            df = con.execute(query, {"date": report_date}).df()

            if "дата_окончания_сертификата" in df.columns:
                df["дата_окончания_сертификата"] = pd.to_datetime(
                    df["дата_окончания_сертификата"],
                    errors="coerce",
                ).dt.strftime("%d.%m.%Y")

            df = df.where(pd.notnull(df), None)
            return df

        finally:
            con.close()