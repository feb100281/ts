from __future__ import annotations

from io import BytesIO

import pandas as pd
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter


def _prepare_registry(
    df: pd.DataFrame,
) -> pd.DataFrame:
    if df.empty:
        return df.copy()

    columns = {
        "status": "Статус",
        "counterparty_name": "Контрагент",
        "inn": "ИНН",
        "contract_number": "Договор",
        "contract_date": "Дата договора",
        "contract_type": "Тип договора",
        "currency": "Валюта",
        "contract_amount": "Сумма договора",
        "total_drawdown": "Выдано / привлечено",
        "total_repaid": "Погашено",
        "ending_balance": "Основной долг",
        "interest_balance": "Долг по процентам",
        "total_debt": "Общий долг",
        "rate": "Ставка, %",
        "repayment_date": "Дата погашения",
        "days_to_maturity": "Дней до погашения",
        "repayment_profile": "Профиль погашения",
        "compounding": "Компаундинг",
        "penalty_rate": "Штрафная ставка, %",
        "total_interest_accrued": "Начислено процентов",
        "total_interest_repaid": "Погашено процентов",
        "contract_id": "ID договора",
    }

    result = df[
        [
            column
            for column in columns
            if column in df.columns
        ]
    ].copy()

    result = result.rename(columns=columns)

    for column in (
        "Дата договора",
        "Дата погашения",
    ):
        if column in result.columns:
            result[column] = pd.to_datetime(
                result[column],
                errors="coerce",
            ).dt.date

    return result


def build_excel_bytes(
    registry_df: pd.DataFrame,
    transactions_df: pd.DataFrame | None = None,
) -> bytes:
    output = BytesIO()

    with pd.ExcelWriter(
        output,
        engine="openpyxl",
    ) as writer:
        registry = _prepare_registry(
            registry_df
        )
        registry.to_excel(
            writer,
            sheet_name="Реестр займов",
            index=False,
        )

        if (
            transactions_df is not None
            and not transactions_df.empty
        ):
            transactions = (
                transactions_df.copy()
            )
            if "date_from" in transactions.columns:
                transactions["date_from"] = (
                    pd.to_datetime(
                        transactions["date_from"],
                        errors="coerce",
                    ).dt.date
                )

            transactions.to_excel(
                writer,
                sheet_name="Операции",
                index=False,
            )

        for sheet in writer.book.worksheets:
            sheet.freeze_panes = "B2"
            sheet.sheet_view.showGridLines = False

            header_fill = PatternFill(
                fill_type="solid",
                fgColor="E7F1ED",
            )

            for cell in sheet[1]:
                cell.font = Font(
                    name="Roboto Light",
                    size=10,
                    bold=True,
                    color="22312D",
                )
                cell.fill = header_fill
                cell.alignment = Alignment(
                    horizontal="center",
                    vertical="center",
                    wrap_text=True,
                )

            for row in sheet.iter_rows(
                min_row=2
            ):
                for cell in row:
                    cell.font = Font(
                        name="Roboto Light",
                        size=10,
                    )
                    cell.alignment = Alignment(
                        vertical="center",
                    )

                    if isinstance(
                        cell.value,
                        (int, float),
                    ):
                        cell.number_format = (
                            '#,##0.00'
                        )

            for index, column_cells in enumerate(
                sheet.columns,
                start=1,
            ):
                max_length = 0

                for cell in column_cells:
                    value = (
                        ""
                        if cell.value is None
                        else str(cell.value)
                    )
                    max_length = max(
                        max_length,
                        len(value),
                    )

                sheet.column_dimensions[
                    get_column_letter(index)
                ].width = min(
                    max(max_length + 2, 12),
                    34,
                )

    return output.getvalue()
