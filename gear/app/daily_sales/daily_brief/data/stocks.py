# gear/app/daily_sales/daily_brief/data/stocks.py

from __future__ import annotations

import base64
import io
from datetime import date
from typing import Any

import pandas as pd

from gear.app.daily_sales.stocks.dashboard_data import (
    get_effective_stock_date,
    get_stock_dashboard_summary,
    get_stock_regions,
    get_stock_warehouses,
)

from inventories.reporting.map.russia_regions_map import (
    build_russia_regions_map,
)

from inventories.reporting.map.russia_warehouses_map import (
    build_warehouses_stock_map_png,
)

from ..helpers import (
    dataframe_records,
    json_safe,
    number,
)


# =============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# =============================================================================


def _to_dataframe(
    value,
) -> pd.DataFrame:
    """
    Безопасно преобразует результат функции dashboard_data
    в DataFrame.

    Поддерживает:
    - DataFrame;
    - dict;
    - list[dict];
    - None.
    """

    if value is None:
        return pd.DataFrame()

    if isinstance(value, pd.DataFrame):
        return value.copy()

    if isinstance(value, dict):
        return pd.DataFrame(
            [value]
        )

    if isinstance(value, list):
        return pd.DataFrame(
            value
        )

    return pd.DataFrame()


def _first_row(
    value,
) -> dict:
    """
    Возвращает первую строку DataFrame
    или переданный словарь.
    """

    if isinstance(value, dict):
        return dict(value)

    frame = _to_dataframe(value)

    if frame.empty:
        return {}

    return frame.iloc[0].to_dict()


def _rename_existing_columns(
    frame: pd.DataFrame,
    variants: dict[str, list[str]],
) -> pd.DataFrame:
    """
    Приводит возможные варианты названий колонок
    к единой схеме.

    Например:
        warehouse_name -> warehouse
        total_quantity -> total_qty
    """

    if frame.empty:
        return frame

    work = frame.copy()

    rename_map = {}

    for target, candidates in variants.items():
        if target in work.columns:
            continue

        for candidate in candidates:
            if candidate in work.columns:
                rename_map[candidate] = target
                break

    if rename_map:
        work = work.rename(
            columns=rename_map
        )

    return work


def _prepare_warehouses(
    value,
) -> pd.DataFrame:
    """
    Приводит данные складов к формату:

    warehouse
    region
    on_hand
    in_transit
    products
    total_qty
    """

    frame = _to_dataframe(
        value
    )

    frame = _rename_existing_columns(
        frame,
        {
            "warehouse": [
                "warehouse_name",
                "name",
                "склад",
            ],
            "region": [
                "warehouse_region",
                "district",
                "регион",
            ],
            "on_hand": [
                "warehouse_quantity",
                "quantity",
                "quantity_on_hand",
                "на_складе",
            ],
            "in_transit": [
                "in_transit_quantity",
                "transit_quantity",
                "в_пути",
            ],
            "products": [
                "nm_count",
                "product_count",
                "товаров",
            ],
            "total_qty": [
                "stock_quantity",
                "total_quantity",
                "total",
                "итого",
            ],
        },
    )

    if frame.empty:
        return frame

    required = [
        "warehouse",
        "region",
        "on_hand",
        "in_transit",
        "products",
        "total_qty",
    ]

    for column in required:
        if column not in frame.columns:
            if column in {
                "warehouse",
                "region",
            }:
                frame[column] = ""
            else:
                frame[column] = 0

    frame["warehouse"] = (
        frame["warehouse"]
        .fillna("Склад не указан")
        .astype(str)
        .str.strip()
        .replace(
            "",
            "Склад не указан",
        )
    )

    frame["region"] = (
        frame["region"]
        .fillna("Не распределено")
        .astype(str)
        .str.strip()
        .replace(
            "",
            "Не распределено",
        )
    )

    for column in [
        "on_hand",
        "in_transit",
        "products",
        "total_qty",
    ]:
        frame[column] = pd.to_numeric(
            frame[column],
            errors="coerce",
        ).fillna(0)

    # Если total_qty отсутствовал или равен нулю,
    # рассчитываем как склад + путь.
    missing_total = (
        frame["total_qty"] <= 0
    )

    frame.loc[
        missing_total,
        "total_qty",
    ] = (
        frame.loc[
            missing_total,
            "on_hand",
        ]
        + frame.loc[
            missing_total,
            "in_transit",
        ]
    )

    frame = frame[
        frame["total_qty"] > 0
    ].copy()

    frame = frame.sort_values(
        "total_qty",
        ascending=False,
    ).reset_index(
        drop=True
    )

    return frame[
        required
    ]


