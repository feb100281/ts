# gear/app/loans/calculations.py
from __future__ import annotations

from datetime import date
from typing import Any

import numpy as np
import pandas as pd

from .config import MATURITY_ORDER


MONEY_COLUMNS = [
    "contract_amount",
    "total_drawdown",
    "total_repaid",
    "total_interest_accrued",
    "total_interest_repaid",
    "ending_balance",
    "interest_balance",
    "total_debt",
]


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

    work = work.replace(
        [np.inf, -np.inf],
        np.nan,
    )
    work = work.where(pd.notna(work), None)

    return work.to_dict("records")


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
        {"label": value, "value": value}
        for value in sorted(values.unique())
    ]


def enrich_snapshot(
    df: pd.DataFrame,
    report_date: str,
) -> pd.DataFrame:
    if df.empty:
        return df.copy()

    work = df.copy()

    report_ts = pd.Timestamp(
        report_date
    ).normalize()

    for column in MONEY_COLUMNS + [
        "rate",
        "condition_rate",
        "penalty_rate",
    ]:
        if column in work.columns:
            work[column] = pd.to_numeric(
                work[column],
                errors="coerce",
            )

    work["repayment_date"] = pd.to_datetime(
        work.get(
            "repayment_date"
        ),
        errors="coerce",
    ).dt.normalize()

    # Сначала считаем техническое количество дней.
    work["days_to_maturity"] = (
        work["repayment_date"]
        - report_ts
    ).dt.days

    debt = (
        pd.to_numeric(
            work["total_debt"],
            errors="coerce",
        )
        .fillna(0.0)
    )

    days = work[
        "days_to_maturity"
    ]

    # ================================================================
    # СТАТУС ДОГОВОРА
    # ================================================================

    status = pd.Series(
        "Активен",
        index=work.index,
        dtype="object",
    )

    paid_mask = (
        debt.abs()
        <= 0.01
    )

    overdue_mask = (
        debt.gt(0.01)
        & days.notna()
        & days.lt(0)
    )

    due_30_mask = (
        debt.gt(0.01)
        & days.notna()
        & days.between(
            0,
            30,
            inclusive="both",
        )
    )

    status.loc[
        paid_mask
    ] = "Погашен"

    status.loc[
        overdue_mask
    ] = "Просрочен"

    status.loc[
        due_30_mask
    ] = "Погашение ≤ 30 дней"

    work["status"] = status

    # ================================================================
    # ВАЖНО:
    # У погашенного договора больше нет показателя
    # "дней до погашения".
    #
    # Дата погашения договора остаётся исторической,
    # но количество дней в таблице должно быть пустым.
    # ================================================================

    work.loc[
        paid_mask,
        "days_to_maturity",
    ] = np.nan

    # После очистки пересчитываем ссылку days,
    # чтобы maturity_bucket тоже не использовал старые значения.
    days = work[
        "days_to_maturity"
    ]

    # ================================================================
    # ГРУППА ПО СРОКУ ПОГАШЕНИЯ
    # ================================================================

    maturity = pd.Series(
        "Без даты",
        index=work.index,
        dtype="object",
    )

    active = (
        debt.gt(0.01)
    )

    maturity.loc[
        active
        & days.notna()
        & days.lt(0)
    ] = "Просрочено"

    maturity.loc[
        active
        & days.notna()
        & days.between(
            0,
            30,
            inclusive="both",
        )
    ] = "До 30 дней"

    maturity.loc[
        active
        & days.notna()
        & days.between(
            31,
            90,
            inclusive="both",
        )
    ] = "31–90 дней"

    maturity.loc[
        active
        & days.notna()
        & days.between(
            91,
            180,
            inclusive="both",
        )
    ] = "91–180 дней"

    maturity.loc[
        active
        & days.notna()
        & days.between(
            181,
            365,
            inclusive="both",
        )
    ] = "181–365 дней"

    maturity.loc[
        active
        & days.notna()
        & days.gt(365)
    ] = "Более года"

    work["maturity_bucket"] = maturity

    # ================================================================
    # ПРОФИЛЬ ПОГАШЕНИЯ
    # ================================================================

    work["repayment_profile"] = "Не задан"

    principal_first = (
        work.get(
            "repay_principal_first",
            False,
        )
        .astype(bool)
    )

    interest_first = (
        work.get(
            "repay_interest_first",
            False,
        )
        .astype(bool)
    )

    work.loc[
        principal_first,
        "repayment_profile",
    ] = "Сначала тело"

    work.loc[
        interest_first,
        "repayment_profile",
    ] = "Сначала проценты"

    both = (
        principal_first
        & interest_first
    )

    work.loc[
        both,
        "repayment_profile",
    ] = "Смешанный"

    return work


