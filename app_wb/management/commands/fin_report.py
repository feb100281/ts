import os
import json
import time
from pathlib import Path
from datetime import datetime, date, timedelta, timezone

import requests
import pandas as pd

from django.core.management.base import BaseCommand, CommandError


URL = "https://finance-api.wildberries.ru/api/finance/v1/sales-reports/detailed"

LIMIT = 100000
TIMEOUT_SEC = 180
SLEEP_SEC = 5
MAX_WAIT_ON_429 = 300

MSK = timezone(timedelta(hours=3))


def day_start(d: date) -> str:
    return datetime(d.year, d.month, d.day, 0, 0, 0, tzinfo=MSK).isoformat()


def day_end(d: date) -> str:
    return datetime(d.year, d.month, d.day, 23, 59, 59, tzinfo=MSK).isoformat()


class Command(BaseCommand):
    help = "Download WB realization report to parquet (raw payload mode)"

    def add_arguments(self, parser):
        parser.add_argument("date", type=str, help="YYYY-MM-DD")
        parser.add_argument("--overwrite", action="store_true")

    def handle(self, *args, **options):
        token = os.getenv("WB_SUPER_TOKEN")
        if not token:
            raise CommandError("WB_SUPER_TOKEN is not set")

        parquet_path = os.getenv("PARQUET_PATH")
        if not parquet_path:
            raise CommandError("PARQUET_PATH is not set")

        try:
            target_date = date.fromisoformat(options["date"])
        except ValueError:
            raise CommandError("Date must be YYYY-MM-DD")

        output_dir = Path(parquet_path)
        output_dir.mkdir(parents=True, exist_ok=True)

        output_path = output_dir / f"sales_{target_date.isoformat()}.parquet"

        if output_path.exists() and not options["overwrite"]:
            self.stdout.write(f"SKIP exists: {output_path}")
            return

        date_from = day_start(target_date)
        date_to = day_end(target_date)

        self.stdout.write(f"DATE: {target_date}")
        self.stdout.write(f"WINDOW: {date_from} -> {date_to}")
        self.stdout.write(f"OUTPUT: {output_path}")

        rows = []
        rrdid = 0
        page = 0
        is_complete = False

        while True:
            chunk = self.fetch_chunk(token, date_from, date_to, rrdid)

            if chunk is None:
                self.stdout.write("STOP: rate limit")
                break

            if not chunk:
                self.stdout.write("DONE empty response")
                is_complete = True
                break

            page += 1
            rows.extend(chunk)

            self.save_parquet(
                rows, output_path, target_date, date_from, date_to, is_complete=False
            )

            rrdid = self.next_rrdid(chunk, rrdid)

            self.stdout.write(
                f"[{page}] got={len(chunk)} total={len(rows)} next_rrdid={rrdid}"
            )

            if len(chunk) < LIMIT:
                is_complete = True
                break

            time.sleep(SLEEP_SEC)

        self.save_parquet(
            rows, output_path, target_date, date_from, date_to, is_complete
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"SAVED rows={len(rows)} complete={is_complete} file={output_path}"
            )
        )

    def fetch_chunk(self, token, date_from, date_to, rrdid):
        headers = {
            "Authorization": token,
            "Content-Type": "application/json",
        }

        payload = {
            "dateFrom": date_from,
            "dateTo": date_to,
            "limit": LIMIT,
            "rrdid": rrdid,
            "period": "daily"
        }

        response = requests.post(
            URL, headers=headers, json=payload, timeout=TIMEOUT_SEC
        )

        if response.status_code == 204:
            return []

        if response.status_code == 200:
            data = response.json()
            return self.extract_rows(data)

        if response.status_code == 429:
            retry = response.headers.get("X-Ratelimit-Retry")

            wait = int(retry) + 2 if retry and retry.isdigit() else MAX_WAIT_ON_429

            self.stdout.write(f"WB 429 -> wait {wait}s")

            if wait > MAX_WAIT_ON_429:
                return None

            time.sleep(wait)
            return self.fetch_chunk(token, date_from, date_to, rrdid)

        if 500 <= response.status_code < 600:
            time.sleep(60)
            return self.fetch_chunk(token, date_from, date_to, rrdid)

        raise RuntimeError(f"WB HTTP {response.status_code}: {response.text[:1000]}")

    def extract_rows(self, data):
        if isinstance(data, list):
            return data

        if isinstance(data, dict):
            for key in ("data", "rows", "details", "report", "items"):
                value = data.get(key)
                if isinstance(value, list):
                    return value

        raise RuntimeError("Unexpected WB response structure")

    def next_rrdid(self, rows, current):
        ids = [int(r.get("rrdId")) for r in rows if r.get("rrdId")]

        if not ids:
            raise RuntimeError("No rrdId in chunk")

        nxt = max(ids)
        return nxt if nxt > current else current + 1

    def save_parquet(self, rows, path, target_date, date_from, date_to, is_complete):
        normalized = []

        for row in rows:
            rrd_id = row.get("rrdId")
            if not rrd_id:
                continue

            normalized.append({
                "rrd_id": int(rrd_id),
                "rr_dt": row.get("rrDate"),
                "date_from": row.get("dateFrom"),
                "date_to": row.get("dateTo"),
                "payload": json.dumps(row, ensure_ascii=False),
            })

        df = pd.DataFrame(normalized)

        if not df.empty:
            df = df.drop_duplicates(subset=["rrd_id"], keep="last")

        df["_loaded_at"] = datetime.now(timezone.utc).isoformat()
        df["_is_complete"] = is_complete

        tmp_path = path.with_suffix(".parquet.tmp")
        df.to_parquet(tmp_path, index=False)
        tmp_path.replace(path)