def _prepare_regions(
    value,
    warehouses: pd.DataFrame,
) -> pd.DataFrame:
    """
    Приводит данные регионов к формату:

    region
    on_hand
    in_transit
    warehouses
    products
    total_qty

    Если get_stock_regions() вернул пустые данные,
    региональная таблица собирается из складов.
    """

    frame = _to_dataframe(
        value
    )

    frame = _rename_existing_columns(
        frame,
        {
            "region": [
                "warehouse_region",
                "district",
                "регион",
            ],
            "on_hand": [
                "warehouse_quantity",
                "quantity",
                "на_складе",
            ],
            "in_transit": [
                "in_transit_quantity",
                "transit_quantity",
                "в_пути",
            ],
            "warehouses": [
                "warehouse_count",
                "warehouses_count",
                "складов",
            ],
            "products": [
                "nm_count",
                "product_count",
                "товаров",
            ],
            "total_qty": [
                "stock_quantity",
                "total_quantity",
                "total",
                "итого",
            ],
        },
    )

    # Если готовая региональная разбивка отсутствует,
    # строим её из складской таблицы.
    if frame.empty and not warehouses.empty:
        frame = (
            warehouses
            .groupby(
                "region",
                as_index=False,
            )
            .agg(
                on_hand=(
                    "on_hand",
                    "sum",
                ),
                in_transit=(
                    "in_transit",
                    "sum",
                ),
                warehouses=(
                    "warehouse",
                    "nunique",
                ),
                products=(
                    "products",
                    "sum",
                ),
                total_qty=(
                    "total_qty",
                    "sum",
                ),
            )
        )

    if frame.empty:
        return frame

    required = [
        "region",
        "on_hand",
        "in_transit",
        "warehouses",
        "products",
        "total_qty",
    ]

    for column in required:
        if column not in frame.columns:
            if column == "region":
                frame[column] = (
                    "Не распределено"
                )
            else:
                frame[column] = 0

    frame["region"] = (
        frame["region"]
        .fillna("Не распределено")
        .astype(str)
        .str.strip()
        .replace(
            "",
            "Не распределено",
        )
    )

    for column in [
        "on_hand",
        "in_transit",
        "warehouses",
        "products",
        "total_qty",
    ]:
        frame[column] = pd.to_numeric(
            frame[column],
            errors="coerce",
        ).fillna(0)

    missing_total = (
        frame["total_qty"] <= 0
    )

    frame.loc[
        missing_total,
        "total_qty",
    ] = (
        frame.loc[
            missing_total,
            "on_hand",
        ]
        + frame.loc[
            missing_total,
            "in_transit",
        ]
    )

    frame = frame[
        frame["total_qty"] > 0
    ].copy()

    frame = frame.sort_values(
        "total_qty",
        ascending=False,
    ).reset_index(
        drop=True
    )

    return frame[
        required
    ]


def _buffer_to_base64(
    buffer,
) -> str | None:
    """
    Преобразует BytesIO либо bytes в data URI,
    который можно вставить в HTML через <img>.
    """

    if buffer is None:
        return None

    if isinstance(buffer, io.BytesIO):
        buffer.seek(0)
        raw = buffer.read()

    elif isinstance(
        buffer,
        bytes,
    ):
        raw = buffer

    else:
        return None

    if not raw:
        return None

    encoded = base64.b64encode(
        raw
    ).decode(
        "ascii"
    )

    return (
        "data:image/png;base64,"
        + encoded
    )


