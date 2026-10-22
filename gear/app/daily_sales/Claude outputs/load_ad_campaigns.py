"""
Загрузка рекламных кампаний WB (API «Продвижение») в parquet.

Режимы:
    python utils/load_ad_campaigns.py            ежедневный прогон
    python utils/load_ad_campaigns.py --full     полная пересборка истории
    python utils/load_ad_campaigns.py --full --since 2024-01-01

Ежедневный прогон: активные и приостановленные кампании (плюс завершённые
за последние GRACE_DAYS дней), статистика за скользящее окно
STATS_WINDOW_DAYS, бюджеты кампаний, списания, пополнения, баланс.

Полная пересборка: все кампании, статистика завершённых кампаний за месяцы,
в которых по ним были списания, списания и пополнения с даты --since.
"""

from __future__ import annotations

import argparse
import json
import os
import time
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv


load_dotenv()


# ============================================================
# НАСТРОЙКИ
# ============================================================

BASE_URL = "https://advert-api.wildberries.ru"

COUNT_URL = f"{BASE_URL}/adv/v1/promotion/count"
ADVERTS_URL = f"{BASE_URL}/api/advert/v2/adverts"
FULLSTATS_URL = f"{BASE_URL}/adv/v3/fullstats"
BUDGET_URL = f"{BASE_URL}/adv/v1/budget"
BALANCE_URL = f"{BASE_URL}/adv/v1/balance"
EXPENSES_URL = f"{BASE_URL}/adv/v1/upd"
PAYMENTS_URL = f"{BASE_URL}/adv/v1/payments"

TZ = "Europe/Moscow"
HISTORY_START = date(2024, 1, 1)

STATS_WINDOW_DAYS = 30
MAX_PERIOD_DAYS = 31
GRACE_DAYS = 5

BATCH_SIZE = 50
FULLSTATS_PAUSE = 20
BUDGET_PAUSE = 0.3
FINANCE_PAUSE = 1.1
ADVERTS_PAUSE = 0.3

LIVE_STATUSES = {9, 11}
STATS_STATUSES = {7, 9, 11}

ADVERT_TYPE_NAMES = {
    4: "В каталоге",
    5: "В карточке товара",
    6: "В поиске",
    7: "На главной странице",
    8: "Автоматическая",
    9: "Аукцион",
}

ADVERT_STATUS_NAMES = {
    -1: "Удаляется",
    4: "Готова к запуску",
    7: "Завершена",
    8: "Отклонена",
    9: "Активна",
    11: "На паузе",
}

APP_TYPE_NAMES = {
    1: "Сайт",
    32: "Android",
    64: "iOS",
}

PAYMENT_SOURCE_NAMES = {
    0: "Счёт",
    1: "Баланс",
    3: "Карта",
}


# ============================================================
# СХЕМЫ ФАЙЛОВ
# ============================================================

METRIC_COLUMNS = [
    "views", "clicks", "ctr", "cpc", "sum", "atbs",
    "orders", "cr", "shks", "sum_price", "canceled",
]

SCHEMAS = {
    "info": [
        "advert_id", "name", "type", "type_name", "status", "status_name",
        "payment_type", "bid_type", "placement_search",
        "placement_recommendations", "currency", "can_change_nms",
        "create_time", "start_time", "change_time", "end_time",
        "_loaded_at", "payload",
    ],
    "nm_settings": [
        "advert_id", "nm_id", "subject_id", "subject_name",
        "bid_search_kopecks", "bid_recommendations_kopecks", "_loaded_at",
    ],
    "stats": [
        "advert_id", "date", *METRIC_COLUMNS, "currency", "loaded_at", "payload",
    ],
    "stats_by_nm": [
        "advert_id", "date", "app_type", "app_type_name", "nm_id", "title",
        *METRIC_COLUMNS, "loaded_at",
    ],
    "positions": [
        "advert_id", "date", "nm_id", "avg_position", "loaded_at",
    ],
    "budget": [
        "advert_id", "budget_total", "currency", "loaded_at", "payload",
    ],
    "expenses": [
        "upd_num", "upd_time", "upd_date", "upd_sum", "advert_id", "camp_name",
        "advert_type", "advert_type_name", "payment_source", "advert_status",
        "loaded_at",
    ],
    "payments": [
        "payment_id", "payment_date", "payment_sum", "payment_type",
        "payment_type_name", "status_id", "card_status", "currency",
        "loaded_at",
    ],
    "balance": [
        "balance", "net", "bonus", "currency", "cashbacks_total",
        "loaded_at", "payload",
    ],
}

