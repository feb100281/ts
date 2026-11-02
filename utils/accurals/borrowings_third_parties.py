# /opt/wb_jobs/accurals/borrowings_third_parties.py
from __future__ import annotations

from datetime import date
from typing import Any

import numpy as np
import pandas as pd
from psycopg.rows import dict_row


ADJUSTMENTS_TABLE = "public.grossbook_loanadjustment"

# Разнесение по статьям CF (параметр договора «Разнесение по статьям CF»)
CF_PRINCIPAL_CODE = "321100"     # Погашение тела кредитов и займов
CF_INTEREST_CODE = "321200"      # Оплата процентов по кредитам и займам


def _safe_number(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _flag(value: Any) -> bool:
    """Флаг из param_json: true / "true" / 1 / "да"."""
    if isinstance(value, str):
        return value.strip().lower() in ("true", "1", "да", "yes")
    return bool(value)


def _evaluate_expression(
    expression: Any,
    *,
    key_rate: np.ndarray,
    n: int,
) -> np.ndarray:
    """
    Поддерживает прежние параметры договоров:
    - обычное число: 19.25
    - строку-выражение, использующую key_rate
    """
    if isinstance(expression, (int, float, np.integer, np.floating)):
        return np.full(n, float(expression), dtype=float)

    text = str(expression).strip()

    try:
        value = float(text)
        return np.full(n, value, dtype=float)
    except ValueError:
        pass

    # Сохраняем совместимость со старыми выражениями ставок:
    # float(...), int(...), round(...), np.where(...), key_rate и т. д.
    value = eval(
        text,
        {
            "np": np,
            "key_rate": key_rate,
        },
    )

    if np.isscalar(value):
        return np.full(n, float(value), dtype=float)

    result = np.asarray(value, dtype=float)

    if len(result) != n:
        raise ValueError(
            "Выражение ставки вернуло массив неправильной длины: "
            f"{len(result)} вместо {n}."
        )

    return result


def _parse_due_date(value: Any) -> pd.Timestamp:
    """
    Старые параметры могут хранить дату как:
    - date(2026, 7, 30)
    - '2026-07-30'
    - Timestamp(...)
    """
    if isinstance(value, (date, pd.Timestamp)):
        return pd.Timestamp(value).normalize()

    text = str(value).strip()

    parsed = pd.to_datetime(
        text.strip("'\""),
        errors="coerce",
    )

    if pd.notna(parsed):
        return pd.Timestamp(parsed).normalize()

    allowed_globals = {
        "__builtins__": {},
    }
    allowed_locals = {
        "date": date,
        "pd": pd,
    }

    evaluated = eval(
        text,
        allowed_globals,
        allowed_locals,
    )

    parsed = pd.to_datetime(
        evaluated,
        errors="raise",
    )

    return pd.Timestamp(parsed).normalize()


def _get_cashflow(
    conn,
    contract_id: int,
) -> pd.DataFrame:
    # cr_principal / cr_interest — части погашения со статьёй тела / процентов;
    # используются, только если у договора включено «Разнесение по статьям CF»
    query = """
        SELECT
            f.date_from::date AS date_from,
            SUM(COALESCE(f.dt, 0)) AS dt,
            SUM(COALESCE(f.cr, 0)) AS cr,
            SUM(CASE WHEN s.code::text = %s THEN COALESCE(f.cr, 0) ELSE 0 END)
                AS cr_principal,
            SUM(CASE WHEN s.code::text = %s THEN COALESCE(f.cr, 0) ELSE 0 END)
                AS cr_interest,
            STRING_AGG(
                NULLIF(f.description, ''),
                ', '
                ORDER BY f.description
            ) AS description
        FROM gl.fact f
        LEFT JOIN public.corporate_cfitems s ON s.id = f.subconto_id
        WHERE f.contract_id = %s
        GROUP BY f.date_from::date
        ORDER BY f.date_from::date
    """

    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            query,
            (CF_PRINCIPAL_CODE, CF_INTEREST_CODE, contract_id),
        )
        rows = cur.fetchall()

    if not rows:
        return pd.DataFrame(
            columns=[
                "date_from",
                "dt",
                "cr",
                "cr_principal",
                "cr_interest",
                "description",
            ],
        )

    result = pd.DataFrame(rows)
    result["date_from"] = pd.to_datetime(
        result["date_from"],
    ).dt.normalize()
    for col in ("dt", "cr", "cr_principal", "cr_interest"):
        result[col] = pd.to_numeric(
            result[col],
            errors="coerce",
        ).fillna(0.0)
    result["description"] = result["description"].fillna("")

    return result