def _build_regions_map(
    regions: pd.DataFrame,
    report_date: str,
    summary: dict,
) -> tuple[str | None, str | None]:
    """
    Строит карту регионов.

    Возвращает:
        map_base64
        map_error
    """

    if regions.empty:
        return (
            None,
            "Нет данных по регионам.",
        )

    map_frame = regions.rename(
        columns={
            "region": "регион",
            "on_hand": "на_складе",
            "in_transit": "в_пути",
            "warehouses": "складов",
            "total_qty": "итого",
        }
    )

    map_frame = map_frame[
        [
            "регион",
            "на_складе",
            "в_пути",
            "складов",
            "итого",
        ]
    ].copy()

    # Строка «Не распределено» может находиться
    # в таблице, но геометрии на карте у неё нет.
    mapped_frame = map_frame[
        map_frame["регион"]
        != "Не распределено"
    ].copy()

    if mapped_frame.empty:
        return (
            None,
            (
                "Все остатки находятся в группе "
                "«Не распределено»."
            ),
        )

    summary_stats = {
        "total_warehouses": int(
            number(
                summary.get(
                    "warehouses"
                )
            )
        ),
        "total_on_hand": number(
            summary.get(
                "on_hand"
            )
        ),
        "total_in_transit": number(
            summary.get(
                "in_transit"
            )
        ),
        "total_quantity": number(
            summary.get(
                "total_qty"
            )
        ),
    }

    try:
        buffer = build_russia_regions_map(
            region_stats=mapped_frame,
            report_date=report_date,
            summary_stats=summary_stats,
        )

        return (
            _buffer_to_base64(
                buffer
            ),
            None,
        )

    except Exception as exc:
        return (
            None,
            (
                "Ошибка построения карты регионов: "
                f"{type(exc).__name__}: {exc}"
            ),
        )


def _build_warehouses_map(
    warehouses: pd.DataFrame,
    report_date: str,
) -> tuple[str | None, str | None]:
    """
    Строит точечную карту складов.
    """

    if warehouses.empty:
        return (
            None,
            "Нет данных по складам.",
        )

    map_frame = warehouses.rename(
        columns={
            "warehouse": "склад",
            "on_hand": "на_складе",
            "in_transit": "в_пути",
            "total_qty": "итого",
        }
    )

    try:
        buffer = (
            build_warehouses_stock_map_png(
                warehouse_stats=map_frame,
                report_date=report_date,
            )
        )

        return (
            _buffer_to_base64(
                buffer
            ),
            None,
        )

    except Exception as exc:
        return (
            None,
            (
                "Ошибка построения карты складов: "
                f"{type(exc).__name__}: {exc}"
            ),
        )


# =============================================================================
# ОСНОВНАЯ ФУНКЦИЯ
# =============================================================================


