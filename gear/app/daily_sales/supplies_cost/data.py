# gear/app/daily_sales/supplies_cost/data.py
"""Поставки FBW и покрытие их себестоимостью по приходным УПД.

Поставки и состав — wb_raw.wb_supplies / wb_supply_goods (команда wb_supplies).
УПД — inventories.upd_income → inventories.upd_documents.

Покрытие считается по артикулу по принципу FIFO: количество с ценой по всем
УПД артикула закрывает поставки от старых к новым. Что не закрыто — единицы
без себестоимости в конкретной поставке.
"""
from __future__ import annotations

import time
from datetime import date

import numpy as np
import pandas as pd

from conns import get_duckdb_conn_with_opt

from .config import (
    COST_NO_PRICE,
    COST_NO_UPD,
    COST_OK,
    COST_PART,
    WB_BOX_TYPE,
    WB_SUPPLY_STATUS,
)

_J = "json_extract_string(j, '$.{0}')"


def _d(field):
    return f"TRY_CAST(LEFT(NULLIF({_J.format(field)}, ''), 10) AS DATE)"


ROWS_SQL = f"""
WITH s AS (
    SELECT
        sid,
        TRY_CAST({_J.format('preorderID')} AS BIGINT) AS preorder_id,
        {_d('createDate')} AS created,
        {_d('supplyDate')} AS planned,
        {_d('factDate')} AS fact,
        TRY_CAST({_J.format('statusID')} AS INTEGER) AS status_id,
        NULLIF({_J.format('statusName')}, '') AS status_name,
        TRY_CAST({_J.format('boxTypeID')} AS INTEGER) AS box_id,
        NULLIF({_J.format('boxTypeName')}, '') AS box_name,
        COALESCE(NULLIF({_J.format('actualWarehouseName')}, ''),
                 NULLIF({_J.format('warehouseName')}, '')) AS warehouse
    FROM (SELECT supply_id AS sid, row_json::VARCHAR AS j
          FROM pg.wb_raw.wb_supplies)
),
g AS (
    SELECT
        sid,
        nm,
        ANY_VALUE(vendor_code) AS vendor_code,
        SUM(plan_qty) AS plan_qty,
        SUM(acc_qty) AS acc_qty
    FROM (
        SELECT
            supply_id AS sid,
            TRY_CAST({_J.format('nmID')} AS BIGINT) AS nm,
            NULLIF({_J.format('vendorCode')}, '') AS vendor_code,
            COALESCE(TRY_CAST({_J.format('quantity')} AS DOUBLE), 0) AS plan_qty,
            COALESCE(TRY_CAST({_J.format('acceptedQuantity')} AS DOUBLE), 0) AS acc_qty
        FROM (SELECT supply_id, row_json::VARCHAR AS j
              FROM pg.wb_raw.wb_supply_goods)
    )
    WHERE nm IS NOT NULL
    GROUP BY 1, 2
),
x AS (
    SELECT
        g.*, s.* EXCLUDE (sid),
        COALESCE(s.fact, s.planned, s.created) AS d,
        CASE WHEN g.acc_qty > 0 THEN g.acc_qty ELSE g.plan_qty END AS qty
    FROM g JOIN s USING (sid)
)
SELECT
    x.*,
    SUM(qty) OVER (
        PARTITION BY nm
        ORDER BY d NULLS LAST, sid
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS cum_qty
FROM x
WHERE qty > 0
"""

UPD_SQL = """
SELECT
    ui.nm_id AS nm,
    COUNT(*) AS upd_rows,
    COALESCE(SUM(ui.upd_qty) FILTER (WHERE ui.upd_price_vatless > 0), 0) AS upd_qty,
    MAX(ud.date)::DATE AS upd_last_date,
    ARG_MAX(CAST(ud.number AS VARCHAR), ud.date) AS upd_last_number,
    ARG_MAX(ui.upd_price_vatless, ud.date)
        FILTER (WHERE ui.upd_price_vatless > 0) AS upd_last_price
FROM inventories.upd_income ui
LEFT JOIN inventories.upd_documents ud ON ud.id = ui.upd_document_id
WHERE ui.nm_id IS NOT NULL
GROUP BY 1
"""

