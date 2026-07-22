# gear/app/daily_sales/stocks/dashboard_data.py

from __future__ import annotations

from typing import Optional

import pandas as pd

from conns import get_duckdb_conn_with_opt
from .warehouse_coordinates import (
    WAREHOUSE_POINTS,
    WAREHOUSE_MAP_EXCLUDE,
)


# =============================================================================
# ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ НОРМАЛИЗАЦИИ НАЗВАНИЯ
# =============================================================================

def _clean_warehouse_name(value) -> str:
    """
    Приводим название склада к аккуратному виду.

    Не меняем регистр и само название, потому что ключи
    WAREHOUSE_POINTS должны совпадать с данными WB.
    """

    if value is None:
        return ""

    return " ".join(
        str(value).strip().split()
    )


# =============================================================================
# ФАКТИЧЕСКАЯ ДАТА ОСТАТКОВ
# =============================================================================

def get_effective_stock_date(
    report_date,
) -> Optional[object]:
    """
    Последняя имеющаяся дата остатков,
    которая не превышает выбранную дату.

    Например:

        пользователь выбрал:
            22.07.2026

        данные есть максимум:
            21.07.2026

        возвращаем:
            21.07.2026
    """

    with get_duckdb_conn_with_opt() as con:
        row = con.execute(
            """
            SELECT
                MAX(
                    date_from::DATE
                )

            FROM stocks.unpacked_stocks

            WHERE
                date_from::DATE
                    <= $report_date::DATE
            """,
            {
                "report_date": report_date,
            },
        ).fetchone()

    if not row:
        return None

    return row[0]


# =============================================================================
# KPI
# =============================================================================

def get_stock_dashboard_summary(
    report_date,
) -> dict:

    with get_duckdb_conn_with_opt() as con:
        row = con.execute(
            """
            SELECT
                SUM(
                    COALESCE(
                        quantity,
                        0
                    )
                ) AS on_hand,

                SUM(
                    COALESCE(
                        in_way_from_client,
                        0
                    )
                    +
                    COALESCE(
                        in_way_to_client,
                        0
                    )
                ) AS in_transit,

                SUM(
                    COALESCE(
                        quantity,
                        0
                    )
                    +
                    COALESCE(
                        in_way_from_client,
                        0
                    )
                    +
                    COALESCE(
                        in_way_to_client,
                        0
                    )
                ) AS total_qty,

                COUNT(
                    DISTINCT
                    NULLIF(
                        TRIM(
                            warehouse_name
                        ),
                        ''
                    )
                ) AS warehouses,

                COUNT(
                    DISTINCT
                    CASE

                        WHEN
                            COALESCE(
                                quantity,
                                0
                            )
                            +
                            COALESCE(
                                in_way_from_client,
                                0
                            )
                            +
                            COALESCE(
                                in_way_to_client,
                                0
                            )
                            > 0

                        THEN nm_id

                    END
                ) AS products

            FROM stocks.unpacked_stocks

            WHERE
                date_from::DATE
                    = $report_date::DATE
            """,
            {
                "report_date": report_date,
            },
        ).fetchone()

    row = row or (
        0,
        0,
        0,
        0,
        0,
    )

    return {
        "on_hand": int(
            row[0]
            or 0
        ),

        "in_transit": int(
            row[1]
            or 0
        ),

        "total_qty": int(
            row[2]
            or 0
        ),

        "warehouses": int(
            row[3]
            or 0
        ),

        "products": int(
            row[4]
            or 0
        ),
    }


# =============================================================================
# РЕГИОНЫ
# =============================================================================

