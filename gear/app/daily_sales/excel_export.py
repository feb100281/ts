# # gear/app/daily_sales/excel_export.py

# from io import BytesIO

# import pandas as pd
# from dash import dcc, Input, Output, State, ALL, no_update

# from .excel_styles import apply_excel_style


# MAIN_EXCEL_DOWNLOAD_ID = "daily-sales-main-excel-download"
# DETAILS_EXCEL_DOWNLOAD_ID = "daily-sales-details-excel-download"


# def _flatten_columns(column_defs):
#     result = []

#     for col in column_defs or []:
#         if "children" in col:
#             result.extend(_flatten_columns(col["children"]))
#             continue

#         field = col.get("field")
#         if not field:
#             continue

#         result.append(
#             {
#                 "field": field,
#                 "header": col.get("headerName", field),
#             }
#         )

#     return result


# def _make_excel(
#     rows,
#     column_defs,
#     sheet_name="Данные",
#     freeze_panes="B2",
# ):
#     df = pd.DataFrame(rows or [])

#     columns = _flatten_columns(column_defs)

#     ordered_fields = [
#         col["field"]
#         for col in columns
#         if col["field"] in df.columns
#     ]

#     rename_map = {
#         col["field"]: col["header"]
#         for col in columns
#         if col["field"] in df.columns
#     }

#     if ordered_fields:
#         df = df[ordered_fields]

#     df = df.rename(columns=rename_map)

#     # USK всегда оставляем как текст,
#     # чтобы Excel не делал 2 знака после запятой
#     if "USK" in df.columns:
#         df["USK"] = df["USK"].astype(str)

#     output = BytesIO()

#     with pd.ExcelWriter(output, engine="openpyxl") as writer:
#         df.to_excel(writer, index=False, sheet_name=sheet_name)

#         ws = writer.sheets[sheet_name]

#         numeric_columns = {
#             idx
#             for idx, column_name in enumerate(df.columns, start=1)
#             if column_name != "USK"
#             and pd.api.types.is_numeric_dtype(df[column_name])
#         }

#         apply_excel_style(
#             ws,
#             freeze_panes=freeze_panes,
#             numeric_columns=numeric_columns,
#         )

#     output.seek(0)
#     return output.read()


# def register_excel_export_callbacks(app, selected_dates_chips_id):
#     @app.callback(
#         Output(MAIN_EXCEL_DOWNLOAD_ID, "data"),
#         Input({"type": "main-dnl", "index": "xls"}, "n_clicks"),
#         State({"type": "dates_grid", "index": "1"}, "virtualRowData"),
#         State({"type": "dates_grid", "index": "1"}, "columnDefs"),
#         prevent_initial_call=True,
#     )
#     def export_main_excel(n_clicks, rows, column_defs):
#         if not n_clicks or not rows:
#             return no_update

#         content = _make_excel(
#             rows=rows,
#             column_defs=column_defs,
#             sheet_name="Продажи за период",
#             freeze_panes="B2",
#         )

#         return dcc.send_bytes(
#             content,
#             filename="daily_sales.xlsx",
#         )

#     @app.callback(
#         Output(DETAILS_EXCEL_DOWNLOAD_ID, "data"),
#         Input({"type": "xls-dnl", "index": ALL}, "n_clicks"),
#         State(selected_dates_chips_id, "value"),
#         State({"type": "dates_grid", "index": "2"}, "virtualRowData"),
#         State({"type": "dates_grid", "index": "2"}, "columnDefs"),
#         prevent_initial_call=True,
#     )
#     def export_details_excel(n_clicks, date_value, rows, column_defs):
#         if not any(n_clicks or []) or not rows:
#             return no_update

#         rows_with_date = [
#             {
#                 "date_from": date_value,
#                 **row,
#             }
#             for row in rows
#         ]

#         column_defs_with_date = [
#             {
#                 "field": "date_from",
#                 "headerName": "Дата",
#             },
#             *column_defs,
#         ]

