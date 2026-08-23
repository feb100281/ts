from __future__ import annotations

from calendar import monthrange
from datetime import date, timedelta
from typing import Iterable

import pandas as pd

from ..helpers import json_safe


def first_row(df: pd.DataFrame) -> dict:
    if df is None or df.empty:
        return {}
    return {str(k): json_safe(v) for k, v in df.iloc[0].to_dict().items()}


def find_daily_row(rows: list[dict], target_date: date) -> dict:
    for row in rows or []:
        value = pd.to_datetime(row.get("date"), errors="coerce")
        if pd.notna(value) and value.date() == target_date:
            return row
    return {}


def date_range(start: date, finish: date) -> Iterable[date]:
    current = start
    while current <= finish:
        yield current
        current += timedelta(days=1)


def previous_month_same_day(value: date) -> date:
    year = value.year if value.month > 1 else value.year - 1
    month = value.month - 1 if value.month > 1 else 12
    day = min(value.day, monthrange(year, month)[1])
    return date(year, month, day)


def previous_year_same_day(value: date) -> date:
    day = min(value.day, monthrange(value.year - 1, value.month)[1])
    return date(value.year - 1, value.month, day)


def quote_ident(value: str) -> str:
    return '"' + str(value).replace('"', '""') + '"'


def table_columns(connection, table_name: str) -> list[str]:
    try:
        rows = connection.execute(f"PRAGMA table_info('{table_name}')").fetchall()
        return [str(row[1]) for row in rows]
    except Exception:
        try:
            df = connection.execute(f"DESCRIBE {table_name}").df()
            key = "column_name" if "column_name" in df.columns else df.columns[0]
            return df[key].astype(str).tolist()
        except Exception:
            return []


def choose_column(columns: list[str], candidates: list[str]) -> str | None:
    lookup = {str(col).lower(): str(col) for col in columns}
    for candidate in candidates:
        found = lookup.get(candidate.lower())
        if found:
            return found
    return None
