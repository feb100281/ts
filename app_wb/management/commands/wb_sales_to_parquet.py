import os
import time
from pathlib import Path
from datetime import datetime, date, timedelta, timezone

import requests
import pandas as pd

from django.core.management.base import BaseCommand, CommandError


URL = "https://statistics-api.wildberries.ru/api/v5/supplier/reportDetailByPeriod"

PERIOD = "daily"
LIMIT = 100000
TIMEOUT_SEC = 180
SLEEP_SEC = 65

MSK = timezone(timedelta(hours=3))

DEFAULT_BASE_DIR = "/home/daria/ts/data/sales"


def iso_msk(dt: datetime) -> str:
    return dt.astimezone(MSK).replace(microsecond=0).isoformat()


def day_start(d: date) -> datetime:
    return datetime(d.year, d.month, d.day, 0, 0, 0, tzinfo=MSK)


def day_end(d: date) -> datetime:
    return datetime(d.year, d.month, d.day, 23, 59, 59, tzinfo=MSK)


def next_rrdid(rows: list[dict], current: int) -> int:
    ids = [int(x["rrd_id"]) for x in rows if x.get("rrd_id") is not None]

    if not ids:
        raise RuntimeError("Chunk has no rrd_id values; cannot continue paging.")

    nxt = max(ids)

    if nxt <= current:
        nxt = current + 1

    return nxt


class Command(BaseCommand):
    help = "Download WB realization report for one day and save it to parquet"

    def add_arguments(self, parser):
        parser.add_argument(
            "date",
            type=str,
            help="Date to download, format YYYY-MM-DD",
        )

        parser.add_argument(
            "--base-dir",
            type=str,
            default=os.getenv("WB_SALES_PARQUET_DIR", DEFAULT_BASE_DIR),
            help="Base directory for parquet files",
        )

        parser.add_argument(
            "--overwrite",
            action="store_true",
            help="Overwrite parquet file if it already exists",
        )

    def handle(self, *args, **options):
        token = os.getenv("WB_TOKEN")
        if not token:
            raise CommandError("WB_TOKEN is not set")

        try:
            target_date = date.fromisoformat(options["date"])
        except ValueError:
            raise CommandError("Date must be in YYYY-MM-DD format")

        base_dir = Path(options["base_dir"])

        output_dir = base_dir / "realization_daily"
        output_path = output_dir / f"sales_{target_date.isoformat()}.parquet"
        tmp_path = output_path.with_suffix(".parquet.tmp")

        if output_path.exists() and not options["overwrite"]:
            self.stdout.write(f"SKIP exists: {output_path}")
            return

        date_from = iso_msk(day_start(target_date))
        date_to = iso_msk(day_end(target_date))

        self.stdout.write(f"DATE: {target_date}")
        self.stdout.write(f"WINDOW: {date_from} -> {date_to}")
        self.stdout.write(f"OUTPUT: {output_path}")

        rows = self.fetch_day(
            token=token,
            date_from=date_from,
            date_to=date_to,
        )

        loaded_at = datetime.now(timezone.utc).isoformat()

        if rows:
            df = pd.DataFrame(rows)

            if "rrd_id" in df.columns:
                df["rrd_id"] = pd.to_numeric(df["rrd_id"], errors="coerce")
                df = df.dropna(subset=["rrd_id"])
                df["rrd_id"] = df["rrd_id"].astype("int64")
                df = df.drop_duplicates(subset=["rrd_id"], keep="last")

            df["_wb_report_date"] = target_date.isoformat()
            df["_date_from"] = date_from
            df["_date_to"] = date_to
            df["_loaded_at"] = loaded_at
        else:
            df = pd.DataFrame(
                columns=[
                    "_wb_report_date",
                    "_date_from",
                    "_date_to",
                    "_loaded_at",
                ]
            )

        output_dir.mkdir(parents=True, exist_ok=True)

        df.to_parquet(tmp_path, index=False)
        tmp_path.replace(output_path)

        self.stdout.write(
            self.style.SUCCESS(
                f"SAVED rows={len(df)} file={output_path}"
            )
        )

    def fetch_day(self, token: str, date_from: str, date_to: str) -> list[dict]:
        headers = {"Authorization": token}

        rrdid = 0
        page = 0
        rows: list[dict] = []

        while True:
            params = {
                "dateFrom": date_from,
                "dateTo": date_to,
                "limit": LIMIT,
                "rrdid": rrdid,
                "period": PERIOD,
            }

            chunk = self.wb_get(headers=headers, params=params)

            if not chunk:
                self.stdout.write("DONE empty/204")
                break

            page += 1
            rows.extend(chunk)

            rrdid = next_rrdid(chunk, rrdid)

            self.stdout.write(
                f"[{page}] got={len(chunk)} total={len(rows)} next_rrdid={rrdid}"
            )

            time.sleep(SLEEP_SEC)

        return rows

    def wb_get(self, headers: dict, params: dict) -> list[dict]:
        while True:
            response = requests.get(
                URL,
                headers=headers,
                params=params,
                timeout=TIMEOUT_SEC,
            )

            if response.status_code == 204:
                return []

            if response.status_code == 200:
                data = response.json()

                if not isinstance(data, list):
                    raise RuntimeError(f"Unexpected WB response type: {type(data)}")

                return data

            if response.status_code == 429:
                retry = response.headers.get("X-Ratelimit-Retry")
                reset = response.headers.get("X-Ratelimit-Reset")

                if retry and retry.isdigit():
                    wait = int(retry) + 2
                elif reset and reset.isdigit():
                    wait = int(reset) + 2
                else:
                    wait = 300

                self.stdout.write(
                    f"WB 429 -> sleep {wait}s retry={retry} reset={reset}"
                )
                time.sleep(wait)
                continue

            if 500 <= response.status_code < 600:
                self.stdout.write(f"WB {response.status_code} -> sleep 300s")
                time.sleep(300)
                continue

            raise RuntimeError(
                f"WB HTTP {response.status_code}: {response.text[:800]}"
            )