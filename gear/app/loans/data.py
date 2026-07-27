# gear/app/loans/data.py
from __future__ import annotations

import json
import os
import re
from datetime import date
from typing import Any

import pandas as pd
import psycopg
from psycopg.rows import dict_row


def get_db_connection():
    return psycopg.connect(
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        connect_timeout=10,
    )


def _default_conditions() -> dict:
    return {
        "condition_rate": None,
        "compounding": False,
        "repayment_date": None,
        "penalty_rate": 0.0,
        "condition_contract_amount": 0.0,
        "repay_principal_first": False,
        "repay_interest_first": False,
    }


def _parse_conditions(param_json: Any) -> dict:
    result = _default_conditions()

    if not param_json:
        return result

    try:
        if isinstance(param_json, dict):
            data = param_json
        else:
            clean_json = str(param_json)
            clean_json = clean_json.replace("float(", "").replace(")", "")
            clean_json = re.sub(
                r"'(\d{4}-\d{2}-\d{2})'",
                r'"\1"',
                clean_json,
            )
            clean_json = clean_json.replace("'", '"')
            data = json.loads(clean_json)

        repayment_date = data.get("Дата погашения")
        if repayment_date:
            repayment_date = str(repayment_date).strip("'\"")
            parsed = pd.to_datetime(
                repayment_date,
                errors="coerce",
            )
            repayment_date = (
                parsed.date().isoformat()
                if pd.notna(parsed)
                else None
            )

        repayment_profile = (
            data.get("Профиль погашения")
            or {}
        )

        penalty = data.get("Штрафной процент")
        try:
            penalty_rate = float(
                str(penalty)
                .replace("float(", "")
                .replace(")", "")
                .strip()
            ) if penalty is not None else 0.0
        except (TypeError, ValueError):
            penalty_rate = 0.0

        condition_amount = (
            data.get("Сумма по договору")
            or 0
        )
        try:
            condition_amount = float(condition_amount)
        except (TypeError, ValueError):
            condition_amount = 0.0

        condition_rate = data.get("Ставка")
        try:
            condition_rate = (
                float(condition_rate)
                if condition_rate is not None
                else None
            )
        except (TypeError, ValueError):
            condition_rate = None

        result.update(
            {
                "condition_rate": condition_rate,
                "compounding": bool(
                    data.get("Компаудинг", False)
                ),
                "repayment_date": repayment_date,
                "penalty_rate": penalty_rate,
                "condition_contract_amount": condition_amount,
                "repay_principal_first": bool(
                    repayment_profile.get(
                        "Сначало тело",
                        False,
                    )
                ),
                "repay_interest_first": bool(
                    repayment_profile.get(
                        "Сначало проценты",
                        False,
                    )
                ),
            }
        )
    except Exception:
        return result

    return result


def get_min_borrowing_date() -> date:
    query = """
        SELECT MIN(date_from)::date
        FROM gl.borrowings_tp
    """

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            value = cur.fetchone()[0]

    return value or date.today()


