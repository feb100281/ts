#!/usr/bin/env python3
import os
import json
import time
from datetime import datetime, timedelta, timezone

import requests
import psycopg

# --------------------
# WB CONFIG
# --------------------
URL = "https://statistics-api.wildberries.ru/api/v5/supplier/reportDetailByPeriod"
PERIOD = "daily"
LIMIT = 100000

TIMEOUT_SEC = 180
SLEEP_SEC = 1
MAX_RETRIES = 10

# WB expects Moscow timezone in request params
MSK = timezone(timedelta(hours=3))

# --------------------
# DB CONFIG
# --------------------
SCHEMA = "wb_raw"
TABLE = "temp_realization"

STATE_KEY_LAST_TO = f"{TABLE}_last_success_to_{PERIOD}"  # watermark: last successful DATE_TO (MSK)


# --------------------
# Helpers
# --------------------
def get_env(name: str) -> str:
    v = os.getenv(name)
    if not v:
        raise RuntimeError(f"{name} is not set")
    return v


def iso_msk(dt: datetime) -> str:
    return dt.astimezone(MSK).replace(microsecond=0).isoformat()


def connect_db():
    return psycopg.connect(
        dbname=get_env("DB_NAME"),
        user=get_env("DB_USER"),
        password=get_env("DB_PASSWORD"),
        host=get_env("DB_HOST"),
        port=get_env("DB_PORT"),
        connect_timeout=10,
    )


# --------------------
# State table
# --------------------
def ensure_state_table(conn):
    with conn.cursor() as cur:
        cur.execute(f'CREATE SCHEMA IF NOT EXISTS "{SCHEMA}";')
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS "{SCHEMA}"."wb_etl_state" (
              key text PRIMARY KEY,
              value text NOT NULL,
              updated_at timestamptz NOT NULL DEFAULT now()
            );
        """)
    conn.commit()


def set_state_last_to(conn, dt_msk: datetime) -> None:
    ensure_state_table(conn)
    with conn.cursor() as cur:
        cur.execute(
            f"""
            INSERT INTO "{SCHEMA}"."wb_etl_state"(key, value)
            VALUES (%s, %s)
            ON CONFLICT (key) DO UPDATE
              SET value = EXCLUDED.value,
                  updated_at = now()
            """,
            (STATE_KEY_LAST_TO, iso_msk(dt_msk)),
        )
    conn.commit()


def get_date_from_by_state_updated_at(conn) -> datetime:
    """
    Берём max(updated_at) из wb_raw.wb_etl_state по ключам temp_realization%
    и отнимаем 2 дня (фора).
    Если записей нет — now(MSK) - 2 days.
    """
    ensure_state_table(conn)
    with conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT max(updated_at)
            FROM "{SCHEMA}"."wb_etl_state"
            WHERE key LIKE %s
            """,
            (f"{TABLE}%",),
        )
        mx = cur.fetchone()[0]  # aware dt or None

    now_msk = datetime.now(timezone.utc).astimezone(MSK)
    if mx is None:
        return now_msk - timedelta(days=2)

    return mx.astimezone(MSK) - timedelta(days=2)


