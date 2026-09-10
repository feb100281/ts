# # reporting/excel/cogs_realization_data.py

# from django.db import connection
# import pandas as pd


# MONTH_NAMES_RU = {
#     1: "Янв",
#     2: "Фев",
#     3: "Мар",
#     4: "Апр",
#     5: "Май",
#     6: "Июн",
#     7: "Июл",
#     8: "Авг",
#     9: "Сен",
#     10: "Окт",
#     11: "Ноя",
#     12: "Дек",
# }


# def _extract_code(text: str) -> str:
#     if not text:
#         return ""
#     text = str(text).strip()
#     if not text:
#         return ""
#     parts = text.split(" ", 1)
#     if parts and parts[0].isdigit():
#         return parts[0]
#     return ""


# def _normalize_group(value: str) -> str:
#     value = "" if value is None else str(value).strip()
#     return value or "Без группы"


# def _normalize_item(value: str, group_value: str) -> str:
#     value = "" if value is None else str(value).strip()
#     if value:
#         return value
#     return f"{group_value} без детализации"


# def get_cogs_realization_report(date_to=None):
#     """
#     Возвращает payload для листа 1.3 'Себестоимость реализации'.

#     Формат:
#     {
#         "data": DataFrame,
#         "year_groups": [...],
#         "row_meta": DataFrame(index=row_name, columns=["code", "level", "parent_row"])
#     }
#     """

#     if date_to is None:
#         with connection.cursor() as cur:
#             cur.execute("SELECT MAX(date_from)::date FROM public.pl_for_csv")
#             date_to = cur.fetchone()[0]

#     date_to = pd.to_datetime(date_to).date()

#     q = """
#     SELECT
#         EXTRACT(YEAR FROM p.date_from)::int AS year,
#         EXTRACT(MONTH FROM p.date_from)::int AS month_num,
#         COALESCE(NULLIF(TRIM(p.cost_item_group), ''), 'Без группы') AS cost_item_group,
#         COALESCE(NULLIF(TRIM(p.cost_item), ''), '') AS cost_item,
#         SUM(p.amount)::numeric AS amount
#     FROM public.pl_for_csv p
#     WHERE p.date_from <= %s::date
#       AND substring(p.account_name from '^\\d+') = '520000'
#     GROUP BY
#         EXTRACT(YEAR FROM p.date_from)::int,
#         EXTRACT(MONTH FROM p.date_from)::int,
#         COALESCE(NULLIF(TRIM(p.cost_item_group), ''), 'Без группы'),
#         COALESCE(NULLIF(TRIM(p.cost_item), ''), '')
#     ORDER BY 1, 2, 3, 4
#     """

#     with connection.cursor() as cur:
#         cur.execute(q, [date_to])
#         rows = cur.fetchall()
#         columns = [col[0] for col in cur.description]

#     df = pd.DataFrame(rows, columns=columns)

#     if df.empty:
#         return {
#             "data": pd.DataFrame(),
#             "year_groups": [],
#             "row_meta": pd.DataFrame(columns=["code", "level", "parent_row"]),
#         }

#     df["year"] = df["year"].astype(int)
#     df["month_num"] = df["month_num"].astype(int)
#     df["cost_item_group"] = df["cost_item_group"].apply(_normalize_group)
#     df["cost_item"] = df.apply(
#         lambda x: _normalize_item(x["cost_item"], x["cost_item_group"]),
#         axis=1
#     )

#     current_year = date_to.year
#     current_month = date_to.month
#     years = sorted(df["year"].unique())

#     year_groups = []
#     ordered_cols = []

#     for year in years:
#         if year == current_year:
#             months = list(range(1, current_month + 1))
#         else:
#             months = sorted(df.loc[df["year"] == year, "month_num"].unique().tolist())

#         month_cols = [f"{MONTH_NAMES_RU[m]} {year}" for m in months]
#         total_col = f"Итого {year}"

#         year_groups.append({
#             "year": year,
#             "months": months,
#             "month_cols": month_cols,
#             "total_col": total_col,
#         })

#         ordered_cols.extend(month_cols)
#         ordered_cols.append(total_col)

#     df["period_col"] = df.apply(
#         lambda x: f"{MONTH_NAMES_RU[int(x['month_num'])]} {int(x['year'])}",
#         axis=1
#     )

#     # --- дети ---
#     child_df = (
#         df.groupby(["cost_item_group", "cost_item", "period_col"], as_index=False)["amount"]
#         .sum()
#         .copy()
#     )

#     child_df["row_name"] = child_df["cost_item"]

#     child_pivot = child_df.pivot_table(
#         index="row_name",
#         columns="period_col",
#         values="amount",
#         aggfunc="sum",
#         fill_value=0,
#     )

#     # --- родители ---
#     parent_df = (
#         df.groupby(["cost_item_group", "period_col"], as_index=False)["amount"]
#         .sum()
#         .copy()
#     )

#     parent_df["row_name"] = parent_df["cost_item_group"]

#     parent_pivot = parent_df.pivot_table(
#         index="row_name",
#         columns="period_col",
#         values="amount",
#         aggfunc="sum",
#         fill_value=0,
#     )

#     # добавим отсутствующие месяцы
#     for col in ordered_cols:
#         if col.startswith("Итого "):
#             continue

#         if col not in child_pivot.columns:
#             child_pivot[col] = 0
#         if col not in parent_pivot.columns:
#             parent_pivot[col] = 0

#     # считаем итоги по годам
#     for group in year_groups:
#         child_pivot[group["total_col"]] = child_pivot[group["month_cols"]].sum(axis=1)
#         parent_pivot[group["total_col"]] = parent_pivot[group["month_cols"]].sum(axis=1)

