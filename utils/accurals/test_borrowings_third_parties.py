import psycopg
from psycopg.rows import dict_row
import pandas as pd
import numpy as np
from pprint import pprint


def insert_borrowings_tp(conn, final: dict):
    cols = [
        "date_from",
        "contract_id",
        "contract_amount",
        "available_amount",
        "drawdown_amount",
        "bb",
        "rate",
        "interest_accrued",
        "principal_repayment",
        "interest_repayment",
        "repaid_amount",
        "eb",
        "interest_balance",
        "total_debt",
        "operation_description",
        "interest_description",
    ]

    int_cols = {
        "contract_id",
        "contract_amount",
        "available_amount",
        "drawdown_amount",
        "bb",
        "interest_accrued",
        "principal_repayment",
        "interest_repayment",
        "repaid_amount",
        "eb",
        "interest_balance",
        "total_debt",
    }

    n = len(final["date_from"])

    with conn.cursor() as cur:
        with cur.copy(
            """
            COPY gl.borrowings_tp (
                date_from,
                contract_id,
                contract_amount,
                available_amount,
                drawdown_amount,
                bb,
                rate,
                interest_accrued,
                principal_repayment,
                interest_repayment,
                repaid_amount,
                eb,
                interest_balance,
                total_debt,
                operation_description,
                interest_description
            )
            FROM STDIN
        """
        ) as copy:
            for i in range(n):
                row = []
                for col in cols:
                    value = final[col][i]

                    if hasattr(value, "item"):
                        value = value.item()

                    if col in int_cols and value is not None:
                        value = int(value)

                    row.append(value)

                copy.write_row(row)

    conn.commit()


