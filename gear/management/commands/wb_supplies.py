"""Загрузка поставок FBW (склады WB) из API «Поставки» в wb_raw.

    python manage.py wb_supplies --probe          # проверка: показать поля, ничего не пишет
    python manage.py wb_supplies                  # загрузка с 2024-01-01
    python manage.py wb_supplies --since 2026-09-01

Пишет только свои таблицы: wb_raw.wb_supplies (поставка) и wb_raw.wb_supply_goods
(состав поставки). Строки хранятся целиком (jsonb), разбор — во витрине.
Токен — WB_SUPER_TOKEN (категория «Поставки»).
"""
from __future__ import annotations

import json
import os
import time
from datetime import date

import requests
from django.core.management.base import BaseCommand, CommandError
from django.db import connection

BASE = "https://supplies-api.wildberries.ru"
PAUSE = 2.2          # лимит API поставок — около 30 запросов в минуту
PAGE = 1000

DDL = """
CREATE TABLE IF NOT EXISTS wb_raw.wb_supplies (
    supply_id   bigint PRIMARY KEY,
    preorder_id bigint,
    row_json    jsonb NOT NULL,
    loaded_at   timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS wb_raw.wb_supply_goods (
    supply_id bigint NOT NULL,
    line_no   integer NOT NULL,
    row_json  jsonb NOT NULL,
    loaded_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (supply_id, line_no)
);
"""


class Command(BaseCommand):
    help = "Поставки FBW из API WB → wb_raw.wb_supplies / wb_raw.wb_supply_goods"

    def add_arguments(self, parser):
        parser.add_argument("--since", default="2024-01-01")
        parser.add_argument("--date-type", default="createDate",
                            choices=["factDate", "createDate", "supplyDate", "updatedDate"],
                            help="по какой дате отбирать поставки")
        parser.add_argument("--probe", action="store_true",
                            help="показать первую поставку и её состав, без записи")
        parser.add_argument("--refresh-days", type=int, default=60,
                            help="состав перечитывать для поставок не старше N дней")

    # ---------------------------------------------------------------- API
    def _req(self, method, path, **kw):
        token = os.getenv("WB_SUPER_TOKEN")
        if not token:
            raise CommandError("WB_SUPER_TOKEN не задан")
        for attempt in range(5):
            r = requests.request(method, BASE + path, headers={"Authorization": token},
                                 timeout=60, **kw)
            time.sleep(PAUSE)
            if r.status_code == 429:
                time.sleep(20 * (attempt + 1))
                continue
            if r.status_code >= 400:
                raise CommandError(f"{method} {path}: {r.status_code} {r.text[:300]}")
            return r.json()
        raise CommandError(f"{method} {path}: превышен лимит запросов")

    def supplies(self, since: str, dtype: str = "factDate") -> list[dict]:
        out, offset = [], 0
        body = {"dates": [{"from": since, "till": date.today().isoformat(), "type": dtype}]}
        while True:
            page = self._req("POST", "/api/v1/supplies",
                             params={"limit": PAGE, "offset": offset}, json=body)
            page = page if isinstance(page, list) else (page or {}).get("data") or []
            out += page
            if len(page) < PAGE:
                return out
            offset += PAGE

    def goods(self, supply_id: int) -> list[dict]:
        out, offset = [], 0
        while True:
            page = self._req("GET", f"/api/v1/supplies/{supply_id}/goods",
                             params={"limit": PAGE, "offset": offset, "isPreorderID": "false"})
            page = page if isinstance(page, list) else (page or {}).get("data") or []
            out += page
            if len(page) < PAGE:
                return out
            offset += PAGE

    # ---------------------------------------------------------------- run
    def handle(self, *args, **o):
        rows = self.supplies(o["since"], o["date_type"])
        self.stdout.write(f"Поставок с {o['since']} ({o['date_type']}): {len(rows)}")
        if o["probe"]:
            from collections import Counter
            st = Counter(str(r.get("statusID")) for r in rows)
            nofact = sum(1 for r in rows if not r.get("factDate"))
            self.stdout.write(f"statusID: {dict(st)}; без factDate: {nofact}")
        if o["probe"]:
            if not rows:
                return
            first = rows[0]
            self.stdout.write("Поля поставки: " + ", ".join(sorted(first)))
            self.stdout.write(json.dumps(first, ensure_ascii=False, default=str)[:800])
            sid = first.get("supplyID") or first.get("supplyId") or first.get("id")
            if sid:
                g = self.goods(int(sid))
                self.stdout.write(f"Строк состава у {sid}: {len(g)}")
                if g:
                    self.stdout.write("Поля состава: " + ", ".join(sorted(g[0])))
                    self.stdout.write(json.dumps(g[0], ensure_ascii=False, default=str)[:800])
            return

        with connection.cursor() as cur:
            cur.execute(DDL)
            cur.execute("SELECT supply_id FROM wb_raw.wb_supply_goods GROUP BY 1")
            have = {r[0] for r in cur.fetchall()}
        fresh_from = date.fromordinal(date.today().toordinal() - o["refresh_days"]).isoformat()
        n_goods = 0
        for s in rows:
            sid = s.get("supplyID") or s.get("supplyId")
            if not sid:
                continue                            # черновик без номера поставки
            sid = int(sid)
            with connection.cursor() as cur:
                cur.execute("""
                    INSERT INTO wb_raw.wb_supplies (supply_id, preorder_id, row_json, loaded_at)
                    VALUES (%s, %s, %s, now())
                    ON CONFLICT (supply_id) DO UPDATE
                    SET preorder_id = EXCLUDED.preorder_id, row_json = EXCLUDED.row_json,
                        loaded_at = now()""",
                    (sid, s.get("preorderID") or s.get("preorderId"),
                     json.dumps(s, ensure_ascii=False, default=str)))
            fact = str(s.get("factDate") or s.get("supplyDate") or s.get("createDate") or "")[:10]
            if sid in have and fact and fact < fresh_from:
                continue                            # старая принятая поставка — состав не меняется
            g = self.goods(sid)
            with connection.cursor() as cur:
                cur.execute("DELETE FROM wb_raw.wb_supply_goods WHERE supply_id = %s", (sid,))
                for i, line in enumerate(g):
                    cur.execute("""
                        INSERT INTO wb_raw.wb_supply_goods (supply_id, line_no, row_json)
                        VALUES (%s, %s, %s)""",
                        (sid, i, json.dumps(line, ensure_ascii=False, default=str)))
            n_goods += 1
        self.stdout.write(self.style.SUCCESS(
            f"Готово: поставок {len(rows)}, состав обновлён у {n_goods}"))