def get_stock_regions(
    report_date,
) -> pd.DataFrame:

    with get_duckdb_conn_with_opt() as con:
        df = con.execute(
            """
            SELECT
                COALESCE(
                    NULLIF(
                        TRIM(
                            region_name
                        ),
                        ''
                    ),
                    'Регион не указан'
                ) AS region,

                COUNT(
                    DISTINCT
                    NULLIF(
                        TRIM(
                            warehouse_name
                        ),
                        ''
                    )
                ) AS warehouses,

                SUM(
                    COALESCE(
                        quantity,
                        0
                    )
                ) AS on_hand,

                SUM(
                    COALESCE(
                        in_way_from_client,
                        0
                    )
                    +
                    COALESCE(
                        in_way_to_client,
                        0
                    )
                ) AS in_transit,

                SUM(
                    COALESCE(
                        quantity,
                        0
                    )
                    +
                    COALESCE(
                        in_way_from_client,
                        0
                    )
                    +
                    COALESCE(
                        in_way_to_client,
                        0
                    )
                ) AS total_qty

            FROM stocks.unpacked_stocks

            WHERE
                date_from::DATE
                    = $report_date::DATE

            GROUP BY
                1

            HAVING
                SUM(
                    COALESCE(
                        quantity,
                        0
                    )
                    +
                    COALESCE(
                        in_way_from_client,
                        0
                    )
                    +
                    COALESCE(
                        in_way_to_client,
                        0
                    )
                ) > 0

            ORDER BY
                total_qty DESC
            """,
            {
                "report_date": report_date,
            },
        ).df()

    return df


# =============================================================================
# СКЛАДЫ
# =============================================================================