PRODUCT_SQL = """
SELECT
    card_id AS nm,
    ANY_VALUE(COALESCE(NULLIF(TRIM(UPPER(brand)), ''), 'НЕ УКАЗАН')) AS brand,
    ANY_VALUE(CAST(subject_id AS VARCHAR)) AS subject_id,
    ANY_VALUE(COALESCE(NULLIF(TRIM(subject_name), ''), 'Не указана')) AS category,
    ANY_VALUE(COALESCE(gender, 'Не указан')) AS gender,
    ANY_VALUE(COALESCE(sa_name, '')) AS sa,
    ANY_VALUE(COALESCE(NULLIF(TRIM(title), ''), '')) AS title
FROM inventories.wb_product
GROUP BY 1
"""


def _list(v):
    if v is None:
        return []
    if isinstance(v, str):
        return [v] if v.strip() else []
    return [x for x in v if x not in (None, "")]


def _cost_status(r):
    if r.upd_rows == 0:
        return COST_NO_UPD
    if r.upd_qty <= 0:
        return COST_NO_PRICE
    if r.no_cost_qty <= 0:
        return COST_OK
    return COST_PART


CACHE_TTL = 10 * 60
_cache: dict = {}


def _base() -> pd.DataFrame:
    """Все строки «поставка × артикул» со статусом себестоимости; кэш 10 минут."""
    hit = _cache.get("base")
    if hit and time.time() - hit[0] < CACHE_TTL:
        return hit[1]
    with get_duckdb_conn_with_opt(ro=True) as con:
        rows = con.execute(ROWS_SQL).df()
        upd = con.execute(UPD_SQL).df()
        prod = con.execute(PRODUCT_SQL).df()
    a = _enrich(rows, upd, prod) if not rows.empty else rows
    _cache["base"] = (time.time(), a)
    return a


def supply_articles(sid) -> pd.DataFrame:
    """Состав одной поставки."""
    a = _base()
    if a.empty:
        return a
    return a[a["sid"] == int(sid)].sort_values(["cost_status", "brand", "nm"],
                                               ascending=[False, True, True])


def _enrich(rows, upd, prod) -> pd.DataFrame:
    # Покрытие считаем по всей истории, фильтры — после
    a = rows.merge(upd, on="nm", how="left").merge(prod, on="nm", how="left")
    a["upd_rows"] = a["upd_rows"].fillna(0)
    a["upd_qty"] = a["upd_qty"].fillna(0)
    a["no_cost_qty"] = np.clip(a["cum_qty"] - a["upd_qty"], 0, a["qty"])
    a["cost_status"] = [_cost_status(r) for r in a.itertuples(index=False)]
    for c, v in (("brand", "НЕ УКАЗАН"), ("category", "Не указана"),
                 ("gender", "Не указан"), ("sa", ""), ("title", "")):
        a[c] = a[c].fillna(v)
    a["sa"] = np.where(a["sa"] == "", a["vendor_code"].fillna(""), a["sa"])
    a["status"] = [
        sn if isinstance(sn, str) and sn else WB_SUPPLY_STATUS.get(si, "" if pd.isna(si) else str(int(si)))
        for sn, si in zip(a["status_name"], a["status_id"])
    ]
    a["box"] = [
        bn if isinstance(bn, str) and bn else WB_BOX_TYPE.get(bi, "" if pd.isna(bi) or bi == 0 else str(int(bi)))
        for bn, bi in zip(a["box_name"], a["box_id"])
    ]
    a["d"] = pd.to_datetime(a["d"])
    return a