#         content = _make_excel(
#             rows=rows_with_date,
#             column_defs=column_defs_with_date,
#             sheet_name="Детализация",
#             freeze_panes="F2",
#         )

#         return dcc.send_bytes(
#             content,
#             filename=f"daily_details_{date_value}.xlsx",
#         )



from datetime import date, datetime
from io import BytesIO

import pandas as pd
from dash import (
    ALL,
    Input,
    Output,
    State,
    dcc,
    no_update,
)

from .excel_styles import apply_excel_style


MAIN_EXCEL_DOWNLOAD_ID = (
    "daily-sales-main-excel-download"
)

DETAILS_EXCEL_DOWNLOAD_ID = (
    "daily-sales-details-excel-download"
)


DATE_FIELDS = {
    "date_from",
    "ending_stock_date",
    "first_stock_date",
    "last_stock_date",
}

DATE_HEADERS = {
    "Дата",
    "Дата остатка",
    "Первая дата остатка",
    "Последняя дата в периоде",
}


def _flatten_columns(column_defs):
    result = []

    for column in column_defs or []:
        if "children" in column:
            result.extend(
                _flatten_columns(
                    column["children"]
                )
            )
            continue

        field = column.get("field")

        if not field:
            continue

        result.append(
            {
                "field": field,
                "header": column.get(
                    "headerName",
                    field,
                ),
            }
        )

    return result


def _prepare_dataframe(
    rows,
    column_defs,
):
    df = pd.DataFrame(
        rows or []
    )

    columns = _flatten_columns(
        column_defs
    )

    ordered_fields = [
        column["field"]
        for column in columns
        if column["field"] in df.columns
    ]

    rename_map = {
        column["field"]: column["header"]
        for column in columns
        if column["field"] in df.columns
    }

    if ordered_fields:
        df = df[ordered_fields]

    for field in DATE_FIELDS:
        if field not in df.columns:
            continue

        df[field] = pd.to_datetime(
            df[field],
            errors="coerce",
        )

    df = df.rename(
        columns=rename_map
    )

    if "USK" in df.columns:
        df["USK"] = (
            df["USK"]
            .astype("string")
        )

    return df


def _style_dataframe_sheet(
    writer,
    df,
    sheet_name,
    freeze_panes,
):
    ws = writer.sheets[sheet_name]

    numeric_columns = {
        index
        for index, column_name
        in enumerate(
            df.columns,
            start=1,
        )
        if column_name != "USK"
        and column_name not in DATE_HEADERS
        and pd.api.types.is_numeric_dtype(
            df[column_name]
        )
    }

    apply_excel_style(
        ws,
        freeze_panes=freeze_panes,
        numeric_columns=numeric_columns,
    )

    for column_index, column_name in enumerate(
        df.columns,
        start=1,
    ):
        if column_name not in DATE_HEADERS:
            continue

        for row_index in range(
            2,
            ws.max_row + 1,
        ):
            ws.cell(
                row=row_index,
                column=column_index,
            ).number_format = "dd.mm.yyyy"


def _write_dataframe(
    writer,
    df,
    sheet_name,
    freeze_panes="B2",
):
    safe_name = sheet_name[:31]

    if df.empty:
        empty_df = pd.DataFrame(
            {
                "Информация": [
                    "Нет данных"
                ]
            }
        )

        empty_df.to_excel(
            writer,
            index=False,
            sheet_name=safe_name,
        )

        _style_dataframe_sheet(
            writer=writer,
            df=empty_df,
            sheet_name=safe_name,
            freeze_panes=freeze_panes,
        )

        return

    df.to_excel(
        writer,
        index=False,
        sheet_name=safe_name,
    )

    _style_dataframe_sheet(
        writer=writer,
        df=df,
        sheet_name=safe_name,
        freeze_panes=freeze_panes,
    )


def _make_main_excel(
    rows,
    column_defs,
):
    df = _prepare_dataframe(
        rows=rows,
        column_defs=column_defs,
    )

    output = BytesIO()

    with pd.ExcelWriter(
        output,
        engine="openpyxl",
    ) as writer:
        _write_dataframe(
            writer=writer,
            df=df,
            sheet_name="Продажи по дням",
            freeze_panes="B2",
        )

    output.seek(0)

    return output.read()


