# cards/reporting/queries.py

import pandas as pd
from typing import Dict, List, Optional, Tuple
from conns import get_duckdb_conn_with_pg




class MissingFieldsQueries:
    """Запросы для отчетов по недостающим nm_id и chrt_id"""

    def _get_connection(self):
        return get_duckdb_conn_with_pg()

    def _build_upd_filter(self, upd_ids: Optional[List[int]]) -> Tuple[str, List[int]]:
        if not upd_ids:
            return "", []

        placeholders = ",".join(["?"] * len(upd_ids))
        return f"AND t.upd_document_id IN ({placeholders})", upd_ids

    def _base_query(self, missing_condition: str, upd_ids: Optional[List[int]] = None) -> pd.DataFrame:
        """
        Единый базовый запрос для отчетов:
        - нет NM_ID
        - нет CHRT_ID

        ВАЖНО:
        если в cards_upddocument дата называется не u.date,
        замени строку u.date AS upd_date на правильное поле.
        """

        upd_condition, params = self._build_upd_filter(upd_ids)

        query = f"""
            SELECT 
                t.id,
                t.upd_pos,
                t.upd_document_id,

                u.number AS upd_number,
                u.date AS upd_date,

                c.name AS counterparty_name,

                t.brand,
                t.upd_title,
                t.upd_sa_name,
                t.upd_size,

                t.nm_id,
                p.sa_name AS wb_sa_name,
    
                CAST(p.available_sizes AS VARCHAR) AS available_sizes,

                t.upd_qty,

                CASE 
                    WHEN COALESCE(t.upd_qty, 0) <> 0 THEN t.upd_amount_vatadd / t.upd_qty
                    ELSE NULL
                END AS upd_price_vatadd,

                t.upd_amount_vatadd,

                CASE
                    WHEN u.date IS NULL THEN CAST(u.number AS VARCHAR)
                    ELSE CAST(u.number AS VARCHAR) || ' от ' || STRFTIME(CAST(u.date AS DATE), '%d.%m.%Y')
                END AS upd_info

            FROM pg.public.upd_income_lines t

            LEFT JOIN pg.public.cards_upddocument u 
                ON u.id = t.upd_document_id

            LEFT JOIN pg.public.counterparties_counterparty c 
                ON c.id = u.counterparty_id

            LEFT JOIN analytics.cards.product p
                ON p.nm_id = t.nm_id

            WHERE {missing_condition}
                {upd_condition}

            ORDER BY t.upd_document_id, t.upd_pos
        """
   

        with self._get_connection() as conn:
            return conn.sql(query, params=params).df()

    def get_missing_nm_data(self, upd_ids: List[int] = None) -> pd.DataFrame:
        """Строки, где не заполнен nm_id"""

        df = self._base_query(
            missing_condition="t.nm_id IS NULL",
            upd_ids=upd_ids,
        )

        print(f"Found {len(df)} rows with missing nm_id")
        return df

    def get_missing_chrt_data(self, upd_ids: List[int] = None) -> pd.DataFrame:
        """
        Строки, где не заполнен chrt_id.
        nm_id при этом может быть заполнен.
        """

        df = self._base_query(
            missing_condition="t.chrt_id IS NULL",
            upd_ids=upd_ids,
        )

        print(f"Found {len(df)} rows with missing chrt_id")
        return df

    def _group_missing_data(self, df: pd.DataFrame, group_cols: List[str]) -> pd.DataFrame:
        """Единая группировка для двух отчетов"""

        if df.empty:
            return df

        grouped = (
            df.groupby(group_cols, dropna=False)
            .agg(
                upd_info=(
                    "upd_info",
                    lambda x: ", ".join(
                        sorted(set(str(v) for v in x if pd.notna(v) and str(v) != "—"))
                    ),
                ),
                counterparty_name=(
                    "counterparty_name",
                    lambda x: ", ".join(
                        sorted(set(str(v) for v in x if pd.notna(v) and str(v) != "—"))
                    ),
                ),
                upd_qty=("upd_qty", "sum"),
                upd_amount_vatadd=("upd_amount_vatadd", "sum"),
            )
            .reset_index()
        )

        grouped["upd_price_vatadd"] = grouped.apply(
            lambda row: (
                row["upd_amount_vatadd"] / row["upd_qty"]
                if pd.notna(row["upd_qty"]) and row["upd_qty"] != 0
                else None
            ),
            axis=1,
        )

        grouped = grouped.sort_values("upd_amount_vatadd", ascending=False)

        return grouped

    def get_grouped_missing_nm(self, upd_ids: List[int] = None) -> pd.DataFrame:
        """Сгруппированный отчет по товарам без NM_ID"""

        df = self.get_missing_nm_data(upd_ids)

        group_cols = [
            "upd_sa_name",
            "brand",
            "upd_title",
            "upd_size",
        ]

        grouped = self._group_missing_data(df, group_cols)

        print(f"Grouped missing nm_id rows: {len(grouped)}")
        return grouped

    def get_grouped_missing_chrt(self, upd_ids: List[int] = None) -> pd.DataFrame:
        """Сгруппированный отчет по товарам без CHRT_ID / размера"""

        df = self.get_missing_chrt_data(upd_ids)

        group_cols = [
            "upd_sa_name",
            "brand",
            "upd_title",
            "nm_id",
            "wb_sa_name",
            "available_sizes",
            "upd_size",
        ]

        grouped = self._group_missing_data(df, group_cols)

        print(f"Grouped missing chrt_id rows: {len(grouped)}")
        return grouped

    def get_summary_stats(self, upd_ids: List[int] = None) -> Dict:
        """
        Сводная статистика из той же таблицы, что и Excel:
        pg.public.upd_income_lines
        """

        if not upd_ids:
            return self._empty_stats()

        upd_condition, params = self._build_upd_filter(upd_ids)

        query = f"""
            SELECT
                COUNT(*) AS total_lines,

                COALESCE(SUM(t.upd_amount_vatadd), 0) AS total_amount_vatadd,

                COUNT(*) FILTER (
                    WHERE t.nm_id IS NULL
                ) AS missing_nm_count,

                COALESCE(SUM(t.upd_qty) FILTER (
                    WHERE t.nm_id IS NULL
                ), 0) AS missing_nm_qty,

                COALESCE(SUM(t.upd_amount_vatadd) FILTER (
                    WHERE t.nm_id IS NULL
                ), 0) AS missing_nm_amount,

                COUNT(*) FILTER (
                    WHERE t.chrt_id IS NULL
                ) AS missing_chrt_count,

                COALESCE(SUM(t.upd_qty) FILTER (
                    WHERE t.chrt_id IS NULL
                ), 0) AS missing_chrt_qty,

                COALESCE(SUM(t.upd_amount_vatadd) FILTER (
                    WHERE t.chrt_id IS NULL
                ), 0) AS missing_chrt_amount

            FROM pg.public.upd_income_lines t

            WHERE 1 = 1
                {upd_condition}
        """

        with self._get_connection() as conn:
            df = conn.sql(query, params=params).df()

        row = df.iloc[0]

        return {
            "total_upd_count": len(upd_ids),
            "total_lines": int(row["total_lines"]),
            "total_amount_vatadd": float(row["total_amount_vatadd"]),

            "missing_nm_count": int(row["missing_nm_count"]),
            "missing_nm_qty": float(row["missing_nm_qty"]),
            "missing_nm_amount": float(row["missing_nm_amount"]),

            "missing_chrt_count": int(row["missing_chrt_count"]),
            "missing_chrt_qty": float(row["missing_chrt_qty"]),
            "missing_chrt_amount": float(row["missing_chrt_amount"]),
        }
        
        
        
    
    # cards/reporting/queries.py