def get_stock_warehouses(
    report_date,
) -> pd.DataFrame:
    """
    Возвращает агрегированные остатки по складам.

    В результирующем DataFrame остаются ВСЕ склады.

    Дополнительные поля:

        lon
            долгота склада;

        lat
            широта склада;

        map_excluded
            склад сознательно не должен отображаться на карте
            (например "Остальные" или закрытый склад);

        has_coordinates
            склад имеет координаты и может быть показан на карте.

    Важно:
    отсутствие координат никак не удаляет склад из таблицы.
    """

    # =========================================================================
    # Данные из DuckDB
    # =========================================================================

    with get_duckdb_conn_with_opt() as con:
        df = con.execute(
            """
            SELECT
                COALESCE(
                    NULLIF(
                        TRIM(region_name),
                        ''
                    ),
                    'Регион не указан'
                ) AS region,

                COALESCE(
                    NULLIF(
                        TRIM(warehouse_name),
                        ''
                    ),
                    'Склад не указан'
                ) AS warehouse,

                COUNT(
                    DISTINCT
                    CASE
                        WHEN
                            COALESCE(quantity, 0)
                            +
                            COALESCE(in_way_from_client, 0)
                            +
                            COALESCE(in_way_to_client, 0)
                            > 0
                        THEN nm_id
                    END
                ) AS products,

                SUM(
                    COALESCE(
                        quantity,
                        0
                    )
                ) AS on_hand,

                SUM(
                    COALESCE(
                        in_way_from_client,
                        0
                    )
                    +
                    COALESCE(
                        in_way_to_client,
                        0
                    )
                ) AS in_transit,

                SUM(
                    COALESCE(
                        quantity,
                        0
                    )
                    +
                    COALESCE(
                        in_way_from_client,
                        0
                    )
                    +
                    COALESCE(
                        in_way_to_client,
                        0
                    )
                ) AS total_qty

            FROM stocks.unpacked_stocks

            WHERE
                date_from::DATE
                    = $report_date::DATE

            GROUP BY
                1,
                2

            HAVING
                SUM(
                    COALESCE(
                        quantity,
                        0
                    )
                    +
                    COALESCE(
                        in_way_from_client,
                        0
                    )
                    +
                    COALESCE(
                        in_way_to_client,
                        0
                    )
                ) > 0

            ORDER BY
                total_qty DESC
            """,
            {
                "report_date": report_date,
            },
        ).df()

    # =========================================================================
    # Пустой результат
    # =========================================================================

    if df.empty:
        df["lon"] = pd.Series(
            dtype=float
        )

        df["lat"] = pd.Series(
            dtype=float
        )

        df["map_excluded"] = pd.Series(
            dtype=bool
        )

        df["has_coordinates"] = pd.Series(
            dtype=bool
        )

        return df

    # =========================================================================
    # Нормализация названий
    # =========================================================================

    df["warehouse"] = (
        df["warehouse"]
        .astype(str)
        .str.strip()
        .str.replace(
            r"\s+",
            " ",
            regex=True,
        )
    )

    df["region"] = (
        df["region"]
        .astype(str)
        .str.strip()
        .str.replace(
            r"\s+",
            " ",
            regex=True,
        )
    )

    # =========================================================================
    # Исключения для карты
    #
    # Например:
    #
    #     "Остальные"
    #     "Ноябрьск (Закрыт)"
    #
    # Они продолжают участвовать в KPI и таблицах,
    # но не считаются физическими точками карты.
    # =========================================================================

    df["map_excluded"] = (
        df["warehouse"]
        .isin(
            WAREHOUSE_MAP_EXCLUDE
        )
    )

    # =========================================================================
    # Координаты
    #
    # WAREHOUSE_POINTS:
    #
    #     {
    #         "Коледино": (37.55, 55.39),
    #         ...
    #     }
    #
    # Порядок:
    #
    #     longitude,
    #     latitude
    # =========================================================================

    df["lon"] = (
        df["warehouse"]
        .map(
            lambda warehouse: (
                WAREHOUSE_POINTS.get(
                    warehouse,
                    (
                        None,
                        None,
                    ),
                )[0]
            )
        )
    )

    df["lat"] = (
        df["warehouse"]
        .map(
            lambda warehouse: (
                WAREHOUSE_POINTS.get(
                    warehouse,
                    (
                        None,
                        None,
                    ),
                )[1]
            )
        )
    )

    # =========================================================================
    # Можно ли показать склад на карте
    #
    # Только если:
    #
    # - он не исключён сознательно;
    # - есть longitude;
    # - есть latitude.
    # =========================================================================

    df["has_coordinates"] = (
        ~df["map_excluded"]
        &
        df["lon"].notna()
        &
        df["lat"].notna()
    )

    # =========================================================================
    # Диагностика отсутствующих координат
    #
    # map_excluded здесь НЕ считаем ошибкой.
    # =========================================================================

    missing = (
        df.loc[
            ~df["map_excluded"]
            &
            ~df["has_coordinates"],
            [
                "region",
                "warehouse",
            ],
        ]
        .drop_duplicates()
        .sort_values(
            [
                "region",
                "warehouse",
            ]
        )
        .reset_index(
            drop=True
        )
    )

    # =========================================================================
    # Исключённые склады
    # =========================================================================

    excluded = (
        df.loc[
            df["map_excluded"],
            [
                "region",
                "warehouse",
            ],
        ]
        .drop_duplicates()
        .sort_values(
            [
                "region",
                "warehouse",
            ]
        )
        .reset_index(
            drop=True
        )
    )

    # =========================================================================
    # Счётчики
    # =========================================================================

    total_count = int(
        len(df)
    )

    mapped_count = int(
        df["has_coordinates"].sum()
    )

    excluded_count = int(
        df["map_excluded"].sum()
    )

    missing_count = int(
        len(missing)
    )

    # =========================================================================
    # Диагностика в консоль
    # =========================================================================

    print()
    print(
        "=" * 100
    )

    print(
        "КООРДИНАТЫ СКЛАДОВ"
    )

    print(
        "=" * 100
    )

    print(
        f"Всего складов: {total_count}"
    )

    print(
        f"На карте: {mapped_count}"
    )

    print(
        f"Исключено сознательно: {excluded_count}"
    )

    print(
        f"Без координат: {missing_count}"
    )

    # -------------------------------------------------------------------------
    # Исключённые
    # -------------------------------------------------------------------------

    if not excluded.empty:
        print()

        print(
            "ИСКЛЮЧЕНЫ ИЗ КАРТЫ:"
        )

        print(
            "-" * 100
        )

        for _, row in excluded.iterrows():
            print(
                f"{row['region']} | "
                f"{row['warehouse']}"
            )

    # -------------------------------------------------------------------------
    # Реально отсутствующие координаты
    # -------------------------------------------------------------------------

    if not missing.empty:
        print()

        print(
            "СКЛАДЫ БЕЗ КООРДИНАТ:"
        )

        print(
            "-" * 100
        )

        for _, row in missing.iterrows():
            print(
                f"{row['region']} | "
                f"{row['warehouse']}"
            )

    print(
        "=" * 100
    )

    print()

    return df

