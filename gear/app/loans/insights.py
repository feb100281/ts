# gear/app/loans/insights.py

from __future__ import annotations

import pandas as pd

from .calculations import (
    build_maturity_summary,
)


# ---------------------------------------------------------------------
# Форматирование
# ---------------------------------------------------------------------


def _format_money(
    value: float | int | None,
) -> str:
    if value is None:
        return "—"

    try:
        value = float(value)
    except (TypeError, ValueError):
        return "—"

    absolute = abs(value)

    if absolute >= 1_000_000_000:
        return (
            f"{value / 1_000_000_000:.2f}"
            .replace(".", ",")
            + " млрд ₽"
        )

    if absolute >= 1_000_000:
        return (
            f"{value / 1_000_000:.2f}"
            .replace(".", ",")
            + " млн ₽"
        )

    if absolute >= 1_000:
        return (
            f"{value / 1_000:.1f}"
            .replace(".", ",")
            + " тыс. ₽"
        )

    return (
        f"{value:,.2f}"
        .replace(",", " ")
        .replace(".", ",")
        + " ₽"
    )


def _format_percent(
    value: float | None,
) -> str:
    if value is None:
        return "—"

    return (
        f"{value:.1f}"
        .replace(".", ",")
        + "%"
    )


def _format_date(
    value,
) -> str:
    date_value = pd.to_datetime(
        value,
        errors="coerce",
    )

    if pd.isna(date_value):
        return "—"

    return date_value.strftime(
        "%d.%m.%Y"
    )


# ---------------------------------------------------------------------
# Динамика задолженности
# ---------------------------------------------------------------------


