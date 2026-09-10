# gear/app/daily_sales/daily_brief/data/price_analysis.py

from __future__ import annotations

from datetime import timedelta

import pandas as pd

from gear.app.data.base import DashboardData


HISTORY_DAYS = 90


def _records(
    frame: pd.DataFrame,
) -> list[dict]:
    if frame is None or frame.empty:
        return []

    result = []

    for row in frame.to_dict("records"):
        clean = {}

        for key, value in row.items():
            if isinstance(
                value,
                pd.Timestamp,
            ):
                clean[key] = (
                    value.date().isoformat()
                )

            elif pd.isna(value):
                clean[key] = None

            elif hasattr(
                value,
                "item",
            ):
                try:
                    clean[key] = (
                        value.item()
                    )
                except Exception:
                    clean[key] = value

            else:
                clean[key] = value

        result.append(
            clean
        )

    return result


def get_price_analysis_data(
    report_date,
) -> dict:
    """
    История цены и скидки WB.

    Используется тот же агрегированный контур,
    что и основной dashboard продаж.

    amount:
        чистая выручка с НДС до СПП.

    retail_amount:
        сумма реализации покупателю по данным WB.

    discount_amount:
        разница между двумя контурами.

    discount_pct:
        разница относительно amount.

    ВАЖНО:
    если retail_amount и amount в исходном контуре
    имеют иной экономический смысл, формулу скидки
    необходимо синхронизировать с основной
    методологией daily_sales.
    """

    start_date = (
        report_date
        - timedelta(
            days=HISTORY_DAYS - 1
        )
    )

    with DashboardData() as dashboard:
        frame = (
            dashboard
            .get_dayly_sales_grid_data(
                start=start_date,
                end=report_date,
            )
        )

    if (
        frame is None
        or frame.empty
    ):
        return {
            "available": False,
            "rows": [],
        }

    work = frame.copy()

    numeric_columns = (
        "amount",
        "retail_amount",
        "total_net_sales",
        "margin_man",
        "amount_vatless",
    )

    for column in numeric_columns:
        if column not in work.columns:
            work[column] = 0

        work[column] = (
            pd.to_numeric(
                work[column],
                errors="coerce",
            )
            .fillna(0)
        )

    if "date_from" not in work.columns:
        return {
            "available": False,
            "rows": [],
        }

    work["date_from"] = pd.to_datetime(
        work["date_from"],
        errors="coerce",
    )

    work = (
        work
        .dropna(
            subset=["date_from"]
        )
        .sort_values("date_from")
        .reset_index(drop=True)
    )

    # -----------------------------------------------------------------
    # СКИДКА / РАЗНИЦА
    # -----------------------------------------------------------------

    work["discount_amount"] = (
        work["amount"]
        - work["retail_amount"]
    )

    work["discount_pct"] = (
        work["discount_amount"]
        / work["amount"]
        .replace(0, pd.NA)
        * 100
    )

    # -----------------------------------------------------------------
    # ЦЕНЫ НА ЕДИНИЦУ
    # -----------------------------------------------------------------

    qty = (
        work["total_net_sales"]
        .replace(0, pd.NA)
    )

    work["seller_avg_price"] = (
        work["amount"]
        / qty
    )

    work["buyer_avg_price"] = (
        work["retail_amount"]
        / qty
    )

    work[
        [
            "discount_pct",
            "seller_avg_price",
            "buyer_avg_price",
        ]
    ] = (
        work[
            [
                "discount_pct",
                "seller_avg_price",
                "buyer_avg_price",
            ]
        ]
        .replace(
            [float("inf"), float("-inf")],
            pd.NA,
        )
        .fillna(0)
    )

    # -----------------------------------------------------------------
    # MARGIN %
    # -----------------------------------------------------------------

    work["margin_pct"] = (
        work["margin_man"]
        / work["amount_vatless"]
        .replace(0, pd.NA)
        * 100
    )

    work["margin_pct"] = (
        work["margin_pct"]
        .replace(
            [float("inf"), float("-inf")],
            pd.NA,
        )
        .fillna(0)
    )

    # -----------------------------------------------------------------
    # ТЕКУЩИЙ ДЕНЬ
    # -----------------------------------------------------------------

    current = (
        work.iloc[-1]
        .to_dict()
        if not work.empty
        else {}
    )

    # -----------------------------------------------------------------
    # 14 ДНЕЙ / ПРЕДЫДУЩИЕ 14
    # -----------------------------------------------------------------

    recent = (
        work.tail(14)
        .copy()
    )

    previous = (
        work.iloc[
            max(
                len(work) - 28,
                0,
            ):
            max(
                len(work) - 14,
                0,
            )
        ]
        .copy()
    )

    def aggregate(
        part: pd.DataFrame,
    ) -> dict:
        if part.empty:
            return {}

        amount = float(
            part["amount"].sum()
        )

        retail = float(
            part["retail_amount"].sum()
        )

        qty_value = float(
            part["total_net_sales"].sum()
        )

        margin = float(
            part["margin_man"].sum()
        )

        vatless = float(
            part["amount_vatless"].sum()
        )

        discount_amount = (
            amount
            - retail
        )

        return {
            "amount": amount,
            "retail_amount": retail,

            "discount_amount": (
                discount_amount
            ),

            "discount_pct": (
                discount_amount
                / amount
                * 100
                if amount
                else 0
            ),

            "qty": qty_value,

            "seller_avg_price": (
                amount
                / qty_value
                if qty_value
                else 0
            ),

            "buyer_avg_price": (
                retail
                / qty_value
                if qty_value
                else 0
            ),

            "margin_man": margin,

            "margin_pct": (
                margin
                / vatless
                * 100
                if vatless
                else 0
            ),

            "days": len(part),
        }

    return {
        "available": True,

        "history_days": (
            HISTORY_DAYS
        ),

        "current": current,

        "recent_14": aggregate(
            recent
        ),

        "previous_14": aggregate(
            previous
        ),

        "rows": _records(
            work
        ),
    }