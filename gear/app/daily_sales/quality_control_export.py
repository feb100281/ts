# gear/app/daily_sales/quality_control_export.py

"""
Выгрузка проблемных позиций из блока "Контроль данных"
(summary.py) в Excel.

Три листа:

- "Без себестоимости" — no_cost > 0;
- "Нет на складе"     — no_stocks > 0, плюс УПД, по которым
                         товар когда-либо приходил (если найдены);
- "Нет прихода"       — no_income > 0.

Источник данных — тот же метод, что уже используется
для детализации по артикулам (day_details / period_details):

    DashboardData().get_period_details(...)

Это gear/app/data/queries.py: DETAILS_DAY / DETAILS_PERIOD.
В них построчно:

    t.usk AS nm_id,
    t.usk,
    ...
    LEFT JOIN inventories.wb_product w
        ON w.card_id = t.usk

То есть USK, который приходит в столбце "usk", — это и есть
NM ID (id карточки в inventories.wb_product, откуда берутся
"Наименование"/"Бренд"). Отдельно ходить в inventories.usk
за этим соответствием не нужно (и не нужно было — та таблица
для другого и просто не давала совпадений, из-за чего
NM ID/Артикул/УПД оставались пустыми).

Артикул в этой выгрузке = NM ID (в терминах этого проекта
USK == SKU == NM ID — одно и то же число).

УПД по nm_id достаём напрямую:

    inventories.upd_income -> inventories.upd_documents

(тот же путь, что и в last_income в stocks/data.py) —
без ограничения по периоду, чтобы найти вообще любой приход
этой позиции когда-либо, а не только за выбранный период.
"""

from __future__ import annotations

from datetime import date
from io import BytesIO

import pandas as pd
from dash import dcc, Input, Output, State, no_update
from conns import get_duckdb_conn_with_opt

from ..data.base import DashboardData
from .excel_styles import apply_excel_style


QUALITY_CONTROL_EXPORT_BTN_ID = "quality-control-export-btn"
QUALITY_CONTROL_EXPORT_DOWNLOAD_ID = "quality-control-export-download"


# ============================================================
# ОПИСАНИЕ ЛИСТОВ
# ============================================================

_SHEETS = (
    {
        "key": "no_cost",
        "sheet_name": "Без себестоимости",
        "qty_header": "Q без себест.",
        "with_upd": False,
    },
    {
        "key": "no_stocks",
        "sheet_name": "Нет на складе",
        "qty_header": "Нет на складе",
        "with_upd": True,
    },
    {
        "key": "no_income",
        "sheet_name": "Нет прихода",
        "qty_header": "Нет прихода",
        "with_upd": False,
    },
)

_UPD_EMPTY_COLUMNS = [
    "nm_id",
    "Номер УПД",
    "Дата последнего прихода",
    "Кол-во УПД",
]


# ============================================================
# ДАННЫЕ
# ============================================================

def _fetch_details(start, end, cat_list, brand_list, gender_list):
    with DashboardData() as dashboard:
        df = dashboard.get_period_details(
            start=start,
            end=end,
            cat_list=cat_list,
            brand_list=brand_list,
            gender_list=gender_list,
        )

    return df if df is not None else pd.DataFrame()


