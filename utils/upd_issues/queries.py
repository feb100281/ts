# # upd_issues/queries.py
# import os
# import duckdb
# import pandas as pd
# from dotenv import load_dotenv
# from typing import Dict

# load_dotenv()
# db_path = os.getenv("DUCKDB_PATH")


# class UpdIssuesQueries:
#     """Запросы к DuckDB для отчета по косякам в УПД"""
    
#     def __init__(self):
#         self.db_path = db_path
    
#     def get_all_issues(self, full_name: str = None) -> pd.DataFrame:
#         """
#         Получить все данные по косякам
#         Если full_name указан - фильтруем по конкретному файлу
#         """
#         con = duckdb.connect(self.db_path)
        
#         # Используем array_to_string для преобразования массивов в строки
#         query = """
#             SELECT 
#                 id,
#                 full_name,
#                 upd_pos,
#                 upd_sa_name,
#                 sa_pid,
#                 brand,
#                 upd_title,
#                 cards_titles,
#                 name_match,
#                 upd_size,
#                 array_to_string(available_sizes, ', ') as available_sizes,
#                 size_match,
#                 upd_vat_rate,
#                 card_vat_rate,
#                 match_vats,
#                 cert_end_date,
#                 cert_status,
#                 cert_match,
#                 upd_unit,
#                 upd_qty,
#                 upd_price_vatless,
#                 upd_amount_vatless,
#                 upd_vat_amount,
#                 upd_amount_vatadd
#             FROM analytics.upd.megamall_vs_cards
#         """
        
#         params = {}
#         if full_name:
#             query += " WHERE full_name = $full_name"
#             params["full_name"] = full_name
        
#         query += " ORDER BY full_name, name_match, size_match, match_vats, cert_match"
        
#         try:
#             df = con.execute(query, params).df()
            
#             # Преобразуем даты
#             if 'cert_end_date' in df.columns:
#                 df['cert_end_date'] = pd.to_datetime(df['cert_end_date'], errors='coerce').dt.strftime('%d.%m.%Y')
#                 df.loc[df['cert_end_date'].isna(), 'cert_end_date'] = '—'
            
#             # Преобразуем upd_size если он тоже массив (в SQL не получилось, делаем в pandas)
#             if 'upd_size' in df.columns:
#                 df['upd_size'] = df['upd_size'].apply(
#                     lambda x: ', '.join(str(v) for v in x) if isinstance(x, (list, tuple)) else str(x) if x and str(x) != 'nan' else '—'
#                 )
            
#             # Заменяем NaN на пустые строки
#             df = df.fillna('—')
            
#             # Преобразуем булевы значения в Python bool для корректной работы
#             bool_columns = ['name_match', 'size_match', 'match_vats', 'cert_match']
#             for col in bool_columns:
#                 if col in df.columns:
#                     df[col] = df[col].apply(
#                         lambda x: x in [True, 1, 'true', 'True', 't'] if pd.notna(x) else False
#                     )
            
#             return df
#         except Exception as e:
#             print(f"Error in get_all_issues: {e}")
#             raise
#         finally:
#             con.close()
    

  

#     def get_files_list(self) -> pd.DataFrame:
#         """Получить список уникальных файлов для оглавления со статистикой по каждому"""
#         con = duckdb.connect(self.db_path)
        
#         query = """
#             SELECT 
#                 full_name,
#                 ANY_VALUE(supplier) as supplier,
#                 COUNT(*) as total_issues,
#                 SUM(CASE WHEN name_match = FALSE THEN 1 ELSE 0 END) as name_mismatch,
#                 SUM(CASE WHEN size_match = FALSE THEN 1 ELSE 0 END) as size_mismatch,
#                 SUM(CASE WHEN match_vats = FALSE THEN 1 ELSE 0 END) as vat_mismatch,
#                 SUM(CASE WHEN cert_match = FALSE THEN 1 ELSE 0 END) as cert_issues,
#                 MAX(upd_pos) as total_positions
#             FROM analytics.upd.megamall_vs_cards
#             GROUP BY full_name
#             ORDER BY total_issues DESC
#         """
        
#         try:
#             df = con.execute(query).df()
#             df = df.fillna(0)
#             # Преобразуем типы
#             for col in ['total_issues', 'name_mismatch', 'size_mismatch', 'vat_mismatch', 'cert_issues', 'total_positions']:
#                 if col in df.columns:
#                     df[col] = df[col].astype(int)
#             return df
#         except Exception as e:
#             print(f"Error in get_files_list: {e}")
#             raise
#         finally:
#             con.close()
            
#     def get_summary_stats(self, full_name: str = None) -> Dict:
#         """Получить сводную статистику по всем косякам"""
#         con = duckdb.connect(self.db_path)
        
#         where_clause = ""
#         params = {}
#         if full_name:
#             where_clause = " WHERE full_name = $full_name"
#             params["full_name"] = full_name
        