FILE_PREFIX = {
    "info": "ad_campaigns_info",
    "nm_settings": "ad_campaigns_nm_settings",
    "stats": "ad_campaigns_stats",
    "stats_by_nm": "ad_campaigns_stats_by_nm",
    "positions": "ad_campaigns_positions",
    "budget": "ad_campaigns_budget",
    "expenses": "ad_campaigns_expenses",
    "payments": "ad_campaigns_payments",
    "balance": "ad_campaigns_balance",
}


# ============================================================
# HTTP
# ============================================================

class WbApi:

    def __init__(self, token: str):
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": token,
            "Content-Type": "application/json",
        })

    def get(self, url: str, params: dict | None = None, retries: int = 5):
        attempt = 0

        while True:
            attempt += 1

            try:
                response = self.session.get(url, params=params, timeout=90)
            except requests.RequestException as exc:
                if attempt >= retries:
                    raise RuntimeError(f"Сеть: {exc}") from exc
                time.sleep(5 * attempt)
                continue

            if response.status_code == 200:
                return response.json() if response.content else None

            if response.status_code == 204:
                return None

            if response.status_code in (429, 500, 502, 503, 504) and attempt < retries:
                wait = _retry_after(response, default=10 * attempt)
                print(f"  HTTP {response.status_code}, пауза {wait} c ({attempt}/{retries})")
                time.sleep(wait)
                continue

            raise RuntimeError(
                f"GET {url} {params or ''} -> HTTP {response.status_code}: "
                f"{response.text[:500]}"
            )


def _retry_after(response, default: int) -> int:
    for header in ("X-Ratelimit-Retry", "Retry-After"):
        value = response.headers.get(header)
        if value:
            try:
                return max(int(float(value)), 1) + 2
            except ValueError:
                pass
    return default


# ============================================================
# ВСПОМОГАТЕЛЬНОЕ
# ============================================================

def dig(d, *keys, default=None):
    current = d
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key)
    return default if current is None else current


def pick(d: dict, *keys, default=None):
    """Первое непустое значение из вариантов имени поля (camelCase / snake_case)."""
    if not isinstance(d, dict):
        return default
    for key in keys:
        value = d.get(key)
        if value is not None:
            return value
    return default


def chunked(items: list, size: int):
    for start in range(0, len(items), size):
        yield items[start:start + size]


def date_chunks(start: date, end: date, days: int = MAX_PERIOD_DAYS):
    cursor = start
    while cursor <= end:
        chunk_end = min(end, cursor + timedelta(days=days - 1))
        yield cursor, chunk_end
        cursor = chunk_end + timedelta(days=1)


def month_bounds(d: date, today: date) -> tuple[date, date]:
    first = d.replace(day=1)
    next_first = (first + timedelta(days=32)).replace(day=1)
    return first, min(today, next_first - timedelta(days=1))


def to_date(value) -> date | None:
    if not value:
        return None
    try:
        ts = pd.Timestamp(value)
    except Exception:
        return None
    if pd.isna(ts):
        return None
    if ts.tzinfo is not None:
        ts = ts.tz_convert(TZ).tz_localize(None)
    return ts.date()


def section(title: str):
    print()
    print("=" * 70)
    print(title)
    print("=" * 70)


def frame(kind: str, rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows).reindex(columns=SCHEMAS[kind])


# ============================================================
# 1. СПИСОК КАМПАНИЙ
# ============================================================

def load_campaign_list(api: WbApi) -> dict[int, dict]:
    section("1. Список кампаний")

    data = api.get(COUNT_URL) or {}
    campaigns: dict[int, dict] = {}

    for group in data.get("adverts") or []:
        for item in group.get("advert_list") or []:
            advert_id = item.get("advertId")
            if advert_id is None:
                continue
            campaigns[int(advert_id)] = {
                "type": group.get("type"),
                "status": group.get("status"),
                "change_time": item.get("changeTime"),
            }

        print(
            f"  тип {group.get('type')} ({ADVERT_TYPE_NAMES.get(group.get('type'), '—')}), "
            f"статус {group.get('status')} ({ADVERT_STATUS_NAMES.get(group.get('status'), '—')}): "
            f"{group.get('count', 0):,}"
        )

    print(f"Всего кампаний: {len(campaigns):,}")
    return campaigns


