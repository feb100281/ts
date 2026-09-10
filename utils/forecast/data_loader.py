# utils/forecast/data_loader.py
import pandas as pd
from psycopg.rows import dict_row


def get_last_actual_date(conn, start_date=None):
    if start_date is None:
        sql = """
        SELECT MAX(date_from) AS last_actual_date
        FROM gl.fact
        WHERE acc_id = 46
          AND subconto_id IN (52, 87)
        """
        params = ()
    else:
        sql = """
        SELECT MAX(date_from) AS last_actual_date
        FROM gl.fact
        WHERE acc_id = 46
          AND subconto_id IN (52, 87)
          AND date_from >= %s
        """
        params = (start_date,)

    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(sql, params)
        row = cur.fetchone()

    if not row or row["last_actual_date"] is None:
        raise ValueError("В базе не найдена последняя дата факта")

    return pd.to_datetime(row["last_actual_date"])


def get_revenue_data(conn, start_date, end_date, fill_missing_dates=True):
    sql = """
    SELECT
        date_from AS ds,
        SUM(dt - cr) AS y
    FROM gl.fact
    WHERE acc_id = 46
      AND subconto_id IN (52, 87)
      AND date_from >= %s
      AND date_from <= %s
    GROUP BY date_from
    ORDER BY 1
    """

    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(sql, (start_date, end_date))
        rows = cur.fetchall()

    df = pd.DataFrame(rows)

    if df.empty:
        return df

    df["ds"] = pd.to_datetime(df["ds"])
    df["y"] = (pd.to_numeric(df["y"], errors="coerce") / 100).round(2)
    df = df.dropna(subset=["ds", "y"]).sort_values("ds")

    if fill_missing_dates:
        full_range = pd.date_range(df["ds"].min(), df["ds"].max(), freq="D")
        df = (
            df.set_index("ds")
            .reindex(full_range)
            .rename_axis("ds")
            .reset_index()
        )
        df["y"] = df["y"].fillna(0)

    return df