def build_debt_dynamics_insight(
    df: pd.DataFrame,
) -> list[dict]:
    """
    Формирует автоматические выводы
    по графику динамики задолженности.

    Возвращает список словарей:

    [
        {
            "type": "positive | negative | warning | neutral",
            "title": "...",
            "text": "...",
        }
    ]
    """

    if df.empty:
        return [
            {
                "type": "neutral",
                "title": "Нет данных",
                "text": (
                    "За выбранный период "
                    "нет данных для анализа."
                ),
            }
        ]

    work = df.copy()

    work["date_from"] = pd.to_datetime(
        work["date_from"],
        errors="coerce",
    )

    for column in (
        "principal_debt",
        "interest_debt",
        "total_debt",
    ):
        work[column] = pd.to_numeric(
            work[column],
            errors="coerce",
        ).fillna(0)

    work = (
        work
        .dropna(
            subset=["date_from"]
        )
        .sort_values("date_from")
        .reset_index(drop=True)
    )

    if work.empty:
        return []

    # -------------------------------------------------------------
    # Начало / конец
    # -------------------------------------------------------------

    first = work.iloc[0]
    last = work.iloc[-1]

    start_total = float(
        first["total_debt"]
    )

    end_total = float(
        last["total_debt"]
    )

    change = (
        end_total
        - start_total
    )

    change_pct = None

    if start_total != 0:
        change_pct = (
            change
            / abs(start_total)
            * 100
        )

    # -------------------------------------------------------------
    # Максимум
    # -------------------------------------------------------------

    peak_idx = (
        work["total_debt"]
        .idxmax()
    )

    peak = work.loc[peak_idx]

    peak_value = float(
        peak["total_debt"]
    )

    peak_date = peak["date_from"]

    # -------------------------------------------------------------
    # Структура текущего долга
    # -------------------------------------------------------------

    principal_end = float(
        last["principal_debt"]
    )

    interest_end = float(
        last["interest_debt"]
    )

    principal_share = None
    interest_share = None

    if end_total != 0:
        principal_share = (
            principal_end
            / end_total
            * 100
        )

        interest_share = (
            interest_end
            / end_total
            * 100
        )

    # -------------------------------------------------------------
    # Движения
    # -------------------------------------------------------------

    work["debt_change"] = (
        work["total_debt"]
        .diff()
    )

    biggest_growth = (
        work.loc[
            work["debt_change"].idxmax()
        ]
        if work["debt_change"].notna().any()
        else None
    )

    biggest_reduction = (
        work.loc[
            work["debt_change"].idxmin()
        ]
        if work["debt_change"].notna().any()
        else None
    )

    insights: list[dict] = []

    # -------------------------------------------------------------
    # 1. Основной вывод
    # -------------------------------------------------------------

    if change < 0:
        insights.append(
            {
                "type": "positive",
                "title": (
                    "Задолженность снизилась"
                ),
                "text": (
                    f"За период общий долг "
                    f"сократился на "
                    f"{_format_money(abs(change))}"
                    + (
                        f" ({_format_percent(abs(change_pct))})"
                        if change_pct is not None
                        else ""
                    )
                    + f" — с {_format_money(start_total)} "
                    f"до {_format_money(end_total)}."
                ),
            }
        )

    elif change > 0:
        insights.append(
            {
                "type": "warning",
                "title": (
                    "Задолженность выросла"
                ),
                "text": (
                    f"За период общий долг "
                    f"увеличился на "
                    f"{_format_money(change)}"
                    + (
                        f" ({_format_percent(change_pct)})"
                        if change_pct is not None
                        else ""
                    )
                    + f" — с {_format_money(start_total)} "
                    f"до {_format_money(end_total)}."
                ),
            }
        )

    else:
        insights.append(
            {
                "type": "neutral",
                "title": (
                    "Долг не изменился"
                ),
                "text": (
                    "Общий размер задолженности "
                    "на начало и конец периода "
                    f"составляет {_format_money(end_total)}."
                ),
            }
        )

    # -------------------------------------------------------------
    # 2. Максимальная задолженность
    # -------------------------------------------------------------

    insights.append(
        {
            "type": "neutral",
            "title": "Пиковая задолженность",
            "text": (
                f"Максимальный общий долг "
                f"за период составил "
                f"{_format_money(peak_value)} "
                f"на {_format_date(peak_date)}."
            ),
        }
    )

    # -------------------------------------------------------------
    # 3. Структура
    # -------------------------------------------------------------

    if end_total > 0:
        insights.append(
            {
                "type": (
                    "warning"
                    if (
                        interest_share is not None
                        and interest_share >= 10
                    )
                    else "neutral"
                ),
                "title": (
                    "Структура текущего долга"
                ),
                "text": (
                    f"На конец периода основной долг "
                    f"составляет {_format_money(principal_end)}"
                    + (
                        f" ({_format_percent(principal_share)})"
                        if principal_share is not None
                        else ""
                    )
                    + ", начисленные проценты — "
                    f"{_format_money(interest_end)}"
                    + (
                        f" ({_format_percent(interest_share)})."
                        if interest_share is not None
                        else "."
                    )
                ),
            }
        )

    # -------------------------------------------------------------
    # 4. Самое крупное увеличение
    # -------------------------------------------------------------

    if (
        biggest_growth is not None
        and biggest_growth["debt_change"] > 0
    ):
        insights.append(
            {
                "type": "warning",
                "title": (
                    "Крупнейший рост долга"
                ),
                "text": (
                    f"Наибольшее увеличение "
                    f"за одну дату составило "
                    f"{_format_money(biggest_growth['debt_change'])} "
                    f"— {_format_date(biggest_growth['date_from'])}."
                ),
            }
        )

    # -------------------------------------------------------------
    # 5. Самое крупное погашение
    # -------------------------------------------------------------

    if (
        biggest_reduction is not None
        and biggest_reduction["debt_change"] < 0
    ):
        insights.append(
            {
                "type": "positive",
                "title": (
                    "Крупнейшее снижение долга"
                ),
                "text": (
                    f"Наибольшее сокращение "
                    f"за одну дату составило "
                    f"{_format_money(abs(biggest_reduction['debt_change']))} "
                    f"— {_format_date(biggest_reduction['date_from'])}."
                ),
            }
        )

    return insights