# ============================================================
# 2. ДЕТАЛИ КАМПАНИЙ
# ============================================================

def load_details(api: WbApi, advert_ids: list[int]) -> list[dict]:
    section("2. Детали кампаний")

    details: list[dict] = []

    for number, batch in enumerate(chunked(advert_ids, BATCH_SIZE), start=1):
        data = api.get(ADVERTS_URL, params={"ids": ",".join(map(str, batch))})
        adverts = (data or {}).get("adverts") or [] if isinstance(data, dict) else []
        details.extend(adverts)
        print(f"  пачка {number}: запрошено {len(batch)}, получено {len(adverts)}")
        time.sleep(ADVERTS_PAUSE)

    print(f"Деталей получено: {len(details):,}")
    return details


def build_info_rows(details: list[dict], campaigns: dict[int, dict], loaded_at):
    info_rows, nm_rows = [], []

    for detail in details:
        advert_id = detail.get("id")
        if advert_id is None:
            continue
        advert_id = int(advert_id)
        known = campaigns.get(advert_id, {})

        campaign_type = known.get("type")
        status = detail.get("status") if detail.get("status") is not None else known.get("status")

        info_rows.append({
            "advert_id": advert_id,
            "name": dig(detail, "settings", "name"),
            "type": campaign_type,
            "type_name": ADVERT_TYPE_NAMES.get(campaign_type, "—"),
            "status": status,
            "status_name": ADVERT_STATUS_NAMES.get(status, "—"),
            "payment_type": dig(detail, "settings", "payment_type"),
            "bid_type": detail.get("bid_type"),
            "placement_search": dig(detail, "settings", "placements", "search"),
            "placement_recommendations": dig(detail, "settings", "placements", "recommendations"),
            "currency": detail.get("currency"),
            "can_change_nms": dig(detail, "restrictions", "can_change_nms"),
            "create_time": dig(detail, "timestamps", "created"),
            "start_time": dig(detail, "timestamps", "started"),
            "change_time": dig(detail, "timestamps", "updated"),
            "end_time": dig(detail, "timestamps", "deleted"),
            "_loaded_at": loaded_at,
            "payload": json.dumps(detail, ensure_ascii=False),
        })

        for nm in detail.get("nm_settings") or []:
            nm_rows.append({
                "advert_id": advert_id,
                "nm_id": nm.get("nm_id"),
                "subject_id": dig(nm, "subject", "id"),
                "subject_name": dig(nm, "subject", "name"),
                "bid_search_kopecks": dig(nm, "bids_kopecks", "search"),
                "bid_recommendations_kopecks": dig(nm, "bids_kopecks", "recommendations"),
                "_loaded_at": loaded_at,
            })

    info_df = frame("info", info_rows)
    nm_df = frame("nm_settings", nm_rows)

    for column in ("create_time", "start_time", "change_time", "end_time"):
        info_df[column] = pd.to_datetime(info_df[column], utc=True, errors="coerce")

    # WB кодирует «не удалена» датой-заглушкой 2100-01-01
    info_df.loc[info_df["end_time"].dt.year >= 2050, "end_time"] = pd.NaT

    for column in ("placement_search", "placement_recommendations", "can_change_nms"):
        info_df[column] = info_df[column].astype("boolean")

    for df, columns in ((info_df, ("advert_id", "type", "status")), (nm_df, ("advert_id", "nm_id", "subject_id"))):
        for column in columns:
            df[column] = pd.to_numeric(df[column], errors="coerce").astype("Int64")

    for column in ("bid_search_kopecks", "bid_recommendations_kopecks"):
        nm_df[column] = pd.to_numeric(nm_df[column], errors="coerce").astype("Int64")

    return info_df, nm_df


# ============================================================
# 3. ФИНАНСЫ: СПИСАНИЯ И ПОПОЛНЕНИЯ
# ============================================================

