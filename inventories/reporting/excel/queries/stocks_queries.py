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
    
    
    # def get_stocks_data(self, report_date: str) -> pd.DataFrame:
    #     """Детальная информация по остаткам на дату с брендом и размерами"""
    #     con = duckdb.connect(self.db_path)

    #     query = """
    #             WITH x AS (
    #                 SELECT
    #                     t.date_from,
    #                     t.nm_id,
    #                     t.chrt_id,
    #                     SUM(COALESCE(t.quantity, 0)) AS quantity_on_hand,
    #                     SUM(COALESCE(t.in_way_to_client, 0) + COALESCE(t.in_way_from_client, 0)) AS quantity_in_transit,
    #                     SUM(
    #                         COALESCE(t.quantity, 0)
    #                         + COALESCE(t.in_way_to_client, 0)
    #                         + COALESCE(t.in_way_from_client, 0)
    #                     ) AS qty
    #                 FROM stocks.unpacked_stocks t
    #                 WHERE t.date_from = $date
    #                 GROUP BY
    #                     t.date_from,
    #                     t.nm_id,
    #                     t.chrt_id
    #             ),

    #             brands AS (
    #                 SELECT
    #                     nm_id,
    #                     COALESCE(MAX(brand), 'Бренд не указан') AS brand
    #                 FROM cards.unpacked_cards
    #                 GROUP BY nm_id
    #             )

    #             SELECT
    #                 x.nm_id AS nm_id,
    #                 COALESCE(b.brand, 'Бренд не указан') AS бренд,
    #                 p.sa_name AS артикул,
    #                 p.subject_name AS категория,
    #                 p.gender AS пол,
    #                 p.title AS наименование,
    #                 LIST(CONCAT(x.qty::text, ' шт -> ', s.tech_size)) AS доступные_размеры,
    #                 SUM(x.quantity_on_hand) AS на_складе,
    #                 SUM(x.quantity_in_transit) AS в_пути,
    #                 SUM(x.qty) AS количество
    #             FROM x
    #             LEFT JOIN cards.product p ON p.nm_id = x.nm_id
    #             LEFT JOIN brands b ON b.nm_id = x.nm_id
    #             LEFT JOIN cards.sizes s ON s.chrt_id = x.chrt_id
    #             WHERE x.qty > 0
    #             GROUP BY
    #                 x.nm_id,
    #                 b.brand,
    #                 p.sa_name,
    #                 p.subject_name,
    #                 p.gender,
    #                 p.title
    #             ORDER BY
    #                 SUM(x.qty) DESC,
    #                 COALESCE(b.brand, 'Бренд не указан'),
    #                 p.title
    #         """

    #     try:
    #         df = con.execute(query, {"date": report_date}).df()

    #         if 'доступные_размеры' in df.columns:
    #             df['доступные_размеры'] = df['доступные_размеры'].apply(
    #                 lambda x: ', '.join(str(v) for v in x)
    #                 if hasattr(x, '__iter__') and not isinstance(x, str)
    #                 else str(x) if x else ''
    #             )

    #         return df
    #     finally:
    #         con.close()
    
    
    def get_stocks_data(
        self,
        report_date: str,
    ) -> pd.DataFrame:
        """
        Детальные остатки товара.

        Итого:
            WB + FBS + в пути

        FULL OUTER JOIN нужен, чтобы не потерять
        товары, которые есть только на FBS.
        """

        con = duckdb.connect(
            self.db_path
        )

        query = """
            WITH

            wb AS (
                SELECT
                    t.nm_id,
                    t.chrt_id,

                    SUM(
                        COALESCE(
                            t.quantity,
                            0
                        )
                    ) AS wb_quantity,

                    SUM(
                        COALESCE(
                            t.in_way_to_client,
                            0
                        )
                        +
                        COALESCE(
                            t.in_way_from_client,
                            0
                        )
                    ) AS in_transit

                FROM stocks.unpacked_stocks t

                WHERE
                    t.date_from::DATE
                        = $date::DATE

                GROUP BY
                    t.nm_id,
                    t.chrt_id
            ),


            fbs AS (
                SELECT
                    t.nm_id,
                    t.chrt_id,

                    SUM(
                        COALESCE(
                            t.quantity,
                            0
                        )
                    ) AS fbs_quantity

                FROM stocks.unpacked_fbs_stocks t

                WHERE
                    t.date_from::DATE
                        = $date::DATE

                GROUP BY
                    t.nm_id,
                    t.chrt_id
            ),


            stocks AS (
                SELECT
                    COALESCE(
                        wb.nm_id,
                        fbs.nm_id
                    ) AS nm_id,

                    COALESCE(
                        wb.chrt_id,
                        fbs.chrt_id
                    ) AS chrt_id,

                    COALESCE(
                        wb.wb_quantity,
                        0
                    ) AS wb_quantity,

                    COALESCE(
                        fbs.fbs_quantity,
                        0
                    ) AS fbs_quantity,

                    COALESCE(
                        wb.in_transit,
                        0
                    ) AS in_transit,

                    (
                        COALESCE(
                            wb.wb_quantity,
                            0
                        )
                        +
                        COALESCE(
                            fbs.fbs_quantity,
                            0
                        )
                        +
                        COALESCE(
                            wb.in_transit,
                            0
                        )
                    ) AS qty

                FROM wb

                FULL OUTER JOIN fbs
                    ON wb.chrt_id = fbs.chrt_id
            ),


            brands AS (
                SELECT
                    nm_id,

                    COALESCE(
                        MAX(brand),
                        'Бренд не указан'
                    ) AS brand

                FROM cards.unpacked_cards

                GROUP BY
                    nm_id
            )


            SELECT
                x.nm_id,

                COALESCE(
                    b.brand,
                    'Бренд не указан'
                ) AS бренд,

                p.sa_name AS артикул,
                p.subject_name AS категория,
                p.gender AS пол,
                p.title AS наименование,

                LIST(
                    CONCAT(
                        x.qty::TEXT,
                        ' шт -> ',
                        COALESCE(
                            s.tech_size,
                            ''
                        )
                    )
                ) AS доступные_размеры,

                SUM(
                    x.wb_quantity
                ) AS на_складе,

                SUM(
                    x.fbs_quantity
                ) AS fbs,

                SUM(
                    x.in_transit
                ) AS в_пути,

                SUM(
                    x.qty
                ) AS количество

            FROM stocks x

            LEFT JOIN cards.product p
                ON p.nm_id = x.nm_id

            LEFT JOIN brands b
                ON b.nm_id = x.nm_id

            LEFT JOIN cards.sizes s
                ON s.chrt_id = x.chrt_id

            WHERE
                x.qty > 0

            GROUP BY
                x.nm_id,
                b.brand,
                p.sa_name,
                p.subject_name,
                p.gender,
                p.title

            ORDER BY
                SUM(x.qty) DESC,
                COALESCE(
                    b.brand,
                    'Бренд не указан'
                ),
                p.title
        """

        try:
            df = con.execute(
                query,
                {
                    "date": report_date,
                },
            ).df()

            if "доступные_размеры" in df.columns:
                df["доступные_размеры"] = (
                    df["доступные_размеры"]
                    .apply(
                        lambda x: ", ".join(
                            str(v)
                            for v in x
                        )
                        if hasattr(
                            x,
                            "__iter__",
                        )
                        and not isinstance(
                            x,
                            str,
                        )
                        else str(x)
                        if x
                        else ""
                    )
                )

            return df

        finally:
            con.close()

    
    
    def get_stocks_by_category(
        self,
        report_date: str,
    ) -> pd.DataFrame:

        df = self.get_stocks_data(
            report_date
        )

        if df.empty:
            return pd.DataFrame(
                columns=[
                    "категория",
                    "разбивка_по_полу",
                    "на_складе",
                    "fbs",
                    "в_пути",
                    "всего",
                ]
            )

        df["категория"] = (
            df["категория"]
            .fillna("Категория не указана")
        )

        df["пол"] = (
            df["пол"]
            .fillna("Пол не указан")
        )

        gender = (
            df.groupby(
                [
                    "категория",
                    "пол",
                ]
            )["количество"]
            .sum()
            .reset_index()
        )

        gender_text = (
            gender.groupby(
                "категория"
            )
            .apply(
                lambda x: "\n".join(
                    f"{row['пол']} -> "
                    f"{int(row['количество']):,} шт"
                    .replace(",", " ")
                    for _, row in x.iterrows()
                ),
                include_groups=False,
            )
            .rename(
                "разбивка_по_полу"
            )
            .reset_index()
        )

        totals = (
            df.groupby(
                "категория"
            )
            .agg(
                на_складе=(
                    "на_складе",
                    "sum",
                ),
                fbs=(
                    "fbs",
                    "sum",
                ),
                в_пути=(
                    "в_пути",
                    "sum",
                ),
                всего=(
                    "количество",
                    "sum",
                ),
            )
            .reset_index()
        )

        result = totals.merge(
            gender_text,
            on="категория",
            how="left",
        )

        return result[
            [
                "категория",
                "разбивка_по_полу",
                "на_складе",
                "fbs",
                "в_пути",
                "всего",
            ]
        ].sort_values(
            "всего",
            ascending=False,
        )
        
        
        
    def get_fbs_stocks_data(
        self,
        report_date: str,
    ) -> pd.DataFrame:
        """
        Только физические остатки FBS.
        Одна строка = nm_id + chrt_id.
        """

        con = duckdb.connect(
            self.db_path
        )

        query = """
            WITH

            fbs AS (
                SELECT
                    t.nm_id,
                    t.chrt_id,

                    SUM(
                        COALESCE(
                            t.quantity,
                            0
                        )
                    ) AS quantity

                FROM stocks.unpacked_fbs_stocks t

                WHERE
                    t.date_from::DATE
                        = $date::DATE

                GROUP BY
                    t.nm_id,
                    t.chrt_id
            ),


            brands AS (
                SELECT
                    nm_id,

                    COALESCE(
                        MAX(brand),
                        'Бренд не указан'
                    ) AS brand

                FROM cards.unpacked_cards

                GROUP BY
                    nm_id
            )


            SELECT
                f.nm_id,

                COALESCE(
                    b.brand,
                    'Бренд не указан'
                ) AS бренд,

                p.sa_name AS артикул,

                p.subject_name
                    AS категория,

                COALESCE(
                    p.gender,
                    'Пол не указан'
                ) AS пол,

                p.title
                    AS наименование,

                COALESCE(
                    s.tech_size,
                    ''
                ) AS размер,

                f.quantity
                    AS количество

            FROM fbs f

            LEFT JOIN cards.product p
                ON p.nm_id = f.nm_id

            LEFT JOIN brands b
                ON b.nm_id = f.nm_id

            LEFT JOIN cards.sizes s
                ON s.chrt_id = f.chrt_id

            WHERE
                f.quantity > 0

            ORDER BY
                f.quantity DESC,
                b.brand,
                p.title,
                s.tech_size
        """

        try:
            return con.execute(
                query,
                {
                    "date": report_date,
                },
            ).df()

        finally:
            con.close()
    
    # def get_summary_stats(self, report_date: str) -> Dict:
    #     """Получить сводную статистику"""
    #     con = duckdb.connect(self.db_path)
    
    #     query_warehouse = """
    #         SELECT 
    #             COUNT(DISTINCT warehouse_name) as total_warehouses,
    #             SUM(quantity) as total_on_hand,
    #             SUM(in_way_to_client + in_way_from_client) as total_in_transit,
    #             SUM(quantity + in_way_to_client + in_way_from_client) as total_all
    #         FROM stocks.unpacked_stocks
    #         WHERE date_from = $date
    #     """
        
    #     # Статистика по товарам (для других отчетов, не для карты)
    #     query_products = """
    #         SELECT 
    #             COUNT(DISTINCT nm_id) as total_products,
    #             COUNT(DISTINCT sa_name) as total_brands,
    #             COUNT(*) as total_positions,
    #             COUNT(DISTINCT subject_name) as total_categories
    #         FROM reports_stocks.stocks_by_product 
    #         WHERE date_from = $date
    #         AND qty > 0
    #     """
        
    #     try:
    #         warehouse_result = con.execute(query_warehouse, {"date": report_date}).fetchone()
    #         products_result = con.execute(query_products, {"date": report_date}).fetchone()
            
    #         return {
    #             # Данные для карты (из warehouse)
    #             'total_warehouses': warehouse_result[0] or 0,
    #             'total_on_hand': warehouse_result[1] or 0,      # на складах
    #             'total_in_transit': warehouse_result[2] or 0,   # в пути
    #             'total_quantity': warehouse_result[3] or 0,     # всего
                
    #             # Данные для других отчетов (из products)
    #             'total_products': products_result[0] or 0,
    #             'total_brands': products_result[1] or 0,
    #             'total_positions': products_result[2] or 0,
    #             'total_categories': products_result[3] or 0,
                
    #             'report_date': report_date
    #         }
    #     finally:
    #         con.close()
    
    
    def get_summary_stats(
        self,
        report_date: str,
    ) -> Dict:
        """
        Сводная статистика по остаткам.

        Состав:
        - остатки WB;
        - остатки FBS;
        - товары в пути;
        - общее количество = WB + FBS + в пути.
        """

        con = duckdb.connect(
            self.db_path
        )

        # ============================================================
        # WB + ТОВАРЫ В ПУТИ
        # ============================================================

        query_warehouse = """
            SELECT
                COUNT(
                    DISTINCT warehouse_name
                ) AS total_warehouses,

                SUM(
                    COALESCE(
                        quantity,
                        0
                    )
                ) AS total_on_hand,

                SUM(
                    COALESCE(
                        in_way_to_client,
                        0
                    )
                    +
                    COALESCE(
                        in_way_from_client,
                        0
                    )
                ) AS total_in_transit

            FROM stocks.unpacked_stocks

            WHERE
                date_from::DATE
                    = $date::DATE
        """


        # ============================================================
        # FBS — НАШ СКЛАД
        # ============================================================

        query_fbs = """
            SELECT
                SUM(
                    COALESCE(
                        quantity,
                        0
                    )
                ) AS total_fbs

            FROM stocks.unpacked_fbs_stocks

            WHERE
                date_from::DATE
                    = $date::DATE
        """


        # ============================================================
        # ТОВАРЫ / БРЕНДЫ / КАТЕГОРИИ
        #
        # Здесь тоже объединяем WB + FBS,
        # чтобы позиции только на FBS не потерялись.
        # ============================================================

        query_products = """
            WITH

            wb AS (
                SELECT
                    nm_id,
                    chrt_id,

                    SUM(
                        COALESCE(
                            quantity,
                            0
                        )
                        +
                        COALESCE(
                            in_way_to_client,
                            0
                        )
                        +
                        COALESCE(
                            in_way_from_client,
                            0
                        )
                    ) AS qty

                FROM stocks.unpacked_stocks

                WHERE
                    date_from::DATE
                        = $date::DATE

                GROUP BY
                    nm_id,
                    chrt_id
            ),


            fbs AS (
                SELECT
                    nm_id,
                    chrt_id,

                    SUM(
                        COALESCE(
                            quantity,
                            0
                        )
                    ) AS qty

                FROM stocks.unpacked_fbs_stocks

                WHERE
                    date_from::DATE
                        = $date::DATE

                GROUP BY
                    nm_id,
                    chrt_id
            ),


            stocks AS (
                SELECT
                    COALESCE(
                        wb.nm_id,
                        fbs.nm_id
                    ) AS nm_id,

                    COALESCE(
                        wb.chrt_id,
                        fbs.chrt_id
                    ) AS chrt_id,

                    COALESCE(
                        wb.qty,
                        0
                    )
                    +
                    COALESCE(
                        fbs.qty,
                        0
                    ) AS qty

                FROM wb

                FULL OUTER JOIN fbs
                    ON wb.chrt_id = fbs.chrt_id
            ),


            brands AS (
                SELECT
                    nm_id,

                    COALESCE(
                        MAX(brand),
                        'Бренд не указан'
                    ) AS brand

                FROM cards.unpacked_cards

                GROUP BY
                    nm_id
            )


            SELECT
                COUNT(
                    DISTINCT s.nm_id
                ) AS total_products,

                COUNT(
                    DISTINCT b.brand
                ) AS total_brands,

                COUNT(*)
                    AS total_positions,

                COUNT(
                    DISTINCT p.subject_name
                ) AS total_categories

            FROM stocks s

            LEFT JOIN cards.product p
                ON p.nm_id = s.nm_id

            LEFT JOIN brands b
                ON b.nm_id = s.nm_id

            WHERE
                s.qty > 0
        """

        try:
            warehouse_result = con.execute(
                query_warehouse,
                {
                    "date": report_date,
                },
            ).fetchone()

            fbs_result = con.execute(
                query_fbs,
                {
                    "date": report_date,
                },
            ).fetchone()

            products_result = con.execute(
                query_products,
                {
                    "date": report_date,
                },
            ).fetchone()


            # ========================================================
            # WB
            # ========================================================

            total_warehouses = (
                warehouse_result[0]
                or 0
            )

            total_on_hand = (
                warehouse_result[1]
                or 0
            )

            total_in_transit = (
                warehouse_result[2]
                or 0
            )


            # ========================================================
            # FBS
            # ========================================================

            total_fbs = (
                fbs_result[0]
                or 0
            )


            # ========================================================
            # ИТОГО
            #
            # WB + FBS + в пути
            # ========================================================

            total_quantity = (
                total_on_hand
                +
                total_fbs
                +
                total_in_transit
            )


            return {
                # ----------------------------------------------------
                # Карта / KPI
                # ----------------------------------------------------

                "total_warehouses": (
                    total_warehouses
                ),

                "total_on_hand": (
                    total_on_hand
                ),

                "total_fbs": (
                    total_fbs
                ),

                "total_in_transit": (
                    total_in_transit
                ),

                "total_quantity": (
                    total_quantity
                ),

                # ----------------------------------------------------
                # Товары / бренды / категории
                # ----------------------------------------------------

                "total_products": (
                    products_result[0]
                    or 0
                ),

                "total_brands": (
                    products_result[1]
                    or 0
                ),

                "total_positions": (
                    products_result[2]
                    or 0
                ),

                "total_categories": (
                    products_result[3]
                    or 0
                ),

                "report_date": (
                    report_date
                ),
            }

        finally:
            con.close()
        
        
    def get_stocks_by_gender(
        self,
        report_date: str,
    ) -> pd.DataFrame:
        """
        Остатки по полу.

        Итого:
            WB + FBS + в пути
        """

        df = self.get_stocks_data(
            report_date
        )

        if df.empty:
            return pd.DataFrame(
                columns=[
                    "пол",
                    "количество",
                    "товаров",
                ]
            )

        df["пол"] = (
            df["пол"]
            .fillna("не указан")
        )

        result = (
            df.groupby(
                "пол",
                dropna=False,
            )
            .agg(
                количество=(
                    "количество",
                    "sum",
                ),
                товаров=(
                    "nm_id",
                    "nunique",
                ),
            )
            .reset_index()
            .sort_values(
                "количество",
                ascending=False,
            )
            .reset_index(
                drop=True
            )
        )

        return result
            

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
            
                  
    def get_stocks_by_brand(
        self,
        report_date: str,
    ) -> pd.DataFrame:

        df = self.get_stocks_data(
            report_date
        )

        if df.empty:
            return pd.DataFrame(
                columns=[
                    "бренд",
                    "товаров",
                    "на_складе",
                    "fbs",
                    "в_пути",
                    "итого",
                    "доля_остатков_проц",
                ]
            )

        df["бренд"] = (
            df["бренд"]
            .fillna("Бренд не указан")
        )

        result = (
            df.groupby(
                "бренд",
                dropna=False,
            )
            .agg(
                товаров=(
                    "nm_id",
                    "nunique",
                ),
                на_складе=(
                    "на_складе",
                    "sum",
                ),
                fbs=(
                    "fbs",
                    "sum",
                ),
                в_пути=(
                    "в_пути",
                    "sum",
                ),
                итого=(
                    "количество",
                    "sum",
                ),
            )
            .reset_index()
        )

        total = result[
            "итого"
        ].sum()

        result[
            "доля_остатков_проц"
        ] = (
            result["итого"]
            / total
            * 100
            if total
            else 0
        )

        return result.sort_values(
            "итого",
            ascending=False,
        ).reset_index(
            drop=True
        )
    
    
    def get_inventory_turnover(
        self,
        report_date: str,
        days: int = 90,
        min_sales_days: int = 60,
    ) -> pd.DataFrame:
        """
        Расчет оборачиваемости остатков за последние N дней
        + диагностика продаж.

        Логика:
        - Остаток = WB + FBS + товары в пути.
        - Продано за период = продажи за последние `days` дней
        до даты отчета включительно.
        - Дней без продаж = разница между датой отчета
        и последней продажей.
        - Новый товар = первая продажа была менее
        `min_sales_days` дней назад.
        - Для новых товаров запас в днях/месяцах
        не рассчитывается.
        """

        con = duckdb.connect(
            self.db_path
        )

        query = """
            WITH

            -- ============================================================
            -- ОСТАТКИ WB
            -- ============================================================

            wb_stocks AS (
                SELECT
                    t.nm_id,

                    SUM(
                        COALESCE(
                            t.quantity,
                            0
                        )
                    ) AS wb_quantity,

                    SUM(
                        COALESCE(
                            t.in_way_to_client,
                            0
                        )
                        +
                        COALESCE(
                            t.in_way_from_client,
                            0
                        )
                    ) AS in_transit

                FROM stocks.unpacked_stocks t

                WHERE
                    t.date_from::DATE
                        = $date::DATE

                GROUP BY
                    t.nm_id
            ),


            -- ============================================================
            -- ОСТАТКИ FBS
            -- ============================================================

            fbs_stocks AS (
                SELECT
                    t.nm_id,

                    SUM(
                        COALESCE(
                            t.quantity,
                            0
                        )
                    ) AS fbs_quantity

                FROM stocks.unpacked_fbs_stocks t

                WHERE
                    t.date_from::DATE
                        = $date::DATE

                GROUP BY
                    t.nm_id
            ),


            -- ============================================================
            -- ОБЪЕДИНЯЕМ WB + FBS
            --
            -- FULL OUTER JOIN нужен, чтобы не потерять товары,
            -- которые есть только на FBS.
            -- ============================================================

            stocks AS (
                SELECT
                    COALESCE(
                        wb.nm_id,
                        fbs.nm_id
                    ) AS nm_id,

                    COALESCE(
                        wb.wb_quantity,
                        0
                    ) AS wb_quantity,

                    COALESCE(
                        fbs.fbs_quantity,
                        0
                    ) AS fbs_quantity,

                    COALESCE(
                        wb.in_transit,
                        0
                    ) AS in_transit,

                    (
                        COALESCE(
                            wb.wb_quantity,
                            0
                        )
                        +
                        COALESCE(
                            fbs.fbs_quantity,
                            0
                        )
                        +
                        COALESCE(
                            wb.in_transit,
                            0
                        )
                    ) AS stock_qty

                FROM wb_stocks wb

                FULL OUTER JOIN fbs_stocks fbs
                    ON wb.nm_id = fbs.nm_id
            ),


            -- ============================================================
            -- ПРОДАЖИ ЗА АНАЛИЗИРУЕМЫЙ ПЕРИОД
            -- ============================================================

            sales_period AS (
                SELECT
                    nm_id,

                    SUM(
                        CASE
                            WHEN oper = 'dt'
                                THEN 1

                            WHEN oper = 'cr'
                                THEN -1

                            ELSE 0
                        END
                    ) AS sold_qty_period

                FROM sales.sales_long

                WHERE
                    field = 'retail_price'

                    AND date_from
                        BETWEEN
                            (
                                $date::DATE
                                - (
                                    $days::INTEGER
                                    - 1
                                )
                            )
                            AND $date::DATE

                GROUP BY
                    nm_id
            ),


            -- ============================================================
            -- ИСТОРИЯ ПРОДАЖ
            -- ============================================================

            sales_history AS (
                SELECT
                    nm_id,

                    MIN(
                        date_from
                    ) AS first_sale_date,

                    MAX(
                        date_from
                    ) AS last_sale_date,

                    SUM(
                        CASE
                            WHEN oper = 'dt'
                                THEN 1

                            WHEN oper = 'cr'
                                THEN -1

                            ELSE 0
                        END
                    ) AS sold_qty_lifetime

                FROM sales.sales_long

                WHERE
                    field = 'retail_price'

                GROUP BY
                    nm_id
            ),


            -- ============================================================
            -- БРЕНДЫ
            -- ============================================================

            brands AS (
                SELECT
                    nm_id,

                    COALESCE(
                        MAX(
                            brand
                        ),
                        'Бренд не указан'
                    ) AS brand

                FROM cards.unpacked_cards

                GROUP BY
                    nm_id
            ),


            -- ============================================================
            -- ОСНОВНЫЕ ДАННЫЕ
            -- ============================================================

            base AS (
                SELECT
                    s.nm_id,

                    COALESCE(
                        b.brand,
                        'Бренд не указан'
                    ) AS бренд,

                    p.sa_name
                        AS артикул,

                    p.subject_name
                        AS категория,

                    p.gender
                        AS пол,

                    p.title
                        AS наименование,

                    ARRAY_TO_STRING(
                        p.available_sizes,
                        ', '
                    ) AS доступные_размеры,


                    -- ----------------------------------------------------
                    -- РАЗЛОЖЕНИЕ ОСТАТКА
                    -- ----------------------------------------------------

                    s.wb_quantity
                        AS остаток_wb,

                    s.fbs_quantity
                        AS остаток_fbs,

                    s.in_transit
                        AS в_пути,

                    s.stock_qty
                        AS остаток,


                    -- ----------------------------------------------------
                    -- ПРОДАЖИ
                    -- ----------------------------------------------------

                    COALESCE(
                        sp.sold_qty_period,
                        0
                    ) AS продано_за_период,

                    COALESCE(
                        sh.sold_qty_lifetime,
                        0
                    ) AS продано_за_все_время,


                    -- ----------------------------------------------------
                    -- ПЕРИОД
                    -- ----------------------------------------------------

                    (
                        $date::DATE
                        - (
                            $days::INTEGER
                            - 1
                        )
                    ) AS начало_периода_продаж,

                    $date::DATE
                        AS конец_периода_продаж,


                    sh.first_sale_date
                        AS первая_продажа,

                    sh.last_sale_date
                        AS последняя_продажа,


                    -- ----------------------------------------------------
                    -- ДНЕЙ С ПОСЛЕДНЕЙ ПРОДАЖИ
                    -- ----------------------------------------------------

                    CASE
                        WHEN sh.last_sale_date IS NULL
                            THEN NULL

                        ELSE (
                            $date::DATE
                            - sh.last_sale_date
                        )
                    END
                        AS дней_с_последней_продажи,


                    -- ----------------------------------------------------
                    -- ВОЗРАСТ ПРОДАЖ
                    -- ----------------------------------------------------

                    CASE
                        WHEN sh.first_sale_date IS NULL
                            THEN NULL

                        ELSE (
                            $date::DATE
                            - sh.first_sale_date
                        )
                    END
                        AS возраст_продаж_дней,


                    -- ----------------------------------------------------
                    -- ДНЕЙ НАБЛЮДЕНИЯ
                    -- ----------------------------------------------------

                    CASE
                        WHEN sh.first_sale_date IS NULL
                            THEN NULL

                        ELSE LEAST(
                            $days::INTEGER,
                            (
                                $date::DATE
                                - sh.first_sale_date
                            )
                            + 1
                        )
                    END
                        AS дней_наблюдения,


                    -- ----------------------------------------------------
                    -- НОВЫЙ ТОВАР
                    -- ----------------------------------------------------

                    CASE
                        WHEN
                            sh.first_sale_date
                                IS NOT NULL

                            AND (
                                (
                                    $date::DATE
                                    - sh.first_sale_date
                                )
                                <
                                $min_sales_days::INTEGER
                            )

                        THEN TRUE

                        ELSE FALSE
                    END
                        AS новый_товар


                FROM stocks s

                LEFT JOIN sales_period sp
                    ON sp.nm_id = s.nm_id

                LEFT JOIN sales_history sh
                    ON sh.nm_id = s.nm_id

                LEFT JOIN cards.product p
                    ON p.nm_id = s.nm_id

                LEFT JOIN brands b
                    ON b.nm_id = s.nm_id

                WHERE
                    s.stock_qty > 0
            )


            -- ============================================================
            -- ФИНАЛЬНЫЙ РЕЗУЛЬТАТ
            -- ============================================================

            SELECT
                *,


                -- --------------------------------------------------------
                -- СРЕДНИЕ ПРОДАЖИ В ДЕНЬ
                -- --------------------------------------------------------

                CASE
                    WHEN новый_товар
                        THEN NULL

                    WHEN COALESCE(
                        продано_за_период,
                        0
                    ) <= 0
                        THEN NULL

                    ELSE ROUND(
                        продано_за_период
                        /
                        NULLIF(
                            дней_наблюдения,
                            0
                        ),
                        2
                    )
                END
                    AS средние_продажи_в_день,


                -- --------------------------------------------------------
                -- СРЕДНИЕ ПРОДАЖИ В МЕСЯЦ
                -- --------------------------------------------------------

                CASE
                    WHEN новый_товар
                        THEN NULL

                    WHEN COALESCE(
                        продано_за_период,
                        0
                    ) <= 0
                        THEN NULL

                    ELSE ROUND(
                        продано_за_период
                        /
                        NULLIF(
                            дней_наблюдения,
                            0
                        )
                        * 30,
                        2
                    )
                END
                    AS средние_продажи_в_месяц,


                -- --------------------------------------------------------
                -- ДНЕЙ ОСТАТКА
                -- --------------------------------------------------------

                CASE
                    WHEN новый_товар
                        THEN NULL

                    WHEN COALESCE(
                        продано_за_период,
                        0
                    ) <= 0
                        THEN NULL

                    ELSE ROUND(
                        остаток
                        /
                        NULLIF(
                            продано_за_период
                            /
                            NULLIF(
                                дней_наблюдения,
                                0
                            ),
                            0
                        ),
                        0
                    )::INTEGER
                END
                    AS дней_остатка,


                -- --------------------------------------------------------
                -- МЕСЯЦЕВ ОСТАТКА
                -- --------------------------------------------------------

                CASE
                    WHEN новый_товар
                        THEN NULL

                    WHEN COALESCE(
                        продано_за_период,
                        0
                    ) <= 0
                        THEN NULL

                    ELSE ROUND(
                        остаток
                        /
                        NULLIF(
                            продано_за_период
                            /
                            NULLIF(
                                дней_наблюдения,
                                0
                            )
                            * 30,
                            0
                        ),
                        2
                    )
                END
                    AS месяцев_остатка,


                -- --------------------------------------------------------
                -- СТАТУС
                -- --------------------------------------------------------

                CASE
                    WHEN первая_продажа IS NULL
                        THEN 'NO SALES EVER'

                    WHEN новый_товар
                        THEN 'NEW ITEM'

                    WHEN COALESCE(
                        продано_за_период,
                        0
                    ) <= 0
                        THEN 'NO SALES PERIOD'

                    WHEN дней_с_последней_продажи >= 60
                        THEN 'STALE'

                    WHEN
                        остаток
                        /
                        NULLIF(
                            продано_за_период
                            /
                            NULLIF(
                                дней_наблюдения,
                                0
                            ),
                            0
                        )
                        <= 14
                        THEN 'RISK OOS'

                    WHEN
                        остаток
                        /
                        NULLIF(
                            продано_за_период
                            /
                            NULLIF(
                                дней_наблюдения,
                                0
                            ),
                            0
                        )
                        > 90
                        THEN 'SLOW STOCK'

                    ELSE 'ACTIVE'
                END
                    AS статус_остатка


            FROM base

            ORDER BY
                дней_остатка DESC
                NULLS LAST
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
            
    
    
    def get_certificates_data(self, report_date: str) -> pd.DataFrame:
        con = duckdb.connect(self.db_path)

        query = """
            select 
                t.nm_id,
                c.brand as 'бренд',
                t.sa_name as 'артикул',
                t.subject_name as 'категория',
                t.gender as 'пол',
                t.title as 'наименование',
                t.available_sizes as 'размер',
                t.qty as 'количество',
                c.cert_end_date as 'дата_окончания_сертификата',
                case 
                when c.cert_end_date is null then 'Нет сертификата'
                when c.cert_end_date < t.date_from then 'Просрочен'
                when c.cert_end_date < t.date_from + INTERVAL 30 DAYS then 'Истекает в ближайшие 30 дней'
                else 'Действует'
                end as 'статус_сертификата',
                case when c.cert_end_date < t.date_from then 0 
                else c.cert_end_date - t.date_from 
                end as 'дней_до_окончания'
                from reports_stocks.stocks_by_product t
                left join cards.product c on c.nm_id = t.nm_id
                where t.date_from = ?
                and статус_сертификата != 'Действует'
        """

        try:

            df = con.execute(query, parameters=[report_date]).df()

            if "дата_окончания_сертификата" in df.columns:

                df["дата_окончания_сертификата"] = (

                    pd.to_datetime(

                        df["дата_окончания_сертификата"],

                        errors="coerce",

                    )

                    .dt.strftime("%d.%m.%Y")

                )

            # корректная замена NaN → None

            df = df.astype(object).where(pd.notnull(df), None)

            return df

        finally:

            con.close()