def get_loans_snapshot(
    report_date: str,
) -> pd.DataFrame:
    query = """
        WITH loan_aggregates AS (
            SELECT
                t.contract_id,
                SUM(COALESCE(t.drawdown_amount, 0))
                    / 100.0 AS total_drawdown,
                SUM(COALESCE(t.repaid_amount, 0))
                    / 100.0 AS total_repaid,
                SUM(COALESCE(t.interest_accrued, 0))
                    / 100.0 AS total_interest_accrued,
                SUM(COALESCE(t.interest_repayment, 0))
                    / 100.0 AS total_interest_repaid
            FROM gl.borrowings_tp t
            WHERE t.date_from <= %s::date
            GROUP BY t.contract_id
        ),
        latest_loan_state AS (
            SELECT DISTINCT ON (t.contract_id)
                t.contract_id,
                t.contract_amount / 100.0 AS contract_amount,
                COALESCE(t.rate, 0) AS rate,
                t.eb / 100.0 AS ending_balance,
                t.interest_balance / 100.0 AS interest_balance,
                t.total_debt / 100.0 AS total_debt,
                t.date_from::date AS last_state_date
            FROM gl.borrowings_tp t
            WHERE t.date_from <= %s::date
            ORDER BY
                t.contract_id,
                t.date_from DESC
        )
        SELECT
            ls.contract_id,
            c.number AS contract_number,
            c.date::date AS contract_date,
            cp.name AS counterparty_name,
            cp.tax_id AS inn,
            c.currency,
            ct.title AS contract_type,
            COALESCE(
                files.documents_count,
                0
            ) AS documents_count,
            
            cc.param_json,

            COALESCE(la.total_drawdown, 0)
                AS total_drawdown,
            COALESCE(la.total_repaid, 0)
                AS total_repaid,
            COALESCE(la.total_interest_accrued, 0)
                AS total_interest_accrued,
            COALESCE(la.total_interest_repaid, 0)
                AS total_interest_repaid,

            COALESCE(ls.contract_amount, 0)
                AS contract_amount,
            COALESCE(ls.rate, 0)
                AS rate,
            COALESCE(ls.ending_balance, 0)
                AS ending_balance,
            COALESCE(ls.interest_balance, 0)
                AS interest_balance,
            COALESCE(ls.total_debt, 0)
                AS total_debt,
            ls.last_state_date

        FROM latest_loan_state ls

        LEFT JOIN public.contracts_contracts c
            ON c.id = ls.contract_id

        LEFT JOIN public.counterparties_counterparty cp
            ON cp.id = c.cp_id

        LEFT JOIN public.contracts_contractstitle ct
            ON ct.id = c.title_id

        LEFT JOIN loan_aggregates la
            ON la.contract_id = ls.contract_id

        LEFT JOIN LATERAL (
            SELECT cc.param_json
            FROM public.contracts_conditions cc
            WHERE cc.contract_id = ls.contract_id
            ORDER BY cc.id DESC
            LIMIT 1
        ) cc ON TRUE
        
        LEFT JOIN LATERAL (
    SELECT
        COUNT(*) AS documents_count

    FROM public.contracts_contractfiles cf

    WHERE
        cf.contract_id = ls.contract_id

        AND cf.file IS NOT NULL

        AND cf.file <> ''

) files ON TRUE

        ORDER BY
            cp.name NULLS LAST,
            c.number NULLS LAST
    """

    with get_db_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                query,
                (report_date, report_date),
            )
            rows = cur.fetchall()

    if not rows:
        return pd.DataFrame()

    records = []
    for row in rows:
        item = dict(row)
        conditions = _parse_conditions(
            item.pop("param_json", None)
        )
        item.update(conditions)
        records.append(item)

    df = pd.DataFrame(records)

    for column in (
        "contract_date",
        "last_state_date",
        "repayment_date",
    ):
        if column in df.columns:
            df[column] = pd.to_datetime(
                df[column],
                errors="coerce",
            )

    return df


def get_portfolio_dynamics(
    date_from: str,
    date_to: str,
    contract_ids: list[int] | None = None,
) -> pd.DataFrame:
    """
    Динамика портфеля задолженности.

    ВАЖНО:
    borrowings_tp не является ежедневным snapshot
    по каждому договору.

    Поэтому для каждой календарной даты берём
    последнее известное состояние каждого договора
    на эту дату.

    Благодаря этому:
    - договор не исчезает из портфеля в дни,
      когда по нему не было операций;
    - конечное значение графика совпадает
      со snapshot на ту же дату.
    """

    if not contract_ids:
        return pd.DataFrame(
            columns=[
                "date_from",
                "principal_debt",
                "interest_debt",
                "total_debt",
            ]
        )

    query = """
        WITH dates AS (
            SELECT
                generate_series(
                    %s::date,
                    %s::date,
                    interval '1 day'
                )::date AS date_from
        ),

        contracts AS (
            SELECT
                UNNEST(%s::bigint[]) AS contract_id
        ),

        daily_states AS (
            SELECT
                d.date_from,
                c.contract_id,

                COALESCE(
                    state.eb,
                    0
                ) / 100.0 AS principal_debt,

                COALESCE(
                    state.interest_balance,
                    0
                ) / 100.0 AS interest_debt,

                COALESCE(
                    state.total_debt,
                    0
                ) / 100.0 AS total_debt

            FROM dates d

            CROSS JOIN contracts c

            LEFT JOIN LATERAL (
                SELECT
                    t.eb,
                    t.interest_balance,
                    t.total_debt

                FROM gl.borrowings_tp t

                WHERE
                    t.contract_id = c.contract_id
                    AND t.date_from <= d.date_from

                ORDER BY
                    t.date_from DESC

                LIMIT 1
            ) state
                ON TRUE
        )

        SELECT
            date_from,

            SUM(
                principal_debt
            ) AS principal_debt,

            SUM(
                interest_debt
            ) AS interest_debt,

            SUM(
                total_debt
            ) AS total_debt

        FROM daily_states

        GROUP BY
            date_from

        ORDER BY
            date_from
    """

    with get_db_connection() as conn:
        with conn.cursor(
            row_factory=dict_row
        ) as cur:

            cur.execute(
                query,
                (
                    date_from,
                    date_to,
                    contract_ids,
                ),
            )

            rows = cur.fetchall()

    if not rows:
        return pd.DataFrame(
            columns=[
                "date_from",
                "principal_debt",
                "interest_debt",
                "total_debt",
            ]
        )

    df = pd.DataFrame(
        rows
    )

    df["date_from"] = pd.to_datetime(
        df["date_from"],
        errors="coerce",
    )

    for column in (
        "principal_debt",
        "interest_debt",
        "total_debt",
    ):
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce",
        ).fillna(0)

    return df

