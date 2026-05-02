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
        """Получить данные об остатках на дату с размерами"""
        con = duckdb.connect(self.db_path)
        query = """
            SELECT 
                nm_id as 'nm_id',
                sa_name as 'бренд',
                subject_name as 'категория',
                gender as 'пол',
                title as 'наименование',
                available_sizes as 'доступные_размеры',
                qty as 'количество'
            FROM reports_stocks.stocks_by_product 
            WHERE date_from = $date
              AND qty > 0
            ORDER BY qty DESC, sa_name, title
        """
        try:
            df = con.execute(query, {"date": report_date}).df()
            
            # Преобразуем список/массив в строку
            if 'доступные_размеры' in df.columns:
                df['доступные_размеры'] = df['доступные_размеры'].apply(
                    lambda x: ', '.join(str(v) for v in x) if hasattr(x, '__iter__') and not isinstance(x, str) else str(x) if x else ''
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
        
        # Статистика по товарам
        query_products = """
            SELECT 
                COUNT(DISTINCT nm_id) as total_products,
                COUNT(DISTINCT sa_name) as total_brands,
                SUM(qty) as total_quantity,
                COUNT(*) as total_positions,
                COUNT(DISTINCT subject_name) as total_categories
            FROM reports_stocks.stocks_by_product 
            WHERE date_from = $date
            AND qty > 0
        """
        
        # Статистика по складам
        query_warehouse = """
            SELECT 
                COUNT(DISTINCT warehouse_name) as total_warehouses,
                SUM(quantity + in_way_to_client + in_way_from_client) as total_warehouse_quantity
            FROM stocks.unpacked_stocks
            WHERE date_from = $date
        """
        
        try:
            products_result = con.execute(query_products, {"date": report_date}).fetchone()
            warehouse_result = con.execute(query_warehouse, {"date": report_date}).fetchone()
            
            return {
                'total_products': products_result[0] or 0,
                'total_brands': products_result[1] or 0,
                'total_quantity': products_result[2] or 0,
                'total_positions': products_result[3] or 0,
                'total_categories': products_result[4] or 0,
                'total_warehouses': warehouse_result[0] or 0,
                'total_warehouse_quantity': warehouse_result[1] or 0,
                'report_date': report_date
            }
        finally:
            con.close()
    
    def get_top_products(self, report_date: str, limit: int = 10) -> pd.DataFrame:
        """Получить топ N товаров по остаткам"""
        con = duckdb.connect(self.db_path)
        query = f"""
            SELECT 
                nm_id,
                sa_name as бренд,
                title as наименование,
                available_sizes as размеры,
                qty as количество
            FROM reports_stocks.stocks_by_product 
            WHERE date_from = $date
              AND qty > 0
            ORDER BY qty DESC
            LIMIT {limit}
        """
        try:
            df = con.execute(query, {"date": report_date}).df()
            
            # Преобразуем список/массив в строку
            if 'размеры' in df.columns:
                df['размеры'] = df['размеры'].apply(
                    lambda x: ', '.join(str(v) for v in x) if hasattr(x, '__iter__') and not isinstance(x, str) else str(x) if x else ''
                )
            
            return df
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