import os, json, time
import requests
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

# !!! Поменял старт на 2024-01-01
DATE_FROM = "2026-02-21T00:00:00"

# Можно оставить как у тебя, или поставить "now" руками.
# Чтобы было стабильно и воспроизводимо - фиксируем.
DATE_TO   = "2026-02-23T23:59:59"

PERIOD    = "daily"
LIMIT     = 100000

SCHEMA = "wb_raw"
TABLE  = "realization_raw_w"   # <-- можно назвать realization, но лучше не пересекать со старой "ломаной" таблицей

STATE_KEY = f"{TABLE}_rrdid_{DATE_FROM}_{DATE_TO}_{PERIOD}"

SLEEP_SEC = 60
TIMEOUT_SEC = 180

# --------------------
# STATE (resume)
# --------------------
def ensure_state_table():
    with ENGINE.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{SCHEMA}";'))
        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS "{SCHEMA}"."wb_etl_state" (
              key text PRIMARY KEY,
              value text NOT NULL,
              updated_at timestamptz NOT NULL DEFAULT now()
            );
        """))

def get_state_rrdid() -> int:
    ensure_state_table()
    with ENGINE.begin() as conn:
        row = conn.execute(
            text(f'SELECT value FROM "{SCHEMA}"."wb_etl_state" WHERE key=:k'),
            {"k": STATE_KEY},
        ).fetchone()
        return int(row[0]) if row else 0

def set_state_rrdid(next_rrdid: int) -> None:
    ensure_state_table()
    with ENGINE.begin() as conn:
        conn.execute(
            text(f"""
                INSERT INTO "{SCHEMA}"."wb_etl_state"(key, value)
                VALUES (:k, :v)
                ON CONFLICT (key) DO UPDATE
                  SET value = EXCLUDED.value,
                      updated_at = now()
            """),
            {"k": STATE_KEY, "v": str(next_rrdid)},
        )

# --------------------
# DB: raw table
# --------------------
def ensure_raw_table():
    with ENGINE.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{SCHEMA}";'))
        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS "{SCHEMA}"."{TABLE}" (
              rrd_id   BIGINT PRIMARY KEY,
              row_json JSONB  NOT NULL,
              loaded_at timestamptz NOT NULL DEFAULT now()
            );
        """))
        # полезно для поисков по json
        # conn.execute(text(f'CREATE INDEX IF NOT EXISTS "{TABLE}_row_json_gin" ON "{SCHEMA}"."{TABLE}" USING GIN (row_json);'))

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
    r = requests.get(URL, headers=HEADERS, params=params, timeout=TIMEOUT_SEC)
    if r.status_code == 204:
        return []
    if not r.ok:
        raise RuntimeError(f"WB HTTP {r.status_code}: {r.text[:300]}")
    data = r.json()
    if not isinstance(data, list):
        raise RuntimeError(f"Unexpected response type: {type(data)}")
    return data

# --------------------
# LOAD: insert raw jsonb
# --------------------
INSERT_SQL = text(f"""
    INSERT INTO "{SCHEMA}"."{TABLE}" (rrd_id, row_json)
    VALUES (:rrd_id, CAST(:row_json AS JSONB))
    ON CONFLICT (rrd_id) DO NOTHING;
""")

def load_raw(rows: list[dict]) -> int:
    """
    Пишем батчем executemany:
      rrd_id BIGINT
      row_json JSONB (сырой obj)
    """
    payload = []
    skipped = 0

    for obj in rows:
        rrd = obj.get("rrd_id")
        if rrd is None:
            skipped += 1
            continue
        payload.append({
            "rrd_id": int(rrd),
            "row_json": json.dumps(obj, ensure_ascii=False),
        })

    if not payload:
        if skipped:
            print(f"WARN: skipped {skipped} rows without rrd_id")
        return 0

    with ENGINE.begin() as conn:
        conn.execute(INSERT_SQL, payload)

    if skipped:
        print(f"WARN: skipped {skipped} rows without rrd_id")

    return len(payload)

def get_next_rrdid(rows: list[dict], current_rrdid: int) -> tuple[int, int]:
    """
    Возвращает (last_rrd, next_rrdid) по max(rrd_id) в чанке.
    Так надёжнее, чем "последний элемент".
    """
    rrd_ids = [int(x["rrd_id"]) for x in rows if x.get("rrd_id") is not None]
    if not rrd_ids:
        raise RuntimeError("Chunk has no rrd_id values; cannot continue paging.")

    last_rrd = max(rrd_ids)
    next_rrdid = last_rrd

    # антизацикливание (если API вернуло тот же максимум)
    if next_rrdid == current_rrdid:
        next_rrdid = current_rrdid + 1
        print("WARN: cursor stuck, forced +1")

    return last_rrd, next_rrdid

# --------------------
# MAIN
# --------------------
def main():
    ensure_raw_table()

    rrdid = get_state_rrdid()
    print("Start rrdid:", rrdid)
    print("STATE_KEY:", STATE_KEY)

    while True:
        chunk = fetch_chunk(rrdid)
        if not chunk:
            print("DONE (204).")
            break

        inserted = load_raw(chunk)
        last_rrd, next_rrdid = get_next_rrdid(chunk, rrdid)

        # сохраняем курсор и продолжаем
        rrdid = next_rrdid
        set_state_rrdid(rrdid)

        print(f"Fetched {len(chunk)} rows; inserted={inserted}; last_rrd={last_rrd}; next_rrdid={rrdid}")
        time.sleep(SLEEP_SEC)

if __name__ == "__main__":
    main()