def apply_filters(
    df: pd.DataFrame,
    *,
    counterparties: list[str] | None = None,
    contract_types: list[str] | None = None,
    currencies: list[str] | None = None,
    statuses: list[str] | None = None,
) -> pd.DataFrame:
    if df.empty:
        return df.copy()

    work = df.copy()

    if counterparties:
        work = work[
            work["counterparty_name"]
            .astype(str)
            .isin(counterparties)
        ]

    if contract_types:
        work = work[
            work["contract_type"]
            .astype(str)
            .isin(contract_types)
        ]

    if currencies:
        work = work[
            work["currency"]
            .astype(str)
            .isin(currencies)
        ]

    if statuses:
        work = work[
            work["status"]
            .astype(str)
            .isin(statuses)
        ]

    return work.reset_index(drop=True)


def calculate_kpis(
    df: pd.DataFrame,
) -> dict[str, float | int | None]:
    empty = {
        "active_loans": 0,
        "total_debt": 0.0,
        "principal_debt": 0.0,
        "interest_debt": 0.0,
        "weighted_rate": None,
        "due_30": 0,
        "overdue": 0,
        "total_drawdown": 0.0,
    }

    if df.empty:
        return empty

    debt = pd.to_numeric(
        df["total_debt"],
        errors="coerce",
    ).fillna(0)

    principal = pd.to_numeric(
        df["ending_balance"],
        errors="coerce",
    ).fillna(0)

    interest = pd.to_numeric(
        df["interest_balance"],
        errors="coerce",
    ).fillna(0)

    rate = pd.to_numeric(
        df["rate"],
        errors="coerce",
    )

    weights = principal.clip(lower=0)

    weighted_rate = None
    valid = (
        rate.notna()
        & weights.gt(0)
    )

    if valid.any():
        weighted_rate = float(
            np.average(
                rate[valid],
                weights=weights[valid],
            )
        )

    status = (
        df["status"]
        .fillna("")
        .astype(str)
    )

    return {
        "active_loans": int(
            debt.gt(0.01).sum()
        ),
        "total_debt": float(debt.sum()),
        "principal_debt": float(principal.sum()),
        "interest_debt": float(interest.sum()),
        "weighted_rate": weighted_rate,
        "due_30": int(
            status.eq(
                "Погашение ≤ 30 дней"
            ).sum()
        ),
        "overdue": int(
            status.eq(
                "Просрочен"
            ).sum()
        ),
        "total_drawdown": float(
            pd.to_numeric(
                df["total_drawdown"],
                errors="coerce",
            )
            .fillna(0)
            .sum()
        ),
    }


def build_maturity_summary(
    df: pd.DataFrame,
) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(
            {
                "maturity_bucket": MATURITY_ORDER,
                "total_debt": [0.0] * len(MATURITY_ORDER),
                "contracts": [0] * len(MATURITY_ORDER),
            }
        )

    active = df[
        pd.to_numeric(
            df["total_debt"],
            errors="coerce",
        )
        .fillna(0)
        .gt(0.01)
    ].copy()

    summary = (
        active.groupby(
            "maturity_bucket",
            dropna=False,
        )
        .agg(
            total_debt=(
                "total_debt",
                "sum",
            ),
            contracts=(
                "contract_id",
                "nunique",
            ),
        )
        .reindex(
            MATURITY_ORDER,
            fill_value=0,
        )
        .reset_index()
    )

    return summary