def _get_adjustments(
    conn,
    contract_id: int,
) -> pd.DataFrame:
    query = f"""
        SELECT
            id,
            adjustment_date::date AS adjustment_date,
            principal_balance,
            interest_balance,
            reason,
            comment
        FROM {ADJUSTMENTS_TABLE}
        WHERE
            contract_id = %s
            AND is_active = TRUE
        ORDER BY
            adjustment_date,
            id
    """

    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            query,
            (contract_id,),
        )
        rows = cur.fetchall()

    if not rows:
        return pd.DataFrame(
            columns=[
                "id",
                "adjustment_date",
                "principal_balance",
                "interest_balance",
                "reason",
                "comment",
            ],
        )

    result = pd.DataFrame(rows)
    result["adjustment_date"] = pd.to_datetime(
        result["adjustment_date"],
    ).dt.normalize()

    # В Django суммы хранятся в валюте договора.
    # В borrowings_tp и gl.fact используются минимальные единицы / копейки.
    result["principal_balance"] = (
        pd.to_numeric(
            result["principal_balance"],
            errors="raise",
        )
        * 100.0
    )
    result["interest_balance"] = (
        pd.to_numeric(
            result["interest_balance"],
            errors="raise",
        )
        * 100.0
    )

    return result


def _get_key_rate(
    conn,
    days_range: pd.DatetimeIndex,
) -> np.ndarray:
    query = """
        SELECT
            date,
            key_rate
        FROM public.macro_keyrate
        ORDER BY date
    """

    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(query)
        rows = cur.fetchall()

    if not rows:
        raise RuntimeError(
            "Таблица public.macro_keyrate пуста."
        )

    key_rate_df = pd.DataFrame(rows)
    key_rate_df["date"] = pd.to_datetime(
        key_rate_df["date"],
    ).dt.normalize()
    key_rate_df["key_rate"] = pd.to_numeric(
        key_rate_df["key_rate"],
        errors="raise",
    )

    key_rate_df = (
        key_rate_df
        .drop_duplicates(
            subset=["date"],
            keep="last",
        )
        .set_index("date")
        .sort_index()
    )

    series = key_rate_df["key_rate"].reindex(
        days_range,
        method="ffill",
    )

    if series.isna().any():
        series = series.bfill()

    if series.isna().any():
        raise RuntimeError(
            "Не удалось подобрать ключевую ставку для части дат."
        )

    return series.to_numpy(
        dtype=float,
    )


def _build_adjustment_map(
    adjustments: pd.DataFrame,
) -> dict[pd.Timestamp, dict]:
    result: dict[pd.Timestamp, dict] = {}

    if adjustments.empty:
        return result

    for row in adjustments.to_dict("records"):
        day = pd.Timestamp(
            row["adjustment_date"],
        ).normalize()

        # Ограничение БД не позволяет две активные корректировки
        # одного договора на одну дату. keep-last оставлен как защита.
        result[day] = row

    return result


def _allocate(
    *,
    repayment: float,
    tagged_principal: float,
    tagged_interest: float,
    principal_available: float,
    due_interest: float,
    interest_first: bool,
    by_items: bool,
) -> tuple[float, float]:
    """Делит платёж дня на (тело, проценты).

    by_items=False — как раньше: весь платёж по профилю договора.
    by_items=True — сумма со статьёй тела (321100) гасит тело, со статьёй
    процентов (321200) — проценты; остаток без статьи — по профилю.
    Переплата сверх долга остаётся на процентах (отрицательный остаток — аванс).
    """
    if not by_items:
        if interest_first:
            to_int = min(repayment, due_interest)
            to_body = min(repayment - to_int, principal_available)
        else:
            to_body = min(repayment, principal_available)
            to_int = min(repayment - to_body, due_interest)
        return to_body, to_int

    t_int = max(min(tagged_interest, repayment), 0.0)
    t_body = max(min(tagged_principal, repayment - t_int), 0.0)
    to_int = t_int
    to_body = min(t_body, principal_available)
    rest = repayment - to_int - to_body          # без статьи + переплата тела

    int_left = max(due_interest - to_int, 0.0)
    body_left = max(principal_available - to_body, 0.0)
    if interest_first:
        x = min(rest, int_left)
        to_int += x
        rest -= x
        x = min(rest, body_left)
        to_body += x
        rest -= x
    else:
        x = min(rest, body_left)
        to_body += x
        rest -= x
        x = min(rest, int_left)
        to_int += x
        rest -= x
    to_int += rest                               # переплата — аванс по процентам
    return to_body, to_int