def get_stock_data(
    report_date: date,
) -> dict[str, Any]:
    """
    Данные товарного разворота.

    Важно:
    данные берутся из тех же функций, которые использует
    рабочий dashboard остатков.

    Это гарантирует, что:
    - дата снимка совпадает;
    - склады совпадают;
    - регионы совпадают;
    - итоговые показатели совпадают с dashboard.
    """

    requested_date = (
        report_date.isoformat()
    )

    effective_date = (
        get_effective_stock_date(
            requested_date
        )
    )

    if not effective_date:
        return {
            "available": False,
            "requested_date": requested_date,
            "report_date": None,
            "reason": (
                "Не найден доступный снимок "
                "товарных остатков."
            ),
            "regions": [],
            "top_warehouses": [],
            "region_map": None,
            "warehouse_map": None,
        }

    effective_date = (
        pd.to_datetime(
            effective_date,
            errors="coerce",
        )
    )

    if pd.isna(effective_date):
        return {
            "available": False,
            "requested_date": requested_date,
            "report_date": None,
            "reason": (
                "Дата снимка товарных остатков "
                "не распознана."
            ),
            "regions": [],
            "top_warehouses": [],
            "region_map": None,
            "warehouse_map": None,
        }

    effective_date_string = (
        effective_date
        .date()
        .isoformat()
    )

    # -------------------------------------------------------------------------
    # Данные из рабочего dashboard
    # -------------------------------------------------------------------------

    summary_source = (
        get_stock_dashboard_summary(
            effective_date_string
        )
    )

    regions_source = (
        get_stock_regions(
            effective_date_string
        )
    )

    warehouses_source = (
        get_stock_warehouses(
            effective_date_string
        )
    )

    summary_row = _first_row(
        summary_source
    )

    warehouses = _prepare_warehouses(
        warehouses_source
    )

    regions = _prepare_regions(
        regions_source,
        warehouses,
    )

    # -------------------------------------------------------------------------
    # Итоги
    # -------------------------------------------------------------------------

    on_hand = number(
        summary_row.get(
            "on_hand",
            summary_row.get(
                "warehouse_quantity",
                warehouses["on_hand"].sum()
                if not warehouses.empty
                else 0,
            ),
        )
    )

    in_transit = number(
        summary_row.get(
            "in_transit",
            summary_row.get(
                "in_transit_quantity",
                warehouses["in_transit"].sum()
                if not warehouses.empty
                else 0,
            ),
        )
    )

    total_qty = number(
        summary_row.get(
            "total_qty",
            summary_row.get(
                "stock_quantity",
                summary_row.get(
                    "total_quantity",
                    warehouses["total_qty"].sum()
                    if not warehouses.empty
                    else (
                        on_hand
                        + in_transit
                    ),
                ),
            ),
        )
    )

    products = int(
        number(
            summary_row.get(
                "products",
                summary_row.get(
                    "nm_count",
                    summary_row.get(
                        "product_count",
                        0,
                    ),
                ),
            )
        )
    )

    warehouses_count = int(
        number(
            summary_row.get(
                "warehouses",
                summary_row.get(
                    "warehouse_count",
                    warehouses[
                        "warehouse"
                    ].nunique()
                    if not warehouses.empty
                    else 0,
                ),
            )
        )
    )

    if total_qty <= 0:
        total_qty = (
            on_hand
            + in_transit
        )

    transit_share = (
        in_transit
        / total_qty
        * 100
        if total_qty > 0
        else 0
    )

    summary = {
        "on_hand": on_hand,
        "in_transit": in_transit,
        "total_qty": total_qty,
        "products": products,
        "warehouses": warehouses_count,
        "transit_share": transit_share,
    }

    # -------------------------------------------------------------------------
    # Карты
    # -------------------------------------------------------------------------

    region_map, region_map_error = (
        _build_regions_map(
            regions=regions,
            report_date=effective_date_string,
            summary=summary,
        )
    )

    warehouse_map, warehouse_map_error = (
        _build_warehouses_map(
            warehouses=warehouses,
            report_date=effective_date_string,
        )
    )

    # Для газеты сначала используем карту конкретных складов.
    # Если она не построилась — используем карту регионов.
    primary_map = (
        warehouse_map
        or region_map
    )

    primary_map_type = (
        "warehouses"
        if warehouse_map
        else "regions"
        if region_map
        else None
    )

    return {
        "available": True,

        "requested_date": requested_date,
        "report_date": effective_date_string,

        "used_previous_snapshot": (
            effective_date_string
            != requested_date
        ),

        "total_qty": total_qty,
        "on_hand": on_hand,
        "in_transit": in_transit,
        "products": products,
        "warehouses": warehouses_count,
        "transit_share": transit_share,

        "regions": dataframe_records(
            regions
        ),

        "top_regions": dataframe_records(
            regions,
            limit=8,
        ),

        "warehouses_data": dataframe_records(
            warehouses
        ),

        "top_warehouses": dataframe_records(
            warehouses,
            limit=10,
        ),

        # Основная карта для существующего stock_geography().
        "map_image": primary_map,
        "map_type": primary_map_type,

        # Обе карты сохраняем отдельно.
        "warehouse_map": warehouse_map,
        "region_map": region_map,

        # Ошибки не прячем:
        # их можно временно вывести в PDF или лог.
        "warehouse_map_error": (
            warehouse_map_error
        ),
        "region_map_error": (
            region_map_error
        ),

        "debug": {
            "warehouse_rows": int(
                len(warehouses)
            ),
            "region_rows": int(
                len(regions)
            ),
            "warehouse_columns": list(
                warehouses.columns
            ),
            "region_columns": list(
                regions.columns
            ),
        },
    }