def get_interest_flow(
    date_from: str,
    date_to: str,
    contract_ids: list[int] | None = None,
) -> pd.DataFrame:
    query = """
        SELECT
            DATE_TRUNC(
                'month',
                t.date_from
            )::date AS month,
            SUM(COALESCE(t.interest_accrued, 0))
                / 100.0 AS interest_accrued,
            SUM(COALESCE(t.interest_repayment, 0))
                / 100.0 AS interest_repaid
        FROM gl.borrowings_tp t
        WHERE t.date_from BETWEEN %s::date AND %s::date
    """

    params: list[Any] = [date_from, date_to]

    if contract_ids:
        query += """
            AND t.contract_id = ANY(%s)
        """
        params.append(contract_ids)

    query += """
        GROUP BY 1
        ORDER BY 1
    """

    with get_db_connection() as conn:
        df = pd.read_sql_query(
            query,
            conn,
            params=params,
        )

    if not df.empty:
        df["month"] = pd.to_datetime(
            df["month"],
            errors="coerce",
        )

    return df


# def get_contract_transactions(
#     contract_id: int,
#     date_to: str | None = None,
# ) -> pd.DataFrame:
#     query = """
#         SELECT
#             t.contract_id,
#             t.date_from::date AS date_from,
#             t.operation_description,
#             t.interest_description,
#             COALESCE(t.drawdown_amount, 0)
#                 / 100.0 AS drawdown_amount,
#             COALESCE(t.principal_repayment, 0)
#                 / 100.0 AS principal_repayment,
#             COALESCE(t.interest_accrued, 0)
#                 / 100.0 AS interest_accrued,
#             COALESCE(t.interest_repayment, 0)
#                 / 100.0 AS interest_repayment,
#             COALESCE(t.eb, 0)
#                 / 100.0 AS ending_balance,
#             COALESCE(t.interest_balance, 0)
#                 / 100.0 AS interest_balance,
#             COALESCE(t.total_debt, 0)
#                 / 100.0 AS total_debt,
#             COALESCE(t.rate, 0) AS rate
#         FROM gl.borrowings_tp t
#         WHERE t.contract_id = %s
#     """

#     params: list[Any] = [contract_id]

#     if date_to:
#         query += """
#             AND t.date_from <= %s::date
#         """
#         params.append(date_to)

#     query += """
#         ORDER BY t.date_from
#     """

#     with get_db_connection() as conn:
#         df = pd.read_sql_query(
#             query,
#             conn,
#             params=params,
#         )

#     if not df.empty:
#         df["date_from"] = pd.to_datetime(
#             df["date_from"],
#             errors="coerce",
#         )

#     return df



def get_contract_transactions(
    contract_id: int,
    date_to: str | None = None,
) -> pd.DataFrame:
    """
    История выбранного договора.

    Если передана date_to, возвращаем состояние
    и операции только по эту дату включительно.

    Будущие прогнозные строки в выборку не попадают.
    """

    query = """
        SELECT
            t.contract_id,

            t.date_from::date AS date_from,

            t.operation_description,
            t.interest_description,

            COALESCE(
                t.drawdown_amount,
                0
            ) / 100.0 AS drawdown_amount,

            COALESCE(
                t.principal_repayment,
                0
            ) / 100.0 AS principal_repayment,

            COALESCE(
                t.interest_accrued,
                0
            ) / 100.0 AS interest_accrued,

            COALESCE(
                t.interest_repayment,
                0
            ) / 100.0 AS interest_repayment,

            COALESCE(
                t.eb,
                0
            ) / 100.0 AS ending_balance,

            COALESCE(
                t.interest_balance,
                0
            ) / 100.0 AS interest_balance,

            COALESCE(
                t.total_debt,
                0
            ) / 100.0 AS total_debt,

            -- ВАЖНО:
            -- ставка в borrowings_tp уже хранится
            -- как 19.25, а не 0.1925.
            COALESCE(
                t.rate,
                0
            ) AS rate

        FROM gl.borrowings_tp t

        WHERE
            t.contract_id = %s
    """

    params = [
        contract_id,
    ]

    if date_to:
        query += """
            AND t.date_from::date <= %s::date
        """

        params.append(
            date_to
        )

    query += """
        ORDER BY
            t.date_from
    """

    with get_db_connection() as conn:

        df = pd.read_sql_query(
            query,
            conn,
            params=params,
        )

    if df.empty:
        return df

    df["date_from"] = pd.to_datetime(
        df["date_from"],
        errors="coerce",
    )

    return df
