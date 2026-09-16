# cards/upd_app/upload_man_cost.py

from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from tempfile import NamedTemporaryFile

import duckdb

from conns import connect_db


def _to_decimal(value) -> Decimal | None:
    """
    Приводит себестоимость к Decimal:

        2 010,45
        2010.45
        2010,45

    Результат округляется до 2 знаков.
    """

    if value is None:
        return None

    text = (
        str(value)
        .strip()
        .replace("\xa0", "")
        .replace(" ", "")
        .replace(",", ".")
    )

    if not text:
        return None

    try:
        return Decimal(text).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )

    except InvalidOperation:
        return None


def read_man_cost_excel(
    excel_bytes: bytes,
) -> list[dict]:
    """
    Читает Excel-шаблон управленческой себестоимости.

    Ожидаем:
      - лист: УПД;
      - ID строки: колонка A;
      - себестоимость: колонка L;
      - данные начинаются с 10-й строки.

    Конечная строка определяется автоматически:
    берутся только строки с числовым ID в колонке A.
    """

    with NamedTemporaryFile(
        suffix=".xlsx",
    ) as tmp:

        tmp.write(excel_bytes)
        tmp.flush()

        with duckdb.connect() as con:
            rows = con.execute(
                """
                SELECT
                    TRY_CAST(
                        TRIM("A")
                        AS BIGINT
                    ) AS id,

                    "L" AS man_cost_raw

                FROM read_xlsx(
                        ?,
                        sheet = 'УПД',
                        range = 'A10:L1048576',
                        header = false,
                        all_varchar = true
                    )

                WHERE TRY_CAST(
                    TRIM("A")
                    AS BIGINT
                ) IS NOT NULL
                """,
                [tmp.name],
            ).fetchall()

    result = []
    seen_ids = set()

    for row_id, raw_cost in rows:
        row_id = int(row_id)

        if row_id in seen_ids:
            raise ValueError(
                f"В Excel повторяется ID {row_id}."
            )

        seen_ids.add(row_id)

        man_cost = _to_decimal(
            raw_cost
        )

        if man_cost is None:
            raise ValueError(
                f"Для ID {row_id} не заполнена "
                "управленческая себестоимость "
                "в колонке L."
            )

        result.append(
            {
                "id": row_id,
                "man_cost_per_unit": man_cost,
            }
        )

    if not result:
        raise ValueError(
            "В файле не найдены строки с ID "
            "в колонке A и себестоимостью "
            "в колонке L."
        )

    return result


def upload_man_cost(
    upd_id,
    excel_bytes: bytes,
) -> dict:
    """
    Обновляет управленческую себестоимость только
    для строк выбранного УПД.

    Защита от неправильного файла:
    все ID из Excel должны относиться к открытому УПД.
    """

    upd_id = int(upd_id)

    rows = read_man_cost_excel(
        excel_bytes
    )

    file_ids = [
        row["id"]
        for row in rows
    ]

    with connect_db() as conn:
        with conn.cursor() as cur:

            # Находим строки, принадлежащие открытому УПД.
            cur.execute(
                """
                SELECT id
                FROM public.upd_income_lines
                WHERE upd_document_id = %s
                  AND id = ANY(%s)
                """,
                (
                    upd_id,
                    file_ids,
                ),
            )

            matched_ids = {
                int(row[0])
                for row in cur.fetchall()
            }

            missing_ids = [
                row_id
                for row_id in file_ids
                if row_id not in matched_ids
            ]

            # Не разрешаем частично загрузить чужой файл.
            if missing_ids:
                preview = ", ".join(
                    map(
                        str,
                        missing_ids[:10],
                    )
                )

                if len(missing_ids) > 10:
                    preview += ", …"

                raise ValueError(
                    "Excel не соответствует открытому УПД. "
                    f"Не найдены ID: {preview}. "
                    "Изменения не сохранены."
                )

            update_values = [
                (
                    row["man_cost_per_unit"],
                    row["id"],
                    upd_id,
                )
                for row in rows
            ]

            cur.executemany(
                """
                UPDATE public.upd_income_lines

                SET man_cost_per_unit = %s

                WHERE id = %s
                  AND upd_document_id = %s
                """,
                update_values,
            )

        conn.commit()

    total_cost = sum(
        (
            row["man_cost_per_unit"]
            for row in rows
        ),
        Decimal("0.00"),
    )

    return {
        "updated": len(rows),
        "total_cost": total_cost,
    }