# Добавить в класс MissingFieldsQueries:

    def get_upd_list(self, upd_ids: List[int] = None) -> List[Dict]:
        """Получить список УПД с номерами, датами и контрагентами"""
        
        if not upd_ids:
            return []
        
        placeholders = ",".join(["?"] * len(upd_ids))
        
        query = f"""
            SELECT DISTINCT
                u.id,
                u.number,
                u.date,
                c.name AS counterparty
            FROM pg.public.cards_upddocument u
            LEFT JOIN pg.public.counterparties_counterparty c 
                ON c.id = u.counterparty_id
            WHERE u.id IN ({placeholders})
            ORDER BY u.date DESC, u.number
        """
        
        with self._get_connection() as conn:
            df = conn.sql(query, params=upd_ids).df()
        
        result = []
        for _, row in df.iterrows():
            date_val = row["date"]
            date_str = date_val.strftime("%d.%m.%Y") if hasattr(date_val, "strftime") else str(date_val)
            result.append({
                "id": int(row["id"]),
                "number": row["number"],
                "date": date_str,
                "counterparty": row["counterparty"] if row["counterparty"] else "Не указан",
            })
        
        return result
    
    def get_missing_nm_by_upd(self, upd_ids: List[int] = None) -> List[Dict]:
        """Получить распределение проблем с NM_ID по УПД"""
        
        if not upd_ids:
            return []
        
        placeholders = ",".join(["?"] * len(upd_ids))
        
        query = f"""
            SELECT
                t.upd_document_id,
                u.number,
                u.date,
                COUNT(*) AS count,
                COALESCE(SUM(t.upd_qty), 0) AS qty,
                COALESCE(SUM(t.upd_amount_vatadd), 0) AS amount
            FROM pg.public.upd_income_lines t
            LEFT JOIN pg.public.cards_upddocument u 
                ON u.id = t.upd_document_id
            WHERE t.nm_id IS NULL
                AND t.upd_document_id IN ({placeholders})
            GROUP BY t.upd_document_id, u.number, u.date
            ORDER BY amount DESC
        """
        
        with self._get_connection() as conn:
            df = conn.sql(query, params=upd_ids).df()
        
        result = []
        for _, row in df.iterrows():
            date_val = row["date"]
            date_str = date_val.strftime("%d.%m.%Y") if hasattr(date_val, "strftime") else str(date_val)
            result.append({
                "id": int(row["upd_document_id"]),
                "number": row["number"],
                "date": date_str,
                "count": int(row["count"]),
                "qty": float(row["qty"]),
                "amount": float(row["amount"]),
            })
        
        return result
    
    def get_missing_chrt_by_upd(self, upd_ids: List[int] = None) -> List[Dict]:
        """Получить распределение проблем с CHRT_ID по УПД"""
        
        if not upd_ids:
            return []
        
        placeholders = ",".join(["?"] * len(upd_ids))
        
        query = f"""
            SELECT
                t.upd_document_id,
                u.number,
                u.date,
                COUNT(*) AS count,
                COALESCE(SUM(t.upd_qty), 0) AS qty,
                COALESCE(SUM(t.upd_amount_vatadd), 0) AS amount
            FROM pg.public.upd_income_lines t
            LEFT JOIN pg.public.cards_upddocument u 
                ON u.id = t.upd_document_id
            WHERE t.chrt_id IS NULL
                AND t.upd_document_id IN ({placeholders})
            GROUP BY t.upd_document_id, u.number, u.date
            ORDER BY amount DESC
        """
        
        with self._get_connection() as conn:
            df = conn.sql(query, params=upd_ids).df()
        
        result = []
        for _, row in df.iterrows():
            date_val = row["date"]
            date_str = date_val.strftime("%d.%m.%Y") if hasattr(date_val, "strftime") else str(date_val)
            result.append({
                "id": int(row["upd_document_id"]),
                "number": row["number"],
                "date": date_str,
                "count": int(row["count"]),
                "qty": float(row["qty"]),
                "amount": float(row["amount"]),
            })
        
        return result

    def _empty_stats(self) -> Dict:
        return {
            "total_upd_count": 0,
            "total_lines": 0,
            "total_amount_vatadd": 0,

            "missing_nm_count": 0,
            "missing_nm_qty": 0,
            "missing_nm_amount": 0,

            "missing_chrt_count": 0,
            "missing_chrt_qty": 0,
            "missing_chrt_amount": 0,
        }