#         query = f"""
#             SELECT 
#                 COUNT(*) as total_issues,
#                 COUNT(DISTINCT full_name) as total_files,
#                 SUM(CASE WHEN name_match = FALSE THEN 1 ELSE 0 END) as name_mismatch,
#                 SUM(CASE WHEN size_match = FALSE THEN 1 ELSE 0 END) as size_mismatch,
#                 SUM(CASE WHEN match_vats = FALSE THEN 1 ELSE 0 END) as vat_mismatch,
#                 SUM(CASE WHEN cert_match = FALSE THEN 1 ELSE 0 END) as cert_issues,
#                 SUM(upd_pos) as total_positions
#             FROM analytics.upd.megamall_vs_cards
#             {where_clause}
#         """
        
#         try:
#             result = con.execute(query, params).fetchone()
#             return {
#                 'total_issues': int(result[0]) if result[0] else 0,
#                 'total_files': int(result[1]) if result[1] else 0,
#                 'name_mismatch': int(result[2]) if result[2] else 0,
#                 'size_mismatch': int(result[3]) if result[3] else 0,
#                 'vat_mismatch': int(result[4]) if result[4] else 0,
#                 'cert_issues': int(result[5]) if result[5] else 0,
#                 'total_positions': int(result[6]) if result[6] else 0,
#             }
#         except Exception as e:
#             print(f"Error in get_summary_stats: {e}")
#             return {
#                 'total_issues': 0,
#                 'total_files': 0,
#                 'name_mismatch': 0,
#                 'size_mismatch': 0,
#                 'vat_mismatch': 0,
#                 'cert_issues': 0,
#                 'total_positions': 0,
#             }
#         finally:
#             con.close()
            


#     def get_document_totals(self, full_name: str) -> Dict:
#         """
#         Получить итоговые суммы по документу:
#         - общее количество товаров
#         - общая сумма без НДС
#         - общая сумма НДС
#         - общая сумма с НДС
#         """
#         con = duckdb.connect(self.db_path)
        
#         query = """
#             SELECT 
#                 SUM(upd_qty) as total_qty,
#                 SUM(upd_amount_vatless) as total_amount_vatless,
#                 SUM(upd_vat_amount) as total_vat_amount,
#                 SUM(upd_amount_vatadd) as total_amount_vatadd
#             FROM analytics.upd.megamall_vs_cards
#             WHERE full_name = $full_name
#         """
        
#         try:
#             result = con.execute(query, {"full_name": full_name}).fetchone()
#             return {
#                 'total_qty': float(result[0]) if result[0] else 0,
#                 'total_amount_vatless': float(result[1]) if result[1] else 0,
#                 'total_vat_amount': float(result[2]) if result[2] else 0,
#                 'total_amount_vatadd': float(result[3]) if result[3] else 0,
#             }
#         except Exception as e:
#             print(f"Error in get_document_totals: {e}")
#             return {
#                 'total_qty': 0,
#                 'total_amount_vatless': 0,
#                 'total_vat_amount': 0,
#                 'total_amount_vatadd': 0,
#             }
#         finally:
#             con.close()



# utils/upd_issues/queries.py
import os
import duckdb
import pandas as pd
from dotenv import load_dotenv
from typing import Dict

load_dotenv()
db_path = os.getenv("DUCKDB_PATH")


