"""Заказы WB (склады WB и FBS) из API статистики: связь заказ → поставка → выкуп.

    python manage.py wb_orders --probe                 # проверка данных, ничего не пишет
    python manage.py wb_orders --probe --since 2024-01-01

API: statistics-api /api/v1/supplier/orders, flag=0 — заказы с lastChangeDate ≥ dateFrom,
до ~80 тыс. строк за запрос, лимит — 1 запрос в минуту. Токен — WB_TOKEN (категория
«Статистика»), запасной — WB_SUPER_TOKEN.
"""
from __future__ import annotations

import os
import time

import pandas as pd
import requests
from django.core.management.base import BaseCommand, CommandError

URL = "https://statistics-api.wildberries.ru/api/v1/supplier/orders"


def fetch(date_from: str) -> list[dict]:
    token = os.getenv("WB_TOKEN") or os.getenv("WB_SUPER_TOKEN")
    if not token:
        raise CommandError("Не задан WB_TOKEN")
    for attempt in range(4):
        r = requests.get(URL, headers={"Authorization": token},
                         params={"dateFrom": date_from, "flag": 0}, timeout=120)
        if r.status_code == 429:
            time.sleep(65)
            continue
        if r.status_code >= 400:
            raise CommandError(f"{r.status_code} {r.text[:300]}")
        return r.json() or []
    raise CommandError("превышен лимит запросов")


class Command(BaseCommand):
    help = "Заказы WB из API статистики"

    def add_arguments(self, parser):
        parser.add_argument("--probe", action="store_true")
        parser.add_argument("--since", default="2023-01-01")

    def handle(self, *args, **o):
        rows = fetch(o["since"])
        self.stdout.write(f"Строк за запрос (dateFrom={o['since']}): {len(rows)}")
        if not rows:
            return
        self.stdout.write("Поля: " + ", ".join(sorted(rows[0])))
        df = pd.DataFrame(rows)
        d = pd.to_datetime(df["date"], errors="coerce")
        lc = pd.to_datetime(df.get("lastChangeDate"), errors="coerce")
        self.stdout.write(f"Дата заказа: {d.min()} … {d.max()}; lastChangeDate до {lc.max()}")
        inc = pd.to_numeric(df.get("incomeID"), errors="coerce").fillna(0)
        self.stdout.write(f"С номером поставки (incomeID > 0): {(inc > 0).mean() * 100:.1f}%")
        for col in ("isCancel", "isSupply", "isRealization"):
            if col in df:
                self.stdout.write(f"{col}: {df[col].astype(str).value_counts().to_dict()}")
        if not o["probe"]:
            return

        # по месяцам: заказы и доля с номером поставки
        m = (pd.DataFrame({"m": d.dt.strftime("%Y-%m"), "inc": inc > 0})
             .groupby("m")["inc"].agg(["count", "mean"]))
        m["mean"] = (m["mean"] * 100).round(1)
        self.stdout.write("Месяц / заказов / % с поставкой:\n" + m.to_string())

        from conns import get_duckdb_conn_with_opt
        sr = pd.DataFrame({"srid": df["srid"].astype(str), "inc": inc.astype("int64")})
        with get_duckdb_conn_with_opt(ro=True) as con:
            con.register("o", sr)
            r = con.execute("""
                SELECT COUNT(*) AS orders,
                       COUNT(*) FILTER (WHERE o.srid IN (SELECT DISTINCT srid FROM sales.wb_raw
                                                         WHERE dtn = 'Продажа')) AS bought,
                       COUNT(*) FILTER (WHERE o.inc > 0 AND o.inc IN
                                        (SELECT supply_id FROM pg.wb_raw.wb_supplies)) AS inc_known
                FROM o""").fetchone()
        self.stdout.write(f"Заказов: {r[0]}; есть выкуп в отчёте WB (по srid): {r[1]} "
                          f"({r[1] / r[0] * 100:.1f}%); номер поставки найден в загруженных "
                          f"поставках: {r[2]}")