def borrowing_third_party(conn, **args):
    # Получаем параметры для расчеты
    param = args.get("params_json", None)

    # Получаем счет для начислений
    acc_st_id = args.get("acc_st_id", None)

    rate_exp = str(param["Ставка"])

    penalty_rate = eval(str(param["Штрафной процент"]))

    contract_id = args.get("contract_id", None)
    q = f"""
        SELECT 
        date_from, 
        sum(dt) as dt, 
        sum(cr) as cr,
        string_agg(description, ', ') as description
        FROM gl.fact 
        where contract_id = {contract_id} 
        group by date_from order by date_from
        """

    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(q)
        cf = cur.fetchall()

    cf = pd.DataFrame(cf)

    ds = args.get("date_start", None)
    if not ds:
        date_start = pd.to_datetime(cf["date_from"].min())
    else:
        date_start = pd.to_datetime(ds)
    date_finish_exp = param["Дата погашения"]
    date_due = eval(date_finish_exp)
    date_due = pd.to_datetime(date_due)
    date_max = pd.to_datetime(cf["date_from"].max())
    date_finish = max((date_due, date_max))

    start_interval = pd.to_datetime(date_start).normalize()
    end_interval = pd.to_datetime(date_finish).normalize()

    days_range = pd.date_range(start=start_interval, end=end_interval, freq="D")

    days_in_year = np.where(days_range.is_leap_year, 366, 365)
    days_in_year = days_in_year

    ds = days_range.to_numpy().copy()

    # Считаем размер массива
    n = len(ds)

    kr = {}

    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT date, key_rate FROM public.macro_keyrate order by date")
        kr = cur.fetchall()

    kr_df = pd.DataFrame(kr)

    kr_df["date"] = pd.to_datetime(kr_df["date"])
    kr_df = kr_df.set_index("date").sort_index()

    keys = kr_df["key_rate"].reindex(days_range, method="ffill")
    key_rate = keys.to_numpy()

    rate = eval(rate_exp)
    if isinstance(rate, float):
        rate = np.full(n, rate)

    penalty_rates = np.full(n, penalty_rate)
    penalty_rates = penalty_rates * days_in_year

    due_idx = np.where(ds == date_due)[0][0] + 1

    if date_due < date_finish:
        rate[due_idx:] = penalty_rates[due_idx:]

    cf["date_from"] = pd.to_datetime(cf["date_from"])
    days_df = pd.DataFrame({"date_from": days_range})
    df = days_df.merge(cf, on="date_from", how="left").fillna(0)
    # теперь считаем все в numpy

    contract_amount = np.full(n, param["Сумма по договору"] * 100.0)

    drawdown_amount = df["dt"].to_numpy(dtype=float)

    repaid_amount = df["cr"].to_numpy(dtype=float)

    bb = np.zeros(n)
    eb = np.zeros(n)
    available_amount = np.zeros(n)

    interest_accrued = np.zeros(n)
    interest_balance = np.zeros(n)
    interest_repayment = np.zeros(n)
    principal_repayment = np.zeros(n)

    drawdown_amount_cum = np.zeros(n)
    principal_repayment_cum = np.zeros(n)

    if param["Профиль погашения"]["Сначало проценты"]:

        for i in range(n):
            prev_eb = 0 if i == 0 else eb[i - 1]
            prev_interest_balance = 0 if i == 0 else interest_balance[i - 1]
            prev_drawdown_cum = 0 if i == 0 else drawdown_amount_cum[i - 1]
            prev_principal_cum = 0 if i == 0 else principal_repayment_cum[i - 1]

            bb[i] = prev_eb

            # движение по телу: сначала выдача
            current_drawdown = drawdown_amount[i]
            drawdown_amount_cum[i] = prev_drawdown_cum + current_drawdown

            # проценты на начало дня
            interest_accrued[i] = bb[i] * (rate[i] / 100 / days_in_year[i])

            due_interest = prev_interest_balance + interest_accrued[i]

            # из платежа сначала гасим проценты
            current_repayment = repaid_amount[i]
            interest_repayment[i] = min(current_repayment, due_interest)

            # остаток платежа идет в тело
            principal_repayment[i] = current_repayment - interest_repayment[i]
            principal_repayment_cum[i] = prev_principal_cum + principal_repayment[i]

            # остаток процентов
            interest_balance[i] = due_interest - interest_repayment[i]

            # остаток тела на конец дня
            if i == due_idx - 1:
                eb[i] = (
                    prev_eb
                    + current_drawdown
                    - principal_repayment[i]
                    + interest_balance[i]
                )
                interest_balance[i] = 0
            else:
                eb[i] = prev_eb + current_drawdown - principal_repayment[i]

            # доступный лимит
            available_amount[i] = max(
                contract_amount[i]
                - drawdown_amount_cum[i]
                + principal_repayment_cum[i],
                0,
            )
    else:

        for i in range(n):
            prev_eb = 0 if i == 0 else eb[i - 1]
            prev_interest_balance = 0 if i == 0 else interest_balance[i - 1]
            prev_drawdown_cum = 0 if i == 0 else drawdown_amount_cum[i - 1]
            prev_principal_cum = 0 if i == 0 else principal_repayment_cum[i - 1]

            bb[i] = prev_eb

            # сначала выдача
            current_drawdown = drawdown_amount[i]
            drawdown_amount_cum[i] = prev_drawdown_cum + current_drawdown

            # проценты на начало дня
            interest_accrued[i] = bb[i] * (rate[i] / 100 / days_in_year[i])
            due_interest = prev_interest_balance + interest_accrued[i]

            current_repayment = repaid_amount[i]

            # сначала гасим тело
            principal_repayment[i] = min(current_repayment, prev_eb + current_drawdown)
            principal_repayment_cum[i] = prev_principal_cum + principal_repayment[i]

            # остаток платежа идет на проценты
            remaining_repayment = current_repayment - principal_repayment[i]
            interest_repayment[i] = min(remaining_repayment, due_interest)

            # остаток процентов

            interest_balance[i] = due_interest - interest_repayment[i]

            # остаток тела на конец дня
            if i == due_idx - 1:
                eb[i] = (
                    prev_eb
                    + current_drawdown
                    - principal_repayment[i]
                    + interest_balance[i]
                )
                interest_balance[i] = 0
            else:
                eb[i] = prev_eb + current_drawdown - principal_repayment[i]

            # доступный лимит
            available_amount[i] = max(
                contract_amount[i]
                - drawdown_amount_cum[i]
                + principal_repayment_cum[i],
                0,
            )

    total_debt = interest_balance + eb

    operation_description = df["description"].to_numpy()
    interest_description = np.array(
        [
            f""" Проценты по займу на сумму {ai/1_00:,.2f}
        ставка {rate}% годовых / {days_in_year} дней * {bb/100:,.2f}
        """
            for ai, rate, days_in_year, bb in zip(
                interest_accrued, rate, days_in_year, bb
            )
        ]
    )

    final = {
        "date_from": ds,
        "contract_id": np.full(n, contract_id, dtype=int),
        "contract_amount": contract_amount,
        "available_amount": available_amount,
        "drawdown_amount": drawdown_amount,
        "bb": bb,
        "rate": rate,
        "interest_accrued": interest_accrued,
        "principal_repayment": principal_repayment,
        "interest_repayment": interest_repayment,
        "repaid_amount": repaid_amount,
        "eb": eb,
        "interest_balance": interest_balance,
        "total_debt": total_debt,
        "operation_description": operation_description,
        "interest_description": interest_description,
    }

    bigint_cols = [
        "contract_amount",
        "available_amount",
        "drawdown_amount",
        "bb",
        "interest_accrued",
        "principal_repayment",
        "interest_repayment",
        "repaid_amount",
        "eb",
        "interest_balance",
        "total_debt",
    ]

    for col in bigint_cols:
        final[col] = np.round(final[col]).astype(np.int64)

    insert_borrowings_tp(conn,final)
    return "good mayby"


def connect_db():
    return psycopg.connect(
        dbname="ts_db",  # DB_NAME
        user="ts_user",  # DB_USER
        password="Dec8108079",  # DB_PASSWORD
        host="127.0.0.1",  # DB_HOST
        port="5433",  # DB_PORT
        connect_timeout=10,
    )


# Загружаем строку для теста
def load_row_for_test(conn, condition_id):
    sql = f"""
        SELECT *
        FROM gl.accurals_args
        WHERE fn_id IS NOT NULL
        AND condition_id = {condition_id}
    """
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(sql)
        return cur.fetchall()


def main():
    conn = connect_db()

    rows = load_row_for_test(conn, 253)

    df = borrowing_third_party(conn, **rows[0])
    df.to_excel("rp.xlsx")

    conn.close()


if __name__ == "__main__":
    main()
