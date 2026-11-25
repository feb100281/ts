#!/usr/bin/env python3
import os
import json
import sys

import requests
import psycopg


URL = "https://finance-api.wildberries.ru/api/v1/account/balance"


def get_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} is not set")
    return value


def main():
    token = get_env("WB_TOKEN")

    response = requests.get(
        URL,
        headers={"Authorization": token},
        timeout=30,
    )

    if response.status_code == 429:
        retry = response.headers.get("X-Ratelimit-Retry")
        reset = response.headers.get("X-Ratelimit-Reset")

        print(
            f"WB balance skipped: 429 Too Many Requests "
            f"retry={retry} reset={reset}",
            flush=True,
        )

        # 0 — чтобы systemd не считал это ошибкой
        return

    response.raise_for_status()
    payload = response.json()

    conn = psycopg.connect(
        dbname=get_env("DB_NAME"),
        user=get_env("DB_USER"),
        password=get_env("DB_PASSWORD"),
        host=get_env("DB_HOST"),
        port=get_env("DB_PORT"),
        connect_timeout=10,
    )

    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO wb_raw.wb_balance (payload)
                    VALUES (%s::jsonb)
                    """,
                    (json.dumps(payload, ensure_ascii=False),),
                )
    finally:
        conn.close()

    print("WB balance saved", flush=True)


if __name__ == "__main__":
    main()
