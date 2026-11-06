# gear/app/costs_control/article_report/data.py
from __future__ import annotations

from typing import Iterable

import pandas as pd

from conns import (
    get_duckdb_conn_with_opt,
)


def get_article_history(
    articles: Iterable[str],
) -> pd.DataFrame:
    """
    Получает информацию по
    артикулам поставщика.

    Связь:

    Article
        -> inventories.usk_upd.upd_sa_name
        -> inventories.usk_upd.usk
        -> inventories.upd_income.nm_id
        -> inventories.upd_documents
    """

    article_list = [
        str(
            article
        ).strip()
        for article in articles
        if (
            article is not None
            and str(
                article
            ).strip()
        )
    ]

    if not article_list:
        return pd.DataFrame()

    values_sql = ", ".join(
        ["(?)"]
        * len(
            article_list
        )
    )

    query = f"""
        WITH input_articles AS (
            SELECT
                CAST(
                    article AS VARCHAR
                ) AS article

            FROM (
                VALUES
                    {values_sql}
            ) AS source(article)
        ),

        article_mapping AS (
            SELECT DISTINCT
                a.article
                    AS "Article",

                u.usk
                    AS nm_id

            FROM input_articles a

            LEFT JOIN inventories.usk_upd u
                ON TRIM(
                    CAST(
                        u.upd_sa_name
                        AS VARCHAR
                    )
                ) = TRIM(
                    a.article
                )
        ),

        products AS (
            SELECT
                card_id
                    AS nm_id,

                ANY_VALUE(
                    title
                ) AS title

            FROM inventories.wb_product

            WHERE
                card_id IS NOT NULL

            GROUP BY
                card_id
        )

        SELECT
            m."Article",

            m.nm_id
                AS "NM ID",

            COALESCE(
                p.title,
                CASE
                    WHEN
                        m.nm_id
                        IS NULL
                    THEN
                        'Артикул не сопоставлен с NM ID'
                    ELSE
                        'Наименование не указано'
                END
            ) AS "Наименование",

            ud.date::DATE
                AS "Дата УПД",

            ui.upd_document_id
                AS "ID УПД",

            COALESCE(
                CAST(
                    ud.number
                    AS VARCHAR
                ),
                ''
            ) AS "Номер УПД",

            COALESCE(
                cp.name,
                ''
            ) AS "Поставщик",

            ui.upd_qty
                AS "Количество, шт",

            ROUND(
                ui.upd_price_vatless,
                2
            ) AS "Цена, бух",

            ROUND(
                ui.man_cost_per_unit,
                2
            ) AS "Цена, упр",

            ROUND(
                ui.upd_amount_vatless,
                2
            ) AS "Сумма без НДС"

        FROM article_mapping m

        LEFT JOIN products p
            ON p.nm_id = m.nm_id

        LEFT JOIN inventories.upd_income ui
            ON ui.nm_id = m.nm_id

        LEFT JOIN inventories.upd_documents ud
            ON ud.id = ui.upd_document_id

        LEFT JOIN pg.counterparties_counterparty cp
            ON cp.id = ud.counterparty_id

        ORDER BY
            m."Article",
            m.nm_id,
            ud.date,
            ui.upd_document_id
    """

    with get_duckdb_conn_with_opt(
        ro=True
    ) as con:
        df = con.execute(
            query,
            article_list,
        ).df()

    if df.empty:
        return df

    df["Article"] = (
        df["Article"]
        .astype(
            "string"
        )
        .str.strip()
    )

    df["NM ID"] = (
        pd.to_numeric(
            df["NM ID"],
            errors="coerce",
        )
        .astype(
            "Int64"
        )
        .astype(
            "string"
        )
    )

    df["ID УПД"] = (
        pd.to_numeric(
            df["ID УПД"],
            errors="coerce",
        )
        .astype(
            "Int64"
        )
        .astype(
            "string"
        )
    )

    df["Дата УПД"] = (
        pd.to_datetime(
            df["Дата УПД"],
            errors="coerce",
        )
    )

    df["Номер УПД"] = (
        df["Номер УПД"]
        .astype(
            "string"
        )
        .fillna(
            ""
        )
    )

    df["Поставщик"] = (
        df["Поставщик"]
        .astype(
            "string"
        )
        .fillna(
            ""
        )
    )

    for column in (
        "Количество, шт",
        "Цена, бух",
        "Цена, упр",
        "Сумма без НДС",
    ):
        df[column] = (
            pd.to_numeric(
                df[column],
                errors="coerce",
            )
        )

    return df