#     child_pivot = child_pivot.reindex(columns=ordered_cols)
#     parent_pivot = parent_pivot.reindex(columns=ordered_cols)

#     # --- row_meta ---
#     row_meta_rows = []

#     unique_groups = (
#         df[["cost_item_group"]]
#         .drop_duplicates()
#         .sort_values("cost_item_group")
#     )

#     ordered_row_names = []

#     for _, grp in unique_groups.iterrows():
#         group_name = grp["cost_item_group"]
#         group_code = _extract_code(group_name)

#         if group_name in parent_pivot.index:
#             ordered_row_names.append(group_name)
#             row_meta_rows.append({
#                 "row_name": group_name,
#                 "code": group_code,
#                 "level": 1,
#                 "parent_row": None,
#             })

#         group_children = (
#             df.loc[df["cost_item_group"] == group_name, ["cost_item"]]
#             .drop_duplicates()
#             .sort_values("cost_item")
#         )

#         for _, ch in group_children.iterrows():
#             child_name = ch["cost_item"]
#             child_code = _extract_code(child_name)

#             if child_name in child_pivot.index:
#                 ordered_row_names.append(child_name)
#                 row_meta_rows.append({
#                     "row_name": child_name,
#                     "code": child_code,
#                     "level": 2,
#                     "parent_row": group_name,
#                 })

#     # собираем итоговый result: сначала родители, потом дети
#     all_rows = pd.concat([parent_pivot, child_pivot], axis=0)

#     # на случай дублей оставим последнюю запись
#     all_rows = all_rows[~all_rows.index.duplicated(keep="last")]

#     result = all_rows.reindex(ordered_row_names)

#     # убрать полностью пустые строки
#     result = result.loc[(result.fillna(0) != 0).any(axis=1)].copy()

#     row_meta = pd.DataFrame(row_meta_rows)
#     if not row_meta.empty:
#         row_meta = row_meta[row_meta["row_name"].isin(result.index)].copy()
#         row_meta = row_meta.drop_duplicates(subset=["row_name"], keep="first")
#         row_meta = row_meta.set_index("row_name")
#     else:
#         row_meta = pd.DataFrame(columns=["code", "level", "parent_row"])

#     if not result.empty:
#         result.loc["Итого"] = result.sum(axis=0)

#     result = result.where(pd.notna(result), None)

#     return {
#         "data": result,
#         "year_groups": year_groups,
#         "row_meta": row_meta,
#     }




# reporting/excel/cogs_realization_data.py

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


def _make_parent_key(group_name: str) -> str:
    return f"grp::{group_name}"


def _make_child_key(group_name: str, item_name: str) -> str:
    return f"item::{group_name}|||{item_name}"


def get_cogs_realization_report(date_to=None):
    """
    Возвращает payload для листа 1.3 'Себестоимость реализации'.

    Формат:
    {
        "data": DataFrame(index=row_key, columns=period_cols),
        "year_groups": [...],
        "row_meta": DataFrame(index=row_key, columns=[
            "display_name", "code", "level", "parent_row"
        ])
    }
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
        SUM(p.amount)::numeric AS amount
    FROM public.pl_for_csv p
    WHERE p.date_from <= %s::date
      AND substring(p.account_name from '^\\d+') = '520000'
    GROUP BY
        EXTRACT(YEAR FROM p.date_from)::int,
        EXTRACT(MONTH FROM p.date_from)::int,
        COALESCE(NULLIF(TRIM(p.cost_item_group), ''), 'Без группы'),
        COALESCE(NULLIF(TRIM(p.cost_item), ''), '')
    ORDER BY 1, 2, 3, 4
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

    # -----------------------------
    # Детальные строки (children)
    # -----------------------------
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

    # -----------------------------
    # Родительские строки (groups)
    # -----------------------------
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

    # добавим отсутствующие месяцы
    for col in ordered_cols:
        if col.startswith("Итого "):
            continue

        if col not in child_pivot.columns:
            child_pivot[col] = 0
        if col not in parent_pivot.columns:
            parent_pivot[col] = 0

    # итоги по годам по каждой строке
    for group in year_groups:
        child_pivot[group["total_col"]] = child_pivot[group["month_cols"]].sum(axis=1)
        parent_pivot[group["total_col"]] = parent_pivot[group["month_cols"]].sum(axis=1)

    child_pivot = child_pivot.reindex(columns=ordered_cols)
    parent_pivot = parent_pivot.reindex(columns=ordered_cols)

    # -----------------------------
    # row_meta + порядок строк
    # -----------------------------
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

    all_rows = pd.concat([parent_pivot, child_pivot], axis=0)
    all_rows = all_rows[~all_rows.index.duplicated(keep="last")]

    result = all_rows.reindex(ordered_row_keys)

    # убрать полностью пустые строки
    if not result.empty:
        result = result.loc[(result.fillna(0) != 0).any(axis=1)].copy()

    row_meta = pd.DataFrame(row_meta_rows)
    if not row_meta.empty:
        row_meta = row_meta[row_meta["row_key"].isin(result.index)].copy()
        row_meta = row_meta.drop_duplicates(subset=["row_key"], keep="first")
        row_meta = row_meta.set_index("row_key")
    else:
        row_meta = pd.DataFrame(columns=["display_name", "code", "level", "parent_row"])

    # -----------------------------
    # Общий итог — только по детализации
    # чтобы не было двойного счета:
    # родители + дети вместе суммировать нельзя
    # -----------------------------
    if not result.empty:
        if row_meta is not None and not row_meta.empty:
            detail_rows = row_meta[row_meta["level"] == 2].index.tolist()
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