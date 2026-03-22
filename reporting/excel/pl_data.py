# reporting/excel/pl_data.py

from django.db import connection
import pandas as pd


def get_pl_report(date_to=None):
    """
    Возвращает DataFrame для P&L отчета в формате manpack:
    index = статьи P&L
    columns = Note, FYE YYYY..., YTD YYYY..., MTD YYYY..., Diff abs, Diff rel,
              MTD Diff abs, MTD Diff rel
    """

    if date_to is None:
        with connection.cursor() as cur:
            cur.execute("SELECT MAX(date_from)::date FROM public.pl_for_csv")
            date_to = cur.fetchone()[0]

    q = """
    WITH current_params AS (
        SELECT
            %s::date AS max_date,
            EXTRACT(YEAR FROM %s::date)::int AS current_year
    ),

    base AS (
        SELECT
            p.date_from,
            EXTRACT(YEAR FROM p.date_from)::int AS year,
            substring(p.account_name from '^\\d+') AS account_code,
            p.amount
        FROM public.pl_for_csv p
        WHERE p.date_from <= %s::date
          AND substring(p.account_name from '^\\d+') IN (
                '410000',
                '420000',
                '510000',
                '520000',
                '610000',
                '620000',
                '630000'
          )
    ),

    fye_pivot AS (
        SELECT
            year,
            COALESCE(SUM(CASE WHEN account_code = '410000' THEN amount END), 0) AS revenue,
            COALESCE(SUM(CASE WHEN account_code = '510000' THEN amount END), 0) AS cogs_goods,
            COALESCE(SUM(CASE WHEN account_code = '520000' THEN amount END), 0) AS cogs_real,
            COALESCE(SUM(CASE WHEN account_code = '610000' THEN amount END), 0) AS overhead,
            COALESCE(SUM(CASE WHEN account_code = '620000' THEN amount END), 0) AS ga,
            COALESCE(SUM(CASE WHEN account_code = '420000' THEN amount END), 0) AS other_income_expense,
            COALESCE(SUM(CASE WHEN account_code = '630000' THEN amount END), 0) AS fin_expense
        FROM base
        GROUP BY year
    ),

    ytd_pivot AS (
        SELECT
            b.year,
            COALESCE(SUM(CASE WHEN b.account_code = '410000' THEN b.amount END), 0) AS revenue,
            COALESCE(SUM(CASE WHEN b.account_code = '510000' THEN b.amount END), 0) AS cogs_goods,
            COALESCE(SUM(CASE WHEN b.account_code = '520000' THEN b.amount END), 0) AS cogs_real,
            COALESCE(SUM(CASE WHEN b.account_code = '610000' THEN b.amount END), 0) AS overhead,
            COALESCE(SUM(CASE WHEN b.account_code = '620000' THEN b.amount END), 0) AS ga,
            COALESCE(SUM(CASE WHEN b.account_code = '420000' THEN b.amount END), 0) AS other_income_expense,
            COALESCE(SUM(CASE WHEN b.account_code = '630000' THEN b.amount END), 0) AS fin_expense
        FROM base b
        CROSS JOIN current_params p
        WHERE b.year IN (p.current_year, p.current_year - 1)
          AND b.date_from <= (
                make_date(
                    b.year,
                    EXTRACT(MONTH FROM p.max_date)::int,
                    LEAST(
                        EXTRACT(DAY FROM p.max_date)::int,
                        EXTRACT(DAY FROM (
                            date_trunc('month', make_date(b.year, EXTRACT(MONTH FROM p.max_date)::int, 1))
                            + interval '1 month - 1 day'
                        ))::int
                    )
                )
          )
        GROUP BY b.year
    ),

    mtd_pivot AS (
        SELECT
            b.year,
            COALESCE(SUM(CASE WHEN b.account_code = '410000' THEN b.amount END), 0) AS revenue,
            COALESCE(SUM(CASE WHEN b.account_code = '510000' THEN b.amount END), 0) AS cogs_goods,
            COALESCE(SUM(CASE WHEN b.account_code = '520000' THEN b.amount END), 0) AS cogs_real,
            COALESCE(SUM(CASE WHEN b.account_code = '610000' THEN b.amount END), 0) AS overhead,
            COALESCE(SUM(CASE WHEN b.account_code = '620000' THEN b.amount END), 0) AS ga,
            COALESCE(SUM(CASE WHEN b.account_code = '420000' THEN b.amount END), 0) AS other_income_expense,
            COALESCE(SUM(CASE WHEN b.account_code = '630000' THEN b.amount END), 0) AS fin_expense
        FROM base b
        CROSS JOIN current_params p
        WHERE b.year IN (p.current_year, p.current_year - 1)
          AND b.date_from >= make_date(
                b.year,
                EXTRACT(MONTH FROM p.max_date)::int,
                1
          )
          AND b.date_from <= (
                make_date(
                    b.year,
                    EXTRACT(MONTH FROM p.max_date)::int,
                    LEAST(
                        EXTRACT(DAY FROM p.max_date)::int,
                        EXTRACT(DAY FROM (
                            date_trunc('month', make_date(b.year, EXTRACT(MONTH FROM p.max_date)::int, 1))
                            + interval '1 month - 1 day'
                        ))::int
                    )
                )
          )
        GROUP BY b.year
    ),

    fye_rows AS (
        SELECT year, 'FYE'::text AS period_type, 'Выручка от основной деятельности'::text AS row_name, revenue::numeric AS value FROM fye_pivot
        UNION ALL
        SELECT year, 'FYE', 'Себестоимость проданных товаров', cogs_goods FROM fye_pivot
        UNION ALL
        SELECT year, 'FYE', 'Себестоимость реализации', cogs_real FROM fye_pivot
        UNION ALL
        SELECT year, 'FYE', 'Валовая прибыль', revenue + cogs_goods + cogs_real FROM fye_pivot
        UNION ALL
        SELECT year, 'FYE', 'Рентабельность продаж',
               CASE WHEN revenue = 0 THEN NULL ELSE (revenue + cogs_goods + cogs_real) / revenue END
        FROM fye_pivot
        UNION ALL
        SELECT year, 'FYE', 'Накладные расходы', overhead FROM fye_pivot
        UNION ALL
        SELECT year, 'FYE', 'Корпоративные расходы (G&A)', ga FROM fye_pivot
        UNION ALL
        SELECT year, 'FYE', 'EBITDA', revenue + cogs_goods + cogs_real + overhead + ga FROM fye_pivot
        UNION ALL
        SELECT year, 'FYE', 'EBITDA MARGIN',
               CASE WHEN revenue = 0 THEN NULL ELSE (revenue + cogs_goods + cogs_real + overhead + ga) / revenue END
        FROM fye_pivot
        UNION ALL
        SELECT year, 'FYE', 'Прочие доходы и расходы', other_income_expense FROM fye_pivot
        UNION ALL
        SELECT year, 'FYE', 'EBITDA Adjusted',
               revenue + cogs_goods + cogs_real + overhead + ga + other_income_expense
        FROM fye_pivot
        UNION ALL
        SELECT year, 'FYE', 'Финансовые расходы', fin_expense FROM fye_pivot
        UNION ALL
        SELECT year, 'FYE', 'Налог на прибыль',
               CASE
                   WHEN (revenue + cogs_goods + cogs_real + overhead + ga + other_income_expense + fin_expense) > 0
                   THEN (revenue + cogs_goods + cogs_real + overhead + ga + other_income_expense + fin_expense) * -0.25
                   ELSE 0
               END
        FROM fye_pivot
        UNION ALL
        SELECT year, 'FYE', 'Чистая прибыль / убыток',
               (
                   revenue + cogs_goods + cogs_real + overhead + ga
                   + other_income_expense
                   + fin_expense
                   + CASE
                       WHEN (revenue + cogs_goods + cogs_real + overhead + ga + other_income_expense + fin_expense) > 0
                       THEN (revenue + cogs_goods + cogs_real + overhead + ga + other_income_expense + fin_expense) * -0.25
                       ELSE 0
                     END
               )
        FROM fye_pivot
    ),

    ytd_rows AS (
        SELECT year, 'YTD'::text AS period_type, 'Выручка от основной деятельности'::text AS row_name, revenue::numeric AS value FROM ytd_pivot
        UNION ALL
        SELECT year, 'YTD', 'Себестоимость проданных товаров', cogs_goods FROM ytd_pivot
        UNION ALL
        SELECT year, 'YTD', 'Себестоимость реализации', cogs_real FROM ytd_pivot
        UNION ALL
        SELECT year, 'YTD', 'Валовая прибыль', revenue + cogs_goods + cogs_real FROM ytd_pivot
        UNION ALL
        SELECT year, 'YTD', 'Рентабельность продаж',
               CASE WHEN revenue = 0 THEN NULL ELSE (revenue + cogs_goods + cogs_real) / revenue END
        FROM ytd_pivot
        UNION ALL
        SELECT year, 'YTD', 'Накладные расходы', overhead FROM ytd_pivot
        UNION ALL
        SELECT year, 'YTD', 'Корпоративные расходы (G&A)', ga FROM ytd_pivot
        UNION ALL
        SELECT year, 'YTD', 'EBITDA', revenue + cogs_goods + cogs_real + overhead + ga FROM ytd_pivot
        UNION ALL
        SELECT year, 'YTD', 'EBITDA MARGIN',
               CASE WHEN revenue = 0 THEN NULL ELSE (revenue + cogs_goods + cogs_real + overhead + ga) / revenue END
        FROM ytd_pivot
        UNION ALL
        SELECT year, 'YTD', 'Прочие доходы и расходы', other_income_expense FROM ytd_pivot
        UNION ALL
        SELECT year, 'YTD', 'EBITDA Adjusted',
               revenue + cogs_goods + cogs_real + overhead + ga + other_income_expense
        FROM ytd_pivot
        UNION ALL
        SELECT year, 'YTD', 'Финансовые расходы', fin_expense FROM ytd_pivot
        UNION ALL
        SELECT year, 'YTD', 'Налог на прибыль',
               CASE
                   WHEN (revenue + cogs_goods + cogs_real + overhead + ga + other_income_expense + fin_expense) > 0
                   THEN (revenue + cogs_goods + cogs_real + overhead + ga + other_income_expense + fin_expense) * -0.25
                   ELSE 0
               END
        FROM ytd_pivot
        UNION ALL
        SELECT year, 'YTD', 'Чистая прибыль / убыток',
               (
                   revenue + cogs_goods + cogs_real + overhead + ga
                   + other_income_expense
                   + fin_expense
                   + CASE
                       WHEN (revenue + cogs_goods + cogs_real + overhead + ga + other_income_expense + fin_expense) > 0
                       THEN (revenue + cogs_goods + cogs_real + overhead + ga + other_income_expense + fin_expense) * -0.25
                       ELSE 0
                     END
               )
        FROM ytd_pivot
    ),

    mtd_rows AS (
        SELECT year, 'MTD'::text AS period_type, 'Выручка от основной деятельности'::text AS row_name, revenue::numeric AS value FROM mtd_pivot
        UNION ALL
        SELECT year, 'MTD', 'Себестоимость проданных товаров', cogs_goods FROM mtd_pivot
        UNION ALL
        SELECT year, 'MTD', 'Себестоимость реализации', cogs_real FROM mtd_pivot
        UNION ALL
        SELECT year, 'MTD', 'Валовая прибыль', revenue + cogs_goods + cogs_real FROM mtd_pivot
        UNION ALL
        SELECT year, 'MTD', 'Рентабельность продаж',
               CASE WHEN revenue = 0 THEN NULL ELSE (revenue + cogs_goods + cogs_real) / revenue END
        FROM mtd_pivot
        UNION ALL
        SELECT year, 'MTD', 'Накладные расходы', overhead FROM mtd_pivot
        UNION ALL
        SELECT year, 'MTD', 'Корпоративные расходы (G&A)', ga FROM mtd_pivot
        UNION ALL
        SELECT year, 'MTD', 'EBITDA', revenue + cogs_goods + cogs_real + overhead + ga FROM mtd_pivot
        UNION ALL
        SELECT year, 'MTD', 'EBITDA MARGIN',
               CASE WHEN revenue = 0 THEN NULL ELSE (revenue + cogs_goods + cogs_real + overhead + ga) / revenue END
        FROM mtd_pivot
        UNION ALL
        SELECT year, 'MTD', 'Прочие доходы и расходы', other_income_expense FROM mtd_pivot
        UNION ALL
        SELECT year, 'MTD', 'EBITDA Adjusted',
               revenue + cogs_goods + cogs_real + overhead + ga + other_income_expense
        FROM mtd_pivot
        UNION ALL
        SELECT year, 'MTD', 'Финансовые расходы', fin_expense FROM mtd_pivot
        UNION ALL
        SELECT year, 'MTD', 'Налог на прибыль',
               CASE
                   WHEN (revenue + cogs_goods + cogs_real + overhead + ga + other_income_expense + fin_expense) > 0
                   THEN (revenue + cogs_goods + cogs_real + overhead + ga + other_income_expense + fin_expense) * -0.25
                   ELSE 0
               END
        FROM mtd_pivot
        UNION ALL
        SELECT year, 'MTD', 'Чистая прибыль / убыток',
               (
                   revenue + cogs_goods + cogs_real + overhead + ga
                   + other_income_expense
                   + fin_expense
                   + CASE
                       WHEN (revenue + cogs_goods + cogs_real + overhead + ga + other_income_expense + fin_expense) > 0
                       THEN (revenue + cogs_goods + cogs_real + overhead + ga + other_income_expense + fin_expense) * -0.25
                       ELSE 0
                     END
               )
        FROM mtd_pivot
    )

    SELECT
        row_name,
        period_type,
        year,
        ROUND(value, 4) AS value
    FROM (
        SELECT * FROM fye_rows
        UNION ALL
        SELECT * FROM ytd_rows
        UNION ALL
        SELECT * FROM mtd_rows
    ) t
    """

    with connection.cursor() as cur:
        cur.execute(q, [date_to, date_to, date_to])
        rows = cur.fetchall()
        columns = [col[0] for col in cur.description]

    df = pd.DataFrame(rows, columns=columns)

    if df.empty:
        return pd.DataFrame()

    df["period_col"] = df["period_type"] + " " + df["year"].astype(str)
    result = df.pivot(index="row_name", columns="period_col", values="value")

    row_order = [
        "Выручка от основной деятельности",
        "Себестоимость проданных товаров",
        "Себестоимость реализации",
        "Валовая прибыль",
        "Рентабельность продаж",
        "Накладные расходы",
        "Корпоративные расходы (G&A)",
        "EBITDA",
        "EBITDA MARGIN",
        "Прочие доходы и расходы",
        "EBITDA Adjusted",
        "Финансовые расходы",
        "Налог на прибыль",
        "Чистая прибыль / убыток",
    ]
    result = result.reindex(row_order)

    fye_cols = sorted(
        [c for c in result.columns if c.startswith("FYE ")],
        key=lambda x: int(x.split()[1])
    )
    ytd_cols = sorted(
        [c for c in result.columns if c.startswith("YTD ")],
        key=lambda x: int(x.split()[1])
    )
    mtd_cols = sorted(
        [c for c in result.columns if c.startswith("MTD ")],
        key=lambda x: int(x.split()[1])
    )

    result = result[fye_cols + ytd_cols + mtd_cols]
    result.insert(0, "Note", "")

    # YTD diff
    if len(ytd_cols) >= 2:
        prev_ytd = ytd_cols[-2]
        curr_ytd = ytd_cols[-1]

        result["Diff abs"] = result[curr_ytd] - result[prev_ytd]
        result["Diff rel"] = None

        mask = result[prev_ytd].notna() & (result[prev_ytd] != 0)
        result.loc[mask, "Diff rel"] = (
            result.loc[mask, "Diff abs"] / result.loc[mask, prev_ytd]
        )
    else:
        result["Diff abs"] = None
        result["Diff rel"] = None

    # MTD diff
    if len(mtd_cols) >= 2:
        prev_mtd = mtd_cols[-2]
        curr_mtd = mtd_cols[-1]

        result["MTD Diff abs"] = result[curr_mtd] - result[prev_mtd]
        result["MTD Diff rel"] = None

        mask = result[prev_mtd].notna() & (result[prev_mtd] != 0)
        result.loc[mask, "MTD Diff rel"] = (
            result.loc[mask, "MTD Diff abs"] / result.loc[mask, prev_mtd]
        )
    else:
        result["MTD Diff abs"] = None
        result["MTD Diff rel"] = None

    result = result.where(pd.notna(result), None)

    return result