def load_expenses(api: WbApi, start: date, end: date, loaded_at) -> pd.DataFrame:
    section(f"3. Списания за {start} .. {end}")

    rows = []
    for chunk_start, chunk_end in date_chunks(start, end):
        try:
            data = api.get(EXPENSES_URL, params={"from": str(chunk_start), "to": str(chunk_end)})
        except RuntimeError as exc:
            print(f"  {chunk_start}..{chunk_end}: ошибка, пропуск -- {exc}")
            time.sleep(FINANCE_PAUSE)
            continue

        items = data if isinstance(data, list) else []
        for item in items:
            upd_time = pick(item, "updTime", "upd_time")
            advert_type = pick(item, "advertType", "advert_type")
            rows.append({
                "upd_num": pick(item, "updNum", "upd_num"),
                "upd_time": upd_time,
                "upd_date": to_date(upd_time),
                "upd_sum": pick(item, "updSum", "upd_sum"),
                "advert_id": pick(item, "advertId", "advert_id"),
                "camp_name": pick(item, "campName", "camp_name"),
                "advert_type": advert_type,
                "advert_type_name": ADVERT_TYPE_NAMES.get(advert_type, "—"),
                "payment_source": pick(item, "paymentType", "payment_type"),
                "advert_status": pick(item, "advertStatus", "advert_status"),
                "loaded_at": loaded_at,
            })

        print(f"  {chunk_start}..{chunk_end}: {len(items):,}")
        time.sleep(FINANCE_PAUSE)

    df = frame("expenses", rows)
    df["upd_time"] = pd.to_datetime(df["upd_time"], utc=True, errors="coerce")
    for column in ("upd_num", "advert_id", "advert_type", "advert_status"):
        df[column] = pd.to_numeric(df[column], errors="coerce").astype("Int64")
    df["upd_sum"] = pd.to_numeric(df["upd_sum"], errors="coerce")

    print(f"Списаний: {len(df):,}, сумма {df['upd_sum'].sum():,.0f}")
    return df


def load_payments(api: WbApi, start: date, end: date, loaded_at) -> pd.DataFrame:
    section(f"4. Пополнения за {start} .. {end}")

    rows = []
    for chunk_start, chunk_end in date_chunks(start, end):
        try:
            data = api.get(PAYMENTS_URL, params={"from": str(chunk_start), "to": str(chunk_end)})
        except RuntimeError as exc:
            print(f"  {chunk_start}..{chunk_end}: ошибка, пропуск -- {exc}")
            time.sleep(FINANCE_PAUSE)
            continue

        items = data if isinstance(data, list) else []
        for item in items:
            payment_type = item.get("type")
            rows.append({
                "payment_id": item.get("id"),
                "payment_date": item.get("date"),
                "payment_sum": item.get("sum"),
                "payment_type": payment_type,
                "payment_type_name": PAYMENT_SOURCE_NAMES.get(payment_type, "—"),
                "status_id": pick(item, "statusId", "status_id"),
                "card_status": pick(item, "cardStatus", "card_status"),
                "currency": item.get("currency"),
                "loaded_at": loaded_at,
            })

        print(f"  {chunk_start}..{chunk_end}: {len(items):,}")
        time.sleep(FINANCE_PAUSE)

    df = frame("payments", rows)
    df["payment_date"] = pd.to_datetime(df["payment_date"], utc=True, errors="coerce")
    for column in ("payment_id", "payment_type", "status_id"):
        df[column] = pd.to_numeric(df[column], errors="coerce").astype("Int64")
    df["payment_sum"] = pd.to_numeric(df["payment_sum"], errors="coerce")

    print(f"Пополнений: {len(df):,}, сумма {df['payment_sum'].sum():,.0f}")
    return df


# ============================================================
# 5. СТАТИСТИКА
# ============================================================

