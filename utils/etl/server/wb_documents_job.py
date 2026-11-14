import os
import time
import requests
import psycopg
from datetime import datetime, timezone, timedelta
from dateutil.relativedelta import relativedelta

URL = "https://documents-api.wildberries.ru/api/v1/documents/list"

UPSERT_SQL = """
INSERT INTO wb_raw.wb_documents
    (service_name, category, name, creation_time, extensions, viewed, fetched_at)
VALUES
    (%s, %s, %s, %s, %s, %s, NOW())
ON CONFLICT (service_name, name, creation_time)
DO UPDATE SET
    category   = EXCLUDED.category,
    extensions = EXCLUDED.extensions,
    viewed     = EXCLUDED.viewed,
    fetched_at = NOW();
"""


# --- helpers

def ext_to_str(ext):
    if not ext:
        return ""
    if isinstance(ext, list):
        return ",".join(str(x) for x in ext if x is not None)
    return str(ext)


def daterange(start, end):
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)


# --- API

def fetch_page(token, begin_date, end_date, limit, offset, attempt=0):
    params = {
        "locale": "ru",
        "beginTime": begin_date,
        "endTime": end_date,
        "limit": limit,
        "offset": offset,
        "sort": "date",
        "order": "asc",
    }

    r = requests.get(
        URL,
        headers={"Authorization": token},
        params=params,
        timeout=60,
    )

    # 🔥 429
    if r.status_code == 429:
        retry = r.headers.get("Retry-After")
        wait = int(retry) if retry and retry.isdigit() else min(30 * (attempt + 1), 300)

        print(f"WB 429 → sleep {wait}s (attempt={attempt})")

        if attempt >= 10:
            print("SKIP page (too many retries)")
            return []

        time.sleep(wait)
        return fetch_page(token, begin_date, end_date, limit, offset, attempt + 1)

    # 🔥 5xx
    if 500 <= r.status_code < 600:
        wait = min(10 * (attempt + 1), 60)
        print(f"WB {r.status_code} → sleep {wait}s")

        time.sleep(wait)
        return fetch_page(token, begin_date, end_date, limit, offset, attempt + 1)

    # другие ошибки
    if r.status_code != 200:
        raise RuntimeError(f"WB HTTP {r.status_code}: {r.text[:300]}")

    payload = r.json()
    return (payload.get("data") or {}).get("documents") or []


# --- main

def main():
    token = os.getenv("WB_TOKEN")
    if not token:
        raise RuntimeError("WB_TOKEN not set")

    limit = 50
    sleep_seconds = 11  # базовая задержка

    # диапазон: последний месяц
    end = datetime.now(timezone.utc).date()
    start = end - relativedelta(months=1)

    print(f"WB documents range: {start} -> {end}")

    conn = psycopg.connect(
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
    )

    total_processed = 0

    with conn:
        with conn.cursor() as cur:
            cur.execute("SET search_path TO wb_raw, public;")

            for day in daterange(start, end):
                begin_date = day.isoformat()
                end_date = day.isoformat()

                print(f"\n=== DAY {begin_date} ===")

                offset = 0

                while True:
                    docs = fetch_page(token, begin_date, end_date, limit, offset)

                    if not docs:
                        break

                    rows = [
                        (
                            d.get("serviceName"),
                            d.get("category"),
                            d.get("name"),
                            d.get("creationTime"),
                            ext_to_str(d.get("extensions")),
                            bool(d.get("viewed", False)),
                        )
                        for d in docs
                    ]

                    cur.executemany(UPSERT_SQL, rows)

                    total_processed += len(rows)

                    print(f"Fetched {len(rows)} offset={offset}")

                    offset += limit
                    time.sleep(sleep_seconds)

    print(f"\nDONE total_processed={total_processed}")


if __name__ == "__main__":
    main()
