#!/usr/bin/env python3
import os
import json
import time
import random
import requests
import psycopg

URL = "https://content-api.wildberries.ru/content/v2/get/cards/list"

SCHEMA = "wb_raw"
TABLE = "raw_cards"

LIMIT = 100  # WB max 100

# базовые задержки (WB легко банит)
BASE_SLEEP = 0.30
JITTER = 0.15

# retry/backoff для 429/5xx
MAX_RETRIES = 12
BACKOFF_BASE = 1.7
BACKOFF_CAP = 120  # секунд


def get_env(name: str) -> str:
    v = os.getenv(name)
    if not v:
        raise RuntimeError(f"{name} is not set")
    return v


def db_connect():
    return psycopg.connect(
        dbname=get_env("DB_NAME"),
        user=get_env("DB_USER"),
        password=get_env("DB_PASSWORD"),
        host=get_env("DB_HOST"),
        port=get_env("DB_PORT"),
        connect_timeout=10,
    )


def ensure_table(conn):
    with conn.cursor() as cur:
        cur.execute(f'CREATE SCHEMA IF NOT EXISTS "{SCHEMA}";')
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS "{SCHEMA}"."{TABLE}" (
                nm_id       BIGINT PRIMARY KEY,
                payload_raw JSONB NOT NULL,
                loaded_at   TIMESTAMPTZ NOT NULL DEFAULT now()
            );
        """)
    conn.commit()


def upsert_cards(conn, cards: list[dict]) -> int:
    rows = []
    for c in cards:
        nm_id = c.get("nmID")
        if nm_id is None:
            continue
        rows.append((int(nm_id), json.dumps(c, ensure_ascii=False)))

    if not rows:
        return 0

    sql = f"""
        INSERT INTO "{SCHEMA}"."{TABLE}" (nm_id, payload_raw, loaded_at)
        VALUES (%s, %s::jsonb, now())
        ON CONFLICT (nm_id) DO UPDATE
          SET payload_raw = EXCLUDED.payload_raw,
              loaded_at   = now()
    WHERE "raw_cards".payload_raw IS DISTINCT FROM EXCLUDED.payload_raw;
    """

    with conn.cursor() as cur:
        cur.executemany(sql, rows)
    conn.commit()
    return len(rows)


def post_with_retry(headers: dict, payload: dict) -> dict:
    for attempt in range(MAX_RETRIES):
        r = requests.post(URL, headers=headers, json=payload, timeout=120)

        if r.status_code == 200:
            return r.json()

        # 429 Too Many Requests
        if r.status_code == 429:
            retry_after = r.headers.get("Retry-After")
            wait = None
            if retry_after:
                try:
                    wait = float(retry_after)
                except Exception:
                    wait = None
            if wait is None:
                wait = min(BACKOFF_CAP, (BACKOFF_BASE ** attempt)) + random.random()
            print(f"WB 429 -> sleep {wait:.1f}s")
            time.sleep(wait)
            continue

        # transient 5xx
        if 500 <= r.status_code < 600:
            wait = min(BACKOFF_CAP, (BACKOFF_BASE ** attempt)) + random.random()
            print(f"WB {r.status_code} -> sleep {wait:.1f}s")
            time.sleep(wait)
            continue

        # other errors -> fail fast
        raise RuntimeError(f"WB HTTP {r.status_code}: {r.text[:800]}")

    raise RuntimeError("WB: retries exceeded (429/5xx)")


def fetch_page(headers: dict, cursor_updated_at=None, cursor_nm_id=None) -> tuple[list[dict], dict]:
    cursor = {"limit": LIMIT}
    if cursor_updated_at and cursor_nm_id is not None:
        cursor["updatedAt"] = cursor_updated_at
        cursor["nmID"] = int(cursor_nm_id)

    payload = {
        "settings": {
            "sort": {"ascending": True},
            "cursor": cursor,
            "filter": {"withPhoto": -1},
        }
    }

    j = post_with_retry(headers, payload)
    cards = j.get("cards") or []
    cur = j.get("cursor") or {}
    return cards, cur


def upsert_sizes(conn):
    q = """
        WITH a AS (
        SELECT
        (t.payload_raw ->> 'nmID')::bigint AS nm_id,
        s.value ->> 'wbSize' AS "wbSize",
        s.value ->> 'techSize' AS "techSize"
        FROM wb_raw.raw_cards t
        CROSS JOIN LATERAL jsonb_array_elements(t.payload_raw -> 'sizes') AS s(value)
        CROSS JOIN LATERAL jsonb_array_elements_text(s.value -> 'skus') AS sku(value)
        )
        INSERT INTO public.wb_techsize (size)
        SELECT DISTINCT "techSize"
        FROM a
        WHERE "techSize" IS NOT NULL
        ON CONFLICT (size) DO NOTHING;

        """
    with conn.cursor() as cur:
        cur.execute(q)
    conn.commit()

def upsert_nms_sizes(conn):
    q = """
    WITH a AS (
    SELECT
        (t.payload_raw ->> 'nmID')::bigint AS nm_id,
        s.value ->> 'wbSize' AS "wbSize",
        s.value ->> 'techSize' AS "techSize"
    FROM wb_raw.raw_cards t
    CROSS JOIN LATERAL jsonb_array_elements(t.payload_raw -> 'sizes') AS s(value)
    CROSS JOIN LATERAL jsonb_array_elements_text(s.value -> 'skus') AS sku(value)
    )
    INSERT INTO public.wb_product_tech_sizes (product_id, techsize_id)
    SELECT DISTINCT nm_id, "techSize"
    FROM a
    WHERE "techSize" IS NOT NULL and nm_id is not null
    ON CONFLICT (product_id, techsize_id) DO NOTHING;


    """
    with conn.cursor() as cur:
        cur.execute(q)
    conn.commit()

        






def main():
    token = get_env("WB_TOKEN")
    headers = {"Authorization": token, "Content-Type": "application/json"}

    conn = db_connect()
    try:
        ensure_table(conn)

        total_saved = 0
        page = 0

        cursor_updated_at = None
        cursor_nm_id = None

        last_pair = None
        stuck_count = 0

        while True:
            cards, cur = fetch_page(headers, cursor_updated_at, cursor_nm_id)
            page += 1

            got_ids = [c.get("nmID") for c in cards if c.get("nmID") is not None]
            uniq_nm = len(set(got_ids))

            saved = upsert_cards(conn, cards)
            total_saved += saved

            print(f"[{page}] got={len(cards)} uniq_nm={uniq_nm} saved={saved} total_saved={total_saved} cursor={cur}")

            total_in_cursor = cur.get("total")
            if isinstance(total_in_cursor, int) and total_in_cursor < LIMIT:
                print("DONE (cursor.total < limit)")
                break

            next_updated_at = cur.get("updatedAt")
            next_nm_id = cur.get("nmID")

            if not next_updated_at or next_nm_id is None:
                print("DONE (no cursor fields in response)")
                break

            pair = (next_updated_at, int(next_nm_id))

            if pair == last_pair:
                stuck_count += 1
                print(f"WARNING: cursor not moving (stuck={stuck_count})")
                if stuck_count >= 3:
                    raise RuntimeError("Cursor is stuck (same updatedAt/nmID repeats)")
            else:
                stuck_count = 0

            last_pair = pair
            cursor_updated_at, cursor_nm_id = pair

            time.sleep(BASE_SLEEP + random.random() * JITTER)

        print("FINISHED OK")

        with conn.cursor() as cur:
            cur.execute("SELECT wb_raw.sync_raw_cards_to_product();")
            synced = cur.fetchone()[0]
            print(f"SYNC OK: {synced} rows upserted into wb_product")

        conn.commit()
        upsert_sizes(conn)
        upsert_nms_sizes(conn)


    finally:
        conn.close()


if __name__ == "__main__":
    main()
