"""Заказы WB (склады WB и FBS) из API статистики: связь заказ → поставка → выкуп.

    python manage.py wb_orders --probe                 # проверка данных, ничего не пишет
    python manage.py wb_orders --probe --since 2024-01-01
    python manage.py wb_orders                         # загрузка: с последнего изменения в базе
    python manage.py wb_orders --since 2026-01-01      # загрузка с даты (WB хранит ~полгода)

Пишет только свою таблицу wb_raw.wb_orders (строка = заказ, ключ srid), обновляет
заказ при каждом изменении (отмена и т. п.).

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
from django.db import connection

DDL = """
CREATE TABLE IF NOT EXISTS wb_raw.wb_orders (
    srid            text PRIMARY KEY,
    g_number        text,
    order_dt        timestamp,
    last_change     timestamp,
    nm_id           bigint,
    barcode         text,
    tech_size       text,
    supplier_article text,
    brand           text,
    subject         text,
    category        text,
    income_id       bigint,
    is_cancel       boolean,
    cancel_dt       timestamp,
    warehouse       text,
    warehouse_type  text,
    region          text,
    total_price     numeric,
    discount_percent numeric,
    spp             numeric,
    price_with_disc numeric,
    finished_price  numeric,
    loaded_at       timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS wb_orders_income_idx ON wb_raw.wb_orders (income_id);
CREATE INDEX IF NOT EXISTS wb_orders_nm_dt_idx ON wb_raw.wb_orders (nm_id, order_dt);
"""

COLS = [("srid", "srid"), ("g_number", "gNumber"), ("order_dt", "date"),
        ("last_change", "lastChangeDate"), ("nm_id", "nmId"), ("barcode", "barcode"),
        ("tech_size", "techSize"), ("supplier_article", "supplierArticle"), ("brand", "brand"),
        ("subject", "subject"), ("category", "category"), ("income_id", "incomeID"),
        ("is_cancel", "isCancel"), ("cancel_dt", "cancelDate"), ("warehouse", "warehouseName"),
        ("warehouse_type", "warehouseType"), ("region", "regionName"),
        ("total_price", "totalPrice"), ("discount_percent", "discountPercent"), ("spp", "spp"),
        ("price_with_disc", "priceWithDisc"), ("finished_price", "finishedPrice")]

UPSERT = ("INSERT INTO wb_raw.wb_orders (" + ", ".join(c for c, _ in COLS) + ", loaded_at) "
          "VALUES (" + ", ".join(["%s"] * len(COLS)) + ", now()) ON CONFLICT (srid) DO UPDATE SET "
          + ", ".join(f"{c} = EXCLUDED.{c}" for c, _ in COLS[1:]) + ", loaded_at = now()")


def _val(k, v):
    if v in ("", None):
        return None
    if k == "cancelDate" and str(v).startswith("0001"):
        return None
    return v

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
        parser.add_argument("--since", help="dateFrom; по умолчанию — последнее изменение в базе")

    def handle(self, *args, **o):
        if not o["probe"]:
            return self.load(o)
        rows = fetch(o["since"] or "2023-01-01")
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

    # ---------------------------------------------------------------- загрузка
    def load(self, o):
        with connection.cursor() as cur:
            cur.execute(DDL)
            cur.execute("SELECT MAX(last_change) FROM wb_raw.wb_orders")
            last = cur.fetchone()[0]
        since = o["since"] or (last.strftime("%Y-%m-%dT%H:%M:%S") if last else "2023-01-01")
        total = 0
        while True:
            rows = fetch(since)
            if not rows:
                break
            with connection.cursor() as cur:
                cur.executemany(UPSERT, [[_val(k, r.get(k)) for _, k in COLS] for r in rows])
            total += len(rows)
            nxt = max(str(r.get("lastChangeDate") or "") for r in rows)
            self.stdout.write(f"  {len(rows)} строк, изменения до {nxt}", ending="\n")
            self.stdout.flush()
            if len(rows) < 80000 or nxt <= since:
                break
            since = nxt
            time.sleep(61)                       # лимит API: 1 запрос в минуту
        self.stdout.write(self.style.SUCCESS(f"Готово: заказов загружено/обновлено {total}"))