# =============================================================================
# СПИСОК СКЛАДОВ
# =============================================================================

def get_warehouse_options(
    report_date,
) -> list[str]:

    with get_duckdb_conn_with_opt() as con:
        rows = con.execute(
            """
            SELECT DISTINCT
                TRIM(
                    warehouse_name
                ) AS warehouse_name

            FROM stocks.unpacked_stocks

            WHERE
                date_from::DATE
                    = $report_date::DATE

                AND warehouse_name
                    IS NOT NULL

                AND TRIM(
                    warehouse_name
                ) <> ''

            ORDER BY
                warehouse_name
            """,
            {
                "report_date": report_date,
            },
        ).fetchall()

    return [
        _clean_warehouse_name(
            row[0]
        )
        for row in rows
        if row
        and row[0]
    ]


# =============================================================================
# СПИСОК РЕГИОНОВ
# =============================================================================

def get_region_options(
    report_date,
) -> list[str]:

    with get_duckdb_conn_with_opt() as con:
        rows = con.execute(
            """
            SELECT DISTINCT
                COALESCE(
                    NULLIF(
                        TRIM(
                            region_name
                        ),
                        ''
                    ),
                    'Регион не указан'
                ) AS region_name

            FROM stocks.unpacked_stocks

            WHERE
                date_from::DATE
                    = $report_date::DATE

            ORDER BY
                1
            """,
            {
                "report_date": report_date,
            },
        ).fetchall()

    return [
        str(
            row[0]
        )
        for row in rows
        if row
        and row[0]
    ]


# =============================================================================
# ТОВАРЫ ВЫБРАННОГО СКЛАДА
# =============================================================================