def build_article_summary(
    articles: list[str],
    history_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Формирует агрегированный
    анализ по Article и NM ID.
    """

    input_df = pd.DataFrame(
        {
            "Article": articles,
        }
    )

    result_columns = [
        "Article",
        "NM ID",
        "Наименование",
        "Первая дата УПД",
        "Последняя дата УПД",
        "Количество УПД",
        "Количество, шт",
        "Минимальная цена, бух",
        "Максимальная цена, бух",
        "Средняя цена, бух",
        "Медиана цены, бух",
        "Минимальная цена, упр",
        "Максимальная цена, упр",
        "Средняя цена, упр",
        "Медиана цены, упр",
        "Статус",
    ]

    if history_df.empty:
        result = (
            input_df.copy()
        )

        result[
            "NM ID"
        ] = pd.NA

        result[
            "Наименование"
        ] = (
            "Артикул не найден"
        )

        result[
            "Первая дата УПД"
        ] = pd.NaT

        result[
            "Последняя дата УПД"
        ] = pd.NaT

        result[
            "Количество УПД"
        ] = 0

        result[
            "Количество записей"
        ] = 0

        result[
            "Количество, шт"
        ] = 0

        for column in (
            result_columns
        ):
            if (
                column
                not in result.columns
            ):
                result[
                    column
                ] = pd.NA

        result[
            "Статус"
        ] = (
            "Артикул не сопоставлен"
        )

        return result[
            result_columns
        ]

    work = (
        history_df.copy()
    )

    # Реальные строки УПД.
    real_upd = work[
        work[
            "ID УПД"
        ].notna()
    ].copy()

    # Соответствие Article -> NM ID.
    mapping = (
        work[
            [
                "Article",
                "NM ID",
                "Наименование",
            ]
        ]
        .drop_duplicates()
        .copy()
    )

    summary = (
        mapping.copy()
    )

    if not real_upd.empty:
        group_columns = [
            "Article",
            "NM ID",
        ]

        general = (
            real_upd
            .groupby(
                group_columns,
                dropna=False,
            )
            .agg(
                **{
                    "Первая дата УПД": (
                        "Дата УПД",
                        "min",
                    ),
                    "Последняя дата УПД": (
                        "Дата УПД",
                        "max",
                    ),
                    "Количество УПД": (
                        "ID УПД",
                        "nunique",
                    ),
                    "Количество, шт": (
                        "Количество, шт",
                        "sum",
                    ),
                }
            )
            .reset_index()
        )

        acc_prices = (
            real_upd
            .groupby(
                group_columns,
                dropna=False,
            )[
                "Цена, бух"
            ]
            .agg(
                [
                    "min",
                    "max",
                    "mean",
                    "median",
                ]
            )
            .reset_index()
            .rename(
                columns={
                    "min": (
                        "Минимальная цена, бух"
                    ),
                    "max": (
                        "Максимальная цена, бух"
                    ),
                    "mean": (
                        "Средняя цена, бух"
                    ),
                    "median": (
                        "Медиана цены, бух"
                    ),
                }
            )
        )

        man_prices = (
            real_upd
            .groupby(
                group_columns,
                dropna=False,
            )[
                "Цена, упр"
            ]
            .agg(
                [
                    "min",
                    "max",
                    "mean",
                    "median",
                ]
            )
            .reset_index()
            .rename(
                columns={
                    "min": (
                        "Минимальная цена, упр"
                    ),
                    "max": (
                        "Максимальная цена, упр"
                    ),
                    "mean": (
                        "Средняя цена, упр"
                    ),
                    "median": (
                        "Медиана цены, упр"
                    ),
                }
            )
        )

        
        summary = (
            summary
            .merge(
                general,
                on=group_columns,
                how="left",
            )
            .merge(
                acc_prices,
                on=group_columns,
                how="left",
            )
            .merge(
                man_prices,
                on=group_columns,
                how="left",
            )
        )
    # Возвращаем все Article
    # из исходного файла.
    summary = (
        input_df.merge(
            summary,
            on="Article",
            how="left",
        )
    )

    for column in (
        "Количество УПД",
        "Количество, шт",
    ):
        if (
            column
            not in summary.columns
        ):
            summary[
                column
            ] = 0

        summary[
            column
        ] = (
            pd.to_numeric(
                summary[column],
                errors="coerce",
            )
            .fillna(
                0
            )
        )

    for column in (
        "Первая дата УПД",
        "Последняя дата УПД",
    ):
        if (
            column
            not in summary.columns
        ):
            summary[
                column
            ] = pd.NaT

        summary[
            column
        ] = pd.to_datetime(
            summary[
                column
            ],
            errors="coerce",
        )

    numeric_columns = [
        "Минимальная цена, бух",
        "Максимальная цена, бух",
        "Средняя цена, бух",
        "Медиана цены, бух",
        "Минимальная цена, упр",
        "Максимальная цена, упр",
        "Средняя цена, упр",
        "Медиана цены, упр",
    ]

    for column in (
        numeric_columns
    ):
        if (
            column
            not in summary.columns
        ):
            summary[
                column
            ] = pd.NA

        summary[
            column
        ] = (
            pd.to_numeric(
                summary[
                    column
                ],
                errors="coerce",
            )
            .round(
                2
            )
        )

    if (
        "Наименование"
        not in summary.columns
    ):
        summary[
            "Наименование"
        ] = pd.NA

    summary[
        "Наименование"
    ] = (
        summary[
            "Наименование"
        ]
        .fillna(
            "Артикул не сопоставлен с NM ID"
        )
    )

    def build_status(
        row,
    ):
        nm_id = row.get(
            "NM ID"
        )

        document_count = (
            row.get(
                "Количество УПД",
                0,
            )
        )

        if pd.isna(
            nm_id
        ):
            return (
                "Артикул не сопоставлен"
            )

        if not document_count:
            return (
                "NM ID найден, "
                "УПД не найдены"
            )

        return (
            "Данные найдены"
        )

    summary[
        "Статус"
    ] = summary.apply(
        build_status,
        axis=1,
    )

    return summary[
        result_columns
    ]


def prepare_detail_sheet(
    history_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Подготавливает лист
    детализации УПД.
    """

    columns = [
        "Article",
        "NM ID",
        "Наименование",
        "Дата УПД",
        "Номер УПД",
        "ID УПД",
        "Поставщик",
        "Количество, шт",
        "Цена, бух",
        "Цена, упр",
        "Сумма без НДС",
    ]

    if history_df.empty:
        return pd.DataFrame(
            columns=columns
        )

    detail = (
        history_df.copy()
    )

    # Только реальные УПД.
    detail = detail[
        detail[
            "ID УПД"
        ].notna()
    ].copy()

    detail = detail[
        [
            column
            for column in columns
            if (
                column
                in detail.columns
            )
        ]
    ]

    detail = (
        detail.sort_values(
            by=[
                "Article",
                "Дата УПД",
                "Номер УПД",
            ],
            na_position="last",
        )
    )

    return detail