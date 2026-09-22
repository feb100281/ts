# utils/wbapi/cards.py
import os
import json
import time
import random
import requests
from dotenv import load_dotenv
from sqlalchemy import text

from conns import ENGINE

load_dotenv()

WB_TOKEN = os.getenv("WB_TOKEN")
if not WB_TOKEN:
    raise RuntimeError("WB_TOKEN not found in .env")

URL = "https://content-api.wildberries.ru/content/v2/get/cards/list"
HEADERS = {
    "Authorization": WB_TOKEN,
    "Content-Type": "application/json",
}

SCHEMA = "wb_raw"
TABLE = "raw_cards"

LIMIT = 100  # WB max 100

# базовые задержки (WB легко банит)
BASE_SLEEP = 0.30
JITTER = 0.15

# 429/backoff
MAX_RETRIES = 12
BACKOFF_BASE = 1.7
BACKOFF_CAP = 120  # сек


def ensure_table():
    with ENGINE.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{SCHEMA}";'))
        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS "{SCHEMA}"."{TABLE}" (
                nm_id       BIGINT PRIMARY KEY,
                payload_raw JSONB NOT NULL,
                loaded_at   TIMESTAMPTZ NOT NULL DEFAULT now()
            );
        """))


def upsert_raw_cards(cards: list[dict]) -> int:
    if not cards:
        return 0

    params = []
    for c in cards:
        nm_id = c.get("nmID")
        if nm_id is None:
            continue
        params.append({
            "nm_id": int(nm_id),
            "payload_raw": json.dumps(c, ensure_ascii=False),
        })

    if not params:
        return 0

    stmt = text(f"""
        INSERT INTO "{SCHEMA}"."{TABLE}" (nm_id, payload_raw, loaded_at)
        VALUES (:nm_id, CAST(:payload_raw AS jsonb), now())
        ON CONFLICT (nm_id) DO UPDATE
          SET payload_raw = EXCLUDED.payload_raw,
              loaded_at   = now();
    """)

    with ENGINE.begin() as conn:
        # 1) диагностика куда мы вообще подключились
        info = conn.execute(text("""
            select current_database() as db,
                   current_user as usr,
                   inet_server_addr()::text as host,
                   current_schema() as schema,
                   current_setting('search_path') as search_path
        """)).mappings().one()
        print("DB INFO:", dict(info))

        # 2) выполняем upsert
        conn.execute(stmt, params)

        # 3) железная проверка: сколько строк в ТОМ ЖЕ месте
        cnt = conn.execute(text(f'SELECT count(*) FROM "{SCHEMA}"."{TABLE}"')).scalar_one()
        print(f"CHECK COUNT {SCHEMA}.{TABLE} =", cnt)

        # 4) ещё проверка по последним nm_id (чтобы не “считает”, а строк нет)
        last_ids = [p["nm_id"] for p in params[-5:]]
        exists = conn.execute(
            text(f'SELECT nm_id FROM "{SCHEMA}"."{TABLE}" WHERE nm_id = ANY(:ids) ORDER BY nm_id'),
            {"ids": last_ids},
        ).fetchall()
        print("CHECK EXISTS last5:", [r[0] for r in exists])

    return len(params)


def post_with_retry(payload: dict) -> dict:
    """
    Делает POST и переживает 429/5xx.
    """
    for attempt in range(MAX_RETRIES):
        r = requests.post(URL, headers=HEADERS, json=payload, timeout=120)

        # OK
        if r.status_code == 200:
            return r.json()

        # Too Many Requests
        if r.status_code == 429:
            retry_after = r.headers.get("Retry-After")
            if retry_after:
                try:
                    wait = float(retry_after)
                except Exception:
                    wait = None
            else:
                wait = None

            if wait is None:
                wait = min(BACKOFF_CAP, (BACKOFF_BASE ** attempt)) + random.random()

            print(f"WB 429 Too Many Requests -> sleep {wait:.1f}s")
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


def fetch_page(cursor_updated_at=None, cursor_nm_id=None) -> tuple[list[dict], dict]:
    """
    Возвращает (cards, cursor_from_response)
    cursor_from_response = {"updatedAt": "...", "nmID": ..., "total": ...}
    """
    cursor = {"limit": LIMIT}
    if cursor_updated_at and cursor_nm_id is not None:
        cursor["updatedAt"] = cursor_updated_at
        cursor["nmID"] = int(cursor_nm_id)

    payload = {
        "settings": {
            "sort": {"ascending": True},          # критично!
            "cursor": cursor,
            "filter": {"withPhoto": -1},          # "все карточки"
        }
    }

    j = post_with_retry(payload)
    cards = j.get("cards") or []
    cur = j.get("cursor") or {}
    return cards, cur


def main():
    ensure_table()

    total_saved = 0
    page = 0

    # старт без курсора
    cursor_updated_at = None
    cursor_nm_id = None

    # защита от зацикливания: запоминаем последнюю пару cursor
    last_cursor_pair = None
    stuck_count = 0

    while True:
        cards, cur = fetch_page(cursor_updated_at, cursor_nm_id)
        page += 1

        # unique nmIDs в странице
        got_ids = [c.get("nmID") for c in cards if c.get("nmID") is not None]
        uniq_got = len(set(got_ids))
        saved = upsert_raw_cards(cards)
        total_saved += saved

        print(f"[{page}] got={len(cards)} uniq_nm={uniq_got} saved={saved} total_saved={total_saved} cursor={cur}")

        # условие окончания по документации:
        # total < limit => последняя страница
        total_in_cursor = cur.get("total")
        if isinstance(total_in_cursor, int) and total_in_cursor < LIMIT:
            print("DONE (cursor.total < limit)")
            break

        # берём курсор для следующей страницы
        next_updated_at = cur.get("updatedAt")
        next_nm_id = cur.get("nmID")

        if not next_updated_at or next_nm_id is None:
            print("DONE (no cursor fields in response)")
            break

        pair = (next_updated_at, int(next_nm_id))

        # детект зацикливания
        if pair == last_cursor_pair:
            stuck_count += 1
            print(f"WARNING: cursor not moving (stuck={stuck_count})")
            if stuck_count >= 3:
                raise RuntimeError("Cursor is stuck (same updatedAt/nmID повторяется) — WB возвращает одно и то же")
        else:
            stuck_count = 0
        last_cursor_pair = pair

        cursor_updated_at, cursor_nm_id = pair

        # базовая пауза + джиттер
        time.sleep(BASE_SLEEP + random.random() * JITTER)

    print("FINISHED")


if __name__ == "__main__":
    main()