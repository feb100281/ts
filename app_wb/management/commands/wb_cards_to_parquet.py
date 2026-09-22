import os
import json
import time
import random
from pathlib import Path
from datetime import datetime, timezone

import requests
import pandas as pd

from django.core.management.base import BaseCommand, CommandError


URL = "https://content-api.wildberries.ru/content/v2/get/cards/list"

LIMIT = 100

BASE_SLEEP = 0.3
JITTER = 0.15

MAX_RETRIES = 12
BACKOFF_BASE = 1.7
BACKOFF_CAP = 120


class Command(BaseCommand):
    help = "Download WB cards to parquet (raw payload)"

    def add_arguments(self, parser):
        parser.add_argument("--overwrite", action="store_true")

    def handle(self, *args, **options):
        token = os.getenv("WB_TOKEN")
        if not token:
            raise CommandError("WB_TOKEN is not set")

        base_path = os.getenv("PARQUET_PATH")
        if not base_path:
            raise CommandError("PARQUET_PATH is not set")

        output_dir = Path(base_path) / "cards"
        output_dir.mkdir(parents=True, exist_ok=True)

        output_path = output_dir / "cards.parquet"

        if output_path.exists() and not options["overwrite"]:
            self.stdout.write(f"SKIP exists: {output_path}")
            return

        self.stdout.write(f"OUTPUT: {output_path}")

        headers = {
            "Authorization": token,
            "Content-Type": "application/json",
        }

        rows = []
        page = 0

        cursor_updated_at = None
        cursor_nm_id = None

        last_pair = None
        stuck_count = 0

        while True:
            chunk, cur = self.fetch_page(headers, cursor_updated_at, cursor_nm_id)
            page += 1

            if not chunk:
                self.stdout.write("DONE empty response")
                break

            rows.extend(chunk)

            self.save_parquet(rows, output_path)

            got_ids = [c.get("nmID") for c in chunk if c.get("nmID")]
            uniq_nm = len(set(got_ids))

            self.stdout.write(
                f"[{page}] got={len(chunk)} uniq_nm={uniq_nm} total={len(rows)}"
            )

            total_in_cursor = cur.get("total")
            if isinstance(total_in_cursor, int) and total_in_cursor < LIMIT:
                self.stdout.write("DONE (cursor.total < limit)")
                break

            next_updated_at = cur.get("updatedAt")
            next_nm_id = cur.get("nmID")

            if not next_updated_at or next_nm_id is None:
                self.stdout.write("DONE (no cursor)")
                break

            pair = (next_updated_at, int(next_nm_id))

            if pair == last_pair:
                stuck_count += 1
                if stuck_count >= 3:
                    raise RuntimeError("Cursor stuck")
            else:
                stuck_count = 0

            last_pair = pair
            cursor_updated_at, cursor_nm_id = pair

            time.sleep(BASE_SLEEP + random.random() * JITTER)

        self.save_parquet(rows, output_path, is_complete=True)

        self.stdout.write(
            self.style.SUCCESS(f"SAVED rows={len(rows)} file={output_path}")
        )

    # -----------------------
    # FETCH
    # -----------------------
    def fetch_page(self, headers, cursor_updated_at, cursor_nm_id):
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

        for attempt in range(MAX_RETRIES):
            r = requests.post(URL, headers=headers, json=payload, timeout=120)

            if r.status_code == 200:
                j = r.json()
                return j.get("cards") or [], j.get("cursor") or {}

            if r.status_code == 429:
                wait = min(BACKOFF_CAP, (BACKOFF_BASE ** attempt)) + random.random()
                self.stdout.write(f"WB 429 -> sleep {wait:.1f}s")
                time.sleep(wait)
                continue

            if 500 <= r.status_code < 600:
                wait = min(BACKOFF_CAP, (BACKOFF_BASE ** attempt)) + random.random()
                self.stdout.write(f"WB {r.status_code} -> sleep {wait:.1f}s")
                time.sleep(wait)
                continue

            raise RuntimeError(f"WB HTTP {r.status_code}: {r.text[:800]}")

        raise RuntimeError("WB retries exceeded")

    # -----------------------
    # SAVE
    # -----------------------
    def save_parquet(self, rows, path, is_complete=False):
        normalized = []

        for r in rows:
            nm_id = r.get("nmID")
            if not nm_id:
                continue

            normalized.append({
                "nm_id": int(nm_id),
                "payload": json.dumps(r, ensure_ascii=False),
            })

        df = pd.DataFrame(normalized)

        if not df.empty:
            df = df.drop_duplicates(subset=["nm_id"], keep="last")

        df["_loaded_at"] = datetime.now(timezone.utc).isoformat()
        df["_is_complete"] = is_complete

        tmp_path = path.with_suffix(".parquet.tmp")
        df.to_parquet(tmp_path, index=False)
        tmp_path.replace(path)