def _delete_existing_contract_rows(
    conn,
    contract_id: int,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
                DELETE FROM gl.borrowings_tp
                WHERE contract_id = %s
            """,
            (contract_id,),
        )


def insert_borrowings_tp(
    conn,
    final: dict,
) -> None:
    cols = [
        "date_from",
        "contract_id",
        "contract_amount",
        "available_amount",
        "drawdown_amount",
        "bb",
        "rate",
        "interest_accrued",
        "principal_repayment",
        "interest_repayment",
        "repaid_amount",
        "eb",
        "interest_balance",
        "total_debt",
        "operation_description",
        "interest_description",
    ]

    int_cols = {
        "contract_id",
        "contract_amount",
        "available_amount",
        "drawdown_amount",
        "bb",
        "interest_accrued",
        "principal_repayment",
        "interest_repayment",
        "repaid_amount",
        "eb",
        "interest_balance",
        "total_debt",
    }

    n = len(
        final["date_from"],
    )

    with conn.cursor() as cur:
        with cur.copy(
            """
                COPY gl.borrowings_tp (
                    date_from,
                    contract_id,
                    contract_amount,
                    available_amount,
                    drawdown_amount,
                    bb,
                    rate,
                    interest_accrued,
                    principal_repayment,
                    interest_repayment,
                    repaid_amount,
                    eb,
                    interest_balance,
                    total_debt,
                    operation_description,
                    interest_description
                )
                FROM STDIN
            """
        ) as copy:
            for i in range(n):
                row = []

                for col in cols:
                    value = final[col][i]

                    if hasattr(
                        value,
                        "item",
                    ):
                        value = value.item()

                    if col in int_cols and value is not None:
                        value = int(value)

                    row.append(value)

                copy.write_row(row)


def borrowing_third_party(
    conn,
    **args,
):
    """
    Полностью пересчитывает один договор.

    Последовательность дня:
    1. Берём остаток прошлого дня.
    2. Начисляем проценты на тело на начало дня.
    3. Учитываем выдачу/платёж текущего дня.
    4. Распределяем платёж: по профилю договора или, если включено
       «Разнесение по статьям CF», по статьям 321100 / 321200
       (остаток без статьи — по профилю).
    5. Если на дату есть LoanAdjustment —
       принудительно устанавливаем остатки на конец дня.
    6. Со следующего дня проценты считаются уже от исправленного тела.
    """
    param = args.get(
        "params_json",
    ) or {}

    contract_id = int(
        args["contract_id"],
    )

    cashflow = _get_cashflow(
        conn,
        contract_id,
    )
    adjustments = _get_adjustments(
        conn,
        contract_id,
    )

    explicit_start = args.get(
        "date_start",
    )

    possible_start_dates = []

    if explicit_start:
        possible_start_dates.append(
            pd.to_datetime(
                explicit_start,
            ).normalize(),
        )

    if not cashflow.empty:
        possible_start_dates.append(
            cashflow["date_from"].min(),
        )

    if not adjustments.empty:
        possible_start_dates.append(
            adjustments["adjustment_date"].min(),
        )

    if not possible_start_dates:
        raise ValueError(
            f"У договора {contract_id} нет движений, "
            "корректировок и даты начала."
        )

    date_start = min(
        possible_start_dates,
    )

    date_due = _parse_due_date(
        param["Дата погашения"],
    )

    today = pd.Timestamp.today().normalize()

    possible_finish_dates = [
        date_due,
        today,
    ]

    if not cashflow.empty:
        possible_finish_dates.append(
            cashflow["date_from"].max(),
        )

    if not adjustments.empty:
        possible_finish_dates.append(
            adjustments["adjustment_date"].max(),
        )

    date_finish = max(
        possible_finish_dates,
    )

    days_range = pd.date_range(
        start=date_start,
        end=date_finish,
        freq="D",
    )

    n = len(
        days_range,
    )

    days_in_year = np.where(
        days_range.is_leap_year,
        366.0,
        365.0,
    )

    key_rate = _get_key_rate(
        conn,
        days_range,
    )

    rate = _evaluate_expression(
        param["Ставка"],
        key_rate=key_rate,
        n=n,
    )

    penalty_rate = eval(
        str(
            param.get(
                "Штрафной процент",
                0,
            )
        )
    )

    # Штрафной процент указан за один день.
    # После даты погашения начисляется penalty_rate % ежедневно.
    after_due_mask = days_range > date_due

    if penalty_rate:
        rate = rate.copy()
        rate[after_due_mask] = (
            float(penalty_rate)
            * days_in_year[after_due_mask]
        )

    calendar_df = pd.DataFrame(
        {
            "date_from": days_range,
        },
    )

    if cashflow.empty:
        df = calendar_df.copy()
        df["dt"] = 0.0
        df["cr"] = 0.0
        df["cr_principal"] = 0.0
        df["cr_interest"] = 0.0
        df["description"] = ""
    else:
        df = calendar_df.merge(
            cashflow,
            on="date_from",
            how="left",
        )
        for col in ("dt", "cr", "cr_principal", "cr_interest"):
            df[col] = df[col].fillna(0.0)
        df["description"] = df["description"].fillna("")

    contract_amount_value = _safe_number(
        param.get(
            "Сумма по договору",
            0,
        ),
    ) * 100.0

    contract_amount = np.full(
        n,
        contract_amount_value,
        dtype=float,
    )

    drawdown_amount = df["dt"].to_numpy(
        dtype=float,
    )
    repaid_amount = df["cr"].to_numpy(
        dtype=float,
    )
    repaid_principal_tagged = df["cr_principal"].to_numpy(
        dtype=float,
    )
    repaid_interest_tagged = df["cr_interest"].to_numpy(
        dtype=float,
    )

    bb = np.zeros(
        n,
        dtype=float,
    )
    eb = np.zeros(
        n,
        dtype=float,
    )
    available_amount = np.zeros(
        n,
        dtype=float,
    )

    interest_accrued = np.zeros(
        n,
        dtype=float,
    )
    interest_balance = np.zeros(
        n,
        dtype=float,
    )
    interest_repayment = np.zeros(
        n,
        dtype=float,
    )
    principal_repayment = np.zeros(
        n,
        dtype=float,
    )

    drawdown_amount_cum = np.zeros(
        n,
        dtype=float,
    )
    principal_repayment_cum = np.zeros(
        n,
        dtype=float,
    )

    operation_description = df[
        "description"
    ].astype(str).to_numpy(
        dtype=object,
    )

    adjustment_map = _build_adjustment_map(
        adjustments,
    )

    repayment_profile = param.get(
        "Профиль погашения",
        {},
    ) or {}

    interest_first = bool(
        repayment_profile.get(
            "Сначало проценты",
            False,
        ),
    )

    # по умолчанию выключено: договор считается как раньше
    by_items = _flag(
        param.get(
            "Разнесение по статьям CF",
            False,
        ),
    )

    for i, current_day in enumerate(days_range):
        prev_eb = (
            0.0
            if i == 0
            else eb[i - 1]
        )
        prev_interest_balance = (
            0.0
            if i == 0
            else interest_balance[i - 1]
        )
        prev_drawdown_cum = (
            0.0
            if i == 0
            else drawdown_amount_cum[i - 1]
        )
        prev_principal_cum = (
            0.0
            if i == 0
            else principal_repayment_cum[i - 1]
        )

        bb[i] = prev_eb

        current_drawdown = max(
            drawdown_amount[i],
            0.0,
        )
        current_repayment = max(
            repaid_amount[i],
            0.0,
        )

        drawdown_amount_cum[i] = (
            prev_drawdown_cum
            + current_drawdown
        )

        # Проценты начисляются на остаток тела на начало дня.
        interest_accrued[i] = (
            bb[i]
            * (
                rate[i]
                / 100.0
                / days_in_year[i]
            )
        )

        due_interest = (
            prev_interest_balance
            + interest_accrued[i]
        )

        principal_available = (
            prev_eb
            + current_drawdown
        )

        principal_repayment[i], interest_repayment[i] = _allocate(
            repayment=current_repayment,
            tagged_principal=repaid_principal_tagged[i],
            tagged_interest=repaid_interest_tagged[i],
            principal_available=principal_available,
            due_interest=due_interest,
            interest_first=interest_first,
            by_items=by_items,
        )

        principal_repayment_cum[i] = (
            prev_principal_cum
            + principal_repayment[i]
        )

        eb[i] = max(
            principal_available
            - principal_repayment[i],
            0.0,
        )

        # по статьям CF переплата процентов остаётся авансом (минус),
        # в старом режиме — как раньше, не ниже нуля
        interest_balance[i] = (
            due_interest - interest_repayment[i]
            if by_items
            else max(due_interest - interest_repayment[i], 0.0)
        )

        adjustment = adjustment_map.get(
            pd.Timestamp(
                current_day,
            ).normalize(),
        )

        if adjustment:
            eb[i] = float(
                adjustment["principal_balance"],
            )
            interest_balance[i] = float(
                adjustment["interest_balance"],
            )

            adjustment_text = (
                "Ручная корректировка займа "
                f"#{adjustment['id']}: "
                f"тело {eb[i] / 100:,.2f}; "
                f"проценты {interest_balance[i] / 100:,.2f}. "
                f"{adjustment.get('comment') or ''}"
            )

            existing_description = str(
                operation_description[i]
                or ""
            ).strip()

            operation_description[i] = (
                f"{existing_description}; {adjustment_text}"
                if existing_description
                else adjustment_text
            )

        available_amount[i] = max(
            contract_amount[i]
            - drawdown_amount_cum[i]
            + principal_repayment_cum[i],
            0.0,
        )

    total_debt = (
        interest_balance
        + eb
    )

    interest_description = np.array(
        [
            (
                f"Проценты по займу: "
                f"{accrued / 100:,.2f}; "
                f"ставка {current_rate:.6g}% годовых; "
                f"база {current_bb / 100:,.2f}; "
                f"дней в году {int(year_days)}"
            )
            for (
                accrued,
                current_rate,
                year_days,
                current_bb,
            ) in zip(
                interest_accrued,
                rate,
                days_in_year,
                bb,
            )
        ],
        dtype=object,
    )

    final = {
        "date_from": days_range.to_numpy(),
        "contract_id": np.full(
            n,
            contract_id,
            dtype=int,
        ),
        "contract_amount": contract_amount,
        "available_amount": available_amount,
        "drawdown_amount": drawdown_amount,
        "bb": bb,
        "rate": rate,
        "interest_accrued": interest_accrued,
        "principal_repayment": principal_repayment,
        "interest_repayment": interest_repayment,
        "repaid_amount": repaid_amount,
        "eb": eb,
        "interest_balance": interest_balance,
        "total_debt": total_debt,
        "operation_description": operation_description,
        "interest_description": interest_description,
    }

    bigint_cols = [
        "contract_amount",
        "available_amount",
        "drawdown_amount",
        "bb",
        "interest_accrued",
        "principal_repayment",
        "interest_repayment",
        "repaid_amount",
        "eb",
        "interest_balance",
        "total_debt",
    ]

    for col in bigint_cols:
        final[col] = np.round(
            final[col],
        ).astype(
            np.int64,
        )

    # Удаление и новая вставка выполняются одной транзакцией.
    # Если COPY упадёт, conn.rollback() вернёт старые строки.
    try:
        _delete_existing_contract_rows(
            conn,
            contract_id,
        )

        insert_borrowings_tp(
            conn,
            final,
        )

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    return {
        "status": "ok",
        "contract_id": contract_id,
        "date_start": date_start.date().isoformat(),
        "date_finish": date_finish.date().isoformat(),
        "rows": n,
        "adjustments_used": len(
            adjustments,
        ),
        "by_items": by_items,
    }


def main(
    conn,
    **args,
):
    result = borrowing_third_party(
        conn,
        **args,
    )
    print(
        result,
    )
    return result


if __name__ == "__main__":
    raise RuntimeError(
        "Этот модуль должен запускаться через общий wb_jobs runner, "
        "который передаёт соединение conn и параметры договора."
    )