def _calculate_period_parameters(
    df,
    start_date,
    end_date,
):
    start_ts = pd.to_datetime(
        start_date,
        errors="coerce",
    )

    end_ts = pd.to_datetime(
        end_date,
        errors="coerce",
    )

    calendar_days = None

    if (
        pd.notna(start_ts)
        and pd.notna(end_ts)
    ):
        calendar_days = (
            end_ts - start_ts
        ).days + 1

    stock_days = None

    if "Дней с остатками" in df.columns:
        values = pd.to_numeric(
            df["Дней с остатками"],
            errors="coerce",
        ).dropna()

        if not values.empty:
            stock_days = int(
                values.max()
            )

    ending_stock_date = None

    if "Дата остатка" in df.columns:
        dates = pd.to_datetime(
            df["Дата остатка"],
            errors="coerce",
        ).dropna()

        if not dates.empty:
            ending_stock_date = dates.max()

    completeness = None

    if (
        calendar_days
        and stock_days is not None
    ):
        completeness = round(
            stock_days
            / calendar_days
            * 100,
            2,
        )

    return pd.DataFrame(
        {
            "Параметр": [
                "Начало периода продаж",
                "Конец периода продаж",
                "Количество календарных дней",
                "Последняя дата остатков",
                "Максимум дней с остатками",
                "Полнота истории остатков, %",
                "Формула оборачиваемости",
                "Состав общего остатка",
                "Обработка товаров без продаж",
                "Дата формирования отчёта",
            ],
            "Значение": [
                start_ts,
                end_ts,
                calendar_days,
                ending_stock_date,
                stock_days,
                completeness,
                (
                    "Сумма ежедневных остатков "
                    "/ чистое количество продаж"
                ),
                (
                    "На складе + в пути к клиенту "
                    "+ в пути от клиента"
                ),
                (
                    "Оборачиваемость не рассчитывается; "
                    "товар выводится отдельным листом"
                ),
                datetime.now(),
            ],
        }
    )


def _make_details_excel(
    rows,
    column_defs,
    start_date,
    end_date,
    is_period,
):
    df = _prepare_dataframe(
        rows=rows,
        column_defs=column_defs,
    )

    output = BytesIO()

    with pd.ExcelWriter(
        output,
        engine="openpyxl",
    ) as writer:
        if not is_period:
            _write_dataframe(
                writer=writer,
                df=df,
                sheet_name="Детализация дня",
                freeze_panes="F2",
            )

            params_df = pd.DataFrame(
                {
                    "Параметр": [
                        "Дата продаж",
                        "Дата остатка",
                        "Расчёт запаса",
                        "Дата формирования",
                    ],
                    "Значение": [
                        pd.to_datetime(
                            start_date,
                            errors="coerce",
                        ),
                        (
                            pd.to_datetime(
                                df["Дата остатка"],
                                errors="coerce",
                            ).max()
                            if (
                                not df.empty
                                and "Дата остатка"
                                in df.columns
                            )
                            else None
                        ),
                        (
                            "Остаток / чистые продажи "
                            "за выбранный день"
                        ),
                        datetime.now(),
                    ],
                }
            )

            _write_dataframe(
                writer=writer,
                df=params_df,
                sheet_name="Параметры",
                freeze_panes="A2",
            )

        else:
            if "Q продаж" in df.columns:
                sales_qty = pd.to_numeric(
                    df["Q продаж"],
                    errors="coerce",
                ).fillna(0)
            else:
                sales_qty = pd.Series(
                    0,
                    index=df.index,
                )

            if "Остаток всего" in df.columns:
                ending_stock = pd.to_numeric(
                    df["Остаток всего"],
                    errors="coerce",
                ).fillna(0)
            else:
                ending_stock = pd.Series(
                    0,
                    index=df.index,
                )

            without_sales_mask = (
                sales_qty <= 0
            ) & (
                ending_stock > 0
            )

            sales_df = df.loc[
                ~without_sales_mask
            ].copy()

            no_sales_df = df.loc[
                without_sales_mask
            ].copy()

            _write_dataframe(
                writer=writer,
                df=sales_df,
                sheet_name=(
                    "Продажи и оборачиваемость"
                ),
                freeze_panes="F2",
            )

            _write_dataframe(
                writer=writer,
                df=no_sales_df,
                sheet_name="Остатки без продаж",
                freeze_panes="F2",
            )

            params_df = (
                _calculate_period_parameters(
                    df=df,
                    start_date=start_date,
                    end_date=end_date,
                )
            )

            _write_dataframe(
                writer=writer,
                df=params_df,
                sheet_name="Параметры",
                freeze_panes="A2",
            )

    output.seek(0)

    return output.read()


