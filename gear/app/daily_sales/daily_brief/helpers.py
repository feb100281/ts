from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

import pandas as pd


def json_safe(value: Any):
    if value is None:
        return None
    if isinstance(value, (date, datetime, pd.Timestamp)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    return value


def dataframe_records(df: pd.DataFrame, limit: int | None = None) -> list[dict]:
    if df is None or df.empty:
        return []
    work = df.head(limit) if limit is not None else df
    return [{str(key): json_safe(value) for key, value in row.items()} for row in work.to_dict("records")]


def number(value, default=0.0) -> float:
    try:
        if value is None or pd.isna(value):
            return float(default)
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def fmt_number(value, digits=0) -> str:
    value = number(value)
    result = f"{value:,.0f}" if digits == 0 else f"{value:,.{digits}f}"
    return result.replace(",", " ")


def fmt_money(value) -> str:
    return f"{fmt_number(value, 0)} ₽"


def fmt_pct(value, digits=1) -> str:
    return f"{fmt_number(value, digits)}%"


def change_pct(current, previous) -> float | None:
    current = number(current)
    previous = number(previous)
    if previous == 0:
        return None
    return (current - previous) / abs(previous) * 100
