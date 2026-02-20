import os, json, time
import requests
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import text
from conns import ENGINE

# --------------------
# CONFIG
# --------------------
load_dotenv()

TOKEN = os.getenv("WB_TOKEN")
if not TOKEN:
    raise RuntimeError("WB_TOKEN not found in .env")

URL = "https://statistics-api.wildberries.ru/api/v5/supplier/reportDetailByPeriod"
HEADERS = {"Authorization": TOKEN}

DATE_FROM = "2025-11-03T00:00:00"
DATE_TO   = "2025-11-10T23:59:59"
PERIOD    = "weekly"
LIMIT     = 100000

SCHEMA = "wb_raw"
TABLE  = "realization"
STAGE  = f"{TABLE}_stage"

STATE_KEY = f"{TABLE}_rrdid_{DATE_FROM}_{DATE_TO}_{PERIOD}"

# --------------------
# STATE (resume)
# --------------------
def ensure_state_table():
    with ENGINE.begin() as conn:
        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {SCHEMA}.wb_etl_state (
              key text PRIMARY KEY,
              value text NOT NULL,
              updated_at timestamptz NOT NULL DEFAULT now()
            );
        """))

def get_state_rrdid() -> int:
    ensure_state_table()
    with ENGINE.begin() as conn:
        row = conn.execute(
            text(f"SELECT value FROM {SCHEMA}.wb_etl_state WHERE key=:k"),
            {"k": STATE_KEY},
        ).fetchone()
        return int(row[0]) if row else 0

def set_state_rrdid(next_rrdid: int) -> None:
    ensure_state_table()
    with ENGINE.begin() as conn:
        conn.execute(
            text(f"""
                INSERT INTO {SCHEMA}.wb_etl_state(key, value)
                VALUES (:k, :v)
                ON CONFLICT (key) DO UPDATE
                  SET value = EXCLUDED.value,
                      updated_at = now()
            """),
            {"k": STATE_KEY, "v": str(next_rrdid)},
        )

# --------------------
# WB API
# --------------------
def fetch_chunk(rrdid: int) -> list[dict]:
    params = {
        "dateFrom": DATE_FROM,
        "dateTo":   DATE_TO,
        "limit":    LIMIT,
        "rrdid":    rrdid,
        "period":   PERIOD,
    }
    r = requests.get(URL, headers=HEADERS, params=params, timeout=180)
    if r.status_code == 204:
        return []
    if not r.ok:
        raise RuntimeError(f"WB HTTP {r.status_code}: {r.text[:300]}")
    data = r.json()
    if not isinstance(data, list):
        raise RuntimeError(f"Unexpected response type: {type(data)}")
    return data

# --------------------
# DF helpers
# --------------------
def json_stringify_df(df: pd.DataFrame) -> pd.DataFrame:
    for c in df.columns:
        s = df[c]
        if s.map(lambda x: isinstance(x, (dict, list))).any():
            df[c] = s.map(lambda x: json.dumps(x, ensure_ascii=False) if isinstance(x, (dict, list)) else x)
    return df

# --------------------
# DB helpers: schema drift
# --------------------
def table_exists(table: str) -> bool:
    with ENGINE.begin() as conn:
        row = conn.execute(text("""
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = :schema AND table_name = :table
        """), {"schema": SCHEMA, "table": table}).fetchone()
        return bool(row)

def ensure_table_exists_from_df(table: str, df: pd.DataFrame) -> None:
    """Создаёт таблицу, если её нет (только заголовок)."""
    if not table_exists(table):
        df.head(0).to_sql(table, con=ENGINE, schema=SCHEMA, if_exists="replace", index=False)
        print(f"DB: created {SCHEMA}.{table}")

def ensure_columns_for_table(table: str, df: pd.DataFrame) -> None:
    """Добавляет отсутствующие колонки из df (тип TEXT) в указанную таблицу."""
    with ENGINE.begin() as conn:
        existing = conn.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = :schema AND table_name = :table
        """), {"schema": SCHEMA, "table": table}).fetchall()
        existing_cols = {r[0] for r in existing}

        missing = [c for c in df.columns if c not in existing_cols]
        for c in missing:
            conn.execute(text(f'ALTER TABLE "{SCHEMA}"."{table}" ADD COLUMN "{c}" TEXT'))
            print(f"DB: added column {table}.{c} (TEXT)")

# --------------------
# STAGING LOAD + MERGE
# --------------------
def load_via_stage(df: pd.DataFrame) -> None:
    """
    1) гарантируем main+stage таблицы
    2) добавляем новые колонки в обе
    3) грузим df в stage
    4) INSERT INTO main ... SELECT ... FROM stage ON CONFLICT (rrd_id) DO NOTHING
    5) TRUNCATE stage
    """

    # ensure tables
    ensure_table_exists_from_df(TABLE, df)
    ensure_table_exists_from_df(STAGE, df)

    # ensure columns in both
    ensure_columns_for_table(TABLE, df)
    ensure_columns_for_table(STAGE, df)

    # load into stage
    df.to_sql(
        STAGE,
        con=ENGINE,
        schema=SCHEMA,
        if_exists="append",
        index=False,
        chunksize=5000,
        method=None,
    )

    cols = list(df.columns)
    col_list = ", ".join([f'"{c}"' for c in cols])

    with ENGINE.begin() as conn:
        conn.execute(text(f"""
            INSERT INTO "{SCHEMA}"."{TABLE}" ({col_list})
            SELECT {col_list}
            FROM "{SCHEMA}"."{STAGE}"
            ON CONFLICT (rrd_id) DO NOTHING;
        """))
        conn.execute(text(f'TRUNCATE TABLE "{SCHEMA}"."{STAGE}";'))

# --------------------
# MAIN
# --------------------
def main():
    rrdid = get_state_rrdid()
    print("Start rrdid:", rrdid)

    while True:
        chunk = fetch_chunk(rrdid)
        if not chunk:
            print("DONE (204).")
            break

        df = pd.DataFrame(chunk)
        if df.empty:
            print("DONE (empty chunk).")
            break

        df = json_stringify_df(df)

        if "rrd_id" not in df.columns:
            raise RuntimeError("No rrd_id column in response; cannot continue paging.")

        # грузим без падений на дублях
        # грузим без падений на дублях
        load_via_stage(df)

        # курсор берём так:
        rrd_series = pd.to_numeric(df["rrd_id"], errors="coerce")
        last_rrd = int(rrd_series.iloc[-1])
        next_rrdid = last_rrd

        # антизацикливание
        if next_rrdid == rrdid:
            next_rrdid = rrdid + 1
            print("WARN: cursor stuck, forced +1")

        # сохраняем и продолжаем
        rrdid = next_rrdid
        set_state_rrdid(rrdid)

        print(f"Fetched {len(df)} rows; last_rrd={last_rrd}; next_rrdid={rrdid}")
        time.sleep(60)

if __name__ == "__main__":
    main()