def get_warehouse_products(
    report_date,
    warehouse_name,
    brand_list=None,
    cat_list=None,
    gender_list=None,
) -> pd.DataFrame:
    """
    Товары только выбранного склада.

    Уровень строки:

        nm_id
        + chrt_id

    Важно:
    warehouse_stock агрегируем ДО JOIN,
    чтобы справочники не размножали остаток.
    """

    if not warehouse_name:
        return pd.DataFrame()

    warehouse_name = (
        _clean_warehouse_name(
            warehouse_name
        )
    )

    brand_list = (
        brand_list
        or []
    )

    cat_list = (
        cat_list
        or []
    )

    gender_list = (
        gender_list
        or []
    )

    with get_duckdb_conn_with_opt() as con:
        df = con.execute(
            """
            WITH

            warehouse_stock AS (
                SELECT
                    t.nm_id,
                    t.chrt_id,

                    SUM(
                        COALESCE(
                            t.quantity,
                            0
                        )
                    ) AS quantity,

                    SUM(
                        COALESCE(
                            t.in_way_from_client,
                            0
                        )
                    ) AS in_way_from_client,

                    SUM(
                        COALESCE(
                            t.in_way_to_client,
                            0
                        )
                    ) AS in_way_to_client

                FROM stocks.unpacked_stocks t

                WHERE
                    t.date_from::DATE
                        = $report_date::DATE

                    AND TRIM(
                        t.warehouse_name
                    ) = $warehouse_name

                GROUP BY
                    t.nm_id,
                    t.chrt_id
            ),


            brands AS (
                SELECT
                    nm_id,

                    COALESCE(
                        MAX(
                            brand
                        ),
                        'Бренд не указан'
                    ) AS brand

                FROM cards.unpacked_cards

                GROUP BY
                    nm_id
            ),


            nm_usk AS (
                SELECT
                    card_id AS nm_id,
                    usk

                FROM inventories.usk

                WHERE
                    card_id IS NOT NULL
                    AND usk IS NOT NULL

                GROUP BY
                    card_id,
                    usk
            ),


            sales_by_usk AS (
                SELECT
                    usk,

                    SUM(
                        CASE

                            WHEN
                                COALESCE(
                                    cr_rev,
                                    0
                                ) > 0
                            THEN 1

                            WHEN
                                COALESCE(
                                    cr_rev,
                                    0
                                ) < 0
                            THEN -1

                            ELSE 0

                        END
                    ) AS sales_qty_7d

                FROM inventories.inv_gl_final

                WHERE
                    date_from::DATE
                        BETWEEN
                        (
                            $report_date::DATE
                            - INTERVAL 6 DAY
                        )
                        AND
                        $report_date::DATE

                    AND COALESCE(
                        cr_rev,
                        0
                    ) <> 0

                GROUP BY
                    usk
            ),


            sales_by_nm AS (
                SELECT
                    nu.nm_id,

                    SUM(
                        COALESCE(
                            s.sales_qty_7d,
                            0
                        )
                    ) AS sales_qty_7d

                FROM nm_usk nu

                LEFT JOIN sales_by_usk s
                    ON s.usk = nu.usk

                GROUP BY
                    nu.nm_id
            ),


            total_stock_nm AS (
                SELECT
                    nm_id,

                    SUM(
                        COALESCE(
                            quantity,
                            0
                        )
                    ) AS total_stock

                FROM stocks.unpacked_stocks

                WHERE
                    date_from::DATE
                        = $report_date::DATE

                GROUP BY
                    nm_id
            )


            SELECT
                COALESCE(
                    b.brand,
                    'Бренд не указан'
                ) AS "Бренд",

                COALESCE(
                    p.subject_name,
                    'Категория не указана'
                ) AS "Категория",

                COALESCE(
                    p.gender,
                    'Пол не указан'
                ) AS "Пол",

                COALESCE(
                    p.sa_name,
                    ''
                ) AS "Артикул",

                COALESCE(
                    p.title,
                    ''
                ) AS "Наименование",

                COALESCE(
                    sz.tech_size,
                    ''
                ) AS "Размер",

                ws.quantity
                    AS "Остаток",

                ws.in_way_from_client
                    AS "В пути от клиента",

                ws.in_way_to_client
                    AS "В пути к клиенту",

                (
                    ws.quantity
                    +
                    ws.in_way_from_client
                    +
                    ws.in_way_to_client
                ) AS "Итого",

                COALESCE(
                    s7.sales_qty_7d,
                    0
                ) AS "Продажи 7 дней",

                CASE
                    WHEN
                        COALESCE(
                            s7.sales_qty_7d,
                            0
                        ) > 0

                    THEN ROUND(
                        COALESCE(
                            ts.total_stock,
                            0
                        )
                        * 7.0
                        /
                        s7.sales_qty_7d,
                        1
                    )

                    ELSE NULL

                END AS "Оборачиваемость",

                ws.nm_id
                    AS "NM ID",

                ws.chrt_id
                    AS "Chrt ID"

            FROM warehouse_stock ws

            LEFT JOIN cards.product p
                ON p.nm_id = ws.nm_id

            LEFT JOIN cards.sizes sz
                ON sz.chrt_id = ws.chrt_id

            LEFT JOIN brands b
                ON b.nm_id = ws.nm_id

            LEFT JOIN sales_by_nm s7
                ON s7.nm_id = ws.nm_id

            LEFT JOIN total_stock_nm ts
                ON ts.nm_id = ws.nm_id

            WHERE
                (
                    ws.quantity
                    +
                    ws.in_way_from_client
                    +
                    ws.in_way_to_client
                ) > 0

            ORDER BY
                ws.quantity DESC,
                b.brand,
                p.title,
                sz.tech_size
            """,
            {
                "report_date": (
                    report_date
                ),

                "warehouse_name": (
                    warehouse_name
                ),
            },
        ).df()

    # =========================================================================
    # Фильтры приложения
    # =========================================================================

    if (
        brand_list
        and "Бренд" in df.columns
    ):
        df = df[
            df["Бренд"].isin(
                brand_list
            )
        ]

    if (
        cat_list
        and "Категория" in df.columns
    ):
        df = df[
            df["Категория"].isin(
                cat_list
            )
        ]

    if (
        gender_list
        and "Пол" in df.columns
    ):
        df = df[
            df["Пол"].isin(
                gender_list
            )
        ]

    return df.reset_index(
        drop=True
    )