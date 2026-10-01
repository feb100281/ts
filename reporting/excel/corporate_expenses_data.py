# reporting/excel/corporate_expenses_data.py
from django.db import connection
import pandas as pd


MONTH_NAMES_RU = {
    1: "Янв",
    2: "Фев",
    3: "Мар",
    4: "Апр",
    5: "Май",
    6: "Июн",
    7: "Июл",
    8: "Авг",
    9: "Сен",
    10: "Окт",
    11: "Ноя",
    12: "Дек",
}

TOTAL_ROW_KEY = "__TOTAL__"


def _extract_code(text: str) -> str:
    if not text:
        return ""
    text = str(text).strip()
    if not text:
        return ""
    parts = text.split(" ", 1)
    if parts and parts[0].isdigit():
        return parts[0]
    return ""


def _sort_key_by_code_and_name(value: str):
    value = "" if value is None else str(value).strip()
    code = _extract_code(value)
    if code.isdigit():
        return (0, int(code), value.lower())
    return (1, 10**9, value.lower())


def _normalize_group(value: str) -> str:
    value = "" if value is None else str(value).strip()
    return value or "Без группы"


def _normalize_item(value: str, group_value: str) -> str:
    value = "" if value is None else str(value).strip()
    if value:
        return value
    return f"{group_value} без детализации"


def _normalize_cp_name(value: str) -> str:
    value = "" if value is None else str(value).strip()
    return value or "Без контрагента"


def _make_parent_key(group_name: str) -> str:
    return f"grp::{group_name}"


def _make_child_key(group_name: str, item_name: str) -> str:
    return f"item::{group_name}|||{item_name}"


def _make_cp_key(group_name: str, item_name: str, cp_name: str) -> str:
    return f"cp::{group_name}|||{item_name}|||{cp_name}"