class StatsCollector:

    def __init__(self, api: WbApi, loaded_at):
        self.api = api
        self.loaded_at = loaded_at
        self.stats: list[dict] = []
        self.by_nm: list[dict] = []
        self.positions: list[dict] = []
        self.requests = 0
        self.errors = 0

    def fetch(self, advert_ids: list[int], start: date, end: date, label: str = ""):
        for batch in chunked(advert_ids, BATCH_SIZE):
            self._fetch_batch(batch, start, end, label)

    def _fetch_batch(self, batch: list[int], start: date, end: date, label: str):
        self.requests += 1
        params = {
            "ids": ",".join(map(str, batch)),
            "beginDate": str(start),
            "endDate": str(end),
        }

        try:
            data = self.api.get(FULLSTATS_URL, params=params)
        except RuntimeError as exc:
            self.errors += 1
            print(f"  {label}{start}..{end}, {len(batch)} кампаний: ошибка -- {exc}")
            time.sleep(FULLSTATS_PAUSE)
            return

        items = data if isinstance(data, list) else []
        days_total = 0

        for campaign in items:
            advert_id = pick(campaign, "advertId", "advert_id")
            currency = campaign.get("currency")

            for day in campaign.get("days") or []:
                days_total += 1
                day_date = day.get("date")

                self.stats.append({
                    "advert_id": advert_id,
                    "date": day_date,
                    **{column: day.get(column) for column in METRIC_COLUMNS},
                    "currency": currency,
                    "loaded_at": self.loaded_at,
                    "payload": json.dumps(day, ensure_ascii=False),
                })

                for app in day.get("apps") or []:
                    app_type = pick(app, "appType", "app_type")
                    for nm in app.get("nms") or []:
                        self.by_nm.append({
                            "advert_id": advert_id,
                            "date": day_date,
                            "app_type": app_type,
                            "app_type_name": APP_TYPE_NAMES.get(app_type, "—"),
                            "nm_id": pick(nm, "nmId", "nm_id"),
                            "title": nm.get("name"),
                            **{column: nm.get(column) for column in METRIC_COLUMNS},
                            "loaded_at": self.loaded_at,
                        })

            for booster in pick(campaign, "boosterStats", "booster_stats", default=[]) or []:
                self.positions.append({
                    "advert_id": advert_id,
                    "date": booster.get("date"),
                    "nm_id": pick(booster, "nm", "nmId", "nm_id"),
                    "avg_position": pick(booster, "avg_position", "avgPosition"),
                    "loaded_at": self.loaded_at,
                })

        print(f"  {label}{start}..{end}: кампаний {len(batch)}, дней {days_total:,}")
        time.sleep(FULLSTATS_PAUSE)

    def frames(self):
        stats_df = frame("stats", self.stats)
        by_nm_df = frame("stats_by_nm", self.by_nm)
        positions_df = frame("positions", self.positions)

        for df in (stats_df, by_nm_df, positions_df):
            df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date
            df["advert_id"] = pd.to_numeric(df["advert_id"], errors="coerce").astype("Int64")

        for df in (stats_df, by_nm_df):
            for column in METRIC_COLUMNS:
                df[column] = pd.to_numeric(df[column], errors="coerce")

        for df in (by_nm_df, positions_df):
            df["nm_id"] = pd.to_numeric(df["nm_id"], errors="coerce").astype("Int64")

        by_nm_df["app_type"] = pd.to_numeric(by_nm_df["app_type"], errors="coerce").astype("Int64")
        positions_df["avg_position"] = pd.to_numeric(positions_df["avg_position"], errors="coerce")

        return stats_df, by_nm_df, positions_df


def history_months(
    advert_ids: list[int],
    expenses_df: pd.DataFrame,
    details_by_id: dict[int, dict],
    since: date,
    today: date,
) -> dict[date, list[int]]:
    """Месяцы, за которые нужна статистика по давно завершённым кампаниям."""
    months: dict[date, set[int]] = {}
    target = set(advert_ids)

    charged = set()
    if not expenses_df.empty:
        spend = expenses_df.dropna(subset=["advert_id", "upd_date"])
        spend = spend[spend["advert_id"].isin(target)]
        for advert_id, charge_date in zip(spend["advert_id"], spend["upd_date"]):
            charged.add(int(advert_id))
            for d in (charge_date, charge_date - timedelta(days=1)):
                if d >= since:
                    months.setdefault(d.replace(day=1), set()).add(int(advert_id))

    for advert_id in target - charged:
        detail = details_by_id.get(advert_id) or {}
        start = to_date(dig(detail, "timestamps", "started")) or to_date(dig(detail, "timestamps", "created"))
        end = to_date(dig(detail, "timestamps", "updated")) or start
        if start is None:
            continue
        start = max(start, since)
        end = min(max(end, start), today)
        cursor = start.replace(day=1)
        while cursor <= end:
            months.setdefault(cursor, set()).add(advert_id)
            cursor = (cursor + timedelta(days=32)).replace(day=1)

    return {month: sorted(ids) for month, ids in sorted(months.items())}


# ============================================================
# 6. БЮДЖЕТЫ КАМПАНИЙ
# ============================================================

