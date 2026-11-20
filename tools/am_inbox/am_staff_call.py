"""
Сотрудники Армении на сервере: объединение дублей, новые счета — к существующим, новые сотрудники.

    python am_staff_call.py --env <путь к .env>
"""

from __future__ import annotations

import argparse
import json
import ssl
import sys
import urllib.error
import urllib.request
from pathlib import Path

from am_upload import DEFAULT_URL, read_env


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--env", type=Path, required=True)
    args = ap.parse_args(argv)
    env = read_env(args.env)
    token = env.get("AM_UPLOAD_TOKEN", "")
    if not token:
        print(f"В {args.env} нет AM_UPLOAD_TOKEN")
        return 1
    url = env.get("AM_UPLOAD_URL", DEFAULT_URL).replace("/upload/", "/staff/")
    req = urllib.request.Request(url, data=b"", method="POST",
                                 headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req, timeout=300, context=ssl.create_default_context()) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            data = json.loads(exc.read().decode("utf-8"))
        except ValueError:
            print(f"Ошибка сервера: {exc.code}")
            return 1
    except (urllib.error.URLError, OSError) as exc:
        print(f"Нет связи с сервером: {exc}")
        return 1
    for line in data.get("log", []):
        print(line)
    if not data.get("ok"):
        print(f"\n✗ Ошибка: {data.get('error')}")
        return 1
    new = data.get("new", [])
    print("=" * 60)
    if new:
        print(f"ВНИМАНИЕ: заведены новые сотрудники ({len(new)}):")
        for line in new:
            print(f"  {line}")
    else:
        print("Новых сотрудников не заведено.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
