# gear/app/costs_control/article_report/utils.py
from __future__ import annotations

import base64
import io

import pandas as pd


EXPECTED_COLUMN = "Article"


def normalise_article(
    value,
) -> str | None:
    """
    Нормализует артикул поставщика.

    Article может быть:
    - числом;
    - строкой;
    - буквенно-цифровым значением.
    """

    if value is None:
        return None

    try:
        if pd.isna(value):
            return None
    except (
        TypeError,
        ValueError,
    ):
        pass

    value_str = str(
        value
    ).strip()

    if not value_str:
        return None

    # Excel часто превращает:
    # 123456 -> 123456.0
    if value_str.endswith(
        ".0"
    ):
        try:
            number = float(
                value_str
            )

            if number.is_integer():
                value_str = str(
                    int(
                        number
                    )
                )

        except ValueError:
            pass

    return value_str.strip()


def decode_upload_contents(
    contents: str,
) -> bytes:
    """
    Декодирует содержимое dcc.Upload.
    """

    if not contents:
        raise ValueError(
            "Файл не был получен."
        )

    try:
        _, encoded = (
            contents.split(
                ",",
                1,
            )
        )

        return base64.b64decode(
            encoded
        )

    except Exception as exc:
        raise ValueError(
            "Не удалось прочитать "
            "содержимое файла."
        ) from exc


def read_articles_from_excel(
    file_bytes: bytes,
) -> list[str]:
    """
    Проверяет загруженный Excel
    и возвращает список Article.

    Требования:
    - формат .xlsx;
    - один лист;
    - одна непустая колонка;
    - название колонки Article.
    """

    buffer = io.BytesIO(
        file_bytes
    )

    try:
        excel_file = pd.ExcelFile(
            buffer,
            engine="openpyxl",
        )

    except Exception as exc:
        raise ValueError(
            "Не удалось открыть файл "
            "как Excel .xlsx."
        ) from exc

    if (
        len(
            excel_file.sheet_names
        )
        != 1
    ):
        raise ValueError(
            "В файле должен быть "
            "ровно один лист. "
            f"Найдено листов: "
            f"{len(excel_file.sheet_names)}."
        )

    sheet_name = (
        excel_file.sheet_names[0]
    )

    buffer.seek(
        0
    )

    try:
        df = pd.read_excel(
            buffer,
            sheet_name=sheet_name,
            engine="openpyxl",
            dtype=object,
        )

    except Exception as exc:
        raise ValueError(
            "Не удалось прочитать "
            "данные Excel."
        ) from exc

    # Убираем полностью
    # пустые колонки.
    df = df.dropna(
        axis=1,
        how="all",
    )

    if len(
        df.columns
    ) != 1:
        raise ValueError(
            "В файле должна быть "
            "только одна непустая "
            "колонка с названием "
            "Article. "
            f"Найдено колонок: "
            f"{len(df.columns)}."
        )

    actual_column = str(
        df.columns[0]
    ).strip()

    if (
        actual_column
        != EXPECTED_COLUMN
    ):
        raise ValueError(
            "Колонка должна называться "
            "точно «Article». "
            f"Сейчас: "
            f"«{actual_column}»."
        )

    articles: list[str] = []

    for value in df[
        EXPECTED_COLUMN
    ].tolist():

        article = (
            normalise_article(
                value
            )
        )

        if article:
            articles.append(
                article
            )

    # Убираем дубли,
    # сохраняя порядок.
    articles = list(
        dict.fromkeys(
            articles
        )
    )

    if not articles:
        raise ValueError(
            "В колонке Article "
            "нет данных."
        )

    return articles