def load_budgets(api: WbApi, advert_ids: list[int], loaded_at) -> pd.DataFrame:
    section(f"6. Бюджеты кампаний ({len(advert_ids):,})")

    rows = []
    for advert_id in advert_ids:
        try:
            data = api.get(BUDGET_URL, params={"id": advert_id}) or {}
        except RuntimeError as exc:
            print(f"  {advert_id}: ошибка -- {exc}")
            time.sleep(BUDGET_PAUSE)
            continue

        rows.append({
            "advert_id": advert_id,
            "budget_total": data.get("total"),
            "currency": data.get("currency"),
            "loaded_at": loaded_at,
            "payload": json.dumps(data, ensure_ascii=False),
        })
        time.sleep(BUDGET_PAUSE)

    df = frame("budget", rows)
    df["advert_id"] = pd.to_numeric(df["advert_id"], errors="coerce").astype("Int64")
    df["budget_total"] = pd.to_numeric(df["budget_total"], errors="coerce")

    print(f"Бюджетов получено: {len(df):,}, сумма {df['budget_total'].sum():,.0f}")
    return df


# ============================================================
# 7. БАЛАНС КАБИНЕТА
# ============================================================

def load_balance(api: WbApi, loaded_at) -> pd.DataFrame:
    section("7. Баланс кабинета")

    try:
        data = api.get(BALANCE_URL)
    except RuntimeError as exc:
        print(f"Баланс не загружен: {exc}")
        return frame("balance", [])

    if not isinstance(data, dict):
        print("Неожиданный формат ответа, пропуск")
        return frame("balance", [])

    cashbacks_total = sum((c.get("sum") or 0) for c in data.get("cashbacks") or [])
    df = frame("balance", [{
        "balance": data.get("balance"),
        "net": data.get("net"),
        "bonus": data.get("bonus"),
        "currency": data.get("currency"),
        "cashbacks_total": cashbacks_total,
        "loaded_at": loaded_at,
        "payload": json.dumps(data, ensure_ascii=False),
    }])

    print(f"net {data.get('net')}, balance {data.get('balance')}, bonus {data.get('bonus')}")
    return df


# ============================================================
# GRACE: НЕДАВНО ЗАВЕРШЁННЫЕ
# ============================================================

def read_recent_live(path: Path, today: date) -> dict[str, list[int]]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text())
    except Exception:
        return {}
    cutoff = today - timedelta(days=GRACE_DAYS)
    return {k: v for k, v in data.items() if pd.Timestamp(k).date() >= cutoff}


def write_recent_live(path: Path, data: dict[str, list[int]], today: date, live_ids: list[int]):
    data = dict(data)
    data[today.isoformat()] = sorted(live_ids)
    path.write_text(json.dumps(data))


# ============================================================
# ЗАПИСЬ
# ============================================================

def save(output_dir: Path, kind: str, df: pd.DataFrame, suffix: str) -> Path:
    path = output_dir / f"{FILE_PREFIX[kind]}_{suffix}.parquet"
    df.to_parquet(path, index=False)
    return path


# ============================================================
# MAIN
# ============================================================

def parse_args():
    parser = argparse.ArgumentParser(description="Загрузка рекламных кампаний WB")
    parser.add_argument("--full", action="store_true", help="полная пересборка истории")
    parser.add_argument("--since", type=date.fromisoformat, default=HISTORY_START)
    parser.add_argument("--skip-stats", action="store_true", help="без fullstats (отладка)")
    return parser.parse_args()