def collect(start=None, end=None, cat_list=None, brand_list=None,
            gender_list=None) -> dict:
    """Строки «поставка × артикул», агрегаты по поставкам и брендам."""
    a = _base()
    if a.empty:
        return {"empty": True}

    if start is not None and end is not None:
        a = a[(a["d"] >= pd.Timestamp(start)) & (a["d"] <= pd.Timestamp(end))]
    cats, brands, genders = _list(cat_list), _list(brand_list), _list(gender_list)
    if cats:
        a = a[a["subject_id"].isin([str(c) for c in cats])]
    if brands:
        a = a[a["brand"].isin([str(b).upper() for b in brands])]
    if genders:
        a = a[a["gender"].isin([str(g) for g in genders])]

    if a.empty:
        return {"empty": True}

    a = a.copy()
    a["is_ok"] = a["cost_status"] == COST_OK
    a["is_part"] = a["cost_status"] == COST_PART
    a["is_bad"] = a["cost_status"].isin([COST_NO_UPD, COST_NO_PRICE])

    sup = a.groupby("sid").agg(
        d=("d", "first"), created=("created", "first"), planned=("planned", "first"),
        fact=("fact", "first"), status=("status", "first"), box=("box", "first"),
        warehouse=("warehouse", "first"), preorder_id=("preorder_id", "first"),
        arts=("nm", "nunique"), plan_qty=("plan_qty", "sum"), acc_qty=("acc_qty", "sum"),
        qty=("qty", "sum"), ok=("is_ok", "sum"), part=("is_part", "sum"),
        bad=("is_bad", "sum"), no_cost_qty=("no_cost_qty", "sum"),
    ).reset_index()
    brand_by_sup = (a.groupby(["sid", "brand"])["qty"].sum().reset_index()
                    .sort_values(["sid", "qty"], ascending=[True, False])
                    .groupby("sid")["brand"].apply(lambda s: ", ".join(s.head(3))
                                                   + (f" +{len(s) - 3}" if len(s) > 3 else "")))
    sup["brands"] = sup["sid"].map(brand_by_sup)
    sup["no_cost_arts_pct"] = 100.0 * (sup["part"] + sup["bad"]) / sup["arts"]
    sup["no_cost_qty_pct"] = 100.0 * sup["no_cost_qty"] / sup["qty"]
    sup = sup.sort_values(["d", "sid"], ascending=[False, False])

    br = a.groupby("brand").agg(
        supplies=("sid", "nunique"), arts=("nm", "nunique"), qty=("qty", "sum"),
        no_cost_qty=("no_cost_qty", "sum"),
    ).reset_index()
    bad_arts = a[~a["is_ok"]].groupby("brand")["nm"].nunique()
    br["no_cost_arts"] = br["brand"].map(bad_arts).fillna(0)
    br["no_cost_arts_pct"] = 100.0 * br["no_cost_arts"] / br["arts"]
    br["no_cost_qty_pct"] = 100.0 * br["no_cost_qty"] / br["qty"]
    br = br.sort_values("qty", ascending=False)

    arts = a.sort_values(["d", "sid", "cost_status", "brand", "nm"],
                         ascending=[False, False, False, True, True])

    kpi = {
        "supplies": int(sup["sid"].nunique()),
        "supplies_with_gap": int(((sup["part"] + sup["bad"]) > 0).sum()),
        "arts": int(a["nm"].nunique()),
        "arts_no_cost": int(a.loc[~a["is_ok"], "nm"].nunique()),
        "arts_no_upd": int(a.loc[a["is_bad"], "nm"].nunique()),
        "qty": float(a["qty"].sum()),
        "no_cost_qty": float(a["no_cost_qty"].sum()),
        "d_min": a["d"].min(),
        "d_max": a["d"].max(),
    }
    return {"empty": False, "kpi": kpi, "supplies": sup, "articles": arts,
            "brands": br, "has_warehouse": bool(sup["warehouse"].notna().any()),
            "has_box": bool((sup["box"] != "").any())}