def _fetch_upd_info(nm_ids):
    """
    По списку nm_id (id карточки = USK) достаёт ВСЕ УПД,
    по которым товар когда-либо приходил — без ограничения
    по периоду.

    Путь тот же, что и в last_income (stocks/data.py):
    inventories.upd_income -> inventories.upd_documents.
    """

    clean_ids = sorted(
        {
            int(value)
            for value in nm_ids
            if pd.notna(value)
        }
    )

    if not clean_ids:
        return pd.DataFrame(columns=_UPD_EMPTY_COLUMNS)

    placeholders = ", ".join(["?"] * len(clean_ids))

    query = f"""
        SELECT
            ui.nm_id AS nm_id,
            ud.date::DATE AS upd_date,

            COALESCE(
                CAST(ud.number AS VARCHAR),
                ''
            ) AS upd_number,

            ud.id AS upd_document_id

        FROM inventories.upd_income ui

        INNER JOIN inventories.upd_documents ud
            ON ud.id = ui.upd_document_id

        WHERE
            ui.nm_id IN ({placeholders})

        ORDER BY
            ui.nm_id,
            ud.date
    """

    with get_duckdb_conn_with_opt() as con:
        raw = con.execute(query, clean_ids).df()

    if raw.empty:
        return pd.DataFrame(columns=_UPD_EMPTY_COLUMNS)

    def _summarize(group):
        parts = []

        for _, row in group.iterrows():
            upd_date = row["upd_date"]

            date_text = (
                pd.to_datetime(upd_date).strftime("%d.%m.%Y")
                if pd.notna(upd_date)
                else ""
            )

            number = row["upd_number"] or "б/н"

            parts.append(
                f"{number} от {date_text}"
                if date_text
                else number
            )

        return pd.Series(
            {
                "Номер УПД": "; ".join(parts),
                "Дата последнего прихода": group["upd_date"].max(),
                "Кол-во УПД": group["upd_document_id"].nunique(),
            }
        )

    grouped = (
        raw.groupby("nm_id", as_index=False)
        .apply(_summarize)
    )

    # pandas >= 2.1 переносит группирующую колонку
    # в конец / индекс по-разному в зависимости от версии —
    # приводим к предсказуемому виду.
    if "nm_id" not in grouped.columns:
        grouped = grouped.reset_index()

    return grouped[
        [
            "nm_id",
            "Номер УПД",
            "Дата последнего прихода",
            "Кол-во УПД",
        ]
    ]


# ============================================================
# ФОРМИРОВАНИЕ ЛИСТОВ
# ============================================================

def _prepare_sheet_df(
    df,
    qty_field,
    qty_header,
    upd_map=None,
):
    empty_columns = [
        "Наименование",
        "Артикул",
        qty_header,
        "Бренд",
        "NM ID",
    ]

    if upd_map is not None:
        empty_columns.extend(
            [
                "Номер УПД",
                "Дата последнего прихода",
                "Кол-во УПД",
            ]
        )

    if df.empty or qty_field not in df.columns:
        return pd.DataFrame(columns=empty_columns)

    qty = pd.to_numeric(
        df[qty_field],
        errors="coerce",
    ).fillna(0)

    subset = df.loc[qty > 0].copy()

    if subset.empty:
        return pd.DataFrame(columns=empty_columns)

    subset["_qty"] = qty.loc[qty > 0]

    # USK == NM ID == "артикул" в терминах этого проекта
    # (см. DETAILS_DAY/DETAILS_PERIOD: t.usk AS nm_id, t.usk).
    nm_id_numeric = pd.to_numeric(
        subset.get("usk"),
        errors="coerce",
    )

    nm_id_text = (
        nm_id_numeric.astype("Int64").astype("string")
    )

    result = pd.DataFrame(
        {
            "Наименование": subset.get("title", ""),
            "Артикул": nm_id_text,
            qty_header: subset["_qty"].round().astype("Int64"),
            "Бренд": subset.get("brand", ""),
            "NM ID": nm_id_text,
        }
    )

    if upd_map is not None:
        if not upd_map.empty:
            result = result.merge(
                upd_map.rename(
                    columns={"nm_id": "_nm_id_for_merge"}
                ),
                left_on=nm_id_numeric,
                right_on="_nm_id_for_merge",
                how="left",
            ).drop(columns=["_nm_id_for_merge"])
        else:
            result["Номер УПД"] = ""
            result["Дата последнего прихода"] = pd.NaT
            result["Кол-во УПД"] = 0

        result["Номер УПД"] = result["Номер УПД"].fillna("")
        result["Кол-во УПД"] = (
            result["Кол-во УПД"].fillna(0).astype("Int64")
        )

    return result.reset_index(drop=True)