def _parse_date_value(date_value):
    if isinstance(
        date_value,
        (list, tuple),
    ):
        values = [
            value
            for value in date_value
            if value
        ]

        if not values:
            return None, None, False

        if len(values) == 1:
            return (
                values[0],
                values[0],
                False,
            )

        start_date = values[0]
        end_date = values[-1]

        return (
            start_date,
            end_date,
            start_date != end_date,
        )

    if not date_value:
        return None, None, False

    value = str(date_value)

    if " — " in value:
        parts = value.split(
            " — ",
            maxsplit=1,
        )

        return (
            parts[0],
            parts[1],
            parts[0] != parts[1],
        )

    if " - " in value:
        parts = value.split(
            " - ",
            maxsplit=1,
        )

        return (
            parts[0],
            parts[1],
            parts[0] != parts[1],
        )

    return value, value, False


def register_excel_export_callbacks(
    app,
    selected_dates_chips_id,
):
    @app.callback(
        Output(
            MAIN_EXCEL_DOWNLOAD_ID,
            "data",
        ),
        Input(
            {
                "type": "main-dnl",
                "index": "xls",
            },
            "n_clicks",
        ),
        State(
            {
                "type": "dates_grid",
                "index": "1",
            },
            "virtualRowData",
        ),
        State(
            {
                "type": "dates_grid",
                "index": "1",
            },
            "columnDefs",
        ),
        prevent_initial_call=True,
    )
    def export_main_excel(
        n_clicks,
        rows,
        column_defs,
    ):
        if (
            not n_clicks
            or not rows
        ):
            return no_update

        content = _make_main_excel(
            rows=rows,
            column_defs=column_defs,
        )

        return dcc.send_bytes(
            content,
            filename="daily_sales.xlsx",
        )

    @app.callback(
        Output(
            DETAILS_EXCEL_DOWNLOAD_ID,
            "data",
        ),
        Input(
            {
                "type": "xls-dnl",
                "index": ALL,
            },
            "n_clicks",
        ),
        State(
            selected_dates_chips_id,
            "value",
        ),
        State(
            {
                "type": "dates_grid",
                "index": "2",
            },
            "virtualRowData",
        ),
        State(
            {
                "type": "dates_grid",
                "index": "2",
            },
            "columnDefs",
        ),
        prevent_initial_call=True,
    )
    def export_details_excel(
        n_clicks,
        date_value,
        rows,
        column_defs,
    ):
        if (
            not any(n_clicks or [])
            or not rows
        ):
            return no_update

        (
            start_date,
            end_date,
            is_period,
        ) = _parse_date_value(
            date_value
        )

        if not start_date:
            start_date = date.today().isoformat()

        if not end_date:
            end_date = start_date

        content = _make_details_excel(
            rows=rows,
            column_defs=column_defs,
            start_date=start_date,
            end_date=end_date,
            is_period=is_period,
        )

        if is_period:
            filename = (
                f"daily_details_"
                f"{start_date}_"
                f"{end_date}.xlsx"
            )
        else:
            filename = (
                f"daily_details_"
                f"{start_date}.xlsx"
            )

        return dcc.send_bytes(
            content,
            filename=filename,
        )