def main():
    args = parse_args()

    token = os.getenv("WB_SUPER_TOKEN")
    parquet_path = os.getenv("PARQUET_PATH")
    if not token:
        raise RuntimeError("WB_SUPER_TOKEN is not set")
    if not parquet_path:
        raise RuntimeError("PARQUET_PATH is not set")

    full = args.full or os.getenv("AD_CAMPAIGNS_INCLUDE_COMPLETED", "0") == "1"
    since = args.since

    output_dir = Path(parquet_path) / "ad_campaigns"
    output_dir.mkdir(parents=True, exist_ok=True)

    api = WbApi(token)
    now = pd.Timestamp.now(tz=TZ)
    today = now.date()
    loaded_at = now.tz_convert("UTC")
    mode = "full" if full else "daily"
    suffix = f"{today.isoformat()}_{mode}"
    window_start = today - timedelta(days=STATS_WINDOW_DAYS)

    print(f"Режим: {mode}, дата: {today}, окно статистики: {window_start} .. {today}")
    if full:
        print(f"История с {since}")

    campaigns = load_campaign_list(api)

    live_ids = sorted(i for i, c in campaigns.items() if c["status"] in LIVE_STATUSES)

    recent_file = output_dir / "_recent_live_ids.json"
    recent_live = read_recent_live(recent_file, today)
    grace_ids = {
        advert_id
        for ids in recent_live.values()
        for advert_id in ids
        if advert_id in campaigns and advert_id not in live_ids
    }

    if full:
        target_ids = sorted(campaigns)
    else:
        target_ids = sorted(set(live_ids) | grace_ids)
        print(f"Живых: {len(live_ids):,}, недавно завершённых: {len(grace_ids):,}")

    details = load_details(api, target_ids) if target_ids else []
    details_by_id = {int(d["id"]): d for d in details if d.get("id") is not None}
    info_df, nm_df = build_info_rows(details, campaigns, loaded_at)

    finance_start = since if full else window_start
    expenses_df = load_expenses(api, finance_start, today, loaded_at)
    payments_df = load_payments(api, finance_start, today, loaded_at)

    section("5. Статистика (fullstats)")
    collector = StatsCollector(api, loaded_at)

    stats_ids = [i for i in target_ids if campaigns.get(i, {}).get("status") in STATS_STATUSES]

    if not args.skip_stats and stats_ids:
        if full:
            recent_ids = set(live_ids) | grace_ids
            if not expenses_df.empty:
                recent_charged = expenses_df.loc[
                    expenses_df["upd_date"].apply(lambda d: d is not None and d >= window_start),
                    "advert_id",
                ].dropna().astype(int)
                recent_ids |= set(recent_charged)

            window_ids = [i for i in stats_ids if i in recent_ids]
            history_ids = [i for i in stats_ids if i not in recent_ids]

            print(f"Окно {STATS_WINDOW_DAYS} дн.: {len(window_ids):,} кампаний")
            collector.fetch(window_ids, window_start, today, label="окно ")

            months = history_months(history_ids, expenses_df, details_by_id, since, today)
            requests_planned = sum((len(ids) + BATCH_SIZE - 1) // BATCH_SIZE for ids in months.values())
            print(
                f"История: {len(history_ids):,} кампаний, {len(months):,} мес., "
                f"~{requests_planned:,} запросов (~{requests_planned * FULLSTATS_PAUSE / 60:.0f} мин.)"
            )

            for month, ids in months.items():
                month_start, month_end = month_bounds(month, today)
                collector.fetch(ids, month_start, month_end, label=f"{month:%m.%Y} ")
        else:
            collector.fetch(stats_ids, window_start, today)

    stats_df, by_nm_df, positions_df = collector.frames()
    print(
        f"Статистика: запросов {collector.requests:,}, ошибок {collector.errors:,}, "
        f"строк кампания×день {len(stats_df):,}, товар×день {len(by_nm_df):,}"
    )

    budgets_df = load_budgets(api, live_ids, loaded_at) if live_ids else frame("budget", [])
    balance_df = load_balance(api, loaded_at)

    section("8. Сохранение")
    for kind, df in (
        ("info", info_df),
        ("nm_settings", nm_df),
        ("stats", stats_df),
        ("stats_by_nm", by_nm_df),
        ("positions", positions_df),
        ("budget", budgets_df),
        ("expenses", expenses_df),
        ("payments", payments_df),
    ):
        path = save(output_dir, kind, df, suffix)
        print(f"  {path.name}: {len(df):,}")

    if not balance_df.empty:
        path = save(output_dir, "balance", balance_df, suffix)
        print(f"  {path.name}: 1")

    write_recent_live(recent_file, recent_live, today, live_ids)

    section("ГОТОВО")
    spend_stats = stats_df["sum"].sum() if not stats_df.empty else 0
    print(f"Кампаний в деталях: {len(info_df):,}")
    print(f"Расход по статистике: {spend_stats:,.0f} ₽")
    print(f"Списания за период:   {expenses_df['upd_sum'].sum():,.0f} ₽")
    print(f"Бюджеты активных:     {budgets_df['budget_total'].sum():,.0f} ₽")
    print(f"Загружено: {loaded_at}")


if __name__ == "__main__":
    main()
