import os
import json
from pathlib import Path
from datetime import datetime, date, timezone

import requests
import pandas as pd

from django.core.management.base import BaseCommand, CommandError


URL = "https://seller-analytics-api.wildberries.ru/api/analytics/v1/stocks-report/wb-warehouses"
LIMIT = 250000


class Command(BaseCommand):
    help = "Download WB stocks snapshot to parquet (raw payload mode)"

    def handle(self, *args, **options):
        token = os.getenv("WB_SUPER_TOKEN")
        if not token:
            raise CommandError("WB_SUPER_TOKEN is not set")

        parquet_path = os.getenv("PARQUET_PATH")
        if not parquet_path:
            raise CommandError("PARQUET_PATH is not set")

        today = date.today()

        output_dir = Path(parquet_path) / "stocks"
        output_dir.mkdir(parents=True, exist_ok=True)

        output_path = output_dir / f"stocks_{today.isoformat()}.parquet"

        headers = {
            "Authorization": token,
            "Content-Type": "application/json",
        }

        payload = {
            "limit": LIMIT,
            "offset": 0,
        }

        r = requests.post(URL, headers=headers, json=payload)

        self.stdout.write(f"Status code: {r.status_code}")

        if r.status_code != 200:
            self.stdout.write(r.text)
            raise CommandError("WB API error")

        response = r.json()
        rows = response["data"]["items"]

        df = pd.DataFrame({
            "nm_id": [row["nmId"] for row in rows],
            "payload": [json.dumps(row, ensure_ascii=False) for row in rows],
        })

        df["_loaded_at"] = datetime.now(timezone.utc).isoformat()
        df["_is_complete"] = True

        # атомарная запись
        tmp_path = output_path.with_suffix(".parquet.tmp")
        df.to_parquet(tmp_path, index=False)
        tmp_path.replace(output_path)

        self.stdout.write(
            self.style.SUCCESS(
                f"SAVED rows={len(df)} file={output_path}"
            )
        )