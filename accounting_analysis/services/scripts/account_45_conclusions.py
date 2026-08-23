# accounting_analysis/services/scripts/account_45_conclusions.py

from __future__ import annotations

from typing import Any

import pandas as pd


def _format_short_rub(value: float | int | None) -> str:
    if value is None:
        return "0 руб."

    value = float(value)
    abs_value = abs(value)

    if abs_value >= 1_000_000_000:
        short_value = value / 1_000_000_000
        suffix = "млрд руб."
    elif abs_value >= 1_000_000:
        short_value = value / 1_000_000
        suffix = "млн руб."
    elif abs_value >= 1_000:
        short_value = value / 1_000
        suffix = "тыс. руб."
    else:
        return f"{value:,.0f} руб.".replace(",", " ")

    if float(short_value).is_integer():
        formatted = f"{short_value:,.0f}"
    else:
        formatted = f"{short_value:,.1f}"

    return f"{formatted} {suffix}".replace(",", " ")


def build_account_45_conclusions(
    items_df: pd.DataFrame,
    summary_df: pd.DataFrame,
    meta: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    conclusions: list[dict[str, Any]] = []

    negative_qty_df = items_df[items_df["is_negative_ending_qty"]].copy()
    negative_amount_df = items_df[items_df["is_negative_ending_amount"]].copy()
    qty_no_amount_df = items_df[items_df["qty_exists_amount_missing_at_end"]].copy()
    amount_no_qty_df = items_df[items_df["amount_exists_qty_missing_at_end"]].copy()

    negative_qty_count = len(negative_qty_df)
    negative_amount_count = len(negative_amount_df)
    qty_no_amount_count = len(qty_no_amount_df)
    amount_no_qty_count = len(amount_no_qty_df)

    negative_qty_abs_sum = abs(negative_qty_df["ending_qty"].fillna(0).sum())

    avg_sale_price = summary_df.loc[
        summary_df["Показатель"] == "Средняя цена продажи за 1 единицу",
        "Значение",
    ]
    avg_sale_price_value = (
        float(avg_sale_price.iloc[0])
        if not avg_sale_price.empty and pd.notna(avg_sale_price.iloc[0])
        else None
    )

    total_issues = (
        negative_qty_count
        + negative_amount_count
        + qty_no_amount_count
        + amount_no_qty_count
    )

    if total_issues == 0:
        conclusions.append(
            {
                "type": "text",
                "text": (
                    "По результатам анализа существенных отклонений по счету 45 не выявлено. "
                    "Отрицательные остатки, расхождения между количеством и стоимостью, "
                    "а также аномалии стоимостного учета отсутствуют."
                ),
            }
        )
        conclusions.append(
            {
                "type": "text",
                "text": (
                    "Количественный и стоимостной учет по счету 45 на конец периода "
                    "выглядит согласованным."
                ),
            }
        )
        conclusions.append(
            {
                "type": "text",
                "text": (
                    "Существенных ограничений для использования данных счета 45 "
                    "в аналитических и управленческих целях по результатам проверки не выявлено."
                ),
            }
        )
        return conclusions

    conclusions.append(
        {
            "type": "text",
            "text": (
                "В ходе анализа ОСВ по счету 45 выявлены отклонения, которые могут указывать "
                "на ошибки в количественном и стоимостном учете товаров."
            ),
        }
    )

    if negative_qty_count > 0:
        conclusions.append(
            {
                "type": "text",
                "text": (
                    f"Обнаружено {negative_qty_count:,} позиций с отрицательным количеством "
                    f"на конец периода. Совокупный объем отрицательных остатков составляет "
                    f"{negative_qty_abs_sum:,.3f} ед."
                ).replace(",", " "),
            }
        )

        conclusions.append(
            {
                "type": "text",
                "text": (
                    "Наличие отрицательных остатков означает, что в учете отражено выбытие "
                    "или реализация товаров при отсутствии подтвержденного остатка, что "
                    "свидетельствует о нарушении логики движения запасов."
                ),
            }
        )

        conclusions.append(
            {
                "type": "text",
                "text": (
                    "Такая ситуация требует проверки документов прихода, списания, перемещения "
                    "и корректности закрытия периода по проблемным позициям."
                ),
            }
        )

        if avg_sale_price_value is not None:
            approx_value = negative_qty_abs_sum * avg_sale_price_value
            approx_value_short = _format_short_rub(approx_value)

            conclusions.append(
                {
                    "type": "rich",
                    "prefix": (
                        "По расчетной оценке масштаб затронутых остатков составляет около "
                    ),
                    "highlight": approx_value_short,
                    "suffix": ".",
                }
            )

            conclusions.append(
                {
                    "type": "text",
                    "text": (
                        "Поскольку учет по счету 45 ведется по закупочной стоимости, указанные "
                        "отклонения могут приводить к искажению себестоимости реализованных товаров."
                    ),
                }
            )

            conclusions.append(
                {
                    "type": "text",
                    "text": (
                        "В результате может быть некорректно сформирован финансовый результат, "
                        "а также налоговая база по налогу на прибыль."
                    ),
                }
            )

    if qty_no_amount_count > 0:
        conclusions.append(
            {
                "type": "text",
                "text": (
                    f"Выявлено {qty_no_amount_count:,} позиций, по которым на конец периода "
                    f"есть количество, но отсутствует сумма. Это означает, что часть остатков "
                    f"отражена в натуральном выражении без стоимости, что искажает оценку запасов."
                ).replace(",", " "),
            }
        )

    if amount_no_qty_count > 0:
        conclusions.append(
            {
                "type": "text",
                "text": (
                    f"Выявлено {amount_no_qty_count:,} позиций, по которым на конец периода "
                    f"есть сумма, но отсутствует количество. Это указывает на несоответствие "
                    f"между количественным и стоимостным учетом."
                ).replace(",", " "),
            }
        )

    if negative_amount_count > 0:
        conclusions.append(
            {
                "type": "text",
                "text": (
                    f"Обнаружено {negative_amount_count:,} позиций с отрицательной суммой "
                    f"на конец периода, что свидетельствует о возможных ошибках в стоимостном учете."
                ).replace(",", " "),
            }
        )

    conclusions.append(
        {
            "type": "text",
            "text": (
                "Выявленные расхождения означают, что показатели себестоимости продаж, "
                "остатков товаров и финансового результата могут быть недостоверны."
            ),
        }
    )

    conclusions.append(
        {
            "type": "text",
            "text": (
                "До устранения указанных отклонений использовать данные счета 45 "
                "для управленческих выводов и налогового анализа следует с осторожностью."
            ),
        }
    )

    conclusions.append(
        {
            "type": "text",
            "text": (
                "Рекомендуется провести детальную сверку движений по номенклатуре, проверить "
                "корректность проведения приходных и расходных документов, а также восстановить "
                "связь между количеством и стоимостью по проблемным позициям."
            ),
        }
    )

    return conclusions