class UpdIssuesQueries:
    """Запросы к DuckDB для отчета по косякам в УПД"""
    
    def __init__(self):
        self.db_path = db_path
    
    def get_all_issues(self, full_name: str = None) -> pd.DataFrame:
        """
        Получить все данные по косякам
        Если full_name указан - фильтруем по конкретному файлу
        """
        con = duckdb.connect(self.db_path)
        
        query = """
            SELECT 
                id,
                full_name,
                upd_pos,
                upd_sa_name,
                sa_pid,
                brand,
                upd_title,
                cards_titles,
                name_match,
                match_article,
                upd_size,
                array_to_string(available_sizes, ', ') as available_sizes,
                size_match,
                upd_vat_rate,
                card_vat_rate,
                match_vats,
                cert_end_date,
                cert_status,
                cert_match,
                upd_unit,
                upd_qty,
                upd_price_vatless,
                upd_amount_vatless,
                upd_vat_amount,
                upd_amount_vatadd
            FROM analytics.upd.megamall_vs_cards
        """
        
        params = {}
        if full_name:
            query += " WHERE full_name = $full_name"
            params["full_name"] = full_name
        
        query += " ORDER BY full_name, name_match, match_article, size_match, match_vats, cert_match"
        
        try:
            df = con.execute(query, params).df()
            
            if 'cert_end_date' in df.columns:
                df['cert_end_date'] = pd.to_datetime(df['cert_end_date'], errors='coerce').dt.strftime('%d.%m.%Y')
                df.loc[df['cert_end_date'].isna(), 'cert_end_date'] = '—'
            
            if 'upd_size' in df.columns:
                df['upd_size'] = df['upd_size'].apply(
                    lambda x: ', '.join(str(v) for v in x) if isinstance(x, (list, tuple)) else str(x) if x and str(x) != 'nan' else '—'
                )
            
            df = df.fillna('—')
            
            bool_columns = ['name_match', 'match_article', 'size_match', 'match_vats', 'cert_match']
            for col in bool_columns:
                if col in df.columns:
                    df[col] = df[col].apply(
                        lambda x: x in [True, 1, 'true', 'True', 't'] if pd.notna(x) else False
                    )
            
            return df
        except Exception as e:
            print(f"Error in get_all_issues: {e}")
            raise
        finally:
            con.close()
    
    def get_files_list(self) -> pd.DataFrame:
        """Получить список уникальных файлов для оглавления со статистикой по каждому"""
        con = duckdb.connect(self.db_path)
        
        query = """
            SELECT 
                full_name,
                ANY_VALUE(supplier) as supplier,
                COUNT(*) as total_issues,
                SUM(CASE WHEN name_match = FALSE THEN 1 ELSE 0 END) as name_mismatch,
                SUM(CASE WHEN match_article = FALSE THEN 1 ELSE 0 END) as article_mismatch,
                SUM(CASE WHEN size_match = FALSE THEN 1 ELSE 0 END) as size_mismatch,
                SUM(CASE WHEN match_vats = FALSE THEN 1 ELSE 0 END) as vat_mismatch,
                SUM(CASE WHEN cert_match = FALSE THEN 1 ELSE 0 END) as cert_issues,
                SUM(upd_qty) as total_qty,  -- сумма количества товаров
                COUNT(DISTINCT upd_pos) as total_positions  -- количество уникальных позиций
            FROM analytics.upd.megamall_vs_cards
            GROUP BY full_name
            ORDER BY total_issues DESC
        """
        
        try:
            df = con.execute(query).df()
            df = df.fillna(0)
            for col in ['total_issues', 'name_mismatch', 'article_mismatch', 'size_mismatch', 'vat_mismatch', 'cert_issues', 'total_qty', 'total_positions']:
                if col in df.columns:
                    df[col] = df[col].astype(int)
            return df
        except Exception as e:
            print(f"Error in get_files_list: {e}")
            raise
        finally:
            con.close()
    
    def get_summary_stats(self, full_name: str = None) -> Dict:
        """Получить сводную статистику по всем косякам"""
        con = duckdb.connect(self.db_path)
        
        where_clause = ""
        params = {}
        if full_name:
            where_clause = " WHERE full_name = $full_name"
            params["full_name"] = full_name
        
        query = f"""
            SELECT 
                COUNT(*) as total_issues,
                COUNT(DISTINCT full_name) as total_files,
                SUM(CASE WHEN name_match = FALSE THEN 1 ELSE 0 END) as name_mismatch,
                SUM(CASE WHEN match_article = FALSE THEN 1 ELSE 0 END) as article_mismatch,
                SUM(CASE WHEN size_match = FALSE THEN 1 ELSE 0 END) as size_mismatch,
                SUM(CASE WHEN match_vats = FALSE THEN 1 ELSE 0 END) as vat_mismatch,
                SUM(CASE WHEN cert_match = FALSE THEN 1 ELSE 0 END) as cert_issues,
                SUM(upd_pos) as total_positions
            FROM analytics.upd.megamall_vs_cards
            {where_clause}
        """
        
        try:
            result = con.execute(query, params).fetchone()
            return {
                'total_issues': int(result[0]) if result[0] else 0,
                'total_files': int(result[1]) if result[1] else 0,
                'name_mismatch': int(result[2]) if result[2] else 0,
                'article_mismatch': int(result[3]) if result[3] else 0,
                'size_mismatch': int(result[4]) if result[4] else 0,
                'vat_mismatch': int(result[5]) if result[5] else 0,
                'cert_issues': int(result[6]) if result[6] else 0,
                'total_positions': int(result[7]) if result[7] else 0,
            }
        except Exception as e:
            print(f"Error in get_summary_stats: {e}")
            return {
                'total_issues': 0,
                'total_files': 0,
                'name_mismatch': 0,
                'article_mismatch': 0,
                'size_mismatch': 0,
                'vat_mismatch': 0,
                'cert_issues': 0,
                'total_positions': 0,
            }
        finally:
            con.close()
    
    def get_document_totals(self, full_name: str) -> Dict:
        """Получить итоговые суммы по документу"""
        con = duckdb.connect(self.db_path)
        
        query = """
            SELECT 
                SUM(upd_qty) as total_qty,
                SUM(upd_amount_vatless) as total_amount_vatless,
                SUM(upd_vat_amount) as total_vat_amount,
                SUM(upd_amount_vatadd) as total_amount_vatadd
            FROM analytics.upd.megamall_vs_cards
            WHERE full_name = $full_name
        """
        
        try:
            result = con.execute(query, {"full_name": full_name}).fetchone()
            return {
                'total_qty': float(result[0]) if result[0] else 0,
                'total_amount_vatless': float(result[1]) if result[1] else 0,
                'total_vat_amount': float(result[2]) if result[2] else 0,
                'total_amount_vatadd': float(result[3]) if result[3] else 0,
            }
        except Exception as e:
            print(f"Error in get_document_totals: {e}")
            return {
                'total_qty': 0,
                'total_amount_vatless': 0,
                'total_vat_amount': 0,
                'total_amount_vatadd': 0,
            }
        finally:
            con.close()