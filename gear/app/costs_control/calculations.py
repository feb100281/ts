# gear/app/costs_control/calculations.py
from __future__ import annotations

from typing import Any

import pandas as pd

from .config import (
    CRITICAL_CV_LIMIT,
    DEFAULT_MEDIAN_DEVIATION_LIMIT,
)


def get_cost_columns(
    cost_type: str,
) -> dict[str, str]:
    suffix = (
        "упр"
        if cost_type == "Управленческая"
        else "бух"
    )

    return {
        "suffix": suffix,
        "rank": f"Ранг CV, {suffix}",
        "cv": f"Коэффициент вариации, %, {suffix}",
        "median": f"Медиана цены, {suffix}",
        "average": f"Средняя цена, {suffix}",
        "minimum": f"Мин. цена, {suffix}",
        "maximum": f"Макс. цена, {suffix}",
        "range": f"Диапазон цены, {suffix}",
        "different_prices": (
            f"Кол-во разных цен, {suffix}"
        ),
        "max_deviation": (
            f"Макс. отклонение от медианы, %, {suffix}"
        ),
        "min_deviation": (
            f"Мин. отклонение от медианы, %, {suffix}"
        ),
    }


def serialize_dataframe(
    df: pd.DataFrame,
) -> list[dict[str, Any]]:
    if df.empty:
        return []

    work = df.copy()

    for column in work.columns:
        if pd.api.types.is_datetime64_any_dtype(
            work[column]
        ):
            work[column] = work[column].dt.strftime(
                "%Y-%m-%d"
            )

    work = work.where(pd.notna(work), None)

    return work.to_dict("records")


def deserialize_dataframe(
    records: list[dict] | None,
) -> pd.DataFrame:
    if not records:
        return pd.DataFrame()

    return pd.DataFrame(records)


def build_filter_options(
    df: pd.DataFrame,
    column: str,
) -> list[dict]:
    if df.empty or column not in df.columns:
        return []

    values = (
        df[column]
        .dropna()
        .astype(str)
        .str.strip()
    )

    values = values[values.ne("")]

    return [
        {
            "label": value,
            "value": value,
        }
        for value in sorted(values.unique())
    ]


def apply_filters(
    df: pd.DataFrame,
    *,
    cost_type: str,
    brands: list[str] | None = None,
    categories: list[str] | None = None,
    suppliers: list[str] | None = None,
    nm_ids: list[str] | None = None,
    cv_ranks: list[str] | None = None,
    date_range: list[str] | None = None,
    cv_min: float | None = None,
    median_deviation_limit: float | None = None,
    only_changed: bool = False,
    only_anomalies: bool = False,
) -> pd.DataFrame:
    if df.empty:
        return df.copy()

    work = df.copy()
    columns = get_cost_columns(cost_type)

    if brands:
        work = work[
            work["Бренд"].astype(str).isin(brands)
        ]

    if categories:
        work = work[
            work["Категория"].astype(str).isin(
                categories
            )
        ]

    if suppliers:
        supplier_pattern = "|".join(
            map(str, suppliers)
        )

        work = work[
            work["Поставщики"]
            .fillna("")
            .astype(str)
            .str.contains(
                supplier_pattern,
                case=False,
                regex=True,
            )
        ]

    if nm_ids:
        normalized_nm_ids = {
            str(value).strip()
            for value in nm_ids
        }

        work = work[
            work["nm_id"]
            .astype(str)
            .isin(normalized_nm_ids)
        ]

    if cv_ranks:
        work = work[
            work[columns["rank"]].isin(cv_ranks)
        ]

    if date_range and len(date_range) == 2:
        start_date = pd.to_datetime(
            date_range[0],
            errors="coerce",
        )
        end_date = pd.to_datetime(
            date_range[1],
            errors="coerce",
        )

        last_upd_date = pd.to_datetime(
            work["Последняя дата УПД"],
            errors="coerce",
        )

        if pd.notna(start_date):
            work = work[last_upd_date >= start_date]

        if pd.notna(end_date):
            work = work[last_upd_date <= end_date]

    cv_series = pd.to_numeric(
        work[columns["cv"]],
        errors="coerce",
    )

    different_prices = pd.to_numeric(
        work[columns["different_prices"]],
        errors="coerce",
    )

    max_deviation = pd.to_numeric(
        work[columns["max_deviation"]],
        errors="coerce",
    ).abs()

    min_deviation = pd.to_numeric(
        work[columns["min_deviation"]],
        errors="coerce",
    ).abs()

    absolute_deviation = pd.concat(
        [
            max_deviation,
            min_deviation,
        ],
        axis=1,
    ).max(axis=1)

    if cv_min is not None:
        work = work[
            cv_series.fillna(0) >= float(cv_min)
        ]

    if only_changed:
        work = work[
            different_prices.fillna(0) > 1
        ]

    if only_anomalies:
        limit = (
            float(median_deviation_limit)
            if median_deviation_limit is not None
            else DEFAULT_MEDIAN_DEVIATION_LIMIT
        )

        work = work[
            absolute_deviation.fillna(0) >= limit
        ]

    return work.reset_index(drop=True)


def calculate_kpis(
    df: pd.DataFrame,
    cost_type: str,
) -> dict[str, float | int | None]:
    if df.empty:
        return {
            "total_products": 0,
            "changed_products": 0,
            "critical_products": 0,
            "average_cv": None,
            "max_increase": None,
            "max_decrease": None,
        }

    columns = get_cost_columns(cost_type)

    cv = pd.to_numeric(
        df[columns["cv"]],
        errors="coerce",
    )

    different_prices = pd.to_numeric(
        df[columns["different_prices"]],
        errors="coerce",
    )

    max_deviation = pd.to_numeric(
        df[columns["max_deviation"]],
        errors="coerce",
    )

    min_deviation = pd.to_numeric(
        df[columns["min_deviation"]],
        errors="coerce",
    )

    return {
        "total_products": int(len(df)),
        "changed_products": int(
            different_prices.fillna(0).gt(1).sum()
        ),
        "critical_products": int(
            cv.fillna(0).ge(CRITICAL_CV_LIMIT).sum()
        ),
        "average_cv": (
            float(cv.mean())
            if cv.notna().any()
            else None
        ),
        "max_increase": (
            float(max_deviation.max())
            if max_deviation.notna().any()
            else None
        ),
        "max_decrease": (
            float(min_deviation.min())
            if min_deviation.notna().any()
            else None
        ),
    }


def filter_history_for_product(
    history_df: pd.DataFrame,
    nm_id: str | None,
) -> pd.DataFrame:
    if history_df.empty or not nm_id:
        return pd.DataFrame()

    return (
        history_df[
            history_df["nm_id"].astype(str)
            == str(nm_id)
        ]
        .sort_values(
            [
                "Дата УПД",
                "ID УПД",
            ]
        )
        .reset_index(drop=True)
    )