def build_counterparty_debt_insight(
    df: pd.DataFrame,
) -> list[dict]:
    """
    Автоматические выводы по структуре долга
    в разрезе контрагентов.
    """

    if df.empty:
        return [
            {
                "type": "neutral",
                "title": "Нет данных",
                "text": (
                    "Нет данных для анализа "
                    "задолженности по контрагентам."
                ),
            }
        ]

    work = df.copy()

    work["counterparty_name"] = (
        work["counterparty_name"]
        .fillna("Без контрагента")
        .astype(str)
        .str.strip()
    )

    work["total_debt"] = pd.to_numeric(
        work["total_debt"],
        errors="coerce",
    ).fillna(0)

    summary = (
        work.groupby(
            "counterparty_name",
            as_index=False,
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
        .sort_values(
            "total_debt",
            ascending=False,
        )
        .reset_index(drop=True)
    )

    total_debt = float(
        summary["total_debt"].sum()
    )

    if total_debt <= 0:
        return [
            {
                "type": "neutral",
                "title": "Задолженность отсутствует",
                "text": (
                    "На выбранную дату общий долг "
                    "по контрагентам отсутствует."
                ),
            }
        ]

    active = summary[
        summary["total_debt"] > 0.01
    ].copy()

    if active.empty:
        return []

    active["share_pct"] = (
        active["total_debt"]
        / total_debt
        * 100
    )

    insights = []

    # =============================================================
    # 1. Крупнейший контрагент
    # =============================================================

    largest = active.iloc[0]

    largest_name = (
        largest["counterparty_name"]
    )

    largest_debt = float(
        largest["total_debt"]
    )

    largest_share = float(
        largest["share_pct"]
    )

    insight_type = (
        "warning"
        if largest_share >= 50
        else "neutral"
    )

    insights.append(
        {
            "type": insight_type,
            "title": (
                "Крупнейший кредитор"
            ),
            "text": (
                f"{largest_name} — "
                f"{_format_money(largest_debt)}, "
                f"или {_format_percent(largest_share)} "
                f"от общего долга."
            ),
        }
    )

    # =============================================================
    # 2. Концентрация Top-3
    # =============================================================

    top_3 = active.head(3)

    top_3_debt = float(
        top_3["total_debt"].sum()
    )

    top_3_share = (
        top_3_debt
        / total_debt
        * 100
    )

    if top_3_share >= 75:
        concentration_type = "warning"
    else:
        concentration_type = "neutral"

    insights.append(
        {
            "type": concentration_type,
            "title": (
                "Концентрация задолженности"
            ),
            "text": (
                f"На три крупнейших контрагента "
                f"приходится "
                f"{_format_percent(top_3_share)} "
                f"портфеля — "
                f"{_format_money(top_3_debt)}."
            ),
        }
    )

    # =============================================================
    # 3. Количество контрагентов
    # =============================================================

    insights.append(
        {
            "type": "neutral",
            "title": (
                "Структура портфеля"
            ),
            "text": (
                f"Ненулевая задолженность "
                f"сформирована перед "
                f"{len(active)} контрагентами. "
                f"Средний долг на одного "
                f"контрагента составляет "
                f"{_format_money(total_debt / len(active))}."
            ),
        }
    )

    # =============================================================
    # 4. Мелкие остатки
    # =============================================================

    small = active[
        active["total_debt"] < 100_000
    ]

    if not small.empty:

        small_total = float(
            small["total_debt"].sum()
        )

        insights.append(
            {
                "type": "neutral",
                "title": (
                    "Мелкие остатки задолженности"
                ),
                "text": (
                    f"У {len(small)} контрагентов "
                    f"остаток долга менее 100 тыс. ₽. "
                    f"Совокупно — "
                    f"{_format_money(small_total)}."
                ),
            }
        )

    return insights



def _counterparties_for_maturity_bucket(
    df: pd.DataFrame,
    bucket_name: str,
    top_n: int = 3,
) -> list[dict]:
    """
    Возвращает крупнейших контрагентов
    внутри заданной категории срока погашения.

    Результат:

    [
        {
            "name": "...",
            "debt": 1000000,
        }
    ]
    """

    if df.empty:
        return []

    required_columns = {
        "maturity_bucket",
        "counterparty_name",
        "total_debt",
    }

    if not required_columns.issubset(
        df.columns
    ):
        return []

    work = df.copy()

    work["total_debt"] = pd.to_numeric(
        work["total_debt"],
        errors="coerce",
    ).fillna(0)

    work["counterparty_name"] = (
        work["counterparty_name"]
        .fillna("Без контрагента")
        .astype(str)
        .str.strip()
    )

    bucket_df = work[
        work["maturity_bucket"]
        == bucket_name
    ].copy()

    bucket_df = bucket_df[
        bucket_df["total_debt"] > 0.01
    ]

    if bucket_df.empty:
        return []

    summary = (
        bucket_df.groupby(
            "counterparty_name",
            as_index=False,
        )
        .agg(
            debt=(
                "total_debt",
                "sum",
            )
        )
        .sort_values(
            "debt",
            ascending=False,
        )
        .head(top_n)
        .reset_index(drop=True)
    )

    return summary.to_dict(
        "records"
    )
    
    
def _format_counterparties(
    counterparties: list[dict],
) -> str:
    """
    Формирует красивый текст:

    Иванов — 10 млн ₽,
    ООО Ромашка — 5 млн ₽.
    """

    if not counterparties:
        return ""

    parts = []

    for item in counterparties:

        name = str(
            item.get(
                "counterparty_name",
                "",
            )
            or ""
        ).strip()

        debt = item.get(
            "debt",
            0,
        )

        if not name:
            continue

        parts.append(
            f"{name} — "
            f"{_format_money(debt)}"
        )

    return ", ".join(parts)



def build_maturity_insight(
    df: pd.DataFrame,
) -> list[dict]:
    """
    Автоматический анализ структуры
    задолженности по срокам погашения.

    Анализирует:
    - просроченную задолженность;
    - ближайшие 90 дней;
    - среднесрочную нагрузку;
    - долгосрочную часть;
    - крупнейшую зону концентрации;
    - основных контрагентов внутри сроков;
    - договоры без даты погашения.

    "Без даты" контролируется в выводах,
    но намеренно не выводится отдельной
    колонкой на графике.
    """

    if df.empty:
        return [
            {
                "type": "neutral",
                "title": "Нет данных",
                "text": (
                    "Нет данных для анализа "
                    "сроков погашения."
                ),
            }
        ]

    summary = build_maturity_summary(
        df
    )

    if summary.empty:
        return [
            {
                "type": "neutral",
                "title": "Нет данных",
                "text": (
                    "Нет данных для анализа "
                    "сроков погашения."
                ),
            }
        ]

    work = summary.copy()

    work["total_debt"] = pd.to_numeric(
        work["total_debt"],
        errors="coerce",
    ).fillna(0)

    work["contracts"] = pd.to_numeric(
        work["contracts"],
        errors="coerce",
    ).fillna(0)

    # =============================================================
    # Общий долг
    # =============================================================

    total_debt = float(
        pd.to_numeric(
            df["total_debt"],
            errors="coerce",
        )
        .fillna(0)
        .clip(lower=0)
        .sum()
    )

    if total_debt <= 0:
        return [
            {
                "type": "positive",
                "title": (
                    "Задолженность отсутствует"
                ),
                "text": (
                    "На выбранную дату "
                    "непогашенная задолженность "
                    "отсутствует."
                ),
            }
        ]

    # =============================================================
    # Helpers
    # =============================================================

    def get_bucket(
        bucket_name: str,
    ) -> tuple[float, int]:

        rows = work[
            work["maturity_bucket"]
            == bucket_name
        ]

        if rows.empty:
            return 0.0, 0

        row = rows.iloc[0]

        return (
            float(
                row["total_debt"]
            ),
            int(
                row["contracts"]
            ),
        )

    def share(
        value: float,
    ) -> float:

        if total_debt <= 0:
            return 0.0

        return (
            value
            / total_debt
            * 100
        )

    # =============================================================
    # Категории
    # =============================================================

    (
        overdue_debt,
        overdue_contracts,
    ) = get_bucket(
        "Просрочено"
    )

    (
        due_30_debt,
        due_30_contracts,
    ) = get_bucket(
        "До 30 дней"
    )

    (
        due_90_debt,
        due_90_contracts,
    ) = get_bucket(
        "31–90 дней"
    )

    (
        due_180_debt,
        due_180_contracts,
    ) = get_bucket(
        "91–180 дней"
    )

    (
        due_365_debt,
        due_365_contracts,
    ) = get_bucket(
        "181–365 дней"
    )

    (
        long_debt,
        long_contracts,
    ) = get_bucket(
        "Более года"
    )

    (
        no_date_debt,
        no_date_contracts,
    ) = get_bucket(
        "Без даты"
    )

    insights: list[dict] = []

    # =============================================================
    # 1. Просрочка
    # =============================================================

    if overdue_debt > 0:

        overdue_share = share(
            overdue_debt
        )

        overdue_counterparties = (
            _counterparties_for_maturity_bucket(
                df,
                "Просрочено",
                top_n=3,
            )
        )

        counterparties_text = (
            _format_counterparties(
                overdue_counterparties
            )
        )

        text = (
            f"Просрочено "
            f"{_format_money(overdue_debt)} "
            f"по {overdue_contracts} "
            f"договорам — "
            f"{_format_percent(overdue_share)} "
            f"текущей задолженности."
        )

        if counterparties_text:

            text += (
                " Основные контрагенты: "
                f"{counterparties_text}."
            )

        insights.append(
            {
                "type": "negative",
                "title": (
                    "Есть просроченная "
                    "задолженность"
                ),
                "text": text,
            }
        )

    else:

        insights.append(
            {
                "type": "positive",
                "title": (
                    "Просроченная задолженность "
                    "отсутствует"
                ),
                "text": (
                    "На выбранную дату "
                    "обязательств с истёкшим "
                    "сроком погашения нет."
                ),
            }
        )

    # =============================================================
    # 2. Ближайшие 90 дней
    # =============================================================

    short_debt = (
        due_30_debt
        + due_90_debt
    )

    short_contracts = (
        due_30_contracts
        + due_90_contracts
    )

    if short_debt > 0:

        short_share = share(
            short_debt
        )

        # Собираем контрагентов
        # сразу из двух диапазонов.
        short_df = df[
            df["maturity_bucket"].isin(
                [
                    "До 30 дней",
                    "31–90 дней",
                ]
            )
        ].copy()

        short_counterparties = []

        if not short_df.empty:

            short_df[
                "total_debt"
            ] = pd.to_numeric(
                short_df["total_debt"],
                errors="coerce",
            ).fillna(0)

            short_counterparties = (
                short_df[
                    short_df[
                        "total_debt"
                    ] > 0.01
                ]
                .groupby(
                    "counterparty_name",
                    as_index=False,
                )
                .agg(
                    debt=(
                        "total_debt",
                        "sum",
                    )
                )
                .sort_values(
                    "debt",
                    ascending=False,
                )
                .head(3)
                .to_dict("records")
            )

        counterparties_text = (
            _format_counterparties(
                short_counterparties
            )
        )

        text = (
            f"В ближайшие 90 дней "
            f"к погашению приходится "
            f"{_format_money(short_debt)} "
            f"по {short_contracts} "
            f"договорам — "
            f"{_format_percent(short_share)} "
            f"портфеля."
        )

        if counterparties_text:

            text += (
                " Основные выплаты связаны "
                "с контрагентами: "
                f"{counterparties_text}."
            )

        insights.append(
            {
                "type": (
                    "warning"
                    if short_share >= 25
                    else "neutral"
                ),
                "title": (
                    "Погашения в ближайшие "
                    "90 дней"
                ),
                "text": text,
            }
        )

    # =============================================================
    # 3. Среднесрочная нагрузка 91–365 дней
    # =============================================================

    medium_debt = (
        due_180_debt
        + due_365_debt
    )

    medium_contracts = (
        due_180_contracts
        + due_365_contracts
    )

    if medium_debt > 0:

        medium_share = share(
            medium_debt
        )

        medium_df = df[
            df["maturity_bucket"].isin(
                [
                    "91–180 дней",
                    "181–365 дней",
                ]
            )
        ].copy()

        medium_counterparties = []

        if not medium_df.empty:

            medium_df[
                "total_debt"
            ] = pd.to_numeric(
                medium_df["total_debt"],
                errors="coerce",
            ).fillna(0)

            medium_counterparties = (
                medium_df[
                    medium_df[
                        "total_debt"
                    ] > 0.01
                ]
                .groupby(
                    "counterparty_name",
                    as_index=False,
                )
                .agg(
                    debt=(
                        "total_debt",
                        "sum",
                    )
                )
                .sort_values(
                    "debt",
                    ascending=False,
                )
                .head(3)
                .to_dict("records")
            )

        counterparties_text = (
            _format_counterparties(
                medium_counterparties
            )
        )

        text = (
            f"На период от 91 дня "
            f"до одного года приходится "
            f"{_format_money(medium_debt)} "
            f"по {medium_contracts} договорам — "
            f"{_format_percent(medium_share)} "
            f"текущей задолженности."
        )

        if counterparties_text:

            text += (
                " Основные контрагенты: "
                f"{counterparties_text}."
            )

        insights.append(
            {
                "type": "neutral",
                "title": (
                    "Среднесрочная нагрузка"
                ),
                "text": text,
            }
        )

    # =============================================================
    # 4. Долгосрочная часть
    # =============================================================

    if long_debt > 0:

        long_share = share(
            long_debt
        )

        long_counterparties = (
            _counterparties_for_maturity_bucket(
                df,
                "Более года",
                top_n=3,
            )
        )

        counterparties_text = (
            _format_counterparties(
                long_counterparties
            )
        )

        text = (
            f"Со сроком погашения "
            f"более года приходится "
            f"{_format_money(long_debt)} "
            f"по {long_contracts} договорам — "
            f"{_format_percent(long_share)} "
            f"текущей задолженности."
        )

        if counterparties_text:

            text += (
                " Основные контрагенты: "
                f"{counterparties_text}."
            )

        insights.append(
            {
                "type": "neutral",
                "title": (
                    "Долгосрочная часть портфеля"
                ),
                "text": text,
            }
        )

    # =============================================================
    # 5. Договоры без даты
    #
    # На графике НЕ показываем.
    # Но как контроль качества данных
    # обязательно оставляем.
    # =============================================================

    if no_date_debt > 0:

        no_date_share = share(
            no_date_debt
        )

        no_date_counterparties = (
            _counterparties_for_maturity_bucket(
                df,
                "Без даты",
                top_n=3,
            )
        )

        counterparties_text = (
            _format_counterparties(
                no_date_counterparties
            )
        )

        text = (
            f"Для {no_date_contracts} "
            f"договоров на сумму "
            f"{_format_money(no_date_debt)} "
            f"не указана дата погашения — "
            f"{_format_percent(no_date_share)} "
            f"портфеля."
        )

        if counterparties_text:

            text += (
                " Контрагенты: "
                f"{counterparties_text}."
            )

        insights.append(
            {
                "type": "warning",
                "title": (
                    "Есть договоры без "
                    "даты погашения"
                ),
                "text": text,
            }
        )

    # =============================================================
    # 6. Концентрация по сроку
    # =============================================================

    visible_summary = work[
        work["maturity_bucket"]
        != "Без даты"
    ].copy()

    visible_summary = visible_summary[
        visible_summary["total_debt"]
        > 0.01
    ]

    if not visible_summary.empty:

        largest = visible_summary.loc[
            visible_summary[
                "total_debt"
            ].idxmax()
        ]

        largest_bucket = str(
            largest[
                "maturity_bucket"
            ]
        )

        largest_debt = float(
            largest[
                "total_debt"
            ]
        )

        largest_share = share(
            largest_debt
        )

        # ---------------------------------------------------------
        # Не добавляем фактически тот же вывод,
        # если крупнейшая категория = "Более года",
        # потому что выше уже есть отдельный
        # подробный долгосрочный вывод.
        # ---------------------------------------------------------

        if largest_bucket != "Более года":

            largest_counterparties = (
                _counterparties_for_maturity_bucket(
                    df,
                    largest_bucket,
                    top_n=3,
                )
            )

            counterparties_text = (
                _format_counterparties(
                    largest_counterparties
                )
            )

            text = (
                f"Наибольшая часть долга "
                f"сосредоточена в категории "
                f"«{largest_bucket}» — "
                f"{_format_money(largest_debt)}, "
                f"или "
                f"{_format_percent(largest_share)} "
                f"портфеля."
            )

            if counterparties_text:

                text += (
                    " Основные контрагенты: "
                    f"{counterparties_text}."
                )

            insights.append(
                {
                    "type": "neutral",
                    "title": (
                        "Основной срок "
                        "концентрации"
                    ),
                    "text": text,
                }
            )

    return insights





def build_interest_flow_insight(
    df: pd.DataFrame,
    portfolio_df: pd.DataFrame | None = None,
) -> list[dict]:
    """
    Автоматический анализ процентной нагрузки.

    Анализирует:
    - начисленные проценты;
    - погашенные проценты;
    - коэффициент покрытия;
    - чистый поток;
    - месяцы накопления процентного долга;
    - максимальное начисление;
    - максимальное погашение;
    - последний месяц;
    - текущий долг по процентам.
    """

    if df.empty:
        return [
            {
                "type": "neutral",
                "title": "Нет данных",
                "text": (
                    "Нет данных для анализа "
                    "процентного потока."
                ),
            }
        ]

    work = df.copy()

    # =============================================================
    # Подготовка
    # =============================================================

    work["month"] = pd.to_datetime(
        work["month"],
        errors="coerce",
    )

    for column in (
        "interest_accrued",
        "interest_repaid",
    ):
        work[column] = pd.to_numeric(
            work[column],
            errors="coerce",
        ).fillna(0)

    work = (
        work
        .dropna(
            subset=["month"]
        )
        .sort_values("month")
        .reset_index(drop=True)
    )

    if work.empty:
        return []

    work["net_flow"] = (
        work["interest_accrued"]
        - work["interest_repaid"]
    )

    # =============================================================
    # Общие показатели
    # =============================================================

    total_accrued = float(
        work["interest_accrued"].sum()
    )

    total_repaid = float(
        work["interest_repaid"].sum()
    )

    net_flow = (
        total_accrued
        - total_repaid
    )

    coverage_ratio = None

    if total_accrued > 0:

        coverage_ratio = (
            total_repaid
            / total_accrued
            * 100
        )

    insights: list[dict] = []

    # =============================================================
    # 1. Общая способность покрывать начисления
    # =============================================================

    if total_accrued > 0:

        if coverage_ratio >= 100:

            insights.append(
                {
                    "type": "positive",

                    "title": (
                        "Начисленные проценты "
                        "полностью покрыты"
                    ),

                    "text": (
                        f"За выбранный период "
                        f"начислено "
                        f"{_format_money(total_accrued)}, "
                        f"погашено "
                        f"{_format_money(total_repaid)}. "
                        f"Коэффициент покрытия "
                        f"составляет "
                        f"{_format_percent(coverage_ratio)}."
                    ),
                }
            )

        elif coverage_ratio >= 80:

            insights.append(
                {
                    "type": "warning",

                    "title": (
                        "Начисления покрываются "
                        "не полностью"
                    ),

                    "text": (
                        f"За период начислено "
                        f"{_format_money(total_accrued)}, "
                        f"погашено "
                        f"{_format_money(total_repaid)}. "
                        f"Платежами покрыто "
                        f"{_format_percent(coverage_ratio)} "
                        f"начисленных процентов."
                    ),
                }
            )

        else:

            insights.append(
                {
                    "type": "negative",

                    "title": (
                        "Низкое покрытие "
                        "процентных начислений"
                    ),

                    "text": (
                        f"За период начислено "
                        f"{_format_money(total_accrued)}, "
                        f"а погашено только "
                        f"{_format_money(total_repaid)}. "
                        f"Покрытие составляет "
                        f"{_format_percent(coverage_ratio)}, "
                        f"что означает накопление "
                        f"процентной задолженности."
                    ),
                }
            )

    # =============================================================
    # 2. Чистый процентный поток
    # =============================================================

    if net_flow > 0.01:

        insights.append(
            {
                "type": "warning",

                "title": (
                    "Процентная задолженность "
                    "накапливается"
                ),

                "text": (
                    f"Начисления превысили "
                    f"погашения на "
                    f"{_format_money(net_flow)} "
                    f"за выбранный период."
                ),
            }
        )

    elif net_flow < -0.01:

        insights.append(
            {
                "type": "positive",

                "title": (
                    "Процентная задолженность "
                    "сокращается"
                ),

                "text": (
                    f"Погашения превысили "
                    f"начисления на "
                    f"{_format_money(abs(net_flow))} "
                    f"за выбранный период."
                ),
            }
        )

    # =============================================================
    # 3. Месяцы накопления долга
    # =============================================================

    accumulating = work[
        work["net_flow"] > 0.01
    ].copy()

    reducing = work[
        work["net_flow"] < -0.01
    ].copy()

    total_months = len(work)

    if total_months > 0:

        accumulating_count = len(
            accumulating
        )

        if accumulating_count > 0:

            accumulation_share = (
                accumulating_count
                / total_months
                * 100
            )

            insight_type = (
                "warning"
                if accumulation_share >= 50
                else "neutral"
            )

            insights.append(
                {
                    "type": insight_type,

                    "title": (
                        "Месяцы накопления процентов"
                    ),

                    "text": (
                        f"В {accumulating_count} "
                        f"из {total_months} месяцев "
                        f"начисления превышали "
                        f"погашения — "
                        f"{_format_percent(accumulation_share)} "
                        f"анализируемого периода."
                    ),
                }
            )

    # =============================================================
    # 4. Максимальное начисление
    # =============================================================

    if (
        work[
            "interest_accrued"
        ].max() > 0
    ):

        max_accrued_row = work.loc[
            work[
                "interest_accrued"
            ].idxmax()
        ]

        max_accrued = float(
            max_accrued_row[
                "interest_accrued"
            ]
        )

        max_accrued_month = (
            max_accrued_row[
                "month"
            ]
        )

        insights.append(
            {
                "type": "neutral",

                "title": (
                    "Максимальная процентная "
                    "нагрузка"
                ),

                "text": (
                    f"Наибольшая сумма "
                    f"начисленных процентов "
                    f"зафиксирована "
                    f"{max_accrued_month.strftime('%m.%Y')} — "
                    f"{_format_money(max_accrued)}."
                ),
            }
        )

    # =============================================================
    # 5. Максимальное погашение
    # =============================================================

    if (
        work[
            "interest_repaid"
        ].max() > 0
    ):

        max_repaid_row = work.loc[
            work[
                "interest_repaid"
            ].idxmax()
        ]

        max_repaid = float(
            max_repaid_row[
                "interest_repaid"
            ]
        )

        max_repaid_month = (
            max_repaid_row[
                "month"
            ]
        )

        insights.append(
            {
                "type": "positive",

                "title": (
                    "Максимальное погашение "
                    "процентов"
                ),

                "text": (
                    f"Крупнейший объём "
                    f"погашения процентов "
                    f"пришёлся на "
                    f"{max_repaid_month.strftime('%m.%Y')} — "
                    f"{_format_money(max_repaid)}."
                ),
            }
        )

    # =============================================================
    # 6. Последний месяц
    # =============================================================

    last = work.iloc[-1]

    last_month = last[
        "month"
    ]

    last_accrued = float(
        last[
            "interest_accrued"
        ]
    )

    last_repaid = float(
        last[
            "interest_repaid"
        ]
    )

    last_net = float(
        last[
            "net_flow"
        ]
    )

    if last_net > 0.01:

        last_type = "warning"

        last_description = (
            "начисления превысили "
            "погашения"
        )

    elif last_net < -0.01:

        last_type = "positive"

        last_description = (
            "погашения превысили "
            "начисления"
        )

    else:

        last_type = "neutral"

        last_description = (
            "начисления и погашения "
            "были практически равны"
        )

    insights.append(
        {
            "type": last_type,

            "title": (
                "Последний месяц"
            ),

            "text": (
                f"В {last_month.strftime('%m.%Y')} "
                f"начислено "
                f"{_format_money(last_accrued)}, "
                f"погашено "
                f"{_format_money(last_repaid)}; "
                f"{last_description}."
            ),
        }
    )

    # =============================================================
    # 7. Текущий долг по процентам
    #
    # Берём из snapshot портфеля,
    # а не из monthly flow.
    # =============================================================

    if (
        portfolio_df is not None
        and not portfolio_df.empty
        and "interest_balance"
        in portfolio_df.columns
    ):

        current_interest_debt = float(
            pd.to_numeric(
                portfolio_df[
                    "interest_balance"
                ],
                errors="coerce",
            )
            .fillna(0)
            .clip(lower=0)
            .sum()
        )

        if current_interest_debt > 0.01:

            insights.append(
                {
                    "type": (
                        "warning"
                        if net_flow > 0
                        else "neutral"
                    ),

                    "title": (
                        "Текущий долг "
                        "по процентам"
                    ),

                    "text": (
                        f"На дату среза "
                        f"непогашенный процентный "
                        f"долг составляет "
                        f"{_format_money(current_interest_debt)}."
                    ),
                }
            )

    return insights