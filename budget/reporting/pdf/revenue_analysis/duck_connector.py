# budget/reporting/pdf/revenue_analysis/duck_connector.py
import os
import duckdb
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()
db_path = os.getenv("DUCKDB_PATH")


class RevenueDuckConnector:
    """Подключение к DuckDB для данных по выручке"""
    
    def __init__(self):
        self.db_path = db_path
    
    def _get_connection(self):
        return duckdb.connect(self.db_path)
    
    def get_last_fact_date(self, date_from):
        """Последняя дата факта выручки"""
        con = self._get_connection()
        try:
            sql = """
                SELECT MAX(date_from)::date
                FROM sales.sales_long
                WHERE date_from >= ? AND field = 'retail_price'
            """
            result = con.execute(sql, [date_from]).fetchone()
            return result[0] if result and result[0] else None
        finally:
            con.close()
    
    def get_monthly_fact(self, date_from, report_date):
        """Факт по месяцам из sales_long"""
        con = self._get_connection()
        try:
            sql = """
                SELECT
                    EXTRACT(YEAR FROM date_from) AS year,
                    EXTRACT(MONTH FROM date_from) AS month,
                    SUM(CASE WHEN field = 'retail_price' AND oper = 'dt' THEN val ELSE 0 END) / 100.0 AS sales_amount,
                    SUM(CASE WHEN field = 'retail_price' AND oper = 'cr' THEN val ELSE 0 END) / 100.0 AS returns_amount,
                    COUNT(CASE WHEN field = 'retail_price' AND oper = 'dt' THEN 1 END) AS sales_transactions,
                    COUNT(CASE WHEN field = 'retail_price' AND oper = 'cr' THEN 1 END) AS returns_transactions
                FROM sales.sales_long
                WHERE date_from BETWEEN ? AND ?
                  AND EXTRACT(YEAR FROM date_from) = ?
                  AND date_from <= ?
                  AND field = 'retail_price'
                GROUP BY year, month
                ORDER BY year, month
            """
            result = con.execute(sql, [date_from, report_date, report_date.year, report_date]).fetchall()
            
            monthly_data = {}
            for row in result:
                year = int(row[0])
                month = int(row[1])
                key = f"{year}-{month:02d}"
                sales_amount = float(row[2] or 0)
                returns_amount = float(row[3] or 0)
                monthly_data[key] = {
                    "sales_amount": sales_amount,
                    "returns_amount": returns_amount,
                    "net_amount": sales_amount - returns_amount,
                    "sales_transactions": int(row[4] or 0),
                    "returns_transactions": int(row[5] or 0),
                }
            return monthly_data
        finally:
            con.close()
    
    def get_fact_for_period(self, date_start, date_end):
        """Факт выручки за произвольный период"""
        con = self._get_connection()
        try:
            sql = """
                SELECT 
                    COALESCE(SUM(CASE WHEN field = 'retail_price' AND oper = 'dt' THEN val ELSE 0 END), 0) / 100.0 AS sales_amount,
                    COALESCE(SUM(CASE WHEN field = 'retail_price' AND oper = 'cr' THEN val ELSE 0 END), 0) / 100.0 AS returns_amount,
                    COUNT(CASE WHEN field = 'retail_price' AND oper = 'dt' THEN 1 END) AS sales_transactions,
                    COUNT(CASE WHEN field = 'retail_price' AND oper = 'cr' THEN 1 END) AS returns_transactions
                FROM sales.sales_long
                WHERE date_from BETWEEN ? AND ?
                  AND field = 'retail_price'
            """
            result = con.execute(sql, [date_start, date_end]).fetchone()
            sales_amount = float(result[0] or 0)
            returns_amount = float(result[1] or 0)
            return {
                "sales_amount": sales_amount,
                "returns_amount": returns_amount,
                "net_amount": sales_amount - returns_amount,
                "sales_transactions": int(result[2] or 0),
                "returns_transactions": int(result[3] or 0),
            }
        finally:
            con.close()
    
    def get_last_10_days_fact(self, report_date):
        """Факт выручки за последние 10 дней"""
        start_date = report_date - timedelta(days=9)
        con = self._get_connection()
        try:
            sql = """
                SELECT
                    date_from,
                    COALESCE(SUM(CASE WHEN field = 'retail_price' AND oper = 'dt' THEN val ELSE 0 END), 0) / 100.0 AS sales_amount,
                    COALESCE(SUM(CASE WHEN field = 'retail_price' AND oper = 'cr' THEN val ELSE 0 END), 0) / 100.0 AS returns_amount,
                    COUNT(CASE WHEN field = 'retail_price' AND oper = 'dt' THEN 1 END) AS sales_transactions,
                    COUNT(CASE WHEN field = 'retail_price' AND oper = 'cr' THEN 1 END) AS returns_transactions
                FROM sales.sales_long
                WHERE date_from BETWEEN ? AND ?
                  AND field = 'retail_price'
                GROUP BY date_from
                ORDER BY date_from DESC
            """
            rows = con.execute(sql, [start_date, report_date]).fetchall()
            
            result = []
            for row in rows:
                sales_amount = float(row[1] or 0)
                returns_amount = float(row[2] or 0)
                result.append({
                    "date": row[0],
                    "sales_amount": sales_amount,
                    "returns_amount": returns_amount,
                    "net_amount": sales_amount - returns_amount,
                    "sales_transactions": int(row[3] or 0),
                    "returns_transactions": int(row[4] or 0),
                })
            
            # Заполняем пропущенные дни
            current = start_date
            existing_dates = {d["date"] for d in result}
            
            full_result = []
            while current <= report_date:
                if current in existing_dates:
                    day_data = next(d for d in result if d["date"] == current)
                    full_result.append(day_data)
                else:
                    full_result.append({
                        "date": current,
                        "sales_amount": 0.0,
                        "returns_amount": 0.0,
                        "net_amount": 0.0,
                        "sales_transactions": 0,
                        "returns_transactions": 0,
                    })
                current += timedelta(days=1)
            
            return list(reversed(full_result))
        finally:
            con.close()


# Создаём глобальный экземпляр
_revenue_connector = None


def get_revenue_connector():
    global _revenue_connector
    if _revenue_connector is None:
        _revenue_connector = RevenueDuckConnector()
    return _revenue_connector