def _write_sheet(writer, df, sheet_name):
    safe_name = sheet_name[:31]

    display_df = df

    if display_df.empty:
        display_df = pd.DataFrame(
            {
                "Информация": [
                    "Нет позиций — по этому показателю всё в порядке"
                ]
            }
        )

    display_df.to_excel(
        writer,
        index=False,
        sheet_name=safe_name,
    )

    ws = writer.sheets[safe_name]

    text_columns = {
        "NM ID",
        "Артикул",
        "Номер УПД",
        "Наименование",
        "Бренд",
    }

    numeric_columns = {
        idx
        for idx, column_name in enumerate(
            display_df.columns,
            start=1,
        )
        if column_name not in text_columns
        and column_name != "Дата последнего прихода"
        and pd.api.types.is_numeric_dtype(display_df[column_name])
    }

    # Товар штучный — количество всегда целое число,
    # копейки (2 знака после запятой) тут не нужны.
    integer_columns = {
        idx
        for idx in numeric_columns
        if pd.api.types.is_integer_dtype(
            display_df[display_df.columns[idx - 1]]
        )
    }

    apply_excel_style(
        ws,
        freeze_panes="A2",
        numeric_columns=numeric_columns,
    )

    for col_idx in integer_columns:
        for row_idx in range(2, ws.max_row + 1):
            ws.cell(row=row_idx, column=col_idx).number_format = "#,##0"

    if "Дата последнего прихода" in display_df.columns:
        date_col_idx = (
            list(display_df.columns).index(
                "Дата последнего прихода"
            )
            + 1
        )

        for row_idx in range(2, ws.max_row + 1):
            cell = ws.cell(row=row_idx, column=date_col_idx)

            if cell.value:
                cell.number_format = "dd.mm.yyyy"


# ============================================================
# ПУБЛИЧНАЯ ФУНКЦИЯ
# ============================================================

def make_quality_control_excel(
    start,
    end,
    cat_list,
    brand_list,
    gender_list,
):
    df = _fetch_details(
        start=start,
        end=end,
        cat_list=cat_list,
        brand_list=brand_list,
        gender_list=gender_list,
    )

    # УПД ищем только для позиций "Нет на складе" —
    # именно по ним просили показать, чем приходил товар.
    # Ищем по ВСЕМ УПД когда-либо (без ограничения периодом
    # выбранным в календаре).
    if not df.empty and "no_stocks" in df.columns:
        no_stocks_qty = pd.to_numeric(
            df["no_stocks"],
            errors="coerce",
        ).fillna(0)

        no_stocks_nm_ids = pd.to_numeric(
            df.loc[no_stocks_qty > 0, "usk"],
            errors="coerce",
        )

        upd_map = _fetch_upd_info(no_stocks_nm_ids)
    else:
        upd_map = pd.DataFrame(columns=_UPD_EMPTY_COLUMNS)

    output = BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for sheet in _SHEETS:
            sheet_df = _prepare_sheet_df(
                df=df,
                qty_field=sheet["key"],
                qty_header=sheet["qty_header"],
                upd_map=upd_map if sheet["with_upd"] else None,
            )

            _write_sheet(
                writer=writer,
                df=sheet_df,
                sheet_name=sheet["sheet_name"],
            )

    output.seek(0)

    return output.read()


# ============================================================
# CALLBACK
# ============================================================

def register_quality_control_export_callbacks(app, filters):
    @app.callback(
        Output(QUALITY_CONTROL_EXPORT_DOWNLOAD_ID, "data"),
        Input(QUALITY_CONTROL_EXPORT_BTN_ID, "n_clicks"),
        State(filters.date_picker_id, "value"),
        State(filters.cat_multy_id, "value"),
        State(filters.brand_multy_id, "value"),
        State(filters.gender_multy_id, "value"),
        prevent_initial_call=True,
    )
    def export_quality_control(
        n_clicks,
        date_range,
        cat_list,
        brand_list,
        gender_list,
    ):
        if not n_clicks:
            return no_update

        if date_range and len(date_range) == 2:
            start = date_range[0]
            end = date_range[1]
        else:
            start = date(2024, 1, 1)
            end = date.today()

        content = make_quality_control_excel(
            start=start,
            end=end,
            cat_list=cat_list,
            brand_list=brand_list,
            gender_list=gender_list,
        )

        file_start = pd.to_datetime(start).strftime("%Y-%m-%d")
        file_end = pd.to_datetime(end).strftime("%Y-%m-%d")

        return dcc.send_bytes(
            content,
            filename=(
                f"data_control_{file_start}_{file_end}.xlsx"
            ),
        )
