# utils/upd_import/xml_import.py
import xml.etree.ElementTree as ET
import pandas as pd
import duckdb
from pathlib import Path


XML_FILE = Path(
    "/Users/daria/Desktop/131.xml"
)

OUTPUT_FILE = "./data/upd_rf/upd_ts_131_clean.parquet"


# ---------------------------------------------------------
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ---------------------------------------------------------

def to_float(value):
    if value is None:
        return None

    value = str(value).strip().replace(",", ".")

    if not value:
        return None

    try:
        return float(value)
    except ValueError:
        return None


def parse_vat_rate(value):
    """
    '22%' -> 22.0
    '20%' -> 20.0
    '10%' -> 10.0
    """
    if not value:
        return None

    value = value.replace("%", "").strip()

    return to_float(value)


def split_article_size(value):
    """
    Например:

    MC/RA059 - 38
        ->
    upd_sa_name = MC/RA059
    upd_size    = 38

    MC/CC227
        ->
    upd_sa_name = MC/CC227
    upd_size    = NULL
    """

    if not value:
        return None, None

    parts = value.split(" - ", 1)

    article = parts[0].strip()

    size = (
        parts[1].strip()
        if len(parts) > 1
        else None
    )

    return article, size


def clean_title(value):
    """
    Бюстгальтер 2 в уп (MC/RA059 - 38)
        ->
    Бюстгальтер 2 в уп
    """

    if not value:
        return None

    return value.split("(", 1)[0].strip()


# ---------------------------------------------------------
# ЧИТАЕМ XML
# ---------------------------------------------------------

tree = ET.parse(XML_FILE)

root = tree.getroot()

rows = []


# ---------------------------------------------------------
# ТОВАРНЫЕ СТРОКИ УПД
# ---------------------------------------------------------

for item in root.iter("СведТов"):

    # --------------------------
    # Основные атрибуты строки
    # --------------------------

    full_title = item.get("НаимТов")

    unit = item.get("НаимЕдИзм")

    qty = to_float(
        item.get("КолТов")
    )

    price_vatless = to_float(
        item.get("ЦенаТов")
    )

    amount_vatless = to_float(
        item.get("СтТовБезНДС")
    )

    vat_rate = parse_vat_rate(
        item.get("НалСт")
    )

    amount_vatadd = to_float(
        item.get("СтТовУчНал")
    )


    # --------------------------
    # Код товара / артикул
    # --------------------------

    additional = item.find("ДопСведТов")

    product_code = None

    if additional is not None:
        product_code = additional.get("КодТов")


    upd_sa_name, upd_size = split_article_size(
        product_code
    )


    # --------------------------
    # НДС
    # --------------------------

    vat_amount = None

    tax = item.find("СумНал")

    if tax is not None:

        tax_value = tax.find("СумНал")

        if tax_value is not None:
            vat_amount = to_float(
                tax_value.text
            )


    # --------------------------
    # Финальная строка
    # --------------------------

    rows.append(
        {
            "upd_sa_name": upd_sa_name,

            "upd_title": clean_title(
                full_title
            ),

            "upd_unit": unit,

            "upd_qty": qty,

            "upd_price_vatless": price_vatless,

            "upd_amount_vatless": amount_vatless,

            "upd_vat_rate": vat_rate,

            "upd_vat_amount": vat_amount,

            "upd_amount_vatadd": amount_vatadd,

            "upd_size": upd_size,

            # Этого поля в XML нет
            "man_cost_per_unit": None,
        }
    )


# ---------------------------------------------------------
# DATAFRAME
# ---------------------------------------------------------

df = pd.DataFrame(rows)

print(df.head())

print()
print(f"Строк загружено: {len(df)}")


# ---------------------------------------------------------
# СОХРАНЯЕМ В PARQUET
# ---------------------------------------------------------

OUTPUT_FILE = Path(OUTPUT_FILE)

OUTPUT_FILE.parent.mkdir(
    parents=True,
    exist_ok=True
)


con = duckdb.connect()

con.register(
    "upd_xml",
    df
)


con.execute(
    f"""
    COPY (
        SELECT

            upd_sa_name,

            upd_title,

            upd_unit,

            upd_qty::DOUBLE
                AS upd_qty,

            upd_price_vatless::DOUBLE
                AS upd_price_vatless,

            upd_amount_vatless::DOUBLE
                AS upd_amount_vatless,

            upd_vat_rate::DOUBLE
                AS upd_vat_rate,

            upd_vat_amount::DOUBLE
                AS upd_vat_amount,

            upd_amount_vatadd::DOUBLE
                AS upd_amount_vatadd,

            upd_size,

            man_cost_per_unit::DOUBLE
                AS man_cost_per_unit

        FROM upd_xml
    )
    TO '{OUTPUT_FILE}'
    (FORMAT PARQUET)
    """
)

con.close()


print(
    f"Готово: {OUTPUT_FILE}"
)