# --------------------
# Raw table
# --------------------
def ensure_raw_table(conn):
    with conn.cursor() as cur:
        cur.execute(f'CREATE SCHEMA IF NOT EXISTS "{SCHEMA}";')
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS "{SCHEMA}"."{TABLE}" (
              rrd_id    BIGINT PRIMARY KEY,
              row_json  JSONB  NOT NULL,
              loaded_at timestamptz NOT NULL DEFAULT now()
            );
        """)
    conn.commit()


def truncate_raw_table(conn):
    with conn.cursor() as cur:
        cur.execute(f'TRUNCATE TABLE "{SCHEMA}"."{TABLE}";')
    conn.commit()


# --------------------
# WB API
# --------------------
def wb_get_with_retry(headers: dict, params: dict) -> list[dict]:
    for attempt in range(MAX_RETRIES):
        r = requests.get(URL, headers=headers, params=params, timeout=TIMEOUT_SEC)

        if r.status_code == 204:
            return []

        if r.status_code == 200:
            data = r.json()
            if not isinstance(data, list):
                raise RuntimeError(f"Unexpected response type: {type(data)}")
            return data

        if r.status_code == 429 or (500 <= r.status_code < 600):
            wait = min(120, (1.7 ** attempt))
            print(f"WB {r.status_code} -> sleep {wait:.1f}s")
            time.sleep(wait)
            continue

        raise RuntimeError(f"WB HTTP {r.status_code}: {r.text[:800]}")

    raise RuntimeError("WB retries exceeded")


def fetch_chunk(headers: dict, date_from: str, date_to: str, rrdid: int) -> list[dict]:
    params = {
        "dateFrom": date_from,
        "dateTo": date_to,
        "limit": LIMIT,
        "rrdid": rrdid,
        "period": PERIOD,
    }
    return wb_get_with_retry(headers, params)


# --------------------
# Insert raw
# --------------------
def insert_raw(conn, rows: list[dict]) -> int:
    payload = []
    skipped = 0

    for obj in rows:
        rrd = obj.get("rrd_id")
        if rrd is None:
            skipped += 1
            continue
        payload.append((int(rrd), json.dumps(obj, ensure_ascii=False)))

    if not payload:
        if skipped:
            print(f"WARN: skipped {skipped} rows without rrd_id")
        return 0

    sql = f"""
        INSERT INTO "{SCHEMA}"."{TABLE}" (rrd_id, row_json)
        VALUES (%s, %s::jsonb)
        ON CONFLICT (rrd_id) DO NOTHING;
    """
    with conn.cursor() as cur:
        cur.executemany(sql, payload)
    conn.commit()

    if skipped:
        print(f"WARN: skipped {skipped} rows without rrd_id")

    return len(payload)


def next_rrdid(rows: list[dict], current: int) -> int:
    rrd_ids = [int(x["rrd_id"]) for x in rows if x.get("rrd_id") is not None]
    if not rrd_ids:
        raise RuntimeError("Chunk has no rrd_id values; cannot continue paging.")
    last_rrd = max(rrd_ids)
    nxt = last_rrd
    if nxt == current:
        nxt = current + 1
        print("WARN: cursor stuck, forced +1")
    return nxt


# --------------------
# MAIN
# --------------------
def main():
    token = get_env("WB_TOKEN")
    headers = {"Authorization": token}

    conn = connect_db()
    try:
        ensure_raw_table(conn)

        date_to_msk = datetime.now(timezone.utc).astimezone(MSK)
        date_from_msk = get_date_from_by_state_updated_at(conn)

        DATE_FROM = iso_msk(date_from_msk)
        DATE_TO = iso_msk(date_to_msk)

        print("WINDOW:", DATE_FROM, "->", DATE_TO)
        print("STATE_KEY:", STATE_KEY_LAST_TO)

        # 1) staging: чистим и грузим заново
        truncate_raw_table(conn)

        # 2) paging by rrdid
        rrdid = 0
        total_inserted = 0
        page = 0

        while True:
            chunk = fetch_chunk(headers, DATE_FROM, DATE_TO, rrdid)
            if not chunk:
                print("DONE (204/empty).")
                break

            page += 1
            inserted = insert_raw(conn, chunk)
            total_inserted += inserted

            rrdid = next_rrdid(chunk, rrdid)
            print(f"[{page}] got={len(chunk)} inserted={inserted} total={total_inserted} next_rrdid={rrdid}")

            time.sleep(SLEEP_SEC)

        # 3) watermark: фиксируем успешный DATE_TO (в МСК)
        set_state_last_to(conn, date_to_msk)

        # 4) transform
        with conn.cursor() as cur:
            cur.execute("CALL wb_dwh.load_realization_kv_from_temp();")
        conn.commit()

        print("FINISHED OK")

    finally:
        conn.close()


if __name__ == "__main__":
    main()