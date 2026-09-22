# contracts/loans_report/queries.py

import os
import json
import traceback
from typing import List, Dict, Any

import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv

load_dotenv()


def get_db_connection():
    return psycopg.connect(
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        connect_timeout=10,
    )


class LoansQueries:

    def _default_conditions(self) -> Dict:
        return {
            "condition_rate": None,
            "compounding": False,
            "repayment_date": None,
            "penalty_rate": 0,
            "condition_contract_amount": 0,
            "repay_principal_first": False,
            "repay_interest_first": False,
        }

    def _parse_conditions(self, param_json: Any) -> Dict:
        result = self._default_conditions()

        if not param_json:
            return result

        try:
            if isinstance(param_json, dict):
                data = param_json
            else:
                # Очистка строки
                clean_json = str(param_json)
                
                # 1. Убираем float()
                clean_json = clean_json.replace("float(", "").replace(")", "")
                
                # 2. Убираем лишние кавычки вокруг даты
                # "''2025-09-30''" -> "2025-09-30"
                import re
                clean_json = re.sub(r"'(\d{4}-\d{2}-\d{2})'", r'\1', clean_json)
                clean_json = re.sub(r'"(\d{4}-\d{2}-\d{2})"', r'\1', clean_json)
                
                # 3. Одинарные кавычки на двойные для JSON
                clean_json = clean_json.replace("'", '"')
                
                data = json.loads(clean_json)

            # Парсинг даты погашения
            repayment_date = data.get("Дата погашения")
            if repayment_date:
                # Если строка пришла с кавычками - убираем
                repayment_date = str(repayment_date).strip("'\"")
                if repayment_date.lower() in ['none', 'null', '']:
                    repayment_date = None
                else:
                    # Проверяем формат YYYY-MM-DD
                    try:
                        from datetime import datetime
                        datetime.strptime(repayment_date, '%Y-%m-%d')
                    except:
                        repayment_date = None

            # Парсинг профиля погашения
            repayment_profile = data.get("Профиль погашения") or {}

            # Парсинг штрафного процента
            penalty = data.get("Штрафной процент")
            if penalty is not None:
                if isinstance(penalty, (int, float)):
                    penalty_rate = float(penalty)
                elif isinstance(penalty, str):
                    clean_penalty = penalty.replace("float(", "").replace(")", "").strip()
                    try:
                        penalty_rate = float(clean_penalty)
                    except:
                        penalty_rate = 0
                else:
                    penalty_rate = 0
            else:
                penalty_rate = 0

            result.update({
                "condition_rate": data.get("Ставка"),
                "compounding": bool(data.get("Компаудинг", False)),
                "repayment_date": repayment_date,
                "penalty_rate": penalty_rate,
                "condition_contract_amount": data.get("Сумма по договору") or 0,
                "repay_principal_first": bool(repayment_profile.get("Сначало тело", False)),
                "repay_interest_first": bool(repayment_profile.get("Сначало проценты", False)),
            })

            return result

        except Exception as e:
            print(f"Error parsing conditions: {e}, param_json: {param_json}")
            return result

   
    def get_full_report_data(self, report_date: str) -> Dict:
        """
        Возвращает все данные для отчета одним запросом
        Возвращает: {
            'loans': [...],           # список договоров с основными данными
            'transactions': {         # словарь {contract_id: [transactions]}
                contract_id: [...]
            }
        }
        """
        conn = None
        try:
            conn = get_db_connection()
            
            with conn.cursor(row_factory=dict_row) as cur:
                # ЕДИНСТВЕННЫЙ ЗАПРОС - получаем всё сразу
                query = """
                    WITH loan_aggregates AS (
                        SELECT 
                            t.contract_id,
                            SUM(t.drawdown_amount) / 100.0 AS total_drawdown,
                            SUM(t.repaid_amount) / 100.0 AS total_repaid
                        FROM gl.borrowings_tp t
                        WHERE t.date_from <= %s::date
                        GROUP BY t.contract_id
                    ),
                    latest_loan_state AS (
                        SELECT DISTINCT ON (t.contract_id)
                            t.contract_id,
                            t.contract_amount / 100.0 AS contract_amount,
                            t.rate / 100.0 AS rate,
                            t.eb / 100.0 AS ending_balance,
                            t.interest_balance / 100.0 AS interest_balance,
                            t.total_debt / 100.0 AS total_debt,
                            t.date_from
                        FROM gl.borrowings_tp t
                        WHERE t.date_from <= %s::date
                        ORDER BY t.contract_id, t.date_from DESC
                    )
                    SELECT 
                        -- Данные договора
                        t.contract_id,
                        c.number AS contract_number,
                        c.date AS contract_date,
                        cp.name AS counterparty_name,
                        cp.tax_id AS inn,
                        c.currency,
                        ct.title AS contract_type,
                        cc.param_json AS param_json,
                        
                        -- Агрегаты
                        la.total_drawdown,
                        la.total_repaid,
                        
                        -- Последнее состояние
                        ls.contract_amount,
                        ls.rate,
                        ls.ending_balance,
                        ls.interest_balance,
                        ls.total_debt,
                        
                        -- Детальные транзакции (как JSON для группировки)
                        JSONB_AGG(
                            JSONB_BUILD_OBJECT(
                                'date_from', t.date_from,
                                'operation_description', t.operation_description,
                                'interest_description', t.interest_description,
                                'drawdown_amount', t.drawdown_amount / 100.0,
                                'principal_repayment', t.principal_repayment / 100.0,
                                'interest_accrued', t.interest_accrued / 100.0,
                                'interest_repayment', t.interest_repayment / 100.0,
                                'ending_balance', t.eb / 100.0,
                                'interest_balance', t.interest_balance / 100.0,
                                'total_debt', t.total_debt / 100.0,
                                'rate', t.rate / 100.0
                            )
                            ORDER BY t.date_from
                        ) AS transactions_json
                        
                    FROM gl.borrowings_tp t
                    
                    LEFT JOIN public.contracts_contracts c 
                        ON c.id = t.contract_id
                        
                    LEFT JOIN public.counterparties_counterparty cp 
                        ON cp.id = c.cp_id
                        
                    LEFT JOIN public.contracts_contractstitle ct 
                        ON ct.id = c.title_id
                        
                    LEFT JOIN loan_aggregates la ON la.contract_id = t.contract_id
                    
                    LEFT JOIN latest_loan_state ls ON ls.contract_id = t.contract_id
                    
                    LEFT JOIN LATERAL (
                        SELECT cc.param_json
                        FROM public.contracts_conditions cc
                        WHERE cc.contract_id = t.contract_id
                        ORDER BY cc.id DESC
                        LIMIT 1
                    ) cc ON TRUE
                    
                    WHERE t.date_from <= %s::date
                        AND t.total_debt IS NOT NULL
                        
                    GROUP BY 
                        t.contract_id, c.number, c.date, cp.name, cp.tax_id, 
                        c.currency, ct.title, cc.param_json, 
                        la.total_drawdown, la.total_repaid,
                        ls.contract_amount, ls.rate, ls.ending_balance, 
                        ls.interest_balance, ls.total_debt
                        
                    ORDER BY cp.name
                """
                
                cur.execute(query, (report_date, report_date, report_date))
                rows = cur.fetchall()
                
                # Преобразуем в удобный формат
                loans_list = []
                transactions_by_contract = {}
                
                for row in rows:
                    # Извлекаем транзакции из JSON
                    transactions_json = row.get('transactions_json', [])
                    contract_id = row['contract_id']
                    
                    # Сохраняем транзакции в словарь
                    if transactions_json:
                        transactions_by_contract[contract_id] = transactions_json
                    
                    # Создаем запись о договоре (без транзакций)
                    loan = dict(row)
                    loan.pop('transactions_json', None)  # Убираем JSON транзакций
                    
                    # Парсим условия
                    conditions = self._parse_conditions(loan.get('param_json'))
                    loan.update(conditions)
                    loan.pop('param_json', None)
                    
                    # Значения по умолчанию
                    if loan.get('total_drawdown') is None:
                        loan['total_drawdown'] = 0
                    if loan.get('total_repaid') is None:
                        loan['total_repaid'] = 0
                        
                    loans_list.append(loan)
                
                return {
                    'loans': loans_list,
                    'transactions': transactions_by_contract
                }
                
        except Exception as e:
            traceback.print_exc()
            return {'loans': [], 'transactions': {}}
        finally:
            if conn:
                conn.close()
                
                
                
                
    