def get_corporate_expenses_report(date_to=None):
    """
    1.5 Корпоративные расходы (G&A)
    level 1 = cost_item_group
    level 2 = cost_item
    level 3 = cp_name
    """

    if date_to is None:
        with connection.cursor() as cur:
            cur.execute("SELECT MAX(date_from)::date FROM public.pl_for_csv")
            date_to = cur.fetchone()[0]

    date_to = pd.to_datetime(date_to).date()

    q = """
    SELECT
        EXTRACT(YEAR FROM p.date_from)::int AS year,
        EXTRACT(MONTH FROM p.date_from)::int AS month_num,
        COALESCE(NULLIF(TRIM(p.cost_item_group), ''), 'Без группы') AS cost_item_group,
        COALESCE(NULLIF(TRIM(p.cost_item), ''), '') AS cost_item,
        COALESCE(NULLIF(TRIM(p.cp_name), ''), 'Без контрагента') AS cp_name,
        SUM(p.amount)::numeric AS amount
    FROM public.pl_for_csv p
    WHERE p.date_from <= %s::date
      AND substring(p.account_name from '^\\d+') = '620000'
    GROUP BY
        EXTRACT(YEAR FROM p.date_from)::int,
        EXTRACT(MONTH FROM p.date_from)::int,
        COALESCE(NULLIF(TRIM(p.cost_item_group), ''), 'Без группы'),
        COALESCE(NULLIF(TRIM(p.cost_item), ''), ''),
        COALESCE(NULLIF(TRIM(p.cp_name), ''), 'Без контрагента')
    ORDER BY 1, 2, 3, 4, 5
    """

    with connection.cursor() as cur:
        cur.execute(q, [date_to])
        rows = cur.fetchall()
        columns = [col[0] for col in cur.description]

    df = pd.DataFrame(rows, columns=columns)

    if df.empty:
        return {
            "data": pd.DataFrame(),
            "year_groups": [],
            "row_meta": pd.DataFrame(columns=["display_name", "code", "level", "parent_row"]),
        }

    df["year"] = df["year"].astype(int)
    df["month_num"] = df["month_num"].astype(int)
    df["cost_item_group"] = df["cost_item_group"].apply(_normalize_group)
    df["cost_item"] = df.apply(
        lambda x: _normalize_item(x["cost_item"], x["cost_item_group"]),
        axis=1,
    )
    df["cp_name"] = df["cp_name"].apply(_normalize_cp_name)

    current_year = date_to.year
    current_month = date_to.month
    years = sorted(df["year"].unique())

    year_groups = []
    ordered_cols = []

    for year in years:
        if year == current_year:
            months = list(range(1, current_month + 1))
        else:
            months = sorted(df.loc[df["year"] == year, "month_num"].unique().tolist())

        month_cols = [f"{MONTH_NAMES_RU[m]} {year}" for m in months]
        total_col = f"Итого {year}"

        year_groups.append({
            "year": year,
            "months": months,
            "month_cols": month_cols,
            "total_col": total_col,
        })

        ordered_cols.extend(month_cols)
        ordered_cols.append(total_col)

    df["period_col"] = df.apply(
        lambda x: f"{MONTH_NAMES_RU[int(x['month_num'])]} {int(x['year'])}",
        axis=1
    )

    # level 3: контрагент
    cp_df = (
        df.groupby(
            ["cost_item_group", "cost_item", "cp_name", "period_col"],
            as_index=False
        )["amount"]
        .sum()
        .copy()
    )
    cp_df["row_key"] = cp_df.apply(
        lambda x: _make_cp_key(x["cost_item_group"], x["cost_item"], x["cp_name"]),
        axis=1
    )

    cp_pivot = cp_df.pivot_table(
        index="row_key",
        columns="period_col",
        values="amount",
        aggfunc="sum",
        fill_value=0,
    )

    # level 2: статья
    child_df = (
        df.groupby(["cost_item_group", "cost_item", "period_col"], as_index=False)["amount"]
        .sum()
        .copy()
    )
    child_df["row_key"] = child_df.apply(
        lambda x: _make_child_key(x["cost_item_group"], x["cost_item"]),
        axis=1
    )

    child_pivot = child_df.pivot_table(
        index="row_key",
        columns="period_col",
        values="amount",
        aggfunc="sum",
        fill_value=0,
    )

    # level 1: группа
    parent_df = (
        df.groupby(["cost_item_group", "period_col"], as_index=False)["amount"]
        .sum()
        .copy()
    )
    parent_df["row_key"] = parent_df["cost_item_group"].apply(_make_parent_key)

    parent_pivot = parent_df.pivot_table(
        index="row_key",
        columns="period_col",
        values="amount",
        aggfunc="sum",
        fill_value=0,
    )

    for col in ordered_cols:
        if col.startswith("Итого "):
            continue

        if col not in cp_pivot.columns:
            cp_pivot[col] = 0
        if col not in child_pivot.columns:
            child_pivot[col] = 0
        if col not in parent_pivot.columns:
            parent_pivot[col] = 0

    for group in year_groups:
        cp_pivot[group["total_col"]] = cp_pivot[group["month_cols"]].sum(axis=1)
        child_pivot[group["total_col"]] = child_pivot[group["month_cols"]].sum(axis=1)
        parent_pivot[group["total_col"]] = parent_pivot[group["month_cols"]].sum(axis=1)

    cp_pivot = cp_pivot.reindex(columns=ordered_cols)
    child_pivot = child_pivot.reindex(columns=ordered_cols)
    parent_pivot = parent_pivot.reindex(columns=ordered_cols)

    row_meta_rows = []
    ordered_row_keys = []

    unique_groups = (
        df[["cost_item_group"]]
        .drop_duplicates()
        .sort_values("cost_item_group", key=lambda s: s.map(_sort_key_by_code_and_name))
    )

    for _, grp in unique_groups.iterrows():
        group_name = grp["cost_item_group"]
        group_key = _make_parent_key(group_name)
        group_code = _extract_code(group_name)

        if group_key in parent_pivot.index:
            ordered_row_keys.append(group_key)
            row_meta_rows.append({
                "row_key": group_key,
                "display_name": group_name,
                "code": group_code,
                "level": 1,
                "parent_row": None,
            })

        group_children = (
            df.loc[df["cost_item_group"] == group_name, ["cost_item"]]
            .drop_duplicates()
            .sort_values("cost_item", key=lambda s: s.map(_sort_key_by_code_and_name))
        )

        for _, ch in group_children.iterrows():
            child_name = ch["cost_item"]
            child_key = _make_child_key(group_name, child_name)
            child_code = _extract_code(child_name)

            if child_key in child_pivot.index:
                ordered_row_keys.append(child_key)
                row_meta_rows.append({
                    "row_key": child_key,
                    "display_name": child_name,
                    "code": child_code,
                    "level": 2,
                    "parent_row": group_key,
                })

            cp_rows = (
                df.loc[
                    (df["cost_item_group"] == group_name) &
                    (df["cost_item"] == child_name),
                    ["cp_name"]
                ]
                .drop_duplicates()
                .sort_values("cp_name")
            )

            for _, cp in cp_rows.iterrows():
                cp_name = cp["cp_name"]
                cp_key = _make_cp_key(group_name, child_name, cp_name)

                if cp_key in cp_pivot.index:
                    ordered_row_keys.append(cp_key)
                    row_meta_rows.append({
                        "row_key": cp_key,
                        "display_name": cp_name,
                        "code": "",
                        "level": 3,
                        "parent_row": child_key,
                    })

    all_rows = pd.concat([parent_pivot, child_pivot, cp_pivot], axis=0)
    all_rows = all_rows[~all_rows.index.duplicated(keep="last")]
    result = all_rows.reindex(ordered_row_keys)

    if not result.empty:
        result = result.loc[(result.fillna(0) != 0).any(axis=1)].copy()

    row_meta = pd.DataFrame(row_meta_rows)
    if not row_meta.empty:
        row_meta = row_meta[row_meta["row_key"].isin(result.index)].copy()
        row_meta = row_meta.drop_duplicates(subset=["row_key"], keep="first")
        row_meta = row_meta.set_index("row_key")
    else:
        row_meta = pd.DataFrame(columns=["display_name", "code", "level", "parent_row"])

    # общий итог — только по самому нижнему уровню
    if not result.empty:
        if row_meta is not None and not row_meta.empty:
            detail_rows = row_meta[row_meta["level"] == 3].index.tolist()
            if detail_rows:
                total_values = result.loc[detail_rows].sum(axis=0)
            else:
                total_values = result.sum(axis=0)
        else:
            total_values = result.sum(axis=0)

        result.loc[TOTAL_ROW_KEY] = total_values

    result = result.where(pd.notna(result), None)

    return {
        "data": result,
        "year_groups": year_groups,
        "row_meta": row_meta,
    }